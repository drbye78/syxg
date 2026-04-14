"""
SF2 Advanced Sample Processor

Handles mono/stereo sample processing, mip-mapping, interpolation, and caching.
Optimized for real-time synthesis with high-quality sample playback.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np


class MipMapLevel:
    """
    Single mip-map level for a sample.

    Contains downsampled version optimized for specific pitch ratios.
    """

    def __init__(self, level: int, data: np.ndarray, sample_rate: float, pitch_ratio: float):
        """
        Initialize mip-map level.

        Args:
            level: Mip level (0 = original, higher = more downsampled)
            data: Sample data for this level
            sample_rate: Effective sample rate after downsampling
            pitch_ratio: Pitch ratio this level is optimized for
        """
        self.level = level
        self.data = data
        self.sample_rate = sample_rate
        self.pitch_ratio = pitch_ratio
        self.memory_usage = data.nbytes if hasattr(data, "nbytes") else len(data) * 8


class SampleMipMap:
    """
    Complete mip-map pyramid for a sample.

    Generates and manages multiple downsampled versions for different pitch ratios.
    """

    def __init__(self, original_data: np.ndarray, original_sample_rate: float, max_levels: int = 8):
        """
        Initialize sample mip-map.

        Args:
            original_data: Original sample data
            original_sample_rate: Original sample rate
            max_levels: Maximum number of mip levels to generate
        """
        self.original_data = original_data
        self.original_sample_rate = original_sample_rate
        self.levels: dict[int, MipMapLevel] = {}
        self.max_levels = max_levels

        # Generate mip-map levels on demand
        self._generate_base_level()

    def _generate_base_level(self) -> None:
        """Generate level 0 (original sample)."""
        level0 = MipMapLevel(0, self.original_data, self.original_sample_rate, 1.0)
        self.levels[0] = level0

    def get_level(self, level: int) -> np.ndarray | None:
        """
        Get sample data for a specific mip level.

        Args:
            level: Mip level to retrieve

        Returns:
            Sample data or None if level doesn't exist
        """
        if level == 0:
            return self.levels[0].data

        if level in self.levels:
            return self.levels[level].data

        # Generate level if it doesn't exist
        if level <= self.max_levels:
            self._generate_level(level)

        return self.levels.get(level, self.levels[0]).data

    def _generate_level(self, level: int) -> None:
        """
        Generate a specific mip level with proper anti-aliasing.

        Args:
            level: Level to generate
        """
        current_data = self.levels[0].data
        downsample_factor = 2**level

        is_stereo = len(current_data.shape) > 1 and current_data.shape[1] == 2

        if is_stereo:
            frames = current_data.shape[0]
            if frames < downsample_factor * 4:
                return

            filtered_left = self._apply_anti_aliasing_filter(current_data[:, 0], downsample_factor)
            filtered_right = self._apply_anti_aliasing_filter(current_data[:, 1], downsample_factor)

            new_frames = frames // downsample_factor
            downsampled = np.zeros((new_frames, 2), dtype=current_data.dtype)

            for i in range(new_frames):
                pos = i * downsample_factor
                frac = pos - int(pos)
                pos_i = int(pos)

                s1_l = filtered_left[pos_i] if pos_i < len(filtered_left) else 0.0
                s2_l = filtered_left[min(pos_i + 1, len(filtered_left) - 1)]
                downsampled[i, 0] = s1_l + frac * (s2_l - s1_l)

                s1_r = filtered_right[pos_i] if pos_i < len(filtered_right) else 0.0
                s2_r = filtered_right[min(pos_i + 1, len(filtered_right) - 1)]
                downsampled[i, 1] = s1_r + frac * (s2_r - s1_r)
        else:
            if len(current_data) < downsample_factor * 4:
                return

            filtered_data = self._apply_anti_aliasing_filter(current_data, downsample_factor)

            new_length = len(filtered_data) // downsample_factor
            downsampled = np.zeros(new_length, dtype=current_data.dtype)

            for i in range(new_length):
                start_pos = i * downsample_factor
                frac = start_pos - int(start_pos)
                pos_i = int(start_pos)

                s1 = filtered_data[pos_i] if pos_i < len(filtered_data) else 0.0
                s2 = filtered_data[min(pos_i + 1, len(filtered_data) - 1)]
                downsampled[i] = s1 + frac * (s2 - s1)

        effective_sample_rate = self.original_sample_rate / downsample_factor
        pitch_ratio = 1.0 / downsample_factor

        mip_level = MipMapLevel(level, downsampled, effective_sample_rate, pitch_ratio)
        self.levels[level] = mip_level

    def _apply_anti_aliasing_filter(self, data: np.ndarray, downsample_factor: int) -> np.ndarray:
        """
        Apply anti-aliasing low-pass filter before downsampling.

        Args:
            data: Input sample data
            downsample_factor: Downsampling factor

        Returns:
            Filtered sample data
        """
        # Calculate cutoff frequency (Nyquist frequency of target sample rate)
        nyquist_target = self.original_sample_rate / (2 * downsample_factor)

        # Design simple but effective FIR low-pass filter
        # Filter length based on downsampling factor
        filter_length = min(64, downsample_factor * 8)  # Adaptive filter length
        if filter_length % 2 == 0:
            filter_length += 1  # Ensure odd length for symmetry

        # Create sinc-based low-pass filter
        t = np.arange(filter_length) - (filter_length - 1) / 2
        # Avoid division by zero
        sinc_kernel = np.sinc(2 * nyquist_target * t / self.original_sample_rate)
        sinc_kernel /= np.sum(sinc_kernel)  # Normalize

        # Apply Hamming window for better stop-band attenuation
        hamming_window = 0.54 - 0.46 * np.cos(
            2 * np.pi * np.arange(filter_length) / (filter_length - 1)
        )
        filter_kernel = sinc_kernel * hamming_window
        filter_kernel /= np.sum(filter_kernel)  # Renormalize after windowing

        # Apply filter using convolution
        filtered = np.convolve(data, filter_kernel, mode="same")

        # Handle edge effects by using reflection
        # (This is a simplified approach; production systems would use more sophisticated methods)
        fade_length = min(100, len(filtered) // 10)
        if fade_length > 0:
            # Apply gentle fade-in/fade-out to reduce edge artifacts
            fade_in = np.linspace(0.0, 1.0, fade_length)
            fade_out = np.linspace(1.0, 0.0, fade_length)

            filtered[:fade_length] *= fade_in
            filtered[-fade_length:] *= fade_out

        return filtered

    def get_optimal_level(self, pitch_ratio: float) -> int:
        """
        Get optimal mip level for a given pitch ratio.

        Args:
            pitch_ratio: Playback pitch ratio (> 1.0 = higher pitch)

        Returns:
            Optimal mip level
        """
        if pitch_ratio <= 1.0:
            return 0  # Use original for normal/low pitch

        # Find level where pitch_ratio best matches the level's pitch ratio
        best_level = 0
        min_distance = abs(pitch_ratio - 1.0)

        for level in range(1, len(self.levels) + 1):
            if level in self.levels:
                level_pitch_ratio = self.levels[level].pitch_ratio
                distance = abs(pitch_ratio - level_pitch_ratio)
                if distance < min_distance:
                    min_distance = distance
                    best_level = level

        return best_level

    def get_memory_usage(self) -> int:
        """Get total memory usage of all mip levels."""
        return sum(level.memory_usage for level in self.levels.values())


class MipLevelSelector:
    """
    Intelligent mip level selector based on pitch and quality requirements.
    """

    def __init__(self):
        """Initialize mip level selector."""
        # Cache for pitch ratio to level mappings
        self._pitch_cache: dict[float, int] = {}
        self._cache_lock = threading.Lock()

    def select_stable_level(self, pitch_ratio: float) -> int:
        """
        Select stable mip level for consistent quality.

        Args:
            pitch_ratio: Playback pitch ratio

        Returns:
            Selected mip level
        """
        with self._cache_lock:
            if pitch_ratio in self._pitch_cache:
                return self._pitch_cache[pitch_ratio]

            # Simple level selection based on pitch ratio
            if pitch_ratio < 1.5:
                level = 0
            elif pitch_ratio < 3.0:
                level = 1
            elif pitch_ratio < 6.0:
                level = 2
            elif pitch_ratio < 12.0:
                level = 3
            else:
                level = 4  # Maximum level

            self._pitch_cache[pitch_ratio] = level
            return level


class Interpolator:
    """
    Multi-stage sample interpolation system.

    Supports linear, cubic, sinc, and other interpolation methods.
    """

    def __init__(self, method: str = "linear"):
        """
        Initialize interpolator.

        Args:
            method: Interpolation method ('linear', 'cubic', 'sinc')
        """
        self.method = method
        self._interp_functions = {
            "linear": self._linear_interp,
            "cubic": self._cubic_interp,
            "sinc": self._sinc_interp,
        }

    def interpolate(
        self, sample_data: np.ndarray, ratio: float, target_length: int | None = None
    ) -> np.ndarray:
        """
        Interpolate sample data to new length.

        Args:
            sample_data: Input sample data
            ratio: Interpolation ratio
            target_length: Target length (calculated from ratio if None)

        Returns:
            Interpolated sample data
        """
        if target_length is None:
            target_length = int(len(sample_data) * ratio)

        if target_length == len(sample_data):
            return sample_data.copy()

        if self.method in self._interp_functions:
            return self._interp_functions[self.method](sample_data, target_length)
        else:
            return self._linear_interp(sample_data, target_length)

    def _linear_interp(self, data: np.ndarray, target_length: int) -> np.ndarray:
        """Linear interpolation."""
        if len(data) == 0:
            return np.array([], dtype=data.dtype)

        # Create index array for interpolation
        indices = np.linspace(0, len(data) - 1, target_length)

        # Linear interpolation
        result = np.interp(indices, np.arange(len(data)), data)
        return result.astype(data.dtype)

    def _cubic_interp(self, data: np.ndarray, target_length: int) -> np.ndarray:
        """Cubic interpolation using scipy if available, fallback to linear."""
        try:
            from scipy import interpolate

            # Create interpolation function
            x = np.arange(len(data))
            f = interpolate.interp1d(
                x, data, kind="cubic", bounds_error=False, fill_value=0.0
            )  # Use 0.0 as default

            # Interpolate to new length
            x_new = np.linspace(0, len(data) - 1, target_length)
            result = f(x_new)
            return np.asarray(result, dtype=data.dtype)
        except ImportError:
            # Fallback to linear
            return self._linear_interp(data, target_length)
        except Exception:
            # Additional fallback in case of other scipy errors
            return self._linear_interp(data, target_length)

    def _sinc_interp(self, data: np.ndarray, target_length: int) -> np.ndarray:
        """Sinc interpolation for high quality."""
        try:
            from scipy.signal import resample

            # Use scipy's resample for sinc interpolation
            resampled = resample(data, target_length)
            return np.asarray(resampled, dtype=data.dtype)
        except ImportError:
            # Fallback to linear
            return self._linear_interp(data, target_length)
        except Exception:
            # Additional fallback in case of other scipy errors
            return self._linear_interp(data, target_length)


class StereoProcessor:
    """
    Stereo sample processing and management.

    Handles stereo sample pairs, width control, and channel processing.
    """

    def __init__(self):
        """Initialize stereo processor."""
        self.stereo_pairs: dict[str, tuple[str, str]] = {}  # logical -> (left, right)
        self.width_control = 1.0  # Stereo width (0.0 = mono, 1.0 = full stereo)

    def register_stereo_pair(self, logical_name: str, left_sample: str, right_sample: str) -> None:
        """
        Register a stereo sample pair.

        Args:
            logical_name: Logical name for the stereo sample
            left_sample: Left channel sample name
            right_sample: Right channel sample name
        """
        self.stereo_pairs[logical_name] = (left_sample, right_sample)

    def get_stereo_samples(self, sample_name: str) -> tuple[str, str] | None:
        """
        Get stereo sample pair.

        Args:
            sample_name: Sample name to look up

        Returns:
            Tuple of (left, right) sample names or None
        """
        return self.stereo_pairs.get(sample_name)

    def process_stereo_width(
        self, left_data: np.ndarray, right_data: np.ndarray, width: float = 1.0
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Process stereo width control.

        Args:
            left_data: Left channel data
            right_data: Right channel data
            width: Stereo width (0.0 = mono, 1.0 = full stereo)

        Returns:
            Processed (left, right) channel data
        """
        if width == 1.0:
            return left_data, right_data

        # Stereo width processing
        # width = 0.0: mix to mono
        # width = 1.0: original stereo
        mid = (left_data + right_data) * 0.5
        side = (left_data - right_data) * 0.5

        # Apply width control
        mid_processed = mid
        side_processed = side * width

        # Convert back to left/right
        left_processed = mid_processed + side_processed
        right_processed = mid_processed - side_processed

        return left_processed, right_processed

    def create_mono_from_stereo(self, left_data: np.ndarray, right_data: np.ndarray) -> np.ndarray:
        """
        Create mono sample from stereo pair.

        Args:
            left_data: Left channel data
            right_data: Right channel data

        Returns:
            Mono sample data
        """
        return (left_data + right_data) * 0.5


class SF2SampleCache:
    """
    LRU cache for processed samples with memory limits.

    Caches processed sample data across multiple SF2 files.
    """

    def __init__(self, max_memory_mb: int = 256):
        """
        Initialize sample cache.

        Args:
            max_memory_mb: Maximum memory for cached samples
        """
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.current_memory = 0
        self.cache: Ordereddict[str, tuple[np.ndarray, int]] = {}  # key -> (data, size)
        self.lock = threading.RLock()

    def get(self, key: str) -> np.ndarray | None:
        """
        Get sample from cache.

        Args:
            key: Cache key

        Returns:
            Sample data or None if not cached
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                data, size = self.cache.pop(key)
                self.cache[key] = (data, size)
                return data.copy()
            return None

    def put(self, key: str, data: np.ndarray) -> None:
        """
        Put sample in cache.

        Args:
            key: Cache key
            data: Sample data to cache
        """
        with self.lock:
            size = data.nbytes

            # Remove if already exists
            if key in self.cache:
                old_data, old_size = self.cache[key]
                self.current_memory -= old_size

            # Check memory limits
            self._ensure_memory_available(size)

            # Add to cache
            self.cache[key] = (data.copy(), size)
            self.current_memory += size

    def _ensure_memory_available(self, needed_size: int) -> None:
        """Ensure enough memory by evicting LRU items."""
        while self.current_memory + needed_size > self.max_memory and self.cache:
            # Evict least recently used
            evicted_key, (evicted_data, evicted_size) = self.cache.popitem(last=False)
            self.current_memory -= evicted_size
            # Explicitly delete the evicted data to free memory
            del evicted_data

    def clear(self) -> None:
        """Clear all cached samples."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "cached_samples": len(self.cache),
                "memory_usage_bytes": self.current_memory,
                "memory_usage_mb": self.current_memory / (1024 * 1024),
                "max_memory_mb": self.max_memory / (1024 * 1024),
                "utilization": (self.current_memory / self.max_memory * 100)
                if self.max_memory > 0
                else 0.0,
            }


class SF2SampleProcessor:
    """
    Advanced SF2 sample processor with mip-mapping and interpolation.

    Handles all sample processing needs for high-quality SF2 synthesis.
    """

    def __init__(self, cache_memory_mb: int = 256):
        """
        Initialize sample processor.

        Args:
            cache_memory_mb: Memory limit for sample caching
        """
        self.sample_cache = SF2SampleCache(cache_memory_mb)
        self.mip_maps: dict[str, SampleMipMap] = {}
        self.mip_selectors: dict[str, MipLevelSelector] = {}
        self.interpolator = Interpolator("linear")  # Default to linear
        self.stereo_processor = StereoProcessor()

        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0

    def process_sample(
        self,
        raw_data: bytes,
        sample_info: dict[str, Any],
        pitch_ratio: float = 1.0,
        interpolation: str = "linear",
    ) -> np.ndarray | None:
        """
        Process sample data with all enhancements.

        Args:
            raw_data: Raw sample data bytes
            sample_info: Sample metadata
            pitch_ratio: Pitch ratio for mip-mapping
            interpolation: Interpolation method

        Returns:
            Processed sample data
        """
        # Create cache key
        sample_name = sample_info.get("name", "unknown")
        cache_key = f"{sample_name}_{pitch_ratio}_{interpolation}"

        # Check cache first
        cached_data = self.sample_cache.get(cache_key)
        if cached_data is not None:
            with self.sample_cache.lock:  # Thread-safe increment
                self.cache_hits += 1
            return cached_data

        with self.sample_cache.lock:  # Thread-safe increment
            self.cache_misses += 1

        # Process sample data
        processed_data = self._process_sample_data(
            raw_data, sample_info, pitch_ratio, interpolation
        )

        if processed_data is not None:
            # Cache the result
            self.sample_cache.put(cache_key, processed_data)

        return processed_data

    def _process_sample_data(
        self, raw_data: bytes, sample_info: dict[str, Any], pitch_ratio: float, interpolation: str
    ) -> np.ndarray | None:
        """Internal sample processing."""
        try:
            # Parse sample format
            bit_depth = sample_info.get("bit_depth", 16)
            is_stereo = sample_info.get("is_stereo", False)

            # Convert raw data to numpy array
            if bit_depth == 16:
                sample_data = self._convert_16bit_data(raw_data, is_stereo)
            elif bit_depth == 24:
                sample_data = self._convert_24bit_data(raw_data, is_stereo)
            else:
                return None

            # Apply mip-mapping for high pitch ratios
            if pitch_ratio > 1.5:
                sample_data = self._apply_mip_mapping(sample_data, sample_info, pitch_ratio)

            # Apply interpolation if needed
            if interpolation != "linear":
                self.interpolator.method = interpolation
                # Interpolate to improve quality (example: slight oversampling)
                target_length = int(len(sample_data) * 1.1)  # 10% oversampling
                sample_data = self.interpolator.interpolate(sample_data, 1.1, target_length)

            return sample_data

        except Exception as e:
            print(f"Error processing sample {sample_info.get('name', 'unknown')}: {e}")
            return None

    def _convert_16bit_data(self, data: bytes, is_stereo: bool) -> np.ndarray:
        """Convert 16-bit sample data."""
        if len(data) == 0:
            return np.array([], dtype=np.float32)

        samples = np.frombuffer(data, dtype=np.int16)

        if is_stereo:
            # Reshape to (frames, 2) for stereo
            if len(samples) % 2 == 0 and len(samples) >= 2:
                return samples.reshape(-1, 2).astype(np.float32) / 32768.0
            else:
                # Handle odd length or insufficient data
                return samples.astype(np.float32) / 32768.0
        else:
            return samples.astype(np.float32) / 32768.0

    def _convert_24bit_data(self, data: bytes, is_stereo: bool) -> np.ndarray:
        """Convert 24-bit sample data."""
        if len(data) == 0:
            return np.array([], dtype=np.float32)

        samples = []

        if is_stereo:
            # Process 6 bytes per stereo frame
            for i in range(0, len(data), 6):
                if i + 6 > len(data):
                    break

                # Left channel (first 3 bytes)
                left_bytes = data[i : i + 3]
                left_int = int.from_bytes(left_bytes, byteorder="little", signed=True)
                if left_int & 0x800000:
                    left_int |= 0xFF000000
                left_sample = left_int / 8388608.0

                # Right channel (next 3 bytes)
                right_bytes = data[i + 3 : i + 6]
                right_int = int.from_bytes(right_bytes, byteorder="little", signed=True)
                if right_int & 0x800000:
                    right_int |= 0xFF000000
                right_sample = right_int / 8388608.0

                samples.extend([left_sample, right_sample])

            # Only reshape if we have an even number of samples
            if len(samples) % 2 == 0 and len(samples) >= 2:
                return np.array(samples, dtype=np.float32).reshape(-1, 2)
            else:
                return np.array(samples, dtype=np.float32)
        else:
            # Process 3 bytes per mono sample
            for i in range(0, len(data), 3):
                if i + 3 > len(data):
                    break

                sample_bytes = data[i : i + 3]
                sample_int = int.from_bytes(sample_bytes, byteorder="little", signed=True)
                if sample_int & 0x800000:
                    sample_int |= 0xFF000000
                sample = sample_int / 8388608.0
                samples.append(sample)

            return np.array(samples, dtype=np.float32)

    def _apply_mip_mapping(
        self, sample_data: np.ndarray, sample_info: dict[str, Any], pitch_ratio: float
    ) -> np.ndarray:
        """Apply mip-mapping for high-pitch playback."""
        sample_name = sample_info.get("name", "unknown")
        sample_rate = sample_info.get("sample_rate", 44100)

        # Get or create mip-map
        if sample_name not in self.mip_maps:
            self.mip_maps[sample_name] = SampleMipMap(sample_data, sample_rate)
            self.mip_selectors[sample_name] = MipLevelSelector()

        mip_map = self.mip_maps[sample_name]
        selector = self.mip_selectors[sample_name]

        # Select optimal mip level based on pitch ratio and sample rate considerations
        level = selector.select_stable_level(pitch_ratio)

        if level > 0:
            try:
                mip_data = mip_map.get_level(level)
                if mip_data is not None:
                    # Ensure the returned data has the same shape and type as the original
                    if mip_data.shape != sample_data.shape:
                        # If shapes differ, we need to resample to match
                        if len(sample_data.shape) == 1 and len(mip_data.shape) == 1:
                            # Both are mono, just adjust length
                            if len(mip_data) != len(sample_data):
                                interpolator = Interpolator("linear")
                                mip_data = interpolator.interpolate(
                                    mip_data, len(sample_data) / len(mip_data)
                                )
                        elif len(sample_data.shape) > 1 and len(mip_data.shape) > 1:
                            # Both are stereo, adjust both channels
                            if mip_data.shape != sample_data.shape:
                                interpolator = Interpolator("linear")
                                if mip_data.shape[0] != sample_data.shape[0]:
                                    # Adjust number of frames
                                    new_data = np.zeros_like(sample_data)
                                    for ch in range(min(mip_data.shape[1], sample_data.shape[1])):
                                        channel_data = interpolator.interpolate(
                                            mip_data[:, ch],
                                            sample_data.shape[0] / mip_data.shape[0],
                                        )
                                        new_data[:, ch] = channel_data[: sample_data.shape[0]]
                                    mip_data = new_data
                    return mip_data
            except Exception:
                pass  # Fall back to original

        return sample_data

    def set_interpolation_method(self, method: str) -> None:
        """
        Set interpolation method.

        Args:
            method: Interpolation method ('linear', 'cubic', 'sinc')
        """
        if method in ["linear", "cubic", "sinc"]:
            self.interpolator.method = method

    def configure_stereo_pair(self, logical_name: str, left_sample: str, right_sample: str) -> None:
        """
        Configure stereo sample pair.

        Args:
            logical_name: Logical name for stereo sample
            left_sample: Left channel sample name
            right_sample: Right channel sample name
        """
        self.stereo_processor.register_stereo_pair(logical_name, left_sample, right_sample)

    def get_stereo_samples(self, sample_name: str) -> tuple[str, str] | None:
        """
        Get stereo sample pair.

        Args:
            sample_name: Sample name

        Returns:
            Tuple of (left, right) sample names
        """
        return self.stereo_processor.get_stereo_samples(sample_name)

    def preload_sample(
        self, sample_name: str, sample_data: np.ndarray, sample_rate: float = 44100
    ) -> None:
        """
        Preload sample into mip-map system.

        Args:
            sample_name: Sample name
            sample_data: Sample data
            sample_rate: Sample rate
        """
        if sample_name not in self.mip_maps:
            self.mip_maps[sample_name] = SampleMipMap(sample_data, sample_rate)
            self.mip_selectors[sample_name] = MipLevelSelector()

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        total_mip_maps = len(self.mip_maps)
        total_mip_memory = sum(mip_map.get_memory_usage() for mip_map in self.mip_maps.values())

        cache_stats = self.sample_cache.get_stats()

        total_queries = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_queries * 100) if total_queries > 0 else 0.0

        return {
            "cache_stats": cache_stats,
            "mip_maps": total_mip_maps,
            "mip_memory_mb": total_mip_memory / (1024 * 1024),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_queries": total_queries,
            "cache_hit_rate": round(hit_rate, 2),
            "interpolation_method": self.interpolator.method,
            "stereo_pairs": len(self.stereo_processor.stereo_pairs),
        }

    def clear_cache(self) -> None:
        """Clear all caches and mip-maps."""
        self.sample_cache.clear()
        self.mip_maps.clear()
        self.mip_selectors.clear()
        self.cache_hits = 0
        self.cache_misses = 0
