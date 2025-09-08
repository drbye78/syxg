"""
Distortion Effect Implementation

This module implements the XG Distortion effect with various distortion types
and parameter control.
"""

import math
from typing import Dict, List, Tuple, Optional, Any

from .base import BaseEffect


class DistortionEffect(BaseEffect):
    """
    XG Distortion Effect implementation.

    Supports multiple distortion types including soft clipping, hard clipping,
    asymmetric distortion, and symmetric distortion.
    """

    # Distortion types
    TYPE_SOFT_CLIPPING = 0
    TYPE_HARD_CLIPPING = 1
    TYPE_ASYMMETRIC = 2
    TYPE_SYMMETRIC = 3

    def __init__(self, sample_rate: int = 44100):
        """Initialize distortion effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.drive = 0.5  # 0.0-1.0
        self.tone = 0.5   # 0.0-1.0
        self.distortion_type = self.TYPE_SOFT_CLIPPING  # 0-3

        # Internal state
        self._prev_input = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process distortion effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get input sample (mono processing for distortion)
        input_sample = (left + right) / 2.0

        # Apply distortion based on type
        if self.distortion_type == self.TYPE_SOFT_CLIPPING:
            # Soft clipping using hyperbolic tangent
            output = math.tanh(input_sample * (1 + self.drive * 9.0))
        elif self.distortion_type == self.TYPE_HARD_CLIPPING:
            # Hard clipping
            output = max(-1.0, min(1.0, input_sample * (1 + self.drive * 9.0)))
        elif self.distortion_type == self.TYPE_ASYMMETRIC:
            # Asymmetric distortion (tube-like)
            biased = input_sample + self.drive * 0.1
            if biased > 0:
                output = 1.0 - math.exp(-biased * (1 + self.drive * 9.0))
            else:
                output = -1.0 + math.exp(biased * (1 + self.drive * 9.0))
        else:  # TYPE_SYMMETRIC
            # Symmetric distortion
            output = math.tanh(input_sample * (1 + self.drive * 9.0))

        # Apply tone control (simple EQ)
        if self.tone < 0.5:
            # More bass
            bass_boost = 1.0 + (0.5 - self.tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # More treble
            treble_boost = 1.0 + (self.tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        # Apply level
        output *= self.level

        # Store previous input for potential use in future enhancements
        self._prev_input = input_sample

        return (output, output)

    def set_drive(self, drive: float):
        """Set distortion drive level (0.0-1.0)"""
        self.drive = max(0.0, min(1.0, drive))

    def set_tone(self, tone: float):
        """Set distortion tone (0.0-1.0)"""
        self.tone = max(0.0, min(1.0, tone))

    def set_type(self, distortion_type: int):
        """Set distortion type (0-3)"""
        self.distortion_type = max(0, min(3, distortion_type))

    def _reset_impl(self):
        """Reset distortion effect state"""
        self._prev_input = 0.0

    @property
    def type_name(self) -> str:
        """Get current distortion type name"""
        type_names = ["Soft Clipping", "Hard Clipping", "Asymmetric", "Symmetric"]
        return type_names[self.distortion_type]

    def __str__(self) -> str:
        """String representation"""
        return f"Distortion Effect (type={self.type_name}, drive={self.drive:.2f}, tone={self.tone:.2f}, level={self.level:.2f})"
