"""
XG Partial Generator - Production XG-Compliant Implementation

Implements XG Partial Structure concept with up to 8 partials per program.
Each partial has exclusive note/velocity ranges and independent XG parameters.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from ..core.vectorized_envelope import VectorizedADSREnvelope
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner


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

    def __init__(self, wavetable, note: int, velocity: int, program: int,
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
        self.wavetable = wavetable
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
        self.last_amp_mod = 0.0

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

        # No wavetable? Use basic sine wave synthesis
        if self.wavetable is None:
            return base_freq * 2.0 * math.pi / self.sample_rate

        # Get XG wavetable sample for this partial
        sample_table = self.wavetable.get_partial_table(
            self.note, self.program, self.partial_id,
            self.velocity, self.bank
        )

        if sample_table is None or len(sample_table) == 0:
            self.active = False
            return base_freq * 2.0 * math.pi / self.sample_rate

        # Get loop information from sample header
        self._load_sample_loop_info()

        # Calculate phase step for wavetable playback
        table_length = len(sample_table)
        return base_freq * table_length / self.sample_rate

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
            stereo_width=0.5,  # XG default stereo width
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

            sample = self.filter.process(sample, is_stereo=False)

        # Apply XG amplitude envelope and level
        # Handle case where sample might be a tuple (stereo) or float (mono)
        if isinstance(sample, (tuple, list)) and len(sample) >= 1:
            sample = float(sample[0])  # Take left channel if stereo
        else:
            sample = float(sample)

        sample = sample * float(amp_env) * float(self.level) * float(self.last_amp_mod)

        # Apply crossfade
        sample *= (1.0 - self.velocity_crossfade) * (1.0 - self.note_crossfade)

        # Apply XG panning
        left_sample = sample * math.sqrt(1.0 - self.pan)
        right_sample = sample * math.sqrt(self.pan)

        return (left_sample, right_sample)

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

    def _generate_waveform_sample(self, pitch_mod: float) -> float:
        """Generate base waveform sample for XG synthesis with proper SF2 loop handling."""
        # Apply pitch modulation to phase step
        modulation_mult = 2.0 ** (pitch_mod / 1200.0)  # cents to freq multiplier
        current_phase_step = self.phase_step * modulation_mult

        # Generate sample based on wavetable availability
        if self.wavetable is None:
            # Basic XG sine wave generation (fallback)
            self.phase += current_phase_step
            if self.phase > 2.0 * math.pi:
                self.phase -= 2.0 * math.pi
            return math.sin(self.phase)

        # XG Wavetable synthesis
        sample_table = self.wavetable.get_partial_table(
            self.note, self.program, self.partial_id,
            self.velocity, self.bank
        )

        if not sample_table or len(sample_table) == 0:
            return 0.0

        # Calculate table index with loop handling
        table_length = len(sample_table)
        raw_index = self.phase * table_length / (2.0 * math.pi)

        # Apply SF2 loop wrapping if loop is enabled
        if self.loop_mode > 0 and self.loop_end > self.loop_start:
            # Convert loop points from sample space to table index space
            loop_start_idx = self.loop_start
            loop_end_idx = self.loop_end

            # Ensure loop points are within table bounds
            loop_start_idx = max(0, min(loop_start_idx, table_length - 1))
            loop_end_idx = max(loop_start_idx + 1, min(loop_end_idx, table_length))

            # Apply loop wrapping
            if raw_index >= loop_end_idx:
                # Calculate how many loop lengths we've gone past the end
                loop_length = loop_end_idx - loop_start_idx
                if loop_length > 0:
                    # Wrap back into the loop
                    excess = raw_index - loop_end_idx
                    wrapped_index = loop_start_idx + (excess % loop_length)
                    table_index = wrapped_index
                else:
                    table_index = loop_end_idx - 1  # Stay at end if invalid loop
            elif raw_index < 0:
                # Handle negative indices (shouldn't happen in normal playback)
                table_index = 0
            else:
                table_index = raw_index
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

        # Handle stereo vs mono samples - always return mono for processing
        def safe_float_convert(value):
            """Safely convert any value to float."""
            if value is None:
                return 0.0
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    return float(value) if value else 0.0
                else:
                    return 0.0  # Unknown type, default to 0
            except (ValueError, TypeError):
                return 0.0

        def get_mono_sample(sample):
            """Extract mono sample from various sample formats."""
            if sample is None:
                return 0.0
            elif isinstance(sample, (tuple, list)):
                if len(sample) >= 2:
                    # Stereo - average channels
                    left = safe_float_convert(sample[0])
                    right = safe_float_convert(sample[1])
                    return (left + right) * 0.5
                elif len(sample) >= 1:
                    # Single channel in list/tuple
                    return safe_float_convert(sample[0])
                else:
                    return 0.0
            else:
                # Direct numeric value
                return safe_float_convert(sample)

        mono1 = get_mono_sample(sample1)
        mono2 = get_mono_sample(sample2)

        # Linear interpolation
        return mono1 + frac * (mono2 - mono1)

    # XG Sound Controller Parameter Updates (Controllers 71-78)

    def update_harmonic_content(self, value: float):
        """XG Sound Controller 71 - Harmonic Content (+/- 24 semitones)."""
        # Convert 0-127 MIDI to -24 to +24 semitone range
        semitones = ((value - 64) / 64.0) * 24.0
        # Apply to filter resonance (XG harmonic content mapping)
        self.filter_resonance = max(0.0, min(2.0, 0.7 + semitones * 0.05))

    def update_brightness(self, value: float):
        """XG Sound Controller 72 - Brightness (+/- 24 semitones)."""
        # Convert 0-127 MIDI to -24 to +24 semitone offset
        semitones = ((value - 64) / 64.0) * 24.0
        brightness_mult = 2.0 ** (semitones / 12.0)
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
        # 0-127 maps to 4 octaves (16:1 frequency ratio)
        freq_ratio = 2.0 ** ((value - 64) / 32.0)
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
        # 0-127 maps to 0.1 to 10.0 Hz logarithmically
        rate_hz = 0.1 * (10.0 ** (value * 2.0 / 127.0))
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
