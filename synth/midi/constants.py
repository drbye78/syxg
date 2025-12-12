#!/usr/bin/env python3
"""
MIDI Message Type Constants

Centralized definition of MIDI message type identifiers used throughout the synthesizer.
Provides single source of truth for message type names and improves maintainability.

MIDI 1.0 Channel Messages:
- Channel Voice Messages: note_on, note_off, control_change, program_change, etc.
- Channel Mode Messages: Special control_change values

MIDI 2.0 Messages:
- Extended precision channel voice messages
- System messages and sysex

XG-Specific Messages:
- System exclusive messages for Yamaha XG protocol

Copyright (c) 2025
"""

# MIDI 1.0 Channel Voice Message Types
MSG_TYPE_NOTE_OFF = "note_off"
MSG_TYPE_NOTE_ON = "note_on"
MSG_TYPE_POLY_PRESSURE = "poly_pressure"  # Polyphonic Aftertouch
MSG_TYPE_CONTROL_CHANGE = "control_change"
MSG_TYPE_PROGRAM_CHANGE = "program_change"
MSG_TYPE_CHANNEL_PRESSURE = "channel_pressure"  # Channel Aftertouch
MSG_TYPE_PITCH_BEND = "pitch_bend"

# MIDI 1.0 System Messages
MSG_TYPE_SYSEX = "sysex"  # System Exclusive
MSG_TYPE_META = "meta"    # Meta Event (for MIDI files)

# MIDI 2.0 Extended Messages
MSG_TYPE_EXTENDED_CHANNEL_MESSAGE = "extended_channel_message"
MSG_TYPE_COMPLEX_CHANNEL_MESSAGE = "complex_channel_message"
MSG_TYPE_FULL_128BIT_MESSAGE = "full_128bit_message"

# MIDI 2.0 System Messages
MSG_TYPE_DATA_MESSAGE = "data_message"
MSG_TYPE_MIXED_DATA_SET = "mixed_data_set"
MSG_TYPE_FLEX_DATA = "flex_data"
MSG_TYPE_STREAM_MESSAGE = "stream_message"
MSG_TYPE_SYSTEM_MESSAGE = "system_message"

# Special/Unknown Message Types
MSG_TYPE_UNKNOWN_UMP = "unknown_ump"

# MIDI Message Type Lists for Validation/Reference
MIDI_1_0_CHANNEL_MESSAGE_TYPES = [
    MSG_TYPE_NOTE_OFF,
    MSG_TYPE_NOTE_ON,
    MSG_TYPE_POLY_PRESSURE,
    MSG_TYPE_CONTROL_CHANGE,
    MSG_TYPE_PROGRAM_CHANGE,
    MSG_TYPE_CHANNEL_PRESSURE,
    MSG_TYPE_PITCH_BEND,
]

MIDI_SYSTEM_MESSAGE_TYPES = [
    MSG_TYPE_SYSEX,
    MSG_TYPE_META,
    MSG_TYPE_SYSTEM_MESSAGE,
]

MIDI_2_0_MESSAGE_TYPES = [
    MSG_TYPE_EXTENDED_CHANNEL_MESSAGE,
    MSG_TYPE_COMPLEX_CHANNEL_MESSAGE,
    MSG_TYPE_FULL_128BIT_MESSAGE,
    MSG_TYPE_DATA_MESSAGE,
    MSG_TYPE_MIXED_DATA_SET,
    MSG_TYPE_FLEX_DATA,
    MSG_TYPE_STREAM_MESSAGE,
]

ALL_MESSAGE_TYPES = (
    MIDI_1_0_CHANNEL_MESSAGE_TYPES +
    MIDI_SYSTEM_MESSAGE_TYPES +
    MIDI_2_0_MESSAGE_TYPES +
    [MSG_TYPE_UNKNOWN_UMP]
)

# MIDI Status Byte Constants (for reference)
MIDI_STATUS_NOTE_OFF = 0x80
MIDI_STATUS_NOTE_ON = 0x90
MIDI_STATUS_POLY_PRESSURE = 0xA0
MIDI_STATUS_CONTROL_CHANGE = 0xB0
MIDI_STATUS_PROGRAM_CHANGE = 0xC0
MIDI_STATUS_CHANNEL_PRESSURE = 0xD0
MIDI_STATUS_PITCH_BEND = 0xE0
MIDI_STATUS_SYSEX_START = 0xF0
MIDI_STATUS_META_EVENT = 0xFF

# XG-Specific Constants
XG_MANUFACTURER_ID = 0x43  # Yamaha
XG_MODEL_ID = 0x4C         # XG
XG_RECEIVE_CHANNEL_COMMAND = 0x08

def is_channel_message(msg_type: str) -> bool:
    """Check if message type is a MIDI channel message."""
    return msg_type in MIDI_1_0_CHANNEL_MESSAGE_TYPES

def is_system_message(msg_type: str) -> bool:
    """Check if message type is a MIDI system message."""
    return msg_type in MIDI_SYSTEM_MESSAGE_TYPES

def is_midi2_message(msg_type: str) -> bool:
    """Check if message type is a MIDI 2.0 message."""
    return msg_type in MIDI_2_0_MESSAGE_TYPES

def validate_message_type(msg_type: str) -> bool:
    """Validate that a message type string is recognized."""
    return msg_type in ALL_MESSAGE_TYPES

# Message type to status nibble mapping (for channel messages)
MESSAGE_TYPE_TO_STATUS_NIBBLE = {
    MSG_TYPE_NOTE_OFF: 0x8,
    MSG_TYPE_NOTE_ON: 0x9,
    MSG_TYPE_POLY_PRESSURE: 0xA,
    MSG_TYPE_CONTROL_CHANGE: 0xB,
    MSG_TYPE_PROGRAM_CHANGE: 0xC,
    MSG_TYPE_CHANNEL_PRESSURE: 0xD,
    MSG_TYPE_PITCH_BEND: 0xE,
}

def get_status_nibble_for_message_type(msg_type: str) -> int:
    """Get MIDI status nibble for a channel message type."""
    return MESSAGE_TYPE_TO_STATUS_NIBBLE.get(msg_type, 0x0)
