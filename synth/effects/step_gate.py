"""
Step Gate effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepGateEffect:
    """
    Step Gate effect implementation.

    Gate with stepped parameter modulation for rhythmic gating.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step gate effect state"""
        self.open = False
        self.hold_counter = 0
        self.gain = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step gate effect.

        Parameters:
        - threshold: gate threshold (0.0-1.0, maps to -80 to -10 dB)
        - reduction: gate reduction (0.0-1.0, maps to 0-60 dB)
        - steps: number of steps (1-8 steps)
        - hold: hold time (0.0-1.0, maps to 0-1000 ms)
        """
        # Get parameters
        threshold = -80 + params.get("threshold", 0.5) * 70  # -80 to -10 dB
        reduction = params.get("reduction", 0.5) * 60  # 0-60 dB
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        hold = params.get("hold", 0.5) * 1000  # 0-1000 ms

        # Initialize state if needed
        if "step_gate" not in state:
            state["step_gate"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0,
                "step": 0
            }

        # Update step
        step_gate_state = state["step_gate"]
        step_gate_state["step"] = (step_gate_state["step"] + 1) % steps

        # Calculate step-based parameters
        step_threshold = threshold * (step_gate_state["step"] + 1) / steps
        step_reduction = reduction * (step_gate_state["step"] + 1) / steps

        # Convert to linear values
        threshold_linear = 10 ** (step_threshold / 20.0)
        reduction_factor = 10 ** (-step_reduction / 20.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Check threshold
        if input_level > threshold_linear:
            # Signal above threshold, open gate
            step_gate_state["open"] = True
            step_gate_state["hold_counter"] = hold_samples
        else:
            # Signal below threshold, check hold
            if step_gate_state["hold_counter"] > 0:
                step_gate_state["hold_counter"] -= 1
            else:
                step_gate_state["open"] = False

        # Calculate gain
        if step_gate_state["open"]:
            # Smooth opening
            if step_gate_state["gain"] < 1.0:
                step_gate_state["gain"] += 0.1
                step_gate_state["gain"] = min(1.0, step_gate_state["gain"])
        else:
            # Smooth closing
            step_gate_state["gain"] *= 0.99  # Exponential decay

        # Apply reduction
        if not step_gate_state["open"]:
            step_gate_state["gain"] *= reduction_factor

        # Apply gain
        output = input_sample * step_gate_state["gain"]

        return (output, output)


# Factory function for creating step gate effect
def create_step_gate_effect(sample_rate: int = 44100):
    """Create a step gate effect instance"""
    return StepGateEffect(sample_rate)


# Process function for integration with main effects system
def process_step_gate_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step gate effect (for integration)"""
    effect = StepGateEffect()
    return effect.process(left, right, params, state)
