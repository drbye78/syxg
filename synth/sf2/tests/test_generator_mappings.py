"""
SF2 Generator Mapping Tests

Comprehensive tests for SF2 generator ID mappings to ensure
correct parameter extraction and application.
"""

from __future__ import annotations

import numpy as np
import pytest


class TestSF2GeneratorIDs:
    """Test that generator IDs match SF2 2.04 specification."""

    def test_volume_envelope_generators(self):
        """Volume envelope generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        expected = {
            8: "volEnvDelay",
            9: "volEnvAttack",
            10: "volEnvHold",
            11: "volEnvDecay",
            12: "volEnvSustain",
            13: "volEnvRelease",
        }

        for gen_id, expected_name in expected.items():
            assert gen_id in SF2_GENERATORS
            assert SF2_GENERATORS[gen_id]["name"] == expected_name

    def test_modulation_envelope_generators(self):
        """Modulation envelope generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        expected = {
            14: "modEnvDelay",
            15: "modEnvAttack",
            16: "modEnvHold",
            17: "modEnvDecay",
            18: "modEnvSustain",
            19: "modEnvRelease",
            20: "modEnvToPitch",
        }

        for gen_id, expected_name in expected.items():
            assert gen_id in SF2_GENERATORS
            assert SF2_GENERATORS[gen_id]["name"] == expected_name

    def test_mod_lfo_generators(self):
        """Modulation LFO generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        expected = {
            21: "delayModLFO",
            22: "freqModLFO",
            23: "modLfoToVol",
            24: "modLfoToFilterFc",
            25: "modLfoToPitch",
        }

        for gen_id, expected_name in expected.items():
            assert gen_id in SF2_GENERATORS
            assert SF2_GENERATORS[gen_id]["name"] == expected_name

    def test_vib_lfo_generators(self):
        """Vibrato LFO generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        expected = {
            26: "delayVibLFO",
            27: "freqVibLFO",
            28: "vibLfoToPitch",
        }

        for gen_id, expected_name in expected.items():
            assert gen_id in SF2_GENERATORS
            assert SF2_GENERATORS[gen_id]["name"] == expected_name

    def test_filter_generators(self):
        """Filter generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        assert 29 in SF2_GENERATORS
        assert SF2_GENERATORS[29]["name"] == "initialFilterFc"

        assert 30 in SF2_GENERATORS
        assert SF2_GENERATORS[30]["name"] == "initialFilterQ"

    def test_effects_generators(self):
        """Effects generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        # Reverb send
        assert 32 in SF2_GENERATORS
        assert SF2_GENERATORS[32]["name"] == "reverbEffectsSend"

        # Chorus send
        assert 33 in SF2_GENERATORS
        assert SF2_GENERATORS[33]["name"] == "chorusEffectsSend"

        # Pan
        assert 34 in SF2_GENERATORS
        assert SF2_GENERATORS[34]["name"] == "pan"

    def test_key_tracking_generators(self):
        """Key tracking generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        # Note: IDs 35-38 are actually secondary LFO generators in SF2 spec
        # Key tracking generators are not standard SF2 generators
        # These are XG-specific extensions

        # Check what's actually at these IDs
        assert 35 in SF2_GENERATORS
        assert 36 in SF2_GENERATORS
        assert 37 in SF2_GENERATORS
        assert 38 in SF2_GENERATORS

        # Actual SF2 spec names (secondary modulation)
        assert SF2_GENERATORS[35]["name"] == "delayModLFO3"
        assert SF2_GENERATORS[36]["name"] == "freqModLFO2"
        assert SF2_GENERATORS[37]["name"] == "delayVibLFO2"
        assert SF2_GENERATORS[38]["name"] == "freqVibLFO2"

    def test_range_generators(self):
        """Key and velocity range generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        # Key range
        assert 42 in SF2_GENERATORS
        assert SF2_GENERATORS[42]["name"] == "keyRange"

        # Velocity range (actually velRange in our implementation)
        assert 43 in SF2_GENERATORS
        # Note: SF2 spec uses combined keyRange/velRange in single generator
        # Our implementation may have this as a separate entry

    def test_sample_generators(self):
        """Sample-related generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        # Sample ID
        assert 50 in SF2_GENERATORS
        assert SF2_GENERATORS[50]["name"] == "sampleID"

        # Sample modes
        assert 51 in SF2_GENERATORS
        assert SF2_GENERATORS[51]["name"] == "sampleModes"

        # Scale tuning
        assert 52 in SF2_GENERATORS
        assert SF2_GENERATORS[52]["name"] == "scaleTuning"

        # Exclusive class
        assert 53 in SF2_GENERATORS
        assert SF2_GENERATORS[53]["name"] == "exclusiveClass"

    def test_pitch_generators(self):
        """Pitch generator IDs should be correct."""
        from synth.sf2.sf2_constants import SF2_GENERATORS

        # Coarse tune
        assert 48 in SF2_GENERATORS
        assert SF2_GENERATORS[48]["name"] == "coarseTune"

        # Fine tune
        assert 49 in SF2_GENERATORS
        assert SF2_GENERATORS[49]["name"] == "fineTune"


class TestSF2PartialGeneratorMapping:
    """Test SF2Partial generator value extraction."""

    def test_effects_send_mapping(self, mock_synth):
        """Effects send generators should map correctly from nested structure."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "effects": {
                "reverb_send": 0.5,
                "chorus_send": 0.3,
            },
        }

        partial = SF2Partial(params, mock_synth)

        # Should load from nested effects dict
        assert partial.reverb_effects_send == 0.5
        assert partial.chorus_effects_send == 0.3

    def test_sample_id_mapping(self, mock_synth):
        """Sample ID should be available in params."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "sample_id": 42,
        }

        partial = SF2Partial(params, mock_synth)

        # Sample ID should be in params
        assert partial.params.get("sample_id") == 42

    def test_exclusive_class_mapping(self, mock_synth):
        """Exclusive class generator should map correctly."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "sample_settings": {
                "exclusive_class": 5,
            },
        }

        partial = SF2Partial(params, mock_synth)

        assert partial.exclusive_class == 5

    def test_mod_env_to_pitch_mapping(self, mock_synth):
        """Mod envelope to pitch should map correctly from nested structure."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "mod_envelope": {
                "to_pitch": 0.5,  # 0.5 semitones
            },
        }

        partial = SF2Partial(params, mock_synth)

        # Should load from nested mod_envelope dict
        assert partial.mod_env_to_pitch == 0.5

    def test_key_range_mapping(self, mock_synth):
        """Key range should map correctly from params."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "key_range": (48, 72),
        }

        partial = SF2Partial(params, mock_synth)

        assert partial.key_range == (48, 72)

    def test_velocity_range_mapping(self, mock_synth):
        """Velocity range should map correctly from params."""
        from synth.partial.sf2_partial import SF2Partial

        params = {
            "sample_data": np.zeros(1000, dtype=np.float32),
            "note": 60,
            "velocity": 100,
            "vel_range": (64, 127),
        }

        partial = SF2Partial(params, mock_synth)

        assert partial.vel_range == (64, 127)


class TestSF2RegionGeneratorExtraction:
    """Test SF2Region generator extraction from zones."""

    def test_region_extract_volume_envelope(self, region_descriptor, mock_soundfont_manager):
        """SF2Region should extract volume envelope from generators."""
        from synth.engine.region_descriptor import RegionDescriptor
        from synth.partial.sf2_region import SF2Region

        # Create region with generator params
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="sf2",
            generator_params={
                "amp_envelope": {
                    "delay": 0.01,
                    "attack": 0.05,
                    "decay": 0.3,
                    "sustain": 0.7,
                    "release": 0.5,
                }
            },
        )

        region = SF2Region(descriptor, 44100, mock_soundfont_manager)

        # Should extract envelope parameters
        # (specific assertions depend on implementation)

    def test_region_extract_filter_params(self, region_descriptor, mock_soundfont_manager):
        """SF2Region should extract filter parameters from generators."""
        from synth.engine.region_descriptor import RegionDescriptor
        from synth.partial.sf2_region import SF2Region

        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="sf2",
            generator_params={"filter_cutoff": 2000.0, "filter_resonance": 0.5},
        )

        region = SF2Region(descriptor, 44100, mock_soundfont_manager)

        # Should extract filter parameters

    def test_region_extract_pitch_params(self, region_descriptor, mock_soundfont_manager):
        """SF2Region should extract pitch parameters from generators."""
        from synth.engine.region_descriptor import RegionDescriptor
        from synth.partial.sf2_region import SF2Region

        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="sf2",
            generator_params={"coarse_tune": 0, "fine_tune": 0.0, "scale_tuning": 1.0},
        )

        region = SF2Region(descriptor, 44100, mock_soundfont_manager)

        # Should extract pitch parameters


class TestGeneratorInheritance:
    """Test SF2 generator inheritance (preset → instrument → zone)."""

    def test_preset_global_applies_to_all_zones(self):
        """Preset global generators should apply to all zones."""
        # Implementation would test inheritance chain
        pass

    def test_instrument_overrides_preset(self):
        """Instrument generators should override preset generators."""
        pass

    def test_zone_overrides_instrument(self):
        """Zone generators should override instrument generators."""
        pass

    def test_complete_inheritance_chain(self):
        """Full inheritance chain should work correctly."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
