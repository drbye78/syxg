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
        self.controllers[64] = 0    # Sustain Pedal

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
            "controllers": self.controllers.copy(),
            "channel_pressure_value": self.channel_pressure_value,
            "key_pressure": self.key_pressure_values.copy(),
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

        for note in self.active_notes.values():
            left, right = note.generate_sample(channel_state, global_pitch_mod)
            left_sum += left
            right_sum += right

        # Apply channel volume and expression
        channel_volume = (self.volume / 127.0) * (self.expression / 127.0)
        left_out = left_sum * channel_volume
        right_out = right_sum * channel_volume

        # Apply panning and balance
        # Panning: -1.0 (left) to 1.0 (right)
        pan = (self.pan - 64) / 64.0
        # Balance: -1.0 (left) to 1.0 (right)
        balance = (self.balance - 64) / 64.0

        # Combine pan and balance effects
        combined_pan = pan + balance * 0.5  # Balance has half the effect of pan
        combined_pan = max(-1.0, min(1.0, combined_pan))  # Clamp to valid range

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
