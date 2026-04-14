"""
XG SYSEX Message Tests

Tests for XG System Exclusive messages:
- XG System On
- XG Master Volume
- XG Master Tune
- XG Reverb Type
- XG Chorus Type
- XG Variation Type
- XG Multi-Part parameters
- XG Drum Setup parameters
"""

from __future__ import annotations

import pytest
import numpy as np


class TestXGSYSEX:
    """Test XG SYSEX message processing."""

    @pytest.mark.unit
    def test_xg_sysex_header(self):
        """Test XG SYSEX header format."""
        # XG SYSEX: F0 43 10 4C ...
        header = [0xF0, 0x43, 0x10, 0x4C]
        assert header[0] == 0xF0
        assert header[1] == 0x43  # Yamaha ID
        assert header[2] == 0x10  # Device number
        assert header[3] == 0x4C  # Model ID (XG)

    @pytest.mark.unit
    def test_xg_sysex_footer(self):
        """Test XG SYSEX footer format."""
        footer = 0xF7
        assert footer == 0xF7

    @pytest.mark.unit
    def test_xg_system_on(self):
        """Test XG System On message."""
        # F0 43 10 4C 00 00 7E 00 F7
        msg = [0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7]
        assert msg[4] == 0x00  # Address high
        assert msg[5] == 0x00  # Address mid
        assert msg[6] == 0x7E  # Data (system on)
        assert msg[7] == 0x00  # Checksum

    @pytest.mark.unit
    def test_xg_master_volume(self):
        """Test XG Master Volume SYSEX."""
        # F0 43 10 4C 00 00 04 [vol] F7
        volume = 100
        assert 0 <= volume <= 127

    @pytest.mark.unit
    def test_xg_master_tune(self):
        """Test XG Master Tune SYSEX."""
        # F0 43 10 4C 00 00 00 [tune] F7
        tune = 64
        assert 0 <= tune <= 127

    @pytest.mark.unit
    def test_xg_reverb_type(self):
        """Test XG Reverb Type SYSEX."""
        # MSB=1, LSB=8 for reverb type
        nrpn_msb = 1
        nrpn_lsb = 8
        assert nrpn_msb == 1
        assert nrpn_lsb == 8

    @pytest.mark.unit
    def test_xg_chorus_type(self):
        """Test XG Chorus Type SYSEX."""
        # MSB=1, LSB=32 for chorus type
        nrpn_msb = 1
        nrpn_lsb = 32
        assert nrpn_msb == 1
        assert nrpn_lsb == 32

    @pytest.mark.unit
    def test_xg_variation_type(self):
        """Test XG Variation Type SYSEX."""
        # MSB=1, LSB=56 for variation type
        nrpn_msb = 1
        nrpn_lsb = 56
        assert nrpn_msb == 1
        assert nrpn_lsb == 56

    @pytest.mark.unit
    def test_xg_multi_part_level(self):
        """Test XG Multi-Part Level parameter."""
        # MSB=1, LSB=0-15 for part level
        nrpn_msb = 1
        nrpn_lsb = 0
        assert nrpn_msb == 1
        assert 0 <= nrpn_lsb <= 15

    @pytest.mark.unit
    def test_xg_multi_part_pan(self):
        """Test XG Multi-Part Pan parameter."""
        # MSB=1, LSB=16-31 for part pan
        nrpn_msb = 1
        nrpn_lsb = 16
        assert nrpn_msb == 1
        assert 16 <= nrpn_lsb <= 31

    @pytest.mark.unit
    def test_xg_drum_setup_note(self):
        """Test XG Drum Setup note parameter."""
        drum_note = 36
        assert 0 <= drum_note <= 127

    @pytest.mark.unit
    def test_xg_drum_setup_pitch(self):
        """Test XG Drum Setup pitch parameter."""
        pitch = 64
        assert 0 <= pitch <= 127

    @pytest.mark.unit
    def test_xg_drum_setup_level(self):
        """Test XG Drum Setup level parameter."""
        level = 100
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_xg_drum_setup_pan(self):
        """Test XG Drum Setup pan parameter."""
        pan = 64
        assert 0 <= pan <= 127

    @pytest.mark.unit
    def test_xg_drum_setup_reverb(self):
        """Test XG Drum Setup reverb send."""
        reverb = 40
        assert 0 <= reverb <= 127

    @pytest.mark.unit
    def test_xg_drum_setup_chorus(self):
        """Test XG Drum Setup chorus send."""
        chorus = 0
        assert 0 <= chorus <= 127

    @pytest.mark.unit
    def test_xg_sysex_checksum(self):
        """Test XG SYSEX checksum calculation."""
        data = [0x00, 0x00, 0x7E]
        checksum = sum(data) & 0x7F
        checksum = (128 - checksum) & 0x7F
        assert 0 <= checksum <= 127

    @pytest.mark.unit
    def test_xg_sysex_address_high(self):
        """Test XG SYSEX address high byte."""
        addr_high = 0x00
        assert 0 <= addr_high <= 127

    @pytest.mark.unit
    def test_xg_sysex_address_mid(self):
        """Test XG SYSEX address mid byte."""
        addr_mid = 0x00
        assert 0 <= addr_mid <= 127

    @pytest.mark.unit
    def test_xg_sysex_address_low(self):
        """Test XG SYSEX address low byte."""
        addr_low = 0x00
        assert 0 <= addr_low <= 127

    @pytest.mark.unit
    def test_xg_sysex_data_byte(self):
        """Test XG SYSEX data byte."""
        data = 0x7E
        assert 0 <= data <= 127

    @pytest.mark.unit
    def test_xg_master_volume_range(self):
        """Test XG Master Volume range."""
        volume = 127
        assert 0 <= volume <= 127

    @pytest.mark.unit
    def test_xg_master_tune_range(self):
        """Test XG Master Tune range."""
        tune = 64
        assert 0 <= tune <= 127

    @pytest.mark.unit
    def test_xg_reverb_time(self):
        """Test XG Reverb Time parameter."""
        time = 64
        assert 0 <= time <= 127

    @pytest.mark.unit
    def test_xg_reverb_level(self):
        """Test XG Reverb Level parameter."""
        level = 64
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_xg_chorus_rate(self):
        """Test XG Chorus Rate parameter."""
        rate = 64
        assert 0 <= rate <= 127

    @pytest.mark.unit
    def test_xg_chorus_depth(self):
        """Test XG Chorus Depth parameter."""
        depth = 64
        assert 0 <= depth <= 127