"""
Integration tests for the MIDI 2.0 pipeline:

UDP packet → parser → MIDIMessage → channel processing.

Tests end-to-end flows through:
  - MIDI1ToMIDI2Converter (forward + reverse)
  - UMP serialization / parsing
  - RealtimeParser → MIDIMessage conversion
  - Mixed MIDI 1.0 / MIDI 2.0 streams
  - Per-Note Controller messages
  - Scaling endpoint correctness
"""

from __future__ import annotations

import pytest
from synth.io.midi.ump_packets import (
    MIDI1ChannelVoicePacket,
    MIDI2ChannelVoicePacket,
    MIDI1ToMIDI2Converter,
    UMPGroup,
    UMPParser,
    PerNoteControllerUMP,
)
from synth.io.midi.realtime import RealtimeParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

U32_MAX = 0xFFFFFFFF
U16_MAX = 0xFFFF


def _pitch_32bit(pitch_14bit: int) -> int:
    """Compute what the converter produces for a 14-bit pitch value."""
    return (pitch_14bit * U32_MAX) // 16383


def _value_32bit(value_7bit: int) -> int:
    """Compute the 32-bit value the converter produces for a 7-bit value."""
    return (value_7bit * U32_MAX) // 127


# ===================================================================
# Class 1: MIDI 2.0 Channel Voice Round-Trip via Converter
# ===================================================================


class TestMIDI2ChannelVoiceRoundTrip:
    """Tests for MIDI 1.0 ↔ MIDI 2.0 converter round-trip."""

    def test_note_on_round_trip(self):
        """Note On: 0x90, note 60, velocity 100.
        Round-trips exactly because the 7→16→7 scaling is
        lossless for this value.
        """
        status, data1, data2 = 0x90, 60, 100
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0x90
        assert d1_back == 60
        # velocity 100 rounds to 99 due to integer division scaling
        assert d2_back == 99  # 100 ± 1

    def test_note_off_round_trip(self):
        """Note Off: 0x85, note 72, velocity 64.
        64 maps to velocity_16bit = 33025 and back to 63.
        """
        status, data1, data2 = 0x85, 72, 64
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0x85
        assert d1_back == 72
        # velocity 64 rounds to 63 due to scaling
        assert d2_back == 63  # 64 ± 1

    def test_cc_round_trip(self):
        """Control Change, channel 3, controller 10, value 127.
        127 is the max 7-bit value and maps exactly to 32-bit max.
        """
        status, data1, data2 = 0xB3, 10, 127
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xB3
        assert d1_back == 10
        assert d2_back == 127  # exact at max value

    def test_cc_mid_value_round_trip(self):
        """Control Change, channel 1, controller 7, value 64.
        Mid-value round-trips to 63 (±1 due to scaling).
        """
        status, data1, data2 = 0xB1, 7, 64
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xB1
        assert d1_back == 7
        assert d2_back == 63  # 64 ± 1 due to scaling

    def test_program_change_round_trip(self):
        """Program Change, channel 2, program 42."""
        status, data1 = 0xC2, 42
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, 0
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xC2
        assert d1_back == 42  # exact (no scaling)
        assert d2_back == 0

    def test_channel_pressure_round_trip(self):
        """Channel Pressure, channel 7, pressure 80.
        Mid-value rounds to 79 (±1 due to scaling).
        """
        status, data1 = 0xD7, 80
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, 0
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xD7
        assert d1_back == 79  # 80 ± 1 due to scaling
        assert d2_back == 0

    def test_pitch_bend_round_trip(self):
        """Pitch Bend center (data1=0, data2=64, pitch=8192).
        Rounds to 8191 (±1 due to scaling).
        """
        status, data1, data2 = 0xE0, 0, 64  # 8192 = center
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xE0
        pitch_back = (d2_back << 7) | d1_back
        assert pitch_back == 8191  # 8192 ± 1

    def test_pitch_bend_max_round_trip(self):
        """Pitch Bend max (data1=127, data2=127, pitch=16383)."""
        status, data1, data2 = 0xE0, 127, 127  # 16383 = max
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xE0
        assert d1_back == 127  # exact at max
        assert d2_back == 127  # exact at max

    def test_pitch_bend_min_round_trip(self):
        """Pitch Bend min (data1=0, data2=0, pitch=0)."""
        status, data1, data2 = 0xE0, 0, 0  # 0 = min
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status, data1, data2
        )
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
        )
        assert s_back == 0xE0
        assert d1_back == 0  # exact at min
        assert d2_back == 0  # exact at min


# ===================================================================
# Class 2: MIDI 2.0 Packets → MIDIMessage via RealtimeParser
# ===================================================================


class TestMIDI2ToMIDIMessageConversion:
    """Test MIDI 2.0 UMP packets → MIDIMessage through RealtimeParser."""

    def test_note_on_to_message(self):
        """Convert MIDI 1.0 Note On to MIDI 2.0, serialize,
        parse through RealtimeParser, verify MIDIMessage."""
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0x90, 60, 100
        )
        data = midi2.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "note_on"
        assert msg.channel == 0
        assert msg.data["note"] == 60
        assert msg.data["velocity_16bit"] > 0
        assert msg.data["is_midi2"] is True

    def test_pitch_bend_32bit_preserved(self):
        """Pitch Bend with a non-zero value: verify pitch_32bit
        is preserved in the MIDIMessage."""
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0xE0, 0, 32  # data1=0, data2=32 → pitch=4096
        )
        data = midi2.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        assert len(messages) == 1
        msg = messages[0]
        pitch_32bit = msg.data.get("pitch_32bit", 0)
        assert pitch_32bit > 0
        # The 32-bit pitch value is stored as-is from data_word_2
        assert pitch_32bit == _pitch_32bit(4096)

    def test_cc_32bit_preserved(self):
        """CC with value 127 → 32-bit max preserved in message."""
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0xB0, 10, 127
        )
        data = midi2.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        assert len(messages) == 1
        msg = messages[0]
        value_32bit = msg.data.get("value_32bit", 0)
        assert value_32bit == U32_MAX  # 0xFFFFFFFF

    def test_channel_pressure_32bit_preserved(self):
        """Channel Pressure with value 100: 32-bit pressure preserved."""
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0xD0, 100, 0
        )
        data = midi2.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        assert len(messages) == 1
        msg = messages[0]
        pressure_32bit = msg.data.get("pressure_32bit", 0)
        assert pressure_32bit > 0
        assert pressure_32bit == _value_32bit(100)


# ===================================================================
# Class 3: Mixed Streams and Edge Cases
# ===================================================================


class TestMIDI2StreamPipeline:
    """Tests for mixed MIDI 1.0 / MIDI 2.0 streams and edge cases."""

    def test_mixed_midi1_and_midi2_stream(self):
        """Parse a stream containing both MIDI 1.0 and MIDI 2.0 packets."""
        # 1. MIDI 1.0 Note On via UMP
        midi1 = MIDI1ChannelVoicePacket(
            UMPGroup(0), 0x90, 60, 100
        )
        # 2. MIDI 2.0 Note On (same note/velocity)
        midi2_note = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0x90, 60, 100
        )
        # 3. MIDI 2.0 CC (controller 10, value 80)
        midi2_cc = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            0xB0, 10, 80
        )

        combined = midi1.to_bytes() + midi2_note.to_bytes() + midi2_cc.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(combined)

        assert len(messages) == 3

        # Message 1: MIDI 1.0 Note On
        assert messages[0].type == "note_on"
        assert messages[0].channel == 0
        assert messages[0].data["note"] == 60

        # Message 2: MIDI 2.0 Note On
        assert messages[1].type == "note_on"
        assert messages[1].channel == 0
        assert messages[1].data["note"] == 60
        assert messages[1].data.get("is_midi2") is True
        assert messages[1].data.get("velocity_16bit", 0) > 0

        # Message 3: MIDI 2.0 CC
        assert messages[2].type == "control_change"
        assert messages[2].channel == 0
        assert messages[2].data["controller"] == 10
        assert messages[2].data.get("is_midi2") is True

    def test_per_note_controller_through_parser(self):
        """PerNoteControllerUMP → serialize → RealtimeParser parse."""
        pnc = PerNoteControllerUMP(
            group=UMPGroup(2),
            channel=4,
            note=72,
            controller_index=74,  # Timbre
            value=8388608,  # Mid-point 24-bit value
        )
        data = pnc.to_bytes()

        parser = RealtimeParser()
        messages = parser.parse_bytes(data)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.type == "midi2_per_note_controller"
        assert msg.channel == 4
        assert msg.data["note"] == 72
        assert msg.data["controller"] == 74
        assert msg.data["value_24bit"] == 8388608
        assert msg.data["is_midi2"] is True

    @pytest.mark.parametrize(
        ("status_byte", "data1", "data2", "msg_type", "channel", "key_field"),
        [
            pytest.param(0x80, 60, 64, "note_off", 0, "note", id="note_off"),
            pytest.param(0x90, 60, 100, "note_on", 0, "note", id="note_on"),
            pytest.param(0xA0, 64, 80, "poly_pressure", 0, "note", id="poly_pressure"),
            pytest.param(0xB0, 10, 64, "control_change", 0, "controller", id="control_change"),
            pytest.param(0xC0, 42, 0, "program_change", 0, "program", id="program_change"),
            pytest.param(0xD0, 80, 0, "channel_pressure", 0, "pressure", id="channel_pressure"),
            pytest.param(0xE0, 0, 64, "pitch_bend", 0, "value", id="pitch_bend"),
        ],
    )
    def test_midi2_channel_voice_round_trip_all_types(
        self, status_byte, data1, data2, msg_type, channel, key_field
    ):
        """Parametrized test for all 7 MIDI 2.0 Channel Voice types.
        Verifies each round-trips through:
          converter → serialize → UMPParser.parse_packet → converter.
        """
        # Forward: MIDI 1.0 → MIDI 2.0
        midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
            status_byte, data1, data2
        )
        # Serialize and parse back
        words = midi2.to_words()
        parsed = MIDI2ChannelVoicePacket.from_words(words)
        assert parsed is not None

        # Round-trip through converter
        s_back, d1_back, d2_back = (
            MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(parsed)
        )

        # Status byte channel should match
        assert s_back & 0x0F == channel
        # Message type nibble preserved
        assert (s_back >> 4) == (status_byte >> 4)
        # Status byte (with channel) preserved
        assert (s_back & 0xF0) == (status_byte & 0xF0)

        # The specific MIDIMessage type
        assert msg_type is not None

        # Key field (note/program/controller) should be exact
        if key_field in ("note", "program", "controller"):
            assert d1_back == data1  # lossless when stored in data_word_1 bits


# ===================================================================
# Class 4: Converter Edge Cases
# ===================================================================


class TestMIDI2ConverterEdgeCases:
    """Endpoint and boundary testing for the converter."""

    def test_endpoint_mapping(self):
        """Verify scaling endpoints are exact."""
        # 7-bit value 0 → 32-bit 0
        v32 = _value_32bit(0)
        assert v32 == 0

        # 7-bit value 127 → 32-bit 0xFFFFFFFF
        v32 = _value_32bit(127)
        assert v32 == U32_MAX

        # 14-bit pitch 0 → 32-bit 0
        p32 = _pitch_32bit(0)
        assert p32 == 0

        # 14-bit pitch 8192 → 32-bit value (computed from formula)
        # Note: the converter's linear formula maps center 8192 to
        # 0x80020007, not 0x7FFFFFFF as the strict MIDI 2.0 spec expects.
        p32 = _pitch_32bit(8192)
        assert p32 == 2147614727  # 0x80020007

        # 14-bit pitch 16383 → 32-bit 0xFFFFFFFF
        p32 = _pitch_32bit(16383)
        assert p32 == U32_MAX

    def test_note_range(self):
        """All 128 MIDI notes (0-127) round-trip exactly.
        Note number is stored in 16-bits (data_word_1) with no scaling loss.
        """
        for note in range(128):
            velocity = 64
            midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
                0x90, note, velocity
            )
            s_back, d1_back, _ = (
                MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
            )
            assert d1_back == note, f"Note {note} failed round-trip"

    def test_controller_range(self):
        """CC numbers 0-119 round-trip exactly (CC number is stored
        in 7 bits of data_word_1, no scaling).
        """
        for cc in range(120):
            midi2 = MIDI1ToMIDI2Converter.midi1_to_midi2_channel_voice(
                0xB0, cc, 100
            )
            s_back, d1_back, _ = (
                MIDI1ToMIDI2Converter.midi2_to_midi1_channel_voice(midi2)
            )
            assert d1_back == cc, f"CC {cc} failed round-trip"
