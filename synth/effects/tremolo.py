"""
Tremolo Effect Implementation

This module implements the XG Tremolo effect with LFO modulation.
"""

import math
from typing import Dict, List, Tuple, Optional, Any

from .base import BaseEffect


class TremoloEffect(BaseEffect):
    """
    XG Tremolo Effect implementation with LFO amplitude modulation.
    """

    # LFO Waveform types
    WAVE_SINE = 0
    WAVE_TRIANGLE = 1
    WAVE_SQUARE = 2
    WAVE_SAWTOOTH = 3

    def __init__(self, sample_rate: int = 44100):
        """Initialize tremolo effect"""
        super().__init__(sample_rate)

        # Effect parameters
        self.rate = 5.0         # LFO rate in Hz
        self.depth = 0.5        # Modulation depth (0.0-1.0)
        self.waveform = self.WAVE_SINE  # LFO waveform type
        self.phase = 0.0        # LFO phase offset (0.0-1.0)

        # Internal state
        self._lfo_phase = 0.0

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process tremolo effect.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        # Update LFO phase
        self._lfo_phase += 2 * math.pi * self.rate / self.sample_rate
        self._lfo_phase %= 2 * math.pi

        # Generate LFO value based on waveform
        if self.waveform == self.WAVE_SINE:
            lfo_value = math.sin(self._lfo_phase + self.phase * 2 * math.pi)
        elif self.waveform == self.WAVE_TRIANGLE:
            lfo_value = 1 - abs((self._lfo_phase / math.pi) % 2 - 1) * 2
        elif self.waveform == self.WAVE_SQUARE:
            lfo_value = 1 if math.sin(self._lfo_phase + self.phase * 2 * math.pi) > 0 else -1
        else:  # SAWTOOTH
            lfo_value = (self._lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        # Normalize LFO to amplitude modulation range
        lfo_value = lfo_value * self.depth * 0.5 + 0.5

        # Apply tremolo (amplitude modulation)
        left_out = left * lfo_value
        right_out = right * lfo_value

        return (left_out, right_out)

    def set_rate(self, rate_hz: float):
        """Set LFO rate in Hz"""
        self.rate = max(0.1, min(20.0, rate_hz))

    def set_depth(self, depth: float):
        """Set modulation depth (0.0-1.0)"""
        self.depth = max(0.0, min(1.0, depth))

    def set_waveform(self, waveform: int):
        """Set LFO waveform type (0-3)"""
        self.waveform = max(0, min(3, waveform))

    def set_phase(self, phase: float):
        """Set LFO phase offset (0.0-1.0)"""
        self.phase = max(0.0, min(1.0, phase))

    def _reset_impl(self):
        """Reset tremolo effect state"""
        self._lfo_phase = 0.0

    def __str__(self) -> str:
        """String representation"""
        wave_names = ["Sine", "Triangle", "Square", "Sawtooth"]
        return f"Tremolo Effect (rate={self.rate:.1f}Hz, depth={self.depth:.2f}, wave={wave_names[self.waveform]})"
