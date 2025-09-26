"""
Talk Wah effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np

from .base import BaseEffect


class TalkWahEffect(BaseEffect):
    """
    Talk Wah effect implementation.

    Wah-wah effect controlled by envelope follower for vocal-like filtering.
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)

        # Effect parameters
        self.sensitivity = 0.5  # Envelope sensitivity (0.0-1.0)
        self.resonance = 0.5    # Filter resonance (0.0-1.0)
        self.manual = 0.5       # Manual wah position (0.0-1.0)
        self.decay = 0.5        # Envelope decay time (0.0-1.0)
        self.wah_range = 0.5    # Wah frequency range (0.0-1.0)

        # Internal state
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0
        self._envelope = 0.0
        self._prev_input_level = 0.0
        self._current_freq = 500.0  # Current wah frequency
        self._sweep_direction = 1.0  # 1 = up, -1 = down

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process audio through talk wah effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get parameters
        sensitivity = self.sensitivity
        resonance = self.resonance
        manual = self.manual
        decay = self.decay
        wah_range = self.wah_range

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Update envelope follower
        attack_coeff = 0.01 * sensitivity
        release_coeff = 0.1 * decay

        if input_level > self._prev_input_level:
            # Attack
            self._envelope += (input_level - self._envelope) * attack_coeff
        else:
            # Release
            self._envelope += (input_level - self._envelope) * release_coeff

        # Calculate wah frequency
        # Manual control + envelope modulation
        manual_freq = 200 + manual * 2000  # 200-2200 Hz range
        envelope_mod = self._envelope * sensitivity * wah_range * 1000
        target_freq = manual_freq + envelope_mod

        # Smooth frequency changes
        freq_diff = target_freq - self._current_freq
        self._current_freq += freq_diff * 0.1  # Smooth transition

        # Clamp frequency
        self._current_freq = max(100, min(5000, self._current_freq))

        # Calculate filter coefficients for bandpass wah filter
        coeffs = self._calculate_wah_coefficients(self._current_freq, resonance)

        # Apply filter
        output = self._apply_biquad_filter(input_sample, coeffs)

        # Update state
        self._prev_input_level = input_level

        # Apply level
        return (output * self.level, output * self.level)

    def _reset_impl(self):
        """Reset talk wah effect state"""
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0
        self._envelope = 0.0
        self._prev_input_level = 0.0
        self._current_freq = 500.0  # Current wah frequency
        self._sweep_direction = 1.0  # 1 = up, -1 = down

    def _calculate_wah_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate wah filter coefficients (bandpass)"""
        # Normalize frequency
        w0 = 2 * math.pi * frequency / self.sample_rate

        # Q factor for wah (typically high Q for narrow peak)
        q = 2.0 + resonance * 8.0  # Q ranges from 2 to 10

        # Bandwidth in octaves
        bw = math.log2(1 + 1/(q * 2)) * 2

        # Calculate filter coefficients for bandpass
        alpha = math.sin(w0) / (2 * q)

        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        return {
            "b0": b0, "b1": b1, "b2": b2,
            "a0": a0, "a1": a1, "a2": a2
        }

    def _apply_biquad_filter(self, input_sample: float, coeffs: Dict[str, float]) -> float:
        """Apply biquad filter"""
        # Direct Form I implementation
        output = (coeffs["b0"]/coeffs["a0"]) * input_sample + \
                (coeffs["b1"]/coeffs["a0"]) * self._x1 + \
                (coeffs["b2"]/coeffs["a0"]) * self._x2 - \
                (coeffs["a1"]/coeffs["a0"]) * self._y1 - \
                (coeffs["a2"]/coeffs["a0"]) * self._y2

        # Update delay lines
        self._x2 = self._x1
        self._x1 = input_sample
        self._y2 = self._y1
        self._y1 = output

        return output


# Factory function for creating talk wah effect
def create_talk_wah_effect(sample_rate: int = 44100):
    """Create a talk wah effect instance"""
    return TalkWahEffect(sample_rate)


# Process function for integration with main effects system
def process_talk_wah_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through talk wah effect (for integration)"""
    effect = TalkWahEffect()
    # Set parameters from the params dict
    for param_name, value in params.items():
        effect.set_parameter(param_name, value)
    return effect.process_sample(left, right)
