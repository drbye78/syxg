"""
XG System Exclusive (SYSEX) Controller

Handles XG MIDI System Exclusive messages (F0 43 [device] 4C ... F7).
Provides complete XG SYSEX message parsing, validation, and processing.

XG SYSEX Format: F0 43 [device] 4C [model] [command] [data...] F7

Copyright (c) 2025
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading
import time


class XGSystemExclusiveController:
    """
    XG System Exclusive Controller

    Handles all XG MIDI System Exclusive messages for complete XG compliance.
    Processes F0 43 [device] 4C [model] [command] [data...] F7 messages.

    Key Features:
    - Complete XG SYSEX message parsing and validation
    - Device ID handling and filtering
    - Checksum verification for data integrity
    - Command routing to appropriate handlers
    - Error handling and recovery
    - Thread-safe operation for real-time use
    """

    # XG SYSEX Constants
    XG_MANUFACTURER_ID = 0x43  # Yamaha manufacturer ID
    XG_MODEL_ID = 0x4C         # XG model ID
    XG_SYSEX_HEADER = [0xF0, 0x43]  # F0 43

    # XG Command Codes
    XG_COMMANDS = {
        0x00: 'system_parameters',
        0x02: 'xg_system_on',
        0x03: 'xg_system_off',
        0x04: 'xg_reset',
        0x06: 'xg_dump_request',
        0x07: 'xg_bulk_dump',
        0x08: 'parameter_change',
        0x09: 'xg_dump',
        0x0A: 'bulk_dump',
        0x0C: 'bulk_dump_request',
        0x0E: 'master_tune',
        0x0F: 'master_transpose',
        0x10: 'xg_display_message',
        0x11: 'xg_led_control',
        0x12: 'xg_special_message',
    }

    # XG Parameter Addresses
    XG_PARAMETER_ADDRESSES = {
        # MSB 0: RPN Parameters (handled by RPN controller)
        0x0000: 'pitch_bend_range',
        0x0001: 'fine_tuning',
        0x0002: 'coarse_tuning',
        0x0003: 'tuning_program_select',
        0x0004: 'tuning_bank_select',
        0x0005: 'modulation_depth_range',

        # MSB 1-2: System Effects
        0x0100: 'reverb_type',
        0x0101: 'reverb_time',
        0x0102: 'reverb_hf_damping',
        0x0103: 'reverb_balance',
        0x0104: 'reverb_level',
        0x0200: 'chorus_type',
        0x0201: 'chorus_lfo_freq',
        0x0202: 'chorus_depth',
        0x0203: 'chorus_feedback',
        0x0204: 'chorus_send_level',

        # MSB 42-45: Multi-Part Setup
        0x2A00: 'voice_reserve_part_0',
        0x2A01: 'voice_reserve_part_1',
        # ... up to part 15
        0x2B00: 'part_mode_part_0',
        0x2B01: 'part_mode_part_1',
        # ... part modes
        0x2C00: 'part_level_part_0',
        0x2C01: 'part_level_part_1',
        # ... part levels
        0x2D00: 'part_pan_part_0',
        0x2D01: 'part_pan_part_1',
        # ... part pans

        # MSB 48-63: Drum Setup (selected examples)
        0x3000: 'drum_kit_select',
        0x3010: 'drum_note_pitch_offset',
        0x3020: 'drum_note_level_offset',
        0x3030: 'drum_note_decay_offset',
    }

    def __init__(self, device_id: int = 0x10, model_id: int = 0x4C):
        """
        Initialize XG SYSEX Controller.

        Args:
            device_id: XG device ID (0x00-0x7F, default 0x10)
            model_id: XG model ID (default 0x4C for XG)
        """
        self.device_id = device_id
        self.model_id = model_id
        self.lock = threading.RLock()

        # Message processing state
        self.message_buffer = []
        self.in_sysex_message = False
        self.current_message_data = []

        # Command handlers
        self.command_handlers = {
            0x00: self._handle_system_parameters,
            0x02: self._handle_xg_system_on,
            0x03: self._handle_xg_system_off,
            0x04: self._handle_xg_reset,
            0x06: self._handle_xg_dump_request,
            0x07: self._handle_xg_bulk_dump,
            0x08: self._handle_parameter_change,
            0x09: self._handle_xg_dump,
            0x0A: self._handle_bulk_dump,
            0x0C: self._handle_bulk_dump_request,
            0x0E: self._handle_master_tune,
            0x0F: self._handle_master_transpose,
            0x10: self._handle_display_message,
            0x11: self._handle_led_control,
            0x12: self._handle_special_message,
        }

        # Parameter storage (will integrate with main synthesizer)
        self.parameters = {}
        self._initialize_default_parameters()

        # Callbacks for integration with main synthesizer
        self.parameter_change_callback = None
        self.system_command_callback = None
        self.display_callback = None

        print("🎹 XG SYSEX CONTROLLER: Initialized")
        print(f"   Device ID: {self.device_id:02X}, Model ID: {self.model_id:02X}")

    def _initialize_default_parameters(self):
        """Initialize XG parameters to default values."""
        # System effect defaults
        self.parameters.update({
            'reverb_type': 0x01,      # Hall 1
            'reverb_time': 0.5,       # 0.3-30.0 seconds
            'reverb_hf_damping': 0.5, # 0.0-1.0
            'reverb_balance': 0.5,    # 0.0-1.0
            'reverb_level': 0.4,      # 0.0-1.0
            'chorus_type': 0x41,      # Chorus 1
            'chorus_lfo_freq': 0.4,   # Hz
            'chorus_depth': 0.6,      # 0.0-1.0
            'chorus_feedback': 0.3,   # -1.0 to 1.0
            'chorus_send_level': 0.3, # 0.0-1.0
        })

        # Multi-part defaults
        for part in range(16):
            self.parameters[f'voice_reserve_part_{part}'] = 8  # 8 voices default
            self.parameters[f'part_mode_part_{part}'] = 1      # Multi mode
            self.parameters[f'part_level_part_{part}'] = 1.0   # Full level
            self.parameters[f'part_pan_part_{part}'] = 0.0     # Center

        # Master settings
        self.parameters['master_tune'] = 0.0      # ±100 cents
        self.parameters['master_transpose'] = 0   # ±24 semitones

    def process_midi_data(self, data: bytes) -> list[dict[str, Any]]:
        """
        Process MIDI data stream for SYSEX messages.

        Args:
            data: Raw MIDI data bytes

        Returns:
            List of processed message dictionaries
        """
        processed_messages = []

        for byte in data:
            if byte == 0xF0:  # Start of SYSEX
                self.in_sysex_message = True
                self.current_message_data = [byte]
            elif byte == 0xF7:  # End of SYSEX
                if self.in_sysex_message:
                    self.current_message_data.append(byte)
                    message = self._process_sysex_message(self.current_message_data)
                    if message:
                        processed_messages.append(message)
                    self.in_sysex_message = False
                    self.current_message_data = []
            elif self.in_sysex_message:
                self.current_message_data.append(byte)

        return processed_messages

    def _process_sysex_message(self, message_data: list[int]) -> dict[str, Any] | None:
        """
        Process a complete SYSEX message.

        Args:
            message_data: Complete SYSEX message data

        Returns:
            Processed message dictionary or None if invalid
        """
        try:
            # Validate XG SYSEX format
            if len(message_data) < 6:  # Minimum XG message length
                return None

            if message_data[0] != 0xF0 or message_data[-1] != 0xF7:
                return None

            # Check XG manufacturer and model IDs
            if (len(message_data) >= 4 and
                message_data[1] == self.XG_MANUFACTURER_ID and
                message_data[3] == self.XG_MODEL_ID):

                device_id = message_data[2]

                # Device ID filtering (0x7F = all devices, or match our device)
                if device_id != 0x7F and device_id != self.device_id:
                    return None  # Message not for this device

                # Extract command and data
                command = message_data[4]
                data = message_data[5:-2]  # Exclude header, command, checksum, EOX

                # Validate checksum if present
                if len(message_data) >= 3:
                    calculated_checksum = self._calculate_checksum(message_data[1:-2])
                    received_checksum = message_data[-2]
                    if calculated_checksum != received_checksum:
                        print(f"⚠️ XG SYSEX: Checksum error (calculated: {calculated_checksum:02X}, received: {received_checksum:02X})")
                        return None

                # Process command
                return self._process_xg_command(command, data)

            return None  # Not an XG message

        except Exception as e:
            print(f"❌ XG SYSEX: Error processing message: {e}")
            return None

    def _process_xg_command(self, command: int, data: list[int]) -> dict[str, Any] | None:
        """
        Process XG command with data.

        Args:
            command: XG command byte
            data: Command data bytes

        Returns:
            Processed command result
        """
        command_name = self.XG_COMMANDS.get(command, f'unknown_{command:02X}')

        # Route to appropriate handler
        if command in self.command_handlers:
            try:
                result = self.command_handlers[command](data)
                if result:
                    result['command'] = command_name
                    result['raw_command'] = command
                    result['timestamp'] = time.time()
                    return result
            except Exception as e:
                print(f"❌ XG SYSEX: Error in {command_name} handler: {e}")
                return None
        else:
            print(f"⚠️ XG SYSEX: Unknown command {command:02X}")
            return None

        return None

    def _calculate_checksum(self, data: list[int]) -> int:
        """
        Calculate XG SYSEX checksum.

        Args:
            data: Data bytes to checksum

        Returns:
            Checksum byte
        """
        checksum = 0
        for byte in data:
            checksum += byte
        checksum = (checksum & 0x7F) ^ 0x7F  # XG checksum formula
        return checksum

    # XG Command Handlers

    def _handle_system_parameters(self, data: list[int]) -> dict[str, Any] | None:
        """Handle system parameter changes."""
        if len(data) < 3:
            return None

        # Extract parameter address (MSB, LSB) and value
        address_msb = data[0]
        address_lsb = data[1]
        value = data[2] if len(data) > 2 else 0

        parameter_address = (address_msb << 8) | address_lsb
        parameter_name = self.XG_PARAMETER_ADDRESSES.get(parameter_address, f'unknown_{parameter_address:04X}')

        # Update parameter
        self.parameters[parameter_name] = value

        # Notify callback
        if self.parameter_change_callback:
            self.parameter_change_callback(parameter_name, value)

        return {
            'type': 'system_parameter_change',
            'parameter': parameter_name,
            'address': parameter_address,
            'value': value
        }

    def _handle_xg_system_on(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG System ON command."""
        if self.system_command_callback:
            self.system_command_callback('xg_on')

        print("🎹 XG SYSEX: XG System ON")
        return {'type': 'system_command', 'command': 'xg_on'}

    def _handle_xg_system_off(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG System OFF command."""
        if self.system_command_callback:
            self.system_command_callback('xg_off')

        print("🎹 XG SYSEX: XG System OFF")
        return {'type': 'system_command', 'command': 'xg_off'}

    def _handle_xg_reset(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG Reset command."""
        # Reset all parameters to defaults
        self._initialize_default_parameters()

        if self.system_command_callback:
            self.system_command_callback('xg_reset')

        print("🎹 XG SYSEX: XG Reset - All parameters reset to defaults")
        return {'type': 'system_command', 'command': 'xg_reset'}

    def _handle_parameter_change(self, data: list[int]) -> dict[str, Any] | None:
        """
        Handle parameter change command.

        Format: F0 43 [device] 4C 08 [part] [param_msb] [param_lsb] [data_msb] [data_lsb] F7
        """
        if len(data) < 5:
            return None

        part = data[0]
        param_msb = data[1]
        param_lsb = data[2]
        data_msb = data[3]
        data_lsb = data[4] if len(data) > 4 else 0

        # Combine data bytes
        value = (data_msb << 7) | data_lsb

        parameter_address = (param_msb << 8) | param_lsb
        parameter_name = self.XG_PARAMETER_ADDRESSES.get(parameter_address, f'unknown_{parameter_address:04X}')

        # Update parameter for specific part
        part_param_name = f'{parameter_name}_part_{part}'
        self.parameters[part_param_name] = value

        # Notify callback
        if self.parameter_change_callback:
            self.parameter_change_callback(part_param_name, value)

        return {
            'type': 'parameter_change',
            'part': part,
            'parameter': parameter_name,
            'address': parameter_address,
            'value': value
        }

    def _handle_master_tune(self, data: list[int]) -> dict[str, Any] | None:
        """Handle master tune command."""
        if len(data) < 2:
            return None

        # Master tune is in ±100 cent units
        tune_value = (data[0] << 7) | data[1]
        # Convert to actual cent value (-8192 to +8191 range)
        cents = tune_value - 8192 if tune_value > 8191 else tune_value

        self.parameters['master_tune'] = cents / 100.0  # Convert to semitones

        if self.parameter_change_callback:
            self.parameter_change_callback('master_tune', self.parameters['master_tune'])

        return {
            'type': 'master_tune',
            'value': self.parameters['master_tune'],
            'unit': 'semitones'
        }

    def _handle_master_transpose(self, data: list[int]) -> dict[str, Any] | None:
        """Handle master transpose command."""
        if len(data) < 1:
            return None

        # Master transpose is in ±24 semitone units
        transpose_value = data[0]
        if transpose_value > 127:
            transpose_value -= 256  # Signed byte

        transpose_value = max(-24, min(24, transpose_value))
        self.parameters['master_transpose'] = transpose_value

        if self.parameter_change_callback:
            self.parameter_change_callback('master_transpose', transpose_value)

        return {
            'type': 'master_transpose',
            'value': transpose_value,
            'unit': 'semitones'
        }

    def _handle_display_message(self, data: list[int]) -> dict[str, Any] | None:
        """Handle display message command."""
        # Convert data to ASCII string
        try:
            message = ''.join(chr(b) for b in data if 32 <= b <= 126)  # Printable ASCII

            if self.display_callback:
                self.display_callback('message', message)

            return {
                'type': 'display_message',
                'message': message
            }
        except:
            return None

    def _handle_led_control(self, data: list[int]) -> dict[str, Any] | None:
        """Handle LED control command."""
        if len(data) < 2:
            return None

        led_number = data[0]
        led_state = data[1]  # 0=off, 1=on, 2=blink

        if self.display_callback:
            self.display_callback('led', {'number': led_number, 'state': led_state})

        return {
            'type': 'led_control',
            'led_number': led_number,
            'led_state': led_state
        }

    def _handle_xg_dump_request(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG dump request - returns all XG parameters."""
        # Generate comprehensive XG parameter dump
        dump_data = self._generate_xg_parameter_dump()

        return {
            'type': 'dump_request',
            'status': 'completed',
            'data': dump_data,
            'data_length': len(dump_data)
        }

    def _handle_xg_bulk_dump(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG bulk dump - processes XG parameter data."""
        if len(data) < 2:
            return {'type': 'bulk_dump', 'status': 'error', 'error': 'insufficient_data'}

        # XG bulk dump format: [address_msb] [address_lsb] [data...]
        address_msb = data[0]
        address_lsb = data[1]
        parameter_data = data[2:]

        success = self._process_xg_bulk_dump_data(address_msb, address_lsb, parameter_data)

        return {
            'type': 'bulk_dump',
            'status': 'completed' if success else 'error',
            'address': (address_msb << 8) | address_lsb,
            'data_length': len(parameter_data)
        }

    def _handle_xg_dump(self, data: list[int]) -> dict[str, Any] | None:
        """Handle XG dump - similar to bulk dump but XG-specific format."""
        # For XG dump, we handle it the same as bulk dump
        return self._handle_xg_bulk_dump(data)

    def _handle_bulk_dump(self, data: list[int]) -> dict[str, Any] | None:
        """Handle general bulk dump - processes parameter data."""
        if len(data) < 1:
            return {'type': 'bulk_dump', 'status': 'error', 'error': 'no_data'}

        # Determine dump type from first byte
        dump_type = data[0]
        dump_data = data[1:]

        if dump_type == 0x00:  # System parameters
            success = self._process_system_bulk_dump(dump_data)
        elif dump_type == 0x01:  # Effect parameters
            success = self._process_effect_bulk_dump(dump_data)
        elif dump_type == 0x02:  # Multi-part parameters
            success = self._process_multipart_bulk_dump(dump_data)
        else:
            return {'type': 'bulk_dump', 'status': 'error', 'error': 'unknown_dump_type'}

        return {
            'type': 'bulk_dump',
            'dump_type': dump_type,
            'status': 'completed' if success else 'error',
            'data_length': len(dump_data)
        }

    def _handle_bulk_dump_request(self, data: list[int]) -> dict[str, Any] | None:
        """Handle bulk dump request - returns requested parameter data."""
        if len(data) < 1:
            return {'type': 'bulk_dump_request', 'status': 'error', 'error': 'no_request_type'}

        request_type = data[0]

        if request_type == 0x00:  # All system parameters
            dump_data = self._generate_system_bulk_dump()
        elif request_type == 0x01:  # All effect parameters
            dump_data = self._generate_effect_bulk_dump()
        elif request_type == 0x02:  # All multi-part parameters
            dump_data = self._generate_multipart_bulk_dump()
        elif request_type == 0x7F:  # All parameters (XG dump)
            dump_data = self._generate_xg_parameter_dump()
        else:
            return {'type': 'bulk_dump_request', 'status': 'error', 'error': 'unknown_request_type'}

        return {
            'type': 'bulk_dump_request',
            'request_type': request_type,
            'status': 'completed',
            'data': dump_data,
            'data_length': len(dump_data)
        }

    def _handle_special_message(self, data: list[int]) -> dict[str, Any] | None:
        """Handle special message."""
        return {'type': 'special_message', 'data': data}

    # Public interface methods

    def set_parameter_change_callback(self, callback: Callable[[str, Any], None]):
        """
        Set callback for parameter changes.

        Args:
            callback: Function called with (parameter_name, value)
        """
        self.parameter_change_callback = callback

    def set_system_command_callback(self, callback: Callable[[str], None]):
        """
        Set callback for system commands.

        Args:
            callback: Function called with command name
        """
        self.system_command_callback = callback

    def set_display_callback(self, callback: Callable[[str, Any], None]):
        """
        Set callback for display/LED operations.

        Args:
            callback: Function called with (type, data)
        """
        self.display_callback = callback

    def get_parameter(self, parameter_name: str) -> Any:
        """
        Get parameter value.

        Args:
            parameter_name: Parameter name

        Returns:
            Parameter value or None
        """
        return self.parameters.get(parameter_name)

    def set_parameter(self, parameter_name: str, value: Any) -> bool:
        """
        Set parameter value programmatically.

        Args:
            parameter_name: Parameter name
            value: Parameter value

        Returns:
            True if set successfully
        """
        if parameter_name in self.parameters:
            self.parameters[parameter_name] = value

            if self.parameter_change_callback:
                self.parameter_change_callback(parameter_name, value)

            return True
        return False

    def create_sysex_message(self, command: int, data: list[int]) -> bytes:
        """
        Create a properly formatted XG SYSEX message.

        Args:
            command: XG command byte
            data: Command data bytes

        Returns:
            Complete SYSEX message bytes
        """
        # Build message: F0 43 [device] 4C [command] [data...] [checksum] F7
        message = [0xF0, 0x43, self.device_id, self.XG_MODEL_ID, command]
        message.extend(data)

        # Calculate and append checksum
        checksum = self._calculate_checksum(message[1:])  # Exclude F0
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def get_supported_commands(self) -> dict[int, str]:
        """
        Get all supported XG commands.

        Returns:
            Dictionary mapping command bytes to names
        """
        return self.XG_COMMANDS.copy()

    def get_status(self) -> dict[str, Any]:
        """
        Get SYSEX controller status.

        Returns:
            Status dictionary
        """
        return {
            'device_id': self.device_id,
            'model_id': self.model_id,
            'active_parameters': len(self.parameters),
            'supported_commands': len(self.XG_COMMANDS),
            'callbacks_configured': {
                'parameter_change': self.parameter_change_callback is not None,
                'system_command': self.system_command_callback is not None,
                'display': self.display_callback is not None
            }
        }

    # Bulk Dump Data Processing and Generation Methods

    def _generate_xg_parameter_dump(self) -> list[int]:
        """
        Generate comprehensive XG parameter dump data.

        Returns:
            List of parameter data bytes for XG dump
        """
        dump_data = []

        # System effect parameters (MSB 1-2)
        for address, param_name in self.XG_PARAMETER_ADDRESSES.items():
            if address >= 0x0100 and address <= 0x02FF:  # System effects
                value = self.parameters.get(param_name, 0)
                # Convert to 7-bit if needed
                dump_data.extend([address >> 8, address & 0xFF, value & 0x7F])

        # Multi-part parameters (MSB 42-45)
        for part in range(16):
            for base_address in [0x2A00, 0x2B00, 0x2C00, 0x2D00]:  # Voice reserve, mode, level, pan
                address = base_address + part
                param_name = f'{self.XG_PARAMETER_ADDRESSES.get(base_address, "unknown")}_part_{part}'
                value = self.parameters.get(param_name, 0)
                dump_data.extend([address >> 8, address & 0xFF, value & 0x7F])

        return dump_data

    def _process_xg_bulk_dump_data(self, address_msb: int, address_lsb: int,
                                  parameter_data: list[int]) -> bool:
        """
        Process XG bulk dump parameter data.

        Args:
            address_msb: Parameter address MSB
            address_lsb: Parameter address LSB
            parameter_data: Parameter values

        Returns:
            True if processed successfully
        """
        try:
            base_address = (address_msb << 8) | address_lsb

            # Process based on address range
            if base_address >= 0x0100 and base_address <= 0x02FF:  # System effects
                for i, value in enumerate(parameter_data):
                    address = base_address + i
                    param_name = self.XG_PARAMETER_ADDRESSES.get(address)
                    if param_name:
                        self.parameters[param_name] = value
                        if self.parameter_change_callback:
                            self.parameter_change_callback(param_name, value)

            elif base_address >= 0x2A00 and base_address <= 0x2DFF:  # Multi-part
                for i, value in enumerate(parameter_data):
                    part = (base_address + i) & 0x0F  # Extract part number
                    base_param = base_address & 0xFF00
                    param_name = f'{self.XG_PARAMETER_ADDRESSES.get(base_param, "unknown")}_part_{part}'
                    self.parameters[param_name] = value
                    if self.parameter_change_callback:
                        self.parameter_change_callback(param_name, value)

            return True

        except Exception as e:
            print(f"❌ XG SYSEX: Error processing bulk dump data: {e}")
            return False

    def _generate_system_bulk_dump(self) -> list[int]:
        """
        Generate system parameter bulk dump data.

        Returns:
            System parameter dump data
        """
        dump_data = [0x00]  # System parameters type

        # Add system effect parameters
        for param_name in ['reverb_type', 'reverb_time', 'reverb_hf_damping',
                          'reverb_balance', 'reverb_level', 'chorus_type',
                          'chorus_lfo_freq', 'chorus_depth', 'chorus_feedback',
                          'chorus_send_level']:
            value = self.parameters.get(param_name, 0)
            dump_data.append(value & 0x7F)

        return dump_data

    def _generate_effect_bulk_dump(self) -> list[int]:
        """
        Generate effect parameter bulk dump data.

        Returns:
            Effect parameter dump data
        """
        dump_data = [0x01]  # Effect parameters type

        # Add all effect-related parameters
        effect_params = [
            'reverb_type', 'reverb_time', 'reverb_hf_damping', 'reverb_balance', 'reverb_level',
            'chorus_type', 'chorus_lfo_freq', 'chorus_depth', 'chorus_feedback', 'chorus_send_level'
        ]

        for param_name in effect_params:
            value = self.parameters.get(param_name, 0)
            dump_data.append(value & 0x7F)

        return dump_data

    def _generate_multipart_bulk_dump(self) -> list[int]:
        """
        Generate multi-part parameter bulk dump data.

        Returns:
            Multi-part parameter dump data
        """
        dump_data = [0x02]  # Multi-part parameters type

        # Add parameters for all 16 parts (voice reserve, mode, level, pan)
        for part in range(16):
            # Voice reserve (MSB 42)
            reserve = self.parameters.get(f'voice_reserve_part_{part}', 8)
            dump_data.append(reserve & 0x7F)

            # Part mode (MSB 43)
            mode = self.parameters.get(f'part_mode_part_{part}', 1)
            dump_data.append(mode & 0x7F)

            # Part level (MSB 44)
            level = int(self.parameters.get(f'part_level_part_{part}', 1.0) * 127)
            dump_data.append(level & 0x7F)

            # Part pan (MSB 45)
            pan = int((self.parameters.get(f'part_pan_part_{part}', 0.0) + 1.0) * 63.5)
            dump_data.append(pan & 0x7F)

        return dump_data

    def _process_system_bulk_dump(self, dump_data: list[int]) -> bool:
        """
        Process system parameter bulk dump data.

        Args:
            dump_data: Bulk dump parameter data

        Returns:
            True if processed successfully
        """
        try:
            expected_params = ['reverb_type', 'reverb_time', 'reverb_hf_damping',
                              'reverb_balance', 'reverb_level', 'chorus_type',
                              'chorus_lfo_freq', 'chorus_depth', 'chorus_feedback',
                              'chorus_send_level']

            if len(dump_data) < len(expected_params):
                return False

            for i, param_name in enumerate(expected_params):
                self.parameters[param_name] = dump_data[i]
                if self.parameter_change_callback:
                    self.parameter_change_callback(param_name, dump_data[i])

            return True

        except Exception as e:
            print(f"❌ XG SYSEX: Error processing system bulk dump: {e}")
            return False

    def _process_effect_bulk_dump(self, dump_data: list[int]) -> bool:
        """
        Process effect parameter bulk dump data.

        Args:
            dump_data: Bulk dump parameter data

        Returns:
            True if processed successfully
        """
        # For now, handle the same as system bulk dump
        return self._process_system_bulk_dump(dump_data)

    def _process_multipart_bulk_dump(self, dump_data: list[int]) -> bool:
        """
        Process multi-part parameter bulk dump data.

        Args:
            dump_data: Bulk dump parameter data

        Returns:
            True if processed successfully
        """
        try:
            # Expect 64 bytes (4 parameters × 16 parts)
            if len(dump_data) < 64:
                return False

            for part in range(16):
                base_idx = part * 4

                # Voice reserve
                self.parameters[f'voice_reserve_part_{part}'] = dump_data[base_idx]
                if self.parameter_change_callback:
                    self.parameter_change_callback(f'voice_reserve_part_{part}', dump_data[base_idx])

                # Part mode
                self.parameters[f'part_mode_part_{part}'] = dump_data[base_idx + 1]
                if self.parameter_change_callback:
                    self.parameter_change_callback(f'part_mode_part_{part}', dump_data[base_idx + 1])

                # Part level (convert from 0-127 to 0.0-1.0)
                level_norm = dump_data[base_idx + 2] / 127.0
                self.parameters[f'part_level_part_{part}'] = level_norm
                if self.parameter_change_callback:
                    self.parameter_change_callback(f'part_level_part_{part}', level_norm)

                # Part pan (convert from 0-127 to -1.0 to +1.0)
                pan_norm = (dump_data[base_idx + 3] - 64) / 64.0
                self.parameters[f'part_pan_part_{part}'] = pan_norm
                if self.parameter_change_callback:
                    self.parameter_change_callback(f'part_pan_part_{part}', pan_norm)

            return True

        except Exception as e:
            print(f"❌ XG SYSEX: Error processing multipart bulk dump: {e}")
            return False

    # Bulk Dump Creation Methods

    def create_bulk_dump_message(self, dump_type: int = 0x7F) -> bytes:
        """
        Create a complete XG bulk dump SYSEX message.

        Args:
            dump_type: Type of bulk dump (0x7F = all parameters)

        Returns:
            Complete SYSEX message bytes
        """
        if dump_type == 0x7F:  # All parameters
            dump_data = self._generate_xg_parameter_dump()
        elif dump_type == 0x00:  # System parameters
            dump_data = self._generate_system_bulk_dump()
        elif dump_type == 0x01:  # Effect parameters
            dump_data = self._generate_effect_bulk_dump()
        elif dump_type == 0x02:  # Multi-part parameters
            dump_data = self._generate_multipart_bulk_dump()
        else:
            return b''  # Invalid dump type

        # Create SYSEX message with command 0x07 (XG Bulk Dump)
        return self.create_sysex_message(0x07, dump_data)

    def create_bulk_dump_request_message(self, request_type: int = 0x7F) -> bytes:
        """
        Create XG bulk dump request SYSEX message.

        Args:
            request_type: Type of data to request

        Returns:
            Complete SYSEX message bytes
        """
        return self.create_sysex_message(0x0C, [request_type])
