"""
Tests for VoiceManager - Polyphony Management and Voice Allocation System.

Exercises the real VoiceManager from synth.processing.voice.voice_manager
with no stubs or dict mocks.
"""

from __future__ import annotations

import time

import pytest

from synth.processing.voice.voice_manager import (
    VoiceInfo,
    VoiceManager,
    VoiceState,
    VoiceStealingStrategy,
)


# ---------------------------------------------------------------------------
# TestVoiceManagerAllocation
# ---------------------------------------------------------------------------


class TestVoiceManagerAllocation:
    """Voice allocation behavior."""

    @pytest.mark.unit
    def test_allocate_voice_returns_valid_id(self):
        """allocate_voice returns a voice_id in [0, max_voices)."""
        vm = VoiceManager(max_voices=16)
        voice_id = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert voice_id is not None
        assert 0 <= voice_id < 16

    @pytest.mark.unit
    def test_allocate_voice_fills_all_voices(self):
        """Allocating max_voices times succeeds with unique IDs."""
        vm = VoiceManager(max_voices=8)
        ids: list[int] = []
        for i in range(8):
            vid = vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
            assert vid is not None, f"Allocation failed at index {i}"
            ids.append(vid)
        assert len(set(ids)) == 8, "All voice IDs should be unique"

    @pytest.mark.unit
    def test_allocate_voice_beyond_max_triggers_stealing(self):
        """When all voices are occupied, the next allocation steals."""
        vm = VoiceManager(max_voices=4)
        vm.set_stealing_strategy(VoiceStealingStrategy.OLDEST)
        # Fill all voices
        for i in range(4):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        # Next allocation must steal (OLDEST always succeeds)
        vid = vm.allocate_voice(
            channel=1, note=72, velocity=100, engine_type="xg"
        )
        assert vid is not None, "Should steal when polyphony exhausted"
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 4

    @pytest.mark.unit
    def test_allocate_voice_beyond_max_priority_stealing_may_fail(self):
        """With PRIORITY strategy, stealing fails if all voices have equal
        or higher engine priority."""
        vm = VoiceManager(max_voices=4)
        # Fill all voices with same engine type (priority 7)
        for i in range(4):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        # Same engine type means same priority — no steal candidate
        vid = vm.allocate_voice(
            channel=1, note=72, velocity=100, engine_type="xg"
        )
        assert vid is None, (
            "PRIORITY strategy refuses to steal same-priority voices"
        )
        stats = vm.get_voice_statistics()
        assert stats["allocation_stats"]["allocation_failures"] == 1

    @pytest.mark.unit
    def test_allocate_voice_different_engine_types(self):
        """Voices can be allocated with various engine types."""
        vm = VoiceManager(max_voices=16)
        for engine in ("fdsp", "an", "sf2", "xg", "fm", "wavetable"):
            vid = vm.allocate_voice(
                channel=0, note=60, velocity=100, engine_type=engine
            )
            assert vid is not None, f"Allocation failed for engine {engine}"

    @pytest.mark.unit
    def test_allocate_voice_with_mpe_params(self):
        """MPE zone id and note number are stored on the voice info."""
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0,
            note=60,
            velocity=100,
            engine_type="xg",
            mpe_zone_id=1,
            mpe_note_number=60,
        )
        assert vid is not None
        info = vm.get_voice_info(vid)
        assert info is not None
        assert info.mpe_zone_id == 1
        assert info.mpe_note_number == 60

    @pytest.mark.unit
    def test_allocate_voice_same_note_channel_retriggers(self):
        """Allocating the same note on the same channel retriggers the
        existing voice and returns the same ID."""
        vm = VoiceManager(max_voices=16)
        vid1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vid2 = vm.allocate_voice(
            channel=0, note=60, velocity=80, engine_type="xg"
        )
        assert vid2 == vid1, "Retrigger should return same voice_id"
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 1


# ---------------------------------------------------------------------------
# TestVoiceManagerNoteLookup
# ---------------------------------------------------------------------------


class TestVoiceManagerNoteLookup:
    """Channel + note voice lookup (find_voice)."""

    @pytest.mark.unit
    def test_find_voice_finds_allocated(self):
        vm = VoiceManager(max_voices=16)
        vm.allocate_voice(channel=0, note=60, velocity=100, engine_type="xg")
        assert vm.find_voice(0, 60) is not None

    @pytest.mark.unit
    def test_find_voice_returns_none_for_unallocated(self):
        vm = VoiceManager(max_voices=16)
        assert vm.find_voice(0, 60) is None

    @pytest.mark.unit
    def test_find_voice_returns_correct_id(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vm.find_voice(0, 60) == vid

    @pytest.mark.unit
    def test_find_voice_returns_none_after_dealloc(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vm.deallocate_voice(vid)
        assert vm.find_voice(0, 60) is None

    @pytest.mark.unit
    def test_find_voice_distinct_channels(self):
        """Same note on different channels returns separate voices."""
        vm = VoiceManager(max_voices=16)
        vid0 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vid1 = vm.allocate_voice(
            channel=1, note=60, velocity=100, engine_type="xg"
        )
        assert vid0 != vid1
        assert vm.find_voice(0, 60) == vid0
        assert vm.find_voice(1, 60) == vid1


# ---------------------------------------------------------------------------
# TestVoiceManagerDeallocation
# ---------------------------------------------------------------------------


class TestVoiceManagerDeallocation:
    """Voice deallocation behavior."""

    @pytest.mark.unit
    def test_deallocate_voice_valid_returns_true(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vm.deallocate_voice(vid) is True

    @pytest.mark.unit
    def test_deallocate_voice_invalid_returns_false(self):
        vm = VoiceManager(max_voices=16)
        assert vm.deallocate_voice(999) is False

    @pytest.mark.unit
    def test_deallocate_voice_twice_returns_false(self):
        """Deallocating an already freed voice returns False."""
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vm.deallocate_voice(vid)
        assert vm.deallocate_voice(vid) is False

    @pytest.mark.unit
    def test_deallocated_voice_can_be_reallocated(self):
        """With max_voices=1, the freed ID is the only available one."""
        vm = VoiceManager(max_voices=1)
        vid1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vm.deallocate_voice(vid1)
        vid2 = vm.allocate_voice(
            channel=0, note=61, velocity=100, engine_type="xg"
        )
        assert vid2 == vid1, "Freed voice ID should be reused"


# ---------------------------------------------------------------------------
# TestVoiceManagerState
# ---------------------------------------------------------------------------


class TestVoiceManagerState:
    """Voice ADSR state management."""

    @pytest.mark.unit
    def test_allocated_voice_starts_in_attack(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        info = vm.get_voice_info(vid)
        assert info is not None
        assert info.state == VoiceState.ATTACK

    @pytest.mark.unit
    def test_update_voice_state_changes_state(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vm.update_voice_state(vid, VoiceState.SUSTAIN) is True
        info = vm.get_voice_info(vid)
        assert info is not None
        assert info.state == VoiceState.SUSTAIN

    @pytest.mark.unit
    def test_update_voice_state_transitions_all_states(self):
        """Voice can traverse all ADSR states."""
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        for state in (
            VoiceState.ATTACK,
            VoiceState.DECAY,
            VoiceState.SUSTAIN,
            VoiceState.RELEASE,
            VoiceState.PENDING_RELEASE,
        ):
            assert vm.update_voice_state(vid, state) is True
        info = vm.get_voice_info(vid)
        assert info is not None
        assert info.state == VoiceState.PENDING_RELEASE

    @pytest.mark.unit
    def test_update_voice_state_valid_id_returns_true(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vm.update_voice_state(vid, VoiceState.DECAY) is True

    @pytest.mark.unit
    def test_update_voice_state_invalid_id_returns_false(self):
        vm = VoiceManager(max_voices=16)
        assert vm.update_voice_state(999, VoiceState.RELEASE) is False

    @pytest.mark.unit
    def test_update_voice_state_zero_returns_false(self):
        """Voice ID 0 before any allocation is invalid."""
        vm = VoiceManager(max_voices=16)
        assert vm.update_voice_state(0, VoiceState.RELEASE) is False


# ---------------------------------------------------------------------------
# TestVoiceManagerClear
# ---------------------------------------------------------------------------


class TestVoiceManagerClear:
    """Channel and global clear operations."""

    @pytest.mark.unit
    def test_clear_channel_frees_voices_on_channel_only(self):
        vm = VoiceManager(max_voices=16)
        v1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        v2 = vm.allocate_voice(
            channel=1, note=61, velocity=100, engine_type="xg"
        )
        vm.allocate_voice(channel=0, note=62, velocity=100, engine_type="xg")
        vm.clear_channel(0)
        assert vm.find_voice(0, 60) is None
        assert vm.find_voice(0, 62) is None
        assert vm.find_voice(1, 61) is not None  # Untouched

    @pytest.mark.unit
    def test_clear_channel_unknown_channel_safe(self):
        """Clearing a channel with no voices does nothing."""
        vm = VoiceManager(max_voices=16)
        vm.clear_channel(9)  # Should not raise
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 0

    @pytest.mark.unit
    def test_clear_all_voices_frees_everything(self):
        vm = VoiceManager(max_voices=16)
        for i in range(5):
            vm.allocate_voice(
                channel=i, note=60, velocity=100, engine_type="xg"
            )
        vm.clear_all_voices()
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 0

    @pytest.mark.unit
    def test_clear_all_voices_empty_is_safe(self):
        """Clearing when no voices are active does not raise."""
        vm = VoiceManager(max_voices=16)
        vm.clear_all_voices()  # Should not raise

    @pytest.mark.unit
    def test_voices_can_be_reallocated_after_clear(self):
        """After clear_all_voices, new voices can be allocated."""
        vm = VoiceManager(max_voices=4)
        for i in range(4):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        vm.clear_all_voices()
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vid is not None


# ---------------------------------------------------------------------------
# TestVoiceManagerStatistics
# ---------------------------------------------------------------------------


class TestVoiceManagerStatistics:
    """Voice statistics and monitoring."""

    @pytest.mark.unit
    def test_get_voice_statistics_returns_expected_keys(self):
        vm = VoiceManager(max_voices=16)
        stats = vm.get_voice_statistics()
        expected_keys = {
            "active_voices",
            "free_voices",
            "total_capacity",
            "utilization_percent",
            "by_engine",
            "by_channel",
            "allocation_stats",
            "stealing_strategy",
            "voice_priorities",
        }
        assert set(stats.keys()) == expected_keys

    @pytest.mark.unit
    def test_stats_correct_utilization_after_allocation(self):
        vm = VoiceManager(max_voices=8)
        for i in range(4):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 4
        assert stats["free_voices"] == 4
        assert stats["total_capacity"] == 8
        assert stats["utilization_percent"] == 50.0

    @pytest.mark.unit
    def test_stats_empty_voice_manager(self):
        vm = VoiceManager(max_voices=8)
        stats = vm.get_voice_statistics()
        assert stats["active_voices"] == 0
        assert stats["free_voices"] == 8
        assert stats["utilization_percent"] == 0.0
        assert stats["by_engine"] == {}
        assert stats["by_channel"] == {}

    @pytest.mark.unit
    def test_stats_engine_distribution(self):
        vm = VoiceManager(max_voices=16)
        vm.allocate_voice(channel=0, note=60, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=61, velocity=100, engine_type="sf2")
        vm.allocate_voice(channel=0, note=62, velocity=100, engine_type="xg")
        stats = vm.get_voice_statistics()
        assert stats["by_engine"]["xg"] == 2
        assert stats["by_engine"]["sf2"] == 1
        assert stats["by_channel"][0] == 3

    @pytest.mark.unit
    def test_stats_allocation_counters(self):
        vm = VoiceManager(max_voices=8)
        for i in range(3):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        stats = vm.get_voice_statistics()
        assert stats["allocation_stats"]["total_allocations"] == 3
        assert stats["allocation_stats"]["peak_concurrent_voices"] == 3


# ---------------------------------------------------------------------------
# TestVoiceStealingStrategy
# ---------------------------------------------------------------------------


class TestVoiceStealingStrategy:
    """Voice stealing strategy configuration."""

    @pytest.mark.unit
    def test_set_stealing_strategy_accepts_all_enum_values(self):
        vm = VoiceManager(max_voices=8)
        for strategy in VoiceStealingStrategy:
            assert vm.set_stealing_strategy(strategy) is True
            assert vm.stealing_strategy == strategy

    @pytest.mark.unit
    def test_set_stealing_strategy_returns_false_for_invalid(self):
        vm = VoiceManager(max_voices=8)
        assert vm.set_stealing_strategy("oldest") is False  # type: ignore[arg-type]
        assert vm.stealing_strategy == VoiceStealingStrategy.PRIORITY

    @pytest.mark.unit
    def test_set_stealing_strategy_rejects_none(self):
        vm = VoiceManager(max_voices=8)
        assert vm.set_stealing_strategy(None) is False  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_oldest_steals_oldest_voice(self):
        """OLDEST strategy steals the voice with the earliest start_time."""
        vm = VoiceManager(max_voices=3)
        vm.set_stealing_strategy(VoiceStealingStrategy.OLDEST)
        v1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        v2 = vm.allocate_voice(
            channel=0, note=61, velocity=100, engine_type="xg"
        )
        v3 = vm.allocate_voice(
            channel=0, note=62, velocity=100, engine_type="xg"
        )
        # Sleep briefly so OLDEST can differentiate
        time.sleep(0.001)
        # Now steal — should take the oldest (v1 or whichever)
        v4 = vm.allocate_voice(
            channel=1, note=72, velocity=100, engine_type="xg"
        )
        assert v4 is not None
        # The oldest allocated note (60) should be gone
        assert vm.find_voice(0, 60) is None

    @pytest.mark.unit
    def test_quietest_steals_lowest_velocity(self):
        """QUIETEST strategy steals the voice with lowest velocity."""
        vm = VoiceManager(max_voices=3)
        vm.set_stealing_strategy(VoiceStealingStrategy.QUIETEST)
        vm.allocate_voice(channel=0, note=60, velocity=30, engine_type="xg")
        vm.allocate_voice(channel=0, note=61, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=62, velocity=80, engine_type="xg")
        # Steal — should take velocity 30 (note 60)
        vm.allocate_voice(channel=1, note=72, velocity=90, engine_type="xg")
        assert vm.find_voice(0, 60) is None, "Quietest note should be stolen"

    @pytest.mark.unit
    def test_lowest_steals_lowest_note(self):
        """LOWEST strategy steals the voice with the lowest note number."""
        vm = VoiceManager(max_voices=3)
        vm.set_stealing_strategy(VoiceStealingStrategy.LOWEST)
        vm.allocate_voice(channel=0, note=40, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=60, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=80, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=1, note=72, velocity=100, engine_type="xg")
        assert vm.find_voice(0, 40) is None, "Lowest note should be stolen"

    @pytest.mark.unit
    def test_highest_steals_highest_note(self):
        """HIGHEST strategy steals the voice with the highest note number."""
        vm = VoiceManager(max_voices=3)
        vm.set_stealing_strategy(VoiceStealingStrategy.HIGHEST)
        vm.allocate_voice(channel=0, note=40, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=60, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=0, note=80, velocity=100, engine_type="xg")
        vm.allocate_voice(channel=1, note=72, velocity=100, engine_type="xg")
        assert vm.find_voice(0, 80) is None, "Highest note should be stolen"


# ---------------------------------------------------------------------------
# TestVoicePriority
# ---------------------------------------------------------------------------


class TestVoicePriority:
    """Engine priority configuration."""

    @pytest.mark.unit
    def test_set_voice_priority_known_engine_returns_true(self):
        vm = VoiceManager(max_voices=16)
        assert vm.set_voice_priority("xg", 5) is True
        assert vm.voice_priorities["xg"] == 5

    @pytest.mark.unit
    def test_set_voice_priority_unknown_engine_adds_it(self):
        vm = VoiceManager(max_voices=16)
        assert vm.set_voice_priority("custom_engine", 3) is True
        assert vm.voice_priorities["custom_engine"] == 3

    @pytest.mark.unit
    def test_set_voice_priority_updates_existing_voices(self):
        """Setting engine priority updates already-allocated voices of that
        engine type."""
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert vm.get_voice_info(vid).priority == 7  # Default
        vm.set_voice_priority("xg", 3)
        assert vm.get_voice_info(vid).priority == 3  # Updated

    @pytest.mark.unit
    def test_set_voice_priority_zero(self):
        vm = VoiceManager(max_voices=16)
        assert vm.set_voice_priority("xg", 0) is True
        assert vm.voice_priorities["xg"] == 0


# ---------------------------------------------------------------------------
# TestVoiceState Enum
# ---------------------------------------------------------------------------


class TestVoiceStateEnum:
    """VoiceState enum values."""

    @pytest.mark.unit
    def test_voice_state_values(self):
        assert VoiceState.FREE.value == "free"
        assert VoiceState.ATTACK.value == "attack"
        assert VoiceState.DECAY.value == "decay"
        assert VoiceState.SUSTAIN.value == "sustain"
        assert VoiceState.RELEASE.value == "release"
        assert VoiceState.PENDING_RELEASE.value == "pending_release"

    @pytest.mark.unit
    def test_voice_state_sequence(self):
        """States follow expected ADSR order."""
        states = list(VoiceState)
        assert states[0] == VoiceState.FREE
        assert states[1] == VoiceState.ATTACK
        assert states[2] == VoiceState.DECAY
        assert states[3] == VoiceState.SUSTAIN
        assert states[4] == VoiceState.RELEASE
        assert states[5] == VoiceState.PENDING_RELEASE


# ---------------------------------------------------------------------------
# TestVoiceStealingStrategy Enum
# ---------------------------------------------------------------------------


class TestVoiceStealingStrategyEnum:
    """VoiceStealingStrategy enum values."""

    @pytest.mark.unit
    def test_stealing_strategy_values(self):
        assert VoiceStealingStrategy.OLDEST.value == "oldest"
        assert VoiceStealingStrategy.QUIETEST.value == "quietest"
        assert VoiceStealingStrategy.LOWEST.value == "lowest"
        assert VoiceStealingStrategy.HIGHEST.value == "highest"
        assert VoiceStealingStrategy.PRIORITY.value == "priority"


# ---------------------------------------------------------------------------
# TestVoiceInfoDataclass
# ---------------------------------------------------------------------------


class TestVoiceInfoDataclass:
    """VoiceInfo dataclass structure."""

    @pytest.mark.unit
    def test_voice_info_creation(self):
        vi = VoiceInfo(
            voice_id=0,
            channel=1,
            note=60,
            velocity=100,
            engine_type="xg",
            state=VoiceState.ATTACK,
            start_time=time.time(),
        )
        assert vi.voice_id == 0
        assert vi.channel == 1
        assert vi.note == 60
        assert vi.velocity == 100
        assert vi.engine_type == "xg"
        assert vi.state == VoiceState.ATTACK
        assert vi.engine_params is None  # Default for dataclass
        assert vi.modulation_data is None  # Default for dataclass
        assert vi.effects_chain is None
        assert vi.mpe_zone_id is None
        assert vi.mpe_note_number is None

    @pytest.mark.unit
    def test_voice_info_with_optional_fields(self):
        vi = VoiceInfo(
            voice_id=5,
            channel=2,
            note=72,
            velocity=80,
            engine_type="sf2",
            state=VoiceState.SUSTAIN,
            start_time=1234.0,
            engine_params={"bank": 0, "program": 42},
            effects_chain=["reverb", "chorus"],
            modulation_data={"mod_wheel": 64},
            mpe_zone_id=1,
            mpe_note_number=72,
        )
        assert vi.engine_params["bank"] == 0
        assert vi.effects_chain == ["reverb", "chorus"]
        assert vi.modulation_data["mod_wheel"] == 64
        assert vi.mpe_zone_id == 1
        assert vi.mpe_note_number == 72

    @pytest.mark.unit
    def test_voice_info_uses_slots(self):
        """VoiceInfo uses dataclass(slots=True) so no __dict__."""
        vi = VoiceInfo(
            voice_id=0,
            channel=0,
            note=60,
            velocity=100,
            engine_type="xg",
            state=VoiceState.ATTACK,
            start_time=0.0,
        )
        with pytest.raises(AttributeError):
            vi.nonexistent_attr = "test"


# ---------------------------------------------------------------------------
# TestVoiceManagerGetActiveVoices
# ---------------------------------------------------------------------------


class TestVoiceManagerGetActiveVoices:
    """Active voice enumeration."""

    @pytest.mark.unit
    def test_get_active_voices_empty(self):
        vm = VoiceManager(max_voices=16)
        assert vm.get_active_voices() == []

    @pytest.mark.unit
    def test_get_active_voices_after_allocation(self):
        vm = VoiceManager(max_voices=16)
        vm.allocate_voice(channel=0, note=60, velocity=100, engine_type="xg")
        voices = vm.get_active_voices()
        assert len(voices) == 1
        assert voices[0].note == 60
        assert voices[0].channel == 0

    @pytest.mark.unit
    def test_get_voice_info_valid(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        info = vm.get_voice_info(vid)
        assert info is not None
        assert info.voice_id == vid

    @pytest.mark.unit
    def test_get_voice_info_invalid_returns_none(self):
        vm = VoiceManager(max_voices=16)
        assert vm.get_voice_info(999) is None

    @pytest.mark.unit
    def test_get_active_voices_count_after_dealloc(self):
        vm = VoiceManager(max_voices=16)
        v1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vm.allocate_voice(channel=0, note=61, velocity=100, engine_type="xg")
        vm.deallocate_voice(v1)
        voices = vm.get_active_voices()
        assert len(voices) == 1
        assert voices[0].note == 61


# ---------------------------------------------------------------------------
# TestVoiceManagerOptimizePolyphony
# ---------------------------------------------------------------------------


class TestVoiceManagerOptimizePolyphony:
    """Polyphony optimization analysis."""

    @pytest.mark.unit
    def test_optimize_polyphony_returns_dict(self):
        vm = VoiceManager(max_voices=16)
        result = vm.optimize_polyphony(target_utilization=0.8)
        assert "current_utilization" in result
        assert "target_utilization" in result
        assert "recommendations" in result
        assert "statistics" in result
        assert result["target_utilization"] == 0.8

    @pytest.mark.unit
    def test_optimize_polyphony_no_recommendations_at_low_util(self):
        vm = VoiceManager(max_voices=64)
        result = vm.optimize_polyphony(target_utilization=0.8)
        assert result["current_utilization"] == 0.0
        assert isinstance(result["recommendations"], list)

    @pytest.mark.unit
    def test_optimize_polyphony_stealing_recommendation(self):
        vm = VoiceManager(max_voices=4)
        vm.set_stealing_strategy(VoiceStealingStrategy.OLDEST)
        for i in range(5):
            vm.allocate_voice(
                channel=0, note=60 + i, velocity=100, engine_type="xg"
            )
        result = vm.optimize_polyphony(target_utilization=0.5)
        assert len(result["recommendations"]) > 0
        recs = " ".join(result["recommendations"]).lower()
        assert any(
            kw in recs
            for kw in ("stealing", "polyphony", "max_voices", "headroom")
        )


# ---------------------------------------------------------------------------
# TestVoiceManagerEdgeCases
# ---------------------------------------------------------------------------


class TestVoiceManagerEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_max_voices_one(self):
        vm = VoiceManager(max_voices=1)
        v1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        assert v1 is not None
        # Steal with OLDEST should work
        vm.set_stealing_strategy(VoiceStealingStrategy.OLDEST)
        v2 = vm.allocate_voice(
            channel=0, note=61, velocity=100, engine_type="xg"
        )
        assert v2 is not None

    @pytest.mark.unit
    def test_velocity_zero_still_allocates(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=60, velocity=0, engine_type="xg"
        )
        assert vid is not None

    @pytest.mark.unit
    def test_note_zero_still_allocates(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=0, note=0, velocity=100, engine_type="xg"
        )
        assert vid is not None

    @pytest.mark.unit
    def test_channel_fifteen_valid(self):
        vm = VoiceManager(max_voices=16)
        vid = vm.allocate_voice(
            channel=15, note=60, velocity=100, engine_type="xg"
        )
        assert vid is not None

    @pytest.mark.unit
    def test_get_voice_info_after_stolen_returns_none(self):
        """After a voice is stolen, its previous identity is gone."""
        vm = VoiceManager(max_voices=2)
        vm.set_stealing_strategy(VoiceStealingStrategy.OLDEST)
        v1 = vm.allocate_voice(
            channel=0, note=60, velocity=100, engine_type="xg"
        )
        vm.allocate_voice(channel=0, note=61, velocity=100, engine_type="xg")
        # Steal v1 (oldest)
        v3 = vm.allocate_voice(
            channel=1, note=72, velocity=100, engine_type="xg"
        )
        assert v3 is not None
        # Old voice ID v1 is now reused as v3
        info = vm.get_voice_info(v1)
        assert info is not None
        assert info.note == 72  # Reassigned
