"""FM-X LFO oscillator for FM modulation."""

from __future__ import annotations

import math

import numpy as np

class FMXLFO:
    """
    FM-X Compatible LFO (Low Frequency Oscillator)

    Provides modulation sources for FM-X synthesis with multiple waveforms
    and assignable routing.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize FM-X LFO."""
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.frequency = 1.0  # Hz
        self.waveform = "sine"  # sine, triangle, sawtooth, square, random
        self.depth = 1.0
        self.enabled = True

        # Random LFO state
        self.random_value = 0.0
        self.random_hold_time = 0.0

    def set_parameters(self, frequency: float = 1.0, waveform: str = "sine", depth: float = 1.0):
        """Set LFO parameters."""
        self.frequency = max(0.01, min(20.0, frequency))  # 0.01-20 Hz range
        self.waveform = waveform
        self.depth = max(0.0, min(1.0, depth))

    def generate_sample(self) -> float:
        """Generate LFO sample."""
        if not self.enabled:
            return 0.0

        # Update phase
        phase_increment = 2.0 * math.pi * self.frequency / self.sample_rate
        self.phase += phase_increment
        if self.phase >= 2.0 * math.pi:
            self.phase -= 2.0 * math.pi

        # Generate waveform
        if self.waveform == "sine":
            value = math.sin(self.phase)
        elif self.waveform == "triangle":
            value = (
                2.0
                * abs(
                    2.0
                    * (
                        self.phase / (2.0 * math.pi)
                        - math.floor(self.phase / (2.0 * math.pi) + 0.5)
                    )
                )
                - 1.0
            )
        elif self.waveform == "sawtooth":
            value = 2.0 * (
                self.phase / (2.0 * math.pi) - math.floor(self.phase / (2.0 * math.pi) + 0.5)
            )
        elif self.waveform == "square":
            value = 1.0 if math.sin(self.phase) >= 0 else -1.0
        elif self.waveform == "random":
            # Sample and hold random
            self.random_hold_time -= 1.0 / self.sample_rate
            if self.random_hold_time <= 0:
                self.random_value = (np.random.random() - 0.5) * 2.0  # -1 to 1
                self.random_hold_time = 1.0 / self.frequency  # Hold for one cycle
            value = self.random_value
        else:
            value = math.sin(self.phase)  # Default to sine

        return value * self.depth

    def reset(self):
        """Reset LFO state."""
        self.phase = 0.0
        self.random_value = 0.0
        self.random_hold_time = 0.0


