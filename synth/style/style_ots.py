"""
One Touch Settings (OTS) System

Provides quick voice preset functionality that links to styles.
Each style has multiple OTS presets that can be instantly recalled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OTSSection(Enum):
    """OTS section mappings"""

    INTRO = "intro"
    MAIN_A = "main_a"
    MAIN_B = "main_b"
    MAIN_C = "main_c"
    MAIN_D = "main_d"
    ENDING = "ending"


@dataclass(slots=True)
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

    def to_dict(self) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> OTSPart:
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


@dataclass(slots=True)
class OTSPreset:
    """
    Complete One Touch Setting preset.

    An OTS preset contains configuration for 4 parts plus
    master settings. Each style has multiple OTS presets
    (typically 4-8).
    """

    preset_id: int = 0
    name: str = "New OTS"
    parts: list[OTSPart] = field(default_factory=lambda: [OTSPart(i) for i in range(4)])

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

    linked_section: OTSSection | None = None

    # Extended fields
    description: str = ""
    color: str = "#FFFFFF"
    icon: str = ""
    category: str = "user"

    # Dual voice support
    dual_voice_enabled: bool = False
    dual_voice_part: int = -1
    dual_voice_octave: int = 0

    # Key on/off answer back
    key_on_answer: bool = True
    key_off_answer: bool = True

    def get_part(self, part_id: int) -> OTSPart:
        """Get part by ID"""
        for part in self.parts:
            if part.part_id == part_id:
                return part
        return OTSPart(part_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "category": self.category,
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
            "linked_section": self.linked_section.value if self.linked_section else None,
            "dual_voice_enabled": self.dual_voice_enabled,
            "dual_voice_part": self.dual_voice_part,
            "dual_voice_octave": self.dual_voice_octave,
            "key_on_answer": self.key_on_answer,
            "key_off_answer": self.key_off_answer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OTSPreset:
        parts = [OTSPart.from_dict(p) for p in data.get("parts", [])]
        while len(parts) < 4:
            parts.append(OTSPart(len(parts)))

        return cls(
            preset_id=data.get("preset_id", 0),
            name=data.get("name", "New OTS"),
            description=data.get("description", ""),
            color=data.get("color", "#FFFFFF"),
            icon=data.get("icon", ""),
            category=data.get("category", "user"),
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
            dual_voice_enabled=data.get("dual_voice_enabled", False),
            dual_voice_part=data.get("dual_voice_part", -1),
            dual_voice_octave=data.get("dual_voice_octave", 0),
            key_on_answer=data.get("key_on_answer", True),
            key_off_answer=data.get("key_off_answer", True),
        )


@dataclass(slots=True)
class OneTouchSettings:
    """
    Complete OTS management for a style.

    Contains multiple OTS presets (typically 4-8) and manages
    loading/applying them to the synthesizer.
    """

    presets: list[OTSPreset] = field(default_factory=list)
    active_preset_id: int = 0
    ots_link_enabled: bool = True

    _synthesizer: Any = field(default=None, repr=False)

    def __post_init__(self):
        if not self.presets:
            self._init_default_presets()

    def _init_default_presets(self):
        """Initialize default OTS presets (8 presets)"""
        preset_names = [
            "Piano",
            "Organ",
            "Strings",
            "Synth Pad",
            "Bass",
            "Guitar",
            "Brass",
            "Sax",
        ]
        for i in range(8):
            preset = OTSPreset(
                preset_id=i,
                name=preset_names[i] if i < len(preset_names) else f"OTS {i + 1}",
            )
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

    def get_preset(self, preset_id: int) -> OTSPreset | None:
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

    def link_preset_to_section(self, preset_id: int, section: OTSSection) -> bool:
        """Link an OTS preset to a specific section for auto-loading"""
        preset = self.get_preset(preset_id)
        if preset:
            preset.linked_section = section
            return True
        return False

    def get_preset_for_section(self, section: OTSSection) -> OTSPreset | None:
        """Get the OTS preset linked to a specific section"""
        for preset in self.presets:
            if preset.linked_section == section:
                return preset
        return None

    def auto_load_for_section(self, section_name: str) -> bool:
        """
        Automatically load OTS preset for a section if linked.

        Args:
            section_name: Name of the section (e.g., 'main_a', 'intro_1')

        Returns:
            True if a linked preset was found and loaded
        """
        if not self.ots_link_enabled:
            return False

        # Map section name to OTSSection
        section_map = {
            "intro": OTSSection.INTRO,
            "intro_1": OTSSection.INTRO,
            "intro_2": OTSSection.INTRO,
            "intro_3": OTSSection.INTRO,
            "main_a": OTSSection.MAIN_A,
            "main_b": OTSSection.MAIN_B,
            "main_c": OTSSection.MAIN_C,
            "main_d": OTSSection.MAIN_D,
            "ending": OTSSection.ENDING,
            "ending_1": OTSSection.ENDING,
            "ending_2": OTSSection.ENDING,
            "ending_3": OTSSection.ENDING,
        }

        ots_section = section_map.get(section_name.lower())
        if ots_section:
            preset = self.get_preset_for_section(ots_section)
            if preset:
                self.activate_preset(preset.preset_id)
                return True

        return False

    def store_current_to_preset(self, preset_id: int, name: str = "") -> bool:
        """
        Store current synthesizer state to a preset.

        Args:
            preset_id: Target preset ID
            name: Optional new name

        Returns:
            True if successful
        """
        preset = self.get_preset(preset_id)
        if not preset or not self._synthesizer:
            return False

        if name:
            preset.name = name

        try:
            if hasattr(self._synthesizer, "get_parts_state"):
                parts_state = self._synthesizer.get_parts_state()

                for part_id, part_state in enumerate(parts_state[:4]):
                    if part_id < len(preset.parts):
                        part = preset.parts[part_id]

                        if "program" in part_state:
                            prog = part_state["program"]
                            part.program_change = prog & 0x7F
                            part.bank_msb = (prog >> 16) & 0x7F
                            part.bank_lsb = (prog >> 8) & 0x7F

                        if "volume" in part_state:
                            part.volume = part_state["volume"]

                        if "pan" in part_state:
                            part.pan = part_state["pan"]

                        if "reverb_send" in part_state:
                            part.reverb_send = part_state["reverb_send"]

                        if "chorus_send" in part_state:
                            part.chorus_send = part_state["chorus_send"]

                        if "variation_send" in part_state:
                            part.variation_send = part_state["variation_send"]

                        if "enabled" in part_state:
                            part.enabled = part_state["enabled"]

                        if "octave_shift" in part_state:
                            part.octave_shift = part_state["octave_shift"]

                        if "velocity_limit_low" in part_state:
                            part.velocity_limit_low = part_state["velocity_limit_low"]

                        if "velocity_limit_high" in part_state:
                            part.velocity_limit_high = part_state["velocity_limit_high"]

            if hasattr(self._synthesizer, "get_master_volume"):
                preset.master_volume = self._synthesizer.get_master_volume()

            if hasattr(self._synthesizer, "get_tempo"):
                preset.tempo = self._synthesizer.get_tempo()

            if hasattr(self._synthesizer, "get_time_signature"):
                time_sig = self._synthesizer.get_time_signature()
                preset.time_signature_numerator = time_sig[0]
                preset.time_signature_denominator = time_sig[1]

            return True

        except Exception as e:
            print(f"Error storing to preset: {e}")
            return False

    def get_preset_names(self) -> list[str]:
        """Get list of all preset names"""
        return [p.name for p in self.presets]

    def to_dict(self) -> dict[str, Any]:
        return {
            "presets": [p.to_dict() for p in self.presets],
            "active_preset_id": self.active_preset_id,
            "ots_link_enabled": self.ots_link_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], synthesizer: Any = None) -> OneTouchSettings:
        presets = [OTSPreset.from_dict(p) for p in data.get("presets", [])]
        ots = cls(
            presets=presets,
            active_preset_id=data.get("active_preset_id", 0),
            ots_link_enabled=data.get("ots_link_enabled", True),
            _synthesizer=synthesizer,
        )
        return ots

    def get_status(self) -> dict[str, Any]:
        """Get OTS status"""
        return {
            "active_preset_id": self.active_preset_id,
            "active_preset_name": self.active_preset.name,
            "total_presets": len(self.presets),
            "ots_link_enabled": self.ots_link_enabled,
        }
