"""
Registration Memory System - Enhanced

Provides bank/memory recall functionality for storing and recalling
complete panel setups.

Features:
- 8 banks × 16 slots = 128 registration memories
- Freeze function (selectively exclude parameters from recall)
- Copy/move/swap operations
- File I/O (JSON format)
- Callback system for recall/store events
- Thread-safe operations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
import json
import threading
import time


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
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    freeze_mask: Set[RegistrationParameter] = field(default_factory=set)

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
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "freeze_mask": list(self.freeze_mask),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Registration":
        freeze_mask = set()
        for p_value in data.get("freeze_mask", []):
            try:
                freeze_mask.add(RegistrationParameter(p_value))
            except ValueError:
                pass
        
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
            created_at=data.get("created_at", time.time()),
            modified_at=data.get("modified_at", time.time()),
            freeze_mask=freeze_mask,
        )
    
    def set_freeze(self, parameter: RegistrationParameter, frozen: bool) -> None:
        if frozen:
            self.freeze_mask.add(parameter)
        else:
            self.freeze_mask.discard(parameter)
        self.modified_at = time.time()
    
    def is_frozen(self, parameter: RegistrationParameter) -> bool:
        return parameter in self.freeze_mask


@dataclass
class RegistrationBank:
    """A bank containing multiple registration slots"""

    bank_id: int = 0
    name: str = "Bank 1"
    registrations: List[Registration] = field(default_factory=list)

    def __post_init__(self):
        if not self.registrations:
            self.registrations = [Registration(slot_id=i) for i in range(16)]

    def get_registration(self, slot: int) -> Optional[Registration]:
        for reg in self.registrations:
            if reg.slot_id == slot:
                return reg
        return None

    def set_registration(self, slot: int, registration: Registration) -> bool:
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
        registrations = [Registration.from_dict(r) for r in data.get("registrations", [])]
        return cls(
            bank_id=data.get("bank_id", 0),
            name=data.get("name", "Bank 1"),
            registrations=registrations,
        )


class RegistrationMemory:
    """Complete registration memory system."""

    def __init__(self, num_banks: int = 8, slots_per_bank: int = 16):
        self.num_banks = num_banks
        self.slots_per_bank = slots_per_bank
        self._lock = threading.RLock()
        self._banks: Dict[int, RegistrationBank] = {}
        self._current_bank: int = 0
        self._current_slot: int = 0
        self._synthesizer: Any = None
        self._style_player: Any = None
        self._ots: Any = None
        self._global_freeze: Set[RegistrationParameter] = set()
        self._on_recall_callback: Optional[Callable[[Registration], None]] = None
        self._on_store_callback: Optional[Callable[[int, int, Registration], None]] = None
        self._on_change_callback: Optional[Callable[[], None]] = None
        self._initialize_banks()

    def _initialize_banks(self):
        with self._lock:
            for i in range(self.num_banks):
                self._banks[i] = RegistrationBank(bank_id=i, name=f"Bank {i + 1}")

    def set_synthesizer(self, synthesizer: Any):
        self._synthesizer = synthesizer

    def set_style_player(self, style_player: Any):
        self._style_player = style_player

    def set_ots(self, ots: Any):
        self._ots = ots

    def get_current_bank(self) -> RegistrationBank:
        with self._lock:
            return self._banks.get(self._current_bank, self._banks[0])

    def set_bank(self, bank_id: int) -> bool:
        with self._lock:
            if 0 <= bank_id < self.num_banks:
                self._current_bank = bank_id
                self._notify_change()
                return True
            return False

    def next_bank(self):
        with self._lock:
            self._current_bank = (self._current_bank + 1) % self.num_banks
            self._notify_change()

    def previous_bank(self):
        with self._lock:
            self._current_bank = (self._current_bank - 1) % self.num_banks
            self._notify_change()

    def set_slot(self, slot: int) -> bool:
        with self._lock:
            if 0 <= slot < self.slots_per_bank:
                self._current_slot = slot
                self._notify_change()
                return True
            return False

    def next_slot(self):
        with self._lock:
            self._current_slot = (self._current_slot + 1) % self.slots_per_bank
            self._notify_change()

    def previous_slot(self):
        with self._lock:
            self._current_slot = (self._current_slot - 1) % self.slots_per_bank
            self._notify_change()

    def get_current_registration(self) -> Optional[Registration]:
        with self._lock:
            bank = self.get_current_bank()
            return bank.get_registration(self._current_slot)

    def recall(self, bank: Optional[int] = None, slot: Optional[int] = None, 
               ignore_freeze: bool = False) -> bool:
        with self._lock:
            target_bank = bank if bank is not None else self._current_bank
            target_slot = slot if slot is not None else self._current_slot
            bank_obj = self._banks.get(target_bank)
            if not bank_obj:
                return False
            reg = bank_obj.get_registration(target_slot)
            if not reg:
                return False
            self._current_bank = target_bank
            self._current_slot = target_slot
            if self._synthesizer:
                self._apply_registration(reg, ignore_freeze)
            if self._on_recall_callback:
                self._on_recall_callback(reg)
            self._notify_change()
            return True

    def _apply_registration(self, reg: Registration, ignore_freeze: bool = False):
        if not self._synthesizer:
            return
        
        def is_frozen(param: RegistrationParameter) -> bool:
            if ignore_freeze:
                return False
            if param in self._global_freeze:
                return True
            if reg.is_frozen(param):
                return True
            return False

        if not is_frozen(RegistrationParameter.VOICE):
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

        if not is_frozen(RegistrationParameter.STYLE) and self._style_player:
            try:
                if reg.style_tempo != 120:
                    self._style_player.tempo = reg.style_tempo
            except Exception:
                pass

        if not is_frozen(RegistrationParameter.OTS) and self._ots:
            try:
                self._ots.activate_preset(reg.ots_preset)
            except Exception:
                pass

        if not is_frozen(RegistrationParameter.TRANSPOSE):
            try:
                if hasattr(self._synthesizer, 'set_transpose'):
                    self._synthesizer.set_transpose(reg.transpose)
            except Exception:
                pass

        if not is_frozen(RegistrationParameter.VOLUME_MASTER):
            try:
                if hasattr(self._synthesizer, 'set_master_volume'):
                    self._synthesizer.set_master_volume(reg.master_volume)
            except Exception:
                pass

    def store(self, name: str = "", bank: Optional[int] = None, 
              slot: Optional[int] = None, capture_all: bool = True) -> bool:
        with self._lock:
            target_bank = bank if bank is not None else self._current_bank
            target_slot = slot if slot is not None else self._current_slot
            if target_bank not in self._banks:
                return False
            reg = self._create_registration_from_current(target_slot, name, capture_all)
            result = self._banks[target_bank].set_registration(target_slot, reg)
            if result and self._on_store_callback:
                self._on_store_callback(target_bank, target_slot, reg)
            self._notify_change()
            return result

    def _create_registration_from_current(self, slot: int, name: str, 
                                          capture_all: bool = True) -> Registration:
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
        if self._style_player and (capture_all or RegistrationParameter.STYLE not in self._global_freeze):
            reg.style_tempo = int(getattr(self._style_player, "tempo", 120))
        if self._ots and (capture_all or RegistrationParameter.OTS not in self._global_freeze):
            reg.ots_preset = getattr(self._ots, "active_preset_id", 0)
        return reg

    def copy_slot(self, from_bank: int, from_slot: int, to_bank: int, to_slot: int) -> bool:
        with self._lock:
            import copy
            source = self._banks.get(from_bank)
            if not source:
                return False
            source_reg = source.get_registration(from_slot)
            if not source_reg:
                return False
            dest = self._banks.get(to_bank)
            if not dest:
                return False
            new_reg = copy.deepcopy(source_reg)
            new_reg.slot_id = to_slot
            new_reg.modified_at = time.time()
            return dest.set_registration(to_slot, new_reg)

    def swap_slots(self, bank1: int, slot1: int, bank2: int, slot2: int) -> bool:
        with self._lock:
            import copy
            bank1_obj = self._banks.get(bank1)
            bank2_obj = self._banks.get(bank2)
            if not bank1_obj or not bank2_obj:
                return False
            reg1 = bank1_obj.get_registration(slot1)
            reg2 = bank2_obj.get_registration(slot2)
            if not reg1 or not reg2:
                return False
            temp = copy.deepcopy(reg1)
            temp.slot_id = slot2
            reg2.slot_id = slot1
            reg1.slot_id = slot2
            bank1_obj.set_registration(slot1, reg2)
            bank2_obj.set_registration(slot2, temp)
            self._notify_change()
            return True

    def clear_slot(self, bank: Optional[int] = None, slot: Optional[int] = None) -> bool:
        with self._lock:
            target_bank = bank if bank is not None else self._current_bank
            target_slot = slot if slot is not None else self._current_slot
            bank_obj = self._banks.get(target_bank)
            if not bank_obj:
                return False
            empty_reg = Registration(slot_id=target_slot, name="Empty")
            bank_obj.set_registration(target_slot, empty_reg)
            self._notify_change()
            return True

    def set_global_freeze(self, parameter: RegistrationParameter, frozen: bool) -> None:
        with self._lock:
            if frozen:
                self._global_freeze.add(parameter)
            else:
                self._global_freeze.discard(parameter)

    def get_global_freeze(self) -> Set[RegistrationParameter]:
        with self._lock:
            return self._global_freeze.copy()

    def clear_global_freeze(self) -> None:
        with self._lock:
            self._global_freeze.clear()

    def set_recall_callback(self, callback: Callable[[Registration], None]):
        self._on_recall_callback = callback

    def set_store_callback(self, callback: Callable[[int, int, Registration], None]):
        self._on_store_callback = callback

    def set_change_callback(self, callback: Callable[[], None]):
        self._on_change_callback = callback

    def _notify_change(self):
        if self._on_change_callback:
            try:
                self._on_change_callback()
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "num_banks": self.num_banks,
                "slots_per_bank": self.slots_per_bank,
                "current_bank": self._current_bank,
                "current_slot": self._current_slot,
                "global_freeze": [p.value for p in self._global_freeze],
                "banks": {k: v.to_dict() for k, v in self._banks.items()},
            }

    def save_to_file(self, filepath: str) -> bool:
        try:
            with open(filepath, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> Optional["RegistrationMemory"]:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            mem = cls(
                num_banks=data.get("num_banks", 8),
                slots_per_bank=data.get("slots_per_bank", 16),
            )
            for p_value in data.get("global_freeze", []):
                try:
                    mem._global_freeze.add(RegistrationParameter(p_value))
                except ValueError:
                    pass
            banks_data = data.get("banks", {})
            for bank_id, bank_data in banks_data.items():
                mem._banks[int(bank_id)] = RegistrationBank.from_dict(bank_data)
            mem._current_bank = data.get("current_bank", 0)
            mem._current_slot = data.get("current_slot", 0)
            return mem
        except Exception:
            return None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            current = self.get_current_registration()
            return {
                "current_bank": self._current_bank,
                "current_slot": self._current_slot,
                "current_registration": current.name if current else None,
                "total_banks": self.num_banks,
                "slots_per_bank": self.slots_per_bank,
                "global_freeze": [p.value for p in self._global_freeze],
            }
