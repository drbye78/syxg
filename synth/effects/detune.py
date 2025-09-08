"""
Detune effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class DetuneEffect:
    """
    Detune effect implementation.

    Creates a "double" sound by slightly detuning the pitch, simulating multiple instruments
    playing the same note.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the detune effect state"""
        # Create delay buffer for pitch shifting
        buffer_size = int(self.sample_rate * 0.1)  # 100ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through detune effect.

        Parameters:
        - shift: detune amount (-50 to +50 cents)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - formant: formant preservation (0.0-1.0)
        """
        # Get parameters
        shift = params.get("shift", 0.5) * 100.0 - 50.0  # -50 to +50 cents
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        formant = params.get("formant", 0.5)

        # Initialize state if needed
        if "detune" not in state:
            state["detune"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0
            }

        # Calculate pitch factor (convert cents to ratio)
        pitch_factor = 2 ** (shift / 1200.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        detune_state = state["detune"]
        detune_state["delay_buffer"][detune_state["buffer_pos"]] = input_sample
        detune_state["buffer_pos"] = (detune_state["buffer_pos"] + 1) % len(detune_state["delay_buffer"])

        # Calculate read position for detuned sample
        read_pos = detune_state["buffer_pos"] - int(len(detune_state["delay_buffer"]) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(detune_state["delay_buffer"])

        # Get detuned sample
        detuned_sample = detune_state["delay_buffer"][int(read_pos)]

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + detuned_sample * mix

        return (output, output)


# Factory function for creating detune effect
def create_detune_effect(sample_rate: int = 44100):
    """Create a detune effect instance"""
    return DetuneEffect(sample_rate)


# Process function for integration with main effects system
def process_detune_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through detune effect (for integration)"""
    effect = DetuneEffect()
    return effect.process(left, right, params, state)
