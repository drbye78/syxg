"""
SF2 Zone Processor - Complete SoundFont 2.0 zone processing with inheritance.

This module implements the complete SF2 zone processing specification,
including generator/modulator inheritance, zone ordering, and layering.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from ..types.dataclasses import (
    SF2Zone, SF2Generator, SF2Modulator, SF2Instrument, SF2Preset,
    SampleFormat, SF2Sample
)
from ..core.constants import GENERATOR_DEFAULTS, GeneratorType
from .data_parser import (
    PresetHeader, InstrumentHeader, SampleHeader, BagEntry,
    SF2DataParser
)

logger = logging.getLogger(__name__)


class ZoneProcessingError(Exception):
    """Exception raised when zone processing fails."""
    pass


class SF2ZoneProcessor:
    """
    Complete SF2 zone processor implementing the full specification.

    Handles zone creation, inheritance, layering, and validation
    according to SF2 specification sections 7.5, 7.7, and 8.1.

    Optimized with O(1) bag range lookups using on-demand parsing.
    """

    def __init__(self, data_parser: SF2DataParser):
        """
        Initialize the zone processor.

        Args:
            data_parser: Configured SF2DataParser with chunk data
        """
        self.data_parser = data_parser

        # Cache for processed data (headers still cached for performance)
        self._preset_headers: Optional[List[PresetHeader]] = None
        self._instrument_headers: Optional[List[InstrumentHeader]] = None
        self._sample_headers: Optional[List[SampleHeader]] = None







    def process_all_presets(self) -> List[SF2Preset]:
        """
        Process all presets with complete zone processing.

        Returns:
            List of fully processed SF2Preset objects
        """
        presets = []

        # Get all preset headers
        preset_headers = self._get_preset_headers()

        for preset_header in preset_headers:
            try:
                preset = self._process_single_preset(preset_header)
                if preset:
                    presets.append(preset)
            except Exception as e:
                logger.warning(f"Failed to process preset {preset_header.name}: {e}")
                continue

        logger.info(f"Successfully processed {len(presets)} presets")
        return presets

    def process_all_instruments(self) -> List[SF2Instrument]:
        """
        Process all instruments with complete zone processing.

        Returns:
            List of fully processed SF2Instrument objects
        """
        instruments = []

        # Get all instrument headers
        instrument_headers = self._get_instrument_headers()

        for instrument_header in instrument_headers:
            try:
                instrument = self._process_single_instrument(instrument_header)
                if instrument:
                    instruments.append(instrument)
            except Exception as e:
                logger.warning(f"Failed to process instrument {instrument_header.name}: {e}")
                continue

        logger.info(f"Successfully processed {len(instruments)} instruments")
        return instruments

    def get_preset_zones(self, bank: int, preset_num: int) -> List[SF2Zone]:
        """
        Get all zones for a specific preset with layering support.

        Args:
            bank: MIDI bank number
            preset_num: MIDI preset number

        Returns:
            List of zones that can play simultaneously (layering)
        """
        # Find the preset
        presets = self.process_all_presets()
        target_preset = None

        for preset in presets:
            if preset.bank == bank and preset.preset_number == preset_num:
                target_preset = preset
                break

        if not target_preset:
            return []

        return target_preset.get_matching_zones(60, 100)  # Default note/vel

    def _process_single_preset(self, preset_header: PresetHeader) -> Optional[SF2Preset]:
        """
        Process a single preset with complete zone processing.

        Args:
            preset_header: Preset header data

        Returns:
            Fully processed SF2Preset, or None on error
        """
        try:
            # Create preset object
            preset = SF2Preset(
                name=preset_header.name,
                bank=preset_header.bank,
                preset_number=preset_header.preset,
                zones=[]
            )

            # Get zones for this preset using preset_index (O(1) lookup!)
            zones = self._create_preset_zones_by_index(preset_header.preset_index)

            # Separate global and local zones
            global_zones = [z for z in zones if z.is_global]
            local_zones = [z for z in zones if not z.is_global]

            # Apply global zone inheritance
            if global_zones:
                # SF2 spec: only one global zone per preset
                global_zone = global_zones[0]
                for zone in local_zones:
                    self._apply_zone_inheritance(zone, global_zone)

            # Set zones on preset
            preset.zones = zones

            return preset

        except Exception as e:
            logger.error(f"Error processing preset {preset_header.name}: {e}")
            return None

    def _process_single_instrument(self, instrument_header: InstrumentHeader) -> Optional[SF2Instrument]:
        """
        Process a single instrument with complete zone processing.

        Args:
            instrument_header: Instrument header data

        Returns:
            Fully processed SF2Instrument, or None on error
        """
        try:
            # Create instrument object
            instrument = SF2Instrument(
                name=instrument_header.name,
                zones=[]
            )

            # Get zones for this instrument using instrument_index (O(1) lookup!)
            zones = self._create_instrument_zones_by_index(instrument_header.instrument_index)

            # Separate global and local zones
            global_zones = [z for z in zones if z.is_global]
            local_zones = [z for z in zones if not z.is_global]

            # Apply global zone inheritance
            if global_zones:
                # SF2 spec: only one global zone per instrument
                global_zone = global_zones[0]
                for zone in local_zones:
                    self._apply_zone_inheritance(zone, global_zone)

            # Set zones on instrument
            instrument.zones = zones

            return instrument

        except Exception as e:
            logger.error(f"Error processing instrument {instrument_header.name}: {e}")
            return None



    def _create_preset_zones_by_index(self, preset_index: int) -> List[SF2Zone]:
        """
        Create zones for a preset using direct preset index access (O(1)).

        Parses only the bag range needed for this preset on-demand.

        Args:
            preset_index: Sequential preset index (0, 1, 2, ...)

        Returns:
            List of SF2Zone objects for this preset
        """
        zones = []
        preset_headers = self._get_preset_headers()

        if preset_index >= len(preset_headers):
            return zones

        # Compute bag range directly from preset index
        start_bag_index = preset_headers[preset_index].preset_bag_index

        # Find end bag (next preset's start or end of data)
        end_bag_index = self.data_parser.get_preset_bag_count()  # Get total count without parsing all
        if preset_index + 1 < len(preset_headers):
            end_bag_index = preset_headers[preset_index + 1].preset_bag_index

        # Parse only the bag range needed for this preset
        bags = self.data_parser.parse_preset_bags_range(start_bag_index, end_bag_index)

        # Process each zone in the preset
        for i, bag in enumerate(bags):
            # Calculate exact ranges using consecutive bag indices
            gen_start = bag.gen_ndx
            gen_end = bags[i + 1].gen_ndx if i + 1 < len(bags) else self.data_parser.get_preset_generator_count()

            mod_start = bag.mod_ndx
            mod_end = bags[i + 1].mod_ndx if i + 1 < len(bags) else self.data_parser.get_preset_modulator_count()

            zone = self._create_single_preset_zone(gen_start, gen_end, mod_start, mod_end)

            if zone:
                # Update zone ranges from generators
                zone.update_ranges_from_generators()
                zones.append(zone)

        return zones

    def _create_instrument_zones_by_index(self, instrument_index: int) -> List[SF2Zone]:
        """
        Create zones for an instrument using direct instrument index access (O(1)).

        Parses only the instrument header and bag range needed on-demand.

        Args:
            instrument_index: Sequential instrument index (0, 1, 2, ...)

        Returns:
            List of SF2Zone objects for this instrument
        """
        zones = []

        # Parse only the specific instrument header we need (on-demand!)
        try:
            instrument_header = self._get_instrument_header(instrument_index)
        except Exception:
            # Instrument index out of range
            return zones

        # Compute bag range directly from instrument header
        start_bag_index = instrument_header.instrument_bag_index

        # Find end bag (next instrument's start or end of data)
        # We need to check if there's a next instrument to get its bag index
        total_instruments = self.data_parser.get_instrument_count()
        end_bag_index = self.data_parser.get_instrument_bag_count()  # Default to end

        if instrument_index + 1 < total_instruments:
            try:
                next_header = self._get_instrument_header(instrument_index + 1)
                end_bag_index = next_header.instrument_bag_index
            except Exception:
                # If we can't get next header, use total count
                pass

        # Parse only the bag range needed for this instrument
        bags = self.data_parser.parse_instrument_bags_range(start_bag_index, end_bag_index)

        # Process each zone in the instrument
        for i, bag in enumerate(bags):
            # Calculate exact ranges using consecutive bag indices
            gen_start = bag.gen_ndx
            gen_end = bags[i + 1].gen_ndx if i + 1 < len(bags) else self.data_parser.get_instrument_generator_count()

            mod_start = bag.mod_ndx
            mod_end = bags[i + 1].mod_ndx if i + 1 < len(bags) else self.data_parser.get_instrument_modulator_count()

            zone = self._create_single_instrument_zone(gen_start, gen_end, mod_start, mod_end)

            if zone:
                # Update zone ranges from generators
                zone.update_ranges_from_generators()
                zones.append(zone)

        return zones

    def _create_single_preset_zone(self, gen_start: int, gen_end: int, mod_start: int, mod_end: int) -> Optional[SF2Zone]:
        """
        Create a single preset zone from generator and modulator index ranges.

        Args:
            gen_start: Starting generator index
            gen_end: Ending generator index (exclusive)
            mod_start: Starting modulator index
            mod_end: Ending modulator index (exclusive)

        Returns:
            SF2Zone object, or None on error
        """
        try:
            # Create zone
            zone = SF2Zone(zone_type='preset')

            # Get generators and modulators for this zone using exact ranges
            generators = self._get_zone_generators_range(gen_start, gen_end, is_preset=True)
            modulators = self._get_zone_modulators_range(mod_start, mod_end, is_preset=True)

            # Set generators and modulators
            zone.generators = {gen.generator_type: gen for gen in generators}
            zone.modulators = modulators

            # Determine if this is a global zone
            zone.is_global = self._is_global_preset_zone(zone)

            # For preset zones, check if instrument is specified
            if GeneratorType.instrument in zone.generators:
                zone.instrument_index = zone.generators[GeneratorType.instrument].amount

            return zone

        except Exception as e:
            logger.warning(f"Error creating preset zone: {e}")
            return None

    def _create_single_instrument_zone(self, gen_start: int, gen_end: int, mod_start: int, mod_end: int) -> Optional[SF2Zone]:
        """
        Create a single instrument zone from generator and modulator index ranges.

        Args:
            gen_start: Starting generator index
            gen_end: Ending generator index (exclusive)
            mod_start: Starting modulator index
            mod_end: Ending modulator index (exclusive)

        Returns:
            SF2Zone object, or None on error
        """
        try:
            # Create zone
            zone = SF2Zone(zone_type='instrument')

            # Get generators and modulators for this zone using exact ranges
            generators = self._get_zone_generators_range(gen_start, gen_end, is_preset=False)
            modulators = self._get_zone_modulators_range(mod_start, mod_end, is_preset=False)

            # Set generators and modulators
            zone.generators = {gen.generator_type: gen for gen in generators}
            zone.modulators = modulators

            # Determine if this is a global zone
            zone.is_global = self._is_global_instrument_zone(zone)

            # For instrument zones, check if sample is specified
            if GeneratorType.sampleID in zone.generators:
                zone.sample_index = zone.generators[GeneratorType.sampleID].amount

            return zone

        except Exception as e:
            logger.warning(f"Error creating instrument zone: {e}")
            return None



    def _get_zone_generators_range(self, start_index: int, end_index: int, is_preset: bool) -> List[SF2Generator]:
        """
        Get generators for a zone using exact index range.

        Args:
            start_index: Starting generator index (inclusive)
            end_index: Ending generator index (exclusive)
            is_preset: True for preset generators, False for instrument generators

        Returns:
            List of generators for this zone
        """
        if is_preset:
            return self.data_parser.parse_preset_generators_range(start_index, end_index)
        else:
            return self.data_parser.parse_instrument_generators_range(start_index, end_index)

    def _get_zone_modulators_range(self, start_index: int, end_index: int, is_preset: bool) -> List[SF2Modulator]:
        """
        Get modulators for a zone using exact index range.

        Args:
            start_index: Starting modulator index (inclusive)
            end_index: Ending modulator index (exclusive)
            is_preset: True for preset modulators, False for instrument modulators

        Returns:
            List of modulators for this zone
        """
        if is_preset:
            return self.data_parser.parse_preset_modulators_range(start_index, end_index)
        else:
            return self.data_parser.parse_instrument_modulators_range(start_index, end_index)





    def _is_global_preset_zone(self, zone: SF2Zone) -> bool:
        """
        Determine if a preset zone is global.

        SF2 spec: A preset zone is global if it has no instrument assigned.
        """
        return GeneratorType.instrument not in zone.generators

    def _is_global_instrument_zone(self, zone: SF2Zone) -> bool:
        """
        Determine if an instrument zone is global.

        SF2 spec: An instrument zone is global if it has no sample assigned.
        """
        return GeneratorType.sampleID not in zone.generators

    def _apply_zone_inheritance(self, local_zone: SF2Zone, global_zone: SF2Zone):
        """
        Apply global zone inheritance to a local zone.

        SF2 spec section 7.7: Global zone generators/modulators are inherited
        by local zones that don't override them.
        """
        # Inherit generators not present in local zone
        for gen_type, global_gen in global_zone.generators.items():
            if gen_type not in local_zone.generators:
                local_zone.generators[gen_type] = global_gen

        # Inherit modulators (add to existing modulators)
        local_zone.modulators.extend(global_zone.modulators)

    def _find_preset_end_bag(self, start_bag: int) -> int:
        """
        Find the end bag index for a preset.

        SF2 specification requires bag indices are sorted, so we can use
        binary search for O(log n) lookup instead of linear search.
        """
        preset_headers = self._get_preset_headers()

        # Binary search for the next preset's start bag
        left, right = 0, len(preset_headers) - 1
        next_start_bag = self.data_parser.get_preset_bag_count()  # Default to end

        while left <= right:
            mid = (left + right) // 2
            if preset_headers[mid].preset_bag_index > start_bag:
                next_start_bag = preset_headers[mid].preset_bag_index
                right = mid - 1
            else:
                left = mid + 1

        return next_start_bag

    def _find_instrument_end_bag(self, start_bag: int) -> int:
        """
        Find the end bag index for an instrument.

        SF2 specification requires bag indices are sorted, so we can use
        binary search for O(log n) lookup instead of linear search.
        """
        instrument_headers = self._get_instrument_headers()

        # Binary search for the next instrument's start bag
        left, right = 0, len(instrument_headers) - 1
        next_start_bag = self.data_parser.get_instrument_bag_count()  # Default to end

        while left <= right:
            mid = (left + right) // 2
            if instrument_headers[mid].instrument_bag_index > start_bag:
                next_start_bag = instrument_headers[mid].instrument_bag_index
                right = mid - 1
            else:
                left = mid + 1

        return next_start_bag

    # ===== DATA ACCESSOR METHODS =====

    def _get_preset_headers(self) -> List[PresetHeader]:
        """Get preset headers with caching."""
        if self._preset_headers is None:
            self._preset_headers = self.data_parser.parse_preset_headers()
        return self._preset_headers

    def _get_instrument_headers(self) -> List[InstrumentHeader]:
        """Get instrument headers - parses all for methods that need full list."""
        if self._instrument_headers is None:
            self._instrument_headers = self.data_parser.parse_instrument_headers()
        return self._instrument_headers

    def _get_instrument_header(self, instrument_index: int) -> InstrumentHeader:
        """Get a single instrument header on-demand."""
        return self.data_parser.parse_instrument_header(instrument_index)

    def _get_sample_headers(self) -> List[SampleHeader]:
        """Get sample headers - parses all for methods that need full list."""
        if self._sample_headers is None:
            self._sample_headers = self.data_parser.parse_sample_headers()
        return self._sample_headers

    def _get_sample_header(self, sample_index: int) -> SampleHeader:
        """Get a single sample header on-demand."""
        return self.data_parser.parse_sample_header(sample_index)





    def validate_zone_processing(self) -> Dict[str, Any]:
        """
        Validate zone processing results.

        Returns:
            Dictionary with validation results and statistics
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }

        try:
            # Process all presets and instruments
            presets = self.process_all_presets()
            instruments = self.process_all_instruments()

            # Basic validation
            if len(presets) == 0:
                validation_results['errors'].append("No presets could be processed")
                validation_results['valid'] = False

            if len(instruments) == 0:
                validation_results['errors'].append("No instruments could be processed")
                validation_results['valid'] = False

            # Check for zones referencing invalid instruments/samples
            max_instrument_index = len(instruments) - 1
            max_sample_index = len(self._get_sample_headers()) - 1

            for preset in presets:
                for zone in preset.zones:
                    if zone.instrument_index is not None:
                        if not (0 <= zone.instrument_index <= max_instrument_index):
                            validation_results['errors'].append(
                                f"Preset {preset.name} zone references invalid instrument index {zone.instrument_index}"
                            )
                            validation_results['valid'] = False

            for instrument in instruments:
                for zone in instrument.zones:
                    if zone.sample_index is not None:
                        if not (0 <= zone.sample_index <= max_sample_index):
                            validation_results['errors'].append(
                                f"Instrument {instrument.name} zone references invalid sample index {zone.sample_index}"
                            )
                            validation_results['valid'] = False

            # Collect statistics
            validation_results['statistics'] = {
                'presets_processed': len(presets),
                'instruments_processed': len(instruments),
                'total_preset_zones': sum(len(p.zones) for p in presets),
                'total_instrument_zones': sum(len(i.zones) for i in instruments),
                'global_preset_zones': sum(len([z for z in p.zones if z.is_global]) for p in presets),
                'global_instrument_zones': sum(len([z for z in i.zones if z.is_global]) for i in instruments)
            }

        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Zone processing validation failed: {e}")

        return validation_results


def create_sf2_zone_processor(data_parser: SF2DataParser) -> SF2ZoneProcessor:
    """
    Convenience function to create an SF2ZoneProcessor.

    Args:
        data_parser: Configured SF2DataParser

    Returns:
        SF2ZoneProcessor instance
    """
    return SF2ZoneProcessor(data_parser)
