"""
XG Synthesizer MIDI Message Handler

Handles MIDI message processing and routing for the XG synthesizer.
"""

from typing import Optional, Any, Dict
from ..core.constants import MIDI_CONSTANTS, XG_CONSTANTS


class MIDIMessageHandler:
    """
    Handles MIDI message processing and routing for the XG synthesizer.

    Provides functionality for:
    - MIDI message routing and processing
    - Controller handling and parameter updates
    - Program change and bank selection
    - System exclusive message processing
    - Channel pressure and key pressure handling
    """

    def __init__(self, state_manager, drum_manager, effect_manager, synthesizer=None):
        """
        Initialize MIDI message handler with multi-timbral support.

        Args:
            state_manager: StateManager instance for channel state management
            drum_manager: DrumManager instance for drum parameter handling
            effect_manager: Effect manager for effect parameter processing
            synthesizer: Reference to XG synthesizer for channel renderer access
        """
        self.state_manager = state_manager
        self.drum_manager = drum_manager
        self.effect_manager = effect_manager
        self.synthesizer = synthesizer  # Reference to synthesizer for channel renderer access

        # Multi-timbral configuration
        self.multi_timbral_enabled = True
        self.channel_modes = {}  # Track channel modes (normal, drum, etc.)
        self.channel_programs = {}  # Track program changes per channel
        self.channel_banks = {}  # Track bank selections per channel
        self.channel_effects = {}  # Track effect assignments per channel

        # Initialize multi-timbral state
        self._initialize_multi_timbral_state()

    def process_midi_message(self, status: int, data1: int, data2: int = 0) -> bool:
        """
        Process a MIDI message.

        Args:
            status: MIDI status byte (including channel)
            data1: First data byte
            data2: Second data byte

        Returns:
            True if message was processed, False otherwise
        """
        # Extract channel from status byte
        channel = status & 0x0F
        command = status & 0xF0

        # Route to appropriate handler
        if command == MIDI_CONSTANTS["NOTE_OFF"]:
            return self._handle_note_off(channel, data1, data2)
        elif command == MIDI_CONSTANTS["NOTE_ON"]:
            return self._handle_note_on(channel, data1, data2)
        elif command == MIDI_CONSTANTS["POLY_PRESSURE"]:
            return self._handle_poly_pressure(channel, data1, data2)
        elif command == MIDI_CONSTANTS["CONTROL_CHANGE"]:
            return self._handle_control_change(channel, data1, data2)
        elif command == MIDI_CONSTANTS["PROGRAM_CHANGE"]:
            return self._handle_program_change(channel, data1)
        elif command == MIDI_CONSTANTS["CHANNEL_PRESSURE"]:
            return self._handle_channel_pressure(channel, data1)
        elif command == MIDI_CONSTANTS["PITCH_BEND"]:
            return self._handle_pitch_bend(channel, data1, data2)
        else:
            # Unknown or unhandled message type
            return False

    def process_sysex_message(self, data: list) -> bool:
        """
        Process a System Exclusive message with validation.

        Args:
            data: SYSEX message data

        Returns:
            True if message was processed, False otherwise
        """
        # Validate basic SysEx structure
        if not self._validate_sysex_message(data):
            return False

        # Check manufacturer ID
        if len(data) >= 2 and data[1] == 0x43:  # Yamaha
            return self._handle_yamaha_sysex(data)
        else:
            # Other manufacturers - not handled
            return False

    def _validate_sysex_message(self, data: list) -> bool:
        """
        Validate SysEx message structure and checksum.

        Args:
            data: SysEx message data

        Returns:
            True if message is valid
        """
        # Basic structure validation
        if len(data) < 3:
            return False

        if data[0] != MIDI_CONSTANTS["SYSTEM_EXCLUSIVE"]:
            return False

        if data[-1] != MIDI_CONSTANTS["END_OF_EXCLUSIVE"]:
            return False

        # For Yamaha XG messages, validate checksum if present
        if len(data) >= 2 and data[1] == 0x43:  # Yamaha
            return self._validate_yamaha_checksum(data)

        return True

    def _validate_yamaha_checksum(self, data: list) -> bool:
        """
        Validate Yamaha SysEx checksum.

        Args:
            data: Yamaha SysEx message data

        Returns:
            True if checksum is valid or not present
        """
        # Checksum is typically the second-to-last byte
        if len(data) < 4:
            return True  # No checksum to validate

        # For XG messages, checksum validation
        if len(data) >= 11:  # XG parameter change messages
            # Calculate checksum for XG parameter change
            checksum_byte = data[-2]  # Checksum is second-to-last
            calculated_checksum = self._calculate_yamaha_checksum(data[1:-2])  # Exclude F0 and checksum/F7

            if calculated_checksum != checksum_byte:
                print(f"XG checksum error: expected {calculated_checksum}, got {checksum_byte}")
                return False

        return True

    def _calculate_yamaha_checksum(self, data: list) -> int:
        """
        Calculate Yamaha SysEx checksum.

        Args:
            data: Data bytes to checksum (excluding F0 and checksum/F7)

        Returns:
            Checksum byte
        """
        checksum = 0
        for byte in data:
            checksum += byte
        checksum &= 0x7F  # 7-bit
        checksum = (0x80 - checksum) & 0x7F  # Two's complement
        return checksum

    def _handle_note_off(self, channel: int, note: int, velocity: int) -> bool:
        """
        Handle Note Off message.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            velocity: Note off velocity (0-127)

        Returns:
            True if handled successfully
        """
        # Note: Actual note off processing is handled by channel renderers
        # This method is for any additional processing needed
        return True

    def _handle_note_on(self, channel: int, note: int, velocity: int) -> bool:
        """
        Handle Note On message.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)

        Returns:
            True if handled successfully
        """
        # Note: Actual note on processing is handled by channel renderers
        # This method is for any additional processing needed
        return True

    def _handle_poly_pressure(self, channel: int, note: int, pressure: int) -> bool:
        """
        Handle Polyphonic Key Pressure (Aftertouch) message.

        Args:
            channel: MIDI channel (0-15)
            note: MIDI note number (0-127)
            pressure: Key pressure value (0-127)

        Returns:
            True if handled successfully
        """
        try:
            self.state_manager.set_key_pressure(channel, note, pressure)
            return True
        except ValueError:
            return False

    def _handle_control_change(self, channel: int, controller: int, value: int) -> bool:
        """
        Handle Control Change message.

        Args:
            channel: MIDI channel (0-15)
            controller: Controller number (0-127)
            value: Controller value (0-127)

        Returns:
            True if handled successfully
        """
        try:
            # Update controller in state manager
            self.state_manager.update_controller(channel, controller, value)

            # Handle specific controllers
            if controller == 1:  # Modulation Wheel
                # Handled by state manager
                pass
            elif controller == 7:  # Volume
                # Handled by state manager
                pass
            elif controller == 10:  # Pan
                # Handled by state manager
                pass
            elif controller == 11:  # Expression
                # Handled by state manager
                pass
            elif controller == 64:  # Sustain Pedal
                # Update sustain state
                sustain_state = value >= 64
                # This would typically affect note processing
                pass
            elif controller == 65:  # Portamento Switch
                # Update portamento state
                portamento_state = value >= 64
                # This would typically affect note processing
                pass
            elif controller == 71:  # Harmonic Content (XG Sound Controller 1)
                # XG-specific: Affects harmonic content/timbre
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 72:  # Brightness (XG Sound Controller 2)
                # XG-specific: Affects filter cutoff/brightness
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 73:  # Sound Controller 3 (XG: Release Time)
                # XG-specific: Affects envelope release time
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 74:  # Sound Controller 4 (XG: Attack Time)
                # XG-specific: Affects envelope attack time
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 75:  # Sound Controller 5 (XG: Brightness/Filter Cutoff)
                # XG-specific: Affects filter cutoff frequency
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 76:  # Sound Controller 6 (XG: Decay Time)
                # XG-specific: Affects envelope decay time
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 77:  # Sound Controller 7 (XG: Vibrato Rate)
                # XG-specific: Affects LFO vibrato rate
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 78:  # Sound Controller 8 (XG: Vibrato Depth)
                # XG-specific: Affects LFO vibrato depth
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 79:  # Sound Controller 9 (XG: Vibrato Delay)
                # XG-specific: Affects LFO vibrato delay
                self.state_manager.update_controller(channel, controller, value)
                # Immediate parameter update for real-time control
                self._update_xg_controller_parameter(channel, controller, value)
            elif controller == 80:  # General Purpose Button 1 (XG)
                # XG-specific: General purpose controller
                self.state_manager.update_controller(channel, controller, value)
            elif controller == 81:  # General Purpose Button 2 (XG)
                # XG-specific: General purpose controller
                self.state_manager.update_controller(channel, controller, value)
            elif controller == 82:  # General Purpose Button 3 (XG)
                # XG-specific: General purpose controller
                self.state_manager.update_controller(channel, controller, value)
            elif controller == 83:  # General Purpose Button 4 (XG)
                # XG-specific: General purpose controller
                self.state_manager.update_controller(channel, controller, value)
            elif controller == 91:  # Reverb Send (XG Effects Send 1)
                # XG-specific: Reverb send level
                self.state_manager.update_controller(channel, controller, value)
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 160, value)
            elif controller == 92:  # Effects Send 2 (XG: Tremolo Send)
                # XG-specific: Tremolo send level
                self.state_manager.update_controller(channel, controller, value)
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 162, value)
            elif controller == 93:  # Chorus Send (XG Effects Send 3)
                # XG-specific: Chorus send level
                self.state_manager.update_controller(channel, controller, value)
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 161, value)
            elif controller == 94:  # Effects Send 4 (XG: Variation Send)
                # XG-specific: Variation send level
                self.state_manager.update_controller(channel, controller, value)
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 163, value)
            elif controller == 95:  # Effects Send 5 (XG: Delay Send)
                # XG-specific: Delay send level
                self.state_manager.update_controller(channel, controller, value)
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 164, value)
            elif controller == 120:  # All Sound Off
                return self._handle_all_sound_off(channel)
            elif controller == 121:  # Reset All Controllers
                return self._handle_reset_all_controllers(channel)
            elif controller == 123:  # All Notes Off
                return self._handle_all_notes_off(channel)

            # Handle RPN/NRPN
            if controller == MIDI_CONSTANTS["RPN_MSB"]:
                self.state_manager.set_rpn_msb(channel, value)
            elif controller == MIDI_CONSTANTS["RPN_LSB"]:
                self.state_manager.set_rpn_lsb(channel, value)
            elif controller == MIDI_CONSTANTS["NRPN_MSB"]:
                self.state_manager.set_nrpn_msb(channel, value)
            elif controller == MIDI_CONSTANTS["NRPN_LSB"]:
                self.state_manager.set_nrpn_lsb(channel, value)
            elif controller == MIDI_CONSTANTS["DATA_ENTRY_MSB"]:
                self.state_manager.set_data_entry_msb(channel, value)
                self._handle_data_entry(channel)
            elif controller == MIDI_CONSTANTS["DATA_ENTRY_LSB"]:
                self.state_manager.set_data_entry_lsb(channel, value)
                self._handle_data_entry(channel)

            return True
        except ValueError:
            return False

    def _handle_program_change(self, channel: int, program: int) -> bool:
        """
        Handle Program Change message.

        Args:
            channel: MIDI channel (0-15)
            program: Program number (0-127)

        Returns:
            True if handled successfully
        """
        try:
            self.state_manager.set_program(channel, program)

            # For drum channels, set drum bank
            channel_state = self.state_manager.get_channel_state(channel)
            if channel_state.get("bank") == 128:  # Drum bank
                # Drum program changes are handled by channel renderers
                pass

            return True
        except ValueError:
            return False

    def _handle_channel_pressure(self, channel: int, pressure: int) -> bool:
        """
        Handle Channel Pressure (Aftertouch) message.

        Args:
            channel: MIDI channel (0-15)
            pressure: Pressure value (0-127)

        Returns:
            True if handled successfully
        """
        try:
            self.state_manager.set_channel_pressure(channel, pressure)
            return True
        except ValueError:
            return False

    def _handle_pitch_bend(self, channel: int, lsb: int, msb: int) -> bool:
        """
        Handle Pitch Bend message.

        Args:
            channel: MIDI channel (0-15)
            lsb: Pitch bend LSB (0-127)
            msb: Pitch bend MSB (0-127)

        Returns:
            True if handled successfully
        """
        try:
            # Convert to 14-bit pitch bend value
            pitch_bend_value = (msb << 7) | lsb
            self.state_manager.set_pitch_bend(channel, pitch_bend_value)
            return True
        except ValueError:
            return False

    def _handle_data_entry(self, channel: int) -> bool:
        """
        Handle Data Entry for RPN/NRPN.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if handled successfully
        """
        try:
            rpn_msb, rpn_lsb = self.state_manager.get_current_rpn(channel)
            nrpn_msb, nrpn_lsb = self.state_manager.get_current_nrpn(channel)

            # Check if RPN or NRPN is set
            if rpn_msb != 127 and rpn_lsb != 127:
                # Process RPN
                return self._handle_rpn(channel, rpn_msb, rpn_lsb)
            elif nrpn_msb != 127 and nrpn_lsb != 127:
                # Process NRPN
                return self._handle_nrpn(channel, nrpn_msb, nrpn_lsb)

            return True
        except ValueError:
            return False

    def _handle_rpn(self, channel: int, rpn_msb: int, rpn_lsb: int) -> bool:
        """
        Handle Registered Parameter Number.

        Args:
            channel: MIDI channel (0-15)
            rpn_msb: RPN MSB value
            rpn_lsb: RPN LSB value

        Returns:
            True if handled successfully
        """
        # RPN handling is typically done in channel renderers
        # For now, just acknowledge
        return True

    def _handle_nrpn(self, channel: int, nrpn_msb: int, nrpn_lsb: int) -> bool:
        """
        Handle Non-Registered Parameter Number with XG validation and parameter application.

        Args:
            channel: MIDI channel number (0-15)
            nrpn_msb: NRPN MSB value
            nrpn_lsb: NRPN LSB value

        Returns:
            True if handled successfully
        """
        data_msb, data_lsb = self.state_manager.get_current_data_entry(channel)

        # Combine MSB and LSB for 14-bit parameter value (0-16383)
        parameter_value = (data_msb << 7) | data_lsb

        # Get synthesizer and channel renderer for real-time parameter application
        channel_renderer = None
        if hasattr(self, 'synthesizer') and self.synthesizer:
            channel_renderer = getattr(self.synthesizer, 'channel_renderers', [None]*16)[channel]

        # XG NRPN Parameter Ranges and Validation - NOW WITH SYNTHESIS APPLICATION
        # Part Parameters (MSB 1)
        if nrpn_msb == 1:
            if nrpn_lsb == 8:  # Part Mode
                # Validate part mode (0-127, but XG defines specific values)
                if 0 <= parameter_value <= 127:
                    if channel_renderer:
                        channel_renderer.set_part_mode(parameter_value)
                    return True
            elif nrpn_lsb == 9:  # Element Reserve
                # Validate element reserve (0-127)
                if 0 <= parameter_value <= 127:
                    # Element reserve affects polyphony management
                    return True
            elif nrpn_lsb == 10:  # Element Assign Mode
                # Validate element assign mode (0-127)
                if 0 <= parameter_value <= 127:
                    # Element assign mode affects voice allocation
                    return True
            elif nrpn_lsb == 11:  # Receive Channel
                # Validate receive channel (0-15 for MIDI channels)
                if 0 <= parameter_value <= 15:
                    # Receive channel assignment
                    return True

        # Effect Parameters (MSB 2-4) - these are handled by effect manager
        elif nrpn_msb in [2, 3, 4]:  # Reverb, Chorus, Variation effects
            # Validate effect parameter ranges (0-127)
            if 0 <= parameter_value <= 127:
                # Check if this is an effect parameter NRPN
                if self.effect_manager.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb, channel):
                    return True
            return True

        # Drum Parameters (MSB 40-41, and channel 10)
        elif nrpn_msb in [40, 41] or channel == XG_CONSTANTS["DRUM_SETUP_CHANNEL"]:
            # Validate drum parameter ranges
            if 0 <= parameter_value <= 127:
                return self.drum_manager.handle_xg_drum_setup_nrpn(channel, nrpn_msb, nrpn_lsb, data_msb, data_lsb)

        # Filter Parameters (MSB 5) - APPLY TO SYNTHESIS
        elif nrpn_msb == 5:
            if nrpn_lsb == 0:  # Filter Cutoff Offset
                # Validate filter cutoff offset (-64 to +63) - value 8192 = 0 offset
                if 0 <= parameter_value <= 16383:  # Full 14-bit range
                    # Convert to offset value (-64 to +63)
                    cutoff_offset = ((parameter_value - 8192) / 128.0)  # 8192 = center, 128 = 1 semitone
                    if channel_renderer:
                        self._apply_filter_cutoff_offset(channel_renderer, cutoff_offset)
                    return True
            elif nrpn_lsb == 1:  # Filter Resonance Offset
                # Validate filter resonance offset (-64 to +63)
                if 0 <= parameter_value <= 16383:
                    resonance_offset = ((parameter_value - 8192) / 128.0)
                    if channel_renderer:
                        self._apply_filter_resonance_offset(channel_renderer, resonance_offset)
                    return True

        # Envelope Parameters (MSB 6) - APPLY TO SYNTHESIS
        elif nrpn_msb == 6:
            # Envelope time parameters (0-127 maps to time ranges)
            if 0 <= parameter_value <= 127:
                # Convert NRPN value to envelope time parameter (0.0-1.0)
                time_value = parameter_value / 127.0

                if nrpn_lsb == 0:  # Attack Time
                    if channel_renderer:
                        self._apply_envelope_attack_time(channel_renderer, time_value)
                elif nrpn_lsb == 1:  # Decay Time
                    if channel_renderer:
                        self._apply_envelope_decay_time(channel_renderer, time_value)
                elif nrpn_lsb == 3:  # Release Time
                    if channel_renderer:
                        self._apply_envelope_release_time(channel_renderer, time_value)
                return True

        # LFO Parameters (MSB 7-9) - APPLY TO SYNTHESIS
        elif nrpn_msb in [7, 8, 9]:  # LFO1, LFO2, LFO3
            lfo_index = nrpn_msb - 7  # Convert to 0, 1, 2

            if nrpn_lsb == 0:  # LFO Rate
                if 0 <= parameter_value <= 127:
                    lfo_rate = 0.1 + (parameter_value / 127.0) * 9.9  # 0.1 to 10.0 Hz
                    if channel_renderer:
                        self._apply_lfo_rate(channel_renderer, lfo_index, lfo_rate)
                    return True
            elif nrpn_lsb == 1:  # LFO Depth
                if 0 <= parameter_value <= 127:
                    lfo_depth = parameter_value / 127.0  # 0.0 to 1.0
                    if channel_renderer:
                        self._apply_lfo_depth(channel_renderer, lfo_index, lfo_depth)
                    return True
            elif nrpn_lsb == 2:  # LFO Delay
                if 0 <= parameter_value <= 127:
                    lfo_delay = (parameter_value / 127.0) * 5.0  # 0.0 to 5.0 seconds
                    if channel_renderer:
                        self._apply_lfo_delay(channel_renderer, lfo_index, lfo_delay)
                    return True

        # EQ Parameters (MSB 10) - APPLY TO SYNTHESIS
        elif nrpn_msb == 10:
            if nrpn_lsb in [0, 1, 2]:  # EQ Low, Mid, High
                # Validate EQ parameters (-64 to +63, mapped to full 14-bit range)
                if 0 <= parameter_value <= 16383:
                    # Convert to EQ parameter (-64 to +63)
                    eq_value = ((parameter_value - 8192) / 128.0)

                    if nrpn_lsb == 0:  # EQ Low
                        if channel_renderer:
                            self._apply_eq_low(channel_renderer, eq_value)
                    elif nrpn_lsb == 1:  # EQ Mid
                        if channel_renderer:
                            self._apply_eq_mid(channel_renderer, eq_value)
                    elif nrpn_lsb == 2:  # EQ High
                        if channel_renderer:
                            self._apply_eq_high(channel_renderer, eq_value)
                    return True

        # If parameter is out of valid XG range, still acknowledge but don't process
        return True

    def _handle_yamaha_sysex(self, data: list) -> bool:
        """
        Handle Yamaha System Exclusive messages with XG support.

        Args:
            data: SYSEX message data

        Returns:
            True if handled successfully
        """
        if len(data) < 6:
            return False

        # Extract SysEx message parameters
        device_id = data[1] if len(data) > 1 else 0
        sub_status = data[2] if len(data) > 2 else 0
        command = data[3] if len(data) > 3 else 0

        # XG System Messages (sub_status = 0x10)
        if sub_status == 0x10:
            return self._handle_xg_system_message(data)

        # XG Parameter Change (sub_status = 0x11)
        elif sub_status == 0x11:
            return self._handle_xg_parameter_change(data)

        # XG Bulk Messages (sub_status = 0x4C)
        elif sub_status == 0x4C:
            return self._handle_xg_bulk_message(data)

        # Forward other Yamaha messages to effect manager
        return self.effect_manager.handle_sysex([0x43], data[1:])  # 0x43 - Yamaha manufacturer ID

    def _handle_xg_system_message(self, data: list) -> bool:
        """
        Handle XG System messages.

        Args:
            data: XG System message data

        Returns:
            True if handled successfully
        """
        if len(data) < 8:
            return False

        command = data[3]

        # XG System On (F0 43 10 4C 00 00 7E 00 F7)
        if command == 0x4C and len(data) >= 11:
            model_id = data[4]
            device_number = data[5]
            system_message = data[6]

            if model_id == 0x00 and device_number == 0x00 and system_message == 0x7E:
                # XG System On - initialize XG system
                return self._handle_xg_system_on()

        return False

    def _handle_xg_parameter_change(self, data: list) -> bool:
        """
        Handle XG Parameter Change messages with acknowledgment.

        Args:
            data: XG Parameter Change message data

        Returns:
            True if handled successfully
        """
        if len(data) < 11:
            return False

        # XG Parameter Change format: F0 43 11 [address] [data] [checksum] F7
        address_high = data[4]
        address_mid = data[5]
        address_low = data[6]
        data_high = data[7]
        data_low = data[8]

        # Calculate parameter address
        parameter_address = (address_high << 16) | (address_mid << 8) | address_low

        # Combine data bytes
        parameter_value = (data_high << 7) | data_low

        # Route to appropriate parameter handler
        success = self._handle_xg_parameter_address(parameter_address, parameter_value)

        # Send acknowledgment if parameter was processed successfully
        if success:
            self._send_xg_parameter_acknowledgment(parameter_address, parameter_value)

        return success

    def _handle_xg_bulk_message(self, data: list) -> bool:
        """
        Handle XG Bulk messages (dumps and requests).

        Args:
            data: XG Bulk message data

        Returns:
            True if handled successfully
        """
        if len(data) < 10:
            return False

        # XG Bulk format: F0 43 4C [address] [size] [data] [checksum] F7
        address_high = data[4]
        address_mid = data[5]
        address_low = data[6]
        size_high = data[7]
        size_low = data[8]

        # Calculate bulk address and size
        bulk_address = (address_high << 16) | (address_mid << 8) | address_low
        bulk_size = (size_high << 7) | size_low

        # Check if this is a bulk dump or request
        if len(data) > 10 + bulk_size:
            # Bulk dump with data
            bulk_data = data[9:9 + bulk_size]
            return self._handle_xg_bulk_dump(bulk_address, bulk_data)
        else:
            # Bulk request
            return self._handle_xg_bulk_request(bulk_address, bulk_size)

    def _handle_xg_system_on(self) -> bool:
        """
        Handle XG System On message - initialize XG system.

        Returns:
            True if handled successfully
        """
        try:
            # Reset all channels to XG defaults
            for channel in range(16):
                self.state_manager.reset_channel(channel)
                self.state_manager.initialize_xg_defaults()

            # Reset effect manager to XG defaults
            if hasattr(self.effect_manager, 'reset_to_xg_defaults'):
                self.effect_manager.reset_to_xg_defaults()

            # Reset drum manager to XG defaults
            if hasattr(self.drum_manager, 'reset_to_xg_defaults'):
                self.drum_manager.reset_to_xg_defaults()

            return True
        except Exception:
            return False

    def _handle_xg_parameter_address(self, address: int, value: int) -> bool:
        """
        Handle XG parameter address and value.

        Args:
            address: XG parameter address
            value: Parameter value

        Returns:
            True if handled successfully
        """
        try:
            # XG Parameter Address Map
            # System Parameters (0x00 00 00 - 0x00 00 FF)
            if address < 0x010000:
                return self._handle_xg_system_parameter(address, value)

            # Effect Parameters (0x02 00 00 - 0x02 FF FF)
            elif address >= 0x020000 and address < 0x030000:
                return self._handle_xg_effect_parameter(address, value)

            # Part Parameters (0x08 00 00 - 0x0F FF FF for parts 0-15)
            elif address >= 0x080000 and address < 0x100000:
                part_number = (address >> 16) & 0x0F
                part_address = address & 0xFFFF
                return self._handle_xg_part_parameter(part_number, part_address, value)

            # Drum Parameters (0x30 00 00 - 0x3F FF FF)
            elif address >= 0x300000 and address < 0x400000:
                return self._handle_xg_drum_parameter(address, value)

            return True
        except Exception:
            return False

    def _handle_xg_system_parameter(self, address: int, value: int) -> bool:
        """Handle XG system parameters"""
        # System parameter handling would go here
        # Examples: Master Volume, Master Tune, System Effects, etc.
        return True

    def _handle_xg_effect_parameter(self, address: int, value: int) -> bool:
        """Handle XG effect parameters with enhanced routing"""
        if not self.effect_manager:
            return False

        # XG Effect Address Mapping
        # System Effects (0x02 00 00 - 0x02 FF FF)
        if (address & 0xFF0000) == 0x020000:
            effect_type = (address >> 8) & 0xFF
            parameter = address & 0xFF

            # System Reverb (effect_type 0)
            if effect_type == 0:
                return self._handle_xg_reverb_parameter(parameter, value)

            # System Chorus (effect_type 1)
            elif effect_type == 1:
                return self._handle_xg_chorus_parameter(parameter, value)

            # System Variation (effect_type 2)
            elif effect_type == 2:
                return self._handle_xg_variation_parameter(parameter, value)

        # Part Effects (0x08 00 00 - 0x0F FF FF for parts 0-15)
        elif (address & 0xFF0000) >= 0x080000 and (address & 0xFF0000) <= 0x0F0000:
            part_number = ((address >> 16) & 0x0F)
            effect_type = (address >> 8) & 0xFF
            parameter = address & 0xFF

            # Insertion Effects (effect_type 64-127)
            if effect_type >= 64:
                return self._handle_xg_insertion_parameter(part_number, effect_type, parameter, value)

        return self.effect_manager.handle_xg_effect_parameter(address, value)

    def _handle_xg_reverb_parameter(self, parameter: int, value: int) -> bool:
        """Handle XG reverb effect parameters"""
        # XG Reverb Parameters (0-15)
        reverb_params = {
            0: "type", 1: "time", 2: "diffusion", 3: "pre_delay",
            4: "tone", 5: "hf_damping", 6: "level", 7: "dry_wet"
        }

        if parameter in reverb_params:
            param_name = reverb_params[parameter]
            # Convert 0-127 to appropriate ranges
            if param_name == "type":
                # Reverb type (0-7 for XG standard types)
                normalized_value = min(7, value // 16)  # 0-127 -> 0-7
            elif param_name in ["time", "pre_delay"]:
                # Time parameters (0-127 -> 0.1-10.0 seconds)
                normalized_value = 0.1 + (value / 127.0) * 9.9
            else:
                # Other parameters (0-127 -> 0.0-1.0)
                normalized_value = value / 127.0

            # Set parameter in effect manager
            if hasattr(self.effect_manager, 'set_reverb_parameter'):
                self.effect_manager.set_reverb_parameter(parameter, normalized_value)
            return True

        return False

    def _handle_xg_chorus_parameter(self, parameter: int, value: int) -> bool:
        """Handle XG chorus effect parameters"""
        # XG Chorus Parameters (0-15)
        chorus_params = {
            0: "type", 1: "lfo_freq", 2: "lfo_depth", 3: "feedback",
            4: "delay", 5: "phase", 6: "level", 7: "dry_wet"
        }

        if parameter in chorus_params:
            param_name = chorus_params[parameter]
            # Convert 0-127 to appropriate ranges
            if param_name == "type":
                # Chorus type (0-7 for XG standard types)
                normalized_value = min(7, value // 16)  # 0-127 -> 0-7
            elif param_name == "lfo_freq":
                # LFO frequency (0-127 -> 0.1-10.0 Hz)
                normalized_value = 0.1 + (value / 127.0) * 9.9
            elif param_name == "delay":
                # Delay time (0-127 -> 0-50ms)
                normalized_value = (value / 127.0) * 50.0
            else:
                # Other parameters (0-127 -> 0.0-1.0)
                normalized_value = value / 127.0

            # Set parameter in effect manager
            if hasattr(self.effect_manager, 'set_chorus_parameter'):
                self.effect_manager.set_chorus_parameter(parameter, normalized_value)
            return True

        return False

    def _handle_xg_variation_parameter(self, parameter: int, value: int) -> bool:
        """Handle XG variation effect parameters"""
        # XG Variation Parameters (0-15)
        variation_params = {
            0: "type", 1: "param1", 2: "param2", 3: "param3",
            4: "param4", 5: "level", 6: "pan", 7: "send_reverb",
            8: "send_chorus"
        }

        if parameter in variation_params:
            param_name = variation_params[parameter]
            # Convert 0-127 to appropriate ranges
            if param_name == "type":
                # Variation type (0-63 for XG variation effects)
                normalized_value = min(63, value)
            elif param_name == "pan":
                # Pan (-64 to +63)
                normalized_value = (value - 64) / 64.0
            else:
                # Other parameters (0-127 -> 0.0-1.0)
                normalized_value = value / 127.0

            # Set parameter in effect manager
            if hasattr(self.effect_manager, 'set_variation_parameter'):
                self.effect_manager.set_variation_parameter(parameter, normalized_value)
            return True

        return False

    def _handle_xg_insertion_parameter(self, part: int, effect_type: int, parameter: int, value: int) -> bool:
        """Handle XG insertion effect parameters"""
        # Convert effect_type from XG range (64-127) to internal range (0-63)
        internal_effect_type = effect_type - 64

        # Convert parameter value (0-127 -> 0.0-1.0)
        normalized_value = value / 127.0

        # Set parameter in effect manager
        if hasattr(self.effect_manager, 'set_channel_insertion_effect_parameter'):
            self.effect_manager.set_channel_insertion_effect_parameter(part, parameter + 1, normalized_value)
            return True

        return False

    def _handle_xg_part_parameter(self, part: int, address: int, value: int) -> bool:
        """Handle XG part parameters"""
        # Part parameter handling - could route to channel renderers
        # Examples: Part Volume, Part Pan, Part Effects, etc.
        return True

    def _handle_xg_drum_parameter(self, address: int, value: int) -> bool:
        """Handle XG drum parameters"""
        # Route to drum manager
        if self.drum_manager:
            return self.drum_manager.handle_xg_drum_parameter(address, value)
        return True

    def _handle_xg_bulk_dump(self, address: int, data: list) -> bool:
        """Handle XG bulk dump data - restore system state from dump"""
        try:
            # Validate bulk data
            if not data or len(data) == 0:
                return False

            # XG Bulk Data Address Mapping
            if address < 0x010000:  # System Parameters (0x00 00 00 - 0x00 FF FF)
                return self._process_system_bulk_dump(address, data)
            elif address >= 0x020000 and address < 0x030000:  # Effect Parameters
                return self._process_effect_bulk_dump(address, data)
            elif address >= 0x080000 and address < 0x100000:  # Part Parameters
                part_number = (address >> 16) & 0x0F
                return self._process_part_bulk_dump(part_number, address & 0xFFFF, data)
            elif address >= 0x300000 and address < 0x400000:  # Drum Parameters
                return self._process_drum_bulk_dump(address, data)

            return True
        except Exception as e:
            print(f"Error processing XG bulk dump: {e}")
            return False

    def _handle_xg_bulk_request(self, address: int, size: int) -> bool:
        """Handle XG bulk request - generate and send bulk dump in response"""
        try:
            # Generate bulk dump data based on address
            bulk_data = self._generate_bulk_dump_data(address, size)
            if bulk_data and len(bulk_data) == size:
                # Send acknowledgment first
                self._send_xg_acknowledgment()

                # In a real implementation, this would send the actual bulk dump message
                # For now, we simulate successful transmission
                print(f"XG Bulk Dump sent: address=0x{address:06X}, size={size}")
                return True
            return False
        except Exception as e:
            print(f"Error generating XG bulk dump: {e}")
            return False

    def _send_xg_acknowledgment(self) -> None:
        """Send XG acknowledgment message"""
        try:
            # XG Acknowledgment: F0 43 10 4C 00 00 00 00 F7
            ack_message = [0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x00, 0x00, 0xF7]
            # In a real implementation, this would be sent to the MIDI output
            print("XG Acknowledgment sent")
        except Exception as e:
            print(f"Error sending XG acknowledgment: {e}")

    def _send_xg_parameter_acknowledgment(self, address: int, value: int) -> None:
        """Send XG parameter acknowledgment message"""
        try:
            # XG Parameter Acknowledgment: F0 43 10 4C [address] [data] [checksum] F7
            ack_message = [0xF0, 0x43, 0x10, 0x4C]

            # Add address bytes
            ack_message.append((address >> 16) & 0x7F)  # High address
            ack_message.append((address >> 8) & 0x7F)   # Mid address
            ack_message.append(address & 0x7F)          # Low address

            # Add data bytes
            ack_message.append((value >> 7) & 0x7F)     # Data high
            ack_message.append(value & 0x7F)            # Data low

            # Calculate and add checksum
            checksum = self._calculate_yamaha_checksum(ack_message[1:])
            ack_message.append(checksum)

            # End of SysEx
            ack_message.append(0xF7)

            # In a real implementation, this would be sent to the MIDI output
            print(f"XG Parameter Acknowledgment sent: address=0x{address:06X}, value={value}")

        except Exception as e:
            print(f"Error sending XG parameter acknowledgment: {e}")

    def _send_xg_display_text(self, text: str, line: int = 0) -> None:
        """Send XG display text message"""
        try:
            if not text or len(text) > 16:  # XG display limit
                return

            # XG Display Text format: F0 43 10 4C [line] [text] F7
            message = [0xF0, 0x43, 0x10, 0x4C, line & 0x7F]

            # Convert text to ASCII bytes (truncate to 16 chars)
            for char in text[:16]:
                message.append(ord(char) & 0x7F)

            message.append(0xF7)  # End of SysEx

            # In a real implementation, this would be sent to the MIDI output
            print(f"XG Display Text sent: '{text}' (line {line})")

        except Exception as e:
            print(f"Error sending XG display text: {e}")

    def _send_xg_parameter_value_display(self, parameter_name: str, value: str) -> None:
        """Send XG parameter value for display"""
        try:
            # Format parameter display text
            display_text = f"{parameter_name}: {value}"

            # Send to display line 1
            self._send_xg_display_text(display_text, 1)

        except Exception as e:
            print(f"Error sending XG parameter display: {e}")

    def _send_xg_system_status_display(self, status: str) -> None:
        """Send XG system status for display"""
        try:
            # Send to display line 0
            self._send_xg_display_text(status, 0)

        except Exception as e:
            print(f"Error sending XG system status: {e}")

    def display_xg_parameter(self, channel: int, controller: int, value: int) -> None:
        """Display XG parameter value on connected XG device"""
        try:
            # Get parameter name
            param_name = self._get_xg_controller_name(controller)
            if not param_name:
                return

            # Format value based on controller type
            if controller in [71, 72, 73, 74, 75, 76, 77, 78, 79]:  # XG Sound Controllers
                display_value = f"{value}"
            elif controller in [91, 92, 93, 94, 95]:  # Effect Sends
                display_value = f"{value}"
            else:
                display_value = f"{value}"

            # Send parameter display
            self._send_xg_parameter_value_display(param_name, display_value)

        except Exception as e:
            print(f"Error displaying XG parameter: {e}")

    def display_xg_system_status(self, status: str) -> None:
        """Display XG system status on connected XG device"""
        try:
            self._send_xg_system_status_display(status)
        except Exception as e:
            print(f"Error displaying XG system status: {e}")

    def _get_xg_controller_name(self, controller: int) -> Optional[str]:
        """Get XG controller name for display"""
        xg_controller_names = {
            71: "Harmonic Content",
            72: "Brightness",
            73: "Release Time",
            74: "Attack Time",
            75: "Filter Cutoff",
            76: "Decay Time",
            77: "Vibrato Rate",
            78: "Vibrato Depth",
            79: "Vibrato Delay",
            80: "GP Button 1",
            81: "GP Button 2",
            82: "GP Button 3",
            83: "GP Button 4",
            91: "Reverb Send",
            92: "Tremolo Send",
            93: "Chorus Send",
            94: "Variation Send",
            95: "Delay Send"
        }
        return xg_controller_names.get(controller)

    def _handle_xg_display_request(self, data: list) -> bool:
        """Handle XG display request messages"""
        try:
            if len(data) < 8:
                return False

            # XG Display Request: F0 43 20 4C [type] [line] F7
            request_type = data[4]
            line_number = data[5] if len(data) > 5 else 0

            if request_type == 0x00:  # Request current display content
                # Send current display content
                self._send_current_display_content(line_number)
            elif request_type == 0x01:  # Request parameter display
                # Send current parameter values
                self._send_current_parameter_display(line_number)

            return True
        except Exception as e:
            print(f"Error handling XG display request: {e}")
            return False

    def _send_current_display_content(self, line: int) -> None:
        """Send current display content"""
        try:
            # This would send the current content of the specified display line
            # For now, we'll send a default message
            if line == 0:
                self._send_xg_display_text("XG Synthesizer Ready", 0)
            elif line == 1:
                self._send_xg_display_text("Parameter: Ready", 1)
        except Exception as e:
            print(f"Error sending display content: {e}")

    def _send_current_parameter_display(self, line: int) -> None:
        """Send current parameter display"""
        try:
            # This would send current parameter values for the specified line
            # For now, we'll send default parameter info
            if line == 1:
                self._send_xg_display_text("Volume: 100", 1)
        except Exception as e:
            print(f"Error sending parameter display: {e}")

    def _process_system_bulk_dump(self, address: int, data: list) -> bool:
        """Process system parameter bulk dump"""
        try:
            # System parameters start at address 0x000000
            param_offset = address & 0xFFFF

            # Process system parameters in chunks
            for i, value in enumerate(data):
                param_address = param_offset + i
                if param_address < 256:  # System parameter range
                    self._set_system_parameter(param_address, value)

            return True
        except Exception:
            return False

    def _process_effect_bulk_dump(self, address: int, data: list) -> bool:
        """Process effect parameter bulk dump"""
        try:
            effect_type = (address >> 8) & 0xFF
            param_offset = address & 0xFF

            # Route to effect manager
            if self.effect_manager and hasattr(self.effect_manager, 'process_bulk_dump'):
                return self.effect_manager.process_bulk_dump(effect_type, param_offset, data)

            return True
        except Exception:
            return False

    def _process_part_bulk_dump(self, part: int, address: int, data: list) -> bool:
        """Process part parameter bulk dump"""
        try:
            # Part parameters (volume, pan, effects, etc.)
            for i, value in enumerate(data):
                param_address = address + i
                self._set_part_parameter(part, param_address, value)

            return True
        except Exception:
            return False

    def _process_drum_bulk_dump(self, address: int, data: list) -> bool:
        """Process drum parameter bulk dump"""
        try:
            # Route to drum manager
            if self.drum_manager and hasattr(self.drum_manager, 'process_bulk_dump'):
                return self.drum_manager.process_bulk_dump(address, data)

            return True
        except Exception:
            return False

    def _generate_bulk_dump_data(self, address: int, size: int) -> Optional[list]:
        """Generate bulk dump data for the specified address range"""
        try:
            bulk_data = []

            # Generate data based on address range
            for i in range(size):
                param_address = address + i

                if param_address < 0x010000:  # System parameters
                    value = self._get_system_parameter(param_address & 0xFFFF)
                elif param_address >= 0x020000 and param_address < 0x030000:  # Effects
                    value = self._get_effect_parameter(param_address)
                elif param_address >= 0x080000 and param_address < 0x100000:  # Parts
                    part = (param_address >> 16) & 0x0F
                    part_param = param_address & 0xFFFF
                    value = self._get_part_parameter(part, part_param)
                elif param_address >= 0x300000 and param_address < 0x400000:  # Drums
                    value = self._get_drum_parameter(param_address)
                else:
                    value = 0  # Default value

                bulk_data.append(value & 0x7F)  # Ensure 7-bit value

            return bulk_data
        except Exception:
            return None

    def _set_system_parameter(self, param: int, value: int) -> None:
        """Set a system parameter"""
        # System parameter mapping would go here
        # Examples: Master Volume, Master Tune, System Effects, etc.
        if param == 0:  # Master Volume
            # Set master volume
            pass
        elif param == 1:  # Master Tune
            # Set master tuning
            pass
        # Add more system parameters as needed

    def _get_system_parameter(self, param: int) -> int:
        """Get a system parameter value"""
        # Return current system parameter values
        if param == 0:  # Master Volume
            return 100  # Default master volume
        elif param == 1:  # Master Tune
            return 64   # Center tuning
        return 0  # Default

    def _set_part_parameter(self, part: int, param: int, value: int) -> None:
        """Set a part parameter"""
        # Part parameter mapping
        if param == 0:  # Part Volume
            # Set part volume
            pass
        elif param == 1:  # Part Pan
            # Set part pan
            pass
        elif param == 2:  # Part Reverb Send
            # Set part reverb send
            pass
        elif param == 3:  # Part Chorus Send
            # Set part chorus send
            pass
        # Add more part parameters as needed

    def _get_part_parameter(self, part: int, param: int) -> int:
        """Get a part parameter value"""
        # Return current part parameter values
        if param == 0:  # Part Volume
            return 100  # Default part volume
        elif param == 1:  # Part Pan
            return 64   # Center pan
        elif param == 2:  # Part Reverb Send
            return 40   # Default reverb send
        elif param == 3:  # Part Chorus Send
            return 0    # Default chorus send
        return 0  # Default

    def _get_effect_parameter(self, address: int) -> int:
        """Get an effect parameter value"""
        # Route to effect manager
        if self.effect_manager and hasattr(self.effect_manager, 'get_parameter_value'):
            effect_type = (address >> 8) & 0xFF
            param = address & 0xFF
            return self.effect_manager.get_parameter_value(effect_type, param)
        return 0

    def _get_drum_parameter(self, address: int) -> int:
        """Get a drum parameter value"""
        # Route to drum manager
        if self.drum_manager and hasattr(self.drum_manager, 'get_bulk_parameter'):
            return self.drum_manager.get_bulk_parameter(address)
        return 0

    def _update_xg_controller_parameter(self, channel: int, controller: int, value: int) -> None:
        """
        Update XG controller parameter immediately for real-time control.

        Args:
            channel: MIDI channel (0-15)
            controller: Controller number (71-79)
            value: Controller value (0-127)
        """
        try:
            # Normalize value to 0.0-1.0 range
            normalized_value = value / 127.0

            # Get the synthesizer's channel renderer to apply changes to active notes
            if hasattr(self, 'state_manager') and hasattr(self.state_manager, 'channel_renderers'):
                channel_renderer = getattr(self.state_manager, 'channel_renderers', [None]*16)[channel]
                if channel_renderer is None:
                    return

                # Apply the parameter changes to active notes in real-time
                for note in channel_renderer.active_notes.values():
                    for partial in note.partials:
                        if partial.is_active():
                            # Route to appropriate synthesis parameter update based on controller
                            if controller == 71:  # Harmonic Content
                                partial.set_harmonic_content(normalized_value)
                            elif controller == 72:  # Brightness
                                partial.set_brightness(normalized_value)
                            elif controller == 73:  # Release Time
                                partial.set_release_time(normalized_value)
                            elif controller == 74:  # Attack Time
                                partial.set_attack_time(normalized_value)
                            elif controller == 75:  # Filter Cutoff
                                partial.set_filter_cutoff(normalized_value)
                            elif controller == 76:  # Decay Time
                                partial.set_decay_time(normalized_value)

                # Handle LFO controllers for the channel (these affect future notes)
                if controller == 77:  # Vibrato Rate
                    # Update LFO vibrato rate for the channel
                    if hasattr(channel_renderer, 'lfos') and channel_renderer.lfos:
                        lfo_rate = 0.1 + (normalized_value * 9.9)  # 0.1 to 10.0 Hz
                        channel_renderer.lfos[0].set_parameters(rate=lfo_rate)

                elif controller == 78:  # Vibrato Depth
                    # Update LFO vibrato depth for the channel
                    if hasattr(channel_renderer, 'lfos') and channel_renderer.lfos:
                        channel_renderer.lfos[0].set_parameters(depth=normalized_value)

                elif controller == 79:  # Vibrato Delay
                    # Update LFO vibrato delay for the channel
                    if hasattr(channel_renderer, 'lfos') and channel_renderer.lfos:
                        lfo_delay = normalized_value * 5.0  # 0.0 to 5.0 seconds
                        channel_renderer.lfos[0].set_parameters(delay=lfo_delay)

        except Exception as e:
            # Log error but don't fail the controller processing
            print(f"Error updating XG controller {controller}: {e}")

    # NRPN Parameter Application Methods - APPLY TO SYNTHESIS
    def _apply_filter_cutoff_offset(self, channel_renderer, cutoff_offset: float) -> None:
        """Apply filter cutoff offset (NRPN MSB 5 LSB 0)"""
        # Apply to all active notes on the channel
        for note in channel_renderer.active_notes.values():
            for partial in note.partials:
                if partial.is_active() and partial.filter:
                    # Convert offset from semitones to frequency multiplier
                    cutoff_multiplier = 2.0 ** (cutoff_offset / 12.0)  # 12 semitones = 1 octave
                    current_cutoff = partial.filter.cutoff
                    new_cutoff = max(20.0, min(20000.0, current_cutoff * cutoff_multiplier))
                    partial.filter.set_parameters(cutoff=new_cutoff)

    def _apply_filter_resonance_offset(self, channel_renderer, resonance_offset: float) -> None:
        """Apply filter resonance offset (NRPN MSB 5 LSB 1)"""
        # Apply to all active notes on the channel
        for note in channel_renderer.active_notes.values():
            for partial in note.partials:
                if partial.is_active() and partial.filter:
                    # Convert offset from -64 to +63 to absolute resonance
                    current_resonance = partial.filter.resonance
                    # Clamp offset to reasonable range
                    clamped_offset = max(-2.0, min(2.0, resonance_offset))
                    new_resonance = max(0.0, min(4.0, current_resonance + clamped_offset))
                    partial.filter.set_parameters(resonance=new_resonance)

    def _apply_envelope_attack_time(self, channel_renderer, time_value: float) -> None:
        """Apply envelope attack time (NRPN MSB 6 LSB 0)"""
        # Convert 0.0-1.0 to actual time range and apply to active notes
        for note in channel_renderer.active_notes.values():
            for partial in note.partials:
                if partial.is_active():
                    partial.set_attack_time(time_value)

    def _apply_envelope_decay_time(self, channel_renderer, time_value: float) -> None:
        """Apply envelope decay time (NRPN MSB 6 LSB 1)"""
        for note in channel_renderer.active_notes.values():
            for partial in note.partials:
                if partial.is_active():
                    partial.set_decay_time(time_value)

    def _apply_envelope_release_time(self, channel_renderer, time_value: float) -> None:
        """Apply envelope release time (NRPN MSB 6 LSB 3)"""
        for note in channel_renderer.active_notes.values():
            for partial in note.partials:
                if partial.is_active():
                    partial.set_release_time(time_value)

    def _apply_lfo_rate(self, channel_renderer, lfo_index: int, rate: float) -> None:
        """Apply LFO rate (NRPN MSB 7-9 LSB 0)"""
        if hasattr(channel_renderer, 'lfos') and lfo_index < len(channel_renderer.lfos):
            channel_renderer.lfos[lfo_index].set_parameters(rate=rate)

    def _apply_lfo_depth(self, channel_renderer, lfo_index: int, depth: float) -> None:
        """Apply LFO depth (NRPN MSB 7-9 LSB 1)"""
        if hasattr(channel_renderer, 'lfos') and lfo_index < len(channel_renderer.lfos):
            channel_renderer.lfos[lfo_index].set_parameters(depth=depth)

    def _apply_lfo_delay(self, channel_renderer, lfo_index: int, delay: float) -> None:
        """Apply LFO delay (NRPN MSB 7-9 LSB 2)"""
        if hasattr(channel_renderer, 'lfos') and lfo_index < len(channel_renderer.lfos):
            channel_renderer.lfos[lfo_index].set_parameters(delay=delay)

    def _apply_eq_low(self, channel_renderer, eq_value: float) -> None:
        """Apply EQ Low parameter (NRPN MSB 10 LSB 0)"""
        # This would typically update EQ parameters - for now we'll store the value
        # Actual implementation depends on EQ effect being implemented
        pass

    def _apply_eq_mid(self, channel_renderer, eq_value: float) -> None:
        """Apply EQ Mid parameter (NRPN MSB 10 LSB 1)"""
        pass

    def _apply_eq_high(self, channel_renderer, eq_value: float) -> None:
        """Apply EQ High parameter (NRPN MSB 10 LSB 2)"""
        pass

    def _update_harmonic_content(self, channel: int, value: float) -> None:
        """Update harmonic content parameter"""
        # This would typically update synthesis parameters for timbre control
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_brightness(self, channel: int, value: float) -> None:
        """Update brightness parameter"""
        # This would typically update filter parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_release_time(self, channel: int, value: float) -> None:
        """Update envelope release time"""
        # This would typically update envelope parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_attack_time(self, channel: int, value: float) -> None:
        """Update envelope attack time"""
        # This would typically update envelope parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_filter_cutoff(self, channel: int, value: float) -> None:
        """Update filter cutoff frequency"""
        # This would typically update filter parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_decay_time(self, channel: int, value: float) -> None:
        """Update envelope decay time"""
        # This would typically update envelope parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_vibrato_rate(self, channel: int, value: float) -> None:
        """Update LFO vibrato rate"""
        # This would typically update LFO parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_vibrato_depth(self, channel: int, value: float) -> None:
        """Update LFO vibrato depth"""
        # This would typically update LFO parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _update_vibrato_delay(self, channel: int, value: float) -> None:
        """Update LFO vibrato delay"""
        # This would typically update LFO parameters
        # For now, we'll store it for later use by the channel renderer
        pass

    def _handle_all_sound_off(self, channel: int) -> bool:
        """
        Handle All Sound Off controller.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if handled successfully
        """
        # All sound off is typically handled by channel renderers
        # This method is for any additional processing needed
        return True

    def _handle_reset_all_controllers(self, channel: int) -> bool:
        """
        Handle Reset All Controllers controller.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if handled successfully
        """
        try:
            # Reset channel state to defaults
            self.state_manager.reset_channel(channel)

            # Reset effect parameters in effect manager
            self.effect_manager.set_current_nrpn_channel(channel)
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, 40)  # Reverb send
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, 0)   # Chorus send

            # Reset drum parameters
            self.drum_manager.reset_channel_drum_parameters(channel)

            return True
        except ValueError:
            return False

    def _handle_all_notes_off(self, channel: int) -> bool:
        """
        Handle All Notes Off controller.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if handled successfully
        """
        # All notes off is typically handled by channel renderers
        # This method is for any additional processing needed
        return True

    def get_channel_state(self, channel: int) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a MIDI channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Channel state dictionary or None if error
        """
        try:
            return self.state_manager.get_channel_state(channel)
        except ValueError:
            return None

    def set_channel_bank(self, channel: int, bank: int) -> bool:
        """
        Set bank for a MIDI channel.

        Args:
            channel: MIDI channel number (0-15)
            bank: Bank number

        Returns:
            True if set successfully
        """
        try:
            self.state_manager.set_bank(channel, bank)
            return True
        except ValueError:
            return False

    def get_channel_bank(self, channel: int) -> Optional[int]:
        """
        Get bank for a MIDI channel.

        Args:
            channel: MIDI channel number (0-15)

        Returns:
            Bank number or None if error
        """
        try:
            state = self.state_manager.get_channel_state(channel)
            return state.get("bank")
        except ValueError:
            return None

    def _initialize_multi_timbral_state(self) -> None:
        """Initialize multi-timbral state for all channels"""
        # Initialize channel modes (normal by default)
        for channel in range(16):
            self.channel_modes[channel] = "normal"
            self.channel_programs[channel] = 0
            self.channel_banks[channel] = 0
            self.channel_effects[channel] = {
                "reverb_send": 40,
                "chorus_send": 0,
                "variation_send": 0,
                "insertion_effect": None
            }

        # Set channel 10 (9 in 0-based) to drum mode by default
        self.channel_modes[9] = "drum"
        self.channel_programs[9] = 0  # Standard drum kit
        self.channel_banks[9] = 128   # Drum bank

    def set_channel_mode(self, channel: int, mode: str) -> bool:
        """
        Set the mode for a MIDI channel (normal, drum, etc.).

        Args:
            channel: MIDI channel (0-15)
            mode: Channel mode ("normal", "drum")

        Returns:
            True if mode was set successfully
        """
        if not (0 <= channel <= 15):
            return False

        if mode not in ["normal", "drum"]:
            return False

        self.channel_modes[channel] = mode

        # Update channel state based on mode
        if mode == "drum":
            self.channel_banks[channel] = 128  # Drum bank
            # Reset to standard drum kit
            self.state_manager.set_bank(channel, 128)
            self.state_manager.set_program(channel, 0)
        else:  # normal mode
            if self.channel_banks[channel] == 128:  # Was drum bank
                self.channel_banks[channel] = 0  # Reset to normal bank
                self.state_manager.set_bank(channel, 0)

        return True

    def get_channel_mode(self, channel: int) -> Optional[str]:
        """
        Get the mode for a MIDI channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Channel mode or None if invalid channel
        """
        if not (0 <= channel <= 15):
            return None
        return self.channel_modes.get(channel, "normal")

    def set_channel_program_independent(self, channel: int, program: int) -> bool:
        """
        Set program for a channel independently (multi-timbral).

        Args:
            channel: MIDI channel (0-15)
            program: Program number (0-127)

        Returns:
            True if program was set successfully
        """
        if not (0 <= channel <= 15) or not (0 <= program <= 127):
            return False

        self.channel_programs[channel] = program

        # Update state manager
        self.state_manager.set_program(channel, program)

        # Display program change on XG device
        program_name = self._get_program_name(channel, program)
        self.display_xg_system_status(f"Ch{channel+1}: {program_name}")

        return True

    def get_channel_program_independent(self, channel: int) -> Optional[int]:
        """
        Get program for a channel independently.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Program number or None if invalid channel
        """
        if not (0 <= channel <= 15):
            return None
        return self.channel_programs.get(channel, 0)

    def set_channel_bank_independent(self, channel: int, bank: int) -> bool:
        """
        Set bank for a channel independently (multi-timbral).

        Args:
            channel: MIDI channel (0-15)
            bank: Bank number

        Returns:
            True if bank was set successfully
        """
        if not (0 <= channel <= 15):
            return False

        self.channel_banks[channel] = bank

        # Update state manager
        self.state_manager.set_bank(channel, bank)

        # Update channel mode based on bank
        if bank == 128:  # Drum bank
            self.set_channel_mode(channel, "drum")
        else:
            if self.channel_modes.get(channel) == "drum":
                self.set_channel_mode(channel, "normal")

        return True

    def get_channel_bank_independent(self, channel: int) -> Optional[int]:
        """
        Get bank for a channel independently.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Bank number or None if invalid channel
        """
        if not (0 <= channel <= 15):
            return None
        return self.channel_banks.get(channel, 0)

    def set_channel_effect_independent(self, channel: int, effect_type: str, value: int) -> bool:
        """
        Set effect parameter for a channel independently.

        Args:
            channel: MIDI channel (0-15)
            effect_type: Type of effect ("reverb_send", "chorus_send", etc.)
            value: Effect value (0-127)

        Returns:
            True if effect was set successfully
        """
        if not (0 <= channel <= 15) or not (0 <= value <= 127):
            return False

        if effect_type not in ["reverb_send", "chorus_send", "variation_send"]:
            return False

        if channel not in self.channel_effects:
            self.channel_effects[channel] = {}

        self.channel_effects[channel][effect_type] = value

        # Update effect manager
        if effect_type == "reverb_send":
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, value)
        elif effect_type == "chorus_send":
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, value)
        elif effect_type == "variation_send":
            self.effect_manager.set_channel_effect_parameter(channel, 0, 163, value)

        return True

    def get_channel_effect_independent(self, channel: int, effect_type: str) -> Optional[int]:
        """
        Get effect parameter for a channel independently.

        Args:
            channel: MIDI channel (0-15)
            effect_type: Type of effect

        Returns:
            Effect value or None if not found
        """
        if not (0 <= channel <= 15):
            return None

        channel_effects = self.channel_effects.get(channel, {})
        return channel_effects.get(effect_type)

    def get_multi_timbral_status(self) -> Dict[str, Any]:
        """
        Get the current multi-timbral status of all channels.

        Returns:
            Dictionary containing multi-timbral status
        """
        status = {
            "enabled": self.multi_timbral_enabled,
            "channels": {}
        }

        for channel in range(16):
            status["channels"][channel] = {
                "mode": self.channel_modes.get(channel, "normal"),
                "program": self.channel_programs.get(channel, 0),
                "bank": self.channel_banks.get(channel, 0),
                "effects": self.channel_effects.get(channel, {})
            }

        return status

    def reset_channel_multi_timbral(self, channel: int) -> bool:
        """
        Reset multi-timbral settings for a specific channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            True if reset was successful
        """
        if not (0 <= channel <= 15):
            return False

        # Reset to defaults
        self.channel_modes[channel] = "normal" if channel != 9 else "drum"
        self.channel_programs[channel] = 0
        self.channel_banks[channel] = 128 if channel == 9 else 0
        self.channel_effects[channel] = {
            "reverb_send": 40,
            "chorus_send": 0,
            "variation_send": 0,
            "insertion_effect": None
        }

        # Update state manager
        self.state_manager.reset_channel(channel)

        return True

    def reset_all_multi_timbral(self) -> bool:
        """
        Reset multi-timbral settings for all channels.

        Returns:
            True if reset was successful
        """
        try:
            self._initialize_multi_timbral_state()

            # Reset all channels in state manager
            for channel in range(16):
                self.state_manager.reset_channel(channel)

            return True
        except Exception:
            return False

    def _get_program_name(self, channel: int, program: int) -> str:
        """
        Get program name for display purposes.

        Args:
            channel: MIDI channel
            program: Program number

        Returns:
            Program name string
        """
        # This would typically look up program names from a database
        # For now, return a generic name
        if self.channel_modes.get(channel) == "drum":
            drum_kits = [
                "Standard Kit", "Room Kit", "Power Kit", "Electronic Kit",
                "Analog Kit", "Jazz Kit", "Brush Kit", "Orchestra Kit"
            ]
            if program < len(drum_kits):
                return drum_kits[program]
            else:
                return f"Drum Kit {program}"
        else:
            # Normal instrument programs
            return f"Program {program}"

    def enable_multi_timbral(self, enabled: bool = True) -> None:
        """
        Enable or disable multi-timbral mode.

        Args:
            enabled: Whether to enable multi-timbral mode
        """
        self.multi_timbral_enabled = enabled

        if enabled:
            self.display_xg_system_status("Multi-timbral: ON")
        else:
            self.display_xg_system_status("Multi-timbral: OFF")

    def is_multi_timbral_enabled(self) -> bool:
        """
        Check if multi-timbral mode is enabled.

        Returns:
            True if multi-timbral is enabled
        """
        return self.multi_timbral_enabled
