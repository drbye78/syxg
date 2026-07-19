"""Per-voice behavior state machine for the acoustic behavior layer.

Mirrors the FluidSynth voice status pattern (CLEAN/ON/SUSTAINED/HELD/OFF)
and adds a classifier that decides single-note articulation from the
SHARED ChannelAcousticContext (register, held-count, phrase flags) rather
than per-voice-only state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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
    ) -> None:
        """Populate derived fields from the shared context at note-on."""
        self.is_first_of_chord = context_phrase.is_first_of_chord
        self.is_held_chord = context_phrase.is_held_chord
        self.is_roll = context_phrase.is_roll
        self.is_trill = context_phrase.is_trill
        self.register_centroid = context_phrase.register_centroid
        self.detune_offset_cents = detune_offset

        # Legato detection: overlapping note while others held -> skip attack
        if legato and context_phrase.held_count > 1 and prev_note is not None:
            self.attack_skip = True
            self.phase = VoicePhase.LEGATO
        else:
            self.attack_skip = False
            self.phase = VoicePhase.ATTACK

    def note_off(self) -> None:
        self.phase = VoicePhase.RELEASE

    def is_active(self) -> bool:
        return self.phase not in (VoicePhase.OFF,)
