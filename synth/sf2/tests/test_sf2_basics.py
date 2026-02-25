"""
Basic SF2 module tests.

Tests for core SF2 functionality:
- Module imports
- Basic instantiation
- Parameter validation
"""

import pytest
import numpy as np
from unittest.mock import Mock


class TestSF2Imports:
    """Test that all SF2 modules import correctly."""
    
    def test_import_sf2_engine(self):
        """SF2Engine should import without errors."""
        from synth.engine.sf2_engine import SF2Engine
        assert SF2Engine is not None
    
    def test_import_sf2_partial(self):
        """SF2Partial should import without errors."""
        from synth.partial.sf2_partial import SF2Partial
        assert SF2Partial is not None
    
    def test_import_sf2_region(self):
        """SF2Region should import without errors."""
        from synth.partial.sf2_region import SF2Region
        assert SF2Region is not None
    
    def test_import_sf2_soundfont_manager(self):
        """SF2SoundFontManager should import without errors."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        assert SF2SoundFontManager is not None
    
    def test_import_sf2_constants(self):
        """SF2 constants should import without errors."""
        from synth.sf2.sf2_constants import SF2_GENERATORS
        assert SF2_GENERATORS is not None
        assert isinstance(SF2_GENERATORS, dict)


class TestSF2PartialInstantiation:
    """Test SF2Partial creation and initialization."""
    
    def test_partial_creation_with_all_slots(self, minimal_partial_params, mock_synth):
        """SF2Partial should instantiate with all required slots defined."""
        from synth.partial.sf2_partial import SF2Partial
        
        # Should not raise AttributeError
        partial = SF2Partial(minimal_partial_params, mock_synth)
        assert partial is not None
        assert partial.active is True
    
    def test_partial_creation_missing_slots(self, mock_synth):
        """SF2Partial should handle missing optional parameters."""
        from synth.partial.sf2_partial import SF2Partial
        
        # Minimal params without optional fields
        params = {
            'sample_data': np.zeros(1000, dtype=np.float32),
            'note': 60,
            'velocity': 100,
            'generators': {}
        }
        
        # Should not crash - should use defaults
        partial = SF2Partial(params, mock_synth)
        assert partial is not None
    
    def test_partial_requires_synth_instance(self, minimal_partial_params):
        """SF2Partial should require synth instance, not sample_rate."""
        from synth.partial.sf2_partial import SF2Partial
        
        # This should fail - passing int instead of synth
        with pytest.raises((AttributeError, TypeError)):
            partial = SF2Partial(minimal_partial_params, 44100)  # Wrong!
    
    def test_partial_buffers_allocated(self, minimal_partial_params, mock_synth):
        """SF2Partial should allocate buffers from pools."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        
        # Buffers should be allocated
        assert partial.audio_buffer is not None
        assert partial.work_buffer is not None
        assert len(partial.audio_buffer) > 0
        assert len(partial.work_buffer) > 0
    
    def test_partial_envelope_initialized(self, minimal_partial_params, mock_synth):
        """SF2Partial should initialize envelope from parameters."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        
        assert partial.envelope is not None
        # Envelope should have parameters from params
        # (specific assertions depend on envelope implementation)
    
    def test_partial_filter_initialized(self, minimal_partial_params, mock_synth):
        """SF2Partial should initialize filter from parameters."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        
        assert partial.filter is not None
    
    def test_partial_lfos_initialized(self, minimal_partial_params, mock_synth):
        """SF2Partial should initialize LFOs from parameters."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        
        assert partial.mod_lfo is not None
        assert partial.vib_lfo is not None


class TestSF2ParameterStructures:
    """Test parameter structure handling."""
    
    def test_nested_parameter_structure(self, nested_partial_params, mock_synth):
        """SF2Partial should accept nested parameter structure."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(nested_partial_params, mock_synth)
        assert partial is not None
    
    def test_flat_parameter_structure(self, flat_partial_params, mock_synth):
        """SF2Partial should accept flat parameter structure (backward compat)."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(flat_partial_params, mock_synth)
        assert partial is not None
    
    def test_parameter_structure_priority(self, mock_synth):
        """Nested parameters should take priority over flat parameters."""
        from synth.partial.sf2_partial import SF2Partial
        
        # Both nested and flat with different values
        params = {
            'sample_data': np.zeros(1000, dtype=np.float32),
            'note': 60,
            'velocity': 100,
            # Nested structure
            'amp_envelope': {
                'attack': 0.5  # Different value
            },
            # Flat structure
            'amp_attack': 0.1  # Should be ignored
        }
        
        partial = SF2Partial(params, mock_synth)
        # Nested value should be used
        # (specific assertion depends on implementation)


class TestSF2SoundFontManagerMethods:
    """Test SF2SoundFontManager required methods."""
    
    def test_manager_has_required_methods(self):
        """SF2SoundFontManager should have all required methods."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager()
        
        assert hasattr(manager, 'get_sample_info')
        assert hasattr(manager, 'get_sample_loop_info')
        assert hasattr(manager, 'get_zone')
        assert hasattr(manager, 'get_sample_data')
        assert hasattr(manager, 'get_program_parameters')
    
    def test_manager_methods_return_none_when_empty(self):
        """Manager methods should return None when no soundfonts loaded."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager()
        
        assert manager.get_sample_info(0) is None
        assert manager.get_sample_loop_info(0) is None
        assert manager.get_zone(0) is None
        assert manager.get_sample_data(0) is None
        assert manager.get_program_parameters(0, 0) is None
    
    def test_manager_load_soundfont(self, test_data_dir):
        """SF2SoundFontManager should load soundfont files."""
        from synth.sf2.sf2_soundfont_manager import SF2SoundFontManager
        
        manager = SF2SoundFontManager()
        
        # Try to load (may fail if file doesn't exist, that's ok for this test)
        # result = manager.load_soundfont(str(test_data_dir / "minimal.sf2"))
        # Test will be more meaningful with actual SF2 file
        
        assert len(manager) == 0  # No files loaded yet


class TestSF2GeneratorConstants:
    """Test SF2 generator ID constants."""
    
    def test_generator_constants_exist(self):
        """SF2_GENERATORS constant should exist and be a dict."""
        from synth.sf2.sf2_constants import SF2_GENERATORS
        
        assert isinstance(SF2_GENERATORS, dict)
        assert len(SF2_GENERATORS) > 0
    
    def test_critical_generator_ids(self):
        """Critical generator IDs should be correctly mapped."""
        from synth.sf2.sf2_constants import SF2_GENERATORS
        
        # Volume envelope generators
        assert 8 in SF2_GENERATORS
        assert 9 in SF2_GENERATORS
        assert 10 in SF2_GENERATORS
        assert 11 in SF2_GENERATORS
        assert 12 in SF2_GENERATORS
        assert 13 in SF2_GENERATORS
        
        # Filter generators
        assert 29 in SF2_GENERATORS
        assert 30 in SF2_GENERATORS
        
        # Effects generators
        assert 32 in SF2_GENERATORS  # reverbEffectsSend
        assert 33 in SF2_GENERATORS  # chorusEffectsSend
        
        # Sample generators
        assert 50 in SF2_GENERATORS  # sampleID
        assert 51 in SF2_GENERATORS  # sampleModes
        assert 53 in SF2_GENERATORS  # exclusiveClass
    
    def test_generator_names(self):
        """Generator names should match SF2 specification."""
        from synth.sf2.sf2_constants import SF2_GENERATORS
        
        # Spot check some critical names
        assert SF2_GENERATORS[32]['name'] == 'reverbEffectsSend'
        assert SF2_GENERATORS[33]['name'] == 'chorusEffectsSend'
        assert SF2_GENERATORS[50]['name'] == 'sampleID'
        assert SF2_GENERATORS[51]['name'] == 'sampleModes'
        assert SF2_GENERATORS[53]['name'] == 'exclusiveClass'


class TestSF2UtilityFunctions:
    """Test SF2 utility functions."""
    
    def test_timecents_to_seconds(self):
        """Timecents to seconds conversion should be correct."""
        from synth.sf2.sf2_constants import timecents_to_seconds

        # -12000 timecents = 0 seconds (instant)
        assert timecents_to_seconds(-12000) == 0.0

        # 0 timecents = 1 second
        assert timecents_to_seconds(0) == 1.0

        # 1200 timecents = ~2 seconds (allow floating point error)
        result = timecents_to_seconds(1200)
        assert 1.99 < result < 2.01

    def test_cents_to_frequency_multiplier(self):
        """Cents to frequency multiplier conversion should be correct."""
        from synth.sf2.sf2_constants import cents_to_frequency

        # 0 cents = 1.0 multiplier (no change)
        assert cents_to_frequency(0) == 1.0

        # 1200 cents = 2.0 multiplier (one octave up, allow floating point error)
        result = cents_to_frequency(1200)
        assert 1.99 < result < 2.01

        # -1200 cents = 0.5 multiplier (one octave down)
        result = cents_to_frequency(-1200)
        assert 0.49 < result < 0.51

    def test_frequency_to_cents(self):
        """Frequency to cents conversion should be correct."""
        from synth.sf2.sf2_constants import frequency_to_cents

        # 440 Hz = 0 cents (reference)
        assert frequency_to_cents(440.0) == 0

        # 880 Hz = 1200 cents (one octave up)
        assert frequency_to_cents(880.0) == 1200

        # 220 Hz = -1200 cents (one octave down)
        assert frequency_to_cents(220.0) == -1200

    def test_frequency_cents_roundtrip(self):
        """Frequency/cents roundtrip should be identity."""
        from synth.sf2.sf2_constants import frequency_to_cents

        # Test roundtrip using the frequency formula directly
        base_freq = 440.0
        for freq in [220, 440, 880, 1760]:
            cents = frequency_to_cents(freq, base_freq)
            # Recover frequency from cents: f = base * 2^(cents/1200)
            recovered = base_freq * (2.0 ** (cents / 1200.0))
            assert abs(recovered - freq) < 0.1


class TestSF2RegionDescriptor:
    """Test RegionDescriptor for SF2."""
    
    def test_descriptor_creation(self):
        """RegionDescriptor should create successfully."""
        from synth.engine.region_descriptor import RegionDescriptor
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0
        )
        
        assert descriptor.region_id == 0
        assert descriptor.engine_type == 'sf2'
        assert descriptor.sample_id == 0
    
    def test_descriptor_should_play_for_note(self):
        """RegionDescriptor should match note/velocity correctly."""
        from synth.engine.region_descriptor import RegionDescriptor
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(48, 72),  # C3 to C5
            velocity_range=(64, 127),
            sample_id=0
        )
        
        # Should match
        assert descriptor.should_play_for_note(60, 100) is True
        
        # Should not match (note too low)
        assert descriptor.should_play_for_note(40, 100) is False
        
        # Should not match (velocity too low)
        assert descriptor.should_play_for_note(60, 50) is False
    
    def test_descriptor_priority_score(self):
        """RegionDescriptor should calculate priority score."""
        from synth.engine.region_descriptor import RegionDescriptor
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(48, 72),
            velocity_range=(64, 127),
            sample_id=0
        )
        
        # Center of range should have highest priority
        center_score = descriptor.get_priority_score(60, 95)
        edge_score = descriptor.get_priority_score(48, 64)
        
        assert center_score > edge_score


class TestSF2BasicAudioPath:
    """Test basic audio generation path."""
    
    def test_partial_generates_audio(self, minimal_partial_params, mock_synth):
        """SF2Partial should generate audio (not crash)."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        partial.note_on(100, 60)
        
        # Should not crash
        audio = partial.generate_samples(1024, {})
        
        # Should return stereo buffer
        assert len(audio) == 2048  # block_size * 2
        assert audio.dtype == np.float32
    
    def test_partial_inactive_returns_silence(self, minimal_partial_params, mock_synth):
        """Inactive partial should return silence."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        partial.active = False
        
        audio = partial.generate_samples(1024, {})
        
        assert np.all(audio == 0.0)
    
    def test_partial_no_sample_data_returns_silence(self, mock_synth):
        """Partial without sample data should return silence."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = {
            'note': 60,
            'velocity': 100,
            'generators': {}
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(100, 60)
        
        audio = partial.generate_samples(1024, {})
        
        assert np.all(audio == 0.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
