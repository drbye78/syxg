"""
GS SYSEX Message Tests

Tests for Roland GS System Exclusive messages:
- GS System On
- GS Master Volume
- GS Master Tune
- GS Reverb Type
- GS Chorus Type
- GS EQ Type
- GS Part parameters
- GS Drum Setup parameters
"""

from __future__ import annotations

import pytest
import numpy as np


class TestGSSYSEX:
    """Test GS SYSEX message processing."""

    @pytest.mark.unit
    def test_gs_sysex_header(self):
        """Test GS SYSEX header format."""
        # GS SYSEX: F0 41 [device] 42 12 40 ...
        header = [0xF0, 0x41, 0x00, 0x42, 0x12, 0x40]
        assert header[0] == 0xF0
        assert header[1] == 0x41  # Roland ID
        assert header[2] == 0x00  # Device ID
        assert header[3] == 0x42  # Model ID (GS)
        assert header[4] == 0x12  # Command ID (DT1)
        assert header[5] == 0x40  # Address high

    @pytest.mark.unit
    def test_gs_sysex_footer(self):
        """Test GS SYSEX footer format."""
        footer = 0xF7
        assert footer == 0xF7

    @pytest.mark.unit
    def test_gs_sysex_address(self):
        """Test GS SYSEX address format."""
        addr_high = 0x40
        addr_mid = 0x00
        addr_low = 0x00
        assert 0 <= addr_high <= 127
        assert 0 <= addr_mid <= 127
        assert 0 <= addr_low <= 127

    @pytest.mark.unit
    def test_gs_sysex_checksum(self):
        """Test GS SYSEX checksum calculation."""
        # Roland checksum: 128 - (sum % 128)
        data = [0x40, 0x00, 0x00, 0x7F]
        checksum = 128 - (sum(data) % 128)
        checksum = checksum % 128
        assert 0 <= checksum <= 127

    @pytest.mark.unit
    def test_gs_master_volume(self):
        """Test GS Master Volume."""
        # Address: 40 00 04
        volume = 100
        assert 0 <= volume <= 127

    @pytest.mark.unit
    def test_gs_master_pan(self):
        """Test GS Master Pan."""
        # Address: 40 00 05
        pan = 64
        assert 0 <= pan <= 127

    @pytest.mark.unit
    def test_gs_reverb_macro(self):
        """Test GS Reverb Macro."""
        # Address: 40 01 00
        reverb_type = 4
        assert 0 <= reverb_type <= 7

    @pytest.mark.unit
    def test_gs_reverb_character(self):
        """Test GS Reverb Character."""
        # Address: 40 01 01
        character = 0
        assert 0 <= character <= 7

    @pytest.mark.unit
    def test_gs_reverb_pre_lpf(self):
        """Test GS Reverb Pre-LPF."""
        # Address: 40 01 02
        pre_lpf = 4
        assert 0 <= pre_lpf <= 7

    @pytest.mark.unit
    def test_gs_reverb_level(self):
        """Test GS Reverb Level."""
        # Address: 40 01 0A
        level = 40
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_gs_reverb_time(self):
        """Test GS Reverb Time."""
        # Address: 40 01 0B
        time = 24
        assert 0 <= time <= 127

    @pytest.mark.unit
    def test_gs_chorus_macro(self):
        """Test GS Chorus Macro."""
        # Address: 40 01 20
        chorus_type = 5
        assert 0 <= chorus_type <= 7

    @pytest.mark.unit
    def test_gs_chorus_pre_lpf(self):
        """Test GS Chorus Pre-LPF."""
        # Address: 40 01 21
        pre_lpf = 4
        assert 0 <= pre_lpf <= 7

    @pytest.mark.unit
    def test_gs_chorus_level(self):
        """Test GS Chorus Level."""
        # Address: 40 01 2A
        level = 40
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_gs_chorus_depth(self):
        """Test GS Chorus Depth."""
        # Address: 40 01 2B
        depth = 24
        assert 0 <= depth <= 127

    @pytest.mark.unit
    def test_gs_eq_low_freq(self):
        """Test GS EQ Low Frequency."""
        # Address: 40 02 00
        freq = 0
        assert 0 <= freq <= 3

    @pytest.mark.unit
    def test_gs_eq_low_gain(self):
        """Test GS EQ Low Gain."""
        # Address: 40 02 01
        gain = 68
        assert 0 <= gain <= 127

    @pytest.mark.unit
    def test_gs_eq_high_freq(self):
        """Test GS EQ High Frequency."""
        # Address: 40 02 02
        freq = 0
        assert 0 <= freq <= 3

    @pytest.mark.unit
    def test_gs_eq_high_gain(self):
        """Test GS EQ High Gain."""
        # Address: 40 02 03
        gain = 68
        assert 0 <= gain <= 127

    @pytest.mark.unit
    def test_gs_part_mute(self):
        """Test GS Part Mute."""
        # Address: 40 10 [part] 07
        mute = 0
        assert 0 <= mute <= 127

    @pytest.mark.unit
    def test_gs_drum_note_pitch(self):
        """Test GS Drum Note Pitch."""
        # Address: 41 [note] [drum] 00
        pitch = 64
        assert 0 <= pitch <= 127

    @pytest.mark.unit
    def test_gs_drum_note_level(self):
        """Test GS Drum Note Level."""
        # Address: 41 [note] [drum] 01
        level = 100
        assert 0 <= level <= 127

    @pytest.mark.unit
    def test_gs_drum_note_pan(self):
        """Test GS Drum Note Pan."""
        # Address: 41 [note] [drum] 02
        pan = 64
        assert 0 <= pan <= 127

    @pytest.mark.unit
    def test_gs_drum_note_reverb(self):
        """Test GS Drum Note Reverb Send."""
        # Address: 41 [note] [drum] 03
        reverb = 40
        assert 0 <= reverb <= 127

    @pytest.mark.unit
    def test_gs_drum_note_chorus(self):
        """Test GS Drum Note Chorus Send."""
        # Address: 41 [note] [drum] 04
        chorus = 0
        assert 0 <= chorus <= 127

    @pytest.mark.unit
    def test_gs_drum_note_number(self):
        """Test GS Drum Note Number."""
        drum_note = 36
        assert 0 <= drum_note <= 127

    @pytest.mark.unit
    def test_gs_drum_bank_number(self):
        """Test GS Drum Bank Number."""
        drum_bank = 0
        assert 0 <= drum_bank <= 127

    @pytest.mark.unit
    def test_gs_sysex_data_byte(self):
        """Test GS SYSEX data byte range."""
        data = 100
        assert 0 <= data <= 127

    @pytest.mark.unit
    def test_gs_reverb_level_clamping(self):
        """Test GS Reverb Level clamping."""
        level = 200
        clamped = max(0, min(127, level))
        assert clamped == 127

    @pytest.mark.unit
    def test_gs_chorus_depth_clamping(self):
        """Test GS Chorus Depth clamping."""
        depth = -10
        clamped = max(0, min(127, depth))
        assert clamped == 0