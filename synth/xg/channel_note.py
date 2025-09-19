"""
Channel note implementation for XG synthesizer.
Represents an active note on a channel with all its parameters.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from collections import OrderedDict
from ..core.oscillator import LFO
from ..modulation.matrix import ModulationMatrix
from .partial_generator import PartialGenerator


class ChannelNote:
    """Represents an active note on a channel"""
    def __init__(self, note: int, velocity: int, program: int, bank: int,
                 wavetable, sample_rate: int, is_drum: bool = False):
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.active = True
        self.sample_rate = sample_rate
        self.detune = 0.0
        self.phaser_depth = 0.0

        # Initialize parameters for this note
        self.params = self._get_parameters(program, bank, wavetable, note, velocity, is_drum)

        # Initialize LFOs for this note
        lfo1_params = self.params.get("lfo1", {"waveform": "sine", "rate": 5.0, "depth": 0.5, "delay": 0.0})
        lfo2_params = self.params.get("lfo2", {"waveform": "triangle", "rate": 2.0, "depth": 0.3, "delay": 0.0})
        lfo3_params = self.params.get("lfo3", {"waveform": "sawtooth", "rate": 0.5, "depth": 0.1, "delay": 0.5})

        self.lfos = [
            LFO(id=0, waveform=lfo1_params["waveform"],
                rate=lfo1_params["rate"],
                depth=lfo1_params["depth"],
                delay=lfo1_params["delay"],
                sample_rate=sample_rate),
            LFO(id=1, waveform=lfo2_params["waveform"],
                rate=lfo2_params["rate"],
                depth=lfo2_params["depth"],
                delay=lfo2_params["delay"],
                sample_rate=sample_rate),
            LFO(id=2, waveform=lfo3_params["waveform"],
                rate=lfo3_params["rate"],
                depth=lfo3_params["depth"],
                delay=lfo3_params["delay"],
                sample_rate=sample_rate)
        ]

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
                print(f"Warning: Failed to get parameters from wavetable: {e}")

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
                "vibrato_delay": 0.0
            },
            "partials": [
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
                }
            ]
        }

    def _setup_partials(self, wavetable):
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

            partial = PartialGenerator(
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

    def _initialize_envelopes(self):
        """Initialize envelopes for all partials"""
        for partial in self.partials:
            if partial.active:
                partial.amp_envelope.note_on(self.velocity, self.note)
                if partial.filter_envelope:
                    partial.filter_envelope.note_on(self.velocity, self.note)
                if partial.pitch_envelope:
                    partial.pitch_envelope.note_on(self.velocity, self.note)

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
        if not self.is_active():
            return (0.0, 0.0)

        # Update LFOs with cached values
        for lfo in self.lfos:
            lfo.set_mod_wheel(mod_wheel)
            lfo.set_breath_controller(breath_controller)
            lfo.set_foot_controller(foot_controller)
            lfo.set_brightness(brightness)
            lfo.set_harmonic_content(harmonic_content)
            lfo.set_channel_aftertouch(channel_pressure_value)
            lfo.set_key_aftertouch(key_pressure)

        # Pre-calculate LFO values
        lfo1_val = self.lfos[0].step()
        lfo2_val = self.lfos[1].step()
        lfo3_val = self.lfos[2].step()

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

        for partial in self.partials:
            if partial.is_active():
                if partial.amp_envelope:
                    amp_env_val = partial.amp_envelope.process()
                if partial.filter_envelope:
                    filter_env_val = partial.filter_envelope.process()
                if partial.pitch_envelope:
                    pitch_env_val = partial.pitch_envelope.process()
                break

        # Process modulation matrix
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)

        # Apply modulation to global pitch
        if "pitch" in modulation_values:
            global_pitch_mod += modulation_values["pitch"]

        # Generate sample from partials
        left_sum = 0.0
        right_sum = 0.0
        active_partials = 0

        for partial in self.partials:
            if not partial.is_active():
                continue

            partial_samples = partial.generate_sample(
                lfos=self.lfos,
                global_pitch_mod=global_pitch_mod,
                velocity_crossfade=0.0,
                note_crossfade=0.0
            )

            left_sum += partial_samples[0]
            right_sum += partial_samples[1]
            active_partials += 1

        # Normalize by active partials
        if active_partials > 0:
            left_sum /= active_partials
            right_sum /= active_partials
        # Apply channel volume and expression using precomputed values
        volume_factor = (volume / 127.0) * (expression / 127.0)
        left_out = left_sum * volume_factor
        right_out = right_sum * volume_factor

        return (left_out, right_out)

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
