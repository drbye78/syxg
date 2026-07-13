"""OutputBusManager — multi-bus audio routing with per-bus pipeline support."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from .pipeline_topology import PipelineTopology
from .effect_slot import EffectStageType

if TYPE_CHECKING:
    from .effects_coordinator import XGEffectsCoordinator

logger = logging.getLogger(__name__)


@dataclass
class OutputBus:
    """A single output bus with its own pipeline and buffer references.

    Attributes:
        bus_id: Bus index (0 = master, 1-3 = group A/B/C)
        name: Human-readable name (e.g., "Master", "Group A")
        topology: Effect pipeline for this bus
        part_assignments: Set of part numbers assigned to this bus
    """

    bus_id: int
    name: str = ""
    topology: PipelineTopology = field(default_factory=PipelineTopology.xg_standard)
    part_assignments: set[int] = field(default_factory=set)
    output_buffer: np.ndarray | None = None  # Pre-allocated stereo buffer


class OutputBusManager:
    """Manager for multiple audio output buses.

    Supports N stereo output buses (default 1 master, up to 4 for A/B/C/D).
    Each bus has:
    - Its own PipelineTopology (can be different effect chains per group)
    - Per-part assignment (which parts route to which bus)
    - Pre-allocated output buffer

    Part → Bus Routing:
    - By default, all parts route to bus 0 (master)
    - Assign part N to bus M via assign_part_to_bus(part_num, bus_id)
    - Query a part's bus via get_part_bus(part_num)
    """

    def __init__(self, num_buses: int = 1, num_parts: int = 16):
        self.num_buses = max(1, num_buses)
        self.num_parts = num_parts
        self.lock = threading.RLock()

        # Default names
        bus_names = ["Master", "Group A", "Group B", "Group C"]

        # Initialize buses
        self.buses: dict[int, OutputBus] = {}
        for i in range(self.num_buses):
            name = bus_names[i] if i < len(bus_names) else f"Bus {i}"
            self.buses[i] = OutputBus(bus_id=i, name=name)

        # Default: all parts on bus 0
        self._part_bus_map: dict[int, int] = {p: 0 for p in range(self.num_parts)}

    def assign_part_to_bus(self, part_num: int, bus_id: int) -> bool:
        """Assign a part to an output bus.

        Args:
            part_num: Part number (0 to num_parts-1)
            bus_id: Bus ID (0 to num_buses-1)

        Returns:
            True if assignment was successful
        """
        if not (0 <= part_num < self.num_parts):
            return False
        if bus_id not in self.buses:
            return False

        with self.lock:
            # Remove from old bus
            old_bus = self._part_bus_map.get(part_num)
            if old_bus is not None and old_bus in self.buses:
                self.buses[old_bus].part_assignments.discard(part_num)

            # Add to new bus
            self._part_bus_map[part_num] = bus_id
            self.buses[bus_id].part_assignments.add(part_num)

        return True

    def get_part_bus(self, part_num: int) -> int:
        """Get the bus ID for a part."""
        return self._part_bus_map.get(part_num, 0)

    def get_bus_topology(self, bus_id: int) -> PipelineTopology | None:
        """Get the pipeline topology for a bus."""
        bus = self.buses.get(bus_id)
        if bus is None:
            return None
        return bus.topology

    def set_bus_topology(self, bus_id: int, topology: PipelineTopology) -> bool:
        """Set the pipeline topology for a bus."""
        bus = self.buses.get(bus_id)
        if bus is None:
            return False
        with self.lock:
            bus.topology = topology
        return True

    def get_parts_for_bus(self, bus_id: int) -> list[int]:
        """Get all parts assigned to a specific bus."""
        bus = self.buses.get(bus_id)
        if bus is None:
            return []
        return sorted(bus.part_assignments)

    def allocate_buffers(self, block_size: int) -> None:
        """Pre-allocate output buffers for all buses."""
        for bus in self.buses.values():
            bus.output_buffer = np.zeros((block_size, 2), dtype=np.float32)

    def get_bus_output(self, bus_id: int) -> np.ndarray | None:
        """Get the output buffer for a bus."""
        bus = self.buses.get(bus_id)
        if bus is None:
            return None
        return bus.output_buffer

    def master_sum(self, num_samples: int, output_stereo: np.ndarray) -> None:
        """Sum all bus outputs into the master output buffer.

        Args:
            num_samples: Number of samples to sum
            output_stereo: Master output buffer (written to)
        """
        output_stereo[:num_samples].fill(0.0)
        for bus in self.buses.values():
            if bus.output_buffer is not None:
                for s in range(num_samples):
                    output_stereo[s, 0] += bus.output_buffer[s, 0]
                    output_stereo[s, 1] += bus.output_buffer[s, 1]

    def reset_all_buses(self) -> None:
        """Reset all bus output buffers to zero."""
        for bus in self.buses.values():
            if bus.output_buffer is not None:
                bus.output_buffer.fill(0.0)
