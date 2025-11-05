"""
SF2 SoundFont Manager

Refactored version of Sf2SoundFont with modular design and optimizations for large soundfonts.
"""

import os
import threading
from typing import Optional, BinaryIO, List, Dict, Tuple, Union, Any, Set
from ..types import SF2Preset, SF2Instrument, SF2SampleHeader
from ..parsing import ChunkParser, PresetParser, InstrumentParser, SampleParser
from ..caching import SampleCache, StructureCache


class SoundFontManager:
    """
    Manages a single SoundFont file with modular parsing and caching.
    """

    def __init__(self, sf2_path: str, priority: int = 0, max_memory_mb: int = 200,
                 preload_critical: bool = True, lazy_headers: bool = True,
                 selective_parsing: bool = True):
        """
        Initialize SoundFont manager with optimizations for large soundfonts.

        Args:
            sf2_path: Path to SF2 file
            priority: Priority for this SoundFont
            max_memory_mb: Maximum memory for sample cache in MB
            preload_critical: Whether to preload critical presets
            lazy_headers: Whether to use lazy header loading
            selective_parsing: Whether to use selective parsing for presets
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

        # Initialize caches with configurable limits
        sample_cache_limit = max_memory_mb * 1024 * 1024  # Convert MB to bytes
        self.sample_cache = SampleCache(max_size=sample_cache_limit)
        self.structure_cache = StructureCache()

        # Data structures
        self.presets: List[SF2Preset] = []
        self.instruments: List[SF2Instrument] = []
        self.instrument_names: List[str] = []
        self.sample_headers: List[SF2SampleHeader] = []

        # Configuration
        self.preset_blacklist: Set[Tuple[int, int]] = set()
        self.bank_blacklist: Set[int] = set()
        self.bank_mapping: Dict[int, int] = {}
        self.max_memory_mb = max_memory_mb
        self.preload_critical = preload_critical
        self.lazy_headers = lazy_headers
        self.selective_parsing = selective_parsing  # New configuration option

        # Lazy loading state
        self._headers_loaded = False
        self._presets_loaded = False
        self._instruments_loaded: Set[int] = set()
        self._samples_loaded: Set[int] = set()

        # Critical presets for preloading
        self._critical_presets: Set[Tuple[int, int]] = set()

        # Threading locks for concurrent access
        self._file_lock = threading.Lock()
        self._cache_lock = threading.Lock()

        # Initialize file
        self._initialize_file()

        # Preload critical presets if enabled
        if self.preload_critical:
            self.preload_critical_presets()

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
        """Parse basic headers for quick access with lazy loading."""
        if not self.preset_parser or not self.instrument_parser or not self.sample_parser:
            return

        try:
            # Parse preset headers
            self.presets = self.preset_parser.parse_preset_headers()

            # Parse instrument headers
            self.instruments, self.instrument_names = self.instrument_parser.parse_instrument_headers()

            # Parse sample headers
            self.sample_headers = self.sample_parser.parse_sample_headers()

            self._headers_loaded = True

        except Exception as e:
            print(f"Error parsing headers for {self.path}: {e}")

    def _ensure_headers_loaded(self):
        """Ensure headers are loaded if using lazy loading."""
        if self.lazy_headers and not self._headers_loaded:
            with self._file_lock:
                if not self._headers_loaded:
                    self._parse_headers()

    def get_preset(self, program: int, bank: int) -> Optional[SF2Preset]:
        """
        Get preset by program and bank with enhanced lazy loading and caching.
        Uses selective parsing when enabled for dramatic performance improvements.

        Args:
            program: Program number
            bank: Bank number

        Returns:
            SF2Preset or None
        """
        # Ensure headers are loaded
        self._ensure_headers_loaded()

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
        with self._cache_lock:
            if self.structure_cache.is_preset_parsed(self.path, preset_index):
                return self.structure_cache.get_preset(self.path, preset_index)

        # Use selective parsing if enabled (dramatic performance improvement)
        if self.selective_parsing and self.preset_parser:
            with self._file_lock:
                zones = self.preset_parser.parse_single_preset_zones(preset_index, self.presets)
                preset.zones = zones
                self._presets_loaded = True  # Mark as loaded to avoid full batch parsing
        else:
            # Fallback to batch parsing for backward compatibility
            with self._file_lock:
                if self.preset_parser and not self._presets_loaded:
                    self.presets = self.preset_parser.parse_preset_zones(self.presets)
                    self._presets_loaded = True

        # Cache and return
        with self._cache_lock:
            if preset_index < len(self.presets):
                self.structure_cache.put_preset(self.path, preset_index, self.presets[preset_index])
                return self.presets[preset_index]

        return None

    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """
        Get instrument by index with enhanced lazy loading and caching.

        Args:
            index: Instrument index

        Returns:
            SF2Instrument or None
        """
        # Ensure headers are loaded
        self._ensure_headers_loaded()

        if index < 0 or index >= len(self.instruments):
            return None

        # Check cache first
        with self._cache_lock:
            if self.structure_cache.is_instrument_parsed(self.path, index):
                return self.structure_cache.get_instrument(self.path, index)

        # Parse instrument if not cached
        with self._file_lock:
            if index not in self._instruments_loaded:
                inst = self.instrument_parser.parse_instrument_zones(index) # type: ignore
                self._instruments_loaded.add(index)
                if inst:
                    with self._cache_lock:
                        self.structure_cache.put_instrument(self.path, index, inst)
                    return inst

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
        Read sample data with enhanced caching and memory management.

        Args:
            sample_header: Sample header

        Returns:
            Sample data or None
        """
        if not self.sample_parser:
            return None

        # Check if sample is already loaded
        sample_index = self.sample_headers.index(sample_header) if sample_header in self.sample_headers else -1
        if sample_index in self._samples_loaded:
            return sample_header.data

        # Check cache first
        cache_key = f"{self.path}.{sample_header.name}"
        with self._cache_lock:
            cached_sample = self.sample_cache.get(cache_key)
            if cached_sample and cached_sample.data:
                sample_header.data = cached_sample.data
                self._samples_loaded.add(sample_index)
                return cached_sample.data

        # Read from file
        with self._file_lock:
            sample_data = self.sample_parser.read_sample_data(sample_header)

        # Cache if successful
        if sample_data:
            sample_header.data = sample_data
            with self._cache_lock:
                self.sample_cache.put(cache_key, sample_header)
            self._samples_loaded.add(sample_index)

        return sample_data

    def preload_preset(self, preset_index: int):
        """
        Preload a preset and its associated data with enhanced caching.

        Args:
            preset_index: Index of preset to preload
        """
        if preset_index < 0 or preset_index >= len(self.presets):
            return

        preset = self.presets[preset_index]

        # Ensure preset is parsed
        with self._cache_lock:
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

    def preload_critical_presets(self):
        """
        Preload critical presets based on common usage patterns.
        """
        if not self.preload_critical or not self._critical_presets:
            return

        for bank, program in self._critical_presets:
            preset = self.get_preset(program, bank)
            if preset:
                preset_index = self.presets.index(preset)
                self.preload_preset(preset_index)

    def set_critical_presets(self, critical_presets: Set[Tuple[int, int]]):
        """
        Set the list of critical presets to preload.

        Args:
            critical_presets: Set of (bank, program) tuples
        """
        self._critical_presets = critical_presets.copy()

    def add_critical_preset(self, bank: int, program: int):
        """
        Add a critical preset to the preload list.

        Args:
            bank: Bank number
            program: Program number
        """
        self._critical_presets.add((bank, program))

    def batch_parse_presets(self, preset_indices: List[int]):
        """
        Parse multiple presets in batch for better performance.
        Falls back to batch parsing when selective parsing is disabled.

        Args:
            preset_indices: List of preset indices to parse
        """
        if self.selective_parsing:
            # Use selective parsing for each preset
            for idx in preset_indices:
                if idx < len(self.presets) and not self.presets[idx].zones:
                    with self._file_lock:
                        if self.preset_parser:
                            zones = self.preset_parser.parse_single_preset_zones(idx, self.presets)
                            self.presets[idx].zones = zones
                    with self._cache_lock:
                        self.structure_cache.put_preset(self.path, idx, self.presets[idx])
        else:
            # Use traditional batch parsing
            with self._file_lock:
                if self.preset_parser and not self._presets_loaded:
                    self.presets = self.preset_parser.parse_preset_zones(self.presets)
                    self._presets_loaded = True

            # Cache all parsed presets
            with self._cache_lock:
                for idx in preset_indices:
                    if idx < len(self.presets):
                        self.structure_cache.put_preset(self.path, idx, self.presets[idx])

    def batch_parse_instruments(self, instrument_indices: List[int]):
        """
        Parse multiple instruments in batch for better performance.

        Args:
            instrument_indices: List of instrument indices to parse
        """
        for idx in instrument_indices:
            if idx not in self._instruments_loaded and idx < len(self.instruments):
                with self._file_lock:
                    inst = self.instrument_parser.parse_instrument_zones(idx) # type: ignore
                if inst:
                    with self._cache_lock:
                        self.structure_cache.put_instrument(self.path, idx, inst)
                    self._instruments_loaded.add(idx)

    def get_memory_usage(self) -> Dict[str, Union[int, float]]:
        """
        Get current memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        sample_cache_stats = self.sample_cache.get_stats()
        structure_cache_stats = self.structure_cache.get_cache_stats()

        return {
            'sample_cache_bytes': sample_cache_stats['current_size'],
            'sample_cache_limit': sample_cache_stats['max_size'],
            'sample_cache_utilization': sample_cache_stats['utilization'],
            'cached_samples': sample_cache_stats['num_samples'],
            'cached_presets': structure_cache_stats['parsed_presets'],
            'cached_instruments': structure_cache_stats['parsed_instruments'],
            'total_files_cached': structure_cache_stats['files_cached']
        }

    def cleanup_memory(self, target_utilization: float = 0.8):
        """
        Clean up memory by evicting less recently used items.

        Args:
            target_utilization: Target cache utilization (0.0 to 1.0)
        """
        sample_cache_stats = self.sample_cache.get_stats()
        current_utilization = sample_cache_stats['utilization']

        if current_utilization > target_utilization:
            # Calculate how many bytes to evict
            target_bytes = int(self.sample_cache.max_size * target_utilization)
            bytes_to_evict = sample_cache_stats['current_size'] - target_bytes

            # Evict samples from this soundfont
            evicted = self.sample_cache.evict_by_pattern(self.path)
            print(f"Evicted {evicted} samples from {self.path} to free memory")

    def clear_cache(self):
        """
        Clear all caches for this SoundFont.
        """
        self.sample_cache.clear()
        self.structure_cache.clear_file_cache(self.path)
        if self.preset_parser:
            self.preset_parser.clear_preset_zone_cache()

    def get_file_info(self) -> Dict[str, Any]:
        """
        Get information about this SoundFont file.

        Returns:
            Dictionary with file information
        """
        memory_usage = self.get_memory_usage()
        parser_stats = {}
        if self.preset_parser:
            parser_stats = self.preset_parser.get_cache_stats()

        return {
            'path': self.path,
            'priority': self.priority,
            'file_size': self.file_size,
            'presets_count': len(self.presets),
            'instruments_count': len(self.instruments),
            'samples_count': len(self.sample_headers),
            'headers_loaded': self._headers_loaded,
            'presets_loaded': self._presets_loaded,
            'instruments_loaded_count': len(self._instruments_loaded),
            'samples_loaded_count': len(self._samples_loaded),
            'critical_presets_count': len(self._critical_presets),
            'selective_parsing_enabled': self.selective_parsing,
            'memory_usage': memory_usage,
            'cache_stats': self.sample_cache.get_stats(),
            'parser_cache_stats': parser_stats
        }
