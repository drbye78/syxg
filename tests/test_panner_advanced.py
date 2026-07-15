"""
ADVANCED TESTS FOR ULTRA-FAST STEREO PANNER

Tests constant-power pan law, MIDI CC10 mapping, block processing,
stereo processing, reset behavior, and PannerPool lifecycle.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from synth.primitives.panner import PannerPool, UltraFastStereoPanner

# ---------------------------------------------------------------------------
# Constants & tolerances
# ---------------------------------------------------------------------------

GAIN_TOLERANCE = 0.02  # fast_math lookup-table quantisation ~0.1% plus truncation
POWER_RTOL = 0.005  # 0.5% for power conservation (identity is exact per table entry)
CENTER_EQ_TOL = 0.012  # cos/sin at same table index can differ by ~0.007 at π/4

BLOCK = 1024
SR = 44100


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def panner() -> UltraFastStereoPanner:
    return UltraFastStereoPanner(sample_rate=SR, block_size=BLOCK)


@pytest.fixture
def sine_tone() -> np.ndarray:
    """A 440 Hz sine tone at 44.1 kHz, 1024 samples, float32."""
    return np.sin(
        2 * np.pi * 440 * np.arange(BLOCK, dtype=np.float32) / SR
    ).astype(np.float32)


@pytest.fixture
def dc_block() -> np.ndarray:
    """Flat DC signal for precise RMS-based power measurements."""
    return np.full(1000, 0.5, dtype=np.float32)


# ===================================================================
# PAN LAW — CONSTANT POWER VERIFICATION
# ===================================================================


class TestPanLaw:
    """Verify the sinusoidal constant-power pan law."""

    def test_pan_center(self, panner: UltraFastStereoPanner) -> None:
        """Center pan (0.5): left ≈ right within fast_math tolerance."""
        panner.set_pan_normalized(0.5)
        left, right = panner.process(0.5)
        # Gains may differ slightly due to table quantisation
        assert abs(left - right) < CENTER_EQ_TOL, (
            f"Center pan L={left:.6f} ≠ R={right:.6f}"
        )
        # Both should be close to theoretical centre value (0.5 * √2/2 ≈ 0.3536)
        expected = 0.5 * math.cos(math.pi / 4)
        assert abs(left - expected) < GAIN_TOLERANCE, (
            f"Center left {left:.6f} not close to {expected:.6f}"
        )
        assert abs(right - expected) < GAIN_TOLERANCE, (
            f"Center right {right:.6f} not close to {expected:.6f}"
        )

    def test_pan_full_left(self, panner: UltraFastStereoPanner) -> None:
        """Full left pan (0.0): right ≈ 0, left ≈ input amplitude."""
        panner.set_pan_normalized(0.0)
        sample = 0.5
        left, right = panner.process(sample)
        assert abs(right) < 1e-6, f"Full left: right should be 0, got {right}"
        assert abs(abs(left) - abs(sample)) < GAIN_TOLERANCE, (
            f"Full left: left {left:.4f} should ≈ input {sample:.4f}"
        )

    def test_pan_full_right(self, panner: UltraFastStereoPanner) -> None:
        """Full right pan (1.0): left ≈ 0, right ≈ input amplitude."""
        panner.set_pan_normalized(1.0)
        sample = 0.5
        left, right = panner.process(sample)
        assert abs(left) < 0.01, f"Full right: left should be ≈0, got {left}"
        assert abs(abs(right) - abs(sample)) < GAIN_TOLERANCE, (
            f"Full right: right {right:.4f} should ≈ input {sample:.4f}"
        )

    def test_constant_power_law(
        self, panner: UltraFastStereoPanner, dc_block: np.ndarray
    ) -> None:
        """Total output RMS ≈ input RMS at every pan position (within 1 %)."""
        input_rms = float(np.sqrt(np.mean(dc_block ** 2)))
        positions = [0.0, 0.25, 0.5, 0.75, 1.0]
        powers: list[float] = []

        for pos in positions:
            panner.set_pan_normalized(pos)
            out_l, out_r = panner.process_block_mono(dc_block)
            l_rms = float(np.sqrt(np.mean(out_l ** 2)))
            r_rms = float(np.sqrt(np.mean(out_r ** 2)))
            total = float(np.sqrt(l_rms * l_rms + r_rms * r_rms))
            powers.append(total)

        mean_power = float(np.mean(powers))
        for pos, pwr in zip(positions, powers):
            rel_err = abs(pwr - mean_power) / mean_power
            assert rel_err < 0.01, (
                f"Power at pos={pos} ({pwr:.6f}) deviates {rel_err * 100:.2f}% "
                f"from mean ({mean_power:.6f})"
            )
            # Also verify power equals input RMS
            assert abs(pwr - input_rms) < 0.01, (
                f"Power at pos={pos} ({pwr:.6f}) != input RMS ({input_rms:.6f})"
            )

    def test_power_conservation_valid_range(
        self, panner: UltraFastStereoPanner, dc_block: np.ndarray
    ) -> None:
        """Power variation < 5 % across 10 uniformly spaced pan positions."""
        block = dc_block[:500]  # 500 samples is enough
        powers: list[float] = []
        for pos in np.linspace(0.0, 1.0, 10):
            panner.set_pan_normalized(float(pos))
            out_l, out_r = panner.process_block_mono(block)
            l_rms = float(np.sqrt(np.mean(out_l ** 2)))
            r_rms = float(np.sqrt(np.mean(out_r ** 2)))
            powers.append(float(np.sqrt(l_rms * l_rms + r_rms * r_rms)))

        mean_power = float(np.mean(powers))
        max_dev = (max(powers) - min(powers)) / mean_power
        assert max_dev < 0.05, (
            f"Power variation {max_dev * 100:.2f}% exceeds 5%"
        )


# ===================================================================
# MIDI CC10 MAPPING
# ===================================================================


class TestMIDICCMapping:
    """MIDI controller 10 → normalised pan → gain coefficients."""

    def test_set_pan_midi_center(self, panner: UltraFastStereoPanner) -> None:
        """set_pan(64) → gains ≈ 0.707 each (sin / cos at π/4)."""
        panner.set_pan(64)
        expected = math.cos(math.pi / 4)  # ≈ 0.7071
        assert abs(panner.left_gain - expected) < GAIN_TOLERANCE, (
            f"left_gain {panner.left_gain:.4f} != {expected:.4f}"
        )
        assert abs(panner.right_gain - expected) < GAIN_TOLERANCE, (
            f"right_gain {panner.right_gain:.4f} != {expected:.4f}"
        )
        # Both gains should be very close to each other
        assert abs(panner.left_gain - panner.right_gain) < 0.015, (
            f"Center gains differ by {abs(panner.left_gain - panner.right_gain):.6f}"
        )

    def test_set_pan_midi_left(self, panner: UltraFastStereoPanner) -> None:
        """set_pan(0) → left_gain ≈ 1.0, right_gain ≈ 0.0."""
        panner.set_pan(0)
        assert abs(panner.left_gain - 1.0) < GAIN_TOLERANCE
        assert abs(panner.right_gain) < 0.01

    def test_set_pan_midi_right(self, panner: UltraFastStereoPanner) -> None:
        """set_pan(127) → left_gain ≈ 0.0, right_gain ≈ 1.0."""
        panner.set_pan(127)
        assert abs(panner.left_gain) < 0.01
        assert abs(panner.right_gain - 1.0) < GAIN_TOLERANCE

    def test_set_pan_midi_quarter(self, panner: UltraFastStereoPanner) -> None:
        """set_pan(32) → left_gain > right_gain (image is left of centre)."""
        panner.set_pan(32)
        assert panner.left_gain > panner.right_gain, (
            f"At CC10=32 left_gain ({panner.left_gain:.4f}) should be > "
            f"right_gain ({panner.right_gain:.4f})"
        )
        # 32/127 = 0.252 → angle ≈ 0.396 rad → cos ≈ 0.92
        assert panner.left_gain > 0.8, (
            f"left_gain {panner.left_gain:.4f} should be > 0.8 at quarter-left"
        )

    def test_set_pan_normalized_clamping(
        self, panner: UltraFastStereoPanner
    ) -> None:
        """set_pan_normalized clamps out-of-range values to [0, 1]."""
        panner.set_pan_normalized(-0.5)
        assert panner.pan_position == 0.0
        assert abs(panner.left_gain - 1.0) < GAIN_TOLERANCE

        panner.set_pan_normalized(1.5)
        assert panner.pan_position == 1.0
        assert abs(panner.right_gain - 1.0) < GAIN_TOLERANCE


# ===================================================================
# BLOCK PROCESSING
# ===================================================================


class TestBlockProcessing:
    """Numba JIT block processing."""

    def test_process_block_mono_center(
        self, panner: UltraFastStereoPanner, sine_tone: np.ndarray
    ) -> None:
        """process_block_mono at centre: stereo channels match."""
        panner.set_pan_normalized(0.5)
        out_l, out_r = panner.process_block_mono(sine_tone)
        assert out_l.shape == (BLOCK,), f"Left shape {out_l.shape}"
        assert out_r.shape == (BLOCK,), f"Right shape {out_r.shape}"
        diff = float(np.max(np.abs(out_l - out_r)))
        assert diff < CENTER_EQ_TOL, f"Max L-R diff at centre: {diff:.6f}"

    def test_process_block_mono_left(
        self, panner: UltraFastStereoPanner, sine_tone: np.ndarray
    ) -> None:
        """process_block_mono at full left: right channel ≈ 0."""
        panner.set_pan_normalized(0.0)
        _out_l, out_r = panner.process_block_mono(sine_tone)
        assert float(np.max(np.abs(out_r))) < 1e-6, (
            "Right channel should be near-zero at full-left pan"
        )

    def test_process_block_stereo_output_shape(
        self, panner: UltraFastStereoPanner, sine_tone: np.ndarray
    ) -> None:
        """process_block_stereo returns correct output shapes."""
        panner.set_pan_normalized(0.5)
        out_l, out_r = panner.process_block_stereo(sine_tone, sine_tone)
        assert out_l.shape == (BLOCK,), f"Left shape {out_l.shape}"
        assert out_r.shape == (BLOCK,), f"Right shape {out_r.shape}"

    def test_process_block_mono_provided_outputs(
        self, panner: UltraFastStereoPanner, sine_tone: np.ndarray
    ) -> None:
        """Caller-provided output buffers are filled correctly."""
        panner.set_pan_normalized(0.5)
        out_l = np.zeros(BLOCK, dtype=np.float32)
        out_r = np.zeros(BLOCK, dtype=np.float32)
        ret_l, ret_r = panner.process_block_mono(sine_tone, out_l, out_r)

        assert ret_l is out_l, "Should use caller-provided left buffer"
        assert ret_r is out_r, "Should use caller-provided right buffer"
        assert np.any(out_l != 0), "Left buffer should be non-zero"
        assert np.any(out_r != 0), "Right buffer should be non-zero"
        # At centre, L ≈ R
        assert float(np.max(np.abs(out_l - out_r))) < CENTER_EQ_TOL


# ===================================================================
# RESET
# ===================================================================


class TestReset:
    """panner.reset() returns to centre."""

    def test_reset(self, panner: UltraFastStereoPanner) -> None:
        """After set to full-right, reset brings gains back to centre."""
        panner.set_pan_normalized(1.0)  # full right
        assert abs(panner.left_gain) < 0.01, (
            f"Before reset left_gain {panner.left_gain} should be ≈0"
        )
        assert abs(panner.right_gain - 1.0) < GAIN_TOLERANCE

        panner.reset()
        assert panner.pan_position == 0.5, (
            f"pan_position after reset {panner.pan_position} != 0.5"
        )
        expected = math.cos(math.pi / 4)
        assert abs(panner.left_gain - expected) < GAIN_TOLERANCE
        assert abs(panner.right_gain - expected) < GAIN_TOLERANCE


# ===================================================================
# PANNER POOL
# ===================================================================


class TestPannerPool:
    """PannerPool lifecycle."""

    def test_pool_preallocation(self) -> None:
        """Pool pre-allocates panners on construction."""
        pool = PannerPool(max_panners=200, block_size=1024, sample_rate=SR)
        stats = pool.get_pool_stats()
        # num_prealloc = min(200, 200 // 4) = 50
        assert stats["pooled_panners"] == 50, (
            f"Expected 50 pre-allocated panners, got {stats['pooled_panners']}"
        )

    def test_pool_acquire_release(self) -> None:
        """Acquire panner, verify type, release, acquire again."""
        pool = PannerPool(max_panners=100, block_size=512, sample_rate=SR)
        p = pool.acquire_panner()
        assert isinstance(p, UltraFastStereoPanner)
        # Verify it works
        left, right = p.process(0.5)
        assert isinstance(left, (float, np.floating)), (
            f"Expected float or np.floating, got {type(left).__name__}"
        )
        pool.release_panner(p)

        p2 = pool.acquire_panner()
        assert isinstance(p2, UltraFastStereoPanner)

    def test_pool_acquire_with_position(self) -> None:
        """acquire_panner(pan_position=0.0) returns panner at full left."""
        pool = PannerPool(max_panners=50, block_size=1024, sample_rate=SR)
        p = pool.acquire_panner(pan_position=0.0)
        assert abs(p.left_gain - 1.0) < GAIN_TOLERANCE, (
            f"Full left left_gain {p.left_gain:.4f} != 1.0"
        )
        assert abs(p.right_gain) < 0.01, (
            f"Full left right_gain {p.right_gain:.4f} != 0.0"
        )

    def test_pool_stats_keys(self) -> None:
        """get_pool_stats returns the expected metadata keys."""
        pool = PannerPool(max_panners=300, block_size=2048, sample_rate=96000)
        stats = pool.get_pool_stats()
        assert "pooled_panners" in stats
        assert "max_panners" in stats
        assert "block_size" in stats
        assert "sample_rate" in stats
        assert stats["max_panners"] == 300
        assert stats["block_size"] == 2048
        assert stats["sample_rate"] == 96000

    def test_pool_release_none(self) -> None:
        """release_panner(None) does not raise."""
        pool = PannerPool(max_panners=10, block_size=256, sample_rate=SR)
        # should not raise
        pool.release_panner(None)

    def test_pool_returns_to_pool(self) -> None:
        """After release, the panner is returned to the pool."""
        pool = PannerPool(max_panners=100, block_size=256, sample_rate=SR)
        before = pool.get_pool_stats()["pooled_panners"]
        p = pool.acquire_panner()
        pool.release_panner(p)
        after = pool.get_pool_stats()["pooled_panners"]
        assert after == before, (
            f"Pool count {after} != {before} after release"
        )


# ===================================================================
# STEREO PROCESSING
# ===================================================================


class TestStereoProcessing:
    """process_stereo — stereo-in / stereo-out panning."""

    def test_process_stereo_center(
        self, panner: UltraFastStereoPanner
    ) -> None:
        """At centre pan, left input dominates left output (cross-feed balanced)."""
        panner.set_pan_normalized(0.5)
        l_out, r_out = panner.process_stereo(0.75, 0.25)

        # Both outputs should be non-zero
        assert l_out != 0.0
        assert r_out != 0.0
        # L channel dominates left output
        assert l_out > r_out, (
            f"Centre stereo: left_out {l_out:.4f} should be > right_out {r_out:.4f}"
        )

    def test_process_stereo_full_left(
        self, panner: UltraFastStereoPanner
    ) -> None:
        """At full left pan, both inputs sum to left, right is zero."""
        panner.set_pan_normalized(0.0)
        # left_gain = 1.0, right_gain = 0.0
        # left_out = l_in * 1.0 + r_in * (1 - 0) = l_in + r_in
        # right_out = r_in * 0 + l_in * (1 - 1) = 0
        l_in, r_in = 0.75, 0.25
        l_out, r_out = panner.process_stereo(l_in, r_in)
        assert abs(l_out - (l_in + r_in)) < 0.01, (
            f"Full left stereo: left_out {l_out:.4f} != {l_in + r_in:.4f}"
        )
        assert abs(r_out) < 0.01, (
            f"Full left stereo: right_out {r_out:.4f} != 0"
        )

    def test_process_stereo_full_right(
        self, panner: UltraFastStereoPanner
    ) -> None:
        """At full right pan, both inputs sum to right, left is zero."""
        panner.set_pan_normalized(1.0)
        # left_gain = 0.0, right_gain = 1.0
        # left_out = l_in * 0 + r_in * (1 - 1) = 0
        # right_out = r_in * 1 + l_in * (1 - 0) = r_in + l_in
        l_in, r_in = 0.75, 0.25
        l_out, r_out = panner.process_stereo(l_in, r_in)
        assert abs(l_out) < 0.01, (
            f"Full right stereo: left_out {l_out:.4f} != 0"
        )
        assert abs(r_out - (l_in + r_in)) < 0.01, (
            f"Full right stereo: right_out {r_out:.4f} != {l_in + r_in:.4f}"
        )

    def test_process_stereo_symmetry(
        self, panner: UltraFastStereoPanner
    ) -> None:
        """Panning symmetric around centre swaps L/R output levels."""
        panner.set_pan_normalized(0.25)
        l_a, r_a = panner.process_stereo(1.0, 0.0)

        panner.set_pan_normalized(0.75)
        l_b, r_b = panner.process_stereo(0.0, 1.0)

        assert abs(l_a - r_b) < 0.02, (
            f"Symmetry fail: left_0.25 ({l_a:.4f}) != right_0.75 ({r_b:.4f})"
        )
        assert abs(r_a - l_b) < 0.02, (
            f"Symmetry fail: right_0.25 ({r_a:.4f}) != left_0.75 ({l_b:.4f})"
        )
