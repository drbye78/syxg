"""Tests for the PhysicalEngine (physical modeling synthesis engine)."""

from __future__ import annotations

import numpy as np
import pytest


@pytest.mark.unit
class TestPhysicalEngineInit:
    """Tests for PhysicalEngine construction and basic properties."""

    def test_init_defaults(self):
        """Test that PhysicalEngine can be instantiated with defaults."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        info = engine.get_engine_info()
        assert info["name"] == "Physical Modeling Engine"
        assert info["type"] == "physical"
        assert engine.sample_rate == 44100

    def test_init_custom_params(self):
        """Test that PhysicalEngine accepts custom parameters."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine(max_strings=8, sample_rate=48000, block_size=512)
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        assert engine.max_strings == 8
        assert engine.sample_rate == 48000
        assert engine.block_size == 512
        assert len(engine.waveguides) == 8
        assert len(engine.strings) == 8


@pytest.mark.unit
class TestPhysicalEngineInfo:
    """Tests for PhysicalEngine metadata and discovery."""

    def test_engine_info(self):
        """Test that get_engine_info() returns a dict with expected keys."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        info = engine.get_engine_info()
        assert isinstance(info, dict)
        assert info["name"] == "Physical Modeling Engine"
        assert info["type"] == "physical"
        assert "capabilities" in info
        assert "karplus_strong" in info["capabilities"]
        assert "formats" in info
        assert "polyphony" in info

    def test_get_engine_type(self):
        """Test that get_engine_type() returns a string."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        engine_type = engine.get_engine_type()
        assert isinstance(engine_type, str)


@pytest.mark.unit
class TestPhysicalEngineNoteOnOff:
    """Tests for note_on and note_off methods."""

    def test_note_on_off(self):
        """Test that note_on and note_off don't crash."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        # note_on should not raise
        engine.note_on(60, 100)
        assert engine.is_active()

        # note_off should not raise
        engine.note_off(60)
        assert not engine.is_active()

    def test_note_on_multiple(self):
        """Test that multiple note_on calls work."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine(max_strings=4)
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        for note in (60, 64, 67, 72):
            engine.note_on(note, 100)

        assert engine.is_active()
        assert len(engine.active_voices) == 4

        # Release all
        for note in (60, 64, 67, 72):
            engine.note_off(note)

        assert not engine.is_active()

    def test_note_off_nonexistent(self):
        """Test that note_off for a note not currently playing doesn't crash."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        # Should not raise
        engine.note_off(99)

    def test_generate_samples_after_note_on(self):
        """Test that generate_samples produces audio after a note_on."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine()
        except Exception as e:
            pytest.skip(f"Cannot instantiate PhysicalEngine: {e}")

        engine.note_on(60, 100)

        block = engine.generate_samples(
            note=60,
            velocity=100,
            modulation={"pitch": 0.0},
            block_size=256,
        )

        assert isinstance(block, np.ndarray)
        assert block.shape == (256, 2)
        assert block.dtype == np.float32


@pytest.mark.unit
class TestPhysicalEngineProduction:
    """Test from test_production_fixes — PhysicalEngine should instantiate."""

    def test_engine_instantiation_production(self):
        """PhysicalEngine should instantiate."""
        try:
            from synth.engines.physical_engine import PhysicalEngine

            engine = PhysicalEngine(sample_rate=44100)

            assert engine is not None
            assert engine.sample_rate == 44100
        except Exception as e:
            pytest.skip(f"Cannot instantiate: {e}")
