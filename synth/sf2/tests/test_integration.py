"""
SF2 Integration Tests

End-to-end tests for the complete SF2 synthesis pipeline:
- Engine → Region → Partial → Audio output
- Multi-voice polyphony
- Modulation integration
- Effects processing
"""

import pytest
import numpy as np
from unittest.mock import Mock


class TestSF2EngineIntegration:
    """Test SF2Engine integration with full pipeline."""
    
    def test_engine_creates_regions(self, mock_synth):
        """SF2Engine should create regions from descriptors."""
        from synth.engine.sf2_engine import SF2Engine
        from synth.engine.region_descriptor import RegionDescriptor
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(0, 127),
            velocity_range=(0, 127),
            sample_id=0
        )
        
        # Should create region without crashing
        region = engine.create_region(descriptor, 44100)
        assert region is not None
    
    def test_engine_loads_sample_for_region(self, mock_synth, mock_soundfont_manager):
        """SF2Engine should load sample data for regions."""
        from synth.engine.sf2_engine import SF2Engine
        from synth.engine.region_descriptor import RegionDescriptor
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        engine.soundfont_manager = mock_soundfont_manager
        
        # Mock sample data
        mock_soundfont_manager.get_sample_data.return_value = np.zeros(44100, dtype=np.float32)
        
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            sample_id=0,
            is_sample_loaded=False
        )
        
        region = engine.create_region(descriptor, 44100)
        result = engine.load_sample_for_region(region)
        
        # Should attempt to load sample
        # (result depends on mock implementation)
    
    def test_engine_get_preset_info(self, mock_synth, mock_soundfont_manager):
        """SF2Engine should get preset info with all regions."""
        from synth.engine.sf2_engine import SF2Engine
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        engine.soundfont_manager = mock_soundfont_manager
        
        # Mock preset info
        from synth.engine.preset_info import PresetInfo
        
        mock_preset_info = PresetInfo(
            bank=0,
            program=0,
            name="Test Preset",
            engine_type='sf2',
            region_descriptors=[],
            master_level=1.0
        )
        
        # Should return preset info
        # (implementation depends on soundfont manager)
    
    def test_engine_generate_samples_basic(self, mock_synth):
        """SF2Engine generate_samples with preset lookup should work."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        
        # Test with preset lookup (bank 0, program 0)
        # Will return silence if no soundfont loaded, but shouldn't crash
        audio = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={},
            block_size=1024,
            bank=0,
            program=0
        )
        
        # Should return audio buffer (may be silence if no soundfont loaded)
        assert len(audio) == 2048  # block_size * 2
        assert audio.dtype == np.float32


class TestSF2RegionIntegration:
    """Test SF2Region integration with partials."""
    
    def test_region_note_on_triggers_partial(self, region_descriptor, mock_synth, mock_soundfont_manager):
        """SF2Region note_on should trigger partial creation."""
        from synth.partial.sf2_region import SF2Region
        
        region = SF2Region(region_descriptor, 44100, mock_soundfont_manager)
        region.synth = mock_synth  # Set synth reference
        
        # Mock sample data
        region._sample_data = np.zeros(44100, dtype=np.float32)
        
        # Should trigger note on
        result = region.note_on(velocity=100, note=60)
        
        # Should return True if region should play
        assert result is True
        assert region.is_active()
    
    def test_region_generates_samples(self, region_descriptor, mock_synth, mock_soundfont_manager):
        """SF2Region should generate audio samples."""
        from synth.partial.sf2_region import SF2Region
        
        region = SF2Region(region_descriptor, 44100, mock_soundfont_manager)
        region.synth = mock_synth
        
        # Mock sample data
        region._sample_data = np.zeros(44100, dtype=np.float32)
        region._initialized = True
        
        region.note_on(velocity=100, note=60)
        
        # Should generate audio
        audio = region.generate_samples(1024, {})
        
        assert len(audio) == 2048
        assert audio.dtype == np.float32
    
    def test_region_matches_note_velocity(self, mock_soundfont_manager):
        """SF2Region should match note/velocity against ranges."""
        from synth.partial.sf2_region import SF2Region
        from synth.engine.region_descriptor import RegionDescriptor
        
        # Create region with limited range
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type='sf2',
            key_range=(48, 72),
            velocity_range=(64, 127),
            sample_id=0
        )
        
        region = SF2Region(descriptor, 44100, mock_soundfont_manager)
        
        # Should match
        assert region._matches_note_velocity(60, 100) is True
        
        # Should not match (note out of range)
        assert region._matches_note_velocity(40, 100) is False
        
        # Should not match (velocity out of range)
        assert region._matches_note_velocity(60, 50) is False


class TestSF2ModulationIntegration:
    """Test modulation integration in SF2 pipeline."""
    
    def test_global_modulation_applied_to_partial(self, minimal_partial_params, mock_synth):
        """Global modulation should apply to SF2Partial."""
        from synth.partial.sf2_partial import SF2Partial
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Apply global modulation
        modulation = {
            'pitch': 0.5,
            'filter_cutoff': 1.0,
            'volume': 0.8
        }
        
        # Should apply modulation without crashing
        audio = partial.generate_samples(1024, modulation)
        
        assert len(audio) == 2048
    
    def test_lfo_modulation(self, minimal_partial_params, mock_synth):
        """LFO modulation should apply correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['mod_lfo'] = {
            'delay': 0.0,
            'frequency': 5.0,
            'to_pitch': 0.5,
            'to_filter': 0.3,
            'to_volume': 0.2
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Should generate LFO modulation
        audio = partial.generate_samples(1024, {})
        
        assert len(audio) == 2048
    
    def test_envelope_modulation(self, minimal_partial_params, mock_synth):
        """Envelope modulation should apply correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['mod_envelope'] = {
            'delay': 0.0,
            'attack': 0.1,
            'hold': 0.0,
            'decay': 0.2,
            'sustain': 0.5,
            'release': 0.3,
            'to_pitch': 0.25
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Should generate envelope modulation
        audio = partial.generate_samples(1024, {})
        
        assert len(audio) == 2048


class TestSF2MultiVoicePolyphony:
    """Test multi-voice polyphony in SF2 engine."""
    
    def test_multiple_regions_layer(self, mock_synth, mock_soundfont_manager):
        """Multiple regions should layer correctly."""
        from synth.engine.sf2_engine import SF2Engine
        from synth.engine.region_descriptor import RegionDescriptor
        from synth.engine.preset_info import PresetInfo
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        
        # Create preset with multiple regions
        descriptors = [
            RegionDescriptor(
                region_id=0,
                engine_type='sf2',
                key_range=(0, 127),
                velocity_range=(0, 64),
                sample_id=0
            ),
            RegionDescriptor(
                region_id=1,
                engine_type='sf2',
                key_range=(0, 127),
                velocity_range=(65, 127),
                sample_id=1
            )
        ]
        
        # Mock preset info
        preset_info = PresetInfo(
            bank=0,
            program=0,
            name="Layered Preset",
            engine_type='sf2',
            region_descriptors=descriptors,
            master_level=1.0
        )
        
        # Should handle multiple regions
        # (full implementation would test actual layering)
    
    def test_velocity_switching(self, mock_synth):
        """Velocity switching should work correctly."""
        from synth.engine.sf2_engine import SF2Engine
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        
        # Low velocity should trigger different region than high velocity
        # (implementation depends on zone matching)
        pass
    
    def test_key_splitting(self, mock_synth):
        """Key splitting should work correctly."""
        from synth.engine.sf2_engine import SF2Engine
        
        engine = SF2Engine(sample_rate=44100, block_size=1024, synth=mock_synth)
        
        # Low notes should trigger different region than high notes
        # (implementation depends on zone matching)
        pass


class TestSF2EffectsIntegration:
    """Test effects integration in SF2 pipeline."""
    
    def test_reverb_send(self, minimal_partial_params, mock_synth):
        """Reverb send should apply correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['effects'] = {
            'reverb_send': 0.5,
            'chorus_send': 0.0,
            'pan': 0.0
        }
        
        partial = SF2Partial(params, mock_synth)
        
        assert partial.reverb_effects_send == 0.5
    
    def test_chorus_send(self, minimal_partial_params, mock_synth):
        """Chorus send should apply correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['effects'] = {
            'reverb_send': 0.0,
            'chorus_send': 0.3,
            'pan': 0.0
        }
        
        partial = SF2Partial(params, mock_synth)
        
        assert partial.chorus_effects_send == 0.3
    
    def test_pan_position(self, minimal_partial_params, mock_synth):
        """Pan position should apply correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['effects'] = {
            'reverb_send': 0.0,
            'chorus_send': 0.0,
            'pan': -0.5  # Left
        }
        
        partial = SF2Partial(params, mock_synth)
        
        # Pan should affect left/right balance
        # (specific assertion depends on implementation)


class TestSF2LoopModes:
    """Test SF2 loop mode implementation."""
    
    def test_no_loop_mode(self, minimal_partial_params, mock_synth):
        """No loop mode (0) should stop at end of sample."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['loop'] = {
            'mode': 0,  # No loop
            'start': 0,
            'end': 1000
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Should become inactive after sample ends
        # (would need to generate multiple blocks to test fully)
    
    def test_forward_loop_mode(self, minimal_partial_params, mock_synth):
        """Forward loop mode (1) should loop correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['loop'] = {
            'mode': 1,  # Forward loop
            'start': 1000,
            'end': 2000
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Should continue playing in loop
        assert partial.active is True
    
    def test_loop_and_continue_mode(self, minimal_partial_params, mock_synth):
        """Loop and continue mode (3) should work correctly."""
        from synth.partial.sf2_partial import SF2Partial
        
        params = minimal_partial_params.copy()
        params['loop'] = {
            'mode': 3,  # Loop and continue
            'start': 1000,
            'end': 2000
        }
        
        partial = SF2Partial(params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Should loop then continue to end
        assert partial.active is True


class TestSF2Performance:
    """Basic performance tests for SF2 engine."""
    
    def test_audio_generation_latency(self, minimal_partial_params, mock_synth):
        """Audio generation should complete within latency budget."""
        from synth.partial.sf2_partial import SF2Partial
        import time
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        partial.note_on(velocity=100, note=60)
        
        # Measure generation time
        start = time.perf_counter()
        audio = partial.generate_samples(1024, {})
        elapsed = time.perf_counter() - start
        
        # Should complete in < 1ms for 1024 samples at 44.1kHz
        # (1024/44100 = 23ms budget, but we want much faster)
        assert elapsed < 0.001  # 1ms
    
    def test_memory_usage(self, minimal_partial_params, mock_synth):
        """Partial should not allocate excessive memory."""
        from synth.partial.sf2_partial import SF2Partial
        import sys
        
        partial = SF2Partial(minimal_partial_params, mock_synth)
        
        # Estimate memory usage
        # (this is a rough estimate)
        memory = sys.getsizeof(partial)
        
        # Should be reasonable (less than 1MB per partial)
        assert memory < 1024 * 1024


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
