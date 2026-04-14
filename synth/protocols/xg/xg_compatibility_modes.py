"""
XG Compatibility Modes - GM/GM2/XG Mode Switching

Implements XG compatibility mode switching for GM, GM2, and XG operation.
Provides seamless compatibility with legacy MIDI devices and software.

XG Specification Compliance:
- GM Mode: F0 43 [dev] 4C 03 00 F7 (General MIDI)
- GM2 Mode: F0 43 [dev] 4C 03 01 F7 (General MIDI 2)
- XG ON: F0 43 [dev] 4C 02 00 F7 (XG Mode)
- XG OFF: F0 43 [dev] 4C 02 01 F7 (Exit XG Mode)
- XG Reset: F0 43 [dev] 4C 04 F7 (Reset to XG defaults)

Copyright (c) 2025
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class XGCompatibilityModes:
    """
    XG Compatibility Modes - Professional Mode Switching

    Handles seamless switching between GM, GM2, and XG compatibility modes.
    Provides appropriate parameter defaults and behavior for each mode.

    Key Features:
    - GM (General MIDI) compatibility
    - GM2 (General MIDI 2) compatibility
    - XG native mode operation
    - Automatic parameter reset on mode change
    - Mode-specific voice allocation and effects
    """

    # Compatibility mode constants
    MODE_GM = "GM"  # General MIDI
    MODE_GM2 = "GM2"  # General MIDI 2
    MODE_XG = "XG"  # Extended General MIDI (XG)

    # Mode-specific defaults
    MODE_DEFAULTS = {
        MODE_GM: {
            "description": "General MIDI (GM) - 128 voices, basic effects",
            "max_voices": 128,
            "max_parts": 16,
            "effects_support": "basic",
            "drum_channels": [9],  # Channel 10 (9 zero-indexed)
            "voice_allocation": "static",  # Fixed voice assignment
            "parameter_defaults": {
                "reverb_type": 0x01,  # Basic reverb
                "chorus_type": 0x41,  # Basic chorus
                "variation_type": 0x00,  # No variation
                "multi_part_mode": False,  # Single part mode
                "voice_reserve": [8] * 16,  # Equal allocation
            },
        },
        MODE_GM2: {
            "description": "General MIDI 2 (GM2) - Enhanced GM with more controls",
            "max_voices": 128,
            "max_parts": 16,
            "effects_support": "enhanced",
            "drum_channels": [9],  # Channel 10
            "voice_allocation": "dynamic",  # Dynamic voice allocation
            "parameter_defaults": {
                "reverb_type": 0x01,  # Hall 1
                "chorus_type": 0x41,  # Chorus 1
                "variation_type": 0x10,  # Chorus 1
                "multi_part_mode": True,  # Multi-part support
                "voice_reserve": [8] * 16,  # Equal allocation
            },
        },
        MODE_XG: {
            "description": "Extended General MIDI (XG) - Full XG specification",
            "max_voices": 128,
            "max_parts": 16,
            "effects_support": "full",
            "drum_channels": [9],  # Channel 10 (can be extended)
            "voice_allocation": "intelligent",  # XG intelligent allocation
            "parameter_defaults": {
                "reverb_type": 0x01,  # Hall 1
                "chorus_type": 0x41,  # Chorus 1
                "variation_type": 0x10,  # Chorus 1
                "multi_part_mode": True,  # Full multi-part
                "voice_reserve": [8] * 16,  # XG defaults
            },
        },
    }

    def __init__(self):
        """Initialize XG compatibility modes."""
        self.lock = threading.RLock()

        # Current compatibility mode
        self.current_mode = self.MODE_XG  # Default to XG

        # Mode change callback
        self.mode_change_callback = None

        # SYSEX message handler callback
        self.sysex_callback = None

        print("🎹 XG COMPATIBILITY MODES: Initialized")
        print(f"   Current mode: {self.current_mode}")
        print(f"   Available modes: {', '.join(self.MODE_DEFAULTS.keys())}")

    def set_mode_change_callback(self, callback: Callable[[str, dict[str, Any]], None]):
        """Set callback for mode changes (mode, mode_info)."""
        self.mode_change_callback = callback

    def set_sysex_callback(self, callback: Callable[[bytes], dict[str, Any] | None]):
        """Set callback for SYSEX message processing."""
        self.sysex_callback = callback

    def process_sysex_message(self, data: bytes) -> dict[str, Any] | None:
        """
        Process SYSEX message for mode switching.

        Args:
            data: SYSEX message data

        Returns:
            Processing result or None if not handled
        """
        try:
            # Validate XG SYSEX format: F0 43 [dev] 4C [cmd] [data...] F7
            if len(data) < 6 or data[0] != 0xF0 or data[-1] != 0xF7:
                return None

            if data[1] != 0x43 or data[3] != 0x4C:  # Not Yamaha XG
                return None

            command = data[4]
            command_data = data[
                5:-2
            ]  # Exclude F0, manufacturer, device, model, command, checksum, F7

            # Handle mode switching commands
            if command == 0x02:  # XG ON/OFF
                return self._handle_xg_mode_switch(command_data)
            elif command == 0x03:  # GM/GM2 Mode
                return self._handle_gm_mode_switch(command_data)
            elif command == 0x04:  # XG Reset
                return self._handle_xg_reset(command_data)

        except Exception as e:
            print(f"❌ XG COMPATIBILITY: SYSEX processing error - {e}")
            return None

        return None

    def _handle_xg_mode_switch(self, data: bytes) -> dict[str, Any] | None:
        """Handle XG ON/OFF: F0 43 [dev] 4C 02 [mode] F7"""
        if len(data) < 1:
            return None

        mode_value = data[0]

        if mode_value == 0x00:  # XG ON
            self.set_compatibility_mode(self.MODE_XG)
            return {"type": "mode_switch", "mode": self.MODE_XG, "action": "xg_on"}
        elif mode_value == 0x01:  # XG OFF (switch to GM)
            self.set_compatibility_mode(self.MODE_GM)
            return {"type": "mode_switch", "mode": self.MODE_GM, "action": "xg_off"}

        return None

    def _handle_gm_mode_switch(self, data: bytes) -> dict[str, Any] | None:
        """Handle GM/GM2 mode switch: F0 43 [dev] 4C 03 [mode] F7"""
        if len(data) < 1:
            return None

        mode_value = data[0]

        if mode_value == 0x00:  # GM Mode
            self.set_compatibility_mode(self.MODE_GM)
            return {"type": "mode_switch", "mode": self.MODE_GM, "action": "gm_mode"}
        elif mode_value == 0x01:  # GM2 Mode
            self.set_compatibility_mode(self.MODE_GM2)
            return {"type": "mode_switch", "mode": self.MODE_GM2, "action": "gm2_mode"}

        return None

    def _handle_xg_reset(self, data: bytes) -> dict[str, Any] | None:
        """Handle XG reset: F0 43 [dev] 4C 04 F7"""
        # Reset to XG mode with defaults
        self.set_compatibility_mode(self.MODE_XG, reset_parameters=True)
        return {"type": "reset", "mode": self.MODE_XG, "action": "xg_reset"}

    def set_compatibility_mode(self, mode: str, reset_parameters: bool = True) -> bool:
        """
        Set compatibility mode.

        Args:
            mode: Mode name ('GM', 'GM2', or 'XG')
            reset_parameters: Whether to reset parameters to mode defaults

        Returns:
            True if mode was set successfully
        """
        with self.lock:
            if mode not in self.MODE_DEFAULTS:
                return False

            old_mode = self.current_mode
            self.current_mode = mode

            mode_info = self.MODE_DEFAULTS[mode].copy()

            # Notify callback
            if self.mode_change_callback:
                self.mode_change_callback(mode, mode_info)

            print(f"🎹 XG COMPATIBILITY: Switched from {old_mode} to {mode}")
            print(f"   Mode: {mode_info['description']}")

            if reset_parameters:
                print("   Parameters reset to mode defaults")
                # Note: Actual parameter reset would be handled by the main synthesizer
                # This is just the mode switching logic

            return True

    def get_current_mode(self) -> str:
        """Get current compatibility mode."""
        with self.lock:
            return self.current_mode

    def get_mode_info(self, mode: str = None) -> dict[str, Any] | None:
        """
        Get information about a compatibility mode.

        Args:
            mode: Mode name (None = current mode)

        Returns:
            Mode information dictionary
        """
        mode_name = mode or self.current_mode
        if mode_name in self.MODE_DEFAULTS:
            info = self.MODE_DEFAULTS[mode_name].copy()
            info["current"] = mode_name == self.current_mode
            return info
        return None

    def get_available_modes(self) -> list[str]:
        """Get list of available compatibility modes."""
        return list(self.MODE_DEFAULTS.keys())

    def is_gm_mode(self) -> bool:
        """Check if currently in GM mode."""
        return self.current_mode == self.MODE_GM

    def is_gm2_mode(self) -> bool:
        """Check if currently in GM2 mode."""
        return self.current_mode == self.MODE_GM2

    def is_xg_mode(self) -> bool:
        """Check if currently in XG mode."""
        return self.current_mode == self.MODE_XG

    def get_mode_specific_defaults(self, mode: str = None) -> dict[str, Any] | None:
        """
        Get parameter defaults for a specific mode.

        Args:
            mode: Mode name (None = current mode)

        Returns:
            Parameter defaults dictionary
        """
        mode_name = mode if mode is not None else self.current_mode
        mode_info = self.get_mode_info(mode_name)
        if mode_info:
            return mode_info.get("parameter_defaults", {})
        return None

    def should_use_multi_part_mode(self) -> bool:
        """
        Check if current mode supports multi-part operation.

        Returns:
            True if multi-part mode should be used
        """
        defaults = self.get_mode_specific_defaults()
        if defaults:
            return defaults.get("multi_part_mode", False)
        return False

    def get_max_voices_for_mode(self) -> int:
        """
        Get maximum voices supported in current mode.

        Returns:
            Maximum voice count
        """
        mode_info = self.get_mode_info()
        if mode_info:
            return mode_info.get("max_voices", 128)
        return 128

    def get_supported_effects_for_mode(self) -> str:
        """
        Get effects support level for current mode.

        Returns:
            Effects support level ('basic', 'enhanced', 'full')
        """
        mode_info = self.get_mode_info()
        if mode_info:
            return mode_info.get("effects_support", "basic")
        return "basic"

    # SYSEX message creation methods

    def create_xg_on_message(self) -> bytes:
        """
        Create XG ON SYSEX message.

        Returns:
            XG ON SYSEX message
        """
        return self._create_mode_message(0x02, 0x00)  # Command 02, XG ON

    def create_xg_off_message(self) -> bytes:
        """
        Create XG OFF SYSEX message.

        Returns:
            XG OFF SYSEX message
        """
        return self._create_mode_message(0x02, 0x01)  # Command 02, XG OFF

    def create_gm_mode_message(self) -> bytes:
        """
        Create GM mode SYSEX message.

        Returns:
            GM mode SYSEX message
        """
        return self._create_mode_message(0x03, 0x00)  # Command 03, GM mode

    def create_gm2_mode_message(self) -> bytes:
        """
        Create GM2 mode SYSEX message.

        Returns:
            GM2 mode SYSEX message
        """
        return self._create_mode_message(0x03, 0x01)  # Command 03, GM2 mode

    def create_xg_reset_message(self) -> bytes:
        """
        Create XG reset SYSEX message.

        Returns:
            XG reset SYSEX message
        """
        # XG reset: F0 43 [dev] 4C 04 [checksum] F7
        message = [0xF0, 0x43, 0x10, 0x4C, 0x04]  # Device ID 0x10

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def _create_mode_message(self, command: int, mode_value: int) -> bytes:
        """Create mode switching SYSEX message."""
        # Format: F0 43 [dev] 4C [command] [mode_value] [checksum] F7
        message = [0xF0, 0x43, 0x10, 0x4C, command, mode_value]  # Device ID 0x10

        # Calculate checksum
        checksum = self._calculate_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def _calculate_checksum(self, data: list[int]) -> int:
        """Calculate XG SYSEX checksum."""
        checksum = 0
        for byte in data:
            checksum += byte
        checksum = (checksum & 0x7F) ^ 0x7F  # XG checksum formula
        return checksum

    # Mode validation and compatibility

    def validate_parameter_for_mode(self, parameter_name: str, value: Any) -> bool:
        """
        Validate if a parameter is supported in current mode.

        Args:
            parameter_name: Parameter name
            value: Parameter value

        Returns:
            True if parameter is valid for current mode
        """
        mode = self.get_current_mode()

        # XG mode supports all parameters
        if mode == self.MODE_XG:
            return True

        # GM2 supports more than GM
        if mode == self.MODE_GM2:
            # GM2 supports most XG parameters except advanced ones
            advanced_params = {"variation_type", "multi_part_mode"}
            return parameter_name not in advanced_params

        # GM supports only basic parameters
        if mode == self.MODE_GM:
            basic_params = {"reverb_type", "chorus_type", "voice_reserve"}
            return parameter_name in basic_params

        return False

    def get_mode_compatibility_report(self) -> dict[str, Any]:
        """
        Generate mode compatibility report.

        Returns:
            Compatibility report dictionary
        """
        current_mode = self.get_current_mode()
        mode_info = self.get_mode_info(current_mode)

        return {
            "current_mode": current_mode,
            "mode_description": mode_info.get("description", "Unknown") if mode_info else "Unknown",
            "max_voices": mode_info.get("max_voices", 128) if mode_info else 128,
            "max_parts": mode_info.get("max_parts", 16) if mode_info else 16,
            "effects_support": mode_info.get("effects_support", "basic") if mode_info else "basic",
            "voice_allocation": mode_info.get("voice_allocation", "static")
            if mode_info
            else "static",
            "drum_channels": mode_info.get("drum_channels", [9]) if mode_info else [9],
            "available_modes": self.get_available_modes(),
            "multi_part_supported": self.should_use_multi_part_mode(),
        }

    # Status and monitoring

    def get_status(self) -> dict[str, Any]:
        """Get compatibility modes status."""
        with self.lock:
            return {
                "current_mode": self.current_mode,
                "available_modes": self.get_available_modes(),
                "mode_info": self.get_mode_info(),
                "compatibility_report": self.get_mode_compatibility_report(),
                "callbacks_configured": {
                    "mode_change": self.mode_change_callback is not None,
                    "sysex": self.sysex_callback is not None,
                },
            }

    def reset_to_xg_mode(self):
        """Reset to XG mode."""
        self.set_compatibility_mode(self.MODE_XG, reset_parameters=True)
        print("🎹 XG COMPATIBILITY: Reset to XG mode")

    def __str__(self) -> str:
        """String representation."""
        status = self.get_status()
        return f"XGCompatibilityModes(current={status['current_mode']})"

    def __repr__(self) -> str:
        return self.__str__()
