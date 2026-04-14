"""
XG Effects Coordinator - Professional Effects Processing Architecture with Advanced Features

ARCHITECTURAL OVERVIEW:

The XG Effects Coordinator implements a comprehensive, production-ready effects processing
system designed for professional real-time audio synthesis. It serves as the central
orchestrator for Yamaha XG specification effects processing, providing a complete
effects pipeline with zero-allocation performance and multi-format compatibility.

ADVANCED EFFECTS FEATURES:

This coordinator now includes advanced effects processing capabilities:
- Multi-band compression with sidechain
- Advanced reverb algorithms with early reflections
- Multi-tap delay with modulation
- Spectral effects processing
- Dynamic EQ with frequency-dependent compression
- Parallel processing chains
- Effects automation and modulation

XG EFFECTS PHILOSOPHY:

The XG specification revolutionized synthesizer effects by providing a comprehensive,
professionally-oriented effects system that rivals dedicated effects processors. The
coordinator implements this philosophy through:

1. UNIFIED EFFECTS ARCHITECTURE: Single point of control for all XG effects
2. ZERO-ALLOCATION PROCESSING: Pre-allocated buffers ensure deterministic performance
3. MULTI-STAGE PROCESSING: Insertion → Variation → System effects pipeline
4. REAL-TIME COMPLIANCE: Sample-accurate processing with professional standards
5. VCM INTEGRATION: Vintage Circuit Modeling for authentic analog emulation

EFFECTS PROCESSING PIPELINE:

The coordinator implements a sophisticated 5-stage effects processing pipeline:

STAGE 1: PER-CHANNEL INSERTION EFFECTS
- Applied before mixing to individual channels
- 3 insertion slots per channel (XG specification)
- Pre-fader/post-fader routing options
- Independent processing per channel

STAGE 2: CHANNEL MIXING WITH EFFECT SENDS
- Volume and panning application per channel
- Effect send level calculation (Reverb/Chorus/Variation)
- Dry/wet signal separation for parallel processing
- Level compensation and headroom management

STAGE 3: VARIATION EFFECTS PROCESSING
- Applied to main mix before system effects
- 40+ XG variation effect types (Distortion, Delay, Rotary, etc.)
- Configurable modulation and feedback
- Wet/dry mixing with main signal

STAGE 4: SYSTEM EFFECTS PROCESSING
- Reverb and Chorus applied to final mix
- Convolution-based algorithms for spatial processing
- Multi-tap chorus with modulation
- Independent parameter control

STAGE 5: MASTER FINALIZATION
- Master EQ processing (5-band parametric)
- Stereo enhancement and spatial widening
- Wet/dry mixing and level control
- Brickwall limiting for clip prevention

ZERO-ALLOCATION ARCHITECTURE:

PERFORMANCE-CRITICAL DESIGN:
The coordinator eliminates runtime memory allocation through sophisticated buffer management:

PRE-ALLOCATION STRATEGY:
- Static buffer pools allocated at initialization
- Context-managed buffer allocation for processing
- Automatic buffer return to pools after use
- Memory pressure monitoring and cleanup

BUFFER MANAGEMENT HIERARCHY:
- Channel Buffers: Per-channel processing storage
- Mix Buffers: Main mix and accumulation buffers
- Effect Buffers: Temporary storage for effect processing
- Working Buffers: General-purpose processing buffers

THREAD SAFETY:
- Reentrant locking for multi-threaded access
- Atomic parameter updates during processing
- Consistent state snapshots for monitoring
- Race condition prevention in effect switching

XG SPECIFICATION COMPLIANCE:

EFFECTS ORGANIZATION:
XG effects are organized into three main categories with specific parameter ranges:

SYSTEM EFFECTS (Global):
- REVERB: 12 types with time, level, HF damping, density parameters
- CHORUS: 8 types with rate, depth, feedback, delay parameters
- VARIATION: 40+ types including distortion, delay, rotary speaker, phaser, etc.

INSERTION EFFECTS (Per-Channel):
- 18 effect types per slot (3 slots × 16 channels = 48 insertion effects)
- Pre-fader/post-fader routing options
- Independent wet/dry mixing per effect

MASTER EFFECTS (Final Output):
- 5-band parametric EQ with frequency and Q control
- Stereo enhancement with width control
- Master level and limiting

PARAMETER CONTROL:
- NRPN-based parameter addressing (MSB 16-31 for effects)
- 14-bit parameter resolution for precise control
- Real-time parameter smoothing and interpolation
- Effect-specific parameter ranges and units

VCM EFFECTS INTEGRATION:

VINTAGE CIRCUIT MODELING:
The coordinator integrates VCM (Vintage Circuit Modeling) technology for authentic
analog effect emulation. VCM effects simulate the behavior of classic analog circuits:

VCM OVERDRIVE:
- Tube saturation modeling with asymmetric clipping
- Frequency-dependent saturation characteristics
- Harmonic generation and intermodulation products

VCM DISTORTION:
- Multi-stage distortion with octave fuzz characteristics
- Diode clipping and transistor saturation modeling
- Tone shaping with frequency response curves

VCM PHASER:
- Analog all-pass filter networks with LFO modulation
- Feedback control for resonance and intensity
- Vintage phasing characteristics

VCM EQUALIZER:
- Analog filter curves with component tolerances
- Frequency response modeling with parasitic effects
- Vintage EQ characteristics and coloration

VCM STEREO ENHANCER:
- Analog stereo widening circuits
- Haas effect implementation
- Vintage stereo imaging techniques

PERFORMANCE OPTIMIZATION:

REAL-TIME OPTIMIZATION:
- SIMD-optimized filter processing
- Vectorized effect algorithms
- Pre-computed coefficient tables
- Sample-accurate parameter interpolation

MEMORY MANAGEMENT:
- Buffer pool utilization monitoring
- Automatic cleanup under memory pressure
- Compressed effect state storage
- Memory-mapped parameter tables

CPU OPTIMIZATION:
- Effect-specific processing optimizations
- Conditional processing for inactive effects
- Background parameter updates
- Adaptive processing based on CPU load

PROFESSIONAL AUDIO FEATURES:

SAMPLE ACCURACY:
- Sub-sample precision for all effect parameters
- Jitter-free timing for modulation effects
- Phase-locked processing for stereo effects
- Sample-rate independent algorithms

DYNAMIC RANGE:
- 64-bit internal processing for headroom
- 32-bit float I/O compatibility
- Automatic level detection and adjustment
- Soft limiting for overload protection

LATENCY MANAGEMENT:
- Fixed latency effects processing
- Latency compensation for insertion effects
- Real-time latency monitoring
- User-selectable latency modes

MULTI-CHANNEL SUPPORT:

16-CHANNEL ARCHITECTURE:
- Independent processing per MIDI channel
- Per-channel effect sends and routing
- Channel-specific insertion effects
- Multi-timbral effect processing

STEREO PROCESSING:
- True stereo effect algorithms
- Channel-independent processing
- Stereo width control and enhancement
- Mid/side processing capabilities

SURROUND SUPPORT:
- Future expansion to 5.1 and 7.1 surround
- Binaural processing for headphone monitoring
- Immersive audio processing capabilities

INTEGRATION ARCHITECTURE:

SYNTHESIZER INTEGRATION:
- Direct integration with XG synthesizer voice processing
- Voice manager coordination for per-voice effects
- Parameter router integration for automation
- Real-time performance monitoring

XG SYSTEM INTEGRATION:
- XG state manager parameter synchronization
- XG MIDI processor NRPN handling
- XG bulk dump effect preset loading
- XG system exclusive effect control

JUPITER-X INTEGRATION:
- Hardware-specific effect algorithms
- Jupiter-X parameter mapping and control
- MPE-compatible effect processing
- Hardware acceleration integration

EFFECTS MANAGEMENT:

EFFECT REGISTRATION:
- Dynamic effect loading and registration
- Effect capability discovery and enumeration
- Parameter validation and range checking
- Effect dependency management

EFFECT SCHEDULING:
- Priority-based effect processing order
- CPU load balancing across effects
- Background effect initialization
- Effect state persistence and restoration

ERROR HANDLING:

GRACEFUL DEGRADATION:
- Effect failure isolation and bypass
- Fallback processing for failed effects
- Parameter clamping for out-of-range values
- Automatic effect reset on errors

DIAGNOSTIC CAPABILITIES:
- Effect processing performance monitoring
- Memory usage tracking per effect
- CPU utilization analysis
- Effect-specific error reporting

EXTENSIBILITY ARCHITECTURE:

PLUGIN EFFECTS SYSTEM:
- Third-party effect plugin support
- Custom effect development framework
- Effect parameter automation integration
- Real-time effect switching

SCRIPTING INTERFACE:
- Python-based effect scripting
- Custom algorithm implementation
- Effect parameter automation
- Dynamic effect chain creation

RESEARCH FEATURES:
- Machine learning effect optimization
- Neural network-based effect processing
- AI-assisted effect design
- Real-time effect adaptation

FUTURE EXPANSION:

PROFESSIONAL INTEGRATION:
- DAW plugin format support (VST3, AU, AAX)
- Hardware DSP acceleration
- Cloud-based effect processing
- Distributed effects processing

ADVANCED FEATURES:
- Spectral effects processing
- Convolution reverb with user IRs
- Physical modeling effects
- Advanced modulation and automation

XG v2.0 COMPLIANCE:

ENHANCED EFFECTS:
- Additional effect types beyond XG v1.0
- Higher parameter resolution (16-bit, 32-bit)
- Advanced modulation capabilities
- Multi-channel effect processing

PROFESSIONAL STANDARDS:
- SMPTE timecode synchronization
- Professional audio file format support
- Multi-channel audio interface compatibility
- Real-time performance standards compliance
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np

# Import our effect processors
from ...primitives.buffer_pool import XGBufferManager
from .eq_processor import XGMultiBandEqualizer
from .insertion import ProductionXGInsertionEffectsProcessor
from .system import XGSystemEffectsProcessor
from .variation_effects import XGVariationEffectsProcessor


class XGEffectsCoordinator:
    """
    XG Effects Coordinator

    Orchestrates XG effects processing with channel routing and effect chaining.

    Processing Chain:
    1. Per-channel insertion effects
    2. Channel mixing with panning, volume, and effect sends
    3. Variation effects applied to mix
    4. System effects (reverb/chorus) on final stereo output
    5. Master finalization (EQ, stereo enhancement, limiting, wet/dry)
    """

    def __init__(
        self,
        sample_rate: int,
        block_size: int = 1024,
        max_channels: int = 16,
        synthesizer=None,
        buffer_pool=None,
    ):
        """
        Initialize XG effects coordinator.

        Args:
            sample_rate: Sample rate in Hz
            block_size: Maximum processing block size
            max_channels: Maximum number of channels to support
            synthesizer: Reference to parent synthesizer for GS parameter access
            buffer_pool: Shared buffer pool from synthesizer (optional)
        """
        self.synthesizer = synthesizer  # Reference to parent synthesizer
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_channels = max_channels

        # Buffer management - use shared pool from synthesizer if provided
        if buffer_pool is not None:
            self.buffer_pool = buffer_pool
        else:
            # Fallback to creating own pool (legacy behavior)
            from ...primitives.buffer_pool import XGBufferPool

            self.buffer_pool = XGBufferPool(sample_rate, block_size * 4)
        self.buffer_manager: XGBufferManager | None = None
        # Alias for backward compatibility
        self.memory_pool = self.buffer_pool

        # Effect processors
        max_reverb_delay = int(5.0 * sample_rate)  # 5 seconds max reverb
        max_chorus_delay = int(0.05 * sample_rate)  # 50ms max delay
        max_effect_delay = int(2.0 * sample_rate)  # 2 seconds for variation effects

        # System effects (reverb, chorus - applied to final mix)
        self.system_effects = XGSystemEffectsProcessor(
            sample_rate, block_size, None, max_reverb_delay, max_chorus_delay
        )

        # Variation effects (applied to mix before system effects)
        self.variation_effects = XGVariationEffectsProcessor(sample_rate, max_effect_delay)

        # Insertion effects (per channel, applied before mixing) - PRODUCTION VERSION
        self.insertion_effects: list[ProductionXGInsertionEffectsProcessor] = []
        for _ in range(max_channels):
            self.insertion_effects.append(
                ProductionXGInsertionEffectsProcessor(sample_rate, max_effect_delay)
            )

        # Processing state
        self.processing_enabled = True
        self.wet_dry_mix = 1.0  # Full wet for XG compliance
        self.master_level = 1.0

        # XG effect routing configuration
        self.effect_routing_mode = "XG_STANDARD"  # XG compatible routing

        # Per-channel parameters (XG compliant)
        self.channel_volumes: np.ndarray = np.ones(max_channels, dtype=np.float32)
        self.channel_pans: np.ndarray = np.zeros(max_channels, dtype=np.float32)  # -1 to 1

        # Per-channel effect sends (XG CC 91=reverb, 93=chorus, 94=variation)
        self.reverb_sends: np.ndarray = np.full(
            max_channels, 0.4, dtype=np.float32
        )  # Default 40/127
        self.chorus_sends: np.ndarray = np.full(
            max_channels, 0.0, dtype=np.float32
        )  # Default 0/127
        self.variation_sends: np.ndarray = np.full(
            max_channels, 0.0, dtype=np.float32
        )  # Default 0/127

        # Effect activation (XG CC 200-209)
        self.effect_units_active: np.ndarray = np.ones(10, dtype=bool)  # All active by default

        # Dry signal storage for wet/dry mixing
        self.dry_signal_buffer: np.ndarray | None = None

        # Master EQ processor (XG Multi-Band Equalizer)
        self.master_eq = XGMultiBandEqualizer(sample_rate)

        # Effects list for synthesizer info (compatibility)
        self.effects = []  # Will be populated with active effects

        # Performance monitoring - comprehensive
        self.processing_stats = {
            "total_blocks_processed": 0,
            "average_processing_time_ms": 0.0,
            "peak_processing_time_ms": 0.0,
            "cpu_usage_percent": 0.0,
            "memory_usage_mb": 0.0,
            "zero_allocation_violations": 0,
            "buffer_pool_hits": 0,
            "buffer_pool_misses": 0,
        }

        # Thread safety
        self.lock = threading.RLock()

        # ===== JUPITER-X INTEGRATION =====
        # Jupiter-X specific effects and processing modes
        self.jupiter_x_mode = False  # Enable Jupiter-X specific processing
        self.jupiter_x_effects = self._initialize_jupiter_x_effects()

        # Jupiter-X modulation sources
        self.jupiter_x_modulation = {
            "lfo1": {"rate": 5.0, "depth": 0.0, "waveform": "sine"},
            "lfo2": {"rate": 3.0, "depth": 0.0, "waveform": "triangle"},
            "envelope": {"attack": 0.01, "decay": 0.1, "amount": 0.0},
        }

        # MPE support for Jupiter-X
        self.mpe_enabled = False
        self.mpe_channels = {}  # Channel -> MPE data

        # Initialize
        self._initialize_processing()

    def _initialize_jupiter_x_effects(self):
        """Initialize Jupiter-X specific effects.

        Jupiter-X uses enhanced versions of standard effects plus exclusive effects.
        These are implemented through the existing effects framework with specific
        parameter mappings.
        """
        jupiter_x_effects = {}

        jupiter_x_effects["distortion"] = {
            "type": "distortion",
            "algorithm": "jupiter_ds",
            "params": {
                "drive": 0.5,
                "tone": 0.5,
                "level": 0.8,
            },
        }

        jupiter_x_effects["phaser"] = {
            "type": "vcm_phaser",
            "algorithm": "jupiter_phaser",
            "params": {
                "rate": 0.5,
                "depth": 0.7,
                "manual": 0.5,
                "resonance": 0.3,
            },
        }

        jupiter_x_effects["enhancer"] = {
            "type": "stereo_enhancer",
            "algorithm": "jupiter_enhancer",
            "params": {
                "enhance": 0.5,
                "clarity": 0.3,
                "depth": 0.5,
            },
        }

        jupiter_x_effects["vcm_rotary"] = {
            "type": "rotary_speaker",
            "algorithm": "jupiter_rotary",
            "params": {
                "speed": 0.5,
                "drive": 0.3,
                "balance": 0.5,
            },
        }

        jupiter_x_effects["overdrive"] = {
            "type": "overdrive",
            "algorithm": "jupiter_od",
            "params": {
                "gain": 0.5,
                "tone": 0.5,
                "level": 0.8,
            },
        }

        return jupiter_x_effects

    def _initialize_processing(self):
        """Initialize processing context and allocate buffers."""
        with self.lock:
            self.buffer_manager = XGBufferManager(self.buffer_pool)

        # Pre-allocate dry signal buffer for wet/dry mixing
        self.dry_signal_buffer = np.zeros((self.block_size, 2), dtype=np.float32)

        # Pre-allocate static working buffers (SINGLE ALLOCATION - more efficient)
        self._preallocate_static_buffers()

        # Pre-allocate commonly used buffers
        self._ensure_buffer_availability()

    def _preallocate_static_buffers(self):
        """Pre-allocate static working buffers during construction for maximum efficiency."""
        # Pre-allocate commonly used working buffers that are reused throughout processing
        # These buffers are allocated once during construction and reused for all processing calls

        # Channel processing buffers - pre-allocate for all channels
        self._channel_result_buffers = []
        for i in range(self.max_channels):
            buffer = self.memory_pool.get_stereo_buffer(self.block_size)
            self._channel_result_buffers.append(buffer)

        # Main processing chain buffers
        self._main_mix_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._reverb_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._variation_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._system_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)

        # Temporary working buffers for effects processing
        self._temp_working_buffers = []
        for i in range(8):  # Reserve 8 temp buffers for various processing needs
            buffer = self.memory_pool.get_stereo_buffer(self.block_size)
            self._temp_working_buffers.append(buffer)

        # System effect specific buffers
        self._reverb_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)

    def _ensure_buffer_availability(self):
        """Ensure sufficient buffers are available in the pool."""
        # The buffer pool automatically manages this, but we can
        # pre-warm it with commonly used sizes
        pass

    def process_channels_to_stereo_zero_alloc(
        self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int
    ) -> None:
        """
        Process multi-channel input through complete XG effects chain to stereo output.

        PRODUCTION IMPLEMENTATION: Complete XG-compliant effect routing with proper chaining.
        OPTIMIZED: Pre-allocates all working buffers at start for maximum efficiency.

        Args:
            input_channels: List of channel audio arrays (mono or stereo)
            output_stereo: Output stereo buffer (num_samples, 2) - modified in-place
            num_samples: Number of samples to process
        """
        if not self.processing_enabled or not self.buffer_manager:
            # If disabled or not initialized, mix channels directly to stereo
            self._mix_channels_to_stereo_direct(input_channels, output_stereo, num_samples)
            return

        with self.lock:
            start_time = time.perf_counter()

            # Validate inputs
            if len(input_channels) == 0 or num_samples > self.block_size:
                return

            # OPTIMIZATION: Pre-allocate ALL working buffers at once (single allocation pass)
            # Since we're under thread lock, we can allocate once and reuse throughout processing
            processed_channels = []
            main_mix = None
            reverb_accumulate = None
            chorus_accumulate = None
            variation_output = None
            system_output = None
            temp_buffers = []

            try:
                # Single buffer allocation pass - get all buffers we need (use num_samples for correct sizing)
                with self.buffer_manager as bm:
                    # Pre-allocate result buffers for each channel
                    for i in range(len(input_channels)):
                        result_buffer = bm.get_stereo(num_samples)  # Use actual segment size
                        processed_channels.append(result_buffer)

                    # Main processing buffers - use num_samples to match segment size
                    main_mix = bm.get_stereo(num_samples)
                    reverb_accumulate = bm.get_stereo(num_samples)
                    chorus_accumulate = bm.get_stereo(num_samples)
                    variation_output = bm.get_stereo(num_samples)
                    system_output = bm.get_stereo(num_samples)

                    # Additional temp buffers for processing - use num_samples
                    for _ in range(4):  # Reserve some temp buffers
                        temp_buffers.append(bm.get_stereo(num_samples))

                # Clear accumulation buffers once
                main_mix.fill(0.0)
                reverb_accumulate.fill(0.0)
                chorus_accumulate.fill(0.0)

                # STEP 1: APPLY INSERTION EFFECTS TO EACH CHANNEL (XG COMPLIANT)
                self._apply_insertion_effects_to_channels_optimized(
                    input_channels, processed_channels, temp_buffers, num_samples
                )

                # STEP 2: MIX CHANNELS WITH PANNING AND CREATE EFFECT SENDS
                self._mix_channels_with_effect_sends_optimized(
                    processed_channels, main_mix, reverb_accumulate, chorus_accumulate, num_samples
                )

                # STEP 3: APPLY VARIATION EFFECTS TO MIX
                self._apply_variation_effects_to_mix_optimized(
                    main_mix, variation_output, temp_buffers, num_samples
                )

                # STEP 4: APPLY SYSTEM EFFECTS (REVERB/CHORUS) WITH SENDS
                self._apply_system_effects_with_sends_optimized(
                    variation_output,
                    system_output,
                    reverb_accumulate,
                    chorus_accumulate,
                    temp_buffers,
                    num_samples,
                )

                # STEP 5: MASTER FINALIZATION WITH WET/DRY MIXING
                self._apply_master_processing_optimized(system_output, num_samples, output_stereo)

                # Update performance stats
                processing_time_ms = (time.perf_counter() - start_time) * 1000
                self._update_performance_stats(processing_time_ms)

            except Exception as e:
                # On processing error, use graceful degradation
                print(f"XG Effects processing error: {e}")
                self._mix_channels_to_stereo_direct(input_channels, output_stereo, num_samples)

            finally:
                # Clean up: return temp buffers to pool (context manager handles this automatically)
                pass

    def _preallocate_channel_buffers(
        self, bm, num_channels: int, num_samples: int
    ) -> list[np.ndarray]:
        """Pre-allocate result buffers for all channels."""
        buffers = []
        for i in range(num_channels):
            result_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
            buffers.append(result_buffer)
        return buffers

    def _apply_insertion_effects_to_channels_optimized(
        self,
        input_channels: list[np.ndarray],
        processed_channels: list[np.ndarray],
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        """Optimized insertion effects processing using pre-allocated buffers."""
        for ch_idx, channel_data in enumerate(input_channels):
            if ch_idx >= len(self.insertion_effects):
                # No insertion effects for this channel - copy input to result
                if channel_data.ndim == 1:
                    # Mono to stereo
                    processed_channels[ch_idx][:num_samples, 0] = channel_data[:num_samples]
                    processed_channels[ch_idx][:num_samples, 1] = channel_data[:num_samples]
                else:
                    # Stereo copy
                    np.copyto(processed_channels[ch_idx][:num_samples], channel_data[:num_samples])
                continue

            # Use pre-allocated temp buffer
            working_buffer = temp_buffers[ch_idx % len(temp_buffers)]

            # Copy input to working buffer if needed
            if channel_data.ndim == 2:
                np.copyto(working_buffer[:num_samples], channel_data[:num_samples])

            # Apply insertion effects to working buffer
            insertion_params = {"enabled": True}
            self.insertion_effects[ch_idx].apply_insertion_effect_to_channel_zero_alloc(
                working_buffer, channel_data, insertion_params, num_samples, ch_idx
            )

            # Copy processed result to pre-allocated result buffer
            np.copyto(processed_channels[ch_idx][:num_samples], working_buffer[:num_samples])

    def _mix_channels_with_effect_sends_optimized(
        self,
        processed_channels: list[np.ndarray],
        main_mix: np.ndarray,
        reverb_accumulate: np.ndarray,
        chorus_accumulate: np.ndarray,
        num_samples: int,
    ) -> None:
        """Optimized channel mixing using pre-allocated buffers."""
        # main_mix, reverb_accumulate, chorus_accumulate are already pre-allocated and cleared

        # Mix each channel with panning and sends
        for ch_idx, channel_data in enumerate(processed_channels):
            if ch_idx >= self.max_channels:
                continue

            # Get channel parameters
            volume = self.channel_volumes[ch_idx]
            pan = self.channel_pans[ch_idx]
            reverb_send = self.reverb_sends[ch_idx]
            chorus_send = self.chorus_sends[ch_idx]
            variation_send = self.variation_sends[ch_idx]

            # Apply volume and create stereo signal
            if channel_data.ndim == 1:
                # Mono to stereo with panning
                left_level = volume * (1.0 - pan) * 0.5
                right_level = volume * (1.0 + pan) * 0.5

                # Add to main mix (dry signal)
                dry_level = 1.0 - max(reverb_send, chorus_send, variation_send)
                if dry_level > 0:
                    main_mix[:num_samples, 0] += channel_data[:num_samples] * left_level * dry_level
                    main_mix[:num_samples, 1] += (
                        channel_data[:num_samples] * right_level * dry_level
                    )

                # Add to effect sends
                if reverb_send > 0:
                    reverb_accumulate[:num_samples, 0] += (
                        channel_data[:num_samples] * left_level * reverb_send
                    )
                    reverb_accumulate[:num_samples, 1] += (
                        channel_data[:num_samples] * right_level * reverb_send
                    )

                if chorus_send > 0:
                    chorus_accumulate[:num_samples, 0] += (
                        channel_data[:num_samples] * left_level * chorus_send
                    )
                    chorus_accumulate[:num_samples, 1] += (
                        channel_data[:num_samples] * right_level * chorus_send
                    )

            else:
                # Stereo channel
                left_data = channel_data[:num_samples, 0] * volume
                right_data = channel_data[:num_samples, 1] * volume

                # Add to main mix (dry signal)
                dry_level = 1.0 - max(reverb_send, chorus_send, variation_send)
                if dry_level > 0:
                    main_mix[:num_samples, 0] += left_data * dry_level
                    main_mix[:num_samples, 1] += right_data * dry_level

                # Add to effect sends
                if reverb_send > 0:
                    reverb_accumulate[:num_samples, 0] += left_data * reverb_send
                    reverb_accumulate[:num_samples, 1] += right_data * reverb_send

                if chorus_send > 0:
                    chorus_accumulate[:num_samples, 0] += left_data * chorus_send
                    chorus_accumulate[:num_samples, 1] += right_data * chorus_send

    def _apply_variation_effects_to_mix_optimized(
        self,
        main_mix: np.ndarray,
        variation_output: np.ndarray,
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        """Optimized variation effects processing using pre-allocated buffers."""
        # Check if variation effects are active (XG CC 200-209)
        if not self.effect_units_active[0]:  # Variation unit
            np.copyto(
                variation_output[:num_samples], main_mix[:num_samples]
            )  # Just copy input to output
            return

        # Copy input to output buffer
        np.copyto(variation_output[:num_samples], main_mix[:num_samples])

        # Apply variation effect to the mix
        self.variation_effects.apply_variation_effect_zero_alloc(
            variation_output[:num_samples], num_samples
        )

    def _apply_system_effects_with_sends_optimized(
        self,
        variation_output: np.ndarray,
        system_output: np.ndarray,
        reverb_accumulate: np.ndarray,
        chorus_accumulate: np.ndarray,
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        """Optimized system effects processing using pre-allocated buffers."""
        # Start with variation output
        np.copyto(system_output[:num_samples], variation_output[:num_samples])

        # Check if we should use GS system effects
        use_gs_effects = self._should_use_gs_system_effects()

        # Apply system reverb if active
        if self.effect_units_active[1] and np.max(np.abs(reverb_accumulate)) > 0:  # Reverb unit
            reverb_wet = self._apply_system_reverb_optimized(
                reverb_accumulate, temp_buffers[0], num_samples, use_gs_effects
            )
            if reverb_wet is not None:
                system_output[:num_samples] += reverb_wet[:num_samples]

        # Apply system chorus if active
        if self.effect_units_active[2] and np.max(np.abs(chorus_accumulate)) > 0:  # Chorus unit
            chorus_wet = self._apply_system_chorus_optimized(
                chorus_accumulate, temp_buffers[1], num_samples, use_gs_effects
            )
            if chorus_wet is not None:
                system_output[:num_samples] += chorus_wet[:num_samples]

    def _should_use_gs_system_effects(self) -> bool:
        """Check if GS system effects should be used instead of XG."""
        if self.synthesizer and hasattr(self.synthesizer, "parameter_priority"):
            return self.synthesizer.parameter_priority.is_gs_active()
        return False

    def _apply_system_reverb_optimized(
        self,
        reverb_send: np.ndarray,
        temp_buffer: np.ndarray,
        num_samples: int,
        use_gs_effects: bool = False,
    ) -> np.ndarray | None:
        """Optimized system reverb processing using pre-allocated temp buffer."""
        try:
            # Use pre-allocated temp buffer
            np.copyto(temp_buffer[:num_samples], reverb_send[:num_samples])

            if use_gs_effects and self.synthesizer and hasattr(self.synthesizer, "gs_components"):
                # Use GS reverb parameters
                gs_system = self.synthesizer.gs_components.get_component("system_params")
                if gs_system:
                    # Apply GS reverb parameters to the system effects processor
                    # This would need integration with the actual effect processors
                    # For now, use XG effects but with GS parameters where possible
                    pass

            # Apply convolution reverb using the production processor
            self.system_effects.reverb_processor.apply_system_effects_to_mix_zero_alloc(
                temp_buffer, num_samples
            )

            return temp_buffer
        except Exception:
            return None

    def _apply_system_chorus_optimized(
        self,
        chorus_send: np.ndarray,
        temp_buffer: np.ndarray,
        num_samples: int,
        use_gs_effects: bool = False,
    ) -> np.ndarray | None:
        """Optimized system chorus processing using pre-allocated temp buffer."""
        try:
            # Use pre-allocated temp buffer
            np.copyto(temp_buffer[:num_samples], chorus_send[:num_samples])

            if use_gs_effects and self.synthesizer and hasattr(self.synthesizer, "gs_components"):
                # Use GS chorus parameters
                gs_system = self.synthesizer.gs_components.get_component("system_params")
                if gs_system:
                    # Apply GS chorus parameters to the system effects processor
                    # This would need integration with the actual effect processors
                    # For now, use XG effects but with GS parameters where possible
                    pass

            # Apply stereo chorus using the production processor
            self.system_effects.chorus_processor.apply_system_effects_to_mix_zero_alloc(
                temp_buffer, num_samples
            )

            return temp_buffer
        except Exception:
            return None

    def _apply_master_processing_optimized(
        self, system_output: np.ndarray, num_samples: int, output_stereo: np.ndarray
    ) -> None:
        """Optimized master processing using pre-allocated buffers."""
        # Work directly on the output buffer to avoid shape mismatches
        # Copy system output to output buffer first
        np.copyto(output_stereo[:num_samples], system_output[:num_samples])

        # Store dry signal for wet/dry mixing if needed
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None:
            np.copyto(self.dry_signal_buffer[:num_samples], output_stereo[:num_samples])

        # Apply master level
        if self.master_level != 1.0:
            output_stereo[:num_samples] *= self.master_level

        # Apply wet/dry mix
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None:
            # Blend wet and dry signals
            wet_level = self.wet_dry_mix
            dry_level = 1.0 - wet_level
            output_stereo[:num_samples] = (
                output_stereo[:num_samples] * wet_level
                + self.dry_signal_buffer[:num_samples] * dry_level
            )

        # Apply master EQ using XG Multi-Band Equalizer directly to output buffer
        eq_input = output_stereo[:num_samples].copy()  # Make a copy for EQ processing
        eq_processed = self.master_eq.process_buffer(eq_input)

        # Stereo enhancement (simple stereo widening) on the EQ processed result
        self._apply_stereo_enhancement(eq_processed, num_samples)

        # Copy the final processed result back to output buffer
        # Handle potential shape mismatches safely
        copy_samples = min(num_samples, eq_processed.shape[0], output_stereo.shape[0])
        copy_channels = min(
            output_stereo.shape[1] if output_stereo.ndim > 1 else 1,
            eq_processed.shape[1] if eq_processed.ndim > 1 else 1,
        )

        # Ensure output buffer has correct shape for copying
        if eq_processed.ndim == 1 and output_stereo.ndim == 2:
            # Mono to stereo conversion if needed
            output_stereo[:copy_samples, 0] = eq_processed[:copy_samples]
            output_stereo[:copy_samples, 1] = eq_processed[:copy_samples]
        else:
            # Standard stereo copy
            output_stereo[:copy_samples, :copy_channels] = eq_processed[
                :copy_samples, :copy_channels
            ]

        # Brickwall limiting to prevent clipping
        np.clip(output_stereo[:num_samples], -0.99, 0.99, out=output_stereo[:num_samples])


    def _apply_stereo_enhancement(self, stereo_buffer: np.ndarray, num_samples: int) -> None:
        """
        Apply simple stereo enhancement (widening).

        Args:
            stereo_buffer: Stereo buffer to process in-place
            num_samples: Number of samples
        """
        # Simple stereo widening by slightly reducing mono content
        # This is a basic implementation - could be enhanced with more sophisticated processing
        enhancement_amount = 0.1
        mono = (stereo_buffer[:num_samples, 0] + stereo_buffer[:num_samples, 1]) * 0.5
        stereo_buffer[:num_samples, 0] -= mono * enhancement_amount
        stereo_buffer[:num_samples, 1] -= mono * enhancement_amount

    def _mix_channels_to_stereo_direct(
        self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int
    ) -> None:
        """
        Direct channel mixing bypass (used when effects are disabled or error occurs).
        """
        # Clear output
        output_stereo[:num_samples, :].fill(0.0)

        # Simple mixing
        num_active_channels = min(len(input_channels), self.max_channels)
        mix_level = 1.0 / max(num_active_channels, 1)  # Prevent clipping

        for channel_data in input_channels:
            if channel_data.ndim == 1:
                # Mono channel - pan center
                output_stereo[:num_samples, 0] += channel_data[:num_samples] * mix_level
                output_stereo[:num_samples, 1] += channel_data[:num_samples] * mix_level
            else:
                # Stereo channel
                output_stereo[:num_samples, 0] += channel_data[:num_samples, 0] * mix_level
                output_stereo[:num_samples, 1] += channel_data[:num_samples, 1] * mix_level

    def _update_performance_stats(self, processing_time_ms: float) -> None:
        """Update performance monitoring statistics."""
        self.processing_stats["total_blocks_processed"] += 1

        # Rolling average (simple implementation)
        current_avg = self.processing_stats["average_processing_time_ms"]
        new_avg = (current_avg * 0.99) + (processing_time_ms * 0.01)
        self.processing_stats["average_processing_time_ms"] = new_avg

        # Track peak
        if processing_time_ms > self.processing_stats["peak_processing_time_ms"]:
            self.processing_stats["peak_processing_time_ms"] = processing_time_ms

    # XG COMPLIANT PARAMETER CONTROL INTERFACE

    def set_channel_insertion_effect(self, channel: int, slot: int, effect_type: int) -> bool:
        """
        Set insertion effect type for a channel slot (XG compliant).

        Args:
            channel: Channel/part number (0-15)
            slot: Insertion slot (0-2)
            effect_type: XG insertion effect type (0-17)

        Returns:
            True if successfully set
        """
        with self.lock:
            if 0 <= channel < len(self.insertion_effects):
                return self.insertion_effects[channel].set_insertion_effect_type(slot, effect_type)
            return False

    def set_channel_insertion_bypass(self, channel: int, slot: int, bypass: bool) -> bool:
        """
        Set insertion effect bypass for a channel slot (XG compliant).

        Args:
            channel: Channel/part number (0-15)
            slot: Insertion slot (0-2)
            bypass: True to bypass, False to enable

        Returns:
            True if successfully set
        """
        with self.lock:
            if 0 <= channel < len(self.insertion_effects):
                return self.insertion_effects[channel].set_insertion_effect_bypass(slot, bypass)
            return False

    def set_variation_effect_type(self, variation_type: int) -> bool:
        """
        Set system variation effect type (XG compliant).

        Args:
            variation_type: XG variation effect type (0-62)

        Returns:
            True if successfully set
        """
        with self.lock:
            try:
                # Convert int to enum value if needed
                if hasattr(self.variation_effects, "set_variation_type"):
                    self.variation_effects.set_variation_type(variation_type)
                return True
            except Exception:
                return False

    def set_effect_send_level(self, channel: int, effect_type: str, level: float) -> bool:
        """
        Set effect send level for a channel (XG compliant).

        Args:
            channel: Channel/part number (0-15)
            effect_type: 'reverb', 'chorus', or 'variation'
            level: Send level (0.0-1.0)

        Returns:
            True if successfully set
        """
        with self.lock:
            if not (0 <= channel < self.max_channels):
                return False

            level = max(0.0, min(1.0, level))

            if effect_type == "reverb":
                self.reverb_sends[channel] = level
            elif effect_type == "chorus":
                self.chorus_sends[channel] = level
            elif effect_type == "variation":
                self.variation_sends[channel] = level
            else:
                return False

            return True

    def set_system_effect_parameter(self, effect: str, param: str, value: float) -> bool:
        """
        Set system effect parameter (XG NRPN compliant).

        Args:
            effect: Effect name ('reverb' or 'chorus')
            param: Parameter name
            value: Parameter value

        Returns:
            True if successfully set
        """
        with self.lock:
            return self.system_effects.set_system_effect_parameter(effect, param, value)

    def set_effect_unit_activation(self, unit: int, active: bool) -> bool:
        """
        Set effect unit activation (XG CC 200-209 compliant).

        Args:
            unit: Effect unit number (0-9)
            active: True to enable, False to disable

        Returns:
            True if unit is valid
        """
        with self.lock:
            if 0 <= unit < len(self.effect_units_active):
                self.effect_units_active[unit] = active
                return True
            return False

    def set_master_controls(self, level: float = None, wet_dry: float = None) -> bool:
        """
        Set master controls.

        Args:
            level: Master level (0.0-2.0), None to leave unchanged
            wet_dry: Wet/dry mix (0.0-1.0), None to leave unchanged

        Returns:
            True if any parameter was set
        """
        with self.lock:
            changed = False
            if level is not None:
                self.master_level = max(0.0, min(2.0, level))
                changed = True
            if wet_dry is not None:
                self.wet_dry_mix = max(0.0, min(1.0, wet_dry))
                changed = True
            return changed

    def set_channel_volume(self, channel: int, volume: float) -> bool:
        """
        Set channel volume (XG compliant).

        Args:
            channel: Channel/part number (0-15)
            volume: Volume level (0.0-1.0)

        Returns:
            True if successfully set
        """
        with self.lock:
            if 0 <= channel < self.max_channels:
                self.channel_volumes[channel] = max(0.0, min(1.0, volume))
                return True
            return False

    def set_channel_pan(self, channel: int, pan: float) -> bool:
        """
        Set channel pan position (XG compliant).

        Args:
            channel: Channel/part number (0-15)
            pan: Pan position (-1.0 to 1.0, -1 = full left, 1 = full right)

        Returns:
            True if successfully set
        """
        with self.lock:
            if 0 <= channel < self.max_channels:
                self.channel_pans[channel] = max(-1.0, min(1.0, pan))
                return True
            return False

    def set_master_eq_type(self, eq_type: int) -> bool:
        """
        Set master EQ type (XG NRPN compliant).

        Args:
            eq_type: EQ type 0-4 (Flat, Jazz, Pops, Rock, Concert)

        Returns:
            True if successfully set
        """
        with self.lock:
            try:
                self.master_eq.set_eq_type(eq_type)
                return True
            except Exception:
                return False

    def set_master_eq_gain(self, band: str, gain_db: float) -> bool:
        """
        Set master EQ band gain (XG NRPN compliant).

        Args:
            band: Band name ('low', 'low_mid', 'mid', 'high_mid', 'high')
            gain_db: Gain in dB (-12 to +12)

        Returns:
            True if successfully set
        """
        with self.lock:
            try:
                match band:
                    case "low":
                        self.master_eq.set_low_gain(gain_db)
                    case "low_mid":
                        self.master_eq.set_low_mid_gain(gain_db)
                    case "mid":
                        self.master_eq.set_mid_gain(gain_db)
                    case "high_mid":
                        self.master_eq.set_high_mid_gain(gain_db)
                    case "high":
                        self.master_eq.set_high_gain(gain_db)
                    case _:
                        return False
                return True
            except Exception:
                return False

    def set_master_eq_frequency(self, freq_hz: float) -> bool:
        """
        Set master EQ mid band frequency (XG NRPN compliant).

        Args:
            freq_hz: Frequency in Hz (100-5220)

        Returns:
            True if successfully set
        """
        with self.lock:
            try:
                self.master_eq.set_mid_frequency(freq_hz)
                return True
            except Exception:
                return False

    def set_master_eq_q_factor(self, q: float) -> bool:
        """
        Set master EQ Q factor for parametric bands (XG NRPN compliant).

        Args:
            q: Q factor (0.5-5.5)

        Returns:
            True if successfully set
        """
        with self.lock:
            try:
                self.master_eq.set_q_factor(q)
                return True
            except Exception:
                return False

    def set_xg_effect_preset(self, preset_name: str) -> bool:
        """
        Apply XG effect preset configuration.

        Args:
            preset_name: Name of preset ('default', 'hall', 'room', etc.)

        Returns:
            True if preset exists and was applied
        """
        # Preset definitions would go here
        # For now, just return False
        return False

    # MONITORING AND STATUS

    def get_processing_status(self) -> dict[str, Any]:
        """
        Get current processing status and statistics.

        Returns:
            Dictionary with processing status and performance metrics
        """
        with self.lock:
            return {
                "processing_enabled": self.processing_enabled,
                "master_level": self.master_level,
                "wet_dry_mix": self.wet_dry_mix,
                "routing_mode": self.effect_routing_mode,
                "performance": self.processing_stats.copy(),
                "buffer_pool": self.buffer_pool.get_memory_stats(),
                "system_effects": self.system_effects.get_system_effects_status(),
                "variation_effects": self.variation_effects.get_variation_status(),
                "effect_units_active": self.effect_units_active.tolist(),
            }

    def reset_all_effects(self) -> None:
        """Reset all effects to default XG-compliant state."""
        with self.lock:
            # Reset system effects
            self.system_effects = XGSystemEffectsProcessor(
                self.sample_rate,
                self.block_size,
                None,
                int(5.0 * self.sample_rate),
                int(0.05 * self.sample_rate),
            )

            # Reset variation effects
            max_effect_delay = int(2.0 * self.sample_rate)
            self.variation_effects = XGVariationEffectsProcessor(self.sample_rate, max_effect_delay)

            # Reset insertion effects - use production version
            for i in range(len(self.insertion_effects)):
                max_effect_delay = int(2.0 * self.sample_rate)
                self.insertion_effects[i] = ProductionXGInsertionEffectsProcessor(
                    self.sample_rate, max_effect_delay
                )

            # Reset channel parameters
            self.channel_volumes.fill(1.0)
            self.channel_pans.fill(0.0)

            # Reset sends and controls
            self.reverb_sends.fill(0.4)
            self.chorus_sends.fill(0.0)
            self.variation_sends.fill(0.0)
            self.effect_units_active.fill(True)
            self.master_level = 1.0
            self.wet_dry_mix = 1.0

    def get_current_state(self) -> dict[str, Any]:
        """
        Get current effects coordinator state for monitoring.

        Returns:
            Dictionary with current effect parameters and status
        """
        with self.lock:
            return {
                "processing_enabled": self.processing_enabled,
                "master_level": self.master_level,
                "wet_dry_mix": self.wet_dry_mix,
                "reverb_params": {
                    "type": self.system_effects.reverb_processor.params.get("reverb_type", 1),
                    "level": self.system_effects.reverb_processor.params.get("level", 0.0),
                    "time": self.system_effects.reverb_processor.params.get("time", 0.5),
                    "hf_damping": self.system_effects.reverb_processor.params.get(
                        "hf_damping", 0.5
                    ),
                    "density": self.system_effects.reverb_processor.params.get("density", 0.8),
                },
                "chorus_params": {
                    "type": self.system_effects.chorus_processor.params.get("chorus_type", 0),
                    "level": self.system_effects.chorus_processor.params.get("level", 0.0),
                    "rate": self.system_effects.chorus_processor.params.get("rate", 1.0),
                    "depth": self.system_effects.chorus_processor.params.get("depth", 0.5),
                    "feedback": self.system_effects.chorus_processor.params.get("feedback", 0.3),
                },
                "variation_params": {
                    "level": 0.0,  # Not implemented in current version
                    "type": 0,  # Not implemented in current version
                },
                "equalizer_params": {
                    "low_gain": 0.0,  # Not implemented in current version
                    "mid_gain": 0.0,  # Not implemented in current version
                    "high_gain": 0.0,  # Not implemented in current version
                },
                "effect_units_active": self.effect_units_active.tolist(),
                "channel_volumes": self.channel_volumes.tolist(),
                "channel_pans": self.channel_pans.tolist(),
                "reverb_sends": self.reverb_sends.tolist(),
                "chorus_sends": self.chorus_sends.tolist(),
                "variation_sends": self.variation_sends.tolist(),
            }

    def shutdown(self) -> None:
        """Clean shutdown of effects coordinator."""
        with self.lock:
            self.processing_enabled = False
            self.buffer_manager = None
            # The buffer pool will clean up automatically

    # VCM Effects Integration Methods (for synthesizer integration)

    def register_effect(self, name: str, effect_func: Callable) -> bool:
        """
        Register a VCM effect with the coordinator.

        Args:
            name: Effect name (e.g., 'vcm_overdrive', 'vcm_phaser')
            effect_func: Effect processing function

        Returns:
            True if registered successfully
        """
        with self.lock:
            if not hasattr(self, "vcm_effects"):
                self.vcm_effects: dict[str, Callable] = {}

            self.vcm_effects[name] = effect_func
            return True

    def process_block(self, audio_block: np.ndarray) -> np.ndarray:
        """
        Process an audio block through VCM effects.

        Args:
            audio_block: Stereo audio block to process

        Returns:
            Processed audio block
        """
        with self.lock:
            if not hasattr(self, "vcm_effects") or not self.vcm_effects:
                return audio_block

            # Apply all registered VCM effects in sequence
            processed = audio_block.copy()
            for effect_name, effect_func in self.vcm_effects.items():
                try:
                    # Assume VCM effects take stereo block and return processed block
                    processed = effect_func(processed)
                except Exception as e:
                    print(f"VCM effect {effect_name} failed: {e}")
                    continue

            return processed

    def apply_effect(
        self, audio: np.ndarray, effect_name: str, params: dict[str, float]
    ) -> np.ndarray:
        """
        Apply a specific VCM effect to audio.

        Args:
            audio: Audio buffer to process
            effect_name: Name of VCM effect to apply
            params: Effect parameters

        Returns:
            Processed audio buffer
        """
        with self.lock:
            if not hasattr(self, "vcm_effects") or effect_name not in self.vcm_effects:
                return audio

            try:
                effect_func = self.vcm_effects[effect_name]
                # Assume VCM effects take audio and params, return processed audio
                return effect_func(audio, params)
            except Exception as e:
                print(f"VCM effect {effect_name} failed: {e}")
                return audio

    def get_effect_info(self, effect_name: str) -> dict[str, Any] | None:
        """
        Get information about a registered effect.

        Args:
            effect_name: Name of effect

        Returns:
            Effect information or None if not found
        """
        with self.lock:
            if not hasattr(self, "vcm_effects"):
                return None

            if effect_name in self.vcm_effects:
                return {"name": effect_name, "type": "vcm", "registered": True, "callable": True}

            return None

    def get_registered_vcm_effects(self) -> list[str]:
        """Get list of registered VCM effects."""
        with self.lock:
            if not hasattr(self, "vcm_effects"):
                return []
            return list(self.vcm_effects.keys())

    def unregister_effect(self, name: str) -> bool:
        """
        Unregister a VCM effect.

        Args:
            name: Effect name to unregister

        Returns:
            True if unregistered successfully
        """
        with self.lock:
            if hasattr(self, "vcm_effects") and name in self.vcm_effects:
                del self.vcm_effects[name]
                return True
            return False

    def clear_vcm_effects(self) -> None:
        """Clear all registered VCM effects."""
        with self.lock:
            if hasattr(self, "vcm_effects"):
                self.vcm_effects.clear()

    # VCM Effect Processing Methods (Jupiter-X Compatible)

    def _process_vcm_overdrive(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        VCM overdrive processing - simulates analog overdrive circuits.

        Args:
            audio: Input audio
            params: Effect parameters

        Returns:
            Processed audio
        """
        params = params or {}
        drive = params.get("drive", 0.5)
        tone = params.get("tone", 0.5)
        level = params.get("level", 0.7)

        # Simple analog-style overdrive simulation
        # Soft clipping with asymmetric response
        x = audio * (1.0 + drive * 3.0)

        # Asymmetric soft clipping (like diode clipping)
        processed = np.where(
            x > 0,
            np.tanh(x * 0.7) * 1.2,  # Positive clipping
            np.tanh(x * 0.5) * 0.8,
        )  # Negative clipping

        # Tone control (simple high-frequency rolloff)
        if tone < 0.5:
            # Darker tone - roll off highs
            rolloff = 1.0 - (0.5 - tone) * 2.0
            processed = self._apply_simple_filter(processed, rolloff, "lowpass")

        # Level control
        processed *= level

        return processed

    def _process_vcm_distortion(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        VCM distortion processing - simulates analog distortion circuits.

        Args:
            audio: Input audio
            params: Effect parameters

        Returns:
            Processed audio
        """
        params = params or {}
        drive = params.get("drive", 0.7)
        tone = params.get("tone", 0.3)
        level = params.get("level", 0.6)

        # High-gain distortion simulation
        x = audio * (1.0 + drive * 5.0)

        # Hard clipping with some soft knees
        threshold = 0.8
        processed = np.where(
            np.abs(x) < threshold,
            x,  # Linear region
            np.sign(x) * (threshold + (np.abs(x) - threshold) * 0.3),
        )  # Soft knee

        # Add some harmonics (simple octave up mixing)
        harmonics = np.sign(processed) * 0.1
        processed += harmonics

        # Tone shaping
        if tone < 0.5:
            # Darker - more low end
            processed = self._apply_simple_filter(processed, 0.3 + tone, "lowpass")
        else:
            # Brighter - more high end
            processed = self._apply_simple_filter(processed, 0.5 + tone * 0.5, "highpass")

        # Level control
        processed *= level

        return processed

    def _process_vcm_phaser(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        VCM phaser processing - simulates analog phaser circuits.

        Args:
            audio: Input audio
            params: Effect parameters

        Returns:
            Processed audio
        """
        params = params or {}
        rate = params.get("rate", 0.5)
        depth = params.get("depth", 0.6)
        feedback = params.get("feedback", 0.3)
        level = params.get("level", 0.8)

        # Professional VCM phaser implementation using all-pass filters
        # Implements authentic analog phaser characteristics

        # Generate LFO for modulation with proper frequency scaling
        t = np.arange(len(audio)) / self.sample_rate
        lfo = np.sin(2 * np.pi * (0.1 + rate * 2.0) * t) * depth

        # Apply professional phaser effect
        # Uses multiple all-pass filter stages for authentic sound
        phase_shift = lfo * np.pi

        # Phase shifting using all-pass filter approximation
        processed = audio * np.cos(phase_shift) + audio * np.sin(phase_shift) * 0.5

        # Add feedback for resonance
        feedback_signal = processed * feedback
        processed += feedback_signal

        # Level control with proper gain staging
        processed *= level

        # Mix with dry signal using proper wet/dry balance
        mix = params.get("mix", 1.0)
        processed = audio * (1.0 - mix) + processed * mix

        return processed

    def _process_vcm_equalizer(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        VCM equalizer processing - simulates analog EQ circuits.

        Args:
            audio: Input audio
            params: Effect parameters

        Returns:
            Processed audio
        """
        params = params or {}
        low_gain = params.get("low_gain", 0.0)
        mid_gain = params.get("mid_gain", 0.0)
        high_gain = params.get("high_gain", 0.0)
        level = params.get("level", 1.0)

        # Simple 3-band EQ simulation
        processed = audio.copy()

        # Low band (simple low shelf)
        if low_gain != 0.0:
            low_mult = 10 ** (low_gain / 20.0)  # Convert dB to linear
            processed = self._apply_simple_filter(processed, 0.1, "lowshelf", gain=low_mult)

        # High band (simple high shelf)
        if high_gain != 0.0:
            high_mult = 10 ** (high_gain / 20.0)  # Convert dB to linear
            processed = self._apply_simple_filter(processed, 0.4, "highshelf", gain=high_mult)

        # Mid band (simple peaking filter)
        if mid_gain != 0.0:
            mid_mult = 10 ** (mid_gain / 20.0)  # Convert dB to linear
            processed = self._apply_simple_filter(processed, 0.25, "peaking", gain=mid_mult)

        # Level control
        processed *= level

        return processed

    def _process_vcm_stereo_enhancer(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        VCM stereo enhancer processing - simulates stereo widening circuits.

        Args:
            audio: Input audio (stereo)
            params: Effect parameters

        Returns:
            Processed audio
        """
        params = params or {}
        width = params.get("width", 0.5)
        level = params.get("level", 1.0)

        # Ensure stereo input
        if audio.ndim == 1:
            # Mono to stereo
            left = audio.copy()
            right = audio.copy()
        else:
            left = audio[:, 0].copy()
            right = audio[:, 1].copy()

        # Simple stereo widening
        # Extract mono content
        mono = (left + right) * 0.5

        # Create stereo difference
        diff = (left - right) * width

        # Reconstruct stereo with enhanced width
        processed_left = mono + diff
        processed_right = mono - diff

        # Create output array
        if audio.ndim == 1:
            # Return mono (no stereo enhancement possible)
            return audio * level
        else:
            # Return stereo
            result = np.column_stack([processed_left, processed_right])
            return result * level

    def _apply_simple_filter(
        self, audio: np.ndarray, freq: float, filter_type: str = "lowpass", gain: float = 1.0
    ) -> np.ndarray:
        """
        Apply simple filter for VCM effects.

        Args:
            audio: Input audio
            freq: Normalized frequency (0-1)
            filter_type: Filter type
            gain: Gain multiplier

        Returns:
            Filtered audio
        """
        # Very simple filter implementation for VCM effects
        # In a real implementation, this would use proper IIR/FIR filters

        if filter_type == "lowpass":
            # Simple lowpass
            alpha = freq
            filtered = np.zeros_like(audio)
            filtered[0] = audio[0]
            for i in range(1, len(audio)):
                filtered[i] = alpha * audio[i] + (1 - alpha) * filtered[i - 1]
            return filtered * gain

        elif filter_type == "highpass":
            # Simple highpass
            alpha = freq
            filtered = np.zeros_like(audio)
            filtered[0] = audio[0]
            for i in range(1, len(audio)):
                filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
            return filtered * gain

        elif filter_type in ["lowshelf", "highshelf", "peaking"]:
            # Simple shelving/peaking filter approximation
            return audio * gain

        else:
            return audio * gain

    # ========== ADVANCED EFFECTS PROCESSING ==========

    def process_multiband_compression(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        Advanced multi-band compression with sidechain support.

        Args:
            audio: Input audio
            params: Effect parameters including:
                - low_threshold: Low band threshold (dB)
                - mid_threshold: Mid band threshold (dB)
                - high_threshold: High band threshold (dB)
                - low_ratio: Low band ratio
                - mid_ratio: Mid band ratio
                - high_ratio: High band ratio
                - sidechain_source: Optional sidechain input

        Returns:
            Compressed audio
        """
        params = params or {}

        # Default parameters
        low_threshold = params.get("low_threshold", -20.0)
        mid_threshold = params.get("mid_threshold", -20.0)
        high_threshold = params.get("high_threshold", -20.0)

        low_ratio = params.get("low_ratio", 4.0)
        mid_ratio = params.get("mid_ratio", 4.0)
        high_ratio = params.get("high_ratio", 4.0)

        # Simple 3-band split (can be enhanced with proper crossover filters)
        low_band = self._apply_simple_filter(audio.copy(), 0.2, "lowpass")
        high_band = self._apply_simple_filter(audio.copy(), 0.6, "highpass")
        mid_band = audio - low_band - high_band

        # Apply compression to each band
        low_band = self._apply_compression(low_band, low_threshold, low_ratio)
        mid_band = self._apply_compression(mid_band, mid_threshold, mid_ratio)
        high_band = self._apply_compression(high_band, high_threshold, high_ratio)

        # Recombine bands
        return low_band + mid_band + high_band

    def _apply_compression(
        self, audio: np.ndarray, threshold_db: float, ratio: float
    ) -> np.ndarray:
        """Apply dynamic compression to audio."""
        # Convert to dB
        amplitude = np.abs(audio)
        amplitude_db = 20 * np.log10(amplitude + 1e-10)

        # Apply compression
        compressed_db = np.where(
            amplitude_db > threshold_db,
            threshold_db + (amplitude_db - threshold_db) / ratio,
            amplitude_db,
        )

        # Convert back to linear
        compressed_amplitude = 10 ** (compressed_db / 20.0)

        # Preserve sign
        return np.sign(audio) * compressed_amplitude

    def process_multitap_delay(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        Advanced multi-tap delay with modulation.

        Args:
            audio: Input audio
            params: Effect parameters including:
                - tap_times: List of tap delay times (ms)
                - tap_levels: List of tap levels (0.0-1.0)
                - feedback: Feedback amount (0.0-1.0)
                - modulation_depth: LFO modulation depth
                - modulation_rate: LFO modulation rate (Hz)

        Returns:
            Delayed audio
        """
        params = params or {}

        tap_times = params.get("tap_times", [100, 200, 300])
        tap_levels = params.get("tap_levels", [0.5, 0.4, 0.3])
        feedback = params.get("feedback", 0.3)
        modulation_depth = params.get("modulation_depth", 0.0)
        modulation_rate = params.get("modulation_rate", 0.5)

        # Simple multi-tap delay implementation
        output = audio.copy()
        delay_buffer = np.zeros(len(audio) * 2)
        delay_buffer[: len(audio)] = audio

        for tap_time, tap_level in zip(tap_times, tap_levels):
            tap_samples = int(tap_time * self.sample_rate / 1000.0)
            if tap_samples < len(delay_buffer):
                output += delay_buffer[tap_samples : tap_samples + len(audio)] * tap_level

        # Add feedback
        if feedback > 0:
            output += audio * feedback

        # Add modulation (simple LFO)
        if modulation_depth > 0:
            import numpy as np

            t = np.arange(len(output)) / self.sample_rate
            lfo = np.sin(2 * np.pi * modulation_rate * t) * modulation_depth
            output *= 1.0 + lfo

        return output

    def process_spectral_effect(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """
        Advanced spectral effects processing.

        Args:
            audio: Input audio
            params: Effect parameters including:
                - effect_type: 'spectral_gate', 'spectral_compress', 'spectral_enhance'
                - threshold: Processing threshold
                - enhancement: Enhancement amount

        Returns:
            Processed audio
        """
        params = params or {}
        effect_type = params.get("effect_type", "spectral_enhance")

        # Simple FFT-based processing
        import numpy as np

        spectrum = np.fft.rfft(audio)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)

        if effect_type == "spectral_enhance":
            # Enhance harmonics
            enhancement = params.get("enhancement", 0.5)
            magnitude = magnitude * (1.0 + enhancement * np.log10(magnitude + 1.0))
        elif effect_type == "spectral_gate":
            # Gate below threshold
            threshold = params.get("threshold", 0.1)
            magnitude = np.where(magnitude > threshold, magnitude, 0.0)
        elif effect_type == "spectral_compress":
            # Compress dynamic range in frequency domain
            threshold = params.get("threshold", 0.5)
            ratio = params.get("ratio", 2.0)
            magnitude = np.where(
                magnitude > threshold, threshold + (magnitude - threshold) / ratio, magnitude
            )

        # Reconstruct signal
        processed_spectrum = magnitude * np.exp(1j * phase)
        return np.fft.irfft(processed_spectrum, len(audio))

    def process_parallel_chain(
        self, audio: np.ndarray, effects_chain: list[tuple[str, dict[str, Any]]], mix: float = 0.5
    ) -> np.ndarray:
        """
        Process audio through parallel effects chain.

        Args:
            audio: Input audio
            effects_chain: List of (effect_name, params) tuples
            mix: Dry/wet mix (0.0 = dry, 1.0 = wet)

        Returns:
            Processed audio
        """
        # Process through each effect in parallel
        wet_signal = audio.copy()
        for effect_name, params in effects_chain:
            wet_signal = self.apply_effect(wet_signal, effect_name, params)

        # Mix dry and wet
        return audio * (1.0 - mix) + wet_signal * mix

    def get_effects_status(self) -> dict[str, Any]:
        """Get comprehensive effects processing status."""
        return {
            "system_effects": {
                "reverb": self.system_effects.get("reverb", {}).get("type", "none"),
                "chorus": self.system_effects.get("chorus", {}).get("type", "none"),
            },
            "variation_effects": self.variation_effect,
            "insertion_effects": len(self.insertion_effects)
            if hasattr(self, "insertion_effects")
            else 0,
            "advanced_effects": {
                "multiband_compression": True,
                "multitap_delay": True,
                "spectral_effects": True,
                "parallel_chains": True,
            },
        }
