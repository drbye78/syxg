"""
XG Synthesizer Core

Main synthesizer class that orchestrates all modules.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
from collections import OrderedDict
import threading
import heapq
import time
import os

# Import internal modules
from .constants import MIDI_CONSTANTS, XG_CONSTANTS, DEFAULT_CONFIG, VOICE_ALLOCATION_MODES
from ..sf2.manager import SF2Manager
from ..xg.manager import StateManager
from ..xg.drum_manager import DrumManager
from ..midi.message_handler import MIDIMessageHandler
from ..midi.buffered_processor import BufferedProcessor
from ..audio.vectorized_engine import VectorizedAudioEngine
from ..xg.channel_renderer import XGChannelRenderer
from ..effects.core import XGEffectManager


class XGSynthesizer:
    """
    Fully MIDI XG compatible software synthesizer.

    Supports:
    - All MIDI messages including SYSEX and Bulk SYSEX
    - Audio generation in blocks of arbitrary size
    - Maximum polyphony configuration
    - Full tone generation control
    - Effect processing
    - SF2 file management with blacklists and bank mapping
    - Initialization according to MIDI XG standard
    - Full XG drum parameter support
    - Both immediate and buffered operation modes

    Operating modes:
    1. Immediate mode: Messages are processed immediately upon receipt
    2. Buffered mode: Messages are processed with sample-accurate timing synchronization

    Buffered mode features:
    - True frame-by-frame (sample-accurate) MIDI message processing
    - Ability to process messages in the middle of audio blocks with single-sample accuracy
    - Storage of message timestamps for precise synchronization
    """

    def __init__(self, sample_rate: int = DEFAULT_CONFIG["SAMPLE_RATE"],
                 block_size: int = DEFAULT_CONFIG["BLOCK_SIZE"],
                 max_polyphony: int = DEFAULT_CONFIG["MAX_POLYPHONY"],
                 param_cache=None):
        """
        Initialize XG synthesizer.

        Args:
            sample_rate: Sampling rate (default 44100 Hz)
            block_size: Audio block size in samples (default 512)
            max_polyphony: Maximum polyphony (default 64 voices)
            param_cache: Optional parameter cache for performance optimization
        """
        # Basic parameters
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_polyphony = max_polyphony
        self.master_volume = DEFAULT_CONFIG["MASTER_VOLUME"]

        # Thread safety lock
        self.lock = threading.RLock()

        # State management
        self.state_manager = StateManager()

        # Drum management
        self.drum_manager = DrumManager()

        # SF2 file management
        self.sf2_manager = SF2Manager(param_cache=param_cache, drum_manager=self.drum_manager)

        # Buffered message processing
        self.buffered_processor = BufferedProcessor(sample_rate)

        # Audio engine
        self.audio_engine = VectorizedAudioEngine(sample_rate, block_size, DEFAULT_CONFIG["NUM_MIDI_CHANNELS"])

        # Per-channel renderers (one per MIDI channel)
        self.channel_renderers: List[XGChannelRenderer] = []
        for channel in range(DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]):
            renderer = XGChannelRenderer(channel=channel, sample_rate=sample_rate)
            self.channel_renderers.append(renderer)

        # Counters for unique identification
        self.generator_id_counter = 0

        # Effects
        self.effect_manager = XGEffectManager(sample_rate)

        # MIDI message handling
        self.message_handler = MIDIMessageHandler(self.state_manager, self.drum_manager, self.effect_manager, self)

        # Set wavetable manager for all channel renderers
        for renderer in self.channel_renderers:
            renderer.wavetable = self.sf2_manager.get_manager()

        # Initialize XG
        self._initialize_xg()

        # Set up drum channel enhancements
        self._setup_drum_channel_enhancements()

    # Removed _create_channel_state - now handled by StateManager

    def _initialize_xg(self):
        """Initialize XG synthesizer according to standard"""
        # Initialize state manager with XG defaults
        self.state_manager.initialize_xg_defaults()

        # Initialize effect parameters for all channels
        for channel in range(DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]):
            # Initialize effect parameters in effect manager
            self.effect_manager.set_current_nrpn_channel(channel)
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, DEFAULT_CONFIG["DEFAULT_REVERB_SEND"])  # Reverb send
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, DEFAULT_CONFIG["DEFAULT_CHORUS_SEND"])   # Chorus send

        # Reset effects to standard XG state
        self.effect_manager.reset_effects()

        # Additional initialization to match XG standard
        # Set standard parameters for all channels
        for channel in range(DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]):
            # Program Change to piano (program 0) for all channels
            self._handle_program_change(channel, 0)
            # For channel 9, set drum mode by default for XG compatibility
            if channel == 9:
                # Set drum mode - the new XGChannelRenderer handles this internally
                self.channel_renderers[channel].is_drum = True
                # Set drum bank
                self.state_manager.set_bank(channel, 128)

    def _handle_program_change(self, channel: int, program: int):
        """Handle Program Change message"""
        self.state_manager.set_program(channel, program)

        # For drum channels (channels in drum mode), set drum bank
        if self.channel_renderers[channel].is_drum:
            self.state_manager.set_bank(channel, 128)

        # Forward to channel renderer
        self.channel_renderers[channel].program_change(program)

    def _setup_drum_channel_enhancements(self):
        """Set up drum channel enhancements according to XG specification"""
        pass

    # Public API methods
    def set_sf2_files(self, sf2_paths: List[str]):
        """
        Set list of SF2 files to use with synthesizer.

        Args:
            sf2_paths: List of paths to SF2 files
        """
        with self.lock:
            success = self.sf2_manager.set_sf2_files(sf2_paths)

            # Update wavetable manager for all channel renderers
            for renderer in self.channel_renderers:
                renderer.wavetable = self.sf2_manager.get_manager()

            return success

    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Set bank blacklist for specified SF2 file.

        Args:
            sf2_path: Path to SF2 file
            bank_list: List of bank numbers to exclude
        """
        with self.lock:
            self.sf2_manager.set_bank_blacklist(sf2_path, bank_list)

    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Set preset blacklist for specified SF2 file.

        Args:
            sf2_path: Path to SF2 file
            preset_list: List of (bank, program) tuples to exclude
        """
        with self.lock:
            self.sf2_manager.set_preset_blacklist(sf2_path, preset_list)

    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Set MIDI bank to SF2 bank mapping for specified file.

        Args:
            sf2_path: Path to SF2 file
            bank_mapping: Dictionary mapping midi_bank -> sf2_bank
        """
        with self.lock:
            self.sf2_manager.set_bank_mapping(sf2_path, bank_mapping)

    def set_max_polyphony(self, max_polyphony: int):
        """
        Set maximum polyphony.

        Args:
            max_polyphony: Maximum number of simultaneous voices
        """
        with self.lock:
            self.max_polyphony = max_polyphony

    def set_master_volume(self, volume: float):
        """
        Set master volume.

        Args:
            volume: Volume (0.0 - 1.0)
        """
        with self.lock:
            self.master_volume = max(0.0, min(1.0, volume))
            self.audio_engine.set_master_volume(volume)

    def get_available_programs(self) -> List[Tuple[int, int, str]]:
        """
        Get list of available programs (presets).

        Returns:
            List of tuples (bank, program, name)
        """
        with self.lock:
            return self.sf2_manager.get_available_presets()

    def generate_audio_block(self, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block from all active channel renderers.

        Args:
            block_size: Block size in samples (optional)

        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        with self.lock:
            return self.audio_engine.generate_audio_block(
                self.channel_renderers, self.effect_manager, block_size
            )

    def reset(self):
        """Full synthesizer reset"""
        with self.lock:
            # Stop all active notes
            for renderer in self.channel_renderers:
                try:
                    renderer.all_sound_off()
                except:
                    pass

            # Reset state manager
            self.state_manager.reset_all_channels()

            # Reset drum manager
            self.drum_manager.reset_all_drum_parameters()

            # Reset effects
            self.effect_manager.reset_effects()

            # Reset buffered processor
            self.buffered_processor.reset()

            # Reset audio engine
            self.audio_engine.reset()

            # Reinitialize XG
            self._initialize_xg()

    def generate_audio_block_sample_accurate(self, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block with frame-by-frame (sample-accurate) MIDI message processing.
        Each audio sample is processed separately with checking for MIDI messages at that moment.

        Args:
            block_size: Block size in samples (if None, uses default value)

        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        if block_size is None:
            block_size = self.block_size

        with self.lock:
            # Set block start time in buffered processor
            self.buffered_processor.set_block_start_time(self.buffered_processor.current_time)

            # Prepare sample times for this block
            self.buffered_processor.prepare_sample_times(block_size)

            # Create buffers for each sample in block
            left_buffer = np.zeros(block_size, dtype=np.float32)
            right_buffer = np.zeros(block_size, dtype=np.float32)

            # Process each sample separately
            for i in range(block_size):
                # Get time for current sample
                sample_time = self.buffered_processor.sample_times[i]

                # Process all MIDI messages whose time has arrived for this sample
                midi_messages, sysex_messages = self.buffered_processor.process_message_at_time(sample_time)

                # Send processed messages to synthesizer
                for status, data1, data2 in midi_messages:
                    self.send_midi_message(status, data1, data2)

                for sysex_data in sysex_messages:
                    self.send_sysex(sysex_data)

                # Generate audio for this sample
                left_sample, right_sample = self._generate_single_sample()

                # Save sample to buffer
                left_buffer[i] = left_sample
                right_buffer[i] = right_sample

            # Update current time in buffered processor
            self.buffered_processor.current_time = self.buffered_processor.block_start_time + (block_size / self.sample_rate)

            # Apply effects to entire block
            try:
                # Prepare multichannel input data for effects
                # Create 16 channels, each with block_size samples
                input_channels = []
                for channel in range(16):
                    channel_samples = []
                    for i in range(block_size):
                        channel_samples.append((left_buffer[i], right_buffer[i]))
                    input_channels.append(channel_samples)

                # Process effects for all 16 channels
                effected_channels = self.effect_manager.process_audio(
                    input_channels,
                    block_size
                )

                # Mix all channels into single stereo output
                left_result = np.zeros(block_size, dtype=np.float32)
                right_result = np.zeros(block_size, dtype=np.float32)

                for channel in range(16):
                    for i in range(block_size):
                        left_result[i] += effected_channels[channel][i][0]
                        right_result[i] += effected_channels[channel][i][1]

                # Limit final mix
                for i in range(block_size):
                    left_result[i] = max(-1.0, min(1.0, left_result[i]))
                    right_result[i] = max(-1.0, min(1.0, right_result[i]))

                return left_result, right_result

            except Exception as e:
                print(f"Error processing effects: {e}")
                # If effects don't work, return unprocessed mix
                return left_buffer, right_buffer

    def generate_audio_block_vectorized(self, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        VECTORIZED BLOCK PROCESSING OPTIMIZATION - PHASE 4 PERFORMANCE
        Generate audio block using vectorized processing for improved performance.

        This method replaces per-sample processing with block-based vector operations
        to eliminate the identified per-sample processing bottleneck.

        Args:
            block_size: Block size in samples (if None, uses default value)

        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        if block_size is None:
            block_size = self.block_size

        with self.lock:
            try:
                # VECTORIZED PROCESSING: Generate block data for all active channels simultaneously
                # Initialize block buffers for all channels
                block_left = np.zeros(block_size, dtype=np.float32)
                block_right = np.zeros(block_size, dtype=np.float32)

                # Cache volume factors for performance
                master_volume_factor = np.float32(self.master_volume)

                # Process all active channel renderers with optimized loop processing
                active_renderers = []
                for renderer in self.channel_renderers:
                    if renderer.is_active():
                        active_renderers.append(renderer)

                # Batch process all active voices with optimized accumulation
                if active_renderers:
                    # Initialize block-level audio accumulation
                    block_left.fill(0.0)
                    block_right.fill(0.0)

                    # OPTIMIZED BLOCK PROCESSING: Use vectorized accumulation where possible
                    for renderer in active_renderers:
                        try:
                            # Try vectorized block generation first (if available)
                            renderer_left, renderer_right = renderer.generate_sample_block(block_size)
                            block_left = np.add(block_left, renderer_left, out=block_left)
                            block_right = np.add(block_right, renderer_right, out=block_right)

                        except (AttributeError, TypeError):
                            # Fallback: Vectorize per-sample generation where possible
                            try:
                                # Pre-allocate sample arrays for vectorized processing
                                temp_left = np.zeros(block_size, dtype=np.float32)
                                temp_right = np.zeros(block_size, dtype=np.float32)

                                # Generate samples in a loop (still inefficient but better than single accumulation)
                                for idx in range(block_size):
                                    l, r = renderer.generate_sample()
                                    temp_left[idx] = l
                                    temp_right[idx] = r

                                # Vectorized addition to accumulator
                                block_left = np.add(block_left, temp_left, out=block_left)
                                block_right = np.add(block_right, temp_right, out=block_right)

                            except Exception as e:
                                print(f"Error generating samples from renderer: {e}")
                                continue

                    # Apply master volume with vectorized multiplication
                    block_left *= master_volume_factor
                    block_right *= master_volume_factor

                    # Vectorized final clipping
                    np.clip(block_left, -1.0, 1.0, out=block_left)
                    np.clip(block_right, -1.0, 1.0, out=block_right)

                # Apply effects to entire vectors (highly optimized)
                if hasattr(self.effect_manager, 'process_multi_channel_vectorized'):
                    try:
                        # Prepare vectorized input for effects processing
                        effect_input = np.column_stack((block_left, block_right))

                        # Process effects with vectorized operations
                        effect_output = self.effect_manager.process_multi_channel_vectorized(
                            effect_input, self.effect_manager
                        )

                        # Separate stereo channels
                        block_left = effect_output[:, 0]
                        block_right = effect_output[:, 1]

                        # Vectorized final clipping
                        block_left = np.clip(block_left, -1.0, 1.0)
                        block_right = np.clip(block_right, -1.0, 1.0)

                    except Exception as e:
                        print(f"Error in vectorized effects: {e}")
                        # Fallback to unprocessed audio
                        pass

                return block_left, block_right

            except Exception as e:
                print(f"Error in vectorized block generation: {e}")
                # Fallback to original method if vectorization fails
                return self.generate_audio_block(block_size)

    def _generate_single_sample(self) -> Tuple[float, float]:
        """
        Generate one audio sample from all active channel renderers.

        Returns:
            Tuple (left_sample, right_sample) with audio data
        """
        # Generate audio from each active channel renderer
        left_sum = 0.0
        right_sum = 0.0

        for renderer in self.channel_renderers:
            if renderer.is_active():
                try:
                    l, r = renderer.generate_sample()
                    left_sum += l
                    right_sum += r
                except Exception as e:
                    print(f"Error generating sample: {e}")
                    # Disable problematic renderer
                    renderer.active = False

        # Apply master volume
        left_sum *= self.master_volume
        right_sum *= self.master_volume

        # Limit values
        left_sum = max(-1.0, min(1.0, left_sum))
        right_sum = max(-1.0, min(1.0, right_sum))

        return left_sum, right_sum

    def send_midi_message(self, status: int, data1: int, data2: int = 0):
        """
        Send MIDI message to synthesizer.

        Args:
            status: Status byte (including channel number)
            data1: First data byte
            data2: Second data byte (for messages with two data bytes)
        """
        with self.lock:
            # Determine channel number
            channel = status & 0x0F
            command = status & 0xF0

            # Process commands
            if command == 0x80:  # Note Off
                self._handle_note_off(channel, data1, data2)
            elif command == 0x90:  # Note On
                self._handle_note_on(channel, data1, data2)
            elif command == 0xA0:  # Poly Pressure
                self._handle_poly_pressure(channel, data1, data2)
            elif command == 0xB0:  # Control Change
                self._handle_control_change(channel, data1, data2)
            elif command == 0xC0:  # Program Change
                self._handle_program_change(channel, data1)
            elif command == 0xD0:  # Channel Pressure
                self._handle_channel_pressure(channel, data1)
            elif command == 0xE0:  # Pitch Bend
                self._handle_pitch_bend(channel, data1, data2)

    def send_sysex(self, data: List[int]):
        """
        Send system exclusive message.

        Args:
            data: SYSEX message data (including F0 and F7)
        """
        with self.lock:
            # Check if this is really a SYSEX message
            if len(data) < 3 or data[0] != 0xF0 or data[-1] != 0xF7:
                return

            # Determine manufacturer
            if len(data) >= 2 and data[1] == 0x43:  # Yamaha
                self._handle_yamaha_sysex(data)
            else:
                # Process other manufacturers
                pass

    def _handle_note_off(self, channel: int, note: int, velocity: int):
        """Handle Note Off message"""
        # Forward to channel renderer
        self.channel_renderers[channel].note_off(note, velocity)

    def _handle_note_on(self, channel: int, note: int, velocity: int):
        """Handle Note On message"""
        # If velocity = 0, this is Note Off
        if velocity == 0:
            self._handle_note_off(channel, note, velocity)
            return

        # Forward to channel renderer
        self.channel_renderers[channel].note_on(note, velocity)

    def _handle_poly_pressure(self, channel: int, note: int, pressure: int):
        """Handle Poly Pressure (Key Aftertouch) message"""
        # Store in channel state
        self.state_manager.set_key_pressure(channel, note, pressure)

    def _handle_control_change(self, channel: int, controller: int, value: int):
        """Handle Control Change message"""
        # Update controller state
        self.state_manager.update_controller(channel, controller, value)

        # Handle specific controllers
        if controller == 7:  # Volume
            pass  # Handled by state manager
        elif controller == 10:  # Pan
            pass  # Handled by state manager
        elif controller == 11:  # Expression
            pass  # Handled by state manager
        elif controller == 64:  # Sustain Pedal
            pass  # Handled by state manager
        elif controller == 65:  # Portamento Switch
            pass  # Handled by state manager
        elif controller == 91:  # Reverb Send
            # Pass value to effect manager
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, value)
        elif controller == 93:  # Chorus Send
            # Pass value to effect manager
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, value)
        elif controller == 120:  # All Sound Off
            self._handle_all_sound_off(channel)
        elif controller == 121:  # Reset All Controllers
            self._handle_reset_all_controllers(channel)
        elif controller == 123:  # All Notes Off
            self._handle_all_notes_off(channel)

        # Handle RPN/NRPN
        if controller == 101:  # RPN MSB
            self.state_manager.set_rpn_msb(channel, value)
        elif controller == 100:  # RPN LSB
            self.state_manager.set_rpn_lsb(channel, value)
        elif controller == 99:  # NRPN MSB
            self.state_manager.set_nrpn_msb(channel, value)
        elif controller == 98:  # NRPN LSB
            self.state_manager.set_nrpn_lsb(channel, value)
        elif controller == 6:  # Data Entry MSB
            self.state_manager.set_data_entry_msb(channel, value)
            self._handle_data_entry(channel)
        elif controller == 38:  # Data Entry LSB
            self.state_manager.set_data_entry_lsb(channel, value)
            self._handle_data_entry(channel)

        # Forward to channel renderer
        self.channel_renderers[channel].control_change(controller, value)

    def _handle_channel_pressure(self, channel: int, pressure: int):
        """Handle Channel Pressure (Aftertouch) message"""
        self.state_manager.set_channel_pressure(channel, pressure)

        # Forward to channel renderer
        self.channel_renderers[channel].channel_pressure_value = pressure

    def _handle_pitch_bend(self, channel: int, lsb: int, msb: int):
        """Handle Pitch Bend message"""
        # 14-bit pitch bend value
        value = (msb << 7) | lsb
        self.state_manager.set_pitch_bend(channel, value)

        # Forward to channel renderer
        self.channel_renderers[channel].pitch_bend(lsb, msb)

    def _handle_data_entry(self, channel: int):
        """Handle Data Entry for RPN/NRPN"""
        # Get current states
        rpn_msb = self.state_manager.get_current_rpn(channel)[0]
        rpn_lsb = self.state_manager.get_current_rpn(channel)[1]
        nrpn_msb = self.state_manager.get_current_nrpn(channel)[0]
        nrpn_lsb = self.state_manager.get_current_nrpn(channel)[1]
        data_msb = self.state_manager.get_current_data_entry(channel)[0]
        data_lsb = self.state_manager.get_current_data_entry(channel)[1]

        # Check if RPN or NRPN is set
        if rpn_msb != 127 and rpn_lsb != 127:
            # Process RPN
            self._handle_rpn(channel, rpn_msb, rpn_lsb, data_msb, data_lsb)
        elif nrpn_msb != 127 and nrpn_lsb != 127:
            # Process NRPN
            self._handle_nrpn(channel, nrpn_msb, nrpn_lsb, data_msb, data_lsb)

    def _handle_rpn(self, channel: int, rpn_msb: int, rpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle Registered Parameter Number"""
        # Forward to channel renderer
        # Note: RPN handling is done in the channel renderer
        pass

    def _handle_nrpn(self, channel: int, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle Non-Registered Parameter Number"""
        # Check if this is an effect parameter NRPN
        # Forward to effect manager for effect parameter processing
        self.effect_manager.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb, channel)

        # Check if this is a drum parameter
        if channel == 15:  # Drum setup channel
            self._handle_drum_setup_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb)

    def _handle_drum_setup_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle NRPN drum parameters through setup channel (16)"""
        # 14-bit data value
        data = (data_msb << 7) | data_lsb

        # Get drum note from current setup channel state
        drum_note = 36  # Default drum note

        # Process various drum parameters
        if nrpn_lsb == 251:  # Drum Note Tune
            # Drum pitch tuning (-64..+63 semitones)
            tune = (data - 8192) / 100.0  # Convert to semitones
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.state_manager.get_channel_state(ch).get("bank") == 128:
                    self.drum_manager.set_drum_parameter(ch, drum_note, "tune", tune)

    def _handle_yamaha_sysex(self, data: List[int]):
        """Handle Yamaha SYSEX messages"""
        if len(data) < 6:
            return

        # Extract SysEx message parameters
        device_id = data[1] if len(data) > 1 else 0
        sub_status = data[2] if len(data) > 2 else 0
        command = data[3] if len(data) > 3 else 0

        # Forward message to effect manager
        self.effect_manager.handle_sysex([0x43], data[1:])  # 0x43 - Yamaha manufacturer ID

    def _handle_all_sound_off(self, channel: int):
        """Handle All Sound Off controller"""
        # Stop all active notes on channel
        self.channel_renderers[channel].all_sound_off()

    def _handle_reset_all_controllers(self, channel: int):
        """Handle Reset All Controllers controller"""
        # Reset channel state
        self.state_manager.reset_channel(channel)

        # Reset effect parameters in effect manager
        self.effect_manager.set_current_nrpn_channel(channel)
        self.effect_manager.set_channel_effect_parameter(channel, 0, 160, 40)  # Reverb send
        self.effect_manager.set_channel_effect_parameter(channel, 0, 161, 0)   # Chorus send

        # Reset drum parameters
        self.drum_manager.reset_channel_drum_parameters(channel)

    def _handle_all_notes_off(self, channel: int):
        """Handle All Notes Off controller"""
        # Stop all active notes on channel
        self.channel_renderers[channel].all_notes_off()

    # Buffered message processing methods - delegate to BufferedProcessor
    def send_midi_message_block(self, messages: List[Tuple[float, int, int, int]],
                               sysex_messages: Optional[List[Tuple[float, List[int]]]] = None):
        """
        Send block of timestamped MIDI messages to synthesizer.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.

        Args:
            messages: List of tuples (time_in_seconds, status, data1, data2)
            sysex_messages: List of tuples (time_in_seconds, SYSEX_data) (optional)
        """
        with self.lock:
            self.buffered_processor.send_midi_message_block(messages, sysex_messages)

    def set_buffered_mode_time(self, time: float):
        """
        Set current time for buffered mode.
        All messages with time <= current time will be processed.

        Args:
            time: Current time in seconds
        """
        with self.lock:
            self.buffered_processor.set_buffered_mode_time(time)

    def get_buffered_mode_time(self) -> float:
        """
        Get current time for buffered mode.

        Returns:
            Current time in seconds
        """
        with self.lock:
            return self.buffered_processor.get_buffered_mode_time()

    def clear_message_buffers(self):
        """
        Clear message buffers.
        """
        with self.lock:
            self.buffered_processor.clear_message_buffers()

    def send_midi_message_at_time(self, status: int, data1: int, data2: int, time: float):
        """
        Send MIDI message to synthesizer with specified time.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.

        Args:
            status: Status byte (including channel number)
            data1: First data byte
            data2: Second data byte (for messages with two data bytes)
            time: Time in seconds to process message
        """
        with self.lock:
            self.buffered_processor.send_midi_message_at_time(status, data1, data2, time)

    def send_sysex_at_time(self, data: List[int], time: float):
        """
        Send system exclusive message with specified time.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.

        Args:
            data: SYSEX message data (including F0 and F7)
            time: Time in seconds to process message
        """
        with self.lock:
            self.buffered_processor.send_sysex_at_time(data, time)

    def process_buffered_messages(self, current_time: float):
        """
        Process buffered MIDI messages up to specified time.
        Uses heap for efficient message processing in time order.

        Args:
            current_time: Current time in seconds
        """
        with self.lock:
            processed_messages = self.buffered_processor.process_buffered_messages(current_time)
            # Send processed messages to synthesizer
            for status, data1, data2 in processed_messages:
                self.send_midi_message(status, data1, data2)

    def process_buffered_sysex(self, current_time: float):
        """
        Process buffered SYSEX messages up to specified time.
        Uses heap for efficient message processing in time order.

        Args:
            current_time: Current time in seconds
        """
        with self.lock:
            processed_sysex = self.buffered_processor.process_buffered_sysex(current_time)
            # Send processed SYSEX messages to synthesizer
            for sysex_data in processed_sysex:
                self.send_sysex(sysex_data)
