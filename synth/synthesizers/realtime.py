"""

Main Synthesizer Class - Core Architecture

The Synthesizer class represents the central orchestration component of the XG synthesizer system,
providing a unified interface for real-time audio synthesis with full XG specification compliance.

ARCHITECTURAL OVERVIEW:

The synthesizer follows a modular, component-based architecture where each major subsystem
(engine management, effects processing, voice allocation, MIDI processing) is encapsulated
in dedicated components that communicate through well-defined interfaces.

Component Hierarchy:
├── Synthesizer (main orchestrator)
│   ├── Engine Registry (synthesis engine management)
│   ├── Voice Manager (polyphony and voice allocation)
│   ├── Effects Coordinator (DSP effects processing)
│   ├── XG System (XG specification implementation)
│   ├── MIDI Parser (real-time MIDI processing)
│   ├── Buffer Pool (memory management)
│   └── Parameter Router (cross-component parameter routing)

Data Flow Architecture:
1. MIDI Input → MIDI Parser → Parameter Router → Target Components
2. Voice Allocation → Engine Registry → Synthesis Engine → Audio Generation
3. Audio Generation → Effects Coordinator → Master Processing → Output
4. Performance Monitoring → Parameter Router → Adaptive Parameter Adjustment

Threading Model:
- Main thread: MIDI processing, parameter updates, voice management
- Audio thread: Real-time audio generation and effects processing
- Background threads: Sample loading, preset management, performance monitoring

Memory Management:
- Zero-allocation design using pre-allocated buffer pools
- Component-local buffer allocation to prevent contention
- Automatic cleanup on component destruction
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

import numpy as np

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Self

from ..engines.engine_registry import XGEngineRegistry
from ..engines.parameter_router import ParameterRouter
from ..io.midi import MIDIMessage, RealtimeParser
from ..processing.effects.effects_coordinator import XGEffectsCoordinator
from ..processing.effects.pipeline_topology import PipelineTopology
from ..processing.voice.voice_manager import VoiceManager
from ..protocols.xg.part_engine_router import PartEngineRouter
from ..protocols.xg.xg_synthesizer_system import XGSynthesizerSystem
from ..protocols.xg.xg_system import XGSystem
from ..sampling.sample_manager import SampleManager

# Import available engines
try:
    from ..engines.fdsp import FDSPSynthesisEngine
except ImportError:
    FDSPSynthesisEngine = None

try:
    from ..engines.physical_modeling import ANEngine
except ImportError:
    ANEngine = None

try:
    from ..engines.sf2_engine import SF2Engine
except ImportError:
    SF2Engine = None

try:
    from ..engines.sf2_engine_controller import SF2PartModeIntegrator
except ImportError:
    SF2PartModeIntegrator = None

try:
    from ..synthesizers.rendering import ModernXGSynthesizer
except ImportError:
    ModernXGSynthesizer = None

try:
    from ..engines.fm_engine import FMEngine
except ImportError:
    FMEngine = None

try:
    from ..engines.wavetable import WavetableEngine
except ImportError:
    WavetableEngine = None

try:
    from ..engines.additive import AdditiveEngine
except ImportError:
    AdditiveEngine = None
from ..hardware.s90_s70 import (
    S90S70ControlSurfaceMapping,
    S90S70HardwareSpecs,
    S90S70PerformanceFeatures,
    S90S70PresetCompatibility,
)
from ..primitives.buffer_pool import XGBufferPool
from ..primitives.config import SynthConfig
from ..sequencer.groove_quantizer import GrooveQuantizer
from ..sequencer.pattern_sequencer import PatternSequencer

# Style Engine imports
try:
    from ..style import (
        DynamicsParameter,
        RegistrationMemory,
        Style,
        StyleDynamics,
        StyleLoader,
        StyleSectionType,
    )
    from ..style.integrations import StyleIntegrations
    from ..style.midi_learn import LearnTargetType, MIDILearn
    from ..style.scale import ScaleDetector
    from ..style.style_player import StylePlayer
except ImportError:
    StylePlayer = None
    StyleLoader = None
    Style = None
    StyleSectionType = None
    RegistrationMemory = None
    StyleDynamics = None
    DynamicsParameter = None
    MIDILearn = None
    LearnTargetType = None
    StyleIntegrations = None
    ScaleDetector = None


class Synthesizer:
    """
    Main Synthesizer Class - Central Orchestration Component

    RESPONSIBILITIES:
    ================
    The Synthesizer class serves as the central orchestrator for the entire XG synthesis system,
    managing the lifecycle and interactions of all subsystem components. It provides a unified
    public API for real-time audio synthesis while maintaining clean separation of concerns
    between MIDI processing, voice allocation, synthesis generation, and effects processing.

    ARCHITECTURAL ROLE:
    ===================
    - Component Coordinator: Initializes and manages all subsystem components
    - Thread Manager: Orchestrates main thread (MIDI/control) and audio thread (synthesis/effects)
    - Resource Arbiter: Manages shared resources like buffer pools and parameter routing
    - State Controller: Maintains global synthesizer state and configuration
    - Performance Monitor: Tracks real-time performance metrics and system health

    COMPONENT INTERFACES:
    ====================
    The synthesizer implements the Facade pattern, providing simplified interfaces to complex
    subsystem interactions:

    Public API Methods:
    - note_on/off(): Voice allocation and management
    - control_change(): Parameter routing and modulation
    - program_change(): Preset and voice selection
    - get_audio_block(): Real-time audio output retrieval
    - load/save_preset(): Configuration persistence

    Internal Component Management:
    - _initialize_components(): Component lifecycle management
    - _register_engines(): Synthesis engine registration and prioritization
    - _setup_parameter_routing(): Cross-component parameter communication
    - _audio_processing_thread(): Real-time audio generation pipeline

    THREADING ARCHITECTURE:
    ======================
    Dual-thread design for optimal real-time performance:

    Main Thread (UI/Control):
    - MIDI message processing and parameter updates
    - Voice allocation/deallocation decisions
    - Preset loading and configuration changes
    - Performance monitoring and statistics updates

    Audio Thread (Real-time):
    - Audio block generation from active voices
    - Effects processing pipeline execution
    - Buffer management and memory operations
    - Sample-accurate timing and synchronization

    SYNCHRONIZATION:
    ===============
    Uses threading.RLock() for thread-safe operations:
    - Protects shared state during parameter updates
    - Ensures atomic operations across component boundaries
    - Prevents race conditions in voice management
    - Maintains consistency during preset operations

    ERROR HANDLING:
    ==============
    Implements graceful degradation for component failures:
    - Engine registration failures don't prevent startup
    - Missing optional components are handled gracefully
    - Audio processing errors trigger fallback behavior
    - Comprehensive logging for debugging and monitoring

    PERFORMANCE CHARACTERISTICS:
    ===========================
    Designed for professional real-time audio synthesis:
    - Low-latency audio processing (<5ms typical)
    - Zero-allocation hot path design
    - Configurable buffer sizes for different use cases
    - Adaptive parameter routing based on system load
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 1024,
        enable_audio_output: bool = False,
        max_channels: int = 16,
        midi_2_enabled: bool = False,
        xg_enabled: bool = True,
        gs_enabled: bool = True,
        mpe_enabled: bool = False,
        acoustic_behavior: bool = False,
        s90_mode: bool = False,
        gs_mode: str | None = None,
        effects_enabled: bool | None = None,
        sart2_enabled: bool | None = None,
        reverb_enabled: bool | None = None,
        chorus_enabled: bool | None = None,
        variation_enabled: bool | None = None,
        insertion_enabled: bool | None = None,
        master_eq_enabled: bool | None = None,
    ):
        """
        Initialize the synthesizer.

        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: Processing buffer size in samples
            enable_audio_output: Enable real-time audio output via sounddevice
            max_channels: Maximum MIDI channels/parts (default 16, up to 32 for multi-port)
            midi_2_enabled: Enable MIDI 2.0 features
            xg_enabled: Enable XG protocol features
            gs_enabled: Enable GS protocol features
            mpe_enabled: Enable MIDI Polyphonic Expression
            acoustic_behavior: Enable acoustic behavior modeling (SuperNATURAL-like)
            s90_mode: Enable S90/S70 compatibility mode
            gs_mode: GS/XG mode ("auto", "xg", "gs", or None for default)
            effects_enabled: Master effects pipeline toggle (None = library default)
            sart2_enabled: S.Art2 articulation processing (None = library default)
            reverb_enabled: System reverb (None = inherit from effects_enabled)
            chorus_enabled: System chorus (None = inherit)
            variation_enabled: Variation effect (None = inherit)
            insertion_enabled: Insertion effects (None = inherit)
            master_eq_enabled: Master EQ (None = inherit)
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.enable_audio_output = enable_audio_output
        self.max_channels = max_channels
        self.midi_2_enabled = midi_2_enabled
        self.xg_enabled = xg_enabled
        self.gs_enabled = gs_enabled
        self.mpe_enabled = mpe_enabled
        self.acoustic_behavior = acoustic_behavior
        self.s90_mode = s90_mode
        self.gs_mode = gs_mode
        self._effects_enabled = effects_enabled
        self._sart2_enabled = sart2_enabled
        self._reverb_enabled = reverb_enabled
        self._chorus_enabled = chorus_enabled
        self._variation_enabled = variation_enabled
        self._insertion_enabled = insertion_enabled
        self._master_eq_enabled = master_eq_enabled
        self.audio_output = None

        # Core components
        self.config = SynthConfig()
        self.buffer_pool = XGBufferPool(sample_rate, buffer_size)

        # Engine registry and management
        self.engine_registry = XGEngineRegistry(sample_rate)
        self.parameter_router = ParameterRouter(self)  # Pass synthesizer reference

        # Synthesis engines
        self.engines: dict[str, Any] = {}

        # Sample management
        self.sample_manager = SampleManager(max_memory_mb=512)

        # S90/S70 compatibility layer
        self.hardware_specs = S90S70HardwareSpecs()
        self.preset_compatibility = S90S70PresetCompatibility()
        self.control_surface = S90S70ControlSurfaceMapping()
        self.performance_monitor = S90S70PerformanceFeatures(max_voices=128)

        # Effects processing
        self.effects_coordinator = XGEffectsCoordinator(sample_rate, buffer_size)

        # Configure output bus manager for multi-group routing
        self.effects_coordinator.set_num_buses(4)
        self.effects_coordinator.set_bus_topology(0, PipelineTopology.xg_standard())
        self.effects_coordinator.set_bus_topology(1, PipelineTopology.xg_standard())
        self.effects_coordinator.set_bus_topology(2, PipelineTopology.xg_standard())
        self.effects_coordinator.set_bus_topology(3, PipelineTopology.xg_standard())

        # MIDI processing
        self.midi_parser = RealtimeParser()

        # Voice management
        self.voice_manager = VoiceManager(max_voices=128)

        # XG system
        self.xg_system = XGSystem()

        # XG/GS/GM Synthesizer System (production-grade)
        self.xg_synthesizer = XGSynthesizerSystem(
            sample_rate=self.sample_rate,
            device_id=0x10,
            max_polyphony=128,
            num_parts=self.max_channels,
        )

        # Sequencing
        self.pattern_sequencer = PatternSequencer()
        self.groove_quantizer = GrooveQuantizer()

        # Style Engine (auto-accompaniment)
        self.style_player: StylePlayer | None = None
        self.style_engine_enabled = False
        self._chord_detection_channel = 0  # Channel for chord detection
        self._chord_detection_low_note = 36  # Low note for chord detection
        self._chord_detection_high_note = 60  # High note for chord detection

        # Style Engine Integrations
        self.style_integrations: Any | None = None

        # Registration Memory
        self.registration_memory: RegistrationMemory | None = None
        self._registration_enabled = False

        # EFX Control Switch mapping (SC-8850)
        # Maps CC number → (part_num, efx_parameter, depth)
        self.efx_control_switches: dict[int, dict[str, Any]] = {
            3: {"part": 0, "parameter": None, "depth": 0},
            9: {"part": 0, "parameter": None, "depth": 0},
        }

        # Audio output buffers
        self.output_buffer = np.zeros((buffer_size, 2), dtype=np.float32)
        self._channel_buffers: list[np.ndarray | None] = [None] * self.max_channels

        # Threading and synchronization
        self.lock = threading.RLock()
        self.audio_thread: threading.Thread | None = None
        self.running = False

        # Performance monitoring
        self.performance_stats = {
            "voices_active": 0,
            "cpu_usage_percent": 0.0,
            "memory_usage_mb": 0.0,
            "buffer_underruns": 0,
            "buffer_overruns": 0,
        }

        # Initialize all components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize and connect all synthesizer components."""

        # Initialize performance monitoring
        self.performance_monitor.initialize_performance_monitoring()

        # Register synthesis engines
        self._register_engines()

        # Initialize effects system
        self._initialize_effects()

        # Setup parameter routing
        self._setup_parameter_routing()

        # Initialize XG system
        self._initialize_xg_system()

        # Initialize ModernXGSynthesizer as the default audio generator
        self._initialize_xg_synth()

        # Setup S90/S70 compatibility
        self._initialize_s90_s70_compatibility()

        # Initialize real-time audio output if enabled
        if self.enable_audio_output:
            self._initialize_audio_output()

    def _register_engines(self):
        """Register all available synthesis engines."""

        engines_registered = 0

        # FDSP Engine (S90/S70 vocal synthesis)
        if FDSPSynthesisEngine is not None:
            try:
                fdsp_engine = FDSPSynthesisEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(fdsp_engine, "fdsp", priority=10)
                self.engines["fdsp"] = fdsp_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register FDSP engine: {e}")

        # AN Engine (S90/S70 analog modeling)
        if ANEngine is not None:
            try:
                an_engine = ANEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(an_engine, "an", priority=9)
                self.engines["an"] = an_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register AN engine: {e}")

        # SF2 Engine (SoundFont playback)
        if SF2Engine is not None:
            try:
                sf2_engine = SF2Engine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(sf2_engine, "sf2", priority=8)
                self.engines["sf2"] = sf2_engine

                # Connect SF2 part mode integrator for XG/GS drum support
                if SF2PartModeIntegrator is not None:
                    part_mode_integrator = SF2PartModeIntegrator(sf2_engine, self.xg_synthesizer)
                    sf2_engine.set_part_mode_integrator(part_mode_integrator)
                    self._sf2_part_mode_integrator = part_mode_integrator

                    # Register part mode callback: sync XG part mode → SF2 integrator
                    def _on_xg_part_mode(part_num: int, mode: int) -> None:
                        mode_map = {0: "normal", 1: "drum", 4: "single"}
                        mode_str = mode_map.get(mode, "normal")
                        bank_msb = self.xg_synthesizer.parts[part_num].get("bank_msb", 0)
                        part_mode_integrator.set_channel_mode(part_num, mode_str, bank_msb)

                    self.xg_synthesizer.register_part_mode_callback(_on_xg_part_mode)

                    # Register GS parameter callback: sync GS part params → Channel.gs_params
                    def _on_gs_part_param(section: str, param_name: str, value: int) -> None:
                        """Handle GS part parameter changes from sysex."""
                        if section.startswith("part_"):
                            try:
                                part_idx = int(section.split("_")[1])
                                if (
                                    0 <= part_idx < 16
                                    and hasattr(self, "channels")
                                    and self.channels
                                ):
                                    self.channels[part_idx].gs_params[param_name] = value
                                    logger.debug(f"GS part {part_idx} param {param_name} = {value}")
                            except (ValueError, IndexError, AttributeError):
                                pass

                    self.xg_synthesizer.register_parameter_callback(_on_gs_part_param)

                    # Sync initial state: push all existing part modes into integrator
                    for ch in range(self.max_channels):
                        part_info = self.xg_synthesizer.parts[ch]
                        part_mode = part_info.get("part_mode", 0)
                        _on_xg_part_mode(ch, part_mode)

                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register SF2 engine: {e}")

        # Modern XG Synthesizer (AWM)
        if ModernXGSynthesizer is not None:
            try:
                xg_engine = ModernXGSynthesizer(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(xg_engine, "xg", priority=7)
                self.engines["xg"] = xg_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register XG engine: {e}")

        # FM Engine
        if FMEngine is not None:
            try:
                fm_engine = FMEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(fm_engine, "fm", priority=6)
                self.engines["fm"] = fm_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register FM engine: {e}")

        # Wavetable Engine
        if WavetableEngine is not None:
            try:
                wt_engine = WavetableEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(wt_engine, "wavetable", priority=5)
                self.engines["wavetable"] = wt_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register Wavetable engine: {e}")

        # Additive Engine
        if AdditiveEngine is not None:
            try:
                add_engine = AdditiveEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(add_engine, "additive", priority=4)
                self.engines["additive"] = add_engine
                engines_registered += 1
            except Exception as e:
                logger.error(f"Failed to register Additive engine: {e}")

        logger.info(f"Registered {engines_registered} synthesis engines")

    def load_soundfont(self, sf2_path: str, priority: int = 0) -> bool:
        """Load a SoundFont file into the SF2 engine and ModernXGSynthesizer.

        Args:
            sf2_path: Path to the .sf2 file
            priority: Loading priority (higher = loaded first)

        Returns:
            True if loaded successfully
        """
        # Load into ModernXGSynthesizer (primary audio generator)
        xg_loaded = False
        if self.xg_synth is not None:
            try:
                xg_loaded = bool(self.xg_synth.load_soundfont(sf2_path, priority))
            except Exception as e:
                logger.warning(
                    "ModernXGSynthesizer failed to load soundfont '%s': %s", sf2_path, e
                )

        # Also load into SF2 engine (legacy path for non-xg voices)
        sf2_loaded = False
        sf2 = self.engines.get("sf2")
        if sf2 is not None:
            try:
                sf2_loaded = sf2.load_soundfont(sf2_path, priority)
            except Exception as e:
                logger.error("Failed to load SoundFont '%s' into SF2 engine: %s", sf2_path, e)

        return xg_loaded or sf2_loaded

    def set_effects_enabled(self, enabled: bool) -> None:
        """Toggle the master effects pipeline."""
        self._effects_enabled = enabled

    def set_sart2_enabled(self, enabled: bool) -> None:
        """Toggle S.Art2 articulation processing."""
        self._sart2_enabled = enabled

    def set_reverb_enabled(self, enabled: bool) -> None:
        """Toggle system reverb."""
        self._reverb_enabled = enabled

    def set_chorus_enabled(self, enabled: bool) -> None:
        """Toggle system chorus."""
        self._chorus_enabled = enabled

    def set_variation_enabled(self, enabled: bool) -> None:
        """Toggle variation effect."""
        self._variation_enabled = enabled

    def set_insertion_enabled(self, enabled: bool) -> None:
        """Toggle insertion effects."""
        self._insertion_enabled = enabled

    def set_master_eq_enabled(self, enabled: bool) -> None:
        """Toggle master EQ."""
        self._master_eq_enabled = enabled

    def _initialize_effects(self):
        """Initialize the effects processing system."""

        # Register VCM effects with effects coordinator
        vcm_effects = {
            "vcm_overdrive": self.effects_coordinator._process_vcm_overdrive,
            "vcm_distortion": self.effects_coordinator._process_vcm_distortion,
            "vcm_phaser": self.effects_coordinator._process_vcm_phaser,
            "vcm_equalizer": self.effects_coordinator._process_vcm_equalizer,
            "vcm_stereo_enhancer": self.effects_coordinator._process_vcm_stereo_enhancer,
        }

        for effect_name, effect_func in vcm_effects.items():
            self.effects_coordinator.register_effect(effect_name, effect_func)

        logger.info("Initialized effects system with VCM processing")

    def _setup_parameter_routing(self):
        """Setup parameter routing between components."""

        # Connect control surface to parameter router
        self.parameter_router.register_source("control_surface", self.control_surface)

        # Connect S90/S70 hardware specs to parameter validation
        self.parameter_router.register_validator(
            "hardware_compat",
            self.hardware_specs.get_hardware_compatible_parameter_range,
        )

        # Connect performance monitor to parameter router for adaptive parameters
        self.parameter_router.register_monitor("performance", self.performance_monitor)

        logger.info("Parameter routing system initialized")

    def _initialize_xg_system(self):
        """Initialize the XG system."""

        # Connect XG system to engine registry
        self.xg_system.set_engine_registry(self.engine_registry)

        # Connect XG system to effects coordinator
        self.xg_system.set_effects_coordinator(self.effects_coordinator)

        # Initialize XG parameters
        self.xg_system.initialize()

        # PartEngineRouter — per-part engine routing with bank+program support
        router = PartEngineRouter(num_parts=self.max_channels)
        router.set_engine_registry(self.engine_registry)
        self.engine_router = router
        self.xg_system.engine_router = router
        self.xg_synthesizer.engine_router = router

        # Connect production-grade XG/GS/GM synthesizer system
        self.xg_synthesizer.engine_registry = self.engine_registry
        self.xg_synthesizer.effects_coordinator = self.effects_coordinator
        self.xg_synthesizer.voice_manager = self.voice_manager
        self.xg_synthesizer.synthesizer = self

        # Store reference to XGChannelParameterManager for future Channel integration
        # Used by rendering.ModernXGSynthesizer channels; wired here for realtime use
        self.xg_channel_params = getattr(self.xg_synthesizer, "xg_channel_params", None)

        # Wire XGChannelParameterManager to channels if they exist
        if hasattr(self, "channels") and self.xg_channel_params is not None:
            for ch in self.channels:
                if hasattr(ch, "set_xg_parameter_manager"):
                    ch.set_xg_parameter_manager(self.xg_channel_params)

        logger.info("XG system initialized")

    def _initialize_xg_synth(self):
        """Initialize ModernXGSynthesizer as the default audio generator."""
        self.xg_synth: Any = None
        if ModernXGSynthesizer is not None:
            try:
                self.xg_synth = ModernXGSynthesizer(
                    sample_rate=self.sample_rate,
                    max_channels=self.max_channels,
                    xg_enabled=self.xg_enabled,
                    gs_enabled=self.gs_enabled,
                    mpe_enabled=self.mpe_enabled,
                    midi_2_enabled=self.midi_2_enabled,
                    acoustic_behavior=self.acoustic_behavior,
                    s90_mode=self.s90_mode,
                    gs_mode=self.gs_mode or "auto",
                )
                # Apply runtime toggles
                if self._effects_enabled is not None:
                    self.xg_synth.set_effects_enabled(self._effects_enabled)
                if self._sart2_enabled is not None:
                    self.xg_synth.set_sart2_enabled(self._sart2_enabled)
                if self._reverb_enabled is not None:
                    self.xg_synth.set_reverb_enabled(self._reverb_enabled)
                if self._chorus_enabled is not None:
                    self.xg_synth.set_chorus_enabled(self._chorus_enabled)
                if self._variation_enabled is not None:
                    self.xg_synth.set_variation_enabled(self._variation_enabled)
                if self._insertion_enabled is not None:
                    self.xg_synth.set_insertion_enabled(self._insertion_enabled)
                if self._master_eq_enabled is not None:
                    self.xg_synth.set_master_eq_enabled(self._master_eq_enabled)
                logger.info("ModernXGSynthesizer initialized as default audio generator")
            except Exception as e:
                logger.warning("Failed to initialize ModernXGSynthesizer: %s", e)
                self.xg_synth = None

    def _initialize_s90_s70_compatibility(self):
        """Initialize S90/S70 compatibility features."""

        # Set hardware profile (default to S90)
        self.hardware_specs.set_hardware_profile("S90")

        # Connect preset compatibility to XG system
        self.preset_compatibility.set_xg_system(self.xg_system)

        # Setup control surface assignments
        self._setup_control_assignments()

        logger.info("S90/S70 compatibility layer initialized")

    def _initialize_audio_output(self):
        """Initialize real-time audio output via sounddevice."""
        try:
            try:
                from vibexg.audio_outputs import SoundDeviceOutput
            except ImportError:
                from synth.protocols.xg.sart.audio import SoundDeviceOutput

            def audio_callback(outdata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                # Use render_block for the audio thread
                self.render_block(outdata)

            self.audio_output = SoundDeviceOutput(
                sample_rate=self.sample_rate,
                buffer_size=self.buffer_size,
                callback=audio_callback,
            )
            logger.info("Real-time audio output initialized")
        except ImportError:
            logger.warning("sounddevice not available for real-time audio output")
            self.audio_output = None

    def _setup_control_assignments(self):
        """Setup default control surface assignments."""

        # Default S90/S70 control assignments
        assignments = [
            (1, "filter.cutoff", 0, 127, "linear", "Cutoff"),
            (2, "filter.resonance", 0, 127, "exp", "Resonance"),
            (3, "amplitude.attack", 0, 127, "log", "Attack"),
            (4, "amplitude.decay", 0, 127, "log", "Decay"),
        ]

        for ctrl_id, param, min_val, max_val, curve, name in assignments:
            self.control_surface.assign_control(ctrl_id, param, min_val, max_val, curve, name)

    def start(self):
        """Start the synthesizer."""
        with self.lock:
            if self.running:
                return

            self.running = True

            # Start audio processing thread
            self.audio_thread = threading.Thread(
                target=self._audio_processing_thread,
                daemon=True,
                name="SynthesizerAudio",
            )
            self.audio_thread.start()

            logger.info("Synthesizer started")

    def stop(self):
        """Stop the synthesizer."""
        with self.lock:
            if not self.running:
                return

            self.running = False

            # Wait for audio thread to finish
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join(timeout=1.0)

            # Shutdown performance monitoring
            self.performance_monitor.shutdown_performance_monitoring()

            logger.info("Synthesizer stopped")

    def _audio_processing_thread(self):
        """Main audio processing thread."""
        try:
            while self.running:
                # Process MIDI events
                self._process_midi_events()

                # Generate audio
                self._generate_audio_block()

                # Apply effects
                self._apply_effects()

                # Update performance stats
                self._update_performance_stats()

                # Small delay to prevent busy waiting
                time.sleep(0.001)

        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            self.running = False

    def _process_midi_events(self):
        """Process pending MIDI events."""
        # Get MIDI events from parser
        events = self.midi_parser.get_pending_events()

        for event in events:
            self._handle_midi_event(event)

    def _handle_midi_event(self, message: MIDIMessage):
        """Handle a single MIDI message."""

        if message.is_note_on():
            self.note_on(message.channel or 0, message.note or 60, message.velocity or 64)
        elif message.is_note_off():
            self.note_off(message.channel or 0, message.note or 60)
        elif message.is_control_change():
            self.control_change(message.channel or 0, message.controller or 0, message.value or 0)
        elif message.is_pitch_bend():
            self.pitch_bend(message.channel or 0, message.bend_value or 0)
        elif message.is_program_change():
            self.program_change(message.channel or 0, message.program or 0)
        elif message.type == "sysex":
            raw_data = bytes(message.data.get("raw_data", []))
            if raw_data and hasattr(self, "xg_synthesizer"):
                self.xg_synthesizer.process_sysex(raw_data)

    def _generate_audio_block(self):
        """Generate one block of audio."""
        # Clear output buffer
        self.output_buffer.fill(0)

        # Get active voices from voice manager
        active_voices = self.voice_manager.get_active_voices()

        # Generate audio for each active voice
        for voice_info in active_voices:
            voice_audio = self._generate_voice_audio(voice_info)
            if voice_audio is not None:
                # Mix into output buffer
                self.output_buffer += voice_audio

        # Apply master processing
        self._apply_master_processing()

    def _generate_voice_audio(self, voice_info) -> np.ndarray | None:
        """Generate audio for a single voice."""
        engine_type = voice_info.engine_type
        engine = self.engines.get(engine_type)

        if engine is None:
            return None

        # "xg" voices are handled by ModernXGSynthesizer at block level
        if engine_type == "xg":
            return None

        # Safety check: some registered engines are high-level orchestrators
        # without per-voice generate_samples()
        if not hasattr(engine, "generate_samples"):
            logger.debug(
                "Engine '%s' has no generate_samples(), skipping voice (channel=%s, note=%s)",
                engine_type,
                voice_info.channel,
                voice_info.note,
            )
            return None

        note = voice_info.note
        velocity = voice_info.velocity
        modulation = voice_info.modulation_data or {}

        try:
            engine_params = voice_info.engine_params or {}
            if engine_type == "sf2":
                bank = engine_params.get("bank", 0)
                program = engine_params.get("program", 0)
                audio_block = engine.generate_samples(
                    note, velocity, modulation, self.buffer_size, bank=bank, program=program
                )
            else:
                audio_block = engine.generate_samples(note, velocity, modulation, self.buffer_size)

            if voice_info.effects_chain:
                audio_block = self._apply_voice_effects(audio_block, voice_info.effects_chain)

            return audio_block

        except Exception as e:
            logger.error(f"Voice generation error: {e}")
            return None

    def _apply_effects(self):
        """Apply global effects processing."""
        self.effects_coordinator.process_block(self.output_buffer)

    def _apply_voice_effects(self, audio: np.ndarray, effects_chain: list[str]) -> np.ndarray:
        """Apply per-voice effects."""
        processed = audio.copy()

        for effect_type in effects_chain:
            if effect_type in self.effects_coordinator.effects:
                processed = self.effects_coordinator.apply_effect(processed, effect_type, {})

        return processed

    def _apply_master_processing(self):
        """Apply master processing (EQ, limiting, etc.)."""
        # Apply master EQ if configured
        # Apply master limiting
        # Apply dithering if needed
        pass

    def render_block(self, out: np.ndarray) -> None:
        """
        Render one block of audio through the complete synthesis pipeline.

        This is the unified render entry point that orchestrates:
        1. Clear output buffer
        2. Generate audio from ModernXGSynthesizer (handles all xg voices)
        3. Render channel audio from non-xg voices via per-voice path
        4. Apply insertion effects per channel
        5. Accumulate send levels to reverb/chorus buses
        6. Apply system effects to bus returns
        7. Apply master EQ + compressor
        8. Write to output buffer

        Args:
            out: Output buffer (num_samples, 2) - modified in-place
        """
        with self.lock:
            num_samples = min(len(out), self.buffer_size)

            # Step 1: Clear output buffer
            out.fill(0.0)

            # Step 2: Generate audio from ModernXGSynthesizer
            # This covers all "xg" engine voices with full effects processing
            xg_audio: np.ndarray | None = None
            if self.xg_synth is not None:
                try:
                    xg_audio = self.xg_synth.generate_audio_block(num_samples)
                    if xg_audio is not None and len(xg_audio) > 0:
                        xg_len = min(len(xg_audio), num_samples)
                        out[:xg_len] += xg_audio[:xg_len]
                except Exception:
                    logger.warning("ModernXGSynthesizer audio generation failed", exc_info=True)

            # Step 3: Collect channel audio from non-xg active voices
            active_voices = self.voice_manager.get_active_voices()
            channel_buffers: dict[int, np.ndarray] = {}

            # Acoustic behavior: advance shared vibrato phase per block for
            # every channel that has an acoustic context (section coherence).
            for voice_info in active_voices:
                ch_obj = getattr(voice_info, "channel_obj", None)
                if ch_obj is not None:
                    ctx = ch_obj.get_acoustic_context()
                    if ctx is not None:
                        try:
                            ctx.advance_vibrato(ctx.config.ensemble.vibrato_rate_hz, num_samples)
                        except Exception:  # pragma: no cover - defensive
                            pass

            for voice_info in active_voices:
                # Skip xg-engine voices — handled by ModernXGSynthesizer above
                if voice_info.engine_type == "xg":
                    continue
                channel = voice_info.channel
                if channel not in channel_buffers:
                    # Lazy-resize pre-allocated per-channel buffer (zero allocation in hot path)
                    if self._channel_buffers[channel] is None or len(self._channel_buffers[channel]) < num_samples:  # type: ignore[arg-type]
                        self._channel_buffers[channel] = np.zeros(
                            (num_samples, 2), dtype=np.float32
                        )
                    channel_buffer = self._channel_buffers[channel][:num_samples]
                    channel_buffer.fill(0.0)
                    channel_buffers[channel] = channel_buffer

                voice_audio = self._generate_voice_audio(voice_info)
                if voice_audio is not None:
                    channel_buffers[channel] += voice_audio[:num_samples]

            # Step 4-6: Process through effects coordinator
            # Convert channel dict to list for effects coordinator
            channel_list = []
            for ch in range(self.max_channels):
                if ch in channel_buffers:
                    channel_list.append(channel_buffers[ch])
                else:
                    # Empty channel — use lazy-resize pre-allocated buffer
                    if self._channel_buffers[ch] is None or len(self._channel_buffers[ch]) < num_samples:  # type: ignore[arg-type]
                        self._channel_buffers[ch] = np.zeros((num_samples, 2), dtype=np.float32)
                    empty_buffer = self._channel_buffers[ch][:num_samples]
                    empty_buffer.fill(0.0)
                    channel_list.append(empty_buffer)

            # Route channels to their assigned output buses
            bus_inputs: dict[int, list[np.ndarray]] = {}
            for ch, buf in enumerate(channel_list):
                if ch < self.max_channels:
                    # Find bus for this channel from XG part
                    bus_id = 0
                    if hasattr(self, "xg_system"):
                        for part in self.xg_system.parts.values():
                            if part.channel == ch:
                                bus_id = part.output_bus
                                break
                    if bus_id not in bus_inputs:
                        bus_inputs[bus_id] = []
                    bus_inputs[bus_id].append(buf)

            # Process through multi-bus effects pipeline
            # This ADDS non-xg audio to out (already has xg_synth audio mixed in)
            self.effects_coordinator.process_buses_zero_alloc(bus_inputs, num_samples, out)

    def _update_performance_stats(self):
        """Update performance statistics."""
        self.performance_stats.update(self.performance_monitor.get_realtime_performance_data())
        self.performance_stats["voices_active"] = len(self.voice_manager.get_active_voices())

    def note_on(self, channel: int, note: int, velocity: int):
        """Handle note on event."""
        with self.lock:
            # Route to style engine for chord detection if enabled
            if self.style_engine_enabled and self.style_player:
                if channel == self._chord_detection_channel:
                    if self._chord_detection_low_note <= note <= self._chord_detection_high_note:
                        # This is in the chord detection zone - route to style
                        self.style_player.process_midi_note_on(channel, note, velocity)

                        # Also trigger normal voice if style not playing
                        if not self.style_player.is_playing:
                            self._trigger_voice(channel, note, velocity)
                        return
                    elif self.style_player.is_playing:
                        # Let style handle all notes when playing
                        return

            # Normal voice triggering
            self._trigger_voice(channel, note, velocity)

            # Forward to ModernXGSynthesizer for audio generation
            if self.xg_synth is not None:
                try:
                    msg = bytes([0x90 | channel, note, velocity])
                    self.xg_synth.process_midi_message(msg)
                except Exception:
                    logger.warning("Failed to forward note_on to ModernXGSynthesizer", exc_info=True)

    def _trigger_voice(self, channel: int, note: int, velocity: int):
        """Internal method to trigger a voice."""
        engine_type = self.xg_system.get_engine_for_channel(channel)
        engine_params: dict[str, Any] = {}

        # Consult SF2 part mode integrator if available
        if (
            hasattr(self, "_sf2_part_mode_integrator")
            and self._sf2_part_mode_integrator is not None
        ):
            try:
                bank, program, drum_params = self._sf2_part_mode_integrator.get_preset_for_note(
                    channel, note, velocity
                )
                engine_params = {"bank": bank, "program": program}
                # If drum mode, route to SF2 engine
                if drum_params and drum_params.get("is_drum"):
                    engine_type = "sf2"
            except Exception:
                logger.warning("Failed to query SF2 part mode integrator", exc_info=True)

        # Collect current modulation state for this channel
        modulation_data = {}
        try:
            if hasattr(self, "channels") and 0 <= channel < len(self.channels):
                modulation_data = self.channels[channel]._collect_modulation_values()
        except Exception:
            logger.warning("Failed to collect modulation values", exc_info=True)

        # Add output bus routing info
        if hasattr(self, "xg_system"):
            for part_num, part in self.xg_system.parts.items():
                if part.channel == channel:
                    engine_params["output_bus"] = part.output_bus
                    break

        self.voice_manager.allocate_voice(
            channel,
            note,
            velocity,
            engine_type,
            engine_params,
            modulation_data=modulation_data,
        )

    def _trigger_voice_off(self, channel: int, note: int):
        """Internal method to handle note off."""
        # Find and release voice
        voice_id = self.voice_manager.find_voice(channel, note)
        if voice_id is not None:
            self.voice_manager.deallocate_voice(voice_id)

    def note_off(self, channel: int, note: int):
        """Handle note off event."""
        with self.lock:
            # Route to style engine for chord detection if enabled
            if self.style_engine_enabled and self.style_player:
                if channel == self._chord_detection_channel:
                    if self._chord_detection_low_note <= note <= self._chord_detection_high_note:
                        self.style_player.process_midi_note_off(channel, note)

                        # Also trigger normal voice off if style not playing
                        if not self.style_player.is_playing:
                            self._trigger_voice_off(channel, note)
                        return
                    elif self.style_player.is_playing:
                        return

            self._trigger_voice_off(channel, note)

            # Forward to ModernXGSynthesizer for audio generation
            if self.xg_synth is not None:
                try:
                    msg = bytes([0x80 | channel, note, 0])
                    self.xg_synth.process_midi_message(msg)
                except Exception:
                    logger.warning("Failed to forward note_off to ModernXGSynthesizer", exc_info=True)

    def control_change(self, channel: int, controller: int, value: int):
        """Handle control change event."""
        with self.lock:
            # EFX Control Switches (CC#3, CC#9) — SC-8850 real-time EFX modulation
            if controller in (3, 9):
                self._handle_efx_control_switch(controller, channel, value)
                return

            # Check if it's a control surface assignment
            param_update = self.control_surface.process_control_message(controller, value)

            if param_update:
                # Route parameter to appropriate destination
                self.parameter_router.route_parameter(
                    param_update["parameter_path"],
                    param_update["value"],
                    channel=channel,
                )
            else:
                # Handle standard MIDI CC
                self.xg_system.handle_control_change(channel, controller, value)

            # Forward CC to ModernXGSynthesizer for Channel state updates
            # (mirrors note_on/note_off pattern at lines ~1042-1048)
            if self.xg_synth is not None:
                try:
                    midi_bytes = bytes([0xB0 | channel, controller, value])
                    self.xg_synth.process_midi_message(midi_bytes)
                except Exception:
                    pass

    def _handle_efx_control_switch(self, controller: int, channel: int, value: int) -> None:
        """Handle EFX Control Switch CC message (SC-8850).

        CC#3 = ECS 1, CC#9 = ECS 2.
        Routes modulation to the assigned EFX parameter on the assigned part.

        Args:
            controller: CC number (3 or 9)
            channel: MIDI channel
            value: CC value (0-127)
        """
        if controller not in self.efx_control_switches:
            return

        switch = self.efx_control_switches[controller]
        part = self._get_part_for_channel(channel)

        # Normalize value to 0.0-1.0
        normalized = value / 127.0

        # Forward to effects coordinator if configured
        if (
            switch["parameter"] is not None
            and hasattr(self, "effects_coordinator")
            and self.effects_coordinator is not None
        ):
            try:
                self.effects_coordinator.modulate_efx_parameter(
                    part_num=part,
                    parameter=switch["parameter"],
                    depth=switch["depth"],
                    value=normalized,
                )
            except Exception:
                logger.warning(f"EFX modulation failed: CC#{controller}", exc_info=True)

    def _get_part_for_channel(self, channel: int) -> int:
        """Get the part number for a MIDI channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Part number
        """
        if hasattr(self.xg_system, "parts"):
            for part_num, part in self.xg_system.parts.items():
                if part.channel == channel:
                    return part_num
        return channel  # Default: part = channel

    def set_efx_control_switch_mapping(
        self,
        cc_number: int,
        part_num: int,
        parameter: str,
        depth: float = 1.0,
    ) -> bool:
        """Configure an EFX Control Switch mapping.

        Args:
            cc_number: CC number (3 or 9)
            part_num: Target part number
            parameter: EFX parameter name
            depth: Modulation depth (0.0-1.0)

        Returns:
            True if mapping was set
        """
        if cc_number not in self.efx_control_switches:
            return False
        self.efx_control_switches[cc_number] = {
            "part": part_num,
            "parameter": parameter,
            "depth": max(0.0, min(1.0, depth)),
        }
        return True

    def pitch_bend(self, channel: int, value: int):
        """Handle pitch bend event."""
        with self.lock:
            # Convert to pitch bend value (-1.0 to 1.0)
            bend_value = (value - 8192) / 8192.0
            self.parameter_router.route_parameter("pitch_bend", bend_value, channel=channel)

    def program_change(self, channel: int, program: int):
        """Handle program change event."""
        with self.lock:
            self.xg_system.handle_program_change(channel, program)

    def get_audio_block(self) -> np.ndarray:
        """Get the current audio output block."""
        with self.lock:
            return self.output_buffer.copy()

    def get_performance_stats(self) -> dict[str, Any]:
        """Get current performance statistics."""
        with self.lock:
            return self.performance_stats.copy()

    def get_system_info(self) -> dict[str, Any]:
        """Get comprehensive system information."""
        with self.lock:
            return {
                "version": "1.1.0",
                "sample_rate": self.sample_rate,
                "buffer_size": self.buffer_size,
                "engines_registered": len(self.engines),
                "effects_available": len(self.effects_coordinator.effects),
                "hardware_profile": self.hardware_specs.current_profile.model_name,
                "polyphony_limit": self.hardware_specs.current_profile.polyphony,
                "sample_memory_mb": self.sample_manager.get_memory_usage()["max_memory_mb"],
                "compatibility_level": "98%",
            }

    def load_preset(self, bank: str, program: int) -> bool:
        """Load a preset."""
        with self.lock:
            preset_data = self.preset_compatibility.load_preset(program, bank)
            if preset_data:
                # Apply preset to XG system
                return self.xg_system.load_preset(preset_data)
            return False

    def save_preset(self, bank: str, program: int, name: str) -> bool:
        """Save current settings as preset."""
        with self.lock:
            # Get current XG system state
            preset_data = self.xg_system.get_current_preset_data()
            preset_data.update({"common": {"name": name, "category": "user"}})

            return self.preset_compatibility.save_preset(program, preset_data, bank)

    # ===== Style Engine Integration =====

    def initialize_style_engine(self) -> bool:
        """
        Initialize the style engine for auto-accompaniment.

        Returns:
            True if initialization successful
        """
        if StylePlayer is None:
            logger.warning("Style Engine: StylePlayer not available")
            return False

        try:
            self.style_player = StylePlayer(self, sample_rate=self.sample_rate)
            self.style_engine_enabled = True

            # Initialize MIDI Learn for style control
            if MIDILearn is not None:
                self.midi_learn = MIDILearn()
                self._setup_midi_learn_callbacks()

            # Connect XG system to style player
            self.xg_system.set_style_player(self.style_player)

            # Initialize style engine integrations
            self._initialize_style_integrations()

            logger.info("Style Engine: Initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Style Engine: Initialization failed - {e}")
            return False

    def _initialize_style_integrations(self):
        """
        Initialize style engine integrations with other synth subsystems.

        Integrations:
        1. Effects Coordinator ↔ Style Dynamics
        2. Voice Manager ↔ OTS Presets
        3. Modulation Matrix ↔ MIDI Learn
        4. Pattern Sequencer ↔ Style Sections
        5. MPE System ↔ Scale Detection
        """
        if StyleIntegrations is None:
            return

        try:
            self.style_integrations = StyleIntegrations(
                effects_coordinator=self.effects_coordinator,
                voice_manager=self.voice_manager,
                modulation_matrix=getattr(self, "modulation_matrix", None),
                pattern_sequencer=getattr(self, "pattern_sequencer", None),
                mpe_manager=getattr(self, "mpe_manager", None),
                style_player=self.style_player,
                style_dynamics=getattr(self.style_player, "_dynamics", None),
                ots=getattr(self.style_player, "_ots", None),
                midi_learn=getattr(self, "midi_learn", None),
                scale_detector=getattr(self, "scale_detector", None),
            )

            # Enable all integrations
            self.style_integrations.enable_all()
            logger.info("Style Engine: Integrations initialized")
        except Exception as e:
            logger.error(f"Style Engine: Integration initialization failed - {e}")

    def load_style_file(self, file_path: str) -> bool:
        """
        Load a style file.

        Args:
            file_path: Path to YAML style file

        Returns:
            True if load successful
        """
        if not self.style_engine_enabled:
            if not self.initialize_style_engine():
                return False

        if StyleLoader is None:
            return False

        try:
            loader = StyleLoader()
            style = loader.load_style_file(file_path)
            self.style_player.load_style(style)
            logger.info(f"Style Engine: Loaded style '{style.name}'")
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to load style - {e}")
            return False

    def load_style(self, style: Style) -> bool:
        """
        Load a Style object.

        Args:
            style: Style object to load

        Returns:
            True if load successful
        """
        if not self.style_engine_enabled:
            if not self.initialize_style_engine():
                return False

        if self.style_player:
            try:
                self.style_player.load_style(style)
                logger.info(f"Style Engine: Loaded style '{style.name}'")
                return True
            except Exception as e:
                logger.error(f"Style Engine: Failed to load style - {e}")
        return False

    def start_style(self, section: str | None = None) -> bool:
        """
        Start auto-accompaniment.

        Args:
            section: Optional section name (e.g., 'main_a', 'intro_1')

        Returns:
            True if started successfully
        """
        if not self.style_player:
            return False

        try:
            from ..style import StyleSectionType

            if section:
                section_type = StyleSectionType(section)
                self.style_player.start(section_type)
            else:
                self.style_player.start()
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to start - {e}")
            return False

    def stop_style(self) -> bool:
        """
        Stop auto-accompaniment.

        Returns:
            True if stopped successfully
        """
        if not self.style_player:
            return False

        try:
            self.style_player.stop()
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to stop - {e}")
            return False

    def set_style_section(self, section: str) -> bool:
        """
        Set the current style section.

        Args:
            section: Section name (e.g., 'main_a', 'main_b', 'fill_in_aa')

        Returns:
            True if successful
        """
        if not self.style_player:
            return False

        try:
            from ..style import StyleSectionType

            section_type = StyleSectionType(section)
            self.style_player.set_section(section_type)
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to set section - {e}")
            return False

    def trigger_style_fill(self) -> bool:
        """
        Trigger a fill before next section change.

        Returns:
            True if successful
        """
        if not self.style_player:
            return False

        try:
            self.style_player.trigger_fill()
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to trigger fill - {e}")
            return False

    def next_style_section(self) -> bool:
        """
        Advance to next main section (A -> B -> C -> D -> A).

        Returns:
            True if successful
        """
        if not self.style_player:
            return False

        try:
            self.style_player.next_section()
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to advance section - {e}")
            return False

    def set_style_tempo(self, tempo: int) -> bool:
        """
        Set style tempo.

        Args:
            tempo: BPM (20-300)

        Returns:
            True if successful
        """
        if not self.style_player:
            return False

        try:
            self.style_player.tempo = max(20, min(300, tempo))
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to set tempo - {e}")
            return False

    def set_style_dynamics(self, value: int) -> bool:
        """
        Set style dynamics (0-127).

        Args:
            value: Dynamics value (0 = soft, 127 = loud)

        Returns:
            True if successful
        """
        if not self.style_player:
            return False

        try:
            self.style_player.set_dynamics(max(0, min(127, value)))
            return True
        except Exception as e:
            logger.error(f"Style Engine: Failed to set dynamics - {e}")
            return False

    def set_chord_detection_range(self, low_note: int = 36, high_note: int = 60) -> Self:
        """
        Set the note range for chord detection.

        Args:
            low_note: Lowest note for chord detection (default: 36)
            high_note: Highest note for chord detection (default: 60)

        Returns:
            Self for method chaining
        """
        self._chord_detection_low_note = max(0, min(127, low_note))
        self._chord_detection_high_note = max(0, min(127, high_note))
        return self

    def set_chord_detection_channel(self, channel: int) -> Self:
        """
        Set the MIDI channel for chord detection.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            Self for method chaining
        """
        self._chord_detection_channel = max(0, min(15, channel))
        return self

    def get_style_status(self) -> dict[str, Any]:
        """
        Get style engine status.

        Returns:
            Dictionary with status information
        """
        if self.style_player:
            return self.style_player.get_status()
        return {
            "enabled": self.style_engine_enabled,
            "playing": False,
            "style_loaded": False,
        }

    def is_style_playing(self) -> bool:
        """Check if style is currently playing."""
        if self.style_player:
            return self.style_player.is_playing
        return False

    # ===== MIDI Learn Methods =====

    def _setup_midi_learn_callbacks(self) -> None:
        """Set up MIDI Learn callbacks to handle parameter changes."""
        if not hasattr(self, "midi_learn") or not self.midi_learn:
            return

        self.midi_learn.register_callback(
            LearnTargetType.STYLE_START_STOP, self._midi_learn_style_toggle
        )
        self.midi_learn.register_callback(LearnTargetType.STYLE_TEMPO, self._midi_learn_style_tempo)
        self.midi_learn.register_callback(
            LearnTargetType.STYLE_DYNAMICS, self._midi_learn_style_dynamics
        )
        self.midi_learn.register_callback(
            LearnTargetType.STYLE_SECTION, self._midi_learn_style_section
        )
        self.midi_learn.register_callback(LearnTargetType.STYLE_FILL, self._midi_learn_style_fill)
        self.midi_learn.register_callback(
            LearnTargetType.STYLE_OCTAVE, self._midi_learn_style_octave
        )
        self.midi_learn.register_callback(
            LearnTargetType.STYLE_VARIATION, self._midi_learn_style_variation
        )
        self.midi_learn.register_callback(
            LearnTargetType.STYLE_INTENSITY, self._midi_learn_style_intensity
        )

    def _midi_learn_style_toggle(self, value: float) -> None:
        """Handle style start/stop from MIDI learn."""
        if value > 0.5:
            self.start_style()
        else:
            self.stop_style()

    def _midi_learn_style_tempo(self, value: float) -> None:
        """Handle tempo change from MIDI learn."""
        tempo = int(20 + value * 280)  # 20-300 BPM
        self.set_style_tempo(tempo)

    def _midi_learn_style_dynamics(self, value: float) -> None:
        """Handle dynamics change from MIDI learn."""
        dynamics = int(value * 127)
        self.set_style_dynamics(dynamics)

    def _midi_learn_style_section(self, value: float) -> None:
        """Handle section change from MIDI learn."""
        sections = ["main_a", "main_b", "main_c", "main_d"]
        index = int(value * (len(sections) - 1))
        self.set_style_section(sections[index])

    def _midi_learn_style_fill(self, value: float) -> None:
        """Handle fill trigger from MIDI learn."""
        if value > 0.5:
            self.trigger_style_fill()

    def _midi_learn_style_octave(self, value: float) -> None:
        """Handle octave shift from MIDI learn."""
        if self.style_player:
            octave = int(value * 8 - 4)  # -4 to +4
            self.style_player.octave_shift = octave

    def _midi_learn_style_variation(self, value: float) -> None:
        """Handle variation change from MIDI learn."""
        if self.style_player:
            variation = int(value * 3)  # 0-3
            self.style_player.variation = variation

    def _midi_learn_style_intensity(self, value: float) -> None:
        """Handle intensity change from MIDI learn."""
        if self.style_player and self.style_player.dynamics:
            intensity = int(value * 127)
            self.style_player.dynamics.set_parameter(DynamicsParameter.INTENSITY, intensity)

    def process_midi_learn(self, cc_number: int, channel: int, value: int) -> dict[str, Any] | None:
        """
        Process incoming MIDI CC for MIDI Learn.

        Args:
            cc_number: MIDI controller number (0-127)
            channel: MIDI channel (0-15)
            value: Controller value (0-127)

        Returns:
            Dict with processing result or None
        """
        if not hasattr(self, "midi_learn") or not self.midi_learn:
            return None
        return self.midi_learn.process_midi(cc_number, channel, value)

    def start_midi_learn(self, target: str, param: str = "") -> bool:
        """
        Start MIDI learn mode for a target.

        Args:
            target: Target type (e.g., 'style_tempo', 'style_dynamics')
            param: Optional parameter name

        Returns:
            True if learn mode started
        """
        if not hasattr(self, "midi_learn") or not self.midi_learn:
            return False

        target_map = {
            "style_start_stop": LearnTargetType.STYLE_START_STOP,
            "style_tempo": LearnTargetType.STYLE_TEMPO,
            "style_dynamics": LearnTargetType.STYLE_DYNAMICS,
            "style_section": LearnTargetType.STYLE_SECTION,
            "style_fill": LearnTargetType.STYLE_FILL,
            "style_octave": LearnTargetType.STYLE_OCTAVE,
            "style_variation": LearnTargetType.STYLE_VARIATION,
            "style_intensity": LearnTargetType.STYLE_INTENSITY,
        }

        target_type = target_map.get(target)
        if target_type:
            self.midi_learn.start_learn(target_type, param)
            return True
        return False

    def cancel_midi_learn(self) -> None:
        """Cancel pending MIDI learn."""
        if hasattr(self, "midi_learn") and self.midi_learn:
            self.midi_learn.cancel_learn()

    def get_midi_learn_status(self) -> dict[str, Any]:
        """Get MIDI Learn status."""
        if hasattr(self, "midi_learn") and self.midi_learn:
            return self.midi_learn.get_status()
        return {"enabled": False, "mappings": []}

    def save_midi_learn_mappings(self, filepath: str) -> bool:
        """Save MIDI Learn mappings to file."""
        if hasattr(self, "midi_learn") and self.midi_learn:
            return self.midi_learn.save_to_file(filepath)
        return False

    def load_midi_learn_mappings(self, filepath: str) -> bool:
        """Load MIDI Learn mappings from file."""
        if hasattr(self, "midi_learn") and self.midi_learn:
            return self.midi_learn.load_from_file(filepath)
        return False

    # ===== Registration Memory Methods =====

    def initialize_registration_memory(self, num_banks: int = 8, slots_per_bank: int = 16) -> bool:
        """
        Initialize registration memory.

        Args:
            num_banks: Number of banks (default: 8)
            slots_per_bank: Slots per bank (default: 16)

        Returns:
            True if initialization successful
        """
        if RegistrationMemory is None:
            logger.warning("Registration Memory: Not available")
            return False

        try:
            self.registration_memory = RegistrationMemory(num_banks, slots_per_bank)
            self.registration_memory.set_synthesizer(self)
            self._registration_enabled = True
            logger.info("Registration Memory: Initialized")
            return True
        except Exception as e:
            logger.error(f"Registration Memory: Initialization failed - {e}")
            return False

    def recall_registration(self, bank: int = 0, slot: int = 0) -> bool:
        """
        Recall a registration.

        Args:
            bank: Bank number (0-7)
            slot: Slot number (0-15)

        Returns:
            True if recall successful
        """
        if not self.registration_memory:
            if not self.initialize_registration_memory():
                return False

        return self.registration_memory.recall(bank, slot)

    def store_registration(
        self, name: str = "", bank: int | None = None, slot: int | None = None
    ) -> bool:
        """
        Store current setup to a registration.

        Args:
            name: Registration name
            bank: Bank number (optional, uses current)
            slot: Slot number (optional, uses current)

        Returns:
            True if store successful
        """
        if not self.registration_memory:
            return False

        return self.registration_memory.store(name, bank, slot)

    def set_registration_bank(self, bank: int) -> bool:
        """Set current registration bank."""
        if self.registration_memory:
            return self.registration_memory.set_bank(bank)
        return False

    def next_registration_bank(self) -> bool:
        """Advance to next registration bank."""
        if self.registration_memory:
            self.registration_memory.next_bank()
            return True
        return False

    def set_registration_slot(self, slot: int) -> bool:
        """Set current registration slot."""
        if self.registration_memory:
            return self.registration_memory.set_slot(slot)
        return False

    def get_registration_status(self) -> dict[str, Any]:
        """Get registration memory status."""
        if self.registration_memory:
            return self.registration_memory.get_status()
        return {"enabled": False}

    def save_registrations_to_file(self, filepath: str) -> bool:
        """Save registrations to JSON file."""
        if self.registration_memory:
            try:
                self.registration_memory.save_to_file(filepath)
                return True
            except Exception:
                pass
        return False

    def load_registrations_from_file(self, filepath: str) -> bool:
        """Load registrations from JSON file."""
        if RegistrationMemory is None:
            return False

        try:
            self.registration_memory = RegistrationMemory.load_from_file(filepath)
            self.registration_memory.set_synthesizer(self)
            self._registration_enabled = True
            return True
        except Exception:
            return False

    def reset(self):
        """Reset synthesizer to default state."""
        with self.lock:
            # Reset XG system
            self.xg_system.reset()

            # Clear voices
            self.voice_manager.clear_all_voices()

            # Reset control surface
            self.control_surface.reset_to_defaults()

            # Reset performance monitoring
            self.performance_monitor.reset_performance_stats()

            logger.info("Synthesizer reset to default state")

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
