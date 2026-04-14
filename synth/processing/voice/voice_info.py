"""
Voice information for XG synthesizer voice management.
Contains information about active voices for allocation decisions.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .voice_priority import VoicePriority

if TYPE_CHECKING:
    from ...processing.channel_note import ChannelNote


class VoiceInfo:
    """Information about an active voice for voice management"""

    def __init__(
        self,
        note: int,
        velocity: int,
        channel_note: Any,
        priority: int = VoicePriority.NORMAL,
    ):
        self.note = note
        self.velocity = velocity
        self.channel_note = channel_note
        self.priority = priority
        self.start_time = time.time()
        self.release_time = None
        self.is_releasing = False

    def calculate_priority_score(self) -> float:
        """Calculate priority score for voice stealing decisions"""
        velocity_score = self.velocity / 127.0
        priority_score = self.priority / VoicePriority.HIGHEST
        age_penalty = 0.1 * (time.time() - self.start_time)
        release_penalty = 0.5 if self.is_releasing else 0.0

        return (
            velocity_score * 0.4 + priority_score * 0.4 - age_penalty * 0.1 - release_penalty * 0.1
        )

    def start_release(self):
        """Mark voice as starting release phase"""
        self.is_releasing = True
        self.release_time = time.time()

    def reset(
        self,
        note: int,
        velocity: int,
        channel_note: Any,
        priority: int = VoicePriority.NORMAL,
    ):
        """Reset voice info for reuse from pool"""
        self.note = note
        self.velocity = velocity
        self.channel_note = channel_note
        self.priority = priority
        self.start_time = time.time()
        self.release_time = None
        self.is_releasing = False
