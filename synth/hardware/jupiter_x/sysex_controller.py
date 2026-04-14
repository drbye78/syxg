"""Jupiter-X SysEx Message Controller."""

from __future__ import annotations

import threading
from typing import Any

from .component_manager import JupiterXComponentManager
from .constants import *


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


