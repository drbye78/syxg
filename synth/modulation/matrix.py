"""
Modulation matrix for XG synthesizer.
Manages modulation routing and processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from .routes import ModulationRoute


class ModulationMatrix:
    """XG modulation matrix with support for up to 16 routes"""
    def __init__(self, num_routes=16):
        self.routes = [None] * num_routes
        self.num_routes = num_routes
        # Pre-allocate modulation values dict to avoid allocation on every process call
        self.modulation_values = {}

    def set_route(self, index, source, destination, amount=0.0, polarity=1.0,
                  velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Setting modulation route

        Args:
            index: route index (0-15)
            source: modulation source
            destination: modulation destination
            amount: modulation depth
            polarity: polarity (1.0 or -1.0)
            velocity_sensitivity: velocity sensitivity
            key_scaling: note height dependency
        """
        if 0 <= index < self.num_routes:
            self.routes[index] = ModulationRoute(  # type: ignore
                source, destination, amount, polarity,
                velocity_sensitivity, key_scaling
            )

    def clear_route(self, index):
        """Clearing modulation route"""
        if 0 <= index < self.num_routes:
            self.routes[index] = None

    def process(self, sources, velocity, note):
        """
        Processing modulation matrix (zero-allocation)

        Args:
            sources: dictionary with current source values
            velocity: key press velocity (0-127)
            note: MIDI note (0-127)

        Returns:
            dictionary with modulating values for destinations
        """
        # Clear pre-allocated dict instead of creating new one (zero-allocation)
        modulation_values = self.modulation_values
        modulation_values.clear()

        for route in self.routes:
            if route is None:
                continue

            if route.source in sources:
                source_value = sources[route.source]
                mod_value = route.get_modulation_value(source_value, velocity, note)

                if route.destination not in modulation_values:
                    modulation_values[route.destination] = 0.0
                modulation_values[route.destination] += mod_value

        return modulation_values
