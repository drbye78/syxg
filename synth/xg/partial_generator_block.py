"""
Block-optimized Partial Generator for XG synthesizer.
Provides high-performance partial synthesis with vectorized processing.
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from ..core.oscillator import LFO
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner
from ..core.envelope_block import BlockADSREnvelope
from ..core.object_pool import acquire_resonant_filter, release_resonant_filter


class BlockPartialGenerator:
    """
    Block-optimized partial generator for XG sound synthesis.
    Processes audio in blocks while maintaining sample-accurate timing.
    """

    def __init__(self, wavetable, note: int, velocity: int, program: int, partial_id: int,
                 partial_params: Dict[str, Any], is_drum: bool = False, sample_rate: int = 44100,
                 block_size: int = 128):
        """
        Initialize block-based partial generator.

        Args:
            wavetable: Wavetable manager instance
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            program: MIDI program number
            partial_id: Partial structure identifier
            partial_params: Partial structure parameters
            is_drum: Whether this is a drum partial
            sample_rate: Audio sample rate
            block_size: Processing block size for optimization
        """
        self.wavetable = wavetable
        self.note = note
        self.velocity = velocity
        self.program = program
        self.partial_id = partial_id
        self.is_drum = is_drum
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Active state
        self.active = True

        # Partial parameters
        self.level = partial_params.get("level", 1.0)
        self.pan = partial_params.get("pan", 0.5)
        self.key_range_low = partial_params.get("key_range_low", 0)
        self.key_range_high = partial_params.get("key_range_high", 127)
        self.velocity_range_low = partial_params.get("velocity_range_low", 0)
        self.velocity_range_high = partial_params.get("velocity_range_high", 127)

        # Check key and velocity range
        if not (self.key_range_low <= note <= self.key_range_high):
            self.active = False
            return

        if not (self.velocity_range_low <= velocity <= self.velocity_range_high):
            self.active = False
            return

        # Initialize phase tracking for wavetable synthesis
        self.phase = 0.0
        self.phase_step = 0.0
        self._update_phase_step()

        # Initialize amplitude envelope (block-optimized)
        amp_env_params = partial_params.get("amp_envelope", {})
        self.amp_envelope = BlockADSREnvelope(
            delay=amp_env_params.get("delay", 0.0),
            attack=amp_env_params.get("attack", 0.01),
            hold=amp_env_params.get("hold", 0.0),
            decay=amp_env_params.get("decay", 0.3),
            sustain=amp_env_params.get("sustain", 0.7),
            release=amp_env_params.get("release", 0.5),
            velocity_sense=partial_params.get("velocity_sense", 1.0),
            key_scaling=amp_env_params.get("key_scaling", 0.0),
            sample_rate=sample_rate
        )

        # Initialize filter envelope if used
        if partial_params.get("use_filter_env", True):
            filter_env_params = partial_params.get("filter_envelope", {})
            self.filter_envelope = BlockADSREnvelope(
                delay=filter_env_params.get("delay", 0.0),
                attack=filter_env_params.get("attack", 0.1),
                hold=filter_env_params.get("hold", 0.0),
                decay=filter_env_params.get("decay", 0.5),
                sustain=filter_env_params.get("sustain", 0.6),
                release=filter_env_params.get("release", 0.8),
                key_scaling=filter_env_params.get("key_scaling", 0.0),
                sample_rate=sample_rate
            )
        else:
            self.filter_envelope = None

        # Initialize filter (pooled)
        filter_params = partial_params.get("filter", {})
        self.filter = acquire_resonant_filter(
            cutoff=filter_params.get("cutoff", 1000.0),
            resonance=filter_params.get("resonance", 0.7),
            # filter_type=filter_params.get("type", "lowpass"),  # TODO: Add to ResonantFilter
            # key_follow=filter_params.get("key_follow", 0.5),
            sample_rate=sample_rate
        )

        # Pre-allocate block buffers for vectorized processing
        self._oscillator_buffer = np.zeros(block_size, dtype=np.float32)
        self._envelope_buffer = np.zeros(block_size, dtype=np.float32)
        self._filter_buffer = np.zeros(block_size, dtype=np.float32)
        self._left_output_buffer = np.zeros(block_size, dtype=np.float32)
        self._right_output_buffer = np.zeros(block_size, dtype=np.float32)

        # Enhanced panning (cached for performance)
        self.panner = StereoPanner(pan_position=self.pan, sample_rate=sample_rate)

        # Attenuation and scaling factors
        self.initial_attenuation_db = partial_params.get("initial_attenuation", 0.0)  # in dB
        self.scale_tuning = partial_params.get("scale_tuning", 100)  # in cents
        self.coarse_tune = partial_params.get("coarse_tune", 0)
        self.fine_tune = partial_params.get("fine_tune", 0)

        # Convert dB to linear scale
        self.initial_attenuation_factor = 10 ** (-self.initial_attenuation_db / 20.0)

    def _update_phase_step(self):
        """Update oscillator phase step based on note and tuning"""
        if self.wavetable is None:
            # Basic sine wave generation
            root_key = self.note
            base_freq = 440.0 * (2 ** ((root_key - 69) / 12.0))

            # Apply scale tuning (cents to frequency ratio)
            tuning_ratio = 2 ** (self.scale_tuning / 1200.0)
            base_freq *= tuning_ratio

            # Apply coarse and fine tuning
            tuning_cents = self.coarse_tune * 100 + self.fine_tune
            base_freq *= 2 ** (tuning_cents / 1200.0)

            self.phase_step = base_freq / self.sample_rate * 2 * math.pi

        else:
            # Wavetable-based synthesis
            # Update phase step based on wavetable requirements
            table = self.wavetable.get_partial_table(
                self.note, self.program, self.partial_id, self.velocity
            )

            if table is None or len(table) == 0:
                self.active = False
                return

            # Calculate frequency based on note and tuning
            root_key = self.note
            base_freq = 440.0 * (2 ** ((root_key - 69) / 12.0))

            # Apply scale tuning and fine/coarse tuning
            tuning_cents = self.scale_tuning + self.coarse_tune * 100 + self.fine_tune
            base_freq *= 2 ** (tuning_cents / 1200.0)

            # Calculate phase step for wavetable
            table_length = len(table)
            self.phase_step = base_freq / self.sample_rate * table_length

    def is_active(self) -> bool:
        """Check if partial generator is still active"""
        return self.active and self.amp_envelope and self.amp_envelope.state != "idle"

    def note_off(self):
        """Handle note off event"""
        if self.is_active():
            self.amp_envelope.note_off()
            if self.filter_envelope:
                self.filter_envelope.note_off()

    def process_block(self, block_size: int,
                     midi_events: List[Dict[str, Any]] = None,
                     lfo_values: np.ndarray = None,
                     global_pitch_mod: float = 0.0,
                     filter_cutoff_mod: float = 0.0,
                     amp_mod: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process a block of audio samples with optimization.

        Args:
            block_size: Number of samples to process
            midi_events: MIDI events within this block
            lfo_values: LFO modulation values (block_size array)
            global_pitch_mod: Global pitch modulation
            filter_cutoff_mod: Filter cutoff modulation
            amp_mod: Amplitude modulation

        Returns:
            Tuple of (left_samples, right_samples) arrays
        """
        if not self.is_active():
            return np.zeros(block_size, dtype=np.float32), np.zeros(block_size, dtype=np.float32)

        # Generate oscillator/wavetable samples
        self._generate_oscillator_block(block_size, global_pitch_mod, lfo_values)

        # Process amplitude envelope
        self._envelope_buffer[:] = self.amp_envelope.process_block(
            block_size, self.velocity, self.note, midi_events
        )
        self._envelope_buffer *= amp_mod

        # Generate samples early exit for silent envelope
        if np.max(np.abs(self._envelope_buffer)) < 1e-6:
            return np.zeros(block_size, dtype=np.float32), np.zeros(block_size, dtype=np.float32)

        # Apply amplitude envelope
        self._oscillator_buffer *= self._envelope_buffer

        # Process filter if active
        if self.filter is not None:
            # Process filter envelope if available
            if self.filter_envelope:
                filter_env = self.filter_envelope.process_block(
                    block_size, self.velocity, self.note, midi_events
                )
                # Apply filter envelope modulation
                current_cutoff = self.filter.cutoff

                # Calculate modulated cutoff with envelope
                modulated_cutoff = current_cutoff * (0.5 + filter_env * 0.5)
                modulated_cutoff *= (1.0 + filter_cutoff_mod)

                # Update filter parameters
                try:
                    if hasattr(self.filter, 'set_cutoff'):
                        self.filter.set_cutoff(modulated_cutoff)
                except Exception:
                    pass  # Filter might not support dynamic updates

            # Apply filter to oscillator buffer
            # For now, we'll assume the filter can process the entire block
            # TODO: Implement proper block filtering
            self._filter_buffer[:] = self._oscillator_buffer  # Placeholder

        else:
            self._filter_buffer[:] = self._oscillator_buffer

        # Apply initial attenuation
        self._filter_buffer *= self.initial_attenuation_factor

        # Apply partial level
        self._filter_buffer *= self.level

        # Pan the signal using cached panner
        self._left_output_buffer[:], self._right_output_buffer[:] = self.panner.process_block(
            self._filter_buffer, block_size
        )

        return self._left_output_buffer.copy(), self._right_output_buffer.copy()

    def _generate_oscillator_block(self, block_size: int,
                                  global_pitch_mod: float,
                                  lfo_values: np.ndarray = None):
        """Generate oscillator/wavetable samples for the entire block"""

        if self.wavetable is None:
            # Generate sine wave
            self._generate_sine_block(block_size, global_pitch_mod, lfo_values)

        else:
            # Generate wavetable samples
            self._generate_wavetable_block(block_size, global_pitch_mod, lfo_values)

    def _generate_sine_block(self, block_size: int,
                            global_pitch_mod: float,
                            lfo_values: np.ndarray = None):
        """Generate sine wave samples for the block"""
        # Apply pitch modulation to phase step
        modulated_phase_step = self.phase_step * (1.0 + global_pitch_mod)

        # Generate phase values for the entire block
        phase_values = np.arange(block_size, dtype=np.float32)
        phase_values = self.phase + phase_values * modulated_phase_step

        # Apply LFO modulation if available
        if lfo_values is not None:
            pitch_lfo_mod = lfo_values * 0.1  # Scale LFO pitch modulation
            phase_values *= (1.0 + pitch_lfo_mod)

        # Generate sine wave
        self._oscillator_buffer[:] = np.sin(phase_values)

        # Update phase for next block (wrap around)
        self.phase = phase_values[-1] % (2 * math.pi)

    def _generate_wavetable_block(self, block_size: int,
                                 global_pitch_mod: float,
                                 lfo_values: np.ndarray = None):
        """Generate wavetable samples for the block"""
        # Get wavetable data
        table = self.wavetable.get_partial_table(
            self.note, self.program, self.partial_id, self.velocity
        )

        if table is None or len(table) == 0:
            self._oscillator_buffer.fill(0.0)
            return

        table_length = len(table)

        # Apply pitch modulation to phase step
        modulated_phase_step = self.phase_step * (1.0 + global_pitch_mod)

        # Generate wavetable indices for the entire block
        indices = np.arange(block_size, dtype=np.float32)
        phase_values = self.phase + indices * modulated_phase_step

        # Apply LFO modulation if available
        if lfo_values is not None:
            pitch_lfo_mod = lfo_values * 0.05  # Scale LFO pitch modulation
            phase_values *= (1.0 + pitch_lfo_mod)

        # Wrap phase to table length
        table_indices = phase_values % table_length

        # Interpolate wavetable values
        int_indices = table_indices.astype(np.int32)
        frac_parts = table_indices - int_indices

        # Linear interpolation
        next_indices = (int_indices + 1) % table_length

        try:
            if isinstance(table[0], (list, tuple)):
                # Stereo wavetable
                left_current = np.array([table[i][0] if i < table_length else 0.0
                                       for i in int_indices], dtype=np.float32)
                left_next = np.array([table[i][0] if i < table_length else 0.0
                                    for i in next_indices], dtype=np.float32)
                right_current = np.array([table[i][1] if i < table_length else 0.0
                                        for i in int_indices], dtype=np.float32)
                right_next = np.array([table[i][1] if i < table_length else 0.0
                                     for i in next_indices], dtype=np.float32)

                # Generate stereo output
                left_interp = left_current + frac_parts * (left_next - left_current)
                right_interp = right_current + frac_parts * (right_next - right_current)

                self._oscillator_buffer[:] = left_interp  # Use left channel for now
            else:
                # Mono wavetable
                current_values = np.array([table[int(i)] if int(i) < table_length else 0.0
                                         for i in int_indices], dtype=np.float32)
                next_values = np.array([table[int(i)] if int(i) < table_length else 0.0
                                       for i in next_indices], dtype=np.float32)

                # Linear interpolation
                self._oscillator_buffer[:] = current_values + frac_parts * (next_values - current_values)

        except (IndexError, TypeError):
            # Fallback to simple indexing if interpolation fails
            self._oscillator_buffer.fill(0.0)

        # Update phase for next block
        self.phase = table_indices[-1] % table_length

    def release_resources(self):
        """Release pooled resources"""
        if self.filter:
            release_resonant_filter(self.filter)
        self.filter = None

        # Clear references
        self.amp_envelope = None
        self.filter_envelope = None
        self.panner = None
