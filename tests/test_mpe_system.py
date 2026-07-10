"""MPE System Unit Tests — direct MPEManager tests."""
from __future__ import annotations

import pytest

from synth.mpe.mpe_manager import MPEManager, MPENote


class TestMPEManager:
    """Direct MPEManager unit tests."""

    @pytest.fixture
    def manager(self):
        return MPEManager(max_channels=16)

    def test_note_on_off(self, manager):
        """Basic note on/off lifecycle."""
        note = manager.process_note_on(1, 60, 100)
        assert note is not None
        assert note.note_number == 60
        assert note.active
        assert (1, 60) in manager.active_notes

        released = manager.process_note_off(1, 60, 0)
        assert released is not None
        assert not released.active
        assert (1, 60) not in manager.active_notes

    def test_one_note_per_member_channel(self, manager):
        """Member channel enforces one-note limit."""
        manager.process_note_on(1, 60, 100)
        manager.process_note_on(1, 64, 100)  # same channel, new note
        # Only the latest note should be active on channel 1
        notes_on_ch1 = [n for n in manager.active_notes.values() if n.channel == 1]
        assert len(notes_on_ch1) == 1
        assert notes_on_ch1[0].note_number == 64

    def test_dynamic_channel_assignment(self, manager):
        """Master channel note-on assigns to member channel."""
        # Zone 1: master=7, members=0-6.
        # Channel 7 is the master — note-on gets routed to an available member.
        note = manager.process_note_on(7, 60, 100)
        assert note is not None
        assert note.channel != 7  # Should be on a member channel
        assert note.channel in range(0, 7)  # member channels of zone 1

    def test_all_member_channels_full(self, manager):
        """When all members full, oldest is stolen."""
        # Send notes via master channel (7) to dynamically assign to members 0-6
        for i in range(7):
            manager.process_note_on(7, 60 + i, 100)  # master routes to members
        # Try one more — should steal oldest
        note = manager.process_note_on(0, 80, 100)
        assert note is not None  # Should steal oldest

    def test_master_channel_routing_timbre(self, manager):
        """Master channel CC74 updates all member note timbre."""
        # Create notes on two different member channels
        mpe1 = manager.process_note_on(1, 60, 100)
        mpe2 = manager.process_note_on(2, 64, 100)

        # Send timbre on master channel (7)
        manager.process_timbre(7, 100)  # CC74 value 100

        assert mpe1.timbre == pytest.approx(100 / 127.0)
        assert mpe2.timbre == pytest.approx(100 / 127.0)

    def test_member_channel_routing_timbre(self, manager):
        """Member channel CC74 only affects that channel's note."""
        mpe1 = manager.process_note_on(1, 60, 100)
        mpe2 = manager.process_note_on(2, 64, 100)

        # Send timbre on member channel 1 only
        manager.process_timbre(1, 100)

        assert mpe1.timbre == pytest.approx(100 / 127.0)
        assert mpe2.timbre == pytest.approx(0.0)  # unchanged

    def test_pitch_bend_range(self, manager):
        """Pitch bend uses zone.pitch_bend_range."""
        mpe_note = manager.process_note_on(1, 60, 100)
        # Default range is 48 semitones
        manager.process_pitch_bend(1, 16383)  # max bend up
        assert mpe_note.pitch_bend == pytest.approx(48.0, rel=0.01)

    def test_reset(self, manager):
        """Reset clears all active notes."""
        manager.process_note_on(1, 60, 100)
        manager.process_note_on(2, 64, 100)
        manager.reset_all_notes()
        assert len(manager.active_notes) == 0

    def test_zone_configuration(self, manager):
        """Default zone configuration."""
        assert len(manager.zones) == 2
        # Zone 1: lower=0, upper=7 → master=7, members=0-6
        assert manager.zones[0].lower_channel == 0
        assert manager.zones[0].upper_channel == 7
        assert manager.zones[0].master_channel == 7
        assert manager.zones[0].member_channels == [0, 1, 2, 3, 4, 5, 6]
        # Zone 2: lower=8, upper=15 → master=15, members=8-14
        assert manager.zones[1].lower_channel == 8
        assert manager.zones[1].upper_channel == 15
        assert manager.zones[1].master_channel == 15
        assert manager.zones[1].member_channels == [8, 9, 10, 11, 12, 13, 14]

    def test_slide_control(self, manager):
        """CC75 slide control."""
        mpe_note = manager.process_note_on(1, 60, 100)
        manager.process_slide(1, 64)
        assert mpe_note.slide == pytest.approx(64 / 127.0)

    def test_lift_control(self, manager):
        """CC76 lift control."""
        mpe_note = manager.process_note_on(1, 60, 100)
        manager.process_lift(1, 100)
        assert mpe_note.lift == pytest.approx(100 / 127.0)

    def test_poly_pressure(self, manager):
        """Polyphonic pressure (aftertouch) updates correct note."""
        mpe_note = manager.process_note_on(1, 60, 100)
        manager.process_poly_pressure(1, 60, 80)
        assert mpe_note.pressure == pytest.approx(80 / 127.0)

    def test_master_channel_routes_pitch_bend(self, manager):
        """Master channel pitch bend affects all member notes."""
        mpe1 = manager.process_note_on(1, 60, 100)
        mpe2 = manager.process_note_on(2, 64, 100)

        # Pitch bend on master channel (7) goes to all members
        manager.process_pitch_bend(7, 16383)

        assert mpe1.pitch_bend == pytest.approx(48.0, rel=0.01)
        assert mpe2.pitch_bend == pytest.approx(48.0, rel=0.01)

    def test_master_channel_routes_slide(self, manager):
        """Master channel CC75 affects all member notes."""
        mpe1 = manager.process_note_on(1, 60, 100)
        mpe2 = manager.process_note_on(2, 64, 100)

        manager.process_slide(7, 100)  # on master channel

        assert mpe1.slide == pytest.approx(100 / 127.0)
        assert mpe2.slide == pytest.approx(100 / 127.0)

    def test_master_channel_routes_lift(self, manager):
        """Master channel CC76 affects all member notes."""
        mpe1 = manager.process_note_on(1, 60, 100)
        mpe2 = manager.process_note_on(2, 64, 100)

        manager.process_lift(7, 100)  # on master channel

        assert mpe1.lift == pytest.approx(100 / 127.0)
        assert mpe2.lift == pytest.approx(100 / 127.0)

    def test_configure_zone_pitch_bend_range(self, manager):
        """configure_zone sets pitch bend range on the zone."""
        manager.configure_zone(1, 0, 7, pitch_bend_range=24)
        assert manager.zones[0].pitch_bend_range == 24

    def test_mpe_disabled_returns_none(self, manager):
        """When MPE is disabled, process_note_on returns None."""
        manager.set_mpe_enabled(False)
        note = manager.process_note_on(1, 60, 100)
        assert note is None

    def test_get_mpe_info_structure(self, manager):
        """get_mpe_info returns expected keys."""
        info = manager.get_mpe_info()
        assert "enabled" in info
        assert "zones" in info
        assert "active_notes_count" in info
        assert "active_notes" in info

    def test_duplicate_note_replaces(self, manager):
        """Same note on same channel replaces the old note."""
        n1 = manager.process_note_on(1, 60, 100)
        n2 = manager.process_note_on(1, 60, 80)
        # A new MPENote is created (the old one is removed first)
        assert n1.active is False  # old note was deactivated
        assert n2.active is True
        assert n2.velocity == 80
        # After replacement, only one entry for (1, 60) — the new note
        assert len(manager.active_notes) == 1
        assert manager.active_notes[(1, 60)] is n2
