"""
Test Data Generator for XG Synthesizer Test Suite

Provides functions for generating test SF2 data, MIDI sequences, and reference audio.
"""

from __future__ import annotations

import numpy as np
from typing import Any

from .audio_utils import generate_test_frequency, generate_white_noise


def generate_sf2_test_data(sample_rate: int = 44100) -> dict[str, Any]:
    """
    Generate test SF2-like data for testing without actual SF2 files.

    Args:
        sample_rate: Audio sample rate in Hz

    Returns:
        Dictionary containing test sample data and parameters
    """
    # Generate simple test samples
    duration = 0.5  # 500ms samples

    # Sine wave sample (A4 = 440Hz)
    sine_sample = generate_test_frequency(440.0, duration, sample_rate, 0.8)

    # Sawtooth-like sample (using harmonics)
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    sawtooth_sample = np.zeros_like(t)
    for harmonic in range(1, 8):
        sawtooth_sample += np.sin(2 * np.pi * 440.0 * harmonic * t) / harmonic
    sawtooth_sample = sawtooth_sample * 0.3

    # Square wave sample (using odd harmonics)
    square_sample = np.zeros_like(t)
    for harmonic in range(1, 8, 2):
        square_sample += np.sin(2 * np.pi * 440.0 * harmonic * t) / harmonic
    square_sample = square_sample * 0.4

    # Noise sample
    noise_sample = generate_white_noise(duration, sample_rate, 0.5)

    return {
        "samples": {
            0: {"name": "Sine 440Hz", "data": sine_sample, "root_key": 69, "loop_mode": 1},
            1: {"name": "Sawtooth 440Hz", "data": sawtooth_sample, "root_key": 69, "loop_mode": 1},
            2: {"name": "Square 440Hz", "data": square_sample, "root_key": 69, "loop_mode": 1},
            3: {"name": "Noise", "data": noise_sample, "root_key": 60, "loop_mode": 0},
        },
        "presets": {
            0: {
                "name": "Test Piano",
                "bank": 0,
                "program": 0,
                "zones": [
                    {
                        "sample_id": 0,
                        "key_range": (0, 127),
                        "velocity_range": (0, 127),
                        "amp_attack": 0.01,
                        "amp_decay": 0.3,
                        "amp_sustain": 0.7,
                        "amp_release": 0.5,
                        "filter_cutoff": 20000.0,
                        "filter_resonance": 0.7,
                        "pan": 0.0,
                    }
                ],
            },
            1: {
                "name": "Test Strings",
                "bank": 0,
                "program": 48,
                "zones": [
                    {
                        "sample_id": 1,
                        "key_range": (0, 127),
                        "velocity_range": (0, 127),
                        "amp_attack": 0.5,
                        "amp_decay": 0.2,
                        "amp_sustain": 0.8,
                        "amp_release": 0.8,
                        "filter_cutoff": 5000.0,
                        "filter_resonance": 0.5,
                        "pan": 0.0,
                    }
                ],
            },
            2: {
                "name": "Test Brass",
                "bank": 0,
                "program": 61,
                "zones": [
                    {
                        "sample_id": 2,
                        "key_range": (0, 127),
                        "velocity_range": (0, 127),
                        "amp_attack": 0.1,
                        "amp_decay": 0.1,
                        "amp_sustain": 0.9,
                        "amp_release": 0.3,
                        "filter_cutoff": 8000.0,
                        "filter_resonance": 0.8,
                        "pan": 0.0,
                    }
                ],
            },
        },
    }


def generate_midi_test_sequence(sequence_type: str = "scale", channel: int = 0) -> list[dict]:
    """
    Generate test MIDI message sequences.

    Args:
        sequence_type: Type of sequence ('scale', 'chord', 'arpeggio', 'random')
        channel: MIDI channel (0-15)

    Returns:
        List of MIDI message dictionaries
    """
    messages = []

    if sequence_type == "scale":
        # C major scale
        notes = [60, 62, 64, 65, 67, 69, 71, 72]
        for i, note in enumerate(notes):
            messages.append({
                "type": "note_on",
                "channel": channel,
                "note": note,
                "velocity": 100,
                "time": i * 0.5,
            })
            messages.append({
                "type": "note_off",
                "channel": channel,
                "note": note,
                "velocity": 0,
                "time": i * 0.5 + 0.4,
            })

    elif sequence_type == "chord":
        # C major chord
        notes = [60, 64, 67]
        for note in notes:
            messages.append({
                "type": "note_on",
                "channel": channel,
                "note": note,
                "velocity": 100,
                "time": 0.0,
            })
        for note in notes:
            messages.append({
                "type": "note_off",
                "channel": channel,
                "note": note,
                "velocity": 0,
                "time": 1.0,
            })

    elif sequence_type == "arpeggio":
        # C major arpeggio
        notes = [60, 64, 67, 72, 67, 64]
        for i, note in enumerate(notes):
            messages.append({
                "type": "note_on",
                "channel": channel,
                "note": note,
                "velocity": 100,
                "time": i * 0.2,
            })
            messages.append({
                "type": "note_off",
                "channel": channel,
                "note": note,
                "velocity": 0,
                "time": i * 0.2 + 0.15,
            })

    elif sequence_type == "random":
        # Random notes
        import random
        random.seed(42)  # For reproducibility
        for i in range(16):
            note = random.randint(48, 84)
            velocity = random.randint(60, 127)
            messages.append({
                "type": "note_on",
                "channel": channel,
                "note": note,
                "velocity": velocity,
                "time": i * 0.25,
            })
            messages.append({
                "type": "note_off",
                "channel": channel,
                "note": note,
                "velocity": 0,
                "time": i * 0.25 + 0.2,
            })

    return messages


def generate_reference_audio(
    audio_type: str = "sine",
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 44100,
) -> np.ndarray:
    """
    Generate reference audio for comparison testing.

    Args:
        audio_type: Type of audio ('sine', 'noise', 'silence')
        frequency: Frequency in Hz (for sine waves)
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Reference audio buffer as float32 numpy array
    """
    if audio_type == "sine":
        return generate_test_frequency(frequency, duration, sample_rate, 0.8)
    elif audio_type == "noise":
        return generate_white_noise(duration, sample_rate, 0.5)
    elif audio_type == "silence":
        return np.zeros(int(sample_rate * duration), dtype=np.float32)
    else:
        raise ValueError(f"Unknown audio type: {audio_type}")


def generate_controller_sequence(
    controller: int = 1,
    start_value: int = 0,
    end_value: int = 127,
    steps: int = 16,
    channel: int = 0,
) -> list[dict]:
    """
    Generate a sequence of controller changes.

    Args:
        controller: Controller number (0-127)
        start_value: Starting value
        end_value: Ending value
        steps: Number of steps
        channel: MIDI channel (0-15)

    Returns:
        List of controller change dictionaries
    """
    messages = []
    value_step = (end_value - start_value) / (steps - 1)

    for i in range(steps):
        value = int(start_value + i * value_step)
        messages.append({
            "type": "control_change",
            "channel": channel,
            "controller": controller,
            "value": value,
            "time": i * 0.1,
        })

    return messages


def generate_pitch_bend_sequence(
    start_value: int = 8192,
    end_value: int = 16383,
    steps: int = 16,
    channel: int = 0,
) -> list[dict]:
    """
    Generate a sequence of pitch bend changes.

    Args:
        start_value: Starting value (0-16383, 8192 = center)
        end_value: Ending value
        steps: Number of steps
        channel: MIDI channel (0-15)

    Returns:
        List of pitch bend dictionaries
    """
    messages = []
    value_step = (end_value - start_value) / (steps - 1)

    for i in range(steps):
        value = int(start_value + i * value_step)
        messages.append({
            "type": "pitch_bend",
            "channel": channel,
            "value": value,
            "time": i * 0.1,
        })

    return messages


def generate_velocity_curve(
    note: int = 60,
    start_velocity: int = 1,
    end_velocity: int = 127,
    steps: int = 16,
    channel: int = 0,
) -> list[dict]:
    """
    Generate a sequence of notes with varying velocities.

    Args:
        note: MIDI note number
        start_velocity: Starting velocity
        end_velocity: Ending velocity
        steps: Number of steps
        channel: MIDI channel (0-15)

    Returns:
        List of note on/off dictionaries
    """
    messages = []
    velocity_step = (end_velocity - start_velocity) / (steps - 1)

    for i in range(steps):
        velocity = int(start_velocity + i * velocity_step)
        messages.append({
            "type": "note_on",
            "channel": channel,
            "note": note,
            "velocity": velocity,
            "time": i * 0.5,
        })
        messages.append({
            "type": "note_off",
            "channel": channel,
            "note": note,
            "velocity": 0,
            "time": i * 0.5 + 0.4,
        })

    return messages


def generate_key_range_test(channel: int = 0) -> list[dict]:
    """
    Generate notes across the full key range for zone testing.

    Args:
        channel: MIDI channel (0-15)

    Returns:
        List of note on/off dictionaries
    """
    messages = []
    # Play notes at key boundaries
    test_notes = [0, 24, 48, 60, 72, 96, 127]

    for i, note in enumerate(test_notes):
        messages.append({
            "type": "note_on",
            "channel": channel,
            "note": note,
            "velocity": 100,
            "time": i * 0.5,
        })
        messages.append({
            "type": "note_off",
            "channel": channel,
            "note": note,
            "velocity": 0,
            "time": i * 0.5 + 0.4,
        })

    return messages


def generate_velocity_range_test(note: int = 60, channel: int = 0) -> list[dict]:
    """
    Generate notes with velocities across the full range for zone testing.

    Args:
        note: MIDI note number
        channel: MIDI channel (0-15)

    Returns:
        List of note on/off dictionaries
    """
    messages = []
    # Play notes at velocity boundaries
    test_velocities = [1, 32, 64, 96, 127]

    for i, velocity in enumerate(test_velocities):
        messages.append({
            "type": "note_on",
            "channel": channel,
            "note": note,
            "velocity": velocity,
            "time": i * 0.5,
        })
        messages.append({
            "type": "note_off",
            "channel": channel,
            "note": note,
            "velocity": 0,
            "time": i * 0.5 + 0.4,
        })

    return messages


def generate_polyphony_test(
    num_notes: int = 16,
    note_spacing: float = 0.05,
    channel: int = 0,
) -> list[dict]:
    """
    Generate overlapping notes for polyphony testing.

    Args:
        num_notes: Number of overlapping notes
        note_spacing: Time between note ons
        channel: MIDI channel (0-15)

    Returns:
        List of note on/off dictionaries
    """
    messages = []
    base_note = 60
    note_duration = 1.0

    for i in range(num_notes):
        note = base_note + (i % 12)  # Cycle through notes
        messages.append({
            "type": "note_on",
            "channel": channel,
            "note": note,
            "velocity": 100,
            "time": i * note_spacing,
        })
        messages.append({
            "type": "note_off",
            "channel": channel,
            "note": note,
            "velocity": 0,
            "time": i * note_spacing + note_duration,
        })

    return messages