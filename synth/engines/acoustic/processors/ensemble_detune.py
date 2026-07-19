"""[B] Ensemble detune + shared vibrato for section instruments.

Applies a per-voice detune offset (claimed from the shared pool) and a
phase-locked vibrato so section voices stay coherent. Operates per-channel
on the stereo buffer.
"""

from __future__ import annotations

import math

import numpy as np

from ..behavior_config import InstrumentGroup


class EnsembleDetuneProcessor:
    """Per-voice detune + shared vibrato."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._phase_l = 0.0
        self._phase_r = 0.0

    def process(
        self,
        buf: np.ndarray,
        detune_cents: float = 0.0,
        vibrato_phase: float = 0.0,
        group: InstrumentGroup = InstrumentGroup.BOWED_STRINGS,
        vibrato_depth_cents: float = 4.0,
    ) -> np.ndarray:
        n = buf.shape[0]
        # Combined pitch deviation in cents
        vib = vibrato_depth_cents * math.sin(vibrato_phase)
        total_cents = detune_cents + vib
        if abs(total_cents) < 0.01:
            return buf
        ratio = 2.0 ** (total_cents / 1200.0)

        left = buf[:, 0]
        right = buf[:, 1]
        out = np.empty_like(buf)
        phase_l = self._phase_l
        phase_r = self._phase_r
        for i in range(n):
            phase_l += ratio
            phase_r += ratio
            i0 = int(phase_l)
            f = phase_l - i0
            i0 = min(max(i0, 0), n - 1)
            i1 = min(i0 + 1, n - 1)
            out[i, 0] = left[i0] * (1.0 - f) + left[i1] * f
            i0 = int(phase_r)
            f = phase_r - i0
            i0 = min(max(i0, 0), n - 1)
            i1 = min(i0 + 1, n - 1)
            out[i, 1] = right[i0] * (1.0 - f) + right[i1] * f
        self._phase_l = phase_l - (n - 1)
        self._phase_r = phase_r - (n - 1)
        return out

    def reset(self) -> None:
        self._phase_l = 0.0
        self._phase_r = 0.0
