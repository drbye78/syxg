"""
MIDI Processing System - Complete MIDI Message Handling

Production-quality MIDI message processing for XG/GS/MPE synthesizer with
complete protocol support and sample-perfect timing.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable, Union
import threading
import time
import math
from pathlib import Path
import os
import hashlib
import weakref


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
        self.lock = threading.RLock()

    def process_midi_message(self, message_bytes: bytes):
        """
        Process MIDI message with XG/GS integration using structured MIDIMessage objects.

        Args:
            message_bytes: Raw MIDI message bytes
        """
        with self.lock:
            # Check for XG receive channel SYSEX first
            if (self.synthesizer.xg_enabled and
                self._is_receive_channel_sysex(message_bytes)):
                self._handle_receive_channel_sysex(message_bytes)
                if hasattr(self.synthesizer, 'performance_monitor'):
                    self.synthesizer.performance_monitor.update(xg_messages_processed=1)
                return

            # GS processing if enabled (GS SYSEX)
            if (self.synthesizer.gs_enabled and
                self.synthesizer.gs_midi_processor.process_message(message_bytes)):
                return  # GS handled it

            # Parse raw bytes to MIDIMessage using synth/midi package
            from ..midi.binary_parser import parse_binary_message
            midi_message = parse_binary_message(message_bytes)

            if midi_message is None:
                return  # Invalid message

            # XG processing first if enabled
            if (self.synthesizer.xg_enabled and
                self.synthesizer.xg_midi_processor.process_message(message_bytes)):
                if hasattr(self.synthesizer, 'performance_monitor'):
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
        # XG Receive Channel SYSEX format: F0 43 [device] 4C 08 [part] [channel] F7
        if len(data) != 9 or data[0] != 0xF0 or data[-1] != 0xF7:
            return False

        # Check Yamaha manufacturer ID and XG model ID
        if data[1] != 0x43 or data[3] != 0x4C:
            return False

        # Check device ID matches our device
        if data[2] != self.synthesizer.device_id:
            return False

        # Check command is 0x08 (receive channel assignment)
        return data[4] == 0x08

    def _handle_receive_channel_sysex(self, data: bytes):
        """
        Handle XG receive channel SYSEX message.

        Args:
            data: Raw SYSEX data
        """
        if not self.synthesizer.xg_enabled or not hasattr(self.synthesizer, 'receive_channel_manager'):
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
            print(f"XG SYSEX: Part {part_id} receive channel set to "
                  f"{'MIDI CH ' + str(midi_channel) if midi_channel < 16 else 'ALL' if midi_channel == 255 else 'OFF'}")

    def _process_standard_midi(self, midi_message):
        """
        Process standard MIDI messages using structured MIDIMessage objects with XG/GS receive channel mapping.

        Args:
            midi_message: Parsed MIDIMessage object
        """
        # Handle SYSEX and other system messages that don't have channels
        if midi_message.type == 'sysex':
            # Reconstruct SYSEX bytes from parsed message
            sysex_data = [midi_message.status] + midi_message.sysex_data

            # Process Arpeggiator SYSEX messages first (Yamaha Motif)
            if hasattr(self.synthesizer, 'arpeggiator_sysex_controller'):
                result = self.synthesizer.arpeggiator_sysex_controller.process_sysex_message(bytes(sysex_data))
                if result:
                    return  # Arpeggiator SYSEX handled it

            # Process GS SYSEX messages
            if self.synthesizer.gs_enabled and self.synthesizer.gs_midi_processor.process_message(bytes(sysex_data)):
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
        if hasattr(self.synthesizer, 'arpeggiator_engine') and midi_message.type in ['note_on', 'note_off']:
            arpeggiator = self.synthesizer.arpeggiator_engine.get_arpeggiator(midi_channel)
            if arpeggiator and arpeggiator.enabled and arpeggiator.current_pattern:
                # Arpeggiator is active - let it handle the note
                if midi_message.type == 'note_on':
                    self.synthesizer.arpeggiator_engine.process_note_on(midi_channel, midi_message.note, midi_message.velocity)
                else:  # note_off
                    self.synthesizer.arpeggiator_engine.process_note_off(midi_channel, midi_message.note)
                # Arpeggiator will generate its own note events via callbacks
                return
            # Arpeggiator is inactive - continue with normal processing

        # XG receive channel mapping - route message to appropriate parts
        if self.synthesizer.xg_enabled and hasattr(self.synthesizer, 'receive_channel_manager'):
            target_parts = self.synthesizer.receive_channel_manager.get_parts_for_midi_channel(midi_channel)

            if target_parts:
                # Route message to all target parts
                for part_id in target_parts:
                    if not (0 <= part_id < len(self.synthesizer.channels)):
                        continue  # Invalid part ID

                    target_channel = self.synthesizer.channels[part_id]

                    # Apply XG modifications if enabled
                    modified_message = self._apply_xg_channel_modifications(part_id, midi_message)

                    # Update channel XG state from message metadata
                    if hasattr(modified_message, '_xg_metadata'):
                        target_channel.update_xg_state_from_message(modified_message._xg_metadata)

                    # Process message based on type
                    self._process_message_on_channel(target_channel, modified_message)
            else:
                # No specific mapping, use default 1:1
                if midi_channel < len(self.synthesizer.channels):
                    target_channel = self.synthesizer.channels[midi_channel]
                    modified_message = self._apply_xg_channel_modifications(midi_channel, midi_message)
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

        if msg_type == 'note_off':
            self.synthesizer._process_note_off_mpe(midi_channel, midi_message.note, midi_message.velocity)
        elif msg_type == 'note_on':
            if midi_message.velocity == 0:
                self.synthesizer._process_note_off_mpe(midi_channel, midi_message.note, midi_message.velocity)
            else:
                self.synthesizer._process_note_on_mpe(midi_channel, midi_message.note, midi_message.velocity)
        elif msg_type == 'poly_pressure':
            self.synthesizer._process_poly_pressure_mpe(midi_channel, midi_message.note, midi_message.pressure)
        elif msg_type == 'control_change':
            controller, value = midi_message.control, midi_message.value

            # MPE controller processing (highest priority)
            if self.synthesizer.mpe_enabled and self.synthesizer._process_mpe_controller(midi_channel, controller, value):
                return  # MPE controller handled it

            # Arpeggiator NRPN processing (Yamaha Motif style - highest priority)
            if hasattr(self.synthesizer, 'arpeggiator_nrpn_controller') and self.synthesizer.arpeggiator_nrpn_controller:
                if self.synthesizer.arpeggiator_nrpn_controller.process_nrpn_message(controller, value):
                    return  # Arpeggiator NRPN handled it

            # GS NRPN processing (GS uses NRPN for parameter control)
            if self.synthesizer.gs_enabled and self.synthesizer.gs_nrpn_controller:
                if self.synthesizer.gs_nrpn_controller.process_nrpn_message(controller, value):
                    return  # GS NRPN handled it

            # XG controller processing
            if self.synthesizer.xg_enabled:
                applied = self.synthesizer.xg_components.get_component('controllers').apply_controller_value(
                    target_channel.channel_number, controller, value
                )
                if applied:
                    return  # XG controller handled it

            target_channel.control_change(controller, value)
        elif msg_type == 'program_change':
            target_channel.program_change(midi_message.program)
        elif msg_type == 'channel_pressure':
            target_channel.set_channel_pressure(midi_message.pressure)
        elif msg_type == 'pitch_bend':
            # Check for MPE pitch bend first
            if self.synthesizer.mpe_enabled and self.synthesizer._process_pitch_bend_mpe(midi_channel, midi_message.pitch):
                return  # MPE handled it

            # Convert pitch bend value to LSB/MSB for regular processing
            pitch_value = midi_message.pitch
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
        if not self.synthesizer.xg_enabled or not hasattr(self.synthesizer.channels[channel], 'xg_config'):
            return midi_message

        xg_config = self.synthesizer.channels[channel].xg_config

        # Create a copy of the message for modification
        from ..midi.parser import MIDIMessage
        modified_message = MIDIMessage(**{k: getattr(midi_message, k) for k in midi_message.__slots__ if getattr(midi_message, k) is not None})

        # Initialize XG metadata as a separate attribute
        xg_metadata = {}

        # Apply part level (volume scaling)
        if 'part_level' in xg_config and xg_config['part_level'] != 100:
            level_scale = xg_config['part_level'] / 100.0
            if modified_message.type == 'note_on':
                # Scale velocity by part level
                modified_velocity = max(1, int(modified_message.velocity * level_scale))
                modified_message.velocity = modified_velocity
                xg_metadata['velocity_scaled'] = True
                xg_metadata['original_velocity'] = midi_message.velocity

        # Apply part pan (calculate pan gains for stereo output)
        if 'part_pan' in xg_config and xg_config['part_pan'] != 64:
            pan_position = (xg_config['part_pan'] - 64) / 63.0  # Convert to -1.0 to +1.0
            left_gain, right_gain = self._calculate_pan_gains(pan_position)
            xg_metadata['pan_left_gain'] = left_gain
            xg_metadata['pan_right_gain'] = right_gain
            xg_metadata['pan_position'] = pan_position

        # Handle drum kit assignments for percussion channel
        if channel == 9 and 'drum_kit' in xg_config:  # Channel 10 (0-indexed as 9)
            kit_number = xg_config['drum_kit']
            if modified_message.type in ['note_on', 'note_off']:
                # Apply drum kit note remapping
                remapped_note = self._remap_drum_note(modified_message.note, kit_number)
                if remapped_note != modified_message.note:
                    xg_metadata['original_note'] = modified_message.note
                    xg_metadata['drum_kit_applied'] = kit_number
                    modified_message.note = remapped_note

        # Apply effects sends (store routing information for channel processing)
        if 'effects_sends' in xg_config:
            effects_sends = xg_config['effects_sends']
            xg_metadata['effects_routing'] = {
                'reverb_send': effects_sends.get('reverb', 40) / 127.0,  # Normalize to 0.0-1.0
                'chorus_send': effects_sends.get('chorus', 0) / 127.0,
                'variation_send': effects_sends.get('variation', 0) / 127.0
            }

        # Apply part mode modifications
        if 'part_mode' in xg_config:
            part_mode = xg_config['part_mode']
            if part_mode == 0:  # Normal mode - polyphonic
                xg_metadata['part_mode'] = 'normal'
            elif part_mode == 1:  # Single mode - monophonic
                xg_metadata['part_mode'] = 'single'
                xg_metadata['monophonic'] = True
            elif part_mode == 2:  # Layer mode - allow layering
                xg_metadata['part_mode'] = 'layer'
                xg_metadata['layered'] = True

        # Apply voice reserve information
        if 'voice_reserve' in xg_config:
            voice_reserve = xg_config['voice_reserve']
            xg_metadata['voice_reserve'] = voice_reserve

        # Attach metadata to message (using setattr to avoid type checker issues)
        if xg_metadata:
            setattr(modified_message, '_xg_metadata', xg_metadata)

        return modified_message

    def _calculate_pan_gains(self, pan_position: float) -> Tuple[float, float]:
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
        drum_setup = self.synthesizer.xg_components.get_component('drum_setup')
        if drum_setup and hasattr(drum_setup, 'get_drum_kit_mapping'):
            # Get note mapping for this kit
            kit_mapping = drum_setup.get_drum_kit_mapping(kit_number)
            if kit_mapping and note in kit_mapping:
                return kit_mapping[note]

        # Return original note if no remapping available
        return note
