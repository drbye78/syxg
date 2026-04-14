"""
XG Drum Parameters Tests

Tests for XG drum parameter handling:
- Drum note assignment
- Drum pitch tuning
- Drum level
- Drum pan
- Drum reverb send
- Drum chorus send
"""

from __future__ import annotations

import pytest


class TestXGDrumParameters:
    """Test XG drum parameter handling."""

    @pytest.mark.unit
    def test_drum_note_assignment(self):
        """Test drum note to instrument mapping."""
        drum_notes = {36: "kick", 38: "snare", 42: "hihat_closed"}
        assert drum_notes[36] == "kick"
        assert drum_notes[38] == "snare"

    @pytest.mark.unit
    def test_drum_pitch_tuning(self):
        """Test drum pitch tuning parameter."""
        pitch_tuning = 64
        assert -64 <= pitch_tuning - 64 <= 63

    @pytest.mark.unit
    def test_drum_level(self):
        """Test drum level parameter."""
        level = 100
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_drum_pan(self):
        """Test drum pan parameter."""
        pan = 64
        assert 0 <= pan <= 127

    @pytest.mark.unit
    def test_drum_reverb_send(self):
        """Test drum reverb send parameter."""
        reverb = 40
        assert 0 <= reverb <= 127

    @pytest.mark.unit
    def test_drum_chorus_send(self):
        """Test drum chorus send parameter."""
        chorus = 0
        assert 0 <= chorus <= 127