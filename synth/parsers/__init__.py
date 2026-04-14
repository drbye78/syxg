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
    SECTION_TYPE_MAP,
    SFF2OTS,
    TRACK_TYPE_MAP,
    SFF2CCEvent,
    SFF2ChordTable,
    SFF2Header,
    SFF2NoteEvent,
    SFF2Parser,
    SFF2Section,
    SFF2SectionType,
    SFF2TrackData,
    SFF2TrackType,
    SFFGEParser,
    convert_sff2_to_yaml,
    parse_sff2_file,
)

__all__ = [
    # SFF2 Parser
    "SFF2Parser",
    "SFFGEParser",
    "SFF2Header",
    "SFF2Section",
    "SFF2TrackData",
    "SFF2NoteEvent",
    "SFF2CCEvent",
    "SFF2ChordTable",
    "SFF2OTS",
    "SFF2SectionType",
    "SFF2TrackType",
    "SECTION_TYPE_MAP",
    "TRACK_TYPE_MAP",
    "parse_sff2_file",
    "convert_sff2_to_yaml",
]
