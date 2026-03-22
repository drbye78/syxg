"""
Unit tests for the unified region-based synthesis architecture.

Tests cover:
- RegionDescriptor matching
- PresetInfo region selection
- Voice lazy region selection
- Multi-zone preset handling (key splits, velocity splits)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from synth.engine.preset_info import PresetInfo

# Import architecture components
from synth.engine.region_descriptor import RegionDescriptor
from synth.engine.synthesis_engine import SynthesisEngine, SynthesisEngineRegistry
from synth.partial.region import IRegion
from synth.voice.voice import Voice
from synth.voice.voice_factory import VoiceFactory

# ============================================================================
# Mock Objects for Testing
# ============================================================================


class MockRegion(IRegion):
    """Mock region for testing."""

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        super().__init__(descriptor, sample_rate)
        self._initialized = True
        self._sample_data = np.zeros(44100, dtype=np.float32)  # 1 second of silence

    def _load_sample_data(self) -> np.ndarray | None:
        return self._sample_data

    def _create_partial(self) -> Any | None:
        return None

    def _init_envelopes(self) -> None:
        pass

    def _init_filters(self) -> None:
        pass

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        if not self._initialized:
            return np.zeros(block_size * 2, dtype=np.float32)
        return np.zeros(block_size * 2, dtype=np.float32)


class MockEngine(SynthesisEngine):
    """Mock synthesis engine for testing."""

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        super().__init__(sample_rate, block_size)
        self._presets: dict[tuple, PresetInfo] = {}

    def register_preset(self, bank: int, program: int, preset_info: PresetInfo):
        """Register a preset for testing."""
        self._presets[(bank, program)] = preset_info

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        return self._presets.get((bank, program))

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        preset_info = self.get_preset_info(bank, program)
        if preset_info:
            return preset_info.region_descriptors
        return []

    def create_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        return MockRegion(descriptor, sample_rate)

    def load_sample_for_region(self, region: IRegion) -> bool:
        return True

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        return np.zeros(block_size * 2, dtype=np.float32)

    def is_note_supported(self, note: int) -> bool:
        return 0 <= note <= 127

    def get_engine_info(self) -> dict[str, Any]:
        return {
            "name": "Mock Engine",
            "type": "mock",
            "capabilities": ["test"],
            "formats": [],
            "polyphony": 64,
            "parameters": [],
        }

    def get_engine_type(self) -> str:
        return "mock"


# ============================================================================
# RegionDescriptor Tests
# ============================================================================


class TestRegionDescriptor:
    """Tests for RegionDescriptor class."""

    def test_should_play_for_note_in_range(self):
        """Test region matching for note in range."""
        desc = RegionDescriptor(
            region_id=1, engine_type="mock", key_range=(36, 60), velocity_range=(0, 127)
        )

        # Notes in range should match
        assert desc.should_play_for_note(48, 100) == True
        assert desc.should_play_for_note(36, 100) == True  # Boundary
        assert desc.should_play_for_note(60, 100) == True  # Boundary

        # Notes out of range should not match
        assert desc.should_play_for_note(35, 100) == False
        assert desc.should_play_for_note(61, 100) == False

    def test_should_play_for_note_velocity_split(self):
        """Test region matching for velocity splits."""
        desc = RegionDescriptor(
            region_id=1,
            engine_type="mock",
            key_range=(0, 127),
            velocity_range=(0, 64),  # Soft velocity only
        )

        # Soft velocities should match
        assert desc.should_play_for_note(60, 50) == True
        assert desc.should_play_for_note(60, 64) == True  # Boundary

        # Loud velocities should not match
        assert desc.should_play_for_note(60, 65) == False
        assert desc.should_play_for_note(60, 100) == False

    def test_should_play_for_note_key_and_velocity_split(self):
        """Test region matching for both key and velocity splits."""
        desc = RegionDescriptor(
            region_id=1,
            engine_type="mock",
            key_range=(0, 48),  # Bass range
            velocity_range=(65, 127),  # Loud only
        )

        # Bass + loud should match
        assert desc.should_play_for_note(36, 100) == True

        # Bass + soft should not match
        assert desc.should_play_for_note(36, 50) == False

        # Treble + loud should not match
        assert desc.should_play_for_note(72, 100) == False

    def test_get_priority_score(self):
        """Test priority score calculation."""
        desc = RegionDescriptor(
            region_id=1, engine_type="mock", key_range=(36, 60), velocity_range=(64, 127)
        )

        # Center of range should have highest score
        score_center = desc.get_priority_score(48, 96)
        score_edge = desc.get_priority_score(36, 64)

        assert score_center > score_edge

    def test_is_sample_based(self):
        """Test sample-based region detection."""
        # Sample-based region
        desc_sample = RegionDescriptor(region_id=1, engine_type="sf2", sample_id=42)
        assert desc_sample.is_sample_based() == True
        assert desc_sample.is_algorithmic() == False

        # Algorithmic region
        desc_algo = RegionDescriptor(
            region_id=1, engine_type="fm", algorithm_params={"algorithm": 1}
        )
        assert desc_algo.is_sample_based() == False
        assert desc_algo.is_algorithmic() == True


# ============================================================================
# PresetInfo Tests
# ============================================================================


class TestPresetInfo:
    """Tests for PresetInfo class."""

    def test_get_matching_descriptors_simple(self):
        """Test getting matching descriptors for simple preset."""
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Test Piano",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 127)),
            ],
        )

        # All notes/velocities should match
        matching = preset.get_matching_descriptors(60, 100)
        assert len(matching) == 1

    def test_get_matching_descriptors_velocity_splits(self):
        """Test getting matching descriptors for velocity-split preset."""
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Velocity Split Piano",
            engine_type="mock",
            region_descriptors=[
                # Soft layer
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 64)),
                # Medium layer
                RegionDescriptor(2, "mock", key_range=(0, 127), velocity_range=(65, 100)),
                # Loud layer
                RegionDescriptor(3, "mock", key_range=(0, 127), velocity_range=(101, 127)),
            ],
        )

        # Soft velocity should match only soft layer
        matching = preset.get_matching_descriptors(60, 50)
        assert len(matching) == 1
        assert matching[0].region_id == 1

        # Medium velocity should match only medium layer
        matching = preset.get_matching_descriptors(60, 80)
        assert len(matching) == 1
        assert matching[0].region_id == 2

        # Loud velocity should match only loud layer
        matching = preset.get_matching_descriptors(60, 120)
        assert len(matching) == 1
        assert matching[0].region_id == 3

    def test_get_matching_descriptors_key_splits(self):
        """Test getting matching descriptors for key-split preset."""
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Key Split Bass",
            engine_type="mock",
            region_descriptors=[
                # Bass zone (C0-B2)
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 127)),
                # Piano zone (C3-C8)
                RegionDescriptor(2, "mock", key_range=(48, 127), velocity_range=(0, 127)),
            ],
        )

        # Low note should match bass zone
        matching = preset.get_matching_descriptors(36, 100)  # C2
        assert len(matching) == 1
        assert matching[0].region_id == 1

        # High note should match piano zone
        matching = preset.get_matching_descriptors(72, 100)  # C5
        assert len(matching) == 1
        assert matching[0].region_id == 2

    def test_get_matching_descriptors_complex_splits(self):
        """Test getting matching descriptors for complex key+velocity splits."""
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Complex Piano",
            engine_type="mock",
            region_descriptors=[
                # Bass soft
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 64)),
                # Bass loud
                RegionDescriptor(2, "mock", key_range=(0, 47), velocity_range=(65, 127)),
                # Treble soft
                RegionDescriptor(3, "mock", key_range=(48, 127), velocity_range=(0, 64)),
                # Treble loud
                RegionDescriptor(4, "mock", key_range=(48, 127), velocity_range=(65, 127)),
            ],
        )

        # Bass + soft
        matching = preset.get_matching_descriptors(36, 50)
        assert len(matching) == 1
        assert matching[0].region_id == 1

        # Bass + loud
        matching = preset.get_matching_descriptors(36, 100)
        assert len(matching) == 1
        assert matching[0].region_id == 2

        # Treble + soft
        matching = preset.get_matching_descriptors(72, 50)
        assert len(matching) == 1
        assert matching[0].region_id == 3

        # Treble + loud
        matching = preset.get_matching_descriptors(72, 100)
        assert len(matching) == 1
        assert matching[0].region_id == 4

    def test_has_velocity_splits(self):
        """Test velocity split detection."""
        # No splits
        preset_no_splits = PresetInfo(
            bank=0,
            program=1,
            name="No Splits",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 127)),
            ],
        )
        assert preset_no_splits.has_velocity_splits() == False

        # Has velocity splits
        preset_vel_splits = PresetInfo(
            bank=0,
            program=1,
            name="Velocity Splits",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 64)),
                RegionDescriptor(2, "mock", key_range=(0, 127), velocity_range=(65, 127)),
            ],
        )
        assert preset_vel_splits.has_velocity_splits() == True

    def test_has_key_splits(self):
        """Test key split detection."""
        # No splits
        preset_no_splits = PresetInfo(
            bank=0,
            program=1,
            name="No Splits",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 127)),
            ],
        )
        assert preset_no_splits.has_key_splits() == False

        # Has key splits
        preset_key_splits = PresetInfo(
            bank=0,
            program=1,
            name="Key Splits",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 127)),
                RegionDescriptor(2, "mock", key_range=(48, 127), velocity_range=(0, 127)),
            ],
        )
        assert preset_key_splits.has_key_splits() == True


# ============================================================================
# Voice Tests (Multi-Zone Preset Support)
# ============================================================================


class TestVoice:
    """Tests for Voice class with lazy region selection."""

    def test_voice_get_regions_for_note_velocity_splits(self):
        """Test Voice region selection for velocity splits."""
        # Create preset with velocity splits
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Velocity Split Piano",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 64)),
                RegionDescriptor(2, "mock", key_range=(0, 127), velocity_range=(65, 127)),
            ],
        )

        # Create voice
        engine = MockEngine()
        voice = Voice(preset, engine, channel=0, sample_rate=44100)

        # Soft note should get soft region
        regions = voice.get_regions_for_note(60, 50)
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 1

        # Loud note should get loud region
        regions = voice.get_regions_for_note(60, 100)
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 2

    def test_voice_get_regions_for_note_key_splits(self):
        """Test Voice region selection for key splits."""
        # Create preset with key splits
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Key Split Bass",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 127)),
                RegionDescriptor(2, "mock", key_range=(48, 127), velocity_range=(0, 127)),
            ],
        )

        # Create voice
        engine = MockEngine()
        voice = Voice(preset, engine, channel=0, sample_rate=44100)

        # Bass note should get bass region
        regions = voice.get_regions_for_note(36, 100)  # C2
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 1

        # Treble note should get treble region
        regions = voice.get_regions_for_note(72, 100)  # C5
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 2

    def test_voice_get_regions_for_note_complex_splits(self):
        """Test Voice region selection for complex splits."""
        # Create preset with both key and velocity splits
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Complex Piano",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 64)),
                RegionDescriptor(2, "mock", key_range=(0, 47), velocity_range=(65, 127)),
                RegionDescriptor(3, "mock", key_range=(48, 127), velocity_range=(0, 64)),
                RegionDescriptor(4, "mock", key_range=(48, 127), velocity_range=(65, 127)),
            ],
        )

        # Create voice
        engine = MockEngine()
        voice = Voice(preset, engine, channel=0, sample_rate=44100)

        # Test all combinations
        test_cases = [
            (36, 50, 1),  # Bass soft
            (36, 100, 2),  # Bass loud
            (72, 50, 3),  # Treble soft
            (72, 100, 4),  # Treble loud
        ]

        for note, velocity, expected_id in test_cases:
            regions = voice.get_regions_for_note(note, velocity)
            assert len(regions) == 1, f"Expected 1 region for note={note}, vel={velocity}"
            assert regions[0].descriptor.region_id == expected_id, (
                f"Expected region {expected_id} for note={note}, vel={velocity}"
            )

    def test_voice_note_on_activates_correct_regions(self):
        """Test that note_on activates correct regions."""
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Test",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 64)),
                RegionDescriptor(2, "mock", key_range=(0, 47), velocity_range=(65, 127)),
                RegionDescriptor(3, "mock", key_range=(48, 127), velocity_range=(0, 127)),
            ],
        )

        engine = MockEngine()
        voice = Voice(preset, engine, channel=0, sample_rate=44100)

        # Bass soft
        activated = voice.note_on(36, 50)
        assert len(activated) == 1
        assert activated[0].descriptor.region_id == 1

        # Bass loud
        activated = voice.note_on(36, 100)
        assert len(activated) == 1
        assert activated[0].descriptor.region_id == 2

        # Treble (any velocity)
        activated = voice.note_on(72, 50)
        assert len(activated) == 1
        assert activated[0].descriptor.region_id == 3

        activated = voice.note_on(72, 100)
        assert len(activated) == 1
        assert activated[0].descriptor.region_id == 3


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the region-based architecture."""

    def test_voice_factory_creates_voice_with_preset_info(self):
        """Test VoiceFactory creates Voice with preset info."""
        # Create engine registry
        registry = SynthesisEngineRegistry()

        # Create and register mock engine
        engine = MockEngine()
        registry.register_engine(engine, "mock", priority=10)

        # Create voice factory
        factory = VoiceFactory(registry)

        # Register a preset
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Test Piano",
            engine_type="mock",
            region_descriptors=[
                RegionDescriptor(1, "mock", key_range=(0, 127), velocity_range=(0, 127)),
            ],
        )
        engine.register_preset(0, 1, preset)

        # Create voice
        voice = factory.create_voice(bank=0, program=1, channel=0, sample_rate=44100)

        assert voice is not None
        assert voice.get_preset_name() == "Test Piano"
        assert voice.get_region_count() == 1

    def test_multi_zone_preset_workflow(self):
        """Test complete workflow with multi-zone preset."""
        # Create engine registry
        registry = SynthesisEngineRegistry()
        engine = MockEngine()
        registry.register_engine(engine, "mock", priority=10)

        # Create complex multi-zone preset
        preset = PresetInfo(
            bank=0,
            program=1,
            name="Multi-Zone Piano",
            engine_type="mock",
            region_descriptors=[
                # Bass zone (C0-B2)
                RegionDescriptor(1, "mock", key_range=(0, 47), velocity_range=(0, 127)),
                # Mid zone (C3-B4) - soft
                RegionDescriptor(2, "mock", key_range=(48, 71), velocity_range=(0, 64)),
                # Mid zone (C3-B4) - loud
                RegionDescriptor(3, "mock", key_range=(48, 71), velocity_range=(65, 127)),
                # Treble zone (C5-C8)
                RegionDescriptor(4, "mock", key_range=(72, 127), velocity_range=(0, 127)),
            ],
        )
        engine.register_preset(0, 1, preset)

        # Create voice factory and voice
        factory = VoiceFactory(registry)
        voice = factory.create_voice(bank=0, program=1, channel=0, sample_rate=44100)

        # Test bass zone
        regions = voice.get_regions_for_note(36, 100)  # C2
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 1

        # Test mid zone soft
        regions = voice.get_regions_for_note(60, 50)  # C4 soft
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 2

        # Test mid zone loud
        regions = voice.get_regions_for_note(60, 100)  # C4 loud
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 3

        # Test treble zone
        regions = voice.get_regions_for_note(84, 100)  # C6
        assert len(regions) == 1
        assert regions[0].descriptor.region_id == 4


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
