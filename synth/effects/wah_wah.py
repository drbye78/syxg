"""
XG Wah Wah Effect - Classic Auto-Wah Implementation

This module implements the classic Wah Wah effect as an XG insertion effect.
The Wah Wah effect is a classic guitar effect that creates a talking-like sound
by sweeping a bandpass filter across the frequency spectrum.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from .base import BaseEffect
from ..math.fast_approx import fast_math


class WahWahEffect(BaseEffect):
    """
    XG Wah Wah Effect - Classic bandpass filter sweep effect.

    This effect implements the classic Wah Wah sound by sweeping a bandpass
    filter through the frequency spectrum, creating the characteristic
    "wah" sound. The effect can be controlled manually or automatically.

    XG Effect Type: 18 (Wah Wah)
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize Wah Wah effect.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(sample_rate)

        # Wah Wah filter parameters
        self.center_freq = 1000.0  # Center frequency in Hz
        self.bandwidth = 2000.0    # Filter bandwidth in Hz
        self.resonance = 2.0       # Filter resonance (Q factor)

        # LFO for automatic wah (when not using envelope follower)
        self.lfo_rate = 2.0        # LFO rate in Hz
        self.lfo_depth = 0.7       # LFO depth (0.0-1.0)
        self.lfo_phase = 0.0       # LFO phase accumulator

        # Envelope follower parameters
        self.envelope_sensitivity = 0.5  # How responsive to input (0.0-1.0)
        self.envelope_attack = 0.01      # Envelope attack time
        self.envelope_release = 0.1      # Envelope release time

        # Filter state variables (separate for left and right channels)
        self.x1_left = 0.0   # Previous left input sample
        self.x2_left = 0.0   # Left input sample before that
        self.y1_left = 0.0   # Previous left output sample
        self.y2_left = 0.0   # Left output sample before that

        self.x1_right = 0.0  # Previous right input sample
        self.x2_right = 0.0  # Right input sample before that
        self.y1_right = 0.0  # Previous right output sample
        self.y2_right = 0.0  # Right output sample before that

        # Envelope follower state
        self.envelope = 0.0
        self.envelope_coeff_attack = self._calculate_attack_coeff()
        self.envelope_coeff_release = self._calculate_release_coeff()

        # Mode selection
        self.mode = "auto"  # "auto", "manual", "envelope"

        # Manual control (for manual wah)
        self.manual_position = 0.5  # 0.0-1.0 (low to high frequency)

        # Pre-calculate filter coefficients
        self._update_filter_coefficients()

    def _calculate_attack_coeff(self) -> float:
        """Calculate envelope attack coefficient."""
        return 1.0 - np.exp(-1.0 / (self.envelope_attack * self.sample_rate))

    def _calculate_release_coeff(self) -> float:
        """Calculate envelope release coefficient."""
        return 1.0 - np.exp(-1.0 / (self.envelope_release * self.sample_rate))

    def _update_filter_coefficients(self):
        """Update bandpass filter coefficients based on current center frequency."""
        # Normalize frequency
        normalized_freq = 2.0 * np.pi * self.center_freq / self.sample_rate

        # Calculate bandwidth in radians
        bandwidth_rad = 2.0 * np.pi * self.bandwidth / self.sample_rate

        # Calculate Q factor from resonance
        q = self.resonance

        # Calculate filter coefficients for bandpass filter
        # Using the standard biquad bandpass filter design
        k = np.tan(bandwidth_rad / 2.0)
        norm = 1.0 / (1.0 + k / q + k * k)

        self.b0 = k / q * norm
        self.b1 = 0.0
        self.b2 = -k / q * norm
        self.a1 = 2.0 * (k * k - 1.0) * norm
        self.a2 = (1.0 - k / q + k * k) * norm

    def set_parameters(self, params: Dict[str, float]):
        """
        Set Wah Wah effect parameters.

        Args:
            params: Dictionary containing parameter values
        """
        # Manual wah position (0.0-1.0 maps to frequency range)
        if "manual_position" in params:
            self.manual_position = np.clip(params["manual_position"], 0.0, 1.0)

        # LFO parameters for auto-wah
        if "lfo_rate" in params:
            self.lfo_rate = max(0.1, min(10.0, params["lfo_rate"]))
        if "lfo_depth" in params:
            self.lfo_depth = np.clip(params["lfo_depth"], 0.0, 1.0)

        # Envelope follower parameters
        if "envelope_sensitivity" in params:
            self.envelope_sensitivity = np.clip(params["envelope_sensitivity"], 0.0, 1.0)
        if "envelope_attack" in params:
            self.envelope_attack = max(0.001, params["envelope_attack"])
            self.envelope_coeff_attack = self._calculate_attack_coeff()
        if "envelope_release" in params:
            self.envelope_release = max(0.001, params["envelope_release"])
            self.envelope_coeff_release = self._calculate_release_coeff()

        # Filter parameters
        if "resonance" in params:
            self.resonance = max(0.1, min(10.0, params["resonance"]))

        # Mode selection
        if "mode" in params:
            self.mode = params["mode"]

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Implementation of stereo sample processing for Wah Wah effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Use left channel for envelope detection (mono processing for simplicity)
        sample = (left + right) * 0.5

        # Update center frequency based on mode
        if self.mode == "manual":
            # Manual wah - use manual position
            freq_range = 2000.0  # Frequency sweep range in Hz
            self.center_freq = 300.0 + self.manual_position * freq_range

        elif self.mode == "auto":
            # Auto wah - use LFO
            lfo_value = fast_math.fast_sin(self.lfo_phase)
            self.lfo_phase += 2.0 * np.pi * self.lfo_rate / self.sample_rate
            if self.lfo_phase > 2.0 * np.pi:
                self.lfo_phase -= 2.0 * np.pi

            # Convert LFO to frequency modulation
            freq_mod = (lfo_value * self.lfo_depth + 1.0) * 0.5  # 0.0-1.0 range
            freq_range = 2000.0
            self.center_freq = 300.0 + freq_mod * freq_range

        elif self.mode == "envelope":
            # Envelope follower wah
            # Calculate envelope from input signal
            input_level = abs(sample)
            if input_level > self.envelope:
                self.envelope += (input_level - self.envelope) * self.envelope_coeff_attack
            else:
                self.envelope += (input_level - self.envelope) * self.envelope_coeff_release

            # Use envelope to modulate frequency
            env_mod = min(1.0, self.envelope * self.envelope_sensitivity * 10.0)
            freq_range = 2000.0
            self.center_freq = 300.0 + env_mod * freq_range

        # Update filter coefficients
        self._update_filter_coefficients()

        # Apply bandpass filter to each channel
        left_output = (self.b0 * left +
                      self.b1 * self.x1_left +
                      self.b2 * self.x2_left -
                      self.a1 * self.y1_left -
                      self.a2 * self.y2_left)

        right_output = (self.b0 * right +
                       self.b1 * self.x1_right +
                       self.b2 * self.x2_right -
                       self.a1 * self.y1_right -
                       self.a2 * self.y2_right)

        # Update filter state for both channels
        self.x2_left = self.x1_left
        self.x1_left = left
        self.y2_left = self.y1_left
        self.y1_left = left_output

        self.x2_right = self.x1_right
        self.x1_right = right
        self.y2_right = self.y1_right
        self.y1_right = right_output

        return (left_output, right_output)

    def _reset_impl(self):
        """Reset effect state."""
        # Reset filter state for both channels
        self.x1_left = self.x2_left = self.y1_left = self.y2_left = 0.0
        self.x1_right = self.x2_right = self.y1_right = self.y2_right = 0.0
        self.envelope = 0.0
        self.lfo_phase = 0.0

    def get_parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter information for XG control."""
        return {
            "manual_position": {
                "range": (0.0, 1.0),
                "default": 0.5,
                "description": "Manual wah position (0.0 = low freq, 1.0 = high freq)"
            },
            "lfo_rate": {
                "range": (0.1, 10.0),
                "default": 2.0,
                "description": "LFO rate for auto-wah (Hz)"
            },
            "lfo_depth": {
                "range": (0.0, 1.0),
                "default": 0.7,
                "description": "LFO depth for auto-wah"
            },
            "envelope_sensitivity": {
                "range": (0.0, 1.0),
                "default": 0.5,
                "description": "Envelope follower sensitivity"
            },
            "envelope_attack": {
                "range": (0.001, 1.0),
                "default": 0.01,
                "description": "Envelope attack time (seconds)"
            },
            "envelope_release": {
                "range": (0.001, 1.0),
                "default": 0.1,
                "description": "Envelope release time (seconds)"
            },
            "resonance": {
                "range": (0.1, 10.0),
                "default": 2.0,
                "description": "Filter resonance (Q factor)"
            },
            "mode": {
                "options": ["auto", "manual", "envelope"],
                "default": "auto",
                "description": "Wah control mode"
            }
        }


# Factory function for creating wah wah effect
def create_wah_wah_effect(sample_rate: int = 44100) -> WahWahEffect:
    """Create a Wah Wah effect instance."""
    return WahWahEffect(sample_rate)


# Process function for integration with main effects system
def process_wah_wah_effect(left: float, right: float, params: Dict[str, float],
                          state: Dict[str, Any]) -> Tuple[float, float]:
    """
    Process audio through Wah Wah effect (for integration).

    Args:
        left: Left channel input
        right: Right channel input
        params: Effect parameters
        state: Effect state

    Returns:
        Tuple of (left_output, right_output)
    """
    # Get or create effect instance in state
    if "wah_wah_effect" not in state:
        state["wah_wah_effect"] = WahWahEffect()

    effect = state["wah_wah_effect"]

    # Update parameters by setting them individually
    for param_name, param_value in params.items():
        effect.set_parameter(param_name, param_value)

    # Process audio (stereo processing)
    return effect.process_sample(left, right)