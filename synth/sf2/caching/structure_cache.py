"""
SF2 Structure Cache

Handles caching of parsed SF2 structures to avoid re-parsing.
"""

import threading
from typing import Dict, Set, Any, Optional, Tuple
from ..types import SF2Preset, SF2Instrument


class StructureCache:
    """
    Cache for parsed SF2 structures with thread-safe access.
    """

    def __init__(self):
        """Initialize structure cache."""
        self.lock = threading.Lock()

        # Cache for parsed presets and instruments
        self.parsed_presets: Dict[str, Dict[int, SF2Preset]] = {}
        self.parsed_instruments: Dict[str, Dict[int, SF2Instrument]] = {}

        # Track which structures have been parsed
        self.parsed_preset_indices: Dict[str, Set[int]] = {}
        self.parsed_instrument_indices: Dict[str, Set[int]] = {}

        # Cache for modulation and normalization data
        self.source_name_cache: Dict[Tuple[int, int], str] = {}
        self.normalize_cache: Dict[Tuple[int, int], float] = {}

    def get_preset(self, sf2_path: str, preset_index: int) -> Optional[SF2Preset]:
        """
        Get cached preset.

        Args:
            sf2_path: Path to SF2 file
            preset_index: Preset index

        Returns:
            Cached preset or None
        """
        with self.lock:
            if sf2_path in self.parsed_presets:
                return self.parsed_presets[sf2_path].get(preset_index)
            return None

    def put_preset(self, sf2_path: str, preset_index: int, preset: SF2Preset):
        """
        Cache a preset.

        Args:
            sf2_path: Path to SF2 file
            preset_index: Preset index
            preset: Preset to cache
        """
        with self.lock:
            if sf2_path not in self.parsed_presets:
                self.parsed_presets[sf2_path] = {}
                self.parsed_preset_indices[sf2_path] = set()

            self.parsed_presets[sf2_path][preset_index] = preset
            self.parsed_preset_indices[sf2_path].add(preset_index)

    def get_instrument(self, sf2_path: str, instrument_index: int) -> Optional[SF2Instrument]:
        """
        Get cached instrument.

        Args:
            sf2_path: Path to SF2 file
            instrument_index: Instrument index

        Returns:
            Cached instrument or None
        """
        with self.lock:
            if sf2_path in self.parsed_instruments:
                return self.parsed_instruments[sf2_path].get(instrument_index)
            return None

    def put_instrument(self, sf2_path: str, instrument_index: int, instrument: SF2Instrument):
        """
        Cache an instrument.

        Args:
            sf2_path: Path to SF2 file
            instrument_index: Instrument index
            instrument: Instrument to cache
        """
        with self.lock:
            if sf2_path not in self.parsed_instruments:
                self.parsed_instruments[sf2_path] = {}
                self.parsed_instrument_indices[sf2_path] = set()

            self.parsed_instruments[sf2_path][instrument_index] = instrument
            self.parsed_instrument_indices[sf2_path].add(instrument_index)

    def is_preset_parsed(self, sf2_path: str, preset_index: int) -> bool:
        """
        Check if a preset has been parsed.

        Args:
            sf2_path: Path to SF2 file
            preset_index: Preset index

        Returns:
            True if preset is cached
        """
        with self.lock:
            return (sf2_path in self.parsed_preset_indices and
                   preset_index in self.parsed_preset_indices[sf2_path])

    def is_instrument_parsed(self, sf2_path: str, instrument_index: int) -> bool:
        """
        Check if an instrument has been parsed.

        Args:
            sf2_path: Path to SF2 file
            instrument_index: Instrument index

        Returns:
            True if instrument is cached
        """
        with self.lock:
            return (sf2_path in self.parsed_instrument_indices and
                   instrument_index in self.parsed_instrument_indices[sf2_path])

    def get_source_name(self, source_oper: int, source_index: int) -> Optional[str]:
        """
        Get cached source name.

        Args:
            source_oper: Source operator
            source_index: Source index

        Returns:
            Cached source name or None
        """
        cache_key = (source_oper, source_index)
        with self.lock:
            return self.source_name_cache.get(cache_key)

    def put_source_name(self, source_oper: int, source_index: int, source_name: str):
        """
        Cache a source name.

        Args:
            source_oper: Source operator
            source_index: Source index
            source_name: Source name to cache
        """
        cache_key = (source_oper, source_index)
        with self.lock:
            self.source_name_cache[cache_key] = source_name

    def get_normalized_amount(self, amount: int, destination: int) -> Optional[float]:
        """
        Get cached normalized amount.

        Args:
            amount: Raw amount
            destination: Modulation destination

        Returns:
            Cached normalized amount or None
        """
        cache_key = (amount, destination)
        with self.lock:
            return self.normalize_cache.get(cache_key)

    def put_normalized_amount(self, amount: int, destination: int, normalized_amount: float):
        """
        Cache a normalized amount.

        Args:
            amount: Raw amount
            destination: Modulation destination
            normalized_amount: Normalized amount to cache
        """
        cache_key = (amount, destination)
        with self.lock:
            self.normalize_cache[cache_key] = normalized_amount

    def clear_file_cache(self, sf2_path: str):
        """
        Clear all cached data for a specific SF2 file.

        Args:
            sf2_path: Path to SF2 file
        """
        with self.lock:
            if sf2_path in self.parsed_presets:
                del self.parsed_presets[sf2_path]
            if sf2_path in self.parsed_instruments:
                del self.parsed_instruments[sf2_path]
            if sf2_path in self.parsed_preset_indices:
                del self.parsed_preset_indices[sf2_path]
            if sf2_path in self.parsed_instrument_indices:
                del self.parsed_instrument_indices[sf2_path]

    def clear_all_cache(self):
        """
        Clear all cached data.
        """
        with self.lock:
            self.parsed_presets.clear()
            self.parsed_instruments.clear()
            self.parsed_preset_indices.clear()
            self.parsed_instrument_indices.clear()
            self.source_name_cache.clear()
            self.normalize_cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            return {
                'parsed_presets': sum(len(presets) for presets in self.parsed_presets.values()),
                'parsed_instruments': sum(len(instruments) for instruments in self.parsed_instruments.values()),
                'source_names_cached': len(self.source_name_cache),
                'normalized_amounts_cached': len(self.normalize_cache),
                'files_cached': len(self.parsed_presets)
            }

    def preload_file_structures(self, sf2_path: str, presets: Dict[int, SF2Preset],
                              instruments: Dict[int, SF2Instrument]):
        """
        Preload parsed structures for a file.

        Args:
            sf2_path: Path to SF2 file
            presets: Dictionary of presets to cache
            instruments: Dictionary of instruments to cache
        """
        with self.lock:
            # Cache presets
            if sf2_path not in self.parsed_presets:
                self.parsed_presets[sf2_path] = {}
                self.parsed_preset_indices[sf2_path] = set()

            for preset_index, preset in presets.items():
                self.parsed_presets[sf2_path][preset_index] = preset
                self.parsed_preset_indices[sf2_path].add(preset_index)

            # Cache instruments
            if sf2_path not in self.parsed_instruments:
                self.parsed_instruments[sf2_path] = {}
                self.parsed_instrument_indices[sf2_path] = set()

            for instrument_index, instrument in instruments.items():
                self.parsed_instruments[sf2_path][instrument_index] = instrument
                self.parsed_instrument_indices[sf2_path].add(instrument_index)
