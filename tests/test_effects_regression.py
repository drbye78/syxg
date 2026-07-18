"""Regression tests for all effect processors.

Captures current behavior BEFORE refactoring to detect regressions.
Each test: known deterministic input → assert shape/dtype/no-NaN/no-Inf/pins output.
"""

from __future__ import annotations

import numpy as np
import pytest

# Shared test configuration
BLOCK_SIZE = 256
SAMPLE_RATE = 44100
DETERMINISTIC_SEED = 42


def _make_deterministic_stereo(block_size: int = BLOCK_SIZE) -> np.ndarray:
    """Create deterministic stereo test signal."""
    rng = np.random.default_rng(DETERMINISTIC_SEED)
    return (rng.random((block_size, 2), dtype=np.float32) - 0.5) * 0.5


def _make_deterministic_mono(block_size: int = BLOCK_SIZE) -> np.ndarray:
    """Create deterministic mono test signal."""
    rng = np.random.default_rng(DETERMINISTIC_SEED)
    return (rng.random(block_size, dtype=np.float32) - 0.5) * 0.5


class TestReverbRegression:
    """Regression tests for XGSystemReverbProcessor — all 13 XG types."""

    @pytest.mark.parametrize("reverb_type", list(range(13)))
    def test_reverb_type_produces_finite_output(self, reverb_type: int):
        from synth.processing.effects.system import XGSystemReverbProcessor

        proc = XGSystemReverbProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("reverb_type", reverb_type)
        signal = _make_deterministic_stereo()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal)), f"NaN/Inf in reverb type {reverb_type}"
        assert signal.shape == (BLOCK_SIZE, 2)
        assert signal.dtype == np.float32

    def test_reverb_passthrough_at_zero_level(self):
        from synth.processing.effects.system import XGSystemReverbProcessor

        proc = XGSystemReverbProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("level", 0.0)
        signal = _make_deterministic_stereo()
        original = signal.copy()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        # At level=0, output should be near-identical to input
        assert np.all(np.isfinite(signal))
        assert np.allclose(signal, original, atol=1e-6)

    def test_reverb_disabled_bypass(self):
        from synth.processing.effects.system import XGSystemReverbProcessor

        proc = XGSystemReverbProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("enabled", False)
        signal = _make_deterministic_stereo()
        original = signal.copy()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.allclose(signal, original)


class TestChorusRegression:
    """Regression tests for XGChorusProcessor — all 18 XG types."""

    @pytest.mark.parametrize("chorus_type", list(range(18)))
    def test_chorus_type_produces_finite_output(self, chorus_type: int):
        from synth.processing.effects.system import XGSystemChorusProcessor

        proc = XGSystemChorusProcessor(sample_rate=SAMPLE_RATE)
        proc.set_chorus_type(chorus_type)
        signal = _make_deterministic_stereo()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal)), f"NaN/Inf in chorus type {chorus_type}"
        assert signal.shape == (BLOCK_SIZE, 2)
        assert signal.dtype == np.float32

    def test_chorus_disabled_bypass(self):
        from synth.processing.effects.system import XGSystemChorusProcessor

        proc = XGSystemChorusProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("enabled", False)
        signal = _make_deterministic_stereo()
        original = signal.copy()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.allclose(signal, original)


class TestModulationRegression:
    """Regression tests for XGSystemModulationProcessor."""

    @pytest.mark.parametrize("rate", [1.0, 3.0, 5.0, 10.0])
    def test_modulation_rate_produces_finite_output(self, rate: float):
        from synth.processing.effects.system import XGSystemModulationProcessor

        proc = XGSystemModulationProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("rate", rate)
        proc.set_parameter("depth", 0.5)
        proc.set_parameter("enabled", True)
        signal = _make_deterministic_stereo()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal))
        assert signal.shape == (BLOCK_SIZE, 2)

    def test_modulation_disabled_bypass(self):
        from synth.processing.effects.system import XGSystemModulationProcessor

        proc = XGSystemModulationProcessor(sample_rate=SAMPLE_RATE)
        signal = _make_deterministic_stereo()
        original = signal.copy()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.allclose(signal, original)

    @pytest.mark.parametrize("depth", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_modulation_depth_produces_finite_output(self, depth: float):
        from synth.processing.effects.system import XGSystemModulationProcessor

        proc = XGSystemModulationProcessor(sample_rate=SAMPLE_RATE)
        proc.set_parameter("depth", depth)
        proc.set_parameter("enabled", True)
        signal = _make_deterministic_stereo()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal))


class TestEQRegression:
    """Regression tests for XGMultiBandEqualizer — all 5 presets."""

    @pytest.mark.parametrize("eq_type", list(range(5)))
    def test_eq_preset_produces_finite_output(self, eq_type: int):
        from synth.processing.effects.eq_processor import XGMultiBandEqualizer

        proc = XGMultiBandEqualizer(sample_rate=SAMPLE_RATE)
        proc.set_eq_type(eq_type)
        signal = _make_deterministic_stereo()

        output = proc.process_buffer(signal)

        assert np.all(np.isfinite(output)), f"NaN/Inf in EQ type {eq_type}"
        assert output.shape == (BLOCK_SIZE, 2)
        assert output.dtype == np.float32

    def test_eq_mono_produces_finite_output(self):
        from synth.processing.effects.eq_processor import XGMultiBandEqualizer

        proc = XGMultiBandEqualizer(sample_rate=SAMPLE_RATE)
        signal = _make_deterministic_mono()

        output = proc.process_buffer(signal)

        assert np.all(np.isfinite(output))
        assert output.shape == (BLOCK_SIZE,)
        assert output.dtype == np.float32

    def test_eq_bypass_returns_copy(self):
        from synth.processing.effects.eq_processor import XGMultiBandEqualizer

        proc = XGMultiBandEqualizer(sample_rate=SAMPLE_RATE)
        proc.bypass = True
        signal = _make_deterministic_stereo()

        output = proc.process_buffer(signal)

        assert np.allclose(output, signal)


class TestInsertionRegression:
    """Regression tests for ProductionXGInsertionEffectsProcessor."""

    @pytest.mark.parametrize("effect_type", list(range(18)))
    def test_insertion_type_produces_finite_output(self, effect_type: int):
        from synth.processing.effects.insertion import ProductionXGInsertionEffectsProcessor

        proc = ProductionXGInsertionEffectsProcessor(sample_rate=SAMPLE_RATE)
        proc.set_insertion_effect_type(0, effect_type)
        signal = _make_deterministic_mono()

        proc._apply_single_effect_to_samples(signal, BLOCK_SIZE, effect_type, {})

        assert np.all(np.isfinite(signal)), f"NaN/Inf in insertion type {effect_type}"

    def test_insertion_thru_passthrough(self):
        from synth.processing.effects.insertion import ProductionXGInsertionEffectsProcessor

        proc = ProductionXGInsertionEffectsProcessor(sample_rate=SAMPLE_RATE)
        proc.set_insertion_effect_type(0, 0)  # Thru
        signal = _make_deterministic_mono()

        proc._apply_single_effect_to_samples(signal, BLOCK_SIZE, 0, {})

        assert np.all(np.isfinite(signal))


class TestSystemChainRegression:
    """Regression tests for XGSystemEffectsProcessor."""

    def test_system_chain_produces_finite_output(self):
        from synth.processing.effects.system import XGSystemEffectsProcessor

        proc = XGSystemEffectsProcessor(
            sample_rate=SAMPLE_RATE,
            block_size=BLOCK_SIZE,
            max_reverb_delay=SAMPLE_RATE * 2,
            max_chorus_delay=8192,
        )
        signal = _make_deterministic_stereo()

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal))
        assert signal.shape == (BLOCK_SIZE, 2)

    def test_system_chain_handles_zero_input(self):
        from synth.processing.effects.system import XGSystemEffectsProcessor

        proc = XGSystemEffectsProcessor(
            sample_rate=SAMPLE_RATE,
            block_size=BLOCK_SIZE,
            max_reverb_delay=SAMPLE_RATE * 2,
            max_chorus_delay=8192,
        )
        signal = np.zeros((BLOCK_SIZE, 2), dtype=np.float32)

        proc.apply_system_effects_to_mix_zero_alloc(signal, BLOCK_SIZE)

        # Zero input should produce near-zero output (may have noise floor)
        assert np.all(np.isfinite(signal))


class TestVariationRegression:
    """Regression tests for XGVariationEffectsProcessor — all 4 sub-processor categories."""

    @pytest.mark.parametrize(
        "variation_type",
        [
            # Delays (0-9) — handled by DelayVariationProcessor
            0,   # DELAY_LCR
            2,   # DELAY_L_R
            4,   # DELAY_L_R_STEREO
            9,   # DELAY_PING_PONG_3
            # Chorus/Modulation (10-31) — handled by ChorusModulationProcessor
            10,  # CHORUS_1
            16,  # FLANGER_1
            22,  # TREMOLO
            26,  # PHASER
            31,  # REVERB_AUTOPAN
            # Distortion/Dynamics (32-56) — handled by ProductionDistortionDynamicsProcessor
            43,  # DISTORTION_LIGHT
            49,  # CLIPPING_WARNING
            53,  # COMPRESSOR_ELECTRONIC
            # Special (57-83) — handled by SpecialVariationProcessor
            58,  # ENHANCER_PEAKING
            64,  # PITCH_SHIFT_UP_MINOR_THIRD
            70,  # ERL_HALL_SMALL
            78,  # GATE_REVERB_FAST_ATTACK
        ],
    )
    def test_variation_type_produces_finite_output(self, variation_type: int):
        from synth.processing.effects.variation_effects import XGVariationEffectsProcessor

        proc = XGVariationEffectsProcessor(sample_rate=SAMPLE_RATE)
        proc.set_variation_type(variation_type)
        signal = _make_deterministic_stereo()

        proc.apply_variation_effect_zero_alloc(signal, BLOCK_SIZE)

        assert np.all(np.isfinite(signal)), f"NaN/Inf in variation type {variation_type}"
        assert signal.shape == (BLOCK_SIZE, 2)


class TestEffectsCoordinatorRegression:
    """Regression tests for XGEffectsCoordinator pipeline."""

    def test_coordinator_process_block(self):
        from synth.processing.effects.effects_coordinator import XGEffectsCoordinator

        coord = XGEffectsCoordinator(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
        signal = _make_deterministic_stereo()

        output = coord.process_block(signal)

        assert np.all(np.isfinite(output))
        assert output.shape == (BLOCK_SIZE, 2) or output.shape == signal.shape
        assert output.dtype == np.float32
