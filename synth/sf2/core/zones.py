"""
SF2 Zone Classes

Zone processing classes for SF2 SoundFont instruments and presets.
Handles key/velocity ranges, generator inheritance, and modulator processing.

Note: This module provides legacy compatibility. Use classes from ..types.dataclasses for new code.
"""

from typing import Dict, List, Any
from ..types.dataclasses import SF2InstrumentZone as SF2InstrumentZoneMaster, SF2PresetZone as SF2PresetZoneMaster
from .types import SF2Modulator

# Provide aliases for backward compatibility
SF2InstrumentZone = SF2InstrumentZoneMaster
SF2PresetZone = SF2PresetZoneMaster
