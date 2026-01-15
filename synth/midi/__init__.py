"""
XG Synthesizer MIDI Module

Unified MIDI processing for both real-time and file-based applications.
Provides clean, consistent interfaces for all MIDI operations.
"""

# Core message system
from .message import MIDIMessage

# Processing modules
from .realtime import RealtimeParser
from .file import FileParser
from .buffer import MessageBuffer

# Types and constants
from .types import (
    MessageType, MIDIStatus, XGConstants,
    is_channel_message, is_system_message, is_sysex_message,
    validate_message_type, get_status_byte, get_message_type_from_status
)

__all__ = [
    # Core messages
    "MIDIMessage",

    # Processing
    "RealtimeParser",
    "FileParser",
    "MessageBuffer",

    # Types and constants
    "MessageType",
    "MIDIStatus",
    "XGConstants",
    "is_channel_message",
    "is_system_message",
    "is_sysex_message",
    "validate_message_type",
    "get_status_byte",
    "get_message_type_from_status"
]
