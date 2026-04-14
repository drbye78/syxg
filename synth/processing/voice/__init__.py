"""
Voice management components for XG synthesizer.

Contains voice allocation, priority management, voice stealing, and new Voice abstraction layer.
"""

from __future__ import annotations

# New Voice abstraction layer
from .voice import Voice
from .voice_factory import VoiceFactory
from .voice_info import VoiceInfo
from .voice_manager import VoiceManager

# Legacy voice management (backward compatibility)
from .voice_priority import VoicePriority

__all__ = [
    # Legacy components
    "VoicePriority",
    "VoiceInfo",
    "VoiceManager",
    # New Voice abstraction
    "Voice",
    "VoiceFactory",
]
