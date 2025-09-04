import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
from collections import OrderedDict
import threading
import heapq
import time
import os

# Import classes from other modules
from sf2 import Sf2WavetableManager
from tg import XGChannelRenderer  # Use the refactored channel renderer
from fx import XGEffectManager

# Import required classes from the original tg.py for drum instrument name lookup
from tg import DrumNoteMap


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
    
    # Default constants
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_BLOCK_SIZE = 512
    DEFAULT_MAX_POLYPHONY = 64
    DEFAULT_MASTER_VOLUME = 1.0
    
    # MIDI system statuses
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0
    SYSTEM_EXCLUSIVE = 0xF0
    MIDI_TIME_CODE = 0xF1
    SONG_POSITION = 0xF2
    SONG_SELECT = 0xF3
    TUNE_REQUEST = 0xF6
    END_OF_EXCLUSIVE = 0xF7
    TIMING_CLOCK = 0xF8
    START = 0xFA
    CONTINUE = 0xFB
    STOP = 0xFC
    ACTIVE_SENSING = 0xFE
    SYSTEM_RESET = 0xFF
    
    # Registration system messages
    RPN_MSB = 101
    RPN_LSB = 100
    NRPN_MSB = 99
    NRPN_LSB = 98
    DATA_ENTRY_MSB = 6
    DATA_ENTRY_LSB = 38
    
    # XG Drum Setup Parameters (NRPN)
    # Channel 16 (drum channel) is used for drum setup parameters
    DRUM_NOTE_NUMBER = 250
    DRUM_NOTE_TUNE = 251
    DRUM_NOTE_LEVEL = 252
    DRUM_NOTE_PAN = 253
    DRUM_NOTE_REVERB = 254
    DRUM_NOTE_CHORUS = 255
    DRUM_NOTE_VARIATION = 256
    DRUM_NOTE_KEY_ASSIGN = 257
    DRUM_NOTE_FILTER_CUTOFF = 258
    DRUM_NOTE_FILTER_RESONANCE = 259
    DRUM_NOTE_EG_ATTACK = 260
    DRUM_NOTE_EG_DECAY = 261
    DRUM_NOTE_EG_RELEASE = 262
    DRUM_NOTE_PITCH_COARSE = 263
    DRUM_NOTE_PITCH_FINE = 264
    DRUM_NOTE_LEVEL_HOLD = 265
    DRUM_NOTE_VARIATION_EFFECT = 266
    DRUM_NOTE_VARIATION_PARAMETER1 = 267
    DRUM_NOTE_VARIATION_PARAMETER2 = 268
    DRUM_NOTE_VARIATION_PARAMETER3 = 269
    DRUM_NOTE_VARIATION_PARAMETER4 = 270
    DRUM_NOTE_VARIATION_PARAMETER5 = 271
    DRUM_NOTE_VARIATION_PARAMETER6 = 272
    DRUM_NOTE_VARIATION_PARAMETER7 = 273
    DRUM_NOTE_VARIATION_PARAMETER8 = 274
    DRUM_NOTE_VARIATION_PARAMETER9 = 275
    DRUM_NOTE_VARIATION_PARAMETER10 = 276
    
    # Drum Kit Selection
    DRUM_KIT_SELECT_MSB = 277
    DRUM_KIT_SELECT_LSB = 278
    
    # Drum Setup Channel (Channel 16)
    DRUM_SETUP_CHANNEL = 15
    
    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE, 
                 block_size: int = DEFAULT_BLOCK_SIZE,
                 max_polyphony: int = DEFAULT_MAX_POLYPHONY):
        """
        Initialize XG synthesizer.
        
        Args:
            sample_rate: Sampling rate (default 48000 Hz)
            block_size: Audio block size in samples (default 960)
            max_polyphony: Maximum polyphony (default 64 voices)
        """
        # Basic parameters
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_polyphony = max_polyphony
        self.master_volume = self.DEFAULT_MASTER_VOLUME
        
        # Thread safety lock
        self.lock = threading.RLock()
        
        # SF2 file management
        self.sf2_manager: Optional[Sf2WavetableManager] = None
        self.sf2_paths: List[str] = []
        
        # Per-channel renderers (one per MIDI channel)
        self.channel_renderers: List[XGChannelRenderer] = []
        for channel in range(16):
            renderer = XGChannelRenderer(channel=channel, sample_rate=sample_rate)
            self.channel_renderers.append(renderer)
        
        # Channel states
        self.channel_states: List[Dict[str, Any]] = [self._create_channel_state() for _ in range(16)]
        
        # RPN/NRPN states
        self.rpn_states: List[Dict[str, int]] = [{"msb": 127, "lsb": 127} for _ in range(16)]
        self.nrpn_states: List[Dict[str, int]] = [{"msb": 127, "lsb": 127} for _ in range(16)]
        self.data_entry_states: List[Dict[str, int]] = [{"msb": 0, "lsb": 0} for _ in range(16)]
        
        # Drum parameters for each channel
        self.drum_parameters: List[Dict[int, Dict[str, Any]]] = [{} for _ in range(16)]
        
        # Effects
        self.effect_manager = XGEffectManager(sample_rate)
        
        # Counters for unique identification
        self.generator_id_counter = 0
        
        # Structures for frame-by-frame (sample-accurate) processing
        self._message_heap: List[Tuple[float, int, int, int, int]] = []  # (time, priority, status, data1, data2)
        self._sysex_heap: List[Tuple[float, int, List[int]]] = []  # (time, priority, data)
        self._current_time: float = 0.0  # Current time in seconds for buffered mode
        self._block_start_time: float = 0.0  # Start time of current audio block
        self._sample_times: List[float] = []  # Timestamps for each sample in block
        self._message_priority_counter: int = 0  # Counter for unique message identification
        self._message_buffer = []
        self._sysex_buffer = []
        self.sf2_manager = None
        
        # Set wavetable manager for all channel renderers
        for renderer in self.channel_renderers:
            renderer.wavetable = self.sf2_manager
            
        # Initialize XG
        self._initialize_xg()
        
    def _create_channel_state(self) -> Dict[str, Any]:
        """Create initial MIDI channel state"""
        return {
            "program": 0,
            "bank": 0,
            "volume": 100,
            "expression": 127,
            "pan": 64,
            "mod_wheel": 0,
            "pitch_bend": 8192,
            "pitch_bend_range": 2,
            "sustain_pedal": False,
            "portamento": False,
            "portamento_time": 0,
            "reverb_send": 40,
            "chorus_send": 0,
            "variation_send": 0,
            "key_pressure": {},
            "controllers": {i: 0 for i in range(128)},
            "rpn_msb": 127,
            "rpn_lsb": 127,
            "nrpn_msb": 127,
            "nrpn_lsb": 127,
            "drum_kit": 0,  # Current drum kit
            "drum_bank": 128  # Default drum bank
        }
        
    def _initialize_xg(self):
        """Initialize XG synthesizer according to standard"""
        # Initialize XG without sending SYSEX message
        # Reset all channels to default state
        for channel in range(16):
            # Reset all controllers
            self._handle_reset_all_controllers(channel)
            
            # Set standard XG values
            self.channel_states[channel]["pitch_bend_range"] = 2  # Standard pitch bend range
            self.channel_states[channel]["reverb_send"] = 40     # Standard reverb send
            self.channel_states[channel]["chorus_send"] = 0      # No chorus send by default
            self.channel_states[channel]["variation_send"] = 0   # No variation send by default
            
            # Initialize standard values for all controllers
            for i in range(128):
                self.channel_states[channel]["controllers"][i] = 0
            self.channel_states[channel]["controllers"][7] = 100   # Volume = 100
            self.channel_states[channel]["controllers"][10] = 64   # Pan = 64 (center)
            self.channel_states[channel]["controllers"][11] = 127  # Expression = 127
            self.channel_states[channel]["controllers"][91] = 40   # Reverb Send = 40
            self.channel_states[channel]["controllers"][93] = 0    # Chorus Send = 0
            
            # Reset RPN/NRPN states
            self.rpn_states[channel] = {"msb": 127, "lsb": 127}
            self.nrpn_states[channel] = {"msb": 127, "lsb": 127}
            self.data_entry_states[channel] = {"msb": 0, "lsb": 0}
            
            # Initialize effect parameters in effect manager
            self.effect_manager.set_current_nrpn_channel(channel)
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, 40)  # Reverb send
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, 0)   # Chorus send
            
            # Initialize drum parameters
            self.drum_parameters[channel] = {}
            
        # Reset effects to standard XG state
        self.effect_manager.reset_effects()
        
        # Additional initialization to match XG standard
        # Set standard parameters for all channels
        for channel in range(16):
            # Program Change to piano (program 0) for all channels
            self._handle_program_change(channel, 0)
            # For channel 9, set drum mode by default for XG compatibility
            if channel == 9:
                # Set drum mode via RPN
                self.channel_renderers[channel]._handle_rpn(0, 120, 1, 0)  # Set drum mode on
                # Set drum bank
                self.channel_states[channel]["bank"] = 128
                
    def set_sf2_files(self, sf2_paths: List[str]):
        """
        Set list of SF2 files to use with synthesizer.
        
        Args:
            sf2_paths: List of paths to SF2 files
        """
        with self.lock:
            self.sf2_paths = sf2_paths.copy()
            
            # If real SF2 file paths are provided, create real manager
            if sf2_paths and any(os.path.exists(path) for path in sf2_paths):
                try:
                    self.sf2_manager = Sf2WavetableManager(sf2_paths)
                except Exception as e:
                    print(f"Error creating SF2 manager: {e}")
                    self.sf2_manager = None
            else:
                self.sf2_manager = None
                    
            # Update wavetable manager for all channel renderers
            for renderer in self.channel_renderers:
                renderer.wavetable = self.sf2_manager
                
    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Set bank blacklist for specified SF2 file.
        
        Args:
            sf2_path: Path to SF2 file
            bank_list: List of bank numbers to exclude
        """
        if self.sf2_manager:
            with self.lock:
                self.sf2_manager.set_bank_blacklist(sf2_path, bank_list)
                
    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Set preset blacklist for specified SF2 file.
        
        Args:
            sf2_path: Path to SF2 file
            preset_list: List of (bank, program) tuples to exclude
        """
        if self.sf2_manager:
            with self.lock:
                self.sf2_manager.set_preset_blacklist(sf2_path, preset_list)
                
    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Set MIDI bank to SF2 bank mapping for specified file.
        
        Args:
            sf2_path: Path to SF2 file
            bank_mapping: Dictionary mapping midi_bank -> sf2_bank
        """
        if self.sf2_manager:
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
            # Add regular MIDI messages to heap
            for time, status, data1, data2 in messages:
                priority = self._message_priority_counter
                self._message_priority_counter += 1
                heapq.heappush(self._message_heap, (time, priority, status, data1, data2))
                
            # Add SYSEX messages to heap if provided
            if sysex_messages:
                for time, data in sysex_messages:
                    priority = self._message_priority_counter
                    self._message_priority_counter += 1
                    heapq.heappush(self._sysex_heap, (time, priority, data))
                    
    def set_buffered_mode_time(self, time: float):
        """
        Set current time for buffered mode.
        All messages with time <= current time will be processed.
        
        Args:
            time: Current time in seconds
        """
        with self.lock:
            self._current_time = time
            
    def get_buffered_mode_time(self) -> float:
        """
        Get current time for buffered mode.
        
        Returns:
            Current time in seconds
        """
        with self.lock:
            return self._current_time
            
    def clear_message_buffers(self):
        """
        Clear message buffers.
        """
        with self.lock:
            self._message_buffer.clear()
            self._sysex_buffer.clear()
            
    def _prepare_sample_times(self, block_size: int):
        """
        Prepare timestamps for each sample in block.
        Used for precise MIDI message synchronization by sample.
        
        Args:
            block_size: Block size in samples
        """
        # Calculate time for each sample in block
        self._sample_times = []
        sample_duration = 1.0 / self.sample_rate
        
        for i in range(block_size):
            sample_time = self._block_start_time + (i * sample_duration)
            self._sample_times.append(sample_time)
            
    def _process_sample_accurate_messages(self, sample_index: int):
        """
        Process MIDI messages with sample-accurate synchronization.
        
        Args:
            sample_index: Sample index in current block (0 - block_size-1)
        """
        if not self._sample_times or sample_index >= len(self._sample_times):
            return
            
        # Get time for current sample
        current_sample_time = self._sample_times[sample_index]
        
        # Process regular MIDI messages whose time has arrived
        processed_messages = []
        for i, (msg_time, status, data1, data2) in enumerate(self._message_buffer):
            if msg_time <= current_sample_time:
                # Process message immediately
                self.send_midi_message(status, data1, data2)
                processed_messages.append(i)
            else:
                break
                
        # Remove processed messages (in reverse order to not disrupt indices)
        for i in reversed(processed_messages):
            del self._message_buffer[i]
            
        # Process SYSEX messages whose time has arrived
        processed_sysex = []
        for i, (msg_time, data) in enumerate(self._sysex_buffer):
            if msg_time <= current_sample_time:
                # Process SYSEX message immediately
                self.send_sysex(data)
                processed_sysex.append(i)
            else:
                break
                
        # Remove processed SYSEX messages (in reverse order to not disrupt indices)
        for i in reversed(processed_sysex):
            del self._sysex_buffer[i]
            
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
            if command == self.NOTE_OFF:
                self._handle_note_off(channel, data1, data2)
            elif command == self.NOTE_ON:
                self._handle_note_on(channel, data1, data2)
            elif command == self.POLY_PRESSURE:
                self._handle_poly_pressure(channel, data1, data2)
            elif command == self.CONTROL_CHANGE:
                self._handle_control_change(channel, data1, data2)
            elif command == self.PROGRAM_CHANGE:
                self._handle_program_change(channel, data1)
            elif command == self.CHANNEL_PRESSURE:
                self._handle_channel_pressure(channel, data1)
            elif command == self.PITCH_BEND:
                self._handle_pitch_bend(channel, data1, data2)
                
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
            # Add message to heap with unique priority for stable sorting
            priority = self._message_priority_counter
            self._message_priority_counter += 1
            
            heapq.heappush(self._message_heap, (time, priority, status, data1, data2))
            
    def process_buffered_messages(self, current_time: float):
        """
        Process buffered MIDI messages up to specified time.
        Uses heap for efficient message processing in time order.
        
        Args:
            current_time: Current time in seconds
        """
        with self.lock:
            # Process all messages whose time has arrived
            while self._message_heap and self._message_heap[0][0] <= current_time:
                _, _, status, data1, data2 = heapq.heappop(self._message_heap)
                self.send_midi_message(status, data1, data2)
                
    def send_sysex(self, data: List[int]):
        """
        Send system exclusive message.
        
        Args:
            data: SYSEX message data (including F0 and F7)
        """
        with self.lock:
            # Check if this is really a SYSEX message
            if len(data) < 3 or data[0] != self.SYSTEM_EXCLUSIVE or data[-1] != self.END_OF_EXCLUSIVE:
                return
                
            # Determine manufacturer
            if len(data) >= 2 and data[1] == 0x43:  # Yamaha
                self._handle_yamaha_sysex(data)
            else:
                # Process other manufacturers
                pass
                
    def send_sysex_at_time(self, data: List[int], time: float):
        """
        Send system exclusive message with specified time.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.
        
        Args:
            data: SYSEX message data (including F0 and F7)
            time: Time in seconds to process message
        """
        with self.lock:
            # Add message to heap with unique priority for stable sorting
            priority = self._message_priority_counter
            self._message_priority_counter += 1
            
            heapq.heappush(self._sysex_heap, (time, priority, data))
            
    def process_buffered_sysex(self, current_time: float):
        """
        Process buffered SYSEX messages up to specified time.
        Uses heap for efficient message processing in time order.
        
        Args:
            current_time: Current time in seconds
        """
        with self.lock:
            # Process all messages whose time has arrived
            while self._sysex_heap and self._sysex_heap[0][0] <= current_time:
                _, _, data = heapq.heappop(self._sysex_heap)
                self.send_sysex(data)
                
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
            
        print(f"DEBUG: Handling Note On - channel={channel}, note={note}, velocity={velocity}")
        
        # Forward to channel renderer
        self.channel_renderers[channel].note_on(note, velocity)
        
    def _handle_poly_pressure(self, channel: int, note: int, pressure: int):
        """Handle Poly Pressure (Key Aftertouch) message"""
        # Store in channel state
        self.channel_states[channel]["key_pressure"][note] = pressure
        # Note: Key pressure is handled per-note in the channel renderer if needed
        
    def _handle_control_change(self, channel: int, controller: int, value: int):
        """Handle Control Change message"""
        # Update controller state
        self.channel_states[channel]["controllers"][controller] = value
        
        # Handle specific controllers
        if controller == 1:  # Modulation Wheel
            self.channel_states[channel]["mod_wheel"] = value
        elif controller == 7:  # Volume
            self.channel_states[channel]["volume"] = value
        elif controller == 10:  # Pan
            self.channel_states[channel]["pan"] = value
        elif controller == 11:  # Expression
            self.channel_states[channel]["expression"] = value
        elif controller == 64:  # Sustain Pedal
            self.channel_states[channel]["sustain_pedal"] = (value >= 64)
        elif controller == 65:  # Portamento Switch
            self.channel_states[channel]["portamento"] = (value >= 64)
        elif controller == 91:  # Reverb Send
            self.channel_states[channel]["reverb_send"] = value
            # Pass value to effect manager
            self.effect_manager.set_channel_effect_parameter(channel, 0, 160, value)
        elif controller == 93:  # Chorus Send
            self.channel_states[channel]["chorus_send"] = value
            # Pass value to effect manager
            self.effect_manager.set_channel_effect_parameter(channel, 0, 161, value)
        elif controller == 120:  # All Sound Off
            self._handle_all_sound_off(channel)
        elif controller == 121:  # Reset All Controllers
            self._handle_reset_all_controllers(channel)
        elif controller == 123:  # All Notes Off
            self._handle_all_notes_off(channel)
            
        # Handle RPN/NRPN
        if controller == self.RPN_MSB:
            self.rpn_states[channel]["msb"] = value
            self.nrpn_states[channel]["msb"] = 127  # Reset NRPN
        elif controller == self.RPN_LSB:
            self.rpn_states[channel]["lsb"] = value
            self.nrpn_states[channel]["lsb"] = 127  # Reset NRPN
        elif controller == self.NRPN_MSB:
            self.nrpn_states[channel]["msb"] = value
            self.rpn_states[channel]["msb"] = 127  # Reset RPN
        elif controller == self.NRPN_LSB:
            self.nrpn_states[channel]["lsb"] = value
            self.rpn_states[channel]["lsb"] = 127  # Reset RPN
        elif controller == self.DATA_ENTRY_MSB:
            self.data_entry_states[channel]["msb"] = value
            self._handle_data_entry(channel)
        elif controller == self.DATA_ENTRY_LSB:
            self.data_entry_states[channel]["lsb"] = value
            self._handle_data_entry(channel)
            
        # Forward to channel renderer
        self.channel_renderers[channel].control_change(controller, value)
        
    def _handle_program_change(self, channel: int, program: int):
        """Handle Program Change message"""
        self.channel_states[channel]["program"] = program
        
        # For drum channels (channels in drum mode), set drum bank
        if self.channel_renderers[channel].is_drum:
            self.channel_states[channel]["bank"] = 128
            
        # Forward to channel renderer
        self.channel_renderers[channel].program_change(program)
        
    def _handle_channel_pressure(self, channel: int, pressure: int):
        """Handle Channel Pressure (Aftertouch) message"""
        self.channel_states[channel]["channel_pressure"] = pressure
        
        # Forward to channel renderer
        self.channel_renderers[channel].channel_pressure(pressure)
        
    def _handle_pitch_bend(self, channel: int, lsb: int, msb: int):
        """Handle Pitch Bend message"""
        # 14-bit pitch bend value
        value = (msb << 7) | lsb
        self.channel_states[channel]["pitch_bend"] = value
        
        # Forward to channel renderer
        self.channel_renderers[channel].pitch_bend(lsb, msb)
        
    def _handle_data_entry(self, channel: int):
        """Handle Data Entry for RPN/NRPN"""
        # Get current states
        rpn_msb = self.rpn_states[channel]["msb"]
        rpn_lsb = self.rpn_states[channel]["lsb"]
        nrpn_msb = self.nrpn_states[channel]["msb"]
        nrpn_lsb = self.nrpn_states[channel]["lsb"]
        data_msb = self.data_entry_states[channel]["msb"]
        data_lsb = self.data_entry_states[channel]["lsb"]
        
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
        if channel == self.DRUM_SETUP_CHANNEL:
            self._handle_drum_setup_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb)
            
        # Also forward to channel renderer
        # Note: NRPN handling is done in the channel renderer
        pass
        
    def _handle_drum_setup_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle NRPN drum parameters through setup channel (16)"""
        # 14-bit data value
        data = (data_msb << 7) | data_lsb
        
        # Get drum note from current setup channel state
        drum_note = self.channel_states[self.DRUM_SETUP_CHANNEL].get("current_drum_note", 36)
        
        # Process various drum parameters
        if nrpn_lsb == self.DRUM_NOTE_TUNE:
            # Drum pitch tuning (-64..+63 semitones)
            tune = (data - 8192) / 100.0  # Convert to semitones
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["tune"] = tune
        elif nrpn_lsb == self.DRUM_NOTE_LEVEL:
            # Drum level (0..127)
            level = data / 127.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["level"] = level
        elif nrpn_lsb == self.DRUM_NOTE_PAN:
            # Drum panning (-64..+63)
            pan = (data - 8192) / 8192.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["pan"] = pan
        elif nrpn_lsb == self.DRUM_NOTE_REVERB:
            # Drum reverb send (0..127)
            reverb = data / 127.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["reverb_send"] = reverb
        elif nrpn_lsb == self.DRUM_NOTE_CHORUS:
            # Drum chorus send (0..127)
            chorus = data / 127.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["chorus_send"] = chorus
        elif nrpn_lsb == self.DRUM_NOTE_VARIATION:
            # Drum variation send (0..127)
            variation = data / 127.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["variation_send"] = variation
        elif nrpn_lsb == self.DRUM_NOTE_KEY_ASSIGN:
            # Drum key assignment (0..127)
            key_assign = data
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["key_assign"] = key_assign
        elif nrpn_lsb == self.DRUM_NOTE_FILTER_CUTOFF:
            # Drum filter cutoff frequency (0..127)
            cutoff = 20 + data * 150  # 20Hz to 19020Hz
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["filter_cutoff"] = cutoff
        elif nrpn_lsb == self.DRUM_NOTE_FILTER_RESONANCE:
            # Drum filter resonance (0..127)
            resonance = data / 64.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["filter_resonance"] = resonance
        elif nrpn_lsb == self.DRUM_NOTE_EG_ATTACK:
            # Drum envelope attack (0..127)
            attack = data * 0.05  # 0 to 6.35 seconds
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["eg_attack"] = attack
        elif nrpn_lsb == self.DRUM_NOTE_EG_DECAY:
            # Drum envelope decay (0..127)
            decay = data * 0.05  # 0 to 6.35 seconds
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["eg_decay"] = decay
        elif nrpn_lsb == self.DRUM_NOTE_EG_RELEASE:
            # Drum envelope release (0..127)
            release = data * 0.05  # 0 to 6.35 seconds
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["eg_release"] = release
        elif nrpn_lsb == self.DRUM_NOTE_PITCH_COARSE:
            # Drum pitch coarse tuning (-64..+63 semitones)
            pitch_coarse = (data - 8192) / 100.0
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["pitch_coarse"] = pitch_coarse
        elif nrpn_lsb == self.DRUM_NOTE_PITCH_FINE:
            # Drum pitch fine tuning (-64..+63 cents)
            pitch_fine = (data - 8192) * 0.5
            # Apply parameter to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    if drum_note not in self.drum_parameters[ch]:
                        self.drum_parameters[ch][drum_note] = {}
                    self.drum_parameters[ch][drum_note]["pitch_fine"] = pitch_fine
        elif nrpn_lsb == self.DRUM_KIT_SELECT_LSB:
            # Drum kit selection
            kit = data
            # Apply to all drum channels
            for ch in range(16):
                if self.channel_renderers[ch].is_drum or self.channel_states[ch].get("bank") == 128:
                    self.channel_states[ch]["drum_kit"] = kit
                    
    def get_drum_instrument_name(self, channel: int, note: int) -> Optional[str]:
        """
        Get drum instrument name.
        
        Args:
            channel: MIDI channel
            note: MIDI note
            
        Returns:
            Drum instrument name or None
        """
        if self.sf2_manager:
            # For drum channel, create temporary tone generator to get map
            is_drum = self.channel_renderers[channel].is_drum or (self.channel_states[channel].get("bank") == 128)
            if is_drum:
                from tg import DrumNoteMap  # Import from original tg module
                drum_map = DrumNoteMap()
                return drum_map.get_instrument_name(note)
        return None
        
    def set_drum_parameter(self, channel: int, note: int, parameter: str, value: float):
        """
        Set drum instrument parameter.
        
        Args:
            channel: MIDI channel
            note: Drum note
            parameter: Parameter name ("tune", "level", "pan", etc.)
            value: Parameter value
        """
        if channel not in range(16):
            return
            
        is_drum = self.channel_renderers[channel].is_drum or (self.channel_states[channel].get("bank") == 128)
        if not is_drum:
            return
            
        if note not in self.drum_parameters[channel]:
            self.drum_parameters[channel][note] = {}
            
        self.drum_parameters[channel][note][parameter] = value
        
        # Update channel renderer parameters
        self.channel_renderers[channel].set_drum_instrument_parameters(note, 
                                                                     self.drum_parameters[channel][note])
                                                                     
    def get_drum_parameter(self, channel: int, note: int, parameter: str) -> Optional[float]:
        """
        Get drum instrument parameter.
        
        Args:
            channel: MIDI channel
            note: Drum note
            parameter: Parameter name
            
        Returns:
            Parameter value or None
        """
        if channel not in range(16):
            return None
            
        is_drum = self.channel_renderers[channel].is_drum or (self.channel_states[channel].get("bank") == 128)
        if not is_drum:
            return None
            
        if note in self.drum_parameters[channel]:
            return self.drum_parameters[channel][note].get(parameter, None)
        return None
        
    def set_current_drum_note(self, channel: int, note: int):
        """
        Set current drum note for parameter setup.
        
        Args:
            channel: MIDI channel (should be drum setup channel - 16)
            note: Drum note
        """
        if channel == self.DRUM_SETUP_CHANNEL:
            self.channel_states[channel]["current_drum_note"] = note
            # Also set in channel renderer
            self.channel_renderers[channel].set_current_drum_note(note)
            
    def _handle_yamaha_sysex(self, data: List[int]):
        """Handle Yamaha SYSEX messages"""
        if len(data) < 6:
            return
            
        # Extract SysEx message parameters
        device_id = data[1] if len(data) > 1 else 0
        sub_status = data[2] if len(data) > 2 else 0
        command = data[3] if len(data) > 3 else 0
        
        # Forward message to effect manager
        self.effect_manager.handle_sysex(0x43, data[1:])  # 0x43 - Yamaha manufacturer ID
        
        # Forward message to all channel renderers
        for renderer in self.channel_renderers:
            try:
                renderer.sysex([0x43], data[1:])  # 0x43 - Yamaha manufacturer ID
            except Exception as e:
                print(f"Error processing SysEx in channel renderer: {e}")
                
    def _handle_all_sound_off(self, channel: int):
        """Handle All Sound Off controller"""
        # Stop all active notes on channel
        self.channel_renderers[channel].all_sound_off()
        
    def _handle_reset_all_controllers(self, channel: int):
        """Handle Reset All Controllers controller"""
        # Reset channel state
        self.channel_states[channel] = self._create_channel_state()
        
        # Reset RPN/NRPN states
        self.rpn_states[channel] = {"msb": 127, "lsb": 127}
        self.nrpn_states[channel] = {"msb": 127, "lsb": 127}
        self.data_entry_states[channel] = {"msb": 0, "lsb": 0}
        
        # Reset effect parameters in effect manager
        self.effect_manager.set_current_nrpn_channel(channel)
        self.effect_manager.set_channel_effect_parameter(channel, 0, 160, 40)  # Reverb send
        self.effect_manager.set_channel_effect_parameter(channel, 0, 161, 0)   # Chorus send
        
        # Reset drum parameters
        self.drum_parameters[channel] = {}
        
        # Forward to channel renderer
        # Note: Controller reset is handled in the channel renderer
        
    def _handle_all_notes_off(self, channel: int):
        """Handle All Notes Off controller"""
        # Stop all active notes on channel
        self.channel_renderers[channel].all_notes_off()
        
    def generate_audio_block(self, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block in immediate mode or with message processing at block boundary.
        For true frame-by-frame accuracy, use generate_audio_block_buffered().
        
        Args:
            block_size: Block size in samples (if None, uses default value)
            
        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        if block_size is None:
            block_size = self.block_size
            
        with self.lock:
            # Process all buffered messages up to current time
            # This ensures compatibility with previous behavior
            self.process_buffered_messages(self._current_time)
            self.process_buffered_sysex(self._current_time)
            
            # Create buffers for each MIDI channel (16 channels)
            channel_buffers = [[(0.0, 0.0) for _ in range(block_size)] for _ in range(16)]
            
            # Generate audio for each channel renderer
            for channel in range(16):
                renderer = self.channel_renderers[channel]
                if renderer.is_active():
                    try:
                        # Generate block audio for this renderer
                        for i in range(block_size):
                            l, r = renderer.generate_sample()
                            # Add to existing audio on this channel
                            existing_l, existing_r = channel_buffers[channel][i]
                            channel_buffers[channel][i] = (existing_l + l, existing_r + r)
                    except Exception as e:
                        print(f"Error generating sample: {e}")
                        # Disable problematic renderer
                        renderer.active = False
                        
            # Apply master volume and limiting to each channel
            for channel in range(16):
                channel_state = self.channel_states[channel]
                volume = channel_state["volume"] / 127.0
                expression = channel_state["expression"] / 127.0
                channel_volume = volume * expression * self.master_volume
                
                for i in range(block_size):
                    l, r = channel_buffers[channel][i]
                    l *= channel_volume
                    r *= channel_volume
                    # Limit values
                    l = max(-1.0, min(1.0, l))
                    r = max(-1.0, min(1.0, r))
                    channel_buffers[channel][i] = (l, r)
                    
            # Apply effects
            try:
                # Prepare multichannel input data for effects
                # Create 16 channels, each with block_size samples
                input_channels = []
                for channel in range(16):
                    channel_samples = []
                    for i in range(block_size):
                        channel_samples.append(channel_buffers[channel][i])
                    input_channels.append(channel_samples)
                    
                # Process effects for all 16 channels
                effected_channels = self.effect_manager.process_audio(
                    input_channels,
                    block_size
                )
                
                # Mix all channels into single stereo output
                left_buffer = np.zeros(block_size, dtype=np.float32)
                right_buffer = np.zeros(block_size, dtype=np.float32)
                
                for channel in range(16):
                    for i in range(block_size):
                        left_buffer[i] += effected_channels[channel][i][0]
                        right_buffer[i] += effected_channels[channel][i][1]
                        
                # Limit final mix
                for i in range(block_size):
                    left_buffer[i] = max(-1.0, min(1.0, left_buffer[i]))
                    right_buffer[i] = max(-1.0, min(1.0, right_buffer[i]))
                    
            except Exception as e:
                print(f"Error processing effects: {e}")
                # If effects don't work, return unprocessed mix
                left_buffer = np.zeros(block_size, dtype=np.float32)
                right_buffer = np.zeros(block_size, dtype=np.float32)
                
                for channel in range(16):
                    for i in range(block_size):
                        left_buffer[i] += channel_buffers[channel][i][0]
                        right_buffer[i] += channel_buffers[channel][i][1]
                        
        return left_buffer, right_buffer
        
    def generate_audio_block_at_time(self, block_size: Optional[int] = None, current_time: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block with buffered message processing.
        
        Args:
            block_size: Block size in samples (if None, uses default value)
            current_time: Current time in seconds for buffered message processing
            
        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        # Process buffered MIDI messages
        self.process_buffered_messages(current_time)
        
        # Process buffered SYSEX messages
        self.process_buffered_sysex(current_time)
        
        # Generate audio block
        return self.generate_audio_block(block_size)
        
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
            # Set block start time
            self._block_start_time = self._current_time
            
            # Create buffers for each sample in block
            left_buffer = np.zeros(block_size, dtype=np.float32)
            right_buffer = np.zeros(block_size, dtype=np.float32)
            
            # Process each sample separately
            for i in range(block_size):
                # Calculate time for current sample
                sample_time = self._block_start_time + (i / self.sample_rate)
                
                # Process all MIDI messages whose time has arrived for this sample
                self._process_message_at_time(sample_time)
                
                # Generate audio for this sample
                left_sample, right_sample = self._generate_single_sample()
                
                # Save sample to buffer
                left_buffer[i] = left_sample
                right_buffer[i] = right_sample
                
            # Update current time
            self._current_time = self._block_start_time + (block_size / self.sample_rate)
            
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
                
    def _generate_audio_block_sample_accurate(self, block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block with frame-by-frame (sample-accurate) MIDI message processing.
        Each audio sample is processed separately with checking for MIDI messages at that moment.
        
        Args:
            block_size: Block size in samples
            
        Returns:
            Tuple (left_channel, right_channel) with audio data
        """
        # Create timestamps for each sample in block
        self._sample_times = [self._block_start_time + (i / self.sample_rate) 
                             for i in range(block_size)]
        
        # Buffers for left and right channels
        left_buffer = np.zeros(block_size, dtype=np.float32)
        right_buffer = np.zeros(block_size, dtype=np.float32)
        
        # Process each sample separately
        for sample_index in range(block_size):
            sample_time = self._sample_times[sample_index]
            
            # Process all MIDI messages whose time has arrived for this sample
            self._process_message_at_time(sample_time)
            
            # Generate audio for this sample
            left_sample, right_sample = self._generate_single_sample()
            
            # Save sample to buffer
            left_buffer[sample_index] = left_sample
            right_buffer[sample_index] = right_sample
            
        # Apply effects to entire block
        left_buffer, right_buffer = self._apply_effects_to_block(left_buffer, right_buffer, block_size)
        
        return left_buffer, right_buffer
        
    def _process_message_at_time(self, sample_time: float):
        """
        Process all MIDI messages whose time has arrived by specified time.
        
        Args:
            sample_time: Time in seconds to process messages
        """
        # Process regular MIDI messages
        while self._message_heap and self._message_heap[0][0] <= sample_time:
            _, _, status, data1, data2 = heapq.heappop(self._message_heap)
            self.send_midi_message(status, data1, data2)
            
        # Process SYSEX messages
        while self._sysex_heap and self._sysex_heap[0][0] <= sample_time:
            _, _, data = heapq.heappop(self._sysex_heap)
            self.send_sysex(data)
            
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
        
    def _apply_effects_to_block(self, left_buffer: np.ndarray, right_buffer: np.ndarray, 
                              block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply effects to audio block.
        
        Args:
            left_buffer: Left channel buffer
            right_buffer: Right channel buffer
            block_size: Block size in samples
            
        Returns:
            Tuple (left_channel, right_channel) with processed audio data
        """
        try:
            # Create multichannel input data for effects
            # For simplicity, use only first 2 channels (stereo mix)
            input_channels = []
            
            # Create 16 channels (for each MIDI channel)
            for channel in range(16):
                channel_samples = []
                # For each sample, create tuple (left, right)
                # In real implementation, there should be more complex channel separation logic
                for i in range(block_size):
                    # For now, mix everything into channel 0, leave others empty
                    if channel == 0:  # Main stereo channel
                        channel_samples.append((left_buffer[i], right_buffer[i]))
                    else:
                        channel_samples.append((0.0, 0.0))  # Empty channels
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
            
    def get_active_voice_count(self) -> int:
        """Get number of active voices"""
        with self.lock:
            count = 0
            for renderer in self.channel_renderers:
                if renderer.is_active():
                    count += 1
            return count
            
    def get_available_programs(self) -> List[Tuple[int, int, str]]:
        """
        Get list of available programs (presets).
        
        Returns:
            List of tuples (bank, program, name)
        """
        if self.sf2_manager:
            with self.lock:
                return self.sf2_manager.get_available_presets()
        return []
        
    def reset(self):
        """Full synthesizer reset"""
        with self.lock:
            # Stop all active notes
            for renderer in self.channel_renderers:
                try:
                    renderer.all_sound_off()
                except:
                    pass
                    
            # Reset channel states
            self.channel_states = [self._create_channel_state() for _ in range(16)]
            
            # Reset RPN/NRPN states
            self.rpn_states = [{"msb": 127, "lsb": 127} for _ in range(16)]
            self.nrpn_states = [{"msb": 127, "lsb": 127} for _ in range(16)]
            self.data_entry_states = [{"msb": 0, "lsb": 0} for _ in range(16)]
            
            # Reset drum parameters
            self.drum_parameters = [{} for _ in range(16)]
            
            # Reset effects
            self.effect_manager.reset_effects()
            
            # Clear message buffers
            self._message_heap.clear()
            self._sysex_heap.clear()
            
            # Reset counters
            self._message_priority_counter = 0
            self._current_time = 0.0
            self._block_start_time = 0.0
            self._sample_times.clear()
            
            # Reinitialize XG
            self._initialize_xg()
            
    def send_midi_message_at_sample(self, status: int, data1: int, data2: int, sample: int):
        """
        Send MIDI message to synthesizer with specified sample.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.
        
        Args:
            status: Status byte (including channel number)
            data1: First data byte
            data2: Second data byte (for messages with two data bytes)
            sample: Sample number to process message (relative to start of current audio block)
        """
        with self.lock:
            # Convert sample number to absolute time
            message_time = self._block_start_time + (sample / self.sample_rate)
            
            # Add message to heap with unique priority for stable sorting
            priority = self._message_priority_counter
            self._message_priority_counter += 1
            
            heapq.heappush(self._message_heap, (message_time, priority, status, data1, data2))
            
    def send_sysex_at_sample(self, data: List[int], sample: int):
        """
        Send system exclusive message with specified sample.
        Messages are buffered and processed during audio generation with frame-by-frame accuracy.
        
        Args:
            data: SYSEX message data (including F0 and F7)
            sample: Sample number to process message (relative to start of current audio block)
        """
        with self.lock:
            # Convert sample number to absolute time
            message_time = self._block_start_time + (sample / self.sample_rate)
            
            # Add message to heap with unique priority for stable sorting
            priority = self._message_priority_counter
            self._message_priority_counter += 1
            
            heapq.heappush(self._sysex_heap, (message_time, priority, data))


# Usage example:
#
# # Create synthesizer
# synth = XGSynthesizer(sample_rate=48000, block_size=960)  # 20ms blocks at 48kHz
#
# # Set SF2 files
# synth.set_sf2_files(["path/to/soundfont1.sf2", "path/to/soundfont2.sf2"])
#
# # Set blacklists and bank mapping
# synth.set_bank_blacklist("path/to/soundfont1.sf2", [120, 121, 122])
# synth.set_preset_blacklist("path/to/soundfont1.sf2", [(0, 30), (0, 31)])
# synth.set_bank_mapping("path/to/soundfont1.sf2", {1: 0, 2: 1})
#
# # Send MIDI messages with frame-by-frame accuracy
# synth.send_midi_message_at_sample(0x90, 60, 100, 100)  # Note On: C4, velocity 100 at sample 100
# synth.send_midi_message_at_sample(0x80, 60, 64, 200)   # Note Off: C4 at sample 200
#
# # Generate audio block with frame-by-frame processing
# left_channel, right_channel = synth.generate_audio_block_sample_accurate(960)
#
# # Get information
# voice_count = synth.get_active_voice_count()
# programs = synth.get_available_programs()