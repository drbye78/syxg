"""
Synth Parsers Package

File format parsers for the synth engine including:
- SFF2 (Yamaha Style File Format) parser
- YAML style loader
- MIDI file parser (future)
- SFZ sampler format (future)
"""
from __future__ import annotations

from .sff2_parser import (
    SFF2Parser,
    SFFGEParser,
    SFF2Header,
    SFF2Section,
    SFF2TrackData,
    SFF2NoteEvent,
    SFF2CCEvent,
    SFF2ChordTable,
    SFF2OTS,
    SFF2SectionType,
    SFF2TrackType,
    SECTION_TYPE_MAP,
    TRACK_TYPE_MAP,
    parse_sff2_file,
    convert_sff2_to_yaml,
)

__all__ = [
    # SFF2 Parser
    'SFF2Parser',
    'SFFGEParser',
    'SFF2Header',
    'SFF2Section',
    'SFF2TrackData',
    'SFF2NoteEvent',
    'SFF2CCEvent',
    'SFF2ChordTable',
    'SFF2OTS',
    'SFF2SectionType',
    'SFF2TrackType',
    'SECTION_TYPE_MAP',
    'TRACK_TYPE_MAP',
    'parse_sff2_file',
    'convert_sff2_to_yaml',
]
