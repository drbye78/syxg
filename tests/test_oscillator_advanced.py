"""
Advanced tests for UltraFastXGLFO and OscillatorPool.

Verifies actual DSP behavior: waveform shapes, frequency accuracy,
phase continuity, delay, fade-in, reset, modulation, and pooling.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from synth.primitives.oscillator import UltraFastXGLFO, OscillatorPool


# ============================================================================
# HELPERS
# ============================================================================


def make_lfo(
    id: int = 0,
    waveform: str = "sine",
    rate: float = 5.0,
    depth: float = 1.0,
    delay: float = 0.0,
    sample_rate: int = 48000,
    block_size: int = 1024,
) -> UltraFastXGLFO:
    """Create an LFO with controllers set to neutral (rate_modulation = 0).

    The default controller values (mod_wheel=0, etc.) produce a negative
    rate_modulation of -0.75, which makes the effective rate 25% of nominal.
    Setting all controllers to 0.5 gives rate_modulation = 0, so the LFO
    runs at exactly the requested frequency.
    """
    lfo = UltraFastXGLFO(
        id=id,
        waveform=waveform,
        rate=rate,
        depth=depth,
        delay=delay,
        sample_rate=sample_rate,
        block_size=block_size,
    )
    # Neutralise controller modulation
    lfo.set_mod_wheel(0.5)
    lfo.set_breath_controller(0.5)
    lfo.set_foot_controller(0.5)
    lfo.set_channel_aftertouch(0.5)
    lfo.set_frequency(lfo.rate)  # recalculate phase_step with neutral controllers
    return lfo


def generate_lfo_blocks(lfo: UltraFastXGLFO, num_samples: int) -> np.ndarray:
    """Generate LFO samples in consecutive blocks, respecting buffer capacity.

    Uses the LFO's own block_size (or num_samples if smaller) and preserves
    phase continuity between calls.
    """
    output = np.zeros(num_samples, dtype=np.float32)
    block_size = lfo.block_size
    if block_size <= 0:
        return output
    pos = 0
    while pos < num_samples:
        remaining = num_samples - pos
        n = min(block_size, remaining)
        buf = output[pos : pos + n]
        lfo.generate_block(buf, n)
        pos += n
    return output


def find_zero_crossings(
    samples: np.ndarray, min_gap: int = 100
) -> list[int]:
    """Return sample indices of positive-going zero crossings.

    Filters out spurious crossings caused by discrete LUT interpolation
    noise near zero by requiring crossings to be at least *min_gap* apart.
    """
    raw: list[int] = []
    for i in range(1, len(samples)):
        if samples[i - 1] <= 0 and samples[i] > 0:
            raw.append(i)

    # Filter crossings that are too close (likely LUT noise near zero)
    if not raw:
        return []

    crossings: list[int] = [raw[0]]
    for c in raw[1:]:
        if c - crossings[-1] >= min_gap:
            crossings.append(c)
    return crossings


def measure_period(
    lfo: UltraFastXGLFO, expected_hz: float, sr: int = 48000, cycles: int = 2
) -> float:
    """Generate enough samples and measure period from zero-crossings."""
    samples_needed = int(sr / expected_hz * cycles) + 2048
    samples = generate_lfo_blocks(lfo, samples_needed)
    crossings = find_zero_crossings(samples)
    assert len(crossings) >= 2, f"Not enough zero crossings for {expected_hz} Hz"
    period_samples = crossings[-1] - crossings[0]
    period_cycles = len(crossings) - 1
    return period_samples / period_cycles


# ============================================================================
# WAVEFORM SHAPE VERIFICATION
# ============================================================================


@pytest.mark.unit
class TestWaveformShape:
    """Verify actual DSP waveform shapes."""

    def test_sine_waveform_shape(self):
        """Verify sine LFO produces correct period and amplitude."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        samples = generate_lfo_blocks(lfo, sr)  # 1 full cycle at 1Hz
        assert len(samples) == sr

        # Find zero crossings to measure period
        crossings = find_zero_crossings(samples)
        assert len(crossings) >= 2, "Should have at least 2 zero crossings"
        period = crossings[1] - crossings[0]
        assert 47800 <= period <= 48200, f"Period {period} out of range (expected ~{sr})"

        # Verify amplitude range
        assert np.max(samples) <= 1.0 + 1e-6, f"Max amplitude {np.max(samples)} > 1.0"
        assert np.min(samples) >= -1.0 - 1e-6, f"Min amplitude {np.min(samples)} < -1.0"
        assert np.max(samples) > 0.95, f"Max amplitude too low: {np.max(samples)}"
        assert np.min(samples) < -0.95, f"Min amplitude too high: {np.min(samples)}"

    def test_triangle_waveform_linearity(self):
        """Verify triangle LFO has constant slope (linear ramps).

        The second difference of a triangle wave should be near zero
        everywhere except at the inflection points (peak and trough).
        """
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="triangle", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        samples = generate_lfo_blocks(lfo, sr)

        # First difference (slope)
        diff = np.diff(samples)
        # Second difference (change in slope) — near-zero means constant slope
        second_diff = np.diff(diff)

        # Exclude samples near inflection points (peaks/troughs at 1/4 and 3/4)
        # For 48000 samples: inflection at ~12000 and ~36000
        mask = np.ones(len(second_diff), dtype=bool)
        for center in (11999, 12000, 12001, 35999, 36000, 36001):
            for offset in range(-3, 4):
                idx = center + offset
                if 0 <= idx < len(second_diff):
                    mask[idx] = False

        filtered = second_diff[mask]
        max_dev = np.abs(filtered).max()
        assert max_dev < 0.02, f"Second diff max deviation {max_dev} — slopes not constant"

    def test_square_waveform_duty_cycle(self):
        """Verify square LFO has 50% duty cycle."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="square", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        samples = generate_lfo_blocks(lfo, sr)

        above = np.sum(samples > 0)
        below = np.sum(samples < 0)
        total = above + below
        duty = above / total

        assert 0.48 <= duty <= 0.52, f"Duty cycle {duty:.4f} out of 50% range"

    def test_sawtooth_waveform_ramp(self):
        """Verify sawtooth LFO ramps and resets correctly.

        The sawtooth rises from 0->1 in the first half, then resets to -1
        and rises to 0 in the second half.
        """
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sawtooth", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        samples = generate_lfo_blocks(lfo, sr)

        # Find midpoint (where phase wraps)
        half_idx = sr // 2

        # Verify first half ramp (samples ~1 to half_idx-1): monotonically increasing
        first_half = samples[1:half_idx]
        if len(first_half) > 1:
            diffs = np.diff(first_half)
            # Allow tiny negative due to floating point
            assert np.all(diffs >= -1e-7), "First half should be monotonically non-decreasing"

        # Verify second half ramp (samples half_idx+1 to end): monotonically increasing
        second_half = samples[half_idx + 1 :]
        if len(second_half) > 1:
            diffs2 = np.diff(second_half)
            assert np.all(diffs2 >= -1e-7), "Second half should be monotonically non-decreasing"

        # Verify reset at midpoint: sample[half_idx-1] ~ 1.0, sample[half_idx] ~ -1.0
        assert samples[half_idx - 1] > 0.9, (
            f"Pre-reset value too low: {samples[half_idx - 1]}"
        )
        assert samples[half_idx] < -0.9, (
            f"Post-reset value too high: {samples[half_idx]}"
        )

    def test_sample_and_hold_steps(self):
        """Verify S&H LFO holds constant values within each step."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sample_and_hold", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        samples = generate_lfo_blocks(lfo, sr)

        # For 1Hz at 48kHz, 16 steps per cycle => each step is 3000 samples
        # Verify constant values within each step
        step_size = sr // 16
        step_values: list[float] = []
        for step in range(16):
            start = step * step_size
            end = min(start + step_size - 2, len(samples))
            if start >= end:
                break
            chunk = samples[start:end]
            if len(chunk) > 5:
                unique_vals = np.unique(chunk)
                assert len(unique_vals) <= 2, (
                    f"Step {step}: expected constant value, got {len(unique_vals)} "
                    f"unique values"
                )
                step_values.append(float(chunk[0]))

        # Verify not all steps have the same value
        if len(step_values) > 1:
            unique_step_vals = set(round(v, 4) for v in step_values)
            assert len(unique_step_vals) > 1, "All S&H steps have same value!"


# ============================================================================
# FREQUENCY ACCURACY
# ============================================================================


@pytest.mark.unit
class TestFrequencyAccuracy:
    """Verify LFO frequency accuracy across rates."""

    @pytest.mark.parametrize("hz", [0.5, 1.0, 5.0, 10.0])
    def test_frequency_accuracy(self, hz: float):
        """Measure period at various frequencies, verify within 5%."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=hz, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        measured = measure_period(lfo, hz, sr)
        expected = sr / hz
        error_pct = abs(measured - expected) / expected * 100
        assert error_pct < 5.0, (
            f"Frequency {hz} Hz: measured period {measured:.1f} samples, "
            f"expected {expected:.1f}, error {error_pct:.2f}%"
        )

    def test_frequency_update(self):
        """Change frequency mid-stream and verify new period."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        # Generate some samples at 1Hz
        _ = generate_lfo_blocks(lfo, sr // 2)
        # Change to 5Hz via set_parameters (also resets phase)
        lfo.set_parameters(rate=5.0)
        # Measure period at 5Hz
        measured = measure_period(lfo, 5.0, sr)
        expected = sr / 5.0
        error_pct = abs(measured - expected) / expected * 100
        assert error_pct < 5.0, (
            f"After rate change: measured period {measured:.1f} samples, "
            f"expected {expected:.1f}, error {error_pct:.2f}%"
        )


# ============================================================================
# PHASE CONTINUITY ACROSS BLOCKS
# ============================================================================


@pytest.mark.unit
class TestPhaseContinuity:
    """Verify seamless phase continuity across block boundaries."""

    def test_phase_continuity(self):
        """Last sample of block 1 should match first of block 2 (within tolerance)."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf1 = np.zeros(1024, dtype=np.float32)
        buf2 = np.zeros(1024, dtype=np.float32)

        lfo.generate_block(buf1, 1024)
        lfo.generate_block(buf2, 1024)

        # Last sample of block 1 and first of block 2 are consecutive phases
        # For a 1Hz sine at 48kHz, difference ≈ step*cos(phase) ≤ 0.00013
        diff = abs(buf2[0] - buf1[-1])
        assert diff < 0.01, (
            f"Phase discontinuity: block1[-1]={buf1[-1]:.6f}, "
            f"block2[0]={buf2[0]:.6f}, diff={diff:.6f}"
        )

    def test_phase_continuity_multiple_blocks(self):
        """Verify seamless waveform across 5 consecutive blocks."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=1.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        blocks = []
        for _ in range(100):  # enough for ~2.1 cycles at 1Hz
            buf = np.zeros(1024, dtype=np.float32)
            lfo.generate_block(buf, 1024)
            blocks.append(buf)

        # Check each boundary
        for i in range(99):
            diff = abs(blocks[i + 1][0] - blocks[i][-1])
            assert diff < 0.01, (
                f"Boundary {i}: block{i}[-1]={blocks[i][-1]:.6f}, "
                f"block{i+1}[0]={blocks[i+1][0]:.6f}, diff={diff:.6f}"
            )

        # Concatenate and verify frequency is still correct
        full = np.concatenate(blocks)
        crossings = find_zero_crossings(full)
        assert len(crossings) >= 2, "Not enough zero crossings in concatenated blocks"
        period = (crossings[-1] - crossings[0]) / (len(crossings) - 1)
        expected = sr
        error_pct = abs(period - expected) / expected * 100
        assert error_pct < 5.0, (
            f"Concatenated period {period:.1f}, expected {expected:.1f}, "
            f"error {error_pct:.2f}%"
        )


# ============================================================================
# PHASE OFFSET
# ============================================================================


@pytest.mark.unit
class TestPhaseOffset:
    """Verify phase offset produces correct waveform shifts."""

    def test_phase_offset_180_degrees(self):
        """180° offset sine should be inverted relative to normal sine."""
        sr = 48000
        # Normal sine
        lfo_normal = make_lfo(
            id=0, waveform="sine", rate=4.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        # Offset sine (180°) — reset first, THEN set phase offset
        lfo_offset = make_lfo(
            id=0, waveform="sine", rate=4.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo_offset.reset()
        lfo_offset.set_phase_offset(180.0)

        n = sr // 4  # 1 full cycle at 4Hz
        norm_samples = generate_lfo_blocks(lfo_normal, n)
        off_samples = generate_lfo_blocks(lfo_offset, n)

        # 180° offset means off[i] ≈ -norm[i]
        # Compare only samples where magnitude is significant
        ratios: list[float] = []
        for i in range(len(norm_samples)):
            if abs(norm_samples[i]) > 0.01:
                ratios.append(float(off_samples[i] / norm_samples[i]))
        if ratios:
            mean_ratio = np.mean(ratios)
            assert -1.1 <= mean_ratio <= -0.9, (
                f"180° offset ratio {mean_ratio:.4f} should be ~ -1.0"
            )

    def test_phase_offset_90_degrees(self):
        """90° offset sine should differ from normal (cosine vs sine)."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=4.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.reset()
        lfo.set_phase_offset(90.0)

        n = sr // 4  # 1 cycle at 4Hz
        samples = generate_lfo_blocks(lfo, n)

        # At 90° offset, sin(x + π/2) = cos(x). The first sample at phase=90°
        # should be sin(π/2) ≈ 1.0
        assert abs(samples[0]) > 0.5, (
            f"90° offset sine should start near peak, got {samples[0]:.4f}"
        )

        # Normal sine (phase=0) at the same indices should differ
        lfo_normal = make_lfo(
            id=0, waveform="sine", rate=4.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        normal = generate_lfo_blocks(lfo_normal, n)

        # The correlation between sin(x) and cos(x) over 1 full cycle should be ~0
        # But small sample sizes + discrete sampling might give ~0.3
        correlation = np.mean(samples * normal) / (
            np.std(samples) * np.std(normal) + 1e-10
        )
        assert abs(correlation) < 0.5, (
            f"90° offset should attenuate correlation, got {correlation:.4f}"
        )


# ============================================================================
# DELAY BEHAVIOR
# ============================================================================


@pytest.mark.unit
class TestDelay:
    """Verify LFO delay behavior."""

    def test_delay_phase(self):
        """With delay=0.1s, first delay_samples should be 0, then non-zero."""
        sr = 48000
        delay_s = 0.1
        expected_delay_samples = int(delay_s * sr)  # 4800

        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=delay_s,
            sample_rate=sr, block_size=1024,
        )
        assert lfo.delay_samples == expected_delay_samples

        # Generate enough samples to cover the delay plus some active
        total = expected_delay_samples + 2048
        samples = generate_lfo_blocks(lfo, total)

        # First delay_samples should be zero
        assert np.all(samples[:expected_delay_samples] == 0.0), (
            f"First {expected_delay_samples} samples should be zero"
        )
        # Samples after delay should be non-zero
        post_delay = samples[expected_delay_samples : expected_delay_samples + 1024]
        assert np.any(post_delay != 0.0), "Post-delay samples should be non-zero"

    def test_delay_zero(self):
        """With delay=0, first sample should be non-zero for square waveform."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="square", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1,
        )
        buf = np.zeros(1, dtype=np.float32)
        lfo.generate_block(buf, 1)
        # Square wave at phase=0 should be 1.0 * depth
        assert buf[0] != 0.0, "First sample with delay=0 should be non-zero"
        assert buf[0] == pytest.approx(1.0, abs=1e-6), (
            f"Square wave first sample should be ~1.0, got {buf[0]}"
        )


# ============================================================================
# FADE-IN
# ============================================================================


@pytest.mark.unit
class TestFadeIn:
    """Verify fade-in parameter storage.

    Note: The DSP processing path does not currently apply fade-in
    to the output buffer. This test verifies the parameter is stored
    and calculated correctly.
    """

    def test_fade_in_time(self):
        """Verify fade_in_time sets fade_in_samples and fade_in_time."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        assert lfo.fade_in_time == 0.0
        assert lfo.fade_in_samples == 0

        lfo.set_fade_in_time(0.05)
        assert lfo.fade_in_time == pytest.approx(0.05)
        assert lfo.fade_in_samples == int(0.05 * sr)  # 2400

    def test_fade_in_time_max_bounds(self):
        """Verify fade-in clamps to 0-5s."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.set_fade_in_time(10.0)
        assert lfo.fade_in_time == pytest.approx(5.0)

        lfo.set_fade_in_time(-1.0)
        assert lfo.fade_in_time == pytest.approx(0.0)

    def test_fade_in_via_set_parameters(self):
        """Verify set_parameters(fade=...) sets fade-in time."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.set_parameters(fade=0.1)
        assert lfo.fade_in_time == pytest.approx(0.1)
        assert lfo.fade_in_samples == int(0.1 * sr)


# ============================================================================
# RESET
# ============================================================================


@pytest.mark.unit
class TestReset:
    """Verify LFO reset behavior."""

    def test_reset_phase(self):
        """Verify reset() zeroes phase and delay_counter."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.1,
            sample_rate=sr, block_size=1024,
        )
        # Advance state
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert lfo.phase != 0.0 or lfo.delay_counter != 0

        lfo.reset()
        assert lfo.phase == 0.0
        assert lfo.delay_counter == 0


# ============================================================================
# KEY SYNC
# ============================================================================


@pytest.mark.unit
class TestKeySync:
    """Verify key synchronization behavior."""

    def test_key_sync_resets_phase(self):
        """With key_sync=True, reset_phase_for_key_sync() resets phase."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.set_key_sync(True)
        # Advance phase
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert lfo.phase != 0.0, "Phase should have advanced"

        lfo.reset_phase_for_key_sync()
        assert lfo.phase == 0.0, "Key sync should reset phase to 0"

    def test_key_sync_with_phase_offset(self):
        """With key_sync + phase_offset, reset goes to offset."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.set_key_sync(True)
        lfo.set_phase_offset(90.0)
        # Advance phase
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert lfo.phase != 0.0

        lfo.reset_phase_for_key_sync()
        expected_phase = (90.0 / 360.0) * 2.0 * math.pi
        assert lfo.phase == pytest.approx(expected_phase, abs=1e-10), (
            f"Key sync should reset to phase offset {expected_phase}, "
            f"got {lfo.phase}"
        )

    def test_key_sync_disabled(self):
        """With key_sync=False, reset_phase_for_key_sync() is no-op."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.set_key_sync(False)
        # Advance phase
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        phase_before = lfo.phase

        lfo.reset_phase_for_key_sync()
        # Phase should NOT have changed (key_sync is False)
        assert lfo.phase == phase_before, "Key sync disabled should not change phase"


# ============================================================================
# XG CONTROLLER MODULATION
# ============================================================================


@pytest.mark.unit
class TestXGControllerModulation:
    """Verify XG controller modulation affects LFO parameters."""

    def test_mod_wheel_affects_phase_step(self):
        """Set mod_wheel to 1.0, phase_step should differ from mod_wheel=0."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        orig_step = lfo.phase_step
        # Set to neutral (0.5) — rate_modulation = 0
        lfo.set_mod_wheel(0.5)
        lfo.set_frequency(lfo.rate)
        neutral_step = lfo.phase_step

        # Set to max (1.0)
        lfo.set_mod_wheel(1.0)
        lfo.set_frequency(lfo.rate)
        max_step = lfo.phase_step

        assert max_step != pytest.approx(neutral_step), (
            "Mod wheel should change phase_step from neutral"
        )

    def test_update_xg_vibrato_rate(self):
        """Verify XG CC77 sets rate correctly."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )

        # CC77 value 64 → rate ~1.0 Hz
        lfo.update_xg_vibrato_rate(64)
        assert lfo.rate == pytest.approx(1.0, abs=0.01), (
            f"Vibrato rate CC77=64 should be ~1.0, got {lfo.rate}"
        )

        # CC77 value 127 → rate > 5.0 Hz
        lfo.update_xg_vibrato_rate(127)
        assert lfo.rate > 5.0, (
            f"Vibrato rate CC77=127 should be >5.0, got {lfo.rate}"
        )
        assert lfo.rate == pytest.approx(10.0, abs=0.01)

    def test_update_xg_vibrato_depth(self):
        """Verify XG CC78 sets pitch_depth_cents correctly."""
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.update_xg_vibrato_depth(64)
        expected = (64 / 127.0) * 600.0
        assert lfo.pitch_depth_cents == pytest.approx(expected, abs=0.5)

        lfo.update_xg_vibrato_depth(127)
        assert lfo.pitch_depth_cents == pytest.approx(600.0, abs=0.5)

    def test_update_xg_vibrato_delay(self):
        """Verify XG CC79 sets delay correctly."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        lfo.update_xg_vibrato_delay(64)
        expected_delay = (64 / 127.0) * 5.0
        assert lfo.pitch_delay == pytest.approx(expected_delay, abs=0.01)
        assert lfo.delay_samples == int(expected_delay * sr)


# ============================================================================
# RATE / DEPTH MODULATION
# ============================================================================


@pytest.mark.unit
class TestRateDepthModulation:
    """Verify real-time rate/depth modulation with smoothing."""

    def test_apply_rate_modulation(self):
        """Apply rate_mod=1.0 should roughly double the rate."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        orig_step = lfo.phase_step

        lfo.apply_rate_modulation(1.0)
        # 2^1.0 = 2x rate
        expected_step = lfo.base_rate * (2.0 ** 1.0) * 2.0 * math.pi / sr
        assert lfo.phase_step == pytest.approx(expected_step, rel=0.01), (
            f"Rate modulation: phase_step should be ~2x, "
            f"got {lfo.phase_step}, expected {expected_step}"
        )
        assert lfo.phase_step > orig_step, (
            "Rate modulation should increase phase_step"
        )

    def test_apply_rate_modulation_negative(self):
        """Apply rate_mod=-1.0 should roughly halve the rate."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        orig_step = lfo.phase_step

        lfo.apply_rate_modulation(-1.0)
        # 2^(-1.0) = 0.5x rate
        expected_step = lfo.base_rate * (2.0 ** (-1.0)) * 2.0 * math.pi / sr
        assert lfo.phase_step == pytest.approx(expected_step, rel=0.01), (
            f"Rate modulation: phase_step should be ~0.5x, "
            f"got {lfo.phase_step}, expected {expected_step}"
        )
        assert lfo.phase_step < orig_step, (
            "Negative rate modulation should decrease phase_step"
        )

    def test_smooth_rate_transitions(self):
        """Rate modulation uses 4-sample smoothing."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        # Apply modulation multiple times - each call adds to smoothing history
        lfo.apply_rate_modulation(1.0)
        step1 = lfo.phase_step
        lfo.apply_rate_modulation(1.0)
        step2 = lfo.phase_step
        lfo.apply_rate_modulation(1.0)
        step3 = lfo.phase_step

        # After 3 identical modulations, the smoothing should be stable
        # (average of [1.0, 1.0, 1.0] = 1.0, same as single [1.0] = 1.0)
        assert step3 == pytest.approx(step1, rel=0.01)

    def test_apply_depth_modulation(self):
        """Apply depth_mod=0.5 should increase modulated_depth by ~1.5x."""
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        orig_mod_depth = lfo.modulated_depth

        lfo.apply_depth_modulation(0.5)
        expected = lfo.base_depth * (1.0 + 0.5)
        assert lfo.modulated_depth == pytest.approx(expected, rel=0.01), (
            f"Depth modulation: expected {expected}, got {lfo.modulated_depth}"
        )
        assert lfo.modulated_depth > orig_mod_depth


# ============================================================================
# PITCH / TREMOLO MODULATION OUTPUT
# ============================================================================


@pytest.mark.unit
class TestModulationOutput:
    """Verify get_pitch_modulation and get_tremolo_modulation."""

    def test_get_pitch_modulation_returns_float(self):
        """get_pitch_modulation() returns a float within expected range."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        # Advance phase past 0 to avoid sin(0)=0
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)

        val = lfo.get_pitch_modulation()
        assert isinstance(val, float), f"Expected float, got {type(val)}"
        # pitch_depth is 50 cents, LFO value in [-1, 1]
        assert -50.0 <= val <= 50.0, f"Pitch modulation out of range: {val}"

    def test_get_tremolo_modulation_returns_float(self):
        """get_tremolo_modulation() returns a float."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        # Advance phase
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)

        val = lfo.get_tremolo_modulation()
        assert isinstance(val, float)
        assert -1.0 <= val <= 1.0, f"Tremolo modulation out of range: {val}"

    def test_get_pitch_modulation_with_vibrato_disabled(self):
        """get_pitch_modulation returns 0 when vibrato disabled."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        val = lfo.get_pitch_modulation(vibrato_enabled=False)
        assert val == 0.0


# ============================================================================
# DEPTH SCALING
# ============================================================================


@pytest.mark.unit
class TestDepthScaling:
    """Verify depth parameter scales output correctly."""

    def test_depth_zero(self):
        """With depth=0.0, all output should be 0."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=0.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert np.all(buf == 0.0), "Depth=0 should produce all zeros"

    def test_depth_half(self):
        """With depth=0.5, max absolute value should be ~0.5."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(2048, dtype=np.float32)
        # Generate in blocks of block_size (1024) each to stay within buffer capacity
        lfo.generate_block(buf[:1024], 1024)
        lfo.generate_block(buf[1024:], 1024)
        max_abs = np.max(np.abs(buf))
        assert 0.45 <= max_abs <= 0.55, (
            f"Depth=0.5 should give max_abs ~0.5, got {max_abs}"
        )

    def test_depth_max_one(self):
        """With depth=1.0, max absolute value should be ~1.0."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(2048, dtype=np.float32)
        lfo.generate_block(buf[:1024], 1024)
        lfo.generate_block(buf[1024:], 1024)
        max_abs = np.max(np.abs(buf))
        assert 0.95 <= max_abs <= 1.05, (
            f"Depth=1.0 should give max_abs ~1.0, got {max_abs}"
        )


# ============================================================================
# OSCILLATOR POOL
# ============================================================================


@pytest.mark.unit
class TestOscillatorPool:
    """Verify OscillatorPool acquire/release and stats."""

    def test_pool_acquire_release(self):
        """Acquire and release oscillator works correctly."""
        pool = OscillatorPool(max_oscillators=100, block_size=256, sample_rate=48000)
        stats_before = pool.get_pool_stats()

        osc = pool.acquire_oscillator(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
        )
        assert isinstance(osc, UltraFastXGLFO)
        assert osc.rate == 5.0
        assert osc.waveform == "sine"

        pool.release_oscillator(osc)
        stats_after = pool.get_pool_stats()
        # Should have at least as many as before
        # (acquire took one, release puts one back — might be same or more if
        # acquire created new)
        assert stats_after["pooled_oscillators"] >= stats_before["pooled_oscillators"] - 1

    def test_pool_preallocation(self):
        """Verify pool pre-allocates oscillators."""
        pool = OscillatorPool(max_oscillators=100, block_size=256, sample_rate=48000)
        stats = pool.get_pool_stats()
        expected_prealloc = min(300, 100 // 4)  # = 25
        assert stats["pooled_oscillators"] == expected_prealloc, (
            f"Expected {expected_prealloc} pre-allocated, "
            f"got {stats['pooled_oscillators']}"
        )

    def test_pool_stats(self):
        """Verify get_pool_stats() returns expected keys and values."""
        pool = OscillatorPool(max_oscillators=500, block_size=512, sample_rate=44100)
        stats = pool.get_pool_stats()
        assert "pooled_oscillators" in stats
        assert "max_oscillators" in stats
        assert "block_size" in stats
        assert "sample_rate" in stats
        assert stats["max_oscillators"] == 500
        assert stats["block_size"] == 512
        assert stats["sample_rate"] == 44100

    def test_pool_reuse(self):
        """Verify acquired oscillator can be used after release."""
        pool = OscillatorPool(max_oscillators=10, block_size=256, sample_rate=48000)
        osc1 = pool.acquire_oscillator(id=0, waveform="square", rate=2.0)
        pool.release_oscillator(osc1)

        osc2 = pool.acquire_oscillator(id=0, waveform="sine", rate=5.0)
        assert osc2 is not None
        assert isinstance(osc2, UltraFastXGLFO)
        assert osc2.waveform == "sine"


# ============================================================================
# SET_FREQUENCY
# ============================================================================


@pytest.mark.unit
class TestSetFrequency:
    """Verify set_frequency updates rate without resetting phase."""

    def test_set_frequency_updates_rate(self):
        """set_frequency changes rate and recalculates phase_step."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        orig_step = lfo.phase_step

        lfo.set_frequency(10.0)
        assert lfo.rate == 10.0
        # phase_step should be ~2x (10 Hz vs 5 Hz)
        assert lfo.phase_step > orig_step, (
            "set_frequency to higher rate should increase phase_step"
        )

    def test_set_frequency_minimum(self):
        """set_frequency clamps to 0.01 Hz minimum."""
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_frequency(0.0)
        assert lfo.rate == 0.01, f"Rate should clamp to 0.01, got {lfo.rate}"

        lfo.set_frequency(-5.0)
        assert lfo.rate == 0.01


# ============================================================================
# WAVEFORM INT MAPPING
# ============================================================================


@pytest.mark.unit
class TestWaveformMapping:
    """Verify waveform string-to-int mapping."""

    def test_all_waveforms_accepted(self):
        """All supported waveform strings are valid and produce output."""
        sr = 48000
        for wf in [
            "sine",
            "triangle",
            "square",
            "sawtooth",
            "sample_and_hold",
            "random_sh",
            "trapezoid",
        ]:
            lfo = make_lfo(
                id=0, waveform=wf, rate=5.0, depth=1.0, delay=0.0,
                sample_rate=sr, block_size=1024,
            )
            assert lfo.waveform == wf, f"Waveform '{wf}' not accepted"
            # Verify waveform_int matches
            int_map = {
                "sine": 0,
                "triangle": 1,
                "square": 2,
                "sawtooth": 3,
                "sample_and_hold": 4,
                "random_sh": 5,
                "trapezoid": 6,
            }
            assert lfo.waveform_int == int_map[wf], (
                f"waveform_int mismatch for '{wf}'"
            )

    def test_invalid_waveform_defaults_to_sine(self):
        """Invalid waveform defaults to 'sine'."""
        lfo = make_lfo(
            id=0, waveform="invalid_waveform", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        assert lfo.waveform == "sine", (
            f"Invalid waveform should default to 'sine', got '{lfo.waveform}'"
        )


# ============================================================================
# SET_PARAMETERS
# ============================================================================


@pytest.mark.unit
class TestSetParameters:
    """Verify set_parameters updates multiple params and resets state."""

    def test_set_parameters_no_reset(self):
        """set_parameters with waveform-only should not reset phase."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        phase_before = lfo.phase
        assert phase_before != 0.0

        lfo.set_parameters(waveform="triangle")
        # phase should NOT be reset (waveform-only change)
        assert lfo.waveform == "triangle"
        assert lfo.phase == phase_before

    def test_set_parameters_with_rate_resets(self):
        """set_parameters with rate should reset phase."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert lfo.phase != 0.0

        lfo.set_parameters(rate=2.0)
        assert lfo.phase == 0.0, "set_parameters with rate should reset phase"
        assert lfo.rate == 2.0

    def test_set_parameters_with_delay_resets(self):
        """set_parameters with delay should reset phase."""
        sr = 48000
        lfo = make_lfo(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert lfo.delay_counter != 0

        lfo.set_parameters(delay=0.5)
        assert lfo.delay_counter == 0, "set_parameters with delay should reset"
        assert lfo.delay == 0.5


# ============================================================================
# MODULATION ROUTING
# ============================================================================


@pytest.mark.unit
class TestModulationRouting:
    """Verify set_modulation_routing sets routing flags."""

    def test_default_routing(self):
        """LFO1 should default to pitch modulation."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        assert lfo.modulates_pitch is True
        assert lfo.modulates_filter is False
        assert lfo.modulates_amplitude is False

    def test_set_all_routes(self):
        """Verify set_modulation_routing sets all flags."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_modulation_routing(
            pitch=True, filter=True, amplitude=True,
            pan=True, pwm=True, fm_amount=True,
        )
        assert lfo.modulates_pitch is True
        assert lfo.modulates_filter is True
        assert lfo.modulates_amplitude is True
        assert lfo.modulates_pan is True
        assert lfo.modulates_pwm is True
        assert lfo.modulates_fm_amount is True

    def test_clear_all_routes(self):
        """LFO2/3 (id=1,2) should not default to pitch modulation."""
        for lfo_id in (1, 2):
            lfo = UltraFastXGLFO(
                id=lfo_id, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
                sample_rate=48000, block_size=1024,
            )
            assert lfo.modulates_pitch is False, (
                f"LFO{1 + lfo_id} should not default to pitch modulation"
            )


# ============================================================================
# PITCH MODULATION PARAMETERS
# ============================================================================


@pytest.mark.unit
class TestPitchModulation:
    """Verify set_pitch_modulation parameters."""

    def test_set_pitch_modulation(self):
        """Verify pitch modulation params are set and clamped."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_pitch_modulation(delay=1.0, fade_in=0.5, depth=200)
        assert lfo.pitch_delay == pytest.approx(1.0)
        assert lfo.pitch_fade_in == pytest.approx(0.5)
        assert lfo.pitch_depth == 200

    def test_pitch_modulation_clamping(self):
        """Verify pitch params are clamped to valid ranges."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_pitch_modulation(delay=10.0, fade_in=10.0, depth=1000)
        assert lfo.pitch_delay == pytest.approx(5.0)
        assert lfo.pitch_fade_in == pytest.approx(5.0)
        assert lfo.pitch_depth == 600


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Verify edge cases and boundary conditions."""

    def test_min_rate(self):
        """Rate clamps to 0.1 Hz minimum."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=0.01, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        assert lfo.rate == 0.1, f"Min rate should be 0.1, got {lfo.rate}"

    def test_max_rate(self):
        """Rate clamps to 200 Hz maximum."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=500.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        assert lfo.rate == 200.0, f"Max rate should be 200, got {lfo.rate}"

    def test_depth_zero_max_rate(self):
        """Depth=0 at max rate still produces output (zeros)."""
        sr = 48000
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=200.0, depth=0.0, delay=0.0,
            sample_rate=sr, block_size=1024,
        )
        buf = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buf, 1024)
        assert np.all(buf == 0.0)

    def test_differing_block_sizes(self):
        """LFO works correctly with different block sizes."""
        sr = 48000
        for bs in [64, 256, 1024, 4096]:
            lfo = make_lfo(
                id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
                sample_rate=sr, block_size=bs,
            )
            n = bs * 4  # 4 blocks worth
            samples = generate_lfo_blocks(lfo, n)
            assert len(samples) == n
            crossings = find_zero_crossings(samples)
            if len(crossings) >= 2:
                period = (crossings[-1] - crossings[0]) / (len(crossings) - 1)
                expected = sr / 5.0
                error_pct = abs(period - expected) / expected * 100
                assert error_pct < 10.0, (
                    f"Block size {bs}: period error {error_pct:.2f}%"
                )


# ============================================================================
# CONTROLLER SETTERS
# ============================================================================


@pytest.mark.unit
class TestControllerSetters:
    """Verify XG controller setters clamp values."""

    def test_breath_controller(self):
        """breath controller clamps to 0-1."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_breath_controller(2.0)
        assert lfo.breath_controller == 1.0

        lfo.set_breath_controller(-1.0)
        assert lfo.breath_controller == 0.0

    def test_foot_controller(self):
        """foot controller clamps to 0-1."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_foot_controller(0.5)
        assert lfo.foot_controller == 0.5

    def test_channel_aftertouch(self):
        """channel aftertouch clamps to 0-1."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_channel_aftertouch(1.5)
        assert lfo.channel_aftertouch == 1.0

    def test_key_aftertouch(self):
        """key aftertouch clamps to 0-1."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_key_aftertouch(0.75)
        assert lfo.key_aftertouch == 0.75

    def test_brightness(self):
        """brightness clamps to 0-127."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_brightness(200)
        assert lfo.brightness == 127

        lfo.set_brightness(-10)
        assert lfo.brightness == 0


# ============================================================================
# JUPITER-X FEATURES
# ============================================================================


@pytest.mark.unit
class TestJupiterXFeatures:
    """Verify Jupiter-X specific LFO features."""

    def test_get_jupiter_x_lfo_info(self):
        """get_jupiter_x_lfo_info returns expected keys."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        info = lfo.get_jupiter_x_lfo_info()
        assert "phase_offset_degrees" in info
        assert "fade_in_time_seconds" in info
        assert "fade_in_samples" in info
        assert "key_sync_enabled" in info
        assert "current_phase_radians" in info
        assert info["jupiter_x_compatible"] is True

    def test_set_phase_offset_boundary(self):
        """Phase offset clamps to 0-360."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_phase_offset(400.0)
        assert lfo.phase_offset == 360.0

        lfo.set_phase_offset(-90.0)
        assert lfo.phase_offset == 0.0

        lfo.set_phase_offset(180.0)
        assert lfo.phase_offset == 180.0


# ============================================================================
# MODULATION DEPTHS
# ============================================================================


@pytest.mark.unit
class TestModulationDepths:
    """Verify set_modulation_depths."""

    def test_set_modulation_depths(self):
        """set_modulation_depths stores all depths."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        lfo.set_modulation_depths(
            pitch_cents=100.0, filter_depth=0.5, amplitude_depth=0.25,
        )
        assert lfo.pitch_depth_cents == 100.0
        assert lfo.filter_depth == 0.5
        assert lfo.amplitude_depth == 0.25


# ============================================================================
# STEP METHOD (BACKWARD COMPAT)
# ============================================================================


@pytest.mark.unit
class TestStepMethod:
    """Verify step() backward compatibility."""

    def test_step_returns_float(self):
        """step() returns a float value."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        val = lfo.step()
        assert isinstance(val, float)

    def test_step_advances_phase(self):
        """step() advances the internal phase."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
            sample_rate=48000, block_size=1024,
        )
        phase_before = lfo.phase
        lfo.step()
        assert lfo.phase != phase_before, "step() should advance phase"
