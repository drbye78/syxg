"""
Doubler effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class DoublerEffect:
    """
    Doubler effect implementation.

    Creates a doubling effect by mixing the original signal with a slightly delayed and pitch-modulated version.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the doubler effect state"""
        # Create delay buffer for doubling
        buffer_size = int(self.sample_rate * 0.1)  # 100ms buffer
        self.delay_buffer = [0.0] * buffer_size
        self.buffer_pos = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through doubler effect.

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
        if "doubler" not in state:
            state["doubler"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        doubler_state = state["doubler"]
        doubler_state["delay_buffer"][doubler_state["buffer_pos"]] = input_sample
        doubler_state["buffer_pos"] = (doubler_state["buffer_pos"] + 1) % len(doubler_state["delay_buffer"])

        # Calculate delay for doubling effect (around 20-30ms)
        delay_samples = int(0.025 * self.sample_rate)  # 25ms delay
        delay_pos = (doubler_state["buffer_pos"] - delay_samples) % len(doubler_state["delay_buffer"])

        # Get delayed sample
        delayed_sample = doubler_state["delay_buffer"][int(delay_pos)]

        # Apply enhancement (harmonic enhancement)
        enhanced_sample = delayed_sample + enhance * math.sin(delayed_sample * math.pi)

        # Apply reverb-like processing
        reverb_sample = enhanced_sample * reverb

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + reverb_sample * mix

        # Apply level
        output *= level

        return (output, output)


# Factory function for creating doubler effect
def create_doubler_effect(sample_rate: int = 44100):
    """Create a doubler effect instance"""
    return DoublerEffect(sample_rate)


# Process function for integration with main effects system
def process_doubler_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through doubler effect (for integration)"""
    effect = DoublerEffect()
    return effect.process(left, right, params, state)
