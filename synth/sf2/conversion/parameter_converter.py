"""
SF2 Parameter Converter

Handles conversion of SF2 parameters to XG synthesizer format.
"""

import math
from typing import Dict, List, Any, Optional
from ..types import SF2InstrumentZone


class ParameterConverter:
    """
    Converts SF2 parameters to XG synthesizer format.
    """

    # Constants for parameter conversion
    TIME_CENTISECONDS_TO_SECONDS = 0.01
    FILTER_CUTOFF_SCALE = 0.1
    PAN_SCALE = 0.01
    VELOCITY_SENSE_SCALE = 0.01
    PITCH_SCALE = 0.1
    FILTER_RESONANCE_SCALE = 0.01

    def __init__(self):
        """Initialize parameter converter."""
        pass

    def convert_time_cents_to_seconds(self, time_cents: int) -> float:
        """
        Convert time cents to seconds.

        Args:
            time_cents: Time in centiseconds

        Returns:
            Time in seconds
        """
        if time_cents <= 0:
            return 0.001  # Minimum value

        # SoundFont uses: time = 0.001 * 10^(value/1200)
        return 0.001 * (10 ** (time_cents / 1200.0))

    def convert_lfo_rate(self, lfo_value: int) -> float:
        """
        Convert LFO rate from SF2 format to Hz.

        Args:
            lfo_value: LFO rate in SF2 format

        Returns:
            LFO rate in Hz
        """
        if lfo_value <= 0:
            return 0.1  # Minimum rate

        # SoundFont uses logarithmic scale
        return (10 ** (lfo_value / 1200.0)) * 0.01

    def convert_lfo_delay(self, delay_value: int) -> float:
        """
        Convert LFO delay from SF2 format to seconds.

        Args:
            delay_value: LFO delay in SF2 format

        Returns:
            LFO delay in seconds
        """
        if delay_value <= 0:
            return 0.0

        # SoundFont uses logarithmic scale
        return (10 ** (delay_value / 1200.0)) * self.TIME_CENTISECONDS_TO_SECONDS

    def convert_filter_cutoff(self, cutoff_value: int) -> float:
        """
        Convert filter cutoff from SF2 format.

        Args:
            cutoff_value: Filter cutoff in SF2 format

        Returns:
            Filter cutoff in Hz
        """
        # SF2 cutoff is in cents above 8.175 Hz
        if cutoff_value <= 0:
            return 20.0  # Minimum cutoff

        # Convert from cents to Hz: 8.175 * 2^(cutoff/1200)
        return 8.175 * (2 ** (cutoff_value / 1200.0))

    def convert_filter_resonance(self, resonance_value: int) -> float:
        """
        Convert filter resonance from SF2 format.

        Args:
            resonance_value: Filter resonance in SF2 format

        Returns:
            Filter resonance (0.0 to 1.0)
        """
        # SF2 resonance is in centibels (1/10 dB)
        # Convert to linear scale
        if resonance_value <= 0:
            return 0.0

        # Convert centibels to linear: 10^(value/200)
        linear_resonance = 10 ** (resonance_value / 200.0)

        # Normalize to 0-1 range (rough approximation)
        return min(1.0, linear_resonance / 10.0)

    def convert_pan(self, pan_value: int) -> float:
        """
        Convert pan from SF2 format to normalized range.

        Args:
            pan_value: Pan value in SF2 format

        Returns:
            Pan value in range -1.0 to 1.0
        """
        # SF2 pan is -500 to +500 (left to right)
        # Convert to -1.0 to 1.0
        return max(-1.0, min(1.0, pan_value / 500.0))

    def convert_attenuation(self, attenuation_value: int) -> float:
        """
        Convert attenuation from SF2 format to linear gain.

        Args:
            attenuation_value: Attenuation in centibels

        Returns:
            Linear gain (0.0 to 1.0)
        """
        if attenuation_value <= 0:
            return 1.0

        # Convert centibels to linear: 10^(-value/200)
        return 10 ** (-attenuation_value / 200.0)

    def convert_pitch(self, pitch_value: int) -> float:
        """
        Convert pitch from SF2 format to semitones.

        Args:
            pitch_value: Pitch in cents

        Returns:
            Pitch in semitones
        """
        # SF2 pitch is in cents
        return pitch_value / 100.0

    def convert_velocity_sense(self, velocity_value: int) -> float:
        """
        Convert velocity sensitivity from SF2 format.

        Args:
            velocity_value: Velocity sensitivity in SF2 format

        Returns:
            Velocity sensitivity (0.0 to 1.0)
        """
        # SF2 velocity is typically -9600 to 9600
        # Convert to 0-1 range
        return max(0.0, min(1.0, (velocity_value + 9600) / 19200.0))

    def cents_to_amplitude(self, bells: int) -> float:
        """
        Convert centibels to amplitude.

        Args:
            bells: Value in centibels

        Returns:
            Amplitude (0.0 to 1.0)
        """
        amp = math.pow(10.0, bells / -200.0)
        return min(1.0, amp)

    def convert_envelope_times(self, attack: int, decay: int, release: int) -> Dict[str, float]:
        """
        Convert envelope times from SF2 format.

        Args:
            attack: Attack time in time cents
            decay: Decay time in time cents
            release: Release time in time cents

        Returns:
            Dictionary with converted times
        """
        return {
            'attack': self.convert_time_cents_to_seconds(attack),
            'decay': self.convert_time_cents_to_seconds(decay),
            'release': self.convert_time_cents_to_seconds(release)
        }

    def convert_zone_to_partial_params(self, zone: SF2InstrumentZone,
                                     is_drum: bool = False) -> Dict[str, Any]:
        """
        Convert SF2 zone to XG partial parameters.

        Args:
            zone: SF2 instrument zone
            is_drum: Whether this is a drum zone

        Returns:
            Dictionary with XG partial parameters
        """
        # Convert envelope times
        envelope_times = self.convert_envelope_times(
            zone.AttackVolEnv,
            zone.DecayVolEnv,
            zone.ReleaseVolEnv
        )

        # Convert filter parameters
        cutoff = self.convert_filter_cutoff(zone.initialFilterFc)
        resonance = self.convert_filter_resonance(zone.initial_filterQ)

        # Convert pan
        pan = self.convert_pan(zone.Pan)

        # Convert attenuation
        attenuation = self.convert_attenuation(zone.InitialAttenuation)

        # Convert velocity sensitivity
        velocity_sense = self.convert_velocity_sense(zone.VelocityAttenuation)

        # Convert pitch shift
        pitch_shift = self.convert_pitch(zone.VelocityPitch)

        # Build partial parameters
        partial_params = {
            "level": attenuation,
            "pan": pan,
            "key_range_low": zone.lokey,
            "key_range_high": zone.hikey,
            "velocity_range_low": zone.lovel,
            "velocity_range_high": zone.hivel,
            "key_scaling": 0.0,
            "velocity_sense": velocity_sense,
            "crossfade_velocity": True,
            "crossfade_note": True,
            "use_filter_env": True,
            "use_pitch_env": True,
            "pitch_shift": pitch_shift,
            "note_crossfade": 0.0,
            "velocity_crossfade": 0.0,

            # Sample address offsets
            "start_coarse": zone.start_coarse,
            "end_coarse": zone.end_coarse,
            "start_loop_coarse": zone.start_loop_coarse,
            "end_loop_coarse": zone.end_loop_coarse,

            # Amplitude envelope
            "amp_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.DelayVolEnv),
                "attack": envelope_times['attack'],
                "hold": self.convert_time_cents_to_seconds(zone.HoldVolEnv),
                "decay": envelope_times['decay'],
                "sustain": self.cents_to_amplitude(zone.SustainVolEnv),
                "release": envelope_times['release'],
                "key_scaling": zone.KeynumToVolEnvDecay / 1200.0
            },

            # Filter envelope
            "filter_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.DelayFilEnv),
                "attack": self.convert_time_cents_to_seconds(zone.AttackFilEnv),
                "hold": self.convert_time_cents_to_seconds(zone.HoldFilEnv),
                "decay": self.convert_time_cents_to_seconds(zone.DecayFilEnv),
                "sustain": self.cents_to_amplitude(zone.SustainFilEnv),
                "release": self.convert_time_cents_to_seconds(zone.ReleaseFilEnv),
                "key_scaling": zone.KeynumToModEnvDecay / 1200.0
            },

            # Pitch envelope
            "pitch_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.DelayPitchEnv),
                "attack": self.convert_time_cents_to_seconds(zone.AttackPitchEnv),
                "hold": self.convert_time_cents_to_seconds(zone.HoldPitchEnv),
                "decay": self.convert_time_cents_to_seconds(zone.DecayPitchEnv),
                "sustain": self.cents_to_amplitude(zone.SustainPitchEnv),
                "release": self.convert_time_cents_to_seconds(zone.ReleasePitchEnv)
            },

            # Filter
            "filter": {
                "cutoff": cutoff,
                "resonance": resonance,
                "type": "lowpass",
                "key_follow": 0.5
            },

            # Tuning
            "coarse_tune": zone.CoarseTune,
            "fine_tune": zone.FineTune
        }

        # For drums, simplify parameters
        if is_drum:
            partial_params["use_filter_env"] = False
            partial_params["use_pitch_env"] = False
            partial_params["amp_envelope"]["attack"] = max(0.001, partial_params["amp_envelope"]["attack"] * 0.1)
            partial_params["amp_envelope"]["decay"] = max(0.01, partial_params["amp_envelope"]["decay"] * 0.5)
            partial_params["amp_envelope"]["sustain"] = 0.0

        return partial_params
