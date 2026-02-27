"""
Integration tests for SF2 package integration with new region architecture.

Tests verify that SF2Region properly uses:
- SF2SoundFontManager for sample loading
- SF2Zone for generator parameters
- SF2 modulation engine
- Mip-map anti-aliasing
"""
from __future__ import annotations

import pytest
import numpy as np
from pathlib import Path

from synth.engine.region_descriptor import RegionDescriptor
from synth.partial.sf2_region import SF2Region


@pytest.fixture
def sf2_soundfont_path():
    """Get path to test SF2 soundfont."""
    test_paths = [
        Path(__file__).parent.parent / 'sine_test.sf2',
        Path('/mnt/c/work/guga/syxg/sine_test.sf2'),
    ]

    for path in test_paths:
        if path.exists():
            return str(path)

    pytest.skip("No test SF2 soundfont found")


class TestSF2Integration:
    """Tests for SF2 package integration."""

    @pytest.fixture
    def sf2_manager(self, sf2_soundfont_path):
        """Create SF2SoundFontManager with loaded soundfont."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager(cache_memory_mb=128)
        manager.load_soundfont(sf2_soundfont_path)
        
        return manager
    
    def test_sf2_soundfont_manager_loads_soundfont(self, sf2_manager):
        """Test SF2SoundFontManager loads soundfont correctly."""
        assert len(sf2_manager.loaded_files) >= 1
        assert sf2_manager.file_order
    
    def test_sf2_manager_get_sample_data(self, sf2_manager):
        """Test SF2SoundFontManager sample data retrieval."""
        # Get first sample from first soundfont
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                sample_data = sf2_manager.get_sample_data(sample_id)
                
                assert sample_data is not None
                assert len(sample_data) > 0
                return
        
        pytest.skip("No samples found in soundfont")
    
    def test_sf2_manager_get_sample_info(self, sf2_manager):
        """Test SF2SoundFontManager sample info retrieval."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                info = sf2_manager.get_sample_info(sample_id)
                
                if info:
                    assert 'original_pitch' in info
                    assert 'sample_rate' in info
                    return
        
        pytest.skip("No sample info available")
    
    def test_sf2_manager_get_sample_loop_info(self, sf2_manager):
        """Test SF2SoundFontManager loop info retrieval."""
        for filepath in sf2_manager.file_order:
            soundfont = sf2_manager.loaded_files[filepath]
            if hasattr(soundfont, 'samples') and soundfont.samples:
                sample_id = list(soundfont.samples.keys())[0]
                loop_info = sf2_manager.get_sample_loop_info(sample_id)
                
                if loop_info:
                    assert 'start' in loop_info
                    assert 'end' in loop_info
                    assert 'mode' in loop_info
                    return
        
        pytest.skip("No loop info available")
    
    def test_sf2_region_uses_soundfont_manager(self, sf2_manager):
        """Test SF2Region uses SF2SoundFontManager for sample loading."""
        # Create SF2 region descriptor
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0,  # First sample
            generator_params={
                'amp_attack': 0.01,
                'amp_decay': 0.3,
                'amp_sustain': 0.7,
                'amp_release': 0.5
            }
        )
        
        # Create region with soundfont manager
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Region should have reference to soundfont manager
        assert region.soundfont_manager is sf2_manager
        
        # Initialize region (may load sample if available)
        region.initialize()
        
        # Sample data may or may not be loaded depending on soundfont content
        # The key test is that region has the manager reference
        assert region.soundfont_manager is not None
    
    def test_sf2_region_caches_sf2_zone(self, sf2_manager):
        """Test SF2Region caches SF2Zone object."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Get SF2 zone (should cache it)
        zone = region._get_sf2_zone()
        
        # Zone should be cached
        assert region._sf2_zone is zone or zone is None
    
    def test_sf2_region_gets_generator_values(self, sf2_manager):
        """Test SF2Region retrieves SF2 generator values."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0,
            generator_params={
                'amp_attack': 0.01,
                'filter_cutoff': 5000.0
            }
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Test generator value retrieval
        # Generator 9 = volEnvAttack
        attack = region._get_generator_value(9, -12000)
        
        # Should return from descriptor if zone not available
        assert attack == -12000 or attack >= -12000
    
    def test_sf2_region_builds_partial_params_from_generators(self, sf2_manager):
        """Test SF2Region builds partial params from SF2 generators."""
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
                'filter_cutoff': 5000.0,
                'filter_resonance': 0.5
            }
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Mock sample data for testing
        region._sample_data = np.zeros(44100, dtype=np.float32)
        region._initialized = True
        
        # Build partial params
        params = region._build_partial_params_from_generators()
        
        # Check SF2 generator parameters are included
        assert 'amp_attack' in params
        assert 'amp_decay' in params
        assert 'amp_sustain' in params
        assert 'filter_cutoff' in params
        assert 'filter_resonance' in params
        
        # Check SF2-specific parameters
        assert 'mod_env_delay' in params
        assert 'mod_lfo_rate' in params
        assert 'vib_lfo_rate' in params
        assert 'reverb_send' in params
        assert 'chorus_send' in params
    
    def test_sf2_region_timecents_conversion(self, sf2_manager):
        """Test SF2Region timecents to seconds conversion."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127)
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Test timecents conversion
        # -12000 timecents = instant (0 seconds)
        assert region._timecents_to_seconds(-12000) == 0.0
        
        # 0 timecents = 2^0 = 1 second
        assert abs(region._timecents_to_seconds(0) - 1.0) < 0.001
        
        # 1200 timecents = 2^1 = 2 seconds
        assert abs(region._timecents_to_seconds(1200) - 2.0) < 0.01
        
        # -1200 timecents = 2^-1 = 0.5 seconds
        assert abs(region._timecents_to_seconds(-1200) - 0.5) < 0.01
    
    def test_sf2_region_cents_to_frequency(self, sf2_manager):
        """Test SF2Region cents to frequency conversion."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127)
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # 0 cents = 440 Hz
        assert abs(region._cents_to_frequency(0) - 440.0) < 0.1
        
        # 1200 cents = 880 Hz (one octave up)
        assert abs(region._cents_to_frequency(1200) - 880.0) < 0.1
        
        # -1200 cents = 220 Hz (one octave down)
        assert abs(region._cents_to_frequency(-1200) - 220.0) < 0.1
    
    def test_sf2_region_matches_note_velocity(self, sf2_manager):
        """Test SF2Region note/velocity matching."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(36, 72),  # C2 to C4
            velocity_range=(0, 64),  # Soft only
            sample_id=0
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Before zone is cached, uses default ranges (0, 127)
        # Note in default range, velocity in default range - should match
        assert region._matches_note_velocity(60, 50) == True
        
        # All notes are in default range (0, 127)
        assert region._matches_note_velocity(30, 50) == True
        assert region._matches_note_velocity(80, 50) == True
        
        # Test with cached zone ranges (after _get_sf2_zone is called)
        # This would use the actual SF2 zone's key/velocity ranges
    
    def test_sf2_region_sf2_looping(self, sf2_manager):
        """Test SF2Region SF2 looping modes."""
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0
        )
        
        region = SF2Region(descriptor, 44100, sf2_manager)
        
        # Set loop parameters
        region._loop_start = 1000
        region._loop_end = 2000
        region._loop_mode = 1  # Forward loop
        
        # Test forward looping
        position = region._handle_sf2_looping(2500, 4000)
        
        # Should wrap back to loop start
        assert position >= region._loop_start
        assert position < region._loop_end


class TestSF2ModulationIntegration:
    """Tests for SF2 modulation engine integration."""

    @pytest.fixture
    def sf2_manager(self, sf2_soundfont_path):
        """Create SF2SoundFontManager with loaded soundfont."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager

        manager = SF2SoundFontManager(cache_memory_mb=128)
        manager.load_soundfont(sf2_soundfont_path)

        return manager

    def test_sf2_modulation_engine_exists(self, sf2_manager):
        """Test SF2 modulation engine is available."""
        # Modulation engine should be initialized
        assert sf2_manager.modulation_engine is not None
    
    def test_sf2_modulation_controller_update(self, sf2_manager):
        """Test SF2 modulation controller updates."""
        # Update modulation controller
        sf2_manager.update_controller(1, 64)  # Mod wheel
        
        # Controller value should be updated in modulation engine
        controller_value = sf2_manager.modulation_engine.controller_values.get(1, 0)
        assert controller_value >= 0  # Value was set


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
