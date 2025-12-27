"""
SF2 Data Types and Structures

Core data structures and type definitions for SF2 SoundFont processing.
Contains NamedTuple classes and basic data structures used throughout the SF2 engine.
"""

from typing import NamedTuple, Tuple, Dict, List, Any, Optional
import time


class SF2Generator(NamedTuple):
    """SF2 Generator parameter with type and amount."""
    type: int  # Generator type (0-60)
    amount: int  # Signed 16-bit value


class SF2Modulator(NamedTuple):
    """SF2 Modulator with source/destination and parameters."""
    src_operator: int
    dest_operator: int
    mod_amount: int
    amt_src_operator: int
    mod_trans_operator: int


class SF2SampleHeader(NamedTuple):
    """SF2 Sample header with metadata and loop points."""
    name: str
    start: int  # Start offset in sample data (24-bit words)
    end: int  # End offset in sample data (24-bit words)
    start_loop: int  # Loop start point
    end_loop: int  # Loop end point
    sample_rate: int
    original_pitch: int  # MIDI note number
    pitch_correction: int  # Pitch correction in cents (-50 to +50)
    sample_link: int  # For stereo samples
    sample_type: int  # Loop types and other flags


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
