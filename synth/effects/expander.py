"""
Expander Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class Expander(BaseEffect):
    """
    Expander Effect - Dynamic range expansion

    Parameters:
    - threshold: Expansion threshold (-60 to 0 dB)
    - ratio: Expansion ratio (1:1 to 10:1)
    - attack: Attack time (1-100 ms)
    - release: Release time (10-300 ms)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'threshold': -30.0,  # dB
            'ratio': 2.0,        # ratio
            'attack': 10.0,      # ms
            'release': 50.0      # ms
        }
        self.state = {
            'gain': 1.0,
            'counter': 0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        threshold_db = self._state.get('threshold', self.parameters['threshold'])
        ratio = self._state.get('ratio', self.parameters['ratio'])
        attack_ms = self._state.get('attack', self.parameters['attack'])
        release_ms = self._state.get('release', self.parameters['release'])

        # Convert to linear values
        threshold_linear = 10 ** (threshold_db / 20.0)

        # Get input level
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Calculate desired gain
        if input_level < threshold_linear:
            desired_gain = 1.0 / (ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            desired_gain = 1.0

        # Smooth gain changes
        if desired_gain < self.state['gain']:
            # Release (slow)
            self.state['gain'] -= 0.01
            self.state['gain'] = max(desired_gain, self.state['gain'])
        else:
            # Attack (fast)
            self.state['gain'] = desired_gain

        # Apply gain
        output = input_sample * self.state['gain']

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'gain': 1.0,
            'counter': 0
        }
