"""
Step Filter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepFilterEffect:
    """
    Step Filter effect implementation.

    Filter with stepped parameter modulation for rhythmic filtering.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step filter effect state"""
        self.step = 0
        self.prev_input = 0.0
        self.prev_output = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step filter effect.

        Parameters:
        - cutoff: base cutoff frequency (0.0-1.0, maps to 20-20000 Hz)
        - resonance: filter resonance (0.0-1.0)
        - depth: modulation depth (0.0-1.0)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        cutoff = 20 + params.get("cutoff", 0.5) * 19980  # 20-20000 Hz
        resonance = params.get("resonance", 0.5)
        depth = params.get("depth", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_filter" not in state:
            state["step_filter"] = {
                "step": 0,
                "prev_input": 0.0,
                "prev_output": 0.0
            }

        # Update step
        step_filter_state = state["step_filter"]
        step_filter_state["step"] = (step_filter_state["step"] + 1) % steps

        # Calculate step-based cutoff frequency
        step_cutoff = cutoff * (step_filter_state["step"] + 1) / steps

        # Normalize cutoff frequency
        norm_cutoff = step_cutoff / (self.sample_rate / 2.0)
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply simple low-pass filter (simplified implementation)
        # This would normally use a proper filter implementation
        alpha = 0.1 + depth * 0.8  # Filter coefficient based on depth
        output = input_sample * (1 - alpha) + step_filter_state["prev_input"] * alpha

        # Apply resonance
        if resonance > 0:
            output += (output - step_filter_state["prev_output"]) * resonance

        # Update state
        step_filter_state["prev_input"] = input_sample
        step_filter_state["prev_output"] = output

        return (output, output)


# Factory function for creating step filter effect
def create_step_filter_effect(sample_rate: int = 44100):
    """Create a step filter effect instance"""
    return StepFilterEffect(sample_rate)


# Process function for integration with main effects system
def process_step_filter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step filter effect (for integration)"""
    effect = StepFilterEffect()
    return effect.process(left, right, params, state)
