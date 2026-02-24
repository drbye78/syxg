"""
Style Engine Module - Professional Auto-Accompaniment System

This module provides a complete Yamaha-style auto-accompaniment system
with YAML-based style files, chord detection, and full section management.

Main Components:
- StyleLoader: YAML style file parser
- ChordDetector: Real-time chord recognition
- AutoAccompaniment: Main accompaniment engine
- StylePlayer: Style playback with section transitions
- OneTouchSettings: Quick voice preset system
- RegistrationMemory: Bank/memory recall system

Usage:
    from synth.style import StyleLoader, AutoAccompaniment

    # Load a style
    loader = StyleLoader()
    style = loader.load_style_file("pop_ballad.yaml")

    # Create accompaniment engine
    engine = AutoAccompaniment(style, synthesizer)
    engine.start()
"""

from .style import Style, StyleCategory, StyleSection, StyleSectionType
from .style_track import StyleTrack, TrackType
from .style_ots import OneTouchSettings, OTSPreset
from .chord_detector import ChordDetector, ChordType, ChordRoot, DetectedChord
from .auto_accompaniment import AutoAccompaniment, AccompanimentMode
from .style_player import StylePlayer, SectionTransition
from .registration import RegistrationMemory, RegistrationBank, Registration
from .style_loader import StyleLoader, StyleValidationError
from .dynamics import StyleDynamics, DynamicsParameter
from .groove import (
    GrooveQuantizer,
    GrooveType,
    GrooveTemplate,
    get_default_groove_quantizer,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "Style",
    "StyleCategory",
    "StyleSection",
    "StyleSectionType",
    "StyleLoader",
    "StyleValidationError",
    # Tracks
    "StyleTrack",
    "TrackType",
    # Chord Detection
    "ChordDetector",
    "ChordType",
    "ChordRoot",
    "DetectedChord",
    # Accompaniment
    "AutoAccompaniment",
    "AccompanimentMode",
    # Player
    "StylePlayer",
    "SectionTransition",
    # OTS
    "OneTouchSettings",
    "OTSPreset",
    # Registration
    "RegistrationMemory",
    "RegistrationBank",
    "Registration",
    # Dynamics
    "StyleDynamics",
    "DynamicsParameter",
    # Groove
    "GrooveQuantizer",
    "GrooveType",
    "GrooveTemplate",
    "get_default_groove_quantizer",
]
