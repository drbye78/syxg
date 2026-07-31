"""AmplitudeModProcessor — AM/LFO articulation effects (tremolo, flutter, growl)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class AmplitudeModProcessor(ArticulationProcessor):
    """Applies amplitude modulation articulations.

    Handles: tremolo, flutter, growl, buzz_roll, press_roll.

    Uses scratch buffer caching for zero-allocation after warm-up.
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._t: np.ndarray | None = None
        self._scratch: np.ndarray | None = None
        self._lp_state: dict[str, float] = {}
        self._prev_n: int = 0

    def _ensure_time(self, n: int) -> np.ndarray:
        if self._t is None or len(self._t) < n:
            sr = 1.0 / self.sample_rate
            self._t = np.empty(n, dtype=np.float32)
            self._t[0] = 0.0
            for i in range(1, n):
                self._t[i] = self._t[i - 1] + sr
            self._prev_n = n
        return self._t[:n]

    def _ensure_scratch(self, n: int) -> np.ndarray:
        if self._scratch is None or len(self._scratch) < n:
            self._scratch = np.zeros(n, dtype=np.float32)
        return self._scratch[:n]

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "tremolo")
        n = buf.shape[0]
        if n < 1:
            return

        if atype == "tremolo":
            rate = params.get("rate", 6.0)
            depth = params.get("depth", 0.5)
            t = self._ensure_time(n)
            mod = 1.0 + depth * np.sin(2.0 * np.pi * rate * t)
            buf[:, 0] *= mod
            buf[:, 1] *= mod

        elif atype == "flutter":
            mod_freq = params.get("rate", params.get("mod_freq", 12.0))
            depth = params.get("depth", 0.15)
            t = self._ensure_time(n)
            mod = 1.0 + depth * np.sin(2.0 * np.pi * mod_freq * t)
            buf[:, 0] *= mod
            buf[:, 1] *= mod

        elif atype == "growl":
            mod_freq = params.get("rate", params.get("mod_freq", 25.0))
            depth = params.get("depth", 0.25)
            t = self._ensure_time(n)
            mod = 1.0 + depth * np.sin(2.0 * np.pi * mod_freq * t)
            # Filtered noise for growl texture
            noise = np.random.normal(0, 0.08, n).astype(np.float32)
            # One-pole lowpass for noise colouration
            lp_key = f"growl_{context.instrument_group.value}"
            noise_filtered = self._one_pole_lowpass(noise, 800.0, lp_key)
            mix = params.get("noise_mix", 0.15)
            buf[:, 0] = buf[:, 0] * mod + noise_filtered * mix
            buf[:, 1] = buf[:, 1] * mod + noise_filtered * mix

    def _one_pole_lowpass(self, sample: np.ndarray, cutoff_hz: float, key: str) -> np.ndarray:
        dt = 1.0 / self.sample_rate
        tau = 1.0 / max(2.0 * np.pi * cutoff_hz, 1e-6)
        alpha = float(np.clip(dt / (tau + dt), 0.001, 0.999))
        out = self._ensure_scratch(len(sample))
        state = self._lp_state.get(key, 0.0)
        for i in range(len(sample)):
            state += alpha * (float(sample[i]) - state)
            out[i] = state
        self._lp_state[key] = state
        return out

    def reset(self) -> None:
        self._lp_state.clear()
