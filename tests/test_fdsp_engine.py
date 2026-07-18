"""Tests for FDSP (Formant) synthesis engine."""
from __future__ import annotations

import numpy as np
import pytest


class TestFormantFilter:
    """Test the anti-resonant formant biquad filter."""

    def test_init_defaults(self):
        from synth.engines.fdsp.engine import FormantFilter

        filt = FormantFilter(sample_rate=44100)
        assert filt.sample_rate == 44100
        assert filt.frequency == 1000.0
        assert filt.bandwidth == 100.0
        assert filt.gain == 1.0

    def test_set_parameters_clamps(self):
        from synth.engines.fdsp.engine import FormantFilter

        filt = FormantFilter(sample_rate=44100)
        filt.set_parameters(frequency=6000, bandwidth=500, gain=20.0)
        # Should be clamped
        assert filt.frequency <= 8000.0
        assert filt.bandwidth <= 2000.0
        assert filt.gain <= 10.0

    def test_set_parameters_minimum(self):
        from synth.engines.fdsp.engine import FormantFilter

        filt = FormantFilter(sample_rate=44100)
        filt.set_parameters(frequency=10, bandwidth=1, gain=0.01)
        # Should be clamped up
        assert filt.frequency >= 50.0
        assert filt.bandwidth >= 10.0
        assert filt.gain >= 0.1

    def test_process_sample_returns_finite(self):
        from synth.engines.fdsp.engine import FormantFilter

        filt = FormantFilter(sample_rate=44100)
        for _ in range(10):
            out = filt.process_sample(0.5)
            assert np.isfinite(out)

    def test_reset_clears_state(self):
        from synth.engines.fdsp.engine import FormantFilter

        filt = FormantFilter(sample_rate=44100)
        filt.process_sample(0.5)
        filt.process_sample(0.5)
        filt.reset()
        assert filt.x1 == 0.0
        assert filt.x2 == 0.0
        assert filt.y1 == 0.0
        assert filt.y2 == 0.0


class TestFormantFilterBank:
    """Test the parallel formant filter bank."""

    def test_init_defaults(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        assert bank.sample_rate == 44100
        assert bank.num_formants == 5
        assert len(bank.filters) == 5
        assert bank.master_gain == 1.0

    def test_init_custom_formants(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100, num_formants=3)
        assert bank.num_formants == 3
        assert len(bank.filters) == 3

    def test_set_formant(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.set_formant(0, 800.0, 60.0, 0.9)
        assert bank.filters[0].frequency == 800.0
        assert bank.filters[0].bandwidth == 60.0

    def test_set_formant_out_of_range(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        # Should not raise
        bank.set_formant(99, 800.0, 60.0, 0.9)

    def test_set_formant_frequencies(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.set_formant_frequencies([500, 1500, 2500, 3500, 4500])
        for i, freq in enumerate([500, 1500, 2500, 3500, 4500]):
            assert bank.filters[i].frequency == pytest.approx(freq)

    def test_set_formant_bandwidths(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.set_formant_bandwidths([50, 100, 150, 200, 250])
        for i, bw in enumerate([50, 100, 150, 200, 250]):
            assert bank.filters[i].bandwidth == pytest.approx(bw)

    def test_set_formant_gains(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.set_formant_gains([0.5, 0.8, 1.0, 0.7, 0.3])
        assert list(bank.formant_gains) == pytest.approx([0.5, 0.8, 1.0, 0.7, 0.3])

    def test_set_tilt(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.set_tilt(-3.0)
        assert bank.tilt == -3.0

    def test_process_sample_returns_finite(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        for _ in range(10):
            out = bank.process_sample(0.5)
            assert np.isfinite(out)

    def test_reset(self):
        from synth.engines.fdsp.engine import FormantFilterBank

        bank = FormantFilterBank(sample_rate=44100)
        bank.process_sample(0.5)
        bank.reset()
        for f in bank.filters:
            assert f.x1 == 0.0
            assert f.y1 == 0.0


class TestPhonemeData:
    """Test phoneme data structure."""

    def test_init(self):
        from synth.engines.fdsp.engine import PhonemeData

        phoneme = PhonemeData(
            "ah",
            formant_frequencies=[800, 1200, 2500, 3500, 4500],
            formant_bandwidths=[60, 80, 120, 150, 200],
        )
        assert phoneme.name == "ah"
        assert len(phoneme.formant_frequencies) == 5
        assert len(phoneme.formant_bandwidths) == 5

    def test_pads_to_five_formants(self):
        from synth.engines.fdsp.engine import PhonemeData

        phoneme = PhonemeData(
            "short",
            formant_frequencies=[800, 1200],
            formant_bandwidths=[60, 80],
        )
        assert len(phoneme.formant_frequencies) == 5
        assert len(phoneme.formant_bandwidths) == 5
        assert phoneme.formant_frequencies[2] == 3000.0  # padded value

    def test_custom_duration(self):
        from synth.engines.fdsp.engine import PhonemeData

        phoneme = PhonemeData(
            "long",
            formant_frequencies=[800, 1200, 2500, 3500, 4500],
            formant_bandwidths=[60, 80, 120, 150, 200],
            duration_ms=500.0,
        )
        assert phoneme.duration_ms == 500.0


class TestVocalDatabase:
    """Test the phoneme database."""

    def test_init_has_phonemes(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        assert len(db.phonemes) > 0

    def test_get_phoneme_exists(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        phoneme = db.get_phoneme("ɑ")
        assert phoneme is not None
        assert phoneme.name == "ɑ"
        assert len(phoneme.formant_frequencies) == 5

    def test_get_phoneme_missing(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        phoneme = db.get_phoneme("nonexistent")
        assert phoneme is None

    def test_get_phoneme_names(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        names = db.get_phoneme_names()
        assert "ɑ" in names
        assert "i" in names
        assert "ə" in names

    def test_interpolate_phonemes(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        p1 = db.get_phoneme("i")
        p2 = db.get_phoneme("ɑ")
        assert p1 is not None
        assert p2 is not None

        interp = db.interpolate_phonemes(p1, p2, 0.5)
        assert interp is not None
        assert "i" in interp.name and "ɑ" in interp.name
        assert len(interp.formant_frequencies) == 5

    def test_interpolate_clamps_factor(self):
        from synth.engines.fdsp.engine import VocalDatabase

        db = VocalDatabase()
        p1 = db.get_phoneme("i")
        p2 = db.get_phoneme("ɑ")
        assert p1 is not None
        assert p2 is not None

        interp = db.interpolate_phonemes(p1, p2, 2.0)
        # Should be clamped to 1.0
        assert list(interp.formant_frequencies) == list(p2.formant_frequencies)


class TestFormantAnalyzer:
    """Test formant analysis."""

    def test_init_defaults(self):
        from synth.engines.fdsp.engine import FormantAnalyzer

        analyzer = FormantAnalyzer(sample_rate=44100)
        assert analyzer.sample_rate == 44100
        assert analyzer.frame_size == 1024

    def test_analyze_frame_returns_formants(self):
        from synth.engines.fdsp.engine import FormantAnalyzer

        analyzer = FormantAnalyzer(sample_rate=44100)
        frame = np.sin(2 * np.pi * 440 * np.arange(1024) / 44100, dtype=np.float32)
        formants = analyzer.analyze_frame(frame)
        assert len(formants) == 5
        for freq, bw, gain in formants:
            assert freq > 0
            assert bw > 0
            assert 0.0 <= gain <= 1.0

    def test_analyze_silence_returns_defaults(self):
        from synth.engines.fdsp.engine import FormantAnalyzer

        analyzer = FormantAnalyzer(sample_rate=44100)
        frame = np.zeros(1024, dtype=np.float32)
        formants = analyzer.analyze_frame(frame)
        assert len(formants) == 5


class TestFDSPEngine:
    """Test the core FDSP engine."""

    def test_init(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        assert eng.sample_rate == 44100
        assert eng.pitch == 220.0
        assert eng.formant_shift == 1.0
        assert eng.excitation_type == "pulse"

    def test_set_phoneme(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_phoneme("ɑ")
        assert eng.current_phoneme is not None

    def test_set_phoneme_missing(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_phoneme("nonexistent")
        # Should not crash, current_phoneme remains None

    def test_process_sample_with_phoneme(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_phoneme("ɑ")
        eng.set_pitch(440.0)
        for _ in range(20):
            out = eng.process_sample(0.5)
            assert np.isfinite(out)

    def test_set_pitch_clamps(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_pitch(10000.0)
        assert eng.pitch == 1000.0  # clamped
        eng.set_pitch(10.0)
        assert eng.pitch == 50.0  # clamped

    def test_set_formant_shift(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_formant_shift(1.5)
        assert eng.formant_shift == 1.5

    def test_set_formant_shift_clamps(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_formant_shift(3.0)
        assert eng.formant_shift == 2.0

    def test_set_vibrato(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_vibrato(rate_hz=5.0, depth_semitones=0.02)
        assert eng.vibrato_rate == 5.0
        assert eng.vibrato_depth == 0.02

    def test_set_vibrato_clamps(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_vibrato(rate_hz=100.0, depth_semitones=10.0)
        assert eng.vibrato_rate == 20.0
        assert eng.vibrato_depth == 2.0

    def test_set_breath_level(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_breath_level(0.3)
        assert eng.breath_level == 0.3

    def test_set_breath_level_clamps(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_breath_level(5.0)
        assert eng.breath_level == 1.0

    def test_set_tilt(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_tilt(-6.0)
        assert eng.tilt == -6.0

    def test_set_excitation_type(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_excitation_type("noise")
        assert eng.excitation_type == "noise"
        eng.set_excitation_type("invalid")
        assert eng.excitation_type == "noise"  # unchanged

    def test_analyze_audio(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        frame = np.sin(2 * np.pi * 440 * np.arange(1024) / 44100, dtype=np.float32)
        formants = eng.analyze_audio(frame)
        assert len(formants) == 5

    def test_get_engine_info(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        info = eng.get_engine_info()
        assert isinstance(info, dict)
        assert info["sample_rate"] == 44100
        assert info["excitation_type"] == "pulse"
        assert "available_phonemes" in info

    def test_reset(self):
        from synth.engines.fdsp.engine import FDSPEngine

        eng = FDSPEngine(sample_rate=44100)
        eng.set_phoneme("ɑ")
        eng.process_sample(0.5)
        eng.reset()
        assert eng.current_phoneme is None
        assert eng.samples_processed == 0


class TestFDSPSynthesisEngine:
    """Test the SynthesisEngine interface wrapper."""

    @pytest.fixture
    def engine(self):
        from synth.engines.fdsp.engine import FDSPSynthesisEngine

        return FDSPSynthesisEngine(sample_rate=44100)

    def test_initialization(self, engine):
        assert engine.sample_rate == 44100
        assert engine.fdsp_engine is not None
        assert engine.block_size == 1024

    def test_get_engine_info(self, engine):
        info = engine.get_engine_info()
        assert isinstance(info, dict)
        assert info["name"] == "FDSP Formant Synthesis"
        assert info["type"] == "fdsp"

    def test_get_preset_info(self, engine):
        from synth.engines.preset_info import PresetInfo

        info = engine.get_preset_info(bank=0, program=0)
        assert info is not None
        assert isinstance(info, PresetInfo)
        assert info.bank == 0
        assert info.program == 0

    def test_get_all_region_descriptors(self, engine):
        descriptors = engine.get_all_region_descriptors(bank=0, program=0)
        assert isinstance(descriptors, list)
        assert len(descriptors) > 0

    def test_get_parameter_info(self, engine):
        info = engine.get_parameter_info("pitch")
        assert info is not None
        assert info["type"] == "float"
        assert info["default"] == 220.0

    def test_get_parameter_info_missing(self, engine):
        info = engine.get_parameter_info("nonexistent")
        assert info is None

    def test_create_partial(self, engine):
        partial = engine.create_partial(
            partial_params={"note": 60, "velocity": 100},
            sample_rate=44100,
        )
        from synth.engines.fdsp.engine import FDSPSynthesisPartial

        assert isinstance(partial, FDSPSynthesisPartial)
        assert partial.note == 60
        assert partial.velocity == 100

    def test_create_partial_with_phoneme(self, engine):
        partial = engine.create_partial(
            partial_params={"note": 72, "velocity": 80, "phoneme": "ɑ"},
            sample_rate=44100,
        )
        assert partial.phoneme == "ɑ"

    def test_generate_samples_output(self, engine):
        output = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch_bend": 0.0},
            block_size=256,
        )
        assert output is not None
        assert isinstance(output, np.ndarray)
        assert output.shape == (256, 2)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))

    def test_generate_samples_different_note(self, engine):
        # Higher note = higher frequency = more cycles in block
        output = engine.generate_samples(
            note=84,
            velocity=80,
            modulation={},
            block_size=128,
        )
        assert output.shape == (128, 2)
        assert np.all(np.isfinite(output))

    def test_is_note_supported(self, engine):
        assert engine.is_note_supported(60) is True
        assert engine.is_note_supported(-1) is False
        assert engine.is_note_supported(128) is False

    def test_get_engine_type(self, engine):
        assert engine.get_engine_type() == "fdsp"

    def test_get_max_polyphony(self, engine):
        assert engine.get_max_polyphony() == 32

    def test_supports_modulation(self, engine):
        assert engine.supports_modulation("pitch") is True
        assert engine.supports_modulation("formant_shift") is True
        assert engine.supports_modulation("vibrato") is True
        assert engine.supports_modulation("breath") is True
        assert engine.supports_modulation("cutoff") is False

    def test_validate_parameters(self, engine):
        validated = engine.validate_parameters(
            {"pitch": 500.0, "formant_shift": 3.0, "unknown_param": 42}
        )
        assert validated["pitch"] == 500.0
        assert validated["formant_shift"] == 2.0  # clamped
        assert validated["unknown_param"] == 42

    def test_reset(self, engine):
        engine.generate_samples(note=60, velocity=100, modulation={}, block_size=64)
        engine.reset()
        assert len(engine.active_voices) == 0
        assert engine.next_voice_id == 1

    def test_get_memory_usage(self, engine):
        usage = engine.get_memory_usage()
        assert isinstance(usage, dict)
        assert "samples_loaded" in usage
        assert "memory_used_mb" in usage

    def test_load_sample_for_region(self, engine):
        # FDSP is generative - no sample loading
        assert engine.load_sample_for_region(None) is True


class TestFDSPSynthesisPartial:
    """Test the FDSP synthesis partial (single voice)."""

    @pytest.fixture
    def partial(self):
        from synth.engines.fdsp.engine import FDSPSynthesisPartial

        return FDSPSynthesisPartial(note=60, velocity=100, sample_rate=44100)

    def test_init(self, partial):
        assert partial.note == 60
        assert partial.velocity == 100
        assert partial.sample_rate == 44100
        assert partial.phoneme == "ə"
        assert partial.is_active is True
        assert partial.age == 0

    def test_frequency_from_midi(self, partial):
        # MIDI note 69 = 440 Hz, note 60 = ~261.63 Hz
        expected = 440.0 * (2.0 ** ((60 - 69) / 12.0))
        assert partial.frequency == pytest.approx(expected, rel=1e-3)

    def test_set_phoneme(self, partial):
        partial.set_phoneme("ɑ")
        assert partial.phoneme == "ɑ"

    def test_set_formant_shift(self, partial):
        partial.set_formant_shift(1.5)
        assert partial.formant_shift == 1.5

    def test_set_formant_shift_clamps(self, partial):
        partial.set_formant_shift(3.0)
        assert partial.formant_shift == 2.0

    def test_release(self, partial):
        assert partial.is_active is True
        partial.release()
        assert partial.is_active is False

    def test_is_finished(self, partial):
        assert partial.is_finished() is False
        partial.release()
        assert partial.is_finished() is True

    def test_apply_modulation(self, partial):
        partial.apply_modulation(
            {"pitch_bend": 2.0, "formant_shift": 0.3, "vibrato_rate": 6.0, "vibrato_depth": 0.5}
        )
        # Should not crash; pitch and formant shift should be updated

    def test_apply_modulation_empty(self, partial):
        # Should not crash with empty modulation dict
        partial.apply_modulation({})
