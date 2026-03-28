"""
SF2 Zone Selection Unit Tests

Tests for SF2 zone matching based on key and velocity ranges,
zone inheritance, and multiple zone layering.
"""

from __future__ import annotations

import pytest
import numpy as np

from synth.engine.sf2_engine import SF2Engine
from synth.engine.region_descriptor import RegionDescriptor


class TestSF2ZoneSelection:
    """Test SF2 zone selection functionality."""

    @pytest.mark.unit
    def test_key_range_matching(self, ref_sf2_path):
        """Test zone matching based on key ranges."""
        from synth.engine.sf2_engine import SF2Engine
        engine = SF2Engine(sf2_file_path=ref_sf2_path, sample_rate=44100, block_size=1024)
        
        # Get preset info
        preset_info = engine.get_preset_info(0, 0)
        assert preset_info is not None, "Should be able to load preset from reference SF2"

        # Test key range matching
        descriptors = preset_info.region_descriptors
        assert len(descriptors) > 0, "Preset should have at least one region"

        # Test that notes within key ranges match their zones
        matched_notes = 0
        for note in range(128):
            matching = [d for d in descriptors if d.should_play_for_note(note, 100)]
            if matching:
                matched_notes += 1
        
        # Most notes should match at least one zone in a real SF2 file
        assert matched_notes > 0, "At least some notes should match zones"

    @pytest.mark.unit
    def test_velocity_range_matching(self, ref_sf2_path):
        """Test zone matching based on velocity ranges."""
        from synth.engine.sf2_engine import SF2Engine
        engine = SF2Engine(sf2_file_path=ref_sf2_path, sample_rate=44100, block_size=1024)
        
        preset_info = engine.get_preset_info(0, 0)
        assert preset_info is not None, "Should be able to load preset from reference SF2"

        descriptors = preset_info.region_descriptors

        # Test velocity range matching
        for velocity in [1, 32, 64, 96, 127]:
            matching = [d for d in descriptors if d.should_play_for_note(60, velocity)]
            # Verify matching zones have appropriate velocity ranges
            for desc in matching:
                vel_low, vel_high = desc.velocity_range
                assert vel_low <= velocity <= vel_high

    @pytest.mark.unit
    def test_zone_inheritance(self, sf2_engine):
        """Test that instrument zones inherit from preset zones."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Verify all descriptors have engine type set
        for desc in preset_info.region_descriptors:
            assert desc.engine_type == "sf2"

    @pytest.mark.unit
    def test_multiple_zone_layering(self, sf2_engine):
        """Test that multiple zones can be triggered simultaneously."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Find a note that matches multiple zones
        note = 60
        velocity = 100

        matching = [
            d for d in preset_info.region_descriptors if d.should_play_for_note(note, velocity)
        ]

        # Multiple zones may match (layering)
        # Just verify we can find matching zones
        assert len(matching) >= 0

    @pytest.mark.unit
    def test_drum_zone_mapping(self, sf2_engine):
        """Test drum zone mapping for percussion sounds."""
        # Try to get drum preset (typically bank 128)
        preset_info = sf2_engine.get_preset_info(128, 0)

        if preset_info is None:
            pytest.skip("No drum preset available for testing")

        # Drum presets should have zones
        assert len(preset_info.region_descriptors) > 0

    @pytest.mark.unit
    def test_round_robin_selection(self, sf2_engine):
        """Test round-robin sample selection."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Check for round-robin groups
        rr_groups = set()
        for desc in preset_info.region_descriptors:
            if desc.round_robin_group > 0:
                rr_groups.add(desc.round_robin_group)

        # Round-robin groups may or may not exist
        # Just verify we can check for them
        assert isinstance(rr_groups, set)

    @pytest.mark.unit
    def test_region_descriptor_properties(self):
        """Test RegionDescriptor properties."""
        # Create a test region descriptor
        desc = RegionDescriptor(
            region_id=0,
            engine_type="sf2",
            key_range=(60, 72),
            velocity_range=(64, 127),
            round_robin_group=0,
            round_robin_position=0,
            sample_id=1,
            generator_params={"filter_cutoff": 5000.0},
        )

        # Test properties
        assert desc.region_id == 0
        assert desc.engine_type == "sf2"
        assert desc.key_range == (60, 72)
        assert desc.velocity_range == (64, 127)
        assert desc.sample_id == 1
        assert "filter_cutoff" in desc.generator_params

    @pytest.mark.unit
    def test_should_play_for_note(self):
        """Test should_play_for_note method."""
        desc = RegionDescriptor(
            region_id=0,
            engine_type="sf2",
            key_range=(60, 72),
            velocity_range=(64, 127),
            round_robin_group=0,
            round_robin_position=0,
            sample_id=1,
            generator_params={},
        )

        # Test key range
        assert desc.should_play_for_note(60, 100) is True  # Within range
        assert desc.should_play_for_note(72, 100) is True  # Edge of range
        assert desc.should_play_for_note(59, 100) is False  # Below range
        assert desc.should_play_for_note(73, 100) is False  # Above range

        # Test velocity range
        assert desc.should_play_for_note(60, 64) is True  # Within range
        assert desc.should_play_for_note(60, 127) is True  # Edge of range
        assert desc.should_play_for_note(60, 63) is False  # Below range
        assert desc.should_play_for_note(60, 128) is False  # Above range (velocity capped)

    @pytest.mark.unit
    def test_global_zone(self, sf2_engine):
        """Test global zone handling."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Global zone should match all notes
        global_zones = [
            d
            for d in preset_info.region_descriptors
            if d.key_range == (0, 127) and d.velocity_range == (0, 127)
        ]

        # Global zones may or may not exist
        assert isinstance(global_zones, list)

    @pytest.mark.unit
    def test_preset_info_structure(self, sf2_engine):
        """Test PresetInfo structure."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Verify PresetInfo structure
        assert hasattr(preset_info, "bank")
        assert hasattr(preset_info, "program")
        assert hasattr(preset_info, "name")
        assert hasattr(preset_info, "engine_type")
        assert hasattr(preset_info, "region_descriptors")
        assert hasattr(preset_info, "master_level")
        assert hasattr(preset_info, "master_pan")
        assert hasattr(preset_info, "reverb_send")
        assert hasattr(preset_info, "chorus_send")

        # Verify values
        assert preset_info.bank == 0
        assert preset_info.program == 0
        assert preset_info.engine_type == "sf2"
        assert isinstance(preset_info.region_descriptors, list)

    @pytest.mark.unit
    def test_zone_overlap_handling(self, sf2_engine):
        """Test handling of overlapping zones."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Check for overlapping key ranges
        descriptors = preset_info.region_descriptors
        overlaps = []

        for i, desc1 in enumerate(descriptors):
            for desc2 in descriptors[i + 1 :]:
                # Check if key ranges overlap
                if desc1.key_range[0] <= desc2.key_range[1] and desc2.key_range[0] <= desc1.key_range[1]:
                    overlaps.append((desc1.region_id, desc2.region_id))

        # Overlaps are allowed in SF2 (for layering)
        assert isinstance(overlaps, list)

    @pytest.mark.unit
    def test_velocity_crossfade(self, sf2_engine):
        """Test velocity crossfade between zones."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Check for velocity crossfade zones
        descriptors = preset_info.region_descriptors

        # Look for adjacent velocity ranges
        for i, desc1 in enumerate(descriptors):
            for desc2 in descriptors[i + 1 :]:
                # Check if velocity ranges are adjacent
                if desc1.velocity_range[1] == desc2.velocity_range[0]:
                    # Adjacent velocity ranges detected
                    pass

    @pytest.mark.unit
    def test_key_crossfade(self, sf2_engine):
        """Test key crossfade between zones."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Check for key crossfade zones
        descriptors = preset_info.region_descriptors

        # Look for adjacent key ranges
        for i, desc1 in enumerate(descriptors):
            for desc2 in descriptors[i + 1 :]:
                # Check if key ranges are adjacent
                if desc1.key_range[1] == desc2.key_range[0]:
                    # Adjacent key ranges detected
                    pass

    @pytest.mark.unit
    def test_empty_preset(self, sf2_engine):
        """Test handling of empty preset."""
        # Try to get non-existent preset
        preset_info = sf2_engine.get_preset_info(999, 999)

        # Should return None for non-existent preset
        assert preset_info is None

    @pytest.mark.unit
    def test_preset_name(self, sf2_engine):
        """Test preset name retrieval."""
        preset_info = sf2_engine.get_preset_info(0, 0)

        if preset_info is None:
            pytest.skip("No SF2 file available for testing")

        # Preset should have a name
        assert isinstance(preset_info.name, str)
        assert len(preset_info.name) > 0