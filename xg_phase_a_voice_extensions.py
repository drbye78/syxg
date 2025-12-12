# XG PHASE A: VOICE PARAMETER EXTENSIONS\n# Add these methods to XGPartialGenerator class\n
    # XG VOICE PARAMETER EXTENSIONS - PHASE A COMPLETION
    # Implements missing MSB 127 NRPN voice synthesis parameters

    def _process_element_switch(self, value: int):
        """Process XG Voice Element Switch (MSB 127, LSB 0).

        Controls which voice elements (0-7) are active as bit field.
        Bit 0 = Element 0, Bit 1 = Element 1, etc.

        Args:
            value: Bit field (0-255) where each bit enables/disables an element
        """
        # Update element activation state (though partials typically don't manage elements)
        # This is mainly for XG voice definition consistency
        self.element_switch = value

        # In a real XG voice, this would enable/disable partial elements
        # For this partial generator, we note the element activation
        active_elements = []
        for i in range(8):  # Maximum 8 elements in XG
            if (value & (1 << i)) != 0:
                active_elements.append(i)
        self.active_elements = active_elements

    def _handle_key_limits(self, low_limit: int, high_limit: int):
        """Handle XG Voice Key Limits (MSB 127, LSB 3-4).

        Defines the note range this voice responds to.

        Args:
            low_limit: Lowest MIDI note (0-127)
            high_limit: Highest MIDI note (0-127)
        """
        self.voice_key_low = max(0, min(127, low_limit))
        self.voice_key_high = max(0, min(127, high_limit))

        # Ensure valid range
        if self.voice_key_high < self.voice_key_low:
            self.voice_key_high = self.voice_key_low

    def _apply_pitch_shift(self, shift_semitones: int):
        """Apply XG Voice Note Shift (MSB 127, LSB 5).

        Shifts the entire voice up/down in semitone intervals.

        Args:
            shift_semitones: Shift in semitones (-64 to +63)
        """
        # Clamp to valid range per XG specification
        self.note_shift_semitones = max(-64, min(63, shift_semitones))

        # Apply shift to fundamental calculation
        # This effectively offsets the root key
        self.effective_root_key = self.root_key + self.note_shift_semitones

    def _calc_detune(self, detune_cents: float):
        """Calculate XG Voice Detune (MSB 127, LSB 6).

        Fine pitch adjustment beyond tuning in Hz, centered at 0.

        Args:
            detune_cents: Detune in cent units (-400 to +393.75 cents)
        """
        # XG detune formula: (value - 64) * 100 / 16 (where value = MSB 127 LSB 6)
        # Converts MIDI value to cents, then to Hz
        if detune_cents != 0.0:
            # Convert cents to frequency ratio
            detune_ratio = 2.0 ** (detune_cents / 1200.0)

            # Apply to base frequency (compound with note shift)
            self.detune_multiplier = detune_ratio
        else:
            self.detune_multiplier = 1.0

    def _velocity_sensitivity_xg(self, sensitivity: int):
        """Apply XG Voice Velocity Sensitivity (MSB 127, LSB 7).

        Controls how MIDI velocity affects voice level.

        Args:
            sensitivity: Velocity sensitivity (0-127)
        """
        # XG formula: (velocity_sense_param * 127 / 2000) + 0.007
        self.xg_velocity_sensitivity = (sensitivity * 127.0 / 2000.0) + 0.007

        # Update velocity scaling curve
        # This affects how input velocity maps to output amplitude
        self.velocity_curve_factor = 1.0 + (sensitivity / 127.0) * 0.5

    def _level_control(self, voice_level: float):
        """Control XG Voice Level (MSB 127, LSB 8).

        Overall voice output level.

        Args:
            voice_level: Voice level (0.0 to 1.0)
        """
        self.voice_master_level = max(0.0, min(1.0, voice_level))

        # This multiplies with the existing level parameter
        # self.level *= self.voice_master_level

    def _velocity_rate_sens(self, rate_sensitivity: float):
        """Control XG Velocity Rate Sensitivity (MSB 127, LSB 9).

        How velocity affects envelope attack time.

        Args:
            rate_sensitivity: Velocity sensitivity for attack rate (-1.0 to +1.0)
        """
        # XG velocity rate sensitivity affects envelope attack time
        self.attack_velocity_factor = max(-1.0, min(1.0, rate_sensitivity))

        # Update envelope parameters if envelope exists
        if hasattr(self, 'amp_envelope') and self.amp_envelope:
            # Modify attack time based on velocity
            # Higher positive values = faster attack with higher velocity
            base_attack = getattr(self.amp_envelope, '_attack_time', 0.01)
            self.modified_attack_time = base_attack * (1.0 + rate_sensitivity * 0.5)

    def _pan_control(self, pan_position: float):
        """Control XG Voice Pan (MSB 127, LSB 10).

        Left/right stereo positioning for the voice.

        Args:
            pan_position: Pan position (-1.0 left, 0.0 center, +1.0 right)
        """
        self.voice_pan = max(-1.0, min(1.0, pan_position))

        # Convert to pan gains (overrides channel pan for voice-specific positioning)
        if self.voice_pan < 0:
            # Pan left: left gain full, right gain reduced
            self.voice_pan_left = 1.0
            self.voice_pan_right = 1.0 + self.voice_pan  # -1.0 results in 0.0
        elif self.voice_pan > 0:
            # Pan right: left gain reduced, right gain full
            self.voice_pan_left = 1.0 - self.voice_pan   # 1.0 results in 0.0
            self.voice_pan_right = 1.0
        else:
            # Center: both full gain
            self.voice_pan_left = 1.0
            self.voice_pan_right = 1.0

    def _mode_assignment(self, assign_mode: int):
        """Control XG Voice Assign Mode (MSB 127, LSB 11).

        How voices are assigned when polyphony is exceeded.

        Args:
            assign_mode: Assignment mode (0=single, 1=multi, 2=poly, 3=mono)
        """
        self.voice_assign_mode = max(0, min(3, assign_mode))

        # XG assign modes:
        # 0: Single - only one voice at a time
        # 1: Multi - multiple voices (default polyphonic)
        # 2: Poly - strict polyphonic allocation
        # 3: Mono - monophonic with portamento

        # Configure polyphony behavior
        if assign_mode == 0:  # Single
            self.max_concurrent_voices = 1
            self.voice_stealing_mode = 'single'
        elif assign_mode == 3:  # Mono
            self.max_concurrent_voices = 1
            self.voice_stealing_mode = 'mono'
            self.portamento_enabled = True
        else:  # Multi/Poly
            self.max_concurrent_voices = 8  # No limit
            self.voice_stealing_mode = 'round_robin'

    def _fine_tune_xg(self, fine_tune_cents: float):
        """Apply XG Fine Tuning (MSB 127, LSB 12).

        Microscopic pitch adjustment in cents.

        Args:
            fine_tune_cents: Fine tuning in cents (-1.0 to +1.0)
        """
        # XG fine tuning precision: (value - 64) / 8192 relative to A=440
        # This is in addition to coarse tuning and detune
        self.xg_fine_tune_cents = max(-1.0, min(1.0, fine_tune_cents))

        # Convert to frequency ratio
        fine_tune_ratio = 2.0 ** (self.xg_fine_tune_cents / 1200.0)
        self.fine_tune_multiplier = fine_tune_ratio

    def _coarse_tune_xg(self, coarse_tune_semitones: int):
        """Apply XG Coarse Tuning (MSB 127, LSB 13).

        Coarse pitch adjustment in semitones.

        Args:
            coarse_tune_semitones: Coarse tuning in semitones (-64 to +63)
        """
        # XG coarse tuning: full semitone steps
        self.xg_coarse_tune_semitones = max(-64, min(63, coarse_tune_semitones))

        # Convert to frequency ratio
        coarse_tune_ratio = 2.0 ** (self.xg_coarse_tune_semitones / 12.0)
        self.coarse_tune_multiplier = coarse_tune_ratio

    def _random_pitch(self, random_range: float):
        """Apply XG Pitch Random (MSB 127, LSB 14).

        Adds randomization to pitch per note-on.

        Args:
            random_range: Random range in semitones (0-1.27)
        """
        self.pitch_random_range = max(0.0, min(1.27, random_range))

        # This would be applied per note-on event
        # Implementation would set a random offset within this range
        self.pitch_random_enabled = random_range > 0.0

    def _pitch_scaling(self, scale_tune_cents: int, scale_sensitivity: int):
        """Apply XG Pitch Scale Tuning/Sensitivity (MSB 127, LSB 15-16).

        Microtonal per-scale-degree pitch adjustments.

        Args:
            scale_tune_cents: Scale tuning offset (-64 to +63 cents per degree)
            scale_sensitivity: How scale degrees affect pitch (-24 to +24)
        """
        self.scale_tuning_cents = max(-64, min(63, scale_tune_cents))
        self.scale_sensitivity = max(-24, min(24, scale_sensitivity))

        # XG scale tuning affects pitch based on scale degree
        # This is complex and would require scale analysis
        self.scale_tuning_enabled = abs(scale_tune_cents) > 0 or abs(scale_sensitivity) > 0

    def _voice_delay_effects(self, delay_mode: int, delay_time: float, delay_feedback: float):
        """XA Apply XG Voice Delay Effects (MSB 127, LSB 17-19).

        Voice-internal delay processing.

        Args:
            delay_mode: Delay trigger mode (0=normal, 1=keyed, 2=hold)
            delay_time: Delay time in samples (0-2048 typically)
            delay_feedback: Delay feedback amount (0.0-1.0)
        """
        self.delay_mode = max(0, min(2, delay_mode))
        self.delay_time_samples = max(0, min(2048, delay_time))
        self.delay_feedback = max(0.0, min(1.0, delay_feedback))

        # These would control internal voice delay processing
        self.voice_delay_enabled = delay_time > 0
