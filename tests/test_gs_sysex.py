"""
GS Sysex Handler Tests

Exercises GSSysexHandler from synth.protocols.gs.gs_sysex_handler.
Covers system params, part params, effects (reverb/chorus), callbacks,
message creation, validation, edge cases, and the public API.
"""

from __future__ import annotations

import pytest

from synth.protocols.gs.gs_sysex_handler import GSSysexHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rol_checksum(payload: list[int]) -> int:
    """Roland checksum: (128 - (sum % 128)) & 0x7F."""
    return (128 - (sum(payload) % 128)) & 0x7F


def _build_sysex(
    device_id: int,
    command: int,
    address: tuple[int, int, int],
    data: list[int],
) -> bytes:
    """Build a complete GS sysex byte string."""
    msg: list[int] = [
        0xF0,
        0x41,  # Roland
        device_id,
        0x42,  # GS
        command,
        address[0],
        address[1],
        address[2],
    ]
    msg.extend(data)
    cs = _rol_checksum(msg[1:])  # sum from manufacturer byte forward
    msg.append(cs)
    msg.append(0xF7)
    return bytes(msg)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestGSSysexHandler:
    """Comprehensive tests for GSSysexHandler."""

    # -- fixtures -----------------------------------------------------------

    @pytest.fixture
    def handler(self) -> GSSysexHandler:
        return GSSysexHandler()

    # -- initial state ------------------------------------------------------

    def test_initial_state(self, handler: GSSysexHandler) -> None:
        """Default-initialised handler has expected parameter values."""
        assert handler.master_volume == 100
        assert handler.master_tune == 0x40  # 0 cents
        assert handler.master_transpose == 0x40  # 0 semitones
        assert handler.gs_enabled is False
        assert handler.device_id == 0x10

    # -- system parameters --------------------------------------------------

    def test_master_tune(self, handler: GSSysexHandler) -> None:
        """Parse master tune sysex and verify stored value."""
        # address (0x00, 0x00, 0x00) → master_tune, value 0x40 = 0 cents
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x00), [0x40])
        handler.process_message(msg)
        assert handler.master_tune == 0x40

    def test_master_tune_positive(self, handler: GSSysexHandler) -> None:
        """Master tune with positive cents offset."""
        # value 0x50 = +12 cents  (64 + 12 = 0x4C... actually 0x50-64=16 cents)
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x00), [0x50])
        handler.process_message(msg)
        assert handler.master_tune == 0x50

    def test_master_volume(self, handler: GSSysexHandler) -> None:
        """Parse master volume sysex."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [80])
        handler.process_message(msg)
        assert handler.master_volume == 80

    def test_master_volume_max(self, handler: GSSysexHandler) -> None:
        """Master volume at maximum (127)."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [127])
        handler.process_message(msg)
        assert handler.master_volume == 127

    def test_master_transpose(self, handler: GSSysexHandler) -> None:
        """Parse master transpose sysex."""
        # value 0x40 = 0 semitones
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x02), [0x40])
        handler.process_message(msg)
        assert handler.master_transpose == 0x40

    def test_master_transpose_shift_up(self, handler: GSSysexHandler) -> None:
        """Master transpose shifted up."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x02), [0x46])  # +6
        handler.process_message(msg)
        assert handler.master_transpose == 0x46

    # -- part parameters ----------------------------------------------------

    def test_part_volume(self, handler: GSSysexHandler) -> None:
        """Part 0 volume set to 100."""
        # address (0x01, 0x00, 0x03) → part 0, volume
        msg = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x03), [100])
        handler.process_message(msg)
        assert handler.part_params[0]["volume"] == 100

    def test_part_pan(self, handler: GSSysexHandler) -> None:
        """Part 0 pan set to 64 (center)."""
        msg = _build_sysex(0x10, 0x10, (0x01, 0x00, 0x04), [64])
        handler.process_message(msg)
        assert handler.part_params[0]["pan"] == 64

    def test_part_program_change(self, handler: GSSysexHandler) -> None:
        """Part 0 program number set to 42."""
        msg = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x02), [42])
        handler.process_message(msg)
        assert handler.part_params[0]["program_num"] == 42

    def test_part_program_change_data_set(self, handler: GSSysexHandler) -> None:
        """Part 0 program number set via Data Set (0x10) command."""
        msg = _build_sysex(0x10, 0x10, (0x01, 0x00, 0x02), [77])
        handler.process_message(msg)
        assert handler.part_params[0]["program_num"] == 77

    def test_all_16_parts(self, handler: GSSysexHandler) -> None:
        """Set volume on all 16 parts independently.

        Parts 0 and 6-15 use the flat addr_high=0x01+part encoding.
        Parts 1-5 have addr_high values (0x02-0x06) that are reserved for
        part-key and effects handlers, so those are set via
        set_part_parameter() instead.
        """
        # Parts via sysex (non-conflicting addr_high: 0x01, 0x07-0x10)
        for part in (0, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15):
            addr_high = 0x01 + part
            vol = part * 8
            msg = _build_sysex(0x10, 0x12, (addr_high, 0x00, 0x03), [vol])
            handler.process_message(msg)

        # Parts via set_part_parameter (addr_high 0x02-0x06 are reserved)
        for part in (1, 2, 3, 4, 5):
            vol = part * 8
            handler.set_part_parameter(part, 0x00, 0x03, vol)

        for part in range(16):
            expected = part * 8
            assert handler.part_params[part]["volume"] == expected, (
                f"Part {part} volume mismatch: expected {expected}, "
                f"got {handler.part_params[part]['volume']}"
            )

    def test_part_filter_cutoff(self, handler: GSSysexHandler) -> None:
        """Part filter cutoff parameter."""
        msg = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x10), [90])
        handler.process_message(msg)
        assert handler.part_params[0]["filter_cutoff"] == 90

    def test_part_key_range_low(self, handler: GSSysexHandler) -> None:
        """Part key range low via part key params (0x02 address)."""
        # address (0x02, part_num, 0x12) → part_key_param key_range_low
        msg = _build_sysex(0x10, 0x12, (0x02, 0x00, 0x12), [36])
        handler.process_message(msg)
        assert handler.part_params[0]["key_range_low"] == 36

    def test_part_key_range_high(self, handler: GSSysexHandler) -> None:
        """Part key range high via part key params."""
        msg = _build_sysex(0x10, 0x12, (0x02, 0x00, 0x13), [96])
        handler.process_message(msg)
        assert handler.part_params[0]["key_range_high"] == 96

    # -- reverb parameters --------------------------------------------------

    def test_reverb_type(self, handler: GSSysexHandler) -> None:
        """Reverb type set to 4 (Hall2)."""
        msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x00), [4])
        handler.process_message(msg)
        assert handler.reverb_params["type"] == 4

    def test_reverb_level(self, handler: GSSysexHandler) -> None:
        """Reverb level."""
        msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x01), [80])
        handler.process_message(msg)
        assert handler.reverb_params["level"] == 80

    def test_reverb_time(self, handler: GSSysexHandler) -> None:
        """Reverb time."""
        msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x02), [60])
        handler.process_message(msg)
        assert handler.reverb_params["time"] == 60

    def test_reverb_feedback(self, handler: GSSysexHandler) -> None:
        """Reverb feedback."""
        msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x03), [100])
        handler.process_message(msg)
        assert handler.reverb_params["feedback"] == 100

    def test_reverb_predelay(self, handler: GSSysexHandler) -> None:
        """Reverb predelay."""
        msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x04), [40])
        handler.process_message(msg)
        assert handler.reverb_params["predelay"] == 40

    def test_reverb_all_types(self, handler: GSSysexHandler) -> None:
        """All 8 reverb types (0-7) are accepted."""
        for rev_type in range(8):
            h = GSSysexHandler()
            msg = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x00), [rev_type])
            h.process_message(msg)
            assert h.reverb_params["type"] == rev_type

    # -- chorus parameters --------------------------------------------------

    def test_chorus_type(self, handler: GSSysexHandler) -> None:
        """Chorus type set to 3 (Chorus4)."""
        msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x00), [3])
        handler.process_message(msg)
        assert handler.chorus_params["type"] == 3

    def test_chorus_level(self, handler: GSSysexHandler) -> None:
        """Chorus level."""
        msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x01), [70])
        handler.process_message(msg)
        assert handler.chorus_params["level"] == 70

    def test_chorus_rate(self, handler: GSSysexHandler) -> None:
        """Chorus rate."""
        msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x02), [30])
        handler.process_message(msg)
        assert handler.chorus_params["rate"] == 30

    def test_chorus_depth(self, handler: GSSysexHandler) -> None:
        """Chorus depth."""
        msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x03), [50])
        handler.process_message(msg)
        assert handler.chorus_params["depth"] == 50

    def test_chorus_feedback(self, handler: GSSysexHandler) -> None:
        """Chorus feedback."""
        msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x04), [90])
        handler.process_message(msg)
        assert handler.chorus_params["feedback"] == 90

    def test_chorus_all_types(self, handler: GSSysexHandler) -> None:
        """All 6 chorus types (0-5) are accepted."""
        for ch_type in range(6):
            h = GSSysexHandler()
            msg = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x00), [ch_type])
            h.process_message(msg)
            assert h.chorus_params["type"] == ch_type

    # -- GS reset -----------------------------------------------------------

    def test_reset(self, handler: GSSysexHandler) -> None:
        """reset() reinitialises state and enables GS."""
        # Mutate state first
        handler.master_volume = 127
        handler.part_params[0]["volume"] = 50
        handler.gs_enabled = False

        handler.reset()

        assert handler.master_volume == 100
        assert handler.part_params[0]["volume"] == 100
        assert handler.gs_enabled is True

    # -- callbacks ----------------------------------------------------------

    def test_parameter_callback_fires(self, handler: GSSysexHandler) -> None:
        """Register a parameter callback and verify it fires with correct args."""
        captured: list[tuple[str, str, int]] = []

        def cb(section: str, param: str, value: int) -> None:
            captured.append((section, param, value))

        handler.register_parameter_callback(cb)

        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [90])
        handler.process_message(msg)

        assert len(captured) >= 1
        section, param, value = captured[0]
        assert section == "system"
        assert param == "master_volume"
        assert value == 90

    def test_parameter_callback_part(self, handler: GSSysexHandler) -> None:
        """Parameter callback fires for part parameter changes."""
        captured: list[tuple[str, str, int]] = []

        def cb(section: str, param: str, value: int) -> None:
            captured.append((section, param, value))

        handler.register_parameter_callback(cb)

        msg = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x03), [75])
        handler.process_message(msg)

        assert len(captured) >= 1
        assert captured[0] == ("part_0", "volume", 75)

    def test_system_callback_gs_reset(self, handler: GSSysexHandler) -> None:
        """System callback for gs_reset fires on reset()."""
        reset_fired: list[bool] = []

        def on_reset() -> None:
            reset_fired.append(True)

        handler.register_system_callback("gs_reset", on_reset)
        handler.reset()

        assert len(reset_fired) == 1

    def test_multiple_parameter_callbacks(self, handler: GSSysexHandler) -> None:
        """Multiple parameter callbacks all receive notifications."""
        fired: list[int] = []

        def cb1(section: str, param: str, value: int) -> None:
            fired.append(1)

        def cb2(section: str, param: str, value: int) -> None:
            fired.append(2)

        handler.register_parameter_callback(cb1)
        handler.register_parameter_callback(cb2)

        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [100])
        handler.process_message(msg)

        assert 1 in fired
        assert 2 in fired

    # -- create_message & checksum ------------------------------------------

    def test_create_message_basic(self, handler: GSSysexHandler) -> None:
        """create_message returns valid GS sysex with correct checksum."""
        msg = handler.create_message(0x12, (0x00, 0x00, 0x01), [100])
        assert isinstance(msg, bytes)
        assert len(msg) >= 10
        assert msg[0] == 0xF0
        assert msg[-1] == 0xF7
        assert msg[1] == 0x41  # Roland
        assert msg[3] == 0x42  # GS

    def test_create_message_checksum_valid(self, handler: GSSysexHandler) -> None:
        """Checksum in created message is correct per Roland spec."""
        msg = handler.create_message(0x12, (0x05, 0x00, 0x01), [80])
        # Extract checksum (second-to-last byte)
        checksum = msg[-2]
        # Recalculate
        expected_cs = _rol_checksum(list(msg[1:-2]))
        assert checksum == expected_cs

    def test_create_message_roundtrip(self, handler: GSSysexHandler) -> None:
        """Message created via create_message is accepted by process_message."""
        # Create a message for part 0 volume = 85
        msg = handler.create_message(0x12, (0x01, 0x00, 0x03), [85])
        # Process it on a fresh handler
        h2 = GSSysexHandler()
        h2.process_message(msg)
        assert h2.part_params[0]["volume"] == 85

    def test_create_message_different_command(self, handler: GSSysexHandler) -> None:
        """create_message works with different command IDs."""
        msg = handler.create_message(0x10, (0x01, 0x00, 0x04), [32])
        assert msg[4] == 0x10  # Data Set command

    # -- get_status ---------------------------------------------------------

    def test_get_status_keys(self, handler: GSSysexHandler) -> None:
        """get_status() returns expected keys."""
        status = handler.get_status()
        expected_keys = {
            "gs_enabled", "master_volume", "master_tune",
            "drum_channel", "reverb_type", "chorus_type",
        }
        assert expected_keys.issubset(status.keys()), (
            f"Missing keys: {expected_keys - set(status.keys())}"
        )

    def test_get_status_types(self, handler: GSSysexHandler) -> None:
        """get_status() values have correct types."""
        status = handler.get_status()
        assert isinstance(status["gs_enabled"], bool)
        assert isinstance(status["master_volume"], int)
        assert isinstance(status["master_tune"], int)
        assert isinstance(status["drum_channel"], int)
        assert isinstance(status["reverb_type"], int)
        assert isinstance(status["chorus_type"], int)

    def test_get_status_after_updates(self, handler: GSSysexHandler) -> None:
        """get_status() reflects parameter changes."""
        msg_v = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [50])
        handler.process_message(msg_v)
        msg_r = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x00), [3])
        handler.process_message(msg_r)
        msg_c = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x00), [2])
        handler.process_message(msg_c)

        status = handler.get_status()
        assert status["master_volume"] == 50
        assert status["reverb_type"] == 3
        assert status["chorus_type"] == 2

    # -- validation & edge cases --------------------------------------------

    def test_empty_sysex(self, handler: GSSysexHandler) -> None:
        """Empty sysex returns None."""
        result = handler.process_message(b"")
        assert result is None

    def test_too_short_sysex(self, handler: GSSysexHandler) -> None:
        """Very short sysex returns None."""
        result = handler.process_message(b"\xF0\x41\x00")
        assert result is None

    def test_missing_f0(self, handler: GSSysexHandler) -> None:
        """Missing F0 start byte causes rejection."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [100])
        bad = msg[1:]  # strip F0
        result = handler.process_message(bad)
        assert result is None

    def test_missing_f7(self, handler: GSSysexHandler) -> None:
        """Missing F7 end byte causes rejection."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [100])
        bad = msg[:-1]  # strip F7
        result = handler.process_message(bad)
        assert result is None

    def test_wrong_manufacturer(self, handler: GSSysexHandler) -> None:
        """Message with wrong manufacturer ID is rejected."""
        # Yamaha = 0x43 instead of Roland 0x41
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [100])
        bad = bytearray(msg)
        bad[1] = 0x43  # Yamaha
        result = handler.process_message(bytes(bad))
        assert result is None

    def test_wrong_model_id(self, handler: GSSysexHandler) -> None:
        """Message with wrong model ID (not 0x42) is rejected."""
        msg = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [100])
        bad = bytearray(msg)
        bad[3] = 0x16  # not GS model
        result = handler.process_message(bytes(bad))
        assert result is None

    def test_unknown_command(self, handler: GSSysexHandler) -> None:
        """Unknown command returns None without error."""
        # command 0x7F is not defined
        msg = _build_sysex(0x10, 0x7F, (0x00, 0x00, 0x01), [100])
        result = handler.process_message(msg)
        assert result is None

    def test_device_id_zero_accepted(self, handler: GSSysexHandler) -> None:
        """Device ID 0x00 is always accepted (broadcast)."""
        msg = _build_sysex(0x00, 0x12, (0x00, 0x00, 0x01), [90])
        result = handler.process_message(msg)
        # Should be accepted and return None (no response)
        assert result is None
        assert handler.master_volume == 90

    def test_wrong_device_id_rejected(self, handler: GSSysexHandler) -> None:
        """Non-matching device ID is rejected."""
        # Default device_id is 0x10; try 0x11
        msg = _build_sysex(0x11, 0x12, (0x00, 0x00, 0x01), [90])
        result = handler.process_message(msg)
        assert result is None
        assert handler.master_volume == 100  # unchanged

    # -- public API ---------------------------------------------------------

    def test_enable_gs(self, handler: GSSysexHandler) -> None:
        """enable_gs sets gs_enabled to True."""
        assert handler.gs_enabled is False
        handler.enable_gs()
        assert handler.gs_enabled is True

    def test_gs_mode_property(self, handler: GSSysexHandler) -> None:
        """gs_mode property reflects gs_enabled state."""
        assert handler.gs_mode == "gm"
        handler.enable_gs()
        assert handler.gs_mode == "gs"

    def test_set_part_parameter(self, handler: GSSysexHandler) -> None:
        """set_part_parameter directly updates part state and fires callback."""
        captured: list[tuple[str, str, int]] = []

        def cb(section: str, param: str, value: int) -> None:
            captured.append((section, param, value))

        handler.register_parameter_callback(cb)
        result = handler.set_part_parameter(7, 0, 0x04, 80)  # part 7 pan=80

        assert result is True
        assert handler.part_params[7]["pan"] == 80
        assert ("part_7", "pan", 80) in captured

    def test_set_part_parameter_invalid_part(self, handler: GSSysexHandler) -> None:
        """set_part_parameter returns False for out-of-range part."""
        result = handler.set_part_parameter(99, 0, 0x03, 100)
        assert result is False

    def test_set_part_parameter_invalid_param(self, handler: GSSysexHandler) -> None:
        """set_part_parameter returns False for unknown param."""
        result = handler.set_part_parameter(0, 0xFF, 0xFF, 100)
        assert result is False

    def test_set_drum_part(self, handler: GSSysexHandler) -> None:
        """set_drum_part configures channel as drum part."""
        result = handler.set_drum_part(9, 1)
        assert result is True

    def test_is_drum_part(self, handler: GSSysexHandler) -> None:
        """is_drum_part returns True for channels with bank 127."""
        handler.set_drum_part(9, 1)
        assert handler.is_drum_part(9) is True
        assert handler.is_drum_part(0) is False

    def test_is_drum_part_invalid(self, handler: GSSysexHandler) -> None:
        """is_drum_part returns False for out-of-range part."""
        assert handler.is_drum_part(99) is False

    def test_get_part_bank_defaults(self, handler: GSSysexHandler) -> None:
        """get_part_bank returns default bank values."""
        bank = handler.get_part_bank(5)
        assert bank == (0, 0, 0)

    def test_get_part_bank_after_drum(self, handler: GSSysexHandler) -> None:
        """get_part_bank reflects drum setup."""
        handler.set_drum_part(9, 2)
        bank = handler.get_part_bank(9)
        assert bank[0] == 127
        assert bank[1] == 1  # drum_map - 1

    def test_get_part_bank_invalid(self, handler: GSSysexHandler) -> None:
        """get_part_bank returns (0,0,0) for out-of-range part."""
        assert handler.get_part_bank(99) == (0, 0, 0)

    def test_get_drum_channel(self, handler: GSSysexHandler) -> None:
        """get_drum_channel returns channel 9 (MIDI channel 10)."""
        assert handler.get_drum_channel() == 9

    def test_set_channel_parameter(self, handler: GSSysexHandler) -> None:
        """set_channel_parameter returns True (stub)."""
        result = handler.set_channel_parameter(0, "volume", 80)
        assert result is True

    def test_get_channel_parameter_default(self, handler: GSSysexHandler) -> None:
        """get_channel_parameter returns defaults for known params."""
        assert handler.get_channel_parameter(0, "volume") == 100
        assert handler.get_channel_parameter(0, "pan") == 64

    # -- data request (bulk dump) -------------------------------------------

    def test_data_request_system(self, handler: GSSysexHandler) -> None:
        """Data request for system params returns a valid sysex response."""
        # address (0x00, 0x00, 0x00) triggers system dump
        msg = _build_sysex(0x10, 0x11, (0x00, 0x00, 0x00), [])
        result = handler.process_message(msg)
        assert result is not None
        assert result[0] == 0xF0
        assert result[-1] == 0xF7
        assert len(result) >= 6

    def test_data_request_part(self, handler: GSSysexHandler) -> None:
        """Data request for a part returns part parameter dump."""
        msg = _build_sysex(0x10, 0x11, (0x01, 0x00, 0x00), [])  # part 0
        result = handler.process_message(msg)
        assert result is not None
        assert result[0] == 0xF0
        assert result[-1] == 0xF7

    def test_data_request_drum(self, handler: GSSysexHandler) -> None:
        """Data request for drum part returns drum dump."""
        msg = _build_sysex(0x10, 0x11, (0x10, 0x00, 0x00), [])  # drum part 0
        result = handler.process_message(msg)
        assert result is not None
        assert result[0] == 0xF0
        assert result[-1] == 0xF7

    # -- drum parameters ----------------------------------------------------
    #
    # NOTE: addr_high=0x10 maps to part 15 (0x10-1) via the part handler.
    # Drum params use addr_high >= 0x11 to avoid the part handler range
    # (0x01-0x10).  addr_high=0x11 → drum_part=1.

    def test_drum_map_low_note(self, handler: GSSysexHandler) -> None:
        """Drum part map low note parameter."""
        # address (0x11, 0x00, 0x00) → drum part 1, map_low_note
        msg = _build_sysex(0x10, 0x12, (0x11, 0x00, 0x00), [24])
        handler.process_message(msg)
        assert handler.drum_params[1]["map_low_note"] == 24

    def test_drum_pitch_offset(self, handler: GSSysexHandler) -> None:
        """Drum part pitch offset."""
        msg = _build_sysex(0x10, 0x12, (0x11, 0x00, 0x02), [70])
        handler.process_message(msg)
        assert handler.drum_params[1]["pitch_offset"] == 70

    def test_drum_key_param_level(self, handler: GSSysexHandler) -> None:
        """Drum key parameter (per-note level)."""
        # address (0x11, note, param) where note=36, param=0x01 (level)
        # drum_part = 0x11 - 0x10 = 1
        msg = _build_sysex(0x10, 0x12, (0x11, 36, 0x01), [100])
        handler.process_message(msg)
        key = (1, 36)  # drum_part=1, note=36
        assert key in handler.drum_key_params
        assert handler.drum_key_params[key]["level"] == 100

    def test_drum_key_param_pan(self, handler: GSSysexHandler) -> None:
        """Drum key parameter (per-note pan)."""
        msg = _build_sysex(0x10, 0x12, (0x11, 42, 0x02), [48])
        handler.process_message(msg)
        key = (1, 42)  # drum_part=1, note=42
        assert handler.drum_key_params[key]["pan"] == 48

    # -- common effects -----------------------------------------------------

    def test_common_effects_chorus_to_reverb(self, handler: GSSysexHandler) -> None:
        """Common effect: chorus-to-reverb send level."""
        # address (0x03, 0x00, 0x00) → chorus_to_reverb
        msg = _build_sysex(0x10, 0x12, (0x03, 0x00, 0x00), [64])
        # No state stored for this in a simple dict, but it shouldn't crash
        result = handler.process_message(msg)
        # No response expected
        assert result is None

    # -- variation (MFX) ----------------------------------------------------

    def test_variation_type(self, handler: GSSysexHandler) -> None:
        """Variation type parameter is accepted."""
        # address (0x06, 0x00, 0x00) → variation type
        msg = _build_sysex(0x10, 0x12, (0x06, 0x00, 0x00), [3])  # CHORUS type
        result = handler.process_message(msg)
        assert result is None  # no response expected

    # -- EQ parameters ------------------------------------------------------

    def test_eq_param_low_gain(self, handler: GSSysexHandler) -> None:
        """Per-part EQ low gain parameter."""
        # address (0x40, 0x00, part_num) → part EQ, low_gain
        msg = _build_sysex(0x10, 0x12, (0x40, 0x00, 0x05), [64])  # 0 dB
        result = handler.process_message(msg)
        assert result is None  # No response, no crash

    # -- edge cases ---------------------------------------------------------

    def test_devices_match_id_or_ten(self, handler: GSSysexHandler) -> None:
        """Custom device ID is accepted."""
        h = GSSysexHandler(device_id=0x15)
        msg = _build_sysex(0x15, 0x12, (0x00, 0x00, 0x01), [80])
        h.process_message(msg)
        assert h.master_volume == 80

    def test_key_range_clamping(self, handler: GSSysexHandler) -> None:
        """Part key params are clamped to valid range."""
        # velocity_range_low has min 1, send 0 → clamped to 1
        msg = _build_sysex(0x10, 0x12, (0x02, 0x00, 0x10), [0])
        handler.process_message(msg)
        assert handler.part_params[0]["velocity_range_low"] == 1

    def test_out_of_range_part_rejected(self, handler: GSSysexHandler) -> None:
        """Part number > 15 is silently rejected."""
        # addr_high = 0x11 → part_num = 16, which is out of range
        msg = _build_sysex(0x10, 0x12, (0x11, 0x00, 0x03), [100])
        result = handler.process_message(msg)
        assert result is None

    def test_many_sysex_in_sequence(self, handler: GSSysexHandler) -> None:
        """Multiple sysex messages processed sequentially work correctly."""
        # Part 0 via sysex (addr_high=0x01 is non-conflicting)
        msg = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x03), [64])
        handler.process_message(msg)
        # Parts 1-3 use set_part_parameter (addr_high 0x02-0x04 are reserved)
        handler.set_part_parameter(1, 0x00, 0x03, 74)
        handler.set_part_parameter(2, 0x00, 0x03, 84)
        handler.set_part_parameter(3, 0x00, 0x03, 94)

        msg_r = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x00), [7])
        handler.process_message(msg_r)

        assert handler.master_volume == 100  # unchanged
        assert handler.part_params[0]["volume"] == 64
        assert handler.part_params[1]["volume"] == 74
        assert handler.part_params[2]["volume"] == 84
        assert handler.part_params[3]["volume"] == 94
        assert handler.reverb_params["type"] == 7

    def test_reset_after_mutations(self, handler: GSSysexHandler) -> None:
        """After setting many values, reset restores defaults."""
        # Mutate
        msg1 = _build_sysex(0x10, 0x12, (0x00, 0x00, 0x01), [127])
        handler.process_message(msg1)
        msg2 = _build_sysex(0x10, 0x12, (0x01, 0x00, 0x03), [50])
        handler.process_message(msg2)

        handler.reset()

        assert handler.master_volume == 100
        assert handler.part_params[0]["volume"] == 100
        assert handler.gs_enabled is True

    def test_reverb_chorus_independence(self, handler: GSSysexHandler) -> None:
        """Reverb and Chorus parameter changes don't interfere."""
        msg_r = _build_sysex(0x10, 0x12, (0x05, 0x00, 0x01), [100])
        handler.process_message(msg_r)
        msg_c = _build_sysex(0x10, 0x12, (0x04, 0x00, 0x02), [50])
        handler.process_message(msg_c)

        assert handler.reverb_params["level"] == 100
        assert handler.chorus_params["rate"] == 50
