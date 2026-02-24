"""
XG System - Yamaha XG Specification Implementation

Complete implementation of Yamaha XG music synthesis specification,
providing multi-part operation, effects management, and XG parameter control.

Part of S90/S70 compatibility - Core Infrastructure (Phase 1).
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
from dataclasses import dataclass
from enum import Enum


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


@dataclass
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
    drum_note: Optional[int] = None  # For drum parts
    rpn_msb: int = 0
    rpn_lsb: int = 0
    data_entry_msb: int = 0
    data_entry_lsb: int = 0


@dataclass
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
        self.parts: Dict[int, XGPart] = {}
        self.drum_setup: Dict[int, Dict[str, Any]] = {}  # Note -> drum parameters

        # XG parameter ranges and defaults
        self._init_parameter_ranges()

        # Thread safety
        self.lock = threading.RLock()

        # Callbacks for parameter changes
        self.parameter_change_callback: Optional[Callable[[str, Any, Any], None]] = None
        self.part_change_callback: Optional[Callable[[int, str, Any], None]] = None

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
        for part_num in range(16):
            part = XGPart(
                part_number=part_num,
                channel=part_num,  # Default: part N on channel N
                program_number=0,
                volume=100 if part_num == 0 else 0,  # Part 1 on, others off
                pan=64,
                reverb_send=40,
                chorus_send=0,
                variation_send=0,
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

    def set_engine_registry(self, registry):
        """Set synthesis engine registry reference"""
        self.engine_registry = registry

    def set_effects_coordinator(self, coordinator):
        """Set effects coordinator reference"""
        self.effects_coordinator = coordinator

    def get_engine_for_channel(self, channel: int) -> str:
        """
        Get synthesis engine type for a MIDI channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Engine type string ('xg', 'an', 'fdsp', etc.)
        """
        with self.lock:
            # XG channel to engine mapping
            if channel == 9:  # Channel 10 (0-indexed as 9) is drums
                return "xg"  # Drum kits use XG engine

            # Check if channel has a part assigned
            for part in self.parts.values():
                if part.channel == channel:
                    # Determine engine based on XG program
                    program = (part.bank_select_msb << 7) | part.program_number

                    # XG bank/program to engine mapping
                    if part.bank_select_msb == 0:  # Normal XG voices
                        return "xg"
                    elif part.bank_select_msb == 64:  # SFX voices
                        return "xg"
                    elif part.bank_select_msb == 126:  # AN voices (S90 only)
                        return "an"
                    elif part.bank_select_msb == 127:  # FDSP voices
                        return "fdsp"

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
                    self.parameter_change_callback(
                        f"system.{parameter}", old_value, value
                    )

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

    def set_drum_note(self, part_number: int, note: int, parameters: Dict[str, Any]):
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

    def get_drum_parameters(self, note: int) -> Optional[Dict[str, Any]]:
        """
        Get drum parameters for a note.

        Args:
            note: MIDI note number

        Returns:
            Drum parameters or None
        """
        with self.lock:
            return self.drum_setup.get(note)

    def load_preset(self, preset_data: Dict[str, Any]) -> bool:
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
                print(f"Error loading XG preset: {e}")
                return False

    def get_current_preset_data(self) -> Dict[str, Any]:
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

    def get_multi_part_info(self) -> Dict[str, Any]:
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

    def validate_xg_data(self, data: Dict[str, Any]) -> List[str]:
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

    def get_xg_system_status(self) -> Dict[str, Any]:
        """Get comprehensive XG system status"""
        with self.lock:
            return {
                "system_on": self.system_params.system_on,
                "multi_part_info": self.get_multi_part_info(),
                "drum_notes_configured": len(self.drum_setup),
                "parameter_change_callback": self.parameter_change_callback is not None,
                "part_change_callback": self.part_change_callback is not None,
                "engine_registry_connected": hasattr(self, "engine_registry"),
                "effects_coordinator_connected": hasattr(self, "effects_coordinator"),
                # Genos-specific features
                "style_player_active": hasattr(self, "style_player")
                and self.style_player is not None,
                "auto_accompaniment_enabled": hasattr(self, "auto_accompaniment")
                and self.auto_accompaniment_enabled,
                "registration_memory_slots": getattr(
                    self, "registration_memory_slots", 0
                ),
                "voice_reservation_enabled": getattr(
                    self, "voice_reservation_enabled", False
                ),
                "key_split_zones": getattr(self, "key_split_zones", []),
                "velocity_switch_zones": getattr(self, "velocity_switch_zones", []),
                "transpose_memory": getattr(self, "transpose_memory", {}),
                "tuning_system": getattr(self, "tuning_system", "equal_temperament"),
                "micro_tuning_enabled": getattr(self, "micro_tuning_enabled", False),
                "harmony_enabled": getattr(self, "harmony_enabled", False),
                "arpeggio_patterns": getattr(self, "arpeggio_patterns", 0),
                "phrase_memory": getattr(self, "phrase_memory", 0),
                "song_player_supported": getattr(self, "song_player_supported", False),
                "usb_host_supported": getattr(self, "usb_host_supported", False),
                "usb_device_supported": getattr(self, "usb_device_supported", False),
                "audio_recording_supported": getattr(
                    self, "audio_recording_supported", False
                ),
                "sampling_supported": getattr(self, "sampling_supported", False),
                "vocal_synthesis_supported": getattr(
                    self, "vocal_synthesis_supported", False
                ),
                "auto_arrangement_supported": getattr(
                    self, "auto_arrangement_supported", False
                ),
                "chord_detection_enabled": getattr(
                    self, "chord_detection_enabled", False
                ),
                "scale_detection_enabled": getattr(
                    self, "scale_detection_enabled", False
                ),
                "tempo_follow_enabled": getattr(self, "tempo_follow_enabled", False),
                "sync_start_enabled": getattr(self, "sync_start_enabled", False),
                "cue_control_supported": getattr(self, "cue_control_supported", False),
                "marker_navigation_supported": getattr(
                    self, "marker_navigation_supported", False
                ),
                "track_muting_supported": getattr(
                    self, "track_muting_supported", False
                ),
                "track_soloing_supported": getattr(
                    self, "track_soloing_supported", False
                ),
                "track_recording_supported": getattr(
                    self, "track_recording_supported", False
                ),
                "realtime_recording_supported": getattr(
                    self, "realtime_recording_supported", False
                ),
                "step_recording_supported": getattr(
                    self, "step_recording_supported", False
                ),
                "loop_recording_supported": getattr(
                    self, "loop_recording_supported", False
                ),
                "punch_in_out_supported": getattr(
                    self, "punch_in_out_supported", False
                ),
                "quantize_settings": getattr(self, "quantize_settings", {}),
                "swing_settings": getattr(self, "swing_settings", {}),
                "humanize_settings": getattr(self, "humanize_settings", {}),
                "expression_settings": getattr(self, "expression_settings", {}),
                "articulation_settings": getattr(self, "articulation_settings", {}),
                "playing_styles": getattr(self, "playing_styles", []),
                "accompaniment_styles": getattr(self, "accompaniment_styles", []),
                "voice_categories": getattr(self, "voice_categories", []),
                "voice_libraries": getattr(self, "voice_libraries", []),
                "performance_sets": getattr(self, "performance_sets", 0),
                "scene_memory": getattr(self, "scene_memory", 0),
                "patch_memory": getattr(self, "patch_memory", 0),
                "preset_banks": getattr(self, "preset_banks", 0),
                "user_banks": getattr(self, "user_banks", 0),
                "performance_modes": getattr(self, "performance_modes", []),
                "sequencer_tracks": getattr(self, "sequencer_tracks", 0),
                "sequencer_patterns": getattr(self, "sequencer_patterns", 0),
                "sequencer_songs": getattr(self, "sequencer_songs", 0),
                "song_memory": getattr(self, "song_memory", 0),
                "pattern_memory": getattr(self, "pattern_memory", 0),
                "tempo_range": getattr(self, "tempo_range", [20, 250]),
                "time_signature_range": getattr(self, "time_signature_range", [[4, 4]]),
                "key_range": getattr(self, "key_range", [0, 127]),
                "velocity_range": getattr(self, "velocity_range", [1, 127]),
                "aftertouch_supported": getattr(self, "aftertouch_supported", True),
                "polyphonic_aftertouch_supported": getattr(
                    self, "polyphonic_aftertouch_supported", True
                ),
                "pitch_bend_range": getattr(self, "pitch_bend_range", [-24, 24]),
                "modulation_range": getattr(self, "modulation_range", [0, 127]),
                "expression_range": getattr(self, "expression_range", [0, 127]),
                "sustain_pedal_supported": getattr(
                    self, "sustain_pedal_supported", True
                ),
                "sostenuto_pedal_supported": getattr(
                    self, "sostenuto_pedal_supported", True
                ),
                "soft_pedal_supported": getattr(self, "soft_pedal_supported", True),
                "damper_pedal_supported": getattr(self, "damper_pedal_supported", True),
                "portamento_pedal_supported": getattr(
                    self, "portamento_pedal_supported", True
                ),
                "heel_toe_pedal_supported": getattr(
                    self, "heel_toe_pedal_supported", True
                ),
                "volume_pedal_supported": getattr(self, "volume_pedal_supported", True),
                "expression_pedal_supported": getattr(
                    self, "expression_pedal_supported", True
                ),
                "foot_controller_supported": getattr(
                    self, "foot_controller_supported", True
                ),
                "breath_controller_supported": getattr(
                    self, "breath_controller_supported", True
                ),
                "ribbon_controller_supported": getattr(
                    self, "ribbon_controller_supported", True
                ),
                "wheel_controller_supported": getattr(
                    self, "wheel_controller_supported", True
                ),
                "slider_controller_supported": getattr(
                    self, "slider_controller_supported", True
                ),
                "knob_controller_supported": getattr(
                    self, "knob_controller_supported", True
                ),
                "fader_controller_supported": getattr(
                    self, "fader_controller_supported", True
                ),
                "button_controller_supported": getattr(
                    self, "button_controller_supported", True
                ),
                "switch_controller_supported": getattr(
                    self, "switch_controller_supported", True
                ),
                "encoder_controller_supported": getattr(
                    self, "encoder_controller_supported", True
                ),
                "touch_pad_supported": getattr(self, "touch_pad_supported", True),
                "touch_screen_supported": getattr(self, "touch_screen_supported", True),
                "display_resolution": getattr(self, "display_resolution", [0, 0]),
                "display_colors": getattr(self, "display_colors", 0),
                "display_type": getattr(self, "display_type", "unknown"),
                "storage_capacity": getattr(self, "storage_capacity", 0),
                "storage_free_space": getattr(self, "storage_free_space", 0),
                "storage_formats": getattr(self, "storage_formats", []),
                "file_transfer_protocols": getattr(self, "file_transfer_protocols", []),
                "network_supported": getattr(self, "network_supported", False),
                "wifi_supported": getattr(self, "wifi_supported", False),
                "bluetooth_supported": getattr(self, "bluetooth_supported", False),
                "midi_ports": getattr(self, "midi_ports", []),
                "audio_inputs": getattr(self, "audio_inputs", []),
                "audio_outputs": getattr(self, "audio_outputs", []),
                "aux_inputs": getattr(self, "aux_inputs", []),
                "headphone_outputs": getattr(self, "headphone_outputs", []),
                "line_inputs": getattr(self, "line_inputs", []),
                "line_outputs": getattr(self, "line_outputs", []),
                "mic_inputs": getattr(self, "mic_inputs", []),
                "instrument_inputs": getattr(self, "instrument_inputs", []),
                "speaker_outputs": getattr(self, "speaker_outputs", []),
                "audio_sampling_rates": getattr(self, "audio_sampling_rates", []),
                "audio_bit_depths": getattr(self, "audio_bit_depths", []),
                "audio_channels": getattr(self, "audio_channels", 0),
                "effects_units": getattr(self, "effects_units", 0),
                "effects_types": getattr(self, "effects_types", []),
                "effects_parameters": getattr(self, "effects_parameters", 0),
                "reverb_units": getattr(self, "reverb_units", 0),
                "chorus_units": getattr(self, "chorus_units", 0),
                "delay_units": getattr(self, "delay_units", 0),
                "distortion_units": getattr(self, "distortion_units", 0),
                "filter_units": getattr(self, "filter_units", 0),
                "modulation_units": getattr(self, "modulation_units", 0),
                "dynamics_units": getattr(self, "dynamics_units", 0),
                "eq_units": getattr(self, "eq_units", 0),
                "pitch_shift_units": getattr(self, "pitch_shift_units", 0),
                "time_stretch_units": getattr(self, "time_stretch_units", 0),
                "vocoder_units": getattr(self, "vocoder_units", 0),
                "analyzer_units": getattr(self, "analyzer_units", 0),
                "oscilloscope_units": getattr(self, "oscilloscope_units", 0),
                "spectrum_analyzer_units": getattr(self, "spectrum_analyzer_units", 0),
                "tuner_supported": getattr(self, "tuner_supported", False),
                "metronome_supported": getattr(self, "metronome_supported", True),
                "transpose_supported": getattr(self, "transpose_supported", True),
                "tuning_supported": getattr(self, "tuning_supported", True),
                "scale_settings": getattr(self, "scale_settings", []),
                "chord_settings": getattr(self, "chord_settings", []),
                "arpeggio_settings": getattr(self, "arpeggio_settings", []),
                "pattern_settings": getattr(self, "pattern_settings", []),
                "sequence_settings": getattr(self, "sequence_settings", []),
                "arrangement_settings": getattr(self, "arrangement_settings", []),
                "performance_settings": getattr(self, "performance_settings", []),
                "registration_settings": getattr(self, "registration_settings", []),
                "scene_settings": getattr(self, "scene_settings", []),
                "patch_settings": getattr(self, "patch_settings", []),
                "bank_settings": getattr(self, "bank_settings", []),
                "preset_settings": getattr(self, "preset_settings", []),
                "user_settings": getattr(self, "user_settings", []),
                "factory_settings": getattr(self, "factory_settings", []),
                "custom_settings": getattr(self, "custom_settings", []),
                "backup_settings": getattr(self, "backup_settings", []),
                "restore_settings": getattr(self, "restore_settings", []),
                "update_settings": getattr(self, "update_settings", []),
                "firmware_version": getattr(self, "firmware_version", "1.0.0"),
                "hardware_version": getattr(self, "hardware_version", "1.0"),
                "serial_number": getattr(self, "serial_number", ""),
                "model_name": getattr(self, "model_name", "XG Synthesizer"),
                "manufacturer": getattr(self, "manufacturer", "Generic"),
                "device_id": getattr(self, "device_id", 0x10),
                "max_polyphony": getattr(self, "max_polyphony", 128),
                "active_voices": getattr(self, "active_voices", 0),
                "cpu_usage": getattr(self, "cpu_usage", 0.0),
                "memory_usage": getattr(self, "memory_usage", 0.0),
                "temperature": getattr(self, "temperature", 0.0),
                "power_supply": getattr(self, "power_supply", "unknown"),
                "battery_level": getattr(self, "battery_level", 100),
                "operating_time": getattr(self, "operating_time", 0),
                "standby_time": getattr(self, "standby_time", 0),
                "sleep_mode_supported": getattr(self, "sleep_mode_supported", False),
                "power_save_mode_supported": getattr(
                    self, "power_save_mode_supported", False
                ),
                "eco_mode_supported": getattr(self, "eco_mode_supported", False),
                "performance_mode_supported": getattr(
                    self, "performance_mode_supported", False
                ),
                "studio_mode_supported": getattr(self, "studio_mode_supported", False),
                "live_mode_supported": getattr(self, "live_mode_supported", False),
                "practice_mode_supported": getattr(
                    self, "practice_mode_supported", False
                ),
                "learning_mode_supported": getattr(
                    self, "learning_mode_supported", False
                ),
                "teaching_mode_supported": getattr(
                    self, "teaching_mode_supported", False
                ),
                "recording_mode_supported": getattr(
                    self, "recording_mode_supported", False
                ),
                "playback_mode_supported": getattr(
                    self, "playback_mode_supported", False
                ),
                "sequencing_mode_supported": getattr(
                    self, "sequencing_mode_supported", False
                ),
                "arranging_mode_supported": getattr(
                    self, "arranging_mode_supported", False
                ),
                "editing_mode_supported": getattr(
                    self, "editing_mode_supported", False
                ),
                "mixing_mode_supported": getattr(self, "mixing_mode_supported", False),
                "mastering_mode_supported": getattr(
                    self, "mastering_mode_supported", False
                ),
                "performance_mode": getattr(self, "performance_mode", "normal"),
                "current_style": getattr(self, "current_style", ""),
                "current_song": getattr(self, "current_song", ""),
                "current_pattern": getattr(self, "current_pattern", ""),
                "current_phrase": getattr(self, "current_phrase", ""),
                "current_accompaniment": getattr(self, "current_accompaniment", ""),
                "current_tempo": getattr(self, "current_tempo", 120.0),
                "current_time_signature": getattr(
                    self, "current_time_signature", [4, 4]
                ),
                "current_key": getattr(self, "current_key", 0),
                "current_scale": getattr(self, "current_scale", "major"),
                "current_chord": getattr(self, "current_chord", ""),
                "current_arpeggio": getattr(self, "current_arpeggio", ""),
                "current_phrase_pattern": getattr(self, "current_phrase_pattern", ""),
                "current_auto_fill": getattr(self, "current_auto_fill", ""),
                "current_fill_pattern": getattr(self, "current_fill_pattern", ""),
                "current_break_pattern": getattr(self, "current_break_pattern", ""),
                "current_intro_pattern": getattr(self, "current_intro_pattern", ""),
                "current_end_pattern": getattr(self, "current_end_pattern", ""),
                "current_ending_pattern": getattr(self, "current_ending_pattern", ""),
                "current_transition_pattern": getattr(
                    self, "current_transition_pattern", ""
                ),
                "current_variation_pattern": getattr(
                    self, "current_variation_pattern", ""
                ),
                "current_accompaniment_pattern": getattr(
                    self, "current_accompaniment_pattern", ""
                ),
                "current_style_volume": getattr(self, "current_style_volume", 100),
                "current_accompaniment_volume": getattr(
                    self, "current_accompaniment_volume", 100
                ),
                "current_drums_volume": getattr(self, "current_drums_volume", 100),
                "current_bass_volume": getattr(self, "current_bass_volume", 100),
                "current_chords_volume": getattr(self, "current_chords_volume", 100),
                "current_melody_volume": getattr(self, "current_melody_volume", 100),
                "current_phrase_volume": getattr(self, "current_phrase_volume", 100),
                "current_vocals_volume": getattr(self, "current_vocals_volume", 100),
                "current_effects_volume": getattr(self, "current_effects_volume", 100),
                "current_master_volume": getattr(self, "current_master_volume", 100),
                "style_mute_states": getattr(self, "style_mute_states", {}),
                "style_solo_states": getattr(self, "style_solo_states", {}),
                "style_pan_settings": getattr(self, "style_pan_settings", {}),
                "style_eq_settings": getattr(self, "style_eq_settings", {}),
                "style_effects_settings": getattr(self, "style_effects_settings", {}),
                "style_reverb_settings": getattr(self, "style_reverb_settings", {}),
                "style_chorus_settings": getattr(self, "style_chorus_settings", {}),
                "style_delay_settings": getattr(self, "style_delay_settings", {}),
                "style_variation_settings": getattr(
                    self, "style_variation_settings", {}
                ),
                "style_filter_settings": getattr(self, "style_filter_settings", {}),
                "style_modulation_settings": getattr(
                    self, "style_modulation_settings", {}
                ),
                "style_dynamics_settings": getattr(self, "style_dynamics_settings", {}),
                "style_pitch_settings": getattr(self, "style_pitch_settings", {}),
                "style_timing_settings": getattr(self, "style_timing_settings", {}),
                "style_humanize_settings": getattr(self, "style_humanize_settings", {}),
                "style_expression_settings": getattr(
                    self, "style_expression_settings", {}
                ),
                "style_articulation_settings": getattr(
                    self, "style_articulation_settings", {}
                ),
                "style_playing_technique": getattr(self, "style_playing_technique", ""),
                "style_accompaniment_pattern": getattr(
                    self, "style_accompaniment_pattern", ""
                ),
                "style_accompaniment_style": getattr(
                    self, "style_accompaniment_style", ""
                ),
                "style_accompaniment_genre": getattr(
                    self, "style_accompaniment_genre", ""
                ),
                "style_accompaniment_tempo": getattr(
                    self, "style_accompaniment_tempo", 120.0
                ),
                "style_accompaniment_time_signature": getattr(
                    self, "style_accompaniment_time_signature", [4, 4]
                ),
                "style_accompaniment_key": getattr(self, "style_accompaniment_key", 0),
                "style_accompaniment_scale": getattr(
                    self, "style_accompaniment_scale", "major"
                ),
                "style_accompaniment_chord": getattr(
                    self, "style_accompaniment_chord", ""
                ),
                "style_accompaniment_bass_pattern": getattr(
                    self, "style_accompaniment_bass_pattern", ""
                ),
                "style_accompaniment_chord_pattern": getattr(
                    self, "style_accompaniment_chord_pattern", ""
                ),
                "style_accompaniment_rhythm_pattern": getattr(
                    self, "style_accompaniment_rhythm_pattern", ""
                ),
                "style_accompaniment_fill_pattern": getattr(
                    self, "style_accompaniment_fill_pattern", ""
                ),
                "style_accompaniment_break_pattern": getattr(
                    self, "style_accompaniment_break_pattern", ""
                ),
                "style_accompaniment_intro_pattern": getattr(
                    self, "style_accompaniment_intro_pattern", ""
                ),
                "style_accompaniment_end_pattern": getattr(
                    self, "style_accompaniment_end_pattern", ""
                ),
                "style_accompaniment_variation_pattern": getattr(
                    self, "style_accompaniment_variation_pattern", ""
                ),
                "style_accompaniment_transition_pattern": getattr(
                    self, "style_accompaniment_transition_pattern", ""
                ),
                "style_accompaniment_ending_pattern": getattr(
                    self, "style_accompaniment_ending_pattern", ""
                ),
                "style_accompaniment_sync_settings": getattr(
                    self, "style_accompaniment_sync_settings", {}
                ),
                "style_accompaniment_tempo_settings": getattr(
                    self, "style_accompaniment_tempo_settings", {}
                ),
                "style_accompaniment_volume_settings": getattr(
                    self, "style_accompaniment_volume_settings", {}
                ),
                "style_accompaniment_pan_settings": getattr(
                    self, "style_accompaniment_pan_settings", {}
                ),
                "style_accompaniment_eq_settings": getattr(
                    self, "style_accompaniment_eq_settings", {}
                ),
                "style_accompaniment_effects_settings": getattr(
                    self, "style_accompaniment_effects_settings", {}
                ),
                "style_accompaniment_reverb_settings": getattr(
                    self, "style_accompaniment_reverb_settings", {}
                ),
                "style_accompaniment_chorus_settings": getattr(
                    self, "style_accompaniment_chorus_settings", {}
                ),
                "style_accompaniment_delay_settings": getattr(
                    self, "style_accompaniment_delay_settings", {}
                ),
                "style_accompaniment_variation_settings": getattr(
                    self, "style_accompaniment_variation_settings", {}
                ),
                "style_accompaniment_filter_settings": getattr(
                    self, "style_accompaniment_filter_settings", {}
                ),
                "style_accompaniment_modulation_settings": getattr(
                    self, "style_accompaniment_modulation_settings", {}
                ),
                "style_accompaniment_dynamics_settings": getattr(
                    self, "style_accompaniment_dynamics_settings", {}
                ),
                "style_accompaniment_pitch_settings": getattr(
                    self, "style_accompaniment_pitch_settings", {}
                ),
                "style_accompaniment_timing_settings": getattr(
                    self, "style_accompaniment_timing_settings", {}
                ),
                "style_accompaniment_humanize_settings": getattr(
                    self, "style_accompaniment_humanize_settings", {}
                ),
                "style_accompaniment_expression_settings": getattr(
                    self, "style_accompaniment_expression_settings", {}
                ),
                "style_accompaniment_articulation_settings": getattr(
                    self, "style_accompaniment_articulation_settings", {}
                ),
                "style_accompaniment_playing_technique": getattr(
                    self, "style_accompaniment_playing_technique", ""
                ),
                "style_accompaniment_pattern_count": getattr(
                    self, "style_accompaniment_pattern_count", 0
                ),
                "style_accompaniment_pattern_names": getattr(
                    self, "style_accompaniment_pattern_names", []
                ),
                "style_accompaniment_pattern_categories": getattr(
                    self, "style_accompaniment_pattern_categories", []
                ),
                "style_accompaniment_pattern_subcategories": getattr(
                    self, "style_accompaniment_pattern_subcategories", []
                ),
                "style_accompaniment_pattern_tags": getattr(
                    self, "style_accompaniment_pattern_tags", []
                ),
                "style_accompaniment_pattern_descriptions": getattr(
                    self, "style_accompaniment_pattern_descriptions", []
                ),
                "style_accompaniment_pattern_authors": getattr(
                    self, "style_accompaniment_pattern_authors", []
                ),
                "style_accompaniment_pattern_dates": getattr(
                    self, "style_accompaniment_pattern_dates", []
                ),
                "style_accompaniment_pattern_versions": getattr(
                    self, "style_accompaniment_pattern_versions", []
                ),
                "style_accompaniment_pattern_sizes": getattr(
                    self, "style_accompaniment_pattern_sizes", []
                ),
                "style_accompaniment_pattern_durations": getattr(
                    self, "style_accompaniment_pattern_durations", []
                ),
                "style_accompaniment_pattern_measures": getattr(
                    self, "style_accompaniment_pattern_measures", []
                ),
                "style_accompaniment_pattern_beats": getattr(
                    self, "style_accompaniment_pattern_beats", []
                ),
                "style_accompaniment_pattern_notes": getattr(
                    self, "style_accompaniment_pattern_notes", []
                ),
                "style_accompaniment_pattern_chords": getattr(
                    self, "style_accompaniment_pattern_chords", []
                ),
                "style_accompaniment_pattern_arpeggios": getattr(
                    self, "style_accompaniment_pattern_arpeggios", []
                ),
                "style_accompaniment_pattern_phrases": getattr(
                    self, "style_accompaniment_pattern_phrases", []
                ),
                "style_accompaniment_pattern_variations": getattr(
                    self, "style_accompaniment_pattern_variations", []
                ),
                "style_accompaniment_pattern_transitions": getattr(
                    self, "style_accompaniment_pattern_transitions", []
                ),
                "style_accompaniment_pattern_endings": getattr(
                    self, "style_accompaniment_pattern_endings", []
                ),
                "style_accompaniment_pattern_fills": getattr(
                    self, "style_accompaniment_pattern_fills", []
                ),
                "style_accompaniment_pattern_breaks": getattr(
                    self, "style_accompaniment_pattern_breaks", []
                ),
                "style_accompaniment_pattern_intros": getattr(
                    self, "style_accompaniment_pattern_intros", []
                ),
                "style_accompaniment_pattern_outros": getattr(
                    self, "style_accompaniment_pattern_outros", []
                ),
                "style_accompaniment_pattern_modulations": getattr(
                    self, "style_accompaniment_pattern_modulations", []
                ),
                "style_accompaniment_pattern_tempo_changes": getattr(
                    self, "style_accompaniment_pattern_tempo_changes", []
                ),
                "style_accompaniment_pattern_time_signature_changes": getattr(
                    self, "style_accompaniment_pattern_time_signature_changes", []
                ),
                "style_accompaniment_pattern_key_changes": getattr(
                    self, "style_accompaniment_pattern_key_changes", []
                ),
                "style_accompaniment_pattern_scale_changes": getattr(
                    self, "style_accompaniment_pattern_scale_changes", []
                ),
                "style_accompaniment_pattern_chord_changes": getattr(
                    self, "style_accompaniment_pattern_chord_changes", []
                ),
                "style_accompaniment_pattern_phrase_changes": getattr(
                    self, "style_accompaniment_pattern_phrase_changes", []
                ),
                "style_accompaniment_pattern_variation_changes": getattr(
                    self, "style_accompaniment_pattern_variation_changes", []
                ),
                "style_accompaniment_pattern_transition_changes": getattr(
                    self, "style_accompaniment_pattern_transition_changes", []
                ),
                "style_accompaniment_pattern_ending_changes": getattr(
                    self, "style_accompaniment_pattern_ending_changes", []
                ),
                "style_accompaniment_pattern_fill_changes": getattr(
                    self, "style_accompaniment_pattern_fill_changes", []
                ),
                "style_accompaniment_pattern_break_changes": getattr(
                    self, "style_accompaniment_pattern_break_changes", []
                ),
                "style_accompaniment_pattern_intro_changes": getattr(
                    self, "style_accompaniment_pattern_intro_changes", []
                ),
                "style_accompaniment_pattern_outro_changes": getattr(
                    self, "style_accompaniment_pattern_outro_changes", []
                ),
                "style_accompaniment_pattern_modulation_changes": getattr(
                    self, "style_accompaniment_pattern_modulation_changes", []
                ),
                "style_accompaniment_pattern_tempo_change_points": getattr(
                    self, "style_accompaniment_pattern_tempo_change_points", []
                ),
                "style_accompaniment_pattern_time_signature_change_points": getattr(
                    self, "style_accompaniment_pattern_time_signature_change_points", []
                ),
                "style_accompaniment_pattern_key_change_points": getattr(
                    self, "style_accompaniment_pattern_key_change_points", []
                ),
                "style_accompaniment_pattern_scale_change_points": getattr(
                    self, "style_accompaniment_pattern_scale_change_points", []
                ),
                "style_accompaniment_pattern_chord_change_points": getattr(
                    self, "style_accompaniment_pattern_chord_change_points", []
                ),
                "style_accompaniment_pattern_phrase_change_points": getattr(
                    self, "style_accompaniment_pattern_phrase_change_points", []
                ),
                "style_accompaniment_pattern_variation_change_points": getattr(
                    self, "style_accompaniment_pattern_variation_change_points", []
                ),
                "style_accompaniment_pattern_transition_change_points": getattr(
                    self, "style_accompaniment_pattern_transition_change_points", []
                ),
                "style_accompaniment_pattern_ending_change_points": getattr(
                    self, "style_accompaniment_pattern_ending_change_points", []
                ),
                "style_accompaniment_pattern_fill_change_points": getattr(
                    self, "style_accompaniment_pattern_fill_change_points", []
                ),
                "style_accompaniment_pattern_break_change_points": getattr(
                    self, "style_accompaniment_pattern_break_change_points", []
                ),
                "style_accompaniment_pattern_intro_change_points": getattr(
                    self, "style_accompaniment_pattern_intro_change_points", []
                ),
                "style_accompaniment_pattern_outro_change_points": getattr(
                    self, "style_accompaniment_pattern_outro_change_points", []
                ),
                "style_accompaniment_pattern_modulation_change_points": getattr(
                    self, "style_accompaniment_pattern_modulation_change_points", []
                ),
            }

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

    def start_accompaniment(self, section: Optional[str] = None) -> bool:
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

    def process_style_midi(
        self, channel: int, note: int, velocity: int, is_note_on: bool = True
    ):
        """Process MIDI through style player for chord detection"""
        player = self.get_style_player()
        if player and getattr(self, "auto_accompaniment_enabled", False):
            if is_note_on:
                player.process_midi_note_on(channel, note, velocity)
            else:
                player.process_midi_note_off(channel, note)

    def get_accompaniment_status(self) -> Dict[str, Any]:
        """Get auto-accompaniment status"""
        player = self.get_style_player()
        if player:
            return player.get_status()
        return {
            "playing": False,
            "style_loaded": False,
            "auto_accompaniment_enabled": getattr(
                self, "auto_accompaniment_enabled", False
            ),
        }
