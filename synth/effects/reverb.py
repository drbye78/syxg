"""
Reverb Effect Implementation

This module implements the XG Reverb effect using Schroeder algorithm.
"""

import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from .base import BaseEffect


class ReverbEffect(BaseEffect):
    """
    XG Reverb Effect implementation using Schroeder algorithm.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize reverb effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.time = 2.5      # Reverb time in seconds
        self.level = 0.6     # Reverb level (0.0-1.0)
        self.pre_delay = 20.0  # Pre-delay in milliseconds
        self.hf_damping = 0.5  # High frequency damping (0.0-1.0)
        self.density = 0.8    # Reverb density (0.0-1.0)

        # Internal state - Schroeder reverb
        self._reverb_state = self._create_reverb_state()

    def _create_reverb_state(self) -> Dict[str, Any]:
        """Create initial reverb state"""
        return {
            "allpass_buffers": [np.zeros(441) for _ in range(4)],
            "allpass_indices": [0] * 4,
            "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
            "comb_indices": [0] * 4,
            "early_reflection_buffer": np.zeros(441),
            "early_reflection_index": 0,
            "late_reflection_buffer": np.zeros(441 * 10),
            "late_reflection_index": 0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process reverb effect using Schroeder algorithm.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get input sample (mono for reverb)
        input_sample = (left + right) / 2.0

        state = self._reverb_state

        # Pre-delay
        pre_delay_samples = int(self.pre_delay * self.sample_rate / 1000.0)
        if pre_delay_samples >= len(state["early_reflection_buffer"]):
            pre_delay_samples = len(state["early_reflection_buffer"]) - 1

        # Write to pre-delay buffer
        state["early_reflection_buffer"][state["early_reflection_index"]] = input_sample
        state["early_reflection_index"] = (state["early_reflection_index"] + 1) % len(state["early_reflection_buffer"])

        # Read from pre-delay buffer
        pre_delay_index = (state["early_reflection_index"] - pre_delay_samples) % len(state["early_reflection_buffer"])
        pre_delay_sample = state["early_reflection_buffer"][int(pre_delay_index)]

        # Early reflections
        early_reflections = pre_delay_sample * 0.7

        # Comb filter density
        num_comb_filters = 4 + int(self.density * 4)
        comb_input = early_reflections

        # Process through comb filters
        for i in range(min(num_comb_filters, len(state["comb_buffers"]))):
            delay_length = int(self.time * self.sample_rate * (i + 1) / 8.0)
            if delay_length >= len(state["comb_buffers"][i]):
                delay_length = len(state["comb_buffers"][i]) - 1

            # Read from delay buffer
            read_index = (state["comb_indices"][i] - delay_length) % len(state["comb_buffers"][i])
            comb_sample = state["comb_buffers"][i][int(read_index)]

            # Calculate feedback
            feedback = 0.7 + (i * 0.05)

            # Write to delay buffer with feedback and damping
            state["comb_buffers"][i][state["comb_indices"][i]] = comb_input + comb_sample * feedback * (1.0 - self.hf_damping)
            state["comb_indices"][i] = (state["comb_indices"][i] + 1) % len(state["comb_buffers"][i])

            # Add to output
            comb_input += comb_sample * 0.9

        # Process through allpass filters for diffusion
        allpass_output = comb_input
        for i in range(len(state["allpass_buffers"])):
            delay_length = int(self.time * self.sample_rate * (i + 1) / 16.0)
            if delay_length >= len(state["allpass_buffers"][i]):
                delay_length = len(state["allpass_buffers"][i]) - 1

            # Read from delay buffer
            read_index = (state["allpass_indices"][i] - delay_length) % len(state["allpass_buffers"][i])
            allpass_sample = state["allpass_buffers"][i][int(read_index)]

            # Allpass filter
            g = 0.7  # Damping coefficient
            state["allpass_buffers"][i][state["allpass_indices"][i]] = allpass_output
            state["allpass_indices"][i] = (state["allpass_indices"][i] + 1) % len(state["allpass_buffers"][i])

            # Apply allpass formula
            allpass_output = -g * allpass_output + allpass_sample + g * allpass_sample

        # Apply level and mix with original
        reverb_output = allpass_output * self.level

        # Mix dry and wet
        dry_left = left * (1.0 - self.level)
        dry_right = right * (1.0 - self.level)
        wet_left = reverb_output * 0.7
        wet_right = reverb_output * 0.7

        return (dry_left + wet_left, dry_right + wet_right)

    def set_time(self, time_sec: float):
        """Set reverb time in seconds"""
        self.time = max(0.1, min(8.0, time_sec))

    def set_pre_delay(self, delay_ms: float):
        """Set pre-delay in milliseconds"""
        self.pre_delay = max(0.0, min(200.0, delay_ms))

    def set_hf_damping(self, damping: float):
        """Set high frequency damping (0.0-1.0)"""
        self.hf_damping = max(0.0, min(1.0, damping))

    def set_density(self, density: float):
        """Set reverb density (0.0-1.0)"""
        self.density = max(0.0, min(1.0, density))

    def _reset_impl(self):
        """Reset reverb effect state"""
        self._reverb_state = self._create_reverb_state()

    def __str__(self) -> str:
        """String representation"""
        return f"Reverb Effect (time={self.time:.1f}s, level={self.level:.2f}, pre_delay={self.pre_delay:.1f}ms)"
