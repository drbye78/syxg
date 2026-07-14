"""
Tests for synth.io.audio modules: writer, converter, sample_cache_manager.
"""

from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

from synth.io.audio.writer import AudioWriter


class TestAudioWriter:
    """Tests for AudioWriter — audio file writing with pyav."""

    @pytest.mark.unit
    def test_init(self) -> None:
        """Verify AudioWriter stores sample_rate and chunk_size_ms."""
        writer = AudioWriter(44100, 10.0)
        assert writer.sample_rate == 44100
        assert writer.chunk_size_ms == 10.0

    @pytest.mark.unit
    def test_supported_formats(self) -> None:
        """SUPPORTED_FORMATS dict contains all expected format keys."""
        expected = {"ogg", "wav", "mp3", "aac", "flac", "m4a"}
        assert set(AudioWriter.SUPPORTED_FORMATS.keys()) == expected

    @pytest.mark.unit
    def test_create_writer_no_av(self) -> None:
        """create_writer raises SystemExit when AvWriter instantiation fails with ImportError."""
        writer = AudioWriter(44100, 10.0)
        with mock.patch(
            "synth.io.audio.writer.AvWriter", side_effect=ImportError("PyAV not available")
        ):
            with pytest.raises(SystemExit):
                writer.create_writer("/tmp/test.wav", "wav")

    @pytest.mark.unit
    def test_write_multiple_files_empty_lists(self) -> None:
        """write_multiple_files with empty lists should not raise any exception."""
        writer = AudioWriter(44100, 10.0)

        # All lists empty
        writer.write_multiple_files([], [], [])

        # Only audio_data populated — zip stops at shortest (empty output_files)
        writer.write_multiple_files([np.zeros((1024, 2), dtype=np.float32)], [], [])

        # Only output_files / formats populated — zip yields nothing
        writer.write_multiple_files([], ["/tmp/out.wav"], ["wav"])


class TestAudioConverterImport:
    """Tests for AudioConverter (import-based, skips if heavy deps missing)."""

    @pytest.mark.unit
    def test_converter_init(self) -> None:
        """Import AudioConverter; skip gracefully if dependencies unavailable."""
        try:
            from synth.io.audio.converter import AudioConverter  # noqa: F811
        except ImportError:
            pytest.skip("AudioConverter dependencies (synthesizer, midi, xgml) not available")
        else:
            assert isinstance(AudioConverter, type)


class TestSampleCacheManager:
    """Tests for SampleCacheManager (pure numpy/stdlib, always importable)."""

    @pytest.mark.unit
    def test_cache_manager_init(self) -> None:
        """SampleCacheManager initialises with correct memory limits and zero cache."""
        from synth.io.audio.sample_cache_manager import SampleCacheManager

        mgr = SampleCacheManager(max_memory_mb=128)
        assert mgr.max_memory_mb == 128
        assert mgr.max_memory_bytes == 128 * 1024 * 1024
        assert len(mgr) == 0
        stats = mgr.get_stats()
        assert stats["cached_samples"] == 0
        assert stats["memory_used_mb"] == 0.0
        assert stats["memory_limit_mb"] == 128
