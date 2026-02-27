"""
Style Loader - YAML and SFF2-based Style File Parser

Parses YAML-based style files and SFF2 binary files.
Provides validation and conversion capabilities.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any
from dataclasses import asdict

from .style import (
    Style,
    StyleCategory,
    StyleMetadata,
    StyleSection,
    StyleSectionType,
    ChordTable,
    TrackType,
    StyleTrackData,
    NoteEvent,
    CCEvent,
)


class StyleValidationError(Exception):
    """Raised when style validation fails"""

    pass


class StyleLoader:
    """
    Loads and parses YAML-based style files and SFF2 binary files.

    Supports loading style files in:
    - Custom YAML format (native)
    - Yamaha SFF2 binary format (.sty)
    """

    DEFAULT_SCHEMA_VERSION = "1.0"

    def __init__(self, validate: bool = True):
        self.validate = validate
        self._sff2_parser = None

    def _get_sff2_parser(self):
        """Lazy load SFF2 parser."""
        if self._sff2_parser is None:
            try:
                from ..parsers.sff2_parser import SFF2Parser
                self._sff2_parser = SFF2Parser()
            except ImportError:
                self._sff2_parser = None
        return self._sff2_parser

    def load_style_file(self, file_path: str | Path) -> Style:
        """
        Load a style from YAML or SFF2 file.
        
        Automatically detects file format based on extension.

        Args:
            file_path: Path to style file (.yaml, .yml, or .sty)

        Returns:
            Style object
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Style file not found: {path}")

        # Detect format based on extension
        if path.suffix.lower() in ['.sty']:
            return self._load_sff2_file(path)
        else:
            return self._load_yaml_file(path)

    def _load_yaml_file(self, path: Path) -> Style:
        """Load style from YAML file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise StyleValidationError("Empty style file")

        style = self.parse_style_data(data)

        if self.validate:
            self.validate_style(style)

        style._file_path = path

        return style

    def _load_sff2_file(self, path: Path) -> Style:
        """Load style from SFF2 binary file."""
        parser = self._get_sff2_parser()
        
        if parser is None:
            raise StyleValidationError(
                "SFF2 parser not available. Install with: pip install sff2-parser"
            )

        style = parser.parse_file(str(path))

        if self.validate:
            self.validate_style(style)

        style._file_path = path

        return style

    def parse_style_data(self, data: dict[str, Any]) -> Style:
        """Parse style data from dictionary"""
        metadata = StyleMetadata.from_dict(data.get("metadata", {}))

        sections = {}
        for section_key, section_data in data.get("sections", {}).items():
            try:
                section_type = StyleSectionType(section_key)
                sections[section_type] = self._parse_section(section_data, section_type)
            except ValueError:
                continue

        chord_tables = {}
        for table_key, table_data in data.get("chord_tables", {}).items():
            try:
                section_type = StyleSectionType(table_key)
                chord_tables[section_type] = self._parse_chord_table(
                    table_data, section_type
                )
            except ValueError:
                continue

        style = Style(
            metadata=metadata,
            sections=sections,
            chord_tables=chord_tables,
            parameters=data.get("parameters", {}),
            default_section=StyleSectionType(data.get("default_section", "main_a")),
            fade_master=data.get("fade_master", True),
            tempo_lock=data.get("tempo_lock", True),
        )

        return style

    def _parse_section(
        self, data: dict[str, Any], section_type: StyleSectionType
    ) -> StyleSection:
        """Parse a style section"""
        time_sig = data.get("time_signature")
        if time_sig:
            num, den = map(int, time_sig.split("/"))
        else:
            num, den = 4, 4

        tracks = {}
        for track_key, track_data in data.get("tracks", {}).items():
            try:
                track_type = TrackType(track_key)
                tracks[track_type] = self._parse_track_data(track_data)
            except ValueError:
                continue

        section = StyleSection(
            section_type=section_type,
            length_bars=data.get("length_bars", section_type.length_bars),
            length_ticks=data.get("length_ticks", section_type.length_bars * 480 * num),
            tempo=data.get("tempo"),
            time_signature_numerator=num,
            time_signature_denominator=den,
            tracks=tracks,
            fade_in_time=data.get("fade_in_time", 0.0),
            fade_out_time=data.get("fade_out_time", 0.0),
            count_in_bars=data.get("count_in_bars", 0),
            auto_fill=data.get("auto_fill", True),
        )

        return section

    def _parse_track_data(self, data: dict[str, Any]) -> StyleTrackData:
        """Parse track data"""
        notes = [NoteEvent.from_dict(n) for n in data.get("notes", [])]
        cc_events = [CCEvent.from_dict(c) for c in data.get("cc_events", [])]

        return StyleTrackData(
            notes=notes,
            cc_events=cc_events,
            mute=data.get("mute", False),
            solo=data.get("solo", False),
            volume=data.get("volume", 1.0),
            pan=data.get("pan", 64),
            reverb_send=data.get("reverb_send", 0),
            chorus_send=data.get("chorus_send", 0),
            variation_send=data.get("variation_send", 0),
            quantize=data.get("quantize", 480),
            swing=data.get("swing", 0.0),
            groove=data.get("groove", ""),
            velocity_offset=data.get("velocity_offset", 0),
            velocity_curve=data.get("velocity_curve", "linear"),
            humanize=data.get("humanize", 0.0),
        )

    def _parse_chord_table(
        self, data: dict[str, Any], section: StyleSectionType
    ) -> ChordTable:
        """Parse chord table"""
        table = ChordTable(section=section)

        for chord_key, track_mappings in data.get("mappings", {}).items():
            mappings = {}
            for track_key, notes in track_mappings.items():
                try:
                    track_type = TrackType(track_key)
                    mappings[track_type] = notes
                except ValueError:
                    continue
            table.chord_type_mappings[chord_key] = mappings

        return table

    def validate_style(self, style: Style) -> bool:
        """Validate a style for completeness"""
        errors = []

        if not style.metadata.name:
            errors.append("Missing style name")

        if style.metadata.tempo < 20 or style.metadata.tempo > 300:
            errors.append(f"Invalid tempo: {style.metadata.tempo}")

        required_sections = [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]

        for section in required_sections:
            if section not in style.sections:
                errors.append(f"Missing required section: {section.value}")

        for section_type, section in style.sections.items():
            if not section.tracks:
                errors.append(f"Section {section_type.value} has no track data")

        if errors:
            raise StyleValidationError(f"Style validation failed: {', '.join(errors)}")

        return True

    def create_minimal_style(
        self,
        name: str = "New Style",
        category: StyleCategory = StyleCategory.POP,
        tempo: int = 120,
    ) -> Style:
        """Create a minimal valid style with default values"""
        metadata = StyleMetadata(
            name=name,
            category=category,
            tempo=tempo,
        )

        style = Style(metadata=metadata)

        return style

    def create_example_style(
        self,
        name: str = "Example Style",
        category: StyleCategory = StyleCategory.POP,
        tempo: int = 120,
    ) -> Style:
        """Create a complete example style with demo patterns"""

        metadata = StyleMetadata(
            name=name,
            category=category,
            tempo=tempo,
            time_signature_numerator=4,
            time_signature_denominator=4,
            author="Style Engine",
            version="1.0",
            description="Example style created by Style Engine",
        )

        style = Style(metadata=metadata)

        from .style import StyleSectionType

        for section_type in [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]:
            section = style.sections[section_type]

            section.length_bars = 4
            section.length_ticks = 1920

            from .style import TrackType, StyleTrackData

            for track_type in TrackType:
                track_data = StyleTrackData()

                if track_type == TrackType.RHYTHM_1:
                    track_data.notes = [
                        NoteEvent(tick=0, note=36, velocity=100, duration=120),
                        NoteEvent(tick=240, note=38, velocity=90, duration=120),
                        NoteEvent(tick=480, note=42, velocity=80, duration=120),
                        NoteEvent(tick=720, note=42, velocity=70, duration=120),
                        NoteEvent(tick=960, note=36, velocity=100, duration=120),
                        NoteEvent(tick=1200, note=38, velocity=90, duration=120),
                        NoteEvent(tick=1440, note=42, velocity=80, duration=120),
                        NoteEvent(tick=1680, note=42, velocity=70, duration=120),
                    ]
                elif track_type == TrackType.BASS:
                    track_data.notes = [
                        NoteEvent(tick=0, note=36, velocity=100, duration=480),
                        NoteEvent(tick=960, note=38, velocity=100, duration=480),
                    ]
                elif track_type in (TrackType.CHORD_1, TrackType.CHORD_2):
                    track_data.notes = [
                        NoteEvent(tick=0, note=60, velocity=80, duration=240),
                        NoteEvent(tick=480, note=64, velocity=80, duration=240),
                        NoteEvent(tick=960, note=67, velocity=80, duration=240),
                        NoteEvent(tick=1440, note=72, velocity=80, duration=240),
                    ]

                section.tracks[track_type] = track_data

        return style

    def save_style(self, style: Style, file_path: str | Path):
        """Save style to YAML file"""
        path = Path(file_path)

        with open(path, "w", encoding="utf-8") as f:
            f.write(style.to_yaml())

    def get_available_styles(self, directory: str | Path) -> list[dict[str, Any]]:
        """Get list of available styles in a directory"""
        path = Path(directory)

        if not path.exists() or not path.is_dir():
            return []

        styles = []
        
        # Load YAML styles
        for file_path in path.glob("*.yaml"):
            try:
                style = self.load_style_file(file_path)
                styles.append(
                    {
                        "name": style.name,
                        "path": str(file_path),
                        "category": style.category.name,
                        "tempo": style.tempo,
                        "format": "yaml",
                    }
                )
            except Exception:
                continue

        for file_path in path.glob("*.yml"):
            try:
                style = self.load_style_file(file_path)
                styles.append(
                    {
                        "name": style.name,
                        "path": str(file_path),
                        "category": style.category.name,
                        "tempo": style.tempo,
                        "format": "yaml",
                    }
                )
            except Exception:
                continue
        
        # Load SFF2 styles
        for file_path in path.glob("*.sty"):
            try:
                style = self.load_style_file(file_path)
                styles.append(
                    {
                        "name": style.name,
                        "path": str(file_path),
                        "category": style.category.name,
                        "tempo": style.tempo,
                        "format": "sff2",
                    }
                )
            except Exception:
                continue

        return sorted(styles, key=lambda s: s["name"])
    
    def convert_sff2_to_yaml(self, sff2_path: str | Path, 
                             yaml_path: str | Path | None = None) -> str:
        """
        Convert SFF2 file to YAML format.
        
        Args:
            sff2_path: Path to input .sty file
            yaml_path: Optional path for output .yaml file.
                      If None, uses same name with .yaml extension.
        
        Returns:
            Path to converted YAML file
        """
        sff2_path = Path(sff2_path)
        
        if yaml_path is None:
            yaml_path = sff2_path.with_suffix('.yaml')
        else:
            yaml_path = Path(yaml_path)
        
        # Load SFF2
        style = self._load_sff2_file(sff2_path)
        
        # Save as YAML
        style.save(yaml_path)
        
        return str(yaml_path)
