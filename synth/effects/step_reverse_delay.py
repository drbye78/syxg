"""
Step Reverse Delay effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepReverseDelayEffect:
    """
    Step Reverse Delay effect implementation.

    Reverse delay with stepped parameter modulation for unique rhythmic effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step reverse delay effect state"""
        # Create delay buffers
        buffer_size = int(self.sample_rate)
        self.buffer = [0.0] * buffer_size
        self.reverse_buffer = [0.0] * buffer_size
        self.pos = 0
        self.feedback_buffer = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step reverse delay effect.

        Parameters:
        - time: delay time (0.0-1.0, maps to 0-1000 ms)
        - feedback: feedback amount (0.0-1.0)
        - level: output level (0.0-1.0)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        time = params.get("time", 0.5) * 1000  # 0-1000 ms
        feedback = params.get("feedback", 0.5)
        level = params.get("level", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_reverse_delay" not in state:
            state["step_reverse_delay"] = {
                "buffer": [0.0] * int(self.sample_rate),
                "reverse_buffer": [0.0] * int(self.sample_rate),
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        # Update step
        step_reverse_delay_state = state["step_reverse_delay"]
        step_reverse_delay_state["step"] = (step_reverse_delay_state["step"] + 1) % steps

        # Calculate step-based delay time
        step_time = time * (step_reverse_delay_state["step"] + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample from buffer
        delay_pos = (step_reverse_delay_state["pos"] - delay_samples) % len(step_reverse_delay_state["buffer"])
        delayed_sample = step_reverse_delay_state["buffer"][int(delay_pos)]

        # Apply feedback
        feedback_sample = step_reverse_delay_state["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        step_reverse_delay_state["buffer"][step_reverse_delay_state["pos"]] = processed_sample
        step_reverse_delay_state["pos"] = (step_reverse_delay_state["pos"] + 1) % len(step_reverse_delay_state["buffer"])
        step_reverse_delay_state["feedback_buffer"] = processed_sample

        # Get reverse sample
        reverse_pos = (step_reverse_delay_state["pos"] + delay_samples) % len(step_reverse_delay_state["reverse_buffer"])
        reverse_sample = step_reverse_delay_state["reverse_buffer"][int(reverse_pos)]

        # Store in reverse buffer
        step_reverse_delay_state["reverse_buffer"][step_reverse_delay_state["pos"]] = processed_sample

        # Mix dry, forward delayed, and reverse delayed signals
        output = input_sample * (1 - level) + delayed_sample * level * (1 - step_reverse_delay_state["step"] / steps) + \
                reverse_sample * level * (step_reverse_delay_state["step"] / steps)

        return (output, output)


# Factory function for creating step reverse delay effect
def create_step_reverse_delay_effect(sample_rate: int = 44100):
    """Create a step reverse delay effect instance"""
    return StepReverseDelayEffect(sample_rate)


# Process function for integration with main effects system
def process_step_reverse_delay_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step reverse delay effect (for integration)"""
    effect = StepReverseDelayEffect()
    return effect.process(left, right, params, state)
