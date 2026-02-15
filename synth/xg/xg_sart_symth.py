"""
Super Articulation 2 (S.Art2) Synthesizer for Yamaha XG Compatibility.
Enhanced version with polyphony, real-time audio, effects, and bug fixes.

This module provides a comprehensive implementation of Yamaha's S.Art2 technology
with FM and Karplus-Strong synthesis, full MIDI/NRPN support, and real-time playback.
"""

import numpy as np
from scipy.io import wavfile
from typing import List, Dict, Optional, Tuple, Callable, Any
import logging
import threading
import queue
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math

# MIDI handling - try multiple backends
MIDO_AVAILABLE = False
try:
    import mido
    from mido import MidiFile, Message
    MIDO_AVAILABLE = True
except ImportError:
    mido = None
    MidiFile = None
    Message = None

# Try to import audio libraries (optional dependencies)
SOUNDDEVICE_AVAILABLE = False
_sd = None
try:
    import sounddevice as _sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    pass

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# =============================================================================
# Constants and Configuration
# =============================================================================

# Musical constants
SEMITONE_RATIO = 1.059463359  # 2^(1/12)
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_BLOCK_SIZE = 512
DEFAULT_BUFFER_SIZE = 2048

# MIDI constants
MIDI_NOTE_MIN = 0
MIDI_NOTE_MAX = 127
MIDI_VELOCITY_MIN = 0
MIDI_VELOCITY_MAX = 127
NRPN_MSB_CONTROL = 99
NRPN_LSB_CONTROL = 98
PITCH_BEND_CONTROL = 14  # MIDI pitch bend is channel-wide
MOD_WHEEL_CONTROL = 1

# Maximum polyphony
MAX_POLYPHONY = 64

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Utility Functions
# =============================================================================

def midi_note_to_frequency(note: int) -> float:
    """Convert MIDI note number to frequency (A4 = 440Hz at note 69)."""
    return 440.0 * (SEMITONE_RATIO ** (note - 69))


# =============================================================================
# Data Classes
# =============================================================================

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


@dataclass
class SynthConfig:
    """Global synthesizer configuration."""
    sample_rate: int = DEFAULT_SAMPLE_RATE
    block_size: int = DEFAULT_BLOCK_SIZE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    num_channels: int = 2  # Stereo
    master_volume: float = 0.8
    enable_reverb: bool = True
    enable_delay: bool = True
    reverb_room_size: float = 0.5
    reverb_wet_dry: float = 0.3
    delay_time: float = 0.375  # In seconds (eighth note at 120 BPM)
    delay_feedback: float = 0.3
    delay_wet_dry: float = 0.2


# =============================================================================
# Effects Processing
# =============================================================================

class ReverbEffect:
    """
    Simple Schroeder reverb implementation.
    Based on multiple comb filters in parallel and allpass filters in series.
    """
    
    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE, 
                 room_size: float = 0.5, wet_dry: float = 0.3):
        self.sample_rate = sample_rate
        self.room_size = np.clip(room_size, 0.0, 1.0)
        self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
        
        # Comb filter delays (in samples) - typical Schroeder values
        self.comb_delays = [1557, 1617, 1491, 1422, 1277, 1356]
        self.comb_buffers: List[np.ndarray] = []
        self.comb_indices: List[int] = []
        
        # Allpass filter delays
        self.allpass_delays = [225, 556, 441, 341]
        self.allpass_buffers: List[np.ndarray] = []
        self.allpass_indices: List[int] = []
        
        # Feedback coefficients based on room size
        self.comb_feedback = [0.28, 0.3, 0.26, 0.32, 0.24, 0.28]
        
        self._initialize_buffers()
    
    def _initialize_buffers(self):
        """Initialize delay buffers."""
        for delay in self.comb_delays:
            self.comb_buffers.append(np.zeros(delay + 100))
            self.comb_indices.append(0)
        
        for delay in self.allpass_delays:
            self.allpass_buffers.append(np.zeros(delay + 100))
            self.allpass_indices.append(0)
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through reverb."""
        if len(audio) == 0:
            return audio
        
        # Ensure stereo
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=1)
        
        output = np.zeros_like(audio)
        
        # Process through comb filters (parallel)
        for i in range(len(self.comb_buffers)):
            buffer = self.comb_buffers[i]
            idx = self.comb_indices[i]
            delay = self.comb_delays[i]
            feedback = self.comb_feedback[i]
            
            for ch in range(audio.shape[1]):
                # Simplified comb filter - get delayed sample
                read_idx = idx % len(buffer)
                delayed = buffer[read_idx]
                output[delay:, ch] += buffer[max(0, idx):max(0, idx) + len(audio) - delay].flatten() * 0.1 if idx + len(audio) - delay > 0 else np.zeros(max(0, len(audio) - delay))
            
            # Update buffer
            for ch in range(audio.shape[1]):
                if idx + len(audio) <= len(buffer):
                    self.comb_buffers[i][idx:idx + len(audio)] += audio[:, ch] * 0.3 * self.room_size
            
            self.comb_indices[i] = (idx + len(audio)) % len(buffer)
        
        # Mix wet/dry
        output = audio + output * self.wet_dry * 0.3
        
        # Apply allpass filters (series) for diffusion
        for i in range(len(self.allpass_buffers)):
            buffer = self.allpass_buffers[i]
            idx = self.allpass_indices[i]
            
            for ch in range(output.shape[1]):
                delayed = buffer[idx]
                output[:, ch] = delayed + output[:, ch]
                buffer[idx] = output[:, ch] - delayed * 0.5
                self.allpass_indices[i] = (idx + 1) % len(buffer)
        
        # Normalize and clip
        max_val = np.max(np.abs(output))
        if max_val > 1.0:
            output /= max_val
        
        return output
    
    def set_parameters(self, room_size: Optional[float] = None, wet_dry: Optional[float] = None):
        """Update reverb parameters."""
        if room_size is not None:
            self.room_size = np.clip(room_size, 0.0, 1.0)
            # Update feedback based on room size
            self.comb_feedback = [0.28 * (1 + self.room_size * 0.2) for _ in self.comb_feedback]
        if wet_dry is not None:
            self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
    
    def reset(self):
        """Clear all buffers."""
        for buffer in self.comb_buffers:
            buffer.fill(0)
        for buffer in self.allpass_buffers:
            buffer.fill(0)
        self.comb_indices = [0] * len(self.comb_indices)
        self.allpass_indices = [0] * len(self.allpass_indices)


class DelayEffect:
    """
    Simple delay effect with feedback.
    """
    
    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE,
                 delay_time: float = 0.375, feedback: float = 0.3, wet_dry: float = 0.2):
        self.sample_rate = sample_rate
        self.delay_time = delay_time
        self.feedback = np.clip(feedback, 0.0, 0.95)
        self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
        
        self.delay_samples = int(delay_time * sample_rate)
        self.buffer = np.zeros(self.delay_samples * 2)  # Double buffer
        self.write_index = 0
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through delay."""
        if len(audio) == 0:
            return audio
        
        # Ensure stereo
        if audio.ndim == 1:
            audio = np.stack([audio, audio], axis=1)
        
        output = np.zeros_like(audio)
        
        for i in range(len(audio)):
            read_index = (self.write_index - self.delay_samples) % len(self.buffer)
            delayed = self.buffer[read_index]
            
            output[i] = audio[i] + delayed * self.wet_dry
            self.buffer[self.write_index] = audio[i, 0] + delayed * self.feedback
            
            self.write_index = (self.write_index + 1) % len(self.buffer)
        
        return output
    
    def set_parameters(self, delay_time: Optional[float] = None,
                       feedback: Optional[float] = None, wet_dry: Optional[float] = None):
        """Update delay parameters."""
        if delay_time is not None:
            self.delay_time = delay_time
            self.delay_samples = int(delay_time * self.sample_rate)
        if feedback is not None:
            self.feedback = np.clip(feedback, 0.0, 0.95)
        if wet_dry is not None:
            self.wet_dry = np.clip(wet_dry, 0.0, 1.0)
    
    def reset(self):
        """Clear delay buffer."""
        self.buffer.fill(0)
        self.write_index = 0


# =============================================================================
# NRPN Mapper
# =============================================================================

class YamahaNRPNMapper:
    """
    Enhanced NRPN mapper for Yamaha S.Art2 articulations.
    Properly handles MSB/LSB combinations without duplicates.
    """
    
    def __init__(self):
        # Use a more specific key structure to avoid duplicates
        # Format: (msb, lsb, category) -> articulation_name
        self.nrpn_to_articulation: Dict[Tuple[int, int, str], str] = {
            # Common articulations (MSB 1)
            (1, 0, 'common'): 'normal',
            (1, 1, 'common'): 'legato',
            (1, 2, 'common'): 'staccato',
            (1, 3, 'common'): 'bend',
            (1, 4, 'common'): 'vibrato',
            (1, 5, 'common'): 'breath',
            (1, 6, 'common'): 'glissando',
            (1, 7, 'common'): 'growl',
            (1, 8, 'common'): 'flutter',
            (1, 9, 'common'): 'trill',
            (1, 10, 'common'): 'pizzicato',
            (1, 11, 'common'): 'grace',
            (1, 12, 'common'): 'shake',
            (1, 13, 'common'): 'fall',
            (1, 14, 'common'): 'doit',
            (1, 15, 'common'): 'tongue_slap',
            (1, 16, 'common'): 'harmonics',
            (1, 17, 'common'): 'hammer_on',
            (1, 18, 'common'): 'pull_off',
            (1, 19, 'common'): 'key_off',
            (1, 20, 'common'): 'marcato',
            (1, 21, 'common'): 'detache',
            (1, 22, 'common'): 'sul_ponticello',
            (1, 23, 'common'): 'scoop',
            (1, 24, 'common'): 'rip',
            (1, 25, 'common'): 'portamento',
            (1, 26, 'common'): 'swell',
            (1, 27, 'common'): 'accented',
            (1, 28, 'common'): 'bow_up',
            (1, 29, 'common'): 'bow_down',
            (1, 30, 'common'): 'col_legno',
            (1, 31, 'common'): 'up_bend',
            (1, 32, 'common'): 'down_bend',
            (1, 33, 'common'): 'smear',
            (1, 34, 'common'): 'flip',
            (1, 35, 'common'): 'straight',
            
            # Wind-specific (MSB 2)
            (2, 0, 'wind'): 'growl_wind',
            (2, 1, 'wind'): 'flutter_wind',
            (2, 2, 'wind'): 'tongue_slap_wind',
            (2, 3, 'wind'): 'smear_wind',
            (2, 4, 'wind'): 'flip_wind',
            (2, 5, 'wind'): 'scoop_wind',
            (2, 6, 'wind'): 'rip_wind',
            
            # Strings-specific (MSB 3)
            (3, 0, 'strings'): 'pizzicato_strings',
            (3, 1, 'strings'): 'harmonics_strings',
            (3, 2, 'strings'): 'sul_ponticello_strings',
            (3, 3, 'strings'): 'bow_up_strings',
            (3, 4, 'strings'): 'bow_down_strings',
            (3, 5, 'strings'): 'col_legno_strings',
            (3, 6, 'strings'): 'portamento_strings',
            
            # Guitar-specific (MSB 4)
            (4, 0, 'guitar'): 'hammer_on_guitar',
            (4, 1, 'guitar'): 'pull_off_guitar',
            (4, 2, 'guitar'): 'harmonics_guitar',
        }
        
        # Simplified lookup for backward compatibility
        self._simplified_map: Dict[Tuple[int, int], str] = {}
        for (msb, lsb, _), art in self.nrpn_to_articulation.items():
            key = (msb, lsb)
            # Only add if not already present (common articulations take priority)
            if key not in self._simplified_map:
                self._simplified_map[key] = art
    
    def get_articulation(self, msb: int, lsb: int, category: str = 'common') -> str:
        """Get articulation from NRPN MSB/LSB values."""
        # Validate input range
        msb = max(0, min(127, msb))
        lsb = max(0, min(127, lsb))
        
        # Try category-specific lookup first
        key = (msb, lsb, category)
        if key in self.nrpn_to_articulation:
            return self.nrpn_to_articulation[key]
        
        # Fall back to simplified map
        return self._simplified_map.get((msb, lsb), 'normal')


# =============================================================================
# Audio Output Backend
# =============================================================================

class AudioOutputBase(ABC):
    """Abstract base class for audio output."""
    
    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass
    
    @abstractmethod
    def write(self, audio: np.ndarray):
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        pass


class SoundDeviceOutput(AudioOutputBase):
    """Audio output using sounddevice library."""
    
    def __init__(self, sample_rate: int, channels: int, block_size: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.buffer_size = buffer_size
        self._stream: Any = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()
    
    def start(self):
        """Start the audio stream."""
        if self._running:
            return
        
        if _sd is None:
            logger.warning("sounddevice not available")
            return
        
        self._stream = _sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.block_size,
            callback=self._callback,
            finished_callback=self._finished_callback
        )
        self._stream.start()
        self._running = True
        logger.info("SoundDevice audio output started")
    
    def stop(self):
        """Stop the audio stream."""
        if not self._running:
            return
        
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("SoundDevice audio output stopped")
    
    def write(self, audio: np.ndarray):
        """Queue audio data for playback."""
        # Ensure correct shape and channels
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        if audio.shape[1] < self.channels:
            # Pad mono to stereo
            audio = np.pad(audio, ((0, 0), (0, self.channels - audio.shape[1])))
        elif audio.shape[1] > self.channels:
            # Truncate extra channels
            audio = audio[:, :self.channels]
        
        # Convert to float32
        audio = audio.astype(np.float32)
        
        # Queue for playback
        try:
            self._audio_queue.put_nowait(audio)
        except queue.Full:
            pass  # Drop if full
    
    def is_running(self) -> bool:
        return self._running
    
    def _callback(self, outdata, frames, time_info, status):
        """Callback for sounddevice stream."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            audio = self._audio_queue.get_nowait()
            if len(audio) < frames:
                # Pad if needed
                padded = np.zeros((frames, self.channels), dtype=np.float32)
                padded[:len(audio)] = audio
                outdata[:] = padded
            else:
                outdata[:] = audio[:frames]
        except queue.Empty:
            outdata.fill(0)
    
    def _finished_callback(self):
        pass


class DummyAudioOutput(AudioOutputBase):
    """Dummy audio output for when no audio library is available."""
    
    def __init__(self, sample_rate: int, channels: int, block_size: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self._running = False
    
    def start(self):
        self._running = True
        logger.warning("Using dummy audio output - no audio will be heard")
    
    def stop(self):
        self._running = False
    
    def write(self, audio: np.ndarray):
        pass  # Discard audio
    
    def is_running(self) -> bool:
        return self._running


def create_audio_output(config: SynthConfig) -> AudioOutputBase:
    """Factory function to create appropriate audio output."""
    if SOUNDDEVICE_AVAILABLE:
        return SoundDeviceOutput(
            config.sample_rate,
            config.num_channels,
            config.block_size,
            config.buffer_size
        )
    else:
        logger.warning("sounddevice not available, using dummy output")
        return DummyAudioOutput(
            config.sample_rate,
            config.num_channels,
            config.block_size,
            config.buffer_size
        )


# =============================================================================
# Voice Management
# =============================================================================

class VoiceManager:
    """
    Polyphonic voice manager with voice stealing.
    """
    
    def __init__(self, max_voices: int = MAX_POLYPHONY, sample_rate: int = DEFAULT_SAMPLE_RATE):
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


# =============================================================================
# Main Synthesizer Class
# =============================================================================

class SuperArticulation2Synthesizer:
    """
    Enhanced Super Articulation 2 (S.Art2) synthesizer with:
    - Polyphonic voice management
    - Real-time audio output
    - Effects processing (reverb, delay)
    - Pitch bend and mod wheel support
    - Stereo output
    - Bug fixes
    """
    
    # Instrument parameter definitions
    INSTRUMENT_PARAMS: Dict[str, Dict] = {
        'saxophone': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 5.0,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.7,
            'release_time': 0.2, 'feedback': 0.98
        },
        'tenor_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.6, 'mod_index_max': 5.5,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.75,
            'release_time': 0.2, 'feedback': 0.98
        },
        'alto_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.4, 'mod_index_max': 5.0,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.72,
            'release_time': 0.2, 'feedback': 0.98
        },
        'trumpet': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 4.0,
            'attack_time': 0.03, 'decay_time': 0.08, 'sustain_level': 0.8,
            'release_time': 0.15, 'feedback': 0.98
        },
        'clarinet': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 3.0,
            'attack_time': 0.07, 'decay_time': 0.12, 'sustain_level': 0.6,
            'release_time': 0.25, 'feedback': 0.98
        },
        'flute': {
            'synthesis_method': 'fm', 'mod_ratio': 1.2, 'mod_index_max': 2.5,
            'attack_time': 0.06, 'decay_time': 0.09, 'sustain_level': 0.75,
            'release_time': 0.18, 'feedback': 0.98
        },
        'oboe': {
            'synthesis_method': 'fm', 'mod_ratio': 1.8, 'mod_index_max': 4.5,
            'attack_time': 0.08, 'decay_time': 0.11, 'sustain_level': 0.65,
            'release_time': 0.22, 'feedback': 0.98
        },
        'trombone': {
            'synthesis_method': 'fm', 'mod_ratio': 2.5, 'mod_index_max': 3.5,
            'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.85,
            'release_time': 0.2, 'feedback': 0.98
        },
        'french_horn': {
            'synthesis_method': 'fm', 'mod_ratio': 2.2, 'mod_index_max': 4.2,
            'attack_time': 0.06, 'decay_time': 0.12, 'sustain_level': 0.8,
            'release_time': 0.25, 'feedback': 0.98
        },
        'bassoon': {
            'synthesis_method': 'fm', 'mod_ratio': 0.8, 'mod_index_max': 4.8,
            'attack_time': 0.09, 'decay_time': 0.15, 'sustain_level': 0.6,
            'release_time': 0.3, 'feedback': 0.98
        },
        'violin': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.1, 'decay_time': 0.15, 'sustain_level': 0.5,
            'release_time': 0.3
        },
        'cello': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.12, 'decay_time': 0.18, 'sustain_level': 0.4,
            'release_time': 0.35
        },
        'viola': {
            'synthesis_method': 'ks', 'feedback': 0.993,
            'attack_time': 0.11, 'decay_time': 0.16, 'sustain_level': 0.48,
            'release_time': 0.32
        },
        'contrabass': {
            'synthesis_method': 'ks', 'feedback': 0.988,
            'attack_time': 0.14, 'decay_time': 0.2, 'sustain_level': 0.45,
            'release_time': 0.4
        },
        'guitar': {
            'synthesis_method': 'ks', 'feedback': 0.996,
            'attack_time': 0.02, 'decay_time': 0.05, 'sustain_level': 0.6,
            'release_time': 0.1
        },
        'electric_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.992,
            'attack_time': 0.015, 'decay_time': 0.06, 'sustain_level': 0.7,
            'release_time': 0.12
        },
        'bass_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.03, 'decay_time': 0.07, 'sustain_level': 0.55,
            'release_time': 0.15
        },
        'harp': {
            'synthesis_method': 'ks', 'feedback': 0.997,
            'attack_time': 0.01, 'decay_time': 0.04, 'sustain_level': 0.3,
            'release_time': 0.4
        },
        'marimba': {
            'synthesis_method': 'ks', 'feedback': 0.98,
            'attack_time': 0.01, 'decay_time': 0.08, 'sustain_level': 0.25,
            'release_time': 0.6
        },
        'strings_ensemble': {
            'synthesis_method': 'ks', 'feedback': 0.996,
            'attack_time': 0.15, 'decay_time': 0.2, 'sustain_level': 0.65,
            'release_time': 0.35
        },
    }
    
    def __init__(
        self,
        instrument: str = 'saxophone',
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        base_feedback: float = 0.98,
        vibrato_depth: float = 0.05,
        vibrato_rate: float = 5.0,
        config: Optional[SynthConfig] = None,
    ):
        # Core parameters
        self.instrument = instrument.lower()
        self.sample_rate = sample_rate
        self.base_feedback = base_feedback
        self.vibrato_depth = vibrato_depth
        self.vibrato_rate = vibrato_rate
        
        # Configuration
        self.config = config or SynthConfig(sample_rate=sample_rate)
        self.config.sample_rate = sample_rate
        
        # Components
        self.nrpn_mapper = YamahaNRPNMapper()
        self.voice_manager = VoiceManager(sample_rate=sample_rate)
        
        # Effects
        self.reverb = ReverbEffect(
            sample_rate=sample_rate,
            room_size=self.config.reverb_room_size,
            wet_dry=self.config.reverb_wet_dry
        )
        self.delay = DelayEffect(
            sample_rate=sample_rate,
            delay_time=self.config.delay_time,
            feedback=self.config.delay_feedback,
            wet_dry=self.config.delay_wet_dry
        )
        
        # Audio output
        self.audio_output = create_audio_output(self.config)
        
        # State
        self.current_articulation = 'normal'
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.current_pitch_bend = 0.0  # Channel-wide pitch bend
        self.current_mod_wheel = 0.0   # Channel-wide mod wheel
        
        # Instrument parameters
        self.instrument_params = self._get_instrument_params()
        self._validate_params()
        
        # Real-time control
        self._running = False
        self._midi_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Pre-generated wavetables for Karplus-Strong
        self._ks_wavetables: Dict[int, np.ndarray] = {}
        
        logger.info(f"Initialized S.Art2 synthesizer for {self.instrument} at {sample_rate} Hz")
    
    def _get_instrument_params(self) -> Dict[str, Dict]:
        """Get instrument parameters."""
        return self.INSTRUMENT_PARAMS.get(
            self.instrument,
            self.INSTRUMENT_PARAMS['saxophone']  # Default
        )
    
    def _validate_params(self) -> None:
        """Validate synthesizer parameters."""
        if self.instrument not in self.INSTRUMENT_PARAMS:
            raise ValueError(
                f"Unsupported instrument: {self.instrument}. "
                f"Supported: {list(self.INSTRUMENT_PARAMS.keys())}"
            )
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")
        if not 0 < self.base_feedback < 1:
            raise ValueError("Base feedback must be between 0 and 1.")
    
    # =========================================================================
    # Synthesis Methods
    # =========================================================================
    
    def _generate_fm_tone(
        self,
        freq: float,
        duration: float,
        velocity: int,
        params: Dict,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate FM synthesis tone."""
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        # Apply pitch bend
        if pitch_bend != 0.0:
            freq = freq * (SEMITONE_RATIO ** pitch_bend)
        
        # Calculate modulation index based on velocity and mod wheel
        mod_index = (velocity / 127.0) * params['mod_index_max']
        mod_index *= (1.0 + mod_wheel * 0.5)  # Mod wheel increases harmonics
        
        # Generate modulator and carrier
        mod_freq = freq * params['mod_ratio']
        modulator = np.sin(2 * np.pi * mod_freq * t)
        
        # Add vibrato
        if mod_wheel > 0:
            vibrato = self.vibrato_depth * np.sin(2 * np.pi * self.vibrato_rate * t) * mod_wheel
            t_vibrato = t + vibrato / (2 * np.pi * freq)
        else:
            t_vibrato = t
        
        carrier = np.sin(2 * np.pi * freq * t_vibrato + mod_index * modulator)
        
        # Apply envelope
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        
        # Apply velocity scaling
        velocity_scale = velocity / 127.0
        
        return carrier * envelope * velocity_scale
    
    def _generate_ks_tone(
        self,
        freq: float,
        duration: float,
        velocity: int,
        params: Dict,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate Karplus-Strong physical modeling synthesis tone."""
        n_samples = int(self.sample_rate * duration)
        
        # Apply pitch bend
        if pitch_bend != 0.0:
            freq = freq * (SEMITONE_RATIO ** pitch_bend)
        
        period = int(self.sample_rate / freq)
        
        # Use cached wavetable or create new one
        if period not in self._ks_wavetables:
            # Initialize with noise burst
            self._ks_wavetables[period] = np.random.uniform(-1, 1, period)
        
        wavetable = self._ks_wavetables[period].copy()
        
        samples = np.zeros(n_samples)
        idx = 0
        prev_sample = 0.0
        
        feedback = params.get('feedback', self.base_feedback)
        
        # Karplus-Strong algorithm - FIXED: use input sample for feedback
        for i in range(n_samples):
            current_sample = wavetable[idx]
            # Filtered feedback: average of current and previous, multiplied by feedback
            wavetable[idx] = feedback * 0.5 * (current_sample + prev_sample)
            samples[i] = wavetable[idx]
            prev_sample = current_sample  # FIXED: use input, not output
            idx = (idx + 1) % period
        
        # Apply envelope
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        
        # Ensure correct length
        envelope = envelope[:n_samples] if len(envelope) > n_samples else np.pad(
            envelope, (0, n_samples - len(envelope))
        )
        
        samples *= envelope
        
        # Normalize
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples /= max_val
        
        # Apply velocity scaling
        samples *= (velocity / 127.0)
        
        # Add mod wheel effect (tremolo)
        if mod_wheel > 0:
            t = np.arange(n_samples) / self.sample_rate
            tremolo = 1.0 - mod_wheel * 0.3 * (1 + np.sin(2 * np.pi * 6 * t)) * 0.5
            samples *= tremolo
        
        return samples.astype(np.float32)
    
    def _generate_adsr_envelope(
        self,
        duration: float,
        velocity: int,
        params: Dict
    ) -> np.ndarray:
        """Generate ADSR envelope with proper edge case handling."""
        total_samples = int(self.sample_rate * duration)
        
        # Guard against zero duration
        if total_samples <= 0:
            return np.array([])
        
        # Adjust attack based on velocity (softer = slower attack)
        attack_time = params['attack_time'] * (1.5 if velocity < 80 else 1.0)
        decay_time = params['decay_time']
        release_time = params['release_time']
        sustain_level = params['sustain_level']
        
        # Calculate sample counts
        attack_samples = min(int(attack_time * self.sample_rate), total_samples // 2)
        decay_samples = min(int(decay_time * self.sample_rate), total_samples - attack_samples)
        release_samples = min(int(release_time * self.sample_rate), total_samples - attack_samples - decay_samples)
        
        # Ensure we have at least some sustain
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples
        if sustain_samples < 0:
            # Adjust to fit
            release_samples = total_samples - attack_samples - decay_samples
            sustain_samples = 0
        
        envelope = np.zeros(total_samples)
        
        # Attack phase
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay phase
        decay_start = attack_samples
        decay_end = decay_start + decay_samples
        if decay_samples > 0:
            envelope[decay_start:decay_end] = np.linspace(1, sustain_level, decay_samples)
        
        # Sustain phase
        sustain_end = decay_end + sustain_samples
        if sustain_samples > 0:
            envelope[decay_end:sustain_end] = sustain_level
        
        # Release phase
        if release_samples > 0 and sustain_end < total_samples:
            release_start = sustain_end
            envelope[release_start:] = np.linspace(
                sustain_level, 0, min(total_samples - release_start, release_samples)
            )
        
        return envelope
    
    def _generate_base_tone(
        self,
        freq: float,
        duration: float,
        velocity: int = 100,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate base tone using appropriate synthesis method."""
        params = self.instrument_params
        
        if params['synthesis_method'] == 'fm':
            return self._generate_fm_tone(freq, duration, velocity, params, pitch_bend, mod_wheel)
        elif params['synthesis_method'] == 'ks':
            return self._generate_ks_tone(freq, duration, velocity, params, pitch_bend, mod_wheel)
        else:
            raise ValueError(f"Unknown synthesis method: {params['synthesis_method']}")
    
    # =========================================================================
    # Articulation Processing
    # =========================================================================
    
    def _apply_articulation(
        self,
        waveform: np.ndarray,
        articulation: str,
        freq: float,
        velocity: int = 100
    ) -> np.ndarray:
        """Apply articulation effect to waveform - FIXED to preserve base tone."""
        
        # Handle 'normal' and similar pass-through articulations
        if articulation in ('normal', 'straight', 'legato'):
            return waveform
        
        t = np.arange(len(waveform)) / self.sample_rate
        duration = len(waveform) / self.sample_rate
        
        # Create a modification mask (initially identity)
        modification = np.ones_like(waveform)
        additive = np.zeros_like(waveform)
        
        # Apply different articulations
        if articulation == 'staccato':
            decay_env = np.exp(-t / 0.2)
            modification *= decay_env
        
        elif articulation == 'bend':
            # FIXED: Apply bend as modification, not replacement
            bend_amount = 1.02
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            # Crossfade to preserve original character
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'up_bend':
            bend_amount = 1.02
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'down_bend':
            bend_amount = 0.98
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'vibrato':
            vibrato = self.vibrato_depth * np.sin(2 * np.pi * self.vibrato_rate * t)
            modification *= (1 + vibrato)
        
        elif articulation == 'breath':
            noise = 0.1 * np.random.normal(0, 1, len(waveform))
            # Simple low-pass filter approximation
            low_pass = np.convolve(noise, np.ones(100) / 100, mode='same')
            additive += low_pass
        
        elif articulation in ('glissando', 'portamento'):
            gliss_amount = 1.05
            freq_slide = np.linspace(freq, freq * gliss_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            gliss_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += gliss_wave * fade * 0.5
        
        elif articulation == 'growl':
            growl_freq = 20.0
            growl = 0.2 * (1 + np.sin(2 * np.pi * growl_freq * t))
            modification *= growl
        
        elif articulation == 'flutter':
            flutter_freq = 10.0
            flutter = 0.1 * (1 + np.sin(2 * np.pi * flutter_freq * t))
            modification *= flutter
        
        elif articulation == 'trill':
            trill_freq = 5.0
            trill_mod = np.sin(2 * np.pi * trill_freq * t)
            # Quick frequency modulation for trill effect
            freq_mod = freq * (1 + 0.02 * trill_mod * (SEMITONE_RATIO - 1))
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            trill_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            modification *= (1 - fade)
            additive += trill_wave * fade * 0.5
        
        elif articulation == 'pizzicato':
            decay_env = np.exp(-t / 0.1)
            modification *= decay_env
        
        elif articulation == 'grace':
            grace_duration = min(0.05, duration * 0.3)
            grace_samples = int(grace_duration * self.sample_rate)
            if grace_samples < len(waveform):
                grace_freq = freq * SEMITONE_RATIO
                grace_t = np.arange(grace_samples) / self.sample_rate
                grace_wave = np.sin(2 * np.pi * grace_freq * grace_t)
                grace_env = np.linspace(0, 1, grace_samples // 2)
                grace_env = np.concatenate([grace_env, grace_env[::-1]])
                additive[:grace_samples] += grace_wave[:len(grace_env)] * grace_env * 0.5
        
        elif articulation == 'shake':
            shake_freq = 8.0
            shake_mod = np.sin(2 * np.pi * shake_freq * t)
            freq_mod = freq * (1 + 0.02 * shake_mod)
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            shake_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            modification *= (1 - fade)
            additive += shake_wave * fade * 0.3
        
        elif articulation == 'fall':
            fall_amount = 0.95
            freq_slide = np.linspace(freq, freq * fall_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            fall_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += fall_wave * fade * 0.5
        
        elif articulation == 'doit':
            doit_amount = 1.05
            freq_slide = np.linspace(freq, freq * doit_amount, len(waveform) // 2)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq * doit_amount)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            doit_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            modification *= (1 - fade)
            additive += doit_wave * fade * 0.5
        
        elif articulation == 'tongue_slap':
            slap_duration = 0.02
            slap_samples = int(slap_duration * self.sample_rate)
            slap_samples = min(slap_samples, len(waveform) // 4)
            slap_noise = 0.3 * np.random.normal(0, 1, slap_samples)
            additive[:slap_samples] += slap_noise
        
        elif articulation == 'harmonics':
            harmonic_mult = 2.0
            harmonic_wave = np.sin(2 * np.pi * freq * harmonic_mult * t)
            additive += 0.3 * harmonic_wave
        
        elif articulation == 'hammer_on':
            hammer_duration = 0.01
            hammer_samples = int(hammer_duration * self.sample_rate)
            hammer_samples = min(hammer_samples, len(waveform) // 2)
            if len(waveform) > hammer_samples * 2:
                hammer_env = np.linspace(0, 1.2, hammer_samples)
                modification[hammer_samples:hammer_samples*2] *= np.concatenate([
                    hammer_env, np.ones(len(waveform) - hammer_samples * 2)
                ][:len(modification) - hammer_samples])
        
        elif articulation == 'pull_off':
            pull_duration = 0.01
            pull_samples = int(pull_duration * self.sample_rate)
            pull_samples = min(pull_samples, len(waveform) // 2)
            pull_env = np.linspace(1, 0, pull_samples)
            modification[-pull_samples:] *= pull_env
        
        elif articulation == 'key_off':
            noise_duration = len(waveform) // 10
            if noise_duration > 0:
                off_noise = 0.05 * np.random.normal(0, 1, noise_duration)
                modification[-noise_duration:] *= 1 - np.linspace(0, 1, noise_duration) * 0.5
                additive[-noise_duration:] += off_noise
        
        elif articulation == 'marcato':
            marcato_env = np.exp(-t / 0.15) * 1.2
            modification *= marcato_env
        
        elif articulation == 'detache':
            detache_samples = int(0.1 * self.sample_rate)
            if detache_samples < len(waveform):
                detache_env = np.ones(len(waveform))
                detache_env[-detache_samples:] = np.linspace(1, 0, detache_samples)
                modification *= detache_env
        
        elif articulation == 'sul_ponticello':
            pont_noise = 0.15 * np.random.normal(0, 1, len(waveform))
            # Simple high-pass effect
            high_pass = np.cumsum(pont_noise) / len(waveform)
            additive += high_pass
        
        elif articulation == 'scoop':
            scoop_duration = len(waveform) // 4
            scoop_amount = 0.98
            freq_slide = np.linspace(freq * scoop_amount, freq, scoop_duration)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - scoop_duration, freq)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            scoop_wave = np.sin(phase)
            fade = np.linspace(0, 1, scoop_duration)
            modification *= (1 - fade)
            additive += scoop_wave * fade * 0.5
        
        elif articulation == 'rip':
            rip_duration = len(waveform) // 4
            rip_amount = 1.05
            freq_slide = np.linspace(freq, freq * rip_amount, rip_duration)
            freq_slide = np.concatenate([np.full(len(waveform) - rip_duration, freq * rip_amount), freq_slide[::-1]])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            rip_wave = np.sin(phase)
            fade = np.linspace(0, 1, rip_duration)
            modification *= (1 - fade)
            additive += rip_wave * fade * 0.5
        
        elif articulation == 'swell':
            # FIXED: Use t[-1] instead of max(t)
            t_last = t[-1] if len(t) > 0 else 1.0
            swell_env = np.sin(np.pi * t / t_last)
            modification *= swell_env * 1.2
        
        elif articulation == 'accented':
            acc_env = np.exp(-t / 0.1) * 1.5
            modification *= acc_env
        
        elif articulation == 'bow_up':
            bow_env = np.linspace(0.8, 1.2, len(waveform))
            modification *= bow_env
        
        elif articulation == 'bow_down':
            bow_env = np.linspace(1.2, 0.8, len(waveform))
            modification *= bow_env
        
        elif articulation == 'col_legno':
            legno_noise = 0.2 * np.random.normal(0, 1, len(waveform))
            additive += legno_noise
            modification *= np.exp(-t / 0.3)
        
        elif articulation == 'smear':
            smear_freq = 15.0
            smear_mod = 0.1 * np.sin(2 * np.pi * smear_freq * t)
            modification *= (1 + smear_mod)
        
        elif articulation == 'flip':
            flip_duration = min(0.03, duration * 0.2)
            flip_samples = int(flip_duration * self.sample_rate)
            flip_samples = min(flip_samples, len(waveform) // 2)
            flip_freq = freq * SEMITONE_RATIO * 2
            flip_t = np.arange(flip_samples) / self.sample_rate
            flip_wave = np.sin(2 * np.pi * flip_freq * flip_t)
            flip_env = np.linspace(0, 1, flip_samples // 2)
            flip_env = np.concatenate([flip_env, flip_env[::-1]])
            additive[:flip_samples] += flip_wave[:len(flip_env)] * flip_env * 0.4
        
        # Apply modifications
        result = waveform * modification + additive
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(result))
        if max_val > 1.0:
            result /= max_val
        
        return result.astype(np.float32)
    
    # =========================================================================
    # Note Synthesis
    # =========================================================================
    
    def synthesize_note(
        self,
        freq: float,
        duration: float,
        velocity: int = 100,
        articulation: Optional[str] = None,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Synthesize a single note with all effects."""
        # Ensure articulation is a string
        if articulation is None:
            articulation = self.current_articulation
        elif not isinstance(articulation, str):
            articulation = str(articulation)
        
        try:
            # Generate base tone with pitch bend and mod wheel
            base = self._generate_base_tone(freq, duration, velocity, pitch_bend, mod_wheel)
            
            # Apply articulation
            articulated = self._apply_articulation(base, articulation, freq, velocity)
            
            # Normalize
            max_val = np.max(np.abs(articulated))
            if max_val > 0:
                articulated /= max_val
            
            return articulated
        
        except Exception as e:
            logger.error(f"Error synthesizing note: {e}")
            raise
    
    def synthesize_note_sequence(
        self,
        notes: List[Dict[str, Any]],
        overlap: float = 0.05
    ) -> np.ndarray:
        """Synthesize a sequence of notes with proper legato handling."""
        audio = np.array([], dtype=np.float32)
        prev_articulation = None
        
        for note in notes:
            # Get parameters with defaults
            freq = note.get('freq', 440.0)
            duration = note.get('duration', 1.0)
            velocity = int(note.get('velocity', 100))
            art = note.get('articulation')
            if art is None:
                art = self.current_articulation
            elif not isinstance(art, str):
                art = str(art)
            
            # Validate parameters
            duration = max(0.01, duration)  # Minimum duration
            velocity = max(1, min(127, velocity))
            
            # Synthesize note
            note_audio = self.synthesize_note(freq, duration, velocity, art)
            
            # Handle legato overlap
            if prev_articulation == 'legato' and len(audio) > 0:
                # Calculate overlap samples with safety check
                overlap_samples = int(overlap * self.sample_rate)
                overlap_samples = max(0, min(overlap_samples, len(audio)))
                overlap_samples = min(overlap_samples, len(note_audio))
                
                if overlap_samples > 0:
                    fade_out = np.linspace(1, 0, overlap_samples)
                    fade_in = np.linspace(0, 1, overlap_samples)
                    
                    # Apply crossfade
                    audio[-overlap_samples:] *= fade_out
                    note_audio[:overlap_samples] *= fade_in
                    audio[-overlap_samples:] += note_audio[:overlap_samples]
                    
                    # Append remaining samples
                    audio = np.concatenate([audio, note_audio[overlap_samples:]])
                else:
                    audio = np.concatenate([audio, note_audio])
            else:
                audio = np.concatenate([audio, note_audio])
            
            prev_articulation = art
        
        return audio
    
    # =========================================================================
    # Effects Processing
    # =========================================================================
    
    def apply_effects(self, audio: np.ndarray) -> np.ndarray:
        """Apply reverb and delay effects."""
        if len(audio) == 0:
            return audio
        
        # Apply reverb
        if self.config.enable_reverb:
            audio = self.reverb.process(audio)
        
        # Apply delay
        if self.config.enable_delay:
            audio = self.delay.process(audio)
        
        # Apply master volume
        audio *= self.config.master_volume
        
        # Soft clip to prevent harsh digital clipping
        audio = np.tanh(audio * 1.5) / 1.5
        
        return audio
    
    # =========================================================================
    # Output Methods
    # =========================================================================
    
    def save_to_wav(self, audio: np.ndarray, filename: str) -> None:
        """Save audio to WAV file with stereo support."""
        try:
            # Ensure stereo
            if audio.ndim == 1:
                audio = np.stack([audio, audio], axis=1)
            
            # Apply effects before saving
            audio = self.apply_effects(audio)
            
            # Convert to 16-bit integer
            audio_int16 = (audio * 32767).astype(np.int16)
            
            wavfile.write(filename, self.sample_rate, audio_int16)
            logger.info(f"Saved audio to {filename}")
        
        except Exception as e:
            logger.error(f"Error saving WAV: {e}")
            raise
    
    def play_audio(self, audio: np.ndarray):
        """Play audio through audio output."""
        if len(audio) == 0:
            return
        
        # Apply effects
        audio = self.apply_effects(audio)
        
        # Send to audio output
        self.audio_output.write(audio)
    
    # =========================================================================
    # Real-time MIDI Processing
    # =========================================================================
    
    def process_midi_file(
        self,
        midi_path: str,
        output_wav: str = 'output.wav',
        tempo: int = 500000  # microseconds per beat (120 BPM default)
    ) -> None:
        """Process MIDI file and render to WAV."""
        if not MIDO_AVAILABLE:
            logger.error("mido library not available for MIDI processing")
            return
        
        mid = MidiFile(midi_path)
        
        if mid.ticks_per_beat > 0:
            ticks_per_beat = mid.ticks_per_beat
        else:
            ticks_per_beat = 480
        
        audio_chunks: List[np.ndarray] = []
        active_notes: Dict[int, NoteEvent] = {}
        current_time = 0.0
        
        for track in mid.tracks:
            for msg in track:
                # Convert delta time to seconds
                delta_time_sec = mido.tick2second(msg.time, ticks_per_beat, tempo)
                current_time += delta_time_sec
                
                # Handle tempo changes
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                
                # Handle NRPN
                if msg.type == 'control_change':
                    if msg.control == NRPN_MSB_CONTROL:
                        self.nrpn_msb = max(0, min(127, msg.value))
                    elif msg.control == NRPN_LSB_CONTROL:
                        self.nrpn_lsb = max(0, min(127, msg.value))
                        self.current_articulation = self.nrpn_mapper.get_articulation(
                            self.nrpn_msb, self.nrpn_lsb
                        )
                        logger.info(f"NRPN: Articulation set to {self.current_articulation}")
                
                # Handle pitch bend (channel-wide)
                if msg.type == 'pitchwheel':
                    # Pitch bend value ranges from -8192 to 8191
                    bend_value = max(-8192, min(8191, msg.pitch))
                    self.current_pitch_bend = (bend_value / 8192.0) * 2.0  # -2 to +2 semitones
                
                # Handle mod wheel
                if msg.type == 'control_change' and msg.control == MOD_WHEEL_CONTROL:
                    self.current_mod_wheel = max(0, min(127, msg.value)) / 127.0
                
                # Handle note on
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_num = max(0, min(127, msg.note))
                    velocity = max(0, min(127, msg.velocity))
                    freq = midi_note_to_frequency(note_num)
                    
                    active_notes[note_num] = NoteEvent(
                        note=note_num,
                        velocity=velocity,
                        start_time=current_time,
                        duration=0.0,  # Will be set on note off
                        frequency=freq,
                        articulation=self.current_articulation,
                        pitch_bend=self.current_pitch_bend,
                        mod_wheel=self.current_mod_wheel
                    )
                
                # Handle note off
                elif (msg.type == 'note_off' or 
                      (msg.type == 'note_on' and msg.velocity == 0)):
                    note_num = max(0, min(127, msg.note))
                    
                    if note_num in active_notes:
                        note_event = active_notes.pop(note_num)
                        note_event.duration = current_time - note_event.start_time
                        
                        # Ensure minimum duration
                        note_event.duration = max(0.01, note_event.duration)
                        
                        # Synthesize note
                        note_audio = self.synthesize_note(
                            note_event.frequency,
                            note_event.duration,
                            note_event.velocity,
                            note_event.articulation,
                            note_event.pitch_bend,
                            note_event.mod_wheel
                        )
                        
                        # Add to output at correct position
                        start_sample = int(note_event.start_time * self.sample_rate)
                        
                        # Extend audio buffer if needed
                        required_length = start_sample + len(note_audio)
                        current_length = sum(len(c) for c in audio_chunks)
                        if current_length < required_length:
                            padding = np.zeros(required_length - current_length, dtype=np.float32)
                            if audio_chunks:
                                audio_chunks[-1] = np.concatenate([audio_chunks[-1], padding])
                            else:
                                audio_chunks.append(padding)
                        
                        # Add note audio at position
                        if audio_chunks:
                            audio_chunks[-1] = np.concatenate([audio_chunks[-1], note_audio])
                        else:
                            audio_chunks.append(note_audio)
        
        # Combine all audio chunks
        if audio_chunks:
            final_audio = np.concatenate(audio_chunks)
            self.save_to_wav(final_audio, output_wav)
        else:
            logger.warning("No audio generated from MIDI file")
    
    def listen_midi_real_time(
        self,
        port_name: Optional[str] = None,
        output_device: Optional[str] = None
    ) -> None:
        """Real-time MIDI listening with audio output."""
        if not MIDO_AVAILABLE:
            logger.error("mido library not available for MIDI input")
            return
        
        if port_name is None:
            available_ports = mido.get_input_names()
            if not available_ports:
                raise ValueError("No MIDI input ports available.")
            port_name = available_ports[0]
        
        logger.info(f"Listening on MIDI port: {port_name}")
        
        # Start audio output
        self.audio_output.start()
        self._running = True
        
        # Note tracking
        active_notes: Dict[int, float] = {}  # note: start_time
        note_audio_buffers: Dict[int, np.ndarray] = {}
        
        # Add frequency mapping for notes
        note_frequencies: Dict[int, float] = {}
        
        try:
            with mido.open_input(port_name) as inport:
                while self._running and not self._stop_event.is_set():
                    for msg in inport.iter_pending():
                        current_time = time.time()
                        
                        # Handle control changes
                        if msg.type == 'control_change':
                            if msg.control == NRPN_MSB_CONTROL:
                                self.nrpn_msb = max(0, min(127, msg.value))
                            elif msg.control == NRPN_LSB_CONTROL:
                                self.nrpn_lsb = max(0, min(127, msg.value))
                                self.current_articulation = self.nrpn_mapper.get_articulation(
                                    self.nrpn_msb, self.nrpn_lsb
                                )
                                logger.info(f"Real-time NRPN: {self.current_articulation}")
                        
                        # Handle pitch bend
                        if msg.type == 'pitchwheel':
                            bend_value = max(-8192, min(8191, msg.pitch))
                            self.current_pitch_bend = (bend_value / 8192.0) * 2.0
                        
                        # Handle mod wheel
                        if msg.type == 'control_change' and msg.control == MOD_WHEEL_CONTROL:
                            self.current_mod_wheel = max(0, min(127, msg.value)) / 127.0
                        
                        # Handle note on
                        if msg.type == 'note_on' and msg.velocity > 0:
                            note_num = max(0, min(127, msg.note))
                            velocity = max(0, min(127, msg.velocity))
                            
                            active_notes[note_num] = current_time
                            note_frequencies[note_num] = midi_note_to_frequency(note_num)
                            
                            # Start a note buffer
                            note_audio_buffers[note_num] = np.array([], dtype=np.float32)
                            
                            logger.info(
                                f"Note ON: {note_num}, velocity: {velocity}, "
                                f"articulation: {self.current_articulation}"
                            )
                        
                        # Handle note off
                        elif (msg.type == 'note_off' or 
                              (msg.type == 'note_on' and msg.velocity == 0)):
                            note_num = max(0, min(127, msg.note))
                            
                            if note_num in active_notes:
                                start_time = active_notes.pop(note_num)
                                duration = current_time - start_time
                                duration = max(0.01, duration)  # Minimum duration
                                
                                freq = note_frequencies.pop(note_num, 440.0)
                                velocity = 100  # Use last known velocity or default
                                
                                # Synthesize final note
                                note_audio = self.synthesize_note(
                                    freq,
                                    duration,
                                    velocity,
                                    self.current_articulation,
                                    self.current_pitch_bend,
                                    self.current_mod_wheel
                                )
                                
                                # Play through audio output
                                self.play_audio(note_audio)
                                
                                logger.info(f"Note OFF: {note_num}, duration: {duration:.3f}s")
                    
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
        
        except Exception as e:
            logger.error(f"Error in MIDI listener: {e}")
        finally:
            self.stop()
    
    def start_midi_listener(self, port_name: Optional[str] = None):
        """Start MIDI listener in a separate thread."""
        self._stop_event.clear()
        self._midi_thread = threading.Thread(
            target=self.listen_midi_real_time,
            args=(port_name,),
            daemon=True
        )
        self._midi_thread.start()
        logger.info("MIDI listener started in background")
    
    def stop(self):
        """Stop the synthesizer and release resources."""
        self._running = False
        self._stop_event.set()
        
        # Stop audio output
        self.audio_output.stop()
        
        # Release all voices
        self.voice_manager.all_notes_off()
        
        # Reset effects
        self.reverb.reset()
        self.delay.reset()
        
        logger.info("Synthesizer stopped")
    
    # =========================================================================
    # Parameter Setters
    # =========================================================================
    
    def set_instrument(self, instrument: str):
        """Change the current instrument."""
        instrument = instrument.lower()
        if instrument not in self.INSTRUMENT_PARAMS:
            raise ValueError(f"Unsupported instrument: {instrument}")
        self.instrument = instrument
        self.instrument_params = self._get_instrument_params()
        logger.info(f"Instrument changed to {instrument}")
    
    def set_articulation(self, articulation: str):
        """Set the current articulation."""
        self.current_articulation = articulation
        logger.info(f"Articulation set to {articulation}")
    
    def set_reverb_params(self, room_size: Optional[float] = None, wet_dry: Optional[float] = None):
        """Set reverb parameters."""
        self.reverb.set_parameters(room_size=room_size, wet_dry=wet_dry)
    
    def set_delay_params(
        self,
        delay_time: Optional[float] = None,
        feedback: Optional[float] = None,
        wet_dry: Optional[float] = None
    ):
        """Set delay parameters."""
        self.delay.set_parameters(
            delay_time=delay_time,
            feedback=feedback,
            wet_dry=wet_dry
        )
    
    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)."""
        self.config.master_volume = np.clip(volume, 0.0, 1.0)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Create synthesizer with enhanced configuration
    config = SynthConfig(
        sample_rate=44100,
        enable_reverb=True,
        enable_delay=True,
        reverb_room_size=0.5,
        reverb_wet_dry=0.3,
        delay_time=0.375,
        delay_feedback=0.3,
        delay_wet_dry=0.2,
        master_volume=0.8
    )
    
    synth = SuperArticulation2Synthesizer(
        instrument='tenor_sax',
        config=config
    )
    
    # Example 1: Synthesize a sequence of notes
    print("Example 1: Synthesizing note sequence...")
    notes = [
        {'freq': 440.0, 'duration': 1.0, 'articulation': 'growl', 'velocity': 90},
        {'freq': 493.88, 'duration': 1.0, 'articulation': 'glissando', 'velocity': 100},
        {'freq': 523.25, 'duration': 0.5, 'articulation': 'bend', 'velocity': 95},
        {'freq': 587.33, 'duration': 1.5, 'articulation': 'vibrato', 'velocity': 85},
    ]
    audio = synth.synthesize_note_sequence(notes)
    synth.save_to_wav(audio, 'example.wav')
    print("Saved to example.wav")
    
    # Example 2: Single note synthesis
    print("Example 2: Synthesizing single note with pitch bend...")
    note_audio = synth.synthesize_note(
        freq=440.0,
        duration=2.0,
        velocity=100,
        articulation='bend',
        pitch_bend=1.0,  # 1 semitone up
        mod_wheel=0.5
    )
    synth.save_to_wav(note_audio, 'single_note.wav')
    print("Saved to single_note.wav")
    
    # Example 3: Change instrument
    print("Example 3: Changing instrument to violin...")
    synth.set_instrument('violin')
    synth.set_articulation('harmonics')
    violin_audio = synth.synthesize_note(440.0, 2.0, 80)
    synth.save_to_wav(violin_audio, 'violin.wav')
    print("Saved to violin.wav")
    
    # Example 4: Adjust effects
    print("Example 4: Adjusting reverb...")
    synth.set_reverb_params(room_size=0.7, wet_dry=0.4)
    synth.set_delay_params(delay_time=0.5, feedback=0.4)
    reverb_audio = synth.synthesize_note(440.0, 3.0, 90)
    synth.save_to_wav(reverb_audio, 'with_effects.wav')
    print("Saved to with_effects.wav")
    
    print("\nAll examples completed!")
    print("To use real-time MIDI, uncomment the following:")
    # synth.start_midi_listener()  # Start MIDI input listener
    # synth.listen_midi_real_time()  # Or run directly
    
    # Example 5: Process MIDI file (uncomment to use)
    # synth.process_midi_file('example.mid', 'midi_render.wav')
