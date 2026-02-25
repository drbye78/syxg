"""
SF2 Integration Tests with Reference Soundfont

Tests the complete SF2 synthesis pipeline using a real SF2 file.
Requires: tests/ref.sf2 (reference soundfont file)
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock


# ============================================================================
# Fixtures for Reference Soundfont Testing
# ============================================================================

@pytest.fixture
def ref_sf2_path() -> Path:
    """Get path to reference SF2 file."""
    ref_path = Path(__file__).parent / "ref.sf2"
    if not ref_path.exists():
        pytest.skip(f"Reference SF2 file not found at {ref_path}")
    return ref_path


@pytest.fixture
def engine_with_ref_sf2(ref_sf2_path, mock_synth):
    """Create SF2Engine with reference soundfont loaded."""
    from synth.engine.sf2_engine import SF2Engine
    
    engine = SF2Engine(
        sf2_file_path=str(ref_sf2_path),
        sample_rate=44100,
        block_size=1024,
        synth=mock_synth
    )
    return engine


@pytest.fixture
def soundfont_with_ref_sf2(ref_sf2_path):
    """Load reference soundfont directly."""
    from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
    
    manager = SF2SoundFontManager()
    if ref_sf2_path.exists():
        manager.load_soundfont(str(ref_sf2_path))
    else:
        pytest.skip(f"Reference SF2 file not found at {ref_sf2_path}")
    
    return manager


# ============================================================================
# Soundfont Loading Tests
# ============================================================================

class TestSF2FileLoading:
    """Test SF2 file loading with real soundfont."""
    
    def test_load_reference_soundfont(self, ref_sf2_path):
        """Should load reference soundfont successfully."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager()
        result = manager.load_soundfont(str(ref_sf2_path))
        
        assert result is True
        assert len(manager) == 1
        assert ref_sf2_path.name in str(manager.loaded_files.keys())
    
    def test_soundfont_metadata(self, soundfont_with_ref_sf2):
        """Should extract soundfont metadata."""
        info = soundfont_with_ref_sf2.get_soundfont_info()
        
        if isinstance(info, list) and len(info) > 0:
            sf_info = info[0]
            assert 'name' in sf_info or 'bank_name' in sf_info
    
    def test_get_available_programs(self, soundfont_with_ref_sf2):
        """Should list available programs from soundfont."""
        programs = soundfont_with_ref_sf2.get_available_programs()
        
        # Should have at least one program
        assert len(programs) > 0
        
        # Each program should be (bank, program, name) tuple
        for bank, program, name in programs:
            assert isinstance(bank, int)
            assert isinstance(program, int)
            assert isinstance(name, str)
            assert 0 <= bank <= 127
            assert 0 <= program <= 127


# ============================================================================
# Preset Lookup Tests
# ============================================================================

class TestSF2PresetLookup:
    """Test preset lookup with real soundfont."""
    
    def test_get_preset_info(self, engine_with_ref_sf2):
        """Should retrieve preset info from loaded soundfont."""
        # Get first available program
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available in reference soundfont")
        
        bank, program, name = programs[0]
        
        # Get preset info
        preset_info = engine_with_ref_sf2.get_preset_info(bank, program)
        
        if preset_info:
            assert preset_info.name == name
            assert preset_info.bank == bank
            assert preset_info.program == program
            assert len(preset_info.region_descriptors) >= 0
    
    def test_get_all_region_descriptors(self, engine_with_ref_sf2):
        """Should retrieve all region descriptors for a preset."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        descriptors = engine_with_ref_sf2.get_all_region_descriptors(bank, program)
        
        # Should return list of descriptors
        assert isinstance(descriptors, list)


# ============================================================================
# Region Matching Tests
# ============================================================================

class TestSF2RegionMatching:
    """Test region matching with real soundfont."""
    
    def test_region_note_matching(self, engine_with_ref_sf2):
        """Should match regions correctly for different notes."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        descriptors = engine_with_ref_sf2.get_all_region_descriptors(bank, program)
        
        if not descriptors:
            pytest.skip("No regions available")
        
        # Test that regions match notes within their range
        for descriptor in descriptors:
            key_low, key_high = descriptor.key_range
            
            # Note within range should match
            if key_low <= 60 <= key_high:
                assert descriptor.should_play_for_note(60, 100) is True
            
            # Note outside range should not match
            if key_high < 60:
                assert descriptor.should_play_for_note(60, 100) is False
            if key_low > 60:
                assert descriptor.should_play_for_note(60, 100) is False
    
    def test_region_velocity_matching(self, engine_with_ref_sf2):
        """Should match regions correctly for different velocities."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        descriptors = engine_with_ref_sf2.get_all_region_descriptors(bank, program)
        
        if not descriptors:
            pytest.skip("No regions available")
        
        # Test velocity matching
        for descriptor in descriptors:
            vel_low, vel_high = descriptor.velocity_range
            
            # Velocity within range should match
            if vel_low <= 100 <= vel_high:
                assert descriptor.should_play_for_note(60, 100) is True
            
            # Velocity outside range should not match
            if vel_high < 100:
                assert descriptor.should_play_for_note(60, 100) is False
            if vel_low > 100:
                assert descriptor.should_play_for_note(60, 100) is False


# ============================================================================
# Sample Loading Tests
# ============================================================================

class TestSF2SampleLoading:
    """Test sample loading with real soundfont."""
    
    def test_get_sample_data(self, soundfont_with_ref_sf2):
        """Should retrieve sample data from soundfont."""
        # Get sample info for first sample
        # This tests the sample loading pipeline
        sample_data = soundfont_with_ref_sf2.get_sample_data(0)
        
        # May return None if sample 0 doesn't exist, but shouldn't crash
        # If data exists, verify it's valid
        if sample_data is not None:
            assert isinstance(sample_data, np.ndarray)
            assert len(sample_data) > 0
            assert sample_data.dtype in [np.float32, np.int16, np.int32]
    
    def test_get_sample_info(self, soundfont_with_ref_sf2):
        """Should retrieve sample information."""
        sample_info = soundfont_with_ref_sf2.get_sample_info(0)
        
        # May return None if sample 0 doesn't exist
        if sample_info is not None:
            assert isinstance(sample_info, dict)
            # Should have at least some sample information
            assert 'name' in sample_info or 'original_pitch' in sample_info or 'sample_rate' in sample_info


# ============================================================================
# Audio Generation Tests
# ============================================================================

class TestSF2AudioGeneration:
    """Test audio generation with real soundfont."""
    
    def test_generate_samples_with_preset(self, engine_with_ref_sf2):
        """Should generate audio for a preset."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        
        # Generate audio
        audio = engine_with_ref_sf2.generate_samples(
            note=60,
            velocity=100,
            modulation={},
            block_size=1024,
            bank=bank,
            program=program
        )
        
        # Should return valid audio buffer
        assert isinstance(audio, np.ndarray)
        assert len(audio) == 2048  # block_size * 2
        assert audio.dtype == np.float32
        
        # Audio may be silence if no sample loaded, but shouldn't crash
    
    def test_generate_samples_multiple_notes(self, engine_with_ref_sf2):
        """Should generate audio for different notes."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        
        # Test multiple notes
        for note in [48, 60, 72]:  # C3, C4, C5
            audio = engine_with_ref_sf2.generate_samples(
                note=note,
                velocity=100,
                modulation={},
                block_size=1024,
                bank=bank,
                program=program
            )
            
            assert len(audio) == 2048
            assert audio.dtype == np.float32
    
    def test_generate_samples_multiple_velocities(self, engine_with_ref_sf2):
        """Should generate audio for different velocities."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        
        # Test multiple velocities
        for velocity in [50, 100, 127]:
            audio = engine_with_ref_sf2.generate_samples(
                note=60,
                velocity=velocity,
                modulation={},
                block_size=1024,
                bank=bank,
                program=program
            )
            
            assert len(audio) == 2048
            assert audio.dtype == np.float32


# ============================================================================
# Loop Mode Tests
# ============================================================================

class TestSF2LoopModes:
    """Test SF2 loop modes with real soundfont."""
    
    def test_sample_loop_info(self, soundfont_with_ref_sf2):
        """Should retrieve sample loop information."""
        loop_info = soundfont_with_ref_sf2.get_sample_loop_info(0)
        
        # May return None if sample doesn't exist
        if loop_info is not None:
            assert isinstance(loop_info, dict)
            # Should have loop information
            assert 'start' in loop_info or 'end' in loop_info or 'mode' in loop_info
    
    def test_loop_mode_values(self, soundfont_with_ref_sf2):
        """Should have valid loop mode values."""
        for sample_id in range(5):  # Test first 5 samples
            loop_info = soundfont_with_ref_sf2.get_sample_loop_info(sample_id)
            
            if loop_info is not None:
                mode = loop_info.get('mode', 0)
                # Valid SF2 loop modes: 0=no loop, 1=forward, 2=backward, 3=loop+continue
                assert mode in [0, 1, 2, 3], f"Invalid loop mode {mode} for sample {sample_id}"


# ============================================================================
# Memory and Cache Tests
# ============================================================================

class TestSF2MemoryManagement:
    """Test SF2 memory management with real soundfont."""
    
    def test_soundfont_unload(self, ref_sf2_path):
        """Should unload soundfont and clear caches."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager()
        manager.load_soundfont(str(ref_sf2_path))
        
        assert len(manager) == 1
        
        # Unload
        manager.unload_soundfont(str(ref_sf2_path))
        
        assert len(manager) == 0
    
    def test_memory_usage_stats(self, soundfont_with_ref_sf2):
        """Should report memory usage statistics."""
        stats = soundfont_with_ref_sf2.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert 'loaded_files' in stats
        assert 'memory_usage' in stats or 'file_stats' in stats


# ============================================================================
# Modulation Tests
# ============================================================================

class TestSF2Modulation:
    """Test SF2 modulation with real soundfont."""
    
    def test_modulation_envelope_parameters(self, mock_synth):
        """Should support modulation envelope to volume/pan (Issue #1 fix)."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = {
            'sample_data': np.zeros(1000, dtype=np.float32),
            'note': 60,
            'velocity': 100,
            'mod_envelope': {
                'to_pitch': 0.5,
                'to_volume': 0.3,  # NEW
                'to_pan': 0.2,      # NEW
            }
        }
        
        partial = SF2Partial(params, mock_synth)
        
        # Should load modulation envelope parameters
        assert hasattr(partial, 'mod_env_to_volume')
        assert hasattr(partial, 'mod_env_to_pan')
        assert partial.mod_env_to_volume == 0.3
        assert partial.mod_env_to_pan == 0.2


# ============================================================================
# Performance Tests
# ============================================================================

class TestSF2Performance:
    """Test SF2 performance with real soundfont."""
    
    def test_audio_generation_latency(self, engine_with_ref_sf2):
        """Should generate audio with low latency."""
        import time
        
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        
        # Measure generation time
        start = time.perf_counter()
        audio = engine_with_ref_sf2.generate_samples(
            note=60,
            velocity=100,
            modulation={},
            block_size=1024,
            bank=bank,
            program=program
        )
        elapsed = time.perf_counter() - start
        
        # Should complete in < 10ms for 1024 samples at 44.1kHz
        # (1024/44100 = 23ms budget, but we want much faster)
        assert elapsed < 0.010, f"Audio generation took {elapsed*1000:.2f}ms, expected < 10ms"
    
    def test_concurrent_note_generation(self, engine_with_ref_sf2):
        """Should handle concurrent note generation."""
        programs = engine_with_ref_sf2.soundfont_manager.get_available_programs()
        if not programs:
            pytest.skip("No programs available")
        
        bank, program, name = programs[0]
        
        # Generate multiple notes in sequence (simulates polyphony)
        for i in range(10):
            audio = engine_with_ref_sf2.generate_samples(
                note=60 + i,
                velocity=100,
                modulation={},
                block_size=1024,
                bank=bank,
                program=program
            )
            assert len(audio) == 2048


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
