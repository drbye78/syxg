"""
Tests for vibexg.managers module

Tests PresetManager, MIDILearnManager, and StyleEngineIntegration.
"""

import pytest
import os
import tempfile
from pathlib import Path
from vibexg.managers import PresetManager, MIDILearnManager, StyleEngineIntegration


class MockSynthesizer:
    """Mock synthesizer for testing."""
    pass


class TestPresetManager:
    """Test PresetManager class."""

    def test_create_preset(self):
        """Test preset creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            preset = pm.create_preset('Test Preset')
            
            assert preset.name == 'Test Preset'
            assert pm.current_preset == preset

    def test_save_preset(self):
        """Test preset saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            preset = pm.create_preset('Test Preset')
            preset.master_volume = 0.75
            
            filepath = pm.save_preset(preset)
            
            assert filepath.exists()
            assert filepath.suffix == '.preset'

    def test_load_preset(self):
        """Test preset loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            preset = pm.create_preset('Test Preset')
            preset.master_volume = 0.75
            preset.tempo = 110.0
            
            filepath = pm.save_preset(preset)
            loaded = pm.load_preset(filepath.name)
            
            assert loaded is not None
            assert loaded.name == 'Test Preset'
            assert loaded.master_volume == 0.75
            assert loaded.tempo == 110.0

    def test_list_presets(self):
        """Test listing presets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            
            # Create and save multiple presets
            for i in range(3):
                preset = pm.create_preset(f'Preset {i}')
                pm.save_preset(preset)
            
            presets = pm.list_presets()
            assert len(presets) == 3

    def test_delete_preset(self):
        """Test preset deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            preset = pm.create_preset('Test Preset')
            filepath = pm.save_preset(preset)
            
            result = pm.delete_preset(filepath.name)
            
            assert result is True
            assert not filepath.exists()

    def test_export_preset_json(self):
        """Test JSON export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = PresetManager(tmpdir)
            preset = pm.create_preset('Test Preset')
            
            filepath = pm.export_preset_json(preset, 'test.json')
            
            assert filepath.exists()
            assert filepath.suffix == '.json'


class TestMIDILearnManager:
    """Test MIDILearnManager class."""

    def test_add_mapping(self):
        """Test adding CC mapping."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff', channel=0, min_val=100, max_val=1000)
        
        mappings = ml.get_mappings()
        assert 74 in mappings
        assert mappings[74]['target'] == 'filter.cutoff'

    def test_remove_mapping(self):
        """Test removing CC mapping."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff')
        ml.remove_mapping(74)
        
        mappings = ml.get_mappings()
        assert 74 not in mappings

    def test_clear_mappings(self):
        """Test clearing all mappings."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff')
        ml.add_mapping(1, 'amplitude.attack')
        ml.clear_mappings()
        
        mappings = ml.get_mappings()
        assert len(mappings) == 0

    def test_process_cc_linear(self):
        """Test CC processing with linear curve."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff', min_val=0, max_val=127, curve='linear')
        
        # Should not raise
        ml.process_cc(74, 64, channel=0)

    def test_process_cc_exp(self):
        """Test CC processing with exponential curve."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff', min_val=100, max_val=1000, curve='exp')
        
        # Should not raise
        ml.process_cc(74, 64, channel=0)

    def test_process_cc_invert(self):
        """Test CC processing with invert."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(72, 'filter.resonance', invert=True)
        
        # Should not raise
        ml.process_cc(72, 100, channel=0)

    def test_export_mappings(self):
        """Test exporting mappings."""
        ml = MIDILearnManager(MockSynthesizer())
        ml.add_mapping(74, 'filter.cutoff')
        
        exported = ml.export_mappings()
        
        assert 'mappings' in exported
        assert len(exported['mappings']) == 1

    def test_import_mappings(self):
        """Test importing mappings."""
        ml = MIDILearnManager(MockSynthesizer())
        data = {
            'mappings': [
                {'cc': 74, 'target': 'filter.cutoff', 'channel': 0}
            ],
            'learning_mode': False
        }
        
        ml.import_mappings(data)
        mappings = ml.get_mappings()
        
        assert 74 in mappings


class TestStyleEngineIntegration:
    """Test StyleEngineIntegration class."""

    def test_initialization(self):
        """Test style engine initialization."""
        se = StyleEngineIntegration(MockSynthesizer())
        
        # Style engine may not be available
        assert se.synthesizer is not None

    def test_add_style_path(self):
        """Test adding style path."""
        se = StyleEngineIntegration(MockSynthesizer())
        
        with tempfile.TemporaryDirectory() as tmpdir:
            se.add_style_path(Path(tmpdir))
            assert len(se.style_paths) == 1

    def test_get_loaded_styles(self):
        """Test getting loaded styles."""
        se = StyleEngineIntegration(MockSynthesizer())
        styles = se.get_loaded_styles()
        
        assert isinstance(styles, dict)
