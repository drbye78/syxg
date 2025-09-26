"""
Harmonizer Variation effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class HarmonizerVariationEffect:
    """
    Harmonizer Variation effect implementation.

    Pitch shifting with harmony generation for creating vocal harmonies.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the harmonizer variation effect state"""
        # Pitch shifting buffers
        self.delay_buffer = [0.0] * int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer_pos = 0

        # Harmony state
        self.harmony_buffer = [0.0] * int(self.sample_rate * 0.1)
        self.harmony_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through harmonizer variation effect.

        Parameters:
        - intervals: harmony intervals (0.0-1.0, maps to different interval sets)
        - depth: harmony depth (0.0-1.0)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - detune: detuning amount (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        intervals = int(params.get("intervals", 0.5) * 7)  # 0-7 interval sets
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        detune = params.get("detune", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "harmonizer_variation" not in state:
            state["harmonizer_variation"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0,
                "harmony_buffer": [0.0] * int(self.sample_rate * 0.1),
                "harmony_pos": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        harmonizer_state = state["harmonizer_variation"]
        harmonizer_state["delay_buffer"][harmonizer_state["buffer_pos"]] = input_sample
        harmonizer_state["buffer_pos"] = (harmonizer_state["buffer_pos"] + 1) % len(harmonizer_state["delay_buffer"])

        # Generate harmonies based on interval set
        harmony_intervals = self._get_harmony_intervals(intervals)

        # Mix harmonies
        harmony_mix = 0.0
        for interval in harmony_intervals:
            # Calculate pitch shift factor
            pitch_factor = 2 ** (interval / 12.0)

            # Add detuning
            detune_factor = 1.0 + (detune - 0.5) * 0.02
            pitch_factor *= detune_factor

            # Calculate read position
            read_pos = harmonizer_state["buffer_pos"] - int(len(harmonizer_state["delay_buffer"]) * (1 - pitch_factor))
            if read_pos < 0:
                read_pos += len(harmonizer_state["delay_buffer"])

            # Get harmony sample
            harmony_sample = harmonizer_state["delay_buffer"][int(read_pos)]

            # Apply feedback
            harmony_sample += feedback * harmonizer_state["harmony_buffer"][harmonizer_state["harmony_pos"]]

            harmony_mix += harmony_sample

        # Average harmonies
        if len(harmony_intervals) > 0:
            harmony_mix /= len(harmony_intervals)

        # Store harmony for feedback
        harmonizer_state["harmony_buffer"][harmonizer_state["harmony_pos"]] = harmony_mix
        harmonizer_state["harmony_pos"] = (harmonizer_state["harmony_pos"] + 1) % len(harmonizer_state["harmony_buffer"])

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + harmony_mix * mix * depth

        # Apply level
        return (output * level, output * level)

    def _get_harmony_intervals(self, interval_set: int) -> List[float]:
        """Get harmony intervals for the specified set"""
        interval_sets = [
            [4.0, 7.0],      # Major third + fifth
            [3.0, 7.0],      # Minor third + fifth
            [5.0, 9.0],      # Perfect fourth + major sixth
            [7.0, 12.0],     # Perfect fifth + octave
            [4.0, 9.0],      # Major third + major sixth
            [3.0, 8.0],      # Minor third + major sixth
            [2.0, 7.0],      # Major second + fifth
            [5.0, 12.0],     # Perfect fourth + octave
        ]

        return interval_sets[min(interval_set, len(interval_sets) - 1)]


# Factory function for creating harmonizer variation effect
def create_harmonizer_variation_effect(sample_rate: int = 44100):
    """Create a harmonizer variation effect instance"""
    return HarmonizerVariationEffect(sample_rate)


# Process function for integration with main effects system
def process_harmonizer_variation_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through harmonizer variation effect (for integration)"""
    effect = HarmonizerVariationEffect()
    return effect.process(left, right, params, state)
