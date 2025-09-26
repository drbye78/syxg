"""
Enhancer effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class EnhancerEffect:
    """
    Enhancer effect implementation.

    Enhances certain frequencies to add clarity and presence to the sound.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the enhancer effect state"""
        self.prev_input = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through enhancer effect.

        Parameters:
        - enhance: enhancement amount (0.0-1.0)
        - bass: bass enhancement (0.0-1.0)
        - treble: treble enhancement (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        enhance = params.get("enhance", 0.5)
        bass = params.get("bass", 0.5)
        treble = params.get("treble", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "enhancer" not in state:
            state["enhancer"] = {
                "prev_input": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply harmonic enhancement
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)

        # Apply frequency-specific enhancement
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)

        # Update state
        state["enhancer"]["prev_input"] = equalized

        # Apply level and return
        return (equalized * level, equalized * level)


# Factory function for creating enhancer effect
def create_enhancer_effect(sample_rate: int = 44100):
    """Create an enhancer effect instance"""
    return EnhancerEffect(sample_rate)


# Process function for integration with main effects system
def process_enhancer_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through enhancer effect (for integration)"""
    effect = EnhancerEffect()
    return effect.process(left, right, params, state)
