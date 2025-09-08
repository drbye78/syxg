"""
Gate Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class Gate(BaseEffect):
    """
    Gate Effect - Noise Gate implementation

    Parameters:
    - threshold: Gate threshold (-80 to -10 dB)
    - reduction: Reduction amount (0-60 dB)
    - attack: Attack time (1-10 ms)
    - hold: Hold time (0-1000 ms)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'threshold': -40.0,  # dB
            'reduction': 40.0,   # dB
            'attack': 5.0,       # ms
            'hold': 100.0        # ms
        }
        self.state = {
            'open': False,
            'hold_counter': 0,
            'gain': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        threshold_db = self._state.get('threshold', self.parameters['threshold'])
        reduction_db = self._state.get('reduction', self.parameters['reduction'])
        attack_ms = self._state.get('attack', self.parameters['attack'])
        hold_ms = self._state.get('hold', self.parameters['hold'])

        # Convert to linear values
        threshold_linear = 10 ** (threshold_db / 20.0)
        reduction_factor = 10 ** (-reduction_db / 20.0)
        attack_samples = int(attack_ms * self.sample_rate / 1000.0)
        hold_samples = int(hold_ms * self.sample_rate / 1000.0)

        # Get input level
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        # Check threshold
        if input_level > threshold_linear:
            # Signal above threshold, open gate
            self.state['open'] = True
            self.state['hold_counter'] = hold_samples
        else:
            # Signal below threshold, check hold
            if self.state['hold_counter'] > 0:
                self.state['hold_counter'] -= 1
            else:
                self.state['open'] = False

        # Calculate gain
        if self.state['open']:
            # Smooth opening
            if self.state['gain'] < 1.0:
                self.state['gain'] += 1.0 / max(1, attack_samples)
                self.state['gain'] = min(1.0, self.state['gain'])
        else:
            # Smooth closing
            self.state['gain'] *= 0.99  # Exponential decay

        # Apply reduction
        if not self.state['open']:
            self.state['gain'] *= reduction_factor

        # Apply gain
        output = input_sample * self.state['gain']

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'open': False,
            'hold_counter': 0,
            'gain': 0.0
        }
