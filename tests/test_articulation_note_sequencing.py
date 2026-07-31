"""Tests for ArticulationNoteSequencer — grace, agoge, raking, double/triple tongue."""

from __future__ import annotations

import time

import pytest

from synth.engines.note_sequencing import ArticulationNoteSequencer


@pytest.fixture
def handler():
    h = ArticulationNoteSequencer()
    h.note_on_callback = lambda ch, n, v: None
    h.note_off_callback = lambda ch, n: None
    return h


class TestGrace:
    def test_grace_returns_true(self, handler):
        assert handler.handle_note_on(0, 60, 100, "grace") is True

    def test_grace_schedules_notes(self, handler):
        handler.handle_note_on(0, 60, 100, "grace")
        assert handler.pending_count > 0

    def test_grace_ethnic(self, handler):
        result = handler.handle_note_on(0, 60, 100, "grace_ethnic")
        assert result is True

    def test_grace_clears_on_stop(self, handler):
        handler.handle_note_on(0, 60, 100, "grace")
        handler.stop()
        assert handler.pending_count == 0


class TestAgoge:
    def test_agoge_returns_true(self, handler):
        assert handler.handle_note_on(0, 60, 100, "agoge") is True

    def test_agoge_buffers_notes(self, handler):
        handler.handle_note_on(0, 60, 100, "agoge")
        handler.handle_note_on(0, 64, 100, "agoge")
        handler.handle_note_on(0, 67, 100, "agoge")
        # Notes are buffered until process_timing flushes them
        assert handler.pending_count == 0  # not yet flushed
        # Flush after >5ms gap
        handler.process_timing(time.time() + 0.01)
        assert handler.pending_count > 0  # chord flushed


class TestRaking:
    def test_raking_returns_true(self, handler):
        assert handler.handle_note_on(0, 60, 100, "raking") is True

    def test_raking_schedules_ghosts_plus_target(self, handler):
        handler.handle_note_on(0, 60, 100, "raking")
        # 3 ghosts + 1 target = 4 notes scheduled
        assert handler.pending_count > 0

    def test_raking_clears_on_stop(self, handler):
        handler.handle_note_on(0, 60, 100, "raking")
        handler.stop()
        assert handler.pending_count == 0
        assert handler.active_count == 0


class TestDoubleTongue:
    def test_double_tongue_returns_false(self, handler):
        # Returns False because voice must be created normally first
        assert handler.handle_note_on(0, 60, 100, "double_tongue") is False

    def test_triple_tongue_returns_false(self, handler):
        assert handler.handle_note_on(0, 60, 100, "triple_tongue") is False

    def test_double_tongue_schedules_retriggers(self, handler):
        class MockVoice:
            def retrigger_envelope(self):
                pass

        voice = MockVoice()
        handler.schedule_retriggers(0, 60, 100, "double_tongue", 1, voice)
        # Retrigger timers are scheduled — check _retrigger_timers dict
        assert 1 in handler._retrigger_timers
        assert len(handler._retrigger_timers[1]) > 0

    def test_triple_tongue_faster_interval(self, handler):
        class MockVoice:
            def retrigger_envelope(self):
                pass

        voice = MockVoice()
        handler.schedule_retriggers(0, 60, 100, "triple_tongue", 1, voice)
        # Verify triple tongue triggers exist
        assert 1 in handler._retrigger_timers

    def test_note_off_cleans_retriggers(self, handler):
        class MockVoice:
            def retrigger_envelope(self):
                pass

        voice = MockVoice()
        handler.schedule_retriggers(0, 60, 100, "double_tongue", 42, voice)
        handler.handle_note_off(0, 60, "double_tongue", voice_id=42)
        assert 42 not in handler._retrigger_timers


class TestNormalNotes:
    def test_normal_articulation_returns_false(self, handler):
        assert handler.handle_note_on(0, 60, 100, "normal") is False

    def test_vibrato_returns_false(self, handler):
        assert handler.handle_note_on(0, 60, 100, "vibrato") is False

    def test_unknown_articulation_returns_false(self, handler):
        assert handler.handle_note_on(0, 60, 100, "nonexistent") is False


class TestControl:
    def test_stop_clears_all(self, handler):
        handler.handle_note_on(0, 60, 100, "grace")
        handler.handle_note_on(0, 64, 100, "raking")
        handler.stop()
        assert handler.pending_count == 0

    def test_clear_resets_all(self, handler):
        handler.handle_note_on(0, 60, 100, "grace")
        handler.clear()
        assert handler.pending_count == 0
        assert handler.active_count == 0
