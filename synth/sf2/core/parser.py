"""
SF2 File Parser

RIFF/SF2 file format parsing and data extraction.
Handles SoundFont 2.0 file structure and chunk processing.
"""

from typing import Dict, List, Any, Optional, BinaryIO, Tuple
import struct
import numpy as np

from .types import SF2SampleHeader
from .zones import SF2InstrumentZone, SF2PresetZone
from .containers import SF2Instrument, SF2Preset

class SF2ParseError(Exception):
    """Exception raised for SF2 parsing errors."""
    pass

class SF2SoundFont:
    """
    SF2 SoundFont Container

    Main container for SoundFont 2.0 data with all presets, instruments,
    samples, and metadata.
    """

    # SF2 Chunk IDs
    RIFF_ID = b'RIFF'
    SFBK_ID = b'sfbk'
    LIST_ID = b'LIST'
    INFO_ID = b'INFO'
    SDTA_ID = b'sdta'
    PDTA_ID = b'pdta'

    def __init__(self):
        # File metadata
        self.filename: str = ""
        self.file_size: int = 0

        # INFO chunk data
        self.version: Tuple[int, int] = (0, 0)
        self.sound_engine: str = ""
        self.bank_name: str = ""
        self.rom_name: str = ""
        self.rom_version: Tuple[int, int] = (0, 0)
        self.creation_date: str = ""
        self.sound_designers: str = ""
        self.product: str = ""
        self.copyright: str = ""
        self.comments: str = ""
        self.software: str = ""

        # Sample data
        self.sample_data: Optional[np.ndarray] = None
        self.sample_headers: List[SF2SampleHeader] = []

        # Instruments and presets
        self.instruments: List[SF2Instrument] = []
        self.presets: List[SF2Preset] = []

        # Internal parsing state
        self._instrument_bags: List[int] = []
        self._preset_bags: List[int] = []

    @classmethod
    def load_from_file(cls, filename: str) -> 'SF2SoundFont':
        """Load SF2 file from disk."""
        sf2 = cls()
        sf2.filename = filename

        try:
            with open(filename, 'rb') as f:
                sf2._parse_riff_container(f)
        except Exception as e:
            raise SF2ParseError(f"Failed to parse SF2 file {filename}: {e}")

        return sf2

    def _parse_riff_container(self, f: BinaryIO):
        """Parse the main RIFF container."""
        riff_id = f.read(4)
        if riff_id != self.RIFF_ID:
            raise SF2ParseError("Not a valid RIFF file")

        file_size = struct.unpack('<I', f.read(4))[0]
        self.file_size = file_size + 8

        sfbk_id = f.read(4)
        if sfbk_id != self.SFBK_ID:
            raise SF2ParseError("Not a valid SF2 file (missing sfbk ID)")

        while f.tell() < self.file_size:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break

            chunk_size = struct.unpack('<I', f.read(4))[0]

            if chunk_id == self.LIST_ID:
                self._parse_list_chunk(f, chunk_size)
            else:
                f.seek(chunk_size, 1)

    def _parse_list_chunk(self, f: BinaryIO, size: int):
        """Parse a LIST chunk."""
        list_type = f.read(4)

        if list_type == self.INFO_ID:
            self._parse_info_chunk(f, size - 4)
        elif list_type == self.SDTA_ID:
            self._parse_sdta_chunk(f, size - 4)
        elif list_type == self.PDTA_ID:
            self._parse_pdta_chunk(f, size - 4)

    def _parse_info_chunk(self, f: BinaryIO, size: int):
        """Parse INFO chunk with metadata."""
        end_pos = f.tell() + size

        while f.tell() < end_pos:
            sub_id = f.read(4)
            if len(sub_id) < 4:
                break

            sub_size = struct.unpack('<I', f.read(4))[0]

            if sub_id == b'ifil':
                self.version = struct.unpack('<HH', f.read(4))
            elif sub_id == b'isng':
                self.sound_engine = self._read_zstr(f, sub_size)
            elif sub_id == b'INAM':
                self.bank_name = self._read_zstr(f, sub_size)
            else:
                f.seek(sub_size, 1)

    def _parse_sdta_chunk(self, f: BinaryIO, size: int):
        """Parse SDTA chunk with sample data."""
        smpl_id = f.read(4)
        if smpl_id != b'smpl':
            return

        smpl_size = struct.unpack('<I', f.read(4))[0]

        # Simple 16-bit sample detection for now
        if smpl_size > 0:
            sample_data = np.frombuffer(f.read(smpl_size), dtype=np.int16)
            self.sample_data = sample_data.astype(np.float32) / 32768.0

    def _parse_pdta_chunk(self, f: BinaryIO, size: int):
        """Parse PDTA chunk with preset/instrument definitions."""
        end_pos = f.tell() + size

        while f.tell() < end_pos:
            sub_id = f.read(4)
            if len(sub_id) < 4:
                break

            sub_size = struct.unpack('<I', f.read(4))[0]

            if sub_id == b'phdr':
                self._parse_preset_headers(f, sub_size)
            elif sub_id == b'inst':
                self._parse_instrument_headers(f, sub_size)
            elif sub_id == b'shdr':
                self._parse_sample_headers(f, sub_size)
            else:
                f.seek(sub_size, 1)

    def _parse_preset_headers(self, f: BinaryIO, size: int):
        """Parse preset headers."""
        count = size // 38
        self.presets = []

        for _ in range(count - 1):
            name_bytes = f.read(20)
            name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')
            preset_num = struct.unpack('<H', f.read(2))[0]
            bank_num = struct.unpack('<H', f.read(2))[0]
            f.seek(12, 1)  # Skip library, genre, morphology

            preset = SF2Preset(name, bank_num, preset_num)
            self.presets.append(preset)

    def _parse_instrument_headers(self, f: BinaryIO, size: int):
        """Parse instrument headers."""
        count = size // 22
        self.instruments = []

        for _ in range(count - 1):
            name_bytes = f.read(20)
            name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')
            f.read(2)  # Skip bag index

            instrument = SF2Instrument(name)
            self.instruments.append(instrument)

    def _parse_sample_headers(self, f: BinaryIO, size: int):
        """Parse sample headers."""
        count = size // 46
        self.sample_headers = []

        for _ in range(count - 1):
            name_bytes = f.read(20)
            name = name_bytes.decode('ascii', errors='ignore').rstrip('\x00')

            start = struct.unpack('<I', f.read(4))[0]
            end = struct.unpack('<I', f.read(4))[0]
            start_loop = struct.unpack('<I', f.read(4))[0]
            end_loop = struct.unpack('<I', f.read(4))[0]
            sample_rate = struct.unpack('<I', f.read(4))[0]
            original_pitch = struct.unpack('<B', f.read(1))[0]
            pitch_correction = struct.unpack('<b', f.read(1))[0]
            sample_link = struct.unpack('<H', f.read(2))[0]
            sample_type = struct.unpack('<H', f.read(2))[0]

            header = SF2SampleHeader(
                name=name, start=start, end=end, start_loop=start_loop, end_loop=end_loop,
                sample_rate=sample_rate, original_pitch=original_pitch,
                pitch_correction=pitch_correction, sample_link=sample_link, sample_type=sample_type
            )
            self.sample_headers.append(header)

    def _read_zstr(self, f: BinaryIO, size: int) -> str:
        """Read null-terminated string."""
        data = f.read(size)
        null_pos = data.find(b'\x00')
        if null_pos >= 0:
            data = data[:null_pos]
        return data.decode('ascii', errors='ignore')

    def get_preset(self, bank: int, preset: int) -> Optional[SF2Preset]:
        """Get preset by bank and preset number."""
        for p in self.presets:
            if p.bank == bank and p.preset == preset:
                return p
        return None

    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """Get instrument by index."""
        if 0 <= index < len(self.instruments):
            return self.instruments[index]
        return None

    def get_sample_header(self, index: int) -> Optional[SF2SampleHeader]:
        """Get sample header by index."""
        if 0 <= index < len(self.sample_headers):
            return self.sample_headers[index]
        return None

    def read_sample_data(self, header: SF2SampleHeader) -> Optional[np.ndarray]:
        """Read sample data for a given header."""
        if self.sample_data is None:
            return None

        start = header.start
        end = header.end

        if start >= len(self.sample_data) or end > len(self.sample_data):
            return None

        return self.sample_data[start:end]
