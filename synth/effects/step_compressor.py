"""
Step Compressor effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepCompressorEffect:
    """
    Step Compressor effect implementation.

    Compressor with stepped parameter changes for rhythmic effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step compressor effect state"""
        self.gain = 1.0
        self.attack_counter = 0
        self.release_counter = 0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step compressor effect.

        Parameters:
        - threshold: compression threshold (0.0-1.0, maps to -60 to 0 dB)
        - ratio: compression ratio (0.0-1.0, maps to 1:1 to 20:1)
        - steps: number of steps (1-8 steps)
        - release: release time (0.0-1.0, maps to 10-300 ms)
        """
        # Get parameters
        threshold = -60 + params.get("threshold", 0.5) * 60  # -60 to 0 dB
        ratio = 1 + params.get("ratio", 0.5) * 19  # 1:1 to 20:1
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        release = 10 + params.get("release", 0.5) * 290  # 10-300 ms

        # Initialize state if needed
        if "step_compressor" not in state:
            state["step_compressor"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0,
                "step": 0
            }

        # Update step
        step_compressor_state = state["step_compressor"]
        step_compressor_state["step"] = (step_compressor_state["step"] + 1) % steps

        # Calculate step-based parameters
        step_ratio = ratio * (step_compressor_state["step"] + 1) / steps
        step_threshold = threshold * (step_compressor_state["step"] + 1) / steps

        # Convert to linear values
        threshold_linear = 10 ** (step_threshold / 20.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Calculate desired gain
        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/step_ratio))
        else:
            desired_gain = 1.0

        # Apply compression with step-based parameters
        if desired_gain < step_compressor_state["gain"]:
            # Attack
            step_compressor_state["gain"] = desired_gain
        else:
            # Release
            if step_compressor_state["release_counter"] < release_samples:
                step_compressor_state["release_counter"] += 1
                factor = step_compressor_state["release_counter"] / release_samples
                step_compressor_state["gain"] = step_compressor_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                step_compressor_state["gain"] = desired_gain

        # Apply gain
        output = input_sample * step_compressor_state["gain"]

        return (output, output)


# Factory function for creating step compressor effect
def create_step_compressor_effect(sample_rate: int = 44100):
    """Create a step compressor effect instance"""
    return StepCompressorEffect(sample_rate)


# Process function for integration with main effects system
def process_step_compressor_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step compressor effect (for integration)"""
    effect = StepCompressorEffect()
    return effect.process(left, right, params, state)
