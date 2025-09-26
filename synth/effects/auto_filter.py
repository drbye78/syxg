"""
Auto Filter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class AutoFilterEffect:
    """
    Production-quality auto filter effect implementation.

    Automatically modulates filter cutoff frequency based on envelope following.
    Uses proper IIR filter implementation with resonance control.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the auto filter effect state"""
        # Filter state variables
        self.x1 = 0.0  # Previous input
        self.x2 = 0.0  # Input before that
        self.y1 = 0.0  # Previous output
        self.y2 = 0.0  # Output before that

        # Envelope follower state
        self.envelope = 0.0
        self.prev_input_level = 0.0

        # LFO state
        self.lfo_phase = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through auto filter effect.

        Parameters:
        - cutoff: base cutoff frequency (0.0-1.0, maps to 20-20000 Hz)
        - resonance: filter resonance (0.0-1.0)
        - depth: modulation depth (0.0-1.0)
        - lfo_waveform: LFO waveform type (0.0-1.0, maps to different waveforms)
        - attack: envelope attack time (0.0-1.0, maps to 1-100 ms)
        - release: envelope release time (0.0-1.0, maps to 10-1000 ms)
        - filter_type: filter type (0.0-1.0, maps to different filter types)
        """
        # Get parameters
        cutoff = 20 + params.get("cutoff", 0.5) * 19980  # 20-20000 Hz
        resonance = params.get("resonance", 0.5)
        depth = params.get("depth", 0.5)
        lfo_waveform = int(params.get("lfo_waveform", 0.5) * 3)  # 0-3 waveforms
        attack = 1 + params.get("attack", 0.5) * 99  # 1-100 ms
        release = 10 + params.get("release", 0.5) * 990  # 10-1000 ms
        filter_type = int(params.get("filter_type", 0.5) * 3)  # 0-3 filter types

        # Initialize state if needed
        if "auto_filter" not in state:
            state["auto_filter"] = {
                "x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0,
                "envelope": 0.0,
                "prev_input_level": 0.0,
                "lfo_phase": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Update envelope follower
        auto_filter_state = state["auto_filter"]
        attack_samples = attack * self.sample_rate / 1000.0
        release_samples = release * self.sample_rate / 1000.0

        if input_level > auto_filter_state["prev_input_level"]:
            # Attack
            coeff = 1.0 / attack_samples
            auto_filter_state["envelope"] += (input_level - auto_filter_state["envelope"]) * coeff
        else:
            # Release
            coeff = 1.0 / release_samples
            auto_filter_state["envelope"] += (input_level - auto_filter_state["envelope"]) * coeff

        # Update LFO
        lfo_rate = 2.0  # 2 Hz base rate
        auto_filter_state["lfo_phase"] += 2 * math.pi * lfo_rate / self.sample_rate

        # Generate LFO waveform
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(auto_filter_state["lfo_phase"])
        elif lfo_waveform == 1:  # Triangle
            phase = auto_filter_state["lfo_phase"] / (2 * math.pi)
            lfo_value = 1 - abs((phase % 1) * 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(auto_filter_state["lfo_phase"]) > 0 else -1
        else:  # Sawtooth
            phase = auto_filter_state["lfo_phase"] / (2 * math.pi)
            lfo_value = (phase % 1) * 2 - 1

        # Calculate modulated cutoff frequency
        envelope_mod = auto_filter_state["envelope"] * depth
        lfo_mod = lfo_value * depth * 0.3
        modulated_cutoff = cutoff * (1 + envelope_mod + lfo_mod)

        # Clamp cutoff frequency
        modulated_cutoff = max(20, min(20000, modulated_cutoff))

        # Calculate filter coefficients
        coeffs = self._calculate_filter_coefficients(modulated_cutoff, resonance, filter_type)

        # Apply filter
        output = self._apply_filter(input_sample, coeffs, auto_filter_state)

        # Update state
        auto_filter_state["prev_input_level"] = input_level

        return (output, output)

    def _calculate_filter_coefficients(self, cutoff: float, resonance: float, filter_type: int) -> Dict[str, float]:
        """Calculate IIR filter coefficients"""
        # Normalize cutoff frequency
        norm_cutoff = 2 * math.pi * cutoff / self.sample_rate

        # Resonance (Q factor)
        q = 1.0 / (2 * resonance + 0.1)  # Q ranges from 0.5 to 10

        # Pre-warp cutoff frequency for bilinear transform
        wd = 2 * math.pi * cutoff
        wa = 2 * self.sample_rate * math.tan(wd / (2 * self.sample_rate))
        norm_cutoff = wa / self.sample_rate

        # Calculate filter coefficients based on type
        if filter_type == 0:  # Lowpass
            k = math.tan(norm_cutoff / 2)
            k2 = k * k
            sqrt2 = math.sqrt(2)

            norm = 1 + k / q + k2
            b0 = k2 / norm
            b1 = 2 * b0
            b2 = b0
            a1 = (2 * (k2 - 1)) / norm
            a2 = (1 - k / q + k2) / norm

        elif filter_type == 1:  # Highpass
            k = math.tan(norm_cutoff / 2)
            k2 = k * k
            sqrt2 = math.sqrt(2)

            norm = 1 + k / q + k2
            b0 = 1 / norm
            b1 = -2 * b0
            b2 = b0
            a1 = (2 * (k2 - 1)) / norm
            a2 = (1 - k / q + k2) / norm

        elif filter_type == 2:  # Bandpass
            k = math.tan(norm_cutoff / 2)
            norm = 1 + k / q + k * k

            b0 = k / q / norm
            b1 = 0
            b2 = -b0
            a1 = (2 * (k * k - 1)) / norm
            a2 = (1 - k / q + k * k) / norm

        else:  # Notch
            k = math.tan(norm_cutoff / 2)
            norm = 1 + k / q + k * k

            b0 = (1 + k * k) / norm
            b1 = (2 * (k * k - 1)) / norm
            b2 = b0
            a1 = b1
            a2 = (1 - k / q + k * k) / norm

        return {
            "b0": b0, "b1": b1, "b2": b2,
            "a1": a1, "a2": a2
        }

    def _apply_filter(self, input_sample: float, coeffs: Dict[str, float], state: Dict[str, Any]) -> float:
        """Apply IIR filter to input sample"""
        # Direct Form I implementation
        output = (coeffs["b0"] * input_sample +
                 coeffs["b1"] * state["x1"] +
                 coeffs["b2"] * state["x2"] -
                 coeffs["a1"] * state["y1"] -
                 coeffs["a2"] * state["y2"])

        # Update delay lines
        state["x2"] = state["x1"]
        state["x1"] = input_sample
        state["y2"] = state["y1"]
        state["y1"] = output

        return output


# Factory function for creating auto filter effect
def create_auto_filter_effect(sample_rate: int = 44100):
    """Create an auto filter effect instance"""
    return AutoFilterEffect(sample_rate)


# Process function for integration with main effects system
def process_auto_filter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through auto filter effect (for integration)"""
    effect = AutoFilterEffect()
    return effect.process(left, right, params, state)
