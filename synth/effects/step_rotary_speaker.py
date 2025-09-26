"""
Step Rotary Speaker effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class StepRotarySpeakerEffect:
    """
    Step Rotary Speaker effect implementation.

    Rotary speaker with stepped parameter modulation for rhythmic speaker effects.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the step rotary speaker effect state"""
        self.horn_phase = 0.0
        self.drum_phase = 0.0
        self.horn_speed = 0.0
        self.drum_speed = 0.0
        self.step = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through step rotary speaker effect.

        Parameters:
        - speed: rotation speed (0.0-1.0, maps to 0-5 Hz)
        - balance: horn/drum balance (0.0-1.0)
        - steps: number of steps (1-8 steps)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        speed = params.get("speed", 0.5) * 5.0  # 0-5 Hz
        balance = params.get("balance", 0.5)
        steps = int(params.get("steps", 0.5) * 7) + 1  # 1-8 steps
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "step_rotary_speaker" not in state:
            state["step_rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0,
                "step": 0
            }

        # Update step
        step_rotary_speaker_state = state["step_rotary_speaker"]
        step_rotary_speaker_state["step"] = (step_rotary_speaker_state["step"] + 1) % steps

        # Calculate step-based speed
        step_speed = speed * (step_rotary_speaker_state["step"] + 1) / steps

        # Update phases
        step_rotary_speaker_state["horn_phase"] += 2 * math.pi * step_rotary_speaker_state["horn_speed"] / self.sample_rate
        step_rotary_speaker_state["drum_phase"] += 2 * math.pi * step_rotary_speaker_state["drum_speed"] / self.sample_rate

        # Update speeds with acceleration
        accel = 0.1
        target_speed = step_speed * 0.5 + 0.5  # 0.5-1.0
        step_rotary_speaker_state["horn_speed"] += (target_speed - step_rotary_speaker_state["horn_speed"]) * accel
        step_rotary_speaker_state["drum_speed"] += (target_speed * 0.5 - step_rotary_speaker_state["drum_speed"]) * accel

        # Calculate positions
        horn_pos = math.sin(step_rotary_speaker_state["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(step_rotary_speaker_state["drum_phase"] * 2) * 0.5 + 0.5

        # Get input samples
        input_left = left
        input_right = right

        # Apply rotary speaker effect
        left_out = input_left * (1 - horn_pos) * (1 - drum_pos) + input_left * horn_pos * drum_pos
        right_out = input_right * horn_pos * (1 - drum_pos) + input_right * (1 - horn_pos) * drum_pos

        # Apply balance and level
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)


# Factory function for creating step rotary speaker effect
def create_step_rotary_speaker_effect(sample_rate: int = 44100):
    """Create a step rotary speaker effect instance"""
    return StepRotarySpeakerEffect(sample_rate)


# Process function for integration with main effects system
def process_step_rotary_speaker_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through step rotary speaker effect (for integration)"""
    effect = StepRotarySpeakerEffect()
    return effect.process(left, right, params, state)
