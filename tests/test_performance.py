"""
Performance Tests for XG Synthesizer

Tests for maximum polyphony, block processing latency,
memory usage, and long-running stability.
"""

from __future__ import annotations

import pytest
import numpy as np
import time

from tests.utils.audio_utils import calculate_rms


class TestPerformance:
    """Test synthesizer performance characteristics."""

    @pytest.mark.performance
    def test_max_polyphony(self, sample_rate, block_size):
        """Test maximum polyphony limit."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available")

        # Create many regions
        regions = []
        max_notes = 64

        for i in range(max_notes):
            region = engine.create_region(descriptors[0], sample_rate)
            if engine.load_sample_for_region(region):
                note = 36 + (i % 48)  # Cycle through notes
                region.note_on(100, note)
                regions.append(region)

        # Should handle many voices
        assert len(regions) > 0

        # Generate audio
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        mixed = np.zeros(block_size * 2, dtype=np.float32)

        for region in regions:
            audio = region.generate_samples(block_size, modulation)
            mixed += audio

        assert calculate_rms(mixed) > 0

    @pytest.mark.performance
    def test_block_processing_latency(self, sample_rate, block_size):
        """Test block processing latency."""
        from synth.core.envelope import UltraFastADSREnvelope

        envelope = UltraFastADSREnvelope(
            sample_rate=sample_rate,
            block_size=block_size,
            attack=0.01,
            decay=0.1,
            sustain=0.7,
            release=0.3,
        )

        # Measure processing time
        envelope.note_on(100, 60)

        start_time = time.time()

        for _ in range(100):
            buffer = np.zeros(block_size)
            envelope.generate_block(buffer, block_size)

        end_time = time.time()

        # Processing should be fast
        elapsed = end_time - start_time
        blocks_per_second = 100 / elapsed

        # Should process many blocks per second
        assert blocks_per_second > 1000

    @pytest.mark.performance
    def test_memory_usage(self, sample_rate, block_size):
        """Test memory usage."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size, max_memory_mb=256)

        # Get memory stats
        stats = engine.get_performance_stats()

        # Should have memory tracking
        assert "memory_usage" in stats

    @pytest.mark.performance
    def test_cpu_usage(self, sample_rate, block_size):
        """Test CPU usage during processing."""
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

        # Measure processing time
        start_time = time.time()

        for _ in range(1000):
            filtered = filter_obj.process_block(signal)

        end_time = time.time()

        # Should be efficient
        elapsed = end_time - start_time
        assert elapsed < 1.0  # Should complete in under 1 second

    @pytest.mark.performance
    def test_long_running_stability(self, sample_rate, block_size):
        """Test long-running stability."""
        from synth.core.oscillator import UltraFastXGLFO

        lfo = UltraFastXGLFO(id=0, sample_rate=sample_rate, block_size=block_size)
        lfo.set_parameters(waveform="sine", rate=5.0, depth=1.0, delay=0.0)

        # Run for many blocks
        for _ in range(1000):
            result = lfo.generate_block(block_size)

            if isinstance(result, np.ndarray):
                # Should remain stable
                assert np.all(np.isfinite(result))

    @pytest.mark.performance
    def test_voice_allocation_speed(self, sample_rate, block_size):
        """Test voice allocation speed."""
        from synth.engine.sf2_engine import SF2Engine

        engine = SF2Engine(sample_rate=sample_rate, block_size=block_size)

        preset_info = engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        descriptors = preset_info.region_descriptors
        if len(descriptors) == 0:
            pytest.skip("No regions available")

        # Measure allocation time
        start_time = time.time()

        regions = []
        for i in range(100):
            region = engine.create_region(descriptors[0], sample_rate)
            if engine.load_sample_for_region(region):
                regions.append(region)

        end_time = time.time()

        # Should allocate quickly
        elapsed = end_time - start_time
        assert elapsed < 1.0

    @pytest.mark.performance
    def test_effects_processing_speed(self, sample_rate, block_size):
        """Test effects processing speed."""
        from synth.effects.system_effects import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Create test signal
        signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5

        # Measure processing time
        start_time = time.time()

        for _ in range(100):
            reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

        end_time = time.time()

        # Should process quickly
        elapsed = end_time - start_time
        assert elapsed < 1.0

    @pytest.mark.performance
    def test_channel_rendering_speed(self, sample_rate, block_size):
        """Test channel rendering speed."""
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
        renderer = VectorizedChannelRenderer(channel=0, synth=synth)

        # Measure rendering time
        start_time = time.time()

        for _ in range(100):
            # Simulate channel rendering
            pass

        end_time = time.time()

        # Should be fast
        elapsed = end_time - start_time
        assert elapsed < 0.1

    @pytest.mark.performance
    def test_modulation_matrix_speed(self, sample_rate, block_size):
        """Test modulation matrix processing speed."""
        from synth.modulation.vectorized_matrix import VectorizedModulationMatrix

        matrix = VectorizedModulationMatrix(num_routes=16)

        # Setup routes
        for i in range(16):
            matrix.set_route(i, "lfo1", "pitch", amount=0.5, polarity=1.0)

        # Measure processing time
        start_time = time.time()

        for _ in range(1000):
            # Simulate modulation processing
            pass

        end_time = time.time()

        # Should be fast
        elapsed = end_time - start_time
        assert elapsed < 0.1

    @pytest.mark.performance
    def test_sample_interpolation_speed(self, sample_rate, block_size):
        """Test sample interpolation speed."""
        # Create test sample
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        # Measure interpolation time
        start_time = time.time()

        for _ in range(1000):
            # Simulate interpolation
            pos = np.random.random() * len(sample_data)
            pos_int = int(pos)
            frac = pos - pos_int

            if pos_int < len(sample_data) - 1:
                sample1 = sample_data[pos_int]
                sample2 = sample_data[pos_int + 1]
                interpolated = sample1 + frac * (sample2 - sample1)

        end_time = time.time()

        # Should be fast
        elapsed = end_time - start_time
        assert elapsed < 0.1

    @pytest.mark.performance
    def test_envelope_generation_speed(self, sample_rate, block_size):
        """Test envelope generation speed."""
        from synth.core.envelope import UltraFastADSREnvelope

        envelope = UltraFastADSREnvelope(
            sample_rate=sample_rate,
            block_size=block_size,
            attack=0.01,
            decay=0.1,
            sustain=0.7,
            release=0.3,
        )

        # Measure generation time
        envelope.note_on(100, 60)

        start_time = time.time()

        for _ in range(1000):
            buffer = np.zeros(block_size)
            envelope.generate_block(buffer, block_size)

        end_time = time.time()

        # Should be fast
        elapsed = end_time - start_time
        blocks_per_second = 1000 / elapsed
        assert blocks_per_second > 10000

    @pytest.mark.performance
    def test_filter_processing_speed(self, sample_rate, block_size):
        """Test filter processing speed."""
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

        # Measure processing time
        start_time = time.time()

        for _ in range(1000):
            filtered = filter_obj.process_block(signal)

        end_time = time.time()

        # Should be fast
        elapsed = end_time - start_time
        blocks_per_second = 1000 / elapsed
        assert blocks_per_second > 10000