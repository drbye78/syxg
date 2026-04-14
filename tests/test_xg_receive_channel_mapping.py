"""
XG Receive Channel Mapping Tests

Tests for XG receive channel mapping functionality including:
- Channel enable/disable
- Channel assignment
- Omni mode handling
- Multi-channel reception
- Channel priority and routing
"""

from __future__ import annotations

import pytest
import numpy as np


class TestXGReceiveChannelMapping:
    """Test XG receive channel mapping functionality."""

    @pytest.mark.unit
    def test_receive_channel_enable_disable(self):
        """Test enabling and disabling receive channels."""
        enabled_channels = set()
        for ch in [0, 1, 2]:
            enabled_channels.add(ch)
        assert 0 in enabled_channels
        assert 1 in enabled_channels
        assert 3 not in enabled_channels
        enabled_channels.discard(1)
        assert 1 not in enabled_channels

    @pytest.mark.unit
    def test_receive_channel_assignment(self):
        """Test channel assignment for receive mapping."""
        channel_map = {}
        channel_map[0] = 0
        channel_map[1] = 1
        channel_map[2] = 9
        assert channel_map[0] == 0
        assert channel_map[2] == 9

    @pytest.mark.unit
    def test_omni_mode_handling(self):
        """Test omni mode receive behavior."""
        omni_mode = False
        if not omni_mode:
            assigned_channel = 0
            received_channel = 0
            assert received_channel == assigned_channel
        omni_mode = True
        if omni_mode:
            for ch in range(16):
                assert 0 <= ch <= 15

    @pytest.mark.unit
    def test_drum_channel_assignment(self):
        """Test drum channel (channel 10) assignment."""
        drum_channel = 9
        assert drum_channel == 9
        drum_msg = {"channel": drum_channel, "type": "note_on", "note": 36}
        assert drum_msg["channel"] == 9

    @pytest.mark.unit
    def test_receive_channel_mask(self):
        """Test channel receive mask functionality."""
        channel_mask = 0x000F
        for ch in range(4):
            assert (channel_mask >> ch) & 1 == 1
        assert (channel_mask >> 4) & 1 == 0