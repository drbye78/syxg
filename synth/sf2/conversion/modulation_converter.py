"""
SF2 Modulation Converter

Handles conversion of SF2 modulation parameters to XG format.
"""

from typing import Dict, List, Any, Optional
from ..types import SF2Modulator, SF2InstrumentZone


class ModulationConverter:
    """
    Converts SF2 modulation parameters to XG synthesizer format.
    """

    # SF2 to XG destination mapping
    SF2_TO_XG_DESTINATIONS = {
        5: "pitch",  # modLfoToPitch
        6: "pitch",  # vibLfoToPitch
        7: "pitch",  # modEnvToPitch
        8: "filter_cutoff",  # initialFilterFc
        10: "filter_cutoff",  # modLfoToFilterFc
        11: "filter_cutoff",  # modEnvToFilterFc
        13: "amplitude",  # modLfoToVolume
        17: "pan",  # pan
        25: "amp_attack",  # delayVolEnv
        26: "filter_attack",  # attackModEnv
        27: "filter_hold",  # holdModEnv
        28: "filter_decay",  # decayModEnv
        29: "filter_sustain",  # sustainModEnv
        30: "filter_release",  # releaseModEnv
        31: "filter_hold",  # keynumToModEnvHold
        32: "filter_decay",  # keynumToModEnvDecay
        33: "amp_attack",  # delayVolEnv
        34: "amp_attack",  # attackVolEnv
        35: "amp_hold",  # holdVolEnv
        36: "amp_decay",  # decayVolEnv
        37: "amp_sustain",  # sustainVolEnv
        38: "amp_release",  # releaseVolEnv
        39: "amp_hold",  # keynumToVolEnvHold
        40: "amp_decay",  # keynumToVolEnvDecay
        51: "coarse_tune",  # coarseTune
        52: "fine_tune",  # fineTune
        77: "tremolo_depth",  # cc_tremolo_depth
        78: "tremolo_rate"  # cc_tremolo_rate
    }

    # SF2 to XG source mapping
    SF2_TO_XG_SOURCES = {
        "note_on_velocity": "velocity",
        "channel_aftertouch": "after_touch",
        "cc_mod_wheel": "mod_wheel",
        "modLFO": "lfo1",
        "vibLFO": "lfo2",
        "modEnv": "amp_env",
        "pitch_wheel": "pitch_wheel",
        "cc_brightness": "brightness",
        "cc_tremolo_depth": "tremolo_depth",
        "cc_tremolo_rate": "tremolo_rate",
        "cc_portamento_control": "portamento"
    }

    def __init__(self):
        """Initialize modulation converter."""
        pass

    def convert_modulator(self, modulator: SF2Modulator) -> Optional[Dict[str, Any]]:
        """
        Convert SF2 modulator to XG modulation route.

        Args:
            modulator: SF2 modulator

        Returns:
            XG modulation route dictionary or None if unsupported
        """
        # Get source name
        source_name = self._get_modulator_source_name(modulator)
        if not source_name:
            return None

        # Get destination name
        destination_name = self._get_modulator_destination_name(modulator.destination)
        if not destination_name:
            return None

        # Convert amount
        amount = self._normalize_modulator_amount(modulator.amount, modulator.destination)

        # Determine polarity
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0

        return {
            "source": source_name,
            "destination": destination_name,
            "amount": amount * polarity,
            "velocity_sensitivity": 0.0,
            "key_scaling": 0.0
        }

    def process_zone_modulators(self, zone: SF2InstrumentZone) -> Dict[str, Any]:
        """
        Process all modulators in a zone and extract useful parameters.

        Args:
            zone: SF2 instrument zone

        Returns:
            Dictionary with extracted modulation parameters
        """
        params = {
            "lfo1_to_pitch": 0.0,
            "lfo2_to_pitch": 0.0,
            "env_to_pitch": 0.0,
            "aftertouch_to_pitch": 0.0,
            "lfo_to_filter": 0.0,
            "env_to_filter": 0.0,
            "aftertouch_to_filter": 0.0,
            "tremolo_depth": 0.0,
            "vibrato_depth": 0.0,
            "vibrato_rate": 5.0,
            "vibrato_delay": 0.0
        }

        for modulator in zone.modulators:
            self._process_single_modulator(zone, modulator, params)

        return params

    def calculate_modulation_params(self, zones: List[SF2InstrumentZone]) -> Dict[str, Any]:
        """
        Calculate modulation parameters from multiple zones.

        Args:
            zones: List of SF2 instrument zones

        Returns:
            Dictionary with modulation parameters
        """
        # Start with default values
        params = {
            "lfo1_to_pitch": 0.0,
            "lfo2_to_pitch": 0.0,
            "env_to_pitch": 0.0,
            "aftertouch_to_pitch": 0.0,
            "lfo_to_filter": 0.0,
            "env_to_filter": 0.0,
            "aftertouch_to_filter": 0.0,
            "tremolo_depth": 0.0,
            "vibrato_depth": 0.0,
            "vibrato_rate": 5.0,
            "vibrato_delay": 0.0
        }

        # Accumulate values from all zones
        for zone in zones:
            zone_params = self.process_zone_modulators(zone)
            for key in params:
                params[key] += zone_params[key]

        # Average values across zones
        num_zones = len(zones)
        if num_zones > 0:
            for key in params:
                if key not in ["vibrato_rate", "vibrato_delay"]:  # Don't average these
                    params[key] /= num_zones
                # Clamp to reasonable ranges
                if key not in ["vibrato_rate", "vibrato_delay"]:
                    params[key] = max(0.0, min(1.0, params[key]))

        return params

    def _get_modulator_source_name(self, modulator: SF2Modulator) -> Optional[str]:
        """
        Get modulation source name from SF2 modulator.

        Args:
            modulator: SF2 modulator

        Returns:
            Source name or None if unsupported
        """
        # Check main source
        if modulator.source_oper in [0, 1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 32, 33, 34, 35, 36, 37, 38, 39, 40, 74, 77, 78, 84]:
            source_name = self._source_oper_to_name(modulator.source_oper)

            # Add index for CC controllers
            if source_name.startswith("cc_") and modulator.source_index > 0:
                source_name = f"{source_name}_{modulator.source_index}"

            return source_name

        # Check for LFO sources
        if modulator.source_oper == 5:
            return "modLFO"
        elif modulator.source_oper == 6:
            return "vibLFO"
        elif modulator.source_oper == 7:
            return "modEnv"
        elif modulator.source_oper == 13:
            return "channel_aftertouch"

        return None

    def _get_modulator_destination_name(self, destination: int) -> Optional[str]:
        """
        Get modulation destination name from SF2 destination code.

        Args:
            destination: SF2 destination code

        Returns:
            Destination name or None if unsupported
        """
        return self.SF2_TO_XG_DESTINATIONS.get(destination)

    def _normalize_modulator_amount(self, amount: int, destination: int) -> float:
        """
        Normalize modulation amount based on destination.

        Args:
            amount: Raw modulation amount
            destination: Modulation destination

        Returns:
            Normalized amount
        """
        abs_amount = abs(amount)

        # Pitch modulation (in cents)
        if destination in [5, 6, 7]:
            return abs_amount / 100.0  # 100 = 1 cent

        # Filter cutoff
        elif destination in [8, 10, 11]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Amplitude
        elif destination in [13, 31, 33, 34, 35]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Pan
        elif destination == 17:
            return abs_amount / 100.0  # 0-100 in SF2 -> 0-1

        # Tremolo
        elif destination in [77, 78]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Default normalization
        else:
            return abs_amount / 1000.0

    def _process_single_modulator(self, zone: SF2InstrumentZone, modulator: SF2Modulator, params: Dict[str, Any]):
        """
        Process a single modulator and update zone parameters.

        Args:
            zone: SF2 instrument zone
            modulator: SF2 modulator
            params: Parameters dictionary to update
        """
        source_name = self._get_modulator_source_name(modulator)
        if not source_name:
            return

        destination = modulator.destination
        amount = self._normalize_modulator_amount(modulator.amount, destination)
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0

        # Update zone attributes and params dictionary
        if destination == 5:  # modLfoToPitch
            zone.mod_lfo_to_pitch = amount * polarity
            params["lfo1_to_pitch"] += amount * polarity
        elif destination == 6:  # vibLfoToPitch
            zone.vib_lfo_to_pitch = amount * polarity
            params["lfo2_to_pitch"] += amount * polarity
            params["vibrato_depth"] += amount * polarity
        elif destination == 7:  # modEnvToPitch
            zone.mod_env_to_pitch = amount * polarity
            params["env_to_pitch"] += amount * polarity
        elif destination == 10:  # modLfoToFilterFc
            zone.mod_lfo_to_filter = amount * polarity
            params["lfo_to_filter"] += amount * polarity
        elif destination == 11:  # modEnvToFilterFc
            zone.mod_env_to_filter = amount * polarity
            params["env_to_filter"] += amount * polarity
        elif destination == 13:  # modLfoToVolume
            zone.mod_lfo_to_volume = amount * polarity
            params["tremolo_depth"] += amount * polarity
        elif destination == 77:  # cc_tremolo_depth
            zone.tremolo_depth = amount * polarity
            params["tremolo_depth"] += amount * polarity
        elif destination == 84:  # cc_portamento_control
            zone.portamento_to_pitch = amount * polarity

    def _source_oper_to_name(self, source_oper: int) -> str:
        """
        Convert SF2 source operator to source name.

        Args:
            source_oper: SF2 source operator code

        Returns:
            Source name
        """
        source_map = {
            0: "no_controller",
            1: "note_on_velocity",
            2: "note_on_key_number",
            3: "polyphonic_aftertouch",
            4: "channel_aftertouch",
            5: "pitch_wheel",
            16: "cc_mod_wheel",
            17: "cc_breath_controller",
            18: "cc_unknown_18",
            19: "cc_foot_controller",
            20: "cc_portamento_time",
            21: "cc_data_entry",
            22: "cc_volume",
            23: "cc_balance",
            32: "cc_bank_select_lsb",
            33: "cc_mod_wheel_lsb",
            34: "cc_breath_controller_lsb",
            35: "cc_unknown_35_lsb",
            36: "cc_foot_controller_lsb",
            37: "cc_portamento_time_lsb",
            38: "cc_data_entry_lsb",
            39: "cc_volume_lsb",
            40: "cc_balance_lsb",
            74: "cc_brightness",
            77: "cc_tremolo_depth",
            78: "cc_tremolo_rate",
            84: "cc_portamento_control"
        }

        return source_map.get(source_oper, "unknown_source")
