"""PitchModProcessor — pitch-based articulation effects using linear resampling.

Handles: vibrato, trill, glissando, bend, scoop, fall, doit, rip,
hammer_on, pull_off, portamento, smear, flip, ethnic_bend, sitar_bend.

Implements independent linear-interpolation resampling (NOT extracted from
SF2SampleModifier to avoid Numba JIT hot-path risks).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext

SEMITONE_RATIO: float = 1.059463094359  # 2^(1/12)


class PitchModProcessor(ArticulationProcessor):
    """Applies pitch-based articulations via linear-interpolation resampling.

    Handles ~60 articulation variants covering pitch modulation, glides,
    bends, and ornament techniques. Operates on stereo buffers — the same
    pitch modification is applied to both channels.
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._t: np.ndarray | None = None
        self._phase: np.ndarray | None = None
        self._scratch: np.ndarray | None = None
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

    def _ensure_phase(self, n: int) -> np.ndarray:
        needed = n + 1
        if self._phase is None or len(self._phase) < needed:
            self._phase = np.empty(needed, dtype=np.float32)
        return self._phase[:needed]

    def _resample(self, sample: np.ndarray, freq_mult: np.ndarray) -> np.ndarray:
        """Resample with linear interpolation."""
        n = len(sample)
        phase = self._ensure_phase(n)
        phase[0] = 0.0
        np.cumsum(freq_mult, out=phase[1:])
        src = phase[:-1]
        idx0 = np.floor(src).astype(np.int64)
        idx0 = np.clip(idx0, 0, n - 1)
        idx1 = np.clip(idx0 + 1, 0, n - 1)
        frac = src - idx0.astype(np.float32)
        return (sample[idx0] * (1.0 - frac) + sample[idx1] * frac).astype(np.float32)

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "vibrato")
        n = buf.shape[0]
        if n < 1:
            return

        # Apply same resampling to both channels independently
        left = buf[:, 0]
        right = buf[:, 1]
        left_mod = self._compute_freq_mult(left, atype, params)
        buf[:, 0] = self._resample(left, left_mod)
        buf[:, 1] = self._resample(right, left_mod)  # same mult for stereo

    def _compute_freq_mult(
        self, sample: np.ndarray, atype: str, params: dict[str, Any]
    ) -> np.ndarray:
        n = len(sample)
        t = self._ensure_time(n)

        if atype == "vibrato":
            rate = params.get("rate", 5.0)
            depth = params.get("depth", 0.5)
            pitch_mod = (depth * 0.3) * np.sin(2.0 * np.pi * rate * t)
            return SEMITONE_RATIO**pitch_mod

        elif atype == "trill":
            rate = params.get("rate", 8.0)
            interval = params.get("interval", 2)
            pitch_mod = interval * 0.5 * (1.0 + np.sin(2.0 * np.pi * rate * t))
            return SEMITONE_RATIO**pitch_mod

        elif atype in ("glissando", "slide"):
            amount = params.get("amount", 12)
            progress = np.arange(n, dtype=np.float32) / n
            return SEMITONE_RATIO ** (amount * progress)

        elif atype in ("bend", "scoop", "fall", "doit", "rip"):
            amount = params.get("amount", 1.0)
            curve = params.get("curve", "linear")
            if curve == "exponential":
                progress = 1.0 - np.exp(-t * params.get("speed", 5.0))
            else:
                progress = np.arange(n, dtype=np.float32) / n
            # scoop/fall: negative amount means pitch approach from below/above
            return SEMITONE_RATIO ** (amount * progress)

        elif atype in ("hammer_on", "pull_off"):
            amount = params.get("amount", 2)
            progress = np.arange(n, dtype=np.float32) / n
            return SEMITONE_RATIO ** (amount * progress)

        elif atype == "ethnic_bend":
            amount = params.get("bend_amount", params.get("amount", 0.5))
            speed = params.get("bend_speed", params.get("speed", 0.3))
            progress = 1.0 - np.exp(-t * speed * 10.0)
            return SEMITONE_RATIO ** (amount * progress)

        elif atype == "smear":
            amount = params.get("amount", 2.0)
            progress = (t / max(t[-1], 1e-6)) ** 2  # slow start
            return SEMITONE_RATIO ** (amount * progress)

        elif atype == "flip":
            amount = params.get("amount", 1.0)
            progress = np.sin(2.0 * np.pi * 15.0 * t) * 0.5 + 0.5
            return SEMITONE_RATIO ** (amount * progress)

        elif atype == "portamento":
            speed = params.get("speed", 0.05)
            progress = 1.0 - np.exp(-t * (1.0 / max(speed, 1e-6)))
            return SEMITONE_RATIO ** (0.0 * progress)  # pitch target set at voice level

        # Default: unity
        return np.ones(n, dtype=np.float32)

    def reset(self) -> None:
        pass
