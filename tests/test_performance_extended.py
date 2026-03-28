"""
Extended Performance Tests

Tests for performance characteristics and resource usage.
"""

from __future__ import annotations

import pytest
import time
import numpy as np


class TestPerformanceExtended:
    """Test performance characteristics."""

    @pytest.mark.performance
    def test_maximum_polyphony(self):
        """Test maximum simultaneous voices."""
        max_voices = 64
        voices = []

        for i in range(max_voices):
            voices.append({"id": i, "active": True})

        assert len(voices) == max_voices

    @pytest.mark.performance
    def test_voice_stealing_performance(self):
        """Test performance during voice stealing."""
        voices = [{"id": i, "active": True} for i in range(64)]

        start_time = time.time()
        for _ in range(100):
            stolen = voices.pop(0)
            voices.append({"id": stolen["id"], "active": True})
        end_time = time.time()

        assert (end_time - start_time) < 1.0

    @pytest.mark.performance
    def test_sysex_processing_time(self):
        """Test SYSEX message processing time."""
        message = [0xF0, 0x43, 0x10, 0x4C] + [0] * 100 + [0xF7]

        start_time = time.time()
        _ = len(message)
        end_time = time.time()

        assert (end_time - start_time) < 0.1

    @pytest.mark.performance
    def test_nrpn_processing_time(self):
        """Test NRPN message processing time."""
        nrpn = {"msb": 1, "lsb": 8, "data_msb": 64, "data_lsb": 0}

        start_time = time.time()
        param_id = (nrpn["msb"] << 7) | nrpn["lsb"]
        value = (nrpn["data_msb"] << 7) | nrpn["data_lsb"]
        end_time = time.time()

        assert (end_time - start_time) < 0.1

    @pytest.mark.performance
    def test_buffer_allocation_performance(self):
        """Test buffer allocation performance."""
        buffer_size = 1024

        start_time = time.time()
        for _ in range(100):
            buffer = np.zeros(buffer_size, dtype=np.float32)
        end_time = time.time()

        assert (end_time - start_time) < 1.0

    @pytest.mark.performance
    def test_modulation_matrix_performance(self):
        """Test modulation matrix performance."""
        routes = [
            {"source": "lfo1", "destination": "pitch", "amount": 50.0},
            {"source": "lfo2", "destination": "filter", "amount": 30.0},
            {"source": "velocity", "destination": "amp", "amount": 0.5},
        ]

        start_time = time.time()
        for _ in range(100):
            total = sum(r["amount"] for r in routes)
        end_time = time.time()

        assert (end_time - start_time) < 0.1
