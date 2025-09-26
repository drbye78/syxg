"""
Sine Oscillator

This module provides a sine wave oscillator implementation.
"""

import numpy as np
from typing import Optional
from .base import OscillatorInterface


class SineOscillator(OscillatorInterface):
    """
    Sine wave oscillator.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize sine oscillator.

        Args:
            sample_rate: Sample rate in Hz
        """
        super().__init__(sample_rate)
        self.waveform = "sine"

    def generate_samples(self, frequency: float, num_samples: int) -> np.ndarray:
        """
        Generate sine wave samples.

        Args:
            frequency: Frequency in Hz
            num_samples: Number of samples to generate

        Returns:
            Array of sine wave samples
        """
        if frequency <= 0:
            return np.zeros(num_samples)

        # Calculate phase increment per sample
        phase_increment = 2.0 * np.pi * frequency / self.sample_rate

        # Generate phase
        start_phase = self.phase
        phases = np.arange(num_samples) * phase_increment + start_phase

        # Generate sine wave
        samples = self.amplitude * np.sin(phases)

        # Update phase for next call
        self.phase = (start_phase + num_samples * phase_increment) % (2.0 * np.pi)

        return samples

    def reset(self):
        """Reset oscillator phase."""
        self.phase = 0.0

    def set_phase(self, phase: float):
        """Set oscillator phase."""
        self.phase = phase % (2.0 * np.pi)

    def get_phase(self) -> float:
        """Get current oscillator phase."""
        return self.phase