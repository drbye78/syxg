"""
Cross Delay Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class CrossDelay(BaseEffect):
    """
    Cross Delay Effect - Delay with cross-feedback between channels

    Parameters:
    - time: Delay time (0-1000 ms)
    - feedback: Feedback amount (0.0-1.0)
    - level: Wet/dry mix level (0.0-1.0)
    - cross: Cross-feedback amount (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'time': 300.0,      # ms
            'feedback': 0.3,    # 0.0-1.0
            'level': 0.5,       # 0.0-1.0
            'cross': 0.5        # 0.0-1.0
        }
        self.state = {
            'left_buffer': [0.0] * int(sample_rate),   # 1 second buffer
            'right_buffer': [0.0] * int(sample_rate),  # 1 second buffer
            'left_pos': 0,
            'right_pos': 0,
            'left_feedback': 0.0,
            'right_feedback': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        time = self._state.get('time', self.parameters['time'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])
        cross = self._state.get('cross', self.parameters['cross'])

        # Calculate delay samples
        delay_samples = int(time * self.sample_rate / 1000.0)

        # Get delayed samples
        left_buffer = self.state['left_buffer']
        right_buffer = self.state['right_buffer']
        left_pos = self.state['left_pos']
        right_pos = self.state['right_pos']

        left_delay_pos = (left_pos - delay_samples) % len(left_buffer)
        right_delay_pos = (right_pos - delay_samples) % len(right_buffer)

        left_delayed = left_buffer[int(left_delay_pos)]
        right_delayed = right_buffer[int(right_delay_pos)]

        # Apply feedback with cross-coupling
        left_feedback = self.state['left_feedback'] * feedback * (1 - cross)
        right_feedback = self.state['right_feedback'] * feedback * (1 - cross)
        cross_left_feedback = self.state['right_feedback'] * feedback * cross
        cross_right_feedback = self.state['left_feedback'] * feedback * cross

        processed_left = left + left_feedback + cross_left_feedback
        processed_right = right + right_feedback + cross_right_feedback

        # Store in buffers
        left_buffer[left_pos] = processed_left
        right_buffer[right_pos] = processed_right
        self.state['left_pos'] = (left_pos + 1) % len(left_buffer)
        self.state['right_pos'] = (right_pos + 1) % len(right_buffer)
        self.state['left_feedback'] = processed_left
        self.state['right_feedback'] = processed_right

        # Mix original and delayed signals
        left_out = left * (1 - level) + left_delayed * level
        right_out = right * (1 - level) + right_delayed * level

        return (left_out, right_out)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'left_buffer': [0.0] * int(self.sample_rate),
            'right_buffer': [0.0] * int(self.sample_rate),
            'left_pos': 0,
            'right_pos': 0,
            'left_feedback': 0.0,
            'right_feedback': 0.0
        }
