"""
SF2 Voice Management

Voice allocation, deallocation, and exclusive class voice stealing
according to SF2 specification requirements.
"""

from typing import Dict, List, Any, Optional
import numpy as np

# Forward references
SF2PartialGenerator = Any

class SF2VoiceManager:
    """SF2 Voice Manager with Exclusive Class Support."""

    def __init__(self, max_voices: int = 128):
        self.max_voices = max_voices
        self.active_voices: List['SF2Voice'] = []
        self.voice_pool: List['SF2Voice'] = []
        self.exclusive_classes: Dict[int, List['SF2Voice']] = {}
        self.next_voice_id = 0

    def allocate_voice(self, partial_generator: SF2PartialGenerator) -> Optional['SF2Voice']:
        """Allocate a voice with exclusive class handling."""
        exclusive_class = partial_generator.exclusive_class

        # Handle exclusive class voice stealing
        if exclusive_class > 0:
            existing_voices = self.exclusive_classes.get(exclusive_class, [])
            if existing_voices:
                for voice in existing_voices[:]:
                    self._release_voice_immediately(voice)

        # Allocate voice
        voice = self._find_available_voice(partial_generator)
        if voice:
            voice.voice_id = self.next_voice_id
            self.next_voice_id += 1
            self.active_voices.append(voice)

            if exclusive_class > 0:
                if exclusive_class not in self.exclusive_classes:
                    self.exclusive_classes[exclusive_class] = []
                self.exclusive_classes[exclusive_class].append(voice)

            return voice
        return None

    def _find_available_voice(self, partial_generator: SF2PartialGenerator) -> Optional['SF2Voice']:
        """Find an available voice."""
        if self.voice_pool:
            voice = self.voice_pool.pop()
            voice.reset_with_generator(partial_generator)
            return voice

        if len(self.active_voices) < self.max_voices:
            return SF2Voice(partial_generator)

        return self._steal_voice(partial_generator)

    def _steal_voice(self, partial_generator: SF2PartialGenerator) -> Optional['SF2Voice']:
        """Steal a voice using priority system."""
        # Priority 1: Release phase voices
        release_voices = [v for v in self.active_voices if not v.is_active()]
        if release_voices:
            voice_to_steal = min(release_voices, key=lambda v: v.voice_id)
            self._release_voice_immediately(voice_to_steal)
            voice_to_steal.reset_with_generator(partial_generator)
            return voice_to_steal

        # Priority 2: Oldest voice
        if self.active_voices:
            voice_to_steal = min(self.active_voices, key=lambda v: v.voice_id)
            self._release_voice_immediately(voice_to_steal)
            voice_to_steal.reset_with_generator(partial_generator)
            return voice_to_steal

        return None

    def _release_voice_immediately(self, voice: 'SF2Voice'):
        """Immediately release a voice."""
        if voice in self.active_voices:
            self.active_voices.remove(voice)

        exclusive_class = getattr(voice.partial_generator, 'exclusive_class', 0)
        if exclusive_class > 0 and exclusive_class in self.exclusive_classes:
            if voice in self.exclusive_classes[exclusive_class]:
                self.exclusive_classes[exclusive_class].remove(voice)
                if not self.exclusive_classes[exclusive_class]:
                    del self.exclusive_classes[exclusive_class]

        voice.cleanup()
        self.voice_pool.append(voice)

    def update_active_voices(self):
        """Update active voices and clean up finished ones."""
        finished_voices = []
        for voice in self.active_voices:
            if not voice.is_active():
                finished_voices.append(voice)

        for voice in finished_voices:
            self._release_voice_immediately(voice)

    def get_active_voice_count(self) -> int:
        """Get number of active voices."""
        return len(self.active_voices)

    def get_exclusive_class_info(self) -> Dict[int, int]:
        """Get exclusive class information."""
        return {class_id: len(voices) for class_id, voices in self.exclusive_classes.items()}

    def cleanup_all_voices(self):
        """Clean up all voices."""
        for voice in self.active_voices:
            voice.cleanup()
        for voice in self.voice_pool:
            voice.cleanup()
        self.active_voices.clear()
        self.voice_pool.clear()
        self.exclusive_classes.clear()
        self.next_voice_id = 0


class SF2Voice:
    """SF2 Voice with partial generator management."""

    def __init__(self, partial_generator: SF2PartialGenerator):
        self.partial_generator = partial_generator
        self.note = partial_generator.note
        self.velocity = partial_generator.velocity
        self.active = True
        self.voice_id = 0

    def reset_with_generator(self, partial_generator: SF2PartialGenerator):
        """Reset voice with new generator."""
        if hasattr(self, 'partial_generator'):
            self.partial_generator.cleanup()

        self.partial_generator = partial_generator
        self.note = partial_generator.note
        self.velocity = partial_generator.velocity
        self.active = True
        self.voice_id = 0

    def note_on(self, velocity: int):
        """Start voice playback."""
        self.partial_generator.note_on(velocity)
        self.active = True

    def note_off(self):
        """Release voice."""
        self.partial_generator.note_off()

    def is_active(self) -> bool:
        """Check if voice is active."""
        self.active = self.partial_generator.is_active()
        return self.active

    def generate_samples(self, block_size: int) -> np.ndarray:
        """Generate voice audio."""
        if not self.active:
            return np.zeros(block_size, dtype=np.float32)
        return self.partial_generator.generate_samples(block_size)

    def set_pitch_bend(self, bend_value: float):
        """Apply pitch bend."""
        # Implementation would go here
        pass

    def cleanup(self):
        """Clean up voice resources."""
        self.active = False
