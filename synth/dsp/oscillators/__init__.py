"""
Oscillators Package

This package contains waveform generator implementations.
"""

from .base import OscillatorInterface
from .sine import SineOscillator
from .sawtooth import SawtoothOscillator
from .square import SquareOscillator
from .triangle import TriangleOscillator

__all__ = [
    'OscillatorInterface',
    'SineOscillator',
    'SawtoothOscillator',
    'SquareOscillator',
    'TriangleOscillator'
]