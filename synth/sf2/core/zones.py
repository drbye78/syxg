"""
SF2 Zone Classes

Zone processing classes for SF2 SoundFont instruments and presets.
Handles key/velocity ranges, generator inheritance, and modulator processing.
"""

from typing import Dict, List, Any, Tuple
from .types import SF2Generator, SF2Modulator


class SF2InstrumentZone:
    """
    SF2 Instrument Zone

    Defines a zone within an instrument with note/velocity ranges,
    generators, modulators, and sample assignment.
    """

    def __init__(self):
        # Zone ranges
        self.lokey: int = 0  # Lowest note (0-127)
        self.hikey: int = 127  # Highest note (0-127)
        self.lovel: int = 0  # Lowest velocity (0-127)
        self.hivel: int = 127  # Highest velocity (0-127)

        # Sample reference
        self.sample_index: int = -1  # Index into sample header list

        # Generators and modulators
        self.generators: Dict[int, int] = {}  # generator_type -> amount
        self.modulators: List[SF2Modulator] = []

        # Zone flags
        self.is_global: bool = False  # True if this is a global zone

    def set_generator(self, gen_type: int, amount: int):
        """Set a generator parameter."""
        self.generators[gen_type] = amount

    def add_modulator(self, modulator: SF2Modulator):
        """Add a modulator to this zone."""
        self.modulators.append(modulator)

    def get_generator(self, gen_type: int, default: int = 0) -> int:
        """Get generator value with default."""
        return self.generators.get(gen_type, default)

    def contains_note_velocity(self, note: int, velocity: int) -> bool:
        """Check if this zone contains the given note and velocity."""
        return (self.lokey <= note <= self.hikey and
                self.lovel <= velocity <= self.hivel)

    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary for serialization."""
        return {
            'lokey': self.lokey,
            'hikey': self.hikey,
            'lovel': self.lovel,
            'hivel': self.hivel,
            'sample_index': self.sample_index,
            'generators': dict(self.generators),
            'modulators': [mod._asdict() for mod in self.modulators],
            'is_global': self.is_global
        }


class SF2PresetZone:
    """
    SF2 Preset Zone

    Defines a zone within a preset with instrument reference and parameters.
    """

    def __init__(self):
        # Zone ranges
        self.lokey: int = 0
        self.hikey: int = 127
        self.lovel: int = 0
        self.hivel: int = 127

        # Instrument reference
        self.instrument_index: int = -1  # Index into instrument list

        # Generators and modulators (override instrument settings)
        self.generators: Dict[int, int] = {}
        self.modulators: List[SF2Modulator] = []

        # Zone flags
        self.is_global: bool = False

    def set_generator(self, gen_type: int, amount: int):
        """Set a generator parameter."""
        self.generators[gen_type] = amount

    def add_modulator(self, modulator: SF2Modulator):
        """Add a modulator to this zone."""
        self.modulators.append(modulator)

    def get_generator(self, gen_type: int, default: int = 0) -> int:
        """Get generator value with default."""
        return self.generators.get(gen_type, default)

    def contains_note_velocity(self, note: int, velocity: int) -> bool:
        """Check if this zone contains the given note and velocity."""
        return (self.lokey <= note <= self.hikey and
                self.lovel <= velocity <= self.hivel)

    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary for serialization."""
        return {
            'lokey': self.lokey,
            'hikey': self.hikey,
            'lovel': self.lovel,
            'hivel': self.hivel,
            'instrument_index': self.instrument_index,
            'generators': dict(self.generators),
            'modulators': [mod._asdict() for mod in self.modulators],
            'is_global': self.is_global
        }
