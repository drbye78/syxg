"""FilterProcessor — filtering-based articulation effects (mutes, pedals, timbre)."""

from __future__ import annotations

from typing import Any

import numpy as np

from synth.primitives.filter import BiquadFilter

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class FilterProcessor(ArticulationProcessor):
    """Applies filtering-based articulations using BiquadFilter.

    Handles: soft_pedal, sub_bass, palm_mute, con_sordino, sul_ponticello,
    sul_tasto, mutes (brass, guitar, bass, percussion), Organ_soft/loud.

    Uses existing BiquadFilter from synth/primitives/ for production-quality
    filtering (RBJ cookbook, TDF-II form).
    """

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)
        self._filter_left: BiquadFilter | None = None
        self._filter_right: BiquadFilter | None = None
        self._active_type: str | None = None

    def _ensure_filter(self, filter_type: str, cutoff_hz: float, resonance: float) -> None:
        if self._filter_left is None or self._active_type != filter_type:
            self._filter_left = BiquadFilter(
                filter_type=filter_type,
                cutoff=cutoff_hz,
                resonance=resonance,
                sample_rate=self.sample_rate,
            )
            self._filter_right = BiquadFilter(
                filter_type=filter_type,
                cutoff=cutoff_hz,
                resonance=resonance,
                sample_rate=self.sample_rate,
            )
            self._active_type = filter_type
        elif self._filter_left is not None:
            self._filter_left.cutoff = cutoff_hz
            self._filter_left.resonance = resonance
            self._filter_left._update_coefficients()
            if self._filter_right is not None:
                self._filter_right.cutoff = cutoff_hz
                self._filter_right.resonance = resonance
                self._filter_right._update_coefficients()

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "lowpass")
        n = buf.shape[0]
        if n < 1:
            return

        if atype == "bypass":
            return  # senza_sordino — unity gain

        # Determine cutoff frequency
        cutoff_hz = params.get("cutoff_hz", 0.0)
        cutoff_ratio = params.get("cutoff_ratio", 1.0)
        if cutoff_hz <= 0.0:
            cutoff_hz = cutoff_ratio * context.sample_rate * 0.4
        cutoff_hz = max(20.0, min(cutoff_hz, context.sample_rate * 0.49))
        resonance = params.get("resonance", 0.7)

        if atype == "lowpass":
            self._ensure_filter("lowpass_2p", cutoff_hz, resonance)
        elif atype == "highpass":
            self._ensure_filter("highpass_2p", cutoff_hz, resonance)
        else:
            self._ensure_filter("lowpass_2p", cutoff_hz, resonance)

        # Process stereo channels
        if self._filter_left is not None and self._filter_right is not None:
            from synth.primitives.filter import UltraFastResonantFilter

            # Use UltraFastResonantFilter for block processing when available
            # Fall back to per-sample biquad for simplicity
            for i in range(n):
                buf[i, 0] = self._filter_left.process(float(buf[i, 0]))
                buf[i, 1] = self._filter_right.process(float(buf[i, 1]))

        # Apply level scaling
        level = params.get("level", 1.0)
        if level != 1.0:
            buf[:, 0] *= level
            buf[:, 1] *= level

        # Sub-bass: mix in sub-oscillator
        if atype == "sub_osc" or params.get("sub_osc_mix", 0.0) > 0.0:
            mix = params.get("sub_osc_mix", 0.3)
            sub_freq = params.get("sub_freq", 40.0)
            t = np.arange(n, dtype=np.float32) / self.sample_rate
            sub = np.sin(2.0 * np.pi * sub_freq * t).astype(np.float32) * mix
            buf[:, 0] += sub
            buf[:, 1] += sub

    def reset(self) -> None:
        if self._filter_left is not None:
            self._filter_left.z1 = 0.0
            self._filter_left.z2 = 0.0
        if self._filter_right is not None:
            self._filter_right.z1 = 0.0
            self._filter_right.z2 = 0.0
