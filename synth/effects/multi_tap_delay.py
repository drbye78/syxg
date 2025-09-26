"""
Multi Tap Delay Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class MultiTapDelay(BaseEffect):
    """
    Multi Tap Delay Effect - Multiple delay taps

    Parameters:
    - taps: Number of delay taps (1-10)
    - feedback: Feedback amount (0.0-1.0)
    - level: Wet/dry mix level (0.0-1.0)
    - spacing: Time spacing between taps (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'taps': 5,          # 1-10
            'feedback': 0.3,    # 0.0-1.0
            'level': 0.5,       # 0.0-1.0
            'spacing': 0.2      # 0.0-1.0
        }
        self.state = {
            'buffer': [0.0] * int(sample_rate),  # 1 second buffer
            'pos': 0,
            'feedback_buffer': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        taps = int(self._state.get('taps', self.parameters['taps']))
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])
        spacing = self._state.get('spacing', self.parameters['spacing'])

        # Clamp taps
        taps = max(1, min(10, taps))

        # Get input sample
        input_sample = (left + right) / 2.0

        # Get delayed samples for each tap
        buffer = self.state['buffer']
        pos = self.state['pos']

        delayed_sum = 0.0
        for i in range(taps):
            # Calculate delay time for this tap
            delay_time = (i + 1) * spacing * 500  # up to 500ms between taps
            delay_samples = int(delay_time * self.sample_rate / 1000.0)

            # Get delayed sample
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sample = buffer[int(delay_pos)]
            delayed_sum += delayed_sample

        # Normalize sum
        delayed_sum /= taps

        # Apply feedback
        feedback_sample = self.state['feedback_buffer'] * feedback
        processed_sample = input_sample + feedback_sample

        # Store in buffer
        buffer[pos] = processed_sample
        self.state['pos'] = (pos + 1) % len(buffer)
        self.state['feedback_buffer'] = processed_sample

        # Mix original and delayed signals
        output = input_sample * (1 - level) + delayed_sum * level

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'buffer': [0.0] * int(self.sample_rate),
            'pos': 0,
            'feedback_buffer': 0.0
        }
