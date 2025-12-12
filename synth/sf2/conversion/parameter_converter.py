"""
SF2 Parameter Converter

Handles conversion of SF2 parameters to XG synthesizer format.
Enhanced with comprehensive error handling, unicode support, and sample normalization.
"""

import math
import logging
from typing import Dict, List, Any, Optional, Union
from ..types import SF2InstrumentZone, SF2PresetZone, SF2Instrument

# Set up logging for parameter conversion issues
logger = logging.getLogger('SF2ParameterConverter')


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
        # SoundFont uses: time = 0.001 * 10^(value/1200)
        # For negative values, this gives times < 0.001 seconds
        time_seconds = 0.001 * (10 ** (time_cents / 1200.0))

        # Clamp to reasonable minimum (0.001 seconds = 1ms)
        # but allow the formula to work for negative values
        return max(0.0001, time_seconds)

    def convert_lfo_rate(self, lfo_value: int) -> float:
        """
        Convert LFO rate from SF2 cents to Hz.

        Args:
            lfo_value: LFO rate in SF2 cents above 8.176 Hz

        Returns:
            LFO rate in Hz
        """
        if lfo_value <= -12000:
            return 0.1  # Minimum rate

        # SF2 LFO rate is in cents above 8.176 Hz
        # Same formula as filter cutoff: base * 2^(value/1200)
        hz = 8.176 * (2 ** (lfo_value / 1200.0))

        # Clamp to reasonable audio range (0.1 Hz to 50 Hz)
        return max(0.1, min(50.0, hz))

    def convert_lfo_delay(self, delay_value: int) -> float:
        """
        Convert LFO delay from SF2 time cents to seconds.

        Args:
            delay_value: LFO delay in SF2 time cents

        Returns:
            LFO delay in seconds
        """
        if delay_value <= -12000:
            return 0.0

        # SF2 LFO delay uses same logarithmic time conversion as envelopes
        seconds = 0.001 * (10 ** (delay_value / 1200.0))

        # Clamp to reasonable range (0.0 to 30.0 seconds)
        return max(0.0, min(30.0, seconds))

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
        Convert filter resonance from SF2 format to XG linear gain factor.

        Args:
            resonance_value: Filter resonance in SF2 centibels (1/10 dB)

        Returns:
            Filter resonance as linear gain factor (1.0 = no boost, >1.0 = resonance boost)
        """
        # SF2 resonance is in centibels (1/10 dB)
        # Convert centibels to linear gain: 10^(value/200)
        # Example: +200 cb = +2 dB = 1.2589 linear gain
        if resonance_value <= 0:
            return 1.0  # No resonance boost (unity gain)

        linear_gain = 10 ** (resonance_value / 200.0)

        # Clamp to reasonable range to prevent extreme values
        # Allow up to +48 dB boost (resonance_value = 9600 cb)
        return max(1.0, min(251.0, linear_gain))  # 251 = 10^(9600/200)

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
        return min(1.0, max(0.0, amp))  # Clamp to valid range

    def validate_envelope_parameters(self, env_dict: Dict[str, float], envelope_type: str = "unknown") -> Dict[str, float]:
        """
        Validate envelope parameters to ensure they don't cause issues.

        Args:
            env_dict: Envelope parameter dictionary
            envelope_type: Type of envelope for logging (e.g., "amplitude", "filter")

        Returns:
            Validated envelope dictionary
        """
        validated = {}
        was_clamped = False

        # Validate time parameters (should be >= 0)
        for param in ['delay', 'attack', 'hold', 'decay', 'release']:
            original_value = env_dict.get(param, 0.0)
            value = max(0.0, original_value)

            # Cap extremely long times to prevent issues
            max_time = 60.0  # Max 60 seconds
            if value > max_time:
                logger.warning(f"{envelope_type} envelope {param} time clamped from {value:.3f}s to {max_time:.1f}s")
                value = max_time
                was_clamped = True
            elif original_value < 0:
                logger.warning(f"{envelope_type} envelope {param} time was negative ({original_value:.6f}s), clamped to 0.0s")
                was_clamped = True

            validated[param] = value

        # Validate sustain level (0.0 to 1.0 for amplitude envelopes)
        original_sustain = env_dict.get('sustain', 0.7)
        sustain = max(0.0, min(1.0, original_sustain))
        if sustain != original_sustain:
            logger.warning(f"{envelope_type} envelope sustain clamped from {original_sustain:.3f} to {sustain:.3f}")
            was_clamped = True
        validated['sustain'] = sustain

        # Validate key scaling (-10.0 to 10.0 reasonable range)
        key_scaling = env_dict.get('key_scaling', 0.0)
        clamped_scaling = max(-10.0, min(10.0, key_scaling))
        if clamped_scaling != key_scaling:
            logger.warning(f"{envelope_type} envelope key scaling clamped from {key_scaling:.1f} to {clamped_scaling:.1f}")
            was_clamped = True
        validated['key_scaling'] = clamped_scaling

        if was_clamped:
            logger.info(f"Envelope parameter validation completed for {envelope_type} envelope")

        return validated

    def validate_lfo_parameters(self, lfo_dict: Dict[str, float]) -> Dict[str, float]:
        """
        Validate LFO parameters.

        Args:
            lfo_dict: LFO parameter dictionary

        Returns:
            Validated LFO dictionary
        """
        validated = {}

        # Validate rate (reasonable 0.1 to 30 Hz range)
        rate = max(0.1, min(30.0, lfo_dict.get('rate', 5.0)))
        validated['rate'] = rate

        # Validate depth (0.0 to 5.0 reasonable range)
        depth = max(0.0, min(5.0, lfo_dict.get('depth', 0.5)))
        validated['depth'] = depth

        # Validate delay (0.0 to 30.0 seconds)
        delay = max(0.0, min(30.0, lfo_dict.get('delay', 0.0)))
        validated['delay'] = delay

        validated['waveform'] = lfo_dict.get('waveform', 'sine')

        return validated

    def validate_filter_parameters(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate filter parameters.

        Args:
            filter_dict: Filter parameter dictionary

        Returns:
            Validated filter dictionary
        """
        validated = filter_dict.copy()

        # Validate cutoff frequency (20 Hz to 20 kHz)
        cutoff = max(20.0, min(20000.0, filter_dict.get('cutoff', 1000.0)))
        validated['cutoff'] = cutoff

        # Validate resonance (0.0 to 2.0 reasonable range)
        resonance = max(0.0, min(2.0, filter_dict.get('resonance', 0.7)))
        validated['resonance'] = resonance

        # Ensure key_follow is reasonable (-200 to 200 cents/opt)
        key_follow = max(-200.0, min(200.0, filter_dict.get('key_follow', 0.5)))
        validated['key_follow'] = key_follow

        return validated

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
        # Use SF2 envelope generator codes directly:
        # 34: attackVolEnv, 36: decayVolEnv, 38: releaseVolEnv
        # Use musical defaults instead of SF2 "fastest" defaults when generators missing
        amp_attack = zone.generators.get(34, 2000)    # Default: ~0.046s (musical attack)
        amp_decay = zone.generators.get(36, 2800)     # Default: ~0.2s (musical decay)
        amp_release = zone.generators.get(38, 3200)   # Default: ~0.4s (musical release)

        # Convert envelope times using complete SF2 envelope parameters
        envelope_times = self.convert_envelope_times(
            amp_attack, amp_decay, amp_release
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

        # Apply parameter validation to ensure all values are reasonable
        validated_envelope_times = self.validate_envelope_parameters({
            'delay': self.convert_time_cents_to_seconds(amp_attack),
            'attack': self.convert_time_cents_to_seconds(amp_decay),
            'decay': self.convert_time_cents_to_seconds(amp_release),
        })

        # Check modulation routing to assign SF2 modulation envelope correctly
        # SF2 has one modulation envelope that gets routed to pitch, filter, or both
        mod_env_to_pitch = getattr(zone, 'modEnvToPitch', 0)
        mod_env_to_filter = getattr(zone, 'modEnvToFilterFc', 0)

        # Initialize envelopes with defaults
        pitch_envelope = self._create_default_pitch_envelope()
        filter_envelope = self._create_default_filter_envelope()

        # Assign SF2 modulation envelope based on routing
        if mod_env_to_pitch and not mod_env_to_filter:
            # Modulation envelope affects pitch
            pitch_envelope = self._convert_sf2_modulation_envelope(zone)
        elif mod_env_to_filter and not mod_env_to_pitch:
            # Modulation envelope affects filter
            filter_envelope = self._convert_sf2_modulation_envelope(zone)
        elif mod_env_to_pitch and mod_env_to_filter:
            # Both pitch and filter modulation - prioritize based on strength
            pitch_strength = abs(mod_env_to_pitch)
            filter_strength = abs(mod_env_to_filter)
            if pitch_strength >= filter_strength:
                pitch_envelope = self._convert_sf2_modulation_envelope(zone)
            else:
                filter_envelope = self._convert_sf2_modulation_envelope(zone)
        # If neither is set, modulation envelope remains unused (defaults)

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

            # Amplitude envelope (complete SF2 envelope) - SF2 generator types:
            # 33: delayVolEnv, 34: attackVolEnv, 35: holdVolEnv
            # 36: decayVolEnv, 37: sustainVolEnv, 38: releaseVolEnv
            # 40: keynumToVolEnvDecay
            # Use musical defaults when generators are missing
            "amp_envelope": {
                "delay": self.convert_time_cents_to_seconds(zone.generators.get(33, -12000)),
                "attack": self.convert_time_cents_to_seconds(zone.generators.get(34, 2000)),    # ~0.046s default
                "hold": self.convert_time_cents_to_seconds(zone.generators.get(35, -12000)),
                "decay": self.convert_time_cents_to_seconds(zone.generators.get(36, 2800)),    # ~0.2s default
                "sustain": self.cents_to_amplitude(zone.generators.get(37, 0)),               # ~1.0 sustain default (no decay)
                "release": self.convert_time_cents_to_seconds(zone.generators.get(38, 3200)),  # ~0.4s default
                "key_scaling": zone.generators.get(40, 0) / 1200.0
            },

            # Pitch and filter envelopes (assigned based on SF2 modulation routing)
            "pitch_envelope": pitch_envelope,
            "filter_envelope": filter_envelope,

            # Filter (complete SF2 filter support)
            "filter": {
                "cutoff": cutoff,
                "resonance": resonance,
                "type": "lowpass",
                "key_follow": 0.5
            },

            # LFO parameters (complete SF2 LFO support) - SF2 generator types:
            # 21: delayModLFO, 22: freqModLFO for LFO1 (Tremolo/Filters)
            # 23: delayVibLFO, 24: freqVibLFO for LFO2 (Vibrato)
            "lfo1": {
                "waveform": "sine",
                "rate": self.convert_lfo_rate(zone.generators.get(22, 0)),
                "depth": 0.5,
                "delay": self.convert_lfo_delay(zone.generators.get(21, 0))
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": self.convert_lfo_rate(zone.generators.get(24, 0)),
                "depth": 0.3,
                "delay": self.convert_lfo_delay(zone.generators.get(23, 0))
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

        # Apply final parameter validation
        if "amp_envelope" in partial_params:
            partial_params["amp_envelope"] = self.validate_envelope_parameters(partial_params["amp_envelope"])
        if "filter_envelope" in partial_params:
            partial_params["filter_envelope"] = self.validate_envelope_parameters(partial_params["filter_envelope"])
        if "lfo1" in partial_params:
            partial_params["lfo1"] = self.validate_lfo_parameters(partial_params["lfo1"])
        if "lfo2" in partial_params:
            partial_params["lfo2"] = self.validate_lfo_parameters(partial_params["lfo2"])
        if "filter" in partial_params:
            partial_params["filter"] = self.validate_filter_parameters(partial_params["filter"])

        return partial_params

    def validate_parameter_conversion(self, zone: SF2InstrumentZone, converted_params: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate that parameter conversion preserves the intent of original SF2 parameters.

        This method provides debugging information to ensure envelope, LFO, and filter
        parameters are being converted correctly from SF2 generators.

        Args:
            zone: Original SF2 zone
            converted_params: XG parameters after conversion

        Returns:
            Dictionary of validation warnings/errors (empty if all good)
        """
        warnings = {}

        # Check envelope conversion
        try:
            amp_env = converted_params.get('amp_envelope', {})
            if 'delay' in amp_env and amp_env['delay'] >= 60.0:
                warnings["amp_delay"] = f"Amp envelope delay {amp_env['delay']:.1f}s was clamped to maximum"
            if 'attack' in amp_env and amp_env['attack'] <= 0.001:
                warnings["amp_attack"] = f"Amp envelope attack {amp_env['attack']:.6f}s may be too fast"
        except:
            warnings["amp_envelope"] = "Invalid amp envelope conversion"

        # Check filter parameters
        try:
            filter_params = converted_params.get('filter', {})
            if 'cutoff' in filter_params:
                cutoff = filter_params['cutoff']
                if cutoff < 20.0 or cutoff > 20000.0:
                    warnings["filter_cutoff"] = f"Filter cutoff {cutoff:.1f}Hz outside normal range"
        except:
            warnings["filter"] = "Invalid filter parameter conversion"

        # Check LFO parameters
        for lfo_name in ['lfo1', 'lfo2']:
            lfo_params = converted_params.get(lfo_name, {})
            try:
                rate = lfo_params.get('rate', 0.0)
                if rate < 0.1 and rate > 0.0:
                    warnings[f"{lfo_name}_rate"] = f"LFO rate {rate:.3f}Hz may be too slow for vibrato"
                elif rate == 0.0:
                    warnings[f"{lfo_name}_rate"] = f"LFO rate is zero - LFO will not function"
            except:
                warnings[lfo_name] = f"Invalid {lfo_name} parameter conversion"

        # Verify critical generators were accessed
        critical_generators = [33, 34, 36, 37, 38, 25, 26, 28, 29, 30, 22, 24]
        critical_missing = []
        for gen_code in critical_generators:
            if gen_code not in zone.generators:
                critical_missing.append(gen_code)

        if critical_missing:
            warnings["missing_generators"] = f"Critical SF2 generators {critical_missing} were not found - envelope/LFO parameters may be default"

        return warnings

    def _create_default_pitch_envelope(self) -> Dict[str, float]:
        """Create default XG pitch envelope (no modulation)."""
        return {
            "delay": 0.0,
            "attack": 0.0,
            "hold": 0.0,
            "decay": 0.0,
            "sustain": 1.0,
            "release": 0.0,
            "key_scaling": 0.0
        }

    def _create_default_filter_envelope(self) -> Dict[str, float]:
        """Create default XG filter envelope (no modulation)."""
        return {
            "delay": 0.0,
            "attack": 0.0,
            "hold": 0.0,
            "decay": 0.0,
            "sustain": 1.0,
            "release": 0.0,
            "key_scaling": 0.0
        }

    def _convert_sf2_modulation_envelope(self, zone: SF2InstrumentZone) -> Dict[str, float]:
        """Convert SF2 modulation envelope to XG format."""
        return {
            "delay": self.convert_time_cents_to_seconds(zone.generators.get(25, -12000)),  # delayModEnv
            "attack": self.convert_time_cents_to_seconds(zone.generators.get(26, -12000)),  # attackModEnv
            "hold": self.convert_time_cents_to_seconds(zone.generators.get(27, -12000)),   # holdModEnv
            "decay": self.convert_time_cents_to_seconds(zone.generators.get(28, -12000)),  # decayModEnv
            "sustain": self.cents_to_amplitude(zone.generators.get(29, 0)),                # sustainModEnv
            "release": self.convert_time_cents_to_seconds(zone.generators.get(30, -12000)), # releaseModEnv
            "key_scaling": zone.generators.get(32, 0) / 1200.0  # keynumToModEnvDecay
        }
