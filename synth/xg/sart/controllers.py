"""
Articulation Controllers for S.Art2 System.

Contains ArticulationController class that manages articulation state
and processes NRPN/SYSEX messages. Extracted for better code organization.
"""

import logging
from typing import Dict, Tuple, Optional, Any, Callable, List
import numpy as np

from .mappings import NRPN_ARTICULATION_MAP, MSB_CATEGORIES, get_nrpn_for_articulation


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

    # Yamaha S.Art2 SYSEX manufacturer ID
    YAMAHA_SYSEX_ID = 0x43

    def __init__(self):
        """Initialize the articulation controller."""
        self.current_articulation = "normal"
        self.current_category = "common"
        self.nrpn_msb = 0
        self.nrpn_lsb = 0

        # Compatibility mode (sart2, xg, gs)
        self.compatibility_mode = "sart2"

        # Current articulation parameters
        self.articulation_params: Dict[str, Any] = {}

        # Articulation change callbacks
        self._callbacks: List[Callable[[str], None]] = []

        # Custom articulation handlers
        self._custom_articulations: Dict[str, Dict[str, Any]] = {}

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

        # Look up articulation
        articulation = self.NRPN_ARTICULATION_MAP.get((msb, lsb), "normal")

        # Update state
        self.current_articulation = articulation
        self.current_category = MSB_CATEGORIES.get(msb, "common")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(articulation)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return articulation

    def process_sysex(self, sysex: bytes) -> Optional[Dict[str, Any]]:
        """
        Process Yamaha SYSEX message for articulations.

        Args:
            sysex: SYSEX message bytes

        Returns:
            Parsed parameters or None
        """
        if len(sysex) < 5:
            return None

        # Check Yamaha manufacturer ID
        if sysex[1] != 0x43:  # Yamaha
            return None

        # Determine message type
        sub_id1 = sysex[2] if len(sysex) > 2 else 0
        sub_id2 = sysex[3] if len(sysex) > 3 else 0

        if sub_id1 == 0x19 and sub_id2 == 0x00:
            return self._parse_sysex_articulation_set(sysex)
        elif sub_id1 == 0x19 and sub_id2 == 0x01:
            return self._parse_sysex_parameter_set(sysex)
        elif sub_id1 == 0x19 and sub_id2 == 0x02:
            return self._parse_sysex_articulation_release(sysex)

        return None

    def _parse_sysex_articulation_set(self, sysex: bytes) -> Dict[str, Any]:
        """Parse SYSEX articulation set message."""
        if len(sysex) < 8:
            return {}

        channel = sysex[4] & 0x0F
        art_type = sysex[5]
        art_index = sysex[6]

        return {
            "type": "articulation_set",
            "channel": channel,
            "art_type": art_type,
            "art_index": art_index,
        }

    def _parse_sysex_parameter_set(self, sysex: bytes) -> Dict[str, Any]:
        """Parse SYSEX parameter set message."""
        if len(sysex) < 9:
            return {}

        channel = sysex[4] & 0x0F
        param_msb = sysex[5]
        param_lsb = sysex[6]
        value_msb = sysex[7]
        value_lsb = sysex[8] if len(sysex) > 8 else 0

        return {
            "type": "parameter_set",
            "channel": channel,
            "param": (param_msb << 7) | param_lsb,
            "value": (value_msb << 7) | value_lsb,
        }

    def _parse_sysex_articulation_release(self, sysex: bytes) -> Dict[str, Any]:
        """Parse SYSEX articulation release message."""
        if len(sysex) < 6:
            return {}

        channel = sysex[4] & 0x0F

        return {
            "type": "articulation_release",
            "channel": channel,
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

    def get_articulation_params(
        self, articulation: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get parameters for articulation."""
        art = articulation or self.current_articulation

        # Return stored params or defaults
        if art in self._custom_articulations:
            return self._custom_articulations[art].copy()

        # Return common defaults
        defaults = {
            "normal": {},
            "legato": {"blend": 0.5, "transition_time": 0.05},
            "staccato": {"note_length": 0.3},
            "vibrato": {"rate": 5.0, "depth": 0.5},
            "tremolo": {"rate": 6.0, "depth": 0.5},
            "crescendo": {"target_level": 1.0, "duration": 1.0},
            "diminuendo": {"target_level": 0.1, "duration": 1.0},
        }

        return defaults.get(art, {})

    def set_articulation_param(self, param: str, value: Any) -> None:
        """Set parameter for current articulation."""
        self.articulation_params[param] = value

    def get_available_articulations(self) -> List[str]:
        """Get list of available articulations."""
        return list(set(self.NRPN_ARTICULATION_MAP.values()))

    def get_articulations_by_category(self, category: str) -> List[str]:
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
