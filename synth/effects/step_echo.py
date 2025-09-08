"""
Step Echo effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepEchoEffect:
    """
    Step Echo effect implementation.

    Echo with stepped parameter modulation for rhythmic effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step echo effect state"""
        # Create delay buffer
        buffer_size = int(self.sample_rate)
        self.buffer = [0.0] * buffer_size
        self.pos = 0
        self.feedback_buffer = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step echo effect.

        Parameters:
        - time: echo time (0.0-1.0, maps to 0-1000 ms)
        - feedback: feedback amount (0.0-1.0)
        - level: output level (0.0-1.0)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        time = params.get("time", 0.5) * 1000  # 0-1000 ms
        feedback = params.get("feedback", 0.7)
        level = params.get("level", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_echo" not in state:
            state["step_echo"] = {
                "buffer": [0.0] * int(self.sample_rate),
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        # Update step
        step_echo_state = state["step_echo"]
        step_echo_state["step"] = (step_echo_state["step"] + 1) % steps

        # Calculate step-based delay time
        step_time = time * (step_echo_state["step"] + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample from buffer
        delay_pos = (step_echo_state["pos"] - delay_samples) % len(step_echo_state["buffer"])
        delayed_sample = step_echo_state["buffer"][int(delay_pos)]

        # Apply step-based feedback with decay
        step_feedback = feedback * (1 - step_echo_state["step"] / steps)
        feedback_sample = step_echo_state["feedback_buffer"] * step_feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        step_echo_state["buffer"][step_echo_state["pos"]] = processed_sample
        step_echo_state["pos"] = (step_echo_state["pos"] + 1) % len(step_echo_state["buffer"])
        step_echo_state["feedback_buffer"] = processed_sample

        # Mix dry and wet signals
        output = input_sample * (1 - level) + delayed_sample * level

        return (output, output)


# Factory function for creating step echo effect
def create_step_echo_effect(sample_rate: int = 44100):
    """Create a step echo effect instance"""
    return StepEchoEffect(sample_rate)


# Process function for integration with main effects system
def process_step_echo_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step echo effect (for integration)"""
    effect = StepEchoEffect()
    return effect.process(left, right, params, state)
