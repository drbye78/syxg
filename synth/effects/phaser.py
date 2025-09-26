"""
Phaser effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np

from .base import BaseEffect
from ..math.fast_approx import fast_math


class PhaserEffect(BaseEffect):
    """
    Phaser effect implementation.

    Creates notches in the frequency spectrum using allpass filters with LFO modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)

        # Effect parameters
        self.rate = 0.5      # LFO rate (0.0-1.0, maps to 0.1-10 Hz)
        self.depth = 0.5     # Modulation depth (0.0-1.0)
        self.feedback = 0.5  # Feedback amount (0.0-1.0)
        self.manual = 0.5    # Manual notch frequency (0.0-1.0, maps to 200-5000 Hz)
        self.stages = 0.5    # Number of allpass stages (0.0-1.0, maps to 2-6 stages)

        # Internal state
        self._allpass_filters = [
            {"x1": 0.0, "y1": 0.0} for _ in range(6)
        ]
        self._lfo_phase = 0.0
        self._current_depth = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process audio through phaser effect.

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
        manual = 200 + self.manual * 4800  # 200-5000 Hz
        stages = 2 + int(self.stages * 4)  # 2-6 stages

        # Get input sample
        input_sample = (left + right) / 2.0

        # Update LFO
        self._lfo_phase += 2 * math.pi * rate / self.sample_rate

        # Calculate modulation
        lfo_value = fast_math.fast_sin(self._lfo_phase)
        modulation = lfo_value * depth

        # Calculate notch frequencies
        base_freq = manual
        notch_freqs = []
        for i in range(stages):
            # Spread frequencies logarithmically
            freq_ratio = 1.0 + (i / (stages - 1)) * 0.5  # 1.0 to 1.5 ratio
            modulated_freq = base_freq * freq_ratio * (1.0 + modulation * 0.3)
            notch_freqs.append(modulated_freq)

        # Process through allpass filters
        output = input_sample
        feedback_signal = 0.0

        for i in range(min(stages, len(self._allpass_filters))):
            # Calculate allpass coefficients for this stage
            coeffs = self._calculate_allpass_coefficients(notch_freqs[i])

            # Apply allpass filter with feedback
            filter_input = output + feedback_signal * feedback
            filter_output = self._apply_allpass_filter(filter_input, coeffs, self._allpass_filters[i])

            # Update feedback signal
            feedback_signal = filter_output

            # Mix with original for phaser effect
            output = output + filter_output * 0.5

        # Apply level
        return (output * self.level, output * self.level)

    def _reset_impl(self):
        """Reset phaser effect state"""
        self._allpass_filters = [
            {"x1": 0.0, "y1": 0.0} for _ in range(6)
        ]
        self._lfo_phase = 0.0
        self._current_depth = 0.0

    def _calculate_allpass_coefficients(self, frequency: float) -> Dict[str, float]:
        """Calculate allpass filter coefficients"""
        # Normalize frequency
        w0 = 2 * math.pi * frequency / self.sample_rate

        # Allpass filter with Q=1 (maximally flat)
        q = 1.0
        alpha = fast_math.fast_sin(w0) / (2 * q)

        b0 = 1 - alpha
        b1 = -2 * fast_math.fast_cos(w0)
        b2 = 1 + alpha
        a0 = 1 + alpha
        a1 = -2 * fast_math.fast_cos(w0)
        a2 = 1 - alpha

        return {
            "b0": b0, "b1": b1, "b2": b2,
            "a0": a0, "a1": a1, "a2": a2
        }

    def _apply_allpass_filter(self, input_sample: float, coeffs: Dict[str, float], filter_state: Dict[str, Any]) -> float:
        """Apply allpass filter"""
        # Direct Form I implementation
        output = (coeffs["b0"]/coeffs["a0"]) * input_sample + \
                (coeffs["b1"]/coeffs["a0"]) * filter_state["x1"] - \
                (coeffs["a1"]/coeffs["a0"]) * filter_state["y1"] + \
                (coeffs["b2"]/coeffs["a0"]) * filter_state["x1"] - \
                (coeffs["a2"]/coeffs["a0"]) * filter_state["y1"]

        # Update delay lines
        filter_state["x1"] = input_sample
        filter_state["y1"] = output

        return output


# Factory function for creating phaser effect
def create_phaser_effect(sample_rate: int = 44100):
    """Create a phaser effect instance"""
    return PhaserEffect(sample_rate)


# Process function for integration with main effects system
def process_phaser_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through phaser effect (for integration)"""
    effect = PhaserEffect()
    # Set parameters from the params dict
    for param_name, value in params.items():
        effect.set_parameter(param_name, value)
    return effect.process_sample(left, right)
