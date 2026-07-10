"""
Tests for MIDI 2.0 UMP packet round-trip and Per-Note Controller support.
"""

from __future__ import annotations

import pytest
from synth.io.midi.ump_packets import (
    UMPGroup,
    UMPMessageType,
    UMPParser,
    PER_NOTE_CONTROLLER,
    PerNoteControllerUMP,
)


class TestPerNoteControllerUMP:
    """Tests for PerNoteControllerUMP packet class."""

    def test_create_and_serialize(self):
        """Create a PerNoteControllerUMP and serialize to words."""
        pnc = PerNoteControllerUMP(
            group=UMPGroup(0),
            channel=5,
            note=60,
            controller_index=74,  # Timbre
            value=8388608,  # 24-bit value, midpoint (0x800000)
        )
        words = pnc.to_words()
        assert len(words) == 2

        # Check header word
        header = words[0]
        assert (header >> 28) & 0xF == 0xF  # UMP type
        assert (header >> 24) & 0xF == 0  # Group
        assert (header >> 20) & 0xF == 0x0  # Status = Per-Note Controller
        assert (header >> 16) & 0xF == 5  # Channel
        assert header & 0xFFFF == 60  # Note

        # Check data word
        word1 = words[1]
        assert (word1 >> 24) & 0xFF == 74  # Controller index
        assert word1 & 0xFFFFFF == 8388608  # Value

    def test_bytes_round_trip(self):
        """Serialize to bytes and parse back."""
        pnc = PerNoteControllerUMP(
            group=UMPGroup(3),
            channel=7,
            note=72,
            controller_index=75,  # Slide
            value=1234567,
        )
        packet_bytes = pnc.to_bytes()
        assert len(packet_bytes) == 8

        parsed = UMPParser.parse_packet(packet_bytes)
        assert parsed is not None
        assert isinstance(parsed, PerNoteControllerUMP)
        assert parsed.group == 3
        assert parsed.channel == 7
        assert parsed.note == 72
        assert parsed.controller_index == 75
        assert parsed.value == 1234567

    def test_words_round_trip(self):
        """Convert to words and back via from_words."""
        pnc = PerNoteControllerUMP(
            group=UMPGroup(1),
            channel=0,
            note=127,
            controller_index=76,  # Lift
            value=16777215,  # Max 24-bit value
        )
        words = pnc.to_words()
        parsed = PerNoteControllerUMP.from_words(words)
        assert parsed is not None
        assert parsed.group == 1
        assert parsed.channel == 0
        assert parsed.note == 127
        assert parsed.controller_index == 76
        assert parsed.value == 16777215

    def test_min_max_values(self):
        """Test edge cases for 24-bit value range."""
        # Minimum value
        pnc = PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 0)
        assert pnc.to_words()[1] & 0xFFFFFF == 0

        # Maximum value
        pnc = PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 0xFFFFFF)
        assert pnc.to_words()[1] & 0xFFFFFF == 0xFFFFFF

        # Maximum controller index
        pnc = PerNoteControllerUMP(UMPGroup(0), 0, 60, 0xFF, 100)
        assert (pnc.to_words()[1] >> 24) & 0xFF == 0xFF

    def test_invalid_channel_raises(self):
        """Invalid channel should raise ValueError."""
        with pytest.raises(ValueError, match="Channel"):
            PerNoteControllerUMP(UMPGroup(0), 16, 60, 74, 100)

    def test_invalid_note_raises(self):
        """Note > 16-bit should raise ValueError."""
        with pytest.raises(ValueError, match="Note"):
            PerNoteControllerUMP(UMPGroup(0), 0, 0x10000, 74, 100)

    def test_invalid_controller_index_raises(self):
        """Controller index > 8-bit should raise ValueError."""
        with pytest.raises(ValueError, match="Controller"):
            PerNoteControllerUMP(UMPGroup(0), 0, 60, 0x100, 100)

    def test_invalid_value_raises(self):
        """Value > 24-bit should raise ValueError."""
        with pytest.raises(ValueError, match="Value"):
            PerNoteControllerUMP(UMPGroup(0), 0, 60, 74, 0x1000000)

    def test_parser_rejects_wrong_type(self):
        """Parser should reject non-0xF packets."""
        words = [0x20000000, 0]  # Header: MIDI 2.0 Channel Voice (type 0x2)
        result = PerNoteControllerUMP.from_words(words)
        assert result is None

    def test_parser_stream(self):
        """Parse PerNoteControllerUMP from a stream with mixed packets."""
        # Create a PerNoteControllerUMP
        pnc = PerNoteControllerUMP(UMPGroup(0), 1, 64, 74, 5000)
        data = pnc.to_bytes()

        # Parse stream
        packets = UMPParser.parse_packet_stream(data)
        assert len(packets) == 1
        assert isinstance(packets[0], PerNoteControllerUMP)
        assert packets[0].note == 64
        assert packets[0].controller_index == 74
        assert packets[0].value == 5000

    def test_per_note_controller_constant(self):
        """PER_NOTE_CONTROLLER constant should be 0x0."""
        assert PER_NOTE_CONTROLLER == 0x0

    def test_ump_type_constant(self):
        """UMPMessageType.STREAM should be 0xF."""
        assert UMPMessageType.STREAM == 0xF

    def test_all_controllers_round_trip(self):
        """Test all three MPE per-note controllers round-trip."""
        for controller in [74, 75, 76]:
            pnc = PerNoteControllerUMP(
                UMPGroup(0), 0, 60, controller, 8388608
            )
            data = pnc.to_bytes()
            parsed = UMPParser.parse_packet(data)
            assert parsed is not None
            assert isinstance(parsed, PerNoteControllerUMP)
            assert parsed.controller_index == controller


class TestPerNoteControllerViaRealtime:
    """Tests for PerNoteControllerUMP → MIDIMessage via RealtimeParser."""

    def test_conversion_to_midimessage(self):
        """PerNoteControllerUMP should convert to MIDIMessage through RealtimeParser."""
        from synth.io.midi.realtime import RealtimeParser

        pnc = PerNoteControllerUMP(
            group=UMPGroup(0),
            channel=3,
            note=60,
            controller_index=74,
            value=8388608,
        )
        data = pnc.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        # Should produce exactly one MIDI message
        assert len(messages) == 1
        msg = messages[0]

        assert msg.type == "midi2_per_note_controller"
        assert msg.channel == 3
        assert msg.data["note"] == 60
        assert msg.data["controller"] == 74
        assert msg.data["value_24bit"] == 8388608
        assert msg.data["is_midi2"] is True

    def test_mixed_midi1_and_per_note_controller(self):
        """Parse a mixed stream of MIDI 1.0 and Per-Note Controller messages."""
        from synth.io.midi.realtime import RealtimeParser

        # Create a MIDI 1.0 Note On packet
        from synth.io.midi.ump_packets import MIDI1ChannelVoicePacket

        note_on = MIDI1ChannelVoicePacket(
            UMPGroup(0), 0x90, 60, 100
        )
        pnc = PerNoteControllerUMP(
            UMPGroup(0), 3, 64, 75, 5000
        )

        combined = note_on.to_bytes() + pnc.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(combined)

        assert len(messages) == 2
        assert messages[0].type == "note_on"
        assert messages[1].type == "midi2_per_note_controller"
        assert messages[1].data["controller"] == 75
        assert messages[1].data["value_24bit"] == 5000
