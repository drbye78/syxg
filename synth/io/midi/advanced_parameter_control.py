"""
Advanced Parameter Control System for MIDI 2.0

Implements sophisticated parameter mapping, routing, and control mechanisms for MIDI 2.0.
Supports complex modulation matrices, parameter automation, and advanced control surfaces.
"""

from __future__ import annotations

import math
from enum import Enum


class ParameterResolution(Enum):
    """Parameter resolution types for MIDI 2.0"""

    MIDI_1_7_BIT = 7  # Standard MIDI 1.0 (7-bit)
    MIDI_1_14_BIT = 14  # MIDI 1.0 with LSB (14-bit)
    MIDI_2_32_BIT = 32  # MIDI 2.0 (32-bit)
    MIDI_2_64_BIT = 64  # MIDI 2.0 extended (64-bit)


class ParameterAutomationMode(Enum):
    """Automation modes for parameter control"""

    OFF = "off"  # No automation
    TOUCH = "touch"  # Touch recording
    LATCH = "latch"  # Latch recording
    WRITE = "write"  # Overdub recording
    PLAY = "play"  # Play automation data


class ParameterMapping:
    """Represents a mapping between a source and destination parameter"""

    def __init__(
        self,
        source: str,
        destination: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
        curve: str = "linear",
        sensitivity: float = 1.0,
    ):
        """
        Initialize parameter mapping.

        Args:
            source: Source parameter/controller name
            destination: Destination parameter name
            min_value: Minimum output value
            max_value: Maximum output value
            curve: Response curve ('linear', 'log', 'exp', 'sine', 'cosine')
            sensitivity: Sensitivity multiplier
        """
        self.source = source
        self.destination = destination
        self.min_value = min_value
        self.max_value = max_value
        self.curve = curve
        self.sensitivity = sensitivity
        self.enabled = True

    def apply_curve(self, value: float) -> float:
        """Apply response curve to the input value."""
        if not self.enabled:
            return 0.0

        # Normalize to 0-1 range
        norm_value = max(0.0, min(1.0, value))

        # Apply curve transformation
        if self.curve == "linear":
            result = norm_value
        elif self.curve == "log":
            result = math.log(norm_value * 9 + 1) / math.log(10) if norm_value > 0 else 0
        elif self.curve == "exp":
            result = (math.exp(norm_value) - 1) / (math.e - 1)
        elif self.curve == "sine":
            result = math.sin(norm_value * math.pi / 2)
        elif self.curve == "cosine":
            result = math.cos((1 - norm_value) * math.pi / 2)
        else:
            result = norm_value  # Default to linear

        # Apply sensitivity
        result *= self.sensitivity

        # Scale to output range
        output_range = self.max_value - self.min_value
        return self.min_value + result * output_range


class AdvancedParameterController:
    """
    Advanced Parameter Control System for MIDI 2.0

    Provides sophisticated parameter mapping, automation, and control routing
    for complex MIDI 2.0 applications.
    """

    def __init__(self):
        """Initialize the advanced parameter control system."""
        self.parameter_mappings: dict[str, list[ParameterMapping]] = {}
        self.parameter_values: dict[str, float] = {}
        self.automation_data: dict[str, list[tuple[float, float]]] = {}  # time -> value
        self.automation_mode = ParameterAutomationMode.OFF
        self.current_time = 0.0
        self.modulation_matrix: dict[str, dict[str, float]] = {}  # source -> dest -> amount
        self.learning_mode = False
        self.learned_mappings: list[ParameterMapping] = []

        # Initialize with default parameter values
        self._initialize_default_parameters()

    def _initialize_default_parameters(self):
        """Initialize default parameter values."""
        default_params = [
            "volume",
            "pan",
            "expression",
            "mod_wheel",
            "breath_controller",
            "foot_controller",
            "sustain",
            "portamento",
            "sostenuto",
            "soft_pedal",
            "harmonic_content",
            "brightness",
            "reverb_send",
            "chorus_send",
            "variation_send",
            "pitch_bend",
            "channel_pressure",
            "poly_pressure",
            "filter_cutoff",
            "filter_resonance",
            "attack_time",
            "decay_time",
            "sustain_level",
            "release_time",
            "tremolo_rate",
            "tremolo_depth",
            "vibrato_rate",
            "vibrato_depth",
            "vibrato_delay",
        ]

        for param in default_params:
            self.parameter_values[param] = 0.0 if param in ["pan", "pitch_bend"] else 1.0

    def add_parameter_mapping(
        self,
        source: str,
        destination: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
        curve: str = "linear",
        sensitivity: float = 1.0,
    ) -> str:
        """
        Add a parameter mapping from source to destination.

        Args:
            source: Source parameter/controller name
            destination: Destination parameter name
            min_value: Minimum output value
            max_value: Maximum output value
            curve: Response curve
            sensitivity: Sensitivity multiplier

        Returns:
            Unique ID for the mapping
        """
        mapping = ParameterMapping(source, destination, min_value, max_value, curve, sensitivity)

        if source not in self.parameter_mappings:
            self.parameter_mappings[source] = []

        # Create unique ID for this mapping
        mapping_id = f"{source}_to_{destination}_{len(self.parameter_mappings[source])}"
        self.parameter_mappings[source].append(mapping)

        return mapping_id

    def remove_parameter_mapping(self, source: str, mapping_index: int = 0) -> bool:
        """
        Remove a parameter mapping.

        Args:
            source: Source parameter name
            mapping_index: Index of mapping to remove (default: 0)

        Returns:
            True if mapping was removed
        """
        if source in self.parameter_mappings and 0 <= mapping_index < len(
            self.parameter_mappings[source]
        ):
            del self.parameter_mappings[source][mapping_index]
            return True
        return False

    def set_parameter_value(self, parameter: str, value: float, source: str | None = None):
        """
        Set a parameter value, triggering any mapped destinations.

        Args:
            parameter: Parameter name
            value: Parameter value
            source: Optional source that triggered this change
        """
        self.parameter_values[parameter] = value

        # If this parameter has mappings, process them
        if parameter in self.parameter_mappings:
            for mapping in self.parameter_mappings[parameter]:
                if mapping.enabled:
                    mapped_value = mapping.apply_curve(value)
                    self.parameter_values[mapping.destination] = mapped_value

        # Update modulation matrix if applicable
        self._update_modulation_matrix(parameter, value)

        # Record automation if in record mode
        if self.automation_mode in [
            ParameterAutomationMode.TOUCH,
            ParameterAutomationMode.LATCH,
            ParameterAutomationMode.WRITE,
        ]:
            self._record_automation(parameter, value)

    def get_parameter_value(self, parameter: str) -> float:
        """
        Get the current value of a parameter.

        Args:
            parameter: Parameter name

        Returns:
            Current parameter value
        """
        return self.parameter_values.get(parameter, 0.0)

    def _update_modulation_matrix(self, source_param: str, value: float):
        """
        Update the modulation matrix based on source parameter changes.

        Args:
            source_param: Source parameter name
            value: Source parameter value
        """
        if source_param in self.modulation_matrix:
            for dest_param, modulation_amount in self.modulation_matrix[source_param].items():
                if dest_param in self.parameter_values:
                    # Apply modulation to destination parameter
                    modulated_value = self.parameter_values[dest_param] + (
                        value * modulation_amount
                    )
                    # Clamp to reasonable range
                    modulated_value = max(-1.0, min(1.0, modulated_value))
                    self.parameter_values[dest_param] = modulated_value

    def add_modulation_route(self, source: str, destination: str, amount: float = 1.0):
        """
        Add a modulation route from source to destination.

        Args:
            source: Source parameter name
            destination: Destination parameter name
            amount: Modulation amount (-1.0 to 1.0)
        """
        if source not in self.modulation_matrix:
            self.modulation_matrix[source] = {}

        self.modulation_matrix[source][destination] = max(-1.0, min(1.0, amount))

    def remove_modulation_route(self, source: str, destination: str) -> bool:
        """
        Remove a modulation route.

        Args:
            source: Source parameter name
            destination: Destination parameter name

        Returns:
            True if route was removed
        """
        if source in self.modulation_matrix and destination in self.modulation_matrix[source]:
            del self.modulation_matrix[source][destination]

            # Clean up empty source entries
            if not self.modulation_matrix[source]:
                del self.modulation_matrix[source]

            return True
        return False

    def set_automation_mode(self, mode: ParameterAutomationMode):
        """
        Set the automation recording/playback mode.

        Args:
            mode: Automation mode
        """
        self.automation_mode = mode
        if mode == ParameterAutomationMode.OFF:
            # Clear temporary automation data when turning off
            pass

    def _record_automation(self, parameter: str, value: float):
        """
        Record automation data for the given parameter.

        Args:
            parameter: Parameter name
            value: Parameter value
        """
        if parameter not in self.automation_data:
            self.automation_data[parameter] = []

        # Add time-value pair
        self.automation_data[parameter].append((self.current_time, value))

    def play_automation_at_time(self, time: float):
        """
        Play back automation data at the specified time.

        Args:
            time: Time to play automation at
        """
        for param, automation_points in self.automation_data.items():
            if len(automation_points) >= 2:
                # Find the two points that bracket the current time
                prev_point = None
                next_point = None

                for i, (t, v) in enumerate(automation_points):
                    if t <= time:
                        prev_point = (t, v)
                    elif t > time and prev_point is not None:
                        next_point = (t, v)
                        break

                if prev_point and next_point:
                    # Interpolate between the two points
                    t1, v1 = prev_point
                    t2, v2 = next_point

                    if t2 != t1:  # Avoid division by zero
                        interpolation_factor = (time - t1) / (t2 - t1)
                        interpolated_value = v1 + (v2 - v1) * interpolation_factor
                        self.parameter_values[param] = interpolated_value
                elif prev_point:
                    # Use the last known value
                    self.parameter_values[param] = prev_point[1]

    def start_learning_mode(self):
        """Start parameter learning mode."""
        self.learning_mode = True
        self.learned_mappings.clear()

    def stop_learning_mode(self) -> list[ParameterMapping]:
        """
        Stop parameter learning mode and return learned mappings.

        Returns:
            List of learned parameter mappings
        """
        self.learning_mode = False
        learned = self.learned_mappings.copy()
        self.learned_mappings.clear()
        return learned

    def learn_parameter_mapping(self, source: str, destination: str) -> str:
        """
        Learn a parameter mapping (used in learning mode).

        Args:
            source: Source parameter
            destination: Destination parameter

        Returns:
            Mapping ID
        """
        if not self.learning_mode:
            raise RuntimeError("Learning mode not active")

        mapping = ParameterMapping(source, destination)
        self.learned_mappings.append(mapping)

        # Also add to active mappings
        mapping_id = self.add_parameter_mapping(source, destination)
        return mapping_id

    def get_all_parameters(self) -> dict[str, float]:
        """
        Get all current parameter values.

        Returns:
            Dictionary of all parameter names and values
        """
        return self.parameter_values.copy()

    def reset_all_parameters(self):
        """Reset all parameters to their default values."""
        self._initialize_default_parameters()

        # Clear automation data
        self.automation_data.clear()

    def get_modulation_matrix(self) -> dict[str, dict[str, float]]:
        """
        Get the current modulation matrix.

        Returns:
            Modulation matrix as dictionary
        """
        return {k: v.copy() for k, v in self.modulation_matrix.items()}

    def get_parameter_mappings(
        self, source: str | None = None
    ) -> dict[str, list[ParameterMapping]]:
        """
        Get parameter mappings, optionally filtered by source.

        Args:
            source: Optional source parameter to filter by

        Returns:
            Dictionary of parameter mappings
        """
        if source:
            return {source: self.parameter_mappings.get(source, [])}
        return {k: v.copy() for k, v in self.parameter_mappings.items()}

    def set_current_time(self, time: float):
        """
        Set the current time for automation playback.

        Args:
            time: Current time in seconds
        """
        self.current_time = time
        if self.automation_mode == ParameterAutomationMode.PLAY:
            self.play_automation_at_time(time)


# Global instance for shared access
advanced_parameter_controller = AdvancedParameterController()


def get_advanced_parameter_controller() -> AdvancedParameterController:
    """
    Get the global advanced parameter controller instance.

    Returns:
        AdvancedParameterController instance
    """
    return advanced_parameter_controller
