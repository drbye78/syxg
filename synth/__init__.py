"""
XG Synthesizer Package

Python implementation of the Yamaha XG (eXtended General MIDI) synthesizer specification.
Provides modular synthesis engine architecture with MIDI processing, effects, and voice management.

Package Structure:
- primitives: Core DSP building blocks (BufferPool, Config, Envelope, Filter, etc.)
- synthesizers: Top-level orchestrators (Synthesizer, ModernXGSynthesizer)
- engines: Synthesis engine implementations (SF2, FM, AN, FDSP, etc.)
- processing: Audio/MIDI processing pipeline (channel, voice, partial, effects, modulation)
- protocols: XG and GS specification implementations
- hardware: Hardware emulation layers (Jupiter-X, S90/S70)
- io: File/network I/O (MIDI, audio, SF2, SFZ)
- sampling: Sample loading and manipulation
- xgml: XG Markup Language configuration
- style: Auto-accompaniment style engine
- sequencer: Pattern sequencing
"""

from __future__ import annotations

from .primitives.buffer_pool import XGBufferPool as BufferPool
from .primitives.config import SynthConfig
from .primitives.constants import SynthConstants

# Main synthesizer classes
from .synthesizers.realtime import Synthesizer
from .synthesizers.rendering import ModernXGSynthesizer

# Effects processing
from .processing.effects.effects_coordinator import XGEffectsCoordinator as EffectsCoordinator

# Synthesis engines
from .engines import (
    SF2Engine,
    SynthesisEngine,
    SynthesisEngineRegistry,
    get_global_coefficient_manager,
)
from .engines.physical_modeling import ANEngine

# FDSP engine (S90/S70)
from .engines.fdsp import FDSPEngine

# Parameter routing
from .engines.parameter_router import ParameterRouter

# MIDI processing - Unified API
from .io.midi import FileParser, MessageBuffer, MessageType, MIDIMessage, MIDIStatus, RealtimeParser

# S90/S70 compatibility
from .hardware.s90_s70 import (
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
from .processing.voice.voice_manager import VoiceManager

# XG system
from .protocols.xg.xg_system import XGSystem

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
