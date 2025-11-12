"""
SF2 Sample Cache

Handles caching of loaded SF2 sample data with memory management.
"""

import threading
import time
from collections import OrderedDict
from typing import Dict, Optional, Union, Tuple, List, Any
from ..types import SF2SampleHeader


class SampleCache:
    """
    Cache for SF2 sample data with LRU eviction policy.
    """

    def __init__(self, max_size: int = 50000000):  # ~200 MB default
        """
        Initialize sample cache with priority system.

        Args:
            max_size: Maximum cache size in samples (not bytes)
        """
        self.lock = threading.Lock()
        self.cache: OrderedDict[str, SF2SampleHeader] = OrderedDict()
        self.current_size = 0
        self.max_size = max_size

        # Priority system for cache management
        self.priority_cache: Dict[str, int] = {}  # key -> priority level
        self.access_counts: Dict[str, int] = {}  # key -> access count
        self.last_access: Dict[str, float] = {}  # key -> timestamp

    def get(self, key: str) -> Optional[SF2SampleHeader]:
        """
        Get sample from cache with priority tracking.

        Args:
            key: Cache key

        Returns:
            Sample header or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                # Update access statistics
                self.access_counts[key] = self.access_counts.get(key, 0) + 1
                self.last_access[key] = time.time()
                return self.cache[key]
            return None

    def put(self, key: str, sample: SF2SampleHeader, priority: int = 0) -> bool:
        """
        Put sample in cache with priority system.

        Args:
            key: Cache key
            sample: Sample header to cache
            priority: Priority level (higher = more important)

        Returns:
            True if successfully cached, False otherwise
        """
        if sample.data is None:
            return False

        with self.lock:
            # Calculate size estimate
            size_estimate = self._estimate_sample_size(sample)

            # Remove items if needed, considering priority
            while self.current_size + size_estimate > self.max_size and self.cache:
                # Find least valuable item to evict (lowest priority, then LRU)
                evict_key = self._find_eviction_candidate()
                if evict_key:
                    removed_sample = self.cache[evict_key]
                    removed_size = self._estimate_sample_size(removed_sample)
                    self.current_size -= removed_size
                    del self.cache[evict_key]
                    del self.priority_cache[evict_key]
                    del self.access_counts[evict_key]
                    del self.last_access[evict_key]

            # Add new item
            if self.current_size + size_estimate <= self.max_size:
                self.cache[key] = sample
                self.current_size += size_estimate
                self.priority_cache[key] = priority
                self.access_counts[key] = 1
                self.last_access[key] = time.time()
                return True

            return False

    def clear(self):
        """
        Clear all cached samples.
        """
        with self.lock:
            self.cache.clear()
            self.current_size = 0
            self.priority_cache.clear()
            self.access_counts.clear()
            self.last_access.clear()

    def _find_eviction_candidate(self) -> Optional[str]:
        """
        Find the best candidate for eviction based on priority and access patterns.

        Returns:
            Cache key to evict or None
        """
        if not self.cache:
            return None

        # Find item with lowest priority, then lowest access count, then oldest access
        candidates = []
        for key in self.cache.keys():
            priority = self.priority_cache.get(key, 0)
            access_count = self.access_counts.get(key, 0)
            last_access_time = self.last_access.get(key, 0)
            candidates.append((priority, access_count, last_access_time, key))

        # Sort by priority (ascending), then access count (ascending), then last access (ascending)
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))

        return candidates[0][3] if candidates else None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics including priority information.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            priority_counts = {}
            for priority in self.priority_cache.values():
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

            total_accesses = sum(self.access_counts.values())
            avg_accesses = total_accesses / len(self.access_counts) if self.access_counts else 0

            return {
                'current_size': self.current_size,
                'max_size': self.max_size,
                'utilization': self.current_size / self.max_size if self.max_size > 0 else 0.0,
                'num_samples': len(self.cache),
                'priority_distribution': priority_counts,
                'total_accesses': total_accesses,
                'avg_accesses_per_sample': avg_accesses
            }

    def _estimate_sample_size(self, sample: SF2SampleHeader) -> int:
        """
        Estimate memory size of a sample.

        Args:
            sample: Sample header

        Returns:
            Estimated size in samples
        """
        if sample.data is None:
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

    def preload_samples(self, samples: List[SF2SampleHeader], sf2_path: str, priority: int = 1) -> int:
        """
        Preload multiple samples into cache with priority.

        Args:
            samples: List of sample headers to preload
            sf2_path: Path to SF2 file for cache keys
            priority: Priority level for preloaded samples

        Returns:
            Number of samples successfully cached
        """
        cached_count = 0

        for sample in samples:
            if sample.data:  # Only cache if data is already loaded
                key = f"{sf2_path}.{sample.name}"
                if self.put(key, sample, priority):
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
                # Clean up priority tracking
                if key in self.priority_cache:
                    del self.priority_cache[key]
                if key in self.access_counts:
                    del self.access_counts[key]
                if key in self.last_access:
                    del self.last_access[key]
                evicted_count += 1

        return evicted_count

    def set_priority(self, key: str, priority: int):
        """
        Set priority for a cached sample.

        Args:
            key: Cache key
            priority: New priority level
        """
        with self.lock:
            if key in self.cache:
                self.priority_cache[key] = priority

    def get_priority(self, key: str) -> Optional[int]:
        """
        Get priority for a cached sample.

        Args:
            key: Cache key

        Returns:
            Priority level or None if not cached
        """
        with self.lock:
            return self.priority_cache.get(key)
