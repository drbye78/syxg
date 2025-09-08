"""
SF2 SoundFont Manager

Refactored version of Sf2SoundFont with modular design.
"""

import os
from typing import Optional, BinaryIO, List, Dict, Tuple, Union, Any
from ..types import SF2Preset, SF2Instrument, SF2SampleHeader
from ..parsing import ChunkParser, PresetParser, InstrumentParser, SampleParser
from ..caching import SampleCache, StructureCache


class SoundFontManager:
    """
    Manages a single SoundFont file with modular parsing and caching.
    """

    def __init__(self, sf2_path: str, priority: int = 0):
        """
        Initialize SoundFont manager.

        Args:
            sf2_path: Path to SF2 file
            priority: Priority for this SoundFont
        """
        self.path = sf2_path
        self.priority = priority
        self.file: Optional[BinaryIO] = None
        self.file_size = 0

        # Initialize parsers (will be set up in _initialize_file)
        self.chunk_parser: Optional[ChunkParser] = None
        self.preset_parser: Optional[PresetParser] = None
        self.instrument_parser: Optional[InstrumentParser] = None
        self.sample_parser: Optional[SampleParser] = None

        # Initialize caches
        self.sample_cache = SampleCache()
        self.structure_cache = StructureCache()

        # Data structures
        self.presets: List[SF2Preset] = []
        self.instruments: List[SF2Instrument] = []
        self.instrument_names: List[str] = []
        self.sample_headers: List[SF2SampleHeader] = []

        # Configuration
        self.preset_blacklist = []
        self.bank_blacklist = []
        self.bank_mapping = {}

        # Flags
        self.headers_parsed = False
        self.presets_parsed = False
        self.instruments_parsed = False
        self.samples_parsed = False

        # Initialize file
        self._initialize_file()

    def __del__(self):
        """Clean up file handle."""
        if self.file and not self.file.closed:
            self.file.close()

    def _initialize_file(self):
        """Initialize the SF2 file and basic structures."""
        try:
            # Open file
            self.file = open(self.path, 'rb', buffering=1024*1024)
            self.file_size = os.path.getsize(self.path)

            # Initialize parsers with file handle
            self.chunk_parser = ChunkParser(self.file)

            # Validate file format
            if not self.chunk_parser.parse_file_header():
                raise ValueError(f"Invalid SF2 file format: {self.path}")

            # Locate chunks
            chunk_info = self.chunk_parser.locate_chunks()

            # Initialize specialized parsers
            self.preset_parser = PresetParser(self.file, chunk_info)
            self.instrument_parser = InstrumentParser(self.file, chunk_info)
            self.sample_parser = SampleParser(self.file, chunk_info)

            # Parse headers for quick access
            self._parse_headers()

        except Exception as e:
            print(f"Error initializing SF2 file {self.path}: {e}")
            if self.file and not self.file.closed:
                self.file.close()
            self.file = None

    def _parse_headers(self):
        """Parse basic headers for quick access."""
        if not self.preset_parser or not self.instrument_parser or not self.sample_parser:
            return

        try:
            # Parse preset headers
            self.presets = self.preset_parser.parse_preset_headers()

            # Parse instrument headers
            self.instruments, self.instrument_names = self.instrument_parser.parse_instrument_headers()

            # Parse sample headers
            self.sample_headers = self.sample_parser.parse_sample_headers()

            self.headers_parsed = True

        except Exception as e:
            print(f"Error parsing headers for {self.path}: {e}")

    def get_preset(self, program: int, bank: int) -> Optional[SF2Preset]:
        """
        Get preset by program and bank with lazy loading.

        Args:
            program: Program number
            bank: Bank number

        Returns:
            SF2Preset or None
        """
        # Apply bank mapping
        mapped_bank = self.bank_mapping.get(bank, bank)

        # Check blacklists
        if mapped_bank in self.bank_blacklist:
            return None

        preset_key = (mapped_bank, program)
        if preset_key in self.preset_blacklist:
            return None

        # Find preset
        preset = None
        preset_index = -1

        for i, p in enumerate(self.presets):
            if p.preset == program and p.bank == mapped_bank:
                preset = p
                preset_index = i
                break

        if not preset:
            return None

        # Check cache first
        if self.structure_cache.is_preset_parsed(self.path, preset_index):
            return self.structure_cache.get_preset(self.path, preset_index)

        # Parse preset if not cached
        if self.preset_parser and not self.presets_parsed:
            self.presets = self.preset_parser.parse_preset_zones(self.presets)
            self.presets_parsed = True

        # Cache and return
        if preset_index < len(self.presets):
            self.structure_cache.put_preset(self.path, preset_index, self.presets[preset_index])
            return self.presets[preset_index]

        return None

    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """
        Get instrument by index with lazy loading.

        Args:
            index: Instrument index

        Returns:
            SF2Instrument or None
        """
        if index < 0 or index >= len(self.instruments):
            return None

        # Check cache first
        if self.structure_cache.is_instrument_parsed(self.path, index):
            return self.structure_cache.get_instrument(self.path, index)

        # Parse instruments if not done
        if self.instrument_parser and not self.instruments_parsed:
            self.instruments = self.instrument_parser.parse_instrument_zones(self.instruments)
            self.instruments_parsed = True

        # Cache and return
        if index < len(self.instruments):
            self.structure_cache.put_instrument(self.path, index, self.instruments[index])
            return self.instruments[index]

        return None

    def get_sample_header(self, index: int) -> Optional[SF2SampleHeader]:
        """
        Get sample header by index.

        Args:
            index: Sample index

        Returns:
            SF2SampleHeader or None
        """
        if index < 0 or index >= len(self.sample_headers):
            return None

        return self.sample_headers[index]

    def read_sample_data(self, sample_header: SF2SampleHeader) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Read sample data with caching.

        Args:
            sample_header: Sample header

        Returns:
            Sample data or None
        """
        if not self.sample_parser:
            return None

        # Check cache first
        cache_key = f"{self.path}.{sample_header.name}"
        cached_sample = self.sample_cache.get(cache_key)
        if cached_sample and cached_sample.data:
            return cached_sample.data

        # Read from file
        sample_data = self.sample_parser.read_sample_data(sample_header)

        # Cache if successful
        if sample_data:
            sample_header.data = sample_data
            self.sample_cache.put(cache_key, sample_header)

        return sample_data

    def preload_preset(self, preset_index: int):
        """
        Preload a preset and its associated data.

        Args:
            preset_index: Index of preset to preload
        """
        if preset_index < 0 or preset_index >= len(self.presets):
            return

        preset = self.presets[preset_index]

        # Ensure preset is parsed
        if not self.structure_cache.is_preset_parsed(self.path, preset_index):
            self.get_preset(preset.preset, preset.bank)

        # Preload associated instruments and samples
        for zone in preset.zones:
            if zone.instrument_index >= 0:
                instrument = self.get_instrument(zone.instrument_index)
                if instrument:
                    for inst_zone in instrument.zones:
                        if inst_zone.sample_index >= 0:
                            sample_header = self.get_sample_header(inst_zone.sample_index)
                            if sample_header:
                                self.read_sample_data(sample_header)

    def clear_cache(self):
        """
        Clear all caches for this SoundFont.
        """
        self.sample_cache.clear()
        self.structure_cache.clear_file_cache(self.path)

    def get_file_info(self) -> Dict[str, Any]:
        """
        Get information about this SoundFont file.

        Returns:
            Dictionary with file information
        """
        return {
            'path': self.path,
            'priority': self.priority,
            'file_size': self.file_size,
            'presets_count': len(self.presets),
            'instruments_count': len(self.instruments),
            'samples_count': len(self.sample_headers),
            'headers_parsed': self.headers_parsed,
            'cache_stats': self.sample_cache.get_stats()
        }
