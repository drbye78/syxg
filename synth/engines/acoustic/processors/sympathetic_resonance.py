"""[B] Sympathetic resonance bank — the flagship cross-note behavior.

A shared bus owned by the ChannelAcousticContext. Every active voice FEEDS
the bank with its pitch energy; the bank rings at the instrument's natural
resonant modes and is MIXED back into every voice. This is what makes a
piano/strings sound "alive" when other notes are held — the core
SuperNATURAL cross-note authenticity.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class SympatheticResonanceBank:
    """Shared resonant body model fed by all voices on a channel."""

    # Default modal frequencies (Hz) for a generic acoustic body.
    _DEFAULT_MODES = (110.0, 146.8, 196.0, 246.9, 329.6, 392.0, 493.9, 587.3, 659.3, 784.0)

    def __init__(
        self,
        sample_rate: int,
        loop_gain: float = 0.85,
        coupling: float = 0.25,
        modes: tuple[float, ...] | None = None,
    ):
        self.sample_rate = sample_rate
        self.loop_gain = loop_gain
        self.coupling = coupling
        self.modes = modes or self._DEFAULT_MODES

        # Per-mode resonator state (biquad-style one-pole loop)
        self._mode_state = np.zeros(len(self.modes), dtype=np.float32)
        self._mode_vel = np.zeros(len(self.modes), dtype=np.float32)
        # Excitation accumulator (per block)
        self._excited = np.zeros(len(self.modes), dtype=np.float32)
        self._work: np.ndarray | None = None

    def feed(self, buf: np.ndarray, note: int) -> None:
        """Excite resonant modes from a voice's output energy."""
        # Estimate energy in this block (RMS proxy)
        energy = float(np.mean(np.abs(buf)))
        if energy <= 0.0:
            return
        # Map note to nearest modes by pitch class (octave-folded)
        note_freq = 440.0 * 2.0 ** ((note - 69) / 12.0)
        for i, f in enumerate(self.modes):
            # Coupling stronger for modes near the note's harmonics
            ratio = note_freq / f
            harm = min(ratio, 1.0 / max(ratio, 1e-3))
            coup = self.coupling * (0.5 + 0.5 * harm)
            self._excited[i] += energy * coup

    def mix(self, buf: np.ndarray, amount: float = 1.0) -> np.ndarray:
        """Ring the resonators and mix the result into the buffer."""
        n = buf.shape[0]
        if self._work is None or len(self._work) < n:
            self._work = np.zeros(n, dtype=np.float32)
        out = self._work[:n]
        out.fill(0.0)

        dt = 1.0 / self.sample_rate
        for i, f in enumerate(self.modes):
            # Resonant one-pole loop (damped oscillator)
            w = 2.0 * np.pi * f
            decay = self.loop_gain
            # Simple damped resonator update
            self._mode_vel[i] += -w * w * self._mode_state[i] * dt
            self._mode_vel[i] *= decay
            self._mode_state[i] += self._mode_vel[i] * dt
            # Inject excitation (decaying)
            exc = self._excited[i]
            self._mode_state[i] += exc
            self._excited[i] *= 0.5  # excitation decays each block
            # Accumulate into output
            out += self._mode_state[i] * 0.1

        # Normalize and mix
        out *= amount
        buf[:, 0] += out
        buf[:, 1] += out
        return buf

    def reset(self) -> None:
        self._mode_state.fill(0.0)
        self._mode_vel.fill(0.0)
        self._excited.fill(0.0)
