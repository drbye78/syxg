"""
Square Oscillator

This module provides a square wave oscillator implementation.
"""

import numpy as np
from .base import OscillatorInterface


class SquareOscillator(OscillatorInterface):
    """
    Square wave oscillator.
    """

    def __init__(self, sample_rate: int = 44100, duty_cycle: float = 0.5):
        super().__init__(sample_rate)
        self.duty_cycle = duty_cycle
        self.waveform = "square"

    def generate_samples(self, frequency: float, num_samples: int) -> np.ndarray:
        if frequency <= 0:
            return np.zeros(num_samples)

        phase_increment = 2.0 * frequency / self.sample_rate
        start_phase = self.phase
        phases = np.arange(num_samples) * phase_increment + start_phase
        phases = phases % 2.0

        samples = np.where(phases < self.duty_cycle * 2.0, 1.0, -1.0)
        self.phase = (start_phase + num_samples * phase_increment) % 2.0
        return self.amplitude * samples

    def reset(self):
        self.phase = 0.0

    def set_phase(self, phase: float):
        self.phase = phase % 2.0

    def get_phase(self) -> float:
        return self.phase

    def set_duty_cycle(self, duty_cycle: float):
        self.duty_cycle = max(0.0, min(1.0, duty_cycle))