"""
SF2 Sample Parser

Handles parsing of SF2 sample data including headers and sample data.
"""

import struct
from typing import List, Optional, BinaryIO, Dict, Tuple, Union, Any
from ..types import SF2SampleHeader


class SampleParser:
    """
    Parser for SF2 sample data structures.
    """

    def __init__(self, file: BinaryIO, chunk_info: Dict[str, Tuple[int, int]], max_block_size: int = 10 * 1024 * 1024):
        """
        Initialize sample parser.

        Args:
            file: Open binary file handle
            chunk_info: Dictionary of chunk positions and sizes
            max_block_size: Maximum block size for reading chunks (bytes)
        """
        self.file = file
        self.chunk_info = chunk_info
        self.max_block_size = max_block_size

    def parse_sample_headers(self) -> List[SF2SampleHeader]:
        """
        Parse sample headers (shdr chunk) using block reading for performance.

        Returns:
            List of SF2SampleHeader objects
        """
        sample_headers = []

        if 'shdr' not in self.chunk_info:
            return sample_headers

        pos, size = self.chunk_info['shdr']
        self.file.seek(pos)

        # Each sample header is 46 bytes
        num_samples = size // 46

        # Read entire chunk at once for better performance
        chunk_data = self.file.read(min(size, self.max_block_size))
        if len(chunk_data) < size:
            # Fallback to individual reads if chunk is too large
            self.file.seek(pos)
            for i in range(num_samples - 1):  # Exclude terminal sample
                header_data = self.file.read(46)
                if len(header_data) < 46:
                    break
                sample_header = self._parse_single_sample_header(header_data)
                sample_headers.append(sample_header)
        else:
            # Block parse all headers
            for i in range(num_samples - 1):  # Exclude terminal sample
                offset = i * 46
                if offset + 46 > len(chunk_data):
                    break
                header_data = chunk_data[offset:offset + 46]
                sample_header = self._parse_single_sample_header(header_data)
                sample_headers.append(sample_header)

        return sample_headers

    def _parse_single_sample_header(self, header_data: bytes) -> SF2SampleHeader:
        """
        Parse a single sample header from raw bytes.

        Args:
            header_data: 46 bytes of header data

        Returns:
            SF2SampleHeader object
        """
        sample_header = SF2SampleHeader()
        sample_header.name = header_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
        sample_header.start = struct.unpack('<I', header_data[20:24])[0]
        sample_header.end = struct.unpack('<I', header_data[24:28])[0]
        sample_header.start_loop = struct.unpack('<I', header_data[28:32])[0]
        sample_header.end_loop = struct.unpack('<I', header_data[32:36])[0]
        sample_header.sample_rate = struct.unpack('<I', header_data[36:40])[0]
        sample_header.original_pitch = header_data[40]
        sample_header.pitch_correction = struct.unpack('<b', header_data[41:42])[0]  # Signed byte
        sample_header.link = struct.unpack('<H', header_data[42:44])[0]
        sample_header.type = struct.unpack('<H', header_data[44:46])[0]

        # Determine if stereo
        sample_header.stereo = (sample_header.type & 3) == 2

        return sample_header

    def read_sample_data(self, sample_header: SF2SampleHeader) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Read sample data from the file using block reading for performance.

        Args:
            sample_header: Sample header containing position information

        Returns:
            Sample data as list of floats (mono) or list of tuples (stereo)
        """
        if not self.file or 'smpl' not in self.chunk_info:
            return None

        if sample_header.data is not None:
            return sample_header.data

        # Calculate sample data size
        sample_length = sample_header.end - sample_header.start
        if sample_length <= 0:
            return None

        num_samples = sample_length * 2 if sample_header.stereo else sample_length
        sample_size = num_samples * 2  # 16-bit samples

        # Get sample data position
        smpl_pos, _ = self.chunk_info['smpl']
        self.file.seek(smpl_pos + sample_header.start * 2)

        # Read raw sample data in blocks for better performance
        raw_data = self._read_block_data(sample_size)

        # Unpack 16-bit signed integers using block unpacking
        raw_samples = self._unpack_sample_data(raw_data, num_samples)

        # Check for 24-bit samples
        is_24bit = 'sm24' in self.chunk_info
        if is_24bit:
            # Read 24-bit extension data
            sm24_pos, _ = self.chunk_info['sm24']
            self.file.seek(sm24_pos + sample_header.start)

            aux_data = self._read_block_data(num_samples)
            if len(aux_data) < num_samples:
                return None

            # Convert to 24-bit samples using vectorized operations
            maxx = 2.0 ** -23
            sample_data = [(raw_samples[i] << 8 | aux_data[i]) * maxx for i in range(num_samples)]
        else:
            # Convert to normalized floats
            sample_data = [raw_samples[i] / 32768.0 for i in range(num_samples)]

        # Format as mono or stereo
        if sample_header.stereo:
            sample_header.data = [(sample_data[i], sample_data[i + 1]) for i in range(0, len(sample_data), 2)]
        else:
            sample_header.data = sample_data

        return sample_header.data

    def _read_block_data(self, size: int) -> bytes:
        """
        Read data in blocks for better performance.

        Args:
            size: Total size to read

        Returns:
            Raw data bytes
        """
        if size <= self.max_block_size:
            return self.file.read(size)

        # Read in blocks
        data = bytearray()
        remaining = size
        while remaining > 0:
            block_size = min(remaining, self.max_block_size)
            block = self.file.read(block_size)
            if not block:
                break
            data.extend(block)
            remaining -= len(block)

        return bytes(data)

    def _unpack_sample_data(self, raw_data: bytes, num_samples: int) -> List[int]:
        """
        Unpack sample data using efficient block operations.

        Args:
            raw_data: Raw sample data bytes
            num_samples: Number of samples to unpack

        Returns:
            List of unpacked 16-bit signed integers
        """
        if len(raw_data) < num_samples * 2:
            return []

        # Use struct.unpack for efficient unpacking
        return list(struct.unpack(f'<{num_samples}h', raw_data))

    def get_sample_info(self, sample_index: int, sample_headers: List[SF2SampleHeader]) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific sample.

        Args:
            sample_index: Index of the sample
            sample_headers: List of sample headers

        Returns:
            Dictionary with sample information
        """
        if sample_index < 0 or sample_index >= len(sample_headers):
            return None

        header = sample_headers[sample_index]

        return {
            'name': header.name,
            'start': header.start,
            'end': header.end,
            'length': header.end - header.start,
            'start_loop': header.start_loop,
            'end_loop': header.end_loop,
            'sample_rate': header.sample_rate,
            'original_pitch': header.original_pitch,
            'pitch_correction': header.pitch_correction,
            'stereo': header.stereo,
            'type': header.type,
            'link': header.link
        }

    def preload_sample_data(self, sample_header: SF2SampleHeader) -> bool:
        """
        Preload sample data into memory.

        Args:
            sample_header: Sample header to preload

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self.read_sample_data(sample_header)
            return data is not None
        except Exception:
            return False

    def estimate_sample_size(self, sample_header: SF2SampleHeader) -> int:
        """
        Estimate the memory size of a sample in bytes.

        Args:
            sample_header: Sample header

        Returns:
            Estimated size in bytes
        """
        sample_length = sample_header.end - sample_header.start
        if sample_length <= 0:
            return 0

        # Base size for 16-bit samples
        base_size = sample_length * 2

        # Additional size for stereo
        if sample_header.stereo:
            base_size *= 2

        # Additional size for 24-bit samples
        if 'sm24' in self.chunk_info:
            base_size += sample_length

        # Python list/tuple overhead (rough estimate)
        python_overhead = sample_length * 8  # ~8 bytes per float/tuple

        return base_size + python_overhead
