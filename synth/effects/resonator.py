"""
Resonator effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class ResonatorEffect:
    """
    Production-quality resonator effect implementation.

    Creates resonant peaks at specific frequencies for metallic, bell-like, wood, or glass sounds.
    Uses proper IIR filter implementations for consistent high-quality resonance across all modes.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the resonator effect state"""
        # Filter state variables for each mode
        self.filter_states = {
            0: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},  # Bell
            1: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},  # Metallic
            2: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},  # Wood
            3: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},  # Glass
        }

        # Resonance frequencies for different modes
        self.resonance_freqs = {
            0: [800.0, 1200.0, 2400.0],    # Bell harmonics
            1: [200.0, 400.0, 800.0],      # Metallic harmonics
            2: [100.0, 200.0, 400.0],      # Wood fundamentals
            3: [600.0, 1200.0, 2400.0],    # Glass harmonics
        }

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through resonator effect.

        Parameters:
        - resonance: resonance amount (0.0-1.0)
        - decay: decay time (0.0-1.0)
        - level: output level (0.0-1.0)
        - mode: resonance mode (0.0-1.0, maps to different frequency responses)
        - frequency: base frequency (0.0-1.0, maps to 50-5000 Hz)
        - spread: frequency spread (0.0-1.0)
        """
        # Get parameters
        resonance = params.get("resonance", 0.5)
        decay = params.get("decay", 0.5)
        level = params.get("level", 0.5)
        mode = int(params.get("mode", 0.5) * 3)  # 0-3 modes
        frequency = 50 + params.get("frequency", 0.5) * 4950  # 50-5000 Hz
        spread = params.get("spread", 0.5)

        # Initialize state if needed
        if "resonator" not in state:
            state["resonator"] = {
                "filter_states": {
                    0: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},
                    1: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},
                    2: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},
                    3: {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0},
                }
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply resonator processing based on mode
        if mode == 0:  # Bell-like resonance
            output = self._process_bell_resonance(input_sample, frequency, resonance, decay, spread, state)
        elif mode == 1:  # Metallic resonance
            output = self._process_metallic_resonance(input_sample, frequency, resonance, decay, spread, state)
        elif mode == 2:  # Wood-like resonance
            output = self._process_wood_resonance(input_sample, frequency, resonance, decay, spread, state)
        else:  # Glass-like resonance
            output = self._process_glass_resonance(input_sample, frequency, resonance, decay, spread, state)

        # Apply level
        output *= level

        return (output, output)

    def _process_bell_resonance(self, input_sample: float, frequency: float, resonance: float,
                              decay: float, spread: float, state: Dict[str, Any]) -> float:
        """Process bell-like resonance with multiple harmonics"""
        output = 0.0

        # Bell harmonics: fundamental + octave + fifth + major third
        harmonics = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        amplitudes = [1.0, 0.8, 0.6, 0.4, 0.3, 0.2]

        for i, (harmonic, amplitude) in enumerate(zip(harmonics, amplitudes)):
            # Calculate harmonic frequency with spread
            spread_factor = 1.0 + (spread - 0.5) * 0.1 * i
            harm_freq = frequency * harmonic * spread_factor

            # Create resonator filter for this harmonic
            coeffs = self._calculate_resonator_coefficients(harm_freq, resonance * amplitude, decay)

            # Apply filter
            filter_state = state["resonator"]["filter_states"][0]
            filtered = self._apply_biquad_filter(input_sample * amplitude, coeffs, filter_state)
            output += filtered

        return output

    def _process_metallic_resonance(self, input_sample: float, frequency: float, resonance: float,
                                  decay: float, spread: float, state: Dict[str, Any]) -> float:
        """Process metallic resonance with inharmonic partials"""
        output = 0.0

        # Metallic partials: fundamental + inharmonic overtones
        partials = [1.0, 1.4, 2.1, 2.8, 3.5, 4.2]
        amplitudes = [1.0, 0.7, 0.5, 0.3, 0.2, 0.1]

        for i, (partial, amplitude) in enumerate(zip(partials, amplitudes)):
            # Calculate partial frequency with spread
            spread_factor = 1.0 + (spread - 0.5) * 0.2 * i
            part_freq = frequency * partial * spread_factor

            # Create resonator filter for this partial
            coeffs = self._calculate_resonator_coefficients(part_freq, resonance * amplitude, decay)

            # Apply filter
            filter_state = state["resonator"]["filter_states"][1]
            filtered = self._apply_biquad_filter(input_sample * amplitude, coeffs, filter_state)
            output += filtered

        return output

    def _process_wood_resonance(self, input_sample: float, frequency: float, resonance: float,
                              decay: float, spread: float, state: Dict[str, Any]) -> float:
        """Process wood-like resonance with fundamental and formants"""
        output = 0.0

        # Wood formants: fundamental + formants
        formants = [1.0, 2.0, 3.0, 4.0, 5.0]
        amplitudes = [1.0, 0.6, 0.4, 0.2, 0.1]

        for i, (formant, amplitude) in enumerate(zip(formants, amplitudes)):
            # Calculate formant frequency with spread
            spread_factor = 1.0 + (spread - 0.5) * 0.05 * i
            form_freq = frequency * formant * spread_factor

            # Create resonator filter for this formant
            coeffs = self._calculate_resonator_coefficients(form_freq, resonance * amplitude, decay)

            # Apply filter
            filter_state = state["resonator"]["filter_states"][2]
            filtered = self._apply_biquad_filter(input_sample * amplitude, coeffs, filter_state)
            output += filtered

        return output

    def _process_glass_resonance(self, input_sample: float, frequency: float, resonance: float,
                               decay: float, spread: float, state: Dict[str, Any]) -> float:
        """Process glass-like resonance with high harmonics"""
        output = 0.0

        # Glass harmonics: high frequency harmonics
        harmonics = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
        amplitudes = [0.8, 0.6, 0.4, 0.3, 0.2, 0.1]

        for i, (harmonic, amplitude) in enumerate(zip(harmonics, amplitudes)):
            # Calculate harmonic frequency with spread
            spread_factor = 1.0 + (spread - 0.5) * 0.15 * i
            harm_freq = frequency * harmonic * spread_factor

            # Create resonator filter for this harmonic
            coeffs = self._calculate_resonator_coefficients(harm_freq, resonance * amplitude, decay)

            # Apply filter
            filter_state = state["resonator"]["filter_states"][3]
            filtered = self._apply_biquad_filter(input_sample * amplitude, coeffs, filter_state)
            output += filtered

        return output

    def _calculate_resonator_coefficients(self, frequency: float, resonance: float, decay: float) -> Dict[str, float]:
        """Calculate biquad filter coefficients for resonator"""
        # Normalize frequency
        w0 = 2 * math.pi * frequency / self.sample_rate

        # Q factor based on resonance and decay
        q = 1.0 / (resonance * 2 + 0.1)
        q *= (1.0 + decay * 2.0)  # Higher Q for longer decay

        # Bandwidth in octaves
        bw = math.log2(1 + 1/(q * 2)) * 2

        # Calculate filter coefficients for bandpass resonator
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
        """Apply biquad filter to input sample"""
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


# Factory function for creating resonator effect
def create_resonator_effect(sample_rate: int = 44100):
    """Create a resonator effect instance"""
    return ResonatorEffect(sample_rate)


# Process function for integration with main effects system
def process_resonator_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through resonator effect (for integration)"""
    effect = ResonatorEffect()
    return effect.process(left, right, params, state)
