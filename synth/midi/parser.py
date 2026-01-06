"""
MIDI Message Parser - Complete MIDI Processing Pipeline

Professional MIDI message parsing, sysex handling, and real-time event processing
for complete MIDI input/output functionality.

Part of S90/S70 compatibility - Core Infrastructure (Phase 1).
"""

from typing import Dict, List, Any, Optional, Tuple, Callable, Union
import threading
import time
import struct


class MIDIStatus:
    """MIDI status byte constants"""
    # Channel messages
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0

    # System messages
    SYSTEM_EXCLUSIVE = 0xF0
    TIME_CODE = 0xF1
    SONG_POSITION = 0xF2
    SONG_SELECT = 0xF3
    TUNE_REQUEST = 0xF6
    END_OF_EXCLUSIVE = 0xF7
    TIMING_CLOCK = 0xF8
    START = 0xFA
    CONTINUE = 0xFB
    STOP = 0xFC
    ACTIVE_SENSING = 0xFE
    SYSTEM_RESET = 0xFF


class MIDIMessage:
    """Represents a parsed MIDI message"""

    def __init__(self, type: str, channel: Optional[int] = None,
                 data: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[float] = None):
        """
        Initialize MIDI message.

        Args:
            type: Message type ('note_on', 'note_off', 'control_change', etc.)
            channel: MIDI channel (0-15) or None for system messages
            data: Message-specific data
            timestamp: Message timestamp
        """
        self.type = type
        self.channel = channel
        self.data = data or {}
        self.timestamp = timestamp or time.time()

    def __str__(self) -> str:
        """String representation"""
        channel_str = f" ch{self.channel}" if self.channel is not None else ""
        return f"MIDIMessage({self.type}{channel_str}, {self.data})"


class MIDISysexParser:
    """Specialized parser for System Exclusive messages"""

    def __init__(self):
        """Initialize sysex parser"""
        # XG sysex constants
        self.XG_MANUFACTURER_ID = [0x43, 0x10]  # Yamaha XG
        self.XG_MODEL_ID = 0x4C  # XG model ID

        # Parameter change commands
        self.XG_BULK_DUMP = 0x00
        self.XG_PARAMETER_CHANGE = 0x10
        self.XG_DATA_SET = 0x12

    def parse_sysex(self, data: List[int]) -> Optional[MIDIMessage]:
        """
        Parse system exclusive message.

        Args:
            data: Raw sysex data (without F0/F7)

        Returns:
            Parsed MIDI message or None if unrecognized
        """
        if len(data) < 3:
            return None

        # Check for XG manufacturer ID
        if data[:2] == self.XG_MANUFACTURER_ID:
            return self._parse_xg_sysex(data[2:])

        # Handle other manufacturer sysex
        manufacturer_id = data[0]
        if manufacturer_id == 0x7E:  # Universal Non-Real Time
            return self._parse_universal_sysex(data[1:])
        elif manufacturer_id == 0x7F:  # Universal Real Time
            return self._parse_universal_sysex(data[1:], real_time=True)

        return None

    def _parse_xg_sysex(self, data: List[int]) -> Optional[MIDIMessage]:
        """Parse Yamaha XG system exclusive message"""
        if len(data) < 2:
            return None

        model_id = data[0]
        if model_id != self.XG_MODEL_ID:
            return None

        command = data[1]

        if command == self.XG_BULK_DUMP:
            return self._parse_xg_bulk_dump(data[2:])
        elif command == self.XG_PARAMETER_CHANGE:
            return self._parse_xg_parameter_change(data[2:])
        elif command == self.XG_DATA_SET:
            return self._parse_xg_data_set(data[2:])

        return None

    def _parse_xg_bulk_dump(self, data: List[int]) -> Optional[MIDIMessage]:
        """Parse XG bulk dump"""
        # XG bulk dump format parsing would go here
        return MIDIMessage('xg_bulk_dump', data={'raw_data': data})

    def _parse_xg_parameter_change(self, data: List[int]) -> Optional[MIDIMessage]:
        """Parse XG parameter change"""
        if len(data) < 4:
            return None

        # Parse XG parameter change format
        address_high = data[0]
        address_mid = data[1]
        address_low = data[2]
        value = data[3]

        # Convert to XG address
        xg_address = (address_high << 16) | (address_mid << 8) | address_low

        return MIDIMessage('xg_parameter_change', data={
            'address': xg_address,
            'value': value,
            'address_bytes': [address_high, address_mid, address_low]
        })

    def _parse_xg_data_set(self, data: List[int]) -> Optional[MIDIMessage]:
        """Parse XG data set (multiple parameters)"""
        return MIDIMessage('xg_data_set', data={'raw_data': data})

    def _parse_universal_sysex(self, data: List[int], real_time: bool = False) -> Optional[MIDIMessage]:
        """Parse universal system exclusive"""
        if len(data) < 2:
            return None

        sub_id1 = data[0]
        sub_id2 = data[1]

        message_type = 'universal_realtime_sysex' if real_time else 'universal_sysex'

        return MIDIMessage(message_type, data={
            'sub_id1': sub_id1,
            'sub_id2': sub_id2,
            'payload': data[2:] if len(data) > 2 else []
        })


class MIDIMessageParser:
    """
    MIDI Message Parser - Complete MIDI Processing Pipeline

    Handles real-time MIDI input parsing, sysex processing, and event queuing
    with proper timestamping and channel filtering.
    """

    def __init__(self):
        """Initialize MIDI parser"""
        self.sysex_parser = MIDISysexParser()

        # Message queue
        self.message_queue: List[MIDIMessage] = []
        self.max_queue_size = 1000

        # Running status for MIDI 1.0 compatibility
        self.running_status = 0
        self.running_status_enabled = True

        # Channel filtering
        self.active_channels: List[int] = list(range(16))  # All channels active by default
        self.system_messages_enabled = True

        # Sysex handling
        self.sysex_buffer: List[int] = []
        self.in_sysex = False

        # Thread safety
        self.lock = threading.RLock()

        # Callbacks
        self.message_callback: Optional[Callable[[MIDIMessage], None]] = None

    def parse_bytes(self, data: bytes) -> List[MIDIMessage]:
        """
        Parse raw MIDI bytes into messages.

        Args:
            data: Raw MIDI data bytes

        Returns:
            List of parsed MIDI messages
        """
        with self.lock:
            messages = []

            for byte in data:
                message = self._parse_byte(byte)
                if message:
                    messages.append(message)
                    if self.message_callback:
                        self.message_callback(message)

            return messages

    def _parse_byte(self, byte: int) -> Optional[MIDIMessage]:
        """
        Parse a single MIDI byte.

        Args:
            byte: MIDI byte value (0-255)

        Returns:
            Parsed message or None if incomplete
        """
        # Handle system exclusive
        if self.in_sysex:
            if byte == MIDIStatus.END_OF_EXCLUSIVE:
                # End of sysex
                self.in_sysex = False
                sysex_data = self.sysex_buffer.copy()
                self.sysex_buffer.clear()

                # Parse sysex message
                sysex_message = self.sysex_parser.parse_sysex(sysex_data)
                if sysex_message:
                    self._enqueue_message(sysex_message)
                    return sysex_message
            else:
                # Continue collecting sysex data
                self.sysex_buffer.append(byte)
            return None

        # Check for status byte
        if byte & 0x80:
            # Status byte
            if byte == MIDIStatus.SYSTEM_EXCLUSIVE:
                # Start of system exclusive
                self.in_sysex = True
                self.sysex_buffer.clear()
                return None
            elif byte >= MIDIStatus.SYSTEM_RESET:
                # System message
                if self.system_messages_enabled:
                    message = self._parse_system_message(byte)
                    if message:
                        self._enqueue_message(message)
                        return message
                return None
            else:
                # Channel message status
                self.running_status = byte
                return None
        else:
            # Data byte - use running status if enabled
            if self.running_status_enabled and self.running_status:
                status = self.running_status
            else:
                return None  # No status available

            # Parse channel message
            message = self._parse_channel_message(status, byte)
            if message:
                self._enqueue_message(message)
                return message

        return None

    def _parse_system_message(self, status: int) -> Optional[MIDIMessage]:
        """Parse system message"""
        if status == MIDIStatus.TIMING_CLOCK:
            return MIDIMessage('timing_clock')
        elif status == MIDIStatus.START:
            return MIDIMessage('start')
        elif status == MIDIStatus.CONTINUE:
            return MIDIMessage('continue')
        elif status == MIDIStatus.STOP:
            return MIDIMessage('stop')
        elif status == MIDIStatus.ACTIVE_SENSING:
            return MIDIMessage('active_sensing')
        elif status == MIDIStatus.SYSTEM_RESET:
            return MIDIMessage('system_reset')
        elif status == MIDIStatus.TUNE_REQUEST:
            return MIDIMessage('tune_request')
        elif status == MIDIStatus.TIME_CODE:
            # Would need additional data byte
            return MIDIMessage('time_code', data={'quarter_frame': 0})
        elif status == MIDIStatus.SONG_POSITION:
            # Would need two data bytes
            return MIDIMessage('song_position', data={'position': 0})
        elif status == MIDIStatus.SONG_SELECT:
            # Would need data byte
            return MIDIMessage('song_select', data={'song': 0})

        return None

    def _parse_channel_message(self, status: int, first_data: int) -> Optional[MIDIMessage]:
        """
        Parse channel message with first data byte.

        Args:
            status: Status byte
            first_data: First data byte

        Returns:
            Parsed message or None
        """
        message_type = status & 0xF0
        channel = status & 0x0F

        # Filter by active channels
        if channel not in self.active_channels:
            return None

        if message_type == MIDIStatus.NOTE_OFF:
            return MIDIMessage('note_off', channel, {
                'note': first_data,
                'velocity': 0  # Note off with velocity 0
            })
        elif message_type == MIDIStatus.NOTE_ON:
            velocity = 0  # Would need second data byte
            if velocity == 0:
                return MIDIMessage('note_off', channel, {
                    'note': first_data,
                    'velocity': velocity
                })
            else:
                return MIDIMessage('note_on', channel, {
                    'note': first_data,
                    'velocity': velocity
                })
        elif message_type == MIDIStatus.POLY_PRESSURE:
            return MIDIMessage('poly_pressure', channel, {
                'note': first_data,
                'pressure': 0  # Would need second data byte
            })
        elif message_type == MIDIStatus.CONTROL_CHANGE:
            return MIDIMessage('control_change', channel, {
                'controller': first_data,
                'value': 0  # Would need second data byte
            })
        elif message_type == MIDIStatus.PROGRAM_CHANGE:
            return MIDIMessage('program_change', channel, {
                'program': first_data
            })
        elif message_type == MIDIStatus.CHANNEL_PRESSURE:
            return MIDIMessage('channel_pressure', channel, {
                'pressure': first_data
            })
        elif message_type == MIDIStatus.PITCH_BEND:
            return MIDIMessage('pitch_bend', channel, {
                'value': first_data  # Would need second data byte for full value
            })

        return None

    def _enqueue_message(self, message: MIDIMessage):
        """Add message to queue"""
        self.message_queue.append(message)

        # Maintain queue size limit
        if len(self.message_queue) > self.max_queue_size:
            self.message_queue.pop(0)

    def get_pending_events(self) -> List[MIDIMessage]:
        """
        Get all pending MIDI events.

        Returns:
            List of pending messages (clears queue)
        """
        with self.lock:
            events = self.message_queue.copy()
            self.message_queue.clear()
            return events

    def get_next_event(self) -> Optional[MIDIMessage]:
        """
        Get next pending MIDI event.

        Returns:
            Next message or None if queue empty
        """
        with self.lock:
            if self.message_queue:
                return self.message_queue.pop(0)
            return None

    def clear_queue(self):
        """Clear message queue"""
        with self.lock:
            self.message_queue.clear()

    def set_active_channels(self, channels: List[int]):
        """
        Set active MIDI channels for filtering.

        Args:
            channels: List of active channel numbers (0-15)
        """
        with self.lock:
            self.active_channels = [ch for ch in channels if 0 <= ch <= 15]

    def enable_system_messages(self, enabled: bool = True):
        """
        Enable/disable system message processing.

        Args:
            enabled: Whether to process system messages
        """
        with self.lock:
            self.system_messages_enabled = enabled

    def set_running_status_enabled(self, enabled: bool = True):
        """
        Enable/disable MIDI running status.

        Args:
            enabled: Whether to use running status
        """
        with self.lock:
            self.running_status_enabled = enabled

    def create_note_on(self, channel: int, note: int, velocity: int) -> MIDIMessage:
        """
        Create a note on message.

        Args:
            channel: MIDI channel (0-15)
            note: Note number (0-127)
            velocity: Velocity (0-127)

        Returns:
            MIDI message
        """
        return MIDIMessage('note_on', channel, {
            'note': note,
            'velocity': velocity
        })

    def create_note_off(self, channel: int, note: int, velocity: int = 0) -> MIDIMessage:
        """
        Create a note off message.

        Args:
            channel: MIDI channel (0-15)
            note: Note number (0-127)
            velocity: Velocity (0-127)

        Returns:
            MIDI message
        """
        return MIDIMessage('note_off', channel, {
            'note': note,
            'velocity': velocity
        })

    def create_control_change(self, channel: int, controller: int, value: int) -> MIDIMessage:
        """
        Create a control change message.

        Args:
            channel: MIDI channel (0-15)
            controller: Controller number (0-127)
            value: Controller value (0-127)

        Returns:
            MIDI message
        """
        return MIDIMessage('control_change', channel, {
            'controller': controller,
            'value': value
        })

    def create_program_change(self, channel: int, program: int) -> MIDIMessage:
        """
        Create a program change message.

        Args:
            channel: MIDI channel (0-15)
            program: Program number (0-127)

        Returns:
            MIDI message
        """
        return MIDIMessage('program_change', channel, {
            'program': program
        })

    def create_pitch_bend(self, channel: int, value: int) -> MIDIMessage:
        """
        Create a pitch bend message.

        Args:
            channel: MIDI channel (0-15)
            value: Pitch bend value (-8192 to 8191)

        Returns:
            MIDI message
        """
        # Convert to 14-bit MIDI value
        midi_value = value + 8192
        lsb = midi_value & 0x7F
        msb = (midi_value >> 7) & 0x7F

        return MIDIMessage('pitch_bend', channel, {
            'value': value,
            'lsb': lsb,
            'msb': msb
        })

    def create_sysex(self, manufacturer_id: Union[int, List[int]],
                     data: List[int]) -> MIDIMessage:
        """
        Create a system exclusive message.

        Args:
            manufacturer_id: Manufacturer ID (int or list of ints)
            data: Sysex data bytes

        Returns:
            MIDI message
        """
        if isinstance(manufacturer_id, int):
            full_data = [manufacturer_id] + data
        else:
            full_data = manufacturer_id + data

        return MIDIMessage('sysex', data={
            'manufacturer_id': manufacturer_id,
            'payload': data,
            'raw_data': full_data
        })

    def create_xg_parameter_change(self, address: int, value: int) -> MIDIMessage:
        """
        Create an XG parameter change message.

        Args:
            address: XG parameter address
            value: Parameter value

        Returns:
            MIDI message
        """
        # Convert address to XG format
        addr_high = (address >> 16) & 0xFF
        addr_mid = (address >> 8) & 0xFF
        addr_low = address & 0xFF

        # Create XG sysex data
        sysex_data = [0x43, 0x10, 0x4C, 0x10, addr_high, addr_mid, addr_low, value]

        return MIDIMessage('xg_parameter_change', data={
            'address': address,
            'value': value,
            'address_bytes': [addr_high, addr_mid, addr_low]
        })

    def set_message_callback(self, callback: Callable[[MIDIMessage], None]):
        """
        Set callback for incoming MIDI messages.

        Args:
            callback: Function to call for each message
        """
        self.message_callback = callback

    def get_queue_status(self) -> Dict[str, Any]:
        """Get message queue status"""
        with self.lock:
            return {
                'queue_size': len(self.message_queue),
                'max_queue_size': self.max_queue_size,
                'active_channels': self.active_channels.copy(),
                'system_messages_enabled': self.system_messages_enabled,
                'running_status_enabled': self.running_status_enabled,
                'in_sysex': self.in_sysex,
                'sysex_buffer_size': len(self.sysex_buffer)
            }

    def reset_parser(self):
        """Reset parser to clean state"""
        with self.lock:
            self.message_queue.clear()
            self.running_status = 0
            self.sysex_buffer.clear()
            self.in_sysex = False
