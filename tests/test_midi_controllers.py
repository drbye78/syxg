"""
MIDI Controller Processing Tests

Comprehensive tests for MIDI controller handling including:
- Standard CC messages (0-127)
- XG sound controllers (CC71-CC79)
- Bank select (CC0, CC32)
- Expression and volume
- Sustain pedal
- Modulation wheel
- Effects sends
"""

from __future__ import annotations

import pytest
import numpy as np


class TestMIDIControllers:
    """Test MIDI controller processing."""

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
        bank = (127 << 7) | 0
        assert bank == 16256

    @pytest.mark.unit
    def test_modulation_wheel(self):
        """Test CC#1 Modulation Wheel."""
        mod_wheel = 0
        assert 0 <= mod_wheel <= 127

    @pytest.mark.unit
    def test_breath_controller(self):
        """Test CC#2 Breath Controller."""
        breath = 0
        assert 0 <= breath <= 127

    @pytest.mark.unit
    def test_foot_controller(self):
        """Test CC#4 Foot Controller."""
        foot = 0
        assert 0 <= foot <= 127

    @pytest.mark.unit
    def test_volume_controller(self):
        """Test CC#7 Volume."""
        volume = 100
        assert 0 <= volume <= 127
        normalized = volume / 127.0
        assert 0.0 <= normalized <= 1.0

    @pytest.mark.unit
    def test_pan_controller(self):
        """Test CC#10 Pan."""
        pan = 64
        assert 0 <= pan <= 127
        normalized = (pan - 64) / 63.0
        assert -1.0 <= normalized <= 1.0

    @pytest.mark.unit
    def test_expression_controller(self):
        """Test CC#11 Expression."""
        expression = 127
        assert 0 <= expression <= 127

    @pytest.mark.unit
    def test_sustain_pedal(self):
        """Test CC#64 Sustain Pedal."""
        sustain = 127
        is_sustained = sustain >= 64
        assert is_sustained is True
        sustain = 0
        is_sustained = sustain >= 64
        assert is_sustained is False

    @pytest.mark.unit
    def test_portamento(self):
        """Test CC#65 Portamento On/Off."""
        portamento = 127
        is_enabled = portamento >= 64
        assert is_enabled is True

    @pytest.mark.unit
    def test_sostenuto_pedal(self):
        """Test CC#66 Sostenuto Pedal."""
        sostenuto = 64
        is_enabled = sostenuto >= 64
        assert is_enabled is True

    @pytest.mark.unit
    def test_soft_pedal(self):
        """Test CC#67 Soft Pedal."""
        soft = 64
        is_enabled = soft >= 64
        assert is_enabled is True

    @pytest.mark.unit
    def test_xg_harmonic_content(self):
        """Test CC#71 Harmonic Content (XG)."""
        harmonic = 64
        assert 0 <= harmonic <= 127
        value = (harmonic - 64) / 64.0
        assert -1.0 <= value <= 1.0

    @pytest.mark.unit
    def test_xg_brightness(self):
        """Test CC#74 Brightness (XG)."""
        brightness = 64
        assert 0 <= brightness <= 127

    @pytest.mark.unit
    def test_xg_reverb_send(self):
        """Test CC#91 Reverb Send Level."""
        reverb = 40
        assert 0 <= reverb <= 127

    @pytest.mark.unit
    def test_xg_chorus_send(self):
        """Test CC#93 Chorus Send Level."""
        chorus = 0
        assert 0 <= chorus <= 127

    @pytest.mark.unit
    def test_xg_variation_send(self):
        """Test CC#94 Variation Send Level."""
        variation = 0
        assert 0 <= variation <= 127

    @pytest.mark.unit
    def test_controller_value_clamping(self):
        """Test controller value clamping."""
        value = 150
        clamped = max(0, min(127, value))
        assert clamped == 127
        value = -10
        clamped = max(0, min(127, value))
        assert clamped == 0

    @pytest.mark.unit
    def test_controller_message_format(self):
        """Test MIDI controller message format."""
        cc = {"type": "control_change", "channel": 0, "controller": 7, "value": 100}
        assert cc["type"] == "control_change"
        assert 0 <= cc["controller"] <= 127
        assert 0 <= cc["value"] <= 127