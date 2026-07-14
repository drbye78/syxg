"""Tests for the sequencer module (synth/sequencer/)"""

from __future__ import annotations

import math

import pytest

from synth.sequencer import (
    ControlEvent,
    GrooveTemplate,
    NoteEvent,
    Pattern,
    QuantizeMode,
    RecordingMode,
    Song,
    Track,
)


# =========================================================================
# Enum tests
# =========================================================================


class TestQuantizeMode:
    @pytest.mark.unit
    def test_quantize_mode_values(self):
        assert QuantizeMode.OFF.value == 0
        assert QuantizeMode.Q_8TH.value == 1
        assert QuantizeMode.Q_16TH.value == 2
        assert QuantizeMode.Q_32ND.value == 3
        assert QuantizeMode.Q_TRIPLET.value == 4
        assert QuantizeMode.Q_SWING.value == 5


class TestGrooveTemplate:
    @pytest.mark.unit
    def test_groove_template_values(self):
        assert GrooveTemplate.STRAIGHT.value == 0
        assert GrooveTemplate.SWING_8TH.value == 1
        assert GrooveTemplate.SWING_16TH.value == 2
        assert GrooveTemplate.TRIPLET.value == 3
        assert GrooveTemplate.SHUFFLE.value == 4
        assert GrooveTemplate.HALF_TIME.value == 5
        assert GrooveTemplate.DOUBLE_TIME.value == 6


class TestRecordingMode:
    @pytest.mark.unit
    def test_recording_mode_values(self):
        assert RecordingMode.REAL_TIME.value == 0
        assert RecordingMode.STEP_INPUT.value == 1
        assert RecordingMode.OVERDUB.value == 2
        assert RecordingMode.REPLACE.value == 3


# =========================================================================
# NoteEvent tests
# =========================================================================


class TestNoteEvent:
    @pytest.mark.unit
    def test_note_event_init(self):
        note = NoteEvent(1.0, 0.5, 60, 100, channel=1, track_id=2)
        assert note.time == 1.0
        assert note.duration == 0.5
        assert note.note_number == 60
        assert note.velocity == 100
        assert note.channel == 1
        assert note.track_id == 2

    @pytest.mark.unit
    def test_note_event_defaults(self):
        note = NoteEvent(0.0, 1.0, 64, 80)
        assert note.channel == 0
        assert note.track_id == 0

    @pytest.mark.unit
    def test_to_midi_bytes_note_on(self):
        note = NoteEvent(0.0, 1.0, 60, 100, channel=0)
        on_bytes, _ = note.to_midi_bytes()
        assert on_bytes[0] == 0x90  # Note on status byte for channel 0
        assert on_bytes[1] == 60  # Note number
        assert on_bytes[2] == 100  # Velocity

    @pytest.mark.unit
    def test_to_midi_bytes_note_off(self):
        note = NoteEvent(0.0, 1.0, 60, 100, channel=0)
        _, off_bytes = note.to_midi_bytes()
        assert off_bytes[0] == 0x80  # Note off status byte for channel 0
        assert off_bytes[1] == 60  # Note number
        assert off_bytes[2] == 0  # Velocity is 0 for note off

    @pytest.mark.unit
    def test_to_midi_bytes_channel_not_zero(self):
        note = NoteEvent(0.0, 1.0, 72, 110, channel=5)
        on_bytes, off_bytes = note.to_midi_bytes()
        assert on_bytes[0] == 0x90 + 5  # 0x95
        assert off_bytes[0] == 0x80 + 5  # 0x85

    @pytest.mark.unit
    def test_get_end_time(self):
        note = NoteEvent(time=1.0, duration=0.5, note_number=60, velocity=100)
        assert note.get_end_time() == 1.5


# =========================================================================
# ControlEvent tests
# =========================================================================


class TestControlEvent:
    @pytest.mark.unit
    def test_control_event_init(self):
        ctrl = ControlEvent(2.0, 7, 100, channel=1, track_id=3)
        assert ctrl.time == 2.0
        assert ctrl.controller == 7
        assert ctrl.value == 100
        assert ctrl.channel == 1
        assert ctrl.track_id == 3

    @pytest.mark.unit
    def test_control_event_defaults(self):
        ctrl = ControlEvent(0.0, 10, 64)
        assert ctrl.channel == 0
        assert ctrl.track_id == 0

    @pytest.mark.unit
    def test_control_event_to_midi_bytes(self):
        ctrl = ControlEvent(1.0, 7, 100, channel=2)
        midi_bytes = ctrl.to_midi_bytes()
        assert midi_bytes[0] == 0xB0 + 2  # 0xB2
        assert midi_bytes[1] == 7  # Controller number
        assert midi_bytes[2] == 100  # Value


# =========================================================================
# Pattern tests
# =========================================================================


class TestPattern:
    @pytest.mark.unit
    def test_pattern_init(self):
        pattern = Pattern(0, "Test", 16)
        assert pattern.id == 0
        assert pattern.name == "Test"
        assert pattern.length == 16
        assert pattern.resolution == 96
        assert pattern.notes == []
        assert pattern.controls == []

    @pytest.mark.unit
    def test_pattern_add_note(self):
        pattern = Pattern(0, "Test", 16)
        note = NoteEvent(0.0, 0.5, 60, 100)
        pattern.add_note(note)
        assert len(pattern.notes) == 1
        assert pattern.notes[0] is note

    @pytest.mark.unit
    def test_pattern_add_control(self):
        pattern = Pattern(0, "Test", 16)
        ctrl = ControlEvent(0.0, 7, 100)
        pattern.add_control(ctrl)
        assert len(pattern.controls) == 1
        assert pattern.controls[0] is ctrl

    @pytest.mark.unit
    def test_pattern_remove_note(self):
        pattern = Pattern(0, "Test", 16)
        note1 = NoteEvent(0.0, 0.5, 60, 100)
        note2 = NoteEvent(1.0, 0.5, 64, 100)
        pattern.add_note(note1)
        pattern.add_note(note2)
        pattern.remove_note(0)
        assert len(pattern.notes) == 1
        assert pattern.notes[0] is note2

    @pytest.mark.unit
    def test_pattern_remove_note_out_of_range(self):
        """Removing an out-of-range index should be a no-op."""
        pattern = Pattern(0, "Test", 16)
        pattern.add_note(NoteEvent(0.0, 0.5, 60, 100))
        pattern.remove_note(99)  # Should not raise
        assert len(pattern.notes) == 1

    @pytest.mark.unit
    def test_pattern_clear(self):
        pattern = Pattern(0, "Test", 16)
        pattern.add_note(NoteEvent(0.0, 0.5, 60, 100))
        pattern.add_control(ControlEvent(0.0, 7, 100))
        pattern.clear()
        assert pattern.notes == []
        assert pattern.controls == []

    @pytest.mark.unit
    def test_pattern_get_notes_in_range(self):
        pattern = Pattern(0, "Test", 16)
        pattern.add_note(NoteEvent(0.0, 0.5, 60, 100))  # In range
        pattern.add_note(NoteEvent(1.0, 0.5, 64, 100))  # In range
        pattern.add_note(NoteEvent(2.5, 0.5, 67, 100))  # In range (end is exclusive)
        pattern.add_note(NoteEvent(4.0, 0.5, 72, 100))  # Out of range
        pattern.add_note(NoteEvent(-1.0, 0.5, 48, 100))  # Out of range

        result = pattern.get_notes_in_range(0.0, 3.0)
        assert len(result) == 3
        for note in result:
            assert 0.0 <= note.time < 3.0

    @pytest.mark.unit
    def test_pattern_get_total_duration_with_notes(self):
        pattern = Pattern(0, "Test", 8)
        pattern.add_note(NoteEvent(0.0, 0.5, 60, 100))
        pattern.add_note(NoteEvent(2.0, 0.75, 64, 100))
        pattern.add_note(NoteEvent(4.0, 3.5, 67, 100))  # Ends at 7.5
        # max_end_time = 7.5, length = 8 → returns 8
        assert pattern.get_total_duration() == 8.0

    @pytest.mark.unit
    def test_pattern_get_total_duration_exceeds_length(self):
        pattern = Pattern(0, "Test", 4)
        pattern.add_note(NoteEvent(0.0, 5.0, 60, 100))  # Ends at 5.0
        assert pattern.get_total_duration() == 5.0  # max(5.0, 4)

    @pytest.mark.unit
    def test_pattern_get_total_duration_no_notes(self):
        pattern = Pattern(0, "Test", 16)
        assert pattern.get_total_duration() == 16.0

    @pytest.mark.unit
    def test_pattern_quantize_notes(self):
        pattern = Pattern(0, "Test", 16)
        pattern.add_note(NoteEvent(0.3, 0.5, 60, 100))  # Q_16TH grid 0.25 → 0.25
        pattern.add_note(NoteEvent(0.8, 0.5, 64, 100))  # 0.8 / 0.25 = 3.2 → 3 → 0.75
        pattern.add_note(NoteEvent(1.1, 0.5, 67, 100))  # 1.1 / 0.25 = 4.4 → 4 → 1.0

        pattern.quantize_notes(QuantizeMode.Q_16TH, strength=1.0)

        assert math.isclose(pattern.notes[0].time, 0.25)
        assert math.isclose(pattern.notes[1].time, 0.75)
        assert math.isclose(pattern.notes[2].time, 1.0)
        assert pattern.quantize_mode == QuantizeMode.Q_16TH

    @pytest.mark.unit
    def test_pattern_quantize_notes_off_no_op(self):
        pattern = Pattern(0, "Test", 16)
        note = NoteEvent(0.3, 0.5, 60, 100)
        pattern.add_note(note)
        pattern.quantize_notes(QuantizeMode.OFF)
        assert note.time == 0.3  # Unchanged

    @pytest.mark.unit
    def test_pattern_quantize_notes_with_strength(self):
        """Partial strength should blend between original and quantized."""
        pattern = Pattern(0, "Test", 16)
        pattern.add_note(NoteEvent(0.3, 0.5, 60, 100))

        pattern.quantize_notes(QuantizeMode.Q_16TH, strength=0.5)
        # quantized_time = 0.25, original = 0.3
        # result = 0.3 * 0.5 + 0.25 * 0.5 = 0.275
        assert math.isclose(pattern.notes[0].time, 0.275, rel_tol=1e-9)

    @pytest.mark.unit
    def test_pattern_to_dict_roundtrip(self):
        pattern = Pattern(id=1, name="RoundtripPattern", length=8, resolution=192)
        pattern.add_note(NoteEvent(0.0, 0.5, 60, 100, channel=0, track_id=0))
        pattern.add_note(NoteEvent(1.0, 0.25, 64, 80, channel=0, track_id=1))
        pattern.add_control(ControlEvent(0.0, 7, 100, channel=0, track_id=0))
        pattern.quantize_mode = QuantizeMode.Q_16TH
        pattern.swing_amount = 0.3

        data = pattern.to_dict()
        restored = Pattern.from_dict(data)

        assert restored.id == pattern.id
        assert restored.name == pattern.name
        assert restored.length == pattern.length
        assert restored.resolution == pattern.resolution
        assert restored.tempo == pattern.tempo
        assert restored.time_signature == pattern.time_signature
        assert restored.swing_amount == pattern.swing_amount
        assert restored.quantize_mode == pattern.quantize_mode
        assert restored.created_time == pattern.created_time
        assert restored.modified_time == pattern.modified_time
        assert len(restored.notes) == len(pattern.notes)
        assert len(restored.controls) == len(pattern.controls)

        for n1, n2 in zip(pattern.notes, restored.notes):
            assert n1.time == n2.time
            assert n1.duration == n2.duration
            assert n1.note_number == n2.note_number
            assert n1.velocity == n2.velocity
            assert n1.channel == n2.channel
            assert n1.track_id == n2.track_id

    @pytest.mark.unit
    def test_pattern_apply_swing(self):
        pattern = Pattern(0, "Test", 16)
        note = NoteEvent(0.0, 0.5, 60, 100)
        pattern.add_note(note)

        pattern.apply_swing(0.5)
        assert pattern.swing_amount == 0.5
        # Note should be unchanged by current swing implementation
        assert note.time == 0.0

    @pytest.mark.unit
    def test_pattern_remove_control(self):
        pattern = Pattern(0, "Test", 16)
        ctrl1 = ControlEvent(0.0, 7, 100)
        ctrl2 = ControlEvent(1.0, 7, 64)
        pattern.add_control(ctrl1)
        pattern.add_control(ctrl2)
        pattern.remove_control(0)
        assert len(pattern.controls) == 1
        assert pattern.controls[0] is ctrl2

    @pytest.mark.unit
    def test_pattern_remove_control_out_of_range(self):
        pattern = Pattern(0, "Test", 16)
        pattern.add_control(ControlEvent(0.0, 7, 100))
        pattern.remove_control(99)  # Should not raise
        assert len(pattern.controls) == 1

    @pytest.mark.unit
    def test_pattern_quantize_modes(self):
        """Test all quantize modes produce expected grid values."""
        pattern = Pattern(0, "Test", 16)

        # Q_8TH: grid = 0.5 → round(0.3/0.5)*0.5 = round(0.6)*0.5 = 1*0.5 = 0.5
        p8 = Pattern(0, "Test", 16)
        p8.add_note(NoteEvent(0.3, 0.5, 60, 100))
        p8.quantize_notes(QuantizeMode.Q_8TH, strength=1.0)
        assert math.isclose(p8.notes[0].time, 0.5)

        # Q_32ND: grid = 0.125 → round(0.36/0.125)*0.125 = round(2.88)*0.125 = 3*0.125 = 0.375
        p32 = Pattern(0, "Test", 16)
        p32.add_note(NoteEvent(0.36, 0.5, 60, 100))
        p32.quantize_notes(QuantizeMode.Q_32ND, strength=1.0)
        assert math.isclose(p32.notes[0].time, 0.375)

        # Q_TRIPLET: grid = 1/3 → round(0.3/(1/3))*1/3 = round(0.9)*1/3 = 1*1/3 ≈ 0.333
        pt = Pattern(0, "Test", 16)
        pt.add_note(NoteEvent(0.3, 0.5, 60, 100))
        pt.quantize_notes(QuantizeMode.Q_TRIPLET, strength=1.0)
        expected = round(0.3 / (1.0 / 3.0)) * (1.0 / 3.0)
        assert math.isclose(pt.notes[0].time, expected)

        # Q_SWING: falls through to else: return time
        psw = Pattern(0, "Test", 16)
        psw.add_note(NoteEvent(0.3, 0.5, 60, 100))
        psw.quantize_notes(QuantizeMode.Q_SWING, strength=1.0)
        assert math.isclose(psw.notes[0].time, 0.3)


# =========================================================================
# Track tests
# =========================================================================


class TestTrack:
    @pytest.mark.unit
    def test_track_init(self):
        track = Track(id=1, name="Piano", channel=0, pattern_id=5, muted=False, solo=True, volume=80, pan=32)
        assert track.id == 1
        assert track.name == "Piano"
        assert track.channel == 0
        assert track.pattern_id == 5
        assert track.muted is False
        assert track.solo is True
        assert track.volume == 80
        assert track.pan == 32
        assert track.sequence == []

    @pytest.mark.unit
    def test_track_defaults(self):
        track = Track(id=1, name="Piano")
        assert track.channel == 0
        assert track.pattern_id == 0
        assert track.muted is False
        assert track.solo is False
        assert track.volume == 100
        assert track.pan == 64
        assert track.sequence == []

    @pytest.mark.unit
    def test_track_add_pattern_instance(self):
        track = Track(id=1, name="Drums")
        track.add_pattern_instance(pattern_id=10, start_time=0.0, length_multiplier=1.0)
        assert len(track.sequence) == 1
        assert track.sequence[0] == (10, 0.0, 1.0)

    @pytest.mark.unit
    def test_track_remove_pattern_instance(self):
        track = Track(id=1, name="Drums")
        track.add_pattern_instance(pattern_id=10, start_time=0.0)
        track.add_pattern_instance(pattern_id=20, start_time=4.0)
        track.remove_pattern_instance(0)
        assert len(track.sequence) == 1
        assert track.sequence[0][0] == 20

    @pytest.mark.unit
    def test_track_remove_pattern_instance_out_of_range(self):
        track = Track(id=1, name="Drums")
        track.add_pattern_instance(pattern_id=10, start_time=0.0)
        track.remove_pattern_instance(99)  # Should not raise
        assert len(track.sequence) == 1

    @pytest.mark.unit
    def test_track_get_patterns_at_time(self):
        track = Track(id=1, name="Bass")
        track.add_pattern_instance(pattern_id=1, start_time=0.0, length_multiplier=1.0)
        # Pattern length = 4.0 * 1.0 = 4.0 beats, active from 0.0 to 4.0

        # Inside the pattern
        active = track.get_patterns_at_time(2.0)
        assert len(active) == 1
        assert active[0] == (1, 0.0, 1.0)

        # At start boundary
        active = track.get_patterns_at_time(0.0)
        assert len(active) == 1

        # At end boundary (exclusive)
        active = track.get_patterns_at_time(4.0)
        assert len(active) == 0

        # Before start
        active = track.get_patterns_at_time(-1.0)
        assert len(active) == 0

    @pytest.mark.unit
    def test_track_get_patterns_at_time_multiple(self):
        track = Track(id=1, name="Bass")
        track.add_pattern_instance(pattern_id=1, start_time=0.0, length_multiplier=1.0)
        track.add_pattern_instance(pattern_id=2, start_time=2.0, length_multiplier=1.0)
        # Pattern 1: 0.0 - 4.0, Pattern 2: 2.0 - 6.0
        # At time 3.0, both are active
        active = track.get_patterns_at_time(3.0)
        assert len(active) == 2

    @pytest.mark.unit
    def test_track_clear_sequence(self):
        track = Track(id=1, name="Guitar")
        track.add_pattern_instance(pattern_id=1, start_time=0.0)
        track.add_pattern_instance(pattern_id=2, start_time=4.0)
        track.clear_sequence()
        assert track.sequence == []


# =========================================================================
# Song tests
# =========================================================================


class TestSong:
    @pytest.mark.unit
    def test_song_init(self):
        song = Song(id=0, name="TestSong")
        assert song.id == 0
        assert song.name == "TestSong"
        assert song.tempo == 120.0
        assert song.time_signature == (4, 4)
        assert song.length == 16
        assert song.tracks == []

    @pytest.mark.unit
    def test_song_add_track(self):
        song = Song(id=0, name="TestSong")
        track = Track(id=1, name="Piano")
        song.add_track(track)
        assert len(song.tracks) == 1
        assert song.tracks[0] is track

    @pytest.mark.unit
    def test_song_remove_track(self):
        song = Song(id=0, name="TestSong")
        song.add_track(Track(id=1, name="Piano"))
        song.add_track(Track(id=2, name="Drums"))
        song.remove_track(1)
        assert len(song.tracks) == 1
        assert song.tracks[0].id == 2

    @pytest.mark.unit
    def test_song_get_track(self):
        song = Song(id=0, name="TestSong")
        track1 = Track(id=1, name="Piano")
        track2 = Track(id=2, name="Drums")
        song.add_track(track1)
        song.add_track(track2)

        assert song.get_track(1) is track1
        assert song.get_track(2) is track2
        assert song.get_track(99) is None

    @pytest.mark.unit
    def test_song_get_active_tracks_at_time(self):
        song = Song(id=0, name="TestSong")
        track1 = Track(id=1, name="Bass", muted=False)
        track1.add_pattern_instance(pattern_id=10, start_time=0.0, length_multiplier=1.0)
        track2 = Track(id=2, name="Drums", muted=True)
        track2.add_pattern_instance(pattern_id=20, start_time=0.0, length_multiplier=1.0)
        track3 = Track(id=3, name="Piano", muted=False)
        # No pattern instance — should not be active

        song.add_track(track1)
        song.add_track(track2)
        song.add_track(track3)

        active = song.get_active_tracks_at_time(2.0)
        assert len(active) == 1
        assert active[0] is track1

    @pytest.mark.unit
    def test_song_get_active_tracks_at_time_no_tracks(self):
        song = Song(id=0, name="Empty")
        active = song.get_active_tracks_at_time(0.0)
        assert active == []

    @pytest.mark.unit
    def test_song_to_dict_roundtrip(self):
        song = Song(id=1, name="RoundtripSong", tempo=140.0, time_signature=(3, 4), length=8)
        track1 = Track(id=1, name="Piano", channel=0, volume=90, pan=32)
        track1.add_pattern_instance(pattern_id=5, start_time=0.0, length_multiplier=2.0)
        track2 = Track(id=2, name="Drums", channel=9, muted=True)
        track2.add_pattern_instance(pattern_id=3, start_time=0.0, length_multiplier=1.0)
        track2.add_pattern_instance(pattern_id=3, start_time=4.0, length_multiplier=1.0)
        song.add_track(track1)
        song.add_track(track2)

        data = song.to_dict()
        restored = Song.from_dict(data)

        assert restored.id == song.id
        assert restored.name == song.name
        assert restored.tempo == song.tempo
        assert restored.time_signature == song.time_signature
        assert restored.length == song.length
        assert restored.created_time == song.created_time
        assert restored.modified_time == song.modified_time
        assert len(restored.tracks) == len(song.tracks)

        for t1, t2 in zip(song.tracks, restored.tracks):
            assert t1.id == t2.id
            assert t1.name == t2.name
            assert t1.channel == t2.channel
            assert t1.pattern_id == t2.pattern_id
            assert t1.muted == t2.muted
            assert t1.solo == t2.solo
            assert t1.volume == t2.volume
            assert t1.pan == t2.pan
            assert t1.sequence == t2.sequence
