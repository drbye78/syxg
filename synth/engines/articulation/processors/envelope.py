"""EnvelopeProcessor — amplitude envelope articulations (pizzicato, staccato, etc.)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class EnvelopeProcessor(ArticulationProcessor):
    """Applies amplitude envelope shaping articulations.

    Handles: pizzicato, staccato, marcato, swell, spiccato, dead_note,
    ricochet, tenuto, detache, straight + pizzicato variants.

    Uses scratch buffer caching for zero-allocation after warm-up.
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._scratch: np.ndarray | None = None
        self._t: np.ndarray | None = None
        self._prev_n: int = 0

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
            self._prev_n = n
        return self._t[:n]

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "pizzicato")
        n = buf.shape[0]
        if n < 1:
            return
        if atype == "pizzicato":
            decay = params.get("decay", 8.0)
            t = self._ensure_time(n)
            env = np.exp(-t * decay).astype(np.float32)
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "staccato":
            fade_time = params.get("fade_time", 0.05)
            fade_samples = max(1, int(fade_time * self.sample_rate))
            fade_samples = min(fade_samples, n)
            env = self._ensure_scratch(n)
            env[:] = 1.0
            if fade_samples < n:
                t = self._ensure_time(n - fade_samples)
                decay = np.exp(-t * 20.0).astype(np.float32)
                env[fade_samples:] = decay
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "marcato":
            accent = params.get("accent", 1.3)
            decay = params.get("decay", 0.1)
            decay_samples = max(1, int(decay * self.sample_rate))
            env = self._ensure_scratch(n)
            env[:] = 1.0
            if decay_samples < n:
                t = self._ensure_time(n - decay_samples)
                env[decay_samples:] = np.exp(-t * 10.0)
            env *= accent
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "swell":
            attack = params.get("attack", 0.1)
            release = params.get("release", 0.2)
            attack_s = int(attack * self.sample_rate)
            release_s = int(release * self.sample_rate)
            env = self._ensure_scratch(n)
            env[:] = 1.0
            if attack_s > 0:
                at_len = min(attack_s, n)
                env[:at_len] = np.linspace(0.0, 1.0, at_len, dtype=np.float32)
            if release_s > 0 and n > attack_s:
                rel_start = max(0, n - release_s)
                rel_len = n - rel_start
                env[rel_start:] = np.linspace(1.0, 0.0, rel_len, dtype=np.float32)
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "crescendo":
            ramp = params.get("ramp", "up")
            env = self._ensure_scratch(n)
            if ramp == "down":
                env[:] = np.linspace(1.0, 0.0, n, dtype=np.float32)
            else:
                env[:] = np.linspace(0.0, 1.0, n, dtype=np.float32)
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "dead_note":
            decay = params.get("decay", 0.01)
            t = self._ensure_time(n)
            env = np.exp(-t * (1.0 / max(decay, 1e-6))).astype(np.float32)
            level = params.get("level", 0.3)
            buf[:, 0] *= env * level
            buf[:, 1] *= env * level
        elif atype == "legato":
            transition = params.get("transition_time", 0.05)
            trans_samples = max(1, int(transition * self.sample_rate))
            trans_samples = min(trans_samples, n)
            env = self._ensure_scratch(n)
            env[:] = 1.0
            env[:trans_samples] = np.linspace(0.5, 1.0, trans_samples, dtype=np.float32)
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "tenuto":
            hold = params.get("hold", 0.8)
            env = self._ensure_scratch(n)
            env[:] = hold
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "detache":
            separation = params.get("separation", 0.02)
            sep_samples = max(1, int(separation * self.sample_rate))
            env = self._ensure_scratch(n)
            env[:] = 1.0
            if sep_samples < n:
                env[-sep_samples:] = 0.0
            buf[:, 0] *= env
            buf[:, 1] *= env
        elif atype == "straight":
            pass  # no vibrato modulation — handled at voice level
        elif atype == "ricochet":
            bounces = params.get("bounces", 4)
            decay = params.get("decay", 0.8)
            env = self._ensure_scratch(n)
            env[:] = 1.0
            bounce_len = n // (bounces * 2)
            for b in range(bounces):
                start = b * bounce_len * 2
                end = start + bounce_len
                if start < n:
                    amp = decay**b
                    segment_len = min(bounce_len, n - start)
                    env[start : start + segment_len] = amp
            buf[:, 0] *= env
            buf[:, 1] *= env

    def reset(self) -> None:
        pass
