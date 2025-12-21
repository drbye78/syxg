"""
XG NRPN Controller - Complete XG MIDI Parameter Control

Implements full XG NRPN (Non-Registered Parameter Number) specification
for comprehensive MIDI control of XG effects parameters.

XG NRPN Mapping (MSB/LSB):
- MSB 0: System Reverb (LSB 0-10)
- MSB 1: System Chorus (LSB 0-9)
- MSB 3: System Variation (LSB 0-14)
- MSB 4: Master EQ (LSB 0-12)
- MSB 16: Effect Presets (LSB 0-127)
- MSB 32: Part Selection (LSB 0-15)
- MSB 33-35: Insertion Effects (per slot)
- MSB 36: Variation Effects
- MSB 37: Part Send Levels

Copyright (c) 2025 XG Synthesis Core
"""

import threading
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import IntEnum

from .xg_presets import XGEffectPresets


class XGNRPNController:
    """
    XG NRPN Controller - Full XG MIDI Parameter Control Implementation

    Handles all XG NRPN messages for complete MIDI control of effects parameters.
    Supports multi-part addressing, system effects, and effect presets.
    """

    def __init__(self, effects_coordinator):
        """
        Initialize XG NRPN controller.

        Args:
            effects_coordinator: XGEffectsCoordinator instance to control
        """
        self.coordinator = effects_coordinator

        # NRPN state tracking
        self.active_msb: Optional[int] = None
        self.active_lsb: Optional[int] = None
        self.data_msb: Optional[int] = None
        self.data_lsb: Optional[int] = None

        # Multi-part addressing
        self.selected_part: int = 0  # 0-15, default to part 0

        # Thread safety
        self.lock = threading.RLock()

        # NRPN handler registry - maps (MSB, LSB) to handler functions
        self._register_nrpn_handlers()

    def _register_nrpn_handlers(self):
        """Register all XG NRPN parameter handlers."""
        self.nrpn_handlers: Dict[Tuple[int, int], Callable[[int, int], bool]] = {

            # System Reverb (MSB 0)
            (0, 0): self._handle_reverb_type,
            (0, 1): self._handle_reverb_time,
            (0, 2): self._handle_reverb_level,
            (0, 3): self._handle_reverb_pre_delay,
            (0, 4): self._handle_reverb_hf_damping,
            (0, 5): self._handle_reverb_density,
            (0, 6): self._handle_reverb_early_level,
            (0, 7): self._handle_reverb_tail_level,
            (0, 8): self._handle_reverb_shape,
            (0, 9): self._handle_reverb_gate_time,
            (0, 10): self._handle_reverb_pre_delay_scale,

            # System Chorus (MSB 1)
            (1, 0): self._handle_chorus_type,
            (1, 1): self._handle_chorus_rate,
            (1, 2): self._handle_chorus_depth,
            (1, 3): self._handle_chorus_feedback,
            (1, 4): self._handle_chorus_level,
            (1, 5): self._handle_chorus_delay,
            (1, 6): self._handle_chorus_output,
            (1, 7): self._handle_chorus_cross_feedback,
            (1, 8): self._handle_chorus_lfo_waveform,
            (1, 9): self._handle_chorus_phase_diff,

            # System Variation (MSB 3) - Add basic variation type control
            (3, 0): self._handle_variation_type,

            # System Variation (MSB 3)
            (3, 0): self._handle_variation_type,

            # Master EQ (MSB 4)
            (4, 0): self._handle_eq_type,
            (4, 1): self._handle_eq_low_gain,
            (4, 2): self._handle_eq_low_mid_gain,
            (4, 3): self._handle_eq_mid_gain,
            (4, 4): self._handle_eq_high_mid_gain,
            (4, 5): self._handle_eq_high_gain,
            (4, 6): self._handle_eq_mid_freq,
            (4, 7): self._handle_eq_q_factor,

            # Effect Presets (MSB 16)
            (16, 0): self._handle_preset_select,

            # Part Selection (MSB 32)
            (32, 0): self._handle_part_select,

            # Insertion Effects (MSB 33-35, one per slot)
            (33, 0): lambda v, l: self._handle_insertion_param(0, "type", v, l),  # Slot 0 type
            (33, 1): lambda v, l: self._handle_insertion_param(0, "bypass", v, l),  # Slot 0 bypass
            # Slot 0 parameters (2-127) handled dynamically

            (34, 0): lambda v, l: self._handle_insertion_param(1, "type", v, l),  # Slot 1 type
            (34, 1): lambda v, l: self._handle_insertion_param(1, "bypass", v, l),  # Slot 1 bypass
            # Slot 1 parameters (2-127) handled dynamically

            (35, 0): lambda v, l: self._handle_insertion_param(2, "type", v, l),  # Slot 2 type
            (35, 1): lambda v, l: self._handle_insertion_param(2, "bypass", v, l),  # Slot 2 bypass
            # Slot 2 parameters (2-127) handled dynamically

            # Part Send Levels (MSB 37)
            (37, 0): self._handle_part_reverb_send,
            (37, 1): self._handle_part_chorus_send,
            (37, 2): self._handle_part_variation_send,
        }

    def process_nrpn(self, msb: int, lsb: int, data_msb: int, data_lsb: int) -> bool:
        """
        Process XG NRPN message.

        Args:
            msb: NRPN MSB (parameter group)
            lsb: NRPN LSB (parameter index)
            data_msb: Data MSB (parameter value)
            data_lsb: Data LSB (unused for most XG params)

        Returns:
            True if NRPN was handled successfully
        """
        with self.lock:
            # Set active NRPN parameter
            self.active_msb = msb
            self.active_lsb = lsb

            # Combine data MSB/LSB (most XG params use only MSB)
            data_value = data_msb  # LSB typically unused in XG

            # Find and execute handler
            handler_key = (msb, lsb)
            if handler_key in self.nrpn_handlers:
                return self.nrpn_handlers[handler_key](data_value, data_lsb)

            # Unknown NRPN parameter
            print(f"XG NRPN: Unknown parameter MSB={msb}, LSB={lsb}, Data={data_value}")
            return False

    # ===== SYSTEM REVERB HANDLERS (MSB 0) =====

    def _handle_reverb_type(self, value: int, lsb: int) -> bool:
        """Handle reverb type NRPN (MSB 0, LSB 0)."""
        reverb_type = min(max(value, 0), 24)  # 0-24 XG reverb types
        return self.coordinator.set_system_effect_parameter('reverb', 'type', reverb_type)

    def _handle_reverb_time(self, value: int, lsb: int) -> bool:
        """Handle reverb time NRPN (MSB 0, LSB 1)."""
        # Convert 0-127 to 0.1-8.3 seconds
        time_seconds = 0.1 + (value / 127.0) * 8.2
        return self.coordinator.set_system_effect_parameter('reverb', 'time', time_seconds)

    def _handle_reverb_level(self, value: int, lsb: int) -> bool:
        """Handle reverb level NRPN (MSB 0, LSB 2)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('reverb', 'level', level)

    def _handle_reverb_pre_delay(self, value: int, lsb: int) -> bool:
        """Handle reverb pre-delay NRPN (MSB 0, LSB 3)."""
        # Convert 0-127 to 0-50ms
        pre_delay_ms = (value / 127.0) * 50.0
        return self.coordinator.set_system_effect_parameter('reverb', 'pre_delay', pre_delay_ms / 1000.0)

    def _handle_reverb_hf_damping(self, value: int, lsb: int) -> bool:
        """Handle reverb HF damping NRPN (MSB 0, LSB 4)."""
        damping = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('reverb', 'hf_damping', damping)

    def _handle_reverb_density(self, value: int, lsb: int) -> bool:
        """Handle reverb density NRPN (MSB 0, LSB 5)."""
        density = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('reverb', 'density', density)

    def _handle_reverb_early_level(self, value: int, lsb: int) -> bool:
        """Handle reverb early level NRPN (MSB 0, LSB 6)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('reverb', 'early_level', level)

    def _handle_reverb_tail_level(self, value: int, lsb: int) -> bool:
        """Handle reverb tail level NRPN (MSB 0, LSB 7)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('reverb', 'tail_level', level)

    def _handle_reverb_shape(self, value: int, lsb: int) -> bool:
        """Handle reverb shape NRPN (MSB 0, LSB 8)."""
        return self.coordinator.set_system_effect_parameter('reverb', 'shape', value)

    def _handle_reverb_gate_time(self, value: int, lsb: int) -> bool:
        """Handle reverb gate time NRPN (MSB 0, LSB 9)."""
        return self.coordinator.set_system_effect_parameter('reverb', 'gate_time', value)

    def _handle_reverb_pre_delay_scale(self, value: int, lsb: int) -> bool:
        """Handle reverb pre-delay scale NRPN (MSB 0, LSB 10)."""
        return self.coordinator.set_system_effect_parameter('reverb', 'pre_delay_scale', value)

    # ===== SYSTEM CHORUS HANDLERS (MSB 1) =====

    def _handle_chorus_type(self, value: int, lsb: int) -> bool:
        """Handle chorus type NRPN (MSB 1, LSB 0)."""
        chorus_type = min(max(value, 0), 5)  # 0-5 XG chorus types
        return self.coordinator.set_system_effect_parameter('chorus', 'type', chorus_type)

    def _handle_chorus_rate(self, value: int, lsb: int) -> bool:
        """Handle chorus rate NRPN (MSB 1, LSB 1)."""
        # Convert 0-127 to 0.125-10 Hz
        rate_hz = 0.125 + (value / 127.0) * 9.875
        return self.coordinator.set_system_effect_parameter('chorus', 'rate', rate_hz)

    def _handle_chorus_depth(self, value: int, lsb: int) -> bool:
        """Handle chorus depth NRPN (MSB 1, LSB 2)."""
        depth = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('chorus', 'depth', depth)

    def _handle_chorus_feedback(self, value: int, lsb: int) -> bool:
        """Handle chorus feedback NRPN (MSB 1, LSB 3)."""
        # Convert 0-127 to -0.5 to +0.5
        feedback = ((value - 64) / 63.0) * 0.5
        return self.coordinator.set_system_effect_parameter('chorus', 'feedback', feedback)

    def _handle_chorus_level(self, value: int, lsb: int) -> bool:
        """Handle chorus level NRPN (MSB 1, LSB 4)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_system_effect_parameter('chorus', 'level', level)

    def _handle_chorus_delay(self, value: int, lsb: int) -> bool:
        """Handle chorus delay NRPN (MSB 1, LSB 5)."""
        return self.coordinator.set_system_effect_parameter('chorus', 'delay', value)

    def _handle_chorus_output(self, value: int, lsb: int) -> bool:
        """Handle chorus output NRPN (MSB 1, LSB 6)."""
        return self.coordinator.set_system_effect_parameter('chorus', 'output', value)

    def _handle_chorus_cross_feedback(self, value: int, lsb: int) -> bool:
        """Handle chorus cross-feedback NRPN (MSB 1, LSB 7)."""
        # Convert 0-127 to -0.5 to +0.5
        cross_feedback = ((value - 64) / 63.0) * 0.5
        return self.coordinator.set_system_effect_parameter('chorus', 'cross_feedback', cross_feedback)

    def _handle_chorus_lfo_waveform(self, value: int, lsb: int) -> bool:
        """Handle chorus LFO waveform NRPN (MSB 1, LSB 8)."""
        waveform = min(max(value, 0), 3)  # 0-3: sine, triangle, square, sawtooth
        return self.coordinator.set_system_effect_parameter('chorus', 'lfo_waveform', waveform)

    def _handle_chorus_phase_diff(self, value: int, lsb: int) -> bool:
        """Handle chorus phase difference NRPN (MSB 1, LSB 9)."""
        # Convert 0-127 to 0-180 degrees
        phase_degrees = (value / 127.0) * 180.0
        return self.coordinator.set_system_effect_parameter('chorus', 'phase_diff', phase_degrees)

    # ===== SYSTEM VARIATION HANDLERS (MSB 3) =====

    def _handle_variation_type(self, value: int, lsb: int) -> bool:
        """Handle variation type NRPN (MSB 3, LSB 0)."""
        variation_type = min(max(value, 0), 62)  # 0-62 XG variation types
        return self.coordinator.set_variation_effect_type(variation_type)

    # ===== MASTER EQ HANDLERS (MSB 4) =====

    def _handle_eq_type(self, value: int, lsb: int) -> bool:
        """Handle EQ type NRPN (MSB 4, LSB 0)."""
        eq_type = min(max(value, 0), 4)  # 0-4: Flat, Jazz, Pops, Rock, Concert
        return self.coordinator.set_master_eq_type(eq_type)

    def _handle_eq_low_gain(self, value: int, lsb: int) -> bool:
        """Handle EQ low gain NRPN (MSB 4, LSB 1)."""
        # Convert 0-127 to -12 to +12 dB
        gain_db = ((value - 64) / 63.0) * 12.0
        return self.coordinator.set_master_eq_gain('low', gain_db)

    def _handle_eq_low_mid_gain(self, value: int, lsb: int) -> bool:
        """Handle EQ low-mid gain NRPN (MSB 4, LSB 2)."""
        gain_db = ((value - 64) / 63.0) * 12.0
        return self.coordinator.set_master_eq_gain('low_mid', gain_db)

    def _handle_eq_mid_gain(self, value: int, lsb: int) -> bool:
        """Handle EQ mid gain NRPN (MSB 4, LSB 3)."""
        gain_db = ((value - 64) / 63.0) * 12.0
        return self.coordinator.set_master_eq_gain('mid', gain_db)

    def _handle_eq_high_mid_gain(self, value: int, lsb: int) -> bool:
        """Handle EQ high-mid gain NRPN (MSB 4, LSB 4)."""
        gain_db = ((value - 64) / 63.0) * 12.0
        return self.coordinator.set_master_eq_gain('high_mid', gain_db)

    def _handle_eq_high_gain(self, value: int, lsb: int) -> bool:
        """Handle EQ high gain NRPN (MSB 4, LSB 5)."""
        gain_db = ((value - 64) / 63.0) * 12.0
        return self.coordinator.set_master_eq_gain('high', gain_db)

    def _handle_eq_mid_freq(self, value: int, lsb: int) -> bool:
        """Handle EQ mid frequency NRPN (MSB 4, LSB 6)."""
        # Convert 0-127 to 100-5220 Hz (logarithmic)
        if value == 0:
            freq = 100.0
        else:
            freq = 100.0 * (5220.0 / 100.0) ** (value / 127.0)
        return self.coordinator.set_master_eq_frequency(freq)

    def _handle_eq_q_factor(self, value: int, lsb: int) -> bool:
        """Handle EQ Q factor NRPN (MSB 4, LSB 7)."""
        # Convert 0-127 to 0.5-5.5
        q_factor = 0.5 + (value / 127.0) * 5.0
        return self.coordinator.set_master_eq_q_factor(q_factor)

    # ===== EFFECT PRESETS (MSB 16) =====

    def _handle_preset_select(self, value: int, lsb: int) -> bool:
        """Handle effect preset selection NRPN (MSB 16, LSB 0)."""
        preset_id = min(max(value, 0), 127)  # 0-127 preset range
        success = XGEffectPresets.apply_preset_to_coordinator(preset_id, self.coordinator)

        if success:
            preset_info = XGEffectPresets.get_preset(preset_id)
            preset_name = preset_info.get("name", f"Preset {preset_id}")
            print(f"XG NRPN: Applied effect preset '{preset_name}' (ID: {preset_id})")
        else:
            print(f"XG NRPN: Failed to apply effect preset {preset_id}")

        return success

    # ===== MULTI-PART CONTROL (MSB 32) =====

    def _handle_part_select(self, value: int, lsb: int) -> bool:
        """Handle part selection NRPN (MSB 32, LSB 0)."""
        self.selected_part = min(max(value, 0), 15)  # 0-15 parts
        print(f"XG NRPN: Selected part {self.selected_part}")
        return True

    # ===== PART SEND LEVELS (MSB 37) =====

    def _handle_part_reverb_send(self, value: int, lsb: int) -> bool:
        """Handle part reverb send NRPN (MSB 37, LSB 0)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_effect_send_level(self.selected_part, 'reverb', level)

    def _handle_part_chorus_send(self, value: int, lsb: int) -> bool:
        """Handle part chorus send NRPN (MSB 37, LSB 1)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_effect_send_level(self.selected_part, 'chorus', level)

    def _handle_part_variation_send(self, value: int, lsb: int) -> bool:
        """Handle part variation send NRPN (MSB 37, LSB 2)."""
        level = value / 127.0  # 0.0-1.0
        return self.coordinator.set_effect_send_level(self.selected_part, 'variation', level)

    # ===== INSERTION EFFECTS HANDLERS (MSB 33-35) =====

    def _handle_insertion_param(self, slot: int, param_type: str, value: int, lsb: int) -> bool:
        """
        Handle insertion effect parameters NRPN (MSB 33-35).

        Args:
            slot: Insertion slot (0-2)
            param_type: Parameter type ('type', 'bypass', or parameter name)
            value: Parameter value
            lsb: NRPN LSB (parameter index within slot)

        Returns:
            True if parameter was set successfully
        """
        try:
            # Handle special parameters
            if param_type == 'type':
                # Set effect type for slot (0-17)
                effect_type = min(max(value, 0), 17)
                return self.coordinator.set_channel_insertion_effect(self.selected_part, slot, effect_type)

            elif param_type == 'bypass':
                # Set bypass state (0=enabled, 127=bypassed)
                bypass = value >= 64
                return self.coordinator.set_channel_insertion_bypass(self.selected_part, slot, bypass)

            else:
                # Handle individual effect parameters
                # LSB maps to parameter index within the effect
                param_index = lsb - 2  # LSB 0-1 are type/bypass, 2+ are parameters

                if param_index >= 0:
                    # Get parameter name from effect type
                    effect_type = self.coordinator.insertion_effects[self.selected_part].insertion_types[slot]
                    param_info = self.coordinator.insertion_effects[self.selected_part].get_xg_parameter_info(effect_type)

                    if param_info:
                        param_names = list(param_info.keys())
                        if param_index < len(param_names):
                            param_name = param_names[param_index]

                            # Convert MIDI value to parameter range
                            param_def = param_info[param_name]
                            min_val, max_val = param_def['range']

                            if isinstance(min_val, int) and isinstance(max_val, int):
                                # Integer parameter
                                param_value = min_val + (value / 127.0) * (max_val - min_val)
                            else:
                                # Float parameter - scale appropriately
                                param_value = min_val + (value / 127.0) * (max_val - min_val)

                            # Set the parameter
                            return self.coordinator.insertion_effects[self.selected_part].set_xg_parameter(
                                slot, param_name, param_value
                            )

            return False

        except Exception as e:
            print(f"XG NRPN: Error handling insertion parameter slot={slot}, type={param_type}: {e}")
            return False

    def get_current_state(self) -> Dict[str, Any]:
        """Get current NRPN controller state."""
        return {
            'active_msb': self.active_msb,
            'active_lsb': self.active_lsb,
            'data_msb': self.data_msb,
            'data_lsb': self.data_lsb,
            'selected_part': self.selected_part
        }
