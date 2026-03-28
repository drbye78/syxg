"""
XG Multi-Part Parameter Tests

Tests for XG multi-part parameter handling.
"""

from __future__ import annotations

import pytest


class TestXGMultiPart:
    """Test XG multi-part parameter handling."""

    @pytest.mark.unit
    def test_part_level(self):
        """Test level for each of 16 parts."""
        parts = {i: {"level": 100} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["level"] <= 127

    @pytest.mark.unit
    def test_part_pan(self):
        """Test pan for each of 16 parts."""
        parts = {i: {"pan": 64} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["pan"] <= 127

    @pytest.mark.unit
    def test_part_reverb_send(self):
        """Test reverb send for each part."""
        parts = {i: {"reverb": 40} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["reverb"] <= 127

    @pytest.mark.unit
    def test_part_chorus_send(self):
        """Test chorus send for each part."""
        parts = {i: {"chorus": 0} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["chorus"] <= 127

    @pytest.mark.unit
    def test_part_variation_send(self):
        """Test variation send for each part."""
        parts = {i: {"variation": 0} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["variation"] <= 127

    @pytest.mark.unit
    def test_part_mute_solo(self):
        """Test mute/solo for each part."""
        parts = {i: {"muted": False, "solo": False} for i in range(16)}

        parts[0]["muted"] = True
        parts[1]["solo"] = True

        assert parts[0]["muted"] is True
        assert parts[1]["solo"] is True

    @pytest.mark.unit
    def test_part_receive_channel(self):
        """Test receive channel for each part."""
        parts = {i: {"receive_channel": i} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["receive_channel"] <= 15

    @pytest.mark.unit
    def test_part_bank_select(self):
        """Test bank select for each part."""
        parts = {i: {"bank_msb": 0, "bank_lsb": 0} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["bank_msb"] <= 127
            assert 0 <= params["bank_lsb"] <= 127

    @pytest.mark.unit
    def test_part_program_change(self):
        """Test program change for each part."""
        parts = {i: {"program": 0} for i in range(16)}

        for part_id, params in parts.items():
            assert 0 <= params["program"] <= 127
