"""
XG Component System - Clean XG Implementation

Production-quality XG synthesizer components with complete XG specification compliance.
Contains XG component manager, MIDI processor, and state management.
"""

from __future__ import annotations

from typing import Any


class XGComponentManager:
    """Manages XG components with clean interfaces and zero-allocation"""

    def __init__(self, device_id: int, max_channels: int, sample_rate: int):
        """Initialize XG component manager"""
        self.device_id = device_id
        self.max_channels = max_channels
        self.sample_rate = sample_rate

        # Pre-allocated component storage - no runtime allocation
        self.components = {}
        self._init_components()

    def _init_components(self):
        """Initialize all XG components - production quality"""
        # Import XG components
        from ...protocols.xg.xg_compatibility_modes import XGCompatibilityModes
        from ...protocols.xg.xg_controller_assignments import XGControllerAssignments
        from ...protocols.xg.xg_drum_setup_parameters import XGDrumSetupParameters
        from ...protocols.xg.xg_effects_enhancement import XGSystemEffectsEnhancement
        from ...protocols.xg.xg_micro_tuning import XGMicroTuning
        from ...protocols.xg.xg_multi_part_setup import XGMultiPartSetup
        from ...protocols.xg.xg_realtime_control import XGRealtimeControl
        from ...protocols.xg.xg_sysex_controller import XGSystemExclusiveController
        from ...protocols.xg.xg_system_parameters import XGSystemEffectParameters

        # Initialize all XG components
        self.components = {
            "sysex": XGSystemExclusiveController(self.device_id),
            "system_params": XGSystemEffectParameters(),
            "multi_part": XGMultiPartSetup(self.max_channels),
            "controllers": XGControllerAssignments(self.max_channels),
            "effects": XGSystemEffectsEnhancement(self.sample_rate),
            "drum_setup": XGDrumSetupParameters(self.max_channels),
            "micro_tuning": XGMicroTuning(self.max_channels),
            "realtime": XGRealtimeControl(self.device_id),
            "compatibility": XGCompatibilityModes(),
        }

    def get_component(self, name: str):
        """Get component by name - fast lookup"""
        return self.components.get(name)

    def process_sysex_message(self, data: bytes) -> dict[str, Any] | None:
        """Process SYSEX message through XG components"""
        # Route to appropriate component based on command
        if len(data) >= 6:
            command = data[4]

            # Parameter change
            if command == 0x08:
                return self.components["realtime"].process_sysex_message(data)
            # Display/LED control
            elif command in (0x10, 0x11):
                return self.components["realtime"].process_sysex_message(data)
            # Bulk operations
            elif command in (0x07, 0x09, 0x0A, 0x0C):
                return self.components["realtime"].process_sysex_message(data)
            # Mode switching
            elif command in (0x02, 0x03, 0x04):
                return self.components["compatibility"].process_sysex_message(data)

        return None

    def reset_all(self):
        """Reset all XG components to defaults"""
        for component in self.components.values():
            if hasattr(component, "reset"):
                component.reset()

    def cleanup(self):
        """Clean up all XG components"""
        for component in self.components.values():
            if hasattr(component, "cleanup"):
                component.cleanup()


class XGMIDIProcessor:
    """Efficient XG MIDI message processing with zero-allocation"""

    def __init__(self, component_manager: XGComponentManager):
        self.components = component_manager
        # Pre-compiled routing for performance
        self._init_routing()

    def _init_routing(self):
        """Initialize fast routing tables"""
        self.sysex_routes = {
            0x08: self.components.get_component(
                "realtime"
            ),  # Parameter change (also used for receive channel)
            0x10: self.components.get_component("realtime"),  # Display
            0x11: self.components.get_component("realtime"),  # LED
            0x07: self.components.get_component("realtime"),  # Bulk dump
            0x02: self.components.get_component("compatibility"),  # XG ON/OFF
            0x03: self.components.get_component("compatibility"),  # GM/GM2
            0x04: self.components.get_component("compatibility"),  # XG Reset
        }

        # Note: Receive channel SYSEX (0x08 with specific format) will be handled
        # by the synthesizer's receive_channel_manager after initialization

    def process_message(self, message_bytes: bytes) -> bool:
        """Process MIDI message - return True if XG handled it"""
        if self._is_sysex(message_bytes):
            return self._process_sysex(message_bytes)
        return False

    def _is_sysex(self, data: bytes) -> bool:
        """Check if message is SYSEX"""
        return len(data) >= 3 and data[0] == 0xF0 and data[-1] == 0xF7

    def _process_sysex(self, data: bytes) -> bool:
        """Process SYSEX message"""
        if len(data) < 6:
            return False

        command = data[4]
        handler = self.sysex_routes.get(command)

        if handler and hasattr(handler, "process_sysex_message"):
            return handler.process_sysex_message(data) is not None

        return False


class XGStateManager:
    """XG parameter state management with caching"""

    def __init__(self, component_manager: XGComponentManager):
        self.components = component_manager
        # Cached parameter getters for performance
        self._init_parameter_cache()

    def _init_parameter_cache(self):
        """Initialize parameter cache for fast access"""
        self.parameter_cache = {
            "reverb_type": lambda: self.components.get_component("system_params").get_reverb_type(),
            "chorus_type": lambda: self.components.get_component("system_params").get_chorus_type(),
            "variation_type": lambda: self.components.get_component("effects").get_variation_type(),
        }

        # Drum kit cache
        for ch in range(16):
            self.parameter_cache[f"drum_kit_ch{ch}"] = lambda c=ch: self.components.get_component(
                "drum_setup"
            ).get_drum_kit_info(c)

    def get_parameter(self, param_name: str):
        """Get parameter value from cache"""
        getter = self.parameter_cache.get(param_name)
        return getter() if getter else None

    def get_effects_config(self) -> dict[str, Any]:
        """Get effects configuration for audio processing"""
        return {
            "reverb_enabled": self.get_parameter("reverb_type") > 0,
            "chorus_enabled": self.get_parameter("chorus_type") > 0,
            "variation_enabled": self.get_parameter("variation_type") > 0,
        }
