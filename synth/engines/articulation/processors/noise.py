"""NoiseProcessor — noise-based articulation effects (fret_noise, rim_shot, breath, etc.)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class NoiseProcessor(ArticulationProcessor):
    """Applies noise-based and transient articulations.

    Handles: fret_noise, organ_click, rim_shot, open_rim, breath,
    tongue_slap, key_off_noise, damper_noise, hammer_noise,
    body_hit_gtr, string noise variants.
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._scratch: np.ndarray | None = None
        self._t: np.ndarray | None = None
        self._noise_buf: np.ndarray | None = None
        self._noise_idx: int = 0
        self._lp_state: dict[str, float] = {}

    def _ensure_scratch(self, n: int) -> np.ndarray:
        if self._scratch is None or len(self._scratch) < n:
            self._scratch = np.zeros(n, dtype=np.float32)
        return self._scratch[:n]

    def _ensure_time(self, n: int) -> np.ndarray:
        if self._t is None or len(self._t) < n:
            sr = 1.0 / self.sample_rate
            self._t = np.empty(n, dtype=np.float32)
            self._t[0] = 0.0
            for i in range(1, n):
                self._t[i] = self._t[i - 1] + sr
        return self._t[:n]

    def _ensure_noise(self, n: int) -> np.ndarray:
        if self._noise_buf is None or len(self._noise_buf) < n:
            self._noise_buf = np.random.normal(0, 1, max(n, 1024)).astype(np.float32)
            self._noise_idx = 0
        if self._noise_idx + n > len(self._noise_buf):
            self._noise_buf = np.random.normal(0, 1, max(n, 1024)).astype(np.float32)
            self._noise_idx = 0
        result = self._noise_buf[self._noise_idx : self._noise_idx + n].copy()
        self._noise_idx += n
        return result

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

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "fret_noise")
        n = buf.shape[0]
        if n < 1:
            return

        if atype == "fret_noise":
            level = params.get("noise_level", params.get("level", 0.15))
            noise = self._ensure_noise(n) * level
            cutoff = params.get("lowpass_cutoff", params.get("lowpass", 4000.0))
            noise = self._one_pole_lowpass(noise, cutoff, "fret")
            t = self._ensure_time(n)
            env = np.exp(-t * 50.0).astype(np.float32)
            trans = noise * env
            buf[:, 0] += trans
            buf[:, 1] += trans

        elif atype == "organ_click":
            level = params.get("level", 0.2)
            noise = self._ensure_noise(n) * level
            cutoff = params.get("lowpass", 2000.0)
            noise = self._one_pole_lowpass(noise, cutoff, "organ")
            t = self._ensure_time(n)
            env = np.exp(-t * 200.0).astype(np.float32)
            buf[:, 0] += noise * env
            buf[:, 1] += noise * env

        elif atype == "rim_shot":
            level = params.get("level", 0.3)
            noise = self._ensure_noise(n) * level
            cutoff = params.get("lowpass", 4000.0)
            noise = self._one_pole_lowpass(noise, cutoff, "rim_shot")
            t = self._ensure_time(n)
            env = np.exp(-t * 80.0).astype(np.float32)
            buf[:, 0] += noise * env
            buf[:, 1] += noise * env

        elif atype == "open_rim":
            level = params.get("level", 0.25)
            noise = self._ensure_noise(n) * level
            resonance = params.get("resonance", 3000.0)
            # Add resonance by ringing noise
            t = self._ensure_time(n)
            ring = np.sin(2.0 * np.pi * resonance * t) * np.exp(-t * 20.0) * 0.15
            noise_filtered = self._one_pole_lowpass(noise, resonance, "open_rim")
            buf[:, 0] += noise_filtered + ring
            buf[:, 1] += noise_filtered + ring

        elif atype == "breath":
            level = params.get("level", 0.15)
            noise = self._ensure_noise(n) * level
            cutoff = params.get("lowpass", 800.0)
            noise = self._one_pole_lowpass(noise, cutoff, "breath")
            buf[:, 0] += noise
            buf[:, 1] += noise

        elif atype == "tongue_slap":
            level = params.get("level", 0.3)
            noise = self._ensure_noise(n) * level
            cutoff = params.get("lowpass", 1200.0)
            noise = self._one_pole_lowpass(noise, cutoff, "tongue")
            t = self._ensure_time(n)
            env = np.exp(-t * 100.0).astype(np.float32)
            buf[:, 0] += noise * env
            buf[:, 1] += noise * env

        elif atype in ("key_off", "damper", "hammer", "body_hit"):
            level = params.get("level", 0.05)
            noise = self._ensure_noise(n) * level
            cutoffs = {"key_off": 4000.0, "damper": 2000.0, "hammer": 6000.0, "body_hit": 500.0}
            cutoff = params.get("lowpass", cutoffs.get(atype, 4000.0))
            noise = self._one_pole_lowpass(noise, cutoff, atype)
            decays = {"key_off": 80.0, "damper": 40.0, "hammer": 120.0, "body_hit": 30.0}
            decay = decays.get(atype, 50.0)
            t = self._ensure_time(n)
            env = np.exp(-t * decay).astype(np.float32)
            buf[:, 0] += noise * env
            buf[:, 1] += noise * env

    def reset(self) -> None:
        self._lp_state.clear()
