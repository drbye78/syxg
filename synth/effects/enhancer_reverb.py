"""
Enhancer/Reverb effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class EnhancerReverbEffect:
    """
    Enhancer/Reverb effect implementation.

    Combines harmonic enhancement with reverb processing.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the enhancer/reverb effect state"""
        # Create delay buffer for reverb
        buffer_size = int(self.sample_rate * 0.5)  # 500ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through enhancer/reverb effect.

        Parameters:
        - enhance: enhancement amount (0.0-1.0)
        - reverb: reverb amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        enhance = params.get("enhance", 0.5)
        reverb = params.get("reverb", 0.5)
        mix = params.get("mix", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "enhancer_reverb" not in state:
            state["enhancer_reverb"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.5),
                "buffer_pos": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply harmonic enhancement
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)

        # Store in delay buffer
        enhancer_reverb_state = state["enhancer_reverb"]
        enhancer_reverb_state["delay_buffer"][enhancer_reverb_state["buffer_pos"]] = enhanced
        enhancer_reverb_state["buffer_pos"] = (enhancer_reverb_state["buffer_pos"] + 1) % len(enhancer_reverb_state["delay_buffer"])

        # Calculate delay time for reverb
        delay_samples = int(0.3 * self.sample_rate)  # 300ms delay
        delay_pos = (enhancer_reverb_state["buffer_pos"] - delay_samples) % len(enhancer_reverb_state["delay_buffer"])

        # Get delayed sample
        delayed_sample = enhancer_reverb_state["delay_buffer"][int(delay_pos)]

        # Apply reverb processing
        reverb_sample = delayed_sample * reverb

        # Mix dry and wet signals
        output = enhanced * (1 - mix) + reverb_sample * mix

        # Apply level
        output *= level

        return (output, output)


# Factory function for creating enhancer/reverb effect
def create_enhancer_reverb_effect(sample_rate: int = 44100):
    """Create an enhancer/reverb effect instance"""
    return EnhancerReverbEffect(sample_rate)


# Process function for integration with main effects system
def process_enhancer_reverb_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through enhancer/reverb effect (for integration)"""
    effect = EnhancerReverbEffect()
    return effect.process(left, right, params, state)
