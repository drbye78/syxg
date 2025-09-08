"""
Slicer Effect Implementation
"""

import math
from typing import Dict, Any, Tuple
from .base import BaseEffect


class Slicer(BaseEffect):
    """
    Slicer Effect - Rhythmic gate effect

    Parameters:
    - rate: Slice rate (0-10 Hz)
    - depth: Slice depth (0.0-1.0)
    - waveform: LFO waveform (0=sine, 1=triangle, 2=square, 3=sawtooth)
    - phase: LFO phase offset (0.0-1.0)
    """

    def __init__(self, sample_rate: int = 44100):
        super().__init__(sample_rate)
        self.parameters = {
            'rate': 2.0,       # Hz
            'depth': 1.0,      # 0.0-1.0
            'waveform': 2,     # 0-3 (square wave default)
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

        # Normalize LFO for slicing (-1 to 1)
        lfo_value = lfo_value * depth * 0.5 + 0.5

        # Calculate amplitude based on LFO
        amplitude = lfo_value * 2.0 - 1.0

        # Get input sample
        input_sample = (left + right) / 2.0

        # Apply slicing effect
        if input_sample > amplitude:
            output = input_sample
        else:
            output = 0.0

        return (output, output)

    def reset(self):
        """Reset effect state"""
        self.state = {
            'lfo_phase': 0.0
        }
