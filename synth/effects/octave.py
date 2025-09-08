"""
Octave effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class OctaveEffect:
    """
    Octave effect implementation.

    Changes the pitch of the input signal by integer octaves up or down.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the octave effect state"""
        # Create delay buffer for pitch shifting
        buffer_size = int(self.sample_rate * 0.1)  # 100ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through octave effect.

        Parameters:
        - shift: octave shift (-2 to +2 octaves)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - formant: formant preservation (0.0-1.0)
        """
        # Get parameters
        shift = int(params.get("shift", 0.5) * 4) - 2  # -2 to +2 octaves
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        formant = params.get("formant", 0.5)

        # Initialize state if needed
        if "octave" not in state:
            state["octave"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0
            }

        # Calculate pitch factor
        pitch_factor = 2 ** shift

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        octave_state = state["octave"]
        octave_state["delay_buffer"][octave_state["buffer_pos"]] = input_sample
        octave_state["buffer_pos"] = (octave_state["buffer_pos"] + 1) % len(octave_state["delay_buffer"])

        # Calculate read position for pitch-shifted sample
        read_pos = octave_state["buffer_pos"] - int(len(octave_state["delay_buffer"]) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(octave_state["delay_buffer"])

        # Get pitch-shifted sample
        shifted_sample = octave_state["delay_buffer"][int(read_pos)]

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + shifted_sample * mix

        return (output, output)


# Factory function for creating octave effect
def create_octave_effect(sample_rate: int = 44100):
    """Create an octave effect instance"""
    return OctaveEffect(sample_rate)


# Process function for integration with main effects system
def process_octave_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through octave effect (for integration)"""
    effect = OctaveEffect()
    return effect.process(left, right, params, state)
