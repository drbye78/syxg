"""
MIDI Controller Processing Tests

Comprehensive tests for MIDI controller handling using
SF2RealtimeControllerManager from synth.io.sf2.sf2_modulation_engine.

Tests cover CC messages, specialized methods, pitch bend, multiple
controllers, value range handling, and edge cases.
"""

from __future__ import annotations

import pytest

from synth.io.sf2.sf2_modulation_engine import (
    SF2ModulationEngine,
    SF2RealtimeControllerManager,
)


@pytest.fixture
def manager() -> SF2RealtimeControllerManager:
    """Create a fresh controller manager with a real modulation engine."""
    mod_engine = SF2ModulationEngine()
    return SF2RealtimeControllerManager(mod_engine)


class TestMIDIControllers:
    """Test MIDI controller processing via SF2RealtimeControllerManager."""

    # ── CC message handling ────────────────────────────────────────────────

    @pytest.mark.unit
    def test_cc_volume(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC 7 (volume) value 100 produces correct normalized range."""
        manager.update_controller(7, 100, smooth=False)
        val = manager.get_controller_value(7)
        # (100/127 - 0.5) * 2 ≈ 0.5748
        assert val == pytest.approx(0.5748, abs=0.001)

    @pytest.mark.unit
    def test_cc_pan_center(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC 10 (pan) value 64 produces centre (~0)."""
        manager.update_controller(10, 64, smooth=False)
        val = manager.get_controller_value(10)
        # (64/127 - 0.5) * 2 ≈ 0.00787
        assert val == pytest.approx(0.00787, abs=0.001)

    @pytest.mark.unit
    def test_cc_sustain_off(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC 64 value 0 is below sustain threshold (off)."""
        manager.update_sustain_pedal(0)
        val = manager.get_controller_value(64)
        assert val == 0.0

    @pytest.mark.unit
    def test_cc_sustain_on(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC 64 value 127 is above sustain threshold (on)."""
        manager.update_sustain_pedal(127)
        val = manager.get_controller_value(64)
        assert val == 1.0

    @pytest.mark.unit
    def test_cc_mod_wheel_range(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC 1 (mod wheel) min (0) and max (127) produce -1.0 and 1.0."""
        manager.update_controller(1, 0, smooth=False)
        assert manager.get_controller_value(1) == pytest.approx(-1.0, abs=0.001)

        manager.update_controller(1, 127, smooth=False)
        assert manager.get_controller_value(1) == pytest.approx(1.0, abs=0.001)

    # ── Specialized methods ───────────────────────────────────────────────

    @pytest.mark.unit
    def test_update_modulation_wheel(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_modulation_wheel sets CC 1 value."""
        manager.update_modulation_wheel(64)
        # First call with smooth: filter init → 64/127, normalized ≈ 0.00787
        val = manager.get_controller_value(1)
        assert val == pytest.approx(0.00787, abs=0.001)

    @pytest.mark.unit
    def test_update_expression(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_expression sets CC 11 value."""
        manager.update_expression(100)
        # First call with smooth: filter init → 100/127, normalized ≈ 0.5748
        val = manager.get_controller_value(11)
        assert val == pytest.approx(0.5748, abs=0.001)

    @pytest.mark.unit
    def test_sustain_pedal_on_off(self, manager: SF2RealtimeControllerManager) -> None:
        """Test sustain pedal boundary: 63=off, 64=on."""
        for off_val in (0, 63):
            manager.update_sustain_pedal(off_val)
            assert manager.get_controller_value(64) == 0.0, f"Expected off for {off_val}"

        for on_val in (64, 127):
            manager.update_sustain_pedal(on_val)
            assert manager.get_controller_value(64) == 1.0, f"Expected on for {on_val}"

    @pytest.mark.unit
    def test_channel_pressure(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_channel_pressure stores normalized value."""
        manager.update_channel_pressure(64)
        expected = 64 / 127.0
        assert manager.get_controller_value(130) == pytest.approx(expected, abs=0.001)
        assert manager.current_channel_pressure == pytest.approx(expected, abs=0.001)

    @pytest.mark.unit
    def test_poly_pressure(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_poly_pressure stores per-note values independently."""
        manager.update_poly_pressure(60, 100)
        val_c4 = manager.get_controller_value(200 + 60)
        assert val_c4 == pytest.approx(100 / 127.0, abs=0.001)

        # A different note should have its own entry
        manager.update_poly_pressure(72, 50)
        val_c5 = manager.get_controller_value(200 + 72)
        assert val_c5 == pytest.approx(50 / 127.0, abs=0.001)

        # Note 60 must be unchanged
        assert manager.get_controller_value(200 + 60) == pytest.approx(100 / 127.0, abs=0.001)

    # ── Pitch bend ─────────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_pitch_bend_center(self, manager: SF2RealtimeControllerManager) -> None:
        """Test pitch bend centre (8192) produces 0 semitones."""
        manager.update_pitch_bend(8192)
        assert manager.current_pitch_bend_value == pytest.approx(0.0, abs=0.001)

    @pytest.mark.unit
    def test_pitch_bend_max(self, manager: SF2RealtimeControllerManager) -> None:
        """Test pitch bend max (16383) produces positive shift."""
        manager.update_pitch_bend(16383)
        # Default range = 12 semitones → 1.0 * 12 = 12.0
        assert manager.current_pitch_bend_value == pytest.approx(12.0, abs=0.01)

    @pytest.mark.unit
    def test_pitch_bend_min(self, manager: SF2RealtimeControllerManager) -> None:
        """Test pitch bend min (0) produces negative shift."""
        manager.update_pitch_bend(0)
        # Default range = 12 semitones → ≈ -12.0
        assert manager.current_pitch_bend_value == pytest.approx(-12.0, abs=0.01)

    @pytest.mark.unit
    def test_pitch_bend_custom_range(self, manager: SF2RealtimeControllerManager) -> None:
        """Test pitch bend with custom range_semitones parameter."""
        manager.update_pitch_bend(16383, range_semitones=24)
        assert manager.current_pitch_bend_value == pytest.approx(24.0, abs=0.01)
        assert manager.current_pitch_bend_range == 24

    @pytest.mark.unit
    def test_set_pitch_bend_range(self, manager: SF2RealtimeControllerManager) -> None:
        """Test set_pitch_bend_range configures range for subsequent bends."""
        manager.set_pitch_bend_range(5)
        assert manager.current_pitch_bend_range == 5
        manager.update_pitch_bend(16383)
        assert manager.current_pitch_bend_value == pytest.approx(5.0, abs=0.01)

    # ── Multiple controllers ──────────────────────────────────────────────

    @pytest.mark.unit
    def test_multiple_cc_updates(self, manager: SF2RealtimeControllerManager) -> None:
        """Test multiple CC updates in sequence — each stored independently."""
        manager.update_controller(7, 100, smooth=False)
        manager.update_controller(10, 64, smooth=False)
        manager.update_controller(11, 80, smooth=False)
        manager.update_controller(91, 50, smooth=False)

        assert manager.get_controller_value(7) == pytest.approx(0.5748, abs=0.001)
        assert manager.get_controller_value(10) == pytest.approx(0.00787, abs=0.001)
        assert manager.get_controller_value(11) == pytest.approx(0.2598, abs=0.001)
        assert manager.get_controller_value(91) == pytest.approx(-0.2126, abs=0.001)

    @pytest.mark.unit
    def test_cc_persistence(self, manager: SF2RealtimeControllerManager) -> None:
        """Test CC value persists after updating a different controller."""
        manager.update_controller(7, 100, smooth=False)
        val_before = manager.get_controller_value(7)

        manager.update_controller(10, 32, smooth=False)

        val_after = manager.get_controller_value(7)
        assert val_before == val_after
        assert val_after == pytest.approx(0.5748, abs=0.001)

    @pytest.mark.unit
    def test_unset_controller_default(self, manager: SF2RealtimeControllerManager) -> None:
        """Test unset controller returns default value 0.0."""
        assert manager.get_controller_value(99) == 0.0
        assert manager.get_controller_value(0) == 0.0
        assert manager.get_controller_value(127) == 0.0

    # ── CC range handling ─────────────────────────────────────────────────

    @pytest.mark.unit
    def test_cc_value_above_127(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_controller with value > 127 (no clamping in impl)."""
        manager.update_controller(7, 200, smooth=False)
        val = manager.get_controller_value(7)
        # (200/127 - 0.5) * 2 ≈ 2.1496 — the implementation does not clamp
        assert val == pytest.approx(2.1496, abs=0.001)

    @pytest.mark.unit
    def test_cc_value_below_zero(self, manager: SF2RealtimeControllerManager) -> None:
        """Test update_controller with value < 0 (no clamping in impl)."""
        manager.update_controller(7, -10, smooth=False)
        val = manager.get_controller_value(7)
        # ((-10)/127 - 0.5) * 2 ≈ -1.1575
        assert val == pytest.approx(-1.1575, abs=0.001)

    # ── Additional edge cases ──────────────────────────────────────────────

    @pytest.mark.unit
    def test_reset_all_controllers(self, manager: SF2RealtimeControllerManager) -> None:
        """Test reset_all_controllers clears state and zeroes values."""
        manager.update_controller(7, 100, smooth=False)
        manager.update_channel_pressure(64)
        manager.update_pitch_bend(8192)

        manager.reset_all_controllers()

        assert manager.get_controller_value(7) == 0.0
        assert manager.current_channel_pressure == 0.0
        assert manager.current_pitch_bend_value == 0.0

    @pytest.mark.unit
    def test_pitch_bend_range_clamping(self, manager: SF2RealtimeControllerManager) -> None:
        """Test set_pitch_bend_range clamps to [1, 24] semitones."""
        manager.set_pitch_bend_range(0)
        assert manager.current_pitch_bend_range == 1  # clamped min

        manager.set_pitch_bend_range(48)
        assert manager.current_pitch_bend_range == 24  # clamped max

        manager.set_pitch_bend_range(12)
        assert manager.current_pitch_bend_range == 12  # unchanged

    @pytest.mark.unit
    def test_mod_wheel_sets_lfo_depth(
        self, manager: SF2RealtimeControllerManager
    ) -> None:
        """Test update_modulation_wheel also sets CC 145 (LFO depth)."""
        manager.update_modulation_wheel(100)
        # CC 145 = 100/127 ≈ 0.7874 (passed as float, no smoothing)
        cc145 = manager.get_controller_value(145)
        assert cc145 == pytest.approx(100 / 127.0, abs=0.001)

    @pytest.mark.unit
    def test_controller_smoothing_toggle(
        self, manager: SF2RealtimeControllerManager
    ) -> None:
        """Test enable/disable controller smoothing."""
        manager.disable_controller_smoothing(1)
        assert 1 not in manager.smoothing_filters

        manager.enable_controller_smoothing(1, alpha=0.5)
        assert 1 in manager.smoothing_filters
        assert manager.smoothing_filters[1].alpha == 0.5

    @pytest.mark.unit
    def test_raw_cc_value_map(
        self, manager: SF2RealtimeControllerManager
    ) -> None:
        """Test several raw CC values cover the full normalized range."""
        cases = {
            0: -1.0,
            32: -0.4961,
            64: 0.00787,
            96: 0.5118,
            127: 1.0,
        }
        for raw, expected in cases.items():
            manager.update_controller(7, raw, smooth=False)
            assert manager.get_controller_value(7) == pytest.approx(expected, abs=0.001)
