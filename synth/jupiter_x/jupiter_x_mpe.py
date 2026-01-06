"""
Jupiter-X MPE - MIDI Polyphonic Expression Implementation

Provides complete MPE (MIDI Polyphonic Expression) support for Jupiter-X,
enabling per-note control of timbre, pitch bend, pressure, and other
parameters with hardware-accurate behavior and real-time performance.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import threading


class MPEZone(Enum):
    """MPE zone definitions."""
    LOWER = "lower"
    UPPER = "upper"


class MPEChannel:
    """
    MPE Channel - Represents one channel in MPE zone.

    Handles per-note expression data and parameter management.
    """

    def __init__(self, channel_number: int, zone: MPEZone):
        """
        Initialize MPE channel.

        Args:
            channel_number: MIDI channel number
            zone: MPE zone this channel belongs to
        """
        self.channel_number = channel_number
        self.zone = zone

        # Per-note expression data
        self.active_notes: Dict[int, Dict[str, Any]] = {}  # note -> expression data

        # Channel-wide parameters
        self.pitch_bend_range = 48  # semitones (MPE default)
        self.timbre_cc = 74  # Brightness CC
        self.pressure_curve = 'linear'  # 'linear', 'exponential'

        # Zone configuration
        self.zone_master_channel = 1 if zone == MPEZone.LOWER else 16

    def note_on(self, note: int, velocity: int, initial_timbre: float = 0.0):
        """
        Handle note-on with MPE data.

        Args:
            note: MIDI note number
            velocity: Note velocity
            initial_timbre: Initial timbre value
        """
        self.active_notes[note] = {
            'velocity': velocity,
            'timbre': initial_timbre,
            'pressure': 0.0,
            'pitch_bend': 0.0,
            'slide': 0.0,
            'start_time': self._get_current_time(),
            'last_update': self._get_current_time()
        }

    def note_off(self, note: int):
        """
        Handle note-off.

        Args:
            note: MIDI note number
        """
        if note in self.active_notes:
            del self.active_notes[note]

    def update_timbre(self, note: int, value: float):
        """
        Update timbre for specific note.

        Args:
            note: MIDI note number
            value: Timbre value (0-127)
        """
        if note in self.active_notes:
            self.active_notes[note]['timbre'] = value / 127.0
            self.active_notes[note]['last_update'] = self._get_current_time()

    def update_pressure(self, note: int, value: float):
        """
        Update pressure for specific note.

        Args:
            note: MIDI note number
            value: Pressure value (0-127)
        """
        if note in self.active_notes:
            # Apply pressure curve
            if self.pressure_curve == 'linear':
                pressure = value / 127.0
            elif self.pressure_curve == 'exponential':
                pressure = (value / 127.0) ** 2.0
            else:
                pressure = value / 127.0

            self.active_notes[note]['pressure'] = pressure
            self.active_notes[note]['last_update'] = self._get_current_time()

    def update_pitch_bend(self, note: int, value: float):
        """
        Update pitch bend for specific note.

        Args:
            note: MIDI note number
            value: Pitch bend value (-8192 to 8191)
        """
        if note in self.active_notes:
            # Convert to semitones based on pitch bend range
            bend_semitones = (value / 8192.0) * (self.pitch_bend_range / 2.0)
            self.active_notes[note]['pitch_bend'] = bend_semitones
            self.active_notes[note]['last_update'] = self._get_current_time()

    def update_slide(self, note: int, value: float):
        """
        Update slide for specific note.

        Args:
            note: MIDI note number
            value: Slide value (0-127)
        """
        if note in self.active_notes:
            self.active_notes[note]['slide'] = value / 127.0
            self.active_notes[note]['last_update'] = self._get_current_time()

    def get_note_expression(self, note: int) -> Optional[Dict[str, Any]]:
        """
        Get expression data for specific note.

        Args:
            note: MIDI note number

        Returns:
            Expression data or None if note not active
        """
        return self.active_notes.get(note)

    def get_all_active_notes(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all active notes with their expression data.

        Returns:
            Dictionary of active notes
        """
        return self.active_notes.copy()

    def clear_channel(self):
        """Clear all notes from channel."""
        self.active_notes.clear()

    def _get_current_time(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()


class JupiterXMPEManager:
    """
    Jupiter-X MPE Manager - Complete MPE implementation.

    Provides full MPE support with per-note expression control,
    zone management, and hardware-accurate behavior.
    """

    def __init__(self):
        """Initialize Jupiter-X MPE manager."""
        self.enabled = False
        self.zones: Dict[MPEZone, Dict[str, Any]] = {}

        # Initialize zones
        self._initialize_zones()

        # Global MPE settings
        self.global_pitch_bend_range = 2  # Traditional pitch bend range
        self.mpe_profile = 'standard'  # 'standard', 'extended'

        # Threading
        self.lock = threading.RLock()

    def _initialize_zones(self):
        """Initialize MPE zones."""
        # Lower zone (channels 2-9, master channel 1)
        self.zones[MPEZone.LOWER] = {
            'master_channel': 1,
            'member_channels': list(range(2, 10)),  # Channels 2-9
            'pitch_bend_range': 48,  # semitones
            'timbre_cc': 74,  # Brightness
            'enabled': False
        }

        # Upper zone (channels 10-15, master channel 16)
        self.zones[MPEZone.UPPER] = {
            'master_channel': 16,
            'member_channels': list(range(10, 16)),  # Channels 10-15
            'pitch_bend_range': 48,  # semitones
            'timbre_cc': 74,  # Brightness
            'enabled': False
        }

        # Create channel objects
        for zone in self.zones.values():
            zone['channels'] = {}
            for ch_num in zone['member_channels']:
                zone['channels'][ch_num] = MPEChannel(ch_num, MPEZone.LOWER if zone['master_channel'] == 1 else MPEZone.UPPER)

    def enable_mpe(self, enabled: bool = True):
        """
        Enable or disable MPE globally.

        Args:
            enabled: Whether to enable MPE
        """
        with self.lock:
            self.enabled = enabled

            if not enabled:
                # Clear all zones when disabling
                for zone in self.zones.values():
                    zone['enabled'] = False
                    for channel in zone['channels'].values():
                        channel.clear_channel()

    def enable_zone(self, zone: MPEZone, enabled: bool = True, pitch_bend_range: int = 48):
        """
        Enable or disable specific MPE zone.

        Args:
            zone: Zone to enable/disable
            enabled: Whether to enable the zone
            pitch_bend_range: Pitch bend range in semitones
        """
        with self.lock:
            if zone in self.zones:
                self.zones[zone]['enabled'] = enabled
                self.zones[zone]['pitch_bend_range'] = pitch_bend_range

                # Update pitch bend range for all channels in zone
                for channel in self.zones[zone]['channels'].values():
                    channel.pitch_bend_range = pitch_bend_range

                if not enabled:
                    # Clear channels when disabling zone
                    for channel in self.zones[zone]['channels'].values():
                        channel.clear_channel()

    def configure_zone(self, zone: MPEZone, master_channel: int, member_channels: List[int],
                      pitch_bend_range: int = 48, timbre_cc: int = 74):
        """
        Configure MPE zone parameters.

        Args:
            zone: Zone to configure
            master_channel: Master channel for zone
            member_channels: List of member channels
            pitch_bend_range: Pitch bend range in semitones
            timbre_cc: Timbre CC number
        """
        with self.lock:
            if zone in self.zones:
                zone_config = self.zones[zone]
                zone_config['master_channel'] = master_channel
                zone_config['member_channels'] = member_channels.copy()
                zone_config['pitch_bend_range'] = pitch_bend_range
                zone_config['timbre_cc'] = timbre_cc

                # Recreate channels with new configuration
                zone_config['channels'] = {}
                zone_enum = MPEZone.LOWER if master_channel == 1 else MPEZone.UPPER
                for ch_num in member_channels:
                    zone_config['channels'][ch_num] = MPEChannel(ch_num, zone_enum)
                    zone_config['channels'][ch_num].pitch_bend_range = pitch_bend_range
                    zone_config['channels'][ch_num].timbre_cc = timbre_cc

    def process_midi_message(self, message_type: str, channel: int, data1: int, data2: int = 0) -> List[Dict[str, Any]]:
        """
        Process MIDI message for MPE.

        Args:
            message_type: Type of MIDI message ('note_on', 'note_off', 'cc', 'pitch_bend', 'aftertouch')
            channel: MIDI channel
            data1: First data byte
            data2: Second data byte

        Returns:
            List of MPE events to process
        """
        with self.lock:
            if not self.enabled:
                return []

            events = []

            # Find which zone/channel this belongs to
            zone, mpe_channel = self._get_channel_for_message(channel)

            if not zone or not mpe_channel:
                return events

            if message_type == 'note_on':
                mpe_channel.note_on(data1, data2)
                events.append({
                    'type': 'mpe_note_on',
                    'zone': zone.value,
                    'channel': channel,
                    'note': data1,
                    'velocity': data2,
                    'timbre': mpe_channel.get_note_expression(data1)['timbre'] if data1 in mpe_channel.active_notes else 0.0
                })

            elif message_type == 'note_off':
                mpe_channel.note_off(data1)
                events.append({
                    'type': 'mpe_note_off',
                    'zone': zone.value,
                    'channel': channel,
                    'note': data1
                })

            elif message_type == 'cc':
                cc_number = data1
                cc_value = data2

                # Check if this is a per-note CC (MPE)
                if cc_number == mpe_channel.timbre_cc:
                    # This is per-note timbre control
                    # In MPE, CC messages to member channels are per-note
                    # We need to determine which note this applies to (last note played on channel)
                    last_note = self._get_last_note_on_channel(channel)
                    if last_note is not None:
                        mpe_channel.update_timbre(last_note, cc_value)
                        events.append({
                            'type': 'mpe_timbre',
                            'zone': zone.value,
                            'channel': channel,
                            'note': last_note,
                            'timbre': cc_value / 127.0
                        })

            elif message_type == 'pitch_bend':
                # Pitch bend on member channels is per-note
                bend_value = (data2 << 7) | data1  # Combine 14-bit value
                bend_signed = bend_value - 8192  # Convert to signed

                last_note = self._get_last_note_on_channel(channel)
                if last_note is not None:
                    mpe_channel.update_pitch_bend(last_note, bend_signed)
                    events.append({
                        'type': 'mpe_pitch_bend',
                        'zone': zone.value,
                        'channel': channel,
                        'note': last_note,
                        'bend': bend_signed
                    })

            elif message_type == 'aftertouch':
                # Aftertouch (pressure) on member channels is per-note
                last_note = self._get_last_note_on_channel(channel)
                if last_note is not None:
                    mpe_channel.update_pressure(last_note, data1)
                    events.append({
                        'type': 'mpe_pressure',
                        'zone': zone.value,
                        'channel': channel,
                        'note': last_note,
                        'pressure': data1 / 127.0
                    })

            return events

    def _get_channel_for_message(self, channel: int) -> Tuple[Optional[MPEZone], Optional[MPEChannel]]:
        """
        Get MPE zone and channel for MIDI channel.

        Args:
            channel: MIDI channel (1-16)

        Returns:
            Tuple of (zone, mpe_channel) or (None, None)
        """
        for zone_enum, zone_config in self.zones.items():
            if zone_enum in zone_config['channels'] and channel in zone_config['channels']:
                if zone_config['enabled']:
                    return zone_enum, zone_config['channels'][channel]

        return None, None

    def _get_last_note_on_channel(self, channel: int) -> Optional[int]:
        """
        Get the last note played on a channel.

        Args:
            channel: MIDI channel

        Returns:
            Last note number or None
        """
        zone, mpe_channel = self._get_channel_for_message(channel)
        if mpe_channel and mpe_channel.active_notes:
            # Return most recently played note
            notes_by_time = sorted(mpe_channel.active_notes.items(),
                                 key=lambda x: x[1]['start_time'],
                                 reverse=True)
            return notes_by_time[0][0]

        return None

    def get_note_expression(self, channel: int, note: int) -> Optional[Dict[str, Any]]:
        """
        Get expression data for specific note on channel.

        Args:
            channel: MIDI channel
            note: MIDI note number

        Returns:
            Expression data or None
        """
        with self.lock:
            zone, mpe_channel = self._get_channel_for_message(channel)
            if mpe_channel:
                return mpe_channel.get_note_expression(note)
            return None

    def get_channel_expression(self, channel: int) -> Dict[int, Dict[str, Any]]:
        """
        Get all expression data for channel.

        Args:
            channel: MIDI channel

        Returns:
            Dictionary of note expression data
        """
        with self.lock:
            zone, mpe_channel = self._get_channel_for_message(channel)
            if mpe_channel:
                return mpe_channel.get_all_active_notes()
            return {}

    def get_zone_status(self, zone: MPEZone) -> Optional[Dict[str, Any]]:
        """
        Get status of MPE zone.

        Args:
            zone: Zone to query

        Returns:
            Zone status or None if zone doesn't exist
        """
        with self.lock:
            if zone in self.zones:
                zone_config = self.zones[zone].copy()
                # Count active notes across all channels in zone
                total_active_notes = sum(len(ch.get_all_active_notes()) for ch in zone_config['channels'].values())
                zone_config['active_notes'] = total_active_notes
                return zone_config
            return None

    def get_mpe_status(self) -> Dict[str, Any]:
        """
        Get complete MPE status.

        Returns:
            Comprehensive MPE status information
        """
        with self.lock:
            status = {
                'enabled': self.enabled,
                'profile': self.mpe_profile,
                'global_pitch_bend_range': self.global_pitch_bend_range,
                'zones': {}
            }

            for zone_enum, zone_config in self.zones.items():
                status['zones'][zone_enum.value] = self.get_zone_status(zone_enum)

            return status

    def reset_mpe(self):
        """Reset MPE to default state."""
        with self.lock:
            self.enabled = False
            self.mpe_profile = 'standard'
            self.global_pitch_bend_range = 2

            for zone_config in self.zones.values():
                zone_config['enabled'] = False
                for channel in zone_config['channels'].values():
                    channel.clear_channel()

    def set_mpe_profile(self, profile: str):
        """
        Set MPE profile.

        Args:
            profile: Profile name ('standard', 'extended')
        """
        with self.lock:
            if profile in ['standard', 'extended']:
                self.mpe_profile = profile

                if profile == 'extended':
                    # Extended profile uses wider ranges
                    for zone_config in self.zones.values():
                        zone_config['pitch_bend_range'] = 96  # Wider pitch bend
                        for channel in zone_config['channels'].values():
                            channel.pitch_bend_range = 96
                else:
                    # Standard profile
                    for zone_config in self.zones.values():
                        zone_config['pitch_bend_range'] = 48
                        for channel in zone_config['channels'].values():
                            channel.pitch_bend_range = 48

    def export_mpe_configuration(self) -> Dict[str, Any]:
        """
        Export MPE configuration.

        Returns:
            MPE configuration data
        """
        with self.lock:
            config = {
                'enabled': self.enabled,
                'profile': self.mpe_profile,
                'global_pitch_bend_range': self.global_pitch_bend_range,
                'zones': {}
            }

            for zone_enum, zone_config in self.zones.items():
                zone_data = zone_config.copy()
                # Remove channel objects from export
                zone_data.pop('channels', None)
                config['zones'][zone_enum.value] = zone_data

            return config

    def import_mpe_configuration(self, config: Dict[str, Any]):
        """
        Import MPE configuration.

        Args:
            config: MPE configuration data
        """
        with self.lock:
            self.enabled = config.get('enabled', False)
            self.mpe_profile = config.get('profile', 'standard')
            self.global_pitch_bend_range = config.get('global_pitch_bend_range', 2)

            zones_config = config.get('zones', {})
            for zone_name, zone_data in zones_config.items():
                try:
                    zone_enum = MPEZone(zone_name)
                    self.configure_zone(
                        zone_enum,
                        zone_data.get('master_channel', 1 if zone_name == 'lower' else 16),
                        zone_data.get('member_channels', []),
                        zone_data.get('pitch_bend_range', 48),
                        zone_data.get('timbre_cc', 74)
                    )
                    self.enable_zone(zone_enum, zone_data.get('enabled', False))
                except ValueError:
                    continue  # Skip invalid zones
