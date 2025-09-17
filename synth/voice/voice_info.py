"""
Voice information for XG synthesizer voice management.
Contains information about active voices for allocation decisions.
"""

import time
from typing import Optional
from .voice_priority import VoicePriority
from ..xg.channel_note import ChannelNote


class VoiceInfo:
    """Information about an active voice for voice management"""
    def __init__(self, note: int, velocity: int, channel_note: ChannelNote, priority: int = VoicePriority.NORMAL):
        self.note = note
        self.velocity = velocity
        self.channel_note = channel_note
        self.priority = priority
        self.start_time = time.time()
        self.release_time = None
        self.is_releasing = False

    def calculate_priority_score(self) -> float:
        """Calculate priority score for voice stealing decisions"""
        # Higher velocity = higher priority
        velocity_score = self.velocity / 127.0

        # Higher priority level = higher priority
        priority_score = self.priority / VoicePriority.HIGHEST

        # More recent notes get slightly higher priority
        age_penalty = 0.1 * (time.time() - self.start_time)

        # Notes in release phase get lower priority
        release_penalty = 0.5 if self.is_releasing else 0.0

        return velocity_score * 0.4 + priority_score * 0.4 - age_penalty * 0.1 - release_penalty * 0.1

    def start_release(self):
        """Mark voice as starting release phase"""
        self.is_releasing = True
        self.release_time = time.time()
