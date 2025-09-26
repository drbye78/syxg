"""
Octave Variation effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class OctaveVariationEffect:
    """
    Octave Variation effect implementation.

    Octave shifting with multiple octave options for creating rich harmonic textures.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the octave variation effect state"""
        # Octave shifting buffers
        self.delay_buffer = [0.0] * int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer_pos = 0

        # Multiple octave states
        self.octave_states = {
            -2: [0.0] * int(self.sample_rate * 0.1),  # Down 2 octaves
            -1: [0.0] * int(self.sample_rate * 0.1),  # Down 1 octave
            1: [0.0] * int(self.sample_rate * 0.1),   # Up 1 octave
            2: [0.0] * int(self.sample_rate * 0.1),   # Up 2 octaves
        }
        self.octave_pos = {k: 0 for k in self.octave_states.keys()}

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through octave variation effect.

        Parameters:
        - shift: octave shift amount (0.0-1.0, maps to -2 to +2 octaves)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - formant: formant preservation (0.0-1.0)
        - level: output level (0.0-1.0)
        - mode: octave mode (0.0-1.0, maps to different octave combinations)
        """
        # Get parameters
        shift = int(params.get("shift", 0.5) * 4) - 2  # -2 to +2 octaves
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        formant = params.get("formant", 0.5)
        level = params.get("level", 0.5)
        mode = int(params.get("mode", 0.5) * 3)  # 0-3 modes

        # Initialize state if needed
        if "octave_variation" not in state:
            state["octave_variation"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0,
                "octave_states": {
                    -2: [0.0] * int(self.sample_rate * 0.1),
                    -1: [0.0] * int(self.sample_rate * 0.1),
                    1: [0.0] * int(self.sample_rate * 0.1),
                    2: [0.0] * int(self.sample_rate * 0.1),
                },
                "octave_pos": {-2: 0, -1: 0, 1: 0, 2: 0}
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        octave_state = state["octave_variation"]
        octave_state["delay_buffer"][octave_state["buffer_pos"]] = input_sample
        octave_state["buffer_pos"] = (octave_state["buffer_pos"] + 1) % len(octave_state["delay_buffer"])

        # Generate octave-shifted signals based on mode
        octave_signals = self._generate_octave_signals(input_sample, shift, mode, octave_state, feedback, formant)

        # Mix all octave signals
        octave_mix = sum(octave_signals.values()) / len(octave_signals) if octave_signals else 0.0

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + octave_mix * mix

        # Apply level
        return (output * level, output * level)

    def _generate_octave_signals(self, input_sample: float, shift: int, mode: int,
                               state: Dict[str, Any], feedback: float, formant: float) -> Dict[int, float]:
        """Generate octave-shifted signals based on mode"""
        octave_signals = {}

        # Define octave combinations based on mode
        if mode == 0:  # Single octave
            octaves = [shift]
        elif mode == 1:  # Dual octaves
            octaves = [shift, shift + 1] if shift >= 0 else [shift, shift - 1]
        elif mode == 2:  # Triple octaves
            octaves = [shift - 1, shift, shift + 1]
        else:  # All octaves
            octaves = [-2, -1, 1, 2]

        for octave in octaves:
            if octave in [-2, -1, 1, 2]:
                # Calculate pitch shift factor
                pitch_factor = 2 ** octave

                # Calculate read position
                read_pos = state["buffer_pos"] - int(len(state["delay_buffer"]) * (1 - pitch_factor))
                if read_pos < 0:
                    read_pos += len(state["delay_buffer"])

                # Get octave-shifted sample
                octave_sample = state["delay_buffer"][int(read_pos)]

                # Apply feedback
                octave_sample += feedback * state["octave_states"][octave][state["octave_pos"][octave]]

                # Apply formant preservation (simple high-frequency boost)
                if formant > 0:
                    # Boost high frequencies for better formant preservation
                    formant_boost = 1.0 + formant * 0.5
                    octave_sample *= formant_boost

                # Store for feedback
                state["octave_states"][octave][state["octave_pos"][octave]] = octave_sample
                state["octave_pos"][octave] = (state["octave_pos"][octave] + 1) % len(state["octave_states"][octave])

                octave_signals[octave] = octave_sample

        return octave_signals


# Factory function for creating octave variation effect
def create_octave_variation_effect(sample_rate: int = 44100):
    """Create an octave variation effect instance"""
    return OctaveVariationEffect(sample_rate)


# Process function for integration with main effects system
def process_octave_variation_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through octave variation effect (for integration)"""
    effect = OctaveVariationEffect()
    return effect.process(left, right, params, state)
