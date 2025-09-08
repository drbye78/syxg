"""
Envelope Filter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np

from .base import BaseEffect


class EnvelopeFilterEffect(BaseEffect):
    """
    Envelope Filter effect implementation.

    Filter controlled by envelope follower for dynamic frequency response.
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)

        # Effect parameters
        self.cutoff = 0.5      # Base cutoff frequency (0.0-1.0, maps to 20-20000 Hz)
        self.resonance = 0.5   # Filter resonance (0.0-1.0)
        self.sensitivity = 0.5 # Envelope sensitivity (0.0-1.0)
        self.attack = 0.5      # Envelope attack time (0.0-1.0, maps to 1-100 ms)
        self.release = 0.5     # Envelope release time (0.0-1.0, maps to 10-1000 ms)
        self.mode = 0.0        # Filter mode (0.0-1.0, maps to different filter types)
        self.depth = 0.5       # Modulation depth (0.0-1.0)

        # Internal state
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0
        self._envelope = 0.0
        self._prev_input_level = 0.0
        self._a0 = 1.0
        self._a1 = 0.0
        self._a2 = 0.0
        self._b0 = 1.0
        self._b1 = 0.0
        self._b2 = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process audio through envelope filter effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get parameters
        cutoff = 20 + self.cutoff * 19980  # 20-20000 Hz
        resonance = self.resonance
        sensitivity = self.sensitivity
        attack = 1 + self.attack * 99  # 1-100 ms
        release = 10 + self.release * 990  # 10-1000 ms
        mode = int(self.mode * 3)  # 0-3 modes
        depth = self.depth

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Update envelope follower
        attack_samples = attack * self.sample_rate / 1000.0
        release_samples = release * self.sample_rate / 1000.0

        if input_level > self._prev_input_level:
            # Attack
            coeff = 1.0 / attack_samples
            self._envelope += (input_level - self._envelope) * coeff
        else:
            # Release
            coeff = 1.0 / release_samples
            self._envelope += (input_level - self._envelope) * coeff

        # Calculate modulated cutoff frequency
        envelope_mod = self._envelope * sensitivity * depth
        modulated_cutoff = cutoff * (1.0 + envelope_mod * 4.0)  # Up to 5x the base frequency

        # Clamp cutoff frequency
        modulated_cutoff = max(20, min(20000, modulated_cutoff))

        # Update filter coefficients based on mode
        self._update_filter_coefficients(modulated_cutoff, resonance, mode)

        # Apply filter
        output = self._apply_biquad_filter(input_sample)

        # Update state
        self._prev_input_level = input_level

        # Apply level
        return (output * self.level, output * self.level)

    def _reset_impl(self):
        """Reset envelope filter effect state"""
        self._x1 = 0.0
        self._x2 = 0.0
        self._y1 = 0.0
        self._y2 = 0.0
        self._envelope = 0.0
        self._prev_input_level = 0.0
        self._a0 = 1.0
        self._a1 = 0.0
        self._a2 = 0.0
        self._b0 = 1.0
        self._b1 = 0.0
        self._b2 = 0.0

    def _update_filter_coefficients(self, cutoff: float, resonance: float, mode: int):
        """Update filter coefficients based on mode"""
        # Normalize cutoff frequency
        w0 = 2 * math.pi * cutoff / self.sample_rate

        # Resonance (Q factor)
        q = 1.0 / (resonance * 2 + 0.1)

        # Pre-warp cutoff frequency for bilinear transform
        wd = 2 * math.pi * cutoff
        wa = 2 * self.sample_rate * math.tan(wd / (2 * self.sample_rate))
        norm_cutoff = wa / self.sample_rate

        # Calculate filter coefficients based on mode
        if mode == 0:  # Lowpass
            k = math.tan(norm_cutoff / 2)
            k2 = k * k
            norm = 1 + k / q + k2

            self._b0 = k2 / norm
            self._b1 = 2 * self._b0
            self._b2 = self._b0
            self._a0 = 1
            self._a1 = (2 * (k2 - 1)) / norm
            self._a2 = (1 - k / q + k2) / norm

        elif mode == 1:  # Highpass
            k = math.tan(norm_cutoff / 2)
            k2 = k * k
            norm = 1 + k / q + k2

            self._b0 = 1 / norm
            self._b1 = -2 * self._b0
            self._b2 = self._b0
            self._a0 = 1
            self._a1 = (2 * (k2 - 1)) / norm
            self._a2 = (1 - k / q + k2) / norm

        elif mode == 2:  # Bandpass
            k = math.tan(norm_cutoff / 2)
            norm = 1 + k / q + k * k

            self._b0 = k / q / norm
            self._b1 = 0
            self._b2 = -self._b0
            self._a0 = 1
            self._a1 = (2 * (k * k - 1)) / norm
            self._a2 = (1 - k / q + k * k) / norm

        else:  # Notch
            k = math.tan(norm_cutoff / 2)
            norm = 1 + k / q + k * k

            self._b0 = (1 + k * k) / norm
            self._b1 = (2 * (k * k - 1)) / norm
            self._b2 = self._b0
            self._a0 = 1
            self._a1 = self._b1
            self._a2 = (1 - k / q + k * k) / norm

    def _apply_biquad_filter(self, input_sample: float) -> float:
        """Apply biquad filter to input sample"""
        # Direct Form I implementation
        output = (self._b0/self._a0) * input_sample + \
                (self._b1/self._a0) * self._x1 + \
                (self._b2/self._a0) * self._x2 - \
                (self._a1/self._a0) * self._y1 - \
                (self._a2/self._a0) * self._y2

        # Update delay lines
        self._x2 = self._x1
        self._x1 = input_sample
        self._y2 = self._y1
        self._y1 = output

        return output


# Factory function for creating envelope filter effect
def create_envelope_filter_effect(sample_rate: int = 44100):
    """Create an envelope filter effect instance"""
    return EnvelopeFilterEffect(sample_rate)


# Process function for integration with main effects system
def process_envelope_filter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through envelope filter effect (for integration)"""
    effect = EnvelopeFilterEffect()
    # Set parameters from the params dict
    for param_name, value in params.items():
        effect.set_parameter(param_name, value)
    return effect.process_sample(left, right)
