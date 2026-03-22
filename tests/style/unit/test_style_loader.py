"""
Style Loader Unit Tests

Tests for the StyleLoader class including:
- Valid style file loading
- Invalid file handling
- Style validation
- Style creation utilities
"""

from __future__ import annotations

import pytest

from synth.style.style import (
    StyleCategory,
    StyleSectionType,
    TrackType,
)
from synth.style.style_loader import StyleLoader, StyleValidationError


class TestStyleLoaderValid:
    """Test loading valid style files."""

    @pytest.fixture
    def loader(self):
        return StyleLoader(validate=True)

    def test_load_valid_style(self, loader, example_style_yaml):
        """Test loading a valid style file."""
        style = loader.load_style_file(example_style_yaml)

        assert style is not None
        assert style.name == "Test Style"
        assert style.tempo == 120
        assert StyleSectionType.MAIN_A in style.sections
        assert StyleSectionType.MAIN_B in style.sections
        assert StyleSectionType.MAIN_C in style.sections
        assert StyleSectionType.MAIN_D in style.sections

    def test_load_style_with_chord_table(self, loader, example_style_yaml):
        """Test loading style with chord tables."""
        style = loader.load_style_file(example_style_yaml)

        assert StyleSectionType.MAIN_A in style.chord_tables
        chord_table = style.chord_tables[StyleSectionType.MAIN_A]

        # Check C major mapping
        assert "0_major" in chord_table.chord_type_mappings

    def test_load_preserves_metadata(self, loader, tmp_path):
        """Test that all metadata is preserved."""
        content = """
style_format_version: "1.0"
metadata:
  name: "Custom Style"
  category: "JAZZ"
  subcategory: "swing"
  tempo: 140
  time_signature: "4/4"
  author: "Test Author"
  version: "2.0"
  description: "A test style"
  tags: ["test", "jazz", "swing"]

sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_b:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_c:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_d:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }

chord_tables: {}
parameters: {}
default_section: "main_a"
fade_master: true
tempo_lock: true
"""
        path = tmp_path / "custom_style.yaml"
        path.write_text(content)

        style = loader.load_style_file(path)

        assert style.name == "Custom Style"
        assert style.category == StyleCategory.JAZZ
        assert style.metadata.subcategory == "swing"
        assert style.tempo == 140
        assert style.metadata.author == "Test Author"
        assert style.metadata.version == "2.0"
        assert "test" in style.metadata.tags


class TestStyleLoaderInvalid:
    """Test loading invalid style files."""

    @pytest.fixture
    def loader(self):
        return StyleLoader(validate=True)

    def test_load_missing_file(self, loader):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            loader.load_style_file("/nonexistent/path/style.yaml")

    def test_load_empty_file(self, loader, tmp_path):
        """Test loading empty file raises error."""
        path = tmp_path / "empty.yaml"
        path.write_text("")

        with pytest.raises(StyleValidationError):
            loader.load_style_file(path)

    def test_load_invalid_yaml(self, loader, tmp_path):
        """Test loading invalid YAML raises error."""
        path = tmp_path / "invalid.yaml"
        path.write_text("not: valid: yaml: {{{")

        with pytest.raises(Exception):
            loader.load_style_file(path)

    def test_load_missing_required_sections(self, loader, tmp_path):
        """Test loading style missing required sections raises error."""
        content = """
metadata:
  name: "Incomplete"
  tempo: 120
sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
"""
        path = tmp_path / "incomplete.yaml"
        path.write_text(content)

        with pytest.raises(StyleValidationError) as exc_info:
            loader.load_style_file(path)

        assert "Missing required section" in str(exc_info.value)

    def test_load_invalid_tempo(self, loader, tmp_path):
        """Test loading style with invalid tempo raises error."""
        content = """
metadata:
  name: "Bad Tempo"
  tempo: 500
sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_b:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_c:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
  main_d:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
      bass: { notes: [] }
      chord_1: { notes: [] }
      chord_2: { notes: [] }
      pad: { notes: [] }
      phrase_1: { notes: [] }
      phrase_2: { notes: [] }
      rhythm_2: { notes: [] }
"""
        path = tmp_path / "bad_tempo.yaml"
        path.write_text(content)

        with pytest.raises(StyleValidationError) as exc_info:
            loader.load_style_file(path)

        assert "Invalid tempo" in str(exc_info.value)


class TestStyleCreation:
    """Test style creation utilities."""

    @pytest.fixture
    def loader(self):
        return StyleLoader(validate=False)

    def test_create_minimal_style(self, loader):
        """Test creating minimal valid style."""
        style = loader.create_minimal_style(
            name="New Style",
            tempo=100,
        )

        assert style.name == "New Style"
        assert style.tempo == 100
        assert len(style.sections) > 0

    def test_create_example_style(self, loader):
        """Test creating example style with demo patterns."""
        style = loader.create_example_style(
            name="Example Style",
            tempo=120,
        )

        assert style.name == "Example Style"
        assert style.tempo == 120

        # Check that sections have note data
        main_a = style.sections.get(StyleSectionType.MAIN_A)
        assert main_a is not None

        # Check rhythm track has notes
        rhythm_track = main_a.tracks.get(TrackType.RHYTHM_1)
        assert rhythm_track is not None
        assert len(rhythm_track.notes) > 0

    def test_create_example_style_has_all_sections(self, loader):
        """Test that example style has all required sections."""
        style = loader.create_example_style()

        required_sections = [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]

        for section in required_sections:
            assert section in style.sections, f"Missing section: {section}"


class TestStyleSaveLoad:
    """Test style save and reload."""

    @pytest.fixture
    def loader(self):
        return StyleLoader(validate=True)

    def test_save_and_reload(self, loader, tmp_path):
        """Test saving and reloading a style."""
        # Create style
        style = loader.create_example_style(name="Save Test", tempo=110)

        # Save
        path = tmp_path / "saved_style.yaml"
        loader.save_style(style, path)

        assert path.exists()

        # Reload
        reloaded = loader.load_style_file(path)

        assert reloaded.name == style.name
        assert reloaded.tempo == style.tempo
        assert reloaded.category == style.category

    def test_reload_preserves_sections(self, loader, tmp_path):
        """Test that sections are preserved through save/load."""
        style = loader.create_example_style()
        path = tmp_path / "sections_test.yaml"

        loader.save_style(style, path)
        reloaded = loader.load_style_file(path)

        original_sections = set(style.sections.keys())
        reloaded_sections = set(reloaded.sections.keys())

        assert original_sections == reloaded_sections


class TestStyleValidation:
    """Test style validation functionality."""

    @pytest.fixture
    def loader_no_validate(self):
        return StyleLoader(validate=False)

    @pytest.fixture
    def loader_validate(self):
        return StyleLoader(validate=True)

    def test_validate_disabled_accepts_incomplete(self, loader_no_validate, tmp_path):
        """Test that validation disabled accepts incomplete styles."""
        content = """
metadata:
  name: "Incomplete"
  tempo: 120
sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
"""
        path = tmp_path / "incomplete.yaml"
        path.write_text(content)

        # Should not raise with validation disabled
        style = loader_no_validate.load_style_file(path)
        assert style is not None

    def test_validate_enabled_rejects_incomplete(self, loader_validate, tmp_path):
        """Test that validation enabled rejects incomplete styles."""
        content = """
metadata:
  name: "Incomplete"
  tempo: 120
sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1: { notes: [] }
"""
        path = tmp_path / "incomplete.yaml"
        path.write_text(content)

        with pytest.raises(StyleValidationError):
            loader_validate.load_style_file(path)


class TestGetAvailableStyles:
    """Test getting list of available styles."""

    @pytest.fixture
    def loader(self):
        return StyleLoader(validate=True)

    def test_get_available_styles(self, loader, tmp_path):
        """Test getting list of styles in directory."""
        # Create multiple style files
        for name in ["style_a", "style_b", "style_c"]:
            style = loader.create_minimal_style(name=name)
            loader.save_style(style, tmp_path / f"{name}.yaml")

        styles = loader.get_available_styles(tmp_path)

        assert len(styles) == 3
        style_names = [s["name"] for s in styles]

        assert "style_a" in style_names
        assert "style_b" in style_names
        assert "style_c" in style_names

    def test_get_available_styles_empty_dir(self, loader, tmp_path):
        """Test getting styles from empty directory."""
        styles = loader.get_available_styles(tmp_path)

        assert len(styles) == 0

    def test_get_available_styles_sorted(self, loader, tmp_path):
        """Test that styles are sorted by name."""
        for name in ["zebra", "alpha", "mango"]:
            style = loader.create_minimal_style(name=name)
            loader.save_style(style, tmp_path / f"{name}.yaml")

        styles = loader.get_available_styles(tmp_path)
        style_names = [s["name"] for s in styles]

        assert style_names == sorted(style_names)
