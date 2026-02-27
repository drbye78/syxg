"""
Vibexg Utilities - Helper functions for MIDI conversion

This module provides utility functions for MIDI message conversion.
"""
from __future__ import annotations

from synth.midi import MIDIMessage


def midimessage_to_bytes(message: MIDIMessage) -> bytes:
    """
    Convert MIDIMessage to MIDI byte stream.
    
    Args:
        message: MIDIMessage to convert
    
    Returns:
        Raw MIDI bytes as bytes object
    
    Example:
        >>> from synth.midi import MIDIMessage
        >>> msg = MIDIMessage(type='note_on', channel=0, data={'note': 60, 'velocity': 80})
        >>> data = midimessage_to_bytes(msg)
        >>> data.hex()
        '903c50'
    """
    result: bytearray = bytearray()
    channel: int = message.channel or 0
    
    if message.type == 'note_on':
        status = 0x90 | channel
        result.append(status)
        result.append(message.note or 0)
        result.append(message.velocity or 0)
    
    elif message.type == 'note_off':
        status = 0x80 | channel
        result.append(status)
        result.append(message.note or 0)
        result.append(message.velocity or 0)
    
    elif message.type == 'control_change':
        status = 0xB0 | channel
        result.append(status)
        result.append(message.controller or 0)
        result.append(message.value or 0)
    
    elif message.type == 'program_change':
        status = 0xC0 | channel
        result.append(status)
        result.append(message.program or 0)
    
    elif message.type == 'channel_pressure':
        status = 0xD0 | channel
        result.append(status)
        result.append(message.pressure or 0)
    
    elif message.type == 'poly_pressure':
        status = 0xA0 | channel
        result.append(status)
        result.append(message.note or 0)
        result.append(message.pressure or 0)
    
    elif message.type == 'pitch_bend':
        status = 0xE0 | channel
        result.append(status)
        value = message.bend_value if message.bend_value is not None else 8192
        result.append(value & 0x7F)
        result.append((value >> 7) & 0x7F)
    
    elif message.type == 'sysex':
        result.append(0xF0)
        raw_data = message.data.get('raw_data', [])
        for byte in raw_data:
            result.append(byte & 0x7F)
        result.append(0xF7)
    
    return bytes(result)


def bytes_to_midimessage(data: bytes, timestamp: float | None = None) -> list[MIDIMessage]:
    """
    Convert MIDI bytes to MIDIMessage objects.
    
    Args:
        data: Raw MIDI bytes to parse
        timestamp: Optional timestamp to assign to messages (default: None)
    
    Returns:
        List of MIDIMessage objects parsed from the byte stream
    
    Example:
        >>> data = bytes([0x90, 60, 80])  # Note on, middle C, velocity 80
        >>> messages = bytes_to_midimessage(data)
        >>> len(messages)
        1
    """
    from synth.midi import RealtimeParser
    parser: RealtimeParser = RealtimeParser()
    return parser.parse_bytes(data)
