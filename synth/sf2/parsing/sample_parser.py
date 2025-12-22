"""
SF2 Sample Parser

Handles parsing of SF2 sample data including headers and sample data.
Supports compressed samples (Vorbis) for SF3 compatibility.
"""

import struct
import numpy as np
from typing import List, Optional, BinaryIO, Dict, Tuple, Union, Any
from ..types import SF2SampleHeader

try:
    import av  # PyAV for audio decoding
    import io
    VORBIS_AVAILABLE = True
except ImportError:
    VORBIS_AVAILABLE = False


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

        # Determine sample format and channels
        sample_type = sample_header.type & 3
        if sample_type == 1:
            # Mono sample
            sample_header.stereo = False
            sample_header.channels = 1
            sample_header.sample_format = "mono"
        elif sample_type == 2:
            # Right channel of stereo pair
            sample_header.stereo = True
            sample_header.channels = 2
            sample_header.sample_format = "stereo"
        elif sample_type == 4:
            # Left channel of stereo pair
            sample_header.stereo = True
            sample_header.channels = 2
            sample_header.sample_format = "stereo"
        else:
            # Default to mono
            sample_header.stereo = False
            sample_header.channels = 1
            sample_header.sample_format = "mono"

        return sample_header

    def read_sample_data(self, sample_header: SF2SampleHeader) -> Optional[Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
        """
        Read sample data from the file using block reading for performance.
        Supports compressed samples (Vorbis) for SF3 compatibility.

        Args:
            sample_header: Sample header containing position information

        Returns:
            Sample data as numpy array (mono) or tuple of numpy arrays (stereo per-channel planes)
        """
        if not self.file:
            return None

        if sample_header.data is not None:
            return sample_header.data

        # Check for compressed samples first
        if self._is_compressed_sample(sample_header):
            return self._read_compressed_sample_data(sample_header)

        # Handle uncompressed samples (SF2 standard)
        if 'smpl' not in self.chunk_info:
            return None

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

        # Unpack 16-bit signed integers using numpy for better performance
        if len(raw_data) < num_samples * 2:
            return None

        raw_samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)

        # Check for 24-bit samples
        is_24bit = 'sm24' in self.chunk_info
        if is_24bit:
            # Read 24-bit extension data
            sm24_pos, _ = self.chunk_info['sm24']
            self.file.seek(sm24_pos + sample_header.start)

            aux_data = self._read_block_data(num_samples)
            if len(aux_data) < num_samples:
                return None

            aux_samples = np.frombuffer(aux_data, dtype=np.uint8).astype(np.int32)
            # Convert to 24-bit samples using vectorized operations
            maxx = 2.0 ** -23
            raw_samples = ((raw_samples.astype(np.int32) << 8) | aux_samples) * maxx
        else:
            # Convert to normalized floats
            raw_samples /= 32768.0

        # Format as mono or stereo per-channel planes
        if sample_header.stereo:
            # Split into left and right channels as separate numpy arrays
            left_channel = raw_samples[0::2].copy()  # Even indices
            right_channel = raw_samples[1::2].copy()  # Odd indices
            sample_header.data = (left_channel, right_channel)
        else:
            # Mono sample as single numpy array
            sample_header.data = raw_samples

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

    def _is_compressed_sample(self, sample_header: SF2SampleHeader) -> bool:
        """
        Check if a sample is compressed.

        Args:
            sample_header: Sample header to check

        Returns:
            True if sample is compressed, False otherwise
        """
        # Check sample type for compression flags
        sample_type = sample_header.type

        # SF3 compression flags (non-standard extension)
        # Bit 8-15 may indicate compression type
        compression_type = (sample_type >> 8) & 0xFF

        if compression_type == 1 and VORBIS_AVAILABLE:
            return True  # Vorbis compressed
        elif compression_type == 2:
            return True  # Other compression (not supported yet)

        # Check for SF3-style compressed chunks
        if 'smpl' in self.chunk_info and 'cmpd' in self.chunk_info:
            # Has compressed data chunk - assume compressed
            return True

        return False

    def _read_compressed_sample_data(self, sample_header: SF2SampleHeader) -> Optional[Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
        """
        Read and decompress compressed sample data.

        Args:
            sample_header: Sample header containing position information

        Returns:
            Decompressed sample data or None if decompression failed
        """
        if not self.file:
            return None

        # Get compression information from sample type
        sample_type = sample_header.type
        compression_type = (sample_type >> 8) & 0xFF

        # Calculate compressed data size
        sample_length = sample_header.end - sample_header.start
        if sample_length <= 0:
            return None

        # For SF3-style files, compressed data is in 'cmpd' chunk
        if 'cmpd' in self.chunk_info:
            cmpd_pos, _ = self.chunk_info['cmpd']
            self.file.seek(cmpd_pos + sample_header.start)

            # Read compressed data size (first 4 bytes)
            size_data = self.file.read(4)
            if len(size_data) < 4:
                return None

            compressed_size = struct.unpack('<I', size_data)[0]

            # Read compressed data
            compressed_data = self._read_block_data(compressed_size)
            if len(compressed_data) < compressed_size:
                return None

            # Decompress based on compression type
            if compression_type == 1 and VORBIS_AVAILABLE:  # Vorbis
                return self._decompress_vorbis(compressed_data, sample_header)
            else:
                # Unsupported compression
                return None
        else:
            # Fallback: assume compressed data is inline (non-standard)
            if 'smpl' in self.chunk_info:
                smpl_pos, _ = self.chunk_info['smpl']
                self.file.seek(smpl_pos + sample_header.start * 2)

                # Read compressed data (size stored in first 4 bytes)
                size_data = self.file.read(4)
                if len(size_data) < 4:
                    return None

                compressed_size = struct.unpack('<I', size_data)[0]
                compressed_data = self._read_block_data(compressed_size)

                if compression_type == 1 and VORBIS_AVAILABLE:  # Vorbis
                    return self._decompress_vorbis(compressed_data, sample_header)

        return None

    def _decompress_vorbis(self, compressed_data: bytes, sample_header: SF2SampleHeader) -> Optional[Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
        """
        Decompress Vorbis-compressed sample data using PyAV.

        Args:
            compressed_data: Vorbis-compressed data
            sample_header: Sample header with format information

        Returns:
            Decompressed sample data or None if decompression failed
        """
        if not VORBIS_AVAILABLE:
            return None

        try:
            # Method 1: Try to decode as complete OGG file
            try:
                # Create a BytesIO object to simulate a file
                audio_stream = io.BytesIO(compressed_data)

                # Open with PyAV as if it were a complete OGG file
                container = av.open(audio_stream, format='ogg')

                # Find audio stream
                stream = None
                for s in container.streams:
                    if s.type == 'audio':
                        stream = s
                        break

                if stream is None:
                    raise ValueError("No audio stream in Vorbis data")

                # Decode all frames
                frames = []
                for frame in container.decode(stream):
                    # Convert to numpy array and transpose to (samples, channels)
                    frame_data = frame.to_ndarray().astype(np.float32).T
                    frames.append(frame_data)

                container.close()

                if not frames:
                    raise ValueError("No frames decoded from Vorbis data")

                # Concatenate all frames
                audio_data = np.concatenate(frames, axis=0)

                # Normalize to [-1, 1] range (PyAV outputs float32 in this range)
                audio_data = np.clip(audio_data, -1.0, 1.0)

                # Format output based on channels
                if sample_header.stereo:
                    if audio_data.shape[1] >= 2:
                        # Extract left and right channels
                        left_channel = audio_data[:, 0]
                        right_channel = audio_data[:, 1]
                        sample_header.data = (left_channel, right_channel)
                    else:
                        # Mono data for stereo header - duplicate channel
                        mono_data = audio_data[:, 0]
                        sample_header.data = (mono_data, mono_data)
                else:
                    # Mono output
                    if audio_data.shape[1] >= 1:
                        sample_header.data = audio_data[:, 0]
                    else:
                        raise ValueError("No audio data in decoded frames")

                return sample_header.data

            except Exception as e1:
                # Method 1 failed, try Method 2: Raw Vorbis packet decoding
                # This is more complex and may require manual OGG/Vorbis parsing
                print(f"Complete OGG decoding failed: {e1}, trying raw Vorbis decoding...")

                # For raw Vorbis data (not in OGG container), we would need to:
                # 1. Parse OGG page structure manually
                # 2. Extract Vorbis packets
                # 3. Decode Vorbis packets using av.codec
                # This is quite complex, so for now we fall back to a simpler approach

                # Method 2: Use PyAV codec directly (experimental)
                try:
                    codec = av.codec.Codec('vorbis', 'r')
                    codec_context = av.codec.CodecContext.create(codec, 'r')

                    # Set codec parameters based on sample header
                    codec_context.sample_rate = sample_header.sample_rate
                    codec_context.channels = 2 if sample_header.stereo else 1

                    # Open codec
                    codec_context.open()

                    # Feed compressed data
                    packet = av.Packet(compressed_data)
                    codec_context.send_packet(packet)

                    # Receive frames
                    frames = []
                    while True:
                        try:
                            frame = codec_context.receive_frame()
                            frames.append(frame)
                        except av.error.EOFError:
                            break

                    if frames:
                        # Process first frame (simplified - assumes single frame)
                        frame = frames[0]
                        audio_data = frame.to_ndarray().astype(np.float32).T

                        # Normalize and format output
                        audio_data = np.clip(audio_data, -1.0, 1.0)

                        if sample_header.stereo:
                            if audio_data.shape[1] >= 2:
                                left_channel = audio_data[:, 0]
                                right_channel = audio_data[:, 1]
                                sample_header.data = (left_channel, right_channel)
                            else:
                                mono_data = audio_data[:, 0]
                                sample_header.data = (mono_data, mono_data)
                        else:
                            sample_header.data = audio_data[:, 0]

                        codec_context.close()
                        return sample_header.data

                except Exception as e2:
                    print(f"Raw Vorbis decoding also failed: {e2}")

                # Final fallback: return silence with proper length
                print(f"Vorbis decompression failed, returning silence. Compressed size: {len(compressed_data)} bytes")

                sample_length = sample_header.end - sample_header.start
                if sample_header.stereo:
                    left_data = np.zeros(sample_length, dtype=np.float32)
                    right_data = np.zeros(sample_length, dtype=np.float32)
                    sample_header.data = (left_data, right_data)
                    return sample_header.data
                else:
                    mono_data = np.zeros(sample_length, dtype=np.float32)
                    sample_header.data = mono_data
                    return sample_header.data

        except Exception as e:
            print(f"Vorbis decompression failed: {e}")
            return None

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
