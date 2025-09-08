"""
Pan Delay Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class PanDelay(BaseEffect):
    """
    Pan Delay Effect - Delay with panning modulation

    Parameters:
    - time: Delay time (0-1000 ms)
    - feedback: Feedback amount (0.0-1.0)
    - level: Wet/dry mix level (0.0-1.0)
    - rate: Panning modulation rate (0-5 Hz)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'time': 300.0,      # ms
            'feedback': 0.3,    # 0.0-1.0
            'level': 0.5,       # 0.0-1.0
            'rate': 1.0         # Hz
        }
        self.state = {
            'buffer': [0.0] * int(sample_rate),  # 1 second buffer
            'pos': 0,
            'feedback_buffer': 0.0,
            'lfo_phase': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        time = self._state.get('time', self.parameters['time'])
        feedback = self._state.get('feedback', self.parameters['feedback'])
        level = self._state.get('level', self.parameters['level'])
        rate = self._state.get('rate', self.parameters['rate'])

        # Update LFO phase
        self.state['lfo_phase'] += 2 * math.pi * rate / self.sample_rate

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

        # Mix original and delayed signals
        output = input_sample * (1 - level) + delayed_sample * level

        # Apply panning modulation
        pan = math.sin(self.state['lfo_phase']) * 0.5 + 0.5
        left_out = output * (1 - pan)
        right_out = output * pan

        return (left_out, right_out)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'buffer': [0.0] * int(self.sample_rate),
            'pos': 0,
            'feedback_buffer': 0.0,
            'lfo_phase': 0.0
        }
