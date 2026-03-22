"""
XG Realtime Control - SYSEX Realtime Operations

Implements XG realtime control features for professional operation.
Handles parameter changes, display messages, LED control, and bulk operations.

XG Specification Compliance:
- Parameter Change SYSEX: F0 43 [dev] 4C 08 [part] [param] [value] F7
- Display Messages: F0 43 [dev] 4C 10 [message] F7
- LED Control: F0 43 [dev] 4C 11 [led] [state] F7
- Bulk Dump: F0 43 [dev] 4C 07/09/0A [data] F7

Copyright (c) 2025
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class XGRealtimeControl:
    """
    XG Realtime Control - Professional SYSEX Operations

    Handles XG realtime control messages for live performance and
    professional synthesizer operation.

    Key Features:
    - Parameter change SYSEX for real-time control
    - Display message control for user interface
    - LED indicator control for visual feedback
    - Bulk dump operations for state management
    - Thread-safe operation for live performance
    """

    def __init__(self, device_id: int = 0x10):
        """
        Initialize XG realtime control.

        Args:
            device_id: XG device ID (0x00-0x7F)
        """
        self.device_id = device_id
        self.lock = threading.RLock()

        # Display callback for UI integration
        self.display_callback = None

        # LED state tracking
        self.led_states = [0] * 16  # Support for 16 LEDs

        # Parameter change callback
        self.parameter_change_callback = None

        # Bulk operation callbacks
        self.bulk_dump_callback = None
        self.bulk_dump_request_callback = None

        print("🎛️ XG REALTIME CONTROL: Initialized")
        print(f"   Device ID: {self.device_id:02X}, LED control ready")

    def set_display_callback(self, callback: Callable[[str, Any], None]):
        """Set callback for display operations."""
        self.display_callback = callback

    def set_parameter_change_callback(self, callback: Callable[[int, int, int], None]):
        """Set callback for parameter changes (part, parameter, value)."""
        self.parameter_change_callback = callback

    def set_bulk_callbacks(
        self, dump_callback: Callable[[bytes], None], request_callback: Callable[[], bytes]
    ):
        """Set callbacks for bulk operations."""
        self.bulk_dump_callback = dump_callback
        self.bulk_dump_request_callback = request_callback

    def process_sysex_message(self, data: bytes) -> dict[str, Any] | None:
        """
        Process incoming SYSEX message for realtime control.

        Args:
            data: SYSEX message data

        Returns:
            Processing result or None if not handled
        """
        try:
            # Validate XG SYSEX format: F0 43 [dev] 4C [cmd] [data...] F7
            if len(data) < 6 or data[0] != 0xF0 or data[-1] != 0xF7:
                return None

            if data[1] != 0x43 or data[3] != 0x4C:  # Not Yamaha XG
                return None

            device_id = data[2]
            if device_id != self.device_id and device_id != 0x7F:  # Not for this device
                return None

            command = data[4]
            command_data = data[
                5:-2
            ]  # Exclude F0, manufacturer, device, model, command, checksum, F7

            # Route to appropriate handler
            if command == 0x08:  # Parameter Change
                return self._handle_parameter_change(command_data)
            elif command == 0x10:  # Display Message
                return self._handle_display_message(command_data)
            elif command == 0x11:  # LED Control
                return self._handle_led_control(command_data)
            elif command == 0x07:  # XG Bulk Dump
                return self._handle_bulk_dump(command_data)
            elif command == 0x09:  # XG Dump
                return self._handle_xg_dump(command_data)
            elif command == 0x0A:  # Bulk Dump
                return self._handle_bulk_dump_data(command_data)
            elif command == 0x0C:  # Bulk Dump Request
                return self._handle_bulk_dump_request(command_data)

        except Exception as e:
            print(f"❌ XG REALTIME: SYSEX processing error - {e}")
            return None

        return None

    def _handle_parameter_change(self, data: bytes) -> dict[str, Any] | None:
        """Handle parameter change SYSEX: F0 43 [dev] 4C 08 [part] [param_msb] [param_lsb] [data_msb] [data_lsb] F7"""
        if len(data) < 5:
            return None

        part = data[0]
        param_msb = data[1]
        param_lsb = data[2]
        data_msb = data[3]
        data_lsb = data[4] if len(data) > 4 else 0

        # Combine data bytes to 14-bit value
        value = (data_msb << 7) | data_lsb
        parameter_address = (param_msb << 8) | param_lsb

        # Notify callback
        if self.parameter_change_callback:
            self.parameter_change_callback(part, parameter_address, value)

        return {
            "type": "parameter_change",
            "part": part,
            "parameter": parameter_address,
            "value": value,
            "timestamp": time.time(),
        }

    def _handle_display_message(self, data: bytes) -> dict[str, Any] | None:
        """Handle display message SYSEX: F0 43 [dev] 4C 10 [message_data] F7"""
        try:
            # Convert to ASCII string (XG display messages are ASCII)
            message = "".join(chr(b) for b in data if 32 <= b <= 126)

            # Notify display callback
            if self.display_callback:
                self.display_callback("message", message)

            return {"type": "display_message", "message": message, "timestamp": time.time()}
        except:
            return None

    def _handle_led_control(self, data: bytes) -> dict[str, Any] | None:
        """Handle LED control SYSEX: F0 43 [dev] 4C 11 [led_number] [led_state] F7"""
        if len(data) < 2:
            return None

        led_number = data[0]
        led_state = data[1]

        # Validate LED number
        if 0 <= led_number < len(self.led_states):
            with self.lock:
                self.led_states[led_number] = led_state

            # Notify display callback
            if self.display_callback:
                self.display_callback("led", {"number": led_number, "state": led_state})

            return {
                "type": "led_control",
                "led_number": led_number,
                "led_state": led_state,
                "timestamp": time.time(),
            }

        return None

    def _handle_bulk_dump(self, data: bytes) -> dict[str, Any] | None:
        """Handle XG bulk dump: F0 43 [dev] 4C 07 [data] F7"""
        if self.bulk_dump_callback:
            self.bulk_dump_callback(data)

        return {"type": "bulk_dump", "data_length": len(data), "timestamp": time.time()}

    def _handle_xg_dump(self, data: bytes) -> dict[str, Any] | None:
        """Handle XG dump: F0 43 [dev] 4C 09 [data] F7"""
        # Similar to bulk dump but XG-specific format
        if self.bulk_dump_callback:
            self.bulk_dump_callback(data)

        return {"type": "xg_dump", "data_length": len(data), "timestamp": time.time()}

    def _handle_bulk_dump_data(self, data: bytes) -> dict[str, Any] | None:
        """Handle bulk dump data: F0 43 [dev] 4C 0A [data] F7"""
        if self.bulk_dump_callback:
            self.bulk_dump_callback(data)

        return {"type": "bulk_dump_data", "data_length": len(data), "timestamp": time.time()}

    def _handle_bulk_dump_request(self, data: bytes) -> dict[str, Any] | None:
        """Handle bulk dump request: F0 43 [dev] 4C 0C [request_data] F7"""
        if self.bulk_dump_request_callback:
            response_data = self.bulk_dump_request_callback()
            if response_data:
                # Send response (this would typically be handled by MIDI output)
                return {
                    "type": "bulk_dump_request",
                    "response_data": response_data,
                    "timestamp": time.time(),
                }

        return {"type": "bulk_dump_request", "handled": False, "timestamp": time.time()}

    # Outgoing SYSEX message creation methods

    def create_parameter_change_message(
        self, part: int, parameter_address: int, value: int
    ) -> bytes:
        """
        Create XG parameter change SYSEX message.

        Args:
            part: MIDI part/channel (0-15)
            parameter_address: XG parameter address (0-65535)
            value: Parameter value (0-16383)

        Returns:
            Complete SYSEX message bytes
        """
        # Split parameter address
        param_msb = (parameter_address >> 8) & 0x7F
        param_lsb = parameter_address & 0x7F

        # Split value to 14-bit
        data_msb = (value >> 7) & 0x7F
        data_lsb = value & 0x7F

        # Build message: F0 43 [dev] 4C 08 [part] [param_msb] [param_lsb] [data_msb] [data_lsb] [checksum] F7
        message = [
            0xF0,
            0x43,
            self.device_id,
            0x4C,
            0x08,  # Header
            part & 0x7F,
            param_msb,
            param_lsb,
            data_msb,
            data_lsb,  # Data
        ]

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def create_display_message(self, message: str) -> bytes:
        """
        Create XG display message SYSEX.

        Args:
            message: Display message (ASCII string)

        Returns:
            Complete SYSEX message bytes
        """
        # Convert message to bytes (limit to printable ASCII)
        message_bytes = [ord(c) for c in message[:32] if 32 <= ord(c) <= 126]  # Max 32 chars

        # Build message: F0 43 [dev] 4C 10 [message_bytes] [checksum] F7
        message_data = [0xF0, 0x43, self.device_id, 0x4C, 0x10] + message_bytes

        # Calculate checksum
        checksum = self._calculate_checksum(message_data[1:])
        message_data.append(checksum)
        message_data.append(0xF7)

        return bytes(message_data)

    def create_led_control_message(self, led_number: int, led_state: int) -> bytes:
        """
        Create XG LED control SYSEX message.

        Args:
            led_number: LED number (0-15)
            led_state: LED state (0=off, 1=on, 2=blink)

        Returns:
            Complete SYSEX message bytes
        """
        # Build message: F0 43 [dev] 4C 11 [led_number] [led_state] [checksum] F7
        message = [
            0xF0,
            0x43,
            self.device_id,
            0x4C,
            0x11,  # Header
            led_number & 0x7F,
            led_state & 0x7F,  # Data
        ]

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def create_bulk_dump_message(self, data: bytes) -> bytes:
        """
        Create XG bulk dump SYSEX message.

        Args:
            data: Bulk dump data

        Returns:
            Complete SYSEX message bytes
        """
        # Build message: F0 43 [dev] 4C 07 [data] [checksum] F7
        message = [0xF0, 0x43, self.device_id, 0x4C, 0x07] + list(data)

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def create_bulk_dump_request_message(self, request_type: int = 0) -> bytes:
        """
        Create XG bulk dump request SYSEX message.

        Args:
            request_type: Request type (0=all parameters, etc.)

        Returns:
            Complete SYSEX message bytes
        """
        # Build message: F0 43 [dev] 4C 0C [request_type] [checksum] F7
        message = [
            0xF0,
            0x43,
            self.device_id,
            0x4C,
            0x0C,  # Header
            request_type & 0x7F,  # Request type
        ]

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def _calculate_checksum(self, data: list[int]) -> int:
        """Calculate XG SYSEX checksum."""
        checksum = 0
        for byte in data:
            checksum += byte
        checksum = (checksum & 0x7F) ^ 0x7F  # XG checksum formula
        return checksum

    # LED state management

    def set_led_state(self, led_number: int, state: int) -> bool:
        """
        Set LED state programmatically.

        Args:
            led_number: LED number (0-15)
            state: LED state (0=off, 1=on, 2=blink)

        Returns:
            True if set successfully
        """
        if 0 <= led_number < len(self.led_states):
            with self.lock:
                self.led_states[led_number] = state

                # Notify callback
                if self.display_callback:
                    self.display_callback("led", {"number": led_number, "state": state})

            return True
        return False

    def get_led_state(self, led_number: int) -> int:
        """Get current LED state."""
        if 0 <= led_number < len(self.led_states):
            with self.lock:
                return self.led_states[led_number]
        return 0

    def get_all_led_states(self) -> list[int]:
        """Get all LED states."""
        with self.lock:
            return self.led_states.copy()

    # Status and monitoring

    def get_status(self) -> dict[str, Any]:
        """Get realtime control status."""
        with self.lock:
            return {
                "device_id": self.device_id,
                "led_states": self.led_states.copy(),
                "callbacks_configured": {
                    "display": self.display_callback is not None,
                    "parameter_change": self.parameter_change_callback is not None,
                    "bulk_dump": self.bulk_dump_callback is not None,
                    "bulk_dump_request": self.bulk_dump_request_callback is not None,
                },
                "active_leds": sum(1 for state in self.led_states if state > 0),
            }

    def reset_led_states(self):
        """Reset all LED states to off."""
        with self.lock:
            self.led_states = [0] * len(self.led_states)

        print("🎛️ XG REALTIME: All LED states reset")

    def __str__(self) -> str:
        """String representation."""
        status = self.get_status()
        return f"XGRealtimeControl(device={status['device_id']:02X}, leds_active={status['active_leds']})"

    def __repr__(self) -> str:
        return self.__str__()
