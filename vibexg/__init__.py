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

__version__ = "1.0.0"
__author__ = "Roger"

__all__ = [
    "AUDIO_FORMATS",
    "DEFAULT_BLOCK_SIZE",
    "DEFAULT_BUFFER_SIZE",
    "DEFAULT_SAMPLE_RATE",
    "MIDI_CHANNELS",
    "AudioOutputConfig",
    "AudioOutputEngine",
    "AudioOutputType",
    "DemoMode",
    "FileAudioOutput",
    "FileMIDIInput",
    "InputInterfaceType",
    "KeyboardInput",
    "MIDIInputConfig",
    "MIDIInputInterface",
    "MIDILearnManager",
    "MidoPortInput",
    "NetworkMIDIHandler",
    "NetworkMIDIInput",
    "PresetData",
    "PresetManager",
    "SoundDeviceOutput",
    "StdinMIDIInput",
    "StyleEngineIntegration",
    "TUIControlSurface",
    "VirtualPortInput",
    "WorkstationState",
    "XGWorkstation",
    "__author__",
    "__version__",
    "bytes_to_midimessage",
    "list_midi_ports",
    "main",
    "midimessage_to_bytes",
    "parse_arguments",
    "parse_input_spec",
    "parse_output_spec",
]

_import_map = {
    "XGWorkstation": ".workstation",
    "WorkstationState": ".types",
    "PresetData": ".types",
    "MIDIInputConfig": ".types",
    "AudioOutputConfig": ".types",
    "InputInterfaceType": ".types",
    "AudioOutputType": ".types",
    "DEFAULT_SAMPLE_RATE": ".types",
    "DEFAULT_BUFFER_SIZE": ".types",
    "DEFAULT_BLOCK_SIZE": ".types",
    "MIDI_CHANNELS": ".types",
    "AUDIO_FORMATS": ".types",
    "PresetManager": ".managers",
    "MIDILearnManager": ".managers",
    "StyleEngineIntegration": ".managers",
    "MIDIInputInterface": ".midi_inputs",
    "MidoPortInput": ".midi_inputs",
    "VirtualPortInput": ".midi_inputs",
    "NetworkMIDIInput": ".midi_inputs",
    "KeyboardInput": ".midi_inputs",
    "FileMIDIInput": ".midi_inputs",
    "StdinMIDIInput": ".midi_inputs",
    "AudioOutputEngine": ".audio_outputs",
    "SoundDeviceOutput": ".audio_outputs",
    "FileAudioOutput": ".audio_outputs",
    "TUIControlSurface": ".tui",
    "DemoMode": ".demo",
    "parse_arguments": ".cli",
    "parse_input_spec": ".cli",
    "parse_output_spec": ".cli",
    "list_midi_ports": ".cli",
    "main": ".cli",
    "midimessage_to_bytes": ".utils",
    "bytes_to_midimessage": ".utils",
    "NetworkMIDIHandler": ".backends",
}


def __getattr__(name: str):
    if name in _import_map:
        module = __import__(_import_map[name], globals(), locals(), [name], 1)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
