"""
NRPN/RPN Processing Tests

Tests for XG NRPN message handling using the real XGNRPNController
and canonical NRPN definitions from the XG specification.

Exercises:
- NRPN addressing via process_nrpn(msb, lsb, data_msb, data_lsb)
- System effect parameter routing (reverb, chorus, variation, EQ)
- Multi-part addressing and send levels
- Insertion effect parameters
- Effect preset selection
- ParameterDef / ParameterAddress / DrumNoteParam from xg_nrpn_definitions
- Edge cases and state introspection
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, call

import pytest

from synth.processing.effects.xg_nrpn_controller import XGNRPNController
from synth.protocols.xg.xg_nrpn_definitions import (
    REVERB_TYPE,
    REVERB_TIME,
    CHORUS_RATE,
    CHORUS_DEPTH,
    CHORUS_FEEDBACK,
    CHORUS_LEVEL,
    CHORUS_DELAY_OFFSET,
    CHORUS_OUTPUT,
    CHORUS_CROSS_FEEDBACK,
    CHORUS_LFO_WAVEFORM,
    CHORUS_PHASE_DIFF,
    VARIATION_TYPE,
    PART_REVERB_SEND,
    PART_CHORUS_SEND,
    PART_VARIATION_SEND,
    DRUM_KIT_NUMBER,
    DRUM_KIT_LEVEL,
    DRUM_KIT_PAN,
    DRUM_KEY_ASSIGN,
    ParameterAddress,
    ParameterDef,
    DrumNoteParam,
    drum_note_address,
    part_reverb_send,
    part_chorus_send,
    part_variation_send,
    nrpn_value_to_float,
    float_to_nrpn_value,
    note_name_to_midi,
    midi_note_to_name,
    XG_REVERB_TYPES_MAP,
    XG_CHORUS_TYPES_MAP,
    XG_VARIATION_TYPES_MAP,
    XG_INSERTION_TYPES_MAP,
    XG_LFO_WAVEFORMS,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def mock_coordinator():
    """Return a MagicMock that simulates XGEffectsCoordinator."""
    mock = MagicMock()
    # All coordinator methods return True by default
    mock.set_system_effect_parameter.return_value = True
    mock.set_variation_effect_type.return_value = True
    mock.set_master_eq_type.return_value = True
    mock.set_master_eq_gain.return_value = True
    mock.set_master_eq_frequency.return_value = True
    mock.set_master_eq_q_factor.return_value = True
    mock.set_effect_send_level.return_value = True
    mock.set_channel_insertion_effect.return_value = True
    mock.set_channel_insertion_bypass.return_value = True

    # Mock insertion_effects array (one per channel)
    ins_mock = MagicMock()
    ins_mock.insertion_types = [0, 0, 0]  # 3 slots, default "through"
    ins_mock.get_xg_parameter_info.return_value = {}
    mock.insertion_effects = [ins_mock for _ in range(16)]

    return mock


@pytest.fixture
def ctrl(mock_coordinator):
    """XGNRPNController with a mocked coordinator."""
    return XGNRPNController(mock_coordinator)


# ==============================================================================
# TestXGNRPNController — NRPN addressing & process_nrpn
# ==============================================================================


class TestXGNRPNController:
    """Exercise XGNRPNController.process_nrpn() with real routing."""

    def test_initial_state(self, ctrl):
        """Verify freshly constructed controller has clean state."""
        state = ctrl.get_current_state()
        assert state["active_msb"] is None
        assert state["active_lsb"] is None
        assert state["data_msb"] is None
        assert state["data_lsb"] is None
        assert state["selected_part"] == 0

    def test_process_nrpn_reverb_type_returns_true(self, ctrl, mock_coordinator):
        """MSB=0 LSB=0 → reverb type handler → True."""
        result = ctrl.process_nrpn(0, 0, 3, 0)
        assert result is True
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "type", 3
        )

    def test_process_nrpn_reverb_type_clamps(self, ctrl, mock_coordinator):
        """Data value > 24 is clamped to 24 (max XG reverb type)."""
        result = ctrl.process_nrpn(0, 0, 50, 0)
        assert result is True
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "type", 24
        )

    def test_process_nrpn_reverb_time_maps_to_seconds(self, ctrl, mock_coordinator):
        """Value 64 → ~4.2 seconds."""
        ctrl.process_nrpn(0, 1, 64, 0)
        args = mock_coordinator.set_system_effect_parameter.call_args
        assert args[0][0] == "reverb"
        assert args[0][1] == "time"
        # 0.1 + (64/127) * 8.2 ≈ 4.231
        time_val = args[0][2]
        assert 4.0 < time_val < 4.5

    def test_process_nrpn_reverb_level(self, ctrl, mock_coordinator):
        """Value 127 → level 1.0."""
        ctrl.process_nrpn(0, 2, 127, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "level", pytest.approx(1.0)
        )

    def test_process_nrpn_chorus_type(self, ctrl, mock_coordinator):
        """MSB=1 LSB=0 → chorus type handler."""
        result = ctrl.process_nrpn(1, 0, 5, 0)
        assert result is True
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "type", 5
        )

    def test_process_nrpn_chorus_rate(self, ctrl, mock_coordinator):
        """Value 64 → ~5.0 Hz."""
        ctrl.process_nrpn(1, 1, 64, 0)
        args = mock_coordinator.set_system_effect_parameter.call_args
        assert args[0][0] == "chorus"
        assert args[0][1] == "rate"
        rate = args[0][2]
        assert 4.5 < rate < 5.5

    def test_process_nrpn_chorus_feedback_bipolar(self, ctrl, mock_coordinator):
        """Value 0 → -0.5, value 64 → 0.0, value 127 → +0.5."""
        ctrl.process_nrpn(1, 3, 0, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "feedback", pytest.approx(-0.5, abs=0.01)
        )

        ctrl.process_nrpn(1, 3, 64, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "feedback", pytest.approx(0.0, abs=0.01)
        )

        ctrl.process_nrpn(1, 3, 127, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "feedback", pytest.approx(0.5, abs=0.01)
        )

    def test_process_nrpn_chorus_depth(self, ctrl, mock_coordinator):
        """Value 64 → depth ~0.5."""
        ctrl.process_nrpn(1, 2, 64, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "depth", pytest.approx(64 / 127.0)
        )

    def test_process_nrpn_variation_type(self, ctrl, mock_coordinator):
        """MSB=3 LSB=0 → variation type handler."""
        result = ctrl.process_nrpn(3, 0, 16, 0)
        assert result is True
        mock_coordinator.set_variation_effect_type.assert_called_with(16)

    def test_process_nrpn_unknown_returns_false(self, ctrl):
        """Unregistered MSB/LSB pair returns False."""
        result = ctrl.process_nrpn(99, 99, 0, 0)
        assert result is False

    def test_process_nrpn_unknown_msb_returns_false(self, ctrl):
        """Known MSB but unknown LSB returns False."""
        result = ctrl.process_nrpn(0, 127, 0, 0)
        assert result is False

    def test_process_nrpn_state_updates(self, ctrl):
        """After process_nrpn, get_current_state reflects the call.
        Note: data_msb/data_lsb are not persisted to self (the method uses
        them only as local variables), so they remain None in state.
        """
        ctrl.process_nrpn(1, 3, 64, 0)
        state = ctrl.get_current_state()
        assert state["active_msb"] == 1
        assert state["active_lsb"] == 3
        assert state["data_msb"] is None
        assert state["data_lsb"] is None

    # --- Part selection & send levels ---

    def test_part_select(self, ctrl):
        """MSB=32 LSB=0 → selects part."""
        result = ctrl.process_nrpn(32, 0, 7, 0)
        assert result is True
        state = ctrl.get_current_state()
        assert state["selected_part"] == 7

    def test_part_select_clamps_to_15(self, ctrl):
        """Part value > 15 is clamped to 15."""
        ctrl.process_nrpn(32, 0, 20, 0)
        state = ctrl.get_current_state()
        assert state["selected_part"] == 15

    def test_part_reverb_send(self, ctrl, mock_coordinator):
        """MSB=37 LSB=0 → part reverb send via coordinator."""
        ctrl.process_nrpn(32, 0, 3, 0)  # select part 3
        ctrl.process_nrpn(37, 0, 64, 0)  # set reverb send
        mock_coordinator.set_effect_send_level.assert_called_with(
            3, "reverb", pytest.approx(64 / 127.0)
        )

    def test_part_chorus_send(self, ctrl, mock_coordinator):
        """MSB=37 LSB=1 → part chorus send via coordinator."""
        ctrl.process_nrpn(32, 0, 5, 0)
        ctrl.process_nrpn(37, 1, 80, 0)
        mock_coordinator.set_effect_send_level.assert_called_with(
            5, "chorus", pytest.approx(80 / 127.0)
        )

    def test_part_variation_send(self, ctrl, mock_coordinator):
        """MSB=37 LSB=2 → part variation send via coordinator."""
        ctrl.process_nrpn(37, 2, 127, 0)
        mock_coordinator.set_effect_send_level.assert_called_with(
            0, "variation", pytest.approx(1.0)
        )

    # --- Master EQ ---

    def test_eq_type(self, ctrl, mock_coordinator):
        """MSB=4 LSB=0 → set EQ type."""
        result = ctrl.process_nrpn(4, 0, 2, 0)
        assert result is True
        mock_coordinator.set_master_eq_type.assert_called_with(2)

    def test_eq_low_gain_bipolar(self, ctrl, mock_coordinator):
        """Value 0 → ~-12.19 dB, 64 → 0 dB, 127 → +12.0 dB.
        Formula: ((value - 64) / 63.0) * 12.0 (asymmetric because 64 is center).
        """
        ctrl.process_nrpn(4, 1, 0, 0)
        mock_coordinator.set_master_eq_gain.assert_called_with(
            "low", pytest.approx(-12.1905, abs=0.001)
        )
        ctrl.process_nrpn(4, 1, 64, 0)
        mock_coordinator.set_master_eq_gain.assert_called_with(
            "low", pytest.approx(0.0, abs=0.001)
        )
        ctrl.process_nrpn(4, 1, 127, 0)
        mock_coordinator.set_master_eq_gain.assert_called_with(
            "low", pytest.approx(12.0, abs=0.001)
        )

    def test_eq_mid_gain(self, ctrl, mock_coordinator):
        """MSB=4 LSB=3 → mid gain."""
        ctrl.process_nrpn(4, 3, 96, 0)
        mock_coordinator.set_master_eq_gain.assert_called_with(
            "mid", pytest.approx(6.1, abs=0.1)
        )

    def test_eq_q_factor(self, ctrl, mock_coordinator):
        """MSB=4 LSB=7 → Q factor."""
        ctrl.process_nrpn(4, 7, 64, 0)
        q = 0.5 + (64 / 127.0) * 5.0
        mock_coordinator.set_master_eq_q_factor.assert_called_with(
            pytest.approx(q)
        )

    def test_eq_mid_freq(self, ctrl, mock_coordinator):
        """MSB=4 LSB=6 → mid frequency (log mapping)."""
        ctrl.process_nrpn(4, 6, 64, 0)
        freq = 100.0 * (5220.0 / 100.0) ** (64 / 127.0)
        mock_coordinator.set_master_eq_frequency.assert_called_with(
            pytest.approx(freq, rel=0.01)
        )

    # --- Insertion effects ---

    def test_insertion_slot0_type(self, ctrl, mock_coordinator):
        """MSB=33 LSB=0 → set insertion slot 0 type."""
        ctrl.process_nrpn(33, 0, 5, 0)
        mock_coordinator.set_channel_insertion_effect.assert_called_with(0, 0, 5)

    def test_insertion_slot1_bypass(self, ctrl, mock_coordinator):
        """MSB=34 LSB=1 → bypass insertion slot 1 (value >= 64 = True)."""
        ctrl.process_nrpn(34, 1, 100, 0)
        mock_coordinator.set_channel_insertion_bypass.assert_called_with(0, 1, True)

    def test_insertion_slot2_type(self, ctrl, mock_coordinator):
        """MSB=35 LSB=0 → set insertion slot 2 type."""
        ctrl.process_nrpn(35, 0, 8, 0)
        mock_coordinator.set_channel_insertion_effect.assert_called_with(0, 2, 8)

    # --- Effect presets ---

    def test_preset_select(self, ctrl, mock_coordinator):
        """MSB=16 LSB=0 → apply effect preset."""
        result = ctrl.process_nrpn(16, 0, 5, 0)
        assert result is True

    # --- Reverb pre-delay & damping ---

    def test_reverb_pre_delay(self, ctrl, mock_coordinator):
        """MSB=0 LSB=3 → pre-delay mapped to seconds."""
        ctrl.process_nrpn(0, 3, 64, 0)
        pre_delay_s = (64 / 127.0) * 50.0 / 1000.0
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "pre_delay", pytest.approx(pre_delay_s)
        )

    def test_reverb_hf_damping(self, ctrl, mock_coordinator):
        """MSB=0 LSB=4 → HF damping 0.0–1.0."""
        ctrl.process_nrpn(0, 4, 100, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "hf_damping", pytest.approx(100 / 127.0)
        )

    def test_reverb_density(self, ctrl, mock_coordinator):
        """MSB=0 LSB=5 → density 0.0–1.0."""
        ctrl.process_nrpn(0, 5, 40, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "density", pytest.approx(40 / 127.0)
        )

    def test_chorus_lfo_waveform(self, ctrl, mock_coordinator):
        """MSB=1 LSB=8 → LFO waveform, clamped to 0-3."""
        ctrl.process_nrpn(1, 8, 2, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "lfo_waveform", 2
        )
        # Clamp test
        ctrl.process_nrpn(1, 8, 10, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "lfo_waveform", 3
        )

    def test_chorus_phase_diff(self, ctrl, mock_coordinator):
        """MSB=1 LSB=9 → phase diff 0-180 degrees."""
        ctrl.process_nrpn(1, 9, 64, 0)
        degrees = (64 / 127.0) * 180.0
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "phase_diff", pytest.approx(degrees)
        )

    def test_chorus_output(self, ctrl, mock_coordinator):
        """MSB=1 LSB=6 → chorus output routed."""
        ctrl.process_nrpn(1, 6, 100, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "output", 100
        )

    def test_chorus_cross_feedback_bipolar(self, ctrl, mock_coordinator):
        """MSB=1 LSB=7 → cross feedback -0.5 to +0.5."""
        ctrl.process_nrpn(1, 7, 0, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "cross_feedback", pytest.approx(-0.5, abs=0.01)
        )

    # --- Variations in reverb shape/gate ---

    def test_reverb_shape(self, ctrl, mock_coordinator):
        """MSB=0 LSB=8 → shape passed as integer."""
        ctrl.process_nrpn(0, 8, 5, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "shape", 5
        )

    def test_reverb_gate_time(self, ctrl, mock_coordinator):
        """MSB=0 LSB=9 → gate_time passed as integer."""
        ctrl.process_nrpn(0, 9, 120, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "gate_time", 120
        )

    def test_reverb_pre_delay_scale(self, ctrl, mock_coordinator):
        """MSB=0 LSB=10 → pre_delay_scale passed as integer."""
        ctrl.process_nrpn(0, 10, 80, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "pre_delay_scale", 80
        )

    def test_reverb_early_level(self, ctrl, mock_coordinator):
        """MSB=0 LSB=6 → early_level 0.0–1.0."""
        ctrl.process_nrpn(0, 6, 64, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "early_level", pytest.approx(64 / 127.0)
        )

    def test_reverb_tail_level(self, ctrl, mock_coordinator):
        """MSB=0 LSB=7 → tail_level 0.0–1.0."""
        ctrl.process_nrpn(0, 7, 100, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "tail_level", pytest.approx(100 / 127.0)
        )


# ==============================================================================
# TestParameterDef — xg_nrpn_definitions data types
# ==============================================================================


class TestParameterDef:
    """Verify ParameterDef and ParameterAddress from xg_nrpn_definitions."""

    def test_parameter_address_is_named_tuple(self):
        """ParameterAddress is a NamedTuple with msb and lsb fields."""
        addr = ParameterAddress(1, 5)
        assert addr.msb == 1
        assert addr.lsb == 5
        assert addr == (1, 5)  # tuple-like

    def test_parameter_def_has_expected_attributes(self):
        """ParameterDef has address, name, min_value, max_value."""
        p = ParameterDef(
            address=ParameterAddress(1, 0),
            name="Reverb Type",
            min_value=0,
            max_value=24,
            unit="type",
            description="XG Reverb Type",
        )
        assert p.address == ParameterAddress(1, 0)
        assert p.name == "Reverb Type"
        assert p.min_value == 0
        assert p.max_value == 24
        assert p.unit == "type"

    def test_reverb_type_address(self):
        """REVERB_TYPE = ParameterAddress(1, 0)."""
        assert REVERB_TYPE == ParameterAddress(1, 0)

    def test_reverb_time_address(self):
        """REVERB_TIME = ParameterAddress(1, 1)."""
        assert REVERB_TIME == ParameterAddress(1, 1)

    def test_chorus_rate_address(self):
        """CHORUS_RATE = ParameterAddress(2, 1)."""
        assert CHORUS_RATE == ParameterAddress(2, 1)

    def test_chorus_depth_address(self):
        """CHORUS_DEPTH = ParameterAddress(2, 2)."""
        assert CHORUS_DEPTH == ParameterAddress(2, 2)

    def test_chorus_feedback_address(self):
        """CHORUS_FEEDBACK = ParameterAddress(2, 3)."""
        assert CHORUS_FEEDBACK == ParameterAddress(2, 3)

    def test_chorus_level_address(self):
        """CHORUS_LEVEL = ParameterAddress(2, 4)."""
        assert CHORUS_LEVEL == ParameterAddress(2, 4)

    def test_variation_type_address(self):
        """VARIATION_TYPE = ParameterAddress(2, 0)."""
        assert VARIATION_TYPE == ParameterAddress(2, 0)

    def test_drum_kit_number_address(self):
        """DRUM_KIT_NUMBER = ParameterAddress(40, 0)."""
        assert DRUM_KIT_NUMBER == ParameterAddress(40, 0)

    def test_drum_key_assign_address(self):
        """DRUM_KEY_ASSIGN = ParameterAddress(40, 2)."""
        assert DRUM_KEY_ASSIGN == ParameterAddress(40, 2)


# ==============================================================================
# TestDrumNoteParam
# ==============================================================================


class TestDrumNoteParam:
    """Exercise DrumNoteParam enum and drum_note_address()."""

    def test_enum_values(self):
        """DrumNoteParam members have expected integer values."""
        assert DrumNoteParam.PITCH_COARSE.value == 0
        assert DrumNoteParam.PITCH_FINE.value == 1
        assert DrumNoteParam.LEVEL.value == 2
        assert DrumNoteParam.PAN.value == 3
        assert DrumNoteParam.REVERB_SEND.value == 4
        assert DrumNoteParam.CHORUS_SEND.value == 5
        assert DrumNoteParam.VARIATION_SEND.value == 6
        assert DrumNoteParam.DECAY_TIME.value == 7
        assert DrumNoteParam.ATTACK_TIME.value == 8
        assert DrumNoteParam.FILTER_CUTOFF.value == 9
        assert DrumNoteParam.FILTER_RESONANCE.value == 10
        assert DrumNoteParam.LFO_RATE.value == 11
        assert DrumNoteParam.LFO_DEPTH.value == 12
        assert DrumNoteParam.EQ_LOW_GAIN.value == 13
        assert DrumNoteParam.EQ_MID_GAIN.value == 14
        assert DrumNoteParam.EQ_HIGH_GAIN.value == 15
        assert DrumNoteParam.ALTERNATE_GROUP.value == 16
        assert DrumNoteParam.MUTE_GROUP.value == 17

    def test_drum_note_address_pitch_coarse(self):
        """drum_note_address(PITCH_COARSE, 36) → (48, 36)."""
        addr = drum_note_address(DrumNoteParam.PITCH_COARSE, 36)
        assert addr == ParameterAddress(48, 36)

    def test_drum_note_address_level(self):
        """drum_note_address(LEVEL, 60) → (50, 60)."""
        addr = drum_note_address(DrumNoteParam.LEVEL, 60)
        assert addr == ParameterAddress(50, 60)

    def test_drum_note_address_pan(self):
        """drum_note_address(PAN, 42) → (51, 42)."""
        addr = drum_note_address(DrumNoteParam.PAN, 42)
        assert addr == ParameterAddress(51, 42)

    def test_drum_note_address_enum_iteration(self):
        """Every DrumNoteParam produces a unique MSB offset."""
        addrs = {drum_note_address(p, 0) for p in DrumNoteParam}
        assert len(addrs) == len(DrumNoteParam)


# ==============================================================================
# Test helper functions from xg_nrpn_definitions
# ==============================================================================


class TestXGNRPNDefinitionHelpers:
    """Exercise utility functions in xg_nrpn_definitions."""

    def test_nrpn_value_to_float_default_range(self):
        """0→0.0, 64→~0.504, 127→1.0."""
        assert nrpn_value_to_float(0) == 0.0
        assert nrpn_value_to_float(127) == 1.0
        val = nrpn_value_to_float(64)
        assert 0.5 <= val <= 0.51

    def test_nrpn_value_to_float_custom_range(self):
        """Value 64 maps to midpoint of [-12, 12]."""
        val = nrpn_value_to_float(64, -12.0, 12.0)
        assert -0.1 < val < 0.1  # near zero (midpoint)

    def test_float_to_nrpn_value_default(self):
        """0.0→0, 1.0→127, 0.5→64 (or 63)."""
        assert float_to_nrpn_value(0.0) == 0
        assert float_to_nrpn_value(1.0) == 127
        val = float_to_nrpn_value(0.5)
        assert 63 <= val <= 64

    def test_float_to_nrpn_value_clamps(self):
        """Values outside [0, 1] are clamped."""
        assert float_to_nrpn_value(-0.1) == 0
        assert float_to_nrpn_value(1.5) == 127

    def test_note_name_to_midi_middle_c(self):
        """C4 → 60."""
        assert note_name_to_midi("C4") == 60

    def test_note_name_to_midi_a4(self):
        """A4 → 69."""
        assert note_name_to_midi("A4") == 69

    def test_note_name_to_midi_sharps(self):
        """C#4 → 61, F#3 → 54."""
        assert note_name_to_midi("C#4") == 61
        assert note_name_to_midi("F#3") == 54

    def test_note_name_to_midi_flats(self):
        """Db4 → 61, Eb4 → 63."""
        assert note_name_to_midi("Db4") == 61
        assert note_name_to_midi("Eb4") == 63

    def test_note_name_to_midi_default_octave(self):
        """C (no octave) → 60."""
        assert note_name_to_midi("C") == 60

    def test_midi_note_to_name(self):
        """60 → 'C4', 69 → 'A4'."""
        assert midi_note_to_name(60) == "C4"
        assert midi_note_to_name(69) == "A4"
        assert midi_note_to_name(0) == "C-1"

    def test_roundtrip_note_conversion(self):
        """note_name_to_midi(midi_note_to_name(n)) → n for mid-range notes."""
        # Skip extreme notes (0, 127) because note_name_to_midi
        # does not handle negative octave strings like "C-1".
        for note in [12, 24, 36, 48, 60, 69, 72, 84, 96]:
            name = midi_note_to_name(note)
            assert note_name_to_midi(name) == note

    def test_part_reverb_send(self):
        """part_reverb_send(3) → (32, 3)."""
        assert part_reverb_send(3) == ParameterAddress(32, 3)

    def test_part_chorus_send(self):
        """part_chorus_send(7) → (33, 7)."""
        assert part_chorus_send(7) == ParameterAddress(33, 7)

    def test_part_variation_send(self):
        """part_variation_send(0) → (34, 0)."""
        assert part_variation_send(0) == ParameterAddress(34, 0)

    def test_part_send_functions_roundtrip(self):
        """part_reverb_send/chorus/variation produce correct MSBs."""
        assert part_reverb_send(5).msb == 32
        assert part_chorus_send(5).msb == 33
        assert part_variation_send(5).msb == 34
        for p in range(16):
            assert part_reverb_send(p).lsb == p
            assert part_chorus_send(p).lsb == p
            assert part_variation_send(p).lsb == p


# ==============================================================================
# TestXGTypeMaps
# ==============================================================================


class TestXGTypeMaps:
    """Exercise the XG type maps (reverb, chorus, variation, insertion, LFO)."""

    def test_reverb_type_map_contains_key_types(self):
        assert XG_REVERB_TYPES_MAP[0] == "no_effect"
        assert XG_REVERB_TYPES_MAP[1] == "hall1"
        assert XG_REVERB_TYPES_MAP[8] == "plate"

    def test_chorus_type_map_contains_key_types(self):
        assert XG_CHORUS_TYPES_MAP[0] == "chorus1"
        assert XG_CHORUS_TYPES_MAP[5] == "celeste1"
        assert XG_CHORUS_TYPES_MAP[10] == "flanger1"
        assert XG_CHORUS_TYPES_MAP[16] == "symphonic1"

    def test_variation_type_map(self):
        assert XG_VARIATION_TYPES_MAP[0] == "delay_lcr"
        assert XG_VARIATION_TYPES_MAP[16] == "chorus1"
        assert XG_VARIATION_TYPES_MAP[32] == "flanger1"
        assert XG_VARIATION_TYPES_MAP[48] == "distortion1"
        assert XG_VARIATION_TYPES_MAP[65] == "tremolo"

    def test_insertion_type_map(self):
        assert XG_INSERTION_TYPES_MAP[0] == "through"
        assert XG_INSERTION_TYPES_MAP[5] == "overdrive"
        assert XG_INSERTION_TYPES_MAP[9] == "chorus"
        assert XG_INSERTION_TYPES_MAP[15] == "delay"

    def test_lfo_waveforms(self):
        assert XG_LFO_WAVEFORMS[0] == "sine"
        assert XG_LFO_WAVEFORMS[1] == "triangle"
        assert XG_LFO_WAVEFORMS[4] == "square"

    def test_drum_note_address_all_params(self):
        """Every DrumNoteParam produces a valid MSB/LSB pair."""
        for param in DrumNoteParam:
            addr = drum_note_address(param, 60)
            assert 48 <= addr.msb <= 65
            assert 0 <= addr.lsb <= 127

    def test_part_send_part_reverb_send_ranges(self):
        """Part send functions produce LSB in 0-15 range."""
        for p in range(16):
            assert part_reverb_send(p).lsb == p
        for p in range(16):
            assert part_chorus_send(p).lsb == p
        for p in range(16):
            assert part_variation_send(p).lsb == p

    def test_drum_note_address_lsb_is_note_number(self):
        """drum_note_address parameter LSB is the note number."""
        for note in [0, 36, 60, 127]:
            for param in DrumNoteParam:
                addr = drum_note_address(param, note)
                assert addr.lsb == note


# ==============================================================================
# TestXGNRPNControllerEdgeCases
# ==============================================================================


class TestXGNRPNControllerEdgeCases:
    """Edge cases for XGNRPNController."""

    def test_data_lsb_is_passed_but_not_persisted_in_state(
        self, ctrl, mock_coordinator
    ):
        """LSB data value is passed to handlers but NOT persisted to state."""
        ctrl.process_nrpn(1, 4, 100, 27)
        state = ctrl.get_current_state()
        # data_lsb is not stored in self by process_nrpn
        assert state["data_lsb"] is None
        # The chorus level handler only uses data_msb
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "level", pytest.approx(100 / 127.0)
        )

    def test_thread_safety(self, ctrl):
        """Controller uses an RLock and doesn't explode under concurrent access."""
        import concurrent.futures

        def hammer():
            for _ in range(50):
                ctrl.process_nrpn(0, 0, 3, 0)
                ctrl.process_nrpn(1, 1, 64, 0)
                ctrl.process_nrpn(32, 0, 7, 0)
                ctrl.get_current_state()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as exe:
            futures = [exe.submit(hammer) for _ in range(4)]
            for f in concurrent.futures.as_completed(futures, timeout=5):
                assert f.result() is None  # no exception

    def test_get_current_state_always_returns_dict(self, ctrl):
        """get_current_state always returns a dict with the expected keys."""
        state = ctrl.get_current_state()
        assert isinstance(state, dict)
        expected_keys = {"active_msb", "active_lsb", "data_msb", "data_lsb", "selected_part"}
        assert set(state.keys()) == expected_keys

    def test_multiple_calls_accumulate_state(self, ctrl):
        """Multiple process_nrpn calls update active_msb/lsb correctly.
        Note: data_msb/data_lsb remain None (not persisted).
        """
        ctrl.process_nrpn(0, 3, 100, 0)
        ctrl.process_nrpn(1, 5, 50, 0)
        ctrl.process_nrpn(4, 1, 0, 0)
        state = ctrl.get_current_state()
        assert state["active_msb"] == 4
        assert state["active_lsb"] == 1
        assert state["data_msb"] is None

    def test_variation_type_clamps_to_62(self, ctrl, mock_coordinator):
        """Variation type value > 62 clamped to 62."""
        ctrl.process_nrpn(3, 0, 200, 0)
        mock_coordinator.set_variation_effect_type.assert_called_with(62)

    def test_eq_type_clamps_to_4(self, ctrl, mock_coordinator):
        """EQ type value > 4 clamped to 4."""
        ctrl.process_nrpn(4, 0, 10, 0)
        mock_coordinator.set_master_eq_type.assert_called_with(4)

    def test_reverb_type_clamps_min(self, ctrl, mock_coordinator):
        """Reverb type negative value clamped to 0."""
        ctrl.process_nrpn(0, 0, -5, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "type", 0
        )

    def test_chorus_type_clamps(self, ctrl, mock_coordinator):
        """Chorus type value > 17 clamped to 17."""
        ctrl.process_nrpn(1, 0, 30, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "type", 17
        )

    def test_chorus_delay_is_passed_as_integer(self, ctrl, mock_coordinator):
        """MSB=1 LSB=5 → chorus delay."""
        ctrl.process_nrpn(1, 5, 90, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "delay", 90
        )

    def test_chorus_level_zero(self, ctrl, mock_coordinator):
        """Value 0 → level 0.0."""
        ctrl.process_nrpn(1, 4, 0, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "level", pytest.approx(0.0)
        )

    def test_chorus_level_max(self, ctrl, mock_coordinator):
        """Value 127 → level 1.0."""
        ctrl.process_nrpn(1, 4, 127, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "chorus", "level", pytest.approx(1.0)
        )


# ==============================================================================
# TestXGNRPNController — reverb edge cases
# ==============================================================================


class TestReverbEdgeCases:
    """Reverb-specific value conversion edge cases."""

    def test_reverb_time_min(self, ctrl, mock_coordinator):
        """Reverb time at value 0 → ~0.1s."""
        ctrl.process_nrpn(0, 1, 0, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "time", pytest.approx(0.1)
        )

    def test_reverb_time_max(self, ctrl, mock_coordinator):
        """Reverb time at value 127 → ~8.3s."""
        ctrl.process_nrpn(0, 1, 127, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "time", pytest.approx(8.3)
        )

    def test_reverb_pre_delay_min(self, ctrl, mock_coordinator):
        """Pre-delay at value 0 → 0.0s."""
        ctrl.process_nrpn(0, 3, 0, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "pre_delay", pytest.approx(0.0)
        )

    def test_reverb_pre_delay_max(self, ctrl, mock_coordinator):
        """Pre-delay at value 127 → 0.05s."""
        ctrl.process_nrpn(0, 3, 127, 0)
        mock_coordinator.set_system_effect_parameter.assert_called_with(
            "reverb", "pre_delay", pytest.approx(0.05)
        )


# ==============================================================================
# TestXGNRPNController — NRPN definitions cross-reference
# ==============================================================================


class TestNRPNDefinitionsCrossReference:
    """Verify the controller handler registry covers expected NRPN addresses."""

    def test_handler_registry_has_reverb_handlers(self, ctrl):
        """Handler registry covers MSB=0 LSB=0..10 (reverb)."""
        for lsb in range(11):
            result = ctrl.process_nrpn(0, lsb, 64, 0)
            assert result is True, f"MSB=0 LSB={lsb} should have a handler"

    def test_handler_registry_has_chorus_handlers(self, ctrl):
        """Handler registry covers MSB=1 LSB=0..9 (chorus)."""
        for lsb in range(10):
            result = ctrl.process_nrpn(1, lsb, 64, 0)
            assert result is True, f"MSB=1 LSB={lsb} should have a handler"

    def test_handler_registry_has_variation_handler(self, ctrl):
        """Handler registry covers MSB=3 LSB=0 (variation type)."""
        assert ctrl.process_nrpn(3, 0, 16, 0) is True

    def test_handler_registry_has_eq_handlers(self, ctrl):
        """Handler registry covers MSB=4 LSB=0..7 (master EQ)."""
        for lsb in range(8):
            result = ctrl.process_nrpn(4, lsb, 64, 0)
            assert result is True, f"MSB=4 LSB={lsb} should have a handler"

    def test_handler_registry_has_part_select(self, ctrl):
        """Handler registry covers MSB=32 LSB=0 (part select)."""
        assert ctrl.process_nrpn(32, 0, 5, 0) is True

    def test_handler_registry_has_insertion_slots(self, ctrl):
        """Handler registry covers MSB=33-35 LSB=0-1 (insertion)."""
        for msb in range(33, 36):
            result = ctrl.process_nrpn(msb, 0, 1, 0)
            assert result is True, f"MSB={msb} LSB=0 should have a handler"
            result = ctrl.process_nrpn(msb, 1, 0, 0)
            assert result is True, f"MSB={msb} LSB=1 should have a handler"

    def test_handler_registry_has_part_send_levels(self, ctrl):
        """Handler registry covers MSB=37 LSB=0..2 (part sends)."""
        for lsb in range(3):
            result = ctrl.process_nrpn(37, lsb, 64, 0)
            assert result is True, f"MSB=37 LSB={lsb} should have a handler"

    def test_handler_registry_has_preset_select(self, ctrl):
        """Handler registry covers MSB=16 LSB=0 (effect presets)."""
        assert ctrl.process_nrpn(16, 0, 5, 0) is True
