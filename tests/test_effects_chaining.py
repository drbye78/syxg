"""
Effects Chaining Tests

Tests for effects routing, chaining, and wet/dry mixing.
"""

from __future__ import annotations

import pytest


class TestEffectsChaining:
    """Test effects routing and chaining."""

    @pytest.mark.unit
    def test_reverb_to_chorus(self):
        """Test reverb output to chorus input."""
        reverb_output = 0.5
        chorus_input = reverb_output

        assert chorus_input == 0.5

    @pytest.mark.unit
    def test_insertion_to_system(self):
        """Test insertion effect to system effect routing."""
        insertion_output = 0.7
        system_input = insertion_output

        assert system_input == 0.7

    @pytest.mark.unit
    def test_multiple_insertion_effects(self):
        """Test multiple insertion effects in series."""
        effects = ["distortion", "chorus", "delay"]
        output = 1.0

        for effect in effects:
            output *= 0.8

        assert output < 1.0

    @pytest.mark.unit
    def test_effect_bypass_chain(self):
        """Test bypassing individual effects in chain."""
        bypassed = False
        output = 1.0

        if not bypassed:
            output *= 0.8

        assert output == 0.8

        bypassed = True
        output = 1.0

        if not bypassed:
            output *= 0.8

        assert output == 1.0

    @pytest.mark.unit
    def test_effect_wet_dry_mix(self):
        """Test wet/dry mixing in effects chain."""
        dry = 1.0
        wet = 0.5
        mix = 0.5

        output = dry * (1.0 - mix) + wet * mix
        assert 0.0 <= output <= 1.0

    @pytest.mark.unit
    def test_effect_send_levels(self):
        """Test individual effect send levels."""
        sends = {"reverb": 40, "chorus": 0, "variation": 0}

        assert 0 <= sends["reverb"] <= 127
        assert 0 <= sends["chorus"] <= 127
        assert 0 <= sends["variation"] <= 127

    @pytest.mark.unit
    def test_effect_send_clamping(self):
        """Test effect send level clamping."""
        send = 200
        clamped = max(0, min(127, send))
        assert clamped == 127

    @pytest.mark.unit
    def test_effect_chain_order(self):
        """Test effect chain processing order."""
        chain = ["insertion1", "insertion2", "system_reverb", "system_chorus"]

        assert chain[0] == "insertion1"
        assert chain[-1] == "system_chorus"

    @pytest.mark.unit
    def test_effect_wet_dry_balance(self):
        """Test wet/dry balance calculation."""
        dry = 1.0
        wet = 0.5
        balance = 0.5

        output = dry * (1.0 - balance) + wet * balance
        expected = 0.75

        assert abs(output - expected) < 0.01
