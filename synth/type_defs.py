"""
XG Synthesizer - Type Aliases and Type Definitions (Python 3.11+)

This module provides centralized type aliases for the entire XG Synthesizer project.
Using Python 3.11+ type system features for better type safety and code clarity.

Example:
    from synth.types import MIDIChannel, MIDINote, MIDIVelocity

    def note_on(channel: MIDIChannel, note: MIDINote, velocity: MIDIVelocity) -> None:
        ...
"""

from __future__ import annotations

from enum import IntEnum
from typing import Annotated, Literal, NewType, Protocol, TypeAlias, TypedDict

# =============================================================================
# MIDI Value Types (Annotated with ranges)
# =============================================================================

# MIDI Channels (0-15)
MIDIChannel: TypeAlias = Annotated[int, 0, 15]

# MIDI Notes (0-127, typically 21-108 for 88-key piano)
MIDINote: TypeAlias = Annotated[int, 0, 127]

# MIDI Velocity (0-127)
MIDIVelocity: TypeAlias = Annotated[int, 0, 127]

# MIDI Controllers (0-127)
MIDIController: TypeAlias = Annotated[int, 0, 127]

# MIDI Control Value (0-127)
MIDIControlValue: TypeAlias = Annotated[int, 0, 127]

# MIDI Program Number (0-127)
MIDIProgram: TypeAlias = Annotated[int, 0, 127]

# MIDI Pitch Bend (0-16383, 14-bit, 8192 = center)
MIDIPitchBend: TypeAlias = Annotated[int, 0, 16383]

# MIDI Channel Pressure (0-127)
MIDIChannelPressure: TypeAlias = Annotated[int, 0, 127]

# MIDI Polyphonic Pressure (0-127)
MIDIPolyPressure: TypeAlias = Annotated[int, 0, 127]

# MIDI Bank Select MSB (0-127)
MIDIBankMSB: TypeAlias = Annotated[int, 0, 127]

# MIDI Bank Select LSB (0-127)
MIDIBankLSB: TypeAlias = Annotated[int, 0, 127]


# =============================================================================
# Audio Value Types (Annotated with ranges)
# =============================================================================

# Sample Rate (44100, 48000, 88200, 96000, 192000 Hz)
SampleRate: TypeAlias = Literal[44100, 48000, 88200, 96000, 192000]

# Buffer Size (64-8192 samples, power of 2)
BufferSize: TypeAlias = Annotated[int, 64, 8192]

# Audio Gain/Volume (0.0-1.0)
AudioGain: TypeAlias = Annotated[float, 0.0, 1.0]

# Audio Pan (-1.0 to 1.0, left to right)
AudioPan: TypeAlias = Annotated[float, -1.0, 1.0]

# Audio Frequency (20Hz-20kHz, human hearing range)
AudioFrequency: TypeAlias = Annotated[float, 20.0, 20000.0]

# Filter Frequency (20Hz-20kHz)
FilterFrequency: TypeAlias = Annotated[float, 20.0, 20000.0]

# Filter Resonance/Q (0.0-10.0)
FilterQ: TypeAlias = Annotated[float, 0.0, 10.0]

# Effect Send Level (0.0-1.0)
EffectSend: TypeAlias = Annotated[float, 0.0, 1.0]

# Effect Return Level (0.0-1.0)
EffectReturn: TypeAlias = Annotated[float, 0.0, 1.0]


# =============================================================================
# Time Value Types
# =============================================================================

# Timestamp in seconds (0.0 to infinity)
Timestamp: TypeAlias = Annotated[float, 0.0, float("inf")]

# Duration in seconds (0.0 to infinity)
Duration: TypeAlias = Annotated[float, 0.0, float("inf")]

# Tempo in BPM (20-300 BPM)
TempoBPM: TypeAlias = Annotated[float, 20.0, 300.0]

# Tempo in microseconds per quarter note (200000-3000000)
TempoUS: TypeAlias = Annotated[int, 200000, 3000000]

# Time Signature numerator (1-32)
TimeSigNumerator: TypeAlias = Annotated[int, 1, 32]

# Time Signature denominator (1, 2, 4, 8, 16, 32)
TimeSigDenominator: TypeAlias = Literal[1, 2, 4, 8, 16, 32]

# Key Signature (-7 to 7, flats to sharps)
KeySignature: TypeAlias = Annotated[int, -7, 7]


# =============================================================================
# XG-Specific Types
# =============================================================================

# XG Part Number (0-31 for 32-part multi-timbral)
XGPart: TypeAlias = Annotated[int, 0, 31]

# XG Reverb Type (0-12 for 13 reverb types)
XGReverbType: TypeAlias = Annotated[int, 0, 12]

# XG Chorus Type (0-17 for 18 chorus types)
XGChorusType: TypeAlias = Annotated[int, 0, 17]

# XG Variation Effect Type (0-45 for 46 variation types)
XGVariationType: TypeAlias = Annotated[int, 0, 45]

# XG Insertion Effect Type (0-16 for 17 insertion types)
XGInsertionType: TypeAlias = Annotated[int, 0, 16]

# XG Drum Kit Number (0-127)
XGDrumKit: TypeAlias = Annotated[int, 0, 127]

# XG Scale Tuning Note (0-11 for 12 semitones)
XGScaleNote: TypeAlias = Annotated[int, 0, 11]

# XG Scale Tuning Cents (-64 to +63 cents)
XGScaleCents: TypeAlias = Annotated[int, -64, 63]


# =============================================================================
# Complex Type Aliases
# =============================================================================

# Parameter Map: parameter name -> list of (timestamp, value) tuples
ParameterMap: TypeAlias = dict[str, list[tuple[Timestamp, float | int]]]

# Voice Allocation: (channel, note, velocity)
VoiceAllocation: TypeAlias = tuple[MIDIChannel, MIDINote, MIDIVelocity]

# Effect Chain: list of (effect_type, parameters) tuples
EffectChain: TypeAlias = list[tuple[str, dict[str, float | int]]]

# Preset Data: preset name -> value mapping
PresetData: TypeAlias = dict[str, float | int | str | list[float | int]]

# MIDI Message Data: message type -> data dict
MIDIMessageData: TypeAlias = dict[str, int | float | list[int]]

# Audio Buffer: numpy array of shape (samples, channels)
# Note: Can't use numpy types directly, so use object
AudioBuffer: TypeAlias = object  # type: ignore

# Sample Data: dictionary with audio sample information
SampleData: TypeAlias = dict[str, float | int | str | AudioBuffer]


# =============================================================================
# Protocol Definitions (Structural Subtyping)
# =============================================================================


class MIDIMessageProtocol(Protocol):
    """Protocol for MIDI message-like objects."""

    type: str
    channel: MIDIChannel | None
    data: MIDIMessageData
    timestamp: Timestamp

    def is_note_on(self) -> bool: ...
    def is_note_off(self) -> bool: ...
    def is_control_change(self) -> bool: ...


class SynthesisEngineProtocol(Protocol):
    """Protocol for synthesis engine-like objects."""

    name: str
    sample_rate: SampleRate

    def generate_samples(
        self, note: MIDINote, velocity: MIDIVelocity, modulation: dict[str, float], num_samples: int
    ) -> AudioBuffer: ...


class EffectProtocol(Protocol):
    """Protocol for effect-like objects."""

    name: str
    effect_type: str

    def process(self, audio: AudioBuffer) -> AudioBuffer: ...


# =============================================================================
# TypedDict Definitions
# =============================================================================


class EngineInfo(TypedDict, total=False):
    """Information about a synthesis engine."""

    name: str
    type: str
    polyphony: int
    sample_rate: SampleRate
    features: list[str]


class VoiceInfo(TypedDict, total=False):
    """Information about an active voice."""

    channel: MIDIChannel
    note: MIDINote
    velocity: MIDIVelocity
    engine: str
    start_time: Timestamp
    duration: Duration


class EffectInfo(TypedDict, total=False):
    """Information about an effect."""

    name: str
    type: str
    enabled: bool
    parameters: dict[str, float | int]


class PresetInfo(TypedDict, total=False):
    """Information about a preset."""

    name: str
    programs: dict[MIDIChannel, MIDIProgram]
    volumes: dict[MIDIChannel, AudioGain]
    pans: dict[MIDIChannel, AudioPan]
    created_at: Timestamp
    modified_at: Timestamp


# =============================================================================
# NewType Definitions (for stricter type checking)
# =============================================================================

# Unique identifiers
VoiceID = NewType("VoiceID", int)
PresetID = NewType("PresetID", str)
EffectID = NewType("EffectID", str)
EngineID = NewType("EngineID", str)

# File paths
FilePath = NewType("FilePath", str)
SoundFontPath = NewType("SoundFontPath", str)
SFZPath = NewType("SFZPath", str)

# =============================================================================
# Literal Types
# =============================================================================

# MIDI Message Types
MIDIMessageType: TypeAlias = Literal[
    "note_on",
    "note_off",
    "control_change",
    "program_change",
    "channel_pressure",
    "poly_pressure",
    "pitch_bend",
    "sysex",
    "time_code",
    "song_position",
    "song_select",
    "tune_request",
    "clock",
    "start",
    "continue",
    "stop",
    "active_sensing",
    "system_reset",
]

# Synthesis Engine Types
EngineType: TypeAlias = Literal[
    "sf2",
    "sfz",
    "fm",
    "an",
    "fdsp",
    "wavetable",
    "additive",
    "granular",
    "spectral",
    "physical",
]

# Effect Types
EffectType: TypeAlias = Literal[
    "reverb",
    "chorus",
    "delay",
    "eq",
    "compressor",
    "limiter",
    "distortion",
    "overdrive",
    "phaser",
    "flanger",
    "wah",
    "filter",
]

# =============================================================================
# Union Types
# =============================================================================

# Any numeric MIDI value
MIDINumericValue: TypeAlias = int | float

# Any MIDI parameter value
MIDIParameterValue: TypeAlias = int | float | None

# Any audio parameter value
AudioParameterValue: TypeAlias = float | int

# Any parameter value (generic)
ParameterValue: TypeAlias = float | int | str | None

# =============================================================================
# Enumerations
# =============================================================================


class ProcessingPriority(IntEnum):
    """Processing priority levels for audio threads."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    REALTIME = 3


class ThreadState(IntEnum):
    """Thread state enumeration."""

    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3


class AudioFormat(IntEnum):
    """Audio format enumeration."""

    INT16 = 0
    INT24 = 1
    INT32 = 2
    FLOAT32 = 3
    FLOAT64 = 4


# =============================================================================
# Helper Functions
# =============================================================================


def validate_midi_value(value: int, min_val: int = 0, max_val: int = 127) -> int:
    """Validate and clamp MIDI value to valid range."""
    return max(min_val, min(max_val, value))


def validate_audio_value(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Validate and clamp audio value to valid range."""
    return max(min_val, min(max_val, value))


def validate_tempo_bpm(bpm: float) -> TempoBPM:
    """Validate tempo BPM."""
    return validate_audio_value(bpm, 20.0, 300.0)  # type: ignore


def validate_sample_rate(rate: int) -> SampleRate:
    """Validate sample rate."""
    valid_rates = {44100, 48000, 88200, 96000, 192000}
    if rate not in valid_rates:
        raise ValueError(f"Invalid sample rate: {rate}. Must be one of {valid_rates}")
    return rate  # type: ignore
