"""
PyAV-Powered Sample Manager for SFZ Synthesis

Leverages the project's existing 'av' package for high-performance,
format-agnostic sample loading and management.
"""

import os
import av
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import threading


class SampleCache:
    """LRU cache for audio samples with memory management"""

    def __init__(self, max_memory_mb: float = 512.0):
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.current_memory_bytes = 0
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache, updating access time"""
        with self.lock:
            if key in self.cache:
                self.access_times[key] = self._current_time()
                return self.cache[key]
        return None

    def put(self, key: str, item: Any) -> None:
        """Put item in cache, evicting if necessary"""
        with self.lock:
            # Calculate item size (approximate)
            item_size = self._estimate_size(item)

            # Evict items if needed
            while self.current_memory_bytes + item_size > self.max_memory_bytes and self.cache:
                self._evict_lru()

            # Add item
            self.cache[key] = item
            self.access_times[key] = self._current_time()
            self.current_memory_bytes += item_size

    def clear(self) -> None:
        """Clear all cached items"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.current_memory_bytes = 0

    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.access_times:
            return

        # Find LRU item
        lru_key = min(self.access_times, key=self.access_times.get)

        # Remove it
        item = self.cache[lru_key]
        item_size = self._estimate_size(item)

        del self.cache[lru_key]
        del self.access_times[lru_key]
        self.current_memory_bytes -= item_size

    def _estimate_size(self, item: Any) -> int:
        """Estimate memory usage of an item"""
        if hasattr(item, 'data') and hasattr(item.data, 'nbytes'):
            return item.data.nbytes
        elif hasattr(item, '__sizeof__'):
            return item.__sizeof__()
        else:
            return 1024  # Default estimate

    def _current_time(self) -> float:
        """Get current time for LRU tracking"""
        import time
        return time.time()


class StreamingSample:
    """Streaming sample for large audio files"""

    def __init__(self, container: av.container.Container, stream: av.audio.AudioStream, path: str):
        self.container = container
        self.stream = stream
        self.path = path
        self.decoder = container.decode(stream)
        self.position = 0
        self.current_frame: Optional[np.ndarray] = None
        self.frame_offset = 0

    def seek_to_sample(self, sample_position: int) -> None:
        """Seek to specific sample position"""
        # Convert sample position to time
        time_position = sample_position / self.stream.sample_rate

        # Seek in container
        self.container.seek(int(time_position * av.time_base))
        self.decoder = self.container.decode(self.stream)
        self.position = sample_position
        self.current_frame = None
        self.frame_offset = 0

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Read specified number of samples"""
        samples_read = 0
        output = np.zeros((num_samples, self.stream.channels), dtype=np.float32)

        while samples_read < num_samples:
            # Get next frame if needed
            if self.current_frame is None or self.frame_offset >= len(self.current_frame):
                try:
                    frame = next(self.decoder)
                    # Convert to numpy array and ensure float32
                    self.current_frame = frame.to_ndarray().astype(np.float32).T
                    self.frame_offset = 0
                except StopIteration:
                    # End of stream
                    break

            # Copy available samples
            available_samples = len(self.current_frame) - self.frame_offset
            samples_to_copy = min(num_samples - samples_read, available_samples)

            if samples_to_copy > 0:
                output[samples_read:samples_read + samples_to_copy] = \
                    self.current_frame[self.frame_offset:self.frame_offset + samples_to_copy]
                samples_read += samples_to_copy
                self.frame_offset += samples_to_copy
                self.position += samples_to_copy

        return output[:samples_read] if samples_read < num_samples else output

    def get_metadata(self) -> Dict[str, Any]:
        """Get stream metadata"""
        return {
            'sample_rate': self.stream.sample_rate,
            'channels': self.stream.channels,
            'duration_samples': self.stream.duration or 0,
            'bit_depth': self._get_bit_depth(),
            'codec': self.stream.codec.name
        }

    def _get_bit_depth(self) -> int:
        """Determine bit depth from stream"""
        format_map = {
            'u8': 8, 's16': 16, 's32': 32, 'flt': 32, 'dbl': 64,
            'u8p': 8, 's16p': 16, 's32p': 32, 'fltp': 32, 'dblp': 64,
        }
        return format_map.get(self.stream.format.name, 16)

    def close(self) -> None:
        """Close the stream"""
        self.container.close()


class SFZSample:
    """SFZ sample with PyAV-powered loading"""

    def __init__(self, data: np.ndarray, metadata: Dict[str, Any], path: str):
        self.data = data  # Shape: (samples, channels)
        self.metadata = metadata
        self.path = path
        self.sample_rate = metadata['sample_rate']
        self.channels = metadata['channels']
        self.loop_start = metadata.get('loop_start', 0)
        self.loop_end = metadata.get('loop_end', len(data))
        self.cues: List[Dict[str, Any]] = metadata.get('cues', [])

    def is_stereo(self) -> bool:
        """Check if sample is stereo"""
        return self.channels == 2

    def get_channel_data(self, channel: int) -> np.ndarray:
        """Get data for specific channel"""
        if self.is_stereo():
            return self.data[:, channel]
        else:
            return self.data[:, 0]  # Mono

    def get_duration_seconds(self) -> float:
        """Get sample duration in seconds"""
        return len(self.data) / self.sample_rate

    def get_memory_usage_mb(self) -> float:
        """Get memory usage in MB"""
        return self.data.nbytes / (1024 * 1024)


class PyAVSampleManager:
    """
    High-performance sample manager using PyAV

    Leverages the project's existing 'av' package for comprehensive
    audio format support and professional-quality decoding.
    """

    SUPPORTED_FORMATS = {
        '.wav', '.aiff', '.aif', '.flac', '.ogg', '.mp3',
        '.aac', '.m4a', '.wma', '.ape', '.wv', '.tta'
    }

    def __init__(self, max_memory_mb: float = 512.0):
        """
        Initialize PyAV sample manager

        Args:
            max_memory_mb: Maximum memory for cached samples
        """
        self.cache = SampleCache(max_memory_mb)
        self.streaming_threshold_mb = 50.0  # Stream files larger than this

    def load_sample(self, path: str) -> SFZSample:
        """
        Load sample using PyAV with intelligent caching

        Args:
            path: Path to audio file

        Returns:
            SFZSample instance
        """
        # Check cache first
        cached_sample = self.cache.get(path)
        if cached_sample:
            return cached_sample

        # Validate file exists and is supported
        if not os.path.exists(path):
            raise FileNotFoundError(f"Sample file not found: {path}")

        file_ext = Path(path).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported audio format: {file_ext}")

        # Check file size for streaming decision
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > self.streaming_threshold_mb:
            # Use streaming for large files
            return self._create_streaming_sample(path)
        else:
            # Load fully into memory
            return self._load_full_sample(path)

    def _load_full_sample(self, path: str) -> SFZSample:
        """Load complete sample into memory"""
        try:
            # Open with PyAV
            container = av.open(path)

            # Get audio stream
            audio_stream = None
            for stream in container.streams:
                if stream.type == 'audio':
                    audio_stream = stream
                    break

            if not audio_stream:
                raise ValueError(f"No audio stream found in {path}")

            # Decode all frames
            frames = []
            for frame in container.decode(audio_stream):
                # Convert to numpy array (channels, samples) -> (samples, channels)
                frame_data = frame.to_ndarray().astype(np.float32).T
                frames.append(frame_data)

            # Concatenate all frames
            if frames:
                sample_data = np.concatenate(frames, axis=0)
            else:
                # Empty file
                sample_data = np.zeros((0, audio_stream.channels), dtype=np.float32)

            # Extract metadata
            metadata = self._extract_metadata(audio_stream, container)

            # Create sample
            sample = SFZSample(sample_data, metadata, path)

            # Cache it
            self.cache.put(path, sample)

            container.close()
            return sample

        except Exception as e:
            raise RuntimeError(f"Failed to load sample {path}: {e}")

    def _create_streaming_sample(self, path: str) -> StreamingSample:
        """Create streaming sample for large files"""
        try:
            container = av.open(path)
            audio_stream = None

            for stream in container.streams:
                if stream.type == 'audio':
                    audio_stream = stream
                    break

            if not audio_stream:
                container.close()
                raise ValueError(f"No audio stream found in {path}")

            return StreamingSample(container, audio_stream, path)

        except Exception as e:
            raise RuntimeError(f"Failed to create streaming sample {path}: {e}")

    def _extract_metadata(self, stream: av.audio.AudioStream,
                         container: av.container.Container) -> Dict[str, Any]:
        """Extract comprehensive metadata using PyAV"""
        metadata = {
            'sample_rate': stream.sample_rate,
            'channels': stream.channels,
            'duration_samples': stream.duration or 0,
            'bit_depth': self._get_bit_depth(stream),
            'codec': stream.codec.name,
            'format': container.format.name if container.format else 'unknown'
        }

        # Extract loop points from metadata
        if container.metadata:
            loop_start = container.metadata.get('loop_start')
            loop_end = container.metadata.get('loop_end')
            if loop_start and loop_end:
                metadata['loop_start'] = int(loop_start)
                metadata['loop_end'] = int(loop_end)

        # Extract cue points (if supported by format)
        metadata['cues'] = self._extract_cues(container)

        # Extract other metadata
        for key, value in container.metadata.items():
            if key not in ['loop_start', 'loop_end']:
                metadata[f'metadata_{key}'] = value

        return metadata

    def _get_bit_depth(self, stream: av.audio.AudioStream) -> int:
        """Determine bit depth from PyAV stream format"""
        format_bits = {
            'u8': 8, 's16': 16, 's32': 32, 'flt': 32, 'dbl': 64,
            'u8p': 8, 's16p': 16, 's32p': 32, 'fltp': 32, 'dblp': 64,
        }
        return format_bits.get(stream.format.name, 16)

    def _extract_cues(self, container: av.container.Container) -> List[Dict[str, Any]]:
        """Extract cue points from audio file"""
        cues = []

        # PyAV supports cue extraction for certain formats
        # This is a placeholder for future enhancement
        # WAV cue chunks, AIFF markers, etc. would be handled here

        return cues

    def preload_samples(self, sample_paths: List[str]) -> None:
        """Preload multiple samples into cache"""
        for path in sample_paths:
            try:
                self.load_sample(path)
            except Exception as e:
                print(f"Warning: Failed to preload sample {path}: {e}")

    def clear_cache(self) -> None:
        """Clear all cached samples"""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_samples': len(self.cache.cache),
            'memory_used_mb': self.cache.current_memory_bytes / (1024 * 1024),
            'max_memory_mb': self.cache.max_memory_bytes / (1024 * 1024)
        }

    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return sorted(list(self.SUPPORTED_FORMATS))

    def validate_sample_file(self, path: str) -> Tuple[bool, str]:
        """
        Validate that a file can be loaded as a sample

        Returns:
            (is_valid, error_message)
        """
        try:
            # Quick validation - try to open with PyAV
            container = av.open(path)
            has_audio = any(stream.type == 'audio' for stream in container.streams)
            container.close()

            if not has_audio:
                return False, "No audio stream found"

            return True, ""

        except Exception as e:
            return False, str(e)
