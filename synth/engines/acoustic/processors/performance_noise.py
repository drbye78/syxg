"""[A] Performance noise: key-off click, hammer/breath, fret/string noise.

Adds the small transient/noise textures that make a sampled instrument
sound physically played rather than looped. Group-dependent: pianos get
hammer + key-off, winds get breath, strings get bow/fret noise.
"""

from __future__ import annotations

import logging

import numpy as np

from ..behavior_config import InstrumentGroup
from ..voice_state import VoiceBehaviorState

logger = logging.getLogger(__name__)


class PerformanceNoiseProcessor:
    """Adds group-appropriate performance noise textures."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._noise_idx = 0
        self._white = np.random.normal(0, 1, 2048).astype(np.float32)
        self._breath_state = 0.0

    def _noise(self, n: int) -> np.ndarray:
        out = np.empty(n, dtype=np.float32)
        for i in range(n):
            out[i] = self._white[self._noise_idx]
            self._noise_idx = (self._noise_idx + 1) % len(self._white)
        return out

    def process(
        self,
        buf: np.ndarray,
        state: VoiceBehaviorState,
        modulation: dict[str, float],
        group: InstrumentGroup,
        cc_value: float = 0.0,
        variant: str = "default",
    ) -> np.ndarray:
        n = buf.shape[0]
        vel_norm = max(0.0, min(1.0, state.velocity / 127.0))

        # Variant factor for hammer/mechanical noise (piano family)
        variant_factor = 1.0
        if variant == "upright":
            variant_factor = 1.4
        elif variant == "grand":
            variant_factor = 1.0

        if group in (
            InstrumentGroup.ACOUSTIC_PIANO,
            InstrumentGroup.ELECTRIC_PIANO,
            InstrumentGroup.HARP,
        ):
            # Hammer attack noise (front-loaded) + key-off click at release
            attack = (
                self._noise(n)
                * (1.0 - np.arange(n) / max(n, 1))
                * 0.015
                * vel_norm
                * variant_factor
            )
            if state.phase.name == "release":
                off = self._noise(n) * (np.arange(n) / max(n, 1)) * 0.02 * vel_norm
                buf[:, 0] += attack + off
                buf[:, 1] += attack + off
            else:
                buf[:, 0] += attack
                buf[:, 1] += attack

        elif group in (
            InstrumentGroup.REEDS_WOODWINDS,
            InstrumentGroup.BRASS,
            InstrumentGroup.CHOIR,
            InstrumentGroup.ACCORDION,
            InstrumentGroup.FREE_REED,
        ):
            # Breath noise (continuous, low-level, driven by breath CC)
            breath_level = cc_value if cc_value > 0.0 else vel_norm
            # Per-sample breath turbulence (not a mean — must actually vary)
            breath = self._noise(n) * 0.008 * breath_level
            # Smooth the breath envelope so it reads as sustained air, not clicks
            self._breath_state = 0.9 * self._breath_state + 0.1 * float(
                np.mean(np.abs(breath))
            )
            buf[:, 0] += breath + self._breath_state * 0.0
            buf[:, 1] += breath + self._breath_state * 0.0

        elif group in (
            InstrumentGroup.BOWED_STRINGS,
            InstrumentGroup.ETHNIC,
            InstrumentGroup.PLUCKED_WORLD,
        ):
            # Bow/fret noise (very low, only at attack)
            if state.phase.name in ("attack", "legato"):
                bow = self._noise(n) * (1.0 - np.arange(n) / max(n, 1)) * 0.006 * vel_norm
                buf[:, 0] += bow
                buf[:, 1] += bow

        elif group in (
            InstrumentGroup.ACOUSTIC_GUITAR,
            InstrumentGroup.ELECTRIC_GUITAR,
            InstrumentGroup.MALLETS,
            InstrumentGroup.ACOUSTIC_BASS,
            InstrumentGroup.ELECTRIC_BASS,
            InstrumentGroup.TIMPANI,
        ):
            # Pluck/fret noise (short transient)
            pluck = self._noise(n) * (1.0 - np.arange(n) / max(n, 1)) ** 2 * 0.01 * vel_norm
            buf[:, 0] += pluck
            buf[:, 1] += pluck

        return buf

    def reset(self) -> None:
        self._breath_state = 0.0
