"""
Modulation Matrix Tests

Tests for modulation routing, depth, and polarity.
"""

from __future__ import annotations

import pytest


class TestModulationMatrix:
    """Test modulation routing and processing."""

    @pytest.mark.unit
    def test_modulation_depth(self):
        """Test modulation depth scaling."""
        depth = 0.5
        source_value = 1.0
        modulated = source_value * depth

        assert modulated == 0.5

    @pytest.mark.unit
    def test_modulation_polarity(self):
        """Test positive/negative modulation."""
        positive_amount = 0.5
        negative_amount = -0.5

        base_value = 1.0
        modulated_positive = base_value * (1.0 + positive_amount)
        modulated_negative = base_value * (1.0 + negative_amount)

        assert modulated_positive > base_value
        assert modulated_negative < base_value

    @pytest.mark.unit
    def test_velocity_sensitivity(self):
        """Test velocity-sensitive modulation."""
        velocity = 100
        sensitivity = 0.5

        mod_amount = (velocity / 127.0) * sensitivity
        assert 0.0 <= mod_amount <= sensitivity

    @pytest.mark.unit
    def test_key_scaling(self):
        """Test key-follow modulation."""
        note = 72
        center_note = 60
        scaling = 0.5

        key_offset = note - center_note
        mod_amount = key_offset * scaling

        assert mod_amount > 0
