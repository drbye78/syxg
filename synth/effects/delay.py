"""
Delay Effect Implementation

This module implements the XG Delay effect with feedback and stereo capabilities.
"""

import math
from typing import Dict, List, Tuple, Optional, Any

from .base import BaseEffect


class DelayEffect(BaseEffect):
    """
    XG Delay Effect implementation.

    Supports stereo delay with feedback and level control.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize delay effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.time = 500.0    # Delay time in milliseconds
        self.feedback = 0.3  # Feedback amount (0.0-1.0)
        self.level = 0.5     # Wet/dry mix (0.0-1.0)
        self.stereo = 0.5    # Stereo spread (0.0-1.0)

        # Internal state
        self._max_delay_samples = int(2.0 * sample_rate)  # 2 second max delay
        self._delay_buffer = [0.0] * self._max_delay_samples
        self._write_pos = 0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process delay effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Calculate delay in samples
        delay_samples = int(self.time * self.sample_rate / 1000.0)
        delay_samples = min(delay_samples, self._max_delay_samples - 1)

        # Read from delay buffer
        read_pos = (self._write_pos - delay_samples) % self._max_delay_samples
        delayed_sample = self._delay_buffer[int(read_pos)]

        # Apply feedback
        feedback_sample = delayed_sample * self.feedback

        # Mix input with feedback
        processed_sample = (left + right) / 2.0 + feedback_sample

        # Write to delay buffer
        self._delay_buffer[self._write_pos] = processed_sample
        self._write_pos = (self._write_pos + 1) % self._max_delay_samples

        # Mix dry and wet signals
        dry_left = left * (1.0 - self.level)
        dry_right = right * (1.0 - self.level)
        wet_left = delayed_sample * self.level * (1.0 - self.stereo)
        wet_right = delayed_sample * self.level * self.stereo

        return (dry_left + wet_left, dry_right + wet_right)

    def set_time(self, time_ms: float):
        """Set delay time in milliseconds"""
        self.time = max(1.0, min(2000.0, time_ms))

    def set_feedback(self, feedback: float):
        """Set feedback amount (0.0-1.0)"""
        self.feedback = max(0.0, min(0.99, feedback))

    def set_stereo(self, stereo: float):
        """Set stereo spread (0.0-1.0)"""
        self.stereo = max(0.0, min(1.0, stereo))

    def _reset_impl(self):
        """Reset delay effect state"""
        self._delay_buffer = [0.0] * self._max_delay_samples
        self._write_pos = 0

    def __str__(self) -> str:
        """String representation"""
        return f"Delay Effect (time={self.time:.1f}ms, feedback={self.feedback:.2f}, level={self.level:.2f})"
