"""
Chorus Effect Implementation

This module implements the XG Chorus effect with LFO modulation.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from .base import BaseEffect


class ChorusEffect(BaseEffect):
    """
    XG Chorus Effect implementation with dual LFO modulation.
    """

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
        self._chorus_state = self._create_chorus_state()

    def _create_chorus_state(self) -> Dict[str, Any]:
        """Create initial chorus state"""
        return {
            "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms delays
            "lfo_phases": [0.0, 0.0],
            "lfo_rates": [1.0, 0.5],
            "lfo_depths": [0.5, 0.3],
            "write_indices": [0, 0],
            "feedback_buffers": [0.0, 0.0]
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process chorus effect with dual LFO modulation.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        state = self._chorus_state

        # Process left channel
        left_input = left

        # Update LFO phase
        state["lfo_phases"][0] = (state["lfo_phases"][0] + state["lfo_rates"][0] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(self.delay * self.sample_rate / 1000.0)
        modulation = int(state["lfo_depths"][0] * self.depth * self.sample_rate / 1000.0 * (1 + math.sin(state["lfo_phases"][0])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(state["delay_lines"][0]):
            total_delay = len(state["delay_lines"][0]) - 1

        # Read from delay buffer
        read_index = (state["write_indices"][0] - total_delay) % len(state["delay_lines"][0])
        delayed_sample = state["delay_lines"][0][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * self.feedback + state["feedback_buffers"][0] * 0.2
        state["delay_lines"][0][state["write_indices"][0]] = left_input + feedback_sample

        # Update write index
        state["write_indices"][0] = (state["write_indices"][0] + 1) % len(state["delay_lines"][0])
        state["feedback_buffers"][0] = feedback_sample

        # Process right channel (similar but with phase offset)
        right_input = right

        # Update LFO phase
        state["lfo_phases"][1] = (state["lfo_phases"][1] + state["lfo_rates"][1] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(self.delay * self.sample_rate / 1000.0)
        modulation = int(state["lfo_depths"][1] * self.depth * self.sample_rate / 1000.0 * (1 + math.sin(state["lfo_phases"][1])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(state["delay_lines"][1]):
            total_delay = len(state["delay_lines"][1]) - 1

        # Read from delay buffer
        read_index = (state["write_indices"][1] - total_delay) % len(state["delay_lines"][1])
        delayed_sample = state["delay_lines"][1][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * self.feedback + state["feedback_buffers"][1] * 0.2
        state["delay_lines"][1][state["write_indices"][1]] = right_input + feedback_sample

        # Update write index
        state["write_indices"][1] = (state["write_indices"][1] + 1) % len(state["delay_lines"][1])
        state["feedback_buffers"][1] = feedback_sample

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
        self._chorus_state = self._create_chorus_state()

    def __str__(self) -> str:
        """String representation"""
        return f"Chorus Effect (rate={self.rate:.1f}Hz, depth={self.depth:.2f}, level={self.level:.2f})"
