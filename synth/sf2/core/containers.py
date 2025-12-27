"""
SF2 Container Classes

Container classes for SF2 SoundFont instruments and presets.
Includes zone management and spatial query optimization.
"""

from typing import Dict, List, Any, Optional, Tuple
import time
from .types import RangeRectangle, ZoneCacheEntry, RangeTreeNode, SF2InstrumentZone, SF2PresetZone
from .zones import SF2InstrumentZone as SF2InstrumentZoneImpl, SF2PresetZone as SF2PresetZoneImpl


class RangeTree:
    """
    2D Range Tree for efficient range queries over note/velocity rectangles.

    Optimizes cache hit rate by finding cached entries that cover
    requested note/velocity combinations through arbitrary overlaps.
    """

    def __init__(self):
        self.root: Optional[RangeTreeNode] = None
        self.entries: Dict[str, ZoneCacheEntry] = {}

    def insert(self, range_key: str, rect: RangeRectangle, zones: List[SF2InstrumentZone]):
        """Insert a new range into the tree."""
        new_entry = ZoneCacheEntry(
            zones=zones.copy(),
            coverage=rect,
            access_count=1,
            created_time=time.time()
        )

        self.entries[range_key] = new_entry
        self._insert_helper(range_key, rect)
        self._maintain_tree_invariants()

    def _insert_helper(self, range_key: str, rect: RangeRectangle):
        """Helper to insert into the tree structure."""
        self.root = self._insert_iterator(self.root, range_key, rect)

    def _insert_iterator(self, node: Optional[RangeTreeNode], range_key: str,
                        rect: RangeRectangle) -> RangeTreeNode:
        """Iterative insertion into the range tree."""
        if node is None:
            return RangeTreeNode(rect, range_key)

        # Simple binary tree insertion by note range center
        center_note = (rect.note_min + rect.note_max) // 2
        node_center = (node.rect.note_min + node.rect.note_max) // 2

        if center_note <= node_center:
            node.left = self._insert_iterator(node.left, range_key, rect)
        else:
            node.right = self._insert_iterator(node.right, range_key, rect)

        return node

    def query(self, note: int, velocity: int) -> List[str]:
        """Query for all ranges that contain the given note/velocity point."""
        results = []
        self._query_helper(self.root, note, velocity, results)
        return results

    def _query_helper(self, node: Optional[RangeTreeNode], note: int, velocity: int, results: List[str]):
        """Recursive query helper."""
        if node is None:
            return

        # Check if this node's rectangle contains the query point
        if (node.rect.note_min <= note <= node.rect.note_max and
            node.rect.vel_min <= velocity <= node.rect.vel_max):
            results.append(node.data)

        # Search both subtrees (range tree guarantees we need to check both)
        self._query_helper(node.left, note, velocity, results)
        self._query_helper(node.right, note, velocity, results)

    def _maintain_tree_invariants(self):
        """Ensure tree remains balanced and efficient."""
        # For Phase 2, we'll keep this simple - can be optimized with balancing if needed
        pass

    def find_overlapping_ranges(self, note: int, velocity: int) -> List[str]:
        """Find ranges that overlap with or contain the query point."""
        return self.query(note, velocity)


class SF2Instrument:
    """
    SF2 Instrument

    Contains an instrument definition with name, zones, and global parameters.
    """

    def __init__(self, name: str = ""):
        self.name: str = name
        self.zones: List[SF2InstrumentZone] = []
        self.global_zone: Optional[SF2InstrumentZone] = None

    def add_zone(self, zone: SF2InstrumentZone):
        """Add a zone to this instrument."""
        if zone.is_global:
            self.global_zone = zone
        else:
            self.zones.append(zone)

    def get_zones_for_note_velocity(self, note: int, velocity: int) -> List[SF2InstrumentZone]:
        """Get all zones that match the given note and velocity."""
        matching_zones = []

        # Check regular zones
        for zone in self.zones:
            if zone.contains_note_velocity(note, velocity):
                matching_zones.append(zone)

        return matching_zones

    def to_dict(self) -> Dict[str, Any]:
        """Convert instrument to dictionary for serialization."""
        return {
            'name': self.name,
            'zones': [zone.to_dict() for zone in self.zones],
            'global_zone': self.global_zone.to_dict() if self.global_zone else None
        }


class SF2Preset:
    """
    SF2 Preset

    Contains a preset definition with name, bank/program numbers, zones, and global parameters.
    """

    def __init__(self, name: str = "", bank: int = 0, preset: int = 0):
        self.name: str = name
        self.bank: int = bank  # MIDI bank number (0-16383)
        self.preset: int = preset  # MIDI program number (0-127)
        self.zones: List[SF2PresetZone] = []
        self.global_zone: Optional[SF2PresetZone] = None

    def add_zone(self, zone: SF2PresetZone):
        """Add a zone to this preset."""
        if zone.is_global:
            self.global_zone = zone
        else:
            self.zones.append(zone)

    def get_zones_for_note_velocity(self, note: int, velocity: int) -> List[SF2PresetZone]:
        """Get all zones that match the given note and velocity."""
        matching_zones = []

        # Check regular zones
        for zone in self.zones:
            if zone.contains_note_velocity(note, velocity):
                matching_zones.append(zone)

        return matching_zones

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary for serialization."""
        return {
            'name': self.name,
            'bank': self.bank,
            'preset': self.preset,
            'zones': [zone.to_dict() for zone in self.zones],
            'global_zone': self.global_zone.to_dict() if self.global_zone else None
        }
