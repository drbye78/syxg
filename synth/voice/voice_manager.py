"""
Voice manager for XG synthesizer.
Handles voice allocation, priority management, and voice stealing.
"""

import time
from typing import Dict, Optional
from .voice_priority import VoicePriority
from .voice_info import VoiceInfo
from ..xg.channel_note import ChannelNote


class VoiceManager:
    """XG Voice Management System with allocation modes and voice stealing"""

    def __init__(self, max_voices: int = 64):
        self.max_voices = max_voices
        self.active_voices: Dict[int, VoiceInfo] = {}  # note -> VoiceInfo
        self.voice_allocation_mode = 0  # Default to basic polyphonic
        self.polyphony_limit = 32  # Default polyphony limit

    def set_allocation_mode(self, mode: int):
        """Set voice allocation mode"""
        self.voice_allocation_mode = mode

    def set_polyphony_limit(self, limit: int):
        """Set maximum polyphony limit"""
        self.polyphony_limit = max(1, min(limit, self.max_voices))

    def can_allocate_voice(self, note: int, velocity: int, priority: int = VoicePriority.NORMAL) -> bool:
        """Check if a new voice can be allocated"""
        current_voice_count = len(self.active_voices)

        # If under polyphony limit, always allow
        if current_voice_count < self.polyphony_limit:
            return True

        # Handle different allocation modes
        if self.voice_allocation_mode == 0:  # Basic polyphonic
            # Basic polyphonic - no stealing, just reject if at limit
            return False
        elif self.voice_allocation_mode == 1:  # Priority-based polyphonic
            return self._can_steal_voice(note, velocity, priority)
        elif self.voice_allocation_mode == 2:  # Advanced polyphonic
            return self._can_steal_voice_advanced(note, velocity, priority)
        elif self.voice_allocation_mode in [3, 4, 5]:  # Monophonic modes
            # Monophonic modes - only one voice at a time
            return current_voice_count == 0 or self._should_replace_mono_voice(note, velocity)

        return False

    def _can_steal_voice(self, note: int, velocity: int, priority: int) -> bool:
        """Check if we can steal a voice using priority-based algorithm"""
        if not self.active_voices:
            return True

        # Find the voice with lowest priority score
        lowest_score = float('inf')
        lowest_note = None

        for voice_note, voice_info in self.active_voices.items():
            score = voice_info.calculate_priority_score()
            if score < lowest_score:
                lowest_score = score
                lowest_note = voice_note

        # Calculate priority score for new voice
        new_voice_score = self._calculate_new_voice_score(note, velocity, priority)

        # Can steal if new voice has higher priority
        return new_voice_score > lowest_score

    def _can_steal_voice_advanced(self, note: int, velocity: int, priority: int) -> bool:
        """Advanced voice stealing with multiple criteria"""
        if not self.active_voices:
            return True

        # Criteria for stealing:
        # 1. Voices in release phase (lowest priority)
        # 2. Lowest velocity
        # 3. Oldest voices
        # 4. Lowest priority level

        release_voices = [(n, v) for n, v in self.active_voices.items() if v.is_releasing]
        if release_voices:
            # Steal from release voices first
            return True

        # Find voice with lowest velocity
        min_velocity = min(v.velocity for v in self.active_voices.values())
        if velocity > min_velocity:
            return True

        # Find oldest voice
        oldest_time = min(v.start_time for v in self.active_voices.values())
        current_time = time.time() if 'time' in globals() else 0
        if current_time - oldest_time > 1.0:  # Voices older than 1 second
            return True

        # Check priority levels
        min_priority = min(v.priority for v in self.active_voices.values())
        if priority > min_priority:
            return True

        return False

    def _should_replace_mono_voice(self, note: int, velocity: int) -> bool:
        """Check if we should replace the current mono voice"""
        if not self.active_voices:
            return True

        # In mono modes, always replace with new note
        # But consider velocity for some modes
        if self.voice_allocation_mode == 4:  # Mono with portamento
            # Consider if portamento is active
            return True
        elif self.voice_allocation_mode == 5:  # Mono with legato
            # Only replace if different note
            current_notes = list(self.active_voices.keys())
            return len(current_notes) == 0 or note != current_notes[0]

        return True  # Mono1 - always replace

    def _calculate_new_voice_score(self, note: int, velocity: int, priority: int) -> float:
        """Calculate priority score for a potential new voice"""
        velocity_score = velocity / 127.0
        priority_score = priority / VoicePriority.HIGHEST
        return velocity_score * 0.6 + priority_score * 0.4

    def allocate_voice(self, note: int, velocity: int, channel_note: ChannelNote,
                      priority: int = VoicePriority.NORMAL) -> Optional[int]:
        """Allocate a voice, potentially stealing an existing one"""
        if not self.can_allocate_voice(note, velocity, priority):
            return None

        # Handle mono modes - clear all existing voices
        if self.voice_allocation_mode in [3, 4, 5]:  # Monophonic modes
            for voice_note in list(self.active_voices.keys()):
                self.deallocate_voice(voice_note)

        # If at polyphony limit, steal a voice
        elif len(self.active_voices) >= self.polyphony_limit:
            stolen_note = self._steal_voice(note, velocity, priority)
            if stolen_note is None:
                return None

        # Allocate new voice
        voice_info = VoiceInfo(note, velocity, channel_note, priority)
        self.active_voices[note] = voice_info

        return note

    def _steal_voice(self, new_note: int, new_velocity: int, new_priority: int) -> Optional[int]:
        """Steal a voice using the current allocation strategy"""
        if self.voice_allocation_mode == 1:  # Priority-based
            return self._steal_by_priority(new_note, new_velocity, new_priority)
        elif self.voice_allocation_mode == 2:  # Advanced
            return self._steal_by_advanced_criteria(new_note, new_velocity, new_priority)
        return None

    def _steal_by_priority(self, new_note: int, new_velocity: int, new_priority: int) -> Optional[int]:
        """Steal voice with lowest priority score"""
        if not self.active_voices:
            return None

        lowest_score = float('inf')
        lowest_note = None

        for voice_note, voice_info in self.active_voices.items():
            score = voice_info.calculate_priority_score()
            if score < lowest_score:
                lowest_score = score
                lowest_note = voice_note

        if lowest_note is not None:
            self.deallocate_voice(lowest_note)
            return lowest_note

        return None

    def _steal_by_advanced_criteria(self, new_note: int, new_velocity: int, new_priority: int) -> Optional[int]:
        """Advanced voice stealing algorithm"""
        # Priority order for stealing:
        # 1. Voices in release phase
        # 2. Lowest velocity
        # 3. Oldest voices
        # 4. Lowest priority

        # 1. Try to steal from release voices first
        release_voices = [(n, v) for n, v in self.active_voices.items() if v.is_releasing]
        if release_voices:
            stolen_note = release_voices[0][0]
            self.deallocate_voice(stolen_note)
            return stolen_note

        # 2. Steal lowest velocity voice
        min_velocity = min(v.velocity for v in self.active_voices.values())
        lowest_velocity_notes = [n for n, v in self.active_voices.items() if v.velocity == min_velocity]
        if lowest_velocity_notes:
            stolen_note = lowest_velocity_notes[0]
            self.deallocate_voice(stolen_note)
            return stolen_note

        # 3. Steal oldest voice
        oldest_time = min(v.start_time for v in self.active_voices.values())
        oldest_notes = [n for n, v in self.active_voices.items() if v.start_time == oldest_time]
        if oldest_notes:
            stolen_note = oldest_notes[0]
            self.deallocate_voice(stolen_note)
            return stolen_note

        # 4. Steal lowest priority voice
        min_priority = min(v.priority for v in self.active_voices.values())
        lowest_priority_notes = [n for n, v in self.active_voices.items() if v.priority == min_priority]
        if lowest_priority_notes:
            stolen_note = lowest_priority_notes[0]
            self.deallocate_voice(stolen_note)
            return stolen_note

        return None

    def deallocate_voice(self, note: int):
        """Deallocate a voice"""
        if note in self.active_voices:
            voice_info = self.active_voices[note]
            voice_info.start_release()
            # In a real implementation, we'd wait for the release to complete
            # For now, we'll remove it immediately for simplicity
            del self.active_voices[note]

    def start_voice_release(self, note: int):
        """Start release phase for a voice"""
        if note in self.active_voices:
            self.active_voices[note].start_release()

    def get_active_voice_count(self) -> int:
        """Get current number of active voices"""
        return len(self.active_voices)

    def get_voice_info(self, note: int) -> Optional[VoiceInfo]:
        """Get voice information for a specific note"""
        return self.active_voices.get(note)

    def cleanup_released_voices(self):
        """Clean up voices that have finished their release phase"""
        # In a real implementation, this would check if envelopes have completed
        # For now, we'll clean up voices that have been in release for too long
        current_time = time.time() if 'time' in globals() else 0
        to_remove = []

        for note, voice_info in self.active_voices.items():
            if voice_info.is_releasing and voice_info.release_time:
                if current_time - voice_info.release_time > 2.0:  # 2 second release timeout
                    to_remove.append(note)

        for note in to_remove:
            del self.active_voices[note]

    def get_allocation_mode_name(self) -> str:
        """Get human-readable name for current allocation mode"""
        mode_names = {
            0: "Poly1 (Basic)",
            1: "Poly2 (Priority)",
            2: "Poly3 (Advanced)",
            3: "Mono1 (Basic)",
            4: "Mono2 (Portamento)",
            5: "Mono3 (Legato)"
        }
        return mode_names.get(self.voice_allocation_mode, "Unknown")
