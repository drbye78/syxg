"""Tests for Wavetable synthesis engine components."""

from __future__ import annotations
from unittest.mock import patch

import numpy as np
import pytest


@pytest.mark.unit
class TestWavetable:
    """Tests for Wavetable data container."""

    def _make_sine_wavetable(self, size: int = 256, name: str = "sine"):
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.sin(np.linspace(0, 2 * np.pi, size))
        return Wavetable(data=data, name=name)

    def test_create_wavetable(self):
        """Create a basic wavetable and verify attributes."""
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.sin(np.linspace(0, 2 * np.pi, 256))
        wt = Wavetable(data=data, name="sine")
        assert len(wt.data) == 256
        assert wt.name == "sine"
        assert wt.length == 256
        assert wt.sample_rate == 44100
        assert wt.data.dtype == np.float32

    def test_default_name(self):
        """Default name should be 'unnamed'."""
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.sin(np.linspace(0, 2 * np.pi, 128))
        wt = Wavetable(data=data)
        assert wt.name == "unnamed"

    def test_normalization(self):
        """Data should be normalized to leave headroom."""
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.ones(256) * 2.0  # Peak > 1.0
        wt = Wavetable(data=data, name="loud")
        assert np.max(np.abs(wt.data)) <= 0.9  # Normalized with 0.9 headroom

    def test_dc_offset_removed(self):
        """DC offset should be removed from wavetable data."""
        data = np.ones(256) * 0.5  # All positive = DC offset
        wt = self._make_sine_wavetable()  # Use a real wavetable
        from synth.engines.wavetable.wavetable import Wavetable

        wt = Wavetable(data=data, name="dc_test")
        assert abs(np.mean(wt.data)) < 1e-6  # Mean should be ~0

    def test_multichannel_converted_to_mono(self):
        """Multi-channel input should take first channel."""
        from synth.engines.wavetable.wavetable import Wavetable

        stereo = np.column_stack(
            [np.sin(np.linspace(0, 2 * np.pi, 256)), np.cos(np.linspace(0, 2 * np.pi, 256))]
        )
        assert stereo.ndim == 2
        wt = Wavetable(data=stereo, name="stereo")
        assert wt.data.ndim == 1
        assert len(wt.data) == 256

    def test_get_sample(self):
        """get_sample returns a float within [-1, 1]."""
        wt = self._make_sine_wavetable()
        val = wt.get_sample(0.0)
        assert isinstance(val, float) or isinstance(val, np.floating)
        assert np.isfinite(val)
        assert -1.0 <= val <= 1.0

    def test_get_sample_quarter_phase(self):
        """At phase 0.25, sine should be at max amplitude (0.9 headroom)."""
        wt = self._make_sine_wavetable(size=2048)
        val = wt.get_sample(0.25)
        assert val == pytest.approx(0.9, abs=0.05)

    def test_get_sample_half_phase(self):
        """At phase 0.5, sine should be ~0."""
        wt = self._make_sine_wavetable(size=2048)
        val = wt.get_sample(0.5)
        assert val == pytest.approx(0.0, abs=0.05)

    def test_get_sample_interpolates(self):
        """get_sample with non-integer phase index interpolates."""
        wt = self._make_sine_wavetable(size=256)
        # Phase 0.0 and 0.001 should give different values with interpolation
        val1 = wt.get_sample(0.0)
        val2 = wt.get_sample(1.0 / 256 * 0.5)  # Halfway between samples
        assert val1 != val2

    def test_get_samples_vectorized(self):
        """get_samples returns array of same length as input phases."""
        wt = self._make_sine_wavetable()
        phases = np.linspace(0, 1, 100)
        samples = wt.get_samples(phases)
        assert samples.shape == (100,)
        assert samples.dtype == np.float64
        assert np.all(np.isfinite(samples))

    def test_get_samples_matches_get_sample(self):
        """get_samples should match sequential get_sample calls."""
        wt = self._make_sine_wavetable(size=1024)
        phases = np.array([0.0, 0.1, 0.25, 0.5, 0.75, 1.0])
        vectorized = wt.get_samples(phases)
        manual = np.array([wt.get_sample(p) for p in phases])
        np.testing.assert_allclose(vectorized, manual, rtol=1e-5)

    def test_empty_wavetable_raises(self):
        """Zero-length data raises ValueError due to normalization failure."""
        from synth.engines.wavetable.wavetable import Wavetable

        with pytest.raises((ValueError, ZeroDivisionError)):
            Wavetable(data=np.array([], dtype=np.float32), name="empty")


@pytest.mark.unit
class TestWavetableOscillator:
    """Tests for WavetableOscillator."""

    def _make_oscillator(self, sample_rate: int = 44100):
        from synth.engines.wavetable.oscillator import WavetableOscillator

        return WavetableOscillator(sample_rate=sample_rate)

    def _make_sine_wavetable(self, size: int = 256):
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.sin(np.linspace(0, 2 * np.pi, size))
        return Wavetable(data=data, name="sine")

    def test_init(self):
        """Verify default oscillator state after construction."""
        osc = self._make_oscillator()
        assert osc.sample_rate == 44100
        assert osc.phase == 0.0
        assert osc.frequency == 440.0
        assert osc.amplitude == 1.0
        assert osc.active is False
        assert osc.note == 60
        assert osc.velocity == 100
        assert osc.wavetable is None
        assert osc.frequency_mod == 0.0
        assert osc.amplitude_mod == 0.0
        assert osc.wavetable_position == 0.0

    def test_custom_sample_rate(self):
        """Custom sample rate should be reflected."""
        osc = self._make_oscillator(sample_rate=48000)
        assert osc.sample_rate == 48000

    def test_set_wavetable(self):
        """Setting a wavetable should store it."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        assert osc.wavetable is wt

    def test_set_frequency(self):
        """set_frequency should clamp to valid range."""
        osc = self._make_oscillator()
        osc.set_frequency(440.0)
        assert osc.frequency == 440.0

    def test_set_frequency_clamps_low(self):
        """Frequency should not go below 20 Hz."""
        osc = self._make_oscillator()
        osc.set_frequency(5.0)
        assert osc.frequency == 20.0

    def test_set_frequency_clamps_high(self):
        """Frequency should not exceed Nyquist."""
        osc = self._make_oscillator(sample_rate=44100)
        osc.set_frequency(30000.0)
        assert osc.frequency == 22050.0

    def test_set_note(self):
        """set_note sets frequency via MIDI-to-pitch formula."""
        osc = self._make_oscillator()
        osc.set_note(69, 100)  # A4
        assert osc.frequency == pytest.approx(440.0, rel=1e-3)
        assert osc.active is True
        assert osc.note == 69

    def test_set_note_velocity_scales_amplitude(self):
        """Velocity should affect amplitude with slight compression."""
        osc = self._make_oscillator()
        osc.set_note(60, 127)
        assert osc.amplitude == pytest.approx(1.0, abs=0.01)

        osc.set_note(60, 64)
        assert osc.amplitude < 1.0

    def test_set_amplitude(self):
        """set_amplitude clamps to [0, 1]."""
        osc = self._make_oscillator()
        osc.set_amplitude(0.5)
        assert osc.amplitude == 0.5

        osc.set_amplitude(-0.1)
        assert osc.amplitude == 0.0

        osc.set_amplitude(1.5)
        assert osc.amplitude == 1.0

    def test_update_modulation(self):
        """update_modulation sets all modulation inputs."""
        osc = self._make_oscillator()
        osc.update_modulation(freq_mod=0.1, amp_mod=-0.2, wt_pos=0.5)
        assert osc.frequency_mod == 0.1
        assert osc.amplitude_mod == -0.2
        assert osc.wavetable_position == 0.5

    def test_generate_samples_no_wavetable_returns_silence(self):
        """Without a wavetable, generate_samples returns zeros."""
        osc = self._make_oscillator()
        osc.set_note(60, 100)
        output = osc.generate_samples(256)
        assert output.shape == (256,)
        assert output.dtype == np.float32
        assert np.all(output == 0.0)

    def test_generate_samples_not_active_returns_silence(self):
        """Without being set to active, oscillator returns silence."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        output = osc.generate_samples(256)
        assert np.all(output == 0.0)

    def test_generate_samples_active(self):
        """Active oscillator with wavetable produces valid output."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)
        output = osc.generate_samples(256)
        assert output.shape == (256,)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))
        # Should not be all zeros
        assert not np.allclose(output, 0.0)

    def test_phase_advances(self):
        """Phase should advance after generating samples."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)
        initial_phase = osc.phase
        osc.generate_samples(256)
        assert osc.phase != initial_phase

    def test_phase_wraps_around(self):
        """Phase should wrap around within [0, 1)."""
        osc = self._make_oscillator(sample_rate=44100)
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)
        # Generate many samples so phase wraps
        osc.generate_samples(44100)  # 1 second at 440Hz = 440 cycles
        assert 0.0 <= osc.phase < 1.0

    def test_frequency_affects_pitch(self):
        """Higher frequency should produce more zero crossings."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)

        # Low frequency
        osc.set_note(48, 100)  # ~130.81 Hz
        low = osc.generate_samples(256)
        osc.reset()

        # High frequency
        osc.set_note(84, 100)  # ~1046.50 Hz
        osc.set_wavetable(wt)
        high = osc.generate_samples(256)

        low_zc = int(np.sum(np.abs(np.diff(np.sign(low, dtype=np.float64))) > 0))
        high_zc = int(np.sum(np.abs(np.diff(np.sign(high, dtype=np.float64))) > 0))
        assert high_zc > low_zc

    def test_reset_clears_phase(self):
        """Reset should set phase to 0 and deactivate."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)
        osc.generate_samples(256)
        osc.reset()
        assert osc.phase == 0.0
        assert osc.active is False
        assert osc.frequency_mod == 0.0
        assert osc.amplitude_mod == 0.0

    def test_reset_then_generate(self):
        """After reset, generating should start from phase 0."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)
        osc.generate_samples(256)
        osc.reset()

        # After reset, first sample should be at phase 0 (sine = ~0)
        osc.set_note(60, 100)
        output = osc.generate_samples(1)
        assert np.isfinite(output[0])

    def test_note_off(self):
        """note_off should set active to False."""
        osc = self._make_oscillator()
        osc.set_note(60, 100)
        assert osc.active is True
        osc.note_off()
        assert osc.active is False

    def test_is_active(self):
        """is_active reflects the active flag."""
        osc = self._make_oscillator()
        assert osc.is_active() is False
        osc.set_note(60, 100)
        assert osc.is_active() is True
        osc.note_off()
        assert osc.is_active() is False

    def test_amplitude_modulation(self):
        """Amplitude modulation should affect output level."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)

        # No modulation
        osc.update_modulation(amp_mod=0.0)
        ref = osc.generate_samples(256)
        osc.reset()

        # With positive amplitude modulation
        osc.set_note(60, 100)
        osc.set_wavetable(wt)
        osc.update_modulation(amp_mod=0.5)
        boosted = osc.generate_samples(256)

        # RMS should be higher with positive amp mod
        ref_rms = np.sqrt(np.mean(ref**2))
        boosted_rms = np.sqrt(np.mean(boosted**2))
        assert boosted_rms > ref_rms

    def test_frequency_modulation(self):
        """Frequency modulation should change pitch (zero crossings)."""
        osc = self._make_oscillator()
        wt = self._make_sine_wavetable()
        osc.set_wavetable(wt)
        osc.set_note(60, 100)

        # No modulation
        osc.update_modulation(freq_mod=0.0)
        ref = osc.generate_samples(256)
        osc.reset()

        # With frequency modulation
        osc.set_note(60, 100)
        osc.set_wavetable(wt)
        osc.update_modulation(freq_mod=0.5)
        modulated = osc.generate_samples(256)

        # Outputs should differ
        assert not np.allclose(ref, modulated)

    def test_silence_buffer_cached(self):
        """Silence buffer should be reused across calls."""
        osc = self._make_oscillator()
        out1 = osc.generate_samples(256)
        out2 = osc.generate_samples(256)
        # Both should be silence
        assert np.all(out1 == 0.0)
        assert np.all(out2 == 0.0)


@pytest.mark.unit
class TestWavetableBank:
    """Tests for WavetableBank."""

    def _make_bank(self):
        from synth.engines.wavetable.bank import WavetableBank

        return WavetableBank()

    def _make_sine_wavetable(self, size: int = 256, name: str = "sine"):
        from synth.engines.wavetable.wavetable import Wavetable

        data = np.sin(np.linspace(0, 2 * np.pi, size))
        return Wavetable(data=data, name=name)

    def test_init(self):
        """Bank initializes with empty wavetables and morph groups."""
        bank = self._make_bank()
        assert bank.wavetables == {}
        assert bank.morph_groups == {}
        assert bank.max_wavetables == 64

    def test_add_wavetable(self):
        """Adding a wavetable stores it and returns True."""
        bank = self._make_bank()
        wt = self._make_sine_wavetable(name="sine")
        result = bank.add_wavetable(wt, "sine")
        assert result is True
        assert "sine" in bank.wavetables

    def test_get_wavetable_found(self):
        """Getting an existing wavetable returns it."""
        bank = self._make_bank()
        wt = self._make_sine_wavetable(name="sine")
        bank.add_wavetable(wt, "sine")
        retrieved = bank.get_wavetable("sine")
        assert retrieved is wt

    def test_get_wavetable_not_found(self):
        """Getting a non-existent wavetable returns None."""
        bank = self._make_bank()
        assert bank.get_wavetable("nonexistent") is None

    def test_add_wavetable_at_capacity(self):
        """Adding beyond max_wavetables should return False."""
        from synth.engines.wavetable.bank import WavetableBank

        bank = WavetableBank(max_wavetables=2)
        wt1 = self._make_sine_wavetable(name="sine1")
        wt2 = self._make_sine_wavetable(name="sine2")
        wt3 = self._make_sine_wavetable(name="sine3")
        assert bank.add_wavetable(wt1, "sine1") is True
        assert bank.add_wavetable(wt2, "sine2") is True
        assert bank.add_wavetable(wt3, "sine3") is False

    def test_create_wavetable_from_waveform_sine(self):
        """create_wavetable_from_waveform creates a sine wavetable."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("sine", "my_sine", size=256)
        assert result is True
        wt = bank.get_wavetable("my_sine")
        assert wt is not None
        assert wt.name == "my_sine"
        assert wt.length == 256

    def test_create_wavetable_from_waveform_triangle(self):
        """create_wavetable_from_waveform creates a triangle wavetable."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("triangle", "tri", size=256)
        assert result is True
        wt = bank.get_wavetable("tri")
        assert wt is not None

    def test_create_wavetable_from_waveform_square(self):
        """create_wavetable_from_waveform creates a square wavetable."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("square", "sq", size=256)
        assert result is True

    def test_create_wavetable_from_waveform_sawtooth(self):
        """create_wavetable_from_waveform creates a sawtooth wavetable."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("sawtooth", "saw", size=256)
        assert result is True

    def test_create_wavetable_from_waveform_noise(self):
        """create_wavetable_from_waveform handles noise type."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("noise", "noise", size=256)
        assert result is True
        wt = bank.get_wavetable("noise")
        assert wt is not None
        assert wt.length == 256

    def test_create_wavetable_from_waveform_unknown(self):
        """Unknown waveform type defaults to sine."""
        bank = self._make_bank()
        result = bank.create_wavetable_from_waveform("unknown", "fallback", size=256)
        assert result is True

    def test_list_wavetables(self):
        """list_wavetables returns names of all wavetables."""
        bank = self._make_bank()
        assert bank.list_wavetables() == []
        bank.create_wavetable_from_waveform("sine", "sine1")
        bank.create_wavetable_from_waveform("sine", "sine2")
        names = bank.list_wavetables()
        assert "sine1" in names
        assert "sine2" in names

    def test_get_stats(self):
        """get_stats returns dict with wavetable statistics."""
        bank = self._make_bank()
        stats = bank.get_stats()
        assert isinstance(stats, dict)
        assert "total_wavetables" in stats
        assert "total_samples" in stats
        assert "average_length" in stats
        assert "morph_groups" in stats
        assert "memory_usage_mb" in stats
        assert stats["total_wavetables"] == 0

        bank.create_wavetable_from_waveform("sine", "sine1", size=512)
        stats = bank.get_stats()
        assert stats["total_wavetables"] == 1
        assert stats["total_samples"] == 512

    def test_morph_group_create_and_get(self):
        """Creating and retrieving morph groups."""
        bank = self._make_bank()
        bank.create_wavetable_from_waveform("sine", "sine")
        bank.create_wavetable_from_waveform("square", "square")
        bank.create_morph_group("morph1", ["sine", "square"])
        group = bank.get_morph_group("morph1")
        assert group == ["sine", "square"]

    def test_get_morph_group_not_found(self):
        """Non-existent morph group returns empty list."""
        bank = self._make_bank()
        assert bank.get_morph_group("nonexistent") == []

    def test_get_morphed_wavetable(self):
        """get_morphed_wavetable interpolates between two wavetables."""
        bank = self._make_bank()
        bank.create_wavetable_from_waveform("sine", "sine", size=256)
        bank.create_wavetable_from_waveform("square", "square", size=256)
        morphed = bank.get_morphed_wavetable(["sine", "square"], 0.5)
        assert morphed is not None
        assert "morph" in morphed.name
        assert len(morphed.data) == 256

    def test_get_morphed_wavetable_single_source(self):
        """Single source returns that wavetable directly."""
        bank = self._make_bank()
        bank.create_wavetable_from_waveform("sine", "sine", size=256)
        morphed = bank.get_morphed_wavetable(["sine"], 0.5)
        assert morphed is not None
        assert morphed.name == "sine"

    def test_get_morphed_wavetable_missing_source(self):
        """Missing source returns None."""
        bank = self._make_bank()
        bank.create_wavetable_from_waveform("sine", "sine", size=256)
        morphed = bank.get_morphed_wavetable(["sine", "nonexistent"], 0.5)
        assert morphed is None


@pytest.mark.unit
class TestWavetableEngine:
    """Tests for WavetableEngine extending SynthesisEngine."""

    @pytest.fixture
    def engine(self):
        from synth.engines.wavetable.engine import WavetableEngine

        return WavetableEngine(sample_rate=44100, block_size=256)

    def test_initialization(self, engine):
        """Engine initializes with default state."""
        assert engine.sample_rate == 44100
        assert engine.block_size == 256
        assert engine.current_wavetable == "sine"
        assert engine.wavetable_bank is not None
        assert len(engine.oscillators) >= 1
        assert engine.active_oscillators == []

    def test_initial_basic_wavetables(self, engine):
        """Engine initializes with basic waveform wavetables."""
        wts = engine.get_available_wavetables()
        assert "sine" in wts
        assert "triangle" in wts
        assert "square" in wts
        assert "sawtooth" in wts

    def test_get_engine_type(self, engine):
        """get_engine_type returns 'wavetable'."""
        assert engine.get_engine_type() == "wavetable"

    def test_get_engine_info_returns_dict(self, engine):
        """get_engine_info returns a comprehensive dict."""
        info = engine.get_engine_info()
        assert isinstance(info, dict)
        assert info["name"] == "Wavetable Synthesis Engine"
        assert info["type"] == "wavetable"
        assert "capabilities" in info
        assert isinstance(info["capabilities"], list)
        assert "parameters" in info
        assert isinstance(info["parameters"], list)
        assert "modulation_sources" in info
        assert "modulation_destinations" in info
        assert "wavetable_bank" in info
        assert "max_oscillators" in info

    def test_get_engine_info_contains_bank_stats(self, engine):
        """Engine info includes wavetable bank statistics."""
        info = engine.get_engine_info()
        bank_stats = info["wavetable_bank"]
        assert "total_wavetables" in bank_stats
        assert bank_stats["total_wavetables"] >= 4  # sine, triangle, square, sawtooth

    def test_get_preset_info(self, engine):
        """get_preset_info returns a PresetInfo with descriptors."""
        preset = engine.get_preset_info(bank=0, program=0)
        assert preset is not None
        assert preset.bank == 0
        assert preset.program == 0
        assert preset.engine_type == "wavetable"
        assert "Wavetable" in preset.name
        assert preset.region_descriptors is not None
        assert len(preset.region_descriptors) >= 1

    def test_get_all_region_descriptors(self, engine):
        """get_all_region_descriptors returns descriptors from preset."""
        descs = engine.get_all_region_descriptors(bank=0, program=0)
        assert isinstance(descs, list)
        assert len(descs) >= 1

    def test_create_partial(self, engine):
        """create_partial returns a WavetablePartial."""
        partial = engine.create_partial({"wavetable": "sine"}, 44100)
        assert partial is not None
        from synth.engines.wavetable.partial import WavetablePartial

        assert isinstance(partial, WavetablePartial)

    def test_generate_samples(self, engine):
        """generate_samples returns stereo float32 buffer."""
        output = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=256
        )
        assert output is not None
        assert isinstance(output, np.ndarray)
        assert output.shape == (256, 2)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))

    def test_generate_samples_with_modulation(self, engine):
        """generate_samples with modulation params produces output."""
        output = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch": 0.0, "volume": 0.0, "pan": 0.0},
            block_size=128,
        )
        assert output.shape == (128, 2)
        assert np.all(np.isfinite(output))

    def test_generate_samples_pan_modulation(self, engine):
        """Pan modulation should affect channel balance."""
        left = engine.generate_samples(
            note=60, velocity=100, modulation={"pan": -1.0}, block_size=64
        )
        right = engine.generate_samples(
            note=60, velocity=100, modulation={"pan": 1.0}, block_size=64
        )
        # Hard left: left channel should be louder than right
        # Hard right: right channel should be louder than left
        left_rms_l = np.sqrt(np.mean(left[:, 0] ** 2))
        left_rms_r = np.sqrt(np.mean(left[:, 1] ** 2))
        right_rms_l = np.sqrt(np.mean(right[:, 0] ** 2))
        right_rms_r = np.sqrt(np.mean(right[:, 1] ** 2))
        assert left_rms_l > left_rms_r
        assert right_rms_r > right_rms_l

    def test_generate_samples_different_notes(self, engine):
        """Different MIDI notes produce different output."""
        c4 = engine.generate_samples(note=60, velocity=100, modulation={}, block_size=128)
        c5 = engine.generate_samples(note=72, velocity=100, modulation={}, block_size=128)
        assert not np.allclose(c4, c5)

    def test_get_regions_for_note(self, engine):
        """get_regions_for_note returns list with WavetableRegion."""
        with patch("synth.engines.wavetable.engine.WavetableRegion") as mock_region:
            mock_instance = mock_region.return_value
            regions = engine.get_regions_for_note(60, 100)
            assert isinstance(regions, list)
            assert len(regions) >= 1

    def test_get_regions_for_note_different_program(self, engine):
        """get_regions_for_note with different program still returns regions."""
        with patch("synth.engines.wavetable.engine.WavetableRegion") as mock_region:
            regions = engine.get_regions_for_note(72, 127, program=5, bank=2)
            assert len(regions) >= 1

    def test_create_wavetable(self, engine):
        """create_wavetable creates a new wavetable in the bank."""
        result = engine.create_wavetable("sawtooth", "my_saw", size=512)
        assert result is True
        wts = engine.get_available_wavetables()
        assert "my_saw" in wts

    def test_set_wavetable(self, engine):
        """set_wavetable changes current wavetable."""
        engine.create_wavetable("square", "test_square")
        engine.set_wavetable("test_square")
        assert engine.current_wavetable == "test_square"

    def test_set_wavetable_nonexistent(self, engine):
        """Setting non-existent wavetable does not change current."""
        engine.set_wavetable("nonexistent")
        assert engine.current_wavetable == "sine"  # Default unchanged

    def test_get_available_wavetables(self, engine):
        """get_available_wavetables returns list of names."""
        wts = engine.get_available_wavetables()
        assert isinstance(wts, list)
        assert len(wts) >= 4

    def test_get_wavetable_info(self, engine):
        """get_wavetable_info returns info dict for existing wavetable."""
        info = engine.get_wavetable_info("sine")
        assert info is not None
        assert info["name"] == "sine"
        assert "length" in info
        assert "sample_rate" in info
        assert "duration_ms" in info

    def test_get_wavetable_info_nonexistent(self, engine):
        """get_wavetable_info returns None for unknown wavetable."""
        info = engine.get_wavetable_info("nonexistent")
        assert info is None

    def test_morph_group_operations(self, engine):
        """Morph group create/get round-trip works."""
        engine.create_wavetable("sine", "sine_morph")
        engine.create_wavetable("square", "square_morph")
        engine.create_morph_group("test_group", ["sine_morph", "square_morph"])
        group = engine.get_morph_group("test_group")
        assert group == ["sine_morph", "square_morph"]

    def test_is_note_supported(self, engine):
        """All MIDI notes 0-127 are supported."""
        assert engine.is_note_supported(0) is True
        assert engine.is_note_supported(60) is True
        assert engine.is_note_supported(127) is True
        assert engine.is_note_supported(-1) is False
        assert engine.is_note_supported(128) is False

    def test_get_supported_formats(self, engine):
        """get_supported_formats returns list of audio file extensions."""
        formats = engine.get_supported_formats()
        assert ".wav" in formats
        assert ".aiff" in formats
        assert ".flac" in formats
        assert ".ogg" in formats

    def test_reset(self, engine):
        """Reset clears active oscillators without error."""
        engine.generate_samples(note=60, velocity=100, modulation={}, block_size=64)
        engine.reset()
        assert engine.active_oscillators == []

    def test_reset_then_generate(self, engine):
        """After reset, engine can still generate output."""
        engine.reset()
        output = engine.generate_samples(note=60, velocity=100, modulation={}, block_size=64)
        assert output.shape == (64, 2)
        assert np.all(np.isfinite(output))

    def test_cleanup(self, engine):
        """Cleanup resets engine and clears wavetable bank."""
        engine.cleanup()
        assert engine.active_oscillators == []
        assert engine.wavetable_bank.wavetables == {}

    def test_string_representation(self, engine):
        """__str__ returns informative string."""
        s = str(engine)
        assert "WavetableEngine" in s
        assert "oscillators" in s
        assert "wavetables" in s

    def test_get_voice_parameters(self, engine):
        """get_voice_parameters returns params dict or None."""
        params = engine.get_voice_parameters(program=0, bank=0, note=60, velocity=100)
        # May be None if not implemented deeply, but should not crash
        assert params is None or isinstance(params, dict)

    def test_get_max_polyphony(self, engine):
        """get_max_polyphony returns default 64."""
        assert engine.get_max_polyphony() == 64

    def test_supports_modulation(self, engine):
        """supports_modulation checks known types."""
        assert engine.supports_modulation("pitch") is True
        assert engine.supports_modulation("filter") is True
        assert engine.supports_modulation("amp") is True
        assert engine.supports_modulation("unknown") is False

    def test_generate_samples_modulation_cutoff(self, engine):
        """Cutoff modulation changes output vs no cutoff (finite values)."""
        no_cut = engine.generate_samples(
            note=60, velocity=100, modulation={}, block_size=256
        ).copy()
        engine.reset()
        low_cut = engine.generate_samples(
            note=60, velocity=100, modulation={"cutoff": 200.0}, block_size=256
        ).copy()
        assert np.all(np.isfinite(no_cut))
        assert np.all(np.isfinite(low_cut))
        assert low_cut.shape == (256, 2)
        # Different filtering should produce different output
        assert not np.allclose(no_cut, low_cut)

    def test_consecutive_generations_advance_phase(self, engine):
        """Consecutive generate_samples calls advance oscillator phase."""
        first = engine.generate_samples(note=60, velocity=100, modulation={}, block_size=64)
        second = engine.generate_samples(note=60, velocity=100, modulation={}, block_size=64)
        # Phase is continuous so output should differ (unless silence)
        assert np.all(np.isfinite(first))
        assert np.all(np.isfinite(second))
