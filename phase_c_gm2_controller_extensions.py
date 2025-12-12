# PHASE C: GM2 CONTROLLER EXTENSIONS
# Add to VectorizedChannelRenderer class

    # GM2 LSB CONTROLLER IMPLEMENTATION (PHASE C)

    def __init__(self, channel: int, synth):
        # Original initialization
        self.channel = channel
        self.synth = synth
        self.sample_rate = synth.sample_rate
        # ... existing initialization ...

        # ===== PHASE C: GM2 LSB CONTROLLER SUPPORT =====
        # GM2 LSB controllers for 14-bit parameter control (0-16383 range)
        self.lsb_values = np.zeros(128, dtype=np.uint8)  # Store LSB values
        self.msb_values = np.zeros(128, dtype=np.uint8)  # Mirror MSB values

        # GM2 14-bit controller mappings (pairs that support LSB)
        self.lsb_controller_pairs = {
            # Standard GM/GM2 14-bit controller pairs
            0: 32,   # Bank Select MSB:LSB
            1: 33,   # Modulation MSB:LSB
            2: 34,   # Breath Controller MSB:LSB
            4: 36,   # Foot Controller MSB:LSB
            5: 37,   # Portamento Time MSB:LSB
            6: 38,   # Data Entry MSB:LSB
            7: 39,   # Volume MSB:LSB
            8: 40,   # Balance MSB:LSB
            10: 42,  # Pan MSB:LSB
            11: 43,  # Expression MSB:LSB
            12: 44,  # Effect Control 1 MSB:LSB
            13: 45,  # Effect Control 2 MSB:LSB

            # GM2 General Purpose controllers
            16: 48,  # GP Slider 1 MSB:LSB
            17: 49,  # GP Slider 2 MSB:LSB
            18: 50,  # GP Slider 3 MSB:LSB
            19: 51,  # GP Slider 4 MSB:LSB
            80: 48,  # GP Slider 5 MSB:LSB (GM2)
            81: 49,  # GP Slider 6 MSB:LSB (GM2)
            82: 50,  # GP Slider 7 MSB:LSB (GM2)
            83: 51,  # GP Slider 8 MSB:LSB (GM2)
        }

        # GM2 controller parameter ranges (7-bit vs 14-bit)
        self.gm2_controller_ranges = {
            "volume": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 16256},
            "expression": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 16256},
            "pan": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},  # Center
            "modulation": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 0},
            "breath": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 0},
            "foot": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 0},

            # GP controllers default to center/unity
            "gp_slider_1": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_2": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_3": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_4": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_5": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_6": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_7": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
            "gp_slider_8": {"7bit_range": (0, 127), "14bit_range": (0, 16256), "default": 8192},
        }

        # GM2 Data Entry enhancement
        self.data_entry_increment_step = 128  # Default step size for increment/decrement
        self.data_entry_mode = "rpn"  # "rpn" or "nrpn"

    def get_14bit_controller_value(self, msb_controller: int) -> int:
        """Get the 14-bit value (MSB + LSB) for a GM2 controller pair.

        Args:
            msb_controller: MSB controller number (0-127)

        Returns:
            14-bit controller value (0-16256)
        """
        lsb_controller = self.lsb_controller_pairs.get(msb_controller)
        if lsb_controller is not None:
            msb_value = self.msb_values[msb_controller]
            lsb_value = self.lsb_values[lsb_controller]
            return (msb_value << 7) | lsb_value
        else:
            # No LSB pair, return MSB value scaled to 14-bit
            return self.controllers[msb_controller] << 7

    def set_gm2_lsb_controller(self, controller: int, value: int):
        """Set a GM2 LSB controller value for 14-bit resolution.

        Args:
            controller: LSB controller number (32-63, 48-51)
            value: LSB value (0-127)
        """
        if 32 <= controller <= 63 or 48 <= controller <= 51:
            self.lsb_values[controller] = value

            # Update corresponding MSB controller parameter with 14-bit value
            for msb, lsb in self.lsb_controller_pairs.items():
                if lsb == controller:
                    self._update_14bit_parameter(msb, self.get_14bit_controller_value(msb))
                    break

    def _update_14bit_parameter(self, controller: int, value_14bit: int):
        """Update synthesis parameter with 14-bit precision.

        Args:
            controller: MSB controller number
            value_14bit: 14-bit parameter value
        """
        # Normalize 14-bit value to unit range
        normalized_value = value_14bit / 16256.0

        if controller == 7:  # Volume
            self._handle_gm2_volume_14bit(normalized_value)
        elif controller == 10:  # Pan
            self._handle_gm2_pan_14bit(normalized_value)
        elif controller == 11:  # Expression
            self._handle_gm2_expression_14bit(normalized_value)
        elif controller == 1:  # Modulation
            self._handle_gm2_modulation_14bit(normalized_value)
        elif controller in [16, 17, 18, 19, 80, 81, 82, 83]:  # GP Controllers
            self._handle_gm2_general_purpose_14bit(controller, normalized_value)
        # Add other 14-bit controllers as needed

    def _handle_gm2_volume_14bit(self, normalized_value: float):
        """Handle GM2 14-bit volume with enhanced precision."""
        # 14-bit volume provides much finer volume control
        self.volume_14bit = normalized_value
        # Could implement dithering or filtering for smooth volume changes
        self.volume = int(normalized_value * 127.0)  # Update 7-bit version too

    def _handle_gm2_pan_14bit(self, normalized_value: float):
        """Handle GM2 14-bit pan with enhanced stereo precision."""
        # 14-bit pan allows for very precise stereo positioning
        self.pan_14bit = normalized_value
        pan_7bit = int(normalized_value * 127.0)
        self.pan = pan_7bit
        self._update_cached_pan()

    def _handle_gm2_expression_14bit(self, normalized_value: float):
        """Handle GM2 14-bit expression with fine dynamic control."""
        self.expression_14bit = normalized_value
        expression_7bit = int(normalized_value * 127.0)
        self.expression = expression_7bit
        self._update_cached_volume()

    def _handle_gm2_modulation_14bit(self, normalized_value: float):
        """Handle GM2 14-bit modulation with precise LFO control."""
        self.modulation_14bit = normalized_value
        modulation_7bit = int(normalized_value * 127.0)
        self.controllers[1] = modulation_7bit

    def _handle_gm2_general_purpose_14bit(self, controller: int, normalized_value: float):
        """Handle GM2 14-bit general purpose controllers."""
        gp_index = {16: 0, 17: 1, 18: 2, 19: 3, 80: 4, 81: 5, 82: 6, 83: 7}.get(controller, 0)
        self.gp_controllers_14bit[gp_index] = normalized_value

        # Could route GP controllers to various modulation destinations
        # For now, store for potential use by effects or modulation matrix

    # GM2 GENERAL PURPOSE CONTROLLERS (80-83)

    def set_gm2_general_purpose_controller(self, controller: int, value: int):
        """Handle GM2 General Purpose controllers (CC80-83).

        These controllers provide additional continuous controls that can be
        mapped to various synthesis or effects parameters.
        """
        if 80 <= controller <= 83:
            self.controllers[controller] = value

            if controller == 80:  # GP5
                self._handle_gm2_gp5(value)
            elif controller == 81:  # GP6
                self._handle_gm2_gp6(value)
            elif controller == 82:  # GP7
                self._handle_gm2_gp7(value)
            elif controller == 83:  # GP8
                self._handle_gm2_gp8(value)

    def _handle_gm2_gp5(self, value: int):
        """Handle GM2 General Purpose 5 controller."""
        # Could be used for effects send, filter modulation, etc.
        # For demonstration, route to modulation matrix
        pass

    def _handle_gm2_gp6(self, value: int):
        """Handle GM2 General Purpose 6 controller."""
        pass

    def _handle_gm2_gp7(self, value: int):
        """Handle GM2 General Purpose 7 controller."""
        pass

    def _handle_gm2_gp8(self, value: int):
        """Handle GM2 General Purpose 8 controller."""
        pass

    # GM2 DATA ENTRY CONTROLS (96-97)

    def handle_gm2_data_increment(self):
        """Handle GM2 Data Increment (CC96)."""
        current_value = self.get_current_rpn_nrpn_value()
        new_value = min(current_value + self.data_entry_increment_step, 16256)
        self.set_rpn_nrpn_value(new_value)

    def handle_gm2_data_decrement(self):
        """Handle GM2 Data Decrement (CC97)."""
        current_value = self.get_current_rpn_nrpn_value()
        new_value = max(current_value - self.data_entry_increment_step, 0)
        self.set_rpn_nrpn_value(new_value)

    def set_data_entry_increment_step(self, step_size: int):
        """Set the step size for data increment/decrement operations."""
        self.data_entry_increment_step = max(1, min(step_size, 16384))

    # ENHANCED RPN/NRPN SUPPORT

    def initialize_gm2_rpn_nrpn_enhancements(self):
        """Initialize enhanced RPN/NRPN support for GM2 compatibility."""
        # Enhanced RPN support beyond XG voice parameters
        self.rpn_parameters_extended = {
            # RPN 0: Pitch Bend Range (already supported)
            # Add additional GM2 RPN parameters
            (0, 1): "channel_fine_tuning",     # Channel Fine Tuning (14-bit)
            (0, 2): "channel_coarse_tuning",   # Channel Coarse Tuning
            (0, 3): "tuning_program_select",   # Tuning Program Select
            (0, 4): "tuning_bank_select",      # Tuning Bank Select
        }

        # Extended NRPN ranges beyond XG voice parameters (MSB 127)
        self.nrpn_parameters_extended = {
            # System-wide parameters (MSB 0, various LSB)
            (0, 440): "pitch_env_depth_range",  # Pitch Envelope Depth Range
            (0, 441): "master_fine_tuning",     # Master Fine Tuning (14-bit)
            (0, 442): "master_coarse_tuning",   # Master Coarse Tuning

            # Effects parameters (various MSB, LSB combinations)
            (1, 0): "reverb_type",             # Reverb Type (0-127 types)
            (1, 1): "reverb_time",             # Reverb Time
            (2, 0): "chorus_type",             # Chorus Type
            (2, 1): "chorus_depth",            # Chorus Depth
            (3, 0): "variation_type",          # Variation Type
            (3, 1): "variation_depth",         # Variation Depth
        }

    # CONTROLLER PERFORMANCE OPTIMIZATIONS

    def implement_controller_batching_enhancement(self):
        """Enhanced controller batching for better performance."""
        # Batch related controllers together for efficient processing
        self.controller_batch_groups = {
            "volume_envelope": [7, 11, 43],    # Volume, Expression, Expression LSB
            "filter_controls": [71, 72, 75],  # Harmonic, Brightness, Filter Cutoff
            "envelope_times": [73, 74, 76],   # Release, Attack, Decay
            "lfo_controls": [77, 78, 79],     # Vibrato Rate, Depth, Delay
            "effects_sends": [91, 92, 93, 94, 95],  # Reverb, Tremolo, Chorus, Celeste, Phaser
            "pan_balance": [8, 10, 40, 42],   # Balance, Pan, Balance LSB, Pan LSB
            "modulation": [1, 33],             # Modulation, Modulation LSB
        }

        # Enhanced batch processing timing
        self.controller_batch_max_delay = 5  # Process batch within 5ms
        self.controller_batch_last_processed = time.time()

    def process_enhanced_controller_batch(self):
        """Process controller batches with enhanced grouping."""
        current_time = time.time()
        time_since_last_batch = current_time - self.controller_batch_last_processed

        if time_since_last_batch >= (self.controller_batch_max_delay / 1000.0):
            # Process batches by functional group for better performance
            for group_name, controllers in self.controller_batch_groups.items():
                if any(c in self.pending_controller_updates for c in controllers):
                    self._process_controller_group_batch(group_name, controllers)

            self.pending_controller_updates.clear()
            self.controller_batch_last_processed = current_time

    def _process_controller_group_batch(self, group_name: str, controllers: List[int]):
        """Process a group of related controllers together."""
        if group_name == "volume_envelope":
            self._batch_process_volume_envelope()
        elif group_name == "filter_controls":
            self._batch_process_filter_controls()
        elif group_name == "lfo_controls":
            self._batch_process_lfo_controls()
        # Add other group processors...

    def _batch_process_volume_envelope(self):
        """Batch process volume and envelope controls together."""
        # Efficiently update volume, expression, and related parameters
        pass

    def _batch_process_filter_controls(self):
        """Batch process filter controls for stable filter response."""
        pass

    def _batch_process_lfo_controls(self):
        """Batch process LFO controls for consistent modulation."""
        pass

    # COMPATIBILITY MODE SUPPORT

    def set_gm2_compatibility_mode(self, enabled: bool):
        """Enable/disable GM2 compatibility features."""
        self.gm2_mode_enabled = enabled

        if enabled:
            # Initialize GM2-specific features
            self.initialize_gm2_rpn_nrpn_enhancements()
            self.implement_controller_batching_enhancement()

            # Set default 14-bit values
            for param_name, param_info in self.gm2_controller_ranges.items():
                setattr(self, f"{param_name}_14bit", param_info["default"] / 16256.0)

            print(f"GM2 Compatibility Mode enabled for channel {self.channel}")
        else:
            # Revert to GM/XG only mode
            print(f"GM2 Compatibility Mode disabled for channel {self.channel}")
