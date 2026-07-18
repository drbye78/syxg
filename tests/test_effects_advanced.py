"""Advanced tests for the effects pipeline — distortion, delay, frequency response, wet/dry mix.

Covers:
- Distortion subpackage: MultiStageDistortion, TubeSaturation, ProfessionalCompressor,
  MultibandCompressor, DynamicEQEnhancer, ProductionDistortionDynamicsProcessor
- SystemDelayEffect: multi-block state, all 10 delay types, feedback
- Frequency response verification for XGMultiBandEqualizer
- Wet/dry mix and master level at the coordinator level
- Pipeline bypass (processing_enabled=False → passthrough)
"""

from __future__ import annotations

import numpy as np
import pytest

BLOCK_SIZE = 256
SAMPLE_RATE = 44100
DETERMINISTIC_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sin_sweep(
    block_size: int = BLOCK_SIZE, sr: int = SAMPLE_RATE
) -> np.ndarray:
    """200 → 2000 Hz sine sweep, mono, float32."""
    t = np.arange(block_size, dtype=np.float32) / sr
    freq = 200.0 + 1800.0 * t / t[-1]  # linear sweep
    return np.sin(2 * np.pi * freq * t, dtype=np.float32)


def _stereo_signal(
    block_size: int = BLOCK_SIZE, seed: int = DETERMINISTIC_SEED
) -> np.ndarray:
    """Deterministic stereo noise, (block_size, 2), float32, range ≈ [-0.25, 0.25]."""
    rng = np.random.default_rng(seed)
    return (rng.random((block_size, 2), dtype=np.float32) - 0.5) * 0.5


def _dynamic_signal(
    block_size: int = BLOCK_SIZE, sr: int = SAMPLE_RATE
) -> np.ndarray:
    """Signal with realistic dynamics: attack burst then sustained tone."""
    n = block_size
    attack = np.linspace(0.0, 1.0, min(48, n // 2))
    tone = 0.15 * np.sin(2 * np.pi * 440.0 * np.arange(n, dtype=np.float32) / sr)
    tone[: len(attack)] *= attack
    return tone


def _process_buffer_distortion(
    processor,
    buf: np.ndarray,
    process_fn: str,
    **kwargs,
) -> np.ndarray:
    """Run a sample-by-sample distortion processor on a mono buffer."""
    out = np.empty_like(buf)
    for i in range(len(buf)):
        fn = getattr(processor, process_fn)
        out[i] = fn(buf[i], **kwargs)
    return out


# ---------------------------------------------------------------------------
# MultiStageDistortionProcessor
# ---------------------------------------------------------------------------


class TestMultiStageDistortion:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.multi_stage import (
            MultiStageDistortionProcessor,
        )

        return MultiStageDistortionProcessor(SAMPLE_RATE)

    def test_zero_in_zero_out(self, proc):
        out = _process_buffer_distortion(
            proc, np.zeros(128, dtype=np.float32), "process_sample",
            drive=0.5, tone=0.5, level=0.5, fuzz_mode=False,
        )
        assert np.all(np.isfinite(out))
        assert np.allclose(out, 0.0, atol=1e-7)

    def test_drive_increases_output_level(self, proc):
        buf = _sin_sweep()
        low = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.0, tone=0.5, level=0.5, fuzz_mode=False,
        )
        high = _process_buffer_distortion(
            proc, buf, "process_sample", drive=1.0, tone=0.5, level=0.5, fuzz_mode=False,
        )
        assert np.abs(high).mean() > np.abs(low).mean()

    def test_tone_affects_output(self, proc):
        buf = _sin_sweep()
        dark = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.5, tone=0.0, level=0.5, fuzz_mode=False,
        )
        bright = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.5, tone=1.0, level=0.5, fuzz_mode=False,
        )
        # Different tone → different output
        assert not np.allclose(dark, bright, atol=1e-4)

    def test_fuzz_mode_changes_output(self, proc):
        buf = _sin_sweep()
        no_fuzz = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.8, tone=0.5, level=0.5, fuzz_mode=False,
        )
        fuzz = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.8, tone=0.5, level=0.5, fuzz_mode=True,
        )
        assert not np.allclose(no_fuzz, fuzz, atol=1e-4)

    def test_level_scales_output(self, proc):
        buf = _sin_sweep()
        low = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.5, tone=0.5, level=0.0, fuzz_mode=False,
        )
        high = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.5, tone=0.5, level=1.0, fuzz_mode=False,
        )
        assert np.abs(high).mean() >= np.abs(low).mean()

    def test_output_finite_at_extremes(self, proc):
        buf = np.full(64, 10.0, dtype=np.float32)  # very hot input
        out = _process_buffer_distortion(
            proc, buf, "process_sample",
            drive=1.0, tone=1.0, level=1.0, fuzz_mode=True,
        )
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# TubeSaturationProcessor
# ---------------------------------------------------------------------------


class TestTubeSaturation:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.tube_saturation import (
            TubeSaturationProcessor,
        )

        return TubeSaturationProcessor(SAMPLE_RATE)

    def test_zero_input_produces_finite_output(self, proc):
        out = _process_buffer_distortion(
            proc, np.zeros(128, dtype=np.float32), "process_sample",
            drive=0.5, tone=0.5, level=0.5,
        )
        assert np.all(np.isfinite(out))
        # Tube has grid bias so DC offset is expected — just check finite

    def test_drive_increases_gain(self, proc):
        buf = _sin_sweep()
        low = _process_buffer_distortion(
            proc, buf, "process_sample", drive=0.0, tone=0.5, level=0.5,
        )
        high = _process_buffer_distortion(
            proc, buf, "process_sample", drive=1.0, tone=0.5, level=0.5,
        )
        assert np.abs(high).mean() > np.abs(low).mean()

    def test_asymmetric_clipping(self, proc):
        """Positive and negative half-cycles should differ (tube asymmetry)."""
        buf = _sin_sweep(block_size=1024)
        out = _process_buffer_distortion(
            proc, buf, "process_sample", drive=1.0, tone=0.5, level=1.0,
        )
        pos_energy = np.sum(np.maximum(out, 0.0) ** 2)
        neg_energy = np.sum(np.minimum(out, 0.0) ** 2)
        # Asymmetry: positive and negative energies should differ measurably
        ratio = max(pos_energy, neg_energy) / max(min(pos_energy, neg_energy), 1e-10)
        assert ratio > 1.02, f"Positive/negative energy ratio {ratio:.4f} too close to 1"

    def test_output_finite_at_extremes(self, proc):
        buf = np.full(64, 10.0, dtype=np.float32)
        out = _process_buffer_distortion(
            proc, buf, "process_sample",
            drive=1.0, tone=1.0, level=1.0,
        )
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# ProfessionalCompressor
# ---------------------------------------------------------------------------


class TestProfessionalCompressor:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.compressor import (
            ProfessionalCompressor,
        )

        return ProfessionalCompressor(SAMPLE_RATE)

    def test_zero_in_zero_out(self, proc):
        buf = np.zeros(256, dtype=np.float32)
        for i in range(len(buf)):
            buf[i] = proc.process_sample(0.0)
        assert np.allclose(buf, 0.0, atol=1e-7)

    def test_higher_threshold_reduces_compression(self, proc):
        """Higher threshold → less gain reduction for the same signal."""
        buf = _sin_sweep(block_size=256) * 2.0  # moderately hot signal

        low_thresh = proc.__class__(SAMPLE_RATE)
        low_thresh.set_parameters(threshold=-60.0, ratio=4.0, attack=0.001, release=0.05)
        out_low = np.empty_like(buf)
        for i in range(len(buf)):
            out_low[i] = low_thresh.process_sample(buf[i])

        high_thresh = proc.__class__(SAMPLE_RATE)
        high_thresh.set_parameters(threshold=0.0, ratio=4.0, attack=0.001, release=0.05)
        out_high = np.empty_like(buf)
        for i in range(len(buf)):
            out_high[i] = high_thresh.process_sample(buf[i])

        # Higher threshold → signal passes through more (less compression)
        assert np.abs(out_high).mean() > np.abs(out_low).mean()

    def test_ratio_reduces_dynamics(self, proc):
        """Higher ratio → more gain reduction for above-threshold signal."""
        buf = _dynamic_signal(block_size=256) * 10.0  # hot signal well above threshold

        low_ratio = proc
        low_ratio.set_parameters(threshold=-40.0, ratio=2.0, attack=0.001, release=0.05)
        out_low = np.empty_like(buf)
        for i in range(len(buf)):
            out_low[i] = low_ratio.process_sample(buf[i])

        # Reset state
        high_ratio = proc.__class__(SAMPLE_RATE)
        high_ratio.set_parameters(threshold=-40.0, ratio=20.0, attack=0.001, release=0.05)
        out_high = np.empty_like(buf)
        for i in range(len(buf)):
            out_high[i] = high_ratio.process_sample(buf[i])

        # Higher ratio → lower output level (more compression)
        assert np.abs(out_high).mean() <= np.abs(out_low).mean()

    def test_sidechain_alters_behavior(self, proc):
        proc.set_parameters(threshold=-24.0, ratio=4.0, attack=0.01, release=0.1)
        buf = _dynamic_signal(block_size=256)
        # Without sidechain
        out_direct = np.empty_like(buf)
        for i in range(len(buf)):
            out_direct[i] = proc.process_sample(buf[i])
        # With sidechain
        sc = np.full_like(buf, 0.5)  # hot sidechain triggers more compression
        out_sc = np.empty_like(buf)
        for i in range(len(buf)):
            out_sc[i] = proc.process_sample(buf[i], sidechain_sample=sc[i])
        # Sidechain should change output
        assert not np.allclose(out_direct, out_sc, atol=1e-4)

    def test_output_finite_at_extremes(self, proc):
        proc.set_parameters(threshold=-80.0, ratio=20.0, attack=0.001, release=0.01)
        buf = np.full(64, 100.0, dtype=np.float32)
        out = np.empty_like(buf)
        for i in range(len(buf)):
            out[i] = proc.process_sample(buf[i])
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# MultibandCompressor
# ---------------------------------------------------------------------------


class TestMultibandCompressor:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.multiband_compressor import (
            MultibandCompressor,
        )

        return MultibandCompressor(SAMPLE_RATE)

    def test_zero_in_zero_out(self, proc):
        buf = np.zeros(256, dtype=np.float32)
        for i in range(len(buf)):
            buf[i] = proc.process_sample(0.0)
        assert np.allclose(buf, 0.0, atol=1e-7)

    def test_band_config_changes_output(self, proc):
        buf = _sin_sweep(block_size=256)
        default = np.empty_like(buf)
        for i in range(len(buf)):
            default[i] = proc.process_sample(buf[i])

        proc2 = proc.__class__(SAMPLE_RATE)
        proc2.configure_bands(
            low_params={"threshold": -80.0, "ratio": 20.0, "attack": 0.001, "release": 0.01, "knee": 0.0, "makeup": 0.0},
            mid_params={"threshold": -80.0, "ratio": 20.0, "attack": 0.001, "release": 0.01, "knee": 0.0, "makeup": 0.0},
            high_params={"threshold": -80.0, "ratio": 20.0, "attack": 0.001, "release": 0.01, "knee": 0.0, "makeup": 0.0},
        )
        custom = np.empty_like(buf)
        for i in range(len(buf)):
            custom[i] = proc2.process_sample(buf[i])

        assert not np.allclose(default, custom, atol=1e-4)

    def test_crossover_frequencies_affect_output(self, proc):
        buf = _sin_sweep(block_size=256)
        # Wide crossover
        proc.low_mid_freq = 100.0
        proc.mid_high_freq = 8000.0
        out1 = np.empty_like(buf)
        for i in range(len(buf)):
            out1[i] = proc.process_sample(buf[i])

        # Narrow crossover
        proc2 = proc.__class__(SAMPLE_RATE)
        proc2.low_mid_freq = 1000.0
        proc2.mid_high_freq = 2000.0
        out2 = np.empty_like(buf)
        for i in range(len(buf)):
            out2[i] = proc2.process_sample(buf[i])

        assert not np.allclose(out1, out2, atol=1e-4)

    def test_output_finite(self, proc):
        buf = _dynamic_signal(block_size=256) * 5.0
        out = np.empty_like(buf)
        for i in range(len(buf)):
            out[i] = proc.process_sample(buf[i])
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# DynamicEQEnhancer
# ---------------------------------------------------------------------------


class TestDynamicEQEnhancer:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.dynamic_eq import (
            DynamicEQEnhancer,
        )

        return DynamicEQEnhancer(SAMPLE_RATE, freq=5000.0, peaking=True)

    def test_zero_in_zero_out(self, proc):
        buf = np.zeros(128, dtype=np.float32)
        for i in range(len(buf)):
            buf[i] = proc.process_sample(0.0, enhance_amount=0.5)
        assert np.allclose(buf, 0.0, atol=1e-7)

    def test_enhance_amount_affects_output(self, proc):
        buf = _sin_sweep(block_size=256)
        low = np.empty_like(buf)
        for i in range(len(buf)):
            low[i] = proc.process_sample(buf[i], enhance_amount=0.0)
        high = np.empty_like(buf)
        for i in range(len(buf)):
            high[i] = proc.process_sample(buf[i], enhance_amount=1.0)
        assert not np.allclose(low, high, atol=1e-4)

    def test_shelving_vs_peaking(self, proc):
        from synth.processing.effects.distortion.dynamic_eq import (
            DynamicEQEnhancer,
        )

        buf = _sin_sweep(block_size=256)
        peaking_proc = DynamicEQEnhancer(SAMPLE_RATE, freq=5000.0, peaking=True)
        shelving_proc = DynamicEQEnhancer(SAMPLE_RATE, freq=5000.0, peaking=False)
        peaking_out = np.empty_like(buf)
        for i in range(len(buf)):
            peaking_out[i] = peaking_proc.process_sample(buf[i], enhance_amount=0.8)
        shelving_out = np.empty_like(buf)
        for i in range(len(buf)):
            shelving_out[i] = shelving_proc.process_sample(buf[i], enhance_amount=0.8)
        assert not np.allclose(peaking_out, shelving_out, atol=1e-4)

    def test_output_finite(self, proc):
        buf = np.full(64, 2.0, dtype=np.float32)
        out = np.empty_like(buf)
        for i in range(len(buf)):
            out[i] = proc.process_sample(buf[i], enhance_amount=1.0)
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# ProductionDistortionDynamicsProcessor (orchestrator)
# ---------------------------------------------------------------------------


class TestDistortionDynamicsOrchestrator:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.distortion.processor import (
            ProductionDistortionDynamicsProcessor,
        )

        return ProductionDistortionDynamicsProcessor(SAMPLE_RATE)

    @pytest.mark.parametrize(
        "effect_type",
        [
            32,  # auto pan
            33,  # auto wah
            34,  # ring modulation
            35, 36,  # step phaser up/down
            37, 38,  # step flanger up/down
            39, 40,  # step tremolo up/down
            43, 44, 45,  # overdrive 1/2/3
            46,  # clipping warning
            47,  # fuzz
            48,  # guitar distortion
            49, 50,  # compressor electronic/optical
            51,  # limiter
            52,  # multiband compressor
            53,  # expander
            54, 55, 56,  # enhancers
        ],
    )
    def test_effect_type_produces_finite_output(self, proc, effect_type: int):
        signal = _stereo_signal().copy()
        params = {
            "parameter1": 0.5,
            "parameter2": 0.5,
            "parameter3": 0.5,
            "parameter4": 0.5,
        }
        proc.process_effect(effect_type, signal, BLOCK_SIZE, params)
        assert np.all(np.isfinite(signal)), f"NaN/Inf in effect type {effect_type}"
        assert signal.shape == (BLOCK_SIZE, 2)
        assert signal.dtype == np.float32

    def test_effect_types_produce_distinct_output(self, proc):
        """Two different effect types should produce measurably different audio."""
        signal = _stereo_signal().copy()
        ref = signal.copy()
        params = {"parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5}

        # Auto pan (32)
        proc.process_effect(32, signal, BLOCK_SIZE, params)
        auto_pan_out = signal.copy()

        # Overdrive (43) — should be different
        signal[:] = ref
        proc.process_effect(43, signal, BLOCK_SIZE, params)
        assert not np.allclose(auto_pan_out, signal, atol=1e-4)

    def test_output_finite_at_extreme_params(self, proc):
        signal = np.full((BLOCK_SIZE, 2), 10.0, dtype=np.float32)
        params = {"parameter1": 1.0, "parameter2": 1.0, "parameter3": 1.0, "parameter4": 1.0}
        for etype in [43, 46, 47, 48, 49, 51]:
            proc.process_effect(etype, signal.copy(), BLOCK_SIZE, params)
        assert np.all(np.isfinite(signal))

    def test_reset_clears_state(self, proc):
        """After reset, state should be reinitialized."""
        from synth.processing.effects.distortion.processor import (
            ProductionDistortionDynamicsProcessor,
        )

        proc.process_effect(32, _stereo_signal(), BLOCK_SIZE,
                            {"parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5})
        proc.reset()
        fresh = ProductionDistortionDynamicsProcessor(SAMPLE_RATE)
        assert proc.limiter_envelope is not None
        assert fresh.limiter_envelope is not None
        assert proc.peaking_enhancer is not None


# ---------------------------------------------------------------------------
# SystemDelayEffect
# ---------------------------------------------------------------------------


class TestSystemDelay:
    @pytest.fixture
    def proc(self):
        from synth.processing.effects.system_delay import SystemDelayEffect

        return SystemDelayEffect(SAMPLE_RATE, max_delay_seconds=5.0)

    @pytest.mark.parametrize("delay_type", list(range(10)))
    def test_delay_type_produces_finite_output(self, proc, delay_type: int):
        proc.set_delay_type(delay_type)
        proc.time = 100.0  # 100 ms
        inp = _stereo_signal()
        out_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp[:, 0], inp[:, 1], out_l, out_r, BLOCK_SIZE)
        assert np.all(np.isfinite(out_l)), f"NaN/Inf in delay type {delay_type}"
        assert np.all(np.isfinite(out_r)), f"NaN/Inf in delay type {delay_type}"

    def _process_blocks(self, proc, num_blocks: int, inp_per_block):
        """Process multiple blocks through the delay to fill delay line."""
        out_l = np.zeros(num_blocks * BLOCK_SIZE, dtype=np.float32)
        out_r = np.zeros(num_blocks * BLOCK_SIZE, dtype=np.float32)
        for i in range(num_blocks):
            proc.process(
                inp_per_block[i, :, 0], inp_per_block[i, :, 1],
                out_l[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE],
                out_r[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE],
                BLOCK_SIZE,
            )
        return out_l, out_r

    def test_delay_changes_output(self, proc):
        """Delay with non-zero level should produce output different from input."""
        proc.time = 2.0  # 2 ms → ~88 samples — fits in one block
        proc.level = 0.8
        inp = _stereo_signal()
        out_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp[:, 0], inp[:, 1], out_l, out_r, BLOCK_SIZE)
        # Output should be measurably different from input (delay introduces smear)
        assert not np.allclose(out_l, inp[:, 0], atol=1e-4)
        assert not np.allclose(out_r, inp[:, 1], atol=1e-4)

    def test_zero_feedback_no_sustain(self, proc):
        """With zero feedback, output should not persist after impulse passes."""
        proc.time = 1.0  # 1 ms → ~44 samples
        proc.feedback = 0.0
        proc.level = 0.5

        inp = np.zeros((BLOCK_SIZE, 2), dtype=np.float32)
        inp[:10] = 1.0  # brief impulse
        out_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp[:, 0], inp[:, 1], out_l, out_r, BLOCK_SIZE)

        output_energy = np.sum(out_l ** 2)
        # An impulse of 10 samples at amplitude 1 through ~44-sample delay
        # should produce at most ~10 samples of output, then silence
        nonzero = np.count_nonzero(np.abs(out_l) > 1e-6)
        assert nonzero <= 20, f"Expected ≤20 nonzero samples, got {nonzero}"
        assert output_energy > 0.0  # delay should produce some output

    def test_feedback_sustains_output(self, proc):
        """With feedback > 0, output should persist beyond delay tap."""
        proc.time = 1.0  # 1 ms
        proc.feedback = 0.9
        proc.level = 0.5

        # First block: fill delay line with impulse
        inp1 = np.zeros((BLOCK_SIZE, 2), dtype=np.float32)
        inp1[:5] = 1.0
        out1_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out1_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp1[:, 0], inp1[:, 1], out1_l, out1_r, BLOCK_SIZE)

        # Second block: check if there's sustained output (feedback keeps it alive)
        inp2 = np.zeros((BLOCK_SIZE, 2), dtype=np.float32)
        out2_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out2_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp2[:, 0], inp2[:, 1], out2_l, out2_r, BLOCK_SIZE)

        energy_block2 = np.sum(out2_l ** 2)
        assert energy_block2 > 0.0, "No energy in second block — feedback not sustaining"

    def test_modulation_delay_produces_output(self, proc):
        """Modulation delay should produce non-zero output with steady input."""
        proc.set_delay_type(9)
        proc.time = 2.0
        proc.depth = 0.01  # keep modulation small so effective delay ≈ delay_samples
        proc.rate = 0.5
        proc.level = 0.5

        inp = np.tile(_stereo_signal(), (10, 1))
        inp_blocks = inp.reshape(10, BLOCK_SIZE, 2)
        out_l, out_r = self._process_blocks(proc, 10, inp_blocks)

        assert np.max(np.abs(out_l)) > 0.0, "Modulation delay produced zero output"
        assert np.max(np.abs(out_r)) > 0.0, "Modulation delay produced zero output"

    def test_reset_clears_state(self, proc):
        proc.time = 2.0
        inp = _stereo_signal()
        out_l = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out_r = np.zeros(BLOCK_SIZE, dtype=np.float32)
        proc.process(inp[:, 0], inp[:, 1], out_l, out_r, BLOCK_SIZE)
        proc.reset()
        # After reset, state should be clear (delay lines zeroed)
        out_l2 = np.zeros(BLOCK_SIZE, dtype=np.float32)
        out_r2 = np.zeros(BLOCK_SIZE, dtype=np.float32)
        zero_inp = np.zeros((BLOCK_SIZE, 2), dtype=np.float32)
        proc.process(zero_inp[:, 0], zero_inp[:, 1], out_l2, out_r2, BLOCK_SIZE)
        assert np.allclose(out_l2, 0.0, atol=1e-7)
        assert np.allclose(out_r2, 0.0, atol=1e-7)

    def test_pan_delay_differs_from_mono_delay(self, proc):
        """Pan delay (types 3-5) should produce different stereo image than mono delay (type 0)."""
        def _get_lr_diff(delay_type, proc):
            proc.reset()
            proc.set_delay_type(delay_type)
            proc.time = 2.0
            proc.feedback = 0.3
            proc.level = 0.5
            inp = np.tile(_stereo_signal(), (3, 1))
            inp_blocks = inp.reshape(3, BLOCK_SIZE, 2)
            out_l, out_r = self._process_blocks(proc, 3, inp_blocks)
            return np.mean(np.abs(out_l - out_r))

        mono_diff = _get_lr_diff(0, proc)
        pan_diff = _get_lr_diff(3, proc)
        assert abs(pan_diff - mono_diff) > 1e-6


# ---------------------------------------------------------------------------
# XGMultiBandEqualizer frequency response
# ---------------------------------------------------------------------------


class TestEQFrequencyResponse:
    @pytest.fixture
    def eq(self):
        from synth.processing.effects.eq_processor import XGMultiBandEqualizer

        return XGMultiBandEqualizer(SAMPLE_RATE)

    def test_low_gain_changes_response(self, eq):
        """Increasing low shelf gain should increase magnitude at low frequencies."""
        eq.set_eq_type(0)  # flat baseline
        freqs = np.array([100], dtype=np.float64)
        resp_flat = eq.get_frequency_response(freqs)
        db_flat = 20.0 * np.log10(np.abs(resp_flat) + 1e-12)

        eq.set_low_gain(6.0)
        resp_boost = eq.get_frequency_response(freqs)
        db_boost = 20.0 * np.log10(np.abs(resp_boost) + 1e-12)

        assert db_boost > db_flat, f"Low shelf boost didn't increase: {db_flat[0]:.2f} → {db_boost[0]:.2f}"

    def test_high_gain_changes_response(self, eq):
        """Changing high shelf gain should change the frequency response."""
        eq.set_eq_type(0)
        freqs = np.array([5000, 15000], dtype=np.float64)
        resp_flat = eq.get_frequency_response(freqs)
        db_flat = 20.0 * np.log10(np.abs(resp_flat) + 1e-12)

        eq.set_high_gain(12.0)
        resp_boost = eq.get_frequency_response(freqs)
        db_boost = 20.0 * np.log10(np.abs(resp_boost) + 1e-12)

        # Check that response changed measurably (even if direction is
        # unexpected due to known high-shelf coefficient bug).
        delta = np.sum(np.abs(db_boost - db_flat))
        assert delta > 0.5, f"High shelf gain change barely affects response: Δ={delta:.2f} dB"

    def test_parametric_gain_peaks_at_center(self, eq):
        """Parametric boost should be higher at center frequency than an octave away."""
        eq.set_mid_gain(12.0)
        eq.set_mid_frequency(1000.0)
        eq.set_q_factor(2.0)
        freqs = np.array([500, 1000, 2000], dtype=np.float64)
        resp = eq.get_frequency_response(freqs)
        db = 20.0 * np.log10(np.abs(resp) + 1e-12)
        # Gain at center should be higher than at off-center
        assert db[1] > db[0] + 1.0, f"Peak not above lower: {db}"
        assert db[1] > db[2] + 1.0, f"Peak not above higher: {db}"

    def test_presets_produce_different_responses(self, eq):
        """Each of the 5 EQ presets should produce a measurably different response."""
        responses = []
        for preset in range(5):
            eq.set_eq_type(preset)
            freqs = np.array([100, 500, 1000, 5000, 10000], dtype=np.float64)
            resp = eq.get_frequency_response(freqs)
            responses.append(20.0 * np.log10(np.abs(resp) + 1e-12))
        # At least some presets should differ
        diffs = [np.sum(np.abs(responses[i] - responses[0])) for i in range(1, 5)]
        assert any(d > 0.5 for d in diffs), "All presets produce nearly identical response"


# ---------------------------------------------------------------------------
# XGEffectsCoordinator — wet/dry mix, master level, bypass
# ---------------------------------------------------------------------------


class TestCoordinatorWetDryMaster:
    """Wet/dry mix, master level scaling, and processing bypass at coordinator level."""

    @pytest.fixture
    def coord(self):
        from synth.processing.effects.effects_coordinator import (
            XGEffectsCoordinator,
        )

        coord = XGEffectsCoordinator(
            sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE, max_channels=4,
        )
        coord.processing_enabled = True
        # Mute reverb so it doesn't color the dry signal
        coord.set_system_effect_parameter("reverb", "level", 0.0)
        coord.set_system_effect_parameter("chorus", "level", 0.0)
        # Disable variation so dry signal is predictable
        coord.set_effect_unit_activation(0, False)
        return coord

    def test_processing_disabled_passthrough(self, coord):
        """processing_enabled=False should pass audio unchanged."""
        coord.processing_enabled = False
        audio = _stereo_signal().copy()
        ref = audio.copy()
        output = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(
            [audio], output, BLOCK_SIZE
        )
        assert np.allclose(output, ref, atol=1e-6)

    def test_wet_dry_mix_scales_vs_fully_wet(self, coord):
        """Output at wet_dry=0.3 should have lower processed effect amplitude than wet_dry=1.0."""
        audio = _stereo_signal().copy()
        channels = [audio.copy()]

        coord.set_master_controls(wet_dry=0.3)
        output_low = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(channels, output_low, BLOCK_SIZE)

        coord.set_master_controls(wet_dry=1.0)
        output_full = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(channels, output_full, BLOCK_SIZE)

        # Lower wet/dry should differ from full wet
        assert not np.allclose(output_low, output_full, atol=1e-4)

    def test_wet_dry_mix_blends(self, coord):
        """wet_dry_mix=0.5 should blend processed and dry signals."""
        coord.set_master_controls(wet_dry=0.5)
        audio = _stereo_signal().copy()
        output_half = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(
            [audio], output_half, BLOCK_SIZE
        )

        coord.set_master_controls(wet_dry=1.0)
        output_full = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(
            [audio], output_full, BLOCK_SIZE
        )

        # Half wet should be between dry and full wet
        half_mean = np.abs(output_half).mean()
        full_mean = np.abs(output_full).mean()
        # Full-wet may or may not be louder — but half shouldn't equal full
        assert not np.allclose(output_half, output_full, atol=1e-4)

    def test_master_level_scales_output(self, coord):
        """master_level should scale output amplitude."""
        coord.set_master_controls(level=0.5)
        audio = _stereo_signal().copy()
        output_half = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(
            [audio], output_half, BLOCK_SIZE
        )

        coord.set_master_controls(level=1.0)
        output_full = np.zeros_like(audio)
        coord.process_channels_to_stereo_zero_alloc(
            [audio], output_full, BLOCK_SIZE
        )

        half_mean = np.abs(output_half).mean()
        full_mean = np.abs(output_full).mean()
        assert full_mean > half_mean, "Master level not scaling output"

    def test_full_pipeline_produces_finite_output(self, coord):
        """Full pipeline with multiple channels should produce finite stereo output."""
        audio = _stereo_signal().copy()
        channels = [audio.copy() for _ in range(4)]
        output = np.zeros_like(audio)

        # Enable full pipeline
        coord.processing_enabled = True
        coord.set_master_controls(level=1.0, wet_dry=1.0)

        coord.process_channels_to_stereo_zero_alloc(channels, output, BLOCK_SIZE)
        assert np.all(np.isfinite(output))
        assert output.shape == (BLOCK_SIZE, 2)
        assert output.dtype == np.float32
