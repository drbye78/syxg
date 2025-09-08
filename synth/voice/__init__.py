"""
Voice management components for XG synthesizer.
Contains voice allocation, priority management, and voice stealing.
"""

from .voice_priority import VoicePriority
from .voice_info import VoiceInfo
from .voice_manager import VoiceManager

__all__ = [
    'VoicePriority',
    'VoiceInfo',
    'VoiceManager'
]
