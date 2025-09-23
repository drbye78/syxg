"""
XG Synthesizer Audio Module

Handles audio generation and processing.
"""

from .writer import AudioWriter
from .vectorized_engine import VectorizedAudioEngine

__all__ = [
    "AudioWriter",
    "VectorizedAudioEngine"
]
