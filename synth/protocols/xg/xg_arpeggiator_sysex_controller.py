"""
Yamaha Arpeggiator SYSEX Controller

SYSEX command processing for Yamaha Motif arpeggiator control.
Implements the complete SYSEX protocol for arpeggiator management.

Copyright (c) 2025
"""

from __future__ import annotations

import threading
from typing import Any


class YamahaArpeggiatorSysexController:
    """
    Yamaha Arpeggiator SYSEX Command Controller

    Handles SYSEX commands for arpeggiator control following Yamaha Motif
    protocol specifications. Processes real-time arpeggiator parameter changes
    and bulk operations.
    """

    # SYSEX Command IDs for Arpeggiator
    CMD_ARP_SWITCH = 0x0A  # Arpeggiator On/Off
    CMD_ARP_PATTERN = 0x0B  # Pattern Select
    CMD_ARP_HOLD = 0x0C  # Hold Mode
    CMD_ARP_VELOCITY = 0x0D  # Velocity Mode
    CMD_ARP_OCTAVE = 0x0E  # Octave Range
    CMD_ARP_GATE = 0x0F  # Gate Time
    CMD_ARP_SWING = 0x10  # Swing Amount

    # Bulk operations
    CMD_ARP_BULK_DUMP = 0x11  # Bulk Dump Request
    CMD_ARP_BULK_DATA = 0x12  # Bulk Data Transfer

    def __init__(self, arpeggiator_engine):
        """
        Initialize SYSEX controller.

        Args:
            arpeggiator_engine: YamahaArpeggiatorEngine instance
        """
        self.arpeggiator_engine = arpeggiator_engine
        self.lock = threading.RLock()

        # SYSEX command routing table
        self.command_handlers = {
            self.CMD_ARP_SWITCH: self._handle_arp_switch,
            self.CMD_ARP_PATTERN: self._handle_arp_pattern,
            self.CMD_ARP_HOLD: self._handle_arp_hold,
            self.CMD_ARP_VELOCITY: self._handle_arp_velocity,
            self.CMD_ARP_OCTAVE: self._handle_arp_octave,
            self.CMD_ARP_GATE: self._handle_arp_gate,
            self.CMD_ARP_SWING: self._handle_arp_swing,
            self.CMD_ARP_BULK_DUMP: self._handle_bulk_dump,
            self.CMD_ARP_BULK_DATA: self._handle_bulk_data,
        }

        # Bulk transfer state
        self.bulk_transfer_active = False
        self.bulk_data_buffer = bytearray()
        self.bulk_expected_size = 0

        print("🎹 Yamaha Arpeggiator SYSEX Controller: Initialized")

    def process_sysex_message(self, data: bytes) -> dict[str, Any] | None:
        """
        Process SYSEX message for arpeggiator control.

        Args:
            data: SYSEX message data (without F0/F7)

        Returns:
            Processing result or None if not handled
        """
        try:
            # Validate Yamaha Motif arpeggiator SYSEX format
            # F0 43 [dev] 7E [command] [data...] [checksum] F7
            if len(data) < 6:
                return None

            # Check Yamaha manufacturer ID (0x43) and model ID (0x7E for arpeggiator)
            if data[0] != 0x43 or data[2] != 0x7E:
                return None

            device_id = data[1]
            command = data[3]

            # Extract data portion (skip manufacturer, device, model, command)
            command_data = data[4:-1]  # Exclude checksum

            # Route to appropriate handler
            handler = self.command_handlers.get(command)
            if handler:
                return handler(device_id, command_data)
            else:
                print(f"⚠️  Unknown arpeggiator SYSEX command: {command:02X}")
                return None

        except Exception as e:
            print(f"❌ Arpeggiator SYSEX processing error: {e}")
            return None

    def _handle_arp_switch(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle arpeggiator on/off: F0 43 [dev] 7E 0A [part] [on/off] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        enabled = data[1] > 0

        if self.arpeggiator_engine.enable_arpeggiator(part, enabled):
            return {
                "type": "arpeggiator_control",
                "command": "switch",
                "part": part,
                "enabled": enabled,
            }
        return None

    def _handle_arp_pattern(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle pattern select: F0 43 [dev] 7E 0B [part] [pattern_msb] [pattern_lsb] [checksum] F7"""
        if len(data) < 3:
            return None

        part = data[0]
        pattern_msb = data[1]
        pattern_lsb = data[2]
        pattern_id = (pattern_msb << 7) | pattern_lsb

        if self.arpeggiator_engine.set_pattern(part, pattern_id):
            return {
                "type": "arpeggiator_control",
                "command": "pattern_select",
                "part": part,
                "pattern_id": pattern_id,
            }
        return None

    def _handle_arp_hold(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle hold mode: F0 43 [dev] 7E 0C [part] [hold_mode] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        hold_mode = data[1] > 0

        if self.arpeggiator_engine.set_arpeggiator_parameter(part, "hold_mode", hold_mode):
            return {
                "type": "arpeggiator_control",
                "command": "hold_mode",
                "part": part,
                "hold_mode": hold_mode,
            }
        return None

    def _handle_arp_velocity(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle velocity mode: F0 43 [dev] 7E 0D [part] [velocity_mode] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        velocity_mode = data[1]  # 0=Original, 1=Fixed, 2=Accent

        if self.arpeggiator_engine.set_arpeggiator_parameter(part, "velocity_mode", velocity_mode):
            return {
                "type": "arpeggiator_control",
                "command": "velocity_mode",
                "part": part,
                "velocity_mode": velocity_mode,
            }
        return None

    def _handle_arp_octave(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle octave range: F0 43 [dev] 7E 0E [part] [octave_range] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        octave_range = data[1] + 1  # 0=1 octave, 1=2 octaves, etc.

        if self.arpeggiator_engine.set_arpeggiator_parameter(part, "octave_range", octave_range):
            return {
                "type": "arpeggiator_control",
                "command": "octave_range",
                "part": part,
                "octave_range": octave_range,
            }
        return None

    def _handle_arp_gate(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle gate time: F0 43 [dev] 7E 0F [part] [gate_time] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        gate_time = data[1] / 127.0  # Convert to 0.0-1.0 range

        if self.arpeggiator_engine.set_arpeggiator_parameter(part, "gate_time", gate_time):
            return {
                "type": "arpeggiator_control",
                "command": "gate_time",
                "part": part,
                "gate_time": gate_time,
            }
        return None

    def _handle_arp_swing(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle swing amount: F0 43 [dev] 7E 10 [part] [swing] [checksum] F7"""
        if len(data) < 2:
            return None

        part = data[0]
        swing_amount = data[1] / 127.0  # Convert to 0.0-1.0 range

        if self.arpeggiator_engine.set_arpeggiator_parameter(part, "swing_amount", swing_amount):
            return {
                "type": "arpeggiator_control",
                "command": "swing_amount",
                "part": part,
                "swing_amount": swing_amount,
            }
        return None

    def _handle_bulk_dump(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle bulk dump request: F0 43 [dev] 7E 11 [type] [checksum] F7"""
        if len(data) < 1:
            return None

        dump_type = data[0]

        # Start bulk transfer
        self.bulk_transfer_active = True
        self.bulk_data_buffer.clear()

        # Determine expected size based on dump type
        if dump_type == 0:  # All arpeggiator settings
            self.bulk_expected_size = 16 * 16  # 16 parts × 16 parameters
        elif dump_type == 1:  # Pattern library
            self.bulk_expected_size = 1000 * 64  # Rough estimate
        else:
            self.bulk_expected_size = 1024  # Default

        return {
            "type": "bulk_operation",
            "command": "bulk_dump_request",
            "dump_type": dump_type,
            "expected_size": self.bulk_expected_size,
        }

    def _handle_bulk_data(self, device_id: int, data: bytes) -> dict[str, Any] | None:
        """Handle bulk data transfer: F0 43 [dev] 7E 12 [data...] [checksum] F7"""
        if not self.bulk_transfer_active:
            return None

        # Append data to buffer
        self.bulk_data_buffer.extend(data)

        # Check if transfer is complete
        if len(self.bulk_data_buffer) >= self.bulk_expected_size:
            # Process complete bulk data
            result = self._process_bulk_data(self.bulk_data_buffer)

            # Reset bulk transfer state
            self.bulk_transfer_active = False
            self.bulk_data_buffer.clear()
            self.bulk_expected_size = 0

            return result

        return {
            "type": "bulk_operation",
            "command": "bulk_data_chunk",
            "received_size": len(self.bulk_data_buffer),
            "expected_size": self.bulk_expected_size,
        }

    def _process_bulk_data(self, data: bytes) -> dict[str, Any] | None:
        """Process complete bulk data transfer."""
        try:
            # Yamaha Motif Arpeggiator Bulk Data Format
            # Format: [type][data...]
            # Type 0: All arpeggiator settings for all parts
            # Type 1: Pattern library data

            if len(data) < 1:
                return None

            bulk_type = data[0]
            bulk_payload = data[1:]

            if bulk_type == 0:
                # All arpeggiator settings (16 parts × parameters per part)
                return self._process_bulk_arpeggiator_settings(bulk_payload)
            elif bulk_type == 1:
                # Pattern library data
                return self._process_bulk_pattern_library(bulk_payload)
            else:
                print(f"⚠️  Unknown bulk data type: {bulk_type}")
                return None

        except Exception as e:
            print(f"❌ Bulk data processing error: {e}")
            return None

    def _process_bulk_arpeggiator_settings(self, data: bytes) -> dict[str, Any] | None:
        """Process bulk arpeggiator settings for all parts."""
        try:
            # Expected format: 16 parts × 16 parameters per part = 256 bytes
            if len(data) != 256:
                print(f"⚠️  Invalid bulk settings size: {len(data)} (expected 256)")
                return None

            parts_processed = 0
            for part in range(16):
                part_offset = part * 16
                part_data = data[part_offset : part_offset + 16]

                # Apply settings for this part
                if self._apply_bulk_part_settings(part, part_data):
                    parts_processed += 1

            print(f"🎹 Arpeggiator bulk settings loaded: {parts_processed}/16 parts")
            return {
                "type": "bulk_operation",
                "command": "bulk_data_complete",
                "data_size": len(data),
                "parts_processed": parts_processed,
                "operation": "arpeggiator_settings",
            }

        except Exception as e:
            print(f"❌ Bulk arpeggiator settings processing error: {e}")
            return None

    def _apply_bulk_part_settings(self, part: int, part_data: bytes) -> bool:
        """Apply bulk settings for a single part."""
        try:
            if len(part_data) != 16:
                return False

            # Decode part settings from bulk data
            # Format: [switch, pattern_msb, pattern_lsb, hold, velocity, octave, gate, swing, ...]
            settings = {
                "arp_switch": part_data[0] > 0,
                "pattern_msb": part_data[1],
                "pattern_lsb": part_data[2],
                "hold_mode": part_data[3] > 0,
                "velocity_mode": part_data[4],
                "octave_range": part_data[5] + 1,  # 0=1 octave, 1=2 octaves, etc.
                "gate_time": part_data[6] / 127.0,
                "swing_amount": part_data[7] / 127.0,
                "velocity_rate": part_data[8],
                "accent_velocity": part_data[9],
                "arp_tempo": (part_data[10] << 7) | part_data[11],  # 14-bit tempo
                "pattern_length": part_data[12] + 1,
                "key_mode": part_data[13],
                "voice_assign_mode": part_data[14],
                "motif_retrigger": part_data[15] > 0,
            }

            # Apply pattern selection
            pattern_id = (settings["pattern_msb"] << 7) | settings["pattern_lsb"]
            self.arpeggiator_engine.set_pattern(part, pattern_id)

            # Apply other settings
            for param_name, value in settings.items():
                if param_name not in ["pattern_msb", "pattern_lsb"]:
                    self.arpeggiator_engine.set_arpeggiator_parameter(part, param_name, value)

            # Enable/disable arpeggiator based on switch
            self.arpeggiator_engine.enable_arpeggiator(part, settings["arp_switch"])

            return True

        except Exception as e:
            print(f"❌ Error applying bulk settings for part {part}: {e}")
            return False

    def _process_bulk_pattern_library(self, data: bytes) -> dict[str, Any] | None:
        """Process bulk pattern library data."""
        try:
            # Parse pattern library bulk data
            # Format: header (4 bytes) + patterns (variable) + checksum
            result = {
                "type": "bulk_operation",
                "command": "bulk_data_complete",
                "data_size": len(data),
                "operation": "pattern_library",
                "status": "processed",
                "patterns": [],
            }

            # Parse pattern data if enough bytes
            offset = 0
            while offset + 8 <= len(data):
                # Pattern header: ID (2), length (2), type (1), flags (1), reserved (2)
                pattern_id = data[offset] << 8 | data[offset + 1]
                pattern_len = data[offset + 2] << 8 | data[offset + 3]
                pattern_type = data[offset + 4]

                offset += 8

                if offset + pattern_len <= len(data):
                    pattern_data = data[offset : offset + pattern_len]
                    result["patterns"].append(
                        {
                            "id": pattern_id,
                            "length": pattern_len,
                            "type": pattern_type,
                            "data": pattern_data.hex()[:32],  # Store truncated hex
                        }
                    )
                    offset += pattern_len
                else:
                    break

            if not result["patterns"]:
                result["status"] = "acknowledged"

            return result

        except Exception as e:
            print(f"❌ Bulk pattern library processing error: {e}")
            return None

    def create_bulk_dump_request(self, dump_type: int, device_id: int = 0x10) -> bytes:
        """Create bulk dump request SYSEX message."""
        command = self.CMD_ARP_BULK_DUMP
        data = bytes([0x43, device_id, 0x7E, command, dump_type])
        return self._create_sysex_message(data)

    def create_bulk_data_message(
        self, bulk_type: int, bulk_data: bytes, device_id: int = 0x10
    ) -> bytes:
        """Create bulk data transfer SYSEX message."""
        command = self.CMD_ARP_BULK_DATA
        # Limit bulk data to reasonable size (Yamaha typically limits to ~256 bytes per message)
        max_data_size = 240  # Leave room for headers and checksum
        if len(bulk_data) > max_data_size:
            bulk_data = bulk_data[:max_data_size]

        data = bytes([0x43, device_id, 0x7E, command, bulk_type]) + bulk_data
        return self._create_sysex_message(data)

    def create_arpeggiator_bulk_dump(self, device_id: int = 0x10) -> bytes:
        """Create complete arpeggiator settings bulk dump."""
        # Collect settings for all 16 parts
        bulk_data = bytearray()

        for part in range(16):
            # Get current settings for this part
            status = self.arpeggiator_engine.get_arpeggiator_status(part)
            if status:
                # Encode part settings into bulk format (16 bytes per part)
                part_settings = bytearray(16)

                # Basic settings
                part_settings[0] = 1 if status.get("enabled", False) else 0
                part_settings[1] = (status.get("current_pattern", 0) >> 7) & 0x7F  # MSB
                part_settings[2] = status.get("current_pattern", 0) & 0x7F  # LSB
                part_settings[3] = 1 if status.get("hold_mode", False) else 0
                part_settings[4] = status.get("velocity_mode", 0)
                part_settings[5] = max(0, status.get("octave_range", 1) - 1)
                part_settings[6] = int(status.get("gate_time", 0.8) * 127.0) & 0x7F
                part_settings[7] = int(status.get("swing_amount", 0.0) * 127.0) & 0x7F

                # Extended settings from status
                part_settings[8] = status.get("fixed_velocity", 0) & 0x7F
                part_settings[9] = status.get("accent_velocity", 127) & 0x7F
                tempo = int(status.get("bpm", 120))
                part_settings[10] = (tempo >> 7) & 0x7F  # Tempo MSB
                part_settings[11] = tempo & 0x7F  # Tempo LSB
                part_settings[12] = status.get("pattern_length", 0) & 0x7F
                part_settings[13] = status.get("key_mode", 0) & 0x7F
                part_settings[14] = status.get("voice_assign_mode", 0) & 0x7F
                part_settings[15] = 1 if status.get("motif_retrigger", False) else 0

                bulk_data.extend(part_settings)
            else:
                # Default settings for part with no status
                bulk_data.extend(bytearray(16))

        # Create bulk data message (type 0 = arpeggiator settings)
        return self.create_bulk_data_message(0, bulk_data, device_id)

    def get_bulk_dump_capabilities(self) -> dict[str, Any]:
        """Get bulk dump capabilities information."""
        return {
            "supported_dump_types": [
                {
                    "type": 0,
                    "name": "Arpeggiator Settings",
                    "description": "All arpeggiator settings for 16 parts",
                },
                {"type": 1, "name": "Pattern Library", "description": "User pattern library data"},
            ],
            "max_message_size": 256,
            "parts_per_dump": 16,
            "bytes_per_part": 16,
            "total_settings_size": 256,
        }

    def create_arp_switch_message(self, part: int, enabled: bool, device_id: int = 0x10) -> bytes:
        """Create arpeggiator switch SYSEX message."""
        command = self.CMD_ARP_SWITCH
        data = bytes([0x43, device_id, 0x7E, command, part, 1 if enabled else 0])
        return self._create_sysex_message(data)

    def create_arp_pattern_message(
        self, part: int, pattern_id: int, device_id: int = 0x10
    ) -> bytes:
        """Create pattern select SYSEX message."""
        command = self.CMD_ARP_PATTERN
        pattern_msb = (pattern_id >> 7) & 0x7F
        pattern_lsb = pattern_id & 0x7F
        data = bytes([0x43, device_id, 0x7E, command, part, pattern_msb, pattern_lsb])
        return self._create_sysex_message(data)

    def create_arp_hold_message(self, part: int, hold_mode: bool, device_id: int = 0x10) -> bytes:
        """Create hold mode SYSEX message."""
        command = self.CMD_ARP_HOLD
        data = bytes([0x43, device_id, 0x7E, command, part, 1 if hold_mode else 0])
        return self._create_sysex_message(data)

    def create_arp_velocity_message(
        self, part: int, velocity_mode: int, device_id: int = 0x10
    ) -> bytes:
        """Create velocity mode SYSEX message."""
        command = self.CMD_ARP_VELOCITY
        data = bytes([0x43, device_id, 0x7E, command, part, velocity_mode & 0x7F])
        return self._create_sysex_message(data)

    def create_arp_octave_message(
        self, part: int, octave_range: int, device_id: int = 0x10
    ) -> bytes:
        """Create octave range SYSEX message."""
        command = self.CMD_ARP_OCTAVE
        data = bytes([0x43, device_id, 0x7E, command, part, (octave_range - 1) & 0x7F])
        return self._create_sysex_message(data)

    def create_arp_gate_message(self, part: int, gate_time: float, device_id: int = 0x10) -> bytes:
        """Create gate time SYSEX message."""
        command = self.CMD_ARP_GATE
        gate_value = int(gate_time * 127.0) & 0x7F
        data = bytes([0x43, device_id, 0x7E, command, part, gate_value])
        return self._create_sysex_message(data)

    def create_arp_swing_message(
        self, part: int, swing_amount: float, device_id: int = 0x10
    ) -> bytes:
        """Create swing amount SYSEX message."""
        command = self.CMD_ARP_SWING
        swing_value = int(swing_amount * 127.0) & 0x7F
        data = bytes([0x43, device_id, 0x7E, command, part, swing_value])
        return self._create_sysex_message(data)

    def _create_sysex_message(self, data: bytes) -> bytes:
        """Create complete SYSEX message with checksum."""
        # Calculate checksum (Yamaha format)
        checksum = 0
        for byte in data:
            checksum += byte
        checksum = (checksum & 0x7F) ^ 0x7F

        # Create full message: F0 [data] [checksum] F7
        return bytes([0xF0]) + data + bytes([checksum, 0xF7])

    def get_supported_commands(self) -> list[dict[str, Any]]:
        """Get list of supported SYSEX commands."""
        return [
            {
                "command": self.CMD_ARP_SWITCH,
                "name": "Arpeggiator Switch",
                "description": "Enable/disable arpeggiator for a part",
            },
            {
                "command": self.CMD_ARP_PATTERN,
                "name": "Pattern Select",
                "description": "Select arpeggio pattern for a part",
            },
            {
                "command": self.CMD_ARP_HOLD,
                "name": "Hold Mode",
                "description": "Set hold mode for arpeggiator",
            },
            {
                "command": self.CMD_ARP_VELOCITY,
                "name": "Velocity Mode",
                "description": "Set velocity processing mode",
            },
            {
                "command": self.CMD_ARP_OCTAVE,
                "name": "Octave Range",
                "description": "Set octave range for arpeggiation",
            },
            {
                "command": self.CMD_ARP_GATE,
                "name": "Gate Time",
                "description": "Set note duration within pattern",
            },
            {
                "command": self.CMD_ARP_SWING,
                "name": "Swing Amount",
                "description": "Set timing swing amount",
            },
        ]

    def __str__(self) -> str:
        """String representation."""
        return "YamahaArpeggiatorSysexController()"

    def __repr__(self) -> str:
        return self.__str__()
