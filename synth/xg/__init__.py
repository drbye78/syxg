"""
XG Synthesizer Module

Handles XG-specific components including drum management and XG parameter handling.
Note: Channel and partial components have been moved to dedicated packages.
"""
from __future__ import annotations

from .drum_manager import DrumManager
# Note: Channel and partial components moved to synth.channel and synth.partial

__all__ = [
    "DrumManager"
    # Channel and partial components available via synth.channel and synth.partial
]
