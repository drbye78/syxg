# PHASE C: EXTENDED RPN/NRPN SUPPORT

# ============================================================================
# EXTENDED RPN/NRPN PARAMETER SUPPORT - PHASE C ENHANCEMENT
# ============================================================================

class ExtendedRPN_NRPN_Handler:
    """
    Extended RPN/NRPN handler supporting GM2 system parameters and additional effects.
    Go beyond XG voice parameters (MSB 127) to system-wide and effects parameters.
    """

    def __init__(self):
        # Extended RPN parameters (beyond pitch bend range)
        self.extended_rpn_parameters = {
            (0, 1): "channel_fine_tuning",       # Channel Fine Tuning ±50 cents
            (0, 2): "channel_coarse_tuning",     # Channel Coarse Tuning ±24 semitones
            (0, 3): "tuning_program_select",     # Tuning Program Select (0-127)
            (0, 4): "tuning_bank_select",        # Tuning Bank Select (0-127)
            (0, 5): "modulation_depth_range",    # Modulation Depth Range Setup
            (0, 6): "MPE_config",                # MPE Configuration Message
        }

        # System-wide NRPN parameters (MSB 0)
        self.system_nrpn_parameters = {
            (0, 440): "pitch_env_depth_range",   # Pitch Envelope Depth Range (±24 semitones)
            (0, 441): "master_fine_tuning",      # Master Fine Tuning (±50 cents, 14-bit)
            (0, 442): "master_coarse_tuning",    # Master Coarse Tuning (±24 semitones)

            # GM2 System Exclusive parameters via NRPN
            (0, 443): "master_volume",           # Master Volume (14-bit)
            (0, 444): "master_balance",          # Master Balance (-100% to +100%)
            (0, 445): "master_tune_scale",       # Master Tune Scale (equal/non-equal)

            # Effects system parameters
            (0, 450): "system_reverb_level",     # System Reverb Level
            (0, 451): "system_chorus_level",     # System Chorus Level
            (0, 452): "system_delay_level",      # System Delay Level
        }

        # Effects NRPN parameters (MSB 1-7 for different effect types)
        self.effects_nrpn_parameters = {
            # Reverb parameters (MSB 1)
            (1, 0): "reverb_type",               # Reverb Type (0-79 XG types)
            (1, 1): "reverb_time",               # Reverb Time (0.3-30.0 seconds)
            (1, 2): "reverb_diffusion",          # Reverb Diffusion/Early Reflection
            (1, 3): "reverb_tone",               # Reverb Tone/Filter
            (1, 16): "reverb_pre_delay",         # Reverb Pre-Delay
            (1, 17): "reverb_pre_delay_ratio",   # Pre-Delay to Reverb Ratio

            # Chorus parameters (MSB 2)
            (2, 0): "chorus_type",               # Chorus Type (0-7 XG types)
            (2, 1): "chorus_depth",              # Chorus Depth
            (2, 2): "chorus_speed",              # Chorus Speed/Rate
            (2, 3): "chorus_feedback",           # Chorus Feedback Level

            # Variation parameters (MSB 3)
            (3, 0): "variation_type",            # Variation Type (0-61 XG types)
            (3, 1): "variation_depth",           # Variation Depth
            (3, 2): "variation_speed",           # Variation Speed
            (3, 3): "variation_feedback",        # Variation Feedback

            # Insertion effects (MSB 4-7)
            (4, 0): "insertion_1_type",          # Insertion Effect 1 Type
            (4, 1): "insertion_1_param_1",       # Insertion Effect 1 Parameter 1
            # ... additional insertion effect parameters
        }

        # Parameter value ranges and validation
        self.parameter_ranges = {
            # RPN ranges
            "channel_fine_tuning": (-8192, 8191),    # ±50 cents in cent units
            "channel_coarse_tuning": (-64, 63),      # ±24 semitones
            "tuning_program_select": (0, 127),
            "tuning_bank_select": (0, 127),

            # System NRPN ranges
            "pitch_env_depth_range": (0, 48),        # 0-48 semitones range
            "master_fine_tuning": (-8192, 8191),     # ±50 cents, 14-bit
            "master_coarse_tuning": (-64, 63),       # ±24 semitones
            "master_volume": (0, 16256),             # 14-bit volume
            "master_balance": (-8192, 8191),         # 14-bit balance

            # Effects ranges
            "reverb_type": (0, 79),                  # XG reverb types
            "reverb_time": (3, 300),                 # 0.3-30.0 seconds in 0.1s units
            "reverb_diffusion": (0, 10),             # Diffusion factor
            "reverb_tone": (0, 30),                  # Tone adjustment
        }

        # Current parameter state
        self.current_parameter_values = {}

    def handle_extended_rpn_nrpn(self, msb: int, lsb: int, data_value: int,
                                is_nrpn: bool = True) -> bool:
        """
        Handle extended RPN/NRPN parameters beyond XG voice controls.

        Args:
            msb: Parameter MSB (0-127)
            lsb: Parameter LSB (0-127)
            data_value: Parameter value (0-16383 for 14-bit, 0-127 for 7-bit)
            is_nrpn: True for NRPN, False for RPN

        Returns:
            True if parameter was handled, False otherwise
        """
        parameter_key = (msb, lsb)

        if is_nrpn:
            return self._handle_nrpn_parameter(parameter_key, data_value)
        else:
            return self._handle_rpn_parameter(parameter_key, data_value)

    def _handle_rpn_parameter(self, parameter_key: Tuple[int, int], value: int) -> bool:
        """Handle extended RPN parameter."""
        if parameter_key in self.extended_rpn_parameters:
            param_name = self.extended_rpn_parameters[parameter_key]
            return self._apply_rpn_parameter(param_name, value)
        return False

    def _handle_nrpn_parameter(self, parameter_key: Tuple[int, int], value: int) -> bool:
        """Handle extended NRPN parameter."""
        # Check system parameters first (MSB 0)
        if parameter_key in self.system_nrpn_parameters:
            param_name = self.system_nrpn_parameters[parameter_key]
            return self._apply_system_nrpn_parameter(param_name, value)

        # Check effects parameters (MSB 1-7)
        elif parameter_key in self.effects_nrpn_parameters:
            param_name = self.effects_nrpn_parameters[parameter_key]
            return self._apply_effects_nrpn_parameter(param_name, value)

        return False

    def _apply_rpn_parameter(self, param_name: str, value: int) -> bool:
        """Apply RPN parameter value."""
        if param_name == "channel_fine_tuning":
            # Apply fine tuning to all channels/notes
            self._apply_channel_fine_tuning(value)
        elif param_name == "channel_coarse_tuning":
            self._apply_channel_coarse_tuning(value)
        elif param_name == "tuning_program_select":
            self._apply_tuning_program_select(value)
        elif param_name == "tuning_bank_select":
            self._apply_tuning_bank_select(value)

        # Store current value
        self.current_parameter_values[param_name] = value
        return True

    def _apply_system_nrpn_parameter(self, param_name: str, value: int) -> bool:
        """Apply system NRPN parameter value."""
        if param_name == "pitch_env_depth_range":
            self._apply_pitch_env_depth_range(value)
        elif param_name == "master_fine_tuning":
            self._apply_master_fine_tuning(value)
        elif param_name == "master_coarse_tuning":
            self._apply_master_coarse_tuning(value)
        elif param_name == "master_volume":
            self._apply_master_volume(value)
        elif param_name == "master_balance":
            self._apply_master_balance(value)
        elif param_name.startswith("system_"):
            self._apply_system_effects_level(param_name, value)

        # Store current value
        self.current_parameter_values[param_name] = value
        return True

    def _apply_effects_nrpn_parameter(self, param_name: str, value: int) -> bool:
        """Apply effects NRPN parameter value."""
        # Route to effects system
        # This would integrate with the effects engine

        # Store current value
        self.current_parameter_values[param_name] = value
        return True

    # PARAMETER IMPLEMENTATION METHODS

    def _apply_channel_fine_tuning(self, value: int):
        """Apply channel fine tuning RPN (0,1)."""
        # Convert to cents: value is in units of 8192/1200 ≈ 6.826 cents per unit
        cents = (value - 8192) * (1.0 / 6.826)  # Approximate conversion
        self.channel_fine_tuning = cents

        # Apply to all active notes on this channel
        fine_tune_factor = 2 ** (cents / 1200.0)
        # Implementation would modify note frequencies

    def _apply_channel_coarse_tuning(self, value: int):
        """Apply channel coarse tuning RPN (0,2)."""
        semitones = (value - 64)  # Range -64 to +63 semitones
        self.channel_coarse_tuning = semitones

        # Apply coarse frequency shift
        coarse_tune_factor = 2 ** (semitones / 12.0)

    def _apply_pitch_env_depth_range(self, value: int):
        """Apply pitch envelope depth range NRPN (0,440)."""
        # Set the maximum range for pitch envelope depth
        max_depth_semitones = value / 2.0  # Convert to semitones (0-24 semitones range)
        # This affects how much pitch envelopes can modulate

    def _apply_master_fine_tuning(self, value: int):
        """Apply master fine tuning NRPN (0,441)."""
        # 14-bit master fine tuning (same as channel fine tuning but system-wide)
        pass

    def _apply_master_coarse_tuning(self, value: int):
        """Apply master coarse tuning NRPN (0,442)."""
        # Master coarse tuning affects all channels
        pass

    def _apply_master_volume(self, value: int):
        """Apply master volume NRPN (0,443)."""
        # 14-bit master volume setting
        pass

    def _apply_master_balance(self, value: int):
        """Apply master balance NRPN (0,444)."""
        # Master left/right balance for the entire system
        pass

    def _apply_system_effects_level(self, param_name: str, value: int):
        """Apply system effects level NRPN."""
        # Normalize value to 0.0-1.0 range
        level = value / 127.0

        if param_name == "system_reverb_level":
            # Set system-wide reverb level
            pass
        elif param_name == "system_chorus_level":
            # Set system-wide chorus level
            pass
        elif param_name == "system_delay_level":
            # Set system-wide delay level
            pass

    # UTILITY METHODS

    def get_parameter_value(self, param_name: str) -> Optional[int]:
        """Get current value of a parameter."""
        return self.current_parameter_values.get(param_name)

    def reset_all_parameters(self):
        """Reset all extended RPN/NRPN parameters to defaults."""
        # Clear stored values and reset to defaults
        self.current_parameter_values.clear()

        # Reset specific parameters to their default values
        self.channel_fine_tuning = 0
        self.channel_coarse_tuning = 0
        # ... reset other parameters

    def get_supported_parameters(self) -> Dict[str, List]:
        """Get lists of supported RPN and NRPN parameters."""
        return {
            "rpn": list(self.extended_rpn_parameters.values()),
            "system_nrpn": list(self.system_nrpn_parameters.values()),
            "effects_nrpn": list(self.effects_nrpn_parameters.values()),
        }
