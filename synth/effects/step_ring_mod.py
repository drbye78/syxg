"""
Step Ring Mod effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepRingModEffect:
    """
    Step Ring Mod effect implementation.

    Ring modulation with stepped parameter modulation for rhythmic modulation effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step ring mod effect state"""
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step ring mod effect.

        Parameters:
        - frequency: modulation frequency (0.0-1.0, maps to 0-1000 Hz)
        - depth: modulation depth (0.0-1.0)
        - waveform: LFO waveform (0.0-1.0, maps to different waveforms)
        - steps: number of steps (1-8 steps)
        """
        # Get parameters
        frequency = params.get("frequency", 0.5) * 1000.0  # 0-1000 Hz
        depth = params.get("depth", 0.5)
        waveform = int(params.get("waveform", 0.5) * 3)  # 0-3 waveforms
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps

        # Initialize state if needed
        if "step_ring_mod" not in state:
            state["step_ring_mod"] = {
                "step": 0
            }

        # Update step
        step_ring_mod_state = state["step_ring_mod"]
        step_ring_mod_state["step"] = (step_ring_mod_state["step"] + 1) % steps

        # Calculate step-based frequency
        step_frequency = frequency * (step_ring_mod_state["step"] + 1) / steps

        # Generate modulation signal based on waveform
        phase = (step_ring_mod_state["step"] / steps) * 2 * math.pi
        if waveform == 0:  # Sine
            mod_signal = math.sin(phase)
        elif waveform == 1:  # Triangle
            mod_signal = 1 - abs((phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            mod_signal = 1 if math.sin(phase) > 0 else -1
        else:  # Sawtooth
            mod_signal = (phase / (2 * math.pi)) % 1 * 2 - 1

        # Apply depth
        mod_signal *= depth

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply ring modulation
        output = input_sample * mod_signal

        return (output, output)


# Factory function for creating step ring mod effect
def create_step_ring_mod_effect(sample_rate: int = 44100):
    """Create a step ring mod effect instance"""
    return StepRingModEffect(sample_rate)


# Process function for integration with main effects system
def process_step_ring_mod_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step ring mod effect (for integration)"""
    effect = StepRingModEffect()
    return effect.process(left, right, params, state)
