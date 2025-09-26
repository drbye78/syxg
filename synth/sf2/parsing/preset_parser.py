"""
SF2 Preset Parser

Handles parsing of SF2 preset data including headers, generators, and modulators.
"""

import struct
import numpy as np
from typing import List, Tuple, Optional, BinaryIO, Dict, Any
from ..types import SF2Preset, SF2PresetZone, SF2Modulator


class PresetParser:
    """
    Parser for SF2 preset data structures.
    """

    def __init__(self, file: BinaryIO, chunk_info: Dict[str, Tuple[int, int]]):
        """
        Initialize preset parser.

        Args:
            file: Open binary file handle
            chunk_info: Dictionary of chunk positions and sizes
        """
        self.file = file
        self.chunk_info = chunk_info

    def parse_preset_headers(self) -> List[SF2Preset]:
        """
        Parse preset headers (phdr chunk).

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

        for i in range(num_presets - 1):  # Exclude terminal preset
            # Read preset header data
            header_data = self.file.read(38)
            if len(header_data) < 38:
                break

            # Parse preset header
            name = header_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
            preset_num = struct.unpack('<H', header_data[20:22])[0]
            bank = struct.unpack('<H', header_data[22:24])[0]
            preset_bag_ndx = struct.unpack('<H', header_data[24:26])[0]

            # Create preset object
            preset = SF2Preset()
            preset.name = name
            preset.preset = preset_num
            preset.bank = bank
            preset.preset_bag_index = preset_bag_ndx

            presets.append(preset)

        return presets

    def parse_preset_zones(self, presets: List[SF2Preset]) -> List[SF2Preset]:
        """
        Parse preset zones and associate them with presets.

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

        # Associate zones with presets
        for i, preset in enumerate(presets):
            start_bag = preset.preset_bag_index
            end_bag = presets[i + 1].preset_bag_index if i < len(presets) - 1 else len(bag_data)

            # Create zones for this preset
            for bag_idx in range(start_bag, end_bag):
                if bag_idx >= len(bag_data):
                    break

                gen_ndx, mod_ndx = bag_data[bag_idx]

                # Create preset zone
                zone = SF2PresetZone()
                zone.preset = preset.preset
                zone.bank = preset.bank
                zone.gen_ndx = gen_ndx
                zone.mod_ndx = mod_ndx

                # Parse generators for this zone
                self._parse_zone_generators(zone, gen_data, gen_ndx)

                # Parse modulators for this zone
                self._parse_zone_modulators(zone, mod_data, mod_ndx)

                preset.zones.append(zone)

        return presets

    def _parse_bag_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse bag data (pbag/ibag chunks).

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

        for _ in range(num_entries):
            entry_data = self.file.read(4)
            if len(entry_data) < 4:
                break

            gen_ndx = struct.unpack('<H', entry_data[:2])[0]
            mod_ndx = struct.unpack('<H', entry_data[2:4])[0]

            bag_data.append((gen_ndx, mod_ndx))

        return bag_data

    def _parse_generator_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse generator data (pgen/igen chunks).

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

        for _ in range(num_entries):
            entry_data = self.file.read(4)
            if len(entry_data) < 4:
                break

            gen_type = struct.unpack('<H', entry_data[:2])[0]
            gen_amount = struct.unpack('<h', entry_data[2:4])[0]  # Signed short

            gen_data.append((gen_type, gen_amount))

        return gen_data

    def _parse_modulator_data(self, chunk_name: str) -> List[SF2Modulator]:
        """
        Parse modulator data (pmod/imod chunks).

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

        for _ in range(num_entries):
            entry_data = self.file.read(10)
            if len(entry_data) < 10:
                break

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

            mod_data.append(modulator)

        return mod_data

    def _parse_zone_generators(self, zone: SF2PresetZone, gen_data: List[Tuple[int, int]], start_idx: int):
        """
        Parse generators for a specific zone.

        Args:
            zone: The preset zone to populate
            gen_data: List of generator data
            start_idx: Starting index in generator data
        """
        # Find the end of this zone's generators (next zone's start or end of data)
        end_idx = start_idx + 1
        for i in range(start_idx + 1, len(gen_data)):
            if gen_data[i][0] == 0:  # Terminal generator
                end_idx = i
                break

        # Process generators for this zone
        for i in range(start_idx, end_idx):
            if i >= len(gen_data):
                break

            gen_type, gen_amount = gen_data[i]
            zone.generators[gen_type] = gen_amount

            # Handle specific generator types
            if gen_type == 41:  # instrument
                zone.instrument_index = gen_amount
            elif gen_type == 43:  # keyRange
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 44:  # velRange
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF

    def _parse_zone_modulators(self, zone: SF2PresetZone, mod_data: List[SF2Modulator], start_idx: int):
        """
        Parse modulators for a specific zone.

        Args:
            zone: The preset zone to populate
            mod_data: List of modulator data
            start_idx: Starting index in modulator data
        """
        # Find the end of this zone's modulators
        end_idx = start_idx + 1
        for i in range(start_idx + 1, len(mod_data)):
            if (mod_data[i].source_oper == 0 and
                mod_data[i].destination == 0 and
                mod_data[i].amount == 0):
                end_idx = i
                break

        # Add modulators to zone
        for i in range(start_idx, end_idx):
            if i < len(mod_data):
                zone.modulators.append(mod_data[i])
