"""FormantProcessor — vocal formant filtering via parallel biquad bandpass.

Handles: falsetto, chest_voice, head_voice, mixed_voice, shout, scream,
straight_tone, vocal_attack, vocal_fry.

Uses three parallel BiquadFilter instances in bandpass mode at F1/F2/F3
for vocal formant shaping. C2b (whisper noise excitation) deferred.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from synth.primitives.filter import BiquadFilter

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


# ── Formant frequencies for vocal registers ──
# F1, F2, F3 in Hz. From standard vocal acoustics literature.
VOCAL_FORMANTS: dict[str, tuple[float, float, float]] = {
    "falsetto":      (500.0, 1400.0, 2800.0),
    "chest_voice":   (700.0, 1200.0, 2500.0),
    "head_voice":    (400.0, 1600.0, 3000.0),
    "mixed_voice":   (600.0, 1400.0, 2700.0),
    "whisper":       (600.0, 1300.0, 2500.0),  # C2b: needs noise excitation
    "shout":         (800.0, 1100.0, 2400.0),
    "scream":        (900.0, 1000.0, 3000.0),
    "straight_tone": (700.0, 1200.0, 2500.0),
    "vocal_attack":  (650.0, 1200.0, 2500.0),
    "vocal_fry":     (300.0, 1000.0, 2000.0),
}


class FormantProcessor(ArticulationProcessor):
    """Vocal formant shaping via three parallel biquad bandpass filters.

    Each filter targets one formant (F1, F2, F3). The dry/wet mix is
    controlled by a mix parameter — 1.0 = fully formant-shaped, 0.0 = dry.

    For shout/scream: adds mild saturation (tanh) for vocal drive.
    For vocal_fry: adds irregular low-frequency modulation.
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._f1: BiquadFilter | None = None
        self._f2: BiquadFilter | None = None
        self._f3: BiquadFilter | None = None
        self._active_register: str | None = None
        self._t: np.ndarray | None = None

    def _ensure_time(self, n: int) -> np.ndarray:
        if self._t is None or len(self._t) < n:
            sr = 1.0 / self.sample_rate
            self._t = np.empty(n, dtype=np.float32)
            self._t[0] = 0.0
            for i in range(1, n):
                self._t[i] = self._t[i - 1] + sr
        return self._t[:n]

    def _ensure_filters(self, f1: float, f2: float, f3: float) -> None:
        register_key = f"{f1:.0f}_{f2:.0f}_{f3:.0f}"
        if self._active_register != register_key:
            q = 1.5  # moderate resonance for vocal formants
            self._f1 = BiquadFilter("bandpass", f1, q, self.sample_rate)
            self._f2 = BiquadFilter("bandpass", f2, q, self.sample_rate)
            self._f3 = BiquadFilter("bandpass", f3, q, self.sample_rate)
            self._active_register = register_key

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        register = params.get("register", "chest_voice")
        f1, f2, f3 = params.get("formants", VOCAL_FORMANTS.get(register, (700, 1200, 2500)))
        breathiness = params.get("breathiness", 0.0)
        drive = params.get("drive", 0.0)
        mix = params.get("mix", 0.5)
        n = buf.shape[0]
        if n < 1:
            return

        self._ensure_filters(f1, f2, f3)

        # Process each channel through the parallel formant chain
        for ch in (0, 1):
            channel_buf = buf[:, ch].copy()
            # Run through each formant filter
            f1_out = np.array([self._f1.process(float(x)) for x in channel_buf])
            f2_out = np.array([self._f2.process(float(x)) for x in channel_buf])
            f3_out = np.array([self._f3.process(float(x)) for x in channel_buf])
            # Mix formant-shaped output with dry
            shaped = (f1_out + f2_out + f3_out) * 0.3
            buf[:, ch] = channel_buf * (1.0 - mix) + shaped * mix

        # Breathiness: mix in filtered noise
        if breathiness > 0.0:
            noise = np.random.normal(0, breathiness * 0.1, n).astype(np.float32)
            buf[:, 0] += noise
            buf[:, 1] += noise

        # Drive/saturation for shout/scream
        if drive > 0.0:
            buf = np.tanh(buf * (1.0 + drive * 3.0))

        # Vocal fry: irregular low-frequency modulation
        if register == "vocal_fry":
            t = self._ensure_time(n)
            irregular = np.sin(2.0 * np.pi * 15.0 * t + np.random.uniform(0, 1)) * 0.1
            buf[:, 0] *= (1.0 + irregular)
            buf[:, 1] *= (1.0 + irregular)

    def reset(self) -> None:
        if self._f1 is not None:
            self._f1.z1 = self._f1.z2 = 0.0
        if self._f2 is not None:
            self._f2.z1 = self._f2.z2 = 0.0
        if self._f3 is not None:
            self._f3.z1 = self._f3.z2 = 0.0
