"""
MIDI Utility Functions

Common utility functions for MIDI processing.
"""

from typing import Optional
from .message import MIDIMessage


def tempo2bpm(tempo_us: int) -> float:
    """
    Convert tempo in microseconds per beat to BPM.
    
    Args:
        tempo_us: Tempo in microseconds per quarter note
    
    Returns:
        Tempo in beats per minute
    
    Example:
        >>> tempo2bpm(500000)  # 120 BPM
        120.0
    """
    return 60000000.0 / tempo_us


def bpm2tempo(bpm: float) -> int:
    """
    Convert BPM to microseconds per beat.
    
    Args:
        bpm: Tempo in beats per minute
    
    Returns:
        Tempo in microseconds per quarter note
    
    Example:
        >>> bpm2tempo(120.0)  # 500000 μs
        500000
    """
    return int(60000000.0 / bpm)


def ticks_to_seconds(ticks: int, division: int, tempo_us: int) -> float:
    """
    Convert MIDI ticks to seconds.
    
    Args:
        ticks: Number of ticks
        division: PPQ (pulses per quarter note)
        tempo_us: Tempo in microseconds per quarter note
    
    Returns:
        Time in seconds
    
    Example:
        >>> ticks_to_seconds(960, 960, 500000)  # 1 quarter note at 120 BPM
        0.5
    """
    seconds_per_tick = (tempo_us / 1000000.0) / division
    return ticks * seconds_per_tick


def seconds_to_ticks(seconds: float, division: int, tempo_us: int) -> int:
    """
    Convert seconds to MIDI ticks.
    
    Args:
        seconds: Time in seconds
        division: PPQ (pulses per quarter note)
        tempo_us: Tempo in microseconds per quarter note
    
    Returns:
        Number of ticks
    
    Example:
        >>> seconds_to_ticks(0.5, 960, 500000)  # 1 quarter note
        960
    """
    seconds_per_tick = (tempo_us / 1000000.0) / division
    return int(seconds / seconds_per_tick)


def message_type_to_status(msg_type: str, channel: int = 0) -> int:
    """
    Convert message type and channel to MIDI status byte.
    
    Args:
        msg_type: Message type (note_on, note_off, etc.)
        channel: MIDI channel (0-15)
    
    Returns:
        MIDI status byte
    
    Example:
        >>> message_type_to_status('note_on', 0)
        144  # 0x90
    """
    status_map = {
        'note_off': 0x80,
        'note_on': 0x90,
        'poly_pressure': 0xA0,
        'control_change': 0xB0,
        'program_change': 0xC0,
        'channel_pressure': 0xD0,
        'pitch_bend': 0xE0,
    }
    
    base_status = status_map.get(msg_type, 0)
    return base_status | (channel & 0x0F)


def status_to_message_type(status: int) -> tuple:
    """
    Convert MIDI status byte to message type and channel.
    
    Args:
        status: MIDI status byte
    
    Returns:
        Tuple of (message_type, channel)
    
    Example:
        >>> status_to_message_type(0x90)
        ('note_on', 0)
    """
    type_map = {
        0x80: 'note_off',
        0x90: 'note_on',
        0xA0: 'poly_pressure',
        0xB0: 'control_change',
        0xC0: 'program_change',
        0xD0: 'channel_pressure',
        0xE0: 'pitch_bend',
    }
    
    msg_type = type_map.get(status & 0xF0, 'unknown')
    channel = status & 0x0F
    return msg_type, channel
