"""RotaryProcessor — Leslie speaker effect (simplified AM+FM)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class RotaryProcessor(ArticulationProcessor):
    """Simplified Leslie speaker: AM + FM stereo modulation."""

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._t: np.ndarray | None = None
        self._phase: float = 0.0

    def _ensure_time(self, n: int) -> np.ndarray:
        if self._t is None or len(self._t) < n:
            sr = 1.0 / self.sample_rate
            self._t = np.empty(n, dtype=np.float32)
            self._t[0] = 0.0
            for i in range(1, n):
                self._t[i] = self._t[i - 1] + sr
        return self._t[:n]

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        speed = params.get("speed", "slow")
        rates = {"slow": 1.5, "medium": 4.0, "fast": 7.0}
        rate = rates.get(speed, 1.5)
        n = buf.shape[0]
        t = self._ensure_time(n)
        # AM + FM modulation with stereo phase offset
        am_l = 1.0 + 0.3 * np.sin(2.0 * np.pi * rate * t)
        am_r = 1.0 + 0.3 * np.cos(2.0 * np.pi * rate * t)
        buf[:, 0] *= am_l
        buf[:, 1] *= am_r
        # Gentle saturation
        buf = np.tanh(buf * 1.2)

    def reset(self) -> None:
        self._phase = 0.0
