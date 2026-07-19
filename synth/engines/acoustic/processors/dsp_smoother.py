"""Smoothing helper for parameter ramps in the acoustic behavior layer."""

from __future__ import annotations

import numpy as np


class DSPSmoother:
    """One-pole smoothing for per-block parameter changes (no allocation)."""

    def __init__(self, sample_rate: int, time_constant_ms: float = 10.0):
        self.sample_rate = sample_rate
        dt = 1.0 / sample_rate
        tau = max(time_constant_ms / 1000.0, 1e-4)
        self.alpha = dt / (tau + dt)
        self._state = 0.0

    def process(self, target: float, block_size: int) -> np.ndarray:
        out = np.empty(block_size, dtype=np.float32)
        state = self._state
        a = self.alpha
        for i in range(block_size):
            state += a * (target - state)
            out[i] = state
        self._state = state
        return out

    def reset(self) -> None:
        self._state = 0.0
