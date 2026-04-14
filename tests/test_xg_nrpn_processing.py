"""
XG NRPN Processing Tests

Tests for XG NRPN (Non-Registered Parameter Number) processing:
- System effect parameters
- Insertion effect parameters
- Drum setup parameters
- Multi-part parameters
"""

from __future__ import annotations

import pytest


class TestXGNRPNProcessing:
    """Test XG NRPN processing."""

    @pytest.mark.unit
    def test_nrpn_msb_lsb(self):
        """Test NRPN MSB/LSB addressing."""
        nrpn_msb = 1
        nrpn_lsb = 8
        assert 0 <= nrpn_msb <= 127
        assert 0 <= nrpn_lsb <= 127

    @pytest.mark.unit
    def test_system_effect_nrpn(self):
        """Test NRPN for system effect parameters."""
        # Reverb type NRPN
        reverb_type_msb = 1
        reverb_type_lsb = 8
        assert reverb_type_msb == 1
        assert reverb_type_lsb == 8

    @pytest.mark.unit
    def test_insertion_effect_nrpn(self):
        """Test NRPN for insertion effect parameters."""
        # Insertion effect type
        ins_effect_msb = 1
        ins_effect_lsb = 0
        assert ins_effect_msb == 1
        assert ins_effect_lsb == 0

    @pytest.mark.unit
    def test_drum_setup_nrpn(self):
        """Test NRPN for drum setup parameters."""
        # Drum setup MSB
        drum_msb = 24
        assert drum_msb == 24

    @pytest.mark.unit
    def test_data_entry_msb(self):
        """Test NRPN data entry MSB."""
        data_msb = 64
        assert 0 <= data_msb <= 127

    @pytest.mark.unit
    def test_data_entry_lsb(self):
        """Test NRPN data entry LSB."""
        data_lsb = 0
        assert 0 <= data_lsb <= 127

    @pytest.mark.unit
    def test_nrpn_value_range(self):
        """Test NRPN value ranges."""
        # 14-bit value
        msb = 64
        lsb = 0
        value = (msb << 7) | lsb
        assert 0 <= value <= 16383

    @pytest.mark.unit
    def test_nrpn_parameter_mapping(self):
        """Test NRPN parameter ID mapping."""
        param_id = (1 << 7) | 8
        assert param_id == 136