"""
Step Limiter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepLimiterEffect:
    """
    Step Limiter effect implementation.

    Limiter with stepped parameter modulation for dynamic control.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step limiter effect state"""
        self.gain = 1.0
        self.attack_counter = 0
        self.release_counter = 0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step limiter effect.

        Parameters:
        - threshold: limiting threshold (0.0-1.0, maps to -20 to 0 dB)
        - ratio: limiting ratio (0.0-1.0, maps to 10:1 to 20:1)
        - steps: number of steps (1-8 steps)
        - release: release time (0.0-1.0, maps to 50-300 ms)
        """
        # Get parameters
        threshold = -20 + params.get("threshold", 0.5) * 20  # -20 to 0 dB
        ratio = 10 + params.get("ratio", 0.5) * 10  # 10:1 to 20:1
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        release = 50 + params.get("release", 0.5) * 250  # 50-300 ms

        # Initialize state if needed
        if "step_limiter" not in state:
            state["step_limiter"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0,
                "step": 0
            }

        # Update step
        step_limiter_state = state["step_limiter"]
        step_limiter_state["step"] = (step_limiter_state["step"] + 1) % steps

        # Calculate step-based parameters
        step_ratio = ratio * (step_limiter_state["step"] + 1) / steps
        step_threshold = threshold * (step_limiter_state["step"] + 1) / steps

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

        # Apply limiting with step-based parameters
        if desired_gain < step_limiter_state["gain"]:
            # Attack (fast)
            step_limiter_state["gain"] = desired_gain
        else:
            # Release (slow)
            if step_limiter_state["release_counter"] < release_samples:
                step_limiter_state["release_counter"] += 1
                factor = step_limiter_state["release_counter"] / release_samples
                step_limiter_state["gain"] = step_limiter_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                step_limiter_state["gain"] = desired_gain

        # Apply gain
        output = input_sample * step_limiter_state["gain"]

        return (output, output)


# Factory function for creating step limiter effect
def create_step_limiter_effect(sample_rate: int = 44100):
    """Create a step limiter effect instance"""
    return StepLimiterEffect(sample_rate)


# Process function for integration with main effects system
def process_step_limiter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step limiter effect (for integration)"""
    effect = StepLimiterEffect()
    return effect.process(left, right, params, state)
