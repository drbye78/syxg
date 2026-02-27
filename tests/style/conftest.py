"""
Pytest fixtures for style engine tests.

Provides shared fixtures for unit, integration, and acceptance tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import tempfile
import yaml

from synth.style.style import (
    Style,
    StyleMetadata,
    StyleSection,
    StyleSectionType,
    TrackType,
    StyleTrackData,
    NoteEvent,
    ChordTable,
)
from synth.style.style_loader import StyleLoader
from synth.style.chord_detector import ChordDetector, ChordDetectionConfig
from synth.style.auto_accompaniment import AutoAccompaniment, AutoAccompanimentConfig


@pytest.fixture
def mock_synthesizer():
    """Create a mock synthesizer for testing."""
    synth = Mock()
    synth.note_on = Mock()
    synth.note_off = Mock()
    synth.program_change = Mock()
    synth.control_change = Mock()
    synth.channels = [Mock(program=0, bank_msb=0, bank_lsb=0, volume=100, pan=64) 
                      for _ in range(16)]
    return synth


@pytest.fixture
def sample_style():
    """Create a minimal valid style for testing."""
    metadata = StyleMetadata(
        name="Test Style",
        tempo=120,
        category="pop"
    )
    
    style = Style(metadata=metadata)
    
    # Ensure all main sections exist
    for section_type in [StyleSectionType.MAIN_A, StyleSectionType.MAIN_B,
                          StyleSectionType.MAIN_C, StyleSectionType.MAIN_D]:
        section = StyleSection(section_type=section_type, length_bars=4)
        for track_type in TrackType:
            section.tracks[track_type] = StyleTrackData()
        style.sections[section_type] = section
    
    return style


@pytest.fixture
def example_style_yaml(tmp_path):
    """Create a temporary YAML style file for testing."""
    content = """
style_format_version: "1.0"
metadata:
  name: "Test Style"
  category: "POP"
  tempo: 120
  time_signature: "4/4"

sections:
  main_a:
    length_bars: 4
    tracks:
      rhythm_1:
        notes:
          - tick: 0
            note: 36
            velocity: 100
            duration: 120
      bass:
        notes:
          - tick: 0
            note: 36
            velocity: 90
            duration: 480
      chord_1:
        notes: []
      chord_2:
        notes: []
      pad:
        notes: []
      phrase_1:
        notes: []
      phrase_2:
        notes: []
      rhythm_2:
        notes: []
  main_b:
    length_bars: 4
    tracks:
      rhythm_1:
        notes: []
      bass:
        notes: []
      chord_1:
        notes: []
      chord_2:
        notes: []
      pad:
        notes: []
      phrase_1:
        notes: []
      phrase_2:
        notes: []
      rhythm_2:
        notes: []
  main_c:
    length_bars: 4
    tracks:
      rhythm_1:
        notes: []
      bass:
        notes: []
      chord_1:
        notes: []
      chord_2:
        notes: []
      pad:
        notes: []
      phrase_1:
        notes: []
      phrase_2:
        notes: []
      rhythm_2:
        notes: []
  main_d:
    length_bars: 4
    tracks:
      rhythm_1:
        notes: []
      bass:
        notes: []
      chord_1:
        notes: []
      chord_2:
        notes: []
      pad:
        notes: []
      phrase_1:
        notes: []
      phrase_2:
        notes: []
      rhythm_2:
        notes: []

chord_tables:
  main_a:
    mappings:
      "0_major":
        chord_1: [0, 4, 7]
        bass: [0]

parameters: {}
default_section: "main_a"
fade_master: true
tempo_lock: true
"""
    path = tmp_path / "test_style.yaml"
    path.write_text(content)
    return path


@pytest.fixture
def chord_detector():
    """Create a chord detector for testing."""
    config = ChordDetectionConfig(
        detection_zone_low=48,
        detection_zone_high=72,
        use_bass_detection=True,
        bass_detection_threshold=48,
    )
    return ChordDetector(config)


@pytest.fixture
def accompaniment_config():
    """Create default accompaniment configuration."""
    return AutoAccompanimentConfig(
        chord_detection_zone_low=48,
        chord_detection_zone_high=72,
        sync_start_enabled=False,
        auto_fill_enabled=True,
    )


@pytest.fixture
def auto_accompaniment(sample_style, mock_synthesizer, accompaniment_config):
    """Create auto accompaniment engine for testing."""
    return AutoAccompaniment(
        style=sample_style,
        synthesizer=mock_synthesizer,
        config=accompaniment_config,
        sample_rate=44100
    )


@pytest.fixture
def style_loader():
    """Create style loader for testing."""
    return StyleLoader(validate=True)
