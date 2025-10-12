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
        Convert SF2 zone to XG partial parameters with complete generator support.

        Args:
            zone: SF2 instrument zone
            is_drum: Whether this is a drum zone

        Returns:
            Dictionary with XG partial parameters
        """
        # Convert envelope times using complete SF2 envelope parameters
        envelope_times = self.convert_envelope_times(
            zone.attackVolEnv,  # Use new SF2 generator names
            zone.decayVolEnv,
            zone.releaseVolEnv
        )

        # Convert filter parameters with complete SF2 filter support
        cutoff = self.convert_filter_cutoff(zone.initialFilterFc)
        resonance = self.convert_filter_resonance(zone.initialFilterQ)

        # Convert pan using SF2 pan generator
        pan = self.convert_pan(zone.pan)

        # Convert attenuation
        attenuation = self.convert_attenuation(zone.initialAttenuation)

        # Convert velocity sensitivity
        velocity_sense = self.convert_velocity_sense(zone.velocity if hasattr(zone, 'velocity') and zone.velocity >= 0 else 0)

        # Convert pitch shift
        pitch_shift = self.convert_pitch(zone.velocity if hasattr(zone, 'velocity') and zone.velocity >= 0 else 0)

        # Extract key/velocity ranges from SF2 generators
        key_range_low = zone.lokey if hasattr(zone, 'lokey') else 0
        key_range_high = zone.hikey if hasattr(zone, 'hikey') else 127
        vel_range_low = zone.lovel if hasattr(zone, 'lovel') else 0
        vel_range_high = zone.hivel if hasattr(zone, 'hivel') else 127

        # Override with SF2 keyRange/velRange if set
        if hasattr(zone, 'keyRange') and zone.keyRange != 0:
            key_range_low = zone.keyRange & 0xFF
            key_range_high = (zone.keyRange >> 8) & 0xFF
        if hasattr(zone, 'velRange') and zone.velRange != 0:
            vel_range_low = zone.velRange & 0xFF
            vel_range_high = (zone.velRange >> 8) & 0xFF

        # Build comprehensive partial parameters with all SF2 generators
        partial_params = {
            "level": attenuation,
            "pan": pan,
            "key_range_low": key_range_low,
            "key_range_high": key_range_high,
            "velocity_range_low": vel_range_low,
            "velocity_range_high": vel_range_high,
            "key_scaling": 0.0,
            "velocity_sense": velocity_sense,
            "crossfade_velocity": True,
            "crossfade_note": True,
            "use_filter_env": True,
            "use_pitch_env": True,
            "pitch_shift": pitch_shift,
            "note_crossfade": 0.0,
            "velocity_crossfade": 0.0,

            # Sample address offsets (complete SF2 addressing)
            "start_offset": zone.startAddrsOffset if hasattr(zone, 'startAddrsOffset') else 0,
            "end_offset": zone.endAddrsOffset if hasattr(zone, 'endAddrsOffset') else 0,
            "start_loop_offset": zone.startloopAddrsOffset if hasattr(zone, 'startloopAddrsOffset') else 0,
            "end_loop_offset": zone.endloopAddrsOffset if hasattr(zone, 'endloopAddrsOffset') else 0,
            "start_coarse_offset": zone.startAddrsCoarseOffset if hasattr(zone, 'startAddrsCoarseOffset') else 0,
            "end_coarse_offset": zone.endAddrsCoarseOffset if hasattr(zone, 'endAddrsCoarseOffset') else 0,
            "start_loop_coarse": zone.startloopAddrsCoarse if hasattr(zone, 'startloopAddrsCoarse') else 0,
            "end_loop_coarse": zone.endloopAddrsCoarse if hasattr(zone, 'endloopAddrsCoarse') else 0,

            # Effects sends (complete SF2 effects support)
            "reverb_send": zone.reverbEffectsSend if hasattr(zone, 'reverbEffectsSend') else 0,
            "chorus_send": zone.chorusEffectsSend if hasattr(zone, 'chorusEffectsSend') else 0,

            # Amplitude envelope (complete SF2 envelope)
            "amp_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.delayVolEnv),
                "attack": self.convert_time_cents_to_seconds(zone.attackVolEnv),
                "hold": self.convert_time_cents_to_seconds(zone.holdVolEnv),
                "decay": self.convert_time_cents_to_seconds(zone.decayVolEnv),
                "sustain": self.cents_to_amplitude(zone.sustainVolEnv),
                "release": self.convert_time_cents_to_seconds(zone.releaseVolEnv),
                "key_scaling": zone.keynumToVolEnvDecay / 1200.0 if hasattr(zone, 'keynumToVolEnvDecay') else 0.0
            },

            # Filter envelope (complete SF2 envelope)
            "filter_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.delayModEnv if hasattr(zone, 'delayModEnv') else -12000),
                "attack": self.convert_time_cents_to_seconds(zone.attackModEnv if hasattr(zone, 'attackModEnv') else -12000),
                "hold": self.convert_time_cents_to_seconds(zone.holdModEnv if hasattr(zone, 'holdModEnv') else -12000),
                "decay": self.convert_time_cents_to_seconds(zone.decayModEnv if hasattr(zone, 'decayModEnv') else -12000),
                "sustain": self.cents_to_amplitude(zone.sustainModEnv if hasattr(zone, 'sustainModEnv') else 0),
                "release": self.convert_time_cents_to_seconds(zone.releaseModEnv if hasattr(zone, 'releaseModEnv') else -12000),
                "key_scaling": zone.keynumToModEnvDecay / 1200.0 if hasattr(zone, 'keynumToModEnvDecay') else 0.0
            },

            # Pitch envelope (complete SF2 envelope)
            "pitch_envelope": {
                "delay": 0.0,  # SF2 doesn't have pitch envelope delay
                "attack": 0.0,  # SF2 doesn't have pitch envelope attack
                "hold": 0.0,   # SF2 doesn't have pitch envelope hold
                "decay": 0.0,  # SF2 doesn't have pitch envelope decay
                "sustain": 1.0, # SF2 doesn't have pitch envelope sustain
                "release": 0.0  # SF2 doesn't have pitch envelope release
            },

            # Filter (complete SF2 filter support)
            "filter": {
                "cutoff": cutoff,
                "resonance": resonance,
                "type": "lowpass",
                "key_follow": 0.5
            },

            # LFO parameters (complete SF2 LFO support)
            "lfo1": {
                "waveform": "sine",
                "rate": self.convert_lfo_rate(zone.freqModLFO if hasattr(zone, 'freqModLFO') else 0),
                "depth": 0.5,
                "delay": self.convert_lfo_delay(zone.delayModLFO if hasattr(zone, 'delayModLFO') else 0)
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": self.convert_lfo_rate(zone.freqVibLFO if hasattr(zone, 'freqVibLFO') else 0),
                "depth": 0.3,
                "delay": self.convert_lfo_delay(zone.delayVibLFO if hasattr(zone, 'delayVibLFO') else 0)
            },
            "lfo3": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },

            # Modulation parameters (complete SF2 modulation support)
            "modulation": {
                "lfo1_to_pitch": zone.modLfoToPitch / 100.0 if hasattr(zone, 'modLfoToPitch') else 0.0,
                "lfo2_to_pitch": zone.vibLfoToPitch / 100.0 if hasattr(zone, 'vibLfoToPitch') else 0.0,
                "env_to_pitch": zone.modEnvToPitch / 100.0 if hasattr(zone, 'modEnvToPitch') else 0.0,
                "lfo_to_filter": zone.modLfoToFilterFc / 1000.0 if hasattr(zone, 'modLfoToFilterFc') else 0.0,
                "env_to_filter": zone.modEnvToFilterFc / 1000.0 if hasattr(zone, 'modEnvToFilterFc') else 0.0,
                "lfo_to_volume": zone.modLfoToVolume / 1000.0 if hasattr(zone, 'modLfoToVolume') else 0.0,
                "velocity_to_pitch": zone.velocity / 100.0 if hasattr(zone, 'velocity') and zone.velocity >= 0 else 0.0,
                "velocity_to_filter": 0.0,  # SF2 doesn't have direct velocity to filter
                "aftertouch_to_pitch": 0.0,  # SF2 doesn't have direct aftertouch to pitch
                "aftertouch_to_filter": 0.0,  # SF2 doesn't have direct aftertouch to filter
                "mod_wheel_to_pitch": 0.0,  # Handled by modulators
                "mod_wheel_to_filter": 0.0,  # Handled by modulators
                "brightness_to_filter": 0.0,  # Handled by modulators
                "portamento_to_pitch": 0.0,  # Handled by modulators
                "tremolo_depth": 0.0,  # Handled by modulators
                "vibrato_depth": zone.vibLfoToPitch / 100.0 if hasattr(zone, 'vibLfoToPitch') else 0.0
            },

            # Tuning (complete SF2 tuning support)
            "coarse_tune": zone.coarseTune if hasattr(zone, 'coarseTune') else 0,
            "fine_tune": zone.fineTune if hasattr(zone, 'fineTune') else 0,
            "scale_tuning": zone.scaleTuning if hasattr(zone, 'scaleTuning') else 100,
            "overriding_root_key": zone.overridingRootKey if hasattr(zone, 'overridingRootKey') else -1,

            # Sample modes and exclusive class
            "sample_modes": zone.sampleModes if hasattr(zone, 'sampleModes') else 0,
            "exclusive_class": zone.exclusiveClass if hasattr(zone, 'exclusiveClass') else 0
        }

        # For drums, simplify parameters according to SF2 drum conventions
        if is_drum:
            partial_params["use_filter_env"] = False
            partial_params["use_pitch_env"] = False
            partial_params["amp_envelope"]["attack"] = max(0.001, partial_params["amp_envelope"]["attack"] * 0.1)
            partial_params["amp_envelope"]["decay"] = max(0.01, partial_params["amp_envelope"]["decay"] * 0.5)
            partial_params["amp_envelope"]["sustain"] = 0.0
            # Drums typically don't use LFOs
            partial_params["lfo1"]["rate"] = 0.0
            partial_params["lfo2"]["rate"] = 0.0

        return partial_params
