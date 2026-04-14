"""
S90/S70 Control Surface Mapping

Authentic control surface mapping for S90/S70 synthesizers,
including assignable knobs, buttons, and parameter assignment.
"""

from __future__ import annotations

import threading
from typing import Any


class ControlAssignment:
    """Represents a control surface assignment"""

    def __init__(
        self,
        control_id: int,
        parameter_path: str,
        min_value: float = 0.0,
        max_value: float = 127.0,
        curve: str = "linear",
        name: str = "",
    ):
        """
        Initialize control assignment.

        Args:
            control_id: Control identifier
            parameter_path: Parameter path (e.g., 'filter.cutoff')
            min_value: Minimum parameter value
            max_value: Maximum parameter value
            curve: Response curve ('linear', 'log', 'exp')
            name: Display name
        """
        self.control_id = control_id
        self.parameter_path = parameter_path
        self.min_value = min_value
        self.max_value = max_value
        self.curve = curve
        self.name = name or f"Control {control_id}"

    def apply_value(self, midi_value: int) -> float:
        """
        Convert MIDI value to parameter value.

        Args:
            midi_value: MIDI control value (0-127)

        Returns:
            Parameter value
        """
        # Normalize MIDI value to 0.0-1.0
        normalized = midi_value / 127.0

        # Apply curve
        if self.curve == "log":
            # Logarithmic curve (good for frequency parameters)
            if normalized < 0.01:
                normalized = 0.01  # Avoid log(0)
            normalized = math.log10(normalized * 99 + 1) / 2.0
        elif self.curve == "exp":
            # Exponential curve (good for resonance)
            normalized = normalized**2

        # Scale to parameter range
        return self.min_value + normalized * (self.max_value - self.min_value)


class ControlGroup:
    """Represents a group of related controls"""

    def __init__(self, group_id: int, name: str, controls: list[ControlAssignment]):
        """
        Initialize control group.

        Args:
            group_id: Group identifier
            name: Group name
            controls: List of control assignments
        """
        self.group_id = group_id
        self.name = name
        self.controls = controls
        self.active = True

    def get_control(self, control_id: int) -> ControlAssignment | None:
        """Get control assignment by ID"""
        for control in self.controls:
            if control.control_id == control_id:
                return control
        return None

    def set_active(self, active: bool):
        """Set group active/inactive"""
        self.active = active


class S90S70ControlSurfaceMapping:
    """
    S90/S70 Control Surface Mapping Manager

    Provides authentic control surface mapping for S90/S70 synthesizers,
    including assignable knobs, buttons, and parameter assignment.
    """

    def __init__(self):
        """Initialize control surface mapping"""
        self.assignments: dict[int, ControlAssignment] = {}
        self.groups: dict[int, ControlGroup] = {}

        # Control surface layout
        self.control_layout = {
            "knobs": list(range(1, 5)),  # Assignable knobs 1-4
            "buttons": list(range(81, 85)),  # Assignable buttons A-D
            "data_entry": 6,  # Data entry slider
            "mod_wheel": 1,  # Mod wheel
            "pitch_bend": "pitch_bend",  # Pitch bend wheel
            "foot_pedal": 4,  # Foot pedal (CC4)
            "foot_switch": 64,  # Foot switch (CC64)
        }

        # Default assignments
        self._init_default_assignments()

        # Thread safety
        self.lock = threading.RLock()

    def _init_default_assignments(self):
        """Initialize default control assignments"""

        # Default knob assignments (S90/S70 style)
        default_knobs = [
            ControlAssignment(1, "filter.cutoff", 0, 127, "linear", "Cutoff"),
            ControlAssignment(2, "filter.resonance", 0, 127, "exp", "Resonance"),
            ControlAssignment(3, "amplitude.attack", 0, 127, "log", "Attack"),
            ControlAssignment(4, "amplitude.decay", 0, 127, "log", "Decay"),
        ]

        # Create default group
        default_group = ControlGroup(0, "Default", default_knobs)
        self.groups[0] = default_group

        # Assign controls to default group
        for knob in default_knobs:
            self.assignments[knob.control_id] = knob

        # Performance controls (always available)
        self.performance_assignments = {
            self.control_layout["mod_wheel"]: ControlAssignment(
                self.control_layout["mod_wheel"], "modulation.depth", 0, 127, "linear", "Mod Wheel"
            ),
            self.control_layout["foot_pedal"]: ControlAssignment(
                self.control_layout["foot_pedal"],
                "volume.expression",
                0,
                127,
                "linear",
                "Expression",
            ),
            self.control_layout["data_entry"]: ControlAssignment(
                self.control_layout["data_entry"], "data_entry", 0, 127, "linear", "Data Entry"
            ),
        }

    def assign_control(
        self,
        control_id: int,
        parameter_path: str,
        min_value: float = 0.0,
        max_value: float = 127.0,
        curve: str = "linear",
        name: str = "",
    ) -> bool:
        """
        Assign a parameter to a control.

        Args:
            control_id: Control identifier
            parameter_path: Parameter path
            min_value: Minimum parameter value
            max_value: Maximum parameter value
            curve: Response curve
            name: Display name

        Returns:
            True if assignment successful
        """
        with self.lock:
            if control_id not in self._get_available_controls():
                return False

            assignment = ControlAssignment(
                control_id, parameter_path, min_value, max_value, curve, name
            )

            self.assignments[control_id] = assignment

            # Update group if control belongs to one
            for group in self.groups.values():
                if group.active:
                    existing_control = group.get_control(control_id)
                    if existing_control:
                        # Replace in group
                        group.controls = [
                            assignment if ctrl.control_id == control_id else ctrl
                            for ctrl in group.controls
                        ]
                        break

            return True

    def unassign_control(self, control_id: int) -> bool:
        """
        Unassign a control.

        Args:
            control_id: Control to unassign

        Returns:
            True if unassigned successfully
        """
        with self.lock:
            if control_id in self.assignments:
                del self.assignments[control_id]

                # Remove from groups
                for group in self.groups.values():
                    group.controls = [
                        ctrl for ctrl in group.controls if ctrl.control_id != control_id
                    ]

                return True
            return False

    def create_control_group(
        self, group_id: int, name: str, control_assignments: list[ControlAssignment]
    ) -> bool:
        """
        Create a control group.

        Args:
            group_id: Group identifier
            name: Group name
            control_assignments: List of control assignments

        Returns:
            True if group created successfully
        """
        with self.lock:
            if group_id in self.groups:
                return False

            group = ControlGroup(group_id, name, control_assignments)
            self.groups[group_id] = group

            # Add assignments to global assignments
            for assignment in control_assignments:
                self.assignments[assignment.control_id] = assignment

            return True

    def activate_group(self, group_id: int) -> bool:
        """
        Activate a control group.

        Args:
            group_id: Group to activate

        Returns:
            True if activated successfully
        """
        with self.lock:
            # Deactivate all groups
            for group in self.groups.values():
                group.active = False

            # Activate specified group
            if group_id in self.groups:
                self.groups[group_id].active = True

                # Update global assignments
                for assignment in self.groups[group_id].controls:
                    self.assignments[assignment.control_id] = assignment

                return True
            return False

    def get_control_assignment(self, control_id: int) -> ControlAssignment | None:
        """
        Get control assignment for a control ID.

        Args:
            control_id: Control identifier

        Returns:
            Control assignment or None
        """
        with self.lock:
            return self.assignments.get(control_id)

    def process_control_message(self, control_id: int, midi_value: int) -> dict[str, Any] | None:
        """
        Process a control change message.

        Args:
            control_id: Control identifier
            midi_value: MIDI control value (0-127)

        Returns:
            Parameter update info or None if no assignment
        """
        with self.lock:
            # Check performance controls first
            if control_id in self.performance_assignments:
                assignment = self.performance_assignments[control_id]
            else:
                assignment = self.get_control_assignment(control_id)

            if assignment:
                parameter_value = assignment.apply_value(midi_value)
                return {
                    "parameter_path": assignment.parameter_path,
                    "value": parameter_value,
                    "control_id": control_id,
                    "midi_value": midi_value,
                    "assignment_name": assignment.name,
                }

            return None

    def get_available_controls(self) -> list[int]:
        """Get list of available controls for assignment"""
        return self._get_available_controls()

    def _get_available_controls(self) -> list[int]:
        """Get all assignable controls"""
        controls = []
        controls.extend(self.control_layout["knobs"])
        controls.extend(self.control_layout["buttons"])
        return controls

    def get_control_groups(self) -> dict[int, dict[str, Any]]:
        """Get information about all control groups"""
        with self.lock:
            return {
                group_id: {
                    "name": group.name,
                    "active": group.active,
                    "controls": len(group.controls),
                    "control_ids": [ctrl.control_id for ctrl in group.controls],
                }
                for group_id, group in self.groups.items()
            }

    def export_assignments(self, filename: str) -> bool:
        """
        Export control assignments to file.

        Args:
            filename: Output filename

        Returns:
            True if exported successfully
        """
        with self.lock:
            try:
                export_data = {
                    "assignments": {
                        ctrl_id: {
                            "parameter_path": assignment.parameter_path,
                            "min_value": assignment.min_value,
                            "max_value": assignment.max_value,
                            "curve": assignment.curve,
                            "name": assignment.name,
                        }
                        for ctrl_id, assignment in self.assignments.items()
                    },
                    "groups": {
                        group_id: {
                            "name": group.name,
                            "active": group.active,
                            "controls": [
                                {
                                    "control_id": ctrl.control_id,
                                    "parameter_path": ctrl.parameter_path,
                                    "min_value": ctrl.min_value,
                                    "max_value": ctrl.max_value,
                                    "curve": ctrl.curve,
                                    "name": ctrl.name,
                                }
                                for ctrl in group.controls
                            ],
                        }
                        for group_id, group in self.groups.items()
                    },
                }

                import json

                with open(filename, "w") as f:
                    json.dump(export_data, f, indent=2)

                return True
            except Exception:
                return False

    def import_assignments(self, filename: str) -> bool:
        """
        Import control assignments from file.

        Args:
            filename: Input filename

        Returns:
            True if imported successfully
        """
        with self.lock:
            try:
                import json

                with open(filename) as f:
                    import_data = json.load(f)

                # Clear existing assignments
                self.assignments.clear()
                self.groups.clear()

                # Import assignments
                for ctrl_id_str, assignment_data in import_data.get("assignments", {}).items():
                    ctrl_id = int(ctrl_id_str)
                    assignment = ControlAssignment(
                        ctrl_id,
                        assignment_data["parameter_path"],
                        assignment_data["min_value"],
                        assignment_data["max_value"],
                        assignment_data["curve"],
                        assignment_data["name"],
                    )
                    self.assignments[ctrl_id] = assignment

                # Import groups
                for group_id_str, group_data in import_data.get("groups", {}).items():
                    group_id = int(group_id_str)

                    controls = []
                    for ctrl_data in group_data.get("controls", []):
                        ctrl = ControlAssignment(
                            ctrl_data["control_id"],
                            ctrl_data["parameter_path"],
                            ctrl_data["min_value"],
                            ctrl_data["max_value"],
                            ctrl_data["curve"],
                            ctrl_data["name"],
                        )
                        controls.append(ctrl)

                    group = ControlGroup(group_id, group_data["name"], controls)
                    group.active = group_data.get("active", False)
                    self.groups[group_id] = group

                return True
            except Exception:
                return False

    def get_control_surface_layout(self) -> dict[str, Any]:
        """Get control surface layout information"""
        return {
            "knobs": {
                "count": len(self.control_layout["knobs"]),
                "ids": self.control_layout["knobs"],
                "description": "Assignable control knobs 1-4",
            },
            "buttons": {
                "count": len(self.control_layout["buttons"]),
                "ids": self.control_layout["buttons"],
                "description": "Assignable buttons A-D",
            },
            "fixed_controls": {
                "mod_wheel": self.control_layout["mod_wheel"],
                "pitch_bend": self.control_layout["pitch_bend"],
                "data_entry": self.control_layout["data_entry"],
                "foot_pedal": self.control_layout["foot_pedal"],
                "foot_switch": self.control_layout["foot_switch"],
            },
            "total_assignable": len(self._get_available_controls()),
        }

    def create_preset_group(self, preset_name: str) -> int:
        """
        Create a control group from a preset.

        Args:
            preset_name: Name for the preset group

        Returns:
            Group ID
        """
        with self.lock:
            # Find available group ID
            group_id = 1
            while group_id in self.groups:
                group_id += 1

            # Create group with current assignments
            controls = list(self.assignments.values())
            group = ControlGroup(group_id, preset_name, controls)
            self.groups[group_id] = group

            return group_id

    def get_midi_mapping(self) -> dict[int, str]:
        """
        Get MIDI CC to parameter mapping.

        Returns:
            Dictionary mapping MIDI CC numbers to parameter paths
        """
        with self.lock:
            mapping = {}
            for ctrl_id, assignment in self.assignments.items():
                if ctrl_id <= 127:  # Valid MIDI CC
                    mapping[ctrl_id] = assignment.parameter_path

            # Add performance controls
            for ctrl_id, assignment in self.performance_assignments.items():
                if ctrl_id <= 127:
                    mapping[ctrl_id] = assignment.parameter_path

            return mapping

    def validate_assignment(self, control_id: int, parameter_path: str) -> bool:
        """
        Validate if an assignment is possible.

        Args:
            control_id: Control identifier
            parameter_path: Parameter path

        Returns:
            True if assignment is valid
        """
        # Check if control exists
        if control_id not in self._get_available_controls():
            return False

        # Basic parameter path validation
        if not parameter_path or not isinstance(parameter_path, str):
            return False

        # Could add more sophisticated validation here
        # (e.g., check if parameter exists in synthesizer)

        return True

    def reset_to_defaults(self):
        """Reset control surface to default assignments"""
        with self.lock:
            self.assignments.clear()
            self.groups.clear()
            self._init_default_assignments()

    def get_assignment_statistics(self) -> dict[str, Any]:
        """Get statistics about control assignments"""
        with self.lock:
            assigned_controls = len(self.assignments)
            total_groups = len(self.groups)
            active_groups = sum(1 for group in self.groups.values() if group.active)

            return {
                "assigned_controls": assigned_controls,
                "total_groups": total_groups,
                "active_groups": active_groups,
                "available_controls": len(self._get_available_controls()),
                "assignment_percentage": (assigned_controls / len(self._get_available_controls()))
                * 100,
            }


# Import math for control calculations
import math
