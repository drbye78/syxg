"""
Style Data Model - Core Style Classes

Defines the complete style data structure based on Yamaha SFF format,
extended with additional capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from pathlib import Path
import json


class StyleCategory(Enum):
    """Style genre categories (similar to Yamaha categories)"""

    POP = "pop"
    ROCK = "rock"
    DANCE = "dance"
    JAZZ = "jazz"
    SWING = "swing"
    BIG_BAND = "big_band"
    BALLAD = "ballad"
    BOSSANOVA = "bossa_nova"
    SALSA = "salsa"
    REGGAE = "reggae"
    COUNTRY = "country"
    LATIN = "latin"
    WORLD = "world"
    TRADITIONAL = "traditional"
    ENTERTAINER = "entertainer"
    FUSION = "fusion"
    RNB = "rnb"
    SOUL = "soul"
    FUNK = "funk"
    DISCO = "disco"
    HIPHOP = "hiphop"
    ELECTRONIC = "electronic"
    CLASSICAL = "classical"
    ORCHESTRAL = "orchestral"
    WALTZ = auto()
    MARCH = auto()
    CUSTOM = auto()


class StyleSectionType(Enum):
    """Style section types ( Yamaha SFF compatible)"""

    INTRO_1 = "intro_1"
    INTRO_2 = "intro_2"
    INTRO_3 = "intro_3"
    MAIN_A = "main_a"
    MAIN_B = "main_b"
    MAIN_C = "main_c"
    MAIN_D = "main_d"
    FILL_IN_AA = "fill_in_aa"
    FILL_IN_AB = "fill_in_ab"
    FILL_IN_AC = "fill_in_ac"
    FILL_IN_AD = "fill_in_ad"
    FILL_IN_BA = "fill_in_ba"
    FILL_IN_BB = "fill_in_bb"
    FILL_IN_BC = "fill_in_bc"
    FILL_IN_BD = "fill_in_bd"
    FILL_IN_CA = "fill_in_ca"
    FILL_IN_CB = "fill_in_cb"
    FILL_IN_CC = "fill_in_cc"
    FILL_IN_CD = "fill_in_cd"
    FILL_IN_DA = "fill_in_da"
    FILL_IN_DB = "fill_in_db"
    FILL_IN_DC = "fill_in_dc"
    FILL_IN_DD = "fill_in_dd"
    BREAK = "break"
    ENDING_1 = "ending_1"
    ENDING_2 = "ending_2"
    ENDING_3 = "ending_3"

    @property
    def is_intro(self) -> bool:
        return self.value.startswith("intro")

    @property
    def is_main(self) -> bool:
        return self.value.startswith("main")

    @property
    def is_fill(self) -> bool:
        return self.value.startswith("fill")

    @property
    def is_ending(self) -> bool:
        return self.value.startswith("ending")

    @property
    def is_break(self) -> bool:
        return self.value == "break"

    @property
    def length_bars(self) -> int:
        """Default length in bars"""
        if "intro_1" in self.value or "ending_1" in self.value:
            return 1
        elif "intro_2" in self.value or "ending_2" in self.value:
            return 2
        elif "intro_3" in self.value or "ending_3" in self.value:
            return 4
        elif "break" in self.value:
            return 1
        return 4


class StyleSectionVariation(Enum):
    """Section variation identifiers"""

    A = "a"
    B = "b"
    C = "c"
    D = "d"


class TrackType(Enum):
    """Style track types"""

    RHYTHM_1 = "rhythm_1"
    RHYTHM_2 = "rhythm_2"
    BASS = "bass"
    CHORD_1 = "chord_1"
    CHORD_2 = "chord_2"
    PAD = "pad"
    PHRASE_1 = "phrase_1"
    PHRASE_2 = "phrase_2"

    @property
    def default_midi_channel(self) -> int:
        """Default MIDI channel for this track type"""
        mapping = {
            TrackType.RHYTHM_1: 9,
            TrackType.RHYTHM_2: 9,
            TrackType.BASS: 0,
            TrackType.CHORD_1: 1,
            TrackType.CHORD_2: 2,
            TrackType.PAD: 3,
            TrackType.PHRASE_1: 4,
            TrackType.PHRASE_2: 5,
        }
        return mapping.get(self, 0)

    @property
    def is_drum(self) -> bool:
        return self in (TrackType.RHYTHM_1, TrackType.RHYTHM_2)

    @property
    def is_chordal(self) -> bool:
        return self in (TrackType.CHORD_1, TrackType.CHORD_2, TrackType.PAD)


@dataclass(slots=True)
class StyleMetadata:
    """Style metadata and header information"""

    name: str = "New Style"
    category: StyleCategory = StyleCategory.POP
    subcategory: str = ""
    tempo: int = 120
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
    volume: float = 1.0
    fade_in_time: float = 0.0
    fade_out_time: float = 0.0
    fade_in_enabled: bool = False
    fade_out_enabled: bool = False
    parent_style: str = ""
    author: str = ""
    version: str = "1.0"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    characteristics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.name,
            "subcategory": self.subcategory,
            "tempo": self.tempo,
            "time_signature": f"{self.time_signature_numerator}/{self.time_signature_denominator}",
            "volume": self.volume,
            "fade_in_time": self.fade_in_time,
            "fade_out_time": self.fade_out_time,
            "fade_in_enabled": self.fade_in_enabled,
            "fade_out_enabled": self.fade_out_enabled,
            "parent_style": self.parent_style,
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "characteristics": self.characteristics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleMetadata:
        return cls(
            name=data.get("name", "New Style"),
            category=StyleCategory[data.get("category", "POP")],
            subcategory=data.get("subcategory", ""),
            tempo=data.get("tempo", 120),
            time_signature_numerator=int(
                data.get("time_signature", "4/4").split("/")[0]
            ),
            time_signature_denominator=int(
                data.get("time_signature", "4/4").split("/")[1]
            ),
            volume=data.get("volume", 1.0),
            fade_in_time=data.get("fade_in_time", 0.0),
            fade_out_time=data.get("fade_out_time", 0.0),
            fade_in_enabled=data.get("fade_in_enabled", False),
            fade_out_enabled=data.get("fade_out_enabled", False),
            parent_style=data.get("parent_style", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            characteristics=data.get("characteristics", {}),
        )


@dataclass(slots=True)
class NoteEvent:
    """A single note event in a style pattern"""

    tick: int = 0
    note: int = 60
    velocity: int = 100
    duration: int = 480
    gate_time: float = 0.8
    variation: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "note": self.note,
            "velocity": self.velocity,
            "duration": self.duration,
            "gate_time": self.gate_time,
            "variation": self.variation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NoteEvent:
        return cls(
            tick=data.get("tick", 0),
            note=data.get("note", 60),
            velocity=data.get("velocity", 100),
            duration=data.get("duration", 480),
            gate_time=data.get("gate_time", 0.8),
            variation=data.get("variation", 0),
        )


@dataclass(slots=True)
class CCEvent:
    """MIDI Control Change event"""

    tick: int = 0
    controller: int = 7
    value: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "controller": self.controller,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CCEvent:
        return cls(
            tick=data.get("tick", 0),
            controller=data.get("controller", 7),
            value=data.get("value", 100),
        )


@dataclass(slots=True)
class StyleTrackData:
    """Note data for a single track in a section"""

    notes: list[NoteEvent] = field(default_factory=list)
    cc_events: list[CCEvent] = field(default_factory=list)
    mute: bool = False
    solo: bool = False
    volume: float = 1.0
    pan: int = 64
    reverb_send: int = 0
    chorus_send: int = 0
    variation_send: int = 0
    quantize: int = 480
    swing: float = 0.0
    groove: str = ""
    velocity_offset: int = 0
    velocity_curve: str = "linear"
    humanize: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "notes": [n.to_dict() for n in self.notes],
            "cc_events": [c.to_dict() for c in self.cc_events],
            "mute": self.mute,
            "solo": self.solo,
            "volume": self.volume,
            "pan": self.pan,
            "reverb_send": self.reverb_send,
            "chorus_send": self.chorus_send,
            "variation_send": self.variation_send,
            "quantize": self.quantize,
            "swing": self.swing,
            "groove": self.groove,
            "velocity_offset": self.velocity_offset,
            "velocity_curve": self.velocity_curve,
            "humanize": self.humanize,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleTrackData:
        return cls(
            notes=[NoteEvent.from_dict(n) for n in data.get("notes", [])],
            cc_events=[CCEvent.from_dict(c) for c in data.get("cc_events", [])],
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


@dataclass(slots=True)
class StyleSection:
    """A single section of a style (Intro, Main, Fill, Ending)"""

    section_type: StyleSectionType = StyleSectionType.MAIN_A
    length_bars: int = 4
    length_ticks: int = 1920
    tempo: int | None = None
    time_signature_numerator: int | None = None
    time_signature_denominator: int | None = None
    tracks: dict[TrackType, StyleTrackData] = field(default_factory=dict)
    fade_in_time: float = 0.0
    fade_out_time: float = 0.0
    count_in_bars: int = 0
    auto_fill: bool = True
    variation_link: StyleSectionType | None = None

    def __post_init__(self):
        if not self.tracks:
            for tt in TrackType:
                self.tracks[tt] = StyleTrackData()

    def get_track(self, track_type: TrackType) -> StyleTrackData:
        return self.tracks.get(track_type, StyleTrackData())

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_type": self.section_type.value,
            "length_bars": self.length_bars,
            "length_ticks": self.length_ticks,
            "tempo": self.tempo,
            "time_signature": (
                f"{self.time_signature_numerator}/{self.time_signature_denominator}"
                if self.time_signature_numerator
                else None
            ),
            "tracks": {k.value: v.to_dict() for k, v in self.tracks.items()},
            "fade_in_time": self.fade_in_time,
            "fade_out_time": self.fade_out_time,
            "count_in_bars": self.count_in_bars,
            "auto_fill": self.auto_fill,
            "variation_link": self.variation_link.value
            if self.variation_link
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleSection:
        section_type = StyleSectionType(data.get("section_type", "main_a"))
        time_sig = (
            data.get("time_signature", "4/4").split("/")
            if data.get("time_signature")
            else None
        )

        tracks = {}
        for tt in TrackType:
            if tt.value in data.get("tracks", {}):
                tracks[tt] = StyleTrackData.from_dict(data["tracks"][tt.value])

        return cls(
            section_type=section_type,
            length_bars=data.get("length_bars", section_type.length_bars),
            length_ticks=data.get("length_ticks", 1920),
            tempo=data.get("tempo"),
            time_signature_numerator=int(time_sig[0]) if time_sig else None,
            time_signature_denominator=int(time_sig[1]) if time_sig else None,
            tracks=tracks,
            fade_in_time=data.get("fade_in_time", 0.0),
            fade_out_time=data.get("fade_out_time", 0.0),
            count_in_bars=data.get("count_in_bars", 0),
            auto_fill=data.get("auto_fill", True),
            variation_link=StyleSectionType(data["variation_link"])
            if data.get("variation_link")
            else None,
        )


@dataclass(slots=True)
class ChordTable:
    """Chord-to-note mapping table for a style section"""

    section: StyleSectionType = StyleSectionType.MAIN_A
    chord_type_mappings: dict[str, dict[TrackType, list[int]]] = field(
        default_factory=dict
    )

    def get_notes_for_chord(
        self, chord_root: int, chord_type: str, track_type: TrackType
    ) -> list[int]:
        """Get note offsets for a specific chord"""
        key = f"{chord_root}_{chord_type}"
        if (
            key in self.chord_type_mappings
            and track_type in self.chord_type_mappings[key]
        ):
            return self.chord_type_mappings[key][track_type]
        return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section.value,
            "mappings": {
                k: {tt.value: notes for tt, notes in v.items()}
                for k, v in self.chord_type_mappings.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChordTable:
        mappings = {}
        for key, track_mappings in data.get("mappings", {}).items():
            mappings[key] = {
                TrackType(tt): notes for tt, notes in track_mappings.items()
            }
        return cls(
            section=StyleSectionType(data.get("section", "main_a")),
            chord_type_mappings=mappings,
        )


@dataclass(slots=True)
class Style:
    """
    Complete Style data structure (YAML-based SFF format)

    This is the main container for all style data, equivalent to Yamaha's
    SFF (Style File Format) but using open YAML format.

    Structure:
    - metadata: Header info (name, tempo, category, etc.)
    - sections: All section data (Intro, Main, Fill, Ending)
    - chord_tables: Chord-to-note mappings per section
    - ots_data: One Touch Settings presets
    - parameters: Style-wide parameters
    """

    metadata: StyleMetadata = field(default_factory=StyleMetadata)
    sections: dict[StyleSectionType, StyleSection] = field(default_factory=dict)
    chord_tables: dict[StyleSectionType, ChordTable] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)

    default_section: StyleSectionType = StyleSectionType.MAIN_A
    fade_master: bool = True
    tempo_lock: bool = True

    _file_path: Path | None = field(default=None, repr=False)

    def __post_init__(self):
        if not self.sections:
            self._init_default_sections()

    def _init_default_sections(self):
        """Initialize default section structure"""
        intro_types = [
            StyleSectionType.INTRO_1,
            StyleSectionType.INTRO_2,
            StyleSectionType.INTRO_3,
        ]
        main_types = [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]
        ending_types = [
            StyleSectionType.ENDING_1,
            StyleSectionType.ENDING_2,
            StyleSectionType.ENDING_3,
        ]

        for st in intro_types + main_types + [StyleSectionType.BREAK] + ending_types:
            self.sections[st] = StyleSection(section_type=st)

        for st in main_types:
            self.chord_tables[st] = ChordTable(section=st)

    def get_section(self, section_type: StyleSectionType) -> StyleSection:
        return self.sections.get(section_type, StyleSection(section_type=section_type))

    def get_main_sections(self) -> list[StyleSection]:
        return [
            self.sections[st]
            for st in StyleSectionType
            if st.is_main and st in self.sections
        ]

    def get_intro_sections(self) -> list[StyleSection]:
        return [
            self.sections[st]
            for st in StyleSectionType
            if st.is_intro and st in self.sections
        ]

    def get_ending_sections(self) -> list[StyleSection]:
        return [
            self.sections[st]
            for st in StyleSectionType
            if st.is_ending and st in self.sections
        ]

    def get_fill_for_main(self, main_section: StyleSectionType) -> list[StyleSection]:
        """Get fill sections associated with a main section"""
        fills = []
        var = main_section.value.split("_")[-1]
        for st in StyleSectionType:
            if st.is_fill and f"_{var}" in st.value:
                fills.append(self.sections.get(st, StyleSection(section_type=st)))
        return fills

    def get_next_main(self, current: StyleSectionType) -> StyleSectionType | None:
        """Get next main section in sequence"""
        main_order = [
            StyleSectionType.MAIN_A,
            StyleSectionType.MAIN_B,
            StyleSectionType.MAIN_C,
            StyleSectionType.MAIN_D,
        ]
        try:
            idx = main_order.index(current)
            return main_order[(idx + 1) % len(main_order)]
        except ValueError:
            return StyleSectionType.MAIN_A

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_format_version": "1.0",
            "metadata": self.metadata.to_dict(),
            "sections": {k.value: v.to_dict() for k, v in self.sections.items()},
            "chord_tables": {
                k.value: v.to_dict() for k, v in self.chord_tables.items()
            },
            "parameters": self.parameters,
            "default_section": self.default_section.value,
            "fade_master": self.fade_master,
            "tempo_lock": self.tempo_lock,
        }

    def to_yaml(self) -> str:
        """Convert to YAML string"""
        import yaml

        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Style:
        sections = {}
        for key, section_data in data.get("sections", {}).items():
            try:
                st = StyleSectionType(key)
                sections[st] = StyleSection.from_dict(section_data)
            except ValueError:
                continue

        chord_tables = {}
        for key, table_data in data.get("chord_tables", {}).items():
            try:
                st = StyleSectionType(key)
                chord_tables[st] = ChordTable.from_dict(table_data)
            except ValueError:
                continue

        return cls(
            metadata=StyleMetadata.from_dict(data.get("metadata", {})),
            sections=sections,
            chord_tables=chord_tables,
            parameters=data.get("parameters", {}),
            default_section=StyleSectionType(data.get("default_section", "main_a")),
            fade_master=data.get("fade_master", True),
            tempo_lock=data.get("tempo_lock", True),
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> Style:
        import yaml

        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: Path) -> Style:
        with open(file_path) as f:
            data = yaml.safe_load(f)
        style = cls.from_dict(data)
        style._file_path = file_path
        return style

    def save(self, file_path: Path | None = None):
        """Save style to YAML file"""
        path = file_path or self._file_path
        if path is None:
            raise ValueError("No file path specified")

        with open(path, "w") as f:
            f.write(self.to_yaml())
        self._file_path = path

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def tempo(self) -> int:
        return self.metadata.tempo

    @property
    def category(self) -> StyleCategory:
        return self.metadata.category
