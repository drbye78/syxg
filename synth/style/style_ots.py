"""
One Touch Settings (OTS) System

Provides quick voice preset functionality that links to styles.
Each style has multiple OTS presets that can be instantly recalled.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class OTSSection(Enum):
    """OTS section mappings"""

    INTRO = "intro"
    MAIN_A = "main_a"
    MAIN_B = "main_b"
    MAIN_C = "main_c"
    MAIN_D = "main_d"
    ENDING = "ending"


@dataclass
class OTSPart:
    """
    Single part configuration within an OTS preset.

    Each OTS has 4 parts that can be configured independently.
    """

    part_id: int = 0
    enabled: bool = True
    program_change: int = 0
    bank_msb: int = 0
    bank_lsb: int = 0
    volume: int = 100
    pan: int = 64
    reverb_send: int = 40
    chorus_send: int = 0
    variation_send: int = 0
    octave_shift: int = 0
    velocity_limit_low: int = 1
    velocity_limit_high: int = 127
    assign_type: str = "normal"

    @property
    def program(self) -> int:
        return (self.bank_msb << 16) | (self.bank_lsb << 8) | self.program_change

    @property
    def midi_channel(self) -> int:
        return self.part_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_id": self.part_id,
            "enabled": self.enabled,
            "program_change": self.program_change,
            "bank_msb": self.bank_msb,
            "bank_lsb": self.bank_lsb,
            "volume": self.volume,
            "pan": self.pan,
            "reverb_send": self.reverb_send,
            "chorus_send": self.chorus_send,
            "variation_send": self.variation_send,
            "octave_shift": self.octave_shift,
            "velocity_limit_low": self.velocity_limit_low,
            "velocity_limit_high": self.velocity_limit_high,
            "assign_type": self.assign_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OTSPart":
        return cls(
            part_id=data.get("part_id", 0),
            enabled=data.get("enabled", True),
            program_change=data.get("program_change", 0),
            bank_msb=data.get("bank_msb", 0),
            bank_lsb=data.get("bank_lsb", 0),
            volume=data.get("volume", 100),
            pan=data.get("pan", 64),
            reverb_send=data.get("reverb_send", 40),
            chorus_send=data.get("chorus_send", 0),
            variation_send=data.get("variation_send", 0),
            octave_shift=data.get("octave_shift", 0),
            velocity_limit_low=data.get("velocity_limit_low", 1),
            velocity_limit_high=data.get("velocity_limit_high", 127),
            assign_type=data.get("assign_type", "normal"),
        )


@dataclass
class OTSPreset:
    """
    Complete One Touch Setting preset.

    An OTS preset contains configuration for 4 parts plus
    master settings. Each style has multiple OTS presets
    (typically 4-8).
    """

    preset_id: int = 0
    name: str = "New OTS"
    parts: List[OTSPart] = field(default_factory=lambda: [OTSPart(i) for i in range(4)])

    master_volume: int = 100
    master_tempo: int = 0
    master_transpose: int = 0
    master_tune: int = 0

    reverb_type: int = 0
    reverb_parameter: int = 64
    chorus_type: int = 0
    chorus_parameter: int = 64
    variation_type: int = 0
    variation_parameter: int = 64

    linked_section: Optional[OTSSection] = None

    def get_part(self, part_id: int) -> OTSPart:
        """Get part by ID"""
        for part in self.parts:
            if part.part_id == part_id:
                return part
        return OTSPart(part_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "parts": [p.to_dict() for p in self.parts],
            "master_volume": self.master_volume,
            "master_tempo": self.master_tempo,
            "master_transpose": self.master_transpose,
            "master_tune": self.master_tune,
            "reverb_type": self.reverb_type,
            "reverb_parameter": self.reverb_parameter,
            "chorus_type": self.chorus_type,
            "chorus_parameter": self.chorus_parameter,
            "variation_type": self.variation_type,
            "variation_parameter": self.variation_parameter,
            "linked_section": self.linked_section.value
            if self.linked_section
            else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OTSPreset":
        parts = [OTSPart.from_dict(p) for p in data.get("parts", [])]
        while len(parts) < 4:
            parts.append(OTSPart(len(parts)))

        return cls(
            preset_id=data.get("preset_id", 0),
            name=data.get("name", "New OTS"),
            parts=parts,
            master_volume=data.get("master_volume", 100),
            master_tempo=data.get("master_tempo", 0),
            master_transpose=data.get("master_transpose", 0),
            master_tune=data.get("master_tune", 0),
            reverb_type=data.get("reverb_type", 0),
            reverb_parameter=data.get("reverb_parameter", 64),
            chorus_type=data.get("chorus_type", 0),
            chorus_parameter=data.get("chorus_parameter", 64),
            variation_type=data.get("variation_type", 0),
            variation_parameter=data.get("variation_parameter", 64),
            linked_section=OTSSection(data["linked_section"])
            if data.get("linked_section")
            else None,
        )


@dataclass
class OneTouchSettings:
    """
    Complete OTS management for a style.

    Contains multiple OTS presets (typically 4-8) and manages
    loading/applying them to the synthesizer.
    """

    presets: List[OTSPreset] = field(default_factory=list)
    active_preset_id: int = 0
    ots_link_enabled: bool = True

    _synthesizer: Any = field(default=None, repr=False)

    def __post_init__(self):
        if not self.presets:
            self._init_default_presets()

    def _init_default_presets(self):
        """Initialize default OTS presets"""
        for i in range(4):
            preset = OTSPreset(preset_id=i, name=f"OTS {i + 1}")
            self.presets.append(preset)

    @property
    def active_preset(self) -> OTSPreset:
        """Get currently active preset"""
        for preset in self.presets:
            if preset.preset_id == self.active_preset_id:
                return preset
        return self.presets[0]

    def set_synthesizer(self, synthesizer: Any):
        """Set synthesizer reference for applying OTS"""
        self._synthesizer = synthesizer

    def activate_preset(self, preset_id: int) -> bool:
        """Activate an OTS preset"""
        for preset in self.presets:
            if preset.preset_id == preset_id:
                self.active_preset_id = preset_id
                if self._synthesizer:
                    self._apply_preset(preset)
                return True
        return False

    def next_preset(self):
        """Activate next OTS preset"""
        next_id = (self.active_preset_id + 1) % len(self.presets)
        self.activate_preset(next_id)

    def previous_preset(self):
        """Activate previous OTS preset"""
        prev_id = (self.active_preset_id - 1) % len(self.presets)
        self.activate_preset(prev_id)

    def _apply_preset(self, preset: OTSPreset):
        """Apply OTS preset to synthesizer"""
        if not self._synthesizer:
            return

        for part in preset.parts:
            if not part.enabled:
                continue

            channel = part.midi_channel

            try:
                self._synthesizer.program_change(
                    channel, part.program_change, part.bank_msb, part.bank_lsb
                )
                self._synthesizer.control_change(channel, 7, part.volume)
                self._synthesizer.control_change(channel, 10, part.pan)
                self._synthesizer.control_change(channel, 91, part.reverb_send)
                self._synthesizer.control_change(channel, 93, part.chorus_send)
            except Exception:
                pass

    def get_preset(self, preset_id: int) -> Optional[OTSPreset]:
        """Get preset by ID"""
        for preset in self.presets:
            if preset.preset_id == preset_id:
                return preset
        return None

    def add_preset(self, preset: OTSPreset):
        """Add a new OTS preset"""
        if len(self.presets) < 16:
            self.presets.append(preset)

    def remove_preset(self, preset_id: int) -> bool:
        """Remove an OTS preset"""
        for i, preset in enumerate(self.presets):
            if preset.preset_id == preset_id:
                self.presets.pop(i)
                return True
        return False

    def copy_preset(self, source_id: int, dest_id: int) -> bool:
        """Copy one preset to another"""
        source = self.get_preset(source_id)
        if not source:
            return False

        dest = self.get_preset(dest_id)
        if dest:
            dest.parts = [p for p in source.parts]
            dest.master_volume = source.master_volume
            dest.master_tempo = source.master_tempo
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "presets": [p.to_dict() for p in self.presets],
            "active_preset_id": self.active_preset_id,
            "ots_link_enabled": self.ots_link_enabled,
        }

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], synthesizer: Any = None
    ) -> "OneTouchSettings":
        presets = [OTSPreset.from_dict(p) for p in data.get("presets", [])]
        ots = cls(
            presets=presets,
            active_preset_id=data.get("active_preset_id", 0),
            ots_link_enabled=data.get("ots_link_enabled", True),
            _synthesizer=synthesizer,
        )
        return ots

    def get_status(self) -> Dict[str, Any]:
        """Get OTS status"""
        return {
            "active_preset_id": self.active_preset_id,
            "active_preset_name": self.active_preset.name,
            "total_presets": len(self.presets),
            "ots_link_enabled": self.ots_link_enabled,
        }
