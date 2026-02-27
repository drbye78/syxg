"""
MIDI File Handler - Standard MIDI File Import/Export

Provides comprehensive MIDI file handling capabilities including Standard MIDI Files (SMF)
format 0 and 1 support, with import/export functionality for the XG sequencer.
"""
from __future__ import annotations

import struct
from typing import Any, BinaryIO
import math


class MIDIFileHandler:
    """
    Standard MIDI File handler for import and export operations.

    Supports SMF format 0 (single track) and format 1 (multi-track) with comprehensive
    MIDI event handling for professional sequencing workflows.
    """

    # MIDI file format constants
    SMF_FORMAT_0 = 0  # Single track
    SMF_FORMAT_1 = 1  # Multi-track
    SMF_FORMAT_2 = 2  # Multi-song (rarely used)

    # MIDI status bytes
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0
    SYSTEM_EXCLUSIVE = 0xF0
    MIDI_TIME_CODE = 0xF1
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

    # Meta event types
    META_SEQUENCE_NUMBER = 0x00
    META_TEXT = 0x01
    META_COPYRIGHT = 0x02
    META_TRACK_NAME = 0x03
    META_INSTRUMENT_NAME = 0x04
    META_LYRIC = 0x05
    META_MARKER = 0x06
    META_CUE_POINT = 0x07
    META_CHANNEL_PREFIX = 0x20
    META_END_OF_TRACK = 0x2F
    META_SET_TEMPO = 0x51
    META_SMPTE_OFFSET = 0x54
    META_TIME_SIGNATURE = 0x58
    META_KEY_SIGNATURE = 0x59
    META_SEQUENCER_SPECIFIC = 0x7F

    def __init__(self):
        """Initialize MIDI file handler."""
        self.format = 1
        self.num_tracks = 0
        self.division = 960  # PPQ (pulses per quarter note)
        self.tracks = []
        self.tempo_events = []
        self.time_sig_events = []

    def load_midi_file(self, filename: str) -> dict[str, Any] | None:
        """
        Load a Standard MIDI File.

        Args:
            filename: Path to MIDI file

        Returns:
            MIDI file data dictionary or None if error
        """
        try:
            with open(filename, 'rb') as f:
                return self._parse_midi_file(f)
        except Exception as e:
            print(f"Error loading MIDI file {filename}: {e}")
            return None

    def _parse_midi_file(self, file: BinaryIO) -> dict[str, Any] | None:
        """Parse MIDI file from binary stream."""
        # Read header chunk
        header = self._read_chunk(file)
        if header['type'] != b'MThd':
            raise ValueError("Not a valid MIDI file")

        # Parse header data
        header_data = struct.unpack('>HHH', header['data'])
        format_type = header_data[0]
        num_tracks = header_data[1]
        division = header_data[2]

        # Parse division (PPQ or SMPTE)
        if division & 0x8000:
            # SMPTE time code
            smpte_format = (division >> 8) & 0x7F
            ticks_per_frame = division & 0xFF
            ppq = None
        else:
            # PPQ
            ppq = division & 0x7FFF
            smpte_format = None
            ticks_per_frame = None

        # Read tracks
        tracks = []
        for i in range(num_tracks):
            track_chunk = self._read_chunk(file)
            if track_chunk['type'] != b'MTrk':
                continue

            track_events = self._parse_track(track_chunk['data'])
            tracks.append(track_events)

        return {
            'format': format_type,
            'num_tracks': num_tracks,
            'ppq': ppq,
            'smpte_format': smpte_format,
            'ticks_per_frame': ticks_per_frame,
            'tracks': tracks
        }

    def _read_chunk(self, file: BinaryIO) -> dict[str, Any]:
        """Read a MIDI file chunk."""
        chunk_type = file.read(4)
        if len(chunk_type) != 4:
            raise ValueError("Unexpected end of file")

        chunk_length = struct.unpack('>I', file.read(4))[0]
        chunk_data = file.read(chunk_length)

        return {
            'type': chunk_type,
            'length': chunk_length,
            'data': chunk_data
        }

    def _parse_track(self, track_data: bytes) -> list[dict[str, Any]]:
        """Parse a track's event data."""
        events = []
        pos = 0
        running_status = 0
        ticks = 0

        while pos < len(track_data):
            # Read delta time
            delta_time, pos = self._read_variable_length(track_data, pos)
            ticks += delta_time

            # Read event
            if pos >= len(track_data):
                break

            status = track_data[pos]
            pos += 1

            # Handle running status
            if status < 0x80:
                # Running status - reuse previous status
                status = running_status
                pos -= 1  # Put back the data byte

            running_status = status

            # Parse event based on status
            event = self._parse_event(track_data, pos, status, ticks)
            if event:
                events.append(event)
                pos = event.get('next_pos', pos + event.get('data_length', 0))

        return events

    def _parse_event(self, data: bytes, pos: int, status: int, ticks: int) -> dict[str, Any] | None:
        """Parse a MIDI event."""
        event_type = status & 0xF0
        channel = status & 0x0F

        if event_type == self.NOTE_OFF:
            note = data[pos]
            velocity = data[pos + 1]
            return {
                'ticks': ticks,
                'type': 'note_off',
                'channel': channel,
                'note': note,
                'velocity': velocity,
                'data_length': 2
            }

        elif event_type == self.NOTE_ON:
            note = data[pos]
            velocity = data[pos + 1]
            event_type_str = 'note_off' if velocity == 0 else 'note_on'
            return {
                'ticks': ticks,
                'type': event_type_str,
                'channel': channel,
                'note': note,
                'velocity': velocity,
                'data_length': 2
            }

        elif event_type == self.CONTROL_CHANGE:
            controller = data[pos]
            value = data[pos + 1]
            return {
                'ticks': ticks,
                'type': 'control_change',
                'channel': channel,
                'controller': controller,
                'value': value,
                'data_length': 2
            }

        elif event_type == self.PROGRAM_CHANGE:
            program = data[pos]
            return {
                'ticks': ticks,
                'type': 'program_change',
                'channel': channel,
                'program': program,
                'data_length': 1
            }

        elif event_type == self.PITCH_BEND:
            lsb = data[pos]
            msb = data[pos + 1]
            value = (msb << 7) | lsb
            return {
                'ticks': ticks,
                'type': 'pitch_bend',
                'channel': channel,
                'value': value,
                'data_length': 2
            }

        elif status == self.SYSTEM_EXCLUSIVE or status == self.END_OF_EXCLUSIVE:
            # System exclusive - variable length
            length, new_pos = self._read_variable_length(data, pos)
            sysex_data = data[new_pos:new_pos + length]
            return {
                'ticks': ticks,
                'type': 'system_exclusive',
                'data': sysex_data,
                'next_pos': new_pos + length
            }

        elif status == 0xFF:
            # Meta event
            meta_type = data[pos]
            pos += 1
            length, pos = self._read_variable_length(data, pos)
            meta_data = data[pos:pos + length]

            return self._parse_meta_event(meta_type, meta_data, ticks, pos + length)

        return None

    def _parse_meta_event(self, meta_type: int, data: bytes, ticks: int, next_pos: int) -> dict[str, Any]:
        """Parse a meta event."""
        if meta_type == self.META_SET_TEMPO:
            # Tempo: 3 bytes microseconds per quarter note
            if len(data) >= 3:
                microseconds = (data[0] << 16) | (data[1] << 8) | data[2]
                tempo = 60000000 / microseconds  # BPM
                return {
                    'ticks': ticks,
                    'type': 'tempo_change',
                    'tempo': tempo,
                    'next_pos': next_pos
                }

        elif meta_type == self.META_TIME_SIGNATURE:
            # Time signature: numerator, denominator, etc.
            if len(data) >= 4:
                numerator = data[0]
                denominator = 2 ** data[1]  # Denominator is 2^data[1]
                return {
                    'ticks': ticks,
                    'type': 'time_signature',
                    'numerator': numerator,
                    'denominator': denominator,
                    'next_pos': next_pos
                }

        elif meta_type == self.META_TRACK_NAME:
            # Track name
            name = data.decode('utf-8', errors='ignore')
            return {
                'ticks': ticks,
                'type': 'track_name',
                'name': name,
                'next_pos': next_pos
            }

        elif meta_type == self.META_END_OF_TRACK:
            return {
                'ticks': ticks,
                'type': 'end_of_track',
                'next_pos': next_pos
            }

        # Generic meta event
        return {
            'ticks': ticks,
            'type': 'meta_event',
            'meta_type': meta_type,
            'data': data,
            'next_pos': next_pos
        }

    def _read_variable_length(self, data: bytes, pos: int) -> tuple[int, int]:
        """Read a variable-length quantity from MIDI data."""
        value = 0
        i = 0
        
        # Limit to maximum 4 bytes to prevent infinite loops with malformed data
        max_bytes = 4

        while i < max_bytes:
            if pos + i >= len(data):
                break

            byte = data[pos + i]
            value = (value << 7) | (byte & 0x7F)
            i += 1

            if byte & 0x80 == 0:
                break

        return value, pos + i

    def save_midi_file(self, midi_data: dict[str, Any], filename: str) -> bool:
        """
        Save MIDI data to a Standard MIDI File.

        Args:
            midi_data: MIDI data dictionary
            filename: Output filename

        Returns:
            Success status
        """
        try:
            with open(filename, 'wb') as f:
                self._write_midi_file(midi_data, f)
            return True
        except Exception as e:
            print(f"Error saving MIDI file {filename}: {e}")
            return False

    def _write_midi_file(self, midi_data: dict[str, Any], file: BinaryIO):
        """Write MIDI file to binary stream."""
        format_type = midi_data.get('format', 1)
        tracks = midi_data.get('tracks', [])
        ppq = midi_data.get('ppq', 960)

        # Write header chunk
        self._write_chunk(file, b'MThd', struct.pack('>HHH', format_type, len(tracks), ppq))

        # Write track chunks
        for track_events in tracks:
            track_data = self._encode_track(track_events)
            self._write_chunk(file, b'MTrk', track_data)

    def _write_chunk(self, file: BinaryIO, chunk_type: bytes, data: bytes):
        """Write a MIDI file chunk."""
        file.write(chunk_type)
        file.write(struct.pack('>I', len(data)))
        file.write(data)

    def _encode_track(self, events: list[dict[str, Any]]) -> bytes:
        """Encode track events to MIDI data."""
        data = bytearray()
        last_ticks = 0

        for event in events:
            ticks = event.get('ticks', 0)
            delta_time = ticks - last_ticks
            last_ticks = ticks

            # Write delta time
            data.extend(self._write_variable_length(delta_time))

            # Encode event
            event_data = self._encode_event(event)
            data.extend(event_data)

        # Add end of track meta event
        data.extend(self._write_variable_length(0))  # Delta time
        data.extend([0xFF, 0x2F, 0x00])  # End of track

        return bytes(data)

    def _encode_event(self, event: dict[str, Any]) -> bytes:
        """Encode a MIDI event to bytes."""
        event_type = event.get('type')

        if event_type in ['note_on', 'note_off']:
            status = (self.NOTE_ON if event_type == 'note_on' else self.NOTE_OFF) | event.get('channel', 0)
            return bytes([status, event.get('note', 60), event.get('velocity', 64)])

        elif event_type == 'control_change':
            status = self.CONTROL_CHANGE | event.get('channel', 0)
            return bytes([status, event.get('controller', 0), event.get('value', 0)])

        elif event_type == 'program_change':
            status = self.PROGRAM_CHANGE | event.get('channel', 0)
            return bytes([status, event.get('program', 0)])

        elif event_type == 'pitch_bend':
            status = self.PITCH_BEND | event.get('channel', 0)
            value = event.get('value', 8192)
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            return bytes([status, lsb, msb])

        elif event_type == 'tempo_change':
            tempo = event.get('tempo', 120.0)
            microseconds = int(60000000 / tempo)
            data = bytes([(microseconds >> 16) & 0xFF, (microseconds >> 8) & 0xFF, microseconds & 0xFF])
            return b'\xFF\x51\x03' + data

        elif event_type == 'time_signature':
            numerator = event.get('numerator', 4)
            denominator = event.get('denominator', 4)
            denominator_exp = int(math.log2(denominator))
            return bytes([0xFF, 0x58, 0x04, numerator, denominator_exp, 24, 8])

        # Default: empty event
        return b''

    def _write_variable_length(self, value: int) -> bytes:
        """Write a variable-length quantity."""
        if value == 0:
            return b'\x00'

        data = bytearray()
        while value > 0:
            byte = value & 0x7F
            value >>= 7
            if value > 0:
                byte |= 0x80
            data.insert(0, byte)

        return bytes(data)

    def convert_to_sequencer_format(self, midi_data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert MIDI file data to internal sequencer format.

        Args:
            midi_data: MIDI file data

        Returns:
            Sequencer-compatible format
        """
        tracks = midi_data.get('tracks', [])
        ppq = midi_data.get('ppq', 960)

        sequencer_tracks = {}

        for track_idx, track_events in enumerate(tracks):
            track_name = f"Track {track_idx + 1}"
            midi_events = []
            tempo_events = []
            time_sig_events = []

            for event in track_events:
                event_type = event.get('type')

                if event_type in ['note_on', 'note_off', 'control_change', 'program_change', 'pitch_bend']:
                    midi_events.append(event)
                elif event_type == 'track_name':
                    track_name = event.get('name', track_name)
                elif event_type == 'tempo_change':
                    tempo_events.append(event)
                elif event_type == 'time_signature':
                    time_sig_events.append(event)

            sequencer_tracks[track_idx] = {
                'name': track_name,
                'events': midi_events,
                'tempo_events': tempo_events,
                'time_signature_events': time_sig_events
            }

        return {
            'format': 'sequencer',
            'ppq': ppq,
            'tracks': sequencer_tracks,
            'tempo_events': tempo_events,
            'time_signature_events': time_sig_events
        }

    def get_midi_file_info(self, midi_data: dict[str, Any]) -> dict[str, Any]:
        """
        Get information about a MIDI file.

        Args:
            midi_data: MIDI file data

        Returns:
            File information
        """
        tracks = midi_data.get('tracks', [])
        total_events = sum(len(track) for track in tracks)

        # Calculate duration (simplified)
        max_ticks = 0
        for track in tracks:
            for event in track:
                max_ticks = max(max_ticks, event.get('ticks', 0))

        # Assume 120 BPM for duration calculation
        ppq = midi_data.get('ppq', 960)
        tempo = 120.0  # BPM
        duration_seconds = (max_ticks / ppq) * (60.0 / tempo)

        return {
            'format': midi_data.get('format', 1),
            'num_tracks': len(tracks),
            'total_events': total_events,
            'ppq': ppq,
            'duration_seconds': duration_seconds,
            'duration_minutes': duration_seconds / 60.0
        }
