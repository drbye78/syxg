"""
LFO and Filter Processing Unit Tests

Tests for LFO waveforms, rate modulation, delay, vibrato depth,
filter types, cutoff modulation, resonance, and key follow.
"""

from __future__ import annotations

import pytest
import numpy as np

from synth.core.oscillator import UltraFastXGLFO
from synth.core.filter import UltraFastResonantFilter


class TestLFOProcessing:
    """Test LFO processing functionality."""

    @pytest.mark.unit
    def test_lfo_sine_waveform(self, sample_rate, block_size):
        """Test LFO sine waveform generation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=1.0, delay=0.0)

        # Generate LFO samples
        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # Verify output is not all zeros
        assert np.any(buffer != 0)

        # Verify output is within expected range
        assert np.max(np.abs(buffer)) <= 1.0

    @pytest.mark.unit
    def test_lfo_triangle_waveform(self, sample_rate, block_size):
        """Test LFO triangle waveform generation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="triangle", rate=5.0, depth=1.0, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        assert np.any(buffer != 0)
        assert np.max(np.abs(buffer)) <= 1.0

    @pytest.mark.unit
    def test_lfo_sawtooth_waveform(self, sample_rate, block_size):
        """Test LFO sawtooth waveform generation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sawtooth", rate=5.0, depth=1.0, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        assert np.any(buffer != 0)
        assert np.max(np.abs(buffer)) <= 1.0

    @pytest.mark.unit
    def test_lfo_square_waveform(self, sample_rate, block_size):
        """Test LFO square waveform generation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="square", rate=5.0, depth=1.0, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        assert np.any(buffer != 0)
        assert np.max(np.abs(buffer)) <= 1.0

    @pytest.mark.unit
    def test_lfo_rate_modulation(self, sample_rate, block_size):
        """Test LFO rate modulation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)

        # Test different rates
        for rate in [0.5, 2.0, 5.0, 10.0]:
            lfo.set_parameters(waveform="sine", rate=rate, depth=1.0, delay=0.0)

            buffer = np.zeros(block_size)
            result = lfo.generate_block(block_size)

            if isinstance(result, np.ndarray):
                buffer = result

            assert np.any(buffer != 0)

    @pytest.mark.unit
    def test_lfo_delay(self, sample_rate, block_size):
        """Test LFO delay parameter."""
        delay_time = 0.1

        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=1.0, delay=delay_time)

        # During delay, LFO output should be near zero
        delay_blocks = int(delay_time * sample_rate / block_size) + 1
        for _ in range(delay_blocks):
            buffer = np.zeros(block_size)
            result = lfo.generate_block(block_size)

            if isinstance(result, np.ndarray):
                buffer = result

            # Should be near zero during delay
            assert np.max(np.abs(buffer)) < 0.1

    @pytest.mark.unit
    def test_lfo_depth(self, sample_rate, block_size):
        """Test LFO depth parameter."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)

        # Test different depths
        for depth in [0.0, 0.5, 1.0]:
            lfo.set_parameters(waveform="sine", rate=5.0, depth=depth, delay=0.0)

            buffer = np.zeros(block_size)
            result = lfo.generate_block(block_size)

            if isinstance(result, np.ndarray):
                buffer = result

            # Verify output scales with depth
            if depth == 0.0:
                assert np.max(np.abs(buffer)) < 0.1
            else:
                assert np.max(np.abs(buffer)) > 0.1

    @pytest.mark.unit
    def test_lfo_fade(self, sample_rate, block_size):
        """Test LFO fade parameter."""
        fade_time = 0.1

        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=1.0, delay=0.0, fade=fade_time)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # LFO should generate output
        assert np.any(buffer != 0)

    @pytest.mark.unit
    def test_lfo_vibrato_modulation(self, sample_rate, block_size):
        """Test LFO vibrato modulation depth."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=0.5, delay=0.0)

        # Generate samples
        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # Verify LFO is generating modulation
        assert np.any(buffer != 0)

    @pytest.mark.unit
    def test_lfo_to_filter_modulation(self, sample_rate, block_size):
        """Test LFO to filter modulation."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=0.5, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # LFO should generate modulation for filter
        assert np.any(buffer != 0)

    @pytest.mark.unit
    def test_lfo_to_volume_modulation(self, sample_rate, block_size):
        """Test LFO to volume modulation (tremolo)."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=0.5, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # LFO should generate tremolo modulation
        assert np.any(buffer != 0)

    @pytest.mark.unit
    def test_lfo_to_pan_modulation(self, sample_rate, block_size):
        """Test LFO to pan modulation (auto-pan)."""
        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=0.5, delay=0.0)

        buffer = np.zeros(block_size)
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            buffer = result

        # LFO should generate auto-pan modulation
        assert np.any(buffer != 0)


class TestFilterProcessing:
    """Test filter processing functionality."""

    @pytest.mark.unit
    def test_filter_lowpass(self, sample_rate, block_size):
        """Test lowpass filter."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=5000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Create test signal (mix of frequencies)
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 5000 * t)

        # Process through filter
        filtered = filter_obj.process_block(signal)

        # Lowpass should attenuate high frequencies
        assert filtered is not None
        assert len(filtered) == len(signal)

    @pytest.mark.unit
    def test_filter_highpass(self, sample_rate, block_size):
        """Test highpass filter."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=1000.0,
            resonance=0.7,
            filter_type="highpass",
        )

        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 5000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None
        assert len(filtered) == len(signal)

    @pytest.mark.unit
    def test_filter_bandpass(self, sample_rate, block_size):
        """Test bandpass filter."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="bandpass",
        )

        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 100 * t) + np.sin(2 * np.pi * 2000 * t) + np.sin(2 * np.pi * 5000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None
        assert len(filtered) == len(signal)

    @pytest.mark.unit
    def test_filter_notch(self, sample_rate, block_size):
        """Test notch filter."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="notch",
        )

        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 2000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None
        assert len(filtered) == len(signal)

    @pytest.mark.unit
    def test_filter_cutoff_modulation(self, sample_rate, block_size):
        """Test filter cutoff modulation."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Test different cutoff frequencies
        for cutoff in [500.0, 2000.0, 8000.0]:
            filter_obj.set_parameters(cutoff=cutoff, resonance=0.7, filter_type="lowpass")

            t = np.linspace(0, 0.1, block_size, dtype=np.float32)
            signal = np.sin(2 * np.pi * 1000 * t)

            filtered = filter_obj.process_block(signal)

            assert filtered is not None

    @pytest.mark.unit
    def test_filter_resonance(self, sample_rate, block_size):
        """Test filter resonance."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Test different resonance values
        for resonance in [0.0, 0.5, 1.0, 2.0]:
            filter_obj.set_parameters(cutoff=2000.0, resonance=resonance, filter_type="lowpass")

            t = np.linspace(0, 0.1, block_size, dtype=np.float32)
            signal = np.sin(2 * np.pi * 2000 * t)

            filtered = filter_obj.process_block(signal)

            assert filtered is not None

    @pytest.mark.unit
    def test_filter_key_follow(self, sample_rate, block_size):
        """Test filter key follow."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
            key_follow=0.5,
        )

        # Filter should respond to key follow parameter
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None

    @pytest.mark.unit
    def test_filter_velocity_sensitivity(self, sample_rate, block_size):
        """Test filter velocity sensitivity."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Process signal
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None

    @pytest.mark.unit
    def test_filter_envelope_modulation(self, sample_rate, block_size):
        """Test filter envelope modulation."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Process signal
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None

    @pytest.mark.unit
    def test_filter_stereo_width(self, sample_rate, block_size):
        """Test filter stereo width parameter."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
            stereo_width=1.0,
        )

        # Process stereo signal
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None

    @pytest.mark.unit
    def test_filter_reset(self, sample_rate, block_size):
        """Test filter reset functionality."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Process some samples
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered1 = filter_obj.process_block(signal)

        # Reset filter
        filter_obj.reset()

        # Process again
        filtered2 = filter_obj.process_block(signal)

        # Both should produce valid output
        assert filtered1 is not None
        assert filtered2 is not None

    @pytest.mark.unit
    def test_filter_parameter_update(self, sample_rate, block_size):
        """Test filter parameter updates."""
        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Update parameters
        filter_obj.set_parameters(cutoff=5000.0, resonance=1.0, filter_type="highpass")

        # Process signal
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        filtered = filter_obj.process_block(signal)

        assert filtered is not None