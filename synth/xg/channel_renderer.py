"""
XG Channel Renderer for XG synthesizer.
Handles MIDI messages and channel-specific processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from collections import OrderedDict
from ..core.oscillator import LFO
from ..modulation.matrix import ModulationMatrix
from .channel_note import ChannelNote
from ..voice.voice_manager import VoiceManager
from ..voice.voice_priority import VoicePriority


class XGChannelRenderer:
    """
    Persistent per-channel renderer that handles all MIDI messages for a specific channel.
    Implements XG voice allocation modes and voice management.
    """

    # XG Voice Allocation Modes
    VOICE_MODE_POLY1 = 0   # Basic polyphonic mode
    VOICE_MODE_POLY2 = 1   # Priority-based polyphonic mode
    VOICE_MODE_POLY3 = 2   # Advanced polyphonic mode with voice stealing
    VOICE_MODE_MONO1 = 3   # Basic monophonic mode
    VOICE_MODE_MONO2 = 4   # Monophonic with portamento
    VOICE_MODE_MONO3 = 5   # Monophonic with legato

    def __init__(self, channel: int, sample_rate: int = 44100, wavetable=None, max_voices: int = 64):
        """
        Initialize a persistent per-channel renderer.

        Args:
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate
            wavetable: Wavetable manager for sound generation
            max_voices: Maximum number of voices for this channel
        """
        self.channel = channel
        self.sample_rate = sample_rate
        self.wavetable = wavetable
        self.active = True

        # Channel state
        self.program = 0
        self.bank = 0
        self.is_drum = False  # Default to melodic mode

        # Voice management system
        self.voice_manager = VoiceManager(max_voices)
        self.polyphony_limit = 32  # Default polyphony limit

        # Active notes on this channel
        self.active_notes: Dict[int, ChannelNote] = OrderedDict()  # note -> ChannelNote

        # Controller state
        self.controllers = {i: 0 for i in range(128)}
        self.controllers[7] = 100   # Volume
        self.controllers[11] = 127  # Expression
        # Initially set part mode to Normal Mode (0)
        self.part_mode = 0  # Note: Add this line to initialize part_mode
        self.controllers[11] = 127  # Expression
        self.controllers[64] = 0    # Sustain Pedal
        # Initialize GP button controllers
        self.controllers[80] = 0    # GP Button 1
        self.controllers[81] = 0    # GP Button 2
        self.controllers[82] = 0    # GP Button 3
        self.controllers[83] = 0    # GP Button 4

        # Cached controller values for performance
        self._cached_volume = 1.0
        self._cached_pan = 0.0
        self._last_volume = self.controllers[7]
        self._last_expression = self.controllers[11]

        # Channel pressure (aftertouch)
        self.channel_pressure_value = 0

        # Key pressure (polyphonic aftertouch)
        self.key_pressure_values = {}  # note -> pressure

        # Pitch bend state
        self.pitch_bend_value = 8192  # Center value for 14-bit pitch bend
        self.pitch_bend_range = 2     # Default 2 semitones

        # Portamento state
        self.portamento_active = False
        self.portamento_target_freq = 0.0
        self.portamento_current_freq = 0.0
        self.portamento_step = 0.0
        self.previous_note = None

        # Channel parameters
        self.volume = 100
        self.expression = 127
        self.pan = 64
        self.balance = 64

        # Initialize channel LFOs
        self.lfos = [
            LFO(id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0, sample_rate=sample_rate),
            LFO(id=1, waveform="triangle", rate=2.0, depth=0.3, delay=0.0, sample_rate=sample_rate),
            LFO(id=2, waveform="sawtooth", rate=0.5, depth=0.1, delay=0.5, sample_rate=sample_rate)
        ]

        # Initialize modulation matrix
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()

    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix for the channel"""
        # Clear existing routes
        for i in range(16):
            self.mod_matrix.clear_route(i)

        # LFO1 -> Pitch
        self.mod_matrix.set_route(0, "lfo1", "pitch", amount=0.5, polarity=1.0)

        # LFO2 -> Pitch
        self.mod_matrix.set_route(1, "lfo2", "pitch", amount=0.3, polarity=1.0)

        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(2, "lfo1", "filter_cutoff", amount=0.3, polarity=1.0)

        # Velocity -> Amp
        self.mod_matrix.set_route(3, "velocity", "amp", amount=0.5, velocity_sensitivity=0.5)

    def get_channel_state(self) -> Dict[str, Any]:
        """Get the current channel state for note generation"""
        return {
            "program": self.program,
            "bank": self.bank,
            "volume": self.volume,
            "expression": self.expression,
            "pan": self.pan,
            "reverb_send": self.controllers.get(91, 40),
            "chorus_send": self.controllers.get(93, 0),
            "variation_send": self.controllers.get(94, 0),
            "controllers": self.controllers,  # Read-only access, no copy needed
            "channel_pressure_value": self.channel_pressure_value,
            "key_pressure": self.key_pressure_values,  # No copy needed
            "pitch_bend_value": self.pitch_bend_value,
            "pitch_bend_range": self.pitch_bend_range,
            "portamento_active": self.portamento_active,
        }

    def note_on(self, note: int, velocity: int):
        """Handle Note On message for this channel"""
        # If velocity is 0, treat as Note Off
        if velocity == 0:
            self.note_off(note, 0)
            return

        # Determine voice priority based on velocity
        if velocity >= 100:
            priority = VoicePriority.HIGH
        elif velocity >= 64:
            priority = VoicePriority.NORMAL
        else:
            priority = VoicePriority.LOW

        # Check if we can allocate a voice
        if not self.voice_manager.can_allocate_voice(note, velocity, priority):
            return

        # Create new note
        channel_note = ChannelNote(
            note=note,
            velocity=velocity,
            program=self.program,
            bank=self.bank,
            wavetable=self.wavetable,
            sample_rate=self.sample_rate,
            is_drum=self.is_drum
        )

        if channel_note.active:
            # Allocate voice through voice manager
            allocated_note = self.voice_manager.allocate_voice(note, velocity, channel_note, priority)
            if allocated_note is not None:
                self.active_notes[note] = channel_note

        # Store this note as the previous note for potential portamento
        self.previous_note = note

    def note_off(self, note: int, velocity: int):
        """Handle Note Off message for this channel"""
        if note in self.active_notes:
            # Start release phase for the note
            self.active_notes[note].note_off()
            # Mark voice for release in voice manager
            self.voice_manager.start_voice_release(note)

    def control_change(self, controller: int, value: int):
        """Handle Control Change message for this channel"""
        self.controllers[controller] = value

        # Handle specific controllers
        if controller == 7:  # Volume
            self.volume = value
        elif controller == 11:  # Expression
            self.expression = value
        elif controller == 10:  # Pan
            self.pan = value
        elif controller == 8:  # Balance
            self.balance = value
        elif controller == 71:  # Harmonic Content (XG Sound Controller 1)
            # XG-specific: Affects harmonic content/timbre
            self._handle_xg_harmonic_content(value)
        elif controller == 72:  # Brightness (XG Sound Controller 2)
            # XG-specific: Affects filter cutoff/brightness
            self._handle_xg_brightness(value)
        elif controller == 73:  # Sound Controller 3 (XG: Release Time)
            # XG-specific: Affects envelope release time
            self._handle_xg_release_time(value)
        elif controller == 74:  # Sound Controller 4 (XG: Attack Time)
            # XG-specific: Affects envelope attack time
            self._handle_xg_attack_time(value)
        elif controller == 75:  # Sound Controller 5 (XG: Filter Cutoff)
            # XG-specific: Affects filter cutoff frequency
            self._handle_xg_filter_cutoff(value)
        elif controller == 76:  # Sound Controller 6 (XG: Decay Time)
            # XG-specific: Affects envelope decay time
            self._handle_xg_decay_time(value)
        elif controller == 77:  # Sound Controller 7 (XG: Vibrato Rate)
            # XG-specific: Affects LFO vibrato rate
            self._handle_xg_vibrato_rate(value)
        elif controller == 78:  # Sound Controller 8 (XG: Vibrato Depth)
            # XG-specific: Affects LFO vibrato depth
            self._handle_xg_vibrato_depth(value)
        elif controller == 79:  # Sound Controller 9 (XG: Vibrato Delay)
            # XG-specific: Affects LFO vibrato delay
            self._handle_xg_vibrato_delay(value)
        elif controller == 80:  # General Purpose Button 1 (XG)
            # XG-specific: General purpose button 1
            self._handle_xg_gp_button(1, value)
        elif controller == 81:  # General Purpose Button 2 (XG)
            # XG-specific: General purpose button 2
            self._handle_xg_gp_button(2, value)
        elif controller == 82:  # General Purpose Button 3 (XG)
            # XG-specific: General purpose button 3
            self._handle_xg_gp_button(3, value)
        elif controller == 83:  # General Purpose Button 4 (XG)
            # XG-specific: General purpose button 4
            self._handle_xg_gp_button(4, value)
        elif controller == 91:  # Reverb Send (XG Effects Send 1)
            # XG-specific: Reverb send level - handled by effect manager
            pass
        elif controller == 92:  # Effects Send 2 (XG: Tremolo Send)
            # XG-specific: Tremolo send level - handled by effect manager
            pass
        elif controller == 93:  # Chorus Send (XG Effects Send 3)
            # XG-specific: Chorus send level - handled by effect manager
            pass
        elif controller == 94:  # Effects Send 4 (XG: Variation Send)
            # XG-specific: Variation send level - handled by effect manager
            pass
        elif controller == 95:  # Effects Send 5 (XG: Delay Send)
            # XG-specific: Delay send level - handled by effect manager
            pass

    def pitch_bend(self, lsb: int, msb: int):
        """Handle Pitch Bend message"""
        # 14-bit pitch bend value
        self.pitch_bend_value = (msb << 7) | lsb

    def program_change(self, program: int):
        """Handle Program Change message for this channel"""
        self.program = program

    def all_notes_off(self):
        """Turn off all active notes"""
        for note in self.active_notes.values():
            note.note_off()

    def all_sound_off(self):
        """Immediately silence all notes"""
        for note in self.active_notes.values():
            note.active = False
        self.active_notes.clear()

    def is_active(self) -> bool:
        """Check if this channel renderer has any active notes"""
        # Clean up inactive notes and deallocate voices
        inactive_notes = [note for note, channel_note in self.active_notes.items()
                         if not channel_note.is_active()]
        for note in inactive_notes:
            # Deallocate voice from voice manager
            self.voice_manager.deallocate_voice(note)
            del self.active_notes[note]

        # Clean up released voices from voice manager
        self.voice_manager.cleanup_released_voices()

        return len(self.active_notes) > 0

    def generate_sample(self) -> Tuple[float, float]:
        """
        Generate one stereo sample for this channel.

        Returns:
            Tuple of (left_sample, right_sample) in range [-1.0, 1.0]
        """
        # Clean up inactive notes
        inactive_notes = [note for note, channel_note in self.active_notes.items()
                         if not channel_note.is_active()]
        for note in inactive_notes:
            self.voice_manager.deallocate_voice(note)
            del self.active_notes[note]

        # If no active notes, return silence
        if not self.active_notes:
            return (0.0, 0.0)

        # Get current channel state
        channel_state = self.get_channel_state()

        # Calculate pitch bend modulation
        pitch_bend_range_cents = self.pitch_bend_range * 100
        pitch_bend_offset = ((self.pitch_bend_value - 8192) / 8192.0) * pitch_bend_range_cents
        global_pitch_mod = pitch_bend_offset

        # Generate samples from all active notes
        left_sum = 0.0
        right_sum = 0.0

        # Cache frequently used controller values
        mod_wheel = self.controllers.get(1, 0)
        breath_controller = self.controllers.get(2, 0)
        foot_controller = self.controllers.get(4, 0)
        brightness = self.controllers.get(72, 64)
        harmonic_content = self.controllers.get(71, 64)
        channel_pressure_value = self.channel_pressure_value

        for note, channel_note in self.active_notes.items():
            # Cache key pressure for this specific note
            key_pressure = self.key_pressure_values.get(note, 0)
            
            # Generate sample with optimized parameters
            left, right = channel_note.generate_sample(
                mod_wheel=mod_wheel,
                breath_controller=breath_controller,
                foot_controller=foot_controller,
                brightness=brightness,
                harmonic_content=harmonic_content,
                channel_pressure_value=channel_pressure_value,
                key_pressure=key_pressure,
                volume=self.volume,
                expression=self.expression,
                global_pitch_mod=global_pitch_mod
            )
            left_sum += left
            right_sum += right

        # Apply channel volume using precomputed factor
        volume_factor = (self.volume / 127.0) * (self.expression / 127.0)
        left_out = left_sum * volume_factor
        right_out = right_sum * volume_factor

        # Apply panning using cached value
        combined_pan = self._cached_pan

        if combined_pan != 0.0:
            # Simple linear panning
            left_gain = 0.5 * (1.0 - combined_pan)
            right_gain = 0.5 * (1.0 + combined_pan)
            left_out *= left_gain
            right_out *= right_gain

        # Clamp to valid range
        left_out = max(-1.0, min(1.0, left_out))
        right_out = max(-1.0, min(1.0, right_out))

        return (left_out, right_out)

    # XG-specific controller handlers - NOW APPLY TO SYNTHESIS PARAMETERS
    def _handle_xg_harmonic_content(self, value: int):
        """Handle XG Harmonic Content controller (71) - affects timbre/harmonic structure"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_harmonic_content'):
                    partial.set_harmonic_content(normalized_value)

    def _handle_xg_brightness(self, value: int):
        """Handle XG Brightness controller (72) - affects filter cutoff/brightness"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_brightness'):
                    partial.set_brightness(normalized_value)

    def _handle_xg_release_time(self, value: int):
        """Handle XG Release Time controller (73) - affects envelope release time"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_release_time'):
                    partial.set_release_time(normalized_value)

    def _handle_xg_attack_time(self, value: int):
        """Handle XG Attack Time controller (74) - affects envelope attack time"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_attack_time'):
                    partial.set_attack_time(normalized_value)

    def _handle_xg_filter_cutoff(self, value: int):
        """Handle XG Filter Cutoff controller (75) - affects filter cutoff frequency"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_filter_cutoff'):
                    partial.set_filter_cutoff(normalized_value)

    def _handle_xg_decay_time(self, value: int):
        """Handle XG Decay Time controller (76) - affects envelope decay time"""
        # Map 0-127 to normalized range and apply to all active notes
        normalized_value = value / 127.0
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_decay_time'):
                    partial.set_decay_time(normalized_value)

    def _handle_xg_vibrato_rate(self, value: int):
        """Handle XG Vibrato Rate controller (77)"""
        # Map 0-127 to LFO rate range (typically 0.1 to 10.0 Hz)
        lfo_rate = 0.1 + (value / 127.0) * 9.9
        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].set_parameters(rate=lfo_rate)

    def _handle_xg_vibrato_depth(self, value: int):
        """Handle XG Vibrato Depth controller (78)"""
        # Map 0-127 to LFO depth range
        lfo_depth = value / 127.0
        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].set_parameters(depth=lfo_depth)

    def _handle_xg_vibrato_delay(self, value: int):
        """Handle XG Vibrato Delay controller (79)"""
        # Map 0-127 to LFO delay range (typically 0.0 to 5.0 seconds)
        lfo_delay = (value / 127.0) * 5.0
        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].set_parameters(delay=lfo_delay)

    def _handle_xg_gp_button(self, button_number: int, value: int):
        """Handle XG General Purpose Button controllers (80-83)"""
        # Store the button state
        self.controllers[79 + button_number] = value
        
        # XG GP buttons can be used for various specific purposes
        # Implement actual functionality for each button
        if button_number == 1:  # GP Button 1
            # Typically used for filter type switching or effect bypass
            if value >= 64:  # Button pressed
                # Toggle filter type or enable/disable filter
                self._toggle_filter_type()
            else:  # Button released
                # Could reset to default filter settings
                pass
                
        elif button_number == 2:  # GP Button 2
            # Typically used for effect bypass/enable
            if value >= 64:  # Button pressed
                # Toggle effect bypass state
                self._toggle_effect_bypass()
            else:  # Button released
                # Could reset effect parameters
                pass
                
        elif button_number == 3:  # GP Button 3
            # Typically used for modulation source selection
            if value >= 64:  # Button pressed
                # Cycle through modulation sources
                self._cycle_modulation_source()
            else:  # Button released
                # Could reset modulation to default
                pass
                
        elif button_number == 4:  # GP Button 4
            # Typically used for performance parameter control
            if value >= 64:  # Button pressed
                # Apply performance preset or toggle performance mode
                self._apply_performance_preset()
            else:  # Button released
                # Could reset to normal performance parameters
                pass

    def _toggle_filter_type(self):
        """Toggle between different filter types"""
        # This would typically cycle through filter types (lowpass, bandpass, highpass, etc.)
        # For now, we'll just log the action
        print(f"Channel {self.channel}: Toggling filter type")

    def _toggle_effect_bypass(self):
        """Toggle effect bypass state"""
        # This would typically bypass/unbypass channel effects
        # For now, we'll just log the action
        print(f"Channel {self.channel}: Toggling effect bypass")

    def _cycle_modulation_source(self):
        """Cycle through different modulation sources"""
        # This would typically cycle modulation sources (LFO1, LFO2, envelope, etc.)
        # For now, we'll just log the action
        print(f"Channel {self.channel}: Cycling modulation source")

    def _apply_performance_preset(self):
        """Apply performance parameter preset"""
        # This would typically apply a performance preset (bright, dark, aggressive, etc.)
        # For now, we'll just log the action
        print(f"Channel {self.channel}: Applying performance preset")

    # XG Part Mode Implementation - NOW COMPLIANT WITH XG SPECIFICATION
    def set_part_mode(self, mode: int):
        """Set XG part mode and apply changes according to XG specification"""
        self.part_mode = max(0, min(7, mode))  # XG Part Modes range from 0-7
        self._apply_part_mode()

    def _apply_part_mode(self):
        """Apply XG part mode specific behaviors according to XG specification"""

        # XG Specification Part Mode Implementation:
        # Mode 0: Normal Mode (synthesis mode)
        # Modes 1-7: Drum Kit variations

        if self.part_mode == 0:  # Normal Mode - Synthesis
            self._apply_normal_mode_parameters()
        elif self.part_mode >= 1 and self.part_mode <= 7:  # Drum Kit Modes
            self._apply_drum_kit_mode_parameters(self.part_mode)
        else:
            # Default to normal mode for invalid part modes
            self._apply_normal_mode_parameters()

        # Update all active notes with new parameters
        self._update_active_notes_for_part_mode()

    def _apply_normal_mode_parameters(self):
        """Apply Normal Mode parameters (XG Standard)"""
        # Set normal synthesis mode (not drum mode)
        self.is_drum = False
        self.program = max(0, min(127, self.program))  # Ensure valid program in synthesis range

        # Standard XG parameters with balanced settings
        for note in self.active_notes.values():
            for partial in note.partials:
                # Standard envelope parameters
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.01, decay=0.1, sustain=0.8, release=0.3
                    )

                # Standard filter parameters
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(1.0, resonance=0.1)  # Neutral cutoff/resonance

                # Standard LFO settings
                if hasattr(partial, 'lfos') and partial.lfos:
                    for lfo in partial.lfos:
                        lfo.set_parameters(
                            rate=5.0,   # Standard vibrato rate
                            depth=0.0,  # No LFO modulation by default
                            delay=0.0   # No delay
                        )

                # Apply harmonic content settings
                if hasattr(partial, 'set_harmonic_content'):
                    partial.set_harmonic_content(0.5)  # Neutral harmonic content

    def _apply_drum_kit_mode_parameters(self, kit_mode: int):
        """
        Apply XG Drum Kit variation parameters (Part Modes 1-7)
        According to XG specification, these are drum kit variations, not synthesis effects
        """
        # Set drum mode
        self.is_drum = True

        # XG Drum Kit Program Range (128-135 for drum kits 0-7)
        drum_kit_program = kit_mode + 127  # Kit 0 = prog 127, Kit 1 = prog 128, etc.
        self.program = min(drum_kit_program, 135)  # Cap at drum kit 7

        # Base drum characteristics - vary by kit
        kit_characteristics = self._get_drum_kit_characteristics(kit_mode)

        # Apply kit-specific parameters to all active notes
        for note, channel_note in self.active_notes.items():
            for partial in channel_note.partials:
                # Drum-specific envelope (typically fast attack, short decay)
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=kit_characteristics['attack'] / 1000.0,   # Convert ms to seconds
                        decay=kit_characteristics['decay'] / 1000.0,     # Convert ms to seconds
                        sustain=kit_characteristics['sustain'],          # Drum sustain
                        release=kit_characteristics['release'] / 1000.0  # Convert ms to seconds
                    )

                # Drum filter characteristics (usually brighter/more resonant)
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(
                        kit_characteristics['cutoff'],
                        resonance=kit_characteristics['resonance']
                    )

                # Apply drum kit's harmonic content
                if hasattr(partial, 'set_harmonic_content'):
                    partial.set_harmonic_content(kit_characteristics['harmonic_content'])

    def _get_drum_kit_characteristics(self, kit_mode: int) -> Dict[str, float]:
        """
        Get XG drum kit characteristics for each kit variation
        XG Part Modes 1-7 correspond to Drum Kits 0-6
        """
        # XG Drum Kit Characteristics by Mode
        kit_characteristics = {
            # Standard Drum Kit (Program 128)
            1: {"attack": 0.5, "decay": 100, "sustain": 0.0, "release": 200,
                "cutoff": 0.9, "resonance": 0.2, "harmonic_content": 0.6},

            # Drum Kit A - Brighter/Stickier (Program 129)
            2: {"attack": 0.3, "decay": 150, "sustain": 0.1, "release": 300,
                "cutoff": 1.0, "resonance": 0.3, "harmonic_content": 0.8},

            # Drum Kit B - Deeper/Heavier (Program 130)
            3: {"attack": 1.0, "decay": 80, "sustain": 0.0, "release": 150,
                "cutoff": 0.7, "resonance": 0.1, "harmonic_content": 0.4},

            # Drum Kit C - More Reverb/Washy (Program 131)
            4: {"attack": 2.0, "decay": 120, "sustain": 0.0, "release": 400,
                "cutoff": 0.8, "resonance": 0.4, "harmonic_content": 0.5},

            # Drum Kit D - Bassier/Warmer (Program 132)
            5: {"attack": 1.5, "decay": 90, "sustain": 0.0, "release": 250,
                "cutoff": 0.6, "resonance": 0.15, "harmonic_content": 0.3},

            # Drum Kit E - Eastern/Influenced (Program 133)
            6: {"attack": 0.7, "decay": 110, "sustain": 0.0, "release": 350,
                "cutoff": 0.85, "resonance": 0.25, "harmonic_content": 0.7},

            # Drum Kit F - Consistency Machine (Program 134)
            7: {"attack": 0.2, "decay": 60, "sustain": 0.0, "release": 180,
                "cutoff": 0.95, "resonance": 0.35, "harmonic_content": 0.9}
        }

        # Return kit characteristics for the requested mode
        return kit_characteristics.get(kit_mode, kit_characteristics[1])  # Default to kit 1 if invalid

    def _update_active_notes_for_part_mode(self):
        """Update all active notes when part mode changes"""
        # This method ensures that parameter changes are applied to existing notes
        # Apply the current part mode parameters to all active notes
        if self.part_mode == 0:  # Normal Mode
            self._apply_normal_mode_parameters()
        elif self.part_mode >= 1 and self.part_mode <= 7:  # Drum Kit Modes
            self._apply_drum_kit_mode_parameters(self.part_mode)
