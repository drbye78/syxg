"""Tests for synth.sampling module data types and key methods."""

from __future__ import annotations

import pytest

from synth.sampling.sample_manager import (
    Keygroup,
    SampleFormat,
    SampleMetadata,
    SampleQuality,
)
from synth.sampling.sample_formats import SampleFormatHandler


# ── SampleFormat / SampleQuality enum tests ──────────────────────────────


class TestSampleFormat:
    @pytest.mark.unit
    def test_sample_format_values(self):
        assert SampleFormat.WAV.value == "wav"
        assert SampleFormat.AIFF.value == "aiff"
        assert SampleFormat.FLAC.value == "flac"
        assert SampleFormat.OGG.value == "ogg"
        assert SampleFormat.MP3.value == "mp3"

    @pytest.mark.unit
    def test_sample_quality_values(self):
        assert SampleQuality.COMPRESSED.value == "compressed"
        assert SampleQuality.STANDARD.value == "standard"
        assert SampleQuality.HIGH.value == "high"
        assert SampleQuality.LOSSLESS.value == "lossless"


# ── SampleMetadata tests ────────────────────────────────────────────────


class TestSampleMetadata:
    @pytest.mark.unit
    def test_sample_metadata_defaults(self):
        meta = SampleMetadata(
            name="test",
            format=SampleFormat.WAV,
            sample_rate=44100,
            bit_depth=16,
            channels=2,
            length_samples=1000,
            duration_seconds=0.023,
        )
        assert meta.name == "test"
        assert meta.format == SampleFormat.WAV
        assert meta.sample_rate == 44100
        assert meta.bit_depth == 16
        assert meta.channels == 2
        assert meta.length_samples == 1000
        assert meta.duration_seconds == 0.023

    @pytest.mark.unit
    def test_sample_metadata_all_fields(self):
        meta = SampleMetadata(
            name="full_test",
            format=SampleFormat.FLAC,
            sample_rate=48000,
            bit_depth=24,
            channels=1,
            length_samples=48000,
            duration_seconds=1.0,
            file_path="/tmp/test.flac",
            file_size_bytes=123456,
            checksum="abc123",
            quality=SampleQuality.LOSSLESS,
            loop_start=0,
            loop_end=48000,
            root_note=69,
            fine_tune=5,
            volume=0.8,
            pan=-0.5,
        )
        assert meta.name == "full_test"
        assert meta.format == SampleFormat.FLAC
        assert meta.sample_rate == 48000
        assert meta.bit_depth == 24
        assert meta.channels == 1
        assert meta.length_samples == 48000
        assert meta.duration_seconds == 1.0
        assert meta.file_path == "/tmp/test.flac"
        assert meta.file_size_bytes == 123456
        assert meta.checksum == "abc123"
        assert meta.quality == SampleQuality.LOSSLESS
        assert meta.loop_start == 0
        assert meta.loop_end == 48000
        assert meta.root_note == 69
        assert meta.fine_tune == 5
        assert meta.volume == 0.8
        assert meta.pan == -0.5

    @pytest.mark.unit
    def test_sample_metadata_defaults_optional(self):
        meta = SampleMetadata(
            name="defaults",
            format=SampleFormat.AIFF,
            sample_rate=22050,
            bit_depth=8,
            channels=1,
            length_samples=500,
            duration_seconds=0.5,
        )
        assert meta.root_note == 60
        assert meta.volume == 1.0
        assert meta.pan == 0.0
        assert meta.file_path is None
        assert meta.file_size_bytes == 0
        assert meta.checksum is None
        assert meta.quality == SampleQuality.STANDARD
        assert meta.loop_start is None
        assert meta.loop_end is None
        assert meta.fine_tune == 0


# ── Keygroup tests ──────────────────────────────────────────────────────


class TestKeygroup:
    @pytest.mark.unit
    def test_keygroup_create(self):
        kg = Keygroup(36, 96, "s001")
        assert kg.low_note == 36
        assert kg.high_note == 96
        assert kg.sample_id == "s001"

    @pytest.mark.unit
    def test_keygroup_velocity_range(self):
        kg = Keygroup(36, 96, "s001", velocity_min=50, velocity_max=100)
        assert kg.velocity_min == 50
        assert kg.velocity_max == 100

    @pytest.mark.unit
    def test_keygroup_defaults(self):
        kg = Keygroup(0, 127, "s002")
        assert kg.velocity_min == 0
        assert kg.velocity_max == 127
        assert kg.volume == 1.0
        assert kg.pan == 0.0
        assert kg.tune_coarse == 0
        assert kg.tune_fine == 0
        assert kg.filter_cutoff is None
        assert kg.filter_resonance is None


# ── SampleFormatHandler tests ───────────────────────────────────────────


class TestSampleFormatHandler:
    @pytest.fixture
    def handler(self):
        return SampleFormatHandler()

    @pytest.mark.unit
    def test_detect_format_wav(self, handler):
        assert handler.detect_format("test.wav") == "wav"
        assert handler.detect_format("test.WAVE") == "wav"

    @pytest.mark.unit
    def test_detect_format_aiff(self, handler):
        assert handler.detect_format("test.aiff") == "aiff"
        assert handler.detect_format("test.aif") == "aiff"
        assert handler.detect_format("test.AIFF") == "aiff"

    @pytest.mark.unit
    def test_detect_format_other(self, handler):
        assert handler.detect_format("test.flac") == "flac"
        assert handler.detect_format("test.ogg") == "ogg"
        assert handler.detect_format("test.mp3") == "mp3"

    @pytest.mark.unit
    def test_detect_format_unknown(self, handler):
        assert handler.detect_format("test.xyz") is None
        assert handler.detect_format("test") is None

    @pytest.mark.unit
    def test_get_format_info_int16(self, handler):
        import numpy as np

        info = handler.get_format_info("int16")
        assert info is not None
        assert info["bits"] == 16
        assert info["signed"] is True
        assert info["numpy_dtype"] is np.int16

    @pytest.mark.unit
    def test_get_format_info_float32(self, handler):
        import numpy as np

        info = handler.get_format_info("float32")
        assert info is not None
        assert info["bits"] == 32
        assert info["numpy_dtype"] is np.float32

    @pytest.mark.unit
    def test_get_format_info_unknown(self, handler):
        assert handler.get_format_info("unknown") is None

    @pytest.mark.unit
    def test_get_supported_formats(self, handler):
        fmts = handler.get_supported_formats()
        assert "wav" in fmts
        assert "aiff" in fmts
        assert "flac" in fmts
        assert "ogg" in fmts
        assert "mp3" in fmts


# ── SampleManager tests (graceful skip if deps missing) ─────────────────


class TestSampleManager:
    @pytest.mark.unit
    def test_sample_manager_init(self):
        """SampleManager should initialise without errors."""
        try:
            from synth.sampling.sample_manager import SampleManager

            mgr = SampleManager()
            assert mgr.max_samples == 1000
            assert mgr.max_memory_mb == 512
            assert mgr.samples == {}
            assert mgr.multisamples == {}
            assert mgr.favorites == []
            assert "user" in mgr.categories
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_manager_custom_params(self):
        try:
            from synth.sampling.sample_manager import SampleManager

            mgr = SampleManager(max_samples=500, max_memory_mb=256)
            assert mgr.max_samples == 500
            assert mgr.max_memory_mb == 256
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_manager_create_keygroup_and_multisample(self):
        try:
            from synth.sampling.sample_manager import SampleManager, Keygroup

            mgr = SampleManager()
            kg = Keygroup(36, 84, "s001")
            ms_id = mgr.create_multisample("TestMS", [kg], category="piano")
            assert ms_id.startswith("ms_")
            assert mgr.multisamples[ms_id].name == "TestMS"
            assert mgr.multisamples[ms_id].category == "piano"
            assert len(mgr.multisamples[ms_id].keygroups) == 1
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_manager_get_memory_usage(self):
        try:
            from synth.sampling.sample_manager import SampleManager

            mgr = SampleManager()
            stats = mgr.get_memory_usage()
            assert stats["total_samples"] == 0
            assert stats["total_multisamples"] == 0
            assert "cache_memory_mb" in stats
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_manager_favorites(self):
        try:
            from synth.sampling.sample_manager import SampleManager

            mgr = SampleManager()
            assert mgr.add_to_favorites("nonexistent") is False
            assert mgr.remove_from_favorites("nonexistent") is False
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_manager_reset(self):
        try:
            from synth.sampling.sample_manager import SampleManager, Keygroup

            mgr = SampleManager()
            mgr.create_multisample("MS", [Keygroup(36, 96, "s001")])
            assert len(mgr.multisamples) == 1
            mgr.reset()
            assert mgr.multisamples == {}
            assert mgr.samples == {}
            assert mgr.favorites == []
        except ImportError as e:
            pytest.skip(f"SampleManager dependencies not available: {e}")


# ── SampleProcessor tests (graceful skip if deps missing) ───────────────


class TestSampleProcessor:
    @pytest.mark.unit
    def test_sample_processor_init(self):
        """SampleProcessor should initialise without errors."""
        try:
            from synth.sampling.sample_processor import SampleProcessor

            proc = SampleProcessor()
            assert proc.sample_rate == 44100
        except ImportError as e:
            pytest.skip(f"SampleProcessor dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_processor_custom_sample_rate(self):
        try:
            from synth.sampling.sample_processor import SampleProcessor

            proc = SampleProcessor(sample_rate=96000)
            assert proc.sample_rate == 96000
        except ImportError as e:
            pytest.skip(f"SampleProcessor dependencies not available: {e}")

    @pytest.mark.unit
    def test_sample_processor_get_processing_info(self):
        try:
            from synth.sampling.sample_processor import SampleProcessor

            proc = SampleProcessor()
            info = proc.get_processing_info()
            assert info["sample_rate"] == 44100
            assert info["pitch_shift_ratio"] == 1.0
            assert info["time_stretch_ratio"] == 1.0
        except ImportError as e:
            pytest.skip(f"SampleProcessor dependencies not available: {e}")
