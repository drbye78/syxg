"""
XG Object Pool Implementation for high-performance object reuse.
Reduces garbage collection overhead and memory allocation pressure.
"""

import threading
import time
from typing import Dict, List, Type, Any, Optional, Callable, Generic, TypeVar
from collections import deque


T = TypeVar('T')


class XGObjectPool(Generic[T]):
    """
    High-performance object pooling system for XG synthesizer components.

    Provides thread-safe object reuse with automatic cleanup and monitoring.
    """

    def __init__(self, factory: Callable[[], T], max_size: int = 1024,
                 name: str = "XGObjectPool"):
        """
        Initialize object pool.

        Args:
            factory: Function that creates new instances of the pooled object
            max_size: Maximum number of objects to keep in pool
            name: Pool name for monitoring and debugging
        """
        self.factory = factory
        self.max_size = max_size
        self.name = name
        self._pool = deque(maxlen=max_size)
        self._lock = threading.RLock()

        # Statistics tracking
        self.created_count = 0
        self.acquired_count = 0
        self.released_count = 0
        self._hit_count = 0
        self._miss_count = 0

    def acquire(self) -> T:
        """Acquire an object from the pool or create new one."""
        with self._lock:
            obj = None

            # Try to get from pool first
            if self._pool:
                obj = self._pool.popleft()
                self._hit_count += 1
            else:
                self._miss_count += 1
                obj = self.factory()
                self.created_count += 1

            self.acquired_count += 1

            # Reset object state if it has a reset method
            if hasattr(obj, 'reset') and callable(getattr(obj, 'reset', None)):
                obj.reset()

            return obj

    def release(self, obj: T) -> bool:
        """Release object back to pool for reuse."""
        if obj is None:
            return False

        with self._lock:
            # Only add if pool has space
            if len(self._pool) < self.max_size:
                self._pool.append(obj)
                self.released_count += 1
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get pool performance statistics."""
        with self._lock:
            total_requests = self.acquired_count
            hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0

            return {
                'pool_name': self.name,
                'pool_size': len(self._pool),
                'max_size': self.max_size,
                'created_count': self.created_count,
                'hit_rate_percent': hit_rate,
                'total_requests': total_requests
            }


class XGPoolManager:
    """Centralized pool manager for XG synthesizer components."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._pools = {}

        # Initialize standard pools
        self._init_standard_pools()

    def _init_standard_pools(self):
        """Initialize pools for XG components."""
        from ..core.oscillator import LFO
        from ..core.envelope import ADSREnvelope
        from ..core.filter import ResonantFilter
        from ..modulation.matrix import ModulationMatrix

        self._pools['lfo'] = XGObjectPool(
            factory=lambda: LFO(id=0),
            max_size=512,
            name="LFO_Pool"
        )

        self._pools['adsr_envelope'] = XGObjectPool(
            factory=lambda: ADSREnvelope(),
            max_size=1024,
            name="ADSR_Envelope_Pool"
        )

        self._pools['resonant_filter'] = XGObjectPool(
            factory=lambda: ResonantFilter(),
            max_size=1024,
            name="Resonant_Filter_Pool"
        )

        self._pools['modulation_matrix'] = XGObjectPool(
            factory=lambda: ModulationMatrix(num_routes=16),
            max_size=256,
            name="Modulation_Matrix_Pool"
        )


# Global pool manager instance
xg_pools = XGPoolManager()


# Convenience functions
def acquire_lfo(**kwargs):
    lfo = xg_pools._pools['lfo'].acquire()
    if kwargs:
        lfo.set_parameters(**kwargs)
    return lfo

def release_lfo(lfo):
    return xg_pools._pools['lfo'].release(lfo)

def acquire_adsr_envelope(**kwargs):
    envelope = xg_pools._pools['adsr_envelope'].acquire()
    if kwargs:
        envelope.update_parameters(**kwargs)
    return envelope

def release_adsr_envelope(envelope):
    return xg_pools._pools['adsr_envelope'].release(envelope)

def acquire_resonant_filter(**kwargs):
    filter_obj = xg_pools._pools['resonant_filter'].acquire()
    if kwargs:
        filter_obj.set_parameters(**kwargs)
    return filter_obj

def release_resonant_filter(filter_obj):
    return xg_pools._pools['resonant_filter'].release(filter_obj)

def acquire_modulation_matrix(**kwargs):
    matrix = xg_pools._pools['modulation_matrix'].acquire()
    return matrix

def release_modulation_matrix(matrix):
    return xg_pools._pools['modulation_matrix'].release(matrix)
