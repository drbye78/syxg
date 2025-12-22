"""
XG Channel implementation for synthesizer.

Provides the Channel class that manages MIDI channel state and voice assignment
using the new Voice abstraction layer.
"""

from typing import Dict, Optional, Any
import numpy as np

from .channel_note import ChannelNote
from ..voice.voice_factory import VoiceFactory


class Channel:
    """
    XG MIDI Channel - manages voice assignment and channel-level state.

    A Channel represents a single MIDI channel (0-15) that can play voices.
    It handles program changes, bank selection, controller processing, and
    routes MIDI events to the appropriate voice.

    XG Specification Compliance:
    - Channel key range and transposition
    - Bank/program selection with XG bank mapping
    - Controller processing and NRPN/RPN support
    - Multi-timbral operation
    """

    def __init__(self, channel_number: int, voice_factory: VoiceFactory, sample_rate: int):
        """
        Initialize XG Channel.

        Args:
            channel_number: MIDI channel number (0-15)
            voice_factory: Factory for creating voices
            sample_rate: Audio sample rate in Hz
        """
        self.channel_number = channel_number
        self.voice_factory = voice_factory
        self.sample_rate = sample_rate

        # Voice management
        self.current_voice = None
        self.program = 0
        self.bank_msb = 0
        self.bank_lsb = 0
        self.bank = 0

        # Channel state
        self.active = True
        self._muted = False
        self._solo = False

        # XG channel parameters
        self.key_range_low = 0
        self.key_range_high = 127
        self.master_level = 1.0
        self.pan = 0.0
        self.transpose = 0

        # Controller state
        self.controllers = [0] * 128
        self._initialize_default_controllers()

        # Channel pressure and key pressure
        self._channel_pressure = 0
        self.key_pressure_values: Dict[int, int] = {}

        # Pitch bend state
        self.pitch_bend_value = 8192  # Center position
        self.pitch_bend_range = 2.0   # Default ±2 semitones

        # NRPN/RPN state
        self.nrpn_active = False
        self.rpn_active = False
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.rpn_msb = 0
        self.rpn_lsb = 0
        self.data_msb = 0
        self.data_msb_received = False

    def _initialize_default_controllers(self):
        """Initialize default controller values per GM/XG specification."""
        # GM/XG default values
        self.controllers[7] = 100   # Volume
        self.controllers[10] = 64   # Pan (center)
        self.controllers[11] = 127  # Expression
        self.controllers[64] = 0    # Sustain pedal
        self.controllers[71] = 64   # Harmonic Content (XG)
        self.controllers[72] = 64   # Brightness (XG)
        self.controllers[73] = 0    # Release Time (XG)
        self.controllers[74] = 0    # Attack Time (XG)
        self.controllers[91] = 40   # Reverb send
        self.controllers[93] = 0    # Chorus send

    def load_program(self, program: int, bank_msb: int = 0, bank_lsb: int = 0):
        """
        Load a program (voice) for this channel.

        Args:
            program: MIDI program number (0-127)
            bank_msb: Bank select MSB (0-127)
            bank_lsb: Bank select LSB (0-127)
        """
        self.program = program
        self.bank_msb = bank_msb
        self.bank_lsb = bank_lsb
        self.bank = (bank_msb << 7) | bank_lsb

        # Create new voice using factory
        self.current_voice = self.voice_factory.create_voice(
            bank=self.bank,
            program=program,
            channel=self.channel_number,
            sample_rate=self.sample_rate
        )

    def note_on(self, note: int, velocity: int) -> bool:
        """
        Handle note-on event.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)

        Returns:
            True if note was accepted, False otherwise
        """
        if not self.current_voice or self.muted:
            return False

        # Apply channel transposition
        transposed_note = note + self.transpose

        # Check channel key range
        if not (self.key_range_low <= transposed_note <= self.key_range_high):
            return False

        # Check voice key range
        if not self.current_voice.is_note_supported(transposed_note):
            return False

        # Send note-on to voice
        self.current_voice.note_on(transposed_note, velocity)
        return True

    def note_off(self, note: int, velocity: int = 64):
        """
        Handle note-off event.

        Args:
            note: MIDI note number (0-127)
            velocity: Note-off velocity (0-127)
        """
        if not self.current_voice:
            return

        # Apply channel transposition
        transposed_note = note + self.transpose

        # Send note-off to voice
        self.current_voice.note_off(transposed_note)

    def control_change(self, controller: int, value: int):
        """
        Handle control change event.

        Args:
            controller: Controller number (0-127)
            value: Controller value (0-127)
        """
        self.controllers[controller] = value

        # Handle special XG controllers
        if controller == 0:  # Bank Select MSB
            self.bank_msb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 32:  # Bank Select LSB
            self.bank_lsb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 7:  # Volume
            self.master_level = value / 127.0
        elif controller == 10:  # Pan
            self.pan = (value - 64) / 64.0  # Convert to -1.0 to 1.0
        elif controller == 84:  # Portamento Control
            # Handle portamento control if needed
            pass

        # Handle NRPN/RPN sequences
        elif controller == 98:  # NRPN LSB
            self.nrpn_lsb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return
        elif controller == 99:  # NRPN MSB
            self.nrpn_msb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return
        elif controller == 100:  # RPN LSB
            self.rpn_lsb = value
            self.rpn_active = True
            return
        elif controller == 101:  # RPN MSB
            self.rpn_msb = value
            self.rpn_active = True
            return
        elif controller == 6:  # Data Entry MSB
            if self.nrpn_active:
                if not self.data_msb_received:
                    self.data_msb = value
                    self.data_msb_received = True
                else:
                    # Complete NRPN message
                    self._handle_nrpn_complete(self.data_msb, value)
                    self.nrpn_active = False
                    self.data_msb_received = False
            elif self.rpn_active:
                self._handle_rpn_complete(value)
                self.rpn_active = False

    def _handle_nrpn_complete(self, msb: int, lsb: int):
        """
        Handle complete NRPN message.

        Args:
            msb: Data MSB
            lsb: Data LSB
        """
        # XG NRPN handling would go here
        # For now, this is a placeholder
        pass

    def _handle_rpn_complete(self, value: int):
        """
        Handle complete RPN message.

        Args:
            value: RPN value
        """
        if self.rpn_msb == 0 and self.rpn_lsb == 0:
            # Pitch Bend Range
            self.pitch_bend_range = value
        # Other RPN parameters can be handled here

    def pitch_bend(self, lsb: int, msb: int):
        """
        Handle pitch bend event.

        Args:
            lsb: Pitch bend LSB (0-127)
            msb: Pitch bend MSB (0-127)
        """
        self.pitch_bend_value = (msb << 7) | lsb

    def set_channel_pressure(self, pressure: int):
        """
        Handle channel pressure (aftertouch).

        Args:
            pressure: Pressure value (0-127)
        """
        self.channel_pressure = pressure

    def key_pressure(self, note: int, pressure: int):
        """
        Handle polyphonic key pressure.

        Args:
            note: MIDI note number (0-127)
            pressure: Pressure value (0-127)
        """
        self.key_pressure_values[note] = pressure

    def program_change(self, program: int):
        """
        Handle program change.

        Args:
            program: New program number (0-127)
        """
        self.load_program(program, self.bank_msb, self.bank_lsb)

    def all_notes_off(self):
        """Turn off all notes on this channel."""
        if self.current_voice:
            # This would need to be implemented in the Voice class
            # For now, we'll iterate through a reasonable note range
            for note in range(128):
                self.current_voice.note_off(note)

    def all_sound_off(self):
        """Immediately silence all sounds on this channel."""
        if self.current_voice:
            # Force all partials to stop immediately
            for note in range(128):
                self.current_voice.note_off(note)

    def reset_all_controllers(self):
        """Reset all controllers to default values."""
        self._initialize_default_controllers()
        self.channel_pressure = 0
        self.key_pressure_values.clear()
        self.pitch_bend_value = 8192

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this channel.

        Note: This is a simplified implementation. The voice architecture needs
        significant rework to properly handle polyphony. Currently it only
        supports monophonic playback per channel.

        Args:
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size * 2,)
        """
        if not self.current_voice or not self.current_voice.is_active():
            return np.zeros(block_size * 2, dtype=np.float32)

        # Collect modulation values from controllers
        modulation = self._collect_modulation_values()

        # For now, use a fixed note/velocity since the voice architecture
        # doesn't properly handle multiple simultaneous notes yet.
        # TODO: Implement proper polyphony with multiple active voices
        audio = self.current_voice.generate_samples(
            note=60,  # Fixed note - should be dynamic
            velocity=64,  # Fixed velocity - should be dynamic
            modulation=modulation,
            block_size=block_size
        )

        # Apply channel-level processing
        if self.muted:
            audio.fill(0.0)
        else:
            # Apply master level and pan
            audio *= self.master_level

            # Apply pan (simple implementation)
            if self.pan != 0.0:
                left_gain = 1.0 - max(0.0, self.pan)
                right_gain = 1.0 - max(0.0, -self.pan)
                audio[0::2] *= left_gain   # Left channel
                audio[1::2] *= right_gain  # Right channel

        return audio

    def _collect_modulation_values(self) -> Dict[str, float]:
        """
        Collect modulation values from controllers and channel state.

        Returns:
            Dictionary of modulation values
        """
        # Convert pitch bend to modulation value
        pitch_bend_semitones = ((self.pitch_bend_value - 8192) / 8192.0) * self.pitch_bend_range

        modulation = {
            'pitch': pitch_bend_semitones * 100.0,  # Convert to cents
            'filter_cutoff': 0.0,  # Could be mapped to controllers
            'amp': 1.0,
            'pan': self.pan,
            'velocity_crossfade': 0.0,
            'note_crossfade': 0.0,
            'stereo_width': 1.0,
            'tremolo_rate': 4.0,
            'tremolo_depth': 0.3,
            'mod_wheel': self.controllers[1] / 127.0,
            'breath_controller': self.controllers[2] / 127.0,
            'foot_controller': self.controllers[4] / 127.0,
            'expression': self.controllers[11] / 127.0,
            'brightness': self.controllers[72] / 127.0,
            'harmonic_content': self.controllers[71] / 127.0,
            'channel_aftertouch': self.channel_pressure / 127.0,
            'volume_cc': self.controllers[7] / 127.0,
        }

        return modulation

    def get_channel_info(self) -> Dict[str, Any]:
        """
        Get information about this channel.

        Returns:
            Dictionary with channel state information
        """
        return {
            'channel_number': self.channel_number,
            'program': self.program,
            'bank': self.bank,
            'bank_msb': self.bank_msb,
            'bank_lsb': self.bank_lsb,
            'active': self.active,
            'muted': self.muted,
            'solo': self.solo,
            'key_range': (self.key_range_low, self.key_range_high),
            'master_level': self.master_level,
            'pan': self.pan,
            'transpose': self.transpose,
            'has_voice': self.current_voice is not None,
            'voice_info': self.current_voice.get_voice_info() if self.current_voice else None
        }

    def set_key_range(self, low: int, high: int):
        """
        Set the key range for this channel.

        Args:
            low: Lowest note (0-127)
            high: Highest note (0-127)
        """
        self.key_range_low = max(0, min(127, low))
        self.key_range_high = max(0, min(127, high))

        if self.key_range_high < self.key_range_low:
            self.key_range_high = self.key_range_low

    def set_transpose(self, transpose: int):
        """
        Set channel transposition.

        Args:
            transpose: Transposition in semitones (-127 to 127)
        """
        self.transpose = max(-127, min(127, transpose))

    def mute(self, muted: bool = True):
        """
        Mute or unmute this channel.

        Args:
            muted: True to mute, False to unmute
        """
        self.muted = muted

    def set_solo(self, solo: bool = True):
        """
        Solo or unsolo this channel.

        Args:
            solo: True to solo, False to unsolo
        """
        self.solo = solo

    def is_active(self) -> bool:
        """
        Check if this channel is active (has notes playing).

        Returns:
            True if channel has active voices
        """
        return self.current_voice is not None and self.current_voice.is_active()

    @property
    def muted(self) -> bool:
        """Get mute state."""
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        """Set mute state."""
        self._muted = value

    @property
    def solo(self) -> bool:
        """Get solo state."""
        return self._solo

    @solo.setter
    def solo(self, value: bool):
        """Set solo state."""
        self._solo = value

    @property
    def channel_pressure(self) -> int:
        """Get channel pressure value."""
        return self._channel_pressure

    @channel_pressure.setter
    def channel_pressure(self, value: int):
        """Set channel pressure value."""
        self._channel_pressure = value
