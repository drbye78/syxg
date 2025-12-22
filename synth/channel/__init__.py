"""
Channel abstraction layer for XG synthesizer.

Provides MIDI channel management, voice coordination, and note handling.
"""

from .channel import Channel
from .channel_note import ChannelNote
from .vectorized_channel_renderer import VectorizedChannelRenderer

__all__ = ['Channel', 'ChannelNote', 'VectorizedChannelRenderer']
