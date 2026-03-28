"""
XG Channel Renderer

Handles audio synthesis for individual MIDI channels using vectorized operations.
Supports XG specification features including voice allocation, modulation, and effects routing.
"""

from __future__ import annotations

# Import VoiceManager dynamically to avoid circular imports
import importlib
from typing import Any

import numpy as np

# Import internal modules
from ..engine.optimized_coefficient_manager import get_global_coefficient_manager
from ..modulation.vectorized_matrix import VectorizedModulationMatrix
from ..voice.voice_priority import VoicePriority
from .channel_note import ChannelNote


class VectorizedChannelRenderer:
    """
    XG Channel Renderer

    Processes MIDI channel data for XG synthesizer using vectorized NumPy operations.
    Manages voice allocation, controller processing, and audio generation per MIDI channel.
    """

    # XG Voice Allocation Modes (Complete Implementation)
    VOICE_MODE_POLY = 0  # Standard polyphonic mode (XG default)
    VOICE_MODE_MONO = 1  # Basic monophonic mode
    VOICE_MODE_POLY_DRUM = 2  # Poly with drum priority
    VOICE_MODE_MONO_LEGATO = 3  # Monophonic with legato (note overlapping)
    VOICE_MODE_MONO_PORTAMENTO = 4  # Monophonic with portamento (glide)

    def __init__(self, channel: int, synth):
        """
        Initialize channel renderer for XG synthesizer.

        Args:
            channel: MIDI channel number (0-15)
            synth: Parent synthesizer instance
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

        # XG voice management system (dynamic import to avoid circular imports)
        voice_manager_module = importlib.import_module("synth.voice.voice_manager")
        VoiceManager = voice_manager_module.VoiceManager
        self.voice_manager = VoiceManager(synth.max_polyphony)
        self.polyphony_limit = synth.max_polyphony

        # XG Voice Allocation Mode
        self.voice_mode = self.VOICE_MODE_POLY  # Default to standard polyphonic (XG)
        self.mono_legato = False  # XG mono legato mode
        self.mono_portamento = False  # XG mono portamento mode

        # Active notes on this channel
        self.active_notes: dict[int, ChannelNote] = {}  # note -> ChannelNote

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
        self.lfos[0].set_modulation_depths(pitch_cents=50.0, filter_depth=0.0, amplitude_depth=0.0)

        # LFO2: Filter modulation - optional
        self.lfos[1].set_modulation_routing(pitch=False, filter=True, amplitude=False)
        self.lfos[1].set_modulation_depths(pitch_cents=0.0, filter_depth=0.3, amplitude_depth=0.0)

        # LFO3: Amplitude modulation (tremolo) - optional
        self.lfos[2].set_modulation_routing(pitch=False, filter=False, amplitude=True)
        self.lfos[2].set_modulation_depths(pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3)

        # XG LFO modulation state for channel-wide modulation
        self.lfo_pitch_modulation = 0.0
        self.lfo_tremolo_modulation = 0.0

        # Initialize vectorized modulation matrix with pre-allocated buffers
        self.mod_matrix = VectorizedModulationMatrix(num_routes=16)
        # Setup modulation matrix after all components are initialized
        self._setup_default_modulation_matrix()

        # Optimized coefficient manager for performance
        self.coeff_manager = get_global_coefficient_manager()

        # Get stereo buffers from synthesizer's XGBufferPool (will be zeroed)
        self.left_buffer = self.memory_pool.get_mono_buffer(self.synth.block_size)
        self.right_buffer = self.memory_pool.get_mono_buffer(self.synth.block_size)

        # Temporary buffers for intermediate processing
        self.temp_left = self.memory_pool.get_mono_buffer(self.synth.block_size)
        self.temp_right = self.memory_pool.get_mono_buffer(self.synth.block_size)
        self.note_left = self.memory_pool.get_mono_buffer(self.synth.block_size)
        self.note_right = self.memory_pool.get_mono_buffer(self.synth.block_size)

        # Cached parameter values for performance
        self.cached_mod_wheel = 0
        self.cached_breath_controller = 0
        self.cached_foot_controller = 0
        self.cached_brightness = 64
        self.cached_harmonic_content = 64
        self.cached_channel_pressure = 0

        # Lazy parameter update system
        self.parameter_cache = {}  # Cached parameter values for lazy updates
        self.parameter_dirty = False  # Flag when parameters need updating

        # NRPN (Non-Registered Parameter Number) state tracking - XG compatibility
        self.nrpn_msb = 0  # NRPN MSB (CC 99)
        self.nrpn_lsb = 0  # NRPN LSB (CC 98)
        self.nrpn_active = False  # NRPN sequence in progress
        self.data_msb = 0  # Data Entry MSB received
        self.data_msb_received = False  # Track if Data MSB has been received

        # RPN (Registered Parameter Number) state tracking - GM2 compatibility
        self.rpn_msb = 0  # RPN MSB (CC 101)
        self.rpn_lsb = 0  # RPN LSB (CC 100)
        self.rpn_active = False  # RPN sequence in progress

        # Hold 2 pedal state - GM optional compliance
        self.hold2_active = False  # CC69

        # Local control state - GM optional
        self.local_control = True  # CC122 - True = local control on

        # Omni mode state - GM mode messages
        self.omni_mode = False  # CC124/125 - False = omni off, True = omni on
        self.mono_mode = False  # CC126/CC127 - False = poly, True = mono

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
        self.mod_matrix.set_route(3, "amp_env", "filter_cutoff", amount=0.5, polarity=1.0)

        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(4, "lfo1", "filter_cutoff", amount=0.3, polarity=1.0)

        # Velocity -> Amplitude
        self.mod_matrix.set_route(5, "velocity", "amp", amount=0.5, velocity_sensitivity=0.5)

        # Note Number -> Pitch (basic pitch mapping)
        self.mod_matrix.set_route(6, "note_number", "pitch", amount=1.0, key_scaling=1.0)

        # Mod Wheel -> LFO1 Depth (vibrato control)
        self.mod_matrix.set_route(7, "mod_wheel", "lfo1_depth", amount=1.0, polarity=1.0)

        # Breath Controller -> LFO1 Depth
        self.mod_matrix.set_route(8, "breath_controller", "lfo1_depth", amount=0.8, polarity=1.0)

        # Foot Controller -> Filter Cutoff
        self.mod_matrix.set_route(9, "foot_controller", "filter_cutoff", amount=0.5, polarity=1.0)

        # Channel Aftertouch -> LFO1 Depth
        self.mod_matrix.set_route(10, "channel_aftertouch", "lfo1_depth", amount=0.6, polarity=1.0)

        # Key Aftertouch -> Filter Resonance
        self.mod_matrix.set_route(
            11, "key_aftertouch", "filter_resonance", amount=0.4, polarity=1.0
        )

        # Brightness -> Filter Cutoff (XG controller 72)
        self.mod_matrix.set_route(12, "brightness", "filter_cutoff", amount=0.7, polarity=1.0)

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

    def _get_controller_mapping(self) -> dict[int, str]:
        """Map controllers to parameter types for generic handling."""
        return {
            # XG Sound Controllers
            71: "harmonic_content",
            72: "brightness",
            73: "release_time",
            74: "attack_time",
            75: "filter_cutoff",
            76: "decay_time",
            77: "vibrato_rate",
            78: "vibrato_depth",
            79: "vibrato_delay",
            # General Purpose Buttons
            80: "gp_button_1",
            81: "gp_button_2",
            82: "gp_button_3",
            83: "gp_button_4",
            # XG Pedals/Controllers
            66: "sostenuto_pedal",
            67: "soft_pedal",
            68: "legato_foot_switch",
            69: "hold2_pedal",
            70: "sound_controller_1",
            # Portamento
            5: "portamento_time",
            65: "portamento_on_off",
            84: "portamento_control",
            # Effects
            92: "effects_2_depth",
            95: "effects_5_depth",
        }

    def _apply_cached_parameter_updates(self):
        """Apply cached parameter updates during audio processing (lazy updates)."""
        if not self.parameter_dirty:
            return

        # Apply harmonic content updates
        if "harmonic_content" in self.parameter_cache:
            for controller, value in self.parameter_cache["harmonic_content"].items():
                self._handle_xg_harmonic_content(value)

        # Apply brightness updates
        if "brightness" in self.parameter_cache:
            for controller, value in self.parameter_cache["brightness"].items():
                self._handle_xg_brightness(value)

        # Apply envelope parameter updates
        if "release_time" in self.parameter_cache:
            for controller, value in self.parameter_cache["release_time"].items():
                self._handle_xg_release_time(value)

        if "attack_time" in self.parameter_cache:
            for controller, value in self.parameter_cache["attack_time"].items():
                self._handle_xg_attack_time(value)

        if "decay_time" in self.parameter_cache:
            for controller, value in self.parameter_cache["decay_time"].items():
                self._handle_xg_decay_time(value)

        # Apply filter updates
        if "filter_cutoff" in self.parameter_cache:
            for controller, value in self.parameter_cache["filter_cutoff"].items():
                self._handle_xg_filter_cutoff(value)

        # Apply LFO updates
        if "vibrato_rate" in self.parameter_cache:
            for controller, value in self.parameter_cache["vibrato_rate"].items():
                self._handle_xg_vibrato_rate(value)

        if "vibrato_depth" in self.parameter_cache:
            for controller, value in self.parameter_cache["vibrato_depth"].items():
                self._handle_xg_vibrato_depth(value)

        if "vibrato_delay" in self.parameter_cache:
            for controller, value in self.parameter_cache["vibrato_delay"].items():
                self._handle_xg_vibrato_delay(value)

        # Apply pedal/button updates
        pedal_mappings = {
            "sostenuto_pedal": self._handle_sostenuto_pedal,
            "soft_pedal": self._handle_soft_pedal,
            "legato_foot_switch": self._handle_legato_foot_switch,
            "hold2_pedal": self._handle_hold2_pedal,
            "sound_controller_1": self._handle_sound_controller_1,
        }

        for param_type, handler in pedal_mappings.items():
            if param_type in self.parameter_cache:
                for controller, value in self.parameter_cache[param_type].items():
                    handler(value)

        # Apply GP button updates
        if "gp_button_1" in self.parameter_cache:
            for controller, value in self.parameter_cache["gp_button_1"].items():
                self._handle_xg_gp_button(1, value)

        if "gp_button_2" in self.parameter_cache:
            for controller, value in self.parameter_cache["gp_button_2"].items():
                self._handle_xg_gp_button(2, value)

        if "gp_button_3" in self.parameter_cache:
            for controller, value in self.parameter_cache["gp_button_3"].items():
                self._handle_xg_gp_button(3, value)

        if "gp_button_4" in self.parameter_cache:
            for controller, value in self.parameter_cache["gp_button_4"].items():
                self._handle_xg_gp_button(4, value)

        # Apply portamento updates
        if "portamento_time" in self.parameter_cache:
            for controller, value in self.parameter_cache["portamento_time"].items():
                self._handle_portamento_time(value)

        if "portamento_on_off" in self.parameter_cache:
            for controller, value in self.parameter_cache["portamento_on_off"].items():
                self._handle_portamento_on_off(value)

        if "portamento_control" in self.parameter_cache:
            for controller, value in self.parameter_cache["portamento_control"].items():
                self._handle_portamento_control(value)

        # Apply effects updates
        if "effects_2_depth" in self.parameter_cache:
            for controller, value in self.parameter_cache["effects_2_depth"].items():
                self._handle_effects_2_depth(value)

        if "effects_5_depth" in self.parameter_cache:
            for controller, value in self.parameter_cache["effects_5_depth"].items():
                self._handle_effects_5_depth(value)

        # Clear cache after applying
        self.parameter_cache.clear()
        self.parameter_dirty = False

    def get_channel_state(self) -> dict[str, Any]:
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
            use_modulation_matrix=self.synth.use_modulation_matrix,
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
        """Handle Control Change message for this channel with generic parameter mapping and lazy updates."""
        self.controllers[controller] = value

        # GENERIC PARAMETER MAPPING - High Performance Replacement for 50+ verbose handlers
        # Map controllers to parameter types for lazy updates
        if controller in self._get_controller_mapping():
            param_type = self._get_controller_mapping()[controller]

            # LAZY UPDATE: Cache parameter value, apply during audio processing
            if param_type not in self.parameter_cache:
                self.parameter_cache[param_type] = {}

            self.parameter_cache[param_type][controller] = value
            self.parameter_dirty = True

            # Handle special cases that need immediate attention
            if controller in [0, 32]:  # Bank select needs immediate update
                if controller == 0:
                    self.bank_msb = value
                elif controller == 32:
                    self.bank_lsb = value
                self.bank = (self.bank_msb << 7) | self.bank_lsb
            elif controller in [7, 11, 10, 8]:  # Basic parameters
                if controller == 7:
                    self.volume = value
                elif controller == 11:
                    self.expression = value
                elif controller == 10:
                    self.pan = value
                elif controller == 8:
                    self.balance = value

        # Handle NRPN/RPN sequences (must be processed immediately)
        elif controller == 98:  # NRPN LSB
            self.nrpn_lsb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return  # Don't process as regular controller
        elif controller == 99:  # NRPN MSB
            self.nrpn_msb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return  # Don't process as regular controller
        elif controller == 100:  # RPN LSB
            self.rpn_lsb = value
            self.rpn_active = True
            return  # Don't process as regular controller
        elif controller == 101:  # RPN MSB
            self.rpn_msb = value
            self.rpn_active = True
            return  # Don't process as regular controller
        elif controller == 6:  # Data Entry MSB
            if self.nrpn_active and not self.data_msb_received:
                self.data_msb = value
                self.data_msb_received = True
                return  # Wait for LSB
            elif self.nrpn_active and self.data_msb_received:
                # Complete NRPN message received
                self._handle_nrpn_complete(self.nrpn_msb, self.nrpn_lsb, self.data_msb, value)
                self.nrpn_active = False
                self.data_msb_received = False
                return
            elif self.rpn_active:
                # Handle RPN data entry
                self._handle_rpn_complete(self.rpn_msb, self.rpn_lsb, value)
                self.rpn_active = False
                return
        elif controller == 96:  # Data Increment (GM2 Optional)
            if self.nrpn_active:
                self._handle_nrpn_increment()
            elif self.rpn_active:
                self._handle_rpn_increment()
        elif controller == 97:  # Data Decrement (GM2 Optional)
            if self.nrpn_active:
                self._handle_nrpn_decrement()
            elif self.rpn_active:
                self._handle_rpn_decrement()
        elif controller == 121:  # Reset All Controllers (GM)
            self._handle_reset_all_controllers()
        elif controller == 122:  # Local Control (GM Optional)
            self._handle_local_control(value)
        elif controller == 124:  # Omni Off (GM Mode)
            self._handle_omni_off()
        elif controller == 125:  # Omni On (GM Mode)
            self._handle_omni_on()
        elif controller == 126:  # Mono On (GM Mode)
            self._handle_mono_on(value)
        elif controller == 127:  # Poly On (GM Mode)
            self._handle_poly_on()

    # Removed controller batching system for lazy parameter updates

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
        if hasattr(self, "active_notes"):
            for note, channel_note in list(self.active_notes.items()):
                if hasattr(channel_note, "cleanup"):
                    channel_note.cleanup()  # type: ignore
                del self.active_notes[note]

        # Return LFOs to pool
        if hasattr(self, "lfos"):
            for lfo in self.lfos:
                if hasattr(self.synth, "lfo_pool"):
                    self.synth.lfo_pool.release_oscillator(lfo)

        # Clean up buffers
        self.cleanup_buffers()

        # Clear references
        if hasattr(self, "lfos"):
            self.lfos.clear()
        if hasattr(self, "active_notes"):
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
                            partial.filter_cutoff = min(20000, partial.filter_cutoff * 1.5)
                            partial.amp_attack_time = max(0.001, partial.amp_attack_time * 0.7)
                        elif new_preset == "dark":
                            # Dark: lower cutoff, slower attack
                            partial.filter_cutoff = max(20, partial.filter_cutoff, 1000) * 0.7
                            partial.amp_attack_time = min(2.0, partial.amp_attack_time * 1.3)
                        elif new_preset == "aggressive":
                            # Aggressive: higher resonance, faster decay
                            partial.filter_resonance = min(
                                2.0,
                                (partial.filter_resonance if partial.filter_resonance else 0.7)
                                * 1.5,
                            )
                            partial.amp_decay_time = max(0.01, partial.amp_decay_time * 0.6)
                        elif new_preset == "mellow":
                            # Mellow: lower resonance, slower decay
                            partial.filter_resonance = max(
                                0.0, (partial.filter_resonance or 0.7) * 0.6
                            )

    def is_active(self) -> bool:
        """Check if this channel renderer has any active notes with optimized check."""
        # Clean up inactive notes with optimized cleanup
        inactive_notes = [
            note for note, channel_note in self.active_notes.items() if not channel_note.is_active()
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

    def generate_silence(self, block_size: int) -> tuple[np.ndarray, np.ndarray]:
        ch_left = self.left_buffer[:block_size]
        ch_right = self.right_buffer[:block_size]
        ch_left.fill(0.0)
        ch_right.fill(0.0)
        return ch_left, ch_right

    def generate_sample_block_vectorized(self, block_size: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate audio sample block for this channel using vectorized operations.

        Processes all active notes in parallel using NumPy vectorized operations.
        Applies channel-wide modulation, controller updates, and audio clipping.

        Args:
            block_size: Number of samples to generate

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
        pitch_bend_offset = ((self.pitch_bend_value - 8192) / 8192.0) * pitch_bend_range_cents
        global_pitch_mod = pitch_bend_offset

        # LAZY PARAMETER UPDATE: Apply cached controller changes during audio processing
        self._apply_cached_parameter_updates()

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
        np.clip(self.left_buffer[:block_size], -1.0, 1.0, out=self.left_buffer[:block_size])
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
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Process active notes using block-based sample generation.

        Generates audio samples for all active notes in the channel.
        Uses vectorized operations for efficient processing.

        Args:
            active_notes_list: List of (note, channel_note) tuples for active notes
            block_size: Number of samples to generate
            global_pitch_mod: Global pitch modulation in cents
            left_batch: Left channel output buffer
            right_batch: Right channel output buffer

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
        """Apply XG part mode specific behaviors according to XG specification."""
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

        # Update all active notes with new parameters
        self._update_active_notes_for_part_mode()

    def _apply_normal_mode_parameters(self):
        """Apply Normal Mode parameters (XG Standard synthesis mode)."""
        # Normal mode: Standard melodic instrument synthesis
        self.is_drum = False

        # Ensure valid program range for melodic instruments (0-127)
        self.program = max(0, min(127, self.program))

        # Set bank to melodic bank (MSB 0, LSB 0 for standard GM)
        self.bank_msb = 0
        self.bank_lsb = 0
        self.bank = 0

        # Reset any drum-specific parameters
        # In normal mode, use standard envelope and filter settings
        # These will be applied through the standard parameter loading

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
        # Update all active notes with new part mode parameters
        # This ensures smooth transitions when switching between modes

        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                # Update drum/melodic mode for the note
                channel_note.is_drum = self.is_drum

                # Update program and bank for the note
                channel_note.program = self.program
                channel_note.bank = self.bank

                # For drum mode, the note parameters will be refreshed on next audio block
                # The ChannelNote constructor already handles drum vs melodic parameter selection
                # based on the is_drum flag and other parameters

    def _apply_hyper_scream_mode_parameters(self):
        """Apply Hyper Scream Mode parameters (XG Aggressive sound mode)."""
        # Hyper Scream: Aggressive, bright, high-energy sound
        # Fast attack, high resonance, bright filter, enhanced modulation

        # Adjust envelope parameters for aggressive attack
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Fast attack for punchy sound
                        if partial.amp_envelope:
                            partial.amp_attack_time = max(0.001, partial.amp_attack_time * 0.3)
                            partial.amp_decay_time = max(0.01, partial.amp_decay_time * 0.8)
                            partial.amp_sustain_level = max(0.1, partial.amp_sustain_level * 0.9)

                        # High resonance and bright filter
                        partial.filter_resonance = min(2.0, (partial.filter_resonance or 0.7) * 2.0)
                        partial.filter_cutoff = min(20000, (partial.filter_cutoff or 1000) * 1.5)

                        # Enhanced modulation for aggressive character
                        if partial.filter_envelope:
                            partial.filter_envelope.attack = max(
                                0.001, partial.filter_envelope.attack * 0.5
                            )
                            partial.filter_envelope.decay = max(
                                0.01, partial.filter_envelope.decay * 0.7
                            )

        # Adjust LFO parameters for more intense modulation
        if self.lfos:
            for lfo in self.lfos:
                lfo.depth *= 1.5  # Increase modulation depth
                lfo.rate *= 1.2  # Slightly faster modulation

    def _apply_analog_mode_parameters(self):
        """Apply Analog Mode parameters (XG Warmer Sound mode)."""
        # Analog mode: Warmer, more natural sound with gentler filtering
        # Slower envelopes, darker tone, reduced resonance

        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Slower, more natural envelope response
                        if partial.amp_envelope:
                            partial.amp_attack_time = min(1.0, partial.amp_attack_time * 1.3)
                            partial.amp_decay_time = min(3.0, partial.amp_decay_time * 1.2)
                            partial.amp_release_time = min(8.0, partial.amp_release_time * 1.5)

                        # Darker, warmer filter response
                        partial.filter_cutoff = max(100, (partial.filter_cutoff or 1000) * 0.75)
                        partial.filter_resonance = max(0.1, (partial.filter_resonance or 0.7) * 0.6)

                        # Soften filter envelope for more natural response
                        if partial.filter_envelope:
                            partial.filter_envelope.attack = min(
                                1.0, partial.filter_envelope.attack * 1.5
                            )
                            partial.filter_envelope.decay = min(
                                3.0, partial.filter_envelope.decay * 1.3
                            )

        # Reduce LFO modulation for warmer sound
        if self.lfos:
            for lfo in self.lfos:
                lfo.depth *= 0.7  # Reduce modulation intensity
                lfo.rate *= 0.8  # Slower modulation

    def _apply_max_resonance_mode_parameters(self):
        """Apply Max Resonance Mode parameters (XG High Resonance mode)."""
        # Max Resonance: Emphasized filter resonance with controlled cutoff
        # Creates a more pronounced, resonant character

        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Maximum resonance for emphasis
                        partial.filter_resonance = 2.0

                        # Slightly lower cutoff to compensate for resonance boost
                        partial.filter_cutoff = max(200, (partial.filter_cutoff or 1000) * 0.9)

                        # Enhance filter envelope for more dynamic resonance
                        if partial.filter_envelope:
                            partial.filter_envelope.sustain = min(
                                1.0, partial.filter_envelope.sustain * 1.2
                            )
                            partial.filter_envelope.decay = min(
                                5.0, partial.filter_envelope.decay * 1.3
                            )

        # Reduce LFO modulation slightly to avoid overwhelming resonance
        if self.lfos:
            for lfo in self.lfos:
                lfo.depth *= 0.8  # Slightly reduce modulation to complement resonance

    def _apply_stereo_mode_parameters(self):
        """Apply Stereo Mode parameters (XG Enhanced Stereo mode)."""
        # Enhanced stereo: Increase stereo width and dynamic panning
        # Creates a wider, more spacious sound field

        # Increase stereo width for all partials
        self.stereo_width = min(1.0, getattr(self, "stereo_width", 0.5) * 1.5)

        # Apply enhanced stereo routing to modulation matrix
        self.mod_matrix.set_route(14, "expression", "pan", amount=0.4, polarity=1.0)
        self.mod_matrix.set_route(15, "lfo3", "pan", amount=0.2, polarity=1.0)  # Subtle LFO panning

        # Adjust panning for individual partials to create stereo spread
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for i, partial in enumerate(channel_note.partials):
                    if partial.is_active():
                        # Alternate partials slightly left/right for stereo spread
                        if i % 2 == 0:
                            partial.pan = max(-1.0, partial.pan - 0.1)  # Slightly left
                        else:
                            partial.pan = min(1.0, partial.pan + 0.1)  # Slightly right

        # Reduce mono-compatible effects to enhance stereo perception
        if self.lfos:
            # Increase LFO 3 rate for subtle stereo movement
            if len(self.lfos) >= 3:
                self.lfos[2].rate *= 1.3

    def _apply_wah_mode_parameters(self):
        """Apply Wah Mode parameters (XG Wah Effect mode)."""
        # Wah effect: Dynamic bandpass filter sweep with LFO modulation
        # Creates classic wah-wah effect with frequency sweeping

        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Switch to bandpass filter for wah effect
                        partial.filter_type = "bandpass"

                        # Increase resonance for more pronounced wah character
                        partial.filter_resonance = min(2.0, (partial.filter_resonance or 0.7) * 1.8)

                        # Set initial cutoff in mid-range for wah sweep
                        partial.filter_cutoff = max(200, min(8000, (partial.filter_cutoff or 1000)))

                        # Adjust envelope for wah response
                        if partial.filter_envelope:
                            partial.filter_envelope.attack = max(
                                0.001, partial.filter_envelope.attack * 0.8
                            )
                            partial.filter_envelope.decay = min(
                                2.0, partial.filter_envelope.decay * 1.5
                            )

        # Add LFO modulation to filter cutoff for automatic wah sweep
        self.mod_matrix.set_route(4, "lfo1", "filter_cutoff", amount=0.8, polarity=1.0)

        # Configure LFO for wah effect (slower, wider sweep)
        if self.lfos and len(self.lfos) > 0:
            self.lfos[0].rate *= 0.6  # Slower sweep rate
            self.lfos[0].depth *= 1.2  # Wider frequency sweep

    def _apply_dynamic_mode_parameters(self):
        """Apply Dynamic Mode parameters (XG Velocity Sensitive mode)."""
        # Dynamic mode: Enhanced velocity sensitivity for expressive playing
        # Makes the instrument more responsive to playing dynamics

        # Increase velocity sensitivity in modulation matrix
        self.mod_matrix.set_route(5, "velocity", "amp", amount=1.2, velocity_sensitivity=1.5)
        self.mod_matrix.set_route(
            11, "velocity", "filter_cutoff", amount=0.7, velocity_sensitivity=1.2
        )
        self.mod_matrix.set_route(
            12, "velocity", "filter_resonance", amount=0.4, velocity_sensitivity=0.8
        )

        # Adjust envelope response for better velocity tracking
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Make envelopes more velocity-sensitive
                        if partial.amp_envelope:
                            partial.amp_envelope.velocity_sense = min(
                                2.0, partial.amp_envelope.velocity_sense * 1.5
                            )

                        if partial.filter_envelope:
                            partial.filter_envelope.velocity_sense = min(
                                2.0, partial.filter_envelope.velocity_sense * 1.3
                            )

        # Slightly increase LFO depth for more dynamic movement
        if self.lfos:
            for lfo in self.lfos:
                lfo.depth *= 1.1  # Subtle increase in modulation

    def _apply_distortion_mode_parameters(self):
        """Apply Distortion Mode parameters (XG Distorted Sound mode)."""
        # Distortion mode: Aggressive, overdriven sound with enhanced harmonics
        # High resonance, bright filter, fast attack, compressed sustain

        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active():
                        # Aggressive envelope for distorted character
                        if partial.amp_envelope:
                            partial.amp_attack_time = max(
                                0.001, partial.amp_attack_time * 0.2
                            )  # Very fast attack
                            partial.amp_decay_time = max(
                                0.01, partial.amp_decay_time * 0.5
                            )  # Fast decay
                            partial.amp_sustain_level = max(
                                0.3, partial.amp_sustain_level * 0.7
                            )  # Compressed sustain
                            partial.amp_release_time = min(
                                3.0, partial.amp_release_time * 0.8
                            )  # Moderate release

                        # High resonance and bright filter for distortion harmonics
                        partial.filter_resonance = min(2.0, (partial.filter_resonance or 0.7) * 2.5)
                        partial.filter_cutoff = min(20000, (partial.filter_cutoff or 1000) * 1.4)

                        # Aggressive filter envelope
                        if partial.filter_envelope:
                            partial.filter_envelope.attack = max(
                                0.001, partial.filter_envelope.attack * 0.3
                            )
                            partial.filter_envelope.decay = max(
                                0.01, partial.filter_envelope.decay * 0.6
                            )
                            partial.filter_envelope.sustain = max(
                                0.2, partial.filter_envelope.sustain * 0.8
                            )

        # Enhanced LFO modulation for distorted character
        if self.lfos:
            for lfo in self.lfos:
                lfo.depth *= 1.3  # More intense modulation
                lfo.rate *= 1.1  # Slightly faster for edgy feel

        # Add distortion-specific modulation routes
        self.mod_matrix.set_route(13, "lfo2", "filter_resonance", amount=0.3, polarity=1.0)

    def _handle_nrpn_complete(
        self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int
    ) -> bool:
        """
        Handle completed NRPN message routing.

        Args:
            nrpn_msb: NRPN parameter MSB (0-127)
            nrpn_lsb: NRPN parameter LSB (0-127)
            data_msb: Data entry MSB (0-127)
            data_lsb: Data entry LSB (0-127)

        Returns:
            True if NRPN was handled, False otherwise
        """
        # Check if this is a system NRPN (MSB 0-3) - includes effects parameters
        if nrpn_msb <= 3:  # MSB 0-3: System Effects (Reverb, Chorus, Variation)
            # Route to XG effects manager
            if hasattr(self.synth, "effects_manager"):
                return self.synth.effects_manager.handle_nrpn_system_effects(
                    nrpn_msb, nrpn_lsb, data_msb, data_lsb, self.channel
                )

        # Check if this is a channel-specific effect NRPN (MSB 1-15)
        elif 1 <= nrpn_msb <= 15:
            # Route to effect manager with channel specified
            if hasattr(self.synth, "effects_manager"):
                return self.synth.effects_manager.handle_nrpn(
                    nrpn_msb, nrpn_lsb, data_msb, data_lsb, self.channel
                )

        # Check if this is a drum NRPN (MSB 40-41) and we're on drum channel
        elif 40 <= nrpn_msb <= 41 and self.channel == 9 and hasattr(self.synth, "drum_manager"):
            # Route to drum manager
            return self.synth.drum_manager.handle_xg_drum_setup_nrpn(
                self.channel, nrpn_msb, nrpn_lsb, data_msb, data_lsb
            )

        # Check if this is pitch envelope depth (MSB 0, LSB 440)
        elif nrpn_msb == 0 and nrpn_lsb == 440:
            # Control pitch envelope depth for all partial generators
            for note in self.active_notes.values():
                if hasattr(note, "partials"):
                    for partial in note.partials:
                        if hasattr(partial, "update_pitch_envelope_depth"):
                            partial.update_pitch_envelope_depth(data_msb)
            return True

        # Check if this is XG Voice parameter (MSB 127)
        elif nrpn_msb == 127:
            # Route XG Voice parameters to all active partial generators
            # These are voice-level synthesis parameters that affect all partials
            for note in self.active_notes.values():
                if hasattr(note, "partials"):
                    for partial in note.partials:
                        self._route_xg_voice_nrpn_to_partial(partial, nrpn_lsb, data_msb, data_lsb)
            return True

        # Unknown NRPN - not handled
        return False

    def _handle_rpn_complete(self, rpn_msb: int, rpn_lsb: int, value: int) -> bool:
        """
        Handle completed RPN (Registered Parameter Number) message.

        Args:
            rpn_msb: RPN parameter MSB (0-127)
            rpn_lsb: RPN parameter LSB (0-127)
            value: Data entry value (0-127)

        Returns:
            True if RPN was handled, False otherwise
        """
        # GM2 RPN parameters - these are standardized across all devices
        if rpn_msb == 0:
            if rpn_lsb == 0:
                # Pitch Bend Range - MSB (semitones)
                self.pitch_bend_range = value
                return True
            elif rpn_lsb == 1:
                # Fine Pitch Bend Range (cents) - LSB part of pitch bend range
                # Usually used with MSB
                return True
            elif rpn_lsb == 2:
                # Coarse Tuning (semitones -64 to +63)
                # This affects the entire channel
                semitones = value - 64  # Center at 0
                # Would apply global tuning offset
                return True
            elif rpn_lsb == 3:
                # Fine Tuning (cents -100 to +100)
                # High resolution tuning adjustment
                cents = ((value - 64) / 64.0) * 100.0
                # Would apply fine tuning offset
                return True
            elif rpn_lsb == 4 or rpn_lsb == 5:
                # Parameter Selection (for GM2 extended parameters)
                # LSB 4 = Parameter selection MSB
                # LSB 5 = Parameter selection LSB
                return True

        # Unknown RPN
        return False

    def _route_xg_voice_nrpn_to_partial(
        self, partial, nrpn_lsb: int, data_msb: int, data_lsb: int
    ) -> None:
        """
        Route XG Voice NRPN parameters (MSB 127) to appropriate partial generator methods.

        XG Voice Parameters are mapped according to the XG specification:
        - LSB 0: Element Switch (bit field for which elements are active)
        - And many others...
        """
        try:
            if nrpn_lsb == 0:
                # Element Switch - bit field for active elements
                partial._process_element_switch(data_msb) if hasattr(
                    partial, "_process_element_switch"
                ) else None
            elif nrpn_lsb == 1:
                # Detune Adjustment - fine pitch
                detune_cents = ((data_msb - 64) * 100) / 16.0
                partial._calc_detune(detune_cents) if hasattr(partial, "_calc_detune") else None
            elif nrpn_lsb == 2:
                # Volume Control
                partial._level_control(data_msb / 127.0) if hasattr(
                    partial, "_level_control"
                ) else None
            elif nrpn_lsb == 3:
                # Pan Control (-1 to +1)
                pan = (data_msb - 64) / 63.0
                partial._pan_control(pan) if hasattr(partial, "_pan_control") else None
            # Add more XG Voice NRPN handlers as needed
        except Exception:
            # Ignore NRPN routing errors to maintain stability
            pass

    def _handle_nrpn_increment(self):
        """Handle NRPN data increment (CC 96)."""
        # Increment current NRPN parameter value by 1
        if self.nrpn_active and self.data_msb_received:
            # Increment the current parameter value
            current_value = (self.data_msb << 7) | self.data_lsb
            new_value = min(16383, current_value + 1)  # 14-bit max

            # Update data values
            self.data_msb = (new_value >> 7) & 0x7F
            self.data_lsb = new_value & 0x7F

            # Process the updated NRPN message
            self._handle_nrpn_complete(self.nrpn_msb, self.nrpn_lsb, self.data_msb, self.data_lsb)
        elif self.rpn_active:
            # Handle RPN increment
            self._handle_rpn_increment()

    def _handle_nrpn_decrement(self):
        """Handle NRPN data decrement (CC 97)."""
        # Decrement current NRPN parameter value by 1
        if self.nrpn_active and self.data_msb_received:
            # Decrement the current parameter value
            current_value = (self.data_msb << 7) | self.data_lsb
            new_value = max(0, current_value - 1)  # Don't go below 0

            # Update data values
            self.data_msb = (new_value >> 7) & 0x7F
            self.data_lsb = new_value & 0x7F

            # Process the updated NRPN message
            self._handle_nrpn_complete(self.nrpn_msb, self.nrpn_lsb, self.data_msb, self.data_lsb)
        elif self.rpn_active:
            # Handle RPN decrement
            self._handle_rpn_decrement()

    def _handle_rpn_increment(self):
        """Handle RPN data increment (CC 96)."""
        # Increment current RPN parameter value by 1
        if self.rpn_active:
            # Get current parameter value (RPN uses single byte values)
            current_value = self.controllers[6] if hasattr(self, "controllers") else 64

            # Increment the parameter value
            new_value = min(127, current_value + 1)

            # Update the data entry value
            self.controllers[6] = new_value

            # Process the updated RPN message
            self._handle_rpn_complete(self.rpn_msb, self.rpn_lsb, new_value)

    def _handle_rpn_decrement(self):
        """Handle RPN data decrement (CC 97)."""
        # Decrement current RPN parameter value by 1
        if self.rpn_active:
            # Get current parameter value (RPN uses single byte values)
            current_value = self.controllers[6] if hasattr(self, "controllers") else 64

            # Decrement the parameter value
            new_value = max(0, current_value - 1)

            # Update the data entry value
            self.controllers[6] = new_value

            # Process the updated RPN message
            self._handle_rpn_complete(self.rpn_msb, self.rpn_lsb, new_value)

    def _handle_reset_all_controllers(self):
        """Handle Reset All Controllers (CC 121)."""
        # Reset all controllers to default values per GM specification
        self.controllers = [0] * 128

        # Set standard defaults
        self.controllers[7] = 100  # Volume
        self.controllers[11] = 127  # Expression
        self.controllers[10] = 64  # Pan center
        self.controllers[64] = 0  # Sustain off

        # Reset channel parameters
        self.volume = 100
        self.expression = 127
        self.pan = 64

    def _handle_local_control(self, value: int):
        """Handle Local Control (CC 122)."""
        # Local control on/off
        self.local_control = value >= 64

    def _handle_omni_off(self):
        """Handle Omni Off (CC 124)."""
        # All Notes Off, Omni Off
        self.all_notes_off()
        self.omni_mode = False

    def _handle_omni_on(self):
        """Handle Omni On (CC 125)."""
        # All Notes Off, Omni On
        self.all_notes_off()
        self.omni_mode = True

    def _handle_mono_on(self, value: int):
        """Handle Mono On (Poly Off) - CC 126."""
        # All Notes Off, Mono On (Poly Off)
        self.all_notes_off()
        self.mono_mode = True
        self.voice_mode = self.VOICE_MODE_MONO

    def _handle_poly_on(self):
        """Handle Poly On (Mono Off) - CC 127."""
        # All Notes Off, Poly On (Mono Off)
        self.all_notes_off()
        self.mono_mode = False
        self.voice_mode = self.VOICE_MODE_POLY

    def _handle_hold2_pedal(self, value: int):
        """Handle Hold 2 pedal controller (69) - additional sustain mechanism."""
        # Hold 2 pedal provides another sustain mechanism independent of sustain pedal
        self.hold2_active = value >= 64

        # Apply to all active notes - trigger hold mechanism
        for note, channel_note in self.active_notes.items():
            if channel_note.is_active():
                for partial in channel_note.partials:
                    if partial.is_active() and partial.amp_envelope:
                        # Hold 2 creates additional sustain independent of main sustain pedal
                        if hasattr(partial.amp_envelope, "hold2"):
                            partial.amp_envelope.hold2 = self.hold2_active

    def _handle_sound_controller_1(self, value: int):
        """Handle Sound Controller 1 (70) - Tremolo depth control."""
        # Map 0-127 to tremolo depth range (0-100%)
        tremolo_depth = value / 127.0

        # Apply to third LFO (used for tremolo/amplitude modulation)
        if self.lfos and len(self.lfos) >= 3:
            self.lfos[2].depth = tremolo_depth
            if hasattr(self.lfos[2], "update_xg_tremolo_depth"):
                self.lfos[2].update_xg_tremolo_depth(value)

    def _handle_portamento_control(self, value: int):
        """Handle Portamento Control (84) - Portamento time control."""
        # Portamento time is the glide time between notes
        # Map 0-127 to portamento time range (0.0 to 10.0 seconds)
        self.portamento_time = (value / 127.0) * 10.0

        # Enable portamento if time is > 0
        self.portamento_active = self.portamento_time > 0 and self.portamento_on

    def _handle_effects_2_depth(self, value: int):
        """Handle Effects 2 Depth (92) - Tremolo effect send level."""
        # Effects 2 Depth typically controls tremolo send level in XG
        # Store the value for use by effect manager
        self.controllers[92] = value

    def _handle_effects_5_depth(self, value: int):
        """Handle Effects 5 Depth (95) - Phaser effect send level."""
        # Effects 5 Depth typically controls phaser send level in XG
        # Store the value for use by effect manager
        self.controllers[95] = value

    def _handle_portamento_time(self, value: int):
        """Handle Portamento Time (CC5) - Portamento response time."""
        # CC5 Portamento Time: 0-127 mapped to time in seconds
        # This sets the fixed time for pitch gliding between notes
        self.portamento_time = value / 127.0 * 10.0  # 0-10 seconds

    def _handle_portamento_on_off(self, value: int):
        """Handle Portamento On/Off (CC65) - Enable/disable portamento."""
        # CC65: Enable/disable portamento (pitch glide between notes)
        self.portamento_on = value >= 64
        # Update active state based on both enable flag and time setting
        self.portamento_active = self.portamento_on and self.portamento_time > 0
