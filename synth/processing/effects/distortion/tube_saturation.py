"""Tube saturation modeling for overdrive effects."""

from __future__ import annotations

import math
import threading

import numpy as np


class TubeSaturationProcessor:
    """
    Tube saturation modeling for overdrive effects.

    Models the non-linear characteristics of vacuum tubes including:
    - Soft clipping at high levels
    - Even harmonic generation
    - Asymmetrical transfer function
    - Frequency-dependent saturation
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Tube model parameters
        self.plate_voltage = 250.0  # V
        self.grid_bias = -1.5  # V
        self.mu = 100.0  # Amplification factor

        # State variables for smoothing
        self.last_input = 0.0
        self.last_output = 0.0

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, drive: float, tone: float, level: float) -> float:
        """Process sample through tube saturation model."""
        with self.lock:
            # Input scaling and biasing
            scaled_input = input_sample * (1.0 + drive * 4.0)  # Drive control
            biased_input = scaled_input + self.grid_bias

            # Tube transfer function approximation
            # Triode tube model: i = k * (v_g + v_gk)^1.5
            if biased_input >= 0:
                # Positive region - soft clipping
                output_current = 0.1 * (biased_input**1.5)
            else:
                # Negative region - asymmetric behavior
                output_current = 0.05 * (biased_input**1.5) * 0.7

            # Plate voltage limiting
            output_voltage = output_current * 1000.0  # Load resistor
            output_voltage = np.clip(output_voltage, -self.plate_voltage, self.plate_voltage)

            # Add even harmonics (tube characteristic)
            harmonic_content = 0.1 * math.sin(output_voltage * math.pi * 2)
            output_voltage += harmonic_content

            # Tone control (simple high-frequency rolloff)
            alpha = 1.0 / (1.0 + 2 * math.pi * 2000 * tone / self.sample_rate)
            filtered_output = alpha * output_voltage + (1 - alpha) * self.last_output
            self.last_output = filtered_output

            # Output level scaling
            return filtered_output * level * 0.5


