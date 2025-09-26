"""
Step Distortion effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepDistortionEffect:
    """
    Step Distortion effect implementation.

    Distortion with stepped parameter modulation for rhythmic effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step distortion effect state"""
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step distortion effect.

        Parameters:
        - drive: distortion drive (0.0-1.0)
        - tone: tone control (0.0-1.0)
        - steps: number of steps (1-8 steps)
        - type: distortion type (0.0-1.0, maps to different types)
        """
        # Get parameters
        drive = params.get("drive", 0.5)
        tone = params.get("tone", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        type_param = int(params.get("type", 0.5) * 3)  # 0-3 types

        # Initialize state if needed
        if "step_distortion" not in state:
            state["step_distortion"] = {
                "step": 0
            }

        # Update step
        step_distortion_state = state["step_distortion"]
        step_distortion_state["step"] = (step_distortion_state["step"] + 1) % steps

        # Calculate step-based drive
        step_drive = drive * (step_distortion_state["step"] + 1) / steps

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply different distortion types based on step
        if type_param == 0:  # Soft clipping
            output = math.atan(input_sample * step_drive * 5.0) / (math.pi / 2)
        elif type_param == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * step_drive))
        elif type_param == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * step_drive)
            else:
                output = -1 + math.exp(input_sample * step_drive)
        else:  # Symmetric
            output = math.tanh(input_sample * step_drive)

        # Apply tone control
        if tone < 0.5:
            # More low frequencies
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # More high frequencies
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        return (output, output)


# Factory function for creating step distortion effect
def create_step_distortion_effect(sample_rate: int = 44100):
    """Create a step distortion effect instance"""
    return StepDistortionEffect(sample_rate)


# Process function for integration with main effects system
def process_step_distortion_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step distortion effect (for integration)"""
    effect = StepDistortionEffect()
    return effect.process(left, right, params, state)
