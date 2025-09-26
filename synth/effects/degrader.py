"""
Degrader effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class DegraderEffect:
    """
    Production-quality degrader effect implementation.

    Degrades audio quality by reducing bit depth and/or sample rate for lo-fi effects.
    Includes proper sample rate conversion, dithering, and anti-aliasing.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the degrader effect state"""
        # Sample rate conversion state
        self.accumulator = 0.0
        self.last_sample = 0.0
        self.filter_state = [0.0] * 4  # Anti-aliasing filter state

        # Dithering state
        self.dither_state = 0.0
        self.random_state = np.random.RandomState(42)  # Reproducible noise

        # Bit crushing state
        self.quantization_error = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through degrader effect.

        Parameters:
        - bit_depth: bit depth reduction (1-16 bits)
        - sample_rate: sample rate reduction (0.0-1.0, maps to different rates)
        - level: output level (0.0-1.0)
        - mode: degradation mode (0.0-1.0, maps to different degradation types)
        - dither: dither amount (0.0-1.0)
        - noise: noise amount (0.0-1.0)
        - filter: anti-aliasing filter (0.0-1.0)
        """
        # Get parameters
        bit_depth = int(params.get("bit_depth", 0.5) * 15) + 1  # 1-16 bits
        sample_rate_ratio = params.get("sample_rate", 0.5)  # 0.0-1.0
        level = params.get("level", 0.5)
        mode = int(params.get("mode", 0.5) * 4)  # 0-4 modes
        dither = params.get("dither", 0.5)
        noise = params.get("noise", 0.5)
        filter_param = params.get("filter", 0.5)

        # Initialize state if needed
        if "degrader" not in state:
            state["degrader"] = {
                "accumulator": 0.0,
                "last_sample": 0.0,
                "filter_state": [0.0] * 4,
                "dither_state": 0.0,
                "quantization_error": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply sample rate reduction with proper interpolation
        degraded_sample = self._apply_sample_rate_reduction(input_sample, sample_rate_ratio, state)

        # Apply anti-aliasing filter if needed
        if filter_param > 0:
            degraded_sample = self._apply_anti_aliasing_filter(degraded_sample, filter_param, state)

        # Apply bit depth reduction with dithering
        if bit_depth < 16:
            degraded_sample = self._apply_bit_crushing(degraded_sample, bit_depth, dither, state)

        # Apply different degradation modes
        if mode == 1:  # Add noise
            degraded_sample = self._add_noise(degraded_sample, noise, state)
        elif mode == 2:  # Add distortion
            degraded_sample = self._add_distortion(degraded_sample, noise)
        elif mode == 3:  # Add aliasing
            degraded_sample = self._add_aliasing(degraded_sample, noise)
        elif mode == 4:  # Vintage tape effect
            degraded_sample = self._apply_tape_effect(degraded_sample, noise, state)

        # Apply level
        output = degraded_sample * level

        return (output, output)

    def _apply_sample_rate_reduction(self, input_sample: float, ratio: float, state: Dict[str, Any]) -> float:
        """Apply sample rate reduction with proper interpolation"""
        # Calculate target sample rate (from 1kHz to original rate)
        target_rate = 1000 + ratio * (self.sample_rate - 1000)
        step_size = self.sample_rate / target_rate

        # Accumulate phase
        state["degrader"]["accumulator"] += 1.0

        # Check if we should update the sample
        if state["degrader"]["accumulator"] >= step_size:
            state["degrader"]["accumulator"] -= step_size
            state["degrader"]["last_sample"] = input_sample

        # Linear interpolation between samples
        phase = state["degrader"]["accumulator"] / step_size
        output = state["degrader"]["last_sample"] * (1 - phase) + input_sample * phase

        return output

    def _apply_anti_aliasing_filter(self, input_sample: float, filter_param: float, state: Dict[str, Any]) -> float:
        """Apply anti-aliasing filter to prevent aliasing artifacts"""
        # Simple low-pass filter for anti-aliasing
        cutoff = 0.1 + filter_param * 0.3  # Normalized cutoff frequency

        # Filter coefficients (simple IIR)
        a = 0.1 * cutoff
        b = 1 - a

        # Apply filter
        filter_state = state["degrader"]["filter_state"]
        output = a * input_sample + b * filter_state[0]

        # Update filter state
        filter_state[0] = output

        return output

    def _apply_bit_crushing(self, input_sample: float, bit_depth: int, dither: float, state: Dict[str, Any]) -> float:
        """Apply bit depth reduction with proper dithering"""
        # Calculate quantization levels
        levels = 2 ** bit_depth
        scale = levels / 2.0

        # Add dither noise
        if dither > 0:
            # Triangular dither
            r1 = self.random_state.random() - 0.5
            r2 = self.random_state.random() - 0.5
            dither_noise = (r1 + r2) * dither * (1.0 / scale)
        else:
            dither_noise = 0.0

        # Add dither to input
        dithered = input_sample + dither_noise

        # Quantize
        quantized = round(dithered * scale) / scale

        # Calculate quantization error for noise shaping (optional)
        error = dithered - quantized
        state["degrader"]["quantization_error"] = error

        return quantized

    def _add_noise(self, input_sample: float, noise_amount: float, state: Dict[str, Any]) -> float:
        """Add noise to the signal"""
        # Generate filtered noise
        noise = self.random_state.normal(0, 1) * noise_amount * 0.1

        # Apply simple high-pass filter to noise (makes it sound more like hiss)
        state["degrader"]["dither_state"] = 0.9 * state["degrader"]["dither_state"] + 0.1 * noise

        return input_sample + state["degrader"]["dither_state"]

    def _add_distortion(self, input_sample: float, distortion_amount: float) -> float:
        """Add distortion to the signal"""
        # Soft clipping distortion
        drive = 1 + distortion_amount * 5
        return math.tanh(input_sample * drive)

    def _add_aliasing(self, input_sample: float, aliasing_amount: float) -> float:
        """Add aliasing artifacts"""
        # Simulate aliasing by folding high frequencies
        folded = math.sin(input_sample * math.pi * (1 + aliasing_amount * 10))
        return input_sample + folded * aliasing_amount * 0.1

    def _apply_tape_effect(self, input_sample: float, tape_amount: float, state: Dict[str, Any]) -> float:
        """Apply vintage tape effect"""
        # Simulate tape saturation and high-frequency loss
        saturated = math.tanh(input_sample * (1 + tape_amount))

        # High-frequency rolloff
        rolloff = 0.8 + tape_amount * 0.2
        filtered = saturated * rolloff + state["degrader"]["last_sample"] * (1 - rolloff)

        state["degrader"]["last_sample"] = filtered

        return filtered


# Factory function for creating degrader effect
def create_degrader_effect(sample_rate: int = 44100):
    """Create a degrader effect instance"""
    return DegraderEffect(sample_rate)


# Process function for integration with main effects system
def process_degrader_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through degrader effect (for integration)"""
    effect = DegraderEffect()
    return effect.process(left, right, params, state)
