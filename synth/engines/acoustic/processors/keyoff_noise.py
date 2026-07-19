"""[A] Key-off noise — dedicated transient at note release.

Separate from the general performance noise so it can be tuned per-group
(key thunk for pianos, air release for winds, string stop for bowed).
"""

from __future__ import annotations

import numpy as np

from ..behavior_config import InstrumentGroup


class KeyOffNoise:
    """Short transient injected at note-off."""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._noise_idx = 0
        self._white = np.random.normal(0, 1, 1024).astype(np.float32)

    def _noise(self, n: int) -> np.ndarray:
        out = np.empty(n, dtype=np.float32)
        for i in range(n):
            out[i] = self._white[self._noise_idx]
            self._noise_idx = (self._noise_idx + 1) % len(self._white)
        return out

    def process(self, buf: np.ndarray, velocity: int, group: InstrumentGroup) -> np.ndarray:
        n = buf.shape[0]
        vel_norm = max(0.0, min(1.0, velocity / 127.0))
        # Front-loaded decay envelope (release transient at block start)
        env = (1.0 - np.arange(n) / max(n, 1)).astype(np.float32)
        amp = 0.0
        if group in (
            InstrumentGroup.ACOUSTIC_PIANO,
            InstrumentGroup.ELECTRIC_PIANO,
            InstrumentGroup.HARP,
        ):
            amp = 0.025 * vel_norm
        elif group in (
            InstrumentGroup.REEDS_WOODWINDS,
            InstrumentGroup.BRASS,
            InstrumentGroup.CHOIR,
            InstrumentGroup.ACCORDION,
            InstrumentGroup.FREE_REED,
        ):
            amp = 0.015 * vel_norm
        elif group in (
            InstrumentGroup.BOWED_STRINGS,
            InstrumentGroup.ETHNIC,
            InstrumentGroup.PLUCKED_WORLD,
        ):
            amp = 0.012 * vel_norm
        if amp <= 0.0:
            return buf
        trans = self._noise(n) * env * amp
        buf[:, 0] += trans
        buf[:, 1] += trans
        return buf

    def reset(self) -> None:
        pass
