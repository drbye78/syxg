"""Production phaser processor."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProductionPhaserProcessor:
    """
    Professional phaser implementation with modulated all-pass filters.

    Features:
    - Multi-stage all-pass filter chain
    - LFO modulation of filter frequencies
    - Feedback control
    - Stereo processing
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # All-pass filter chain (6 stages typical for phaser)
        self.allpass_stages = 6
        self.allpass_delays = [
            int(0.001 * self.sample_rate * (i + 1)) for i in range(self.allpass_stages)
        ]
        self.allpass_states = [
            {"delay_line": np.zeros(int(0.01 * self.sample_rate)), "write_pos": 0}
            for _ in range(self.allpass_stages)
        ]

        # LFO for modulation
        self.lfo_phase = 0.0
        self.lfo_rate = 1.0
        self.lfo_depth = 0.5

        # Feedback
        self.feedback = 0.3

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process sample through professional phaser."""
        with self.lock:
            self.lfo_rate = params.get("rate", 1.0)
            self.lfo_depth = params.get("depth", 0.5)
            self.feedback = params.get("feedback", 0.3)

            # Update LFO
            phase_increment = 2 * math.pi * self.lfo_rate / self.sample_rate
            self.lfo_phase = (self.lfo_phase + phase_increment) % (2 * math.pi)

            # Calculate modulation (sine wave centered on 1.0)
            modulation = 1.0 + math.sin(self.lfo_phase) * self.lfo_depth

            # Process through all-pass filter chain
            output = input_sample
            feedback_signal = 0.0

            for stage in range(self.allpass_stages):
                stage_state = self.allpass_stages[stage]
                delay_line = stage_state["delay_line"]
                write_pos = stage_state["write_pos"]

                # Modulated delay time
                base_delay = self.allpass_delays[stage]
                modulated_delay = int(base_delay * modulation)
                modulated_delay = max(1, min(modulated_delay, len(delay_line) - 1))

                # Read from delay line
                read_pos = (write_pos - modulated_delay) % len(delay_line)
                delayed = delay_line[int(read_pos)]

                # All-pass filter with feedback
                allpass_input = output + feedback_signal * self.feedback
                allpass_coeff = 0.5  # All-pass coefficient

                allpass_output = allpass_coeff * allpass_input + delayed
                feedback_signal = allpass_input - allpass_coeff * allpass_output

                # Write to delay line
                delay_line[write_pos] = allpass_output
                stage_state["write_pos"] = (write_pos + 1) % len(delay_line)

                output = allpass_output

            return output


