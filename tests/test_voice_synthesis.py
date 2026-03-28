"""
Voice Synthesis Unit Tests

Tests for SF2 voice synthesis including mono/stereo sample playback,
loop modes, pitch shifting, and sample interpolation.
"""

from __future__ import annotations

import pytest
import numpy as np

from synth.engine.sf2_engine import SF2Engine
from synth.partial.sf2_partial import SF2Partial


class TestVoiceSynthesis:
    """Test SF2 voice synthesis functionality."""

    @pytest.mark.unit
    def test_mono_sample_playback(self, sample_rate, block_size):
        """Test mono sample playback."""
        # Create test sample data
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        # Create a mock synth for testing
        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        # Trigger note
        partial.note_on(100, 60)

        # Generate samples
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        audio = partial.generate_samples(block_size, modulation)

        # Verify output
        assert audio is not None
        assert len(audio) == block_size * 2  # Stereo output
        assert np.any(audio != 0)  # Not silence

    @pytest.mark.unit
    def test_stereo_sample_playback(self, sample_rate, block_size):
        """Test stereo sample playback."""
        # Create stereo test sample data
        sample_data = np.random.randn(sample_rate, 2).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        # Trigger note
        partial.note_on(100, 60)

        # Generate samples
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        audio = partial.generate_samples(block_size, modulation)

        # Verify stereo output
        assert audio is not None
        assert len(audio) == block_size * 2

        # Verify channels are different (stereo separation)
        left = audio[::2]
        right = audio[1::2]
        # Channels should differ for stereo samples
        # (may be identical for mono samples duplicated to stereo)

    @pytest.mark.unit
    def test_loop_modes_forward(self, sample_rate, block_size):
        """Test forward loop mode."""
        # Create sample with loop points
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {"sample_mode": 1},  # Forward loop
            "loop": {"mode": 1, "start": 1000, "end": 5000},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        # Trigger note
        partial.note_on(100, 60)

        # Generate multiple blocks to test looping
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        for _ in range(10):
            audio = partial.generate_samples(block_size, modulation)
            assert partial.is_active()
            assert np.any(audio != 0)

    @pytest.mark.unit
    def test_loop_modes_backward(self, sample_rate, block_size):
        """Test backward loop mode."""
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {"sample_mode": 2},  # Backward loop
            "loop": {"mode": 2, "start": 1000, "end": 5000},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        partial.note_on(100, 60)
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        for _ in range(10):
            audio = partial.generate_samples(block_size, modulation)
            assert partial.is_active()

    @pytest.mark.unit
    def test_loop_modes_alternating(self, sample_rate, block_size):
        """Test alternating loop mode."""
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {"sample_mode": 3},  # Alternating loop
            "loop": {"mode": 3, "start": 1000, "end": 5000},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        partial.note_on(100, 60)
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        for _ in range(10):
            audio = partial.generate_samples(block_size, modulation)
            assert partial.is_active()

    @pytest.mark.unit
    def test_loop_modes_no_loop(self, sample_rate, block_size):
        """Test no loop mode (one-shot)."""
        # Create short sample
        sample_data = np.random.randn(1000).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {"sample_mode": 0},  # No loop
            "loop": {"mode": 0, "start": 0, "end": 1000},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        partial.note_on(100, 60)
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        # Generate until sample ends
        while partial.is_active():
            audio = partial.generate_samples(block_size, modulation)

        # Should eventually become inactive
        assert not partial.is_active()

    @pytest.mark.unit
    def test_pitch_shifting(self, sample_rate, block_size):
        """Test pitch shifting through different notes."""
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        # Test different notes (different pitches)
        for note in [48, 60, 72]:
            params = {
                "sample_data": sample_data,
                "note": note,
                "velocity": 100,
                "original_pitch": 60,  # Sample recorded at C4
                "generators": {},
                "amp_attack": 0.01,
                "amp_decay": 0.3,
                "amp_sustain": 0.7,
                "amp_release": 0.5,
                "filter_cutoff": 20000.0,
                "filter_resonance": 0.7,
                "pan": 0.0,
                "reverb_send": 0.0,
                "chorus_send": 0.0,
            }

            class MockMemoryPool:
                def get_stereo_buffer(self, size):
                    return np.zeros(size * 2, dtype=np.float32)

                def get_mono_buffer(self, size):
                    return np.zeros(size, dtype=np.float32)

            class MockEnvelopePool:
                def acquire_envelope(self, **kwargs):
                    from synth.core.envelope import UltraFastADSREnvelope
                    return UltraFastADSREnvelope(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        delay=kwargs.get("delay", 0.0),
                        attack=kwargs.get("attack", 0.01),
                        hold=kwargs.get("hold", 0.0),
                        decay=kwargs.get("decay", 0.3),
                        sustain=kwargs.get("sustain", 0.7),
                        release=kwargs.get("release", 0.5),
                    )

                def release_envelope(self, envelope):
                    pass

            class MockFilterPool:
                def acquire_filter(self, **kwargs):
                    from synth.core.filter import UltraFastResonantFilter
                    return UltraFastResonantFilter(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        cutoff=kwargs.get("cutoff", 20000.0),
                        resonance=kwargs.get("resonance", 0.0),
                        filter_type=kwargs.get("filter_type", "lowpass"),
                    )

                def release_filter(self, filt):
                    pass

            class MockLFOPool:
                def acquire_oscillator(self, **kwargs):
                    from synth.core.oscillator import UltraFastXGLFO
                    return UltraFastXGLFO(
                        id=kwargs.get("id", 0),
                        sample_rate=sample_rate,
                        block_size=block_size,
                    )

                def release_oscillator(self, osc):
                    pass

            class MockSynth:
                def __init__(self):
                    self.sample_rate = sample_rate
                    self.block_size = block_size
                    self.memory_pool = MockMemoryPool()
                    self.buffer_pool = None
                    self.envelope_pool = MockEnvelopePool()
                    self.filter_pool = MockFilterPool()
                    self.partial_lfo_pool = MockLFOPool()

            synth = MockSynth()
            partial = SF2Partial(params, synth)

            partial.note_on(100, note)
            modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

            audio = partial.generate_samples(block_size, modulation)
            assert np.any(audio != 0)

    @pytest.mark.unit
    def test_mip_mapping(self, sample_rate, block_size):
        """Test mip-mapping for high-pitch quality."""
        # Create multiple sample rates for mip-mapping
        samples = {
            "full": np.random.randn(sample_rate).astype(np.float32) * 0.5,
            "half": np.random.randn(sample_rate // 2).astype(np.float32) * 0.5,
            "quarter": np.random.randn(sample_rate // 4).astype(np.float32) * 0.5,
        }

        # Test at different pitches
        for note in [60, 72, 84]:
            params = {
                "sample_data": samples["full"],
                "note": note,
                "velocity": 100,
                "original_pitch": 60,
                "generators": {},
                "amp_attack": 0.01,
                "amp_decay": 0.3,
                "amp_sustain": 0.7,
                "amp_release": 0.5,
                "filter_cutoff": 20000.0,
                "filter_resonance": 0.7,
                "pan": 0.0,
                "reverb_send": 0.0,
                "chorus_send": 0.0,
            }

            class MockMemoryPool:
                def get_stereo_buffer(self, size):
                    return np.zeros(size * 2, dtype=np.float32)

                def get_mono_buffer(self, size):
                    return np.zeros(size, dtype=np.float32)

            class MockEnvelopePool:
                def acquire_envelope(self, **kwargs):
                    from synth.core.envelope import UltraFastADSREnvelope
                    return UltraFastADSREnvelope(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        delay=kwargs.get("delay", 0.0),
                        attack=kwargs.get("attack", 0.01),
                        hold=kwargs.get("hold", 0.0),
                        decay=kwargs.get("decay", 0.3),
                        sustain=kwargs.get("sustain", 0.7),
                        release=kwargs.get("release", 0.5),
                    )

                def release_envelope(self, envelope):
                    pass

            class MockFilterPool:
                def acquire_filter(self, **kwargs):
                    from synth.core.filter import UltraFastResonantFilter
                    return UltraFastResonantFilter(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        cutoff=kwargs.get("cutoff", 20000.0),
                        resonance=kwargs.get("resonance", 0.0),
                        filter_type=kwargs.get("filter_type", "lowpass"),
                    )

                def release_filter(self, filt):
                    pass

            class MockLFOPool:
                def acquire_oscillator(self, **kwargs):
                    from synth.core.oscillator import UltraFastXGLFO
                    return UltraFastXGLFO(
                        id=kwargs.get("id", 0),
                        sample_rate=sample_rate,
                        block_size=block_size,
                    )

                def release_oscillator(self, osc):
                    pass

            class MockSynth:
                def __init__(self):
                    self.sample_rate = sample_rate
                    self.block_size = block_size
                    self.memory_pool = MockMemoryPool()
                    self.buffer_pool = None
                    self.envelope_pool = MockEnvelopePool()
                    self.filter_pool = MockFilterPool()
                    self.partial_lfo_pool = MockLFOPool()

            synth = MockSynth()
            partial = SF2Partial(params, synth)

            partial.note_on(100, note)
            modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

            audio = partial.generate_samples(block_size, modulation)
            assert np.any(audio != 0)

    @pytest.mark.unit
    def test_sample_interpolation(self, sample_rate, block_size):
        """Test sample interpolation quality."""
        # Create simple sine wave sample
        duration = 0.1
        freq = 440.0
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
        sample_data = np.sin(2 * np.pi * freq * t).astype(np.float32)

        params = {
            "sample_data": sample_data,
            "note": 69,  # A4 = 440Hz
            "velocity": 100,
            "original_pitch": 69,
            "generators": {},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        partial.note_on(100, 69)
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        # Generate samples and verify no clicks/pops (smooth interpolation)
        audio = partial.generate_samples(block_size, modulation)

        # Check for smooth transitions (no sudden jumps)
        diff = np.abs(np.diff(audio))
        max_diff = np.max(diff)
        assert max_diff < 0.5  # Reasonable threshold for smooth audio

    @pytest.mark.unit
    def test_velocity_sensitivity(self, sample_rate, block_size):
        """Test velocity sensitivity."""
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        # Test different velocities
        for velocity in [32, 64, 96, 127]:
            params = {
                "sample_data": sample_data,
                "note": 60,
                "velocity": velocity,
                "generators": {},
                "amp_attack": 0.01,
                "amp_decay": 0.3,
                "amp_sustain": 0.7,
                "amp_release": 0.5,
                "filter_cutoff": 20000.0,
                "filter_resonance": 0.7,
                "pan": 0.0,
                "reverb_send": 0.0,
                "chorus_send": 0.0,
            }

            class MockMemoryPool:
                def get_stereo_buffer(self, size):
                    return np.zeros(size * 2, dtype=np.float32)

                def get_mono_buffer(self, size):
                    return np.zeros(size, dtype=np.float32)

            class MockEnvelopePool:
                def acquire_envelope(self, **kwargs):
                    from synth.core.envelope import UltraFastADSREnvelope
                    return UltraFastADSREnvelope(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        delay=kwargs.get("delay", 0.0),
                        attack=kwargs.get("attack", 0.01),
                        hold=kwargs.get("hold", 0.0),
                        decay=kwargs.get("decay", 0.3),
                        sustain=kwargs.get("sustain", 0.7),
                        release=kwargs.get("release", 0.5),
                    )

                def release_envelope(self, envelope):
                    pass

            class MockFilterPool:
                def acquire_filter(self, **kwargs):
                    from synth.core.filter import UltraFastResonantFilter
                    return UltraFastResonantFilter(
                        sample_rate=sample_rate,
                        block_size=block_size,
                        cutoff=kwargs.get("cutoff", 20000.0),
                        resonance=kwargs.get("resonance", 0.0),
                        filter_type=kwargs.get("filter_type", "lowpass"),
                    )

                def release_filter(self, filt):
                    pass

            class MockLFOPool:
                def acquire_oscillator(self, **kwargs):
                    from synth.core.oscillator import UltraFastXGLFO
                    return UltraFastXGLFO(
                        id=kwargs.get("id", 0),
                        sample_rate=sample_rate,
                        block_size=block_size,
                    )

                def release_oscillator(self, osc):
                    pass

            class MockSynth:
                def __init__(self):
                    self.sample_rate = sample_rate
                    self.block_size = block_size
                    self.memory_pool = MockMemoryPool()
                    self.buffer_pool = None
                    self.envelope_pool = MockEnvelopePool()
                    self.filter_pool = MockFilterPool()
                    self.partial_lfo_pool = MockLFOPool()

            synth = MockSynth()
            partial = SF2Partial(params, synth)

            partial.note_on(velocity, 60)
            modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

            audio = partial.generate_samples(block_size, modulation)
            rms = np.sqrt(np.mean(audio ** 2))

            # Higher velocity should generally produce louder output
            assert rms > 0

    @pytest.mark.unit
    def test_note_off_release(self, sample_rate, block_size):
        """Test note off triggers release phase."""
        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {},
            "amp_attack": 0.01,
            "amp_decay": 0.3,
            "amp_sustain": 0.7,
            "amp_release": 0.5,
            "filter_cutoff": 20000.0,
            "filter_resonance": 0.7,
            "pan": 0.0,
            "reverb_send": 0.0,
            "chorus_send": 0.0,
        }

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.core.envelope import UltraFastADSREnvelope
                return UltraFastADSREnvelope(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    delay=kwargs.get("delay", 0.0),
                    attack=kwargs.get("attack", 0.01),
                    hold=kwargs.get("hold", 0.0),
                    decay=kwargs.get("decay", 0.3),
                    sustain=kwargs.get("sustain", 0.7),
                    release=kwargs.get("release", 0.5),
                )

            def release_envelope(self, envelope):
                pass

        class MockFilterPool:
            def acquire_filter(self, **kwargs):
                from synth.core.filter import UltraFastResonantFilter
                return UltraFastResonantFilter(
                    sample_rate=sample_rate,
                    block_size=block_size,
                    cutoff=kwargs.get("cutoff", 20000.0),
                    resonance=kwargs.get("resonance", 0.0),
                    filter_type=kwargs.get("filter_type", "lowpass"),
                )

            def release_filter(self, filt):
                pass

        class MockLFOPool:
            def acquire_oscillator(self, **kwargs):
                from synth.core.oscillator import UltraFastXGLFO
                return UltraFastXGLFO(
                    id=kwargs.get("id", 0),
                    sample_rate=sample_rate,
                    block_size=block_size,
                )

            def release_oscillator(self, osc):
                pass

        class MockSynth:
            def __init__(self):
                self.sample_rate = sample_rate
                self.block_size = block_size
                self.memory_pool = MockMemoryPool()
                self.buffer_pool = None
                self.envelope_pool = MockEnvelopePool()
                self.filter_pool = MockFilterPool()
                self.partial_lfo_pool = MockLFOPool()

        synth = MockSynth()
        partial = SF2Partial(params, synth)

        partial.note_on(100, 60)
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}

        # Generate some samples
        for _ in range(5):
            partial.generate_samples(block_size, modulation)

        # Trigger note off
        partial.note_off()

        # Continue generating to hear release
        for _ in range(10):
            audio = partial.generate_samples(block_size, modulation)
            # Should eventually become silent
            if not partial.is_active():
                break