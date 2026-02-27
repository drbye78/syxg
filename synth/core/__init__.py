"""
Core synthesis components for XG synthesizer.
Contains fundamental building blocks for sound synthesis.
"""
from __future__ import annotations

from .envelope import ADSREnvelope
from .oscillator import XGLFO
from .filter import ResonantFilter
from .panner import StereoPanner
from .constants import DEFAULT_CONFIG

__all__ = [
    'ADSREnvelope',
    'XGLFO',
    'ResonantFilter',
    'StereoPanner',
    'DEFAULT_CONFIG'
]
