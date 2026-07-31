"""Articulation processors — modular DSP for each articulation category."""

from .pitch import PitchModProcessor
from .envelope import EnvelopeProcessor
from .amplitude import AmplitudeModProcessor
from .filter_proc import FilterProcessor
from .noise import NoiseProcessor
from .transient import TransientProcessor
from .formant import FormantProcessor
from .rotary import RotaryProcessor
from .harmonics import HarmonicsProcessor
from .standalone import PedalProcessor, CompositeProcessor

__all__ = [
    "PitchModProcessor",
    "EnvelopeProcessor",
    "AmplitudeModProcessor",
    "FilterProcessor",
    "NoiseProcessor",
    "TransientProcessor",
    "FormantProcessor",
    "RotaryProcessor",
    "HarmonicsProcessor",
    "PedalProcessor",
    "CompositeProcessor",
]
