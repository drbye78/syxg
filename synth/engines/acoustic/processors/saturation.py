"""Gentle saturation for analog warmth (optional layer)."""

from __future__ import annotations

import numpy as np


class SaturationProcessor:
    """Soft tanh saturation with drive control (no allocation)."""

    def __init__(self, sample_rate: int, drive: float = 0.15):
        self.sample_rate = sample_rate
        self.drive = drive

    def process(self, buf: np.ndarray, drive: float | None = None) -> np.ndarray:
        d = self.drive if drive is None else drive
        if d <= 0.0:
            return buf
        left = buf[:, 0]
        right = buf[:, 1]
        for i in range(len(left)):
            x = float(left[i]) * (1.0 + d * 4.0)
            left[i] = np.tanh(x)
            x = float(right[i]) * (1.0 + d * 4.0)
            right[i] = np.tanh(x)
        return buf

    def reset(self) -> None:
        pass
