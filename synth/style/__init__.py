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
- ScaleDetector: Musical scale/key detection
- GrooveQuantizer: Rhythmic feel processing
- MIDILearn: MIDI controller learning

Usage:
    from synth.style import StyleLoader, AutoAccompaniment, ScaleDetector

    # Load a style
    loader = StyleLoader()
    style = loader.load_style_file("pop_ballad.yaml")

    # Create accompaniment engine
    engine = AutoAccompaniment(style, synthesizer)
    engine.start()

    # Get scale detection
    scale_detector = ScaleDetector()
    scale_detector.add_note(60)
    current_scale = scale_detector.get_current_scale()
"""

from __future__ import annotations

from .auto_accompaniment import AccompanimentMode, AutoAccompaniment
from .chord_detector import ChordDetector, ChordRoot, ChordType, DetectedChord
from .dynamics import DynamicsParameter, StyleDynamics
from .groove import (
    GrooveQuantizer,
    GrooveTemplate,
    GrooveType,
    get_default_groove_quantizer,
)
from .integrations import (
    StyleEffectsIntegration,
    StyleIntegrations,
    StyleModulationIntegration,
    StyleMPEIntegration,
    StyleSequencerIntegration,
    StyleVoiceIntegration,
)
from .midi_learn import LearnTargetType, MIDILearn, MIDILearnMapping
from .registration import Registration, RegistrationBank, RegistrationMemory
from .scale import (
    SCALE_PATTERNS,
    DetectedScale,
    ScaleDetectionConfig,
    ScaleDetector,
    ScalePattern,
    ScaleType,
    get_scale_detector,
)
from .style import Style, StyleCategory, StyleSection, StyleSectionType
from .style_loader import StyleLoader, StyleValidationError
from .style_ots import OneTouchSettings, OTSPreset
from .style_player import SectionTransition, StylePlayer
from .style_track import StyleTrack, TrackType

__version__ = "1.2.0"

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
    # MIDI Learn
    "MIDILearn",
    "MIDILearnMapping",
    "LearnTargetType",
    # Scale Detection
    "ScaleDetector",
    "ScaleType",
    "ScalePattern",
    "DetectedScale",
    "ScaleDetectionConfig",
    "get_scale_detector",
    "SCALE_PATTERNS",
    # Integrations (NEW)
    "StyleEffectsIntegration",
    "StyleVoiceIntegration",
    "StyleModulationIntegration",
    "StyleSequencerIntegration",
    "StyleMPEIntegration",
    "StyleIntegrations",
]
