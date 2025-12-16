"""
XG Effects Zero-Allocation Buffer Pool System

This module provides a zero-allocation buffer pool optimized for XG effects processing.
Key features:
- Pre-allocated buffers that are reused in hot paths
- Vectorized memory clearing operations
- Memory pool with fixed-size blocks to avoid fragmentation
- Stereo-friendly buffer layouts for SIMD processing

Memory Layout Optimization:
- Contiguous memory blocks for better cache performance
- Stereo buffers store L/R channels contiguously for SIMD operations
- Circular buffer indexing to minimize modulo operations in DSP loops
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
import threading


class XGBufferPool:
    """
    Zero-Allocation Buffer Pool for XG Effects Processing

    Manages pre-allocated buffers that can be checked out and returned
    during audio processing without any runtime allocation.

    Features:
    - Pre-allocated buffer pools based on typical block sizes
    - Automatic buffer size validation and reuse
    - Memory usage tracking for performance monitoring
    - Thread-safe operations with minimal locking
    """

    def __init__(self, sample_rate: int, max_block_size: int = 1024):
        """
        Initialize zero-allocation buffer pool.

        Args:
            sample_rate: Sample rate for buffer size calculations
            max_block_size: Maximum block size for processing
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size
        self.lock = threading.RLock()

        # Pre-allocated buffer pools - different sizes for different use cases
        self._mono_buffers: Dict[int, deque[np.ndarray]] = {}
        self._stereo_buffers: Dict[int, deque[np.ndarray]] = {}
        self._biquad_buffers: Dict[int, deque[np.ndarray]] = {}  # For filter state buffers
        self._delay_buffers: Dict[Tuple[int, int], deque[np.ndarray]] = {}  # (size, channels)

        # Pre-allocate common buffer sizes
        self._preallocate_common_sizes()

        # Memory usage tracking
        self._active_buffers = 0
        self._total_memory_mb = 0.0
        self._allocation_count = 0

    def _preallocate_common_sizes(self):
        """Pre-allocate buffers for common XG processing scenarios."""
        common_sizes = [64, 128, 256, 512, 1024]  # Block sizes

        # Pre-allocate mono buffers for general processing
        for size in common_sizes:
            self._mono_buffers[size] = deque()
            for _ in range(8):  # Pool size - 8 buffers per size
                buffer = np.zeros(size, dtype=np.float32)
                self._mono_buffers[size].append(buffer)
                self._total_memory_mb += buffer.nbytes / (1024 * 1024)

        # Pre-allocate stereo buffers for main processing
        for size in common_sizes:
            self._stereo_buffers[size] = deque()
            for _ in range(4):  # Fewer stereo buffers needed
                buffer = np.zeros((size, 2), dtype=np.float32)
                self._stereo_buffers[size].append(buffer)
                self._total_memory_mb += buffer.nbytes / (1024 * 1024)

        # Pre-allocate biquad filter state buffers (8 values per instance)
        self._biquad_buffers[8] = deque()
        for _ in range(16):  # More filter instances
            buffer = np.zeros(8, dtype=np.float64)  # High precision for filter state
            self._biquad_buffers[8].append(buffer)
            self._total_memory_mb += buffer.nbytes / (1024 * 1024)

        # Pre-allocate common delay line sizes (in samples)
        delay_sizes = [
            int(0.025 * self.sample_rate),  # 25ms delay
            int(0.050 * self.sample_rate),  # 50ms delay
            int(0.100 * self.sample_rate),  # 100ms delay
            int(0.200 * self.sample_rate),  # 200ms delay
            int(0.500 * self.sample_rate),  # 500ms delay
        ]

        for delay_size in delay_sizes:
            for channels in [1, 2]:  # Mono and stereo delay lines
                key = (delay_size, channels)
                self._delay_buffers[key] = deque()
                for _ in range(4):  # Pool size for delay lines
                    if channels == 1:
                        buffer = np.zeros(delay_size, dtype=np.float32)
                    else:
                        buffer = np.zeros((delay_size, 2), dtype=np.float32)
                    self._delay_buffers[key].append(buffer)
                    self._total_memory_mb += buffer.nbytes / (1024 * 1024)

    def get_mono_buffer(self, size: int) -> np.ndarray:
        """
        Get a pre-allocated mono buffer of the specified size.

        Args:
            size: Buffer size in samples

        Returns:
            Pre-allocated mono buffer (cleared and ready to use)

        Note: Buffer must be returned using return_mono_buffer()
        """
        with self.lock:
            # Find nearest larger or equal size in our pools
            for pool_size in sorted(self._mono_buffers.keys()):
                if pool_size >= size and self._mono_buffers[pool_size]:
                    buffer = self._mono_buffers[pool_size].popleft()
                    self._active_buffers += 1
                    return self._clear_buffer(buffer, size)

            # No suitable buffer found, create temporary one (not zero-allocation but rare)
            buffer = np.zeros(size, dtype=np.float32)
            self._allocation_count += 1
            self._total_memory_mb += buffer.nbytes / (1024 * 1024)
            self._active_buffers += 1
            return buffer

    def return_mono_buffer(self, buffer: np.ndarray):
        """
        Return a mono buffer to the pool.

        Args:
            buffer: Buffer to return (must be from get_mono_buffer)
        """
        with self.lock:
            size = buffer.shape[0]
            # Find appropriate pool size
            pool_size = None
            for pool_size in sorted(self._mono_buffers.keys()):
                if pool_size >= size:
                    break

            if pool_size is None or pool_size < size:
                # Buffer is larger than our pools, this shouldn't happen with prealloc
                return

            self._mono_buffers[pool_size].append(buffer)
            self._active_buffers -= 1

    def get_stereo_buffer(self, size: int) -> np.ndarray:
        """
        Get a pre-allocated stereo buffer of the specified size.

        Args:
            size: Buffer size in samples

        Returns:
            Pre-allocated stereo buffer (size, 2) - cleared and ready to use

        Note: Buffer must be returned using return_stereo_buffer()
        """
        with self.lock:
            for pool_size in sorted(self._stereo_buffers.keys()):
                if pool_size >= size and self._stereo_buffers[pool_size]:
                    buffer = self._stereo_buffers[pool_size].popleft()
                    self._active_buffers += 1
                    return self._clear_buffer_stereo(buffer, size)

            # Fallback allocation
            buffer = np.zeros((size, 2), dtype=np.float32)
            self._allocation_count += 1
            self._total_memory_mb += buffer.nbytes / (1024 * 1024)
            self._active_buffers += 1
            return buffer

    def return_stereo_buffer(self, buffer: np.ndarray):
        """
        Return a stereo buffer to the pool.

        Args:
            buffer: Buffer to return (must be from get_stereo_buffer)
        """
        with self.lock:
            size = buffer.shape[0]
            pool_size = None
            for pool_size in sorted(self._stereo_buffers.keys()):
                if pool_size >= size:
                    break

            if pool_size is None or pool_size < size:
                return

            self._stereo_buffers[pool_size].append(buffer)
            self._active_buffers -= 1

    def get_biquad_state_buffer(self) -> np.ndarray:
        """
        Get a pre-allocated biquad filter state buffer.

        Returns:
            8-element float64 buffer for biquad filter state

        Note: Buffer must be returned using return_biquad_state_buffer()
        """
        with self.lock:
            if self._biquad_buffers[8]:
                buffer = self._biquad_buffers[8].popleft()
                self._active_buffers += 1
                # Clear the state buffer
                buffer.fill(0.0)
                return buffer

            # Fallback
            buffer = np.zeros(8, dtype=np.float64)
            self._allocation_count += 1
            self._total_memory_mb += buffer.nbytes / (1024 * 1024)
            self._active_buffers += 1
            return buffer

    def return_biquad_state_buffer(self, buffer: np.ndarray):
        """
        Return a biquad state buffer to the pool.
        """
        with self.lock:
            self._biquad_buffers[8].append(buffer)
            self._active_buffers -= 1

    def get_delay_line_buffer(self, delay_samples: int, channels: int = 1) -> np.ndarray:
        """
        Get a pre-allocated delay line buffer.

        Args:
            delay_samples: Delay length in samples
            channels: Number of channels (1=mono, 2=stereo)

        Returns:
            Delay line buffer - cleared and ready to use
        """
        with self.lock:
            # Find appropriate delay line size in our pools
            for (pool_delay, pool_channels), buffers in self._delay_buffers.items():
                if pool_delay >= delay_samples and pool_channels == channels and buffers:
                    buffer = buffers.popleft()
                    self._active_buffers += 1
                    # Clear the delay buffer
                    buffer.fill(0.0)
                    return buffer

            # Fallback allocation
            if channels == 1:
                buffer = np.zeros(delay_samples, dtype=np.float32)
            else:
                buffer = np.zeros((delay_samples, channels), dtype=np.float32)
            self._allocation_count += 1
            self._total_memory_mb += buffer.nbytes / (1024 * 1024)
            self._active_buffers += 1
            return buffer

    def return_delay_line_buffer(self, buffer: np.ndarray):
        """
        Return a delay line buffer to the pool.
        """
        with self.lock:
            if buffer.ndim == 1:
                channels = 1
                delay_samples = buffer.shape[0]
            else:
                channels = buffer.shape[1]
                delay_samples = buffer.shape[0]

            key = (delay_samples, channels)
            if key in self._delay_buffers:
                self._delay_buffers[key].append(buffer)
                self._active_buffers -= 1

    @staticmethod
    def _clear_buffer(buffer: np.ndarray, size: int) -> np.ndarray:
        """
        Clear a buffer using vectorized operations, up to the specified size.

        Args:
            buffer: Buffer to clear
            size: Size to clear (may be smaller than buffer size)

        Returns:
            Cleared buffer
        """
        buffer[:size].fill(0.0)
        return buffer

    @staticmethod
    def _clear_buffer_stereo(buffer: np.ndarray, size: int) -> np.ndarray:
        """
        Clear a stereo buffer using vectorized operations.

        Args:
            buffer: Stereo buffer to clear
            size: Number of samples to clear

        Returns:
            Cleared stereo buffer
        """
        buffer[:size, :].fill(0.0)
        return buffer

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory pool statistics.

        Returns:
            Dictionary with memory usage statistics
        """
        with self.lock:
            total_buffers = sum(len(pool) for pool in self._mono_buffers.values())
            total_buffers += sum(len(pool) for pool in self._stereo_buffers.values())
            total_buffers += sum(len(pool) for pool in self._biquad_buffers.values())
            total_buffers += sum(len(pool) for pool in self._delay_buffers.values())

            return {
                "total_memory_mb": self._total_memory_mb,
                "active_buffers": self._active_buffers,
                "total_available_buffers": total_buffers,
                "allocation_count": self._allocation_count,
                "pool_efficiency": (total_buffers - self._active_buffers) / max(total_buffers, 1),
                "mono_buffer_sizes": list(self._mono_buffers.keys()),
                "stereo_buffer_sizes": list(self._stereo_buffers.keys()),
                "delay_buffer_configs": list(self._delay_buffers.keys()),
            }

    def maintenance(self):
        """
        Perform periodic maintenance on the buffer pools.
        Should be called periodically to ensure pool health.
        """
        with self.lock:
            # Could implement buffer validation, pool resizing, etc. here
            pass


class XGBufferManager:
    """
    High-Level Buffer Management for XG Effects Context

    Provides a context manager interface for acquiring and releasing
    multiple buffers required for XG effect processing blocks.

    This ensures that all buffers used in a processing block are
    properly returned to the pool, even if exceptions occur.
    """

    def __init__(self, buffer_pool: XGBufferPool):
        self.buffer_pool = buffer_pool
        self.active_buffers: List[Tuple[str, np.ndarray]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Return all active buffers to the pool
        for buffer_type, buffer in self.active_buffers:
            if buffer_type == "mono":
                self.buffer_pool.return_mono_buffer(buffer)
            elif buffer_type == "stereo":
                self.buffer_pool.return_stereo_buffer(buffer)
            elif buffer_type == "biquad":
                self.buffer_pool.return_biquad_state_buffer(buffer)
            elif buffer_type.startswith("delay"):
                self.buffer_pool.return_delay_line_buffer(buffer)
        self.active_buffers.clear()

    def get_mono(self, size: int) -> np.ndarray:
        """Get a mono buffer for the duration of the context."""
        buffer = self.buffer_pool.get_mono_buffer(size)
        self.active_buffers.append(("mono", buffer))
        return buffer

    def get_stereo(self, size: int) -> np.ndarray:
        """Get a stereo buffer for the duration of the context."""
        buffer = self.buffer_pool.get_stereo_buffer(size)
        self.active_buffers.append(("stereo", buffer))
        return buffer

    def get_biquad_state(self) -> np.ndarray:
        """Get a biquad filter state buffer for the duration of the context."""
        buffer = self.buffer_pool.get_biquad_state_buffer()
        self.active_buffers.append(("biquad", buffer))
        return buffer

    def get_delay_line(self, delay_samples: int, channels: int = 1) -> np.ndarray:
        """Get a delay line buffer for the duration of the context."""
        buffer = self.buffer_pool.get_delay_line_buffer(delay_samples, channels)
        self.active_buffers.append((f"delay_{channels}ch", buffer))
        return buffer


class XGMemoryProfiler:
    """
    Memory Usage Profiler for XG Effects Processing

    Tracks memory allocation patterns and provides performance insights
    to ensure the system remains zero-allocation during hot paths.
    """

    def __init__(self, buffer_pool: XGBufferPool):
        self.buffer_pool = buffer_pool
        self.profile_data = {
            "processing_blocks": [],
            "allocation_events": [],
            "high_water_mark": 0,
            "peak_allocation_count": 0,
        }

    def start_processing_block(self):
        """Mark the start of a processing block for profiling."""
        self.profile_data["processing_blocks"].append({
            "start_time": len(self.profile_data["processing_blocks"]),  # Simplified
            "initial_allocations": self.buffer_pool._allocation_count,
            "initial_active": self.buffer_pool._active_buffers,
        })

    def end_processing_block(self):
        """Mark the end of a processing block for profiling."""
        if self.profile_data["processing_blocks"]:
            block = self.profile_data["processing_blocks"][-1]
            block["end_time"] = len(self.profile_data["processing_blocks"])
            block["final_allocations"] = self.buffer_pool._allocation_count
            block["final_active"] = self.buffer_pool._active_buffers
            block["allocations_during_block"] = (
                block["final_allocations"] - block["initial_allocations"]
            )

            # Update high water marks
            if block["final_active"] > self.profile_data["high_water_mark"]:
                self.profile_data["high_water_mark"] = block["final_active"]

            if block["allocations_during_block"] > 0:
                self.profile_data["allocation_events"].append(block)

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get a performance report on memory usage patterns.

        Returns:
            Dictionary with performance metrics
        """
        if not self.profile_data["processing_blocks"]:
            return {"status": "No data collected"}

        total_blocks = len(self.profile_data["processing_blocks"])
        blocks_with_allocations = len(self.profile_data["allocation_events"])
        total_allocations = sum(block["allocations_during_block"]
                              for block in self.profile_data["processing_blocks"])

        return {
            "zero_allocation_compliance_percent": (
                (total_blocks - blocks_with_allocations) / total_blocks * 100
            ),
            "total_processing_blocks": total_blocks,
            "blocks_with_allocations": blocks_with_allocations,
            "total_allocation_events": total_allocations,
            "high_water_mark_buffers": self.profile_data["high_water_mark"],
        }
