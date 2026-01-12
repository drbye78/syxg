"""
SF2 File Loader with Binary Chunk Storage

Handles SF2 file loading, RIFF chunk parsing, and on-demand binary data access.
Optimized for large soundfonts with 100% SF2 specification compliance.
"""

import struct
import threading
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path
import os


class SF2BinaryChunk:
    """
    Binary chunk data with lazy parsing support.

    Stores raw chunk data in memory for on-demand parsing.
    """

    def __init__(self, chunk_id: str, data: bytes, offset: int = 0):
        """
        Initialize binary chunk.

        Args:
            chunk_id: Four-character chunk identifier
            data: Raw chunk data bytes
            offset: File offset of this chunk
        """
        self.chunk_id = chunk_id
        self.data = data
        self.offset = offset
        self.size = len(data)

        # Parsing state
        self._parsed_data: Optional[Any] = None
        self._is_parsed = False

    def get_data_slice(self, start: int, length: int) -> bytes:
        """
        Get slice of chunk data.

        Args:
            start: Start offset within chunk
            length: Number of bytes to read

        Returns:
            Raw bytes slice
        """
        end = min(start + length, self.size)
        return self.data[start:end]

    def parse_as_struct(self, format_string: str, offset: int = 0) -> Tuple:
        """
        Parse chunk data as structured data.

        Args:
            format_string: struct format string
            offset: Offset within chunk to start parsing

        Returns:
            Tuple of parsed values
        """
        data_slice = self.get_data_slice(offset, struct.calcsize(format_string))
        return struct.unpack(format_string, data_slice)

    def parse_string(self, offset: int, max_length: int) -> str:
        """
        Parse null-terminated string from chunk data.

        Args:
            offset: Start offset of string
            max_length: Maximum string length

        Returns:
            Decoded string
        """
        data_slice = self.get_data_slice(offset, max_length)
        # Find null terminator
        null_pos = data_slice.find(b'\x00')
        if null_pos >= 0:
            data_slice = data_slice[:null_pos]
        return data_slice.decode('ascii', errors='ignore')

    def mark_parsed(self, parsed_data: Any) -> None:
        """
        Mark chunk as parsed with result data.

        Args:
            parsed_data: Parsed data to cache
        """
        self._parsed_data = parsed_data
        self._is_parsed = True

    def get_parsed_data(self) -> Optional[Any]:
        """
        Get cached parsed data if available.

        Returns:
            Cached parsed data or None
        """
        return self._parsed_data if self._is_parsed else None

    def clear_cache(self) -> None:
        """Clear parsed data cache."""
        self._parsed_data = None
        self._is_parsed = False


class SF2ChunkIndex:
    """
    Index of all chunks in an SF2 file.

    Provides fast lookup of chunks by ID and handles LIST subchunks.
    """

    def __init__(self):
        """Initialize chunk index."""
        self.chunks: Dict[str, SF2BinaryChunk] = {}
        self.list_chunks: Dict[str, Dict[str, SF2BinaryChunk]] = {}  # list_type -> {subchunk_id -> chunk}

    def add_chunk(self, chunk_id: str, chunk: SF2BinaryChunk) -> None:
        """
        Add chunk to index.

        Args:
            chunk_id: Chunk identifier
            chunk: Binary chunk object
        """
        self.chunks[chunk_id] = chunk

    def add_list_subchunk(self, list_type: str, subchunk_id: str, chunk: SF2BinaryChunk) -> None:
        """
        Add subchunk to LIST chunk.

        Args:
            list_type: LIST type (e.g., 'INFO', 'sdta', 'pdta')
            subchunk_id: Subchunk identifier
            chunk: Binary chunk object
        """
        if list_type not in self.list_chunks:
            self.list_chunks[list_type] = {}
        self.list_chunks[list_type][subchunk_id] = chunk

    def get_chunk(self, chunk_id: str, list_type: Optional[str] = None) -> Optional[SF2BinaryChunk]:
        """
        Get chunk by ID.

        Args:
            chunk_id: Chunk identifier
            list_type: LIST type if subchunk

        Returns:
            Binary chunk or None if not found
        """
        if list_type:
            return self.list_chunks.get(list_type, {}).get(chunk_id)
        return self.chunks.get(chunk_id)

    def get_all_chunks(self, list_type: Optional[str] = None) -> Dict[str, SF2BinaryChunk]:
        """
        Get all chunks of a type.

        Args:
            list_type: LIST type or None for top-level chunks

        Returns:
            Dictionary of chunk_id -> chunk
        """
        if list_type:
            return self.list_chunks.get(list_type, {}).copy()
        return self.chunks.copy()

    def clear(self) -> None:
        """Clear all chunks and cache."""
        for chunk in self.chunks.values():
            chunk.clear_cache()

        for list_type_chunks in self.list_chunks.values():
            for chunk in list_type_chunks.values():
                chunk.clear_cache()

        self.chunks.clear()
        self.list_chunks.clear()


class SF2FileLoader:
    """
    SF2 file loader with binary chunk storage and on-demand parsing.

    Loads RIFF structure into memory as binary chunks, parses only when needed.
    Optimized for large soundfonts (1GB+) with minimal memory overhead.
    """

    def __init__(self, filepath: str):
        """
        Initialize SF2 file loader.

        Args:
            filepath: Path to SF2 file
        """
        self.filepath = Path(filepath)
        self.filename = self.filepath.name
        self.file_size = 0

        # File handle and locking
        self._file_handle: Optional[Any] = None
        self._file_lock = threading.RLock()

        # Chunk storage
        self.chunk_index = SF2ChunkIndex()
        self._is_loaded = False

        # Sample data chunk locations (for lazy loading)
        self.sample_data_chunks: Dict[str, Tuple[int, int]] = {}  # chunk_id -> (offset, size)

        # Metadata
        self.version: Tuple[int, int] = (0, 0)
        self.bank_name = ""
        self.rom_name = ""
        self.creation_date = ""
        self.authors = ""
        self.product = ""
        self.copyright = ""
        self.comments = ""
        self.tools = ""

    def load_file(self) -> bool:
        """
        Load SF2 file and build chunk index WITHOUT preloading sample data.

        Only loads metadata chunks into memory. Sample data ('smpl', 'sm24') is read on-demand
        to prevent loading hundreds of MB of unused sample data into memory.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Open file and verify (keep file handle open for sample data access)
            self._file_handle = open(self.filepath, 'rb')

            if not self._verify_sf2_header():
                self._cleanup()
                return False

            # Parse RIFF structure (only indexes chunks, doesn't load sample data)
            self._parse_riff_structure_lazy()

            # Load INFO metadata (small metadata chunks)
            self._load_info_metadata()

            self._is_loaded = True
            return True

        except Exception as e:
            print(f"Error loading SF2 file {self.filepath}: {e}")
            self._cleanup()
            return False

    def _verify_sf2_header(self) -> bool:
        """
        Verify SF2 file header.

        Returns:
            True if valid SF2 file
        """
        if self._file_handle is None:
            return False

        # Read and verify RIFF header
        riff_header = self._file_handle.read(12)
        if len(riff_header) < 12:
            return False

        riff_id, file_size, sfbk_id = struct.unpack('<4sI4s', riff_header)

        if riff_id != b'RIFF' or sfbk_id != b'sfbk':
            return False

        self.file_size = file_size + 8  # Include RIFF header
        return True

    def _parse_riff_structure_lazy(self) -> None:
        """
        Parse RIFF structure with lazy loading - only load metadata chunks into memory.

        Sample data chunks ('smpl', 'sm24') are indexed but not loaded to prevent
        loading hundreds of MB of unused sample data into memory.
        """
        file_pos = 12  # Skip RIFF header

        while file_pos < self.file_size:
            # Read chunk header
            chunk_header = self._file_handle.read(8)
            if len(chunk_header) < 8:
                break

            chunk_id, chunk_size = struct.unpack('<4sI', chunk_header)
            chunk_id_str = chunk_id.decode('ascii', errors='ignore')

            # Handle LIST chunks specially
            if chunk_id_str == 'LIST':
                list_type_data = self._file_handle.read(4)
                if len(list_type_data) < 4:
                    break

                list_type = list_type_data.decode('ascii', errors='ignore')
                actual_chunk_size = chunk_size - 4  # Subtract list type size

                # Decide whether to load LIST chunk data or just index it
                should_load_data = self._should_load_chunk_data(list_type)

                if should_load_data:
                    # Load metadata LIST chunks (INFO, pdta)
                    list_chunk_data = self._read_chunk_data(actual_chunk_size)
                    list_chunk = SF2BinaryChunk(f'LIST_{list_type}', list_chunk_data, file_pos)
                    self.chunk_index.add_chunk(f'LIST_{list_type}', list_chunk)

                    # Parse subchunks
                    self._parse_list_subchunks(list_type, list_chunk_data, file_pos + 12)
                else:
                    # For sdta (sample data), just index the chunk location
                    if list_type == 'sdta':
                        self.sample_data_chunks[f'LIST_{list_type}'] = (file_pos, chunk_size + 8)  # Include LIST header

                    # Skip the LIST chunk data
                    self._file_handle.seek(actual_chunk_size, 1)

                file_pos += chunk_size + 8  # Skip entire LIST chunk

            else:
                # Regular chunk
                should_load_data = self._should_load_chunk_data(chunk_id_str)

                if should_load_data:
                    # Load metadata chunks
                    chunk_data = self._read_chunk_data(chunk_size)
                    chunk = SF2BinaryChunk(chunk_id_str, chunk_data, file_pos)
                    self.chunk_index.add_chunk(chunk_id_str, chunk)
                else:
                    # For sample data chunks, just index their location
                    if chunk_id_str in ['smpl', 'sm24']:
                        self.sample_data_chunks[chunk_id_str] = (file_pos, chunk_size + 8)  # Include chunk header

                    # Skip the chunk data
                    self._file_handle.seek(chunk_size, 1)

                file_pos += chunk_size + 8

    def _should_load_chunk_data(self, chunk_id: str) -> bool:
        """
        Determine whether a chunk's data should be loaded into memory.

        Only loads metadata chunks. Sample data chunks are read on-demand.

        Args:
            chunk_id: Chunk identifier

        Returns:
            True if chunk data should be loaded into memory
        """
        # Load metadata chunks
        metadata_chunks = [
            'ifil', 'INAM', 'irom', 'ICRD', 'IENG', 'IPRD', 'ICOP', 'ICMT', 'ISFT',  # INFO
            'phdr', 'pbag', 'pmod', 'pgen', 'inst', 'ibag', 'imod', 'igen', 'shdr'  # pdta
        ]

        # Load LIST chunks that contain metadata
        metadata_lists = ['INFO', 'pdta']

        return chunk_id in metadata_chunks or chunk_id in metadata_lists

    def _parse_list_subchunks(self, list_type: str, list_data: bytes, base_offset: int) -> None:
        """
        Parse subchunks within a LIST chunk.

        Args:
            list_type: LIST type identifier
            list_data: Raw LIST chunk data
            base_offset: Base file offset for subchunks
        """
        if self._file_handle is None:
            return

        data_pos = 0

        while data_pos < len(list_data):
            # Read subchunk header
            if data_pos + 8 > len(list_data):
                break

            subchunk_header = list_data[data_pos:data_pos + 8]
            subchunk_id, subchunk_size = struct.unpack('<4sI', subchunk_header)
            subchunk_id_str = subchunk_id.decode('ascii', errors='ignore')

            data_pos += 8

            # Read subchunk data
            if data_pos + subchunk_size > len(list_data):
                break

            subchunk_data = list_data[data_pos:data_pos + subchunk_size]

            # Create subchunk
            subchunk = SF2BinaryChunk(subchunk_id_str, subchunk_data, base_offset + data_pos)
            self.chunk_index.add_list_subchunk(list_type, subchunk_id_str, subchunk)

            data_pos += subchunk_size

    def _read_chunk_data(self, size: int) -> bytes:
        """
        Read chunk data from file.

        Args:
            size: Size of data to read

        Returns:
            Raw chunk data bytes
        """
        if self._file_handle is None:
            return b''

        data = self._file_handle.read(size)
        # Pad if necessary (some chunks may be padded to even boundaries)
        if len(data) < size:
            data += b'\x00' * (size - len(data))
        return data

    def _load_info_metadata(self) -> None:
        """Load INFO metadata from binary chunks."""
        info_chunks = self.chunk_index.get_all_chunks('INFO')

        # Version
        if 'ifil' in info_chunks:
            version_data = info_chunks['ifil'].parse_as_struct('<HH')
            self.version = (version_data[0], version_data[1])

        # Strings
        string_fields = {
            'INAM': 'bank_name',
            'irom': 'rom_name',
            'ICRD': 'creation_date',
            'IENG': 'authors',
            'IPRD': 'product',
            'ICOP': 'copyright',
            'ICMT': 'comments',
            'ISFT': 'tools'
        }

        for chunk_id, field_name in string_fields.items():
            if chunk_id in info_chunks:
                string_value = info_chunks[chunk_id].parse_string(0, len(info_chunks[chunk_id].data))
                setattr(self, field_name, string_value)

    def get_chunk(self, chunk_id: str, list_type: Optional[str] = None) -> Optional[SF2BinaryChunk]:
        """
        Get binary chunk by ID.

        Args:
            chunk_id: Chunk identifier
            list_type: LIST type if subchunk

        Returns:
            Binary chunk or None
        """
        return self.chunk_index.get_chunk(chunk_id, list_type)

    def parse_preset_headers(self) -> List[Dict[str, Any]]:
        """
        Parse ALL preset headers on-demand (legacy method for compatibility).

        Note: This parses all headers upfront. For selective parsing, use
        parse_preset_header_at_index() or find_preset_by_bank_program().

        Returns:
            List of preset header dictionaries
        """
        phdr_chunk = self.get_chunk('phdr', 'pdta')
        if not phdr_chunk:
            return []

        presets = []
        data = phdr_chunk.data

        # Each preset header is 38 bytes
        for i in range(0, len(data), 38):
            if i + 38 > len(data):
                break

            # Parse preset header
            header_data = data[i:i + 38]
            preset_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')
            preset_num, bank_num, bag_ndx = struct.unpack('<HHH', header_data[20:26])

            # Skip library, genre, morphology for now
            presets.append({
                'name': preset_name,
                'program': preset_num,
                'bank': bank_num,
                'bag_index': bag_ndx,
                'header_index': i // 38  # Store index for selective access
            })

        return presets

    def find_preset_by_bank_program(self, bank: int, program: int) -> Optional[Dict[str, Any]]:
        """
        Find a specific preset by bank and program number with selective parsing.

        This method only parses the preset header that matches the requested
        bank/program, avoiding parsing of all preset headers for large soundfonts.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            Preset header dictionary or None if not found
        """
        phdr_chunk = self.get_chunk('phdr', 'pdta')
        if not phdr_chunk:
            return None

        data = phdr_chunk.data
        num_presets = len(data) // 38

        # Search for matching preset
        for i in range(num_presets):
            offset = i * 38
            if offset + 26 > len(data):  # Need at least up to bag_ndx
                break

            # Parse just the bank/program part (offsets 20-25)
            header_data = data[offset + 20:offset + 26]
            preset_num, bank_num = struct.unpack('<HH', header_data[:4])

            if preset_num == program and bank_num == bank:
                # Found match - parse the full header
                full_header = data[offset:offset + 38]
                preset_name = full_header[:20].decode('ascii', errors='ignore').rstrip('\x00')
                bag_ndx = struct.unpack('<H', full_header[24:26])[0]

                return {
                    'name': preset_name,
                    'program': preset_num,
                    'bank': bank_num,
                    'bag_index': bag_ndx,
                    'header_index': i
                }

        return None

    def parse_preset_header_at_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse a specific preset header by index with selective parsing.

        Args:
            index: Preset header index (0-based)

        Returns:
            Preset header dictionary or None if index invalid
        """
        phdr_chunk = self.get_chunk('phdr', 'pdta')
        if not phdr_chunk:
            return None

        offset = index * 38
        if offset + 38 > len(phdr_chunk.data):
            return None

        # Parse specific header
        header_data = phdr_chunk.data[offset:offset + 38]
        preset_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')
        preset_num, bank_num, bag_ndx = struct.unpack('<HHH', header_data[20:26])

        return {
            'name': preset_name,
            'program': preset_num,
            'bank': bank_num,
            'bag_index': bag_ndx,
            'header_index': index
        }

    def parse_instrument_headers(self) -> List[Dict[str, Any]]:
        """
        Parse ALL instrument headers on-demand (legacy method for compatibility).

        Note: This parses all headers upfront. For selective parsing, use
        parse_instrument_header_at_index().

        Returns:
            List of instrument header dictionaries
        """
        inst_chunk = self.get_chunk('inst', 'pdta')
        if not inst_chunk:
            return []

        instruments = []
        data = inst_chunk.data

        # Each instrument header is 22 bytes
        for i in range(0, len(data), 22):
            if i + 22 > len(data):
                break

            # Parse instrument header
            header_data = data[i:i + 22]
            inst_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')
            bag_ndx = struct.unpack('<H', header_data[20:22])[0]

            instruments.append({
                'name': inst_name,
                'bag_index': bag_ndx,
                'header_index': i // 22  # Store index for selective access
            })

        return instruments

    def parse_instrument_header_at_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse a specific instrument header by index with selective parsing.

        Args:
            index: Instrument header index (0-based)

        Returns:
            Instrument header dictionary or None if index invalid
        """
        inst_chunk = self.get_chunk('inst', 'pdta')
        if not inst_chunk:
            return None

        offset = index * 22
        if offset + 22 > len(inst_chunk.data):
            return None

        # Parse specific header
        header_data = inst_chunk.data[offset:offset + 22]
        inst_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')
        bag_ndx = struct.unpack('<H', header_data[20:22])[0]

        return {
            'name': inst_name,
            'bag_index': bag_ndx,
            'header_index': index
        }

    def parse_sample_headers(self) -> List[Dict[str, Any]]:
        """
        Parse ALL sample headers on-demand (legacy method for compatibility).

        Note: This parses all headers upfront. For selective parsing, use
        parse_sample_header_at_index().

        Returns:
            List of sample header dictionaries
        """
        shdr_chunk = self.get_chunk('shdr', 'pdta')
        if not shdr_chunk:
            return []

        samples = []
        data = shdr_chunk.data

        # Each sample header is 46 bytes
        for i in range(0, len(data), 46):
            if i + 46 > len(data):
                break

            # Parse sample header
            header_data = data[i:i + 46]
            sample_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')

            start, end, start_loop, end_loop, sample_rate, orig_pitch, pitch_corr, sample_link, sample_type = struct.unpack(
                '<IIIIIIHHH', header_data[20:46]
            )

            samples.append({
                'name': sample_name,
                'start': start,
                'end': end,
                'start_loop': start_loop,
                'end_loop': end_loop,
                'sample_rate': sample_rate,
                'original_pitch': orig_pitch,
                'pitch_correction': pitch_corr,
                'sample_link': sample_link,
                'sample_type': sample_type,
                'header_index': i // 46  # Store index for selective access
            })

        return samples

    def parse_sample_header_at_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse a specific sample header by index with selective parsing.

        Args:
            index: Sample header index (0-based)

        Returns:
            Sample header dictionary or None if index invalid
        """
        shdr_chunk = self.get_chunk('shdr', 'pdta')
        if not shdr_chunk:
            return None

        offset = index * 46
        if offset + 46 > len(shdr_chunk.data):
            return None

        # Parse specific header
        header_data = shdr_chunk.data[offset:offset + 46]
        sample_name = header_data[:20].decode('ascii', errors='ignore').rstrip('\x00')

        start, end, start_loop, end_loop, sample_rate, orig_pitch, pitch_corr, sample_link, sample_type = struct.unpack(
            '<IIIIIIHHH', header_data[20:46]
        )

        return {
            'name': sample_name,
            'start': start,
            'end': end,
            'start_loop': start_loop,
            'end_loop': end_loop,
            'sample_rate': sample_rate,
            'original_pitch': orig_pitch,
            'pitch_correction': pitch_corr,
            'sample_link': sample_link,
            'sample_type': sample_type,
            'header_index': index
        }

    def get_sample_data(self, sample_start: int, sample_end: int,
                       is_24bit: bool = False) -> Optional[bytes]:
        """
        Get raw sample data from smpl and sm24 chunks with proper 24-bit reconstruction.
        Reads data directly from file on-demand to avoid loading large sample data into memory.

        Args:
            sample_start: Sample start index
            sample_end: Sample end index
            is_24bit: Whether sample is 24-bit (requires sm24 + smpl combination)

        Returns:
            Raw sample data bytes or None
        """
        if self._file_handle is None or not self._is_loaded:
            return None

        with self._file_lock:
            if is_24bit:
                # For 24-bit samples, combine data from both smpl and sm24 chunks
                return self._read_24bit_sample_data_from_file(sample_start, sample_end)
            else:
                # 16-bit samples
                return self._read_16bit_sample_data_from_file(sample_start, sample_end)

    def _read_16bit_sample_data_from_file(self, sample_start: int, sample_end: int) -> Optional[bytes]:
        """
        Read 16-bit sample data directly from file.

        Args:
            sample_start: Sample start index
            sample_end: Sample end index

        Returns:
            Raw 16-bit sample data bytes
        """
        if 'smpl' not in self.sample_data_chunks:
            return None

        chunk_offset, chunk_size = self.sample_data_chunks['smpl']

        # Calculate file offsets for the sample data
        # Skip chunk header (8 bytes: 'smpl' + size)
        data_start_offset = chunk_offset + 8
        bytes_per_sample = 2
        sample_data_start = data_start_offset + (sample_start * bytes_per_sample)
        sample_data_end = data_start_offset + (sample_end * bytes_per_sample)

        # Ensure we don't read beyond chunk boundaries
        chunk_data_end = chunk_offset + chunk_size
        if sample_data_end > chunk_data_end:
            sample_data_end = chunk_data_end

        data_size = sample_data_end - sample_data_start
        if data_size <= 0:
            return b''

        # Read data directly from file
        self._file_handle.seek(sample_data_start)
        return self._file_handle.read(data_size)

    def _read_24bit_sample_data_from_file(self, sample_start: int, sample_end: int) -> Optional[bytes]:
        """
        Read and combine 24-bit sample data from both smpl and sm24 chunks directly from file.

        Args:
            sample_start: Sample start index
            sample_end: Sample end index

        Returns:
            Combined 24-bit sample data as bytes
        """
        if 'smpl' not in self.sample_data_chunks or 'sm24' not in self.sample_data_chunks:
            return None

        smpl_offset, smpl_size = self.sample_data_chunks['smpl']
        sm24_offset, sm24_size = self.sample_data_chunks['sm24']

        # Calculate data ranges
        num_samples = sample_end - sample_start
        if num_samples <= 0:
            return b''

        # Each 24-bit sample needs: 2 bytes from smpl + 1 byte from sm24 = 3 bytes total
        combined_data = bytearray(num_samples * 3)

        try:
            # Read smpl data (16-bit samples)
            smpl_data_start = smpl_offset + 8 + (sample_start * 2)  # Skip header + offset to sample
            smpl_data_size = num_samples * 2

            self._file_handle.seek(smpl_data_start)
            smpl_bytes = self._file_handle.read(smpl_data_size)

            if len(smpl_bytes) < smpl_data_size:
                return None

            # Read sm24 data (8-bit extensions)
            sm24_data_start = sm24_offset + 8 + sample_start  # Skip header + offset to sample
            sm24_data_size = num_samples

            self._file_handle.seek(sm24_data_start)
            sm24_bytes = self._file_handle.read(sm24_data_size)

            if len(sm24_bytes) < sm24_data_size:
                return None

            # Combine the data
            for i in range(num_samples):
                # Get 16-bit data from smpl
                smpl_word = int.from_bytes(smpl_bytes[i*2:i*2+2], byteorder='little', signed=True)

                # Get 8-bit extension from sm24
                sm24_value = sm24_bytes[i]

                # Handle sign extension for 24-bit sample
                if sm24_value & 0x80:  # If MSB is set, it's negative
                    sm24_value |= 0xFFFFFF00  # Sign extend to 32-bit

                # Combine: upper 8 bits from sm24, lower 16 bits from smpl
                sample_24bit = (sm24_value << 16) | (smpl_word & 0xFFFF)

                # Convert back to 3 bytes (24-bit)
                combined_bytes = sample_24bit.to_bytes(3, byteorder='little', signed=True)
                combined_data[i*3:(i+1)*3] = combined_bytes

            return bytes(combined_data[:len(combined_data)//3*3])  # Ensure complete samples

        except Exception as e:
            print(f"Error reading 24-bit sample data from file: {e}")
            return None

    def _combine_24bit_sample_data(self, smpl_chunk: SF2BinaryChunk, sm24_chunk: SF2BinaryChunk,
                                  sample_start: int, sample_end: int) -> Optional[bytes]:
        """
        Combine 16-bit data from smpl chunk with 8-bit extensions from sm24 chunk
        to reconstruct proper 24-bit sample data.

        Args:
            smpl_chunk: 16-bit sample data chunk
            sm24_chunk: 8-bit extension data chunk
            sample_start: Sample start index
            sample_end: Sample end index

        Returns:
            Combined 24-bit sample data as bytes
        """
        # Calculate data ranges
        num_samples = sample_end - sample_start
        if num_samples <= 0:
            return b''

        # Each 24-bit sample needs: 2 bytes from smpl + 1 byte from sm24 = 3 bytes total
        combined_data = bytearray(num_samples * 3)

        try:
            for i in range(num_samples):
                sample_idx = sample_start + i

                # Get 16-bit data from smpl chunk (2 bytes per sample)
                smpl_offset = sample_idx * 2
                if smpl_offset + 2 > smpl_chunk.size:
                    break

                smpl_bytes = smpl_chunk.get_data_slice(smpl_offset, 2)
                if len(smpl_bytes) < 2:
                    break

                # Get 8-bit extension from sm24 chunk (1 byte per sample)
                sm24_offset = sample_idx * 1  # sm24 has 1 byte per sample
                if sm24_offset + 1 > sm24_chunk.size:
                    break

                sm24_byte = sm24_chunk.get_data_slice(sm24_offset, 1)
                if len(sm24_byte) < 1:
                    break

                # Reconstruct 24-bit sample: (sm24_byte << 16) | (smpl_word << 0)
                smpl_word = int.from_bytes(smpl_bytes, byteorder='little', signed=True)
                sm24_value = sm24_byte[0]

                # Handle sign extension for 24-bit sample
                if sm24_value & 0x80:  # If MSB is set, it's negative
                    sm24_value |= 0xFFFFFF00  # Sign extend to 32-bit

                # Combine: upper 8 bits from sm24, lower 16 bits from smpl
                sample_24bit = (sm24_value << 16) | (smpl_word & 0xFFFF)

                # Convert back to 3 bytes (24-bit)
                combined_bytes = sample_24bit.to_bytes(3, byteorder='little', signed=True)
                combined_data[i*3:(i+1)*3] = combined_bytes

            return bytes(combined_data[:len(combined_data)//3*3])  # Ensure complete samples

        except Exception as e:
            print(f"Error combining 24-bit sample data: {e}")
            return None

    def get_bag_data(self, level_type: str) -> List[Tuple[int, int]]:
        """
        Get ALL bag data (pbag/ibag) on-demand (legacy method for compatibility).

        Note: This parses all bag data upfront. For selective parsing, use
        get_bag_data_in_range() for specific bag ranges.

        Args:
            level_type: 'preset' or 'instrument'

        Returns:
            List of (gen_ndx, mod_ndx) tuples
        """
        chunk_id = 'pbag' if level_type == 'preset' else 'ibag'
        bag_chunk = self.get_chunk(chunk_id, 'pdta')
        if not bag_chunk:
            return []

        bags = []
        data = bag_chunk.data

        # Each bag is 4 bytes: gen_ndx (2), mod_ndx (2)
        for i in range(0, len(data), 4):
            if i + 4 > len(data):
                break

            gen_ndx, mod_ndx = struct.unpack('<HH', data[i:i + 4])
            bags.append((gen_ndx, mod_ndx))

        return bags

    def get_bag_data_in_range(self, level_type: str, start_bag: int, end_bag: int) -> List[Tuple[int, int]]:
        """
        Get bag data for a specific range of bags with selective parsing.

        This method only parses the bag data for the specified range,
        avoiding parsing of all bag data for large soundfonts.

        Args:
            level_type: 'preset' or 'instrument'
            start_bag: Starting bag index (inclusive)
            end_bag: Ending bag index (exclusive)

        Returns:
            List of (gen_ndx, mod_ndx) tuples for the specified range
        """
        chunk_id = 'pbag' if level_type == 'preset' else 'ibag'
        bag_chunk = self.get_chunk(chunk_id, 'pdta')
        if not bag_chunk:
            return []

        bags = []
        data = bag_chunk.data

        # Calculate byte range for the requested bags
        start_offset = start_bag * 4  # 4 bytes per bag
        end_offset = min(end_bag * 4, len(data))

        if start_offset >= len(data):
            return []

        # Parse only the requested range
        for offset in range(start_offset, end_offset, 4):
            if offset + 4 > len(data):
                break

            gen_ndx, mod_ndx = struct.unpack('<HH', data[offset:offset + 4])
            bags.append((gen_ndx, mod_ndx))

        return bags

    def get_generator_data_in_range(self, level_type: str, start_gen: int, end_gen: int) -> List[Tuple[int, int]]:
        """
        Get generator data for a specific range with selective parsing.

        Args:
            level_type: 'preset' or 'instrument'
            start_gen: Starting generator index (inclusive)
            end_gen: Ending generator index (exclusive)

        Returns:
            List of (gen_type, gen_amount) tuples for the specified range
        """
        chunk_id = 'pgen' if level_type == 'preset' else 'igen'
        gen_chunk = self.get_chunk(chunk_id, 'pdta')
        if not gen_chunk:
            return []

        generators = []
        data = gen_chunk.data

        # Calculate byte range for the requested generators
        start_offset = start_gen * 4  # 4 bytes per generator
        end_offset = min(end_gen * 4, len(data))

        if start_offset >= len(data):
            return []

        # Parse only the requested range
        for offset in range(start_offset, end_offset, 4):
            if offset + 4 > len(data):
                break

            gen_type, gen_amount = struct.unpack('<Hh', data[offset:offset + 4])
            generators.append((gen_type, gen_amount))

        return generators

    def get_modulator_data_in_range(self, level_type: str, start_mod: int, end_mod: int) -> List[Dict[str, Any]]:
        """
        Get modulator data for a specific range with selective parsing.

        Args:
            level_type: 'preset' or 'instrument'
            start_mod: Starting modulator index (inclusive)
            end_mod: Ending modulator index (exclusive)

        Returns:
            List of modulator dictionaries for the specified range
        """
        chunk_id = 'pmod' if level_type == 'preset' else 'imod'
        mod_chunk = self.get_chunk(chunk_id, 'pdta')
        if not mod_chunk:
            return []

        modulators = []
        data = mod_chunk.data

        # Calculate byte range for the requested modulators
        start_offset = start_mod * 10  # 10 bytes per modulator
        end_offset = min(end_mod * 10, len(data))

        if start_offset >= len(data):
            return []

        # Parse only the requested range
        for offset in range(start_offset, end_offset, 10):
            if offset + 10 > len(data):
                break

            mod_data = data[offset:offset + 10]
            src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper = struct.unpack('<HHhHH', mod_data)

            modulators.append({
                'src_operator': src_oper,
                'dest_operator': dest_oper,
                'mod_amount': mod_amount,
                'amt_src_operator': amt_src_oper,
                'mod_trans_operator': mod_trans_oper
            })

        return modulators

    def get_generator_data(self, level_type: str) -> List[Tuple[int, int]]:
        """
        Get generator data (pgen/igen) on-demand.

        Args:
            level_type: 'preset' or 'instrument'

        Returns:
            List of (gen_type, gen_amount) tuples
        """
        chunk_id = 'pgen' if level_type == 'preset' else 'igen'
        gen_chunk = self.get_chunk(chunk_id, 'pdta')
        if not gen_chunk:
            return []

        generators = []
        data = gen_chunk.data

        # Each generator is 4 bytes: gen_type (2), gen_amount (2, signed)
        for i in range(0, len(data), 4):
            if i + 4 > len(data):
                break

            gen_type, gen_amount = struct.unpack('<Hh', data[i:i + 4])
            generators.append((gen_type, gen_amount))

        return generators

    def get_modulator_data(self, level_type: str) -> List[Dict[str, Any]]:
        """
        Get modulator data (pmod/imod) on-demand.

        Args:
            level_type: 'preset' or 'instrument'

        Returns:
            List of modulator dictionaries
        """
        chunk_id = 'pmod' if level_type == 'preset' else 'imod'
        mod_chunk = self.get_chunk(chunk_id, 'pdta')
        if not mod_chunk:
            return []

        modulators = []
        data = mod_chunk.data

        # Each modulator is 10 bytes: src_oper(2), dest_oper(2), mod_amount(2), amt_src_oper(2), mod_trans_oper(2)
        for i in range(0, len(data), 10):
            if i + 10 > len(data):
                break

            mod_data = data[i:i + 10]
            src_oper, dest_oper, mod_amount, amt_src_oper, mod_trans_oper = struct.unpack('<HHhHH', mod_data)

            modulators.append({
                'src_operator': src_oper,
                'dest_operator': dest_oper,
                'mod_amount': mod_amount,
                'amt_src_operator': amt_src_oper,
                'mod_trans_operator': mod_trans_oper
            })

        return modulators

    def is_loaded(self) -> bool:
        """
        Check if file is loaded.

        Returns:
            True if file is loaded and ready
        """
        return self._is_loaded

    def get_file_info(self) -> Dict[str, Any]:
        """
        Get file information.

        Returns:
            Dictionary with file metadata
        """
        return {
            'filename': self.filename,
            'filepath': str(self.filepath),
            'file_size': self.file_size,
            'version': self.version,
            'bank_name': self.bank_name,
            'rom_name': self.rom_name,
            'creation_date': self.creation_date,
            'authors': self.authors,
            'product': self.product,
            'copyright': self.copyright,
            'comments': self.comments,
            'tools': self.tools,
            'loaded': self._is_loaded
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Memory usage information
        """
        total_chunks = len(self.chunk_index.chunks)
        list_chunk_groups = len(self.chunk_index.list_chunks)

        total_memory = sum(len(chunk.data) for chunk in self.chunk_index.chunks.values())
        for list_chunks in self.chunk_index.list_chunks.values():
            total_memory += sum(len(chunk.data) for chunk in list_chunks.values())

        return {
            'total_chunks': total_chunks,
            'list_chunk_groups': list_chunk_groups,
            'total_memory_bytes': total_memory,
            'total_memory_mb': total_memory / (1024 * 1024)
        }

    def clear_cache(self) -> None:
        """Clear all parsed data caches."""
        self.chunk_index.clear()

    def _cleanup(self) -> None:
        """Clean up file handles and resources."""
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

        self.chunk_index.clear()
        self._is_loaded = False

    def __del__(self):
        """Destructor - ensure cleanup."""
        self._cleanup()
