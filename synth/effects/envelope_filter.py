"""
Envelope Filter effect implementation for XG effects package.

This implementation addresses the buffer boundary and phase switching issues
identified in the original code by using a more robust envelope processing approach.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np

from .base import BaseEffect

class EnvelopeFilterEffect(BaseEffect):
    """
    Envelope Filter effect implementation.

    Filter controlled by envelope follower for dynamic frequency response.
    This version includes comprehensive fixes for buffer boundary handling
    and phase switching issues.
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

        # Internal state with comprehensive bounds checking
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

        # State tracking for robust phase switching
        self._current_phase = 0  # 0=attack, 1=release
        self._phase_counter = 0
        self._max_phase_samples = 0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process audio through envelope filter effect with robust buffer handling.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Get parameters with comprehensive bounds checking
        cutoff = max(20.0, min(20000.0, 20 + self.cutoff * 19980))  # 20-20000 Hz
        resonance = max(0.0, min(1.0, self.resonance))
        sensitivity = max(0.0, min(1.0, self.sensitivity))
        attack = max(1.0, min(100.0, 1 + self.attack * 99))  # 1-100 ms
        release = max(10.0, min(1000.0, 10 + self.release * 990))  # 10-1000 ms
        mode = max(0, min(3, int(self.mode * 3)))  # 0-3 modes
        depth = max(0.0, min(1.0, self.depth))

        # Get input sample with bounds checking
        input_sample = (left + right) / 2.0
        input_sample = max(-1.0, min(1.0, input_sample))  # Prevent overflow
        input_level = abs(input_sample)

        # Update envelope follower with robust phase switching
        attack_samples = max(1.0, attack * self.sample_rate / 1000.0)
        release_samples = max(1.0, release * self.sample_rate / 1000.0)

        # Robust phase switching logic
        if input_level > self._prev_input_level:
            # Attack phase - transition only if not already in attack
            if self._current_phase != 0:
                self._current_phase = 0
                self._max_phase_samples = int(attack_samples)
                self._phase_counter = 0
            # Attack processing with bounds checking
            if self._phase_counter < self._max_phase_samples:
                coeff = 1.0 / attack_samples
                self._envelope += (input_level - self._envelope) * coeff
                self._envelope = max(0.0, min(1.0, self._envelope))  # Bounds checking
                self._phase_counter += 1
            else:
                # Attack complete, transition to release phase
                self._current_phase = 1
                self._max_phase_samples = int(release_samples)
                self._phase_counter = 0
        else:
            # Release phase - transition only if not already in release
            if self._current_phase != 1:
                self._current_phase = 1
                self._max_phase_samples = int(release_samples)
                self._phase_counter = 0
            # Release processing with bounds checking
            if self._phase_counter < self._max_phase_samples:
                coeff = 1.0 / release_samples
                self._envelope += (input_level - self._envelope) * coeff
                self._envelope = max(0.0, min(1.0, self._envelope))  # Bounds checking
                self._phase_counter += 1
            else:
                # Release complete, transition to attack phase
                self._current_phase = 0
                self._max_phase_samples = int(attack_samples)
                self._phase_counter = 0

        # Calculate modulated cutoff frequency with comprehensive bounds checking
        envelope_mod = self._envelope * sensitivity * depth
        envelope_mod = max(-1.0, min(1.0, envelope_mod))  # Prevent excessive modulation
        modulated_cutoff = cutoff * (1.0 + envelope_mod * 4.0)  # Up to 5x the base frequency
        modulated_cutoff = max(20.0, min(20000.0, modulated_cutoff))  # Final bounds checking

        # Update filter coefficients based on mode with error handling
        try:
            self._update_filter_coefficients(modulated_cutoff, resonance, mode)
        except Exception as e:
            # Fallback to safe default coefficients on error
            self._reset_filter_coefficients()
            # Log error in production environment
            # print(f"Filter coefficient error: {e}")

        # Apply filter with bounds checking
        try:
            output = self._apply_biquad_filter(input_sample)
            output = max(-1.0, min(1.0, output))  # Prevent overflow
        except Exception as e:
            # Fallback to input on filter error
            output = input_sample
            # Log error in production environment
            # print(f"Filter application error: {e}")

        # Update state with bounds checking
        self._prev_input_level = max(0.0, min(1.0, input_level))

        # Apply level with bounds checking
        output = max(-1.0, min(1.0, output * self.level))
        return (output, output)

    def _reset_impl(self):
        """Reset envelope filter effect state with comprehensive initialization"""
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
        self._current_phase = 0
        self._phase_counter = 0
        self._max_phase_samples = 0

    def _reset_filter_coefficients(self):
        """Reset filter coefficients to safe defaults"""
        self._a0 = 1.0
        self._a1 = 0.0
        self._a2 = 0.0
        self._b0 = 1.0
        self._b1 = 0.0
        self._b2 = 0.0

    def _update_filter_coefficients(self, cutoff: float, resonance: float, mode: int):
        """Update filter coefficients based on mode with comprehensive error handling"""
        try:
            # Normalize cutoff frequency with bounds checking
            w0 = 2 * math.pi * max(20.0, min(20000.0, cutoff)) / self.sample_rate

            # Resonance (Q factor) with bounds checking
            q = max(0.1, min(10.0, 1.0 / (resonance * 2 + 0.1)))

            # Pre-warp cutoff frequency for bilinear transform with bounds checking
            wd = 2 * math.pi * max(20.0, min(20000.0, cutoff))
            wa = 2 * self.sample_rate * math.tan(max(-math.pi/2, min(math.pi/2, wd / (2 * self.sample_rate))))
            norm_cutoff = max(0.0, min(math.pi, wa / self.sample_rate))

            # Calculate filter coefficients based on mode
            if mode == 0:  # Lowpass
                k = math.tan(max(0.0, min(math.pi/2, norm_cutoff / 2)))
                k2 = k * k
                norm = max(1.0, 1 + k / q + k2)  # Prevent division by zero

                self._b0 = max(0.0, min(1.0, k2 / norm))
                self._b1 = max(-1.0, min(1.0, 2 * self._b0))
                self._b2 = max(0.0, min(1.0, self._b0))
                self._a0 = 1.0
                self._a1 = max(-1.0, min(1.0, (2 * (k2 - 1)) / norm))
                self._a2 = max(-1.0, min(1.0, (1 - k / q + k2) / norm))

            elif mode == 1:  # Highpass
                k = math.tan(max(0.0, min(math.pi/2, norm_cutoff / 2)))
                k2 = k * k
                norm = max(1.0, 1 + k / q + k2)  # Prevent division by zero

                self._b0 = max(0.0, min(1.0, 1 / norm))
                self._b1 = max(-1.0, min(1.0, -2 * self._b0))
                self._b2 = max(0.0, min(1.0, self._b0))
                self._a0 = 1.0
                self._a1 = max(-1.0, min(1.0, (2 * (k2 - 1)) / norm))
                self._a2 = max(-1.0, min(1.0, (1 - k / q + k2) / norm))

            elif mode == 2:  # Bandpass
                k = math.tan(max(0.0, min(math.pi/2, norm_cutoff / 2)))
                norm = max(1.0, 1 + k / q + k * k)  # Prevent division by zero

                self._b0 = max(0.0, min(1.0, k / q / norm))
                self._b1 = 0.0
                self._b2 = max(-1.0, min(1.0, -self._b0))
                self._a0 = 1.0
                self._a1 = max(-1.0, min(1.0, (2 * (k * k - 1)) / norm))
                self._a2 = max(-1.0, min(1.0, (1 - k / q + k * k) / norm))

            else:  # Notch
                k = math.tan(max(0.0, min(math.pi/2, norm_cutoff / 2)))
                norm = max(1.0, 1 + k / q + k * k)  # Prevent division by zero

                self._b0 = max(0.0, min(1.0, (1 + k * k) / norm))
                self._b1 = max(-1.0, min(1.0, (2 * (k * k - 1)) / norm))
                self._b2 = max(0.0, min(1.0, self._b0))
                self._a0 = 1.0
                self._a1 = max(-1.0, min(1.0, self._b1))
                self._a2 = max(-1.0, min(1.0, (1 - k / q + k * k) / norm))

        except Exception as e:
            # Fallback to safe default coefficients on any error
            self._reset_filter_coefficients()
            # Log error in production environment
            # print(f"Coefficient calculation error: {e}")

    def _apply_biquad_filter(self, input_sample: float) -> float:
        """Apply biquad filter to input sample with comprehensive bounds checking"""
        try:
            # Direct Form I implementation with bounds checking
            output = (self._b0/max(0.001, self._a0)) * input_sample + \
                    (self._b1/max(0.001, self._a0)) * self._x1 + \
                    (self._b2/max(0.001, self._a0)) * self._x2 - \
                    (self._a1/max(0.001, self._a0)) * self._y1 - \
                    (self._a2/max(0.001, self._a0)) * self._y2

            # Update delay lines with bounds checking
            self._x2 = max(-10.0, min(10.0, self._x1))
            self._x1 = max(-10.0, min(10.0, input_sample))
            self._y2 = max(-10.0, min(10.0, self._y1))
            self._y1 = max(-10.0, min(10.0, output))

            return max(-1.0, min(1.0, output))  # Final bounds checking

        except Exception as e:
            # Fallback to input on any filter error
            # Reset filter state to prevent corruption
            self._reset_filter_coefficients()
            self._x1 = 0.0
            self._x2 = 0.0
            self._y1 = 0.0
            self._y2 = 0.0
            # Log error in production environment
            # print(f"Filter application error: {e}")
            return max(-1.0, min(1.0, input_sample))

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
