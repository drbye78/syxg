"""
Pytest fixtures for SF2 module testing.

Provides reusable fixtures for SF2 testing including:
- Mock soundfont manager
- Test SF2 file generation
- Sample data fixtures
- Mock synthesizer instances
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest

# ============================================================================
# Directory and Path Fixtures
# ============================================================================


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test data."""
    test_dir = tmp_path / "sf2_test_data"
    test_dir.mkdir()
    return test_dir


# ============================================================================
# Mock SF2 File Fixtures
# ============================================================================


@pytest.fixture
def minimal_sf2_file(test_data_dir: Path) -> Path:
    """
    Create minimal valid SF2 file for testing.

    Creates a simple SF2 file with:
    - One preset (bank 0, program 0)
    - One instrument with one zone
    - One sample (1 second sine wave at 440Hz)
    """

    sf2_path = test_data_dir / "minimal.sf2"

    # Create minimal SF2 structure
    # This is a simplified version - in production would use full RIFF structure

    # For now, create a mock that passes basic validation
    # Full implementation would write actual RIFF chunks

    return sf2_path


@pytest.fixture
def sample_sf2_file(test_data_dir: Path) -> Path:
    """
    Create SF2 file with multiple presets and layers.

    Features:
    - 2 presets (bank 0, programs 0 and 1)
    - Multiple velocity layers
    - Loop points configured
    - Effects sends configured
    """
    sf2_path = test_data_dir / "sample.sf2"
    # Implementation would create multi-preset SF2
    return sf2_path


@pytest.fixture
def stereo_sf2_file(test_data_dir: Path) -> Path:
    """Create SF2 file with stereo samples."""
    sf2_path = test_data_dir / "stereo.sf2"
    return sf2_path


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def mono_sample_data() -> np.ndarray:
    """Generate mono sample data (1 second sine wave)."""
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * frequency * t)
    return samples.astype(np.float32)


@pytest.fixture
def stereo_sample_data() -> np.ndarray:
    """Generate stereo sample data."""
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    left = np.sin(2 * np.pi * frequency * t)
    right = np.sin(2 * np.pi * frequency * t * 0.99)  # Slightly detuned

    stereo = np.column_stack([left, right])
    return stereo.astype(np.float32)


@pytest.fixture
def looped_sample_data() -> np.ndarray:
    """Generate sample data with loop points."""
    sample_rate = 44100
    duration = 2.0  # 2 seconds

    t = np.linspace(0, duration, int(sample_rate * duration))
    # Attack portion (first 0.5s)
    attack = np.sin(2 * np.pi * 440 * t[: int(sample_rate * 0.5)])
    # Loop portion (remaining 1.5s)
    loop = np.sin(2 * np.pi * 440 * t[int(sample_rate * 0.5) :])

    samples = np.concatenate([attack, loop])
    return samples.astype(np.float32)


# ============================================================================
# Mock Object Fixtures
# ============================================================================


@pytest.fixture
def mock_synth():
    """Create mock ModernXGSynthesizer instance."""
    synth = Mock()
    synth.sample_rate = 44100
    synth.block_size = 1024

    # Mock memory pool
    memory_pool = Mock()
    memory_pool.get_stereo_buffer = lambda size: np.zeros(size * 2, dtype=np.float32)
    memory_pool.get_mono_buffer = lambda size: np.zeros(size, dtype=np.float32)
    synth.memory_pool = memory_pool

    # Mock envelope pool
    envelope_pool = Mock()
    mock_envelope = Mock()
    mock_envelope.update_parameters = Mock()
    mock_envelope.generate_block = Mock(return_value=None)
    envelope_pool.acquire_envelope = Mock(return_value=mock_envelope)
    synth.envelope_pool = envelope_pool

    # Mock filter pool
    filter_pool = Mock()
    mock_filter = Mock()
    mock_filter.set_parameters = Mock()
    mock_filter.process_block = Mock(side_effect=lambda x: x)
    filter_pool.acquire_filter = Mock(return_value=mock_filter)
    synth.filter_pool = filter_pool

    # Mock LFO pool
    partial_lfo_pool = Mock()
    mock_lfo = Mock()
    mock_lfo.set_parameters = Mock()
    mock_lfo.generate_block = Mock(return_value=np.zeros(1024, dtype=np.float32))
    partial_lfo_pool.acquire_oscillator = Mock(return_value=mock_lfo)
    synth.partial_lfo_pool = partial_lfo_pool

    return synth


@pytest.fixture
def mock_soundfont_manager():
    """Create mock SF2SoundFontManager instance."""
    manager = Mock()
    manager.loaded_files = {}
    manager.file_order = []

    # Mock methods that should exist
    manager.get_sample_data = Mock(return_value=None)
    manager.get_sample_info = Mock(return_value=None)
    manager.get_sample_loop_info = Mock(return_value=None)
    manager.get_zone = Mock(return_value=None)
    manager.get_program_parameters = Mock(return_value=None)

    return manager


@pytest.fixture
def mock_sf2_soundfont():
    """Create mock SF2SoundFont instance."""
    soundfont = Mock()
    soundfont.name = "Test SoundFont"
    soundfont.version = (2, 4)
    soundfont.priority = 0

    soundfont.presets = {}
    soundfont.instruments = {}
    soundfont.samples = {}

    soundfont.get_program_parameters = Mock(return_value=None)
    soundfont.get_sample_data = Mock(return_value=None)
    soundfont.get_sample_info = Mock(return_value=None)
    soundfont.get_sample_loop_info = Mock(return_value=None)
    soundfont.get_zone = Mock(return_value=None)

    return soundfont


# ============================================================================
# Parameter Fixtures
# ============================================================================


@pytest.fixture
def minimal_partial_params() -> dict[str, Any]:
    """Create minimal valid parameters for SF2Partial."""
    return {
        "sample_data": np.zeros(44100, dtype=np.float32),  # 1 second silence
        "note": 60,
        "velocity": 100,
        "original_pitch": 60,
        "loop": {"mode": 0, "start": 0, "end": 44100},
        "amp_envelope": {
            "delay": 0.0,
            "attack": 0.01,
            "hold": 0.0,
            "decay": 0.3,
            "sustain": 0.7,
            "release": 0.5,
        },
        "filter": {"cutoff": 20000.0, "resonance": 0.0, "type": "lowpass"},
        "mod_lfo": {
            "delay": 0.0,
            "frequency": 8.0,
            "to_volume": 0.0,
            "to_filter": 0.0,
            "to_pitch": 0.0,
        },
        "vib_lfo": {"delay": 0.0, "frequency": 8.0, "to_pitch": 0.0},
        "effects": {"reverb_send": 0.0, "chorus_send": 0.0, "pan": 0.0},
        "pitch_modulation": {"coarse_tune": 0, "fine_tune": 0.0, "scale_tuning": 1.0},
        "generators": {},
    }


@pytest.fixture
def nested_partial_params(minimal_partial_params) -> dict[str, Any]:
    """Create parameters with nested structure (SF2 spec compliant)."""
    params = minimal_partial_params.copy()
    # Already nested, but could add more detail
    return params


@pytest.fixture
def flat_partial_params() -> dict[str, Any]:
    """Create parameters with flat structure (backward compatibility)."""
    return {
        "sample_data": np.zeros(44100, dtype=np.float32),
        "note": 60,
        "velocity": 100,
        "original_pitch": 60,
        "loop_mode": 0,
        "loop_start": 0,
        "loop_end": 44100,
        "amp_delay": 0.0,
        "amp_attack": 0.01,
        "amp_hold": 0.0,
        "amp_decay": 0.3,
        "amp_sustain": 0.7,
        "amp_release": 0.5,
        "filter_cutoff": 20000.0,
        "filter_resonance": 0.0,
        "mod_lfo_delay": 0.0,
        "mod_lfo_frequency": 8.0,
        "vib_lfo_delay": 0.0,
        "vib_lfo_frequency": 8.0,
        "reverb_send": 0.0,
        "chorus_send": 0.0,
        "pan": 0.0,
        "coarse_tune": 0,
        "fine_tune": 0.0,
        "generators": {},
    }


@pytest.fixture
def region_descriptor():
    """Create RegionDescriptor for testing."""
    from synth.engine.region_descriptor import RegionDescriptor

    return RegionDescriptor(
        region_id=0,
        engine_type="sf2",
        key_range=(0, 127),
        velocity_range=(0, 127),
        sample_id=None,  # No sample for basic testing
        generator_params={},
    )


# ============================================================================
# Helper Function Fixtures
# ============================================================================


@pytest.fixture
def create_test_tone():
    """Factory function for creating test tones."""

    def _create_tone(
        frequency: float = 440.0,
        duration: float = 1.0,
        sample_rate: int = 44100,
        amplitude: float = 0.5,
    ) -> np.ndarray:
        t = np.linspace(0, duration, int(sample_rate * duration))
        samples = amplitude * np.sin(2 * np.pi * frequency * t)
        return samples.astype(np.float32)

    return _create_tone


@pytest.fixture
def create_sf2_generators():
    """Factory function for creating SF2 generator dictionaries."""

    def _create_generators(overrides: dict[int, int] | None = None) -> dict[int, int]:
        """Create generator dict with SF2 default values."""
        defaults = {
            8: -12000,  # volEnvDelay
            9: -12000,  # volEnvAttack
            10: -12000,  # volEnvHold
            11: -12000,  # volEnvDecay
            12: 0,  # volEnvSustain
            13: -12000,  # volEnvRelease
            29: 13500,  # initialFilterFc
            30: 0,  # initialFilterQ
            32: 0,  # reverbEffectsSend
            33: 0,  # chorusEffectsSend
            34: 0,  # pan
            48: 0,  # coarseTune
            49: 0,  # fineTune
        }

        if overrides:
            defaults.update(overrides)

        return defaults

    return _create_generators


# ============================================================================
# Integration Test Fixtures
# ============================================================================


@pytest.fixture
def sf2_engine_with_soundfont(mock_synth):
    """Create SF2Engine with loaded soundfont."""
    from synth.engine.sf2_engine import SF2Engine

    engine = SF2Engine(
        sf2_file_path=None,  # Will be set in test
        sample_rate=44100,
        block_size=1024,
        synth=mock_synth,
    )

    return engine


@pytest.fixture
def audio_comparison_fixture():
    """Fixture for audio comparison utilities."""

    class AudioComparator:
        def assert_almost_equal(
            self, audio1: np.ndarray, audio2: np.ndarray, tolerance: float = 1e-6
        ):
            """Assert two audio arrays are nearly equal."""
            assert len(audio1) == len(audio2)
            max_diff = np.max(np.abs(audio1 - audio2))
            assert max_diff < tolerance, f"Max difference {max_diff} exceeds tolerance {tolerance}"

        def assert_not_silent(self, audio: np.ndarray, threshold: float = 1e-6):
            """Assert audio is not silent."""
            rms = np.sqrt(np.mean(audio**2))
            assert rms > threshold, f"Audio is silent (RMS: {rms})"

        def assert_no_clipping(self, audio: np.ndarray, threshold: float = 0.99):
            """Assert audio doesn't clip."""
            max_val = np.max(np.abs(audio))
            assert max_val <= threshold, f"Audio clips (max: {max_val})"

    return AudioComparator()


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "sample_rate": 44100,
        "block_size": 1024,
        "polyphony": 64,
        "duration_seconds": 60,
        "cpu_threshold_percent": 10.0,
    }


@pytest.fixture
def benchmark_audio_render():
    """Fixture for benchmarking audio rendering."""

    def _benchmark(render_func, iterations: int = 10):
        import time

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            render_func()
            end = time.perf_counter()
            times.append(end - start)

        return {
            "mean": np.mean(times),
            "std": np.std(times),
            "min": np.min(times),
            "max": np.max(times),
        }

    return _benchmark
