"""
XG Controller Assignments (NRPN MSB 15-16)

Implements XG controller assignment system for professional MIDI control.
Handles NRPN MSB 15-16 parameter ranges for controller routing.

XG Specification Compliance:
- MSB 15 LSB 0-7: Controller assignments (Mod, Foot, Aftertouch, etc.)
- MSB 16 LSB 0-3: Extended controller assignments
- Controller curves and ranges
- Real-time controller routing updates

Copyright (c) 2025
"""
from __future__ import annotations

from typing import Any
import threading


class XGControllerAssignments:
    """
    XG Controller Assignments (NRPN MSB 15-16)

    Handles XG controller assignment parameters for professional MIDI control.
    Provides complete controller routing with curves, ranges, and smoothing.

    Key Features:
    - 12 XG controller assignments (Mod, Vol, Pan, Exp, Rev, Cho, Var, etc.)
    - Controller curves (Linear, Exponential, etc.)
    - Controller ranges and smoothing
    - Real-time assignment updates
    - Thread-safe operation
    """

    # XG Controller Assignment Constants
    CONTROLLER_ASSIGNMENTS = {
        0: {'name': 'OFF', 'description': 'Controller disabled'},
        1: {'name': 'MOD', 'description': 'Modulation Wheel (CC 1)'},
        2: {'name': 'VOL', 'description': 'Volume (CC 7)'},
        3: {'name': 'PAN', 'description': 'Pan (CC 10)'},
        4: {'name': 'EXP', 'description': 'Expression (CC 11)'},
        5: {'name': 'REV', 'description': 'Reverb Send (CC 91)'},
        6: {'name': 'CHO', 'description': 'Chorus Send (CC 93)'},
        7: {'name': 'VAR', 'description': 'Variation Send'},
        8: {'name': 'PAN', 'description': 'Pan (alternative)'},
        9: {'name': 'FLT', 'description': 'Filter Cutoff'},
        10: {'name': 'POR', 'description': 'Portamento Time'},
        11: {'name': 'PIT', 'description': 'Pitch Bend'},
        12: {'name': 'AMB', 'description': 'Ambience/Depth'}
    }

    # Controller Curves
    CONTROLLER_CURVES = {
        0: 'Linear',
        1: 'Exponential',
        2: 'Logarithmic',
        3: 'S-Curve',
        4: 'Reverse Linear',
        5: 'Reverse Exponential'
    }

    def __init__(self, num_channels: int = 16):
        """
        Initialize XG Controller Assignments.

        Args:
            num_channels: Number of MIDI channels (default 16)
        """
        self.num_channels = num_channels
        self.lock = threading.RLock()

        # Controller assignments per channel: channel -> assignment_slot -> controller_number
        self.controller_assignments = {}

        # Controller curves per channel: channel -> assignment_slot -> curve_type
        self.controller_curves = {}

        # Controller ranges per channel: channel -> assignment_slot -> (min, max)
        self.controller_ranges = {}

        # Parameter change callback
        self.parameter_change_callback = None

        # Initialize defaults
        self._initialize_xg_defaults()

        print("🎛️ XG CONTROLLER ASSIGNMENTS: Initialized")
        print(f"   {num_channels} channels configured for XG controller routing")

    def _initialize_xg_defaults(self):
        """Initialize XG controller assignment defaults."""
        # XG Default assignments (MSB 15-16)
        xg_defaults = {
            0: 1,   # Mod Wheel -> MOD
            1: 2,   # Foot Controller -> VOL
            2: 3,   # Aftertouch -> PAN
            3: 4,   # Breath Controller -> EXP
            4: 5,   # General 1 -> REV
            5: 6,   # General 2 -> CHO
            6: 7,   # General 3 -> VAR
            7: 8,   # General 4 -> PAN
            8: 12,  # Ribbon -> AMB
        }

        for channel in range(self.num_channels):
            self.controller_assignments[channel] = xg_defaults.copy()
            self.controller_curves[channel] = {slot: 0 for slot in xg_defaults.keys()}  # Linear curves
            self.controller_ranges[channel] = {slot: (0, 127) for slot in xg_defaults.keys()}  # Full range

    def handle_nrpn_msb15(self, channel: int, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 15 (Controller Assignments) messages.

        Args:
            channel: MIDI channel (0-15)
            lsb: NRPN LSB value (0-7 for assignment slots)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= lsb <= 7):  # LSB 0-7 for assignments
                return False

            # Convert 14-bit value to controller assignment (0-12)
            assignment = data_value >> 7  # Take upper 7 bits

            if assignment in self.CONTROLLER_ASSIGNMENTS:
                if channel not in self.controller_assignments:
                    self.controller_assignments[channel] = {}
                self.controller_assignments[channel][lsb] = assignment

                self._notify_parameter_change(f'controller_assignment_ch{channel}_slot{lsb}', assignment)
                return True

        return False

    def handle_nrpn_msb16(self, channel: int, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 16 (Extended Controller Assignments) messages.

        Args:
            channel: MIDI channel (0-15)
            lsb: NRPN LSB value (0-3 for extended assignments)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= lsb <= 3):  # LSB 0-3 for extended assignments
                return False

            # Map to assignment slot (8-11)
            assignment_slot = lsb + 8

            # Convert 14-bit value to controller assignment (0-12)
            assignment = data_value >> 7

            if assignment in self.CONTROLLER_ASSIGNMENTS:
                if channel not in self.controller_assignments:
                    self.controller_assignments[channel] = {}
                self.controller_assignments[channel][assignment_slot] = assignment

                self._notify_parameter_change(f'controller_assignment_ch{channel}_slot{assignment_slot}', assignment)
                return True

        return False

    def handle_controller_curve(self, channel: int, assignment_slot: int, curve_type: int) -> bool:
        """
        Handle controller curve assignment.

        Args:
            channel: MIDI channel (0-15)
            assignment_slot: Assignment slot (0-11)
            curve_type: Curve type (0-5)

        Returns:
            True if curve was set
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= assignment_slot <= 11):
                return False
            if curve_type not in self.CONTROLLER_CURVES:
                return False

            if channel not in self.controller_curves:
                self.controller_curves[channel] = {}
            self.controller_curves[channel][assignment_slot] = curve_type

            self._notify_parameter_change(f'controller_curve_ch{channel}_slot{assignment_slot}', curve_type)
            return True

    def handle_controller_range(self, channel: int, assignment_slot: int,
                              min_value: int, max_value: int) -> bool:
        """
        Handle controller range assignment.

        Args:
            channel: MIDI channel (0-15)
            assignment_slot: Assignment slot (0-11)
            min_value: Minimum controller value (0-127)
            max_value: Maximum controller value (0-127)

        Returns:
            True if range was set
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= assignment_slot <= 11):
                return False
            if not (0 <= min_value <= max_value <= 127):
                return False

            if channel not in self.controller_ranges:
                self.controller_ranges[channel] = {}
            self.controller_ranges[channel][assignment_slot] = (min_value, max_value)

            self._notify_parameter_change(f'controller_range_ch{channel}_slot{assignment_slot}',
                                       {'min': min_value, 'max': max_value})
            return True

    def _notify_parameter_change(self, parameter_name: str, value: Any):
        """Notify parameter change callback."""
        if self.parameter_change_callback:
            self.parameter_change_callback(parameter_name, value)

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback

    def get_controller_assignment(self, channel: int, slot: int) -> int:
        """
        Get controller assignment for a channel and slot.

        Args:
            channel: MIDI channel (0-15)
            slot: Assignment slot (0-11)

        Returns:
            Controller assignment (0-12, 0=OFF)
        """
        with self.lock:
            if (channel in self.controller_assignments and
                slot in self.controller_assignments[channel]):
                return self.controller_assignments[channel][slot]

        # Return XG default
        xg_defaults = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 12}
        return xg_defaults.get(slot, 0)

    def get_controller_curve(self, channel: int, slot: int) -> int:
        """
        Get controller curve for a channel and slot.

        Args:
            channel: MIDI channel (0-15)
            slot: Assignment slot (0-11)

        Returns:
            Curve type (0-5, 0=Linear)
        """
        with self.lock:
            if (channel in self.controller_curves and
                slot in self.controller_curves[channel]):
                return self.controller_curves[channel][slot]

        return 0  # Linear

    def get_controller_range(self, channel: int, slot: int) -> tuple[int, int]:
        """
        Get controller range for a channel and slot.

        Args:
            channel: MIDI channel (0-15)
            slot: Assignment slot (0-11)

        Returns:
            Tuple of (min_value, max_value), default (0, 127)
        """
        with self.lock:
            if (channel in self.controller_ranges and
                slot in self.controller_ranges[channel]):
                return self.controller_ranges[channel][slot]

        return (0, 127)

    def apply_controller_value(self, channel: int, controller_number: int,
                             controller_value: int) -> dict[str, Any]:
        """
        Apply a controller value to assigned destinations.

        Args:
            channel: MIDI channel (0-15)
            controller_number: MIDI controller number (0-127)
            controller_value: Controller value (0-127)

        Returns:
            Dictionary of applied controller destinations and values
        """
        applied = {}

        with self.lock:
            # Find all assignment slots that use this controller
            for slot in range(12):
                assigned_controller = self.get_controller_assignment(channel, slot)
                if assigned_controller == controller_number:
                    # Apply controller value to this destination
                    curve = self.get_controller_curve(channel, slot)
                    min_val, max_val = self.get_controller_range(channel, slot)

                    # Apply curve transformation
                    processed_value = self._apply_controller_curve(controller_value, curve)

                    # Apply range scaling
                    scaled_value = self._scale_controller_value(processed_value, min_val, max_val)

                    destination_name = self._get_destination_name(slot)
                    applied[destination_name] = scaled_value

        return applied

    def _apply_controller_curve(self, value: int, curve_type: int) -> float:
        """
        Apply controller curve transformation.

        Args:
            value: Controller value (0-127)
            curve_type: Curve type (0-5)

        Returns:
            Transformed value (0.0-1.0)
        """
        normalized = value / 127.0

        if curve_type == 0:  # Linear
            return normalized
        elif curve_type == 1:  # Exponential
            return normalized * normalized
        elif curve_type == 2:  # Logarithmic
            return normalized ** 0.5 if normalized > 0 else 0.0
        elif curve_type == 3:  # S-Curve
            # S-curve using sigmoid-like function
            return 1.0 / (1.0 + (1.0 / normalized - 1.0) ** -2) if normalized > 0 else 0.0
        elif curve_type == 4:  # Reverse Linear
            return 1.0 - normalized
        elif curve_type == 5:  # Reverse Exponential
            return (1.0 - normalized) ** 2
        else:
            return normalized

    def _scale_controller_value(self, normalized_value: float, min_val: int, max_val: int) -> float:
        """
        Scale controller value to specified range.

        Args:
            normalized_value: Normalized value (0.0-1.0)
            min_val: Minimum output value
            max_val: Maximum output value

        Returns:
            Scaled value
        """
        range_size = max_val - min_val
        return min_val + normalized_value * range_size

    def _get_destination_name(self, slot: int) -> str:
        """
        Get destination name for assignment slot.

        Args:
            slot: Assignment slot (0-11)

        Returns:
            Destination name string
        """
        destinations = [
            'modulation_wheel', 'foot_controller', 'aftertouch', 'breath_controller',
            'general_controller_1', 'general_controller_2', 'general_controller_3',
            'general_controller_4', 'ribbon_controller', 'reserved_9', 'reserved_10', 'reserved_11'
        ]
        return destinations[slot] if slot < len(destinations) else f'slot_{slot}'

    def get_channel_assignments(self, channel: int) -> dict[str, Any]:
        """
        Get all controller assignments for a channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Dictionary with all assignments, curves, and ranges
        """
        with self.lock:
            assignments = {}
            for slot in range(12):
                assignment = self.get_controller_assignment(channel, slot)
                curve = self.get_controller_curve(channel, slot)
                min_val, max_val = self.get_controller_range(channel, slot)

                assignments[f'slot_{slot}'] = {
                    'controller': assignment,
                    'controller_name': self.CONTROLLER_ASSIGNMENTS.get(assignment, {}).get('name', 'UNKNOWN'),
                    'curve': curve,
                    'curve_name': self.CONTROLLER_CURVES.get(curve, 'UNKNOWN'),
                    'range': {'min': min_val, 'max': max_val}
                }

            return assignments

    def reset_channel_to_xg_defaults(self, channel: int):
        """Reset channel controller assignments to XG defaults."""
        with self.lock:
            if 0 <= channel < self.num_channels:
                # Reset to XG defaults
                xg_defaults = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 12}
                self.controller_assignments[channel] = xg_defaults.copy()
                self.controller_curves[channel] = {slot: 0 for slot in xg_defaults.keys()}
                self.controller_ranges[channel] = {slot: (0, 127) for slot in xg_defaults.keys()}

    def reset_all_channels_to_xg_defaults(self):
        """Reset all channels to XG controller assignment defaults."""
        with self.lock:
            for channel in range(self.num_channels):
                self.reset_channel_to_xg_defaults(channel)

        print("🎛️ XG CONTROLLER ASSIGNMENTS: Reset all channels to XG defaults")

    def export_assignments(self) -> dict[str, Any]:
        """Export all controller assignments."""
        with self.lock:
            return {
                'controller_assignments': self.controller_assignments.copy(),
                'controller_curves': self.controller_curves.copy(),
                'controller_ranges': dict(self.controller_ranges),  # Convert tuples to lists
                'version': '1.0'
            }

    def import_assignments(self, data: dict[str, Any]) -> bool:
        """Import controller assignments."""
        try:
            with self.lock:
                if 'controller_assignments' in data:
                    self.controller_assignments = data['controller_assignments'].copy()
                if 'controller_curves' in data:
                    self.controller_curves = data['controller_curves'].copy()
                if 'controller_ranges' in data:
                    # Convert lists back to tuples
                    self.controller_ranges = {ch: {slot: tuple(rng) for slot, rng in ranges.items()}
                                            for ch, ranges in data['controller_ranges'].items()}
                return True
        except Exception as e:
            print(f"❌ XG CONTROLLER ASSIGNMENTS: Import failed - {e}")
            return False

    def get_controller_assignment_info(self, assignment: int) -> dict[str, Any]:
        """
        Get information about a controller assignment.

        Args:
            assignment: Controller assignment number (0-12)

        Returns:
            Assignment information dictionary
        """
        info = self.CONTROLLER_ASSIGNMENTS.get(assignment, {}).copy()
        info['assignment_number'] = assignment
        return info

    def list_available_assignments(self) -> dict[int, dict[str, Any]]:
        """
        List all available controller assignments.

        Returns:
            Dictionary mapping assignment numbers to info
        """
        return {num: self.get_controller_assignment_info(num)
                for num in self.CONTROLLER_ASSIGNMENTS.keys()}

    def __str__(self) -> str:
        """String representation of controller assignments."""
        return f"XGControllerAssignments(channels={self.num_channels})"

    def __repr__(self) -> str:
        return self.__str__()
