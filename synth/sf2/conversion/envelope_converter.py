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
        # SF2 Generator type codes for amplitude envelope:
        # 33: delayVolEnv, 34: attackVolEnv, 35: holdVolEnv
        # 36: decayVolEnv, 37: sustainVolEnv, 38: releaseVolEnv
        # 40: keynumToVolEnvDecay

        # Convert time values from time cents to seconds
        delay = self._time_cents_to_seconds(zone.generators.get(33, -12000))
        attack = self._time_cents_to_seconds(zone.generators.get(34, -12000))
        hold = self._time_cents_to_seconds(zone.generators.get(35, -12000))
        decay = self._time_cents_to_seconds(zone.generators.get(36, -12000))
        release = self._time_cents_to_seconds(zone.generators.get(38, -12000))

        # Convert sustain from centibels to amplitude
        sustain = self._cents_to_amplitude(zone.generators.get(37, 0))

        # Key scaling for volume envelope
        key_scaling = zone.generators.get(40, 0) / 1200.0

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
        # SF2 Generator type codes for filter envelope:
        # 25: delayModEnv, 26: attackModEnv, 27: holdModEnv
        # 28: decayModEnv, 29: sustainModEnv, 30: releaseModEnv
        # 32: keynumToModEnvDecay

        # Convert time values from time cents to seconds
        delay = self._time_cents_to_seconds(zone.generators.get(25, -12000))
        attack = self._time_cents_to_seconds(zone.generators.get(26, -12000))
        hold = self._time_cents_to_seconds(zone.generators.get(27, -12000))
        decay = self._time_cents_to_seconds(zone.generators.get(28, -12000))
        release = self._time_cents_to_seconds(zone.generators.get(30, -12000))

        # Convert sustain from centibels to amplitude
        sustain = self._cents_to_amplitude(zone.generators.get(29, 0))

        # Key scaling for filter envelope
        key_scaling = zone.generators.get(32, 0) / 1200.0

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

        Note: SF2 specification doesn't define dedicated pitch envelope stages
        like amplitude and filter envelopes. Pitch envelopes in XG synthesizers
        are typically implemented separately or through modulation to the pitch
        destination.

        Returns fixed values for XG compatibility.
        """
        # SF2 doesn't have dedicated pitch envelope generators like vol/mod env
        # Pitch modulation is typically handled through general modulators
        # Return constants for XG compatibility (disabled pitch envelope)
        return {
            "delay": 0.0,
            "attack": 0.0,
            "hold": 0.0,
            "decay": 0.0,
            "sustain": 1.0,
            "release": 0.0
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
