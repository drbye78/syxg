"""
Tests for XGReceiveChannelManager.

Exercises the complete XG receive channel mapping system: default state,
channel assignment, special channel values (OFF/ALL), MIDI message routing,
mapping import/export, reset, and edge cases.
"""

from __future__ import annotations

import pytest
from typing import Any

from synth.protocols.xg.xg_receive_channel_manager import XGReceiveChannelManager


class TestXGReceiveChannelManager:
    """Comprehensive tests for XGReceiveChannelManager."""

    @pytest.fixture
    def mgr(self) -> XGReceiveChannelManager:
        return XGReceiveChannelManager(num_parts=16)

    # ------------------------------------------------------------------ #
    #  Default state                                                      #
    # ------------------------------------------------------------------ #

    def test_default_mapping_part_n_receives_from_channel_n(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Default mapping: part N receives from MIDI channel N (0-15)."""
        for part_id in range(16):
            ch = mgr.get_receive_channel(part_id)
            assert ch == part_id, f"Expected part {part_id} to receive from CH {part_id}, got {ch}"

    def test_get_parts_for_midi_channel_one_to_one(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Each MIDI channel maps to exactly one part in default 1:1 mode."""
        for midi_ch in range(16):
            parts = mgr.get_parts_for_midi_channel(midi_ch)
            assert parts == [midi_ch], (
                f"Expected MIDI CH {midi_ch} -> [Part {midi_ch}], got {parts}"
            )

    def test_get_channel_mapping_status_returns_expected_keys(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """get_channel_mapping_status() returns dict with expected structure."""
        status = mgr.get_channel_mapping_status()
        assert isinstance(status, dict)
        assert "total_parts" in status
        assert "mappings" in status
        assert "reverse_mappings" in status
        assert "conflicts" in status
        assert status["total_parts"] == 16
        assert len(status["mappings"]) == 16
        assert len(status["conflicts"]) == 0  # 1:1 = no conflicts

    # ------------------------------------------------------------------ #
    #  Setting channels                                                   #
    # ------------------------------------------------------------------ #

    def test_set_receive_channel_changes_part_channel(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """set_receive_channel changes a part's receive channel."""
        result = mgr.set_receive_channel(part_id=0, midi_channel=7)
        assert result is True
        assert mgr.get_receive_channel(0) == 7

    def test_set_receive_channel_max_channel(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Setting midi_channel=15 (max valid) works correctly."""
        result = mgr.set_receive_channel(part_id=0, midi_channel=15)
        assert result is True
        assert mgr.get_receive_channel(0) == 15

    def test_get_receive_channel_returns_updated_value(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """get_receive_channel reflects the last set value."""
        mgr.set_receive_channel(0, 3)
        assert mgr.get_receive_channel(0) == 3
        mgr.set_receive_channel(0, 12)
        assert mgr.get_receive_channel(0) == 12

    def test_set_receive_channel_part_out_of_range_returns_false(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Setting channel for a part_id outside valid range returns False."""
        assert mgr.set_receive_channel(part_id=-1, midi_channel=0) is False
        assert mgr.set_receive_channel(part_id=16, midi_channel=0) is False
        assert mgr.set_receive_channel(part_id=999, midi_channel=0) is False

    def test_set_receive_channel_invalid_channel_returns_false(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Setting an invalid midi_channel value returns False."""
        assert mgr.set_receive_channel(part_id=0, midi_channel=-1) is False
        assert mgr.set_receive_channel(part_id=0, midi_channel=16) is False
        assert mgr.set_receive_channel(part_id=0, midi_channel=100) is False
        assert mgr.set_receive_channel(part_id=0, midi_channel=253) is False
        # 254=OFF and 255=ALL ARE valid — make sure they are NOT rejected
        assert mgr.set_receive_channel(part_id=0, midi_channel=254) is True
        assert mgr.set_receive_channel(part_id=0, midi_channel=255) is True

    # ------------------------------------------------------------------ #
    #  Special channels: OFF / ALL                                        #
    # ------------------------------------------------------------------ #

    def test_receive_channel_off_disables_part(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """RECEIVE_CHANNEL_OFF (254) disables part — not in any channel list."""
        mgr.set_receive_channel(part_id=0, midi_channel=XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        assert mgr.get_receive_channel(0) == XGReceiveChannelManager.RECEIVE_CHANNEL_OFF
        # Part should not appear in any MIDI channel's part list
        for midi_ch in range(16):
            parts = mgr.get_parts_for_midi_channel(midi_ch)
            assert 0 not in parts, f"Part 0 should not appear in MIDI CH {midi_ch} parts"

    def test_receive_channel_all_broadcasts_to_all_channels(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """RECEIVE_CHANNEL_ALL (255) — part appears in all 16 channel lists."""
        mgr.set_receive_channel(part_id=0, midi_channel=XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        assert mgr.get_receive_channel(0) == XGReceiveChannelManager.RECEIVE_CHANNEL_ALL
        for midi_ch in range(16):
            parts = mgr.get_parts_for_midi_channel(midi_ch)
            assert 0 in parts, f"Part 0 should appear in MIDI CH {midi_ch} parts when ALL set"

    def test_receive_channel_all_with_multiple_parts(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Multiple parts in ALL mode all appear in every channel's list."""
        mgr.set_receive_channel(0, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        mgr.set_receive_channel(1, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        for midi_ch in range(16):
            parts = mgr.get_parts_for_midi_channel(midi_ch)
            assert 0 in parts
            assert 1 in parts

    # ------------------------------------------------------------------ #
    #  Routing                                                             #
    # ------------------------------------------------------------------ #

    def test_route_midi_message_routes_to_correct_part(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """route_midi_message routes a message to the correct target part."""
        # Part 5 is on CH 5 by default — move it away so only part 0 listens
        mgr.set_receive_channel(5, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.set_receive_channel(0, 5)  # Part 0 listens on CH 5
        routed = mgr.route_midi_message(5, "note_on", {"note": 60, "velocity": 100})
        assert len(routed) == 1
        part_id, data = routed[0]
        assert part_id == 0
        assert data["original_channel"] == 5
        assert data["target_part"] == 0
        assert data["note"] == 60
        assert data["velocity"] == 100

    def test_route_midi_message_disabled_part_returns_empty(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Routing to a disabled part returns empty list."""
        mgr.set_receive_channel(0, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        # Part 0 was on CH 0 by default, now disabled — CH 0 has no listeners
        routed = mgr.route_midi_message(0, "note_on", {"note": 60, "velocity": 100})
        assert routed == []

    def test_route_midi_message_all_channels_part(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """A part set to ALL receives messages on every channel."""
        mgr.set_receive_channel(0, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        for midi_ch in range(16):
            routed = mgr.route_midi_message(midi_ch, "cc", {"controller": 7, "value": 100})
            assert len(routed) >= 1, f"Part 0 should receive on CH {midi_ch}"
            assert routed[0][0] == 0

    def test_route_midi_message_routes_to_multiple_parts_when_layered(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Multiple parts on the same channel all receive routed messages."""
        # Part 2 is on CH 2 by default — move it away to avoid interference
        mgr.set_receive_channel(2, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.set_receive_channel(0, 2)
        mgr.set_receive_channel(1, 2)  # Both parts 0 and 1 on CH 2
        routed = mgr.route_midi_message(2, "note_on", {"note": 64, "velocity": 80})
        assert len(routed) == 2
        part_ids = {p for p, _ in routed}
        assert part_ids == {0, 1}

    def test_route_midi_message_no_targets_returns_empty(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Routing on a channel with no listeners returns empty list."""
        # Remove all listeners from CH 0 by setting part 0 to a different channel
        mgr.set_receive_channel(0, 1)
        routed = mgr.route_midi_message(0, "note_on", {"note": 60, "velocity": 100})
        assert routed == []

    def test_route_midi_message_invalid_channel_returns_empty(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Routing on an out-of-range MIDI channel returns empty list."""
        routed = mgr.route_midi_message(99, "note_on", {"note": 60, "velocity": 100})
        assert routed == []

    # ------------------------------------------------------------------ #
    #  Reset to XG defaults                                                #
    # ------------------------------------------------------------------ #

    def test_reset_to_xg_defaults_restores_mapping(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """reset_to_xg_defaults restores the default 1:1 mapping."""
        # Remap several parts
        mgr.set_receive_channel(0, 7)
        mgr.set_receive_channel(1, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.set_receive_channel(2, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        mgr.reset_to_xg_defaults()
        for part_id in range(16):
            assert mgr.get_receive_channel(part_id) == part_id

    def test_get_channel_mapping_status_after_reset_matches_defaults(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """After reset, mapping status matches initial defaults."""
        mgr.set_receive_channel(0, 7)
        mgr.reset_to_xg_defaults()
        status = mgr.get_channel_mapping_status()
        assert status["total_parts"] == 16
        assert len(status["conflicts"]) == 0
        for part_id in range(16):
            assert status["mappings"][f"part_{part_id}"]["receive_channel"] == part_id

    # ------------------------------------------------------------------ #
    #  Export / Import                                                     #
    # ------------------------------------------------------------------ #

    def test_export_mapping_returns_valid_structure(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """export_mapping returns a dict with receive_channels and version."""
        exported = mgr.export_mapping()
        assert "receive_channels" in exported
        assert "version" in exported
        assert exported["version"] == "1.0"
        assert isinstance(exported["receive_channels"], list)
        assert len(exported["receive_channels"]) == 16
        assert exported["receive_channels"] == list(range(16))

    def test_import_mapping_applies_correctly(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """import_mapping correctly applies a saved mapping."""
        # Create a custom mapping
        custom_channels = list(range(16))
        custom_channels[0] = 15
        custom_channels[1] = XGReceiveChannelManager.RECEIVE_CHANNEL_OFF
        custom_channels[2] = XGReceiveChannelManager.RECEIVE_CHANNEL_ALL
        mapping_data = {"receive_channels": custom_channels, "version": "1.0"}
        result = mgr.import_mapping(mapping_data)
        assert result is True
        assert mgr.get_receive_channel(0) == 15
        assert mgr.get_receive_channel(1) == XGReceiveChannelManager.RECEIVE_CHANNEL_OFF
        assert mgr.get_receive_channel(2) == XGReceiveChannelManager.RECEIVE_CHANNEL_ALL

    def test_import_mapping_rebuilds_reverse_lookups(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """import_mapping rebuilds reverse lookups correctly."""
        custom = list(range(16))
        custom[0] = XGReceiveChannelManager.RECEIVE_CHANNEL_ALL
        mgr.import_mapping({"receive_channels": custom, "version": "1.0"})
        # Part 0 should be in every channel's part list
        for midi_ch in range(16):
            assert 0 in mgr.get_parts_for_midi_channel(midi_ch)

    def test_import_mapping_wrong_length_returns_false(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """import_mapping with wrong-length data returns False."""
        mapping_data = {"receive_channels": [0, 1, 2], "version": "1.0"}  # Only 3 elements
        result = mgr.import_mapping(mapping_data)
        assert result is False

    def test_import_mapping_missing_key_returns_false(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """import_mapping without receive_channels key returns False."""
        result = mgr.import_mapping({"version": "1.0"})
        assert result is False

    def test_import_mapping_empty_dict_returns_false(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """import_mapping with empty dict returns False."""
        result = mgr.import_mapping({})
        assert result is False

    # ------------------------------------------------------------------ #
    #  Edge cases                                                         #
    # ------------------------------------------------------------------ #

    def test_single_part_manager(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Manager with num_parts=1 works correctly."""
        single = XGReceiveChannelManager(num_parts=1)
        assert single.get_receive_channel(0) == 0
        assert single.get_receive_channel(1) is None
        assert single.set_receive_channel(0, 5) is True
        assert single.set_receive_channel(1, 5) is False
        # After setting part 0 to CH 5, routing on CH 5 should find it
        routed = single.route_midi_message(5, "note_on", {"note": 60, "velocity": 100})
        assert len(routed) == 1
        assert routed[0][0] == 0

    def test_max_parts_manager(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Manager with num_parts=32 works correctly."""
        big = XGReceiveChannelManager(num_parts=32)
        assert big.get_receive_channel(31) == 31
        assert big.get_receive_channel(32) is None
        # Default mapping for first 32 parts
        for part_id in range(32):
            assert big.get_receive_channel(part_id) == part_id
        # Set a high part ID
        assert big.set_receive_channel(31, 0) is True
        assert big.get_receive_channel(31) == 0

    def test_get_parts_for_midi_channel_invalid_returns_empty_list(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """get_parts_for_midi_channel with out-of-range channel returns []."""
        assert mgr.get_parts_for_midi_channel(-1) == []
        assert mgr.get_parts_for_midi_channel(16) == []
        assert mgr.get_parts_for_midi_channel(255) == []

    def test_get_receive_channel_invalid_part_returns_none(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """get_receive_channel with invalid part ID returns None."""
        assert mgr.get_receive_channel(-1) is None
        assert mgr.get_receive_channel(16) is None
        assert mgr.get_receive_channel(999) is None

    def test_export_mapping_reflects_custom_mapping(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """export_mapping returns the current mapping after changes."""
        mgr.set_receive_channel(0, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.set_receive_channel(1, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        exported = mgr.export_mapping()
        assert exported["receive_channels"][0] == XGReceiveChannelManager.RECEIVE_CHANNEL_OFF
        assert exported["receive_channels"][1] == XGReceiveChannelManager.RECEIVE_CHANNEL_ALL

    def test_import_export_round_trip(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """Exporting then importing the same data produces identical state."""
        # Create a non-trivial mapping
        mgr.set_receive_channel(0, 7)
        mgr.set_receive_channel(1, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.set_receive_channel(3, XGReceiveChannelManager.RECEIVE_CHANNEL_ALL)
        exported = mgr.export_mapping()
        # Create a fresh manager and import
        fresh = XGReceiveChannelManager(num_parts=16)
        fresh.import_mapping(exported)
        for part_id in range(16):
            assert fresh.get_receive_channel(part_id) == mgr.get_receive_channel(part_id)

    def test_route_midi_message_preserves_extra_data(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """route_midi_message preserves all extra keys in message_data."""
        data: dict[str, Any] = {
            "note": 72,
            "velocity": 90,
            "detune": 0.5,
            "custom_field": "hello",
        }
        routed = mgr.route_midi_message(0, "note_on", data)
        assert len(routed) == 1
        _, routed_data = routed[0]
        assert routed_data["note"] == 72
        assert routed_data["velocity"] == 90
        assert routed_data["detune"] == 0.5
        assert routed_data["custom_field"] == "hello"
        assert routed_data["original_channel"] == 0
        assert routed_data["target_part"] == 0

    def test_conflicts_detected_when_multiple_parts_on_same_channel(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """get_channel_mapping_status reports conflicts for layered parts."""
        mgr.set_receive_channel(0, 5)
        mgr.set_receive_channel(1, 5)  # Conflict: both on CH 5
        status = mgr.get_channel_mapping_status()
        assert len(status["conflicts"]) == 1
        assert status["conflicts"][0]["midi_channel"] == 5
        assert 0 in status["conflicts"][0]["parts"]
        assert 1 in status["conflicts"][0]["parts"]

    def test_string_representation(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """__str__ produces a readable mapping summary."""
        s = str(mgr)
        assert "XG Receive Channel Mapping" in s
        assert "Part  0:" in s
        assert "Part 15:" in s

    def test_repr(self, mgr: XGReceiveChannelManager) -> None:
        """__repr__ shows class name and part count."""
        r = repr(mgr)
        assert "XGReceiveChannelManager" in r
        assert "parts=16" in r

    def test_reset_clears_all_channels(
        self, mgr: XGReceiveChannelManager
    ) -> None:
        """reset_to_xg_defaults resets ALL parts including high ones."""
        for i in range(16):
            mgr.set_receive_channel(i, XGReceiveChannelManager.RECEIVE_CHANNEL_OFF)
        mgr.reset_to_xg_defaults()
        for part_id in range(16):
            assert mgr.get_receive_channel(part_id) == part_id
