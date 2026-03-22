"""
Test suite for SF2 file loader.

Tests RIFF parsing, chunk handling, sample data retrieval.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from synth.sf2 import sf2_file_loader

# Path to test soundfonts
TESTS_DIR = Path(__file__).parent
REF_SF2 = TESTS_DIR / "ref.sf2"


@pytest.fixture
def ref_sf2_path():
    """Get path to ref.sf2."""
    if REF_SF2.exists():
        return str(REF_SF2)
    pytest.skip("ref.sf2 not found")


class TestSF2FileLoader:
    """Tests for SF2FileLoader class."""

    def test_loader_creation(self):
        """Test file loader creation."""
        loader = sf2_file_loader.SF2FileLoader("/fake/path.sf2")

        assert loader.filepath.name == "path.sf2"
        assert loader._is_loaded is False

    @pytest.mark.slow
    def test_load_file_success(self, ref_sf2_path):
        """Test loading valid SF2 file."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        result = loader.load_file()

        assert result is True
        assert loader._is_loaded is True
        assert loader.file_size > 0

    @pytest.mark.slow
    def test_load_invalid_file(self):
        """Test loading invalid file."""
        # Create temp invalid file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
            f.write(b"NOT A VALID SF2 FILE")
            temp_path = f.name

        try:
            loader = sf2_file_loader.SF2FileLoader(temp_path)
            result = loader.load_file()
            assert result is False
        finally:
            os.unlink(temp_path)

    @pytest.mark.slow
    def test_file_info_extraction(self, ref_sf2_path):
        """Test file info extraction."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        info = loader.get_file_info()

        assert "filename" in info
        assert "file_size" in info
        assert info["file_size"] > 0

    @pytest.mark.slow
    def test_parse_preset_headers(self, ref_sf2_path):
        """Test preset header parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        presets = loader.parse_preset_headers()

        assert len(presets) > 0
        # Check first preset has required fields
        preset = presets[0]
        assert "name" in preset
        assert "program" in preset
        assert "bank" in preset

    @pytest.mark.slow
    def test_find_preset_by_bank_program(self, ref_sf2_path):
        """Test finding specific preset."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        # Find acoustic grand piano (bank 0, program 0)
        preset = loader.find_preset_by_bank_program(0, 0)

        assert preset is not None
        assert preset["bank"] == 0
        assert preset["program"] == 0

    @pytest.mark.slow
    def test_parse_instrument_headers(self, ref_sf2_path):
        """Test instrument header parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        instruments = loader.parse_instrument_headers()

        assert len(instruments) > 0
        inst = instruments[0]
        assert "name" in inst
        assert "bag_index" in inst

    @pytest.mark.slow
    def test_parse_sample_headers(self, ref_sf2_path):
        """Test sample header parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        samples = loader.parse_sample_headers()

        assert len(samples) > 0
        sample = samples[0]
        assert "name" in sample
        assert "start" in sample
        assert "end" in sample
        assert "sample_rate" in sample
        assert "original_pitch" in sample

    @pytest.mark.slow
    def test_sample_data_chunk_indexing(self, ref_sf2_path):
        """Test sample data chunks are indexed."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        # Sample data chunks should be indexed
        assert "smpl" in loader.sample_data_chunks or "LIST_sdta" in loader.sample_data_chunks

    @pytest.mark.slow
    def test_get_sample_data_16bit(self, ref_sf2_path):
        """Test retrieving 16-bit sample data."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        # Get sample header
        samples = loader.parse_sample_headers()
        if not samples:
            pytest.skip("No samples in file")

        sample = samples[0]

        # Get sample data
        data = loader.get_sample_data(sample["start"], sample["end"], is_24bit=False)

        assert data is not None
        assert len(data) > 0

    @pytest.mark.slow
    def test_bag_data_parsing(self, ref_sf2_path):
        """Test bag data parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        preset_bags = loader.get_bag_data("preset")
        inst_bags = loader.get_bag_data("instrument")

        assert len(preset_bags) > 0
        assert len(inst_bags) > 0

    @pytest.mark.slow
    def test_generator_data_parsing(self, ref_sf2_path):
        """Test generator data parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        gen_data = loader.get_generator_data("preset")

        assert len(gen_data) > 0
        # Each entry should be (gen_type, gen_amount)
        assert len(gen_data[0]) == 2

    @pytest.mark.slow
    def test_modulator_data_parsing(self, ref_sf2_path):
        """Test modulator data parsing."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        mod_data = loader.get_modulator_data("preset")

        # Modulator entries are optional
        assert isinstance(mod_data, list)

    @pytest.mark.slow
    def test_selective_parsing(self, ref_sf2_path):
        """Test selective parsing methods."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        # Parse specific preset
        preset = loader.parse_preset_header_at_index(0)
        assert preset is not None

        # Parse specific instrument
        inst = loader.parse_instrument_header_at_index(0)
        assert inst is not None

        # Parse specific sample
        sample = loader.parse_sample_header_at_index(0)
        assert sample is not None

    @pytest.mark.slow
    def test_memory_usage(self, ref_sf2_path):
        """Test memory usage reporting."""
        loader = sf2_file_loader.SF2FileLoader(ref_sf2_path)
        loader.load_file()

        memory = loader.get_memory_usage()

        assert "total_chunks" in memory
        assert "total_memory_bytes" in memory
        # Should not have loaded sample data
        assert memory["total_memory_mb"] < 100  # Much less than full file

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file fails gracefully."""
        loader = sf2_file_loader.SF2FileLoader("/nonexistent/path.sf2")
        result = loader.load_file()

        assert result is False


class TestSF2BinaryChunk:
    """Tests for SF2BinaryChunk class."""

    def test_chunk_creation(self):
        """Test chunk creation."""
        chunk = sf2_file_loader.SF2BinaryChunk("test", b"hello world", 0)

        assert chunk.chunk_id == "test"
        assert chunk.size == 11
        assert chunk.offset == 0

    def test_get_data_slice(self):
        """Test getting data slice."""
        chunk = sf2_file_loader.SF2BinaryChunk("test", b"hello world", 0)

        slice_data = chunk.get_data_slice(0, 5)
        assert slice_data == b"hello"

    def test_parse_string(self):
        """Test parsing null-terminated string."""
        chunk = sf2_file_loader.SF2BinaryChunk("test", b"hello\x00world\x00", 0)

        string = chunk.parse_string(0, 20)
        assert string == "hello"


class TestSF2ChunkIndex:
    """Tests for SF2ChunkIndex class."""

    def test_index_creation(self):
        """Test chunk index creation."""
        index = sf2_file_loader.SF2ChunkIndex()

        assert len(index.chunks) == 0

    def test_add_chunk(self):
        """Test adding chunk to index."""
        index = sf2_file_loader.SF2ChunkIndex()
        chunk = sf2_file_loader.SF2BinaryChunk("test", b"data", 0)

        index.add_chunk("test", chunk)

        assert "test" in index.chunks

    def test_add_list_subchunk(self):
        """Test adding subchunk to LIST."""
        index = sf2_file_loader.SF2ChunkIndex()
        chunk = sf2_file_loader.SF2BinaryChunk("INAM", b"data", 0)

        index.add_list_subchunk("INFO", "INAM", chunk)

        retrieved = index.get_chunk("INAM", "INFO")
        assert retrieved is not None
        assert retrieved.chunk_id == "INAM"

    def test_get_all_chunks(self):
        """Test getting all chunks."""
        index = sf2_file_loader.SF2ChunkIndex()

        chunk1 = sf2_file_loader.SF2BinaryChunk(b"t1", b"d1", 0)
        chunk2 = sf2_file_loader.SF2BinaryChunk(b"t2", b"d2", 0)

        index.add_chunk("t1", chunk1)
        index.add_chunk("t2", chunk2)

        all_chunks = index.get_all_chunks()
        assert len(all_chunks) == 2

    def test_clear(self):
        """Test clearing index."""
        index = sf2_file_loader.SF2ChunkIndex()

        chunk = sf2_file_loader.SF2BinaryChunk(b"test", b"data", 0)
        index.add_chunk("test", chunk)

        index.clear()

        assert len(index.chunks) == 0
