"""
Pitch Shifter effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class PitchShifterEffect:
    """
    Pitch Shifter effect implementation.

    Changes the pitch of the input signal without changing its duration.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the pitch shifter effect state"""
        # Pitch shifting buffer
        self.delay_buffer = [0.0] * int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer_pos = 0

        # Crossfade state for smooth transitions
        self.crossfade_pos = 0.0
        self.prev_sample = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through pitch shifter effect.

        Parameters:
        - shift: pitch shift amount (0.0-1.0, maps to -12 to +12 semitones)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - formant: formant preservation (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        shift = params.get("shift", 0.5) * 24.0 - 12.0  # -12 to +12 semitones
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        formant = params.get("formant", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "pitch_shifter" not in state:
            state["pitch_shifter"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0,
                "crossfade_pos": 0.0,
                "prev_sample": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        pitch_shifter_state = state["pitch_shifter"]

        # Store in delay buffer
        pitch_shifter_state["delay_buffer"][pitch_shifter_state["buffer_pos"]] = input_sample
        pitch_shifter_state["buffer_pos"] = (pitch_shifter_state["buffer_pos"] + 1) % len(pitch_shifter_state["delay_buffer"])

        # Calculate pitch shift factor
        pitch_factor = 2 ** (shift / 12.0)

        # Calculate read position
        read_pos = pitch_shifter_state["buffer_pos"] - int(len(pitch_shifter_state["delay_buffer"]) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(pitch_shifter_state["delay_buffer"])

        # Get pitch-shifted sample
        shifted_sample = pitch_shifter_state["delay_buffer"][int(read_pos)]

        # Apply feedback
        shifted_sample += feedback * pitch_shifter_state["prev_sample"]

        # Apply formant preservation (simple high-frequency boost)
        if formant > 0:
            # Boost high frequencies for better formant preservation
            formant_boost = 1.0 + formant * 0.5
            shifted_sample *= formant_boost

        # Store for feedback
        pitch_shifter_state["prev_sample"] = shifted_sample

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + shifted_sample * mix

        # Apply level
        return (output * level, output * level)


# Factory function for creating pitch shifter effect
def create_pitch_shifter_effect(sample_rate: int = 44100):
    """Create a pitch shifter effect instance"""
    return PitchShifterEffect(sample_rate)


# Process function for integration with main effects system
def process_pitch_shifter_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through pitch shifter effect (for integration)"""
    effect = PitchShifterEffect()
    return effect.process(left, right, params, state)
