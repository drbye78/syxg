"""
XG Effects MIDI Communication

This module handles NRPN and SysEx communication for XG effects,
including parameter changes and bulk data operations.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union

from .constants import (
    XG_EFFECT_NRPN_PARAMS, XG_CHANNEL_NRPN_PARAMS, YAMAHA_MANUFACTURER_ID,
    XG_PARAMETER_CHANGE, XG_BULK_PARAMETER_DUMP, XG_BULK_PARAMETER_REQUEST,
    XG_BULK_EFFECTS, XG_BULK_CHANNEL_EFFECTS
)
from .state import EffectStateManager


class XGCommunicationHandler:
    """
    Handles MIDI communication for XG effects including NRPN and SysEx messages.
    """

    def __init__(self, state_manager: EffectStateManager):
        """Initialize the communication handler"""
        self.state_manager = state_manager
        self.current_nrpn_channel = 0  # Current channel for NRPN
        self.nrpn_active = False
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.data_msb = 0

    def set_current_nrpn_channel(self, channel: int):
        """Set the current channel for NRPN operations"""
        if 0 <= channel < 16:  # NUM_CHANNELS
            self.current_nrpn_channel = channel

    def set_nrpn_msb(self, value: int):
        """Set MSB for NRPN"""
        self.nrpn_msb = value
        self.nrpn_active = True

    def set_nrpn_lsb(self, value: int):
        """Set LSB for NRPN"""
        self.nrpn_lsb = value
        self.nrpn_active = True

    def set_channel_effect_parameter(self, channel: int, nrpn_msb: int, nrpn_lsb: int, value: int):
        """
        Set a channel effect parameter via NRPN.

        Args:
            channel: MIDI channel
            nrpn_msb: NRPN MSB
            nrpn_lsb: NRPN LSB
            value: Parameter value (0-127)
        """
        nrpn = (nrpn_msb, nrpn_lsb)
        if nrpn not in XG_EFFECT_NRPN_PARAMS:
            return

        param_info = XG_EFFECT_NRPN_PARAMS[nrpn]
        real_value = param_info["transform"](value)

        # Update the temporary state
        self.state_manager.update_temp_state(param_info["target"], param_info["param"], real_value)

    def handle_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int,
                    channel: Optional[int] = None) -> bool:
        """
        Handle NRPN message for effects and XG parameters.

        Args:
            nrpn_msb: NRPN MSB
            nrpn_lsb: NRPN LSB
            data_msb: Data MSB
            data_lsb: Data LSB
            channel: MIDI channel (optional)

        Returns:
            True if the NRPN was handled, False otherwise
        """
        nrpn = (nrpn_msb, nrpn_lsb)
        data = (data_msb << 7) | data_lsb  # 14-bit value

        # Check if this is an XG channel parameter (MSB 1-15)
        if 1 <= nrpn_msb <= 15 and nrpn in XG_CHANNEL_NRPN_PARAMS:
            param_info = XG_CHANNEL_NRPN_PARAMS[nrpn]
            if channel is None:
                channel = self.current_nrpn_channel
            return self._handle_xg_channel_parameter(channel, param_info["param"], param_info["transform"](data))

        # Check if this is an XG effect parameter
        elif nrpn in XG_EFFECT_NRPN_PARAMS:
            param_info = XG_EFFECT_NRPN_PARAMS[nrpn]

            # Apply transformation
            real_value = param_info["transform"](data)

            # Update state
            if channel is None:
                channel = self.current_nrpn_channel

            self.state_manager.update_temp_state(param_info["target"], param_info["param"], real_value)
            return True

        return False

    def handle_sysex(self, manufacturer_id: List[int], data: List[int]) -> bool:
        """
        Handle SysEx message for effects.

        Args:
            manufacturer_id: Manufacturer ID
            data: SysEx data

        Returns:
            True if the SysEx was handled, False otherwise
        """
        # Check if this is a Yamaha SysEx
        if manufacturer_id != YAMAHA_MANUFACTURER_ID:
            return False

        # Process XG-specific SysEx messages
        if len(data) < 3:
            return False

        device_id = data[0]
        sub_status = data[1]
        command = data[2]

        # XG Parameter Change (F0 43 mm 04 0n pp vv F7)
        if sub_status == XG_PARAMETER_CHANGE:
            return self._handle_xg_parameter_change(data[3:])

        # XG Bulk Parameter Dump (F0 43 mm 7F 0n tt ... F7)
        elif sub_status == XG_BULK_PARAMETER_DUMP:
            return self._handle_xg_bulk_parameter_dump(data[3:])

        return False

    def _handle_xg_parameter_change(self, data: List[int]) -> bool:
        """Handle XG Parameter Change"""
        if len(data) < 3:
            return False

        # Extract parameter and value
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value = data[2]

        # Handle as NRPN
        return self.handle_nrpn(parameter_msb, parameter_lsb, value, 0)

    def _handle_xg_bulk_parameter_dump(self, data: List[int]) -> bool:
        """Handle XG Bulk Parameter Dump"""
        if len(data) < 2:
            return False

        # Check data type
        data_type = data[1]

        # System effects
        if data_type == XG_BULK_EFFECTS:
            return self._handle_bulk_effects(data[2:])
        # Channel-specific effects
        elif data_type == XG_BULK_CHANNEL_EFFECTS:
            return self._handle_bulk_channel_effects(data[2:])

        return False

    def _handle_bulk_effects(self, data: List[int]) -> bool:
        """Handle bulk data for system effects"""
        offset = 0
        while offset < len(data) - 1:
            # Extract parameter and value
            param_msb = data[offset]
            param_lsb = data[offset + 1]

            # Check if this is an effects NRPN
            if (param_msb, param_lsb) in XG_EFFECT_NRPN_PARAMS:
                # Extract 14-bit value
                if offset + 3 >= len(data):
                    break

                value = (data[offset + 2] << 7) | data[offset + 3]

                # Handle as NRPN
                self.handle_nrpn(param_msb, param_lsb, value >> 7, value & 0x7F)

                # Move to next parameter
                offset += 4
            else:
                # Skip unknown parameter
                offset += 1

        return True

    def _handle_bulk_channel_effects(self, data: List[int]) -> bool:
        """Handle bulk data for channel-specific effects"""
        offset = 0
        while offset < len(data) - 4:
            # Extract channel and parameter
            channel = data[offset]
            param_msb = data[offset + 1]
            param_lsb = data[offset + 2]

            # Check if this is a channel effects NRPN
            if (param_msb, param_lsb) in XG_EFFECT_NRPN_PARAMS:
                # Extract 14-bit value
                value = (data[offset + 3] << 7) | data[offset + 4]

                # Handle as NRPN for specific channel
                self.handle_nrpn(param_msb, param_lsb, value >> 7, value & 0x7F, channel)

                # Move to next parameter
                offset += 5
            else:
                # Skip unknown parameter
                offset += 1

        return True

    def get_bulk_dump(self, channel_specific: bool = False) -> List[int]:
        """
        Generate bulk dump of current effect parameters.

        Args:
            channel_specific: If True, generate channel-specific dump

        Returns:
            SysEx data for bulk dump
        """
        state = self.state_manager.get_current_state()

        if not channel_specific:
            # System effects bulk dump: F0 43 mm 7F 00 03 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_EFFECTS]

            # Add effect parameters
            for target, params in [("reverb", state["reverb_params"]),
                                  ("chorus", state["chorus_params"]),
                                  ("variation", state["variation_params"]),
                                  ("equalizer", state["equalizer_params"]),
                                  ("routing", state["routing_params"]),
                                  ("global", state["global_effect_params"])]:
                for param, value in params.items():
                    # Find corresponding NRPN
                    nrpn = self._find_nrpn_for_parameter(target, param)
                    if nrpn is None:
                        continue

                    # Convert to bulk value
                    data_value = self._convert_to_bulk_value(target, param, value)

                    # Add to dump
                    dump.append(nrpn[0])  # MSB
                    dump.append(nrpn[1])  # LSB
                    dump.append((data_value >> 7) & 0x7F)  # Data MSB
                    dump.append(data_value & 0x7F)  # Data LSB

            return dump
        else:
            # Channel effects bulk dump: F0 43 mm 7F 00 04 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_CHANNEL_EFFECTS]

            # Add parameters for each channel
            for channel in range(16):  # NUM_CHANNELS
                channel_params = state["channel_params"][channel]

                # Add insertion effect parameters
                insertion_effect = channel_params.get("insertion_effect", {})
                for param, value in insertion_effect.items():
                    nrpn = self._find_nrpn_for_parameter("insertion", param)
                    if nrpn is None:
                        continue

                    data_value = self._convert_to_bulk_value("insertion", param, value)
                    dump.append(channel)
                    dump.append(nrpn[0])
                    dump.append(nrpn[1])
                    dump.append((data_value >> 7) & 0x7F)
                    dump.append(data_value & 0x7F)

                # Add channel-specific parameters
                for param in ["reverb_send", "chorus_send", "variation_send",
                             "insertion_send", "muted", "soloed", "pan", "volume"]:
                    nrpn = self._find_nrpn_for_parameter("channel", param)
                    if nrpn is None:
                        continue

                    # Convert to bulk value
                    value = channel_params.get(param, 0.5)
                    if param == "muted" or param == "soloed":
                        data_value = 127 if value else 0
                    elif param == "pan":
                        data_value = int((value * 2 - 1) * 64 + 64)
                    else:
                        data_value = int(value * 127)

                    dump.append(channel)
                    dump.append(nrpn[0])
                    dump.append(nrpn[1])
                    dump.append((data_value >> 7) & 0x7F)
                    dump.append(data_value & 0x7F)

            return dump

    def _find_nrpn_for_parameter(self, target: str, param: str) -> Optional[Tuple[int, int]]:
        """Find NRPN for a given parameter"""
        for nrpn, info in XG_EFFECT_NRPN_PARAMS.items():
            if info["target"] == target and info["param"] == param:
                return nrpn
        return None

    def _convert_to_bulk_value(self, target: str, param: str, value: Union[float, bool, int]) -> int:
        """Convert parameter value to bulk dump format"""
        # Find NRPN for parameter
        nrpn = self._find_nrpn_for_parameter(target, param)
        if nrpn is None:
            return 0

        # Handle boolean values
        if isinstance(value, bool):
            return 127 if value else 0

        # Handle different parameter types
        if target == "reverb":
            if param == "type":
                return int(value)
            elif param == "time":
                return int((value - 0.1) / 0.05)
            elif param in ["level", "hf_damping", "density", "early_level", "tail_level"]:
                return int(value * 127)
            elif param == "pre_delay":
                return int(value / 0.1)

        elif target == "chorus":
            if param == "type":
                return int(value)
            elif param == "rate":
                return int((value - 0.1) / 0.05)
            elif param in ["depth", "feedback", "level", "output", "cross_feedback"]:
                return int(value * 127)
            elif param == "delay":
                return int(value / 0.1)

        elif target in ["variation", "insertion"]:
            if param == "type":
                return int(value)
            elif param.startswith("parameter") or param == "level":
                return int(value * 127)
            elif param == "bypass":
                return 127 if value else 0
            # Extended parameters for Phaser and Flanger
            elif param == "frequency":
                if target == "insertion":
                    return int(value / 0.2)
            elif param in ["depth", "feedback"]:
                if target == "insertion":
                    return int(value * 127)
            elif param == "lfo_waveform":
                if target == "insertion":
                    return int(value)

        elif target == "equalizer":
            if param in ["low_gain", "mid_gain", "high_gain"]:
                return int((value / 0.2) + 64)
            elif param == "mid_freq":
                return int((value - 100) / 40)
            elif param == "q_factor":
                return int((value - 0.5) / 0.04)

        elif target == "routing":
            if param in ["system_effect_order", "insertion_effect_order"]:
                # Bit representation for effect order
                if isinstance(value, list):
                    order_value = 0
                    for i, effect in enumerate(value):
                        order_value |= (effect << (i * 4))
                    return order_value
                else:
                    return int(value)
            elif param == "parallel_routing":
                return 127 if value else 0
            elif param in ["reverb_to_chorus", "chorus_to_variation"]:
                return int(value * 127)

        elif target in ["global", "channel"]:
            if param in ["reverb_send", "chorus_send", "variation_send", "insertion_send",
                        "stereo_width", "master_level"]:
                return int(value * 127)
            elif param in ["bypass_all", "muted", "soloed"]:
                return 127 if value else 0
            elif param == "pan":
                return int((value * 2 - 1) * 64 + 64)
            elif param == "volume":
                return int(value * 127)

        # Default scaling
        return int(value * 127)

    def create_sysex_message(self, data: List[int]) -> List[int]:
        """
        Create a complete SysEx message with manufacturer ID and data.

        Args:
            data: SysEx data (without F0, manufacturer ID, or F7)

        Returns:
            Complete SysEx message
        """
        return [0xF0] + YAMAHA_MANUFACTURER_ID + data + [0xF7]

    def parse_sysex_message(self, message: List[int]) -> Tuple[List[int], List[int]]:
        """
        Parse a SysEx message into manufacturer ID and data.

        Args:
            message: Complete SysEx message

        Returns:
            Tuple of (manufacturer_id, data)
        """
        if len(message) < 4 or message[0] != 0xF0 or message[-1] != 0xF7:
            return [], []

        manufacturer_id = message[1:4]  # Usually 3 bytes for Yamaha
        data = message[4:-1]

        return manufacturer_id, data

    def _handle_xg_channel_parameter(self, channel: int, param: str, value: Union[float, int, bool]) -> bool:
        """
        Handle XG channel-specific parameters.

        Args:
            channel: MIDI channel (0-15)
            param: Parameter name
            value: Parameter value

        Returns:
            True if the parameter was handled, False otherwise
        """
        if not (0 <= channel < 16):
            return False

        # Store the current NRPN channel for the state manager
        old_channel = self.current_nrpn_channel
        self.current_nrpn_channel = channel

        try:
            # Update the channel state in the state manager
            self.state_manager.update_temp_state("channel", param, value)
            return True
        except Exception:
            return False
        finally:
            # Restore the original channel
            self.current_nrpn_channel = old_channel

    def _handle_system_parameter(self, param: str, value: Union[float, int, bool]) -> bool:
        """
        Handle XG system parameters.

        Args:
            param: Parameter name
            value: Parameter value

        Returns:
            True if the parameter was handled, False otherwise
        """
        try:
            self.state_manager.update_temp_state("system", param, value)
            return True
        except Exception:
            return False
