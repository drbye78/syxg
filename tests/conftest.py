"""
Pytest Configuration and Fixtures for XG Synthesizer Test Suite

Provides shared fixtures for SF2 engine, synthesizer, and test utilities.
"""

from __future__ import annotations

import os
import pytest
import numpy as np

from synth.engine.sf2_engine import SF2Engine
from synth.midi.file import FileParser


@pytest.fixture(scope="session")
def sample_rate():
    """Audio sample rate for testing."""
    return 44100


@pytest.fixture(scope="session")
def block_size():
    """Audio block size for testing."""
    return 1024


@pytest.fixture(scope="session")
def test_duration():
    """Default test duration in seconds."""
    return 1.0


@pytest.fixture(scope="session")
def sf2_test_file():
    """Path to test SF2 file - uses reference SF2 file."""
    # Use reference SF2 file for testing
    ref_file = os.path.join(os.path.dirname(__file__), "ref.sf2")
    if os.path.exists(ref_file):
        return ref_file
    return None


@pytest.fixture(scope="session")
def midi_test_file():
    """Path to test MIDI file."""
    test_file = os.path.join(os.path.dirname(__file__), "test.mid")
    if os.path.exists(test_file):
        return test_file
    return None


@pytest.fixture(scope="function")
def sf2_engine(sample_rate, block_size, sf2_test_file):
    """
    Create SF2 engine for testing.

    If no SF2 file is available, creates engine without loading soundfont.
    """
    engine = SF2Engine(
        sf2_file_path=sf2_test_file,
        sample_rate=sample_rate,
        block_size=block_size,
        max_memory_mb=256,
    )
    yield engine
    # Cleanup
    engine.clear_cache()


@pytest.fixture(scope="function")
def midi_parser():
    """Create MIDI file parser."""
    return FileParser()


@pytest.fixture(scope="session")
def silence_buffer(sample_rate, block_size):
    """Create a silence buffer for testing."""
    return np.zeros(block_size * 2, dtype=np.float32)  # Stereo


@pytest.fixture(scope="session")
def mono_silence_buffer(sample_rate, block_size):
    """Create a mono silence buffer for testing."""
    return np.zeros(block_size, dtype=np.float32)


@pytest.fixture(scope="function")
def random_audio_buffer(sample_rate, block_size):
    """Create a random audio buffer for testing."""
    return np.random.randn(block_size * 2).astype(np.float32) * 0.5  # Stereo


@pytest.fixture(scope="function")
def mono_random_audio_buffer(sample_rate, block_size):
    """Create a mono random audio buffer for testing."""
    return np.random.randn(block_size).astype(np.float32) * 0.5


@pytest.fixture(scope="session")
def test_frequencies():
    """Standard test frequencies."""
    return {
        "A4": 440.0,
        "C4": 261.63,
        "C5": 523.25,
        "A0": 27.5,
        "C8": 4186.01,
    }


@pytest.fixture(scope="session")
def test_notes():
    """Standard test MIDI notes."""
    return {
        "C4": 60,
        "D4": 62,
        "E4": 64,
        "F4": 65,
        "G4": 67,
        "A4": 69,
        "B4": 71,
        "C5": 72,
    }


@pytest.fixture(scope="session")
def test_velocities():
    """Standard test velocities."""
    return {
        "ppp": 16,
        "pp": 32,
        "p": 48,
        "mp": 64,
        "mf": 80,
        "f": 96,
        "ff": 112,
        "fff": 127,
    }


@pytest.fixture(scope="session")
def test_controllers():
    """Standard MIDI controller numbers."""
    return {
        "mod_wheel": 1,
        "breath": 2,
        "foot": 4,
        "portamento_time": 5,
        "volume": 7,
        "balance": 8,
        "pan": 10,
        "expression": 11,
        "sustain": 64,
        "portamento": 65,
        "sostenuto": 66,
        "soft_pedal": 67,
        "filter_cutoff": 74,
        "reverb_send": 91,
        "chorus_send": 93,
        "variation_send": 94,
    }


@pytest.fixture(scope="session")
def xg_part_modes():
    """XG part mode values."""
    return {
        "normal": 0,
        "drum": 1,
        "single": 2,
        "hyper_scream": 3,
        "analog": 4,
        "max_resonance": 5,
        "stereo": 6,
        "wah": 7,
        "dynamic": 8,
        "distortion": 9,
    }


@pytest.fixture(scope="session")
def reverb_types():
    """XG reverb type values."""
    return {
        "hall1": 1,
        "hall2": 2,
        "hall3": 3,
        "room1": 9,
        "room2": 10,
        "room3": 11,
        "plate1": 17,
        "plate2": 18,
        "white_room": 25,
        "tunnel": 26,
        "canyon": 27,
        "basement": 28,
    }


@pytest.fixture(scope="session")
def chorus_types():
    """XG chorus type values."""
    return {
        "chorus1": 0,
        "chorus2": 1,
        "chorus3": 2,
        "chorus4": 3,
        "feedback_chorus": 4,
        "flanger1": 5,
        "flanger2": 6,
        "flanger3": 7,
        "symphonic": 8,
        "rotary_speaker": 9,
    }


@pytest.fixture(scope="session")
def insertion_effect_types():
    """XG insertion effect type values."""
    return {
        "off": 0,
        "thru": 1,
        "distortion": 64,
        "overdrive": 65,
        "amp_simulator": 66,
        "3_band_eq": 67,
        "parametric_eq": 68,
        "compressor": 69,
        "expander": 70,
        "gate": 71,
        "chorus": 72,
        "flanger": 73,
        "phaser": 74,
        "distortion_plus": 75,
        "overdrive_plus": 76,
        "speaker_simulator": 77,
    }


@pytest.fixture(scope="function")
def modulation_matrix_params():
    """Default modulation matrix parameters."""
    return {
        "routes": [
            {"source": "lfo1", "destination": "pitch", "amount": 50.0, "polarity": 1.0},
            {"source": "velocity", "destination": "amp", "amount": 0.5, "velocity_sensitivity": 0.5},
            {"source": "mod_wheel", "destination": "lfo1_depth", "amount": 1.0, "polarity": 1.0},
            {"source": "expression", "destination": "amp", "amount": 0.8, "polarity": 1.0},
        ]
    }


@pytest.fixture(scope="function")
def envelope_params():
    """Default envelope parameters."""
    return {
        "amp": {
            "delay": 0.0,
            "attack": 0.01,
            "hold": 0.0,
            "decay": 0.3,
            "sustain": 0.7,
            "release": 0.5,
        },
        "filter": {
            "delay": 0.0,
            "attack": 0.05,
            "hold": 0.0,
            "decay": 0.2,
            "sustain": 0.5,
            "release": 0.3,
            "depth": 5000.0,
        },
        "pitch": {
            "delay": 0.0,
            "attack": 0.01,
            "hold": 0.0,
            "decay": 0.1,
            "sustain": 0.0,
            "release": 0.1,
            "depth": 100.0,
        },
    }


@pytest.fixture(scope="function")
def lfo_params():
    """Default LFO parameters."""
    return {
        "lfo1": {
            "waveform": "sine",
            "rate": 5.0,
            "depth": 0.5,
            "delay": 0.0,
            "fade": 0.0,
        },
        "lfo2": {
            "waveform": "triangle",
            "rate": 2.0,
            "depth": 0.3,
            "delay": 0.0,
            "fade": 0.0,
        },
        "lfo3": {
            "waveform": "sawtooth",
            "rate": 0.5,
            "depth": 0.1,
            "delay": 0.5,
            "fade": 0.2,
        },
    }


@pytest.fixture(scope="function")
def filter_params():
    """Default filter parameters."""
    return {
        "type": "lowpass",
        "cutoff": 20000.0,
        "resonance": 0.7,
        "key_follow": 0.5,
        "velocity_sensitivity": 0.3,
    }


@pytest.fixture(scope="session")
def ref_sf2_path():
    """Provide path to reference SF2 file for testing."""
    sf2_path = os.path.join(os.path.dirname(__file__), "ref.sf2")
    if not os.path.exists(sf2_path):
        pytest.skip("Reference SF2 file not found")
    return sf2_path


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "system: System tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_sf2: Tests requiring SF2 file")
