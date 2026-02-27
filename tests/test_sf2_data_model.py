"""
Test suite for SF2 data model classes.

Tests SF2Zone, SF2Instrument, SF2Preset, SF2Sample, and RangeTree.
"""
from __future__ import annotations

import pytest
from synth.sf2 import sf2_data_model


class TestSF2Zone:
    """Tests for SF2Zone class."""

    def test_zone_creation(self):
        """Test zone creation with default values."""
        zone = sf2_data_model.SF2Zone("preset")
        assert zone.level_type == "preset"
        assert zone.sample_id == -1
        assert zone.key_range == (0, 127)
        assert zone.velocity_range == (0, 127)

    def test_add_generator_sample_id(self):
        """Test adding sampleID generator at index 50."""
        zone = sf2_data_model.SF2Zone("instrument")
        zone.add_generator(50, 42)  # sampleID at gen 50
        assert zone.sample_id == 42

    def test_add_generator_instrument_index(self):
        """Test adding instrument generator."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.add_generator(41, 5)  # instrument at gen 41
        assert zone.instrument_index == 5

    def test_add_generator_key_range(self):
        """Test adding keyRange generator."""
        zone = sf2_data_model.SF2Zone("preset")
        # Key range: low=36, high=96 (encoded as 36 | (96 << 8))
        encoded = 36 | (96 << 8)
        zone.add_generator(42, encoded)
        assert zone.key_range == (36, 96)

    def test_add_generator_vel_range(self):
        """Test adding velRange generator."""
        zone = sf2_data_model.SF2Zone("instrument")
        # Velocity range: low=64, high=127 (encoded as 64 | (127 << 8))
        encoded = 64 | (127 << 8)
        zone.add_generator(43, encoded)
        assert zone.velocity_range == (64, 127)

    def test_add_generator_exclusive_class(self):
        """Test adding exclusiveClass generator at index 53."""
        zone = sf2_data_model.SF2Zone("instrument")
        zone.add_generator(53, 1)  # exclusiveClass
        assert zone.get_generator_value(53) == 1

    def test_matches_note_velocity_in_range(self):
        """Test zone matching when note/velocity in range."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (36, 96)
        zone.velocity_range = (64, 127)

        assert zone.matches_note_velocity(60, 100) is True
        assert zone.matches_note_velocity(36, 64) is True
        assert zone.matches_note_velocity(96, 127) is True

    def test_matches_note_velocity_out_of_range(self):
        """Test zone matching when note/velocity out of range."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (36, 96)
        zone.velocity_range = (64, 127)

        assert zone.matches_note_velocity(20, 100) is False  # key too low
        assert zone.matches_note_velocity(60, 10) is False  # vel too low

    def test_matches_note_velocity_boundary(self):
        """Test zone matching at boundaries."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (36, 96)
        zone.velocity_range = (64, 127)

        assert zone.matches_note_velocity(35, 100) is False  # just below
        assert zone.matches_note_velocity(97, 100) is False  # just above

    def test_zone_finalize_preset_global(self):
        """Test preset global zone detection."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.instrument_index = -1
        zone.finalize()
        assert zone.is_global is True

    def test_zone_finalize_instrument_global(self):
        """Test instrument global zone detection."""
        zone = sf2_data_model.SF2Zone("instrument")
        zone.sample_id = -1
        zone.key_range = (0, 127)
        zone.velocity_range = (0, 127)
        zone.finalize()
        assert zone.is_global is True

    def test_zone_finalize_clamp_ranges(self):
        """Test zone finalize clamps invalid ranges."""
        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (100, 50)  # Invalid: low > high
        zone.velocity_range = (200, 10)  # Invalid
        zone.finalize()
        assert zone.key_range == (0, 127)
        assert zone.velocity_range == (0, 127)


class TestSF2Instrument:
    """Tests for SF2Instrument class."""

    def test_instrument_creation(self):
        """Test instrument creation."""
        inst = sf2_data_model.SF2Instrument(0, "Piano")
        assert inst.index == 0
        assert inst.name == "Piano"
        assert len(inst.zones) == 0

    def test_add_zone_non_global(self):
        """Test adding non-global zone."""
        inst = sf2_data_model.SF2Instrument(0, "Piano")
        zone = sf2_data_model.SF2Zone("instrument")
        zone.sample_id = 0
        inst.add_zone(zone)
        assert len(inst.zones) == 1
        assert inst.global_zone is None

    def test_add_zone_global(self):
        """Test adding global zone."""
        inst = sf2_data_model.SF2Instrument(0, "Piano")
        zone = sf2_data_model.SF2Zone("instrument")
        zone.sample_id = -1
        zone.key_range = (0, 127)
        zone.velocity_range = (0, 127)
        zone.finalize()
        inst.add_zone(zone)
        assert inst.global_zone is not None
        assert len(inst.zones) == 0

    def test_get_matching_zones_with_global(self):
        """Test get_matching_zones includes global zone."""
        inst = sf2_data_model.SF2Instrument(0, "Piano")

        # Add global zone
        global_zone = sf2_data_model.SF2Zone("instrument")
        global_zone.sample_id = -1
        global_zone.key_range = (0, 127)
        global_zone.velocity_range = (0, 127)
        global_zone.finalize()
        inst.add_zone(global_zone)

        # Add specific zone
        specific_zone = sf2_data_model.SF2Zone("instrument")
        specific_zone.sample_id = 5
        specific_zone.key_range = (48, 72)
        specific_zone.velocity_range = (0, 127)
        specific_zone.finalize()
        inst.add_zone(specific_zone)

        # Should get both global and specific
        zones = inst.get_matching_zones(60, 100)
        assert len(zones) == 2

    def test_has_samples(self):
        """Test has_samples detection."""
        inst = sf2_data_model.SF2Instrument(0, "Test")

        assert inst.has_samples() is False

        zone = sf2_data_model.SF2Zone("instrument")
        zone.sample_id = 0
        inst.add_zone(zone)

        assert inst.has_samples() is True

    def test_get_sample_ids(self):
        """Test get_sample_ids."""
        inst = sf2_data_model.SF2Instrument(0, "Test")

        zone1 = sf2_data_model.SF2Zone("instrument")
        zone1.sample_id = 0
        inst.add_zone(zone1)

        zone2 = sf2_data_model.SF2Zone("instrument")
        zone2.sample_id = 3
        inst.add_zone(zone2)

        sample_ids = inst.get_sample_ids()
        assert 0 in sample_ids
        assert 3 in sample_ids


class TestSF2Preset:
    """Tests for SF2Preset class."""

    def test_preset_creation(self):
        """Test preset creation."""
        preset = sf2_data_model.SF2Preset(0, 0, "Grand Piano")
        assert preset.bank == 0
        assert preset.program == 0
        assert preset.name == "Grand Piano"

    def test_add_zone_instrument(self):
        """Test adding zone with instrument link."""
        preset = sf2_data_model.SF2Preset(0, 0, "Test")
        zone = sf2_data_model.SF2Zone("preset")
        zone.instrument_index = 5
        preset.add_zone(zone)

        instruments = preset.get_instruments()
        assert 5 in instruments
        assert preset.has_instruments() is True


class TestSF2Sample:
    """Tests for SF2Sample class."""

    def test_sample_creation(self):
        """Test sample creation from header data."""
        header = {
            "name": "Piano C4",
            "start": 0,
            "end": 44100,
            "start_loop": 22000,
            "end_loop": 44000,
            "sample_rate": 44100,
            "original_pitch": 60,
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 1,  # mono
        }
        sample = sf2_data_model.SF2Sample(header)

        assert sample.name == "Piano C4"
        assert sample.start == 0
        assert sample.end == 44100
        assert sample.sample_rate == 44100
        assert sample.original_pitch == 60

    def test_sample_derived_properties(self):
        """Test derived sample properties."""
        header = {
            "name": "Test",
            "start": 0,
            "end": 1000,
            "start_loop": 800,
            "end_loop": 950,
            "sample_rate": 44100,
            "original_pitch": 60,
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 1,
        }
        sample = sf2_data_model.SF2Sample(header)

        assert sample.length == 1000
        assert sample.loop_length == 150
        assert sample.bit_depth == 16

    def test_sample_24bit_detection(self):
        """Test 24-bit sample detection."""
        header = {
            "name": "Test24",
            "start": 0,
            "end": 1000,
            "start_loop": 0,
            "end_loop": 0,
            "sample_rate": 48000,
            "original_pitch": 60,
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 0x8001,  # 24-bit mono flag
        }
        sample = sf2_data_model.SF2Sample(header)

        assert sample.is_24bit is True
        assert sample.bit_depth == 24

    def test_sample_stereo_detection(self):
        """Test stereo sample detection."""
        header = {
            "name": "TestStereo",
            "start": 0,
            "end": 1000,
            "start_loop": 0,
            "end_loop": 0,
            "sample_rate": 44100,
            "original_pitch": 60,
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 2,  # right channel
        }
        sample = sf2_data_model.SF2Sample(header)

        assert sample.is_stereo is True

    def test_get_root_frequency(self):
        """Test root frequency calculation."""
        header = {
            "name": "Test",
            "start": 0,
            "end": 1000,
            "start_loop": 0,
            "end_loop": 0,
            "sample_rate": 44100,
            "original_pitch": 69,  # A4
            "pitch_correction": 0,
            "sample_link": 0,
            "sample_type": 1,
        }
        sample = sf2_data_model.SF2Sample(header)

        assert abs(sample.get_root_frequency() - 440.0) < 0.1


class TestRangeTree:
    """Tests for RangeTree class."""

    def test_range_tree_insertion(self):
        """Test zone insertion into range tree."""
        tree = sf2_data_model.RangeTree()

        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.velocity_range = (0, 127)

        tree.add_zone(zone)
        assert tree.zone_count == 1

    def test_range_tree_query(self):
        """Test zone query in range tree."""
        tree = sf2_data_model.RangeTree()

        # Add zone for middle range
        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (48, 72)
        zone.velocity_range = (64, 127)
        tree.add_zone(zone)

        # Query should find it
        results = tree.find_matching_zones(60, 100)
        assert len(results) == 1

        # Query outside range should not find it
        results = tree.find_matching_zones(20, 100)
        assert len(results) == 0

    def test_range_tree_multiple_zones(self):
        """Test multiple zones in range tree."""
        tree = sf2_data_model.RangeTree()

        zones = [
            (0, 127, 0, 127),  # Full range
            (48, 60, 0, 127),  # Low keys
            (72, 96, 0, 127),  # High keys
        ]

        for key_lo, key_hi, vel_lo, vel_hi in zones:
            zone = sf2_data_model.SF2Zone("preset")
            zone.key_range = (key_lo, key_hi)
            zone.velocity_range = (vel_lo, vel_hi)
            tree.add_zone(zone)

        # Middle note should match 2 zones
        results = tree.find_matching_zones(55, 100)
        assert len(results) == 2

    def test_range_tree_clear(self):
        """Test clearing range tree."""
        tree = sf2_data_model.RangeTree()

        zone = sf2_data_model.SF2Zone("preset")
        zone.key_range = (48, 72)
        tree.add_zone(zone)

        tree.clear()
        assert tree.zone_count == 0
        assert tree.root is None

    def test_range_tree_avl_balance(self):
        """Test AVL tree remains balanced."""
        tree = sf2_data_model.RangeTree()

        # Add zones in descending order (worst case for unbalanced)
        for i in range(10, 0, -1):
            zone = sf2_data_model.SF2Zone("preset")
            zone.key_range = (i * 5, i * 5 + 10)
            tree.add_zone(zone)

        stats = tree.get_stats()
        assert stats["is_balanced"] is True
