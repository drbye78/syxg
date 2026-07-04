"""

Articulation Controllers for S.Art2 System.

Contains ArticulationController class that manages articulation state
and processes NRPN/SYSEX messages. Extracted for better code organization.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, ClassVar

from .mappings import MSB_CATEGORIES, NRPN_ARTICULATION_MAP, get_nrpn_for_articulation

logger = logging.getLogger(__name__)


class ArticulationController:
    """
    Controller that maps NRPN/SYSEX messages to S.Art2-style articulations.

    Provides articulation control for sample-based synthesis (SF2) by converting
    MIDI control messages into articulation parameters.

    Usage:
        controller = ArticulationController()
        controller.process_nrpn(1, 1)  # Sets 'legato'
    """

    # Import mapping from separate module
    NRPN_ARTICULATION_MAP = NRPN_ARTICULATION_MAP

    # S.Art2 SYSEX sub-commands (0x4C format)
    SYSEX_COMMANDS: ClassVar[dict[int, str]] = {
        0x10: "set_articulation",
        0x11: "set_parameter",
        0x12: "articulation_release",
        0x13: "articulation_query",
        0x14: "set_articulation_chain",
        0x15: "bulk_dump",
        0x16: "bulk_dump_request",
        0x17: "bulk_dump_data",
    }

    # Yamaha S.Art2 SYSEX manufacturer ID
    YAMAHA_SYSEX_ID = 0x43

    # XG compatibility mode NRPN overrides
    XG_ARTICULATION_MAP: ClassVar[dict[tuple[int, int], str]] = {
        (4, 1): "legato",
        (4, 2): "staccato",
        (4, 3): "marcato",
    }

    # GS compatibility mode NRPN overrides
    GS_ARTICULATION_MAP: ClassVar[dict[tuple[int, int], str]] = {
        (1, 5): "pizzicato",
    }

    def __init__(self):
        """Initialize the articulation controller."""
        self.current_articulation = "normal"
        self.current_category = "common"
        self.nrpn_msb = 0
        self.nrpn_lsb = 0

        # Compatibility mode (sart2, xg, gs)
        self.compatibility_mode = "sart2"

        # Current articulation parameters
        self.articulation_params: dict[str, Any] = {}

        # Articulation change callbacks
        self._callbacks: list[Callable[[str], None]] = []

        # Custom articulation handlers
        self._custom_articulations: dict[str, dict[str, Any]] = {}

    def set_compatibility_mode(self, mode: str) -> None:
        """Set compatibility mode."""
        if mode in ("sart2", "xg", "gs"):
            self.compatibility_mode = mode
        else:
            logger.warning(f"Unknown compatibility mode: {mode}")

    def get_compatibility_mode(self) -> str:
        """Get current compatibility mode."""
        return self.compatibility_mode

    def process_nrpn(self, msb: int, lsb: int) -> str:
        """
        Process NRPN message and set articulation.

        Args:
            msb: NRPN MSB (parameter number high)
            lsb: NRPN LSB (parameter number low)

        Returns:
            Articulation name
        """
        self.nrpn_msb = msb
        self.nrpn_lsb = lsb

        # Check compatibility mode first — mode-specific overrides
        if self.compatibility_mode == "xg":
            articulation = self.XG_ARTICULATION_MAP.get((msb, lsb))
            if articulation is None:
                articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")
        elif self.compatibility_mode == "gs":
            articulation = self.GS_ARTICULATION_MAP.get((msb, lsb))
            if articulation is None:
                articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")
        else:
            # Standard S.Art2 mode
            articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")

        self.current_articulation = articulation
        self.current_category = MSB_CATEGORIES.get(msb, "common")
        for callback in self._callbacks:
            try:
                callback(articulation)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        return articulation

    def process_sysex(self, sysex: bytes) -> dict[str, Any] | None:
        """
        Process Yamaha SYSEX message for articulations.

        Args:
            sysex: SYSEX message bytes

        Returns:
            Parsed parameters or None
        """
        if len(sysex) < 5:
            return None
        if sysex[1] != 0x43:  # Yamaha
            return None

        sub_id1 = sysex[2] if len(sysex) > 2 else 0  # Device ID
        sub_id2 = sysex[3] if len(sysex) > 3 else 0  # Message type

        if sub_id2 == 0x4C:
            # New S.Art2 format: F0 43 <device> 4C <sub_cmd> <channel> <data...> F7
            sub_cmd = sysex[4] if len(sysex) > 4 else 0
            if sub_cmd == 0x10:
                return self._parse_sysex_articulation_set(sysex)
            elif sub_cmd == 0x11:
                return self._parse_sysex_parameter_set(sysex)
            elif sub_cmd == 0x12:
                return self._parse_sysex_articulation_release(sysex)
            elif sub_cmd == 0x13:
                return self._parse_sysex_articulation_query(sysex)
            elif sub_cmd == 0x14:
                return self._parse_sysex_articulation_chain(sysex)
            elif sub_cmd == 0x15:
                return self._parse_sysex_bulk_dump(sysex)
            return {"type": f"unknown_0x4C_{sub_cmd:02X}", "command": "unknown", "channel": sysex[5] if len(sysex) > 5 else 0}
        elif sub_id1 == 0x19:
            # Existing format: F0 43 <device> 19 <sub_id2> <data...> F7
            if sub_id2 == 0x00:
                return self._parse_sysex_articulation_set(sysex)
            elif sub_id2 == 0x01:
                return self._parse_sysex_parameter_set(sysex)
            elif sub_id2 == 0x02:
                return self._parse_sysex_articulation_release(sysex)
            return None

        return None

    def _parse_sysex_articulation_set(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX articulation set message. Handles both 0x19 and 0x4C formats."""
        if sysex[3] == 0x4C:
            # 0x4C format: F0 43 <device> 4C 10 <channel> <art_msb> <art_lsb> ... F7
            if len(sysex) < 8:
                return {}
            channel = sysex[5] & 0x0F
            art_msb = sysex[6]
            art_lsb = sysex[7]
        else:
            # 0x19 format: F0 43 <device> 19 00 <channel> <art_type> <art_index> ... F7
            if len(sysex) < 8:
                return {}
            channel = sysex[4] & 0x0F
            art_msb = sysex[5]
            art_lsb = sysex[6]

        articulation = self.NRPN_ARTICULATION_MAP.get((art_msb, art_lsb), "normal")
        return {
            "type": "articulation_set",
            "command": "set_articulation",
            "channel": channel,
            "articulation": articulation,
            "nrpn_msb": art_msb,
            "nrpn_lsb": art_lsb,
            "art_type": art_msb,
            "art_index": art_lsb,
        }

    def _parse_sysex_parameter_set(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX parameter set message. Handles both 0x19 and 0x4C formats."""
        if sysex[3] == 0x4C:
            # 0x4C format: F0 43 <device> 4C 11 <channel> <param_msb> <param_lsb> <val_msb> <val_lsb> ... F7
            if len(sysex) < 10:
                return {}
            channel = sysex[5] & 0x0F
            param_msb = sysex[6]
            param_lsb = sysex[7]
            value_msb = sysex[8]
            value_lsb = sysex[9] if len(sysex) > 9 else 0
        else:
            # 0x19 format: F0 43 <device> 19 01 <channel> <param_msb> <param_lsb> <val_msb> <val_lsb> ... F7
            if len(sysex) < 9:
                return {}
            channel = sysex[4] & 0x0F
            param_msb = sysex[5]
            param_lsb = sysex[6]
            value_msb = sysex[7]
            value_lsb = sysex[8] if len(sysex) > 8 else 0

        param = (param_msb << 7) | param_lsb
        value = (value_msb << 7) | value_lsb

        # Build param_info
        param_info = {"param": param, "value": value, "name": f"param_{param}"}

        return {
            "type": "parameter_set",
            "command": "set_parameter",
            "channel": channel,
            "param_msb": param_msb,
            "param_lsb": param_lsb,
            "param": param,
            "value": value,
            "param_info": param_info,
        }

    def _parse_sysex_articulation_release(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX articulation release message."""
        if sysex[3] == 0x4C:
            # 0x4C format: F0 43 <device> 4C 12 <channel> ... F7
            channel = sysex[5] if len(sysex) > 5 else 0
        else:
            # 0x19 format
            channel = sysex[4] if len(sysex) > 4 else 0

        return {
            "type": "articulation_release",
            "command": "articulation_release",
            "channel": channel,
        }

    def _parse_sysex_articulation_query(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX articulation query message."""
        channel = sysex[5] if len(sysex) > 5 else 0
        return {
            "type": "articulation_query",
            "command": "articulation_query",
            "channel": channel,
        }

    def _parse_sysex_articulation_chain(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX articulation chain message (0x14)."""
        channel = sysex[5] if len(sysex) > 5 else 0
        count = sysex[6] if len(sysex) > 6 else 0
        articulations = []
        offset = 7
        for i in range(count):
            if offset + 4 < len(sysex):
                msb = sysex[offset]
                lsb = sysex[offset + 1]
                articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")
                duration_ms = (sysex[offset + 2] << 7) | sysex[offset + 3]
                articulations.append({
                    "articulation": articulation,
                    "duration_ms": duration_ms,
                    "nrpn_msb": msb,
                    "nrpn_lsb": lsb,
                })
                offset += 4
        return {
            "type": "articulation_chain",
            "command": "set_articulation_chain",
            "channel": channel,
            "count": count,
            "articulations": articulations,
        }

    def _parse_sysex_bulk_dump(self, sysex: bytes) -> dict[str, Any]:
        """Parse SYSEX bulk dump message (0x15)."""
        channel = sysex[5] if len(sysex) > 5 else 0
        data_start = 6
        checksum_index = len(sysex) - 2 if len(sysex) > 7 else data_start
        data = sysex[data_start:checksum_index]
        stored_checksum = sysex[checksum_index] if checksum_index < len(sysex) else 0
        calculated_checksum = self._calculate_sysex_checksum(data)
        return {
            "type": "bulk_dump",
            "command": "bulk_dump",
            "channel": channel,
            "data": list(data),
            "checksum_valid": stored_checksum == calculated_checksum,
        }

    def build_sysex_response(self, articulation: str) -> bytes:
        """Build SYSEX response for articulation query."""
        msb, lsb = get_nrpn_for_articulation(articulation)

        # Build basic SYSEX response
        response = bytearray(
            [
                0xF0,  # SYSEX start
                0x43,  # Yamaha
                0x10,  # Device ID
                0x19,  # S.Art2
                0x00,  # Sub ID
                msb,  # Articulation MSB
                lsb,  # Articulation LSB
                0x00,  # Checksum placeholder
                0xF7,  # SYSEX end
            ]
        )

        # Calculate checksum
        checksum = self._calculate_sysex_checksum(bytes(response[1:-2]))
        response[-2] = checksum

        return bytes(response)

    def _calculate_sysex_checksum(self, data: bytes) -> int:
        """Calculate Yamaha SYSEX checksum."""
        return (128 - (sum(data) % 128)) % 128

    def build_sysex_articulation_set(self, channel: int, art_msb: int, art_lsb: int) -> bytes:
        """Build SYSEX message to set articulation."""
        data = bytes([0x43, 0x10, 0x4C, 0x10, channel & 0x0F, art_msb, art_lsb])
        checksum = self._calculate_sysex_checksum(data)
        return bytes([0xF0]) + data + bytes([checksum, 0xF7])

    def build_sysex_parameter_set(self, channel: int, param_msb: int, param_lsb: int, value: int) -> bytes:
        """Build SYSEX message to set parameter."""
        value_msb = (value >> 7) & 0x7F
        value_lsb = value & 0x7F
        data = bytes([0x43, 0x10, 0x4C, 0x11, channel & 0x0F, param_msb, param_lsb, value_msb, value_lsb])
        checksum = self._calculate_sysex_checksum(data)
        return bytes([0xF0]) + data + bytes([checksum, 0xF7])

    def build_sysex_articulation_query(self, channel: int) -> bytes:
        """Build SYSEX message to query articulation."""
        data = bytes([0x43, 0x10, 0x4C, 0x13, channel & 0x0F])
        checksum = self._calculate_sysex_checksum(data)
        return bytes([0xF0]) + data + bytes([checksum, 0xF7])

    def _find_nrpn_for_articulation(self, articulation: str) -> tuple[int, int]:
        """Find NRPN (MSB, LSB) for an articulation name."""
        for (msb, lsb), art in self.NRPN_ARTICULATION_MAP.items():
            if art == articulation:
                return (msb, lsb)
        return (1, 0)  # Default: normal

    # =========================================================================
    # High-level API
    # =========================================================================

    def set_articulation(self, articulation: str) -> None:
        """Set articulation directly."""
        self.current_articulation = articulation

        # Find NRPN values
        msb, lsb = get_nrpn_for_articulation(articulation)
        self.nrpn_msb = msb
        self.nrpn_lsb = lsb

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(articulation)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_articulation(self) -> str:
        """Get current articulation."""
        return self.current_articulation

    def get_articulation_params(self, articulation: str | None = None) -> dict[str, Any]:
        """Get parameters for articulation."""
        art = articulation or self.current_articulation

        # Return stored params or defaults
        if art in self._custom_articulations:
            return self._custom_articulations[art].copy()

        # Return common defaults (merged with any stored custom params)
        defaults = {
            "normal": {},
            "legato": {"blend": 0.5, "transition_time": 0.05},
            "staccato": {"note_length": 0.3},
            "vibrato": {"rate": 5.0, "depth": 0.5},
            "tremolo": {"rate": 6.0, "depth": 0.5},
            "crescendo": {"target_level": 1.0, "duration": 1.0},
            "diminuendo": {"target_level": 0.1, "duration": 1.0},
        }

        base = defaults.get(art, {}).copy()
        base.update(self.articulation_params)
        return base

    def set_articulation_param(self, param: str, value: Any) -> None:
        """Set parameter for current articulation."""
        self.articulation_params[param] = value

    def get_available_articulations(self) -> list[str]:
        """Get list of available articulations."""
        return list(set(self.NRPN_ARTICULATION_MAP.values()))

    def get_articulations_by_category(self, category: str) -> list[str]:
        """Get articulations by category."""
        result = []
        for (msb, _), art in self.NRPN_ARTICULATION_MAP.items():
            if MSB_CATEGORIES.get(msb) == category:
                result.append(art)
        return list(set(result))

    def on_articulation_change(self, callback: Callable[[str], None]) -> None:
        """Register callback for articulation changes."""
        self._callbacks.append(callback)

    def reset(self) -> None:
        """Reset to default state."""
        self.current_articulation = "normal"
        self.current_category = "common"
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.articulation_params.clear()


def create_articulation_controller() -> ArticulationController:
    """Create and return an ArticulationController instance."""
    return ArticulationController()


__all__ = [
    "ArticulationController",
    "create_articulation_controller",
]
