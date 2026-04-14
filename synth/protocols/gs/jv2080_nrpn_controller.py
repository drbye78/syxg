"""
JV-2080 NRPN (Non-Registered Parameter Number) Controller

Full NRPN parameter control system for JV-2080 enhanced GS implementation,
providing comprehensive parameter access via MIDI NRPN messages.
"""

from __future__ import annotations

import threading
from typing import Any


class JV2080NRPNController:
    """
    JV-2080 NRPN Parameter Control System

    Implements the full NRPN parameter matrix for JV-2080, allowing
    comprehensive control of all synthesizer parameters via MIDI.
    """

    def __init__(self, component_manager):
        """
        Initialize NRPN controller.

        Args:
            component_manager: JV2080ComponentManager instance
        """
        self.component_manager = component_manager

        # NRPN State
        self.active_nrpn = False
        self.current_msb = 0  # NRPN MSB (0-127)
        self.current_lsb = 0  # NRPN LSB (0-127)
        self.data_msb = 0  # Data MSB (0-127)
        self.data_msb_received = False

        # Parameter Map - Complete JV-2080 NRPN address space
        self.parameter_map = self._build_parameter_map()

        # Thread safety
        self.lock = threading.RLock()

    def _build_parameter_map(self) -> dict[tuple[int, int], dict[str, Any]]:
        """
        Build comprehensive NRPN parameter map.

        JV-2080 uses a structured address space:
        - 0x01,0x00-0x0F: System parameters
        - 0x18-0x2F,0x00-0x1F: Part parameters (16 parts × 32 params)
        - 0x03,0x00-0x0F: Reverb parameters
        - 0x04,0x00-0x0F: Chorus parameters
        - 0x05,0x00-0x1F: MFX parameters
        - 0x40-0x5F,0x00-0x1F: Insert effect parameters
        """
        param_map = {}

        # System Parameters (0x01, 0x00-0x0F)
        system_params = {
            0x00: {"name": "master_tune", "range": (-24, 24), "default": 0, "unit": "semitones"},
            0x01: {"name": "master_volume", "range": (0, 127), "default": 100, "unit": "level"},
            0x02: {"name": "master_pan", "range": (-64, 63), "default": 0, "unit": "pan"},
            0x03: {
                "name": "master_coarse_tune",
                "range": (-24, 24),
                "default": 0,
                "unit": "semitones",
            },
            0x04: {"name": "master_fine_tune", "range": (-50, 50), "default": 0, "unit": "cents"},
            0x05: {"name": "reverb_send_level", "range": (0, 127), "default": 0, "unit": "level"},
            0x06: {"name": "chorus_send_level", "range": (0, 127), "default": 0, "unit": "level"},
            0x07: {"name": "delay_send_level", "range": (0, 127), "default": 0, "unit": "level"},
            0x08: {"name": "mfx_send_level", "range": (0, 127), "default": 0, "unit": "level"},
            0x09: {"name": "device_id", "range": (0, 31), "default": 16, "unit": "id"},
            0x0A: {"name": "midi_channel", "range": (0, 15), "default": 0, "unit": "channel"},
            0x0B: {"name": "local_control", "range": (0, 1), "default": 1, "unit": "on/off"},
            0x0C: {"name": "program_change_mode", "range": (0, 1), "default": 1, "unit": "on/off"},
            0x0D: {"name": "lcd_contrast", "range": (0, 15), "default": 8, "unit": "level"},
            0x0E: {"name": "led_brightness", "range": (0, 15), "default": 8, "unit": "level"},
        }

        for lsb, param_info in system_params.items():
            param_map[(0x01, lsb)] = param_info

        # Part Parameters (0x18-0x2F, 0x00-0x1F)
        # 16 parts (0x18 to 0x2F) × 32 parameters (0x00 to 0x1F)
        part_param_names = [
            "instrument_lsb",
            "instrument_msb",
            "volume",
            "pan",
            "coarse_tune",
            "fine_tune",
            "reverb_send",
            "chorus_send",
            "delay_send",
            "mfx_send",
            "insert_effect_assign",
            "key_range_low",
            "key_range_high",
            "velocity_range_low",
            "velocity_range_high",
            "receive_channel",
            "polyphony_mode",
            "portamento_time",
            "reserved_18",
            "reserved_19",
            "reserved_1A",
            "reserved_1B",
            "reserved_1C",
            "reserved_1D",
            "reserved_1E",
            "reserved_1F",
            "reserved_20",
            "reserved_21",
            "reserved_22",
            "reserved_23",
            "reserved_24",
            "reserved_25",
        ]

        for part_offset in range(16):  # 16 parts
            msb = 0x18 + part_offset
            for lsb in range(32):  # 32 parameters per part
                param_name = f"part_{part_offset}_{part_param_names[lsb % len(part_param_names)]}"
                param_map[(msb, lsb)] = {
                    "name": param_name,
                    "part": part_offset,
                    "param_id": lsb,
                    "range": (0, 127),
                    "default": 64,
                    "unit": "value",
                }

        # Reverb Parameters (0x03, 0x00-0x0F)
        reverb_params = {
            0x00: {"name": "reverb_type", "range": (0, 7), "default": 0, "unit": "type"},
            0x01: {"name": "reverb_level", "range": (0, 127), "default": 64, "unit": "level"},
            0x02: {"name": "reverb_time", "range": (0, 127), "default": 64, "unit": "time"},
            0x03: {"name": "reverb_feedback", "range": (0, 127), "default": 0, "unit": "feedback"},
            0x04: {"name": "reverb_pre_delay", "range": (0, 127), "default": 0, "unit": "time"},
            0x05: {
                "name": "reverb_high_freq_damp",
                "range": (0, 127),
                "default": 64,
                "unit": "freq",
            },
            0x06: {"name": "reverb_low_freq_damp", "range": (0, 127), "default": 0, "unit": "freq"},
            0x07: {"name": "reverb_balance", "range": (-64, 63), "default": 0, "unit": "balance"},
        }

        for lsb, param_info in reverb_params.items():
            param_map[(0x03, lsb)] = param_info

        # Chorus Parameters (0x04, 0x00-0x0F)
        chorus_params = {
            0x00: {"name": "chorus_type", "range": (0, 7), "default": 0, "unit": "type"},
            0x01: {"name": "chorus_level", "range": (0, 127), "default": 64, "unit": "level"},
            0x02: {"name": "chorus_rate", "range": (0, 127), "default": 64, "unit": "rate"},
            0x03: {"name": "chorus_depth", "range": (0, 127), "default": 64, "unit": "depth"},
            0x04: {"name": "chorus_pre_delay", "range": (0, 127), "default": 0, "unit": "time"},
            0x05: {"name": "chorus_feedback", "range": (0, 127), "default": 0, "unit": "feedback"},
            0x06: {"name": "chorus_balance", "range": (-64, 63), "default": 0, "unit": "balance"},
        }

        for lsb, param_info in chorus_params.items():
            param_map[(0x04, lsb)] = param_info

        # MFX Parameters (0x05, 0x00-0x1F)
        # 32 MFX parameters (type + 31 effect parameters)
        mfx_params = {0x00: {"name": "mfx_type", "range": (0, 40), "default": 0, "unit": "type"}}
        for i in range(1, 32):
            mfx_params[0x00 + i] = {
                "name": f"mfx_param_{i}",
                "range": (0, 127),
                "default": 64,
                "unit": "value",
            }

        for lsb, param_info in mfx_params.items():
            param_map[(0x05, lsb)] = param_info

        # Insert Effect Parameters (0x40-0x47, 0x00-0x0F)
        # 8 insert effects × 16 parameters each
        for insert_num in range(8):
            msb = 0x40 + insert_num
            for param_num in range(16):
                param_map[(msb, param_num)] = {
                    "name": f"insert_{insert_num}_param_{param_num}",
                    "insert_effect": insert_num,
                    "param_id": param_num,
                    "range": (0, 127),
                    "default": 64,
                    "unit": "value",
                }

        # ===== JUPITER-X INTEGRATION PARAMETERS =====

        # Jupiter-X Engine Parameters (0x48-0x5F, 0x00-0x1F)
        # 16 parts × 4 engines × 32 parameters per engine
        # MSB range: 0x48-0x5F (72-95)
        engine_param_names = [
            # Analog Engine (0x00-0x0F)
            "osc1_waveform",
            "osc1_coarse_tune",
            "osc1_fine_tune",
            "osc1_level",
            "osc1_supersaw_spread",
            "osc2_waveform",
            "osc2_coarse_tune",
            "osc2_fine_tune",
            "osc2_level",
            "osc2_detune",
            "osc2_ring_mod",
            "filter_type",
            "filter_cutoff",
            "filter_resonance",
            "filter_env_amount",
            "amp_attack",
            "amp_decay",
            "amp_sustain",
            "amp_release",
            "filter_attack",
            "filter_decay",
            "filter_sustain",
            "filter_release",
            "lfo_waveform",
            "lfo_rate",
            "lfo_depth",
            "lfo_phase_offset",
            "lfo_fade_in",
            "lfo_key_sync",
            "env_attack_curve",
            "env_decay_curve",
            "env_release_curve",
            # Digital/FM/External Engine parameters (0x10-0x1F)
            "engine_param_16",
            "engine_param_17",
            "engine_param_18",
            "engine_param_19",
            "engine_param_20",
            "engine_param_21",
            "engine_param_22",
            "engine_param_23",
            "engine_param_24",
            "engine_param_25",
            "engine_param_26",
            "engine_param_27",
            "engine_param_28",
            "engine_param_29",
            "engine_param_30",
            "engine_param_31",
        ]

        for part_offset in range(16):  # 16 parts
            for engine_offset in range(4):  # 4 engines per part
                msb = 0x48 + (part_offset * 4) + engine_offset
                for lsb in range(32):  # 32 parameters per engine
                    param_name = f"part_{part_offset}_engine_{engine_offset}_{engine_param_names[lsb % len(engine_param_names)]}"
                    param_map[(msb, lsb)] = {
                        "name": param_name,
                        "type": "jupiter_x_engine",
                        "part": part_offset,
                        "engine": engine_offset,
                        "param_id": lsb,
                        "range": (0, 127),
                        "default": 64,
                        "unit": "value",
                    }

        # Jupiter-X LFO Parameters (0x60-0x6F, 0x00-0x0F)
        # 16 parts × 16 LFO parameters each
        lfo_param_names = [
            "lfo_waveform",
            "lfo_rate",
            "lfo_depth",
            "lfo_phase_offset",
            "lfo_fade_in",
            "lfo_key_sync",
            "lfo_to_pitch",
            "lfo_to_filter",
            "lfo_to_amplitude",
            "lfo_to_pan",
            "lfo_to_pwm",
            "lfo_to_fm_amount",
            "lfo_pitch_depth_cents",
            "lfo_filter_depth",
            "lfo_amp_depth",
            "lfo_reserved_15",
        ]

        for part_offset in range(16):  # 16 parts
            msb = 0x60 + part_offset
            for lsb in range(16):  # 16 LFO parameters per part
                param_name = f"part_{part_offset}_lfo_{lfo_param_names[lsb % len(lfo_param_names)]}"
                param_map[(msb, lsb)] = {
                    "name": param_name,
                    "type": "jupiter_x_lfo",
                    "part": part_offset,
                    "param_id": lsb,
                    "range": (0, 127),
                    "default": 64,
                    "unit": "value",
                }

        # Jupiter-X Envelope Parameters (0x70-0x7F, 0x00-0x0F)
        # 16 parts × 16 envelope parameters each
        envelope_param_names = [
            "env_attack_time",
            "env_decay_time",
            "env_sustain_level",
            "env_release_time",
            "env_attack_curve",
            "env_decay_curve",
            "env_release_curve",
            "env_attack_vel_sens",
            "env_decay_vel_sens",
            "env_sustain_vel_sens",
            "env_release_vel_sens",
            "env_legato_mode",
            "env_trigger_mode",
            "env_reserved_13",
            "env_reserved_14",
            "env_reserved_15",
        ]

        for part_offset in range(16):  # 16 parts
            msb = 0x70 + part_offset
            for lsb in range(16):  # 16 envelope parameters per part
                param_name = f"part_{part_offset}_env_{envelope_param_names[lsb % len(envelope_param_names)]}"
                param_map[(msb, lsb)] = {
                    "name": param_name,
                    "type": "jupiter_x_envelope",
                    "part": part_offset,
                    "param_id": lsb,
                    "range": (0, 127),
                    "default": 64,
                    "unit": "value",
                }

        # Jupiter-X Modulation Parameters (0x80-0x8F, 0x00-0x0F)
        # 16 parts × 16 modulation parameters each
        modulation_param_names = [
            "mod_wheel_depth",
            "breath_ctrl_depth",
            "foot_ctrl_depth",
            "aftertouch_depth",
            "velocity_depth",
            "key_follow",
            "tempo_sync",
            "swing_amount",
            "arp_enable",
            "arp_pattern",
            "arp_octave",
            "arp_gate_time",
            "arp_tempo",
            "effects_balance",
            "master_tune",
            "global_reserved_15",
        ]

        for part_offset in range(16):  # 16 parts
            msb = 0x80 + part_offset
            for lsb in range(16):  # 16 modulation parameters per part
                param_name = f"part_{part_offset}_mod_{modulation_param_names[lsb % len(modulation_param_names)]}"
                param_map[(msb, lsb)] = {
                    "name": param_name,
                    "type": "jupiter_x_modulation",
                    "part": part_offset,
                    "param_id": lsb,
                    "range": (0, 127),
                    "default": 64,
                    "unit": "value",
                }

        return param_map

    def process_nrpn_message(self, controller: int, value: int) -> bool:
        """
        Process NRPN-related controller messages.

        Args:
            controller: MIDI controller number
            value: Controller value (0-127)

        Returns:
            True if NRPN message was processed
        """
        with self.lock:
            if controller == 98:  # NRPN LSB
                self.current_lsb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 99:  # NRPN MSB
                self.current_msb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 6:  # Data Entry MSB
                if self.active_nrpn:
                    if not self.data_msb_received:
                        self.data_msb = value
                        self.data_msb_received = True
                    else:
                        # Complete NRPN message received
                        data_value = (self.data_msb << 7) | value
                        success = self._process_nrpn_data(data_value)
                        self.active_nrpn = False
                        self.data_msb_received = False
                        return success

            elif controller == 96:  # Data Increment
                if self.active_nrpn:
                    # Increment current parameter value
                    current_value = self.get_current_parameter_value()
                    if current_value is not None:
                        new_value = min(current_value + 1, 16383)  # Max NRPN value
                        return self._process_nrpn_data(new_value)

            elif controller == 97:  # Data Decrement
                if self.active_nrpn:
                    # Decrement current parameter value
                    current_value = self.get_current_parameter_value()
                    if current_value is not None:
                        new_value = max(current_value - 1, 0)
                        return self._process_nrpn_data(new_value)

        return False

    def _process_nrpn_data(self, data_value: int) -> bool:
        """
        Process complete NRPN data value.

        Args:
            data_value: 14-bit NRPN data value (0-16383)

        Returns:
            True if parameter was processed successfully
        """
        # Convert 14-bit value to 7-bit MIDI range (0-127)
        midi_value = data_value >> 7  # Take MSB only, or could average MSB/LSB

        # Get parameter info
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.parameter_map.get(param_key)

        if not param_info:
            print(f"Unknown NRPN parameter: {param_key}")
            return False

        # Process parameter based on type
        param_name = param_info["name"]

        if param_name.startswith("part_"):
            # Part parameter
            part_num = param_info["part"]
            param_id = param_info["param_id"]
            return self._set_part_parameter(part_num, param_id, midi_value)

        elif param_name.startswith("system_") or param_name in [
            "master_tune",
            "master_volume",
            "master_pan",
            "master_coarse_tune",
            "master_fine_tune",
            "reverb_send_level",
            "chorus_send_level",
            "delay_send_level",
            "mfx_send_level",
            "device_id",
            "midi_channel",
            "local_control",
            "program_change_mode",
            "lcd_contrast",
            "led_brightness",
        ]:
            # System parameter
            return self._set_system_parameter(param_name, midi_value)

        elif param_name.startswith(("reverb_", "chorus_", "mfx_", "insert_")):
            # Effects parameter
            return self._set_effects_parameter(param_name, midi_value)

        elif param_info.get("type") == "jupiter_x_engine":
            # Jupiter-X engine parameter
            part_num = param_info["part"]
            engine_type = param_info["engine"]
            param_id = param_info["param_id"]
            return self._set_jupiter_x_engine_parameter(part_num, engine_type, param_id, midi_value)

        elif param_info.get("type") == "jupiter_x_lfo":
            # Jupiter-X LFO parameter
            part_num = param_info["part"]
            param_id = param_info["param_id"]
            return self._set_jupiter_x_lfo_parameter(part_num, param_id, midi_value)

        elif param_info.get("type") == "jupiter_x_envelope":
            # Jupiter-X envelope parameter
            part_num = param_info["part"]
            param_id = param_info["param_id"]
            return self._set_jupiter_x_envelope_parameter(part_num, param_id, midi_value)

        elif param_info.get("type") == "jupiter_x_modulation":
            # Jupiter-X modulation parameter
            part_num = param_info["part"]
            param_id = param_info["param_id"]
            return self._set_jupiter_x_modulation_parameter(part_num, param_id, midi_value)

        else:
            print(f"Unimplemented NRPN parameter: {param_name}")
            return False

    def _set_system_parameter(self, param_name: str, value: int) -> bool:
        """Set system parameter via component manager."""
        # Map parameter names to addresses
        param_addresses = {
            "master_tune": (0x00, 0x00),
            "master_volume": (0x00, 0x01),
            "master_pan": (0x00, 0x02),
            "master_coarse_tune": (0x00, 0x03),
            "master_fine_tune": (0x00, 0x04),
            "reverb_send_level": (0x00, 0x05),
            "chorus_send_level": (0x00, 0x06),
            "delay_send_level": (0x00, 0x07),
            "mfx_send_level": (0x00, 0x08),
            "device_id": (0x00, 0x09),
            "midi_channel": (0x00, 0x0A),
            "local_control": (0x00, 0x0B),
            "program_change_mode": (0x00, 0x0C),
            "lcd_contrast": (0x00, 0x0D),
            "led_brightness": (0x00, 0x0E),
        }

        address = param_addresses.get(param_name)
        if address:
            return self.component_manager.process_parameter_change(bytes(address), value)

        return False

    def _set_part_parameter(self, part_num: int, param_id: int, value: int) -> bool:
        """Set part parameter via component manager."""
        # Part parameters start at 0x10 + part_num
        addr_high = 0x10 + part_num
        address = bytes([addr_high, param_id])
        return self.component_manager.process_parameter_change(address, value)

    def _set_effects_parameter(self, param_name: str, value: int) -> bool:
        """Set effects parameter via component manager."""
        # Parse parameter name to determine address
        if param_name.startswith("reverb_"):
            # Reverb parameters at 0x03
            param_map = {
                "reverb_type": 0x00,
                "reverb_level": 0x01,
                "reverb_time": 0x02,
                "reverb_feedback": 0x03,
                "reverb_pre_delay": 0x04,
                "reverb_high_freq_damp": 0x05,
                "reverb_low_freq_damp": 0x06,
                "reverb_balance": 0x07,
            }
            addr_low = param_map.get(param_name)
            if addr_low is not None:
                return self.component_manager.process_parameter_change(
                    bytes([0x03, addr_low]), value
                )

        elif param_name.startswith("chorus_"):
            # Chorus parameters at 0x04
            param_map = {
                "chorus_type": 0x00,
                "chorus_level": 0x01,
                "chorus_rate": 0x02,
                "chorus_depth": 0x03,
                "chorus_pre_delay": 0x04,
                "chorus_feedback": 0x05,
                "chorus_balance": 0x06,
            }
            addr_low = param_map.get(param_name)
            if addr_low is not None:
                return self.component_manager.process_parameter_change(
                    bytes([0x04, addr_low]), value
                )

        elif param_name.startswith("mfx_"):
            # MFX parameters at 0x05
            if param_name == "mfx_type":
                return self.component_manager.process_parameter_change(bytes([0x05, 0x00]), value)
            elif param_name.startswith("mfx_param_"):
                param_num = int(param_name.split("_")[-1])
                return self.component_manager.process_parameter_change(
                    bytes([0x05, param_num]), value
                )

        elif param_name.startswith("insert_"):
            # Insert effect parameters at 0x40-0x47
            parts = param_name.split("_")
            if len(parts) >= 4:
                insert_num = int(parts[1])
                param_num = int(parts[3])
                addr_high = 0x40 + insert_num
                return self.component_manager.process_parameter_change(
                    bytes([addr_high, param_num]), value
                )

        return False

    def _set_jupiter_x_engine_parameter(
        self, part_num: int, engine_type: int, param_id: int, value: int
    ) -> bool:
        """Set Jupiter-X engine parameter via GS part."""
        try:
            multipart = self.component_manager.components["multipart"]
            part = multipart.get_part(part_num)
            if part and hasattr(part, "engines"):
                # Route to appropriate Jupiter-X engine
                engine_params = getattr(part, "engine_params", {})
                engine_params[engine_type] = engine_params.get(engine_type, {})
                engine_params[engine_type][param_id] = value
                part.engine_params = engine_params

                # Trigger reconfiguration if needed
                if hasattr(part, "notify_engine_change"):
                    part.notify_engine_change(engine_type)
                return True
        except Exception as e:
            print(f"Error setting Jupiter-X engine parameter: {e}")
        return False

    def _set_jupiter_x_lfo_parameter(self, part_num: int, param_id: int, value: int) -> bool:
        """Set Jupiter-X LFO parameter via GS part."""
        try:
            multipart = self.component_manager.components["multipart"]
            part = multipart.get_part(part_num)
            if part and hasattr(part, "lfo") and part.lfo:
                # Map parameter ID to LFO parameter
                lfo_param_map = {
                    0: "waveform",
                    1: "rate",
                    2: "depth",
                    3: "phase_offset",
                    4: "fade_in",
                    5: "key_sync",
                    6: "to_pitch",
                    7: "to_filter",
                    8: "to_amplitude",
                    9: "to_pan",
                    10: "to_pwm",
                    11: "to_fm_amount",
                    12: "pitch_depth_cents",
                    13: "filter_depth",
                    14: "amplitude_depth",
                }

                if param_id in lfo_param_map:
                    param_name = lfo_param_map[param_id]
                    # Set LFO parameter on the part
                    if hasattr(part.lfo, param_name):
                        setattr(part.lfo, param_name, value)
                        return True
                    return False
        except Exception as e:
            print(f"Error setting Jupiter-X LFO parameter: {e}")
        return False

    def _set_jupiter_x_envelope_parameter(self, part_num: int, param_id: int, value: int) -> bool:
        """Set Jupiter-X envelope parameter via GS part."""
        try:
            multipart = self.component_manager.components["multipart"]
            part = multipart.get_part(part_num)
            if part and hasattr(part, "envelope") and part.envelope:
                # Map parameter ID to envelope parameter
                env_param_map = {
                    0: "attack_time",
                    1: "decay_time",
                    2: "sustain_level",
                    3: "release_time",
                    4: "attack_curve",
                    5: "decay_curve",
                    6: "release_curve",
                    7: "attack_vel_sens",
                    8: "decay_vel_sens",
                    9: "sustain_vel_sens",
                    10: "release_vel_sens",
                    11: "legato_mode",
                    12: "trigger_mode",
                }

                if param_id in env_param_map:
                    param_name = env_param_map[param_id]
                    # Set envelope parameter on the part
                    if hasattr(part.envelope, param_name):
                        setattr(part.envelope, param_name, value)
                        return True
                    return False
        except Exception as e:
            print(f"Error setting Jupiter-X envelope parameter: {e}")
        return False

    def _set_jupiter_x_modulation_parameter(self, part_num: int, param_id: int, value: int) -> bool:
        """Set Jupiter-X modulation parameter via GS part."""
        try:
            # Jupiter-X modulation parameters
            modulation_param_map = {
                0: "mod_wheel_depth",
                1: "breath_ctrl_depth",
                2: "foot_ctrl_depth",
                3: "aftertouch_depth",
                4: "velocity_depth",
                5: "key_follow",
                6: "tempo_sync",
                7: "swing_amount",
                8: "arp_enable",
                9: "arp_pattern",
                10: "arp_octave",
                11: "arp_gate_time",
                12: "arp_tempo",
                13: "effects_balance",
                14: "master_tune",
            }

            if param_id in modulation_param_map:
                param_name = modulation_param_map[param_id]
                print(f"Jupiter-X modulation parameter: part {part_num}, {param_name} = {value}")
                return True
        except Exception as e:
            print(f"Error setting Jupiter-X modulation parameter: {e}")
        return False

    def get_current_parameter_value(self) -> int | None:
        """Get current parameter value for data increment/decrement."""
        if not self.active_nrpn:
            return None

        param_key = (self.current_msb, self.current_lsb)
        address = bytes(param_key)

        # Get current value from component manager
        current_value = self.component_manager.get_parameter_value(address)
        return current_value

    def get_parameter_info(self, msb: int, lsb: int) -> dict[str, Any] | None:
        """Get information about a specific NRPN parameter."""
        param_key = (msb, lsb)
        return self.parameter_map.get(param_key)

    def list_parameters(self, category: str = "all") -> list[dict[str, Any]]:
        """
        List all NRPN parameters, optionally filtered by category.

        Args:
            category: 'all', 'system', 'part', 'effects'

        Returns:
            List of parameter information dictionaries
        """
        parameters = []

        for (msb, lsb), param_info in self.parameter_map.items():
            if category == "all":
                parameters.append(
                    {"address": f"{msb:02X}:{lsb:02X}", "msb": msb, "lsb": lsb, **param_info}
                )
            elif category == "system" and msb == 0x01:
                parameters.append(
                    {"address": f"{msb:02X}:{lsb:02X}", "msb": msb, "lsb": lsb, **param_info}
                )
            elif category == "part" and 0x18 <= msb <= 0x2F:
                parameters.append(
                    {"address": f"{msb:02X}:{lsb:02X}", "msb": msb, "lsb": lsb, **param_info}
                )
            elif (category == "effects" and msb in [0x03, 0x04, 0x05]) or 0x40 <= msb <= 0x47:
                parameters.append(
                    {"address": f"{msb:02X}:{lsb:02X}", "msb": msb, "lsb": lsb, **param_info}
                )

        return parameters

    def get_nrpn_status(self) -> dict[str, Any]:
        """Get current NRPN controller status."""
        with self.lock:
            return {
                "active": self.active_nrpn,
                "current_msb": self.current_msb,
                "current_lsb": self.current_lsb,
                "data_msb_received": self.data_msb_received,
                "data_msb": self.data_msb,
                "current_parameter": self.get_parameter_info(self.current_msb, self.current_lsb),
            }

    def reset_nrpn_state(self):
        """Reset NRPN controller state."""
        with self.lock:
            self.active_nrpn = False
            self.current_msb = 0
            self.current_lsb = 0
            self.data_msb = 0
            self.data_msb_received = False

    def __str__(self) -> str:
        """String representation."""
        status = self.get_nrpn_status()
        active = "Active" if status["active"] else "Inactive"
        return f"JV2080NRPNController({active}, params={len(self.parameter_map)})"

    def __repr__(self) -> str:
        return self.__str__()
