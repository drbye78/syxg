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

    def __init__(self, state_manager, drum_manager, effect_manager):
        """
        Initialize MIDI message handler.

        Args:
            state_manager: StateManager instance for channel state management
            drum_manager: DrumManager instance for drum parameter handling
            effect_manager: Effect manager for effect parameter processing
        """
        self.state_manager = state_manager
        self.drum_manager = drum_manager
        self.effect_manager = effect_manager

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
        Process a System Exclusive message.

        Args:
            data: SYSEX message data

        Returns:
            True if message was processed, False otherwise
        """
        if len(data) < 3 or data[0] != MIDI_CONSTANTS["SYSTEM_EXCLUSIVE"] or data[-1] != MIDI_CONSTANTS["END_OF_EXCLUSIVE"]:
            return False

        # Check manufacturer ID
        if len(data) >= 2 and data[1] == 0x43:  # Yamaha
            return self._handle_yamaha_sysex(data)
        else:
            # Other manufacturers - not handled
            return False

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
            elif controller == 91:  # Reverb Send
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 160, value)
            elif controller == 93:  # Chorus Send
                # Pass value to effect manager
                self.effect_manager.set_channel_effect_parameter(channel, 0, 161, value)
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
        Handle Non-Registered Parameter Number.

        Args:
            channel: MIDI channel (0-15)
            nrpn_msb: NRPN MSB value
            nrpn_lsb: NRPN LSB value

        Returns:
            True if handled successfully
        """
        data_msb, data_lsb = self.state_manager.get_current_data_entry(channel)

        # Check if this is an effect parameter NRPN
        if self.effect_manager.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb, channel):
            return True

        # Check if this is a drum parameter
        if channel == XG_CONSTANTS["DRUM_SETUP_CHANNEL"]:
            return self.drum_manager.handle_xg_drum_setup_nrpn(channel, nrpn_msb, nrpn_lsb, data_msb, data_lsb)

        # Other NRPN handling would go here
        return True

    def _handle_yamaha_sysex(self, data: list) -> bool:
        """
        Handle Yamaha System Exclusive messages.

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

        # Forward message to effect manager
        return self.effect_manager.handle_sysex([0x43], data[1:])  # 0x43 - Yamaha manufacturer ID

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
