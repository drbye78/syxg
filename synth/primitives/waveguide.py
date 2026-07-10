"""
Digital waveguide synthesis implementation.

Provides the DigitalWaveguide class for physical modeling synthesis,
using delay lines and scattering junctions for realistic instrument simulation.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class DigitalWaveguide:
    """
    Digital waveguide synthesis implementation.

    Models wave propagation in acoustic systems using delay lines
    and scattering junctions for realistic instrument simulation.
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        """
        Initialize digital waveguide.

        Args:
            sample_rate: Audio sample rate in Hz
            max_delay_samples: Maximum delay line length
        """
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Delay lines for waveguide
        self.delay_line_left = np.zeros(max_delay_samples, dtype=np.float32)
        self.delay_line_right = np.zeros(max_delay_samples, dtype=np.float32)

        # Current delay positions
        self.delay_pos_left = 0
        self.delay_pos_right = 0

        # Delay lengths (set by excitation)
        self.delay_length_left = max_delay_samples // 2
        self.delay_length_right = max_delay_samples // 2

        # Scattering coefficients
        self.scattering_coeff = 0.5  # Reflection coefficient

        # Loop filter for decay
        self.loop_filter_coeff = 0.99  # Close to 1.0 for long sustain

        # Excitation state
        self.excitation_active = False
        self.excitation_samples: list[float] = []
        self.excitation_index = 0

    def set_frequency(self, frequency: float):
        """
        Set fundamental frequency by adjusting delay lengths.

        Args:
            frequency: Fundamental frequency in Hz
        """
        # Calculate delay length for fundamental frequency
        delay_samples = int(self.sample_rate / frequency)

        # Ensure within bounds
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        # Set symmetric delay for stereo
        self.delay_length_left = delay_samples
        self.delay_length_right = delay_samples

    def excite(self, excitation_type: str = "pluck", amplitude: float = 1.0):
        """
        Excite the waveguide with initial conditions.

        Args:
            excitation_type: Type of excitation ('pluck', 'strike', 'blow')
            amplitude: Excitation amplitude
        """
        if excitation_type == "pluck":
            # Karplus-Strong pluck excitation
            noise_samples = int(self.delay_length_left * 0.1)  # 10% of period
            excitation = np.random.uniform(-amplitude, amplitude, noise_samples)

            # Smooth excitation for more realistic pluck
            if len(excitation) > 1:
                excitation[1:] = excitation[:-1] * 0.5 + excitation[1:] * 0.5

        elif excitation_type == "strike":
            # Percussive strike (impulse)
            excitation = np.zeros(self.delay_length_left)
            excitation[0] = amplitude

        elif excitation_type == "blow":
            # Wind instrument excitation (noise with envelope)
            noise_samples = int(self.delay_length_left * 0.05)
            excitation = np.random.uniform(-amplitude, amplitude, noise_samples)
            envelope = np.linspace(1.0, 0.1, noise_samples)
            excitation *= envelope

        else:
            excitation = np.array([amplitude])

        self.excitation_samples = excitation.tolist()
        self.excitation_index = 0
        self.excitation_active = True

        # Initialize delay lines with excitation
        if len(excitation) > 0:
            fill_length = min(len(excitation), len(self.delay_line_left))
            self.delay_line_left[:fill_length] = excitation[:fill_length]
            self.delay_line_right[:fill_length] = excitation[:fill_length] * 0.8

    def process_sample(self) -> float:
        """
        Process one sample through the waveguide.

        Returns:
            Output sample value
        """
        left_in = self.delay_line_left[self.delay_pos_left]
        right_in = self.delay_line_right[self.delay_pos_right]

        # Scattering junction (simplified)
        left_reflection = left_in * self.scattering_coeff
        right_reflection = right_in * self.scattering_coeff

        # Waveguide loop with negative reflection for string
        new_left = -right_reflection * self.loop_filter_coeff
        new_right = -left_reflection * self.loop_filter_coeff

        # Add excitation if active
        if self.excitation_active and self.excitation_index < len(self.excitation_samples):
            excitation_value = self.excitation_samples[self.excitation_index]
            new_left += excitation_value
            new_right += excitation_value * 0.7
            self.excitation_index += 1

            if self.excitation_index >= len(self.excitation_samples):
                self.excitation_active = False

        # Store new values in delay lines
        self.delay_line_left[self.delay_pos_left] = new_left
        self.delay_line_right[self.delay_pos_right] = new_right

        # Update delay positions
        self.delay_pos_left = (self.delay_pos_left + 1) % self.delay_length_left
        self.delay_pos_right = (self.delay_pos_right + 1) % self.delay_length_right

        # Output is combination of delay line values
        output = (left_in + right_in) * 0.5

        return output

    def set_parameters(self, params: dict[str, Any]):
        """
        Set waveguide parameters.

        Args:
            params: Parameter dictionary
        """
        self.scattering_coeff = params.get("scattering_coeff", 0.5)
        self.loop_filter_coeff = params.get("loop_filter_coeff", 0.99)

        if "frequency" in params:
            self.set_frequency(params["frequency"])

    def is_active(self) -> bool:
        """
        Check if waveguide is still producing sound.

        Returns:
            True if waveguide has significant energy
        """
        left_energy = np.sum(np.abs(self.delay_line_left)) / len(self.delay_line_left)
        right_energy = np.sum(np.abs(self.delay_line_right)) / len(self.delay_line_right)

        return (left_energy + right_energy) > 0.001

    def reset(self):
        """Reset waveguide state."""
        self.delay_line_left.fill(0.0)
        self.delay_line_right.fill(0.0)
        self.delay_pos_left = 0
        self.delay_pos_right = 0
        self.excitation_active = False
        self.excitation_samples = []
        self.excitation_index = 0
