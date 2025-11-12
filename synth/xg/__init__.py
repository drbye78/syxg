"""
XG Synthesizer Module

Handles XG synthesizer components including drum management and channel rendering.
"""

from .drum_manager import DrumManager
from .vectorized_channel_renderer import VectorizedChannelRenderer
from .channel_note import ChannelNote
from .partial_generator import XGPartialGenerator

__all__ = [
    "DrumManager",
    "VectorizedChannelRenderer",
    "ChannelNote",
    "XGPartialGenerator"
]
