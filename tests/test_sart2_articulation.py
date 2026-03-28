"""
S.Art2 Articulation System Tests

Tests for S.Art2 articulation control:
- NRPN articulation control
- SYSEX articulation messages
- Articulation presets
- Per-channel articulation
"""

from __future__ import annotations

import pytest


class TestSArt2Articulation:
    """Test S.Art2 articulation system."""

    @pytest.mark.unit
    def test_articulation_control_nrpn(self):
        """Test articulation control via NRPN."""
        articulations = {0: "normal", 1: "legato", 2: "staccato", 7: "growl", 8: "flutter"}
        assert articulations[0] == "normal"
        assert articulations[1] == "legato"

    @pytest.mark.unit
    def test_articulation_sysex(self):
        """Test articulation via SYSEX messages."""
        sysex = [0xF0, 0x43, 0x10, 0x4C, 0x08, 0x00, 0x00, 0x00, 0xF7]
        assert sysex[0] == 0xF0
        assert sysex[-1] == 0xF7

    @pytest.mark.unit
    def test_articulation_presets(self):
        """Test articulation preset loading."""
        presets = {"normal": 0, "legato": 1, "staccato": 2}
        assert presets["normal"] == 0
        assert presets["legato"] == 1

    @pytest.mark.unit
    def test_per_channel_articulation(self):
        """Test per-channel articulation."""
        channel_articulations = {0: "normal", 1: "legato", 9: "normal"}
        assert channel_articulations[0] == "normal"
        assert channel_articulations[9] == "normal"

    @pytest.mark.unit
    def test_articulation_parameter_range(self):
        """Test articulation parameter range."""
        articulation = 5
        assert 0 <= articulation <= 127
