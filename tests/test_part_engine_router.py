"""Tests for PartEngineRouter — per-part engine assignment with fallback chains.

Tests cover:
- EngineRoutingMode enum values
- Default mode (FULL_BANK_PROGRAM)
- EXPLICIT mode assignment
- Bank-MSB-based fallback routing
- Drum part detection via part_mode
- Engine registry interaction
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from synth.protocols.xg.part_engine_router import PartEngineRouter, EngineRoutingMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _part_data(
    bank_msb: int = 0,
    bank_lsb: int = 0,
    program_num: int = 0,
    part_mode: int = 0,
) -> dict:
    """Build a minimal part-data dict."""
    return {
        "bank_msb": bank_msb,
        "bank_lsb": bank_lsb,
        "program_num": program_num,
        "part_mode": part_mode,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEngineRoutingMode:
    """EngineRoutingMode enum values."""

    def test_mode_explicit(self):
        assert EngineRoutingMode.EXPLICIT.value == "explicit"

    def test_mode_full_bank_program(self):
        assert EngineRoutingMode.FULL_BANK_PROGRAM.value == "full"

    def test_mode_distinct(self):
        assert EngineRoutingMode.EXPLICIT != EngineRoutingMode.FULL_BANK_PROGRAM


class TestPartEngineRouterDefaults:
    """Default construction and mode."""

    def test_default_num_parts(self):
        router = PartEngineRouter()
        assert router.num_parts == 16

    def test_default_mode(self):
        router = PartEngineRouter()
        assert router.mode == EngineRoutingMode.FULL_BANK_PROGRAM

    def test_default_explicit_engines_empty(self):
        router = PartEngineRouter()
        assert router._explicit_engines == {}

    def test_default_engine_registry_none(self):
        router = PartEngineRouter()
        assert router._engine_registry is None

    def test_custom_num_parts(self):
        router = PartEngineRouter(num_parts=8)
        assert router.num_parts == 8


class TestPartEngineRouterMode:
    """set_mode and mode transitions."""

    def test_set_mode_explicit(self):
        router = PartEngineRouter()
        router.set_mode(EngineRoutingMode.EXPLICIT)
        assert router.mode == EngineRoutingMode.EXPLICIT

    def test_set_mode_full(self):
        router = PartEngineRouter()
        router.set_mode(EngineRoutingMode.EXPLICIT)
        router.set_mode(EngineRoutingMode.FULL_BANK_PROGRAM)
        assert router.mode == EngineRoutingMode.FULL_BANK_PROGRAM


class TestPartEngineRouterGetEngine:
    """get_part_engine — bank+program and fallback logic."""

    def test_default_fallback_xg(self):
        """When no registry and bank_msb=0, returns 'xg'."""
        router = PartEngineRouter()
        engine = router.get_part_engine(0, _part_data())
        assert engine == "xg"

    def test_bank_msb_126_an(self):
        """bank_msb=126 → 'an' (analog engine)."""
        router = PartEngineRouter()
        engine = router.get_part_engine(0, _part_data(bank_msb=126))
        assert engine == "an"

    def test_bank_msb_127_fdsp(self):
        """bank_msb=127 → 'fdsp' (FDSP engine)."""
        router = PartEngineRouter()
        engine = router.get_part_engine(0, _part_data(bank_msb=127))
        assert engine == "fdsp"

    def test_explicit_mode_returns_assigned(self):
        """EXPLICIT mode returns the assigned engine."""
        router = PartEngineRouter()
        router.set_mode(EngineRoutingMode.EXPLICIT)
        router.set_part_engine(0, "sf2")
        router.set_part_engine(1, "fm")
        assert router.get_part_engine(0, _part_data()) == "sf2"
        assert router.get_part_engine(1, _part_data()) == "fm"

    def test_explicit_mode_fallback_when_not_assigned(self):
        """EXPLICIT mode falls through for unassigned parts."""
        router = PartEngineRouter()
        router.set_mode(EngineRoutingMode.EXPLICIT)
        router.set_part_engine(0, "sf2")
        # Part 1 not explicitly assigned → falls to bank-msb fallback
        engine = router.get_part_engine(1, _part_data())
        assert engine == "xg"

    def test_engine_registry_lookup_success(self):
        """When engine_registry returns a match, that engine is used."""
        router = PartEngineRouter()
        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.return_value = "sf2"
        router.set_engine_registry(mock_registry)

        engine = router.get_part_engine(0, _part_data(program_num=42))
        assert engine == "sf2"
        mock_registry.get_engine_for_program.assert_called_once_with(0, 42)

    def test_engine_registry_returns_none_fallback(self):
        """When registry returns None, falls back to bank-MSB routing."""
        router = PartEngineRouter()
        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.return_value = None
        router.set_engine_registry(mock_registry)

        engine = router.get_part_engine(0, _part_data())
        assert engine == "xg"

    def test_engine_registry_exception_fallback(self):
        """When registry raises, gracefully falls to bank-MSB routing."""
        router = PartEngineRouter()
        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.side_effect = RuntimeError("registry error")
        router.set_engine_registry(mock_registry)

        engine = router.get_part_engine(0, _part_data())
        assert engine == "xg"

    def test_full_bank_program_uses_bank_code(self):
        """The bank code is (bank_msb << 7) | bank_lsb."""
        router = PartEngineRouter()
        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.return_value = "fm"
        router.set_engine_registry(mock_registry)
        router.get_part_engine(0, _part_data(bank_msb=1, bank_lsb=2, program_num=3))
        mock_registry.get_engine_for_program.assert_called_once_with(1 << 7 | 2, 3)

    def test_part_data_missing_keys(self):
        """Missing keys in part_data use defaults (0)."""
        router = PartEngineRouter()
        engine = router.get_part_engine(0, {"bank_msb": 126})
        assert engine == "an"


class TestPartEngineRouterEdgeCases:
    """Edge cases / invalid inputs."""

    def test_get_engine_with_empty_dict(self):
        """Empty part_data should use defaults and return 'xg'."""
        router = PartEngineRouter()
        engine = router.get_part_engine(0, {})
        assert engine == "xg"

    def test_get_engine_out_of_range_part(self):
        """Part numbers beyond normal range still get a result (no crash)."""
        router = PartEngineRouter()
        engine = router.get_part_engine(99, _part_data())
        assert engine == "xg"


class TestPartEngineRouterIsDrum:
    """is_drum_part — drum part detection."""

    def test_normal_part_not_drum(self):
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data()) is False

    def test_part_mode_1_is_drum(self):
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data(part_mode=1)) is True

    def test_part_mode_2_is_drum(self):
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data(part_mode=2)) is True

    def test_bank_msb_127_is_drum(self):
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data(bank_msb=127)) is True

    def test_bank_msb_127_with_part_mode_0_is_drum(self):
        """bank_msb=127 overrides part_mode=0."""
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data(bank_msb=127, part_mode=0)) is True

    def test_bank_msb_125_not_drum(self):
        """bank_msb=125 is not a drum indicator."""
        router = PartEngineRouter()
        assert router.is_drum_part(_part_data(bank_msb=125)) is False


class TestPartEngineRouterSetPart:
    """set_part_engine explicit assignment."""

    def test_set_and_retrieve(self):
        router = PartEngineRouter()
        router.set_part_engine(0, "sf2")
        assert router._explicit_engines[0] == "sf2"

    def test_set_overwrites(self):
        router = PartEngineRouter()
        router.set_part_engine(0, "sf2")
        router.set_part_engine(0, "fm")
        assert router._explicit_engines[0] == "fm"

    def test_explicit_mode_precedes_registry(self):
        """EXPLICIT mode returns assigned engine before consulting registry."""
        router = PartEngineRouter()
        router.set_mode(EngineRoutingMode.EXPLICIT)
        router.set_part_engine(0, "sf2")

        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.return_value = "fm"
        router.set_engine_registry(mock_registry)

        engine = router.get_part_engine(0, _part_data(bank_msb=126))
        assert engine == "sf2"
        mock_registry.get_engine_for_program.assert_not_called()


class TestPartEngineRouterSetRegistry:
    """set_engine_registry interface."""

    def test_set_registry_none(self):
        router = PartEngineRouter()
        router.set_engine_registry(None)
        engine = router.get_part_engine(0, _part_data())
        assert engine == "xg"

    def test_set_registry_clears_old(self):
        router = PartEngineRouter()
        mock_registry = MagicMock()
        mock_registry.get_engine_for_program.return_value = "an"
        router.set_engine_registry(mock_registry)
        engine = router.get_part_engine(0, _part_data(bank_msb=0))
        assert engine == "an"
