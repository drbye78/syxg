"""
Test suite for SF2 constants and conversion functions.

Tests SF2_GENERATORS, SF2_MODULATOR_SOURCES, SF2_MODULATOR_DESTINATIONS,
and all conversion functions for specification compliance.
"""

import pytest
import math
from synth.sf2 import sf2_constants


class TestSF2Generators:
    """Tests for SF2 generator definitions."""

    def test_all_generator_indices_valid(self):
        """Test all generator indices are in valid range 0-65."""
        for gen_id, gen_info in sf2_constants.SF2_GENERATORS.items():
            assert 0 <= gen_id <= 65, f"Generator {gen_id} out of range"

    def test_generator_has_required_fields(self):
        """Test each generator has name, default, and range."""
        for gen_id, gen_info in sf2_constants.SF2_GENERATORS.items():
            assert "name" in gen_info, f"Generator {gen_id} missing 'name'"
            assert "default" in gen_info, f"Generator {gen_id} missing 'default'"
            assert "range" in gen_info, f"Generator {gen_id} missing 'range'"
            assert len(gen_info["range"]) == 2, (
                f"Generator {gen_id} range must be tuple"
            )

    def test_sampleid_at_index_50(self):
        """Test sampleID generator is at correct index 50."""
        assert 50 in sf2_constants.SF2_GENERATORS
        assert sf2_constants.SF2_GENERATORS[50]["name"] == "sampleID"

    def test_exclusiveclass_at_index_53(self):
        """Test exclusiveClass generator is at correct index 53."""
        assert 53 in sf2_constants.SF2_GENERATORS
        assert sf2_constants.SF2_GENERATORS[53]["name"] == "exclusiveClass"

    def test_loop_generators_complete(self):
        """Test loop generators 44-47 are defined correctly."""
        assert 44 in sf2_constants.SF2_GENERATORS  # startloopAddrsCoarse
        assert 45 in sf2_constants.SF2_GENERATORS  # startloopAddrsFine
        assert 46 in sf2_constants.SF2_GENERATORS  # endloopAddrsCoarse
        assert 47 in sf2_constants.SF2_GENERATORS  # endloopAddrsFine

    def test_envelope_generators_complete(self):
        """Test all envelope generators are defined."""
        # Volume envelope
        assert 8 in sf2_constants.SF2_GENERATORS  # volEnvDelay
        assert 9 in sf2_constants.SF2_GENERATORS  # volEnvAttack
        assert 10 in sf2_constants.SF2_GENERATORS  # volEnvHold
        assert 11 in sf2_constants.SF2_GENERATORS  # volEnvDecay
        assert 12 in sf2_constants.SF2_GENERATORS  # volEnvSustain
        assert 13 in sf2_constants.SF2_GENERATORS  # volEnvRelease

        # Modulation envelope
        assert 14 in sf2_constants.SF2_GENERATORS  # modEnvDelay
        assert 15 in sf2_constants.SF2_GENERATORS  # modEnvAttack
        assert 16 in sf2_constants.SF2_GENERATORS  # modEnvHold
        assert 17 in sf2_constants.SF2_GENERATORS  # modEnvDecay
        assert 18 in sf2_constants.SF2_GENERATORS  # modEnvSustain
        assert 19 in sf2_constants.SF2_GENERATORS  # modEnvRelease


class TestConversionFunctions:
    """Tests for SF2 conversion functions."""

    def test_frequency_to_cents_440_to_a4(self):
        """Test frequency_to_cents returns 0 for A4 (440Hz)."""
        result = sf2_constants.frequency_to_cents(440.0, 440.0)
        assert result == 0

    def test_frequency_to_cents_880_octave(self):
        """Test frequency_to_cents returns 1200 for octave up (880Hz)."""
        result = sf2_constants.frequency_to_cents(880.0, 440.0)
        assert result == 1200

    def test_frequency_to_cents_220_half_octave(self):
        """Test frequency_to_cents returns -1200 for octave down (220Hz)."""
        result = sf2_constants.frequency_to_cents(220.0, 440.0)
        assert result == -1200

    def test_frequency_to_cents_440_semitone(self):
        """Test frequency_to_cents for semitone (A4# = 466.16Hz)."""
        result = sf2_constants.frequency_to_cents(466.16, 440.0)
        assert abs(result - 100) < 5  # Approximately 100 cents

    def test_frequency_to_cents_invalid_frequency(self):
        """Test frequency_to_cents handles invalid frequency."""
        result = sf2_constants.frequency_to_cents(0, 440.0)
        assert result == -12000

    def test_cents_to_frequency_a4(self):
        """Test cents_to_frequency returns base_freq for 0 cents."""
        result = sf2_constants.cents_to_frequency(0)
        assert result == 1.0  # Multiplier of 1.0

    def test_cents_to_frequency_octave(self):
        """Test cents_to_frequency for octave (1200 cents)."""
        result = sf2_constants.cents_to_frequency(1200)
        assert abs(result - 2.0) < 0.001  # Multiplier of 2.0

    def test_timecents_to_seconds_instant(self):
        """Test timecents_to_seconds for instant (-12000)."""
        result = sf2_constants.timecents_to_seconds(-12000)
        assert result == 0.0

    def test_timecents_to_seconds_one_second(self):
        """Test timecents_to_seconds for 1 second."""
        result = sf2_constants.timecents_to_seconds(1200)  # 1 octave = 2x time
        assert abs(result - 2.0) < 0.001

    def test_roundtrip_frequency_cents(self):
        """Test frequency -> cents -> frequency roundtrip."""
        original_freq = 440.0
        cents = sf2_constants.frequency_to_cents(original_freq, 440.0)
        result = sf2_constants.cents_to_frequency(cents) * 440.0
        assert abs(result - original_freq) < 0.01


class TestSF2ModulatorConstants:
    """Tests for SF2 modulator constants."""

    def test_modulator_sources_complete(self):
        """Test key modulator sources are defined."""
        assert 0 in sf2_constants.SF2_MODULATOR_SOURCES  # none
        assert 2 in sf2_constants.SF2_MODULATOR_SOURCES  # velocity
        assert 3 in sf2_constants.SF2_MODULATOR_SOURCES  # key
        assert 10 in sf2_constants.SF2_MODULATOR_SOURCES  # pan
        assert 14 in sf2_constants.SF2_MODULATOR_SOURCES  # pitch_wheel

    def test_modulator_sources_cc_complete(self):
        """Test CC sources 0-127 are defined."""
        for cc in range(128):
            assert cc in sf2_constants.SF2_MODULATOR_SOURCES

    def test_modulator_destinations_complete(self):
        """Test key modulator destinations are defined."""
        assert 7 in sf2_constants.SF2_MODULATOR_DESTINATIONS  # volume
        assert 21 in sf2_constants.SF2_MODULATOR_DESTINATIONS  # modEnvAttack
        assert 29 in sf2_constants.SF2_MODULATOR_DESTINATIONS  # filterFc

    def test_modulator_transforms_complete(self):
        """Test all transform types are defined."""
        assert 0 in sf2_constants.SF2_MODULATOR_TRANSFORMS  # linear
        assert 1 in sf2_constants.SF2_MODULATOR_TRANSFORMS  # absolute
        assert 2 in sf2_constants.SF2_MODULATOR_TRANSFORMS  # bipolar_to_unipolar


class TestSF2SampleTypes:
    """Tests for SF2 sample type definitions."""

    def test_sample_types_defined(self):
        """Test all sample types are defined."""
        assert sf2_constants.SF2_SAMPLE_TYPES
        assert 0x0001 in sf2_constants.SF2_SAMPLE_TYPES  # mono
        assert 0x0002 in sf2_constants.SF2_SAMPLE_TYPES  # right
        assert 0x0004 in sf2_constants.SF2_SAMPLE_TYPES  # left

    def test_sample_types_have_required_fields(self):
        """Test each sample type has required fields."""
        for type_id, type_info in sf2_constants.SF2_SAMPLE_TYPES.items():
            assert "name" in type_info
            assert "channels" in type_info
            assert "bit_depth" in type_info


class TestSF2ConstantsValues:
    """Tests for SF2 constant values."""

    def test_header_sizes(self):
        """Test header size constants."""
        assert sf2_constants.SF2_HEADER_SIZE == 8
        assert sf2_constants.SF2_RIFF_HEADER_SIZE == 12

    def test_envelope_defaults(self):
        """Test envelope default values."""
        defaults = sf2_constants.SF2_ENVELOPE_DEFAULTS
        assert defaults["delay"] == -12000
        assert defaults["attack"] == -12000
        assert defaults["hold"] == -12000
        assert defaults["decay"] == -12000
        assert defaults["sustain"] == 0
        assert defaults["release"] == -12000

    def test_loop_modes(self):
        """Test loop mode definitions."""
        assert 0 in sf2_constants.SF2_LOOP_MODES
        assert 1 in sf2_constants.SF2_LOOP_MODES
        assert sf2_constants.SF2_LOOP_MODES[0] == "no_loop"
        assert sf2_constants.SF2_LOOP_MODES[1] == "forward_loop"
