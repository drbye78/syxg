"""
XG Synthesizer Drum Manager

Handles drum kit management and XG drum specifications.
"""

from typing import List, Dict, Tuple, Optional, Any
from ..core.constants import XG_CONSTANTS, DEFAULT_DRUM_KIT_NOTES, DEFAULT_DRUM_PARAMETERS


class DrumManager:
    """
    Manages drum parameters and XG drum specifications.

    Provides functionality for:
    - Drum parameter storage and retrieval
    - XG drum kit management
    - Drum note mapping and processing
    - Drum-specific XG parameter handling
    """

    def __init__(self, num_channels: int = 16):
        """
        Initialize drum manager.

        Args:
            num_channels: Number of MIDI channels to manage
        """
        self.num_channels = num_channels

        # Drum parameters for each channel - dict[note] -> dict[param_name] -> value
        self.drum_parameters: List[Dict[int, Dict[str, Any]]] = [
            {} for _ in range(num_channels)
        ]

        # Current drum note for parameter setup (per channel)
        self.current_drum_notes: List[Optional[int]] = [None] * num_channels

        # Drum kit information
        self.drum_kits: Dict[int, str] = {}  # kit_number -> kit_name

        # Initialize default drum parameters
        self._initialize_default_drum_parameters()

    def _initialize_default_drum_parameters(self):
        """
        Initialize default drum parameters for all channels.
        """
        for channel in range(self.num_channels):
            for note in DEFAULT_DRUM_KIT_NOTES:
                if note not in self.drum_parameters[channel]:
                    self.drum_parameters[channel][note] = DEFAULT_DRUM_PARAMETERS.copy()

    def set_drum_parameter(self, channel: int, note: int, parameter: str, value: Any):
        """
        Set a drum parameter for a specific note on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)
            parameter: Parameter name (e.g., "tune", "level", "pan")
            value: Parameter value

        Raises:
            ValueError: If channel or note is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")

        if note not in self.drum_parameters[channel]:
            self.drum_parameters[channel][note] = {}

        self.drum_parameters[channel][note][parameter] = value

    def get_drum_parameter(self, channel: int, note: int, parameter: str) -> Any:
        """
        Get a drum parameter for a specific note on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)
            parameter: Parameter name

        Returns:
            Parameter value or None if not found

        Raises:
            ValueError: If channel or note is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")

        if note in self.drum_parameters[channel]:
            return self.drum_parameters[channel][note].get(parameter)
        return None

    def get_drum_parameters_for_note(self, channel: int, note: int) -> Dict[str, Any]:
        """
        Get all drum parameters for a specific note on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)

        Returns:
            Dictionary of all parameters for the note

        Raises:
            ValueError: If channel or note is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")

        return self.drum_parameters[channel].get(note, {}).copy()

    def set_current_drum_note(self, channel: int, note: int):
        """
        Set the current drum note for parameter setup on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)

        Raises:
            ValueError: If channel or note is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")

        self.current_drum_notes[channel] = note

    def get_current_drum_note(self, channel: int) -> Optional[int]:
        """
        Get the current drum note for parameter setup on a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Current drum note or None

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.current_drum_notes[channel]

    def initialize_drum_kit_parameters(self, channel: int, kit_number: int = 0):
        """
        Initialize default drum kit parameters for a channel.

        Args:
            channel: MIDI channel number (0-15)
            kit_number: Drum kit number

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        # Clear existing parameters
        self.drum_parameters[channel] = {}

        # Initialize with default parameters for common drum notes
        for note in DEFAULT_DRUM_KIT_NOTES:
            self.drum_parameters[channel][note] = DEFAULT_DRUM_PARAMETERS.copy()

    def reset_channel_drum_parameters(self, channel: int):
        """
        Reset drum parameters for a channel to defaults.

        Args:
            channel: MIDI channel number (0-15)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        self.drum_parameters[channel] = {}
        self.current_drum_notes[channel] = None
        self._initialize_default_drum_parameters()

    def reset_all_drum_parameters(self):
        """
        Reset drum parameters for all channels to defaults.
        """
        for channel in range(self.num_channels):
            self.reset_channel_drum_parameters(channel)

    def get_drum_instrument_name(self, note: int) -> Optional[str]:
        """
        Get the XG drum instrument name for a MIDI note.

        Args:
            note: MIDI note number (0-127)

        Returns:
            Drum instrument name or None if not found
        """
        return XG_CONSTANTS["XG_DRUM_MAP"].get(note)

    def is_drum_note(self, note: int) -> bool:
        """
        Check if a MIDI note is a standard drum note.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if the note is a standard drum note
        """
        return note in XG_CONSTANTS["XG_DRUM_MAP"]

    def get_all_drum_notes_for_channel(self, channel: int) -> List[int]:
        """
        Get all drum notes that have parameters set for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            List of MIDI note numbers

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return list(self.drum_parameters[channel].keys())

    def get_channel_drum_parameters(self, channel: int) -> Dict[int, Dict[str, Any]]:
        """
        Get all drum parameters for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Dictionary mapping note -> parameters

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return {note: params.copy() for note, params in self.drum_parameters[channel].items()}

    def copy_drum_parameters(self, source_channel: int, dest_channel: int):
        """
        Copy drum parameters from one channel to another.

        Args:
            source_channel: Source MIDI channel number (0-15)
            dest_channel: Destination MIDI channel number (0-15)

        Raises:
            ValueError: If channels are out of range
        """
        if not (0 <= source_channel < self.num_channels):
            raise ValueError(f"Source channel {source_channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= dest_channel < self.num_channels):
            raise ValueError(f"Destination channel {dest_channel} is out of range (0-{self.num_channels-1})")

        self.drum_parameters[dest_channel] = {
            note: params.copy() for note, params in self.drum_parameters[source_channel].items()
        }
        self.current_drum_notes[dest_channel] = self.current_drum_notes[source_channel]

    def handle_xg_drum_setup_nrpn(self, channel: int, nrpn_msb: int, nrpn_lsb: int,
                                 data_msb: int, data_lsb: int) -> bool:
        """
        Handle XG drum setup NRPN messages.

        Args:
            channel: MIDI channel number (0-15)
            nrpn_msb: NRPN MSB value
            nrpn_lsb: NRPN LSB value
            data_msb: Data entry MSB value
            data_lsb: Data entry LSB value

        Returns:
            True if the NRPN was handled, False otherwise
        """
        if channel != XG_CONSTANTS["DRUM_SETUP_CHANNEL"]:
            return False

        # 14-bit data value
        data = (data_msb << 7) | data_lsb

        # Get drum note from current setup channel state
        drum_note = self.current_drum_notes[channel]
        if drum_note is None:
            return False

        # Process various drum parameters based on NRPN LSB
        if nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_TUNE"]:
            # Drum pitch tuning (-64..+63 semitones)
            tune = (data - 8192) / 100.0  # Convert to semitones
            self.set_drum_parameter(channel, drum_note, "tune", tune)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_LEVEL"]:
            # Drum level (0..127)
            level = data / 127.0
            self.set_drum_parameter(channel, drum_note, "level", level)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_PAN"]:
            # Drum panning (-64..+63)
            pan = (data - 8192) / 8192.0
            self.set_drum_parameter(channel, drum_note, "pan", pan)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_REVERB"]:
            # Drum reverb send (0..127)
            reverb = data / 127.0
            self.set_drum_parameter(channel, drum_note, "reverb_send", reverb)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_CHORUS"]:
            # Drum chorus send (0..127)
            chorus = data / 127.0
            self.set_drum_parameter(channel, drum_note, "chorus_send", chorus)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_VARIATION"]:
            # Drum variation send (0..127)
            variation = data / 127.0
            self.set_drum_parameter(channel, drum_note, "variation_send", variation)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_KEY_ASSIGN"]:
            # Drum key assignment (0..127)
            key_assign = data
            self.set_drum_parameter(channel, drum_note, "key_assign", key_assign)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_FILTER_CUTOFF"]:
            # Drum filter cutoff frequency (0..127)
            cutoff = 20 + data * 150  # 20Hz to 19020Hz
            self.set_drum_parameter(channel, drum_note, "filter_cutoff", cutoff)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_FILTER_RESONANCE"]:
            # Drum filter resonance (0..127)
            resonance = data / 64.0
            self.set_drum_parameter(channel, drum_note, "filter_resonance", resonance)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_EG_ATTACK"]:
            # Drum envelope attack (0..127)
            attack = data * 0.05  # 0 to 6.35 seconds
            self.set_drum_parameter(channel, drum_note, "eg_attack", attack)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_EG_DECAY"]:
            # Drum envelope decay (0..127)
            decay = data * 0.05  # 0 to 6.35 seconds
            self.set_drum_parameter(channel, drum_note, "eg_decay", decay)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_EG_RELEASE"]:
            # Drum envelope release (0..127)
            release = data * 0.05  # 0 to 6.35 seconds
            self.set_drum_parameter(channel, drum_note, "eg_release", release)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_PITCH_COARSE"]:
            # Drum pitch coarse tuning (-64..+63 semitones)
            pitch_coarse = (data - 8192) / 100.0
            self.set_drum_parameter(channel, drum_note, "pitch_coarse", pitch_coarse)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_NOTE_PITCH_FINE"]:
            # Drum pitch fine tuning (-64..+63 cents)
            pitch_fine = (data - 8192) * 0.5
            self.set_drum_parameter(channel, drum_note, "pitch_fine", pitch_fine)
            return True

        elif nrpn_lsb == XG_CONSTANTS["DRUM_KIT_SELECT_LSB"]:
            # Drum kit selection
            kit = data
            # This would typically affect all drum channels
            # For now, we'll just store it
            self.drum_kits[channel] = f"Kit_{kit}"
            return True

        return False

    def get_drum_kit_info(self, channel: int) -> Optional[str]:
        """
        Get drum kit information for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Drum kit name or None

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.drum_kits.get(channel)

    def set_drum_kit_info(self, channel: int, kit_name: str):
        """
        Set drum kit information for a channel.

        Args:
            channel: MIDI channel number (0-15)
            kit_name: Name of the drum kit

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        self.drum_kits[channel] = kit_name
