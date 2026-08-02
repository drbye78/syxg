"""[B] Ensemble detune + shared vibrato for section instruments.

Applies a per-voice detune offset (claimed from the shared pool) and a
phase-locked vibrato so section voices stay coherent. Operates per-channel
on the stereo buffer.
"""

from __future__ import annotations

import math

import numpy as np

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
        # Cubic Hermite spline interpolation — replaces linear to fix aliasing
        # Use 4-point interpolation for smoother pitch shifting
        if n >= 4:
            # Pre-compute read positions for entire block
            positions = np.arange(n) * ratio + self._phase_l
            int_pos = np.floor(positions).astype(np.int64)
            frac = positions - int_pos

            # 4-point cubic: i-1, i, i+1, i+2
            i0 = np.clip(int_pos - 1, 0, n - 1)
            i1 = np.clip(int_pos, 0, n - 1)
            i2 = np.clip(int_pos + 1, 0, n - 1)
            i3 = np.clip(int_pos + 2, 0, n - 1)

            t = frac
            t2 = t * t
            t3 = t2 * t
            # Cubic Hermite basis functions
            h00 = 2.0 * t3 - 3.0 * t2 + 1.0
            h10 = t3 - 2.0 * t2 + t
            h01 = -2.0 * t3 + 3.0 * t2
            h11 = t3 - t2

            # Tangent estimation (Catmull-Rom)
            m0 = (left[i1] - left[i0]) * 0.5
            m1 = (left[i3] - left[i2]) * 0.5
            out[:, 0] = h00 * left[i1] + h10 * m0 + h01 * left[i2] + h11 * m1

            m0 = (right[i1] - right[i0]) * 0.5
            m1 = (right[i3] - right[i2]) * 0.5
            out[:, 1] = h00 * right[i1] + h10 * m0 + h01 * right[i2] + h11 * m1
        else:
            # Fallback: linear for very short blocks
            positions = np.arange(n) * ratio + self._phase_l
            int_pos = np.floor(positions).astype(np.int64)
            frac = positions - int_pos
            i0 = np.clip(int_pos, 0, n - 1)
            i1 = np.clip(int_pos + 1, 0, n - 1)
            out[:, 0] = left[i0] * (1.0 - frac) + left[i1] * frac
            out[:, 1] = right[i0] * (1.0 - frac) + right[i1] * frac

        self._phase_l = self._phase_l + n * ratio - (n - 1)
        self._phase_r = self._phase_r + n * ratio - (n - 1)
        return out

    def reset(self) -> None:
        self._phase_l = 0.0
        self._phase_r = 0.0
