"""
Reverse Delay Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class ReverseDelay(BaseEffect):
    """
    Reverse Delay Effect - Backwards delay effect

    Parameters:
    - time: Delay time (0-1000 ms)
    - feedback: Feedback amount (0.0-1.0)
    - level: Wet/dry mix level (0.0-1.0)
    - reverse: Reverse amount (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'time': 500.0,      # ms
            'feedback': 0.3,    # 0.0-1.0
            'level': 0.5,       # 0.0-1.0
            'reverse': 0.5      # 0.0-1.0
        }
        self.state = {
            'buffer': [0.0] * int(sample_rate),  # 1 second buffer
            'reverse_buffer': [0.0] * int(sample_rate),
            'pos': 0,
            'feedback_buffer': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        time = self._state.get('time', self.parameters['time'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])
        reverse = self._state.get('reverse', self.parameters['reverse'])

        # Calculate delay samples
        delay_samples = int(time * self.sample_rate / 1000.0)

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed sample
        buffer = self.state['buffer']
        pos = self.state['pos']
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        # Apply feedback
        feedback_sample = self.state['feedback_buffer'] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        buffer[pos] = processed_sample
        self.state['pos'] = (pos + 1) % len(buffer)
        self.state['feedback_buffer'] = processed_sample

        # Handle reverse delay
        reverse_buffer = self.state['reverse_buffer']
        reverse_pos = (pos + delay_samples) % len(reverse_buffer)
        reverse_sample = reverse_buffer[int(reverse_pos)]

        # Store in reverse buffer
        reverse_buffer[pos] = processed_sample

        # Mix original, forward delayed, and reverse delayed signals
        output = (input_sample * (1 - level) +
                 delayed_sample * level * (1 - reverse) +
                 reverse_sample * level * reverse)

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'buffer': [0.0] * int(self.sample_rate),
            'reverse_buffer': [0.0] * int(self.sample_rate),
            'pos': 0,
            'feedback_buffer': 0.0
        }
