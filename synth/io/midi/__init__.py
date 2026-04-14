"""
XG Synthesizer MIDI Module

Unified MIDI processing for both real-time and file-based applications.
Provides clean, consistent interfaces for all MIDI operations.
"""

from __future__ import annotations

from .buffer import MessageBuffer
from .file import FileParser

# Core message system
from .message import MIDIMessage, midimessage_to_bytes

# Processing modules
from .realtime import RealtimeParser

# Port I/O (optional - requires rtmidi)
try:
    from .ports import (
        RTMIDI_AVAILABLE,
        MIDIInputPort,
        MIDIOutputPort,
        get_input_names,
        get_output_names,
        open_input,
        open_output,
    )
except ImportError:
    # Ports module not available (rtmidi not installed)
    get_input_names = None
    get_output_names = None
    open_input = None
    open_output = None
    MIDIInputPort = None
    MIDIOutputPort = None
    RTMIDI_AVAILABLE = False

# File writing
from .file_writer import MIDIFileWriter

# Types and constants
from .types import (
    MessageType,
    MIDIStatus,
    XGConstants,
    get_message_type_from_status,
    get_status_byte,
    is_channel_message,
    is_sysex_message,
    is_system_message,
    validate_message_type,
)

# Utilities
from .utils import (
    bpm2tempo,
    message_type_to_status,
    seconds_to_ticks,
    status_to_message_type,
    tempo2bpm,
    ticks_to_seconds,
)

__all__ = [
    # Core messages
    "MIDIMessage",
    "midimessage_to_bytes",
    # Processing
    "RealtimeParser",
    "FileParser",
    "MessageBuffer",
    # Port I/O
    "get_input_names",
    "get_output_names",
    "open_input",
    "open_output",
    "MIDIInputPort",
    "MIDIOutputPort",
    "RTMIDI_AVAILABLE",
    # File writing
    "MIDIFileWriter",
    # Utilities
    "tempo2bpm",
    "bpm2tempo",
    "ticks_to_seconds",
    "seconds_to_ticks",
    "message_type_to_status",
    "status_to_message_type",
    # Types and constants
    "MessageType",
    "MIDIStatus",
    "XGConstants",
    "is_channel_message",
    "is_system_message",
    "is_sysex_message",
    "validate_message_type",
    "get_status_byte",
    "get_message_type_from_status",
]
