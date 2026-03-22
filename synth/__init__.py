"""
XG Synthesizer Package

Python implementation of the Yamaha XG (eXtended General MIDI) synthesizer specification.
Provides modular synthesis engine architecture with MIDI processing, effects, and voice management.

Package Structure:
- core: Core synthesizer infrastructure (Synthesizer, Config, BufferPool, Constants)
- engine: Synthesis engine implementations (SF2, FM, AN, FDSP, XG, etc.)
- effects: Audio effects processing (XG effects, VCM effects, spatial processing)
- voice: Polyphony management and voice allocation
- xg: XG specification implementation (system, effects, controllers)
- midi: MIDI message parsing and processing
- audio: Audio I/O and sample management
- sampling: Sample loading and manipulation
- modulation: Parameter modulation and routing
- sf2: SoundFont 2.0 file format support
- sfz: SFZ sample format support
- s90_s70: S90/S70 hardware compatibility layer
"""

from __future__ import annotations

from .core.buffer_pool import XGBufferPool as BufferPool
from .core.config import SynthConfig
from .core.constants import SynthConstants

# Main synthesizer class
from .core.synthesizer import Synthesizer

# Effects processing
from .effects.effects_coordinator import XGEffectsCoordinator as EffectsCoordinator

# Synthesis engines
from .engine import (
    ModernXGSynthesizer,
    SF2Engine,
    SynthesisEngine,
    SynthesisEngineRegistry,
    get_global_coefficient_manager,
)
from .engine.an_engine import ANEngine

# FDSP and AN engines (S90/S70)
from .engine.fdsp_engine import FDSPEngine

# Parameter routing
from .engine.parameter_router import ParameterRouter

# MIDI processing - Unified API
from .midi import FileParser, MessageBuffer, MessageType, MIDIMessage, MIDIStatus, RealtimeParser

# S90/S70 compatibility
from .s90_s70 import (
    S90S70ControlSurfaceMapping,
    S90S70HardwareSpecs,
    S90S70PerformanceFeatures,
    S90S70PresetCompatibility,
)

# Sample management
from .sampling.sample_manager import SampleManager

# Type aliases (Python 3.11+)
from .type_defs import (
    AudioBuffer,
    AudioFormat,
    AudioFrequency,
    AudioGain,
    AudioPan,
    BufferSize,
    Duration,
    EffectChain,
    EffectID,
    EffectInfo,
    EffectProtocol,
    EffectReturn,
    EffectSend,
    EffectType,
    EngineID,
    # TypedDicts
    EngineInfo,
    EngineType,
    FilePath,
    FilterFrequency,
    FilterQ,
    MIDIBankLSB,
    MIDIBankMSB,
    # MIDI types
    MIDIChannel,
    MIDIChannelPressure,
    MIDIController,
    MIDIControlValue,
    MIDIMessageData,
    # Protocols
    MIDIMessageProtocol,
    # Literals
    MIDIMessageType,
    MIDINote,
    MIDIPitchBend,
    MIDIPolyPressure,
    MIDIProgram,
    MIDIVelocity,
    # Complex types
    ParameterMap,
    PresetData,
    PresetID,
    PresetInfo,
    # Enums
    ProcessingPriority,
    SampleData,
    # Audio types
    SampleRate,
    SFZPath,
    SoundFontPath,
    SynthesisEngineProtocol,
    TempoBPM,
    TempoUS,
    ThreadState,
    # Time types
    Timestamp,
    VoiceAllocation,
    # NewTypes
    VoiceID,
    VoiceInfo,
    XGChorusType,
    XGDrumKit,
    XGInsertionType,
    # XG types
    XGPart,
    XGReverbType,
    XGVariationType,
    validate_audio_value,
    # Validators
    validate_midi_value,
    validate_sample_rate,
    validate_tempo_bpm,
)

# Core synthesizer components
from .version import __version__

# Voice management
from .voice.voice_manager import VoiceManager

# XG system
from .xg.xg_system import XGSystem

__all__ = [
    # Version
    "__version__",
    # Core components
    "SynthConfig",
    "SynthConstants",
    "BufferPool",
    "Synthesizer",
    # Synthesis engines
    "SynthesisEngine",
    "SynthesisEngineRegistry",
    "SF2Engine",
    "ModernXGSynthesizer",
    "FDSPEngine",
    "ANEngine",
    "get_global_coefficient_manager",
    # Sample management
    "SampleManager",
    # S90/S70 compatibility
    "S90S70HardwareSpecs",
    "S90S70PresetCompatibility",
    "S90S70ControlSurfaceMapping",
    "S90S70PerformanceFeatures",
    # Effects and processing
    "EffectsCoordinator",
    # MIDI processing
    "MIDIMessage",
    "RealtimeParser",
    "FileParser",
    "MessageBuffer",
    "MessageType",
    "MIDIStatus",
    # Voice management
    "VoiceManager",
    # XG system
    "XGSystem",
    # Parameter routing
    "ParameterRouter",
    # Type aliases (Python 3.11+)
    # MIDI types
    "MIDIChannel",
    "MIDINote",
    "MIDIVelocity",
    "MIDIController",
    "MIDIControlValue",
    "MIDIProgram",
    "MIDIPitchBend",
    "MIDIChannelPressure",
    "MIDIPolyPressure",
    "MIDIBankMSB",
    "MIDIBankLSB",
    # Audio types
    "SampleRate",
    "BufferSize",
    "AudioGain",
    "AudioPan",
    "AudioFrequency",
    "FilterFrequency",
    "FilterQ",
    "EffectSend",
    "EffectReturn",
    # Time types
    "Timestamp",
    "Duration",
    "TempoBPM",
    "TempoUS",
    # XG types
    "XGPart",
    "XGReverbType",
    "XGChorusType",
    "XGVariationType",
    "XGInsertionType",
    "XGDrumKit",
    # Complex types
    "ParameterMap",
    "VoiceAllocation",
    "EffectChain",
    "PresetData",
    "MIDIMessageData",
    "AudioBuffer",
    "SampleData",
    # Protocols
    "MIDIMessageProtocol",
    "SynthesisEngineProtocol",
    "EffectProtocol",
    # TypedDicts
    "EngineInfo",
    "VoiceInfo",
    "EffectInfo",
    "PresetInfo",
    # NewTypes
    "VoiceID",
    "PresetID",
    "EffectID",
    "EngineID",
    "FilePath",
    "SoundFontPath",
    "SFZPath",
    # Literals
    "MIDIMessageType",
    "EngineType",
    "EffectType",
    # Enums
    "ProcessingPriority",
    "ThreadState",
    "AudioFormat",
    # Validators
    "validate_midi_value",
    "validate_audio_value",
    "validate_tempo_bpm",
    "validate_sample_rate",
]
