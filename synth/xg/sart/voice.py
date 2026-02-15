"""
Voice management for polyphonic synthesis.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class VoiceState:
    """Represents the state of a single voice."""
    note: int = -1
    velocity: int = 0
    frequency: float = 440.0
    start_time: float = 0.0
    sample_index: int = 0
    active: bool = False
    articulation: str = 'normal'
    pitch_bend: float = 0.0  # Semitones
    mod_wheel: float = 0.0   # 0-1


@dataclass
class NoteEvent:
    """Represents a note event for the scheduler."""
    note: int
    velocity: int
    start_time: float
    duration: float
    frequency: float = 440.0
    articulation: str = 'normal'
    pitch_bend: float = 0.0
    mod_wheel: float = 0.0


class VoiceManager:
    """
    Polyphonic voice manager with voice stealing.
    """
    
    def __init__(self, max_voices: int = 64, sample_rate: int = 44100):
        self.max_voices = max_voices
        self.sample_rate = sample_rate
        self.voices: List[VoiceState] = [VoiceState() for _ in range(max_voices)]
        self.free_voices: List[int] = list(range(max_voices))
        self.active_voices: List[int] = []
    
    def allocate_voice(self, note: int, velocity: int, frequency: float,
                       start_time: float, articulation: str) -> Optional[int]:
        """Allocate a voice for a new note."""
        if not self.free_voices:
            # Voice stealing - steal the oldest voice
            if self.active_voices:
                voice_id = self.active_voices[0]
                self.active_voices.pop(0)
            else:
                return None  # No voices available
        else:
            voice_id = self.free_voices.pop()
        
        voice = self.voices[voice_id]
        voice.note = note
        voice.velocity = velocity
        voice.frequency = frequency
        voice.start_time = start_time
        voice.active = True
        voice.sample_index = 0
        voice.articulation = articulation
        voice.pitch_bend = 0.0
        voice.mod_wheel = 0.0
        
        self.active_voices.append(voice_id)
        return voice_id
    
    def release_voice(self, voice_id: int):
        """Release a voice (note off)."""
        if 0 <= voice_id < self.max_voices:
            self.voices[voice_id].active = False
            if voice_id in self.active_voices:
                self.active_voices.remove(voice_id)
            self.free_voices.append(voice_id)
    
    def release_note(self, note: int):
        """Release all voices playing a specific note."""
        for voice_id in list(self.active_voices):
            if self.voices[voice_id].note == note:
                self.release_voice(voice_id)
    
    def get_active_voices(self) -> List[Tuple[int, VoiceState]]:
        """Get all currently active voices."""
        return [(i, v) for i, v in enumerate(self.voices) if v.active]
    
    def all_notes_off(self):
        """Release all voices."""
        for voice_id in list(self.active_voices):
            self.release_voice(voice_id)
    
    def update_pitch_bend(self, note: int, pitch_bend: float):
        """Update pitch bend for a specific note."""
        for voice_id in self.active_voices:
            if self.voices[voice_id].note == note:
                self.voices[voice_id].pitch_bend = pitch_bend
    
    def update_mod_wheel(self, note: int, mod_wheel: float):
        """Update mod wheel for a specific note."""
        for voice_id in self.active_voices:
            if self.voices[voice_id].note == note:
                self.voices[voice_id].mod_wheel = mod_wheel
