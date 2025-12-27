"""
SF2 Memory Management

Ultra-fast direct dict caching for SF2 synthesis parameters.
No serialization overhead - direct Python object storage.
"""

from typing import Dict, List, Any, Optional, Tuple
import threading
import time
from collections import OrderedDict

class MemoryPool:
    """Ultra-fast direct dict caching for SF2 parameter sets. No serialization overhead."""

    def __init__(self):
        # Direct dict storage - no serialization
        self.program_param_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # LRU cache for hot parameters (expanded to 1024 entries)
        self._hot_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hot_cache_max_size = 1024  # Increased for better hit rate

        # Statistics
        self.total_stored_params = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.allocation_count = 0

        # Thread safety
        self._lock = threading.RLock()

    def alloc_param_set(self, param_data: Dict[str, Any]) -> str:
        """Store parameter set directly - no serialization. Returns cache key."""
        with self._lock:
            # Generate unique key for this parameter set
            cache_key = f"param_{self.allocation_count}_{hash(str(param_data))}"
            self.allocation_count += 1

            # Store directly in hot cache (will be LRU managed)
            if len(self._hot_cache) >= self._hot_cache_max_size:
                # Remove least recently used
                self._hot_cache.popitem(last=False)

            self._hot_cache[cache_key] = param_data.copy()  # Store copy
            self.total_stored_params += 1

            return cache_key

    def read_param_set(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Read parameter set directly from cache - zero deserialization overhead."""
        with self._lock:
            if cache_key in self._hot_cache:
                # Move to end (most recently used)
                self._hot_cache.move_to_end(cache_key)
                self.cache_hits += 1
                return self._hot_cache[cache_key]
            else:
                self.cache_misses += 1
                return None

    def cache_program_params(self, params: Dict[str, Any], program: int, bank: int, note: int, velocity: int):
        """Cache program parameters directly in LRU cache."""
        with self._lock:
            prog_key = f"{program}-{bank}"
            instance_key = f"{note}-{velocity}"
            cache_key = f"{prog_key}:{instance_key}"

            # Store directly in hot cache
            if len(self._hot_cache) >= self._hot_cache_max_size:
                # Remove least recently used
                self._hot_cache.popitem(last=False)

            self._hot_cache[cache_key] = params.copy()
            self.total_stored_params += 1

    def get_program_params(self, program: int, bank: int, note: int, velocity: int) -> Optional[Dict[str, Any]]:
        """Get cached program parameters with ultra-fast direct access."""
        with self._lock:
            prog_key = f"{program}-{bank}"
            instance_key = f"{note}-{velocity}"
            cache_key = f"{prog_key}:{instance_key}"

            # Direct LRU cache access - no serialization/deserialization
            if cache_key in self._hot_cache:
                # Move to end (most recently used)
                self._hot_cache.move_to_end(cache_key)
                self.cache_hits += 1
                return self._hot_cache[cache_key]
            else:
                self.cache_misses += 1
                return None

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory and performance statistics."""
        import sys

        # Calculate memory usage of cached dicts
        cache_memory = sum(sys.getsizeof(params) for params in self._hot_cache.values())

        hit_rate = self.cache_hits / max(1, self.cache_hits + self.cache_misses)

        return {
            'total_cache_entries': len(self._hot_cache),
            'max_cache_size': self._hot_cache_max_size,
            'cache_memory_kb': cache_memory / 1024,
            'cache_hit_rate': hit_rate,
            'total_stored_params': self.total_stored_params,
            'allocation_count': self.allocation_count,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'serialization': 'direct_dict',
            'thread_safe': True,
        }

    def clear(self):
        """Clear all caches."""
        with self._lock:
            self.program_param_cache.clear()
            self._hot_cache.clear()
            self.total_stored_params = 0
            self.cache_hits = 0
            self.cache_misses = 0
            self.allocation_count = 0
