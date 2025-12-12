#!/usr/bin/env python3
"""
XG RECEIVE CHANNEL MANAGER

Production-quality XG MIDI channel mapping implementation.
Manages receive channel assignments for all 16 XG parts with thread-safe operations.

XG Specification Compliance:
- Each part (0-15) can receive from any MIDI channel (0-15)
- Default: Part N receives from MIDI channel N
- Supports dynamic reassignment via SYSEX and NRPN
- Thread-safe for real-time performance

Copyright (c) 2025
"""

from typing import Dict, List, Optional, Tuple, Any
import threading
import numpy as np


class XGReceiveChannelManager:
    """
    XG RECEIVE CHANNEL MANAGER

    Manages XG receive channel mapping with O(1) lookup performance.
    Supports full XG specification compliance for MIDI channel routing.

    Key Features:
    - 16-element receive channel mapping (parts 0-15)
    - O(1) MIDI-to-part lookup using reverse mapping tables
    - Thread-safe operations for real-time use
    - XG SYSEX and NRPN parameter support
    - Default 1:1 mapping (XG standard)

    XG Mapping Rules:
    - receive_channels[part_id] = midi_channel (0-15)
    - Multiple parts can receive from same MIDI channel
    - Part can be disabled (receive_channel = None)
    - All parts can receive from one channel (broadcast mode)
    """

    # XG Receive Channel Constants
    RECEIVE_CHANNEL_OFF = 254    # Part disabled
    RECEIVE_CHANNEL_ALL = 255    # Part receives from all channels

    def __init__(self, num_parts: int = 16):
        """
        Initialize XG Receive Channel Manager.

        Args:
            num_parts: Number of XG parts (default 16)
        """
        self.num_parts = num_parts
        self.lock = threading.RLock()

        # Core mapping: part_id -> receive_channel
        # XG default: part N receives from MIDI channel N
        self.receive_channels = list(range(num_parts))  # [0, 1, 2, ..., 15]

        # Reverse lookup tables for O(1) performance
        self._build_reverse_mappings()

        print(f"🎹 XG RECEIVE CHANNEL MANAGER: {num_parts} parts initialized")
        print("   Default 1:1 MIDI channel mapping active")

    def _build_reverse_mappings(self):
        """Build optimized reverse lookup tables for O(1) MIDI-to-part mapping."""
        with self.lock:
            # midi_channel -> list of part_ids that receive from it
            self.midi_to_parts = {i: [] for i in range(16)}

            # Build reverse mapping
            for part_id in range(self.num_parts):
                receive_channel = self.receive_channels[part_id]

                if receive_channel == self.RECEIVE_CHANNEL_OFF:
                    # Part is disabled - no mapping
                    continue
                elif receive_channel == self.RECEIVE_CHANNEL_ALL:
                    # Part receives from all channels
                    for midi_ch in range(16):
                        self.midi_to_parts[midi_ch].append(part_id)
                elif 0 <= receive_channel <= 15:
                    # Part receives from specific channel
                    self.midi_to_parts[receive_channel].append(part_id)

    def set_receive_channel(self, part_id: int, midi_channel: int) -> bool:
        """
        Set receive channel for a specific XG part.

        Args:
            part_id: XG part number (0-15)
            midi_channel: MIDI channel to receive from (0-15, 254=OFF, 255=ALL)

        Returns:
            True if mapping was set, False otherwise
        """
        with self.lock:
            if not (0 <= part_id < self.num_parts):
                return False

            if midi_channel not in (list(range(16)) + [self.RECEIVE_CHANNEL_OFF, self.RECEIVE_CHANNEL_ALL]):
                return False

            # Update mapping
            old_channel = self.receive_channels[part_id]
            self.receive_channels[part_id] = midi_channel

            # Rebuild reverse mappings for consistency
            self._build_reverse_mappings()

            print(f"🎹 XG RECEIVE: Part {part_id} now receives from "
                  f"{'MIDI CH ' + str(midi_channel) if midi_channel < 16 else 'ALL' if midi_channel == 255 else 'OFF'}")
            return True

    def get_receive_channel(self, part_id: int) -> Optional[int]:
        """
        Get receive channel for a specific XG part.

        Args:
            part_id: XG part number (0-15)

        Returns:
            MIDI channel number (0-15, 254=OFF, 255=ALL) or None if invalid
        """
        with self.lock:
            if 0 <= part_id < self.num_parts:
                return self.receive_channels[part_id]
        return None

    def get_parts_for_midi_channel(self, midi_channel: int) -> List[int]:
        """
        Get all XG parts that receive from a specific MIDI channel.

        Args:
            midi_channel: MIDI channel number (0-15)

        Returns:
            List of part IDs that receive from this channel
        """
        with self.lock:
            if 0 <= midi_channel <= 15:
                return self.midi_to_parts[midi_channel].copy()
        return []

    def route_midi_message(self, midi_channel: int, message_type: str,
                          message_data: Dict) -> List[Tuple[int, Dict]]:
        """
        Route a MIDI message to appropriate XG parts based on receive channel mapping.

        Args:
            midi_channel: Source MIDI channel (0-15)
            message_type: Type of MIDI message
            message_data: Message data dictionary

        Returns:
            List of (part_id, routed_message_data) tuples
        """
        with self.lock:
            target_parts = self.get_parts_for_midi_channel(midi_channel)

            if not target_parts:
                return []

            # Route message to all target parts
            routed_messages = []
            for part_id in target_parts:
                # Create routed message with updated channel info
                routed_data = message_data.copy()
                routed_data['original_channel'] = midi_channel
                routed_data['target_part'] = part_id

                routed_messages.append((part_id, routed_data))

            return routed_messages

    def reset_to_xg_defaults(self):
        """Reset all receive channels to XG default mapping (1:1)."""
        with self.lock:
            self.receive_channels = list(range(self.num_parts))
            self._build_reverse_mappings()
            print("🎹 XG RECEIVE CHANNELS: Reset to XG defaults (1:1 mapping)")

    def handle_sysex_receive_channel(self, part_id: int, midi_channel: int) -> bool:
        """
        Handle XG SYSEX receive channel assignment.

        XG SYSEX Format: F0 43 [device] 4C 08 [part] [channel] F7

        Args:
            part_id: XG part number (0-15)
            midi_channel: MIDI channel to assign (0-15)

        Returns:
            True if assignment was successful
        """
        return self.set_receive_channel(part_id, midi_channel)

    def handle_nrpn_receive_channel(self, part_id: int, midi_channel: int) -> bool:
        """
        Handle XG NRPN receive channel assignment.

        XG NRPN: MSB 126 (7E), LSB 0, Data = midi_channel

        Args:
            part_id: XG part number (0-15)
            midi_channel: MIDI channel to assign (0-15, 254=OFF, 255=ALL)

        Returns:
            True if assignment was successful
        """
        return self.set_receive_channel(part_id, midi_channel)

    def get_channel_mapping_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all receive channel mappings."""
        with self.lock:
            status = {
                'total_parts': self.num_parts,
                'mappings': {},
                'reverse_mappings': {},
                'conflicts': []
            }

            # Part-to-channel mappings
            for part_id in range(self.num_parts):
                channel = self.receive_channels[part_id]
                status['mappings'][f'part_{part_id}'] = {
                    'receive_channel': channel,
                    'description': self._channel_description(channel)
                }

            # Channel-to-parts reverse mappings
            for midi_ch in range(16):
                parts = self.midi_to_parts[midi_ch]
                if parts:
                    status['reverse_mappings'][f'midi_{midi_ch}'] = parts.copy()

            # Detect conflicts (multiple parts receiving from same channel)
            for midi_ch in range(16):
                parts = self.midi_to_parts[midi_ch]
                if len(parts) > 1:
                    status['conflicts'].append({
                        'midi_channel': midi_ch,
                        'parts': parts.copy()
                    })

            return status

    def _channel_description(self, channel: int) -> str:
        """Get human-readable description of channel assignment."""
        if channel == self.RECEIVE_CHANNEL_OFF:
            return "OFF (disabled)"
        elif channel == self.RECEIVE_CHANNEL_ALL:
            return "ALL (broadcast)"
        elif 0 <= channel <= 15:
            return f"MIDI CH {channel}"
        else:
            return f"INVALID ({channel})"

    def export_mapping(self) -> Dict[str, List[int]]:
        """Export receive channel mapping for serialization."""
        with self.lock:
            return {
                'receive_channels': self.receive_channels.copy(),
                'version': '1.0'
            }

    def import_mapping(self, mapping_data: Dict[str, List[int]]) -> bool:
        """Import receive channel mapping from serialized data."""
        try:
            with self.lock:
                if 'receive_channels' in mapping_data:
                    channels = mapping_data['receive_channels']
                    if len(channels) == self.num_parts:
                        self.receive_channels = channels.copy()
                        self._build_reverse_mappings()
                        print("🎹 XG RECEIVE CHANNELS: Mapping imported successfully")
                        return True
        except Exception as e:
            print(f"❌ XG RECEIVE CHANNELS: Import failed - {e}")

        return False

    def __str__(self) -> str:
        """String representation of receive channel mapping."""
        with self.lock:
            lines = ["XG Receive Channel Mapping:"]
            for part_id in range(self.num_parts):
                channel = self.receive_channels[part_id]
                desc = self._channel_description(channel)
                lines.append(f"  Part {part_id:2d}: {desc}")
            return "\n".join(lines)

    def __repr__(self) -> str:
        return f"XGReceiveChannelManager(parts={self.num_parts})"
