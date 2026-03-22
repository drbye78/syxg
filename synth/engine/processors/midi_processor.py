"""
MIDI Processing System - Complete MIDI Message Handling

Production-quality MIDI message processing for XG/GS/MPE synthesizer with
complete protocol support and sample-perfect timing.
"""

from __future__ import annotations

import math
import struct
import threading

from ...midi.message import MIDIMessage
from ...midi.realtime import RealtimeParser


class MIDIMessageProcessor:
    """
    Complete MIDI message processing system for Modern XG Synthesizer.

    Handles all MIDI message types including XG, GS, MPE, and standard MIDI,
    with support for receive channel mapping, parameter processing, and
    sample-perfect timing.
    """

    def __init__(self, synthesizer):
        """
        Initialize MIDI message processor.

        Args:
            synthesizer: Reference to the parent synthesizer
        """
        self.synthesizer = synthesizer
        self.parser = RealtimeParser()
        self.lock = threading.RLock()

    def process_midi_message(self, message_bytes: bytes):
        """
        Process MIDI message with XG/GS integration using RealtimeParser.
        Supports both MIDI 1.0 and MIDI 2.0 formats.

        Args:
            message_bytes: Raw MIDI message bytes
        """
        with self.lock:
            # Check if this looks like UMP data (starts with valid UMP message type)
            if len(message_bytes) >= 4:
                first_word = struct.unpack(">I", message_bytes[:4])[0]
                ump_type = (first_word >> 28) & 0xF

                # If it's a valid UMP message type, treat as UMP
                if ump_type in [0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0xF]:
                    # Process as UMP packets
                    ump_packets = self.parser.ump_parser.parse_packet_stream(message_bytes)
                    for packet in ump_packets:
                        # Convert UMP packet to MIDIMessage and process
                        if hasattr(self.parser, "_convert_ump_to_midimessage"):
                            midi_message = self.parser._convert_ump_to_midimessage(packet)
                            if midi_message:
                                self._process_standard_midi(midi_message)
                    return

            # Check for XG receive channel SYSEX first
            if self.synthesizer.xg_enabled and self._is_receive_channel_sysex(message_bytes):
                self._handle_receive_channel_sysex(message_bytes)
                if hasattr(self.synthesizer, "performance_monitor"):
                    self.synthesizer.performance_monitor.update(xg_messages_processed=1)
                return

            # GS processing if enabled (GS SYSEX)
            if (
                self.synthesizer.gs_enabled
                and hasattr(self.synthesizer, "gs_midi_processor")
                and self.synthesizer.gs_midi_processor.process_message(message_bytes)
            ):
                return  # GS handled it

            # Parse raw bytes to MIDIMessage
            midi_messages = self.parser.parse_bytes(message_bytes)

            if not midi_messages:
                return  # No valid messages parsed

            # Process each parsed message
            for midi_message in midi_messages:
                # XG processing first if enabled
                if (
                    self.synthesizer.xg_enabled
                    and hasattr(self.synthesizer, "xg_midi_processor")
                    and self.synthesizer.xg_midi_processor.process_message(message_bytes)
                ):
                    if hasattr(self.synthesizer, "performance_monitor"):
                        self.synthesizer.performance_monitor.update(xg_messages_processed=1)
                    return  # XG handled it

                # Standard MIDI processing with structured message
                self._process_standard_midi(midi_message)

    def _is_receive_channel_sysex(self, data: bytes) -> bool:
        """
        Check if SYSEX message is for receive channel assignment.

        Args:
            data: Raw MIDI bytes

        Returns:
            True if this is an XG receive channel SYSEX message
        """
        # Basic validation: must start with 0xF0 and end with 0xF7
        if len(data) < 6 or data[0] != 0xF0 or data[-1] != 0xF7:
            return False

        # Check Yamaha manufacturer ID (0x43 = Yamaha)
        if len(data) < 2 or data[1] != 0x43:
            return False

        # Check XG model ID (0x4C = XG model ID)
        if len(data) < 4 or data[3] != 0x4C:
            return False

        # Check command is 0x08 (receive channel assignment)
        if len(data) < 5 or data[4] != 0x08:
            return False

        # Check that we have at least 2 more bytes for part and channel
        if len(data) < 7:
            return False

        # Check that we have exactly the right number of bytes (9 total for this command)
        if len(data) != 9:
            return False

        # Extract part and channel to validate ranges
        part_id = data[5]
        channel = data[6]

        # Validate ranges
        if not (0 <= part_id <= 15):  # Valid XG part numbers
            return False

        if not (
            0 <= channel <= 15 or channel == 254 or channel == 255
        ):  # Valid channel numbers (0-15, 254=OFF, 255=ALL)
            return False

        # Check device ID matches our device (if synthesizer has device_id attribute)
        if hasattr(self.synthesizer, "device_id"):
            if data[2] != self.synthesizer.device_id:
                return False

        return True

    def _handle_receive_channel_sysex(self, data: bytes):
        """
        Handle XG receive channel SYSEX message.

        Args:
            data: Raw SYSEX data
        """
        if not self.synthesizer.xg_enabled or not hasattr(
            self.synthesizer, "receive_channel_manager"
        ):
            return

        # Extract part and channel from SYSEX data
        # Format: F0 43 [device] 4C 08 [part] [channel] F7
        part_id = data[5]
        midi_channel = data[6]

        # Validate ranges
        if not (0 <= part_id <= 15):
            print(f"XG SYSEX: Invalid part ID {part_id}")
            return

        if midi_channel not in list(range(16)) + [254, 255]:  # 0-15, 254=OFF, 255=ALL
            print(f"XG SYSEX: Invalid MIDI channel {midi_channel}")
            return

        # Set the receive channel mapping
        if self.synthesizer.receive_channel_manager.set_receive_channel(part_id, midi_channel):
            print(
                f"XG SYSEX: Part {part_id} receive channel set to "
                f"{'MIDI CH ' + str(midi_channel) if midi_channel < 16 else 'ALL' if midi_channel == 255 else 'OFF'}"
            )

    def _process_standard_midi(self, midi_message):
        """
        Process standard MIDI messages using structured MIDIMessage objects with XG/GS receive channel mapping.

        Args:
            midi_message: Parsed MIDIMessage object
        """
        # Handle SYSEX and other system messages that don't have channels
        if midi_message.type == "sysex":
            # Reconstruct SYSEX bytes from parsed message
            sysex_data = midi_message.data.get("raw_data", [])

            # Process Arpeggiator SYSEX messages first (Yamaha Motif)
            if hasattr(self.synthesizer, "arpeggiator_sysex_controller"):
                result = self.synthesizer.arpeggiator_sysex_controller.process_sysex_message(
                    bytes(sysex_data)
                )
                if result:
                    return  # Arpeggiator SYSEX handled it

            # Process GS SYSEX messages
            if self.synthesizer.gs_enabled and self.synthesizer.gs_midi_processor.process_message(
                bytes(sysex_data)
            ):
                return  # GS handled it

            # Process XG SYSEX messages
            if self.synthesizer.xg_enabled:
                # Check for XG receive channel SYSEX first
                if self._is_receive_channel_sysex(bytes(sysex_data)):
                    self._handle_receive_channel_sysex(bytes(sysex_data))
                    return

                # Process through XG MIDI processor
                if self.synthesizer.xg_midi_processor.process_message(bytes(sysex_data)):
                    return

            # If not handled by GS or XG, SYSEX is ignored in standard MIDI processing
            return

        # For all other messages, check if they have valid channels
        midi_channel = midi_message.channel
        if midi_channel is None or not (0 <= midi_channel <= 15):  # MIDI channels 0-15
            return

        # Arpeggiator processing first (Yamaha Motif style)
        if hasattr(self.synthesizer, "arpeggiator_system") and midi_message.type in [
            "note_on",
            "note_off",
        ]:
            arpeggiator_status = self.synthesizer.arpeggiator_system.get_arpeggiator_status()
            if arpeggiator_status and arpeggiator_status.get("enabled", False):
                # Arpeggiator is active - let it handle the note through the system
                note = midi_message.data.get("note", 60)
                velocity = midi_message.data.get("velocity", 64)
                if midi_message.type == "note_on":
                    self.synthesizer.arpeggiator_system.process_note_on(
                        midi_channel, note, velocity
                    )
                else:  # note_off
                    self.synthesizer.arpeggiator_system.process_note_off(midi_channel, note)
                # Arpeggiator will generate its own note events via callbacks
                return
            # Arpeggiator is inactive - continue with normal processing

        # XG receive channel mapping - route message to appropriate parts
        if self.synthesizer.xg_enabled and hasattr(self.synthesizer, "receive_channel_manager"):
            target_parts = self.synthesizer.receive_channel_manager.get_parts_for_midi_channel(
                midi_channel
            )

            if target_parts:
                # Route message to all target parts
                for part_id in target_parts:
                    if not (0 <= part_id < len(self.synthesizer.channels)):
                        continue  # Invalid part ID

                    target_channel = self.synthesizer.channels[part_id]

                    # Apply XG modifications if enabled
                    modified_message = self._apply_xg_channel_modifications(part_id, midi_message)

                    # Update channel XG state from message metadata
                    if hasattr(modified_message, "_xg_metadata"):
                        target_channel.update_xg_state_from_message(modified_message._xg_metadata)

                    # Process message based on type
                    self._process_message_on_channel(target_channel, modified_message)
            else:
                # No specific mapping, use default 1:1
                if midi_channel < len(self.synthesizer.channels):
                    target_channel = self.synthesizer.channels[midi_channel]
                    modified_message = self._apply_xg_channel_modifications(
                        midi_channel, midi_message
                    )
                    self._process_message_on_channel(target_channel, modified_message)
        else:
            # Fallback to direct 1:1 mapping when XG is disabled or manager not available
            if midi_channel < len(self.synthesizer.channels):
                target_channel = self.synthesizer.channels[midi_channel]
                modified_message = self._apply_xg_channel_modifications(midi_channel, midi_message)
                self._process_message_on_channel(target_channel, modified_message)

    def _process_message_on_channel(self, target_channel, midi_message):
        """
        Process a MIDI message on a specific channel.

        Args:
            target_channel: Target channel to process message on
            midi_message: MIDI message to process
        """
        msg_type = midi_message.type
        midi_channel = midi_message.channel

        if msg_type == "note_off":
            note = midi_message.data.get("note", 60)
            velocity = midi_message.data.get("velocity", 0)
            self.synthesizer._process_note_off_mpe(midi_channel, note, velocity)
        elif msg_type == "note_on":
            note = midi_message.data.get("note", 60)
            velocity = midi_message.data.get("velocity", 64)
            if velocity == 0:
                self.synthesizer._process_note_off_mpe(midi_channel, note, velocity)
            else:
                self.synthesizer._process_note_on_mpe(midi_channel, note, velocity)
        elif msg_type == "poly_pressure":
            note = midi_message.data.get("note", 60)
            pressure = midi_message.data.get("pressure", 0)
            self.synthesizer._process_poly_pressure_mpe(midi_channel, note, pressure)
        elif msg_type == "control_change":
            controller = midi_message.data.get("controller", 0)
            value = midi_message.data.get("value", 0)

            # MPE controller processing (highest priority)
            if self.synthesizer.mpe_enabled and self.synthesizer._process_mpe_controller(
                midi_channel, controller, value
            ):
                return  # MPE controller handled it

            # Arpeggiator NRPN processing (Yamaha Motif style - highest priority)
            if (
                hasattr(self.synthesizer, "arpeggiator_nrpn_controller")
                and self.synthesizer.arpeggiator_nrpn_controller
            ):
                if self.synthesizer.arpeggiator_nrpn_controller.process_nrpn_message(
                    controller, value
                ):
                    return  # Arpeggiator NRPN handled it

            # GS NRPN processing (GS uses NRPN for parameter control)
            if self.synthesizer.gs_enabled and self.synthesizer.gs_nrpn_controller:
                if self.synthesizer.gs_nrpn_controller.process_nrpn_message(controller, value):
                    return  # GS NRPN handled it

            # XG controller processing
            if self.synthesizer.xg_enabled:
                applied = self.synthesizer.xg_components.get_component(
                    "controllers"
                ).apply_controller_value(target_channel.channel_number, controller, value)
                if applied:
                    return  # XG controller handled it

            target_channel.control_change(controller, value)
        elif msg_type == "program_change":
            program = midi_message.data.get("program", 0)
            target_channel.program_change(program)
        elif msg_type == "channel_pressure":
            pressure = midi_message.data.get("pressure", 0)
            target_channel.set_channel_pressure(pressure)
        elif msg_type == "pitch_bend":
            # Check for MPE pitch bend first
            pitch_value = midi_message.data.get("value", midi_message.data.get("pitch", 0))
            if self.synthesizer.mpe_enabled and self.synthesizer._process_pitch_bend_mpe(
                midi_channel, pitch_value
            ):
                return  # MPE handled it

            # Convert pitch bend value to LSB/MSB for regular processing
            lsb = pitch_value & 0x7F
            msb = (pitch_value >> 7) & 0x7F
            target_channel.pitch_bend(lsb, msb)

    def _apply_xg_channel_modifications(self, channel: int, midi_message):
        """
        Apply XG channel modifications to MIDIMessage.

        Args:
            channel: Channel number
            midi_message: Original MIDI message

        Returns:
            Modified MIDI message with XG transformations applied
        """
        if not self.synthesizer.xg_enabled or not hasattr(
            self.synthesizer.channels[channel], "xg_config"
        ):
            return midi_message

        xg_config = self.synthesizer.channels[channel].xg_config

        # Initialize XG metadata
        xg_metadata = {}

        # Start with original message data
        modified_data = midi_message.data.copy()

        # Apply part level (volume scaling)
        if "part_level" in xg_config and xg_config["part_level"] != 100:
            level_scale = xg_config["part_level"] / 100.0
            if midi_message.type == "note_on" and "velocity" in modified_data:
                # Scale velocity by part level
                modified_velocity = max(1, int(modified_data["velocity"] * level_scale))
                modified_data["velocity"] = modified_velocity
                xg_metadata["velocity_scaled"] = True
                xg_metadata["original_velocity"] = modified_data["velocity"]

        # Apply part pan (calculate pan gains for stereo output)
        if "part_pan" in xg_config and xg_config["part_pan"] != 64:
            pan_position = (xg_config["part_pan"] - 64) / 63.0  # Convert to -1.0 to +1.0
            left_gain, right_gain = self._calculate_pan_gains(pan_position)
            xg_metadata["pan_left_gain"] = left_gain
            xg_metadata["pan_right_gain"] = right_gain
            xg_metadata["pan_position"] = pan_position

        # Handle drum kit assignments for percussion channel
        if channel == 9 and "drum_kit" in xg_config:  # Channel 10 (0-indexed as 9)
            kit_number = xg_config["drum_kit"]
            if midi_message.type in ["note_on", "note_off"] and "note" in modified_data:
                # Apply drum kit note remapping
                original_note = modified_data["note"]
                remapped_note = self._remap_drum_note(original_note, kit_number)
                if remapped_note != original_note:
                    xg_metadata["original_note"] = original_note
                    xg_metadata["drum_kit_applied"] = kit_number
                    modified_data["note"] = remapped_note

        # Apply effects sends (store routing information for channel processing)
        if "effects_sends" in xg_config:
            effects_sends = xg_config["effects_sends"]
            xg_metadata["effects_routing"] = {
                "reverb_send": effects_sends.get("reverb", 40) / 127.0,  # Normalize to 0.0-1.0
                "chorus_send": effects_sends.get("chorus", 0) / 127.0,
                "variation_send": effects_sends.get("variation", 0) / 127.0,
            }

        # Apply part mode modifications
        if "part_mode" in xg_config:
            part_mode = xg_config["part_mode"]
            if part_mode == 0:  # Normal mode - polyphonic
                xg_metadata["part_mode"] = "normal"
            elif part_mode == 1:  # Single mode - monophonic
                xg_metadata["part_mode"] = "single"
                xg_metadata["monophonic"] = True
            elif part_mode == 2:  # Layer mode - allow layering
                xg_metadata["part_mode"] = "layer"
                xg_metadata["layered"] = True

        # Apply voice reserve information
        if "voice_reserve" in xg_config:
            voice_reserve = xg_config["voice_reserve"]
            xg_metadata["voice_reserve"] = voice_reserve

        # Create new message with modified data if any changes were made
        if modified_data != midi_message.data:
            modified_message = MIDIMessage(
                type=midi_message.type,
                channel=midi_message.channel,
                data=modified_data,
                timestamp=midi_message.timestamp,
            )
        else:
            modified_message = midi_message

        # Attach metadata to message (using setattr to avoid type checker issues)
        if xg_metadata:
            modified_message._xg_metadata = xg_metadata

        return modified_message

    def _calculate_pan_gains(self, pan_position: float) -> tuple[float, float]:
        """
        Calculate left and right channel gains for pan position using constant power pan law.

        Args:
            pan_position: Pan position from -1.0 (full left) to +1.0 (full right)

        Returns:
            Tuple of (left_gain, right_gain)
        """
        # Constant power pan law: -3dB at center, -6dB at edges
        if pan_position < -1.0:
            pan_position = -1.0
        elif pan_position > 1.0:
            pan_position = 1.0

        # Convert to angle (in radians)
        angle = pan_position * (math.pi / 4.0)  # 45 degrees max

        # Calculate gains using trig functions
        left_gain = math.cos(angle + math.pi / 4.0)
        right_gain = math.sin(angle + math.pi / 4.0)

        return left_gain, right_gain

    def _remap_drum_note(self, note: int, kit_number: int) -> int:
        """
        Remap drum note based on XG drum kit assignments.

        Args:
            note: Original MIDI note number
            kit_number: XG drum kit number

        Returns:
            Remapped note number (may be same if no remapping needed)
        """
        if not self.synthesizer.xg_enabled:
            return note

        # Get drum kit configuration from XG components
        drum_setup = self.synthesizer.xg_components.get_component("drum_setup")
        if drum_setup and hasattr(drum_setup, "get_drum_kit_mapping"):
            # Get note mapping for this kit
            kit_mapping = drum_setup.get_drum_kit_mapping(kit_number)
            if kit_mapping and note in kit_mapping:
                return kit_mapping[note]

        # Return original note if no remapping available
        return note
