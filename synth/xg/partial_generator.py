"""
ULTRA-FAST XG PARTIAL GENERATOR - SIMD-OPTIMIZED BLOCK PROCESSING

High-performance XG-compliant partial generator with vectorized block processing.
Optimized for 100+ concurrent partials at 48000 Hz with 1024-sample blocks.

Key Features:
- SIMD-friendly vectorized waveform generation using Numba JIT compilation
- Block-based envelope processing with zero temporary allocations
- Pre-calculated phase stepping for ultra-fast wavetable synthesis
- Memory pool integration for buffer management
- XG-compliant parameter scaling and modulation
- Support for SF2 loop modes with optimized boundary handling

Performance Targets:
- 100+ concurrent partials at 48000 Hz
- 1024-sample block processing
- Zero allocations during audio generation
- SIMD acceleration for mathematical operations
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import numpy as np
import numba as nb
from numba import jit, float32, int32, boolean

from synth.core.oscillator import XGLFO
from synth.sf2.core.wavetable_manager import WavetableManager
from ..core.envelope import UltraFastADSREnvelope, EnvelopeState
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner
from ..engine.optimized_coefficient_manager import get_global_coefficient_manager

@jit(nopython=True, fastmath=True, cache=True)
def _numba_generate_waveform_block_stereo_time_varying_numpy(
    left_block: np.ndarray, right_block: np.ndarray, left_table: np.ndarray, right_table: np.ndarray,
    table_length: int, phase: float, base_phase_step: float, pitch_mod_block: np.ndarray,
    loop_mode: int, loop_start: int, loop_end: int, block_size: int, loop_direction: int
):
    """
    NUMBA-COMPILED: Time-varying SIMD waveform generation for stereo NumPy arrays (per-plane format).

    Processes stereo sample tables (separate left/right arrays) with time-varying pitch modulation.
    Preserves stereo information from SF2 samples.

    Args:
        left_block: Output left channel buffer (modified in-place)
        right_block: Output right channel buffer (modified in-place)
        left_table: Left channel sample table (numpy array)
        right_table: Right channel sample table (numpy array)
        table_length: Length of sample table
        phase: Current phase position (table index, 0 to table_length-1)
        base_phase_step: Base phase step per sample (samples per sample)
        pitch_mod_block: Time-varying pitch modulation in cents (block_size array)
        loop_mode: SF2 loop mode (0=no loop, 1=forward, 2=backward, 3=alternating)
        loop_start: Loop start index
        loop_end: Loop end index
        block_size: Number of samples to generate
    """
    # For alternating loops, use the passed direction state
    current_loop_direction = loop_direction

    for i in range(block_size):
        # Calculate time-varying phase step with pitch modulation
        pitch_mod_cents = pitch_mod_block[i]
        modulation_mult = 2.0 ** (pitch_mod_cents / 1200.0)
        current_phase_step = base_phase_step * modulation_mult

        # Phase now directly represents table index position
        raw_index = phase

        # Apply SF2 loop wrapping with optimized branching
        if loop_mode > 0 and loop_end > loop_start and loop_end < table_length:
            loop_length = loop_end - loop_start

            if loop_mode == 1:  # Forward loop - most common
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    table_index = loop_start + (excess % loop_length)
                elif raw_index < loop_start:
                    table_index = loop_start
                else:
                    table_index = raw_index

            elif loop_mode == 2:  # Backward loop
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    backward_pos = loop_length - 1 - (excess % loop_length)
                    table_index = loop_start + backward_pos
                elif raw_index < loop_start:
                    table_index = loop_end - 1
                else:
                    table_index = loop_end - 1 - (raw_index - loop_start)

            elif loop_mode == 3:  # Alternating loop (ping-pong)
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    current_loop_direction = -1  # Switch to backward
                    backward_pos = excess % loop_length
                    table_index = loop_end - 1 - backward_pos
                elif raw_index < loop_start:
                    excess = loop_start - raw_index
                    current_loop_direction = 1  # Switch to forward
                    table_index = loop_start + (excess % loop_length)
                else:
                    if current_loop_direction > 0:  # Forward
                        table_index = raw_index
                    else:  # Backward
                        table_index = loop_end - 1 - (raw_index - loop_start)
            else:
                table_index = raw_index
        else:
            table_index = raw_index

        # SIMD-friendly bounds checking and interpolation - ensure valid range
        table_index = max(0.0, min(float(table_length - 1), table_index))
        index_int = int(table_index)
        frac = table_index - index_int

        # Get stereo samples with bounds checking from separate arrays
        left1, right1 = 0.0, 0.0
        left2, right2 = 0.0, 0.0

        # Bounds check indices to prevent out-of-bounds access
        if 0 <= index_int < table_length:
            left1 = left_table[index_int]
            right1 = right_table[index_int]

            next_index = index_int + 1
            if next_index < table_length:
                left2 = left_table[next_index]
                right2 = right_table[next_index]
            else:
                # If at end of table, duplicate last sample to avoid discontinuities
                left2 = left1
                right2 = right1
        else:
            # If somehow index is out of bounds, use first sample
            left1 = left_table[0] if table_length > 0 else 0.0
            right1 = right_table[0] if table_length > 0 else 0.0
            left2 = left1
            right2 = right1

        # Linear interpolation for both channels - SIMD friendly
        left_interp = left1 + frac * (left2 - left1)
        right_interp = right1 + frac * (right2 - right1)

        left_block[i] = left_interp
        right_block[i] = right_interp

        # Update phase with proper wrapping
        phase += current_phase_step

        # Handle table wrapping (no more 2*Pi normalization)
        if phase >= table_length and table_length > 0:
            phase = phase - table_length
        elif phase < 0:
            phase = phase + table_length

    return phase, current_loop_direction


@jit(nopython=True, fastmath=True, cache=True)
def _numba_apply_time_varying_filter(
    left_block, right_block, filter_cutoff_block, filter_resonance,
    block_size, sample_rate
):
    """
    NUMBA-COMPILED: Apply time-varying filter with per-sample cutoff modulation.

    Args:
        left_block: Left channel buffer (modified in-place)
        right_block: Right channel buffer (modified in-place)
        filter_cutoff_block: Time-varying cutoff frequencies (block_size array)
        filter_resonance: Filter resonance (constant)
        block_size: Number of samples to process
        sample_rate: Audio sample rate
    """
    # Simple time-varying low-pass filter implementation
    # This is a simplified version - in production you'd want a more sophisticated filter
    prev_left = 0.0
    prev_right = 0.0

    for i in range(block_size):
        cutoff = filter_cutoff_block[i]
        # Clamp cutoff frequency
        cutoff = max(20.0, min(cutoff, sample_rate * 0.4))

        # Calculate filter coefficients (simplified bilinear transform)
        # This is a basic implementation - production code would use more sophisticated filtering
        wc = 2.0 * math.pi * cutoff / sample_rate
        k = wc / (wc + 1.0)  # Simplified coefficient

        # Apply resonance
        resonance_factor = 1.0 + filter_resonance * 0.5

        # Apply filter to both channels
        filtered_left = k * left_block[i] + (1.0 - k) * prev_left
        filtered_right = k * right_block[i] + (1.0 - k) * prev_right

        # Apply resonance feedback
        filtered_left *= resonance_factor
        filtered_right *= resonance_factor

        # Store filtered values
        left_block[i] = filtered_left
        right_block[i] = filtered_right

        # Update previous values
        prev_left = filtered_left
        prev_right = filtered_right


@jit(nopython=True, fastmath=True, cache=True)
def _numba_generate_waveform_block_mono_time_varying_numpy(
    left_block: np.ndarray, right_block: np.ndarray, sample_table: np.ndarray,
    table_length: int, phase: float, base_phase_step: float, pitch_mod_block: np.ndarray,
    loop_mode: int, loop_start: int, loop_end: int, block_size: int, loop_direction: int
):
    """
    NUMBA-COMPILED: Time-varying SIMD waveform generation for mono NumPy arrays.

    Processes mono sample tables (NumPy float32 arrays) with time-varying pitch modulation.
    Supports SF2 loop handling with per-sample pitch modulation.

    Args:
        left_block: Output left channel buffer (modified in-place)
        right_block: Output right channel buffer (modified in-place)
        sample_table: NumPy float32 array of mono samples
        table_length: Length of sample table
        phase: Current phase position (table index, 0 to table_length-1)
        base_phase_step: Base phase step per sample (samples per sample)
        pitch_mod_block: Time-varying pitch modulation in cents (block_size array)
        loop_mode: SF2 loop mode (0=no loop, 1=forward, 2=backward, 3=alternating)
        loop_start: Loop start index
        loop_end: Loop end index
        block_size: Number of samples to generate
    """
    # For alternating loops, use the passed direction state
    current_loop_direction = loop_direction

    for i in range(block_size):
        # Calculate time-varying phase step with pitch modulation
        pitch_mod_cents = pitch_mod_block[i]
        modulation_mult = 2.0 ** (pitch_mod_cents / 1200.0)
        current_phase_step = base_phase_step * modulation_mult

        # Phase now directly represents table index position
        raw_index = phase

        # Apply SF2 loop wrapping with optimized branching
        if loop_mode > 0 and loop_end > loop_start:
            loop_length = loop_end - loop_start

            if loop_mode == 1:  # Forward loop - most common
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    table_index = loop_start + (excess % loop_length)
                elif raw_index < loop_start:
                    table_index = loop_start
                else:
                    table_index = raw_index

            elif loop_mode == 2:  # Backward loop
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    backward_pos = loop_length - (excess % loop_length)
                    table_index = loop_start + backward_pos
                elif raw_index < loop_start:
                    table_index = loop_end - 1
                else:
                    table_index = loop_end - (raw_index - loop_start)

            elif loop_mode == 3:  # Alternating loop (ping-pong)
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    current_loop_direction = -1  # Switch to backward
                    backward_pos = excess % loop_length
                    table_index = loop_end - backward_pos
                elif raw_index < loop_start:
                    excess = loop_start - raw_index
                    current_loop_direction = 1  # Switch to forward
                    table_index = loop_start + (excess % loop_length)
                else:
                    if current_loop_direction > 0:  # Forward
                        table_index = raw_index
                    else:  # Backward
                        table_index = loop_end - (raw_index - loop_start)
            else:
                table_index = raw_index
        else:
            table_index = raw_index

        # SIMD-friendly bounds checking and interpolation
        table_index = max(0.0, min(table_index, table_length - 1))
        index_int = int(table_index)
        frac = table_index - index_int

        # Get mono samples with bounds checking
        mono1 = 0.0
        mono2 = 0.0

        if index_int < table_length:
            mono1 = sample_table[index_int]
            mono2 = sample_table[min(index_int + 1, table_length - 1)]

        # Linear interpolation - SIMD friendly
        mono_interp = mono1 + frac * (mono2 - mono1)

        # Expand mono to stereo
        left_block[i] = mono_interp
        right_block[i] = mono_interp

        # Update phase with proper wrapping
        phase += current_phase_step

        # Handle table wrapping (no more 2*Pi normalization)
        if phase >= table_length:
            phase -= table_length
        elif phase < 0:
            phase += table_length

    return phase, current_loop_direction


@jit(nopython=True, fastmath=True, cache=True)
def _numba_apply_envelope_and_modulation(
    left_block, right_block, amp_env_block, level, amp_mod,
    crossfade_factor, pan_left, pan_right, block_size
):
    """
    NUMBA-COMPILED: Apply envelope, level, crossfade, and panning in SIMD fashion.

    Args:
        left_block: Left channel buffer (modified in-place)
        right_block: Right channel buffer (modified in-place)
        amp_env_block: Amplitude envelope values
        level: Partial level scaling
        amp_mod: Amplitude modulation
        crossfade_factor: Crossfade coefficient
        pan_left: Left pan gain
        pan_right: Right pan gain
        block_size: Number of samples to process
    """
    # SIMD vectorized operations for entire block
    for i in range(block_size):
        # Apply envelope, level, and modulation
        env_level = amp_env_block[i] * level * amp_mod

        # Apply crossfade
        final_level = env_level * crossfade_factor

        # Apply panning
        left_block[i] *= final_level * pan_left
        right_block[i] *= final_level * pan_right


class XGPartialGenerator:
    """
    XG-compliant partial generator implementing XG Partial Structure concept.
    Supports up to 8 partials per program with proper XG parameter mappings.

    XG Specification Compliance:
    - Up to 8 partial structures per program (extended from XG standard 4)
    - Exclusive note ranges per partial (no overlap)
    - Independent envelopes, filters, and modulation per partial
    - Proper XG controller parameter mappings (71-78)
    - XG-compliant envelope curves and scaling
    """

    # XG Standard Constants
    MAX_PARTIALS = 8  # Extended from XG standard of 4
    PITCH_BEND_CENTS = 1200  # XG pitch bend range in cents
    VELOCITY_SENSE_SCALING = 0.023  # XG velocity sensitivity formula

    def _set_partial_parameters(self, partial_params: Dict, is_drum: bool):
        """Set XG partial parameters from configuration dictionary.

        This method contains the common parameter setting logic used by both
        __init__() and _reconfigure() methods to eliminate code duplication.

        Args:
            partial_params: XG partial parameters dictionary
            is_drum: True for drum mode (affects envelope/filter behavior)
        """
        # XG Core Partial Parameters
        self.element_type = partial_params.get("element_type", "normal")  # normal, drum, sfx
        self.level = partial_params.get("level", 1.0)  # 0.0-2.0
        self.pan = partial_params.get("pan", 0.5)  # 0.0-1.0

        # Key Range - Exclusive per XG specification
        self.key_range_low = partial_params.get("key_range_low", 0)
        self.key_range_high = partial_params.get("key_range_high", 127)
        self.velocity_range_low = partial_params.get("velocity_range_low", 0)
        self.velocity_range_high = partial_params.get("velocity_range_high", 127)

        # Crossfade settings for smooth partial transitions
        self.crossfade_note_width = partial_params.get("crossfade_note", 0)
        self.crossfade_vel_width = partial_params.get("crossfade_velocity", 0)

        # Key scaling and velocity sensitivity (XG-compliant)
        self.key_scaling = partial_params.get("key_scaling", 0.0)  # -100 to 100 cents/key
        self.velocity_sense = partial_params.get("velocity_sense", 1.0)  # XG velocity formula

        # XG Scale tuning and octave settings
        self.scale_tuning = partial_params.get("scale_tuning", 100)  # cents
        self.coarse_tune = partial_params.get("coarse_tune", 0)  # semitones
        self.fine_tune = partial_params.get("fine_tune", 0)  # cents
        self.overriding_root_key = partial_params.get("overriding_root_key", -1)

        # XG Envelope parameters with proper scaling
        self.amp_attack_time = partial_params.get("amp_attack", 0.01)
        self.amp_decay_time = partial_params.get("amp_decay", 0.3)
        self.amp_sustain_level = partial_params.get("amp_sustain", 0.7)
        self.amp_release_time = partial_params.get("amp_release", 0.5)
        self.amp_delay_time = partial_params.get("amp_delay", 0.0)
        self.amp_hold_time = partial_params.get("amp_hold", 0.0)

        # XG Filter envelope - can be disabled for drums
        self.use_filter_env = not is_drum or partial_params.get("use_filter_env", True)
        if self.use_filter_env:
            self.filter_attack_time = partial_params.get("filter_attack", 0.1)
            self.filter_decay_time = partial_params.get("filter_decay", 0.5)
            self.filter_sustain_level = partial_params.get("filter_sustain", 0.6)
            self.filter_release_time = partial_params.get("filter_release", 0.8)
            self.filter_delay_time = partial_params.get("filter_delay", 0.0)
            self.filter_hold_time = partial_params.get("filter_hold", 0.0)

        # XG Pitch envelope - can be disabled for drums
        self.use_pitch_env = not is_drum or partial_params.get("use_pitch_env", True)
        if self.use_pitch_env:
            self.pitch_attack_time = partial_params.get("pitch_attack", 0.05)
            self.pitch_decay_time = partial_params.get("pitch_decay", 0.1)
            self.pitch_sustain_level = partial_params.get("pitch_sustain", 0.0)  # Fixed for XG
            self.pitch_release_time = partial_params.get("pitch_release", 0.05)
            self.pitch_delay_time = partial_params.get("pitch_delay", 0.0)
            self.pitch_hold_time = partial_params.get("pitch_hold", 0.0)

        # XG Filter parameters
        filter_config = partial_params.get("filter", {})
        self.filter_cutoff = filter_config.get("cutoff", 1000.0)
        self.filter_resonance = filter_config.get("resonance", 0.7)
        self.filter_type = filter_config.get("type", "lowpass")
        self.filter_key_follow = filter_config.get("key_follow", 0.5)

    def __init__(self, synth, note: int, velocity: int, program: int,
                  partial_id: int, partial_params: Dict, is_drum: bool = False,
                  sample_rate: int = 44100, bank: int = 0):
        """
        XG-compliant partial generator initialization.

        Args:
            wavetable: XG wavetable manager for sample access
            note: MIDI note number (0-127)
            velocity: Velocity value (0-127)
            program: Program number (can be extended for drum kits)
            partial_id: Partial identifier (0-7 for up to 8 partials)
            partial_params: XG partial parameters dictionary
            is_drum: True for drum mode (affects envelope/filter behavior)
            sample_rate: Audio sample rate
            bank: Bank number (MSB 0-127)
        """
        self.synth = synth
        self.wavetable: Optional[WavetableManager] = synth.sf2_manager.get_manager()
        self.partial_id = partial_id
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.sample_rate = sample_rate
        self.active = True

        # Set XG partial parameters using shared method
        self._set_partial_parameters(partial_params, is_drum)

        # SF2 Loop information (initialized later when sample is loaded)
        self.sample_start = 0
        self.sample_end = 0
        self.loop_start = 0
        self.loop_end = 0
        self.loop_mode = 0  # 0=no loop, 1=forward, 2=backward, 3=alternating

        # Loop state for alternating loops
        self.loop_direction = 1  # 1=forward, -1=backward (for alternating loops)
        self.loop_position = 0.0  # Current position within loop

        # Pre-calculated loop parameters for optimization
        self.loop_length = 0.0
        self.loop_start_reciprocal = 0.0
        self.loop_length_reciprocal = 0.0
        self.has_loop = False

        # Optimized coefficient manager for performance
        self.coeff_manager = get_global_coefficient_manager()

        self._cached_sample_table = None
        self._load_sample_table_once()
        # Update loop parameters when loop info is loaded
        self._update_loop_parameters()

        # Initialize sample table position and advance parameters
        self.sample_position = 0.0
        self.sample_advance_step = self._calculate_sample_advance_step()

        # Initialize XG-compliant envelopes
        self._initialize_envelopes(partial_params)

        # Initialize XG filter
        self._initialize_filter()

        # Start envelopes (Per XG, envelopes start on note-on)
        self.note_on(velocity, note)

        self.dedicated_lfos = []
        for i in range(3):  # 3 LFOs per partial: pitch, filter, amplitude
            lfo = self.synth.partial_lfo_pool.acquire_oscillator(
                id=self.partial_id * 3 + i,  # Unique ID per partial+LFO
                waveform="sine",
                rate=5.0,
                depth=0.5,
                delay=0.0
            )
            # Configure LFO modulation routing
            if i == 0:  # LFO1: Pitch modulation (vibrato)
                lfo.set_modulation_routing(pitch=True, filter=False, amplitude=False)
                lfo.set_modulation_depths(pitch_cents=50.0, filter_depth=0.0, amplitude_depth=0.0)
            elif i == 1:  # LFO2: Filter modulation
                lfo.set_modulation_routing(pitch=False, filter=True, amplitude=False)
                lfo.set_modulation_depths(pitch_cents=0.0, filter_depth=0.3, amplitude_depth=0.0)
            else:  # LFO3: Amplitude modulation (tremolo)
                lfo.set_modulation_routing(pitch=False, filter=False, amplitude=True)
                lfo.set_modulation_depths(pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3)
            self.dedicated_lfos.append(lfo)

        # Crossfade tracking
        self.velocity_crossfade = 0.0
        self.note_crossfade = 0.0

        # XG Modulation cache
        self.last_pitch_mod = 0.0
        self.last_filter_mod = 0.0
        self.last_amp_mod = 1.0  # Default to 1.0 (no modulation)

    def _update_loop_parameters(self):
        """Pre-calculate optimized loop parameters for performance."""
        if self.loop_mode > 0 and self.loop_end > self.loop_start:
            self.loop_length = self.loop_end - self.loop_start
            self.loop_start_reciprocal = 1.0 / self.loop_start if self.loop_start != 0 else 0.0
            self.loop_length_reciprocal = 1.0 / self.loop_length if self.loop_length != 0 else 0.0
            self.has_loop = True
        else:
            self.loop_length = 0.0
            self.loop_start_reciprocal = 0.0
            self.loop_length_reciprocal = 0.0
            self.has_loop = False

    def _calculate_base_frequency(self) -> float:
        """
        Calculate the base frequency for this partial based on SF2/XG specifications.

        This includes:
        1. The target note to be played (MIDI note number)
        2. XG scale tuning (100 cents = 1 semitone)
        3. XG coarse/fine tuning
        4. XG key scaling (note-dependent pitch variation)
        5. Root key override (if specified)

        Returns:
            Base frequency in Hz
        """
        # Start with the root key (MIDI note number)
        target_note = self.overriding_root_key if self.overriding_root_key >= 0 else self.note

        # Calculate base frequency from the target note
        base_freq = 440.0 * (2.0 ** ((target_note - 69) / 12.0))

        # Apply XG scale tuning (100 cents per semitone by default)
        if self.scale_tuning != 100:
            scale_tuning_cents = self.scale_tuning - 100  # Relative to 100 cents/semitone
            base_freq *= 2.0 ** (scale_tuning_cents / 1200.0)

        # Apply XG coarse tuning (semitones)
        if self.coarse_tune != 0:
            base_freq *= 2.0 ** (self.coarse_tune / 12.0)

        # Apply XG fine tuning (cents)
        if self.fine_tune != 0:
            base_freq *= 2.0 ** (self.fine_tune / 1200.0)

        # Apply XG key scaling (note-dependent pitch variation)
        if self.key_scaling != 0.0:
            # XG formula: pitch varies linearly with note from center (note 60)
            # key_scaling is in cents per key
            key_offset_cents = (self.note - 60) * self.key_scaling
            base_freq *= 2.0 ** (key_offset_cents / 1200.0)

        return base_freq

    def _get_sample_header(self):
        """
        Get the SF2 sample header for this partial.

        Returns:
            SF2SampleHeader object or None if not available
        """
        if not self.wavetable:
            return None

        # Get sample header from wavetable manager
        cache_key = f'{self.bank}-{self.program}-{self.note}-{self.velocity}-{self.partial_id}'
        header, soundfont_obj, valid = getattr(self.wavetable, 'partial_map', {}).get(cache_key, (None, None, False))

        return header if valid else None

    def _calculate_sample_advance_step(self) -> float:
        """
        Calculate the base sample advance step for wavetable playback.

        The sample advance step represents how many source sample indices to advance per output sample.
        For proper wavetable synthesis, this depends on:

        1. The target frequency (from _calculate_base_frequency)
        2. The original sample frequency (from sample header original_pitch)
        3. The original sample's sample rate (from sample header)
        4. The rendering sample rate

        The sample advance step accounts for:
        - Pitch change from original sample pitch to target pitch
        - Sample rate differences between original and rendering rate

        Returns:
            Sample advance step in source sample indices per output sample
        """
        # Get target frequency (what we want to achieve)
        target_freq = self._calculate_base_frequency()

        # Get the original sample's properties from the header
        sample_header = self._get_sample_header()
        if sample_header:
            original_pitch = sample_header.original_pitch
            pitch_correction_cents = sample_header.pitch_correction
            original_sample_rate = sample_header.sample_rate
        else:
            # Fallback values
            original_pitch = self.note  # Use current note as fallback
            pitch_correction_cents = 0
            original_sample_rate = 44100  # Default sample rate

        # Calculate the original frequency of the sample (as it was recorded)
        original_freq = 440.0 * (2.0 ** ((original_pitch - 69) / 12.0))
        
        # Apply pitch correction if present
        if pitch_correction_cents != 0:
            original_freq *= 2.0 ** (pitch_correction_cents / 1200.0)

        # Calculate the frequency ratio: how much faster/slower we want to play
        frequency_ratio = target_freq / original_freq if original_freq != 0 else 1.0

        # Calculate the sample rate ratio: account for original vs rendering sample rate
        sample_rate_ratio = original_sample_rate / self.sample_rate

        # Calculate the final phase step
        # This properly accounts for both the desired pitch change and sample rate differences
        phase_step = frequency_ratio * sample_rate_ratio #* table_length

        return phase_step

    EMPTY_SAMPLE = np.zeros(1)

    def _load_sample_table_once(self):
        """Load sample table once during construction (XG partials never change sample table)."""
        if not self.wavetable:
            return

        # Get sample table from wavetable manager (only called once)
        sample_table = self.wavetable.get_partial_table(
            self.note, self.program, self.partial_id,
            self.velocity, self.bank
        )

        # Handle NumPy arrays returned by updated SampleParser
        if sample_table is not None:
            if isinstance(sample_table, tuple):
                # Stereo samples - tuple of (left_array, right_array)
                self._cached_sample_table = sample_table
                self._sample_format_is_stereo = True
            elif isinstance(sample_table, np.ndarray):
                # Mono samples - single numpy array
                self._cached_sample_table = sample_table
                self._sample_format_is_stereo = False
        else:
            # Empty or None sample table
            self._cached_sample_table = XGPartialGenerator.EMPTY_SAMPLE
            self._sample_format_is_stereo = False

        # Load loop information when sample table is loaded
        self._load_sample_loop_info()

    def _load_sample_loop_info(self):
        """Load loop information from SF2 sample header."""
        if not self.wavetable:
            return

        # Access the cached sample header from wavetable manager
        cache_key = f'{self.bank}-{self.program}-{self.note}-{self.velocity}-{self.partial_id}'
        header, soundfont_obj, valid = getattr(self.wavetable, 'partial_map', {}).get(cache_key, (None, None, False))

        if header and valid:
            # Store sample boundaries (absolute indices in original file)
            self.sample_start = header.start
            self.sample_end = header.end

            # Convert absolute loop indices to relative indices in trimmed array
            # SF2 loop points are absolute indices, but sample data is trimmed to [start:end]
            loop_start_rel = header.start_loop - header.start
            loop_end_rel = header.end_loop - header.start

            # Store relative loop indices for use with trimmed sample arrays
            self.loop_start = max(0, loop_start_rel)  # Ensure non-negative
            self.loop_end = max(self.loop_start + 1, loop_end_rel)  # Ensure valid range

            # Determine loop mode from SF2 sample type
            # SF2 sample types: 0=no loop, 1=forward, 2=backward+forward, 3=backward
            sample_type = header.type & 3  # Lower 2 bits contain loop type
            if sample_type == 1:
                self.loop_mode = 1  # Forward loop
            elif sample_type == 2:
                self.loop_mode = 3  # Alternating (backward then forward)
            elif sample_type == 3:
                self.loop_mode = 2  # Backward loop
            else:
                self.loop_mode = 0  # No loop

            # Get the actual sample table length to validate loop points
            if self._cached_sample_table is not None:
                if isinstance(self._cached_sample_table, tuple):
                    # Stereo sample: use left channel length
                    table_length = len(self._cached_sample_table[0])
                else:
                    # Mono sample
                    table_length = len(self._cached_sample_table)

                # Validate loop points are within sample bounds
                if self.loop_mode > 0:
                    self.loop_start = max(0, min(self.loop_start, table_length - 1))
                    self.loop_end = max(self.loop_start + 1, min(self.loop_end, table_length))

                    # Disable loop if validation fails (loop points out of bounds)
                    if self.loop_start >= self.loop_end or self.loop_end > table_length:
                        self.loop_mode = 0
        else:
            # No loop information available
            self.loop_mode = 0

    def _initialize_envelopes(self, partial_params: Dict):
        """Initialize XG-compliant envelopes with proper parameter scaling."""
        # XG Amplitude Envelope - always present - use envelope pool
        self.amp_envelope = self.synth.envelope_pool.acquire_envelope(
            delay=self.amp_delay_time,
            attack=self.amp_attack_time,
            hold=self.amp_hold_time,
            decay=self.amp_decay_time,
            sustain=self.amp_sustain_level,
            release=self.amp_release_time,
            velocity_sense=self._calculate_velocity_sense(),  # XG formula
            key_scaling=0.0  # XG envelope key scaling handled separately
        )
        self.amp_buffer = self.synth.memory_pool.get_mono_buffer()
        self.work_buffer = self.synth.memory_pool.get_mono_buffer()
        self.acc_buffer = self.synth.memory_pool.get_mono_buffer()
        self.item_buffer = self.synth.memory_pool.get_mono_buffer()

        # XG Filter Envelope - optional for drums - use envelope pool
        if self.use_filter_env:
            self.filter_envelope = self.synth.envelope_pool.acquire_envelope(
                delay=self.filter_delay_time,
                attack=self.filter_attack_time,
                hold=self.filter_hold_time,
                decay=self.filter_decay_time,
                sustain=self.filter_sustain_level,
                release=self.filter_release_time,
                velocity_sense=0.0,  # XG filter env typically not velocity-sensitive
                key_scaling=0.0
            )
            self.filter_buffer = self.synth.memory_pool.get_mono_buffer()
        else:
            self.filter_envelope = None
            self.filter_buffer = None

        # XG Pitch Envelope - optional for drums - use envelope pool
        if self.use_pitch_env:
            self.pitch_envelope = self.synth.envelope_pool.acquire_envelope(
                delay=self.pitch_delay_time,
                attack=self.pitch_attack_time,
                hold=self.pitch_hold_time,
                decay=self.pitch_decay_time,
                sustain=self.pitch_sustain_level,  # Fixed level per XG
                release=self.pitch_release_time,
                velocity_sense=0.0,  # XG pitch env typically not velocity-sensitive
                key_scaling=0.0
            )
            self.pitch_buffer = self.synth.memory_pool.get_mono_buffer()
        else:
            self.pitch_envelope = None
            self.pitch_buffer = None

    def _initialize_filter(self):
        """Initialize XG-compliant filter."""
        self.filter = self.synth.filter_pool.acquire_filter(
            cutoff=self.filter_cutoff,
            resonance=self.filter_resonance,
            filter_type=self.filter_type,
            key_follow=self.filter_key_follow,
            stereo_width=1.0  # Enable stereo processing for partials
        )

    def _calculate_velocity_sense(self) -> float:
        """Calculate XG velocity sensitivity using standard formula."""
        # XG Velocity Sensitivity = (velocity_sense_param * 127 / 2000) + 0.007
        return (self.velocity_sense * 127.0 / 2000.0) + 0.007

    def note_on(self, velocity: int, note: int):
        """Handle XG note-on event."""
        if not self.active:
            return

        # Reset loop state for alternating loops
        self.loop_direction = 1  # Start with forward direction
        self.loop_position = 0.0

        # Calculate XG velocity scaling
        vel_normalized = velocity / 127.0
        velocity_factor = 1.0 - (1.0 - vel_normalized) * (1.0 - self.velocity_sense)

        # Start XG envelopes
        self.amp_envelope.note_on(velocity, note)
        if self.filter_envelope:
            self.filter_envelope.note_on(velocity, note)
        if self.pitch_envelope:
            self.pitch_envelope.note_on(velocity, note)

    def note_off(self):
        """Handle XG note-off event."""
        if not self.active:
            return

        # Release XG envelopes
        self.amp_envelope.note_off()
        if self.filter_envelope:
            self.filter_envelope.note_off()
        if self.pitch_envelope:
            self.pitch_envelope.note_off()

    def is_active(self) -> bool:
        """Check if XG partial is still active."""
        return (self.active and
                self.amp_envelope and
                self.amp_envelope.state != EnvelopeState.IDLE)

    def generate_sample_block(self, block_size: int, left_block: np.ndarray, right_block: np.ndarray, lfos: List[XGLFO],
                              global_pitch_mod: float = 0.0,
                              velocity_crossfade: float = 0.0,
                              note_crossfade: float = 0.0) -> None:
        """
        Generate XG partial audio block with FULL time-varying modulation processing.

        This method implements proper XG-compliant time-varying modulation within blocks,
        including per-channel and per-note LFO processing, maintaining the same audio
        quality as per-sample processing while achieving high performance through vectorized operations.

        Args:
            left_block: Pre-allocated array to fill with left channel samples
            right_block: Pre-allocated array to fill with right channel samples
            lfos: Channel-level LFO sources (per XG architecture)
            global_pitch_mod: Global pitch modulation (pitch bend, etc.)
            velocity_crossfade: Velocity crossfade coefficient
            note_crossfade: Note crossfade coefficient
        """
        if not self.is_active():
            left_block[:block_size].fill(0.0)
            right_block[:block_size].fill(0.0)
            return

        # Update crossfade coefficients
        self.velocity_crossfade = velocity_crossfade
        self.note_crossfade = note_crossfade

        # Generate envelope blocks with XG key follow
        amp_env_block = self.amp_envelope.generate_block(self.amp_buffer, block_size)
        key_follow_factor = self._calculate_key_follow_factor()
        amp_env_block[:block_size] *= key_follow_factor

        # Generate time-varying pitch modulation block (includes LFO modulation)
        self.work_buffer[:block_size].fill(global_pitch_mod + self.last_pitch_mod)

        if self.use_pitch_env and self.pitch_envelope:
            pitch_env_block = self.pitch_envelope.generate_block(self.pitch_buffer, block_size)
            pitch_env_processed = self._process_pitch_envelope_block(pitch_env_block, block_size)
            self.work_buffer[:block_size] += pitch_env_processed[:block_size]

        # Add LFO modulation to pitch (time-varying within block)
        if lfos:
            lfo_pitch_block = self._generate_lfo_pitch_modulation_block(lfos, block_size)
            self.work_buffer[:block_size] += lfo_pitch_block[:block_size]

        # Generate base waveform with TIME-VARYING pitch modulation
        self._generate_waveform_block_time_varying(left_block, right_block, self.work_buffer)

        # Apply XG filter with TIME-VARYING envelope modulation
        if self.filter and self.use_filter_env and self.filter_envelope:
            filter_env_block = self.filter_envelope.generate_block(self.filter_buffer, block_size)
            # XG Filter envelope to cutoff modulation (±4800 cents range typically)
            self.work_buffer[:block_size] = filter_env_block[:block_size] * 4800.0 * self.last_filter_mod

            # Add LFO modulation to filter cutoff (time-varying within block)
            if lfos:
                lfo_filter_block = self._generate_lfo_filter_modulation_block(lfos, block_size)
                self.work_buffer[:block_size] += lfo_filter_block[:block_size] * 4800.0  # Convert to cents

            filter_cutoff_freq_block = self._calculate_xg_filter_cutoff_block(self.work_buffer)

            # Apply TIME-VARYING filter processing
            _numba_apply_time_varying_filter(
                left_block, right_block, filter_cutoff_freq_block,
                self.filter_resonance, block_size, self.sample_rate
            )

        # Generate time-varying amplitude modulation (LFO tremolo)
        self.work_buffer[:block_size].fill(self.last_amp_mod)
        if lfos:
            lfo_amp_block = self._generate_lfo_amplitude_modulation_block(lfos, block_size)
            self.work_buffer[:block_size] *= lfo_amp_block[:block_size]

        # Apply envelope, level, crossfade, and panning using Numba-compiled SIMD operations
        crossfade_factor = (1.0 - self.velocity_crossfade) * (1.0 - self.note_crossfade)

        # Get pre-computed panning coefficients
        pan_int = int(self.pan * 127.0)
        pan_int = max(0, min(127, pan_int))
        pan_left, pan_right = self.coeff_manager.get_pan_gains(pan_int)

        # Use Numba-compiled function for ultra-fast SIMD processing
        _numba_apply_envelope_and_modulation(
            left_block, right_block, self.work_buffer,
            float(self.level), 1.0,  # amp_mod_block is already applied above
            crossfade_factor, pan_left, pan_right, block_size
        )

    def _calculate_key_follow_factor(self) -> float:
        """Calculate XG envelope key follow factor."""
        # XG standard: envelopes vary by ±88.02 cents over 10 octaves
        # Simplified implementation: linear variation from note 21 to 108
        key_follow_range = 1.059463  # 2^(88.02/1200) ≈ 1.0595
        center_note = 60
        note_distance = abs(self.note - center_note)

        if note_distance == 0:
            return 1.0

        # Use manual log calculation to avoid expensive math.log2
        # log2(x) = ln(x) / ln(2), but since we're using 2**exponent, we can precompute
        log_factor = 0.073637  # approximately ln(1.059463) / ln(2) = 0.073637
        exponent = (note_distance / (108 - 21)) * log_factor
        result = math.exp(exponent * math.log(2.0))  # Use natural log for better performance
        
        return result if self.note < center_note else 1.0 / result

    def _calculate_xg_filter_cutoff(self, env_mod_cents: float) -> float:
        """Calculate XG filter cutoff with envelope modulation."""
        base_freq = self.filter_cutoff

        # Apply key follow per XG formula: ±24 semitones range
        key_follow_semitones = (self.note - 60) * self.filter_key_follow
        key_follow_mult = 2.0 ** (key_follow_semitones / 12.0)

        # Apply envelope modulation
        env_mult = 2.0 ** (env_mod_cents / 1200.0)

        final_freq = base_freq * key_follow_mult * env_mult

        # XG-compliant frequency clamping
        return max(20.0, min(20000.0, final_freq))

    def _process_pitch_envelope_block(self, pitch_env_block: np.ndarray, block_size: int) -> np.ndarray:
        """Process XG pitch envelope for block (fixed sustain level)."""
        if self.pitch_envelope and self.pitch_envelope.state == EnvelopeState.SUSTAIN:
            # Fixed sustain per XG spec
            pitch_env_block[:block_size].fill(0.0)
        else:
            pitch_env_block[:block_size] *= 1200.0
        return pitch_env_block

    def _generate_waveform_block_time_varying(self, left_block: np.ndarray, right_block: np.ndarray,
                                             pitch_mod_block: np.ndarray) -> None:
        """Generate entire sample block with TIME-VARYING pitch modulation.

        This method implements proper XG-compliant time-varying pitch modulation within blocks,
        maintaining the same audio quality as per-sample processing.

        Args:
            left_block: Pre-allocated array to fill with left channel samples
            right_block: Pre-allocated array to fill with right channel samples
            pitch_mod_block: Time-varying pitch modulation in cents (block_size array)
        """
        block_size = len(left_block)

        # Generate sample based on wavetable availability
        if self.wavetable is None:
            # Zero sample fallback - arrays are already zeroed
            return

        # XG Wavetable synthesis - use cached sample table
        sample_table = self._cached_sample_table

        if sample_table is None or len(sample_table) == 0:
            return

        table_length = len(sample_table)

        # Use cached sample format detection for zero-overhead format selection
        if self._sample_format_is_stereo:
            # Stereo samples - extract left and right arrays from the combined array
            left_table, right_table = sample_table
            # Stereo samples - use time-varying stereo Numba function
            self.sample_position, self.loop_direction = _numba_generate_waveform_block_stereo_time_varying_numpy(
                left_block, right_block, left_table, right_table, table_length,
                self.sample_position, self.sample_advance_step, pitch_mod_block, self.loop_mode,
                self.loop_start, self.loop_end, block_size, self.loop_direction
            )
        else:
            # Mono samples - use time-varying mono Numba function (expands to stereo)
            self.sample_position, self.loop_direction = _numba_generate_waveform_block_mono_time_varying_numpy(
                left_block, right_block, sample_table, table_length,
                self.sample_position, self.sample_advance_step, pitch_mod_block, self.loop_mode,
                self.loop_start, self.loop_end, block_size, self.loop_direction
            )

    def _generate_lfo_pitch_modulation_block(self, lfos: List[XGLFO], block_size: int) -> np.ndarray:
        """Generate time-varying LFO pitch modulation block for XG compliance.

        CRITICAL FIX: Use dedicated partial LFOs instead of shared channel LFOs to avoid contention.

        Args:
            lfos: List of channel-level LFO objects (ignored - using dedicated LFOs)
            block_size: Number of samples in the block

        Returns:
            Array of pitch modulation values in cents
        """
        if not hasattr(self, 'dedicated_lfos') or len(self.dedicated_lfos) == 0:
            # Fallback to zero if no dedicated LFOs
            return np.zeros(block_size, dtype=np.float32)
            
        pitch_mod_block = self.acc_buffer
        if pitch_mod_block is None:
            return np.zeros(block_size, dtype=np.float32)
        pitch_mod_block[:block_size].fill(0.0)

        # Use dedicated LFO for pitch modulation (LFO1)
        if len(self.dedicated_lfos) > 0:
            lfo = self.dedicated_lfos[0]  # Dedicated pitch LFO
            if lfo and hasattr(lfo, 'generate_block'):
                lfo_block = lfo.generate_block(self.item_buffer, block_size)
                if lfo_block is not None and len(lfo_block) >= block_size:
                    pitch_mod_block[:block_size] += lfo_block[:block_size] * lfo.pitch_depth_cents

        return pitch_mod_block

    def _generate_lfo_filter_modulation_block(self, lfos: List[XGLFO], block_size: int) -> np.ndarray:
        """Generate time-varying LFO filter modulation block for XG compliance.

        CRITICAL FIX: Use dedicated partial LFOs instead of shared channel LFOs to avoid contention.

        Args:
            lfos: List of channel-level LFO objects (ignored - using dedicated LFOs)
            block_size: Number of samples in the block

        Returns:
            Array of filter modulation values (0.0 to 1.0)
        """
        if not hasattr(self, 'dedicated_lfos') or len(self.dedicated_lfos) < 2:
            # Fallback to zero if no dedicated LFOs
            return np.zeros(block_size, dtype=np.float32)
            
        filter_mod_block = self.acc_buffer
        if filter_mod_block is None:
            return np.zeros(block_size, dtype=np.float32)
        filter_mod_block[:block_size].fill(0.0)

        # Use dedicated LFO for filter modulation (LFO2)
        if len(self.dedicated_lfos) > 1:
            lfo = self.dedicated_lfos[1]  # Dedicated filter LFO
            if lfo and hasattr(lfo, 'generate_block'):
                lfo_block = lfo.generate_block(self.item_buffer, block_size)
                if lfo_block is not None and len(lfo_block) >= block_size:
                    filter_mod_block[:block_size] += lfo_block[:block_size] * lfo.filter_depth

        return filter_mod_block

    def _generate_lfo_amplitude_modulation_block(self, lfos: List[XGLFO], block_size: int) -> np.ndarray:
        """Generate time-varying LFO amplitude modulation block for XG tremolo.

        CRITICAL FIX: Use dedicated partial LFOs instead of shared channel LFOs to avoid contention.

        Args:
            lfos: List of channel-level LFO objects (ignored - using dedicated LFOs)
            block_size: Number of samples in the block

        Returns:
            Array of amplitude modulation values (0.0 to 1.0, centered around 1.0)
        """
        if not hasattr(self, 'dedicated_lfos') or len(self.dedicated_lfos) < 3:
            # Fallback to ones if no dedicated LFOs
            return np.ones(block_size, dtype=np.float32)
            
        amp_mod_block = self.acc_buffer
        if amp_mod_block is None:
            return np.ones(block_size, dtype=np.float32)
        amp_mod_block[:block_size].fill(1.0)

        # Use dedicated LFO for amplitude modulation (LFO3)
        if len(self.dedicated_lfos) > 2:
            lfo = self.dedicated_lfos[2]  # Dedicated amplitude LFO
            if lfo and hasattr(lfo, 'generate_block'):
                lfo_block = lfo.generate_block(self.item_buffer, block_size)

                if lfo_block is not None and len(lfo_block) >= block_size:
                    # Apply LFO depth for tremolo effect
                    depth = lfo.amplitude_depth
                    # Convert bipolar LFO (-1 to 1) to unipolar modulation (0.7 to 1.3)
                    tremolo_mod = 1.0 + lfo_block[:block_size] * depth
                    amp_mod_block[:block_size] *= tremolo_mod

        return amp_mod_block

    def _calculate_xg_filter_cutoff_block(self, env_mod_cents_block: np.ndarray) -> np.ndarray:
        """Calculate XG filter cutoff with envelope modulation for block."""
        base_freq = self.filter_cutoff

        # Apply key follow per XG formula: ±24 semitones range
        key_follow_semitones = (self.note - 60) * self.filter_key_follow
        key_follow_mult = 2.0 ** (key_follow_semitones / 12.0)

        # Apply envelope modulation - fix overflow issue by clipping before pow
        env_mod_octaves = np.clip(env_mod_cents_block / 1200.0, -6.0, 6.0)  # Limit to ±7200 cents
        env_mult_block = np.exp2(env_mod_octaves)  # Use exp2 which is more stable than pow
        result = env_mult_block * base_freq * key_follow_mult

        # XG-compliant frequency clamping
        return np.clip(result, 20.0, 20000.0)

    # XG Sound Controller Parameter Updates (Controllers 71-78)

    def update_harmonic_content(self, value: float):
        """XG Sound Controller 71 - Harmonic Content (+/- 24 semitones)."""
        # Convert 0-127 MIDI to -24 to +24 semitone range
        semitones = ((value - 64) / 64.0) * 24.0
        # Apply to filter resonance (XG harmonic content mapping)
        self.filter_resonance = max(0.0, min(2.0, 0.7 + semitones * 0.05))

    def update_brightness(self, value: float):
        """XG Sound Controller 72 - Brightness (+/- 24 semitones)."""
        # Update coefficient manager with new brightness value
        self.coeff_manager.update_xg_coefficient('brightness', int(value))

        # Get pre-computed brightness multiplier
        brightness_mult = self.coeff_manager.get_xg_coefficient('brightness', int(value))
        self.filter_cutoff = max(20, min(20000, 1000.0 * brightness_mult))

    def update_amp_release(self, value: float):
        """XG Sound Controller 73 - Amp Release Time."""
        # 0-127 maps to 0.001 to 18.0 seconds logarithmically
        if value <= 64:
            release_time = 0.001 + (value / 64.0) * 0.999
        else:
            release_time = 1.0 + ((value - 64) / 63.0) * 17.0

        if self.amp_envelope:
            self.amp_envelope.update_parameters(release=release_time)

    def update_amp_attack(self, value: float):
        """XG Sound Controller 74 - Amp Attack Time."""
        # 0-127 maps to 0.001 to 6.0 seconds logarithmically
        if value <= 64:
            attack_time = 0.001 + (value / 64.0) * 0.999
        else:
            attack_time = 1.0 + ((value - 64) / 63.0) * 5.0

        if self.amp_envelope:
            self.amp_envelope.update_parameters(attack=attack_time)

    def update_filter_cutoff(self, value: float):
        """XG Sound Controller 75 - Filter Cutoff Frequency."""
        # Update coefficient manager with new filter cutoff value
        self.coeff_manager.update_xg_coefficient('filter_cutoff', int(value))

        # Get pre-computed frequency ratio
        freq_ratio = self.coeff_manager.get_xg_coefficient('filter_cutoff', int(value))
        self.filter_cutoff = max(20, min(20000, 1000.0 * freq_ratio))

    def update_amp_decay(self, value: float):
        """XG Sound Controller 76 - Amp Decay Time."""
        # 0-127 maps to 0.001 to 24.0 seconds logarithmically
        if value <= 64:
            decay_time = 0.001 + (value / 64.0) * 0.999
        else:
            decay_time = 1.0 + ((value - 64) / 63.0) * 23.0

        if self.amp_envelope:
            self.amp_envelope.update_parameters(decay=decay_time)

    def update_vibrato_rate(self, value: float):
        """XG Sound Controller 77 - Vibrato Rate."""
        # Update coefficient manager with new vibrato rate value
        self.coeff_manager.update_xg_coefficient('vibrato_rate', int(value))

        # Get pre-computed rate
        rate_hz = self.coeff_manager.get_xg_coefficient('vibrato_rate', int(value))
        # Stored for use by channel-level LFO
        self.vibrato_rate = rate_hz

    def update_vibrato_depth(self, value: float):
        """XG Sound Controller 78 - Vibrato Depth."""
        # 0-127 maps to 0 to 600 cents linearly
        depth_cents = (value / 127.0) * 600.0
        # Stored for use by modulation matrix
        self.vibrato_depth_cents = depth_cents

    # XG Modulation interface methods

    def set_modulation_values(self, pitch_mod: float = 0.0, filter_mod: float = 0.0,
                            amp_mod: float = 1.0):
        """Set modulation values from XG modulation matrix."""
        self.last_pitch_mod = pitch_mod
        self.last_filter_mod = filter_mod
        self.last_amp_mod = amp_mod

    def _reset_for_pool(self):
        """Reset partial generator state for pool reuse."""
        # Reset basic state
        self.active = False

        # Ensure cached sample table is initialized
        if not hasattr(self, '_cached_sample_table'):
            self._cached_sample_table = None

        # Reset envelopes to idle state
        self.cleanup()
        # if self.amp_envelope:
        #     self.amp_envelope.reset()
        # if self.filter_envelope:
        #     self.filter_envelope.reset()
        # if self.pitch_envelope:
        #     self.pitch_envelope.reset()

        # Reset LFO modulation values
        self.last_pitch_mod = 0.0
        self.last_filter_mod = 0.0
        self.last_amp_mod = 1.0

        # Reset crossfade values
        self.velocity_crossfade = 0.0
        self.note_crossfade = 0.0

        # Reset phase for sample playback
        self.sample_position = 0.0

        # Reset loop state
        self.loop_direction = 1
        self.loop_position = 0.0

    def _reconfigure(self, synth, note: int, velocity: int, program: int,
                    partial_id: int, partial_params: Dict, is_drum: bool = False,
                    sample_rate: int = 44100, bank: int = 0):
        """Reconfigure existing partial generator with new parameters."""
        # Update basic properties
        self.synth = synth
        self.partial_id = partial_id
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.sample_rate = sample_rate
        self.active = True

        # Set XG partial parameters using shared method
        self._set_partial_parameters(partial_params, is_drum)

        self._cached_sample_table = None
        self._load_sample_table_once()

        # Reinitialize sample table position and advance parameters
        self.sample_position = 0.0
        self.sample_advance_step = self._calculate_sample_advance_step()

        # CRITICAL: Clean up pool resources first (but keep attributes) to prevent None reference errors
        self._cleanup_for_reconfigure()

        # Reinitialize XG-compliant envelopes
        self._initialize_envelopes(partial_params)

        # Reinitialize XG filter
        self._initialize_filter()

        # Reinitialize dedicated LFOs (CRITICAL: recreate after reconfiguration)
        self.dedicated_lfos = []
        for i in range(3):  # 3 LFOs per partial: pitch, filter, amplitude
            lfo = self.synth.partial_lfo_pool.acquire_oscillator(
                id=self.partial_id * 3 + i,  # Unique ID per partial+LFO
                waveform="sine",
                rate=5.0,
                depth=0.5,
                delay=0.0
            )
            # Configure LFO modulation routing
            if i == 0:  # LFO1: Pitch modulation (vibrato)
                lfo.set_modulation_routing(pitch=True, filter=False, amplitude=False)
                lfo.set_modulation_depths(pitch_cents=50.0, filter_depth=0.0, amplitude_depth=0.0)
            elif i == 1:  # LFO2: Filter modulation
                lfo.set_modulation_routing(pitch=False, filter=True, amplitude=False)
                lfo.set_modulation_depths(pitch_cents=0.0, filter_depth=0.3, amplitude_depth=0.0)
            else:  # LFO3: Amplitude modulation (tremolo)
                lfo.set_modulation_routing(pitch=False, filter=False, amplitude=True)
                lfo.set_modulation_depths(pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3)
            self.dedicated_lfos.append(lfo)

        # Start envelopes
        self.note_on(velocity, note)

        # Reset crossfade tracking
        self.velocity_crossfade = 0.0
        self.note_crossfade = 0.0

        # XG Modulation cache
        self.last_pitch_mod = 0.0
        self.last_filter_mod = 0.0
        self.last_amp_mod = 1.0

        # Mark as active
        self.active = True

    def _release_resources(self):
        """Release all pool-allocated resources back to their respective pools.

        This method contains the common resource cleanup logic used by both
        cleanup() and _cleanup_for_reconfigure() methods.
        """
        # Return envelope buffers
        if hasattr(self, 'amp_buffer') and self.amp_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.amp_buffer)
            self.amp_buffer = None

        if hasattr(self, 'work_buffer') and self.work_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.work_buffer)
            self.work_buffer = None

        if hasattr(self, 'acc_buffer') and self.acc_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.acc_buffer)
            self.acc_buffer = None

        if hasattr(self, 'item_buffer') and self.item_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.item_buffer)
            self.item_buffer = None

        if hasattr(self, 'filter_buffer') and self.filter_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.filter_buffer)
            self.filter_buffer = None

        if hasattr(self, 'pitch_buffer') and self.pitch_buffer is not None:
            self.synth.memory_pool.return_mono_buffer(self.pitch_buffer)
            self.pitch_buffer = None

        # Return dedicated LFOs to LFO pool (CRITICAL: prevent resource leaks)
        if hasattr(self, 'dedicated_lfos') and self.dedicated_lfos is not None:
            if hasattr(self.synth, 'partial_lfo_pool'):
                for lfo in self.dedicated_lfos:
                    if lfo is not None and hasattr(self.synth.partial_lfo_pool, 'release_oscillator'):
                        self.synth.partial_lfo_pool.release_oscillator(lfo)
            self.dedicated_lfos = None

        # Return envelopes to envelope pool
        if hasattr(self, 'amp_envelope') and self.amp_envelope is not None:
            if hasattr(self.synth, 'envelope_pool'):
                self.synth.envelope_pool.release_envelope(self.amp_envelope)
            self.amp_envelope = None

        if hasattr(self, 'filter_envelope') and self.filter_envelope is not None:
            if hasattr(self.synth, 'envelope_pool'):
                self.synth.envelope_pool.release_envelope(self.filter_envelope)
            self.filter_envelope = None

        if hasattr(self, 'pitch_envelope') and self.pitch_envelope is not None:
            if hasattr(self.synth, 'envelope_pool'):
                self.synth.envelope_pool.release_envelope(self.pitch_envelope)
            self.pitch_envelope = None

        # Return filter to filter pool
        if hasattr(self, 'filter') and self.filter is not None:
            if hasattr(self.synth, 'filter_pool'):
                self.synth.filter_pool.release_filter(self.filter)
            self.filter = None

    def cleanup(self):
        """Clean up all resources and return buffers to memory pool."""
        self._release_resources()

    def _cleanup_for_reconfigure(self):
        """Clean up pool resources for reconfiguration."""
        self._release_resources()

    def __del__(self):
        """Cleanup when XGPartialGenerator is destroyed."""
        self.cleanup()
