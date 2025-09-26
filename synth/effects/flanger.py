"""
Flanger effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np

from .base import BaseEffect


class FlangerEffect(BaseEffect):
    """
    Flanger effect implementation.

    Creates comb filtering effect by mixing signal with delayed version with LFO modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)

        # Effect parameters
        self.rate = 0.5      # LFO rate (0.0-1.0, maps to 0.1-10 Hz)
        self.depth = 0.5     # Modulation depth (0.0-1.0)
        self.feedback = 0.5  # Feedback amount (0.0-1.0)
        self.manual = 0.5    # Manual delay time (0.0-1.0, maps to 0.1-10 ms)
        self.waveform = 0.0  # LFO waveform (0.0-1.0, maps to different waveforms)

        # Internal state
        self._delay_buffer = [0.0] * int(self.sample_rate * 0.02)  # 20ms max delay
        self._buffer_pos = 0
        self._lfo_phase = 0.0
        self._feedback_buffer = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process audio through flanger effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get parameters
        rate = 0.1 + self.rate * 9.9  # 0.1-10 Hz
        depth = self.depth
        feedback = self.feedback
        manual = 0.1 + self.manual * 9.9  # 0.1-10 ms
        waveform = int(self.waveform * 3)  # 0-3 waveforms

        # Get input sample
        input_sample = (left + right) / 2.0

        # Update LFO
        self._lfo_phase += 2 * math.pi * rate / self.sample_rate

        # Generate LFO waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(self._lfo_phase)
        elif waveform == 1:  # Triangle
            phase = self._lfo_phase / (2 * math.pi)
            lfo_value = 1 - abs((phase % 1) * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(self._lfo_phase) > 0 else -1
        else:  # Sawtooth
            phase = self._lfo_phase / (2 * math.pi)
            lfo_value = (phase % 1) * 2 - 1

        # Calculate modulated delay
        base_delay_samples = int(manual * self.sample_rate / 1000.0)
        modulation_samples = int(depth * self.sample_rate / 1000.0 * (lfo_value + 1) / 2)
        total_delay_samples = base_delay_samples + modulation_samples

        # Clamp delay
        max_delay = len(self._delay_buffer) - 1
        total_delay_samples = min(total_delay_samples, max_delay)

        # Store input in delay buffer
        self._delay_buffer[self._buffer_pos] = input_sample + self._feedback_buffer * feedback
        self._buffer_pos = (self._buffer_pos + 1) % len(self._delay_buffer)

        # Read from delay buffer
        read_pos = (self._buffer_pos - total_delay_samples) % len(self._delay_buffer)
        delayed_sample = self._delay_buffer[int(read_pos)]

        # Update feedback buffer
        self._feedback_buffer = delayed_sample

        # Mix dry and wet signals
        output = input_sample + delayed_sample * depth

        # Apply level
        return (output * self.level, output * self.level)

    def _reset_impl(self):
        """Reset flanger effect state"""
        self._delay_buffer = [0.0] * int(self.sample_rate * 0.02)  # 20ms max delay
        self._buffer_pos = 0
        self._lfo_phase = 0.0
        self._feedback_buffer = 0.0


# Factory function for creating flanger effect
def create_flanger_effect(sample_rate: int = 44100):
    """Create a flanger effect instance"""
    return FlangerEffect(sample_rate)


# Process function for integration with main effects system
def process_flanger_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through flanger effect (for integration)"""
    effect = FlangerEffect()
    # Set parameters from the params dict
    for param_name, value in params.items():
        effect.set_parameter(param_name, value)
    return effect.process_sample(left, right)
