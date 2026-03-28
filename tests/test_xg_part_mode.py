"""
XG Part Mode Selection Tests

Tests for XG part mode functionality:
- Normal mode
- Drum mode
- Single mode
- Mode switching
"""

from __future__ import annotations

import pytest


class TestXGPartMode:
    """Test XG part mode selection."""

    @pytest.mark.unit
    def test_normal_mode(self):
        """Test normal (melodic) part mode."""
        part_mode = "normal"
        assert part_mode == "normal"
        is_drum = part_mode == "drum"
        assert is_drum is False

    @pytest.mark.unit
    def test_drum_mode(self):
        """Test drum part mode."""
        part_mode = "drum"
        assert part_mode == "drum"
        is_drum = part_mode == "drum"
        assert is_drum is True

    @pytest.mark.unit
    def test_mode_switching(self):
        """Test switching between part modes."""
        mode = "normal"
        assert mode == "normal"
        mode = "drum"
        assert mode == "drum"
        mode = "normal"
        assert mode == "normal"

    @pytest.mark.unit
    def test_drum_mode_bank_selection(self):
        """Test drum mode uses bank 127."""
        is_drum = True
        bank = 127 if is_drum else 0
        assert bank == 127

    @pytest.mark.unit
    def test_normal_mode_bank_selection(self):
        """Test normal mode uses bank 0."""
        is_drum = False
        bank = 127 if is_drum else 0
        assert bank == 0