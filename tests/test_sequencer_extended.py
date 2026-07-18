"""Tests for sequencer: GrooveQuantizer, MIDIFileHandler, PatternSequencer, SongMode, RecordingEngine."""
from __future__ import annotations

import os
import struct
import tempfile
from typing import Any

import numpy as np
import pytest

from synth.sequencer import (
    ControlEvent,
    GrooveQuantizer,
    GrooveTemplate,
    MIDIFileHandler,
    NoteEvent,
    PatternSequencer,
    QuantizeMode,
    SongMode,
)
from synth.sequencer.recording_engine import RecordingEngine
from synth.sequencer.groove_quantizer import GrooveTemplateData


# =========================================================================
# GrooveQuantizer tests
# =========================================================================


class TestGrooveTemplateData:
    def test_init(self):
        td = GrooveTemplateData(
            name="test",
            timing_offsets=[0.0, 0.1, 0.2, 0.3],
            velocity_multipliers=[1.0, 0.9, 1.0, 0.8],
        )
        assert td.name == "test"
        assert len(td.timing_offsets) == 4
        assert len(td.velocity_multipliers) == 4

    def test_init_default_velocities(self):
        td = GrooveTemplateData(name="test", timing_offsets=[0.0, 0.5, 1.0])
        assert len(td.velocity_multipliers) == 3
        assert np.all(td.velocity_multipliers == 1.0)

    def test_get_offset_for_position(self):
        td = GrooveTemplateData(
            name="test", timing_offsets=[0.0, 0.1, 0.2, 0.3]
        )
        assert td.get_offset_for_position(0) == 0.0
        assert td.get_offset_for_position(1) == 0.1
        assert td.get_offset_for_position(3) == 0.3
        # Out of range returns 0.0
        assert td.get_offset_for_position(999) == 0.0

    def test_get_velocity_multiplier(self):
        td = GrooveTemplateData(
            name="test",
            timing_offsets=[0.0] * 4,
            velocity_multipliers=[1.0, 0.9, 1.0, 0.8],
        )
        assert td.get_velocity_multiplier(0) == 1.0
        assert td.get_velocity_multiplier(1) == 0.9
        assert td.get_velocity_multiplier(3) == 0.8
        # Out of range returns 1.0
        assert td.get_velocity_multiplier(999) == 1.0


class TestGrooveQuantizer:
    def test_init(self):
        gq = GrooveQuantizer()
        assert gq is not None
        assert gq.current_template == GrooveTemplate.STRAIGHT
        assert gq.quantize_strength == 1.0
        assert gq.humanize_amount == 0.0
        assert gq.swing_amount == 0.0

    def test_init_builtin_templates(self):
        gq = GrooveQuantizer()
        templates = gq.get_available_templates()
        assert len(templates) >= 6
        template_types = [t[0] for t in templates]
        assert GrooveTemplate.STRAIGHT in template_types
        assert GrooveTemplate.SWING_8TH in template_types
        assert GrooveTemplate.SWING_16TH in template_types
        assert GrooveTemplate.TRIPLET in template_types
        assert GrooveTemplate.SHUFFLE in template_types

    def test_set_groove_template(self):
        gq = GrooveQuantizer()
        gq.set_groove_template(GrooveTemplate.SWING_8TH)
        assert gq.current_template == GrooveTemplate.SWING_8TH

    def test_set_groove_template_invalid(self):
        gq = GrooveQuantizer()
        gq.set_groove_template("NONEXISTENT")  # type: ignore[arg-type]
        # Should stay unchanged since "NONEXISTENT" not in templates
        assert gq.current_template == GrooveTemplate.STRAIGHT

    def test_set_quantize_strength(self):
        gq = GrooveQuantizer()
        gq.set_quantize_strength(0.5)
        assert gq.quantize_strength == 0.5

    def test_set_quantize_strength_clamp(self):
        gq = GrooveQuantizer()
        gq.set_quantize_strength(1.5)
        assert gq.quantize_strength == 1.0
        gq.set_quantize_strength(-0.5)
        assert gq.quantize_strength == 0.0

    def test_set_humanize_amount(self):
        gq = GrooveQuantizer()
        gq.set_humanize_amount(0.3)
        assert gq.humanize_amount == 0.3

    def test_set_swing_amount(self):
        gq = GrooveQuantizer()
        gq.set_swing_amount(0.75)
        assert gq.swing_amount == 0.75

    def test_quantize_notes_empty(self):
        gq = GrooveQuantizer()
        result = gq.quantize_notes([])
        assert result == []

    def test_quantize_notes_eighth(self):
        gq = GrooveQuantizer()
        notes = [NoteEvent(time=0.3, duration=0.5, note_number=60, velocity=100)]
        result = gq.quantize_notes(notes, mode=QuantizeMode.Q_8TH, template=GrooveTemplate.STRAIGHT)
        assert len(result) == 1
        # Q_8TH grid = 0.5, round(0.3/0.5)*0.5 = 0.5, strength=1.0
        assert result[0].time == 0.5

    def test_quantize_notes_sixteenth(self):
        gq = GrooveQuantizer()
        notes = [NoteEvent(time=0.3, duration=0.5, note_number=60, velocity=100)]
        result = gq.quantize_notes(notes, mode=QuantizeMode.Q_16TH, template=GrooveTemplate.STRAIGHT)
        assert len(result) == 1
        # Q_16TH grid = 0.25, round(0.3/0.25)*0.25 = round(1.2)*0.25 = 1*0.25 = 0.25
        assert result[0].time == 0.25

    def test_quantize_notes_with_strength(self):
        gq = GrooveQuantizer()
        gq.set_quantize_strength(0.5)
        notes = [NoteEvent(time=0.3, duration=0.5, note_number=60, velocity=100)]
        result = gq.quantize_notes(notes, mode=QuantizeMode.Q_16TH, template=GrooveTemplate.STRAIGHT)
        # 0.3 * 0.5 + 0.25 * 0.5 = 0.275
        assert result[0].time == 0.275

    def test_quantize_notes_velocity_adjustment(self):
        gq = GrooveQuantizer()
        notes = [NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100)]
        # SWING_8TH has velocity 0.9 on off-beat positions
        # position 0 is on-beat, velocity multiplier should be 1.0
        result = gq.quantize_notes(notes, mode=QuantizeMode.Q_16TH, template=GrooveTemplate.SWING_8TH)
        assert result[0].velocity == 100  # on-beat: multiplier 1.0

    def test_quantize_notes_off_mode(self):
        gq = GrooveQuantizer()
        notes = [NoteEvent(time=0.3, duration=0.5, note_number=60, velocity=100)]
        result = gq.quantize_notes(notes, mode=QuantizeMode.OFF)
        # OFF mode: no quantization
        assert result[0].time == 0.3

    def test_get_available_templates(self):
        gq = GrooveQuantizer()
        templates = gq.get_available_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0
        for template, name in templates:
            assert isinstance(name, str)

    def test_get_template_info(self):
        gq = GrooveQuantizer()
        info = gq.get_template_info(GrooveTemplate.STRAIGHT)
        assert info is not None
        assert info["name"] == "Straight"
        assert len(info["timing_offsets"]) == 16

    def test_get_template_info_nonexistent(self):
        gq = GrooveQuantizer()
        info = gq.get_template_info("NONEXISTENT")  # type: ignore[arg-type]
        assert info is None

    def test_create_custom_template(self):
        gq = GrooveQuantizer()
        key = gq.create_custom_template(
            name="Funk",
            timing_offsets=[0.0, 0.05, 0.0, 0.08],
            velocity_multipliers=[1.0, 0.8, 1.0, 0.7],
        )
        assert key is not None
        info = gq.get_template_info(key)
        assert info is not None
        assert info["name"] == "Funk"

    def test_analyze_groove_few_notes(self):
        gq = GrooveQuantizer()
        notes = [NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100)]
        result = gq.analyze_groove(notes)
        assert "error" in result

    def test_analyze_groove(self):
        gq = GrooveQuantizer()
        notes = [
            NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100),
            NoteEvent(time=0.5, duration=0.5, note_number=64, velocity=90),
            NoteEvent(time=1.0, duration=0.5, note_number=67, velocity=100),
            NoteEvent(time=1.5, duration=0.5, note_number=72, velocity=80),
            NoteEvent(time=2.0, duration=0.5, note_number=60, velocity=100),
        ]
        result = gq.analyze_groove(notes)
        assert "error" not in result
        assert result["note_count"] == 5
        assert result["timing_regularity"] >= 0.0
        assert result["estimated_tempo"] > 0

    def test_reset(self):
        gq = GrooveQuantizer()
        gq.set_groove_template(GrooveTemplate.SHUFFLE)
        gq.set_quantize_strength(0.5)
        gq.set_humanize_amount(0.3)
        gq.set_swing_amount(0.7)
        gq.reset()
        assert gq.current_template == GrooveTemplate.STRAIGHT
        assert gq.quantize_strength == 1.0
        assert gq.humanize_amount == 0.0
        assert gq.swing_amount == 0.0


# =========================================================================
# MIDIFileHandler tests
# =========================================================================


def _make_smf_header(format_type: int = 0, num_tracks: int = 1, division: int = 96) -> bytes:
    """Build a raw SMF header chunk."""
    return b"MThd" + struct.pack(">I", 6) + struct.pack(">HHH", format_type, num_tracks, division)


def _make_mtrk_chunk(event_data: bytes) -> bytes:
    """Wrap event data in an MTrk chunk."""
    return b"MTrk" + struct.pack(">I", len(event_data)) + event_data


class TestMIDIFileHandler:
    def test_init(self):
        mfh = MIDIFileHandler()
        assert mfh.format == 1
        assert mfh.division == 960
        assert mfh.tracks == []
        assert mfh.tempo_events == []
        assert mfh.time_sig_events == []

    def test_load_midi_file_smf0(self):
        """Round-trip write then read a minimal SMF format 0 file."""
        mfh = MIDIFileHandler()
        # Build a tiny SMF0: header + one track with a note_on and note_off
        track_events = bytes([
            0x00,                # delta=0
            0x90, 0x3C, 0x64,   # note_on ch0, note=60, vel=100
            0x60,                # delta=96
            0x80, 0x3C, 0x40,   # note_off ch0, note=60, vel=64
            0x00,                # delta=0
            0xFF, 0x2F, 0x00,   # end of track
        ])
        raw = _make_smf_header(0, 1, 96) + _make_mtrk_chunk(track_events)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            f.write(raw)
            path = f.name

        try:
            data = mfh.load_midi_file(path)
            assert data is not None
            assert data["format"] == 0
            assert data["num_tracks"] == 1
            assert data["ppq"] == 96
            assert len(data["tracks"]) == 1
            assert len(data["tracks"][0]) >= 2  # at least note_on + end_of_track
        finally:
            os.unlink(path)

    def test_load_midi_file_smf1(self):
        """Load SMF format 1 with two tracks."""
        mfh = MIDIFileHandler()
        track1 = bytes([
            0x00, 0x90, 0x3C, 0x64,
            0x60, 0x80, 0x3C, 0x40,
            0x00, 0xFF, 0x2F, 0x00,
        ])
        track2 = bytes([
            0x00, 0x90, 0x40, 0x50,
            0x60, 0x80, 0x40, 0x40,
            0x00, 0xFF, 0x2F, 0x00,
        ])
        raw = _make_smf_header(1, 2, 480) + _make_mtrk_chunk(track1) + _make_mtrk_chunk(track2)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            f.write(raw)
            path = f.name

        try:
            data = mfh.load_midi_file(path)
            assert data is not None
            assert data["format"] == 1
            assert data["num_tracks"] == 2
            assert data["ppq"] == 480
            assert len(data["tracks"]) == 2
        finally:
            os.unlink(path)

    def test_load_midi_file_invalid(self):
        mfh = MIDIFileHandler()
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            f.write(b"NOT A MIDI FILE")
            path = f.name
        try:
            data = mfh.load_midi_file(path)
            assert data is None
        finally:
            os.unlink(path)

    def test_load_midi_file_not_found(self):
        mfh = MIDIFileHandler()
        data = mfh.load_midi_file("/nonexistent/file.mid")
        assert data is None

    def test_save_midi_file_smf0(self):
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {
            "format": 0,
            "tracks": [
                [
                    {"type": "note_on", "ticks": 0, "channel": 0, "note": 60, "velocity": 100},
                    {"type": "note_off", "ticks": 96, "channel": 0, "note": 60, "velocity": 64},
                ]
            ],
            "ppq": 96,
        }
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name

        try:
            success = mfh.save_midi_file(midi_data, path)
            assert success is True
            assert os.path.getsize(path) > 0

            # Verify we can read it back
            loaded = mfh.load_midi_file(path)
            assert loaded is not None
            assert loaded["format"] == 0
        finally:
            os.unlink(path)

    def test_save_midi_file_smf1(self):
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {
            "format": 1,
            "tracks": [
                [
                    {"type": "note_on", "ticks": 0, "channel": 0, "note": 60, "velocity": 100},
                ],
                [
                    {"type": "note_on", "ticks": 0, "channel": 1, "note": 64, "velocity": 80},
                ],
            ],
            "ppq": 480,
        }
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name

        try:
            success = mfh.save_midi_file(midi_data, path)
            assert success is True

            loaded = mfh.load_midi_file(path)
            assert loaded is not None
            assert loaded["format"] == 1
            assert loaded["num_tracks"] == 2
        finally:
            os.unlink(path)

    def test_save_midi_file_error(self):
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {"format": 0, "tracks": [], "ppq": 96}
        success = mfh.save_midi_file(midi_data, "/nonexistent/dir/output.mid")
        assert success is False

    def test_save_and_load_with_tempo_and_time_sig(self):
        """Tempo and time signature survive a roundtrip write/load."""
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {
            "format": 1,
            "tracks": [
                [
                    {"type": "tempo_change", "ticks": 0, "tempo": 140.0},
                    {"type": "time_signature", "ticks": 0, "numerator": 3, "denominator": 4},
                    {"type": "note_on", "ticks": 0, "channel": 0, "note": 60, "velocity": 100},
                    {"type": "note_off", "ticks": 96, "channel": 0, "note": 60, "velocity": 64},
                ]
            ],
            "ppq": 960,
        }
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name

        try:
            success = mfh.save_midi_file(midi_data, path)
            assert success is True

            loaded = mfh.load_midi_file(path)
            assert loaded is not None

            track = loaded["tracks"][0]
            events_by_type = {e["type"]: e for e in track}
            assert "tempo_change" in events_by_type
            assert "time_signature" in events_by_type
            assert "note_on" in events_by_type
            assert "note_off" in events_by_type
        finally:
            os.unlink(path)

    def test_convert_to_sequencer_format(self):
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {
            "format": 0,
            "tracks": [
                [
                    {"type": "note_on", "ticks": 0, "channel": 0, "note": 60, "velocity": 100},
                    {"type": "note_off", "ticks": 96, "channel": 0, "note": 60, "velocity": 64},
                    {"type": "track_name", "ticks": 0, "name": "Piano"},
                    {"type": "tempo_change", "ticks": 0, "tempo": 120.0},
                ]
            ],
            "ppq": 960,
        }
        result = mfh.convert_to_sequencer_format(midi_data)
        assert result["format"] == "sequencer"
        assert result["ppq"] == 960
        assert 0 in result["tracks"]
        track_info = result["tracks"][0]
        assert track_info["name"] == "Piano"
        assert len(track_info["events"]) == 2
        assert len(track_info["tempo_events"]) == 1

    def test_get_midi_file_info(self):
        mfh = MIDIFileHandler()
        midi_data: dict[str, Any] = {
            "format": 1,
            "tracks": [
                [{"type": "note_on", "ticks": 0, "channel": 0, "note": 60, "velocity": 100}],
                [{"type": "note_on", "ticks": 480, "channel": 1, "note": 64, "velocity": 80}],
            ],
            "ppq": 960,
        }
        info = mfh.get_midi_file_info(midi_data)
        assert info["format"] == 1
        assert info["num_tracks"] == 2
        assert info["total_events"] == 2
        assert info["ppq"] == 960
        assert info["duration_seconds"] > 0

    def test_smf_format_0_parse_control_change(self):
        """Parse a track containing a control_change event."""
        mfh = MIDIFileHandler()
        track_data = bytes([
            0x00, 0xB0, 0x07, 0x64,  # delta=0, CC ch0, controller=7, value=100
            0x00, 0xFF, 0x2F, 0x00,  # end of track
        ])
        raw = _make_smf_header(0, 1, 96) + _make_mtrk_chunk(track_data)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            f.write(raw)
            path = f.name

        try:
            data = mfh.load_midi_file(path)
            assert data is not None
            track = data["tracks"][0]
            cc_events = [e for e in track if e["type"] == "control_change"]
            assert len(cc_events) == 1
            assert cc_events[0]["controller"] == 7
            assert cc_events[0]["value"] == 100
        finally:
            os.unlink(path)


# =========================================================================
# PatternSequencer tests
# =========================================================================


class TestPatternSequencer:
    @pytest.fixture
    def seq(self):
        return PatternSequencer()

    def test_init(self, seq):
        assert seq is not None
        assert seq.patterns == {}
        assert seq.is_playing is False

    def test_create_pattern(self, seq):
        pid = seq.create_pattern(name="test", length=16, resolution=96)
        assert pid == 1  # First pattern gets ID 1

    def test_create_pattern_custom_params(self, seq):
        pid = seq.create_pattern(name="long", length=32, resolution=192)
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert pattern.name == "long"
        assert pattern.length == 32
        assert pattern.resolution == 192

    def test_get_pattern_nonexistent(self, seq):
        assert seq.get_pattern(999) is None

    def test_delete_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        result = seq.delete_pattern(pid)
        assert result is True
        assert seq.get_pattern(pid) is None

    def test_delete_pattern_nonexistent(self, seq):
        result = seq.delete_pattern(999)
        assert result is False

    def test_get_pattern_list(self, seq):
        seq.create_pattern(name="a")
        seq.create_pattern(name="b")
        patterns = seq.get_pattern_list()
        assert len(patterns) == 2
        names = {p["name"] for p in patterns}
        assert names == {"a", "b"}

    def test_get_pattern_list_empty(self, seq):
        assert seq.get_pattern_list() == []

    def test_duplicate_pattern(self, seq):
        pid = seq.create_pattern(name="original", length=8)
        note = NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100)
        seq.add_note_to_pattern(pid, note)

        new_pid = seq.duplicate_pattern(pid, "copy")
        assert new_pid is not None
        assert new_pid != pid
        new_pattern = seq.get_pattern(new_pid)
        assert new_pattern is not None
        assert new_pattern.name == "copy"
        assert len(new_pattern.notes) == 1

    def test_duplicate_pattern_nonexistent(self, seq):
        new_pid = seq.duplicate_pattern(999, "copy")
        assert new_pid is None

    def test_add_note_to_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        note = NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100, channel=0, track_id=1)
        result = seq.add_note_to_pattern(pid, note)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert len(pattern.notes) == 1
        assert pattern.notes[0].note_number == 60

    def test_add_note_to_pattern_nonexistent(self, seq):
        note = NoteEvent(time=0.0, duration=0.5, note_number=60, velocity=100)
        result = seq.add_note_to_pattern(999, note)
        assert result is False

    def test_add_note_at_position(self, seq):
        pid = seq.create_pattern(name="test", length=16)
        result = seq.add_note_at_position(
            pid, step=0, note_number=60, velocity=100, duration=0.25, channel=0, track_id=1
        )
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert len(pattern.notes) == 1
        assert pattern.notes[0].time == 0.0  # step 0 at time 0

    def test_add_note_at_position_step_7(self, seq):
        pid = seq.create_pattern(name="test", length=16)
        seq.add_note_at_position(pid, step=7, note_number=64, velocity=80)
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        # Default grid_length = 16, length = 16, time_per_step = 16/16 = 1.0, step 7 = 7.0
        assert pattern.notes[0].time == 7.0

    def test_add_note_at_position_nonexistent(self, seq):
        result = seq.add_note_at_position(999, step=0, note_number=60, velocity=100)
        assert result is False

    def test_remove_note_from_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 60, 100))
        seq.add_note_to_pattern(pid, NoteEvent(1.0, 0.5, 64, 100))
        result = seq.remove_note_from_pattern(pid, 0)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert len(pattern.notes) == 1
        assert pattern.notes[0].note_number == 64

    def test_remove_note_from_pattern_nonexistent(self, seq):
        result = seq.remove_note_from_pattern(999, 0)
        assert result is False

    def test_clear_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 60, 100))
        result = seq.clear_pattern(pid)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert len(pattern.notes) == 0

    def test_clear_pattern_nonexistent(self, seq):
        result = seq.clear_pattern(999)
        assert result is False

    def test_get_grid_data(self, seq):
        pid = seq.create_pattern(name="test", length=16)
        seq.add_note_at_position(pid, step=0, note_number=60, velocity=100)
        seq.add_note_at_position(pid, step=4, note_number=64, velocity=80)
        grid = seq.get_grid_data(pid)
        assert len(grid) == 128  # 128 notes
        assert len(grid[0]) == 16  # 16 steps
        assert grid[60][0] == 100  # note 60 at step 0
        assert grid[64][4] == 80  # note 64 at step 4
        # Other positions should be None
        assert grid[60][1] is None

    def test_get_grid_data_with_track_filter(self, seq):
        pid = seq.create_pattern(name="test", length=16)
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 60, 100, track_id=1))
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 64, 80, track_id=2))
        grid = seq.get_grid_data(pid, track_id=1)
        assert grid[60][0] == 100
        assert grid[64][0] is None  # track_id=2 filtered out

    def test_get_grid_data_empty_pattern(self, seq):
        pid = seq.create_pattern(name="empty")
        grid = seq.get_grid_data(pid)
        # Returns a 128 x grid_length grid of None for empty patterns
        assert len(grid) == 128
        assert len(grid[0]) == seq.grid_length
        assert all(cell is None for row in grid for cell in row)

    def test_set_grid_resolution(self, seq):
        seq.set_grid_resolution(8)
        assert seq.grid_resolution == 8
        assert seq.grid_length == 32  # 4 * 8

    def test_set_grid_resolution_clamp(self, seq):
        seq.set_grid_resolution(1)
        assert seq.grid_resolution == 4
        seq.set_grid_resolution(100)
        assert seq.grid_resolution == 32

    def test_enable_disable_step_input(self, seq):
        seq.enable_step_input(note_number=72, velocity=90, duration=0.5)
        assert seq.step_input_enabled is True
        assert seq.step_input_note == 72
        assert seq.step_input_velocity == 90
        assert seq.step_input_duration == 0.5
        seq.disable_step_input()
        assert seq.step_input_enabled is False

    def test_input_step_note(self, seq):
        pid = seq.create_pattern(name="test")
        seq.enable_step_input(note_number=60, velocity=100, duration=0.25)
        result = seq.input_step_note(step=2, pattern_id=pid)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert len(pattern.notes) == 1
        assert pattern.notes[0].note_number == 60

    def test_input_step_note_disabled(self, seq):
        result = seq.input_step_note(step=0)
        assert result is False

    def test_input_step_note_no_pattern(self, seq):
        seq.enable_step_input()
        result = seq.input_step_note(step=0)
        assert result is False  # no current_pattern_id and no pattern_id provided

    def test_set_pattern_chain(self, seq):
        pid1 = seq.create_pattern(name="a")
        pid2 = seq.create_pattern(name="b")
        seq.set_pattern_chain([pid1, pid2])
        assert seq.pattern_chain == [pid1, pid2]
        assert seq.current_chain_index == 0

    def test_get_next_pattern_in_chain(self, seq):
        pid1 = seq.create_pattern(name="a")
        pid2 = seq.create_pattern(name="b")
        seq.set_pattern_chain([pid1, pid2])
        assert seq.get_next_pattern_in_chain() == pid1
        assert seq.get_next_pattern_in_chain() == pid2
        assert seq.get_next_pattern_in_chain() == pid1  # wraps around

    def test_get_next_pattern_in_chain_empty(self, seq):
        assert seq.get_next_pattern_in_chain() is None

    def test_quantize_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        seq.add_note_to_pattern(pid, NoteEvent(0.3, 0.5, 60, 100))
        result = seq.quantize_pattern(pid, mode=QuantizeMode.Q_16TH, strength=1.0)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert pattern.notes[0].time == 0.25

    def test_quantize_pattern_nonexistent(self, seq):
        result = seq.quantize_pattern(999, mode=QuantizeMode.Q_16TH)
        assert result is False

    def test_apply_swing_to_pattern(self, seq):
        pid = seq.create_pattern(name="test")
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 60, 100))
        result = seq.apply_swing_to_pattern(pid, amount=0.5)
        assert result is True
        pattern = seq.get_pattern(pid)
        assert pattern is not None
        assert pattern.swing_amount == 0.5

    def test_apply_swing_to_pattern_nonexistent(self, seq):
        result = seq.apply_swing_to_pattern(999, amount=0.5)
        assert result is False

    def test_start_stop_playback(self, seq):
        pid = seq.create_pattern(name="test")
        result = seq.start_playback(pattern_id=pid, loop=False)
        assert result is True
        assert seq.is_playing is True
        seq.stop_playback()
        assert seq.is_playing is False

    def test_start_playback_nonexistent(self, seq):
        result = seq.start_playback(pattern_id=999)
        assert result is False

    def test_start_playback_no_pattern(self, seq):
        result = seq.start_playback()
        assert result is False

    def test_pause_playback(self, seq):
        pid = seq.create_pattern(name="test")
        seq.start_playback(pattern_id=pid)
        seq.pause_playback()
        assert seq.is_playing is False

    def test_set_get_playback_position(self, seq):
        pid = seq.create_pattern(name="test", length=16)
        seq.start_playback(pattern_id=pid)
        seq.set_playback_position(4.0)
        pos = seq.get_playback_position()
        assert pos == 4.0
        seq.stop_playback()

    def test_get_playback_status(self, seq):
        pid = seq.create_pattern(name="test")
        seq.start_playback(pattern_id=pid)
        status = seq.get_playback_status()
        assert status["is_playing"] is True
        assert status["current_pattern_id"] == pid
        seq.stop_playback()

    def test_save_load_pattern_roundtrip(self, seq):
        pid = seq.create_pattern(name="roundtrip", length=8, resolution=96)
        seq.add_note_to_pattern(pid, NoteEvent(0.0, 0.5, 60, 100, channel=0, track_id=0))
        seq.add_note_to_pattern(pid, NoteEvent(1.0, 0.25, 64, 80, channel=0, track_id=1))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            success = seq.save_pattern_to_file(pid, path)
            assert success is True

            loaded_pid = seq.load_pattern_from_file(path)
            assert loaded_pid is not None
            loaded = seq.get_pattern(loaded_pid)
            assert loaded is not None
            assert loaded.name == "roundtrip"
            assert len(loaded.notes) == 2
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_save_pattern_nonexistent(self, seq):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = seq.save_pattern_to_file(999, path)
            assert result is False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_load_pattern_invalid_file(self, seq):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b"invalid json")
            path = f.name
        try:
            result = seq.load_pattern_from_file(path)
            assert result is None
        finally:
            os.unlink(path)

    def test_load_pattern_nonexistent_file(self, seq):
        result = seq.load_pattern_from_file("/nonexistent/file.json")
        assert result is None

    def test_get_playback_position_no_pattern(self, seq):
        assert seq.get_playback_position() == 0.0

    def test_reset(self, seq):
        seq.create_pattern(name="a")
        seq.create_pattern(name="b")
        seq.set_pattern_chain([1, 2])
        seq.reset()
        assert seq.patterns == {}
        assert seq.current_pattern_id is None
        assert seq.pattern_chain == []
        assert seq.next_pattern_id == 1
        assert seq.step_input_enabled is False


# =========================================================================
# SongMode tests
# =========================================================================


class TestSongMode:
    @pytest.fixture
    def song(self):
        return SongMode()

    def test_init(self, song):
        assert song.max_tracks == 64
        assert song.ppq == 960
        assert song.tracks == {}
        assert song.tempo == 120.0
        assert song.time_signature == (4, 4)
        assert song.song_name == "Untitled Song"
        assert song.is_playing is False

    def test_init_custom_params(self):
        song = SongMode(max_tracks=16, ppq=480)
        assert song.max_tracks == 16
        assert song.ppq == 480

    def test_create_track(self, song):
        result = song.create_track(0, "Piano")
        assert result is True
        assert 0 in song.tracks
        assert song.tracks[0]["name"] == "Piano"

    def test_create_track_default_name(self, song):
        song.create_track(5)
        assert song.tracks[5]["name"] == "Track 6"

    def test_create_track_duplicate(self, song):
        song.create_track(0, "Piano")
        result = song.create_track(0, "Drums")  # Already exists
        assert result is False
        assert song.tracks[0]["name"] == "Piano"  # Unchanged

    def test_create_track_max_exceeded(self, song):
        song.max_tracks = 2
        result = song.create_track(5)
        assert result is False

    def test_add_note_event(self, song):
        song.create_track(0)
        result = song.add_note_event(0, start_tick=0, duration_ticks=96, note_number=60, velocity=100)
        assert result is True
        events = song.tracks[0]["events"]
        assert len(events) == 2  # note_on + note_off
        assert events[0]["type"] == "note_on"
        assert events[0]["tick"] == 0
        assert events[1]["type"] == "note_off"
        assert events[1]["tick"] == 96

    def test_add_note_event_invalid_track(self, song):
        result = song.add_note_event(999, start_tick=0, duration_ticks=96, note_number=60, velocity=100)
        assert result is False

    def test_add_control_change(self, song):
        song.create_track(0)
        result = song.add_control_change(0, tick=48, controller=7, value=100)
        assert result is True
        events = song.tracks[0]["events"]
        assert len(events) == 1
        assert events[0]["type"] == "control_change"
        assert events[0]["controller"] == 7

    def test_add_tempo_change(self, song):
        result = song.add_tempo_change(tick=0, tempo=140.0)
        assert result is True
        assert len(song.tempo_events) == 1
        assert song.tempo_events[0]["tempo"] == 140.0

    def test_add_tempo_change_sorts(self, song):
        song.add_tempo_change(tick=96, tempo=160.0)
        song.add_tempo_change(tick=0, tempo=120.0)
        assert song.tempo_events[0]["tick"] == 0
        assert song.tempo_events[1]["tick"] == 96

    def test_add_time_signature_change(self, song):
        result = song.add_time_signature_change(tick=0, numerator=3, denominator=4)
        assert result is True
        assert len(song.time_signature_events) == 1

    def test_get_tempo_at_tick_default(self, song):
        tempo = song.get_tempo_at_tick(0)
        assert tempo == 120.0

    def test_get_tempo_at_tick_with_changes(self, song):
        song.add_tempo_change(tick=0, tempo=140.0)
        song.add_tempo_change(tick=96, tempo=160.0)
        assert song.get_tempo_at_tick(0) == 140.0
        assert song.get_tempo_at_tick(48) == 140.0
        assert song.get_tempo_at_tick(96) == 160.0
        assert song.get_tempo_at_tick(192) == 160.0

    def test_get_time_signature_at_tick(self, song):
        song.add_time_signature_change(tick=0, numerator=3, denominator=4)
        ts = song.get_time_signature_at_tick(0)
        assert ts == (3, 4)

    def test_get_time_signature_at_tick_default(self, song):
        ts = song.get_time_signature_at_tick(0)
        assert ts == (4, 4)

    def test_get_events_at_position(self, song):
        song.create_track(0)
        song.add_note_event(0, start_tick=0, duration_ticks=96, note_number=60, velocity=100)
        song.add_tempo_change(tick=0, tempo=140.0)
        events = song.get_events_at_position(0)
        assert len(events) >= 2  # tempo change + note_on
        types = {e["type"] for e in events}
        assert "tempo_change" in types
        assert "note_on" in types

    def test_get_events_at_position_muted_track(self, song):
        song.create_track(0)
        song.add_note_event(0, start_tick=0, duration_ticks=96, note_number=60, velocity=100)
        song.tracks[0]["muted"] = True
        events = song.get_events_at_position(0)
        note_events = [e for e in events if e["type"] == "note_on"]
        assert len(note_events) == 0  # muted track excluded

    def test_start_stop_playback(self, song):
        result = song.start_playback(start_tick=0)
        assert result is True
        assert song.is_playing is True
        assert song.current_position == 0
        song.stop_playback()
        assert song.is_playing is False

    def test_get_playback_info(self, song):
        info = song.get_playback_info()
        assert info["is_playing"] is False
        assert info["tempo"] == 120.0
        assert info["time_signature"] == (4, 4)

    def test_clear_track(self, song):
        song.create_track(0)
        song.add_note_event(0, start_tick=0, duration_ticks=96, note_number=60, velocity=100)
        result = song.clear_track(0)
        assert result is True
        assert song.tracks[0]["events"] == []

    def test_clear_track_invalid(self, song):
        result = song.clear_track(999)
        assert result is False

    def test_delete_track(self, song):
        song.create_track(0)
        result = song.delete_track(0)
        assert result is True
        assert 0 not in song.tracks

    def test_delete_track_invalid(self, song):
        result = song.delete_track(999)
        assert result is False

    def test_get_track_info(self, song):
        song.create_track(0, "Piano")
        info = song.get_track_info(0)
        assert info is not None
        assert info["name"] == "Piano"
        assert info["event_count"] >= 0

    def test_get_track_info_invalid(self, song):
        info = song.get_track_info(999)
        assert info is None

    def test_song_name_settable(self, song):
        song.song_name = "My Song"
        assert song.song_name == "My Song"

    def test_tempo_settable(self, song):
        song.tempo = 140.0
        assert song.tempo == 140.0

    def test_loop_settings(self, song):
        song.loop_start = 0
        song.loop_end = 960
        song.loop_enabled = True
        assert song.loop_enabled is True
        info = song.get_playback_info()
        assert info["loop_enabled"] is True
        assert info["loop_start"] == 0
        assert info["loop_end"] == 960


# =========================================================================
# RecordingEngine tests
# =========================================================================


class TestRecordingEngine:
    @pytest.fixture
    def engine(self):
        return RecordingEngine()

    def test_init(self, engine):
        assert engine.is_recording is False
        assert engine.is_playing is False
        assert engine.sample_rate == 44100
        assert engine.max_tracks == 64
        assert engine.ppq == 960
        assert engine.tempo == 120.0

    def test_start_recording(self, engine):
        result = engine.start_recording(track_number=0, record_type="midi", start_position=0)
        assert result is True
        assert engine.is_recording is True
        assert 0 in engine.active_record_tracks

    def test_start_recording_track_exists(self, engine):
        engine.start_recording(track_number=0)
        assert 0 in engine.tracks

    def test_start_recording_max_tracks(self, engine):
        engine.max_tracks = 2
        result = engine.start_recording(track_number=5)
        assert result is False

    def test_stop_recording(self, engine):
        engine.start_recording(track_number=0)
        result = engine.stop_recording()
        assert result is True
        assert engine.is_recording is False

    def test_stop_recording_not_recording(self, engine):
        result = engine.stop_recording()
        assert result is False

    def test_record_midi_event(self, engine):
        engine.start_recording(track_number=0, record_type="midi")
        event: dict[str, Any] = {"type": "note_on", "note": 60, "velocity": 100, "channel": 0}
        result = engine.record_midi_event(track_number=0, event_data=event)
        assert result is True
        track_data = engine.get_track_data(0)
        assert track_data is not None
        assert len(track_data["events"]) == 1
        assert track_data["events"][0]["note"] == 60

    def test_record_midi_event_not_recording(self, engine):
        event: dict[str, Any] = {"type": "note_on", "note": 60, "velocity": 100}
        result = engine.record_midi_event(track_number=0, event_data=event)
        assert result is False

    def test_record_midi_event_wrong_track(self, engine):
        engine.start_recording(track_number=0)
        event: dict[str, Any] = {"type": "note_on", "note": 60, "velocity": 100}
        result = engine.record_midi_event(track_number=1, event_data=event)
        assert result is False

    def test_record_midi_event_assigns_timestamp(self, engine):
        engine.start_recording(track_number=0)
        event: dict[str, Any] = {"type": "note_on", "note": 60, "velocity": 100}
        engine.record_midi_event(track_number=0, event_data=event)
        track_data = engine.get_track_data(0)
        assert track_data is not None
        assert "timestamp" in track_data["events"][0]
        assert track_data["events"][0]["timestamp"] >= 0

    def test_record_midi_event_updates_length(self, engine):
        engine.start_recording(track_number=0)
        engine.record_midi_event(track_number=0, event_data={"type": "note_on", "note": 60, "velocity": 100})
        track_data = engine.get_track_data(0)
        assert track_data is not None
        assert track_data["length"] >= 0

    def test_record_audio_block(self, engine):
        engine.start_recording(track_number=0, record_type="audio")
        block = np.zeros((256, 2), dtype=np.float32)
        result = engine.record_audio_block(track_number=0, audio_block=block, block_position=0)
        assert result is True

    def test_record_audio_block_wrong_type(self, engine):
        engine.start_recording(track_number=0, record_type="midi")
        block = np.zeros((256, 2), dtype=np.float32)
        result = engine.record_audio_block(track_number=0, audio_block=block, block_position=0)
        assert result is False

    def test_enable_punch_in_out(self, engine):
        result = engine.enable_punch_in_out(punch_in=96, punch_out=480)
        assert result is True
        assert engine.punch_in_enabled is True
        assert engine.punch_out_enabled is True
        assert engine.punch_in_position == 96
        assert engine.punch_out_position == 480

    def test_disable_punch_in_out(self, engine):
        engine.enable_punch_in_out(96, 480)
        result = engine.disable_punch_in_out()
        assert result is True
        assert engine.punch_in_enabled is False
        assert engine.punch_out_enabled is False

    def test_set_overdub_mode(self, engine):
        result = engine.set_overdub_mode(enabled=True)
        assert result is True
        assert engine.overdub_enabled is True
        assert engine.replace_enabled is False

        result = engine.set_overdub_mode(enabled=False)
        assert result is True
        assert engine.overdub_enabled is False
        assert engine.replace_enabled is True

    def test_get_recording_status(self, engine):
        engine.start_recording(track_number=0, record_type="midi")
        status = engine.get_recording_status()
        assert status["is_recording"] is True
        assert status["active_tracks"] == [0]
        engine.stop_recording()

    def test_get_recording_status_idle(self, engine):
        status = engine.get_recording_status()
        assert status["is_recording"] is False
        assert status["active_tracks"] == []

    def test_get_track_data_nonexistent(self, engine):
        data = engine.get_track_data(999)
        assert data is None

    def test_clear_track(self, engine):
        engine.start_recording(track_number=0, record_type="midi")
        engine.record_midi_event(track_number=0, event_data={"type": "note_on", "note": 60, "velocity": 100})
        engine.stop_recording()
        result = engine.clear_track(0)
        assert result is True
        track_data = engine.get_track_data(0)
        assert track_data is not None
        assert track_data["events"] == []

    def test_clear_track_nonexistent(self, engine):
        result = engine.clear_track(999)
        assert result is False

    def test_set_quantize_settings(self, engine):
        result = engine.set_quantize_settings(enabled=True, grid_size=240)
        assert result is True
        assert engine.quantize_enabled is True
        assert engine.quantize_grid == 240

    def test_get_recording_stats(self, engine):
        stats = engine.get_recording_stats()
        assert stats["total_tracks"] == 0
        assert stats["total_events"] == 0

    def test_get_recording_stats_after_recording(self, engine):
        engine.start_recording(track_number=0, record_type="midi")
        engine.record_midi_event(track_number=0, event_data={"type": "note_on", "note": 60, "velocity": 100})
        engine.record_midi_event(track_number=0, event_data={"type": "note_off", "note": 60, "velocity": 0})
        engine.stop_recording()
        stats = engine.get_recording_stats()
        assert stats["total_tracks"] == 1
        assert stats["total_events"] == 2

    def test_start_recording_audio_initializes_buffer(self, engine):
        result = engine.start_recording(track_number=0, record_type="audio")
        assert result is True
        assert engine.current_audio_buffer is not None
        assert engine.current_audio_buffer.shape[1] == 2
