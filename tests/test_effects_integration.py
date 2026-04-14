"""
Effects Integration Tests

Tests for reverb types, chorus types, insertion effects,
and effects bypass functionality in the XG synthesizer.
"""

from __future__ import annotations

import pytest
import numpy as np

from tests.utils.audio_utils import calculate_rms


class TestEffectsIntegration:
    """Test effects processing integration."""

    @pytest.mark.integration
    def test_reverb_types(self, sample_rate, block_size):
        """Test different reverb types."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Test different reverb types
        for reverb_type in [1, 9, 17, 25]:
            reverb.set_parameter("reverb_type", reverb_type)

            # Create test signal
            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5

            # Apply reverb
            reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            # Should produce valid output
            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_chorus_types(self, sample_rate, block_size):
        """Test different chorus types."""
        from synth.processing.effects.system import XGSystemChorusProcessor

        chorus = XGSystemChorusProcessor(sample_rate=sample_rate)

        # Test different chorus types
        for chorus_type in range(6):
            chorus.set_chorus_type(chorus_type)

            # Create test signal
            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5

            # Apply chorus
            chorus.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            # Should produce valid output
            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_insertion_effects(self, sample_rate, block_size):
        """Test insertion effects processing."""
        from synth.processing.effects.insertion import ProductionXGInsertionEffectsProcessor

        insertion = ProductionXGInsertionEffectsProcessor(sample_rate=sample_rate)

        # Test different effect types
        for effect_type in [0, 2, 6, 15, 16]:
            insertion.set_insertion_effect_type(0, effect_type)

            # Create test signal
            signal = np.random.randn(block_size).astype(np.float32) * 0.5

            # Process through insertion effect
            for i in range(block_size):
                signal[i] = insertion._apply_single_effect_to_samples(
                    np.array([signal[i]]),
                    1,
                    effect_type,
                    {},
                )[0]

            # Should produce valid output
            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_effects_bypass(self, sample_rate, block_size):
        """Test effects bypass functionality."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Create test signal
        signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
        original = signal.copy()

        # Disable reverb
        reverb.set_parameter("enabled", False)

        # Apply reverb (should be bypassed)
        reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

        # Signal should be unchanged when bypassed
        assert np.allclose(signal, original)

    @pytest.mark.integration
    def test_effects_parameter_ranges(self, sample_rate, block_size):
        """Test effects parameter ranges."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Test parameter ranges
        reverb.set_parameter("time", 0.5)
        reverb.set_parameter("level", 0.6)
        reverb.set_parameter("pre_delay", 0.02)
        reverb.set_parameter("hf_damping", 0.5)
        reverb.set_parameter("density", 0.8)

        # Parameters should be accepted
        assert reverb.params["time"] == 0.5
        assert reverb.params["level"] == 0.6

    @pytest.mark.integration
    def test_effects_chain_processing(self, sample_rate, block_size):
        """Test complete effects chain processing."""
        from synth.processing.effects.system import XGSystemEffectsProcessor

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

        # Should produce valid output
        assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_reverb_send_levels(self, sample_rate, block_size):
        """Test reverb send level control."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Test different send levels
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            reverb.set_parameter("level", level)

            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
            reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_chorus_send_levels(self, sample_rate, block_size):
        """Test chorus send level control."""
        from synth.processing.effects.system import XGSystemChorusProcessor

        chorus = XGSystemChorusProcessor(sample_rate=sample_rate)

        # Test different send levels
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            chorus.set_parameter("level", level)

            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
            chorus.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_reverb_time_modulation(self, sample_rate, block_size):
        """Test reverb time modulation."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Test different reverb times
        for time in [0.5, 1.0, 2.0, 4.0]:
            reverb.set_parameter("time", time)

            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
            reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_chorus_rate_modulation(self, sample_rate, block_size):
        """Test chorus rate modulation."""
        from synth.processing.effects.system import XGSystemChorusProcessor

        chorus = XGSystemChorusProcessor(sample_rate=sample_rate)

        # Test different chorus rates
        for rate in [0.5, 1.0, 2.0, 5.0]:
            chorus.set_parameter("rate", rate)

            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
            chorus.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_effects_stereo_processing(self, sample_rate, block_size):
        """Test effects stereo processing."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Create stereo signal
        signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5

        # Apply reverb
        reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

        # Should maintain stereo
        assert signal.shape == (block_size, 2)
        assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_effects_mono_processing(self, sample_rate, block_size):
        """Test effects mono processing."""
        from synth.processing.effects.insertion import ProductionXGInsertionEffectsProcessor

        insertion = ProductionXGInsertionEffectsProcessor(sample_rate=sample_rate)

        # Create mono signal
        signal = np.random.randn(block_size).astype(np.float32) * 0.5

        # Process through insertion effect
        insertion.set_insertion_effect_type(0, 0)  # Thru

        for i in range(block_size):
            signal[i] = insertion._apply_single_effect_to_samples(
                np.array([signal[i]]),
                1,
                0,
                {},
            )[0]

        assert np.all(np.isfinite(signal))

    @pytest.mark.integration
    def test_effects_wet_dry_mix(self, sample_rate, block_size):
        """Test effects wet/dry mix control."""
        from synth.processing.effects.system import XGSystemReverbProcessor

        reverb = XGSystemReverbProcessor(sample_rate=sample_rate)

        # Test different wet/dry mixes
        for level in [0.0, 0.5, 1.0]:
            reverb.set_parameter("level", level)

            signal = np.random.randn(block_size, 2).astype(np.float32) * 0.5
            reverb.apply_system_effects_to_mix_zero_alloc(signal, block_size)

            assert np.all(np.isfinite(signal))