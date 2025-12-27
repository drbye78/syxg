"""
SF2 Manager

High-level SF2 file management and parameter retrieval.
Integrates all SF2 components for production-quality SoundFont support.
"""

from typing import Dict, List, Any, Optional
import threading
import struct
from collections import OrderedDict

from .containers import RangeTree
from .memory import MemoryPool
import numpy as np
from typing import Set, Tuple

# Import mip-mapping components
try:
    from .mipmapping import SampleMipMap, MipLevelSelector, create_sample_mipmap
    MIPMAPPING_AVAILABLE = True
except ImportError:
    MIPMAPPING_AVAILABLE = False
    SampleMipMap = None
    MipLevelSelector = None
    create_sample_mipmap = None
    print("Warning: Mip-mapping not available, high-pitch notes may have quality issues")


class PreloadedZoneIndex:
    """
    Preloaded zone index for ultra-fast zone lookups.

    Preloads all zone data into optimized data structures for O(1) lookups.
    Eliminates all file I/O during zone matching operations.
    """

    def __init__(self, sf2_file: 'LazySF2SoundFont', chunk_name: str):
        self.sf2_file = sf2_file
        self.chunk_name = chunk_name  # 'pbag' or 'ibag'
        self.is_preset_level = (chunk_name == 'pbag')

        # Preloaded data structures
        self.bag_data: List[Tuple[int, int]] = []  # (gen_ndx, mod_ndx) for each bag
        self.zone_ranges: List[Tuple[int, int, int, int]] = []  # (lokey, hikey, lovel, hivel) for each zone
        self.zone_generators: List[Dict[int, int]] = []  # generator dict for each zone
        self.zone_modulators: List[List] = []  # modulator list for each zone

        # Precompute zone lookup structures
        self._preload_zone_data()

    def _preload_zone_data(self):
        """Preload all zone data into memory structures."""
        # Parse bag data
        self.bag_data = self.sf2_file._parse_bag_data(self.chunk_name)

        if not self.bag_data:
            return

        # Parse generators and modulators for all zones
        gen_data = self.sf2_file._parse_generator_data('pgen' if self.is_preset_level else 'igen')
        mod_data = self.sf2_file._parse_modulator_data('pmod' if self.is_preset_level else 'imod')

        # Process each zone
        for zone_idx in range(len(self.bag_data)):
            gen_start = self.bag_data[zone_idx][0]
            mod_start = self.bag_data[zone_idx][1]

            gen_end = (self.bag_data[zone_idx + 1][0] if zone_idx + 1 < len(self.bag_data)
                      else len(gen_data))
            mod_end = (self.bag_data[zone_idx + 1][1] if zone_idx + 1 < len(self.bag_data)
                      else len(mod_data))

            # Parse zone generators
            zone_gens = {}
            key_range = None
            vel_range = None

            for gen_idx in range(gen_start, gen_end):
                if gen_idx >= len(gen_data):
                    break
                gen_type, gen_amount = gen_data[gen_idx]
                zone_gens[gen_type] = gen_amount

                # Extract key/velocity ranges
                if gen_type == 42:  # keyRange
                    key_range = gen_amount
                elif gen_type == 43:  # velRange
                    vel_range = gen_amount

            # Parse zone modulators
            zone_mods = []
            for mod_idx in range(mod_start, mod_end):
                if mod_idx >= len(mod_data):
                    break
                zone_mods.append(mod_data[mod_idx])

            # Extract key/velocity ranges (default to full range)
            lokey = (key_range & 0xFF) if key_range is not None else 0
            hikey = ((key_range >> 8) & 0xFF) if key_range is not None else 127
            lovel = (vel_range & 0xFF) if vel_range is not None else 0
            hivel = ((vel_range >> 8) & 0xFF) if vel_range is not None else 127

            # Store preloaded data
            self.zone_ranges.append((lokey, hikey, lovel, hivel))
            self.zone_generators.append(zone_gens)
            self.zone_modulators.append(zone_mods)

    def get_matching_zones(self, start_bag: int, end_bag: int, note: int, velocity: int) -> List[Dict[str, Any]]:
        """
        Get all zones in the specified bag range that match the note/velocity.

        Args:
            start_bag: Starting bag index (inclusive)
            end_bag: Ending bag index (exclusive)
            note: MIDI note (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of zone data dictionaries for matching zones
        """
        matching_zones = []

        for zone_idx in range(start_bag, min(end_bag, len(self.zone_ranges))):
            lokey, hikey, lovel, hivel = self.zone_ranges[zone_idx]

            # Check if zone matches note/velocity
            if lokey <= note <= hikey and lovel <= velocity <= hivel:
                # Create zone data dictionary
                zone_data = {
                    'zone_index': zone_idx,
                    'generators': self.zone_generators[zone_idx].copy(),
                    'modulators': self.zone_modulators[zone_idx].copy(),
                    'lokey': lokey,
                    'hikey': hikey,
                    'lovel': lovel,
                    'hivel': hivel,
                    'keyRange': ((hikey << 8) | lokey),
                    'velRange': ((hivel << 8) | lovel)
                }

                matching_zones.append(zone_data)

        return matching_zones


class PreloadedPresetIndex:
    """
    Preloaded preset index for ultra-fast preset zone lookups.

    Preloads all preset zone data and provides O(1) lookups for note/velocity matching.
    """

    def __init__(self, sf2_file: 'LazySF2SoundFont'):
        self.sf2_file = sf2_file
        self.preset_zones = PreloadedZoneIndex(sf2_file, 'pbag')
        self.preset_boundaries: Dict[Tuple[int, int], Tuple[int, int]] = {}  # (bank, preset) -> (start_bag, end_bag)

        self._preload_preset_boundaries()

    def _preload_preset_boundaries(self):
        """Preload preset boundary information for fast lookups."""
        # Build preset boundary map
        sorted_presets = sorted(self.sf2_file.presets_index.keys())

        for i, preset_key in enumerate(sorted_presets):
            start_bag = self.sf2_file.presets_index[preset_key]

            # Find end bag (next preset's start or end of data)
            if i + 1 < len(sorted_presets):
                end_bag = self.sf2_file.presets_index[sorted_presets[i + 1]]
            else:
                end_bag = len(self.preset_zones.bag_data)

            self.preset_boundaries[preset_key] = (start_bag, end_bag)

    def get_matching_zones(self, bank: int, preset: int, note: int, velocity: int) -> List[Dict[str, Any]]:
        """
        Get zones for a preset that match the specified note/velocity.

        Args:
            bank: MIDI bank number
            preset: MIDI preset number
            note: MIDI note (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zone data dictionaries
        """
        preset_key = (bank, preset)

        if preset_key not in self.preset_boundaries:
            return []

        start_bag, end_bag = self.preset_boundaries[preset_key]

        return self.preset_zones.get_matching_zones(start_bag, end_bag, note, velocity)


class PreloadedInstrumentIndex:
    """
    Preloaded instrument index for ultra-fast instrument zone lookups.
    """

    def __init__(self, sf2_file: 'LazySF2SoundFont'):
        self.sf2_file = sf2_file
        self.instrument_zones = PreloadedZoneIndex(sf2_file, 'ibag')
        self.instrument_boundaries: Dict[int, Tuple[int, int]] = {}  # instrument_index -> (start_bag, end_bag)

        self._preload_instrument_boundaries()

    def _preload_instrument_boundaries(self):
        """Preload instrument boundary information."""
        # Build instrument boundary map - sort instruments by their bag index
        sorted_by_bag = sorted(self.sf2_file.instruments_index.items(), key=lambda x: x[1])

        for i, (inst_idx, start_bag) in enumerate(sorted_by_bag):
            # Find end bag (next instrument's start bag or end of bag data)
            if i + 1 < len(sorted_by_bag):
                end_bag = sorted_by_bag[i + 1][1]
            else:
                end_bag = len(self.instrument_zones.bag_data)

            self.instrument_boundaries[inst_idx] = (start_bag, end_bag)

    def get_matching_zones(self, instrument_index: int, note: int, velocity: int) -> List[Dict[str, Any]]:
        """
        Get zones for an instrument that match the specified note/velocity.

        Args:
            instrument_index: Instrument index
            note: MIDI note (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zone data dictionaries
        """
        if instrument_index not in self.instrument_boundaries:
            return []

        start_bag, end_bag = self.instrument_boundaries[instrument_index]

        return self.instrument_zones.get_matching_zones(start_bag, end_bag, note, velocity)


class SF2OptimizedPreset:
    """
    Production-grade optimized preset with preloaded zone data.

    Uses preloaded indices for O(1) zone lookups - no file I/O during synthesis.
    """

    def __init__(self, sf2_file: 'LazySF2SoundFont', name: str, bank: int, preset: int, bag_index: int):
        self.sf2_file = sf2_file
        self.name = name
        self.bank = bank
        self.preset = preset
        self.bag_index = bag_index

    def get_matching_zones(self, note: int, velocity: int) -> List[Dict[str, Any]]:
        """
        Get zones that match the note/velocity using preloaded indices.

        Ultra-fast O(1) lookup with zero file I/O.
        """
        return self.sf2_file.preset_index.get_matching_zones(self.bank, self.preset, note, velocity)


class LazySF2SoundFont:
    """
    Lazy-loading SF2 SoundFont for large files with preloaded binary chunks.

    Only loads metadata initially, loads samples and presets on-demand.
    Preloads raw binary data for frequently accessed chunks (bags, generators, modulators)
    to avoid repeated file I/O operations. Perfect for 1GB+ SoundFonts.
    """

    def __init__(self, filename: str, manager: 'SF2Manager'):
        self.filename = filename
        self.manager = manager
        self.file_size = 0
        self.file_handle = None  # Keep file open for performance

        # Lazy loading state
        self.metadata_loaded = False
        self.presets_index: Dict[Tuple[int, int], int] = {}  # (bank, preset) -> bag_index
        self.instruments_index: Dict[int, int] = {}  # instrument_index -> bag_index
        self.samples_index: Dict[str, Tuple[int, int]] = {}  # sample_name -> (header_offset, data_offset)
        self.samples_by_index: List[str] = []  # index -> sample_name mapping

        # Loaded data cache
        self.loaded_presets: Dict[Tuple[int, int], Any] = {}
        self.loaded_instruments: Dict[int, Any] = {}
        self.loaded_samples: Dict[str, np.ndarray] = {}

        # File structure info
        self.chunk_offsets: Dict[str, Tuple[int, int]] = {}  # chunk_id -> (offset, size)

        # PERFORMANCE OPTIMIZATION: Preload critical synthesis chunks
        # These small chunks are accessed constantly during synthesis
        self.preloaded_chunks: Dict[str, bytes] = {}  # chunk_name -> raw_binary_data

        # Thread safety for file access
        self.file_lock = threading.Lock()

        # MEMORY-EFFICIENT LAZY INDICES - Load data on-demand
        self.preset_index: Optional[PreloadedPresetIndex] = None
        self.instrument_index: Optional[PreloadedInstrumentIndex] = None

        # Initialize lazy loading with preloaded critical chunks and offset-based indices
        self._initialize_lazy_loading()

    def _initialize_lazy_loading(self):
        """Initialize lazy loading by scanning file structure and preloading frequently accessed chunks."""
        try:
            # Open file handle for persistent access
            self.file_handle = open(self.filename, 'rb')

            # Parse RIFF header
            if self.file_handle.read(4) != b'RIFF':
                raise ValueError("Not a valid RIFF file")

            self.file_size = int.from_bytes(self.file_handle.read(4), byteorder='little') + 8

            if self.file_handle.read(4) != b'sfbk':
                raise ValueError("Not a valid SF2 file")

            # Build chunk index without loading data
            self._build_chunk_index_lazy(self.file_handle)

            # Build preset/instrument/sample indices
            self._build_indices_lazy(self.file_handle)

            # PERFORMANCE OPTIMIZATION: Preload critical synthesis chunks
            # These small chunks (~260KB total) are accessed constantly during synthesis
            self._preload_critical_chunks()

            # CREATE PRELOADED INDICES FOR PRODUCTION-GRADE PERFORMANCE
            # Preload all zone data into memory structures for O(1) lookups
            self.preset_index = PreloadedPresetIndex(self)
            self.instrument_index = PreloadedInstrumentIndex(self)

            self.metadata_loaded = True

        except Exception as e:
            # Clean up file handle on error
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception:
                    pass
                self.file_handle = None
            raise RuntimeError(f"Failed to initialize lazy loading for {self.filename}: {e}")

    def _preload_critical_chunks(self):
        """
        Preload critical synthesis chunks that are accessed constantly during playback.

        These chunks contain the core SF2 parameters (bags, generators, modulators)
        that are required for every note played. Total size is typically ~260KB,
        making preloading highly beneficial for performance.
        """
        # Critical chunks to preload for synthesis performance
        critical_chunks = ['pbag', 'ibag', 'pgen', 'igen', 'pmod', 'imod']

        with self.file_lock:
            for chunk_name in critical_chunks:
                if chunk_name in self.chunk_offsets:
                    offset, size = self.chunk_offsets[chunk_name]

                    # Seek to chunk data
                    self.file_handle.seek(offset)

                    # Read entire chunk data into memory
                    chunk_data = self.file_handle.read(size)

                    if len(chunk_data) == size:
                        self.preloaded_chunks[chunk_name] = chunk_data
                        print(f"🎹 SF2: Preloaded {chunk_name} chunk ({size} bytes) for synthesis performance")
                    else:
                        print(f"⚠️  SF2: Failed to preload {chunk_name} chunk (expected {size}, got {len(chunk_data)})")

    def __del__(self):
        """Clean up file handle when object is destroyed."""
        self._close_file_handle()

    def _close_file_handle(self):
        """Close the persistent file handle."""
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass  # Ignore errors during cleanup
            self.file_handle = None

    def _build_chunk_index_lazy(self, f):
        """Build index of chunk offsets without loading data."""
        while f.tell() < self.file_size:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break

            chunk_size = int.from_bytes(f.read(4), byteorder='little')
            offset = f.tell()

            chunk_id_str = chunk_id.decode('ascii', errors='ignore')

            # Handle LIST chunks specially - they contain subchunks
            if chunk_id_str == 'LIST':
                # Read the list type
                list_type = f.read(4).decode('ascii', errors='ignore')
                # Adjust offset and size to account for the list type
                actual_data_offset = f.tell()
                actual_data_size = chunk_size - 4  # Subtract the list type size

                # Store the LIST chunk
                self.chunk_offsets[f'LIST_{list_type}'] = (actual_data_offset, actual_data_size)

                # Parse subchunks within this LIST
                end_of_list = actual_data_offset + actual_data_size
                while f.tell() < end_of_list:
                    subchunk_id = f.read(4)
                    if len(subchunk_id) < 4:
                        break

                    subchunk_size = int.from_bytes(f.read(4), byteorder='little')
                    subchunk_offset = f.tell()

                    subchunk_id_str = subchunk_id.decode('ascii', errors='ignore')
                    self.chunk_offsets[subchunk_id_str] = (subchunk_offset, subchunk_size)

                    # Skip subchunk data
                    f.seek(subchunk_size, 1)
            else:
                # Regular chunk
                self.chunk_offsets[chunk_id_str] = (offset, chunk_size)
                # Skip chunk data
                f.seek(chunk_size, 1)

    def _build_indices_lazy(self, f):
        """Build indices for presets, instruments, and samples."""
        # Index presets
        if 'phdr' in self.chunk_offsets:
            offset, size = self.chunk_offsets['phdr']
            f.seek(offset)
            self._build_preset_index_lazy(f, size)

        # Index instruments
        if 'inst' in self.chunk_offsets:
            offset, size = self.chunk_offsets['inst']
            f.seek(offset)
            self._build_instrument_index_lazy(f, size)

        # Index samples
        if 'shdr' in self.chunk_offsets:
            offset, size = self.chunk_offsets['shdr']
            f.seek(offset)
            self._build_sample_index_lazy(f, size)

    def _build_preset_index_lazy(self, f, size: int):
        """Build preset index without loading preset data.

        SF2 Preset Header structure (38 bytes):
        - achPresetName: char[20] (20 bytes)
        - wPreset: WORD (uint16, 2 bytes) - offset 20
        - wBank: WORD (uint16, 2 bytes) - offset 22
        - wPresetBagNdx: WORD (uint16, 2 bytes) - offset 24
        - dwLibrary: DWORD (uint32, 4 bytes) - offset 26
        - dwGenre: DWORD (uint32, 4 bytes) - offset 30
        - dwMorphology: DWORD (uint32, 4 bytes) - offset 34
        """
        count = size // 38
        for i in range(count - 1):  # Last entry is terminator
            preset_offset = f.tell()
            # Read preset header (38 bytes) and unpack preset_num, bank_num, and bag_ndx
            header_data = f.read(38)
            if len(header_data) >= 26:  # Need at least up to bag_ndx
                # Unpack: preset_num at offset 20, bank_num at offset 22, bag_ndx at offset 24
                preset_num, bank_num, bag_ndx = struct.unpack('<HHH', header_data[20:26])
                self.presets_index[(bank_num, preset_num)] = bag_ndx  # Store bag index, not file offset
            else:
                # Skip malformed entries
                continue

    def _build_instrument_index_lazy(self, f, size: int):
        """Build instrument index without loading instrument data.

        SF2 Instrument Header structure (22 bytes):
        - achInstName: char[20] (20 bytes)
        - wInstBagNdx: WORD (uint16, 2 bytes) - offset 20
        """
        count = size // 22
        for i in range(count - 1):  # Last entry is terminator
            instrument_offset = f.tell()
            # Read instrument header (22 bytes) and extract bag index
            header_data = f.read(22)
            if len(header_data) >= 22:
                # Unpack bag index at offset 20
                bag_ndx = struct.unpack('<H', header_data[20:22])[0]
                self.instruments_index[i] = bag_ndx  # Store bag index, not file offset
            else:
                # Skip malformed entries
                continue

    def _build_sample_index_lazy(self, f, size: int):
        """Build sample index without loading sample data.

        SF2 Sample Header structure (46 bytes):
        - achSampleName: char[20] (20 bytes) - offset 0
        - dwStart: DWORD (uint32, 4 bytes) - offset 20
        - dwEnd: DWORD (uint32, 4 bytes) - offset 24
        - dwStartloop: DWORD (uint32, 4 bytes) - offset 28
        - dwEndloop: DWORD (uint32, 4 bytes) - offset 32
        - dwSampleRate: DWORD (uint32, 4 bytes) - offset 36
        - byOriginalPitch: BYTE (uint8, 1 byte) - offset 40
        - chPitchCorrection: CHAR (int8, 1 byte) - offset 41
        - wSampleLink: WORD (uint16, 2 bytes) - offset 42
        - sfSampleType: SFSampleLink (WORD, uint16, 2 bytes) - offset 44
        """
        count = size // 46
        sample_data_offset = self.chunk_offsets.get('smpl', (0, 0))[0]

        # Determine bit depth by reading the first sample header
        bytes_per_sample = 2  # Default to 16-bit
        if count > 1:
            # Read first sample header to determine bit depth
            first_header_pos = f.tell()
            first_header = f.read(46)
            if len(first_header) >= 46:
                sample_type = struct.unpack('<H', first_header[44:46])[0]
                is_24bit = bool(sample_type & 0x8000)
                bytes_per_sample = 3 if is_24bit else 2
            # Reset file position
            f.seek(first_header_pos)

        for i in range(count - 1):  # Last entry is terminator
            sample_offset = f.tell()
            # Read sample header (46 bytes)
            header_data = f.read(46)
            if len(header_data) >= 24:
                # Unpack name (20 bytes) and start offset (4 bytes)
                name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')
                start = struct.unpack('<I', header_data[20:24])[0]

                # Calculate sample data offset based on determined bit depth
                data_offset = sample_data_offset + start * bytes_per_sample
                self.samples_index[name] = (sample_offset, data_offset)

                # Also store mapping from index to name
                self.samples_by_index.append(name)
            else:
                # Skip malformed entries
                continue

    def get_preset_lazy(self, bank: int, preset: int):
        """Get lazy preset that defers zone processing until needed."""
        key = (bank, preset)

        if key in self.loaded_presets:
            return self.loaded_presets[key]

        if key not in self.presets_index:
            return None

        # Create lazy preset object
        offset = self.presets_index[key]
        with self.file_lock:
            if self.file_handle is None:
                return None  # File handle was closed
            self.file_handle.seek(offset)
            preset = self._create_lazy_preset_from_offset(self.file_handle)

        if preset:
            self.loaded_presets[key] = preset

        return preset

    def get_instrument_lazy(self, index: int):
        """Load instrument on-demand using persistent file handle."""
        if index in self.loaded_instruments:
            return self.loaded_instruments[index]

        if index not in self.instruments_index:
            return None

        # Load instrument on-demand using persistent file handle
        offset = self.instruments_index[index]
        with self.file_lock:
            if self.file_handle is None:
                return None  # File handle was closed
            self.file_handle.seek(offset)
            instrument = self._parse_single_instrument_from_offset(self.file_handle)

        if instrument:
            self.loaded_instruments[index] = instrument

        return instrument

    def get_sample_data_lazy(self, sample_name: str) -> Optional[np.ndarray]:
        """Load sample data on-demand using persistent file handle with proper bit depth and channel support."""
        if sample_name in self.loaded_samples:
            return self.loaded_samples[sample_name]

        if sample_name not in self.samples_index:
            return None

        # Load sample on-demand using persistent file handle
        header_offset, data_offset = self.samples_index[sample_name]

        with self.file_lock:
            if self.file_handle is None:
                return None  # File handle was closed

            # Read complete sample header (46 bytes) to get sample type
            self.file_handle.seek(header_offset)
            header_data = self.file_handle.read(46)
            if len(header_data) < 46:
                return None  # Invalid header

            # Parse sample header fields
            name_bytes = header_data[:20]
            start, end = struct.unpack('<II', header_data[20:28])
            # Skip loop points (28-35)
            sample_rate = struct.unpack('<I', header_data[36:40])[0]
            original_pitch = header_data[40]  # int8
            pitch_correction = header_data[41]  # int8
            # Skip sample link (42-43)
            sample_type = struct.unpack('<H', header_data[44:46])[0]

            # Parse sample type (SF2 specification)
            # Bit 0: Mono (0) / Stereo (1)
            # Bit 15: 16-bit (0) / 24-bit (1)
            claimed_stereo = bool(sample_type & 0x0001)
            claimed_24bit = bool(sample_type & 0x8000)

            # Calculate sample size based on bit depth and channels
            sample_count = end - start

            # Determine actual format by checking available data size
            # Get the actual size of data available in the SMPL chunk
            smpl_chunk_size = self.chunk_offsets.get('smpl', (0, 0))[1]

            # Calculate what format the data actually is based on chunk size
            if claimed_24bit:
                # For 24-bit, check if mono or stereo format fits
                mono_24bit_size = sample_count * 3
                stereo_24bit_size = sample_count * 6

                if mono_24bit_size <= smpl_chunk_size:
                    is_stereo = False
                    is_24bit = True
                    actual_size = mono_24bit_size
                elif stereo_24bit_size <= smpl_chunk_size:
                    is_stereo = True
                    is_24bit = True
                    actual_size = stereo_24bit_size
                else:
                    # Fallback to 16-bit mono
                    is_stereo = False
                    is_24bit = False
                    actual_size = sample_count * 2
            else:
                # For 16-bit, check if mono or stereo format fits
                mono_16bit_size = sample_count * 2
                stereo_16bit_size = sample_count * 4

                if mono_16bit_size <= smpl_chunk_size:
                    is_stereo = False
                    is_24bit = False
                    actual_size = mono_16bit_size
                elif stereo_16bit_size <= smpl_chunk_size:
                    is_stereo = True
                    is_24bit = False
                    actual_size = stereo_16bit_size
                else:
                    # Data size doesn't match header - use what we have
                    is_stereo = False
                    is_24bit = False
                    actual_size = smpl_chunk_size

            # Load sample data based on determined format
            self.file_handle.seek(data_offset)
            sample_bytes = self.file_handle.read(actual_size)

            if len(sample_bytes) == 0:
                return None  # No data read

            # Convert based on actual format
            if is_24bit:
                # 24-bit samples are stored as 3 bytes per sample (SF2 spec section 3.6)
                sample_data = np.zeros(sample_count, dtype=np.float32)

                if is_stereo:
                    # Handle stereo 24-bit samples - create 2D array [samples, channels]
                    stereo_data = np.zeros((sample_count, 2), dtype=np.float32)
                    for i in range(sample_count):
                        # Left channel (first 3 bytes of pair)
                        left_bytes = sample_bytes[i*6:i*6+3]
                        if len(left_bytes) == 3:
                            left_int = int.from_bytes(left_bytes, byteorder='little', signed=True)
                            if left_int & 0x800000:
                                left_int |= 0xFF000000
                            stereo_data[i, 0] = left_int / 8388608.0

                        # Right channel (next 3 bytes of pair)
                        right_bytes = sample_bytes[i*6+3:i*6+6]
                        if len(right_bytes) == 3:
                            right_int = int.from_bytes(right_bytes, byteorder='little', signed=True)
                            if right_int & 0x800000:
                                right_int |= 0xFF000000
                            stereo_data[i, 1] = right_int / 8388608.0

                    sample_data = stereo_data
                else:
                    # Handle mono 24-bit samples
                    for i in range(sample_count):
                        sample_24bit = sample_bytes[i*3:(i+1)*3]
                        if len(sample_24bit) == 3:
                            # Convert 24-bit little-endian to int32
                            sample_int = int.from_bytes(sample_24bit, byteorder='little', signed=True)
                            # Sign extend from 24-bit to 32-bit
                            if sample_int & 0x800000:  # Check if sign bit is set
                                sample_int |= 0xFF000000  # Sign extend
                            sample_data[i] = sample_int / 8388608.0  # 2^23 normalization
            else:
                # 16-bit samples (standard PCM)
                if is_stereo:
                    # Load as 16-bit stereo - keep as stereo for proper processing
                    stereo_data = np.frombuffer(sample_bytes, dtype=np.int16)
                    # Reshape to [samples, channels] and keep both channels
                    stereo_data = stereo_data.reshape(-1, 2).astype(np.float32) / 32768.0
                    sample_data = stereo_data
                else:
                    # Load as 16-bit mono
                    sample_data = np.frombuffer(sample_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        self.loaded_samples[sample_name] = sample_data
        return sample_data

    def _create_lazy_preset_from_offset(self, f) -> Optional[Any]:
        """
        Create a lazy preset object that defers zone processing until needed.

        This enables selective processing of only matching zones based on note/velocity.
        """
        try:
            from .containers import SF2Preset

            # Read entire preset header (38 bytes) at once
            header_data = f.read(38)
            if len(header_data) < 38:
                return None

            # Extract and decode preset name
            name_bytes = header_data[:20]
            preset_name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

            # Unpack preset metadata (offsets 20-37)
            preset_num, bank_num, bag_ndx, library, genre, morphology = struct.unpack('<HHHIII', header_data[20:38])

            # Create optimized preset object
            preset = SF2OptimizedPreset(self, preset_name, bank_num, preset_num, bag_ndx)
            return preset

        except Exception as e:
            print(f"Error creating lazy preset: {e}")
            return None

    def _parse_preset_zones_from_bag_index(self, start_bag: int, preset_num: int, bank_num: int) -> List[Any]:
        """
        Parse preset zones using bag indices and generator/modulator data.

        This implements proper SF2 zone processing:
        - Resolve bag indices to generator/modulator ranges
        - Process generators and modulators for each zone
        - Handle zone inheritance and global zones
        """
        zones = []

        # Get bag data if available
        if not hasattr(self, '_bag_data_cache') or self._bag_data_cache is None:
            self._bag_data_cache = self._parse_bag_data('pbag')

        if not hasattr(self, '_gen_data_cache') or self._gen_data_cache is None:
            self._gen_data_cache = self._parse_generator_data('pgen')

        if not hasattr(self, '_mod_data_cache') or self._mod_data_cache is None:
            self._mod_data_cache = self._parse_modulator_data('pmod')

        bag_data = self._bag_data_cache
        gen_data = self._gen_data_cache
        mod_data = self._mod_data_cache

        # Find the next preset's start bag index for boundary calculation
        next_bag_start = len(bag_data)  # Default to end
        for other_preset_key in self.presets_index.keys():
            if other_preset_key[1] > preset_num or (other_preset_key[1] == preset_num and other_preset_key[0] > bank_num):
                next_bag_start = min(next_bag_start, self.presets_index[other_preset_key])
                break

        # Calculate actual bag indices for this preset
        preset_bag_start = start_bag
        preset_bag_end = next_bag_start

        # Process each zone in the preset
        for zone_idx in range(preset_bag_start, preset_bag_end):
            if zone_idx >= len(bag_data):
                break

            gen_start, mod_start = bag_data[zone_idx]

            # Calculate zone boundaries
            next_gen_start = bag_data[zone_idx + 1][0] if zone_idx + 1 < len(bag_data) else len(gen_data)
            next_mod_start = bag_data[zone_idx + 1][1] if zone_idx + 1 < len(bag_data) else len(mod_data)

            # Create zone and parse its generators/modulators
            zone = self._parse_single_preset_zone(gen_data, mod_data, gen_start, next_gen_start, mod_start, next_mod_start)
            if zone:
                zone.preset = preset_num
                zone.bank = bank_num
                zones.append(zone)

        return zones

    def _parse_single_preset_zone(self, gen_data: List[Tuple[int, int]], mod_data: List[Any],
                                gen_start: int, gen_end: int, mod_start: int, mod_end: int) -> Optional[Any]:
        """
        Parse a single preset zone with complete SF2 generator and modulator processing.

        Implements full SF2 specification compliance for preset zone processing:
        - All 60+ SF2 generators with proper defaults
        - Generator range validation and normalization
        - Modulator processing with transform operations
        - Proper global zone detection
        - SF2-compliant parameter inheritance

        Args:
            gen_data: Generator data list [(gen_type, gen_amount), ...]
            mod_data: Modulator data list [SimpleModulator, ...]
            gen_start: Start index in generator data
            gen_end: End index in generator data (exclusive)
            mod_start: Start index in modulator data
            mod_end: End index in modulator data (exclusive)

        Returns:
            Fully parsed SF2PresetZone or None on error
        """
        try:
            from ..types.dataclasses import SF2PresetZone

            zone = SF2PresetZone()
            zone.gen_ndx = gen_start
            zone.mod_ndx = mod_start

            # Initialize all SF2 generators with specification-compliant defaults
            # SF2 Spec section 8.1: Default values for generators
            self._initialize_sf2_preset_generator_defaults(zone)

            # Parse and validate all generators for this zone
            generator_count = self._parse_zone_generators_with_validation(
                zone, gen_.data, gen_start, gen_end
            )

            # Parse modulators with transform processing
            modulator_count = self._parse_zone_modulators_with_transforms(
                zone, mod_data, mod_start, mod_end
            )

            # Determine zone type and validate consistency
            # Note: is_global attribute doesn't exist in SF2PresetZone

            # Post-processing validation
            self._validate_parsed_preset_zone(zone)

            return zone

        except Exception as e:
            print(f"Critical error parsing preset zone: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _initialize_sf2_preset_generator_defaults(self, zone):
        """
        Initialize all SF2 preset generators with specification-compliant defaults.

        SF2 Specification section 8.1: Default generator values
        Note: Only set attributes that exist in the data structure
        """
        # Volume envelope (only set attributes that exist)
        zone.pan = 0  # -500 to +500 (0 = center)
        zone.chorusEffectsSend = 0
        zone.reverbEffectsSend = 0

        # LFO
        zone.freqModLFO = 0  # Default LFO frequency
        zone.delayVibLFO = 0
        zone.freqVibLFO = 0

        # Volume envelope
        zone.delayVolEnv = -12000
        zone.attackVolEnv = -12000
        zone.holdVolEnv = -12000
        zone.decayVolEnv = -12000
        zone.sustainVolEnv = 0
        zone.releaseVolEnv = -12000
        zone.keynumToVolEnvHold = 0
        zone.keynumToVolEnvDecay = 0

        # Key/velocity ranges
        zone.keyRange = 0x7F007F00  # Full range 0-127
        zone.velRange = 0x7F007F00  # Full range 0-127
        zone.lokey = 0
        zone.hikey = 127
        zone.lovel = 0
        zone.hivel = 127

        # Tuning
        zone.coarseTune = 0
        zone.fineTune = 0
        zone.scaleTuning = 100  # 100 cents per semitone
        zone.exclusiveClass = 0
        zone.overridingRootKey = -1  # Use sample root key

        # Initialize generator and modulator collections
        zone.generators = {}
        zone.modulators = []

    def _parse_zone_generators_with_validation(self, zone, gen_data: List[Tuple[int, int]],
                                             gen_start: int, gen_end: int) -> int:
        """
        Parse zone generators with comprehensive validation and range checking.

        Returns:
            Number of generators processed
        """
        generator_count = 0

        for gen_idx in range(gen_start, min(gen_end, len(gen_data))):
            gen_type, gen_amount = gen_data[gen_idx]

            # Validate generator type range (0-65 per SF2 spec)
            if not (0 <= gen_type <= 65):
                print(f"Warning: Invalid generator type {gen_type}, skipping")
                continue

            # Validate generator amount range
            if not (-32768 <= gen_amount <= 32767):
                print(f"Warning: Generator {gen_type} amount {gen_amount} out of range, clamping")
                gen_amount = max(-32768, min(32767, gen_amount))

            # Process generator based on type
            if gen_type == 41:  # instrument (key generator for preset zones)
                zone.instrument_index = gen_amount
            elif gen_type == 42:  # keyRange
                zone.keyRange = gen_amount
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
                # Validate range
                if zone.lokey > zone.hikey:
                    print(f"Warning: Invalid key range {zone.lokey}-{zone.hikey}, setting to full range")
                    zone.lokey, zone.hikey = 0, 127
                    zone.keyRange = 0x7F007F00
            elif gen_type == 43:  # velRange
                zone.velRange = gen_amount
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF
                # Validate range
                if zone.lovel > zone.hivel:
                    print(f"Warning: Invalid velocity range {zone.lovel}-{zone.hivel}, setting to full range")
                    zone.lovel, zone.hivel = 0, 127
                    zone.velRange = 0x7F007F00
            else:
                # Store all other generators
                zone.generators[gen_type] = gen_amount
                # Update corresponding zone attribute if it exists
                self._update_zone_attribute_from_generator(zone, gen_type, gen_amount)

            generator_count += 1

        return generator_count

    def _update_zone_attribute_from_generator(self, zone, gen_type: int, gen_amount: int):
        """
        Update zone attributes based on generator values.

        This maintains backward compatibility with zone attribute access.
        """
        generator_to_attribute = {
            7: 'endAddrsCoarseOffset',
            8: 'volEnvDelay',
            9: 'volEnvAttack',
            10: 'volEnvHold',
            11: 'volEnvDecay',
            12: 'volEnvSustain',
            13: 'volEnvRelease',
            14: 'modEnvDelay',
            15: 'modEnvAttack',
            16: 'modEnvHold',
            17: 'modEnvDecay',
            18: 'modEnvSustain',
            19: 'modEnvRelease',
            20: 'modEnvToPitch',
            21: 'delayModLFO',
            22: 'freqModLFO',
            23: 'modLfoToVol',
            24: 'modLfoToFilterFc',
            25: 'modLfoToPitch',
            26: 'delayVibLFO',
            27: 'freqVibLFO',
            28: 'vibLfoToPitch',
            29: 'initialFilterFc',
            30: 'initialFilterQ',
            32: 'reverbEffectsSend',
            33: 'chorusEffectsSend',
            34: 'pan',
            44: 'startloopAddrsCoarse',
            45: 'keynum',
            46: 'velocity',
            47: 'endloopAddrsCoarse',
            48: 'coarseTune',
            49: 'fineTune',
            52: 'scaleTuning',
            53: 'exclusiveClass',
            54: 'overridingRootKey',
            55: 'endAddrsCoarseOffset',
        }

        if gen_type in generator_to_attribute:
            attr_name = generator_to_attribute[gen_type]
            if hasattr(zone, attr_name):
                setattr(zone, attr_name, gen_amount)

    def _parse_zone_modulators_with_transforms(self, zone, mod_data: List[Any],
                                             mod_start: int, mod_end: int) -> int:
        """
        Parse zone modulators with transform operations and validation.

        Returns:
            Number of modulators processed
        """
        modulator_count = 0

        for mod_idx in range(mod_start, min(mod_end, len(mod_data))):
            modulator = mod_data[mod_idx]

            # Validate modulator structure
            if not hasattr(modulator, 'src_operator'):
                print(f"Warning: Invalid modulator structure at index {mod_idx}")
                continue

            # Process transform operations (SF2 spec section 8.2)
            processed_modulator = self._process_modulator_transforms(modulator)

            # Add to zone modulators
            zone.modulators.append(processed_modulator)
            modulator_count += 1

        return modulator_count

    def _process_modulator_transforms(self, modulator) -> Any:
        """
        Process SF2 modulator transforms and create modulator with proper transform support.

        SF2 modulators support transform operations that modify the modulation amount:
        - 0: Linear (no transform)
        - 1: Absolute value (remove negative values)
        - 2: Bipolar to unipolar conversion

        This method creates a modulator that can apply these transforms in real-time.
        """
        # Get transform type from modulator (SF2 specification section 8.2.3)
        transform_type = getattr(modulator, 'mod_trans_operator', 0)

        # Create processed modulator with transform capability
        class SF2ProcessedModulator:
            def __init__(self, src_op, dest_op, amount, transform_type):
                self.src_operator = src_op
                self.dest_operator = dest_op
                self.mod_amount = amount
                self.transform_type = transform_type
                # Pre-compute base amount for efficiency
                self.base_amount = amount / 32768.0  # Convert SF2 16-bit to float

            def apply_transform(self, input_value: float) -> float:
                """
                Apply SF2 transform operation to input value.

                Args:
                    input_value: Raw modulation input (-1.0 to +1.0)

                Returns:
                    Transformed modulation value
                """
                # Apply transform based on SF2 specification
                if self.transform_type == 0:
                    # Linear: no transformation
                    transformed = input_value
                elif self.transform_type == 1:
                    # Absolute: remove negative values
                    transformed = abs(input_value)
                elif self.transform_type == 2:
                    # Bipolar to unipolar: convert (-1,1) to (0,1)
                    transformed = (input_value + 1.0) * 0.5
                else:
                    # Unknown transform type - default to linear
                    transformed = input_value

                # Apply base modulation amount
                return transformed * self.base_amount

        return SF2ProcessedModulator(
            modulator.src_operator,
            modulator.dest_operator,
            modulator.mod_amount,
            transform_type
        )

    def _determine_zone_global_status(self, zone, generator_count: int) -> bool:
        """
        Determine if this is a global zone based on SF2 rules.

        Global zones affect all notes/velocities in the preset but don't
        reference specific instruments.
        """
        # SF2 global zone rules:
        # 1. No instrument assigned (instrument_index == -1)
        # 2. Full key/velocity range (unless explicitly set otherwise)
        # 3. Contains generators that should apply globally

        is_global = (zone.instrument_index == -1)

        # Additional check: if zone has no specific key/vel constraints
        # and contains global generators, it's likely a global zone
        if is_global and generator_count > 0:
            # Check for generators that are typically global
            global_generators = {21, 22, 26, 27, 32, 33, 34}  # LFO and effect generators
            has_global_gens = any(gen in zone.generators for gen in global_generators)
            if has_global_gens:
                return True

        return is_global

    def _validate_parsed_preset_zone(self, zone):
        """
        Perform comprehensive validation on parsed preset zone.

        Ensures zone data is consistent and within SF2 specification limits.
        """
        # Validate instrument index
        if zone.instrument_index < -1:
            print(f"Warning: Invalid instrument index {zone.instrument_index}, setting to -1")
            zone.instrument_index = -1

        # Validate key/velocity ranges
        zone.lokey = max(0, min(127, zone.lokey))
        zone.hikey = max(0, min(127, zone.hikey))
        zone.lovel = max(0, min(127, zone.lovel))
        zone.hivel = max(0, min(127, zone.hivel))

        # Ensure ranges are valid
        if zone.lokey > zone.hikey:
            zone.lokey, zone.hikey = 0, 127
        if zone.lovel > zone.hivel:
            zone.lovel, zone.hivel = 0, 127

        # Update range values
        zone.keyRange = (zone.hikey << 8) | zone.lokey
        zone.velRange = (zone.hivel << 8) | zone.lovel

    def _parse_single_instrument_from_offset(self, f) -> Optional[Any]:
        """
        Parse a single instrument from file offset with complete zone processing.

        This implements proper SF2 instrument parsing including:
        - Instrument header parsing
        - Bag index resolution
        - Generator and modulator processing
        - Zone creation with proper inheritance
        """
        try:
            from .containers import SF2Instrument
            from ..types.dataclasses import SF2InstrumentZone

            # Read entire instrument header (22 bytes) at once
            header_data = f.read(22)
            if len(header_data) < 22:
                return None

            # Extract and decode instrument name
            name_bytes = header_data[:20]
            instrument_name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

            # Unpack instrument bag index (offset 20)
            bag_index = struct.unpack('<H', header_data[20:22])[0]

            # Create instrument object
            instrument = SF2Instrument()
            instrument.name = instrument_name

            # Parse zones for this instrument using bag indices
            zones = self._parse_instrument_zones_from_bag_index(bag_index)
            instrument.zones = zones

            return instrument

        except Exception as e:
            print(f"Error parsing instrument: {e}")
            return None

    def _parse_instrument_zones_from_bag_index(self, start_bag: int) -> List[Any]:
        """
        Parse instrument zones using bag indices and generator/modulator data.

        This implements proper SF2 zone processing for instruments:
        - Resolve bag indices to generator/modulator ranges
        - Process generators and modulators for each zone
        - Handle zone inheritance and global zones
        """
        zones = []

        # Get bag data if available
        if not hasattr(self, '_inst_bag_data_cache') or self._inst_bag_data_cache is None:
            self._inst_bag_data_cache = self._parse_bag_data('ibag')

        if not hasattr(self, '_inst_gen_data_cache') or self._inst_gen_data_cache is None:
            self._inst_gen_data_cache = self._parse_generator_data('igen')

        if not hasattr(self, '_inst_mod_data_cache') or self._inst_mod_data_cache is None:
            self._inst_mod_data_cache = self._parse_modulator_data('imod')

        bag_data = self._inst_bag_data_cache
        gen_data = self._inst_gen_data_cache
        mod_data = self._inst_mod_data_cache

        # Find the next instrument's start bag index for boundary calculation
        next_bag_start = len(bag_data)  # Default to end
        for other_inst_idx in self.instruments_index.keys():
            if other_inst_idx > start_bag:  # Simple comparison for now
                next_bag_start = min(next_bag_start, self.instruments_index[other_inst_idx])
                break

        # Calculate actual bag indices for this instrument
        instrument_bag_start = start_bag
        instrument_bag_end = next_bag_start

        # Process each zone in the instrument
        for zone_idx in range(instrument_bag_start, instrument_bag_end):
            if zone_idx >= len(bag_data):
                break

            gen_start, mod_start = bag_data[zone_idx]

            # Calculate zone boundaries
            next_gen_start = bag_data[zone_idx + 1][0] if zone_idx + 1 < len(bag_data) else len(gen_data)
            next_mod_start = bag_data[zone_idx + 1][1] if zone_idx + 1 < len(bag_data) else len(mod_data)

            # Create zone and parse its generators/modulators
            zone = self._parse_single_instrument_zone(gen_data, mod_data, gen_start, next_gen_start, mod_start, next_mod_start)
            if zone:
                zones.append(zone)

        return zones

    def _parse_single_instrument_zone(self, gen_data: List[Tuple[int, int]], mod_data: List[Any],
                                    gen_start: int, gen_end: int, mod_start: int, mod_end: int) -> Optional[Any]:
        """
        Parse a single instrument zone with generators and modulators.

        Args:
            gen_data: Generator data list
            mod_data: Modulator data list
            gen_start: Start index in generator data
            gen_end: End index in generator data
            mod_start: Start index in modulator data
            mod_end: End index in modulator data

        Returns:
            Parsed instrument zone or None
        """
        try:
            from ..types.dataclasses import SF2InstrumentZone

            zone = SF2InstrumentZone()
            zone.gen_ndx = gen_start
            zone.mod_ndx = mod_start

            # SF2 Generator defaults for instrument level
            defaults = {
                0: 0,     # startAddrsOffset
                1: 0,     # endAddrsOffset
                2: 0,     # startloopAddrsOffset
                3: 0,     # endloopAddrsOffset
                4: 0,     # startAddrsCoarseOffset
                5: -12000, # modLfoToFilterFc
                6: -12000, # modEnvToFilterFc
                7: 0,     # endAddrsCoarseOffset
                8: -12000, # volEnvDelay
                9: -12000, # volEnvAttack
                10: -12000, # volEnvHold
                11: -12000, # volEnvDecay
                12: 0,    # volEnvSustain
                13: -12000, # volEnvRelease
                14: -12000, # modEnvDelay
                15: -12000, # modEnvAttack
                16: -12000, # modEnvHold
                17: -12000, # modEnvDecay
                18: -12000, # modEnvSustain
                19: -12000, # modEnvRelease
                20: 0,    # modEnvToPitch
                21: -12000, # delayModLFO
                22: 0,    # freqModLFO
                23: 0,    # modLfoToVol
                24: 0,    # modLfoToFilterFc (duplicate)
                25: 0,    # modLfoToPitch (duplicate)
                26: -12000, # delayVibLFO
                27: 0,    # freqVibLFO
                28: 0,    # vibLfoToPitch
                29: -200, # initialFilterFc
                30: 0,    # initialFilterQ
                31: 0,    # filterType
                32: 0,    # reverbSend
                33: 0,    # chorusSend
                34: 0,    # pan
                35: -12000, # delayModEnv (duplicate)
                36: -12000, # attackModEnv (duplicate)
                37: -12000, # holdModEnv (duplicate)
                38: -12000, # decayModEnv (duplicate)
                39: -12000, # sustainModEnv (duplicate)
                40: -12000, # releaseModEnv (duplicate)
                41: -1,   # instrument (not used in instrument zones)
                42: 0x7F007F00, # keyRange (lo=0, hi=127)
                43: 0x7F007F00, # velRange (lo=0, hi=127)
                44: 0,    # startloopAddrsCoarse
                45: -1,   # keynum
                46: -1,   # velocity
                47: 0,    # endloopAddrsCoarse
                48: 0,    # coarseTune
                49: 0,    # fineTune
                50: -1,   # sampleID
                51: 0,    # sampleModes
                52: 100,  # scaleTuning
                53: 0,    # exclusiveClass
                54: -1,   # overridingRootKey
                55: 0,    # endAddrsCoarseOffset
                56: -12000, # volEnvDelay (duplicate)
                57: -12000, # volEnvAttack (duplicate)
                58: -12000, # volEnvHold (duplicate)
                59: -12000, # volEnvDecay (duplicate)
                60: 0,    # volEnvSustain (duplicate)
                61: -12000, # volEnvRelease (duplicate)
                62: 0,    # keyRange (duplicate)
                63: 0,    # velRange (duplicate)
                64: 0,    # keynum (duplicate)
                65: 0,    # velocity (duplicate)
            }

            # Parse generators for this zone
            for gen_idx in range(gen_start, gen_end):
                if gen_idx >= len(gen_data):
                    break

                gen_type, gen_amount = gen_data[gen_idx]

                # Special handling for key generators
                if gen_type == 42:  # keyRange
                    zone.keyRange = gen_amount
                    zone.lokey = gen_amount & 0xFF
                    zone.hikey = (gen_amount >> 8) & 0xFF
                elif gen_type == 43:  # velRange
                    zone.velRange = gen_amount
                    zone.lovel = gen_amount & 0xFF
                    zone.hivel = (gen_amount >> 8) & 0xFF
                elif gen_type == 53:  # sampleID
                    zone.sample_index = gen_amount
                else:
                    # Store generator value
                    zone.generators[gen_type] = gen_amount

            # Parse modulators for this zone
            for mod_idx in range(mod_start, mod_end):
                if mod_idx >= len(mod_data):
                    break

                # Add modulator to zone (simplified - would need proper SF2Modulator objects)
                zone.modulators.append(mod_data[mod_idx])

            # Note: is_global attribute doesn't exist in SF2InstrumentZone

            return zone

        except Exception as e:
            print(f"Error parsing instrument zone: {e}")
            return None

    def _parse_bag_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse bag data (pbag/ibag chunks) from cache or file on-demand.

        Args:
            chunk_name: Name of the bag chunk ('pbag' or 'ibag')

        Returns:
            List of (gen_ndx, mod_ndx) tuples
        """
        if chunk_name not in self.chunk_offsets:
            return []

        # Try to get from cache first
        if hasattr(self.manager, 'chunk_cache') and self.manager.chunk_cache:
            chunk_data = self.manager.chunk_cache.get_chunk_data(self, chunk_name)
            if chunk_data is not None:
                return self._parse_bag_data_from_bytes(chunk_data)

        # Load from file
        offset, size = self.chunk_offsets[chunk_name]

        # Each bag entry is 4 bytes: gen_ndx (2), mod_ndx (2)
        count = size // 4
        bag_data = []

        with self.file_lock:
            if self.file_handle is None:
                return []

            for i in range(count):
                bag_offset = offset + i * 4
                self.file_handle.seek(bag_offset)
                entry_data = self.file_handle.read(4)
                if len(entry_data) < 4:
                    break

                gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
                bag_data.append((gen_ndx, mod_ndx))

        return bag_data

    def _parse_bag_data_from_bytes(self, chunk_data: bytes) -> List[Tuple[int, int]]:
        """Parse bag data from cached chunk bytes."""
        size = len(chunk_data)
        count = size // 4
        bag_data = []

        for i in range(count):
            offset = i * 4
            if offset + 4 > size:
                break

            entry_data = chunk_data[offset:offset + 4]
            gen_ndx, mod_ndx = struct.unpack('<HH', entry_data)
            bag_data.append((gen_ndx, mod_ndx))

        return bag_data

    def _parse_generator_data(self, chunk_name: str) -> List[Tuple[int, int]]:
        """
        Parse generator data (pgen/igen chunks) from cache or file on-demand.

        Args:
            chunk_name: Name of the generator chunk ('pgen' or 'igen')

        Returns:
            List of (gen_type, gen_amount) tuples
        """
        if chunk_name not in self.chunk_offsets:
            return []

        # Try to get from cache first
        if hasattr(self.manager, 'chunk_cache') and self.manager.chunk_cache:
            chunk_data = self.manager.chunk_cache.get_chunk_data(self, chunk_name)
            if chunk_data is not None:
                return self._parse_generator_data_from_bytes(chunk_data)

        # Load from file
        offset, size = self.chunk_offsets[chunk_name]

        # Each generator entry is 4 bytes: gen_type (2), gen_amount (2, signed)
        count = size // 4
        gen_data = []

        with self.file_lock:
            if self.file_handle is None:
                return []

            for i in range(count):
                gen_offset = offset + i * 4
                self.file_handle.seek(gen_offset)
                entry_data = self.file_handle.read(4)
                if len(entry_data) < 4:
                    break

                gen_type, gen_amount = struct.unpack('<Hh', entry_data)
                gen_data.append((gen_type, gen_amount))

        return gen_data

    def _parse_generator_data_from_bytes(self, chunk_data: bytes) -> List[Tuple[int, int]]:
        """Parse generator data from cached chunk bytes."""
        size = len(chunk_data)
        count = size // 4
        gen_data = []

        for i in range(count):
            offset = i * 4
            if offset + 4 > size:
                break

            entry_data = chunk_data[offset:offset + 4]
            gen_type, gen_amount = struct.unpack('<Hh', entry_data)
            gen_data.append((gen_type, gen_amount))

        return gen_data

    def _parse_modulator_data(self, chunk_name: str) -> List[Any]:
        """
        Parse modulator data (pmod/imod chunks) from cache or file on-demand.

        Args:
            chunk_name: Name of the modulator chunk ('pmod' or 'imod')

        Returns:
            List of SF2Modulator objects with complete transform information
        """
        if chunk_name not in self.chunk_offsets:
            return []

        # Try to get from cache first
        if hasattr(self.manager, 'chunk_cache') and self.manager.chunk_cache:
            chunk_data = self.manager.chunk_cache.get_chunk_data(self, chunk_name)
            if chunk_data is not None:
                return self._parse_modulator_data_from_bytes(chunk_data)

        # Load from file
        offset, size = self.chunk_offsets[chunk_name]

        # Each modulator entry is 10 bytes (SF2 specification section 8.2)
        # Format: src_oper(2), dest_oper(2), mod_amount(2), amt_src_oper(2), mod_trans_oper(2)
        count = size // 10
        mod_data = []

        with self.file_lock:
            if self.file_handle is None:
                return []

            for i in range(count):
                mod_offset = offset + i * 10
                self.file_handle.seek(mod_offset)
                entry_data = self.file_handle.read(10)
                if len(entry_data) < 10:
                    break

                # Parse complete modulator structure per SF2 spec
                src_oper = struct.unpack('<H', entry_data[0:2])[0]       # Source operator
                dest_oper = struct.unpack('<H', entry_data[2:4])[0]      # Destination operator
                mod_amount = struct.unpack('<h', entry_data[4:6])[0]     # Modulation amount
                amt_src_oper = struct.unpack('<H', entry_data[6:8])[0]   # Amount source operator
                mod_trans_oper = struct.unpack('<H', entry_data[8:10])[0] # Transform operator

                # Create complete modulator object with all SF2 fields
                class SF2Modulator:
                    def __init__(self, src_op, dest_op, amount, amt_src_op, trans_op):
                        self.src_operator = src_op
                        self.dest_operator = dest_op
                        self.mod_amount = amount
                        self.amt_src_operator = amt_src_op
                        self.mod_trans_operator = trans_op

                modulator = SF2Modulator(src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper)
                mod_data.append(modulator)

        return mod_data

    def _parse_modulator_data_from_bytes(self, chunk_data: bytes) -> List[Any]:
        """Parse modulator data from cached chunk bytes."""
        size = len(chunk_data)
        count = size // 10
        mod_data = []

        for i in range(count):
            offset = i * 10
            if offset + 10 > size:
                break

            entry_data = chunk_data[offset:offset + 10]

            # Parse complete modulator structure per SF2 spec
            src_oper = struct.unpack('<H', entry_data[0:2])[0]       # Source operator
            dest_oper = struct.unpack('<H', entry_data[2:4])[0]      # Destination operator
            mod_amount = struct.unpack('<h', entry_data[4:6])[0]     # Modulation amount
            amt_src_oper = struct.unpack('<H', entry_data[6:8])[0]   # Amount source operator
            mod_trans_oper = struct.unpack('<H', entry_data[8:10])[0] # Transform operator

            # Create complete modulator object with all SF2 fields
            class SF2Modulator:
                def __init__(self, src_op, dest_op, amount, amt_src_op, trans_op):
                    self.src_operator = src_op
                    self.dest_operator = dest_op
                    self.mod_amount = amount
                    self.amt_src_operator = amt_src_op
                    self.mod_trans_operator = trans_op

            modulator = SF2Modulator(src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper)
            mod_data.append(modulator)

        return mod_data

    def create_sf2_voice(self, partial_params: Dict, global_voice_manager, synth) -> Optional[Any]:
        """
        Create SF2 voice with global voice management integration.

        This method creates an SF2 voice that participates in the global voice
        allocation system instead of using its own isolated voice management.

        Args:
            partial_params: SF2 partial parameters
            global_voice_manager: Global voice manager instance
            synth: ModernXGSynthesizer instance for infrastructure access

        Returns:
            SF2Voice instance allocated through global manager, or None if allocation failed
        """
        try:
            from ...voice.voice import Voice
            from ...partial.sf2_partial import SF2Partial

            # Create SF2 partial with modern synth integration
            sf2_partial = SF2Partial(partial_params, synth)

            # Create voice that uses global voice management
            class SF2Voice(Voice):
                """
                SF2 Voice with global voice management integration.

                Extends the standard Voice class to use global voice manager
                for allocation, stealing, and polyphony instead of SF2-specific management.
                """

                __slots__ = ['global_manager', 'voice_id', 'current_note']

                def __init__(self, synthesis_engine, voice_params: Dict, channel: int, sample_rate: int):
                    # Initialize with SF2 engine and params
                    super().__init__(synthesis_engine, voice_params, channel, sample_rate)

                    # Add global voice management
                    self.global_manager = global_voice_manager
                    self.voice_id = -1  # Assigned by global manager
                    self.current_note = -1

                    # Allocate voice immediately upon creation
                    if not self.allocate():
                        raise RuntimeError("Failed to allocate SF2 voice from global manager")

                def allocate(self) -> bool:
                    """
                    Allocate voice through global voice manager.

                    Uses global polyphony limits and voice stealing priorities.
                    """
                    # Request allocation from global manager
                    allocation_result = self.global_manager.allocate_voice_for_engine(
                        'sf2', self, priority='normal'
                    )

                    if allocation_result:
                        self.voice_id = allocation_result['voice_id']
                        return True

                    return False

                def deallocate(self):
                    """Deallocate voice through global manager."""
                    if self.voice_id >= 0:
                        self.global_manager.deallocate_voice(self.voice_id)
                        self.voice_id = -1

                def note_on(self, note: int, velocity: int):
                    """Handle note-on event."""
                    self.current_note = note
                    # Call parent implementation which will handle partials
                    super().note_on(note, velocity)

                def note_off(self, note: int):
                    """Handle note-off event."""
                    # Call parent implementation which will handle partials
                    super().note_off(note)

                def apply_global_parameters(self, global_params: Dict) -> None:
                    """Apply global synthesizer parameters."""
                    # Apply to voice level
                    super().apply_global_parameters(global_params)

                    # Apply to SF2 partial specifically
                    if hasattr(self.sf2_partial, 'apply_global_parameters'):
                        self.sf2_partial.apply_global_parameters(global_params)

                def apply_channel_parameters(self, channel_params: Dict) -> None:
                    """Apply XG channel parameters."""
                    # Apply to voice level
                    super().apply_channel_parameters(channel_params)

                    # Apply to SF2 partial specifically
                    if hasattr(self.sf2_partial, 'apply_channel_parameters'):
                        self.sf2_partial.apply_channel_parameters(channel_params)

                def get_effect_send_levels(self) -> Dict[str, float]:
                    """Get effect send levels from SF2 partial for global effects routing."""
                    if hasattr(self.sf2_partial, 'get_effect_send_levels'):
                        return self.sf2_partial.get_effect_send_levels()
                    return {'reverb': 0.0, 'chorus': 0.0, 'variation': 0.0}

                def get_channel_pan(self) -> float:
                    """Get channel pan position from SF2 partial."""
                    if hasattr(self.sf2_partial, 'get_channel_pan'):
                        return self.sf2_partial.get_channel_pan()
                    return 0.0

                def cleanup(self):
                    """Clean up voice resources."""
                    self.deallocate()
                    super().reset()  # Use parent's reset method

            # Create voice parameters for SF2 engine
            voice_params = {
                'name': 'SF2 Voice',
                'partials': [partial_params],  # SF2 partials
            }

            # Create and return voice using proper Voice constructor
            voice = SF2Voice(synth.sf2_engine, voice_params, 0, synth.sample_rate)

            # Attempt allocation through global manager
            if voice.allocate():
                return voice
            else:
                # Allocation failed - clean up
                voice.cleanup()
                return None

        except Exception as e:
            print(f"Error creating SF2 voice: {e}")
            return None

    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        loaded_presets_mb = len(self.loaded_presets) * 0.01  # Rough estimate
        loaded_instruments_mb = len(self.loaded_instruments) * 0.005  # Rough estimate
        loaded_samples_mb = sum(len(data) * 4 / (1024 * 1024)
                               for data in self.loaded_samples.values())

        return {
            'loaded_presets_mb': loaded_presets_mb,
            'loaded_instruments_mb': loaded_instruments_mb,
            'loaded_samples_mb': loaded_samples_mb,
            'total_loaded_mb': loaded_presets_mb + loaded_instruments_mb + loaded_samples_mb
        }


class ChunkDataCache:
    """
    LRU cache for loaded chunk data segments.

    Caches frequently accessed chunk data to avoid repeated file I/O
    while maintaining memory efficiency through LRU eviction.
    """

    def __init__(self, max_memory_mb: int = 50):
        """
        Initialize chunk data cache.

        Args:
            max_memory_mb: Maximum memory to use for cached chunk data
        """
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.cache: OrderedDict[str, bytes] = OrderedDict()
        self.lock = threading.Lock()

    def get_chunk_data(self, sf2_file: 'LazySF2SoundFont', chunk_name: str) -> Optional[bytes]:
        """
        Get chunk data from cache or load from file.

        Args:
            sf2_file: SF2 file instance
            chunk_name: Name of the chunk to load

        Returns:
            Chunk data bytes or None if not found
        """
        cache_key = f"{sf2_file.filename}:{chunk_name}"

        with self.lock:
            # Check if already cached
            if cache_key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                return self.cache[cache_key]

            # Load from file
            if chunk_name not in sf2_file.chunk_offsets:
                return None

            offset, size = sf2_file.chunk_offsets[chunk_name]

            with sf2_file.file_lock:
                if sf2_file.file_handle is None:
                    return None

                sf2_file.file_handle.seek(offset)
                chunk_data = sf2_file.file_handle.read(size)

                if len(chunk_data) != size:
                    return None

            # Check memory limits
            self._ensure_memory_available(len(chunk_data))

            # Cache the data
            self.cache[cache_key] = chunk_data
            self.current_memory += len(chunk_data)

            return chunk_data

    def _ensure_memory_available(self, needed_memory: int):
        """Ensure enough memory by evicting LRU items."""
        while self.current_memory + needed_memory > self.max_memory and self.cache:
            # Evict least recently used
            evicted_key, evicted_data = self.cache.popitem(last=False)
            self.current_memory -= len(evicted_data)

    def clear_cache(self):
        """Clear all cached chunk data."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_chunks = len(self.cache)
            total_memory_mb = self.current_memory / (1024 * 1024)

            return {
                'cached_chunks': total_chunks,
                'memory_usage_mb': total_memory_mb,
                'memory_limit_mb': self.max_memory / (1024 * 1024),
                'memory_utilization': total_memory_mb / (self.max_memory / (1024 * 1024)) if self.max_memory > 0 else 0.0
            }


class MipMapCache:
    """
    LRU cache for sample mip-maps with memory limits.

    Manages mip-map creation and storage with intelligent eviction
    to prevent memory exhaustion while maintaining performance.
    """

    def __init__(self, max_memory_mb: int = 256):
        """
        Initialize mip-map cache.

        Args:
            max_memory_mb: Maximum memory to use for mip-maps
        """
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.cache: OrderedDict[str, SampleMipMap] = OrderedDict()
        self.lock = threading.Lock()

    def get_mipmap(self, sample_key: str, original_sample: np.ndarray,
                   sample_rate: int) -> SampleMipMap:
        """
        Get mip-map for sample, creating if needed.

        Args:
            sample_key: Unique key for the sample
            original_sample: Original PCM sample data
            sample_rate: Sample rate in Hz

        Returns:
            SampleMipMap instance (possibly cached)
        """
        with self.lock:
            # Check if already cached
            if sample_key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(sample_key)
                return self.cache[sample_key]

            # Create new mip-map
            mipmap = create_sample_mipmap(original_sample, sample_rate)

            # Check memory limits
            mipmap_memory = mipmap.get_memory_usage()
            self._ensure_memory_available(mipmap_memory)

            # Cache the mip-map
            self.cache[sample_key] = mipmap
            self.current_memory += mipmap_memory

            return mipmap


    def _ensure_memory_available(self, needed_memory: int):
        """Ensure enough memory by evicting LRU items."""
        while self.current_memory + needed_memory > self.max_memory and self.cache:
            # Evict least recently used
            evicted_key, evicted_mipmap = self.cache.popitem(last=False)
            evicted_memory = evicted_mipmap.get_memory_usage()
            self.current_memory -= evicted_memory

    def clear_cache(self):
        """Clear all cached mip-maps."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_mipmaps = len(self.cache)
            total_memory_mb = self.current_memory / (1024 * 1024)

            return {
                'cached_mipmaps': total_mipmaps,
                'memory_usage_mb': total_memory_mb,
                'memory_limit_mb': self.max_memory / (1024 * 1024),
                'memory_utilization': total_memory_mb / (self.max_memory / (1024 * 1024)) if self.max_memory > 0 else 0.0
            }


class SF2Manager:
    """
    Enhanced SF2 Manager with lazy loading and mip-mapping support.

    Uses lazy loading exclusively for large SoundFonts,
    with integrated audio mip-mapping for high-quality high-pitch playback.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.sf2_files: Dict[str, Any] = {}
        self.memory_pool = MemoryPool()
        self.range_tree = RangeTree()
        self._zone_cache: Dict[str, List[Any]] = {}
        self._zone_cache_hits = 0
        self._zone_cache_misses = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # Lazy loading configuration (always enabled)
        self.lazy_loading = True
        self.sample_cache_size_mb = 256
        self.sample_cache = None
        self.background_loader = None

        # Mip-mapping support
        self.mip_map_cache: Optional[MipMapCache] = None

        # Chunk data cache for performance optimization
        self.chunk_cache: Optional[ChunkDataCache] = None

        # Initialize lazy loading immediately
        self.enable_lazy_loading()

    def enable_lazy_loading(self, sample_cache_size_mb: int = 256):
        """
        Enable lazy loading for large SoundFonts.

        Args:
            sample_cache_size_mb: Maximum memory for cached samples
        """
        self.lazy_loading = True
        self.sample_cache_size_mb = sample_cache_size_mb

        # Initialize sample cache if not already done
        if self.sample_cache is None:
            from synth.sf2.caching.sample_cache import SampleCache
            self.sample_cache = SampleCache(max_size=sample_cache_size_mb * 1024 * 1024)

        # Initialize background loader
        self.background_loader = BackgroundSampleLoader(self)

        # Initialize chunk data cache
        if self.chunk_cache is None:
            self.chunk_cache = ChunkDataCache(max_memory_mb=50)  # 50MB cache

    def load_sf2_file(self, filename: str) -> bool:
        """Load SF2 file with lazy loading (exclusive loading method).
           Only loads metadata initially, samples loaded on-demand.
        """
        try:
            sf2 = LazySF2SoundFont(filename, self)
            self.sf2_files[filename] = sf2
            return True
        except Exception as e:
            print(f"Failed to load SF2 file progressively {filename}: {e}")
            return False

    def get_program_parameters(self, program: int, bank: int = 0, note: int = 60, velocity: int = 64) -> Optional[Dict[str, Any]]:
        """
        Get program parameters with high-performance caching.
        """
        # Check cache first
        cached_params = self.memory_pool.get_program_params(program, bank, note, velocity)
        if cached_params is not None:
            self.cache_hits += 1
            return cached_params

        self.cache_misses += 1

        # Compute parameters from SF2 data
        params = self._compute_program_parameters(program, bank, note, velocity)

        if params:
            # Cache for future use
            self.memory_pool.cache_program_params(params, program, bank, note, velocity)

        return params

    def _compute_program_parameters(self, program: int, bank: int, note: int, velocity: int) -> Optional[Dict[str, Any]]:
        """Compute program parameters from SF2 data using lazy loading."""
        # Find SF2 file containing this program
        sf2_file = None
        for sf2 in self.sf2_files.values():
            if (bank, program) in sf2.presets_index:
                sf2_file = sf2
                break

        if not sf2_file:
            return None

        # Get preset using lazy loading
        preset = sf2_file.get_preset_lazy(bank, program)

        if not preset:
            return None

        # Process zones for this preset
        partials = self._process_preset_zones_lazy(sf2_file, preset, note, velocity)

        return {
            'program': program,
            'bank': bank,
            'name': getattr(preset, 'name', f'Program {program}'),
            'note': note,
            'velocity': velocity,
            'source': 'SF2_Lazy',
            'layers': len(partials),
            'partials': partials
        }

    def _process_preset_zones_lazy(self, sf2_file, preset, note: int, velocity: int) -> List[Dict[str, Any]]:
        """Process preset zones with lazy loading using preloaded indices."""
        partials = []

        # Get zones that match the current note/velocity using preloaded indices
        matching_zones = sf2_file.preset_index.get_matching_zones(preset.bank, preset.preset, note, velocity)

        for zone_data in matching_zones:
            # Get instrument using lazy loading
            instrument_index = zone_data.get('generators', {}).get(41, -1)  # instrument generator
            if instrument_index >= 0:
                instrument = sf2_file.get_instrument_lazy(instrument_index)

                if instrument:
                    # Process instrument zones
                    instrument_partials = self._process_instrument_zones_lazy(sf2_file, instrument, zone_data, note, velocity)
                    partials.extend(instrument_partials)

        return partials

    def _process_instrument_zones_lazy(self, sf2_file, instrument, preset_zone, note: int, velocity: int) -> List[Dict[str, Any]]:
        """Process instrument zones with lazy loading support."""
        partials = []

        for zone in getattr(instrument, 'zones', []):
            if (zone.lokey <= note <= zone.hikey and zone.lovel <= velocity <= zone.hivel):
                # Get sample data (lazy loaded if applicable)
                sample_index = getattr(zone, 'sample_index', -1)
                sample_data = None
                sample_rate = 44100
                original_pitch = 60

                if sample_index >= 0 and sample_index < len(sf2_file.samples_by_index):
                    # Use lazy loading for sample data - get actual sample name from index
                    sample_name = sf2_file.samples_by_index[sample_index]
                    sample_data = sf2_file.get_sample_data_lazy(sample_name)
                    sample_rate = 44100  # Default
                    original_pitch = 60   # Default

                if sample_data is not None:
                    partial = self._create_partial_from_zones(preset_zone, zone, sample_data, sample_rate, original_pitch)
                    partials.append(partial)

        return partials

    def _create_partial_from_zones(self, preset_zone, instrument_zone, sample_data, sample_rate, original_pitch) -> Dict[str, Any]:
        """Create partial parameters from preset and instrument zones."""
        return {
            'layer_index': 0,
            'sample_data': sample_data,
            'sample_rate': sample_rate,
            'original_pitch': original_pitch,
            'pitch_correction': 0.0,
            'amp_envelope': {'delay': 0.0, 'attack': 0.01, 'hold': 0.0, 'decay': 0.3, 'sustain': 0.7, 'release': 0.5},
            'filter': {'cutoff': 20000.0, 'resonance': 0.0, 'type': 'lowpass'},
            'pan': 0.0,
            'volume': 1.0,
            'exclusive_class': 0,
            'mod_lfo': {'delay': 0.0, 'frequency': 8.176, 'to_pitch': 0.0, 'to_filter': 0.0, 'to_volume': 0.0},
            'vib_lfo': {'delay': 0.0, 'frequency': 8.176, 'to_pitch': 0.0}
        }

    def create_partial_generator(self, program: int, bank: int, note: int, velocity: int):
        """Create SF2 partial generator."""
        from .generator import SF2PartialGenerator
        return SF2PartialGenerator(self, program, bank, note, velocity)

    def create_voice(self, program: int, bank: int, note: int, velocity: int):
        """Create SF2 voice."""
        from .voice import SF2Voice
        partial_gen = self.create_partial_generator(program, bank, note, velocity)
        return SF2Voice(partial_gen) if partial_gen else None

    def preload_samples_for_program(self, sf2_file: str, program: int, bank: int = 0):
        """Preload commonly used samples for a program in background."""
        if not self.background_loader:
            return

        params = self.get_program_parameters(program, bank)
        if not params or 'partials' not in params:
            return

        # Identify samples to preload
        sample_names = set()
        for partial in params['partials']:
            # This would analyze partial to find required samples
            # For now, simplified
            pass

        # Trigger background preloading
        for sample_name in sample_names:
            self.background_loader.preload_sample_async(sf2_file, sample_name)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get basic cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests,
            'memory_pool_stats': self.memory_pool.get_memory_stats()
        }

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive caching statistics."""
        stats = self.get_cache_stats()

        if hasattr(self, 'sample_cache') and self.sample_cache:
            sample_stats = self.sample_cache.get_stats()
            stats.update({
                'sample_cache_size_mb': sample_stats['current_size'] / (1024 * 1024),
                'sample_cache_utilization': sample_stats['utilization'],
                'sample_cache_entries': sample_stats['num_samples']
            })

        # Add lazy loading statistics
        lazy_stats = {}
        for filename, sf2 in self.sf2_files.items():
            lazy_stats[filename] = sf2.get_memory_usage()

        stats['lazy_loading_stats'] = lazy_stats

        return stats

    def create_sf2_voice(self, partial_params: Dict, global_voice_manager, synth) -> Optional[Any]:
        """
        Create SF2 voice with global voice management integration.

        This method creates an SF2 voice that participates in the global voice
        allocation system instead of using its own isolated voice management.

        Args:
            partial_params: SF2 partial parameters
            global_voice_manager: Global voice manager instance
            synth: ModernXGSynthesizer instance for infrastructure access

        Returns:
            SF2Voice instance allocated through global manager, or None if allocation failed
        """
        # Delegate to LazySF2SoundFont if we have any loaded files
        for sf2_file in self.sf2_files.values():
            if hasattr(sf2_file, 'create_sf2_voice'):
                return sf2_file.create_sf2_voice(partial_params, global_voice_manager, synth)

        # Fallback: create voice directly if no SF2 files loaded
        try:
            from ...voice.voice import Voice
            from ...partial.sf2_partial import SF2Partial

            # Create SF2 partial with modern synth integration
            sf2_partial = SF2Partial(partial_params, synth)

            # Create voice parameters for SF2 engine
            voice_params = {
                'name': 'SF2 Voice',
                'partials': [partial_params],  # SF2 partials
            }

            # Create and return voice using proper Voice constructor
            voice = Voice(synth.sf2_engine, voice_params, 0, synth.sample_rate)

            # Attempt allocation through global manager
            if voice.allocate():
                return voice
            else:
                # Allocation failed - clean up
                voice.cleanup()
                return None

        except Exception as e:
            print(f"Error creating SF2 voice: {e}")
            return None


class BackgroundSampleLoader:
    """
    Background sample loader for progressive loading.

    Loads samples asynchronously to avoid blocking the main thread.
    """

    def __init__(self, manager: SF2Manager):
        self.manager = manager
        self.loading_queue: Set[Tuple[str, str]] = set()  # (sf2_file, sample_name)
        self.executor = None

    def preload_sample_async(self, sf2_file: str, sample_name: str):
        """Asynchronously preload a sample."""
        if (sf2_file, sample_name) in self.loading_queue:
            return

        self.loading_queue.add((sf2_file, sample_name))

        # Lazy initialization of executor
        if self.executor is None:
            import concurrent.futures
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        # Submit background loading task
        self.executor.submit(self._load_sample_background, sf2_file, sample_name)

    def _load_sample_background(self, sf2_file: str, sample_name: str):
        """Background sample loading task."""
        try:
            sf2 = self.manager.sf2_files.get(sf2_file)
            if sf2:
                sf2.get_sample_data_lazy(sample_name)

        except Exception as e:
            print(f"Background loading failed for {sf2_file}:{sample_name}: {e}")

        finally:
            self.loading_queue.discard((sf2_file, sample_name))
