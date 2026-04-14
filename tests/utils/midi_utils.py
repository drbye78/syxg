"""
MIDI Testing Utilities for XG Synthesizer Test Suite

Provides helper functions for creating MIDI messages for testing.
"""

from __future__ import annotations

from synth.io.midi.message import MIDIMessage
from typing import Any


def create_note_on_message(
    note: int = 60, velocity: int = 100, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Note On MIDI message.

    Args:
        note: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="note_on",
        channel=channel,
        data={"note": note, "velocity": velocity},
        timestamp=timestamp,
    )


def create_note_off_message(
    note: int = 60, velocity: int = 0, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Note Off MIDI message.

    Args:
        note: MIDI note number (0-127)
        velocity: Release velocity (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="note_off",
        channel=channel,
        data={"note": note, "velocity": velocity},
        timestamp=timestamp,
    )


def create_control_change_message(
    controller: int = 0, value: int = 0, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Control Change MIDI message.

    Args:
        controller: Controller number (0-127)
        value: Controller value (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="control_change",
        channel=channel,
        data={"controller": controller, "value": value},
        timestamp=timestamp,
    )


def create_program_change_message(
    program: int = 0, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Program Change MIDI message.

    Args:
        program: Program number (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="program_change",
        channel=channel,
        data={"program": program},
        timestamp=timestamp,
    )


def create_pitch_bend_message(
    value: int = 8192, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Pitch Bend MIDI message.

    Args:
        value: Pitch bend value (0-16383, 8192 = center)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="pitch_bend",
        channel=channel,
        data={"value": value},
        timestamp=timestamp,
    )


def create_sysex_message(data: list[int], timestamp: float = 0.0) -> MIDIMessage:
    """
    Create a System Exclusive MIDI message.

    Args:
        data: SysEx data bytes
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="sysex",
        data={"raw_data": data},
        timestamp=timestamp,
    )


def create_channel_pressure_message(
    pressure: int = 0, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Channel Pressure (aftertouch) MIDI message.

    Args:
        pressure: Pressure value (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="channel_pressure",
        channel=channel,
        data={"pressure": pressure},
        timestamp=timestamp,
    )


def create_poly_pressure_message(
    note: int = 60, pressure: int = 0, channel: int = 0, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Polyphonic Pressure (key aftertouch) MIDI message.

    Args:
        note: MIDI note number (0-127)
        pressure: Pressure value (0-127)
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="poly_pressure",
        channel=channel,
        data={"note": note, "pressure": pressure},
        timestamp=timestamp,
    )


def create_tempo_message(tempo_us_per_beat: int = 500000, timestamp: float = 0.0) -> MIDIMessage:
    """
    Create a Set Tempo meta message.

    Args:
        tempo_us_per_beat: Tempo in microseconds per beat (default 120 BPM)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="tempo",
        data={"tempo_us_per_beat": tempo_us_per_beat},
        timestamp=timestamp,
    )


def create_time_signature_message(
    numerator: int = 4, denominator: int = 4, timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Time Signature meta message.

    Args:
        numerator: Time signature numerator
        denominator: Time signature denominator
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="time_signature",
        data={
            "numerator": numerator,
            "denominator": denominator,
            "metronome_pulse": 24,
            "thirty_seconds_per_quarter": 8,
        },
        timestamp=timestamp,
    )


def create_key_signature_message(
    key: int = 0, scale: str = "major", timestamp: float = 0.0
) -> MIDIMessage:
    """
    Create a Key Signature meta message.

    Args:
        key: Key signature (-7 to +7, negative = flats, positive = sharps)
        scale: Scale type ('major' or 'minor')
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(
        type="key_signature",
        data={"key": key, "scale": scale},
        timestamp=timestamp,
    )


def create_end_of_track_message(timestamp: float = 0.0) -> MIDIMessage:
    """
    Create an End of Track meta message.

    Args:
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    return MIDIMessage(type="end_of_track", timestamp=timestamp)


def create_xg_sysex_reset(timestamp: float = 0.0) -> MIDIMessage:
    """
    Create an XG System Reset SysEx message.

    Args:
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    # XG System Reset: F0 43 10 4C 00 00 7E 00 F7
    return create_sysex_message([0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7], timestamp)


def create_xg_normal_part_mode(channel: int, timestamp: float = 0.0) -> MIDIMessage:
    """
    Create an XG Normal Part Mode SysEx message.

    Args:
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    # XG Normal Part Mode: F0 43 10 4C 08 [channel] 00 00 00 F7
    return create_sysex_message(
        [0xF0, 0x43, 0x10, 0x4C, 0x08, channel & 0x0F, 0x00, 0x00, 0x00, 0xF7], timestamp
    )


def create_xg_drum_part_mode(channel: int, timestamp: float = 0.0) -> MIDIMessage:
    """
    Create an XG Drum Part Mode SysEx message.

    Args:
        channel: MIDI channel (0-15)
        timestamp: Message timestamp in seconds

    Returns:
        MIDIMessage object
    """
    # XG Drum Part Mode: F0 43 10 4C 08 [channel] 01 00 00 F7
    return create_sysex_message(
        [0xF0, 0x43, 0x10, 0x4C, 0x08, channel & 0x0F, 0x01, 0x00, 0x00, 0xF7], timestamp
    )


def create_note_sequence(
    notes: list[int],
    velocities: list[int] | None = None,
    durations: list[float] | None = None,
    channel: int = 0,
    start_time: float = 0.0,
    tempo: float = 120.0,
) -> list[MIDIMessage]:
    """
    Create a sequence of note on/off messages.

    Args:
        notes: List of MIDI note numbers
        velocities: List of velocities (default 100 for all)
        durations: List of note durations in seconds (default 0.5 for all)
        channel: MIDI channel (0-15)
        start_time: Start time in seconds
        tempo: Tempo in BPM for duration calculation

    Returns:
        List of MIDIMessage objects
    """
    if velocities is None:
        velocities = [100] * len(notes)
    if durations is None:
        durations = [0.5] * len(notes)

    messages = []
    current_time = start_time

    for note, velocity, duration in zip(notes, velocities, durations):
        # Note on
        messages.append(create_note_on_message(note, velocity, channel, current_time))
        # Note off
        messages.append(create_note_off_message(note, 0, channel, current_time + duration))
        current_time += duration

    return messages


def create_chord(
    notes: list[int],
    velocity: int = 100,
    duration: float = 1.0,
    channel: int = 0,
    start_time: float = 0.0,
) -> list[MIDIMessage]:
    """
    Create a chord (simultaneous notes).

    Args:
        notes: List of MIDI note numbers
        velocity: Note velocity
        duration: Chord duration in seconds
        channel: MIDI channel (0-15)
        start_time: Start time in seconds

    Returns:
        List of MIDIMessage objects
    """
    messages = []

    # All notes on at the same time
    for note in notes:
        messages.append(create_note_on_message(note, velocity, channel, start_time))

    # All notes off at the same time
    for note in notes:
        messages.append(create_note_off_message(note, 0, channel, start_time + duration))

    return messages


def create_scale(
    root: int = 60,
    scale_type: str = "major",
    velocity: int = 100,
    duration: float = 0.5,
    channel: int = 0,
    start_time: float = 0.0,
) -> list[MIDIMessage]:
    """
    Create a musical scale.

    Args:
        root: Root note MIDI number
        scale_type: Scale type ('major', 'minor', 'chromatic')
        velocity: Note velocity
        duration: Note duration in seconds
        channel: MIDI channel (0-15)
        start_time: Start time in seconds

    Returns:
        List of MIDIMessage objects
    """
    scale_intervals = {
        "major": [0, 2, 4, 5, 7, 9, 11, 12],
        "minor": [0, 2, 3, 5, 7, 8, 10, 12],
        "chromatic": list(range(13)),
    }

    intervals = scale_intervals.get(scale_type, scale_intervals["major"])
    notes = [root + interval for interval in intervals]

    return create_note_sequence(notes, None, [duration] * len(notes), channel, start_time)