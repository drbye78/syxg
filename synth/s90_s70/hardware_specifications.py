"""
S90/S70 Hardware Specifications

Authentic hardware characteristics, parameters, and behaviors
specific to Yamaha S90 and S70 synthesizers.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class S90S70HardwareProfile:
    """Hardware profile for S90/S70 synthesizers"""

    # Basic specifications
    model_name: str
    polyphony: int
    multitimbral_parts: int
    sample_rate: int = 44100
    bit_depth: int = 24

    # AWM engine specifications
    awm_voices: int = 128
    awm_samples_per_voice: int = 2
    awm_filters_per_voice: int = 2
    awm_envelopes_per_voice: int = 3

    # AN engine specifications (S90 only)
    an_engines: int = 0  # 0 for S70, 2 for S90
    an_polyphony: int = 32

    # FDSP engine specifications
    fdsp_voices: int = 1
    fdsp_polyphony: int = 32

    # Effects specifications
    insertion_effects_per_part: int = 3
    system_effects: int = 2
    variation_effects: int = 1
    master_effects: int = 1

    # Memory specifications
    wave_rom_size_mb: int = 64
    user_samples_memory_mb: int = 32
    preset_memory_slots: int = 128
    user_memory_slots: int = 128

    # Control surface
    assignable_knobs: int = 4
    assignable_sliders: int = 0
    assignable_buttons: int = 4

    # Display
    display_type: str = "LCD"
    display_lines: int = 2
    display_chars_per_line: int = 16


class S90S70HardwareSpecs:
    """
    S90/S70 Hardware Specifications Manager

    Provides authentic hardware characteristics, parameter behaviors,
    and compatibility features for S90/S70 synthesizers.
    """

    def __init__(self):
        """Initialize hardware specifications"""
        self.profiles = {
            'S70': S90S70HardwareProfile(
                model_name="S70",
                polyphony=64,
                multitimbral_parts=16,
                awm_voices=64,
                an_engines=0,  # No AN engine on S70
                wave_rom_size_mb=32,
                assignable_knobs=4,
                assignable_sliders=0,
                assignable_buttons=4
            ),
            'S90': S90S70HardwareProfile(
                model_name="S90",
                polyphony=64,
                multitimbral_parts=16,
                awm_voices=64,
                an_engines=2,  # Dual AN engines
                wave_rom_size_mb=64,
                assignable_knobs=4,
                assignable_sliders=0,
                assignable_buttons=4
            ),
            'S90ES': S90S70HardwareProfile(
                model_name="S90ES",
                polyphony=128,
                multitimbral_parts=32,
                awm_voices=128,
                an_engines=2,
                wave_rom_size_mb=64,
                user_samples_memory_mb=64,
                assignable_knobs=4,
                assignable_sliders=0,
                assignable_buttons=4
            )
        }

        self.current_profile = self.profiles['S90']

        # Hardware-specific parameter behaviors
        self._init_hardware_behaviors()

    def _init_hardware_behaviors(self):
        """Initialize hardware-specific parameter behaviors"""

        # AWM filter characteristics (specific to S90/S70)
        self.awm_filter_specs = {
            'low_pass': {
                'slope': -12,  # dB/octave
                'resonance_range': (0.0, 1.0),
                'frequency_range': (10.0, 20000.0),
                'self_oscillation': True
            },
            'high_pass': {
                'slope': -12,
                'resonance_range': (0.0, 0.5),  # Less resonance on HPF
                'frequency_range': (10.0, 5000.0),
                'self_oscillation': False
            },
            'band_pass': {
                'slope': -12,
                'resonance_range': (0.0, 2.0),
                'frequency_range': (100.0, 10000.0),
                'bandwidth_range': (0.1, 5.0)  # octaves
            }
        }

        # AN engine characteristics (S90 only)
        self.an_engine_specs = {
            'oscillators': 2,
            'filters_per_oscillator': 1,
            'envelopes_per_voice': 4,
            'lfo_count': 2,
            'feedback_possible': True,
            'ring_modulation': True,
            'sync_modes': ['soft', 'hard', 'ring'],
            'waveforms': ['sawtooth', 'square', 'triangle', 'sine', 'noise']
        }

        # FDSP engine characteristics
        self.fdsp_specs = {
            'formant_filters': 5,
            'phoneme_slots': 16,
            'breath_control': True,
            'gender_control': True,
            'age_control': True,
            'excitation_types': ['pulse', 'noise', 'mixed']
        }

        # Hardware-specific timing and performance
        self.hardware_timing = {
            'midi_latency_ms': 2.0,      # Hardware MIDI latency
            'voice_allocation_time_us': 50,  # Voice allocation overhead
            'filter_update_rate_hz': 1000,   # Filter coefficient updates
            'envelope_update_rate_hz': 2000, # Envelope updates
            'lfo_update_rate_hz': 1000       # LFO updates
        }

        # Memory management characteristics
        self.memory_specs = {
            'sample_compression_ratio': 0.5,  # Hardware compression
            'voice_stealing_priority': ['oldest', 'quietest', 'lowest'],
            'preset_load_time_ms': 50,       # Time to load preset
            'sample_load_time_ms_per_mb': 10  # Sample loading overhead
        }

    def set_hardware_profile(self, model: str) -> bool:
        """
        Set the current hardware profile.

        Args:
            model: Hardware model ('S70', 'S90', 'S90ES')

        Returns:
            True if profile exists and was set
        """
        if model in self.profiles:
            self.current_profile = self.profiles[model]
            return True
        return False

    def get_hardware_limits(self) -> Dict[str, Any]:
        """Get hardware limits for the current profile"""
        profile = self.current_profile
        return {
            'max_polyphony': profile.polyphony,
            'max_parts': profile.multitimbral_parts,
            'max_awm_voices': profile.awm_voices,
            'max_an_voices': profile.an_polyphony if profile.an_engines > 0 else 0,
            'max_fdsp_voices': profile.fdsp_polyphony,
            'insertion_effects': profile.insertion_effects_per_part,
            'system_effects': profile.system_effects,
            'variation_effects': profile.variation_effects,
            'master_effects': profile.master_effects,
            'user_samples_mb': profile.user_samples_memory_mb,
            'wave_rom_mb': profile.wave_rom_size_mb
        }

    def get_awm_voice_resources(self) -> Dict[str, int]:
        """Get AWM voice resource allocation"""
        return {
            'samples_per_voice': self.current_profile.awm_samples_per_voice,
            'filters_per_voice': self.current_profile.awm_filters_per_voice,
            'envelopes_per_voice': self.current_profile.awm_envelopes_per_voice,
            'lfo_count': 2,  # Standard for AWM
            'modulation_matrix_size': 8  # Simultaneous modulation routings
        }

    def get_an_engine_resources(self) -> Dict[str, Any]:
        """Get AN engine resource allocation (S90 only)"""
        if self.current_profile.an_engines == 0:
            return {'available': False}

        return {
            'available': True,
            'engines': self.current_profile.an_engines,
            'oscillators_per_engine': self.an_engine_specs['oscillators'],
            'filters_per_oscillator': self.an_engine_specs['filters_per_oscillator'],
            'envelopes_per_voice': self.an_engine_specs['envelopes_per_voice'],
            'lfo_count': self.an_engine_specs['lfo_count'],
            'feedback_supported': self.an_engine_specs['feedback_possible'],
            'ring_mod_supported': self.an_engine_specs['ring_modulation'],
            'sync_modes': self.an_engine_specs['sync_modes'],
            'waveforms': self.an_engine_specs['waveforms']
        }

    def get_fdsp_resources(self) -> Dict[str, Any]:
        """Get FDSP engine resource allocation"""
        return {
            'available': True,
            'formant_filters': self.fdsp_specs['formant_filters'],
            'phoneme_slots': self.fdsp_specs['phoneme_slots'],
            'breath_control': self.fdsp_specs['breath_control'],
            'gender_control': self.fdsp_specs['gender_control'],
            'age_control': self.fdsp_specs['age_control'],
            'excitation_types': self.fdsp_specs['excitation_types'],
            'max_polyphony': self.current_profile.fdsp_polyphony
        }

    def get_hardware_timings(self) -> Dict[str, float]:
        """Get hardware-specific timing characteristics"""
        return self.hardware_timing.copy()

    def get_memory_characteristics(self) -> Dict[str, Any]:
        """Get memory management characteristics"""
        return self.memory_specs.copy()

    def apply_hardware_filter_characteristics(self, filter_type: str,
                                            frequency: float, resonance: float) -> Tuple[float, float]:
        """
        Apply hardware-specific filter characteristics.

        Args:
            filter_type: Filter type ('low_pass', 'high_pass', 'band_pass')
            frequency: Base frequency
            resonance: Base resonance

        Returns:
            Tuple of (adjusted_frequency, adjusted_resonance)
        """
        if filter_type not in self.awm_filter_specs:
            return frequency, resonance

        specs = self.awm_filter_specs[filter_type]

        # Clamp frequency to hardware range
        adjusted_freq = max(specs['frequency_range'][0],
                           min(specs['frequency_range'][1], frequency))

        # Apply hardware-specific resonance scaling
        resonance_range = specs['resonance_range']
        adjusted_resonance = resonance * (resonance_range[1] - resonance_range[0]) + resonance_range[0]

        # Special handling for self-oscillation
        if specs.get('self_oscillation', False) and adjusted_resonance > 0.9:
            # Hardware self-oscillation behavior
            adjusted_freq = min(adjusted_freq * 1.1, 20000.0)

        return adjusted_freq, adjusted_resonance

    def get_hardware_compatible_parameter_range(self, parameter_name: str) -> Optional[Tuple[float, float]]:
        """
        Get hardware-compatible parameter range.

        Args:
            parameter_name: Parameter name

        Returns:
            Tuple of (min, max) or None if not hardware-specific
        """
        # Hardware-specific parameter ranges
        ranges = {
            'awm_filter_frequency': (10.0, 20000.0),
            'awm_filter_resonance': (0.0, 1.0),
            'awm_envelope_attack': (0.0, 31.0),  # In hardware units
            'awm_envelope_decay': (0.0, 31.0),
            'awm_envelope_sustain': (0.0, 15.0),
            'awm_envelope_release': (0.0, 31.0),
            'an_oscillator_detune': (-7.0, 7.0),  # Semitones
            'an_filter_cutoff': (0.0, 100.0),    # Hardware units
            'an_filter_resonance': (0.0, 7.0),   # Hardware units
            'fdsp_formant_shift': (0.5, 2.0),    # Ratio
            'fdsp_breath_level': (0.0, 1.0),
            'insertion_effect_send': (0.0, 127.0), # MIDI units
            'system_effect_return': (0.0, 127.0)
        }

        return ranges.get(parameter_name)

    def simulate_hardware_voice_allocation(self, requested_voices: int,
                                         voice_type: str = 'awm') -> int:
        """
        Simulate hardware voice allocation behavior.

        Args:
            requested_voices: Number of voices requested
            voice_type: Type of voices ('awm', 'an', 'fdsp')

        Returns:
            Number of voices actually allocated (may be less due to hardware limits)
        """
        if voice_type == 'awm':
            max_voices = self.current_profile.awm_voices
        elif voice_type == 'an':
            max_voices = self.current_profile.an_polyphony if self.current_profile.an_engines > 0 else 0
        elif voice_type == 'fdsp':
            max_voices = self.current_profile.fdsp_polyphony
        else:
            max_voices = self.current_profile.polyphony

        return min(requested_voices, max_voices)

    def get_hardware_performance_metrics(self) -> Dict[str, Any]:
        """Get hardware performance characteristics"""
        return {
            'model': self.current_profile.model_name,
            'polyphony': self.current_profile.polyphony,
            'multitimbral_parts': self.current_profile.multitimbral_parts,
            'sample_rate': self.current_profile.sample_rate,
            'bit_depth': self.current_profile.bit_depth,
            'awm_voices': self.current_profile.awm_voices,
            'an_engines': self.current_profile.an_engines,
            'fdsp_voices': self.current_profile.fdsp_voices,
            'wave_rom_mb': self.current_profile.wave_rom_size_mb,
            'user_memory_mb': self.current_profile.user_samples_memory_mb,
            'midi_latency_ms': self.hardware_timing['midi_latency_ms'],
            'voice_allocation_us': self.hardware_timing['voice_allocation_time_us']
        }
