"""Shared per-channel acoustic context for cross-note behavior modeling.

This is the architectural foundation of the SuperNATURAL-Acoustic alike
engine. It owns ALL collective state that outlives individual voices:

- the set of currently-held notes (for register/phrase context)
- the shared sympathetic-resonance bus (fed by ALL active voices)
- ensemble/phrase state (section vs solo, roll/trill/held-chord detection)
- the detune-offset pool (inter-voice ensemble tuning)

A single ChannelAcousticContext is owned by a MIDI Channel (or MPE zone)
and is read by every AcousticBehaviorRegion on that channel every block,
and written to on every note-on/note-off event.
"""

from __future__ import annotations

import logging
import math
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any

from .behavior_config import BehaviorConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HeldNote:
    """A currently-sounding note tracked by the context."""

    note: int
    velocity: int
    voice_id: int
    start_time: float
    is_sustained: bool = False


@dataclass(slots=True)
class PhraseState:
    """Derived phrasing flags computed from recent note history."""

    is_first_of_chord: bool = True
    is_held_chord: bool = False
    is_roll: bool = False
    is_trill: bool = False
    held_count: int = 0
    register_centroid: float = 60.0


class ChannelAcousticContext:
    """Owns collective acoustic state for one MIDI channel / MPE zone.

    Thread-safety: in this architecture MIDI events are serialized into the
    render loop, so the audio thread is the sole mutator during rendering.
    If events arrive from another thread, guard mutations with the lock.
    """

    def __init__(
        self,
        sample_rate: int,
        channel_number: int = 0,
        config: BehaviorConfig | None = None,
        buffer_pool: Any | None = None,
    ):
        self.sample_rate = sample_rate
        self.channel_number = channel_number
        self.config = config or BehaviorConfig()
        self.buffer_pool = buffer_pool
        self._lock = threading.Lock()

        # --- Held notes (cross-note context) ---
        # Keyed by voice_id so two voices on the same note are both tracked.
        self.held_notes: dict[int, HeldNote] = {}  # voice_id -> HeldNote
        self._note_to_voice_ids: dict[int, list[int]] = {}  # note -> [voice_id]

        # --- Phrase / density detection ---
        self._recent_note_ons: deque[tuple[float, int]] = deque(maxlen=16)
        self.last_note_on_time: float = -1.0
        self._note_on_counter: int = 0
        self.phrase = PhraseState()

        # --- Ensemble detune pool ---
        self._detune_pool: list[float] = []
        self._claimed_offsets: dict[int, float] = {}  # voice_id -> cents
        self._vibrato_phase: float = 0.0

        # --- Shared resonance bus (lazy; created on first use) ---
        self._resonance_bank: Any | None = None
        self._damper: Any | None = None

        # --- Continuous controller mirror (for cross-note reads) ---
        self.sustain_pedal: bool = False
        self.resonance_amount: float = 1.0  # CC71
        self.expression: float = 1.0  # CC11
        self.global_brightness: float = 0.5  # derived

    # ------------------------------------------------------------------
    # Note lifecycle (called on every MIDI event, not just per block)
    # ------------------------------------------------------------------
    def note_on(self, note: int, velocity: int, voice_id: int, time: float) -> None:
        """Register a note-on. Order: callers must process note-off before
        note-on on the same tick."""
        with self._lock:
            self._note_on_counter += 1
            self._recent_note_ons.append((time, note))
            self.last_note_on_time = time
            held = HeldNote(note=note, velocity=velocity, voice_id=voice_id, start_time=time)
            self.held_notes[voice_id] = held
            self._note_to_voice_ids.setdefault(note, []).append(voice_id)
            self._recompute_phrase()

    def note_off(self, note: int, voice_id: int, time: float) -> None:
        with self._lock:
            self.held_notes.pop(voice_id, None)
            ids = self._note_to_voice_ids.get(note, [])
            if voice_id in ids:
                ids.remove(voice_id)
                if not ids:
                    self._note_to_voice_ids.pop(note, None)
            self._recompute_phrase()

    def set_sustained(self, note: int, sustained: bool) -> None:
        with self._lock:
            for vid in self._note_to_voice_ids.get(note, []):
                if vid in self.held_notes:
                    self.held_notes[vid].is_sustained = sustained

    def update_controller(self, name: str, value: float) -> None:
        """Update a continuous controller mirror used by cross-note logic."""
        with self._lock:
            if name == "sustain":
                self.sustain_pedal = bool(value >= 0.5)
            elif name == "resonance":
                self.resonance_amount = float(value)
            elif name == "expression":
                self.expression = float(value)

    # ------------------------------------------------------------------
    # Phrase / register derivation
    # ------------------------------------------------------------------
    def _recompute_phrase(self) -> None:
        held = list(self.held_notes.values())
        n = len(held)
        self.phrase.held_count = n
        self.phrase.is_held_chord = n >= 3
        if n > 0:
            centroid = sum(h.note for h in held) / n
            self.phrase.register_centroid = centroid
        # Roll/trill: >=3 note-ons within 250 ms on near-repeat
        recent = [(t, nt) for (t, nt) in self._recent_note_ons if self.last_note_on_time - t < 0.25]
        self.phrase.is_roll = len(recent) >= 3
        if len(recent) >= 2:
            notes = [nt for _, nt in recent]
            self.phrase.is_trill = all(
                abs(notes[i] - notes[i - 1]) <= 2 for i in range(1, len(notes))
            )
        else:
            self.phrase.is_trill = False

    def get_phrase_state(self) -> PhraseState:
        with self._lock:
            return self.phrase

    # ------------------------------------------------------------------
    # Ensemble detune pool
    # ------------------------------------------------------------------
    def claim_detune_offset(self, voice_id: int) -> float:
        with self._lock:
            if voice_id in self._claimed_offsets:
                return self._claimed_offsets[voice_id]
            n = self.phrase.held_count
            spread = self.config.ensemble.detune_spread_cents
            # Deterministic spread based on held count + voice id
            if n <= 1 or not self.config.ensemble.shared_vibrato:
                offset = 0.0
            else:
                idx = len(self._claimed_offsets)
                offset = spread * (2.0 * ((idx % n) / max(1, n - 1)) - 1.0)
            self._claimed_offsets[voice_id] = offset
            return offset

    def release_detune_offset(self, voice_id: int) -> None:
        with self._lock:
            self._claimed_offsets.pop(voice_id, None)

    def advance_vibrato(self, rate_hz: float, block_size: int) -> None:
        """Advance the shared vibrato phase so section voices stay in phase."""
        with self._lock:
            self._vibrato_phase += 2.0 * math.pi * rate_hz * block_size / self.sample_rate
            if self._vibrato_phase > 2.0 * math.pi:
                self._vibrato_phase -= 2.0 * math.pi * math.pi

    def shared_vibrato_phase(self) -> float:
        with self._lock:
            return self._vibrato_phase

    # ------------------------------------------------------------------
    # Shared resonance bus (Layer B flagship)
    # ------------------------------------------------------------------
    def get_resonance_bank(self) -> Any:
        """Lazily create the shared sympathetic-resonance bank."""
        if self._resonance_bank is None:
            from .processors.sympathetic_resonance import SympatheticResonanceBank

            self._resonance_bank = SympatheticResonanceBank(
                sample_rate=self.sample_rate,
                loop_gain=self.config.resonance_loop_gain,
                coupling=self.config.resonance_coupling,
            )
        return self._resonance_bank

    def get_damper(self) -> Any:
        if self._damper is None:
            from .processors.damper_resonance import DamperResonance

            self._damper = DamperResonance(sample_rate=self.sample_rate)
        return self._damper

    # ------------------------------------------------------------------
    # Serialization (JSON, no pickle)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        with self._lock:
            return {
                "channel_number": self.channel_number,
                "config": self.config.to_dict(),
                "sustain_pedal": self.sustain_pedal,
                "resonance_amount": self.resonance_amount,
                "expression": self.expression,
                "held_notes": [asdict(h) for h in self.held_notes.values()],
            }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], sample_rate: int, buffer_pool: Any | None = None
    ) -> ChannelAcousticContext:
        cfg = BehaviorConfig.from_dict(data.get("config", {}))
        ctx = cls(
            sample_rate=sample_rate,
            channel_number=data.get("channel_number", 0),
            config=cfg,
            buffer_pool=buffer_pool,
        )
        ctx.sustain_pedal = data.get("sustain_pedal", False)
        ctx.resonance_amount = data.get("resonance_amount", 1.0)
        ctx.expression = data.get("expression", 1.0)
        # Restore held notes (keyed by voice_id) for state continuity.
        for h in data.get("held_notes", []):
            voice_id = h.get("voice_id", 0)
            note = h.get("note", 60)
            held = HeldNote(
                note=note,
                velocity=h.get("velocity", 0),
                voice_id=voice_id,
                start_time=h.get("start_time", 0.0),
                is_sustained=h.get("is_sustained", False),
            )
            ctx.held_notes[voice_id] = held
            ctx._note_to_voice_ids.setdefault(note, []).append(voice_id)
        ctx._recompute_phrase()
        return ctx
