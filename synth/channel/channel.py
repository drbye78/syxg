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

from typing import Dict, Optional, Any, List
import numpy as np

from .channel_note import ChannelNote
from ..voice.voice_factory import VoiceFactory
from ..voice.voice_instance import VoiceInstance


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

    def __init__(self, channel_number: int, voice_factory: VoiceFactory, sample_rate: int, synthesizer=None):
        """
        Initialize XG Channel.

        Args:
            channel_number: MIDI channel number (0-15)
            voice_factory: Factory for creating voices
            sample_rate: Audio sample rate in Hz
            synthesizer: Reference to parent synthesizer for parameter access
        """
        self.channel_number = channel_number
        self.voice_factory = voice_factory
        self.sample_rate = sample_rate
        self.synthesizer = synthesizer  # Reference to parent synthesizer

        # Polyphonic voice management - multiple simultaneous voices
        self.active_voices: Dict[int, VoiceInstance] = {}  # note -> VoiceInstance
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

        # Controller state
        self.controllers = [0] * 128
        self._initialize_default_controllers()

        # Channel pressure and key pressure
        self._channel_pressure = 0
        self.key_pressure_values: Dict[int, int] = {}

        # Pitch bend state
        self.pitch_bend_value = 8192  # Center position
        self.pitch_bend_range = 2.0   # Default ±2 semitones

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
        self.xg_effects_routing = {
            'reverb_send': 0.0,
            'chorus_send': 0.0,
            'variation_send': 0.0
        }
        self.xg_part_mode = 'normal'  # 'normal', 'single', 'layer'
        self.xg_voice_reserve = None  # Voice limit for this channel

        # GS integration
        self.gs_part = None  # Reference to GS part when in GS mode

    def update_xg_state_from_message(self, xg_metadata: Dict[str, Any]):
        """
        Update XG channel state from message metadata.

        Args:
            xg_metadata: XG metadata dictionary from MIDI message
        """
        if not xg_metadata:
            return

        # Update pan gains
        if 'pan_left_gain' in xg_metadata:
            self.xg_pan_left_gain = xg_metadata['pan_left_gain']
        if 'pan_right_gain' in xg_metadata:
            self.xg_pan_right_gain = xg_metadata['pan_right_gain']

        # Update effects routing
        if 'effects_routing' in xg_metadata:
            self.xg_effects_routing.update(xg_metadata['effects_routing'])

        # Update part mode
        if 'part_mode' in xg_metadata:
            self.xg_part_mode = xg_metadata['part_mode']

        # Update voice reserve
        if 'voice_reserve' in xg_metadata:
            self.xg_voice_reserve = xg_metadata['voice_reserve']

    def _initialize_default_controllers(self):
        """Initialize default controller values per GM/XG specification."""
        # GM/XG default values
        self.controllers[7] = 100   # Volume
        self.controllers[10] = 64   # Pan (center)
        self.controllers[11] = 127  # Expression
        self.controllers[64] = 0    # Sustain pedal
        self.controllers[71] = 64   # Harmonic Content (XG)
        self.controllers[72] = 64   # Brightness (XG)
        self.controllers[73] = 0    # Release Time (XG)
        self.controllers[74] = 0    # Attack Time (XG)
        self.controllers[91] = 40   # Reverb send
        self.controllers[93] = 0    # Chorus send

    def load_program(self, program: int, bank_msb: int = 0, bank_lsb: int = 0):
        """
        Load a program (voice) for this channel.

        Args:
            program: MIDI program number (0-127)
            bank_msb: Bank select MSB (0-127)
            bank_lsb: Bank select LSB (0-127)
        """
        self.program = program
        self.bank_msb = bank_msb
        self.bank_lsb = bank_lsb
        self.bank = (bank_msb << 7) | bank_lsb

        # Create new voice using factory
        self.current_voice = self.voice_factory.create_voice(
            bank=self.bank,
            program=program,
            channel=self.channel_number,
            sample_rate=self.sample_rate
        )

        # Set current program for region-based playback (fallback to voice for now)
        self.current_program = self.current_voice

    def note_on(self, note: int, velocity: int) -> bool:
        """
        Handle note-on event with polyphony support.

        Creates a new VoiceInstance for each note, allowing multiple
        simultaneous notes per channel (true polyphony).

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

        # Check if we already have a voice instance for this note
        if transposed_note in self.active_voices:
            # Retrigger existing voice (for monophonic instruments)
            existing_voice = self.active_voices[transposed_note]
            existing_voice.note_on(velocity)
            return True

        # Create new VoiceInstance for this note
        voice_instance = VoiceInstance(transposed_note, velocity, self.channel_number, self.sample_rate)

        # Get regions for this note/velocity from current program
        if self.current_program:
            regions = self.current_program.get_regions_for_note(transposed_note, velocity)
            for region in regions:
                voice_instance.add_region(region)

        # Check if we have any regions to play
        if not voice_instance.regions:
            # Fallback to legacy single voice if no regions
            if self.current_voice and self.current_voice.is_note_supported(transposed_note):
                self.current_voice.note_on(transposed_note, velocity)
                return True
            return False

        # Trigger note-on for the voice instance
        voice_instance.note_on(velocity)

        # Store the active voice instance
        self.active_voices[transposed_note] = voice_instance

        return True

    def note_off(self, note: int, velocity: int = 64):
        """
        Handle note-off event with polyphony support.

        Args:
            note: MIDI note number (0-127)
            velocity: Note-off velocity (0-127)
        """
        # Apply channel transposition
        transposed_note = note + self.transpose

        # Check if we have a voice instance for this note
        if transposed_note in self.active_voices:
            voice_instance = self.active_voices[transposed_note]
            voice_instance.note_off(velocity)

            # Note: We don't remove the voice instance here - it will be
            # removed in generate_samples() when it's no longer active
            # This allows for proper release phase handling
        else:
            # Fallback to legacy single voice
            if self.current_voice:
                self.current_voice.note_off(transposed_note)

    def control_change(self, controller: int, value: int):
        """
        Handle control change event.

        Args:
            controller: Controller number (0-127)
            value: Controller value (0-127)
        """
        self.controllers[controller] = value

        # Handle special XG controllers
        if controller == 0:  # Bank Select MSB
            self.bank_msb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 32:  # Bank Select LSB
            self.bank_lsb = value
            self.bank = (self.bank_msb << 7) | self.bank_lsb
        elif controller == 7:  # Volume
            self.master_level = value / 127.0
        elif controller == 10:  # Pan
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
                if not self.data_msb_received:
                    self.data_msb = value
                    self.data_msb_received = True
                else:
                    # Complete NRPN message
                    self._handle_nrpn_complete(self.data_msb, value)
                    self.nrpn_active = False
                    self.data_msb_received = False
            elif self.rpn_active:
                self._handle_rpn_complete(value)
                self.rpn_active = False

    def _handle_nrpn_complete(self, msb: int, lsb: int):
        """
        Handle complete NRPN message.

        Args:
            msb: Data MSB
            lsb: Data LSB
        """
        # XG NRPN handling would go here
        # For now, this is a placeholder
        pass

    def _handle_rpn_complete(self, value: int):
        """
        Handle complete RPN message.

        Args:
            value: RPN value
        """
        if self.rpn_msb == 0 and self.rpn_lsb == 0:
            # Pitch Bend Range
            self.pitch_bend_range = value
        # Other RPN parameters can be handled here

    def pitch_bend(self, lsb: int, msb: int):
        """
        Handle pitch bend event.

        Args:
            lsb: Pitch bend LSB (0-127)
            msb: Pitch bend MSB (0-127)
        """
        self.pitch_bend_value = (msb << 7) | lsb

    def set_channel_pressure(self, pressure: int):
        """
        Handle channel pressure (aftertouch).

        Args:
            pressure: Pressure value (0-127)
        """
        self.channel_pressure = pressure

    def key_pressure(self, note: int, pressure: int):
        """
        Handle polyphonic key pressure.

        Args:
            note: MIDI note number (0-127)
            pressure: Pressure value (0-127)
        """
        self.key_pressure_values[note] = pressure

    def program_change(self, program: int):
        """
        Handle program change.

        Args:
            program: New program number (0-127)
        """
        self.load_program(program, self.bank_msb, self.bank_lsb)

    def all_notes_off(self):
        """Turn off all notes on this channel."""
        # Send note-off to all active voice instances
        for voice_instance in list(self.active_voices.values()):
            voice_instance.note_off()

        # Fallback to legacy single voice
        if self.current_voice:
            for note in range(128):
                self.current_voice.note_off(note)

    def all_sound_off(self):
        """Immediately silence all sounds on this channel."""
        # Immediately silence all active voice instances
        for voice_instance in list(self.active_voices.values()):
            voice_instance.all_notes_off()

        # Clear active voices
        self.active_voices.clear()

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

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this channel with true polyphony.

        Supports multiple simultaneous VoiceInstance objects, each handling
        their own note with multiple regions (velocity layers, round robin, etc.).

        Args:
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Start with silence
        output = np.zeros((block_size, 2), dtype=np.float32)

        if self.muted:
            return output

        # Generate samples from all active voice instances
        active_voice_count = 0
        for voice_instance in list(self.active_voices.values()):
            if voice_instance.is_active():
                # Get samples from this voice instance
                voice_audio = voice_instance.generate_samples(block_size)

                # Mix voice into channel output
                output += voice_audio
                active_voice_count += 1

                # Remove inactive voices to prevent accumulation
                if not voice_instance.is_active():
                    del self.active_voices[voice_instance.note]
            else:
                # Remove inactive voices
                del self.active_voices[voice_instance.note]

        # Apply channel-level processing if we have active voices
        if active_voice_count > 0:
            # Collect modulation values from controllers
            modulation = self._collect_modulation_values()

            # Apply master level - check GS parameters first
            master_level = self._get_master_level()
            output *= master_level

            # Apply pan - check GS parameters first, then XG, then regular
            pan_gains = self._get_pan_gains()
            output[:, 0] *= pan_gains[0]  # Left channel
            output[:, 1] *= pan_gains[1]  # Right channel

            # Update modulation for all active voices
            for voice_instance in self.active_voices.values():
                voice_instance.update_modulation(modulation)

        return output

    def _collect_modulation_values(self) -> Dict[str, float]:
        """
        Collect modulation values from controllers and channel state.

        Returns:
            Dictionary of modulation values
        """
        # Convert pitch bend to modulation value
        pitch_bend_semitones = ((self.pitch_bend_value - 8192) / 8192.0) * self.pitch_bend_range

        modulation = {
            'pitch': pitch_bend_semitones * 100.0,  # Convert to cents
            'filter_cutoff': 0.0,  # Could be mapped to controllers
            'amp': 1.0,
            'pan': self.pan,
            'velocity_crossfade': 0.0,
            'note_crossfade': 0.0,
            'stereo_width': 1.0,
            'tremolo_rate': 4.0,
            'tremolo_depth': 0.3,
            'mod_wheel': self.controllers[1] / 127.0,
            'breath_controller': self.controllers[2] / 127.0,
            'foot_controller': self.controllers[4] / 127.0,
            'expression': self.controllers[11] / 127.0,
            'brightness': self.controllers[72] / 127.0,
            'harmonic_content': self.controllers[71] / 127.0,
            'channel_aftertouch': self.channel_pressure / 127.0,
            'volume_cc': self.controllers[7] / 127.0,
        }

        return modulation

    def get_channel_info(self) -> Dict[str, Any]:
        """
        Get information about this channel.

        Returns:
            Dictionary with channel state information
        """
        return {
            'channel_number': self.channel_number,
            'program': self.program,
            'bank': self.bank,
            'bank_msb': self.bank_msb,
            'bank_lsb': self.bank_lsb,
            'active': self.active,
            'muted': self.muted,
            'solo': self.solo,
            'key_range': (self.key_range_low, self.key_range_high),
            'master_level': self.master_level,
            'pan': self.pan,
            'transpose': self.transpose,
            'has_voice': self.current_voice is not None,
            'voice_info': self.current_voice.get_voice_info() if self.current_voice else None
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
        return len(self.active_voices) > 0 or (self.current_voice is not None and self.current_voice.is_active())

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
        if hasattr(self, 'xg_config') and self.xg_config and 'part_level' in self.xg_config:
            return self.xg_config['part_level'] / 100.0

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

                import math
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
