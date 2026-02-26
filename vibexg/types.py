"""
Vibexg Types - Data classes, enums, and constants

This module defines all data structures used throughout the vibexg package.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import time


# ============================================================================
# Constants
# ============================================================================

DEFAULT_SAMPLE_RATE: int = 44100
DEFAULT_BUFFER_SIZE: int = 512
DEFAULT_BLOCK_SIZE: int = 1024
MIDI_CHANNELS: int = 16
AUDIO_FORMATS: List[str] = ['wav', 'flac', 'ogg', 'mp3', 'aac', 'm4a']


# ============================================================================
# Enums
# ============================================================================

class InputInterfaceType(Enum):
    """Supported MIDI input interface types."""
    MIDO_PORT = "mido_port"
    VIRTUAL_PORT = "virtual_port"
    NETWORK_MIDI = "network_midi"
    MIDI_FILE = "midi_file"
    KEYBOARD = "keyboard"
    STDIN = "stdin"


class AudioOutputType(Enum):
    """Supported audio output types."""
    SOUNDDEVICE = "sounddevice"
    FILE = "file"
    NONE = "none"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MIDIInputConfig:
    """Configuration for a MIDI input interface."""
    interface_type: InputInterfaceType
    name: str = ""
    port_name: str = ""
    enabled: bool = True
    channel_filter: Optional[List[int]] = None
    velocity_offset: int = 0
    transpose: int = 0
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioOutputConfig:
    """Configuration for audio output."""
    output_type: AudioOutputType
    device_name: str = ""
    file_path: str = ""
    file_format: str = "wav"
    sample_rate: int = DEFAULT_SAMPLE_RATE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    channels: int = 2
    enabled: bool = True


@dataclass
class PresetData:
    """Preset configuration data."""
    name: str = "Init"
    programs: Dict[int, int] = field(default_factory=dict)  # channel -> program
    volumes: Dict[int, int] = field(default_factory=dict)   # channel -> volume
    pans: Dict[int, int] = field(default_factory=dict)      # channel -> pan
    reverb_sends: Dict[int, int] = field(default_factory=dict)
    chorus_sends: Dict[int, int] = field(default_factory=dict)
    master_volume: float = 0.8
    tempo: float = 120.0
    effects_config: Dict[str, Any] = field(default_factory=dict)
    midi_learn_mappings: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: __import__('time').time())
    modified_at: float = field(default_factory=lambda: __import__('time').time())


@dataclass
class WorkstationState:
    """Current state of the workstation."""
    running: bool = False
    recording: bool = False
    playing: bool = False
    metronome: bool = False
    tempo: float = 120.0
    master_volume: float = 0.8
    current_preset: str = "Init"
    active_channels: int = 0
    voices_active: int = 0
    cpu_usage: float = 0.0
    midi_activity: Dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(16)})
    recorded_events: List[Dict[str, Any]] = field(default_factory=list)
    loaded_styles: Dict[int, str] = field(default_factory=dict)  # channel -> style name
