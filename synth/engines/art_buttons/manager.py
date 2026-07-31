"""ART Button Manager — per-voice 3-slot assignable button system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TriggerMode(StrEnum):
    ONE_SHOT = "one_shot"           # Press → play effect, red while active
    HOLD_TRANSFORM = "hold_transform"  # Hold → voice changes; release → normal
    NOTE_EVENT = "note_event"       # Press → flash → next note-on fires effect


@dataclass(slots=True)
class ArtButtonSlot:
    articulation: str = "normal"
    mode: TriggerMode = TriggerMode.ONE_SHOT
    active: bool = False
    flashing: bool = False


@dataclass(slots=True)
class ArtButtonManager:
    """Per-voice 3-slot assignable ART button system.

    Usage:
        mgr = ArtButtonManager()
        mgr.assign(1, "harmonics", TriggerMode.HOLD_TRANSFORM)
        mgr.press(1)  # hold button 1 → voice plays harmonics
        articulation = mgr.get_active_articulation()  # "harmonics"
        mgr.release(1)
    """

    slots: dict[int, ArtButtonSlot] = field(default_factory=lambda: {
        1: ArtButtonSlot(),
        2: ArtButtonSlot(),
        3: ArtButtonSlot(),
    })

    def assign(self, slot: int, articulation: str, mode: TriggerMode) -> None:
        """Assign an articulation to a button slot.

        Args:
            slot: Button number (1-3).
            articulation: Articulation name to trigger.
            mode: Trigger behavior for this slot.
        """
        if slot not in (1, 2, 3):
            raise ValueError(f"Invalid slot: {slot}. Must be 1, 2, or 3.")
        self.slots[slot] = ArtButtonSlot(articulation=articulation, mode=mode)

    def press(self, slot: int) -> None:
        """Press an ART button."""
        slot_obj = self.slots.get(slot)
        if slot_obj is None:
            return
        if slot_obj.mode == TriggerMode.NOTE_EVENT:
            slot_obj.flashing = True
        else:
            slot_obj.active = True

    def release(self, slot: int) -> None:
        """Release an ART button."""
        slot_obj = self.slots.get(slot)
        if slot_obj is None:
            return
        if slot_obj.mode == TriggerMode.HOLD_TRANSFORM:
            slot_obj.active = False
        elif slot_obj.mode == TriggerMode.ONE_SHOT and slot_obj.active:
            slot_obj.active = False

    def get_active_articulation(self) -> str | None:
        """Get the currently active articulation from held or flashing buttons.

        Returns:
            Articulation name if any button is active, None otherwise.
            ONE_SHOT and HOLD_TRANSFORM buttons with active=True take priority.
            NOTE_EVENT buttons with flashing=True return their articulation
            but do NOT auto-clear — the caller must call consume_note_event().
        """
        for slot_obj in self.slots.values():
            if slot_obj.active:
                return slot_obj.articulation
        for slot_obj in self.slots.values():
            if slot_obj.flashing:
                return slot_obj.articulation
        return None

    def consume_note_event(self) -> str | None:
        """Fire a NOTE_EVENT button and clear its flashing state.

        Call at note-on after checking get_active_articulation().
        """
        for slot_obj in self.slots.values():
            if slot_obj.flashing:
                slot_obj.flashing = False
                return slot_obj.articulation
        return None

    def reset(self) -> None:
        """Reset all slots to default state."""
        for slot in (1, 2, 3):
            self.slots[slot] = ArtButtonSlot()
