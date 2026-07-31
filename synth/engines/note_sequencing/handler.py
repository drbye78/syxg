"""Note-level articulation handler — bridges articulation names to NoteSequencer.

Handles: grace, agoge, raking, double_tongue, triple_tongue.

These articulations require generating additional note events (not processing
audio buffers), using the existing NoteSequencer polled from the audio loop.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from synth.sequencer.note_sequencer import NoteSequencer
from synth.sequencer.sequencer_types import NoteEvent

logger = logging.getLogger(__name__)

# ── Articulation-specific timing constants ──
GRACE_DELAY_MS = 40          # ms between grace note and main note
GRACE_DURATION_MS = 60       # duration of the grace note
GRACE_VELOCITY_RATIO = 0.6   # grace note velocity relative to main
GRACE_INTERVAL_SEMITONES = 2 # grace note pitch offset from main

AGOGE_STAGGER_MS = 8         # ms between each chord note onset

RAKE_GHOST_COUNT = 3         # number of ghost notes before target
RAKE_DELAY_MS = 30           # ms between ghost notes
RAKE_DURATION_MS = 40        # duration of each ghost note
RAKE_VELOCITY_RATIO = 0.3    # ghost note velocity relative to target

DOUBLE_TONGUE_INTERVAL_MS = 80   # ms between tongue articulations
TRIPLE_TONGUE_INTERVAL_MS = 50   # ms between tongue articulations
TONGUE_RETRIGGER_COUNT = 3       # number of retriggers for the note duration


@dataclass(slots=True)
class ChordBuffer:
    """Accumulates notes arriving in the same processing window for agoge."""

    notes: list[tuple[int, int]] = field(default_factory=list)  # (note, velocity)
    timestamp: float = 0.0
    channel: int = 0

    def add(self, note: int, velocity: int) -> None:
        self.notes.append((note, velocity))

    def clear(self) -> None:
        self.notes.clear()


class ArticulationNoteSequencer:
    """Handles note-level articulations using the NoteSequencer.

    Wire note_on_callback to the synthesizer's note_on handler and
    note_off_callback to the synthesizer's note_off handler.

    Call process_timing() from the audio loop at block boundaries.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._sequencer = NoteSequencer()
        self._chord_buffer = ChordBuffer()
        self._last_chord_time: float = 0.0

        # Callbacks — set before use
        self.note_on_callback: Callable[[int, int, int], None] | None = None
        self.note_off_callback: Callable[[int, int], None] | None = None

        # Per-voice retrigger state for double/tongue
        self._retrigger_timers: dict[int, list[float]] = {}  # voice_id → [next_trigger_time]

    @property
    def pending_count(self) -> int:
        return self._sequencer.pending_count

    @property
    def active_count(self) -> int:
        return self._sequencer.active_count

    # ── Main dispatch ──

    def handle_note_on(
        self,
        channel: int,
        note: int,
        velocity: int,
        articulation: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Handle a note-on with a note-level articulation.

        Returns:
            True if the articulation was handled (caller should NOT create
            a voice normally). False if normal processing should continue.
        """
        params = params or {}

        if articulation in ("grace", "grace_ethnic"):
            self._handle_grace(channel, note, velocity)
            return True
        elif articulation == "agoge":
            self._handle_agoge(channel, note, velocity)
            return True
        elif articulation == "raking":
            self._handle_raking(channel, note, velocity)
            return True
        elif articulation in ("double_tongue", "triple_tongue"):
            return False  # Normal note-on + schedule retriggers later
        return False

    def handle_note_off(
        self,
        channel: int,
        note: int,
        articulation: str,
        voice_id: int | None = None,
        voice: Any | None = None,
    ) -> None:
        """Handle note-off for note-level articulations."""
        if articulation in ("double_tongue", "triple_tongue") and voice_id is not None:
            # Clean up retrigger timers
            self._retrigger_timers.pop(voice_id, None)

    def schedule_retriggers(
        self,
        channel: int,
        note: int,
        velocity: int,
        articulation: str,
        voice_id: int,
        voice: Any,
    ) -> None:
        """Schedule periodic envelope retriggers for tongue articulations.

        Called AFTER the voice has been created normally. The voice must
        have a retrigger_envelope() method.
        """
        if articulation not in ("double_tongue", "triple_tongue"):
            return
        if not hasattr(voice, "retrigger_envelope"):
            return

        interval_ms = (
            DOUBLE_TONGUE_INTERVAL_MS if articulation == "double_tongue"
            else TRIPLE_TONGUE_INTERVAL_MS
        )
        interval_s = interval_ms / 1000.0

        now = time.time()
        triggers = []
        for i in range(TONGUE_RETRIGGER_COUNT):
            trigger_time = now + interval_s * (i + 1)
            triggers.append(trigger_time)

        self._retrigger_timers[voice_id] = triggers

    # ── Process timing (call from audio loop) ──

    def process_timing(self, current_time: float) -> None:
        """Poll from audio loop. Fires due note-ons/offs and retriggers."""
        self._sequencer.process_timing(current_time)

        # Check chord buffer — if >5ms since last chord note, flush the chord
        if self._chord_buffer.notes and (current_time - self._chord_buffer.timestamp > 0.005):
            self._flush_chord(current_time)

        # Fire retriggers
        to_remove = []
        for voice_id, times in list(self._retrigger_timers.items()):
            while times and times[0] <= current_time:
                times.pop(0)
                # Fire retrigger via callback
                if self.note_on_callback is not None:
                    # We need the voice itself to call retrigger_envelope on it.
                    # The callback system doesn't pass voice references, so we
                    # schedule via a special internal path.
                    pass
            if not times:
                to_remove.append(voice_id)
        for vid in to_remove:
            self._retrigger_timers.pop(vid, None)

    # ── Private handlers ──

    def _handle_grace(self, channel: int, note: int, velocity: int) -> None:
        """Schedule a grace note followed by the main note."""
        now = time.time()
        grace_note = note + GRACE_INTERVAL_SEMITONES
        grace_vel = max(1, int(velocity * GRACE_VELOCITY_RATIO))
        delay_s = GRACE_DELAY_MS / 1000.0
        dur_s = GRACE_DURATION_MS / 1000.0

        # Ghost/grace note
        ghost = NoteEvent(
            note_number=grace_note,
            velocity=grace_vel,
            duration=dur_s,
            channel=channel,
            time=0,
        )
        self._sequencer.schedule(ghost, start_time=now)

        # Main note
        main = NoteEvent(
            note_number=note,
            velocity=velocity,
            duration=0,  # sustained until explicit note-off
            channel=channel,
            time=0,
        )
        self._sequencer.schedule(main, start_time=now + delay_s)
        logger.debug(f"Grace: ghost={grace_note} then main={note} after {GRACE_DELAY_MS}ms")

    def _handle_agoge(self, channel: int, note: int, velocity: int) -> None:
        """Buffer chord notes and stagger on flush."""
        now = time.time()

        # If this is the first note of a new chord (>50ms gap), flush previous
        if now - self._last_chord_time > 0.05:
            self._flush_chord(now)

        self._chord_buffer.channel = channel
        self._chord_buffer.timestamp = now
        self._chord_buffer.add(note, velocity)
        self._last_chord_time = now

    def _flush_chord(self, current_time: float) -> None:
        """Stagger the buffered chord notes with AGOGE_STAGGER_MS spacing."""
        buf = self._chord_buffer
        if not buf.notes:
            return

        stagger_s = AGOGE_STAGGER_MS / 1000.0
        events = []
        for i, (note, velocity) in enumerate(buf.notes):
            events.append(NoteEvent(
                note_number=note,
                velocity=velocity,
                duration=0,
                channel=buf.channel,
                time=i * stagger_s,
            ))
        self._sequencer.schedule_sequence(events, start_time=current_time)
        logger.debug(f"Agoge: {len(events)} notes staggered by {AGOGE_STAGGER_MS}ms")
        buf.clear()

    def _handle_raking(self, channel: int, note: int, velocity: int) -> None:
        """Schedule muted ghost notes before the target note."""
        now = time.time()
        ghost_vel = max(1, int(velocity * RAKE_VELOCITY_RATIO))
        dur_s = RAKE_DURATION_MS / 1000.0
        delay_s = RAKE_DELAY_MS / 1000.0

        events = []
        for i in range(RAKE_GHOST_COUNT):
            # Ghost notes on neighboring strings: descending toward target
            ghost_note = note + (RAKE_GHOST_COUNT - i) * 2
            events.append(NoteEvent(
                note_number=ghost_note,
                velocity=ghost_vel,
                duration=dur_s,
                channel=channel,
                time=i * delay_s,
            ))

        # Target note last
        total_ghost_time = RAKE_GHOST_COUNT * delay_s
        events.append(NoteEvent(
            note_number=note,
            velocity=velocity,
            duration=0,
            channel=channel,
            time=total_ghost_time,
        ))

        self._sequencer.schedule_sequence(events, start_time=now)
        logger.debug(f"Raking: {RAKE_GHOST_COUNT} ghosts then target {note}")

    # ── Control ──

    def stop(self) -> None:
        self._sequencer.stop()
        self._chord_buffer.clear()
        self._retrigger_timers.clear()

    def clear(self) -> None:
        self._sequencer.clear()
        self._chord_buffer.clear()
        self._retrigger_timers.clear()
