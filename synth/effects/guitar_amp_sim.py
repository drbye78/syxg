"""
Guitar Amp Simulator effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class GuitarAmpSimEffect:
    """
    Guitar Amp Simulator effect implementation.

    Simulates the sound of a guitar amplifier with speaker cabinet.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the guitar amp sim effect state"""
        self.prev_input = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through guitar amp simulator effect.

        Parameters:
        - drive: distortion drive (0.0-1.0)
        - bass: bass frequency boost/cut (0.0-1.0)
        - treble: treble frequency boost/cut (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        drive = params.get("drive", 0.5)
        bass = params.get("bass", 0.5)
        treble = params.get("treble", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "guitar_amp_sim" not in state:
            state["guitar_amp_sim"] = {
                "prev_input": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply distortion (simplified tube amp simulation)
        distorted = math.tanh(input_sample * (1 + drive * 9.0))

        # Apply tone controls (simple EQ)
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)

        # Simulate speaker cabinet (simple reverb-like effect)
        cabinet = equalized * 0.8 + state["guitar_amp_sim"]["prev_input"] * 0.2

        # Update state
        state["guitar_amp_sim"]["prev_input"] = equalized

        # Apply level and return
        return (cabinet * level, cabinet * level)


# Factory function for creating guitar amp sim effect
def create_guitar_amp_sim_effect(sample_rate: int = 44100):
    """Create a guitar amp simulator effect instance"""
    return GuitarAmpSimEffect(sample_rate)


# Process function for integration with main effects system
def process_guitar_amp_sim_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through guitar amp simulator effect (for integration)"""
    effect = GuitarAmpSimEffect()
    return effect.process(left, right, params, state)
