"""
Pytest fixtures for vibexg tests
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_preset_dir(temp_dir):
    """Create a temporary directory for preset tests."""
    preset_dir = temp_dir / "presets"
    preset_dir.mkdir()
    return preset_dir


@pytest.fixture
def mock_synthesizer():
    """Create a mock synthesizer for testing."""

    class MockSynth:
        def __init__(self):
            self.sample_rate = 44100
            self.buffer_size = 512

        def note_on(self, channel, note, velocity):
            pass

        def note_off(self, channel, note):
            pass

        def control_change(self, channel, controller, value):
            pass

        def program_change(self, channel, program):
            pass

    return MockSynth()
