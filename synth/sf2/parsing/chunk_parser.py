"""
SF2 Chunk Parser

Handles parsing of SF2 file chunks and basic file structure.
"""

import struct
from typing import Dict, Tuple, Optional, BinaryIO


class ChunkParser:
    """
    Parser for SF2 file chunks and basic file structure.
    """

    def __init__(self, file: BinaryIO):
        """
        Initialize chunk parser.

        Args:
            file: Open binary file handle
        """
        self.file = file
        self.chunk_info: Dict[str, Tuple[int, int]] = {}

    def parse_file_header(self) -> bool:
        """
        Parse the RIFF header of the SF2 file.

        Returns:
            True if valid SF2 file, False otherwise
        """
        try:
            # Read RIFF header
            header = self.file.read(12)
            if len(header) < 12:
                return False

            riff_id = header[:4]
            file_size = struct.unpack('<I', header[4:8])[0]
            form_type = header[8:12]

            # Check for valid SF2 format
            if riff_id != b'RIFF' or form_type != b'sfbk':
                return False

            return True
        except Exception:
            return False

    def locate_chunks(self) -> Dict[str, Tuple[int, int]]:
        """
        Locate and catalog all chunks in the SF2 file.

        Returns:
            Dictionary mapping chunk names to (position, size) tuples
        """
        if not self.file:
            return {}

        self.file.seek(12)  # Skip RIFF header

        while True:
            # Read chunk header
            chunk_header = self.file.read(8)
            if len(chunk_header) < 8:
                break

            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack('<I', chunk_header[4:8])[0]

            # Calculate chunk end position
            chunk_end = self.file.tell() + chunk_size + (chunk_size % 2)

            # Handle LIST chunks (container chunks)
            if chunk_id == b'LIST':
                list_type = self.file.read(4)
                if len(list_type) < 4:
                    break

                list_type_str = list_type.decode('ascii', 'ignore')
                list_position = self.file.tell() - 4
                self.chunk_info[list_type_str] = (list_position, chunk_size)
                self._locate_subchunks(list_position, chunk_size)
            else:
                # Regular chunk
                chunk_name = chunk_id.decode('ascii', 'ignore')
                self.chunk_info[chunk_name] = (self.file.tell(), chunk_size)

            # Move to next chunk
            self.file.seek(chunk_end)

        return self.chunk_info

    def _locate_subchunks(self, list_position: int, list_size: int):
        """
        Locate subchunks within a LIST chunk.

        Args:
            list_position: Position of the LIST chunk
            list_size: Size of the LIST chunk
        """
        if not self.file:
            return

        # Move to start of LIST data (skip LIST header)
        self.file.seek(list_position + 4)
        list_end = list_position + list_size - 4

        while self.file.tell() < list_end:
            # Read subchunk header
            subchunk_header = self.file.read(8)
            if len(subchunk_header) < 8:
                break

            subchunk_id = subchunk_header[:4]
            subchunk_size = struct.unpack('<I', subchunk_header[4:8])[0]
            subchunk_name = subchunk_id.decode('ascii', 'ignore')

            # Store subchunk info
            self.chunk_info[subchunk_name] = (self.file.tell(), subchunk_size)

            # Move to next subchunk
            subchunk_end = self.file.tell() + subchunk_size + (subchunk_size % 2)
            self.file.seek(subchunk_end)

    def get_chunk_info(self, chunk_name: str) -> Optional[Tuple[int, int]]:
        """
        Get position and size of a chunk.

        Args:
            chunk_name: Name of the chunk

        Returns:
            Tuple of (position, size) or None if not found
        """
        return self.chunk_info.get(chunk_name)

    def read_chunk_data(self, chunk_name: str) -> Optional[bytes]:
        """
        Read the data from a chunk.

        Args:
            chunk_name: Name of the chunk

        Returns:
            Chunk data as bytes or None if not found
        """
        chunk_info = self.get_chunk_info(chunk_name)
        if not chunk_info:
            return None

        position, size = chunk_info
        self.file.seek(position)
        return self.file.read(size)
