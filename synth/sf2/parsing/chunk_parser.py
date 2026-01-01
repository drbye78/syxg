"""
SF2 Chunk Parser - Robust RIFF chunk parsing for SoundFont 2.0 files.

This module provides comprehensive RIFF chunk parsing with support for
nested LIST chunks, error recovery, and validation.
"""

import struct
import logging
from typing import Dict, Optional, Tuple, BinaryIO, List, Any
from dataclasses import dataclass
from enum import Enum

from ..core.constants import RIFFChunks, SF2Spec

logger = logging.getLogger(__name__)


class ChunkParseError(Exception):
    """Exception raised when chunk parsing fails."""
    pass


class ChunkType(Enum):
    """Types of chunks that can be parsed."""
    RIFF = "RIFF"
    LIST = "LIST"
    DATA = "DATA"


@dataclass
class ChunkInfo:
    """Information about a parsed chunk."""
    id: str
    offset: int
    size: int
    data_offset: int
    type: ChunkType
    list_type: Optional[str] = None

    @property
    def end_offset(self) -> int:
        """Get the end offset of this chunk."""
        return self.offset + 8 + self.size  # 8 = chunk header size


class SF2ChunkParser:
    """
    Robust RIFF chunk parser for SF2 files.

    Handles nested LIST chunks, validates structure, and provides
    error recovery for malformed files.
    """

    def __init__(self, file_path: str):
        """
        Initialize the chunk parser.

        Args:
            file_path: Path to the SF2 file to parse
        """
        self.file_path = file_path
        self.file_handle: Optional[BinaryIO] = None
        self.file_size = 0
        self.chunks: Dict[str, ChunkInfo] = {}
        self.list_chunks: Dict[str, List[str]] = {}

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def open(self):
        """Open the SF2 file for parsing."""
        try:
            self.file_handle = open(self.file_path, 'rb')
            self.file_size = self._get_file_size()
            self._validate_file_header()
        except Exception as e:
            self.close()
            raise ChunkParseError(f"Failed to open SF2 file {self.file_path}: {e}")

    def close(self):
        """Close the file handle."""
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass  # Ignore errors during cleanup
            self.file_handle = None

    def parse_chunks(self) -> Dict[str, ChunkInfo]:
        """
        Parse all chunks in the SF2 file.

        Returns:
            Dictionary mapping chunk IDs to ChunkInfo objects
        """
        if not self.file_handle:
            raise ChunkParseError("File not open")

        self.chunks.clear()
        self.list_chunks.clear()

        try:
            self.file_handle.seek(0)
            self._parse_riff_container()

            logger.info(f"Parsed {len(self.chunks)} chunks from {self.file_path}")
            return self.chunks.copy()

        except Exception as e:
            logger.error(f"Failed to parse chunks: {e}")
            raise ChunkParseError(f"Chunk parsing failed: {e}")

    def get_chunk_data(self, chunk_id: str) -> Optional[bytes]:
        """
        Get raw data for a specific chunk.

        Args:
            chunk_id: ID of the chunk to retrieve

        Returns:
            Raw chunk data bytes, or None if chunk not found
        """
        if not self.file_handle or chunk_id not in self.chunks:
            return None

        chunk_info = self.chunks[chunk_id]

        try:
            self.file_handle.seek(chunk_info.data_offset)
            return self.file_handle.read(chunk_info.size)
        except Exception as e:
            logger.error(f"Failed to read chunk {chunk_id}: {e}")
            return None

    def get_list_chunks(self, list_type: str) -> List[str]:
        """
        Get all chunks within a LIST container.

        Args:
            list_type: Type of the LIST container (e.g., 'INFO', 'sdta', 'pdta')

        Returns:
            List of chunk IDs within the LIST
        """
        return self.list_chunks.get(list_type, [])

    def validate_sf2_structure(self) -> bool:
        """
        Validate that the parsed chunks form a valid SF2 structure.

        Returns:
            True if structure is valid, False otherwise
        """
        # Check for pdta LIST container (required)
        if 'LIST_pdta' not in self.chunks:
            logger.error("Missing required LIST chunk: pdta")
            return False

        # Check for critical chunks within pdta
        pdta_chunks = self.get_list_chunks('pdta')
        required_pdta = ['phdr', 'pbag', 'pgen', 'inst', 'ibag', 'igen', 'shdr']
        for chunk_id in required_pdta:
            if chunk_id not in pdta_chunks:
                logger.error(f"Missing required PDTA chunk: {chunk_id}")
                return False

        # Check for sample data chunk (may be at root level or in sdta)
        sdta_chunks = self.get_list_chunks('sdta')
        has_sample_data = 'smpl' in sdta_chunks or 'smpl' in self.chunks

        if not has_sample_data:
            logger.error("Missing required sample data chunk: smpl")
            return False

        # INFO chunks are optional for basic functionality
        # Some SF2 files may not have INFO chunks

        logger.info("SF2 structure validation passed")
        return True

    def _get_file_size(self) -> int:
        """Get the size of the file."""
        if not self.file_handle:
            return 0

        current_pos = self.file_handle.tell()
        self.file_handle.seek(0, 2)  # Seek to end
        file_size = self.file_handle.tell()
        self.file_handle.seek(current_pos)  # Restore position
        return file_size

    def _validate_file_header(self):
        """Validate the RIFF file header."""
        if not self.file_handle:
            raise ChunkParseError("File not open")

        # Read RIFF header
        header_data = self.file_handle.read(12)
        if len(header_data) < 12:
            raise ChunkParseError("File too small to be a valid RIFF file")

        riff_id, file_size_riff, sf2_magic = struct.unpack('<4sI4s', header_data)

        if riff_id != RIFFChunks.RIFF:
            raise ChunkParseError("Not a valid RIFF file")

        if sf2_magic != RIFFChunks.SF2_MAGIC:
            raise ChunkParseError("Not a valid SF2 file")

        if file_size_riff + 8 != self.file_size:
            logger.warning(f"RIFF header size ({file_size_riff + 8}) doesn't match file size ({self.file_size})")

    def _parse_riff_container(self):
        """Parse the main RIFF container and its subchunks."""
        if not self.file_handle:
            return

        # Skip the RIFF header (already validated)
        self.file_handle.seek(12)

        # Parse the three main LIST containers: INFO, sdta, pdta
        while self.file_handle.tell() < self.file_size:
            try:
                chunk_info = self._read_chunk_header()
                if not chunk_info:
                    break

                if chunk_info.type == ChunkType.LIST:
                    # Store the LIST chunk info with proper naming
                    list_key = f'LIST_{chunk_info.list_type}' if chunk_info.list_type else chunk_info.id
                    self.chunks[list_key] = chunk_info
                    self._parse_list_container(chunk_info)
                else:
                    # Store non-LIST chunks at root level
                    self.chunks[chunk_info.id] = chunk_info
                    # Skip chunk data
                    self.file_handle.seek(chunk_info.data_offset + chunk_info.size)

            except Exception as e:
                logger.warning(f"Error parsing chunk at offset {self.file_handle.tell()}: {e}")
                # Try to recover by skipping to next aligned position
                self._recover_from_parse_error()

    def _parse_list_container(self, list_chunk: ChunkInfo):
        """Parse a LIST container and its subchunks."""
        if not self.file_handle:
            return

        self.file_handle.seek(list_chunk.data_offset)

        # Parse all subchunks within this LIST
        list_end = list_chunk.data_offset + list_chunk.size
        subchunk_ids = []

        while self.file_handle.tell() < list_end:
            try:
                subchunk_info = self._read_chunk_header()
                if not subchunk_info:
                    break

                # Store the subchunk
                self.chunks[subchunk_info.id] = subchunk_info
                subchunk_ids.append(subchunk_info.id)

                # Skip to next chunk
                self.file_handle.seek(subchunk_info.data_offset + subchunk_info.size)

            except Exception as e:
                logger.warning(f"Error parsing subchunk in LIST {list_chunk.list_type}: {e}")
                break

        # Store the list of subchunks for this LIST type
        if list_chunk.list_type:
            self.list_chunks[list_chunk.list_type] = subchunk_ids

    def _read_chunk_header(self) -> Optional[ChunkInfo]:
        """
        Read a chunk header from the current file position.

        Returns:
            ChunkInfo object, or None if end of file reached
        """
        if not self.file_handle:
            return None

        current_offset = self.file_handle.tell()

        # Check if we have enough data for a chunk header
        if current_offset + 8 > self.file_size:
            return None

        # Read chunk header (8 bytes: 4-byte ID + 4-byte size)
        header_data = self.file_handle.read(8)
        if len(header_data) < 8:
            return None

        chunk_id_bytes, chunk_size = struct.unpack('<4sI', header_data)

        # Convert chunk ID to string, handling invalid characters
        try:
            chunk_id = chunk_id_bytes.decode('ascii', errors='ignore').rstrip('\x00')
        except UnicodeDecodeError:
            # Generate a synthetic ID for invalid chunks
            chunk_id = f"INVALID_{current_offset:08X}"

        # Determine chunk type
        if chunk_id == 'RIFF':
            chunk_type = ChunkType.RIFF
        elif chunk_id == 'LIST':
            chunk_type = ChunkType.LIST
        else:
            chunk_type = ChunkType.DATA

        # Handle LIST chunks specially
        list_type = None
        data_offset = self.file_handle.tell()

        if chunk_type == ChunkType.LIST:
            # Read the LIST type (4 bytes)
            if current_offset + 12 <= self.file_size:
                list_type_bytes = self.file_handle.read(4)
                if len(list_type_bytes) == 4:
                    try:
                        list_type = list_type_bytes.decode('ascii', errors='ignore').rstrip('\x00')
                    except UnicodeDecodeError:
                        list_type = f"INVALID_LIST_{current_offset:08X}"
                    # Adjust data offset for LIST chunks (after list type)
                    data_offset = self.file_handle.tell()
                    # Adjust size for LIST chunks (subtract list type size)
                    chunk_size -= 4

        # Validate chunk size
        if chunk_size < 0:
            logger.warning(f"Invalid negative chunk size for {chunk_id}: {chunk_size}")
            chunk_size = 0

        # Ensure chunk doesn't extend beyond file
        max_chunk_size = self.file_size - data_offset
        if chunk_size > max_chunk_size:
            logger.warning(f"Chunk {chunk_id} size {chunk_size} exceeds file size, truncating to {max_chunk_size}")
            chunk_size = max_chunk_size

        return ChunkInfo(
            id=chunk_id,
            offset=current_offset,
            size=chunk_size,
            data_offset=data_offset,
            type=chunk_type,
            list_type=list_type
        )

    def _recover_from_parse_error(self):
        """
        Attempt to recover from a parsing error by finding the next valid chunk.
        """
        if not self.file_handle:
            return

        current_pos = self.file_handle.tell()

        # Try to find the next chunk by looking for 4-byte boundaries
        # that might contain valid chunk IDs
        for offset in range(current_pos, min(current_pos + 1024, self.file_size - 8), 1):
            try:
                self.file_handle.seek(offset)
                potential_header = self.file_handle.read(8)

                if len(potential_header) < 8:
                    break

                chunk_id_bytes, chunk_size = struct.unpack('<4sI', potential_header)

                # Check if this looks like a valid chunk
                if self._is_likely_valid_chunk_id(chunk_id_bytes):
                    logger.info(f"Recovered parsing at offset {offset} (chunk ID: {chunk_id_bytes})")
                    self.file_handle.seek(offset)
                    return

            except Exception:
                continue

        # If we can't recover, skip to a safe boundary
        safe_offset = min(current_pos + 4, self.file_size)
        logger.warning(f"Could not recover from parse error, skipping to offset {safe_offset}")
        self.file_handle.seek(safe_offset)

    def _is_likely_valid_chunk_id(self, chunk_id_bytes: bytes) -> bool:
        """
        Check if a byte sequence looks like a valid chunk ID.

        This is a heuristic check for recovery purposes.
        """
        if len(chunk_id_bytes) != 4:
            return False

        # Check if all bytes are printable ASCII or known special cases
        for byte in chunk_id_bytes:
            if not (32 <= byte <= 126):  # Printable ASCII range
                # Allow some special cases (space, null, etc.)
                if byte not in (0, 32):
                    return False

        # Check for obviously invalid patterns
        chunk_id_str = chunk_id_bytes.decode('ascii', errors='ignore')

        # Avoid very short or repetitive IDs
        if len(chunk_id_str.strip()) < 3:
            return False

        # Avoid IDs that are all the same character
        if len(set(chunk_id_str)) == 1 and chunk_id_str[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            return False

        return True

    def get_chunk_info(self, chunk_id: str) -> Optional[ChunkInfo]:
        """
        Get information about a specific chunk.

        Args:
            chunk_id: ID of the chunk

        Returns:
            ChunkInfo object, or None if not found
        """
        return self.chunks.get(chunk_id)

    def get_chunk_sizes(self) -> Dict[str, int]:
        """
        Get sizes of all parsed chunks.

        Returns:
            Dictionary mapping chunk IDs to their sizes
        """
        return {chunk_id: info.size for chunk_id, info in self.chunks.items()}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get parsing statistics.

        Returns:
            Dictionary with parsing statistics
        """
        total_chunks = len(self.chunks)
        total_data_size = sum(info.size for info in self.chunks.values())

        list_types = {}
        for chunk_info in self.chunks.values():
            if chunk_info.list_type:
                list_types[chunk_info.list_type] = list_types.get(chunk_info.list_type, 0) + 1

        return {
            'total_chunks': total_chunks,
            'total_data_size': total_data_size,
            'list_types': list_types,
            'chunks_by_type': {
                'riff': len([c for c in self.chunks.values() if c.type == ChunkType.RIFF]),
                'list': len([c for c in self.chunks.values() if c.type == ChunkType.LIST]),
                'data': len([c for c in self.chunks.values() if c.type == ChunkType.DATA])
            }
        }


def parse_sf2_chunks(file_path: str) -> Dict[str, ChunkInfo]:
    """
    Convenience function to parse SF2 chunks.

    Args:
        file_path: Path to the SF2 file

    Returns:
        Dictionary mapping chunk IDs to ChunkInfo objects
    """
    with SF2ChunkParser(file_path) as parser:
        return parser.parse_chunks()
