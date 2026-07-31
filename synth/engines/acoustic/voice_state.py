"""Per-voice behavior state machine for the acoustic behavior layer.

Mirrors the FluidSynth voice status pattern (CLEAN/ON/SUSTAINED/HELD/OFF)
and adds a classifier that decides single-note articulation from the
SHARED ChannelAcousticContext (register, held-count, phrase flags) rather
than per-voice-only state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .behavior_config import InstrumentGroup

# ── Interval glissando thresholds (semitones) per instrument group ──
LEGATO_GLISSANDO_THRESHOLD: dict[InstrumentGroup, int] = {
    InstrumentGroup.ACOUSTIC_PIANO: 12,
    InstrumentGroup.ELECTRIC_PIANO: 12,
    InstrumentGroup.ORGAN: 12,
    InstrumentGroup.ACOUSTIC_GUITAR: 5,
    InstrumentGroup.ELECTRIC_GUITAR: 5,
    InstrumentGroup.ACOUSTIC_BASS: 5,
    InstrumentGroup.ELECTRIC_BASS: 5,
    InstrumentGroup.BOWED_STRINGS: 3,
    InstrumentGroup.MALLETS: 12,
    InstrumentGroup.TIMPANI: 12,
    InstrumentGroup.BRASS: 7,
    InstrumentGroup.REEDS_WOODWINDS: 10,
    InstrumentGroup.ETHNIC: 7,
    InstrumentGroup.PLUCKED_WORLD: 5,
    InstrumentGroup.ACCORDION: 7,
    InstrumentGroup.CHOIR: 7,
    InstrumentGroup.HARP: 12,
    InstrumentGroup.FREE_REED: 7,
}

# Duration thresholds for release variants
STACCATO_RELEASE_THRESHOLD: float = 0.08
LONG_RELEASE_THRESHOLD: float = 1.0


class VoicePhase(StrEnum):
    """Voice lifecycle phases for behavior modeling."""

    ATTACK = "attack"
    SUSTAIN = "sustain"
    LEGATO = "legato"
    RELEASE = "release"
    OFF = "off"


@dataclass(slots=True)
class VoiceBehaviorState:
    """Per-voice behavior state, informed by shared context at note-on."""

    voice_id: int
    note: int
    velocity: int
    phase: VoicePhase = VoicePhase.ATTACK
    start_time: float = 0.0

    # Derived at note-on from ChannelAcousticContext
    is_first_of_chord: bool = True
    is_held_chord: bool = False
    is_roll: bool = False
    is_trill: bool = False
    register_centroid: float = 60.0
    detune_offset_cents: float = 0.0

    # Articulation selection
    articulation: str = "normal"
    attack_skip: bool = False  # legato: skip re-attack

    def classify(
        self,
        context_phrase: Any,
        detune_offset: float = 0.0,
        legato: bool = True,
        prev_note: int | None = None,
        instrument_group: InstrumentGroup | None = None,
        held_note_pitches: list[int] | None = None,
    ) -> None:
        """Populate derived fields from the shared context at note-on.

        Detection order (first match wins):
        1. Interval glissando — wide legato interval → articulation = glissando
        2. Legato — any held notes → attack_skip = True, phase = LEGATO
        3. Single note — attack_skip = False, phase = ATTACK

        Args:
            context_phrase: PhraseState from ChannelAcousticContext.
            detune_offset: Ensemble detune offset in cents.
            legato: Whether legato detection is enabled.
            prev_note: Previous note (for interval calculation).
            instrument_group: Instrument group for threshold selection.
            held_note_pitches: Currently held note pitches for interval check.
        """
        self.is_first_of_chord = context_phrase.is_first_of_chord
        self.is_held_chord = context_phrase.is_held_chord
        self.is_roll = context_phrase.is_roll
        self.is_trill = context_phrase.is_trill
        self.register_centroid = context_phrase.register_centroid
        self.detune_offset_cents = detune_offset

        has_held = context_phrase.held_count > 1 and prev_note is not None

        if not has_held:
            self.attack_skip = False
            self.phase = VoicePhase.ATTACK
            return

        # 1. Interval-based glissando: wide legato interval → glissando
        if _should_trigger_glissando(
            self.note, held_note_pitches, instrument_group=instrument_group
        ):
            self.articulation = "glissando"
            self.attack_skip = True
            self.phase = VoicePhase.LEGATO
            return

        # 2. Legato: overlapping notes with close interval → skip attack
        if legato:
            self.attack_skip = True
            self.phase = VoicePhase.LEGATO
        else:
            self.attack_skip = False
            self.phase = VoicePhase.ATTACK

        # Track start time for duration-based release detection
        self.start_time = time.monotonic()

    def note_off(self) -> None:
        """Transition to release phase and compute release variant."""
        self.phase = VoicePhase.RELEASE

    def get_release_variant(self) -> str | None:
        """Return release variant based on note duration.

        Returns:
            "staccato_release" if note was held < 80ms,
            "long_release" if note was held > 1s,
            None for normal release.
        """
        if self.start_time <= 0.0:
            return None
        duration = time.monotonic() - self.start_time
        if duration < STACCATO_RELEASE_THRESHOLD:
            return "staccato_release"
        if duration > LONG_RELEASE_THRESHOLD:
            return "long_release"
        return None


def _should_trigger_glissando(
    note: int,
    held_pitches: list[int] | None,
    instrument_group: InstrumentGroup | None = None,
) -> bool:
    """Check if a glissando should be triggered based on interval size."""
    if held_pitches is None or instrument_group is None:
        return False
    threshold = LEGATO_GLISSANDO_THRESHOLD.get(instrument_group, 7)
    for held in held_pitches:
        if abs(note - held) >= threshold:
            return True
    return False

    def is_active(self) -> bool:
        return self.phase not in (VoicePhase.OFF,)
