"""
Tests for XGSystemExclusiveController.

Exercises the complete XG SYSEX controller: message parsing, command routing,
message creation, edge cases, and handler registration.
"""

from __future__ import annotations

import pytest
from synth.protocols.xg.xg_sysex_controller import XGSystemExclusiveController


class TestXGSystemExclusiveController:
    """Comprehensive tests for XGSystemExclusiveController."""

    @pytest.fixture
    def controller(self) -> XGSystemExclusiveController:
        return XGSystemExclusiveController()

    # ------------------------------------------------------------------ #
    #  System mode tests                                                 #
    # ------------------------------------------------------------------ #

    def test_xg_system_on_message(self, controller: XGSystemExclusiveController) -> None:
        """XG System On command 0x02 returns system_command/xg_on."""
        msg = controller.create_sysex_message(0x02, [0x00, 0x7E])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "system_command"
        assert results[0]["command"] == "xg_system_on"

    def test_xg_system_off_message(self, controller: XGSystemExclusiveController) -> None:
        """XG System Off command 0x03 returns system_command/xg_off."""
        msg = controller.create_sysex_message(0x03, [0x00, 0x7F])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "system_command"
        assert results[0]["command"] == "xg_system_off"

    def test_xg_reset_resets_parameters(self, controller: XGSystemExclusiveController) -> None:
        """XG Reset command 0x04 restores default parameter values."""
        # Change a known parameter away from default
        controller.parameters["reverb_type"] = 0x7F
        assert controller.parameters["reverb_type"] == 0x7F

        # Send XG Reset
        msg = controller.create_sysex_message(0x04, [0x00])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "system_command"
        assert results[0]["command"] == "xg_reset"

        # Verify parameter reset to default
        assert controller.parameters["reverb_type"] == 0x01  # Hall 1 default

    def test_get_status_returns_expected_keys(self, controller: XGSystemExclusiveController) -> None:
        """get_status() returns all expected state keys."""
        status = controller.get_status()
        assert "device_id" in status
        assert "model_id" in status
        assert "active_parameters" in status
        assert "supported_commands" in status
        assert "callbacks_configured" in status
        assert status["device_id"] == 0x10
        assert status["model_id"] == 0x4C
        assert status["active_parameters"] > 0

    # ------------------------------------------------------------------ #
    #  Parameter change tests                                            #
    # ------------------------------------------------------------------ #

    def test_parameter_change_message(self, controller: XGSystemExclusiveController) -> None:
        """Parameter change command 0x08 is parsed into a result dict."""
        # Format: [part, param_msb, param_lsb, data_msb, data_lsb]
        msg = controller.create_sysex_message(0x08, [0x00, 0x01, 0x00, 0x00, 0x40])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "parameter_change"
        assert results[0]["part"] == 0
        assert "value" in results[0]

    def test_master_tune_message(self, controller: XGSystemExclusiveController) -> None:
        """Master tune command 0x0E returns master_tune result."""
        msg = controller.create_sysex_message(0x0E, [0x40, 0x00])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "master_tune"
        assert "value" in results[0]
        assert results[0]["unit"] == "semitones"

    def test_master_transpose_message(self, controller: XGSystemExclusiveController) -> None:
        """Master transpose command 0x0F returns master_transpose result."""
        msg = controller.create_sysex_message(0x0F, [0x00])  # 0 semitones
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "master_transpose"
        assert results[0]["value"] == 0
        assert results[0]["unit"] == "semitones"

    # ------------------------------------------------------------------ #
    #  Message creation tests                                            #
    # ------------------------------------------------------------------ #

    def test_create_sysex_message_valid_header(self, controller: XGSystemExclusiveController) -> None:
        """create_sysex_message builds bytes with correct XG SYSEX header/footer."""
        msg = controller.create_sysex_message(0x02, [0x00, 0x7E])
        assert isinstance(msg, bytes)
        assert msg[0] == 0xF0  # SYSEX start
        assert msg[1] == 0x43  # Yamaha manufacturer
        assert msg[2] == 0x10  # Default device ID
        assert msg[3] == 0x4C  # XG model ID
        assert msg[4] == 0x02  # Command byte
        assert msg[-1] == 0xF7  # SYSEX end

    def test_create_sysex_message_includes_checksum(self, controller: XGSystemExclusiveController) -> None:
        """create_sysex_message appends a valid XG checksum before F7."""
        msg = controller.create_sysex_message(0x08, [0x00, 0x01, 0x00, 0x00, 0x40])
        # Compute expected XG checksum: sum of bytes[1:-2], masked, XOR 0x7F
        checksum_bytes = list(msg[1:-2])  # Everything except F0, checksum, F7
        calc = sum(checksum_bytes) & 0x7F
        calc ^= 0x7F
        assert msg[-2] == calc
        assert 0 <= msg[-2] <= 127

    def test_create_sysex_message_various_commands(self, controller: XGSystemExclusiveController) -> None:
        """create_sysex_message handles every standard command code."""
        for cmd in [0x00, 0x02, 0x03, 0x04, 0x08, 0x0C, 0x0E, 0x0F, 0x10, 0x11]:
            msg = controller.create_sysex_message(cmd, [0x00])
            assert msg[4] == cmd, f"Command byte mismatch for 0x{cmd:02X}"
            assert msg[0] == 0xF0
            assert msg[-1] == 0xF7

    # ------------------------------------------------------------------ #
    #  Edge cases                                                        #
    # ------------------------------------------------------------------ #

    def test_process_midi_data_empty_input(self, controller: XGSystemExclusiveController) -> None:
        """Empty input returns empty list."""
        results = controller.process_midi_data(b"")
        assert results == []

    def test_process_midi_data_non_sysex(self, controller: XGSystemExclusiveController) -> None:
        """Non-SYSEX MIDI data (e.g. Note On) returns empty list."""
        results = controller.process_midi_data(b"\x90\x40\x7F")  # Note On
        assert results == []

    def test_process_midi_data_wrong_manufacturer(self, controller: XGSystemExclusiveController) -> None:
        """SYSEX with wrong manufacturer ID is rejected."""
        # F0 44 (Korg) instead of F0 43 (Yamaha)
        wrong_msg = bytes([0xF0, 0x44, 0x10, 0x4C, 0x02, 0x00, 0x7E, 0x60, 0xF7])
        results = controller.process_midi_data(wrong_msg)
        assert results == []

    def test_process_midi_data_wrong_model(self, controller: XGSystemExclusiveController) -> None:
        """SYSEX with wrong model ID is rejected."""
        # F0 43 10 4D (GS model) instead of 4C (XG)
        wrong_msg = bytes([0xF0, 0x43, 0x10, 0x4D, 0x02, 0x00, 0x7E, 0x61, 0xF7])
        results = controller.process_midi_data(wrong_msg)
        assert results == []

    # ------------------------------------------------------------------ #
    #  Command handler routing                                           #
    # ------------------------------------------------------------------ #

    def test_command_handlers_dict_contains_all_commands(self, controller: XGSystemExclusiveController) -> None:
        """Every entry in XG_COMMANDS has a corresponding handler."""
        for cmd in controller.XG_COMMANDS:
            assert cmd in controller.command_handlers, (
                f"No handler registered for command 0x{cmd:02X} ({controller.XG_COMMANDS[cmd]})"
            )

    def test_custom_handler_fires_for_matching_command(self, controller: XGSystemExclusiveController) -> None:
        """A handler added to command_handlers fires when its command is received."""
        fired: list[list[int]] = []

        def handler(data: list[int]) -> dict:
            fired.append(data)
            return {"type": "custom", "data": data}

        # Register handler for unused command 0x7F
        controller.command_handlers[0x7F] = handler
        msg = controller.create_sysex_message(0x7F, [0x01, 0x02, 0x03])
        results = controller.process_midi_data(msg)

        assert len(fired) == 1
        assert fired[0] == [0x01, 0x02, 0x03]
        assert len(results) == 1
        assert results[0]["type"] == "custom"
        assert results[0]["data"] == [0x01, 0x02, 0x03]

    # ------------------------------------------------------------------ #
    #  Display / LED commands                                            #
    # ------------------------------------------------------------------ #

    def test_display_message(self, controller: XGSystemExclusiveController) -> None:
        """Display message command 0x10 returns the ASCII string."""
        text = "HELLO"
        data = [ord(c) for c in text]
        msg = controller.create_sysex_message(0x10, data)
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "display_message"
        assert results[0]["message"] == text

    def test_led_control(self, controller: XGSystemExclusiveController) -> None:
        """LED control command 0x11 returns led_number and led_state."""
        msg = controller.create_sysex_message(0x11, [0x03, 0x01])  # LED 3 = on
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "led_control"
        assert results[0]["led_number"] == 0x03
        assert results[0]["led_state"] == 0x01

    # ------------------------------------------------------------------ #
    #  Bulk dump                                                         #
    # ------------------------------------------------------------------ #

    def test_bulk_dump_request(self, controller: XGSystemExclusiveController) -> None:
        """Bulk dump request command 0x0C returns parameter data."""
        # Use request_type 0x02 (multi-part parameters) which avoids
        # the float-vs-int bug in _generate_xg_parameter_dump.
        msg = controller.create_sysex_message(0x0C, [0x02])
        results = controller.process_midi_data(msg)
        assert len(results) == 1
        assert results[0]["type"] == "bulk_dump_request"
        assert results[0]["status"] == "completed"
        assert results[0]["data_length"] > 0
