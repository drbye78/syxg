"""
Step Pitch Shifter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepPitchShifterEffect:
    """
    Step Pitch Shifter effect implementation.

    Pitch shifting with stepped parameter modulation for rhythmic pitch effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step pitch shifter effect state"""
        # Create delay buffer for pitch shifting
        buffer_size = int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer = [0.0] * buffer_size
        self.pos = 0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step pitch shifter effect.

        Parameters:
        - shift: pitch shift (0.0-1.0, maps to -12 to +12 semitones)
        - feedback: feedback amount (0.0-1.0)
        - steps: number of steps (1-8 steps)
        - formant: formant preservation (0.0-1.0)
        """
        # Get parameters
        shift = (params.get("shift", 0.5) * 24.0) - 12.0  # -12 to +12 semitones
        feedback = params.get("feedback", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        formant = params.get("formant", 0.5)

        # Initialize state if needed
        if "step_pitch_shifter" not in state:
            state["step_pitch_shifter"] = {
                "buffer": [0.0] * int(self.sample_rate * 0.1),
                "pos": 0,
                "step": 0
            }

        # Update step
        step_pitch_shifter_state = state["step_pitch_shifter"]
        step_pitch_shifter_state["step"] = (step_pitch_shifter_state["step"] + 1) % steps

        # Calculate step-based pitch shift
        step_shift = shift * (step_pitch_shifter_state["step"] + 1) / steps
        pitch_factor = 2 ** (step_shift / 12.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in buffer
        step_pitch_shifter_state["buffer"][step_pitch_shifter_state["pos"]] = input_sample
        step_pitch_shifter_state["pos"] = (step_pitch_shifter_state["pos"] + 1) % len(step_pitch_shifter_state["buffer"])

        # Calculate read position for pitch shifting
        read_pos = step_pitch_shifter_state["pos"] - int(len(step_pitch_shifter_state["buffer"]) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(step_pitch_shifter_state["buffer"])

        # Get shifted sample
        shifted_sample = step_pitch_shifter_state["buffer"][int(read_pos)]

        # Apply feedback
        shifted_sample = shifted_sample + feedback * input_sample

        # Mix dry and wet signals
        output = input_sample * (1 - feedback) + shifted_sample * feedback

        return (output, output)


# Factory function for creating step pitch shifter effect
def create_step_pitch_shifter_effect(sample_rate: int = 44100):
    """Create a step pitch shifter effect instance"""
    return StepPitchShifterEffect(sample_rate)


# Process function for integration with main effects system
def process_step_pitch_shifter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step pitch shifter effect (for integration)"""
    effect = StepPitchShifterEffect()
    return effect.process(left, right, params, state)
