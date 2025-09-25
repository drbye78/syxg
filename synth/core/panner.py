"""
Stereo Panner implementation for XG synthesizer.
Provides stereo positioning with MIDI XG standard compliance.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from ..math.fast_approx import fast_math


class StereoPanner:
    """Class for panning sound in the stereo field"""
    def __init__(self, pan_position=0.5, sample_rate=44100):
        """
        Stereo panner initialization

        Args:
            pan_position: panning position (0.0 - left, 0.5 - center, 1.0 - right)
            sample_rate: sample rate
        """
        self.pan_position = pan_position
        self.sample_rate = sample_rate
        self.left_gain = 0.0
        self.right_gain = 0.0
        self._update_gains()

    def _update_gains(self):
        """Updating gain coefficients for left and right channels"""
        # Position normalization (0 = left, 1 = right)
        pan = max(0.0, min(1.0, self.pan_position))

        # Sinusoidal panning to preserve level
        angle = pan * math.pi / 2
        self.left_gain = fast_math.fast_cos(angle)
        self.right_gain = fast_math.fast_sin(angle)

    def set_pan(self, controller_value):
        """
        Setting panning via MIDI controller

        Args:
            controller_value: controller 10 value (0-127)
        """
        # MIDI controller 10: 0 = left, 64 = center, 127 = right
        self.pan_position = controller_value / 127.0
        self._update_gains()

    def set_pan_normalized(self, pan_normalized):
        """
        Setting normalized panning

        Args:
            pan_normalized: value from 0.0 (left) to 1.0 (right)
        """
        self.pan_position = max(0.0, min(1.0, pan_normalized))
        self._update_gains()

    def process(self, mono_sample):
        """
        Panning mono sample to stereo

        Args:
            mono_sample: input mono sample

        Returns:
            tuple (left_sample, right_sample)
        """
        return (mono_sample * self.left_gain, mono_sample * self.right_gain)

    def process_stereo(self, left_in, right_in):
        """
        Processing stereo sample with possible additional panning

        Args:
            left_in: left input sample
            right_in: right input sample

        Returns:
            tuple (left_out, right_out)
        """
        # When processing stereo sample, apply panning to each channel
        left_out = left_in * self.left_gain + right_in * (1.0 - self.right_gain)
        right_out = right_in * self.right_gain + left_in * (1.0 - self.left_gain)
        return (left_out, right_out)
