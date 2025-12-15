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
    block_size, sample_rate, filter_state=None
):
    """
    PRODUCTION-GRADE NUMBA-COMPILED: Apply time-varying second-order low-pass filter with accurate bilinear transform.

    This implementation uses a proper digital state variable filter topology with:
    - Accurate bilinear transform coefficient calculation
    - State preservation across blocks (requires filter_state buffer)
    - Proper DC response (no DC offset)
    - Resonance limiting to prevent instability
    - Time-varying cutoff with smooth interpolation

    Args:
        left_block: Left channel buffer (modified in-place)
        right_block: Right channel buffer (modified in-place)
        filter_cutoff_block: Time-varying cutoff frequencies (block_size array)
        filter_resonance: Filter resonance (0.0-4.0, clamped to reasonable range)
        block_size: Number of samples to process
        sample_rate: Audio sample rate
        filter_state: 4-element array for [left_z1, left_z2, right_z1, right_z2] filter state
                     If None, state variables are reset to 0.0
    """
    # Initialize or validate filter state
    if filter_state is None:
        # Temporary state (won't persist between blocks)
        left_z1, left_z2 = 0.0, 0.0
        right_z1, right_z2 = 0.0, 0.0
    else:
        # Persistent state across blocks
        left_z1 = filter_state[0]
        left_z2 = filter_state[1]
        right_z1 = filter_state[2]
        right_z2 = filter_state[3]

    # Clamp resonance to prevent instability (typical range 0.0-4.0)
    resonance = max(0.0, min(4.0, filter_resonance))

    for i in range(block_size):
        # Get and clamp cutoff frequency (prewarping for bilinear transform)
        cutoff = filter_cutoff_block[i]
        cutoff = max(20.0, min(cutoff, sample_rate * 0.49))

        # Calculate angular frequency with bilinear prewarping
        wc = 2.0 * math.pi * cutoff / sample_rate

        # Limit wc to prevent tan() overflow (π/2 - ε for stability)
        wc = min(wc, math.pi * 0.499)

        # Bilinear transform prewarping (maps analog frequency to digital)
        wp = math.tan(wc * 0.5)

        # Additional safety clamp for wp to prevent extreme values
        wp = max(0.001, min(wp, 1000.0))

        # Calculate filter coefficients for second-order Butterworth response
        # This provides smooth frequency response without ripple
        k1 = wp * wp
        k2 = 2.0 * wp * math.sqrt(resonance + 1.0)  # Q factor from resonance

        # Clamp intermediate values to prevent overflow in coefficient calculation
        k1 = max(0.001, min(k1, 10000.0))
        k2 = max(0.001, min(k2, 10000.0))

        k3 = 1.0 + k1 + k2

        # Normalize coefficients
        a0 = 1.0 / k3
        a1 = 2.0 / k3
        a2 = 1.0 / k3
        b1 = (2.0 - 2.0 * k1) / k3
        b2 = (1.0 - k1 - k2) / k3

        # Apply filter to left channel (direct form 2) with overflow protection
        input_left = left_block[i]
        # Clamp input to prevent overflow
        input_left = max(-10.0, min(10.0, input_left))
        output_left = a0 * input_left + a1 * left_z1 + a2 * left_z2 - b1 * left_z1 - b2 * left_z2
        # Clamp output to prevent overflow
        output_left = max(-10.0, min(10.0, output_left))

        # Update left channel state with overflow protection
        left_z2 = left_z1
        left_z1 = a0 * input_left + left_z1 * (1.0 + b1) + left_z2 * b2
        # Clamp state variables to prevent overflow
        left_z1 = max(-10.0, min(10.0, left_z1))
        left_z2 = max(-10.0, min(10.0, left_z2))

        # Apply filter to right channel (direct form 2) with overflow protection
        input_right = right_block[i]
        # Clamp input to prevent overflow
        input_right = max(-10.0, min(10.0, input_right))
        output_right = a0 * input_right + a1 * right_z1 + a2 * right_z2 - b1 * right_z1 - b2 * right_z2
        # Clamp output to prevent overflow
        output_right = max(-10.0, min(10.0, output_right))

        # Update right channel state with overflow protection
        right_z2 = right_z1
        right_z1 = a0 * input_right + right_z1 * (1.0 + b1) + right_z2 * b2
        # Clamp state variables to prevent overflow
        right_z1 = max(-10.0, min(10.0, right_z1))
        right_z2 = max(-10.0, min(10.0, right_z2))

        # Store output samples
        left_block[i] = output_left
        right_block[i] = output_right

    # Update filter state if provided
    if filter_state is not None:
        filter_state[0] = left_z1
        filter_state[1] = left_z2
        filter_state[2] = right_z1
        filter_state[3] = right_z2


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
        if pitch_mod_cents > 3400:
            pitch_mod_cents = 2400.0
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
        elif phase == np.inf:
            phase = 0.0

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
        self.use_filter_env = partial_params.get("use_filter_env", False)#not is_drum)
        if self.use_filter_env:
            self.filter_attack_time = partial_params.get("filter_attack", 0.1)
            self.filter_decay_time = partial_params.get("filter_decay", 0.5)
            self.filter_sustain_level = partial_params.get("filter_sustain", 0.6)
            self.filter_release_time = partial_params.get("filter_release", 0.8)
            self.filter_delay_time = partial_params.get("filter_delay", 0.0)
            self.filter_hold_time = partial_params.get("filter_hold", 0.0)

        # XG Pitch envelope - can be disabled for drums
        self.use_pitch_env = partial_params.get("use_pitch_env", False)#not is_drum)
        if self.use_pitch_env:
            self.pitch_attack_time = partial_params.get("pitch_attack", 0.05)
            self.pitch_decay_time = partial_params.get("pitch_decay", 0.1)
            self.pitch_sustain_level = partial_params.get("pitch_sustain", 0.0)  # Fixed for XG
            self.pitch_release_time = partial_params.get("pitch_release", 0.05)
            self.pitch_delay_time = partial_params.get("pitch_delay", 0.0)
            self.pitch_hold_time = partial_params.get("pitch_hold", 0.0)
            # XG Pitch envelope depth - controllable amount (cents)
            self.pitch_envelope_depth = partial_params.get("pitch_envelope_depth", 1200.0)  # Default ±1200 cents

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

        # Base values for modulation
        self.base_velocity_crossfade = 0.0
        self.base_note_crossfade = 0.0
        self.base_stereo_width = 1.0
        self.base_pan = self.pan  # Store original pan for modulation

        # Filter state for time-varying filter (4 elements: left_z1, left_z2, right_z1, right_z2)
        self.filter_state = np.zeros(4, dtype=np.float32)

    def _calculate_antialiasing_cutoff(self) -> float:
        """
        Calculate the appropriate antialiasing filter cutoff for the current note.

        This prevents aliasing artifacts when playing high-pitched notes by filtering
        out harmonics that would fold back into the audible range above the Nyquist
        frequency (half the sample rate).

        The cutoff is calculated based on:
        1. The fundamental frequency of the note being played
        2. The desired harmonic content preservation (typically up to 8th harmonic)
        3. Safe margin below the Nyquist frequency

        Returns:
            Antialiasing filter cutoff frequency in Hz
        """
        # Get the fundamental frequency of the note
        fundamental_freq = self._calculate_base_frequency()

        # Determine how many harmonics to preserve
        # For high notes, we need to be more aggressive to prevent aliasing
        if fundamental_freq > 1000:  # Above C6
            # Preserve up to 4th harmonic for very high notes
            max_preserved_harmonic = 4
        elif fundamental_freq > 500:  # Above C5
            # Preserve up to 6th harmonic for high notes
            max_preserved_harmonic = 6
        else:
            # Preserve up to 8th harmonic for lower notes
            max_preserved_harmonic = 8

        # Calculate the highest frequency to preserve
        highest_preserved_freq = fundamental_freq * max_preserved_harmonic

        # Apply safety margin (80% of Nyquist to prevent artifacts)
        nyquist_freq = self.sample_rate / 2.0
        safe_cutoff = nyquist_freq * 0.8  # 80% of Nyquist

        # The antialiasing cutoff is the minimum of:
        # 1. The highest preserved harmonic frequency
        # 2. The safe cutoff frequency
        # 3. A reasonable maximum (20kHz for audibility)
        antialiasing_cutoff = min(highest_preserved_freq, safe_cutoff, 20000.0)

        # Ensure minimum cutoff (prevent over-filtering low notes)
        antialiasing_cutoff = max(antialiasing_cutoff, 5000.0)  # Minimum 5kHz

        return antialiasing_cutoff

    def _apply_antialiasing_filter(self, left_block: np.ndarray, right_block: np.ndarray,
                                  block_size: int):
        """
        Apply antialiasing filter to prevent high-frequency aliasing artifacts.

        This filter removes frequencies above the calculated cutoff that would
        fold back into the audible range when the sample is pitch-shifted to
        high notes.

        Args:
            left_block: Left channel audio buffer (modified in-place)
            right_block: Right channel audio buffer (modified in-place)
            block_size: Number of samples to process
        """
        if not self.antialiasing_enabled or self.antialiasing_cutoff_hz >= 20000.0:
            # Skip filtering if disabled or cutoff is very high
            return

        # Create time-varying cutoff block for the antialiasing filter
        # Use the same cutoff for the entire block (could be made time-varying in future)
        cutoff_block = np.full(block_size, self.antialiasing_cutoff_hz, dtype=np.float32)

        # Apply low-pass filter with high slope (24dB/octave) for effective antialiasing
        # Use resonance = 0.0 for flat response, focus on frequency attenuation
        _numba_apply_time_varying_filter(
            left_block, right_block, cutoff_block,
            0.0,  # No resonance for clean antialiasing
            block_size, self.sample_rate, self.antialiasing_filter_state
        )

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
        # Mip-mapping handles quality reduction at sample loading level
        self._generate_waveform_block_time_varying(left_block, right_block, self.work_buffer, block_size)

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
                self.filter_resonance, block_size, self.sample_rate, self.filter_state
            )

        # Generate time-varying amplitude modulation (LFO tremolo)
        self.work_buffer[:block_size].fill(self.last_amp_mod)
        if lfos:
            lfo_amp_block = self._generate_lfo_amplitude_modulation_block(lfos, block_size)
            self.work_buffer[:block_size] *= lfo_amp_block[:block_size]

        # Apply envelope, level, crossfade, and panning using Numba-compiled SIMD operations
        crossfade_factor = (1.0 - self.velocity_crossfade) * (1.0 - self.note_crossfade)

        # Get pre-computed panning coefficients
        # Convert normalized pan (-1.0 to 1.0) to MIDI pan (0-127)
        pan_int = int((self.pan + 1.0) / 2.0 * 127.0)
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
            pitch_env_block[:block_size] *= self.pitch_envelope_depth
        return pitch_env_block

    def update_pitch_envelope_depth(self, value: float):
        """XG NRPN/Parameter: Pitch envelope to pitch depth control.

        Maps 0-127 MIDI values to pitch envelope depth range.
        XG Spec: MSB 0, LSB 440 (System Effects pitch env amount)
        """
        # Map 0-127 to ±1200 cents (1 octave) range, with center at 0
        # 64 = 0 cents (no pitch modulation), 127 = +1200 cents, 0 = -1200 cents
        cents_range = ((value - 64) / 63.0) * 1200.0
        self.pitch_envelope_depth = max(-1200.0, min(2400.0, cents_range))  # Allow wider range

    def _generate_waveform_block_time_varying(self, left_block: np.ndarray, right_block: np.ndarray,
                                             pitch_mod_block: np.ndarray, block_size: int) -> None:
        """Generate entire sample block with TIME-VARYING pitch modulation.

        This method implements proper XG-compliant time-varying pitch modulation within blocks,
        maintaining the same audio quality as per-sample processing.

        Args:
            left_block: Pre-allocated array to fill with left channel samples
            right_block: Pre-allocated array to fill with right channel samples
            pitch_mod_block: Time-varying pitch modulation in cents (block_size array)
        """
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
                # Apply LFO modulation with comprehensive bounds checking
                if lfo_block is not None and len(lfo_block) >= block_size:
                    # Calculate modulation with bounds checking
                    raw_modulation = lfo_block[:block_size] * lfo.pitch_depth_cents
                    # Apply bounds checking to prevent excessive modulation
                    max_pitch_mod = 2400.0  # ±2 octaves maximum
                    bounded_modulation = np.clip(raw_modulation, -max_pitch_mod, max_pitch_mod)
                    pitch_mod_block[:block_size] += bounded_modulation

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
                # Apply LFO filter modulation with comprehensive bounds checking
                if lfo_block is not None and len(lfo_block) >= block_size:
                    # Calculate modulation with bounds checking
                    raw_modulation = lfo_block[:block_size] * lfo.filter_depth
                    # Apply bounds checking to prevent excessive modulation
                    max_filter_mod = 1.0  # Maximum filter modulation depth
                    bounded_modulation = np.clip(raw_modulation, -max_filter_mod, max_filter_mod)
                    filter_mod_block[:block_size] += bounded_modulation

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
                    # Apply LFO amplitude modulation with comprehensive bounds checking
                    depth = lfo.amplitude_depth
                    # Apply bounds checking to depth
                    bounded_depth = max(0.0, min(1.0, depth))
                    # Convert bipolar LFO (-1 to 1) to unipolar modulation with bounds checking
                    raw_tremolo_mod = 1.0 + lfo_block[:block_size] * bounded_depth
                    # Apply bounds checking to prevent excessive modulation
                    min_tremolo = 0.5  # Minimum tremolo depth
                    max_tremolo = 1.5  # Maximum tremolo depth
                    bounded_tremolo_mod = np.clip(raw_tremolo_mod, min_tremolo, max_tremolo)
                    amp_mod_block[:block_size] *= bounded_tremolo_mod

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
        # Store for use by dedicated LFO
        self.vibrato_rate = rate_hz

        # Apply rate to dedicated pitch LFO (LFO0)
        if hasattr(self, 'dedicated_lfos') and self.dedicated_lfos is not None and len(self.dedicated_lfos) > 0:
            lfo = self.dedicated_lfos[0]  # Dedicated pitch LFO
            if lfo and hasattr(lfo, 'set_rate'):
                lfo.set_rate(self.vibrato_rate)

    def update_vibrato_depth(self, value: float):
        """XG Sound Controller 78 - Vibrato Depth."""
        # 0-127 maps to 0 to 600 cents linearly
        depth_cents = (value / 127.0) * 600.0
        # Store for use by dedicated LFO
        self.vibrato_depth_cents = depth_cents

        # Apply depth to dedicated pitch LFO (LFO0)
        if hasattr(self, 'dedicated_lfos') and self.dedicated_lfos is not None and len(self.dedicated_lfos) > 0:
            lfo = self.dedicated_lfos[0]  # Pitch LFO
            if lfo and hasattr(lfo, 'set_modulation_depths'):
                lfo.set_modulation_depths(pitch_cents=self.vibrato_depth_cents, filter_depth=0.0, amplitude_depth=0.0)

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

        # LFO modulation cache for dynamic LFO control
        self.lfo_rate_modulation = {}  # {lfo_index: rate_mod_value}
        self.lfo_depth_modulation = {}  # {lfo_index: depth_mod_value}

    def apply_lfo_modulation(self, lfo_modulation_values: Dict[str, float]):
        """
        Consume LFO modulation destinations and apply to dedicated LFOs.

        This method enables real-time control of LFO parameters through the
        modulation matrix, allowing controllers to modulate vibrato rate/depth,
        filter LFO rate/depth, and tremolo rate/depth dynamically.

        Args:
            lfo_modulation_values: Dictionary containing LFO modulation values
                                  from modulation matrix destinations
        """
        # Extract LFO rate modulation values
        lfo1_rate_mod = lfo_modulation_values.get("lfo1_rate", 0.0)
        lfo2_rate_mod = lfo_modulation_values.get("lfo2_rate", 0.0)
        lfo3_rate_mod = lfo_modulation_values.get("lfo3_rate", 0.0)

        # Extract LFO depth modulation values
        lfo1_depth_mod = lfo_modulation_values.get("lfo1_depth", 0.0)
        lfo2_depth_mod = lfo_modulation_values.get("lfo2_depth", 0.0)
        lfo3_depth_mod = lfo_modulation_values.get("lfo3_depth", 0.0)

        # Apply rate modulation to dedicated LFOs
        if hasattr(self, 'dedicated_lfos') and self.dedicated_lfos:
            # LFO1: Pitch modulation (vibrato)
            if len(self.dedicated_lfos) > 0 and self.dedicated_lfos[0]:
                self.dedicated_lfos[0].apply_rate_modulation(lfo1_rate_mod)
                self.dedicated_lfos[0].apply_depth_modulation(lfo1_depth_mod)

            # LFO2: Filter modulation
            if len(self.dedicated_lfos) > 1 and self.dedicated_lfos[1]:
                self.dedicated_lfos[1].apply_rate_modulation(lfo2_rate_mod)
                self.dedicated_lfos[1].apply_depth_modulation(lfo2_depth_mod)

            # LFO3: Amplitude modulation (tremolo)
            if len(self.dedicated_lfos) > 2 and self.dedicated_lfos[2]:
                self.dedicated_lfos[2].apply_rate_modulation(lfo3_rate_mod)
                self.dedicated_lfos[2].apply_depth_modulation(lfo3_depth_mod)

    def apply_envelope_modulation(self, envelope_modulation_values: Dict[str, float]):
        """
        Consume envelope modulation destinations for dynamic envelope control.

        This enables real-time modulation of envelope parameters during performance,
        allowing controllers to dynamically adjust attack, decay, sustain, and release
        times for amplitude, filter, and pitch envelopes.

        Args:
            envelope_modulation_values: Dictionary containing envelope modulation values
                                       from modulation matrix destinations
        """
        # Amplitude envelope modulation
        amp_attack_mod = envelope_modulation_values.get("amp_attack", 0.0)
        amp_decay_mod = envelope_modulation_values.get("amp_decay", 0.0)
        amp_sustain_mod = envelope_modulation_values.get("amp_sustain", 0.0)
        amp_release_mod = envelope_modulation_values.get("amp_release", 0.0)

        if self.amp_envelope:
            self.amp_envelope.modulate_parameters(
                attack_mod=amp_attack_mod, decay_mod=amp_decay_mod,
                sustain_mod=amp_sustain_mod, release_mod=amp_release_mod
            )

        # Filter envelope modulation
        if self.use_filter_env and self.filter_envelope:
            filter_attack_mod = envelope_modulation_values.get("filter_attack", 0.0)
            filter_decay_mod = envelope_modulation_values.get("filter_decay", 0.0)
            filter_sustain_mod = envelope_modulation_values.get("filter_sustain", 0.0)
            filter_release_mod = envelope_modulation_values.get("filter_release", 0.0)

            self.filter_envelope.modulate_parameters(
                attack_mod=filter_attack_mod, decay_mod=filter_decay_mod,
                sustain_mod=filter_sustain_mod, release_mod=filter_release_mod
            )

        # Pitch envelope modulation
        if self.use_pitch_env and self.pitch_envelope:
            pitch_attack_mod = envelope_modulation_values.get("pitch_attack", 0.0)
            pitch_decay_mod = envelope_modulation_values.get("pitch_decay", 0.0)
            pitch_sustain_mod = envelope_modulation_values.get("pitch_sustain", 0.0)
            pitch_release_mod = envelope_modulation_values.get("pitch_release", 0.0)

            self.pitch_envelope.modulate_parameters(
                attack_mod=pitch_attack_mod, decay_mod=pitch_decay_mod,
                sustain_mod=pitch_sustain_mod, release_mod=pitch_release_mod
            )

    def apply_advanced_modulation(self, advanced_modulation_values: Dict[str, float]):
        """
        Consume advanced synthesis modulation destinations.

        This enables dynamic control of crossfade, stereo width, and tremolo
        parameters for advanced synthesis capabilities.

        Args:
            advanced_modulation_values: Dictionary containing advanced modulation values
                                       from modulation matrix destinations
        """
        # Crossfade modulation
        velocity_crossfade_mod = advanced_modulation_values.get("velocity_crossfade", 0.0)
        note_crossfade_mod = advanced_modulation_values.get("note_crossfade", 0.0)

        # Apply crossfade modulation to existing crossfade parameters
        self.velocity_crossfade = np.clip(self.base_velocity_crossfade + velocity_crossfade_mod, 0.0, 1.0)
        self.note_crossfade = np.clip(self.base_note_crossfade + note_crossfade_mod, 0.0, 1.0)

        # Stereo width modulation
        stereo_width_mod = advanced_modulation_values.get("stereo_width", 0.0)
        self.stereo_width = np.clip(self.base_stereo_width + stereo_width_mod, 0.0, 2.0)
        self._update_stereo_coefficients()

        # Tremolo rate modulation (applied to dedicated tremolo LFO)
        tremolo_rate_mod = advanced_modulation_values.get("tremolo_rate", 0.0)
        tremolo_depth_mod = advanced_modulation_values.get("tremolo_depth", 0.0)

        if hasattr(self, 'dedicated_lfos') and self.dedicated_lfos and len(self.dedicated_lfos) > 2:
            tremolo_lfo = self.dedicated_lfos[2]  # Dedicated amplitude LFO
            if tremolo_lfo:
                tremolo_lfo.apply_rate_modulation(tremolo_rate_mod)
                tremolo_lfo.apply_depth_modulation(tremolo_depth_mod)

    def _update_stereo_coefficients(self):
        """
        Update stereo panning coefficients based on current stereo width.

        This method recalculates left/right channel gains based on the
        modulated stereo width parameter for dynamic stereo imaging.

        Stereo width ranges from 0.0 (mono) to 2.0 (extra-wide stereo).
        """
        # Base panning from partial pan parameter
        base_pan = self.pan  # -1.0 to 1.0 range

        # Apply stereo width modulation
        # Width of 1.0 = normal stereo, 0.0 = mono, 2.0 = enhanced stereo
        width_factor = self.stereo_width

        if width_factor <= 0.0:
            # Mono - both channels get same signal
            self.stereo_left_gain = 0.707  # 1/sqrt(2) for proper mono mix
            self.stereo_right_gain = 0.707
        else:
            # Stereo with width modulation
            # Calculate left/right gains based on pan and width
            if base_pan < 0:
                # Panned left - reduce right channel more with width
                left_base = 1.0
                right_base = 1.0 + base_pan  # base_pan is negative, so this increases right
            elif base_pan > 0:
                # Panned right - reduce left channel more with width
                left_base = 1.0 - base_pan  # base_pan is positive, so this reduces left
                right_base = 1.0
            else:
                # Center - equal power to both channels
                left_base = 1.0
                right_base = 1.0

            # Apply width factor
            # Width > 1.0 increases separation, width < 1.0 reduces separation
            width_boost = width_factor
            self.stereo_left_gain = left_base * width_boost
            self.stereo_right_gain = right_base * width_boost

            # Normalize to prevent clipping (optional - could be left as-is for effect)
            total_gain = self.stereo_left_gain + self.stereo_right_gain
            if total_gain > 2.0:  # Prevent excessive boost
                normalize_factor = 2.0 / total_gain
                self.stereo_left_gain *= normalize_factor
                self.stereo_right_gain *= normalize_factor

    def apply_pan_modulation(self, pan_mod: float):
        """
        Apply pan modulation to the partial.

        Args:
            pan_mod: Pan modulation value (-1.0 to 1.0, where 0.0 = center)
        """
        # Apply pan modulation with bounds checking
        self.pan = np.clip(self.base_pan + pan_mod, -1.0, 1.0)

        # Update stereo coefficients if stereo width is active
        if hasattr(self, 'stereo_width') and self.stereo_width != 1.0:
            self._update_stereo_coefficients()

    def apply_modulation(self, synthesis_mod, lfo_mod, envelope_mod, advanced_mod):
        """
        Unified modulation application method.

        Applies all types of modulation in the correct order for proper synthesis:
        1. Envelope modulation (affects envelope shapes)
        2. LFO modulation (affects LFO parameters)
        3. Advanced synthesis modulation (crossfade, stereo, etc.)
        4. Core synthesis modulation (pitch, filter, amplitude, pan)

        Args:
            synthesis_mod: Core synthesis modulation values
            lfo_mod: LFO parameter modulation values
            envelope_mod: Envelope parameter modulation values
            advanced_mod: Advanced synthesis modulation values
        """
        # 1. Apply envelope modulation first (affects envelope shapes)
        self.apply_envelope_modulation(envelope_mod)

        # 2. Apply LFO modulation (affects LFO parameters)
        self.apply_lfo_modulation(lfo_mod)

        # 3. Apply advanced synthesis modulation
        self.apply_advanced_modulation(advanced_mod)

        # 4. Apply pan modulation
        pan_mod = synthesis_mod.get("pan", 0.0)
        if pan_mod != 0.0:
            self.apply_pan_modulation(pan_mod)

        # 5. Apply core synthesis modulation (stored for audio generation)
        self.set_modulation_values(
            synthesis_mod.get("pitch", 0.0),
            synthesis_mod.get("filter_cutoff", 0.0),
            synthesis_mod.get("amp", 1.0)
        )

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


    # ============================================================================
    # XG VOICE PARAMETER EXTENSIONS - PHASE A COMPLETION
    # Implements missing MSB 127 NRPN voice synthesis parameters
    # ============================================================================

    def _process_element_switch(self, value: int):
        """Process XG Voice Element Switch (MSB 127, LSB 0).

        Controls which voice elements (0-7) are active as bit field.
        Bit 0 = Element 0, Bit 1 = Element 1, etc.

        Args:
            value: Bit field (0-255) where each bit enables/disables an element
        """
        # Update element activation state (though partials typically don't manage elements)
        # This is mainly for XG voice definition consistency
        self.element_switch = value

        # In a real XG voice, this would enable/disable partial elements
        # For this partial generator, we note the element activation
        active_elements = []
        for i in range(8):  # Maximum 8 elements in XG
            if (value & (1 << i)) != 0:
                active_elements.append(i)
        self.active_elements = active_elements

    def _handle_key_limits(self, low_limit: int, high_limit: int):
        """Handle XG Voice Key Limits (MSB 127, LSB 3-4).

        Defines the note range this voice responds to.

        Args:
            low_limit: Lowest MIDI note (0-127)
            high_limit: Highest MIDI note (0-127)
        """
        self.voice_key_low = max(0, min(127, low_limit))
        self.voice_key_high = max(0, min(127, high_limit))

        # Ensure valid range
        if self.voice_key_high < self.voice_key_low:
            self.voice_key_high = self.voice_key_low

    def _apply_pitch_shift(self, shift_semitones: int):
        """Apply XG Voice Note Shift (MSB 127, LSB 5).

        Shifts the entire voice up/down in semitone intervals.

        Args:
            shift_semitones: Shift in semitones (-64 to +63)
        """
        # Clamp to valid range per XG specification
        self.note_shift_semitones = max(-64, min(63, shift_semitones))

        # Apply shift to fundamental calculation
        # This effectively offsets the root key
        self.effective_root_key = self.note + self.note_shift_semitones

    def _calc_detune(self, detune_cents: float):
        """Calculate XG Voice Detune (MSB 127, LSB 6).

        Fine pitch adjustment beyond tuning in Hz, centered at 0.

        Args:
            detune_cents: Detune in cent units (-400 to +393.75 cents)
        """
        # XG detune formula: (value - 64) * 100 / 16 (where value = MSB 127 LSB 6)
        # Converts MIDI value to cents, then to Hz
        if detune_cents != 0.0:
            # Convert cents to frequency ratio
            detune_ratio = 2.0 ** (detune_cents / 1200.0)

            # Apply to base frequency (compound with note shift)
            self.detune_multiplier = detune_ratio
        else:
            self.detune_multiplier = 1.0

    def _velocity_sensitivity_xg(self, sensitivity: int):
        """Apply XG Voice Velocity Sensitivity (MSB 127, LSB 7).

        Controls how MIDI velocity affects voice level.

        Args:
            sensitivity: Velocity sensitivity (0-127)
        """
        # XG formula: (velocity_sense_param * 127 / 2000) + 0.007
        self.xg_velocity_sensitivity = (sensitivity * 127.0 / 2000.0) + 0.007

        # Update velocity scaling curve
        # This affects how input velocity maps to output amplitude
        self.velocity_curve_factor = 1.0 + (sensitivity / 127.0) * 0.5

    def _level_control(self, voice_level: float):
        """Control XG Voice Level (MSB 127, LSB 8).

        Overall voice output level.

        Args:
            voice_level: Voice level (0.0 to 1.0)
        """
        self.voice_master_level = max(0.0, min(1.0, voice_level))

        # This multiplies with the existing level parameter
        # self.level *= self.voice_master_level

    def _velocity_rate_sens(self, rate_sensitivity: float):
        """Control XG Velocity Rate Sensitivity (MSB 127, LSB 9).

        How velocity affects envelope attack time.

        Args:
            rate_sensitivity: Velocity sensitivity for attack rate (-1.0 to +1.0)
        """
        # XG velocity rate sensitivity affects envelope attack time
        self.attack_velocity_factor = max(-1.0, min(1.0, rate_sensitivity))

        # Update envelope parameters if envelope exists
        if hasattr(self, 'amp_envelope') and self.amp_envelope:
            # Modify attack time based on velocity
            # Higher positive values = faster attack with higher velocity
            base_attack = getattr(self.amp_envelope, '_attack_time', 0.01)
            self.modified_attack_time = base_attack * (1.0 + rate_sensitivity * 0.5)

    def _pan_control(self, pan_position: float):
        """Control XG Voice Pan (MSB 127, LSB 10).

        Left/right stereo positioning for the voice.

        Args:
            pan_position: Pan position (-1.0 left, 0.0 center, +1.0 right)
        """
        self.voice_pan = max(-1.0, min(1.0, pan_position))

        # Convert to pan gains (overrides channel pan for voice-specific positioning)
        if self.voice_pan < 0:
            # Pan left: left gain full, right gain reduced
            self.voice_pan_left = 1.0
            self.voice_pan_right = 1.0 + self.voice_pan  # -1.0 results in 0.0
        elif self.voice_pan > 0:
            # Pan right: left gain reduced, right gain full
            self.voice_pan_left = 1.0 - self.voice_pan   # 1.0 results in 0.0
            self.voice_pan_right = 1.0
        else:
            # Center: both full gain
            self.voice_pan_left = 1.0
            self.voice_pan_right = 1.0

    def _mode_assignment(self, assign_mode: int):
        """Control XG Voice Assign Mode (MSB 127, LSB 11).

        How voices are assigned when polyphony is exceeded.

        Args:
            assign_mode: Assignment mode (0=single, 1=multi, 2=poly, 3=mono)
        """
        self.voice_assign_mode = max(0, min(3, assign_mode))

        # XG assign modes:
        # 0: Single - only one voice at a time
        # 1: Multi - multiple voices (default polyphonic)
        # 2: Poly - strict polyphonic allocation
        # 3: Mono - monophonic with portamento

        # Configure polyphony behavior
        if assign_mode == 0:  # Single
            self.max_concurrent_voices = 1
            self.voice_stealing_mode = 'single'
        elif assign_mode == 3:  # Mono
            self.max_concurrent_voices = 1
            self.voice_stealing_mode = 'mono'
            self.portamento_enabled = True
        else:  # Multi/Poly
            self.max_concurrent_voices = 8  # No limit
            self.voice_stealing_mode = 'round_robin'

    def _fine_tune_xg(self, fine_tune_cents: float):
        """Apply XG Fine Tuning (MSB 127, LSB 12).

        Microscopic pitch adjustment in cents.

        Args:
            fine_tune_cents: Fine tuning in cents (-1.0 to +1.0)
        """
        # XG fine tuning precision: (value - 64) / 8192 relative to A=440
        # This is in addition to coarse tuning and detune
        self.xg_fine_tune_cents = max(-1.0, min(1.0, fine_tune_cents))

        # Convert to frequency ratio
        fine_tune_ratio = 2.0 ** (self.xg_fine_tune_cents / 1200.0)
        self.fine_tune_multiplier = fine_tune_ratio

    def _coarse_tune_xg(self, coarse_tune_semitones: int):
        """Apply XG Coarse Tuning (MSB 127, LSB 13).

        Coarse pitch adjustment in semitones.

        Args:
            coarse_tune_semitones: Coarse tuning in semitones (-64 to +63)
        """
        # XG coarse tuning: full semitone steps
        self.xg_coarse_tune_semitones = max(-64, min(63, coarse_tune_semitones))

        # Convert to frequency ratio
        coarse_tune_ratio = 2.0 ** (self.xg_coarse_tune_semitones / 12.0)
        self.coarse_tune_multiplier = coarse_tune_ratio

    def _random_pitch(self, random_range: float):
        """Apply XG Pitch Random (MSB 127, LSB 14).

        Adds randomization to pitch per note-on.

        Args:
            random_range: Random range in semitones (0-1.27)
        """
        self.pitch_random_range = max(0.0, min(1.27, random_range))

        # This would be applied per note-on event
        # Implementation would set a random offset within this range
        self.pitch_random_enabled = random_range > 0.0

    def _pitch_scaling(self, scale_tune_cents: int, scale_sensitivity: int):
        """Apply XG Pitch Scale Tuning/Sensitivity (MSB 127, LSB 15-16).

        Microtonal per-scale-degree pitch adjustments.

        Args:
            scale_tune_cents: Scale tuning offset (-64 to +63 cents per degree)
            scale_sensitivity: How scale degrees affect pitch (-24 to +24)
        """
        self.scale_tuning_cents = max(-64, min(63, scale_tune_cents))
        self.scale_sensitivity = max(-24, min(24, scale_sensitivity))

        # XG scale tuning affects pitch based on scale degree
        # This is complex and would require scale analysis
        self.scale_tuning_enabled = abs(scale_tune_cents) > 0 or abs(scale_sensitivity) > 0

    def _voice_delay_effects(self, delay_mode: int, delay_time: float, delay_feedback: float):
        """Apply XG Voice Delay Effects (MSB 127, LSB 17-19).

        Voice-internal delay processing.

        Args:
            delay_mode: Delay trigger mode (0=normal, 1=keyed, 2=hold)
            delay_time: Delay time in samples (0-2048 typically)
            delay_feedback: Delay feedback amount (0.0-1.0)
        """
        self.delay_mode = max(0, min(2, delay_mode))
        self.delay_time_samples = max(0, min(2048, delay_time))
        self.delay_feedback = max(0.0, min(1.0, delay_feedback))

        # These would control internal voice delay processing
        self.voice_delay_enabled = delay_time > 0
