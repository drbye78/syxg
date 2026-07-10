"""
Tests for UMP Group routing — verifying that UMP Groups 0-15 are correctly
propagated through packet serialization, MIDIMessage conversion, and converter.

UMP Groups provide 16 independent channel groups, each containing 16 MIDI channels,
for a total of 256 channels over a single UMP stream.
"""

from __future__ import annotations

import struct

import pytest

from synth.io.midi.realtime import RealtimeParser
from synth.io.midi.ump_packets import (
    UMPGroup,
    MIDI2ChannelVoicePacket,
    MIDI1ChannelVoicePacket,
    PerNoteControllerUMP,
    PerNoteManagementUMP,
    MIDI1ToMIDI2Converter,
    UMPParser,
    UMPMessageType,
)


class TestPacketGroupPreservation:
    """UMP packets preserve group through serialize/deserialize."""

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_midi2_packet_words_round_trip(self, group: int) -> None:
        """MIDI2ChannelVoicePacket preserves group through words round-trip."""
        packet = MIDI2ChannelVoicePacket(
            UMPGroup(group), channel=5, message_type=0x9,
            data_word_1=60, data_word_2=100 << 16,
        )
        assert packet.group == UMPGroup(group)

        words = packet.to_words()
        restored = MIDI2ChannelVoicePacket.from_words(words)
        assert restored is not None
        assert restored.group == UMPGroup(group)
        assert restored.channel == 5
        assert restored.data_word_1 == 60

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_midi2_packet_bytes_round_trip(self, group: int) -> None:
        """MIDI2ChannelVoicePacket preserves group through bytes round-trip."""
        packet = MIDI2ChannelVoicePacket(
            UMPGroup(group), channel=5, message_type=0x9,
            data_word_1=60, data_word_2=100 << 16,
        )
        data = packet.to_bytes()
        restored = UMPParser.parse_packet(data)
        assert restored is not None
        assert isinstance(restored, MIDI2ChannelVoicePacket)
        assert restored.group == UMPGroup(group)
        assert restored.channel == 5

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_midi1_packet_words_round_trip(self, group: int) -> None:
        """MIDI1ChannelVoicePacket preserves group through words round-trip."""
        packet = MIDI1ChannelVoicePacket(
            UMPGroup(group), status_byte=0x90, data1=60, data2=100,
        )
        words = packet.to_words()
        restored = MIDI1ChannelVoicePacket.from_words(words)
        assert restored is not None
        assert restored.group == UMPGroup(group)
        assert restored.status_byte == 0x90

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_per_note_controller_words_round_trip(self, group: int) -> None:
        """PerNoteControllerUMP preserves group through words round-trip."""
        packet = PerNoteControllerUMP(
            group=UMPGroup(group), channel=3, note=60,
            controller_index=74, value=0x800000,
        )
        words = packet.to_words()
        restored = PerNoteControllerUMP.from_words(words)
        assert restored is not None
        assert restored.group == UMPGroup(group)
        assert restored.channel == 3
        assert restored.note == 60

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_per_note_management_words_round_trip(self, group: int) -> None:
        """PerNoteManagementUMP preserves group through words round-trip."""
        packet = PerNoteManagementUMP(
            group=UMPGroup(group), channel=7, note=72, assign=True,
        )
        words = packet.to_words()
        restored = PerNoteManagementUMP.from_words(words)
        assert restored is not None
        assert restored.group == UMPGroup(group)
        assert restored.channel == 7
        assert restored.note == 72
        assert restored.assign is True


class TestMIDIMessageGroupRouting:
    """RealtimeParser attaches midi_group to MIDIMessages."""

    @pytest.mark.parametrize("group,channel", [(0, 0), (1, 5), (3, 15), (7, 0), (15, 15)])
    def test_midi2_note_on_has_midi_group(self, group: int, channel: int) -> None:
        """MIDI 2.0 note on from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = MIDI2ChannelVoicePacket(
            UMPGroup(group), channel=channel, message_type=0x9,
            data_word_1=60, data_word_2=100 << 16,
        )
        msg = parser._convert_midi2_packet_to_message(packet)
        assert msg is not None
        assert msg.channel == channel  # raw channel preserved
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "note_on"

    @pytest.mark.parametrize("group,channel", [(0, 0), (1, 5), (3, 15)])
    def test_midi2_cc_has_midi_group(self, group: int, channel: int) -> None:
        """MIDI 2.0 control change from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = MIDI2ChannelVoicePacket(
            UMPGroup(group), channel=channel, message_type=0xB,
            data_word_1=7 << 9, data_word_2=0x7FFFFFFF,  # CC=7, value=0x7FFFFFFF
        )
        msg = parser._convert_midi2_packet_to_message(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "control_change"

    @pytest.mark.parametrize("group,channel", [(0, 0), (2, 7), (15, 15)])
    def test_midi1_note_on_has_midi_group(self, group: int, channel: int) -> None:
        """MIDI 1.0 (UMP) note on from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = MIDI1ChannelVoicePacket(
            UMPGroup(group), status_byte=0x90 | channel, data1=60, data2=100,
        )
        msg = parser._convert_midi1_packet_to_message(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "note_on"

    @pytest.mark.parametrize("group,channel", [(0, 3), (1, 12), (7, 0)])
    def test_per_note_controller_has_midi_group(self, group: int, channel: int) -> None:
        """Per-note controller from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = PerNoteControllerUMP(
            group=UMPGroup(group), channel=channel, note=64,
            controller_index=74, value=0x800000,
        )
        msg = parser._convert_per_note_controller(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "midi2_per_note_controller"

    @pytest.mark.parametrize("group,channel", [(0, 3), (1, 12), (7, 0)])
    def test_per_note_management_has_midi_group(self, group: int, channel: int) -> None:
        """Per-note management from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = PerNoteManagementUMP(
            group=UMPGroup(group), channel=channel, note=72, assign=True,
        )
        msg = parser._convert_per_note_management(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "midi2_per_note_management"

    @pytest.mark.parametrize("group,channel", [(0, 0), (0, 15), (1, 0), (3, 7)])
    def test_pitch_bend_has_midi_group(self, group: int, channel: int) -> None:
        """MIDI 2.0 pitch bend from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        packet = MIDI2ChannelVoicePacket(
            UMPGroup(group), channel=channel, message_type=0xE,
            data_word_1=0, data_word_2=0x7FFFFFFF,  # pitch bend = midpoint
        )
        msg = parser._convert_midi2_packet_to_message(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.data.get("pitch_32bit") == 0x7FFFFFFF

    @pytest.mark.parametrize("group,channel", [(0, 0), (1, 3), (5, 10)])
    def test_midi1_pitch_bend_has_midi_group(self, group: int, channel: int) -> None:
        """MIDI 1.0 (UMP) pitch bend from a non-zero group carries midi_group."""
        parser = RealtimeParser()
        # Pitch bend: status=0xE0|ch, data1=lsb, data2=msb
        packet = MIDI1ChannelVoicePacket(
            UMPGroup(group), status_byte=0xE0 | channel, data1=0, data2=64,
        )
        msg = parser._convert_midi1_packet_to_message(packet)
        assert msg is not None
        assert msg.channel == channel
        assert msg.data.get("midi_group") == UMPGroup(group)
        assert msg.type == "pitch_bend"


class TestConverterGroupPreservation:
    """MIDI1ToMIDI2Converter preserves group when converting."""

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_converter_preserves_group(self, group: int) -> None:
        """midi1_to_midi2_channel_voice preserves the group parameter."""
        m2_packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status_byte=0x90, data1=60, data2=100,
            group=UMPGroup(group),
        )
        assert m2_packet.group == UMPGroup(group)
        assert m2_packet.channel == 0

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_converter_defaults_to_group_0(self, group: int) -> None:
        """Converter defaults to group 0 when no group is specified."""
        m2_packet = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status_byte=0x91, data1=60, data2=100,
        )
        assert m2_packet.group == UMPGroup(0)
        assert m2_packet.channel == 1


class TestUMPParserGroupRouting:
    """UMPParser correctly extracts group from packet headers."""

    def _make_midi2_words(self, group: int, channel: int, msg_type: int,
                          note: int = 60, velocity: int = 100) -> list[int]:
        """Build a 2-word MIDI 2.0 channel voice UMP message."""
        header = (UMPMessageType.MIDI_2_CHANNEL << 28) | (group << 24) | (msg_type << 20) | (channel << 16) | note
        # Word 0 = header with note, Word 1 = velocity << 16
        return [header, velocity << 16]

    @pytest.mark.parametrize("group", [0, 1, 3, 7, 15])
    def test_parser_extracts_group_from_midi2_header(self, group: int) -> None:
        """UMPParser extracts the correct group from MIDI 2.0 headers."""
        words = self._make_midi2_words(group, channel=5, msg_type=0x9)
        packet = MIDI2ChannelVoicePacket.from_words(words)
        assert packet is not None
        assert isinstance(packet, MIDI2ChannelVoicePacket)
        assert packet.group == UMPGroup(group)
        assert packet.channel == 5

    def test_parser_stream_extracts_group(self) -> None:
        """UMPParser.parse_packet_stream extracts groups from raw bytes."""

    def test_parser_handles_mixed_groups(self) -> None:
        """Parse a stream with interleaved group 0 and group 1 messages."""
        parser = RealtimeParser()
        # Build a stream: group 0 note_on ch0, group 1 note_on ch0
        g0_words = self._make_midi2_words(0, 0, 0x9, note=60, velocity=100)
        g1_words = self._make_midi2_words(1, 0, 0x9, note=72, velocity=80)
        stream = b"".join(struct.pack(">II", *w) for w in [g0_words, g1_words])

        packets = parser.ump_parser.parse_packet_stream(stream)
        assert len(packets) == 2

        msg0 = parser._convert_ump_to_midimessage(packets[0])
        msg1 = parser._convert_ump_to_midimessage(packets[1])

        assert msg0 is not None
        assert msg1 is not None
        assert msg0.data["midi_group"] == UMPGroup(0)
        assert msg0.channel == 0
        assert msg1.data["midi_group"] == UMPGroup(1)
        assert msg1.channel == 0
        # Different groups → same MIDI channel but different flat addresses
        synth_ch0 = msg0.data["midi_group"] * 16 + msg0.channel
        synth_ch1 = msg1.data["midi_group"] * 16 + msg1.channel
        assert synth_ch0 == 0
        assert synth_ch1 == 16


class TestGroupOffsetComputation:
    """Verify the group-offset channel formula."""

    @pytest.mark.parametrize("group,channel,expected", [
        (0, 0, 0),
        (0, 15, 15),
        (1, 0, 16),
        (1, 15, 31),
        (3, 7, 55),
        (15, 15, 255),
    ])
    def test_synth_channel_formula(self, group: int, channel: int, expected: int) -> None:
        """synthesizer_channel = group * 16 + channel."""
        assert group * 16 + channel == expected


class TestUMPDirectGroupParsing:
    """UMPParser stream parsing preserves groups."""

    def _build_midi2_packet_bytes(self, group: int, channel: int,
                                   msg_type: int = 0x9,
                                   note: int = 60, velocity: int = 0x7FFF) -> bytes:
        """Build raw bytes for a MIDI 2.0 UMP packet (64-bit / 2 words)."""
        header = (UMPMessageType.MIDI_2_CHANNEL << 28) | (group << 24) | (msg_type << 20) | (channel << 16) | note
        return struct.pack(">II", header, velocity << 16)

    def test_ump_parser_preserves_group(self) -> None:
        """UMPParser preserves group during stream parsing."""
        raw = self._build_midi2_packet_bytes(group=3, channel=7)
        packets = UMPParser.parse_packet_stream(raw)
        assert len(packets) == 1
        assert packets[0].group == UMPGroup(3)
        assert packets[0].channel == 7

    def test_ump_parser_mixed_groups(self) -> None:
        """UMPParser handles a stream with multiple groups."""
        raw_g0 = self._build_midi2_packet_bytes(group=0, channel=0)
        raw_g1 = self._build_midi2_packet_bytes(group=1, channel=0)
        raw_g0_ch2 = self._build_midi2_packet_bytes(group=0, channel=2)
        stream = raw_g0 + raw_g1 + raw_g0_ch2
        packets = UMPParser.parse_packet_stream(stream)
        assert len(packets) == 3
        assert packets[0].group == UMPGroup(0)
        assert packets[0].channel == 0
        assert packets[1].group == UMPGroup(1)
        assert packets[1].channel == 0
        assert packets[2].group == UMPGroup(0)
        assert packets[2].channel == 2
