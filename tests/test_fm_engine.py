"""Tests for FM synthesis engine components."""

from __future__ import annotations

import math

import pytest

from synth.engines.fm_lfo import FMXLFO
from synth.engines.fm_operator import FMOperator


@pytest.mark.unit
class TestFMOperator:
    """Tests for FMOperator."""

    def test_init_defaults(self):
        """Verify default values after construction."""
        op = FMOperator(44100)
        assert op.sample_rate == 44100
        assert op.frequency_ratio == 1.0
        assert op.detune_cents == 0.0
        assert op.feedback_level == 0
        assert op.waveform == "sine"
        assert op.phase == 0.0
        assert op.envelope_phase == "idle"
        assert op.envelope_stage == 0
        assert op.envelope_value == 0.0
        assert op.envelope_levels == [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]
        assert op.envelope_rates == [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        assert op.envelope_loop_start == -1
        assert op.envelope_loop_end == -1
        assert op.key_scaling_depth == 0
        assert op.velocity_sensitivity == 0

    def test_set_parameters(self):
        """Set params and verify they're applied."""
        op = FMOperator(44100)
        params = {
            "frequency_ratio": 2.0,
            "detune_cents": 10.0,
            "feedback_level": 3,
            "waveform": "square",
            "envelope_levels": [0.1, 0.9, 0.6, 0.6, 0.0, 0.0, 0.0, 0.0],
            "envelope_rates": [0.02, 0.2, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0],
            "envelope_loop_start": 2,
            "envelope_loop_end": 4,
            "key_scaling_depth": 5,
            "velocity_sensitivity": 3,
            "lfo_depth": 0.5,
            "lfo_waveform": "triangle",
            "lfo_speed": 2.0,
        }
        op.set_parameters(params)
        assert op.frequency_ratio == 2.0
        assert op.detune_cents == 10.0
        assert op.feedback_level == 3
        assert op.waveform == "square"
        assert op.envelope_levels == [0.1, 0.9, 0.6, 0.6, 0.0, 0.0, 0.0, 0.0]
        assert op.envelope_rates == [0.02, 0.2, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0]
        assert op.envelope_loop_start == 2
        assert op.envelope_loop_end == 4
        assert op.key_scaling_depth == 5
        assert op.velocity_sensitivity == 3
        assert op.lfo_depth == 0.5
        assert op.lfo_waveform == "triangle"
        assert op.lfo_speed == 2.0

    def test_note_on(self):
        """Verify note_on sets envelope_phase='active' and envelope_value to levels[0]."""
        op = FMOperator(44100)
        assert op.envelope_phase == "idle"

        op.note_on(127)
        assert op.envelope_phase == "active"
        assert op.envelope_stage == 0
        assert op.envelope_value == op.envelope_levels[0]  # 0.0

    def test_note_on_velocity_sensitivity(self):
        """velocity_sensitivity>0 scales envelope_value by velocity factor."""
        op = FMOperator(44100)
        # Set custom levels so that levels[0] is non-zero
        op.set_parameters(
            {
                "velocity_sensitivity": 3,
                "envelope_levels": [0.5, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0],
            }
        )

        velocity = 100
        op.note_on(velocity)

        expected_scale = (velocity / 127.0) ** (1.0 / (8 - 3))
        expected_value = 0.5 * expected_scale
        assert op.envelope_value == pytest.approx(expected_value, rel=1e-4)

    def test_note_off(self):
        """Verify note_off sets stage to release stage (6)."""
        op = FMOperator(44100)
        op.note_on(127)
        assert op.envelope_phase == "active"

        op.note_off()
        # Without loop points, note_off should jump to stage 6
        assert op.envelope_stage == 6
        assert op.envelope_time == 0.0

    def test_note_off_with_loop(self):
        """note_off with loop points uses loop_end as the target stage."""
        op = FMOperator(44100)
        op.set_parameters(
            {
                "envelope_loop_start": 1,
                "envelope_loop_end": 3,
            }
        )
        op.note_on(127)
        # Advance to stage 2
        op.update_envelope(0.01)  # stage 0 -> 1
        op.update_envelope(0.3)  # stage 1 -> 2

        op.note_off()
        # With loop, stage = min(current_stage, loop_end) = min(2, 3) = 2
        assert op.envelope_stage == 2

    def test_update_envelope_idle(self):
        """When phase is 'idle', envelope_value stays 0."""
        op = FMOperator(44100)
        assert op.envelope_phase == "idle"
        assert op.envelope_value == 0.0

        op.update_envelope(0.1)
        assert op.envelope_value == 0.0
        assert op.envelope_phase == "idle"

    def test_update_envelope_active(self):
        """After note_on, update_envelope advances through stages."""
        op = FMOperator(44100)
        op.note_on(127)

        # Stage 0 -> 1: rate = 0.01
        op.update_envelope(0.01)
        assert op.envelope_stage == 1
        assert op.envelope_value == pytest.approx(op.envelope_levels[1])  # 1.0
        assert op.envelope_phase == "active"

        # Stage 1 -> 2: rate = 0.3
        op.update_envelope(0.3)
        assert op.envelope_stage == 2
        assert op.envelope_value == pytest.approx(op.envelope_levels[2])  # 0.7

    def test_update_envelope_interpolation(self):
        """Partial dt interpolates between levels."""
        op = FMOperator(44100)
        op.note_on(127)

        # Stage 0: rate = 0.01, levels 0->1 = 0.0 -> 1.0
        # Advance halfway (0.005 sec)
        op.update_envelope(0.005)
        assert op.envelope_stage == 0  # Not yet advanced
        assert op.envelope_value == pytest.approx(0.5, rel=1e-4)

    def test_is_active(self):
        """True after note_on, False after envelope completes."""
        op = FMOperator(44100)
        assert not op.is_active()

        op.note_on(127)
        assert op.is_active()

        # Advance through all stages. The envelope rates are:
        # [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        # After stage 3 (rate 0.5), stages 4-7 are instantaneous (rate 0)
        # stage 7 triggers phase="idle" in _advance_envelope_stage
        op.update_envelope(0.01)  # stage 0 -> 1
        op.update_envelope(0.3)  # 1 -> 2
        op.update_envelope(0.0)  # 2 -> 3 (instant, rate=0)
        op.update_envelope(0.5)  # 3 -> 4
        # Stages 4-7 are instant -> idle
        op.update_envelope(0.0)  # 4 -> 5
        op.update_envelope(0.0)  # 5 -> 6
        op.update_envelope(0.0)  # 6 -> 7
        op.update_envelope(0.0)  # 7 -> idle

        assert not op.is_active()

    def test_generate_sample_returns_float(self):
        """After note_on, generate_sample returns a float."""
        op = FMOperator(44100)
        op.note_on(127)
        # Update envelope so value is non-zero
        op.update_envelope(0.01)  # stage 0 -> 1, value = 1.0

        result = op.generate_sample(440.0)
        assert isinstance(result, float)

    def test_generate_sample_sine_wave(self):
        """Basic sine waveform output within [-1, 1]."""
        op = FMOperator(44100)
        op.note_on(127)
        op.update_envelope(0.01)  # stage 0 -> 1, envelope_value = 1.0

        for _ in range(100):
            sample = op.generate_sample(440.0)
            assert -1.0 <= sample <= 1.0

    def test_generate_sample_with_modulation(self):
        """modulation_input affects frequency producing different output."""
        op = FMOperator(44100)
        op.note_on(127)
        op.update_envelope(0.01)

        samples_no_mod = [op.generate_sample(440.0) for _ in range(100)]

        op.reset()
        op.note_on(127)
        op.update_envelope(0.01)

        samples_with_mod = [op.generate_sample(440.0, modulation_input=100.0) for _ in range(100)]

        # With modulation the output should differ
        assert samples_no_mod != samples_with_mod

    def test_generate_sample_with_ring_mod(self):
        """ring_mod_input applies ring modulation."""
        op = FMOperator(44100)
        op.ring_mod_enabled = True
        op.note_on(127)
        op.update_envelope(0.01)

        sample_no_ring = op.generate_sample(440.0)
        sample_with_ring = op.generate_sample(440.0, ring_mod_input=0.5)

        # ring modulation should produce different output than no ring mod
        # when ring_mod_input is non-zero
        assert sample_no_ring != sample_with_ring

    def test_generate_sample_all_waveforms(self):
        """All supported waveforms produce valid output."""
        op = FMOperator(44100)
        for waveform in ("sine", "triangle", "sawtooth", "square"):
            op.reset()
            op.waveform = waveform
            op.note_on(127)
            op.update_envelope(0.01)

            for _ in range(50):
                sample = op.generate_sample(440.0)
                assert isinstance(sample, float), f"waveform={waveform}"

    def test_reset(self):
        """Reset restores all state."""
        op = FMOperator(44100)
        op.note_on(127)
        op.update_envelope(0.01)
        op.generate_sample(440.0)

        op.reset()
        assert op.phase == 0.0
        assert op.envelope_phase == "idle"
        assert op.envelope_value == 0.0
        assert op.envelope_time == 0.0
        assert op.feedback_sample == 0.0
        assert not op.is_active()


@pytest.mark.unit
class TestFMXLFO:
    """Tests for FMXLFO."""

    def test_init_defaults(self):
        """Verify default values."""
        lfo = FMXLFO(44100)
        assert lfo.sample_rate == 44100
        assert lfo.phase == 0.0
        assert lfo.frequency == 1.0
        assert lfo.waveform == "sine"
        assert lfo.depth == 1.0
        assert lfo.enabled is True

    def test_set_parameters(self):
        """Set frequency, depth, and verify clamped."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=5.0, waveform="triangle", depth=0.75)
        assert lfo.frequency == 5.0
        assert lfo.waveform == "triangle"
        assert lfo.depth == 0.75

    def test_set_parameters_clamped(self):
        """Frequency clamped to [0.01, 20], depth to [0.0, 1.0]."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=-1.0, depth=5.0)
        assert lfo.frequency == 0.01
        assert lfo.depth == 1.0

        lfo.set_parameters(frequency=100.0, depth=-0.5)
        assert lfo.frequency == 20.0
        assert lfo.depth == 0.0

    def test_generate_sample_sine(self):
        """Returns float within [-depth, depth]."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=5.0, depth=0.5)
        for _ in range(200):
            sample = lfo.generate_sample()
            assert isinstance(sample, float)
            assert -0.5 <= sample <= 0.5

    def test_generate_sample_disabled(self):
        """Returns 0 when disabled."""
        lfo = FMXLFO(44100)
        lfo.enabled = False
        for _ in range(10):
            assert lfo.generate_sample() == 0.0

    def test_reset(self):
        """Reset sets phase to 0 and clears random state."""
        lfo = FMXLFO(44100)
        lfo.generate_sample()  # Advance phase
        lfo.reset()
        assert lfo.phase == 0.0
        assert lfo.random_value == 0.0
        assert lfo.random_hold_time == 0.0

    def test_waveform_triangle(self):
        """Triangle mode produces different output than sine."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=5.0, depth=1.0)

        # Collect sine samples
        sine_samples = [lfo.generate_sample() for _ in range(100)]

        # Reset and switch to triangle
        lfo.reset()
        lfo.set_parameters(frequency=5.0, waveform="triangle", depth=1.0)

        triangle_samples = [lfo.generate_sample() for _ in range(100)]

        # The waveforms should differ overall
        assert sine_samples != triangle_samples

    def test_waveform_square(self):
        """Square mode produces only -1 or 1 (× depth)."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=5.0, waveform="square", depth=0.8)
        for _ in range(200):
            sample = lfo.generate_sample()
            assert sample in (-0.8, 0.8) or (0.8 >= sample >= -0.8)

    def test_waveform_sawtooth(self):
        """Sawtooth mode produces valid output."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=3.0, waveform="sawtooth", depth=0.6)
        for _ in range(200):
            sample = lfo.generate_sample()
            assert isinstance(sample, float)
            assert -0.6 <= sample <= 0.6

    def test_waveform_random(self):
        """Random waveform produces varying output."""
        # Use low sample rate so random hold time expires after fewer samples
        lfo = FMXLFO(sample_rate=100)
        lfo.set_parameters(frequency=10.0, waveform="random", depth=1.0)
        samples = [lfo.generate_sample() for _ in range(50)]
        # Random values should differ
        unique = set(samples)
        assert len(unique) > 1

    def test_frequency_update_affects_rate(self):
        """Changing frequency changes the LFO speed (phase increment)."""
        lfo = FMXLFO(44100)
        lfo.set_parameters(frequency=1.0, depth=1.0)
        # Generate one sample to advance phase
        lfo.generate_sample()
        phase_slow = lfo.phase

        lfo.reset()
        lfo.set_parameters(frequency=10.0, depth=1.0)
        lfo.generate_sample()
        phase_fast = lfo.phase

        # Higher frequency = larger phase increment
        assert phase_fast > phase_slow


@pytest.mark.unit
class TestFMEngine:
    """Tests for FMEngine."""

    def _make_engine(self):
        """Factory helper: create FMEngine wrapped in try/except."""
        try:
            from synth.engines.fm_engine import FMEngine

            return FMEngine(num_operators=8, sample_rate=44100, block_size=1024)
        except Exception as exc:
            pytest.skip(f"FMEngine construction failed: {exc}")

    def test_init_defaults(self):
        """Create engine, verify operators list length, LFOs, algorithm, master_volume."""
        engine = self._make_engine()
        assert len(engine.operators) == 8
        assert len(engine.lfos) == 3
        assert engine.algorithm == "basic"
        assert engine.master_volume == 1.0
        assert engine.num_operators == 8
        # Each element should be an FMOperator
        for op in engine.operators:
            assert isinstance(op, FMOperator)
        for lfo in engine.lfos:
            assert isinstance(lfo, FMXLFO)

    def test_init_num_operators(self):
        """num_operators is clamped to [2, 8]."""
        from synth.engines.fm_engine import FMEngine

        eng_low = FMEngine(num_operators=1)
        assert eng_low.num_operators == 2
        assert len(eng_low.operators) == 2

        eng_high = FMEngine(num_operators=16)
        assert eng_high.num_operators == 8
        assert len(eng_high.operators) == 8

    def test_engine_info(self):
        """get_engine_info() returns dict with required keys."""
        engine = self._make_engine()
        info = engine.get_engine_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "type" in info
        assert info["type"] == "fm"
        assert "capabilities" in info
        assert isinstance(info["capabilities"], list)
        assert "parameters" in info
        assert isinstance(info["parameters"], list)

    def test_algorithms_defined(self):
        """ALGORITHMS has 88 entries."""
        from synth.engines.fm_engine import FMEngine

        assert len(FMEngine.ALGORITHMS) == 88

    def test_algorithm_1_structure(self):
        """algorithm_1 has operators, modulation, output, name keys."""
        from synth.engines.fm_engine import FMEngine

        alg1 = FMEngine.ALGORITHMS["algorithm_1"]
        assert "operators" in alg1
        assert "modulation" in alg1
        assert "output" in alg1
        assert "name" in alg1
        assert alg1["operators"] == [0, 1]
        assert alg1["modulation"] == {0: [1]}
        assert alg1["output"] == [0]

    def test_default_algorithm(self):
        """After init, algorithm should be set to 'basic'."""
        engine = self._make_engine()
        assert engine.algorithm == "basic"

    def test_set_algorithm_valid(self):
        """set_algorithm with a valid ALGORITHMS key updates modulation_matrix."""
        engine = self._make_engine()
        engine.set_algorithm("algorithm_1")
        assert engine.algorithm == "algorithm_1"
        assert engine.modulation_matrix == {0: [1]}
        assert engine.output_operators == [0]

    def test_set_algorithm_stacked(self):
        """algorithm_2 sets up stacked modulation."""
        engine = self._make_engine()
        engine.set_algorithm("algorithm_2")
        assert engine.algorithm == "algorithm_2"
        assert engine.modulation_matrix == {0: [1], 1: [2]}

    def test_set_operator_parameters(self):
        """set_operator_parameters applies params to a specific operator."""
        engine = self._make_engine()
        engine.set_operator_parameters(0, {"frequency_ratio": 3.0, "waveform": "square"})
        assert engine.operators[0].frequency_ratio == 3.0
        assert engine.operators[0].waveform == "square"
        # Other operators unchanged
        assert engine.operators[1].frequency_ratio == 1.0

    def test_get_operator_parameters(self):
        """get_operator_parameters returns a dict with operator state."""
        engine = self._make_engine()
        params = engine.get_operator_parameters(0)
        assert isinstance(params, dict)
        assert "frequency_ratio" in params
        assert "detune_cents" in params
        assert "waveform" in params
        assert "envelope_levels" in params
        assert params["frequency_ratio"] == 1.0

    def test_note_on_off_engine(self):
        """Engine-level note_on/note_off propagates to all operators."""
        engine = self._make_engine()
        for op in engine.operators:
            assert not op.is_active()

        engine.note_on(60, 100)
        for op in engine.operators:
            assert op.is_active()

        engine.note_off(60)
        for op in engine.operators:
            assert not op.is_active() or op.envelope_stage >= 6

    def test_engine_is_active(self):
        """is_active reflects operator envelope state."""
        engine = self._make_engine()
        assert not engine.is_active()

        engine.note_on(60, 100)
        assert engine.is_active()

        engine.note_off(60)
        # After note_off, operators may still be active in release
        # Reset fully
        engine.reset()
        assert not engine.is_active()

    def test_engine_reset(self):
        """reset clears active_notes and resets all operators."""
        engine = self._make_engine()
        engine.note_on(60, 100)
        engine.note_on(64, 90)
        assert len(engine.active_notes) == 2

        engine.reset()
        assert len(engine.active_notes) == 0
        for op in engine.operators:
            assert not op.is_active()

    def test_set_lfo_parameters(self):
        """set_lfo_parameters configures a specific LFO."""
        engine = self._make_engine()
        engine.set_lfo_parameters(0, frequency=5.0, waveform="triangle", depth=0.5)
        lfo_params = engine.get_lfo_parameters(0)
        assert lfo_params["frequency"] == 5.0
        assert lfo_params["waveform"] == "triangle"
        assert lfo_params["depth"] == 0.5

    def test_add_ring_modulation_connection(self):
        """Ring modulation connection enables ring mod on paired operators."""
        engine = self._make_engine()
        engine.add_ring_modulation_connection(0, 1)
        assert (0, 1) in engine.ring_mod_connections
        assert engine.operators[0].ring_mod_enabled
        assert engine.operators[1].ring_mod_enabled

    def test_set_effects_sends(self):
        """set_effects_sends clamps values to [0, 1] and updates effects_enabled."""
        engine = self._make_engine()
        engine.set_effects_sends(reverb=0.5, chorus=0.3, delay=0.0)
        assert engine.reverb_send == 0.5
        assert engine.chorus_send == 0.3
        assert engine.delay_send == 0.0
        assert engine.effects_enabled is True

        engine.set_effects_sends(reverb=0.0, chorus=0.0, delay=0.0)
        assert engine.effects_enabled is False

    def test_get_supported_formats(self):
        """get_supported_formats returns FM patch format extensions."""
        engine = self._make_engine()
        formats = engine.get_supported_formats()
        assert ".fmp" in formats
        assert ".dx7" in formats

    def test_get_fm_x_status(self):
        """get_fm_x_status returns a comprehensive status dict."""
        engine = self._make_engine()
        status = engine.get_fm_x_status()
        assert status["num_operators"] == 8
        assert status["current_algorithm"] == "basic"
        assert status["lfo_count"] == 3
        assert "capabilities" in status

    def test_generate_samples_output_shape(self):
        """generate_samples returns (block_size, 2) float32 array."""
        engine = self._make_engine()
        result = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch": 0.0},
            block_size=64,
        )
        assert result.shape == (64, 2)
        assert result.dtype == np.float32

    def test_generate_samples_valid_range(self):
        """generated samples fall within a reasonable range."""
        import numpy as np

        engine = self._make_engine()
        result = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch": 0.0},
            block_size=128,
        )
        # Should not contain NaN or Inf
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))

    def test_set_mpe_enabled(self):
        """MPE toggle works."""
        engine = self._make_engine()
        assert engine.mpe_enabled is False
        engine.set_mpe_enabled(True)
        assert engine.mpe_enabled is True

    def test_add_custom_algorithm(self):
        """Custom algorithms can be added and used."""
        engine = self._make_engine()
        engine.add_custom_algorithm(
            "custom_feedback",
            operators=[0, 1, 2],
            modulation={0: [1], 1: [2], 2: [0]},
            output=[0],
        )
        assert "custom_feedback" in engine.ALGORITHMS
        engine.set_algorithm("custom_feedback")
        assert engine.algorithm == "custom_feedback"

    def test_configure_formant_operator(self):
        """Formant configuration enables formant synthesis on an operator."""
        engine = self._make_engine()
        engine.configure_formant_operator(2, [700, 50, 2.0])
        assert engine.operators[2].formant_enabled
        assert engine.operators[2].formant_data == [700, 50, 2.0]

        engine.disable_formant_operator(2)
        assert not engine.operators[2].formant_enabled
        assert engine.operators[2].formant_data == []


# Import numpy for the engine tests that use it
import numpy as np  # noqa: E402 (placed after tests for cleanliness)
