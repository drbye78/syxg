"""
S.Art2 Integration Tests

Tests for full S.Art2 integration with Modern XG Synth.
"""

import pytest
import numpy as np
from typing import Dict, Any

from synth.xg.sart.articulation_controller import ArticulationController
from synth.xg.sart.articulation_preset import ArticulationPreset, ArticulationPresetManager
from synth.xg.sart.sart2_region import SArt2Region
from synth.partial.region import IRegion
from synth.engine.region_descriptor import RegionDescriptor


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def controller():
    """Create ArticulationController for testing."""
    return ArticulationController()


@pytest.fixture
def preset_manager():
    """Create ArticulationPresetManager for testing."""
    return ArticulationPresetManager()


@pytest.fixture
def mock_region():
    """Create mock base region for testing."""
    class MockRegion(IRegion):
        def __init__(self):
            descriptor = RegionDescriptor(
                region_id=0,
                engine_type='mock',
                key_range=(0, 127),
                velocity_range=(0, 127)
            )
            super().__init__(descriptor, 44100)
            self._active = False
        
        def _load_sample_data(self):
            return None
        
        def _create_partial(self):
            return None
        
        def _init_envelopes(self):
            pass
        
        def _init_filters(self):
            pass
        
        def note_on(self, velocity, note):
            self._active = True
            return True
        
        def note_off(self):
            self._active = False
        
        def is_active(self):
            return self._active
        
        def generate_samples(self, block_size, modulation):
            return np.zeros(block_size * 2, dtype=np.float32)
        
        def initialize(self):
            return True
        
        def reset(self):
            pass
        
        def dispose(self):
            pass
        
        def get_region_info(self):
            return {}
    
    return MockRegion()


# ============================================================================
# COMPATIBILITY MODE TESTS
# ============================================================================

class TestCompatibilityModes:
    """Tests for XG/GS compatibility modes."""
    
    def test_default_mode(self, controller):
        """Test default compatibility mode."""
        assert controller.get_compatibility_mode() == 'sart2'
    
    def test_set_mode(self, controller):
        """Test setting compatibility mode."""
        controller.set_compatibility_mode('xg')
        assert controller.get_compatibility_mode() == 'xg'
        
        controller.set_compatibility_mode('gs')
        assert controller.get_compatibility_mode() == 'gs'
        
        controller.set_compatibility_mode('sart2')
        assert controller.get_compatibility_mode() == 'sart2'
    
    def test_invalid_mode(self, controller):
        """Test setting invalid mode."""
        initial_mode = controller.get_compatibility_mode()
        controller.set_compatibility_mode('invalid')
        assert controller.get_compatibility_mode() == initial_mode
    
    def test_xg_nrpn_mapping(self, controller):
        """Test XG NRPN mapping."""
        controller.set_compatibility_mode('xg')
        
        # Test XG articulation mappings
        art = controller.process_nrpn(4, 1)
        assert art == 'legato'
        
        art = controller.process_nrpn(4, 2)
        assert art == 'staccato'
        
        art = controller.process_nrpn(4, 3)
        assert art == 'marcato'
    
    def test_gs_nrpn_mapping(self, controller):
        """Test GS NRPN mapping."""
        controller.set_compatibility_mode('gs')
        
        # Test GS articulation mappings
        art = controller.process_nrpn(1, 0)
        assert art == 'normal'
        
        art = controller.process_nrpn(1, 1)
        assert art == 'legato'
        
        art = controller.process_nrpn(1, 5)
        assert art == 'pizzicato'
    
    def test_mode_switching(self, controller):
        """Test switching between modes."""
        # S.Art2 mode
        controller.set_compatibility_mode('sart2')
        art = controller.process_nrpn(1, 1)
        assert art == 'legato'
        
        # XG mode
        controller.set_compatibility_mode('xg')
        art = controller.process_nrpn(4, 1)
        assert art == 'legato'
        
        # GS mode
        controller.set_compatibility_mode('gs')
        art = controller.process_nrpn(1, 1)
        assert art == 'legato'


# ============================================================================
# ARTICULATION PRESET TESTS
# ============================================================================

class TestArticulationPreset:
    """Tests for ArticulationPreset."""
    
    def test_create_preset(self):
        """Test creating articulation preset."""
        preset = ArticulationPreset(
            name='Test Piano',
            program=0,
            bank=0,
            default_articulation='normal'
        )
        
        assert preset.name == 'Test Piano'
        assert preset.program == 0
        assert preset.bank == 0
        assert preset.default_articulation == 'normal'
    
    def test_add_velocity_split(self):
        """Test adding velocity splits."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0
        )
        
        preset.add_velocity_split(0, 64, 'staccato')
        preset.add_velocity_split(65, 127, 'legato')
        
        assert len(preset.velocity_splits) == 2
    
    def test_add_key_split(self):
        """Test adding key splits."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0
        )
        
        preset.add_key_split(0, 47, 'bass')
        preset.add_key_split(48, 127, 'treble')
        
        assert len(preset.key_splits) == 2
    
    def test_get_articulation(self):
        """Test getting articulation for note/velocity."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0,
            default_articulation='normal'
        )
        
        preset.add_velocity_split(0, 64, 'staccato')
        preset.add_velocity_split(65, 127, 'legato')
        
        # Test velocity-based articulation
        art, params = preset.get_articulation(60, 50)
        assert art == 'staccato'
        
        art, params = preset.get_articulation(60, 100)
        assert art == 'legato'
    
    def test_preset_serialization(self):
        """Test preset serialization to/from JSON."""
        preset = ArticulationPreset(
            name='Test Piano',
            program=0,
            bank=0,
            default_articulation='normal',
            description='Test preset',
            category='piano',
            instrument='grand_piano'
        )
        
        preset.add_velocity_split(0, 64, 'staccato', note_length=0.5)
        preset.add_velocity_split(65, 127, 'legato')
        
        # Serialize to JSON
        json_str = preset.to_json()
        
        # Deserialize from JSON
        preset2 = ArticulationPreset.from_json(json_str)
        
        assert preset2.name == preset.name
        assert preset2.program == preset.program
        assert len(preset2.velocity_splits) == len(preset.velocity_splits)


# ============================================================================
# ARTICULATION PRESET MANAGER TESTS
# ============================================================================

class TestArticulationPresetManager:
    """Tests for ArticulationPresetManager."""
    
    def test_add_preset(self, preset_manager):
        """Test adding preset."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0
        )
        
        preset_manager.add_preset(preset)
        
        assert preset_manager.get_preset_count() == 1
    
    def test_get_preset(self, preset_manager):
        """Test getting preset."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0
        )
        
        preset_manager.add_preset(preset)
        
        retrieved = preset_manager.get_preset(0, 0)
        
        assert retrieved is not None
        assert retrieved.name == 'Test'
    
    def test_get_nonexistent_preset(self, preset_manager):
        """Test getting nonexistent preset."""
        preset = preset_manager.get_preset(99, 99)
        assert preset is None
    
    def test_remove_preset(self, preset_manager):
        """Test removing preset."""
        preset = ArticulationPreset(
            name='Test',
            program=0,
            bank=0
        )
        
        preset_manager.add_preset(preset)
        assert preset_manager.get_preset_count() == 1
        
        preset_manager.remove_preset(0, 0)
        assert preset_manager.get_preset_count() == 0
    
    def test_get_presets_by_category(self, preset_manager):
        """Test getting presets by category."""
        piano_preset = ArticulationPreset(
            name='Piano',
            program=0,
            bank=0,
            category='piano'
        )
        
        strings_preset = ArticulationPreset(
            name='Strings',
            program=48,
            bank=0,
            category='strings'
        )
        
        preset_manager.add_preset(piano_preset)
        preset_manager.add_preset(strings_preset)
        
        piano_presets = preset_manager.get_presets_by_category('piano')
        assert len(piano_presets) == 1
        assert piano_presets[0].name == 'Piano'
        
        strings_presets = preset_manager.get_presets_by_category('strings')
        assert len(strings_presets) == 1
        assert strings_presets[0].name == 'Strings'


# ============================================================================
# SART2REGION INTEGRATION TESTS
# ============================================================================

class TestSArt2RegionIntegration:
    """Tests for SArt2Region integration."""
    
    def test_sart2_region_with_preset(self, mock_region):
        """Test SArt2Region with articulation preset."""
        region = SArt2Region(mock_region)
        
        # Set velocity articulations
        region.set_velocity_articulation(0, 64, 'staccato')
        region.set_velocity_articulation(65, 127, 'legato')
        
        # Test note-on with different velocities
        region.note_on(velocity=50, note=60)
        assert region.get_articulation() == 'staccato'
        
        region.note_on(velocity=100, note=60)
        assert region.get_articulation() == 'legato'
    
    def test_sart2_region_with_key_splits(self, mock_region):
        """Test SArt2Region with key splits."""
        region = SArt2Region(mock_region)
        
        # Set key articulations
        region.set_key_articulation(0, 47, 'pizzicato')
        region.set_key_articulation(48, 127, 'legato')
        
        # Test note-on with different keys
        region.note_on(velocity=100, note=36)
        art = region.get_articulation()
        assert art == 'pizzicato', f"Expected pizzicato, got {art}"
        
        region.note_on(velocity=100, note=72)
        art = region.get_articulation()
        assert art == 'legato', f"Expected legato, got {art}"
    
    def test_sart2_region_combined_switching(self, mock_region):
        """Test SArt2Region with combined velocity and key switching."""
        region = SArt2Region(mock_region)
        
        # Set both velocity and key articulations
        region.set_key_articulation(0, 60, 'pizzicato')
        region.set_key_articulation(61, 127, 'legato')
        region.set_velocity_articulation(0, 64, 'staccato')
        region.set_velocity_articulation(65, 127, 'marcato')
        
        # Test combined switching (key is checked first)
        region.note_on(velocity=50, note=36)
        art = region.get_articulation()
        assert art == 'pizzicato', f"Expected pizzicato, got {art}"
        
        region.note_on(velocity=100, note=84)
        art = region.get_articulation()
        assert art == 'legato', f"Expected legato, got {art}"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
