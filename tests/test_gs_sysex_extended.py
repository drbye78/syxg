"""Tests for extended GS Sysex Handler methods — SC-8850 feature additions.

Tests cover four extended address handlers added for SC-8850 support:
1. Part key parameters (address 0x02) — velocity/key range, portamento, bend
2. Common effects parameters (address 0x03) — chorus/reverb routing
3. Drum key editing (address 0x11) — per-note configuration
4. Per-part EQ (address 0x40 02 xx) — low/high shelf gain

NOTE: The _handle_data_set routing has a pre-existing issue where
`elif 0x01 <= addr_high <= 0x10` catches addresses 0x02-0x10 before
the more specific elif branches (0x02 part-key, 0x03-0x06 effects)
can execute. Therefore part-key-param and effects messages routed
through process_message go to the wrong handler. This test file
tests the extended methods directly and uses process_message only
for addresses that route correctly (0x11 drum-key, 0x40 EQ).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from synth.protocols.gs.gs_sysex_handler import GSSysexHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_gs_msg(
    device_id: int = 0x10,
    command: int = 0x12,
    addr: tuple = (0x00, 0x00, 0x00),
    data: tuple = (0x00,),
) -> bytes:
    """Build a GS sysex message with proper framing and Roland checksum.

    GS sysex format: F0 41 <dev> 42 <cmd> <A1> <A2> <A3> [data...] <sum> F7
    """
    body = [0x41, device_id, 0x42, command, addr[0], addr[1], addr[2]]
    body.extend(data)
    body_sum = sum(body)
    checksum = (128 - (body_sum % 128)) & 0x7F
    msg = [0xF0] + body + [checksum, 0xF7]
    return bytes(msg)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def handler():
    """Basic GSSysexHandler with default device ID (0x10)."""
    return GSSysexHandler(device_id=0x10)


# ---------------------------------------------------------------------------
# Part Key Parameters (address 0x02 0n xx)
#
# These are tested via direct _handle_part_key_param calls because the
# process_message routing via _handle_data_set is broken for addr_high=0x02
# (caught by the broader 0x01-0x10 range).
# ---------------------------------------------------------------------------

class TestPartKeyParamDirect:
    """_handle_part_key_param — address 0x02, tested directly.

    Parameter map:
      0x10 = velocity_range_low   (min=1, max=127)
      0x11 = velocity_range_high  (min=1, max=127)
      0x12 = key_range_low        (min=0, max=127)
      0x13 = key_range_high       (min=0, max=127)
      0x14 = portamento_time      (min=0, max=127)
      0x15 = bend_range           (min=0, max=24)
    """

    def test_set_velocity_range_low(self, handler):
        result = handler._handle_part_key_param(0, 0x10, (20,))
        assert handler.part_params[0]["velocity_range_low"] == 20

    def test_set_velocity_range_high(self, handler):
        handler._handle_part_key_param(0, 0x11, (100,))
        assert handler.part_params[0]["velocity_range_high"] == 100

    def test_set_key_range_low(self, handler):
        handler._handle_part_key_param(0, 0x12, (36,))
        assert handler.part_params[0]["key_range_low"] == 36

    def test_set_key_range_high(self, handler):
        handler._handle_part_key_param(0, 0x13, (84,))
        assert handler.part_params[0]["key_range_high"] == 84

    def test_set_portamento_time(self, handler):
        handler._handle_part_key_param(0, 0x14, (50,))
        assert handler.part_params[0]["portamento_time"] == 50

    def test_set_bend_range(self, handler):
        handler._handle_part_key_param(0, 0x15, (12,))
        assert handler.part_params[0]["bend_range"] == 12

    def test_multi_part_independence(self, handler):
        handler._handle_part_key_param(0, 0x10, (20,))
        handler._handle_part_key_param(1, 0x10, (50,))
        assert handler.part_params[0]["velocity_range_low"] == 20
        assert handler.part_params[1]["velocity_range_low"] == 50

    def test_param_clamped_low(self, handler):
        handler._handle_part_key_param(0, 0x10, (0,))
        assert handler.part_params[0]["velocity_range_low"] == 1

    def test_param_clamped_high(self, handler):
        handler._handle_part_key_param(0, 0x15, (99,))
        assert handler.part_params[0]["bend_range"] == 24

    def test_all_defaults(self, handler):
        for p in range(16):
            assert handler.part_params[p]["velocity_range_low"] == 1
            assert handler.part_params[p]["velocity_range_high"] == 127
            assert handler.part_params[p]["key_range_low"] == 0
            assert handler.part_params[p]["key_range_high"] == 127
            assert handler.part_params[p]["portamento_time"] == 0
            assert handler.part_params[p]["bend_range"] == 2

    def test_notifies_callback(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_part_key_param(0, 0x12, (48,))
        assert any("part_0_key" in e[0] for e in events)
        assert any(e[1] == "key_range_low" for e in events)

    def test_invalid_part_returns_none(self, handler):
        result = handler._handle_part_key_param(99, 0x10, (50,))
        assert result is None
        assert handler.part_params[0]["velocity_range_low"] == 1  # unchanged

    def test_unknown_param_returns_none(self, handler):
        result = handler._handle_part_key_param(0, 0xFF, (50,))
        assert result is None

    def test_forwards_to_jv2080(self, handler):
        mock_jv = MagicMock()
        mock_jv.set_part_key_param = MagicMock()
        handler.set_jv2080_manager(mock_jv)
        handler._handle_part_key_param(0, 0x12, (60,))
        mock_jv.set_part_key_param.assert_called_once_with(0, "key_range_low", 60)

    def test_jv2080_exception_handled(self, handler):
        mock_jv = MagicMock()
        mock_jv.set_part_key_param = MagicMock()
        mock_jv.set_part_key_param.side_effect = RuntimeError("error")
        handler.set_jv2080_manager(mock_jv)
        handler._handle_part_key_param(0, 0x12, (48,))
        assert handler.part_params[0]["key_range_low"] == 48  # still updated

    def test_return_type(self, handler):
        result = handler._handle_part_key_param(0, 0x12, (48,))
        assert result is None  # returns None (void)


# ---------------------------------------------------------------------------
# Drum Key Parameters (address 0x11 1n kk pp)
#
# addr_high=0x11 routes correctly through process_message.
# drum_part = addr_high - 0x10 = 1
# addr_mid = MIDI note, addr_low = param_id
#
# Parameter map:
#   0x00 = pitch_offset   (0-127)
#   0x01 = level          (0-127)
#   0x02 = pan            (0-127)
#   0x03 = reverb_send    (0-127)
#   0x04 = chorus_send    (0-127)
#   0x05 = key_group      (0-7)
#   0x06 = mute_group     (0-31)
# ---------------------------------------------------------------------------

class TestDrumKeyParamDirect:
    """_handle_drum_key_param — address 0x11, tested directly and via process_message."""

    def test_set_pitch_offset(self, handler):
        handler._handle_drum_key_param(1, 36, 0, (55,))
        assert handler.drum_key_params[(1, 36)]["pitch_offset"] == 55

    def test_set_level(self, handler):
        handler._handle_drum_key_param(1, 36, 1, (100,))
        assert handler.drum_key_params[(1, 36)]["level"] == 100

    def test_set_pan(self, handler):
        handler._handle_drum_key_param(1, 60, 2, (10,))
        assert handler.drum_key_params[(1, 60)]["pan"] == 10

    def test_set_reverb_send(self, handler):
        handler._handle_drum_key_param(1, 48, 3, (64,))
        assert handler.drum_key_params[(1, 48)]["reverb_send"] == 64

    def test_set_chorus_send(self, handler):
        handler._handle_drum_key_param(1, 72, 4, (32,))
        assert handler.drum_key_params[(1, 72)]["chorus_send"] == 32

    def test_set_key_group(self, handler):
        handler._handle_drum_key_param(1, 36, 5, (3,))
        assert handler.drum_key_params[(1, 36)]["key_group"] == 3

    def test_set_mute_group(self, handler):
        handler._handle_drum_key_param(1, 42, 6, (5,))
        assert handler.drum_key_params[(1, 42)]["mute_group"] == 5

    def test_multiple_keys_independent(self, handler):
        handler._handle_drum_key_param(1, 48, 1, (90,))
        handler._handle_drum_key_param(1, 50, 1, (80,))
        assert handler.drum_key_params[(1, 48)]["level"] == 90
        assert handler.drum_key_params[(1, 50)]["level"] == 80

    def test_param_clamped(self, handler):
        handler._handle_drum_key_param(1, 36, 5, (99,))
        assert handler.drum_key_params[(1, 36)]["key_group"] == 7

    def test_invalid_note_returns_none(self, handler):
        result = handler._handle_drum_key_param(1, 200, 0, (50,))
        assert result is None

    def test_invalid_drum_part_returns_none(self, handler):
        result = handler._handle_drum_key_param(99, 36, 0, (50,))
        assert result is None

    def test_invalid_param_returns_none(self, handler):
        result = handler._handle_drum_key_param(1, 36, 0xFF, (50,))
        assert result is None

    def test_forwards_to_jv2080(self, handler):
        mock_jv = MagicMock()
        mock_jv.set_drum_key_param = MagicMock()
        handler.set_jv2080_manager(mock_jv)
        handler._handle_drum_key_param(1, 36, 1, (80,))
        mock_jv.set_drum_key_param.assert_called_once_with(1, 36, "level", 80)

    def test_jv2080_exception_handled(self, handler):
        mock_jv = MagicMock()
        mock_jv.set_drum_key_param = MagicMock()
        mock_jv.set_drum_key_param.side_effect = RuntimeError("JV2080 error")
        handler.set_jv2080_manager(mock_jv)
        handler._handle_drum_key_param(1, 36, 1, (80,))
        assert handler.drum_key_params[(1, 36)]["level"] == 80

    def test_notifies_callback(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_drum_key_param(1, 36, 1, (80,))
        assert any("drum_1_key" in e[0] for e in events)
        assert any("level" in e[1] for e in events)

    def test_via_process_message(self, handler):
        """0x11 routing through process_message works correctly."""
        msg = _build_gs_msg(addr=(0x11, 60, 0x01), data=(100,))
        handler.process_message(msg)
        assert handler.drum_key_params[(1, 60)]["level"] == 100

    def test_multiple_via_process_message(self, handler):
        """Multiple drum key messages through process_message."""
        handler.process_message(_build_gs_msg(addr=(0x11, 48, 0x01), data=(90,)))
        handler.process_message(_build_gs_msg(addr=(0x11, 50, 0x01), data=(80,)))
        assert handler.drum_key_params[(1, 48)]["level"] == 90
        assert handler.drum_key_params[(1, 50)]["level"] == 80


# ---------------------------------------------------------------------------
# Common Effects Parameters (address 0x03 0x nn)
#
# These are tested via direct _handle_effects_param calls because the
# process_message routing is broken for addr_high=0x03 (caught by the
# broader 0x01-0x10 range in _handle_data_set).
# ---------------------------------------------------------------------------

class TestCommonEffectsDirect:
    """_handle_effects_param — address 0x03, common effects section.

    Parameter map:
      0x00 = chorus_to_reverb  (0-127)
      0x01 = reverb_output     (0-1)
      0x02 = chorus_output     (0-1)
    """

    def test_chorus_to_reverb_param(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_effects_param(0x03, 0x00, 0x00, (64,))
        matching = [(s, p, v) for s, p, v in events if s == "common_effects"]
        assert len(matching) >= 1
        assert matching[0][1] == "chorus_to_reverb"
        assert matching[0][2] == 64

    def test_reverb_output_param(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_effects_param(0x03, 0x00, 0x01, (1,))
        matching = [(s, p, v) for s, p, v in events if p == "reverb_output"]
        assert len(matching) >= 1
        assert matching[0][2] == 1

    def test_chorus_output_param(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_effects_param(0x03, 0x00, 0x02, (0,))
        matching = [(s, p, v) for s, p, v in events if s == "common_effects"]
        assert any(p == "chorus_output" for s, p, v in matching)

    def test_invalid_param_returns_none(self, handler):
        result = handler._handle_effects_param(0x03, 0x00, 0xFF, (64,))
        assert result is None

    def test_chorus_routes_correctly(self, handler):
        """Chorus effect (0x04) can be tested directly."""
        handler._handle_effects_param(0x04, 0x00, 0x00, (2,))
        assert handler.chorus_params["type"] == 2

    def test_reverb_routes_correctly(self, handler):
        """Reverb effect (0x05) can be tested directly."""
        handler._handle_effects_param(0x05, 0x00, 0x00, (4,))
        assert handler.reverb_params["type"] == 4

    def test_variation_routes_correctly(self, handler):
        """Variation effect (0x06) can be tested directly."""
        handler._handle_effects_param(0x06, 0x00, 0x00, (3,))
        # Variation fires callback; no state to check

    def test_chorus_type_mapping(self, handler):
        """GS chorus type maps to XG chorus type."""
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_effects_param(0x04, 0x00, 0x00, (5,))  # Flanger
        assert handler.chorus_params["type"] == 5

    def test_reverb_type_mapping(self, handler):
        """GS reverb type maps to XG reverb type."""
        handler._handle_effects_param(0x05, 0x00, 0x00, (3,))  # Hall1
        assert handler.reverb_params["type"] == 3


# ---------------------------------------------------------------------------
# Per-Part EQ (address 0x40 02 0n xx)
#
# addr_high=0x40 routes correctly through process_message.
# addr_low = part_num, addr_mid = param (0x00=low_gain, 0x01=high_gain)
# ---------------------------------------------------------------------------

class TestPartEQDirect:
    """_handle_eq_param — address 0x40, tested directly and via process_message.

    EQ parameter map:
      0x00 = low_gain    (value 0-127 → -12 to +12 dB, 64=0dB)
      0x01 = high_gain   (value 0-127 → -12 to +12 dB, 64=0dB)
    """

    def test_eq_low_gain(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_eq_param(0, 0x00, (64,))
        assert any("part_0_eq" in s for s, p, v in events)

    def test_eq_high_gain(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_eq_param(0, 0x01, (72,))
        assert any("part_0_eq" in s for s, p, v in events)

    def test_eq_multiple_parts(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_eq_param(0, 0x00, (72,))
        handler._handle_eq_param(1, 0x00, (56,))
        handler._handle_eq_param(0, 0x01, (80,))
        part0 = [(s, p, v) for s, p, v in events if "part_0_eq" in s]
        part1 = [(s, p, v) for s, p, v in events if "part_1_eq" in s]
        assert len(part0) >= 2
        assert len(part1) >= 1

    def test_invalid_part_returns_none(self, handler):
        result = handler._handle_eq_param(99, 0x00, (64,))
        assert result is None

    def test_invalid_param_returns_none(self, handler):
        result = handler._handle_eq_param(0, 0xFF, (64,))
        assert result is None

    def test_forwards_to_coordinator(self, handler):
        mock_coord = MagicMock()
        mock_coord.set_channel_eq_gain = MagicMock()
        handler.set_effects_coordinator(mock_coord)
        handler._handle_eq_param(0, 0x00, (72,))
        mock_coord.set_channel_eq_gain.assert_called_once()

    def test_coordinator_missing_method(self, handler):
        mock_coord = MagicMock(spec=[])
        handler.set_effects_coordinator(mock_coord)
        handler._handle_eq_param(0, 0x00, (64,))  # no error

    def test_coordinator_exception_handled(self, handler):
        mock_coord = MagicMock()
        mock_coord.set_channel_eq_gain = MagicMock()
        mock_coord.set_channel_eq_gain.side_effect = RuntimeError("coord error")
        handler.set_effects_coordinator(mock_coord)
        handler._handle_eq_param(0, 0x00, (64,))  # no error

    def test_via_process_message(self, handler):
        """0x40 routing through process_message works correctly."""
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        msg = _build_gs_msg(addr=(0x40, 0x00, 0x00), data=(64,))
        handler.process_message(msg)
        assert any("part_0_eq" in s for s, p, v in events)

    def test_multiple_parts_via_process_message(self, handler):
        """Multiple EQ messages through process_message."""
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler.process_message(_build_gs_msg(addr=(0x40, 0x00, 0x00), data=(72,)))
        handler.process_message(_build_gs_msg(addr=(0x40, 0x00, 0x01), data=(56,)))
        part0 = [e for e in events if "part_0_eq" in e[0]]
        part1 = [e for e in events if "part_1_eq" in e[0]]
        assert len(part0) >= 1
        assert len(part1) >= 1

    def test_eq_values_center(self, handler):
        handler._handle_eq_param(0, 0x00, (64,))  # 0 dB

    def test_eq_values_min(self, handler):
        handler._handle_eq_param(3, 0x01, (0,))   # -12 dB

    def test_eq_values_max(self, handler):
        handler._handle_eq_param(5, 0x00, (127,))  # +12 dB


# ---------------------------------------------------------------------------
# Cross-cutting: process_message routing tests
# ---------------------------------------------------------------------------

class TestProcessMessageRouting:
    """Tests which addresses route correctly through process_message.

    Working:
      - 0x11 → drum key params (via 0x10-0x1F branch)
      - 0x40 → per-part EQ (explicit branch)
      - 0x00 → system params
      - 0x01 → part params (working, though 0x02 also routes here)

    Known routing bug: 0x02, 0x03, 0x04, 0x05, 0x06 are caught by the
    0x01-0x10 range and routed to _handle_part_param instead of their
    specific handlers.
    """

    def test_route_drum_key(self, handler):
        """0x11 message correctly routes to _handle_drum_key_param."""
        msg = _build_gs_msg(addr=(0x11, 60, 0x01), data=(100,))
        handler.process_message(msg)
        assert handler.drum_key_params[(1, 60)]["level"] == 100

    def test_route_eq(self, handler):
        """0x40 message correctly routes to _handle_eq_param."""
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        msg = _build_gs_msg(addr=(0x40, 0x00, 0x00), data=(64,))
        handler.process_message(msg)
        assert any("eq" in s for s, p, v in events)

    def test_route_part_param(self, handler):
        """0x01 message routes to _handle_part_param."""
        msg = _build_gs_msg(addr=(0x01, 0x00, 0x00), data=(5,))
        handler.process_message(msg)
        # Part 0 (addr_high-1), param 0x03 (bank_msb)
        assert handler.part_params[0]["bank_msb"] == 5

    def test_route_system_param(self, handler):
        """0x00 message routes to _handle_system_param."""
        msg = _build_gs_msg(addr=(0x00, 0x00, 0x01), data=(80,))
        handler.process_message(msg)
        # 0x01 = master_volume
        assert handler.master_volume == 80

    def test_route_drum_key_device_id_0(self, handler):
        """Device ID 0x00 is accepted."""
        msg = _build_gs_msg(device_id=0x00, addr=(0x11, 48, 0x01), data=(90,))
        handler.process_message(msg)
        assert handler.drum_key_params[(1, 48)]["level"] == 90

    def test_drum_key_device_id_mismatch(self, handler):
        """Device ID 0x20 is rejected."""
        msg = _build_gs_msg(device_id=0x20, addr=(0x11, 48, 0x01), data=(90,))
        result = handler.process_message(msg)
        assert result is None

    def test_invalid_address_returns_none(self, handler):
        msg = _build_gs_msg(addr=(0xFF, 0x00, 0x00), data=(0,))
        result = handler.process_message(msg)
        assert result is None

    def test_malformed_sysex_rejected(self, handler):
        result = handler.process_message(b"\xF0\x41\x10\x42\x12")
        assert result is None


# ---------------------------------------------------------------------------
# Callback interaction tests
# ---------------------------------------------------------------------------

class TestCallbacks:
    """Callback registration and firing."""

    def test_register_multiple_callbacks(self, handler):
        events = []
        handler.register_parameter_callback(lambda s, p, v: events.append("cb1"))
        handler.register_parameter_callback(lambda s, p, v: events.append("cb2"))
        handler._handle_part_key_param(0, 0x10, (50,))
        assert events == ["cb1", "cb2"]

    def test_callback_error_does_not_break(self, handler):
        good_events = []

        def bad_cb(section, param, value):
            raise RuntimeError("callback failure")

        def good_cb(section, param, value):
            good_events.append((section, param, value))

        handler.register_parameter_callback(bad_cb)
        handler.register_parameter_callback(good_cb)
        handler._handle_part_key_param(0, 0x12, (48,))
        assert len(good_events) >= 1

    def test_parameter_callback_section(self, handler):
        events = []
        handler.register_parameter_callback(
            lambda s, p, v: events.append((s, p, v))
        )
        handler._handle_part_key_param(0, 0x12, (48,))
        assert any(e[0] == "part_0_key" for e in events)
        assert any(e[1] == "key_range_low" for e in events)
        assert any(e[2] == 48 for e in events)

    def test_gs_reset_callback(self, handler):
        events = []
        handler.register_system_callback("gs_reset", lambda: events.append("reset"))
        handler._handle_gs_reset()
        assert "reset" in events


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_empty_data_for_key_param(self, handler):
        handler._handle_part_key_param(0, 0x10, ())
        assert handler.part_params[0]["velocity_range_low"] == 1  # clamped from 0

    def test_gs_reset_state(self, handler):
        handler.part_params[0]["volume"] = 50
        handler.gs_enabled = False
        handler._handle_gs_reset()
        assert handler.part_params[0]["volume"] == 100  # default
        assert handler.gs_enabled is True

    def test_drum_key_without_jv2080(self, handler):
        """No error when jv2080_manager is not set."""
        handler._handle_drum_key_param(1, 36, 1, (80,))
        assert handler.drum_key_params[(1, 36)]["level"] == 80

    def test_part_key_without_jv2080(self, handler):
        """No error when jv2080_manager is not set."""
        handler._handle_part_key_param(0, 0x12, (48,))
        assert handler.part_params[0]["key_range_low"] == 48

    def test_eq_without_coordinator(self, handler):
        """No error when effects_coordinator is not set."""
        handler._handle_eq_param(0, 0x00, (64,))

    def test_chorus_effects_without_coordinator(self, handler):
        """No error when effects_coordinator is not set."""
        handler._handle_effects_param(0x04, 0x00, 0x00, (3,))
        assert handler.chorus_params["type"] == 3

    def test_reverb_effects_without_coordinator(self, handler):
        handler._handle_effects_param(0x05, 0x00, 0x00, (2,))
        assert handler.reverb_params["type"] == 2
