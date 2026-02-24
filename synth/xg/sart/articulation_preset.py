"""
S.Art2 Articulation Preset System

Provides articulation preset management for Modern XG Synth.
Supports program-specific articulation configurations with velocity/key splits.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import json


class ArticulationType(Enum):
    """Standard articulation types."""

    NORMAL = "normal"
    LEGATO = "legato"
    STACCATO = "staccato"
    TENUTO = "tenuto"
    MARCATO = "marcato"
    PIZZICATO = "pizzicato"
    SPICCATO = "spiccato"
    TREMOLO = "tremolo"
    VIBRATO = "vibrato"
    TRILL = "trill"
    GROWL = "growl"
    FLUTTER = "flutter"
    HARMONICS = "harmonics"
    # ... more articulations


@dataclass
class VelocitySplit:
    """Velocity-based articulation split."""

    vel_low: int
    vel_high: int
    articulation: str
    parameters: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.vel_low = max(0, min(127, self.vel_low))
        self.vel_high = max(0, min(127, self.vel_high))
        if self.vel_low > self.vel_high:
            self.vel_low, self.vel_high = self.vel_high, self.vel_low

    def get_articulation(self, velocity: int) -> Optional[str]:
        """Get articulation for velocity."""
        if self.vel_low <= velocity <= self.vel_high:
            return self.articulation
        return None


@dataclass
class KeySplit:
    """Key-based articulation split."""

    key_low: int
    key_high: int
    articulation: str
    parameters: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.key_low = max(0, min(127, self.key_low))
        self.key_high = max(0, min(127, self.key_high))
        if self.key_low > self.key_high:
            self.key_low, self.key_high = self.key_high, self.key_low

    def get_articulation(self, note: int) -> Optional[str]:
        """Get articulation for note."""
        if self.key_low <= note <= self.key_high:
            return self.articulation
        return None


@dataclass
class ArticulationPreset:
    """
    Articulation preset for a program.

    Contains default articulation, velocity splits, key splits,
    and parameter configurations for a specific instrument program.
    """

    name: str
    program: int
    bank: int = 0
    bank_lsb: int = 0

    # Default articulation
    default_articulation: str = "normal"

    # Splits
    velocity_splits: List[VelocitySplit] = field(default_factory=list)
    key_splits: List[KeySplit] = field(default_factory=list)

    # Global parameters
    parameters: Dict[str, float] = field(default_factory=dict)

    # Metadata
    description: str = ""
    category: str = ""  # e.g., 'piano', 'strings', 'guitar'
    instrument: str = ""  # e.g., 'grand_piano', 'violin'

    def get_articulation(
        self, note: int, velocity: int
    ) -> Tuple[str, Dict[str, float]]:
        """
        Get articulation and parameters for note/velocity.

        Priority:
        1. Key splits (if defined)
        2. Velocity splits (if defined)
        3. Default articulation

        Args:
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            Tuple of (articulation_name, parameters)
        """
        params = self.parameters.copy()

        # Check key splits first
        if self.key_splits:
            for split in self.key_splits:
                art = split.get_articulation(note)
                if art:
                    params.update(split.parameters)
                    return (art, params)

        # Check velocity splits
        if self.velocity_splits:
            for split in self.velocity_splits:
                art = split.get_articulation(velocity)
                if art:
                    params.update(split.parameters)
                    return (art, params)

        # Return default
        return (self.default_articulation, params)

    def add_velocity_split(
        self, vel_low: int, vel_high: int, articulation: str, **params
    ) -> None:
        """Add velocity split."""
        split = VelocitySplit(
            vel_low=vel_low,
            vel_high=vel_high,
            articulation=articulation,
            parameters=params,
        )
        self.velocity_splits.append(split)

    def add_key_split(
        self, key_low: int, key_high: int, articulation: str, **params
    ) -> None:
        """Add key split."""
        split = KeySplit(
            key_low=key_low,
            key_high=key_high,
            articulation=articulation,
            parameters=params,
        )
        self.key_splits.append(split)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "program": self.program,
            "bank": self.bank,
            "bank_lsb": self.bank_lsb,
            "default_articulation": self.default_articulation,
            "velocity_splits": [
                {
                    "vel_low": s.vel_low,
                    "vel_high": s.vel_high,
                    "articulation": s.articulation,
                    "parameters": s.parameters,
                }
                for s in self.velocity_splits
            ],
            "key_splits": [
                {
                    "key_low": s.key_low,
                    "key_high": s.key_high,
                    "articulation": s.articulation,
                    "parameters": s.parameters,
                }
                for s in self.key_splits
            ],
            "parameters": self.parameters,
            "description": self.description,
            "category": self.category,
            "instrument": self.instrument,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArticulationPreset":
        """Create from dictionary."""
        preset = cls(
            name=data["name"],
            program=data["program"],
            bank=data.get("bank", 0),
            bank_lsb=data.get("bank_lsb", 0),
            default_articulation=data.get("default_articulation", "normal"),
            description=data.get("description", ""),
            category=data.get("category", ""),
            instrument=data.get("instrument", ""),
        )

        # Load velocity splits
        for split_data in data.get("velocity_splits", []):
            preset.add_velocity_split(
                split_data["vel_low"],
                split_data["vel_high"],
                split_data["articulation"],
                **split_data.get("parameters", {}),
            )

        # Load key splits
        for split_data in data.get("key_splits", []):
            preset.add_key_split(
                split_data["key_low"],
                split_data["key_high"],
                split_data["articulation"],
                **split_data.get("parameters", {}),
            )

        # Load parameters
        preset.parameters = data.get("parameters", {})

        return preset

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "ArticulationPreset":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


class ArticulationPresetManager:
    """
    Manager for articulation presets.

    Provides loading, saving, and querying of articulation presets
    for all programs in the synthesizer.
    """

    def __init__(self):
        """Initialize preset manager."""
        # Presets indexed by (bank, program)
        self.presets: Dict[Tuple[int, int], ArticulationPreset] = {}

        # Category-based indexing
        self.by_category: Dict[str, List[ArticulationPreset]] = {}

        # Instrument-based indexing
        self.by_instrument: Dict[str, List[ArticulationPreset]] = {}

    def add_preset(self, preset: ArticulationPreset) -> None:
        """Add articulation preset."""
        key = (preset.bank, preset.program)
        self.presets[key] = preset

        # Index by category
        if preset.category:
            if preset.category not in self.by_category:
                self.by_category[preset.category] = []
            self.by_category[preset.category].append(preset)

        # Index by instrument
        if preset.instrument:
            if preset.instrument not in self.by_instrument:
                self.by_instrument[preset.instrument] = []
            self.by_instrument[preset.instrument].append(preset)

    def get_preset(self, bank: int, program: int) -> Optional[ArticulationPreset]:
        """Get preset for bank/program."""
        return self.presets.get((bank, program))

    def get_presets_by_category(self, category: str) -> List[ArticulationPreset]:
        """Get all presets in a category."""
        return self.by_category.get(category, [])

    def get_presets_by_instrument(self, instrument: str) -> List[ArticulationPreset]:
        """Get all presets for an instrument."""
        return self.by_instrument.get(instrument, [])

    def get_all_presets(self) -> List[ArticulationPreset]:
        """Get all presets."""
        return list(self.presets.values())

    def remove_preset(self, bank: int, program: int) -> bool:
        """Remove preset."""
        key = (bank, program)
        if key not in self.presets:
            return False

        preset = self.presets.pop(key)

        # Remove from indexes
        if preset.category and preset.category in self.by_category:
            self.by_category[preset.category].remove(preset)

        if preset.instrument and preset.instrument in self.by_instrument:
            self.by_instrument[preset.instrument].remove(preset)

        return True

    def save_to_file(self, filepath: str) -> None:
        """Save all presets to JSON file."""
        data = {
            "version": "1.0",
            "presets": [p.to_dict() for p in self.get_all_presets()],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filepath: str) -> int:
        """Load presets from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        count = 0
        for preset_data in data.get("presets", []):
            preset = ArticulationPreset.from_dict(preset_data)
            self.add_preset(preset)
            count += 1

        return count

    def get_preset_count(self) -> int:
        """Get total number of presets."""
        return len(self.presets)

    def get_category_count(self) -> int:
        """Get number of categories."""
        return len(self.by_category)

    def get_instrument_count(self) -> int:
        """Get number of instruments."""
        return len(self.by_instrument)


# ============================================================================
# BUILT-IN ARTICULATION PRESETS
# ============================================================================


def create_builtin_presets() -> ArticulationPresetManager:
    """Create built-in articulation presets for common instruments."""
    manager = ArticulationPresetManager()

    # Piano presets
    piano_preset = ArticulationPreset(
        name="Grand Piano",
        program=0,
        bank=0,
        category="piano",
        instrument="grand_piano",
        default_articulation="normal",
        description="Standard grand piano articulation",
    )
    piano_preset.add_velocity_split(0, 64, "staccato", note_length=0.5)
    piano_preset.add_velocity_split(65, 100, "normal")
    piano_preset.add_velocity_split(101, 127, "marcato", accent=1.2)
    manager.add_preset(piano_preset)

    # Electric Piano
    epiano_preset = ArticulationPreset(
        name="Electric Piano",
        program=4,
        bank=0,
        category="piano",
        instrument="electric_piano",
        default_articulation="normal",
    )
    epiano_preset.add_velocity_split(0, 80, "normal")
    epiano_preset.add_velocity_split(81, 127, "legato", release=0.3)
    manager.add_preset(epiano_preset)

    # Strings presets
    strings_preset = ArticulationPreset(
        name="Strings Ensemble",
        program=48,
        bank=0,
        category="strings",
        instrument="strings_ensemble",
        default_articulation="legato",
        description="Legato strings ensemble",
    )
    strings_preset.add_velocity_split(0, 64, "pizzicato_strings", decay=0.2)
    strings_preset.add_velocity_split(65, 100, "legato", attack=0.05)
    strings_preset.add_velocity_split(101, 127, "spiccato", accent=1.1)
    manager.add_preset(strings_preset)

    # Violin
    violin_preset = ArticulationPreset(
        name="Violin",
        program=40,
        bank=0,
        category="strings",
        instrument="violin",
        default_articulation="legato",
    )
    violin_preset.add_key_split(0, 47, "pizzicato_strings")
    violin_preset.add_key_split(48, 127, "legato")
    violin_preset.add_velocity_split(0, 64, "legato", bow_pressure=0.5)
    violin_preset.add_velocity_split(65, 127, "marcato", bow_pressure=0.8)
    manager.add_preset(violin_preset)

    # Guitar presets
    guitar_preset = ArticulationPreset(
        name="Acoustic Guitar",
        program=24,
        bank=0,
        category="guitar",
        instrument="acoustic_guitar",
        default_articulation="normal",
    )
    guitar_preset.add_velocity_split(0, 64, "palm_mute_gtr", mute=0.7)
    guitar_preset.add_velocity_split(65, 100, "normal")
    guitar_preset.add_velocity_split(101, 127, "accented", accent=1.2)
    manager.add_preset(guitar_preset)

    # Electric Guitar
    eguitar_preset = ArticulationPreset(
        name="Electric Guitar",
        program=26,
        bank=0,
        category="guitar",
        instrument="electric_guitar",
        default_articulation="normal",
    )
    eguitar_preset.add_velocity_split(0, 64, "palm_mute_gtr")
    eguitar_preset.add_velocity_split(65, 100, "normal")
    eguitar_preset.add_velocity_split(101, 127, "bend_gtr", bend_amount=0.5)
    manager.add_preset(eguitar_preset)

    # Saxophone presets
    sax_preset = ArticulationPreset(
        name="Alto Sax",
        program=65,
        bank=0,
        category="wind",
        instrument="alto_sax",
        default_articulation="normal",
    )
    sax_preset.add_velocity_split(0, 64, "sub_tone_sax", breath=0.3)
    sax_preset.add_velocity_split(65, 100, "normal")
    sax_preset.add_velocity_split(101, 127, "growl_wind", growl=0.5)
    manager.add_preset(sax_preset)

    # Trumpet
    trumpet_preset = ArticulationPreset(
        name="Trumpet",
        program=56,
        bank=0,
        category="wind",
        instrument="trumpet",
        default_articulation="normal",
    )
    trumpet_preset.add_velocity_split(0, 64, "soft", volume=0.7)
    trumpet_preset.add_velocity_split(65, 100, "normal")
    trumpet_preset.add_velocity_split(101, 127, "marcato", accent=1.3)
    manager.add_preset(trumpet_preset)

    # Vocal presets
    vocal_preset = ArticulationPreset(
        name="Choir Aahs",
        program=52,
        bank=0,
        category="vocal",
        instrument="choir",
        default_articulation="legato",
    )
    vocal_preset.add_velocity_split(0, 64, "whisper", breath=0.5)
    vocal_preset.add_velocity_split(65, 100, "normal")
    vocal_preset.add_velocity_split(101, 127, "shout", volume=1.2)
    manager.add_preset(vocal_preset)

    # Synth presets
    synth_preset = ArticulationPreset(
        name="Saw Lead",
        program=81,
        bank=0,
        category="synth",
        instrument="saw_lead",
        default_articulation="legato",
    )
    synth_preset.add_velocity_split(0, 64, "legato", filter=0.5)
    synth_preset.add_velocity_split(65, 127, "normal", filter=1.0)
    manager.add_preset(synth_preset)

    # ============================================================================
    # ADDITIONAL INSTRUMENT PRESETS
    # ============================================================================

    # ---- Keyboard Instruments ----

    # Clavinet
    clavinet_preset = ArticulationPreset(
        name="Clavinet",
        program=7,
        bank=0,
        category="keyboard",
        instrument="clavinet",
        default_articulation="normal",
    )
    clavinet_preset.add_velocity_split(0, 60, "staccato", decay=0.3)
    clavinet_preset.add_velocity_split(61, 100, "normal")
    clavinet_preset.add_velocity_split(101, 127, "accented", accent=1.3)
    manager.add_preset(clavinet_preset)

    # Hammond B3 Organ
    hammond_preset = ArticulationPreset(
        name="Hammond B3",
        program=16,
        bank=0,
        category="keyboard",
        instrument="hammond_b3",
        default_articulation="drawbar_organ",
    )
    hammond_preset.add_velocity_split(0, 64, "Organ_soft")
    hammond_preset.add_velocity_split(65, 127, "Organ_loud")
    hammond_preset.parameters = {"leslie_speed": 0.5, "drawbar_9": 0.8}
    manager.add_preset(hammond_preset)

    # Electric Piano 2
    epiano2_preset = ArticulationPreset(
        name="Electric Piano 2",
        program=5,
        bank=0,
        category="keyboard",
        instrument="electric_piano_2",
        default_articulation="normal",
    )
    epiano2_preset.add_velocity_split(0, 70, "normal")
    epiano2_preset.add_velocity_split(71, 127, "bright", brightness=1.2)
    manager.add_preset(epiano2_preset)

    # ---- Guitar Instruments ----

    # Nylon Guitar
    nylon_preset = ArticulationPreset(
        name="Nylon Guitar",
        program=24,
        bank=0,
        category="guitar",
        instrument="nylon_guitar",
        default_articulation="normal",
    )
    nylon_preset.add_key_split(0, 19, "harmonics_guitar")
    nylon_preset.add_key_split(20, 60, "normal")
    nylon_preset.add_key_split(61, 127, "tremolo_gtr")
    nylon_preset.add_velocity_split(0, 60, "soft_pedal", level=0.7)
    nylon_preset.add_velocity_split(61, 127, "normal")
    manager.add_preset(nylon_preset)

    # Electric Guitar Clean
    clean_guitar_preset = ArticulationPreset(
        name="Electric Guitar Clean",
        program=27,
        bank=0,
        category="guitar",
        instrument="electric_guitar_clean",
        default_articulation="normal",
    )
    clean_guitar_preset.add_velocity_split(0, 40, "palm_mute_gtr", mute=0.6)
    clean_guitar_preset.add_velocity_split(41, 80, "normal")
    clean_guitar_preset.add_velocity_split(81, 127, "overdrive", gain=1.2)
    manager.add_preset(clean_guitar_preset)

    # Electric Guitar Overdrive
    overdrive_preset = ArticulationPreset(
        name="Electric Guitar Overdrive",
        program=29,
        bank=0,
        category="guitar",
        instrument="electric_guitar_overdrive",
        default_articulation="distortion",
    )
    overdrive_preset.add_velocity_split(0, 50, "palm_mute_gtr", mute=0.7)
    overdrive_preset.add_velocity_split(51, 100, "normal")
    overdrive_preset.add_velocity_split(101, 127, "bend_gtr", bend_amount=0.5)
    manager.add_preset(overdrive_preset)

    # ---- Bass Instruments ----

    # Electric Bass Finger
    bass_finger_preset = ArticulationPreset(
        name="Electric Bass Finger",
        program=33,
        bank=0,
        category="bass",
        instrument="electric_bass_finger",
        default_articulation="finger_style",
    )
    bass_finger_preset.add_velocity_split(0, 50, "finger_style")
    bass_finger_preset.add_velocity_split(51, 100, "pop_bass")
    bass_finger_preset.add_velocity_split(101, 127, "slap_bass")
    bass_finger_preset.add_key_split(0, 35, "open_string", resonance=0.5)
    manager.add_preset(bass_finger_preset)

    # Electric Bass Pick
    bass_pick_preset = ArticulationPreset(
        name="Electric Bass Pick",
        program=34,
        bank=0,
        category="bass",
        instrument="electric_bass_pick",
        default_articulation="pick_style",
    )
    bass_pick_preset.add_velocity_split(0, 70, "pick_style")
    bass_pick_preset.add_velocity_split(71, 127, "dead_note", decay=0.5)
    manager.add_preset(bass_pick_preset)

    # Synth Bass
    synth_bass_preset = ArticulationPreset(
        name="Synth Bass",
        program=38,
        bank=0,
        category="bass",
        instrument="synth_bass",
        default_articulation="legato_synth",
    )
    synth_bass_preset.add_velocity_split(0, 64, "sub_bass", sub_level=0.5)
    synth_bass_preset.add_velocity_split(65, 127, "normal")
    manager.add_preset(synth_bass_preset)

    # ---- String Instruments ----

    # String Section
    strings_section_preset = ArticulationPreset(
        name="String Section",
        program=48,
        bank=0,
        category="strings",
        instrument="string_section",
        default_articulation="legato",
    )
    strings_section_preset.add_key_split(0, 40, "cello_range")
    strings_section_preset.add_key_split(41, 64, "viola_range")
    strings_section_preset.add_key_split(65, 127, "violin_range")
    strings_section_preset.add_velocity_split(0, 64, "pizzicato_strings")
    strings_section_preset.add_velocity_split(65, 127, "legato")
    manager.add_preset(strings_section_preset)

    # Solo Cello
    cello_preset = ArticulationPreset(
        name="Solo Cello",
        program=42,
        bank=0,
        category="strings",
        instrument="cello",
        default_articulation="legato",
    )
    cello_preset.add_velocity_split(0, 50, "pizzicato_bass")
    cello_preset.add_velocity_split(51, 100, "col_legno_strings")
    cello_preset.add_velocity_split(101, 127, "spiccato")
    manager.add_preset(cello_preset)

    # ---- Wind Instruments ----

    # Tenor Sax
    tenor_sax_preset = ArticulationPreset(
        name="Tenor Sax",
        program=66,
        bank=0,
        category="winds",
        instrument="tenor_sax",
        default_articulation="legato",
    )
    tenor_sax_preset.add_velocity_split(0, 50, "breath", breath=0.4)
    tenor_sax_preset.add_velocity_split(51, 100, "normal")
    tenor_sax_preset.add_velocity_split(101, 127, "growl_wind", growl=0.6)
    manager.add_preset(tenor_sax_preset)

    # Soprano Sax
    soprano_sax_preset = ArticulationPreset(
        name="Soprano Sax",
        program=63,
        bank=0,
        category="winds",
        instrument="soprano_sax",
        default_articulation="normal",
    )
    soprano_sax_preset.add_velocity_split(0, 60, "sub_tone_sax")
    soprano_sax_preset.add_velocity_split(61, 127, "legato")
    manager.add_preset(soprano_sax_preset)

    # Flute
    flute_preset = ArticulationPreset(
        name="Flute",
        program=73,
        bank=0,
        category="winds",
        instrument="flute",
        default_articulation="normal",
    )
    flute_preset.add_velocity_split(0, 60, "breath", breath=0.5)
    flute_preset.add_velocity_split(61, 127, "normal")
    manager.add_preset(flute_preset)

    # Clarinet
    clarinet_preset = ArticulationPreset(
        name="Clarinet",
        program=71,
        bank=0,
        category="winds",
        instrument="clarinet",
        default_articulation="normal",
    )
    clarinet_preset.add_velocity_split(0, 50, "soft")
    clarinet_preset.add_velocity_split(51, 100, "normal")
    clarinet_preset.add_velocity_split(101, 127, "accented")
    manager.add_preset(clarinet_preset)

    # ---- Brass Instruments ----

    # Trombone
    trombone_preset = ArticulationPreset(
        name="Trombone",
        program=57,
        bank=0,
        category="brass",
        instrument="trombone",
        default_articulation="legato",
    )
    trombone_preset.add_velocity_split(0, 50, "muted_brass", mute=0.6)
    trombone_preset.add_velocity_split(51, 100, "normal")
    trombone_preset.add_velocity_split(101, 127, "scoop_brass", scoop=0.5)
    manager.add_preset(trombone_preset)

    # French Horn
    french_horn_preset = ArticulationPreset(
        name="French Horn",
        program=60,
        bank=0,
        category="brass",
        instrument="french_horn",
        default_articulation="muted_brass",
    )
    french_horn_preset.add_velocity_split(0, 80, "muted_brass")
    french_horn_preset.add_velocity_split(81, 127, "cup_mute")
    manager.add_preset(french_horn_preset)

    # ---- Drum Kits ----

    # Rock Drum Kit
    rock_kit_preset = ArticulationPreset(
        name="Rock Drum Kit",
        program=0,
        bank=0,
        category="drums",
        instrument="rock_kit",
        default_articulation="normal",
    )
    rock_kit_preset.add_key_split(35, 36, "kick")
    rock_kit_preset.add_key_split(36, 37, "kick")
    rock_kit_preset.add_key_split(38, 38, "snare")
    rock_kit_preset.add_key_split(40, 40, "snare")
    rock_kit_preset.add_key_split(42, 42, "hihat")
    rock_kit_preset.add_key_split(46, 46, "hihat")
    manager.add_preset(rock_kit_preset)

    # Jazz Drum Kit
    jazz_kit_preset = ArticulationPreset(
        name="Jazz Drum Kit",
        program=1,
        bank=0,
        category="drums",
        instrument="jazz_kit",
        default_articulation="brush_sweep",
    )
    jazz_kit_preset.add_key_split(36, 36, "kick")
    jazz_kit_preset.add_key_split(38, 38, "snare")
    jazz_kit_preset.add_key_split(41, 41, "floor_tom")
    manager.add_preset(jazz_kit_preset)

    # Electronic Drum Kit
    electronic_kit_preset = ArticulationPreset(
        name="Electronic Drum Kit",
        program=24,
        bank=0,
        category="drums",
        instrument="electronic_kit",
        default_articulation="normal",
    )
    electronic_kit_preset.add_key_split(36, 36, "kick")
    electronic_kit_preset.add_key_split(38, 38, "snare")
    electronic_kit_preset.add_key_split(42, 42, "hihat")
    manager.add_preset(electronic_kit_preset)

    # ---- Ethnic Instruments ----

    # Sitar
    sitar_preset = ArticulationPreset(
        name="Sitar",
        program=104,
        bank=0,
        category="ethnic",
        instrument="sitar",
        default_articulation="sitar_attack",
    )
    sitar_preset.add_key_split(0, 30, "sitar_bend", bend_amount=0.3)
    sitar_preset.add_key_split(31, 127, "sitar_pluck")
    manager.add_preset(sitar_preset)

    # Balalaika
    balalaika_preset = ArticulationPreset(
        name="Balalaika",
        program=107,
        bank=0,
        category="ethnic",
        instrument="balalaika",
        default_articulation="normal",
    )
    balalaika_preset.add_velocity_split(0, 60, "pluck")
    balalaika_preset.add_velocity_split(61, 127, "tremolo")
    manager.add_preset(balalaika_preset)

    # Shamisen
    shamisen_preset = ArticulationPreset(
        name="Shamisen",
        program=106,
        bank=0,
        category="ethnic",
        instrument="shamisen",
        default_articulation="pluck",
    )
    shamisen_preset.add_velocity_split(0, 80, "normal")
    shamisen_preset.add_velocity_split(81, 127, "bend_ethnic", bend=0.5)
    manager.add_preset(shamisen_preset)

    # Koto
    koto_preset = ArticulationPreset(
        name="Koto",
        program=107,
        bank=0,
        category="ethnic",
        instrument="koto",
        default_articulation="pluck",
    )
    koto_preset.add_key_split(0, 40, "harmonics_ethnic")
    koto_preset.add_key_split(41, 127, "normal")
    manager.add_preset(koto_preset)

    # ---- Additional Synths ----

    # Polysynth
    polysynth_preset = ArticulationPreset(
        name="Polysynth",
        program=80,
        bank=0,
        category="synth",
        instrument="polysynth",
        default_articulation="normal",
    )
    polysynth_preset.add_velocity_split(0, 64, "legato_synth")
    polysynth_preset.add_velocity_split(65, 127, "normal")
    manager.add_preset(polysynth_preset)

    # Square Lead
    square_lead_preset = ArticulationPreset(
        name="Square Lead",
        program=80,
        bank=0,
        category="synth",
        instrument="square_lead",
        default_articulation="staccato_synth",
    )
    square_lead_preset.add_velocity_split(0, 50, "staccato_synth")
    square_lead_preset.add_velocity_split(51, 100, "normal")
    square_lead_preset.add_velocity_split(101, 127, "glide")
    manager.add_preset(square_lead_preset)

    # ---- Vocal ----

    # Solo Voice
    solo_voice_preset = ArticulationPreset(
        name="Solo Voice",
        program=52,
        bank=0,
        category="vocal",
        instrument="solo_voice",
        default_articulation="chest_voice",
    )
    solo_voice_preset.add_velocity_split(0, 40, "falsetto")
    solo_voice_preset.add_velocity_split(41, 80, "chest_voice")
    solo_voice_preset.add_velocity_split(81, 127, "head_voice")
    manager.add_preset(solo_voice_preset)

    return manager


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def get_default_preset_manager() -> ArticulationPresetManager:
    """Get default preset manager with built-in presets."""
    return create_builtin_presets()


def create_empty_preset_manager() -> ArticulationPresetManager:
    """Create empty preset manager."""
    return ArticulationPresetManager()
