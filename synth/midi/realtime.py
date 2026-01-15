"""
Real-time MIDI Processing

Handles real-time MIDI input processing for live synthesizer control.
Converts raw MIDI bytes to structured messages and manages real-time message buffering.
"""

import time
from typing import List, Optional, Callable, Dict, Any
import threading

from .message import MIDIMessage
from .types import MIDIStatus, get_message_type_from_status


class RealtimeParser:
    """
    Real-time MIDI byte parser for live synthesizer input.

    Converts raw MIDI bytes from devices into structured MIDIMessage objects
    with proper running status handling and system exclusive processing.
    Supports all standard MIDI message types for complete synthesizer compatibility.
    """

    def __init__(self):
        """Initialize the real-time MIDI parser."""
        self.last_status = 0x00  # For running status support
        self.sysex_buffer: List[int] = []
        self.in_sysex = False
        self.pending_message: Optional[Dict[str, Any]] = None  # For multi-byte messages
        self.lock = threading.RLock()

    def parse_bytes(self, data: bytes) -> List[MIDIMessage]:
        """
        Parse raw MIDI bytes into structured messages.

        Args:
            data: Raw MIDI byte data

        Returns:
            List of parsed MIDIMessage objects
        """
        with self.lock:
            messages = []

            for byte in data:
                message = self._parse_byte(byte)
                if message:
                    messages.append(message)

            # Clear any pending state after processing
            self.pending_message = None

            return messages

    def _parse_byte(self, byte: int) -> Optional[MIDIMessage]:
        """
        Parse a single MIDI byte with complete message type support.

        Args:
            byte: MIDI byte value (0-255)

        Returns:
            Parsed MIDIMessage or None if incomplete
        """
        # Handle system exclusive
        if self.in_sysex:
            if byte == MIDIStatus.END_OF_EXCLUSIVE:
                # End of sysex
                self.in_sysex = False
                sysex_data = self.sysex_buffer.copy()
                self.sysex_buffer.clear()

                # Create sysex message
                return MIDIMessage(
                    type='sysex',
                    data={'raw_data': sysex_data}
                )
            else:
                # Continue collecting sysex data
                self.sysex_buffer.append(byte)
            return None

        # Check for status byte
        if byte & 0x80:
            # Status byte - handle system messages and start new channel messages
            if byte == MIDIStatus.SYSTEM_EXCLUSIVE:
                # Start of system exclusive
                self.in_sysex = True
                self.sysex_buffer.clear()
                self.pending_message = None  # Cancel any pending message
                return None
            elif byte >= MIDIStatus.TIMING_CLOCK and byte != MIDIStatus.TUNE_REQUEST:
                # System real-time message (doesn't affect running status)
                return self._parse_system_message(byte)
            elif (byte >= MIDIStatus.TIME_CODE and byte <= MIDIStatus.SONG_SELECT) or byte == MIDIStatus.TUNE_REQUEST:
                # System common messages - handle immediately
                return self._parse_system_common_message(byte)
            else:
                # Channel message status - update running status and start new message
                self.last_status = byte
                self.pending_message = None  # Cancel any pending message
                return None
        else:
            # Data byte - handle based on current state
            if self.pending_message:
                # Continue building pending message
                return self._continue_channel_message(byte)
            elif self.last_status and (self.last_status & 0xF0) in [0x80, 0x90, 0xA0, 0xB0, 0xE0]:
                # Start building a 2-byte channel message
                return self._start_channel_message(self.last_status, byte)
            elif self.last_status and (self.last_status & 0xF0) in [0xC0, 0xD0]:
                # 1-byte channel message with running status
                return self._parse_channel_message_single(self.last_status, byte)
            elif self.pending_message and self.pending_message['type'] in ['time_code', 'song_select']:
                # Handle system common messages that need data
                return self._continue_system_common_message(byte)
            elif self.pending_message and self.pending_message['type'] == 'song_position':
                # Start song position with first data byte
                self.pending_message['first_data'] = byte
                return None
            else:
                # Unexpected data byte - ignore
                return None

    def _parse_system_message(self, status: int) -> Optional[MIDIMessage]:
        """Parse system real-time message."""
        message_type = get_message_type_from_status(status)
        # System real-time messages have no data
        return MIDIMessage(type=message_type)

    def _parse_system_common_message(self, status: int) -> Optional[MIDIMessage]:
        """
        Parse system common messages (time code, song position, song select, tune request).
        """
        message_type = get_message_type_from_status(status)

        if message_type == 'time_code':
            # Time code needs 1 data byte - start pending message
            self.pending_message = {
                'type': 'time_code'
            }
            return None
        elif message_type == 'song_position':
            # Song position needs 2 data bytes - start pending message
            self.pending_message = {
                'type': 'song_position'
            }
            return None
        elif message_type == 'song_select':
            # Song select needs 1 data byte - start pending message
            self.pending_message = {
                'type': 'song_select'
            }
            return None
        elif message_type == 'tune_request':
            # Tune request has no data
            return MIDIMessage(type='tune_request')

        return None

    def _start_channel_message(self, status: int, first_data: int) -> Optional[MIDIMessage]:
        """
        Start parsing a 2-byte channel message.
        """
        message_type = get_message_type_from_status(status)
        channel = status & 0x0F

        # Create pending message for 2-byte messages
        self.pending_message = {
            'status': status,
            'type': message_type,
            'channel': channel,
            'first_data': first_data
        }
        return None  # Wait for second data byte

    def _continue_channel_message(self, byte: int) -> Optional[MIDIMessage]:
        """
        Continue parsing a pending message with the second data byte.
        """
        if not self.pending_message:
            return None

        msg = self.pending_message
        message_type = msg['type']

        # Clear pending message
        self.pending_message = None

        # Handle channel messages
        if 'channel' in msg:
            channel = msg['channel']
            first_data = msg['first_data']

            # Parse based on message type
            if message_type == 'note_off':
                return MIDIMessage(
                    type='note_off',
                    channel=channel,
                    data={'note': first_data, 'velocity': byte}
                )
            elif message_type == 'note_on':
                return MIDIMessage(
                    type='note_on',
                    channel=channel,
                    data={'note': first_data, 'velocity': byte}
                )
            elif message_type == 'poly_pressure':
                return MIDIMessage(
                    type='poly_pressure',
                    channel=channel,
                    data={'note': first_data, 'pressure': byte}
                )
            elif message_type == 'control_change':
                return MIDIMessage(
                    type='control_change',
                    channel=channel,
                    data={'controller': first_data, 'value': byte}
                )
            elif message_type == 'pitch_bend':
                # Combine LSB and MSB into 14-bit value
                pitch_value = (byte << 7) | first_data
                return MIDIMessage(
                    type='pitch_bend',
                    channel=channel,
                    data={'value': pitch_value}
                )
        else:
            # Handle system common messages
            if message_type == 'time_code':
                return MIDIMessage(
                    type='time_code',
                    data={'value': byte}
                )
            elif message_type == 'song_select':
                return MIDIMessage(
                    type='song_select',
                    data={'song': byte}
                )
            elif message_type == 'song_position':
                # For song position, we need the first data byte
                first_data = msg.get('first_data', 0)
                position = (byte << 7) | first_data
                return MIDIMessage(
                    type='song_position',
                    data={'position': position}
                )

        return None

    def _parse_channel_message_single(self, status: int, data: int) -> Optional[MIDIMessage]:
        """
        Parse a 1-byte channel message (program change, channel pressure).
        """
        message_type = get_message_type_from_status(status)
        channel = status & 0x0F

        if message_type == 'program_change':
            return MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': data}
            )
        elif message_type == 'channel_pressure':
            return MIDIMessage(
                type='channel_pressure',
                channel=channel,
                data={'pressure': data}
            )

        return None

    def _continue_system_common_message(self, byte: int) -> Optional[MIDIMessage]:
        """
        Continue parsing a system common message with data byte.
        """
        if not self.pending_message:
            return None

        msg = self.pending_message
        message_type = msg['type']

        # Clear pending message
        self.pending_message = None

        # Handle system common messages
        if message_type == 'time_code':
            return MIDIMessage(
                type='time_code',
                data={'value': byte}
            )
        elif message_type == 'song_select':
            return MIDIMessage(
                type='song_select',
                data={'song': byte}
            )

        return None

    def reset(self):
        """Reset parser to clean state."""
        with self.lock:
            self.last_status = 0x00
            self.sysex_buffer.clear()
            self.in_sysex = False
