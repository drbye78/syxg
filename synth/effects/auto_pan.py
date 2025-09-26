"""
Auto Pan Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class AutoPan(BaseEffect):
    """
    Auto Pan Effect - Automatic panning modulation

    Parameters:
    - rate: Panning rate (0-5 Hz)
    - depth: Panning depth (0.0-1.0)
    - waveform: LFO waveform (0=sine, 1=triangle, 2=square, 3=sawtooth)
    - phase: LFO phase offset (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'rate': 1.0,       # Hz
            'depth': 0.8,      # 0.0-1.0
            'waveform': 0,     # 0-3
            'phase': 0.0       # 0.0-1.0
        }
        self.state = {
            'lfo_phase': 0.0
        }

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """Process a single stereo sample"""
        # Get parameters from state
        rate = self._state.get('rate', self.parameters['rate'])
        depth = self._state.get('depth', self.parameters['depth'])
        waveform = int(self._state.get('waveform', self.parameters['waveform']))
        phase = self._state.get('phase', self.parameters['phase'])

        # Update LFO phase
        self.state['lfo_phase'] += 2 * math.pi * rate / self.sample_rate

        # Generate LFO value based on waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(self.state['lfo_phase'] + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((self.state['lfo_phase'] / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(self.state['lfo_phase'] + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (self.state['lfo_phase'] / (2 * math.pi)) % 1 * 2 - 1

        # Normalize LFO for panning (-1 to 1)
        pan = lfo_value * depth

        # Apply panning
        left_out = left * (1 - pan) + right * pan
        right_out = right * pan + left * (1 - pan)

        return (left_out, right_out)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'lfo_phase': 0.0
        }
