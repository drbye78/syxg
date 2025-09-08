"""
Rotary Speaker Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class RotarySpeaker(BaseEffect):
    """
    Rotary Speaker Effect - Leslie speaker simulation

    Parameters:
    - speed: Rotation speed (0.0-1.0)
    - balance: Horn/drum balance (0.0-1.0)
    - accel: Acceleration (0.0-1.0)
    - level: Output level (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'speed': 0.5,      # 0.0-1.0
            'balance': 0.5,    # 0.0-1.0
            'accel': 0.1,      # 0.0-1.0
            'level': 1.0       # 0.0-1.0
        }
        self.state = {
            'horn_phase': 0.0,
            'drum_phase': 0.0,
            'horn_speed': 0.0,
            'drum_speed': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        speed = self._state.get('speed', self.parameters['speed'])
        balance = self._state.get('balance', self.parameters['balance'])
        accel = self._state.get('accel', self.parameters['accel'])
        level = self._state.get('level', self.parameters['level'])

        # Update phases
        self.state['horn_phase'] += 2 * math.pi * self.state['horn_speed'] / self.sample_rate
        self.state['drum_phase'] += 2 * math.pi * self.state['drum_speed'] / self.sample_rate

        # Update speeds with acceleration
        target_speed = speed * 5.0  # 0-5 Hz
        self.state['horn_speed'] += (target_speed - self.state['horn_speed']) * accel
        self.state['drum_speed'] += (target_speed * 0.5 - self.state['drum_speed']) * accel

        # Calculate positions
        horn_pos = math.sin(self.state['horn_phase']) * 0.5 + 0.5
        drum_pos = math.sin(self.state['drum_phase'] * 2) * 0.5 + 0.5

        # Apply rotary effect
        input_sample = (left + right) / 2.0

        # Mix channels based on positions
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        # Apply balance and level
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'horn_phase': 0.0,
            'drum_phase': 0.0,
            'horn_speed': 0.0,
            'drum_speed': 0.0
        }
