"""
HIGH-PERFORMANCE XG SYNTHESIZER

Fully MIDI XG compatible software synthesizer with optimized vectorized processing.

Key Features:
- Sample-perfect MIDI message processing with precise timing accuracy
- Vectorized audio generation using NumPy operations for maximum performance
- Efficient buffer management with pre-allocated memory pools
- Comprehensive XG specification compliance including insertion effects
- Multi-channel audio rendering with individual channel processing
- Real-time effects processing per XG specification requirements
- Thread-safe design for concurrent access in real-time applications

Architecture:
- Buffered MIDI message processing for efficient real-time performance
- Per-channel audio generation for proper XG insertion effects support
- Vectorized mathematical operations for high-performance computing
- Object pooling to minimize memory allocation overhead
- Pre-allocated audio buffers for zero-allocation rendering
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from synth.channel.vectorized_channel_renderer import VectorizedChannelRenderer
from synth.core.buffer_pool import XGBufferPool
from synth.core.envelope import EnvelopePool
from synth.core.filter import FilterPool
from synth.core.oscillator import OscillatorPool
from synth.core.panner import PannerPool

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ..core.constants import DEFAULT_CONFIG
from ..midi.parser import MIDIMessage
from ..sf2.manager import SF2Manager
from ..xg.drum_manager import DrumManager
from ..xg.xg_receive_channel_manager import XGReceiveChannelManager
from ..xg.xg_rpn_controller import XGRPNController
from .optimized_coefficient_manager import (
    get_global_coefficient_manager,
)

# MIDI Message Type Constants (for maintainability)
MSG_TYPE_NOTE_OFF = "note_off"
MSG_TYPE_NOTE_ON = "note_on"
MSG_TYPE_POLY_PRESSURE = "poly_pressure"
MSG_TYPE_CONTROL_CHANGE = "control_change"
MSG_TYPE_PROGRAM_CHANGE = "program_change"
MSG_TYPE_CHANNEL_PRESSURE = "channel_pressure"
MSG_TYPE_PITCH_BEND = "pitch_bend"
MSG_TYPE_SYSEX = "sysex"

from ..audio.writer import AudioWriter

# XG Effects System Integration - Production-Ready Effects Coordinator
from ..effects import (
    XGEffectsCoordinator,  # Main coordinator (production-ready)
    )
from ..effects.xg_nrpn_controller import XGNRPNController
from ..effects.xg_sysex_controller import XGSYSEXController


class OptimizedXGSynthesizer:
    """
    HIGH-PERFORMANCE XG SYNTHESIZER

    Fully MIDI XG compatible software synthesizer with optimized vectorized processing.

    Key Features:
    - Sample-perfect MIDI message processing with precise timing accuracy
    - Vectorized audio generation using NumPy operations for maximum performance
    - Efficient buffer management with pre-allocated memory pools
    - Comprehensive XG specification compliance including insertion effects
    - Multi-channel audio rendering with individual channel processing
    - Real-time effects processing per XG specification requirements
    - Thread-safe design for concurrent access in real-time applications

    Architecture:
    - Buffered MIDI message processing for efficient real-time performance
    - Per-channel audio generation for proper XG insertion effects support
    - Vectorized mathematical operations for high-performance computing
    - Object pooling to minimize memory allocation overhead
    - Pre-allocated audio buffers for zero-allocation rendering
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_CONFIG["SAMPLE_RATE"],
        max_polyphony: int = DEFAULT_CONFIG["MAX_POLYPHONY"],
        block_size: int = DEFAULT_CONFIG["BLOCK_SIZE"],
        sf2_files=None,
        param_cache=None,
        render_log_level: int = 0,
        voice_allocation_mode: int = 1,  # Default to XG priority polyphonic
        memory_pool_stereo_multiplier: int = 8,  # Configurable memory pool size multipliers
        memory_pool_mono_multiplier: int = 4,
        minimum_time_slice: float = 0.002,  # Configurable timing parameters
        sysex_response_callback: Callable | None = None,  # Callback for SYSEX responses
        architecture: str = "legacy",  # "legacy" or "voice" - NEW: Architecture selection
    ):
        """
        Initialize optimized XG synthesizer with performance enhancements.

        Args:
            sample_rate: Sampling rate (default 44100 Hz)
            max_polyphony: Maximum polyphony (default 64 voices)
            block_size: Audio processing block size (default 1024)
            sf2_files: Optional list of SF2 soundfont files
            param_cache: Optional parameter cache for performance optimization
            render_log_level: Audio rendering debug log level (0-3)
            voice_allocation_mode: Voice allocation mode (0=basic poly, 1=XG priority, 2=mono)
        """
        # Basic parameters - use fixed default block size for simplicity
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_polyphony = max_polyphony
        self.master_volume = DEFAULT_CONFIG["MASTER_VOLUME"]
        self.render_log_level = render_log_level
        self.voice_allocation_mode = voice_allocation_mode
        self.sysex_response_callback = sysex_response_callback
        self.architecture = architecture  # NEW: Architecture selection

        # Thread safety lock
        self.lock = threading.RLock()

        # Modulation matrix configuration
        self.use_modulation_matrix = True  # Enable XG modulation matrix by default

        # Memory and object pooling system - XGBufferPool for advanced buffer management
        self.memory_pool = XGBufferPool(
            sample_rate=sample_rate, max_block_size=block_size
        )  # Advanced zero-allocation buffer pool
        self._initialize_object_pools()

        # Core synthesizer components owned by this class
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_polyphony = max_polyphony

        # Drum management
        self.drum_manager = DrumManager()

        # SF2 file management
        self.sf2_manager = SF2Manager(param_cache=param_cache, drum_manager=self.drum_manager)
        if sf2_files:
            self.sf2_manager.set_sf2_files(sf2_files)

        # Per-channel renderers owned by synthesizer (one per MIDI channel)
        # Can be VectorizedChannelRenderer (legacy) or Channel (voice)
        self.channel_renderers: list[Any] = []
        self._create_channel_renderers()

        # NEW XG Effects System - Zero-allocation, XG-compliant effects coordinator
        self.effects_coordinator = XGEffectsCoordinator(
            sample_rate=sample_rate,
            block_size=block_size,
            max_channels=self.num_channels,  # 16 for XG
        )
        self.effects_coordinator.reset_all_effects()  # Set XG defaults

        # XG NRPN Controller for comprehensive MIDI parameter control
        self.nrpn_controller = XGNRPNController(self.effects_coordinator)

        # XG RPN Controller for standard MIDI parameter control
        self.rpn_controller = XGRPNController()

        # XG SYSEX Controller for bulk parameter dumps and advanced control
        self.sysex_controller = XGSYSEXController(self.effects_coordinator, self.nrpn_controller)

        # XG Receive Channel Manager - Production-ready multichannel routing
        self.receive_channel_manager = XGReceiveChannelManager(num_parts=self.num_channels)

        # Initialize optimized coefficient manager for performance optimization

        self.coeff_manager = get_global_coefficient_manager()

        # Initialize partial generator pool for XG partial management
        from ..xg.channel_note import PartialGeneratorPool

        self.partial_pool = PartialGeneratorPool(
            max_size=512
        )  # Pool for up to 512 partial generators

        # Initialize message processing state
        self._message_sequence: list[MIDIMessage] = []
        self._current_message_index: int = 0
        self._current_time: float = 0.0
        self._minimum_time_slice = minimum_time_slice

        # Pre-allocated audio buffers for performance
        self._initialize_audio_buffers()

        # Initialize XG
        self._initialize_xg()

        # Warm up numba-compiled functions to avoid runtime compilation
        self._warm_up_numba_functions()

        # Recreate performance log file upon class creation
        self._recreate_performance_log()

        # Initialize audio writers for debugging pipeline
        self._initialize_audio_writers()

        # Ensure render_logs directory exists
        os.makedirs("render_logs", exist_ok=True)

    def _create_channel_renderers(self):
        """Create and initialize channel renderers owned by synthesizer."""
        self.num_channels = DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]
        self.channel_renderers = [None] * self.num_channels
        self.channel_buffers = [None] * self.num_channels

        # NEW: Architecture selection
        if self.architecture == "voice":
            # Use new Voice architecture
            from ..engine.synthesis_engine import SynthesisEngineRegistry
            from ..voice.voice_factory import VoiceFactory

            # Initialize voice architecture components
            self.engine_registry = SynthesisEngineRegistry()
            from .sf2_engine import SF2Engine

            sf2_engine = SF2Engine()
            self.engine_registry.register_engine(sf2_engine)

            self.voice_factory = VoiceFactory(self.engine_registry)

            for channel in range(self.num_channels):
                # Create Voice-based channel
                from ..channel.channel import Channel

                voice_channel = Channel(channel, self.voice_factory, self.sample_rate)
                self.channel_renderers[channel] = voice_channel

        else:  # legacy architecture
            # Use existing legacy architecture
            for channel in range(self.num_channels):
                # Create renderer with synthesizer-owned resources
                renderer = VectorizedChannelRenderer(channel=channel, synth=self)
                # Set voice allocation mode from synthesizer parameter
                renderer.voice_manager.set_allocation_mode(self.voice_allocation_mode)
                self.channel_renderers[channel] = renderer

    def _initialize_audio_buffers(self):
        """Initialize pre-allocated audio buffers for performance using XGBufferPool."""
        # Get buffers from advanced XGBufferPool - optimized for audio processing
        # Main output buffers need zeroing for accumulation
        self.out_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self.temp_left = self.memory_pool.get_mono_buffer(self.block_size)
        self.temp_right = self.memory_pool.get_mono_buffer(self.block_size)
        self.effect_input = self.memory_pool.get_stereo_buffer(self.block_size)
        self.effect_output = self.memory_pool.get_stereo_buffer(self.block_size)

    def get_audio_buffer(
        self, size: int, channels: int = 1, zero_buffer: bool = True
    ) -> np.ndarray:
        """Get an audio buffer from the XGBufferPool."""
        if size == self.block_size and channels == 1:
            return self.memory_pool.get_mono_buffer(size)
        elif size == self.block_size and channels == 2:
            return self.memory_pool.get_stereo_buffer(size)
        else:
            # XGBufferPool handles different sizes automatically
            if channels == 1:
                return self.memory_pool.get_mono_buffer(size)
            else:
                return self.memory_pool.get_stereo_buffer(size)

    def return_audio_buffer(self, buffer: np.ndarray, needs_zeroing: bool = True) -> None:
        """Return an audio buffer to the XGBufferPool."""
        if buffer.shape[0] == self.block_size:
            if buffer.ndim == 1:
                self.memory_pool.return_mono_buffer(buffer)
            elif buffer.ndim == 2 and buffer.shape[1] == 2:
                self.memory_pool.return_stereo_buffer(buffer)

    def _initialize_object_pools(self):
        """Initialize object pools for frequently allocated objects."""
        # Envelope object pool
        self.envelope_pool = EnvelopePool(
            block_size=self.block_size, memory_pool=self.memory_pool, sample_rate=self.sample_rate
        )
        # Channel-level LFO pool for shared channel LFOs
        self.lfo_pool = OscillatorPool(
            max_oscillators=500,
            block_size=self.block_size,
            memory_pool=self.memory_pool,
            sample_rate=self.sample_rate,
        )
        # Dedicated LFO pool for partials to avoid LFO contention (LFO bottleneck fix)
        self.partial_lfo_pool = OscillatorPool(
            max_oscillators=1000,
            block_size=self.block_size,
            memory_pool=self.memory_pool,
            sample_rate=self.sample_rate,
        )
        # Filter pool with OptimizedCoefficientManager integration for instant coefficient lookups
        self.filter_pool = FilterPool(
            block_size=self.block_size,
            memory_pool=self.memory_pool,
            sample_rate=self.sample_rate,
            coeff_manager=self.coeff_manager,
        )
        self.panner_pool = PannerPool(
            block_size=self.block_size, memory_pool=self.memory_pool, sample_rate=self.sample_rate
        )

    def _initialize_xg(self):
        """Initialize XG synthesizer according to XG MIDI specification."""
        # Initialize XG RPN controller - production-ready implementation
        self.rpn_controller.reset_rpn_parameters()

        # Initialize drum kit parameters to XG defaults
        self.drum_manager.reset_all_drum_parameters()

        # XG Effects Manager initialization handled in __init__ with effects_coordinator
        # XG Effects Coordinator is initialized and reset in __init__

        # Additional initialization to match XG standard
        # Set standard parameters for all channels
        for channel in range(self.num_channels):
            # Program Change to piano (program 0) for XG compatibility
            self._handle_program_change(channel, 0)
            # Channel 9 (MIDI channel 10) defaults to drum mode for XG
            if channel == 9:
                # Set drum mode - channel renderer handles internally
                self.channel_renderers[channel].is_drum = True

    def _warm_up_numba_functions(self):
        """Warm up numba-compiled functions to avoid runtime compilation overhead."""
        try:
            # Generate a small amount of audio to trigger numba compilation
            # This will naturally call all the numba functions used in normal operation
            dummy_messages = [
                MIDIMessage(type="note_on", channel=0, note=60, velocity=100, time=0.0),
                MIDIMessage(type="note_off", channel=0, note=60, velocity=0, time=0.1),
            ]
            self.send_midi_message_block(dummy_messages)

            # Generate a small block of audio to trigger all numba paths
            self.generate_audio_block_sample_accurate()

            # Reset to clean state
            self.reset()

        except Exception:
            # If warm-up fails, just continue - numba will compile on first use
            pass

    def _handle_program_change(self, channel: int, program: int):
        """Handle Program Change message."""
        # Forward to channel renderer
        self.channel_renderers[channel].program_change(program)

    # Public API methods
    def set_sf2_files(self, sf2_paths: list[str]):
        """
        Set list of SF2 files to use with synthesizer.

        Args:
            sf2_paths: List of paths to SF2 files
        """
        with self.lock:
            return self.sf2_manager.set_sf2_files(sf2_paths)

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

    def set_part_mode(self, channel: int, mode: int):
        """
        Set XG part mode for a specific MIDI channel.

        XG Part Modes control how the synthesizer processes sounds:
        - Mode 0: Normal Mode (standard synthesis)
        - Modes 1-7: Drum Kit variations (different drum kits)

        Args:
            channel: MIDI channel number (0-15)
            mode: Part mode (0-7)

        Returns:
            True if mode was set successfully, False otherwise
        """
        with self.lock:
            if 0 <= channel < len(self.channel_renderers) and 0 <= mode <= 7:
                if hasattr(self.channel_renderers[channel], "set_part_mode"):
                    self.channel_renderers[channel].set_part_mode(mode)
                    print(f"🎹 XG Part Mode: Channel {channel} set to mode {mode}")
                    return True
            return False

    def send_midi_message(self, message: MIDIMessage):
        """
        Send MIDI message to synthesizer with XG receive channel mapping.

        XG Specification Compliance:
        - Messages are routed based on receive channel mapping, not direct MIDI channel
        - Multiple parts can receive from the same MIDI channel
        - Parts can be disabled or set to receive from all channels

        Args:
            message: MIDIMessage instance containing the message data
        """
        with self.lock:
            msg_type = message.type
            midi_channel = message.channel
            if midi_channel is None:
                return  # Not channel-specific message

            # Route message through XG receive channel mapping - Production-ready implementation
            target_parts = self.receive_channel_manager.get_parts_for_midi_channel(midi_channel)

            if not target_parts:
                # No parts receive from this MIDI channel
                return

            # Route message to all target parts
            for part_id in target_parts:
                if part_id >= len(self.channel_renderers):
                    continue  # Invalid part ID

                channel_renderer = self.channel_renderers[part_id]

                # Process based on message type - route to appropriate part
                if msg_type == MSG_TYPE_NOTE_OFF:
                    channel_renderer.note_off(message.note, message.velocity)
                elif msg_type == MSG_TYPE_NOTE_ON:
                    channel_renderer.note_on(message.note, message.velocity)
                elif msg_type == MSG_TYPE_POLY_PRESSURE:
                    # Forward polyphonic aftertouch to channel renderer
                    channel_renderer.set_key_pressure(message.note, message.pressure)
                elif msg_type == MSG_TYPE_CONTROL_CHANGE:
                    # Handle XG Effect Activation (CC 200-209) - forward to effects coordinator
                    if 200 <= message.control <= 209:
                        # XG Effect Unit Activation - map CC 200-209 to effect units 0-9
                        unit_index = message.control - 200
                        active = message.value >= 64  # 64 = halfway point, values >= 64 enable
                        self.effects_coordinator.set_effect_unit_activation(unit_index, active)
                    elif message.control == 84:
                        # XG Part Mode Control (CC 84) - set part mode for this channel
                        # Map 0-127 to part modes 0-7 (XG specification)
                        part_mode = min(
                            message.value // 18, 7
                        )  # Divide range evenly across 8 modes
                        if hasattr(channel_renderer, "set_part_mode"):
                            channel_renderer.set_part_mode(part_mode)
                    elif message.control in (98, 99, 6, 38):
                        # NRPN messages - route to NRPN controller
                        self._handle_nrpn_message(message.control, message.value)
                    elif message.control in (91, 93, 94):
                        # Effect send levels - route to effects coordinator
                        effect_type = {91: "reverb", 93: "chorus", 94: "variation"}[message.control]
                        level = message.value / 127.0  # Convert to 0.0-1.0
                        self.effects_coordinator.set_effect_send_level(part_id, effect_type, level)
                    else:
                        # Forward other control changes to channel renderer
                        channel_renderer.control_change(message.control, message.value)
                elif msg_type == MSG_TYPE_PROGRAM_CHANGE:
                    self._handle_program_change(
                        part_id, message.program
                    )  # Use part_id, not midi_channel
                elif msg_type == MSG_TYPE_CHANNEL_PRESSURE:
                    # Forward channel pressure to channel renderer
                    channel_renderer.set_channel_pressure(message.pressure)
                elif msg_type == MSG_TYPE_PITCH_BEND:
                    # Forward pitch bend to channel renderer
                    channel_renderer.set_pitch_bend(message.pitch)

    def send_sysex(self, message: MIDIMessage):
        """
        Send system exclusive message.

        Args:
            message: MIDIMessage instance containing SYSEX data
        """
        with self.lock:
            data = message.sysex_data
            if not data or len(data) < 3 or data[0] != 0xF0 or data[-1] != 0xF7:
                return

            # Determine manufacturer
            if len(data) >= 2 and data[1] == 0x43:  # Yamaha
                self._handle_yamaha_sysex(data)

    def send_midi_message_block(self, messages: list[MIDIMessage]):
        """
        Send block of MIDI messages for buffered processing.
        Messages are stored in a sorted sequence for efficient consumption during rendering.

        Args:
            messages: List of MIDIMessage instances
        """
        with self.lock:
            # Add messages to the sequence and keep it sorted by time
            self._message_sequence.extend(messages)
            # Sort the entire sequence by time (only when new messages are added)
            self._message_sequence.sort(key=lambda msg: msg.time)

    def generate_audio_block(self) -> np.ndarray:
        """
        Generate audio block using buffered message processing.

        This method processes buffered MIDI messages automatically during audio generation,
        providing efficient buffered processing for real-time applications.

        Uses the synthesizer's default block size set during construction.

        Returns:
            Audio data as numpy array with shape (block_size, 2)
        """
        # Use the sample-accurate method which already handles buffered processing
        return self.generate_audio_block_sample_accurate()

    def _handle_yamaha_sysex(self, data: list[int]):
        """Handle Yamaha SYSEX messages with XG receive channel mapping support."""
        if len(data) < 4:
            return

        # Route to XG SYSEX controller for comprehensive XG SYSEX handling
        if hasattr(self, "sysex_controller") and self.sysex_controller:
            try:
                response = self.sysex_controller.process_sysex(data)
                if response:
                    # Send SYSEX response back to MIDI device if callback is available
                    if self.sysex_response_callback:
                        try:
                            self.sysex_response_callback(response)
                            print(f"XG SYSEX: Response sent ({len(response)} bytes)")
                        except Exception as callback_error:
                            print(f"Warning: SYSEX response callback failed: {callback_error}")
                    else:
                        print(
                            f"XG SYSEX: Processed command, response available ({len(response)} bytes) - no callback configured"
                        )
                return
            except Exception as e:
                print(f"XG SYSEX: Error processing message: {e}")

        # Fallback: Basic XG parameter handling if SYSEX controller not available
        if len(data) >= 8 and data[3] == 0x4C:  # XG Parameter Change
            if data[4] == 0x00:  # Part Mode
                part_id = data[5] if len(data) > 5 else 0
                part_mode = data[6] if len(data) > 6 else 0
                if 0 <= part_id < len(self.channel_renderers) and 0 <= part_mode <= 7:
                    if hasattr(self.channel_renderers[part_id], "set_part_mode"):
                        self.channel_renderers[part_id].set_part_mode(part_mode)
                        print(f"🎹 XG SYSEX: Part {part_id} mode set to {part_mode}")
            elif data[4] == 0x08:  # Receive Channel
                part_id = data[5] if len(data) > 5 else 0
                midi_channel = data[6] if len(data) > 6 else 0
                print(f"🎹 XG SYSEX: Part {part_id} receive channel set to MIDI CH {midi_channel}")

    def _handle_nrpn_message(self, cc_number: int, value: int):
        """
        Handle NRPN (Non-Registered Parameter Number) messages with enhanced processing.

        NRPN messages consist of:
        - CC 98: NRPN LSB (parameter index)
        - CC 99: NRPN MSB (parameter group)
        - CC 6: Data Entry MSB (parameter value)
        - CC 38: Data Entry LSB (fine control, usually unused)

        Enhanced implementation with proper state management and validation.

        Args:
            cc_number: Control change number (98, 99, 6, 38)
            value: Control change value (0-127)
        """
        # Initialize NRPN state if not exists
        if not hasattr(self, "_nrpn_state"):
            self._nrpn_state: dict[str, int | None] = {
                "msb": None,  # NRPN MSB (CC 99)
                "lsb": None,  # NRPN LSB (CC 98)
                "data_msb": None,  # Data Entry MSB (CC 6)
                "data_lsb": None,  # Data Entry LSB (CC 38)
            }

        # Update NRPN state based on controller
        if cc_number == 99:  # NRPN MSB
            self._nrpn_state["msb"] = value
            # Reset data when NRPN is set
            self._nrpn_state["data_msb"] = None
            self._nrpn_state["data_lsb"] = None
        elif cc_number == 98:  # NRPN LSB
            self._nrpn_state["lsb"] = value
            # Reset data when NRPN is set
            self._nrpn_state["data_msb"] = None
            self._nrpn_state["data_lsb"] = None
        elif cc_number == 6:  # Data Entry MSB
            self._nrpn_state["data_msb"] = value
            # Process complete NRPN message if we have all required parts
            self._process_complete_nrpn_message()
        elif cc_number == 38:  # Data Entry LSB
            self._nrpn_state["data_lsb"] = value
            # Process complete NRPN message if we have all required parts
            self._process_complete_nrpn_message()

    def _process_complete_nrpn_message(self):
        """
        Process a complete NRPN message when all required parts are received.

        NRPN requires at minimum: MSB, LSB, and Data MSB.
        Data LSB is optional for fine control.
        """
        state = self._nrpn_state

        # Check if we have minimum required parts for NRPN processing
        if state["msb"] is not None and state["lsb"] is not None and state["data_msb"] is not None:
            # Process the NRPN message through the XG NRPN controller
            if hasattr(self, "nrpn_controller") and self.nrpn_controller:
                try:
                    # Use 0 for LSB if not provided (common case)
                    data_lsb = state["data_lsb"] if state["data_lsb"] is not None else 0

                    # Process NRPN through effects coordinator
                    self.nrpn_controller.process_nrpn(
                        state["msb"], state["lsb"], state["data_msb"], data_lsb
                    )

                    # Log successful NRPN processing
                    nrpn_value = (state["data_msb"] << 7) | data_lsb
                    print(
                        f"🎛️  NRPN: Processed {state['msb']:3d}:{state['lsb']:3d} = {nrpn_value:5d}"
                    )

                except Exception as e:
                    print(f"Warning: NRPN processing failed for {state['msb']}:{state['lsb']}: {e}")

            # Reset NRPN state after processing (NRPN is one-shot)
            self._reset_nrpn_state()

    def _reset_nrpn_state(self):
        """Reset NRPN state to prepare for next message sequence."""
        if hasattr(self, "_nrpn_state"):
            self._nrpn_state = {"msb": None, "lsb": None, "data_msb": None, "data_lsb": None}

    def generate_audio_block_sample_accurate(self) -> np.ndarray:
        """
        TRUE SAMPLE-PERFECT AUDIO PROCESSING - PRODUCTION READY

        Generate audio block with true sample-perfect MIDI message processing.
        Each MIDI message is processed at its exact sample position within the block,
        ensuring perfect timing accuracy for professional audio applications.

        This implements the correct architecture:
        1. Process each sample individually
        2. Apply MIDI messages at exact sample positions
        3. Generate audio for each sample with current state
        4. Apply effects per XG specification

        Uses the synthesizer's default block size set during construction.

        Returns:
            Audio data as numpy array with shape (block_size, 2)
        """
        block_size = self.block_size

        # Performance logging: initialize timing and metrics collection
        start_time = time.perf_counter()
        midi_processing_time = 0.0
        envelope_processing_time = 0.0
        lfo_processing_time = 0.0
        filter_processing_time = 0.0
        wavetable_rendering_time = 0.0
        partial_generator_rendering_time = 0.0
        channel_notes_rendering_time = 0.0
        channels_rendering_time = 0.0
        effect_processing_time = 0.0

        # Initialize real-time counters
        envelope_blocks_processed = 0
        lfo_blocks_processed = 0
        filter_blocks_processed = 0
        wavetable_blocks_processed = 0
        partial_blocks_processed = 0
        channel_note_blocks_processed = 0

        # Initialize performance counters for this audio block
        performance_counters = {
            "envelope_blocks_processed": 0,
            "lfo_blocks_processed": 0,
            "filter_blocks_processed": 0,
            "wavetable_blocks_processed": 0,
            "partial_blocks_processed": 0,
            "channel_note_blocks_processed": 0,
        }

        # Store counters in instance variable for component access
        self._current_performance_counters = performance_counters

        # MIDI event counters
        midi_events_consumed = {
            "sysex": 0,
            "note_on": 0,
            "note_off": 0,
            "control_change": 0,
            "program_change": 0,
            "channel_pressure": 0,
            "pitch_bend": 0,
            "poly_pressure": 0,
            "other": 0,
        }
        segments_processed = 0

        with self.lock:
            if self.out_buffer is None:
                self.out_buffer = self.memory_pool.get_stereo_buffer(self.block_size)

            at_time = self._current_time
            at_index = self._current_message_index
            block_offset = 0

            # Process messages in segments to reduce per-sample overhead
            while block_offset < block_size:
                # Process all messages that occur at or before the minimum time slice
                midi_start = time.perf_counter()
                messages_in_segment = 0
                while (
                    at_index < len(self._message_sequence)
                    and self._message_sequence[at_index].time <= at_time + self._minimum_time_slice
                ):
                    message = self._message_sequence[at_index]
                    at_index += 1
                    messages_in_segment += 1

                    # Count MIDI events by type
                    msg_type = message.type
                    if msg_type in midi_events_consumed:
                        midi_events_consumed[msg_type] += 1
                    else:
                        midi_events_consumed["other"] += 1

                    if message.type == MSG_TYPE_SYSEX:
                        self.send_sysex(message)
                    else:
                        self.send_midi_message(message)

                midi_processing_time += time.perf_counter() - midi_start

                # Determine the segment length until the next MIDI message
                if at_index < len(self._message_sequence):
                    next_time = self._message_sequence[at_index].time
                    segment_length = int((next_time - at_time) * self.sample_rate)
                    # Clamp to remaining block size
                    segment_length = min(segment_length, block_size - block_offset)
                else:
                    # No more messages, process to end of block
                    segment_length = block_size - block_offset

                segments_processed += 1

                # Generate individual channel audio
                channels_start = time.perf_counter()
                channel_audio = self._generate_channel_audio_vectorized(segment_length)
                channels_rendering_time += time.perf_counter() - channels_start

                # Process through new XG effects coordinator (zero-allocation processing)
                effects_start = time.perf_counter()
                # Use buffer from XGBufferPool to maintain zero-allocation principle
                final_stereo_segment = self.memory_pool.get_stereo_buffer(segment_length)
                self.effects_coordinator.process_channels_to_stereo_zero_alloc(
                    channel_audio, final_stereo_segment, segment_length
                )
                effect_processing_time += time.perf_counter() - effects_start

                self.out_buffer[block_offset : block_offset + segment_length] = (
                    final_stereo_segment[:segment_length]
                )

                # Return buffer to pool to maintain zero-allocation
                self.memory_pool.return_stereo_buffer(final_stereo_segment)

                # Advance time by the segment length
                block_offset += segment_length
                at_time = at_time + (segment_length / self.sample_rate)

            # Update message index and time to reflect current position
            self._current_message_index = at_index
            self._current_time = at_time

            # Performance logging: collect and log comprehensive statistics
            total_time = time.perf_counter() - start_time

            # Get final counter values from instance counters
            envelope_blocks_processed = self._current_performance_counters.get(
                "envelope_blocks_processed", 0
            )
            lfo_blocks_processed = self._current_performance_counters.get("lfo_blocks_processed", 0)
            filter_blocks_processed = self._current_performance_counters.get(
                "filter_blocks_processed", 0
            )
            wavetable_blocks_processed = self._current_performance_counters.get(
                "wavetable_blocks_processed", 0
            )
            partial_blocks_processed = self._current_performance_counters.get(
                "partial_blocks_processed", 0
            )
            channel_note_blocks_processed = self._current_performance_counters.get(
                "channel_note_blocks_processed", 0
            )

            self._log_comprehensive_performance_stats(
                self._current_time,
                midi_processing_time,
                envelope_processing_time,
                lfo_processing_time,
                filter_processing_time,
                wavetable_rendering_time,
                partial_generator_rendering_time,
                channel_notes_rendering_time,
                channels_rendering_time,
                effect_processing_time,
                midi_events_consumed,
                segments_processed,
                envelope_blocks_processed,
                lfo_blocks_processed,
                filter_blocks_processed,
                wavetable_blocks_processed,
                partial_blocks_processed,
                channel_note_blocks_processed,
            )

            return self.out_buffer

    def _generate_channel_audio_vectorized(self, block_size: int) -> list[np.ndarray]:
        """
        CORRECT XG INSERTION EFFECTS IMPLEMENTATION - Audio Quality Priority

        Generate audio for each individual MIDI channel separately.
        This is required for proper XG insertion effects processing where
        each channel needs to have insertion effects applied individually
        before mixing channels together.

        Uses XGBufferPool for buffer allocation and smart zeroing.

        Returns:
            List of channels, each containing stereo numpy array (block_size x 2)
        """
        # Process each MIDI channel individually for insertion effects
        for channel_idx in range(self.num_channels):
            channel_renderer = self.channel_renderers[channel_idx]
            if channel_renderer.is_active():
                try:
                    # Generate audio block for this specific channel
                    channel_left, channel_right = channel_renderer.generate_sample_block_vectorized(
                        block_size
                    )

                    # Apply volume and pan in-place
                    if self.master_volume < 1.0:
                        master_volume_factor = self.master_volume
                        np.multiply(channel_left, master_volume_factor, out=channel_left)
                        np.multiply(channel_right, master_volume_factor, out=channel_right)
                except Exception as e:
                    # Log error and generate silence to prevent audio dropouts
                    print(f"Warning: Channel {channel_idx} audio generation failed: {e}")
                    channel_left, channel_right = channel_renderer.generate_silence(block_size)
            else:
                # Inactive channel - get zero buffer from XGBufferPool
                channel_left, channel_right = channel_renderer.generate_silence(block_size)

            # Convert to stereo numpy array format expected by effect processor
            channel_stereo = np.column_stack((channel_left, channel_right))
            self.channel_buffers[channel_idx] = channel_stereo

        # Handle audio rendering logging based on level
        if self.render_log_level >= 1:
            self._log_channel_audio_rendering(block_size)

        return self.channel_buffers

    def rewind(self):
        """
        Reset playback position to the beginning for repeated playback.

        This method resets the message consumption index and current time to allow
        replaying the same sequence of messages from the start.
        """
        with self.lock:
            self._current_message_index = 0
            self._current_time = 0.0

    def set_current_time(self, time: float):
        """
        Set the current playback time.

        Args:
            time: The new playback time in seconds.
        """
        with self.lock:
            self._current_time = time

    def get_current_time(self) -> float:
        """
        Get the current playback time.

        Returns:
            The current playback time in seconds.
        """
        with self.lock:
            return self._current_time

    def finalize_audio_logging(self):
        """
        Finalize audio logging by closing all streams and updating WAV headers.

        This method should be called when MIDI rendering is complete to ensure
        all audio log files are properly finalized with correct headers.
        """
        with self.lock:
            self._finalize_audio_logging()

    def cleanup(self):
        """Complete cleanup of all synthesizer resources."""
        with self.lock:
            # Finalize audio logging first
            self._finalize_audio_logging()

            # Clean up channel renderers
            for renderer in self.channel_renderers:
                try:
                    if hasattr(renderer, "cleanup"):
                        renderer.cleanup()
                except:
                    pass

            # Return main audio buffers to XGBufferPool
            if hasattr(self, "out_buffer") and self.out_buffer is not None:
                self.memory_pool.return_stereo_buffer(self.out_buffer)
                self.out_buffer = None

            if hasattr(self, "temp_left") and self.temp_left is not None:
                self.memory_pool.return_mono_buffer(self.temp_left)
                self.temp_left = None

            if hasattr(self, "temp_right") and self.temp_right is not None:
                self.memory_pool.return_mono_buffer(self.temp_right)
                self.temp_right = None

            if hasattr(self, "effect_input") and self.effect_input is not None:
                self.memory_pool.return_stereo_buffer(self.effect_input)
                self.effect_input = None

            if hasattr(self, "effect_output") and self.effect_output is not None:
                self.memory_pool.return_stereo_buffer(self.effect_output)
                self.effect_output = None

            # Return channel buffers
            if hasattr(self, "channel_buffers"):
                for buffer in self.channel_buffers:
                    if buffer is not None:
                        self.memory_pool.return_stereo_buffer(buffer)
                self.channel_buffers.clear()

            # Clear references
            self.channel_renderers.clear()
            if hasattr(self, "_message_sequence"):
                self._message_sequence.clear()

    def reset(self):
        """Full synthesizer reset."""
        with self.lock:
            # Stop all active notes and cleanup buffers
            for renderer in self.channel_renderers:
                try:
                    renderer.all_sound_off()
                    if hasattr(renderer, "cleanup_buffers"):
                        renderer.cleanup_buffers()
                except:
                    pass

            # Reset channel renderers
            for renderer in self.channel_renderers:
                if hasattr(renderer, "reset"):
                    renderer.reset()

            # Reset drum manager
            self.drum_manager.reset_all_drum_parameters()

            # Reset effects coordinator to XG defaults
            if hasattr(self.effects_coordinator, "reset_all_effects"):
                self.effects_coordinator.reset_all_effects()

            # Reset message sequence and consumption state
            self._message_sequence.clear()
            self._current_message_index = 0
            self._current_time = 0.0

            # Reinitialize XG
            self._initialize_xg()

    def _log_comprehensive_performance_stats(
        self,
        total_time,
        midi_processing_time,
        envelope_processing_time,
        lfo_processing_time,
        filter_processing_time,
        wavetable_rendering_time,
        partial_generator_rendering_time,
        channel_notes_rendering_time,
        channels_rendering_time,
        effect_processing_time,
        midi_events_consumed,
        segments_processed,
        envelope_blocks_processed,
        lfo_blocks_processed,
        filter_blocks_processed,
        wavetable_blocks_processed,
        partial_blocks_processed,
        channel_note_blocks_processed,
    ):
        """Log comprehensive performance statistics to file after each audio block generation."""
        # Collect total statistics
        total_active_channels = sum(
            1 for renderer in self.channel_renderers if renderer.is_active()
        )
        total_active_channel_notes = sum(
            len(renderer.active_notes) for renderer in self.channel_renderers
        )
        total_active_partials = sum(
            sum(1 for partial in channel_note.partials if partial.is_active())
            for renderer in self.channel_renderers
            for channel_note in renderer.active_notes.values()
        )

        # Collect LFO statistics
        total_active_lfos = sum(
            len([lfo for lfo in renderer.lfos if hasattr(lfo, "is_active") and lfo.is_active()])
            for renderer in self.channel_renderers
        )

        # Collect resonant filter statistics
        total_active_filters = sum(
            sum(
                len(
                    [
                        partial
                        for partial in channel_note.partials
                        if hasattr(partial, "filter") and partial.filter is not None
                    ]
                )
                for channel_note in renderer.active_notes.values()
            )
            for renderer in self.channel_renderers
        )

        # Calculate RMS of rendered audio buffer
        if self.out_buffer is not None:
            # RMS calculation: sqrt(mean(x^2))
            rms_left = np.sqrt(np.mean(self.out_buffer[:, 0] ** 2))
            rms_right = np.sqrt(np.mean(self.out_buffer[:, 1] ** 2))
            rms_total = (rms_left + rms_right) / 2.0
        else:
            rms_total = 0.0

        # Collect system effects status
        system_effects_status = self._get_system_effects_status()

        # Collect insertion effects status
        insertion_effects = self._get_insertion_effects_status()

        # Collect per-channel details with MIDI settings
        per_channel_stats = []
        for channel_idx, renderer in enumerate(self.channel_renderers):
            if renderer.is_active():
                channel_notes = len(renderer.active_notes)
                channel_partials = sum(
                    len(channel_note.partials) for channel_note in renderer.active_notes.values()
                )

                # Get channel MIDI settings from channel renderer
                bank = getattr(renderer, "bank", 0)
                program = getattr(renderer, "program", 0)

                # Get SF2 preset name if available
                preset_name = self._get_sf2_preset_name(bank, program)

                # Get receive channel from XG receive channel manager
                receive_channel = self.receive_channel_manager.get_receive_channel(channel_idx)
                if receive_channel is None:
                    receive_channel = channel_idx  # Fallback to direct mapping
                part_mode = getattr(renderer, "part_mode", 0)  # Default to normal mode

                # Calculate per-channel RMS from the channel buffer used in mixing
                if self.channel_buffers[channel_idx] is not None:
                    channel_buffer = self.channel_buffers[channel_idx]
                    ch_rms_left = np.sqrt(np.mean(channel_buffer[:, 0] ** 2))
                    ch_rms_right = np.sqrt(np.mean(channel_buffer[:, 1] ** 2))
                    ch_rms = (ch_rms_left + ch_rms_right) / 2.0
                else:
                    ch_rms = 0.0

                per_channel_stats.append(
                    {
                        "channel": channel_idx,
                        "receive_channel": receive_channel,
                        "part_mode": part_mode,
                        "bank": bank,
                        "program": program,
                        "preset_name": preset_name,
                        "active_notes": channel_notes,
                        "active_partials": channel_partials,
                        "rms": ch_rms,
                    }
                )

        # Write comprehensive statistics to log file
        log_data = {
            "timestamp": time.time(),
            "current_time": total_time,
            "midi_processing_time": midi_processing_time,
            "envelope_processing_time": envelope_processing_time,
            "lfo_processing_time": lfo_processing_time,
            "filter_processing_time": filter_processing_time,
            "wavetable_rendering_time": wavetable_rendering_time,
            "partial_generator_rendering_time": partial_generator_rendering_time,
            "channel_notes_rendering_time": channel_notes_rendering_time,
            "channels_rendering_time": channels_rendering_time,
            "effect_processing_time": effect_processing_time,
            "total_active_channels": total_active_channels,
            "total_active_channel_notes": total_active_channel_notes,
            "total_active_partials": total_active_partials,
            "total_active_lfos": total_active_lfos,
            "total_active_filters": total_active_filters,
            "audio_output_rms": rms_total,
            "segments_processed": segments_processed,
            "midi_events_consumed": midi_events_consumed,
            "total_midi_events": sum(midi_events_consumed.values()),
            "system_effects": system_effects_status,
            "insertion_effects": insertion_effects,
            "blocks_processed": {
                "envelope": envelope_blocks_processed,
                "lfo": lfo_blocks_processed,
                "filter": filter_blocks_processed,
                "wavetable": wavetable_blocks_processed,
                "partial": partial_blocks_processed,
                "channel_note": channel_note_blocks_processed,
            },
            "per_channel_stats": per_channel_stats,
        }

        # Write to log file
        self._write_performance_log(log_data)

    def _get_system_effects_status(self):
        """Get status of system effects during block processing."""
        try:
            state = self.effects_coordinator.get_current_state()
            return {
                "reverb": "ON" if state.get("reverb_params", {}).get("level", 0) > 0 else "OFF",
                "chorus": "ON" if state.get("chorus_params", {}).get("level", 0) > 0 else "OFF",
                "variation": "ON"
                if state.get("variation_params", {}).get("level", 0) > 0
                else "OFF",
                "multi_eq": "ON"
                if any(
                    state.get("equalizer_params", {}).get(param, 0) != 0
                    for param in ["low_gain", "mid_gain", "high_gain"]
                )
                else "OFF",
            }
        except:
            return {"reverb": "UNK", "chorus": "UNK", "variation": "UNK", "multi_eq": "UNK"}

    def _get_insertion_effects_status(self):
        """Get status of insertion effects during block processing."""
        try:
            # Query effects coordinator for basic insertion effects state
            state = self.effects_coordinator.get_current_state()

            # Check if insertion effects are available in the coordinator
            if hasattr(self.effects_coordinator, "insertion_effects"):
                num_channels = len(self.effects_coordinator.insertion_effects)
                if num_channels > 0:
                    return f"{num_channels} channels available"
                else:
                    return "None"
            else:
                return "Not configured"

        except Exception as e:
            # Log error but don't crash the performance logging
            print(f"Warning: Failed to get insertion effects status: {e}")
            return "UNK"

    def _get_sf2_preset_name(self, bank: int, program: int) -> str:
        """Get the SF2 preset name for a given bank and program."""
        try:
            presets = self.sf2_manager.get_available_presets()
            for preset_bank, preset_program, preset_name in presets:
                if preset_bank == bank and preset_program == program:
                    return preset_name
            # If drum bank and no match found, try bank 0
            if bank == 128:
                for preset_bank, preset_program, preset_name in presets:
                    if preset_bank == 0 and preset_program == program:
                        return preset_name
            return "Unknown"
        except:
            return "Unknown"

    def _recreate_performance_log(self):
        """Recreate the performance log file upon class creation."""
        try:
            # Ensure log directory exists
            log_dir = os.path.join(os.path.dirname(sys.argv[0]), "logs")
            os.makedirs(log_dir, exist_ok=True)

            # Log file path
            log_file = os.path.join(log_dir, "performance.log")

            # Create/recreate the log file with a header
            header = f"{'=' * 80}\n"
            header += "XG SYNTHESIZER PERFORMANCE LOG - SESSION STARTED\n"
            header += f"{'=' * 80}\n"
            header += (
                f"Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}\n"
            )
            header += "Synthesizer: OptimizedXGSynthesizer\n"
            header += f"Sample Rate: {self.sample_rate} Hz\n"
            header += f"Block Size: {self.block_size} samples\n"
            header += f"Max Polyphony: {self.max_polyphony} voices\n"
            header += f"{'=' * 80}\n\n"

            # Write header to recreate the file
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(header)

        except Exception as e:
            # If log recreation fails, print to console as fallback
            print(f"Warning: Failed to recreate performance log: {e}")

    def _write_performance_log(self, log_data: dict[str, Any]):
        """Write performance statistics to a log file."""
        try:
            # Ensure log directory exists
            log_dir = os.path.join(os.path.dirname(sys.argv[0]), "logs")
            os.makedirs(log_dir, exist_ok=True)

            # Log file path
            log_file = os.path.join(log_dir, "performance.log")

            # Format the log entry
            timestamp = log_data["timestamp"]
            current_time = log_data["current_time"]

            # Build the log entry
            log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}] Performance Report:\n"
            log_entry += f"  Current Time: {current_time * 1000:.3f}ms\n"
            log_entry += f"  Active Resources: channels={log_data['total_active_channels']}, notes={log_data['total_active_channel_notes']}, partials={log_data['total_active_partials']}, LFOs={log_data['total_active_lfos']}, filters={log_data['total_active_filters']}\n"
            log_entry += f"  System Effects: reverb={log_data['system_effects']['reverb']}, chorus={log_data['system_effects']['chorus']}, variation={log_data['system_effects']['variation']}, multi_eq={log_data['system_effects']['multi_eq']}\n"
            log_entry += f"  Insertion Effects: {log_data['insertion_effects']}\n"
            log_entry += f"  MIDI Events: total={log_data['total_midi_events']}, segments={log_data['segments_processed']}\n"
            log_entry += f"  Audio Output RMS: {log_data['audio_output_rms']:.6f}\n"

            # Processing times
            log_entry += "  Processing Times (ms):\n"
            times = log_data["blocks_processed"]
            log_entry += f"    MIDI: {log_data['midi_processing_time'] * 1000:.3f}, Envelope: {log_data['envelope_processing_time'] * 1000:.3f} ({times['envelope']} blocks), LFO: {log_data['lfo_processing_time'] * 1000:.3f} ({times['lfo']} blocks)\n"
            log_entry += f"    Filter: {log_data['filter_processing_time'] * 1000:.3f} ({times['filter']} blocks), Wavetable: {log_data['wavetable_rendering_time'] * 1000:.3f} ({times['wavetable']} blocks), Partials: {log_data['partial_generator_rendering_time'] * 1000:.3f} ({times['partial']} blocks)\n"
            log_entry += f"    Channel Notes: {log_data['channel_notes_rendering_time'] * 1000:.3f} ({times['channel_note']} blocks), Channels: {log_data['channels_rendering_time'] * 1000:.3f}, Effects: {log_data['effect_processing_time'] * 1000:.3f}\n"

            # Per-channel statistics
            log_entry += "  Per-Channel Statistics:\n"
            for stat in log_data["per_channel_stats"]:
                log_entry += f"    Ch{stat['channel']:2d} (RX:{stat['receive_channel']:2d}, Mode:{stat['part_mode']:1d}, Bank:{stat['bank']:3d}, Prog:{stat['program']:3d}, Preset:{stat['preset_name'][:12]:12}): notes={stat['active_notes']:2d}, partials={stat['active_partials']:2d}, RMS={stat['rms']:.6f}\n"

            log_entry += "\n"

            # Write to file (append mode)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

        except Exception as e:
            # If logging fails, print to console as fallback
            print(f"Warning: Failed to write performance log: {e}")

    def _initialize_audio_writers(self):
        """Initialize audio writers for debugging pipeline based on render log level."""
        # Create audio writer instance
        self.audio_writer = AudioWriter(self.sample_rate, chunk_size_ms=100.0)

        # Initialize audio writers for different logging levels
        self.audio_writers = {}

        # Level 1: Dry stereo output before effects processing
        if self.render_log_level >= 1:
            self.audio_writers[1] = self.audio_writer.create_writer(
                os.path.join("render_logs", "level1_dry_output.wav"), "wav"
            ).__enter__()

        # Level 2: Output of each active channel renderer
        if self.render_log_level >= 2:
            for channel_idx in range(self.num_channels):
                self.audio_writers[f"channel_{channel_idx}"] = self.audio_writer.create_writer(
                    os.path.join("render_logs", f"level2_channel_{channel_idx}.wav"), "wav"
                ).__enter__()

        # Level 3: Output of each active channel note
        if self.render_log_level >= 3:
            # Note writers will be created dynamically as notes become active
            self.note_writers = {}

        # Initialize accumulation buffers for continuous logging
        self.dry_output_accumulator = []
        self.channel_accumulators = {f"channel_{i}": [] for i in range(self.num_channels)}
        self.note_accumulators = {}

    def _log_channel_audio_rendering(self, block_size: int):
        """Log channel audio rendering based on the configured log level."""
        if self.render_log_level == 0 or not hasattr(self, "audio_writers"):
            return

        # Level 1: Dry stereo output before effects processing
        if self.render_log_level >= 1 and 1 in self.audio_writers:
            # Accumulate dry channel outputs (before effects)
            dry_mix = np.zeros((block_size, 2), dtype=np.float32)
            for channel_idx in range(self.num_channels):
                if self.channel_buffers[channel_idx] is not None:
                    # Use only the first block_size samples since channel_buffers may be larger
                    np.add(dry_mix, self.channel_buffers[channel_idx][:block_size], out=dry_mix)

            # Write accumulated dry output
            self.audio_writers[1].write(dry_mix)

        # Level 2: Output of each active channel renderer
        if self.render_log_level >= 2:
            for channel_idx in range(self.num_channels):
                writer_key = f"channel_{channel_idx}"
                if (
                    writer_key in self.audio_writers
                    and self.channel_buffers[channel_idx] is not None
                ):
                    # Write only the first block_size samples of individual channel output
                    self.audio_writers[writer_key].write(
                        self.channel_buffers[channel_idx][:block_size]
                    )

        # Level 3: Output of each active channel note
        if self.render_log_level >= 3:
            for channel_idx, renderer in enumerate(self.channel_renderers):
                if renderer.is_active():
                    for note_num, channel_note in renderer.active_notes.items():
                        writer_key = f"channel_{channel_idx}_note_{note_num}"

                        # Create writer if it doesn't exist
                        if writer_key not in self.audio_writers:
                            self.audio_writers[writer_key] = self.audio_writer.create_writer(
                                os.path.join(
                                    "render_logs",
                                    f"level3_channel_{channel_idx}_note_{note_num}.wav",
                                ),
                                "wav",
                            ).__enter__()

                        # Generate note audio and write it
                        if hasattr(channel_note, "generate_sample_block"):
                            # Get appropriately sized buffers for this block
                            if block_size == self.block_size:
                                # Use XGBufferPool buffers for standard size
                                note_left = self.memory_pool.get_mono_buffer(block_size)
                                note_right = self.memory_pool.get_mono_buffer(block_size)
                            else:
                                # Get variable-sized buffers for smaller blocks
                                note_left = self.memory_pool.get_mono_buffer(block_size)
                                note_right = self.memory_pool.get_mono_buffer(block_size)

                            try:
                                channel_note.generate_sample_block(
                                    block_size,
                                    note_left,
                                    note_right,
                                    mod_wheel=renderer.controllers[1]
                                    if 1 in renderer.controllers
                                    else 0,
                                    breath_controller=renderer.controllers[2]
                                    if 2 in renderer.controllers
                                    else 0,
                                    foot_controller=renderer.controllers[4]
                                    if 4 in renderer.controllers
                                    else 0,
                                    brightness=renderer.controllers[72]
                                    if 72 in renderer.controllers
                                    else 64,
                                    harmonic_content=renderer.controllers[71]
                                    if 71 in renderer.controllers
                                    else 64,
                                    channel_pressure_value=renderer.channel_pressure_value,
                                    key_pressure=renderer.key_pressure_values.get(note_num, 0),
                                    volume=renderer.volume,
                                    expression=renderer.expression,
                                    global_pitch_mod=0.0,
                                )

                                # Combine into stereo and write
                                note_stereo = np.column_stack((note_left, note_right))
                                self.audio_writers[writer_key].write(note_stereo)

                            finally:
                                # Return buffers to XGBufferPool - updated to use new API
                                self.memory_pool.return_mono_buffer(note_left)
                                self.memory_pool.return_mono_buffer(note_right)

    def _finalize_audio_logging(self):
        """Finalize and close all audio logging streams."""
        # Close all audio writers
        if hasattr(self, "audio_writers") and self.audio_writers:
            for writer in self.audio_writers.values():
                try:
                    if hasattr(writer, "__exit__"):
                        writer.__exit__(None, None, None)
                except:
                    pass

        # Clear writer references
        if hasattr(self, "audio_writers"):
            self.audio_writers.clear()
        if hasattr(self, "note_writers"):
            self.note_writers.clear()

        # Clear accumulators
        if hasattr(self, "dry_output_accumulator"):
            self.dry_output_accumulator.clear()
        if hasattr(self, "channel_accumulators"):
            self.channel_accumulators.clear()
        if hasattr(self, "note_accumulators"):
            self.note_accumulators.clear()

    def __del__(self):
        """Cleanup when OptimizedXGSynthesizer is destroyed."""
        self.cleanup()
