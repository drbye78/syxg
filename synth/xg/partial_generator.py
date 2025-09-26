"""
XG Partial Generator - Production XG-Compliant Implementation

Implements XG Partial Structure concept with up to 8 partials per program.
Each partial has exclusive note/velocity ranges and independent XG parameters.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import numpy as np

from synth.sf2.core.wavetable_manager import WavetableManager
from ..core.vectorized_envelope import VectorizedADSREnvelope
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner
from ..engine.optimized_coefficient_manager import get_global_coefficient_manager


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

    def __init__(self, wavetable: Optional[WavetableManager], note: int, velocity: int, program: int,
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
        self.wavetable: Optional[WavetableManager] = wavetable
        self.partial_id = partial_id
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.sample_rate = sample_rate
        self.active = True

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

        # SF2 Loop information (initialized later when sample is loaded)
        self.sample_start = 0
        self.sample_end = 0
        self.loop_start = 0
        self.loop_end = 0
        self.loop_mode = 0  # 0=no loop, 1=forward, 2=backward, 3=alternating

        # Loop state for alternating loops
        self.loop_direction = 1  # 1=forward, -1=backward (for alternating loops)
        self.loop_position = 0.0  # Current position within loop

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
        self.filter_cutoff = filter_config.get("cutoff", 1000.0)  # Hz
        self.filter_resonance = filter_config.get("resonance", 0.7)  # 0.0-2.0
        self.filter_type = filter_config.get("type", "lowpass")
        self.filter_key_follow = filter_config.get("key_follow", 0.5)  # XG key follow

        # Check if note/velocity fall within this partial's range
        if not self._is_note_in_range(note, velocity):
            self.active = False
            return

        # Optimized coefficient manager for performance
        self.coeff_manager = get_global_coefficient_manager()

        # Cache sample table once during construction (never changes for XG partials)
        self._cached_sample_table = None
        self._load_sample_table_once()

        # Initialize phase and synthesis parameters
        self.phase = 0.0
        self.phase_step = self._calculate_phase_step()

        # Initialize XG-compliant envelopes
        self._initialize_envelopes(partial_params)

        # Initialize XG filter
        self._initialize_filter()

        # Start envelopes (Per XG, envelopes start on note-on)
        self.note_on(velocity, note)

        # Crossfade tracking
        self.velocity_crossfade = 0.0
        self.note_crossfade = 0.0

        # XG Modulation cache
        self.last_pitch_mod = 0.0
        self.last_filter_mod = 0.0
        self.last_amp_mod = 1.0  # Default to 1.0 (no modulation)


    def _is_note_in_range(self, note: int, velocity: int) -> bool:
        """Check if note and velocity fall within this partial's XG-defined ranges."""
        return (self.key_range_low <= note <= self.key_range_high and
                self.velocity_range_low <= velocity <= self.velocity_range_high)

    def _calculate_phase_step(self) -> float:
        """Calculate phase step for XG synthesis with proper tuning."""
        # Determine root key for XG synthesis
        root_key = self.overriding_root_key if self.overriding_root_key >= 0 else self.note

        # XG Base frequency calculation
        base_freq = 440.0 * (2.0 ** ((root_key - 69) / 12.0))

        # Apply XG scale tuning (cents to frequency multiplier)
        tuning_multiplier = 2.0 ** (self.scale_tuning / 1200.0)
        base_freq *= tuning_multiplier

        # Apply XG coarse/fine tuning
        coarse_offset = 2.0 ** (self.coarse_tune / 12.0)
        fine_multiplier = 2.0 ** (self.fine_tune / 1200.0)
        base_freq *= coarse_offset * fine_multiplier

        # XG Key scaling (note-dependence of pitch)
        if self.key_scaling != 0.0:
            # XG formula: pitch varies linearly with note from center (note 60)
            key_offset = (self.note - 60) * (self.key_scaling / 1200.0)
            freq_multiplier = 2.0 ** key_offset
            base_freq *= freq_multiplier

        # No wavetable? Use zero sample fallback
        if self.wavetable is None:
            # Create a 1-sample zero table for silent fallback
            self._cached_sample_table = [(0.0, 0.0)]  # 1-sample stereo zero table
            return base_freq * 1 / self.sample_rate  # Phase step for 1-sample table

        # Get XG wavetable sample for this partial - use cached table
        sample_table = self._cached_sample_table

        if sample_table is None or len(sample_table) == 0:
            # No sample table available - use zero sample fallback
            # Don't set active=False, as we can still generate silence
            return base_freq * 1 / self.sample_rate  # Phase step for 1-sample table

        # Calculate phase step for wavetable playback
        table_length = len(sample_table)
        return base_freq * table_length / self.sample_rate

    def _load_sample_table_once(self):
        """Load sample table once during construction (XG partials never change sample table)."""
        if not self.wavetable:
            return

        # Get sample table from wavetable manager (only called once)
        sample_table = self.wavetable.get_partial_table(
            self.note, self.program, self.partial_id,
            self.velocity, self.bank
        )

        # Cache the sample table
        self._cached_sample_table = sample_table

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
            # Store loop information from SF2 sample header
            self.sample_start = header.start
            self.sample_end = header.end
            self.loop_start = header.start_loop
            self.loop_end = header.end_loop

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
        else:
            # No loop information available
            self.loop_mode = 0

    def _initialize_envelopes(self, partial_params: Dict):
        """Initialize XG-compliant envelopes with proper parameter scaling."""
        # XG Amplitude Envelope - always present
        self.amp_envelope = VectorizedADSREnvelope(
            delay=self.amp_delay_time,
            attack=self.amp_attack_time,
            hold=self.amp_hold_time,
            decay=self.amp_decay_time,
            sustain=self.amp_sustain_level,
            release=self.amp_release_time,
            velocity_sense=self._calculate_velocity_sense(),  # XG formula
            key_scaling=0.0,  # XG envelope key scaling handled separately
            sample_rate=self.sample_rate
        )

        # XG Filter Envelope - optional for drums
        if self.use_filter_env:
            self.filter_envelope = VectorizedADSREnvelope(
                delay=self.filter_delay_time,
                attack=self.filter_attack_time,
                hold=self.filter_hold_time,
                decay=self.filter_decay_time,
                sustain=self.filter_sustain_level,
                release=self.filter_release_time,
                velocity_sense=0.0,  # XG filter env typically not velocity-sensitive
                key_scaling=0.0,
                sample_rate=self.sample_rate
            )
        else:
            self.filter_envelope = None

        # XG Pitch Envelope - optional for drums
        if self.use_pitch_env:
            self.pitch_envelope = VectorizedADSREnvelope(
                delay=self.pitch_delay_time,
                attack=self.pitch_attack_time,
                hold=self.pitch_hold_time,
                decay=self.pitch_decay_time,
                sustain=self.pitch_sustain_level,  # Fixed level per XG
                release=self.pitch_release_time,
                velocity_sense=0.0,  # XG pitch env typically not velocity-sensitive
                key_scaling=0.0,
                sample_rate=self.sample_rate
            )
        else:
            self.pitch_envelope = None

    def _initialize_filter(self):
        """Initialize XG-compliant filter."""
        self.filter = ResonantFilter(
            cutoff=self.filter_cutoff,
            resonance=self.filter_resonance,
            filter_type=self.filter_type,
            key_follow=self.filter_key_follow,
            stereo_width=1.0,  # Enable stereo processing for partials
            sample_rate=self.sample_rate
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
                self.amp_envelope.state != "idle")

    def generate_sample(self, lfos: List, global_pitch_mod: float = 0.0,
                        velocity_crossfade: float = 0.0, note_crossfade: float = 0.0) -> Tuple[float, float]:
        """
        Generate XG partial audio sample.

        Args:
            lfos: Channel-level LFO sources (per XG architecture)
            global_pitch_mod: Global pitch modulation (pitch bend, etc.)
            velocity_crossfade: Velocity crossfade coefficient
            note_crossfade: Note crossfade coefficient

        Returns:
            Tuple of (left_sample, right_sample) in range [-1.0, 1.0]
        """
        if not self.is_active():
            return (0.0, 0.0)

        # Update crossfade coefficients
        self.velocity_crossfade = velocity_crossfade
        self.note_crossfade = note_crossfade

        # Process XG envelopes
        amp_env = self.amp_envelope.process()
        filter_env = self.filter_envelope.process() if self.filter_envelope else 0.0
        pitch_env = self.pitch_envelope.process() if self.pitch_envelope else 0.0

        # Apply XG key follow to envelopes (envelope variation with note)
        key_follow_factor = self._calculate_key_follow_factor()

        # XG Amplitude envelope scaling (only affects amp env)
        amp_env *= key_follow_factor

        # Generate base waveform with pitch modulation
        pitch_mod_total = (global_pitch_mod +
                          self.last_pitch_mod +
                          self._process_pitch_envelope(pitch_env))

        sample = self._generate_waveform_sample(pitch_mod_total)

        # Apply XG filter with envelope modulation
        if self.filter:
            # XG Filter envelope to cutoff modulation (±4800 cents range typically)
            filter_cutoff_mod = filter_env * 4800.0 * self.last_filter_mod
            filter_cutoff_freq = self._calculate_xg_filter_cutoff(filter_cutoff_mod)

            self.filter.set_parameters(
                cutoff=filter_cutoff_freq,
                resonance=self.filter_resonance
            )

            # Now sample is always stereo, so process as stereo
            sample = self.filter.process(sample, is_stereo=True)

        # Apply XG amplitude envelope and level
        # Sample is now always stereo (left, right)
        if isinstance(sample, (tuple, list)) and len(sample) >= 2:
            left_sample = float(sample[0])
            right_sample = float(sample[1])
        else:
            # Fallback: if somehow not stereo, treat as mono and convert
            mono_sample = float(sample[0]) if isinstance(sample, (tuple, list)) else float(sample)
            left_sample = mono_sample
            right_sample = mono_sample

        # Apply amplitude envelope and level to both channels
        left_sample = left_sample * float(amp_env) * float(self.level) * float(self.last_amp_mod)
        right_sample = right_sample * float(amp_env) * float(self.level) * float(self.last_amp_mod)

        # Apply crossfade to both channels
        crossfade_factor = (1.0 - self.velocity_crossfade) * (1.0 - self.note_crossfade)
        left_sample *= crossfade_factor
        right_sample *= crossfade_factor

        # Apply XG panning - OPTIMIZED
        # Use pre-computed panning coefficients instead of expensive sqrt() calls
        pan_int = int(self.pan * 127.0)  # Convert to MIDI range
        pan_int = max(0, min(127, pan_int))
        left_gain, right_gain = self.coeff_manager.get_pan_gains(pan_int)

        left_sample *= left_gain
        right_sample *= right_gain

        return (left_sample, right_sample)

    def generate_sample_block(self, block_size: int, lfos: List,
                             global_pitch_mod: float = 0.0,
                             velocity_crossfade: float = 0.0,
                             note_crossfade: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate XG partial audio block with vectorized processing.

        Args:
            block_size: Number of samples to generate
            lfos: Channel-level LFO sources (per XG architecture)
            global_pitch_mod: Global pitch modulation (pitch bend, etc.)
            velocity_crossfade: Velocity crossfade coefficient
            note_crossfade: Note crossfade coefficient

        Returns:
            Tuple of (left_block, right_block) numpy arrays
        """
        if not self.is_active():
            return (np.zeros(block_size, dtype=np.float32),
                   np.zeros(block_size, dtype=np.float32))

        # Update crossfade coefficients
        self.velocity_crossfade = velocity_crossfade
        self.note_crossfade = note_crossfade

        # Generate envelope blocks
        amp_env_block = self._generate_envelope_block(block_size, 'amp')
        filter_env_block = self._generate_envelope_block(block_size, 'filter')
        pitch_env_block = self._generate_envelope_block(block_size, 'pitch')

        # Apply XG key follow to envelopes (envelope variation with note)
        key_follow_factor = self._calculate_key_follow_factor()
        amp_env_block *= key_follow_factor

        # Generate base waveform block with pitch modulation
        pitch_mod_total = (global_pitch_mod +
                          self.last_pitch_mod +
                          self._process_pitch_envelope_block(pitch_env_block))

        # For now, use constant pitch modulation across block
        # TODO: Implement time-varying pitch modulation
        pitch_mod_constant = float(pitch_mod_total[0]) if len(pitch_mod_total) > 0 else 0.0
        left_block, right_block = self._generate_waveform_block(block_size, pitch_mod_constant)

        # Apply XG filter with envelope modulation
        if self.filter:
            # XG Filter envelope to cutoff modulation (±4800 cents range typically)
            filter_cutoff_mod_block = filter_env_block * 4800.0 * self.last_filter_mod
            filter_cutoff_freq_block = self._calculate_xg_filter_cutoff_block(filter_cutoff_mod_block)

            # Apply filter to entire block
            left_block, right_block = self._apply_filter_block(
                left_block, right_block, filter_cutoff_freq_block)

        # Apply amplitude envelope and level to both channels
        amp_env_block = amp_env_block * float(self.level) * float(self.last_amp_mod)
        left_block *= amp_env_block
        right_block *= amp_env_block

        # Apply crossfade to both channels
        crossfade_factor = (1.0 - self.velocity_crossfade) * (1.0 - self.note_crossfade)
        left_block *= crossfade_factor
        right_block *= crossfade_factor

        # Apply XG panning - OPTIMIZED
        # Use pre-computed panning coefficients
        pan_int = int(self.pan * 127.0)
        pan_int = max(0, min(127, pan_int))
        left_gain, right_gain = self.coeff_manager.get_pan_gains(pan_int)

        left_block *= left_gain
        right_block *= right_gain

        return left_block, right_block

    def _calculate_key_follow_factor(self) -> float:
        """Calculate XG envelope key follow factor."""
        # XG standard: envelopes vary by ±88.02 cents over 10 octaves
        # Simplified implementation: linear variation from note 21 to 108
        key_follow_range = 1.059463  # 2^(88.02/1200) ≈ 1.0595
        center_note = 60
        note_distance = abs(self.note - center_note)

        if note_distance == 0:
            return 1.0

        exponent = (note_distance / (108 - 21)) * math.log2(key_follow_range)
        return 2.0 ** exponent if self.note < center_note else 1.0 / (2.0 ** exponent)

    def _process_pitch_envelope(self, pitch_env: float) -> float:
        """Process XG pitch envelope (fixed sustain level)."""
        # XG pitch envelope has fixed sustain level (typically 0)
        if self.pitch_envelope and self.pitch_envelope.state == "sustain":
            return 0.0  # Fixed sustain per XG spec
        return pitch_env * 1200.0  # Convert to cents

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

    def _generate_envelope_block(self, block_size: int, envelope_type: str) -> np.ndarray:
        """Generate envelope values for entire block using vectorized processing."""
        if envelope_type == 'amp' and self.amp_envelope:
            return self.amp_envelope.process_block_vectorized(block_size)
        elif envelope_type == 'filter' and self.filter_envelope:
            return self.filter_envelope.process_block_vectorized(block_size)
        elif envelope_type == 'pitch' and self.pitch_envelope:
            return self.pitch_envelope.process_block_vectorized(block_size)
        else:
            return np.zeros(block_size, dtype=np.float32)

    def _process_pitch_envelope_block(self, pitch_env_block: np.ndarray) -> np.ndarray:
        """Process XG pitch envelope for block (fixed sustain level)."""
        # XG pitch envelope has fixed sustain level (typically 0)
        result = np.zeros_like(pitch_env_block)
        if self.pitch_envelope and self.pitch_envelope.state == "sustain":
            # Fixed sustain per XG spec
            result.fill(0.0)
        else:
            # Convert to cents and apply
            result = pitch_env_block * 1200.0
        return result

    def _generate_waveform_block(self, block_size: int, pitch_mod: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generate entire sample block for XG synthesis with SF2 loop handling."""
        left_block = np.zeros(block_size, dtype=np.float32)
        right_block = np.zeros(block_size, dtype=np.float32)

        # Generate sample based on wavetable availability
        if self.wavetable is None:
            # Zero sample fallback - return stereo silence
            return left_block, right_block

        # XG Wavetable synthesis - use cached sample table
        sample_table = self._cached_sample_table

        if not sample_table or len(sample_table) == 0:
            return left_block, right_block

        # Apply pitch modulation to phase step
        modulation_mult = 2.0 ** (pitch_mod / 1200.0)
        current_phase_step = self.phase_step * modulation_mult

        # Generate block of samples
        for i in range(block_size):
            # Calculate table index with loop handling
            table_length = len(sample_table)
            raw_index = self.phase * table_length / (2.0 * math.pi)

            # Apply SF2 loop wrapping based on loop mode
            table_index = self._apply_sf2_looping(raw_index, table_length)

            # Ensure index is within bounds
            table_index = max(0, min(table_index, table_length - 1))

            # Linear interpolation for smooth playback
            index_int = int(table_index)
            frac = table_index - index_int

            # Get samples with bounds checking
            sample1 = sample_table[index_int] if index_int < table_length else 0.0
            sample2 = sample_table[min(index_int + 1, table_length - 1)] if index_int < table_length else 0.0

            # Get stereo samples
            def get_stereo_sample(sample):
                if isinstance(sample, tuple):
                    left, right = sample
                    return (left, right)
                else:
                    return (sample, sample)

            stereo1 = get_stereo_sample(sample1)
            stereo2 = get_stereo_sample(sample2)

            # Linear interpolation for both channels
            left_interp = stereo1[0] + frac * (stereo2[0] - stereo1[0])
            right_interp = stereo1[1] + frac * (stereo2[1] - stereo1[1])

            left_block[i] = left_interp
            right_block[i] = right_interp

            # Update phase
            self.phase += current_phase_step
            if self.phase > 2.0 * math.pi:
                self.phase -= 2.0 * math.pi

        return left_block, right_block

    def _calculate_xg_filter_cutoff_block(self, env_mod_cents_block: np.ndarray) -> np.ndarray:
        """Calculate XG filter cutoff with envelope modulation for block."""
        base_freq = self.filter_cutoff

        # Apply key follow per XG formula: ±24 semitones range
        key_follow_semitones = (self.note - 60) * self.filter_key_follow
        key_follow_mult = 2.0 ** (key_follow_semitones / 12.0)

        # Apply envelope modulation
        env_mult_block = 2.0 ** (env_mod_cents_block / 1200.0)

        final_freq_block = base_freq * key_follow_mult * env_mult_block

        # XG-compliant frequency clamping
        return np.clip(final_freq_block, 20.0, 20000.0)

    def _apply_filter_block(self, left_block: np.ndarray, right_block: np.ndarray,
                            cutoff_freq_block: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply filter to entire block with varying cutoff frequencies."""
        # For now, use the first cutoff frequency for the whole block
        # TODO: Implement time-varying filter for better quality
        cutoff_freq = cutoff_freq_block[0] if len(cutoff_freq_block) > 0 else self.filter_cutoff

        if self.filter:
            self.filter.set_parameters(
                cutoff=cutoff_freq,
                resonance=self.filter_resonance
            )

            # Process each sample individually (filter doesn't support block processing yet)
            filtered_left = np.zeros_like(left_block)
            filtered_right = np.zeros_like(right_block)

            for i in range(len(left_block)):
                # Process stereo sample
                filtered_sample = self.filter.process((left_block[i], right_block[i]), is_stereo=True)
                filtered_left[i] = filtered_sample[0]
                filtered_right[i] = filtered_sample[1]

            return filtered_left, filtered_right

        return left_block, right_block

    def _apply_sf2_looping(self, raw_index: float, table_length: int) -> float:
        """Apply SF2 loop wrapping based on loop mode."""
        if self.loop_mode == 0 or self.loop_end <= self.loop_start:
            return raw_index

        loop_start = float(self.loop_start)
        loop_end = float(self.loop_end)
        loop_length = loop_end - loop_start

        if loop_length > 0:
            if self.loop_mode == 1:  # Forward loop
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    return loop_start + (excess % loop_length)
                elif raw_index < loop_start:
                    return loop_start
                else:
                    return raw_index

            elif self.loop_mode == 2:  # Backward loop
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    backward_pos = loop_length - (excess % loop_length)
                    return loop_start + backward_pos
                elif raw_index < loop_start:
                    return loop_end - 1
                else:
                    return loop_end - (raw_index - loop_start)

            elif self.loop_mode == 3:  # Alternating loop (ping-pong)
                if raw_index >= loop_end:
                    excess = raw_index - loop_end
                    self.loop_direction = -1  # Switch to backward
                    backward_pos = excess % loop_length
                    return loop_end - backward_pos
                elif raw_index < loop_start:
                    excess = loop_start - raw_index
                    self.loop_direction = 1  # Switch to forward
                    return loop_start + (excess % loop_length)
                else:
                    if self.loop_direction > 0:  # Forward
                        return raw_index
                    else:  # Backward
                        return loop_end - (raw_index - loop_start)

        return raw_index

    def _generate_waveform_sample(self, pitch_mod: float) -> Tuple[float, float]:
        """Generate base waveform sample for XG synthesis with proper SF2 loop handling.

        Returns stereo samples (left, right) - converts mono to stereo if needed.
        """
        # Apply pitch modulation to phase step
        modulation_mult = 2.0 ** (pitch_mod / 1200.0)  # cents to freq multiplier
        current_phase_step = self.phase_step * modulation_mult

        # Generate sample based on wavetable availability
        if self.wavetable is None:
            # Zero sample fallback - return stereo silence
            # For 1-sample zero table, always return the same sample
            return (0.0, 0.0)  # Return stereo silence

        # XG Wavetable synthesis - use cached sample table
        sample_table = self._cached_sample_table

        if not sample_table or len(sample_table) == 0:
            return (0.0, 0.0)  # Return stereo silence

        # Calculate table index with loop handling
        table_length = len(sample_table)
        raw_index = self.phase * table_length / (2.0 * math.pi)

        # Apply SF2 loop wrapping based on loop mode
        if self.loop_mode > 0 and self.loop_end > self.loop_start:
            # Convert loop points from sample space to table index space
            loop_start_idx = float(self.loop_start)
            loop_end_idx = float(self.loop_end)

            # Ensure loop points are within table bounds
            loop_start_idx = max(0.0, min(loop_start_idx, table_length - 1))
            loop_end_idx = max(loop_start_idx + 1, min(loop_end_idx, table_length - 1))
            loop_length = loop_end_idx - loop_start_idx

            if loop_length > 0:
                if self.loop_mode == 1:  # Forward loop
                    # Standard forward loop
                    if raw_index >= loop_end_idx:
                        excess = raw_index - loop_end_idx
                        table_index = loop_start_idx + (excess % loop_length)
                    elif raw_index < loop_start_idx:
                        # Before loop start - could clamp or wrap
                        table_index = loop_start_idx
                    else:
                        table_index = raw_index

                elif self.loop_mode == 2:  # Backward loop
                    # Backward loop - play from end to start repeatedly
                    if raw_index >= loop_end_idx:
                        excess = raw_index - loop_end_idx
                        # Calculate position from end
                        backward_pos = loop_length - (excess % loop_length)
                        table_index = loop_start_idx + backward_pos
                    elif raw_index < loop_start_idx:
                        table_index = loop_end_idx - 1  # Start from end
                    else:
                        # Within loop - play backward from current position
                        table_index = loop_end_idx - (raw_index - loop_start_idx)

                elif self.loop_mode == 3:  # Alternating loop (ping-pong)
                    # Alternating between forward and backward
                    if raw_index >= loop_end_idx:
                        # Reached end - switch to backward and calculate position
                        excess = raw_index - loop_end_idx
                        self.loop_direction = -1  # Switch to backward
                        # Position from end
                        backward_pos = excess % loop_length
                        table_index = loop_end_idx - backward_pos
                    elif raw_index < loop_start_idx:
                        # Reached start - switch to forward
                        excess = loop_start_idx - raw_index
                        self.loop_direction = 1  # Switch to forward
                        table_index = loop_start_idx + (excess % loop_length)
                    else:
                        # Within loop - continue in current direction
                        if self.loop_direction > 0:  # Forward
                            table_index = raw_index
                        else:  # Backward
                            table_index = loop_end_idx - (raw_index - loop_start_idx)
                else:
                    # Unknown loop mode - default to forward
                    table_index = raw_index
            else:
                # Invalid loop - no looping
                table_index = max(0.0, min(raw_index, table_length - 1))
        else:
            # No loop - use raw index
            table_index = raw_index

        # Ensure index is within bounds
        table_index = max(0, min(table_index, table_length - 1))

        # Linear interpolation for smooth playback
        index_int = int(table_index)
        frac = table_index - index_int

        # Get samples with bounds checking
        sample1 = sample_table[index_int] if index_int < table_length else 0.0
        sample2 = sample_table[min(index_int + 1, table_length - 1)] if index_int < table_length else 0.0

        # Get stereo samples instead of mono
        def get_stereo_sample(sample):
            if isinstance(sample, tuple):
                left, right = sample
                return (left, right)
            else:
                return (sample, sample)

        stereo1 = get_stereo_sample(sample1)
        stereo2 = get_stereo_sample(sample2)

        # Linear interpolation for both channels
        left_interp = stereo1[0] + frac * (stereo2[0] - stereo1[0])
        right_interp = stereo1[1] + frac * (stereo2[1] - stereo1[1])

        return (left_interp, right_interp)

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



# Backward compatibility alias
PartialGenerator = XGPartialGenerator
