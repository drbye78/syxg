"""
SFZ Advanced Controller Mapping System

Provides sophisticated MIDI controller mapping with custom curves,
ranges, and bipolar support for professional SFZ control.
"""

from __future__ import annotations

import math
from typing import Any


class ControllerCurve:
    """Controller response curve functions."""

    @staticmethod
    def linear(value: float) -> float:
        """Linear response curve."""
        return value

    @staticmethod
    def exponential(value: float, exponent: float = 2.0) -> float:
        """Exponential response curve."""
        return value**exponent

    @staticmethod
    def logarithmic(value: float) -> float:
        """Logarithmic response curve."""
        if value <= 0.0:
            return 0.0
        return math.log10(value * 9 + 1) / math.log10(10)

    @staticmethod
    def sine(value: float) -> float:
        """Sine-based smooth curve."""
        return (math.sin((value - 0.5) * math.pi) + 1.0) / 2.0

    @staticmethod
    def smoothstep(value: float) -> float:
        """Smooth step curve (S-curve)."""
        x = max(0.0, min(1.0, value))
        return x * x * (3.0 - 2.0 * x)


class SFZControllerMapper:
    """
    Advanced MIDI Controller Mapping for SFZ Engine

    Features:
    - Custom response curves (linear, exponential, logarithmic, etc.)
    - Configurable value ranges and bipolar support
    - MIDI learn functionality
    - Controller smoothing and hysteresis
    - Grouped controller management
    """

    def __init__(self):
        """Initialize the controller mapper."""
        self.controller_mappings: dict[int, dict[str, Any]] = {}
        self.controller_groups: dict[str, list[int]] = {}
        self.smoothing_filters: dict[int, float] = {}
        self.curve_functions = {
            "linear": ControllerCurve.linear,
            "exponential": lambda v: ControllerCurve.exponential(v, 2.0),
            "logarithmic": ControllerCurve.logarithmic,
            "sine": ControllerCurve.sine,
            "smoothstep": ControllerCurve.smoothstep,
        }

    def map_controller(
        self,
        cc_number: int,
        parameter: str,
        curve: str = "linear",
        min_val: float = 0.0,
        max_val: float = 1.0,
        bipolar: bool = False,
        smoothing: float = 0.0,
        group: str | None = None,
    ) -> bool:
        """
        Map a MIDI CC to an SFZ parameter with advanced options.

        Args:
            cc_number: MIDI controller number (0-127)
            parameter: SFZ parameter name to control
            curve: Response curve ('linear', 'exponential', 'logarithmic', 'sine', 'smoothstep')
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            bipolar: Whether to treat as bipolar control (-1.0 to 1.0)
            smoothing: Smoothing factor (0.0 = no smoothing, 1.0 = heavy smoothing)
            group: Controller group name for linked controls

        Returns:
            True if mapping was successful
        """
        if cc_number < 0 or cc_number > 127:
            return False

        if curve not in self.curve_functions:
            return False

        if min_val >= max_val:
            return False

        # Create mapping
        mapping = {
            "parameter": parameter,
            "curve": curve,
            "min_val": min_val,
            "max_val": max_val,
            "bipolar": bipolar,
            "smoothing": max(0.0, min(1.0, smoothing)),
            "group": group,
            "last_value": 0.0,  # For smoothing
            "current_value": 0.0,  # Smoothed output value
        }

        self.controller_mappings[cc_number] = mapping

        # Initialize smoothing filter
        if smoothing > 0.0:
            self.smoothing_filters[cc_number] = 0.0

        # Add to group if specified
        if group:
            if group not in self.controller_groups:
                self.controller_groups[group] = []
            if cc_number not in self.controller_groups[group]:
                self.controller_groups[group].append(cc_number)

        return True

    def unmap_controller(self, cc_number: int) -> bool:
        """
        Remove a controller mapping.

        Args:
            cc_number: MIDI controller number

        Returns:
            True if mapping was removed
        """
        if cc_number in self.controller_mappings:
            # Remove from group
            mapping = self.controller_mappings[cc_number]
            group = mapping.get("group")
            if group and group in self.controller_groups:
                if cc_number in self.controller_groups[group]:
                    self.controller_groups[group].remove(cc_number)
                    if not self.controller_groups[group]:
                        del self.controller_groups[group]

            # Remove mapping and smoothing filter
            del self.controller_mappings[cc_number]
            if cc_number in self.smoothing_filters:
                del self.smoothing_filters[cc_number]

            return True
        return False

    def process_controller(self, cc_number: int, value: int) -> dict[str, float]:
        """
        Process a MIDI controller value and return parameter updates.

        Args:
            cc_number: MIDI controller number
            value: Controller value (0-127)

        Returns:
            Dictionary of parameter updates {param_name: value}
        """
        if cc_number not in self.controller_mappings:
            return {}

        mapping = self.controller_mappings[cc_number]

        # Normalize MIDI value to 0.0-1.0
        normalized_value = value / 127.0

        # Apply response curve
        curve_func = self.curve_functions[mapping["curve"]]
        curved_value = curve_func(normalized_value)

        # Apply smoothing if enabled
        if mapping["smoothing"] > 0.0:
            last_value = self.smoothing_filters.get(cc_number, curved_value)
            smoothed_value = self._apply_smoothing(last_value, curved_value, mapping["smoothing"])
            self.smoothing_filters[cc_number] = smoothed_value
            curved_value = smoothed_value

        # Handle bipolar controls
        if mapping["bipolar"]:
            # Convert 0.0-1.0 to -1.0 to 1.0
            bipolar_value = (curved_value - 0.5) * 2.0
            # Scale to parameter range
            param_value = (
                mapping["min_val"]
                + (bipolar_value + 1.0) * (mapping["max_val"] - mapping["min_val"]) / 2.0
            )
        else:
            # Scale to parameter range
            param_value = mapping["min_val"] + curved_value * (
                mapping["max_val"] - mapping["min_val"]
            )

        # Clamp to range
        param_value = max(mapping["min_val"], min(mapping["max_val"], param_value))

        return {mapping["parameter"]: param_value}

    def process_controller_group(self, group_name: str, values: dict[int, int]) -> dict[str, float]:
        """
        Process multiple controllers in a group simultaneously.

        Args:
            group_name: Name of the controller group
            values: Dictionary of {cc_number: value} for all controllers in group

        Returns:
            Combined parameter updates from all controllers in group
        """
        if group_name not in self.controller_groups:
            return {}

        combined_updates = {}

        for cc_number in self.controller_groups[group_name]:
            if cc_number in values:
                updates = self.process_controller(cc_number, values[cc_number])
                combined_updates.update(updates)

        return combined_updates

    def _apply_smoothing(self, last_value: float, new_value: float, smoothing: float) -> float:
        """
        Apply exponential smoothing to controller values.

        Args:
            last_value: Previous smoothed value
            new_value: New raw value
            smoothing: Smoothing factor (0.0-1.0)

        Returns:
            Smoothed value
        """
        # Exponential smoothing: output = alpha * new + (1-alpha) * old
        # Higher smoothing value = more smoothing (less responsive)
        alpha = 1.0 - smoothing
        return alpha * new_value + (1.0 - alpha) * last_value

    def get_controller_mapping(self, cc_number: int) -> dict[str, Any] | None:
        """
        Get the mapping for a specific controller.

        Args:
            cc_number: MIDI controller number

        Returns:
            Mapping dictionary or None if not mapped
        """
        return self.controller_mappings.get(cc_number)

    def get_all_mappings(self) -> dict[int, dict[str, Any]]:
        """
        Get all controller mappings.

        Returns:
            Dictionary of all mappings {cc_number: mapping}
        """
        return self.controller_mappings.copy()

    def get_group_controllers(self, group_name: str) -> list[int]:
        """
        Get all controllers in a group.

        Args:
            group_name: Name of the controller group

        Returns:
            List of controller numbers in the group
        """
        return self.controller_groups.get(group_name, []).copy()

    def get_parameter_controllers(self, parameter: str) -> list[int]:
        """
        Get all controllers mapped to a specific parameter.

        Args:
            parameter: Parameter name

        Returns:
            List of controller numbers mapped to the parameter
        """
        controllers = []
        for cc_number, mapping in self.controller_mappings.items():
            if mapping["parameter"] == parameter:
                controllers.append(cc_number)
        return controllers

    def clear_all_mappings(self) -> None:
        """Clear all controller mappings and groups."""
        self.controller_mappings.clear()
        self.controller_groups.clear()
        self.smoothing_filters.clear()

    def create_factory_preset(self, preset_name: str) -> dict[str, Any]:
        """
        Create a factory preset mapping configuration.

        Args:
            preset_name: Name of the preset ('basic', 'advanced', 'performance')

        Returns:
            Preset configuration dictionary
        """
        if preset_name == "basic":
            return {
                "name": "Basic SFZ Controls",
                "mappings": [
                    {"cc": 7, "param": "volume", "curve": "linear", "min_val": 0.0, "max_val": 1.0},
                    {
                        "cc": 10,
                        "param": "pan",
                        "curve": "linear",
                        "min_val": -1.0,
                        "max_val": 1.0,
                        "bipolar": True,
                    },
                    {
                        "cc": 74,
                        "param": "cutoff",
                        "curve": "exponential",
                        "min_val": 20.0,
                        "max_val": 20000.0,
                    },
                    {
                        "cc": 71,
                        "param": "resonance",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 0.99,
                    },
                ],
            }
        elif preset_name == "advanced":
            return {
                "name": "Advanced SFZ Controls",
                "mappings": [
                    {"cc": 7, "param": "volume", "curve": "linear", "min_val": 0.0, "max_val": 1.0},
                    {
                        "cc": 10,
                        "param": "pan",
                        "curve": "linear",
                        "min_val": -1.0,
                        "max_val": 1.0,
                        "bipolar": True,
                    },
                    {
                        "cc": 74,
                        "param": "cutoff",
                        "curve": "exponential",
                        "min_val": 20.0,
                        "max_val": 20000.0,
                    },
                    {
                        "cc": 71,
                        "param": "resonance",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 0.99,
                    },
                    {
                        "cc": 1,
                        "param": "modulation",
                        "curve": "smoothstep",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                    {
                        "cc": 2,
                        "param": "breath_control",
                        "curve": "logarithmic",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                    {
                        "cc": 4,
                        "param": "foot_control",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                    {
                        "cc": 11,
                        "param": "expression",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                ],
            }
        elif preset_name == "performance":
            return {
                "name": "Performance SFZ Controls",
                "mappings": [
                    {
                        "cc": 7,
                        "param": "volume",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                        "smoothing": 0.2,
                    },
                    {
                        "cc": 10,
                        "param": "pan",
                        "curve": "sine",
                        "min_val": -1.0,
                        "max_val": 1.0,
                        "bipolar": True,
                        "smoothing": 0.1,
                    },
                    {
                        "cc": 74,
                        "param": "cutoff",
                        "curve": "exponential",
                        "min_val": 100.0,
                        "max_val": 10000.0,
                        "smoothing": 0.3,
                    },
                    {
                        "cc": 71,
                        "param": "resonance",
                        "curve": "smoothstep",
                        "min_val": 0.0,
                        "max_val": 0.8,
                        "smoothing": 0.2,
                    },
                    {
                        "cc": 1,
                        "param": "lfo_depth",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                    {
                        "cc": 2,
                        "param": "filter_envelope_depth",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 2.0,
                        "bipolar": True,
                    },
                    {
                        "cc": 4,
                        "param": "pitch_modulation",
                        "curve": "linear",
                        "min_val": -12.0,
                        "max_val": 12.0,
                        "bipolar": True,
                    },
                    {
                        "cc": 11,
                        "param": "amplitude",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 2.0,
                    },
                    {
                        "cc": 91,
                        "param": "reverb_send",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                    {
                        "cc": 93,
                        "param": "chorus_send",
                        "curve": "linear",
                        "min_val": 0.0,
                        "max_val": 1.0,
                    },
                ],
            }

        return {"name": "Unknown Preset", "mappings": []}

    def load_preset(self, preset_config: dict[str, Any]) -> bool:
        """
        Load a controller mapping preset.

        Args:
            preset_config: Preset configuration from create_factory_preset()

        Returns:
            True if preset was loaded successfully
        """
        try:
            mappings = preset_config.get("mappings", [])
            for mapping_config in mappings:
                cc = mapping_config["cc"]
                param = mapping_config["param"]
                curve = mapping_config.get("curve", "linear")
                min_val = mapping_config.get("min_val", 0.0)
                max_val = mapping_config.get("max_val", 1.0)
                bipolar = mapping_config.get("bipolar", False)
                smoothing = mapping_config.get("smoothing", 0.0)

                if not self.map_controller(cc, param, curve, min_val, max_val, bipolar, smoothing):
                    return False

            return True

        except (KeyError, TypeError):
            return False

    def export_mappings(self) -> dict[str, Any]:
        """
        Export all controller mappings for serialization.

        Returns:
            Serializable dictionary of all mappings and groups
        """
        return {
            "mappings": self.controller_mappings.copy(),
            "groups": self.controller_groups.copy(),
            "smoothing_filters": self.smoothing_filters.copy(),
        }

    def import_mappings(self, data: dict[str, Any]) -> bool:
        """
        Import controller mappings from serialized data.

        Args:
            data: Data from export_mappings()

        Returns:
            True if import was successful
        """
        try:
            self.controller_mappings = data.get("mappings", {}).copy()
            self.controller_groups = data.get("groups", {}).copy()
            self.smoothing_filters = data.get("smoothing_filters", {}).copy()
            return True
        except (KeyError, TypeError):
            return False

    def __str__(self) -> str:
        """String representation."""
        num_mappings = len(self.controller_mappings)
        num_groups = len(self.controller_groups)
        return f"SFZControllerMapper(mappings={num_mappings}, groups={num_groups})"

    def __repr__(self) -> str:
        return self.__str__()
