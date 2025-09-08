"""
Step Flanger Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class StepFlanger(BaseEffect):
    """
    Step Flanger Effect - Flanger with stepped modulation

    Parameters:
    - frequency: LFO frequency (0-5 Hz)
    - depth: Modulation depth (0.0-1.0)
    - feedback: Feedback amount (0.0-1.0)
    - steps: Number of steps (1-8)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'frequency': 0.5,     # Hz
            'depth': 0.8,         # 0.0-1.0
            'feedback': 0.6,      # 0.0-1.0
            'steps': 4            # 1-8
        }
        self.state = {
            'lfo_phase': 0.0,
            'delay_buffer': [0.0] * int(0.02 * sample_rate),  # 20ms buffer
            'buffer_pos': 0,
            'feedback_buffer': 0.0,
            'step': 0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        frequency = self._state.get('frequency', self.parameters['frequency'])
        depth = self._state.get('depth', self.parameters['depth'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        steps = int(self._state.get('steps', self.parameters['steps']))

        # Limit frequency for flanger
        frequency = min(frequency, 10.0)

        # Update LFO phase
        lfo_phase = self.state['lfo_phase']
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        # Calculate current step
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != self.state['step']:
            self.state['step'] = step
            # Reset buffer when step changes
            self.state['delay_buffer'] = [0.0] * len(self.state['delay_buffer'])

        # Normalize LFO value
        lfo_value = step / (steps - 1)
        lfo_value = lfo_value * depth * 0.5 + 0.5

        # Calculate current delay (0-20ms)
        delay_samples = int(lfo_value * len(self.state['delay_buffer']) * 0.5)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample
        buffer = self.state['delay_buffer']
        pos = self.state['buffer_pos']
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        # Apply feedback
        feedback_sample = self.state['feedback_buffer'] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        buffer[pos] = processed_sample
        self.state['buffer_pos'] = (pos + 1) % len(buffer)
        self.state['feedback_buffer'] = processed_sample

        # Mix original and delayed signals
        output = input_sample * (1 - depth) + delayed_sample * depth

        # Save state
        self.state['lfo_phase'] = lfo_phase

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'lfo_phase': 0.0,
            'delay_buffer': [0.0] * int(0.02 * self.sample_rate),
            'buffer_pos': 0,
            'feedback_buffer': 0.0,
            'step': 0
        }
