"""
File-based MIDI Processing

Handles MIDI file parsing for SMF (Standard MIDI Files) and UMP (Universal MIDI Packet) formats.
Provides high-level file parsing with proper timing and metadata handling.
"""

import os
from typing import List, Optional, Tuple
import struct

from .message import MIDIMessage
from .types import MIDIStatus, MessageType


class FileParser:
    """
    MIDI file parser for SMF and UMP formats.

    Parses MIDI files into structured MIDIMessage objects with proper timing
    and metadata handling. Supports both Standard MIDI Files (.mid) and
    Universal MIDI Packet files (.ump).
    """

    def __init__(self):
        """Initialize the file parser."""
        self.filename = ""
        self.format = 0
        self.tracks = []
        self.division = 0
        self.tempo = 500000  # Default 120 BPM
        self.is_ump_file = False
        self.time_base = 0
        self.smpte_offset = 0.0
        # Import UMP parser
        try:
            from .ump_packets import UMPParser
            self.ump_parser = UMPParser
        except ImportError:
            self.ump_parser = None

    def parse_file(self, filename: str) -> List[MIDIMessage]:
        """
        Parse a MIDI file and return structured messages.

        Args:
            filename: Path to MIDI file (.mid, .midi, .ump)

        Returns:
            List of MIDIMessage objects in chronological order

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"MIDI file not found: {filename}")

        self.filename = filename
        self._reset_state()

        with open(filename, 'rb') as f:
            # Check for UMP file signature
            signature = f.read(4)
            if signature == b'UMPP':
                self.is_ump_file = True
                return self._parse_ump_file(f)
            else:
                # Standard MIDI file
                f.seek(0)
                return self._parse_smf_file(f)

    def _reset_state(self):
        """Reset parser state for new file."""
        self.format = 0
        self.tracks = []
        self.division = 0
        self.tempo = 500000
        self.is_ump_file = False
        self.time_base = 0
        self.smpte_offset = 0.0

    def _parse_smf_file(self, file_handle) -> List[MIDIMessage]:
        """
        Parse Standard MIDI File format.

        Args:
            file_handle: Open file handle positioned at start

        Returns:
            List of MIDIMessage objects
        """
        try:
            # Read MThd header
            header = file_handle.read(14)
            if len(header) < 14 or header[:4] != b'MThd':
                raise ValueError("Invalid MIDI file header - missing or incorrect MThd signature")

            header_length = struct.unpack('>I', header[4:8])[0]
            if header_length < 6:
                raise ValueError("Invalid MIDI header length")
            
            self.format = struct.unpack('>H', header[8:10])[0]
            if self.format not in [0, 1, 2]:
                print(f"Warning: Unknown MIDI format {self.format}, continuing with parsing")
            
            num_tracks = struct.unpack('>H', header[10:12])[0]
            if num_tracks == 0:
                print("Warning: MIDI file has no tracks")
                return []
                
            self.division = struct.unpack('>H', header[12:14])[0]

            # Skip extended header if present
            if header_length > 6:
                file_handle.read(header_length - 6)

            # Read tracks with error handling
            for i in range(num_tracks):
                track_header = file_handle.read(8)
                if len(track_header) < 8:
                    print(f"Warning: Unexpected end of file while reading track {i} header")
                    break
                    
                if track_header[:4] != b'MTrk':
                    print(f"Warning: Invalid track header at track {i}, expected MTrk")
                    continue

                track_length = struct.unpack('>I', track_header[4:8])[0]
                if track_length > 100 * 1024 * 1024:  # 100MB limit to prevent memory issues
                    print(f"Warning: Track {i} appears to have invalid length ({track_length}), skipping")
                    continue
                    
                track_data = file_handle.read(track_length)
                if len(track_data) != track_length:
                    print(f"Warning: Track {i} has unexpected length (expected {track_length}, got {len(track_data)})")
                    # Truncate to actual length if shorter, or skip if too long
                    if len(track_data) < track_length:
                        continue
                
                self.tracks.append(track_data)

            # Parse all tracks and merge
            return self._parse_and_merge_tracks()
            
        except struct.error as e:
            raise ValueError(f"Error parsing MIDI file structure: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error parsing MIDI file: {e}")

    def _parse_ump_file(self, file_handle) -> List[MIDIMessage]:
        """
        Parse Universal MIDI Packet file format.

        Args:
            file_handle: Open file handle positioned after UMPP signature

        Returns:
            List of MIDIMessage objects
        """
        if not self.ump_parser:
            raise RuntimeError("UMP parser not available")

        # Read UMP header
        header_data = file_handle.read(28)
        if len(header_data) < 28:
            raise ValueError("Invalid UMP file header")

        self.time_base = struct.unpack('>I', header_data[0:4])[0]
        self.format = struct.unpack('>H', header_data[4:6])[0]
        num_chunks = struct.unpack('>H', header_data[6:8])[0]

        all_messages = []

        # Read chunks
        for _ in range(num_chunks):
            chunk_header = file_handle.read(8)
            if len(chunk_header) < 8:
                break

            chunk_type = chunk_header[:4]
            chunk_length = struct.unpack('>I', chunk_header[4:8])[0]

            if chunk_type in (b'MChk', b'SChk'):  # MIDI or Stream chunk
                chunk_data = file_handle.read(chunk_length)
                
                # Parse UMP packets in the chunk
                ump_packets = self.ump_parser.parse_packet_stream(chunk_data)
                
                # Convert UMP packets to MIDIMessage objects
                chunk_messages = self._convert_ump_packets_to_messages(ump_packets)
                all_messages.extend(chunk_messages)
            else:
                # Skip unknown chunks
                file_handle.seek(chunk_length, 1)

        return all_messages

    def _convert_ump_packets_to_messages(self, ump_packets: List) -> List[MIDIMessage]:
        """
        Convert UMP packets to MIDIMessage objects.

        Args:
            ump_packets: List of UMP packet objects

        Returns:
            List of MIDIMessage objects
        """
        from .ump_packets import MIDI1ChannelVoicePacket, MIDI2ChannelVoicePacket, SysExUMP, UtilityUMP
        from .ump_packets import MIDI1ToMIDI2Converter
        
        messages = []
        
        for packet in ump_packets:
            if isinstance(packet, MIDI2ChannelVoicePacket):
                # Convert MIDI 2.0 packet to MIDIMessage
                msg = self._convert_midi2_packet_to_message(packet)
                if msg:
                    messages.append(msg)
            elif isinstance(packet, MIDI1ChannelVoicePacket):
                # Convert MIDI 1.0 packet to MIDIMessage
                msg = self._convert_midi1_packet_to_message(packet)
                if msg:
                    messages.append(msg)
            elif isinstance(packet, SysExUMP):
                # Convert SysEx packet to MIDIMessage
                msg = self._convert_sysex_packet_to_message(packet)
                if msg:
                    messages.append(msg)
            elif isinstance(packet, UtilityUMP):
                # Convert utility packet to MIDIMessage
                msg = self._convert_utility_packet_to_message(packet)
                if msg:
                    messages.append(msg)
        
        return messages

    def _convert_midi2_packet_to_message(self, packet) -> Optional[MIDIMessage]:
        """
        Convert MIDI 2.0 UMP packet to MIDIMessage.

        Args:
            packet: MIDI2ChannelVoicePacket object

        Returns:
            MIDIMessage object or None
        """
        # Actually, let's get the proper MIDI 2.0 data
        status_byte = packet.get_status_byte()
        channel = status_byte & 0x0F
        message_type = (status_byte >> 4) & 0x0F
        
        # Extract data from the packet's data words
        # This is a simplified extraction - in reality, MIDI 2.0 has more complex data formats
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
                timestamp=0.0  # Will be set by caller
            )
        elif message_type == 0x9:  # Note On
            note = (data_word_1 >> 24) & 0xFF
            velocity = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='note_on',
                channel=channel,
                data={'note': note, 'velocity': velocity},
                timestamp=0.0
            )
        elif message_type == 0xB:  # Control Change
            controller = (data_word_1 >> 24) & 0xFF
            value = (data_word_2 >> 24) & 0xFF
            return MIDIMessage(
                type='control_change',
                channel=channel,
                data={'controller': controller, 'value': value},
                timestamp=0.0
            )
        elif message_type == 0xC:  # Program Change
            program = (data_word_1 >> 24) & 0xFF
            return MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': program},
                timestamp=0.0
            )
        elif message_type == 0xE:  # Pitch Bend
            # MIDI 2.0 pitch bend is 32-bit
            pitch_value = data_word_1
            return MIDIMessage(
                type='pitch_bend',
                channel=channel,
                data={'value': pitch_value},
                timestamp=0.0
            )
        # Add more message types as needed
        
        return None

    def _convert_midi1_packet_to_message(self, packet) -> Optional[MIDIMessage]:
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
                timestamp=0.0
            )
        elif message_type == 0x9:  # Note On
            return MIDIMessage(
                type='note_on',
                channel=channel,
                data={'note': packet.data1, 'velocity': packet.data2},
                timestamp=0.0
            )
        elif message_type == 0xB:  # Control Change
            return MIDIMessage(
                type='control_change',
                channel=channel,
                data={'controller': packet.data1, 'value': packet.data2},
                timestamp=0.0
            )
        elif message_type == 0xC:  # Program Change
            return MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': packet.data1},
                timestamp=0.0
            )
        elif message_type == 0xE:  # Pitch Bend
            pitch_value = (packet.data2 << 7) | packet.data1
            return MIDIMessage(
                type='pitch_bend',
                channel=channel,
                data={'value': pitch_value},
                timestamp=0.0
            )
        
        return None

    def _convert_sysex_packet_to_message(self, packet) -> Optional[MIDIMessage]:
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
            timestamp=0.0
        )

    def _convert_utility_packet_to_message(self, packet) -> Optional[MIDIMessage]:
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
                timestamp=0.0
            )
        # Add other utility message types as needed
        
        return None

    def _parse_and_merge_tracks(self) -> List[MIDIMessage]:
        """Parse all tracks and merge into chronological order."""
        all_messages = []

        for track_index, track_data in enumerate(self.tracks):
            track_messages = self._parse_track(track_data, track_index)
            all_messages.extend(track_messages)

        # Sort by timestamp
        all_messages.sort(key=lambda msg: msg.timestamp)

        # Apply SMPTE offset if present
        if self.smpte_offset > 0:
            for msg in all_messages:
                msg.timestamp += self.smpte_offset

        return all_messages

    def _parse_track(self, track_data: bytes, track_index: int) -> List[MIDIMessage]:
        """Parse a single track into messages."""
        messages = []
        offset = 0
        ticks_accumulated = 0
        current_tempo = self.tempo
        running_status = 0

        while offset < len(track_data):
            # Read delta time
            delta_ticks, offset = self._read_variable_length(track_data, offset)
            ticks_accumulated += delta_ticks

            # Convert ticks to seconds
            time_seconds = self._ticks_to_seconds(ticks_accumulated, current_tempo)

            # Read event
            if offset >= len(track_data):
                break

            event_type = track_data[offset]
            offset += 1

            if event_type == MIDIStatus.META_EVENT:
                # Meta event
                if offset >= len(track_data):
                    break
                meta_type = track_data[offset]
                offset += 1
                length, offset = self._read_variable_length(track_data, offset)
                if offset + length > len(track_data):
                    break

                meta_data = list(track_data[offset:offset + length])
                offset += length

                message = self._parse_meta_event(meta_type, meta_data, time_seconds)
                if message:
                    messages.append(message)

                    # Update tempo if this was a tempo change
                    if meta_type == 0x51 and len(meta_data) == 3:
                        current_tempo = struct.unpack('>I', b'\x00' + bytes(meta_data))[0]

                # Meta events don't affect running status
                running_status = 0

            elif event_type == MIDIStatus.SYSTEM_EXCLUSIVE or event_type == MIDIStatus.END_OF_EXCLUSIVE:
                # System Exclusive
                length, offset = self._read_variable_length(track_data, offset)
                if offset + length > len(track_data):
                    break

                sysex_data = list(track_data[offset:offset + length])
                offset += length

                message = MIDIMessage(
                    type='sysex',
                    timestamp=time_seconds,
                    data={'raw_data': sysex_data}
                )
                messages.append(message)

                # System exclusive events don't affect running status
                running_status = 0

            else:
                # Channel message
                if event_type < 0x80:
                    # Running status - use previously stored status
                    if running_status == 0:
                        # No previous status, this is an error in the MIDI file
                        continue
                    # Don't advance offset since this was a data byte
                    offset -= 1
                else:
                    # New status byte - update running status
                    running_status = event_type

                message = self._parse_channel_event(running_status, track_data, offset, time_seconds)
                if message:
                    messages.append(message)
                    
                    # Update offset based on the message type to skip the data bytes
                    if running_status & 0xF0 in [0xC0, 0xD0]:  # 1 data byte messages
                        offset += 1
                    elif running_status & 0xF0 in [0x80, 0x90, 0xA0, 0xB0, 0xE0]:  # 2 data byte messages
                        offset += 2

        return messages

    def _parse_meta_event(self, meta_type: int, data: List[int], timestamp: float) -> Optional[MIDIMessage]:
        """Parse MIDI meta event."""
        if meta_type == 0x00 and len(data) == 2:  # Sequence Number
            seq_num = (data[0] << 8) | data[1]
            return MIDIMessage(
                type='sequence_number',
                timestamp=timestamp,
                data={'sequence_number': seq_num}
            )
        elif meta_type == 0x01:  # Text Event
            text = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='text',
                timestamp=timestamp,
                data={'text': text}
            )
        elif meta_type == 0x02:  # Copyright Notice
            copyright_text = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='copyright',
                timestamp=timestamp,
                data={'text': copyright_text}
            )
        elif meta_type == 0x03:  # Sequence/Track Name
            track_name = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='track_name',
                timestamp=timestamp,
                data={'name': track_name}
            )
        elif meta_type == 0x04:  # Instrument Name
            instrument_name = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='instrument_name',
                timestamp=timestamp,
                data={'name': instrument_name}
            )
        elif meta_type == 0x05:  # Lyric
            lyric_text = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='lyric',
                timestamp=timestamp,
                data={'text': lyric_text}
            )
        elif meta_type == 0x06:  # Marker
            marker_text = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='marker',
                timestamp=timestamp,
                data={'text': marker_text}
            )
        elif meta_type == 0x07:  # Cue Point
            cue_text = bytes(data).decode('utf-8', errors='ignore')
            return MIDIMessage(
                type='cue_point',
                timestamp=timestamp,
                data={'text': cue_text}
            )
        elif meta_type == 0x20 and len(data) == 1:  # MIDI Channel Prefix
            channel = data[0]
            return MIDIMessage(
                type='channel_prefix',
                timestamp=timestamp,
                data={'channel': channel}
            )
        elif meta_type == 0x2F:  # End of Track
            return MIDIMessage(
                type='end_of_track',
                timestamp=timestamp
            )
        elif meta_type == 0x51 and len(data) == 3:  # Set Tempo
            tempo_us = struct.unpack('>I', b'\x00' + bytes(data))[0]
            return MIDIMessage(
                type='tempo',
                timestamp=timestamp,
                data={'tempo_us_per_beat': tempo_us}
            )
        elif meta_type == 0x54 and len(data) == 5:  # SMPTE Offset
            hr, mn, se, fr, ff = data
            smpte_seconds = hr * 3600 + mn * 60 + se + (fr + ff/100.0) / 30.0
            self.smpte_offset = smpte_seconds
            return MIDIMessage(
                type='smpte_offset',
                timestamp=timestamp,
                data={'smpte_seconds': smpte_seconds}
            )
        elif meta_type == 0x58 and len(data) == 4:  # Time Signature
            numerator = data[0]
            denominator = 2 ** data[1]  # Denominator is stored as power of 2
            metronome_pulse = data[2]
            thirty_seconds_per_quarter = data[3]
            return MIDIMessage(
                type='time_signature',
                timestamp=timestamp,
                data={
                    'numerator': numerator,
                    'denominator': denominator,
                    'metronome_pulse': metronome_pulse,
                    'thirty_seconds_per_quarter': thirty_seconds_per_quarter
                }
            )
        elif meta_type == 0x59 and len(data) == 2:  # Key Signature
            # Key signature: -7 to +7 flats/sharps, 0=major/1=minor
            key = data[0] if data[0] < 128 else data[0] - 256  # Signed byte
            scale = data[1]  # 0=major, 1=minor
            return MIDIMessage(
                type='key_signature',
                timestamp=timestamp,
                data={
                    'key': key,
                    'scale': 'major' if scale == 0 else 'minor'
                }
            )
        elif meta_type == 0x7F:  # Sequencer Specific Meta Event
            return MIDIMessage(
                type='sequencer_specific',
                timestamp=timestamp,
                data={'raw_data': data}
            )

        # For any other meta events, return a generic meta message
        return MIDIMessage(
            type='meta',
            timestamp=timestamp,
            data={'meta_type': meta_type, 'data': data}
        )

    def _parse_channel_event(self, status: int, data: bytes, offset: int, timestamp: float) -> Optional[MIDIMessage]:
        """Parse MIDI channel event."""
        channel = status & 0x0F
        command = status & 0xF0

        message_data = {}

        if command == MIDIStatus.NOTE_OFF:
            if offset + 1 >= len(data):
                return None
            note = data[offset]
            velocity = data[offset + 1]
            message_data = {'note': note, 'velocity': velocity}
            message_type = 'note_off'

        elif command == MIDIStatus.NOTE_ON:
            if offset + 1 >= len(data):
                return None
            note = data[offset]
            velocity = data[offset + 1]
            message_data = {'note': note, 'velocity': velocity}
            message_type = 'note_on'

        elif command == MIDIStatus.POLY_PRESSURE:
            if offset + 1 >= len(data):
                return None
            note = data[offset]
            pressure = data[offset + 1]
            message_data = {'note': note, 'pressure': pressure}
            message_type = 'poly_pressure'

        elif command == MIDIStatus.CONTROL_CHANGE:
            if offset + 1 >= len(data):
                return None
            controller = data[offset]
            value = data[offset + 1]
            message_data = {'controller': controller, 'value': value}
            message_type = 'control_change'

        elif command == MIDIStatus.PROGRAM_CHANGE:
            program = data[offset]
            message_data = {'program': program}
            message_type = 'program_change'

        elif command == MIDIStatus.CHANNEL_PRESSURE:
            pressure = data[offset]
            message_data = {'pressure': pressure}
            message_type = 'channel_pressure'

        elif command == MIDIStatus.PITCH_BEND:
            if offset + 1 >= len(data):
                return None
            lsb = data[offset]
            msb = data[offset + 1]
            pitch_value = (msb << 7) | lsb
            message_data = {'value': pitch_value, 'lsb': lsb, 'msb': msb}
            message_type = 'pitch_bend'

        else:
            return None

        return MIDIMessage(
            type=message_type,
            channel=channel,
            timestamp=timestamp,
            data=message_data
        )

    def _read_variable_length(self, data: bytes, offset: int) -> Tuple[int, int]:
        """Read variable-length quantity from MIDI data."""
        value = 0
        # Limit to maximum 4 bytes to prevent infinite loops with malformed data
        max_bytes = 4
        bytes_read = 0
        
        while bytes_read < max_bytes:
            if offset >= len(data):
                break
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7F)
            bytes_read += 1
            if not (byte & 0x80):
                break
        
        # If we've read the maximum number of bytes and the last byte still has MSB set,
        # this is malformed data - return what we have
        if bytes_read == max_bytes and (byte & 0x80):
            # Log warning for malformed data but don't crash
            pass
            
        return value, offset

    def _ticks_to_seconds(self, ticks: int, tempo_us_per_beat: int) -> float:
        """Convert MIDI ticks to seconds."""
        if self.division & 0x8000:  # SMPTE format
            # SMPTE format: upper byte is negative frames per second, lower byte is ticks per frame
            # The upper byte is stored as a positive number representing negative FPS
            fps_negative = (self.division >> 8) & 0xFF
            if fps_negative == 0:
                # Invalid SMPTE format, default to 30 fps
                fps = 30.0
            else:
                # Convert to actual FPS (typically 24, 25, 29.97, 30)
                fps = float(fps_negative)
            
            ticks_per_frame = self.division & 0xFF
            if ticks_per_frame == 0:
                # Invalid ticks per frame, default to 4
                ticks_per_frame = 4
            
            return ticks / (fps * ticks_per_frame)
        else:  # PPQN format
            ppqn = self.division & 0x7FFF  # Mask out the sign bit if somehow set
            if ppqn <= 0:
                # Invalid PPQN, default to 480
                ppqn = 480
            return (ticks * tempo_us_per_beat) / (ppqn * 1000000.0)

    def get_file_info(self) -> dict:
        """Get information about the parsed file."""
        return {
            'filename': self.filename,
            'format': 'UMP' if self.is_ump_file else 'SMF',
            'midi_format': self.format,
            'tracks': len(self.tracks),
            'division': self.division,
            'tempo': self.tempo,
            'is_ump': self.is_ump_file,
            'time_base': self.time_base,
            'smpte_offset': self.smpte_offset
        }
