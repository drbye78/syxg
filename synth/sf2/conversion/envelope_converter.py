"""
SF2 Envelope Converter

Handles conversion of SF2 envelope parameters to XG format.
"""

from typing import Dict, List, Any
from ..types import SF2InstrumentZone


class EnvelopeConverter:
    """
    Converts SF2 envelope parameters to XG synthesizer format.
    """

    def __init__(self):
        """Initialize envelope converter."""
        pass

    def convert_amplitude_envelope(self, zone: SF2InstrumentZone) -> Dict[str, Any]:
        """
        Convert SF2 amplitude envelope to XG format.

        Args:
            zone: SF2 instrument zone

        Returns:
            XG amplitude envelope parameters
        """
        # Convert time values from time cents to seconds
        delay = self._time_cents_to_seconds(zone.DelayVolEnv)
        attack = self._time_cents_to_seconds(zone.AttackVolEnv)
        hold = self._time_cents_to_seconds(zone.HoldVolEnv)
        decay = self._time_cents_to_seconds(zone.DecayVolEnv)
        release = self._time_cents_to_seconds(zone.ReleaseVolEnv)

        # Convert sustain from centibels to amplitude
        sustain = self._cents_to_amplitude(zone.SustainVolEnv)

        # Key scaling for volume envelope
        key_scaling = zone.KeynumToVolEnvDecay / 1200.0

        return {
            "delay": delay,
            "attack": attack,
            "hold": hold,
            "decay": decay,
            "sustain": sustain,
            "release": release,
            "key_scaling": key_scaling
        }

    def convert_filter_envelope(self, zone: SF2InstrumentZone) -> Dict[str, Any]:
        """
        Convert SF2 filter envelope to XG format.

        Args:
            zone: SF2 instrument zone

        Returns:
            XG filter envelope parameters
        """
        # Convert time values from time cents to seconds
        delay = self._time_cents_to_seconds(zone.DelayFilEnv)
        attack = self._time_cents_to_seconds(zone.AttackFilEnv)
        hold = self._time_cents_to_seconds(zone.HoldFilEnv)
        decay = self._time_cents_to_seconds(zone.DecayFilEnv)
        release = self._time_cents_to_seconds(zone.ReleaseFilEnv)

        # Convert sustain from centibels to amplitude
        sustain = self._cents_to_amplitude(zone.SustainFilEnv)

        # Key scaling for filter envelope
        key_scaling = zone.KeynumToModEnvDecay / 1200.0

        return {
            "delay": delay,
            "attack": attack,
            "hold": hold,
            "decay": decay,
            "sustain": sustain,
            "release": release,
            "key_scaling": key_scaling
        }

    def convert_pitch_envelope(self, zone: SF2InstrumentZone) -> Dict[str, Any]:
        """
        Convert SF2 pitch envelope to XG format.

        Args:
            zone: SF2 instrument zone

        Returns:
            XG pitch envelope parameters
        """
        # Convert time values from time cents to seconds
        delay = self._time_cents_to_seconds(zone.DelayPitchEnv)
        attack = self._time_cents_to_seconds(zone.AttackPitchEnv)
        hold = self._time_cents_to_seconds(zone.HoldPitchEnv)
        decay = self._time_cents_to_seconds(zone.DecayPitchEnv)
        release = self._time_cents_to_seconds(zone.ReleasePitchEnv)

        # Convert sustain from centibels to amplitude
        sustain = self._cents_to_amplitude(zone.SustainPitchEnv)

        return {
            "delay": delay,
            "attack": attack,
            "hold": hold,
            "decay": decay,
            "sustain": sustain,
            "release": release
        }

    def calculate_average_envelope(self, envelopes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate average envelope from multiple zones.

        Args:
            envelopes: List of envelope dictionaries

        Returns:
            Average envelope parameters
        """
        if not envelopes:
            return self._get_default_envelope()

        total = {
            "delay": 0.0,
            "attack": 0.0,
            "hold": 0.0,
            "decay": 0.0,
            "sustain": 0.0,
            "release": 0.0,
            "key_scaling": 0.0
        }

        count = len(envelopes)

        for env in envelopes:
            total["delay"] += env.get("delay", 0.0)
            total["attack"] += env.get("attack", 0.01)
            total["hold"] += env.get("hold", 0.0)
            total["decay"] += env.get("decay", 0.3)
            total["sustain"] += env.get("sustain", 0.7)
            total["release"] += env.get("release", 0.5)
            total["key_scaling"] += env.get("key_scaling", 0.0)

        return {
            "delay": total["delay"] / count,
            "attack": total["attack"] / count,
            "hold": total["hold"] / count,
            "decay": total["decay"] / count,
            "sustain": total["sustain"] / count,
            "release": total["release"] / count,
            "key_scaling": total["key_scaling"] / count
        }

    def _time_cents_to_seconds(self, time_cents: int) -> float:
        """
        Convert time cents to seconds.

        Args:
            time_cents: Time in centiseconds

        Returns:
            Time in seconds
        """
        if time_cents <= -32768:
            return 0.0

        # SoundFont formula: time = 0.001 * 10^(value/1200)
        return 0.001 * (10 ** (time_cents / 1200.0))

    def _cents_to_amplitude(self, bells: int) -> float:
        """
        Convert centibels to amplitude.

        Args:
            bells: Value in centibels

        Returns:
            Amplitude (0.0 to 1.0)
        """
        import math
        amp = math.pow(10.0, bells / -200.0)
        return min(1.0, amp)

    def _get_default_envelope(self) -> Dict[str, Any]:
        """
        Get default envelope parameters.

        Returns:
            Default envelope dictionary
        """
        return {
            "delay": 0.0,
            "attack": 0.01,
            "hold": 0.0,
            "decay": 0.3,
            "sustain": 0.7,
            "release": 0.5,
            "key_scaling": 0.0
        }
