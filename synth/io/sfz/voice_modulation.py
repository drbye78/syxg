"""
SFZ Voice-Level Modulation Matrix

Provides advanced modulation routing at the voice level for SFZ instruments,
enabling complex modulation chains and professional control over synthesis parameters.
"""

from __future__ import annotations

import math
from typing import Any


class ModulationRoute:
    """
    Represents a single modulation route in the modulation matrix.

    A route connects a modulation source to a destination parameter with
    configurable amount, polarity, and transformation curve.
    """

    def __init__(
        self,
        source: str,
        destination: str,
        amount: float = 1.0,
        polarity: float = 1.0,
        curve: str = "linear",
        min_val: float = 0.0,
        max_val: float = 1.0,
    ):
        """
        Initialize modulation route.

        Args:
            source: Modulation source name (e.g., 'velocity', 'lfo1', 'envelope1')
            destination: Destination parameter name (e.g., 'volume', 'cutoff', 'pan')
            amount: Modulation amount (0.0-1.0)
            polarity: Modulation polarity (-1.0 to 1.0, -1 inverts modulation)
            curve: Response curve ('linear', 'exponential', 'logarithmic', 'sine')
            min_val: Minimum output value
            max_val: Maximum output value
        """
        self.source = source
        self.destination = destination
        self.amount = amount
        self.polarity = polarity
        self.curve = curve
        self.min_val = min_val
        self.max_val = max_val
        self.enabled = True

        # Curve functions
        self._curve_functions = {
            "linear": lambda x: x,
            "exponential": lambda x: x**2 if x >= 0 else -(abs(x) ** 2),
            "logarithmic": lambda x: (
                math.log10(abs(x) * 9 + 1) * (1 if x >= 0 else -1) if x != 0 else 0
            ),
            "sine": lambda x: math.sin(x * math.pi / 2),
        }

    def process(self, source_value: float) -> float:
        """
        Process modulation source through this route.

        Args:
            source_value: Input modulation value (-1.0 to 1.0)

        Returns:
            Processed modulation value for destination
        """
        if not self.enabled:
            return 0.0

        # Apply polarity
        modulated = source_value * self.polarity

        # Apply curve
        if self.curve in self._curve_functions:
            curve_func = self._curve_functions[self.curve]
            modulated = curve_func(modulated)
        else:
            # Default to linear
            modulated = modulated

        # Apply amount
        modulated *= self.amount

        # Clamp to range
        modulated = max(self.min_val, min(self.max_val, modulated))

        return modulated

    def __str__(self) -> str:
        """String representation."""
        return f"Route({self.source} → {self.destination}, amount={self.amount:.2f})"

    def __repr__(self) -> str:
        return self.__str__()


class SFZVoiceModulationMatrix:
    """
    Voice-level modulation matrix for SFZ instruments.

    Provides sophisticated modulation routing with multiple sources,
    destinations, and complex modulation chains suitable for professional
    music production.
    """

    def __init__(self, max_routes: int = 32):
        """
        Initialize modulation matrix.

        Args:
            max_routes: Maximum number of simultaneous modulation routes
        """
        self.max_routes = max_routes
        self.routes: list[ModulationRoute] = []
        self.source_values: dict[str, float] = {}

        # Initialize common modulation sources
        self._initialize_default_sources()

        # Route groups for organization
        self.route_groups: dict[str, list[int]] = {}

    def _initialize_default_sources(self):
        """Initialize default modulation source values."""
        self.source_values = {
            # MIDI sources
            "velocity": 0.0,  # 0.0-1.0
            "key_number": 0.0,  # 0.0-1.0 (normalized note number)
            "aftertouch": 0.0,  # 0.0-1.0
            "pitch_bend": 0.0,  # -1.0 to 1.0
            "mod_wheel": 0.0,  # 0.0-1.0
            # Envelope sources
            "amp_envelope": 0.0,  # 0.0-1.0
            "filter_envelope": 0.0,  # 0.0-1.0
            # LFO sources
            "lfo1": 0.0,  # -1.0 to 1.0
            "lfo2": 0.0,  # -1.0 to 1.0
            # Controller sources
            "breath_controller": 0.0,  # 0.0-1.0
            "foot_controller": 0.0,  # 0.0-1.0
            "expression": 1.0,  # 0.0-1.0
            "sustain_pedal": 0.0,  # 0.0-1.0
            # Advanced sources
            "random": 0.0,  # -1.0 to 1.0 (sample & hold)
            "noise": 0.0,  # -1.0 to 1.0 (filtered noise)
            "audio_envelope": 0.0,  # 0.0-1.0 (from audio signal)
            "sidechain": 0.0,  # 0.0-1.0 (compressor sidechain)
        }

    def add_route(
        self,
        source: str,
        destination: str,
        amount: float = 1.0,
        polarity: float = 1.0,
        curve: str = "linear",
        min_val: float = 0.0,
        max_val: float = 1.0,
        group: str = None,
    ) -> bool:
        """
        Add a modulation route to the matrix.

        Args:
            source: Modulation source name
            destination: Destination parameter name
            amount: Modulation amount (0.0-1.0)
            polarity: Modulation polarity (-1.0 to 1.0)
            curve: Response curve type
            min_val: Minimum output value
            max_val: Maximum output value
            group: Route group name for organization

        Returns:
            True if route was added successfully
        """
        if len(self.routes) >= self.max_routes:
            return False

        # Create new route
        route = ModulationRoute(source, destination, amount, polarity, curve, min_val, max_val)
        self.routes.append(route)

        route_index = len(self.routes) - 1

        # Add to group if specified
        if group:
            if group not in self.route_groups:
                self.route_groups[group] = []
            self.route_groups[group].append(route_index)

        return True

    def remove_route(self, route_index: int) -> bool:
        """
        Remove a modulation route.

        Args:
            route_index: Index of route to remove

        Returns:
            True if route was removed
        """
        if 0 <= route_index < len(self.routes):
            # Remove from groups
            route = self.routes[route_index]
            for group_name, indices in self.route_groups.items():
                if route_index in indices:
                    indices.remove(route_index)
                    if not indices:
                        del self.route_groups[group_name]
                    break

            # Remove route
            del self.routes[route_index]
            return True

        return False

    def enable_route(self, route_index: int, enabled: bool = True) -> bool:
        """
        Enable or disable a modulation route.

        Args:
            route_index: Index of route to modify
            enabled: Whether to enable the route

        Returns:
            True if route was modified
        """
        if 0 <= route_index < len(self.routes):
            self.routes[route_index].enabled = enabled
            return True
        return False

    def clear_routes(self, group: str = None) -> int:
        """
        Clear modulation routes.

        Args:
            group: Optional group name to clear only that group

        Returns:
            Number of routes cleared
        """
        if group:
            if group in self.route_groups:
                indices_to_remove = sorted(self.route_groups[group], reverse=True)
                for index in indices_to_remove:
                    if index < len(self.routes):
                        del self.routes[index]
                del self.route_groups[group]
                return len(indices_to_remove)
            return 0
        else:
            # Clear all routes
            cleared = len(self.routes)
            self.routes.clear()
            self.route_groups.clear()
            return cleared

    def update_source(self, source_name: str, value: float) -> None:
        """
        Update a modulation source value.

        Args:
            source_name: Name of modulation source
            value: New source value
        """
        if source_name in self.source_values:
            self.source_values[source_name] = value

    def update_sources(self, source_updates: dict[str, float]) -> None:
        """
        Update multiple modulation source values.

        Args:
            source_updates: Dictionary of {source_name: value}
        """
        self.source_values.update(source_updates)

    def process(self) -> dict[str, float]:
        """
        Process the modulation matrix and return parameter updates.

        Returns:
            Dictionary of {parameter_name: modulation_value}
        """
        parameter_updates = {}

        # Process each route
        for route in self.routes:
            if route.enabled and route.source in self.source_values:
                source_value = self.source_values[route.source]
                modulation_value = route.process(source_value)

                # Accumulate modulation for this destination
                if route.destination not in parameter_updates:
                    parameter_updates[route.destination] = 0.0
                parameter_updates[route.destination] += modulation_value

        return parameter_updates

    def get_route_info(self, route_index: int) -> dict[str, Any] | None:
        """
        Get information about a specific route.

        Args:
            route_index: Index of route to query

        Returns:
            Route information dictionary or None if invalid index
        """
        if 0 <= route_index < len(self.routes):
            route = self.routes[route_index]
            return {
                "source": route.source,
                "destination": route.destination,
                "amount": route.amount,
                "polarity": route.polarity,
                "curve": route.curve,
                "min_val": route.min_val,
                "max_val": route.max_val,
                "enabled": route.enabled,
                "current_source_value": self.source_values.get(route.source, 0.0),
            }
        return None

    def get_all_routes(self) -> list[dict[str, Any]]:
        """
        Get information about all routes.

        Returns:
            List of route information dictionaries
        """
        return [self.get_route_info(i) for i in range(len(self.routes))]

    def get_group_routes(self, group_name: str) -> list[dict[str, Any]]:
        """
        Get all routes in a specific group.

        Args:
            group_name: Name of the route group

        Returns:
            List of route information dictionaries
        """
        if group_name not in self.route_groups:
            return []

        return [
            self.get_route_info(i) for i in self.route_groups[group_name] if i < len(self.routes)
        ]

    def get_source_value(self, source_name: str) -> float:
        """
        Get current value of a modulation source.

        Args:
            source_name: Name of modulation source

        Returns:
            Current source value
        """
        return self.source_values.get(source_name, 0.0)

    def get_all_source_values(self) -> dict[str, float]:
        """
        Get all modulation source values.

        Returns:
            Copy of source values dictionary
        """
        return self.source_values.copy()

    def get_matrix_info(self) -> dict[str, Any]:
        """
        Get comprehensive matrix information.

        Returns:
            Matrix status and configuration
        """
        return {
            "total_routes": len(self.routes),
            "max_routes": self.max_routes,
            "active_routes": sum(1 for r in self.routes if r.enabled),
            "groups": list(self.route_groups.keys()),
            "sources": list(self.source_values.keys()),
            "destinations": list(set(r.destination for r in self.routes)),
            "utilization_percent": (len(self.routes) / self.max_routes) * 100,
        }

    def create_preset(self, preset_name: str) -> dict[str, Any]:
        """
        Create a modulation matrix preset.

        Args:
            preset_name: Name of the preset to create

        Returns:
            Preset configuration dictionary
        """
        if preset_name == "basic_synth":
            return {
                "name": "Basic Synth Modulation",
                "description": "Standard synthesizer modulation setup",
                "routes": [
                    {
                        "source": "velocity",
                        "destination": "volume",
                        "amount": 0.3,
                        "curve": "linear",
                    },
                    {
                        "source": "velocity",
                        "destination": "filter_cutoff",
                        "amount": 0.5,
                        "curve": "exponential",
                    },
                    {
                        "source": "mod_wheel",
                        "destination": "lfo1_depth",
                        "amount": 1.0,
                        "curve": "linear",
                    },
                    {
                        "source": "lfo1",
                        "destination": "pitch",
                        "amount": 0.1,
                        "polarity": -1.0,
                        "curve": "sine",
                    },
                    {
                        "source": "filter_envelope",
                        "destination": "filter_cutoff",
                        "amount": 0.7,
                        "curve": "exponential",
                    },
                ],
            }
        elif preset_name == "advanced_lead":
            return {
                "name": "Advanced Lead Modulation",
                "description": "Complex modulation for lead sounds",
                "routes": [
                    {
                        "source": "velocity",
                        "destination": "volume",
                        "amount": 0.4,
                        "curve": "logarithmic",
                    },
                    {
                        "source": "velocity",
                        "destination": "filter_cutoff",
                        "amount": 0.8,
                        "curve": "exponential",
                    },
                    {
                        "source": "aftertouch",
                        "destination": "lfo2_depth",
                        "amount": 0.6,
                        "curve": "linear",
                    },
                    {
                        "source": "breath_controller",
                        "destination": "filter_resonance",
                        "amount": 0.5,
                        "curve": "linear",
                    },
                    {
                        "source": "lfo1",
                        "destination": "pitch",
                        "amount": 0.05,
                        "polarity": 1.0,
                        "curve": "sine",
                    },
                    {
                        "source": "lfo2",
                        "destination": "filter_cutoff",
                        "amount": 0.3,
                        "curve": "sine",
                    },
                    {
                        "source": "amp_envelope",
                        "destination": "pan",
                        "amount": 0.2,
                        "curve": "sine",
                    },
                    {"source": "random", "destination": "pan", "amount": 0.1, "curve": "linear"},
                ],
            }
        elif preset_name == "pad_sound":
            return {
                "name": "Pad Sound Modulation",
                "description": "Slow, evolving modulation for pad sounds",
                "routes": [
                    {
                        "source": "velocity",
                        "destination": "volume",
                        "amount": 0.2,
                        "curve": "linear",
                    },
                    {
                        "source": "lfo1",
                        "destination": "filter_cutoff",
                        "amount": 0.4,
                        "curve": "sine",
                    },
                    {"source": "lfo2", "destination": "pan", "amount": 0.3, "curve": "sine"},
                    {
                        "source": "expression",
                        "destination": "volume",
                        "amount": 0.5,
                        "curve": "linear",
                    },
                    {
                        "source": "filter_envelope",
                        "destination": "filter_cutoff",
                        "amount": 0.6,
                        "curve": "exponential",
                    },
                    {
                        "source": "audio_envelope",
                        "destination": "sidechain",
                        "amount": 0.8,
                        "curve": "logarithmic",
                    },
                ],
            }

        return {"name": "Unknown Preset", "routes": []}

    def load_preset(self, preset_config: dict[str, Any]) -> bool:
        """
        Load a modulation matrix preset.

        Args:
            preset_config: Preset configuration from create_preset()

        Returns:
            True if preset loaded successfully
        """
        try:
            routes = preset_config.get("routes", [])
            for route_config in routes:
                source = route_config["source"]
                destination = route_config["destination"]
                amount = route_config.get("amount", 1.0)
                polarity = route_config.get("polarity", 1.0)
                curve = route_config.get("curve", "linear")

                if not self.add_route(source, destination, amount, polarity, curve):
                    return False

            return True

        except (KeyError, TypeError):
            return False

    def export_matrix(self) -> dict[str, Any]:
        """
        Export modulation matrix configuration.

        Returns:
            Serializable matrix configuration
        """
        routes_data = []
        for route in self.routes:
            routes_data.append(
                {
                    "source": route.source,
                    "destination": route.destination,
                    "amount": route.amount,
                    "polarity": route.polarity,
                    "curve": route.curve,
                    "min_val": route.min_val,
                    "max_val": route.max_val,
                    "enabled": route.enabled,
                }
            )

        return {
            "routes": routes_data,
            "groups": self.route_groups.copy(),
            "source_values": self.source_values.copy(),
        }

    def import_matrix(self, data: dict[str, Any]) -> bool:
        """
        Import modulation matrix configuration.

        Args:
            data: Configuration data from export_matrix()

        Returns:
            True if import successful
        """
        try:
            # Clear current matrix
            self.clear_routes()

            # Import routes
            routes_data = data.get("routes", [])
            for route_data in routes_data:
                source = route_data["source"]
                destination = route_data["destination"]
                amount = route_data.get("amount", 1.0)
                polarity = route_data.get("polarity", 1.0)
                curve = route_data.get("curve", "linear")
                min_val = route_data.get("min_val", 0.0)
                max_val = route_data.get("max_val", 1.0)

                route = ModulationRoute(
                    source, destination, amount, polarity, curve, min_val, max_val
                )
                route.enabled = route_data.get("enabled", True)
                self.routes.append(route)

            # Import groups
            self.route_groups = data.get("groups", {}).copy()

            # Import source values
            self.source_values.update(data.get("source_values", {}))

            return True

        except (KeyError, TypeError):
            return False

    def __str__(self) -> str:
        """String representation."""
        info = self.get_matrix_info()
        return f"SFZVoiceModulationMatrix(routes={info['total_routes']}/{info['max_routes']}, groups={len(info['groups'])})"

    def __repr__(self) -> str:
        return self.__str__()
