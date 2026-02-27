"""
Tests for vibexg.utils module

Tests MIDI conversion utilities.
"""
from __future__ import annotations

import pytest
from synth.midi import MIDIMessage
from vibexg.utils import midimessage_to_bytes, bytes_to_midimessage


class TestMIDIMessageToBytes:
    """Test midimessage_to_bytes function."""

    def test_note_on(self):
        """Test note on message conversion."""
        msg = MIDIMessage(
            type='note_on',
            channel=0,
            data={'note': 60, 'velocity': 80}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0x90, 60, 80])

    def test_note_off(self):
        """Test note off message conversion."""
        msg = MIDIMessage(
            type='note_off',
            channel=1,
            data={'note': 64, 'velocity': 64}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0x81, 64, 64])

    def test_control_change(self):
        """Test control change message conversion."""
        msg = MIDIMessage(
            type='control_change',
            channel=2,
            data={'controller': 74, 'value': 100}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xB2, 74, 100])

    def test_program_change(self):
        """Test program change message conversion."""
        msg = MIDIMessage(
            type='program_change',
            channel=3,
            data={'program': 25}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xC3, 25])

    def test_channel_pressure(self):
        """Test channel pressure message conversion."""
        msg = MIDIMessage(
            type='channel_pressure',
            channel=4,
            data={'pressure': 64}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xD4, 64])

    def test_pitch_bend_center(self):
        """Test pitch bend center position."""
        msg = MIDIMessage(
            type='pitch_bend',
            channel=0,
            data={'value': 8192}  # Center
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xE0, 0x00, 0x40])

    def test_pitch_bend_min(self):
        """Test pitch bend minimum value."""
        msg = MIDIMessage(
            type='pitch_bend',
            channel=0,
            data={'value': 0}  # Use 'value' in data dict
        )
        result = midimessage_to_bytes(msg)
        # Value 0 = LSB 0x00, MSB 0x00
        # Note: Implementation uses message.bend_value which reads from data['value']
        expected_msb = (0 >> 7) & 0x7F  # 0x00
        expected_lsb = 0 & 0x7F  # 0x00
        assert result == bytes([0xE0, expected_lsb, expected_msb])

    def test_pitch_bend_max(self):
        """Test pitch bend maximum value."""
        msg = MIDIMessage(
            type='pitch_bend',
            channel=0,
            data={'value': 16383}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xE0, 0x7F, 0x7F])

    def test_sysex(self):
        """Test system exclusive message conversion."""
        msg = MIDIMessage(
            type='sysex',
            data={'raw_data': [0x41, 0x10, 0x42]}
        )
        result = midimessage_to_bytes(msg)
        assert result == bytes([0xF0, 0x41, 0x10, 0x42, 0xF7])

    def test_none_channel(self):
        """Test message with None channel defaults to 0."""
        msg = MIDIMessage(
            type='note_on',
            channel=None,
            data={'note': 60, 'velocity': 80}
        )
        result = midimessage_to_bytes(msg)
        assert result[0] == 0x90  # Channel 0


class TestBytesToMIDIMessage:
    """Test bytes_to_midimessage function."""

    def test_note_on_bytes(self):
        """Test parsing note on bytes."""
        data = bytes([0x90, 60, 80])
        messages = bytes_to_midimessage(data)
        assert len(messages) > 0
        msg = messages[0]
        assert msg.type == 'note_on'
        assert msg.channel == 0
        assert msg.note == 60
        assert msg.velocity == 80

    def test_note_off_bytes(self):
        """Test parsing note off bytes."""
        data = bytes([0x80, 64, 64])
        messages = bytes_to_midimessage(data)
        assert len(messages) > 0
        msg = messages[0]
        assert msg.type == 'note_off'
        assert msg.channel == 0

    def test_control_change_bytes(self):
        """Test parsing control change bytes."""
        data = bytes([0xB0, 74, 100])
        messages = bytes_to_midimessage(data)
        assert len(messages) > 0
        msg = messages[0]
        assert msg.type == 'control_change'
        assert msg.controller == 74
        assert msg.value == 100

    def test_program_change_bytes(self):
        """Test parsing program change bytes."""
        data = bytes([0xC0, 25])
        messages = bytes_to_midimessage(data)
        assert len(messages) > 0
        msg = messages[0]
        assert msg.type == 'program_change'
        assert msg.program == 25

    def test_empty_bytes(self):
        """Test parsing empty bytes."""
        data = b''
        messages = bytes_to_midimessage(data)
        assert len(messages) == 0
