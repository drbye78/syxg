"""Multi-stage distortion processor for fuzz and guitar distortion."""

from __future__ import annotations

import math
import threading


class MultiStageDistortionProcessor:
    """
    Multi-stage distortion processor for fuzz and guitar distortion.

    Features:
    - Multiple gain stages with clipping
    - Inter-stage filtering
    - Octave fuzz characteristics
    - Sustain modeling
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Multiple distortion stages
        self.stages = 3
        self.stage_gain = 2.0
        self.stage_clipping = 0.8

        # Inter-stage filtering
        self.stage_filters = [0.0] * self.stages

        # Octave generator for fuzz
        self.octave_phase = 0.0

        self.lock = threading.RLock()

    def process_sample(
        self, input_sample: float, drive: float, tone: float, level: float, fuzz_mode: bool = False
    ) -> float:
        """Process sample through multi-stage distortion."""
        with self.lock:
            # Input gain staging
            signal = input_sample * (1.0 + drive * 8.0)

            # Process through stages
            for stage in range(self.stages):
                # Asymmetric clipping for each stage
                if signal > self.stage_clipping:
                    signal = self.stage_clipping + (signal - self.stage_clipping) * 0.1
                elif signal < -self.stage_clipping:
                    signal = -self.stage_clipping + (signal + self.stage_clipping) * 0.3

                # Stage gain
                signal *= self.stage_gain

                # Inter-stage filtering (simple low-pass)
                alpha = 0.1 + tone * 0.4  # Tone control
                signal = alpha * signal + (1 - alpha) * self.stage_filters[stage]
                self.stage_filters[stage] = signal

            # Fuzz octave generation
            if fuzz_mode:
                # Rectify and octave shift for fuzz characteristics
                rectified = abs(signal)
                octave_signal = 0.0

                # Simple octave generation through waveform folding
                if rectified > 0.5:
                    octave_signal = math.sin(self.octave_phase) * 0.3
                    self.octave_phase += math.pi * 2 * (rectified * 2.0) / self.sample_rate
                    self.octave_phase %= math.pi * 2

                signal += octave_signal

            # Final tone shaping (high-cut filter)
            cutoff = 1000 + tone * 4000  # 1kHz to 5kHz
            alpha = 1.0 / (1.0 + 2 * math.pi * cutoff / self.sample_rate)
            signal = alpha * signal + (1 - alpha) * self.stage_filters[-1]

            return signal * level * 0.3  # Conservative output level


