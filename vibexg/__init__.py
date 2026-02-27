"""
Vibexg - Vibe XG Real-Time MIDI Workstation

A professional real-time MIDI workstation emulator with complete implementation of:
- Full MIDI message routing to synthesizer
- Multiple MIDI input interfaces (physical ports, virtual ports, network, file)
- Real-time audio output via sounddevice or file rendering
- Interactive TUI control surface with real-time parameter control
- Full XG synthesizer workstation emulation
- Multi-part setup with 16 MIDI channels
- Style engine for auto-accompaniment
- Recording and playback capabilities
- Preset and registration memory management
- MIDI Learn for CC mapping

Author: Roger
License: MIT
"""
from __future__ import annotations

__version__ = '1.0.0'
__author__ = 'Roger'

__all__ = [
    # Version
    '__version__',
    '__author__',

    # Core
    'XGWorkstation',

    # Types
    'WorkstationState',
    'PresetData',
    'MIDIInputConfig',
    'AudioOutputConfig',
    'InputInterfaceType',
    'AudioOutputType',
    'DEFAULT_SAMPLE_RATE',
    'DEFAULT_BUFFER_SIZE',
    'DEFAULT_BLOCK_SIZE',
    'MIDI_CHANNELS',
    'AUDIO_FORMATS',

    # Managers
    'PresetManager',
    'MIDILearnManager',
    'StyleEngineIntegration',

    # MIDI Inputs
    'MIDIInputInterface',
    'MidoPortInput',
    'VirtualPortInput',
    'NetworkMIDIInput',
    'KeyboardInput',
    'FileMIDIInput',
    'StdinMIDIInput',

    # Audio Outputs
    'AudioOutputEngine',
    'SoundDeviceOutput',
    'FileAudioOutput',

    # TUI
    'TUIControlSurface',

    # Demo
    'DemoMode',

    # CLI
    'parse_arguments',
    'parse_input_spec',
    'parse_output_spec',
    'list_midi_ports',
    'main',

    # Utils
    'midimessage_to_bytes',
    'bytes_to_midimessage',

    # Backends
    'NetworkMIDIHandler',
]

# Import version
from . import types

# Import types
from .types import (
    WorkstationState,
    PresetData,
    MIDIInputConfig,
    AudioOutputConfig,
    InputInterfaceType,
    AudioOutputType,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_BUFFER_SIZE,
    DEFAULT_BLOCK_SIZE,
    MIDI_CHANNELS,
    AUDIO_FORMATS,
)

# Import core
from .workstation import XGWorkstation

# Import managers
from .managers import (
    PresetManager,
    MIDILearnManager,
    StyleEngineIntegration,
)

# Import MIDI inputs
from .midi_inputs import (
    MIDIInputInterface,
    MidoPortInput,
    VirtualPortInput,
    NetworkMIDIInput,
    KeyboardInput,
    FileMIDIInput,
    StdinMIDIInput,
)

# Import audio outputs
from .audio_outputs import (
    AudioOutputEngine,
    SoundDeviceOutput,
    FileAudioOutput,
)

# Import TUI
from .tui import TUIControlSurface

# Import Demo
from .demo import DemoMode

# Import CLI
from .cli import (
    parse_arguments,
    parse_input_spec,
    parse_output_spec,
    list_midi_ports,
    main,
)

# Import utils
from .utils import (
    midimessage_to_bytes,
    bytes_to_midimessage,
)

# Import backends
from .backends import NetworkMIDIHandler
