"""
Tests for XGEngineRegistry - Synthesis Engine Management.

Verifies registry initialization, engine priorities, capabilities,
and public API methods. Handles graceful degradation when engine
dependencies are missing.
"""

from __future__ import annotations

import pytest

from synth.engines.engine_registry import XGEngineRegistry


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def registry():
    """Create an XGEngineRegistry with default settings."""
    return XGEngineRegistry()


# =========================================================================
# Initialization
# =========================================================================


@pytest.mark.unit
class TestInit:
    """Verify registry construction and defaults."""

    def test_init_defaults(self, registry):
        """Default sample_rate is 44100, registry is a SynthesisEngineRegistry."""
        assert registry.sample_rate == 44100
        assert registry.registry is not None
        # engine_priorities is pre-populated regardless of registration success
        assert isinstance(registry.engine_priorities, dict)
        assert len(registry.engine_priorities) > 0
        # engine_capabilities is pre-populated regardless of registration success
        assert isinstance(registry.engine_capabilities, dict)
        assert len(registry.engine_capabilities) > 0


# =========================================================================
# Priorities
# =========================================================================


@pytest.mark.unit
class TestPriorities:
    """Verify engine_priorities contains expected values."""

    def test_engine_priorities(self, registry):
        """Specific engine priorities match expected values."""
        assert registry.engine_priorities.get("fdsp") == 10
        assert registry.engine_priorities.get("sf2") == 8
        assert registry.engine_priorities.get("fm") == 6
        assert registry.engine_priorities.get("wavetable") == 5

    def test_set_engine_priority(self, registry):
        """set_engine_priority updates the priorities dict."""
        registry.set_engine_priority("fm", 99)
        assert registry.engine_priorities["fm"] == 99

        registry.set_engine_priority("nonexistent", 42)
        # Should not add keys that don't exist
        assert "nonexistent" not in registry.engine_priorities

    def test_get_engine_priority(self, registry):
        """get_engine_priority returns correct priority via registry."""
        # This delegates to registry.get_engine_priority which looks at
        # registered engines. It may return 0 if engine not registered.
        priority = registry.get_engine_priority("fm")
        # Should return an int without crashing
        assert isinstance(priority, int)


# =========================================================================
# Capabilities
# =========================================================================


@pytest.mark.unit
class TestCapabilities:
    """Verify engine_capabilities are correctly defined and queryable."""

    def test_engine_capabilities(self, registry):
        """Known engines have expected capabilities."""
        assert "sample_playback" in registry.engine_capabilities["sf2"]
        assert "soundfont_support" in registry.engine_capabilities["sf2"]
        assert "frequency_modulation" in registry.engine_capabilities["fm"]
        assert "dx7_compatibility" in registry.engine_capabilities["fm"]

    def test_get_engine_capabilities(self, registry):
        """get_engine_capabilities returns list for known engine, [] for unknown."""
        caps = registry.get_engine_capabilities("sf2")
        assert isinstance(caps, list)
        assert "sample_playback" in caps

        unknown = registry.get_engine_capabilities("nonexistent_engine")
        assert isinstance(unknown, list)
        assert unknown == []

    def test_find_engines_with_capability(self, registry):
        """find_engines_with_capability returns correct engine names."""
        sample_engines = registry.find_engines_with_capability("sample_playback")
        assert "sfz" in sample_engines
        assert "sf2" in sample_engines

        fm_engines = registry.find_engines_with_capability("frequency_modulation")
        assert "fm" in fm_engines

        # Unknown capability returns empty list
        unknown = registry.find_engines_with_capability("does_not_exist")
        assert isinstance(unknown, list)
        assert unknown == []


# =========================================================================
# Engine queries
# =========================================================================


@pytest.mark.unit
class TestEngineQueries:
    """Verify engine query methods work without crashing."""

    def test_get_engine_for_file(self, registry):
        """get_engine_for_file returns None or a string, never crashes."""
        result = registry.get_engine_for_file("/some/path/test.sf2")
        # May return None if no matching engine registered, or a string
        assert result is None or isinstance(result, str)

        result = registry.get_engine_for_file("/some/path/test.wav")
        assert result is None or isinstance(result, str)

    def test_get_registered_engines(self, registry):
        """get_registered_engines always returns a dict."""
        engines = registry.get_registered_engines()
        assert isinstance(engines, dict)
        # May be empty if all engines failed to register — that's OK

    def test_get_engine_info(self, registry):
        """get_engine_info returns None or a dict without crashing."""
        # Known engine type that might not be registered
        info = registry.get_engine_info("fm")
        assert info is None or isinstance(info, dict)

        # Unknown engine type
        info = registry.get_engine_info("nonexistent")
        assert info is None

    def test_get_engines_for_format(self, registry):
        """get_engines_for_format returns a list."""
        engines = registry.get_engines_for_format("sf2")
        assert isinstance(engines, list)

        engines = registry.get_engines_for_format("wav")
        assert isinstance(engines, list)


# =========================================================================
# Engine creation
# =========================================================================


@pytest.mark.unit
class TestEngineCreation:
    """Verify create_engine works when engine class is available."""

    def test_create_unknown_engine(self, registry):
        """create_engine returns None for unknown engine types."""
        engine = registry.create_engine("nonexistent")
        assert engine is None


# =========================================================================
# S90/S70 and Workstation
# =========================================================================


@pytest.mark.unit
class TestSpecialEngines:
    """Verify S90/S70 and workstation engine lists."""

    def test_get_s90_s70_engines(self, registry):
        """get_s90_s70_engines returns a filtered list of registered engines."""
        engines = registry.get_s90_s70_engines()
        assert isinstance(engines, list)
        for name in engines:
            assert name in ("fdsp", "an", "xg")

    def test_get_workstation_engines(self, registry):
        """get_workstation_engines returns a filtered list of registered engines."""
        engines = registry.get_workstation_engines()
        assert isinstance(engines, list)
        for name in engines:
            assert name in (
                "sf2",
                "xg",
                "an",
                "fdsp",
                "fm",
                "wavetable",
                "additive",
            )
