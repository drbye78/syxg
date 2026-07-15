"""Tests for the XGBufferPool, XGBufferManager, and BufferPoolExhaustedError."""

from __future__ import annotations

import numpy as np
import pytest

from synth.primitives.buffer_pool import (
    XGBufferPool,
    XGBufferManager,
    BufferPoolExhaustedError,
)
from synth.primitives.validation import ValidationResult


# ---------------------------------------------------------------------------
# Pool Lifecycle & Buffer Return
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPoolLifecycle:
    """Test basic pool creation and buffer get/return."""

    def test_init(self):
        """Create XGBufferPool with small memory_budget_mb=16, verify it initializes."""
        pool = XGBufferPool(memory_budget_mb=16)
        assert pool.sample_rate == 44100
        assert pool.max_block_size == 8192
        assert pool.memory_budget_mb == 16
        assert pool.memory_budget_bytes == 16 * 1024 * 1024
        # The pool should have pre-allocated buffers
        stats = pool.get_pool_statistics()
        assert stats["mono_pools"]  # at least one mono pool entry
        assert stats["stereo_pools"]
        assert stats["total_pools"] > 0

    def test_get_mono_buffer(self):
        """Get mono buffer of size 256, verify shape (256,), dtype float32, all zeros."""
        pool = XGBufferPool(memory_budget_mb=64)
        buf = pool.get_mono_buffer(256)
        assert buf.shape == (256,), f"Expected (256,), got {buf.shape}"
        assert buf.dtype == np.float32
        assert np.all(buf == 0.0)

    def test_get_stereo_buffer(self):
        """Get stereo buffer of size 256, verify shape (256, 2), dtype float32."""
        pool = XGBufferPool(memory_budget_mb=64)
        buf = pool.get_stereo_buffer(256)
        assert buf.shape == (256, 2), f"Expected (256, 2), got {buf.shape}"
        assert buf.dtype == np.float32
        assert np.all(buf == 0.0)

    def test_return_buffer_zeros(self):
        """Get a buffer, fill with 1.0, return it, get another — verify it's zeroed."""
        pool = XGBufferPool(memory_budget_mb=64)
        buf = pool.get_mono_buffer(256)
        buf.fill(1.0)
        assert np.all(buf == 1.0)
        pool.return_buffer(buf)
        # Getting a fresh buffer (same or different) must be zeroed
        buf2 = pool.get_mono_buffer(256)
        assert np.all(buf2 == 0.0)

    def test_get_multi_channel_buffer(self):
        """Get 4ch buffer of size 1024, verify shape (1024, 4)."""
        pool = XGBufferPool(memory_budget_mb=64)
        buf = pool.get_multi_channel_buffer(1024, 4)
        assert buf.shape == (1024, 4), f"Expected (1024, 4), got {buf.shape}"
        assert buf.dtype == np.float32
        assert np.all(buf == 0.0)


# ---------------------------------------------------------------------------
# SIMD Alignment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSIMDAlignment:
    """Verify SIMD alignment on allocated buffers."""

    def test_simd_alignment(self):
        """Get any buffer, verify data address is SIMD_ALIGNMENT-aligned."""
        pool = XGBufferPool(memory_budget_mb=64)
        buf = pool.get_mono_buffer(256)
        assert buf.ctypes.data % XGBufferPool.SIMD_ALIGNMENT == 0, (
            f"Buffer address {buf.ctypes.data:#x} not aligned to "
            f"{XGBufferPool.SIMD_ALIGNMENT} bytes"
        )

    def test_alignment_mono_and_stereo(self):
        """Check alignment on both mono and stereo buffers."""
        pool = XGBufferPool(memory_budget_mb=64)
        align = XGBufferPool.SIMD_ALIGNMENT
        mono = pool.get_mono_buffer(512)
        stereo = pool.get_stereo_buffer(512)
        assert mono.ctypes.data % align == 0
        assert stereo.ctypes.data % align == 0


# ---------------------------------------------------------------------------
# Pool Exhaustion & Fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPoolExhaustion:
    """Test pool exhaustion errors and fallback allocation."""

    def test_pool_exhaustion_raises_error(self):
        """
        Create pool with tiny memory budget. Drain all mono buffers of all
        sizes (exact + fallback) until the pool can no longer satisfy a
        request, then verify BufferPoolExhaustedError.
        """
        pool = XGBufferPool(memory_budget_mb=1, max_block_size=256)
        grabbed: list[np.ndarray] = []
        with pytest.raises(BufferPoolExhaustedError) as excinfo:
            while True:
                grabbed.append(pool.get_mono_buffer(256))
        assert "Buffer pool exhausted" in str(excinfo.value)
        # Return buffers so the pool isn't left in a weird state
        for b in grabbed:
            pool.return_buffer(b)

    def test_get_buffer_fallback_larger(self):
        """
        After clearing the exact-size pool entry for mono/256, getting a mono
        256 buffer should fall back to a larger available buffer.
        """
        pool = XGBufferPool(memory_budget_mb=64)
        # Remove all 256-sized mono buffers from the pool (internal access
        # is acceptable here because we are testing the fallback path)
        count = len(pool._mono_pools[256])
        pool._mono_pools[256].clear()
        # Fallback should grab a larger buffer (e.g. 512, 1024, …)
        buf = pool.get_mono_buffer(256)
        assert buf.shape[0] >= 256
        assert buf.dtype == np.float32
        # Return it so the larger buffer goes back to its original pool
        pool.return_buffer(buf)
        # Restore original buffers so other tests aren't affected
        # (not strictly necessary since this pool is local to the test)


# ---------------------------------------------------------------------------
# Temporary Buffer Context Manager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTemporaryBuffer:
    """Test the temporary_buffer context manager."""

    def test_temporary_buffer(self):
        """Use temporary_buffer(256, 1) and verify buffer shape."""
        pool = XGBufferPool(memory_budget_mb=64)
        with pool.temporary_buffer(256, 1) as buf:
            assert buf.shape == (256,)
            assert buf.dtype == np.float32
            assert np.all(buf == 0.0)

    def test_temporary_buffer_returns_on_exception(self):
        """
        Use temporary_buffer inside try/except, raise an exception, verify
        the buffer is returned (can get another buffer successfully after).
        """
        pool = XGBufferPool(memory_budget_mb=64)
        try:
            with pool.temporary_buffer(256, 1) as buf:
                buf[0] = 1.0
                raise ValueError("simulated error")
        except ValueError:
            pass
        # The buffer should have been returned; verify by getting a new one
        buf2 = pool.get_mono_buffer(256)
        assert buf2.shape == (256,)
        assert np.all(buf2 == 0.0)

    def test_temporary_buffer_stereo(self):
        """temporary_buffer(512, 2) returns shape (512, 2)."""
        pool = XGBufferPool(memory_budget_mb=64)
        with pool.temporary_buffer(512, 2) as buf:
            assert buf.shape == (512, 2)
            assert buf.dtype == np.float32


# ---------------------------------------------------------------------------
# Pool Statistics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPoolStatistics:
    """Test get_pool_statistics and active buffer tracking."""

    def test_pool_statistics(self):
        """get_pool_statistics() returns dict with expected keys."""
        pool = XGBufferPool(memory_budget_mb=64)
        stats = pool.get_pool_statistics()
        expected_keys = {
            "mono_pools",
            "stereo_pools",
            "multi_channel_pools",
            "active_buffers",
            "memory_budget_mb",
            "total_memory_used_mb",
            "memory_utilization",
            "total_pools",
            "total_allocated_mb",
            "total_used_mb",
            "peak_usage_mb",
            "allocation_count",
            "deallocation_count",
            "cache_hit_rate",
            "cache_misses",
            "contention_count",
            "efficiency",
        }
        assert expected_keys.issubset(stats.keys()), (
            f"Missing keys: {expected_keys - stats.keys()}"
        )
        # Sanity-check types
        assert isinstance(stats["mono_pools"], dict)
        assert isinstance(stats["stereo_pools"], dict)
        assert isinstance(stats["active_buffers"], int)
        assert isinstance(stats["memory_budget_mb"], float | int)
        assert stats["active_buffers"] == 0

    def test_active_buffer_tracking(self):
        """Get and return a buffer; verify active_buffers count changes."""
        pool = XGBufferPool(memory_budget_mb=64)
        initial = pool.get_pool_statistics()["active_buffers"]

        buf = pool.get_mono_buffer(256)
        stats1 = pool.get_pool_statistics()
        assert stats1["active_buffers"] == initial + 1

        pool.return_buffer(buf)
        stats2 = pool.get_pool_statistics()
        assert stats2["active_buffers"] == initial


# ---------------------------------------------------------------------------
# XGBufferManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestXGBufferManager:
    """Test the XGBufferManager context manager."""

    def test_buffer_manager_context(self):
        """Create XGBufferManager, use as context manager, get_stereo(256)."""
        pool = XGBufferPool(memory_budget_mb=64)
        manager = XGBufferManager(pool)
        with manager:
            buf = manager.get_stereo(256)
            assert buf.shape == (256, 2)
            assert buf.dtype == np.float32

    def test_buffer_manager_raises_outside_context(self):
        """Calling get_stereo outside 'with' raises RuntimeError."""
        pool = XGBufferPool(memory_budget_mb=64)
        manager = XGBufferManager(pool)
        with pytest.raises(RuntimeError, match="context manager"):
            manager.get_stereo(256)

    def test_buffer_manager_returns_buffers(self):
        """Acquire 3 buffers inside context, verify they're returned on exit."""
        pool = XGBufferPool(memory_budget_mb=64)
        manager = XGBufferManager(pool)
        initial_active = pool.get_pool_statistics()["active_buffers"]
        with manager:
            manager.get_stereo(256)
            manager.get_stereo(256)
            manager.get_stereo(256)
            mid = pool.get_pool_statistics()["active_buffers"]
            assert mid == initial_active + 3
        after = pool.get_pool_statistics()["active_buffers"]
        assert after == initial_active

    def test_validate_pool_integrity(self):
        """validate_pool_integrity() returns ValidationResult."""
        pool = XGBufferPool(memory_budget_mb=64)
        result = pool.validate_pool_integrity()
        assert isinstance(result, ValidationResult)
        # A fresh pool should have no errors
        assert result.is_valid()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEdgeCases:
    """Edge-case scenarios for the buffer pool."""

    def test_get_buffer_max_size(self):
        """Get mono buffer with size=max_block_size, verify it works."""
        pool = XGBufferPool(memory_budget_mb=64)
        # The largest pre-allocated size is audio_config().buffer_size * 8,
        # which defaults to 8192.
        buf = pool.get_mono_buffer(8192)
        assert buf.shape == (8192,)
        assert buf.dtype == np.float32

    def test_multiple_gets_returns(self):
        """Get several buffers, return them, get them again — recycling works."""
        pool = XGBufferPool(memory_budget_mb=64)
        bufs = [pool.get_mono_buffer(256) for _ in range(3)]
        for b in bufs:
            b.fill(0.5)
            pool.return_buffer(b)
        # Get again — should all be zeroed
        recycled = [pool.get_mono_buffer(256) for _ in range(3)]
        for b in recycled:
            assert np.all(b == 0.0)
        # Cleanup
        for b in recycled:
            pool.return_buffer(b)
