# XG PHASE A: COMMUNICATION HANDLER EXTENSIONS\n# Add these methods to XGCommunicationHandler class\n
    # EXTENDED VOICE PARAMETER HANDLING - PHASE A

    def handle_voice_nrpn(self, msb: int, lsb: int, data_msb: int, data_lsb: int,
                         channel: int = None) -> bool:
        """Handle XG Voice Parameters (MSB 127) NRPN messages.

        Args:
            msb: NRPN MSB (should be 127 for voice parameters)
            lsb: NRPN LSB (0-31 for voice parameters)
            data_msb: Data MSB (14-bit value high 7 bits)
            data_lsb: Data LSB (14-bit value low 7 bits)
            channel: MIDI channel (0-15)

        Returns:
            True if parameter was handled
        """
        if msb != 127:
            return False  # Not a voice parameter

        # Combine to 14-bit value
        data_value = (data_msb << 7) | data_lsb

        # Handle voice parameter based on LSB
        if lsb == 0:  # Element Switch
            element_switch_value = data_value & 0xFF  # 8-bit bitfield
            self._route_voice_element_switch(channel, element_switch_value)
        elif lsb == 1:  # Velocity Limit High
            velocity_high = min(127, data_value >> 7)  # MSB
            self._route_voice_velocity_limit_high(channel, velocity_high)
        elif lsb == 2:  # Velocity Limit Low
            velocity_low = min(127, data_value >> 7)
            self._route_voice_velocity_limit_low(channel, velocity_low)
        elif lsb == 3:  # Note Limit High
            note_high = min(127, data_value >> 7)
            self._route_voice_note_limit_high(channel, note_high)
        elif lsb == 4:  # Note Limit Low
            note_low = min(127, data_value >> 7)
            self._route_voice_note_limit_low(channel, note_low)
        elif lsb == 5:  # Note Shift
            shift_semitones = (data_value >> 7) - 64  # -64 to +63
            self._route_voice_note_shift(channel, shift_semitones)
        elif lsb == 6:  # Detune
            detune_cents = ((data_value >> 7) - 64) * 100 / 16  # XG formula
            self._route_voice_detune(channel, detune_cents)
        elif lsb == 7:  # Velocity Sensitivity
            vel_sens = data_value >> 7
            self._route_voice_velocity_sensitivity(channel, vel_sens)
        elif lsb == 8:  # Volume
            volume = (data_value >> 7) / 127.0
            self._route_voice_volume(channel, volume)
        elif lsb == 9:  # Velocity Rate Sensitivity
            rate_sens = ((data_value >> 7) - 64) / 32.0
            self._route_voice_velocity_rate_sens(channel, rate_sens)
        elif lsb == 10:  # Pan
            pan_pos = ((data_value >> 7) - 64) / 64.0
            self._route_voice_pan(channel, pan_pos)
        elif lsb == 11:  # Assign Mode
            assign_mode = data_value >> 7
            self._route_voice_assign_mode(channel, assign_mode)
        elif lsb == 12:  # Fine Tuning
            fine_tune = ((data_value >> 7) - 64) / 8192.0
            self._route_voice_fine_tuning(channel, fine_tune)
        elif lsb == 13:  # Coarse Tuning
            coarse_tune = (data_value >> 7) - 64
            self._route_voice_coarse_tuning(channel, coarse_tune)
        elif lsb == 14:  # Pitch Random
            random_range = (data_value >> 7) / 100.0  # 0-1.27 semitones
            self._route_voice_pitch_random(channel, random_range)
        elif lsb == 15:  # Pitch Scale Tuning
            scale_tune = (data_value >> 7) - 64
            self._route_voice_scale_tuning(channel, scale_tune)
        elif lsb == 16:  # Pitch Scale Sensitivity
            scale_sens = (data_value >> 7) - 64
            self._route_voice_scale_sensitivity(channel, scale_sens)
        elif lsb == 17:  # Delay Mode
            delay_mode = data_value >> 7
            self._route_voice_delay_mode(channel, delay_mode)
        elif lsb == 18:  # Delay Time
            delay_time = data_value  # 14-bit sample count
            self._route_voice_delay_time(channel, delay_time)
        elif lsb == 19:  # Delay Feedback
            delay_feedback = (data_value >> 7) / 127.0
            self._route_voice_delay_feedback(channel, delay_feedback)
        else:
            return False  # Invalid LSB for voice parameters

        return True

    # Voice parameter routing methods (would interface with voice management)
    def _route_voice_element_switch(self, channel: int, value: int):
        """Route element switch to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_element_switch(channel, value)

    def _route_voice_velocity_limit_high(self, channel: int, value: int):
        """Route velocity high limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_limit_high(channel, value)

    def _route_voice_velocity_limit_low(self, channel: int, value: int):
        """Route velocity low limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_limit_low(channel, value)

    def _route_voice_note_limit_high(self, channel: int, value: int):
        """Route note high limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_limit_high(channel, value)

    def _route_voice_note_limit_low(self, channel: int, value: int):
        """Route note low limit to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_limit_low(channel, value)

    def _route_voice_note_shift(self, channel: int, value: int):
        """Route note shift to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_note_shift(channel, value)

    def _route_voice_detune(self, channel: int, value: float):
        """Route detune to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_detune(channel, value)

    def _route_voice_velocity_sensitivity(self, channel: int, value: int):
        """Route velocity sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_sensitivity(channel, value)

    def _route_voice_volume(self, channel: int, value: float):
        """Route voice volume to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_volume(channel, value)

    def _route_voice_velocity_rate_sens(self, channel: int, value: float):
        """Route velocity rate sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_velocity_rate_sens(channel, value)

    def _route_voice_pan(self, channel: int, value: float):
        """Route voice pan to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_pan(channel, value)

    def _route_voice_assign_mode(self, channel: int, value: int):
        """Route assign mode to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_assign_mode(channel, value)

    def _route_voice_fine_tuning(self, channel: int, value: float):
        """Route fine tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_fine_tuning(channel, value)

    def _route_voice_coarse_tuning(self, channel: int, value: int):
        """Route coarse tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_coarse_tuning(channel, value)

    def _route_voice_pitch_random(self, channel: int, value: float):
        """Route pitch random to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_pitch_random(channel, value)

    def _route_voice_scale_tuning(self, channel: int, value: int):
        """Route scale tuning to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_scale_tuning(channel, value)

    def _route_voice_scale_sensitivity(self, channel: int, value: int):
        """Route scale sensitivity to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_scale_sensitivity(channel, value)

    def _route_voice_delay_mode(self, channel: int, value: int):
        """Route delay mode to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_mode(channel, value)

    def _route_voice_delay_time(self, channel: int, value: int):
        """Route delay time to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_time(channel, value)

    def _route_voice_delay_feedback(self, channel: int, value: float):
        """Route delay feedback to voice manager."""
        if hasattr(self, 'voice_manager'):
            self.voice_manager.set_voice_delay_feedback(channel, value)
