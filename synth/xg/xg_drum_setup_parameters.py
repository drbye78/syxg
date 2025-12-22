"""
XG Drum Setup Parameters (NRPN MSB 48-63)

Implements XG drum kit editing and individual drum voice parameters.
Handles NRPN MSB 48-63 for complete XG drum architecture compliance.

XG Specification Compliance:
- MSB 48-63: Drum setup parameters (kit selection, voice parameters)
- Individual drum note parameters (pitch, level, decay, etc.)
- Drum kit voice reserve and allocation
- Real-time drum editing during playback

Copyright (c) 2025
"""

from typing import Dict, List, Optional, Any, Tuple
import threading


class XGDrumSetupParameters:
    """
    XG Drum Setup Parameters (NRPN MSB 48-63)

    Handles XG drum kit editing and individual drum voice parameters
    for complete XG drum architecture compliance.

    Key Features:
    - Complete XG drum kit editing (MSB 48-63)
    - Individual drum note parameters
    - Drum kit voice reserve management
    - Real-time drum editing during playback
    - Thread-safe operation for live performance
    """

    # XG Drum Kit Parameters (MSB 48 LSB 0-127)
    XG_DRUM_KIT_PARAMETERS = {
        0x00: {'name': 'Drum Kit Select', 'range': (0, 127), 'default': 0},
        0x01: {'name': 'Drum Level', 'range': (0, 127), 'default': 100},
        0x02: {'name': 'Drum Pan', 'range': (0, 127), 'default': 64},
        0x03: {'name': 'Drum Reverb Send', 'range': (0, 127), 'default': 40},
        0x04: {'name': 'Drum Chorus Send', 'range': (0, 127), 'default': 0},
        0x05: {'name': 'Drum Variation Send', 'range': (0, 127), 'default': 0},
        0x06: {'name': 'Drum Pitch Offset', 'range': (0, 127), 'default': 64},
        0x07: {'name': 'Drum Decay Offset', 'range': (0, 127), 'default': 64},
        0x08: {'name': 'Drum Velocity Curve', 'range': (0, 4), 'default': 0},
        # Extended parameters for XG compliance
        0x10: {'name': 'Drum Filter Cutoff', 'range': (0, 127), 'default': 64},
        0x11: {'name': 'Drum Filter Resonance', 'range': (0, 127), 'default': 64},
        0x12: {'name': 'Drum Attack Time', 'range': (0, 127), 'default': 64},
        0x13: {'name': 'Drum Release Time', 'range': (0, 127), 'default': 64},
        0x14: {'name': 'Drum LFO Rate', 'range': (0, 127), 'default': 64},
        0x15: {'name': 'Drum LFO Depth', 'range': (0, 127), 'default': 0},
        0x16: {'name': 'Drum EQ Low Gain', 'range': (0, 127), 'default': 64},
        0x17: {'name': 'Drum EQ Mid Gain', 'range': (0, 127), 'default': 64},
        0x18: {'name': 'Drum EQ High Gain', 'range': (0, 127), 'default': 64},
    }

    # XG Drum Note Parameters (per drum in kit)
    XG_DRUM_NOTE_PARAMETERS = {
        'pitch_coarse': {'range': (0, 127), 'default': 64, 'description': 'Coarse pitch tuning'},
        'pitch_fine': {'range': (0, 127), 'default': 64, 'description': 'Fine pitch tuning'},
        'level': {'range': (0, 127), 'default': 100, 'description': 'Drum level'},
        'pan': {'range': (0, 127), 'default': 64, 'description': 'Stereo panning'},
        'reverb_send': {'range': (0, 127), 'default': 40, 'description': 'Reverb send level'},
        'chorus_send': {'range': (0, 127), 'default': 0, 'description': 'Chorus send level'},
        'variation_send': {'range': (0, 127), 'default': 0, 'description': 'Variation send level'},
        'decay_time': {'range': (0, 127), 'default': 64, 'description': 'Decay time'},
        'attack_time': {'range': (0, 127), 'default': 64, 'description': 'Attack time'},
        'filter_cutoff': {'range': (0, 127), 'default': 64, 'description': 'Filter cutoff frequency'},
        'filter_resonance': {'range': (0, 127), 'default': 64, 'description': 'Filter resonance'},
        'lfo_rate': {'range': (0, 127), 'default': 64, 'description': 'LFO rate'},
        'lfo_depth': {'range': (0, 127), 'default': 0, 'description': 'LFO depth'},
        'eq_low': {'range': (0, 127), 'default': 64, 'description': 'EQ low frequency gain'},
        'eq_mid': {'range': (0, 127), 'default': 64, 'description': 'EQ mid frequency gain'},
        'eq_high': {'range': (0, 127), 'default': 64, 'description': 'EQ high frequency gain'},
    }

    # Standard XG Drum Kits
    XG_DRUM_KITS = {
        0: 'Standard Kit 1', 1: 'Standard Kit 2', 8: 'Room Kit',
        16: 'Power Kit', 24: 'Electronic Kit', 25: 'Analog Kit', 26: 'Dance Kit',
        32: 'Jazz Kit', 40: 'Brush Kit', 48: 'Orchestra Kit', 56: 'SFX Kit 1',
        127: 'Custom Kit'
    }

    def __init__(self, num_channels: int = 16):
        """
        Initialize XG Drum Setup Parameters.

        Args:
            num_channels: Number of MIDI channels (default 16)
        """
        self.num_channels = num_channels
        self.lock = threading.RLock()

        # Current drum kit selections per channel
        self.drum_kit_selections = [0] * num_channels  # Default to Standard Kit 1

        # Drum kit parameters: channel -> kit_number -> param_name -> value
        self.drum_kit_parameters = {}

        # Individual drum note parameters: channel -> kit_number -> note -> param_name -> value
        self.drum_note_parameters = {}

        # Initialize default parameters
        self._initialize_default_parameters()

        # Parameter change callback
        self.parameter_change_callback = None

        print("🥁 XG DRUM SETUP PARAMETERS: Initialized")
        print(f"   {num_channels} channels configured for XG drum editing")
        print(f"   {len(self.XG_DRUM_KIT_PARAMETERS)} drum kit parameters available")
        print(f"   {len(self.XG_DRUM_NOTE_PARAMETERS)} parameters per drum note")

    def _initialize_default_parameters(self):
        """Initialize default XG drum parameters."""
        for channel in range(self.num_channels):
            # Initialize kit parameters for kit 0 (Standard Kit 1)
            self.drum_kit_parameters[channel] = {0: {}}
            for param_lsb, param_info in self.XG_DRUM_KIT_PARAMETERS.items():
                self.drum_kit_parameters[channel][0][param_lsb] = param_info['default']

            # Initialize drum note parameters for all 128 notes in kit 0
            self.drum_note_parameters[channel] = {0: {}}
            for note in range(128):
                self.drum_note_parameters[channel][0][note] = {}
                for param_name, param_info in self.XG_DRUM_NOTE_PARAMETERS.items():
                    self.drum_note_parameters[channel][0][note][param_name] = param_info['default']

    def handle_nrpn_msb48_to63(self, channel: int, msb: int, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 48-63 (Drum Setup) messages.

        Args:
            channel: MIDI channel (0-15, drum channels typically 9/10)
            msb: NRPN MSB value (48-63)
            lsb: NRPN LSB value (0-127)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (48 <= msb <= 63):
                return False
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= lsb <= 127):
                return False

            # Convert 14-bit value to 7-bit for most parameters
            value_7bit = data_value >> 7

            # Get current kit for this channel
            current_kit = self.drum_kit_selections[channel]

            # Ensure kit exists
            if current_kit not in self.drum_kit_parameters.get(channel, {}):
                self._initialize_kit(channel, current_kit)

            # Handle different MSB ranges
            if msb == 48:
                # MSB 48: Drum Kit Parameters
                return self._handle_drum_kit_parameter(channel, current_kit, lsb, value_7bit)
            elif 49 <= msb <= 63:
                # MSB 49-63: Individual Drum Note Parameters
                drum_note = lsb  # LSB = drum note (0-127)
                param_index = msb - 49  # Map MSB to parameter index
                return self._handle_drum_note_parameter(channel, current_kit, drum_note, param_index, value_7bit)

        return False

    def _handle_drum_kit_parameter(self, channel: int, kit: int, lsb: int, value: int) -> bool:
        """Handle drum kit parameter changes."""
        if lsb in self.XG_DRUM_KIT_PARAMETERS:
            # Validate range
            param_info = self.XG_DRUM_KIT_PARAMETERS[lsb]
            min_val, max_val = param_info['range']
            value = max(min_val, min(max_val, value))

            self.drum_kit_parameters[channel][kit][lsb] = value
            self._notify_parameter_change(f'drum_kit_ch{channel}_kit{kit}_param{lsb}', value)
            return True
        return False

    def _handle_drum_note_parameter(self, channel: int, kit: int, note: int, param_index: int, value: int) -> bool:
        """Handle individual drum note parameter changes."""
        # Map parameter index to parameter name
        param_names = list(self.XG_DRUM_NOTE_PARAMETERS.keys())
        if 0 <= param_index < len(param_names):
            param_name = param_names[param_index]
            param_info = self.XG_DRUM_NOTE_PARAMETERS[param_name]

            # Validate range
            min_val, max_val = param_info['range']
            value = max(min_val, min(max_val, value))

            self.drum_note_parameters[channel][kit][note][param_name] = value
            self._notify_parameter_change(f'drum_note_ch{channel}_kit{kit}_note{note}_{param_name}', value)
            return True
        return False

    def _notify_parameter_change(self, parameter_name: str, value: Any):
        """Notify parameter change callback."""
        if self.parameter_change_callback:
            self.parameter_change_callback(parameter_name, value)

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback

    def set_drum_kit(self, channel: int, kit_number: int) -> bool:
        """
        Set the active drum kit for a channel.

        Args:
            channel: MIDI channel (0-15)
            kit_number: Drum kit number (0-127)

        Returns:
            True if kit was set successfully
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= kit_number <= 127):
                return False

            # Initialize kit if it doesn't exist
            if kit_number not in self.drum_kit_parameters.get(channel, {}):
                self._initialize_kit(channel, kit_number)

            self.drum_kit_selections[channel] = kit_number
            self._notify_parameter_change(f'drum_kit_selection_ch{channel}', kit_number)
            return True

    def _initialize_kit(self, channel: int, kit_number: int):
        """Initialize a drum kit with default parameters."""
        if channel not in self.drum_kit_parameters:
            self.drum_kit_parameters[channel] = {}
        if channel not in self.drum_note_parameters:
            self.drum_note_parameters[channel] = {}

        # Initialize kit parameters
        self.drum_kit_parameters[channel][kit_number] = {}
        for param_lsb, param_info in self.XG_DRUM_KIT_PARAMETERS.items():
            self.drum_kit_parameters[channel][kit_number][param_lsb] = param_info['default']

        # Initialize drum note parameters
        self.drum_note_parameters[channel][kit_number] = {}
        for note in range(128):
            self.drum_note_parameters[channel][kit_number][note] = {}
            for param_name, param_info in self.XG_DRUM_NOTE_PARAMETERS.items():
                self.drum_note_parameters[channel][kit_number][note][param_name] = param_info['default']

    def get_drum_kit_parameter(self, channel: int, kit: int, param_lsb: int) -> Optional[int]:
        """
        Get a drum kit parameter value.

        Args:
            channel: MIDI channel
            kit: Drum kit number
            param_lsb: Parameter LSB (0-127)

        Returns:
            Parameter value or None if not found
        """
        with self.lock:
            try:
                return self.drum_kit_parameters[channel][kit][param_lsb]
            except KeyError:
                return None

    def get_drum_note_parameter(self, channel: int, kit: int, note: int, param_name: str) -> Optional[int]:
        """
        Get a drum note parameter value.

        Args:
            channel: MIDI channel
            kit: Drum kit number
            note: Drum note (0-127)
            param_name: Parameter name

        Returns:
            Parameter value or None if not found
        """
        with self.lock:
            try:
                return self.drum_note_parameters[channel][kit][note][param_name]
            except KeyError:
                return None

    def set_drum_kit_parameter(self, channel: int, kit: int, param_lsb: int, value: int) -> bool:
        """
        Set a drum kit parameter value.

        Args:
            channel: MIDI channel
            kit: Drum kit number
            param_lsb: Parameter LSB
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if param_lsb not in self.XG_DRUM_KIT_PARAMETERS:
                return False

            param_info = self.XG_DRUM_KIT_PARAMETERS[param_lsb]
            min_val, max_val = param_info['range']
            value = max(min_val, min(max_val, value))

            if kit not in self.drum_kit_parameters.get(channel, {}):
                self._initialize_kit(channel, kit)

            self.drum_kit_parameters[channel][kit][param_lsb] = value
            self._notify_parameter_change(f'drum_kit_ch{channel}_kit{kit}_param{param_lsb}', value)
            return True

    def set_drum_note_parameter(self, channel: int, kit: int, note: int, param_name: str, value: int) -> bool:
        """
        Set a drum note parameter value.

        Args:
            channel: MIDI channel
            kit: Drum kit number
            note: Drum note (0-127)
            param_name: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if param_name not in self.XG_DRUM_NOTE_PARAMETERS:
                return False

            param_info = self.XG_DRUM_NOTE_PARAMETERS[param_name]
            min_val, max_val = param_info['range']
            value = max(min_val, min(max_val, value))

            if kit not in self.drum_note_parameters.get(channel, {}):
                self._initialize_kit(channel, kit)

            self.drum_note_parameters[channel][kit][note][param_name] = value
            self._notify_parameter_change(f'drum_note_ch{channel}_kit{kit}_note{note}_{param_name}', value)
            return True

    def get_drum_kit_info(self, channel: int) -> Dict[str, Any]:
        """
        Get information about the current drum kit for a channel.

        Args:
            channel: MIDI channel

        Returns:
            Drum kit information dictionary
        """
        with self.lock:
            current_kit = self.drum_kit_selections[channel]
            kit_name = self.XG_DRUM_KITS.get(current_kit, f'Custom Kit {current_kit}')

            return {
                'channel': channel,
                'current_kit': current_kit,
                'kit_name': kit_name,
                'parameters': self.drum_kit_parameters.get(channel, {}).get(current_kit, {}),
                'available_kits': self.XG_DRUM_KITS
            }

    def get_drum_note_info(self, channel: int, note: int) -> Dict[str, Any]:
        """
        Get information about a specific drum note in the current kit.

        Args:
            channel: MIDI channel
            note: Drum note (0-127)

        Returns:
            Drum note information dictionary
        """
        with self.lock:
            current_kit = self.drum_kit_selections[channel]

            return {
                'channel': channel,
                'kit': current_kit,
                'note': note,
                'parameters': self.drum_note_parameters.get(channel, {}).get(current_kit, {}).get(note, {}),
                'parameter_info': self.XG_DRUM_NOTE_PARAMETERS
            }

    def get_all_drum_kits(self) -> Dict[int, str]:
        """
        Get all available XG drum kits.

        Returns:
            Dictionary mapping kit numbers to names
        """
        return self.XG_DRUM_KITS.copy()

    def reset_channel_to_defaults(self, channel: int):
        """Reset a channel's drum parameters to XG defaults."""
        with self.lock:
            if 0 <= channel < self.num_channels:
                self.drum_kit_selections[channel] = 0
                self.drum_kit_parameters[channel] = {}
                self.drum_note_parameters[channel] = {}
                self._initialize_default_parameters()
                print(f"🥁 XG DRUM: Reset channel {channel} to XG defaults")

    def reset_all_channels_to_defaults(self):
        """Reset all channels to XG drum defaults."""
        with self.lock:
            for channel in range(self.num_channels):
                self.reset_channel_to_defaults(channel)
            print("🥁 XG DRUM: Reset all channels to XG defaults")

    def export_drum_setup(self, channel: int) -> Dict[str, Any]:
        """Export drum setup for a channel."""
        with self.lock:
            return {
                'channel': channel,
                'current_kit': self.drum_kit_selections[channel],
                'kit_parameters': self.drum_kit_parameters.get(channel, {}),
                'note_parameters': self.drum_note_parameters.get(channel, {}),
                'version': '1.0'
            }

    def import_drum_setup(self, channel: int, setup_data: Dict[str, Any]) -> bool:
        """Import drum setup for a channel."""
        try:
            with self.lock:
                if 'current_kit' in setup_data:
                    self.drum_kit_selections[channel] = setup_data['current_kit']
                if 'kit_parameters' in setup_data:
                    self.drum_kit_parameters[channel] = setup_data['kit_parameters']
                if 'note_parameters' in setup_data:
                    self.drum_note_parameters[channel] = setup_data['note_parameters']
                return True
        except Exception as e:
            print(f"❌ XG DRUM: Import failed - {e}")
            return False

    def get_drum_setup_status(self) -> Dict[str, Any]:
        """Get comprehensive drum setup status."""
        with self.lock:
            channels_with_drums = []
            total_kit_parameters = 0
            total_note_parameters = 0

            for channel in range(self.num_channels):
                current_kit = self.drum_kit_selections[channel]
                if current_kit in self.drum_kit_parameters.get(channel, {}):
                    channels_with_drums.append(channel)
                    total_kit_parameters += len(self.drum_kit_parameters[channel][current_kit])
                    if current_kit in self.drum_note_parameters.get(channel, {}):
                        total_note_parameters += len(self.drum_note_parameters[channel][current_kit])

            return {
                'total_channels': self.num_channels,
                'channels_with_drums': channels_with_drums,
                'total_kit_parameters': total_kit_parameters,
                'total_note_parameters': total_note_parameters,
                'available_kit_parameters': len(self.XG_DRUM_KIT_PARAMETERS),
                'available_note_parameters': len(self.XG_DRUM_NOTE_PARAMETERS),
                'available_kits': len(self.XG_DRUM_KITS)
            }

    def __str__(self) -> str:
        """String representation of XG drum setup."""
        status = self.get_drum_setup_status()
        return (f"XGDrumSetupParameters(channels={status['total_channels']}, "
                f"drum_channels={len(status['channels_with_drums'])}, "
                f"kit_params={status['total_kit_parameters']}, "
                f"note_params={status['total_note_parameters']})")

    def __repr__(self) -> str:
        return self.__str__()
