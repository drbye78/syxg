"""TransientProcessor — percussion transient effects with per-group presets.

Handles: flam, drag, ruff, diddle, bounce, dead_stroke, cross_stick,
perc_attack/decay, ethnic_attack/decay.

Uses per-InstrumentGroup preset tables for spectral shaping (pattern
from VelocityTimbreProcessor).
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext
from synth.engines.acoustic.behavior_config import InstrumentGroup


class TransientProcessor(ArticulationProcessor):
    """Percussion and transient articulation effects.

    Each transient type (flam, drag, etc.) has a base algorithm. The per-group
    presets tune spectral shaping (resonance, decay, level) for each instrument.
    """

    # Per-group transient parameters: (resonance_hz, decay_rate, base_level)
    _GROUP_PRESET: ClassVar[dict[InstrumentGroup, tuple[float, float, float]]] = {
        InstrumentGroup.ACOUSTIC_PIANO: (4000.0, 40.0, 0.04),
        InstrumentGroup.ELECTRIC_PIANO: (3500.0, 35.0, 0.03),
        InstrumentGroup.ORGAN: (2500.0, 25.0, 0.02),
        InstrumentGroup.ACOUSTIC_GUITAR: (1500.0, 30.0, 0.08),
        InstrumentGroup.ELECTRIC_GUITAR: (2000.0, 25.0, 0.06),
        InstrumentGroup.ACOUSTIC_BASS: (800.0, 20.0, 0.10),
        InstrumentGroup.ELECTRIC_BASS: (1000.0, 20.0, 0.08),
        InstrumentGroup.BOWED_STRINGS: (2000.0, 50.0, 0.03),
        InstrumentGroup.MALLETS: (5000.0, 60.0, 0.15),
        InstrumentGroup.TIMPANI: (3000.0, 20.0, 0.12),
        InstrumentGroup.BRASS: (2500.0, 40.0, 0.03),
        InstrumentGroup.REEDS_WOODWINDS: (3000.0, 40.0, 0.04),
        InstrumentGroup.ETHNIC: (3500.0, 35.0, 0.10),
        InstrumentGroup.PLUCKED_WORLD: (2500.0, 30.0, 0.08),
        InstrumentGroup.ACCORDION: (2000.0, 30.0, 0.03),
        InstrumentGroup.CHOIR: (1500.0, 25.0, 0.02),
        InstrumentGroup.HARP: (4000.0, 50.0, 0.06),
        InstrumentGroup.FREE_REED: (2000.0, 30.0, 0.04),
    }

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._t: np.ndarray | None = None
        self._noise_buf: np.ndarray | None = None
        self._noise_idx: int = 0
        self._lp_state: dict[str, float] = {}

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
        n = len(sample)
        out = np.empty(n, dtype=np.float32)
        state = self._lp_state.get(key, 0.0)
        for i in range(n):
            state += alpha * (float(sample[i]) - state)
            out[i] = state
        self._lp_state[key] = state
        return out

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "flam")
        n = buf.shape[0]
        if n < 1:
            return

        resonance, decay_rate, base_level = self._GROUP_PRESET.get(
            context.instrument_group, (3000.0, 40.0, 0.05)
        )
        resonance = params.get("resonance", resonance)
        decay_rate = params.get("decay_rate", decay_rate)
        level = params.get("level", base_level)

        if atype in ("flam", "drag", "ruff"):
            delay_ms = params.get("delay_ms", 15 if atype == "flam" else 20)
            bounces = params.get("bounces", {"flam": 1, "drag": 2, "ruff": 3}.get(atype, 1))
            accent_ratio = params.get("accent_ratio", 0.5)
            self._apply_multi_strike(buf, n, delay_ms, bounces, accent_ratio, level, resonance, decay_rate)
        elif atype == "diddle":
            self._apply_multi_strike(buf, n, 8, 2, 0.7, level, resonance, decay_rate)
        elif atype == "bounce":
            self._apply_multi_strike(buf, n, 10, 3, 0.6, level, resonance, decay_rate)
        elif atype == "dead_stroke":
            self._apply_noise_transient(buf, n, level * 0.5, resonance * 0.5, decay_rate * 2.0)
        elif atype == "cross_stick":
            self._apply_noise_transient(buf, n, level * 1.5, resonance, decay_rate * 1.5)
        elif atype in ("perc_attack", "ethnic_attack"):
            self._apply_noise_transient(buf, n, level, resonance, decay_rate * 0.5)
        elif atype in ("perc_decay", "ethnic_decay"):
            self._apply_noise_transient(buf, n, level * 0.3, resonance * 0.8, decay_rate * 0.3)
        else:
            self._apply_noise_transient(buf, n, level, resonance, decay_rate)

    def _apply_multi_strike(
        self, buf: np.ndarray, n: int, delay_ms: float, bounces: int,
        accent_ratio: float, level: float, resonance: float, decay_rate: float,
    ) -> None:
        """Apply a multi-strike transient (flam, drag, ruff, diddle, bounce)."""
        delay_samples = max(1, int(delay_ms * self.sample_rate / 1000.0))
        noise = self._ensure_noise(n) * level
        noise = self._one_pole_lowpass(noise, resonance, "transient_multi")
        t = self._ensure_time(n)
        env = np.zeros(n, dtype=np.float32)
        for b in range(bounces):
            start = b * delay_samples
            if start < n:
                remaining = n - start
                amp = accent_ratio ** (b + 1) if accent_ratio < 1.0 else 1.0
                t_seg = t[:remaining]
                env[start:] += amp * np.exp(-t_seg * decay_rate).astype(np.float32) * (0.5 ** b)
        env = np.clip(env, 0.0, 1.0)
        buf[:, 0] += noise * env
        buf[:, 1] += noise * env

    def _apply_noise_transient(
        self, buf: np.ndarray, n: int, level: float,
        resonance: float, decay_rate: float,
    ) -> None:
        """Apply a simple noise transient with envelope."""
        noise = self._ensure_noise(n) * level
        noise = self._one_pole_lowpass(noise, resonance, "transient_single")
        t = self._ensure_time(n)
        env = np.exp(-t * decay_rate).astype(np.float32)
        buf[:, 0] += noise * env
        buf[:, 1] += noise * env

    def reset(self) -> None:
        self._lp_state.clear()
