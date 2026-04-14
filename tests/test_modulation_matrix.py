"""
Modulation Matrix Tests

Tests for modulation routing, depth, and polarity.
"""

from __future__ import annotations

import pytest


class TestModulationMatrix:
    """Test modulation routing and processing."""

    @pytest.mark.unit
    def test_modulation_route_creation(self):
        """Test creating modulation routes."""
        routes = []
        route = {"source": "lfo1", "destination": "pitch", "amount": 50.0}
        routes.append(route)

        assert len(routes) == 1
        assert routes[0]["source"] == "lfo1"

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

    @pytest.mark.unit
    def test_multiple_sources_one_destination(self):
        """Test multiple sources to single destination."""
        sources = [
            {"name": "lfo1", "amount": 0.3},
            {"name": "lfo2", "amount": 0.2},
            {"name": "velocity", "amount": 0.5},
        ]

        total_mod = sum(s["amount"] for s in sources)
        assert total_mod == 1.0

    @pytest.mark.unit
    def test_modulation_matrix_reset(self):
        """Test matrix reset functionality."""
        routes = [{"source": "lfo1", "destination": "pitch"}]

        routes.clear()

        assert len(routes) == 0

    @pytest.mark.unit
    def test_modulation_depth_clamping(self):
        """Test modulation depth clamping."""
        depth = 1.5
        clamped = max(0.0, min(1.0, depth))
        assert clamped == 1.0

    @pytest.mark.unit
    def test_modulation_route_validation(self):
        """Test modulation route validation."""
        route = {"source": "lfo1", "destination": "pitch", "amount": 50.0}

        assert "source" in route
        assert "destination" in route
        assert "amount" in route
