"""
Talk Wah Variation effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class TalkWahVariationEffect:
    """
    Talk Wah Variation effect implementation.

    Auto-wah with envelope following for vocal-like wah effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the talk wah variation effect state"""
        # Filter state
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

        # Envelope follower state
        self.envelope = 0.0
        self.prev_input_level = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through talk wah variation effect.

        Parameters:
        - sensitivity: envelope sensitivity (0.0-1.0)
        - depth: modulation depth (0.0-1.0)
        - resonance: filter resonance (0.0-1.0)
        - mode: wah mode (0.0-1.0, maps to different wah characteristics)
        - frequency: center frequency (0.0-1.0, maps to 200-5000 Hz)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        sensitivity = params.get("sensitivity", 0.5)
        depth = params.get("depth", 0.5)
        resonance = params.get("resonance", 0.5)
        mode = int(params.get("mode", 0.5) * 3)  # 0-3 modes
        frequency = 200 + params.get("frequency", 0.5) * 4800  # 200-5000 Hz
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "talk_wah_variation" not in state:
            state["talk_wah_variation"] = {
                "x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0,
                "envelope": 0.0,
                "prev_input_level": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Update envelope follower
        talk_wah_state = state["talk_wah_variation"]
        attack_coeff = 0.01 * sensitivity
        release_coeff = 0.1 * sensitivity

        if input_level > talk_wah_state["prev_input_level"]:
            talk_wah_state["envelope"] += (input_level - talk_wah_state["envelope"]) * attack_coeff
        else:
            talk_wah_state["envelope"] += (input_level - talk_wah_state["envelope"]) * release_coeff

        # Calculate modulated cutoff frequency
        base_freq = frequency
        max_freq = frequency * 4  # Up to 4x the base frequency
        envelope_mod = talk_wah_state["envelope"] * depth
        modulated_cutoff = base_freq + (max_freq - base_freq) * envelope_mod

        # Clamp frequency
        modulated_cutoff = max(100, min(10000, modulated_cutoff))

        # Calculate filter coefficients based on mode
        if mode == 0:  # Bandpass (classic wah)
            coeffs = self._calculate_bandpass_coefficients(modulated_cutoff, resonance)
        elif mode == 1:  # Lowpass
            coeffs = self._calculate_lowpass_coefficients(modulated_cutoff, resonance)
        elif mode == 2:  # Highpass
            coeffs = self._calculate_highpass_coefficients(modulated_cutoff, resonance)
        else:  # Notch
            coeffs = self._calculate_notch_coefficients(modulated_cutoff, resonance)

        # Apply filter
        output = self._apply_biquad_filter(input_sample, coeffs, talk_wah_state)

        # Update state
        talk_wah_state["prev_input_level"] = input_level

        # Apply level
        return (output * level, output * level)

    def _calculate_bandpass_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate bandpass filter coefficients"""
        w0 = 2 * math.pi * frequency / self.sample_rate
        q = 1.0 / (resonance * 2 + 0.1)
        alpha = math.sin(w0) / (2 * q)

        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        return {"b0": b0, "b1": b1, "b2": b2, "a0": a0, "a1": a1, "a2": a2}

    def _calculate_lowpass_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate lowpass filter coefficients"""
        w0 = 2 * math.pi * frequency / self.sample_rate
        q = 1.0 / (resonance * 2 + 0.1)
        alpha = math.sin(w0) / (2 * q)

        b0 = (1 - math.cos(w0)) / 2
        b1 = 1 - math.cos(w0)
        b2 = (1 - math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        return {"b0": b0, "b1": b1, "b2": b2, "a0": a0, "a1": a1, "a2": a2}

    def _calculate_highpass_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate highpass filter coefficients"""
        w0 = 2 * math.pi * frequency / self.sample_rate
        q = 1.0 / (resonance * 2 + 0.1)
        alpha = math.sin(w0) / (2 * q)

        b0 = (1 + math.cos(w0)) / 2
        b1 = -(1 + math.cos(w0))
        b2 = (1 + math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        return {"b0": b0, "b1": b1, "b2": b2, "a0": a0, "a1": a1, "a2": a2}

    def _calculate_notch_coefficients(self, frequency: float, resonance: float) -> Dict[str, float]:
        """Calculate notch filter coefficients"""
        w0 = 2 * math.pi * frequency / self.sample_rate
        q = 1.0 / (resonance * 2 + 0.1)
        alpha = math.sin(w0) / (2 * q)

        b0 = 1
        b1 = -2 * math.cos(w0)
        b2 = 1
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        return {"b0": b0, "b1": b1, "b2": b2, "a0": a0, "a1": a1, "a2": a2}

    def _apply_biquad_filter(self, input_sample: float, coeffs: Dict[str, float], state: Dict[str, Any]) -> float:
        """Apply biquad filter"""
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


# Factory function for creating talk wah variation effect
def create_talk_wah_variation_effect(sample_rate: int = 44100):
    """Create a talk wah variation effect instance"""
    return TalkWahVariationEffect(sample_rate)


# Process function for integration with main effects system
def process_talk_wah_variation_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through talk wah variation effect (for integration)"""
    effect = TalkWahVariationEffect()
    return effect.process(left, right, params, state)
