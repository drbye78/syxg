"""
Dual Delay Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class DualDelay(BaseEffect):
    """
    Dual Delay Effect - Two independent delay lines

    Parameters:
    - time1: Delay time for first delay line (0-1000 ms)
    - time2: Delay time for second delay line (0-1000 ms)
    - feedback: Feedback amount (0.0-1.0)
    - level: Wet/dry mix level (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'time1': 300.0,     # ms
            'time2': 600.0,     # ms
            'feedback': 0.3,    # 0.0-1.0
            'level': 0.5        # 0.0-1.0
        }
        self.state = {
            'buffer1': [0.0] * int(sample_rate),  # 1 second buffer
            'buffer2': [0.0] * int(sample_rate),  # 1 second buffer
            'pos1': 0,
            'pos2': 0,
            'feedback_buffer': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        time1 = self._state.get('time1', self.parameters['time1'])
        time2 = self._state.get('time2', self.parameters['time2'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])

        # Calculate delay samples
        delay_samples1 = int(time1 * self.sample_rate / 1000.0)
        delay_samples2 = int(time2 * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed samples
        buffer1 = self.state['buffer1']
        buffer2 = self.state['buffer2']
        pos1 = self.state['pos1']
        pos2 = self.state['pos2']

        delay_pos1 = (pos1 - delay_samples1) % len(buffer1)
        delay_pos2 = (pos2 - delay_samples2) % len(buffer2)

        delayed_sample1 = buffer1[int(delay_pos1)]
        delayed_sample2 = buffer2[int(delay_pos2)]

        # Apply feedback
        feedback_sample = self.state['feedback_buffer'] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffers
        buffer1[pos1] = processed_sample
        buffer2[pos2] = processed_sample
        self.state['pos1'] = (pos1 + 1) % len(buffer1)
        self.state['pos2'] = (pos2 + 1) % len(buffer2)
        self.state['feedback_buffer'] = processed_sample

        # Mix original and delayed signals
        output = input_sample * (1 - level) + (delayed_sample1 + delayed_sample2) * level * 0.5

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'buffer1': [0.0] * int(self.sample_rate),
            'buffer2': [0.0] * int(self.sample_rate),
            'pos1': 0,
            'pos2': 0,
            'feedback_buffer': 0.0
        }
