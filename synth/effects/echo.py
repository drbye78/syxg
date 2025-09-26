"""
Echo Effect Implementation
"""

import math
from typing import Dict, Any, Tuple, List
from .base import BaseEffect


class Echo(BaseEffect):
    """
    Echo Effect - Multiple decaying echoes

    Parameters:
    - time: Echo time (0-1000 ms)
    - feedback: Feedback amount (0.0-1.0)
    - level: Output level (0.0-1.0)
    - decay: Decay rate (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'time': 500.0,     # ms
            'feedback': 0.7,   # 0.0-1.0
            'level': 0.5,      # 0.0-1.0
            'decay': 0.8       # 0.0-1.0
        }
        # Create delay buffer for maximum delay time
        max_delay_samples = int(1000 * self.sample_rate / 1000)  # 1 second
        self.state = {
            'buffer': [0.0] * max_delay_samples,
            'pos': 0,
            'feedback_buffer': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        time = self._state.get('time', self.parameters['time'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])
        decay = self._state.get('decay', self.parameters['decay'])

        # Calculate delay in samples
        delay_samples = int(time * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample from buffer
        buffer = self.state['buffer']
        pos = self.state['pos']
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        # Apply feedback with decay
        feedback_sample = self.state['feedback_buffer'] * feedback * decay
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        buffer[pos] = processed_sample
        self.state['pos'] = (pos + 1) % len(buffer)
        self.state['feedback_buffer'] = processed_sample

        # Mix original and delayed signals
        output = input_sample * (1 - level) + delayed_sample * level

        return (output, output)

    def reset(self):
        """Reset effect state"""
        max_delay_samples = int(1000 * self.sample_rate / 1000)
        self.state = {
            'buffer': [0.0] * max_delay_samples,
            'pos': 0,
            'feedback_buffer': 0.0
        }
