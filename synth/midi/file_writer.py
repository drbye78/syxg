"""
MIDI File Writer - Standard MIDI File Export

Provides SMF (Standard MIDI File) format 0 and 1 writing capabilities.
"""

from __future__ import annotations

import os
import struct
from typing import BinaryIO

from .message import MIDIMessage


class MIDIFileWriter:
    """
    Standard MIDI File writer.

    Supports Format 0 (single track) and Format 1 (multi-track) SMF files.

    Example:
        >>> from synth.midi import MIDIFileWriter, MIDIMessage
        >>> writer = MIDIFileWriter(format=1, division=960)
        >>> writer.add_track([
        ...     MIDIMessage(type='note_on', channel=0, data={'note': 60, 'velocity': 80}, timestamp=0.0),
        ...     MIDIMessage(type='note_off', channel=0, data={'note': 60, 'velocity': 64}, timestamp=0.5),
        ... ])
        >>> writer.save('output.mid')
    """

    def __init__(self, format: int = 1, division: int = 960):
        """
        Initialize MIDI file writer.

        Args:
            format: SMF format (0=single track, 1=multi-track)
            division: PPQ (pulses per quarter note), default 960
        """
        self.format = format
        self.division = division
        self.tracks: list[list[MIDIMessage]] = []
        self.tempo_us: int = 500000  # Default 120 BPM

    def add_track(self, messages: list[MIDIMessage]):
        """
        Add a track with messages.

        Args:
            messages: List of MIDIMessage objects with timestamps
        """
        self.tracks.append(messages)

    def set_tempo(self, tempo_us: int):
        """
        Set tempo in microseconds per quarter note.

        Args:
            tempo_us: Tempo in microseconds per quarter note
        """
        self.tempo_us = tempo_us

    def save(self, filename: str):
        """
        Save MIDI file.

        Args:
            filename: Output file path
        """
        # Ensure directory exists
        output_path = os.path.abspath(filename)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(filename, "wb") as f:
            self._write_header(f)
            for track in self.tracks:
                self._write_track(f, track)

    def _write_header(self, f: BinaryIO):
        """Write MThd header chunk."""
        f.write(b"MThd")
        f.write(struct.pack(">I", 6))  # Header length (always 6)
        f.write(struct.pack(">HHH", self.format, len(self.tracks), self.division))

    def _write_track(self, f: BinaryIO, messages: list[MIDIMessage]):
        """Write MTrk track chunk."""
        track_data = self._encode_track(messages)
        f.write(b"MTrk")
        f.write(struct.pack(">I", len(track_data)))
        f.write(track_data)

    def _encode_track(self, messages: list[MIDIMessage]) -> bytes:
        """Encode messages to track data."""
        result = bytearray()

        # Add tempo meta event if this is the first track
        if len(self.tracks) > 0 and self.tracks.index(messages) == 0:
            result.extend(self._write_tempo_meta_event())

        prev_time = 0.0
        running_status = 0

        for msg in messages:
            # Calculate delta time in ticks
            delta_seconds = msg.timestamp - prev_time
            prev_time = msg.timestamp

            # Convert seconds to ticks (using current tempo)
            ticks_per_second = self.division / (self.tempo_us / 1000000.0)
            delta_ticks = int(delta_seconds * ticks_per_second)

            # Write delta time as variable-length quantity
            result.extend(self._write_variable_length(delta_ticks))

            # Write message
            msg_bytes = self._message_to_bytes(msg, running_status)
            result.extend(msg_bytes)

            # Update running status
            if msg_bytes[0] & 0x80:
                running_status = msg_bytes[0]

        # Write end of track meta event
        result.extend([0x00, 0xFF, 0x2F, 0x00])

        return bytes(result)

    def _write_tempo_meta_event(self) -> bytes:
        """Write tempo meta event."""
        tempo_bytes = struct.pack(">I", self.tempo_us)[1:]  # 3 bytes
        return bytes([0x00, 0xFF, 0x51, 0x03]) + tempo_bytes

    def _write_variable_length(self, value: int) -> bytes:
        """Write variable-length quantity."""
        if value == 0:
            return bytes([0x00])

        result = []
        result.append(value & 0x7F)
        value >>= 7

        while value:
            result.append((value & 0x7F) | 0x80)
            value >>= 7

        return bytes(reversed(result))

    def _message_to_bytes(self, msg: MIDIMessage, running_status: int = 0) -> bytes:
        """Convert MIDIMessage to MIDI bytes."""
        result = bytearray()
        channel = msg.channel or 0

        if msg.type == "note_on":
            status = 0x90 | channel
            result.append(status)
            result.append(msg.note or 0)
            result.append(msg.velocity or 0)

        elif msg.type == "note_off":
            status = 0x80 | channel
            result.append(status)
            result.append(msg.note or 0)
            result.append(msg.velocity or 0)

        elif msg.type == "control_change":
            status = 0xB0 | channel
            result.append(status)
            result.append(msg.controller or 0)
            result.append(msg.value or 0)

        elif msg.type == "program_change":
            status = 0xC0 | channel
            result.append(status)
            result.append(msg.program or 0)

        elif msg.type == "channel_pressure":
            status = 0xD0 | channel
            result.append(status)
            result.append(msg.pressure or 0)

        elif msg.type == "poly_pressure":
            status = 0xA0 | channel
            result.append(status)
            result.append(msg.note or 0)
            result.append(msg.pressure or 0)

        elif msg.type == "pitch_bend":
            status = 0xE0 | channel
            result.append(status)
            value = msg.bend_value or 8192
            result.append(value & 0x7F)
            result.append((value >> 7) & 0x7F)

        elif msg.type == "sysex":
            result.append(0xF0)
            raw_data = msg.data.get("raw_data", [])
            for byte in raw_data:
                result.append(byte & 0x7F)
            result.append(0xF7)

        return bytes(result)
