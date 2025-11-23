"""
SF2 Preset Parser

Handles parsing of SF2 preset data including headers, generators, and modulators.
"""

import struct
import numpy as np
from typing import List, Tuple, Optional, BinaryIO, Dict, Any
from ..types import SF2Preset, SF2PresetZone, SF2Modulator
from .zone_parser_mixin import ZoneParserMixin


class PresetParser(ZoneParserMixin):
    """
    Parser for SF2 preset data structures with selective parsing optimization.
    """

    def __init__(self, file: BinaryIO, chunk_info: Dict[str, Tuple[int, int]], max_block_size: int = 10 * 1024 * 1024):
        """
        Initialize preset parser.

        Args:
            file: Open binary file handle
            chunk_info: Dictionary of chunk positions and sizes
            max_block_size: Maximum block size for reading chunks (bytes)
        """
        self.file = file
        self.chunk_info = chunk_info
        self.max_block_size = max_block_size

        # Lazy loading caches for selective parsing
        self._bag_data_cache: Optional[List[Tuple[int, int]]] = None
        self._gen_data_cache: Optional[List[Tuple[int, int]]] = None
        self._mod_data_cache: Optional[List[SF2Modulator]] = None

        # Preset zone cache for selective parsing
        self._preset_zone_cache: Dict[int, List[SF2PresetZone]] = {}

    def parse_preset_headers(self) -> List[SF2Preset]:
        """
        Parse preset headers (phdr chunk) using block reading for performance.

        Returns:
            List of SF2Preset objects
        """
        presets = []

        if 'phdr' not in self.chunk_info:
            return presets

        pos, size = self.chunk_info['phdr']
        self.file.seek(pos)

        # Each preset header is 38 bytes
        num_presets = size // 38

        # Read entire chunk at once for better performance
        chunk_data = self.file.read(min(size, self.max_block_size))
        if len(chunk_data) < size:
            # Fallback to individual reads if chunk is too large
            self.file.seek(pos)
            for i in range(num_presets - 1):  # Exclude terminal preset
                header_data = self.file.read(38)
                if len(header_data) < 38:
                    break
                preset = self._parse_single_preset_header(header_data)
                presets.append(preset)
        else:
            # Block parse all headers
            for i in range(num_presets - 1):  # Exclude terminal preset
                offset = i * 38
                if offset + 38 > len(chunk_data):
                    break
                header_data = chunk_data[offset:offset + 38]
                preset = self._parse_single_preset_header(header_data)
                presets.append(preset)

        return presets

    def _parse_single_preset_header(self, header_data: bytes) -> SF2Preset:
        """
        Parse a single preset header from raw bytes.

        Args:
            header_data: 38 bytes of header data

        Returns:
            SF2Preset object
        """
        name = header_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
        preset_num = struct.unpack('<H', header_data[20:22])[0]
        bank = struct.unpack('<H', header_data[22:24])[0]
        preset_bag_ndx = struct.unpack('<H', header_data[24:26])[0]

        preset = SF2Preset()
        preset.name = name
        preset.preset = preset_num
        preset.bank = bank
        preset.preset_bag_index = preset_bag_ndx

        return preset

    def parse_preset_zones(self, presets: List[SF2Preset]) -> List[SF2Preset]:
        """
        Parse preset zones and associate them with presets with batch processing.

        Args:
            presets: List of SF2Preset objects

        Returns:
            Updated list of presets with zones
        """
        if 'pbag' not in self.chunk_info or 'pgen' not in self.chunk_info or 'pmod' not in self.chunk_info:
            return presets

        # Parse bag data
        bag_data = self._parse_bag_data('pbag')

        # Parse generator data
        gen_data = self._parse_generator_data('pgen')

        # Parse modulator data
        mod_data = self._parse_modulator_data('pmod')

        # Associate zones with presets using batch processing
        for i, preset in enumerate(presets):
            start_bag = preset.preset_bag_index
            end_bag = presets[i + 1].preset_bag_index if i < len(presets) - 1 else len(bag_data)

            # Get the next preset's start indices for proper zone boundary calculation
            next_gen_start = bag_data[presets[i + 1].preset_bag_index][0] if i < len(presets) - 1 else len(gen_data)
            next_mod_start = bag_data[presets[i + 1].preset_bag_index][1] if i < len(presets) - 1 else len(mod_data)

            # Create zones for this preset
            zones_data = []
            for bag_idx in range(start_bag, end_bag):
                if bag_idx >= len(bag_data):
                    break

                gen_ndx, mod_ndx = bag_data[bag_idx]
                zones_data.append((bag_idx, gen_ndx, mod_ndx))

            # Batch parse zones for this preset
            preset.zones = self._batch_parse_preset_zones(zones_data, gen_data, mod_data, next_gen_start, next_mod_start, preset.preset, preset.bank)

        return presets

    def parse_single_preset_zones(self, preset_index: int, presets: List[SF2Preset]) -> List[SF2PresetZone]:
        """
        Parse zones for a single preset only, implementing lazy loading optimization.

        Args:
            preset_index: Index of the preset to parse
            presets: List of all SF2Preset objects (for bag index calculation)

        Returns:
            List of parsed preset zones for the specified preset
        """
        if preset_index >= len(presets):
            return []

        # Check cache first
        if preset_index in self._preset_zone_cache:
            return self._preset_zone_cache[preset_index]

        if 'pbag' not in self.chunk_info or 'pgen' not in self.chunk_info or 'pmod' not in self.chunk_info:
            return []

        # Lazy load bag data if not cached
        if self._bag_data_cache is None:
            self._bag_data_cache = self._parse_bag_data('pbag')

        # Lazy load generator data if not cached
        if self._gen_data_cache is None:
            self._gen_data_cache = self._parse_generator_data('pgen')

        # Lazy load modulator data if not cached
        if self._mod_data_cache is None:
            self._mod_data_cache = self._parse_modulator_data('pmod')

        bag_data = self._bag_data_cache
        gen_data = self._gen_data_cache
        mod_data = self._mod_data_cache

        preset = presets[preset_index]
        start_bag = preset.preset_bag_index
        end_bag = presets[preset_index + 1].preset_bag_index if preset_index < len(presets) - 1 else len(bag_data)

        # Get the next preset's start indices for proper zone boundary calculation
        next_gen_start = bag_data[presets[preset_index + 1].preset_bag_index][0] if preset_index < len(presets) - 1 else len(gen_data)
        next_mod_start = bag_data[presets[preset_index + 1].preset_bag_index][1] if preset_index < len(presets) - 1 else len(mod_data)

        # Create zones data for this preset only
        zones_data = []
        for bag_idx in range(start_bag, end_bag):
            if bag_idx >= len(bag_data):
                break
            gen_ndx, mod_ndx = bag_data[bag_idx]
            zones_data.append((bag_idx, gen_ndx, mod_ndx))

        # Parse zones for this preset
        zones = self._batch_parse_preset_zones(zones_data, gen_data, mod_data, next_gen_start, next_mod_start, preset.preset, preset.bank)

        # Cache the result
        self._preset_zone_cache[preset_index] = zones

        return zones

    def _batch_parse_preset_zones(self, zones_data: List[Tuple[int, int, int]],
                                gen_data: List[Tuple[int, int]], mod_data: List[SF2Modulator],
                                max_gen_ndx: int, max_mod_ndx: int,
                                preset_num: int, bank: int) -> List[SF2PresetZone]:
        """
        Batch parse multiple preset zones for better performance.

        Args:
            zones_data: List of (bag_idx, gen_ndx, mod_ndx) tuples
            gen_data: Generator data
            mod_data: Modulator data
            max_gen_ndx: Maximum generator index this preset can use
            max_mod_ndx: Maximum modulator index this preset can use
            preset_num: Preset number
            bank: Bank number

        Returns:
            List of parsed preset zones
        """
        zones = []

        for i, (bag_idx, gen_ndx, mod_ndx) in enumerate(zones_data):
            # Calculate end indices for this zone
            next_gen_ndx = zones_data[i + 1][1] if i + 1 < len(zones_data) else max_gen_ndx
            next_mod_ndx = zones_data[i + 1][2] if i + 1 < len(zones_data) else max_mod_ndx

            # Create preset zone
            zone = SF2PresetZone()
            zone.preset = preset_num
            zone.bank = bank
            zone.gen_ndx = gen_ndx
            zone.mod_ndx = mod_ndx

            # Parse generators for this zone
            self._parse_zone_generators(zone, gen_data, gen_ndx, next_gen_ndx)

            # Parse modulators for this zone
            self._parse_zone_modulators(zone, mod_data, mod_ndx, next_mod_ndx)

            zones.append(zone)

        return zones

    def clear_preset_zone_cache(self):
        """
        Clear the preset zone cache to free memory.
        """
        self._preset_zone_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about the lazy loading cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_preset_zones': len(self._preset_zone_cache),
            'bag_data_loaded': self._bag_data_cache is not None,
            'gen_data_loaded': self._gen_data_cache is not None,
            'mod_data_loaded': self._mod_data_cache is not None
        }

    def _parse_bag_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse bag data (pbag/ibag chunks) using block reading for performance.

        Args:
            chunk_name: Name of the bag chunk

        Returns:
            List of (gen_ndx, mod_ndx) tuples
        """
        bag_data = []

        if chunk_name not in self.chunk_info:
            return bag_data

        pos, size = self.chunk_info[chunk_name]
        self.file.seek(pos)

        # Each bag entry is 4 bytes
        num_entries = size // 4

        # Read entire chunk at once for better performance
        chunk_data = self.file.read(min(size, self.max_block_size))
        if len(chunk_data) < size:
            # Fallback to individual reads if chunk is too large
            self.file.seek(pos)
            for _ in range(num_entries):
                entry_data = self.file.read(4)
                if len(entry_data) < 4:
                    break
                gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
                bag_data.append((gen_ndx, mod_ndx))
        else:
            # Block unpack all bag entries using struct.unpack_from
            for i in range(num_entries):
                offset = i * 4
                if offset + 4 > len(chunk_data):
                    break
                gen_ndx, mod_ndx = struct.unpack_from('<HH', chunk_data, offset)
                bag_data.append((gen_ndx, mod_ndx))

        return bag_data

    def _parse_generator_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse generator data (pgen/igen chunks) using block reading for performance.

        Args:
            chunk_name: Name of the generator chunk

        Returns:
            List of (gen_type, gen_amount) tuples
        """
        gen_data = []

        if chunk_name not in self.chunk_info:
            return gen_data

        pos, size = self.chunk_info[chunk_name]
        self.file.seek(pos)

        # Each generator entry is 4 bytes
        num_entries = size // 4

        # Read entire chunk at once for better performance
        chunk_data = self.file.read(min(size, self.max_block_size))
        if len(chunk_data) < size:
            # Fallback to individual reads if chunk is too large
            self.file.seek(pos)
            for _ in range(num_entries):
                entry_data = self.file.read(4)
                if len(entry_data) < 4:
                    break
                gen_type, gen_amount = struct.unpack('<Hh', entry_data)
                gen_data.append((gen_type, gen_amount))
        else:
            # Block unpack all generator entries using struct.unpack_from
            for i in range(num_entries):
                offset = i * 4
                if offset + 4 > len(chunk_data):
                    break
                gen_type, gen_amount = struct.unpack_from('<Hh', chunk_data, offset)
                gen_data.append((gen_type, gen_amount))

        return gen_data

    def _parse_modulator_data(self, chunk_name: str) -> List[SF2Modulator]:
        """
        Parse modulator data (pmod/imod chunks) using block reading for performance.

        Args:
            chunk_name: Name of the modulator chunk

        Returns:
            List of SF2Modulator objects
        """
        mod_data = []

        if chunk_name not in self.chunk_info:
            return mod_data

        pos, size = self.chunk_info[chunk_name]
        self.file.seek(pos)

        # Each modulator entry is 10 bytes
        num_entries = size // 10

        # Read entire chunk at once for better performance
        chunk_data = self.file.read(min(size, self.max_block_size))
        if len(chunk_data) < size:
            # Fallback to individual reads if chunk is too large
            self.file.seek(pos)
            for _ in range(num_entries):
                entry_data = self.file.read(10)
                if len(entry_data) < 10:
                    break
                modulator = self._parse_single_modulator(entry_data)
                mod_data.append(modulator)
        else:
            # Block parse all modulators
            for i in range(num_entries):
                offset = i * 10
                if offset + 10 > len(chunk_data):
                    break
                entry_data = chunk_data[offset:offset + 10]
                modulator = self._parse_single_modulator(entry_data)
                mod_data.append(modulator)

        return mod_data

    def _parse_single_modulator(self, entry_data: bytes) -> SF2Modulator:
        """
        Parse a single modulator from raw bytes.

        Args:
            entry_data: 10 bytes of modulator data

        Returns:
            SF2Modulator object
        """
        modulator = SF2Modulator()

        # Parse source operator
        source = struct.unpack('<H', entry_data[0:2])[0]
        modulator.source_oper = source & 0x00FF
        modulator.source_polarity = (source & 0x0100) >> 8
        modulator.source_direction = (source & 0x0200) >> 9
        modulator.source_type = (source & 0x0400) >> 10
        modulator.source_index = (source & 0xFF00) >> 8

        # Parse destination
        modulator.destination = struct.unpack('<H', entry_data[4:6])[0]

        # Parse amount
        modulator.amount = struct.unpack('<h', entry_data[6:8])[0]

        return modulator



    def _get_instrument_gen_type(self) -> int:
        """
        Return the generator type for linking to instruments (preset zones point to instruments).

        Returns:
            Generator type (41)
        """
        return 41

    def _set_zone_link_index(self, zone, gen_amount: int, sample_headers=None):
        """
        Set the instrument index on the preset zone.

        Args:
            zone: Preset zone to modify
            gen_amount: Generator amount (the instrument index)
            sample_headers: Optional list of sample headers (unused for preset zones)
        """
        zone.instrument_index = gen_amount

    # Refactored methods using the mixin
    def _parse_zone_generators(self, zone: SF2PresetZone, gen_data: List[Tuple[int, int]], start_idx: int, end_idx: int):
        """
        Parse generators for a specific zone using the improved mixin method.

        Args:
            zone: The preset zone to populate
            gen_data: List of generator data
            start_idx: Starting index in generator data
            end_idx: Ending index (next zone's start or len(gen_data))
        """
        self.parse_zone_generators(zone, gen_data, start_idx, end_idx)

    def _parse_zone_modulators(self, zone: SF2PresetZone, mod_data: List[SF2Modulator], start_idx: int, end_idx: int):
        """
        Parse modulators for a specific zone using the improved mixin method.

        Args:
            zone: The preset zone to populate
            mod_data: List of modulator data
            start_idx: Starting index in modulator data
            end_idx: Ending index (next zone's start or len(mod_data))
        """
        self.parse_zone_modulators(zone, mod_data, start_idx, end_idx)
