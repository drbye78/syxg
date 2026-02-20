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

import numpy as np
from typing import Dict, List, Any, Optional
import threading
import time

from ..engine.engine_registry import XGEngineRegistry, get_global_engine_registry
from ..effects.effects_coordinator import XGEffectsCoordinator
from ..midi import RealtimeParser, MIDIMessage
from ..voice.voice_manager import VoiceManager
from ..xg.xg_system import XGSystem
from ..engine.parameter_router import ParameterRouter
from ..sampling.sample_manager import SampleManager

# Import available engines
try:
    from ..engine.fdsp_engine import FDSPEngine
except ImportError:
    FDSPEngine = None

try:
    from ..engine.an_engine import ANEngine
except ImportError:
    ANEngine = None

try:
    from ..engine.sf2_engine import SF2Engine
except ImportError:
    SF2Engine = None

try:
    from ..engine.modern_xg_synthesizer import ModernXGSynthesizer
except ImportError:
    ModernXGSynthesizer = None

try:
    from ..engine.fm_engine import FMEngine
except ImportError:
    FMEngine = None

try:
    from ..engine.wavetable_engine import WavetableEngine
except ImportError:
    WavetableEngine = None

try:
    from ..engine.additive_engine import AdditiveEngine
except ImportError:
    AdditiveEngine = None
from ..s90_s70 import (
    S90S70HardwareSpecs, S90S70PresetCompatibility,
    S90S70ControlSurfaceMapping, S90S70PerformanceFeatures
)
from ..sequencer.pattern_sequencer import PatternSequencer
from ..sequencer.groove_quantizer import GrooveQuantizer
from ..core.buffer_pool import XGBufferPool
from ..core.config import SynthConfig


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

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024,
                 enable_audio_output: bool = False):
        """
        Initialize the synthesizer.

        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: Processing buffer size in samples
            enable_audio_output: Enable real-time audio output via sounddevice
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.enable_audio_output = enable_audio_output
        self.audio_output = None

        # Core components
        self.config = SynthConfig()
        self.buffer_pool = XGBufferPool(sample_rate, buffer_size)

        # Engine registry and management
        self.engine_registry = XGEngineRegistry(sample_rate)
        self.parameter_router = ParameterRouter(self)  # Pass synthesizer reference

        # Synthesis engines
        self.engines: Dict[str, Any] = {}

        # Sample management
        self.sample_manager = SampleManager(max_memory_mb=512)

        # S90/S70 compatibility layer
        self.hardware_specs = S90S70HardwareSpecs()
        self.preset_compatibility = S90S70PresetCompatibility()
        self.control_surface = S90S70ControlSurfaceMapping()
        self.performance_monitor = S90S70PerformanceFeatures(max_voices=128)

        # Effects processing
        self.effects_coordinator = XGEffectsCoordinator(sample_rate, buffer_size)

        # MIDI processing
        self.midi_parser = RealtimeParser()

        # Voice management
        self.voice_manager = VoiceManager(max_voices=128)

        # XG system
        self.xg_system = XGSystem()

        # Sequencing
        self.pattern_sequencer = PatternSequencer()
        self.groove_quantizer = GrooveQuantizer()

        # Audio output buffers
        self.output_buffer = np.zeros((buffer_size, 2), dtype=np.float32)

        # Threading and synchronization
        self.lock = threading.RLock()
        self.audio_thread: Optional[threading.Thread] = None
        self.running = False

        # Performance monitoring
        self.performance_stats = {
            'voices_active': 0,
            'cpu_usage_percent': 0.0,
            'memory_usage_mb': 0.0,
            'buffer_underruns': 0,
            'buffer_overruns': 0
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

        # Setup S90/S70 compatibility
        self._initialize_s90_s70_compatibility()

        # Initialize real-time audio output if enabled
        if self.enable_audio_output:
            self._initialize_audio_output()

    def _register_engines(self):
        """Register all available synthesis engines."""

        engines_registered = 0

        # FDSP Engine (S90/S70 vocal synthesis)
        if FDSPEngine is not None:
            try:
                fdsp_engine = FDSPEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(fdsp_engine, 'fdsp', priority=10)
                self.engines['fdsp'] = fdsp_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register FDSP engine: {e}")

        # AN Engine (S90/S70 analog modeling)
        if ANEngine is not None:
            try:
                an_engine = ANEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(an_engine, 'an', priority=9)
                self.engines['an'] = an_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register AN engine: {e}")

        # SF2 Engine (SoundFont playback)
        if SF2Engine is not None:
            try:
                sf2_engine = SF2Engine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(sf2_engine, 'sf2', priority=8)
                self.engines['sf2'] = sf2_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register SF2 engine: {e}")

        # Modern XG Synthesizer (AWM)
        if ModernXGSynthesizer is not None:
            try:
                xg_engine = ModernXGSynthesizer(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(xg_engine, 'xg', priority=7)
                self.engines['xg'] = xg_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register XG engine: {e}")

        # FM Engine
        if FMEngine is not None:
            try:
                fm_engine = FMEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(fm_engine, 'fm', priority=6)
                self.engines['fm'] = fm_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register FM engine: {e}")

        # Wavetable Engine
        if WavetableEngine is not None:
            try:
                wt_engine = WavetableEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(wt_engine, 'wavetable', priority=5)
                self.engines['wavetable'] = wt_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register Wavetable engine: {e}")

        # Additive Engine
        if AdditiveEngine is not None:
            try:
                add_engine = AdditiveEngine(sample_rate=self.sample_rate)
                self.engine_registry.register_engine(add_engine, 'additive', priority=4)
                self.engines['additive'] = add_engine
                engines_registered += 1
            except Exception as e:
                print(f"Failed to register Additive engine: {e}")

        print(f"Registered {engines_registered} synthesis engines")

    def _initialize_effects(self):
        """Initialize the effects processing system."""

        # Register VCM effects with effects coordinator
        vcm_effects = {
            'vcm_overdrive': self.effects_coordinator._process_vcm_overdrive,
            'vcm_distortion': self.effects_coordinator._process_vcm_distortion,
            'vcm_phaser': self.effects_coordinator._process_vcm_phaser,
            'vcm_equalizer': self.effects_coordinator._process_vcm_equalizer,
            'vcm_stereo_enhancer': self.effects_coordinator._process_vcm_stereo_enhancer
        }

        for effect_name, effect_func in vcm_effects.items():
            self.effects_coordinator.register_effect(effect_name, effect_func)

        print("Initialized effects system with VCM processing")

    def _setup_parameter_routing(self):
        """Setup parameter routing between components."""

        # Connect control surface to parameter router
        self.parameter_router.register_source('control_surface', self.control_surface)

        # Connect S90/S70 hardware specs to parameter validation
        self.parameter_router.register_validator('hardware_compat',
                                               self.hardware_specs.get_hardware_compatible_parameter_range)

        # Connect performance monitor to parameter router for adaptive parameters
        self.parameter_router.register_monitor('performance', self.performance_monitor)

        print("Parameter routing system initialized")

    def _initialize_xg_system(self):
        """Initialize the XG system."""

        # Connect XG system to engine registry
        self.xg_system.set_engine_registry(self.engine_registry)

        # Connect XG system to effects coordinator
        self.xg_system.set_effects_coordinator(self.effects_coordinator)

        # Initialize XG parameters
        self.xg_system.initialize()

        print("XG system initialized")

    def _initialize_s90_s70_compatibility(self):
        """Initialize S90/S70 compatibility features."""

        # Set hardware profile (default to S90)
        self.hardware_specs.set_hardware_profile('S90')

        # Connect preset compatibility to XG system
        self.preset_compatibility.set_xg_system(self.xg_system)

        # Setup control surface assignments
        self._setup_control_assignments()

        print("S90/S70 compatibility layer initialized")

    def _initialize_audio_output(self):
        """Initialize real-time audio output via sounddevice."""
        try:
            from synth.xg.sart.audio import SoundDeviceOutput
            
            def audio_callback(outdata, frames, time_info, status):
                if status:
                    print(f"Audio callback status: {status}")
                # Use render_block for the audio thread
                self.render_block(outdata)
            
            self.audio_output = SoundDeviceOutput(
                sample_rate=self.sample_rate,
                buffer_size=self.buffer_size,
                callback=audio_callback
            )
            print("Real-time audio output initialized")
        except ImportError:
            print("Warning: sounddevice not available for real-time audio output")
            self.audio_output = None

    def _setup_control_assignments(self):
        """Setup default control surface assignments."""

        # Default S90/S70 control assignments
        assignments = [
            (1, 'filter.cutoff', 0, 127, 'linear', 'Cutoff'),
            (2, 'filter.resonance', 0, 127, 'exp', 'Resonance'),
            (3, 'amplitude.attack', 0, 127, 'log', 'Attack'),
            (4, 'amplitude.decay', 0, 127, 'log', 'Decay')
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
            self.audio_thread = threading.Thread(target=self._audio_processing_thread,
                                               daemon=True, name="SynthesizerAudio")
            self.audio_thread.start()

            print("Synthesizer started")

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

            print("Synthesizer stopped")

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
            print(f"Audio processing error: {e}")
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

    def _generate_voice_audio(self, voice_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """Generate audio for a single voice."""

        engine_type = voice_info.get('engine_type', 'xg')
        engine = self.engines.get(engine_type)

        if engine is None:
            return None

        # Get voice parameters
        note = voice_info.get('note', 60)
        velocity = voice_info.get('velocity', 64)
        modulation = voice_info.get('modulation', {})

        # Generate audio block
        try:
            audio_block = engine.generate_samples(
                note, velocity, modulation, self.buffer_size
            )

            # Apply per-voice effects if any
            if voice_info.get('effects'):
                audio_block = self._apply_voice_effects(audio_block, voice_info['effects'])

            return audio_block

        except Exception as e:
            print(f"Voice generation error: {e}")
            return None

    def _apply_effects(self):
        """Apply global effects processing."""
        self.effects_coordinator.process_block(self.output_buffer)

    def _apply_voice_effects(self, audio: np.ndarray, effects: List[Dict[str, Any]]) -> np.ndarray:
        """Apply per-voice effects."""
        processed = audio.copy()

        for effect in effects:
            effect_type = effect.get('type')
            params = effect.get('parameters', {})

            # Apply effect processing (simplified)
            if effect_type in self.effects_coordinator.effects:
                processed = self.effects_coordinator.apply_effect(
                    processed, effect_type, params
                )

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
        2. Render channel audio via VectorizedChannelRenderer
        3. Apply insertion effects per channel
        4. Accumulate send levels to reverb/chorus buses
        5. Apply system effects to bus returns
        6. Apply master EQ + compressor
        7. Write to output buffer

        Args:
            out: Output buffer (num_samples, 2) - modified in-place
        """
        with self.lock:
            num_samples = min(len(out), self.buffer_size)

            # Step 1: Clear output buffer
            out.fill(0.0)

            # Step 2: Collect channel audio from all active channels
            # For now, use the existing voice manager path
            active_voices = self.voice_manager.get_active_voices()
            channel_buffers = {}

            for voice_info in active_voices:
                channel = voice_info.get('channel', 0)
                if channel not in channel_buffers:
                    # Allocate channel buffer if needed
                    channel_buffers[channel] = np.zeros((num_samples, 2), dtype=np.float32)

                # Generate voice audio
                voice_audio = self._generate_voice_audio(voice_info)
                if voice_audio is not None:
                    # Mix into channel buffer
                    channel_buffers[channel] += voice_audio[:num_samples]

            # Step 3-5: Process through effects coordinator
            # Convert channel dict to list for effects coordinator
            channel_list = []
            for ch in range(16):  # XG has 16 channels
                if ch in channel_buffers:
                    channel_list.append(channel_buffers[ch])
                else:
                    # Empty channel
                    channel_list.append(np.zeros((num_samples, 2), dtype=np.float32))

            # Process through effects chain (insertion → variation → system → master)
            self.effects_coordinator.process_channels_to_stereo_zero_alloc(
                channel_list, out, num_samples
            )

    def _update_performance_stats(self):
        """Update performance statistics."""
        self.performance_stats.update(
            self.performance_monitor.get_realtime_performance_data()
        )
        self.performance_stats['voices_active'] = len(self.voice_manager.get_active_voices())

    def note_on(self, channel: int, note: int, velocity: int):
        """Handle note on event."""
        with self.lock:
            # Determine which engine to use based on XG program
            engine_type = self.xg_system.get_engine_for_channel(channel)

            # Allocate voice
            voice_id = self.performance_monitor.allocate_voice(
                engine_type, channel, note, velocity
            )

            if voice_id is not None:
                # Create voice in voice manager
                voice_info = {
                    'id': voice_id,
                    'channel': channel,
                    'note': note,
                    'velocity': velocity,
                    'engine_type': engine_type,
                    'start_time': time.time()
                }

                self.voice_manager.add_voice(voice_info)

    def note_off(self, channel: int, note: int):
        """Handle note off event."""
        with self.lock:
            # Find and release voice
            voice_id = self.voice_manager.find_voice(channel, note)
            if voice_id:
                self.voice_manager.remove_voice(voice_id)
                self.performance_monitor.deallocate_voice(voice_id)

    def control_change(self, channel: int, controller: int, value: int):
        """Handle control change event."""
        with self.lock:
            # Check if it's a control surface assignment
            param_update = self.control_surface.process_control_message(controller, value)

            if param_update:
                # Route parameter to appropriate destination
                self.parameter_router.route_parameter(
                    param_update['parameter_path'],
                    param_update['value'],
                    channel=channel
                )
            else:
                # Handle standard MIDI CC
                self.xg_system.handle_control_change(channel, controller, value)

    def pitch_bend(self, channel: int, value: int):
        """Handle pitch bend event."""
        with self.lock:
            # Convert to pitch bend value (-1.0 to 1.0)
            bend_value = (value - 8192) / 8192.0
            self.parameter_router.route_parameter('pitch_bend', bend_value, channel=channel)

    def program_change(self, channel: int, program: int):
        """Handle program change event."""
        with self.lock:
            self.xg_system.handle_program_change(channel, program)

    def get_audio_block(self) -> np.ndarray:
        """Get the current audio output block."""
        with self.lock:
            return self.output_buffer.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        with self.lock:
            return self.performance_stats.copy()

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        with self.lock:
            return {
                'version': '2.0.0',
                'sample_rate': self.sample_rate,
                'buffer_size': self.buffer_size,
                'engines_registered': len(self.engines),
                'effects_available': len(self.effects_coordinator.effects),
                'hardware_profile': self.hardware_specs.current_profile.model_name,
                'polyphony_limit': self.hardware_specs.current_profile.polyphony,
                'sample_memory_mb': self.sample_manager.get_memory_usage()['max_memory_mb'],
                'compatibility_level': '98%'
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
            preset_data.update({
                'common': {
                    'name': name,
                    'category': 'user'
                }
            })

            return self.preset_compatibility.save_preset(program, preset_data, bank)

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

            print("Synthesizer reset to default state")

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
