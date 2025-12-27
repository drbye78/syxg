"""
SF2 Core Module

Core components for SF2 SoundFont processing.
Modular architecture with separate concerns for maintainability.
"""

# Re-export all classes for backward compatibility
from .types import *
from .zones import *
from .containers import *
from .modulation import *
from .generator import *
from .voice import *
from .memory import *
from .manager import SF2Manager
from .parser import *

# Backward compatibility: SoundFontManager is now SF2Manager
SoundFontManager = SF2Manager

__all__ = [
    # Types
    'SF2Generator',
    'SF2Modulator',
    'SF2SampleHeader',
    'RangeRectangle',
    'ZoneCacheEntry',
    'RangeTreeNode',

    # Zones
    'SF2InstrumentZone',
    'SF2PresetZone',

    # Containers
    'RangeTree',
    'SF2Instrument',
    'SF2Preset',

    # Modulation
    'SF2ModulationMatrix',

    # Synthesis
    'SF2PartialGenerator',

    # Voice Management
    'SF2VoiceManager',
    'SF2Voice',

    # Memory Management
    'MemoryPool',

    # High-level Management
    'SF2Manager',
    'SoundFontManager',  # Backward compatibility alias

    # File Parsing
    'SF2SoundFont',
    'SF2ParseError',
]
