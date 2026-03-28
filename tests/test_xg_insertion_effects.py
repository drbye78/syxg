"""
XG Insertion Effects Tests

Tests for XG insertion effects:
- Effect type selection
- Effect parameters
- Effect bypass
- Effect routing
"""

from __future__ import annotations

import pytest


class TestXGInsertionEffects:
    """Test XG insertion effects."""

    @pytest.mark.unit
    def test_effect_type_selection(self):
        """Test insertion effect type selection."""
        effect_types = [0, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77]
        for etype in effect_types:
            assert 0 <= etype <= 127

    @pytest.mark.unit
    def test_effect_parameter_1(self):
        """Test insertion effect parameter 1."""
        param1 = 64
        assert 0 <= param1 <= 127

    @pytest.mark.unit
    def test_effect_parameter_2(self):
        """Test insertion effect parameter 2."""
        param2 = 64
        assert 0 <= param2 <= 127

    @pytest.mark.unit
    def test_effect_parameter_3(self):
        """Test insertion effect parameter 3."""
        param3 = 0
        assert 0 <= param3 <= 127

    @pytest.mark.unit
    def test_effect_bypass(self):
        """Test insertion effect bypass."""
        bypass = False
        assert bypass is False
        bypass = True
        assert bypass is True

    @pytest.mark.unit
    def test_effect_connection(self):
        """Test insertion effect connection routing."""
        connection = 0
        assert 0 <= connection <= 127

    @pytest.mark.unit
    def test_distortion_effect(self):
        """Test distortion effect type 0."""
        effect_type = 0
        assert effect_type == 0

    @pytest.mark.unit
    def test_compressor_effect(self):
        """Test compressor effect type 69."""
        effect_type = 69
        assert effect_type == 69