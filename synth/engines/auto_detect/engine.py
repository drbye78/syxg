"""Auto-detection engine for S.Art2 playing-style inference.

Detects playing style from performance context (note overlap, intervals,
velocity, duration) and returns articulation overrides without requiring
explicit articulation commands.

Integrates with VoiceManager.note_on() / note_off() to modify voice
creation parameters before the articulation pipeline runs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from synth.engines.acoustic.behavior_config import InstrumentGroup

logger = logging.getLogger(__name__)

# ── Interval thresholds per instrument group (semitones) ──
# Above this threshold, overlapping notes trigger glissando instead of legato.
LEGATO_GLISSANDO_THRESHOLD: dict[InstrumentGroup, int] = {
    InstrumentGroup.ACOUSTIC_PIANO: 12,  # octave
    InstrumentGroup.ELECTRIC_PIANO: 12,
    InstrumentGroup.ORGAN: 12,
    InstrumentGroup.ACOUSTIC_GUITAR: 5,  # perfect fourth
    InstrumentGroup.ELECTRIC_GUITAR: 5,
    InstrumentGroup.ACOUSTIC_BASS: 5,
    InstrumentGroup.ELECTRIC_BASS: 5,
    InstrumentGroup.BOWED_STRINGS: 3,  # minor third
    InstrumentGroup.MALLETS: 12,
    InstrumentGroup.TIMPANI: 12,
    InstrumentGroup.BRASS: 7,  # perfect fifth
    InstrumentGroup.REEDS_WOODWINDS: 10,  # minor seventh
    InstrumentGroup.ETHNIC: 7,
    InstrumentGroup.PLUCKED_WORLD: 5,
    InstrumentGroup.ACCORDION: 7,
    InstrumentGroup.CHOIR: 7,
    InstrumentGroup.HARP: 12,
    InstrumentGroup.FREE_REED: 7,
}

# ── Duration thresholds (seconds) for release variants ──
STACCATO_RELEASE_THRESHOLD = 0.08  # < 80ms → staccato release
LONG_RELEASE_THRESHOLD = 1.0  # > 1s → extended release


@dataclass(slots=True)
class DetectionResult:
    """Result of auto-detection for a single note event."""

    articulation: str | None = None
    attack_skip: bool = False
    release_variant: str | None = None
    repetition_count: int = 0       # How many times this note was repeated
    phrase_trend: float = 0.0       # -1.0 (decresc) to 1.0 (cresc)
    is_sforzando: bool = False      # Hard attack with expected rapid damping


class AutoDetectionEngine:
    """Detects articulation intent from playing style context.

    Call on_note_on() before voice creation and on_note_off() before
    release processing. Results are merged with the channel's current
    articulation state.

    The engine is stateless — all state is read from the channel's
    acoustic context and voice behavior state.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize auto-detection engine."""
        self.sample_rate = sample_rate
        # Expressive gesture state (per-channel, set externally)
        self._last_velocity: int = 64
        self._velocity_ema: float = 64.0  # Exponential moving average for crescendo
        self._last_note: int = 60
        self._last_note_time: float = 0.0
        self._note_history: list[tuple[int, int, float]] = []  # (note, velocity, time)

    def on_note_on(
        self,
        note: int,
        velocity: int,
        instrument_group: InstrumentGroup,
        held_notes: list[int],
        active_preset: Any | None = None,
    ) -> DetectionResult:
        """Analyze a note-on event and return articulation overrides.

        Detection order (first match wins):
        1. Sforzando — velocity > 110 with sudden drop expected
        2. Interval glissando — wide legato interval → glissando
        3. Legato — any held notes → skip attack
        4. Repetition — same note within 500ms
        5. Velocity switch — velocity matches preset split
        6. Crescendo/Decrescendo — velocity trend over phrase
        """
        result = DetectionResult()

        # 1. Interval-based glissando
        if held_notes:
            threshold = LEGATO_GLISSANDO_THRESHOLD.get(instrument_group, 7)
            for held_note in held_notes:
                if abs(note - held_note) >= threshold:
                    result.articulation = "glissando"
                    logger.debug(
                        f"Auto-detect glissando: note={note} held={held_note} "
                        f"interval={abs(note - held_note)} threshold={threshold}"
                    )
                    return result

        # 2. Legato detection (note overlap → skip attack)
        if held_notes:
            result.attack_skip = True
            logger.debug(f"Auto-detect legato: note={note} held_count={len(held_notes)}")

        # 3. Velocity-switched articulation (from channel preset)
        if active_preset and hasattr(active_preset, "velocity_splits"):
            for split in active_preset.velocity_splits:
                art = split.get_articulation(velocity)
                if art and art != "normal":
                    result.articulation = art
                    logger.debug(
                        f"Auto-detect velocity switch: vel={velocity} → {art}"
                    )
                    break

        # 4. Sforzando detection: velocity > 110 → hard attack, expect rapid damping
        if velocity > 110:
            result.articulation = "sforzando"
            result.is_sforzando = True
            logger.debug(f"Auto-detect sforzando: vel={velocity}")

        # 5. Repetition detection: same note within 500ms → reduced attack
        import time
        now = time.monotonic()
        if self._note_history:
            same_note_hits = sum(1 for n, v, t in self._note_history[-4:]
                                 if n == note and now - t < 0.5)
            if same_note_hits > 0:
                result.repetition_count = same_note_hits + 1
                logger.debug(f"Auto-detect repetition: count={result.repetition_count}")

        # Update phrase tracking (crescendo/decrescendo)
        self._velocity_ema = 0.7 * self._velocity_ema + 0.3 * velocity
        self._last_velocity = velocity
        self._last_note = note
        self._last_note_time = now
        self._note_history.append((note, velocity, now))
        if len(self._note_history) > 8:
            self._note_history.pop(0)

        # Track phrase velocity trend for crescendo/decrescendo detection
        if velocity - self._velocity_ema > 15:  # Rising
            result.phrase_trend = 1.0  # Crescendo
        elif self._velocity_ema - velocity > 15:  # Falling
            result.phrase_trend = -1.0  # Decrescendo
        else:
            result.phrase_trend = 0.0

        return result

    def on_note_off(
        self,
        voice_note: int,
        voice_start_time: float | None = None,
    ) -> DetectionResult:
        """Analyze a note-off event and return release overrides.

        Called by VoiceManager before processing note-off for a voice.

        Args:
            voice_note: MIDI note number.
            voice_start_time: Time the note was started (from time.monotonic()).
                             If None, no duration-based detection is performed.

        Returns:
            DetectionResult (only release_variant is populated).
        """
        result = DetectionResult()

        # Duration-based release
        if voice_start_time is not None:
            duration = time.monotonic() - voice_start_time
            if duration < STACCATO_RELEASE_THRESHOLD:
                result.release_variant = "staccato_release"
                logger.debug(
                    f"Auto-detect staccato release: duration={duration:.3f}s"
                )
            elif duration > LONG_RELEASE_THRESHOLD:
                result.release_variant = "long_release"
                logger.debug(
                    f"Auto-detect long release: duration={duration:.3f}s"
                )

        return result
