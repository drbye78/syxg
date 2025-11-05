"""
SF2 Instrument Parser

Handles parsing of SF2 instrument data including headers, generators, and modulators.
"""

import struct
from typing import List, Tuple, Optional, BinaryIO, Dict
from ..types import SF2Instrument, SF2InstrumentZone, SF2Modulator
from .zone_parser_mixin import ZoneParserMixin


class InstrumentParser(ZoneParserMixin):
    """
    Parser for SF2 instrument data structures.
    """

    def __init__(self, file: BinaryIO, chunk_info: Dict[str, Tuple[int, int]], max_block_size: int = 10 * 1024 * 1024):
        """
        Initialize instrument parser.

        Args:
            file: Open binary file handle
            chunk_info: Dictionary of chunk positions and sizes
            max_block_size: Maximum block size for reading chunks (bytes)
        """
        self.file = file
        self.chunk_info = chunk_info
        self.max_block_size = max_block_size
        self._bags = None
        self._gens = None
        self._mods = None
        self._all = None
        self._names = None

    def parse_instrument_headers(self) -> Tuple[List[SF2Instrument], List[str]]:
        """
        Parse instrument headers (inst chunk) using block reading for performance.

        Returns:
            Tuple of (instruments list, instrument names list)
        """
        if self._all is None or self._names is None:
            instruments = []
            instrument_names = []

            if 'inst' in self.chunk_info:
                pos, size = self.chunk_info['inst']
                self.file.seek(pos)

                # Each instrument header is 22 bytes
                num_instruments = size // 22

                # Read entire chunk at once for better performance
                chunk_data = self.file.read(min(size, self.max_block_size))
                if len(chunk_data) < size:
                    # Fallback to individual reads if chunk is too large
                    self.file.seek(pos)
                    for i in range(num_instruments - 1):  # Exclude terminal instrument
                        header_data = self.file.read(22)
                        if len(header_data) < 22:
                            break
                        instrument, name = self._parse_single_instrument_header(header_data)
                        instruments.append(instrument)
                        instrument_names.append(name)
                else:
                    # Block parse all headers
                    for i in range(num_instruments - 1):  # Exclude terminal instrument
                        offset = i * 22
                        if offset + 22 > len(chunk_data):
                            break
                        header_data = chunk_data[offset:offset + 22]
                        instrument, name = self._parse_single_instrument_header(header_data)
                        instruments.append(instrument)
                        instrument_names.append(name)
            self._all = instruments
            self._names = instrument_names

        return self._all, self._names

    def _parse_single_instrument_header(self, header_data: bytes) -> Tuple[SF2Instrument, str]:
        """
        Parse a single instrument header from raw bytes.

        Args:
            header_data: 22 bytes of header data

        Returns:
            Tuple of (SF2Instrument object, instrument name)
        """
        name = header_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
        inst_bag_ndx = struct.unpack('<H', header_data[20:22])[0]

        instrument = SF2Instrument()
        instrument.name = name
        instrument.instrument_bag_index = inst_bag_ndx

        return instrument, name

    def parse_instrument_zones(self, instrument_index: int) -> SF2Instrument:
        """
        Parse instrument zones and associate them with instruments with batch processing.

        Args:
            instrument_index: Index of instrument to parse

        Returns:
            Instrument with zones
        """
        if not self._all:
            self.parse_instrument_headers()

        # Parse bag data if not already parsed
        if self._bags is None:
            self._bags = self._parse_bag_data('ibag')

        # Parse generator data if not already parsed
        if self._gens is None:
            self._gens = self._parse_generator_data('igen')

        # Parse modulator data if not already parsed
        if self._mods is None:
            self._mods = self._parse_modulator_data('imod')

        # Associate zones with instrument
        instrument = self._all[instrument_index] # type: ignore
        start_bag = instrument.instrument_bag_index
        end_bag = self._all[instrument_index + 1].instrument_bag_index if instrument_index < len(self._all) - 1 else len(self._bags) # type: ignore

        # Create zones data for batch processing
        zones_data = []
        for bag_idx in range(start_bag, end_bag):
            if bag_idx >= len(self._bags):
                break

            gen_ndx, mod_ndx = self._bags[bag_idx]
            zones_data.append((bag_idx, gen_ndx, mod_ndx))

        # Batch parse zones for this instrument
        instrument.zones = self._batch_parse_instrument_zones(zones_data, self._gens, self._mods)

        return instrument

    def _batch_parse_instrument_zones(self, zones_data: List[Tuple[int, int, int]],
                                    gen_data: List[Tuple[int, int]], mod_data: List[SF2Modulator]) -> List[SF2InstrumentZone]:
        """
        Batch parse multiple instrument zones for better performance.

        Args:
            zones_data: List of (bag_idx, gen_ndx, mod_ndx) tuples
            gen_data: Generator data
            mod_data: Modulator data

        Returns:
            List of parsed instrument zones
        """
        zones = []

        for i, (bag_idx, gen_ndx, mod_ndx) in enumerate(zones_data):
            # Calculate end indices for this zone
            next_gen_ndx = zones_data[i + 1][1] if i + 1 < len(zones_data) else len(gen_data)
            next_mod_ndx = zones_data[i + 1][2] if i + 1 < len(zones_data) else len(mod_data)

            # Create instrument zone
            zone = SF2InstrumentZone()
            zone.gen_ndx = gen_ndx
            zone.mod_ndx = mod_ndx

            # Parse generators for this zone
            self._parse_zone_generators(zone, gen_data, gen_ndx, next_gen_ndx)

            # Parse modulators for this zone
            self._parse_zone_modulators(zone, mod_data, mod_ndx, next_mod_ndx)

            zones.append(zone)

        return zones

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
        Return the generator type for linking to samples (instrument zones point to samples).

        Returns:
            Generator type (53 for sampleID)
        """
        return 53

    def _set_zone_link_index(self, zone, gen_amount: int):
        """
        Set the sample index on the instrument zone.

        Args:
            zone: Instrument zone to modify
            gen_amount: Generator amount (the sample index)
        """
        zone.sample_index = gen_amount

    # Refactored methods using the mixin
    def _parse_zone_generators(self, zone: SF2InstrumentZone, gen_data: List[Tuple[int, int]], start_idx: int, end_idx: int):
        """
        Parse generators for a specific zone using the improved mixin method.

        Args:
            zone: The instrument zone to populate
            gen_data: List of generator data
            start_idx: Starting index in generator data
            end_idx: Ending index (next zone's start or len(gen_data))
        """
        self.parse_zone_generators(zone, gen_data, start_idx, end_idx)

    def _parse_zone_modulators(self, zone: SF2InstrumentZone, mod_data: List[SF2Modulator], start_idx: int, end_idx: int):
        """
        Parse modulators for a specific zone using the improved mixin method.

        Args:
            zone: The instrument zone to populate
            mod_data: List of modulator data
            start_idx: Starting index in modulator data
            end_idx: Ending index (next zone's start or len(mod_data))
        """
        self.parse_zone_modulators(zone, mod_data, start_idx, end_idx)
