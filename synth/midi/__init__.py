"""
XG Synthesizer MIDI Module

Handles MIDI message processing and routing.
"""

from .message_handler import MIDIMessageHandler
from .buffered_processor import BufferedProcessor

__all__ = [
    "MIDIMessageHandler",
    "BufferedProcessor"
]
