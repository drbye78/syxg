"""
HIGH-PERFORMANCE XG CHANNEL RENDERER

This module provides a vectorized channel renderer implementation with
NumPy-based operations for high-performance audio synthesis.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import math

# Import internal modules
from ..core.constants import DEFAULT_CONFIG
from ..engine.optimized_coefficient_manager import get_global_coefficient_manager
from ..core.oscillator import XGLFO  # XG-compliant LFO
from ..modulation.vectorized_matrix import VectorizedModulationMatrix
from .partial_generator import XGPartialGenerator
from ..voice.voice_manager import VoiceManager
from ..voice.voice_priority import VoicePriority
from .channel_note import ChannelNote


class VectorizedChannelRenderer:
    """
    HIGH-PERFORMANCE XG CHANNEL RENDERER

    Renders audio for individual MIDI channels with optimized NumPy operations.

    Key Features:
    - Vectorized audio processing using NumPy operations for maximum performance
    - Batch note processing for multiple simultaneous voices
    - Pre-allocated audio buffers for zero-allocation rendering
    - Comprehensive XG controller and parameter support
    - Real-time modulation matrix processing with vectorized operations
    - Efficient voice allocation and management
    - XG-compliant LFO implementation for vibrato and modulation effects

    Architecture:
    - NumPy-based vectorized operations for mathematical computations
    - Pre-allocated buffer management to eliminate allocation overhead
    - Batch processing of multiple audio voices simultaneously
    - Real-time XG parameter processing and modulation routing
    - Thread-safe parameter updates for real-time performance
    """

    # XG Voice Allocation Modes (Complete Implementation)
    VOICE_MODE_POLY = 0  # Standard polyphonic mode (XG default)
    VOICE_MODE_MONO = 1  # Basic monophonic mode
    VOICE_MODE_POLY_DRUM = 2  # Poly with drum priority
    VOICE_MODE_MONO_LEGATO = 3  # Monophonic with legato (note overlapping)
    VOICE_MODE_MONO_PORTAMENTO = 4  # Monophonic with portamento (glide)

    def __init__(self, channel: int, synth):
        """
        Initialize vectorized channel renderer owned by OptimizedXGSynthesizer.

        Args:
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate
            max_voices: Maximum number of voices for this channel
            drum_manager: Drum manager for drum parameter handling (owned by synthesizer)
            memory_pool: Memory pool for buffer allocation (owned by synthesizer)
        """
        self.channel = channel
        self.synth = synth
        self.sample_rate = synth.sample_rate
        self.drum_manager = synth.drum_manager
        self.memory_pool = synth.memory_pool  # Reference to synthesizer's memory pool
        self.active = True

        # Channel state with pre-initialized values
        self.program = 0
        self.bank = 0
        self.is_drum = False  # Default to melodic mode

        # XG voice management system with enhanced mono/poly support
        self.voice_manager = VoiceManager(synth.max_polyphony)
        self.polyphony_limit = synth.max_polyphony

        # XG Voice Allocation Mode
        self.voice_mode = self.VOICE_MODE_POLY  # Default to standard polyphonic (XG)
        self.mono_legato = False  # XG mono legato mode
        self.mono_portamento = False  # XG mono portamento mode

        # Active notes on this channel with optimized data structure
        self.active_notes: Dict[int, "ChannelNote"] = {}  # note -> ChannelNote

        # Controller state with CORRECTED default values
        self.controllers = [0] * 128
        self.controllers[7] = 110  # Volume - higher default
        self.controllers[11] = 127  # Expression - full by default
        self.controllers[64] = 0  # Sustain Pedal
        self.controllers[71] = 64  # Harmonic Content default

        # Bank select state for XG bank selection
        self.bank_msb = 0  # Bank Select MSB (CC 0)
        self.bank_lsb = 0  # Bank Select LSB (CC 32)
        self.controllers[72] = 64  # Brightness default

        # Cached controller values for performance
        self._cached_volume = 1.0
        self._cached_pan = 0.0
        self._last_volume = self.controllers[7]
        self._last_expression = self.controllers[11]

        # Channel pressure (aftertouch)
        self.channel_pressure_value = 0

        # Key pressure (polyphonic aftertouch)
        self.key_pressure_values = {}  # note -> pressure

        # Pitch bend state
        self.pitch_bend_value = 8192  # Center value for 14-bit pitch bend
        self.pitch_bend_range = 2  # Default 2 semitones

        # Portamento state
        self.portamento_active = False
        self.portamento_target_freq = 0.0
        self.portamento_current_freq = 0.0
        self.portamento_step = 0.0
        self.previous_note = None

        # Channel parameters with CORRECTED default values
        self.volume = 110  # Higher default volume (87% of MIDI range)
        self.expression = 127  # Full expression by default
        self.pan = 64  # Center pan
        self.balance = 64

        # Initialize XG-compliant channel LFOs per XG specification
        self.lfos = [
            self.synth.lfo_pool.acquire_oscillator(
                id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0
            ),
            self.synth.lfo_pool.acquire_oscillator(
                id=1, waveform="triangle", rate=2.0, depth=0.3, delay=0.0
            ),
            self.synth.lfo_pool.acquire_oscillator(
                id=2, waveform="sawtooth", rate=0.5, depth=0.1, delay=0.5
            ),
        ]

        # Set XG modulation routing for channel LFOs
        # LFO1: Pitch modulation (vibrato) - XG default
        self.lfos[0].set_modulation_routing(pitch=True, filter=False, amplitude=False)
        self.lfos[0].set_modulation_depths(
            pitch_cents=50.0, filter_depth=0.0, amplitude_depth=0.0
        )

        # LFO2: Filter modulation - optional
        self.lfos[1].set_modulation_routing(pitch=False, filter=True, amplitude=False)
        self.lfos[1].set_modulation_depths(
            pitch_cents=0.0, filter_depth=0.3, amplitude_depth=0.0
        )

        # LFO3: Amplitude modulation (tremolo) - optional
        self.lfos[2].set_modulation_routing(pitch=False, filter=False, amplitude=True)
        self.lfos[2].set_modulation_depths(
            pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3
        )

        # XG LFO modulation state for channel-wide modulation
        self.lfo_pitch_modulation = 0.0
        self.lfo_tremolo_modulation = 0.0

        # Initialize vectorized modulation matrix with pre-allocated buffers
        self.mod_matrix = VectorizedModulationMatrix(num_routes=16)
        # Setup modulation matrix after all components are initialized
        self._setup_default_modulation_matrix()

        # Optimized coefficient manager for performance
        self.coeff_manager = get_global_coefficient_manager()

        # Get stereo buffers from synthesizer's memory pool (will be zeroed)
        self.left_buffer = self.memory_pool.get_mono_buffer(zero_buffer=True)
        self.right_buffer = self.memory_pool.get_mono_buffer(zero_buffer=True)

        # Temporary buffers for intermediate processing
        self.temp_left = self.memory_pool.get_mono_buffer(zero_buffer=True)
        self.temp_right = self.memory_pool.get_mono_buffer(zero_buffer=True)
        self.note_left = self.memory_pool.get_mono_buffer(zero_buffer=True)
        self.note_right = self.memory_pool.get_mono_buffer(zero_buffer=True)

        # Cached parameter values for performance
        self.cached_mod_wheel = 0
        self.cached_breath_controller = 0
        self.cached_foot_controller = 0
        self.cached_brightness = 64
        self.cached_harmonic_content = 64
        self.cached_channel_pressure = 0

        # XG Controller batching system for performance optimization
        self.pending_controller_updates = {}  # controller -> value
        self.controller_update_batch = {}  # Batched updates by parameter type
        self.last_controller_update_time = 0
        self.controller_update_threshold = 10  # Process batch every 10 updates

    def _setup_xg_modulation_matrix(self):
        """Setup XG-standard default modulation matrix routes per XG specification."""
        # Clear existing routes efficiently
        for i in range(16):
            self.mod_matrix.clear_route(i)

        # XG MODULATION MATRIX - FULLY ENABLED
        # Setup comprehensive XG modulation routes

        # LFO1 -> Pitch (Vibrato) - normalized amounts
        self.mod_matrix.set_route(
            0,
            "lfo1",
            "pitch",
            amount=50.0 / 100.0,  # 50 cents
            polarity=1.0,
        )

        # LFO2 -> Pitch (additional modulation)
        self.mod_matrix.set_route(
            1,
            "lfo2",
            "pitch",
            amount=30.0 / 100.0,  # 30 cents
            polarity=1.0,
        )

        # LFO3 -> Pitch (subtle modulation)
        self.mod_matrix.set_route(
            2,
            "lfo3",
            "pitch",
            amount=10.0 / 100.0,  # 10 cents
            polarity=1.0,
        )

        # Amp Envelope -> Filter Cutoff
        self.mod_matrix.set_route(
            3, "amp_env", "filter_cutoff", amount=0.5, polarity=1.0
        )

        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(4, "lfo1", "filter_cutoff", amount=0.3, polarity=1.0)

        # Velocity -> Amplitude
        self.mod_matrix.set_route(
            5, "velocity", "amp", amount=0.5, velocity_sensitivity=0.5
        )

        # Note Number -> Pitch (basic pitch mapping)
        self.mod_matrix.set_route(
            6, "note_number", "pitch", amount=1.0, key_scaling=1.0
        )

        # Mod Wheel -> LFO1 Depth (vibrato control)
        self.mod_matrix.set_route(
            7, "mod_wheel", "lfo1_depth", amount=1.0, polarity=1.0
        )

        # Breath Controller -> LFO1 Depth
        self.mod_matrix.set_route(
            8, "breath_controller", "lfo1_depth", amount=0.8, polarity=1.0
        )

        # Foot Controller -> Filter Cutoff
        self.mod_matrix.set_route(
            9, "foot_controller", "filter_cutoff", amount=0.5, polarity=1.0
        )

        # Channel Aftertouch -> LFO1 Depth
        self.mod_matrix.set_route(
            10, "channel_aftertouch", "lfo1_depth", amount=0.6, polarity=1.0
        )

        # Key Aftertouch -> Filter Resonance
        self.mod_matrix.set_route(
            11, "key_aftertouch", "filter_resonance", amount=0.4, polarity=1.0
        )

        # Brightness -> Filter Cutoff (XG controller 72)
        self.mod_matrix.set_route(
            12, "brightness", "filter_cutoff", amount=0.7, polarity=1.0
        )

        # Harmonic Content -> Filter Resonance (XG controller 71)
        self.mod_matrix.set_route(
            13, "harmonic_content", "filter_resonance", amount=0.5, polarity=1.0
        )

        # Expression -> Amplitude
        self.mod_matrix.set_route(14, "expression", "amp", amount=0.8, polarity=1.0)

        # Volume -> Amplitude
        self.mod_matrix.set_route(15, "volume_cc", "amp", amount=0.9, polarity=1.0)

    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix - calls XG-compliant implementation."""
        self._setup_xg_modulation_matrix()

    def get_channel_state(self) -> Dict[str, Any]:
        """Get the current channel state for note generation with optimized access."""
        return {
            "program": self.program,
            "bank": self.bank,
            "bank_msb": self.bank_msb,
            "bank_lsb": self.bank_lsb,
            "volume": self.volume,
            "expression": self.expression,
            "pan": self.pan,
            "reverb_send": self.controllers[91] or 40,
            "chorus_send": self.controllers[93] or 0,
            "variation_send": self.controllers[94] or 0,
            "controllers": self.controllers,
            "channel_pressure_value": self.channel_pressure_value,
            "key_pressure": self.key_pressure_values,
            "pitch_bend_value": self.pitch_bend_value,
            "pitch_bend_range": self.pitch_bend_range,
            "portamento_active": self.portamento_active,
        }

    def note_on(self, note: int, velocity: int):
        """Handle Note On message for this channel with optimized note creation."""
        # If velocity is 0, treat as Note Off
        if velocity == 0:
            self.note_off(note, 0)
            return

        # Determine voice priority based on velocity with optimized calculation
        if velocity >= 100:
            priority = VoicePriority.HIGH
        elif velocity >= 64:
            priority = VoicePriority.NORMAL
        else:
            priority = VoicePriority.LOW

        # Check if we can allocate a voice with optimized check
        if not self.voice_manager.can_allocate_voice(note, velocity, priority):
            return

        # Create new note with proper ChannelNote object
        channel_note = ChannelNote(
            self,
            note=note,
            velocity=velocity,
            program=self.program,
            bank=self.bank,
            is_drum=self.is_drum,
            synth=self.synth,
        )

        if channel_note.is_active():
            # Allocate voice through voice manager with optimized allocation
            allocated_note = self.voice_manager.allocate_voice(
                note, velocity, channel_note, priority
            )
            if allocated_note is not None:
                self.active_notes[note] = channel_note

        # Store this note as the previous note for potential portamento
        self.previous_note = note

    def note_off(self, note: int, velocity: int):
        """Handle Note Off message for this channel with optimized note termination."""
        if note in self.active_notes:
            # Start release phase for the note with optimized termination
            self.active_notes[note].note_off()
            # Mark voice for release in voice manager with optimized marking
            self.voice_manager.start_voice_release(note)

            # Check if note should be cleaned up immediately (no sustain pedal)
            sustain_pedal = self.controllers[64] >= 64
            if not sustain_pedal:
                # Note is released, return partials to pool
                channel_note = self.active_notes[note]
                if hasattr(channel_note, "cleanup"):
                    channel_note.cleanup()
                # Remove from active notes
                del self.active_notes[note]

    def control_change(self, controller: int, value: int):
        """Handle Control Change message for this channel with optimized batching."""
        self.controllers[controller] = value

        # Add to pending updates for batched processing
        self.pending_controller_updates[controller] = value

        # Check if we should process the batch
        current_time = len(self.pending_controller_updates)
        if (
            current_time - self.last_controller_update_time
            >= self.controller_update_threshold
        ):
            self._process_controller_batch()

        # Handle specific controllers with optimized parameter updates
        if controller == 0:  # Bank Select MSB (XG)
            # XG Bank Select MSB - sets most significant byte of bank number
            self.bank_msb = value
            # Update combined bank value for XG compatibility
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 32:  # Bank Select LSB (XG)
            # XG Bank Select LSB - sets least significant byte of bank number
            self.bank_lsb = value
            # Update combined bank value for XG compatibility
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 7:  # Volume
            self.volume = value
        elif controller == 11:  # Expression
            self.expression = value
        elif controller == 10:  # Pan
            self.pan = value
        elif controller == 8:  # Balance
            self.balance = value
        elif controller == 71:  # Harmonic Content (XG Sound Controller 1)
            # XG-specific: Affects harmonic content/timbre with optimized parameter update
            self._handle_xg_harmonic_content(value)
        elif controller == 72:  # Brightness (XG Sound Controller 2)
            # XG-specific: Affects filter cutoff/brightness with optimized parameter update
            self._handle_xg_brightness(value)
        elif controller == 73:  # Sound Controller 3 (XG: Release Time)
            # XG-specific: Affects envelope release time with optimized parameter update
            self._handle_xg_release_time(value)
        elif controller == 74:  # Sound Controller 4 (XG: Attack Time)
            # XG-specific: Affects envelope attack time with optimized parameter update
            self._handle_xg_attack_time(value)
        elif controller == 75:  # Sound Controller 5 (XG: Filter Cutoff)
            # XG-specific: Affects filter cutoff frequency with optimized parameter update
            self._handle_xg_filter_cutoff(value)
        elif controller == 76:  # Sound Controller 6 (XG: Decay Time)
            # XG-specific: Affects envelope decay time with optimized parameter update
            self._handle_xg_decay_time(value)
        elif controller == 77:  # Sound Controller 7 (XG: Vibrato Rate)
            # XG-specific: Affects LFO vibrato rate with optimized parameter update
            self._handle_xg_vibrato_rate(value)
        elif controller == 78:  # Sound Controller 8 (XG: Vibrato Depth)
            # XG-specific: Affects LFO vibrato depth with optimized parameter update
            self._handle_xg_vibrato_depth(value)
        elif controller == 79:  # Sound Controller 9 (XG: Vibrato Delay)
            # XG-specific: Affects LFO vibrato delay with optimized parameter update
            self._handle_xg_vibrato_delay(value)
        elif controller == 91:  # Reverb Send (XG Effects Send 1)
            # XG-specific: Reverb send level - handled by effect manager
            pass
        elif controller == 92:  # Effects Send 2 (XG: Tremolo Send)
            # XG-specific: Tremolo send level - handled by effect manager
            pass
        elif controller == 93:  # Chorus Send (XG Effects Send 3)
            # XG-specific: Chorus send level - handled by effect manager
            pass
        elif controller == 94:  # Effects Send 4 (XG: Variation Send)
            # XG-specific: Variation send level - handled by effect manager
            pass
        elif controller == 95:  # Effects Send 5 (XG: Delay Send)
            # XG-specific: Delay send level - handled by effect manager
            pass
        elif controller == 80:  # General Purpose Button 1 (XG)
            # XG-specific: General purpose button 1 with optimized parameter update
            self._handle_xg_gp_button(1, value)
        elif controller == 81:  # General Purpose Button 2 (XG)
            # XG-specific: General purpose button 2 with optimized parameter update
            self._handle_xg_gp_button(2, value)
        elif controller == 82:  # General Purpose Button 3 (XG)
            # XG-specific: General purpose button 3 with optimized parameter update
            self._handle_xg_gp_button(3, value)
        elif controller == 83:  # General Purpose Button 4 (XG)
            # XG-specific: General purpose button 4 with optimized parameter update
            self._handle_xg_gp_button(4, value)
        elif controller == 66:  # Sostenuto Pedal (XG)
            # XG-specific: Sostenuto pedal - holds notes that are already playing
            self._handle_sostenuto_pedal(value)
        elif controller == 67:  # Soft Pedal (XG)
            # XG-specific: Soft pedal - reduces volume/velocity
            self._handle_soft_pedal(value)
        elif controller == 68:  # Legato Foot Switch (XG)
            # XG-specific: Legato foot switch - forces legato playing mode
            self._handle_legato_foot_switch(value)

    def _process_controller_batch(self):
        """Process batched controller updates for improved performance"""
        if not self.pending_controller_updates:
            return

        # Group updates by parameter type for efficient processing
        filter_controllers = {}
        envelope_controllers = {}
        lfo_controllers = {}

        for controller, value in self.pending_controller_updates.items():
            if controller in [71, 72, 75]:  # Filter controllers
                filter_controllers[controller] = value
            elif controller in [73, 74, 76]:  # Envelope controllers
                envelope_controllers[controller] = value
            elif controller in [77, 78, 79]:  # LFO controllers
                lfo_controllers[controller] = value

        # Apply batched updates
        if filter_controllers:
            self._apply_batched_filter_updates(filter_controllers)
        if envelope_controllers:
            self._apply_batched_envelope_updates(envelope_controllers)
        if lfo_controllers:
            self._apply_batched_lfo_updates(lfo_controllers)

        # Clear pending updates
        self.pending_controller_updates.clear()
        self.last_controller_update_time = len(self.pending_controller_updates)

    def _apply_batched_filter_updates(self, filter_updates: Dict[int, int]):
        """Apply multiple filter controller updates in batch"""
        # Process harmonic content updates
        if 71 in filter_updates:
            self._handle_xg_harmonic_content(filter_updates[71])

        # Process brightness updates
        if 72 in filter_updates:
            self._handle_xg_brightness(filter_updates[72])

        # Process filter cutoff updates
        if 75 in filter_updates:
            self._handle_xg_filter_cutoff(filter_updates[75])

    def _apply_batched_envelope_updates(self, envelope_updates: Dict[int, int]):
        """Apply multiple envelope controller updates in batch"""
        # Process release time updates
        if 73 in envelope_updates:
            self._handle_xg_release_time(envelope_updates[73])

        # Process attack time updates
        if 74 in envelope_updates:
            self._handle_xg_attack_time(envelope_updates[74])

        # Process decay time updates
        if 76 in envelope_updates:
            self._handle_xg_decay_time(envelope_updates[76])

    def _apply_batched_lfo_updates(self, lfo_updates: Dict[int, int]):
        """Apply multiple LFO controller updates in batch"""
        # Process vibrato rate updates
        if 77 in lfo_updates:
            self._handle_xg_vibrato_rate(lfo_updates[77])

        # Process vibrato depth updates
        if 78 in lfo_updates:
            self._handle_xg_vibrato_depth(lfo_updates[78])

        # Process vibrato delay updates
        if 79 in lfo_updates:
            self._handle_xg_vibrato_delay(lfo_updates[79])

    def pitch_bend(self, lsb: int, msb: int):
        """Handle Pitch Bend message with optimized parameter update."""
        # 14-bit pitch bend value with optimized calculation
        self.pitch_bend_value = (msb << 7) | lsb

    def set_channel_pressure(self, pressure: int):
        """Set channel pressure (aftertouch) for this channel."""
        self.channel_pressure_value = pressure

    def set_key_pressure(self, note: int, pressure: int):
        """Set key pressure (polyphonic aftertouch) for a specific note."""
        self.key_pressure_values[note] = pressure

    def set_pitch_bend(self, value: int):
        """Set pitch bend value for this channel."""
        self.pitch_bend_value = value

    def program_change(self, program: int):
        """Handle Program Change message for this channel with XG bank selection support."""
        self.program = program

        # XG Bank Selection Logic:
        # - Bank MSB 0, LSB 0: Normal melodic sounds (default)
        # - Bank MSB 127, LSB 0: SFX sounds
        # - Bank MSB 126, LSB 0: Drum kits (automatically set for channel 9)
        # - Bank MSB 64, LSB 0: XG additional sounds
        # - Other banks: Ignored per XG specification (maintain previous drum/melodic mode)

        # Determine if this is a drum channel (channel 9/MIDI channel 10)
        is_drum_channel = self.is_drum

        # XG Bank Mapping Logic - Only change mode for defined XG banks
        combined_bank = (self.bank_msb << 7) | self.bank_lsb

        if combined_bank == 0:  # Bank 0: Normal melodic sounds
            self.is_drum = False
        elif combined_bank == 16256:  # Bank MSB 127 (127<<7 = 16256): SFX sounds
            self.is_drum = False
            # SFX programs are typically in higher program numbers
        elif combined_bank == 16128:  # Bank MSB 126 (126<<7 = 16128): Drum kits
            self.is_drum = True
        elif combined_bank == 8192:  # Bank MSB 64 (64<<7 = 8192): XG additional sounds
            self.is_drum = False
        else:
            # XG Specification: Undefined banks are COMPLETELY IGNORED
            # Do not change the current drum/melodic mode - maintain previous setting
            # This is the correct XG behavior: undefined banks have no effect
            pass

    def all_notes_off(self):
        """Turn off all active notes with optimized batch termination."""
        for note in self.active_notes.values():
            note.note_off()
        self.active_notes.clear()

    def all_sound_off(self):
        """Immediately silence all notes with optimized batch termination."""
        # Clean up all notes to release LFOs and other resources before clearing
        for note, channel_note in list(self.active_notes.items()):
            if hasattr(channel_note, "cleanup"):
                channel_note.cleanup()
        self.active_notes.clear()

    def cleanup_buffers(self):
        """Return all buffers to memory pool for proper cleanup."""
        if self.memory_pool:
            try:
                # Return main buffers to pool
                if hasattr(self, "left_buffer"):
                    self.memory_pool.return_mono_buffer(self.left_buffer)
                if hasattr(self, "right_buffer"):
                    self.memory_pool.return_mono_buffer(self.right_buffer)
                if hasattr(self, "temp_left"):
                    self.memory_pool.return_mono_buffer(self.temp_left)
                if hasattr(self, "temp_right"):
                    self.memory_pool.return_mono_buffer(self.temp_right)
                if hasattr(self, "note_left"):
                    self.memory_pool.return_mono_buffer(self.note_left)
                if hasattr(self, "note_right"):
                    self.memory_pool.return_mono_buffer(self.note_right)
            except:
                # Ignore cleanup errors
                pass

    def cleanup(self):
        """Complete cleanup of all resources."""
        # Clean up active notes
        for note, channel_note in list(self.active_notes.items()):
            if hasattr(channel_note, "cleanup"):
                channel_note.cleanup()  # type: ignore
            del self.active_notes[note]

        # Return LFOs to pool
        for lfo in self.lfos:
            if hasattr(self.synth, "lfo_pool"):
                self.synth.lfo_pool.release_oscillator(lfo)

        # Clean up buffers
        self.cleanup_buffers()

        # Clear references
        self.lfos.clear()
        self.active_notes.clear()

    def __del__(self):
        """Cleanup when VectorizedChannelRenderer is destroyed."""
        self.cleanup()

    def reset(self):
        """Reset channel renderer and return buffers to pool."""
        # Stop all notes
        self.all_sound_off()

        # Return buffers to memory pool
        self.cleanup_buffers()

        # Reset channel state
        self.controllers = [0] * 128
        self.controllers[7] = 100  # Volume
        self.controllers[11] = 127  # Expression
        self.controllers[64] = 0  # Sustain Pedal
        self.controllers[71] = 64  # Harmonic Content default

        # Reset bank select state to XG defaults
        self.bank_msb = 0
        self.bank_lsb = 0
        self.bank = 0  # Combined bank value
        self.controllers[72] = 64  # Brightness default

        # Reset cached values
        self._cached_volume = 1.0
        self._cached_pan = 0.0
        self._last_volume = self.controllers[7]
        self._last_expression = self.controllers[11]

    def _handle_xg_gp_button(self, button_number: int, value: int):
        """Handle XG General Purpose Button controllers (80-83) with optimized parameter updates."""
        # Store the button state
        self.controllers[79 + button_number] = value

        # XG GP buttons can be used for various specific purposes with optimized updates
        if button_number == 1:  # GP Button 1
            # Typically used for filter type switching or effect bypass
            if value >= 64:  # Button pressed
                # Toggle filter type or enable/disable filter with optimized update
                self._toggle_filter_type()
            else:  # Button released
                # Could reset to default filter settings with optimized update
                pass

        elif button_number == 2:  # GP Button 2
            # Typically used for effect bypass/enable
            if value >= 64:  # Button pressed
                # Toggle effect bypass state with optimized update
                self._toggle_effect_bypass()
            else:  # Button released
                # Could reset effect parameters with optimized update
                pass

        elif button_number == 3:  # GP Button 3
            # Typically used for modulation source selection
            if value >= 64:  # Button pressed
                # Cycle through modulation sources with optimized update
                self._cycle_modulation_source()
            else:  # Button released
                # Could reset modulation to default with optimized update
                pass

        elif button_number == 4:  # GP Button 4
            # Typically used for performance parameter control
            if value >= 64:  # Button pressed
                # Apply performance preset or toggle performance mode with optimized update
                self._apply_performance_preset()
            else:  # Button released
                # Could reset to normal performance parameters with optimized update
                pass

    def _toggle_filter_type(self):
        """Toggle between different filter types with optimized parameter updates."""
        # Cycle through filter types: lowpass -> bandpass -> highpass -> lowpass
        filter_types = ["lowpass", "bandpass", "highpass"]
        current_type = getattr(self, "_current_filter_type", "lowpass")
        next_type_index = (filter_types.index(current_type) + 1) % len(filter_types)
        new_filter_type = filter_types[next_type_index]
        self._current_filter_type = new_filter_type

        # Apply to all active notes - modify filter type parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    partial.filter_type = new_filter_type

    def _toggle_effect_bypass(self):
        """Toggle effect bypass state with optimized parameter updates."""
        # Toggle channel effect bypass flag
        self.effect_bypass = not getattr(self, "effect_bypass", False)

    def _cycle_modulation_source(self):
        """Cycle through different modulation sources with optimized parameter updates."""
        # Cycle through modulation sources for route 0
        sources = [
            "lfo1",
            "lfo2",
            "lfo3",
            "velocity",
            "note_number",
            "channel_aftertouch",
            "mod_wheel",
        ]
        current_source = getattr(self, "_current_mod_source", "lfo1")
        next_index = (sources.index(current_source) + 1) % len(sources)
        new_source = sources[next_index]
        self._current_mod_source = new_source

        # Update modulation matrix route 0 with new source
        self.mod_matrix.set_route(
            0,
            new_source,
            "pitch",  # Keep destination as pitch
            amount=50.0 / 100.0,
            polarity=1.0,
        )

    def _apply_performance_preset(self):
        """Apply performance parameter preset with optimized parameter updates."""
        # Cycle through presets: bright -> dark -> aggressive -> mellow -> bright
        presets = ["bright", "dark", "aggressive", "mellow"]
        current_preset = getattr(self, "_current_preset", "bright")
        next_index = (presets.index(current_preset) + 1) % len(presets)
        new_preset = presets[next_index]
        self._current_preset = new_preset

        # Apply preset parameters to all active notes
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        if new_preset == "bright":
                            # Bright: higher cutoff, faster attack
                            partial.filter_cutoff = min(
                                20000, partial.filter_cutoff * 1.5
                            )
                            partial.amp_attack_time = max(
                                0.001, partial.amp_attack_time * 0.7
                            )
                        elif new_preset == "dark":
                            # Dark: lower cutoff, slower attack
                            partial.filter_cutoff = (
                                max(20, partial.filter_cutoff, 1000) * 0.7
                            )
                            partial.amp_attack_time = min(
                                2.0, partial.amp_attack_time * 1.3
                            )
                        elif new_preset == "aggressive":
                            # Aggressive: higher resonance, faster decay
                            partial.filter_resonance = min(
                                2.0,
                                (
                                    partial.filter_resonance
                                    if partial.filter_resonance
                                    else 0.7
                                )
                                * 1.5,
                            )
                            partial.amp_decay_time = max(
                                0.01, partial.amp_decay_time * 0.6
                            )
                        elif new_preset == "mellow":
                            # Mellow: lower resonance, slower decay
                            partial.filter_resonance = max(
                                0.0, (partial.filter_resonance or 0.7) * 0.6
                            )

    def is_active(self) -> bool:
        """Check if this channel renderer has any active notes with optimized check."""
        # Clean up inactive notes with optimized cleanup
        inactive_notes = [
            note
            for note, channel_note in self.active_notes.items()
            if not channel_note.is_active()
        ]
        for note in inactive_notes:
            # Clean up the channel note to release LFOs and other resources
            channel_note = self.active_notes[note]
            channel_note.cleanup()
            # Deallocate voice from voice manager with optimized deallocation
            self.voice_manager.deallocate_voice(note)
            del self.active_notes[note]

        # Clean up released voices from voice manager with optimized cleanup
        self.voice_manager.cleanup_released_voices()

        return len(self.active_notes) > 0

    def generate_silence(self, block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        ch_left = self.left_buffer[:block_size]
        ch_right = self.right_buffer[:block_size]
        ch_left.fill(0.0)
        ch_right.fill(0.0)
        return ch_left, ch_right

    def generate_sample_block_vectorized(
        self, block_size: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        VECTORIZED BLOCK SAMPLE GENERATION - PHASE 2 PERFORMANCE

        Generate audio block for this channel with vectorized NumPy operations.

        Performance optimizations:
        1. BATCH NOTE PROCESSING - Processes all active notes simultaneously
        2. NUMPY-BASED OPERATIONS - Uses NumPy for efficient mathematical operations
        3. PRE-ALLOCATED BUFFERS - Uses pre-allocated buffers to reduce allocation overhead
        4. ZERO-CLEARING OPTIMIZATION - Clears buffers efficiently using vectorized operations
        5. VECTORIZED MODULATION PROCESSING - Processes modulation with vectorized operations

        Args:
            block_size: Block size in samples

        Returns:
            Tuple of (left_channel, right_channel) audio buffers
        """
        if block_size > self.synth.block_size:
            raise Exception(f"invalid buffer size: {block_size}")

        # If no active notes, return silence with optimized return
        if not self.active_notes:
            return self.generate_silence(block_size)

        # Get current channel state with optimized access
        channel_state = self.get_channel_state()

        # Calculate pitch bend modulation with optimized calculation
        pitch_bend_range_cents = self.pitch_bend_range * 100
        pitch_bend_offset = (
            (self.pitch_bend_value - 8192) / 8192.0
        ) * pitch_bend_range_cents
        global_pitch_mod = pitch_bend_offset

        # Cache frequently used controller values with optimized caching
        self.cached_mod_wheel = self.controllers[1] or 0
        self.cached_breath_controller = self.controllers[2] or 0
        self.cached_foot_controller = self.controllers[4] or 0
        self.cached_brightness = self.controllers[72] or 64
        self.cached_harmonic_content = self.controllers[71] or 64
        self.cached_channel_pressure = self.channel_pressure_value

        if self.active_notes:
            self._process_notes_block_based(
                self.active_notes.items(),
                block_size,
                global_pitch_mod,
                left_batch=self.left_buffer,
                right_batch=self.right_buffer,
            )

        # Apply final clipping with vectorized operations - OPTIMIZED CLIPPING
        np.clip(
            self.left_buffer[:block_size], -1.0, 1.0, out=self.left_buffer[:block_size]
        )
        np.clip(
            self.right_buffer[:block_size],
            -1.0,
            1.0,
            out=self.right_buffer[:block_size],
        )

        return self.left_buffer, self.right_buffer

    def _process_notes_block_based(
        self,
        active_notes_list,
        block_size: int,
        global_pitch_mod: float,
        left_batch,
        right_batch,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        BLOCK-BASED NOTE PROCESSING - Maximum Performance

        Process all active notes using block-based generation for maximum performance.
        This uses the new generate_sample_block methods in ChannelNote and XGPartialGenerator.

        Args:
            active_notes_list: List of (note, channel_note) tuples for active notes
            block_size: Block size in samples
            global_pitch_mod: Global pitch modulation value

        Returns:
            Tuple of (left_channel, right_channel) audio buffers
        """
        left_batch[:block_size].fill(0.0)
        right_batch[:block_size].fill(0.0)
        if not active_notes_list:
            return left_batch, right_batch

        # Process all notes with block-based generation
        for note, channel_note in active_notes_list:
            # Generate samples directly into note buffers
            channel_note.generate_sample_block(
                block_size,
                self.note_left,
                self.note_right,
                mod_wheel=self.cached_mod_wheel,
                breath_controller=self.cached_breath_controller,
                foot_controller=self.cached_foot_controller,
                brightness=self.cached_brightness,
                harmonic_content=self.cached_harmonic_content,
                channel_pressure_value=self.cached_channel_pressure,
                key_pressure=self.key_pressure_values.get(note, 0),
                volume=self.volume,
                expression=self.expression,
                global_pitch_mod=global_pitch_mod,
            )

            # Vectorized accumulation
            np.add(
                left_batch[:block_size],
                self.note_left[:block_size],
                out=left_batch[:block_size],
            )
            np.add(
                right_batch[:block_size],
                self.note_right[:block_size],
                out=right_batch[:block_size],
            )

        return left_batch, right_batch

    def _process_notes_vectorized_per_note(
        self, active_notes_list: List, block_size: int, global_pitch_mod: float
    ):
        """
        VECTORIZED PER-NOTE PROCESSING - FALLBACK METHOD

        Process each active note individually with vectorized operations.
        This is a fallback method when batch processing fails.

        Performance optimizations:
        1. VECTORIZED OPERATIONS - Uses NumPy for efficient mathematical operations
        2. PRE-ALLOCATED BUFFERS - Uses pre-allocated buffers to reduce allocation overhead
        3. ZERO-CLEARING OPTIMIZATION - Clears buffers efficiently using vectorized operations
        4. BATCH SAMPLE PROCESSING - Processes samples in batches rather than individually

        Args:
            active_notes_list: List of (note, channel_note) tuples for active notes
            block_size: Block size in samples
            global_pitch_mod: Global pitch modulation value
        """
        # Process each active note individually with vectorized operations
        for note, channel_note in active_notes_list:
            try:
                # Clear temporary buffers using memory pool optimization
                if self.memory_pool:
                    # Return and get fresh zeroed buffers for better performance
                    self.memory_pool.return_mono_buffer(self.temp_left)
                    self.memory_pool.return_mono_buffer(self.temp_right)
                    self.temp_left = self.memory_pool.get_mono_buffer(zero_buffer=True)
                    self.temp_right = self.memory_pool.get_mono_buffer(zero_buffer=True)
                else:
                    # Fallback to direct zeroing
                    self.temp_left[:block_size].fill(0.0)
                    self.temp_right[:block_size].fill(0.0)

                # Get cached controller values for this processing cycle
                mod_wheel = self.cached_mod_wheel
                breath_controller = self.cached_breath_controller
                foot_controller = self.cached_foot_controller
                brightness = self.cached_brightness
                harmonic_content = self.cached_harmonic_content
                channel_pressure = self.cached_channel_pressure
                key_pressure = self.key_pressure_values.get(note, 0)

                # Process all samples in the block for this note
                for i in range(block_size):
                    # Generate a sample for this note with all modulation sources
                    left_sample, right_sample = channel_note.generate_sample(
                        mod_wheel=mod_wheel,
                        breath_controller=breath_controller,
                        foot_controller=foot_controller,
                        brightness=brightness,
                        harmonic_content=harmonic_content,
                        channel_pressure_value=channel_pressure,
                        key_pressure=key_pressure,
                        volume=self.volume,
                        expression=self.expression,
                        global_pitch_mod=global_pitch_mod,
                    )

                    # Accumulate in main buffers
                    self.left_buffer[i] += left_sample
                    self.right_buffer[i] += right_sample

            except Exception as e:
                # Disable problematic note
                channel_note.active = False
                continue

    # XG-specific controller handlers with optimized parameter updates
    def _handle_xg_harmonic_content(self, value: int):
        """Handle XG Harmonic Content controller (71) with optimized parameter update."""
        # Map 0-127 to resonance range (±24 semitones) and apply to all active notes
        semitones = ((value - 64) / 64.0) * 24.0
        resonance = max(0.0, min(2.0, 0.7 + semitones * 0.05))

        # Apply to all active notes - modify filter resonance parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    partial.filter_resonance = resonance

        self.cached_harmonic_content = value

    def _handle_xg_brightness(self, value: int):
        """Handle XG Brightness controller (72) with optimized parameter update."""
        # Update coefficient manager with new brightness value
        self.coeff_manager.update_xg_coefficient("brightness", value)

        # Get pre-computed brightness multiplier
        brightness_mult = self.coeff_manager.get_xg_coefficient("brightness", value)
        cutoff = max(20, min(20000, 1000.0 * brightness_mult))

        # Apply to all active notes - modify filter cutoff parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    partial.filter_cutoff = cutoff

        self.cached_brightness = value

    def _handle_xg_release_time(self, value: int):
        """Handle XG Release Time controller (73) with optimized parameter update."""
        # Map 0-127 to release time range (0.001 to 10.0 seconds)
        if value <= 64:
            release_time = 0.001 + (value / 64.0) * 0.999
        else:
            release_time = 1.0 + ((value - 64) / 63.0) * 17.0  # Up to 18 seconds

        # Apply to all active notes - modify envelope release parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        partial.amp_release_time = release_time

    def _handle_xg_attack_time(self, value: int):
        """Handle XG Attack Time controller (74) with optimized parameter update."""
        # Map 0-127 to attack time range (0.001 to 1.0 seconds)
        if value <= 64:
            attack_time = 0.001 + (value / 64.0) * 0.999
        else:
            attack_time = 1.0 + ((value - 64) / 63.0) * 17.0  # Up to 18 seconds

        # Apply to all active notes - modify envelope attack parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        partial.amp_attack_time = attack_time

    def _handle_xg_filter_cutoff(self, value: int):
        """Handle XG Filter Cutoff controller (75) with optimized parameter update."""
        # Update coefficient manager with new filter cutoff value
        self.coeff_manager.update_xg_coefficient("filter_cutoff", value)

        # Get pre-computed frequency ratio
        freq_ratio = self.coeff_manager.get_xg_coefficient("filter_cutoff", value)
        cutoff = max(20, min(20000, 1000.0 * freq_ratio))

        # Apply to all active notes - modify filter cutoff parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        partial.filter_cutoff = cutoff

    def _handle_xg_decay_time(self, value: int):
        """Handle XG Decay Time controller (76) with optimized parameter update."""
        # Map 0-127 to decay time range (0.01 to 5.0 seconds)
        decay_time = 0.01 + (value / 127.0) * 4.99

        # Apply to all active notes - modify envelope decay parameters
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        partial.amp_decay_time = decay_time

    def _handle_xg_vibrato_rate(self, value: int):
        """Handle XG Vibrato Rate controller (77) with optimized parameter update."""
        # Update coefficient manager with new vibrato rate value
        self.coeff_manager.update_xg_coefficient("vibrato_rate", value)

        # Get pre-computed LFO rate
        lfo_rate = self.coeff_manager.get_xg_coefficient("vibrato_rate", value)

        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].rate = lfo_rate
            self.lfos[0].update_xg_vibrato_rate(value)

    def _handle_xg_vibrato_depth(self, value: int):
        """Handle XG Vibrato Depth controller (78) with optimized parameter update."""
        # Map 0-127 to LFO depth range (0-600 cents)
        depth_cents = (value / 127.0) * 600.0
        lfo_depth = depth_cents / 100.0  # Convert to semitones

        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].depth = lfo_depth
            self.lfos[0].update_xg_vibrato_depth(value)

    def _handle_xg_vibrato_delay(self, value: int):
        """Handle XG Vibrato Delay controller (79) with optimized parameter update."""
        # Map 0-127 to LFO delay range (0.0 to 5.0 seconds)
        lfo_delay = (value / 127.0) * 5.0

        # Apply to first LFO (typically used for vibrato)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].delay = lfo_delay
            self.lfos[0].update_xg_vibrato_delay(value)

    def _handle_sostenuto_pedal(self, value: int):
        """Handle XG Sostenuto Pedal controller (66) with optimized parameter update."""
        # Sostenuto pedal: holds notes that are already playing when pedal is pressed
        pedal_pressed = value >= 64

        # Apply to all active notes - trigger envelope sostenuto methods
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        if pedal_pressed:
                            partial.amp_envelope.sostenuto_pedal_on()
                        else:
                            partial.amp_envelope.sostenuto_pedal_off()

    def _handle_soft_pedal(self, value: int):
        """Handle XG Soft Pedal controller (67) with optimized parameter update."""
        # Soft pedal: reduces volume/velocity by 50% when engaged
        soft_pedal_active = value >= 64

        # Apply to all active notes - set soft pedal state in envelopes
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        partial.amp_envelope.soft_pedal = soft_pedal_active

    def _handle_legato_foot_switch(self, value: int):
        """Handle XG Legato Foot Switch controller (68) with optimized parameter update."""
        # Legato foot switch: forces monophonic legato mode when engaged
        legato_active = value >= 64

        if legato_active:
            # Switch to monophonic legato mode
            self.voice_mode = self.VOICE_MODE_MONO_LEGATO
            self.mono_legato = True
        else:
            # Switch back to polyphonic mode
            self.voice_mode = self.VOICE_MODE_POLY
            self.mono_legato = False

    # XG Part Mode Implementation with optimized parameter updates
    def set_part_mode(self, mode: int):
        """Set XG part mode and apply changes with optimized parameter updates."""
        self.part_mode = max(0, min(7, mode))  # XG Part Modes range from 0-7
        self._apply_part_mode()

    def _apply_part_mode(self):
        """Apply XG part mode specific behaviors according to XG specification with optimized parameter updates."""
        # Apply part mode-specific changes according to XG specification
        # XG Specification Part Mode Implementation:
        # Mode 0: Normal Mode (synthesis mode)
        # Modes 1-7: Drum Kit variations

        if self.part_mode == 0:  # Normal Mode - Synthesis
            self._apply_normal_mode_parameters()
        elif self.part_mode >= 1 and self.part_mode <= 7:  # Drum Kit Modes
            self._apply_drum_kit_mode_parameters(self.part_mode)
        else:
            # Default to normal mode for invalid part modes
            self._apply_normal_mode_parameters()

        # Update all active notes with new parameters using vectorized operations
        self._update_active_notes_for_part_mode()

    def _apply_normal_mode_parameters(self):
        """Apply Normal Mode parameters (XG Standard) with optimized parameter updates."""
        # Standard synthesis parameters - no special modifications
        # Set normal synthesis mode (not drum mode)
        self.is_drum = False
        self.program = max(
            0, min(127, self.program)
        )  # Ensure valid program in synthesis range

        # Implementation would modify envelope/filter parameters
        # For vectorized renderer, we just flag that normal mode is active
        pass

    def _apply_drum_kit_mode_parameters(self, kit_mode: int):
        """
        Apply XG Drum Kit variation parameters (Part Modes 1-7)
        According to XG specification, these are drum kit variations, not synthesis effects

        XG Drum Kit Mapping:
        - Bank MSB 127, Programs 0-127: Standard drum kits (Kit 0-127)
        - Bank MSB 128, Programs 0-127: Alternative drum kits (Kit 0-127)
        - Part Mode 1-7 maps to different kit variations
        """
        # Set drum mode
        self.is_drum = True

        # XG Drum Kit Bank/Program Mapping
        # Part Mode 1 → Kit 0 (Standard), Part Mode 2 → Kit 1, etc.
        kit_variation = kit_mode - 1  # Mode 1 = Kit 0, Mode 2 = Kit 1, etc.

        # XG uses specific program mappings for drum kits
        # Program 127 = Kit 0 (Standard Kit), Program 128 = Kit 1, etc.
        drum_kit_program = kit_variation + 127
        self.program = min(drum_kit_program, 135)  # Cap at Program 135 (Kit 8)

        # XG requires Bank MSB changes for drum kits
        # Standard kits: Bank MSB 127, Alternative kits: Bank MSB 128
        if kit_mode <= 4:  # Modes 1-4 use standard kits
            self.bank = 127
            self.program = 127 + kit_variation  # Programs 127-130
        else:  # Modes 5-7 use alternative kits
            self.bank = 128
            self.program = 127 + (kit_variation - 4)  # Programs 127-129 for alt kits

        # Update all active notes to use drum mode parameters
        for note, channel_note in self.active_notes.items():
            channel_note.is_drum = True
            # XG drum notes should disable certain features (pitch env, etc.)
            # Implementation would modify drum parameters based on kit mode

    def _update_active_notes_for_part_mode(self):
        """Update all active notes when part mode changes with optimized parameter updates."""
        # Mark all active notes as needing parameter updates
        # TODO: implement proper updating of active notes

    def _apply_hyper_scream_mode_parameters(self):
        """Apply Hyper Scream Mode parameters (XG Aggressive) with optimized parameter updates."""
        # Aggressive sound: fast attack, high resonance, bright filter
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        if partial.amp_envelope:
                            partial.amp_attack_time = max(
                                0.001, partial.amp_attack_time * 0.5
                            )
                            partial.amp_decay_time = max(
                                0.01, partial.amp_decay_time * 0.7
                            )
                            partial.filter_resonance = min(
                                2.0, (partial.filter_resonance or 0.7) * 1.8
                            )
                            partial.filter_cutoff = min(
                                20000, (partial.filter_cutoff or 1000) * 1.3
                            )

    def _apply_analog_mode_parameters(self):
        """Apply Analog Mode parameters (XG Warmer Sound) with optimized parameter updates."""
        # Warmer sound: slower attack, lower cutoff, gentle resonance
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        if partial.amp_envelope:
                            partial.amp_attack_time = min(
                                1.0, partial.amp_attack_time * 1.2
                            )
                            partial.amp_release_time = min(
                                5.0, partial.amp_release_time * 1.3
                            )
                            partial.filter_cutoff = max(
                                100, (partial.filter_cutoff or 1000) * 0.8
                            )
                            partial.filter_resonance = max(
                                0.1, (partial.filter_resonance or 0.7) * 0.8
                            )

    def _apply_max_resonance_mode_parameters(self):
        """Apply Max Resonance Mode parameters (XG High Resonance) with optimized parameter updates."""
        # High resonance: maximum resonance, slightly lower cutoff
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    partial.filter_resonance = 2.0
                    partial.filter_cutoff = max(
                        200, (partial.filter_cutoff or 1000) * 0.9
                    )

    def _apply_stereo_mode_parameters(self):
        """Apply Stereo Mode parameters (XG Enhanced Stereo) with optimized parameter updates."""
        # Enhanced stereo: increase stereo width, adjust panning
        self.stereo_width = min(1.0, getattr(self, "stereo_width", 0.5) * 1.5)
        # Apply to modulation matrix for stereo enhancement
        self.mod_matrix.set_route(14, "expression", "pan", amount=0.3, polarity=1.0)

    def _apply_wah_mode_parameters(self):
        """Apply Wah Mode parameters (XG Wah Effect) with optimized parameter updates."""
        # Wah effect: bandpass filter with LFO modulation
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        partial.filter_type = "bandpass"
                        partial.filter_resonance = min(
                            2.0, (partial.filter_resonance or 0.7) * 1.5
                        )

        # Add LFO modulation to filter cutoff for wah effect
        self.mod_matrix.set_route(4, "lfo1", "filter_cutoff", amount=0.6, polarity=1.0)

    def _apply_dynamic_mode_parameters(self):
        """Apply Dynamic Mode parameters (XG Velocity Sensitive) with optimized parameter updates."""
        # Velocity sensitive: increase velocity sensitivity in modulation matrix
        self.mod_matrix.set_route(
            5, "velocity", "amp", amount=1.0, velocity_sensitivity=1.0
        )
        self.mod_matrix.set_route(
            11, "velocity", "filter_cutoff", amount=0.5, velocity_sensitivity=0.8
        )

    def _apply_distortion_mode_parameters(self):
        """Apply Distortion Mode parameters (XG Distorted Sound) with optimized parameter updates."""
        # Distortion: high resonance, bright filter, aggressive envelope
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        if partial.amp_envelope:
                            partial.amp_attack_time = max(
                                0.001, partial.amp_attack_time * 0.3
                            )
                            partial.amp_sustain_level = max(
                                0.1, partial.amp_sustain_level * 0.8
                            )
                            partial.filter_resonance = min(
                                2.0, (partial.filter_resonance or 0.7) * 2.0
                            )
                            partial.filter_cutoff = min(
                                20000, (partial.filter_cutoff or 1000) * 1.2
                            )
