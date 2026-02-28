"""
Professional Sample Manager - Advanced Sample Playback System

Comprehensive sample management with multi-layer playback, keygroup mapping,
velocity switching, and professional workstation features.

Part of S90/S70 compatibility - Enhanced Sampling System (Phase 3).
"""

from __future__ import annotations

import numpy as np
from typing import Any
from collections.abc import Callable
import threading
import os
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class SampleFormat(Enum):
    """Supported sample formats"""

    WAV = "wav"
    AIFF = "aiff"
    FLAC = "flac"
    OGG = "ogg"
    MP3 = "mp3"


class SampleQuality(Enum):
    """Sample quality settings"""

    COMPRESSED = "compressed"
    STANDARD = "standard"
    HIGH = "high"
    LOSSLESS = "lossless"


@dataclass(slots=True)
class SampleMetadata:
    """Sample metadata container"""

    name: str
    format: SampleFormat
    sample_rate: int
    bit_depth: int
    channels: int
    length_samples: int
    duration_seconds: float
    file_path: str | None = None
    file_size_bytes: int = 0
    checksum: str | None = None
    quality: SampleQuality = SampleQuality.STANDARD
    loop_start: int | None = None
    loop_end: int | None = None
    root_note: int = 60  # MIDI note number
    fine_tune: int = 0  # cents
    volume: float = 1.0
    pan: float = 0.0  # -1.0 to 1.0


@dataclass(slots=True)
class Keygroup:
    """Sample keygroup for keyboard mapping"""

    low_note: int
    high_note: int
    sample_id: str
    velocity_min: int = 0
    velocity_max: int = 127
    volume: float = 1.0
    pan: float = 0.0
    tune_coarse: int = 0
    tune_fine: int = 0
    filter_cutoff: float | None = None
    filter_resonance: float | None = None


@dataclass(slots=True)
class Multisample:
    """Multi-sample instrument definition"""

    id: str
    name: str
    keygroups: list[Keygroup]
    global_volume: float = 1.0
    global_pan: float = 0.0
    global_attack: float = 0.0
    global_decay: float = 0.0
    global_sustain: float = 1.0
    global_release: float = 0.1
    category: str = "user"
    description: str | None = None


class SampleCache:
    """Intelligent sample caching system"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.cache: dict[str, np.ndarray] = {}
        self.metadata: dict[str, SampleMetadata] = {}
        self.access_times: dict[str, float] = {}
        self.lock = threading.RLock()

        # Memory management
        self.current_memory_usage = 0
        self.compression_enabled = True

    def load_sample(
        self, sample_id: str, file_path: str, force_load: bool = False
    ) -> np.ndarray | None:
        """Load sample into cache with intelligent management"""
        with self.lock:
            # Check if already cached
            if sample_id in self.cache and not force_load:
                self.access_times[sample_id] = time.time()
                return self.cache[sample_id]

            # Load sample data
            sample_data = self._load_sample_from_file(file_path)
            if sample_data is None:
                return None

            # Check memory limits
            sample_size_mb = sample_data.nbytes / (1024 * 1024)
            if self.current_memory_usage + sample_size_mb > self.max_memory_mb:
                self._evict_samples(sample_size_mb)

            # Cache the sample
            self.cache[sample_id] = sample_data
            self.access_times[sample_id] = time.time()
            self.current_memory_usage += sample_size_mb

            return sample_data

    def _load_sample_from_file(self, file_path: str) -> np.ndarray | None:
        """Load sample from file"""
        try:
            import soundfile as sf

            audio_data, sr = sf.read(file_path, dtype="float32")

            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            if sr != self.sample_rate:
                num_samples = int(len(audio_data) * self.sample_rate / sr)
                x_old = np.arange(len(audio_data))
                x_new = np.linspace(0, len(audio_data) - 1, num_samples)
                audio_data = np.interp(x_new, x_old, audio_data)

            return audio_data

        except ImportError:
            try:
                import scipy.io.wavfile as wavfile

                sr, audio_data = wavfile.read(file_path)
                audio_data = audio_data.astype(np.float32) / 32768.0

                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)

                if sr != self.sample_rate:
                    num_samples = int(len(audio_data) * self.sample_rate / sr)
                    x_old = np.arange(len(audio_data))
                    x_new = np.linspace(0, len(audio_data) - 1, num_samples)
                    audio_data = np.interp(x_new, x_old, audio_data)

                return audio_data
            except Exception as e:
                # Python 3.11+: Add context to exception
                e.add_note(f"Failed to load sample with scipy: {file_path}")
                return None
        except Exception as e:
            # Python 3.11+: Add context to exception
            e.add_note(f"Failed to load sample with soundfile: {file_path}")
            e.add_note(f"Sample rate: {self.sample_rate}")
            return None

    def _evict_samples(self, required_mb: float):
        """Evict least recently used samples to free memory"""
        # Sort by access time (oldest first)
        sorted_samples = sorted(self.access_times.items(), key=lambda x: x[1])

        freed_mb = 0.0
        to_evict = []

        for sample_id, _ in sorted_samples:
            if sample_id in self.cache:
                sample_size = self.cache[sample_id].nbytes / (1024 * 1024)
                freed_mb += sample_size
                to_evict.append(sample_id)

                if freed_mb >= required_mb:
                    break

        # Evict samples
        for sample_id in to_evict:
            if sample_id in self.cache:
                sample_size = self.cache[sample_id].nbytes / (1024 * 1024)
                del self.cache[sample_id]
                del self.access_times[sample_id]
                self.current_memory_usage -= sample_size

    def get_sample_info(self, sample_id: str) -> SampleMetadata | None:
        """Get sample metadata"""
        return self.metadata.get(sample_id)

    def preload_samples(self, sample_ids: list[str]):
        """Preload multiple samples into cache"""
        for sample_id in sample_ids:
            if sample_id in self.metadata:
                metadata = self.metadata[sample_id]
                if metadata.file_path:
                    self.load_sample(sample_id, metadata.file_path)

    def clear_cache(self):
        """Clear entire sample cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.current_memory_usage = 0


class SampleManager:
    """
    Professional Sample Manager

    Advanced sample management system with multi-layer playback,
    keygroup mapping, velocity switching, and caching.
    """

    def __init__(self, max_samples: int = 1000, max_memory_mb: int = 512):
        """
        Initialize sample manager.

        Args:
            max_samples: Maximum number of samples to manage
            max_memory_mb: Maximum memory for sample cache
        """
        self.max_samples = max_samples
        self.max_memory_mb = max_memory_mb

        # Core components
        self.cache = SampleCache(max_memory_mb)
        self.samples: dict[str, SampleMetadata] = {}
        self.multisamples: dict[str, Multisample] = {}

        # Sample library organization
        self.categories: dict[str, list[str]] = {}
        self.favorites: list[str] = []

        # Playback state
        self.active_samples: dict[str, list[dict[str, Any]]] = {}

        # Callbacks
        self.sample_loaded_callback: Callable[[str], None] | None = None
        self.sample_unloaded_callback: Callable[[str], None] | None = None

        # Threading
        self.lock = threading.RLock()

        # Initialize default categories
        self._init_categories()

    def _init_categories(self):
        """Initialize sample categories"""
        self.categories = {
            "piano": [],
            "strings": [],
            "brass": [],
            "woodwinds": [],
            "percussion": [],
            "drums": [],
            "bass": [],
            "guitar": [],
            "synth": [],
            "effects": [],
            "user": [],
        }

    def add_sample(
        self, file_path: str, name: str | None = None, category: str = "user"
    ) -> str | None:
        """
        Add sample from file.

        Args:
            file_path: Path to sample file
            name: Sample name (uses filename if None)
            category: Sample category

        Returns:
            Sample ID or None if failed
        """
        with self.lock:
            if len(self.samples) >= self.max_samples:
                return None

            # Generate sample ID
            sample_id = self._generate_sample_id(file_path)

            # Check if already exists
            if sample_id in self.samples:
                return sample_id

            # Load metadata
            metadata = self._extract_metadata(file_path, name)
            if metadata is None:
                return None

            # Add to collection
            self.samples[sample_id] = metadata
            self.cache.metadata[sample_id] = metadata

            # Add to category
            if category not in self.categories:
                self.categories[category] = []
            if sample_id not in self.categories[category]:
                self.categories[category].append(sample_id)

            # Notify callback
            if self.sample_loaded_callback:
                self.sample_loaded_callback(sample_id)

            return sample_id

    def _generate_sample_id(self, file_path: str) -> str:
        """Generate unique sample ID from file path"""
        # Use file path hash for uniqueness
        return hashlib.md5(file_path.encode()).hexdigest()[:16]

    def _extract_metadata(self, file_path: str, name: str | None) -> SampleMetadata | None:
        """Extract metadata from sample file"""
        try:
            file_path_obj = Path(file_path)
            file_size = file_path_obj.stat().st_size if file_path_obj.exists() else 0

            # Generate checksum
            checksum = None
            if file_path_obj.exists():
                with open(file_path, "rb") as f:
                    checksum = hashlib.md5(f.read()).hexdigest()

            # Try to extract actual audio metadata
            sample_rate = 44100
            bit_depth = 16
            channels = 1
            length_samples = 44100

            try:
                import soundfile as sf

                info = sf.info(file_path)
                sample_rate = info.samplerate
                channels = info.channels
                length_samples = info.frames
                bit_depth = 16  # soundfile normalizes to float
            except ImportError:
                try:
                    import scipy.io.wavfile as wavfile

                    rate, data = wavfile.read(file_path)
                    sample_rate = rate
                    channels = 1 if len(data.shape) == 1 else data.shape[1]
                    length_samples = len(data)
                    bit_depth = data.dtype.itemsize * 8
                except Exception:
                    pass

            duration = length_samples / sample_rate if sample_rate > 0 else 0.0

            fmt = SampleFormat.WAV
            if file_path_obj.suffix.lower() in (".aiff", ".aif"):
                fmt = SampleFormat.AIFF
            elif file_path_obj.suffix.lower() == ".flac":
                fmt = SampleFormat.FLAC
            elif file_path_obj.suffix.lower() == ".ogg":
                fmt = SampleFormat.OGG

            return SampleMetadata(
                name=name or file_path_obj.stem,
                format=fmt,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                channels=channels,
                length_samples=length_samples,
                duration_seconds=duration,
                file_path=file_path,
                file_size_bytes=file_size,
                checksum=checksum,
                quality=SampleQuality.STANDARD,
            )
        except Exception:
            return None

    def remove_sample(self, sample_id: str) -> bool:
        """
        Remove sample from manager.

        Args:
            sample_id: Sample ID to remove

        Returns:
            True if removed successfully
        """
        with self.lock:
            if sample_id not in self.samples:
                return False

            # Remove from cache
            if sample_id in self.cache.cache:
                del self.cache.cache[sample_id]
            if sample_id in self.cache.metadata:
                del self.cache.metadata[sample_id]
            if sample_id in self.cache.access_times:
                del self.cache.access_times[sample_id]

            # Remove from categories
            for category_samples in self.categories.values():
                if sample_id in category_samples:
                    category_samples.remove(sample_id)

            # Remove from favorites
            if sample_id in self.favorites:
                self.favorites.remove(sample_id)

            # Remove from samples
            del self.samples[sample_id]

            # Notify callback
            if self.sample_unloaded_callback:
                self.sample_unloaded_callback(sample_id)

            return True

    def create_multisample(
        self, name: str, keygroups: list[Keygroup], category: str = "user"
    ) -> str:
        """
        Create multisample from keygroups.

        Args:
            name: Multisample name
            keygroups: List of keygroups
            category: Category

        Returns:
            Multisample ID
        """
        with self.lock:
            multisample_id = f"ms_{hashlib.md5(name.encode()).hexdigest()[:8]}"

            multisample = Multisample(
                id=multisample_id,
                name=name,
                keygroups=keygroups.copy(),
                category=category,
            )

            self.multisamples[multisample_id] = multisample

            # Add to category
            if category not in self.categories:
                self.categories[category] = []
            if multisample_id not in self.categories[category]:
                self.categories[category].append(multisample_id)

            return multisample_id

    def get_sample_data(self, sample_id: str, force_load: bool = False) -> np.ndarray | None:
        """
        Get sample audio data.

        Args:
            sample_id: Sample ID
            force_load: Force reload from disk

        Returns:
            Sample audio data or None
        """
        with self.lock:
            metadata = self.samples.get(sample_id)
            if not metadata or not metadata.file_path:
                return None

            return self.cache.load_sample(sample_id, metadata.file_path, force_load)

    def find_keygroup_for_note(
        self, multisample_id: str, note: int, velocity: int = 64
    ) -> Keygroup | None:
        """
        Find appropriate keygroup for note and velocity.

        Args:
            multisample_id: Multisample ID
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Matching keygroup or None
        """
        with self.lock:
            multisample = self.multisamples.get(multisample_id)
            if not multisample:
                return None

            # Find best matching keygroup
            best_match = None
            best_priority = -1

            for keygroup in multisample.keygroups:
                if (
                    keygroup.low_note <= note <= keygroup.high_note
                    and keygroup.velocity_min <= velocity <= keygroup.velocity_max
                ):
                    # Prioritize more specific ranges
                    priority = (keygroup.high_note - keygroup.low_note) + (
                        keygroup.velocity_max - keygroup.velocity_min
                    )

                    if priority > best_priority:
                        best_match = keygroup
                        best_priority = priority

            return best_match

    def get_samples_in_category(self, category: str) -> list[str]:
        """Get all sample IDs in a category"""
        with self.lock:
            return self.categories.get(category, []).copy()

    def get_multisamples_in_category(self, category: str) -> list[str]:
        """Get all multisample IDs in a category"""
        with self.lock:
            return [ms_id for ms_id, ms in self.multisamples.items() if ms.category == category]

    def search_samples(self, query: str, category: str | None = None) -> list[str]:
        """
        Search samples by name.

        Args:
            query: Search query
            category: Limit to specific category

        Returns:
            List of matching sample IDs
        """
        with self.lock:
            query_lower = query.lower()
            results = []

            search_space = self.samples
            if category:
                category_samples = set(self.categories.get(category, []))
                search_space = {
                    sid: self.samples[sid] for sid in category_samples if sid in self.samples
                }

            for sample_id, metadata in search_space.items():
                if query_lower in metadata.name.lower():
                    results.append(sample_id)

            return results

    def add_to_favorites(self, sample_id: str) -> bool:
        """Add sample to favorites"""
        with self.lock:
            if sample_id in self.samples and sample_id not in self.favorites:
                self.favorites.append(sample_id)
                return True
            return False

    def remove_from_favorites(self, sample_id: str) -> bool:
        """Remove sample from favorites"""
        with self.lock:
            if sample_id in self.favorites:
                self.favorites.remove(sample_id)
                return True
            return False

    def get_memory_usage(self) -> dict[str, Any]:
        """Get memory usage statistics"""
        with self.lock:
            total_samples = len(self.samples)
            total_multisamples = len(self.multisamples)
            cache_memory = self.cache.current_memory_usage

            return {
                "total_samples": total_samples,
                "total_multisamples": total_multisamples,
                "cache_memory_mb": cache_memory,
                "max_memory_mb": self.max_memory_mb,
                "memory_utilization": (cache_memory / self.max_memory_mb) * 100,
                "categories": {cat: len(samples) for cat, samples in self.categories.items()},
                "favorites_count": len(self.favorites),
            }

    def optimize_memory_usage(self):
        """Optimize memory usage by clearing unused samples"""
        with self.lock:
            # Clear samples not recently accessed
            current_time = time.time()
            max_age_seconds = 300  # 5 minutes

            to_remove = []
            for sample_id, access_time in self.cache.access_times.items():
                if current_time - access_time > max_age_seconds:
                    to_remove.append(sample_id)

            for sample_id in to_remove:
                if sample_id in self.cache.cache:
                    sample_size = self.cache.cache[sample_id].nbytes / (1024 * 1024)
                    del self.cache.cache[sample_id]
                    del self.cache.access_times[sample_id]
                    self.cache.current_memory_usage -= sample_size

    def export_sample_library(self, filename: str) -> bool:
        """
        Export sample library to file.

        Args:
            filename: Output filename

        Returns:
            True if exported successfully
        """
        with self.lock:
            try:
                export_data = {
                    "samples": {
                        sid: {
                            "metadata": metadata.__dict__,
                        }
                        for sid, metadata in self.samples.items()
                    },
                    "multisamples": {
                        msid: {
                            "id": ms.id,
                            "name": ms.name,
                            "keygroups": [kg.__dict__ for kg in ms.keygroups],
                            "global_volume": ms.global_volume,
                            "global_pan": ms.global_pan,
                            "global_attack": ms.global_attack,
                            "global_decay": ms.global_decay,
                            "global_sustain": ms.global_sustain,
                            "global_release": ms.global_release,
                            "category": ms.category,
                            "description": ms.description,
                        }
                        for msid, ms in self.multisamples.items()
                    },
                    "categories": self.categories.copy(),
                    "favorites": self.favorites.copy(),
                }

                import json

                with open(filename, "w") as f:
                    json.dump(export_data, f, indent=2)

                return True
            except Exception:
                return False

    def import_sample_library(self, filename: str) -> bool:
        """
        Import sample library from file.

        Args:
            filename: Input filename

        Returns:
            True if imported successfully
        """
        with self.lock:
            try:
                import json

                with open(filename) as f:
                    import_data = json.load(f)

                # Import samples
                for sample_id, sample_data in import_data.get("samples", {}).items():
                    metadata_dict = sample_data["metadata"]
                    metadata = SampleMetadata(**metadata_dict)
                    self.samples[sample_id] = metadata
                    self.cache.metadata[sample_id] = metadata

                # Import multisamples
                for ms_id, ms_data in import_data.get("multisamples", {}).items():
                    keygroups = []
                    for kg_data in ms_data["keygroups"]:
                        keygroup = Keygroup(**kg_data)
                        keygroups.append(keygroup)

                    multisample = Multisample(
                        id=ms_data["id"],
                        name=ms_data["name"],
                        keygroups=keygroups,
                        global_volume=ms_data.get("global_volume", 1.0),
                        global_pan=ms_data.get("global_pan", 0.0),
                        global_attack=ms_data.get("global_attack", 0.0),
                        global_decay=ms_data.get("global_decay", 0.0),
                        global_sustain=ms_data.get("global_sustain", 1.0),
                        global_release=ms_data.get("global_release", 0.1),
                        category=ms_data.get("category", "user"),
                        description=ms_data.get("description"),
                    )
                    self.multisamples[ms_id] = multisample

                # Import categories and favorites
                self.categories.update(import_data.get("categories", {}))
                self.favorites.extend(import_data.get("favorites", []))

                return True
            except Exception:
                return False

    def reset(self):
        """Reset sample manager to clean state"""
        with self.lock:
            self.samples.clear()
            self.multisamples.clear()
            self.categories = {"user": []}
            self.favorites.clear()
            self.cache.clear_cache()
            self.active_samples.clear()
