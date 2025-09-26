"""
Ambience effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class AmbienceEffect:
    """
    Ambience effect implementation.

    Creates spacious ambient soundscapes with reverb and delay elements.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the ambience effect state"""
        # Create delay buffer for ambience
        buffer_size = int(self.sample_rate * 0.5)  # 500ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through ambience effect.

        Parameters:
        - reverb: reverb amount (0.0-1.0)
        - delay: delay amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        reverb = params.get("reverb", 0.5)
        delay = params.get("delay", 0.5)
        mix = params.get("mix", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "ambience" not in state:
            state["ambience"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.5),
                "buffer_pos": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        ambience_state = state["ambience"]
        ambience_state["delay_buffer"][ambience_state["buffer_pos"]] = input_sample
        ambience_state["buffer_pos"] = (ambience_state["buffer_pos"] + 1) % len(ambience_state["delay_buffer"])

        # Calculate delay time based on parameters
        delay_samples = int(delay * len(ambience_state["delay_buffer"]) * 0.5)
        delay_pos = (ambience_state["buffer_pos"] - delay_samples) % len(ambience_state["delay_buffer"])

        # Get delayed sample
        delayed_sample = ambience_state["delay_buffer"][int(delay_pos)]

        # Apply reverb-like processing
        reverb_sample = delayed_sample * reverb

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + reverb_sample * mix

        # Apply level
        output *= level

        return (output, output)


# Factory function for creating ambience effect
def create_ambience_effect(sample_rate: int = 44100):
    """Create an ambience effect instance"""
    return AmbienceEffect(sample_rate)


# Process function for integration with main effects system
def process_ambience_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through ambience effect (for integration)"""
    effect = AmbienceEffect()
    return effect.process(left, right, params, state)
