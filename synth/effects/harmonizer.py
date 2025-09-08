"""
Harmonizer effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class HarmonizerEffect:
    """
    Harmonizer effect implementation.

    Creates harmonic intervals above or below the original pitch.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the harmonizer effect state"""
        # Create delay buffer for pitch shifting
        buffer_size = int(self.sample_rate * 0.1)  # 100ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through harmonizer effect.

        Parameters:
        - intervals: harmonic interval (-12 to +12 semitones)
        - depth: harmonizer depth (0.0-1.0)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        """
        # Get parameters
        intervals = params.get("intervals", 0.5) * 24.0 - 12.0  # -12 to +12 semitones
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)

        # Initialize state if needed
        if "harmonizer" not in state:
            state["harmonizer"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0
            }

        # Calculate pitch factor
        pitch_factor = 2 ** (intervals / 12.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        harmonizer_state = state["harmonizer"]
        harmonizer_state["delay_buffer"][harmonizer_state["buffer_pos"]] = input_sample
        harmonizer_state["buffer_pos"] = (harmonizer_state["buffer_pos"] + 1) % len(harmonizer_state["delay_buffer"])

        # Calculate read position for harmonized sample
        read_pos = harmonizer_state["buffer_pos"] - int(len(harmonizer_state["delay_buffer"]) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(harmonizer_state["delay_buffer"])

        # Get harmonized sample
        harmonized_sample = harmonizer_state["delay_buffer"][int(read_pos)]

        # Apply feedback
        harmonized_sample = harmonized_sample + feedback * input_sample

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + harmonized_sample * mix

        return (output, output)


# Factory function for creating harmonizer effect
def create_harmonizer_effect(sample_rate: int = 44100):
    """Create a harmonizer effect instance"""
    return HarmonizerEffect(sample_rate)


# Process function for integration with main effects system
def process_harmonizer_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through harmonizer effect (for integration)"""
    effect = HarmonizerEffect()
    return effect.process(left, right, params, state)
