"""
SFF2 Parser Unit Tests

Tests for Yamaha SFF2 style file parser including:
- Header parsing
- Section/track extraction
- Chord table parsing
- OTS data extraction
- Style conversion
- File I/O
"""

import pytest
import struct
import tempfile
from pathlib import Path
from io import BytesIO

from synth.parsers.sff2_parser import (
    SFF2Parser,
    SFF2Header,
    SFF2Section,
    SFF2TrackData,
    SFF2NoteEvent,
    SFF2CCEvent,
    SFF2ChordTable,
    SFF2OTS,
    SECTION_TYPE_MAP,
    TRACK_TYPE_MAP,
    parse_sff2_file,
)


class TestSFF2Header:
    """Test SFF2 header parsing."""

    def test_header_magic(self):
        """Test header magic number detection."""
        data = b'SFF2' + b'\x00' * 60
        header = SFF2Header.from_bytes(data)
        assert header.magic == b'SFF2'

    def test_header_version(self):
        """Test header version parsing."""
        data = b'SFF2'
        data += struct.pack('<I', 2)  # Version 2
        data += b'\x00' * 56
        header = SFF2Header.from_bytes(data)
        assert header.version == 2

    def test_header_tempo(self):
        """Test header tempo parsing."""
        data = b'SFF2' + b'\x00' * 44
        data += struct.pack('<H', 120)  # Tempo 120
        data += b'\x00' * 14
        header = SFF2Header.from_bytes(data)
        assert header.tempo == 120

    def test_header_time_signature(self):
        """Test header time signature parsing."""
        data = b'SFF2' + b'\x00' * 46
        data += b'\x04\x04'  # 4/4
        data += b'\x00' * 12
        header = SFF2Header.from_bytes(data)
        assert header.time_signature_num == 4
        assert header.time_signature_denom == 4

    def test_header_style_name(self):
        """Test header style name parsing."""
        data = b'SFF2' + b'\x00' * 8
        data += b'Test Style\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        data += b'\x00' * 32
        header = SFF2Header.from_bytes(data)
        assert header.style_name == 'Test Style'


class TestSFF2SectionMapping:
    """Test section and track type mappings."""

    def test_section_type_map_coverage(self):
        """Test all section types are mapped."""
        # Should have all 27 section types
        assert len(SECTION_TYPE_MAP) >= 27
        
        # Check key sections exist
        assert 0x00 in SECTION_TYPE_MAP  # Intro 1
        assert 0x10 in SECTION_TYPE_MAP  # Main A
        assert 0x40 in SECTION_TYPE_MAP  # Ending 1

    def test_track_type_map_coverage(self):
        """Test all track types are mapped."""
        # Should have all 8 track types
        assert len(TRACK_TYPE_MAP) == 8
        
        for i in range(8):
            assert i in TRACK_TYPE_MAP


class TestSFF2NoteEvent:
    """Test note event handling."""

    def test_note_event_creation(self):
        """Test note event creation."""
        event = SFF2NoteEvent(
            tick=0,
            note=60,
            velocity=100,
            duration=480,
        )
        assert event.tick == 0
        assert event.note == 60
        assert event.velocity == 100

    def test_note_event_to_dict(self):
        """Test note event dictionary conversion."""
        event = SFF2NoteEvent(
            tick=480,
            note=72,
            velocity=90,
            duration=240,
            gate_time=0.9,
        )
        d = event.to_dict()
        assert d['tick'] == 480
        assert d['note'] == 72
        assert d['velocity'] == 90


class TestSFF2CCEvent:
    """Test control change event handling."""

    def test_cc_event_creation(self):
        """Test CC event creation."""
        event = SFF2CCEvent(
            tick=0,
            controller=7,
            value=100,
        )
        assert event.controller == 7
        assert event.value == 100

    def test_cc_event_to_dict(self):
        """Test CC event dictionary conversion."""
        event = SFF2CCEvent(
            tick=960,
            controller=10,
            value=64,
        )
        d = event.to_dict()
        assert d['tick'] == 960
        assert d['controller'] == 10
        assert d['value'] == 64


class TestSFF2TrackData:
    """Test track data handling."""

    def test_track_data_creation(self):
        """Test track data creation."""
        track = SFF2TrackData(
            track_type=2,  # Bass
            volume=0.8,
            pan=64,
        )
        assert track.track_type == 2
        assert track.volume == 0.8

    def test_track_data_to_dict(self):
        """Test track data dictionary conversion."""
        track = SFF2TrackData(
            track_type=0,
            notes=[SFF2NoteEvent(tick=0, note=36, velocity=100)],
            cc_events=[SFF2CCEvent(tick=0, controller=7, value=100)],
            volume=1.0,
            pan=50,
        )
        d = track.to_dict()
        assert 'notes' in d
        assert 'cc_events' in d
        assert len(d['notes']) == 1


class TestSFF2Section:
    """Test section data handling."""

    def test_section_creation(self):
        """Test section creation."""
        section = SFF2Section(
            section_type=0x10,  # Main A
            length_bars=4,
            tempo=120,
        )
        assert section.section_type == 0x10
        assert section.length_bars == 4

    def test_section_to_dict(self):
        """Test section dictionary conversion."""
        section = SFF2Section(
            section_type=0x10,
            length_bars=4,
            length_ticks=1920,
            tempo=120,
        )
        d = section.to_dict()
        assert d['length_bars'] == 4
        assert d['length_ticks'] == 1920


class TestSFF2ChordTable:
    """Test chord table handling."""

    def test_chord_table_creation(self):
        """Test chord table creation."""
        table = SFF2ChordTable(
            section_type=0x10,
            chord_root=0,  # C
            chord_type=0,  # Major
        )
        assert table.chord_root == 0
        assert table.chord_type == 0

    def test_chord_table_to_dict(self):
        """Test chord table dictionary conversion."""
        table = SFF2ChordTable(
            section_type=0x10,
            chord_root=0,
            chord_type=0,
            track_voicings={
                3: [0, 4, 7],  # Chord 1: C major
                2: [0],  # Bass: C
            }
        )
        d = table.to_dict()
        assert '0_major' in d

    def test_chord_type_names(self):
        """Test chord type name generation."""
        table = SFF2ChordTable()
        
        table.chord_type = 0
        assert table._get_chord_type_name() == 'major'
        
        table.chord_type = 1
        assert table._get_chord_type_name() == 'minor'
        
        table.chord_type = 2
        assert table._get_chord_type_name() == 'seventh'


class TestSFF2OTS:
    """Test OTS preset handling."""

    def test_ots_creation(self):
        """Test OTS preset creation."""
        ots = SFF2OTS(
            preset_id=0,
            name="Piano",
        )
        assert ots.preset_id == 0
        assert ots.name == "Piano"

    def test_ots_to_dict(self):
        """Test OTS dictionary conversion."""
        ots = SFF2OTS(
            preset_id=1,
            name="Organ",
            program_changes=[16, 17, 18, 19],
            bank_msb=[0, 0, 0, 0],
            bank_lsb=[0, 0, 0, 0],
            volume=[100, 90, 80, 70],
            pan=[64, 64, 64, 64],
        )
        d = ots.to_dict()
        assert d['preset_id'] == 1
        assert d['name'] == "Organ"
        assert len(d['parts']) == 4


class TestSFF2Parser:
    """Test SFF2 parser functionality."""

    def test_parser_creation(self):
        """Test parser creation."""
        parser = SFF2Parser()
        assert parser is not None
        assert parser.header is None

    def test_parser_file_not_found(self):
        """Test parser handles missing files."""
        parser = SFF2Parser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent.sty")

    def test_parser_invalid_magic(self):
        """Test parser handles invalid magic numbers."""
        parser = SFF2Parser()
        data = b'XXXX' + b'\x00' * 60
        
        with pytest.raises(ValueError):
            parser.parse_stream(BytesIO(data))

    def test_parser_valid_header(self):
        """Test parser with valid header."""
        parser = SFF2Parser()
        
        # Create minimal valid SFF2 header
        data = b'SFF2'
        data += struct.pack('<I', 2)  # Version
        data += struct.pack('<I', 100)  # File size
        data += b'Test\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        data += b'POP\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        data += struct.pack('<H', 120)  # Tempo
        data += b'\x04\x04'  # Time signature
        data += struct.pack('<H', 8)  # Num sections
        data += b'\x00' * 100  # Padding
        
        parser.parse_stream(BytesIO(data))
        assert parser.header is not None
        assert parser.header.style_name == 'Test'


class TestSFF2ToStyleConversion:
    """Test SFF2 to Style conversion."""

    def test_conversion_creates_style(self):
        """Test conversion creates Style object."""
        parser = SFF2Parser()
        parser.header = SFF2Header()
        parser.header.style_name = "Test Style"
        parser.header.tempo = 120
        
        style = parser._to_style()
        
        assert style is not None
        assert style.name == "Test Style"
        assert style.tempo == 120

    def test_conversion_category_detection(self):
        """Test category detection from header."""
        parser = SFF2Parser()
        parser.header = SFF2Header()
        parser.header.category = "ROCK"
        
        category = parser._get_category()
        assert category.name == "ROCK"

    def test_conversion_with_sections(self):
        """Test conversion with sections."""
        parser = SFF2Parser()
        parser.header = SFF2Header()
        
        # Add a section
        section = SFF2Section(
            section_type=0x10,  # Main A
            length_bars=4,
        )
        parser.sections[0x10] = section
        
        style = parser._to_style()
        
        # Should have main_a section
        from synth.style.style import StyleSectionType
        assert StyleSectionType.MAIN_A in style.sections


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_parse_sff2_file_not_found(self):
        """Test parse_sff2_file with missing file."""
        with pytest.raises(FileNotFoundError):
            parse_sff2_file("nonexistent.sty")


class TestSFF2Integration:
    """Test SFF2 integration with StyleLoader."""

    def test_style_loader_sff2_support(self):
        """Test StyleLoader has SFF2 support."""
        from synth.style.style_loader import StyleLoader
        
        loader = StyleLoader()
        assert loader._get_sff2_parser() is not None

    def test_style_loader_file_detection(self):
        """Test StyleLoader detects file format."""
        from synth.style.style_loader import StyleLoader
        
        loader = StyleLoader()
        
        # Should detect YAML
        assert loader._load_yaml_file is not None
        
        # Should have SFF2 method
        assert loader._load_sff2_file is not None


class TestSFF2EdgeCases:
    """Test edge cases and error handling."""

    def test_empty_chord_voicing(self):
        """Test empty chord voicing handling."""
        table = SFF2ChordTable(
            chord_root=0,
            chord_type=0,
            track_voicings={}
        )
        d = table.to_dict()
        assert '0_major' in d

    def test_invalid_section_type(self):
        """Test invalid section type handling."""
        # Should not crash
        section_type = 0xFF
        section_name = SECTION_TYPE_MAP.get(section_type)
        assert section_name is None

    def test_invalid_track_type(self):
        """Test invalid track type handling."""
        track_type = 10
        track_name = TRACK_TYPE_MAP.get(track_type)
        assert track_name is None

    def test_unicode_style_name(self):
        """Test Unicode style name handling."""
        data = b'SFF2' + b'\x00' * 8
        # ASCII only for SFF2
        data += b'Test\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        data += b'\x00' * 48
        
        header = SFF2Header.from_bytes(data)
        assert header.style_name == 'Test'
