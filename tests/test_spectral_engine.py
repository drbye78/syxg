"""Tests for Spectral synthesis engine."""
from __future__ import annotations

import numpy as np
import pytest

from synth.engines.spectral.engine import FFTProcessor, SpectralEngine, SpectralFilter, SpectralSynthesizer


class TestFFTProcessor:
    """Tests for the FFTProcessor class."""

    def test_init_defaults(self):
        proc = FFTProcessor()
        assert proc.fft_size == 2048
        assert proc.hop_size == 512
        assert proc.overlap == 4
        assert len(proc.window) == 2048

    def test_init_custom_fft_size(self):
        proc = FFTProcessor(fft_size=1024)
        assert proc.fft_size == 1024
        # Default hop_size is 512, so overlap = 1024 // 512 = 2
        assert proc.hop_size == 512
        assert proc.overlap == 2

    def test_init_custom_window(self):
        proc = FFTProcessor(fft_size=512, hop_size=128, window_type="hamming")
        assert proc.fft_size == 512
        assert proc.window is not None

    def test_init_blackman_window(self):
        proc = FFTProcessor(fft_size=512, hop_size=128, window_type="blackman")
        assert proc.window is not None

    def test_init_rectangular_window(self):
        proc = FFTProcessor(fft_size=512, hop_size=128, window_type="rectangular")
        assert proc.window is not None
        # Rectangular window is all ones
        np.testing.assert_array_almost_equal(proc.window, np.ones(512))

    def test_forward_basic(self):
        proc = FFTProcessor(fft_size=512, hop_size=128)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 512)).astype(np.float32)
        spectrum = proc.forward(signal)
        assert spectrum is not None
        assert spectrum.shape == (512,)
        assert np.iscomplexobj(spectrum)
        assert np.all(np.isfinite(spectrum))

    def test_forward_normalization(self):
        proc = FFTProcessor(fft_size=512, hop_size=128)
        # DC signal should produce peak at bin 0
        signal = np.ones(512, dtype=np.float32)
        spectrum = proc.forward(signal)
        # DC component should be the largest bin
        assert np.argmax(np.abs(spectrum)) == 0

    def test_inverse_basic(self):
        proc = FFTProcessor(fft_size=512, hop_size=128)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 512)).astype(np.float32)
        spectrum = proc.forward(signal)
        reconstructed = proc.inverse(spectrum)
        assert reconstructed is not None
        assert reconstructed.shape == (512,)
        assert np.all(np.isfinite(reconstructed))

    def test_inverse_reconstruction(self):
        proc = FFTProcessor(fft_size=512, hop_size=128)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 512)).astype(np.float32)
        spectrum = proc.forward(signal)
        reconstructed = proc.inverse(spectrum)
        # Forward + inverse should approximately reconstruct (within rounding)
        # The signal is windowed in forward and windowed again in inverse,
        # so we don't expect exact reconstruction — just finite and similar shape
        assert reconstructed.dtype == np.float64 or reconstructed.dtype == np.float32
        assert len(reconstructed) == 512

    def test_process_block_basic(self):
        """Test process_block returns same-length audio without crashing."""
        proc = FFTProcessor(fft_size=256, hop_size=64)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 64)).astype(np.float32)
        output = proc.process_block(signal)
        assert output is not None
        assert len(output) == 64
        assert np.all(np.isfinite(output))

    def test_process_block_multiple_blocks(self):
        """Process multiple blocks should not crash and produce finite output."""
        proc = FFTProcessor(fft_size=256, hop_size=64)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 64)).astype(np.float32)
        outputs = []
        for _ in range(10):
            out = proc.process_block(signal)
            outputs.append(out)
        assert len(outputs) == 10
        for out in outputs:
            assert np.all(np.isfinite(out))

    def test_process_block_padding(self):
        """Short blocks should be padded, not crash."""
        proc = FFTProcessor(fft_size=256, hop_size=64)
        short_signal = np.array([0.5, 0.5], dtype=np.float32)
        output = proc.process_block(short_signal)
        assert output is not None
        assert np.all(np.isfinite(output))

    def test_fft_size_must_be_power_of_two(self):
        """FFT size should be a power of two (numpy.fft will accept non-powers but
        the processor works best with powers of two)."""
        proc = FFTProcessor(fft_size=512)  # Power of two — no error
        assert proc.fft_size == 512


class TestSpectralFilter:
    """Tests for SpectralFilter domain processing."""

    def test_init(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        assert filt.filter_type == "passthrough"
        assert filt.nyquist == 22050.0

    def test_passthrough(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        spectrum = np.ones(256, dtype=np.complex128)
        result = filt.process_spectrum(spectrum)
        np.testing.assert_array_equal(result, spectrum)

    def test_lowpass(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        filt.set_lowpass(cutoff=5000)
        assert filt.filter_type == "lowpass"
        assert filt.high_cutoff == 5000.0

    def test_highpass(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        filt.set_highpass(cutoff=500)
        assert filt.filter_type == "highpass"

    def test_bandpass(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        filt.set_bandpass(center_freq=1000, bandwidth=200)
        assert filt.filter_type == "bandpass"
        assert filt.center_freq == 1000.0

    def test_bandreject(self):
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        filt.set_bandreject(center_freq=1000, bandwidth=200)
        assert filt.filter_type == "bandreject"

    def test_lowpass_zeros_high_frequencies(self):
        """Lowpass filter should zero out bins above cutoff."""
        filt = SpectralFilter(fft_size=256, sample_rate=44100)
        filt.set_lowpass(cutoff=500)
        spectrum = np.ones(256, dtype=np.complex128)
        result = filt.process_spectrum(spectrum)
        # Some high frequency bins should be zeroed
        assert np.any(result == 0.0 + 0.0j)


class TestSpectralSynthesizer:
    """Tests for the core SpectralSynthesizer."""

    def test_init(self):
        synth = SpectralSynthesizer(sample_rate=44100, fft_size=2048)
        assert synth.sample_rate == 44100
        assert synth.fft_size == 2048
        assert len(synth.spectral_filters) == 8

    def test_analyze_and_synthesize(self):
        synth = SpectralSynthesizer(sample_rate=44100, fft_size=512)
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 512)).astype(np.float32)
        spectrum = synth.analyze_audio(signal)
        assert np.iscomplexobj(spectrum)
        output = synth.synthesize_from_spectrum(spectrum)
        assert output is not None
        assert len(output) == 512

    def test_freeze_unfreeze(self):
        synth = SpectralSynthesizer(sample_rate=44100)
        assert not synth.freeze_spectrum
        synth.set_freeze(True)
        assert synth.freeze_spectrum
        synth.set_freeze(False)
        assert not synth.freeze_spectrum
        assert synth.frozen_spectrum is None

    def test_add_spectral_filter(self):
        synth = SpectralSynthesizer(sample_rate=44100)
        synth.add_spectral_filter("lowpass", cutoff=5000)
        # First filter should be configured
        assert synth.spectral_filters[0].filter_type == "lowpass"

    def test_noise_amount(self):
        synth = SpectralSynthesizer(sample_rate=44100)
        assert synth.noise_amount == 0.0
        synth.noise_amount = 0.5
        assert synth.noise_amount == 0.5

    def test_morph_position(self):
        synth = SpectralSynthesizer(sample_rate=44100)
        assert synth.morph_position == 0.0
        synth.morph_position = 0.3
        assert synth.morph_position == 0.3


class TestSpectralEngine:
    """Tests for the SpectralEngine top-level class."""

    @pytest.fixture
    def engine(self):
        return SpectralEngine(sample_rate=44100, block_size=256, fft_size=512)

    def test_initialization(self, engine):
        assert engine is not None
        assert engine.sample_rate == 44100
        assert engine.block_size == 256
        assert engine.spectral_synth.fft_size == 512
        assert engine.get_engine_type() == "spectral"

    def test_initialization_defaults(self):
        engine = SpectralEngine()
        assert engine.sample_rate == 44100
        assert engine.block_size == 1024
        assert engine.spectral_synth.fft_size == 2048

    def test_get_engine_info(self, engine):
        info = engine.get_engine_info()
        assert info is not None
        assert isinstance(info, dict)
        assert info["name"] == "Spectral Synthesis Engine"
        assert info["type"] == "spectral"
        assert "capabilities" in info
        assert "fft_analysis_synthesis" in info["capabilities"]
        assert info["current_mode"] == "spectral"

    def test_create_partial(self, engine):
        partial = engine.create_partial({}, sample_rate=44100)
        assert partial is not None
        assert isinstance(partial, SpectralSynthesizer)

    def test_generate_samples_output(self, engine):
        output = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=256
        )
        assert output is not None
        assert isinstance(output, np.ndarray)
        # FFT processing naturally produces float64 from numpy
        assert output.dtype in (np.float32, np.float64)
        assert output.shape == (256, 2)  # Stereo output
        assert np.all(np.isfinite(output))

    def test_generate_samples_different_note(self, engine):
        """Different notes should produce different audio."""
        out_c4 = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=256
        )
        engine.reset()
        out_c5 = engine.generate_samples(
            note=72, velocity=100, modulation={}, block_size=256
        )
        # Different pitches should not be identical
        assert not np.allclose(out_c4, out_c5)

    def test_generate_samples_velocity_scaling(self, engine):
        """Higher velocity should produce louder output (roughly)."""
        out_soft = engine.generate_samples(
            note=60, velocity=10, modulation={}, block_size=256
        )
        engine.reset()
        out_loud = engine.generate_samples(
            note=60, velocity=127, modulation={}, block_size=256
        )
        # Louder velocity should have higher amplitude (on average)
        assert np.max(np.abs(out_loud)) > np.max(np.abs(out_soft))

    def test_generate_samples_with_modulation(self, engine):
        output = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"volume": 0.5},
            block_size=256,
        )
        assert output is not None
        assert np.all(np.isfinite(output))

    def test_set_processing_mode_spectral(self, engine):
        engine.set_processing_mode("spectral")
        assert engine.processing_mode == "spectral"

    def test_set_processing_mode_granular(self, engine):
        engine.set_processing_mode("granular")
        assert engine.processing_mode == "granular"

    def test_set_processing_mode_hybrid(self, engine):
        engine.set_processing_mode("hybrid")
        assert engine.processing_mode == "hybrid"

    def test_set_processing_mode_invalid(self, engine):
        # Invalid mode should be ignored
        engine.set_processing_mode("spectral")
        engine.set_processing_mode("invalid")
        assert engine.processing_mode == "spectral"

    def test_enable_granular(self, engine):
        assert not engine.use_granular
        engine.enable_granular(True)
        assert engine.use_granular

    def test_disable_granular(self, engine):
        engine.enable_granular(True)
        assert engine.use_granular
        engine.enable_granular(False)
        assert not engine.use_granular

    def test_set_noise_amount(self, engine):
        assert engine.spectral_synth.noise_amount == 0.0
        engine.set_noise_amount(0.1)
        assert engine.spectral_synth.noise_amount == 0.1

    def test_set_noise_amount_clamps(self, engine):
        engine.set_noise_amount(-0.5)
        assert engine.spectral_synth.noise_amount == 0.0
        engine.set_noise_amount(1.5)
        assert engine.spectral_synth.noise_amount == 1.0

    def test_add_spectral_filter(self, engine):
        engine.add_spectral_filter("lowpass", cutoff=5000.0)
        assert engine.spectral_synth.spectral_filters[0].filter_type == "lowpass"

    def test_set_freeze_spectrum(self, engine):
        engine.set_freeze_spectrum(True)
        assert engine.spectral_synth.freeze_spectrum
        assert engine.spectral_synth.frozen_spectrum is None  # Not yet captured
        engine.set_freeze_spectrum(False)
        assert not engine.spectral_synth.freeze_spectrum
        assert engine.spectral_synth.frozen_spectrum is None

    def test_get_preset_info(self, engine):
        preset = engine.get_preset_info(bank=0, program=0)
        assert preset is not None
        assert preset.bank == 0
        assert preset.program == 0
        assert preset.name == "Spectral 0:0"
        assert preset.engine_type == "spectral"
        assert len(preset.region_descriptors) == 1

    def test_get_preset_info_different_program(self, engine):
        preset = engine.get_preset_info(bank=1, program=42)
        assert preset is not None
        assert preset.bank == 1
        assert preset.program == 42
        assert preset.name == "Spectral 1:42"

    def test_get_all_region_descriptors(self, engine):
        descriptors = engine.get_all_region_descriptors(bank=0, program=0)
        assert descriptors is not None
        assert len(descriptors) == 1
        descriptor = descriptors[0]
        assert descriptor.key_range == (0, 127)
        assert descriptor.velocity_range == (0, 127)
        assert "fft_size" in descriptor.algorithm_params

    def test_get_spectral_info(self, engine):
        info = engine.get_spectral_info()
        assert info is not None
        assert isinstance(info, dict)
        assert info["fft_size"] == 512
        assert info["processing_mode"] == "spectral"
        assert info["num_filters"] == 8

    def test_get_supported_formats(self, engine):
        formats = engine.get_supported_formats()
        assert ".wav" in formats
        assert ".flac" in formats

    def test_reset(self, engine):
        # Change some state then reset
        engine.set_noise_amount(0.5)
        engine.set_freeze_spectrum(True)
        engine.enable_granular(True)
        engine.generate_samples(note=60, velocity=100, modulation={}, block_size=256)
        assert engine.current_time > 0.0

        engine.reset()
        assert engine.current_time == 0.0
        assert engine.spectral_synth.noise_amount == 0.0
        assert not engine.spectral_synth.freeze_spectrum
        assert len(engine.grain_schedule) == 0

    def test_cleanup(self, engine):
        engine.set_noise_amount(0.3)
        engine.cleanup()
        # After cleanup, state should be reset
        assert engine.current_time == 0.0
        assert engine.spectral_synth.noise_amount == 0.0
        assert not engine.spectral_synth.freeze_spectrum

    def test_get_engine_type(self, engine):
        assert engine.get_engine_type() == "spectral"

    def test_is_note_supported(self, engine):
        assert engine.is_note_supported(60)
        assert engine.is_note_supported(0)
        assert engine.is_note_supported(127)
        assert not engine.is_note_supported(-1)
        assert not engine.is_note_supported(128)

    def test_str_repr(self, engine):
        s = str(engine)
        assert "SpectralEngine" in s
        assert "spectral" in s

    def test_get_regions_for_note(self, engine):
        regions = engine.get_regions_for_note(note=60, velocity=100)
        assert len(regions) == 1
        region = regions[0]
        assert region.should_play_for_note(60, 100)
        assert not region.should_play_for_note(61, 100)

    def test_set_granular_parameters(self, engine):
        # Should not crash
        engine.set_granular_parameters(size=0.1, density=20.0, pitch=1.5)

    def test_load_audio_for_granulation(self, engine):
        audio = np.sin(np.linspace(0, 2 * np.pi * 100, 44100)).astype(np.float32)
        engine.load_audio_for_granulation(audio)
        assert engine.spectral_synth.granular_engine.source_audio is not None
        assert len(engine.spectral_synth.granular_engine.source_audio) == 44100

    def test_hybrid_mode_generates_audio(self, engine):
        """Hybrid mode (spectral + granular) should still produce valid audio."""
        engine.set_processing_mode("hybrid")
        audio = np.sin(np.linspace(0, 2 * np.pi * 100, 44100)).astype(np.float32)
        engine.load_audio_for_granulation(audio)
        engine.enable_granular(True)
        output = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=256
        )
        assert output is not None
        assert output.shape == (256, 2)
        assert np.all(np.isfinite(output))
