"""
XG channel note implementation.

Provides classes for managing active notes on MIDI channels,
including partial synthesis and modulation routing.
"""

import math
import threading
from collections import OrderedDict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from synth.sf2.core.wavetable_manager import WavetableManager

from ..core.oscillator import XGLFO  # For note-level LFOs
from ..core.envelope import ADSREnvelope  # For note-level envelopes
from ..modulation.matrix import ModulationMatrix
# Import XGPartialGenerator dynamically to avoid circular imports
import importlib


class PartialGeneratorPool:
    """
    Object pool for XGPartialGenerator instances.

    Manages reusable partial generators to reduce allocation overhead
    during real-time audio synthesis. Thread-safe for concurrent access.
    """

    def __init__(self, max_size: int = 256):
        """
        Initialize partial generator pool.

        Args:
            max_size: Maximum number of partial generators to keep in pool
        """
        self.max_size = max_size
        self.pool = deque()
        self.lock = threading.Lock()
        self._stats = {
            "created": 0,
            "acquired": 0,
            "released": 0,
            "pool_hits": 0,
            "pool_misses": 0,
        }

    def acquire(
        self,
        synth,
        note: int,
        velocity: int,
        program: int,
        partial_id: int,
        partial_params: Dict,
        is_drum: bool = False,
        sample_rate: int = 44100,
        bank: int = 0,
        use_modulation_matrix: bool = False,
    ):
        """
        Acquire a partial generator from the pool or create new one.

        Args:
            synth: Synthesizer instance
            note: MIDI note number
            velocity: Note velocity
            program: Program number
            partial_id: Partial identifier
            partial_params: Partial parameters
            is_drum: Drum mode flag
            sample_rate: Audio sample rate
            bank: Bank number

        Returns:
            Configured XGPartialGenerator instance
        """
        with self.lock:
            self._stats["acquired"] += 1

            # Try to get from pool first
            if self.pool:
                partial = self.pool.popleft()
                self._stats["pool_hits"] += 1

                # Reconfigure existing partial with new parameters
                partial._reconfigure(
                    synth=synth,
                    note=note,
                    velocity=velocity,
                    program=program,
                    partial_id=partial_id,
                    partial_params=partial_params,
                    is_drum=is_drum,
                    sample_rate=sample_rate,
                    bank=bank,
                )
                return partial

            # Pool empty, create new partial
            self._stats["pool_misses"] += 1
            self._stats["created"] += 1

            # Dynamic import to avoid circular import
            partial_generator_module = importlib.import_module('synth.partial.partial_generator')
            XGPartialGenerator = partial_generator_module.XGPartialGenerator

            return XGPartialGenerator(
                synth=synth,
                note=note,
                velocity=velocity,
                program=program,
                partial_id=partial_id,
                partial_params=partial_params,
                is_drum=is_drum,
                sample_rate=sample_rate,
                bank=bank,
                use_modulation_matrix=use_modulation_matrix,
            )

    def release(self, partial) -> None:
        """
        Return a partial generator to the pool for reuse.

        Args:
            partial: Partial generator to return
        """
        if partial is None:
            return

        with self.lock:
            self._stats["released"] += 1

            # Reset partial state for reuse
            partial._reset_for_pool()

            # Only keep in pool if under max size
            if len(self.pool) < self.max_size:
                self.pool.append(partial)
            else:
                # Pool full, cleanup this partial
                partial.cleanup()

    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics for monitoring."""
        with self.lock:
            stats = self._stats.copy()
            stats["pool_size"] = len(self.pool)
            stats["max_size"] = self.max_size
            return stats

    def clear_pool(self) -> None:
        """Clear all partial generators from pool."""
        with self.lock:
            while self.pool:
                partial = self.pool.popleft()
                partial.cleanup()
            self._stats = {
                "created": 0,
                "acquired": 0,
                "released": 0,
                "pool_hits": 0,
                "pool_misses": 0,
            }


class ChannelNote:
    """
    Represents an active note on a MIDI channel.

    Manages partial synthesis, modulation routing, and LFO processing
    for a single note. Supports up to 8 partials per note.

    Attributes:
        note: MIDI note number (0-127)
        velocity: Note velocity (0-127)
        program: Program number (0-127)
        bank: Bank number (0-16383)
        is_drum: True for drum mode, False for melodic
        active: True if note is still producing sound
        partials: List of partial generators
        mod_matrix: Per-note modulation routing
    """

    def __init__(
        self,
        channel,
        note: int,
        velocity: int,
        program: int,
        bank: int,
        is_drum: bool = False,
        synth=None,  # Reference to synthesizer for pool access
        use_modulation_matrix: bool = False,
    ):
        # Input validation
        if not (0 <= note <= 127):
            raise ValueError(f"Note must be between 0-127, got {note}")
        if not (0 <= velocity <= 127):
            raise ValueError(f"Velocity must be between 0-127, got {velocity}")
        if not (0 <= program <= 127):
            raise ValueError(f"Program must be between 0-127, got {program}")
        if not (0 <= bank <= 16383):  # XG supports up to 14-bit bank numbers
            raise ValueError(f"Bank must be between 0-16383, got {bank}")

        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.active = True
        self.channel = channel
        self.synth = synth  # Store synthesizer reference for pool access
        self.sample_rate = channel.sample_rate
        self.use_modulation_matrix = use_modulation_matrix
        self.detune = 0.0
        self.phaser_depth = 0.0

        self.channel_lfos = channel.lfos
        self.params = self._get_parameters(program, bank, note, velocity, is_drum)
        self.note_lfos = []
        self._initialize_note_lfos()
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()

        self.modulation_sources = {
            "velocity": 0.0,
            "after_touch": 0.0,
            "mod_wheel": 0.0,
            "breath_controller": 0.0,
            "foot_controller": 0.0,
            "data_entry": 100 / 127.0,  # Default data entry value
            "lfo1": 0.0,
            "lfo2": 0.0,
            "lfo3": 0.0,
            "note_lfo1": 0.0,  # Note-level LFOs
            "note_lfo2": 0.0,
            "note_lfo3": 0.0,
            "amp_env": 0.0,
            "filter_env": 0.0,
            "pitch_env": 0.0,
            "key_pressure": 0.0,
            "brightness": 0.0,
            "harmonic_content": 0.0,
            "portamento": 1.0,  # Default portamento is active
            "vibrato": 0.5,  # Default vibrato
            "tremolo": 0.0,
            "tremolo_depth": 0.3,
            "tremolo_rate": 4.0,
            "note_number": 0.0,
            "volume_cc": 0.0,  # Use passed volume parameter
            "balance": 0.0,  # Default balance
            "portamento_time_cc": 0.0,  # Default portamento time
        }

        # Pre-allocate combined LFOs list to avoid concatenation on every block
        self.combined_lfos = self.channel_lfos + self.note_lfos

        # Initialize partials
        self.partials = []
        self._setup_partials()

        # If still no active partials, mark as inactive
        if not any(partial.is_active() for partial in self.partials):
            self.active = False

        # Initialize envelopes
        self._initialize_envelopes()
        self.temp_left = channel.memory_pool.get_mono_buffer(channel.synth.block_size)
        self.temp_right = channel.memory_pool.get_mono_buffer(channel.synth.block_size)

    def _get_parameters(
        self,
        program: int,
        bank: int,
        note: int,
        velocity: int,
        is_drum: bool,
    ):
        """Get parameters for this note"""
        wavetable: WavetableManager = self.channel.synth.sf2_manager.get_manager()
        if is_drum:
            params = wavetable.get_drum_parameters(note, program, bank)
        else:
            params = wavetable.get_program_parameters(
                program, bank, note, velocity
            )
            
        return params
        
    def _setup_partials(self):
        """Setup partial structures for this note using optimized pooling"""
        partials_params = self.params.get("partials", [])

        # Create partial generators only for active partials (level > 0)
        for i, partial_params in enumerate(partials_params):
            # Check if this partial should be active (level > 0)
            level = partial_params.get("level", 0.0)
            if level <= 0.0:
                continue  # Skip inactive partials

            # Apply key scaling to envelope parameters
            if "keynum_to_vol_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_vol_env_decay"] / 1200.0
                partial_params["amp_envelope"]["key_scaling"] = key_scaling

            if "keynum_to_mod_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_mod_env_decay"] / 1200.0
                partial_params["filter_envelope"]["key_scaling"] = key_scaling

            # Apply coarseTune and fineTune (pass channel-level tuning to partials)
            self.coarse_tune = partial_params.get("coarse_tune", 0)
            self.fine_tune = partial_params.get("fine_tune", 0)

            # Merge channel-level tuning parameters with partial parameters
            merged_partial_params = {
                **partial_params,
                'coarse_tune': self.coarse_tune,
                'fine_tune': self.fine_tune,
            }

            # Acquire partial generator from pool with merged parameters
            partial = self.synth.partial_pool.acquire(
                synth=self.synth,
                note=self.note,
                velocity=self.velocity,
                program=self.program,
                partial_id=i,
                partial_params=merged_partial_params,
                is_drum=self.is_drum,
                sample_rate=self.sample_rate,
                bank=self.bank,
                use_modulation_matrix=self.use_modulation_matrix,
            )
            self.partials.append(partial)

    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix for this note.

        XG Standard Routes (0-8):
        - Routes 0-8 follow MIDI XG specification defaults

        Extended Routes (9-14):
        - Additional controller and note-level LFO routes for enhanced functionality
        - Note-level LFO routes default to 0.0 for backward compatibility
        """
        # Clear existing routes
        for i in range(16):
            self.mod_matrix.clear_route(i)

        # Get modulation parameters or use defaults
        modulation_params = self.params.get("modulation", {})

        # === XG STANDARD ROUTES (0-8) ===
        # LFO1 -> Pitch
        self.mod_matrix.set_route(
            0,
            "lfo1",
            "pitch",
            amount=modulation_params.get("lfo1_to_pitch", 50.0) / 100.0,
            polarity=1.0,
        )

        # LFO2 -> Pitch
        self.mod_matrix.set_route(
            1,
            "lfo2",
            "pitch",
            amount=modulation_params.get("lfo2_to_pitch", 30.0) / 100.0,
            polarity=1.0,
        )

        # LFO3 -> Pitch
        self.mod_matrix.set_route(
            2,
            "lfo3",
            "pitch",
            amount=modulation_params.get("lfo3_to_pitch", 10.0) / 100.0,
            polarity=1.0,
        )

        # Amp Envelope -> Filter Cutoff
        self.mod_matrix.set_route(
            3,
            "amp_env",
            "filter_cutoff",
            amount=modulation_params.get("env_to_filter", 0.5),
            polarity=1.0,
        )

        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(
            4,
            "lfo1",
            "filter_cutoff",
            amount=modulation_params.get("lfo_to_filter", 0.3),
            polarity=1.0,
        )

        # Velocity -> Amp
        self.mod_matrix.set_route(
            5, "velocity", "amp", amount=0.5, velocity_sensitivity=0.5
        )

        # Note Number -> Pitch
        self.mod_matrix.set_route(
            6, "note_number", "pitch", amount=1.0, key_scaling=1.0
        )

        # Vibrato -> Pitch
        self.mod_matrix.set_route(
            7,
            "vibrato",
            "pitch",
            amount=modulation_params.get("vibrato_depth", 50.0) / 100.0,
            polarity=1.0,
        )

        # Tremolo Depth -> Amp
        self.mod_matrix.set_route(
            8,
            "tremolo_depth",
            "amp",
            amount=modulation_params.get("tremolo_depth", 0.3),
            polarity=1.0,
        )

        # === EXTENDED ROUTES (9-14) ===
        # Controller-based modulation for enhanced expressiveness
        self.mod_matrix.set_route(
            9,
            "mod_wheel",
            "pan",
            amount=1.0,
            polarity=1.0,
        )  # Mod wheel -> Pan

        self.mod_matrix.set_route(
            10,
            "velocity",
            "velocity_crossfade",
            amount=1.0,
            velocity_sensitivity=0.5,
        )  # Velocity -> Crossfade

        self.mod_matrix.set_route(
            11,
            "note_number",
            "note_crossfade",
            amount=1.0,
            key_scaling=0.0,
        )  # Note number -> Crossfade

        self.mod_matrix.set_route(
            12,
            "breath_controller",
            "stereo_width",
            amount=1.0,
            polarity=1.0,
        )  # Breath controller -> Stereo width

        self.mod_matrix.set_route(
            13,
            "foot_controller",
            "tremolo_rate",
            amount=1.0,
            polarity=1.0,
        )  # Foot controller -> Tremolo rate

        self.mod_matrix.set_route(
            14,
            "volume_cc",
            "tremolo_depth",
            amount=0.5,
            polarity=1.0,
        )  # Volume CC -> Tremolo depth

        # === NOTE-LEVEL LFO ROUTES (15) ===
        # Note-level LFOs provide per-note modulation (XG enhancement)
        # Default to 0.0 for backward compatibility
        # Note: Only 1 route available, prioritizing pitch modulation
        self.mod_matrix.set_route(
            15,
            "note_lfo1",
            "pitch",
            amount=modulation_params.get("note_lfo1_to_pitch", 0.0),
            polarity=1.0,
        )  # Note LFO1 -> Pitch (additional vibrato per note)

        # === NOTE-LEVEL TUNING AND EFFECTS ===
        # Routes for note-level detune and phaser effects
        # These provide per-note control over pitch and phasing
        # Detune: Global pitch offset for the entire note (±100 cents range)
        # Phaser: Note-level phasing effect (0.0-1.0 range)

    def _initialize_envelopes(self):
        """Initialize envelopes for all partials"""
        for partial in self.partials:
            if partial.active:
                partial.amp_envelope.note_on(self.velocity, self.note)
                if partial.filter_envelope:
                    partial.filter_envelope.note_on(self.velocity, self.note)
                if partial.pitch_envelope:
                    partial.pitch_envelope.note_on(self.velocity, self.note)

    def _initialize_note_lfos(self):
        """Initialize note-level LFOs per XG specification"""
        # XG allows up to 3 note-level LFOs (similar to channel LFOs)
        # These are separate from channel LFOs and can have different parameters per note

        # Get LFO parameters from note parameters
        lfo_params = self.params.get("modulation", {})

        # Note-level LFO1 (primarily for vibrato - additional pitch modulation per note)
        note_lfo1_rate = lfo_params.get("note_lfo1_rate", 5.0)
        note_lfo1_depth = lfo_params.get(
            "note_lfo1_depth", 0.0
        )  # Default to 0 for backward compatibility
        note_lfo1_delay = lfo_params.get("note_lfo1_delay", 0.0)

        note_lfo1 = self.channel.synth.lfo_pool.acquire_oscillator(
            id=10,  # Use different IDs to avoid conflict with channel LFOs
            waveform="sine",
            rate=note_lfo1_rate,
            depth=note_lfo1_depth,
            delay=note_lfo1_delay,
        )

        # Set XG modulation routing for note-level LFO1 (pitch modulation)
        note_lfo1.set_modulation_routing(pitch=True, filter=False, amplitude=False)
        note_lfo1.set_modulation_depths(
            pitch_cents=25.0, filter_depth=0.0, amplitude_depth=0.0
        )  # 25 cents additional vibrato

        self.note_lfos.append(note_lfo1)

        # Note-level LFO2 (for filter modulation per note)
        note_lfo2_rate = lfo_params.get("note_lfo2_rate", 2.0)
        note_lfo2_depth = lfo_params.get("note_lfo2_depth", 0.0)
        note_lfo2_delay = lfo_params.get("note_lfo2_delay", 0.0)

        note_lfo2 = self.channel.synth.lfo_pool.acquire_oscillator(
            id=11,
            waveform="triangle",
            rate=note_lfo2_rate,
            depth=note_lfo2_depth,
            delay=note_lfo2_delay,
        )

        # Set XG modulation routing for note-level LFO2 (filter modulation)
        note_lfo2.set_modulation_routing(pitch=False, filter=True, amplitude=False)
        note_lfo2.set_modulation_depths(
            pitch_cents=0.0, filter_depth=0.2, amplitude_depth=0.0
        )

        self.note_lfos.append(note_lfo2)

        # Note-level LFO3 (for amplitude modulation per note - tremolo)
        note_lfo3_rate = lfo_params.get("note_lfo3_rate", 0.5)
        note_lfo3_depth = lfo_params.get("note_lfo3_depth", 0.0)
        note_lfo3_delay = lfo_params.get("note_lfo3_delay", 0.5)

        note_lfo3 = self.channel.synth.lfo_pool.acquire_oscillator(
            id=12,
            waveform="sawtooth",
            rate=note_lfo3_rate,
            depth=note_lfo3_depth,
            delay=note_lfo3_delay,
        )

        # Set XG modulation routing for note-level LFO3 (amplitude modulation)
        note_lfo3.set_modulation_routing(pitch=False, filter=False, amplitude=True)
        note_lfo3.set_modulation_depths(
            pitch_cents=0.0, filter_depth=0.0, amplitude_depth=0.3
        )

        self.note_lfos.append(note_lfo3)

    def note_off(self):
        """Handle note off for this note"""
        for partial in self.partials:
            partial.note_off()

    def is_active(self):
        """Check if this note is still active"""
        return self.active and any(partial.is_active() for partial in self.partials)

    def generate_sample_block(
        self,
        block_size: int,
        left_buffer: np.ndarray,
        right_buffer: np.ndarray,
        mod_wheel: int,
        breath_controller: int,
        foot_controller: int,
        brightness: int,
        harmonic_content: int,
        channel_pressure_value: int,
        key_pressure: int,
        volume: float,
        expression: float,
        global_pitch_mod: float = 0.0,
        modulation_pitch: float = 0.0,
        modulation_filter: float = 0.0,
        modulation_amplitude: float = 1.0,
    ) -> None:
        """Generate a block of samples for this note."""

        left_buffer[:block_size].fill(0.0)
        right_buffer[:block_size].fill(0.0)
        if not self.is_active():
            return

        if self.channel_lfos:
            for lfo in self.channel_lfos:
                lfo.set_mod_wheel(mod_wheel)
                lfo.set_breath_controller(breath_controller)
                lfo.set_foot_controller(foot_controller)
                lfo.set_brightness(brightness)
                lfo.set_harmonic_content(harmonic_content)
                lfo.set_channel_aftertouch(channel_pressure_value)
                lfo.set_key_aftertouch(key_pressure)

        for lfo in self.note_lfos:
            lfo.set_mod_wheel(mod_wheel)
            lfo.set_breath_controller(breath_controller)
            lfo.set_foot_controller(foot_controller)
            lfo.set_brightness(brightness)
            lfo.set_harmonic_content(harmonic_content)
            lfo.set_channel_aftertouch(channel_pressure_value)
            lfo.set_key_aftertouch(key_pressure)

        sources = self.modulation_sources
        sources["velocity"] = self.velocity / 127.0
        sources["after_touch"] = channel_pressure_value / 127.0
        sources["mod_wheel"] = mod_wheel / 127.0
        sources["breath_controller"] = breath_controller / 127.0
        sources["foot_controller"] = foot_controller / 127.0
        sources["lfo1"] = (
            self.channel_lfos[0].step() if len(self.channel_lfos) > 0 else 0.0
        )
        sources["lfo2"] = (
            self.channel_lfos[1].step() if len(self.channel_lfos) > 1 else 0.0
        )
        sources["lfo3"] = (
            self.channel_lfos[2].step() if len(self.channel_lfos) > 2 else 0.0
        )
        sources["note_lfo1"] = (
            self.note_lfos[0].step() if len(self.note_lfos) > 0 else 0.0
        )
        sources["note_lfo2"] = (
            self.note_lfos[1].step() if len(self.note_lfos) > 1 else 0.0
        )
        sources["note_lfo3"] = (
            self.note_lfos[2].step() if len(self.note_lfos) > 2 else 0.0
        )
        sources["amp_env"] = 0.0  # Will be set from envelope processing
        sources["filter_env"] = 0.0
        sources["pitch_env"] = 0.0
        sources["key_pressure"] = key_pressure / 127.0
        sources["brightness"] = brightness / 127.0
        sources["harmonic_content"] = harmonic_content / 127.0
        sources["note_number"] = self.note / 127.0
        sources["volume_cc"] = volume / 127.0

        # Process modulation matrix (constant across block for now)
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)

        # Separate modulation by type for different consumers
        synthesis_modulation = {k: v for k, v in modulation_values.items()
                              if k in ['pitch', 'filter_cutoff', 'amp', 'pan']}

        lfo_modulation = {k: v for k, v in modulation_values.items()
                         if k.startswith('lfo') and ('_rate' in k or '_depth' in k)}

        envelope_modulation = {k: v for k, v in modulation_values.items()
                              if any(x in k for x in ['attack', 'decay', 'sustain', 'release', 'hold'])}

        advanced_modulation = {k: v for k, v in modulation_values.items()
                              if k in ['velocity_crossfade', 'note_crossfade', 'stereo_width', 'tremolo_rate']}

        # Apply modulation to global pitch and additional modulation matrix values
        pitch_mod = global_pitch_mod + modulation_pitch
        if "pitch" in synthesis_modulation:
            pitch_mod += synthesis_modulation["pitch"]

        # Apply note-level detune (global pitch offset for entire note)
        # Detune is stored as a modulation destination (±100 cents range)
        detune_mod = modulation_values.get("detune", 0.0)
        self.detune = detune_mod * 100.0  # Convert to cents (±100 cents range)
        pitch_mod += self.detune / 1200.0  # Convert cents to semitones

        # Apply note-level phaser effect
        # Phaser depth controls the intensity of the phasing effect
        phaser_mod = modulation_values.get("phaser_depth", 0.0)
        self.phaser_depth = max(0.0, min(1.0, phaser_mod))  # Clamp to 0.0-1.0 range

        # Get additional modulation values for per-partial application
        filter_mod = modulation_filter
        if "filter_cutoff" in synthesis_modulation:
            filter_mod += synthesis_modulation["filter_cutoff"]

        amp_mod = modulation_amplitude
        if "amp" in synthesis_modulation:
            amp_mod *= 1.0 + synthesis_modulation["amp"]  # Apply as multiplier

        # Use pre-allocated combined LFOs list (zero-allocation)
        combined_lfos = self.combined_lfos

        # Generate samples from partials using comprehensive modulation
        active_partials = 0

        for partial in self.partials:
            if not partial.is_active():
                continue

            # Apply comprehensive modulation to partial
            partial.apply_modulation(
                synthesis_modulation, lfo_modulation,
                envelope_modulation, advanced_modulation
            )

            # Generate partial samples with time-varying LFO modulation
            partial.generate_sample_block(
                block_size,
                self.temp_left,
                self.temp_right,
                lfos=combined_lfos,  # Pass combined channel + note LFOs
                global_pitch_mod=pitch_mod,
                velocity_crossfade=0.0,
                note_crossfade=0.0,
            )

            np.add(
                left_buffer[:block_size],
                self.temp_left[:block_size],
                out=left_buffer[:block_size],
            )
            np.add(
                right_buffer[:block_size],
                self.temp_right[:block_size],
                out=right_buffer[:block_size],
            )
            active_partials += 1

        # Normalize by active partials
        if active_partials > 0:
            # Apply CORRECTED volume scaling to fix inaudible output
            volume_scale = self._calculate_correct_volume_scale(
                volume, expression, active_partials
            )
            left_buffer[:block_size] *= volume_scale
            right_buffer[:block_size] *= volume_scale

            # Apply note-level phaser effect if depth > 0
            if self.phaser_depth > 0.0:
                self._apply_note_phaser(left_buffer, right_buffer, block_size)

    def _calculate_correct_volume_scale(
        self, volume_cc: float, expression_cc: float, active_partials: int
    ) -> float:
        """
        Calculate correct volume scaling to fix inaudible output.

        Fixes multiple issues:
        1. Exponential MIDI volume conversion instead of linear
        2. RMS normalization for multiple partials instead of division
        3. Proper compensation for multiple volume controls
        4. Boost to compensate for processing losses
        """
        import numpy as np

        # Clamp MIDI values
        midi_volume = np.clip(volume_cc, 0, 127)
        midi_expression = np.clip(expression_cc, 0, 127)

        # Convert MIDI volume to exponential scale (dB approximation)
        # MIDI volume follows exponential curve, not linear
        volume_db = (midi_volume / 127.0) * 40.0 - 40.0  # -40dB to 0dB
        volume_linear = 10.0 ** (volume_db / 20.0)

        expression_db = (midi_expression / 127.0) * 40.0 - 40.0
        expression_linear = 10.0 ** (expression_db / 20.0)

        # Combine volume and expression
        combined_volume = volume_linear * expression_linear

        # RMS normalization for multiple partials (not division!)
        # This prevents excessive volume reduction with multiple partials
        if active_partials > 1:
            combined_volume /= np.sqrt(active_partials)

        # Apply compensation boost to fix inaudible output
        # This compensates for processing losses and ensures audibility
        compensation_boost = 1.2  # +3.6dB boost to ensure audibility
        combined_volume *= compensation_boost

        # Limit to reasonable range to prevent clipping
        max_allowed = 3.0  # +9.5dB maximum
        return np.clip(combined_volume, 0.0, max_allowed)

    def _apply_note_phaser(self, left_buffer: np.ndarray, right_buffer: np.ndarray, block_size: int):
        """
        Apply note-level phaser effect.

        A simple phaser implementation using a few all-pass filters to create
        moving notches in the frequency spectrum.

        Args:
            left_buffer: Left channel audio buffer (modified in-place)
            right_buffer: Right channel audio buffer (modified in-place)
            block_size: Number of samples to process
        """
        if not hasattr(self, '_phaser_state'):
            # Initialize phaser state on first use
            self._phaser_state = {
                'phase': 0.0,
                'lfo_phase': 0.0,
                'delay1': 0.0,
                'delay2': 0.0,
                'delay3': 0.0,
                'delay4': 0.0,
            }

        state = self._phaser_state

        # Phaser parameters based on depth
        lfo_rate = 0.5 + self.phaser_depth * 2.0  # 0.5-2.5 Hz
        depth = self.phaser_depth * 0.8  # Max depth of 0.8

        # Simple all-pass filter phaser
        for i in range(block_size):
            # Generate LFO for phaser sweep
            lfo = math.sin(state['lfo_phase']) * depth
            state['lfo_phase'] += lfo_rate * 2.0 * math.pi / self.sample_rate
            if state['lfo_phase'] > 2.0 * math.pi:
                state['lfo_phase'] -= 2.0 * math.pi

            # Calculate all-pass filter coefficient (frequency sweep)
            # Map LFO to frequency range (200-2000 Hz)
            freq = 200.0 + (2000.0 - 200.0) * (lfo + 1.0) * 0.5
            coeff = math.tan(math.pi * freq / self.sample_rate) - 1.0
            coeff = max(-0.99, min(0.99, coeff))  # Stability limit

            # Get input samples
            input_left = left_buffer[i]
            input_right = right_buffer[i]

            # Apply 4-stage all-pass filter chain for left channel
            # Stage 1
            output1_left = state['delay1'] + coeff * input_left
            state['delay1'] = input_left - coeff * output1_left

            # Stage 2
            output2_left = state['delay2'] + coeff * output1_left
            state['delay2'] = output1_left - coeff * output2_left

            # Stage 3
            output3_left = state['delay3'] + coeff * output2_left
            state['delay3'] = output2_left - coeff * output3_left

            # Stage 4
            output4_left = state['delay4'] + coeff * output3_left
            state['delay4'] = output3_left - coeff * output4_left

            # Mix original with phased signal
            mix = self.phaser_depth
            left_buffer[i] = input_left * (1.0 - mix) + output4_left * mix

            # Apply same processing to right channel (slightly different for stereo)
            # Stage 1
            output1_right = state['delay1'] + coeff * input_right
            state['delay1'] = input_right - coeff * output1_right

            # Stage 2
            output2_right = state['delay2'] + coeff * output1_right
            state['delay2'] = output1_right - coeff * output2_right

            # Stage 3
            output3_right = state['delay3'] + coeff * output2_right
            state['delay3'] = output2_right - coeff * output3_right

            # Stage 4
            output4_right = state['delay4'] + coeff * output3_right
            state['delay4'] = output3_right - coeff * output4_right

            # Mix original with phased signal
            right_buffer[i] = input_right * (1.0 - mix) + output4_right * mix

    def cleanup(self):
        """Clean up all resources and return to pools for reuse."""
        # Return our own buffers
        if hasattr(self, "temp_left") and self.temp_left is not None:
            self.channel.memory_pool.return_mono_buffer(self.temp_left)
            self.temp_left = None
        if hasattr(self, "temp_right") and self.temp_right is not None:
            self.channel.memory_pool.return_mono_buffer(self.temp_right)
            self.temp_right = None

        # Return partials to pool instead of cleaning up
        if self.synth and hasattr(self.synth, "partial_pool"):
            for partial in self.partials:
                self.synth.partial_pool.release(partial)

        # Return note-level LFOs to pool
        if hasattr(self.channel.synth, "lfo_pool"):
            for lfo in self.note_lfos:
                self.channel.synth.lfo_pool.release_oscillator(lfo)

        # Clear references
        self.partials.clear()
        self.note_lfos.clear()

    def __del__(self):
        """Cleanup when ChannelNote is destroyed."""
        self.cleanup()
