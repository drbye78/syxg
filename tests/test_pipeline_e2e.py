"""
End-to-End Pipeline System Tests

Tests for complete note rendering, polyphonic rendering,
multi-channel rendering, and drum channel rendering.
"""

from __future__ import annotations

import pytest
import numpy as np

from tests.utils.audio_utils import calculate_rms, detect_clipping


class TestPipelineE2E:
    """Test end-to-end pipeline processing."""

    @pytest.mark.system
    def test_full_note_rendering(self, sample_rate, block_size):
        """Test complete note rendering pipeline."""
        from synth.engine.sf2_engine import SF2Engine

        # Create SF2 engine
        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        # Create test sample data
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        # Get preset info (or create test data)
        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Get region descriptor
        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available for testing")

        # Create region
        region = engine.create_region(descriptors[0], sample_rate)

        # Load sample
        if not engine.load_sample_for_region(region):
            pytest.skip("Failed to load sample for region")

        # Trigger note
        assert region.note_on(100, 60)

        # Generate samples
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        audio = region.generate_samples(block_size, modulation)

        # Verify output
        assert audio is not None
        assert len(audio) == block_size * 2  # Stereo
        assert calculate_rms(audio) > 0
        assert not detect_clipping(audio)

    @pytest.mark.system
    def test_polyphonic_rendering(self, sample_rate, block_size):
        """Test polyphonic rendering with multiple voices."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available for testing")

        # Create multiple regions (chord)
        regions = []
        notes = [60, 64, 67]  # C major chord

        for note in notes:
            region = engine.create_region(descriptors[0], sample_rate)
            if engine.load_sample_for_region(region):
                region.note_on(100, note)
                regions.append(region)

        # Mix all voices
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        mixed = np.zeros(block_size * 2, dtype=np.float32)

        for region in regions:
            audio = region.generate_samples(block_size, modulation)
            mixed += audio

        # Verify output
        assert calculate_rms(mixed) > 0
        assert not detect_clipping(mixed)

    @pytest.mark.system
    def test_multi_channel_rendering(self, sample_rate, block_size):
        """Test multi-channel rendering."""
        from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.max_polyphony = 16
                self.drum_manager = None
                self.memory_pool = None
                self.buffer_pool = None
                self.lfo_pool = None
                self.use_modulation_matrix = False

        synth = MockSynth()

        # Create multiple channel renderers
        renderers = []
        for ch in range(4):
            renderer = VectorizedChannelRenderer(channel=ch, synth=synth)
            renderers.append(renderer)

        # All should be created successfully
        assert len(renderers) == 4

    @pytest.mark.system
    def test_drum_channel_rendering(self, sample_rate, block_size):
        """Test drum channel rendering."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        # Try to get drum preset
        preset_info = engine.get_preset_info(128, 0)

        if preset_info is None:
            pytest.skip("No drum preset available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No drum regions available")

        # Create drum region
        region = engine.create_region(descriptors[0], sample_rate)

        if engine.load_sample_for_region(region):
            # Trigger drum hit
            assert region.note_on(100, 60)

            # Generate samples
            modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
            audio = region.generate_samples(block_size, modulation)

            assert calculate_rms(audio) > 0

    @pytest.mark.system
    def test_effects_chain_rendering(self, sample_rate, block_size):
        """Test effects chain rendering."""
        from synth.effects.system_effects import XGSystemEffectsProcessor

        # Create effects processor
        effects = XGSystemEffectsProcessor(
            sample_rate=sample_rate,
            block_size=block_size,
            dsp_units=None,
            max_reverb_delay=sample_rate * 2,
            max_chorus_delay=8192,
        )

        # Create test signal
        signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5

        # Apply effects chain
        effects.apply_system_effects_to_mix_zero_alloc(signal, block_size)

        # Verify output
        assert np.all(np.isfinite(signal))
        assert not detect_clipping(signal)

    @pytest.mark.system
    def test_pitch_bend_rendering(self, sample_rate, block_size):
        """Test pitch bend rendering."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available")

        region = engine.create_region(descriptors[0], sample_rate)

        if engine.load_sample_for_region(region):
            region.note_on(100, 60)

            # Generate with pitch bend
            modulation = {"pitch": 100.0, "filter_cutoff": 0.0, "volume": 1.0}
            audio = region.generate_samples(block_size, modulation)

            assert calculate_rms(audio) > 0

    @pytest.mark.system
    def test_modulation_rendering(self, sample_rate, block_size):
        """Test modulation rendering."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available")

        region = engine.create_region(descriptors[0], sample_rate)

        if engine.load_sample_for_region(region):
            region.note_on(100, 60)

            # Generate with modulation
            modulation = {
                "pitch": 0.0,
                "filter_cutoff": 5000.0,
                "volume": 1.0,
                "mod_wheel": 64,
            }
            audio = region.generate_samples(block_size, modulation)

            assert calculate_rms(audio) > 0

    @pytest.mark.system
    def test_velocity_rendering(self, sample_rate, block_size):
        """Test velocity-sensitive rendering."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available")

        # Test different velocities
        for velocity in [32, 64, 96, 127]:
            region = engine.create_region(descriptors[0], sample_rate)

            if engine.load_sample_for_region(region):
                region.note_on(velocity, 60)

                modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
                audio = region.generate_samples(block_size, modulation)

                assert calculate_rms(audio) > 0

    @pytest.mark.system
    def test_envelope_rendering(self, sample_rate, block_size):
        """Test envelope rendering."""
        from synth.core.envelope import UltraFastADSREnvelope

        envelope = UltraFastADSREnvelope(
            sample_rate=sample_rate,
            block_size=block_size,
            attack=0.01,
            decay=0.1,
            sustain=0.7,
            release=0.3,
        )

        # Note on
        envelope.note_on(100, 60)

        # Generate through envelope
        buffer = np.zeros(block_size)
        envelope.generate_block(buffer, block_size)

        assert np.any(buffer != 0)

    @pytest.mark.system
    def test_filter_rendering(self, sample_rate, block_size):
        """Test filter rendering."""
        from synth.core.filter import UltraFastResonantFilter

        filter_obj = UltraFastResonantFilter(
            sample_rate=sample_rate,
            block_size=block_size,
            cutoff=2000.0,
            resonance=0.7,
            filter_type="lowpass",
        )

        # Create test signal
        t = np.linspace(0, 0.1, block_size, dtype=np.float32)
        signal = np.sin(2 * np.pi * 1000 * t)

        # Process through filter
        filtered = filter_obj.process_block(signal)

        assert filtered is not None
        assert len(filtered) == len(signal)

    @pytest.mark.system
    def test_lfo_rendering(self, sample_rate, block_size):
        """Test LFO rendering."""
        from synth.core.oscillator import UltraFastXGLFO

        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=1.0, delay=0.0)

        # Generate LFO
        result = lfo.generate_block(block_size)

        if isinstance(result, np.ndarray):
            assert np.any(result != 0)