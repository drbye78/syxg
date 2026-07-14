"""Tests for DigitalWaveguide primitive."""

from __future__ import annotations

import numpy as np
import pytest

from synth.primitives.waveguide import DigitalWaveguide


@pytest.mark.unit
class TestDigitalWaveguide:
    """Test suite for DigitalWaveguide."""

    def test_init_defaults(self):
        """Default params (44100, 44100) — verify all instance vars initialized properly."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)

        assert wg.sample_rate == 44100
        assert wg.max_delay_samples == 44100
        assert len(wg.delay_line_left) == 44100
        assert len(wg.delay_line_right) == 44100
        assert wg.delay_line_left.dtype == np.float32
        assert wg.delay_line_right.dtype == np.float32
        assert np.all(wg.delay_line_left == 0.0)
        assert np.all(wg.delay_line_right == 0.0)
        assert wg.delay_pos_left == 0
        assert wg.delay_pos_right == 0
        assert wg.delay_length_left == 44100 // 2
        assert wg.delay_length_right == 44100 // 2
        assert wg.scattering_coeff == 0.5
        assert wg.loop_filter_coeff == 0.99
        assert wg.excitation_active is False
        assert wg.excitation_samples == []
        assert wg.excitation_index == 0

    def test_init_custom(self):
        """Custom sample_rate and max_delay_samples."""
        wg = DigitalWaveguide(sample_rate=22050, max_delay_samples=10000)

        assert wg.sample_rate == 22050
        assert wg.max_delay_samples == 10000
        assert len(wg.delay_line_left) == 10000
        assert wg.delay_length_left == 5000
        assert wg.delay_length_right == 5000

    def test_set_frequency(self):
        """set_frequency(440) — delay_length ≈ 44100 / 440 = 100."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)

        expected = int(44100 / 440)  # 100
        assert wg.delay_length_left == expected
        assert wg.delay_length_right == expected

    def test_set_frequency_clamped(self):
        """Very high freq — delay_length should be at least 1."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(100000.0)

        # sample_rate / freq = 0, clamped to 1
        assert wg.delay_length_left == 1
        assert wg.delay_length_right == 1

    def test_set_frequency_very_low(self):
        """Very low freq (like 1 Hz) — delay_length clamped to max_delay_samples - 1."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(1.0)

        # int(44100 / 1) = 44100, clamped to 44100 - 1 = 44099
        assert wg.delay_length_left == 44099
        assert wg.delay_length_right == 44099

    def test_excite_pluck(self):
        """excite('pluck') — delay_line_left has non-zero values, excitation_active=True."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)

        np.random.seed(42)
        wg.excite("pluck", amplitude=1.0)

        # Delay line should have non-zero values from excitation
        assert np.any(wg.delay_line_left != 0.0)
        # It should be the noise segment at the start
        assert np.all(wg.delay_line_left[:10] != 0.0)
        assert wg.excitation_active is True
        assert len(wg.excitation_samples) > 0

    def test_excite_strike(self):
        """excite('strike') — delay_line_left[0] == amplitude."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)

        wg.excite("strike", amplitude=0.75)

        assert wg.delay_line_left[0] == 0.75
        assert wg.delay_line_right[0] == 0.75 * 0.8  # right = left * 0.8
        # Only first sample should be non-zero
        assert np.all(wg.delay_line_left[1:100] == 0.0)
        assert wg.excitation_active is True

    def test_excite_blow(self):
        """excite('blow') — delay_line_left has non-zero values."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)

        np.random.seed(42)
        wg.excite("blow", amplitude=0.5)

        assert np.any(wg.delay_line_left != 0.0)
        assert wg.excitation_active is True

    def test_process_sample_returns_float(self):
        """After excite, process_sample() returns a float."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)
        wg.excite("strike", amplitude=1.0)

        output = wg.process_sample()

        assert isinstance(output, (float, np.floating))

    def test_process_sample_output_range(self):
        """After excite, process_sample() output is within [-1.0, 1.0]."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)
        wg.excite("pluck", amplitude=1.0)

        np.random.seed(42)
        for _ in range(200):
            output = wg.process_sample()
            assert -1.0 <= output <= 1.0, f"Output {output} out of range"

    def test_is_active_after_excite(self):
        """After excite, is_active() should be True.

        Use a small max_delay_samples so a single impulse spike exceeds the
        average-energy threshold (0.001) used inside is_active().
        """
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=100)
        wg.set_frequency(440.0)
        wg.excite("strike", amplitude=1.0)

        assert wg.is_active()

    def test_is_active_after_reset(self):
        """After reset(), is_active() should be False."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)
        wg.excite("strike", amplitude=1.0)
        wg.reset()

        assert not wg.is_active()

    def test_reset_clears_state(self):
        """After excite then reset, delay lines zeroed, excitation_active=False."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(440.0)
        wg.excite("strike", amplitude=1.0)
        wg.reset()

        assert np.all(wg.delay_line_left == 0.0)
        assert np.all(wg.delay_line_right == 0.0)
        assert wg.delay_pos_left == 0
        assert wg.delay_pos_right == 0
        assert wg.excitation_active is False
        assert wg.excitation_samples == []
        assert wg.excitation_index == 0

    def test_set_parameters(self):
        """set_parameters with scattering_coeff and loop_filter_coeff."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_parameters({"scattering_coeff": 0.8, "loop_filter_coeff": 0.95})

        assert wg.scattering_coeff == 0.8
        assert wg.loop_filter_coeff == 0.95

    def test_set_parameters_with_frequency(self):
        """set_parameters({'frequency': 440}) — also sets delay_length."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_parameters({"frequency": 440.0})

        expected = int(44100 / 440)
        assert wg.delay_length_left == expected
        assert wg.delay_length_right == expected

    def test_waveguide_decay(self):
        """After excite, repeatedly call process_sample — output amplitude trends toward 0."""
        wg = DigitalWaveguide(sample_rate=44100, max_delay_samples=44100)
        wg.set_frequency(100.0)  # delay length ≈ 441

        # Use strike for a clean impulse response
        wg.excite("strike", amplitude=1.0)

        # Collect samples over several iterations
        samples: list[float] = []
        for _ in range(500):
            samples.append(wg.process_sample())

        # Max absolute amplitude in first 50 samples
        early_max = max(abs(s) for s in samples[:50])
        # Max absolute amplitude in last 50 samples
        late_max = max(abs(s) for s in samples[-50:])

        # Energy should decay, so late max should be less than early max
        assert late_max < early_max, (
            f"Expected decay: late_max={late_max} >= early_max={early_max}"
        )

        # After many iterations, amplitude should be very small
        assert late_max < 0.5, f"Late amplitude {late_max} not sufficiently decayed"
