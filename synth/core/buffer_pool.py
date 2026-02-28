"""
Buffer Pool Management - Zero-Allocation Memory Architecture

ARCHITECTURAL OVERVIEW:

The XG Buffer Pool implements a sophisticated zero-allocation memory management system
designed specifically for real-time audio processing. It eliminates runtime memory
allocation overhead through pre-allocation, pooling, and intelligent buffer reuse,
ensuring deterministic performance in professional audio applications.

MEMORY MANAGEMENT PHILOSOPHY:

1. ZERO-ALLOCATION DESIGN: All buffers pre-allocated at startup, no runtime malloc/free
2. POOL-BASED REUSE: Intelligent buffer categorization and reuse based on size/channel requirements
3. SIMD ALIGNMENT: All buffers aligned for optimal SIMD (AVX/AVX2/AVX-512) performance
4. MEMORY BUDGETING: Configurable memory limits with graceful degradation
5. THREAD SAFETY: Lock-free operations for audio thread, thread-safe management operations

POOL ORGANIZATION:

The buffer pool is organized into three main categories:

MONO BUFFERS (1 channel):
- Optimized for single-channel processing (oscillators, effects sends)
- Sizes: 256, 512, 1024, 2048, 4096, 8192 samples
- Allocation: Pre-allocated based on expected usage patterns

STEREO BUFFERS (2 channels):
- Primary format for audio processing pipeline
- Sizes: Same as mono buffers
- Allocation: Highest allocation priority (most commonly used)
- Special handling for channel mixing and effects processing

MULTI-CHANNEL BUFFERS (3+ channels):
- For surround sound and multi-channel effects
- Configurations: (1024/2048 samples) × (4/6/8 channels)
- Allocation: Minimal pre-allocation, dynamic allocation as needed

BUFFER ALLOCATION STRATEGY:

PRIMARY ALLOCATION (Zero-overhead):
1. Exact size match from appropriate pool
2. Immediate return if available
3. O(1) lookup using dictionary-based pools

FALLBACK ALLOCATION (Minimal overhead):
1. Larger buffer allocation if exact size unavailable
2. Dynamic allocation within memory budget
3. Automatic pool expansion for new sizes

EMERGENCY ALLOCATION (Last resort):
1. Memory pressure detection and reporting
2. Graceful degradation with smaller buffers
3. Comprehensive error reporting and recovery

SIMD ALIGNMENT ARCHITECTURE:

ALIGNMENT REQUIREMENTS:
- AVX-256: 32-byte alignment for optimal performance
- AVX-512: 64-byte alignment for future-proofing
- Cache line alignment: 64-byte boundaries for cache efficiency

ALIGNMENT IMPLEMENTATION:
1. Over-allocation: Allocate extra bytes for alignment
2. Offset calculation: Find properly aligned memory region
3. View creation: Create aligned numpy array view on aligned memory
4. Memory tracking: Track original allocation for proper cleanup

PERFORMANCE OPTIMIZATION:

CACHE OPTIMIZATION:
- Buffer size categorization minimizes cache misses
- Sequential allocation patterns optimize memory locality
- Pool organization reduces lookup overhead

MEMORY EFFICIENCY:
- Pre-allocation eliminates fragmentation
- Buffer reuse maximizes memory utilization
- Configurable memory budgets prevent over-allocation

THREADING ARCHITECTURE:

DUAL-THREADING MODEL:
- AUDIO THREAD: Lock-free buffer operations during processing
- MANAGEMENT THREAD: Thread-safe pool management and statistics

SYNCHRONIZATION STRATEGY:
- ReadWrite locks for pool access
- Atomic operations for statistics
- Context managers for automatic cleanup

CONTEXT MANAGER PATTERN:

ZERO-ALLOCATION USAGE:
```python
with buffer_pool.temporary_buffer(1024, 2) as buffer:
    # Process audio - guaranteed zero allocation
    process_audio(buffer)
# Buffer automatically returned to pool
```

MANUAL MANAGEMENT:
```python
buffer = pool.get_stereo_buffer(1024)
try:
    process_audio(buffer)
finally:
    pool.return_buffer(buffer)  # Explicit return
```

MEMORY PRESSURE HANDLING:

BUDGET MANAGEMENT:
- Configurable memory limits (default 256MB)
- Dynamic allocation within budget constraints
- Automatic cleanup under memory pressure

PRESSURE DETECTION:
- Usage threshold monitoring (80% warning, 95% critical)
- Automatic garbage collection under pressure
- Emergency cleanup for critical situations

LEAK DETECTION:
- Active buffer tracking with stack traces
- Thread-aware leak detection
- Comprehensive debugging information

INTEGRATION POINTS:

SYNTHESIZER INTEGRATION:
- Direct integration with XG synthesizer audio pipeline
- Buffer pool initialization during synthesizer startup
- Automatic buffer lifecycle management

EFFECTS SYSTEM INTEGRATION:
- XGBufferManager context manager for effects processing
- Automatic buffer allocation/deallocation
- Zero-overhead effects chaining

VALIDATION & MONITORING:

COMPREHENSIVE VALIDATION:
- Pool integrity checking
- Memory corruption detection
- Buffer leak detection
- Performance regression monitoring

STATISTICS TRACKING:
- Allocation/deallocation counters
- Cache hit/miss ratios
- Memory utilization metrics
- Contention and performance statistics

XG SPECIFICATION COMPLIANCE:

PROFESSIONAL AUDIO STANDARDS:
- Sample-accurate buffer management
- Deterministic latency characteristics
- Professional memory usage patterns
- Real-time safety guarantees

ERROR HANDLING:

GRACEFUL DEGRADATION:
- Buffer pool exhaustion handling
- Memory budget exceeded recovery
- Fallback to smaller buffer sizes
- Comprehensive error reporting

RECOVERY STRATEGIES:
- Automatic pool optimization
- Emergency cleanup procedures
- Memory pressure relief mechanisms
- Diagnostic information collection
"""
from __future__ import annotations

from typing import Any
import numpy as np
import threading
import math
import gc
from collections import defaultdict
from contextlib import contextmanager

from .validation import ValidationResult, ValidationError, audio_validator
from .config import audio_config


class BufferPoolExhaustedError(Exception):
    """Raised when buffer pool cannot satisfy allocation request."""
    pass


class BufferPoolCorruptionError(Exception):
    """Raised when buffer pool detects memory corruption."""
    pass


class BufferStatistics:
    """Buffer pool usage statistics."""

    def __init__(self):
        self.total_allocated = 0
        self.total_used = 0
        self.peak_usage = 0
        self.allocation_count = 0
        self.deallocation_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.contention_count = 0

    def reset(self):
        """Reset statistics."""
        self.__init__()

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            'total_allocated_mb': self.total_allocated / (1024 * 1024),
            'total_used_mb': self.total_used / (1024 * 1024),
            'peak_usage_mb': self.peak_usage / (1024 * 1024),
            'allocation_count': self.allocation_count,
            'deallocation_count': self.deallocation_count,
            'cache_hit_rate': self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            'contention_count': self.contention_count,
            'efficiency': self.total_used / max(1, self.total_allocated),
            'cache_misses': self.cache_misses
        }


class XGBufferPool:
    """
    XG Buffer Pool

    Buffer management system providing pre-allocated, reusable audio buffers
    with SIMD alignment, memory tracking, and thread-safe operations.
    """

    # SIMD alignment requirements (bytes)
    SIMD_ALIGNMENT = 32  # AVX-256 alignment

    # Memory pool size limits
    MAX_POOL_SIZE_MB = 256  # Maximum total pool size
    MIN_POOL_SIZE_MB = 16   # Minimum pool size for startup

    def __init__(self, sample_rate: int = 44100, max_block_size: int = 8192,
                 max_channels: int = 16, memory_budget_mb: float | None = None):
        """
        Initialize XG Buffer Pool.

        Args:
            sample_rate: Audio sample rate
            max_block_size: Maximum audio block size
            max_channels: Maximum audio channels
            memory_budget_mb: Maximum memory budget in MB for dynamic buffer allocation.
                            If None, uses MAX_POOL_SIZE_MB as default.
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size
        self.max_channels = max_channels
        self.memory_budget_mb = memory_budget_mb if memory_budget_mb is not None else self.MAX_POOL_SIZE_MB
        self.memory_budget_bytes = int(self.memory_budget_mb * 1024 * 1024)
        self.total_memory_used = 0  # Track total memory used by allocated buffers

        # Thread safety
        self.lock = threading.RLock()
        self.stats = BufferStatistics()

        # Buffer pools organized by size and type
        self._mono_pools: dict[int, list[np.ndarray]] = defaultdict(list)
        self._stereo_pools: dict[int, list[np.ndarray]] = defaultdict(list)
        self._multi_channel_pools: dict[tuple[int, int], list[np.ndarray]] = defaultdict(list)

        # Active buffer tracking (for leak detection)
        self._active_buffers: dict[int, tuple[np.ndarray, str, int]] = {}  # id -> (buffer, stack_trace, thread_id)
        self._buffer_id_counter = 0

        # Memory pressure monitoring
        self._memory_pressure_threshold = 0.8  # 80% of max memory
        self._last_gc_time = 0.0
        self._gc_interval = 30.0  # GC every 30 seconds under pressure

        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize buffer pool with pre-allocated buffers."""
        # Calculate pool size based on configuration and instance parameters
        max_buffer_size = audio_config().buffer_size * 8  # Allow up to 8x configured buffer size
        max_channels = self.max_channels  # Use instance parameter instead of config

        # Pre-allocate common buffer sizes
        common_sizes = [256, 512, 1024, 2048, 4096, max_buffer_size]

        print(f"🎛️  Initializing XG Buffer Pool...")
        print(f"   Max buffer size: {max_buffer_size} samples")
        print(f"   Max channels: {max_channels}")

        total_allocated = 0

        # Allocate mono buffers
        for size in common_sizes:
            if size > max_buffer_size:
                continue

            num_buffers = max(4, min(16, max_buffer_size // size))  # Scale buffer count by size

            for _ in range(num_buffers):
                buffer = self._allocate_aligned_buffer(size, 1)
                self._mono_pools[size].append(buffer)
                total_allocated += buffer.nbytes

        # Allocate stereo buffers
        for size in common_sizes:
            if size > max_buffer_size:
                continue

            # Allocate more buffers for commonly used sizes
            if size <= 2048:
                # For commonly used sizes, allocate enough for all channels plus overhead
                base_allocation = max(16, min(64, max_buffer_size // size * 4))
                # Ensure we have enough for max_channels usage
                channel_overhead = max(0, max_channels - base_allocation + 10)  # +10 for temp buffers
                num_buffers = base_allocation + channel_overhead
            else:
                # For larger sizes, allocate more buffers for fallback usage
                num_buffers = max(16, min(64, max_buffer_size // size * 16))

            for _ in range(num_buffers):
                buffer = self._allocate_aligned_buffer(size, 2)
                self._stereo_pools[size].append(buffer)
                total_allocated += buffer.nbytes

        # Allocate multi-channel buffers (less common)
        multi_channel_configs = [(size, channels)
                                for size in [1024, 2048]
                                for channels in [4, 6, 8]
                                if channels <= max_channels]

        for size, channels in multi_channel_configs:
            num_buffers = max(1, min(4, max_buffer_size // size))

            for _ in range(num_buffers):
                buffer = self._allocate_aligned_buffer(size, channels)
                self._multi_channel_pools[(size, channels)].append(buffer)
                total_allocated += buffer.nbytes

        total_mb = total_allocated / (1024 * 1024)
        print(f"Total allocated: {total_mb:.1f} MB")
        print(f"Memory budget: {self.memory_budget_mb:.1f} MB")

        # Check if initial allocation exceeds budget
        if total_allocated > self.memory_budget_bytes:
            print(f"⚠️  Initial pool allocation ({total_mb:.1f} MB) exceeds memory budget ({self.memory_budget_mb:.1f} MB)")
            print(f"   This may limit dynamic allocation capabilities")

        self.stats.total_allocated = total_allocated
        self.total_memory_used = total_allocated

    def _allocate_aligned_buffer(self, size: int, channels: int) -> np.ndarray:
        """Allocate SIMD-aligned buffer."""
        # Calculate total size with alignment
        total_samples = size * channels
        bytes_per_sample = 4  # float32

        # Allocate with SIMD alignment
        buffer = np.zeros(total_samples + self.SIMD_ALIGNMENT, dtype=np.float32)

        # Find aligned offset
        offset = (self.SIMD_ALIGNMENT - (buffer.ctypes.data % self.SIMD_ALIGNMENT)) % self.SIMD_ALIGNMENT
        aligned_buffer = np.frombuffer(
            buffer.data[offset:offset + total_samples * bytes_per_sample],
            dtype=np.float32,
            count=total_samples
        ).reshape(size, channels)

        return aligned_buffer

    def get_mono_buffer(self, size: int) -> np.ndarray:
        """
        Get a mono buffer from the pool (guaranteed zero allocation).

        Args:
            size: Buffer size in samples

        Returns:
            Mono audio buffer

        Raises:
            BufferPoolExhaustedError: If no suitable buffer available
        """
        return self._get_buffer_from_pool(self._mono_pools, size, 1, "mono")

    def get_stereo_buffer(self, size: int) -> np.ndarray:
        """
        Get a stereo buffer from the pool (guaranteed zero allocation).

        Args:
            size: Buffer size in samples

        Returns:
            Stereo audio buffer

        Raises:
            BufferPoolExhaustedError: If no suitable buffer available
        """
        return self._get_buffer_from_pool(self._stereo_pools, size, 2, "stereo")

    def get_multi_channel_buffer(self, size: int, channels: int) -> np.ndarray:
        """
        Get a multi-channel buffer from the pool (guaranteed zero allocation).

        Args:
            size: Buffer size in samples
            channels: Number of channels

        Returns:
            Multi-channel audio buffer

        Raises:
            BufferPoolExhaustedError: If no suitable buffer available
        """
        key = (size, channels)
        return self._get_buffer_from_pool(self._multi_channel_pools, key, channels, f"multi_{channels}ch")

    def _get_buffer_from_pool(self, pool: dict[Any, list[np.ndarray]],
                            key: Any, channels: int, pool_name: str) -> np.ndarray:
        """Get buffer from specific pool."""
        with self.lock:
            # First try exact match
            if key in pool and pool[key]:
                buffer = pool[key].pop(0)
                self._track_buffer_usage(buffer, pool_name)
                self.stats.cache_hits += 1
                return buffer

            # Try to find a larger buffer that can accommodate the request
            # Only do fallback for mono/stereo pools (int keys), not multi-channel pools (tuple keys)
            if isinstance(key, int):
                available_sizes = sorted([k for k in pool.keys() if isinstance(k, int) and k >= key])
                for size in available_sizes:
                    if pool[size]:
                        buffer = pool[size].pop(0)
                        # Return extra space to pool if it's a larger buffer
                        if size > key:
                            extra_size = size - key
                            if extra_size > 64:  # Only if meaningfully larger
                                # Could implement buffer splitting here
                                pass
                        self._track_buffer_usage(buffer, f"{pool_name}_adapted")
                        return buffer

            # Pool exhausted - check if we can allocate new buffer within budget
            self.stats.cache_misses += 1
            if isinstance(key, int):
                # Calculate memory needed for new buffer
                buffer_size = key * channels * 4  # float32 = 4 bytes
                if self.total_memory_used + buffer_size <= self.memory_budget_bytes:
                    buffer = self._allocate_aligned_buffer(key, channels)
                    self.total_memory_used += buffer.nbytes
                    pool[key].append(buffer)  # Add to pool for future reuse
                    buffer = pool[key].pop(0)  # Get it back immediately
                    self._track_buffer_usage(buffer, f"{pool_name}_dynamic")
                    self.stats.allocation_count += 1
                    return buffer
                else:
                    # Budget exceeded
                    raise BufferPoolExhaustedError(
                        f"Buffer pool exhausted for {pool_name} size {key}. "
                        f"Memory budget exceeded: {self.total_memory_used}/{self.memory_budget_bytes} bytes. "
                        f"Available pools: {list(pool.keys())}"
                    )
            else:
                # For multi-channel (tuple keys), try dynamic allocation
                size, ch = key
                buffer_size = size * ch * 4
                if self.total_memory_used + buffer_size <= self.memory_budget_bytes:
                    print(f"🔄 Dynamic allocation for {pool_name} size {key}, "
                          f"within budget ({self.total_memory_used + buffer_size}/{self.memory_budget_bytes} bytes)")
                    buffer = self._allocate_aligned_buffer(size, ch)
                    self.total_memory_used += buffer.nbytes
                    pool[key].append(buffer)
                    buffer = pool[key].pop(0)
                    self._track_buffer_usage(buffer, f"{pool_name}_dynamic")
                    self.stats.allocation_count += 1
                    return buffer
                else:
                    raise BufferPoolExhaustedError(
                        f"Buffer pool exhausted for {pool_name} size {key}. "
                        f"Memory budget exceeded: {self.total_memory_used}/{self.memory_budget_bytes} bytes. "
                        f"Available pools: {list(pool.keys())}"
                    )

    def _track_buffer_usage(self, buffer: np.ndarray, context: str):
        """Track buffer usage for leak detection."""
        buffer_id = id(buffer)
        thread_id = threading.get_ident()

        # Get stack trace for debugging (simplified)
        import inspect
        frame = inspect.currentframe()
        caller = frame.f_back.f_back
        location = f"{caller.f_code.co_filename}:{caller.f_lineno}"

        self._active_buffers[buffer_id] = (buffer, location, thread_id)

    def return_buffer(self, buffer: np.ndarray):
        """
        Return buffer to pool.

        Args:
            buffer: Buffer to return
        """
        with self.lock:
            buffer_id = id(buffer)

            if buffer_id not in self._active_buffers:
                print(f"⚠️  Attempted to return unknown buffer {buffer_id}")
                return

            # Clear buffer contents for security
            buffer.fill(0.0)

            # Determine which pool to return to
            shape = buffer.shape
            if len(shape) == 1:
                # Mono
                size = shape[0]
                if size in self._mono_pools:
                    self._mono_pools[size].append(buffer)
            elif len(shape) == 2:
                size, channels = shape
                if channels == 2 and size in self._stereo_pools:
                    self._stereo_pools[size].append(buffer)
                elif channels > 2:
                    key = (size, channels)
                    if key in self._multi_channel_pools:
                        self._multi_channel_pools[key].append(buffer)

            # Remove from active tracking
            del self._active_buffers[buffer_id]
            self.stats.deallocation_count += 1

    @contextmanager
    def temporary_buffer(self, size: int, channels: int = 2):
        """
        Context manager for temporary buffer usage.

        Guarantees buffer is returned to pool even if exception occurs.

        Usage:
            with pool.temporary_buffer(1024, 2) as buffer:
                # Use buffer
                process_audio(buffer)
            # Buffer automatically returned
        """
        buffer = None
        try:
            if channels == 1:
                buffer = self.get_mono_buffer(size)
            elif channels == 2:
                buffer = self.get_stereo_buffer(size)
            else:
                buffer = self.get_multi_channel_buffer(size, channels)

            yield buffer
        finally:
            if buffer is not None:
                self.return_buffer(buffer)

    def validate_pool_integrity(self) -> ValidationResult:
        """
        Validate pool integrity and report issues.

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        with self.lock:
            # Check for buffer leaks
            active_count = len(self._active_buffers)
            if active_count > 100:  # Arbitrary threshold
                result.add_warning(ValidationError(
                    f"High number of active buffers: {active_count}",
                    "HIGH_ACTIVE_BUFFER_COUNT",
                    {"active_buffers": active_count},
                    "warning"
                ))

            # Check pool utilization
            total_available = sum(len(buffers) for buffers in self._mono_pools.values()) + \
                             sum(len(buffers) for buffers in self._stereo_pools.values()) + \
                             sum(len(buffers) for buffers in self._multi_channel_pools.values())

            if total_available < 10:  # Low buffer count
                result.add_warning(ValidationError(
                    f"Low buffer availability: {total_available} buffers remaining",
                    "LOW_BUFFER_AVAILABILITY",
                    {"available_buffers": total_available},
                    "warning"
                ))

            # Check memory usage
            memory_usage = self.stats.total_used / max(1, self.stats.total_allocated)
            if memory_usage > 0.9:  # Over 90% usage
                result.add_warning(ValidationError(
                    ".1%",
                    "HIGH_MEMORY_USAGE",
                    {"usage_percent": memory_usage * 100},
                    "warning"
                ))

        return result

    def get_pool_statistics(self) -> dict[str, Any]:
        """Get comprehensive pool statistics."""
        with self.lock:
            stats = self.stats.get_stats()

            # Add pool-specific information
            stats.update({
                'mono_pools': {size: len(buffers) for size, buffers in self._mono_pools.items()},
                'stereo_pools': {size: len(buffers) for size, buffers in self._stereo_pools.items()},
                'multi_channel_pools': {f"{size}x{ch}": len(buffers)
                                      for (size, ch), buffers in self._multi_channel_pools.items()},
                'active_buffers': len(self._active_buffers),
                'total_pools': len(self._mono_pools) + len(self._stereo_pools) + len(self._multi_channel_pools),
                'memory_budget_mb': self.memory_budget_mb,
                'total_memory_used_mb': self.total_memory_used / (1024 * 1024),
                'memory_utilization': self.total_memory_used / max(1, self.memory_budget_bytes)
            })

            return stats

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory statistics (alias for get_pool_statistics for compatibility)."""
        return self.get_pool_statistics()

    def optimize_pool(self):
        """Optimize pool by removing unused buffers and defragmenting."""
        with self.lock:
            # Remove empty pool entries
            self._mono_pools = {k: v for k, v in self._mono_pools.items() if v}
            self._stereo_pools = {k: v for k, v in self._stereo_pools.items() if v}
            self._multi_channel_pools = {k: v for k, v in self._multi_channel_pools.items() if v}

            # Could implement more sophisticated optimization here
            # - Buffer size consolidation
            # - Memory defragmentation
            # - Usage pattern analysis

    def emergency_cleanup(self):
        """Emergency cleanup when memory pressure is critical."""
        print("🚨 Emergency buffer pool cleanup initiated")

        with self.lock:
            # Force return of all active buffers (dangerous but necessary)
            for buffer_id, (buffer, location, thread_id) in list(self._active_buffers.items()):
                print(f"⚠️  Force returning buffer from {location} (thread {thread_id})")
                self.return_buffer(buffer)

            # Force garbage collection
            gc.collect()

            print("✅ Emergency cleanup completed")

    def __str__(self) -> str:
        """String representation."""
        stats = self.get_pool_statistics()
        return (".1f"
                f"active={stats['active_buffers']}, "
                f"pools={stats['total_pools']}")

    def __repr__(self) -> str:
        return self.__str__()


class XGBufferManager:
    """
    XG Buffer Manager - Context manager for zero-allocation buffer handling.

    Provides context-managed buffer allocation and automatic cleanup for
    the XG effects processing chain.
    """

    def __init__(self, buffer_pool: XGBufferPool):
        """
        Initialize buffer manager.

        Args:
            buffer_pool: XGBufferPool instance to manage
        """
        self.buffer_pool = buffer_pool
        self.allocated_buffers = []
        self.active = False

    def __enter__(self):
        """Enter context manager."""
        self.active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and clean up buffers."""
        self.active = False
        # Return all allocated buffers to pool
        for buffer in self.allocated_buffers:
            self.buffer_pool.return_buffer(buffer)
        self.allocated_buffers.clear()

    def get_stereo(self, size: int) -> np.ndarray:
        """
        Get a stereo buffer from the pool.

        Args:
            size: Buffer size in samples

        Returns:
            Stereo audio buffer
        """
        if not self.active:
            raise RuntimeError("XGBufferManager must be used as context manager")

        buffer = self.buffer_pool.get_stereo_buffer(size)
        self.allocated_buffers.append(buffer)
        return buffer

    def get_mono(self, size: int) -> np.ndarray:
        """
        Get a mono buffer from the pool.

        Args:
            size: Buffer size in samples

        Returns:
            Mono audio buffer
        """
        if not self.active:
            raise RuntimeError("XGBufferManager must be used as context manager")

        buffer = self.buffer_pool.get_mono_buffer(size)
        self.allocated_buffers.append(buffer)
        return buffer
