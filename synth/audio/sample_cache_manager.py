"""
Sample Cache Manager - Memory-efficient sample caching with LRU eviction.

Part of the unified region-based synthesis architecture.
SampleCacheManager manages sample data caching across all engines with:
- LRU (Least Recently Used) eviction
- Memory pressure monitoring
- Cross-engine sample sharing
- Performance statistics tracking
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
import threading
import time
import collections
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedSample:
    """
    Cached sample with metadata.
    
    Attributes:
        data: Sample audio data
        size_bytes: Size in bytes
        access_count: Number of times accessed
        last_access: Timestamp of last access
        source_id: Source soundfont/file identifier
        sample_id: Sample identifier within source
    """
    data: np.ndarray
    size_bytes: int
    source_id: str
    sample_id: int
    access_count: int = 1
    last_access: float = field(default_factory=time.time)
    
    def touch(self) -> None:
        """Update access timestamp and count."""
        self.access_count += 1
        self.last_access = time.time()


class SampleCacheManager:
    """
    Manages sample data caching across all engines.
    
    Implements LRU eviction with memory pressure monitoring.
    Thread-safe for concurrent access from multiple synthesis voices.
    
    Attributes:
        max_memory_mb: Maximum memory for sample cache in MB
        max_memory_bytes: Maximum memory in bytes
    """
    
    def __init__(self, max_memory_mb: int = 512):
        """
        Initialize sample cache manager.
        
        Args:
            max_memory_mb: Maximum memory for sample cache in megabytes
        """
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Cache: (source_id, sample_id) -> CachedSample
        self._cache: Dict[Tuple[str, int], CachedSample] = {}
        
        # Access order for LRU (oldest first)
        self._access_order: collections.deque = collections.deque()
        
        # Current memory usage
        self._current_memory_bytes = 0
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._evictions = 0
        self._load_failures = 0
    
    def get_sample(
        self, 
        source_id: str, 
        sample_id: int,
        loader: Callable[[], Optional[np.ndarray]]
    ) -> Optional[np.ndarray]:
        """
        Get sample from cache or load using provided loader.
        
        Args:
            source_id: Soundfont/file identifier
            sample_id: Sample identifier within source
            loader: Function to load sample if not cached
        
        Returns:
            Sample data or None if loading failed
        """
        key = (source_id, sample_id)
        
        with self._lock:
            # Check cache first
            if key in self._cache:
                cached = self._cache[key]
                cached.touch()
                self._cache_hits += 1
                
                # Move to end of access order (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                
                return cached.data
            
            # Cache miss - need to load
            self._cache_misses += 1
        
        # Load sample outside of lock to avoid blocking other threads
        try:
            sample_data = loader()
            if sample_data is None:
                with self._lock:
                    self._load_failures += 1
                return None
            
            # Cache the loaded sample
            self._cache_sample(key, sample_data, source_id, sample_id)
            return sample_data
            
        except Exception as e:
            logger.error(f"Sample loading failed for {source_id}:{sample_id}: {e}")
            with self._lock:
                self._load_failures += 1
            return None
    
    def _cache_sample(
        self, 
        key: Tuple[str, int], 
        sample_data: np.ndarray,
        source_id: str,
        sample_id: int
    ) -> None:
        """
        Add sample to cache with memory management.
        
        Args:
            key: Cache key (source_id, sample_id)
            sample_data: Sample audio data
            source_id: Source identifier
            sample_id: Sample identifier
        """
        sample_bytes = sample_data.nbytes
        
        with self._lock:
            # Check if we need to evict samples to make room
            while (self._current_memory_bytes + sample_bytes > 
                   self.max_memory_bytes):
                if not self._evict_least_recently_used():
                    # Cannot evict any more, reject this sample
                    logger.warning(
                        f"Cannot cache sample {source_id}:{sample_id} - "
                        f"cache full ({self._current_memory_bytes / 1024 / 1024:.1f}MB)"
                    )
                    return
            
            # Add to cache
            self._cache[key] = CachedSample(
                data=sample_data,
                size_bytes=sample_bytes,
                source_id=source_id,
                sample_id=sample_id
            )
            self._access_order.append(key)
            self._current_memory_bytes += sample_bytes
    
    def _evict_least_recently_used(self) -> bool:
        """
        Evict least recently used sample.
        
        Returns:
            True if a sample was evicted, False if cache was empty
        """
        if not self._access_order:
            return False
        
        # Get oldest key
        oldest_key = self._access_order.popleft()
        
        if oldest_key in self._cache:
            cached = self._cache[oldest_key]
            self._current_memory_bytes -= cached.size_bytes
            del self._cache[oldest_key]
            self._evictions += 1
            return True
        
        return False
    
    def evict_samples(self, count: int) -> int:
        """
        Evict a specific number of samples.
        
        Args:
            count: Number of samples to evict
        
        Returns:
            Number of samples actually evicted
        """
        evicted = 0
        with self._lock:
            for _ in range(count):
                if self._evict_least_recently_used():
                    evicted += 1
                else:
                    break
        return evicted
    
    def clear_cache(self) -> None:
        """Clear all cached samples."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._current_memory_bytes = 0
    
    def remove_sample(self, source_id: str, sample_id: int) -> bool:
        """
        Remove a specific sample from cache.
        
        Args:
            source_id: Source identifier
            sample_id: Sample identifier
        
        Returns:
            True if sample was removed, False if not found
        """
        key = (source_id, sample_id)
        
        with self._lock:
            if key not in self._cache:
                return False
            
            cached = self._cache[key]
            self._current_memory_bytes -= cached.size_bytes
            del self._cache[key]
            
            if key in self._access_order:
                self._access_order.remove(key)
            
            return True
    
    def is_cached(self, source_id: str, sample_id: int) -> bool:
        """
        Check if a sample is in cache.
        
        Args:
            source_id: Source identifier
            sample_id: Sample identifier
        
        Returns:
            True if sample is cached
        """
        key = (source_id, sample_id)
        with self._lock:
            return key in self._cache
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance metrics
        """
        with self._lock:
            total_accesses = self._cache_hits + self._cache_misses
            hit_rate = (
                self._cache_hits / total_accesses 
                if total_accesses > 0 else 0.0
            )
            
            return {
                'cached_samples': len(self._cache),
                'memory_used_mb': self._current_memory_bytes / (1024 * 1024),
                'memory_used_bytes': self._current_memory_bytes,
                'memory_limit_mb': self.max_memory_mb,
                'memory_limit_bytes': self.max_memory_bytes,
                'memory_usage_percent': (
                    self._current_memory_bytes / self.max_memory_bytes * 100
                    if self.max_memory_bytes > 0 else 0.0
                ),
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions,
                'load_failures': self._load_failures
            }
    
    def get_memory_pressure(self) -> float:
        """
        Get current memory pressure (0.0 to 1.0).
        
        Returns:
            Memory pressure ratio (1.0 = at limit)
        """
        with self._lock:
            return self._current_memory_bytes / self.max_memory_bytes
    
    def get_cached_samples_for_source(self, source_id: str) -> List[int]:
        """
        Get list of cached sample IDs for a source.
        
        Args:
            source_id: Source identifier
        
        Returns:
            List of sample IDs cached for this source
        """
        with self._lock:
            return [
                sample_id for (src, sample_id) in self._cache.keys()
                if src == source_id
            ]
    
    def preload_samples(
        self,
        samples: List[Tuple[str, int, Callable[[], Optional[np.ndarray]]]]
    ) -> int:
        """
        Preload multiple samples into cache.
        
        Args:
            samples: List of (source_id, sample_id, loader) tuples
        
        Returns:
            Number of samples successfully loaded
        """
        loaded = 0
        for source_id, sample_id, loader in samples:
            result = self.get_sample(source_id, sample_id, loader)
            if result is not None:
                loaded += 1
        return loaded
    
    def trim_to_fit(self, required_bytes: int) -> int:
        """
        Trim cache to make room for required bytes.
        
        Args:
            required_bytes: Bytes needed for new sample
        
        Returns:
            Number of samples evicted
        """
        evicted = 0
        with self._lock:
            while (self._current_memory_bytes + required_bytes > 
                   self.max_memory_bytes):
                if not self._evict_least_recently_used():
                    break
                evicted += 1
        return evicted
    
    def __len__(self) -> int:
        """Get number of cached samples."""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: Tuple[str, int]) -> bool:
        """Check if sample is cached."""
        return self.is_cached(key[0], key[1])
    
    def __str__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"SampleCacheManager(samples={stats['cached_samples']}, "
            f"memory={stats['memory_used_mb']:.1f}MB/{stats['memory_limit_mb']}MB, "
            f"hit_rate={stats['hit_rate']:.1%})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()


# Global sample cache instance (lazy initialized)
_global_cache: Optional[SampleCacheManager] = None
_global_cache_lock = threading.Lock()


def get_global_sample_cache(max_memory_mb: int = 512) -> SampleCacheManager:
    """
    Get or create global sample cache instance.
    
    Args:
        max_memory_mb: Maximum memory for cache
    
    Returns:
        Global SampleCacheManager instance
    """
    global _global_cache
    
    if _global_cache is None:
        with _global_cache_lock:
            if _global_cache is None:
                _global_cache = SampleCacheManager(max_memory_mb)
    
    return _global_cache


def reset_global_sample_cache() -> None:
    """Reset global sample cache (for testing)."""
    global _global_cache
    with _global_cache_lock:
        if _global_cache is not None:
            _global_cache.clear_cache()
            _global_cache = None
