from __future__ import annotations

#!/usr/bin/env python3
"""
XG PART EFFECT ROUTER

Complete MSB 32-39 multi-part effect routing implementation for professional
XG channel-to-effect-unit assignment.

Provides:
- MSB 32-39 parameter handling for effect assignment
- Channel-specific effect routing (reverb, chorus, variation)
- Multi-timbral XG effect distribution
- Professional studio effect routing capabilities
"""

import threading
from typing import Any


class XGPartEffectRouter:
    """
    XG MULTI-PART EFFECT ROUTER (MSB 32-39)

    Implements complete XG multi-part effect routing architecture.
    Assigns MIDI channels (parts) to specific XG effect units for:
    - Reverb sending (MSB 32)
    - Chorus sending (MSB 33)
    - Variation sending (MSB 34)
    - Reserved/advanced routing (MSB 35-39)

    This enables professional multi-timbral XG production where different
    instruments can be routed through different effect processors.
    """

    # XG Effect Types for routing
    EFFECT_TYPES = {
        "reverb": {"msb": 32, "description": "Reverb Send Assignment"},
        "chorus": {"msb": 33, "description": "Chorus Send Assignment"},
        "variation": {"msb": 34, "description": "Variation Send Assignment"},
        "reserved_35": {"msb": 35, "description": "Reserved"},
        "reserved_36": {"msb": 36, "description": "Reserved"},
        "reserved_37": {"msb": 37, "description": "Reserved"},
        "reserved_38": {"msb": 38, "description": "Reserved"},
        "reserved_39": {"msb": 39, "description": "Reserved"},
    }

    def __init__(self, num_channels: int = 16, num_effect_units: int = 10):
        """
        Initialize XG Part Effect Router.

        Args:
            num_channels: Number of MIDI channels to manage (default 16)
            num_effect_units: Number of XG effect units available (default 10)
        """
        self.num_channels = num_channels
        self.num_effect_units = num_effect_units
        self.lock = threading.RLock()

        # Effect routing assignments: channel -> effect_type -> assigned_unit
        # Values: 0 = off/bypass, 1-127 = effect unit number (1-127)
        self.effect_assignments: dict[int, dict[str, int]] = {}

        # Raw NRPN MSB 32-39 parameter values: channel -> msb_value -> lsb -> value
        self.routing_parameters: dict[int, dict[int, dict[int, int]]] = {}

        # Parameter caches for performance
        self._assignment_cache: dict[str, Any] = {}
        self._cache_dirty = True

        # Initialize default state
        self._initialize_xg_defaults()

    def _initialize_xg_defaults(self):
        """Initialize XG effect routing to standard defaults."""
        # XG Default: All parts (channels) send to effect unit 1 by default
        for channel in range(self.num_channels):
            # Don't waste memory - only allocate when actually used
            # XG default is all channels use effect unit 1 for each effect type
            pass

    def assign_channel_effect_unit(self, channel: int, effect_type: str, unit_number: int) -> bool:
        """
        Assign a MIDI channel to send to a specific effect unit for given effect type.

        Args:
            channel: MIDI channel (0-15)
            effect_type: 'reverb', 'chorus', or 'variation'
            unit_number: Effect unit number (0=off/bypass, 1-127=effect unit)

        Returns:
            True if assignment successful, False otherwise
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False
            if effect_type not in ["reverb", "chorus", "variation"]:
                return False
            if not (0 <= unit_number <= 127):
                return False

            # Initialize channel routing if needed
            if channel not in self.effect_assignments:
                self.effect_assignments[channel] = {}

            # Store assignment
            self.effect_assignments[channel][effect_type] = unit_number

            # Mark cache as dirty for performance optimization
            self._cache_dirty = True

            return True

    def get_channel_effect_unit(self, channel: int, effect_type: str) -> int:
        """
        Get the assigned effect unit for a channel and effect type.

        Args:
            channel: MIDI channel (0-15)
            effect_type: 'reverb', 'chorus', or 'variation'

        Returns:
            Effect unit number (0=off/bypass, 1-127=effect unit), or 1 (default) if not set
        """
        with self.lock:
            if (
                channel in self.effect_assignments
                and effect_type in self.effect_assignments[channel]
            ):
                return self.effect_assignments[channel][effect_type]

            # XG Default: All channels send to effect unit 1 by default
            return 1

    def get_channel_effect_assignment(self, channel: int) -> dict[str, int]:
        """
        Get all effect assignments for a channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Dictionary mapping effect types to assigned effect units
        """
        result = {}
        for effect_type in ["reverb", "chorus", "variation"]:
            result[effect_type] = self.get_channel_effect_unit(channel, effect_type)
        return result

    def handle_nrpn_msb32_to39(self, channel: int, msb: int, lsb: int, data_value: int) -> bool:
        """
        Handle MSB 32-39 NRPN messages for effect routing assignment.

        XG Multi-Part Effect Routing:
        - MSB 32, LSB 0-127: Reverb send assignment
        - MSB 33, LSB 0-127: Chorus send assignment
        - MSB 34, LSB 0-127: Variation send assignment
        - MSB 35-39: Reserved for advanced routing

        Args:
            channel: MIDI channel
            msb: NRPN MSB value (32-39)
            lsb: NRPN LSB value (0-127)
            data_value: 14-bit data value (0-16383, mapped to 0-127 for effects)

        Returns:
            True if handled, False otherwise
        """
        with self.lock:
            if not (32 <= msb <= 39):
                return False
            if not (0 <= channel < self.num_channels):
                return False
            if not (0 <= lsb <= 127):
                return False

            # Map MSB to effect type
            effect_map = {
                32: "reverb",
                33: "chorus",
                34: "variation",
                # 35-39 reserved for future/advanced routing
            }

            # Store raw parameter value (for bulk dump etc.)
            if channel not in self.routing_parameters:
                self.routing_parameters[channel] = {}
            if msb not in self.routing_parameters[channel]:
                self.routing_parameters[channel][msb] = {}

            self.routing_parameters[channel][msb][lsb] = data_value

            # Apply effect assignment if it's a main effect type
            if msb in effect_map:
                effect_type = effect_map[msb]

                # XG Spec: LSB determines which channel/part gets assigned
                # For now, we implement per-channel assignment
                # (More advanced: could implement channel grouping)
                assigned_channel = lsb  # 0-127 = channel 0-127

                # Currently we only handle channels 0-15, but store all values
                # for future expansion possibilities
                if assigned_channel < self.num_channels:
                    # Convert 14-bit value to effect unit assignment (0-127)
                    # XG: 0 = off/bypass, 1-127 = effect unit 1-127
                    effect_unit = data_value // 128  # Map 14-bit to 7-bit
                    if effect_unit == 0:
                        effect_unit = data_value  # For lower values, keep full resolution

                    self.assign_channel_effect_unit(assigned_channel, effect_type, effect_unit)

                self._cache_dirty = True
                return True

            # For MSB 35-39 (reserved/advanced), just store the parameter
            # Future implementations could add advanced routing features
            return True

    def handle_nrpn_message(
        self, channel: int, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int
    ) -> bool:
        """
        Handle complete NRPN message for effect routing.

        Args:
            channel: MIDI channel
            nrpn_msb: NRPN MSB value
            nrpn_lsb: NRPN LSB value
            data_msb: Data entry MSB
            data_lsb: Data entry LSB

        Returns:
            True if handled, False otherwise
        """
        # Convert to 14-bit data value
        data_value = (data_msb << 7) | data_lsb

        return self.handle_nrpn_msb32_to39(channel, nrpn_msb, nrpn_lsb, data_value)

    def get_all_routing_status(self) -> dict[str, Any]:
        """
        Get complete current status of effect routing.

        Returns:
            Comprehensive routing status dictionary
        """
        with self.lock:
            status = {}

            # Channel assignments
            status["channel_assignments"] = {}
            for channel in range(self.num_channels):
                status["channel_assignments"][f"channel_{channel}"] = (
                    self.get_channel_effect_assignment(channel)
                )

            # Raw parameters
            status["raw_parameters"] = self.routing_parameters.copy()

            # Summary statistics
            status["summary"] = self.get_routing_summary()

            return status

    def get_routing_summary(self) -> dict[str, Any]:
        """
        Get summary statistics of current effect routing configuration.

        Returns:
            Summary of routing assignments
        """
        summary = {
            "total_channels": self.num_channels,
            "effect_types": ["reverb", "chorus", "variation"],
            "assignment_counts": {},
            "routed_channels": {},
            "bypassed_channels": {},
        }

        for effect_type in ["reverb", "chorus", "variation"]:
            count = 0
            routed = []
            bypassed = []

            for channel in range(self.num_channels):
                unit = self.get_channel_effect_unit(channel, effect_type)
                if unit > 0:  # Active assignment
                    count += 1
                    routed.append(channel)
                else:  # Bypassed
                    bypassed.append(channel)

            summary["assignment_counts"][effect_type] = count
            summary["routed_channels"][effect_type] = routed
            summary["bypassed_channels"][effect_type] = bypassed

        return summary

    def reset_channel_routing(self, channel: int) -> bool:
        """
        Reset all effect routing assignments for a specific channel to defaults.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if reset successful, False otherwise
        """
        with self.lock:
            if not (0 <= channel < self.num_channels):
                return False

            # Remove channel assignments
            if channel in self.effect_assignments:
                del self.effect_assignments[channel]

            # Remove raw parameters for this channel
            if channel in self.routing_parameters:
                del self.routing_parameters[channel]

            self._cache_dirty = True
            return True

    def reset_all_routing(self):
        """Reset all effect routing assignments to XG defaults."""
        with self.lock:
            self.effect_assignments.clear()
            self.routing_parameters.clear()
            self._cache_dirty = True
            self._initialize_xg_defaults()

    def export_routing_to_bulk_dump(self, channel: int) -> list[int]:
        """
        Export effect routing parameters to XG bulk dump format.

        Args:
            channel: MIDI channel to export

        Returns:
            List of 7-bit parameter values for SysEx bulk dump
        """
        data = []

        if channel in self.routing_parameters:
            # Export in XG MSB 32-39 parameter order
            for msb in range(32, 40):  # MSB 32-39
                if msb in self.routing_parameters[channel]:
                    for lsb in range(128):  # All 128 LSB values
                        if lsb in self.routing_parameters[channel][msb]:
                            value = self.routing_parameters[channel][msb][lsb]
                            # Convert back to 7-bit for SysEx
                            data.append(value >> 7)  # MSB of 14-bit
                            data.append(value & 0x7F)  # LSB of 14-bit

        return data

    def import_routing_from_bulk_dump(self, channel: int, data: list[int]) -> bool:
        """
        Import effect routing parameters from XG bulk dump format.

        Args:
            channel: MIDI channel to import into
            data: Bulk dump data (pairs of 7-bit values)

        Returns:
            True if imported successfully, False otherwise
        """
        try:
            with self.lock:
                if len(data) % 2 != 0:
                    return False  # Must be pairs

                param_index = 0

                # Import MSB 32-39 parameters in order
                for msb in range(32, 40):
                    for lsb in range(128):
                        if param_index + 1 < len(data):
                            # Reconstruct 14-bit value
                            msb_val = data[param_index]
                            lsb_val = data[param_index + 1]
                            value = (msb_val << 7) | lsb_val

                            # Store parameter
                            if channel not in self.routing_parameters:
                                self.routing_parameters[channel] = {}
                            if msb not in self.routing_parameters[channel]:
                                self.routing_parameters[channel][msb] = {}

                            self.routing_parameters[channel][msb][lsb] = value

                            param_index += 2

                            # Apply to effect assignment if applicable
                            if msb <= 34:  # Main effect types
                                effect_map = {32: "reverb", 33: "chorus", 34: "variation"}
                                effect_type = effect_map[msb]

                                if lsb < self.num_channels:  # Valid channel
                                    effect_unit = value >> 7  # Convert to 0-127
                                    self.assign_channel_effect_unit(lsb, effect_type, effect_unit)
                        else:
                            break

                self._cache_dirty = True
                return True

        except Exception as e:
            print(f"Error importing effect routing bulk dump: {e}")
            return False

    def __str__(self) -> str:
        """String representation of current routing status."""
        summary = self.get_routing_summary()

        output = [f"XG Part Effect Router - {self.num_channels} channels:"]
        output.append("─" * 50)

        for effect_type in ["reverb", "chorus", "variation"]:
            count = summary["assignment_counts"][effect_type]
            routed = summary["routed_channels"][effect_type]
            output.append(f"{effect_type.title()}: {count} channels active")
            if routed:
                output.append(f"  Routed: {routed}")

        return "\n".join(output)
