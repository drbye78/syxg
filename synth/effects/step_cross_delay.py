"""
Step Cross Delay effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepCrossDelayEffect:
    """
    Step Cross Delay effect implementation.

    Cross-feedback delay with stepped parameter modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step cross delay effect state"""
        # Create delay buffers for left and right channels
        buffer_size = int(self.sample_rate)
        self.left_buffer = [0.0] * buffer_size
        self.right_buffer = [0.0] * buffer_size
        self.left_pos = 0
        self.right_pos = 0
        self.left_feedback = 0.0
        self.right_feedback = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step cross delay effect.

        Parameters:
        - time: delay time (0.0-1.0, maps to 0-1000 ms)
        - feedback: feedback amount (0.0-1.0)
        - level: output level (0.0-1.0)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        time = params.get("time", 0.3) * 1000  # 0-1000 ms
        feedback = params.get("feedback", 0.5)
        level = params.get("level", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_cross_delay" not in state:
            state["step_cross_delay"] = {
                "left_buffer": [0.0] * int(self.sample_rate),
                "right_buffer": [0.0] * int(self.sample_rate),
                "left_pos": 0,
                "right_pos": 0,
                "left_feedback": 0.0,
                "right_feedback": 0.0,
                "step": 0
            }

        # Update step
        step_cross_delay_state = state["step_cross_delay"]
        step_cross_delay_state["step"] = (step_cross_delay_state["step"] + 1) % steps

        # Calculate step-based delay time
        step_time = time * (step_cross_delay_state["step"] + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)

        # Get delayed samples from buffers
        left_delay_pos = (step_cross_delay_state["left_pos"] - delay_samples) % len(step_cross_delay_state["left_buffer"])
        right_delay_pos = (step_cross_delay_state["right_pos"] - delay_samples) % len(step_cross_delay_state["right_buffer"])

        left_delayed = step_cross_delay_state["left_buffer"][int(left_delay_pos)]
        right_delayed = step_cross_delay_state["right_buffer"][int(right_delay_pos)]

        # Apply cross-feedback
        step_feedback = feedback * (step_cross_delay_state["step"] + 1) / steps
        left_feedback = step_cross_delay_state["left_feedback"] * step_feedback
        right_feedback = step_cross_delay_state["right_feedback"] * step_feedback
        cross_left_feedback = step_cross_delay_state["right_feedback"] * step_feedback * 0.5
        cross_right_feedback = step_cross_delay_state["left_feedback"] * step_feedback * 0.5

        # Process left channel
        processed_left = left + left_feedback + cross_left_feedback
        step_cross_delay_state["left_buffer"][step_cross_delay_state["left_pos"]] = processed_left
        step_cross_delay_state["left_pos"] = (step_cross_delay_state["left_pos"] + 1) % len(step_cross_delay_state["left_buffer"])
        step_cross_delay_state["left_feedback"] = processed_left

        # Process right channel
        processed_right = right + right_feedback + cross_right_feedback
        step_cross_delay_state["right_buffer"][step_cross_delay_state["right_pos"]] = processed_right
        step_cross_delay_state["right_pos"] = (step_cross_delay_state["right_pos"] + 1) % len(step_cross_delay_state["right_buffer"])
        step_cross_delay_state["right_feedback"] = processed_right

        # Mix dry and wet signals
        left_out = left * (1 - level) + left_delayed * level
        right_out = right * (1 - level) + right_delayed * level

        return (left_out, right_out)


# Factory function for creating step cross delay effect
def create_step_cross_delay_effect(sample_rate: int = 44100):
    """Create a step cross delay effect instance"""
    return StepCrossDelayEffect(sample_rate)


# Process function for integration with main effects system
def process_step_cross_delay_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step cross delay effect (for integration)"""
    effect = StepCrossDelayEffect()
    return effect.process(left, right, params, state)
