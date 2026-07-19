"""[B] Damper resonance — pedal-up body coupling.

When the sustain pedal is released, the strings/drum heads couple to the
resonant body and produce a short sympathetic "thunk"/ring. This processor
adds that coupling on note-off when the pedal is NOT held.
"""

from __future__ import annotations

import numpy as np


class DamperResonance:
    """Short body coupling applied on pedal-up note release."""

    def __init__(self, sample_rate: int, decay_ms: float = 120.0):
        self.sample_rate = sample_rate
        self.decay = decay_ms / 1000.0
        self._state = 0.0

    def process(self, buf: np.ndarray, note: int = 60) -> np.ndarray:
        n = buf.shape[0]
        # Exponentially decaying coupling impulse, front-loaded
        t = np.arange(n) / self.sample_rate
        env = np.exp(-t / max(self.decay, 1e-3)).astype(np.float32)
        # Coupling amplitude scales with note energy proxy
        energy = float(np.mean(np.abs(buf)))
        amp = min(energy * 0.3, 0.05)
        coupling = env * amp
        buf[:, 0] += coupling
        buf[:, 1] += coupling
        return buf

    def reset(self) -> None:
        self._state = 0.0
