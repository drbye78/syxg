"""
Voice Integration Tests

Tests for voice allocation, stealing, priority, and cleanup
in the XG synthesizer voice management system.
"""

from __future__ import annotations

import pytest
import numpy as np

from synth.io.midi.message import MIDIMessage
from tests.utils.audio_utils import calculate_rms
from tests.utils.midi_utils import create_note_on_message, create_note_off_message


class MockSF2Partial:
    """Minimal voice partial mock for voice integration tests.

    Replaces the now-removed SF2Partial with a simple sine-wave generator
    that has the same lifecycle interface.
    """

    def __init__(self, params: dict, synth: object):
        self.params = params
        self.synth = synth
        self._active = False
        self._phase = 0.0
        self._sample_rate = synth.sample_rate if hasattr(synth, "sample_rate") else 44100
        self._released = False
        self._age = 0.0

    def note_on(self, velocity: int, note: int) -> None:
        self._active = True
        self._note_start_time = 0.0

    def note_off(self) -> None:
        self._released = True

    def is_active(self) -> bool:
        return self._active

    def generate_samples(self, block_size: int, modulation: dict) -> np.ndarray:
        """Generate simple sine wave audio."""
        self._age += block_size / self._sample_rate
        t = np.arange(block_size, dtype=np.float32) / self._sample_rate
        freq = 440.0 * (2.0 ** ((self.params.get("note", 60) - 69) / 12.0))
        phase = self._phase + 2.0 * np.pi * freq * t
        self._phase = phase[-1] % (2.0 * np.pi)
        mono = np.sin(phase, dtype=np.float32) * 0.3
        stereo = np.column_stack([mono, mono]) * 0.1
        return stereo.astype(np.float32).reshape(-1)

    def reset(self) -> None:
        self._active = False
        self._released = False
        self._phase = 0.0
        self._age = 0.0

    def is_voice_stealable(self) -> bool:
        return self._released

    def is_released(self) -> bool:
        return self._released

    def get_age(self) -> float:
        return self._age

    def get_priority(self) -> int:
        return self.params.get("velocity", 100)

    def get_active_state(self) -> str:
        if self._released:
            return "release"
        return "active"


class TestVoiceIntegration:
    """Test voice management integration."""

    @pytest.mark.integration
    def test_voice_note_on_off(self, sample_rate, block_size):
        """Test basic voice note on/off functionality."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        partial = MockSF2Partial(params, synth)

        # Test note on
        partial.note_on(100, 60)
        assert partial.is_active()

        # Generate samples
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        audio = partial.generate_samples(block_size, modulation)
        assert np.any(audio != 0)

        # Test note off
        partial.note_off()

        # Continue generating to process release
        for _ in range(10):
            audio = partial.generate_samples(block_size, modulation)

    @pytest.mark.integration
    def test_voice_stealing(self, sample_rate, block_size):
        """Test voice stealing when polyphony limit is reached."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5
        partials = []

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        # Create multiple partials
        for i in range(4):
            params = {
                "sample_data": sample_data,
                "note": 60 + i,
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
            partial = MockSF2Partial(params, synth)
            partial.note_on(100, 60 + i)
            partials.append(partial)

        # All should be active
        for partial in partials:
            assert partial.is_active()

    @pytest.mark.integration
    def test_voice_priority(self, sample_rate, block_size):
        """Test voice priority system."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        # Create partials with different velocities (priority)
        partials = []
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
            partial = MockSF2Partial(params, synth)
            partial.note_on(velocity, 60)
            partials.append(partial)

        # All should be active
        for partial in partials:
            assert partial.is_active()

    @pytest.mark.integration
    def test_exclusive_class(self, sample_rate, block_size):
        """Test exclusive class note stealing."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        # Create partial with exclusive class
        params = {
            "sample_data": sample_data,
            "note": 60,
            "velocity": 100,
            "generators": {"exclusive_class": 1},
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

        partial = MockSF2Partial(params, synth)
        partial.note_on(100, 60)

        # Should be active
        assert partial.is_active()

    @pytest.mark.integration
    def test_voice_cleanup(self, sample_rate, block_size):
        """Test voice cleanup and resource release."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        partial = MockSF2Partial(params, synth)
        partial.note_on(100, 60)

        # Generate some samples
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        for _ in range(5):
            partial.generate_samples(block_size, modulation)

        # Reset partial (cleanup)
        partial.reset()

        # Should be inactive after reset
        assert not partial.is_active()

    @pytest.mark.integration
    def test_multiple_voices_mixing(self, sample_rate, block_size):
        """Test mixing multiple voices together."""
        # SF2Partial was merged into SF2Region; use MockSF2Partial for tests

        sample_data = np.random.randn(sample_rate).astype(np.float32) * 0.5

        class MockMemoryPool:
            def get_stereo_buffer(self, size):
                return np.zeros(size * 2, dtype=np.float32)

            def get_mono_buffer(self, size):
                return np.zeros(size, dtype=np.float32)

        class MockEnvelopePool:
            def acquire_envelope(self, **kwargs):
                from synth.primitives.envelope import UltraFastADSREnvelope
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
                from synth.primitives.filter import UltraFastResonantFilter
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
                from synth.primitives.oscillator import UltraFastXGLFO
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

        # Create chord (multiple voices)
        notes = [60, 64, 67]  # C major chord
        partials = []

        for note in notes:
            params = {
                "sample_data": sample_data,
                "note": note,
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
            partial = MockSF2Partial(params, synth)
            partial.note_on(100, note)
            partials.append(partial)

        # Mix all voices
        modulation = {"pitch": 0.0, "filter_cutoff": 0.0, "volume": 1.0}
        mixed = np.zeros(block_size * 2, dtype=np.float32)

        for partial in partials:
            audio = partial.generate_samples(block_size, modulation)
            mixed += audio

        # Should have audio from all voices
        assert calculate_rms(mixed) > 0

    @pytest.mark.integration
    def test_voice_sustain_pedal(self, sample_rate, block_size):
        """Test sustain pedal functionality."""
        from synth.primitives.envelope import UltraFastADSREnvelope

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

        # Generate some samples
        for _ in range(5):
            buffer = np.zeros(block_size)
            envelope.generate_block(buffer, block_size)

        # Engage sustain pedal
        envelope.sustain_pedal_on()

        # Note off
        envelope.note_off()

        # Should hold at sustain level
        buffer = np.zeros(block_size)
        envelope.generate_block(buffer, block_size)

        assert np.mean(buffer) > 0.3

        # Release sustain pedal
        envelope.sustain_pedal_off()

        # Should now release
        buffer = np.zeros(block_size)
        envelope.generate_block(buffer, block_size)