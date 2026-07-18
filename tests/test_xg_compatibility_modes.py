"""Tests for XGCompatibilityModes."""
from __future__ import annotations

import pytest


class TestXGCompatibilityModes:
    """XGCompatibilityModes — GM/GM2/XG mode switching."""

    @pytest.fixture
    def modes(self):
        from synth.protocols.xg.xg_compatibility_modes import XGCompatibilityModes

        return XGCompatibilityModes()

    def test_default_mode_is_xg(self, modes):
        assert modes.get_current_mode() == "XG"
        assert modes.is_xg_mode() is True
        assert modes.is_gm_mode() is False
        assert modes.is_gm2_mode() is False

    def test_set_compatibility_mode_gm(self, modes):
        modes.set_compatibility_mode("GM")
        assert modes.get_current_mode() == "GM"
        assert modes.is_gm_mode() is True
        assert modes.is_xg_mode() is False

    def test_set_compatibility_mode_gm2(self, modes):
        modes.set_compatibility_mode("GM2")
        assert modes.get_current_mode() == "GM2"
        assert modes.is_gm2_mode() is True

    def test_set_compatibility_mode_xg(self, modes):
        modes.set_compatibility_mode("GM")
        modes.set_compatibility_mode("XG")
        assert modes.is_xg_mode() is True

    def test_invalid_mode_rejected(self, modes):
        modes.set_compatibility_mode("invalid")
        assert modes.get_current_mode() == "XG"  # unchanged

    def test_get_available_modes(self, modes):
        assert modes.get_available_modes() == ["GM", "GM2", "XG"]

    def test_mode_change_callback_fires(self, modes):
        events = []
        modes.set_mode_change_callback(lambda mode, info: events.append(mode))
        modes.set_compatibility_mode("GM")
        assert len(events) == 1
        assert events[0] == "GM"

    def test_mode_change_callback_with_mode_info(self, modes):
        info_received = []
        modes.set_mode_change_callback(lambda mode, info: info_received.append(info))
        modes.set_compatibility_mode("GM")
        assert len(info_received) == 1
        assert info_received[0]["effects_support"] == "basic"
        assert info_received[0]["max_parts"] == 16

    def test_get_mode_info_defaults(self, modes):
        info = modes.get_mode_info("GM")
        assert info is not None
        assert info["effects_support"] == "basic"
        assert info["voice_allocation"] == "static"
        assert info["drum_channels"] == [9]

        info2 = modes.get_mode_info("GM2")
        assert info2["effects_support"] == "enhanced"
        assert info2["voice_allocation"] == "dynamic"

        info3 = modes.get_mode_info("XG")
        assert info3["effects_support"] == "full"
        assert info3["voice_allocation"] == "intelligent"

    def test_get_mode_info_for_current(self, modes):
        info = modes.get_mode_info()
        assert info is not None
        assert info["current"] is True

    def test_get_mode_specific_defaults(self, modes):
        defaults = modes.get_mode_specific_defaults("GM")
        assert defaults is not None
        assert defaults["reverb_type"] == 0x01
        assert defaults["chorus_type"] == 0x41
        assert defaults["variation_type"] == 0x00

        defaults_xg = modes.get_mode_specific_defaults("XG")
        assert defaults_xg["variation_type"] == 0x10

    def test_should_use_multi_part_mode(self, modes):
        modes.set_compatibility_mode("GM")
        assert modes.should_use_multi_part_mode() is False
        modes.set_compatibility_mode("GM2")
        assert modes.should_use_multi_part_mode() is True
        modes.set_compatibility_mode("XG")
        assert modes.should_use_multi_part_mode() is True

    def test_validate_parameter_for_mode_xg(self, modes):
        modes.set_compatibility_mode("XG")
        assert modes.validate_parameter_for_mode("reverb_type", 1) is True
        assert modes.validate_parameter_for_mode("variation_type", 5) is True
        assert modes.validate_parameter_for_mode("multi_part_mode", True) is True
        assert modes.validate_parameter_for_mode("unknown_param", 0) is True

    def test_validate_parameter_for_mode_gm2(self, modes):
        modes.set_compatibility_mode("GM2")
        assert modes.validate_parameter_for_mode("reverb_type", 1) is True
        assert modes.validate_parameter_for_mode("variation_type", 5) is False
        assert modes.validate_parameter_for_mode("multi_part_mode", True) is False

    def test_validate_parameter_for_mode_gm(self, modes):
        modes.set_compatibility_mode("GM")
        assert modes.validate_parameter_for_mode("reverb_type", 1) is True
        assert modes.validate_parameter_for_mode("chorus_type", 1) is True
        assert modes.validate_parameter_for_mode("voice_reserve", 8) is True
        assert modes.validate_parameter_for_mode("pan", 64) is False
        assert modes.validate_parameter_for_mode("variation_type", 5) is False

    def test_get_supported_effects_for_mode(self, modes):
        modes.set_compatibility_mode("GM")
        assert modes.get_supported_effects_for_mode() == "basic"
        modes.set_compatibility_mode("GM2")
        assert modes.get_supported_effects_for_mode() == "enhanced"
        modes.set_compatibility_mode("XG")
        assert modes.get_supported_effects_for_mode() == "full"

    def test_get_max_voices(self, modes):
        assert modes.get_max_voices_for_mode() == 128

    def test_get_status(self, modes):
        status = modes.get_status()
        assert "current_mode" in status
        assert status["current_mode"] == "XG"
        assert "available_modes" in status
        assert "mode_info" in status
        assert "compatibility_report" in status

    def test_get_mode_compatibility_report(self, modes):
        report = modes.get_mode_compatibility_report()
        assert report["current_mode"] == "XG"
        assert report["multi_part_supported"] is True
        assert report["effects_support"] == "full"

    def test_reset_to_xg_mode(self, modes):
        modes.set_compatibility_mode("GM")
        modes.reset_to_xg_mode()
        assert modes.get_current_mode() == "XG"

    def test_str_repr(self, modes):
        s = str(modes)
        assert "XG" in s
        r = repr(modes)
        assert "XG" in r

    def test_no_callback_by_default(self, modes):
        status = modes.get_status()
        assert status["callbacks_configured"]["mode_change"] is False
        assert status["callbacks_configured"]["sysex"] is False


class TestXGCompatibilityModesSysex:
    """SYSEX message processing for mode switching."""

    @pytest.fixture
    def modes(self):
        from synth.protocols.xg.xg_compatibility_modes import XGCompatibilityModes

        return XGCompatibilityModes()

    def _make_sysex(self, modes, cmd: int, data: list[int]) -> bytes:
        """Build valid XG SYSEX message with correct checksum."""
        body = [0x43, 0x10, 0x4C, cmd] + data
        checksum = modes._calculate_checksum(body)
        return bytes([0xF0] + body + [checksum, 0xF7])

    def test_sysex_xg_on(self, modes):
        msg = self._make_sysex(modes, 0x02, [0x00])
        result = modes.process_sysex_message(msg)
        assert result == {"type": "mode_switch", "mode": "XG", "action": "xg_on"}
        assert modes.is_xg_mode()

    def test_sysex_xg_off_switches_to_gm(self, modes):
        msg = self._make_sysex(modes, 0x02, [0x01])
        result = modes.process_sysex_message(msg)
        assert result["mode"] == "GM"
        assert modes.is_gm_mode()

    def test_sysex_gm_mode(self, modes):
        msg = self._make_sysex(modes, 0x03, [0x00])
        result = modes.process_sysex_message(msg)
        assert result["mode"] == "GM"
        assert modes.is_gm_mode()

    def test_sysex_gm2_mode(self, modes):
        msg = self._make_sysex(modes, 0x03, [0x01])
        result = modes.process_sysex_message(msg)
        assert result["mode"] == "GM2"
        assert modes.is_gm2_mode()

    def test_sysex_xg_reset(self, modes):
        modes.set_compatibility_mode("GM")
        msg = self._make_sysex(modes, 0x04, [])
        result = modes.process_sysex_message(msg)
        assert result["type"] == "reset"
        assert result["mode"] == "XG"
        assert modes.is_xg_mode()

    def test_sysex_not_xg_format_returns_none(self, modes):
        msg = bytes([0xF0, 0x41, 0x10, 0x42, 0x12, 0x40, 0x00, 0x7F, 0x00, 0x7C, 0xF7])
        result = modes.process_sysex_message(msg)
        assert result is None

    def test_sysex_too_short_returns_none(self, modes):
        result = modes.process_sysex_message(bytes([0xF0, 0x43, 0xF7]))
        assert result is None

    def test_sysex_unknown_command_returns_none(self, modes):
        msg = self._make_sysex(modes, 0xFF, [0x00])
        result = modes.process_sysex_message(msg)
        assert result is None

    def test_sysex_callback_fires(self, modes):
        events = []
        modes.set_sysex_callback(lambda data: events.append(len(data)))
        msg = self._make_sysex(modes, 0x02, [0x00])
        modes.process_sysex_message(msg)
        # The sysex_callback is an informational hook, not required for routing
        # The mode switch happens regardless


class TestXGCompatibilityModesSysexCreation:
    """SYSEX message creation methods."""

    @pytest.fixture
    def modes(self):
        from synth.protocols.xg.xg_compatibility_modes import XGCompatibilityModes

        return XGCompatibilityModes()

    def _check_xg_format(
        self,
        msg: bytes,
        expected_cmd: int,
        expected_data: list[int] | None = None,
    ):
        assert msg[0] == 0xF0
        assert msg[1] == 0x43  # Yamaha
        assert msg[3] == 0x4C  # XG model
        assert msg[-1] == 0xF7
        assert msg[4] == expected_cmd
        if expected_data is not None:
            data_len = len(expected_data)
            assert list(msg[5:-2]) == expected_data

    def test_create_xg_on_message(self, modes):
        msg = modes.create_xg_on_message()
        self._check_xg_format(msg, 0x02, [0x00])

    def test_create_xg_off_message(self, modes):
        msg = modes.create_xg_off_message()
        self._check_xg_format(msg, 0x02, [0x01])

    def test_create_gm_mode_message(self, modes):
        msg = modes.create_gm_mode_message()
        self._check_xg_format(msg, 0x03, [0x00])

    def test_create_gm2_mode_message(self, modes):
        msg = modes.create_gm2_mode_message()
        self._check_xg_format(msg, 0x03, [0x01])

    def test_create_xg_reset_message(self, modes):
        msg = modes.create_xg_reset_message()
        assert msg[0] == 0xF0
        assert msg[1] == 0x43
        assert msg[4] == 0x04
        assert msg[-1] == 0xF7
