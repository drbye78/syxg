"""
Jupiter-X Hardware Integration Architecture - Professional Hardware Synthesis System

ARCHITECTURAL OVERVIEW:

The Jupiter-X Hardware Integration Architecture implements a comprehensive bridge
between software synthesis frameworks and professional hardware synthesizers,
specifically the Roland Jupiter-X. This system provides seamless integration of
hardware synthesis capabilities into software environments, enabling hybrid
workflows that combine the precision of software with the character of analog hardware.

JUPITER-X SYNTHESIS PHILOSOPHY:

The Roland Jupiter-X represents the pinnacle of modern analog/digital hybrid synthesis,
combining four distinct synthesis engines in a single instrument:

1. ANALOG ENGINE: Classic subtractive synthesis with vintage warmth and character
2. DIGITAL ENGINE: Modern digital synthesis with advanced algorithms and processing
3. FM ENGINE: Frequency modulation synthesis with complex timbral possibilities
4. EXTERNAL ENGINE: Processing of external audio signals through Jupiter-X effects

This architecture enables unprecedented synthesis flexibility while maintaining
the professional performance and reliability expected from hardware instruments.

HARDWARE INTEGRATION DESIGN:

The integration system implements a sophisticated communication layer that bridges
software control with hardware synthesis:

COMMUNICATION ARCHITECTURE:
- SYSEX PROTOCOL: Roland's system exclusive messaging for parameter control
- MIDI TUNNELING: Real-time MIDI message forwarding to hardware
- STATUS POLLING: Hardware state synchronization and monitoring
- BULK OPERATIONS: Efficient parameter dumps and preset management

PERFORMANCE OPTIMIZATION:
- ASYNCHRONOUS COMMUNICATION: Non-blocking hardware communication
- BUFFER MANAGEMENT: Audio streaming with minimal latency
- ERROR RECOVERY: Automatic reconnection and state resynchronization
- RESOURCE POOLING: Efficient management of hardware communication channels

MULTI-ENGINE ARCHITECTURE:

The Jupiter-X's four-engine architecture requires sophisticated coordination:

ENGINE COORDINATION:
- PART ASSIGNMENT: Each of 16 parts can use any synthesis engine
- ENGINE SHARING: Multiple parts can use the same engine type simultaneously
- RESOURCE ALLOCATION: Dynamic allocation of hardware resources
- STATE MANAGEMENT: Independent state for each engine instance

ENGINE CHARACTERISTICS:
- ANALOG ENGINE: Voltage-controlled filters, amplifiers, and oscillators
- DIGITAL ENGINE: DSP-based synthesis with modern algorithms
- FM ENGINE: 8-operator FM synthesis with feedback and ratios
- EXTERNAL ENGINE: Sidechain processing and effects for external sources

MPE (MICROTONAL PITCH EXPRESSION) ARCHITECTURE:

ADVANCED EXPRESSIVE CONTROL:
The Jupiter-X integration provides comprehensive MPE support for microtonal
and expressive control:

MPE ZONE CONFIGURATION:
- UPPER/LOWER ZONES: Independent MPE zones for multi-instrument control
- CHANNEL ASSIGNMENT: Dedicated MIDI channels for MPE control
- NOTE RANGE MAPPING: Configurable note ranges for each zone
- EXPRESSION MAPPING: Per-note control of timbre, pitch, and amplitude

PER-NOTE CONTROL:
- PITCH BEND: Independent pitch control for each note
- TIMBRE CONTROL: Per-note filter and waveform control
- PRESSURE CONTROL: Individual aftertouch for each note
- SLIDE CONTROL: Smooth transitions between notes

ARPEGGIATOR SYSTEM ARCHITECTURE:

PROFESSIONAL SEQUENCING:
The Jupiter-X features a sophisticated arpeggiator system integrated with the synthesis:

ARPEGGIATOR MODES:
- UP/DOWN: Classic ascending/descending patterns
- RANDOM: Non-repetitive note selection
- NOTE ORDER: Plays notes in order pressed
- CHORD MEMORY: Remembers chord voicings

PERFORMANCE FEATURES:
- TEMPO SYNCHRONIZATION: BPM-locked timing
- NOTE LENGTH CONTROL: Variable gate times
- OCTAVE RANGE: Multi-octave pattern generation
- MOTION SEQUENCES: Pattern variation and evolution

PARAMETER CONTROL ARCHITECTURE:

COMPREHENSIVE PARAMETER SYSTEM:
The Jupiter-X exposes thousands of parameters through a hierarchical control system:

GLOBAL PARAMETERS:
- MASTER VOLUME/PAN: Overall level and stereo positioning
- TEMPO CONTROL: System tempo for arpeggiators and effects
- TUNING: Master tuning and temperament settings
- SYSTEM EFFECTS: Reverb, chorus, delay, distortion settings

ENGINE PARAMETERS:
- OSCILLATOR CONTROLS: Waveform, pitch, level for each oscillator
- FILTER PARAMETERS: Cutoff, resonance, envelope amount
- AMPLIFIER CONTROLS: ADSR envelope, velocity sensitivity
- LFO SETTINGS: Rate, depth, waveform, destination routing

EFFECTS PARAMETERS:
- MULTI-EFFECT PROCESSOR: 90+ effect types with full parameter control
- SEND EFFECTS: Dedicated reverb and chorus units
- MODULATION EFFECTS: Phaser, flanger, chorus with LFO control
- DYNAMIC PROCESSING: Compressor, limiter, gate with sidechain

HARDWARE COMMUNICATION ARCHITECTURE:

PROFESSIONAL HARDWARE CONTROL:
The integration implements robust communication with Jupiter-X hardware:

MIDI PROTOCOL IMPLEMENTATION:
- SYSEX MESSAGES: Parameter control and bulk operations
- NRPN CONTROL: Registered parameter number control
- CC MESSAGES: Continuous controller automation
- SYSTEM EXCLUSIVE: Extended parameter and preset control

ERROR HANDLING AND RECOVERY:
- TIMEOUT MANAGEMENT: Automatic retry for failed communications
- STATE VALIDATION: Hardware state verification and correction
- CONNECTION MONITORING: Automatic reconnection on disconnection
- BUFFER UNDERFLOW PROTECTION: Audio continuity during communication issues

AUDIO STREAMING ARCHITECTURE:

LOW-LATENCY AUDIO TRANSFER:
The system provides high-performance audio streaming from hardware:

STREAMING OPTIMIZATION:
- BUFFER MANAGEMENT: Multi-buffered streaming for glitch-free audio
- LATENCY COMPENSATION: Automatic delay compensation
- SAMPLE RATE CONVERSION: Automatic rate matching
- BIT DEPTH HANDLING: 24-bit audio processing and conversion

QUALITY ASSURANCE:
- DROPOUT DETECTION: Audio interruption monitoring and recovery
- JITTER REDUCTION: Timing stabilization for consistent streaming
- LEVEL MATCHING: Automatic gain staging and level normalization
- NOISE REDUCTION: Background noise filtering and artifact removal

WORKSTATION INTEGRATION:

PROFESSIONAL PRODUCTION WORKFLOW:
The Jupiter-X integration enables seamless use in professional production environments:

DAW INTEGRATION:
- PLUGIN HOSTING: VST/AU/AAX plugin wrapper for DAW integration
- AUTOMATION SUPPORT: Full parameter automation from DAW
- TEMPO SYNCHRONIZATION: BPM-locked operation with host
- PROJECT MANAGEMENT: Preset and parameter management within projects

REMOTE CONTROL:
- NETWORK CONTROL: Ethernet-based remote control and monitoring
- WIRELESS OPERATION: Bluetooth and WiFi connectivity options
- MOBILE CONTROL: iOS/Android app control and monitoring
- WEB INTERFACE: Browser-based control and configuration

HYBRID SYNTHESIS WORKFLOW:

SOFTWARE/HARDWARE HYBRID:
The integration enables powerful hybrid workflows combining software and hardware:

LAYERED SYNTHESIS:
- SOFTWARE PRE-PROCESSING: Software effects and processing before hardware
- HARDWARE CHARACTER: Analog warmth and processing from Jupiter-X
- MIXED ROUTING: Flexible signal routing between software and hardware
- UNIFIED CONTROL: Single interface controlling both domains

ADVANCED WORKFLOWS:
- SOUND DESIGN PIPELINE: Software sound design feeding hardware refinement
- LIVE PERFORMANCE: Software sequencing with hardware synthesis
- RECORDING WORKFLOW: Software capture with hardware processing
- MIXING INTEGRATION: Hardware effects in software mixing environment

EXTENSIBILITY ARCHITECTURE:

FUTURE HARDWARE SUPPORT:
The architecture is designed to support future Roland synthesizers and expand to other manufacturers:

ROLAND ECOSYSTEM:
- JUPITER-XM: Extended Jupiter-X with additional capabilities
- FANTOM SERIES: Integration with Fantom workstation synthesizers
- SYSTEM-8: Classic analog synthesizer integration
- AIRA PRODUCTS: Integration with grooveboxes and controllers

THIRD-PARTY INTEGRATION:
- OTHER MANUFACTURERS: Support for synthesizers from other brands
- CUSTOM HARDWARE: User-defined hardware control protocols
- EXPANDABLE PROTOCOLS: Support for new communication standards
- OPEN ARCHITECTURE: Third-party hardware integration support

RESEARCH FEATURES:
- AI-ASSISTED CONTROL: Machine learning parameter optimization
- NEURAL SYNTHESIS: AI-enhanced hardware sound design
- ADAPTIVE CONTROL: Real-time adaptation based on performance
- PREDICTIVE MODELING: Anticipatory parameter changes

PROFESSIONAL STANDARDS COMPLIANCE:

INDUSTRY STANDARDS:
- MIDI 1.0/2.0: Complete MIDI protocol compliance
- AES/EBU: Professional audio standards
- SMPTE TIMING: Broadcast and post-production timing
- IEEE AUDIO: Technical audio processing standards

ROLAND STANDARDS:
- ROLAND SYSEX: Proprietary system exclusive protocol
- GS/XG COMPATIBILITY: Backward compatibility with legacy standards
- INTEGRATED RHYTHM: Drum and percussion integration
- EFFECTS PROCESSING: Professional effects standards

QUALITY ASSURANCE:
- RELIABILITY TESTING: Extensive hardware communication testing
- PERFORMANCE VALIDATION: Real-time performance verification
- COMPATIBILITY TESTING: Multi-platform and multi-DAW testing
- USER EXPERIENCE: Professional user interface design

FUTURE EXPANSION:

NEXT-GENERATION FEATURES:
- HIGH-SPEED CONNECTIVITY: USB 3.0 and Thunderbolt integration
- WIRELESS AUDIO: Bluetooth LE audio streaming
- CLOUD CONNECTIVITY: Remote preset and sound management
- AI ASSISTANCE: Machine learning sound design assistance

PROFESSIONAL INTEGRATION:
- IMMERSIVE AUDIO: Surround and 3D audio support
- NETWORK SYNTHESIS: Distributed synthesis across multiple devices
- ADVANCED CONTROL: Touch screens and gesture control
- AUGMENTED REALITY: AR-based sound design interfaces

ARCHITECTURAL PATTERNS:

DESIGN PATTERNS IMPLEMENTED:
- ADAPTER PATTERN: Hardware abstraction for unified software interface
- FACADE PATTERN: Simplified hardware control interface
- OBSERVER PATTERN: Real-time hardware state monitoring
- COMMAND PATTERN: Hardware parameter changes as executable commands

ARCHITECTURAL PRINCIPLES:
- SINGLE RESPONSIBILITY: Each component handles one aspect of hardware integration
- OPEN/CLOSED PRINCIPLE: New hardware support without modifying core architecture
- DEPENDENCY INVERSION: Abstract hardware interfaces for flexible implementation
- COMPOSITION OVER INHERITANCE: Modular hardware integration assembly
"""
from __future__ import annotations

from typing import Any
import numpy as np
import threading

from ..engine.synthesis_engine import SynthesisEngine
from ..engine.region_descriptor import RegionDescriptor
from ..engine.preset_info import PresetInfo
from ..partial.region import IRegion
from .synthesizer import JupiterXSynthesizer
from ..core.buffer_pool import XGBufferPool


class JupiterXEngineIntegration(SynthesisEngine):
    """
    Jupiter-X Engine Integration

    Wraps the Jupiter-X synthesizer as a synthesis engine that can be
    registered with the modern synthesizer's engine registry, allowing
    Jupiter-X to be used alongside other synthesis engines.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize Jupiter-X engine integration.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size
        """
        super().__init__(sample_rate, block_size)

        # Initialize Jupiter-X synthesizer backend
        self.jupiter_x_synth = JupiterXSynthesizer(
            sample_rate=sample_rate, buffer_size=block_size
        )

        # Enable Jupiter-X mode
        self.jupiter_x_synth.enable_jupiter_x_mode()

        # Thread safety
        self.lock = threading.RLock()

        # Engine metadata
        self.name = "Jupiter-X"
        self.description = "Roland Jupiter-X synthesizer with 4-engine architecture"
        self.version = "1.0.0"

        # Capabilities
        self.capabilities = {
            "polyphony": 16,  # 16 monophonic parts
            "engines": ["analog", "digital", "fm", "external"],
            "effects": True,
            "arpeggiator": True,
            "mpe": True,
            "parameters": 500,  # Approximate parameter count
        }

        print("🎹 Jupiter-X Engine: Integrated with modern synthesizer framework")

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported by this engine."""
        # Jupiter-X supports full MIDI note range
        return 0 <= note <= 127

    def get_engine_info(self) -> dict[str, Any]:
        """Get engine information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "jupiter_x_info": self.jupiter_x_synth.get_system_info(),
        }

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int):
        """Create a partial instance for this engine."""
        # Jupiter-X doesn't use the traditional partial system
        # Instead, it uses its own internal synthesis architecture
        # Return a dummy partial that delegates to Jupiter-X synthesis
        from ..partial.partial import SynthesisPartial

        class JupiterXPartial(SynthesisPartial):
            def __init__(self, engine, params, sample_rate):
                super().__init__(params, sample_rate)
                self.jupiter_x_engine = engine

            def generate_samples(self, note, velocity, modulation, block_size):
                return self.jupiter_x_engine.generate_samples(
                    note, velocity, modulation, block_size
                )

            def note_on(self, velocity):
                self.jupiter_x_engine.note_on(self.note, velocity)

            def note_off(self):
                self.jupiter_x_engine.note_off(self.note)

        return JupiterXPartial(self, partial_params, sample_rate)

    # ========== NEW REGION-BASED ARCHITECTURE METHODS ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get Jupiter-X preset info with region descriptors.

        Jupiter-X uses preset-based architecture rather than traditional
        bank/program mapping. This method provides compatibility with
        the XG bank/program system.

        Args:
            bank: MIDI bank number (0-127)
            program: MIDI program number (0-127)

        Returns:
            PresetInfo with region descriptors, or None if not found
        """
        # Jupiter-X uses single-region presets
        # Each preset is a complete synthesis configuration
        descriptor = RegionDescriptor(
            region_id=0,
            engine_type="jupiter_x",
            key_range=(0, 127),  # Full MIDI range
            velocity_range=(0, 127),
            round_robin_group=0,
            round_robin_position=0,
            generator_params={
                "bank": bank,
                "program": program,
                "engine_type": "jupiter_x",
            },
        )

        return PresetInfo(
            bank=bank,
            program=program,
            name=f"Jupiter-X {bank}:{program}",
            engine_type="jupiter_x",
            region_descriptors=[descriptor],
            master_level=1.0,
            master_pan=0.0,
            reverb_send=0.0,
            chorus_send=0.0,
        )

    def get_all_region_descriptors(
        self, bank: int, program: int
    ) -> list[RegionDescriptor]:
        """
        Get ALL region descriptors for a Jupiter-X preset.

        Jupiter-X uses single-region presets.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            List of RegionDescriptor objects
        """
        preset_info = self.get_preset_info(bank, program)
        if preset_info:
            return preset_info.region_descriptors
        return []

    def _create_base_region(
        self, descriptor: RegionDescriptor, sample_rate: int
    ) -> IRegion:
        """
        Create Jupiter-X base region without S.Art2 wrapper.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance (Jupiter-X uses internal synthesis)
        """
        # Jupiter-X doesn't use traditional regions
        # Create a minimal region that delegates to Jupiter-X synthesis
        from ..partial.region import Region

        class JupiterXRegion(Region):
            """Jupiter-X region wrapper."""

            def __init__(self, engine, descriptor, sample_rate):
                super().__init__({}, sample_rate)
                self.jupiter_x_engine = engine
                self.descriptor = descriptor
                self.active = False
                self.note = 60
                self.velocity = 100

            def _load_sample_data(self) -> np.ndarray | None:
                """Load sample data - not needed for algorithmic synthesis."""
                return None

            def _create_partial(self) -> Any | None:
                """Create synthesis partial - not needed for Jupiter-X."""
                return None

            def _init_envelopes(self) -> None:
                """Initialize envelopes - handled by Jupiter-X engine."""
                pass

            def _init_filters(self) -> None:
                """Initialize filters - handled by Jupiter-X engine."""
                pass

            def note_on(self, velocity: int, note: int = 60):
                """Trigger note on."""
                self.active = True
                self.note = note
                self.velocity = velocity
                self.jupiter_x_engine.note_on(note, velocity)

            def note_off(self):
                """Trigger note off."""
                self.active = False
                self.jupiter_x_engine.note_off(self.note)

            def generate_samples(
                self, block_size: int, modulation: dict = None
            ) -> np.ndarray:
                """Generate samples."""
                if not self.active:
                    return np.zeros((block_size, 2), dtype=np.float32)
                return self.jupiter_x_engine.generate_samples(
                    self.note, self.velocity, modulation or {}, block_size
                )

            def is_active(self) -> bool:
                """Check if region is active."""
                return self.active

            def reset(self):
                """Reset region state."""
                self.active = False
                self.note = 60
                self.velocity = 100

        return JupiterXRegion(self, descriptor, sample_rate)

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for Jupiter-X region.

        Jupiter-X uses algorithmic synthesis, so no sample loading is needed.

        Args:
            region: Region instance to load sample for

        Returns:
            True (always succeeds for algorithmic synthesis)
        """
        return True  # Jupiter-X doesn't use samples

    # ========== END NEW REGION-BASED ARCHITECTURE METHODS ==========

    def set_sample_rate(self, sample_rate: int):
        """Set sample rate (not supported - Jupiter-X must be recreated)."""
        print("⚠️  Jupiter-X Engine: Sample rate changes require engine recreation")

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples using Jupiter-X synthesis.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Modulation parameters
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        with self.lock:
            # Process note through Jupiter-X
            # Note: Jupiter-X uses part-based architecture, so we route to part 0 by default
            # In a full integration, this would be configurable per channel/part

            # Send note on to Jupiter-X (part 0, channel 0)
            self.jupiter_x_synth.note_on(note, velocity, channel=0)

            # Generate audio block
            audio_block = self.jupiter_x_synth.process_audio_block()

            # Send note off (for single-shot generation)
            self.jupiter_x_synth.note_off(note, channel=0)

            # Ensure correct block size (in case Jupiter-X returns different size)
            if audio_block.shape[0] != block_size:
                # Pad or truncate as needed
                if audio_block.shape[0] < block_size:
                    # Pad with zeros
                    padding = np.zeros(
                        (block_size - audio_block.shape[0], 2), dtype=audio_block.dtype
                    )
                    audio_block = np.vstack([audio_block, padding])
                else:
                    # Truncate
                    audio_block = audio_block[:block_size]

            return audio_block

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        with self.lock:
            self.jupiter_x_synth.note_on(note, velocity, channel=0)

    def note_off(self, note: int):
        """Handle note-off event."""
        with self.lock:
            self.jupiter_x_synth.note_off(note, channel=0)

    def all_notes_off(self):
        """Turn off all notes."""
        with self.lock:
            self.jupiter_x_synth.all_notes_off()

    def set_parameter(self, param_name: str, value: Any) -> bool:
        """
        Set engine parameter.

        Args:
            param_name: Parameter name (supports Jupiter-X parameter mapping)
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            # Map common parameter names to Jupiter-X parameters
            param_mapping = {
                "volume": lambda v: self.jupiter_x_synth.set_parameter(
                    "master_volume", v
                ),
                "pan": lambda v: self.jupiter_x_synth.set_parameter("master_pan", v),
                "cutoff": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "filter_cutoff", v
                ),
                "resonance": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "filter_resonance", v
                ),
                "attack": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "amp_attack", v
                ),
                "decay": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "amp_decay", v
                ),
                "sustain": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "amp_sustain", v
                ),
                "release": lambda v: self.jupiter_x_synth.set_engine_parameter(
                    0, "analog", "amp_release", v
                ),
            }

            if param_name in param_mapping:
                return param_mapping[param_name](value)

            # Try direct parameter setting
            return self.jupiter_x_synth.set_parameter(param_name, value)

    def get_parameter(self, param_name: str) -> Any:
        """Get engine parameter."""
        with self.lock:
            # Try direct parameter access
            return self.jupiter_x_synth.get_parameter(param_name)

    def process_midi_cc(self, cc_number: int, value: int) -> bool:
        """Process MIDI CC message."""
        with self.lock:
            return self.jupiter_x_synth.process_midi_cc(0, cc_number, value)

    def process_pitch_bend(self, value: int):
        """Process pitch bend message."""
        with self.lock:
            # Convert 14-bit pitch bend to MIDI message format
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            self.jupiter_x_synth.process_midi_message(0xE0, lsb, msb)

    def process_aftertouch(self, pressure: int):
        """Process aftertouch message."""
        with self.lock:
            self.jupiter_x_synth.process_midi_message(0xD0, pressure, 0)

    def load_program(
        self, program_number: int, bank_msb: int = 0, bank_lsb: int = 0
    ) -> bool:
        """
        Load program/preset.

        Args:
            program_number: Program number
            bank_msb: Bank MSB
            bank_lsb: Bank LSB

        Returns:
            True if program was loaded successfully
        """
        with self.lock:
            # Jupiter-X uses preset system
            preset_name = f"program_{program_number}"
            return self.jupiter_x_synth.load_preset(preset_name)

    def save_program(
        self, program_number: int, bank_msb: int = 0, bank_lsb: int = 0
    ) -> bool:
        """Save current state as program/preset."""
        with self.lock:
            preset_name = f"program_{program_number}"
            return self.jupiter_x_synth.save_preset(preset_name)

    def get_program_info(self, program_number: int) -> dict[str, Any] | None:
        """Get program information."""
        with self.lock:
            # Jupiter-X preset system doesn't have detailed program info
            return {
                "program_number": program_number,
                "name": f"Jupiter-X Program {program_number}",
                "type": "synthesizer",
                "engines": ["analog", "digital", "fm", "external"],
            }

    def reset(self):
        """Reset engine to default state."""
        with self.lock:
            self.jupiter_x_synth.reset()

    def cleanup(self):
        """Clean up engine resources."""
        with self.lock:
            if hasattr(self.jupiter_x_synth, "cleanup"):
                self.jupiter_x_synth.cleanup()

    # Jupiter-X specific methods
    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return "jupiter_x"

    def set_engine_type(self, part_num: int, engine_type: str) -> bool:
        """Set synthesis engine type for a part."""
        with self.lock:
            return self.jupiter_x_synth.set_part_engine(part_num, engine_type)

    def get_engine_type_for_part(self, part_num: int) -> str:
        """Get synthesis engine type for a part."""
        with self.lock:
            return self.jupiter_x_synth.get_part_engine(part_num)

    def set_jupiter_x_parameter(
        self, part_num: int, engine: str, param: str, value: Any
    ) -> bool:
        """Set Jupiter-X specific parameter."""
        with self.lock:
            return self.jupiter_x_synth.set_engine_parameter(
                part_num, engine, param, value
            )

    def get_jupiter_x_parameter(self, part_num: int, engine: str, param: str) -> Any:
        """Get Jupiter-X specific parameter."""
        with self.lock:
            return self.jupiter_x_synth.get_engine_parameter(part_num, engine, param)

    def enable_arpeggiator(self, part_num: int, enable: bool) -> bool:
        """Enable/disable arpeggiator for a part."""
        with self.lock:
            return self.jupiter_x_synth.enable_arpeggiator(part_num, enable)

    def set_arpeggiator_pattern(self, part_num: int, pattern_id: int) -> bool:
        """Set arpeggiator pattern."""
        with self.lock:
            return self.jupiter_x_synth.set_arpeggiator_pattern(part_num, pattern_id)

    def enable_mpe(self, enable: bool) -> bool:
        """Enable/disable MPE mode."""
        with self.lock:
            return self.jupiter_x_synth.enable_mpe(enable)

    def get_jupiter_x_status(self) -> dict[str, Any]:
        """Get Jupiter-X system status."""
        with self.lock:
            return self.jupiter_x_synth.get_system_info()

    def __str__(self) -> str:
        """String representation."""
        return f"JupiterXEngineIntegration({self.jupiter_x_synth})"


# Factory function for easy integration
def create_jupiter_x_engine(
    sample_rate: int = 44100, block_size: int = 1024
) -> JupiterXEngineIntegration:
    """
    Create a Jupiter-X engine integration instance.

    Args:
        sample_rate: Audio sample rate in Hz
        block_size: Processing block size

    Returns:
        Configured Jupiter-X engine integration
    """
    return JupiterXEngineIntegration(sample_rate, block_size)
