"""
Step Multi Tap effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepMultiTapEffect:
    """
    Step Multi Tap effect implementation.

    Multi-tap delay with stepped parameter modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step multi tap effect state"""
        # Create delay buffer
        buffer_size = int(self.sample_rate)
        self.buffer = [0.0] * buffer_size
        self.pos = 0
        self.feedback_buffer = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step multi tap effect.

        Parameters:
        - taps: number of taps (1-10 taps)
        - feedback: feedback amount (0.0-1.0)
        - level: output level (0.0-1.0)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        taps = int(params.get("taps", 0.5) * 9) + 1  # 1-10 taps
        feedback = params.get("feedback", 0.5)
        level = params.get("level", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_multi_tap" not in state:
            state["step_multi_tap"] = {
                "buffer": [0.0] * int(self.sample_rate),
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        # Update step
        step_multi_tap_state = state["step_multi_tap"]
        step_multi_tap_state["step"] = (step_multi_tap_state["step"] + 1) % steps

        # Calculate step-based parameters
        step_taps = taps * (step_multi_tap_state["step"] + 1) // steps
        step_feedback = feedback * (step_multi_tap_state["step"] + 1) / steps

        # Generate tap delays
        delays = []
        for i in range(max(1, step_taps)):
            delay_time = (i * 500 * (step_multi_tap_state["step"] + 1) / steps)  # Up to 500ms
            delays.append(int(delay_time * self.sample_rate / 1000.0))

        # Get input sample
        input_sample = (left + right) / 2.0

        # Sum all taps
        delayed_sum = 0.0
        for delay_samples in delays:
            delay_pos = (step_multi_tap_state["pos"] - delay_samples) % len(step_multi_tap_state["buffer"])
            delayed_sum += step_multi_tap_state["buffer"][int(delay_pos)]

        # Normalize sum
        if step_taps > 0:
            delayed_sum /= step_taps

        # Apply feedback
        feedback_sample = step_multi_tap_state["feedback_buffer"] * step_feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        step_multi_tap_state["buffer"][step_multi_tap_state["pos"]] = processed_sample
        step_multi_tap_state["pos"] = (step_multi_tap_state["pos"] + 1) % len(step_multi_tap_state["buffer"])
        step_multi_tap_state["feedback_buffer"] = processed_sample

        # Mix dry and wet signals
        output = input_sample * (1 - level) + delayed_sum * level

        return (output, output)


# Factory function for creating step multi tap effect
def create_step_multi_tap_effect(sample_rate: int = 44100):
    """Create a step multi tap effect instance"""
    return StepMultiTapEffect(sample_rate)


# Process function for integration with main effects system
def process_step_multi_tap_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step multi tap effect (for integration)"""
    effect = StepMultiTapEffect()
    return effect.process(left, right, params, state)
