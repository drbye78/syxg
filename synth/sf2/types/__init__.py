"""
SF2 Data Types and Structures

This module contains all the data classes and type definitions
for SoundFont 2.0 file format structures.
"""

from .dataclasses import (
    SF2Modulator,
    SF2InstrumentZone,
    SF2PresetZone,
    SF2SampleHeader,
    SF2Preset,
    SF2Instrument
)

__all__ = [
    'SF2Modulator',
    'SF2InstrumentZone',
    'SF2PresetZone',
    'SF2SampleHeader',
    'SF2Preset',
    'SF2Instrument'
]
