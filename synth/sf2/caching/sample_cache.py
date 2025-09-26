"""
SF2 Sample Cache

Handles caching of loaded SF2 sample data with memory management.
"""

import threading
from collections import OrderedDict
from typing import Dict, Optional, Union, Tuple, List
from ..types import SF2SampleHeader


class SampleCache:
    """
    Cache for SF2 sample data with LRU eviction policy.
    """

    def __init__(self, max_size: int = 50000000):  # ~200 MB default
        """
        Initialize sample cache.

        Args:
            max_size: Maximum cache size in samples (not bytes)
        """
        self.lock = threading.Lock()
        self.cache: OrderedDict[str, SF2SampleHeader] = OrderedDict()
        self.current_size = 0
        self.max_size = max_size

    def get(self, key: str) -> Optional[SF2SampleHeader]:
        """
        Get sample from cache.

        Args:
            key: Cache key

        Returns:
            Sample header or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def put(self, key: str, sample: SF2SampleHeader) -> bool:
        """
        Put sample in cache.

        Args:
            key: Cache key
            sample: Sample header to cache

        Returns:
            True if successfully cached, False otherwise
        """
        if not sample.data:
            return False

        with self.lock:
            # Calculate size estimate
            size_estimate = self._estimate_sample_size(sample)

            # Remove least recently used items if needed
            while self.current_size + size_estimate > self.max_size and self.cache:
                _, removed_sample = self.cache.popitem(last=False)
                removed_size = self._estimate_sample_size(removed_sample)
                self.current_size -= removed_size

            # Add new item
            if self.current_size + size_estimate <= self.max_size:
                self.cache[key] = sample
                self.current_size += size_estimate
                return True

            return False

    def clear(self):
        """
        Clear all cached samples.
        """
        with self.lock:
            self.cache.clear()
            self.current_size = 0

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            return {
                'current_size': self.current_size,
                'max_size': self.max_size,
                'utilization': self.current_size / self.max_size if self.max_size > 0 else 0.0,
                'num_samples': len(self.cache)
            }

    def _estimate_sample_size(self, sample: SF2SampleHeader) -> int:
        """
        Estimate memory size of a sample.

        Args:
            sample: Sample header

        Returns:
            Estimated size in samples
        """
        if not sample.data:
            return 0

        sample_length = sample.end - sample.start
        if sample_length <= 0:
            return 0

        # Base size for 16-bit samples
        base_size = sample_length * 2

        # Additional size for stereo
        if sample.stereo:
            base_size *= 2

        # Python list/tuple overhead (rough estimate)
        python_overhead = sample_length * 8  # ~8 bytes per float/tuple

        return base_size + python_overhead

    def preload_samples(self, samples: List[SF2SampleHeader], sf2_path: str) -> int:
        """
        Preload multiple samples into cache.

        Args:
            samples: List of sample headers to preload
            sf2_path: Path to SF2 file for cache keys

        Returns:
            Number of samples successfully cached
        """
        cached_count = 0

        for sample in samples:
            if sample.data:  # Only cache if data is already loaded
                key = f"{sf2_path}.{sample.name}"
                if self.put(key, sample):
                    cached_count += 1

        return cached_count

    def evict_by_pattern(self, pattern: str) -> int:
        """
        Evict samples matching a pattern.

        Args:
            pattern: Pattern to match in cache keys

        Returns:
            Number of samples evicted
        """
        evicted_count = 0

        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]

            for key in keys_to_remove:
                sample = self.cache[key]
                size_estimate = self._estimate_sample_size(sample)
                self.current_size -= size_estimate
                del self.cache[key]
                evicted_count += 1

        return evicted_count
