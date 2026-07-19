"""[A] Single-note velocity-driven timbre shaping.

Maps MIDI velocity to spectral brightness/body so a soft note sounds
rounder and a hard note brighter — the core SuperNATURAL single-note
behavior. Uses a pre-allocated resonant lowpass per channel (stereo).
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from ..behavior_config import InstrumentGroup


class VelocityTimbreProcessor:
    """Brightness/body mapping from note velocity."""

    # Per-group brightness response (cutoff range in Hz at vel 1..127)
    _GROUP_CURVE: ClassVar[dict[InstrumentGroup, tuple[float, float]]] = {
        InstrumentGroup.ACOUSTIC_PIANO: (900.0, 9000.0),
        InstrumentGroup.ELECTRIC_PIANO: (1200.0, 8000.0),
        InstrumentGroup.ORGAN: (2000.0, 12000.0),
        InstrumentGroup.BOWED_STRINGS: (700.0, 7000.0),
        InstrumentGroup.BRASS: (600.0, 6500.0),
        InstrumentGroup.REEDS_WOODWINDS: (800.0, 8000.0),
        InstrumentGroup.ACOUSTIC_GUITAR: (1000.0, 10000.0),
        InstrumentGroup.ELECTRIC_GUITAR: (1000.0, 10000.0),
        InstrumentGroup.ACOUSTIC_BASS: (400.0, 4000.0),
        InstrumentGroup.ELECTRIC_BASS: (400.0, 4000.0),
        InstrumentGroup.CHOIR: (900.0, 8000.0),
        InstrumentGroup.ETHNIC: (800.0, 7500.0),
        InstrumentGroup.PLUCKED_WORLD: (1000.0, 10000.0),
        InstrumentGroup.ACCORDION: (1000.0, 9000.0),
        InstrumentGroup.HARP: (1500.0, 11000.0),
        InstrumentGroup.MALLETS: (1500.0, 11000.0),
        InstrumentGroup.TIMPANI: (1500.0, 12000.0),
        InstrumentGroup.FREE_REED: (1000.0, 9000.0),
    }

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._lp_l = 0.0
        self._lp_r = 0.0
        self._target = 0.0

    @staticmethod
    def _velocity_to_norm(velocity: int) -> float:
        return max(0.0, min(1.0, velocity / 127.0))

    def process(self, buf: np.ndarray, velocity: int, group: InstrumentGroup) -> np.ndarray:
        lo, hi = self._GROUP_CURVE.get(group, (900.0, 9000.0))
        norm = self._velocity_to_norm(velocity)
        # Slight concave curve: soft notes drop brightness faster
        cutoff = lo + (hi - lo) * (norm**1.3)
        dt = 1.0 / self.sample_rate
        tau = 1.0 / max(2.0 * np.pi * cutoff, 1e-6)
        alpha = dt / (tau + dt)
        alpha = float(np.clip(alpha, 0.001, 0.999))

        left = buf[:, 0]
        right = buf[:, 1]
        state_l = self._lp_l
        state_r = self._lp_r
        for i in range(len(left)):
            state_l += alpha * (float(left[i]) - state_l)
            state_r += alpha * (float(right[i]) - state_r)
            left[i] = state_l
            right[i] = state_r
        self._lp_l = state_l
        self._lp_r = state_r
        return buf

    def reset(self) -> None:
        self._lp_l = 0.0
        self._lp_r = 0.0
