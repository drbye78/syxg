"""
Registration Memory System

Provides bank/memory recall functionality for storing and recalling
complete panel setups.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json


class RegistrationParameter(Enum):
    """Types of parameters that can be stored in registration"""

    VOICE = "voice"
    STYLE = "style"
    OTS = "ots"
    TEMPO = "tempo"
    TRANSPOSE = "transpose"
    TUNE = "tune"
    VOLUME_MASTER = "volume_master"
    VOLUME_STYLE = "volume_style"
    VOLUME_VOICE = "volume_voice"
    REVERB = "reverb"
    CHORUS = "chorus"
    VARIATION = "variation"
    MASTER_EFFECT = "master_effect"
    SCALE = "scale"
    TUNING = "tuning"
    FOOTSWITCH = "footswitch"
    KNOB_ASSIGNMENT = "knob_assignment"


@dataclass
class Registration:
    """
    Single registration memory entry.

    Stores complete panel setup including voices, style, effects, etc.
    """

    slot_id: int = 0
    name: str = "New Registration"

    voice_parts: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    style_name: str = ""
    style_tempo: int = 120
    ots_preset: int = 0

    transpose: int = 0
    tune: int = 0

    master_volume: int = 100
    style_volume: int = 100
    voice_volume: int = 100

    reverb_type: int = 0
    reverb_parameter: int = 64
    chorus_type: int = 0
    chorus_parameter: int = 64
    variation_type: int = 0
    variation_parameter: int = 64

    scale_type: str = "equal"
    micro_tuning: Dict[str, Any] = field(default_factory=dict)

    custom_parameters: Dict[str, Any] = field(default_factory=dict)

    color: str = "#FFFFFF"
    icon: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "name": self.name,
            "voice_parts": self.voice_parts,
            "style_name": self.style_name,
            "style_tempo": self.style_tempo,
            "ots_preset": self.ots_preset,
            "transpose": self.transpose,
            "tune": self.tune,
            "master_volume": self.master_volume,
            "style_volume": self.style_volume,
            "voice_volume": self.voice_volume,
            "reverb_type": self.reverb_type,
            "reverb_parameter": self.reverb_parameter,
            "chorus_type": self.chorus_type,
            "chorus_parameter": self.chorus_parameter,
            "variation_type": self.variation_type,
            "variation_parameter": self.variation_parameter,
            "scale_type": self.scale_type,
            "micro_tuning": self.micro_tuning,
            "custom_parameters": self.custom_parameters,
            "color": self.color,
            "icon": self.icon,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Registration":
        return cls(
            slot_id=data.get("slot_id", 0),
            name=data.get("name", "New Registration"),
            voice_parts=data.get("voice_parts", {}),
            style_name=data.get("style_name", ""),
            style_tempo=data.get("style_tempo", 120),
            ots_preset=data.get("ots_preset", 0),
            transpose=data.get("transpose", 0),
            tune=data.get("tune", 0),
            master_volume=data.get("master_volume", 100),
            style_volume=data.get("style_volume", 100),
            voice_volume=data.get("voice_volume", 100),
            reverb_type=data.get("reverb_type", 0),
            reverb_parameter=data.get("reverb_parameter", 64),
            chorus_type=data.get("chorus_type", 0),
            chorus_parameter=data.get("chorus_parameter", 64),
            variation_type=data.get("variation_type", 0),
            variation_parameter=data.get("variation_parameter", 64),
            scale_type=data.get("scale_type", "equal"),
            micro_tuning=data.get("micro_tuning", {}),
            custom_parameters=data.get("custom_parameters", {}),
            color=data.get("color", "#FFFFFF"),
            icon=data.get("icon", ""),
        )


@dataclass
class RegistrationBank:
    """A bank containing multiple registration slots"""

    bank_id: int = 0
    name: str = "Bank 1"
    registrations: List[Registration] = field(default_factory=list)
    _on_change_callback: Optional[Callable] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.registrations:
            self.registrations = [Registration(slot_id=i) for i in range(16)]

    @property
    def slot_count(self) -> int:
        return len(self.registrations)

    def get_registration(self, slot: int) -> Optional[Registration]:
        """Get registration by slot number"""
        for reg in self.registrations:
            if reg.slot_id == slot:
                return reg
        return None

    def set_registration(self, slot: int, registration: Registration):
        """Set registration in a slot"""
        for i, reg in enumerate(self.registrations):
            if reg.slot_id == slot:
                self.registrations[i] = registration
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "name": self.name,
            "registrations": [r.to_dict() for r in self.registrations],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistrationBank":
        registrations = [
            Registration.from_dict(r) for r in data.get("registrations", [])
        ]
        return cls(
            bank_id=data.get("bank_id", 0),
            name=data.get("name", "Bank 1"),
            registrations=registrations,
        )


class RegistrationMemory:
    """
    Complete registration memory system.

    Manages multiple banks of registrations with save/load functionality.
    """

    def __init__(self, num_banks: int = 8, slots_per_bank: int = 16):
        self.num_banks = num_banks
        self.slots_per_bank = slots_per_bank

        self._banks: Dict[int, RegistrationBank] = {}
        self._current_bank: int = 0
        self._current_slot: int = 0

        self._synthesizer: Any = None

        self._initialize_banks()

        self._on_recall_callback: Optional[Callable[[Registration], None]] = None
        self._on_store_callback: Optional[Callable[[int, int, Registration], None]] = (
            None
        )

    def _initialize_banks(self):
        """Initialize all banks"""
        for i in range(self.num_banks):
            self._banks[i] = RegistrationBank(bank_id=i, name=f"Bank {i + 1}")

    def set_synthesizer(self, synthesizer: Any):
        """Set synthesizer for registration recall"""
        self._synthesizer = synthesizer

    def get_current_bank(self) -> RegistrationBank:
        """Get current bank"""
        return self._banks.get(self._current_bank, self._banks[0])

    def set_bank(self, bank_id: int) -> bool:
        """Set current bank"""
        if 0 <= bank_id < self.num_banks:
            self._current_bank = bank_id
            return True
        return False

    def next_bank(self):
        """Advance to next bank"""
        self._current_bank = (self._current_bank + 1) % self.num_banks

    def previous_bank(self):
        """Go to previous bank"""
        self._current_bank = (self._current_bank - 1) % self.num_banks

    def set_slot(self, slot: int) -> bool:
        """Set current slot"""
        if 0 <= slot < self.slots_per_bank:
            self._current_slot = slot
            return True
        return False

    def next_slot(self):
        """Advance to next slot"""
        self._current_slot = (self._current_slot + 1) % self.slots_per_bank

    def previous_slot(self):
        """Go to previous slot"""
        self._current_slot = (self._current_slot - 1) % self.slots_per_bank

    def get_current_registration(self) -> Optional[Registration]:
        """Get current registration"""
        bank = self.get_current_bank()
        return bank.get_registration(self._current_slot)

    def recall(self, bank: Optional[int] = None, slot: Optional[int] = None) -> bool:
        """Recall a registration"""
        target_bank = bank if bank is not None else self._current_bank
        target_slot = slot if slot is not None else self._current_slot

        reg = self.get_current_bank().get_registration(target_slot)
        if not reg:
            return False

        self._current_bank = target_bank
        self._current_slot = target_slot

        if self._synthesizer:
            self._apply_registration(reg)

        if self._on_recall_callback:
            self._on_recall_callback(reg)

        return True

    def _apply_registration(self, reg: Registration):
        """Apply registration to synthesizer"""
        if not self._synthesizer:
            return

        for part_id, voice_data in reg.voice_parts.items():
            try:
                channel = part_id
                program = voice_data.get("program", 0)
                bank_msb = voice_data.get("bank_msb", 0)
                bank_lsb = voice_data.get("bank_lsb", 0)
                volume = voice_data.get("volume", 100)
                pan = voice_data.get("pan", 64)

                self._synthesizer.program_change(channel, program, bank_msb, bank_lsb)
                self._synthesizer.control_change(channel, 7, volume)
                self._synthesizer.control_change(channel, 10, pan)
            except Exception:
                pass

    def store(
        self, name: str = "", bank: Optional[int] = None, slot: Optional[int] = None
    ) -> bool:
        """Store current setup to a registration"""
        target_bank = bank if bank is not None else self._current_bank
        target_slot = slot if slot is not None else self._current_slot

        if target_bank not in self._banks:
            return False

        reg = self._create_registration_from_current(target_slot, name)
        return self._banks[target_bank].set_registration(target_slot, reg)

    def _create_registration_from_current(self, slot: int, name: str) -> Registration:
        """Create registration from current synthesizer state"""
        reg = Registration(slot_id=slot, name=name or f"Registration {slot + 1}")

        if self._synthesizer:
            try:
                if hasattr(self._synthesizer, "channels"):
                    for i, channel in enumerate(self._synthesizer.channels[:16]):
                        reg.voice_parts[i] = {
                            "program": getattr(channel, "program", 0),
                            "bank_msb": getattr(channel, "bank_msb", 0),
                            "bank_lsb": getattr(channel, "bank_lsb", 0),
                            "volume": getattr(channel, "volume", 100),
                            "pan": getattr(channel, "pan", 64),
                        }
            except Exception:
                pass

        return reg

    def copy_slot(
        self, from_bank: int, from_slot: int, to_bank: int, to_slot: int
    ) -> bool:
        """Copy registration from one slot to another"""
        source = self._banks.get(from_bank)
        if not source:
            return False

        source_reg = source.get_registration(from_slot)
        if not source_reg:
            return False

        dest = self._banks.get(to_bank)
        if not dest:
            return False

        new_reg = Registration.from_dict(source_reg.to_dict())
        new_reg.slot_id = to_slot
        return dest.set_registration(to_slot, new_reg)

    def clear_slot(
        self, bank: Optional[int] = None, slot: Optional[int] = None
    ) -> bool:
        """Clear a registration slot"""
        target_bank = bank if bank is not None else self._current_bank
        target_slot = slot if slot is not None else self._current_slot

        bank_obj = self._banks.get(target_bank)
        if not bank_obj:
            return False

        bank_obj.set_registration(target_slot, Registration(slot_id=target_slot))
        return True

    def set_recall_callback(self, callback: Callable[[Registration], None]):
        """Set callback for registration recall"""
        self._on_recall_callback = callback

    def set_store_callback(self, callback: Callable[[int, int, Registration], None]):
        """Set callback for registration store"""
        self._on_store_callback = callback

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary"""
        return {
            "num_banks": self.num_banks,
            "slots_per_bank": self.slots_per_bank,
            "current_bank": self._current_bank,
            "current_slot": self._current_slot,
            "banks": {k: v.to_dict() for k, v in self._banks.items()},
        }

    def save_to_file(self, filepath: str):
        """Save to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistrationMemory":
        """Create from dictionary"""
        mem = cls(
            num_banks=data.get("num_banks", 8),
            slots_per_bank=data.get("slots_per_bank", 16),
        )

        banks_data = data.get("banks", {})
        for bank_id, bank_data in banks_data.items():
            mem._banks[int(bank_id)] = RegistrationBank.from_dict(bank_data)

        mem._current_bank = data.get("current_bank", 0)
        mem._current_slot = data.get("current_slot", 0)

        return mem

    @classmethod
    def load_from_file(cls, filepath: str) -> "RegistrationMemory":
        """Load from JSON file"""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_status(self) -> Dict[str, Any]:
        """Get registration memory status"""
        current = self.get_current_registration()
        return {
            "current_bank": self._current_bank,
            "current_slot": self._current_slot,
            "current_registration": current.name if current else None,
            "total_banks": self.num_banks,
            "slots_per_bank": self.slots_per_bank,
        }
