"""
Step Pan Delay effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepPanDelayEffect:
    """
    Step Pan Delay effect implementation.

    Pan delay with stepped parameter modulation for rhythmic stereo delay effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step pan delay effect state"""
        # Create delay buffer
        buffer_size = int(self.sample_rate)
        self.buffer = [0.0] * buffer_size
        self.pos = 0
        self.feedback_buffer = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step pan delay effect.

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
        if "step_pan_delay" not in state:
            state["step_pan_delay"] = {
                "buffer": [0.0] * int(self.sample_rate),
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        # Update step
        step_pan_delay_state = state["step_pan_delay"]
        step_pan_delay_state["step"] = (step_pan_delay_state["step"] + 1) % steps

        # Calculate step-based delay time
        step_time = time * (step_pan_delay_state["step"] + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample from buffer
        delay_pos = (step_pan_delay_state["pos"] - delay_samples) % len(step_pan_delay_state["buffer"])
        delayed_sample = step_pan_delay_state["buffer"][int(delay_pos)]

        # Apply feedback
        feedback_sample = step_pan_delay_state["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        step_pan_delay_state["buffer"][step_pan_delay_state["pos"]] = processed_sample
        step_pan_delay_state["pos"] = (step_pan_delay_state["pos"] + 1) % len(step_pan_delay_state["buffer"])
        step_pan_delay_state["feedback_buffer"] = processed_sample

        # Mix dry and wet signals
        output = input_sample * (1 - level) + delayed_sample * level

        # Apply step-based panning
        pan = (step_pan_delay_state["step"] / (steps - 1)) * 2 - 1  # -1 to 1
        left_out = output * (1 - pan)
        right_out = output * pan

        return (left_out, right_out)


# Factory function for creating step pan delay effect
def create_step_pan_delay_effect(sample_rate: int = 44100):
    """Create a step pan delay effect instance"""
    return StepPanDelayEffect(sample_rate)


# Process function for integration with main effects system
def process_step_pan_delay_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step pan delay effect (for integration)"""
    effect = StepPanDelayEffect()
    return effect.process(left, right, params, state)
