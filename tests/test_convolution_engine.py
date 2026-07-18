"""Tests for Convolution reverb engine."""
from __future__ import annotations

import numpy as np
import pytest


class TestImpulseResponse:
    def test_create_from_array(self):
        from synth.engines.convolution.engine import ImpulseResponse

        ir = ImpulseResponse(
            audio_data=np.sin(np.linspace(0, 2 * np.pi, 256)).astype(np.float32),
            sample_rate=44100,
        )
        assert ir is not None
        assert len(ir.audio_data) == 256

    def test_get_decay_time(self):
        from synth.engines.convolution.engine import ImpulseResponse

        # Decaying exponential IR
        t = np.linspace(0, 1, 44100)
        ir_data = np.exp(-t * 10).astype(np.float32)
        ir = ImpulseResponse(audio_data=ir_data, sample_rate=44100)
        rt60 = ir.get_decay_time()
        assert rt60 > 0

    def test_normalize(self):
        from synth.engines.convolution.engine import ImpulseResponse

        ir = ImpulseResponse(
            audio_data=np.sin(np.linspace(0, 2 * np.pi, 256)).astype(np.float32),
            sample_rate=44100,
        )
        normalized = ir.normalize()
        assert normalized is not None
        assert normalized.dtype == np.float32

    def test_get_info(self):
        from synth.engines.convolution.engine import ImpulseResponse

        ir = ImpulseResponse(
            audio_data=np.sin(np.linspace(0, 2 * np.pi, 256)).astype(np.float32),
            sample_rate=44100,
            name="test_ir",
        )
        info = ir.get_info()
        assert info["name"] == "test_ir"
        assert info["sample_rate"] == 44100
        assert info["length"] == 256


class TestConvolutionProcessor:
    def test_init(self):
        from synth.engines.convolution.engine import ConvolutionProcessor

        proc = ConvolutionProcessor(max_ir_length=65536, block_size=1024)
        assert proc is not None

    def test_process_block(self):
        from synth.engines.convolution.engine import ConvolutionProcessor

        proc = ConvolutionProcessor(max_ir_length=256, block_size=64)
        # Load a simple IR
        ir = np.array([1.0, 0.5, 0.25, 0.125], dtype=np.float32)
        proc.load_impulse_response(ir)
        # Process a block
        signal = np.sin(np.linspace(0, 2 * np.pi * 2, 64)).astype(np.float32)
        output = proc.process_block(signal)
        assert output is not None
        assert len(output) == 64
        assert np.all(np.isfinite(output))

    def test_process_block_no_ir_returns_copy(self):
        from synth.engines.convolution.engine import ConvolutionProcessor

        proc = ConvolutionProcessor(max_ir_length=256, block_size=64)
        signal = np.sin(np.linspace(0, 2 * np.pi * 2, 64)).astype(np.float32)
        output = proc.process_block(signal)
        np.testing.assert_array_equal(output, signal)

    def test_reset(self):
        from synth.engines.convolution.engine import ConvolutionProcessor

        proc = ConvolutionProcessor(max_ir_length=256, block_size=64)
        proc.reset()  # Must not crash

    def test_get_latency(self):
        from synth.engines.convolution.engine import ConvolutionProcessor

        proc = ConvolutionProcessor(max_ir_length=256, block_size=128)
        assert proc.get_latency() == 128


class TestReverbPreset:
    def test_create_algorithmic_reverb(self):
        from synth.engines.convolution.engine import ReverbPreset

        preset = ReverbPreset.create_algorithmic_reverb(
            name="test_hall", room_size=0.5, decay_time=2.0, sample_rate=44100
        )
        assert preset is not None
        assert preset.name == "test_hall"
        assert preset.impulse_response is not None
        assert preset.impulse_response.length > 0

    def test_init_directly(self):
        from synth.engines.convolution.engine import ReverbPreset

        ir_data = np.sin(np.linspace(0, 2 * np.pi, 256)).astype(np.float32)
        preset = ReverbPreset(name="direct", ir_data=ir_data, sample_rate=44100)
        assert preset.name == "direct"
        assert preset.wet_level == 0.3
        assert preset.dry_level == 0.7

    def test_get_info(self):
        from synth.engines.convolution.engine import ReverbPreset

        preset = ReverbPreset.create_algorithmic_reverb(
            name="test_info", room_size=0.5, decay_time=2.0
        )
        info = preset.get_info()
        assert info["name"] == "test_info"
        assert "wet_level" in info
        assert "dry_level" in info
        assert "ir_info" in info


class TestConvolutionReverbEngine:
    @pytest.fixture
    def engine(self):
        from synth.engines.convolution.engine import ConvolutionReverbEngine

        return ConvolutionReverbEngine(sample_rate=44100, block_size=1024)

    def test_initialization(self, engine):
        assert engine is not None
        assert engine.sample_rate == 44100
        assert engine.block_size == 1024

    def test_get_engine_info(self, engine):
        info = engine.get_engine_info()
        assert info is not None
        assert isinstance(info, dict)
        assert info["type"] == "convolution_reverb"
        assert "capabilities" in info
        assert "parameters" in info

    def test_get_preset_info(self, engine):
        # get_preset_info requires bank and program arguments
        info = engine.get_preset_info(bank=0, program=0)
        assert info is not None

    def test_get_engine_type(self, engine):
        assert engine.get_engine_type() == "convolution_reverb"

    def test_process_audio_mono(self, engine):
        engine.load_preset("small_room")
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 256)).astype(np.float32)
        output = engine.process_audio(signal)
        assert output is not None
        assert len(output) == 256
        assert np.all(np.isfinite(output))

    def test_process_audio_stereo(self, engine):
        engine.load_preset("small_room")
        signal = np.column_stack(
            [
                np.sin(np.linspace(0, 2 * np.pi * 4, 256)).astype(np.float32),
                np.cos(np.linspace(0, 2 * np.pi * 4, 256)).astype(np.float32),
            ]
        )
        output = engine.process_audio(signal)
        assert output is not None
        assert output.shape == (256, 2)
        assert np.all(np.isfinite(output))

    def test_process_audio_no_preset(self, engine):
        # Without a preset loaded, process_audio returns a copy
        signal = np.sin(np.linspace(0, 2 * np.pi * 4, 256)).astype(np.float32)
        output = engine.process_audio(signal)
        np.testing.assert_array_equal(output, signal)

    def test_load_preset(self, engine):
        result = engine.load_preset("small_room")
        assert result is True
        assert engine.current_preset is not None

    def test_load_preset_invalid(self, engine):
        result = engine.load_preset("nonexistent_preset")
        assert result is False

    def test_set_parameters(self, engine):
        engine.set_parameters(wet_level=0.5, dry_level=0.3)
        assert engine.wet_level == 0.5
        assert engine.dry_level == 0.3

    def test_set_parameters_clamps(self, engine):
        engine.set_parameters(wet_level=2.0)  # Should clamp to 1.0
        assert engine.wet_level == 1.0

    def test_get_available_presets(self, engine):
        presets = engine.get_available_presets()
        assert isinstance(presets, list)
        assert "small_room" in presets
        assert "large_hall" in presets

    def test_get_preset_details(self, engine):
        details = engine.get_preset_details("chamber")
        assert details is not None
        assert details["name"] == "Chamber"

    def test_get_preset_details_invalid(self, engine):
        details = engine.get_preset_details("nonexistent")
        assert details is None

    def test_load_impulse_response(self, engine):
        ir_data = np.sin(np.linspace(0, 2 * np.pi, 256)).astype(np.float32)
        result = engine.load_impulse_response(ir_data, name="custom_test")
        assert result is True

    def test_reset(self, engine):
        engine.load_preset("small_room")
        engine.reset()
        # After reset, no current preset
        assert engine.current_preset is not None  # reset doesn't clear preset, just buffers

    def test_cleanup(self, engine):
        engine.cleanup()  # Must not crash

    def test_get_supported_formats(self, engine):
        formats = engine.get_supported_formats()
        assert isinstance(formats, list)
        assert ".wav" in formats

    def test_is_note_supported(self, engine):
        assert engine.is_note_supported(60) is True

    def test_get_regions_for_note(self, engine):
        regions = engine.get_regions_for_note(note=60, velocity=100)
        assert regions == []

    def test_generate_samples(self, engine):
        samples = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=64
        )
        assert samples.shape == (64, 2)

    def test_create_partial(self, engine):
        result = engine.create_partial(partial_params={}, sample_rate=44100)
        assert result is None

    def test_str_repr(self, engine):
        s = str(engine)
        assert "ConvolutionReverbEngine" in s
        engine.load_preset("chamber")
        assert "Chamber" in str(engine)
