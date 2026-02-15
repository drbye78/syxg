"""
Audio output backend for S.Art2 synthesizer.
"""

import logging
import queue
import threading
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import numpy as np

# Optional audio library imports
try:
    import sounddevice as _sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    _sd = None
    SOUNDDEVICE_AVAILABLE = False


logger = logging.getLogger(__name__)


class AudioOutputBase(ABC):
    """Abstract base class for audio output."""
    
    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass
    
    @abstractmethod
    def write(self, audio: np.ndarray) -> None:
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        pass
    
    @abstractmethod
    def get_audio_buffer(self) -> np.ndarray:
        """Get accumulated audio for offline rendering."""
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
        # Buffer for offline rendering
        self._audio_buffer: List[np.ndarray] = []
    
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
    
    def write(self, audio: np.ndarray) -> None:
        """Queue audio data for playback."""
        # Ensure correct shape and channels
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        if audio.shape[1] < self.channels:
            audio = np.pad(audio, ((0, 0), (0, self.channels - audio.shape[1])))
        elif audio.shape[1] > self.channels:
            audio = audio[:, :self.channels]
        
        audio = audio.astype(np.float32)
        
        # Store in buffer for offline rendering
        with self._lock:
            self._audio_buffer.append(audio.copy())
        
        try:
            self._audio_queue.put_nowait(audio)
        except queue.Full:
            logger.warning("Audio queue full, dropping samples")
    
    def is_running(self) -> bool:
        return self._running
    
    def get_audio_buffer(self) -> np.ndarray:
        """Get accumulated audio for offline rendering."""
        with self._lock:
            if not self._audio_buffer:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._audio_buffer, axis=0)
    
    def clear_buffer(self) -> None:
        """Clear the audio buffer."""
        with self._lock:
            self._audio_buffer = []
    
    def _callback(self, outdata, frames, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            audio = self._audio_queue.get_nowait()
            if len(audio) < frames:
                padded = np.zeros((frames, self.channels), dtype=np.float32)
                padded[:len(audio)] = audio
                outdata[:] = padded
            else:
                outdata[:] = audio[:frames]
        except queue.Empty:
            outdata.fill(0)
    
    def _finished_callback(self):
        logger.debug("Audio stream finished")


class DummyAudioOutput(AudioOutputBase):
    """Dummy audio output for when no audio library is available.
    
    Stores audio in buffer for offline rendering.
    """
    
    def __init__(self, sample_rate: int, channels: int, block_size: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self._running = False
        # Store audio for offline rendering
        self._audio_buffer: List[np.ndarray] = []
    
    def start(self):
        self._running = True
        logger.warning("Using dummy audio output - no audio will be heard (use get_audio_buffer() for offline rendering)")
    
    def stop(self):
        self._running = False
    
    def write(self, audio: np.ndarray) -> None:
        """Store audio in buffer for later retrieval."""
        if audio is None or len(audio) == 0:
            return
        
        # Ensure correct shape and channels
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        if audio.shape[1] < self.channels:
            audio = np.pad(audio, ((0, 0), (0, self.channels - audio.shape[1])))
        elif audio.shape[1] > self.channels:
            audio = audio[:, :self.channels]
        
        # Store as float32
        self._audio_buffer.append(audio.astype(np.float32))
    
    def is_running(self) -> bool:
        return self._running
    
    def get_audio_buffer(self) -> np.ndarray:
        """Get accumulated audio for offline rendering."""
        if not self._audio_buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._audio_buffer, axis=0)
    
    def clear_buffer(self) -> None:
        """Clear the audio buffer."""
        self._audio_buffer = []


def create_audio_output(config) -> AudioOutputBase:
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
