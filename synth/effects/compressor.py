"""
Compressor Effect Implementation

This module implements the XG Compressor effect with threshold, ratio, attack, and release controls.
"""

import math
from typing import Dict, List, Tuple, Optional, Any

from .base import BaseEffect


class CompressorEffect(BaseEffect):
    """
    XG Compressor Effect implementation with full parameter control.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize compressor effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.threshold = -20.0  # Threshold in dB (-60 to 0)
        self.ratio = 4.0        # Compression ratio (1:1 to 20:1)
        self.attack = 10.0      # Attack time in milliseconds
        self.release = 100.0    # Release time in milliseconds

        # Internal state
        self._gain = 1.0
        self._envelope = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process compressor effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get input level (mono processing for compressor)
        input_sample = (left + right) / 2.0
        input_level_db = 20.0 * math.log10(abs(input_sample) + 1e-10)

        # Calculate desired gain
        if input_level_db > self.threshold:
            # Above threshold - apply compression
            over_threshold = input_level_db - self.threshold
            gain_reduction_db = over_threshold * (1.0 - 1.0/self.ratio)
            desired_gain_db = -gain_reduction_db
        else:
            # Below threshold - no compression
            desired_gain_db = 0.0

        desired_gain_linear = 10.0 ** (desired_gain_db / 20.0)

        # Smooth gain changes
        if desired_gain_linear < self._gain:
            # Attack phase
            attack_coeff = 1.0 / (self.attack * self.sample_rate / 1000.0)
            self._gain = self._gain * (1.0 - attack_coeff) + desired_gain_linear * attack_coeff
        else:
            # Release phase
            release_coeff = 1.0 / (self.release * self.sample_rate / 1000.0)
            self._gain = self._gain * (1.0 - release_coeff) + desired_gain_linear * release_coeff

        # Apply gain
        output = input_sample * self._gain

        return (output, output)

    def set_threshold(self, threshold_db: float):
        """Set threshold in dB (-60 to 0)"""
        self.threshold = max(-60.0, min(0.0, threshold_db))

    def set_ratio(self, ratio: float):
        """Set compression ratio (1:1 to 20:1)"""
        self.ratio = max(1.0, min(20.0, ratio))

    def set_attack(self, attack_ms: float):
        """Set attack time in milliseconds"""
        self.attack = max(0.1, min(100.0, attack_ms))

    def set_release(self, release_ms: float):
        """Set release time in milliseconds"""
        self.release = max(1.0, min(1000.0, release_ms))

    def _reset_impl(self):
        """Reset compressor effect state"""
        self._gain = 1.0
        self._envelope = 0.0

    def __str__(self) -> str:
        """String representation"""
        return f"Compressor Effect (threshold={self.threshold:.1f}dB, ratio={self.ratio:.1f}:1, attack={self.attack:.1f}ms, release={self.release:.1f}ms)"
