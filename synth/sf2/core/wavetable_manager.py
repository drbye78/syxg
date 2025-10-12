"""
SF2 Wavetable Manager

Refactored version of Sf2WavetableManager with modular design.
"""

import threading
from typing import Dict, List, Tuple, Optional, Union, Any
from ..types import SF2InstrumentZone
from ..core import SoundFontManager
from ..conversion import ParameterConverter, EnvelopeConverter, ModulationConverter


class WavetableManager:
    """
    Wavetable sample manager based on SoundFont 2.0 files.
    Provides interface for XG Tone Generator with support for multiple layers
    and drums. Implements lazy loading of samples and caching.
    """

    # Maximum sample cache size (in samples, not bytes)
    MAX_CACHE_SIZE = 50000000  # ~200 MB for 16-bit samples

    def __init__(self, sf2_paths: Union[str, List[str]], cache_size: Optional[int] = None, param_cache=None):
        """
        Initialize SoundFont manager.

        Args:
            sf2_paths: path to SoundFont file (.sf2) or list of paths
            cache_size: maximum cache size in samples (default MAX_CACHE_SIZE)
            param_cache: optional parameter cache for performance optimization
        """
        self.lock = threading.Lock()

        # Support for single or multiple SF2 files
        self.sf2_paths = sf2_paths if isinstance(sf2_paths, list) else [sf2_paths]

        # List of SoundFont managers for each SF2 file
        self.soundfonts: List[SoundFontManager] = []

        # Settings for each SF2 file
        self.bank_blacklists: Dict[str, List[int]] = {}
        self.preset_blacklists: Dict[str, List[Tuple[int, int]]] = {}
        self.bank_mappings: Dict[str, Dict[int, int]] = {}

        # Performance optimization: parameter cache
        self.param_cache = param_cache

        # Initialize converters
        self.parameter_converter = ParameterConverter()
        self.envelope_converter = EnvelopeConverter()
        self.modulation_converter = ModulationConverter()
        self.partial_map = {}

        # Initialize SoundFont files
        self._initialize_soundfonts()

    def _initialize_soundfonts(self):
        """Initialize SoundFont files"""
        for i, sf2_path in enumerate(self.sf2_paths):
            try:
                # Create SoundFont manager for this file
                soundfont = SoundFontManager(sf2_path, i)
                self.soundfonts.append(soundfont)
            except Exception as e:
                print(f"Error initializing SF2 file {sf2_path}: {str(e)}")

    def get_program_parameters(self, program: int, bank: int = 0, note: int = 60, velocity: int = 64) -> Optional[Dict[str, Any]]:
        """
        Get program parameters in format compatible with XGToneGenerator.
        Implements lazy loading with complete SF2 support including global zones.

        Args:
            program: program number (0-127)
            bank: bank number (0-16383)
            note: MIDI note number for zone matching
            velocity: MIDI velocity for zone matching

        Returns:
            dictionary with program parameters or None if not found
        """
        # Find the preset and its SoundFont by bank and program
        soundfont_obj = None
        preset_obj = None

        # Search for preset in all SoundFont files
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                soundfont_obj = soundfont
                preset_obj = preset
                break

        # If preset not found, return None
        if not soundfont_obj or not preset_obj:
            return None

        # Get instruments from the corresponding SoundFont
        instruments = soundfont_obj.instruments

        # Gather all merged zones for this preset that match the note and velocity
        all_merged_zones = []
        global_preset_zones = []  # Preset-level global zones
        global_instrument_zones = []  # Instrument-level global zones

        for preset_zone in preset_obj.zones:
            # Check if this is a global preset zone (no instrument assigned)
            if preset_zone.instrument_index == -1 or preset_zone.instrument_index >= len(instruments):
                global_preset_zones.append(preset_zone)
                continue

            instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
            if instrument is not None:
                # Process instrument zones
                for instrument_zone in instrument.zones:
                    # Check if this is a global instrument zone (no sample assigned)
                    if instrument_zone.sample_index == -1:
                        global_instrument_zones.append((preset_zone, instrument_zone))
                        continue

                    # Check if note and velocity are within the zone ranges
                    if (instrument_zone.lokey <= note <= instrument_zone.hikey and
                        instrument_zone.lovel <= velocity <= instrument_zone.hivel):
                        merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                        all_merged_zones.append(merged_zone)

        # If no zones found, return None
        if not all_merged_zones:
            return None

        # Apply global zones to all matched zones
        for global_preset in global_preset_zones:
            for zone in all_merged_zones:
                self._apply_global_zone_params(zone, global_preset, is_preset_global=True)

        for preset_zone, global_inst in global_instrument_zones:
            for zone in all_merged_zones:
                if zone.instrument_index == preset_zone.instrument_index:
                    self._apply_global_zone_params(zone, global_inst, is_preset_global=False)

        # Handle exclusive classes - group zones by exclusive class
        exclusive_groups = self._group_zones_by_exclusive_class(all_merged_zones)

        # Convert zones to partial structure parameters
        partials_params = []
        for zone in all_merged_zones:
            partial_params = self.parameter_converter.convert_zone_to_partial_params(zone)
            partials_params.append(partial_params)

        # Apply exclusive class processing
        self._apply_exclusive_class_processing(partials_params, exclusive_groups)

        # Calculate average parameters with proper weighting
        params = self._calculate_weighted_average_params(all_merged_zones, partials_params)

        return params

    def get_drum_parameters(self, note: int, program: int, bank: int = 128) -> Optional[Dict[str, Any]]:
        """
        Get drum parameters in format compatible with XGToneGenerator.

        Args:
            note: MIDI note (0-127)
            program: program number (0-127)
            bank: bank number (usually 128 for drums)

        Returns:
            dictionary with drum parameters or None if not found
        """
        # Find the preset and its SoundFont by bank and program
        soundfont_obj = None
        preset_obj = None

        # Search for preset in all SoundFont files
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                soundfont_obj = soundfont
                preset_obj = preset
                break

        # If not found in bank 128, try bank 0
        if not soundfont_obj or not preset_obj:
            for soundfont in self.soundfonts:
                preset = soundfont.get_preset(program, 0)
                if preset is not None:
                    soundfont_obj = soundfont
                    preset_obj = preset
                    break

        # If preset not found, return None
        if not soundfont_obj or not preset_obj:
            return None

        # Get instruments from the corresponding SoundFont
        instruments = soundfont_obj.instruments

        # Find zones matching the note
        matching_merged_zones = []
        for preset_zone in preset_obj.zones:
            # Check if note is in preset zone range
            if preset_zone.lokey <= note <= preset_zone.hikey:
                if preset_zone.instrument_index < len(instruments):
                    instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                    if instrument is not None:
                        # Check instrument zones
                        for instrument_zone in instrument.zones:
                            if instrument_zone.lokey <= note <= instrument_zone.hikey:
                                # Merge parameters
                                merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                                matching_merged_zones.append(merged_zone)

        # If no zones found, return None
        if not matching_merged_zones:
            return None

        # Convert zones to partial parameters
        partials_params = []
        for zone in matching_merged_zones:
            partial_params = self.parameter_converter.convert_zone_to_partial_params(zone, is_drum=True)
            partial_params["key_range_low"] = note
            partial_params["key_range_high"] = note
            partials_params.append(partial_params)

        # Base parameters for drums
        params = {
            "amp_envelope": self.envelope_converter.calculate_average_envelope(
                [p["amp_envelope"] for p in partials_params]
            ),
            "filter_envelope": self.envelope_converter.calculate_average_envelope(
                [p["filter_envelope"] for p in partials_params]
            ),
            "pitch_envelope": self.envelope_converter.calculate_average_envelope(
                [p["pitch_envelope"] for p in partials_params]
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "modulation": self.modulation_converter.calculate_modulation_params(matching_merged_zones),
            "partials": partials_params
        }

        return params

    def _merge_preset_and_instrument_params(self, preset_zone, instrument_zone) -> SF2InstrumentZone:
        """
        Merge parameters from preset zone and instrument zone.
        Uses parameter cache for performance optimization when available.

        Args:
            preset_zone: preset zone
            instrument_zone: instrument zone

        Returns:
            Merged instrument zone
        """
        # Try to use parameter cache if available
        if self.param_cache is not None:
            # Create simplified parameter dictionaries for caching
            # Optimized version: only create dictionaries when actually needed for caching
            try:
                # Try to get cached result first without creating full dictionaries
                # This avoids the expensive dictionary creation in the common case
                preset_generators_hash = hash(tuple(sorted(preset_zone.generators.items())))
                instrument_generators_hash = hash(tuple(sorted(instrument_zone.generators.items())))
                
                # Create a simple cache key from hashes
                cache_key = (preset_generators_hash, instrument_generators_hash)
                
                if hasattr(self.param_cache, '_simple_cache') and cache_key in self.param_cache._simple_cache:
                    self.param_cache._hit_count += 1
                    return self.param_cache._simple_cache[cache_key].copy()
            except:
                # Fall back to original method if hashing fails
                pass
            
            # Original method for when simple caching doesn't work
            preset_params = {
                'generators': dict(preset_zone.generators),
                'modulators': [dict(mod.__dict__) if hasattr(mod, '__dict__') else mod for mod in preset_zone.modulators]
            }
            instrument_params = {
                'generators': dict(instrument_zone.generators),
                'modulators': [dict(mod.__dict__) if hasattr(mod, '__dict__') else mod for mod in instrument_zone.modulators]
            }

            # Try to get cached result
            cached_result = self.param_cache.get_cached_params(preset_params, instrument_params)
            if cached_result is not None:
                # Reconstruct SF2InstrumentZone from cached data
                merged_zone = SF2InstrumentZone()
                for key, value in cached_result.items():
                    if hasattr(merged_zone, key):
                        setattr(merged_zone, key, value)
                return merged_zone

        # Fallback to original implementation if no cache or cache miss
        # Create a copy of the instrument zone for modification
        merged_zone = SF2InstrumentZone()

        # Copy all attributes from the instrument zone
        for attr in instrument_zone.__slots__:
            setattr(merged_zone, attr, getattr(instrument_zone, attr))

        # Apply parameters from preset as default values
        # Only if the instrument value is not set (equals 0 or standard value)

        # Process generators from preset
        for gen_type, gen_amount in preset_zone.generators.items():
            # Apply value from preset only if instrument has default value
            if gen_type == 43:  # keyRange
                if merged_zone.lokey == 0 and merged_zone.hikey == 127:
                    merged_zone.lokey = gen_amount & 0xFF
                    merged_zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 44:  # velRange
                if merged_zone.lovel == 0 and merged_zone.hivel == 127:
                    merged_zone.lovel = gen_amount & 0xFF
                    merged_zone.hivel = (gen_amount >> 8) & 0xFF

        # Merge modulators from preset and instrument
        merged_modulators = preset_zone.modulators + instrument_zone.modulators
        merged_zone.modulators = merged_modulators

        # Process modulation parameters
        self.modulation_converter.process_zone_modulators(merged_zone)

        return merged_zone

    def _calculate_average_filter(self, filters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate average filter parameters from multiple partials."""
        if not filters:
            return {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass",
                "key_follow": 0.5
            }

        total = {"cutoff": 0.0, "resonance": 0.0}
        count = len(filters)

        for f in filters:
            total["cutoff"] += f["cutoff"]
            total["resonance"] += f["resonance"]

        return {
            "cutoff": total["cutoff"] / count,
            "resonance": total["resonance"] / count,
            "type": "lowpass",
            "key_follow": 0.5
        }

    def is_drum_bank(self, bank: int) -> bool:
        """Check if a bank is a drum bank."""
        return bank == 128

    def get_partial_table(self, note: int, program: int, partial_id: int,
                         velocity: int, bank: int = 0) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Get sample data for a partial.

        Args:
            note: MIDI note (0-127)
            program: program number (0-127)
            partial_id: partial ID within the program
            velocity: velocity value (0-127)
            bank: bank number (0-16383)

        Returns:
            Sample data or None if not found
        """
        cache_key = f'{bank}-{program}-{note}-{velocity}-{partial_id}'
        header, soundfont_obj, valid = self.partial_map.get(cache_key, (None, None, False))
        if not valid:
            # Find the preset and its SoundFont by bank and program
            preset_obj = None

            # Search for preset in all SoundFont files
            for soundfont in self.soundfonts:
                preset = soundfont.get_preset(program, bank)
                if preset is not None:
                    soundfont_obj = soundfont
                    preset_obj = preset
                    break

            # If preset not found, return None
            if not soundfont_obj or not preset_obj:
                self.partial_map[cache_key] = (None, None, True)
                return None

            # Get instruments from the corresponding SoundFont
            instruments = soundfont_obj.instruments

            # Find matching zones
            matching_merged_zones = []
            for preset_zone in preset_obj.zones:
                # Check note and velocity ranges
                if (preset_zone.lokey <= note <= preset_zone.hikey and
                    preset_zone.lovel <= velocity <= preset_zone.hivel):

                    if preset_zone.instrument_index < len(instruments):
                        instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                        if instrument is not None:
                            # Check instrument zones
                            for instrument_zone in instrument.zones:
                                if (instrument_zone.lokey <= note <= instrument_zone.hikey and
                                    instrument_zone.lovel <= velocity <= instrument_zone.hivel):
                                    # Merge parameters
                                    merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                                    matching_merged_zones.append(merged_zone)

            # Check if requested partial exists
            if partial_id < len(matching_merged_zones):
                # Get the requested zone
                zone = matching_merged_zones[partial_id]

                # Get sample header
                header = soundfont_obj.get_sample_header(zone.sample_index)

        self.partial_map[cache_key] = (header, soundfont_obj, True)
        if header is None:
            return None

        # Read sample data
        return soundfont_obj.read_sample_data(header)

    def clear_cache(self):
        """Clear all sample caches."""
        for soundfont in self.soundfonts:
            soundfont.clear_cache()

    def get_available_presets(self) -> List[Tuple[int, int, str]]:
        """
        Get list of available presets.

        Returns:
            List of tuples (bank, program, name)
        """
        presets = []

        with self.lock:
            for soundfont in self.soundfonts:
                for preset in soundfont.presets:
                    presets.append((preset.bank, preset.preset, preset.name))

        return presets

    def preload_program(self, program: int, bank: int = 0):
        """
        Preload program data for faster access.

        Args:
            program: program number (0-127)
            bank: bank number (0-16383)
        """
        # Find the preset and its SoundFont
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                # Find preset index
                preset_index = -1
                for i, p in enumerate(soundfont.presets):
                    if p.preset == program and p.bank == bank:
                        preset_index = i
                        break

                if preset_index >= 0:
                    soundfont.preload_preset(preset_index)
                break

    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Set bank blacklist for specified SF2 file.

        Args:
            sf2_path: path to SF2 file
            bank_list: list of bank numbers to exclude
        """
        with self.lock:
            self.bank_blacklists[sf2_path] = bank_list.copy()

            # Apply to corresponding SoundFont
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.bank_blacklist = bank_list.copy()

    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Set preset blacklist for specified SF2 file.

        Args:
            sf2_path: path to SF2 file
            preset_list: list of (bank, program) tuples to exclude
        """
        with self.lock:
            self.preset_blacklists[sf2_path] = preset_list.copy()

            # Apply to corresponding SoundFont
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.preset_blacklist = preset_list.copy()

    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Set MIDI bank to SF2 bank mapping for specified file.

        Args:
            sf2_path: path to SF2 file
            bank_mapping: dictionary mapping midi_bank -> sf2_bank
        """
        with self.lock:
            self.bank_mappings[sf2_path] = bank_mapping.copy()

            # Apply to corresponding SoundFont
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.bank_mapping = bank_mapping.copy()

    def get_modulation_matrix(self, program: int, bank: int = 0) -> List[Dict[str, Any]]:
        """
        Get modulation matrix for a program.

        Args:
            program: program number (0-127)
            bank: bank number (0-16383)

        Returns:
            List of modulation routes
        """
        # Find the preset
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                # Collect all modulators
                all_modulators = []
                for zone in preset.zones:
                    all_modulators.extend(zone.modulators)
                    # Add modulators from instruments
                    if zone.instrument_index < len(soundfont.instruments):
                        instrument = soundfont.get_instrument(zone.instrument_index)
                        if instrument:
                            for inst_zone in instrument.zones:
                                all_modulators.extend(inst_zone.modulators)

                # Convert to XG modulation routes
                routes = []
                for modulator in all_modulators:
                    route = self.modulation_converter.convert_modulator(modulator)
                    if route:
                        routes.append(route)

                return routes

        return []

    def _apply_global_zone_params(self, zone, global_zone, is_preset_global: bool):
        """
        Apply global zone parameters to a zone.

        Args:
            zone: Target zone to modify
            global_zone: Global zone with parameters to apply
            is_preset_global: Whether this is a preset-level global zone
        """
        # Apply generators from global zone that aren't set in the target zone
        for gen_type, gen_value in global_zone.generators.items():
            # Only apply if the target zone doesn't have this generator set
            if gen_type not in zone.generators or zone.generators[gen_type] == 0:
                zone.generators[gen_type] = gen_value

        # Apply modulators from global zone
        zone.modulators.extend(global_zone.modulators)

    def _group_zones_by_exclusive_class(self, zones):
        """
        Group zones by exclusive class for voice stealing.

        Args:
            zones: List of merged zones

        Returns:
            Dictionary mapping exclusive class to list of zones
        """
        exclusive_groups = {}
        for zone in zones:
            excl_class = getattr(zone, 'exclusive_class', 0)
            if excl_class not in exclusive_groups:
                exclusive_groups[excl_class] = []
            exclusive_groups[excl_class].append(zone)
        return exclusive_groups

    def _apply_exclusive_class_processing(self, partials_params, exclusive_groups):
        """
        Apply exclusive class processing to partial parameters.

        Args:
            partials_params: List of partial parameter dictionaries
            exclusive_groups: Dictionary of exclusive class groups
        """
        # Mark exclusive classes in partial parameters
        for i, params in enumerate(partials_params):
            zone = None  # We'd need to track which zone this partial came from
            # For now, just add exclusive class info
            params["exclusive_class"] = getattr(zone, 'exclusive_class', 0) if zone else 0

    def _calculate_weighted_average_params(self, zones, partials_params):
        """
        Calculate weighted average parameters from zones with proper SF2 weighting.

        Args:
            zones: List of merged zones
            partials_params: List of partial parameter dictionaries

        Returns:
            Weighted average parameters dictionary
        """
        if not partials_params:
            return None

        # Calculate weights based on velocity and key ranges
        weights = []
        for zone in zones:
            # Weight by the size of the key/velocity range
            key_range = max(1, zone.hikey - zone.lokey + 1)
            vel_range = max(1, zone.hivel - zone.lovel + 1)
            weight = key_range * vel_range
            weights.append(weight)

        total_weight = sum(weights)

        # Calculate weighted averages
        avg_params = {
            "amp_envelope": self._weighted_average_envelope(
                [p["amp_envelope"] for p in partials_params], weights
            ),
            "filter_envelope": self._weighted_average_envelope(
                [p["filter_envelope"] for p in partials_params], weights
            ),
            "pitch_envelope": self._weighted_average_envelope(
                [p["pitch_envelope"] for p in partials_params], weights
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": self._average_lfo_params([p["lfo1"] for p in partials_params], weights),
            "lfo2": self._average_lfo_params([p["lfo2"] for p in partials_params], weights),
            "lfo3": partials_params[0]["lfo3"],  # Use first one for LFO3
            "modulation": self.modulation_converter.calculate_modulation_params(zones),
            "partials": partials_params
        }

        return avg_params

    def _weighted_average_envelope(self, envelopes, weights):
        """Calculate weighted average of envelope parameters."""
        if not envelopes:
            return self.envelope_converter._get_default_envelope()

        total_weight = sum(weights)
        avg_envelope = {}

        # Get all envelope keys
        keys = envelopes[0].keys()

        for key in keys:
            if key in ['key_scaling']:  # Don't weight these
                avg_envelope[key] = envelopes[0][key]
            else:
                weighted_sum = sum(env[key] * weight for env, weight in zip(envelopes, weights))
                avg_envelope[key] = weighted_sum / total_weight

        return avg_envelope

    def _average_lfo_params(self, lfo_params, weights):
        """Calculate weighted average of LFO parameters."""
        if not lfo_params:
            return {"waveform": "sine", "rate": 0.0, "depth": 0.0, "delay": 0.0}

        total_weight = sum(weights)
        avg_lfo = {
            "waveform": lfo_params[0]["waveform"],  # Use first waveform
            "rate": sum(lfo["rate"] * weight for lfo, weight in zip(lfo_params, weights)) / total_weight,
            "depth": sum(lfo["depth"] * weight for lfo, weight in zip(lfo_params, weights)) / total_weight,
            "delay": sum(lfo["delay"] * weight for lfo, weight in zip(lfo_params, weights)) / total_weight
        }

        return avg_lfo
