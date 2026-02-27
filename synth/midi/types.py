"""
MIDI Type Definitions and Constants

Centralized definitions for MIDI message types, status bytes, and utility functions.
Provides a single source of truth for MIDI specifications and validation.
"""
from __future__ import annotations

from enum import Enum, StrEnum


class MessageType(StrEnum):
    """Enumeration of all MIDI message types."""

    # Channel Messages
    NOTE_OFF = "note_off"
    NOTE_ON = "note_on"
    POLY_PRESSURE = "poly_pressure"
    CONTROL_CHANGE = "control_change"
    PROGRAM_CHANGE = "program_change"
    CHANNEL_PRESSURE = "channel_pressure"
    PITCH_BEND = "pitch_bend"

    # System Messages
    TIMING_CLOCK = "timing_clock"
    START = "start"
    CONTINUE = "continue"
    STOP = "stop"
    ACTIVE_SENSING = "active_sensing"
    SYSTEM_RESET = "system_reset"
    TUNE_REQUEST = "tune_request"
    TIME_CODE = "time_code"
    SONG_POSITION = "song_position"
    SONG_SELECT = "song_select"

    # System Exclusive
    SYSEX = "sysex"
    XG_PARAMETER_CHANGE = "xg_parameter_change"
    XG_BULK_DUMP = "xg_bulk_dump"
    XG_DATA_SET = "xg_data_set"
    UNIVERSAL_SYSEX = "universal_sysex"
    UNIVERSAL_REALTIME_SYSEX = "universal_realtime_sysex"

    # Meta Events (for file parsing)
    META = "meta"
    TEMPO = "tempo"
    TIME_SIGNATURE = "time_signature"
    KEY_SIGNATURE = "key_signature"
    END_OF_TRACK = "end_of_track"

    # MIDI 2.0 Messages
    EXTENDED_CHANNEL_MESSAGE = "extended_channel_message"
    COMPLEX_CHANNEL_MESSAGE = "complex_channel_message"
    FULL_128BIT_MESSAGE = "full_128bit_message"
    DATA_MESSAGE = "data_message"
    MIXED_DATA_SET = "mixed_data_set"
    FLEX_DATA = "flex_data"
    STREAM_MESSAGE = "stream_message"
    SYSTEM_MESSAGE = "system_message"
    UNKNOWN_UMP = "unknown_ump"
    
    # MIDI 2.0 Channel Voice Messages
    MIDI_2_NOTE_ON = "midi2_note_on"
    MIDI_2_NOTE_OFF = "midi2_note_off"
    MIDI_2_POLY_KEY_PRESSURE = "midi2_poly_key_pressure"
    MIDI_2_CONTROL_CHANGE = "midi2_control_change"
    MIDI_2_PROGRAM_CHANGE = "midi2_program_change"
    MIDI_2_CHANNEL_PRESSURE = "midi2_channel_pressure"
    MIDI_2_PITCH_BEND = "midi2_pitch_bend"
    MIDI_2_PER_NOTE_CONTROLLER = "midi2_per_note_controller"
    MIDI_2_RELATIVE_PER_NOTE_CONTROLLER = "midi2_relative_per_note_controller"
    MIDI_2_PER_NOTE_MANAGEMENT = "midi2_per_note_management"
    
    # MIDI 2.0 Registered and Assignable Parameter Numbers
    MIDI_2_RPN = "midi2_rpn"
    MIDI_2_NRPN = "midi2_nrpn"
    MIDI_2_ASSIGNABLE_CONTROLLER = "midi2_assignable_controller"
    
    # MIDI 2.0 Utilities
    MIDI_2_NOOP = "midi2_noop"
    MIDI_2_JITTER_REDUCTION_TIMESTAMP = "midi2_jitter_reduction_timestamp"
    
    # MIDI 2.0 Property Exchange Messages
    MIDI_2_PROPERTY_GET = "midi2_property_get"
    MIDI_2_PROPERTY_SET = "midi2_property_set"
    MIDI_2_PROPERTY_NOTIFY = "midi2_property_notify"
    MIDI_2_PROPERTY_RESPONSE = "midi2_property_response"
    
    # MIDI 2.0 Mixed Data Set Messages
    MIDI_2_MIXED_DATA_SET = "midi2_mixed_data_set"
    MIDI_2_DATA_INCREMENT = "midi2_data_increment"
    MIDI_2_DATA_DECREMENT = "midi2_data_decrement"
    
    # MIDI 2.0 128-bit Messages
    MIDI_2_128_BIT_MESSAGE = "midi2_128_bit_message"
    
    # MIDI 2.0 Flex Data Messages
    MIDI_2_FLEX_DATA_SIXTEEN = "midi2_flex_data_sixteen"
    MIDI_2_FLEX_DATA_TWENTY_FOUR = "midi2_flex_data_twenty_four"
    MIDI_2_FLEX_DATA_THIRTY_TWO = "midi2_flex_data_thirty_two"


# Message type collections for validation and categorization
CHANNEL_MESSAGE_TYPES: set[str] = {
    MessageType.NOTE_OFF,
    MessageType.NOTE_ON,
    MessageType.POLY_PRESSURE,
    MessageType.CONTROL_CHANGE,
    MessageType.PROGRAM_CHANGE,
    MessageType.CHANNEL_PRESSURE,
    MessageType.PITCH_BEND,
    MessageType.MIDI_2_NOTE_ON,
    MessageType.MIDI_2_NOTE_OFF,
    MessageType.MIDI_2_POLY_KEY_PRESSURE,
    MessageType.MIDI_2_CONTROL_CHANGE,
    MessageType.MIDI_2_PROGRAM_CHANGE,
    MessageType.MIDI_2_CHANNEL_PRESSURE,
    MessageType.MIDI_2_PITCH_BEND,
    MessageType.MIDI_2_PER_NOTE_CONTROLLER,
    MessageType.MIDI_2_RELATIVE_PER_NOTE_CONTROLLER,
    MessageType.MIDI_2_PER_NOTE_MANAGEMENT,
}

# System Real-time Messages (for synchronization)
SYSTEM_REALTIME_MESSAGE_TYPES: set[str] = {
    MessageType.TIMING_CLOCK,
    MessageType.START,
    MessageType.CONTINUE,
    MessageType.STOP,
    MessageType.ACTIVE_SENSING,
    MessageType.SYSTEM_RESET,
}

# System Common Messages
SYSTEM_COMMON_MESSAGE_TYPES: set[str] = {
    MessageType.TIME_CODE,
    MessageType.SONG_POSITION,
    MessageType.SONG_SELECT,
    MessageType.TUNE_REQUEST,
}

SYSTEM_MESSAGE_TYPES: set[str] = {
    MessageType.TIMING_CLOCK,
    MessageType.START,
    MessageType.CONTINUE,
    MessageType.STOP,
    MessageType.ACTIVE_SENSING,
    MessageType.SYSTEM_RESET,
    MessageType.TUNE_REQUEST,
    MessageType.TIME_CODE,
    MessageType.SONG_POSITION,
    MessageType.SONG_SELECT,
}

SYSEX_MESSAGE_TYPES: set[str] = {
    MessageType.SYSEX,
    MessageType.XG_PARAMETER_CHANGE,
    MessageType.XG_BULK_DUMP,
    MessageType.XG_DATA_SET,
    MessageType.UNIVERSAL_SYSEX,
    MessageType.UNIVERSAL_REALTIME_SYSEX,
}

MIDI_2_0_MESSAGE_TYPES: set[str] = {
    MessageType.EXTENDED_CHANNEL_MESSAGE,
    MessageType.COMPLEX_CHANNEL_MESSAGE,
    MessageType.FULL_128BIT_MESSAGE,
    MessageType.DATA_MESSAGE,
    MessageType.MIXED_DATA_SET,
    MessageType.FLEX_DATA,
    MessageType.STREAM_MESSAGE,
    MessageType.MIDI_2_NOTE_ON,
    MessageType.MIDI_2_NOTE_OFF,
    MessageType.MIDI_2_POLY_KEY_PRESSURE,
    MessageType.MIDI_2_CONTROL_CHANGE,
    MessageType.MIDI_2_PROGRAM_CHANGE,
    MessageType.MIDI_2_CHANNEL_PRESSURE,
    MessageType.MIDI_2_PITCH_BEND,
    MessageType.MIDI_2_PER_NOTE_CONTROLLER,
    MessageType.MIDI_2_RELATIVE_PER_NOTE_CONTROLLER,
    MessageType.MIDI_2_PER_NOTE_MANAGEMENT,
    MessageType.MIDI_2_RPN,
    MessageType.MIDI_2_NRPN,
    MessageType.MIDI_2_ASSIGNABLE_CONTROLLER,
    MessageType.MIDI_2_NOOP,
    MessageType.MIDI_2_JITTER_REDUCTION_TIMESTAMP,
    MessageType.MIDI_2_PROPERTY_GET,
    MessageType.MIDI_2_PROPERTY_SET,
    MessageType.MIDI_2_PROPERTY_NOTIFY,
    MessageType.MIDI_2_PROPERTY_RESPONSE,
    MessageType.MIDI_2_MIXED_DATA_SET,
    MessageType.MIDI_2_DATA_INCREMENT,
    MessageType.MIDI_2_DATA_DECREMENT,
    MessageType.MIDI_2_128_BIT_MESSAGE,
    MessageType.MIDI_2_FLEX_DATA_SIXTEEN,
    MessageType.MIDI_2_FLEX_DATA_TWENTY_FOUR,
    MessageType.MIDI_2_FLEX_DATA_THIRTY_TWO,
}

ALL_MESSAGE_TYPES: set[str] = (
    CHANNEL_MESSAGE_TYPES |
    SYSTEM_MESSAGE_TYPES |
    SYSEX_MESSAGE_TYPES |
    MIDI_2_0_MESSAGE_TYPES |
    {MessageType.META, MessageType.UNKNOWN_UMP}
)


# MIDI Status Byte Constants
class MIDIStatus:
    """MIDI status byte constants."""

    # Channel Messages (OR with channel 0-15)
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0

    # System Messages
    SYSTEM_EXCLUSIVE = 0xF0
    TIME_CODE = 0xF1
    SONG_POSITION = 0xF2
    SONG_SELECT = 0xF3
    TUNE_REQUEST = 0xF6
    END_OF_EXCLUSIVE = 0xF7
    TIMING_CLOCK = 0xF8
    START = 0xFA
    CONTINUE = 0xFB
    STOP = 0xFC
    ACTIVE_SENSING = 0xFE
    SYSTEM_RESET = 0xFF

    # Meta Events (for file parsing)
    META_EVENT = 0xFF

    # System Common Messages
    SYSTEM_COMMON_MASK = 0xF0
    SYSTEM_REALTIME_MASK = 0xF8
    
    # MIDI 2.0 Universal MIDI Packet (UMP) Status Types
    UMP_STATUS_TYPE_OTHER = 0x0
    UMP_STATUS_TYPE_MIDI_1_CHANNEL = 0x1
    UMP_STATUS_TYPE_MIDI_2_CHANNEL = 0x2
    UMP_STATUS_TYPE_SYSEX = 0x3
    UMP_STATUS_TYPE_UTILITY = 0x4
    UMP_STATUS_TYPE_MISC = 0x5
    UMP_STATUS_TYPE_STREAM = 0xF


# XG-Specific Constants
class XGConstants:
    """Yamaha XG-specific constants."""

    MANUFACTURER_ID = [0x43, 0x10]  # Yamaha XG
    MODEL_ID = 0x4C                 # XG model

    # XG Command Types
    BULK_DUMP = 0x00
    PARAMETER_CHANGE = 0x10
    DATA_SET = 0x12

    # XG Receive Channel Command
    RECEIVE_CHANNEL_COMMAND = 0x08


# Utility Functions
def is_channel_message(msg_type: str) -> bool:
    """Check if message type is a MIDI channel message."""
    return msg_type in CHANNEL_MESSAGE_TYPES


def is_system_message(msg_type: str) -> bool:
    """Check if message type is a MIDI system message."""
    return msg_type in SYSTEM_MESSAGE_TYPES


def is_sysex_message(msg_type: str) -> bool:
    """Check if message type is a System Exclusive message."""
    return msg_type in SYSEX_MESSAGE_TYPES


def is_midi2_message(msg_type: str) -> bool:
    """Check if message type is a MIDI 2.0 message."""
    return msg_type in MIDI_2_0_MESSAGE_TYPES


def validate_message_type(msg_type: str) -> bool:
    """Validate that a message type string is recognized."""
    return msg_type in ALL_MESSAGE_TYPES


def get_status_byte(message_type: str, channel: int = 0) -> int:
    """
    Get the MIDI status byte for a message type and channel.

    Args:
        message_type: Message type string
        channel: MIDI channel (0-15)

    Returns:
        MIDI status byte
    """
    if message_type == MessageType.NOTE_OFF:
        return MIDIStatus.NOTE_OFF | channel
    elif message_type == MessageType.NOTE_ON:
        return MIDIStatus.NOTE_ON | channel
    elif message_type == MessageType.POLY_PRESSURE:
        return MIDIStatus.POLY_PRESSURE | channel
    elif message_type == MessageType.CONTROL_CHANGE:
        return MIDIStatus.CONTROL_CHANGE | channel
    elif message_type == MessageType.PROGRAM_CHANGE:
        return MIDIStatus.PROGRAM_CHANGE | channel
    elif message_type == MessageType.CHANNEL_PRESSURE:
        return MIDIStatus.CHANNEL_PRESSURE | channel
    elif message_type == MessageType.PITCH_BEND:
        return MIDIStatus.PITCH_BEND | channel
    elif message_type == MessageType.SYSEX:
        return MIDIStatus.SYSTEM_EXCLUSIVE
    elif message_type == MessageType.TIMING_CLOCK:
        return MIDIStatus.TIMING_CLOCK
    elif message_type == MessageType.START:
        return MIDIStatus.START
    elif message_type == MessageType.CONTINUE:
        return MIDIStatus.CONTINUE
    elif message_type == MessageType.STOP:
        return MIDIStatus.STOP
    elif message_type == MessageType.ACTIVE_SENSING:
        return MIDIStatus.ACTIVE_SENSING
    elif message_type == MessageType.SYSTEM_RESET:
        return MIDIStatus.SYSTEM_RESET
    elif message_type == MessageType.TUNE_REQUEST:
        return MIDIStatus.TUNE_REQUEST
    elif message_type == MessageType.TIME_CODE:
        return MIDIStatus.TIME_CODE
    elif message_type == MessageType.SONG_POSITION:
        return MIDIStatus.SONG_POSITION
    elif message_type == MessageType.SONG_SELECT:
        return MIDIStatus.SONG_SELECT
    else:
        return 0x00


def get_message_type_from_status(status_byte: int) -> str:
    """
    Get message type string from MIDI status byte.

    Args:
        status_byte: MIDI status byte

    Returns:
        Message type string
    """
    command = status_byte & 0xF0
    channel = status_byte & 0x0F

    if command == MIDIStatus.NOTE_OFF:
        return MessageType.NOTE_OFF
    elif command == MIDIStatus.NOTE_ON:
        return MessageType.NOTE_ON
    elif command == MIDIStatus.POLY_PRESSURE:
        return MessageType.POLY_PRESSURE
    elif command == MIDIStatus.CONTROL_CHANGE:
        return MessageType.CONTROL_CHANGE
    elif command == MIDIStatus.PROGRAM_CHANGE:
        return MessageType.PROGRAM_CHANGE
    elif command == MIDIStatus.CHANNEL_PRESSURE:
        return MessageType.CHANNEL_PRESSURE
    elif command == MIDIStatus.PITCH_BEND:
        return MessageType.PITCH_BEND
    elif status_byte == MIDIStatus.SYSTEM_EXCLUSIVE:
        return MessageType.SYSEX
    elif status_byte == MIDIStatus.TIMING_CLOCK:
        return MessageType.TIMING_CLOCK
    elif status_byte == MIDIStatus.START:
        return MessageType.START
    elif status_byte == MIDIStatus.CONTINUE:
        return MessageType.CONTINUE
    elif status_byte == MIDIStatus.STOP:
        return MessageType.STOP
    elif status_byte == MIDIStatus.ACTIVE_SENSING:
        return MessageType.ACTIVE_SENSING
    elif status_byte == MIDIStatus.SYSTEM_RESET:
        return MessageType.SYSTEM_RESET
    elif status_byte == MIDIStatus.TUNE_REQUEST:
        return MessageType.TUNE_REQUEST
    elif status_byte == MIDIStatus.TIME_CODE:
        return MessageType.TIME_CODE
    elif status_byte == MIDIStatus.SONG_POSITION:
        return MessageType.SONG_POSITION
    elif status_byte == MIDIStatus.SONG_SELECT:
        return MessageType.SONG_SELECT
    else:
        return MessageType.UNKNOWN_UMP
