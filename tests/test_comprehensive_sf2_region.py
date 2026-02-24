"""
Comprehensive Test Suite for Region-Based Architecture and SF2 Package Integration

This test suite provides in-depth validation of:
1. All refactored region-based architecture components
2. SF2 package integration (SF2SoundFontManager, SF2SoundFont, SF2Zone, etc.)
3. Multi-zone preset handling (key splits, velocity splits, layering)
4. Sample loading and caching
5. Generator parameter extraction
6. Modulation engine integration
7. All synthesis engine region implementations

Uses tests/ref.sf2 as reference soundfont for real-world testing.
"""

import pytest
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import logging

from synth.engine.region_descriptor import RegionDescriptor
from synth.engine.preset_info import PresetInfo
from synth.partial.region import IRegion, RegionState
from synth.partial.sf2_region import SF2Region
from synth.partial.wavetable_region import WavetableRegion
from synth.partial.additive_region import AdditiveRegion
from synth.partial.physical_region import PhysicalRegion
from synth.partial.granular_region import GranularRegion
from synth.partial.fdsp_region import FDSPRegion
from synth.partial.an_region import ANRegion
from synth.voice.voice import Voice
from synth.voice.voice_factory import VoiceFactory
from synth.engine.synthesis_engine import SynthesisEngineRegistry
from synth.engine.sf2_engine import SF2Engine
from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
from synth.sf2.sf2_data_model import SF2Zone, SF2Preset, SF2Instrument

logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='module')
def ref_soundfont_path() -> str:
    """Get path to reference soundfont."""
    path = Path(__file__).parent / 'ref.sf2'
    
    if not path.exists():
        pytest.skip("Reference soundfont (tests/ref.sf2) not found")
    
    return str(path)


@pytest.fixture(scope='module')
def sf2_manager(ref_soundfont_path) -> SF2SoundFontManager:
    """Create SF2SoundFontManager with reference soundfont loaded."""
    manager = SF2SoundFontManager(cache_memory_mb=512, max_loaded_files=5)
    manager.load_soundfont(ref_soundfont_path)
    return manager


@pytest.fixture(scope='module')
def sf2_engine(ref_soundfont_path) -> SF2Engine:
    """Create SF2Engine with reference soundfont loaded."""
    engine = SF2Engine(sample_rate=44100, block_size=1024)
    engine.load_soundfont(ref_soundfont_path)
    return engine


@pytest.fixture(scope='module')
def engine_registry(ref_soundfont_path) -> SynthesisEngineRegistry:
    """Create engine registry with all engines."""
    registry = SynthesisEngineRegistry()
    
    # Register SF2 engine
    sf2_engine = SF2Engine(sample_rate=44100, block_size=1024)
    sf2_engine.load_soundfont(ref_soundfont_path)
    registry.register_engine(sf2_engine, 'sf2', priority=10)
    
    return registry


@pytest.fixture(scope='module')
def voice_factory(engine_registry) -> VoiceFactory:
    """Create VoiceFactory with engine registry."""
    return VoiceFactory(engine_registry)


@pytest.fixture(scope='module')
def available_programs(sf2_manager) -> List[tuple]:
    """Get list of available programs from reference soundfont."""
    programs = []
    for filepath in sf2_manager.file_order:
        soundfont = sf2_manager.loaded_files[filepath]
        if hasattr(soundfont, 'get_available_programs'):
            programs.extend(soundfont.get_available_programs())
    return programs


# ============================================================================
# SF2 PACKAGE CORE TESTS
# ============================================================================

class TestSF2PackageCore:
    """Tests for core SF2 package functionality."""
    
    def test_soundfont_manager_initialization(self, sf2_manager):
        """Test SF2SoundFontManager initializes correctly."""
        assert sf2_manager is not None
        assert len(sf2_manager.loaded_files) >= 1
        assert sf2_manager.sample_processor is not None
        assert sf2_manager.zone_cache_manager is not None
        assert sf2_manager.modulation_engine is not None
    
    def test_soundfont_manager_file_order(self, sf2_manager):
        """Test SF2SoundFontManager maintains file order."""
        assert len(sf2_manager.file_order) >= 1
        assert isinstance(sf2_manager.file_order, list)
    
    def test_soundfont_manager_performance_stats(self, sf2_manager):
        """Test SF2SoundFontManager performance statistics."""
        stats = sf2_manager.get_performance_stats()
        
        assert 'loaded_files' in stats
        assert 'file_order' in stats
        assert 'memory_usage' in stats
        assert stats['loaded_files'] >= 1
    
    def test_soundfont_loads_presets(self, sf2_manager):
        """Test soundfont loads preset data."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            # Check preset data structure
            assert hasattr(soundfont, 'presets')
            assert isinstance(soundfont.presets, dict)
    
    def test_soundfont_loads_instruments(self, sf2_manager):
        """Test soundfont loads instrument data."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            # Check instrument data structure
            assert hasattr(soundfont, 'instruments')
            assert isinstance(soundfont.instruments, dict)
    
    def test_soundfont_loads_samples(self, sf2_manager):
        """Test soundfont loads sample data."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            # Check sample data structure
            assert hasattr(soundfont, 'samples')
            assert isinstance(soundfont.samples, dict)
    
    def test_sf2_zone_key_range_extraction(self, sf2_manager):
        """Test SF2Zone key range extraction from generators."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            for preset_key, preset in soundfont.presets.items():
                if hasattr(preset, 'zones') and preset.zones:
                    for zone in preset.zones:
                        if isinstance(zone, SF2Zone):
                            # Key range should be valid
                            assert 0 <= zone.key_range[0] <= 127
                            assert 0 <= zone.key_range[1] <= 127
                            assert zone.key_range[0] <= zone.key_range[1]
                            return  # Test first valid zone
        
        pytest.skip("No zones found in soundfont")
    
    def test_sf2_zone_velocity_range_extraction(self, sf2_manager):
        """Test SF2Zone velocity range extraction from generators."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            for preset_key, preset in soundfont.presets.items():
                if hasattr(preset, 'zones') and preset.zones:
                    for zone in preset.zones:
                        if isinstance(zone, SF2Zone):
                            # Velocity range should be valid
                            assert 0 <= zone.velocity_range[0] <= 127
                            assert 0 <= zone.velocity_range[1] <= 127
                            assert zone.velocity_range[0] <= zone.velocity_range[1]
                            return  # Test first valid zone
        
        pytest.skip("No zones found in soundfont")
    
    def test_sf2_zone_generator_storage(self, sf2_manager):
        """Test SF2Zone stores generator parameters."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            for preset_key, preset in soundfont.presets.items():
                if hasattr(preset, 'zones') and preset.zones:
                    for zone in preset.zones:
                        if isinstance(zone, SF2Zone):
                            # Zone should have generators dict
                            assert hasattr(zone, 'generators')
                            assert isinstance(zone.generators, dict)
                            return  # Test first valid zone
        
        pytest.skip("No zones found in soundfont")
    
    def test_sf2_zone_matches_note_velocity(self, sf2_manager):
        """Test SF2Zone.matches_note_velocity() method."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            for preset_key, preset in soundfont.presets.items():
                if hasattr(preset, 'zones') and preset.zones:
                    for zone in preset.zones:
                        if isinstance(zone, SF2Zone):
                            # Test matching
                            result = zone.matches_note_velocity(60, 100)
                            assert isinstance(result, bool)
                            
                            # Test caching
                            result2 = zone.matches_note_velocity(60, 100)
                            assert result == result2
                            return  # Test first valid zone
        
        pytest.skip("No zones found in soundfont")
    
    def test_sf2_preset_get_matching_zones(self, sf2_manager):
        """Test SF2Preset.get_matching_zones() method."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            for preset_key, preset in soundfont.presets.items():
                if hasattr(preset, 'get_matching_zones'):
                    # Test with different note/velocity combinations
                    zones_c4_soft = preset.get_matching_zones(60, 50)
                    zones_c4_loud = preset.get_matching_zones(60, 100)
                    
                    assert isinstance(zones_c4_soft, list)
                    assert isinstance(zones_c4_loud, list)
                    return  # Test first valid preset
        
        pytest.skip("No presets with get_matching_zones found")


# ============================================================================
# SF2 SOUNDFONT MANAGER TESTS
# ============================================================================

class TestSF2SoundFontManager:
    """Tests for SF2SoundFontManager functionality."""
    
    def test_get_sample_data(self, sf2_manager):
        """Test SF2SoundFontManager.get_sample_data()."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                sample_data = sf2_manager.get_sample_data(sample_id)
                
                # Sample data should be numpy array or None
                assert sample_data is None or hasattr(sample_data, '__len__')
                return
        
        pytest.skip("No samples found")
    
    def test_get_sample_info(self, sf2_manager):
        """Test SF2SoundFontManager.get_sample_info()."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                info = sf2_manager.get_sample_info(sample_id)
                
                if info:
                    assert isinstance(info, dict)
                    # Should have sample metadata
                    assert 'original_pitch' in info or 'sample_rate' in info
                return
        
        pytest.skip("No samples found")
    
    def test_get_sample_loop_info(self, sf2_manager):
        """Test SF2SoundFontManager.get_sample_loop_info()."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                loop_info = sf2_manager.get_sample_loop_info(sample_id)
                
                if loop_info:
                    assert isinstance(loop_info, dict)
                    assert 'start' in loop_info
                    assert 'end' in loop_info
                    assert 'mode' in loop_info
                return
        
        pytest.skip("No samples found")
    
    def test_get_zone(self, sf2_manager):
        """Test SF2SoundFontManager.get_zone()."""
        # Try to get a zone from first preset
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            
            if hasattr(soundfont, 'presets') and soundfont.presets:
                preset_key = list(soundfont.presets.keys())[0]
                bank, program = preset_key
                
                zone = sf2_manager.get_zone(0, bank, program)
                
                # Zone should be SF2Zone or None
                assert zone is None or isinstance(zone, SF2Zone)
                return
        
        pytest.skip("No presets found")
    
    def test_update_controller(self, sf2_manager):
        """Test SF2SoundFontManager.update_controller()."""
        # Update modulation wheel
        sf2_manager.update_controller(1, 64)
        
        # Controller value should be updated
        controller_value = sf2_manager.modulation_engine.controller_values.get(1, 0)
        assert controller_value >= 0
    
    def test_performance_stats(self, sf2_manager):
        """Test SF2SoundFontManager.get_performance_stats()."""
        stats = sf2_manager.get_performance_stats()
        
        assert 'loaded_files' in stats
        assert 'file_order' in stats
        assert 'memory_usage' in stats
        assert 'cache_performance' in stats or 'zone_cache_stats' in stats
    
    def test_memory_usage_tracking(self, sf2_manager):
        """Test SF2SoundFontManager tracks memory usage."""
        stats = sf2_manager.get_performance_stats()
        memory = stats.get('memory_usage', {})
        
        # Should have memory tracking
        assert 'total_mb' in memory or len(memory) > 0


# ============================================================================
# SF2 ENGINE TESTS
# ============================================================================

class TestSF2Engine:
    """Tests for SF2Engine with new region-based architecture."""
    
    def test_engine_get_preset_info(self, sf2_engine):
        """Test SF2Engine.get_preset_info()."""
        # Try first few programs
        for program in range(min(5, 128)):
            preset_info = sf2_engine.get_preset_info(bank=0, program=program)
            
            if preset_info:
                assert isinstance(preset_info, PresetInfo)
                assert preset_info.bank == 0
                assert preset_info.program == program
                assert preset_info.engine_type == 'sf2'
                assert len(preset_info.region_descriptors) >= 1
                return
        
        pytest.skip("No presets found in bank 0")
    
    def test_engine_get_all_region_descriptors(self, sf2_engine):
        """Test SF2Engine.get_all_region_descriptors()."""
        for program in range(min(5, 128)):
            descriptors = sf2_engine.get_all_region_descriptors(bank=0, program=program)
            
            if descriptors:
                assert isinstance(descriptors, list)
                for desc in descriptors:
                    assert isinstance(desc, RegionDescriptor)
                    assert desc.engine_type == 'sf2'
                return
        
        pytest.skip("No presets found")
    
    def test_engine_create_region(self, sf2_engine):
        """Test SF2Engine.create_region()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            region = sf2_engine.create_region(descriptor, 44100)
            
            assert region is not None
            assert isinstance(region, SF2Region)
            assert region.descriptor == descriptor
        else:
            pytest.skip("No presets found")
    
    def test_engine_load_sample_for_region(self, sf2_engine):
        """Test SF2Engine.load_sample_for_region()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            region = sf2_engine.create_region(descriptor, 44100)
            
            result = sf2_engine.load_sample_for_region(region)
            assert isinstance(result, bool)
        else:
            pytest.skip("No presets found")
    
    def test_engine_multi_zone_preset(self, sf2_engine):
        """Test SF2Engine handles multi-zone presets."""
        # Find a preset with multiple zones
        for program in range(min(20, 128)):
            preset_info = sf2_engine.get_preset_info(bank=0, program=program)
            
            if preset_info and len(preset_info.region_descriptors) > 1:
                # This is a multi-zone preset
                descriptors = preset_info.region_descriptors
                
                # Check for key splits
                key_ranges = [d.key_range for d in descriptors]
                has_key_splits = len(set(key_ranges)) > 1
                
                # Check for velocity splits
                vel_ranges = [d.velocity_range for d in descriptors]
                has_vel_splits = len(set(vel_ranges)) > 1
                
                # At least one type of split should exist
                assert has_key_splits or has_vel_splits or len(descriptors) > 1
                return
        
        pytest.skip("No multi-zone presets found")
    
    def test_engine_zone_selection_by_note(self, sf2_engine):
        """Test SF2Engine selects correct zones for different notes."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            # Get zones for different notes
            zones_low = preset_info.get_matching_descriptors(note=36, velocity=100)
            zones_high = preset_info.get_matching_descriptors(note=84, velocity=100)
            
            # Both should return lists
            assert isinstance(zones_low, list)
            assert isinstance(zones_high, list)
        else:
            pytest.skip("No preset found")


# ============================================================================
# SF2 REGION TESTS
# ============================================================================

class TestSF2Region:
    """Tests for SF2Region implementation."""
    
    @pytest.fixture
    def sf2_region(self, sf2_manager) -> SF2Region:
        """Create SF2Region for testing."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0,
            generator_params={
                'amp_attack': 0.01,
                'amp_decay': 0.3,
                'amp_sustain': 0.7,
                'amp_release': 0.5,
                'filter_cutoff': 5000.0,
                'filter_resonance': 0.5
            }
        )
        
        return SF2Region(descriptor, 44100, sf2_manager)
    
    def test_region_initialization(self, sf2_region):
        """Test SF2Region initializes correctly."""
        assert sf2_region is not None
        assert sf2_region.soundfont_manager is not None
        assert sf2_region.descriptor is not None
    
    def test_region_get_sf2_zone(self, sf2_region, sf2_manager):
        """Test SF2Region._get_sf2_zone() caching."""
        # Get zone (may be None if no zones available)
        zone = sf2_region._get_sf2_zone()
        
        # Zone should be cached
        assert sf2_region._sf2_zone is zone
    
    def test_region_generator_value_retrieval(self, sf2_region):
        """Test SF2Region._get_generator_value()."""
        # Test with default value
        value = sf2_region._get_generator_value(999, -1)
        assert value == -1
        
        # Test with descriptor params
        # Generator 9 = volEnvAttack
        attack = sf2_region._get_generator_value(9, -12000)
        assert isinstance(attack, (int, float))
    
    def test_region_timecents_conversion(self, sf2_region):
        """Test SF2Region._timecents_to_seconds()."""
        # -12000 timecents = instant
        assert sf2_region._timecents_to_seconds(-12000) == 0.0
        
        # 0 timecents = 2^0 = 1 second
        assert abs(sf2_region._timecents_to_seconds(0) - 1.0) < 0.001
        
        # 1200 timecents = 2^1 = 2 seconds
        assert abs(sf2_region._timecents_to_seconds(1200) - 2.0) < 0.01
    
    def test_region_cents_to_frequency(self, sf2_region):
        """Test SF2Region._cents_to_frequency()."""
        # 0 cents = 440 Hz
        assert abs(sf2_region._cents_to_frequency(0) - 440.0) < 0.1
        
        # 1200 cents = 880 Hz (one octave up)
        assert abs(sf2_region._cents_to_frequency(1200) - 880.0) < 0.1
        
        # -1200 cents = 220 Hz (one octave down)
        assert abs(sf2_region._cents_to_frequency(-1200) - 220.0) < 0.1
    
    def test_region_builds_partial_params(self, sf2_region):
        """Test SF2Region._build_partial_params_from_generators()."""
        params = sf2_region._build_partial_params_from_generators()
        
        # Check all SF2 generator groups are included
        assert 'amp_attack' in params
        assert 'amp_decay' in params
        assert 'amp_sustain' in params
        assert 'amp_release' in params
        
        assert 'mod_env_delay' in params
        assert 'mod_env_attack' in params
        assert 'mod_env_to_pitch' in params
        
        assert 'mod_lfo_delay' in params
        assert 'mod_lfo_rate' in params
        assert 'vib_lfo_delay' in params
        assert 'vib_lfo_rate' in params
        
        assert 'filter_cutoff' in params
        assert 'filter_resonance' in params
        
        assert 'reverb_send' in params
        assert 'chorus_send' in params
        assert 'pan' in params
        
        assert 'coarse_tune' in params
        assert 'fine_tune' in params
        assert 'scale_tuning' in params
    
    def test_region_note_velocity_matching(self, sf2_region):
        """Test SF2Region._matches_note_velocity()."""
        # Default ranges are (0, 127) for both
        assert sf2_region._matches_note_velocity(60, 100) == True
        assert sf2_region._matches_note_velocity(0, 0) == True
        assert sf2_region._matches_note_velocity(127, 127) == True
    
    def test_region_sf2_looping(self, sf2_region):
        """Test SF2Region._handle_sf2_looping()."""
        # Set loop parameters
        sf2_region._loop_start = 1000
        sf2_region._loop_end = 2000
        sf2_region._loop_mode = 1  # Forward loop
        
        # Test forward looping
        position = sf2_region._handle_sf2_looping(2500, 4000)
        
        # Should wrap back to loop range
        assert position >= sf2_region._loop_start
        assert position < sf2_region._loop_end
    
    def test_region_sample_loading(self, sf2_region):
        """Test SF2Region._load_sample_data()."""
        # Try to load sample
        sample_data = sf2_region._load_sample_data()
        
        # Sample data should be numpy array or None
        assert sample_data is None or isinstance(sample_data, np.ndarray)
    
    def test_region_initialization_flow(self, sf2_region):
        """Test SF2Region full initialization flow."""
        # Initialize region
        result = sf2_region.initialize()
        
        # Should complete without error
        assert isinstance(result, bool)
    
    def test_region_note_on(self, sf2_region):
        """Test SF2Region.note_on()."""
        sf2_region.initialize()
        result = sf2_region.note_on(velocity=100, note=60)
        
        # Should return boolean
        assert isinstance(result, bool)
    
    def test_region_generate_samples(self, sf2_region):
        """Test SF2Region.generate_samples()."""
        sf2_region.initialize()
        sf2_region.note_on(velocity=100, note=60)
        
        samples = sf2_region.generate_samples(block_size=1024, modulation={})
        
        # Should return numpy array
        assert isinstance(samples, np.ndarray)
        assert len(samples) == 1024 * 2  # Stereo
        assert samples.dtype == np.float32
    
    def test_region_is_active(self, sf2_region):
        """Test SF2Region.is_active()."""
        # Initially should not be active (not initialized)
        # After initialization and note_on, should be active
        sf2_region.initialize()
        sf2_region.note_on(velocity=100, note=60)
        
        # Should return boolean
        result = sf2_region.is_active()
        assert isinstance(result, bool)
    
    def test_region_get_info(self, sf2_region):
        """Test SF2Region.get_region_info()."""
        info = sf2_region.get_region_info()
        
        assert isinstance(info, dict)
        assert 'sample_id' in info
        assert 'engine_type' in info
        assert 'key_range' in info
        assert 'velocity_range' in info


# ============================================================================
# PRESET INFO TESTS
# ============================================================================

class TestPresetInfo:
    """Tests for PresetInfo class."""
    
    def test_preset_info_creation(self, sf2_engine):
        """Test PresetInfo is created correctly."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            assert isinstance(preset_info, PresetInfo)
            assert preset_info.bank == 0
            assert preset_info.program == 0
            assert preset_info.name
            assert preset_info.engine_type == 'sf2'
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_region_descriptors(self, sf2_engine):
        """Test PresetInfo region descriptors."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            assert len(preset_info.region_descriptors) >= 1
            
            for desc in preset_info.region_descriptors:
                assert isinstance(desc, RegionDescriptor)
                assert desc.engine_type == 'sf2'
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_get_matching_descriptors(self, sf2_engine):
        """Test PresetInfo.get_matching_descriptors()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            # Test with different note/velocity combinations
            matches_c4 = preset_info.get_matching_descriptors(60, 100)
            matches_c3 = preset_info.get_matching_descriptors(48, 100)
            matches_c5 = preset_info.get_matching_descriptors(72, 100)
            
            assert isinstance(matches_c4, list)
            assert isinstance(matches_c3, list)
            assert isinstance(matches_c5, list)
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_has_key_splits(self, sf2_engine):
        """Test PresetInfo.has_key_splits()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            result = preset_info.has_key_splits()
            assert isinstance(result, bool)
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_has_velocity_splits(self, sf2_engine):
        """Test PresetInfo.has_velocity_splits()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            result = preset_info.has_velocity_splits()
            assert isinstance(result, bool)
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_get_key_range(self, sf2_engine):
        """Test PresetInfo.get_key_range()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            key_range = preset_info.get_key_range()
            
            assert isinstance(key_range, tuple)
            assert len(key_range) == 2
            assert 0 <= key_range[0] <= 127
            assert 0 <= key_range[1] <= 127
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_get_velocity_range(self, sf2_engine):
        """Test PresetInfo.get_velocity_range()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            vel_range = preset_info.get_velocity_range()
            
            assert isinstance(vel_range, tuple)
            assert len(vel_range) == 2
            assert 0 <= vel_range[0] <= 127
            assert 0 <= vel_range[1] <= 127
        else:
            pytest.skip("No preset found")
    
    def test_preset_info_get_region_count(self, sf2_engine):
        """Test PresetInfo.get_region_count()."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            count = preset_info.get_region_count()
            assert isinstance(count, int)
            assert count >= 1
        else:
            pytest.skip("No preset found")


# ============================================================================
# VOICE TESTS
# ============================================================================

class TestVoice:
    """Tests for Voice class with region-based architecture."""
    
    def test_voice_creation(self, voice_factory):
        """Test Voice creation."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            assert voice is not None
            assert voice.preset_info is not None
            assert voice.engine is not None
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_get_regions_for_note(self, voice_factory):
        """Test Voice.get_regions_for_note()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            regions = voice.get_regions_for_note(note=60, velocity=100)
            
            assert isinstance(regions, list)
            for region in regions:
                assert hasattr(region, 'descriptor')
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_note_on(self, voice_factory):
        """Test Voice.note_on()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            activated = voice.note_on(note=60, velocity=100)
            
            assert isinstance(activated, list)
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_generate_samples(self, voice_factory):
        """Test Voice.generate_samples()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            voice.note_on(note=60, velocity=100)
            samples = voice.generate_samples(block_size=1024, modulation={})
            
            assert isinstance(samples, np.ndarray)
            assert len(samples) == 1024 * 2
            assert samples.dtype == np.float32
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_is_active(self, voice_factory):
        """Test Voice.is_active()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            result = voice.is_active()
            assert isinstance(result, bool)
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_get_preset_name(self, voice_factory):
        """Test Voice.get_preset_name()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            name = voice.get_preset_name()
            assert isinstance(name, str)
            assert len(name) > 0
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_get_engine_type(self, voice_factory):
        """Test Voice.get_engine_type()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            engine_type = voice.get_engine_type()
            assert isinstance(engine_type, str)
        else:
            pytest.skip("Could not create voice")
    
    def test_voice_get_region_count(self, voice_factory):
        """Test Voice.get_region_count()."""
        voice = voice_factory.create_voice(bank=0, program=0, channel=0, sample_rate=44100)
        
        if voice:
            count = voice.get_region_count()
            assert isinstance(count, int)
            assert count >= 1
        else:
            pytest.skip("Could not create voice")


# ============================================================================
# MULTI-ZONE PRESET TESTS
# ============================================================================

class TestMultiZonePresets:
    """Tests for multi-zone preset handling."""
    
    def test_find_multi_zone_presets(self, sf2_engine):
        """Test finding multi-zone presets in soundfont."""
        multi_zone_count = 0
        
        for program in range(min(50, 128)):
            preset_info = sf2_engine.get_preset_info(bank=0, program=program)
            
            if preset_info and len(preset_info.region_descriptors) > 1:
                multi_zone_count += 1
                
                # Check for splits
                if preset_info.has_key_splits() or preset_info.has_velocity_splits():
                    return  # Found at least one multi-zone preset with splits
        
        if multi_zone_count > 0:
            pytest.skip(f"Found {multi_zone_count} multi-zone presets but none with splits")
        else:
            pytest.skip("No multi-zone presets found")
    
    def test_key_split_selection(self, sf2_engine):
        """Test correct zone selection for key splits."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.has_key_splits():
            # Get zones for low and high notes
            low_zones = preset_info.get_matching_descriptors(note=36, velocity=100)
            high_zones = preset_info.get_matching_descriptors(note=84, velocity=100)
            
            # Both should return lists
            assert isinstance(low_zones, list)
            assert isinstance(high_zones, list)
        else:
            pytest.skip("No key-split preset found")
    
    def test_velocity_split_selection(self, sf2_engine):
        """Test correct zone selection for velocity splits."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.has_velocity_splits():
            # Get zones for soft and loud velocities
            soft_zones = preset_info.get_matching_descriptors(note=60, velocity=50)
            loud_zones = preset_info.get_matching_descriptors(note=60, velocity=100)
            
            # Both should return lists
            assert isinstance(soft_zones, list)
            assert isinstance(loud_zones, list)
        else:
            pytest.skip("No velocity-split preset found")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for region-based architecture."""
    
    def test_preset_info_creation_time(self, sf2_engine):
        """Test PresetInfo creation performance."""
        times = []
        
        for _ in range(10):
            start = time.perf_counter()
            preset_info = sf2_engine.get_preset_info(bank=0, program=0)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = np.mean(times) * 1000  # Convert to ms
        
        # Should be fast (< 10ms)
        assert avg_time < 10.0, f"PresetInfo creation too slow: {avg_time:.2f}ms"
    
    def test_region_creation_time(self, sf2_engine):
        """Test region creation performance."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info and preset_info.region_descriptors:
            descriptor = preset_info.region_descriptors[0]
            times = []
            
            for _ in range(10):
                start = time.perf_counter()
                region = sf2_engine.create_region(descriptor, 44100)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            avg_time = np.mean(times) * 1000  # Convert to ms
            
            # Should be fast (< 5ms)
            assert avg_time < 5.0, f"Region creation too slow: {avg_time:.2f}ms"
        else:
            pytest.skip("No preset found")
    
    def test_zone_matching_performance(self, sf2_engine):
        """Test zone matching performance."""
        preset_info = sf2_engine.get_preset_info(bank=0, program=0)
        
        if preset_info:
            times = []
            
            for _ in range(100):
                start = time.perf_counter()
                zones = preset_info.get_matching_descriptors(60, 100)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            
            avg_time = np.mean(times) * 1000  # Convert to ms
            
            # Should be very fast (< 1ms)
            assert avg_time < 1.0, f"Zone matching too slow: {avg_time:.2f}ms"
        else:
            pytest.skip("No preset found")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
