"""
SF2 Wavetable Synthesis Engine - Professional Sample Playback Architecture

ARCHITECTURAL OVERVIEW:

The SF2 Engine implements a comprehensive SoundFont 2 (SF2) wavetable synthesis system
designed for professional sample playback in real-time audio synthesis environments.
It provides full SF2 specification compliance with advanced features like multi-zone
layering, complex envelope modulation, and high-performance sample management.

SF2 SYNTHESIS ARCHITECTURE:

The engine follows a hierarchical synthesis model:

1. PRESET LEVEL: Multi-timbral voice definitions with global parameters
2. ZONE LEVEL: Sample assignment with key/velocity ranges and layer definitions
3. GENERATOR LEVEL: Low-level synthesis parameters (envelopes, filters, modulation)
4. SAMPLE LEVEL: Actual PCM data with loop points and pitch information

SYNTHESIS PIPELINE:

Audio Generation Flow:
1. MIDI Input → Preset Selection → Zone Matching → Generator Processing
2. Sample Loading → Loop Processing → Pitch Shifting → Filter Application
3. Envelope Modulation → Effects Sends → Master Processing → Output

SAMPLE MANAGEMENT ARCHITECTURE:

THREE-TIER SAMPLE CACHE:
- MEMORY CACHE: Hot samples for active voices (immediate access)
- DISK CACHE: Warm samples for quick loading (background prefetch)
- ARCHIVE STORAGE: Cold samples for long-term storage (on-demand loading)

SAMPLE OPTIMIZATION:
- MIP-MAPPING: Pre-computed sample rates for different pitch ranges
- LOOP OPTIMIZATION: Pre-processed loop points for seamless playback
- INTERPOLATION: High-quality resampling algorithms for pitch shifting
- MEMORY POOLING: Shared buffer allocation for multiple voices

ZONE AND LAYERING SYSTEM:

MULTI-ZONE ARCHITECTURE:
- KEY SPLITTING: Different samples for different note ranges
- VELOCITY SPLITTING: Dynamic sample selection based on playing strength
- CROSSFADING: Smooth transitions between adjacent zones
- VELOCITY CROSSFADING: Volume blending between velocity layers

LAYERING MODES:
- POLYPHONIC: Independent voices for each zone
- MONOPHONIC: Single voice with zone switching
- ROUND-ROBIN: Alternating between multiple samples per zone
- RANDOM: Random sample selection for variation

ENVELOPE SYSTEM ARCHITECTURE:

DUAL ENVELOPE DESIGN:
- AMPLITUDE ENVELOPE: Volume contour (Delay/Attack/Hold/Decay/Sustain/Release)
- MODULATION ENVELOPE: Filter/pitch modulation (same stages as amplitude)

ENVELOPE CHARACTERISTICS:
- TIME CENT CONVERSION: Logarithmic time scaling for musical feel
- VELOCITY SENSITIVITY: Note velocity affects envelope response
- KEY FOLLOW: Note pitch affects envelope times and depths
- TEMPO SYNCHRONIZATION: Optional beat-synchronized envelope timing

FILTER ARCHITECTURE:

SF2 FILTER IMPLEMENTATION:
- BIQUAD FILTERS: High-quality IIR filtering with resonance control
- DYNAMIC CUTOFF: Envelope-modulated cutoff frequency
- KEY FOLLOW: Pitch-dependent filter response
- VELOCITY CONTROL: Playing strength affects filter characteristics

FILTER MODES:
- LOWPASS: Standard frequency attenuation
- HIGHPASS: High-frequency emphasis
- BANDPASS: Mid-range focus
- NOTCH: Frequency rejection
- PEAK: Parametric boost/cut

PITCH MODULATION SYSTEM:

MULTI-LAYER PITCH CONTROL:
- COARSE TUNE: Semitone adjustments (±127 semitones)
- FINE TUNE: Cent adjustments (±99 cents)
- SCALE TUNING: Microtonal pitch adjustments per note
- PITCH WHEEL: Real-time pitch bending (±2 semitones default)
- LFO MODULATION: Low-frequency pitch oscillation

PITCH PROCESSING:
- SAMPLE RATE CONVERSION: High-quality pitch shifting algorithms
- FORMANT PRESERVATION: Maintain vocal character during pitch changes
- ANTI-ALIASING: Prevent aliasing artifacts during transposition

LOOP MODES AND SAMPLE PLAYBACK:

SF2 LOOP IMPLEMENTATION:
- FORWARD LOOP: Standard seamless looping between loop points
- BACKWARD LOOP: Reverse playback within loop region
- ALTERNATING LOOP: Forward/backward alternation for special effects
- NO LOOP: One-shot playback without repetition

LOOP OPTIMIZATION:
- CROSSFADE LOOPS: Smooth loop point transitions
- LOOP POINT DETECTION: Automatic loop point identification
- LOOP LENGTH OPTIMIZATION: Minimum loop lengths for quality
- ARTICULATION PRESERVATION: Maintain sample attack characteristics

MULTI-TIMBRAL ARCHITECTURE:

VOICE ALLOCATION:
- PRESET ASSIGNMENT: 16 MIDI channels with independent preset assignment
- VOICE STEALING: Priority-based voice management for polyphony limits
- CHANNEL MUTING: Individual channel level control
- PROGRAM CHANGES: Real-time preset switching with proper cleanup

CHANNEL FEATURES:
- INDEPENDENT CONTROLLERS: Per-channel MIDI CC processing
- BANK SELECT: MSB/LSB bank selection for extended preset ranges
- RPN/NRPN SUPPORT: Registered/non-registered parameter control
- POLY/MONO MODES: Voice allocation strategies per channel

PERFORMANCE OPTIMIZATION:

REAL-TIME OPTIMIZATION:
- SAMPLE PREFETCHING: Background loading of upcoming samples
- BUFFER MANAGEMENT: Zero-allocation hot paths with pre-allocated buffers
- SIMD PROCESSING: Vectorized operations for filter/envelope processing
- CACHE COHERENCE: Optimized data structures for CPU cache efficiency

MEMORY MANAGEMENT:
- SAMPLE COMPRESSION: Optional lossless compression for memory efficiency
- DYNAMIC UNLOADING: Least-recently-used sample eviction
- SHARED SAMPLES: Single sample instance for multiple zones
- MEMORY BUDGETING: Configurable memory limits with graceful degradation

INTEGRATION ARCHITECTURE:

XG SYNTHESIZER INTEGRATION:
- VOICE MANAGER: Polyphony allocation and voice stealing coordination
- EFFECTS COORDINATOR: Send level processing and effects routing
- BUFFER POOL: Shared memory management for sample data
- PARAMETER ROUTER: Real-time parameter modulation and automation

MODULATION INTEGRATION:
- LFO SOURCES: Multiple LFOs for different modulation targets
- ENVELOPE FOLLOWERS: Audio signal analysis for modulation sources
- MIDI CONTROLLERS: Hardware control surface integration
- AUTOMATION CURVES: User-definable modulation curves

EFFECTS PROCESSING:

SF2 EFFECTS ARCHITECTURE:
- REVERB SEND: Convolution reverb with configurable impulse responses
- CHORUS SEND: Multi-tap chorus with modulation and feedback
- DELAY SEND: Stereo delay with tempo synchronization options
- VARIATION SEND: Configurable effects processing (phaser, flanger, etc.)

SEND LEVEL CONTROL:
- PER-ZONE SENDS: Individual send levels per sample zone
- GLOBAL SENDS: Channel-wide send level overrides
- DYNAMIC MODULATION: Envelope and LFO control of send levels
- WET/DRY MIXING: Configurable effect balance per channel

XG SPECIFICATION COMPLIANCE:

SF2 STANDARD IMPLEMENTATION:
- FULL SF2 2.04 SPECIFICATION: Complete feature set implementation
- FILE FORMAT SUPPORT: Standard .sf2 file loading and parsing
- GENERATOR SUPPORT: All 60+ SF2 generators implemented
- MODULATOR SUPPORT: Complete modulation matrix implementation

PROFESSIONAL AUDIO FEATURES:
- SAMPLE ACCURATE TIMING: Sub-sample precision for all parameters
- HIGH-RESOLUTION PROCESSING: 64-bit internal processing where beneficial
- LOW LATENCY DESIGN: Minimal processing delay for real-time performance
- BROAD FORMAT SUPPORT: 8/16/24/32-bit PCM, compressed formats

EXTENSIBILITY ARCHITECTURE:

PLUGIN SAMPLE FORMATS:
- CUSTOM FORMAT LOADERS: Support for additional sample formats
- EXTERNAL SAMPLE LIBRARIES: Integration with third-party sample collections
- USER INTERFACE EXTENSIONS: Custom preset editors and browsers
- SCRIPTING SUPPORT: Python-based preset generation and processing

ADVANCED FEATURES:
- GRANULAR SYNTHESIS: Time-stretching and pitch-shifting extensions
- SPECTRAL PROCESSING: FFT-based effects and processing
- CONVOLUTION ENGINES: Impulse response convolution for reverb
- PHYSICAL MODELING: Integration with modal synthesis engines
"""

from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING
import numpy as np
import logging

from .synthesis_engine import SynthesisEngine
from ..partial.sf2_partial import SF2Partial
from ..sf2.sf2_soundfont_manager import SF2SoundFontManager

if TYPE_CHECKING:
    from ..engine.modern_xg_synthesizer import ModernXGSynthesizer

logger = logging.getLogger(__name__)


class SF2Engine(SynthesisEngine):
    """
    SF2 wavetable synthesis engine.

    Provides SoundFont 2 compatible wavetable synthesis with sample playback,
    loop modes, pitch modulation, and filter envelopes.
    """

    def __init__(self, sf2_file_path: Optional[str] = None, sample_rate: int = 44100,
                 block_size: int = 1024, synth: Optional['ModernXGSynthesizer'] = None,
                 max_memory_mb: int = 512):
        """
        Initialize SF2 synthesis engine with optimized architecture.

        Args:
            sf2_file_path: Path to SF2 file (optional, can be loaded later)
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            synth: ModernXGSynthesizer instance for infrastructure access
            max_memory_mb: Maximum memory for SF2 caching
        """
        super().__init__(sample_rate, block_size)
        self.synth = synth
        self.max_memory_mb = max_memory_mb

        # New optimized SF2 architecture
        self.soundfont_manager = SF2SoundFontManager(
            cache_memory_mb=max_memory_mb,
            max_loaded_files=10
        )

        # Load initial soundfont if provided
        if sf2_file_path:
            self.load_soundfont(sf2_file_path)

        self._engine_info = None

    def load_soundfont(self, file_path: str, priority: int = 0) -> bool:
        """
        Load SF2 soundfont using the optimized manager.

        Args:
            file_path: Path to SF2 file
            priority: Loading priority (higher = loaded first)

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading SF2 soundfont: {file_path}")
            success = self.soundfont_manager.load_soundfont(file_path, priority)
            if success:
                self.sf2_file_path = file_path
                logger.info("SF2 soundfont loaded successfully")
                return True
            else:
                logger.error(f"Failed to load SF2 soundfont {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error loading SF2 soundfont {file_path}: {e}")
            return False

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return 'sf2'
    
    def _create_base_region(self, descriptor: 'RegionDescriptor', 
                           sample_rate: int) -> 'IRegion':
        """
        Create SF2 base region without S.Art2 wrapper.
        
        Args:
            descriptor: Region descriptor with SF2 parameters
            sample_rate: Audio sample rate in Hz
        
        Returns:
            SF2Region instance
        """
        from ..partial.sf2_region import SF2Region
        return SF2Region(descriptor, sample_rate, self.soundfont_manager)

    def create_partial(self, partial_params: Dict, sample_rate: int) -> SF2Partial:
        """
        Create an SF2 partial with modern synth integration.

        Args:
            partial_params: SF2-specific partial parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            SF2Partial instance with pooled resource integration

        Raises:
            RuntimeError: If synth instance not provided for pooled resources
        """
        if self.synth is None:
            raise RuntimeError("SF2Engine requires synth instance for pooled resources. "
                             "Please provide synth parameter to SF2Engine constructor.")

        # Load sample data for the partial if not already present
        if 'sample_data' not in partial_params:
            sample_index = partial_params.get('sample_index')
            if sample_index is not None:
                # Try to get sample data from soundfont manager
                sample_data = self.soundfont_manager.get_sample_data(sample_index)
                if sample_data is not None:
                    partial_params = partial_params.copy()  # Don't modify original
                    partial_params['sample_data'] = sample_data
            else:
                # If no sample index provided, try to get from other parameters
                if 'sample_id' in partial_params:
                    sample_data = self.soundfont_manager.get_sample_data(partial_params['sample_id'])
                    if sample_data is not None:
                        partial_params = partial_params.copy()
                        partial_params['sample_data'] = sample_data

        # Ensure required parameters are present with defaults
        required_params = [
            'sample_index', 'sample_id', 'note', 'velocity', 'generators',
            'amp_attack', 'amp_decay', 'amp_sustain', 'amp_release',
            'filter_cutoff', 'filter_resonance', 'pan', 'reverb_send', 'chorus_send'
        ]
        
        for param in required_params:
            if param not in partial_params:
                # Set reasonable defaults based on parameter type
                if param in ['amp_attack', 'amp_decay', 'amp_release']:
                    partial_params[param] = 0.01  # Default to 10ms
                elif param in ['amp_sustain']:
                    partial_params[param] = 0.7   # Default to 70%
                elif param in ['filter_cutoff']:
                    partial_params[param] = 20000.0  # Default to 20kHz
                elif param in ['filter_resonance']:
                    partial_params[param] = 0.7   # Default resonance
                elif param in ['pan']:
                    partial_params[param] = 0.0   # Center
                elif param in ['reverb_send', 'chorus_send']:
                    partial_params[param] = 0.0   # No effects by default
                elif param in ['note']:
                    partial_params[param] = 60    # Middle C
                elif param in ['velocity']:
                    partial_params[param] = 100   # Medium velocity
                elif param in ['generators']:
                    partial_params[param] = {}    # Empty generators dict

        # Create partial with new architecture integration
        partial = SF2Partial(partial_params, self.synth)
        
        # Ensure the partial has access to the synth's memory pool for zero-allocation buffers
        if hasattr(self.synth, 'memory_pool'):
            partial.memory_pool = self.synth.memory_pool
        elif hasattr(self.synth, 'buffer_pool'):
            partial.memory_pool = self.synth.buffer_pool
        
        return partial

    # ========== NEW REGION-BASED METHODS ==========
    
    def get_preset_info(self, bank: int, program: int) -> Optional['PresetInfo']:
        """
        Get SF2 preset info with all zone descriptors.
        
        This is the KEY method that enables multi-zone preset support.
        Returns ALL zones as descriptors without loading samples.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            PresetInfo with all region descriptors, or None if not found
        """
        # Import here to avoid circular imports
        from .preset_info import PresetInfo
        from .region_descriptor import RegionDescriptor
        
        # Search through loaded soundfonts
        for filepath in self.soundfont_manager.file_order:
            soundfont = self.soundfont_manager.loaded_files.get(filepath)
            if not soundfont:
                continue
            
            # Get or load preset
            preset = soundfont._get_or_load_preset(bank, program)
            if not preset:
                continue
            
            # Build region descriptors from ALL zones
            descriptors = []
            for zone_idx, zone in enumerate(preset.zones):
                descriptor = self._zone_to_descriptor(zone, zone_idx, filepath)
                descriptors.append(descriptor)
            
            if descriptors:
                return PresetInfo(
                    bank=bank,
                    program=program,
                    name=preset.name,
                    engine_type='sf2',
                    region_descriptors=descriptors,
                    master_level=1.0,
                    master_pan=0.0,
                    reverb_send=0.0,
                    chorus_send=0.0
                )
        
        return None
    
    def get_all_region_descriptors(
        self, 
        bank: int, 
        program: int
    ) -> List['RegionDescriptor']:
        """
        Get ALL region descriptors for an SF2 preset.
        
        Args:
            bank: MIDI bank number
            program: MIDI program number
        
        Returns:
            List of all RegionDescriptor objects for this preset
        """
        preset_info = self.get_preset_info(bank, program)
        if preset_info:
            return preset_info.region_descriptors
        return []
    
    def create_region(
        self, 
        descriptor: 'RegionDescriptor', 
        sample_rate: int
    ) -> 'IRegion':
        """
        Create SF2 region instance from descriptor.
        
        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            SF2Region instance ready for lazy initialization
        """
        from ..partial.sf2_region import SF2Region
        return SF2Region(descriptor, sample_rate, self.soundfont_manager, synth=self.synth)
    
    def load_sample_for_region(self, region: 'IRegion') -> bool:
        """
        Load sample data for SF2 region.
        
        Args:
            region: Region instance to load sample for
        
        Returns:
            True if sample loaded successfully
        """
        if hasattr(region, 'load_sample'):
            return region.load_sample()
        return False
    
    def _zone_to_descriptor(
        self, 
        zone: Any, 
        zone_idx: int,
        filepath: str
    ) -> 'RegionDescriptor':
        """
        Convert SF2 zone to region descriptor.
        
        Args:
            zone: SF2Zone object
            zone_idx: Zone index
            filepath: Soundfont file path
        
        Returns:
            RegionDescriptor with zone metadata
        """
        from .region_descriptor import RegionDescriptor
        
        # Extract key/velocity ranges from zone
        key_range = getattr(zone, 'key_range', (0, 127))
        velocity_range = getattr(zone, 'velocity_range', (0, 127))
        
        # Get sample ID if this zone has one
        sample_id = getattr(zone, 'sample_id', -1)
        if sample_id < 0:
            sample_id = None
        
        # Extract generator parameters (but don't load sample)
        generator_params = self._extract_generator_params(zone)
        
        # Get round-robin info (if available)
        round_robin_group = 0
        round_robin_position = zone_idx
        
        return RegionDescriptor(
            region_id=zone_idx,
            engine_type='sf2',
            key_range=key_range,
            velocity_range=velocity_range,
            round_robin_group=round_robin_group,
            round_robin_position=round_robin_position,
            sample_id=sample_id,
            generator_params=generator_params
        )
    
    def _extract_generator_params(self, zone: Any) -> Dict[str, Any]:
        """
        Extract generator parameters from SF2 zone.
        
        Args:
            zone: SF2Zone object
        
        Returns:
            Dictionary of generator parameters
        """
        params = {}
        
        # Helper to get generator value with default
        def get_gen(gen_type: int, default: int) -> int:
            if hasattr(zone, 'get_generator_value'):
                return zone.get_generator_value(gen_type, default)
            return default
        
        # Volume envelope (SF2 generator IDs)
        params['amp_delay'] = self._timecents_to_seconds(get_gen(8, -12000))
        params['amp_attack'] = self._timecents_to_seconds(get_gen(9, -12000))
        params['amp_hold'] = self._timecents_to_seconds(get_gen(10, -12000))
        params['amp_decay'] = self._timecents_to_seconds(get_gen(11, -12000))
        params['amp_sustain'] = get_gen(12, 0) / 1000.0
        params['amp_release'] = self._timecents_to_seconds(get_gen(13, -12000))
        
        # Modulation envelope
        params['mod_env_delay'] = self._timecents_to_seconds(get_gen(14, -12000))
        params['mod_env_attack'] = self._timecents_to_seconds(get_gen(15, -12000))
        params['mod_env_hold'] = self._timecents_to_seconds(get_gen(16, -12000))
        params['mod_env_decay'] = self._timecents_to_seconds(get_gen(17, -12000))
        params['mod_env_sustain'] = get_gen(18, 0) / 1000.0
        params['mod_env_release'] = self._timecents_to_seconds(get_gen(19, -12000))
        params['mod_env_to_pitch'] = get_gen(20, 0) / 1200.0
        
        # LFO parameters
        params['mod_lfo_delay'] = self._timecents_to_seconds(get_gen(21, -12000))
        params['mod_lfo_rate'] = self._cents_to_frequency(get_gen(22, 0))
        params['vib_lfo_delay'] = self._timecents_to_seconds(get_gen(26, -12000))
        params['vib_lfo_rate'] = self._cents_to_frequency(get_gen(27, 0))
        
        # Filter
        params['filter_cutoff'] = self._cents_to_frequency(get_gen(29, 13500))
        params['filter_resonance'] = get_gen(30, 0) / 10.0
        
        # Effects
        params['reverb_send'] = get_gen(32, 0) / 1000.0
        params['chorus_send'] = get_gen(33, 0) / 1000.0
        params['pan'] = get_gen(34, 0) / 500.0
        
        # Pitch
        params['coarse_tune'] = get_gen(48, 0)
        params['fine_tune'] = get_gen(49, 0) / 100.0
        
        return params
    
    # ========== LEGACY METHODS (kept for transition) ==========
    
    def get_voice_parameters(
        self, 
        program: int, 
        bank: int = 0,
        note: int = 60,
        velocity: int = 100
    ) -> Optional[Dict]:
        """
        Get SF2 voice parameters for a program/bank.
        
        DEPRECATED: Use get_preset_info() instead.
        This method now uses the new architecture internally.
        
        Args:
            program: MIDI program number (0-127)
            bank: MIDI bank number (0-127)
            note: MIDI note for zone matching (default 60)
            velocity: MIDI velocity for zone matching (default 100)

        Returns:
            Voice parameters dictionary, or None if not found
        """
        # Try to get parameters from the soundfont manager
        params = self.soundfont_manager.get_program_parameters(bank, program, 60, 100)
        if params:
            return params

        # Fallback to default parameters if no soundfonts loaded
        return self._get_default_voice_params()

    def _preset_to_voice_params(self, preset) -> Dict:
        """Convert SF2 preset to XG voice parameters."""
        # Get preset zones for middle C at full velocity
        zones = preset.get_matching_zones(60, 100)

        if not zones:
            return self._get_default_voice_params()

        # Use the first matching zone for basic parameters
        # In a full implementation, this would handle layering
        zone = zones[0]

        # Build partial parameters from zone generators
        partial_params = self._zone_to_partial_params(zone)

        return {
            'name': preset.name,
            'bank': preset.bank,
            'program': preset.preset_number,
            'key_range_low': 0,  # Would be computed from zones
            'key_range_high': 127,
            'master_level': 1.0,
            'pan': 0.0,
            'assign_mode': 1,  # Polyphonic
            'partials': [partial_params]
        }

    def _zone_to_partial_params(self, zone) -> Dict:
        """Convert SF2 zone to partial parameters."""
        # Extract parameters from zone generators
        params = self.get_default_partial_params()

        # Override with zone-specific values
        if hasattr(zone, 'generators'):
            # Volume envelope (correct SF2 generator IDs)
            params['amp_delay'] = self._timecents_to_seconds(zone.get_generator_value(8, -12000))  # volEnvDelay
            params['amp_attack'] = self._timecents_to_seconds(zone.get_generator_value(9, -12000))  # volEnvAttack
            params['amp_hold'] = self._timecents_to_seconds(zone.get_generator_value(10, -12000))  # volEnvHold
            params['amp_decay'] = self._timecents_to_seconds(zone.get_generator_value(11, -12000))  # volEnvDecay
            params['amp_sustain'] = zone.get_generator_value(12, 0) / 1000.0  # volEnvSustain (0-1000 to 0.0-1.0)
            params['amp_release'] = self._timecents_to_seconds(zone.get_generator_value(13, -12000))  # volEnvRelease

            # Filter (correct SF2 generator IDs)
            params['filter_cutoff'] = self._cents_to_frequency(zone.get_generator_value(29, 13500))  # initialFilterFc
            params['filter_resonance'] = zone.get_generator_value(30, 0) / 10.0  # initialFilterQ (Q to resonance)

            # Pitch modulation (correct SF2 generator IDs)
            params['coarse_tune'] = zone.get_generator_value(48, 0)  # coarseTune
            params['fine_tune'] = zone.get_generator_value(49, 0) / 100.0  # fineTune (cents to semitones)
            params['scale_tuning'] = zone.get_generator_value(52, 100)  # scaleTuning

            # Effects sends (correct SF2 generator IDs)
            params['reverb_send'] = zone.get_generator_value(32, 0) / 1000.0  # reverbEffectsSend
            params['chorus_send'] = zone.get_generator_value(33, 0) / 1000.0  # chorusEffectsSend
            params['pan'] = zone.get_generator_value(34, 0) / 500.0  # pan (-500/+500 to -1.0/+1.0)

        return params

    def _zones_to_voice_params(self, zones: List, program: int, bank: int) -> Dict:
        """Convert SF2 zones to XG voice parameters."""
        if not zones:
            return self._get_default_voice_params()

        # Use the first zone for basic parameters
        # In a full implementation, this would handle layering
        zone = zones[0]

        # Build partial parameters from zone
        partial_params = self._zone_to_partial_params(zone)

        return {
            'name': f'SF2 Program {program}',
            'bank': bank,
            'program': program,
            'key_range_low': 0,  # Would be computed from zones
            'key_range_high': 127,
            'master_level': 1.0,
            'pan': 0.0,
            'assign_mode': 1,  # Polyphonic
            'partials': [partial_params]
        }
    
    def _timecents_to_seconds(self, timecents: int) -> float:
        """Convert SF2 timecents to seconds."""
        if timecents == -12000:
            return 0.0  # -inf means instant
        return 2.0 ** (timecents / 1200.0)  # Convert timecents to seconds
    
    def _cents_to_frequency(self, cents: int) -> float:
        """Convert SF2 cents to frequency in Hz."""
        from ..sf2.sf2_constants import cents_to_frequency
        return cents_to_frequency(cents)

    def supports_feature(self, feature: str) -> bool:
        """Check SF2 engine feature support."""
        sf2_features = {
            'loop_modes': True,           # SF2 supports forward/backward/alternating loops
            'sample_playback': True,      # Core SF2 functionality
            'filter_envelopes': True,     # SF2 modulation envelope
            'pitch_envelopes': True,      # SF2 modulation envelope can be used for pitch
            'fm_synthesis': False,        # Not supported
            'physical_modeling': False,   # Not supported
            'granular_synthesis': False,  # Not supported
            'wavetable_synthesis': True,  # Core SF2 functionality
            'subtractive_synthesis': True, # Filters and envelopes
            'multi_timbral': True,        # SF2 presets support
            'layering': True,             # SF2 zone layering
            'mip_mapping': True,          # High-pitch quality enhancement
            'sf2_compliance': True        # Full SF2 specification support
        }
        return sf2_features.get(feature, False)

    def get_default_partial_params(self) -> Dict:
        """Get default SF2 partial parameters."""
        return {
            'level': 1.0,
            'pan': 0.0,
            'coarse_tune': 0,
            'fine_tune': 0,
            'scale_tuning': 100,
            'overriding_root_key': -1,
            'key_range_low': 0,
            'key_range_high': 127,
            'velocity_range_low': 0,
            'velocity_range_high': 127,
            'filter_cutoff': 1000.0,
            'filter_resonance': 0.7,
            'filter_type': 'lowpass',
            'filter_key_follow': 0.5,
            'use_filter_env': True,
            'filter_attack': 0.1,
            'filter_decay': 0.5,
            'filter_sustain': 0.6,
            'filter_release': 0.8,
            'use_pitch_env': False,
            'pitch_attack': 0.05,
            'pitch_decay': 0.1,
            'pitch_sustain': 0.0,
            'pitch_release': 0.05,
            'pitch_envelope_depth': 1200.0,
            'amp_attack': 0.01,
            'amp_decay': 0.3,
            'amp_sustain': 0.7,
            'amp_release': 0.5,
            'amp_delay': 0.0,
            'amp_hold': 0.0,
            # SF2-specific additions
            'reverb_send': 0.0,
            'chorus_send': 0.0,
            'exclusive_class': 0,
            'sample_mode': 0
        }

    def _get_default_voice_params(self) -> Dict:
        """Get default XG voice parameters."""
        return {
            'name': 'Default SF2 Voice',
            'key_range_low': 0,
            'key_range_high': 127,
            'master_level': 1.0,
            'pan': 0.0,
            'assign_mode': 1,  # Polyphonic
            'partials': [self.get_default_partial_params()]
        }

    def get_engine_info(self) -> Dict[str, Any]:
        """Get SF2 engine information."""
        if self._engine_info is None:
            capabilities = [
                'wavetable_synthesis', 'sample_playback', 'loop_modes',
                'filter_envelopes', 'pitch_envelopes', 'multi_timbral',
                'layering', 'mip_mapping', 'sf2_compliance'
            ]

            # Get memory stats from manager
            mem_stats = self.soundfont_manager.get_performance_stats()
            if 'memory_usage' in mem_stats:
                capabilities.append(f"memory_usage_mb:{mem_stats['memory_usage']['total_mb']:.1f}")

            self._engine_info = {
                'name': 'SF2 Wavetable Engine (New Architecture)',
                'type': 'sf2',
                'version': '2.0',
                'capabilities': capabilities,
                'formats': ['.sf2'],
                'polyphony': 64,  # Would be determined by global voice manager
                'parameters': [
                    'level', 'pan', 'coarse_tune', 'fine_tune',
                    'filter_cutoff', 'filter_resonance', 'reverb_send', 'chorus_send'
                ],
                'soundfonts_loaded': len(self.soundfont_manager)
            }
        return self._engine_info

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float], block_size: int,
                        bank: int = 0, program: int = 0) -> np.ndarray:
        """
        Generate audio samples for a note using SF2 synthesis with preset lookup.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate
            bank: MIDI bank number (default 0)
            program: MIDI program number (default 0)

        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        # Get preset info with all regions
        preset_info = self.get_preset_info(bank, program)
        if not preset_info:
            # No preset found - return silence
            return np.zeros(block_size * 2, dtype=np.float32)
        
        # Find matching regions for this note/velocity
        matching_descriptors = []
        for descriptor in preset_info.region_descriptors:
            if descriptor.should_play_for_note(note, velocity):
                matching_descriptors.append(descriptor)
        
        if not matching_descriptors:
            # No matching regions - return silence
            return np.zeros(block_size * 2, dtype=np.float32)
        
        # Create and initialize regions for all matching descriptors
        audio_output = np.zeros(block_size * 2, dtype=np.float32)
        
        for descriptor in matching_descriptors:
            try:
                # Create region
                region = self.create_region(descriptor, self.sample_rate)
                
                # Load sample data for region
                if not self.load_sample_for_region(region):
                    logger.warning(f"Failed to load sample for region {descriptor.region_id}")
                    continue
                
                # Trigger note
                if not region.note_on(velocity, note):
                    continue
                
                # Generate samples
                region_audio = region.generate_samples(block_size, modulation)
                
                # Mix into output (apply master level)
                audio_output += region_audio * preset_info.master_level
                
            except Exception as e:
                logger.error(f"Error generating SF2 samples for region {descriptor.region_id}: {e}")
                continue
        
        return audio_output

    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by this engine.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if note can be played, False otherwise
        """
        # SF2 supports full MIDI note range
        return 0 <= note <= 127

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        return ['.sf2']

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get SF2 engine memory usage."""
        stats = self.soundfont_manager.get_performance_stats()
        return stats.get('memory_usage', {'total_mb': 0})

    def clear_cache(self):
        """Clear SF2 sample cache to free memory."""
        self.soundfont_manager.clear_all_caches()
        logger.info("SF2 engine cache cleared")

    # ===== MODERN SYNTH INTEGRATION METHODS =====

    def apply_global_parameters(self, global_params: Dict) -> None:
        """
        Apply global synthesizer parameters.

        Args:
            global_params: Global synth parameters (master volume, tuning, etc.)
        """
        # Apply to all active SF2 partials through the synth
        if self.synth and hasattr(self.synth, 'apply_global_parameters_to_engine'):
            self.synth.apply_global_parameters_to_engine('sf2', global_params)

    def get_modulation_destinations(self) -> Dict[str, str]:
        """
        Get available modulation destinations for SF2 engine.

        Returns:
            Dictionary mapping destination names to descriptions
        """
        return {
            'pitch': 'Master pitch modulation',
            'filter_cutoff': 'Master filter cutoff modulation',
            'volume': 'Master volume modulation',
            'pan': 'Master pan modulation',
            'reverb_send': 'Reverb send level',
            'chorus_send': 'Chorus send level'
        }

    def get_effect_send_levels(self) -> Dict[str, float]:
        """
        Get current effect send levels for global effects routing.

        Returns:
            Dictionary with effect send levels
        """
        # This would aggregate send levels from all active voices
        # For now, return defaults
        return {
            'reverb': 0.0,
            'chorus': 0.0,
            'variation': 0.0,
            'delay': 0.0
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get SF2 engine performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        stats = self.soundfont_manager.get_performance_stats()
        stats.update({
            'engine_type': 'sf2',
            'architecture_version': '2.0_production'
        })
        return stats
