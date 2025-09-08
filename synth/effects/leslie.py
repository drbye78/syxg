"""
Leslie speaker effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class LeslieEffect:
    """
    Leslie speaker effect implementation.

    Simulates the sound of a Leslie speaker, commonly used with Hammond organs.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the Leslie effect state"""
        self.horn_phase = 0.0
        self.drum_phase = 0.0
        self.horn_speed = 0.0
        self.drum_speed = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through Leslie speaker effect.

        Parameters:
        - speed: rotation speed (0.0-1.0)
        - balance: horn/drum balance (0.0-1.0)
        - accel: acceleration (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        speed = params.get("speed", 0.5) * 5.0  # 0-5 Hz
        balance = params.get("balance", 0.5)
        accel = params.get("accel", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "leslie" not in state:
            state["leslie"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }

        # Update phases
        leslie_state = state["leslie"]
        leslie_state["horn_phase"] += 2 * math.pi * leslie_state["horn_speed"] / self.sample_rate
        leslie_state["drum_phase"] += 2 * math.pi * leslie_state["drum_speed"] / self.sample_rate

        # Update speeds with acceleration
        target_speed = speed * 0.5 + 0.5  # 0.5-1.0
        leslie_state["horn_speed"] += (target_speed - leslie_state["horn_speed"]) * accel
        leslie_state["drum_speed"] += (target_speed * 0.5 - leslie_state["drum_speed"]) * accel

        # Calculate positions
        horn_pos = math.sin(leslie_state["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(leslie_state["drum_phase"] * 2) * 0.5 + 0.5

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply Leslie effect
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        # Apply balance and level
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)


# Factory function for creating Leslie effect
def create_leslie_effect(sample_rate: int = 44100):
    """Create a Leslie speaker effect instance"""
    return LeslieEffect(sample_rate)


# Process function for integration with main effects system
def process_leslie_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through Leslie speaker effect (for integration)"""
    effect = LeslieEffect()
    return effect.process(left, right, params, state)
