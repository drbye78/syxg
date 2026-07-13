"""Tests for OutputBusManager — multi-bus audio routing with per-bus pipeline support.

Tests cover:
- Bus creation with N buses (1–4+)
- Default names (Master, Group A, Group B, Group C)
- Per-part assignment and retrieval
- get_parts_for_bus
- Bus topology get/set
- Buffer allocation
- master_sum (accumulate bus outputs)
- reset_all_buses
- Edge cases (invalid part/bus, multiple reassignments)
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.processing.effects.output_bus_manager import OutputBus, OutputBusManager
from synth.processing.effects.pipeline_topology import PipelineTopology
from synth.processing.effects.effect_slot import EffectStageType


# ---------------------------------------------------------------------------
# OutputBus dataclass tests
# ---------------------------------------------------------------------------

class TestOutputBus:
    """OutputBus dataclass fields."""

    def test_default_construction(self):
        bus = OutputBus(bus_id=0)
        assert bus.bus_id == 0
        assert bus.name == ""
        assert bus.part_assignments == set()
        assert bus.output_buffer is None
        assert bus.topology.name == "XG_STANDARD"

    def test_custom_name(self):
        bus = OutputBus(bus_id=1, name="Custom")
        assert bus.name == "Custom"

    def test_custom_topology(self):
        topo = PipelineTopology.gs_standard()
        bus = OutputBus(bus_id=2, name="GS", topology=topo)
        assert bus.topology.name == "GS_STANDARD"


# ---------------------------------------------------------------------------
# OutputBusManager initialization
# ---------------------------------------------------------------------------

class TestInit:
    """Manager construction."""

    def test_default_1_bus(self):
        mgr = OutputBusManager()
        assert mgr.num_buses == 1
        assert len(mgr.buses) == 1
        assert 0 in mgr.buses

    def test_4_buses(self):
        mgr = OutputBusManager(num_buses=4)
        assert mgr.num_buses == 4
        assert len(mgr.buses) == 4
        for i in range(4):
            assert i in mgr.buses

    def test_minimum_1_bus(self):
        mgr = OutputBusManager(num_buses=0)
        assert mgr.num_buses == 1

    def test_negative_no_buses(self):
        mgr = OutputBusManager(num_buses=-5)
        assert mgr.num_buses == 1

    def test_default_num_parts(self):
        mgr = OutputBusManager()
        assert mgr.num_parts == 16

    def test_default_names(self):
        mgr = OutputBusManager(num_buses=4)
        assert mgr.buses[0].name == "Master"
        assert mgr.buses[1].name == "Group A"
        assert mgr.buses[2].name == "Group B"
        assert mgr.buses[3].name == "Group C"

    def test_fallback_names(self):
        mgr = OutputBusManager(num_buses=6)
        assert mgr.buses[4].name == "Bus 4"
        assert mgr.buses[5].name == "Bus 5"

    def test_default_all_parts_on_bus_0_in_map(self):
        """The internal part→bus mapping defaults all parts to bus 0."""
        mgr = OutputBusManager(num_parts=16)
        assert all(mgr._part_bus_map[p] == 0 for p in range(16))

    def test_lock_exists(self):
        mgr = OutputBusManager()
        assert hasattr(mgr, "lock")

    def test_bus_topology_default(self):
        mgr = OutputBusManager()
        assert mgr.buses[0].topology.name == "XG_STANDARD"


# ---------------------------------------------------------------------------
# assign_part_to_bus
# ---------------------------------------------------------------------------

class TestAssignPartToBus:
    """assign_part_to_bus method."""

    def test_assign_part_to_bus_1(self):
        mgr = OutputBusManager(num_buses=2)
        result = mgr.assign_part_to_bus(0, 1)
        assert result is True

    def test_part_on_new_bus(self):
        mgr = OutputBusManager(num_buses=3)
        mgr.assign_part_to_bus(0, 2)
        assert mgr.get_part_bus(0) == 2

    def test_reassign_to_same(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.assign_part_to_bus(0, 1)
        mgr.assign_part_to_bus(0, 1)
        assert mgr.get_part_bus(0) == 1

    def test_part_removed_from_old_bus(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.assign_part_to_bus(0, 1)
        mgr.assign_part_to_bus(0, 0)
        assert 0 not in mgr.buses[1].part_assignments

    def test_invalid_part_returns_false(self):
        mgr = OutputBusManager(num_parts=16)
        result = mgr.assign_part_to_bus(99, 0)
        assert result is False

    def test_invalid_bus_returns_false(self):
        mgr = OutputBusManager(num_buses=2)
        result = mgr.assign_part_to_bus(0, 99)
        assert result is False

    def test_negative_part_returns_false(self):
        mgr = OutputBusManager()
        result = mgr.assign_part_to_bus(-1, 0)
        assert result is False

    def test_assign_all_parts(self):
        mgr = OutputBusManager(num_buses=4, num_parts=16)
        for p in range(16):
            mgr.assign_part_to_bus(p, p % 4)
        for p in range(16):
            assert mgr.get_part_bus(p) == p % 4


class TestGetPartBus:
    """get_part_bus method."""

    def test_default_bus(self):
        mgr = OutputBusManager()
        assert mgr.get_part_bus(5) == 0

    def test_after_assignment(self):
        mgr = OutputBusManager(num_buses=3)
        mgr.assign_part_to_bus(2, 1)
        assert mgr.get_part_bus(2) == 1

    def test_out_of_range_returns_default(self):
        """Part out of range falls back to bus 0."""
        mgr = OutputBusManager(num_parts=16)
        assert mgr.get_part_bus(99) == 0


class TestGetPartsForBus:
    """get_parts_for_bus — returns sorted part_assignments from the bus."""

    def test_empty_bus(self):
        """A bus with no explicit assignments returns empty list."""
        mgr = OutputBusManager(num_buses=2)
        assert mgr.get_parts_for_bus(1) == []

    def test_bus_0_empty_before_assignments(self):
        """Bus 0 starts with no explicit part assignments in its set."""
        mgr = OutputBusManager(num_parts=16)
        assert mgr.get_parts_for_bus(0) == []  # part_assignments not populated by default

    def test_explicitly_assigned_parts_appear(self):
        """After assign_part_to_bus, part appears in bus assignments."""
        mgr = OutputBusManager(num_parts=4, num_buses=2)
        mgr.assign_part_to_bus(0, 1)
        mgr.assign_part_to_bus(1, 1)
        assert mgr.get_parts_for_bus(1) == [0, 1]

    def test_invalid_bus_returns_empty(self):
        mgr = OutputBusManager(num_buses=2)
        assert mgr.get_parts_for_bus(99) == []

    def test_returns_sorted(self):
        mgr = OutputBusManager(num_parts=8, num_buses=1)
        for p in [5, 3, 1, 7]:
            mgr.assign_part_to_bus(p, 0)
        assert mgr.get_parts_for_bus(0) == [1, 3, 5, 7]


# ---------------------------------------------------------------------------
# Bus topology
# ---------------------------------------------------------------------------

class TestBusTopology:
    """set_bus_topology / get_bus_topology methods."""

    def test_get_bus_topology_default(self):
        mgr = OutputBusManager()
        topo = mgr.get_bus_topology(0)
        assert topo.name == "XG_STANDARD"

    def test_get_invalid_bus(self):
        mgr = OutputBusManager()
        assert mgr.get_bus_topology(99) is None

    def test_set_bus_topology(self):
        mgr = OutputBusManager(num_buses=2)
        topo = PipelineTopology.sc8850()
        result = mgr.set_bus_topology(1, topo)
        assert result is True
        assert mgr.get_bus_topology(1).name == "SC8850"

    def test_set_bus_topology_invalid_bus(self):
        mgr = OutputBusManager()
        topo = PipelineTopology.gs_standard()
        result = mgr.set_bus_topology(99, topo)
        assert result is False

    def test_set_bus_topology_overwrites(self):
        mgr = OutputBusManager()
        topo1 = PipelineTopology.gs_standard()
        topo2 = PipelineTopology.sc8850()
        mgr.set_bus_topology(0, topo1)
        mgr.set_bus_topology(0, topo2)
        assert mgr.get_bus_topology(0).name == "SC8850"


# ---------------------------------------------------------------------------
# Buffer allocation
# ---------------------------------------------------------------------------

class TestAllocateBuffers:
    """allocate_buffers method."""

    def test_allocates_buffers(self):
        mgr = OutputBusManager(num_buses=3)
        mgr.allocate_buffers(block_size=512)
        for bus in mgr.buses.values():
            assert bus.output_buffer is not None
            assert bus.output_buffer.shape == (512, 2)
            assert bus.output_buffer.dtype == np.float32

    def test_buffers_are_zeroed(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.allocate_buffers(256)
        for bus in mgr.buses.values():
            assert np.all(bus.output_buffer == 0.0)

    def test_get_bus_output(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.allocate_buffers(128)
        buf = mgr.get_bus_output(1)
        assert buf is not None
        assert buf.shape == (128, 2)

    def test_get_bus_output_invalid(self):
        mgr = OutputBusManager()
        assert mgr.get_bus_output(99) is None

    def test_get_bus_output_before_alloc(self):
        mgr = OutputBusManager()
        assert mgr.get_bus_output(0) is None


# ---------------------------------------------------------------------------
# master_sum
# ---------------------------------------------------------------------------

class TestMasterSum:
    """master_sum method."""

    def test_sum_single_bus(self):
        mgr = OutputBusManager(num_buses=1)
        mgr.allocate_buffers(256)
        mgr.buses[0].output_buffer[:] = 0.5
        output = np.ones((256, 2), dtype=np.float32) * 0.1
        mgr.master_sum(256, output)
        assert np.allclose(output, 0.5)

    def test_sum_two_buses(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.allocate_buffers(256)
        mgr.buses[0].output_buffer[:] = 0.3
        mgr.buses[1].output_buffer[:] = 0.2
        output = np.zeros((256, 2), dtype=np.float32)
        mgr.master_sum(256, output)
        assert np.allclose(output, 0.5)

    def test_sum_zeroes_output_before_accum(self):
        """master_sum zeroes output then accumulates."""
        mgr = OutputBusManager(num_buses=1)
        mgr.allocate_buffers(256)
        mgr.buses[0].output_buffer[:] = 0.7
        output = np.ones((256, 2), dtype=np.float32) * 99.0
        mgr.master_sum(256, output)
        assert np.allclose(output, 0.7)

    def test_sum_partial_samples(self):
        mgr = OutputBusManager(num_buses=1)
        mgr.allocate_buffers(64)
        mgr.buses[0].output_buffer[:] = 1.0
        output = np.zeros((64, 2), dtype=np.float32)
        mgr.master_sum(32, output)
        assert np.allclose(output[:32], 1.0)
        assert np.allclose(output[32:], 0.0)

    def test_sum_no_buffers_no_error(self):
        """If no buffers allocated, master_sum still zeros output."""
        mgr = OutputBusManager(num_buses=2)
        output = np.ones((256, 2), dtype=np.float32)
        mgr.master_sum(256, output)
        assert np.allclose(output, 0.0)

    def test_sum_four_buses(self):
        mgr = OutputBusManager(num_buses=4)
        mgr.allocate_buffers(128)
        for i in range(4):
            mgr.buses[i].output_buffer[:] = float(i + 1) * 0.1
        output = np.zeros((128, 2), dtype=np.float32)
        mgr.master_sum(128, output)
        assert np.allclose(output, 1.0)


# ---------------------------------------------------------------------------
# reset_all_buses
# ---------------------------------------------------------------------------

class TestResetAllBuses:
    """reset_all_buses method."""

    def test_reset_zeros_buffers(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.allocate_buffers(256)
        mgr.buses[0].output_buffer[:] = 0.5
        mgr.buses[1].output_buffer[:] = 0.3
        mgr.reset_all_buses()
        for bus in mgr.buses.values():
            assert np.all(bus.output_buffer == 0.0)

    def test_reset_no_buffers_no_error(self):
        mgr = OutputBusManager(num_buses=2)
        mgr.reset_all_buses()


# ---------------------------------------------------------------------------
# Integration / combined scenarios
# ---------------------------------------------------------------------------

class TestIntegration:
    """Multi-step scenarios."""

    def test_assign_allocate_sum(self):
        """Full workflow: assign parts → allocate → sum."""
        mgr = OutputBusManager(num_buses=2, num_parts=16)
        for p in range(16):
            mgr.assign_part_to_bus(p, 0 if p < 8 else 1)
        mgr.allocate_buffers(128)

        mgr.buses[0].output_buffer[:] = 0.4
        mgr.buses[1].output_buffer[:] = 0.6

        output = np.zeros((128, 2), dtype=np.float32)
        mgr.master_sum(128, output)
        assert np.allclose(output, 1.0)

    def test_different_topologies_per_bus(self):
        """Each bus can have its own topology."""
        mgr = OutputBusManager(num_buses=3)
        mgr.set_bus_topology(0, PipelineTopology.xg_standard())
        mgr.set_bus_topology(1, PipelineTopology.gs_standard())
        mgr.set_bus_topology(2, PipelineTopology.sc8850())
        assert mgr.get_bus_topology(0).name == "XG_STANDARD"
        assert mgr.get_bus_topology(1).name == "GS_STANDARD"
        assert mgr.get_bus_topology(2).name == "SC8850"

    def test_assigned_parts_across_buses(self):
        """Parts are tracked per-bus after explicit assignment."""
        mgr = OutputBusManager(num_buses=3, num_parts=8)
        mgr.assign_part_to_bus(0, 1)
        mgr.assign_part_to_bus(2, 1)
        mgr.assign_part_to_bus(4, 2)
        assert mgr.get_parts_for_bus(1) == [0, 2]
        assert mgr.get_parts_for_bus(2) == [4]
        # Parts not explicitly assigned still have _part_bus_map entry of 0,
        # but bus 0's part_assignments set is only populated by assign_part_to_bus calls.
        # So bus 0 will only contain parts that were ever assigned to it via the API.
        # Since we only assigned to bus 1 and 2, bus 0's set is empty.
        assert mgr.get_parts_for_bus(0) == []

    def test_bus_assignments_after_full_assignment(self):
        """After explicitly assigning all parts, each bus has correct set."""
        mgr = OutputBusManager(num_buses=3, num_parts=8)
        for p in range(8):
            mgr.assign_part_to_bus(p, p % 3)
        assert mgr.get_parts_for_bus(0) == [0, 3, 6]
        assert mgr.get_parts_for_bus(1) == [1, 4, 7]
        assert mgr.get_parts_for_bus(2) == [2, 5]

    def test_allocated_buffers_independent(self):
        """Each bus has its own independent buffer."""
        mgr = OutputBusManager(num_buses=3)
        mgr.allocate_buffers(64)
        for i in range(3):
            mgr.buses[i].output_buffer[:, :] = i
        output = np.zeros((64, 2), dtype=np.float32)
        mgr.master_sum(64, output)
        assert np.allclose(output, 0 + 1 + 2)
