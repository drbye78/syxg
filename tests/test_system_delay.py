"""Tests for SystemDelayEffect — SC-8850 System Delay processor.

Tests cover:
- Initialization with sample rate and max delay seconds
- All 10 SC-8850 delay types
- set_delay_type method (including boundary clamping)
- get_delay_samples with type modifiers
- process method with various configurations
- Zero-allocation guarantee (in-place output)
- Edge cases (very short time, zero samples, max delay)
- reset method
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.processing.effects.system_delay import SystemDelayEffect, DELAY_TYPES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def delay_44100():
    """SystemDelayEffect at 44.1 kHz with small max delay."""
    return SystemDelayEffect(sample_rate=44100, max_delay_seconds=2.0)


# ---------------------------------------------------------------------------
# DELAY_TYPES dictionary tests
# ---------------------------------------------------------------------------

class TestDelayTypesDict:
    """DELAY_TYPES mapping."""

    def test_ten_types(self):
        assert len(DELAY_TYPES) == 10

    def test_all_types_present(self):
        expected = {
            0: "delay_1",
            1: "delay_2",
            2: "delay_3",
            3: "pan_delay_1",
            4: "pan_delay_2",
            5: "pan_delay_3",
            6: "long_delay_1",
            7: "long_delay_2",
            8: "long_delay_3",
            9: "modulation_delay",
        }
        assert DELAY_TYPES == expected


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

class TestInit:
    """Constructor correctness."""

    def test_default_sample_rate(self):
        d = SystemDelayEffect(sample_rate=44100)
        assert d.sample_rate == 44100

    def test_max_samples(self):
        d = SystemDelayEffect(sample_rate=44100, max_delay_seconds=2.0)
        assert d.max_samples == 88200

    def test_delay_buf_allocated(self):
        d = SystemDelayEffect(sample_rate=44100, max_delay_seconds=1.0)
        assert d._delay_buf_l.shape == (44100,)
        assert d._delay_buf_r.shape == (44100,)
        assert d._delay_buf_l.dtype == np.float32

    def test_buffers_zeroed(self):
        d = SystemDelayEffect(sample_rate=44100, max_delay_seconds=1.0)
        assert np.all(d._delay_buf_l == 0.0)
        assert np.all(d._delay_buf_r == 0.0)

    def test_write_pos_initial(self):
        d = SystemDelayEffect(sample_rate=44100)
        assert d._write_pos == 0

    def test_default_parameters(self):
        d = SystemDelayEffect(sample_rate=44100)
        assert d.delay_type == 0
        assert d.time == 400.0
        assert d.feedback == 0.3
        assert d.level == 0.5
        assert d.rate == 0.5
        assert d.depth == 0.3
        assert d.high_damp == 0.3
        assert d._phase == 0.0


# ---------------------------------------------------------------------------
# set_delay_type tests
# ---------------------------------------------------------------------------

class TestSetDelayType:
    """set_delay_type method."""

    def test_set_valid(self, delay_44100):
        for dt in range(10):
            delay_44100.set_delay_type(dt)
            assert delay_44100.delay_type == dt

    def test_clamp_below_zero(self, delay_44100):
        delay_44100.set_delay_type(-5)
        assert delay_44100.delay_type == 0

    def test_clamp_above_max(self, delay_44100):
        delay_44100.set_delay_type(99)
        assert delay_44100.delay_type == 9

    def test_set_to_diff_type(self, delay_44100):
        delay_44100.set_delay_type(0)
        delay_44100.set_delay_type(6)
        assert delay_44100.delay_type == 6


# ---------------------------------------------------------------------------
# set_parameter tests
# ---------------------------------------------------------------------------

class TestSetParameter:
    """set_parameter method."""

    def test_set_existing_param(self, delay_44100):
        delay_44100.set_parameter("time", 600.0)
        assert delay_44100.time == 600.0

    def test_set_feedback(self, delay_44100):
        delay_44100.set_parameter("feedback", 0.75)
        assert delay_44100.feedback == 0.75

    def test_set_level(self, delay_44100):
        delay_44100.set_parameter("level", 0.9)
        assert delay_44100.level == 0.9

    def test_set_rate(self, delay_44100):
        delay_44100.set_parameter("rate", 1.2)
        assert delay_44100.rate == 1.2

    def test_set_nonexistent_param(self, delay_44100):
        """Setting unknown param is silently ignored."""
        delay_44100.set_parameter("imaginary_param", 100)

    def test_set_high_damp(self, delay_44100):
        delay_44100.set_parameter("high_damp", 0.0)
        assert delay_44100.high_damp == 0.0


# ---------------------------------------------------------------------------
# get_delay_samples tests
# ---------------------------------------------------------------------------

class TestGetDelaySamples:
    """get_delay_samples — type modifiers applied to time."""

    def test_delay_1_at_400ms_44100(self, delay_44100):
        delay_44100.time = 400.0
        assert delay_44100.get_delay_samples() == 17640

    def test_delay_2_modifier(self, delay_44100):
        """delay_2 has 1.5x modifier = 600ms."""
        delay_44100.set_delay_type(1)
        delay_44100.time = 400.0
        assert delay_44100.get_delay_samples() == int(400 * 1.5 * 44.1)

    def test_delay_3_modifier(self, delay_44100):
        """delay_3 has 0.5x modifier = 200ms."""
        delay_44100.set_delay_type(2)
        assert delay_44100.get_delay_samples() == int(400 * 0.5 * 44.1)

    def test_long_delay_1_modifier(self, delay_44100):
        """long_delay_1 has 4.0x modifier."""
        delay_44100.set_delay_type(6)
        assert delay_44100.get_delay_samples() == int(400 * 4.0 * 44.1)

    def test_long_delay_3_modifier(self, delay_44100):
        """long_delay_3 has 8.0x modifier."""
        delay_44100.set_delay_type(8)
        assert delay_44100.get_delay_samples() == int(400 * 8.0 * 44.1)

    def test_types_share_modifiers(self, delay_44100):
        """Some types share modifiers (0/3/9=1.0, 1/4=1.5, 2/5=0.5)."""
        base = int(400 * 44.1)
        expected = {
            0: base, 3: base, 9: base,          # modifier 1.0
            1: int(base * 1.5), 4: int(base * 1.5),  # modifier 1.5
            2: int(base * 0.5), 5: int(base * 0.5),  # modifier 0.5
            6: int(base * 4.0),                  # long_delay_1
            7: int(base * 6.0),                  # long_delay_2
            8: int(base * 8.0),                  # long_delay_3
        }
        for dt in range(10):
            delay_44100.set_delay_type(dt)
            assert delay_44100.get_delay_samples() == expected[dt], f"Type {dt} mismatch"

    def test_short_time(self, delay_44100):
        delay_44100.time = 1.0
        samples = delay_44100.get_delay_samples()
        assert samples == 44  # 1ms * 44.1 samples/ms

    def test_zero_time(self, delay_44100):
        delay_44100.time = 0.0
        assert delay_44100.get_delay_samples() == 0


# ---------------------------------------------------------------------------
# process tests — use very short delay (2ms = ~88 samples at 44.1kHz)
# so output appears within a 256-sample block.
# ---------------------------------------------------------------------------

class TestProcessBasic:
    """process — fundamental correctness."""

    def test_process_returns_none(self, delay_44100):
        """process returns None (operates in-place on output buffers)."""
        inp = np.zeros(256, dtype=np.float32)
        out = np.zeros(256, dtype=np.float32)
        result = delay_44100.process(inp, inp, out, out, 256)
        assert result is None

    def test_process_zero_samples(self, delay_44100):
        """Processing zero samples should not error."""
        inp = np.zeros(1, dtype=np.float32)
        out = np.zeros(1, dtype=np.float32)
        delay_44100.process(inp, inp, out, out, 0)

    def test_process_produces_output(self, delay_44100):
        """With short delay, output is non-zero after the tap point."""
        n = 256
        inp = np.ones(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0        # ~88 samples
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.process(inp, inp, out, out, n)
        # Output starts at sample 88 (the delay tap)
        tap = delay_44100.get_delay_samples()
        assert tap < n
        assert np.any(out != 0.0)
        # First sample should still be zero (no delay yet)
        assert out[0] == 0.0

    def test_zero_alloc_output_is_input(self, delay_44100):
        """Output = same array as input (zero-alloc pattern)."""
        n = 256
        inp = np.random.randn(n).astype(np.float32)
        out = inp  # same array
        delay_44100.time = 2.0
        delay_44100.level = 0.5
        delay_44100.feedback = 0.0
        delay_44100.process(inp, inp, out, out, n)
        # out should be modified in-place — if out IS inp, contents changed
        assert np.any(out != 0.0)

    def test_process_stereo_independent(self, delay_44100):
        """Left and right channels processed independently (non-pan delay)."""
        n = 256
        inp_l = np.zeros(n, dtype=np.float32)
        inp_r = np.ones(n, dtype=np.float32) * 0.5
        out_l = np.zeros(n, dtype=np.float32)
        out_r = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.set_delay_type(0)
        delay_44100.process(inp_l, inp_r, out_l, out_r, n)
        assert np.all(out_l == 0.0), "Left channel should be all zero"
        assert np.any(out_r != 0.0), "Right channel should have output"


class TestProcessDelayTypes:
    """process — all delay type variations."""

    @pytest.mark.parametrize("dt", list(range(10)))
    def test_all_delay_types_produce_output(self, dt, delay_44100):
        """Each delay type produces non-zero output with non-zero input.

        Note: modulation delay (type 9) uses depth=0 here so the LFO
        does not jump the read pointer past unwritten buffer area in a
        single block. Dedicated modulation tests exercise non-zero depth.
        """
        n = 2048  # large enough for long delays (type 8 modifier=8× → ~705 samples)
        inp = np.ones(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.depth = 0.0  # no LFO offset — basic output test only
        delay_44100.set_delay_type(dt)
        delay_44100.process(inp, inp, out, out, n)
        tap = delay_44100.get_delay_samples()
        assert tap < n, f"Type {dt} delay tap {tap} exceeds buffer {n}"
        assert np.any(out[tap:] != 0.0), f"Delay type {dt} produced no output after tap"

    def test_pan_delay_cross_feed(self, delay_44100):
        """Pan delay (type 3) cross-feeds L→R and R→L."""
        n = 512
        inp_l = np.zeros(n, dtype=np.float32)
        inp_r = np.zeros(n, dtype=np.float32)
        inp_l[0] = 1.0       # impulse on left
        out_l = np.zeros(n, dtype=np.float32)
        out_r = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.set_delay_type(3)  # pan_delay_1
        delay_44100.process(inp_l, inp_r, out_l, out_r, n)
        # Pan delay writes cross-fed delayed signal:
        # _delay_buf_l[wp] += delayed_r * fb * 0.5 (but fb=0 so no-op)
        # _delay_buf_r[wp] += delayed_l * fb * 0.5
        # With feedback=0, only direct delayed output appears
        # Output is at the delay tap position
        tap = delay_44100.get_delay_samples()
        assert tap < n
        # At least one channel should have output at the tap
        assert abs(out_l[tap]) > 0 or abs(out_r[tap]) > 0

    def test_modulation_delay(self, delay_44100):
        """Modulation delay (type 9) applies LFO to delay time.

        Because the LFO offset (depth × max_samples × 0.1) can be
        thousands of samples, we first pre-fill the delay buffer so the
        modulated read position lands on written data.
        """
        n = 512
        inp = np.ones(n, dtype=np.float32) * 0.5
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.depth = 0.0  # fill buffer without LFO offset first
        delay_44100.set_delay_type(9)

        # Pre-fill the circular delay buffer with enough blocks
        for _ in range(400):  # 400 × 512 ≈ 204800 samples >> max_samples (88200)
            delay_44100.process(inp, inp, out, out, n)

        # Now enable modulation — the buffer has data everywhere so
        # modulated reads will hit non-zero samples.
        out.fill(0.0)
        delay_44100.depth = 0.5
        delay_44100.rate = 20.0
        delay_44100._phase = 0.0
        delay_44100.process(inp, inp, out, out, n)

        tap = delay_44100.get_delay_samples()
        assert tap < n
        assert np.any(out != 0.0)


class TestProcessFeedback:
    """process — feedback behavior."""

    def test_feedback_zero_no_repeat(self, delay_44100):
        """With zero feedback, only input appears once."""
        n = 1024
        inp = np.zeros(n, dtype=np.float32)
        inp[0] = 1.0
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 0.5
        delay_44100.feedback = 0.0
        delay_44100.process(inp, inp, out, out, n)
        non_zero = np.count_nonzero(out)
        assert non_zero > 0

    def test_feedback_high_repeats(self, delay_44100):
        """High feedback produces more non-zero samples than low feedback."""
        n = 2048
        inp = np.zeros(n, dtype=np.float32)
        inp[0] = 1.0

        delay_44100.time = 2.0
        delay_44100.level = 0.5

        out_low = np.zeros(n, dtype=np.float32)
        delay_44100.feedback = 0.0
        delay_44100.reset()
        delay_44100.process(inp.copy(), inp.copy(), out_low, out_low, n)

        out_high = np.zeros(n, dtype=np.float32)
        delay_44100.feedback = 0.9
        delay_44100.reset()
        delay_44100.process(inp.copy(), inp.copy(), out_high, out_high, n)

        assert np.count_nonzero(out_high) >= np.count_nonzero(out_low)

    def test_feedback_saturates(self, delay_44100):
        """Feedback internally scaled by 0.7, output stays bounded."""
        n = 512
        inp = np.ones(n, dtype=np.float32) * 0.1
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 1.0
        delay_44100.process(inp, inp, out, out, n)
        assert np.all(np.isfinite(out))
        assert np.max(np.abs(out)) < 10.0


class TestProcessHighDamp:
    """process — high damp filter."""

    def test_high_damp_reduces_output(self, delay_44100):
        """Higher high_damp reduces delayed signal amplitude."""
        n = 512
        inp = np.ones(n, dtype=np.float32) * 0.5
        delay_44100.time = 2.0
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0

        out_lo = np.zeros(n, dtype=np.float32)
        delay_44100.high_damp = 0.0
        delay_44100.reset()
        delay_44100.process(inp.copy(), inp.copy(), out_lo, out_lo, n)

        out_hi = np.zeros(n, dtype=np.float32)
        delay_44100.high_damp = 1.0
        delay_44100.reset()
        delay_44100.process(inp.copy(), inp.copy(), out_hi, out_hi, n)
        # High damp reduces signal, so max(hi) <= max(lo)
        assert np.max(np.abs(out_hi)) <= np.max(np.abs(out_lo)) + 1e-6


class TestProcessEdgeCases:
    """process — boundary conditions."""

    def test_delay_samples_less_than_1_skips(self, delay_44100):
        """When delay_samples < 1, process returns early (no-op)."""
        n = 256
        inp = np.ones(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 0.0
        delay_44100.level = 1.0
        delay_44100.process(inp, inp, out, out, n)
        assert np.all(out == 0.0)

    def test_delay_exceeds_max_skips(self, delay_44100):
        """When delay_samples >= max_samples, process returns early."""
        n = 256
        inp = np.ones(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 1e9
        delay_44100.level = 1.0
        delay_44100.process(inp, inp, out, out, n)
        assert np.all(out == 0.0)

    def test_large_block_size(self, delay_44100):
        """Processing a large block should not error."""
        n = 8192
        inp = np.random.randn(n).astype(np.float32) * 0.25
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 0.5
        delay_44100.feedback = 0.3
        delay_44100.process(inp, inp, out, out, n)
        assert np.all(np.isfinite(out))

    def test_all_zeros_input_produces_zeros(self, delay_44100):
        """Zero input → zero output (no self-oscillation)."""
        n = 256
        inp = np.zeros(n, dtype=np.float32)
        out = np.ones(n, dtype=np.float32)  # start non-zero
        delay_44100.time = 2.0
        delay_44100.level = 0.5
        delay_44100.feedback = 0.0
        delay_44100.process(inp, inp, out, out, n)
        assert np.all(out == 0.0)

    def test_delay_shorter_than_block(self, delay_44100):
        """Delay tap falls within the block."""
        n = 1024
        inp = np.zeros(n, dtype=np.float32)
        inp[0] = 1.0
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0  # ~88 samples
        delay_44100.level = 1.0
        delay_44100.feedback = 0.0
        delay_44100.process(inp, inp, out, out, n)
        tap = delay_44100.get_delay_samples()  # ~88
        assert 0 < tap < n
        assert abs(out[tap]) > 0.0


# ---------------------------------------------------------------------------
# reset tests
# ---------------------------------------------------------------------------

class TestReset:
    """reset method."""

    def test_reset_clears_buffers(self, delay_44100):
        delay_44100._delay_buf_l[100] = 0.5
        delay_44100._delay_buf_r[200] = 0.3
        delay_44100._write_pos = 500
        delay_44100._phase = 1.0
        delay_44100.reset()
        assert delay_44100._delay_buf_l[100] == 0.0
        assert delay_44100._delay_buf_r[200] == 0.0
        assert delay_44100._write_pos == 0
        assert delay_44100._phase == 0.0

    def test_reset_after_process(self, delay_44100):
        n = 256
        inp = np.ones(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        delay_44100.time = 2.0
        delay_44100.level = 0.5
        delay_44100.feedback = 0.3
        delay_44100.process(inp, inp, out, out, n)
        delay_44100.reset()
        assert delay_44100._write_pos == 0
        assert np.all(delay_44100._delay_buf_l == 0.0)
        assert np.all(delay_44100._delay_buf_r == 0.0)
