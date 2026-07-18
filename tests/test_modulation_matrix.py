"""
SF2 Modulation Engine Tests

Exercises SF2ModulationEngine and SF2RealtimeControllerManager
from synth.io.sf2.sf2_modulation_engine with real imports.
"""

from __future__ import annotations

import pytest

from synth.io.sf2.sf2_modulation_engine import (
    SF2ModulationEngine,
    SF2RealtimeControllerManager,
)


class TestSF2ModulationEngine:
    """Tests for the SF2 modulation engine core."""

    # --- get_modulation_for_generator ---

    def test_get_modulation_for_generator_returns_finite_float(self) -> None:
        """Returns a finite float (0.0 when no modulators registered)."""
        engine = SF2ModulationEngine()
        result = engine.get_modulation_for_generator(0, 60, 100)
        assert isinstance(result, float)
        assert result == 0.0

    def test_get_modulation_for_generator_with_different_velocities(self) -> None:
        """No modulators → always 0 regardless of velocity."""
        engine = SF2ModulationEngine()
        assert engine.get_modulation_for_generator(0, 60, 1) == 0.0
        assert engine.get_modulation_for_generator(0, 60, 127) == 0.0

    def test_get_modulation_for_generator_with_different_notes(self) -> None:
        """No modulators → always 0 regardless of note."""
        engine = SF2ModulationEngine()
        assert engine.get_modulation_for_generator(0, 0, 100) == 0.0
        assert engine.get_modulation_for_generator(0, 127, 100) == 0.0

    # --- _get_source_value ---

    def test_get_source_value_zero(self) -> None:
        """SF2 §8.4.2: source index 0 = no controller → 0.0."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(0) == 0.0

    def test_get_source_value_velocity(self) -> None:
        """SF2 §8.4.2: source index 1 = note_on_velocity.
        controller_values[2] defaults to 0 → (0 - 64) / 64 = -1.0."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(1) == -1.0

    def test_get_source_value_key(self) -> None:
        """SF2 §8.4.2: source index 2 = note_on_key.
        controller_values[3] defaults to 0 → (0 - 64) / 64 = -1.0."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(2) == -1.0

    def test_get_source_value_poly_pressure(self) -> None:
        """SF2 §8.4.2: source index 3 = poly pressure (stub → 0.0)."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(3) == 0.0

    def test_get_source_value_pitch_bend(self) -> None:
        """SF2 §8.4.2: source index 5 = pitch wheel.
        controller_values[131] defaults to 0.0."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(5) == 0.0

    def test_get_source_value_channel_pressure(self) -> None:
        """SF2 §8.4.2: source index 4 = channel pressure.
        controller_values[130] defaults to 0 → 0/127 = 0.0."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(4) == 0.0

    def test_get_source_value_cc_7(self) -> None:
        """CC 7 (source index 7) returns (0 - 64) / 64 = -1.0 when unmodified."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(7) == -1.0

    def test_get_source_value_cc_10(self) -> None:
        """CC 10 (source index 10) returns (0 - 64) / 64 = -1.0 when unmodified."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(10) == -1.0

    def test_get_source_value_after_global_update(self) -> None:
        """Updating controller via update_global_controller changes source value."""
        engine = SF2ModulationEngine()
        engine.update_global_controller(7, 0.5)
        # update_global_controller sets the raw value, not normalized
        # _get_source_value reads controller_values and applies its own normalization
        # controller_values[7] = 0.5
        # (0.5 - 64) / 64.0 = -0.9921875
        expected = (0.5 - 64) / 64.0
        assert engine._get_source_value(7) == pytest.approx(expected)

    def test_get_source_value_standard_cc_by_index(self) -> None:
        """Source index 7-127 reads from controller_values[index].
        src_operator=145 → index 17 → CC17 → controller_values[17] = 0.75."""
        engine = SF2ModulationEngine()
        engine.update_global_controller(17, 0.75)
        # (0.75 - 64) / 64 ≈ -0.988
        expected = (0.75 - 64) / 64.0
        assert engine._get_source_value(145) == pytest.approx(expected, abs=0.001)

    def test_get_source_value_operator_beyond_127(self) -> None:
        """src_operator values beyond 127 are decoded via lower 7 bits.
        src_operator=999 → index=103 → CC103 (init to 0) → (0-64)/64 = -1.0.
        Every valid 7-bit source index 0-127 maps to a defined SF2 source,
        so there are no true "unknown" operators."""
        engine = SF2ModulationEngine()
        assert engine._get_source_value(999) == -1.0

    # --- Modulator transforms ---

    def test_modulator_linear_transform(self) -> None:
        """Modulator with linear transform (0) passes through unchanged."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 16384,  # 16384 / 32768 = 0.5
            "mod_trans_operator": 0,
        })
        # _get_source_value(7) = (0 - 64)/64 = -1.0
        # transformed = -1.0 * 0.5 = -0.5
        assert engine.get_modulation_for_generator(0, 60, 100) == -0.5

    def test_modulator_absolute_transform(self) -> None:
        """Modulator with absolute-value transform (1)."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 16384,
            "mod_trans_operator": 1,  # abs
        })
        # source = -1.0 → abs(-1.0) = 1.0 → 1.0 * 0.5 = 0.5
        assert engine.get_modulation_for_generator(0, 60, 100) == 0.5

    def test_modulator_bipolar_to_unipolar_transform(self) -> None:
        """Modulator with bipolar→unipolar transform (2)."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 16384,
            "mod_trans_operator": 2,  # (value + 1) * 0.5
        })
        # source = -1.0 → (-1.0 + 1.0) * 0.5 = 0.0 → 0.0 * 0.5 = 0.0
        assert engine.get_modulation_for_generator(0, 60, 100) == 0.0

    def test_multiple_modulators_sum(self) -> None:
        """Multiple modulators targeting same generator sum their contributions."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,  # -1.0
            "mod_amount": 16384,  # 0.5 → -0.5
            "mod_trans_operator": 0,
        })
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 10,  # -1.0
            "mod_amount": 8192,  # 0.25 → -0.25
            "mod_trans_operator": 0,
        })
        # total = -0.5 + (-0.25) = -0.75
        assert engine.get_modulation_for_generator(0, 60, 100) == -0.75

    def test_modulator_different_destinations(self) -> None:
        """Modulators for different generators don't interfere."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 16384,
            "mod_trans_operator": 0,
        })
        engine.add_modulator({
            "dest_operator": 1,
            "src_operator": 7,
            "mod_amount": 8192,
            "mod_trans_operator": 0,
        })
        # Generator 0 gets -0.5, generator 1 gets -0.25
        assert engine.get_modulation_for_generator(0, 60, 100) == -0.5
        assert engine.get_modulation_for_generator(1, 60, 100) == -0.25

    def test_modulator_amount_scaling(self) -> None:
        """Mod amount is normalized by 32768.0."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 32768,  # 32768 / 32768 = 1.0
            "mod_trans_operator": 0,
        })
        # source = -1.0 → -1.0 * 1.0 = -1.0
        assert engine.get_modulation_for_generator(0, 60, 100) == -1.0

    def test_modulator_negative_amount(self) -> None:
        """Negative mod_amount inverts the modulation."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": -16384,  # -16384 / 32768 = -0.5
            "mod_trans_operator": 0,
        })
        # source = -1.0 → -1.0 * (-0.5) = 0.5
        assert engine.get_modulation_for_generator(0, 60, 100) == 0.5

    def test_unknown_transform_falls_through(self) -> None:
        """Unknown transform type returns value unchanged."""
        engine = SF2ModulationEngine()
        engine.add_modulator({
            "dest_operator": 0,
            "src_operator": 7,
            "mod_amount": 16384,
            "mod_trans_operator": 99,  # unknown → linear
        })
        assert engine.get_modulation_for_generator(0, 60, 100) == -0.5


class TestSF2RealtimeControllerManager:
    """Tests for the SF2 real-time controller manager."""

    @pytest.fixture
    def modulation_engine(self) -> SF2ModulationEngine:
        return SF2ModulationEngine()

    @pytest.fixture
    def manager(self, modulation_engine: SF2ModulationEngine) -> SF2RealtimeControllerManager:
        return SF2RealtimeControllerManager(modulation_engine)

    # --- update_controller ---

    def test_update_controller_cc_7_volume(self, manager: SF2RealtimeControllerManager) -> None:
        """CC 7 (volume) updates and returns in [-1, 1]."""
        manager.update_controller(7, 100, smooth=False)
        value = manager.get_controller_value(7)
        assert isinstance(value, float)
        assert -1.0 <= value <= 1.0

    def test_update_controller_cc_10_pan(self, manager: SF2RealtimeControllerManager) -> None:
        """CC 10 (pan) updates and returns in [-1, 1]."""
        manager.update_controller(10, 64, smooth=False)
        value = manager.get_controller_value(10)
        assert isinstance(value, float)
        assert -1.0 <= value <= 1.0

    def test_update_controller_cc_64_sustain(self, manager: SF2RealtimeControllerManager) -> None:
        """CC 64 (sustain) range check (int input)."""
        manager.update_controller(64, 0, smooth=False)
        assert manager.get_controller_value(64) == -1.0
        manager.update_controller(64, 127, smooth=False)
        assert manager.get_controller_value(64) == 1.0

    # --- Dedicated controller helpers ---

    def test_update_modulation_wheel(self, manager: SF2RealtimeControllerManager) -> None:
        """Modulation wheel updates CC 1 and CC 145 (LFO depth)."""
        manager.update_modulation_wheel(64)
        cc1 = manager.get_controller_value(1)
        assert -1.0 <= cc1 <= 1.0
        cc145 = manager.get_controller_value(145)
        assert cc145 == pytest.approx(64 / 127.0, rel=0.01)

    def test_update_expression(self, manager: SF2RealtimeControllerManager) -> None:
        """Expression controller (CC 11) updates correctly."""
        manager.update_expression(80)
        value = manager.get_controller_value(11)
        assert -1.0 <= value <= 1.0

    def test_update_sustain_pedal_off(self, manager: SF2RealtimeControllerManager) -> None:
        """Sustain pedal < 64 → off (0.0)."""
        manager.update_sustain_pedal(0)
        assert manager.get_controller_value(64) == 0.0

    def test_update_sustain_pedal_on(self, manager: SF2RealtimeControllerManager) -> None:
        """Sustain pedal >= 64 → on (1.0)."""
        manager.update_sustain_pedal(64)
        assert manager.get_controller_value(64) == 1.0

    def test_update_sustain_pedal_max(self, manager: SF2RealtimeControllerManager) -> None:
        """Sustain pedal at max 127 → on (1.0)."""
        manager.update_sustain_pedal(127)
        assert manager.get_controller_value(64) == 1.0

    def test_update_sustain_pedal_threshold(self, manager: SF2RealtimeControllerManager) -> None:
        """Boundary: 63 is off, 64 is on."""
        manager.update_sustain_pedal(63)
        assert manager.get_controller_value(64) == 0.0
        manager.update_sustain_pedal(64)
        assert manager.get_controller_value(64) == 1.0

    # --- Pitch bend ---

    def test_update_pitch_bend_center(self, manager: SF2RealtimeControllerManager) -> None:
        """Pitch bend at center (8192) → 0.0 semitones."""
        manager.update_pitch_bend(8192)
        assert manager.get_controller_value(131) == 0.0

    def test_update_pitch_bend_max(self, manager: SF2RealtimeControllerManager) -> None:
        """Pitch bend at max (16383) with default 12-semitone range."""
        manager.update_pitch_bend(16383)
        assert manager.get_controller_value(131) == pytest.approx(12.0, abs=0.1)

    def test_update_pitch_bend_min(self, manager: SF2RealtimeControllerManager) -> None:
        """Pitch bend at min (0) with default 12-semitone range."""
        manager.update_pitch_bend(0)
        assert manager.get_controller_value(131) == pytest.approx(-12.0, abs=0.1)

    def test_update_pitch_bend_custom_range(self, manager: SF2RealtimeControllerManager) -> None:
        """Pitch bend with custom 24-semitone range."""
        manager.update_pitch_bend(16383, range_semitones=24)
        assert manager.get_controller_value(131) == pytest.approx(24.0, abs=0.1)

    # --- Aftertouch ---

    def test_update_channel_pressure(self, manager: SF2RealtimeControllerManager) -> None:
        """Channel aftertouch (controller 130) updates correctly."""
        manager.update_channel_pressure(64)
        value = manager.get_controller_value(130)
        assert isinstance(value, float)
        assert -1.0 <= value <= 1.0

    def test_update_poly_pressure(self, manager: SF2RealtimeControllerManager) -> None:
        """Polyphonic aftertouch maps to controller 200+note."""
        manager.update_poly_pressure(60, 100)
        value = manager.get_controller_value(260)
        assert value == pytest.approx(100 / 127.0, rel=0.01)

    def test_update_poly_pressure_different_notes(self, manager: SF2RealtimeControllerManager) -> None:
        """Different poly-pressure notes use different controllers."""
        manager.update_poly_pressure(60, 100)
        manager.update_poly_pressure(72, 50)
        assert manager.get_controller_value(260) == pytest.approx(100 / 127.0, rel=0.01)
        assert manager.get_controller_value(272) == pytest.approx(50 / 127.0, rel=0.01)

    # --- get_controller_value ---

    def test_get_controller_value_after_update(self, manager: SF2RealtimeControllerManager) -> None:
        """Returns the last updated normalized value."""
        manager.update_controller(7, 100, smooth=False)
        expected = (100 / 127.0 - 0.5) * 2.0
        assert manager.get_controller_value(7) == pytest.approx(expected, rel=0.01)

    def test_get_controller_value_unset_returns_zero(self, manager: SF2RealtimeControllerManager) -> None:
        """Unset controller returns 0.0."""
        assert manager.get_controller_value(99) == 0.0

    # --- Normalization range ---

    def test_controller_value_zero(self, manager: SF2RealtimeControllerManager) -> None:
        """Raw value 0 maps to -1.0."""
        manager.update_controller(7, 0, smooth=False)
        assert manager.get_controller_value(7) == -1.0

    def test_controller_value_127(self, manager: SF2RealtimeControllerManager) -> None:
        """Raw value 127 maps to 1.0."""
        manager.update_controller(7, 127, smooth=False)
        assert manager.get_controller_value(7) == 1.0

    def test_controller_value_64_near_center(self, manager: SF2RealtimeControllerManager) -> None:
        """Raw value 64 is near 0 (center)."""
        manager.update_controller(7, 64, smooth=False)
        value = manager.get_controller_value(7)
        assert -0.1 < value < 0.1

    def test_controller_values_all_normalize(self, manager: SF2RealtimeControllerManager) -> None:
        """All standard CCs stay within [-1, 1] at min, mid, max."""
        for cc in (0, 1, 7, 10, 11, 64,
                    71, 72, 73, 74, 75, 76, 77, 78, 79,
                    91, 93):
            for raw in (0, 64, 127):
                manager.update_controller(cc, raw, smooth=False)
                assert -1.0 <= manager.get_controller_value(cc) <= 1.0

    # --- Integration ---

    def test_manager_shares_engine(self, modulation_engine: SF2ModulationEngine) -> None:
        """Manager updates propagate to the shared modulation engine."""
        manager = SF2RealtimeControllerManager(modulation_engine)
        manager.update_controller(7, 127, smooth=False)
        assert modulation_engine.get_controller_value(7) == 1.0

    def test_update_controller_with_smoothing(self, manager: SF2RealtimeControllerManager) -> None:
        """Smoothing is applied but value stays in range."""
        manager.update_controller(11, 127, smooth=True)
        value = manager.get_controller_value(11)
        assert isinstance(value, float)
        assert -1.0 <= value <= 1.0

    def test_reset_all_controllers(self, manager: SF2RealtimeControllerManager) -> None:
        """reset_all_controllers clears all stored state."""
        manager.update_controller(7, 100, smooth=False)
        assert manager.get_controller_value(7) != 0.0
        manager.reset_all_controllers()
        assert manager.get_controller_value(7) == 0.0

    def test_reset_all_controllers_pressure(self, manager: SF2RealtimeControllerManager) -> None:
        """reset_all_controllers also resets channel pressure."""
        manager.update_channel_pressure(100)
        manager.reset_all_controllers()
        assert manager.get_controller_value(130) == 0.0

    def test_engine_reset_after_manager_reset(self, modulation_engine: SF2ModulationEngine) -> None:
        """reset_all_controllers on manager resets the underlying engine controllers too."""
        manager = SF2RealtimeControllerManager(modulation_engine)
        manager.update_controller(7, 127, smooth=False)
        assert modulation_engine.get_controller_value(7) == 1.0
        manager.reset_all_controllers()
        assert modulation_engine.get_controller_value(7) == 0.0
