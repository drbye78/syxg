"""
XG Effects MIDI Communication

This module handles NRPN and SysEx communication for XG effects,
including parameter changes and bulk data operations.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union

from .constants import (
    XG_EFFECT_NRPN_PARAMS, XG_CHANNEL_NRPN_PARAMS, YAMAHA_MANUFACTURER_ID,
    XG_PARAMETER_CHANGE, XG_BULK_PARAMETER_DUMP, XG_BULK_PARAMETER_REQUEST,
    XG_BULK_EFFECTS, XG_BULK_CHANNEL_EFFECTS, XG_MODEL_ID_QUERY,
    XG_SYSTEM_RESET, XG_REGISTRATION_CHANGE, XG_BULK_MASTER_PARAMS,
    XG_BULK_DRUM_PARAMS, XG_BULK_SCENE_PARAMS
)

# Import voice parameters for Phase 4 support
try:
    from .constants import XG_VOICE_NRPN_PARAMS
except ImportError:
    XG_VOICE_NRPN_PARAMS = {}  # Fall back if not available
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
        self.device_id = 0x10  # Default device ID (hex 10 = decimal 16)

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
        # Handle Universal SysEx first (not Yamaha-specific)
        if len(data) >= 3 and data[0] == 0x7E and data[2] == XG_MODEL_ID_QUERY:
            return self.handle_universal_model_id_query(data)

        # Check if this is a Yamaha SysEx
        if manufacturer_id != YAMAHA_MANUFACTURER_ID:
            return False

        # Process XG-specific SysEx messages
        if len(data) < 3:
            return False

        device_id = data[0]
        sub_status = data[1]
        command = data[2]

        # XG System Reset (F0 43 1n 4C 00 00 7E 00 F7)
        if sub_status == XG_SYSTEM_RESET and command == 0x00:
            return self._handle_xg_system_reset(data[3:])

        # XG Registration Change (F0 43 1n 4C 08 ss F7)
        elif sub_status == XG_REGISTRATION_CHANGE:
            return self._handle_xg_registration_change(data[3:])

        # XG Bulk Parameter Request (F0 43 mm 7E 0n tt ... F7)
        elif sub_status == XG_BULK_PARAMETER_REQUEST:
            return self._handle_xg_bulk_parameter_request(data[3:])

        # XG Parameter Change (F0 43 mm 04 0n pp vv F7)
        elif sub_status == XG_PARAMETER_CHANGE:
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

        # Master parameters (XG_BULK_MASTER_PARAMS = 0x00)
        if data_type == XG_BULK_MASTER_PARAMS:
            return self._handle_bulk_master_params(data[2:])
        # System effects (XG_BULK_EFFECTS = 0x03)
        elif data_type == XG_BULK_EFFECTS:
            return self._handle_bulk_effects(data[2:])
        # Channel-specific effects (XG_BULK_CHANNEL_EFFECTS = 0x04)
        elif data_type == XG_BULK_CHANNEL_EFFECTS:
            return self._handle_bulk_channel_effects(data[2:])
        # Drum parameters (XG_BULK_DRUM_PARAMS = 0x40)
        elif data_type == XG_BULK_DRUM_PARAMS:
            return self._handle_bulk_drum_params(data[2:])
        # Scene/registration parameters (XG_BULK_SCENE_PARAMS = 0x09)
        elif data_type == XG_BULK_SCENE_PARAMS:
            return self._handle_bulk_scene_params(data[2:])

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

    def handle_universal_model_id_query(self, data: List[int]) -> bool:
        """
        Handle universal model ID query (F0 7E cc 06 01 F7).

        This responds with the XG model ID reply to identify this device
        as an XG-compatible synthesizer.

        Args:
            data: SysEx data containing the query

        Returns:
            True if query was handled, False otherwise
        """
        try:
            # XG Model ID Reply: F0 43 cc 4C 00 00 7E 00 F7
            # Format: F0 43 [device_id] 4C 00 00 7E 00 F7

            # Extract requesting device ID from query (if present)
            device_id = self.device_id  # Use our configured device ID

            # Create XG model ID reply
            reply_data = [device_id, 0x4C, 0x00, 0x00, 0x7E, 0x00]
            reply_message = self.create_sysex_message(reply_data)

            # In a real implementation, this would be sent back to the requester
            # For now, we just acknowledge that we handled the query
            print(f"XG Model ID Query handled - responding with device ID {device_id}")

            return True

        except Exception as e:
            print(f"Error handling XG model ID query: {e}")
            return False

    def _handle_xg_system_reset(self, data: List[int]) -> bool:
        """
        Handle XG system reset (F0 43 1n 4C 00 00 7E 00 F7).

        This resets all XG parameters to their factory defaults and
        restores XG-compatible initial state.

        Args:
            data: Additional SysEx data

        Returns:
            True if reset was handled successfully
        """
        try:
            # Reset all XG parameters to defaults
            self.state_manager.reset_effects()

            # Reset NRPN state
            self.current_nrpn_channel = 0
            self.nrpn_active = False
            self.nrpn_msb = 0
            self.nrpn_lsb = 0
            self.data_msb = 0

            print("XG System Reset: All parameters restored to XG defaults")
            return True

        except Exception as e:
            print(f"Error handling XG system reset: {e}")
            return False

    def _handle_xg_registration_change(self, data: List[int]) -> bool:
        """
        Handle XG registration/scene change (F0 43 1n 4C 08 ss F7).

        This changes to a different XG registration/scene number.

        Args:
            data: SysEx data containing scene number

        Returns:
            True if scene change was handled
        """
        try:
            if len(data) < 1:
                return False

            scene_number = data[0]  # Scene number (0-63)

            # Validate scene number (0-63 for XG)
            if not (0 <= scene_number <= 63):
                return False

            # Note: Actual scene management would require XGSceneManager
            # For now, we acknowledge the scene change request
            print(f"XG Registration Change: Scene {scene_number} requested")

            # In a complete implementation, this would:
            # - Load scene from XG scene manager
            # - Apply all scene parameters
            # - Update synthesizer state
            # - Send confirmation response

            return True

        except Exception as e:
            print(f"Error handling XG registration change: {e}")
            return False

    def _handle_xg_bulk_parameter_request(self, data: List[int]) -> bool:
        """
        Handle XG bulk parameter request (F0 43 mm 7E 0n tt ... F7).

        This requests a bulk dump of XG parameters from another device.

        Args:
            data: SysEx data containing request details

        Returns:
            True if request was handled
        """
        try:
            if len(data) < 2:
                return False

            requested_device_id = data[0]
            data_type = data[1]  # Type of data requested

            # Check if request is for our device
            if requested_device_id != self.device_id:
                return False  # Not for us

            # Generate appropriate bulk dump based on data type
            if data_type == XG_BULK_EFFECTS:
                # Request for system effects data
                bulk_data = self.get_bulk_dump(channel_specific=False)
                print(f"XG Bulk Request: System effects dump generated ({len(bulk_data)} bytes)")

            elif data_type == XG_BULK_CHANNEL_EFFECTS:
                # Request for channel effects data
                bulk_data = self.get_bulk_dump(channel_specific=True)
                print(f"XG Bulk Request: Channel effects dump generated ({len(bulk_data)} bytes)")

            else:
                print(f"XG Bulk Request: Unknown data type {data_type}")
                return False

            # In a complete implementation, bulk_data would be sent as a SysEx message
            # For now, we acknowledge the request was processed
            return True

        except Exception as e:
            print(f"Error handling XG bulk parameter request: {e}")
            return False

    def get_bulk_dump_by_type(self, dump_type: str = "effects") -> List[int]:
        """
        Generate bulk dump of XG parameters by type.

        Args:
            dump_type: Type of dump - "master", "effects", "channel", "drum", "scene"

        Returns:
            SysEx data for bulk dump
        """
        state = self.state_manager.get_current_state()

        if dump_type == "master":
            # XG Master Parameter Dump: F0 43 mm 7F 00 00 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_MASTER_PARAMS]

            # Add master system parameters (MSB 0, LSB 0-127 range)
            master_params = [
                (0, 0, state.get("system", {}).get("master_tune", 0.0)),
                (0, 1, state.get("system", {}).get("master_volume", 1.0)),
                (0, 2, state.get("system", {}).get("master_tune_fine", 0.0)),
                (0, 3, state.get("system", {}).get("transpose", 0)),
                (0, 5, state.get("system", {}).get("system_reset", False)),
            ]

            for msb, lsb, value in master_params:
                data_value = self._convert_to_bulk_value_for_nrpn(msb, lsb, value)
                dump.append(msb)  # NRPN MSB
                dump.append(lsb)  # NRPN LSB
                dump.append((data_value >> 7) & 0x7F)  # Data MSB
                dump.append(data_value & 0x7F)  # Data LSB

            return dump

        elif dump_type == "effects":
            # System effects bulk dump: F0 43 mm 7F 00 03 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_EFFECTS]

            # Add effect parameters
            for target, params in [("reverb", state.get("reverb_params", {})),
                                  ("chorus", state.get("chorus_params", {})),
                                  ("variation", state.get("variation_params", {})),
                                  ("equalizer", state.get("equalizer_params", {})),
                                  ("routing", state.get("routing_params", {})),
                                  ("global", state.get("global_effect_params", {}))]:
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

        elif dump_type == "channel":
            # Channel effects bulk dump: F0 43 mm 7F 00 04 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_CHANNEL_EFFECTS]

            # Add parameters for each channel
            for channel in range(16):  # NUM_CHANNELS
                channel_params = state.get("channel_params", [{}] * 16)[channel]

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

        elif dump_type == "drum":
            # XG Drum Parameter Dump: F0 43 mm 7F 40 xx [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_DRUM_PARAMS, 0x00]  # xx=0x00 for current drum kit

            # Add drum kit parameters (simplified for now)
            # In a full implementation, this would include parameters for each drum note
            drum_params = [
                (41, 0, 0.0),   # Decay/Release Offset
                (41, 1, 1.0),   # Velocity Level Sensitivity
                (41, 2, 1),     # Alternate Sample Selection
                (41, 3, 0.5),   # Random Pitch Modulation
                (41, 4, True),  # Sample Layering Control
            ]

            for msb, lsb, value in drum_params:
                data_value = self._convert_to_bulk_value_for_nrpn(msb, lsb, value)
                dump.append(msb)
                dump.append(lsb)
                dump.append((data_value >> 7) & 0x7F)
                dump.append(data_value & 0x7F)

            return dump

        elif dump_type == "scene":
            # XG Scene Parameter Dump: F0 43 mm 7F 00 09 [data] F7
            dump = [0x43, 0x7F, 0x00, XG_BULK_SCENE_PARAMS, 0, 0]  # scene/bank

            # Add current scene parameters (simplified)
            # In a full implementation, this would save complete scene state
            scene_params = [
                (0, 120, 0),    # Reverb Type
                (0, 130, 1),    # Chorus Type
                (0, 140, 0),    # Variation Type
                (0, 1, 1.0),    # Master Volume
            ]

            for msb, lsb, value in scene_params:
                data_value = self._convert_to_bulk_value_for_nrpn(msb, lsb, value)
                dump.append(msb)
                dump.append(lsb)
                dump.append((data_value >> 7) & 0x7F)
                dump.append(data_value & 0x7F)

            return dump

        else:
            # Default to effects dump
            return self.get_bulk_dump_by_type("effects")

    def _convert_to_bulk_value_for_nrpn(self, msb: int, lsb: int, value: Union[float, bool, int]) -> int:
        """Convert parameter value to bulk dump format for specific NRPN"""
        nrpn = (msb, lsb)

        # Check NRPN mappings
        if nrpn in XG_EFFECT_NRPN_PARAMS:
            param_info = XG_EFFECT_NRPN_PARAMS[nrpn]
            return self._convert_to_bulk_value(param_info["target"], param_info["param"], value)

        elif 1 <= msb <= 15 and nrpn in XG_CHANNEL_NRPN_PARAMS:
            param_info = XG_CHANNEL_NRPN_PARAMS[nrpn]
            return self._convert_to_bulk_value(param_info["target"], param_info["param"], value)

        # Default scaling for generic parameters
        if isinstance(value, bool):
            return 127 if value else 0
        elif isinstance(value, float):
            return int(value * 127)
        else:
            return int(value)

    def _handle_bulk_master_params(self, data: List[int]) -> bool:
        """Handle bulk data for master system parameters"""
        print(f"Handle bulk master parameters: {len(data)} bytes")
        offset = 0

        while offset < len(data) - 3:
            msb = data[offset]
            lsb = data[offset + 1]
            data_msb = data[offset + 2]
            data_lsb = data[offset + 3]

            value = (data_msb << 7) | data_lsb

            # Handle master parameters
            nrpn = (msb, lsb)
            if nrpn in XG_EFFECT_NRPN_PARAMS:
                param_info = XG_EFFECT_NRPN_PARAMS[nrpn]
                real_value = param_info["transform"](value)
                self.state_manager.update_temp_state(param_info["target"], param_info["param"], real_value)

            offset += 4

        return True

    # ============================================================================
    # XG VOICE PARAMETER EXTENSIONS - PHASE A COMPLETION
    # Implements NRPN MSB 127 voice synthesis parameter routing
    # ============================================================================

    def handle_voice_nrpn(self, msb: int, lsb: int, data_msb: int, data_lsb: int,
                         channel: int = None) -> bool:
        """Handle XG Voice Parameters (MSB 127) NRPN messages.

        Args:
            msb: NRPN MSB (should be 127 for voice parameters)
            lsb: NRPN LSB (0-31 for voice parameters)
            data_msb: Data MSB (14-bit value high 7 bits)
            data_lsb: Data LSB (14-bit value low 7 bits)
            channel: MIDI channel (0-15)

        Returns:
            True if parameter was handled
        """
        if msb != 127:
            return False  # Not a voice parameter

        # Combine to 14-bit value
        data_value = (data_msb << 7) | data_lsb

        # Handle voice parameter based on LSB
        if lsb == 0:  # Element Switch
            element_switch_value = data_value & 0xFF  # 8-bit bitfield
            self._route_voice_element_switch(channel, element_switch_value)
        elif lsb == 1:  # Velocity Limit High
            velocity_high = min(127, data_value >> 7)  # MSB
            self._route_voice_velocity_limit_high(channel, velocity_high)
        elif lsb == 2:  # Velocity Limit Low
            velocity_low = min(127, data_value >> 7)
            self._route_voice_velocity_limit_low(channel, velocity_low)
        elif lsb == 3:  # Note Limit High
            note_high = min(127, data_value >> 7)
            self._route_voice_note_limit_high(channel, note_high)
        elif lsb == 4:  # Note Limit Low
            note_low = min(127, data_value >> 7)
            self._route_voice_note_limit_low(channel, note_low)
        elif lsb == 5:  # Note Shift
            shift_semitones = (data_value >> 7) - 64  # -64 to +63
            self._route_voice_note_shift(channel, shift_semitones)
        elif lsb == 6:  # Detune
            detune_cents = ((data_value >> 7) - 64) * 100 / 16  # XG formula
            self._route_voice_detune(channel, detune_cents)
        elif lsb == 7:  # Velocity Sensitivity
            vel_sens = data_value >> 7
            self._route_voice_velocity_sensitivity(channel, vel_sens)
        elif lsb == 8:  # Volume
            volume = (data_value >> 7) / 127.0
            self._route_voice_volume(channel, volume)
        elif lsb == 9:  # Velocity Rate Sensitivity
            rate_sens = ((data_value >> 7) - 64) / 32.0
            self._route_voice_velocity_rate_sens(channel, rate_sens)
        elif lsb == 10:  # Pan
            pan_pos = ((data_value >> 7) - 64) / 64.0
            self._route_voice_pan(channel, pan_pos)
        elif lsb == 11:  # Assign Mode
            assign_mode = data_value >> 7
            self._route_voice_assign_mode(channel, assign_mode)
        elif lsb == 12:  # Fine Tuning
            fine_tune = ((data_value >> 7) - 64) / 8192.0
            self._route_voice_fine_tuning(channel, fine_tune)
        elif lsb == 13:  # Coarse Tuning
            coarse_tune = (data_value >> 7) - 64
            self._route_voice_coarse_tuning(channel, coarse_tune)
        elif lsb == 14:  # Pitch Random
            random_range = (data_value >> 7) / 100.0  # 0-1.27 semitones
            self._route_voice_pitch_random(channel, random_range)
        elif lsb == 15:  # Pitch Scale Tuning
            scale_tune = (data_value >> 7) - 64
            self._route_voice_scale_tuning(channel, scale_tune)
        elif lsb == 16:  # Pitch Scale Sensitivity
            scale_sens = (data_value >> 7) - 64
            self._route_voice_scale_sensitivity(channel, scale_sens)
        elif lsb == 17:  # Delay Mode
            delay_mode = data_value >> 7
            self._route_voice_delay_mode(channel, delay_mode)
        elif lsb == 18:  # Delay Time
            delay_time = data_value  # 14-bit sample count
            self._route_voice_delay_time(channel, delay_time)
        elif lsb == 19:  # Delay Feedback
            delay_feedback = (data_value >> 7) / 127.0
            self._route_voice_delay_feedback(channel, delay_feedback)
        else:
            return False  # Invalid LSB for voice parameters

        return True

    # Voice parameter routing methods (would interface with voice management)
    def _route_voice_element_switch(self, channel: int, value: int):
        """Route element switch to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_element_switch(channel, value)

    def _route_voice_velocity_limit_high(self, channel: int, value: int):
        """Route velocity high limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_limit_high(channel, value)

    def _route_voice_velocity_limit_low(self, channel: int, value: int):
        """Route velocity low limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_limit_low(channel, value)

    def _route_voice_note_limit_high(self, channel: int, value: int):
        """Route note high limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_limit_high(channel, value)

    def _route_voice_note_limit_low(self, channel: int, value: int):
        """Route note low limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_limit_low(channel, value)

    def _route_voice_note_shift(self, channel: int, value: int):
        """Route note shift to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_shift(channel, value)

    def _route_voice_detune(self, channel: int, value: float):
        """Route detune to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_detune(channel, value)

    def _route_voice_velocity_sensitivity(self, channel: int, value: int):
        """Route velocity sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_sensitivity(channel, value)

    def _route_voice_volume(self, channel: int, value: float):
        """Route voice volume to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_volume(channel, value)

    def _route_voice_velocity_rate_sens(self, channel: int, value: float):
        """Route velocity rate sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_rate_sens(channel, value)

    def _route_voice_pan(self, channel: int, value: float):
        """Route voice pan to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_pan(channel, value)

    def _route_voice_assign_mode(self, channel: int, value: int):
        """Route assign mode to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_assign_mode(channel, value)

    def _route_voice_fine_tuning(self, channel: int, value: float):
        """Route fine tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_fine_tuning(channel, value)

    def _route_voice_coarse_tuning(self, channel: int, value: int):
        """Route coarse tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_coarse_tuning(channel, value)

    def _route_voice_pitch_random(self, channel: int, value: float):
        """Route pitch random to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_pitch_random(channel, value)

    def _route_voice_scale_tuning(self, channel: int, value: int):
        """Route scale tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_scale_tuning(channel, value)

    def _route_voice_scale_sensitivity(self, channel: int, value: int):
        """Route scale sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_scale_sensitivity(channel, value)

    def _route_voice_delay_mode(self, channel: int, value: int):
        """Route delay mode to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_mode(channel, value)

    def _route_voice_delay_time(self, channel: int, value: int):
        """Route delay time to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_time(channel, value)

    def _route_voice_delay_feedback(self, channel: int, value: float):
        """Route delay feedback to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_feedback(channel, value)

    def _handle_bulk_drum_params(self, data: List[int]) -> bool:
        """Handle bulk data for drum setup parameters"""
        if len(data) < 1:
            return False

        drum_kit = data[0]  # Drum kit number
        print(f"Handle bulk drum parameters for kit {drum_kit}: {len(data)-1} parameter bytes")

        offset = 1  # Skip drum kit byte

        while offset < len(data) - 3:
            msb = data[offset]
            lsb = data[offset + 1]
            data_msb = data[offset + 2]
            data_lsb = data[offset + 3]

            value = (data_msb << 7) | data_lsb

            # Handle drum parameters (MSB 41 for advanced drum params)
            nrpn = (msb, lsb)
            if nrpn in XG_EFFECT_NRPN_PARAMS:
                param_info = XG_EFFECT_NRPN_PARAMS[nrpn]
                real_value = param_info["transform"](value)
                self.state_manager.update_temp_state(param_info["target"], param_info["param"], real_value)

            offset += 4

        return True

    def _handle_bulk_scene_params(self, data: List[int]) -> bool:
        """Handle bulk data for scene/registration parameters"""
        if len(data) < 2:
            return False

        scene_number = data[0]
        bank_number = data[1]
        print(f"Handle bulk scene parameters: Scene {scene_number}, Bank {bank_number}, {len(data)-2} parameter bytes")

        offset = 2  # Skip scene/bank bytes

        while offset < len(data) - 3:
            msb = data[offset]
            lsb = data[offset + 1]
            data_msb = data[offset + 2]
            data_lsb = data[offset + 3]

            value = (data_msb << 7) | data_lsb

            # Handle scene parameters
            nrpn = (msb, lsb)
            if nrpn in XG_EFFECT_NRPN_PARAMS:
                param_info = XG_EFFECT_NRPN_PARAMS[nrpn]
                real_value = param_info["transform"](value)
                self.state_manager.update_temp_state(param_info["target"], param_info["param"], real_value)

            offset += 4

        return True
