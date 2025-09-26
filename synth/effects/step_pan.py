"""
Step Pan effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepPanEffect:
    """
    Step Pan effect implementation.

    Auto panning with stepped parameter modulation for rhythmic stereo movement.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step pan effect state"""
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step pan effect.

        Parameters:
        - rate: panning rate (0.0-1.0, maps to 0-5 Hz)
        - depth: panning depth (0.0-1.0)
        - waveform: LFO waveform (0.0-1.0, maps to different waveforms)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        rate = params.get("rate", 0.5) * 5.0  # 0-5 Hz
        depth = params.get("depth", 0.5)
        waveform = int(params.get("waveform", 0.5) * 3)  # 0-3 waveforms
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_pan" not in state:
            state["step_pan"] = {
                "lfo_phase": 0.0,
                "step": 0
            }

        # Update step
        step_pan_state = state["step_pan"]
        step_pan_state["step"] = (step_pan_state["step"] + 1) % steps

        # Update LFO phase
        lfo_phase = step_pan_state["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        # Generate LFO based on waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + step_pan_state["step"] * math.pi / steps)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + step_pan_state["step"] * math.pi / steps) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        # Calculate step-based pan
        pan = lfo_value * depth * (step_pan_state["step"] + 1) / steps

        # Apply panning
        left_out = left * (1 - pan)
        right_out = right * pan

        # Update state
        step_pan_state["lfo_phase"] = lfo_phase

        return (left_out, right_out)


# Factory function for creating step pan effect
def create_step_pan_effect(sample_rate: int = 44100):
    """Create a step pan effect instance"""
    return StepPanEffect(sample_rate)


# Process function for integration with main effects system
def process_step_pan_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step pan effect (for integration)"""
    effect = StepPanEffect()
    return effect.process(left, right, params, state)
