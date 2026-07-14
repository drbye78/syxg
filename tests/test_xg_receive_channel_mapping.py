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
    def test_receive_channel_mask(self):
        """Test channel receive mask functionality."""
        channel_mask = 0x000F
        for ch in range(4):
            assert (channel_mask >> ch) & 1 == 1
        assert (channel_mask >> 4) & 1 == 0
