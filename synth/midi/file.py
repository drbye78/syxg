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
        # Read MThd header
        header = file_handle.read(14)
        if len(header) < 14 or header[:4] != b'MThd':
            raise ValueError("Invalid MIDI file header")

        header_length = struct.unpack('>I', header[4:8])[0]
        self.format = struct.unpack('>H', header[8:10])[0]
        num_tracks = struct.unpack('>H', header[10:12])[0]
        self.division = struct.unpack('>H', header[12:14])[0]

        # Skip extended header if present
        if header_length > 6:
            file_handle.read(header_length - 6)

        # Read tracks
        for _ in range(num_tracks):
            track_header = file_handle.read(8)
            if len(track_header) < 8 or track_header[:4] != b'MTrk':
                raise ValueError("Invalid track header")

            track_length = struct.unpack('>I', track_header[4:8])[0]
            track_data = file_handle.read(track_length)
            self.tracks.append(track_data)

        # Parse all tracks and merge
        return self._parse_and_merge_tracks()

    def _parse_ump_file(self, file_handle) -> List[MIDIMessage]:
        """
        Parse Universal MIDI Packet file format.

        Args:
            file_handle: Open file handle positioned after UMPP signature

        Returns:
            List of MIDIMessage objects
        """
        # Read UMP header
        header_data = file_handle.read(28)
        if len(header_data) < 28:
            raise ValueError("Invalid UMP file header")

        self.time_base = struct.unpack('>I', header_data[0:4])[0]
        self.format = struct.unpack('>H', header_data[4:6])[0]
        num_chunks = struct.unpack('>H', header_data[6:8])[0]

        # Read chunks
        for _ in range(num_chunks):
            chunk_header = file_handle.read(8)
            if len(chunk_header) < 8:
                break

            chunk_type = chunk_header[:4]
            chunk_length = struct.unpack('>I', chunk_header[4:8])[0]

            if chunk_type in (b'MChk', b'SChk'):  # MIDI or Stream chunk
                chunk_data = file_handle.read(chunk_length)
                self.tracks.append(chunk_data)
            else:
                # Skip unknown chunks
                file_handle.seek(chunk_length, 1)

        # Parse UMP tracks
        return self._parse_and_merge_tracks()

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

            else:
                # Channel message
                if event_type < 0x80:
                    # Running status
                    if running_status == 0:
                        continue
                    data_byte = event_type
                    event_type = running_status
                    offset -= 1  # Re-read as data
                else:
                    running_status = event_type

                message = self._parse_channel_event(event_type, track_data, offset, time_seconds)
                if message:
                    messages.append(message)

        return messages

    def _parse_meta_event(self, meta_type: int, data: List[int], timestamp: float) -> Optional[MIDIMessage]:
        """Parse MIDI meta event."""
        if meta_type == 0x51 and len(data) == 3:  # Tempo change
            tempo_us = struct.unpack('>I', b'\x00' + bytes(data))[0]
            return MIDIMessage(
                type='tempo',
                timestamp=timestamp,
                data={'tempo_us_per_beat': tempo_us}
            )
        elif meta_type == 0x54 and len(data) == 5:  # SMPTE offset
            hr, mn, se, fr, ff = data
            smpte_seconds = hr * 3600 + mn * 60 + se + (fr + ff/100.0) / 30.0
            self.smpte_offset = smpte_seconds
            return MIDIMessage(
                type='smpte_offset',
                timestamp=timestamp,
                data={'smpte_seconds': smpte_seconds}
            )
        elif meta_type == 0x2F:  # End of track
            return MIDIMessage(
                type='end_of_track',
                timestamp=timestamp
            )

        # Other meta events could be added here
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
            if offset >= len(data):
                return None
            lsb = data[offset]
            msb = data[offset] if offset + 1 < len(data) else 0
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
        while True:
            if offset >= len(data):
                break
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7F)
            if not (byte & 0x80):
                break
        return value, offset

    def _ticks_to_seconds(self, ticks: int, tempo_us_per_beat: int) -> float:
        """Convert MIDI ticks to seconds."""
        if self.division & 0x8000:  # SMPTE format
            fps = 256 - ((self.division >> 8) & 0xFF)
            ticks_per_frame = self.division & 0xFF
            return ticks / (fps * ticks_per_frame)
        else:  # PPQN format
            ppqn = self.division
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
