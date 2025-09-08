"""
Step Tremolo effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepTremoloEffect:
    """
    Step Tremolo effect implementation.

    Tremolo with stepped parameter modulation for rhythmic amplitude modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step tremolo effect state"""
        self.lfo_phase = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step tremolo effect.

        Parameters:
        - rate: modulation rate (0.0-1.0, maps to 0-10 Hz)
        - depth: modulation depth (0.0-1.0)
        - waveform: LFO waveform (0.0-1.0, maps to different waveforms)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        rate = params.get("rate", 0.5) * 10.0  # 0-10 Hz
        depth = params.get("depth", 0.5)
        waveform = int(params.get("waveform", 0.5) * 3)  # 0-3 waveforms
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_tremolo" not in state:
            state["step_tremolo"] = {
                "lfo_phase": 0.0,
                "step": 0
            }

        # Update step
        step_tremolo_state = state["step_tremolo"]
        step_tremolo_state["step"] = (step_tremolo_state["step"] + 1) % steps

        # Update LFO phase
        lfo_phase = step_tremolo_state["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        # Generate LFO based on waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + step_tremolo_state["step"] * math.pi / steps)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + step_tremolo_state["step"] * math.pi / steps) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        # Normalize LFO for amplitude modulation
        lfo_value = lfo_value * depth * 0.5 + 0.5

        # Apply tremolo
        left_out = left * lfo_value
        right_out = right * lfo_value

        # Update state
        step_tremolo_state["lfo_phase"] = lfo_phase

        return (left_out, right_out)


# Factory function for creating step tremolo effect
def create_step_tremolo_effect(sample_rate: int = 44100):
    """Create a step tremolo effect instance"""
    return StepTremoloEffect(sample_rate)


# Process function for integration with main effects system
def process_step_tremolo_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step tremolo effect (for integration)"""
    effect = StepTremoloEffect()
    return effect.process(left, right, params, state)
