"""
SF2 Data Types and Structures

Core data structures and type definitions for SF2 SoundFont processing.
Contains NamedTuple classes and basic data structures used throughout the SF2 engine.

Note: Main SF2 data classes are now in ..types.dataclasses. This module provides
legacy compatibility and additional utility types.
"""

from typing import NamedTuple, List, Any

# Import master SF2 classes
from ..types.dataclasses import SF2Modulator as SF2ModulatorMaster, SF2SampleHeader as SF2SampleHeaderMaster

# Provide aliases for backward compatibility
SF2Modulator = SF2ModulatorMaster
SF2SampleHeader = SF2SampleHeaderMaster


class SF2Generator(NamedTuple):
    """SF2 Generator parameter with type and amount."""
    type: int  # Generator type (0-60)
    amount: int  # Signed 16-bit value


class RangeRectangle(NamedTuple):
    """2D range rectangle for note/velocity range queries."""
    note_min: int
    note_max: int
    vel_min: int
    vel_max: int


class ZoneCacheEntry(NamedTuple):
    """Cache entry with zones and metadata."""
    zones: List[Any]  # Forward reference to avoid circular import
    coverage: RangeRectangle
    access_count: int
    created_time: float


class RangeTreeNode:
    """2D Range Tree node for efficient spatial queries."""
    def __init__(self, rect: RangeRectangle, data: Any, left=None, right=None):
        self.rect = rect
        self.data = data
        self.left = left
        self.right = right


# Forward declarations for type hints
SF2InstrumentZone = Any  # Will be imported from zones module
SF2PresetZone = Any      # Will be imported from zones module
