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
from .midi_learn import MIDILearn, MIDILearnMapping, LearnTargetType
from .scale import (
    ScaleDetector,
    ScaleType,
    ScalePattern,
    DetectedScale,
    ScaleDetectionConfig,
    get_scale_detector,
    SCALE_PATTERNS,
)
from .integrations import (
    StyleEffectsIntegration,
    StyleVoiceIntegration,
    StyleModulationIntegration,
    StyleSequencerIntegration,
    StyleMPEIntegration,
    StyleIntegrations,
)

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
