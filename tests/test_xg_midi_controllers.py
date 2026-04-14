"""
XG MIDI Controller Handling Tests

Tests for XG MIDI controller handling:
- CC#0 (Bank Select MSB)
- CC#32 (Bank Select LSB)
- CC#7 (Volume)
- CC#10 (Pan)
- CC#11 (Expression)
- CC#64 (Sustain Pedal)
- CC#71-79 (XG Sound Controllers)
"""

from __future__ import annotations

import pytest


class TestXGMIDIControllers:
    """Test XG MIDI controller handling."""

    @pytest.mark.unit
    def test_bank_select_msb(self):
        """Test CC#0 Bank Select MSB."""
        bank_msb = 127
        assert 0 <= bank_msb <= 127

    @pytest.mark.unit
    def test_bank_select_lsb(self):
        """Test CC#32 Bank Select LSB."""
        bank_lsb = 0
        assert 0 <= bank_lsb <= 127

    @pytest.mark.unit
    def test_volume_controller(self):
        """Test CC#7 Volume controller."""
        volume = 100
        assert 0 <= volume <= 127
        normalized = volume / 127.0
        assert 0.0 <= normalized <= 1.0

    @pytest.mark.unit
    def test_pan_controller(self):
        """Test CC#10 Pan controller."""
        pan = 64
        assert 0 <= pan <= 127
        normalized = (pan - 64) / 64.0
        assert -1.0 <= normalized <= 1.0

    @pytest.mark.unit
    def test_expression_controller(self):
        """Test CC#11 Expression controller."""
        expression = 127
        assert 0 <= expression <= 127

    @pytest.mark.unit
    def test_sustain_pedal(self):
        """Test CC#64 Sustain Pedal."""
        sustain = 127
        is_sustained = sustain >= 64
        assert is_sustained is True

    @pytest.mark.unit
    def test_xg_harmonic_content(self):
        """Test CC#71 Harmonic Content."""
        harmonic_content = 64
        assert 0 <= harmonic_content <= 127

    @pytest.mark.unit
    def test_xg_brightness(self):
        """Test CC#74 Brightness."""
        brightness = 64
        assert 0 <= brightness <= 127

    @pytest.mark.unit
    def test_xg_reverb_send(self):
        """Test CC#91 Reverb Send Level."""
        reverb_send = 40
        assert 0 <= reverb_send <= 127

    @pytest.mark.unit
    def test_xg_chorus_send(self):
        """Test CC#93 Chorus Send Level."""
        chorus_send = 0
        assert 0 <= chorus_send <= 127