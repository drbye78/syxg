"""
XG Synthesizer State Manager

Handles channel state management and RPN/NRPN parameter processing.
"""

from typing import List, Dict, Tuple, Optional, Any
from ..core.constants import DEFAULT_CONFIG, XG_CONSTANTS


class StateManager:
    """
    Manages MIDI channel states and RPN/NRPN parameter processing.

    Provides functionality for:
    - Channel state initialization and management
    - RPN/NRPN parameter handling
    - Controller state persistence
    - XG-specific state management
    """

    def __init__(self):
        """
        Initialize state manager.
        """
        self.num_channels = DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]

        # Channel states - one per MIDI channel
        self.channel_states: List[Dict[str, Any]] = [
            self._create_default_channel_state() for _ in range(self.num_channels)
        ]

        # RPN/NRPN states
        self.rpn_states: List[Dict[str, int]] = [
            {"msb": 127, "lsb": 127} for _ in range(self.num_channels)
        ]
        self.nrpn_states: List[Dict[str, int]] = [
            {"msb": 127, "lsb": 127} for _ in range(self.num_channels)
        ]
        self.data_entry_states: List[Dict[str, int]] = [
            {"msb": 0, "lsb": 0} for _ in range(self.num_channels)
        ]

    def _create_default_channel_state(self) -> Dict[str, Any]:
        """
        Create a default channel state.

        Returns:
            Dictionary containing default channel state
        """
        return {
            "program": 0,
            "bank": 0,
            "volume": 100,
            "expression": 127,
            "pan": 64,
            "mod_wheel": 0,
            "pitch_bend": 8192,
            "pitch_bend_range": DEFAULT_CONFIG["DEFAULT_PITCH_BEND_RANGE"],
            "sustain_pedal": False,
            "portamento": False,
            "portamento_time": 0,
            "reverb_send": DEFAULT_CONFIG["DEFAULT_REVERB_SEND"],
            "chorus_send": DEFAULT_CONFIG["DEFAULT_CHORUS_SEND"],
            "variation_send": DEFAULT_CONFIG["DEFAULT_VARIATION_SEND"],
            "key_pressure": {},
            "controllers": {i: 0 for i in range(128)},
            "rpn_msb": 127,
            "rpn_lsb": 127,
            "nrpn_msb": 127,
            "nrpn_lsb": 127,
            "drum_kit": 0,  # Current drum kit
            "drum_bank": 128,  # Default drum bank
            "channel_pressure": 0,  # Channel aftertouch
            # XG Part Parameters
            "element_reserve": 0,  # Element reserve (0-127)
            "element_assign_mode": 0,  # Element assign mode (0-127)
            "receive_channel": 0,  # Receive channel (0-15) - will be set per channel
            # XG RPN Parameters
            "fine_tuning": 0.0,  # Fine tuning (-1.0 to +1.0 representing -100 to +100 cents)
            "coarse_tuning": 0,  # Coarse tuning (-64 to +63 semitones)
            "tuning_program": 0,  # Tuning program (0-127)
            "tuning_bank": 0,  # Tuning bank (0-127)
            "modulation_depth": 64,  # Modulation depth (0-127 cents)
        }

    def get_channel_state(self, channel: int) -> Dict[str, Any]:
        """
        Get the current state of a MIDI channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Dictionary containing channel state

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].copy()

    def set_channel_state(self, channel: int, state: Dict[str, Any]):
        """
        Set the state of a MIDI channel.

        Args:
            channel: MIDI channel number (0-15)
            state: Dictionary containing channel state

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        # Update only the provided keys
        for key, value in state.items():
            if key in self.channel_states[channel]:
                self.channel_states[channel][key] = value

    def update_controller(self, channel: int, controller: int, value: int):
        """
        Update a controller value for a channel.

        Args:
            channel: MIDI channel number (0-15)
            controller: Controller number (0-127)
            value: Controller value (0-127)

        Raises:
            ValueError: If channel or controller is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= controller < 128):
            raise ValueError(f"Controller {controller} is out of range (0-127)")
        if not (0 <= value < 128):
            raise ValueError(f"Controller value {value} is out of range (0-127)")

        self.channel_states[channel]["controllers"][controller] = value

    def get_controller(self, channel: int, controller: int) -> int:
        """
        Get a controller value for a channel.

        Args:
            channel: MIDI channel number (0-15)
            controller: Controller number (0-127)

        Returns:
            Controller value (0-127)

        Raises:
            ValueError: If channel or controller is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= controller < 128):
            raise ValueError(f"Controller {controller} is out of range (0-127)")

        return self.channel_states[channel]["controllers"][controller]

    def set_program(self, channel: int, program: int):
        """
        Set program (preset) for a channel.

        Args:
            channel: MIDI channel number (0-15)
            program: Program number (0-127)

        Raises:
            ValueError: If channel or program is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= program < 128):
            raise ValueError(f"Program {program} is out of range (0-127)")

        self.channel_states[channel]["program"] = program

    def set_bank(self, channel: int, bank: int):
        """
        Set bank for a channel.

        Args:
            channel: MIDI channel number (0-15)
            bank: Bank number

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        self.channel_states[channel]["bank"] = bank

    def set_pitch_bend(self, channel: int, value: int):
        """
        Set pitch bend value for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: Pitch bend value (0-16383, center = 8192)

        Raises:
            ValueError: If channel or value is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 16384):
            raise ValueError(f"Pitch bend value {value} is out of range (0-16383)")

        self.channel_states[channel]["pitch_bend"] = value

    def get_pitch_bend_range(self, channel: int) -> float:
        """
        Get pitch bend range for a channel (RPN 0,0).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Pitch bend range in semitones (0.0-24.0)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("pitch_bend_range", DEFAULT_CONFIG["DEFAULT_PITCH_BEND_RANGE"])

    def get_fine_tuning(self, channel: int) -> float:
        """
        Get fine tuning for a channel (RPN 0,1).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Fine tuning in normalized cents (-1.0 to +1.0 representing -100 to +100 cents)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("fine_tuning", 0.0)

    def get_coarse_tuning(self, channel: int) -> int:
        """
        Get coarse tuning for a channel (RPN 0,2).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Coarse tuning in semitones (-64 to +63)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("coarse_tuning", 0)

    def get_tuning_program(self, channel: int) -> int:
        """
        Get tuning program for a channel (RPN 0,3).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Tuning program (0-127)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("tuning_program", 0)

    def get_tuning_bank(self, channel: int) -> int:
        """
        Get tuning bank for a channel (RPN 0,4).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Tuning bank (0-127)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("tuning_bank", 0)

    def get_modulation_depth(self, channel: int) -> int:
        """
        Get modulation depth for a channel (RPN 0,5).

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Modulation depth in cents (0-127)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return self.channel_states[channel].get("modulation_depth", 64)

    def set_channel_pressure(self, channel: int, pressure: int):
        """
        Set channel pressure (aftertouch) for a channel.

        Args:
            channel: MIDI channel number (0-15)
            pressure: Pressure value (0-127)

        Raises:
            ValueError: If channel or pressure is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= pressure < 128):
            raise ValueError(f"Pressure {pressure} is out of range (0-127)")

        self.channel_states[channel]["channel_pressure"] = pressure

    def set_element_reserve(self, channel: int, reserve: int):
        """
        Set element reserve for a channel (XG Part Parameter).

        Args:
            channel: MIDI channel number (0-15)
            reserve: Element reserve value (0-127)

        Raises:
            ValueError: If channel or reserve is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= reserve < 128):
            raise ValueError(f"Element reserve {reserve} is out of range (0-127)")

        self.channel_states[channel]["element_reserve"] = reserve

    def set_element_assign_mode(self, channel: int, mode: int):
        """
        Set element assign mode for a channel (XG Part Parameter).

        Args:
            channel: MIDI channel number (0-15)
            mode: Element assign mode value (0-127)

        Raises:
            ValueError: If channel or mode is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= mode < 128):
            raise ValueError(f"Element assign mode {mode} is out of range (0-127)")

        self.channel_states[channel]["element_assign_mode"] = mode

    def set_receive_channel(self, channel: int, receive_channel: int):
        """
        Set receive channel for a channel (XG Part Parameter).

        Args:
            channel: MIDI channel number (0-15)
            receive_channel: Receive channel value (0-15)

        Raises:
            ValueError: If channels are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= receive_channel < 16):
            raise ValueError(f"Receive channel {receive_channel} is out of range (0-15)")

        self.channel_states[channel]["receive_channel"] = receive_channel

    def set_key_pressure(self, channel: int, note: int, pressure: int):
        """
        Set key pressure (polyphonic aftertouch) for a note on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)
            pressure: Pressure value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")
        if not (0 <= pressure < 128):
            raise ValueError(f"Pressure {pressure} is out of range (0-127)")

        self.channel_states[channel]["key_pressure"][note] = pressure

    def get_key_pressure(self, channel: int, note: int) -> int:
        """
        Get key pressure for a note on a channel.

        Args:
            channel: MIDI channel number (0-15)
            note: MIDI note number (0-127)

        Returns:
            Pressure value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= note < 128):
            raise ValueError(f"Note {note} is out of range (0-127)")

        return self.channel_states[channel]["key_pressure"].get(note, 0)

    # RPN/NRPN handling
    def set_rpn_msb(self, channel: int, value: int):
        """
        Set RPN MSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: RPN MSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"RPN MSB {value} is out of range (0-127)")

        self.rpn_states[channel]["msb"] = value
        # Reset NRPN when RPN is set
        self.nrpn_states[channel]["msb"] = 127
        self.nrpn_states[channel]["lsb"] = 127

    def set_rpn_lsb(self, channel: int, value: int):
        """
        Set RPN LSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: RPN LSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"RPN LSB {value} is out of range (0-127)")

        self.rpn_states[channel]["lsb"] = value
        # Reset NRPN when RPN is set
        self.nrpn_states[channel]["msb"] = 127
        self.nrpn_states[channel]["lsb"] = 127

    def set_nrpn_msb(self, channel: int, value: int):
        """
        Set NRPN MSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: NRPN MSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"NRPN MSB {value} is out of range (0-127)")

        self.nrpn_states[channel]["msb"] = value
        # Reset RPN when NRPN is set
        self.rpn_states[channel]["msb"] = 127
        self.rpn_states[channel]["lsb"] = 127

    def set_nrpn_lsb(self, channel: int, value: int):
        """
        Set NRPN LSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: NRPN LSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"NRPN LSB {value} is out of range (0-127)")

        self.nrpn_states[channel]["lsb"] = value
        # Reset RPN when NRPN is set
        self.rpn_states[channel]["msb"] = 127
        self.rpn_states[channel]["lsb"] = 127

    def set_data_entry_msb(self, channel: int, value: int):
        """
        Set data entry MSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: Data entry MSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"Data entry MSB {value} is out of range (0-127)")

        self.data_entry_states[channel]["msb"] = value

    def set_data_entry_lsb(self, channel: int, value: int):
        """
        Set data entry LSB for a channel.

        Args:
            channel: MIDI channel number (0-15)
            value: Data entry LSB value (0-127)

        Raises:
            ValueError: If parameters are out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")
        if not (0 <= value < 128):
            raise ValueError(f"Data entry LSB {value} is out of range (0-127)")

        self.data_entry_states[channel]["lsb"] = value

    def get_current_rpn(self, channel: int) -> Tuple[int, int]:
        """
        Get current RPN for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Tuple of (RPN MSB, RPN LSB)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return (self.rpn_states[channel]["msb"], self.rpn_states[channel]["lsb"])

    def get_current_nrpn(self, channel: int) -> Tuple[int, int]:
        """
        Get current NRPN for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Tuple of (NRPN MSB, NRPN LSB)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return (self.nrpn_states[channel]["msb"], self.nrpn_states[channel]["lsb"])

    def get_current_data_entry(self, channel: int) -> Tuple[int, int]:
        """
        Get current data entry values for a channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Tuple of (Data Entry MSB, Data Entry LSB)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        return (self.data_entry_states[channel]["msb"], self.data_entry_states[channel]["lsb"])

    def reset_channel(self, channel: int):
        """
        Reset a channel to default state.

        Args:
            channel: MIDI channel number (0-15)

        Raises:
            ValueError: If channel is out of range
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        self.channel_states[channel] = self._create_default_channel_state()
        self.rpn_states[channel] = {"msb": 127, "lsb": 127}
        self.nrpn_states[channel] = {"msb": 127, "lsb": 127}
        self.data_entry_states[channel] = {"msb": 0, "lsb": 0}

    def reset_all_channels(self):
        """
        Reset all channels to default state.
        """
        for channel in range(self.num_channels):
            self.reset_channel(channel)

    def get_all_channel_states(self) -> List[Dict[str, Any]]:
        """
        Get states of all channels.

        Returns:
            List of channel state dictionaries
        """
        return [state.copy() for state in self.channel_states]

    def set_all_channel_states(self, states: List[Dict[str, Any]]):
        """
        Set states of all channels.

        Args:
            states: List of channel state dictionaries

        Raises:
            ValueError: If number of states doesn't match number of channels
        """
        if len(states) != self.num_channels:
            raise ValueError(f"Expected {self.num_channels} channel states, got {len(states)}")

        for channel in range(self.num_channels):
            self.channel_states[channel] = states[channel].copy()

    def initialize_xg_defaults(self):
        """
        Initialize all channels with XG standard defaults.
        """
        for channel in range(self.num_channels):
            # Set XG standard values
            self.channel_states[channel]["pitch_bend_range"] = DEFAULT_CONFIG["DEFAULT_PITCH_BEND_RANGE"]
            self.channel_states[channel]["reverb_send"] = DEFAULT_CONFIG["DEFAULT_REVERB_SEND"]
            self.channel_states[channel]["chorus_send"] = DEFAULT_CONFIG["DEFAULT_CHORUS_SEND"]
            self.channel_states[channel]["variation_send"] = DEFAULT_CONFIG["DEFAULT_VARIATION_SEND"]

            # Initialize standard controller values
            self.channel_states[channel]["controllers"][7] = 100   # Volume = 100
            self.channel_states[channel]["controllers"][10] = 64   # Pan = 64 (center)
            self.channel_states[channel]["controllers"][11] = 127  # Expression = 127
            self.channel_states[channel]["controllers"][91] = DEFAULT_CONFIG["DEFAULT_REVERB_SEND"]   # Reverb Send
            self.channel_states[channel]["controllers"][93] = DEFAULT_CONFIG["DEFAULT_CHORUS_SEND"]   # Chorus Send
            self.channel_states[channel]["controllers"][94] = DEFAULT_CONFIG["DEFAULT_VARIATION_SEND"]  # Variation Send

            # Reset RPN/NRPN states
            self.rpn_states[channel] = {"msb": 127, "lsb": 127}
            self.nrpn_states[channel] = {"msb": 127, "lsb": 127}
            self.data_entry_states[channel] = {"msb": 0, "lsb": 0}

            # Set drum mode for channel 9 (MIDI channel 10)
            if channel == 9:
                self.channel_states[channel]["bank"] = 128  # Drum bank
