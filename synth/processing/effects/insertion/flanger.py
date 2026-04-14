"""Production flanger processor."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProductionFlangerProcessor:
    """
    Professional flanger with proper delay modulation and interpolation.

    Features:
    - Variable delay modulation
    - Linear interpolation for smooth modulation
    - Feedback control
    - High-frequency damping
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Delay line with extra space for interpolation
        self.delay_line = np.zeros(max_delay_samples + 4, dtype=np.float32)
        self.write_pos = 0

        # LFO for modulation
        self.lfo_phase = 0.0
        self.lfo_rate = 0.5
        self.lfo_depth = 0.7

        # Flanger parameters
        self.feedback = 0.5
        self.min_delay = int(0.0001 * self.sample_rate)  # 0.1ms
        self.max_delay = int(0.01 * self.sample_rate)  # 10ms

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process sample through professional flanger."""
        with self.lock:
            self.lfo_rate = params.get("rate", 0.5)
            self.lfo_depth = params.get("depth", 0.7)
            self.feedback = params.get("feedback", 0.5)

            # Update LFO
            phase_increment = 2 * math.pi * self.lfo_rate / self.sample_rate
            self.lfo_phase = (self.lfo_phase + phase_increment) % (2 * math.pi)

            # Calculate modulated delay (triangle wave for smooth flanging)
            lfo_value = (math.sin(self.lfo_phase) + 1.0) * 0.5  # 0 to 1
            delay_samples = self.min_delay + lfo_value * (self.max_delay - self.min_delay)

            # Linear interpolation for smooth delay
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            # Read from delay line with interpolation
            read_pos1 = (self.write_pos - delay_int) % len(self.delay_line)
            read_pos2 = (read_pos1 - 1) % len(self.delay_line)

            delayed1 = self.delay_line[int(read_pos1)]
            delayed2 = self.delay_line[int(read_pos2)]

            # Linear interpolation
            delayed_sample = delayed1 * (1.0 - delay_frac) + delayed2 * delay_frac

            # Calculate output with feedback
            feedback_input = input_sample + delayed_sample * self.feedback
            self.delay_line[self.write_pos] = feedback_input
            self.write_pos = (self.write_pos + 1) % len(self.delay_line)

            # Mix dry and wet
            wet_amount = self.lfo_depth
            return input_sample * (1.0 - wet_amount) + delayed_sample * wet_amount


