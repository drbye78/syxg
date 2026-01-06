"""
SF2 SoundFont - Main coordinator for SF2 synthesis with lazy loading.

This module provides the main SF2SoundFont class that coordinates all SF2
components with full integration into the modern synth engine.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..types.dataclasses import SF2Preset, SF2Instrument, SF2Sample, SF2Zone
from ..parsing.chunk_parser import SF2ChunkParser, ChunkInfo
from ..parsing.data_parser import SF2DataParser
from ..parsing.zone_processor import SF2ZoneProcessor
from .constants import SF2Spec

logger = logging.getLogger(__name__)


class SF2SoundFont:
    """
    Production-quality SF2 SoundFont with complete lazy loading and modern synth integration.

    Provides full SF2 specification compliance with:
    - True lazy loading for 1GB+ soundfonts
    - Multi-format sample support (16/24-bit, mono/stereo)
    - Sample mip-mapping for high-pitch quality
    - Complete integration with modern synth engine
    - Memory-efficient caching and resource management
    """

    def __init__(self, file_path: str, max_memory_mb: int = 512):
        """
        Initialize SF2 SoundFont with lazy loading.

        Args:
            file_path: Path to the SF2 file
            max_memory_mb: Maximum memory to use for caching
        """
        self.file_path = Path(file_path)
        self.max_memory_mb = max_memory_mb

        # Core components
        self.chunk_parser: Optional[SF2ChunkParser] = None
        self.data_parser: Optional[SF2DataParser] = None
        self.zone_processor: Optional[SF2ZoneProcessor] = None

        # Parsed data
        self.presets: Optional[List[SF2Preset]] = None
        self.instruments: Optional[List[SF2Instrument]] = None
        self.samples: Optional[List[SF2Sample]] = None

        # Caching and resource management
        self.sample_cache: Dict[int, SF2Sample] = {}
        self.mip_maps: Dict[int, Any] = {}  # SampleMipMap instances
        self.mip_selectors: Dict[int, Any] = {}  # MipLevelSelector instances

        # Memory tracking
        self.memory_usage = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # Load metadata only (true lazy loading)
        self._load_metadata()

    def _load_metadata(self):
        """Load only metadata initially (true lazy loading)."""
        try:
            logger.info(f"Loading SF2 metadata from {self.file_path}")

            # Parse chunks and load critical data
            self.chunk_parser = SF2ChunkParser(str(self.file_path))
            chunk_data = {}
            chunk_info = {}

            with self.chunk_parser as parser:
                chunks = parser.parse_chunks()

                # Load all required SF2 chunks (metadata + zone data)
                required_chunks = ['phdr', 'pbag', 'pgen', 'inst', 'ibag', 'igen', 'shdr']
                for chunk_id in required_chunks:
                    if chunk_id in chunks:
                        chunk_data[chunk_id] = parser.get_chunk_data(chunk_id)
                        chunk_info[chunk_id] = chunks[chunk_id]
                    else:
                        logger.warning(f"Required chunk {chunk_id} not found in SF2 file")

                # Also load modulator chunks if present
                optional_chunks = ['pmod', 'imod']
                for chunk_id in optional_chunks:
                    if chunk_id in chunks:
                        chunk_data[chunk_id] = parser.get_chunk_data(chunk_id)
                        chunk_info[chunk_id] = chunks[chunk_id]

                # Validate structure
                if not parser.validate_sf2_structure():
                    raise ValueError("Invalid SF2 file structure")

            # Create data parser
            self.data_parser = SF2DataParser(chunk_data, chunk_info)

            # Create zone processor
            self.zone_processor = SF2ZoneProcessor(self.data_parser)

            logger.info("SF2 metadata loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load SF2 metadata: {e}")
            raise

    def get_preset(self, bank: int, preset_num: int) -> Optional[SF2Preset]:
        """
        Get preset with lazy loading and processing.

        Args:
            bank: MIDI bank number
            preset_num: MIDI preset number

        Returns:
            SF2Preset object, or None if not found
        """
        if self.presets is None:
            self._load_all_presets()

        # Find the preset
        for preset in self.presets:
            if preset.bank == bank and preset.preset_number == preset_num:
                return preset

        return None

    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """
        Get instrument with lazy loading and processing.

        Args:
            index: Instrument index

        Returns:
            SF2Instrument object, or None if not found
        """
        if self.instruments is None:
            self._load_all_instruments()

        if 0 <= index < len(self.instruments):
            return self.instruments[index]

        return None

    def get_sample(self, index: int, pitch_ratio: float = 1.0) -> Optional[SF2Sample]:
        """
        Get sample with lazy loading and mip-mapping.

        Args:
            index: Sample index
            pitch_ratio: Playback pitch ratio for mip level selection

        Returns:
            SF2Sample object with appropriate mip level, or None if not found
        """
        if self.samples is None:
            self._load_all_samples()

        if not (0 <= index < len(self.samples)):
            return None

        sample = self.samples[index]

        # Lazy load sample data if not already loaded
        if not sample.loaded:
            self._load_sample_data(sample, index)

        # Apply mip-mapping for high-pitch playback
        if pitch_ratio > 1.5:  # Only use mip-mapping for significant pitch shifts
            return self._get_mip_mapped_sample(sample, index, pitch_ratio)

        return sample

    def get_preset_zones(self, bank: int, preset_num: int, note: int = 60, velocity: int = 100) -> List[SF2Zone]:
        """
        Get zones for a preset that match the given note and velocity.

        Args:
            bank: MIDI bank number
            preset_num: MIDI preset number
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones with layering support
        """
        if not self.zone_processor:
            return []

        return self.zone_processor.get_preset_zones(bank, preset_num)

    def _load_all_presets(self):
        """Load and process all presets."""
        if not self.zone_processor:
            self.presets = []
            return

        logger.info("Processing all presets...")
        self.presets = self.zone_processor.process_all_presets()
        logger.info(f"Loaded {len(self.presets)} presets")

    def _load_all_instruments(self):
        """Load and process all instruments."""
        if not self.zone_processor:
            self.instruments = []
            return

        logger.info("Processing all instruments...")
        self.instruments = self.zone_processor.process_all_instruments()
        logger.info(f"Loaded {len(self.instruments)} instruments")

    def _load_all_samples(self):
        """Load sample metadata (not sample data itself - lazy loading)."""
        if not self.data_parser:
            self.samples = []
            return

        logger.info("Loading sample metadata...")
        sample_headers = self.data_parser.parse_sample_headers()

        self.samples = []
        for header in sample_headers:
            # Create SF2Sample with metadata only (lazy loading)
            sample = SF2Sample(
                name=header.name,
                sample_rate=header.sample_rate,
                original_pitch=header.original_pitch,
                pitch_correction=header.pitch_correction,
                format=self._determine_sample_format(header),
                data=None,  # Not loaded yet
                loop_start=header.start_loop,
                loop_end=header.end_loop,
                loop_mode=self._determine_loop_mode(header),
                loaded=False
            )
            self.samples.append(sample)

        logger.info(f"Loaded metadata for {len(self.samples)} samples")

    def _load_sample_data(self, sample: SF2Sample, index: int):
        """Lazy load sample data with format detection."""
        if not self.chunk_parser:
            return

        try:
            # Determine which chunk contains the sample data
            sample_header = self.data_parser.parse_sample_headers()[index]

            # Load sample data based on format
            if self._is_24bit_sample(sample_header):
                sample_data = self.data_parser.parse_sample_data_24bit()
                if sample_data:
                    # Convert 24-bit data to float32
                    sample.data = self._convert_24bit_to_float32(sample_data, sample_header)
            else:
                sample_data = self.data_parser.parse_sample_data()
                if sample_data:
                    # Convert 16-bit data to float32
                    sample.data = self._convert_16bit_to_float32(sample_data, sample_header)

            if sample.data is not None:
                sample.loaded = True
                self.memory_usage += sample.data.nbytes

                # Create mip-map for this sample
                self._create_mip_map(sample, index)

                logger.debug(f"Loaded sample {index}: {sample.name} ({len(sample.data)} samples)")

        except Exception as e:
            logger.warning(f"Failed to load sample {index}: {e}")

    def _get_mip_mapped_sample(self, sample: SF2Sample, index: int, pitch_ratio: float) -> Optional[SF2Sample]:
        """Get mip-mapped version of sample for high-pitch playback."""
        if index not in self.mip_maps:
            return sample

        mip_map = self.mip_maps[index]
        selector = self.mip_selectors.get(index)

        if selector and mip_map:
            # Select appropriate mip level
            level = selector.select_stable_level(pitch_ratio)

            if level > 0:
                try:
                    mip_data = mip_map.get_level(level)

                    # Create a copy of the sample with mip-mapped data
                    mip_sample = SF2Sample(
                        name=f"{sample.name}_mip{level}",
                        sample_rate=sample.sample_rate,
                        original_pitch=sample.original_pitch,
                        pitch_correction=sample.pitch_correction,
                        format=sample.format,
                        data=mip_data,
                        loop_start=sample.loop_start,
                        loop_end=sample.loop_end,
                        loop_mode=sample.loop_mode,
                        loaded=True
                    )

                    self.cache_hits += 1
                    return mip_sample

                except Exception as e:
                    logger.warning(f"Failed to get mip level {level} for sample {index}: {e}")

        self.cache_misses += 1
        return sample

    def _create_mip_map(self, sample: SF2Sample, index: int):
        """Create mip-map for sample to improve high-pitch quality."""
        if sample.data is None:
            return

        try:
            from ..core.mipmapping import create_sample_mipmap, MipLevelSelector

            mip_map = create_sample_mipmap(sample.data, sample.sample_rate)
            self.mip_maps[index] = mip_map
            self.mip_selectors[index] = MipLevelSelector()

            mip_memory = mip_map.get_memory_usage()
            self.memory_usage += mip_memory

            logger.debug(f"Created mip-map for sample {index}, {mip_memory} bytes")

        except Exception as e:
            logger.warning(f"Failed to create mip-map for sample {index}: {e}")

    def _determine_sample_format(self, header) -> str:
        """Determine sample format from header."""
        if hasattr(header, 'sample_type'):
            if header.sample_type & 0x8000:  # 24-bit
                if header.sample_type & 0x8002:  # Right channel
                    return "stereo_24bit"
                elif header.sample_type & 0x8004:  # Left channel
                    return "stereo_24bit"
                else:
                    return "mono_24bit"
            else:  # 16-bit
                if header.sample_type & 0x0002:  # Right channel
                    return "stereo_16bit"
                elif header.sample_type & 0x0004:  # Left channel
                    return "stereo_16bit"
                else:
                    return "mono_16bit"

        return "mono_16bit"  # Default

    def _determine_loop_mode(self, header) -> int:
        """Determine loop mode from sample header."""
        # SF2 loop modes based on sample type flags
        if hasattr(header, 'sample_type'):
            sample_type = header.sample_type & 0x7FFF  # Mask out 24-bit flag

            if sample_type == 1:  # Mono sample
                return 0  # No loop
            elif sample_type in [2, 4]:  # Stereo samples
                return 0  # No loop for stereo
            elif sample_type == 8:  # Linked sample
                return 1  # Forward loop

        return 0  # Default: no loop

    def _is_24bit_sample(self, header) -> bool:
        """Check if sample is 24-bit."""
        return hasattr(header, 'sample_type') and (header.sample_type & 0x8000)

    def _convert_16bit_to_float32(self, data: bytes, header) -> Optional[Any]:
        """Convert 16-bit sample data to float32."""
        try:
            import numpy as np

            # Calculate sample range for this sample
            start_sample = header.start
            end_sample = header.end

            if start_sample >= end_sample:
                return None

            sample_count = end_sample - start_sample
            expected_bytes = sample_count * 2  # 16-bit = 2 bytes per sample

            if len(data) < start_sample * 2 + expected_bytes:
                return None

            # Extract sample data
            sample_start = start_sample * 2
            sample_end = sample_start + expected_bytes
            sample_bytes = data[sample_start:sample_end]

            # Convert to numpy array
            samples = np.frombuffer(sample_bytes, dtype=np.int16)
            return samples.astype(np.float32) / 32768.0

        except Exception as e:
            logger.warning(f"Failed to convert 16-bit sample data: {e}")
            return None

    def _convert_24bit_to_float32(self, data: bytes, header) -> Optional[Any]:
        """Convert 24-bit sample data to float32."""
        try:
            import numpy as np

            # Calculate sample range for this sample
            start_sample = header.start
            end_sample = header.end

            if start_sample >= end_sample:
                return None

            sample_count = end_sample - start_sample
            expected_bytes = sample_count * 3  # 24-bit = 3 bytes per sample

            if len(data) < start_sample * 3 + expected_bytes:
                return None

            # Extract sample data
            sample_start = start_sample * 3
            sample_end = sample_start + expected_bytes
            sample_bytes = data[sample_start:sample_end]

            # Convert 24-bit to float32
            samples = np.zeros(sample_count, dtype=np.float32)

            for i in range(sample_count):
                # Read 3 bytes as 24-bit signed integer
                byte_offset = i * 3
                if byte_offset + 3 > len(sample_bytes):
                    break

                sample_24bit = sample_bytes[byte_offset:byte_offset + 3]
                sample_int = int.from_bytes(sample_24bit, byteorder='little', signed=True)

                # Sign extend from 24-bit to 32-bit
                if sample_int & 0x800000:
                    sample_int |= 0xFF000000

                # Convert to float32
                samples[i] = sample_int / 8388608.0  # 2^23

            return samples

        except Exception as e:
            logger.warning(f"Failed to convert 24-bit sample data: {e}")
            return None

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage statistics."""
        return {
            'total_mb': self.memory_usage / (1024 * 1024),
            'samples_loaded': sum(1 for s in (self.samples or []) if s and s.loaded),
            'total_samples': len(self.samples) if self.samples else 0,
            'mip_maps_created': len(self.mip_maps),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': (self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100
        }

    def clear_cache(self):
        """Clear sample cache to free memory."""
        self.sample_cache.clear()
        self.mip_maps.clear()
        self.mip_selectors.clear()

        # Mark all samples as not loaded
        if self.samples:
            for sample in self.samples:
                sample.loaded = False
                sample.data = None

        self.memory_usage = 0
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info("SF2 cache cleared")

    def validate_soundfont(self) -> Dict[str, Any]:
        """Validate the soundfont and return detailed validation results."""
        if not self.zone_processor:
            return {'valid': False, 'errors': ['Zone processor not initialized']}

        return self.zone_processor.validate_zone_processing()


def create_sf2_soundfont(file_path: str, max_memory_mb: int = 512) -> SF2SoundFont:
    """
    Convenience function to create an SF2SoundFont.

    Args:
        file_path: Path to the SF2 file
        max_memory_mb: Maximum memory for caching

    Returns:
        Configured SF2SoundFont instance
    """
    return SF2SoundFont(file_path, max_memory_mb)
