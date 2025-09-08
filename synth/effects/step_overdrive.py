"""
Step Overdrive effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepOverdriveEffect:
    """
    Step Overdrive effect implementation.

    Overdrive with stepped parameter modulation for rhythmic distortion.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step overdrive effect state"""
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step overdrive effect.

        Parameters:
        - drive: overdrive drive (0.0-1.0)
        - tone: tone control (0.0-1.0)
        - steps: number of steps (1-8 steps)
        - bias: bias control (0.0-1.0)
        """
        # Get parameters
        drive = params.get("drive", 0.5)
        tone = params.get("tone", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        bias = params.get("bias", 0.5)

        # Initialize state if needed
        if "step_overdrive" not in state:
            state["step_overdrive"] = {
                "step": 0
            }

        # Update step
        step_overdrive_state = state["step_overdrive"]
        step_overdrive_state["step"] = (step_overdrive_state["step"] + 1) % steps

        # Calculate step-based drive
        step_drive = drive * (step_overdrive_state["step"] + 1) / steps

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply overdrive with step-based parameters
        # Add bias for asymmetric distortion
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + step_drive * 9.0))

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


# Factory function for creating step overdrive effect
def create_step_overdrive_effect(sample_rate: int = 44100):
    """Create a step overdrive effect instance"""
    return StepOverdriveEffect(sample_rate)


# Process function for integration with main effects system
def process_step_overdrive_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step overdrive effect (for integration)"""
    effect = StepOverdriveEffect()
    return effect.process(left, right, params, state)
