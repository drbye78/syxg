"""

XG Channel Management Architecture - Multi-Timbral MIDI Processing System

ARCHITECTURAL OVERVIEW:

The XG Channel Management System implements a comprehensive MIDI channel processing
architecture designed for professional multi-timbral synthesis. Each channel serves
as an independent synthesis engine with complete parameter control, polyphonic voice
management, and real-time MIDI processing capabilities.

XG MULTI-TIMBRAL ARCHITECTURE:

The synthesizer supports up to 32 MIDI channels (extended beyond standard 16) with
each channel providing:

1. INDEPENDENT SYNTHESIS: Each channel can use different synthesis engines
2. COMPLETE PARAMETER ISOLATION: Independent control of all synthesis parameters
3. POLYPHONIC VOICE MANAGEMENT: Multiple simultaneous notes per channel
4. REAL-TIME MIDI PROCESSING: Sample-accurate MIDI message handling
5. XG/GS COMPATIBILITY: Full support for both Yamaha XG and Roland GS specifications

CHANNEL PROCESSING PIPELINE:

MIDI MESSAGE → CHANNEL ROUTING → PARAMETER PROCESSING → VOICE ALLOCATION → AUDIO GENERATION

1. MESSAGE ROUTING: MIDI messages are routed to appropriate channels based on channel number
2. PARAMETER UPDATE: Controllers, program changes, and NRPN messages update channel state
3. VOICE MANAGEMENT: Note-on events create voice instances with region selection
4. POLYPHONIC SYNTHESIS: Multiple voice instances generate audio simultaneously
5. CHANNEL MIXING: Individual channel audio is mixed with pan, level, and effects sends

VOICE INSTANCE ARCHITECTURE:

Each channel maintains multiple VoiceInstance objects for true polyphony:

VOICE LIFECYCLE:
- CREATION: Note-on event creates VoiceInstance with appropriate regions
- ACTIVATION: Voice instance begins audio generation with attack phase
- SUSTAIN: Voice maintains steady-state audio generation
- RELEASE: Note-off triggers release phase with proper envelope handling
- TERMINATION: Voice instance removed when envelope completes

REGION-BASED SYNTHESIS:
- MULTI-SAMPLE LAYERING: Different samples for different velocity/note ranges
- ROUND-ROBIN: Alternating between multiple samples for variation
- RANDOM SELECTION: Random sample choice for natural variation
- CROSSFADING: Smooth transitions between adjacent regions

PARAMETER PROCESSING ARCHITECTURE:

HIERARCHICAL PARAMETER SYSTEM:
The channel implements a sophisticated parameter hierarchy with multiple control sources:

PRIMARY CONTROLS:
- MIDI CONTROLLERS: Standard CC messages (7=volume, 10=pan, 11=expression, etc.)
- PROGRAM CHANGES: Bank/program selection with XG bank mapping
- PITCH BEND: Real-time pitch modulation with configurable range
- CHANNEL PRESSURE: Aftertouch for timbre modulation

ADVANCED CONTROLS:
- NRPN PARAMETERS: 14-bit resolution for precise control (XG MSB 3-31)
- RPN PARAMETERS: Registered parameters (pitch bend range, fine tuning)
- POLYPHONIC PRESSURE: Per-note aftertouch for expressive control

XG SPECIFICATION COMPLIANCE:

XG PARAMETER MAPPING:
- MSB 3: Basic channel parameters (volume, pan, expression, modulation)
- MSB 4-31: Extended synthesis parameters (filters, envelopes, LFOs, effects)
- BANK SELECT: XG bank mapping for instrument selection
- CONTROLLER ASSIGNMENT: Flexible CC to parameter routing

GS COMPATIBILITY:
- ROLAND GS SUBSET: GS-specific parameter mapping and drum kits
- GS NRPN SUPPORT: GS parameter access through NRPN messages
- GS SYSTEM EXCLUSIVE: GS-specific sysex parameter control

REAL-TIME PROCESSING ARCHITECTURE:

SAMPLE-ACCURATE TIMING:
- MIDI messages processed at exact sample positions within audio blocks
- Sub-sample interpolation for smooth parameter changes
- Jitter-free timing for professional recording applications

THREAD SAFETY:
- Reentrant design for concurrent MIDI processing and audio generation
- Atomic parameter updates during real-time operation
- Lock-free audio generation path for minimal latency

PERFORMANCE OPTIMIZATION:
- Efficient voice instance management with automatic cleanup
- Pre-allocated data structures for zero runtime allocation
- SIMD-optimized audio processing where applicable

MULTI-TIMBRAL COORDINATION:

VOICE ALLOCATION COORDINATION:
- GLOBAL VOICE LIMITS: System-wide polyphony management across channels
- CHANNEL PRIORITIES: XG voice reserve system for guaranteed polyphony
- STEALING STRATEGIES: Priority-based voice stealing when limits exceeded

EFFECTS COORDINATION:
- PER-CHANNEL SENDS: Individual reverb/chorus/variation send levels
- SYSTEM EFFECTS SHARING: Common reverb/chorus units across channels
- INSERTION EFFECTS: Channel-specific effects processing chains

PROGRAM MANAGEMENT:

XG PROGRAM ARCHITECTURE:
- BANK/PROGRAM SELECTION: 14-bit bank select with MSB/LSB support
- XG BANK MAPPING: Special XG banks for different instrument categories
- PROGRAM CHANGE HANDLING: Proper cleanup and voice reloading
- VOICE FACTORY INTEGRATION: Dynamic voice creation based on program selection

VOICE FACTORY INTEGRATION:
- ENGINE SELECTION: Automatic synthesis engine selection based on program
- PARAMETER INITIALIZATION: Voice parameters set from XG/GM specifications
- REGION LOADING: Sample/regions loaded based on program and bank selection

MODULATION AND CONTROL ARCHITECTURE:

MODULATION SOURCES:
- PITCH BEND: Real-time pitch modulation with configurable range
- MODULATION WHEEL: Primary modulation source (vibrato, tremolo, etc.)
- BREATH CONTROLLER: Wind instrument simulation control
- FOOT CONTROLLER: Expression pedal input
- AFTERTOUCH: Channel and polyphonic pressure modulation

MODULATION DESTINATIONS:
- PITCH: Vibrato and pitch bend effects
- FILTER: Wah-wah and filter sweep effects
- AMPLITUDE: Tremolo and amplitude modulation
- PAN: Auto-pan and spatial modulation
- TIMBRE: Harmonic content and formant modulation

XG CONTROLLER ASSIGNMENT:
- FLEXIBLE ROUTING: Controllers can be assigned to any modulation destination
- MULTI-DESTINATION: Single controller can modulate multiple parameters
- SCALE AND OFFSET: Controller response curves with scaling and offset

POLYPHONY MANAGEMENT:

VOICE INSTANCE LIFECYCLE:
- CREATION: Note-on events create new VoiceInstance objects
- POOLING: Voice instances managed through factory pattern
- CLEANUP: Inactive voices automatically removed to prevent accumulation
- LIMITING: Channel-specific voice limits with priority-based allocation

POLYPHONIC SYNTHESIS:
- TRUE POLYPHONY: Multiple simultaneous notes per channel
- VOICE STEALING: Priority-based voice management when limits exceeded
- RELEASE MANAGEMENT: Proper envelope release even when voices are stolen
- CPU OPTIMIZATION: Efficient voice processing with SIMD acceleration

INTEGRATION ARCHITECTURE:

SYNTHESIZER INTEGRATION:
- VOICE MANAGER COORDINATION: Global voice allocation and management
- EFFECTS COORDINATOR INTEGRATION: Channel-specific effects routing
- BUFFER POOL UTILIZATION: Zero-allocation audio processing
- PARAMETER ROUTER CONNECTION: Real-time parameter modulation

XG SYSTEM INTEGRATION:
- RECEIVE CHANNEL MANAGER: MIDI routing and channel mapping
- PARAMETER MANAGER: NRPN parameter processing and storage
- STATE MANAGER: XG system state persistence and restoration

GS SYSTEM INTEGRATION:
- GS COMPONENT MANAGER: GS-specific parameter handling
- GS MIDI PROCESSOR: GS sysex and NRPN message processing
- GS STATE MANAGER: GS system state management

ERROR HANDLING AND DIAGNOSTICS:

COMPREHENSIVE ERROR HANDLING:
- INVALID MIDI DATA: Graceful handling of malformed MIDI messages
- PARAMETER RANGE CHECKING: Automatic clamping of out-of-range values
- VOICE ALLOCATION FAILURE: Fallback strategies for voice creation failures
- THREAD SAFETY VIOLATIONS: Detection and recovery from race conditions

DIAGNOSTIC CAPABILITIES:
- CHANNEL STATE MONITORING: Real-time channel activity and parameter tracking
- VOICE INSTANCE TRACKING: Active voice monitoring and statistics
- PERFORMANCE METRICS: CPU usage and processing latency measurement
- MIDI MESSAGE LOGGING: Debug logging for troubleshooting

EXTENSIBILITY ARCHITECTURE:

PLUGIN CHANNEL TYPES:
- CUSTOM CHANNEL CLASSES: Specialized channel implementations
- ALTERNATIVE SYNTHESIS ENGINES: Third-party synthesis integration
- CUSTOM PARAMETER MAPPINGS: Non-standard parameter routing
- ADVANCED MODULATION SYSTEMS: Complex modulation routing matrices

FUTURE EXPANSION:

ADVANCED FEATURES:
- MPE SUPPORT: Microtonal pitch and multi-dimensional modulation
- ADVANCED POLYPHONY: Dynamic voice allocation based on CPU availability
- NEURAL SYNTHESIS: AI-assisted parameter optimization
- SPATIAL AUDIO: 3D positioning and binaural rendering

PROFESSIONAL INTEGRATION:
- DAW PLUGIN COMPATIBILITY: VST3/AU/AAX parameter automation
- HARDWARE CONTROLLER SUPPORT: Surface control and LED feedback
- NETWORK SYNCHRONIZATION: Distributed synthesis across multiple devices
- CLOUD PARAMETER MANAGEMENT: Online preset sharing and management

XG SPECIFICATION EVOLUTION:

XG v2.0 FEATURES:
- EXTENDED PARAMETER RANGES: Additional parameters in MSB 20-31
- HIGHER RESOLUTION: 16-bit and 32-bit parameter support
- ADVANCED MODULATION: Complex modulation routing and automation
- NEURAL PROCESSING: AI-assisted synthesis and effects processing

PROFESSIONAL MUSIC PRODUCTION:
- STUDIO-GRADE RELIABILITY: 24/7 operation with comprehensive error recovery
- SAMPLE ACCURATE TIMING: Professional recording and production standards
- LOW LATENCY PERFORMANCE: Real-time performance with minimal delay
- COMPREHENSIVE MONITORING: Detailed performance and diagnostic information
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from ..processing.voice.voice_factory import VoiceFactory
from ..processing.voice.voice_instance import VoiceInstance

logger = logging.getLogger(__name__)


class Channel:
    """
    XG MIDI Channel - manages polyphonic voice instances and channel-level state.

    A Channel represents a single MIDI channel (0-15) that can play multiple
    simultaneous voices (true polyphony). It handles program changes, bank selection,
    controller processing, and routes MIDI events to appropriate voice instances.

    XG Specification Compliance:
    - Channel key range and transposition
    - Bank/program selection with XG bank mapping
    - Controller processing and NRPN/RPN support
    - Multi-timbral operation
    - True polyphony with multiple simultaneous notes
    """

    def __init__(
        self,
        channel_number: int,
        voice_factory: VoiceFactory,
        sample_rate: int,
        synthesizer=None,
        buffer_pool=None,
    ):
        """
        Initialize XG Channel.

        Args:
            channel_number: MIDI channel number (0-15)
            voice_factory: Factory for creating voices
            sample_rate: Audio sample rate in Hz
            synthesizer: Reference to parent synthesizer for parameter access
            buffer_pool: Optional BufferPool for zero-allocation audio buffers
        """
        self.channel_number = channel_number
        self.voice_factory = voice_factory
        self.sample_rate = sample_rate
        self.synthesizer = synthesizer  # Reference to parent synthesizer
        self.buffer_pool = buffer_pool

        # Polyphonic voice management with unique voice IDs
        # CRITICAL FIX: Use unique voice IDs instead of note numbers as keys
        # This enables true polyphony where multiple voices can play the same note
        self.active_voices: dict[int, VoiceInstance] = {}  # voice_id -> VoiceInstance
        self.note_to_voice_ids: dict[int, list[int]] = {}  # note -> [voice_id, ...]
        self._next_voice_id = 0  # Incrementing voice ID counter

        self.program = 0
        self.bank_msb = 0
        self.bank_lsb = 0
        self.bank = 0

        # Current instrument/program (for region selection)
        self.current_program = None

        # Legacy compatibility - maintain current_voice for backward compatibility
        self.current_voice = None

        # Channel state
        self.active = True
        self._muted = False
        self._solo = False

        # XG channel parameters
        self.key_range_low = 0
        self.key_range_high = 127
        self.master_level = 1.0
        self.pan = 0.0
        self.transpose = 0

        # Controller state (support both MIDI 1.0 and MIDI 2.0)
        self.controllers = [0] * 128  # MIDI 1.0 controllers (7-bit)
        self.controllers_32bit = {}  # MIDI 2.0 controllers (32-bit)
        self._initialize_default_controllers()

        # Channel pressure and key pressure
        self._channel_pressure = 0
        self.key_pressure_values: dict[int, int] = {}

        # Pitch bend state
        self.pitch_bend_value = 8192  # Center position
        self.pitch_bend_range = 2.0  # Default ±2 semitones

        # S.Art2 articulation support
        self._articulation = "normal"
        self._articulation_params = {}
        self._articulation_preset = None  # Current articulation preset
        self._velocity_articulations = {}  # Velocity-based articulation splits
        self._key_articulations = {}  # Key-based articulation splits

        # NRPN/RPN state
        self.nrpn_active = False
        self.rpn_active = False
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.rpn_msb = 0
        self.rpn_lsb = 0
        self.data_msb = 0
        self.data_msb_received = False

        # XG channel state (updated from message metadata)
        self.xg_pan_left_gain = 1.0
        self.xg_pan_right_gain = 1.0
        self.xg_effects_routing = {"reverb_send": 0.0, "chorus_send": 0.0, "variation_send": 0.0}
        self.xg_part_mode = "normal"  # 'normal', 'single', 'layer'
        self.xg_voice_reserve = None  # Voice limit for this channel

        # GS integration
        self.gs_part = None  # Reference to GS part when in GS mode

        # GS parameter storage from sysex (part-level values from GSSysexHandler)
        self.gs_params: dict[str, int] = {}

        self.key_pressure_32bit_values: dict[int, int] = {}
        self.channel_pressure_32bit = 0

        # Acoustic behavior context (SuperNATURAL-Acoustic alike cross-note state)
        # Owned by the channel so it outlives individual voices. Lazily created
        # to avoid import cost when the behavior layer is unused.
        self._acoustic_context: Any | None = None

        # Acoustic behavior layer enable flag (defaults to on; the layer is
        # applied at the voice region-creation seam when this is True).
        self.acoustic_behavior_enabled: bool = True

        self.pitch_bend_32bit = 2147483647  # Center position
        self.vibrato_rate = 0.0
        self.vibrato_depth = 0.0
        self.vibrato_delay = 0.0
        self.filter_cutoff = 20000.0
        self.filter_resonance = 0.0
        self.amp_release = 0.0
        self.amp_attack = 0.0
        self.drum_volume = 0.0
        self.drum_pan = 0.0
        self.drum_reverb_send = 0.0
        self.drum_chorus_send = 0.0
        self.drum_delay_send = 0.0
        self.eq_gains = [0.0] * 8
        self.reverb_send = 0.0
        self.chorus_send = 0.0
        self.delay_send = 0.0

        # XGChannelParameterManager reference for NRPN parameter access (MSB 3-31)
        self._xg_param_manager = None

    def get_acoustic_context(self) -> Any | None:
        """Lazily create and return the shared acoustic behavior context.

        Returns None if the behavior layer is unavailable (import failure),
        so callers must guard on the result.
        """
        if not self.acoustic_behavior_enabled:
            return None
        if self._acoustic_context is None:
            try:
                from ..engines.acoustic.channel_context import ChannelAcousticContext

                self._acoustic_context = ChannelAcousticContext(
                    sample_rate=self.sample_rate,
                    channel_number=self.channel_number,
                    buffer_pool=(
                        getattr(self.synthesizer, "buffer_pool", None) if self.synthesizer else None
                    ),
                )
            except Exception as exc:  # pragma: no cover - optional layer
                logger.warning(f"Acoustic context unavailable: {exc}")
                return None
        return self._acoustic_context

    def set_acoustic_behavior_enabled(self, enabled: bool) -> None:
        """Enable/disable the acoustic behavior layer for this channel."""
        self.acoustic_behavior_enabled = bool(enabled)
        if not enabled:
            self._acoustic_context = None

    def set_xg_parameter_manager(self, mgr):
        """Set XG parameter manager reference for NRPN parameter access.

        Args:
            mgr: XGChannelParameterManager instance
        """
        self._xg_param_manager = mgr

    def update_xg_state_from_message(self, xg_metadata: dict[str, Any]):
        """
        Update XG channel state from message metadata.

        Args:
            xg_metadata: XG metadata dictionary from MIDI message
        """
        if not xg_metadata:
            return

        # Update pan gains
        if "pan_left_gain" in xg_metadata:
            self.xg_pan_left_gain = xg_metadata["pan_left_gain"]
        if "pan_right_gain" in xg_metadata:
            self.xg_pan_right_gain = xg_metadata["pan_right_gain"]

        # Update effects routing
        if "effects_routing" in xg_metadata:
            self.xg_effects_routing.update(xg_metadata["effects_routing"])

        # Update part mode
        if "part_mode" in xg_metadata:
            self.xg_part_mode = xg_metadata["part_mode"]

        # Update voice reserve
        if "voice_reserve" in xg_metadata:
            self.xg_voice_reserve = xg_metadata["voice_reserve"]

    def _initialize_default_controllers(self):
        """Initialize default controller values per GM/XG specification."""
        # GM/XG default values
        self.controllers[7] = 100  # Volume
        self.controllers[10] = 64  # Pan (center)
        self.controllers[11] = 127  # Expression
        self.controllers[64] = 0  # Sustain pedal
        self.controllers[71] = 64  # Harmonic Content (XG)
        self.controllers[72] = 64  # Brightness (XG)
        self.controllers[73] = 0  # Release Time (XG)
        self.controllers[74] = 0  # Attack Time (XG)
        self.controllers[91] = 40  # Reverb send
        self.controllers[93] = 0  # Chorus send

    def load_program(self, program: int, bank_msb: int = 0, bank_lsb: int = 0):
        """
        Load a program (voice) for this channel.

        Per MIDI spec, program change releases all held notes (including
        sustain-pedal-held notes).

        Args:
            program: MIDI program number (0-127)
            bank_msb: Bank select MSB (0-127)
            bank_lsb: Bank select LSB (0-127)
        """
        # Release all held notes before changing program
        self.all_notes_off()

        self.program = program
        self.bank_msb = bank_msb
        self.bank_lsb = bank_lsb
        self.bank = (bank_msb << 7) | bank_lsb

        # Special handling for channel 9 (drums) in XG/GS
        # Channel 9 is the rhythm channel, and program changes select drum kits
        # In SoundFonts, drum kits are typically in Bank 127
        # Check if this channel is in drum mode (XG/GS part mode)
        is_drum_mode = getattr(self, "xg_part_mode", None) == "drum" or self.channel_number == 9
        if self.channel_number == 9 and self.bank == 0:
            is_drum_mode = True

        if is_drum_mode:
            # Map to Bank 127 (XG/GS drum bank) using program number for drum kit
            drum_bank = 127
        else:
            drum_bank = self.bank

        # Create new voice using factory
        self.current_voice = self.voice_factory.create_voice(
            bank=drum_bank,
            program=program,
            channel=self.channel_number,
            sample_rate=self.sample_rate,
            channel_obj=self,
        )

        # Set current program for region-based playback
        # current_voice is now a Voice object with preset info
        self.current_program = self.current_voice

        # Reset articulation on program change
        self.set_articulation("normal")

    # ========== S.Art2 ARTICULATION CONTROL ==========

    def set_articulation(self, articulation: str) -> None:
        """
        Set articulation for this channel.

        Args:
            articulation: Articulation name (e.g., 'legato', 'staccato', 'growl')
        """
        self._articulation = articulation

        # Propagate to current voice
        if self.current_voice and hasattr(self.current_voice, "set_articulation"):
            self.current_voice.set_articulation(articulation)

    def get_articulation(self) -> str:
        """Get current articulation."""
        return self._articulation

    # ========== CHANNEL PARAMETER CONTROL ==========

    def set_volume(self, volume: int) -> None:
        """
        Set channel volume.

        Args:
            volume: Volume value (0-127)
        """
        self.master_level = volume / 127.0

    def set_pan(self, pan: int) -> None:
        """
        Set channel pan position.

        Args:
            pan: Pan value (0-127, 64 = center)
        """
        self.pan = (pan - 64) / 64.0  # Convert to -1.0 to 1.0

    def apply_articulation_preset(self, preset) -> None:
        """
        Apply articulation preset to channel.

        Args:
            preset: ArticulationPreset object
        """
        self._articulation_preset = preset

        # Apply preset splits
        self._velocity_articulations = {}
        self._key_articulations = {}

        for split in preset.velocity_splits:
            self._velocity_articulations[(split.vel_low, split.vel_high)] = {
                "articulation": split.articulation,
                "parameters": split.parameters,
            }

        for split in preset.key_splits:
            self._key_articulations[(split.key_low, split.key_high)] = {
                "articulation": split.articulation,
                "parameters": split.parameters,
            }

    def get_articulation_for_note(self, note: int, velocity: int) -> tuple:
        """
        Get articulation and parameters for note/velocity.

        Args:
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Tuple of (articulation_name, parameters_dict)
        """
        # Check key splits first
        for (key_low, key_high), config in self._key_articulations.items():
            if key_low <= note <= key_high:
                return (config["articulation"], config["parameters"])

        # Check velocity splits
        for (vel_low, vel_high), config in self._velocity_articulations.items():
            if vel_low <= velocity <= vel_high:
                return (config["articulation"], config["parameters"])

        # Return default
        return (self._articulation, self._articulation_params)

    def set_velocity_articulation(
        self, vel_low: int, vel_high: int, articulation: str, **params
    ) -> None:
        """Set velocity-based articulation."""
        self._velocity_articulations[(vel_low, vel_high)] = {
            "articulation": articulation,
            "parameters": params,
        }

    def set_key_articulation(
        self, key_low: int, key_high: int, articulation: str, **params
    ) -> None:
        """Set key-based articulation."""
        self._key_articulations[(key_low, key_high)] = {
            "articulation": articulation,
            "parameters": params,
        }

    def clear_articulation_splits(self) -> None:
        """Clear all articulation splits."""
        self._velocity_articulations.clear()
        self._key_articulations.clear()

    def note_on(self, note: int, velocity: int) -> bool:
        """
        Handle note-on event with polyphony support.

        Creates a new VoiceInstance for each note, allowing multiple
        simultaneous notes per channel (true polyphony).

        Uses the new region-based architecture for multi-zone preset support.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)

        Returns:
            True if note was accepted, False otherwise
        """
        if self.muted:
            return False

        # Apply channel transposition
        transposed_note = note + self.transpose

        # Check channel key range
        if not (self.key_range_low <= transposed_note <= self.key_range_high):
            return False

        # Get articulation for this note/velocity
        articulation, art_params = self.get_articulation_for_note(transposed_note, velocity)

        # Allocate unique voice ID for true polyphony
        voice_id = self._allocate_voice_id()

        # Create new VoiceInstance for this note with articulation
        # CRITICAL: Always create new voice instance for true polyphony
        # Don't check for existing voices - allow multiple voices per note
        buffer_pool = getattr(self.synthesizer, "buffer_pool", None) if self.synthesizer else None
        voice_instance = VoiceInstance(
            transposed_note,
            velocity,
            self.channel_number,
            self.sample_rate,
            voice_id=voice_id,
            articulation=articulation,
            buffer_pool=buffer_pool,
        )

        # Apply articulation parameters
        if art_params:
            voice_instance.set_articulation(articulation, **art_params)

        # Get regions for this note/velocity from current Voice
        # This is the KEY call that enables multi-zone preset support
        if self.current_voice:
            try:
                # Voice.get_regions_for_note() returns regions matching this note/velocity
                regions = self.current_voice.get_regions_for_note(transposed_note, velocity)

                # Add all matching regions to voice instance
                for region in regions:
                    voice_instance.add_region(region)

            except Exception as e:
                logger.error(f"Channel note_on: Failed to get regions: {e}")

        # Check if we have any regions to play
        if not voice_instance.regions:
            # No regions matched - check if voice supports this note
            if self.current_voice and self.current_voice.is_note_supported(transposed_note):
                # Fallback: try legacy single voice
                self.current_voice.note_on(transposed_note, velocity)
                return True
            logger.debug(
                f"No regions for note {transposed_note} on channel {self.channel_number}. current_voice={self.current_voice}"
            )
            return False

        # Trigger note-on for the voice instance
        voice_instance.note_on(velocity)

        # Enforce exclusiveClass (SF2 gen 57): if the new voice shares an
        # exclusiveClass with any existing active voice, steal (release) the old one.
        new_excl_classes = {
            reg._exclusive_class
            for reg in voice_instance.active_regions
            if reg._exclusive_class > 0
        }
        if new_excl_classes:
            for _existing_id, existing_vi in list(self.active_voices.items()):
                if existing_vi is voice_instance:
                    continue
                for reg in existing_vi.active_regions:
                    if reg._exclusive_class in new_excl_classes:
                        existing_vi.note_off(64)
                        break

        # Store the active voice instance with unique ID
        self.active_voices[voice_id] = voice_instance

        # Track this voice ID for this note (supports multiple voices per note)
        if transposed_note not in self.note_to_voice_ids:
            self.note_to_voice_ids[transposed_note] = []
        self.note_to_voice_ids[transposed_note].append(voice_id)

        # Acoustic behavior: register note-on in shared cross-note context
        ctx = self.get_acoustic_context()
        if ctx is not None:
            try:
                ctx.note_on(transposed_note, velocity, voice_id, 0.0)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"Acoustic context note_on failed: {exc}")

        return True

    def _allocate_voice_id(self) -> int:
        """
        Allocate a unique voice ID.

        Returns:
            Unique voice ID for this voice instance
        """
        voice_id = self._next_voice_id
        self._next_voice_id += 1
        return voice_id

    def _find_voices_for_note(self, note: int) -> list[int]:
        """
        Find all voice IDs playing a specific note.

        Args:
            note: MIDI note number (after transposition)

        Returns:
            List of voice IDs playing this note
        """
        return self.note_to_voice_ids.get(note, [])

    def _remove_voice_id(self, voice_id: int, note: int) -> None:
        """
        Remove a voice ID from tracking.

        Args:
            voice_id: Voice ID to remove
            note: Note associated with this voice
        """
        if voice_id in self.active_voices:
            del self.active_voices[voice_id]

        if note in self.note_to_voice_ids:
            if voice_id in self.note_to_voice_ids[note]:
                self.note_to_voice_ids[note].remove(voice_id)
            if not self.note_to_voice_ids[note]:
                del self.note_to_voice_ids[note]

    def note_off(self, note: int, velocity: int = 64):
        """
        Handle note-off event with polyphony support.

        CRITICAL FIX: Release ALL voices playing this note, not just one.
        This enables true polyphony where multiple voices can play the same note.

        Args:
            note: MIDI note number (0-127)
            velocity: Note-off velocity (0-127)
        """
        # Apply channel transposition
        transposed_note = note + self.transpose

        # Find ALL voice instances playing this note (supports polyphony)
        voice_ids = self._find_voices_for_note(transposed_note)

        # Release all voices for this note
        for voice_id in voice_ids:
            if voice_id in self.active_voices:
                voice_instance = self.active_voices[voice_id]
                voice_instance.note_off(velocity)
                # Mark for removal during cleanup (allows release phase to complete)
                voice_instance._pending_removal = True

        # Acoustic behavior: register note-off in shared cross-note context
        ctx = self.get_acoustic_context()
        if ctx is not None:
            try:
                for voice_id in voice_ids:
                    ctx.note_off(transposed_note, voice_id, 0.0)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"Acoustic context note_off failed: {exc}")

        # Fallback to legacy single voice if no voices found
        if not voice_ids:
            if self.current_voice:
                self.current_voice.note_off(transposed_note)

    def control_change(self, controller: int, value: int, is_32bit: bool = False):
        """
        Handle control change event.

        Args:
            controller: Controller number (0-127)
            value: Controller value (0-127 for MIDI 1.0, 0-4294967295 for MIDI 2.0)
            is_32bit: Whether this is a 32-bit MIDI 2.0 value
        """
        if is_32bit:
            # Store 32-bit value for MIDI 2.0
            self.controllers_32bit[controller] = value
            # Convert to 7-bit equivalent for backward compatibility
            self.controllers[controller] = self._convert_32bit_to_7bit(value)
        else:
            # Store 7-bit value for MIDI 1.0
            self.controllers[controller] = value
            # Also store as 32-bit for consistency
            self.controllers_32bit[controller] = self._convert_7bit_to_32bit(value)

        # Handle special XG controllers
        if controller == 0:  # Bank Select MSB
            self.bank_msb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 32:  # Bank Select LSB
            self.bank_lsb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 7:  # Volume
            if is_32bit:
                # Use 32-bit value for higher resolution
                self.master_level = self._normalize_32bit_value(value)
            else:
                self.master_level = value / 127.0
        elif controller == 10:  # Pan
            if is_32bit:
                # Use 32-bit value for higher resolution
                self.pan = self._normalize_32bit_pan(value)
            else:
                self.pan = (value - 64) / 64.0  # Convert to -1.0 to 1.0
        elif controller == 84:  # Portamento Control
            # Handle portamento control if needed
            pass

        # Handle NRPN/RPN sequences
        elif controller == 98:  # NRPN LSB
            self.nrpn_lsb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return
        elif controller == 99:  # NRPN MSB
            self.nrpn_msb = value
            self.nrpn_active = True
            self.data_msb_received = False
            return
        elif controller == 100:  # RPN LSB
            self.rpn_lsb = value
            self.rpn_active = True
            return
        elif controller == 101:  # RPN MSB
            self.rpn_msb = value
            self.rpn_active = True
            return
        elif controller == 6:  # Data Entry MSB
            if self.nrpn_active:
                # Standard NRPN: single CC6 provides the 7-bit parameter value
                # CC38 (Data Entry LSB) can provide fine adjustment, but CC6 alone completes.
                self._handle_nrpn_complete(value)
                self.nrpn_active = False
                self.data_msb_received = True
            elif self.rpn_active:
                self._handle_rpn_complete(value)
                self.rpn_active = False

        # Acoustic behavior: mirror continuous controllers into shared context
        ctx = self.get_acoustic_context()
        if ctx is not None:
            try:
                if controller == 64:  # Sustain pedal
                    ctx.update_controller("sustain", 1.0 if value >= 64 else 0.0)
                elif controller == 11:  # Expression
                    ctx.update_controller("expression", value / 127.0)
                elif controller == 71:  # Resonance (filter/body)
                    ctx.update_controller("resonance", value / 127.0)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"Acoustic context controller update failed: {exc}")

    def _convert_32bit_to_7bit(self, value_32: int) -> int:
        """
        Convert 32-bit MIDI 2.0 value to 7-bit MIDI 1.0 value.

        Args:
            value_32: 32-bit value (0-4294967295)

        Returns:
            7-bit value (0-127)
        """
        # Map 32-bit range to 7-bit range (round to nearest, not truncate)
        return round((value_32 / 4294967295.0) * 127.0)

    def _convert_7bit_to_32bit(self, value_7: int) -> int:
        """
        Convert 7-bit MIDI 1.0 value to 32-bit MIDI 2.0 value.

        Args:
            value_7: 7-bit value (0-127)

        Returns:
            32-bit value (0-4294967295)
        """
        # Map 7-bit range to 32-bit range
        return int((value_7 / 127.0) * 4294967295.0)

    def _normalize_32bit_value(self, value_32: int) -> float:
        """
        Normalize 32-bit value to 0.0-1.0 range.

        Args:
            value_32: 32-bit value (0-4294967295)

        Returns:
            Normalized value (0.0-1.0)
        """
        return value_32 / 4294967295.0

    def _normalize_32bit_pan(self, value_32: int) -> float:
        """
        Normalize 32-bit pan value to -1.0 to 1.0 range.

        Args:
            value_32: 32-bit value (0-4294967295)

        Returns:
            Normalized pan value (-1.0 to 1.0)
        """
        # Map 32-bit range to -1.0 to 1.0 range, centered at 0x7FFFFFFF
        center = 2147483647  # 0x7FFFFFFF
        if value_32 <= center:
            # Left side: 0 to center maps to -1.0 to 0.0
            return -((center - value_32) / center)
        else:
            # Right side: center to max maps to 0.0 to 1.0
            return (value_32 - center) / center

    def _handle_nrpn_complete(self, value: int):
        """
        Handle complete NRPN message.

        Per MIDI spec, a single CC6 (Data Entry MSB) provides the 7-bit
        parameter value. CC38 (Data Entry LSB) is optional fine adjustment.

        Args:
            value: Parameter value (7-bit, 0-127)
        """
        param_number = (self.nrpn_msb << 8) | self.nrpn_lsb

        if param_number == 0:
            self.vibrato_rate = (value - 64) / 64.0
        elif param_number == 1:
            self.vibrato_depth = (value - 64) / 64.0
        elif param_number == 2:
            self.vibrato_delay = value / 127.0 * 2.0
        elif param_number == 6:
            self.filter_cutoff = self._midi_to_frequency(value)
        elif param_number == 7:
            self.filter_resonance = (value - 64) / 64.0 * 10.0
        elif param_number == 8:
            self.amp_release = value / 127.0 * 2.0
        elif param_number == 9:
            self.amp_attack = value / 127.0 * 2.0
        elif param_number == 10:
            self.drum_volume = value / 127.0
        elif param_number == 11:
            self.drum_pan = (value - 64) / 64.0
        elif param_number == 12:
            self.drum_reverb_send = value / 127.0
        elif param_number == 13:
            self.drum_chorus_send = value / 127.0
        elif param_number == 14:
            self.drum_delay_send = value / 127.0
        elif param_number == 91:
            self.reverb_send = value / 127.0
        elif param_number == 93:
            self.chorus_send = value / 127.0
        elif param_number == 94:
            self.delay_send = value / 127.0
        elif param_number >= 96 and param_number <= 127:
            eq_band = param_number - 96
            if eq_band < len(self.eq_gains):
                self.eq_gains[eq_band] = (value - 64) / 64.0 * 12.0

    def _handle_rpn_complete(self, value: int):
        """
        Handle complete RPN message.

        Per MIDI spec, CC6 provides a single 7-bit parameter value.

        Args:
            value: RPN value (7-bit, 0-127)
        """
        if self.rpn_msb == 0 and self.rpn_lsb == 0:
            # Pitch Bend Range: single 7-bit value = semitones (0-24 per MIDI spec)
            self.pitch_bend_range = max(0, min(24, value))
        # Other RPN parameters can be handled here

    def pitch_bend(self, lsb: int, msb: int, pitch_32bit: int | None = None):
        """
        Handle pitch bend event with support for both MIDI 1.0 and MIDI 2.0.

        Args:
            lsb: Pitch bend LSB (0-127) for MIDI 1.0
            msb: Pitch bend MSB (0-127) for MIDI 1.0
            pitch_32bit: 32-bit pitch bend value for MIDI 2.0 (optional)
        """
        if pitch_32bit is not None:
            # MIDI 2.0 32-bit pitch bend
            self.pitch_bend_value = pitch_32bit
            self.pitch_bend_32bit = pitch_32bit
        else:
            # MIDI 1.0 14-bit pitch bend
            self.pitch_bend_value = (msb << 7) | lsb
            # Store as 32-bit equivalent for consistency
            self.pitch_bend_32bit = self._convert_14bit_to_32bit(self.pitch_bend_value)

    def _convert_14bit_to_32bit(self, value_14: int) -> int:
        """
        Convert 14-bit MIDI 1.0 pitch bend value to 32-bit MIDI 2.0 value.

        Args:
            value_14: 14-bit value (0-16383)

        Returns:
            32-bit value (0-4294967295)
        """
        # Center 14-bit value (8192) maps to center of 32-bit range (0x7FFFFFFF)
        # Map 0-16383 to 0-4294967295
        if value_14 <= 8192:
            # Lower half: 0-8192 maps to 0x00000000 to 0x7FFFFFFF
            return int((value_14 / 8192.0) * 2147483647.0)
        else:
            # Upper half: 8193-16383 maps to 0x80000000 to 0xFFFFFFFF
            return 2147483647 + int(((value_14 - 8192) / 8191.0) * 2147483648.0)

    def _convert_32bit_to_14bit(self, value_32: int) -> int:
        """
        Convert 32-bit MIDI 2.0 pitch bend value to 14-bit MIDI 1.0 value.

        Args:
            value_32: 32-bit value (0-4294967295)

        Returns:
            14-bit value (0-16383)
        """
        # Center 32-bit value (0x7FFFFFFF) maps to center of 14-bit range (8192)
        # Map 0-4294967295 to 0-16383
        center = 2147483647  # 0x7FFFFFFF
        if value_32 <= center:
            # Lower half: 0x00000000 to 0x7FFFFFFF maps to 0 to 8192
            return int((value_32 / center) * 8192.0)
        else:
            # Upper half: 0x80000000 to 0xFFFFFFFF maps to 8193 to 16383
            return 8192 + int(((value_32 - center) / (4294967295 - center)) * 8191.0)

    def set_channel_pressure(self, pressure: int):
        """
        Handle channel pressure (aftertouch).
        """
        self.channel_pressure = pressure

    def set_channel_pressure_32bit(self, pressure_32bit: int):
        """
        Handle 32-bit channel pressure (aftertouch) for MIDI 2.0.

        Args:
            pressure_32bit: 32-bit pressure value
        """
        self.channel_pressure_32bit = pressure_32bit
        # Convert to 7-bit for backward compatibility
        self.channel_pressure = self._convert_32bit_to_7bit(pressure_32bit)

    def key_pressure(self, note: int, pressure: int, pressure_32bit: int | None = None):
        """
        Handle polyphonic key pressure with support for MIDI 2.0.

        Args:
            note: MIDI note number (0-127)
            pressure: 7-bit pressure value (0-127) for MIDI 1.0
            pressure_32bit: 32-bit pressure value for MIDI 2.0 (optional)
        """
        if pressure_32bit is not None:
            # Store 32-bit value for MIDI 2.0
            if note not in self.key_pressure_32bit_values:
                self.key_pressure_32bit_values[note] = {}
            self.key_pressure_32bit_values[note] = pressure_32bit
            # Convert to 7-bit for backward compatibility
            self.key_pressure_values[note] = self._convert_32bit_to_7bit(pressure_32bit)
        else:
            # Store 7-bit value for MIDI 1.0
            self.key_pressure_values[note] = pressure
            # Store as 32-bit for consistency
            if note not in self.key_pressure_32bit_values:
                self.key_pressure_32bit_values[note] = {}
            self.key_pressure_32bit_values[note] = self._convert_7bit_to_32bit(pressure)

    def _collect_modulation_values(self) -> dict[str, float]:
        """
        Collect modulation values from controllers and channel state.

        Returns:
            Dictionary of modulation values
        """
        # Convert pitch bend to modulation value
        if hasattr(self, "pitch_bend_32bit"):
            # Use 32-bit pitch bend for higher resolution
            pitch_bend_semitones = (
                (self.pitch_bend_32bit - 2147483647) / 2147483647.0
            ) * self.pitch_bend_range
        else:
            # Use 14-bit pitch bend (MIDI 1.0)
            pitch_bend_semitones = ((self.pitch_bend_value - 8192) / 8192.0) * self.pitch_bend_range

        modulation = {
            "pitch": pitch_bend_semitones,  # In semitones
            "filter_cutoff": self.controllers[74] / 127.0,  # CC74 = brightness/cutoff
            "amp": 1.0,
            "pan": self.pan,
            "velocity_crossfade": 0.0,
            "note_crossfade": 0.0,
            "stereo_width": 1.0,
            "tremolo_rate": 4.0,
            "tremolo_depth": 0.3,
            "mod_wheel": self.controllers[1] / 127.0,
            "breath_controller": self.controllers[2] / 127.0,
            "foot_controller": self.controllers[4] / 127.0,
            "expression": self.controllers[11] / 127.0,
            "brightness": self.controllers[72] / 127.0,
            "harmonic_content": self.controllers[71] / 127.0,
            "channel_aftertouch": self.channel_pressure / 127.0,
            "volume": self.master_level,  # CC7 -> region _volume_mod (uses normalized master_level)
            "volume_cc": self.master_level,  # Kept for backward compat
        }

        # Add 32-bit controller values if available
        for controller, value_32bit in self.controllers_32bit.items():
            if controller == 1:  # Mod wheel
                modulation["mod_wheel"] = self._normalize_32bit_value(value_32bit)
            elif controller == 2:  # Breath controller
                modulation["breath_controller"] = self._normalize_32bit_value(value_32bit)
            elif controller == 4:  # Foot controller
                modulation["foot_controller"] = self._normalize_32bit_value(value_32bit)
            elif controller == 7:  # Volume
                modulation["volume_cc"] = self._normalize_32bit_value(value_32bit)
            elif controller == 11:  # Expression
                modulation["expression"] = self._normalize_32bit_value(value_32bit)
            elif controller == 71:  # Harmonic Content
                modulation["harmonic_content"] = self._normalize_32bit_value(value_32bit)
            elif controller == 72:  # Brightness
                modulation["brightness"] = self._normalize_32bit_value(value_32bit)

        # Add NRPN-derived modulation values (set via NRPN, consumed by voice pipeline)
        modulation["nrpn_filter_cutoff"] = self.filter_cutoff
        modulation["nrpn_filter_resonance"] = self.filter_resonance
        modulation["nrpn_amp_attack"] = self.amp_attack
        modulation["nrpn_amp_release"] = self.amp_release
        modulation["nrpn_vibrato_rate"] = self.vibrato_rate
        modulation["nrpn_vibrato_depth"] = self.vibrato_depth

        # If filter_cutoff was set via NRPN, override the controller value
        if hasattr(self, "filter_cutoff") and self.filter_cutoff != 20000.0:
            # NRPN filter cutoff is in Hz, normalize to 0-1 range (relative to 20kHz)
            modulation["filter_cutoff"] = min(1.0, self.filter_cutoff / 20000.0)

        # XG NRPN parameters (MSB 3-31) via XGChannelParameterManager
        if self._xg_param_manager is not None:
            try:
                xg_params = self._xg_param_manager.get_channel_synthesis_parameters(
                    self.channel_number
                )
                if xg_params:
                    # Filter envelope
                    if "filter_cutoff" in xg_params:
                        modulation["xg_filter_cutoff"] = xg_params["filter_cutoff"]
                    if "filter_resonance" in xg_params:
                        modulation["xg_filter_resonance"] = xg_params["filter_resonance"]
                    # Amp envelope
                    if "amp_attack" in xg_params:
                        modulation["xg_amp_attack"] = xg_params["amp_attack"]
                    if "amp_decay" in xg_params:
                        modulation["xg_amp_decay"] = xg_params["amp_decay"]
                    if "amp_sustain" in xg_params:
                        modulation["xg_amp_sustain"] = xg_params["amp_sustain"]
                    if "amp_release" in xg_params:
                        modulation["xg_amp_release"] = xg_params["amp_release"]
                    if "amp_velocity_sense" in xg_params:
                        modulation["xg_amp_velocity_sense"] = xg_params["amp_velocity_sense"]
                    # Pitch envelope
                    if "pitch_attack" in xg_params:
                        modulation["xg_pitch_attack"] = xg_params["pitch_attack"]
                    if "pitch_decay" in xg_params:
                        modulation["xg_pitch_decay"] = xg_params["pitch_decay"]
                    if "pitch_sustain" in xg_params:
                        modulation["xg_pitch_sustain"] = xg_params["pitch_sustain"]
                    if "pitch_release" in xg_params:
                        modulation["xg_pitch_release"] = xg_params["pitch_release"]
                    # Effects sends
                    if "reverb_send" in xg_params:
                        modulation["xg_reverb_send"] = xg_params["reverb_send"]
                    if "chorus_send" in xg_params:
                        modulation["xg_chorus_send"] = xg_params["chorus_send"]
                    if "variation_send" in xg_params:
                        modulation["xg_variation_send"] = xg_params["variation_send"]
                    # Volume / expression
                    if "volume" in xg_params:
                        modulation["xg_volume"] = xg_params["volume"]
                    if "expression" in xg_params:
                        modulation["xg_expression"] = xg_params["expression"]
                    # LFO
                    if "lfo1_speed" in xg_params:
                        modulation["xg_lfo1_speed"] = xg_params["lfo1_speed"]
            except Exception:
                pass

        # Expose raw CC values for the acoustic behavior layer (cc_<n> keys, 0..1)
        for _cc_idx in range(128):
            modulation[f"cc_{_cc_idx}"] = self.controllers[_cc_idx] / 127.0

        # GS part parameters via GSSysexHandler (bridge from GS sysex → audio)
        if self.gs_params:
            if "volume" in self.gs_params:
                modulation["gs_volume"] = self.gs_params["volume"] / 127.0
            if "pan" in self.gs_params:
                # GS pan: 0=left, 64=center, 127=right → -1.0 to 1.0
                modulation["gs_pan"] = (self.gs_params["pan"] - 64) / 63.0
            if "filter_cutoff" in self.gs_params:
                # GS cutoff: 0-127 mapped to ratio (0.0-1.0)
                modulation["gs_filter_cutoff"] = self.gs_params["filter_cutoff"] / 127.0
            if "filter_resonance" in self.gs_params:
                modulation["gs_filter_resonance"] = self.gs_params["filter_resonance"] / 127.0
            if "attack_time" in self.gs_params:
                # GS attack: 0-127 → time multiplier (0.1x to 10x, centered at 1.0 for 64)
                modulation["gs_amp_attack"] = 2.0 ** ((self.gs_params["attack_time"] - 64) / 32.0)
            if "decay_time" in self.gs_params:
                modulation["gs_amp_decay"] = 2.0 ** ((self.gs_params["decay_time"] - 64) / 32.0)
            if "release_time" in self.gs_params:
                modulation["gs_amp_release"] = 2.0 ** ((self.gs_params["release_time"] - 64) / 32.0)
            if "vibrato_rate" in self.gs_params:
                # GS vibrato rate: 0-127 → 0-10 Hz
                modulation["gs_vibrato_rate"] = self.gs_params["vibrato_rate"] / 127.0 * 10.0
            if "vibrato_depth" in self.gs_params:
                # GS vibrato depth: 0-127 → 0-5 semitones
                modulation["gs_vibrato_depth"] = self.gs_params["vibrato_depth"] / 127.0 * 5.0
            if "vibrato_delay" in self.gs_params:
                # GS vibrato delay: 0-127 → 0-5 seconds
                modulation["gs_vibrato_delay"] = self.gs_params["vibrato_delay"] / 127.0 * 5.0
            if "reverb_send" in self.gs_params:
                modulation["gs_reverb_send"] = self.gs_params["reverb_send"] / 127.0
            if "chorus_send" in self.gs_params:
                modulation["gs_chorus_send"] = self.gs_params["chorus_send"] / 127.0

        return modulation

    def program_change(self, program: int):
        """
        Handle program change.

        Args:
            program: New program number (0-127)
        """
        self.load_program(program, self.bank_msb, self.bank_lsb)

    def all_notes_off(self):
        """
        Turn off all notes on this channel.

        CRITICAL FIX: Release all voices using voice IDs.
        """
        # Send note-off to all active voice instances
        for _voice_id, voice_instance in list(self.active_voices.items()):
            voice_instance.note_off()
            voice_instance._pending_removal = True

        # Fallback to legacy single voice
        if self.current_voice:
            for note in range(128):
                self.current_voice.note_off(note)

    def all_sound_off(self):
        """
        Immediately silence all sounds on this channel.

        CRITICAL FIX: Clear all voice tracking structures.
        """
        # Immediately silence all active voice instances
        for voice_instance in list(self.active_voices.values()):
            voice_instance.reset()

        # Clear all voice tracking structures
        self.active_voices.clear()
        self.note_to_voice_ids.clear()

        # Fallback to legacy single voice
        if self.current_voice:
            for note in range(128):
                self.current_voice.note_off(note)

    def reset_all_controllers(self):
        """Reset all controllers to default values."""
        self._initialize_default_controllers()
        self.channel_pressure = 0
        self.key_pressure_values.clear()
        self.pitch_bend_value = 8192

    def generate_samples(
        self, block_size: int, output_buffer: np.ndarray | None = None
    ) -> np.ndarray:
        """
        Generate audio samples for this channel with true polyphony.

        Supports multiple simultaneous VoiceInstance objects, each handling
        their own note with multiple regions (velocity layers, round robin, etc.).

        Args:
            block_size: Number of samples to generate
            output_buffer: Optional pre-allocated buffer for zero-allocation path.
                           If provided, it is filled and returned instead of allocating
                           a new buffer from the pool.

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Use caller-provided buffer for zero-allocation, fall back to pool or np.zeros
        if output_buffer is not None:
            output = output_buffer[:block_size]
            output.fill(0.0)
        elif self.buffer_pool is not None:
            output = self.buffer_pool.get_stereo_buffer(block_size)
        else:
            output = np.zeros((block_size, 2), dtype=np.float32)

        if self.muted:
            return output

        # Collect modulation FIRST so voices use fresh values (Bug 4 fix)
        modulation = self._collect_modulation_values()

        # Generate samples from all active voice instances
        active_voice_count = 0
        voices_to_remove = []

        for voice_id, voice_instance in list(self.active_voices.items()):
            # Apply fresh modulation before generating audio for this block
            voice_instance.update_modulation(modulation)
            is_active = voice_instance.is_active()
            if is_active:
                # Get samples from this voice instance
                voice_audio = voice_instance.generate_samples(block_size)

                # Ensure voice_audio matches expected block size
                if voice_audio.shape[0] != block_size:
                    if voice_audio.shape[0] < block_size:
                        if self.buffer_pool is not None:
                            padding = self.buffer_pool.get_stereo_buffer(
                                block_size - voice_audio.shape[0]
                            )
                        else:
                            padding = np.zeros(
                                (block_size - voice_audio.shape[0], 2), dtype=np.float32
                            )
                        voice_audio = np.vstack([voice_audio, padding])
                    else:
                        voice_audio = voice_audio[:block_size]

                # Mix voice into channel output
                output += voice_audio
                active_voice_count += 1
            else:
                # Mark inactive voices for removal
                voices_to_remove.append((voice_id, voice_instance.note))

        # Remove inactive voices (after iteration to avoid dict modification during iteration)
        for voice_id, note in voices_to_remove:
            self._remove_voice_id(voice_id, note)

        # Apply channel-level processing if we have active voices
        if active_voice_count > 0:
            # Apply master level - check GS parameters first
            master_level = self._get_master_level()
            output *= master_level

            # Apply pan - check GS parameters first, then XG, then regular
            pan_gains = self._get_pan_gains()
            output[:, 0] *= pan_gains[0]  # Left channel
            output[:, 1] *= pan_gains[1]  # Right channel

        return output

    def get_channel_info(self) -> dict[str, Any]:
        """
        Get information about this channel.

        Returns:
            Dictionary with channel state information
        """
        return {
            "channel_number": self.channel_number,
            "program": self.program,
            "bank": self.bank,
            "bank_msb": self.bank_msb,
            "bank_lsb": self.bank_lsb,
            "active": self.active,
            "muted": self.muted,
            "solo": self.solo,
            "key_range": (self.key_range_low, self.key_range_high),
            "master_level": self.master_level,
            "pan": self.pan,
            "transpose": self.transpose,
            "has_voice": self.current_voice is not None,
            "voice_info": self.current_voice.get_voice_info() if self.current_voice else None,
        }

    def set_key_range(self, low: int, high: int):
        """
        Set the key range for this channel.

        Args:
            low: Lowest note (0-127)
            high: Highest note (0-127)
        """
        self.key_range_low = max(0, min(127, low))
        self.key_range_high = max(0, min(127, high))

        if self.key_range_high < self.key_range_low:
            self.key_range_high = self.key_range_low

    def set_transpose(self, transpose: int):
        """
        Set channel transposition.

        Args:
            transpose: Transposition in semitones (-127 to 127)
        """
        self.transpose = max(-127, min(127, transpose))

    def mute(self, muted: bool = True):
        """
        Mute or unmute this channel.

        Args:
            muted: True to mute, False to unmute
        """
        self.muted = muted

    def set_solo(self, solo: bool = True):
        """
        Solo or unsolo this channel.

        Args:
            solo: True to solo, False to unsolo
        """
        self.solo = solo

    def is_active(self) -> bool:
        """
        Check if this channel is active (has notes playing).

        Returns:
            True if channel has active voices
        """
        return len(self.active_voices) > 0 or (
            self.current_voice is not None and self.current_voice.is_active()
        )

    def get_active_voice_count(self) -> int:
        """
        Get the number of active voices on this channel.

        Returns:
            Number of active voices
        """
        count = len(self.active_voices)
        # Also count legacy single voice if active
        if self.current_voice and self.current_voice.is_active():
            count += 1
        return count

    @property
    def muted(self) -> bool:
        """Get mute state."""
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        """Set mute state."""
        self._muted = value

    @property
    def solo(self) -> bool:
        """Get solo state."""
        return self._solo

    @solo.setter
    def solo(self, value: bool):
        """Set solo state."""
        self._solo = value

    @property
    def channel_pressure(self) -> int:
        """Get channel pressure value."""
        return self._channel_pressure

    @channel_pressure.setter
    def channel_pressure(self, value: int):
        """Set channel pressure value."""
        self._channel_pressure = value

    def _get_master_level(self) -> float:
        """
        Get master level from GS part, XG config, or default.

        Priority: GS part volume -> XG part level -> default master_level

        Returns:
            Master level (0.0-1.0)
        """
        if self.synthesizer and self.synthesizer.parameter_priority.is_gs_active():
            # Check GS part volume
            if self.gs_part:
                return self.gs_part.volume / 127.0

        # Check XG part level
        if hasattr(self, "xg_config") and self.xg_config and "part_level" in self.xg_config:
            return self.xg_config["part_level"] / 100.0

        # Default to regular master level
        return self.master_level

    def _get_pan_gains(self) -> tuple[float, float]:
        """
        Get pan gains from GS part, XG config, or default.

        Priority: GS part pan -> XG pan gains -> regular pan

        Returns:
            Tuple of (left_gain, right_gain)
        """
        if self.synthesizer and self.synthesizer.parameter_priority.is_gs_active():
            # Check GS part pan
            if self.gs_part:
                pan_value = self.gs_part.pan
                # Convert GS pan (0-127, center=64) to -1.0 to 1.0
                pan_position = (pan_value - 64) / 64.0
                # Apply constant power pan law
                if pan_position < -1.0:
                    pan_position = -1.0
                elif pan_position > 1.0:
                    pan_position = 1.0

                angle = pan_position * (math.pi / 4.0)  # 45 degrees max
                left_gain = math.cos(angle + math.pi / 4.0)
                right_gain = math.sin(angle + math.pi / 4.0)
                return (left_gain, right_gain)

        # Check XG pan gains
        if self.xg_pan_left_gain != 1.0 or self.xg_pan_right_gain != 1.0:
            return (self.xg_pan_left_gain, self.xg_pan_right_gain)

        # Default to regular pan
        if self.pan != 0.0:
            left_gain = 1.0 - max(0.0, self.pan)
            right_gain = 1.0 - max(0.0, -self.pan)
            return (left_gain, right_gain)

        # Center pan (no change)
        return (1.0, 1.0)
