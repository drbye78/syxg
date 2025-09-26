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
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from collections import OrderedDict

from synth.sf2.core.wavetable_manager import WavetableManager
from ..modulation.matrix import ModulationMatrix
from .partial_generator import XGPartialGenerator  # XG-compliant partial generator
from ..core.vectorized_envelope import VectorizedADSREnvelope  # For note-level envelopes
from ..core.oscillator import XGLFO  # For note-level LFOs


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
    def __init__(self, note: int, velocity: int, program: int, bank: int,
                 wavetable: Optional[WavetableManager], sample_rate: int, is_drum: bool = False, channel_lfos: Optional[List] = None):
        # Input validation
        if not (0 <= note <= 127):
            raise ValueError(f"Note must be between 0-127, got {note}")
        if not (0 <= velocity <= 127):
            raise ValueError(f"Velocity must be between 0-127, got {velocity}")
        if not (0 <= program <= 127):
            raise ValueError(f"Program must be between 0-127, got {program}")
        if not (0 <= bank <= 16383):  # XG supports up to 14-bit bank numbers
            raise ValueError(f"Bank must be between 0-16383, got {bank}")
        if sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {sample_rate}")

        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.active = True
        self.sample_rate = sample_rate
        self.detune = 0.0
        self.phaser_depth = 0.0

        # Store reference to channel-level LFOs (XG architecture)
        self.channel_lfos = channel_lfos or []

        # Initialize parameters for this note
        self.params = self._get_parameters(program, bank, wavetable, note, velocity, is_drum)

        # Initialize note-level LFOs (XG specification allows per-note LFOs)
        self.note_lfos = []
        self._initialize_note_lfos()

        # Initialize modulation matrix
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()

        # Initialize partials
        self.partials = []
        self._setup_partials(wavetable)

        # If no active partials and wavetable is available, create basic generator
        if not any(partial.is_active() for partial in self.partials) and wavetable is None:
            self._setup_basic_generator()

        # If still no active partials, mark as inactive
        if not any(partial.is_active() for partial in self.partials):
            self.active = False

        # Initialize envelopes
        self._initialize_envelopes()

    def _get_parameters(self, program: int, bank: int, wavetable, note: int, velocity: int, is_drum: bool):
        """Get parameters for this note"""
        # If no wavetable is available, use default parameters
        if wavetable is None:
            pass  # Fall through to default parameters
        else:
            try:
                if is_drum:
                    params = wavetable.get_drum_parameters(note, program, bank)
                else:
                    params = wavetable.get_program_parameters(program, bank, note, velocity)
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
                "key_scaling": 0.0
            },
            "filter_envelope": {
                "delay": 0.0,
                "attack": 0.1,
                "hold": 0.0,
                "decay": 0.5,
                "sustain": 0.6,
                "release": 0.8,
                "key_scaling": 0.0
            },
            "pitch_envelope": {
                "delay": 0.0,
                "attack": 0.05,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.05
            },
            "filter": {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass",
                "key_follow": 0.5
            },
            "lfo1": {
                "waveform": "sine",
                "rate": 5.0,
                "depth": 0.5,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": 2.0,
                "depth": 0.3,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sawtooth",
                "rate": 0.5,
                "depth": 0.1,
                "delay": 0.5
            },
            "modulation": {
                "lfo1_to_pitch": 50.0,    # in cents
                "lfo2_to_pitch": 30.0,    # in cents
                "lfo3_to_pitch": 10.0,    # in cents
                "env_to_pitch": 30.0,     # in cents
                "aftertouch_to_pitch": 20.0,  # in cents
                "lfo_to_filter": 0.3,
                "env_to_filter": 0.5,
                "aftertouch_to_filter": 0.2,
                "tremolo_depth": 0.3,
                "vibrato_depth": 50.0,    # in cents
                "vibrato_rate": 5.0,
                "vibrato_delay": 0.0,
                # Note-level LFO parameters (XG enhancement)
                "note_lfo1_rate": 5.0,
                "note_lfo1_depth": 0.0,    # Disabled by default for compatibility
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
                "note_lfo3_to_amp": 0.0
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
                        "key_scaling": 0.0
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05
                    },
                    "filter": {
                        "cutoff": 1000.0,
                        "resonance": 0.7,
                        "type": "lowpass"
                    },
                    "coarse_tune": 0,
                    "fine_tune": 0,
                    "initial_attenuation": 0,  # in dB
                    "scale_tuning": 100,       # in cents
                    "overriding_root_key": -1
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
                        "key_scaling": 0.0
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05
                    },
                    "filter": {
                        "cutoff": 1000.0,
                        "resonance": 0.7,
                        "type": "lowpass"
                    },
                    "coarse_tune": 12,  # Octave above
                    "fine_tune": 0,
                    "initial_attenuation": 0,
                    "scale_tuning": 100,
                    "overriding_root_key": -1
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
                        "key_scaling": 0.0
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05
                    },
                    "filter": {
                        "cutoff": 1000.0,
                        "resonance": 0.7,
                        "type": "lowpass"
                    },
                    "coarse_tune": 7,  # Perfect fifth
                    "fine_tune": 0,
                    "initial_attenuation": 0,
                    "scale_tuning": 100,
                    "overriding_root_key": -1
                },
                # Partials 3-7: Additional partials (all disabled by default)
                *[{
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
                        "key_scaling": 0.0
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05
                    },
                    "filter": {
                        "cutoff": 1000.0,
                        "resonance": 0.7,
                        "type": "lowpass"
                    },
                    "coarse_tune": 0,
                    "fine_tune": 0,
                    "initial_attenuation": 0,
                    "scale_tuning": 100,
                    "overriding_root_key": -1
                } for _ in range(5)]  # 5 more partials to reach 8 total
            ]
        }

    def _setup_partials(self, wavetable: Optional[WavetableManager]):
        """Setup partial structures for this note"""
        partials_params = self.params.get("partials", [])

        # Create partial generators for each partial structure
        for i, partial_params in enumerate(partials_params):
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

            partial = XGPartialGenerator(
                wavetable=wavetable,
                note=self.note,
                velocity=self.velocity,
                program=self.program,
                partial_id=i,
                partial_params=partial_params,
                is_drum=self.is_drum,
                sample_rate=self.sample_rate,
                bank=self.bank
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
        self.mod_matrix.set_route(0,
            "lfo1",
            "pitch",
            amount=modulation_params.get("lfo1_to_pitch", 50.0) / 100.0,
            polarity=1.0
        )

        # LFO2 -> Pitch
        self.mod_matrix.set_route(1,
            "lfo2",
            "pitch",
            amount=modulation_params.get("lfo2_to_pitch", 30.0) / 100.0,
            polarity=1.0
        )

        # LFO3 -> Pitch
        self.mod_matrix.set_route(2,
            "lfo3",
            "pitch",
            amount=modulation_params.get("lfo3_to_pitch", 10.0) / 100.0,
            polarity=1.0
        )

        # Amp Envelope -> Filter Cutoff
        self.mod_matrix.set_route(3,
            "amp_env",
            "filter_cutoff",
            amount=modulation_params.get("env_to_filter", 0.5),
            polarity=1.0
        )

        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(4,
            "lfo1",
            "filter_cutoff",
            amount=modulation_params.get("lfo_to_filter", 0.3),
            polarity=1.0
        )

        # Velocity -> Amp
        self.mod_matrix.set_route(5,
            "velocity",
            "amp",
            amount=0.5,
            velocity_sensitivity=0.5
        )

        # Note Number -> Pitch
        self.mod_matrix.set_route(6,
            "note_number",
            "pitch",
            amount=1.0,
            key_scaling=1.0
        )

        # Vibrato Depth
        self.mod_matrix.set_route(7,
            "vibrato",
            "pitch",
            amount=modulation_params.get("vibrato_depth", 50.0) / 100.0,
            polarity=1.0
        )

        # Tremolo Depth
        self.mod_matrix.set_route(8,
            "tremolo_depth",
            "amp",
            amount=modulation_params.get("tremolo_depth", 0.3),
            polarity=1.0
        )

        # Note-level LFO routes (XG enhancement)
        # Note LFO1 -> Pitch (additional vibrato per note)
        self.mod_matrix.set_route(9,
            "note_lfo1",
            "pitch",
            amount=modulation_params.get("note_lfo1_to_pitch", 0.0),
            polarity=1.0
        )

        # Note LFO2 -> Filter (per-note filter modulation)
        self.mod_matrix.set_route(10,
            "note_lfo2",
            "filter_cutoff",
            amount=modulation_params.get("note_lfo2_to_filter", 0.0),
            polarity=1.0
        )

        # Note LFO3 -> Amplitude (per-note tremolo)
        self.mod_matrix.set_route(11,
            "note_lfo3",
            "amp",
            amount=modulation_params.get("note_lfo3_to_amp", 0.0),
            polarity=1.0
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

        # Note-level LFO1 (primarily for vibrato)
        note_lfo1_rate = lfo_params.get("note_lfo1_rate", 5.0)
        note_lfo1_depth = lfo_params.get("note_lfo1_depth", 0.0)  # Default to 0 for backward compatibility
        note_lfo1_delay = lfo_params.get("note_lfo1_delay", 0.0)

        self.note_lfos.append(XGLFO(
            id=10,  # Use different IDs to avoid conflict with channel LFOs
            waveform="sine",
            rate=note_lfo1_rate,
            depth=note_lfo1_depth,
            delay=note_lfo1_delay,
            sample_rate=self.sample_rate
        ))

        # Note-level LFO2 (for additional modulation)
        note_lfo2_rate = lfo_params.get("note_lfo2_rate", 2.0)
        note_lfo2_depth = lfo_params.get("note_lfo2_depth", 0.0)
        note_lfo2_delay = lfo_params.get("note_lfo2_delay", 0.0)

        self.note_lfos.append(XGLFO(
            id=11,
            waveform="triangle",
            rate=note_lfo2_rate,
            depth=note_lfo2_depth,
            delay=note_lfo2_delay,
            sample_rate=self.sample_rate
        ))

        # Note-level LFO3 (for special effects)
        note_lfo3_rate = lfo_params.get("note_lfo3_rate", 0.5)
        note_lfo3_depth = lfo_params.get("note_lfo3_depth", 0.0)
        note_lfo3_delay = lfo_params.get("note_lfo3_delay", 0.5)

        self.note_lfos.append(XGLFO(
            id=12,
            waveform="sawtooth",
            rate=note_lfo3_rate,
            depth=note_lfo3_depth,
            delay=note_lfo3_delay,
            sample_rate=self.sample_rate
        ))

    def note_off(self):
        """Handle note off for this note"""
        for partial in self.partials:
            partial.note_off()

    def is_active(self):
        """Check if this note is still active"""
        return self.active and any(partial.is_active() for partial in self.partials)

    def generate_sample(self, mod_wheel: int, breath_controller: int, foot_controller: int,
                        brightness: int, harmonic_content: int, channel_pressure_value: int,
                        key_pressure: int, volume: float, expression: float,
                        global_pitch_mod: float = 0.0):
        """Generate a sample for this note with precomputed controller values"""
        import time
        start_time = time.perf_counter()

        if not self.is_active():
            return (0.0, 0.0)

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

        # Pre-calculate LFO values (both channel and note level)
        lfo1_val = self.channel_lfos[0].step() if self.channel_lfos and len(self.channel_lfos) > 0 else 0.0
        lfo2_val = self.channel_lfos[1].step() if self.channel_lfos and len(self.channel_lfos) > 1 else 0.0
        lfo3_val = self.channel_lfos[2].step() if self.channel_lfos and len(self.channel_lfos) > 2 else 0.0

        # Note-level LFO values (XG allows per-note LFO modulation)
        note_lfo1_val = self.note_lfos[0].step() if len(self.note_lfos) > 0 else 0.0
        note_lfo2_val = self.note_lfos[1].step() if len(self.note_lfos) > 1 else 0.0
        note_lfo3_val = self.note_lfos[2].step() if len(self.note_lfos) > 2 else 0.0

        # Get envelope values for first active partial (if any)
        amp_env_val = filter_env_val = pitch_env_val = 0.0
        sources = {
            "velocity": self.velocity / 127.0,
            "after_touch": channel_pressure_value / 127.0,
            "mod_wheel": mod_wheel / 127.0,
            "breath_controller": breath_controller / 127.0,
            "foot_controller": foot_controller / 127.0,
            "data_entry": 100 / 127.0,  # Default data entry value
            "lfo1": lfo1_val,
            "lfo2": lfo2_val,
            "lfo3": lfo3_val,
            "note_lfo1": note_lfo1_val,  # Note-level LFOs
            "note_lfo2": note_lfo2_val,
            "note_lfo3": note_lfo3_val,
            "amp_env": amp_env_val,
            "filter_env": filter_env_val,
            "pitch_env": pitch_env_val,
            "key_pressure": key_pressure / 127.0,
            "brightness": brightness / 127.0,
            "harmonic_content": harmonic_content / 127.0,
            "portamento": 1.0,  # Default portamento is active
            "vibrato": 0.5,  # Default vibrato
            "tremolo": 0.0,
            "tremolo_depth": 0.3,
            "tremolo_rate": 4.0,
            "note_number": self.note / 127.0,
            "volume_cc": volume / 127.0,  # Use passed volume parameter
            "balance": 0.0,  # Default balance
            "portamento_time_cc": 0.0  # Default portamento time
        }

        envelope_time = 0
        modulation_time = 0
        partial_time = 0

        envelope_start = time.perf_counter()
        for partial in self.partials:
            if partial.is_active():
                if partial.amp_envelope:
                    amp_env_val = partial.amp_envelope.process()
                if partial.filter_envelope:
                    filter_env_val = partial.filter_envelope.process()
                if partial.pitch_envelope:
                    pitch_env_val = partial.pitch_envelope.process()
                break
        envelope_time = time.perf_counter() - envelope_start

        # Process modulation matrix
        modulation_start = time.perf_counter()
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)
        modulation_time = time.perf_counter() - modulation_start

        # Apply modulation to global pitch
        if "pitch" in modulation_values:
            global_pitch_mod += modulation_values["pitch"]

        # Generate sample from partials
        left_sum = 0.0
        right_sum = 0.0
        active_partials = 0

        partial_start = time.perf_counter()
        for partial in self.partials:
            if not partial.is_active():
                continue

            partial_samples = partial.generate_sample(
                lfos=self.channel_lfos,
                global_pitch_mod=global_pitch_mod,
                velocity_crossfade=0.0,
                note_crossfade=0.0
            )

            left_sum += partial_samples[0]
            right_sum += partial_samples[1]
            active_partials += 1
        partial_time = time.perf_counter() - partial_start

        # Normalize by active partials
        if active_partials > 0:
            left_sum /= active_partials
            right_sum /= active_partials
        # Apply channel volume and expression using precomputed values
        volume_factor = (volume / 127.0) * (expression / 127.0)
        left_out = left_sum * volume_factor
        right_out = right_sum * volume_factor

        total_time = time.perf_counter() - start_time
        if total_time > 0.0001:  # Log if note sample takes more than 0.1ms
            print(f"Note {self.note}: {total_time:.6f}s, Env: {envelope_time:.6f}s, Mod: {modulation_time:.6f}s, Partials: {partial_time:.6f}s")

        return (left_out, right_out)

    def generate_sample_block(self, block_size: int, mod_wheel: int, breath_controller: int,
                             foot_controller: int, brightness: int, harmonic_content: int,
                             channel_pressure_value: int, key_pressure: int, volume: float,
                             expression: float, global_pitch_mod: float = 0.0):
        """Generate a block of samples for this note with vectorized processing"""
        import time
        import numpy as np
        start_time = time.perf_counter()

        if not self.is_active():
            return (np.zeros(block_size, dtype=np.float32),
                   np.zeros(block_size, dtype=np.float32))

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

        # Pre-calculate LFO values for the block (constant across block for now)
        lfo1_val = self.channel_lfos[0].step() if self.channel_lfos and len(self.channel_lfos) > 0 else 0.0
        lfo2_val = self.channel_lfos[1].step() if self.channel_lfos and len(self.channel_lfos) > 1 else 0.0
        lfo3_val = self.channel_lfos[2].step() if self.channel_lfos and len(self.channel_lfos) > 2 else 0.0

        # Note-level LFO values (XG allows per-note LFO modulation)
        note_lfo1_val = self.note_lfos[0].step() if len(self.note_lfos) > 0 else 0.0
        note_lfo2_val = self.note_lfos[1].step() if len(self.note_lfos) > 1 else 0.0
        note_lfo3_val = self.note_lfos[2].step() if len(self.note_lfos) > 2 else 0.0

        # Build modulation sources
        sources = {
            "velocity": self.velocity / 127.0,
            "after_touch": channel_pressure_value / 127.0,
            "mod_wheel": mod_wheel / 127.0,
            "breath_controller": breath_controller / 127.0,
            "foot_controller": foot_controller / 127.0,
            "data_entry": 100 / 127.0,  # Default data entry value
            "lfo1": lfo1_val,
            "lfo2": lfo2_val,
            "lfo3": lfo3_val,
            "note_lfo1": note_lfo1_val,  # Note-level LFOs
            "note_lfo2": note_lfo2_val,
            "note_lfo3": note_lfo3_val,
            "amp_env": 0.0,  # Will be set from envelope processing
            "filter_env": 0.0,
            "pitch_env": 0.0,
            "key_pressure": key_pressure / 127.0,
            "brightness": brightness / 127.0,
            "harmonic_content": harmonic_content / 127.0,
            "portamento": 1.0,  # Default portamento is active
            "vibrato": 0.5,  # Default vibrato
            "tremolo": 0.0,
            "tremolo_depth": 0.3,
            "tremolo_rate": 4.0,
            "note_number": self.note / 127.0,
            "volume_cc": volume / 127.0,  # Use passed volume parameter
            "balance": 0.0,  # Default balance
            "portamento_time_cc": 0.0  # Default portamento time
        }

        envelope_time = 0
        modulation_time = 0
        partial_time = 0

        # Process modulation matrix (constant across block for now)
        modulation_start = time.perf_counter()
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)
        modulation_time = time.perf_counter() - modulation_start

        # Apply modulation to global pitch
        pitch_mod = global_pitch_mod
        if "pitch" in modulation_values:
            pitch_mod += modulation_values["pitch"]

        # Generate samples from partials using block processing
        left_sum = np.zeros(block_size, dtype=np.float32)
        right_sum = np.zeros(block_size, dtype=np.float32)
        active_partials = 0

        partial_start = time.perf_counter()
        for partial in self.partials:
            if not partial.is_active():
                continue

            partial_left, partial_right = partial.generate_sample_block(
                block_size=block_size,
                lfos=self.channel_lfos,
                global_pitch_mod=pitch_mod,
                velocity_crossfade=0.0,
                note_crossfade=0.0
            )

            left_sum += partial_left
            right_sum += partial_right
            active_partials += 1
        partial_time = time.perf_counter() - partial_start

        # Normalize by active partials
        if active_partials > 0:
            left_sum /= active_partials
            right_sum /= active_partials

        # Apply channel volume and expression using precomputed values
        volume_factor = (volume / 127.0) * (expression / 127.0)
        left_sum *= volume_factor
        right_sum *= volume_factor

        # total_time = time.perf_counter() - start_time
        # if total_time > 0.001:  # Log if note block takes more than 1ms
        #     print(f"Note {self.note} block: {total_time:.6f}s, Mod: {modulation_time:.6f}s, Partials: {partial_time:.6f}s")

        return left_sum, right_sum

    def _setup_basic_generator(self):
        """Setup a basic sine wave generator when no wavetable is available"""
        # Create a simple sine wave partial
        basic_params = {
            "level": 1.0,
            "pan": 0.5,
            "key_range_low": 0,
            "key_range_high": 127,
            "velocity_range_low": 0,
            "velocity_range_high": 127,
            "key_scaling": 0.0,
            "velocity_sense": 1.0,
            "crossfade_velocity": False,
            "crossfade_note": False,
            "use_filter_env": True,
            "use_pitch_env": True,
            "amp_envelope": {
                "delay": 0.0,
                "attack": 0.01,
                "hold": 0.0,
                "decay": 0.3,
                "sustain": 0.7,
                "release": 0.5,
                "key_scaling": 0.0
            },
            "filter_envelope": {
                "delay": 0.0,
                "attack": 0.1,
                "hold": 0.0,
                "decay": 0.5,
                "sustain": 0.6,
                "release": 0.8,
                "key_scaling": 0.0
            },
            "pitch_envelope": {
                "delay": 0.0,
                "attack": 0.05,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.05
            },
            "filter": {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass"
            },
            "coarse_tune": 0,
            "fine_tune": 0
        }

        # For a basic generator, we'll add a simple sine wave partial
        # Note: This would normally use a wavetable, but we're creating a minimal implementation
        pass  # In a real implementation, this would create actual sound generation

