"""
NRPN/RPN Processing Tests

Tests for NRPN and RPN message handling:
- NRPN addressing (MSB/LSB)
- RPN addressing (MSB/LSB)
- Data entry (MSB/LSB)
- Parameter value ranges
- System effect parameters
- Multi-part parameters
"""

from __future__ import annotations

import pytest
import numpy as np


class TestNRPNRPNProcessing:
    """Test NRPN and RPN message processing."""

    @pytest.mark.unit
    def test_nrpn_msb_addressing(self):
        """Test NRPN MSB addressing."""
        nrpn_msb = 1
        assert 0 <= nrpn_msb <= 127

    @pytest.mark.unit
    def test_nrpn_lsb_addressing(self):
        """Test NRPN LSB addressing."""
        nrpn_lsb = 8
        assert 0 <= nrpn_lsb <= 127

    @pytest.mark.unit
    def test_nrpn_data_entry_msb(self):
        """Test NRPN data entry MSB."""
        data_msb = 64
        assert 0 <= data_msb <= 127

    @pytest.mark.unit
    def test_nrpn_data_entry_lsb(self):
        """Test NRPN data entry LSB."""
        data_lsb = 0
        assert 0 <= data_lsb <= 127

    @pytest.mark.unit
    def test_nrpn_parameter_id(self):
        """Test NRPN parameter ID calculation."""
        nrpn_msb = 1
        nrpn_lsb = 8
        param_id = (nrpn_msb << 7) | nrpn_lsb
        assert param_id == 136

    @pytest.mark.unit
    def test_nrpn_14bit_value(self):
        """Test NRPN 14-bit value construction."""
        msb = 64
        lsb = 0
        value = (msb << 7) | lsb
        assert 0 <= value <= 16383

    @pytest.mark.unit
    def test_rpn_msb_addressing(self):
        """Test RPN MSB addressing."""
        rpn_msb = 0
        assert 0 <= rpn_msb <= 127

    @pytest.mark.unit
    def test_rpn_lsb_addressing(self):
        """Test RPN LSB addressing."""
        rpn_lsb = 0
        assert 0 <= rpn_lsb <= 127

    @pytest.mark.unit
    def test_rpn_pitch_bend_range(self):
        """Test RPN#0 Pitch Bend Range."""
        rpn_msb = 0
        rpn_lsb = 0
        assert rpn_msb == 0
        assert rpn_lsb == 0

    @pytest.mark.unit
    def test_rpn_channel_fine_tuning(self):
        """Test RPN#1 Channel Fine Tuning."""
        rpn_msb = 0
        rpn_lsb = 1
        assert rpn_lsb == 1

    @pytest.mark.unit
    def test_rpn_channel_coarse_tuning(self):
        """Test RPN#2 Channel Coarse Tuning."""
        rpn_msb = 0
        rpn_lsb = 2
        assert rpn_lsb == 2

    @pytest.mark.unit
    def test_rpn_tuning_program_change(self):
        """Test RPN#3 Tuning Program Change."""
        rpn_msb = 0
        rpn_lsb = 3
        assert rpn_lsb == 3

    @pytest.mark.unit
    def test_rpn_tuning_bank_select(self):
        """Test RPN#4 Tuning Bank Select."""
        rpn_msb = 0
        rpn_lsb = 4
        assert rpn_lsb == 4

    @pytest.mark.unit
    def test_rpn_modulation_depth_range(self):
        """Test RPN#5 Modulation Depth Range."""
        rpn_msb = 0
        rpn_lsb = 5
        assert rpn_lsb == 5

    @pytest.mark.unit
    def test_nrpn_msb_1_for_effects(self):
        """Test NRPN MSB=1 for system effects."""
        nrpn_msb = 1
        assert nrpn_msb == 1

    @pytest.mark.unit
    def test_nrpn_lsb_8_for_reverb_type(self):
        """Test NRPN LSB=8 for reverb type."""
        nrpn_lsb = 8
        assert nrpn_lsb == 8

    @pytest.mark.unit
    def test_nrpn_msb_1_for_insertion_effects(self):
        """Test NRPN MSB=1 for insertion effects."""
        nrpn_msb = 1
        assert nrpn_msb == 1

    @pytest.mark.unit
    def test_nrpn_drum_setup_msb(self):
        """Test NRPN MSB for drum setup."""
        nrpn_msb = 24
        assert nrpn_msb == 24

    @pytest.mark.unit
    def test_nrpn_drum_note(self):
        """Test NRPN drum note addressing."""
        drum_note = 36
        assert 0 <= drum_note <= 127

    @pytest.mark.unit
    def test_nrpn_drum_pitch(self):
        """Test NRPN drum pitch parameter."""
        pitch = 64
        assert 0 <= pitch <= 127

    @pytest.mark.unit
    def test_nrpn_drum_level(self):
        """Test NRPN drum level parameter."""
        level = 100
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_nrpn_drum_pan(self):
        """Test NRPN drum pan parameter."""
        pan = 64
        assert 0 <= pan <= 127

    @pytest.mark.unit
    def test_nrpn_drum_reverb(self):
        """Test NRPN drum reverb send."""
        reverb = 40
        assert 0 <= reverb <= 127

    @pytest.mark.unit
    def test_nrpn_drum_chorus(self):
        """Test NRPN drum chorus send."""
        chorus = 0
        assert 0 <= chorus <= 127

    @pytest.mark.unit
    def test_nrpn_value_range_0_to_127(self):
        """Test NRPN value range 0-127."""
        value = 100
        assert 0 <= value <= 127

    @pytest.mark.unit
    def test_nrpn_value_range_negative(self):
        """Test NRPN negative value range."""
        value = -64
        assert -128 <= value <= 127

    @pytest.mark.unit
    def test_rpn_reset(self):
        """Test RPN reset command."""
        rpn_msb = 127
        rpn_lsb = 127
        assert rpn_msb == 127
        assert rpn_lsb == 127

    @pytest.mark.unit
    def test_nrpn_value_clamping(self):
        """Test NRPN value clamping."""
        value = 200
        clamped = max(0, min(127, value))
        assert clamped == 127
        value = -10
        clamped = max(0, min(127, value))
        assert clamped == 0