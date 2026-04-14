"""Jupiter-X MIDI Controller - orchestrator."""

from __future__ import annotations

import threading
from typing import Any

from .component_manager import JupiterXComponentManager
from .constants import *
from .sysex_controller import JupiterXSysExController
from .nrpn_controller import JupiterXNRPNController

class JupiterXMIDIController:
    """
    Jupiter-X MIDI Controller

    Main MIDI processing interface for Jupiter-X, combining SysEx and NRPN handling.
    """

    def __init__(self, component_manager: JupiterXComponentManager):
        self.component_manager = component_manager

        # Sub-controllers
        self.sysex_controller = JupiterXSysExController(component_manager)
        self.nrpn_controller = JupiterXNRPNController(component_manager)

        # Thread safety
        self.lock = threading.RLock()

        print("🎹 Jupiter-X MIDI Controller: Initialized")

    def process_midi_message(self, message_bytes: bytes) -> dict[str, Any] | None:
        """
        Process MIDI message for Jupiter-X.

        Args:
            message_bytes: Raw MIDI message bytes

        Returns:
            Processing result or None if not handled
        """
        with self.lock:
            # Check for SysEx first
            if len(message_bytes) > 3 and message_bytes[0] == 0xF0:
                return self.sysex_controller.process_sysex_message(message_bytes)

            # Check for NRPN controller messages
            elif len(message_bytes) == 3 and (message_bytes[0] & 0xF0) == 0xB0:  # CC message
                controller = message_bytes[1]
                value = message_bytes[2]

                # NRPN controllers
                if controller in [98, 99, 6, 38, 96, 97]:  # NRPN related
                    return {
                        "status": "processed"
                        if self.nrpn_controller.process_nrpn_message(controller, value)
                        else "ignored",
                        "type": "nrpn",
                        "controller": controller,
                        "value": value,
                    }

            return None

    def get_midi_status(self) -> dict[str, Any]:
        """Get comprehensive MIDI processing status."""
        with self.lock:
            return {
                "sysex_status": "active",
                "nrpn_status": self.nrpn_controller.get_nrpn_status(),
                "device_id": self.component_manager.system_params.device_id,
                "model_id": JUPITER_X_MODEL_ID,
                "manufacturer_id": JUPITER_X_MANUFACTURER_ID,
            }

    def create_parameter_change_sysex(self, address: bytes, value: int) -> bytes:
        """
        Create SysEx message for parameter change.

        Args:
            address: 3-byte parameter address
            value: Parameter value (0-127)

        Returns:
            Complete SysEx message bytes
        """
        return self.sysex_controller.create_parameter_change_message(address, value)

    def create_nrpn_messages(self, msb: int, lsb: int, value: int) -> list[bytes]:
        """
        Create NRPN message sequence for parameter change.

        Args:
            msb: NRPN MSB
            lsb: NRPN LSB
            value: 14-bit parameter value

        Returns:
            List of MIDI message bytes
        """
        return self.nrpn_controller.create_nrpn_message(msb, lsb, value)

    def reset_midi_state(self):
        """Reset all MIDI processing state."""
        with self.lock:
            self.nrpn_controller._reset_nrpn_state()

    def __str__(self) -> str:
        """String representation."""
        return "JupiterXMIDIController(active)"

    def __repr__(self) -> str:
        return self.__str__()
