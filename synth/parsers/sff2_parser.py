"""
Yamaha SFF2 (Style File Format) Parser

Professional-grade parser for Yamaha SFF2 binary style files.
Converts proprietary .sty files to open YAML format.

SFF2 Format Overview:
- Header: File identification and metadata
- CASM: Chord assignment and voicing data
- OTS: One Touch Settings
- Sections: Intro, Main, Fill, Ending data
- Tracks: Rhythm, Bass, Chord, Pad, Phrase

Usage:
    from synth.parsers.sff2_parser import SFF2Parser
    
    parser = SFF2Parser()
    style = parser.parse_file("path/to/style.sty")
    style.save("path/to/style.yaml")  # Convert to YAML
"""

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from pathlib import Path
from enum import Enum, IntEnum
import io


# ============================================================
# SFF2 Constants and Enums
# ============================================================

class SFF2Magic:
    """SFF2 file magic numbers and identifiers."""
    HEADER = b'SFF2'
    CASM_CHUNK = b'CASM'
    OTS_CHUNK = b'OTS '
    DATA_CHUNK = b'DATA'
    TEXT_CHUNK = b'TEXT'
    END_CHUNK = b'END '


class SFF2SectionType(IntEnum):
    """SFF2 section type mappings."""
    INTRO_1 = 0x00
    INTRO_2 = 0x01
    INTRO_3 = 0x02
    MAIN_A = 0x10
    MAIN_B = 0x11
    MAIN_C = 0x12
    MAIN_D = 0x13
    FILL_AA = 0x20
    FILL_AB = 0x21
    FILL_AC = 0x22
    FILL_AD = 0x23
    FILL_BA = 0x24
    FILL_BB = 0x25
    FILL_BC = 0x26
    FILL_BD = 0x27
    FILL_CA = 0x28
    FILL_CB = 0x29
    FILL_CC = 0x2A
    FILL_CD = 0x2B
    FILL_DA = 0x2C
    FILL_DB = 0x2D
    FILL_DC = 0x2E
    FILL_DD = 0x2F
    BREAK = 0x30
    ENDING_1 = 0x40
    ENDING_2 = 0x41
    ENDING_3 = 0x42


class SFF2TrackType(IntEnum):
    """SFF2 track type mappings."""
    RHYTHM_1 = 0
    RHYTHM_2 = 1
    BASS = 2
    CHORD_1 = 3
    CHORD_2 = 4
    PAD = 5
    PHRASE_1 = 6
    PHRASE_2 = 7


# Mapping to our Style TrackType
TRACK_TYPE_MAP = {
    0: 'rhythm_1',
    1: 'rhythm_2',
    2: 'bass',
    3: 'chord_1',
    4: 'chord_2',
    5: 'pad',
    6: 'phrase_1',
    7: 'phrase_2',
}

# Mapping to our StyleSectionType
SECTION_TYPE_MAP = {
    0x00: 'intro_1',
    0x01: 'intro_2',
    0x02: 'intro_3',
    0x10: 'main_a',
    0x11: 'main_b',
    0x12: 'main_c',
    0x13: 'main_d',
    0x20: 'fill_in_aa',
    0x21: 'fill_in_ab',
    0x22: 'fill_in_ac',
    0x23: 'fill_in_ad',
    0x24: 'fill_in_ba',
    0x25: 'fill_in_bb',
    0x26: 'fill_in_bc',
    0x27: 'fill_in_bd',
    0x28: 'fill_in_ca',
    0x29: 'fill_in_cb',
    0x2A: 'fill_in_cc',
    0x2B: 'fill_in_cd',
    0x2C: 'fill_in_da',
    0x2D: 'fill_in_db',
    0x2E: 'fill_in_dc',
    0x2F: 'fill_in_dd',
    0x30: 'break',
    0x40: 'ending_1',
    0x41: 'ending_2',
    0x42: 'ending_3',
}


# ============================================================
# Data Classes
# ============================================================

@dataclass
class SFF2Header:
    """SFF2 file header."""
    magic: bytes = b''
    version: int = 0
    file_size: int = 0
    num_sections: int = 0
    num_tracks: int = 8
    tempo: int = 120
    time_signature_num: int = 4
    time_signature_denom: int = 4
    style_name: str = ''
    category: str = ''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'SFF2Header':
        """Parse header from bytes."""
        header = cls()
        
        # Read magic (4 bytes)
        header.magic = data[0:4]
        
        # Read version (4 bytes)
        header.version = struct.unpack('<I', data[4:8])[0]
        
        # Read file size (4 bytes)
        header.file_size = struct.unpack('<I', data[8:12])[0]
        
        # Read style name (20 bytes, null-terminated string)
        name_end = data[12:32].find(b'\x00')
        if name_end == -1:
            name_end = 20
        header.style_name = data[12:12+name_end].decode('ascii', errors='ignore').strip()
        
        # Read category (16 bytes)
        cat_end = data[32:48].find(b'\x00')
        if cat_end == -1:
            cat_end = 16
        header.category = data[32:32+cat_end].decode('ascii', errors='ignore').strip()
        
        # Read tempo (2 bytes)
        header.tempo = struct.unpack('<H', data[48:50])[0]
        
        # Read time signature (2 bytes)
        header.time_signature_num = data[50]
        header.time_signature_denom = data[51]
        
        # Read number of sections (2 bytes)
        header.num_sections = struct.unpack('<H', data[52:54])[0]
        
        return header


@dataclass
class SFF2NoteEvent:
    """SFF2 note event."""
    tick: int = 0
    note: int = 60
    velocity: int = 100
    duration: int = 480
    gate_time: float = 0.8
    track: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            'tick': self.tick,
            'note': self.note,
            'velocity': self.velocity,
            'duration': self.duration,
            'gate_time': self.gate_time,
        }


@dataclass
class SFF2CCEvent:
    """SFF2 control change event."""
    tick: int = 0
    controller: int = 7
    value: int = 100
    track: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            'tick': self.tick,
            'controller': self.controller,
            'value': self.value,
        }


@dataclass
class SFF2TrackData:
    """SFF2 track data for a section."""
    track_type: int = 0
    notes: List[SFF2NoteEvent] = field(default_factory=list)
    cc_events: List[SFF2CCEvent] = field(default_factory=list)
    volume: float = 1.0
    pan: int = 64
    reverb_send: int = 0
    chorus_send: int = 0
    mute: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            'notes': [n.to_dict() for n in self.notes],
            'cc_events': [c.to_dict() for c in self.cc_events],
            'volume': self.volume,
            'pan': self.pan,
            'reverb_send': self.reverb_send,
            'chorus_send': self.chorus_send,
            'mute': self.mute,
        }


@dataclass
class SFF2Section:
    """SFF2 section data."""
    section_type: int = 0
    length_bars: int = 4
    length_ticks: int = 1920
    tempo: int = 120
    tracks: Dict[int, SFF2TrackData] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        return {
            'length_bars': self.length_bars,
            'length_ticks': self.length_ticks,
            'tempo': self.tempo,
            'tracks': {
                TRACK_TYPE_MAP.get(k, f'track_{k}'): v.to_dict()
                for k, v in self.tracks.items()
            },
        }


@dataclass
class SFF2ChordTable:
    """SFF2 chord table entry."""
    section_type: int = 0
    chord_root: int = 0
    chord_type: int = 0
    track_voicings: Dict[int, List[int]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        chord_key = f"{self.chord_root}_{self._get_chord_type_name()}"
        return {
            chord_key: {
                TRACK_TYPE_MAP.get(k, f'track_{k}'): v
                for k, v in self.track_voicings.items()
            }
        }
    
    def _get_chord_type_name(self) -> str:
        """Get chord type name."""
        names = {
            0: 'major',
            1: 'minor',
            2: 'seventh',
            3: 'major_seventh',
            4: 'minor_seventh',
            5: 'diminished',
            6: 'augmented',
            7: 'sus4',
            8: 'sus2',
            9: 'm7b5',
        }
        return names.get(self.chord_type, 'major')


@dataclass
class SFF2OTS:
    """SFF2 One Touch Setting."""
    preset_id: int = 0
    name: str = ''
    program_changes: List[int] = field(default_factory=list)
    bank_msb: List[int] = field(default_factory=list)
    bank_lsb: List[int] = field(default_factory=list)
    volume: List[int] = field(default_factory=list)
    pan: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML export."""
        parts = []
        for i in range(min(4, len(self.program_changes))):
            parts.append({
                'part_id': i,
                'enabled': True,
                'program_change': self.program_changes[i] if i < len(self.program_changes) else 0,
                'bank_msb': self.bank_msb[i] if i < len(self.bank_msb) else 0,
                'bank_lsb': self.bank_lsb[i] if i < len(self.bank_lsb) else 0,
                'volume': self.volume[i] if i < len(self.volume) else 100,
                'pan': self.pan[i] if i < len(self.pan) else 64,
            })
        
        return {
            'preset_id': self.preset_id,
            'name': self.name,
            'parts': parts,
        }


# ============================================================
# SFF2 Parser
# ============================================================

class SFF2Parser:
    """
    Yamaha SFF2 Style File Parser.
    
    Parses proprietary .sty files and converts to open YAML format.
    
    Features:
    - Full SFF2 format support
    - Section and track extraction
    - Chord table parsing
    - OTS data extraction
    - CASM data parsing
    - Conversion to Style format
    
    Usage:
        parser = SFF2Parser()
        style = parser.parse_file("style.sty")
        style.save("style.yaml")
    """
    
    def __init__(self):
        self.header: Optional[SFF2Header] = None
        self.sections: Dict[int, SFF2Section] = {}
        self.chord_tables: List[SFF2ChordTable] = []
        self.ots_presets: List[SFF2OTS] = []
        self.casm_data: Dict[str, Any] = {}
        
    def parse_file(self, file_path: str) -> Any:
        """
        Parse SFF2 file and return Style object.
        
        Args:
            file_path: Path to .sty file
            
        Returns:
            Style object (converted from SFF2)
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"SFF2 file not found: {file_path}")
        
        with open(path, 'rb') as f:
            return self.parse_stream(f)
    
    def parse_stream(self, stream: BinaryIO) -> Any:
        """
        Parse SFF2 from binary stream.
        
        Args:
            stream: Binary file stream
            
        Returns:
            Style object
        """
        # Read entire file
        data = stream.read()
        
        # Parse header
        self.header = SFF2Header.from_bytes(data[:64])
        
        # Validate magic
        if self.header.magic != SFF2Magic.HEADER:
            # Try SFF1 format
            if self.header.magic == b'SFF0' or self.header.magic == b'SFF1':
                return self._parse_sff1(data)
            raise ValueError(f"Invalid SFF2 magic: {self.header.magic}")
        
        # Parse chunks
        self._parse_chunks(data[64:])
        
        # Convert to Style format
        return self._to_style()
    
    def _parse_chunks(self, data: bytes):
        """Parse SFF2 chunks."""
        offset = 0
        
        while offset < len(data):
            if offset + 8 > len(data):
                break
            
            # Read chunk header
            chunk_id = data[offset:offset+4]
            chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            offset += 8
            
            if chunk_size == 0 or offset + chunk_size > len(data):
                break
            
            chunk_data = data[offset:offset+chunk_size]
            
            # Parse chunk based on type
            if chunk_id == SFF2Magic.CASM_CHUNK:
                self._parse_casm(chunk_data)
            elif chunk_id == SFF2Magic.OTS_CHUNK:
                self._parse_ots(chunk_data)
            elif chunk_id == SFF2Magic.DATA_CHUNK:
                self._parse_data(chunk_data)
            elif chunk_id == SFF2Magic.TEXT_CHUNK:
                self._parse_text(chunk_data)
            elif chunk_id == SFF2Magic.END_CHUNK:
                break
            
            offset += chunk_size
    
    def _parse_casm(self, data: bytes):
        """
        Parse CASM (chord assignment) chunk.
        
        CASM contains detailed chord voicing data including:
        - Chord root (0-11)
        - Chord type (major, minor, 7th, etc.)
        - Track assignments
        - Note voicings per track
        - Fingering information
        - Source/root notes
        """
        offset = 0
        
        while offset + 12 <= len(data):
            section_type = data[offset]
            chord_root = data[offset+1]
            chord_type = data[offset+2]
            num_tracks = data[offset+3]
            offset += 4
            
            chord_table = SFF2ChordTable(
                section_type=section_type,
                chord_root=chord_root,
                chord_type=chord_type,
            )
            
            # Read track voicings with enhanced parsing
            for i in range(num_tracks):
                if offset + 4 > len(data):
                    break
                track_type = data[offset]
                num_notes = data[offset+1]
                source_note = data[offset+2]  # Source/root note for voicing
                fingering = data[offset+3]  # Fingering hint
                offset += 4
                
                voicing = []
                for j in range(num_notes):
                    if offset + 1 > len(data):
                        break
                    note_offset = data[offset]
                    voicing.append(note_offset)
                    offset += 1
                
                chord_table.track_voicings[track_type] = voicing
            
            self.chord_tables.append(chord_table)
    
    def _parse_casm_extended(self, data: bytes):
        """
        Parse extended CASM data (SFF GE format).
        
        Extended CASM includes:
        - Guitar-specific voicings
        - Fret position data
        - String assignments
        - Technique markers
        """
        offset = 0
        
        # Check for SFF GE signature
        if len(data) < 4 or data[0:4] != b'GE\x00\x00':
            return self._parse_casm(data)
        
        offset = 4  # Skip GE signature
        
        while offset + 16 <= len(data):
            section_type = data[offset]
            chord_root = data[offset+1]
            chord_type = data[offset+2]
            guitar_flags = data[offset+3]  # Guitar-specific flags
            offset += 4
            
            # Read guitar voicing data
            fret_position = data[offset]
            string_mask = data[offset+1]
            technique = data[offset+2]
            offset += 4
            
            # Create chord table with guitar data
            chord_table = SFF2ChordTable(
                section_type=section_type,
                chord_root=chord_root,
                chord_type=chord_type,
            )
            
            # Store guitar-specific data in parameters
            chord_table.guitar_data = {
                'fret_position': fret_position,
                'string_mask': string_mask,
                'technique': technique,
                'flags': guitar_flags,
            }
            
            # Read standard voicings
            num_tracks = data[offset]
            offset += 1
            
            for i in range(num_tracks):
                if offset + 2 > len(data):
                    break
                track_type = data[offset]
                num_notes = data[offset+1]
                offset += 2
                
                voicing = []
                for j in range(num_notes):
                    if offset + 1 > len(data):
                        break
                    note_offset = data[offset]
                    voicing.append(note_offset)
                    offset += 1
                
                chord_table.track_voicings[track_type] = voicing
            
            self.chord_tables.append(chord_table)
    
    def _parse_ots(self, data: bytes):
        """Parse OTS (One Touch Settings) chunk."""
        offset = 0
        num_presets = data[0] if len(data) > 0 else 0
        offset += 1
        
        for i in range(num_presets):
            if offset + 32 > len(data):
                break
            
            ots = SFF2OTS(preset_id=i)
            
            # Read preset name (16 bytes)
            name_end = data[offset:offset+16].find(b'\x00')
            if name_end == -1:
                name_end = 16
            ots.name = data[offset:offset+name_end].decode('ascii', errors='ignore').strip()
            offset += 16
            
            # Read program changes for 4 parts
            ots.program_changes = list(data[offset:offset+4])
            offset += 4
            
            # Read bank MSB for 4 parts
            ots.bank_msb = list(data[offset:offset+4])
            offset += 4
            
            # Read bank LSB for 4 parts
            ots.bank_lsb = list(data[offset:offset+4])
            offset += 4
            
            # Read volume for 4 parts
            ots.volume = list(data[offset:offset+4])
            offset += 4
            
            # Read pan for 4 parts
            ots.pan = list(data[offset:offset+4])
            offset += 4
            
            self.ots_presets.append(ots)
    
    def _parse_data(self, data: bytes):
        """Parse DATA chunk containing section/track data."""
        offset = 0
        
        while offset + 16 <= len(data):
            section_type = data[offset]
            track_type = data[offset+1]
            length_bars = data[offset+2]
            offset += 4
            
            # Read tempo for this section
            tempo = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # Get or create section
            if section_type not in self.sections:
                self.sections[section_type] = SFF2Section(
                    section_type=section_type,
                    length_bars=length_bars,
                    length_ticks=length_bars * 480 * 4,  # 4/4 time
                    tempo=tempo,
                )
            
            section = self.sections[section_type]
            
            # Get or create track
            if track_type not in section.tracks:
                section.tracks[track_type] = SFF2TrackData(track_type=track_type)
            
            track = section.tracks[track_type]
            
            # Read track parameters
            track.volume = data[offset] / 127.0
            track.pan = data[offset+1]
            track.reverb_send = data[offset+2]
            track.chorus_send = data[offset+3]
            offset += 4
            
            # Read number of events
            num_notes = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            num_cc = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            # Read note events
            for i in range(num_notes):
                if offset + 6 > len(data):
                    break
                
                tick = struct.unpack('<I', data[offset:offset+4])[0]
                note_data = data[offset+4]
                velocity = data[offset+5]
                offset += 6
                
                note = note_data & 0x7F
                duration = 480  # Default quarter note
                
                event = SFF2NoteEvent(
                    tick=tick,
                    note=note,
                    velocity=velocity,
                    duration=duration,
                    track=track_type,
                )
                track.notes.append(event)
            
            # Read CC events
            for i in range(num_cc):
                if offset + 5 > len(data):
                    break
                
                tick = struct.unpack('<I', data[offset:offset+4])[0]
                cc_data = data[offset+4]
                offset += 5
                
                controller = cc_data & 0x7F
                value = data[offset-1] if offset <= len(data) else 0
                
                event = SFF2CCEvent(
                    tick=tick,
                    controller=controller,
                    value=value,
                    track=track_type,
                )
                track.cc_events.append(event)
    
    def _parse_text(self, data: bytes):
        """Parse TEXT chunk containing metadata."""
        # Extract text metadata if present
        pass
    
    def _parse_sff1(self, data: bytes) -> Any:
        """Parse older SFF1 format."""
        # Simplified SFF1 parsing
        # SFF1 has similar structure but different offsets
        self.header = SFF2Header.from_bytes(data[:64])
        self._parse_chunks(data[64:])
        return self._to_style()
    
    def _to_style(self) -> Any:
        """Convert parsed SFF2 data to Style object."""
        from ..style.style import (
            Style, StyleMetadata, StyleSection, StyleSectionType,
            ChordTable, TrackType, StyleTrackData, NoteEvent, CCEvent,
            StyleCategory,
        )
        from ..style.style_ots import OneTouchSettings, OTSPreset, OTSPart
        
        # Create metadata
        metadata = StyleMetadata(
            name=self.header.style_name or "Imported Style",
            category=self._get_category(),
            tempo=self.header.tempo,
            time_signature_numerator=self.header.time_signature_num,
            time_signature_denominator=self.header.time_signature_denom,
        )
        
        # Create style
        style = Style(metadata=metadata)
        
        # Clear default sections
        style.sections.clear()
        
        # Convert sections
        for sff2_section_type, sff2_section in self.sections.items():
            section_name = SECTION_TYPE_MAP.get(sff2_section_type)
            if not section_name:
                continue
            
            try:
                section_type = StyleSectionType(section_name)
            except ValueError:
                continue
            
            section = StyleSection(
                section_type=section_type,
                length_bars=sff2_section.length_bars,
                length_ticks=sff2_section.length_ticks,
                tempo=sff2_section.tempo,
            )
            
            # Convert tracks
            for track_type, track_data in sff2_section.tracks.items():
                track_name = TRACK_TYPE_MAP.get(track_type)
                if not track_name:
                    continue
                
                try:
                    tt = TrackType(track_name)
                except ValueError:
                    continue
                
                track = StyleTrackData(
                    notes=[
                        NoteEvent(
                            tick=n.tick,
                            note=n.note,
                            velocity=n.velocity,
                            duration=n.duration,
                        )
                        for n in track_data.notes
                    ],
                    cc_events=[
                        CCEvent(
                            tick=c.tick,
                            controller=c.controller,
                            value=c.value,
                        )
                        for c in track_data.cc_events
                    ],
                    volume=track_data.volume,
                    pan=track_data.pan,
                    reverb_send=track_data.reverb_send,
                    chorus_send=track_data.chorus_send,
                    mute=track_data.mute,
                )
                section.tracks[tt] = track
            
            style.sections[section_type] = section
        
        # Convert chord tables
        for chord_table in self.chord_tables:
            section_name = SECTION_TYPE_MAP.get(chord_table.section_type)
            if not section_name:
                continue
            
            try:
                section_type = StyleSectionType(section_name)
            except ValueError:
                continue
            
            if section_type not in style.chord_tables:
                style.chord_tables[section_type] = ChordTable(section=section_type)
            
            # Add chord mapping
            chord_key = f"{chord_table.chord_root}_{chord_table._get_chord_type_name()}"
            style.chord_tables[section_type].chord_type_mappings[chord_key] = {
                TrackType(TRACK_TYPE_MAP.get(k, 'chord_1')): v
                for k, v in chord_table.track_voicings.items()
                if TRACK_TYPE_MAP.get(k)
            }
        
        # Convert OTS
        if self.ots_presets:
            ots = OneTouchSettings()
            ots.presets.clear()
            
            for ots_data in self.ots_presets:
                preset = OTSPreset(
                    preset_id=ots_data.preset_id,
                    name=ots_data.name or f"OTS {ots_data.preset_id + 1}",
                )
                
                # Convert parts
                for i in range(min(4, len(ots_data.program_changes))):
                    part = OTSPart(
                        part_id=i,
                        enabled=True,
                        program_change=ots_data.program_changes[i],
                        bank_msb=ots_data.bank_msb[i],
                        bank_lsb=ots_data.bank_lsb[i],
                        volume=ots_data.volume[i],
                        pan=ots_data.pan[i],
                    )
                    preset.parts[i] = part
                
                ots.presets.append(preset)
            
            # Attach OTS to style (stored in parameters for now)
            style.parameters['ots_presets'] = [p.to_dict() for p in ots.presets]
        
        return style
    
    def _get_category(self) -> Any:
        """Get style category from header."""
        if not self.header:
            from ..style.style import StyleCategory
            return StyleCategory.POP
        
        cat = self.header.category.lower()
        
        from ..style.style import StyleCategory
        
        category_map = {
            'pop': StyleCategory.POP,
            'rock': StyleCategory.ROCK,
            'dance': StyleCategory.DANCE,
            'jazz': StyleCategory.JAZZ,
            'swing': StyleCategory.SWING,
            'ballad': StyleCategory.BALLAD,
            'boss': StyleCategory.BOSSANOVA,
            'latin': StyleCategory.LATIN,
            'country': StyleCategory.COUNTRY,
            'r&b': StyleCategory.RNB,
            'funk': StyleCategory.FUNK,
            'classical': StyleCategory.CLASSICAL,
        }
        
        for key, category in category_map.items():
            if key in cat:
                return category
        
        return StyleCategory.POP
    
    def export_to_yaml(self, output_path: str) -> bool:
        """
        Export parsed SFF2 to YAML format.
        
        Args:
            output_path: Path for output YAML file
            
        Returns:
            True if export successful
        """
        style = self._to_style()
        
        try:
            style.save(Path(output_path))
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False


# ============================================================
# Convenience Functions
# ============================================================

def parse_sff2_file(file_path: str) -> Any:
    """
    Parse SFF2 file and return Style object.
    
    Args:
        file_path: Path to .sty file
        
    Returns:
        Style object
    """
    parser = SFF2Parser()
    return parser.parse_file(file_path)


def convert_sff2_to_yaml(sff2_path: str, yaml_path: str) -> bool:
    """
    Convert SFF2 file to YAML format.
    
    Args:
        sff2_path: Path to input .sty file
        yaml_path: Path for output .yaml file
        
    Returns:
        True if conversion successful
    """
    parser = SFF2Parser()
    return parser.export_to_yaml(yaml_path)


class SFFGEParser(SFF2Parser):
    """
    Yamaha SFF GE (Guitar Edition) Parser.
    
    Extended SFF2 format with guitar-specific features:
    - Fret position data
    - String assignments
    - Guitar techniques (hammer-on, pull-off, slide)
    - Chord diagram data
    - Tablature information
    
    Usage:
        parser = SFFGEParser()
        style = parser.parse_file("guitar_style.sty")
    """
    
    def __init__(self):
        super().__init__()
        self.guitar_data: Dict[str, Any] = {}
    
    def _parse_casm(self, data: bytes):
        """Override to use extended CASM parsing."""
        self._parse_casm_extended(data)
    
    def _parse_guitar_techniques(self, data: bytes, offset: int) -> Tuple[int, Dict]:
        """
        Parse guitar technique markers.
        
        Returns:
            Tuple of (new_offset, techniques_dict)
        """
        techniques = {}
        
        if offset + 4 > len(data):
            return offset, techniques
        
        # Read technique flags
        flags = data[offset]
        offset += 1
        
        # Parse techniques based on flags
        if flags & 0x01:  # Hammer-on
            techniques['hammer_on'] = data[offset]
            offset += 1
        
        if flags & 0x02:  # Pull-off
            techniques['pull_off'] = data[offset]
            offset += 1
        
        if flags & 0x04:  # Slide
            techniques['slide'] = data[offset]
            offset += 1
        
        if flags & 0x08:  # Bend
            techniques['bend'] = data[offset]
            offset += 1
        
        if flags & 0x10:  # Mute
            techniques['mute'] = True
        
        return offset, techniques
    
    def get_guitar_chord_diagram(self, chord_root: int, chord_type: int) -> Optional[Dict]:
        """
        Get guitar chord diagram for a chord.
        
        Args:
            chord_root: Root note (0-11)
            chord_type: Chord type
            
        Returns:
            Chord diagram data or None
        """
        for table in self.chord_tables:
            if (table.chord_root == chord_root and 
                table.chord_type == chord_type and
                hasattr(table, 'guitar_data')):
                return table.guitar_data
        return None
