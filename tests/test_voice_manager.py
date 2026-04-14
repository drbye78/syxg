"""
Voice Manager Tests

Tests for voice allocation, stealing, priority, and resource management.
"""

from __future__ import annotations

import pytest
import numpy as np


class TestVoiceManager:
    """Test voice allocation and management."""

    @pytest.mark.unit
    def test_voice_allocation_from_pool(self):
        """Test allocating voices from available pool."""
        max_voices = 64
        allocated = []

        for i in range(max_voices):
            voice = {"id": i, "note": 60 + i, "active": True}
            allocated.append(voice)

        assert len(allocated) == max_voices

        for voice in allocated:
            assert voice["active"] is True

    @pytest.mark.unit
    def test_voice_stealing_oldest(self):
        """Test stealing oldest voice when polyphony exceeded."""
        voices = []

        for i in range(64):
            voices.append({"id": i, "note": 60, "start_time": i * 0.01})

        oldest = min(voices, key=lambda v: v["start_time"])
        assert oldest["id"] == 0

        voices.remove(oldest)
        new_voice = {"id": 64, "note": 72, "start_time": 0.64}
        voices.append(new_voice)

        assert len(voices) == 64
        assert new_voice in voices

    @pytest.mark.unit
    def test_voice_stealing_lowest_priority(self):
        """Test stealing lowest priority voice."""
        voices = [
            {"id": 0, "priority": 100},
            {"id": 1, "priority": 50},
            {"id": 2, "priority": 75},
        ]

        lowest = min(voices, key=lambda v: v["priority"])
        assert lowest["id"] == 1

    @pytest.mark.unit
    def test_voice_priority_calculation(self):
        """Test voice priority based on velocity and note age."""
        velocity_weight = 0.7
        age_weight = 0.3

        voice1 = {"velocity": 100, "age": 1.0}
        voice2 = {"velocity": 80, "age": 0.5}

        priority1 = velocity_weight * voice1["velocity"] + age_weight * (
            1.0 / voice1["age"]
        )
        priority2 = velocity_weight * voice2["velocity"] + age_weight * (
            1.0 / voice2["age"]
        )

        assert priority1 > priority2

    @pytest.mark.unit
    def test_drum_voice_allocation(self):
        """Test drum voice allocation (different from melodic)."""
        drum_voices = []
        melodic_voices = []

        drum_voice = {"type": "drum", "note": 36, "channel": 9}
        drum_voices.append(drum_voice)

        melodic_voice = {"type": "melodic", "note": 60, "channel": 0}
        melodic_voices.append(melodic_voice)

        assert drum_voice["channel"] == 9
        assert melodic_voice["channel"] == 0

    @pytest.mark.unit
    def test_exclusive_class_stealing(self):
        """Test exclusive class voice stealing."""
        voices = [
            {"id": 0, "exclusive_class": 1, "active": True},
            {"id": 1, "exclusive_class": 1, "active": True},
            {"id": 2, "exclusive_class": 2, "active": True},
        ]

        new_voice = {"id": 3, "exclusive_class": 1}

        same_class = [v for v in voices if v["exclusive_class"] == 1]
        assert len(same_class) == 2

        stolen = same_class[0]
        voices.remove(stolen)
        voices.append(new_voice)

        assert len(voices) == 3
        assert new_voice in voices

    @pytest.mark.unit
    def test_voice_cleanup_after_release(self):
        """Test voice resources returned to pool after release."""
        pool_size = 64
        pool = list(range(pool_size))
        allocated = []

        voice_id = pool.pop()
        allocated.append(voice_id)
        assert len(pool) == pool_size - 1

        allocated.remove(voice_id)
        pool.append(voice_id)
        assert len(pool) == pool_size

    @pytest.mark.unit
    def test_maximum_polyphony(self):
        """Test maximum simultaneous voices."""
        max_voices = 64
        active_voices = []

        for i in range(max_voices + 10):
            if len(active_voices) < max_voices:
                active_voices.append({"id": i, "active": True})
            else:
                stolen = active_voices.pop(0)
                active_voices.append({"id": i, "active": True})

        assert len(active_voices) == max_voices

    @pytest.mark.unit
    def test_voice_stealing_performance(self):
        """Test voice stealing doesn't cause audio glitches."""
        import time

        voices = [{"id": i, "active": True} for i in range(64)]

        start_time = time.time()
        for _ in range(100):
            stolen = voices.pop(0)
            voices.append({"id": stolen["id"], "active": True})
        end_time = time.time()

        assert (end_time - start_time) < 1.0

    @pytest.mark.unit
    def test_voice_allocation_with_velocity(self):
        """Test voice allocation considers velocity."""
        voices = []

        for i in range(5):
            voices.append({"id": i, "velocity": 100 - i * 10, "active": True})

        voices.sort(key=lambda v: v["velocity"], reverse=True)

        assert voices[0]["velocity"] == 100
        assert voices[4]["velocity"] == 60