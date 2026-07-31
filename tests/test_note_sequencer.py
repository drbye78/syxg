"""Tests for NoteSequencer — general-purpose note-level event scheduler."""

from __future__ import annotations

import time

import pytest

from synth.sequencer.note_sequencer import NoteSequencer
from synth.sequencer.sequencer_types import NoteEvent, NotePlayState, SequencedNote


@pytest.fixture
def seq() -> NoteSequencer:
    s = NoteSequencer(tempo=120.0)
    s._fired = []
    s.note_on_callback = lambda ch, n, v: s._fired.append(("on", ch, n, v))
    s.note_off_callback = lambda ch, n: s._fired.append(("off", ch, n))
    return s


class TestSchedule:
    def test_single_note_triggers_on_and_off(self, seq):
        now = time.time()
        evt = NoteEvent(time=0.0, duration=0.25, note_number=60, velocity=100, channel=0)
        sn = seq.schedule(evt, start_time=now + 0.05)

        assert sn.state == NotePlayState.PENDING
        assert seq.pending_count == 1
        assert seq.active_count == 0

        # Not yet
        seq.process_timing(now + 0.01)
        assert len(seq._fired) == 0

        # Note-on
        seq.process_timing(now + 0.10)
        assert seq._fired == [("on", 0, 60, 100)]
        assert seq.active_count == 1
        assert seq.pending_count == 0

        # Note-off (0.25 beats at 120 BPM = 0.125s; note fires at now+0.05, off at now+0.175)
        seq.process_timing(now + 0.20)
        assert len(seq._fired) == 2
        assert seq._fired[1] == ("off", 0, 60)

        # Cleanup
        seq.process_timing(now + 1.0)
        assert seq.total_count == 0

    def test_schedule_sequence(self, seq):
        now = time.time()
        notes = [
            NoteEvent(time=0.0, duration=0.1, note_number=60, velocity=100, channel=0),
            NoteEvent(time=0.0, duration=0.1, note_number=64, velocity=80, channel=0),
            NoteEvent(time=0.5, duration=0.1, note_number=67, velocity=90, channel=0),
        ]
        sns = seq.schedule_sequence(notes, start_time=now + 0.05)
        assert len(sns) == 3
        assert seq.pending_count == 3

        # Two fire immediately, one later
        seq.process_timing(now + 0.10)
        ons = [f for f in seq._fired if f[0] == "on"]
        assert len(ons) == 2

        seq.process_timing(now + 0.60)
        ons = [f for f in seq._fired if f[0] == "on"]
        assert len(ons) == 3

    def test_schedule_default_start_time(self, seq):
        evt = NoteEvent(time=0.0, duration=1.0, note_number=60, velocity=100, channel=0)
        sn = seq.schedule(evt)
        assert sn.state == NotePlayState.PENDING
        # Should be scheduled roughly at current time
        assert sn.trigger_time <= time.time() + 0.01


class TestCancel:
    def test_cancel_pending(self, seq):
        now = time.time()
        evt = NoteEvent(time=0.0, duration=1.0, note_number=60, velocity=100, channel=0)
        sn = seq.schedule(evt, start_time=now + 10.0)

        assert seq.cancel(sn) is True
        assert sn.state == NotePlayState.CANCELLED

        # Stale heap entry should be cleaned up
        seq.process_timing(now + 20.0)
        assert seq.total_count == 0

    def test_cancel_active_fires_note_off(self, seq):
        now = time.time()
        evt = NoteEvent(time=0.0, duration=10.0, note_number=72, velocity=100, channel=2)
        sn = seq.schedule(evt, start_time=now + 0.01)

        seq.process_timing(now + 0.05)
        assert len(seq._fired) == 1  # note-on

        assert seq.cancel(sn) is True
        assert len(seq._fired) == 2  # note-off fired
        assert seq._fired[1] == ("off", 2, 72)

    def test_cancel_twice_returns_false(self, seq):
        now = time.time()
        evt = NoteEvent(time=0.0, duration=1.0, note_number=60, velocity=100, channel=0)
        sn = seq.schedule(evt, start_time=now + 10.0)

        assert seq.cancel(sn) is True
        assert seq.cancel(sn) is False  # Already cancelled

    def test_cancel_unknown_note(self, seq):
        fake = SequencedNote(
            event=NoteEvent(time=0.0, duration=1.0, note_number=60, velocity=100, channel=0),
            trigger_time=0.0,
            seq_id=99999,
        )
        assert seq.cancel(fake) is False


class TestCancelAll:
    def test_cancel_all_active_fires_note_offs(self, seq):
        now = time.time()
        notes = [
            NoteEvent(time=0.0, duration=10.0, note_number=60, velocity=100, channel=0),
            NoteEvent(time=0.0, duration=10.0, note_number=64, velocity=80, channel=1),
        ]
        seq.schedule_sequence(notes, start_time=now + 0.01)
        seq.process_timing(now + 0.05)  # Both fire note-on
        assert len(seq._fired) == 2

        seq.cancel_all()
        assert len(seq._fired) == 4  # Two note-offs added
        assert seq.total_count == 0
        assert len(seq._heap) == 0

    def test_cancel_all_pending_clears_queue(self, seq):
        now = time.time()
        notes = [NoteEvent(time=0.0, duration=1.0, note_number=n, velocity=100, channel=0) for n in (60, 64, 67)]
        seq.schedule_sequence(notes, start_time=now + 10.0)

        assert seq.pending_count == 3
        seq.cancel_all()
        assert seq.total_count == 0
        assert len(seq._heap) == 0


class TestLifecycle:
    def test_stop_fires_note_offs_and_clears(self, seq):
        now = time.time()
        notes = [
            NoteEvent(time=0.0, duration=10.0, note_number=60, velocity=100, channel=0),
        ]
        seq.schedule_sequence(notes, start_time=now + 0.01)
        seq.process_timing(now + 0.05)
        assert len(seq._fired) == 1  # note-on

        seq.stop()
        assert len(seq._fired) == 2  # note-off fired
        assert seq.total_count == 0

    def test_clear_hard_reset_no_note_offs(self, seq):
        now = time.time()
        notes = [
            NoteEvent(time=0.0, duration=10.0, note_number=60, velocity=100, channel=0),
        ]
        seq.schedule_sequence(notes, start_time=now + 0.01)
        seq.process_timing(now + 0.05)

        fired_before = len(seq._fired)
        seq.clear()
        assert len(seq._fired) == fired_before  # No additional callbacks
        assert seq.total_count == 0


class TestQueries:
    def test_counts(self, seq):
        now = time.time()
        assert not seq.is_active
        assert seq.pending_count == 0
        assert seq.active_count == 0
        assert seq.total_count == 0

        evt = NoteEvent(time=0.0, duration=10.0, note_number=60, velocity=100, channel=0)
        seq.schedule(evt, start_time=now + 10.0)
        assert seq.is_active
        assert seq.pending_count == 1
        assert seq.active_count == 0
        assert seq.total_count == 1

    def test_active_count_after_fire(self, seq):
        now = time.time()
        evt = NoteEvent(time=0.0, duration=10.0, note_number=60, velocity=100, channel=0)
        seq.schedule(evt, start_time=now + 0.01)
        seq.process_timing(now + 0.05)

        assert seq.pending_count == 0
        assert seq.active_count == 1


class TestTempo:
    def test_faster_tempo_shorter_duration(self, seq):
        seq.set_tempo(240.0)  # Double speed → half duration
        assert seq.tempo == 240.0

        now = time.time()
        evt = NoteEvent(time=0.0, duration=1.0, note_number=60, velocity=100, channel=0)
        seq.schedule(evt, start_time=now + 0.01)

        seq.process_timing(now + 0.05)  # Note-on fires
        assert len(seq._fired) == 1

        # At 240 BPM, 1 beat = 0.25s. Note-off at now+0.01 + 0.25 = now+0.26
        seq.process_timing(now + 0.10)
        assert len(seq._fired) == 1  # Not yet

        seq.process_timing(now + 0.30)
        assert len(seq._fired) == 2

    def test_no_callbacks_graceful(self, seq):
        """Sequencer works without callbacks set."""
        s = NoteSequencer()
        now = time.time()
        evt = NoteEvent(time=0.0, duration=0.1, note_number=60, velocity=100, channel=0)
        s.schedule(evt, start_time=now + 0.01)
        s.process_timing(now + 0.05)  # Should not raise
        s.process_timing(now + 0.20)  # Should not raise
        assert s.total_count == 0
