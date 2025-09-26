"""
Chorus Effect Implementation

This module implements the XG Chorus effect with LFO modulation.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from .base import BaseEffect
from ..math.fast_approx import fast_math


class ChorusEffect(BaseEffect):
    """
    XG Chorus Effect implementation with dual LFO modulation.
    """

    __slots__ = ('rate', 'depth', 'feedback', 'delay', 'delay_lines', 'lfo_phases',
                 'lfo_rates', 'lfo_depths', 'write_indices', 'feedback_buffers')

    def __init__(self, sample_rate: int = 44100):
        """Initialize chorus effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.rate = 1.0      # LFO rate in Hz
        self.depth = 0.5     # Modulation depth (0.0-1.0)
        self.feedback = 0.3  # Feedback amount (0.0-1.0)
        self.level = 0.4     # Wet/dry mix (0.0-1.0)
        self.delay = 0.0     # Base delay in milliseconds

        # Internal state
        self.delay_lines = [np.zeros(4410) for _ in range(2)]  # 100ms delays
        self.lfo_phases = [0.0, 0.0]
        self.lfo_rates = [1.0, 0.5]
        self.lfo_depths = [0.5, 0.3]
        self.write_indices = [0, 0]
        self.feedback_buffers = [0.0, 0.0]


    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process chorus effect with dual LFO modulation.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Process left channel
        left_input = left

        # Update LFO phase
        self.lfo_phases[0] = (self.lfo_phases[0] + self.lfo_rates[0] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(self.delay * self.sample_rate / 1000.0)
        modulation = int(self.lfo_depths[0] * self.depth * self.sample_rate / 1000.0 * (1 + fast_math.fast_sin(self.lfo_phases[0])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(self.delay_lines[0]):
            total_delay = len(self.delay_lines[0]) - 1

        # Read from delay buffer
        read_index = (self.write_indices[0] - total_delay) % len(self.delay_lines[0])
        delayed_sample = self.delay_lines[0][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * self.feedback + self.feedback_buffers[0] * 0.2
        self.delay_lines[0][self.write_indices[0]] = left_input + feedback_sample

        # Update write index
        self.write_indices[0] = (self.write_indices[0] + 1) % len(self.delay_lines[0])
        self.feedback_buffers[0] = feedback_sample

        # Process right channel (similar but with phase offset)
        right_input = right

        # Update LFO phase
        self.lfo_phases[1] = (self.lfo_phases[1] + self.lfo_rates[1] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(self.delay * self.sample_rate / 1000.0)
        modulation = int(self.lfo_depths[1] * self.depth * self.sample_rate / 1000.0 * (1 + fast_math.fast_sin(self.lfo_phases[1])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(self.delay_lines[1]):
            total_delay = len(self.delay_lines[1]) - 1

        # Read from delay buffer
        read_index = (self.write_indices[1] - total_delay) % len(self.delay_lines[1])
        delayed_sample = self.delay_lines[1][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * self.feedback + self.feedback_buffers[1] * 0.2
        self.delay_lines[1][self.write_indices[1]] = right_input + feedback_sample

        # Update write index
        self.write_indices[1] = (self.write_indices[1] + 1) % len(self.delay_lines[1])
        self.feedback_buffers[1] = feedback_sample

        # Mix dry and wet signals
        return (
            left * (1.0 - self.level) + delayed_sample * self.level,
            right * (1.0 - self.level) + delayed_sample * self.level
        )

    def set_rate(self, rate_hz: float):
        """Set LFO rate in Hz"""
        self.rate = max(0.1, min(10.0, rate_hz))

    def set_depth(self, depth: float):
        """Set modulation depth (0.0-1.0)"""
        self.depth = max(0.0, min(1.0, depth))

    def set_feedback(self, feedback: float):
        """Set feedback amount (0.0-1.0)"""
        self.feedback = max(0.0, min(0.99, feedback))

    def set_delay(self, delay_ms: float):
        """Set base delay in milliseconds"""
        self.delay = max(0.0, min(50.0, delay_ms))

    def _reset_impl(self):
        """Reset chorus effect state"""
        self.delay_lines = [np.zeros(4410) for _ in range(2)]
        self.lfo_phases = [0.0, 0.0]
        self.lfo_rates = [1.0, 0.5]
        self.lfo_depths = [0.5, 0.3]
        self.write_indices = [0, 0]
        self.feedback_buffers = [0.0, 0.0]

    def __str__(self) -> str:
        """String representation"""
        return f"Chorus Effect (rate={self.rate:.1f}Hz, depth={self.depth:.2f}, level={self.level:.2f})"
