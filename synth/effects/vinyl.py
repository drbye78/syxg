"""
Vinyl effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class VinylEffect:
    """
    Vinyl effect implementation.

    Simulates the sound of vinyl records with crackle, warp, and surface noise.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the vinyl effect state"""
        self.warp_phase = 0.0
        self.crackle_counter = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through vinyl effect.

        Parameters:
        - warp: warp amount (0.0-1.0)
        - crackle: crackle amount (0.0-1.0)
        - level: output level (0.0-1.0)
        - mode: vinyl mode (0.0-1.0, maps to different vinyl characteristics)
        """
        # Get parameters
        warp = params.get("warp", 0.5)
        crackle = params.get("crackle", 0.5)
        level = params.get("level", 0.5)
        mode = int(params.get("mode", 0.5) * 3)  # 0-3 modes

        # Initialize state if needed
        if "vinyl" not in state:
            state["vinyl"] = {
                "warp_phase": 0.0,
                "crackle_counter": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply warp effect (pitch variation)
        warp_phase = state["vinyl"]["warp_phase"]
        warp_phase += 2 * math.pi * 0.1 / self.sample_rate  # Slow modulation
        warp_amount = math.sin(warp_phase) * warp * 0.01  # Small pitch variation
        warped_sample = input_sample * (1 + warp_amount)

        # Apply crackle effect
        crackle_sample = 0.0
        if crackle > 0:
            crackle_counter = state["vinyl"]["crackle_counter"]
            crackle_counter += 1

            # Generate crackle at random intervals
            if crackle_counter > np.random.randint(1000, 5000):  # Random interval
                crackle_counter = 0
                # Generate crackle noise
                crackle_sample = (np.random.random() - 0.5) * crackle * 0.3

            state["vinyl"]["crackle_counter"] = crackle_counter

        # Apply different vinyl modes
        if mode == 1:  # Old record
            # Add more crackle and high-frequency rolloff
            crackle_sample *= 1.5
            warped_sample *= 0.9  # Slight high-frequency loss
        elif mode == 2:  # Worn record
            # Add distortion and more crackle
            warped_sample = math.tanh(warped_sample * 1.2)
            crackle_sample *= 2.0
        elif mode == 3:  # Damaged record
            # Add heavy distortion and lots of crackle
            warped_sample = math.tanh(warped_sample * 1.5)
            crackle_sample *= 3.0

        # Mix original, warped, and crackle
        output = warped_sample + crackle_sample

        # Apply level
        output *= level

        # Update state
        state["vinyl"]["warp_phase"] = warp_phase

        return (output, output)


# Factory function for creating vinyl effect
def create_vinyl_effect(sample_rate: int = 44100):
    """Create a vinyl effect instance"""
    return VinylEffect(sample_rate)


# Process function for integration with main effects system
def process_vinyl_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through vinyl effect (for integration)"""
    effect = VinylEffect()
    return effect.process(left, right, params, state)
