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
        inactive_notes = []
        notes_to_release = []

        for note, channel_note in self.active_notes.items():
            if not channel_note.is_active():
                inactive_notes.append(note)
                notes_to_release.append(channel_note)

        for note in inactive_notes:
            # Deallocate voice from voice manager
            self.voice_manager.deallocate_voice(note)
            del self.active_notes[note]

        # Release pooled resources for inactive notes
        for channel_note in notes_to_release:
            channel_note.release_resources()

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

        # Pre-calculate controller values once per buffer
        mod_wheel = self.controllers.get(1, 0)
        breath_controller = self.controllers.get(2, 0)
        foot_controller = self.controllers.get(4, 0)
        brightness = self.controllers.get(72, 64)
        harmonic_content = self.controllers.get(71, 64)
        channel_pressure_value = self.channel_pressure_value

        # Use optimized processing with pre-computed values
        return self._generate_optimized_sample(
            mod_wheel, breath_controller, foot_controller,
            brightness, harmonic_content, channel_pressure_value
        )

    def _generate_optimized_sample(self, mod_wheel, breath_controller, foot_controller,
                                  brightness, harmonic_content, channel_pressure_value):
        """Optimized per-sample generation using pre-computed values."""
        left_sum = 0.0
        right_sum = 0.0

        # Precompute commonly used values to avoid repeated calculations
        global_pitch_mod_cents = self.pitch_bend_range * 100
        global_pitch_mod = ((self.pitch_bend_value - 8192) / 8192.0) * global_pitch_mod_cents

        # Cache volume and expression (most frequently changing controller values)
        cached_volume = self.controllers[7]  # Volume
        cached_expression = self.controllers[11]  # Expression

        # Process all active notes with cached controller values
        active_notes_items = list(self.active_notes.items())
        for note, channel_note in active_notes_items:
            # Use cached key pressure when available
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
                volume=cached_volume,
                expression=cached_expression,
                global_pitch_mod=global_pitch_mod
            )
            left_sum += left
            right_sum += right

        # Pre-compute channel effects for better performance
        volume_factor = (cached_volume / 127.0) * (cached_expression / 127.0)

        # Apply channel volume optimization
        left_out = left_sum * volume_factor
        right_out = right_sum * volume_factor

        # Optimized panning with early exit for center position
        pan_value = (self.pan - 64) / 64.0  # Convert to -1.0 to 1.0 range
        if abs(pan_value) > 0.001:  # Only if panning is significant
            # Pre-compute panning gains to avoid repeated calculations
            pan_left = 0.5 * (1.0 - pan_value)
            pan_right = 0.5 * (1.0 + pan_value)
            left_out *= pan_left
            right_out *= pan_right

        # Optimized clamping using max/min instead of if-else chains
        left_clamped = max(-1.0, min(1.0, left_out))
        right_clamped = max(-1.0, min(1.0, right_out))

        return (left_clamped, right_clamped)

    # XG-specific controller handlers
    def _handle_xg_harmonic_content(self, value: int):
        """Handle XG Harmonic Content controller (71)"""
        # Map 0-127 to harmonic content range
        normalized_value = value / 127.0
        # Apply to all active notes - affects timbre/harmonic structure
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_harmonic_content'):
                    partial.set_harmonic_content(normalized_value)

    def _handle_xg_brightness(self, value: int):
        """Handle XG Brightness controller (72)"""
        # Map 0-127 to brightness range
        normalized_value = value / 127.0
        # Apply to all active notes - affects filter brightness
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'set_brightness'):
                    partial.set_brightness(normalized_value)

    def _handle_xg_release_time(self, value: int):
        """Handle XG Release Time controller (73)"""
        # Map 0-127 to release time range (typically 0.001 to 10.0 seconds)
        release_time = 0.001 + (value / 127.0) * 9.999
        # Apply to all active notes - affects envelope release time
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(release=release_time)

    def _handle_xg_attack_time(self, value: int):
        """Handle XG Attack Time controller (74)"""
        # Map 0-127 to attack time range (typically 0.001 to 1.0 seconds)
        attack_time = 0.001 + (value / 127.0) * 0.999
        # Apply to all active notes - affects envelope attack time
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(attack=attack_time)

    def _handle_xg_filter_cutoff(self, value: int):
        """Handle XG Filter Cutoff controller (75)"""
        # Map 0-127 to filter cutoff frequency range
        normalized_value = value / 127.0
        # Apply to all active notes - affects filter cutoff
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(normalized_value)

    def _handle_xg_decay_time(self, value: int):
        """Handle XG Decay Time controller (76)"""
        # Map 0-127 to decay time range (typically 0.01 to 5.0 seconds)
        decay_time = 0.01 + (value / 127.0) * 4.99
        # Apply to all active notes - affects envelope decay time
        for note in self.active_notes.values():
            for partial in note.partials:
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(decay=decay_time)

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

    # XG Part Mode Implementation
    def set_part_mode(self, mode: int):
        """Set XG part mode and apply changes"""
        self.part_mode = max(0, min(127, mode))  # Validate range
        self._apply_part_mode()

    def _apply_part_mode(self):
        """Apply XG part mode specific behaviors according to XG specification"""
        # Apply part mode-specific changes according to XG specification
        if self.part_mode == 0:  # Normal Mode
            self._apply_normal_mode_parameters()
        elif self.part_mode == 1:  # Hyper Scream Mode
            self._apply_hyper_scream_mode_parameters()
        elif self.part_mode == 2:  # Analog Mode
            self._apply_analog_mode_parameters()
        elif self.part_mode == 3:  # Max Resonance Mode
            self._apply_max_resonance_mode_parameters()
        elif self.part_mode == 4:  # Stereo Mode
            self._apply_stereo_mode_parameters()
        elif self.part_mode == 5:  # Wah Mode
            self._apply_wah_mode_parameters()
        elif self.part_mode == 6:  # Dynamic Mode
            self._apply_dynamic_mode_parameters()
        elif self.part_mode == 7:  # Distortion Mode
            self._apply_distortion_mode_parameters()
        else:
            # Default to normal mode for undefined part modes
            self._apply_normal_mode_parameters()

        # Update all active notes with new parameters
        self._update_active_notes_for_part_mode()

    def _apply_normal_mode_parameters(self):
        """Apply Normal Mode parameters (XG Standard)"""
        # Standard synthesis parameters - no special modifications
        for note in self.active_notes.values():
            for partial in note.partials:
                # Reset to standard envelope parameters
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.01, decay=0.1, sustain=0.8, release=0.3
                    )
                # Reset filter parameters
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(1.0)  # Normalized cutoff
                    partial.filter.set_resonance(0.1)  # Low resonance

    def _apply_hyper_scream_mode_parameters(self):
        """Apply Hyper Scream Mode parameters (XG Aggressive)"""
        for note in self.active_notes.values():
            for partial in note.partials:
                # Modify envelope for more aggressive sound
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.001, decay=0.05, sustain=0.9, release=0.1
                    )
                # Increase filter resonance and adjust cutoff
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(0.8)  # Higher cutoff
                    partial.filter.set_resonance(0.7)  # High resonance

    def _apply_analog_mode_parameters(self):
        """Apply Analog Mode parameters (XG Warmer Sound)"""
        for note in self.active_notes.values():
            for partial in note.partials:
                # Soften envelope for warmer sound
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.02, decay=0.2, sustain=0.7, release=0.5
                    )
                # Reduce filter resonance for smoother sound
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(0.9)  # Slightly lower cutoff
                    partial.filter.set_resonance(0.05)  # Very low resonance

    def _apply_max_resonance_mode_parameters(self):
        """Apply Max Resonance Mode parameters (XG High Resonance)"""
        for note in self.active_notes.values():
            for partial in note.partials:
                # Standard envelope
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.01, decay=0.1, sustain=0.8, release=0.3
                    )
                # Maximum filter resonance
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(0.7)  # Moderate cutoff
                    partial.filter.set_resonance(1.0)  # Maximum resonance

    def _apply_stereo_mode_parameters(self):
        """Apply Stereo Mode parameters (XG Enhanced Stereo)"""
        # Enhance stereo imaging - this would typically affect panning
        self.pan = 64  # Center pan as base
        # Could implement stereo-specific processing here

    def _apply_wah_mode_parameters(self):
        """Apply Wah Mode parameters (XG Wah Effect)"""
        for note in self.active_notes.values():
            for partial in note.partials:
                # Modify filter for wah-like behavior
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(0.6)  # Lower cutoff for wah
                    partial.filter.set_resonance(0.8)  # High resonance for wah

    def _apply_dynamic_mode_parameters(self):
        """Apply Dynamic Mode parameters (XG Velocity Sensitive)"""
        # This mode would typically make parameters more velocity-sensitive
        # Implementation would depend on velocity-to-parameter mapping
        pass

    def _apply_distortion_mode_parameters(self):
        """Apply Distortion Mode parameters (XG Distorted Sound)"""
        for note in self.active_notes.values():
            for partial in note.partials:
                # Modify envelope for distorted sound
                if hasattr(partial, 'amp_envelope') and partial.amp_envelope:
                    partial.amp_envelope.update_parameters(
                        attack=0.001, decay=0.02, sustain=1.0, release=0.05
                    )
                # Adjust filter for distortion
                if hasattr(partial, 'filter') and partial.filter:
                    partial.filter.set_cutoff(0.5)  # Lower cutoff
                    partial.filter.set_resonance(0.6)  # Moderate-high resonance

    def _update_active_notes_for_part_mode(self):
        """Update all active notes when part mode changes"""
        # This method ensures that parameter changes are applied to existing notes
        # The actual parameter updates happen in the individual mode methods above
        pass
