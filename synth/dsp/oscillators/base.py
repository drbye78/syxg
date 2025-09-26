"""
Oscillator Base Interface

This module provides the base interface for all oscillator implementations.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional


class OscillatorInterface(ABC):
    """
    Base interface for all oscillator implementations.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize oscillator.

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.frequency = 440.0
        self.amplitude = 1.0

    @abstractmethod
    def generate_samples(self, frequency: float, num_samples: int) -> np.ndarray:
        """
        Generate waveform samples.

        Args:
            frequency: Frequency in Hz
            num_samples: Number of samples to generate

        Returns:
            Array of waveform samples
        """
        pass

    @abstractmethod
    def reset(self):
        """Reset oscillator phase."""
        pass

    @abstractmethod
    def set_phase(self, phase: float):
        """Set oscillator phase."""
        pass

    @abstractmethod
    def get_phase(self) -> float:
        """Get current oscillator phase."""
        return self.phase

    def set_frequency(self, frequency: float):
        """Set oscillator frequency."""
        self.frequency = max(0.0, frequency)

    def set_amplitude(self, amplitude: float):
        """Set oscillator amplitude."""
        self.amplitude = amplitude

    def get_frequency(self) -> float:
        """Get oscillator frequency."""
        return self.frequency

    def get_amplitude(self) -> float:
        """Get oscillator amplitude."""
        return self.amplitude