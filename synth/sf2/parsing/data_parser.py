"""
SF2 Data Parser - Type-safe parsing of SoundFont 2.0 data structures.

This module provides comprehensive parsing of all SF2 data structures
from raw chunk data, with full validation and error handling.
"""

import struct
import logging
from typing import List, Dict, Optional, Any, Tuple, BinaryIO
from dataclasses import dataclass
from io import BytesIO

from ..types.dataclasses import SF2Generator, SF2Modulator, SF2Sample
from ..core.constants import SF2Spec, GeneratorType, GENERATOR_DEFAULTS, GENERATOR_NAMES
from .chunk_parser import ChunkInfo

logger = logging.getLogger(__name__)


class DataParseError(Exception):
    """Exception raised when data structure parsing fails."""
    pass


@dataclass
class PresetHeader:
    """SF2 Preset Header structure."""
    name: str
    preset: int
    bank: int
    preset_bag_index: int
    library: int
    genre: int
    morphology: int
    preset_index: int = -1  # Sequential index for O(1) access


@dataclass
class InstrumentHeader:
    """SF2 Instrument Header structure."""
    name: str
    instrument_bag_index: int
    instrument_index: int = -1  # Sequential index for O(1) access


@dataclass
class SampleHeader:
    """SF2 Sample Header structure."""
    name: str
    start: int
    end: int
    start_loop: int
    end_loop: int
    sample_rate: int
    original_pitch: int
    pitch_correction: int
    link: int
    sample_type: int


@dataclass
class BagEntry:
    """SF2 Bag Entry (gen_ndx, mod_ndx)."""
    gen_ndx: int
    mod_ndx: int


class SF2DataParser:
    """
    Type-safe parser for SF2 data structures.

    Parses all SF2 binary structures from chunk data with full validation.
    """

    def __init__(self, chunk_data: Dict[str, bytes], chunk_info: Dict[str, ChunkInfo]):
        """
        Initialize the data parser.

        Args:
            chunk_data: Dictionary mapping chunk IDs to raw data
            chunk_info: Dictionary mapping chunk IDs to ChunkInfo objects
        """
        self.chunk_data = chunk_data
        self.chunk_info = chunk_info

    def parse_preset_headers(self) -> List[PresetHeader]:
        """
        Parse preset headers (phdr chunk).

        Returns:
            List of PresetHeader objects
        """
        if 'phdr' not in self.chunk_data:
            raise DataParseError("Missing phdr chunk")

        data = self.chunk_data['phdr']
        size = self.chunk_info['phdr'].size

        # Each preset header is 38 bytes, last one is terminator
        entry_size = SF2Spec.PRESET_HEADER_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError("Invalid phdr chunk size")

        headers = []
        for i in range(count - 1):  # Skip terminator
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            try:
                header = self._parse_preset_header(entry_data)
                header.preset_index = i  # Assign sequential index for O(1) lookups
                headers.append(header)
            except Exception as e:
                logger.warning(f"Failed to parse preset header {i}: {e}")
                continue

        logger.info(f"Parsed {len(headers)} preset headers")
        return headers

    def parse_instrument_headers(self) -> List[InstrumentHeader]:
        """
        Parse instrument headers (inst chunk).

        Returns:
            List of InstrumentHeader objects
        """
        if 'inst' not in self.chunk_data:
            raise DataParseError("Missing inst chunk")

        data = self.chunk_data['inst']
        size = self.chunk_info['inst'].size

        # Each instrument header is 22 bytes, last one is terminator
        entry_size = SF2Spec.INSTRUMENT_HEADER_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError("Invalid inst chunk size")

        headers = []
        for i in range(count - 1):  # Skip terminator
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            try:
                header = self._parse_instrument_header(entry_data)
                header.instrument_index = i  # Assign sequential index for O(1) lookups
                headers.append(header)
            except Exception as e:
                logger.warning(f"Failed to parse instrument header {i}: {e}")
                continue

        logger.info(f"Parsed {len(headers)} instrument headers")
        return headers

    def parse_sample_headers(self) -> List[SampleHeader]:
        """
        Parse sample headers (shdr chunk).

        Returns:
            List of SampleHeader objects
        """
        if 'shdr' not in self.chunk_data:
            raise DataParseError("Missing shdr chunk")

        data = self.chunk_data['shdr']
        size = self.chunk_info['shdr'].size

        # Each sample header is 46 bytes, last one is terminator
        entry_size = SF2Spec.SAMPLE_HEADER_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError("Invalid shdr chunk size")

        headers = []
        for i in range(count - 1):  # Skip terminator
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            try:
                header = self._parse_sample_header(entry_data)
                headers.append(header)
            except Exception as e:
                logger.warning(f"Failed to parse sample header {i}: {e}")
                continue

        logger.info(f"Parsed {len(headers)} sample headers")
        return headers

    def parse_preset_bags(self) -> List[BagEntry]:
        """
        Parse preset bags (pbag chunk).

        Returns:
            List of BagEntry objects
        """
        return self._parse_bag_chunk('pbag', 'preset bags')

    def parse_instrument_bags(self) -> List[BagEntry]:
        """
        Parse instrument bags (ibag chunk).

        Returns:
            List of BagEntry objects
        """
        return self._parse_bag_chunk('ibag', 'instrument bags')

    def parse_preset_bags_range(self, start_index: int, end_index: int) -> List[BagEntry]:
        """
        Parse a range of preset bags on-demand (pbag chunk).

        Args:
            start_index: Starting bag index to parse
            end_index: Ending bag index (exclusive)

        Returns:
            List of BagEntry objects for the specified range
        """
        return self._parse_bag_chunk_range('pbag', start_index, end_index, 'preset bags')

    def parse_instrument_bags_range(self, start_index: int, end_index: int) -> List[BagEntry]:
        """
        Parse a range of instrument bags on-demand (ibag chunk).

        Args:
            start_index: Starting bag index to parse
            end_index: Ending bag index (exclusive)

        Returns:
            List of BagEntry objects for the specified range
        """
        return self._parse_bag_chunk_range('ibag', start_index, end_index, 'instrument bags')

    def get_preset_bag_count(self) -> int:
        """
        Get the total number of preset bags without parsing.

        Returns:
            Total number of preset bags
        """
        if 'pbag' not in self.chunk_info:
            return 0
        return self.chunk_info['pbag'].size // SF2Spec.BAG_ENTRY_SIZE

    def get_instrument_bag_count(self) -> int:
        """
        Get the total number of instrument bags without parsing.

        Returns:
            Total number of instrument bags
        """
        if 'ibag' not in self.chunk_info:
            return 0
        return self.chunk_info['ibag'].size // SF2Spec.BAG_ENTRY_SIZE

    def parse_preset_generators_range(self, start_index: int, end_index: int) -> List[SF2Generator]:
        """
        Parse a range of preset generators on-demand (pgen chunk).

        Args:
            start_index: Starting generator index to parse
            end_index: Ending generator index (exclusive)

        Returns:
            List of SF2Generator objects for the specified range
        """
        return self._parse_generator_chunk_range('pgen', start_index, end_index, 'preset generators')

    def parse_instrument_generators_range(self, start_index: int, end_index: int) -> List[SF2Generator]:
        """
        Parse a range of instrument generators on-demand (igen chunk).

        Args:
            start_index: Starting generator index to parse
            end_index: Ending generator index (exclusive)

        Returns:
            List of SF2Generator objects for the specified range
        """
        return self._parse_generator_chunk_range('igen', start_index, end_index, 'instrument generators')

    def parse_preset_modulators_range(self, start_index: int, end_index: int) -> List[SF2Modulator]:
        """
        Parse a range of preset modulators on-demand (pmod chunk).

        Args:
            start_index: Starting modulator index to parse
            end_index: Ending modulator index (exclusive)

        Returns:
            List of SF2Modulator objects for the specified range
        """
        return self._parse_modulator_chunk_range('pmod', start_index, end_index, 'preset modulators')

    def parse_instrument_modulators_range(self, start_index: int, end_index: int) -> List[SF2Modulator]:
        """
        Parse a range of instrument modulators on-demand (imod chunk).

        Args:
            start_index: Starting modulator index to parse
            end_index: Ending modulator index (exclusive)

        Returns:
            List of SF2Modulator objects for the specified range
        """
        return self._parse_modulator_chunk_range('imod', start_index, end_index, 'instrument modulators')

    def get_preset_generator_count(self) -> int:
        """
        Get the total number of preset generators without parsing.

        Returns:
            Total number of preset generators
        """
        if 'pgen' not in self.chunk_info:
            return 0
        return self.chunk_info['pgen'].size // SF2Spec.GEN_ENTRY_SIZE

    def get_instrument_generator_count(self) -> int:
        """
        Get the total number of instrument generators without parsing.

        Returns:
            Total number of instrument generators
        """
        if 'igen' not in self.chunk_info:
            return 0
        return self.chunk_info['igen'].size // SF2Spec.GEN_ENTRY_SIZE

    def get_preset_modulator_count(self) -> int:
        """
        Get the total number of preset modulators without parsing.

        Returns:
            Total number of preset modulators
        """
        if 'pmod' not in self.chunk_info:
            return 0
        return self.chunk_info['pmod'].size // SF2Spec.MOD_ENTRY_SIZE

    def get_instrument_modulator_count(self) -> int:
        """
        Get the total number of instrument modulators without parsing.

        Returns:
            Total number of instrument modulators
        """
        if 'imod' not in self.chunk_info:
            return 0
        return self.chunk_info['imod'].size // SF2Spec.MOD_ENTRY_SIZE

    def parse_instrument_header(self, instrument_index: int) -> InstrumentHeader:
        """
        Parse a single instrument header on-demand (inst chunk).

        Args:
            instrument_index: Index of the instrument header to parse

        Returns:
            InstrumentHeader object for the specified index
        """
        if 'inst' not in self.chunk_data:
            raise DataParseError("Missing inst chunk")

        data = self.chunk_data['inst']
        size = self.chunk_info['inst'].size

        # Each instrument header is 22 bytes, last one is terminator
        entry_size = SF2Spec.INSTRUMENT_HEADER_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError("Invalid inst chunk size")

        if instrument_index >= count - 1:  # Skip terminator
            raise DataParseError(f"Instrument index {instrument_index} out of range")

        offset = instrument_index * entry_size
        if offset + entry_size > len(data):
            raise DataParseError(f"Instrument header data out of bounds")

        entry_data = data[offset:offset + entry_size]
        header = self._parse_instrument_header(entry_data)
        header.instrument_index = instrument_index  # Assign sequential index

        return header

    def parse_sample_header(self, sample_index: int) -> SampleHeader:
        """
        Parse a single sample header on-demand (shdr chunk).

        Args:
            sample_index: Index of the sample header to parse

        Returns:
            SampleHeader object for the specified index
        """
        if 'shdr' not in self.chunk_data:
            raise DataParseError("Missing shdr chunk")

        data = self.chunk_data['shdr']
        size = self.chunk_info['shdr'].size

        # Each sample header is 46 bytes, last one is terminator
        entry_size = SF2Spec.SAMPLE_HEADER_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError("Invalid shdr chunk size")

        if sample_index >= count - 1:  # Skip terminator
            raise DataParseError(f"Sample index {sample_index} out of range")

        offset = sample_index * entry_size
        if offset + entry_size > len(data):
            raise DataParseError(f"Sample header data out of bounds")

        entry_data = data[offset:offset + entry_size]
        header = self._parse_sample_header(entry_data)

        return header

    def get_instrument_count(self) -> int:
        """
        Get the total number of instruments without parsing.

        Returns:
            Total number of instruments (excluding terminator)
        """
        if 'inst' not in self.chunk_info:
            return 0
        return self.chunk_info['inst'].size // SF2Spec.INSTRUMENT_HEADER_SIZE - 1

    def get_sample_count(self) -> int:
        """
        Get the total number of samples without parsing.

        Returns:
            Total number of samples (excluding terminator)
        """
        if 'shdr' not in self.chunk_info:
            return 0
        return self.chunk_info['shdr'].size // SF2Spec.SAMPLE_HEADER_SIZE - 1

    def parse_preset_generators(self) -> List[SF2Generator]:
        """
        Parse preset generators (pgen chunk).

        Returns:
            List of SF2Generator objects
        """
        return self._parse_generator_chunk('pgen', 'preset generators')

    def parse_instrument_generators(self) -> List[SF2Generator]:
        """
        Parse instrument generators (igen chunk).

        Returns:
            List of SF2Generator objects
        """
        return self._parse_generator_chunk('igen', 'instrument generators')

    def parse_preset_modulators(self) -> List[SF2Modulator]:
        """
        Parse preset modulators (pmod chunk).

        Returns:
            List of SF2Modulator objects
        """
        return self._parse_modulator_chunk('pmod', 'preset modulators')

    def parse_instrument_modulators(self) -> List[SF2Modulator]:
        """
        Parse instrument modulators (imod chunk).

        Returns:
            List of SF2Modulator objects
        """
        return self._parse_modulator_chunk('imod', 'instrument modulators')

    def parse_sample_data(self) -> Optional[bytes]:
        """
        Parse sample data (smpl chunk).

        Returns:
            Raw sample data bytes, or None if not found
        """
        if 'smpl' not in self.chunk_data:
            logger.warning("Missing smpl chunk")
            return None

        return self.chunk_data['smpl']

    def parse_sample_data_24bit(self) -> Optional[bytes]:
        """
        Parse 24-bit sample data (sm24 chunk).

        Returns:
            Raw 24-bit sample data bytes, or None if not found
        """
        if 'sm24' not in self.chunk_data:
            return None

        return self.chunk_data['sm24']

    def _parse_preset_header(self, data: bytes) -> PresetHeader:
        """Parse a single preset header entry."""
        if len(data) < 38:
            raise DataParseError("Preset header data too short")

        # Unpack binary data (little-endian)
        # Format: 20s H H I I I (name, preset, bank, bag_ndx, library, genre, morphology)
        name_bytes = data[0:20]
        preset, bank, bag_ndx, library, genre, morphology = struct.unpack('<HHHIII', data[20:38])

        # Decode name
        name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

        return PresetHeader(
            name=name,
            preset=preset,
            bank=bank,
            preset_bag_index=bag_ndx,
            library=library,
            genre=genre,
            morphology=morphology
        )

    def _parse_instrument_header(self, data: bytes) -> InstrumentHeader:
        """Parse a single instrument header entry."""
        if len(data) < 22:
            raise DataParseError("Instrument header data too short")

        # Format: 20s H (name, bag_ndx)
        name_bytes = data[0:20]
        bag_ndx = struct.unpack('<H', data[20:22])[0]

        # Decode name
        name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

        return InstrumentHeader(
            name=name,
            instrument_bag_index=bag_ndx
        )

    def _parse_sample_header(self, data: bytes) -> SampleHeader:
        """Parse a single sample header entry."""
        if len(data) < 46:
            raise DataParseError("Sample header data too short")

        # Format: 20s I I I I I h h H H (name, start, end, start_loop, end_loop,
        #                               sample_rate, orig_pitch, pitch_corr, link, type)
        name_bytes = data[0:20]
        start, end, start_loop, end_loop, sample_rate = struct.unpack('<IIIII', data[20:40])
        orig_pitch, pitch_corr, link, sample_type = struct.unpack('<hhHH', data[40:46])

        # Decode name
        name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

        return SampleHeader(
            name=name,
            start=start,
            end=end,
            start_loop=start_loop,
            end_loop=end_loop,
            sample_rate=sample_rate,
            original_pitch=orig_pitch,
            pitch_correction=pitch_corr,
            link=link,
            sample_type=sample_type
        )

    def _parse_bag_chunk(self, chunk_id: str, description: str) -> List[BagEntry]:
        """Parse a bag chunk (pbag or ibag)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each bag entry is 4 bytes (gen_ndx, mod_ndx)
        entry_size = SF2Spec.BAG_ENTRY_SIZE
        count = size // entry_size

        if count < 1:
            raise DataParseError(f"Invalid {chunk_id} chunk size")

        bags = []
        for i in range(count):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
            bags.append(BagEntry(gen_ndx=gen_ndx, mod_ndx=mod_ndx))

        logger.info(f"Parsed {len(bags)} {description}")
        return bags

    def _parse_bag_chunk_range(self, chunk_id: str, start_index: int, end_index: int, description: str) -> List[BagEntry]:
        """Parse a range of bag entries from a chunk (pbag or ibag)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each bag entry is 4 bytes (gen_ndx, mod_ndx)
        entry_size = SF2Spec.BAG_ENTRY_SIZE
        total_count = size // entry_size

        if total_count < 1:
            raise DataParseError(f"Invalid {chunk_id} chunk size")

        # Validate range
        if start_index < 0 or end_index > total_count or start_index >= end_index:
            raise DataParseError(f"Invalid range {start_index}:{end_index} for {chunk_id} chunk")

        bags = []
        for i in range(start_index, end_index):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
            bags.append(BagEntry(gen_ndx=gen_ndx, mod_ndx=mod_ndx))

        logger.debug(f"Parsed {len(bags)} {description} (range {start_index}:{end_index})")
        return bags

    def _parse_generator_chunk_range(self, chunk_id: str, start_index: int, end_index: int, description: str) -> List[SF2Generator]:
        """Parse a range of generator entries from a chunk (pgen or igen)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each generator entry is 4 bytes (type, amount)
        entry_size = SF2Spec.GEN_ENTRY_SIZE
        total_count = size // entry_size

        if total_count < 1:
            raise DataParseError(f"Invalid {chunk_id} chunk size")

        # Validate range
        if start_index < 0 or end_index > total_count or start_index >= end_index:
            raise DataParseError(f"Invalid range {start_index}:{end_index} for {chunk_id} chunk")

        generators = []
        for i in range(start_index, end_index):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            gen_type, amount = struct.unpack('<Hh', entry_data)  # H=unsigned short, h=signed short

            # Create generator with name lookup
            name = self._get_generator_name(gen_type)
            generator = SF2Generator(
                generator_type=gen_type,
                amount=amount,
                name=name
            )
            generators.append(generator)

        logger.debug(f"Parsed {len(generators)} {description} (range {start_index}:{end_index})")
        return generators

    def _parse_modulator_chunk_range(self, chunk_id: str, start_index: int, end_index: int, description: str) -> List[SF2Modulator]:
        """Parse a range of modulator entries from a chunk (pmod or imod)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each modulator entry is 10 bytes
        entry_size = SF2Spec.MOD_ENTRY_SIZE
        total_count = size // entry_size

        if total_count < 1:
            raise DataParseError(f"Invalid {chunk_id} chunk size")

        # Validate range
        if start_index < 0 or end_index > total_count or start_index >= end_index:
            raise DataParseError(f"Invalid range {start_index}:{end_index} for {chunk_id} chunk")

        modulators = []
        for i in range(start_index, end_index):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]

            # Parse complete modulator structure per SF2 spec
            src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper = struct.unpack('<HHHHH', entry_data)

            # Decode source operator components (SF2 spec section 8.2.1)
            source_index = src_oper & 0x007F
            source_type = (src_oper >> 8) & 0x0003
            source_polarity = (src_oper >> 9) & 0x0001
            source_direction = (src_oper >> 10) & 0x0001

            # Decode amount source operator components
            amount_source_index = amt_src_oper & 0x007F
            amount_source_type = (amt_src_oper >> 8) & 0x0003
            amount_source_polarity = (amt_src_oper >> 9) & 0x0001
            amount_source_direction = (amt_src_oper >> 10) & 0x0001

            # Create modulator object
            modulator = SF2Modulator(
                source_operator=src_oper,
                source_polarity=source_polarity,
                source_type=source_type,
                source_direction=source_direction,
                source_index=source_index,
                control_operator=0,  # Secondary control not used in basic SF2
                control_polarity=0,
                control_type=0,
                control_direction=0,
                control_index=0,
                destination=dest_oper,
                amount=mod_amount,
                amount_source_operator=amt_src_oper,
                amount_source_polarity=amount_source_polarity,
                amount_source_type=amount_source_type,
                amount_source_direction=amount_source_direction,
                amount_source_index=amount_source_index,
                transform=mod_trans_oper
            )
            modulators.append(modulator)

        logger.debug(f"Parsed {len(modulators)} {description} (range {start_index}:{end_index})")
        return modulators

    def _parse_generator_chunk(self, chunk_id: str, description: str) -> List[SF2Generator]:
        """Parse a generator chunk (pgen or igen)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each generator entry is 4 bytes (type, amount)
        entry_size = SF2Spec.GEN_ENTRY_SIZE
        count = size // entry_size

        generators = []
        for i in range(count):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]
            gen_type, amount = struct.unpack('<Hh', entry_data)  # H=unsigned short, h=signed short

            # Create generator with name lookup
            name = self._get_generator_name(gen_type)
            generator = SF2Generator(
                generator_type=gen_type,
                amount=amount,
                name=name
            )
            generators.append(generator)

        logger.info(f"Parsed {len(generators)} {description}")
        return generators

    def _parse_modulator_chunk(self, chunk_id: str, description: str) -> List[SF2Modulator]:
        """Parse a modulator chunk (pmod or imod)."""
        if chunk_id not in self.chunk_data:
            raise DataParseError(f"Missing {chunk_id} chunk")

        data = self.chunk_data[chunk_id]
        size = self.chunk_info[chunk_id].size

        # Each modulator entry is 10 bytes
        entry_size = SF2Spec.MOD_ENTRY_SIZE
        count = size // entry_size

        modulators = []
        for i in range(count):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break

            entry_data = data[offset:offset + entry_size]

            # Parse complete modulator structure per SF2 spec
            src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper = struct.unpack('<HHHHH', entry_data)

            # Decode source operator components (SF2 spec section 8.2.1)
            source_index = src_oper & 0x007F
            source_type = (src_oper >> 8) & 0x0003
            source_polarity = (src_oper >> 9) & 0x0001
            source_direction = (src_oper >> 10) & 0x0001

            # Decode amount source operator components
            amount_source_index = amt_src_oper & 0x007F
            amount_source_type = (amt_src_oper >> 8) & 0x0003
            amount_source_polarity = (amt_src_oper >> 9) & 0x0001
            amount_source_direction = (amt_src_oper >> 10) & 0x0001

            # Create modulator object
            modulator = SF2Modulator(
                source_operator=src_oper,
                source_polarity=source_polarity,
                source_type=source_type,
                source_direction=source_direction,
                source_index=source_index,
                control_operator=0,  # Secondary control not used in basic SF2
                control_polarity=0,
                control_type=0,
                control_direction=0,
                control_index=0,
                destination=dest_oper,
                amount=mod_amount,
                amount_source_operator=amt_src_oper,
                amount_source_polarity=amount_source_polarity,
                amount_source_type=amount_source_type,
                amount_source_direction=amount_source_direction,
                amount_source_index=amount_source_index,
                transform=mod_trans_oper
            )
            modulators.append(modulator)

        logger.info(f"Parsed {len(modulators)} {description}")
        return modulators

    def _get_generator_name(self, gen_type: int) -> str:
        """Get human-readable name for a generator type."""
        return GENERATOR_NAMES.get(gen_type, f"Unknown_{gen_type}")

    def validate_data_consistency(self) -> bool:
        """
        Validate consistency between different data structures.

        Returns:
            True if data is consistent, False otherwise
        """
        try:
            # Check that we have all required chunks
            required_chunks = ['phdr', 'pbag', 'pgen', 'inst', 'ibag', 'igen', 'shdr']
            for chunk_id in required_chunks:
                if chunk_id not in self.chunk_data:
                    logger.error(f"Missing required chunk: {chunk_id}")
                    return False

            # Parse headers to get counts
            preset_headers = self.parse_preset_headers()
            instrument_headers = self.parse_instrument_headers()
            sample_headers = self.parse_sample_headers()

            # Parse bags
            preset_bags = self.parse_preset_bags()
            instrument_bags = self.parse_instrument_bags()

            # Basic consistency checks
            if len(preset_headers) == 0:
                logger.error("No preset headers found")
                return False

            if len(instrument_headers) == 0:
                logger.error("No instrument headers found")
                return False

            if len(sample_headers) == 0:
                logger.error("No sample headers found")
                return False

            # Check bag indices are within bounds
            for i, preset in enumerate(preset_headers):
                if preset.preset_bag_index >= len(preset_bags):
                    logger.error(f"Preset {i} bag index {preset.preset_bag_index} out of range")
                    return False

            for i, instrument in enumerate(instrument_headers):
                if instrument.instrument_bag_index >= len(instrument_bags):
                    logger.error(f"Instrument {i} bag index {instrument.instrument_bag_index} out of range")
                    return False

            logger.info("SF2 data consistency validation passed")
            return True

        except Exception as e:
            logger.error(f"Data consistency validation failed: {e}")
            return False

    def get_data_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the parsed data.

        Returns:
            Dictionary with data statistics
        """
        stats = {}

        try:
            # Count various data types
            if 'phdr' in self.chunk_data:
                preset_count = self.chunk_info['phdr'].size // SF2Spec.PRESET_HEADER_SIZE - 1
                stats['presets'] = max(0, preset_count)

            if 'inst' in self.chunk_data:
                instrument_count = self.chunk_info['inst'].size // SF2Spec.INSTRUMENT_HEADER_SIZE - 1
                stats['instruments'] = max(0, instrument_count)

            if 'shdr' in self.chunk_data:
                sample_count = self.chunk_info['shdr'].size // SF2Spec.SAMPLE_HEADER_SIZE - 1
                stats['samples'] = max(0, sample_count)

            if 'pbag' in self.chunk_data:
                bag_count = self.chunk_info['pbag'].size // SF2Spec.BAG_ENTRY_SIZE
                stats['preset_bags'] = bag_count

            if 'ibag' in self.chunk_data:
                bag_count = self.chunk_info['ibag'].size // SF2Spec.BAG_ENTRY_SIZE
                stats['instrument_bags'] = bag_count

            if 'pgen' in self.chunk_data:
                gen_count = self.chunk_info['pgen'].size // SF2Spec.GEN_ENTRY_SIZE
                stats['preset_generators'] = gen_count

            if 'igen' in self.chunk_data:
                gen_count = self.chunk_info['igen'].size // SF2Spec.GEN_ENTRY_SIZE
                stats['instrument_generators'] = gen_count

            if 'pmod' in self.chunk_data:
                mod_count = self.chunk_info['pmod'].size // SF2Spec.MOD_ENTRY_SIZE
                stats['preset_modulators'] = mod_count

            if 'imod' in self.chunk_data:
                mod_count = self.chunk_info['imod'].size // SF2Spec.MOD_ENTRY_SIZE
                stats['instrument_modulators'] = mod_count

            if 'smpl' in self.chunk_data:
                stats['sample_data_size'] = len(self.chunk_data['smpl'])

            if 'sm24' in self.chunk_data:
                stats['sample_data_24bit_size'] = len(self.chunk_data['sm24'])

        except Exception as e:
            logger.warning(f"Failed to compute data statistics: {e}")

        return stats


def parse_sf2_data_structures(chunk_data: Dict[str, bytes],
                            chunk_info: Dict[str, ChunkInfo]) -> SF2DataParser:
    """
    Convenience function to create and return an SF2DataParser.

    Args:
        chunk_data: Dictionary mapping chunk IDs to raw data
        chunk_info: Dictionary mapping chunk IDs to ChunkInfo objects

    Returns:
        Configured SF2DataParser instance
    """
    return SF2DataParser(chunk_data, chunk_info)
