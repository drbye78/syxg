"""[B] Legato processor: smooth pitch glide between overlapping notes.

When a new note starts while others are held (legato), skip the re-attack
and glide from the previous pitch. Operates on the stereo buffer via
per-sample resampling using the shared pitch ratio.
"""

from __future__ import annotations

import numpy as np


class LegatoProcessor:
    """Per-block legato glide between notes."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._phase = 0.0

    def process(
        self, buf: np.ndarray, from_note: int | None, to_note: int, glide_ms: float = 30.0
    ) -> np.ndarray:
        if from_note is None or from_note == to_note:
            return buf
        n = buf.shape[0]
        # Frequency ratio from->to
        ratio = 2.0 ** ((to_note - from_note) / 12.0)
        # Glide over glide_ms (clamped to block)
        glide_samples = int(self.sample_rate * glide_ms / 1000.0)
        glide_samples = min(glide_samples, n)
        # Build per-sample multiplier ramping 1 -> ratio
        mult = np.ones(n, dtype=np.float32)
        if glide_samples > 0:
            t = np.arange(glide_samples) / glide_samples
            mult[:glide_samples] = (1.0 + (ratio - 1.0) * t).astype(np.float32)

        # Resample via linear interpolation (per channel)
        out = np.empty_like(buf)
        for ch in range(2):
            src = buf[:, ch]
            phase = self._phase
            for i in range(n):
                phase += mult[i]
                idx0 = int(phase)
                frac = phase - idx0
                idx0 = min(max(idx0, 0), n - 1)
                idx1 = min(idx0 + 1, n - 1)
                out[i, ch] = src[idx0] * (1.0 - frac) + src[idx1] * frac
            self._phase = phase - (n - 1)
        return out

    def reset(self) -> None:
        self._phase = 0.0
