"""
SF2 Instrument Parser

Handles parsing of SF2 instrument data including headers, generators, and modulators.
"""

import struct
from typing import List, Tuple, Optional, BinaryIO, Dict
from ..types import SF2Instrument, SF2InstrumentZone, SF2Modulator


class InstrumentParser:
    """
    Parser for SF2 instrument data structures.
    """

    def __init__(self, file: BinaryIO, chunk_info: Dict[str, Tuple[int, int]]):
        """
        Initialize instrument parser.

        Args:
            file: Open binary file handle
            chunk_info: Dictionary of chunk positions and sizes
        """
        self.file = file
        self.chunk_info = chunk_info
        self._bags = None
        self._gens = None
        self._mods = None
        self._all = None
        self._names = None

    def parse_instrument_headers(self) -> Tuple[List[SF2Instrument], List[str]]:
        """
        Parse instrument headers (inst chunk).

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

                for i in range(num_instruments - 1):  # Exclude terminal instrument
                    # Read instrument header data
                    header_data = self.file.read(22)
                    if len(header_data) < 22:
                        break

                    # Parse instrument header
                    name = header_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
                    inst_bag_ndx = struct.unpack('<H', header_data[20:22])[0]

                    # Create instrument object
                    instrument = SF2Instrument()
                    instrument.name = name
                    instrument.instrument_bag_index = inst_bag_ndx

                    instruments.append(instrument)
                    instrument_names.append(name)
            self._all = instruments
            self._names = instrument_names

        return self._all, self._names

    def parse_instrument_zones(self, instrument_index: int) -> SF2Instrument:
        """
        Parse instrument zones and associate them with instruments.

        Args:
            instruments: List of SF2Instrument objects

        Returns:
            Updated list of instruments with zones
        """
        if not self._all:
            self.parse_instrument_headers()

        # Parse bag data
        self._bags = self._parse_bag_data('ibag')

        # Parse generator data
        self._gens = self._parse_generator_data('igen')

        # Parse modulator data
        self._mods = self._parse_modulator_data('imod')

        # Associate zones with instrument
        instrument = self._all[instrument_index] # type: ignore
        start_bag = instrument.instrument_bag_index
        end_bag = self._all[instrument_index + 1].instrument_bag_index if instrument_index < len(self._all) - 1 else len(self._bags) # type: ignore

        # Create zones for this instrument
        for bag_idx in range(start_bag, end_bag):
            if bag_idx >= len(self._bags):
                break

            gen_ndx, mod_ndx = self._bags[bag_idx]

            # Create instrument zone
            zone = SF2InstrumentZone()
            zone.gen_ndx = gen_ndx
            zone.mod_ndx = mod_ndx

            # Parse generators for this zone
            self._parse_zone_generators(zone, self._gens, gen_ndx)

            # Parse modulators for this zone
            self._parse_zone_modulators(zone, self._mods, mod_ndx)

            instrument.zones.append(zone)

        return instrument

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

    def _parse_zone_generators(self, zone: SF2InstrumentZone, gen_data: List[Tuple[int, int]], start_idx: int):
        """
        Parse generators for a specific zone.

        Args:
            zone: The instrument zone to populate
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
            if gen_type == 53:  # sampleID
                zone.sample_index = gen_amount
            elif gen_type == 43:  # keyRange
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 44:  # velRange
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF

    def _parse_zone_modulators(self, zone: SF2InstrumentZone, mod_data: List[SF2Modulator], start_idx: int):
        """
        Parse modulators for a specific zone.

        Args:
            zone: The instrument zone to populate
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
