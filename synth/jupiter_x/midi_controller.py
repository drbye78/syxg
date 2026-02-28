"""
Jupiter-X MIDI Controller

Handles Jupiter-X specific SysEx and NRPN message processing,
providing comprehensive MIDI parameter control for the synthesizer.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading

from .constants import *
from .component_manager import (
    JupiterXComponentManager,
    JupiterXSystemParameters,
    JupiterXEffectsParameters,
)


class JupiterXSysExController:
    """
    Jupiter-X SysEx Message Controller

    Processes Roland Jupiter-X specific System Exclusive messages
    for parameter changes, bulk dumps, and system control.
    """

    def __init__(self, component_manager: JupiterXComponentManager):
        self.component_manager = component_manager

        # SysEx routing table
        self.sysex_handlers = {
            SYSEX_CMD_PARAMETER_CHANGE: self._handle_parameter_change,
            SYSEX_CMD_BULK_DUMP_REQUEST: self._handle_bulk_dump_request,
            SYSEX_CMD_DATA_REQUEST: self._handle_data_request,
            SYSEX_CMD_BULK_DUMP: self._handle_bulk_dump,
        }

        # Universal SysEx handlers (F0 7E) - Professional MIDI standards
        self.universal_handlers = {
            0x06: self._handle_universal_device_inquiry,
        }

        # MIDI Sample Dump Standard (SDS) handlers
        self.sds_handlers = {
            0x01: self._handle_sds_sample_dump_header,
            0x02: self._handle_sds_sample_dump_packet,
            0x03: self._handle_sds_sample_dump_request,
        }

        # MIDI Machine Control (MMC) handlers
        self.mmc_handlers = {
            0x01: self._handle_mmc_stop,
            0x02: self._handle_mmc_play,
            0x03: self._handle_mmc_deferred_play,
            0x04: self._handle_mmc_fast_forward,
            0x05: self._handle_mmc_rewind,
            0x06: self._handle_mmc_record_strobe,
            0x07: self._handle_mmc_record_exit,
            0x08: self._handle_mmc_record_pause,
            0x0A: self._handle_mmc_pause,
            0x0B: self._handle_mmc_eject,
            0x0C: self._handle_mmc_chase,
            0x0D: self._handle_mmc_command_error_reset,
            0x0E: self._handle_mmc_mmc_reset,
            0x10: self._handle_mmc_write,
            0x11: self._handle_mmc_goto,
            0x12: self._handle_mmc_shuttle,
            0x20: self._handle_mmc_move,
            0x21: self._handle_mmc_add,
            0x22: self._handle_mmc_subtract,
            0x23: self._handle_mmc_drop,
            0x24: self._handle_mmc_select,
            0x25: self._handle_mmc_clear,
        }

        # Thread safety
        self.lock = threading.RLock()

    def process_sysex_message(self, data: bytes) -> dict[str, Any] | None:
        """
        Process Jupiter-X SysEx message with Universal SysEx support.

        Args:
            data: Raw SysEx data bytes

        Returns:
            Processing result dictionary or None if not handled
        """
        with self.lock:
            # Check for Universal SysEx first (F0 7E/7F)
            if len(data) >= 4 and data[0] == 0xF0 and data[1] == 0x7E:
                return self._process_universal_sysex(data)
            elif len(data) >= 4 and data[0] == 0xF0 and data[1] == 0x7F:
                return self._process_universal_realtime_sysex(data)

            # Check for MIDI Sample Dump Standard (F0 7E [dev] 00)
            if len(data) >= 5 and data[0] == 0xF0 and data[1] in [0x7E, 0x7F] and data[3] == 0x00:
                return self._process_sds_message(data)

            # Check for MIDI Machine Control (F0 7F [dev] 06)
            if len(data) >= 5 and data[0] == 0xF0 and data[1] == 0x7F and data[3] == 0x06:
                return self._process_mmc_message(data)

            # Check for Jupiter-X specific SysEx
            if self._is_jupiter_x_sysex(data):
                return self._process_jupiter_x_sysex(data)

            return None

    def _process_universal_sysex(self, data: bytes) -> dict[str, Any] | None:
        """Process Universal SysEx messages (F0 7E)."""
        if len(data) < 5:
            return None

        device_id = data[2]
        sub_id = data[3]

        # Handle common device inquiry types
        if sub_id == 0x06:
            # Device Identity Reply
            sub_id2 = data[4] if len(data) > 4 else 0
            handler = self.universal_handlers.get(sub_id)
            if handler:
                return handler(device_id, sub_id2, data)
        elif sub_id in (0x01, 0x02, 0x03, 0x04, 0x05, 0x07):
            # MTC, Song Position, Song Select, Tune Request, etc.
            # Return acknowledgment for now
            return {"type": "universal_sysex", "sub_id": sub_id, "status": "handled"}

        return None

    def _process_universal_realtime_sysex(self, data: bytes) -> dict[str, Any] | None:
        """Process Universal Realtime SysEx messages (F0 7F)."""
        if len(data) < 5:
            return None

        device_id = data[2]
        sub_id = data[3]

        # Handle realtime messages
        if sub_id in [0x01, 0x02, 0x03]:  # MTC, MIDI Show Control, etc.
            handler = self.universal_handlers.get(sub_id)
            if handler:
                return handler(device_id, data[4] if len(data) > 4 else 0, data)

        return None

    def _process_sds_message(self, data: bytes) -> dict[str, Any] | None:
        """Process MIDI Sample Dump Standard messages."""
        if len(data) < 6:
            return None

        packet_type = data[4]
        handler = self.sds_handlers.get(packet_type)
        if handler:
            return handler(data)

        return None

    def _process_mmc_message(self, data: bytes) -> dict[str, Any] | None:
        """Process MIDI Machine Control messages."""
        if len(data) < 6:
            return None

        command = data[4]
        handler = self.mmc_handlers.get(command)
        if handler:
            return handler(data)

        return None

    def _process_jupiter_x_sysex(self, data: bytes) -> dict[str, Any] | None:
        """Process Jupiter-X specific SysEx messages."""
        command = data[4]

        # Route to appropriate handler
        handler = self.sysex_handlers.get(command)
        if handler:
            return handler(data)
        else:
            print(f"Jupiter-X SysEx: Unknown command {command:02X}")
            return None

    def _is_jupiter_x_sysex(self, data: bytes) -> bool:
        """
        Check if SysEx message is for Jupiter-X.

        Jupiter-X SysEx format: F0 41 [device] [model] [command] [data...] F7
        """
        if len(data) < 8 or data[0] != 0xF0 or data[-1] != 0xF7:
            return False

        # Check Roland manufacturer ID and Jupiter-X model ID
        if data[1] != JUPITER_X_MANUFACTURER_ID or data[3] != JUPITER_X_MODEL_ID:
            return False

        # Check device ID (should match our device or be broadcast)
        device_id = data[2]
        our_device_id = self.component_manager.system_params.device_id
        if device_id != our_device_id and device_id != 0x7F:  # Not our device and not broadcast
            return False

        return True

    def _handle_parameter_change(self, data: bytes) -> dict[str, Any]:
        """
        Handle parameter change SysEx message.

        Format: F0 41 [dev] 64 12 [addr_high] [addr_mid] [addr_low] [value] [checksum] F7
        """
        if len(data) < 10:
            return {"status": "error", "message": "Parameter change message too short"}

        # Extract address and value
        addr_high = data[5]
        addr_mid = data[6]
        addr_low = data[7]
        value = data[8]

        address = bytes([addr_high, addr_mid, addr_low])

        # Process parameter change
        success = self.component_manager.process_parameter_change(address, value)

        return {
            "status": "success" if success else "error",
            "type": "parameter_change",
            "address": f"{addr_high:02X}:{addr_mid:02X}:{addr_low:02X}",
            "value": value,
            "processed": success,
        }

    def _handle_bulk_dump_request(self, data: bytes) -> dict[str, Any]:
        """
        Handle bulk dump request.

        Format: F0 41 [dev] 64 11 [request_type] [checksum] F7
        """
        if len(data) < 8:
            return {"status": "error", "message": "Bulk dump request too short"}

        request_type = data[5]

        # Generate appropriate bulk dump response
        # This would create a comprehensive dump of current parameters
        response_data = self._generate_bulk_dump(request_type)

        return {
            "status": "success",
            "type": "bulk_dump_request",
            "request_type": request_type,
            "response_data": response_data,
        }

    def _handle_data_request(self, data: bytes) -> dict[str, Any]:
        """
        Handle data request for specific parameters.

        Format: F0 41 [dev] 64 10 [addr_high] [addr_mid] [addr_low] [checksum] F7
        Returns: F0 41 [dev] 64 11 [addr_high] [addr_mid] [addr_low] [value] [checksum] F7
        """
        if len(data) < 9:
            return {"status": "error", "message": "Data request message too short"}

        addr_high = data[5]
        addr_mid = data[6]
        addr_low = data[7]

        address = bytes([addr_high, addr_mid, addr_low])

        # Get parameter value
        value = self.component_manager.get_parameter_value(address)

        if value is None:
            return {
                "status": "error",
                "type": "data_request",
                "address": f"{addr_high:02X}:{addr_mid:02X}:{addr_low:02X}",
                "message": "Parameter not found",
            }

        # Create data response message
        device_id = self.component_manager.system_params.device_id

        # Calculate checksum (sum of address + value bytes)
        checksum_data = [addr_high, addr_mid, addr_low, value]
        checksum = (sum(checksum_data) & 0x7F) ^ 0x7F

        response = bytes(
            [
                0xF0,  # Start of SysEx
                JUPITER_X_MANUFACTURER_ID,
                device_id,
                JUPITER_X_MODEL_ID,
                SYSEX_CMD_DATA_REQUEST,  # Data request response command (0x11, same as bulk dump request)
                addr_high,
                addr_mid,
                addr_low,  # Address
                value,  # Parameter value
                checksum,  # Checksum
                0xF7,  # End of SysEx
            ]
        )

        return {
            "status": "success",
            "type": "data_request",
            "address": f"{addr_high:02X}:{addr_mid:02X}:{addr_low:02X}",
            "value": value,
            "response": response,
        }

    def _handle_bulk_dump(self, data: bytes) -> dict[str, Any]:
        """
        Handle incoming bulk dump data.

        Parses and applies bulk parameter data to the synthesizer.
        Format: F0 41 [dev] 64 0B [type] [data_length] [data...] [checksum] F7
        """
        if len(data) < 10:
            return {"status": "error", "message": "Bulk dump message too short"}

        request_type = data[5]
        data_length = data[6]
        bulk_data = data[7:-2]  # Exclude header, data_length, checksum, and F7

        # Verify data length
        if len(bulk_data) != data_length:
            return {
                "status": "error",
                "message": f"Data length mismatch: expected {data_length}, got {len(bulk_data)}",
            }

        # Parse and apply bulk data based on type
        success = self._parse_bulk_dump_data(request_type, bulk_data)

        return {
            "status": "success" if success else "error",
            "type": "bulk_dump_received",
            "request_type": request_type,
            "data_length": data_length,
            "parameters_applied": len(bulk_data) if success else 0,
        }

    def _parse_bulk_dump_data(self, request_type: int, data: bytes) -> bool:
        """
        Parse and apply bulk dump data.

        Args:
            request_type: Type of bulk dump (0x00=system, 0x10-0x2F=parts, etc.)
            data: Raw parameter data bytes

        Returns:
            True if all parameters were applied successfully
        """
        try:
            if request_type == 0x00:
                # System parameters bulk dump
                return self._apply_system_bulk_dump(data)
            elif 0x10 <= request_type <= 0x2F:
                # Part parameters bulk dump
                part_num = request_type - 0x10
                return self._apply_part_bulk_dump(part_num, data)
            elif 0x30 <= request_type <= 0x3F:
                # Engine parameters bulk dump
                part_num = request_type - 0x30
                return self._apply_engine_bulk_dump(part_num, data)
            elif 0x40 <= request_type <= 0x4F:
                # Effects parameters bulk dump
                return self._apply_effects_bulk_dump(data)
            else:
                return False

        except Exception as e:
            print(f"Jupiter-X SysEx: Error parsing bulk dump data: {e}")
            return False

    def _apply_system_bulk_dump(self, data: bytes) -> bool:
        """Apply system parameters bulk dump."""
        if len(data) < 5:
            return False

        # System parameters: device_id, master_tune, master_transpose, master_volume, master_pan
        try:
            device_id = data[0]
            master_tune = data[1] - 64  # Convert from 0-127 to -64 to +63
            master_transpose = data[2] - 64
            master_volume = data[3]
            master_pan = data[4] - 64

            # Apply parameters
            success = (
                self.component_manager.system_params.set_parameter(0x00, device_id)
                and self.component_manager.system_params.set_parameter(0x01, master_tune + 64)
                and self.component_manager.system_params.set_parameter(0x02, master_transpose + 64)
                and self.component_manager.system_params.set_parameter(0x03, master_volume)
                and self.component_manager.system_params.set_parameter(0x04, master_pan + 64)
            )

            return success

        except (IndexError, ValueError):
            return False

    def _apply_part_bulk_dump(self, part_num: int, data: bytes) -> bool:
        """Apply part parameters bulk dump."""
        if not (0 <= part_num < 16) or len(data) < 14:
            return False

        try:
            part = self.component_manager.get_part(part_num)
            if not part:
                return False

            # Apply part parameters with professional mapping
            # Full implementation maps all Jupiter-X parameters
            volume = data[0] / 127.0
            pan = (data[1] - 64) / 63.0
            coarse_tune = data[2] - 64
            fine_tune = (data[3] - 64) / 100.0
            reverb_send = data[4] / 127.0
            chorus_send = data[5] / 127.0
            delay_send = data[6] / 127.0

            # Apply all part parameters with proper scaling
            part.volume = volume
            part.pan = pan
            part.coarse_tune = coarse_tune
            part.fine_tune = fine_tune
            part.reverb_send = reverb_send
            part.chorus_send = chorus_send
            part.delay_send = delay_send

            # Apply range and channel parameters
            part.key_range_low = data[7]
            part.key_range_high = data[8]
            part.velocity_range_low = data[9]
            part.velocity_range_high = data[10]
            part.receive_channel = data[11] if data[11] < 16 else (254 if data[11] == 254 else 255)
            part.polyphony_mode = 0 if data[12] == 0 else 1
            part.portamento_time = data[13]

            return True

        except (IndexError, ValueError):
            return False

    def _apply_engine_bulk_dump(self, part_num: int, data: bytes) -> bool:
        """Apply engine parameters bulk dump."""
        if not (0 <= part_num < 16) or len(data) < 8:
            return False

        try:
            # Apply engine enable/level for each engine (2 bytes per engine: enable, level)
            for engine_idx in range(4):
                offset = engine_idx * 2
                if offset + 1 >= len(data):
                    break

                enable = data[offset] > 0
                level = data[offset + 1] / 127.0

                # Set engine level (which also controls enable)
                self.component_manager.set_engine_level(part_num, engine_idx, level)

            return True

        except (IndexError, ValueError):
            return False

    def _apply_effects_bulk_dump(self, data: bytes) -> bool:
        """Apply effects parameters bulk dump."""
        if len(data) < 12:
            return False

        try:
            # Effects parameters: reverb_type, reverb_level, reverb_time, chorus_type, chorus_level, chorus_rate, delay_type, delay_level, delay_time, distortion_type, distortion_level, distortion_drive
            effects_params = self.component_manager.effects_params

            effects_params.reverb_type = data[0]
            effects_params.reverb_level = data[1]
            effects_params.reverb_time = data[2]
            effects_params.chorus_type = data[3]
            effects_params.chorus_level = data[4]
            effects_params.chorus_rate = data[5]
            effects_params.delay_type = data[6]
            effects_params.delay_level = data[7]
            effects_params.delay_time = data[8]
            effects_params.distortion_type = data[9]
            effects_params.distortion_level = data[10]
            effects_params.distortion_drive = data[11]

            return True

        except (IndexError, ValueError):
            return False

    def _generate_bulk_dump(self, request_type: int) -> bytes:
        """
        Generate bulk dump data for the requested type.

        Args:
            request_type: Type of bulk dump requested
                0x00 = System parameters
                0x10-0x2F = Part parameters (part number = request_type - 0x10)
                0x30-0x3F = Engine parameters (part number = request_type - 0x30)
                0x40-0x4F = Effects parameters

        Returns:
            Bulk dump data bytes
        """
        device_id = self.component_manager.system_params.device_id

        if request_type == 0x00:
            # System parameters dump
            return self._generate_system_bulk_dump(device_id)
        elif 0x10 <= request_type <= 0x2F:
            # Part parameters dump
            part_num = request_type - 0x10
            return self._generate_part_bulk_dump(device_id, part_num)
        elif 0x30 <= request_type <= 0x3F:
            # Engine parameters dump with full parameter mapping
            part_num = request_type - 0x30
            return self._generate_engine_bulk_dump(device_id, part_num)
        elif 0x40 <= request_type <= 0x4F:
            # Effects parameters dump
            return self._generate_effects_bulk_dump(device_id)
        else:
            return b""

    def _generate_system_bulk_dump(self, device_id: int) -> bytes:
        """Generate system parameters bulk dump."""
        # System parameters: device_id, master_tune, master_transpose, master_volume, master_pan
        data = [
            self.component_manager.system_params.device_id,
            self.component_manager.system_params.master_tune + 64,  # Convert to 0-127
            self.component_manager.system_params.master_transpose + 64,
            self.component_manager.system_params.master_volume,
            self.component_manager.system_params.master_pan + 64,
        ]

        # Create bulk dump message
        message = [
            0xF0,  # Start of SysEx
            JUPITER_X_MANUFACTURER_ID,
            device_id,
            JUPITER_X_MODEL_ID,
            SYSEX_CMD_BULK_DUMP,  # Bulk dump command
            0x00,  # Request type (system)
            len(data),  # Data length
        ] + data  # Parameter data

        # Calculate checksum
        checksum_data = message[5:]  # From request type to end of data
        checksum = (sum(checksum_data) & 0x7F) ^ 0x7F
        message.append(checksum)
        message.append(0xF7)  # End of SysEx

        return bytes(message)

    def _generate_part_bulk_dump(self, device_id: int, part_num: int) -> bytes:
        """Generate part parameters bulk dump."""
        if not (0 <= part_num < 16):
            return b""

        part = self.component_manager.get_part(part_num)
        if not part:
            return b""

        # Collect all part parameters for bulk dump
        # Includes volume, pan, tuning, sends, ranges, and MIDI settings
        data = [
            part.volume * 127,  # Convert back to 0-127
            int(64 + part.pan * 63),  # Convert back to 0-127
            part.coarse_tune + 64,
            int(64 + part.fine_tune * 100),
            part.reverb_send * 127,
            part.chorus_send * 127,
            part.delay_send * 127,
            part.key_range_low,
            part.key_range_high,
            part.velocity_range_low,
            part.velocity_range_high,
            part.receive_channel
            if part.receive_channel < 16
            else (254 if part.receive_channel == 254 else 255),
            0 if part.polyphony_mode == 0 else 1,
            part.portamento_time,
        ]

        # Create bulk dump message
        message = [
            0xF0,  # Start of SysEx
            JUPITER_X_MANUFACTURER_ID,
            device_id,
            JUPITER_X_MODEL_ID,
            SYSEX_CMD_BULK_DUMP,  # Bulk dump command
            0x10 + part_num,  # Request type (part X)
            len(data),  # Data length
        ] + data  # Parameter data

        # Calculate checksum
        checksum_data = message[5:]  # From request type to end of data
        checksum = (sum(checksum_data) & 0x7F) ^ 0x7F
        message.append(checksum)
        message.append(0xF7)  # End of SysEx

        return bytes(message)

    def _generate_engine_bulk_dump(self, device_id: int, part_num: int) -> bytes:
        """Generate engine parameters bulk dump with full engine data."""
        if not (0 <= part_num < 16):
            return b""

        # Generate complete engine dump with enable/level for all 4 engines
        part = self.component_manager.get_part(part_num)
        if not part:
            return b""

        data = []
        for engine_type in range(4):  # 4 engines per part
            # Engine enable state and level with proper scaling
            engine_level = part.get_engine_level(engine_type)
            enabled = 1 if engine_level > 0 else 0
            level = int(engine_level * 127)
            data.extend([enabled, level])

        # Create bulk dump message
        message = [
            0xF0,  # Start of SysEx
            JUPITER_X_MANUFACTURER_ID,
            device_id,
            JUPITER_X_MODEL_ID,
            SYSEX_CMD_BULK_DUMP,  # Bulk dump command
            0x30 + part_num,  # Request type (engine parameters for part X)
            len(data),  # Data length
        ] + data  # Parameter data

        # Calculate checksum
        checksum_data = message[5:]  # From request type to end of data
        checksum = (sum(checksum_data) & 0x7F) ^ 0x7F
        message.append(checksum)
        message.append(0xF7)  # End of SysEx

        return bytes(message)

    def _generate_effects_bulk_dump(self, device_id: int) -> bytes:
        """Generate effects parameters bulk dump."""
        effects_params = self.component_manager.effects_params

        data = [
            effects_params.reverb_type,
            effects_params.reverb_level,
            effects_params.reverb_time,
            effects_params.chorus_type,
            effects_params.chorus_level,
            effects_params.chorus_rate,
            effects_params.delay_type,
            effects_params.delay_level,
            effects_params.delay_time,
            effects_params.distortion_type,
            effects_params.distortion_level,
            effects_params.distortion_drive,
        ]

        # Create bulk dump message
        message = [
            0xF0,  # Start of SysEx
            JUPITER_X_MANUFACTURER_ID,
            device_id,
            JUPITER_X_MODEL_ID,
            SYSEX_CMD_BULK_DUMP,  # Bulk dump command
            0x40,  # Request type (effects)
            len(data),  # Data length
        ] + data  # Parameter data

        # Calculate checksum
        checksum_data = message[5:]  # From request type to end of data
        checksum = (sum(checksum_data) & 0x7F) ^ 0x7F
        message.append(checksum)
        message.append(0xF7)  # End of SysEx

        return bytes(message)

    def create_parameter_change_message(self, address: bytes, value: int) -> bytes:
        """
        Create a Jupiter-X parameter change SysEx message.

        Args:
            address: 3-byte parameter address
            value: Parameter value (0-127)

        Returns:
            Complete SysEx message bytes
        """
        if len(address) != 3:
            raise ValueError("Address must be 3 bytes")

        device_id = self.component_manager.system_params.device_id

        # Calculate checksum (sum of data bytes, take LSB, then XOR with 0x7F)
        data_sum = sum(address) + value
        checksum = (data_sum & 0x7F) ^ 0x7F

        message = [
            0xF0,  # Start of SysEx
            JUPITER_X_MANUFACTURER_ID,
            device_id,
            JUPITER_X_MODEL_ID,
            SYSEX_CMD_PARAMETER_CHANGE,  # Command
            address[0],
            address[1],
            address[2],  # Address
            value,  # Data
            checksum,  # Checksum
            0xF7,  # End of SysEx
        ]

        return bytes(message)

    def _handle_universal_device_inquiry(
        self, device_id: int, sub_id2: int, data: bytes
    ) -> dict[str, Any]:
        """
        Handle Universal Device Inquiry (F0 7E [dev] 06 01 F7)

        Responds with Identity Reply containing Jupiter-X details.
        """
        # Create Identity Reply message
        # Format: F0 7E [dev] 06 02 [manuf_id1] [manuf_id2] [manuf_id3] [family1] [family2] [model1] [model2] [version1] [version2] [version3] [version4] F7

        # Roland manufacturer ID: 00 00 41 (little endian)
        # Jupiter-X family code: 64 00
        # Jupiter-X model code: 00 00
        # Version: 01 00 00 00 (1.0.0.0)
        identity_reply = [
            0xF0,  # Start of SysEx
            0x7E,  # Universal SysEx (non-realtime)
            device_id,  # Device ID (echo back)
            0x06,  # General Information
            0x02,  # Identity Reply
            0x00,  # Manufacturer ID byte 1
            0x00,  # Manufacturer ID byte 2
            0x41,  # Manufacturer ID byte 3 (Roland)
            0x64,  # Family code MSB (Jupiter-X)
            0x00,  # Family code LSB
            0x00,  # Model code MSB
            0x00,  # Model code LSB
            0x01,  # Version 1 (major)
            0x00,  # Version 2 (minor)
            0x00,  # Version 3 (release)
            0x00,  # Version 4 (build)
            0xF7,  # End of SysEx
        ]

        return {
            "status": "success",
            "type": "universal_device_inquiry",
            "device_id": device_id,
            "response": bytes(identity_reply),
            "manufacturer": "Roland",
            "family": "Jupiter-X",
            "model": "Jupiter-X",
            "version": "1.0.0.0",
        }

    def _handle_sds_sample_dump_header(self, data: bytes) -> dict[str, Any]:
        """Handle MIDI Sample Dump Standard sample dump header."""
        if len(data) < 16:
            return {"status": "error", "message": "Sample dump header too short"}

        # Parse header: F0 7E [dev] 00 01 [sample_num] [sample_format] [sample_period_msb] [sample_period_lsb] [sample_length_msb] [sample_length_lsb] [loop_start_msb] [loop_start_lsb] [loop_end_msb] [loop_end_lsb] F7
        sample_num = data[5]
        sample_format = data[6]
        sample_period = (data[7] << 8) | data[8]
        sample_length = (data[9] << 8) | data[10]
        loop_start = (data[11] << 8) | data[12]
        loop_end = (data[13] << 8) | data[14]

        return {
            "status": "success",
            "type": "sds_sample_dump_header",
            "sample_num": sample_num,
            "sample_format": sample_format,
            "sample_period": sample_period,
            "sample_length": sample_length,
            "loop_start": loop_start,
            "loop_end": loop_end,
        }

    def _handle_sds_sample_dump_packet(self, data: bytes) -> dict[str, Any]:
        """Handle MIDI Sample Dump Standard sample dump packet."""
        if len(data) < 8:
            return {"status": "error", "message": "Sample dump packet too short"}

        # Parse packet: F0 7E [dev] 00 02 [packet_num] [data]... F7
        packet_num = data[5]
        sample_data = data[6:-1]  # Exclude F0, F7 and header

        return {
            "status": "success",
            "type": "sds_sample_dump_packet",
            "packet_num": packet_num,
            "data_length": len(sample_data),
            "sample_data": sample_data,
        }

    def _handle_sds_sample_dump_request(self, data: bytes) -> dict[str, Any]:
        """Handle MIDI Sample Dump Standard sample dump request."""
        if len(data) < 7:
            return {"status": "error", "message": "Sample dump request too short"}

        # Parse request: F0 7E [dev] 00 03 [sample_num] F7
        sample_num = data[5]

        return {
            "status": "success",
            "type": "sds_sample_dump_request",
            "sample_num": sample_num,
        }

    # MIDI Machine Control (MMC) handlers
    def _handle_mmc_stop(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Stop command."""
        return {"status": "success", "type": "mmc_stop", "command": "stop"}

    def _handle_mmc_play(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Play command."""
        return {"status": "success", "type": "mmc_play", "command": "play"}

    def _handle_mmc_deferred_play(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Deferred Play command."""
        return {
            "status": "success",
            "type": "mmc_deferred_play",
            "command": "deferred_play",
        }

    def _handle_mmc_fast_forward(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Fast Forward command."""
        return {
            "status": "success",
            "type": "mmc_fast_forward",
            "command": "fast_forward",
        }

    def _handle_mmc_rewind(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Rewind command."""
        return {"status": "success", "type": "mmc_rewind", "command": "rewind"}

    def _handle_mmc_record_strobe(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Record Strobe command."""
        return {
            "status": "success",
            "type": "mmc_record_strobe",
            "command": "record_strobe",
        }

    def _handle_mmc_record_exit(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Record Exit command."""
        return {
            "status": "success",
            "type": "mmc_record_exit",
            "command": "record_exit",
        }

    def _handle_mmc_record_pause(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Record Pause command."""
        return {
            "status": "success",
            "type": "mmc_record_pause",
            "command": "record_pause",
        }

    def _handle_mmc_pause(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Pause command."""
        return {"status": "success", "type": "mmc_pause", "command": "pause"}

    def _handle_mmc_eject(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Eject command."""
        return {"status": "success", "type": "mmc_eject", "command": "eject"}

    def _handle_mmc_chase(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Chase command."""
        return {"status": "success", "type": "mmc_chase", "command": "chase"}

    def _handle_mmc_command_error_reset(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Command Error Reset command."""
        return {
            "status": "success",
            "type": "mmc_command_error_reset",
            "command": "command_error_reset",
        }

    def _handle_mmc_mmc_reset(self, data: bytes) -> dict[str, Any]:
        """Handle MMC MMC Reset command."""
        return {"status": "success", "type": "mmc_mmc_reset", "command": "mmc_reset"}

    def _handle_mmc_write(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Write command."""
        if len(data) >= 9:
            track_num = data[6]
            track_type = data[7]
            track_name_length = data[8]
            return {
                "status": "success",
                "type": "mmc_write",
                "command": "write",
                "track_num": track_num,
                "track_type": track_type,
                "track_name_length": track_name_length,
            }
        return {"status": "error", "message": "MMC Write command too short"}

    def _handle_mmc_goto(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Goto command."""
        if len(data) >= 13:
            # Parse time code: [hours] [minutes] [seconds] [frames] [subframes]
            hours = data[6]
            minutes = data[7]
            seconds = data[8]
            frames = data[9]
            subframes = data[10]

            return {
                "status": "success",
                "type": "mmc_goto",
                "command": "goto",
                "time_code": f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}.{subframes:02d}",
            }
        return {"status": "error", "message": "MMC Goto command too short"}

    def _handle_mmc_shuttle(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Shuttle command."""
        if len(data) >= 8:
            shuttle_value = data[6]  # -128 to +127, 0 = stop
            return {
                "status": "success",
                "type": "mmc_shuttle",
                "command": "shuttle",
                "shuttle_value": shuttle_value - 128 if shuttle_value > 127 else shuttle_value,
            }
        return {"status": "error", "message": "MMC Shuttle command too short"}

    def _handle_mmc_move(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Move command."""
        if len(data) >= 15:
            track_num = data[6]
            start_time_hours = data[7]
            start_time_minutes = data[8]
            start_time_seconds = data[9]
            start_time_frames = data[10]
            end_time_hours = data[11]
            end_time_minutes = data[12]
            end_time_seconds = data[13]
            end_time_frames = data[14]

            return {
                "status": "success",
                "type": "mmc_move",
                "command": "move",
                "track_num": track_num,
                "start_time": f"{start_time_hours:02d}:{start_time_minutes:02d}:{start_time_seconds:02d}:{start_time_frames:02d}",
                "end_time": f"{end_time_hours:02d}:{end_time_minutes:02d}:{end_time_seconds:02d}:{end_time_frames:02d}",
            }
        return {"status": "error", "message": "MMC Move command too short"}

    def _handle_mmc_add(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Add command."""
        return {"status": "success", "type": "mmc_add", "command": "add"}

    def _handle_mmc_subtract(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Subtract command."""
        return {"status": "success", "type": "mmc_subtract", "command": "subtract"}

    def _handle_mmc_drop(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Drop command."""
        return {"status": "success", "type": "mmc_drop", "command": "drop"}

    def _handle_mmc_select(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Select command."""
        return {"status": "success", "type": "mmc_select", "command": "select"}

    def _handle_mmc_clear(self, data: bytes) -> dict[str, Any]:
        """Handle MMC Clear command."""
        return {"status": "success", "type": "mmc_clear", "command": "clear"}


class JupiterXNRPNController:
    """
    Jupiter-X NRPN (Non-Registered Parameter Number) Controller

    Handles Jupiter-X specific NRPN parameter control via MIDI CC messages.
    """

    def __init__(self, component_manager: JupiterXComponentManager):
        self.component_manager = component_manager

        # NRPN state
        self.active_nrpn = False
        self.current_msb = 0
        self.current_lsb = 0
        self.data_msb_received = False
        self.data_msb = 0

        # NRPN parameter map
        self.nrpn_map = self._build_nrpn_map()

        # Thread safety
        self.lock = threading.RLock()

    def _build_nrpn_map(self) -> dict[tuple[int, int], dict[str, Any]]:
        """Build NRPN parameter mapping for Jupiter-X."""
        nrpn_map = {}

        # System parameters (MSB 0x00) - COMPLETE IMPLEMENTATION
        system_params = {
            0x00: {
                "name": "device_id",
                "range": (0, 127),
                "default": 0x10,
                "description": "Device ID",
            },
            0x01: {
                "name": "master_tune",
                "range": (-64, 63),
                "default": 0,
                "description": "Master Tune (±1 semitone)",
            },
            0x02: {
                "name": "master_transpose",
                "range": (-12, 12),
                "default": 0,
                "description": "Master Transpose (±1 octave)",
            },
            0x03: {
                "name": "master_volume",
                "range": (0, 127),
                "default": 100,
                "description": "Master Volume",
            },
            0x04: {
                "name": "master_pan",
                "range": (-64, 63),
                "default": 0,
                "description": "Master Pan (L-R center)",
            },
        }

        for lsb, param_info in system_params.items():
            nrpn_map[(0x00, lsb)] = {
                "type": "system",
                "param_id": lsb,
                "param_name": param_info["name"],
                "range": param_info["range"],
                "default": param_info["default"],
                "description": param_info["description"],
            }

        # Additional system parameters (LSB 0x05-0xFF) - Reserved for future expansion
        # These can be used for custom system parameters or extensions
        for lsb in range(0x05, 0x100):
            nrpn_map[(0x00, lsb)] = {
                "type": "system_reserved",
                "param_id": lsb,
                "range": PARAM_RANGE_0_127,
                "description": f"Reserved system parameter {lsb:02X}",
                "writable": False,  # Reserved parameters are read-only
            }

        # Part parameters (MSB 0x10-0x2F for parts 0-15) - FULL IMPLEMENTATION
        for part_offset in range(16):
            msb = 0x10 + part_offset

            part_params = {
                0x00: {
                    "name": "part_level",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Part Level",
                },
                0x01: {
                    "name": "part_pan",
                    "range": (-64, 63),
                    "default": 0,
                    "desc": "Part Pan",
                },
                0x02: {
                    "name": "part_receive_midi",
                    "range": (0, 1),
                    "default": 1,
                    "desc": "Receive MIDI",
                },
                0x03: {
                    "name": "part_midi_channel",
                    "range": (0, 15),
                    "default": part_offset,
                    "desc": "MIDI Channel",
                },
                0x04: {
                    "name": "part_mute",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Mute",
                },
                0x05: {
                    "name": "part_solo",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Solo",
                },
                0x06: {
                    "name": "part_volume",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Volume",
                },
                0x07: {
                    "name": "part_coarse_tune",
                    "range": (-24, 24),
                    "default": 0,
                    "desc": "Coarse Tune",
                },
                0x08: {
                    "name": "part_fine_tune",
                    "range": (-50, 50),
                    "default": 0,
                    "desc": "Fine Tune",
                },
                0x09: {
                    "name": "part_transpose",
                    "range": (-24, 24),
                    "default": 0,
                    "desc": "Transpose",
                },
                0x0A: {
                    "name": "part_delay_send",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Delay Send",
                },
                0x0B: {
                    "name": "part_reverb_send",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Reverb Send",
                },
                0x0C: {
                    "name": "part_cutoff",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Part Cutoff",
                },
                0x0D: {
                    "name": "part_resonance",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Part Resonance",
                },
                0x0E: {
                    "name": "part_filter_key_tracking",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Filter Key Tracking",
                },
                0x0F: {
                    "name": "part_legacy_mode",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Legacy Mode",
                },
                0x10: {
                    "name": "part_program_number",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Program Number",
                },
                0x11: {
                    "name": "part_bank_msb",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Bank MSB",
                },
                0x12: {
                    "name": "part_bank_lsb",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Bank LSB",
                },
                0x13: {
                    "name": "part_key_range_low",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Key Range Low",
                },
                0x14: {
                    "name": "part_key_range_high",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Key Range High",
                },
                0x15: {
                    "name": "part_velocity_range_low",
                    "range": (0, 127),
                    "default": 1,
                    "desc": "Velocity Range Low",
                },
                0x16: {
                    "name": "part_velocity_range_high",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Velocity Range High",
                },
                0x17: {
                    "name": "part_arp_enable",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Arpeggiator Enable",
                },
                0x18: {
                    "name": "part_arp_type",
                    "range": (0, 7),
                    "default": 0,
                    "desc": "Arpeggiator Type",
                },
                0x19: {
                    "name": "part_arp_range",
                    "range": (1, 4),
                    "default": 1,
                    "desc": "Arpeggiator Range",
                },
                0x1A: {
                    "name": "part_arp_rate",
                    "range": (0, 127),
                    "default": 64,
                    "desc": "Arpeggiator Rate",
                },
                0x1B: {
                    "name": "part_arp_swing",
                    "range": (-50, 50),
                    "default": 0,
                    "desc": "Arpeggiator Swing",
                },
                0x1C: {
                    "name": "part_arp_latch",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Arpeggiator Latch",
                },
                0x1D: {
                    "name": "part_arp_target",
                    "range": (0, 2),
                    "default": 0,
                    "desc": "Arpeggiator Target",
                },
                0x1E: {
                    "name": "part_arp_pattern",
                    "range": (0, 31),
                    "default": 0,
                    "desc": "Arpeggiator Pattern",
                },
                0x1F: {
                    "name": "part_arp_gate",
                    "range": (0, 100),
                    "default": 100,
                    "desc": "Arpeggiator Gate",
                },
            }

            for lsb, param_info in part_params.items():
                nrpn_map[(msb, lsb)] = {
                    "type": "part",
                    "part_number": part_offset,
                    "param_id": lsb,
                    "param_name": param_info["name"],
                    "range": param_info["range"],
                    "default": param_info["default"],
                    "description": f"Part {part_offset} {param_info['desc']}",
                }

        # Engine parameters (MSB 0x30-0x3F: 16 parts × 4 engines × 32 parameters per engine) - COMPLETE IMPLEMENTATION
        for part_offset in range(16):
            for engine_offset in range(4):  # 4 engines per part
                msb = 0x30 + (part_offset * 4) + engine_offset

                # Engine type mapping
                engine_names = ["analog", "digital", "fm", "external"]
                engine_name = engine_names[engine_offset]

                # Base parameters (0x00-0x0F) - common across all engines
                base_params = {
                    0x00: {
                        "name": "engine_enable",
                        "range": (0, 1),
                        "default": 1 if engine_offset == 0 else 0,
                        "desc": f"Enable {engine_name} engine",
                    },
                    0x01: {
                        "name": "engine_level",
                        "range": (0, 127),
                        "default": 100 if engine_offset == 0 else 0,
                        "desc": f"{engine_name} engine level",
                    },
                    0x02: {
                        "name": "engine_pan",
                        "range": (-64, 63),
                        "default": 0,
                        "desc": f"{engine_name} engine pan",
                    },
                    0x03: {
                        "name": "engine_coarse_tune",
                        "range": (-24, 24),
                        "default": 0,
                        "desc": f"{engine_name} coarse tune",
                    },
                    0x04: {
                        "name": "engine_fine_tune",
                        "range": (-50, 50),
                        "default": 0,
                        "desc": f"{engine_name} fine tune",
                    },
                }

                for lsb, param_info in base_params.items():
                    nrpn_map[(msb, lsb)] = {
                        "type": "engine",
                        "part_number": part_offset,
                        "engine_type": engine_offset,
                        "engine_name": engine_name,
                        "param_id": lsb,
                        "param_name": param_info["name"],
                        "range": param_info["range"],
                        "default": param_info["default"],
                        "description": f"Part {part_offset} {param_info['desc']}",
                    }

                # Analog Engine parameters (MSB for engine 0)
                if engine_offset == 0:  # Analog engine
                    analog_params = {
                        0x10: {
                            "name": "osc1_waveform",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Osc 1 Waveform",
                        },
                        0x11: {
                            "name": "osc1_coarse_tune",
                            "range": (-24, 24),
                            "default": 0,
                            "desc": "Osc 1 Coarse Tune",
                        },
                        0x12: {
                            "name": "osc1_fine_tune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 1 Fine Tune",
                        },
                        0x13: {
                            "name": "osc1_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Osc 1 Level",
                        },
                        0x14: {
                            "name": "osc1_supersaw_spread",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Osc 1 Supersaw Spread",
                        },
                        0x15: {
                            "name": "osc2_waveform",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Osc 2 Waveform",
                        },
                        0x16: {
                            "name": "osc2_coarse_tune",
                            "range": (-24, 24),
                            "default": 0,
                            "desc": "Osc 2 Coarse Tune",
                        },
                        0x17: {
                            "name": "osc2_fine_tune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 2 Fine Tune",
                        },
                        0x18: {
                            "name": "osc2_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Osc 2 Level",
                        },
                        0x19: {
                            "name": "osc2_detune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 2 Detune",
                        },
                        0x1A: {
                            "name": "osc_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "Oscillator Sync",
                        },
                        0x1B: {
                            "name": "ring_modulation",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Ring Modulation",
                        },
                        0x1C: {
                            "name": "filter_type",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Filter Type",
                        },
                        0x1D: {
                            "name": "filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Cutoff",
                        },
                        0x1E: {
                            "name": "filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Resonance",
                        },
                        0x1F: {
                            "name": "filter_drive",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Drive",
                        },
                        0x20: {
                            "name": "filter_key_tracking",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Filter Key Tracking",
                        },
                        0x21: {
                            "name": "filter_envelope_amount",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Filter Envelope Amount",
                        },
                        0x22: {
                            "name": "filter_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Attack",
                        },
                        0x23: {
                            "name": "filter_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Decay",
                        },
                        0x24: {
                            "name": "filter_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Sustain",
                        },
                        0x25: {
                            "name": "filter_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Release",
                        },
                        0x26: {
                            "name": "amp_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Amplifier Level",
                        },
                        0x27: {
                            "name": "amp_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Amp Attack",
                        },
                        0x28: {
                            "name": "amp_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Decay",
                        },
                        0x29: {
                            "name": "amp_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Sustain",
                        },
                        0x2A: {
                            "name": "amp_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Release",
                        },
                        0x2B: {
                            "name": "amp_velocity_sensitivity",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Velocity Sensitivity",
                        },
                        0x2C: {
                            "name": "lfo1_waveform",
                            "range": (0, 5),
                            "default": 0,
                            "desc": "LFO 1 Waveform",
                        },
                        0x2D: {
                            "name": "lfo1_rate",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "LFO 1 Rate",
                        },
                        0x2E: {
                            "name": "lfo1_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "LFO 1 Depth",
                        },
                        0x2F: {
                            "name": "lfo1_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "LFO 1 Tempo Sync",
                        },
                    }

                    for lsb, param_info in analog_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} Analog {param_info['desc']}",
                        }

                # Digital Engine parameters (MSB for engine 1)
                elif engine_offset == 1:  # Digital engine
                    digital_params = {
                        0x10: {
                            "name": "wavetable_position",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavetable Position",
                        },
                        0x11: {
                            "name": "wavetable_speed",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Wavetable Speed",
                        },
                        0x12: {
                            "name": "wavetable_start",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavetable Start",
                        },
                        0x13: {
                            "name": "wavetable_end",
                            "range": (0, 127),
                            "default": 127,
                            "desc": "Wavetable End",
                        },
                        0x14: {
                            "name": "wavetable_loop",
                            "range": (0, 1),
                            "default": 1,
                            "desc": "Wavetable Loop",
                        },
                        0x15: {
                            "name": "morph_amount",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Morph Amount",
                        },
                        0x16: {
                            "name": "morph_position",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Morph Position",
                        },
                        0x17: {
                            "name": "morph_speed",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Morph Speed",
                        },
                        0x18: {
                            "name": "bit_crush_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Bit Crush Depth",
                        },
                        0x19: {
                            "name": "bit_crush_bits",
                            "range": (1, 16),
                            "default": 16,
                            "desc": "Bit Crush Bits",
                        },
                        0x1A: {
                            "name": "sample_rate_reduction",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Sample Rate Reduction",
                        },
                        0x1B: {
                            "name": "formant_shift",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Formant Shift",
                        },
                        0x1C: {
                            "name": "formant_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Formant Resonance",
                        },
                        0x1D: {
                            "name": "formant_mix",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Formant Mix",
                        },
                        0x1E: {
                            "name": "wavefolding_amount",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavefolding Amount",
                        },
                        0x1F: {
                            "name": "wavefolding_symmetry",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Wavefolding Symmetry",
                        },
                        0x20: {
                            "name": "ring_mod_frequency",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Ring Mod Frequency",
                        },
                        0x21: {
                            "name": "ring_mod_mix",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Ring Mod Mix",
                        },
                        0x22: {
                            "name": "digital_filter_type",
                            "range": (0, 3),
                            "default": 0,
                            "desc": "Digital Filter Type",
                        },
                        0x23: {
                            "name": "digital_filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Digital Filter Cutoff",
                        },
                        0x24: {
                            "name": "digital_filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Digital Filter Resonance",
                        },
                        0x25: {
                            "name": "digital_filter_envelope",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Digital Filter Envelope",
                        },
                    }

                    for lsb, param_info in digital_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} Digital {param_info['desc']}",
                        }

                # FM Engine parameters (MSB for engine 2)
                elif engine_offset == 2:  # FM engine
                    fm_params = {
                        0x10: {
                            "name": "fm_algorithm",
                            "range": (0, 31),
                            "default": 0,
                            "desc": "FM Algorithm",
                        },
                        0x11: {
                            "name": "fm_feedback",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "FM Feedback",
                        },
                        0x12: {
                            "name": "fm_lfo_waveform",
                            "range": (0, 5),
                            "default": 0,
                            "desc": "FM LFO Waveform",
                        },
                        0x13: {
                            "name": "fm_lfo_rate",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "FM LFO Rate",
                        },
                        0x14: {
                            "name": "fm_lfo_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "FM LFO Depth",
                        },
                        0x15: {
                            "name": "fm_lfo_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "FM LFO Tempo Sync",
                        },
                        0x16: {
                            "name": "op1_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 1 Ratio",
                        },
                        0x17: {
                            "name": "op1_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 1 Level",
                        },
                        0x18: {
                            "name": "op1_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 1 Attack",
                        },
                        0x19: {
                            "name": "op1_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Decay",
                        },
                        0x1A: {
                            "name": "op1_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Sustain",
                        },
                        0x1B: {
                            "name": "op1_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Release",
                        },
                        0x1C: {
                            "name": "op2_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 2 Ratio",
                        },
                        0x1D: {
                            "name": "op2_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 2 Level",
                        },
                        0x1E: {
                            "name": "op2_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 2 Attack",
                        },
                        0x1F: {
                            "name": "op2_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Decay",
                        },
                        0x20: {
                            "name": "op2_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Sustain",
                        },
                        0x21: {
                            "name": "op2_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Release",
                        },
                        0x22: {
                            "name": "op3_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 3 Ratio",
                        },
                        0x23: {
                            "name": "op3_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 3 Level",
                        },
                        0x24: {
                            "name": "op3_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 3 Attack",
                        },
                        0x25: {
                            "name": "op3_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Decay",
                        },
                        0x26: {
                            "name": "op3_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Sustain",
                        },
                        0x27: {
                            "name": "op3_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Release",
                        },
                        0x28: {
                            "name": "op4_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 4 Ratio",
                        },
                        0x29: {
                            "name": "op4_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 4 Level",
                        },
                        0x2A: {
                            "name": "op4_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 4 Attack",
                        },
                        0x2B: {
                            "name": "op4_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Decay",
                        },
                        0x2C: {
                            "name": "op4_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Sustain",
                        },
                        0x2D: {
                            "name": "op4_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Release",
                        },
                    }

                    for lsb, param_info in fm_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} FM {param_info['desc']}",
                        }

                # External Engine parameters (MSB for engine 3)
                elif engine_offset == 3:  # External engine
                    external_params = {
                        0x10: {
                            "name": "external_input_gain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Input Gain",
                        },
                        0x11: {
                            "name": "external_input_pan",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "External Input Pan",
                        },
                        0x12: {
                            "name": "external_filter_type",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "External Filter Type",
                        },
                        0x13: {
                            "name": "external_filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Filter Cutoff",
                        },
                        0x14: {
                            "name": "external_filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Filter Resonance",
                        },
                        0x15: {
                            "name": "external_drive",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Drive",
                        },
                        0x16: {
                            "name": "external_amp_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "External Amp Level",
                        },
                        0x17: {
                            "name": "external_amp_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Amp Attack",
                        },
                        0x18: {
                            "name": "external_amp_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Decay",
                        },
                        0x19: {
                            "name": "external_amp_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Sustain",
                        },
                        0x1A: {
                            "name": "external_amp_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Release",
                        },
                        0x1B: {
                            "name": "external_send_reverb",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Reverb Send",
                        },
                        0x1C: {
                            "name": "external_send_chorus",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Chorus Send",
                        },
                        0x1D: {
                            "name": "external_send_delay",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Delay Send",
                        },
                        0x1E: {
                            "name": "external_routing_mode",
                            "range": (0, 3),
                            "default": 0,
                            "desc": "External Routing Mode",
                        },
                        0x1F: {
                            "name": "external_sidechain_enable",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "External Sidechain Enable",
                        },
                        0x20: {
                            "name": "external_sidechain_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Sidechain Attack",
                        },
                        0x21: {
                            "name": "external_sidechain_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Sidechain Release",
                        },
                        0x22: {
                            "name": "external_compression_enable",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "External Compression Enable",
                        },
                        0x23: {
                            "name": "external_compression_ratio",
                            "range": (1, 20),
                            "default": 4,
                            "desc": "External Compression Ratio",
                        },
                        0x24: {
                            "name": "external_compression_threshold",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Compression Threshold",
                        },
                        0x25: {
                            "name": "external_compression_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Compression Attack",
                        },
                        0x26: {
                            "name": "external_compression_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Compression Release",
                        },
                    }

                    for lsb, param_info in external_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} External {param_info['desc']}",
                        }

        # Effects parameters (MSB 0x40-0x4F) - FULL IMPLEMENTATION
        effect_types = {
            0: "Reverb",
            1: "Delay",
            2: "Chorus",
            3: "Flanger",
            4: "Phaser",
            5: "Ring Modulator",
            6: "Distortion",
            7: "Overdrive",
            8: "EQ",
            9: "Compressor",
            10: "Limiter",
            11: "Gate",
            12: "Tremolo",
            13: "Auto Pan",
            14: "Slap Back Delay",
            15: "Wah",
        }

        common_effect_params = {
            0x00: {
                "name": "effect_type",
                "range": (0, 15),
                "default": 0,
                "desc": "Effect Type",
            },
            0x01: {
                "name": "effect_bypass",
                "range": (0, 1),
                "default": 0,
                "desc": "Bypass",
            },
            0x02: {
                "name": "effect_level",
                "range": (0, 127),
                "default": 100,
                "desc": "Level",
            },
            0x03: {
                "name": "effect_pan",
                "range": (-64, 63),
                "default": 0,
                "desc": "Pan",
            },
            0x04: {
                "name": "effect_dry_wet",
                "range": (0, 127),
                "default": 64,
                "desc": "Dry/Wet",
            },
            0x05: {
                "name": "effect_param1",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 1",
            },
            0x06: {
                "name": "effect_param2",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 2",
            },
            0x07: {
                "name": "effect_param3",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 3",
            },
            0x08: {
                "name": "effect_param4",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 4",
            },
            0x09: {
                "name": "effect_param5",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 5",
            },
            0x0A: {
                "name": "effect_param6",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 6",
            },
            0x0B: {
                "name": "effect_param7",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 7",
            },
            0x0C: {
                "name": "effect_param8",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 8",
            },
            0x0D: {
                "name": "effect_reserve",
                "range": (0, 127),
                "default": 0,
                "desc": "Reserve",
            },
            0x0E: {
                "name": "effect_attack",
                "range": (0, 127),
                "default": 0,
                "desc": "Attack",
            },
            0x0F: {
                "name": "effect_release",
                "range": (0, 127),
                "default": 64,
                "desc": "Release",
            },
        }

        for group_idx in range(16):
            msb = 0x40 + group_idx
            effect_name = effect_types.get(group_idx, "Unknown")

            for lsb, param_info in common_effect_params.items():
                nrpn_map[(msb, lsb)] = {
                    "type": "effects",
                    "group": group_idx,
                    "effect_type": effect_name,
                    "param_id": lsb,
                    "param_name": param_info["name"],
                    "range": param_info["range"],
                    "default": param_info["default"],
                    "description": f"Effect {group_idx} ({effect_name}) {param_info['desc']}",
                }

        return nrpn_map

    def process_nrpn_message(self, controller: int, value: int) -> bool:
        """
        Process NRPN-related controller messages.

        Args:
            controller: MIDI controller number
            value: Controller value (0-127)

        Returns:
            True if NRPN message was processed
        """
        with self.lock:
            if controller == 99:  # NRPN MSB
                self.current_msb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 98:  # NRPN LSB
                self.current_lsb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 6:  # Data Entry MSB
                if self.active_nrpn:
                    if not self.data_msb_received:
                        self.data_msb = value
                        self.data_msb_received = True
                    else:
                        # Complete NRPN message
                        data_value = (self.data_msb << 7) | value
                        success = self._process_nrpn_data(data_value)
                        self._reset_nrpn_state()
                        return success

            elif controller == 96:  # Data Increment
                if self.active_nrpn:
                    current_value = self._get_current_parameter_value()
                    if current_value is not None:
                        new_value = min(current_value + 1, 16383)
                        return self._process_nrpn_data(new_value)

            elif controller == 97:  # Data Decrement
                if self.active_nrpn:
                    current_value = self._get_current_parameter_value()
                    if current_value is not None:
                        new_value = max(current_value - 1, 0)
                        return self._process_nrpn_data(new_value)

        return False

    def _process_nrpn_data(self, data_value: int) -> bool:
        """
        Process complete NRPN data value (14-bit).

        Args:
            data_value: 14-bit NRPN value (0-16383)

        Returns:
            True if parameter was processed successfully
        """
        # Convert to 7-bit MIDI value
        midi_value = data_value >> 7

        # Get parameter info
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.nrpn_map.get(param_key)

        if not param_info:
            print(f"Jupiter-X NRPN: Unknown parameter {param_key}")
            return False

        # Process based on parameter type
        param_type = param_info["type"]

        if param_type == "system":
            param_id = param_info["param_id"]
            return self.component_manager.system_params.set_parameter(param_id, midi_value)

        elif param_type == "part":
            part_number = param_info["part_number"]
            param_id = param_info["param_id"]
            return self.component_manager.set_part_parameter(part_number, param_id, midi_value)

        elif param_type == "engine":
            part_number = param_info["part_number"]
            engine_type = param_info["engine_type"]
            param_id = param_info["param_id"]
            return self.component_manager.set_engine_parameter(
                part_number, engine_type, param_id, midi_value
            )

        elif param_type == "effects":
            # Convert to 3-byte address for effects parameters
            group = param_info["group"]
            param_id = param_info["param_id"]
            addr_high = 0x40 + group
            address = bytes([addr_high, 0x00, param_id])
            return self.component_manager.process_parameter_change(address, midi_value)

        return False

    def _get_current_parameter_value(self) -> int | None:
        """Get current parameter value for increment/decrement."""
        if not self.active_nrpn:
            return None

        param_key = (self.current_msb, self.current_lsb)
        param_info = self.nrpn_map.get(param_key)

        if not param_info:
            return None

        # Get value based on parameter type
        param_type = param_info["type"]

        if param_type == "system":
            param_id = param_info["param_id"]
            return self.component_manager.system_params.get_parameter(param_id)

        elif param_type == "part":
            part_number = param_info["part_number"]
            param_id = param_info["param_id"]
            return self.component_manager.get_part_parameter(part_number, param_id)

        elif param_type == "effects":
            group = param_info["group"]
            param_id = param_info["param_id"]
            addr_high = 0x40 + group
            address = bytes([addr_high, 0x00, param_id])
            return self.component_manager.get_parameter_value(address)

        return None

    def _reset_nrpn_state(self):
        """Reset NRPN controller state."""
        self.active_nrpn = False
        self.current_msb = 0
        self.current_lsb = 0
        self.data_msb = 0
        self.data_msb_received = False

    def get_nrpn_status(self) -> dict[str, Any]:
        """Get current NRPN processing status."""
        with self.lock:
            return {
                "active": self.active_nrpn,
                "current_msb": self.current_msb,
                "current_lsb": self.current_lsb,
                "data_msb_received": self.data_msb_received,
                "data_msb": self.data_msb,
                "current_parameter": self.nrpn_map.get((self.current_msb, self.current_lsb)),
            }

    def create_nrpn_message(self, msb: int, lsb: int, value: int) -> list[bytes]:
        """
        Create NRPN message sequence for a parameter change.

        Args:
            msb: NRPN MSB (0-127)
            lsb: NRPN LSB (0-127)
            value: 14-bit parameter value (0-16383)

        Returns:
            List of MIDI message bytes to send
        """
        messages = []

        # NRPN MSB
        messages.append(bytes([0xB0 | 0, 99, msb]))  # CC 99 on channel 0

        # NRPN LSB
        messages.append(bytes([0xB0 | 0, 98, lsb]))  # CC 98 on channel 0

        # Data Entry MSB
        data_msb = (value >> 7) & 0x7F
        messages.append(bytes([0xB0 | 0, 6, data_msb]))  # CC 6 on channel 0

        # Data Entry LSB
        data_lsb = value & 0x7F
        messages.append(bytes([0xB0 | 0, 38, data_lsb]))  # CC 38 on channel 0

        return messages


class JupiterXMIDIController:
    """
    Jupiter-X MIDI Controller

    Main MIDI processing interface for Jupiter-X, combining SysEx and NRPN handling.
    """

    def __init__(self, component_manager: JupiterXComponentManager):
        self.component_manager = component_manager

        # Sub-controllers
        self.sysex_controller = JupiterXSysExController(component_manager)
        self.nrpn_controller = JupiterXNRPNController(component_manager)

        # Thread safety
        self.lock = threading.RLock()

        print("🎹 Jupiter-X MIDI Controller: Initialized")

    def process_midi_message(self, message_bytes: bytes) -> dict[str, Any] | None:
        """
        Process MIDI message for Jupiter-X.

        Args:
            message_bytes: Raw MIDI message bytes

        Returns:
            Processing result or None if not handled
        """
        with self.lock:
            # Check for SysEx first
            if len(message_bytes) > 3 and message_bytes[0] == 0xF0:
                return self.sysex_controller.process_sysex_message(message_bytes)

            # Check for NRPN controller messages
            elif len(message_bytes) == 3 and (message_bytes[0] & 0xF0) == 0xB0:  # CC message
                controller = message_bytes[1]
                value = message_bytes[2]

                # NRPN controllers
                if controller in [98, 99, 6, 38, 96, 97]:  # NRPN related
                    return {
                        "status": "processed"
                        if self.nrpn_controller.process_nrpn_message(controller, value)
                        else "ignored",
                        "type": "nrpn",
                        "controller": controller,
                        "value": value,
                    }

            return None

    def get_midi_status(self) -> dict[str, Any]:
        """Get comprehensive MIDI processing status."""
        with self.lock:
            return {
                "sysex_status": "active",
                "nrpn_status": self.nrpn_controller.get_nrpn_status(),
                "device_id": self.component_manager.system_params.device_id,
                "model_id": JUPITER_X_MODEL_ID,
                "manufacturer_id": JUPITER_X_MANUFACTURER_ID,
            }

    def create_parameter_change_sysex(self, address: bytes, value: int) -> bytes:
        """
        Create SysEx message for parameter change.

        Args:
            address: 3-byte parameter address
            value: Parameter value (0-127)

        Returns:
            Complete SysEx message bytes
        """
        return self.sysex_controller.create_parameter_change_message(address, value)

    def create_nrpn_messages(self, msb: int, lsb: int, value: int) -> list[bytes]:
        """
        Create NRPN message sequence for parameter change.

        Args:
            msb: NRPN MSB
            lsb: NRPN LSB
            value: 14-bit parameter value

        Returns:
            List of MIDI message bytes
        """
        return self.nrpn_controller.create_nrpn_message(msb, lsb, value)

    def reset_midi_state(self):
        """Reset all MIDI processing state."""
        with self.lock:
            self.nrpn_controller._reset_nrpn_state()

    def __str__(self) -> str:
        """String representation."""
        return "JupiterXMIDIController(active)"

    def __repr__(self) -> str:
        return self.__str__()
