"""
Groove Quantization System

Provides groove templates and quantization for natural-sounding
rhythmic variations in style playback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random


class GrooveType(Enum):
    """Groove template types"""

    OFF = "off"
    SWING_1_3 = "swing_1_3"
    SWING_2_3 = "swing_2_3"
    SHUFFLE = "shuffle"
    FUNK = "funk"
    POP = "pop"
    LATIN = "latin"
    JAZZ = "jazz"
    BOSSA = "bossa"
    WALTZ = "waltz"
    CUSTOM = "custom"


@dataclass(slots=True)
class GrooveTemplate:
    """
    A groove template defining timing offsets for each 16th note position.

    The timing_offsets array contains the timing adjustment (in ticks)
    for each 16th note in a 4/4 measure:
    - Index 0-3: 1st beat (quarter note)
    - Index 4-7: 2nd beat
    - Index 8-11: 3rd beat
    - Index 12-15: 4th beat

    Positive values delay the note, negative values advance it.
    """

    name: str = "Off"
    groove_type: GrooveType = GrooveType.OFF
    timing_offsets: list[int] = field(default_factory=lambda: [0] * 16)
    velocity_offsets: list[int] = field(default_factory=lambda: [0] * 16)
    description: str = ""

    def __post_init__(self):
        if len(self.timing_offsets) < 16:
            self.timing_offsets = self.timing_offsets + [0] * (
                16 - len(self.timing_offsets)
            )
        if len(self.velocity_offsets) < 16:
            self.velocity_offsets = self.velocity_offsets + [0] * (
                16 - len(self.velocity_offsets)
            )

    def get_timing_offset(self, position_16th: int) -> int:
        """Get timing offset for a 16th note position (0-15)"""
        return self.timing_offsets[position_16th % 16]

    def get_velocity_offset(self, position_16th: int) -> int:
        """Get velocity offset for a 16th note position (0-15)"""
        return self.velocity_offsets[position_16th % 16]


# Built-in groove templates
GROOVE_TEMPLATES: dict[GrooveType, GrooveTemplate] = {
    GrooveType.OFF: GrooveTemplate(
        name="Off",
        groove_type=GrooveType.OFF,
        timing_offsets=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        description="No groove - straight timing",
    ),
    GrooveType.SWING_1_3: GrooveTemplate(
        name="Swing 1:3",
        groove_type=GrooveType.SWING_1_3,
        timing_offsets=[0, 30, 0, 0, 0, 30, 0, 0, 0, 30, 0, 0, 0, 30, 0, 0],
        description="Basic swing feel - even 8ths delayed by 30 ticks",
    ),
    GrooveType.SWING_2_3: GrooveTemplate(
        name="Swing 2:3",
        groove_type=GrooveType.SWING_2_3,
        timing_offsets=[0, 50, 0, 0, 0, 50, 0, 0, 0, 50, 0, 0, 0, 50, 0, 0],
        description="Strong swing feel - even 8ths delayed by 50 ticks",
    ),
    GrooveType.SHUFFLE: GrooveTemplate(
        name="Shuffle",
        groove_type=GrooveType.SHUFFLE,
        timing_offsets=[0, 40, -10, 20, 0, 40, -10, 20, 0, 40, -10, 20, 0, 40, -10, 20],
        description="Shuffle feel with triplet-like variations",
    ),
    GrooveType.FUNK: GrooveTemplate(
        name="Funk",
        groove_type=GrooveType.FUNK,
        timing_offsets=[0, 15, -5, 25, 0, 10, -15, 30, 0, 15, -5, 25, 0, 10, -15, 30],
        description="Funky groove with syncopated feel",
    ),
    GrooveType.POP: GrooveTemplate(
        name="Pop",
        groove_type=GrooveType.POP,
        timing_offsets=[0, 10, 0, 5, 0, 10, 0, 5, 0, 10, 0, 5, 0, 10, 0, 5],
        description="Subtle pop groove",
    ),
    GrooveType.LATIN: GrooveTemplate(
        name="Latin",
        groove_type=GrooveType.LATIN,
        timing_offsets=[0, -10, 20, -5, 0, -10, 20, -5, 0, -10, 20, -5, 0, -10, 20, -5],
        description="Latin feel with forward momentum",
    ),
    GrooveType.JAZZ: GrooveTemplate(
        name="Jazz",
        groove_type=GrooveType.JAZZ,
        timing_offsets=[
            0,
            25,
            -15,
            35,
            -10,
            25,
            -15,
            35,
            0,
            25,
            -15,
            35,
            -10,
            25,
            -15,
            35,
        ],
        description="Jazz feel with heavy swing",
    ),
    GrooveType.BOSSA: GrooveTemplate(
        name="Bossa",
        groove_type=GrooveType.BOSSA,
        timing_offsets=[
            0,
            20,
            -10,
            30,
            -5,
            20,
            -10,
            30,
            0,
            20,
            -10,
            30,
            -5,
            20,
            -10,
            30,
        ],
        description="Bossa nova feel",
    ),
    GrooveType.WALTZ: GrooveTemplate(
        name="Waltz",
        groove_type=GrooveType.WALTZ,
        timing_offsets=[0, 15, 0, 15, 0, 15, 0, 15, 0, 15, 0, 15, 0, 15, 0, 15],
        description="Waltz feel for 3/4 time",
    ),
}


class GrooveQuantizer:
    """
    Groove quantization processor.

    Applies groove templates to note timing and velocity with
    configurable intensity.
    """

    def __init__(self):
        self.current_groove: GrooveTemplate = GROOVE_TEMPLATES[GrooveType.OFF]
        self.intensity: float = 1.0  # 0.0 to 1.0
        self.enabled: bool = False
        self._random = random.Random()

    def set_groove(self, groove_type: GrooveType) -> bool:
        """Set the current groove template"""
        if groove_type in GROOVE_TEMPLATES:
            self.current_groove = GROOVE_TEMPLATES[groove_type]
            self.enabled = groove_type != GrooveType.OFF
            return True
        return False

    def set_groove_by_name(self, name: str) -> bool:
        """Set groove by name string"""
        for gt in GrooveType:
            if gt.value.lower() == name.lower():
                return self.set_groove(gt)
        return False

    def set_intensity(self, intensity: float):
        """Set groove intensity (0.0 to 1.0)"""
        self.intensity = max(0.0, min(1.0, intensity))

    def apply_timing_offset(
        self, tick_position: int, measure_position_16th: int
    ) -> int:
        """
        Apply groove timing offset to a tick position.

        Args:
            tick_position: Original tick position
            measure_position_16th: Position in 16th notes (0-15)

        Returns:
            Adjusted tick position
        """
        if not self.enabled or self.intensity == 0:
            return tick_position

        offset = self.current_groove.get_timing_offset(measure_position_16th)
        adjusted_offset = int(offset * self.intensity)

        return tick_position + adjusted_offset

    def apply_velocity_offset(self, velocity: int, measure_position_16th: int) -> int:
        """
        Apply groove velocity offset.

        Args:
            velocity: Original velocity (0-127)
            measure_position_16th: Position in 16th notes (0-15)

        Returns:
            Adjusted velocity
        """
        if not self.enabled or self.intensity == 0:
            return velocity

        offset = self.current_groove.get_velocity_offset(measure_position_16th)
        adjusted_offset = int(offset * self.intensity)

        return max(0, min(127, velocity + adjusted_offset))

    def get_available_grooves(self) -> list[dict[str, str]]:
        """Get list of available groove templates"""
        return [
            {
                "type": gt.value,
                "name": template.name,
                "description": template.description,
            }
            for gt, template in GROOVE_TEMPLATES.items()
        ]

    def get_status(self) -> dict:
        """Get current groove status"""
        return {
            "enabled": self.enabled,
            "groove_type": self.current_groove.groove_type.value,
            "groove_name": self.current_groove.name,
            "intensity": self.intensity,
        }


# Singleton instance for global use
_default_groove_quantizer = GrooveQuantizer()


def get_default_groove_quantizer() -> GrooveQuantizer:
    """Get the default groove quantizer instance"""
    return _default_groove_quantizer
