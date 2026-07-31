"""
NoteSequencer — General-purpose note-level event scheduler.

Polls from the audio loop (no dedicated thread), fires note-on/note-off
events via callbacks when their scheduled wall-clock time arrives. Follows
the same integration pattern as the arpeggiator engines.

Design:
  - Min-heap of (trigger_time, seq_id) for O(log n) insert, O(1) peek.
  - Two heap entries per note: one for note-on, one for note-off.
  - _notes dict maps seq_id → SequencedNote for state lookup and cancellation.
  - Callbacks match the arpeggiator signature: (channel, note, velocity)
    for note_on and (channel, note) for note_off.
  - Thread-safe via reentrant lock.
"""

from __future__ import annotations

import heapq
import threading
from typing import Callable

from .sequencer_types import NoteEvent, NotePlayState, SequencedNote


class NoteSequencer:
    """Schedules and plays note events with per-note wall-clock timing.

    Call process_timing(current_time) from the audio loop at regular intervals
    (typically every ~1 ms or once per audio block). The sequencer fires
    note_on / note_off callbacks for any events whose scheduled time has
    arrived.

    Usage::

        seq = NoteSequencer(tempo=120.0)
        seq.note_on_callback = lambda ch, n, v: synth.note_on(ch, n, v)
        seq.note_off_callback = lambda ch, n: synth.note_off(ch, n)

        # Schedule a C major triad starting 0.5 s from now
        now = time.time()
        for note in [60, 64, 67]:
            evt = NoteEvent(time=0.0, duration=0.25, note_number=note,
                            velocity=100, channel=0)
            seq.schedule(evt, start_time=now + 0.5)

        # In the audio loop:
        seq.process_timing(time.time())
    """

    def __init__(self, tempo: float = 120.0) -> None:
        """Initialize the note sequencer.

        Args:
            tempo: Initial tempo in BPM.  Used to convert NoteEvent beat
                   times to wall-clock seconds when scheduling.
        """
        self.tempo = tempo

        # Min-heap: (trigger_time, seq_id)
        # Two entries per note — one for note-on, one for note-off.
        self._heap: list[tuple[float, int]] = []

        # All scheduled notes keyed by seq_id
        self._notes: dict[int, SequencedNote] = {}

        # Monotonic ID counter
        self._next_id: int = 0

        # Thread safety
        self.lock = threading.RLock()

        # Callbacks — match arpeggiator signature for consistency across the codebase
        #   note_on_callback(channel, note, velocity)
        #   note_off_callback(channel, note)
        self.note_on_callback: Callable[[int, int, int], None] | None = None
        self.note_off_callback: Callable[[int, int], None] | None = None

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule(
        self,
        event: NoteEvent,
        start_time: float | None = None,
    ) -> SequencedNote:
        """Schedule a single note event for playback.

        Args:
            event:   The note to schedule.  ``event.time`` is in beats
                     (quarter notes) and is converted to wall-clock
                     seconds using the current tempo.
                     ``event.duration`` (also in beats) determines the
                     note-off time.
            start_time: Absolute wall-clock time (``time.time()``) when
                        beat 0.0 begins.  ``None`` means now.

        Returns:
            SequencedNote wrapper that can be passed to :meth:`cancel`.
        """
        import time as _time

        if start_time is None:
            start_time = _time.time()

        beat_duration = 60.0 / max(self.tempo, 1.0)

        with self.lock:
            seq_id = self._next_id
            self._next_id += 1

            trigger_time = start_time + event.time * beat_duration
            note_off_beats = event.time + event.duration
            note_off_time = start_time + note_off_beats * beat_duration

            sn = SequencedNote(
                event=event,
                trigger_time=trigger_time,
                note_off_time=note_off_time,
                state=NotePlayState.PENDING,
                seq_id=seq_id,
            )
            self._notes[seq_id] = sn
            heapq.heappush(self._heap, (trigger_time, seq_id))

            return sn

    def schedule_sequence(
        self,
        events: list[NoteEvent],
        start_time: float | None = None,
    ) -> list[SequencedNote]:
        """Schedule multiple note events.

        Each ``NoteEvent.time`` is treated as relative to *start_time*.

        Args:
            events:     Note events to schedule.
            start_time: Absolute wall-clock time for beat 0.0.  ``None``
                        means now.

        Returns:
            List of SequencedNote wrappers (one per event).
        """
        import time as _time

        if start_time is None:
            start_time = _time.time()

        results: list[SequencedNote] = []
        with self.lock:
            for event in events:
                sn = self.schedule(event, start_time=start_time)
                results.append(sn)
        return results

    # ------------------------------------------------------------------
    # Timing poll — called from audio loop
    # ------------------------------------------------------------------

    def process_timing(self, current_time: float) -> None:
        """Fire note-on / note-off events whose scheduled time has arrived.

        Call this once per audio block or at ~1 ms intervals from the
        audio processing loop.

        Args:
            current_time: Current wall-clock time (``time.time()``).
        """
        with self.lock:
            self._process_heap(current_time)
            self._cleanup_released()

    def _process_heap(self, current_time: float) -> None:
        """Pop and dispatch all heap entries whose trigger_time <= current_time."""
        while self._heap and self._heap[0][0] <= current_time:
            trigger_time, seq_id = heapq.heappop(self._heap)
            sn = self._notes.get(seq_id)
            if sn is None:
                continue  # Already cleaned up

            if sn.state == NotePlayState.PENDING:
                # Fire note-on, transition to ACTIVE, schedule note-off
                self._fire_note_on(sn)
                sn.state = NotePlayState.ACTIVE
                if sn.note_off_time is not None:
                    heapq.heappush(self._heap, (sn.note_off_time, seq_id))

            elif sn.state == NotePlayState.ACTIVE:
                # Fire note-off, transition to RELEASED
                self._fire_note_off(sn)
                sn.state = NotePlayState.RELEASED

            elif sn.state == NotePlayState.CANCELLED:
                # Stale heap entry for a cancelled note — discard
                del self._notes[seq_id]

            # RELEASED entries stay in _notes until cleanup sweep

    def _cleanup_released(self) -> None:
        """Remove RELEASED entries from _notes."""
        released = [
            seq_id
            for seq_id, sn in self._notes.items()
            if sn.state == NotePlayState.RELEASED
        ]
        for seq_id in released:
            del self._notes[seq_id]

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel(self, note: SequencedNote) -> bool:
        """Cancel a scheduled note.

        - If PENDING:  marks it cancelled; stale heap entry is skipped
          when it eventually surfaces.
        - If ACTIVE:   fires note-off immediately, marks RELEASED.

        Args:
            note: The SequencedNote returned by :meth:`schedule`.

        Returns:
            True if the note was found and cancelled.
        """
        with self.lock:
            sn = self._notes.get(note.seq_id)
            if sn is None or sn.state in (NotePlayState.RELEASED, NotePlayState.CANCELLED):
                return False

            if sn.state == NotePlayState.ACTIVE:
                self._fire_note_off(sn)
                sn.state = NotePlayState.RELEASED
            else:
                sn.state = NotePlayState.CANCELLED

            return True

    def cancel_all(self) -> None:
        """Cancel all pending notes and stop active ones."""
        with self.lock:
            for sn in list(self._notes.values()):
                if sn.state == NotePlayState.ACTIVE:
                    self._fire_note_off(sn)
                sn.state = NotePlayState.CANCELLED
            self._notes.clear()
            self._heap.clear()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Send note-off for all active notes and clear the pending queue.

        Unlike :meth:`cancel_all`, this does a clean release — note-off
        callbacks fire for every active note so envelopes complete
        naturally.
        """
        with self.lock:
            for sn in list(self._notes.values()):
                if sn.state == NotePlayState.ACTIVE:
                    self._fire_note_off(sn)
                sn.state = NotePlayState.CANCELLED
            self._notes.clear()
            self._heap.clear()

    def clear(self) -> None:
        """Drop all scheduled notes without firing note-offs.

        Use this only for hard-reset scenarios (all-sound-off).
        """
        with self.lock:
            self._notes.clear()
            self._heap.clear()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True if any notes are pending or sounding."""
        with self.lock:
            return any(
                sn.state in (NotePlayState.PENDING, NotePlayState.ACTIVE)
                for sn in self._notes.values()
            )

    @property
    def pending_count(self) -> int:
        """Number of notes in PENDING state."""
        with self.lock:
            return sum(1 for sn in self._notes.values() if sn.state == NotePlayState.PENDING)

    @property
    def active_count(self) -> int:
        """Number of notes currently sounding (ACTIVE state)."""
        with self.lock:
            return sum(1 for sn in self._notes.values() if sn.state == NotePlayState.ACTIVE)

    @property
    def total_count(self) -> int:
        """Total number of notes tracked (all states)."""
        with self.lock:
            return len(self._notes)

    # ------------------------------------------------------------------
    # Tempo
    # ------------------------------------------------------------------

    def set_tempo(self, bpm: float) -> None:
        """Update tempo for future :meth:`schedule` calls.

        Does not retroactively adjust already-scheduled note times.
        """
        self.tempo = max(1.0, bpm)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fire_note_on(self, sn: SequencedNote) -> None:
        """Fire note-on callback for a SequencedNote."""
        if self.note_on_callback is not None:
            self.note_on_callback(
                sn.event.channel,
                sn.event.note_number,
                sn.event.velocity,
            )

    def _fire_note_off(self, sn: SequencedNote) -> None:
        """Fire note-off callback for a SequencedNote."""
        if self.note_off_callback is not None:
            self.note_off_callback(
                sn.event.channel,
                sn.event.note_number,
            )
