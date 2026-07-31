"""

XG System - Yamaha XG Specification Implementation

Complete implementation of Yamaha XG music synthesis specification,
providing multi-part operation, effects management, and XG parameter control.

Part of S90/S70 compatibility - Core Infrastructure (Phase 1).
"""

from __future__ import annotations
import logging


import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Self

from .part_engine_router import PartEngineRouter


class XGParameterType(Enum):
    """XG parameter types"""

    SYSTEM = "system"
    MULTI_PART = "multi_part"
    DRUM_SETUP = "drum_setup"
    EFFECT = "effect"


class XGMultiPartMode(Enum):
    """XG multi-part modes"""

    MULTI_TIMBRAL = "multi_timbral"
    DRUM = "drum"
    PERFORMANCE = "performance"


@dataclass(slots=True)
class XGPart:
    """XG multi-part configuration"""

    part_number: int  # 0-15
    bank_select_msb: int = 0
    bank_select_lsb: int = 0
    program_number: int = 0
    channel: int = 0
    volume: int = 100
    pan: int = 64  # 0-127, 64=center
    chorus_send: int = 0
    reverb_send: int = 40
    variation_send: int = 0
    coarse_tune: int = 0  # -24 to +24 semitones
    fine_tune: int = 0  # -64 to +63 cents
    mono_poly_mode: int = 0  # 0=poly, 1=mono
    portamento_time: int = 0
    cutoff_frequency: int = 64
    resonance: int = 0
    attack_time: int = 64
    decay_time: int = 64
    release_time: int = 64
    vibrato_rate: int = 64
    vibrato_depth: int = 0
    vibrato_delay: int = 0
    part_mode: XGMultiPartMode = XGMultiPartMode.MULTI_TIMBRAL
    drum_note: int | None = None  # For drum parts
    rpn_msb: int = 0
    rpn_lsb: int = 0
    data_entry_msb: int = 0
    data_entry_lsb: int = 0
    engine_assignment: str = ""  # Explicit engine override (empty = use router)
    output_bus: int = 0  # Output bus assignment (0=Master, 1=A, 2=B, 3=C)


@dataclass(slots=True)
class XGSystemParameters:
    """XG system parameters"""

    system_on: bool = True
    master_volume: int = 100
    master_tune: int = 0  # -64 to +63 cents
    master_transpose: int = 0  # -24 to +24 semitones
    master_pan: int = 64
    reverb_type: int = 0
    reverb_return: int = 64
    reverb_pan: int = 64
    chorus_type: int = 0
    chorus_return: int = 64
    chorus_pan: int = 64
    chorus_reverb_send: int = 0
    chorus_to_reverb: int = 0
    variation_type: int = 0
    variation_return: int = 64
    variation_pan: int = 64
    variation_connection: int = 0
    variation_part: int = 0
    variation_mw_send: int = 0
    variation_bend_send: int = 0
    variation_cat_send: int = 0


class XGSystem:
    """
    XG System - Complete Yamaha XG Implementation

    Provides authentic XG multi-part operation, parameter management,
    effects routing, and drum setup functionality.
    """

    def __init__(self):
        """Initialize XG system"""
        self.system_params = XGSystemParameters()
        self.num_parts: int = 16
        self.parts: dict[int, XGPart] = {}
        self.drum_setup: dict[int, dict[str, Any]] = {}  # Note -> drum parameters

        # XG parameter ranges and defaults
        self._init_parameter_ranges()

        # Thread safety
        self.lock = threading.RLock()

        # PartEngineRouter for per-part engine routing
        self.engine_router: PartEngineRouter | None = None

        # Callbacks for parameter changes
        self.parameter_change_callback: Callable[[str, Any, Any], None] | None = None
        self.part_change_callback: Callable[[int, str, Any], None] | None = None

        # Initialize default multi-part setup
        self._init_default_parts()

    def _init_parameter_ranges(self):
        """Initialize XG parameter valid ranges"""
        self.parameter_ranges = {
            # System parameters
            "master_volume": (0, 127),
            "master_tune": (-64, 63),
            "master_transpose": (-24, 24),
            "master_pan": (0, 127),
            # Effect parameters
            "reverb_type": (0, 40),
            "reverb_return": (0, 127),
            "reverb_pan": (0, 127),
            "chorus_type": (0, 43),
            "chorus_return": (0, 127),
            "chorus_pan": (0, 127),
            "variation_type": (0, 80),
            "variation_return": (0, 127),
            "variation_pan": (0, 127),
            # Part parameters
            "volume": (0, 127),
            "pan": (0, 127),
            "chorus_send": (0, 127),
            "reverb_send": (0, 127),
            "variation_send": (0, 127),
            "coarse_tune": (-24, 24),
            "fine_tune": (-64, 63),
            "cutoff_frequency": (0, 127),
            "resonance": (0, 127),
            "attack_time": (0, 127),
            "decay_time": (0, 127),
            "release_time": (0, 127),
            "vibrato_rate": (0, 127),
            "vibrato_depth": (0, 127),
            "vibrato_delay": (0, 127),
        }

    def _init_default_parts(self):
        """Initialize default XG multi-part setup"""
        for part_num in range(min(16, self.num_parts)):  # Support up to num_parts
            part = XGPart(
                part_number=part_num,
                channel=part_num,  # Default: part N on channel N
                program_number=0,
                volume=100 if part_num == 0 else 0,  # Part 1 on, others off
                pan=64,
                reverb_send=40,
                chorus_send=0,
                variation_send=0,
                part_mode=XGMultiPartMode.DRUM if part_num == 9 else XGMultiPartMode.MULTI_TIMBRAL,
            )
            self.parts[part_num] = part

    def initialize(self):
        """Initialize XG system to default state"""
        with self.lock:
            self.system_params = XGSystemParameters()
            self._init_default_parts()
            self.drum_setup.clear()

    def reset(self):
        """Reset XG system to power-on defaults"""
        with self.lock:
            self.initialize()

    def set_engine_registry(self, registry) -> Self:
        """
        Set synthesis engine registry reference.

        Args:
            registry: Engine registry instance

        Returns:
            Self for method chaining
        """
        self.engine_registry = registry
        return self

    def set_effects_coordinator(self, coordinator) -> Self:
        """
        Set effects coordinator reference.

        Args:
            coordinator: Effects coordinator instance

        Returns:
            Self for method chaining
        """
        self.effects_coordinator = coordinator
        return self

    def get_engine_for_channel(self, channel: int) -> str:
        """
        Get synthesis engine type for a MIDI channel, delegating to PartEngineRouter.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Engine type string ('xg', 'an', 'fdsp', etc.)
        """
        with self.lock:
            # Find the part for this channel
            for part in self.parts.values():
                if part.channel == channel:
                    # Check explicit engine assignment first
                    if part.engine_assignment:
                        return part.engine_assignment
                    # Delegate to router
                    if self.engine_router is not None:
                        part_data = {
                            "bank_msb": part.bank_select_msb,
                            "bank_lsb": part.bank_select_lsb,
                            "program_num": part.program_number,
                            "part_mode": part.part_mode.value if hasattr(part.part_mode, "value") else 0,
                        }
                        return self.engine_router.get_part_engine(channel, part_data)

            return "xg"  # Default to XG engine

    def handle_program_change(self, channel: int, program: int):
        """
        Handle MIDI program change for XG system.

        Args:
            channel: MIDI channel
            program: Program number (0-127)
        """
        with self.lock:
            # Find part for this channel
            for part_num, part in self.parts.items():
                if part.channel == channel:
                    part.program_number = program
                    if self.part_change_callback:
                        self.part_change_callback(part_num, "program", program)
                    break

    def handle_control_change(self, channel: int, controller: int, value: int):
        """
        Handle MIDI control change for XG system.

        Args:
            channel: MIDI channel
            controller: Controller number
            value: Controller value
        """
        with self.lock:
            # XG system control changes
            if controller == 0:  # Bank Select MSB
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.bank_select_msb = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "bank_msb", value)
                        break

            elif controller == 32:  # Bank Select LSB
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.bank_select_lsb = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "bank_lsb", value)
                        break

            elif controller == 7:  # Channel Volume
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.volume = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "volume", value)
                        break

            elif controller == 10:  # Pan
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.pan = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "pan", value)
                        break

            elif controller == 91:  # Reverb Send
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.reverb_send = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "reverb_send", value)
                        break

            elif controller == 93:  # Chorus Send
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.chorus_send = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "chorus_send", value)
                        break

            elif controller == 94:  # Variation Send (XG specific)
                for part_num, part in self.parts.items():
                    if part.channel == channel:
                        part.variation_send = value
                        if self.part_change_callback:
                            self.part_change_callback(part_num, "variation_send", value)
                        break

    def set_system_parameter(self, parameter: str, value: Any) -> bool:
        """
        Set XG system parameter.

        Args:
            parameter: Parameter name
            value: Parameter value

        Returns:
            True if parameter set successfully
        """
        with self.lock:
            if hasattr(self.system_params, parameter):
                # Validate parameter range
                if parameter in self.parameter_ranges:
                    min_val, max_val = self.parameter_ranges[parameter]
                    if not (min_val <= value <= max_val):
                        return False

                old_value = getattr(self.system_params, parameter)
                setattr(self.system_params, parameter, value)

                if self.parameter_change_callback:
                    self.parameter_change_callback(f"system.{parameter}", old_value, value)

                return True
            return False

    def get_system_parameter(self, parameter: str) -> Any:
        """
        Get XG system parameter.

        Args:
            parameter: Parameter name

        Returns:
            Parameter value or None if not found
        """
        with self.lock:
            return getattr(self.system_params, parameter, None)

    def set_part_parameter(self, part_number: int, parameter: str, value: Any) -> bool:
        """
        Set parameter for specific part.

        Args:
            part_number: Part number (0-15)
            parameter: Parameter name
            value: Parameter value

        Returns:
            True if parameter set successfully
        """
        with self.lock:
            if part_number not in self.parts:
                return False

            part = self.parts[part_number]

            if hasattr(part, parameter):
                # Validate parameter range
                if parameter in self.parameter_ranges:
                    min_val, max_val = self.parameter_ranges[parameter]
                    if not (min_val <= value <= max_val):
                        return False

                old_value = getattr(part, parameter)
                setattr(part, parameter, value)

                if self.part_change_callback:
                    self.part_change_callback(part_number, parameter, value)

                return True
            return False

    def get_part_parameter(self, part_number: int, parameter: str) -> Any:
        """
        Get parameter for specific part.

        Args:
            part_number: Part number (0-15)
            parameter: Parameter name

        Returns:
            Parameter value or None if not found
        """
        with self.lock:
            if part_number in self.parts:
                return getattr(self.parts[part_number], parameter, None)
            return None

    def set_part_channel(self, part_number: int, channel: int) -> bool:
        """
        Assign part to MIDI channel.

        Args:
            part_number: Part number (0-15)
            channel: MIDI channel (0-15)

        Returns:
            True if assignment successful
        """
        with self.lock:
            if part_number not in self.parts or channel < 0 or channel > 15:
                return False

            # Check if channel is already assigned to another part
            for p_num, part in self.parts.items():
                if p_num != part_number and part.channel == channel:
                    # Reassign the other part to a free channel
                    part.channel = self._find_free_channel()

            self.parts[part_number].channel = channel
            return True

    def _find_free_channel(self) -> int:
        """Find a free MIDI channel"""
        used_channels = {part.channel for part in self.parts.values()}
        for channel in range(16):
            if channel not in used_channels:
                return channel
        return 15  # Fallback to channel 16

    def set_drum_note(self, part_number: int, note: int, parameters: dict[str, Any]):
        """
        Set drum note parameters for drum parts.

        Args:
            part_number: Part number (should be drum part)
            note: MIDI note number
            parameters: Drum parameters (level, pan, reverb, etc.)
        """
        with self.lock:
            if part_number not in self.parts:
                return

            part = self.parts[part_number]
            if part.part_mode != XGMultiPartMode.DRUM:
                return

            if note not in self.drum_setup:
                self.drum_setup[note] = {}

            self.drum_setup[note].update(parameters)

    def get_drum_parameters(self, note: int) -> dict[str, Any] | None:
        """
        Get drum parameters for a note.

        Args:
            note: MIDI note number

        Returns:
            Drum parameters or None
        """
        with self.lock:
            return self.drum_setup.get(note)

    def load_preset(self, preset_data: dict[str, Any]) -> bool:
        """
        Load XG preset data.

        Args:
            preset_data: Preset configuration

        Returns:
            True if loaded successfully
        """
        with self.lock:
            try:
                # Load system parameters
                if "system" in preset_data:
                    system_data = preset_data["system"]
                    for param, value in system_data.items():
                        self.set_system_parameter(param, value)

                # Load part parameters
                if "parts" in preset_data:
                    parts_data = preset_data["parts"]
                    for part_num, part_data in parts_data.items():
                        part_num = int(part_num)
                        for param, value in part_data.items():
                            self.set_part_parameter(part_num, param, value)

                # Load drum setup
                if "drum_setup" in preset_data:
                    self.drum_setup = preset_data["drum_setup"].copy()

                return True
            except Exception as e:
                logger.error(f"Error loading XG preset: {e}")
                return False

    def get_current_preset_data(self) -> dict[str, Any]:
        """
        Get current XG system state as preset data.

        Returns:
            Current configuration as dictionary
        """
        with self.lock:
            # Convert dataclasses to dict
            system_dict = {}
            for field_name in self.system_params.__dataclass_fields__:
                system_dict[field_name] = getattr(self.system_params, field_name)

            parts_dict = {}
            for part_num, part in self.parts.items():
                part_dict = {}
                for field_name in part.__dataclass_fields__:
                    value = getattr(part, field_name)
                    if isinstance(value, XGMultiPartMode):
                        value = value.value
                    part_dict[field_name] = value
                parts_dict[str(part_num)] = part_dict

            return {
                "system": system_dict,
                "parts": parts_dict,
                "drum_setup": self.drum_setup.copy(),
            }

    def get_multi_part_info(self) -> dict[str, Any]:
        """Get information about current multi-part setup"""
        with self.lock:
            channel_assignments = {}
            for part_num, part in self.parts.items():
                channel_assignments[part.channel] = {
                    "part_number": part_num,
                    "program": part.program_number,
                    "bank_msb": part.bank_select_msb,
                    "bank_lsb": part.bank_select_lsb,
                    "volume": part.volume,
                    "mode": part.part_mode.value,
                }

            return {
                "total_parts": len(self.parts),
                "active_parts": sum(1 for p in self.parts.values() if p.volume > 0),
                "channel_assignments": channel_assignments,
                "system_effects": {
                    "reverb_type": self.system_params.reverb_type,
                    "chorus_type": self.system_params.chorus_type,
                    "variation_type": self.system_params.variation_type,
                },
            }

    def validate_xg_data(self, data: dict[str, Any]) -> list[str]:
        """
        Validate XG data structure.

        Args:
            data: XG data to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Validate system parameters
        if "system" in data:
            system_data = data["system"]
            for param, value in system_data.items():
                if param in self.parameter_ranges:
                    min_val, max_val = self.parameter_ranges[param]
                    if not (min_val <= value <= max_val):
                        errors.append(f"System parameter {param} out of range: {value}")

        # Validate part parameters
        if "parts" in data:
            parts_data = data["parts"]
            for part_key, part_data in parts_data.items():
                try:
                    part_num = int(part_key)
                    if not (0 <= part_num <= 15):
                        errors.append(f"Invalid part number: {part_num}")
                        continue

                    for param, value in part_data.items():
                        if param in self.parameter_ranges:
                            min_val, max_val = self.parameter_ranges[param]
                            if not (min_val <= value <= max_val):
                                errors.append(
                                    f"Part {part_num} parameter {param} out of range: {value}"
                                )
                except ValueError:
                    errors.append(f"Invalid part key: {part_key}")

        return errors

    def get_xg_system_status(self) -> dict[str, Any]:
        """Return actual XG system state — only fields that exist on this class."""
        with self.lock:
            return {
                "system_on": self.system_params.system_on,
                "multi_part_info": self.get_multi_part_info(),
                "drum_notes_configured": len(self.drum_setup),
                "parameter_change_callback": self.parameter_change_callback is not None,
                "part_change_callback": self.part_change_callback is not None,
                "engine_registry_connected": hasattr(self, "engine_registry"),
                "effects_coordinator_connected": hasattr(self, "effects_coordinator"),
                "style_player_active": (
                    hasattr(self, "style_player") and self.style_player is not None
                ),
            }

    def set_parameter_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """
        Set callback for parameter changes.

        Args:
            callback: Function called when parameters change
        """
        self.parameter_change_callback = callback

    def set_parameter_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """
        Set callback for parameter changes.

        Args:
            callback: Function called when parameters change
        """
        self.parameter_change_callback = callback

    def set_part_change_callback(self, callback: Callable[[int, str, Any], None]):
        """
        Set callback for part changes.

        Args:
            callback: Function called when part parameters change
        """
        self.part_change_callback = callback

    # ===== Style Engine Integration =====

    def set_style_player(self, style_player: Any):
        """Set style player reference for auto-accompaniment"""
        self.style_player = style_player
        self.auto_accompaniment_enabled = True

    def get_style_player(self) -> Any:
        """Get style player instance"""
        return getattr(self, "style_player", None)

    def load_style(self, style: Any) -> bool:
        """Load a style into the style player"""
        player = self.get_style_player()
        if player:
            player.load_style(style)
            return True
        return False

    def start_accompaniment(self, section: str | None = None) -> bool:
        """Start auto-accompaniment"""
        player = self.get_style_player()
        if player:
            player.start()
            return True
        return False

    def stop_accompaniment(self) -> bool:
        """Stop auto-accompaniment"""
        player = self.get_style_player()
        if player:
            player.stop()
            return True
        return False

    def set_accompaniment_section(self, section: str) -> bool:
        """Set accompaniment section"""
        from synth.style import StyleSectionType

        player = self.get_style_player()
        if player:
            try:
                section_type = StyleSectionType(section)
                player.set_section(section_type)
                return True
            except ValueError:
                pass
        return False

    def trigger_accompaniment_fill(self) -> bool:
        """Trigger fill before section change"""
        player = self.get_style_player()
        if player:
            player.trigger_fill()
            return True
        return False

    def set_accompaniment_tempo(self, tempo: int) -> bool:
        """Set accompaniment tempo"""
        player = self.get_style_player()
        if player:
            player.tempo = tempo
            return True
        return False

    def set_style_dynamics(self, value: int) -> bool:
        """Set style dynamics (0-127)"""
        player = self.get_style_player()
        if player:
            player.set_dynamics(value)
            return True
        return False

    def process_style_midi(self, channel: int, note: int, velocity: int, is_note_on: bool = True):
        """Process MIDI through style player for chord detection"""
        player = self.get_style_player()
        if player and getattr(self, "auto_accompaniment_enabled", False):
            if is_note_on:
                player.process_midi_note_on(channel, note, velocity)
            else:
                player.process_midi_note_off(channel, note)

    def get_accompaniment_status(self) -> dict[str, Any]:
        """Get auto-accompaniment status"""
        player = self.get_style_player()
        if player:
            return player.get_status()
        return {
            "playing": False,
            "style_loaded": False,
            "auto_accompaniment_enabled": getattr(self, "auto_accompaniment_enabled", False),
        }
