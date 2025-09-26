"""
Step Phaser Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class StepPhaser(BaseEffect):
    """
    Step Phaser Effect - Phaser with stepped modulation

    Parameters:
    - frequency: LFO frequency (0-10 Hz)
    - depth: Modulation depth (0.0-1.0)
    - feedback: Feedback amount (0.0-1.0)
    - steps: Number of steps (1-8)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'frequency': 1.0,     # Hz
            'depth': 0.7,         # 0.0-1.0
            'feedback': 0.3,      # 0.0-1.0
            'steps': 4            # 1-8
        }
        self.state = {
            'lfo_phase': 0.0,
            'allpass_filters': [0.0] * 4,
            'step': 0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        frequency = self._state.get('frequency', self.parameters['frequency'])
        depth = self._state.get('depth', self.parameters['depth'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        steps = int(self._state.get('steps', self.parameters['steps']))

        # Update LFO phase
        lfo_phase = self.state['lfo_phase']
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        # Calculate current step
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != self.state['step']:
            self.state['step'] = step
            # Reset filters when step changes
            self.state['allpass_filters'] = [0.0] * 4

        # Normalize LFO value
        lfo_value = step / (steps - 1)
        lfo_value = lfo_value * depth * 0.5 + 0.5

        # Apply phaser
        input_sample = (left + right) / 2.0
        allpass_filters = self.state['allpass_filters']

        # Simple phaser with 4 allpass stages
        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]

        # Apply feedback
        output = input_sample + feedback * (filtered - input_sample)

        # Save state
        self.state['lfo_phase'] = lfo_phase
        self.state['allpass_filters'] = allpass_filters

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'lfo_phase': 0.0,
            'allpass_filters': [0.0] * 4,
            'step': 0
        }
