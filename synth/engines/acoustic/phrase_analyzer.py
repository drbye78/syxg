"""Phrase-level analysis — musical structure detection over multiple notes.

Analyzes multi-note phrases for musical intent: apex anticipation,
rubato timing, phrase boundary detection, dynamic contour tracking.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class PhraseContext:
    """Performance modifiers derived from phrase analysis."""

    timing_anticipation: float = 0.0    # Play slightly ahead (seconds)
    timing_relaxation: float = 0.0      # Hold slightly longer (seconds)
    velocity_boost: float = 0.0         # Relative velocity increase (0-1)
    decay_boost: float = 0.0            # Relative decay rate increase (0-1)
    attack_soften: float = 0.0          # Relative attack softening (0-1)
    is_phrase_start: bool = False       # First note of a new phrase
    is_phrase_end: bool = False         # Last note of a phrase (should ritardando)
    phrase_position: float = 0.5        # 0.0=start, 1.0=end of current phrase
    dynamic_contour: float = 0.0        # -1.0 (decrescendo) to 1.0 (crescendo)


class PhraseAnalyzer:
    """Analyze multi-note phrases for musical structure.

    Tracks note history, detects phrase boundaries (>500ms gap),
    identifies apex points in dynamic contour, and produces
    performance modifiers for the behavioral voice.

    Usage:
        analyzer = PhraseAnalyzer()
        ctx = analyzer.note_on(60, 100, time.monotonic())
        if ctx.is_phrase_start:
            voice.start_phrase()
    """

    def __init__(self, phrase_gap_threshold: float = 0.5):
        self.phrase_gap_threshold = phrase_gap_threshold
        self._history: deque[tuple[int, int, float]] = deque(maxlen=32)
        self._phrase_velocities: list[float] = []
        self._phrase_start_indices: list[int] = []
        self._velocity_ema: float = 64.0

    def note_on(self, note: int, velocity: int, now: float) -> PhraseContext:
        """Analyze a new note in phrase context. Returns performance modifiers."""
        ctx = PhraseContext()

        # Phrase boundary detection: gap > threshold → new phrase
        is_new_phrase = (
            not self._history or now - self._history[-1][2] > self.phrase_gap_threshold
        )
        if is_new_phrase:
            if self._phrase_velocities:
                self._phrase_start_indices.append(len(self._history))
            self._phrase_velocities = []
            ctx.is_phrase_start = True

        self._history.append((note, velocity, now))
        self._phrase_velocities.append(velocity)
        self._velocity_ema = 0.7 * self._velocity_ema + 0.3 * velocity

        # Phrase position (0.0=start, 1.0=end)
        phrase_len = len(self._phrase_velocities)
        ctx.phrase_position = phrase_len / max(phrase_len + 1, 1)

        # Dynamic contour (EMA of velocity trend within current phrase)
        ctx.dynamic_contour = self._compute_dynamic_contour()

        # Apex anticipation: rising velocity mid-phrase → play slightly ahead
        if ctx.dynamic_contour > 0.15 and 0.3 < ctx.phrase_position < 0.8:
            ctx.timing_anticipation = 0.015
            ctx.velocity_boost = 0.04

        # Post-apex decay: falling velocity → softer attack, longer decay
        if ctx.dynamic_contour < -0.1:
            ctx.timing_relaxation = 0.02
            ctx.attack_soften = 0.1
            ctx.decay_boost = 0.08

        # First note of phrase: slightly held (espressivo)
        if ctx.is_phrase_start and phrase_len == 1:
            ctx.timing_relaxation = 0.01

        return ctx

    def note_off(self, note: int, now: float) -> PhraseContext:
        """Analyze a note-off in phrase context."""
        ctx = PhraseContext()
        # If this was the last held note and gap will exceed threshold,
        # mark as phrase end for ritardando on next note
        return ctx

    def _compute_dynamic_contour(self) -> float:
        """Compute dynamic contour (-1=decrescendo, 1=crescendo) within current phrase."""
        if len(self._phrase_velocities) < 3:
            return 0.0
        recent = self._phrase_velocities[-4:]
        if len(recent) < 2:
            return 0.0
        # Linear trend of last 4 velocities
        x = np.arange(len(recent), dtype=np.float64)
        slope = np.polyfit(x, recent, 1)[0]
        return float(np.clip(slope / 30.0, -1.0, 1.0))

    def get_phrase_count(self) -> int:
        """Return number of completed phrases."""
        return len(self._phrase_start_indices)

    def reset(self) -> None:
        self._history.clear()
        self._phrase_velocities.clear()
        self._phrase_start_indices.clear()
        self._velocity_ema = 64.0
