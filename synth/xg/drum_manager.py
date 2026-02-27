"""
XG Synthesizer Drum Manager

Handles drum kit management and XG drum specifications.
"""
from __future__ import annotations

from typing import Any
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
        self.drum_parameters: list[dict[int, dict[str, Any]]] = [
            {} for _ in range(num_channels)
        ]

        # Current drum note for parameter setup (per channel)
        self.current_drum_notes: list[int | None] = [None] * num_channels

        # Drum kit information
        self.drum_kits: dict[int, str] = {}  # kit_number -> kit_name

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

    def get_drum_parameters_for_note(self, channel: int, note: int) -> dict[str, Any]:
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

    def get_current_drum_note(self, channel: int) -> int | None:
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

    def get_drum_instrument_name(self, note: int) -> str | None:
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

    def get_all_drum_notes_for_channel(self, channel: int) -> list[int]:
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

    def get_channel_drum_parameters(self, channel: int) -> dict[int, dict[str, Any]]:
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
        Handle XG drum setup NRPN messages with complete parameter support.

        Args:
            channel: MIDI channel number (0-15)
            nrpn_msb: NRPN MSB value
            nrpn_lsb: NRPN LSB value
            data_msb: Data entry MSB value
            data_lsb: Data entry LSB value

        Returns:
            True if the NRPN was handled, False otherwise
        """
        # 14-bit data value
        data = (data_msb << 7) | data_lsb

        # Get drum note from current setup channel state
        drum_note = self.current_drum_notes[channel]
        if drum_note is None:
            return False

        # XG Drum Parameters (MSB 40-41)
        if nrpn_msb in [40, 41]:
            # Process drum parameters based on NRPN LSB
            if nrpn_lsb == 0:  # Drum Note Pitch Coarse Tune
                # Range: -64 to +63 semitones
                tune_coarse = (data - 8192) / 128.0  # Convert to semitones
                self.set_drum_parameter(channel, drum_note, "pitch_coarse", tune_coarse)
                return True

            elif nrpn_lsb == 1:  # Drum Note Pitch Fine Tune
                # Range: -64 to +63 cents
                tune_fine = (data - 8192) / 128.0  # Convert to semitones
                self.set_drum_parameter(channel, drum_note, "pitch_fine", tune_fine)
                return True

            elif nrpn_lsb == 2:  # Drum Note Level
                # Range: 0-127 (0 = -inf dB, 127 = 0 dB)
                level = data / 16256.0  # Normalize to 0.0-1.0
                self.set_drum_parameter(channel, drum_note, "level", level)
                return True

            elif nrpn_lsb == 3:  # Drum Note Pan
                # Range: -64 to +63 (0 = center)
                pan = (data - 8192) / 8192.0  # Normalize to -1.0 to +1.0
                self.set_drum_parameter(channel, drum_note, "pan", pan)
                return True

            elif nrpn_lsb == 4:  # Drum Note Reverb Send
                # Range: 0-127
                reverb_send = data / 16256.0  # Normalize to 0.0-1.0
                self.set_drum_parameter(channel, drum_note, "reverb_send", reverb_send)
                return True

            elif nrpn_lsb == 5:  # Drum Note Chorus Send
                # Range: 0-127
                chorus_send = data / 16256.0  # Normalize to 0.0-1.0
                self.set_drum_parameter(channel, drum_note, "chorus_send", chorus_send)
                return True

            elif nrpn_lsb == 6:  # Drum Note Variation Send
                # Range: 0-127
                variation_send = data / 16256.0  # Normalize to 0.0-1.0
                self.set_drum_parameter(channel, drum_note, "variation_send", variation_send)
                return True

            elif nrpn_lsb == 7:  # Drum Note Filter Cutoff
                # Range: 0-127 (maps to frequency range)
                cutoff_freq = 20 + (data / 16256.0) * 19980  # 20Hz to 20kHz
                self.set_drum_parameter(channel, drum_note, "filter_cutoff", cutoff_freq)
                return True

            elif nrpn_lsb == 8:  # Drum Note Filter Resonance
                # Range: 0-127
                resonance = data / 16256.0  # Normalize to 0.0-1.0
                self.set_drum_parameter(channel, drum_note, "filter_resonance", resonance)
                return True

            elif nrpn_lsb == 9:  # Drum Note EG Attack
                # Range: 0-127 (time in seconds)
                attack_time = (data / 16256.0) * 10.0  # 0 to 10 seconds
                self.set_drum_parameter(channel, drum_note, "eg_attack", attack_time)
                return True

            elif nrpn_lsb == 10:  # Drum Note EG Decay 1
                # Range: 0-127 (time in seconds)
                decay1_time = (data / 16256.0) * 10.0  # 0 to 10 seconds
                self.set_drum_parameter(channel, drum_note, "eg_decay1", decay1_time)
                return True

            elif nrpn_lsb == 11:  # Drum Note EG Decay 2
                # Range: 0-127 (time in seconds)
                decay2_time = (data / 16256.0) * 10.0  # 0 to 10 seconds
                self.set_drum_parameter(channel, drum_note, "eg_decay2", decay2_time)
                return True

            elif nrpn_lsb == 12:  # Drum Note EG Release
                # Range: 0-127 (time in seconds)
                release_time = (data / 16256.0) * 10.0  # 0 to 10 seconds
                self.set_drum_parameter(channel, drum_note, "eg_release", release_time)
                return True

            elif nrpn_lsb == 13:  # Drum Note Wave Number
                # Range: 0-16383 (wave number selection)
                wave_number = data
                self.set_drum_parameter(channel, drum_note, "wave_number", wave_number)
                return True

            elif nrpn_lsb == 14:  # Drum Note Group Number
                # Range: 0-127 (group assignment)
                group_number = data // 128  # Convert to 0-127 range
                self.set_drum_parameter(channel, drum_note, "group_number", group_number)
                return True

            elif nrpn_lsb == 15:  # Drum Note Group Assign
                # Range: 0-127 (group assignment mode)
                group_assign = data // 128
                self.set_drum_parameter(channel, drum_note, "group_assign", group_assign)
                return True

            elif nrpn_lsb == 16:  # Drum Note Cutoff Offset
                # Range: -64 to +63
                cutoff_offset = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "cutoff_offset", cutoff_offset)
                return True

            elif nrpn_lsb == 17:  # Drum Note Resonance Offset
                # Range: -64 to +63
                resonance_offset = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "resonance_offset", resonance_offset)
                return True

            elif nrpn_lsb == 18:  # Drum Note EG Attack Offset
                # Range: -64 to +63
                attack_offset = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "attack_offset", attack_offset)
                return True

            elif nrpn_lsb == 19:  # Drum Note EG Decay Offset
                # Range: -64 to +63
                decay_offset = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "decay_offset", decay_offset)
                return True

            elif nrpn_lsb == 20:  # Drum Note EG Release Offset
                # Range: -64 to +63
                release_offset = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "release_offset", release_offset)
                return True

            elif nrpn_lsb == 21:  # Drum Note Velocity Pitch Sensitivity
                # Range: -64 to +63
                vel_pitch_sens = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "vel_pitch_sens", vel_pitch_sens)
                return True

            elif nrpn_lsb == 22:  # Drum Note Velocity Filter Sensitivity
                # Range: -64 to +63
                vel_filter_sens = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "vel_filter_sens", vel_filter_sens)
                return True

            elif nrpn_lsb == 23:  # Drum Note Velocity Amplitude Sensitivity
                # Range: -64 to +63
                vel_amp_sens = (data - 8192) / 128.0
                self.set_drum_parameter(channel, drum_note, "vel_amp_sens", vel_amp_sens)
                return True

            elif nrpn_lsb == 24:  # Drum Note Key Assign
                # Range: 0-127 (MIDI note number)
                key_assign = data // 128
                self.set_drum_parameter(channel, drum_note, "key_assign", key_assign)
                return True

            elif nrpn_lsb == 25:  # Drum Note Key Note On Assign
                # Range: 0-127 (MIDI note number)
                key_on_assign = data // 128
                self.set_drum_parameter(channel, drum_note, "key_on_assign", key_on_assign)
                return True

            elif nrpn_lsb == 26:  # Drum Note Key Note Off Assign
                # Range: 0-127 (MIDI note number)
                key_off_assign = data // 128
                self.set_drum_parameter(channel, drum_note, "key_off_assign", key_off_assign)
                return True

        # Drum Kit Selection (MSB 99, LSB 0)
        elif nrpn_msb == 99 and nrpn_lsb == 0:
            # Drum kit selection (0-127)
            kit_number = data // 128
            self.set_drum_kit_for_channel(channel, kit_number)
            return True

        return False

    def set_drum_kit_for_channel(self, channel: int, kit_number: int):
        """
        Set drum kit for a specific channel.

        Args:
            channel: MIDI channel number (0-15)
            kit_number: Drum kit number (0-127)
        """
        if not (0 <= channel < self.num_channels):
            raise ValueError(f"Channel {channel} is out of range (0-{self.num_channels-1})")

        # XG Drum Kit Names
        xg_drum_kits = {
            0: "Standard Kit 1", 1: "Standard Kit 2", 8: "Room Kit", 16: "Power Kit",
            24: "Electronic Kit", 25: "Analog Kit", 32: "Jazz Kit", 40: "Brush Kit",
            48: "Orchestra Kit", 56: "SFX Kit 1", 57: "SFX Kit 2"
        }

        kit_name = xg_drum_kits.get(kit_number, f"Custom Kit {kit_number}")
        self.drum_kits[channel] = kit_name

        # Initialize kit-specific parameters
        self.initialize_drum_kit_parameters(channel, kit_number)

    def handle_xg_drum_parameter(self, address: int, value: int) -> bool:
        """
        Handle XG drum parameter from SysEx messages.

        Args:
            address: XG parameter address
            value: Parameter value

        Returns:
            True if handled successfully
        """
        # Extract channel and note from address
        # Address format: 0x30 XX YY where XX is note, YY is parameter
        if (address & 0xFF0000) == 0x300000:
            note = (address >> 8) & 0xFF
            parameter = address & 0xFF

            # Map parameter to drum parameter name
            param_map = {
                0: "pitch_coarse", 1: "pitch_fine", 2: "level", 3: "pan",
                4: "reverb_send", 5: "chorus_send", 6: "variation_send",
                7: "filter_cutoff", 8: "filter_resonance", 9: "eg_attack",
                10: "eg_decay1", 11: "eg_decay2", 12: "eg_release"
            }

            if parameter in param_map:
                # Use channel 9 (drum channel) for drum parameters
                drum_channel = 9
                param_name = param_map[parameter]

                # Convert value based on parameter type
                if param_name in ["pan"]:
                    converted_value = (value - 64) / 64.0  # -1.0 to 1.0
                elif param_name in ["level", "reverb_send", "chorus_send", "variation_send"]:
                    converted_value = value / 127.0  # 0.0 to 1.0
                elif param_name in ["pitch_coarse", "pitch_fine"]:
                    converted_value = (value - 64) / 64.0  # -1.0 to 1.0
                elif param_name == "filter_cutoff":
                    converted_value = 20 + (value / 127.0) * 19980  # 20Hz to 20kHz
                elif param_name == "filter_resonance":
                    converted_value = value / 127.0  # 0.0 to 1.0
                else:  # EG parameters
                    converted_value = (value / 127.0) * 10.0  # 0 to 10 seconds

                self.set_drum_parameter(drum_channel, note, param_name, converted_value)
                return True

        return False

    def process_bulk_dump(self, address: int, data: list) -> bool:
        """
        Process bulk dump data for drum parameters.
        
        Args:
            address: Starting XG parameter address
            data: List of 7-bit parameter values
            
        Returns:
            True if processed successfully
        """
        try:
            # Process bulk dump data according to XG specification
            # Address format: 0x30 XX YY where XX is note, YY is parameter
            
            # For drum parameters, address is the base address
            base_address = address
            
            # Process each data value
            for i, value in enumerate(data):
                # Calculate actual address for this parameter
                param_address = base_address + i
                
                # Handle the parameter
                self.handle_xg_drum_parameter(param_address, value)
                
            return True
        except Exception as e:
            print(f"Error processing drum bulk dump: {e}")
            return False

    def get_bulk_parameter(self, address: int) -> int:
        """
        Get a drum parameter value by XG address for bulk dump generation.
        
        Args:
            address: XG parameter address
            
        Returns:
            7-bit parameter value
        """
        try:
            # Extract note and parameter from address
            # Address format: 0x30 XX YY where XX is note, YY is parameter
            if (address & 0xFF0000) == 0x300000:
                note = (address >> 8) & 0xFF
                parameter = address & 0xFF

                # Map parameter to drum parameter name
                param_map = {
                    0: "pitch_coarse", 1: "pitch_fine", 2: "level", 3: "pan",
                    4: "reverb_send", 5: "chorus_send", 6: "variation_send",
                    7: "filter_cutoff", 8: "filter_resonance", 9: "eg_attack",
                    10: "eg_decay1", 11: "eg_decay2", 12: "eg_release"
                }

                if parameter in param_map:
                    # Use channel 9 (drum channel) for drum parameters
                    drum_channel = 9
                    param_name = param_map[parameter]
                    
                    # Get current parameter value
                    current_value = self.get_drum_parameter(drum_channel, note, param_name)
                    
                    if current_value is not None:
                        # Convert value back to 7-bit MIDI value based on parameter type
                        if param_name in ["pan"]:
                            # -1.0 to 1.0 -> 0 to 127
                            midi_value = int((current_value + 1.0) * 64)
                        elif param_name in ["level", "reverb_send", "chorus_send", "variation_send"]:
                            # 0.0 to 1.0 -> 0 to 127
                            midi_value = int(current_value * 127)
                        elif param_name in ["pitch_coarse", "pitch_fine"]:
                            # -1.0 to 1.0 -> 0 to 127
                            midi_value = int((current_value + 1.0) * 64)
                        elif param_name == "filter_cutoff":
                            # 20Hz to 20kHz -> 0 to 127
                            midi_value = int(((current_value - 20) / 19980) * 127)
                        elif param_name == "filter_resonance":
                            # 0.0 to 1.0 -> 0 to 127
                            midi_value = int(current_value * 127)
                        else:  # EG parameters
                            # 0 to 10 seconds -> 0 to 127
                            midi_value = int((current_value / 10.0) * 127)
                        
                        # Ensure value is in valid 7-bit range
                        return max(0, min(127, midi_value))
            
            # Return default value if parameter not found
            return 0
        except Exception as e:
            print(f"Error getting drum bulk parameter: {e}")
            return 0

    def reset_to_xg_defaults(self):
        """
        Reset all drum parameters to XG standard defaults.
        """
        for channel in range(self.num_channels):
            self.reset_channel_drum_parameters(channel)
            # Set default drum kit
            self.set_drum_kit_for_channel(channel, 0)

    def get_drum_kit_info(self, channel: int) -> str | None:
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
