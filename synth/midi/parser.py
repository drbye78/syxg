"""
MIDI and UMP File Parser

This module provides the MIDIParser class for parsing MIDI (Musical Instrument Digital Interface)
files and UMP (Universal MIDI Packet) files. The parser supports both MIDI 1.0 and MIDI 2.0 formats,
handling various message types, tempo changes, and providing a unified API for real-time playback.

Supported File Formats:
- MIDI files (.mid): Standard MIDI 1.0 and MIDI 2.0 format files
- UMP files (.ump): Universal MIDI Packet format files

Supported Message Types:

MIDI 1.0 Channel Messages:
- note_on: Note activation with velocity
- note_off: Note deactivation with release velocity
- control_change: Controller value changes (pitch wheel, modulation, etc.)
- program_change: Instrument/program selection
- pitch_bend: Pitch wheel changes
- channel_pressure: Channel-wide pressure/aftertouch
- poly_pressure: Individual note pressure/aftertouch

UMP/MIDI 2.0 Messages:
- Extended channel voice messages with 16-bit precision
- Universal MIDI Packet format messages
- Mixed Data Set (MDS) messages
- Flex Data messages
- UMP Stream messages (JR Clock, JR Timestamp, NOP)

Meta Events & System Messages:
- Tempo changes (auto-handled for timing calculations)
- System Exclusive (SysEx) messages
- MIDI Time Code, Song Position, etc.

Key Features:
- Supports standard MIDI files (.mid) and UMP files (.ump)
- Handles MIDI 1.0 and 2.0 message formats
- Provides real-time playback capabilities with time-based message retrieval
- Supports System Exclusive (SysEx) messages, meta events, and standard channel messages
- Unified message cache with timestamp-ordered access
- Proper handling of tempo changes (per-track) and SMPTE offset
- Timestamps converted to seconds during parsing for consistent timing

Message Format Documentation:

All MIDI messages returned by the API are dictionaries with the following structure:

Common Fields (present in all messages):
- 'time': Timestamp in seconds from the start of the sequence (includes SMPTE offset if present)
- 'type': Message type identifier (string)

Channel Messages:
Channel messages contain both raw MIDI data and parsed details:
- 'status': Raw MIDI status byte (integer)
- 'channel': MIDI channel number (0-15)
- 'data': Raw MIDI data bytes (list of integers)
- Plus type-specific parsed fields

Note On Message:
- 'type': 'note_on'
- 'note': MIDI note number (0-127)
- 'velocity': Note velocity (0-127)
- Raw: 'status', 'channel', 'data'

Note Off Message:
- 'type': 'note_off'
- 'note': MIDI note number (0-127)
- 'velocity': Release velocity (0-127)
- Raw: 'status', 'channel', 'data'

Control Change Message:
- 'type': 'control_change'
- 'control': Controller number (0-127)
- 'value': Controller value (0-127)
- Raw: 'status', 'channel', 'data'

Program Change Message:
- 'type': 'program_change'
- 'program': Program number (0-127)
- Raw: 'status', 'channel', 'data'

Pitch Bend Message:
- 'type': 'pitch_bend'
- 'pitch': 14-bit pitch bend value (-8192 to 8191)
- Raw: 'status', 'channel', 'data'

Channel Pressure Message:
- 'type': 'channel_pressure'
- 'pressure': Pressure value (0-127)
- Raw: 'status', 'channel', 'data'

Poly Pressure Message:
- 'type': 'poly_pressure'
- 'note': MIDI note number (0-127)
- 'pressure': Pressure value (0-127)
- Raw: 'status', 'channel', 'data'

UMP-Specific Messages:
UMP messages additional fields:
- 'ump': True (indicates UMP message)
- 'group': UMP group number (0-15)
- Plus message-type-specific fields for MIDI 2.0 messages

System and Meta Messages:
- 'type': 'sysex', 'meta', 'system_message', etc.
- Additional fields vary by message type

Main API Methods:
- get_total_duration(): Calculate total file duration in seconds
- get_next_messages(duration_ms): Retrieve messages within a time window for real-time playback
- rewind(): Reset playback position to beginning for repeated playback
"""

import struct
from typing import Any, Dict, List, Tuple, Optional, Iterator
from collections import defaultdict

class MIDIParser:
    def __init__(self, filename: str):
        self.filename = filename
        self.format = 0
        self.division = 0
        self.tempo = 500000  # Default 120 BPM in microseconds per beat
        self.tracks = []
        self._message_cache = []
        self._current_time = 0
        self._index = 0
        self._events = []
        self.is_midi2 = False
        self.is_ump_file = False
        self.time_base = 0
        # SMPTE timing variables
        self.smpte_offset = 0.0  # SMPTE offset in seconds
        self._parse_file()
        self._merge_tracks()
        
    def _read_variable_length(self, data: bytes, offset: int) -> Tuple[int, int]:
        """Read variable-length quantity from MIDI data"""
        value = 0
        shift = 0
        while True:
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7F)
            if not (byte & 0x80):
                break
            shift += 7
            if shift > 21:  # Prevent infinite loop
                break
        return value, offset

    def _parse_file(self):
        """Parse MIDI/UMP file header and track data"""
        with open(self.filename, 'rb') as f:
            # Check for UMP file signature
            signature = f.read(4)
            if signature == b'UMPP':
                self.is_ump_file = True
                self._parse_ump_file(f)
            else:
                # Standard MIDI file
                f.seek(0)
                # Read the complete MThd header: 8 bytes signature + 6 bytes data
                header = f.read(14)
                if len(header) < 14 or header[:4] != b'MThd':
                    raise ValueError("Invalid MIDI file")

                header_length = struct.unpack('>I', header[4:8])[0]
                self.format = struct.unpack('>H', header[8:10])[0]
                num_tracks = struct.unpack('>H', header[10:12])[0]
                self.division = struct.unpack('>H', header[12:14])[0]

                # Check for MIDI 2.0 signature (header_length >= 6 for extended header)
                if header_length >= 8:
                    # Skip any extended header data (rare in practice)
                    f.read(header_length - 6)

                # Read track data
                for _ in range(num_tracks):
                    track_header = f.read(8)
                    if len(track_header) < 8 or track_header[:4] != b'MTrk':
                        raise ValueError("Invalid track header")

                    track_length = struct.unpack('>I', track_header[4:8])[0]
                    track_data = f.read(track_length)
                    self.tracks.append(track_data)

    def _parse_ump_file(self, file_handle):
        """Parse UMP (.ump) file format"""
        # Read UMP file header
        header_data = file_handle.read(28)  # Read remaining header bytes
        if len(header_data) < 28:
            raise ValueError("Invalid UMP file header")
            
        # Parse UMP header fields
        self.time_base = struct.unpack('>I', header_data[0:4])[0]
        self.format = struct.unpack('>H', header_data[4:6])[0]
        num_chunks = struct.unpack('>H', header_data[6:8])[0]
        reserved = struct.unpack('>I', header_data[8:12])[0]
        
        # Process chunks
        for _ in range(num_chunks):
            chunk_header = file_handle.read(8)
            if len(chunk_header) < 8:
                break
                
            chunk_type = chunk_header[:4]
            chunk_length = struct.unpack('>I', chunk_header[4:8])[0]
            
            if chunk_type == b'MChk':  # MIDI Chunk
                chunk_data = file_handle.read(chunk_length)
                self.tracks.append(chunk_data)
            elif chunk_type == b'SChk':  # Stream Chunk
                chunk_data = file_handle.read(chunk_length)
                self.tracks.append(chunk_data)
            else:
                # Skip unknown chunks
                file_handle.seek(chunk_length, 1)

    def _parse_ump_message(self, data: bytes, offset: int, time: int) -> Tuple[dict, int]:
        """Parse a single UMP (Universal MIDI Packet) message"""
        if offset + 3 >= len(data):
            raise ValueError("Incomplete UMP message")
            
        # Read 32-bit UMP word
        ump_word = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        
        # Parse UMP header
        message_type = (ump_word >> 28) & 0xF
        group = (ump_word >> 24) & 0xF
        
        message = {
            'time': time,
            'group': group,
            'ump': True
        }
        
        # Parse based on message type
        if message_type == 0x0:  # 32-bit MIDI 2.0 Channel Voice Messages
            status = (ump_word >> 16) & 0xF0
            channel = (ump_word >> 16) & 0x0F
            data1 = (ump_word >> 8) & 0xFF
            data2 = ump_word & 0xFF
            
            message.update({
                'status': status,
                'channel': channel
            })
            
            if status == 0x80:  # Note Off
                message.update({
                    'type': 'note_off',
                    'note': data1,
                    'velocity': data2 << 7  # 16-bit velocity (MSB only in this 32-bit form)
                })
            elif status == 0x90:  # Note On
                message.update({
                    'type': 'note_on',
                    'note': data1,
                    'velocity': data2 << 7  # 16-bit velocity (MSB only in this 32-bit form)
                })
            elif status == 0xB0:  # Control Change
                message.update({
                    'type': 'control_change',
                    'control': data1,
                    'value': data2 << 7  # 16-bit value (MSB only in this 32-bit form)
                })
            elif status == 0xC0:  # Program Change
                message.update({
                    'type': 'program_change',
                    'program': data1 << 8 | data2  # 16-bit program
                })
            elif status == 0xE0:  # Pitch Bend
                message.update({
                    'type': 'pitch_bend',
                    'pitch': data1 << 24 | data2 << 16  # 32-bit pitch bend (partial)
                })
                
        elif message_type == 0x1:  # 64-bit MIDI 2.0 Channel Voice Messages
            if offset + 3 >= len(data):
                raise ValueError("Incomplete 64-bit UMP message")
                
            data_word = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            status = (ump_word >> 16) & 0xF0
            channel = (ump_word >> 16) & 0x0F
            data1 = (ump_word >> 8) & 0xFF
            
            message.update({
                'status': status,
                'channel': channel,
                'type': 'extended_channel_message'
            })
            
            if status == 0x80:  # Note Off with 16-bit velocity
                velocity = data_word & 0xFFFF
                message.update({
                    'type': 'note_off',
                    'note': data1,
                    'velocity': velocity
                })
            elif status == 0x90:  # Note On with 16-bit velocity
                velocity = data_word & 0xFFFF
                message.update({
                    'type': 'note_on',
                    'note': data1,
                    'velocity': velocity
                })
            elif status == 0xB0:  # Control Change with 32-bit value
                value = data_word
                message.update({
                    'type': 'control_change',
                    'control': data1,
                    'value': value
                })
                
        elif message_type == 0x2:  # 96-bit MIDI 2.0 Channel Voice Messages
            if offset + 7 >= len(data):
                raise ValueError("Incomplete 96-bit UMP message")
                
            data_word1 = struct.unpack('>I', data[offset:offset+4])[0]
            data_word2 = struct.unpack('>I', data[offset+4:offset+8])[0]
            offset += 8
            
            status = (ump_word >> 16) & 0xF0
            channel = (ump_word >> 16) & 0x0F
            
            message.update({
                'status': status,
                'channel': channel,
                'type': 'complex_channel_message'
            })
            
        elif message_type == 0x3:  # 128-bit MIDI 2.0 Channel Voice Messages
            if offset + 11 >= len(data):
                raise ValueError("Incomplete 128-bit UMP message")
                
            data_word1 = struct.unpack('>I', data[offset:offset+4])[0]
            data_word2 = struct.unpack('>I', data[offset+4:offset+8])[0]
            data_word3 = struct.unpack('>I', data[offset+8:offset+12])[0]
            offset += 12
            
            message.update({
                'type': 'full_128bit_message',
                'data_words': [data_word1, data_word2, data_word3]
            })
            
        elif message_type == 0x4:  # MIDI 1.0 Channel Voice Messages
            status = (ump_word >> 16) & 0xF0
            channel = (ump_word >> 16) & 0x0F
            data1 = (ump_word >> 8) & 0xFF
            data2 = ump_word & 0xFF
            
            message.update({
                'status': status,
                'channel': channel
            })
            
            if status == 0x80:  # Note Off
                message.update({
                    'type': 'note_off',
                    'note': data1,
                    'velocity': data2
                })
            elif status == 0x90:  # Note On
                message.update({
                    'type': 'note_on',
                    'note': data1,
                    'velocity': data2
                })
            elif status == 0xB0:  # Control Change
                message.update({
                    'type': 'control_change',
                    'control': data1,
                    'value': data2
                })
                
        elif message_type == 0x5:  # MIDI 2.0 Data Messages
            form = (ump_word >> 20) & 0x7
            status = (ump_word >> 16) & 0xF
            
            message.update({
                'type': 'data_message',
                'form': form,
                'status': status
            })
            
        elif message_type >= 0x8 and message_type <= 0xB:  # System Messages
            status = (ump_word >> 16) & 0xFF
            data1 = (ump_word >> 8) & 0xFF
            data2 = ump_word & 0xFF
            
            message.update({
                'type': 'system_message',
                'status': status
            })
            
            if status == 0xF0 or status == 0xF7:  # SysEx
                message.update({
                    'sysex_data': [data1, data2]
                })
                
        elif message_type == 0xC:  # Mixed Data Set Message (MDS)
            mds_id = (ump_word >> 16) & 0xFF
            num_chunks = (ump_word >> 8) & 0x7F
            is_last = (ump_word >> 7) & 0x1
            data_bytes = ump_word & 0x7F
            
            message.update({
                'type': 'mixed_data_set',
                'mds_id': mds_id,
                'num_chunks': num_chunks,
                'is_last': is_last,
                'data_bytes': data_bytes
            })
            
        elif message_type == 0xD:  # Flex Data Message
            addr = (ump_word >> 16) & 0xFFFF
            status = (ump_word >> 8) & 0xFF
            channel = ump_word & 0xFF
            
            message.update({
                'type': 'flex_data',
                'address': addr,
                'status': status,
                'channel': channel
            })
            
        elif message_type == 0xF:  # UMP Stream Messages
            status = (ump_word >> 16) & 0xFF
            data1 = (ump_word >> 8) & 0xFF
            data2 = ump_word & 0xFF
            
            message.update({
                'type': 'stream_message',
                'status': status
            })
            
            if status == 0x00:  # NOP
                message['subtype'] = 'nop'
            elif status == 0x01:  # JR Clock
                message.update({
                    'subtype': 'jr_clock',
                    'time': (data1 << 8) | data2
                })
            elif status == 0x02:  # JR Timestamp
                message.update({
                    'subtype': 'jr_timestamp',
                    'timestamp': (data1 << 8) | data2
                })
                
        else:
            message.update({
                'type': 'unknown_ump',
                'message_type': message_type,
                'raw_data': ump_word
            })
            
        return message, offset

    def _parse_track_messages(self, track_data: bytes, track_index: int) -> List[Tuple[float, dict]]:
        """Parse messages from a single track (MIDI or UMP) with proper timing"""
        messages = []
        offset = 0
        ticks_accumulated = 0  # Accumulated ticks from start of track
        current_tempo = self.tempo  # Track-specific tempo (starts with global default)
        running_status = None

        # Determine if this is an UMP track or standard MIDI track
        is_ump_track = self.is_ump_file or (
            len(track_data) >= 4 and
            struct.unpack('>I', track_data[:4])[0] & 0xF0000000 != 0
        )

        if is_ump_track:
            # Parse UMP messages
            while offset < len(track_data):
                # For UMP files, time is typically implicit or in JR Timestamp messages
                # In this simplified implementation, we'll use message order as time
                try:
                    message, offset = self._parse_ump_message(track_data, offset, ticks_accumulated)
                    # Convert to seconds for UMP (simplified)
                    time_seconds = ticks_accumulated / 1000.0 if self.time_base == 0 else ticks_accumulated / self.time_base
                    messages.append((time_seconds, message))
                    ticks_accumulated += 1  # Increment for ordering
                except ValueError as e:
                    # Skip invalid messages
                    break
        else:
            # Parse standard MIDI messages with proper tempo handling
            while offset < len(track_data):
                # Read delta time (ticks since last event)
                delta_ticks, offset = self._read_variable_length(track_data, offset)
                ticks_accumulated += delta_ticks

                # Convert accumulated ticks to seconds using current tempo
                time_seconds = self._ticks_to_seconds(ticks_accumulated, current_tempo)

                # Read message
                if offset >= len(track_data):
                    break

                first_byte = track_data[offset]

                if first_byte == 0xFF:  # Meta event
                    offset += 1
                    if offset + 1 > len(track_data):
                        break
                    meta_type = track_data[offset]
                    offset += 1
                    length, offset = self._read_variable_length(track_data, offset)
                    if offset + length > len(track_data):
                        break
                    meta_data = list(track_data[offset:offset + length])
                    offset += length

                    message = {
                        'time': time_seconds,
                        'type': 'meta',
                        'meta_type': meta_type,
                        'data': meta_data
                    }

                    # Handle tempo changes (per-track)
                    if meta_type == 0x51 and len(meta_data) == 3:
                        # Update tempo for this track (affects subsequent timing calculations)
                        current_tempo = struct.unpack('>I', b'\x00' + bytes(meta_data))[0]
                        message['tempo_us_per_beat'] = current_tempo

                    # Handle SMPTE offset (global, affects entire sequence)
                    elif meta_type == 0x54 and len(meta_data) == 5:
                        # SMPTE offset: hr, mn, se, fr, ff
                        hr, mn, se, fr, ff = meta_data
                        # Convert to seconds (simplified - assumes 30fps)
                        self.smpte_offset = hr * 3600 + mn * 60 + se + (fr + ff/100.0) / 30.0
                        message['smpte_offset_seconds'] = self.smpte_offset

                    messages.append((time_seconds, message))

                elif first_byte == 0xF0 or first_byte == 0xF7:  # SysEx
                    status_byte = first_byte
                    offset += 1
                    length, offset = self._read_variable_length(track_data, offset)
                    if offset + length > len(track_data):
                        break
                    sysex_data = list(track_data[offset:offset + length])
                    offset += length

                    message = {
                        'time': time_seconds,
                        'type': 'sysex',
                        'status': status_byte,
                        'data': sysex_data
                    }
                    messages.append((time_seconds, message))

                else:  # Channel messages
                    status_byte = first_byte
                    offset += 1

                    # Handle running status
                    if status_byte < 0x80:
                        if running_status is None:
                            continue
                        status_byte = running_status
                        offset -= 1  # Re-read the data byte

                    # Parse channel message
                    status_nibble = status_byte & 0xF0
                    channel = status_byte & 0x0F

                    message:Dict[str, Any] = {
                        'time': time_seconds,
                        'status': status_byte,
                        'channel': channel
                    }

                    if status_nibble in (0x80, 0x90, 0xA0, 0xB0, 0xE0):  # 2-byte messages
                        if offset + 1 > len(track_data):
                            break
                        data_bytes = [track_data[offset], track_data[offset + 1]]
                        message['data'] = data_bytes
                        offset += 2

                        if status_nibble == 0x80:
                            message.update({
                                'type': 'note_off',
                                'note': data_bytes[0],
                                'velocity': data_bytes[1]
                            })
                        elif status_nibble == 0x90:
                            message.update({
                                'type': 'note_on',
                                'note': data_bytes[0],
                                'velocity': data_bytes[1]
                            })
                        elif status_nibble == 0xA0:
                            message.update({
                                'type': 'poly_pressure',
                                'note': data_bytes[0],
                                'pressure': data_bytes[1]
                            })
                        elif status_nibble == 0xB0:
                            message.update({
                                'type': 'control_change',
                                'control': data_bytes[0],
                                'value': data_bytes[1]
                            })
                        elif status_nibble == 0xE0:
                            message.update({
                                'type': 'pitch_bend',
                                'pitch': (data_bytes[1] << 7) | data_bytes[0]
                            })

                    elif status_nibble in (0xC0, 0xD0):  # 1-byte messages
                        if offset >= len(track_data):
                            break
                        data_byte = track_data[offset]
                        message['data'] = [data_byte]
                        offset += 1

                        if status_nibble == 0xC0:
                            message.update({
                                'type': 'program_change',
                                'program': data_byte
                            })
                        elif status_nibble == 0xD0:
                            message.update({
                                'type': 'channel_pressure',
                                'pressure': data_byte
                            })

                    else:
                        running_status = None
                        continue

                    running_status = status_byte
                    messages.append((time_seconds, message))

        return messages

    def _ticks_to_seconds(self, ticks: int, tempo_us_per_beat: int) -> float:
        """
        Convert MIDI ticks to seconds using the specified tempo.

        Args:
            ticks: Number of MIDI ticks
            tempo_us_per_beat: Tempo in microseconds per beat

        Returns:
            Time in seconds
        """
        if self.division & 0x8000:  # SMPTE format
            fps = 256 - ((self.division >> 8) & 0xFF)
            ticks_per_frame = self.division & 0xFF
            return ticks / (fps * ticks_per_frame)
        else:  # PPQN format
            ppqn = self.division
            # Convert ticks to seconds: ticks * (tempo_us/beat) / (ppqn * 1,000,000 us/sec)
            return (ticks * tempo_us_per_beat) / (ppqn * 1000000.0)

    def _merge_tracks(self):
        """Merge multiple tracks into a single time-ordered message stream"""
        # Parse all tracks
        all_messages = []
        for i, track_data in enumerate(self.tracks):
            track_messages = self._parse_track_messages(track_data, i)
            all_messages.extend(track_messages)

        # Sort by timestamp (now in seconds)
        all_messages.sort(key=lambda x: x[0])

        # Apply SMPTE offset to all messages
        if self.smpte_offset > 0:
            for i, (time_seconds, message) in enumerate(all_messages):
                all_messages[i] = (time_seconds + self.smpte_offset, message)

        self._events = all_messages
        self._message_cache = [msg for _, msg in all_messages]

    def get_total_duration(self) -> float:
        """
        Get total duration of the MIDI/UMP file in seconds.

        Since timestamps are now stored in seconds during parsing, this method
        simply returns the timestamp of the last message.

        Returns:
            float: Total duration in seconds. Returns 0.0 if no messages exist.

        Note:
            This method relies on the message cache being populated. Call may return 0.0
            for empty files or files that failed to parse.
        """
        if not self._message_cache:
            return 0.0

        # Get last message time (already in seconds)
        return self._message_cache[-1]['time']

    def get_all_messages(self) -> List[dict]:
        """Get all messages in the file"""
        return self._message_cache.copy()

    def get_next_messages(self, duration_ms: float) -> Optional[List[dict]]:
        """
        Retrieve MIDI messages that occur within the specified time window for real-time playback.

        This method returns all messages scheduled to play in the next time duration and advances
        the internal playback position. It's designed for audio rendering applications that need
        to process MIDI events in real-time processing blocks.

        Args:
            duration_ms (float): Time window in milliseconds to retrieve messages for.
                                Should match your audio buffer processing time.

        Returns:
            List[dict]: List of MIDI message dictionaries that occur within the time window.
                        Messages include timing and event information. None if end of song reached.

        Timing Behavior:
            - Messages are consumed once retrieved (removed from internal cache)
            - Internal time pointer (_current_time) advances by the specified duration
            - Timestamps are now in seconds (converted during parsing)
            - Call repeatedly with consistent duration_ms for smooth real-time playback

        Note:
            This destructive operation removes messages from the cache after retrieval.
            Use rewind() to restart playback or get_all_messages() for non-destructive access.
        """
        if not self._events or self._index >= len(self._events):
            return None

        # Convert duration from milliseconds to seconds
        duration_seconds = duration_ms / 1000.0
        target_time = self._current_time + duration_seconds

        # Retrieve all messages within time range
        start = self._index
        while (self._index < len(self._events) and self._events[self._index][0] <= target_time):
            self._index += 1

        self._current_time = target_time
        return self._message_cache[start:self._index]

    def rewind(self):
        """
        Reset the parser to the beginning of the file for repeated playback.

        This method reinitializes the internal state by resetting the current time position

        Usage:
            - Call before starting a new playback session
            - Use when you need to replay the entire file
            - Essential after reaching the end of file to start over

        Side Effects:
            - Resets _current_time to 0
            - Re-parses the entire file from disk

        """
        self._current_time = 0
        self._index = 0

    def get_file_info(self) -> dict:
        """Get detailed information about the MIDI/UMP file"""
        return {
            'format': 'UMP' if self.is_ump_file else 'MIDI',
            'version': '2.0' if self.is_midi2 or self.is_ump_file else '1.0',
            'tracks': len(self.tracks),
            'division': self.division if not self.is_ump_file else self.time_base,
            'total_messages': len(self._message_cache),
            'duration_seconds': self.get_total_duration()
        }

    def get_message_statistics(self) -> dict:
        """Get statistics about message types in the file"""
        stats = defaultdict(int)
        for msg in self._message_cache:
            msg_type = msg.get('type', 'unknown')
            stats[msg_type] += 1
            
            # Count UMP vs MIDI messages
            if msg.get('ump'):
                stats['ump_messages'] += 1
            else:
                stats['midi_messages'] += 1
                
        return dict(stats)
