"""
Real-time MIDI Processing

Handles real-time MIDI input processing for live synthesizer control.
Converts raw MIDI bytes to structured messages and manages real-time message buffering.
Supports both MIDI 1.0 and MIDI 2.0 Universal MIDI Packet (UMP) formats.
"""

import time
from typing import List, Optional, Callable, Dict, Any
import threading
import struct

from .message import MIDIMessage
from .types import MIDIStatus, get_message_type_from_status
from .ump_packets import UMPParser, UMPPacket, MIDI1ChannelVoicePacket, MIDI2ChannelVoicePacket, SysExUMP, UtilityUMP


class RealtimeParser:
    """
    Real-time MIDI byte parser for live synthesizer input.

    Converts raw MIDI bytes from devices into structured MIDIMessage objects
    with proper running status handling and system exclusive processing.
    Supports all standard MIDI message types for complete synthesizer compatibility.
    Includes support for MIDI 2.0 Universal MIDI Packet (UMP) format.
    """

    def __init__(self):
        """Initialize the real-time MIDI parser."""
        self.last_status = 0x00  # For running status support
        self.sysex_buffer: List[int] = []
        self.in_sysex = False
        self.pending_message: Optional[Dict[str, Any]] = None  # For multi-byte messages
        self.lock = threading.RLock()
        
        # UMP-specific state
        self.ump_parser = UMPParser()
        self.ump_buffer: bytes = b""
        self.is_ump_mode = False  # Whether we're currently in UMP mode

    def parse_bytes(self, data: bytes) -> List[MIDIMessage]:
        """
        Parse raw MIDI bytes into structured messages.
        Supports both MIDI 1.0 and MIDI 2.0 UMP formats.

        Args:
            data: Raw MIDI byte data

        Returns:
            List of parsed MIDIMessage objects
        """
        with self.lock:
            messages = []

            # Check if this looks like UMP data (starts with valid UMP message type)
            if len(data) >= 4:
                first_word = struct.unpack('>I', data[:4])[0]
                ump_type = (first_word >> 28) & 0xF
                
                # If it's a valid UMP message type, treat as UMP
                if ump_type in [0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0xF]:
                    self.is_ump_mode = True
                    # Process as UMP packets
                    ump_packets = self.ump_parser.parse_packet_stream(data)
                    for packet in ump_packets:
                        message = self._convert_ump_to_midimessage(packet)
                        if message:
                            messages.append(message)
                    return messages
                else:
                    self.is_ump_mode = False
            else:
                self.is_ump_mode = False

            # Process as MIDI 1.0 if not UMP
            if not self.is_ump_mode:
                for byte in data:
                    message = self._parse_byte(byte)
                    if message:
                        messages.append(message)

                # Clear any pending state after processing
                self.pending_message = None

            return messages

    def _convert_ump_to_midimessage(self, packet: UMPPacket) -> Optional[MIDIMessage]:
        """
        Convert a UMP packet to a MIDIMessage object.

        Args:
            packet: UMP packet object

        Returns:
            MIDIMessage object or None
        """
        from .ump_packets import MIDI1ChannelVoicePacket, MIDI2ChannelVoicePacket, SysExUMP, UtilityUMP
        from .ump_packets import MIDI1ToMIDI2Converter

        if isinstance(packet, MIDI2ChannelVoicePacket):
            # Convert MIDI 2.0 packet to MIDIMessage
            return self._convert_midi2_packet_to_message(packet)
        elif isinstance(packet, MIDI1ChannelVoicePacket):
            # Convert MIDI 1.0 packet to MIDIMessage
            return self._convert_midi1_packet_to_message(packet)
        elif isinstance(packet, SysExUMP):
            # Convert SysEx packet to MIDIMessage
            return self._convert_sysex_packet_to_message(packet)
        elif isinstance(packet, UtilityUMP):
            # Convert utility packet to MIDIMessage
            return self._convert_utility_packet_to_message(packet)
        else:
            # For other packet types, create a generic message
            return MIDIMessage(
                type='ump_packet',
                data={'ump_type': packet.ump_type, 'group': packet.group},
                timestamp=time.time()
            )

    def _convert_midi2_packet_to_message(self, packet: MIDI2ChannelVoicePacket) -> Optional[MIDIMessage]:
        """
        Convert MIDI 2.0 UMP packet to MIDIMessage.

        Args:
            packet: MIDI2ChannelVoicePacket object

        Returns:
            MIDIMessage object or None
        """
        status_byte = packet.get_status_byte()
        channel = status_byte & 0x0F
        message_type = (status_byte >> 4) & 0x0F

        # Extract data from the packet's data words
        data_word_1 = packet.data_word_1
        data_word_2 = packet.data_word_2

        # Create appropriate MIDIMessage based on message type
        if message_type == 0x8:  # Note Off
            note = (data_word_1 >> 24) & 0xFF
            velocity = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='note_off',
                channel=channel,
                data={'note': note, 'velocity': velocity},
                timestamp=time.time()
            )
        elif message_type == 0x9:  # Note On
            note = (data_word_1 >> 24) & 0xFF
            velocity = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='note_on',
                channel=channel,
                data={'note': note, 'velocity': velocity},
                timestamp=time.time()
            )
        elif message_type == 0xA:  # Poly Pressure
            note = (data_word_1 >> 24) & 0xFF
            pressure = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='poly_pressure',
                channel=channel,
                data={'note': note, 'pressure': pressure},
                timestamp=time.time()
            )
        elif message_type == 0xB:  # Control Change
            controller = (data_word_1 >> 24) & 0xFF
            value = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='control_change',
                channel=channel,
                data={'controller': controller, 'value': value},
                timestamp=time.time()
            )
        elif message_type == 0xC:  # Program Change
            program = (data_word_1 >> 24) & 0xFF
            return MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': program},
                timestamp=time.time()
            )
        elif message_type == 0xD:  # Channel Pressure
            pressure = (data_word_1 >> 24) & 0xFF
            return MIDIMessage(
                type='channel_pressure',
                channel=channel,
                data={'pressure': pressure},
                timestamp=time.time()
            )
        elif message_type == 0xE:  # Pitch Bend
            # MIDI 2.0 pitch bend is 32-bit
            pitch_value = data_word_1
            return MIDIMessage(
                type='pitch_bend',
                channel=channel,
                data={'value': pitch_value},
                timestamp=time.time()
            )
        # Add more message types as needed

        return None

    def _convert_midi1_packet_to_message(self, packet: MIDI1ChannelVoicePacket) -> Optional[MIDIMessage]:
        """
        Convert MIDI 1.0 UMP packet to MIDIMessage.

        Args:
            packet: MIDI1ChannelVoicePacket object

        Returns:
            MIDIMessage object or None
        """
        status_byte = packet.status_byte
        channel = status_byte & 0x0F
        message_type = (status_byte >> 4) & 0x0F

        if message_type == 0x8:  # Note Off
            return MIDIMessage(
                type='note_off',
                channel=channel,
                data={'note': packet.data1, 'velocity': packet.data2},
                timestamp=time.time()
            )
        elif message_type == 0x9:  # Note On
            return MIDIMessage(
                type='note_on',
                channel=channel,
                data={'note': packet.data1, 'velocity': packet.data2},
                timestamp=time.time()
            )
        elif message_type == 0xA:  # Poly Pressure
            return MIDIMessage(
                type='poly_pressure',
                channel=channel,
                data={'note': packet.data1, 'pressure': packet.data2},
                timestamp=time.time()
            )
        elif message_type == 0xB:  # Control Change
            return MIDIMessage(
                type='control_change',
                channel=channel,
                data={'controller': packet.data1, 'value': packet.data2},
                timestamp=time.time()
            )
        elif message_type == 0xC:  # Program Change
            return MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': packet.data1},
                timestamp=time.time()
            )
        elif message_type == 0xD:  # Channel Pressure
            return MIDIMessage(
                type='channel_pressure',
                channel=channel,
                data={'pressure': packet.data1},
                timestamp=time.time()
            )
        elif message_type == 0xE:  # Pitch Bend
            pitch_value = (packet.data2 << 7) | packet.data1
            return MIDIMessage(
                type='pitch_bend',
                channel=channel,
                data={'value': pitch_value},
                timestamp=time.time()
            )

        return None

    def _convert_sysex_packet_to_message(self, packet: SysExUMP) -> Optional[MIDIMessage]:
        """
        Convert SysEx UMP packet to MIDIMessage.

        Args:
            packet: SysExUMP object

        Returns:
            MIDIMessage object or None
        """
        return MIDIMessage(
            type='sysex',
            data={'raw_data': list(packet.sys_ex_data)},
            timestamp=time.time()
        )

    def _convert_utility_packet_to_message(self, packet: UtilityUMP) -> Optional[MIDIMessage]:
        """
        Convert Utility UMP packet to MIDIMessage.

        Args:
            packet: UtilityUMP object

        Returns:
            MIDIMessage object or None
        """
        if packet.utility_type == 0x1:  # JR Timestamp
            return MIDIMessage(
                type='jitter_reduction_timestamp',
                data={'timestamp': packet.data},
                timestamp=time.time()
            )
        # Add other utility message types as needed

        return None

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
                # Prevent buffer overflow by limiting sysex buffer size
                if len(self.sysex_buffer) < 1024:  # Reasonable limit for sysex messages
                    self.sysex_buffer.append(byte)
                else:
                    # Buffer overflow - reset parser state
                    self.reset()
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
            elif byte >= MIDIStatus.TIMING_CLOCK and byte <= MIDIStatus.SYSTEM_RESET:
                # System real-time message (doesn't affect running status)
                return self._parse_system_message(byte)
            elif (byte >= MIDIStatus.TIME_CODE and byte <= MIDIStatus.SONG_SELECT) or byte == MIDIStatus.TUNE_REQUEST:
                # System common messages - handle immediately
                return self._parse_system_common_message(byte)
            elif (byte & 0xF0) in [0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xD0, 0xE0]:
                # Channel message status - update running status and start new message
                self.last_status = byte
                self.pending_message = None  # Cancel any pending message
                return None
            else:
                # Unknown status byte - reset parser to prevent corruption
                self.reset()
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
            elif self.pending_message and self.pending_message.get('type') in ['time_code', 'song_select']:
                # Handle system common messages that need data
                return self._continue_system_common_message(byte)
            elif self.pending_message and self.pending_message.get('type') == 'song_position':
                # Start song position with first data byte
                self.pending_message['first_data'] = byte
                return None
            else:
                # Unexpected data byte - ignore and possibly reset if too many consecutive
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
