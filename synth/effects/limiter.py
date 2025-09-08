"""
Limiter Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class Limiter(BaseEffect):
    """
    Limiter Effect - Peak limiting with fast attack

    Parameters:
    - threshold: Limiting threshold (-20 to 0 dB)
    - ratio: Limiting ratio (10:1 to 20:1)
    - attack: Attack time (0.1-10 ms)
    - release: Release time (50-300 ms)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'threshold': -10.0,  # dB
            'ratio': 15.0,       # ratio
            'attack': 1.0,       # ms
            'release': 100.0     # ms
        }
        self.state = {
            'gain': 1.0,
            'attack_counter': 0,
            'release_counter': 0
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
        attack_samples = int(attack_ms * self.sample_rate / 1000.0)
        release_samples = int(release_ms * self.sample_rate / 1000.0)

        # Get input level
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Calculate desired gain
        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            desired_gain = 1.0

        # Apply fast attack, slow release
        if desired_gain < self.state['gain']:
            # Attack (fast)
            self.state['gain'] = desired_gain
        else:
            # Release (slow)
            if self.state['release_counter'] < release_samples:
                self.state['release_counter'] += 1
                factor = self.state['release_counter'] / release_samples
                self.state['gain'] = self.state['gain'] * (1 - factor) + desired_gain * factor
            else:
                self.state['gain'] = desired_gain

        # Apply gain
        output = input_sample * self.state['gain']

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'gain': 1.0,
            'attack_counter': 0,
            'release_counter': 0
        }
