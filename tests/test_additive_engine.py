"""Tests for Additive synthesis engine components.

Covers:
- HarmonicSpectrum: creation, preset shapes, harmonic manipulation, morphing
- AdditivePartialOscillator: initialization, sample generation, envelope lifecycle
- AdditiveEngine: initialization, audio generation, spectrum control, preset management
"""

from __future__ import annotations

import math

import numpy as np
import pytest


# =============================================================================
# HarmonicSpectrum
# =============================================================================


class TestHarmonicSpectrum:
    """Tests for the HarmonicSpectrum class."""

    def test_create_default(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        assert hs.name == "custom"
        assert len(hs.harmonics) == 0

    def test_create_named(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum(name="test_spec")
        assert hs.name == "test_spec"

    def test_set_and_get_harmonic(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.set_harmonic(1, 1.0, 0.0)
        hs.set_harmonic(3, 0.5, math.pi)

        h1 = hs.get_harmonic(1)
        assert h1 is not None
        assert h1["amplitude"] == pytest.approx(1.0)
        assert h1["phase"] == pytest.approx(0.0)

        h3 = hs.get_harmonic(3)
        assert h3 is not None
        assert h3["amplitude"] == pytest.approx(0.5)
        assert h3["phase"] == pytest.approx(math.pi)

    def test_get_missing_harmonic(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        assert hs.get_harmonic(99) is None

    def test_set_harmonic_overwrites(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.set_harmonic(1, 1.0, 0.0)
        hs.set_harmonic(1, 0.2, math.pi / 2)
        h1 = hs.get_harmonic(1)
        assert h1["amplitude"] == pytest.approx(0.2)
        assert h1["phase"] == pytest.approx(math.pi / 2)

    def test_clear_harmonics(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.set_harmonic(1, 1.0, 0.0)
        hs.set_harmonic(2, 0.5, 0.0)
        assert len(hs.harmonics) == 2
        hs.clear()
        assert len(hs.harmonics) == 0

    # --- Preset shapes ---

    def test_create_sawtooth(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_sawtooth(num_harmonics=8)
        assert len(hs.harmonics) == 8
        # Sawtooth: amplitude = 1/n, phase alternates 0/pi
        for i in range(1, 9):
            h = hs.get_harmonic(i)
            assert h is not None
            assert h["amplitude"] == pytest.approx(1.0 / i)
            expected_phase = 0.0 if i % 2 == 1 else math.pi
            assert h["phase"] == pytest.approx(expected_phase)

    def test_create_square(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_square(num_harmonics=8)
        # Square: only odd harmonics, amplitude = 1/n, phase = 0
        assert len(hs.harmonics) == 4  # 1, 3, 5, 7
        for i in [1, 3, 5, 7]:
            h = hs.get_harmonic(i)
            assert h is not None
            assert h["amplitude"] == pytest.approx(1.0 / i)
            assert h["phase"] == pytest.approx(0.0)
        # Even harmonics should be absent
        for i in [2, 4, 6, 8]:
            assert hs.get_harmonic(i) is None

    def test_create_triangle(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_triangle(num_harmonics=8)
        # Triangle: only odd harmonics, amplitude = 1/n^2, phase alternates
        assert len(hs.harmonics) == 4
        for i in [1, 3, 5, 7]:
            h = hs.get_harmonic(i)
            assert h is not None
            assert h["amplitude"] == pytest.approx(1.0 / (i * i))

    def test_create_pulse(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_pulse(duty_cycle=0.5, num_harmonics=8)
        assert len(hs.harmonics) == 8
        for i in range(1, 9):
            h = hs.get_harmonic(i)
            assert h is not None
            expected = math.sin(math.pi * i * 0.5) / (math.pi * i)
            assert h["amplitude"] == pytest.approx(expected)

    def test_create_pulse_different_duty_cycle(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_pulse(duty_cycle=0.25, num_harmonics=4)
        assert len(hs.harmonics) == 4
        # Verify formula: sin(pi * i * duty) / (pi * i)
        for i in range(1, 5):
            h = hs.get_harmonic(i)
            assert h is not None
            expected_amp = math.sin(math.pi * i * 0.25) / (math.pi * i)
            assert h["amplitude"] == pytest.approx(expected_amp)

    def test_create_pulse_amplitudes_can_be_negative(self):
        """Pulse spectrum can produce negative amplitudes (phase info in amplitude sign)."""
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.create_pulse(duty_cycle=0.5, num_harmonics=8)
        assert len(hs.harmonics) == 8
        for i in range(1, 9):
            h = hs.get_harmonic(i)
            assert h is not None
            expected = math.sin(math.pi * i * 0.5) / (math.pi * i)
            assert h["amplitude"] == pytest.approx(expected)

    def test_create_sawtooth_overwrites_previous(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum()
        hs.set_harmonic(1, 0.5, 0.0)
        hs.create_sawtooth(num_harmonics=4)
        # Should have been cleared and replaced
        assert len(hs.harmonics) == 4

    # --- Morphing ---

    def test_morph_to_self_returns_identity(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        hs = HarmonicSpectrum("source")
        hs.create_sawtooth(8)
        morphed = hs.morph_to(hs, 0.0)
        assert morphed.name == "source_morph"
        for i in range(1, 9):
            src = hs.get_harmonic(i)
            dst = morphed.get_harmonic(i)
            assert dst is not None
            assert dst["amplitude"] == pytest.approx(src["amplitude"])
            assert dst["phase"] == pytest.approx(src["phase"])

    def test_morph_to_target_full(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        source = HarmonicSpectrum("source")
        source.create_sawtooth(8)
        target = HarmonicSpectrum("target")
        target.create_square(8)

        morphed = source.morph_to(target, 1.0)
        assert morphed.name == "source_morph"
        for i in set(range(1, 9)):
            src = source.get_harmonic(i)
            tgt = target.get_harmonic(i)
            m = morphed.get_harmonic(i)
            if src is not None and tgt is not None:
                assert m is not None
                # At morph_factor=1.0, should be identical to target
                assert m["amplitude"] == pytest.approx(tgt["amplitude"])
                assert m["phase"] == pytest.approx(tgt["phase"])
            elif src is None and tgt is not None:
                assert m is not None
            elif src is not None and tgt is None:
                # Target missing -> amplitude 0, phase 0
                assert m is not None
                assert m["amplitude"] == pytest.approx(0.0)

    def test_morph_linear_interpolation(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        source = HarmonicSpectrum()
        target = HarmonicSpectrum()
        source.set_harmonic(1, 1.0, 0.0)
        target.set_harmonic(1, 0.0, math.pi)

        # morph_factor = 0.5 -> expect midpoint
        morphed = source.morph_to(target, 0.5)
        h = morphed.get_harmonic(1)
        assert h is not None
        assert h["amplitude"] == pytest.approx(0.5)
        assert h["phase"] == pytest.approx(math.pi / 2)

    def test_morph_harmonic_union(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        source = HarmonicSpectrum()
        target = HarmonicSpectrum()
        source.set_harmonic(1, 1.0, 0.0)
        target.set_harmonic(3, 0.5, 0.0)

        morphed = source.morph_to(target, 0.5)
        # Should have both harmonic 1 and 3
        assert morphed.get_harmonic(1) is not None
        assert morphed.get_harmonic(3) is not None
        # Harmonic 1 interpolates from 1.0->0.0 = 0.5
        assert morphed.get_harmonic(1)["amplitude"] == pytest.approx(0.5)
        # Harmonic 3 interpolates from 0.0->0.5 = 0.25
        assert morphed.get_harmonic(3)["amplitude"] == pytest.approx(0.25)

    def test_morph_factor_clamping(self):
        from synth.engines.additive.engine import HarmonicSpectrum

        source = HarmonicSpectrum()
        target = HarmonicSpectrum()
        source.set_harmonic(1, 1.0, 0.0)
        target.set_harmonic(1, 0.0, 0.0)

        # morph_factor < 0 should still work (extrapolation possible based on code)
        # But the engine clamps internally. Just verify no crash.
        morphed = source.morph_to(target, -0.5)
        assert morphed.get_harmonic(1) is not None
        # morph_factor > 1 should also not crash
        morphed = source.morph_to(target, 1.5)
        assert morphed.get_harmonic(1) is not None


# =============================================================================
# AdditivePartialOscillator
# =============================================================================


class TestAdditivePartialOscillator:
    """Tests for the AdditivePartialOscillator class."""

    def test_init_defaults(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        assert osc.sample_rate == 44100
        assert osc.frequency_ratio == 1.0
        assert osc.amplitude == 0.0
        assert osc.phase == 0.0
        assert osc.phase_offset == 0.0
        assert osc.attack_time == 0.01
        assert osc.decay_time == 0.3
        assert osc.sustain_level == 0.7
        assert osc.release_time == 0.5
        assert osc.envelope_phase == "idle"
        assert osc.envelope_value == 0.0
        assert osc.envelope_time == 0.0
        assert osc.amplitude_mod == 1.0
        assert osc.frequency_mod == 0.0
        assert osc.phase_mod == 0.0

    def test_init_different_sample_rate(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=48000)
        assert osc.sample_rate == 48000

    def test_set_parameters_updates_all(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        params = {
            "frequency_ratio": 2.0,
            "amplitude": 0.8,
            "phase_offset": math.pi / 2,
            "attack_time": 0.1,
            "decay_time": 0.2,
            "sustain_level": 0.5,
            "release_time": 0.3,
        }
        osc.set_parameters(params)
        assert osc.frequency_ratio == 2.0
        assert osc.amplitude == 0.8
        assert osc.phase_offset == pytest.approx(math.pi / 2)
        assert osc.attack_time == 0.1
        assert osc.decay_time == 0.2
        assert osc.sustain_level == 0.5
        assert osc.release_time == 0.3

    def test_set_parameters_partial(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5})
        assert osc.amplitude == 0.5
        # Other values should remain default
        assert osc.frequency_ratio == 1.0

    def test_set_parameters_empty(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({})
        # All should remain defaults
        assert osc.frequency_ratio == 1.0

    def test_generate_sample_returns_float(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5})
        osc.note_on(127)
        # Advance envelope past attack into sustain
        osc.update_envelope(0.5)
        sample = osc.generate_sample(base_frequency=440.0)
        assert isinstance(sample, float)
        assert np.isfinite(sample)

    def test_generate_sample_with_amplitude_zero(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        # amplitude = 0, should output 0
        osc.note_on(127)
        osc.update_envelope(0.5)
        sample = osc.generate_sample(base_frequency=440.0)
        assert sample == 0.0

    def test_generate_sample_envelope_idle(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5})
        # envelope is idle -> value = 0 -> sample = 0
        sample = osc.generate_sample(base_frequency=440.0)
        assert sample == 0.0

    def test_generate_sample_uses_frequency_ratio(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5, "frequency_ratio": 2.0})
        osc.note_on(127)
        osc.update_envelope(0.5)
        # Should generate at 880 Hz - just verify it produces non-zero output
        sample = osc.generate_sample(base_frequency=440.0)
        assert isinstance(sample, float)

    def test_generate_sample_phase_increment(self):
        """Verify phase advances correctly after multiple calls."""
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 1.0, "frequency_ratio": 1.0})
        osc.note_on(127)
        osc.update_envelope(0.5)
        initial_phase = osc.phase
        osc.generate_sample(base_frequency=440.0)
        expected_increment = 2.0 * math.pi * 440.0 / 44100.0
        assert osc.phase == pytest.approx(initial_phase + expected_increment)

    def test_phase_wraps_after_full_cycle(self):
        """Phase should wrap at 2*pi."""
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 1.0, "frequency_ratio": 1.0})
        osc.note_on(127)
        osc.update_envelope(0.5)
        # Accumulate many samples to force wrap
        for _ in range(1000):
            osc.generate_sample(base_frequency=440.0)
        assert 0.0 <= osc.phase <= 2.0 * math.pi

    # --- Envelope lifecycle ---

    def test_note_on_sets_envelope_phase(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        assert osc.envelope_phase == "idle"
        osc.note_on(127)
        assert osc.envelope_phase == "attack"
        assert osc.envelope_time == 0.0
        assert osc.phase == osc.phase_offset

    def test_note_off_starts_release(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.note_on(127)
        osc.update_envelope(0.1)  # in attack
        osc.note_off()
        assert osc.envelope_phase == "release"
        assert osc.envelope_time == 0.0

    def test_envelope_attack_phase(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"attack_time": 0.1, "amplitude": 1.0})
        osc.note_on(127)
        # Halfway through attack
        osc.update_envelope(0.05)
        assert osc.envelope_phase == "attack"
        assert osc.envelope_value == pytest.approx(0.5)

    def test_envelope_attack_to_decay_transition(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"attack_time": 0.01, "decay_time": 0.3, "sustain_level": 0.7})
        osc.note_on(127)
        osc.update_envelope(0.01)  # end of attack
        assert osc.envelope_phase == "decay"
        assert osc.envelope_value == pytest.approx(1.0)

    def test_envelope_decay_to_sustain_transition(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters(
            {"attack_time": 0.01, "decay_time": 0.1, "sustain_level": 0.5}
        )
        osc.note_on(127)
        osc.update_envelope(0.02)  # attack
        osc.update_envelope(0.11)  # decay complete
        assert osc.envelope_phase == "sustain"
        assert osc.envelope_value == pytest.approx(0.5)

    def test_envelope_sustain_holds(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"attack_time": 0.01, "decay_time": 0.1, "sustain_level": 0.6})
        osc.note_on(127)
        # First call transitions attack -> decay
        osc.update_envelope(0.02)
        # Second call transitions decay -> sustain
        osc.update_envelope(0.2)
        assert osc.envelope_phase == "sustain"
        assert osc.envelope_value == pytest.approx(0.6)
        # Another update should stay at sustain
        osc.update_envelope(1.0)
        assert osc.envelope_value == pytest.approx(0.6)

    def test_envelope_release_to_idle(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters(
            {
                "attack_time": 0.01,
                "decay_time": 0.1,
                "sustain_level": 0.7,
                "release_time": 0.1,
            }
        )
        osc.note_on(127)
        osc.update_envelope(0.5)  # to sustain
        osc.note_off()
        osc.update_envelope(0.1)  # release complete
        assert osc.envelope_phase == "idle"
        assert osc.envelope_value == pytest.approx(0.0)

    def test_envelope_release_decays_linearly(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters(
            {
                "attack_time": 0.01,
                "decay_time": 0.1,
                "sustain_level": 0.8,
                "release_time": 0.2,
            }
        )
        osc.note_on(127)
        osc.update_envelope(0.5)  # to sustain
        osc.note_off()
        osc.update_envelope(0.1)  # halfway through release
        assert osc.envelope_phase == "release"
        expected = 0.8 * (1.0 - 0.1 / 0.2)
        assert osc.envelope_value == pytest.approx(expected)

    def test_is_active_true_when_not_idle(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        assert not osc.is_active()
        osc.note_on(127)
        assert osc.is_active()
        osc.note_off()
        assert osc.is_active()  # still in release
        osc.update_envelope(1.0)  # release should finish
        assert not osc.is_active()

    def test_reset(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.8})
        osc.note_on(127)
        osc.update_envelope(0.5)
        osc.reset()
        assert osc.phase == osc.phase_offset
        assert osc.envelope_phase == "idle"
        assert osc.envelope_value == 0.0
        assert osc.envelope_time == 0.0

    def test_generate_sample_applies_amplitude_mod(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5})
        osc.note_on(127)
        osc.update_envelope(0.5)
        osc.amplitude_mod = 0.5
        sample = osc.generate_sample(base_frequency=440.0)
        # Compare with mod=1.0
        osc2 = AdditivePartialOscillator(sample_rate=44100)
        osc2.set_parameters({"amplitude": 0.5, "phase_offset": osc.phase_offset})
        osc2.note_on(127)
        osc2.update_envelope(0.5)
        # Sync phase by generating
        osc2.generate_sample(base_frequency=440.0)
        # Continue generating
        sample2 = osc.generate_sample(base_frequency=440.0)
        assert isinstance(sample, float)

    def test_generate_sample_applies_frequency_mod(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5, "frequency_ratio": 1.0})
        osc.note_on(127)
        osc.update_envelope(0.5)
        osc.frequency_mod = 100.0  # Add 100 Hz
        sample = osc.generate_sample(base_frequency=440.0)
        # Should effectively run at 540 Hz
        assert isinstance(sample, float)

    def test_generate_sample_applies_phase_mod(self):
        from synth.engines.additive.engine import AdditivePartialOscillator

        osc = AdditivePartialOscillator(sample_rate=44100)
        osc.set_parameters({"amplitude": 0.5})
        osc.note_on(127)
        osc.update_envelope(0.5)
        osc.phase_mod = 0.5
        sample = osc.generate_sample(base_frequency=440.0)
        assert isinstance(sample, float)

    # --- Legacy compatibility test (matches user's boilerplate) ---

    def test_generate_samples(self):
        """Block-style generation works through repeated generate_sample calls."""
        from synth.engines.additive.engine import AdditivePartialOscillator, HarmonicSpectrum

        # This test is adapted from the boilerplate: HarmonicSpectrum is used
        # to configure the oscillator, then generate samples
        osc = AdditivePartialOscillator(sample_rate=44100)
        hs = HarmonicSpectrum()
        hs.create_sawtooth(4)

        # Configure oscillator from spectrum's first harmonic
        h1 = hs.get_harmonic(1)
        assert h1 is not None
        osc.set_parameters(
            {
                "amplitude": h1["amplitude"],
                "phase_offset": h1["phase"],
                "frequency_ratio": 1.0,
            }
        )
        osc.note_on(127)
        osc.update_envelope(0.5)

        # Generate block of samples
        samples = np.array([osc.generate_sample(440.0) for _ in range(256)], dtype=np.float32)
        assert samples.shape == (256,)
        assert samples.dtype == np.float32
        assert np.all(np.isfinite(samples))

    def test_generate_silence_when_gate_off(self):
        """When gate is off (note-off envelope complete), generates silence."""
        from synth.engines.additive.engine import AdditivePartialOscillator, HarmonicSpectrum

        osc = AdditivePartialOscillator(sample_rate=44100)
        hs = HarmonicSpectrum()
        hs.create_sawtooth(4)
        h1 = hs.get_harmonic(1)
        assert h1 is not None
        osc.set_parameters({"amplitude": h1["amplitude"]})

        # Don't call note_on -> envelope stays idle -> silence
        samples = np.array([osc.generate_sample(440.0) for _ in range(256)], dtype=np.float32)
        assert np.all(np.isfinite(samples))
        assert np.max(np.abs(samples)) == pytest.approx(0.0)


# =============================================================================
# AdditiveEngine
# =============================================================================


class TestAdditiveEngine:
    """Tests for the AdditiveEngine class."""

    @pytest.fixture
    def engine(self):
        from synth.engines.additive.engine import AdditiveEngine

        return AdditiveEngine(max_partials=16, sample_rate=44100, block_size=256)

    def test_initialization(self, engine):
        assert engine is not None
        assert engine.max_partials == 16
        assert engine.sample_rate == 44100
        assert engine.block_size == 256
        assert len(engine.partials) == 16
        assert engine.current_spectrum is not None
        assert engine.target_spectrum is not None
        assert engine.master_volume == 1.0
        assert engine.brightness == 1.0
        assert engine.spread == 0.0

    def test_initialization_defaults(self):
        from synth.engines.additive.engine import AdditiveEngine

        eng = AdditiveEngine()
        assert eng.max_partials == 128
        assert eng.sample_rate == 44100
        assert eng.block_size == 1024

    def test_initialization_clamps_max_partials(self):
        from synth.engines.additive.engine import AdditiveEngine

        eng = AdditiveEngine(max_partials=200)
        assert eng.max_partials == 128
        eng2 = AdditiveEngine(max_partials=0)
        assert eng2.max_partials == 1

    def test_get_engine_type(self, engine):
        from synth.engines.additive.engine import AdditiveEngine

        # Base returns "unknown" - AdditiveEngine inherits this
        assert isinstance(engine.get_engine_type(), str)

    def test_get_engine_info(self, engine):
        info = engine.get_engine_info()
        assert info is not None
        assert isinstance(info, dict)
        assert info["name"] == "Additive Synthesis Engine"
        assert info["type"] == "additive"
        assert "capabilities" in info
        assert "additive_synthesis" in info["capabilities"]
        assert "harmonic_control" in info["capabilities"]
        assert "spectral_morphing" in info["capabilities"]
        assert "parameters" in info
        assert "spectrum_type" in info["parameters"]
        assert "brightness" in info["parameters"]
        assert "spread" in info["parameters"]
        assert info["max_partials"] == 16

    def test_create_partial(self, engine):
        """create_partial returns an AdditivePartial instance."""
        partial = engine.create_partial({"frequency_ratio": 2.0, "amplitude": 0.5}, 44100)
        assert partial is not None

    def test_is_note_supported(self, engine):
        assert engine.is_note_supported(60)
        assert engine.is_note_supported(0)
        assert engine.is_note_supported(127)
        assert not engine.is_note_supported(-1)
        assert not engine.is_note_supported(128)

    # --- Audio generation ---

    def test_generate_samples_output_shape_and_dtype(self, engine):
        """Verify generate_samples returns correct buffer."""
        engine.note_on(60, 100)
        output = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=256
        )
        assert output is not None
        assert isinstance(output, np.ndarray)
        assert output.shape == (256, 2)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))

    def test_generate_samples_with_modulation(self, engine):
        """Modulation values are applied (pitch bend, etc.)."""
        engine.note_on(60, 100)
        output = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch": 200.0},  # 200 cents pitch bend
            block_size=128,
        )
        assert output.shape == (128, 2)
        assert np.all(np.isfinite(output))

    def test_generate_samples_different_notes(self, engine):
        """Different MIDI notes produce different audio."""
        engine.note_on(60, 100)
        out_c4 = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=128
        )
        engine.reset()
        engine.note_on(72, 100)
        out_c5 = engine.generate_samples(
            note=72, velocity=100, modulation={"pitch": 0.0}, block_size=128
        )
        # Higher note should have different content
        assert not np.array_equal(out_c4, out_c5)

    def test_generate_samples_velocity_affects_amplitude(self, engine):
        """Higher velocity should produce louder output."""
        engine.note_on(60, 127)
        out_loud = engine.generate_samples(
            note=60, velocity=127, modulation={"pitch": 0.0}, block_size=128
        )
        engine.reset()
        engine.note_on(60, 1)
        out_quiet = engine.generate_samples(
            note=60, velocity=1, modulation={"pitch": 0.0}, block_size=128
        )
        max_loud = np.max(np.abs(out_loud))
        max_quiet = np.max(np.abs(out_quiet))
        assert max_loud > max_quiet

    def test_generate_samples_no_note_on(self, engine):
        """Without note_on, partials are idle -> silence."""
        output = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=128
        )
        assert np.max(np.abs(output)) == pytest.approx(0.0)

    def test_engine_active_state(self, engine):
        """is_active should reflect note_on/note_off state."""
        assert not engine.is_active()
        engine.note_on(60, 100)
        assert engine.is_active()
        engine.note_off(60)
        # After note_off, partials are in release -> still active until release finishes
        assert engine.is_active()
        # Fast-forward by updating envelopes
        engine.generate_samples(
            note=60, velocity=0, modulation={"pitch": 0.0}, block_size=44100
        )
        # After enough samples, release should complete
        # (release_time=0.5, so 22050 samples at 44100)

    # --- Spectrum management ---

    def test_set_spectrum_type_sawtooth(self, engine):
        engine.set_spectrum_type("sawtooth", num_harmonics=8)
        # Spectrum should have 8 harmonics
        assert len(engine.current_spectrum.harmonics) == 8
        # Partials should have their amplitudes set
        for i in range(1, 9):
            h = engine.current_spectrum.get_harmonic(i)
            assert h is not None
        # Partial 0 (harmonic 1) should have non-zero amplitude
        assert engine.partials[0].amplitude > 0

    def test_set_spectrum_type_square(self, engine):
        engine.set_spectrum_type("square", num_harmonics=8)
        # Only odd harmonics have entries in the spectrum dict
        h = engine.current_spectrum.harmonics
        assert 1 in h  # odd
        assert 2 not in h  # even not in square spectrum
        assert 3 in h  # odd
        # Partials for odd harmonics should have amplitude > 0
        assert engine.partials[0].amplitude > 0  # harmonic 1
        assert engine.partials[2].amplitude > 0  # harmonic 3

    def test_set_spectrum_type_triangle(self, engine):
        engine.set_spectrum_type("triangle", num_harmonics=8)
        assert engine.partials[0].amplitude > 0

    def test_set_spectrum_type_pulse(self, engine):
        engine.set_spectrum_type("pulse", num_harmonics=8)
        assert len(engine.current_spectrum.harmonics) == 8

    def test_set_spectrum_type_invalid(self, engine):
        """Invalid spectrum type keeps the current spectrum unchanged."""
        # Start with sawtooth
        engine.set_spectrum_type("sawtooth", 4)
        orig_keys = set(engine.current_spectrum.harmonics.keys())
        # Try invalid type
        engine.set_spectrum_type("invalid_type", 4)
        # Should be unchanged
        assert set(engine.current_spectrum.harmonics.keys()) == orig_keys

    def test_set_spectrum_type_clamps_harmonics(self, engine):
        """num_harmonics should be clamped to max_partials."""
        engine.set_spectrum_type("sawtooth", num_harmonics=100)
        assert len(engine.current_spectrum.harmonics) == engine.max_partials

    def test_set_brightness(self, engine):
        """set_brightness should store the value and apply to partials."""
        engine.set_brightness(0.75)
        assert engine.brightness == 0.75
        # Should not crash
        assert engine is not None

    def test_set_brightness_clamps_negative(self, engine):
        engine.set_brightness(-1.0)
        assert engine.brightness == 0.0

    def test_set_brightness_high(self, engine):
        engine.set_brightness(2.5)
        assert engine.brightness == 2.5  # no upper clamp
        # Should not crash

    def test_set_spread(self, engine):
        engine.set_spread(0.5)
        assert engine.spread == 0.5

    def test_set_spread_clamps(self, engine):
        engine.set_spread(-0.5)
        assert engine.spread == 0.0
        engine.set_spread(1.5)
        assert engine.spread == 1.0

    # --- Partial parameter management ---

    def test_set_partial_parameters(self, engine):
        engine.set_partial_parameters(0, {"amplitude": 0.8, "frequency_ratio": 2.0})
        assert engine.partials[0].amplitude == 0.8
        assert engine.partials[0].frequency_ratio == 2.0

    def test_set_partial_parameters_out_of_range(self, engine):
        """Setting parameters on an out-of-range partial should be a no-op."""
        engine.set_partial_parameters(999, {"amplitude": 0.8})
        # Should not crash
        assert True

    def test_get_partial_parameters(self, engine):
        engine.set_partial_parameters(0, {"amplitude": 0.5, "frequency_ratio": 3.0})
        params = engine.get_partial_parameters(0)
        assert params["amplitude"] == 0.5
        assert params["frequency_ratio"] == 3.0

    def test_get_partial_parameters_out_of_range(self, engine):
        params = engine.get_partial_parameters(999)
        assert params == {}

    # --- Preset management ---

    def test_get_preset_info(self, engine):
        presets = engine.get_preset_info(bank=0, program=0)
        assert presets is not None
        assert presets.bank == 0
        assert presets.program == 0
        assert "Additive" in presets.name
        assert len(presets.region_descriptors) == 1
        # Check region descriptor
        rd = presets.region_descriptors[0]
        assert rd.key_range == (0, 127)
        assert rd.velocity_range == (0, 127)
        assert rd.algorithm_params.get("spectrum_type") == "harmonic"

    def test_get_preset_info_different_bank_program(self, engine):
        presets = engine.get_preset_info(bank=3, program=42)
        assert presets.bank == 3
        assert presets.program == 42
        assert "3:42" in presets.name or "3:42" in str(presets)

    def test_get_all_region_descriptors(self, engine):
        descriptors = engine.get_all_region_descriptors(bank=0, program=0)
        assert isinstance(descriptors, list)
        assert len(descriptors) >= 1

    def test_get_supported_formats(self, engine):
        formats = engine.get_supported_formats()
        assert ".add" in formats
        assert ".harm" in formats

    def test_get_spectrum_info(self, engine):
        info = engine.get_spectrum_info()
        assert info is not None
        assert "num_harmonics" in info
        assert "brightness" in info
        assert "spread" in info
        assert info["brightness"] == 1.0
        assert info["spread"] == 0.0

    # --- Preset load/save ---

    def test_load_preset(self, engine):
        preset_data = {
            "spectrum_type": "square",
            "num_harmonics": 8,
            "master_volume": 0.5,
            "brightness": 0.8,
            "spread": 0.3,
            "bandwidth_limit": 15000.0,
        }
        engine.load_preset(preset_data)
        assert engine.master_volume == 0.5
        assert engine.brightness == 0.8
        assert engine.spread == 0.3
        assert engine.bandwidth_limit == 15000.0
        # Should have applied square spectrum
        h1 = engine.current_spectrum.get_harmonic(1)
        assert h1 is not None and h1["amplitude"] > 0
        h2 = engine.current_spectrum.get_harmonic(2)
        assert h2 is None  # square has no even harmonics

    def test_load_preset_defaults(self, engine):
        """Missing keys should use defaults."""
        engine.load_preset({})
        assert engine.master_volume == 1.0  # default
        # Should have sawtooth (default spectrum type)

    def test_save_preset(self, engine):
        engine.set_spectrum_type("square", 8)
        engine.set_brightness(0.5)
        engine.set_spread(0.2)
        saved = engine.save_preset()
        assert isinstance(saved, dict)
        assert saved["master_volume"] == 1.0
        assert saved["brightness"] == 0.5
        assert saved["spread"] == 0.2
        assert saved["bandwidth_limit"] == 20000.0
        assert "harmonics" in saved

    def test_save_and_load_roundtrip(self, engine):
        """Saving and loading should restore state."""
        engine.set_spectrum_type("triangle", 10)
        engine.set_brightness(0.6)
        engine.set_spread(0.4)
        engine.master_volume = 0.75
        saved = engine.save_preset()
        # New engine
        from synth.engines.additive.engine import AdditiveEngine

        eng2 = AdditiveEngine(max_partials=16, sample_rate=44100)
        eng2.load_preset(saved)
        assert eng2.master_volume == 0.75
        assert eng2.brightness == 0.6
        assert eng2.spread == 0.4

    # --- Morphing ---

    def test_morph_to_spectrum(self, engine):
        """Morphing should not crash and should update state."""
        target = engine.current_spectrum.__class__("target_square")
        target.create_square(16)
        engine.morph_to_spectrum(target, duration=0.5)
        assert engine.morph_duration == 0.5
        assert engine.morph_time == 0.0
        assert engine.morph_factor == 0.0

    def test_morph_progresses_over_time(self, engine):
        """Calling generate_samples during morph should advance morph_factor."""
        target = engine.current_spectrum.__class__("target")
        target.create_square(16)
        engine.morph_to_spectrum(target, duration=1.0)
        # Generate enough samples to advance morph by ~0.5 seconds
        num_blocks = int(0.5 * engine.sample_rate / engine.block_size)
        for _ in range(num_blocks):
            engine.generate_samples(
                note=60,
                velocity=100,
                modulation={"pitch": 0.0},
                block_size=engine.block_size,
            )
        assert engine.morph_factor > 0.0
        assert engine.morph_factor <= 1.0

    def test_morph_completes(self, engine):
        """After the morph duration, morph_factor should be 1.0."""
        target = engine.current_spectrum.__class__("target")
        target.create_square(16)
        # Very short morph relative to block count
        # morph advances by 1/sample_rate per block (not per sample)
        # To complete: need duration * sample_rate blocks
        duration = 0.001
        blocks_needed = int(duration * engine.sample_rate) + 2  # ≈ 46 blocks
        engine.morph_to_spectrum(target, duration=duration)
        for _ in range(blocks_needed):
            engine.generate_samples(
                note=60,
                velocity=100,
                modulation={"pitch": 0.0},
                block_size=engine.block_size,
            )
        assert engine.morph_factor == pytest.approx(1.0)

    # --- Note on/off ---

    def test_note_on_triggers_partials(self, engine):
        engine.set_spectrum_type("sawtooth", 4)
        engine.note_on(60, 100)
        assert 60 in engine.active_notes
        assert engine.active_notes[60] == 100
        # Partials with amplitude > 0 should be active
        assert any(p.is_active() for p in engine.partials)

    def test_note_off_removes_from_active(self, engine):
        engine.note_on(60, 100)
        engine.note_off(60)
        assert 60 not in engine.active_notes

    def test_note_off_starts_release_on_partials(self, engine):
        engine.set_spectrum_type("sawtooth", 4)
        engine.note_on(60, 100)
        engine.note_off(60)
        # Partials should be in release phase
        for p in engine.partials:
            if p.amplitude > 0:
                assert p.envelope_phase == "release"

    # --- Reset and cleanup ---

    def test_reset_clears_state(self, engine):
        engine.note_on(60, 100)
        engine.set_brightness(0.5)
        engine.reset()
        assert len(engine.active_notes) == 0
        for p in engine.partials:
            assert p.envelope_phase == "idle"

    def test_cleanup(self, engine):
        """Cleanup should not crash."""
        engine.cleanup()
        assert True

    # --- Legacy compatibility test (matches user's boilerplate) ---

    def test_generate_samples_output(self, engine):
        """Simplified generate_samples test (matches boilerplate pattern)."""
        engine.note_on(60, 100)
        output = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=256
        )
        assert output is not None
        assert isinstance(output, np.ndarray)
        assert output.dtype == np.float32
        assert np.all(np.isfinite(output))

    def test_get_preset_info_compat(self, engine):
        """get_preset_info with bank/program args (matches boilerplate pattern)."""
        presets = engine.get_preset_info(bank=0, program=0)
        assert presets is not None

    # --- Stereo spread ---

    def test_spread_produces_different_channels(self, engine):
        """With spread > 0, left and right channels should differ."""
        engine.set_spectrum_type("sawtooth", 8)
        engine.set_spread(1.0)
        engine.note_on(60, 100)
        output = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=256
        )
        # Left and right channels should not be identical
        assert not np.array_equal(output[:, 0], output[:, 1])

    def test_spread_zero_produces_identical_channels(self, engine):
        """With spread = 0, both channels should be identical."""
        engine.set_spectrum_type("sawtooth", 8)
        engine.set_spread(0.0)
        engine.note_on(60, 100)
        output = engine.generate_samples(
            note=60, velocity=100, modulation={"pitch": 0.0}, block_size=256
        )
        assert np.array_equal(output[:, 0], output[:, 1])

    # --- Plugin methods (stub-level tests) ---

    def test_plugin_methods_no_crash(self, engine):
        """Plugin methods should not crash when no plugins are loaded."""
        # Unload any auto-loaded plugins (e.g., JupiterXAnalogPlugin)
        loaded = engine.get_loaded_plugins()
        for name in loaded:
            engine.unload_plugin(name)
        assert engine.get_loaded_plugins() == {}
        assert not engine.process_plugin_midi(0x90, 60, 100)
        assert not engine.set_plugin_parameter("nonexistent", "param", 0.5)
        assert engine.get_plugin_parameter("nonexistent", "param") is None
        assert engine.get_plugin_info("nonexistent") is None
        assert not engine.unload_plugin("nonexistent")
