"""
MPE (Microtonal Expression) Manager

Comprehensive MPE implementation for expressive microtonal control,
providing per-note parameter modulation and advanced MIDI expression.
"""

from __future__ import annotations

import threading
from typing import Any


class MPENote:
    """
    Represents a single MPE note with full parameter control.

    Each MPE note can have independent control of pitch, timbre, pressure,
    and other parameters for expressive microtonal playing.
    """

    def __init__(self, note_number: int, channel: int, velocity: int):
        """
        Initialize MPE note.

        Args:
            note_number: MIDI note number (0-127)
            channel: MIDI channel this note belongs to
            velocity: Initial velocity (0-127)
        """
        # Basic note information
        self.note_number = note_number
        self.channel = channel
        self.velocity = velocity
        self.active = True

        # MPE parameters
        self.pitch_bend = 0.0  # Pitch bend in semitones (-48 to +48)
        self.timbre = 0.0  # Timbre control (0.0-1.0)
        self.pressure = 0.0  # Aftertouch pressure (0.0-1.0)
        self.slide = 0.0  # Slide position (0.0-1.0)
        self.lift = 0.0  # Lift position (0.0-1.0)

        # Derived values
        self.frequency = 440.0 * (2.0 ** ((note_number - 69) / 12.0))
        self.adjusted_frequency = self.frequency

        # Timing information
        self.start_time = 0.0
        self.note_on_time = 0.0
        self.note_off_time = None

        # Voice assignment
        self.voice_id = None

        # Update derived values
        self._update_derived_values()

    def _update_derived_values(self):
        """Update frequency and other derived values based on MPE parameters."""
        # Calculate adjusted frequency from pitch bend
        pitch_ratio = 2.0 ** (self.pitch_bend / 12.0)
        self.adjusted_frequency = self.frequency * pitch_ratio

    def update_pitch_bend(self, bend_value: int):
        """
        Update pitch bend for this note.

        Args:
            bend_value: 14-bit pitch bend value (0-16383, center=8192)
        """
        # Convert 14-bit MIDI pitch bend to semitones
        # Standard range is ±2 semitones, but MPE allows much more
        bend_range = 48.0  # ±48 semitones for full MPE range
        normalized_bend = (bend_value - 8192) / 8192.0
        self.pitch_bend = normalized_bend * bend_range
        self._update_derived_values()

    def update_timbre(self, timbre_value: int):
        """
        Update timbre for this note.

        Args:
            timbre_value: Timbre value (0-127)
        """
        self.timbre = timbre_value / 127.0

    def update_pressure(self, pressure_value: int):
        """
        Update pressure (aftertouch) for this note.

        Args:
            pressure_value: Pressure value (0-127)
        """
        self.pressure = pressure_value / 127.0

    def update_slide(self, slide_value: int):
        """
        Update slide position for this note.

        Args:
            slide_value: Slide value (0-127)
        """
        self.slide = slide_value / 127.0

    def update_lift(self, lift_value: int):
        """
        Update lift position for this note.

        Args:
            lift_value: Lift value (0-127)
        """
        self.lift = lift_value / 127.0

    def note_off(self, velocity: int = 0):
        """Mark note as released."""
        self.active = False
        self.note_off_time = 0.0  # Would be set by caller

    def get_mpe_info(self) -> dict[str, Any]:
        """Get comprehensive MPE information for this note."""
        return {
            "note_number": self.note_number,
            "channel": self.channel,
            "velocity": self.velocity,
            "active": self.active,
            "pitch_bend": self.pitch_bend,
            "timbre": self.timbre,
            "pressure": self.pressure,
            "slide": self.slide,
            "lift": self.lift,
            "frequency": self.frequency,
            "adjusted_frequency": self.adjusted_frequency,
            "voice_id": self.voice_id,
        }


class MPEChannel:
    """
    MPE channel configuration and state management.

    Each MPE zone consists of a master channel and multiple member channels.
    """

    def __init__(self, master_channel: int, member_channels: list[int]):
        """
        Initialize MPE channel.

        Args:
            master_channel: Master channel number
            member_channels: List of member channel numbers
        """
        self.master_channel = master_channel
        self.member_channels = member_channels.copy()
        self.all_channels = [master_channel] + member_channels

        # Channel configuration
        self.pitch_bend_range = 48  # ±48 semitones
        self.timbre_cc = 74  # CC74 for timbre
        self.pressure_active = True

        # Active notes on this channel
        self.active_notes: dict[int, MPENote] = {}

        # Channel state
        self.enabled = True

    def is_member_channel(self, channel: int) -> bool:
        """Check if channel is a member of this MPE zone."""
        return channel in self.member_channels

    def is_master_channel(self, channel: int) -> bool:
        """Check if channel is the master of this MPE zone."""
        return channel == self.master_channel

    def add_note(self, note: MPENote):
        """Add note to this channel."""
        self.active_notes[note.note_number] = note

    def remove_note(self, note_number: int) -> MPENote | None:
        """Remove note from this channel."""
        return self.active_notes.pop(note_number, None)

    def get_note(self, note_number: int) -> MPENote | None:
        """Get note by number."""
        return self.active_notes.get(note_number)

    def get_active_notes(self) -> list[MPENote]:
        """Get all active notes."""
        return list(self.active_notes.values())

    def clear_all_notes(self):
        """Clear all active notes."""
        self.active_notes.clear()

    def get_channel_info(self) -> dict[str, Any]:
        """Get channel configuration and status."""
        return {
            "master_channel": self.master_channel,
            "member_channels": self.member_channels.copy(),
            "all_channels": self.all_channels.copy(),
            "pitch_bend_range": self.pitch_bend_range,
            "timbre_cc": self.timbre_cc,
            "pressure_active": self.pressure_active,
            "enabled": self.enabled,
            "active_notes_count": len(self.active_notes),
        }


class MPEZone:
    """
    MPE zone configuration.

    MPE divides the 16 MIDI channels into zones for independent control.
    """

    def __init__(self, zone_id: int, lower_channel: int, upper_channel: int):
        """
        Initialize MPE zone.

        Args:
            zone_id: Zone identifier
            lower_channel: Lower channel boundary
            upper_channel: Upper channel boundary
        """
        self.zone_id = zone_id
        self.lower_channel = lower_channel
        self.upper_channel = upper_channel

        # Zone properties
        self.enabled = True
        self.pitch_bend_range = 48  # ±48 semitones

        # Calculate master and member channels
        if upper_channel > lower_channel:
            self.master_channel = upper_channel
            self.member_channels = list(range(lower_channel, upper_channel))
        else:
            self.master_channel = lower_channel
            self.member_channels = []

        # Create MPE channel
        self.mpe_channel = MPEChannel(self.master_channel, self.member_channels)

    def contains_channel(self, channel: int) -> bool:
        """Check if channel is in this zone."""
        return self.lower_channel <= channel <= self.upper_channel

    def get_zone_info(self) -> dict[str, Any]:
        """Get zone configuration."""
        return {
            "zone_id": self.zone_id,
            "lower_channel": self.lower_channel,
            "upper_channel": self.upper_channel,
            "enabled": self.enabled,
            "pitch_bend_range": self.pitch_bend_range,
            "master_channel": self.master_channel,
            "member_channels": self.member_channels.copy(),
            "channel_info": self.mpe_channel.get_channel_info(),
        }


class MPEManager:
    """
    Main MPE (Microtonal Expression) Manager

    Comprehensive MPE implementation providing per-note control,
    zone management, and microtonal expression capabilities.
    """

    def __init__(self, max_channels: int = 16):
        """
        Initialize MPE manager.

        Args:
            max_channels: Maximum MIDI channels to support
        """
        self.max_channels = max_channels

        # MPE zones (typically 2 zones covering channels 1-8 and 9-16)
        self.zones = self._create_default_zones()

        # Global MPE settings
        self.mpe_enabled = True
        self.global_pitch_bend_range = 48

        # Active notes registry
        self.active_notes: dict[tuple[int, int], MPENote] = {}  # (channel, note) -> MPENote

        # Thread safety
        self.lock = threading.RLock()

    def _create_default_zones(self) -> list[MPEZone]:
        """Create default MPE zones."""
        zones = []

        # Zone 1: Channels 1-8 (MIDI channels 0-7)
        zones.append(MPEZone(1, 0, 7))

        # Zone 2: Channels 9-16 (MIDI channels 8-15)
        zones.append(MPEZone(2, 8, 15))

        return zones

    def get_zone_for_channel(self, channel: int) -> MPEZone | None:
        """Get MPE zone containing the specified channel."""
        for zone in self.zones:
            if zone.contains_channel(channel):
                return zone
        return None

    def process_note_on(self, channel: int, note: int, velocity: int) -> MPENote | None:
        """
        Process MPE note-on event.

        Args:
            channel: MIDI channel
            note: Note number
            velocity: Velocity

        Returns:
            MPENote object if MPE is active, None otherwise
        """
        with self.lock:
            if not self.mpe_enabled:
                return None

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return None

            # Create MPE note
            mpe_note = MPENote(note, channel, velocity)
            mpe_note.note_on_time = 0.0  # Would be set by caller

            # Add to zone and registry
            zone.mpe_channel.add_note(mpe_note)
            self.active_notes[(channel, note)] = mpe_note

            return mpe_note

    def process_note_off(self, channel: int, note: int, velocity: int = 0) -> MPENote | None:
        """
        Process MPE note-off event.

        Args:
            channel: MIDI channel
            note: Note number
            velocity: Release velocity

        Returns:
            MPENote object that was released, None if not found
        """
        with self.lock:
            note_key = (channel, note)
            if note_key not in self.active_notes:
                return None

            mpe_note = self.active_notes[note_key]

            # Mark note as released
            mpe_note.note_off(velocity)

            # Remove from zone and registry
            zone = self.get_zone_for_channel(channel)
            if zone:
                zone.mpe_channel.remove_note(note)

            del self.active_notes[note_key]

            return mpe_note

    def process_pitch_bend(self, channel: int, bend_value: int):
        """
        Process MPE pitch bend.

        Args:
            channel: MIDI channel
            bend_value: 14-bit pitch bend value
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return

            # Apply pitch bend to all active notes on this channel
            for note in zone.mpe_channel.get_active_notes():
                note.update_pitch_bend(bend_value)

    def process_timbre(self, channel: int, timbre_value: int):
        """
        Process MPE timbre control.

        Args:
            channel: MIDI channel
            timbre_value: Timbre value (0-127)
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return

            # Apply timbre to all active notes on this channel
            for note in zone.mpe_channel.get_active_notes():
                note.update_timbre(timbre_value)

    def process_pressure(self, channel: int, pressure_value: int):
        """
        Process MPE pressure (aftertouch).

        Args:
            channel: MIDI channel
            pressure_value: Pressure value (0-127)
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return

            # Apply pressure to all active notes on this channel
            for note in zone.mpe_channel.get_active_notes():
                note.update_pressure(pressure_value)

    def process_poly_pressure(self, channel: int, note: int, pressure_value: int):
        """
        Process MPE per-note pressure.

        Args:
            channel: MIDI channel
            note: Note number
            pressure_value: Pressure value (0-127)
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            note_key = (channel, note)
            if note_key in self.active_notes:
                self.active_notes[note_key].update_pressure(pressure_value)

    def process_slide(self, channel: int, slide_value: int):
        """
        Process MPE slide control.

        Args:
            channel: MIDI channel
            slide_value: Slide value (0-127)
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return

            # Apply slide to all active notes on this channel
            for note in zone.mpe_channel.get_active_notes():
                note.update_slide(slide_value)

    def process_lift(self, channel: int, lift_value: int):
        """
        Process MPE lift control.

        Args:
            channel: MIDI channel
            lift_value: Lift value (0-127)
        """
        with self.lock:
            if not self.mpe_enabled:
                return

            zone = self.get_zone_for_channel(channel)
            if not zone or not zone.enabled:
                return

            # Apply lift to all active notes on this channel
            for note in zone.mpe_channel.get_active_notes():
                note.update_lift(lift_value)

    def get_active_mpe_notes(self) -> list[MPENote]:
        """Get all currently active MPE notes."""
        with self.lock:
            return list(self.active_notes.values())

    def get_channel_mpe_notes(self, channel: int) -> list[MPENote]:
        """Get active MPE notes for a specific channel."""
        with self.lock:
            zone = self.get_zone_for_channel(channel)
            if zone:
                return zone.mpe_channel.get_active_notes()
            return []

    def configure_zone(
        self, zone_id: int, lower_channel: int, upper_channel: int, pitch_bend_range: int = 48
    ):
        """
        Configure MPE zone.

        Args:
            zone_id: Zone identifier (1 or 2)
            lower_channel: Lower channel boundary
            upper_channel: Upper channel boundary
            pitch_bend_range: Pitch bend range in semitones
        """
        with self.lock:
            if 1 <= zone_id <= len(self.zones):
                zone = self.zones[zone_id - 1]
                zone.lower_channel = lower_channel
                zone.upper_channel = upper_channel
                zone.pitch_bend_range = pitch_bend_range

                # Recreate MPE channel
                zone.mpe_channel = MPEChannel(zone.master_channel, zone.member_channels)

    def set_mpe_enabled(self, enabled: bool):
        """Enable or disable MPE globally."""
        with self.lock:
            self.mpe_enabled = enabled

    def reset_all_notes(self):
        """Reset all active MPE notes."""
        with self.lock:
            for note in self.active_notes.values():
                note.active = False

            self.active_notes.clear()

            for zone in self.zones:
                zone.mpe_channel.clear_all_notes()

    def get_mpe_info(self) -> dict[str, Any]:
        """Get comprehensive MPE system information."""
        with self.lock:
            return {
                "enabled": self.mpe_enabled,
                "global_pitch_bend_range": self.global_pitch_bend_range,
                "zones": [zone.get_zone_info() for zone in self.zones],
                "active_notes_count": len(self.active_notes),
                "active_notes": [note.get_mpe_info() for note in self.active_notes.values()],
            }

    def get_zone_info(self, zone_id: int) -> dict[str, Any] | None:
        """Get information for a specific zone."""
        with self.lock:
            if 1 <= zone_id <= len(self.zones):
                return self.zones[zone_id - 1].get_zone_info()
            return None

    def get_channel_info(self, channel: int) -> dict[str, Any] | None:
        """Get MPE information for a specific channel."""
        with self.lock:
            zone = self.get_zone_for_channel(channel)
            if zone:
                return zone.mpe_channel.get_channel_info()
            return None

    def __str__(self) -> str:
        """String representation."""
        info = self.get_mpe_info()
        status = "Enabled" if info["enabled"] else "Disabled"
        return f"MPEManager({status}, zones={len(info['zones'])}, active_notes={info['active_notes_count']})"

    def __repr__(self) -> str:
        return self.__str__()
