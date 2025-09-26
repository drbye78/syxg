"""
Step Expander effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepExpanderEffect:
    """
    Step Expander effect implementation.

    Expander with stepped parameter modulation for dynamic processing.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step expander effect state"""
        self.gain = 1.0
        self.counter = 0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step expander effect.

        Parameters:
        - threshold: expansion threshold (0.0-1.0, maps to -60 to 0 dB)
        - ratio: expansion ratio (0.0-1.0, maps to 1:1 to 10:1)
        - steps: number of steps (1-8 steps)
        - release: release time (0.0-1.0, maps to 10-300 ms)
        """
        # Get parameters
        threshold = -60 + params.get("threshold", 0.5) * 60  # -60 to 0 dB
        ratio = 1 + params.get("ratio", 0.5) * 9  # 1:1 to 10:1
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        release = 10 + params.get("release", 0.5) * 290  # 10-300 ms

        # Initialize state if needed
        if "step_expander" not in state:
            state["step_expander"] = {
                "gain": 1.0,
                "counter": 0,
                "step": 0
            }

        # Update step
        step_expander_state = state["step_expander"]
        step_expander_state["step"] = (step_expander_state["step"] + 1) % steps

        # Calculate step-based parameters
        step_ratio = ratio * (step_expander_state["step"] + 1) / steps
        step_threshold = threshold * (step_expander_state["step"] + 1) / steps

        # Convert to linear values
        threshold_linear = 10 ** (step_threshold / 20.0)

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Calculate desired gain
        if input_level < threshold_linear:
            desired_gain = 1.0 / (step_ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            desired_gain = 1.0

        # Apply expansion with step-based parameters
        if desired_gain < step_expander_state["gain"]:
            # Release (slow)
            step_expander_state["gain"] -= 0.01
            step_expander_state["gain"] = max(desired_gain, step_expander_state["gain"])
        else:
            # Attack (fast)
            step_expander_state["gain"] = desired_gain

        # Apply gain
        output = input_sample * step_expander_state["gain"]

        return (output, output)


# Factory function for creating step expander effect
def create_step_expander_effect(sample_rate: int = 44100):
    """Create a step expander effect instance"""
    return StepExpanderEffect(sample_rate)


# Process function for integration with main effects system
def process_step_expander_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step expander effect (for integration)"""
    effect = StepExpanderEffect()
    return effect.process(left, right, params, state)
