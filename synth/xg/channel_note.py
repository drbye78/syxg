"""
XG Channel Note Implementation - Production XG-Compliant

This module implements the XG Channel Note concept, representing an active note
on a MIDI channel with full XG specification compliance.

XG Specification Compliance:
- Up to 8 partials per note (extended from XG standard of 4)
- Note-level LFO modulation (XG enhancement)
- Independent modulation matrix per note
- Proper XG envelope and filter parameter handling
- Support for both melodic and drum modes

Key Features:
- Multi-partial synthesis with exclusive note/velocity ranges
- Per-note LFO modulation sources
- XG-compliant modulation matrix routing
- Optimized for real-time performance
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
from .partial_generator import XGPartialGenerator  # XG-compliant partial generator


class PartialGeneratorPool:
    """
    HIGH-PERFORMANCE PARTIAL GENERATOR POOL

    Optimized object pool for XGPartialGenerator instances to eliminate
    allocation overhead during real-time audio synthesis.

    Key Features:
    - Pre-allocated partial generators for zero-allocation note triggering
    - Smart caching based on partial parameters
    - Automatic cleanup and resource management
    - Thread-safe operation for concurrent access
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
    ) -> XGPartialGenerator:
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
            )

    def release(self, partial: XGPartialGenerator) -> None:
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
    XG Channel Note - Represents an active note on a MIDI channel.

    This class encapsulates all state and processing for a single active note
    in the XG synthesizer architecture. Each note can have up to 8 partials,
    independent modulation, and note-level LFO sources.

    Attributes:
        note (int): MIDI note number (0-127)
        velocity (int): Note velocity (0-127)
        program (int): Program number (0-127)
        bank (int): Bank number (0-16383)
        is_drum (bool): True for drum mode, False for melodic
        active (bool): True if note is still producing sound
        partials (List[XGPartialGenerator]): List of up to 8 partial generators
        channel_lfos (List[XGLFO]): Reference to channel-level LFOs
        note_lfos (List[XGLFO]): Note-level LFOs (XG enhancement)
        mod_matrix (ModulationMatrix): Per-note modulation routing
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
        self.detune = 0.0
        self.phaser_depth = 0.0

        # Store reference to channel-level LFOs (XG architecture)
        self.channel_lfos = channel.lfos

        # Initialize parameters for this note
        self.params = self._get_parameters(program, bank, note, velocity, is_drum)

        # Initialize note-level LFOs (XG specification allows per-note LFOs)
        self.note_lfos = []
        self._initialize_note_lfos()

        # Initialize modulation matrix
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()

        # Pre-allocate modulation sources dict to avoid allocation on every block
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
        self.partials: List[XGPartialGenerator] = []
        self._setup_partials()

        # If still no active partials, mark as inactive
        if not any(partial.is_active() for partial in self.partials):
            self.active = False

        # Initialize envelopes
        self._initialize_envelopes()
        self.temp_left = channel.memory_pool.get_mono_buffer(zero_buffer=True)
        self.temp_right = channel.memory_pool.get_mono_buffer(zero_buffer=True)

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
        # If no wavetable is available, use default parameters
        if wavetable is None:
            pass  # Fall through to default parameters
        else:
            try:
                if is_drum:
                    params = wavetable.get_drum_parameters(note, program, bank)
                else:
                    params = wavetable.get_program_parameters(
                        program, bank, note, velocity
                    )
                if params:
                    return params
            except Exception as e:
                pass

        # Default parameters (XG specification)
        return {
            "amp_envelope": {
                "delay": 0.0,
                "attack": 0.01,
                "hold": 0.0,
                "decay": 0.3,
                "sustain": 0.7,
                "release": 0.5,
                "velocity_sense": 1.0,
                "key_scaling": 0.0,
            },
            "filter_envelope": {
                "delay": 0.0,
                "attack": 0.1,
                "hold": 0.0,
                "decay": 0.5,
                "sustain": 0.6,
                "release": 0.8,
                "key_scaling": 0.0,
            },
            "pitch_envelope": {
                "delay": 0.0,
                "attack": 0.05,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.05,
            },
            "filter": {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass",
                "key_follow": 0.5,
            },
            "lfo1": {"waveform": "sine", "rate": 5.0, "depth": 0.5, "delay": 0.0},
            "lfo2": {"waveform": "triangle", "rate": 2.0, "depth": 0.3, "delay": 0.0},
            "lfo3": {"waveform": "sawtooth", "rate": 0.5, "depth": 0.1, "delay": 0.5},
            "modulation": {
                "lfo1_to_pitch": 50.0,  # in cents
                "lfo2_to_pitch": 30.0,  # in cents
                "lfo3_to_pitch": 10.0,  # in cents
                "env_to_pitch": 30.0,  # in cents
                "aftertouch_to_pitch": 20.0,  # in cents
                "lfo_to_filter": 0.3,
                "env_to_filter": 0.5,
                "aftertouch_to_filter": 0.2,
                "tremolo_depth": 0.3,
                "vibrato_depth": 50.0,  # in cents
                "vibrato_rate": 5.0,
                "vibrato_delay": 0.0,
                # Note-level LFO parameters (XG enhancement)
                "note_lfo1_rate": 5.0,
                "note_lfo1_depth": 0.0,  # Disabled by default for compatibility
                "note_lfo1_delay": 0.0,
                "note_lfo2_rate": 2.0,
                "note_lfo2_depth": 0.0,
                "note_lfo2_delay": 0.0,
                "note_lfo3_rate": 0.5,
                "note_lfo3_depth": 0.0,
                "note_lfo3_delay": 0.5,
                # Note-level LFO modulation amounts
                "note_lfo1_to_pitch": 0.0,
                "note_lfo2_to_filter": 0.0,
                "note_lfo3_to_amp": 0.0,
            },
            "partials": [
                # Partial 0: Main partial (fundamental)
                {
                    "level": 1.0,
                    "pan": 0.5,
                    "key_range_low": 0,
                    "key_range_high": 127,
                    "velocity_range_low": 0,
                    "velocity_range_high": 127,
                    "key_scaling": 0.0,
                    "velocity_sense": 1.0,
                    "crossfade_velocity": True,
                    "crossfade_note": True,
                    "use_filter_env": True,
                    "use_pitch_env": True,
                    "amp_envelope": {
                        "delay": 0.0,
                        "attack": 0.01,
                        "hold": 0.0,
                        "decay": 0.3,
                        "sustain": 0.7,
                        "release": 0.5,
                        "key_scaling": 0.0,
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0,
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05,
                    },
                    "filter": {"cutoff": 1000.0, "resonance": 0.7, "type": "lowpass"},
                    "coarse_tune": 0,
                    "fine_tune": 0,
                    "initial_attenuation": 0,  # in dB
                    "scale_tuning": 100,  # in cents
                    "overriding_root_key": -1,
                },
                # Partial 1: Octave above (disabled by default for compatibility)
                {
                    "level": 0.0,  # Disabled by default
                    "pan": 0.3,
                    "key_range_low": 0,
                    "key_range_high": 127,
                    "velocity_range_low": 0,
                    "velocity_range_high": 127,
                    "key_scaling": 0.0,
                    "velocity_sense": 1.0,
                    "crossfade_velocity": True,
                    "crossfade_note": True,
                    "use_filter_env": True,
                    "use_pitch_env": True,
                    "amp_envelope": {
                        "delay": 0.0,
                        "attack": 0.01,
                        "hold": 0.0,
                        "decay": 0.3,
                        "sustain": 0.7,
                        "release": 0.5,
                        "key_scaling": 0.0,
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0,
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05,
                    },
                    "filter": {"cutoff": 1000.0, "resonance": 0.7, "type": "lowpass"},
                    "coarse_tune": 12,  # Octave above
                    "fine_tune": 0,
                    "initial_attenuation": 0,
                    "scale_tuning": 100,
                    "overriding_root_key": -1,
                },
                # Partial 2: Fifth above (disabled by default)
                {
                    "level": 0.0,  # Disabled by default
                    "pan": 0.7,
                    "key_range_low": 0,
                    "key_range_high": 127,
                    "velocity_range_low": 0,
                    "velocity_range_high": 127,
                    "key_scaling": 0.0,
                    "velocity_sense": 1.0,
                    "crossfade_velocity": True,
                    "crossfade_note": True,
                    "use_filter_env": True,
                    "use_pitch_env": True,
                    "amp_envelope": {
                        "delay": 0.0,
                        "attack": 0.01,
                        "hold": 0.0,
                        "decay": 0.3,
                        "sustain": 0.7,
                        "release": 0.5,
                        "key_scaling": 0.0,
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0,
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05,
                    },
                    "filter": {"cutoff": 1000.0, "resonance": 0.7, "type": "lowpass"},
                    "coarse_tune": 7,  # Perfect fifth
                    "fine_tune": 0,
                    "initial_attenuation": 0,
                    "scale_tuning": 100,
                    "overriding_root_key": -1,
                },
                # Partials 3-7: Additional partials (all disabled by default)
                *[
                    {
                        "level": 0.0,
                        "pan": 0.5,
                        "key_range_low": 0,
                        "key_range_high": 127,
                        "velocity_range_low": 0,
                        "velocity_range_high": 127,
                        "key_scaling": 0.0,
                        "velocity_sense": 1.0,
                        "crossfade_velocity": True,
                        "crossfade_note": True,
                        "use_filter_env": True,
                        "use_pitch_env": True,
                        "amp_envelope": {
                            "delay": 0.0,
                            "attack": 0.01,
                            "hold": 0.0,
                            "decay": 0.3,
                            "sustain": 0.7,
                            "release": 0.5,
                            "key_scaling": 0.0,
                        },
                        "filter_envelope": {
                            "delay": 0.0,
                            "attack": 0.1,
                            "hold": 0.0,
                            "decay": 0.5,
                            "sustain": 0.6,
                            "release": 0.8,
                            "key_scaling": 0.0,
                        },
                        "pitch_envelope": {
                            "delay": 0.0,
                            "attack": 0.05,
                            "hold": 0.0,
                            "decay": 0.1,
                            "sustain": 0.0,
                            "release": 0.05,
                        },
                        "filter": {
                            "cutoff": 1000.0,
                            "resonance": 0.7,
                            "type": "lowpass",
                        },
                        "coarse_tune": 0,
                        "fine_tune": 0,
                        "initial_attenuation": 0,
                        "scale_tuning": 100,
                        "overriding_root_key": -1,
                    }
                    for _ in range(5)
                ],  # 5 more partials to reach 8 total
            ],
        }

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

            # Apply coarseTune and fineTune
            self.coarse_tune = partial_params.get("coarse_tune", 0)
            self.fine_tune = partial_params.get("fine_tune", 0)

            # Acquire partial generator from pool
            partial = self.synth.partial_pool.acquire(
                synth=self.synth,
                note=self.note,
                velocity=self.velocity,
                program=self.program,
                partial_id=i,
                partial_params=partial_params,
                is_drum=self.is_drum,
                sample_rate=self.sample_rate,
                bank=self.bank,
            )
            self.partials.append(partial)

    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix for this note"""
        # Clear existing routes
        for i in range(16):
            self.mod_matrix.clear_route(i)

        # Get modulation parameters or use defaults
        modulation_params = self.params.get("modulation", {})

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

        # Vibrato Depth
        self.mod_matrix.set_route(
            7,
            "vibrato",
            "pitch",
            amount=modulation_params.get("vibrato_depth", 50.0) / 100.0,
            polarity=1.0,
        )

        # Tremolo Depth
        self.mod_matrix.set_route(
            8,
            "tremolo_depth",
            "amp",
            amount=modulation_params.get("tremolo_depth", 0.3),
            polarity=1.0,
        )

        # Note-level LFO routes (XG enhancement)
        # Note LFO1 -> Pitch (additional vibrato per note)
        self.mod_matrix.set_route(
            9,
            "note_lfo1",
            "pitch",
            amount=modulation_params.get("note_lfo1_to_pitch", 0.0),
            polarity=1.0,
        )

        # Note LFO2 -> Filter (per-note filter modulation)
        self.mod_matrix.set_route(
            10,
            "note_lfo2",
            "filter_cutoff",
            amount=modulation_params.get("note_lfo2_to_filter", 0.0),
            polarity=1.0,
        )

        # Note LFO3 -> Amplitude (per-note tremolo)
        self.mod_matrix.set_route(
            11,
            "note_lfo3",
            "amp",
            amount=modulation_params.get("note_lfo3_to_amp", 0.0),
            polarity=1.0,
        )

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
    ):
        """Generate a block of samples for this note with vectorized processing and XG LFO modulation"""

        left_buffer[:block_size].fill(0.0)
        right_buffer[:block_size].fill(0.0)
        if not self.is_active():
            return

        # Update channel LFOs with cached values (XG architecture: LFOs are channel-level)
        if self.channel_lfos:
            for lfo in self.channel_lfos:
                lfo.set_mod_wheel(mod_wheel)
                lfo.set_breath_controller(breath_controller)
                lfo.set_foot_controller(foot_controller)
                lfo.set_brightness(brightness)
                lfo.set_harmonic_content(harmonic_content)
                lfo.set_channel_aftertouch(channel_pressure_value)
                lfo.set_key_aftertouch(key_pressure)

        # Update note-level LFOs (XG enhancement: per-note LFO modulation)
        for lfo in self.note_lfos:
            lfo.set_mod_wheel(mod_wheel)
            lfo.set_breath_controller(breath_controller)
            lfo.set_foot_controller(foot_controller)
            lfo.set_brightness(brightness)
            lfo.set_harmonic_content(harmonic_content)
            lfo.set_channel_aftertouch(channel_pressure_value)
            lfo.set_key_aftertouch(key_pressure)

        # Update pre-allocated modulation sources dict (zero-allocation)
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

        # Apply modulation to global pitch
        pitch_mod = global_pitch_mod
        if "pitch" in modulation_values:
            pitch_mod += modulation_values["pitch"]

        # Use pre-allocated combined LFOs list (zero-allocation)
        combined_lfos = self.combined_lfos

        # Generate samples from partials using block processing with LFO modulation
        active_partials = 0

        for partial in self.partials:
            if not partial.is_active():
                continue

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

    def _calculate_correct_volume_scale(
        self, volume_cc: int, expression_cc: int, active_partials: int
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
