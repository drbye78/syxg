"""
XGSynthesizerSystem - Production Grade XG/GS/GM Synthesizer Core

Complete implementation integrating:
- Unified sysex routing (XG/GS/GM)
- XG part modes with Drum Map support
- Complete NRPN parameter handling
- GS compatibility layer
- Part mode integration with synthesis engines

This is the production-grade core that unifies all MIDI XG/GS functionality.

Copyright (c) 2025 - Production Grade
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SynthesizerMode:
    """Current synthesizer operating mode"""

    xg_enabled: bool = False
    gs_enabled: bool = False
    gm_enabled: bool = False
    gm2_enabled: bool = False


class XGSynthesizerSystem:
    """
    Production-grade XG/GS/GM Synthesizer System

    Central hub for all MIDI synthesis functionality with complete
    XG specification compliance and GS compatibility.

    Features:
    - Unified sysex routing
    - XG part modes (Normal, Drum, Single)
    - Complete parameter handling
    - GS bank 127 drum support
    - Full XG Drum Map integration
    """

    # XG/GS Bank Constants
    BANK_NORMAL = 0  # Normal XG voices
    BANK_SFX = 64  # SFX voices
    BANK_AN = 126  # Analog modeling (S90/S70)
    BANK_FDSP = 127  # FDSP voices (S90/S70)
    BANK_GS_DRUM = 127  # GS Drum (conflicts with FDSP - use part mode to differentiate)

    # Default drum channel
    DEFAULT_DRUM_CHANNEL = 9  # MIDI channel 10

    def __init__(self, sample_rate: int = 44100, device_id: int = 0x10, max_polyphony: int = 128):
        """
        Initialize XG Synthesizer System.

        Args:
            sample_rate: Audio sample rate
            device_id: MIDI device ID
            max_polyphony: Maximum polyphony
        """
        self.sample_rate = sample_rate
        self.device_id = device_id
        self.max_polyphony = max_polyphony

        # Thread safety
        self.lock = threading.RLock()

        # Operating mode
        self.mode = SynthesizerMode()

        # Import and initialize components
        self._initialize_components()

        # Callbacks
        self._parameter_callbacks: list[Callable] = []
        self._system_callbacks: dict[str, Callable] = {}

        # Part configuration (16 parts)
        self.parts: dict[int, dict] = {}
        self._initialize_parts()

        # External references (set by parent synthesizer)
        self.synthesizer = None
        self.engine_registry = None
        self.effects_coordinator = None
        self.voice_manager = None

        logger.info(
            f"XGSynthesizerSystem: Initialized sample_rate={sample_rate}, device_id={device_id:02X}"
        )

    def _initialize_components(self):
        """Initialize all XG/GS components."""
        # Import unified sysex router
        from ..midi.unified_sysex_router import UnifiedSysexRouter

        self.sysex_router = UnifiedSysexRouter(self.device_id)

        # Import XG-specific components
        # Import GS components
        from ..gs.gs_sysex_handler import GSSysexHandler
        from ..xg.xg_channel_parameter_manager import XGChannelParameterManager
        from ..xg.xg_controller_assignments import XGControllerAssignments
        from ..xg.xg_drum_map import XGPartModeController
        from ..xg.xg_drum_setup_parameters import XGDrumSetupParameters
        from ..xg.xg_effects_enhancement import XGSystemEffectsEnhancement
        from ..xg.xg_micro_tuning import XGMicroTuning
        from ..xg.xg_multi_part_setup import XGMultiPartSetup
        from ..xg.xg_system_parameters import XGSystemEffectParameters

        # Initialize XG components
        self.xg_multi_part = XGMultiPartSetup(16)
        self.xg_drum_setup = XGDrumSetupParameters(16)
        self.xg_part_mode = XGPartModeController(16)
        self.xg_channel_params = XGChannelParameterManager(16)
        self.xg_system_params = XGSystemEffectParameters()
        self.xg_controllers = XGControllerAssignments(16)
        self.xg_effects = XGSystemEffectsEnhancement(self.sample_rate)
        self.xg_micro_tuning = XGMicroTuning(16)

        # Initialize GS handler
        self.gs_handler = GSSysexHandler(self.device_id)

        # Wire up sysex router with components
        self.sysex_router.set_xg_components(self._get_xg_component_manager())
        self.sysex_router.set_gs_components(self.gs_handler)

        # Set callbacks for parameter changes
        self._setup_callbacks()

    def _get_xg_component_manager(self):
        """Get component manager interface for sysex router."""

        # Create a simple component manager interface
        class XGComponentManager:
            def __init__(self, system):
                self.system = system

            def get_component(self, name: str):
                comp_map = {
                    "channel_params": self.system.xg_channel_params,
                    "multi_part": self.system.xg_multi_part,
                    "drum_setup": self.system.xg_drum_setup,
                    "drum_map": self.system.xg_part_mode.drum_map_manager,
                    "effect_router": None,  # Will add if needed
                    "controllers": self.system.xg_controllers,
                    "effects": self.system.xg_effects,
                    "system_params": self.system.xg_system_params,
                    "micro_tuning": self.system.xg_micro_tuning,
                    "realtime": None,
                    "compatibility": None,
                }
                return comp_map.get(name)

            def reset_all(self):
                self.system.reset_to_defaults()

        return XGComponentManager(self)

    def _setup_callbacks(self):
        """Setup callbacks for parameter changes."""
        # Forward parameter changes to callbacks
        self.xg_multi_part.set_parameter_change_callback(self._on_parameter_change)
        self.xg_drum_setup.set_parameter_change_callback(self._on_parameter_change)
        self.xg_part_mode.set_parameter_change_callback(self._on_parameter_change)
        self.xg_channel_params.reset_all_channels_to_xg_defaults()  # Initialize
        self.gs_handler.register_parameter_callback(self._on_parameter_change)

        # System callbacks
        self.sysex_router.register_system_callback("xg_on", self._on_xg_on)
        self.sysex_router.register_system_callback("xg_off", self._on_xg_off)
        self.sysex_router.register_system_callback("xg_reset", self._on_xg_reset)
        self.sysex_router.register_system_callback("gs_reset", self._on_gs_reset)
        self.sysex_router.register_system_callback("gm_on", self._on_gm_on)
        self.sysex_router.register_system_callback("gm2_on", self._on_gm2_on)

    def _on_parameter_change(self, *args):
        """Forward parameter changes to registered callbacks."""
        for callback in self._parameter_callbacks:
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Parameter callback error: {e}")

    def _on_xg_on(self):
        """Handle XG System On."""
        self.mode.xg_enabled = True
        self.mode.gs_enabled = False
        self.mode.gm_enabled = False
        self.mode.gm2_enabled = False
        logger.info("System: XG Mode enabled")

    def _on_xg_off(self):
        """Handle XG System Off."""
        self.mode.xg_enabled = False
        logger.info("System: XG Mode disabled")

    def _on_xg_reset(self):
        """Handle XG Reset."""
        self.reset_to_defaults()
        logger.info("System: XG Reset")

    def _on_gs_reset(self):
        """Handle GS Reset."""
        self.mode.gs_enabled = True
        self.mode.xg_enabled = False
        self.mode.gm_enabled = False
        self.mode.gm2_enabled = False
        self.gs_handler.reset()
        self.reset_to_defaults()
        logger.info("System: GS Mode enabled")

    def _on_gm_on(self):
        """Handle GM System On."""
        self.mode.gm_enabled = True
        self.mode.xg_enabled = False
        self.mode.gs_enabled = False
        self.mode.gm2_enabled = False
        self.reset_to_defaults()
        logger.info("System: GM Mode enabled")

    def _on_gm2_on(self):
        """Handle GM2 System On."""
        self.mode.gm2_enabled = True
        self.mode.gm_enabled = True
        self.mode.xg_enabled = False
        self.mode.gs_enabled = False
        self.reset_to_defaults()
        logger.info("System: GM2 Mode enabled")

    def _initialize_parts(self):
        """Initialize 16 parts with defaults."""
        for part_num in range(16):
            self.parts[part_num] = {
                "part_number": part_num,
                "channel": part_num,
                "bank_msb": 0,
                "bank_lsb": 0,
                "program": 0,
                "volume": 100,
                "pan": 64,
                "reverb_send": 40,
                "chorus_send": 0,
                "variation_send": 0,
                "part_mode": 0,  # 0=Normal, 1-3=Drum modes
                "drum_map": 0,  # 0=off, 1-4=Drum Maps
                "mute": False,
                "solo": False,
            }

        # Set default drum channel (part 9 = MIDI channel 10)
        self.parts[9]["part_mode"] = 1  # Drum mode
        self.parts[9]["drum_map"] = 1  # Drum Map 1

    def enable_xg_mode(self):
        """Enable XG mode."""
        self.mode.xg_enabled = True
        self.mode.gs_enabled = False
        self.mode.gm_enabled = False
        self.sysex_router.enable_xg()
        logger.info("XG mode enabled")

    def enable_gs_mode(self):
        """Enable GS mode."""
        self.mode.xg_enabled = False
        self.mode.gs_enabled = True
        self.mode.gm_enabled = False
        self.sysex_router.enable_gs()
        self.gs_handler.enable_gs()
        logger.info("GS mode enabled")

    def set_external_references(
        self,
        synthesizer: Any = None,
        engine_registry: Any = None,
        effects_coordinator: Any = None,
        voice_manager: Any = None,
    ):
        """Set external component references."""
        self.synthesizer = synthesizer
        self.engine_registry = engine_registry
        self.effects_coordinator = effects_coordinator
        self.voice_manager = voice_manager

        # Forward to components that need them
        if effects_coordinator:
            self.gs_handler.set_effects_coordinator(effects_coordinator)
            self.sysex_router.set_effects_coordinator(effects_coordinator)

        if voice_manager:
            self.gs_handler.set_voice_manager(voice_manager)

    def process_sysex(self, data: bytes) -> bytes | None:
        """
        Process sysex message through unified router.

        Args:
            data: Raw sysex bytes

        Returns:
            Optional response bytes
        """
        return self.sysex_router.process_message(data)

    def get_engine_for_part(self, part_num: int) -> str:
        """
        Get synthesis engine for a part based on bank and mode.

        Args:
            part_num: Part number (0-15)

        Returns:
            Engine type: 'xg', 'sf2', 'an', 'fdsp', 'drum'
        """
        if not (0 <= part_num < 16):
            return "xg"

        part = self.parts[part_num]

        # Check part mode first
        part_mode = part["part_mode"]
        if part_mode >= 1:  # Drum mode
            return "drum"

        # Check bank
        bank_msb = part["bank_msb"]

        if bank_msb == self.BANK_NORMAL:
            return "xg"  # Normal XG voices
        elif bank_msb == self.BANK_SFX:
            return "xg"  # SFX
        elif bank_msb == self.BANK_AN:
            return "an"  # Analog modeling
        elif bank_msb == self.BANK_FDSP:
            return "fdsp"  # FDSP

        # GS drum: check if this is the GS drum channel
        if self.mode.gs_enabled and part_num == 9:  # Channel 10
            return "drum"

        return "xg"

    def get_drum_mapping(
        self, part_num: int, note: int, velocity: int = 64
    ) -> tuple[int, dict | None]:
        """
        Get drum note mapping for a part.

        Args:
            part_num: Part number
            note: Input MIDI note
            velocity: Input velocity

        Returns:
            Tuple of (mapped_note, drum_entry)
        """
        if not (0 <= part_num < 16):
            return note, None

        part = self.parts[part_num]

        # Check if part is in drum mode
        if part["part_mode"] >= 1:
            # Use XG part mode controller for mapping
            return self.xg_part_mode.drum_map_manager.get_instrument_for_note(
                part_num, note, velocity
            )

        # Check GS mode
        if self.mode.gs_enabled and self.gs_handler.is_drum_part(part_num):
            # Use GS drum parameters
            # For now, return note as-is (GS drum mapping is complex)
            return note, None

        return note, None

    def set_part_mode(self, part_num: int, mode: int) -> bool:
        """
        Set part mode (Normal, Drum, Single).

        Args:
            part_num: Part number (0-15)
            mode: Mode (0=Normal, 1=Drum, 4=Single)

        Returns:
            True if successful
        """
        if not (0 <= part_num < 16):
            return False

        with self.lock:
            old_mode = self.parts[part_num]["part_mode"]
            self.parts[part_num]["part_mode"] = mode

            # Update XG part mode controller
            self.xg_part_mode.set_part_mode(part_num, mode)

            # If enabling drum mode, auto-select drum map
            if mode >= 1 and old_mode < 1:
                self.xg_part_mode.drum_map_manager.select_drum_map(part_num, 1)
                self.parts[part_num]["drum_map"] = 1

            # If disabling drum mode, clear drum map
            elif mode == 0 and old_mode >= 1:
                self.xg_part_mode.drum_map_manager.select_drum_map(part_num, 0)
                self.parts[part_num]["drum_map"] = 0

            logger.info(f"Part {part_num}: Mode set to {mode}")
            return True

    def set_part_bank(self, part_num: int, bank_msb: int, bank_lsb: int = 0) -> bool:
        """
        Set part bank (MSB/LSB).

        Args:
            part_num: Part number
            bank_msb: Bank MSB
            bank_lsb: Bank LSB

        Returns:
            True if successful
        """
        if not (0 <= part_num < 16):
            return False

        with self.lock:
            self.parts[part_num]["bank_msb"] = bank_msb
            self.parts[part_num]["bank_lsb"] = bank_lsb

            # Auto-detect drum mode based on bank 127
            if bank_msb == self.BANK_GS_DRUM:
                if self.parts[part_num]["part_mode"] == 0:
                    self.set_part_mode(part_num, 1)  # Enable drum mode

            return True

    def set_part_program(self, part_num: int, program: int) -> bool:
        """Set part program."""
        if not (0 <= part_num < 16):
            return False

        with self.lock:
            self.parts[part_num]["program"] = program
            return True

    def get_part_info(self, part_num: int) -> dict[str, Any]:
        """Get part information."""
        if not (0 <= part_num < 16):
            return {}

        part = self.parts[part_num]

        info = {
            "part_number": part_num,
            "channel": part["channel"],
            "bank": (part["bank_msb"] << 7) | part["bank_lsb"],
            "bank_msb": part["bank_msb"],
            "bank_lsb": part["bank_lsb"],
            "program": part["program"],
            "volume": part["volume"],
            "pan": part["pan"],
            "reverb_send": part["reverb_send"],
            "chorus_send": part["chorus_send"],
            "part_mode": part["part_mode"],
            "drum_map": part["drum_map"],
            "engine": self.get_engine_for_part(part_num),
            "mute": part["mute"],
            "solo": part["solo"],
        }

        # Add drum map info if in drum mode
        if part["part_mode"] >= 1:
            info["drum_map_info"] = self.xg_part_mode.drum_map_manager.get_drum_map_info(part_num)

        return info

    def get_all_parts_info(self) -> list[dict[str, Any]]:
        """Get information for all parts."""
        return [self.get_part_info(i) for i in range(16)]

    def reset_to_defaults(self):
        """Reset to XG/GS defaults."""
        with self.lock:
            # Reset XG components
            self.xg_multi_part.reset_to_xg_defaults()
            self.xg_drum_setup.reset_all_channels_to_defaults()
            self.xg_part_mode.reset_to_defaults()
            self.xg_channel_params.reset_all_channels_to_xg_defaults()
            self.xg_system_params.reset()

            # Reinitialize parts
            self._initialize_parts()

            logger.info("System: Reset to defaults")

    def register_parameter_callback(self, callback: Callable):
        """Register parameter change callback."""
        with self.lock:
            self._parameter_callbacks.append(callback)

    def get_status(self) -> dict[str, Any]:
        """Get system status."""
        return {
            "mode": {
                "xg": self.mode.xg_enabled,
                "gs": self.mode.gs_enabled,
                "gm": self.mode.gm_enabled,
                "gm2": self.mode.gm2_enabled,
            },
            "device_id": self.device_id,
            "sample_rate": self.sample_rate,
            "max_polyphony": self.max_polyphony,
            "sysex_router": self.sysex_router.get_status(),
            "gs_handler": self.gs_handler.get_status(),
            "parts": self.get_all_parts_info(),
        }

    def create_xg_message(self, command: int, data: list[int]) -> bytes:
        """Create XG sysex message."""
        return self.sysex_router.create_xg_message(command, data)

    def create_gs_message(self, command: int, address: tuple, data: list[int]) -> bytes:
        """Create GS sysex message."""
        return self.sysex_router.create_gs_message(command, address, data)

    # ========== MIDI Event Handlers ==========

    def handle_note_on(self, channel: int, note: int, velocity: int) -> tuple[int, dict | None]:
        """
        Handle note on with drum mapping.

        Returns:
            Tuple of (mapped_note, drum_params)
        """
        # Find part for channel
        part_num = channel  # Direct mapping for now

        if part_num >= 16:
            part_num = channel % 16

        # Check for drum mapping
        return self.get_drum_mapping(part_num, note, velocity)

    def handle_program_change(self, channel: int, program: int):
        """Handle program change."""
        part_num = channel if channel < 16 else channel % 16
        self.set_part_program(part_num, program)

    def handle_bank_select(self, channel: int, msb: int, lsb: int = 0):
        """Handle bank select."""
        part_num = channel if channel < 16 else channel % 16
        self.set_part_bank(part_num, msb, lsb)

    def handle_control_change(self, channel: int, controller: int, value: int):
        """Handle control change."""
        part_num = channel if channel < 16 else channel % 16

        with self.lock:
            if controller == 7:  # Volume
                self.parts[part_num]["volume"] = value
            elif controller == 10:  # Pan
                self.parts[part_num]["pan"] = value
            elif controller == 91:  # Reverb
                self.parts[part_num]["reverb_send"] = value
            elif controller == 93:  # Chorus
                self.parts[part_num]["chorus_send"] = value
            elif controller == 0:  # Bank Select MSB
                self.set_part_bank(part_num, value, self.parts[part_num]["bank_lsb"])
            elif controller == 32:  # Bank Select LSB
                self.set_part_bank(part_num, self.parts[part_num]["bank_msb"], value)
