"""
Auto Wah effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class AutoWahEffect:
    """
    Auto Wah effect implementation.

    Automatic wah-wah effect controlled by envelope follower.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the auto wah effect state"""
        # Filter state variables
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

        # Envelope follower state
        self.envelope = 0.0
        self.prev_input_level = 0.0

        # Wah sweep state
        self.current_freq = 500.0  # Current wah frequency

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through auto wah effect.

        Parameters:
        - sensitivity: envelope sensitivity (0.0-1.0)
        - resonance: filter resonance (0.0-1.0)
        - range: wah frequency range (0.0-1.0)
        - decay: envelope decay time (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        sensitivity = params.get("sensitivity", 0.5)
        resonance = params.get("resonance", 0.5)
        wah_range = params.get("range", 0.5)
        decay = params.get("decay", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "auto_wah" not in state:
            state["auto_wah"] = {
                "x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0,
                "envelope": 0.0,
                "prev_input_level": 0.0,
                "current_freq": 500.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        auto_wah_state = state["auto_wah"]

        # Update envelope follower
        attack_coeff = 0.01 * sensitivity
        release_coeff = 0.1 * decay

        if input_level > auto_wah_state["prev_input_level"]:
            # Attack
            auto_wah_state["envelope"] += (input_level - auto_wah_state["envelope"]) * attack_coeff
        else:
            # Release
            auto_wah_state["envelope"] += (input_level - auto_wah_state["envelope"]) * release_coeff

        # Calculate wah frequency based on envelope
        base_freq = 300.0
        max_freq = base_freq + wah_range * 2000.0  # Up to 2300 Hz
        envelope_mod = auto_wah_state["envelope"] * sensitivity
        target_freq = base_freq + (max_freq - base_freq) * envelope_mod

        # Smooth frequency changes
        freq_diff = target_freq - auto_wah_state["current_freq"]
        auto_wah_state["current_freq"] += freq_diff * 0.1  # Smooth transition

        # Clamp frequency
        auto_wah_state["current_freq"] = max(100, min(3000, auto_wah_state["current_freq"]))

        # Calculate filter coefficients for bandpass wah filter
        coeffs = self._calculate_wah_coefficients(auto_wah_state["current_freq"], resonance)

        # Apply filter
        output = self._apply_biquad_filter(input_sample, coeffs, auto_wah_state)

        # Update state
        auto_wah_state["prev_input_level"] = input_level

        # Apply level
        return (output * level, output * level)

    def _calculate_wah_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate wah filter coefficients (bandpass)"""
        # Normalize frequency
        w0 = 2 * math.pi * frequency / self.sample_rate

        # Q factor for wah (typically high Q for narrow peak)
        q = 2.0 + resonance * 8.0  # Q ranges from 2 to 10

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

    def _apply_biquad_filter(self, input_sample: float, coeffs: Dict[str, float], state: Dict[str, Any]) -> float:
        """Apply biquad filter"""
        # Direct Form I implementation
        output = (coeffs["b0"]/coeffs["a0"]) * input_sample + \
                (coeffs["b1"]/coeffs["a0"]) * state["x1"] + \
                (coeffs["b2"]/coeffs["a0"]) * state["x2"] - \
                (coeffs["a1"]/coeffs["a0"]) * state["y1"] - \
                (coeffs["a2"]/coeffs["a0"]) * state["y2"]

        # Update delay lines
        state["x2"] = state["x1"]
        state["x1"] = input_sample
        state["y2"] = state["y1"]
        state["y1"] = output

        return output


# Factory function for creating auto wah effect
def create_auto_wah_effect(sample_rate: int = 44100):
    """Create an auto wah effect instance"""
    return AutoWahEffect(sample_rate)


# Process function for integration with main effects system
def process_auto_wah_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through auto wah effect (for integration)"""
    effect = AutoWahEffect()
    return effect.process(left, right, params, state)
