"""HarmonicsProcessor — pitch shift to harmonic partial via resampling.

Handles: harmonics, harmonics_natural, harmonics_artificial, harmonics_pinch,
harmonic_bass, harmonic_ethnic, harmonic_pizz, harmonic_tap, semi_tone_harm,
harmonics_strings.

Uses independent linear-interpolation resampling to shift pitch to target
partial. Natural harmonics are integer partials; artificial are non-integer.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext

SEMITONE_RATIO: float = 1.059463094359


class HarmonicsProcessor(ArticulationProcessor):
    """Pitch shifts to harmonic partial via linear resampling.

    Different harmonic types:
    - natural: integer partial (2, 3, 4...) → clear overtone
    - artificial: non-integer partial → "false" harmonic
    - pinch: high partial with AM modulation (pinch harmonic on guitar)
    - tap: harmonic tapped at specific node
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._phase: np.ndarray | None = None
        self._t: np.ndarray | None = None

    def _ensure_phase(self, n: int) -> np.ndarray:
        needed = n + 1
        if self._phase is None or len(self._phase) < needed:
            self._phase = np.empty(needed, dtype=np.float32)
        return self._phase[:needed]

    def _ensure_time(self, n: int) -> np.ndarray:
        if self._t is None or len(self._t) < n:
            sr = 1.0 / self.sample_rate
            self._t = np.empty(n, dtype=np.float32)
            self._t[0] = 0.0
            for i in range(1, n):
                self._t[i] = self._t[i - 1] + sr
        return self._t[:n]

    def _pitch_shift(self, sample: np.ndarray, ratio: float) -> np.ndarray:
        """Shift pitch by frequency ratio using linear resampling."""
        n = len(sample)
        freq_mult = np.full(n, ratio, dtype=np.float32)
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
        partial = params.get("partial", 2)
        htype = params.get("harmonic_type", params.get("type", "natural"))
        detune_cents = params.get("detune_cents", 0)
        n = buf.shape[0]
        if n < 1:
            return

        # Compute frequency ratio for the target partial
        ratio = float(partial)
        if detune_cents != 0:
            ratio *= SEMITONE_RATIO ** (detune_cents / 100.0)

        # Process each channel independently
        left = buf[:, 0]
        right = buf[:, 1]
        shifted_left = self._pitch_shift(left, ratio)
        shifted_right = self._pitch_shift(right, ratio)

        # Gentle lowpass: harmonics lose fundamental energy, sound thinner
        # Simple one-pole smoothing
        alpha = 0.85
        for i in range(1, n):
            shifted_left[i] = alpha * shifted_left[i] + (1.0 - alpha) * shifted_left[i - 1]
            shifted_right[i] = alpha * shifted_right[i] + (1.0 - alpha) * shifted_right[i - 1]

        buf[:, 0] = shifted_left
        buf[:, 1] = shifted_right

        # Pinch harmonic: add AM modulation
        if htype == "pinch":
            t = self._ensure_time(n)
            am = 1.0 + 0.15 * np.sin(2.0 * np.pi * 8.0 * t)
            buf[:, 0] *= am
            buf[:, 1] *= am

        # Tap harmonic: softer, more muted
        if htype == "tap":
            buf[:, 0] *= 0.6
            buf[:, 1] *= 0.6

    def reset(self) -> None:
        pass
