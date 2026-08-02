"""Centralized XG CC controller — single dispatch table, O(1) channel-to-part.

Replaces CC handling fragmented across XGSystem, SF2Region, XGSynthesizerSystem,
and XGControllerAssignments with a single XGCCController.
"""

from __future__ import annotations

import logging
from typing import Any

from .xg_state import XGState

logger = logging.getLogger(__name__)

# ── CC dispatch table: controller → parameter name ──

_CC_HANDLERS: dict[int, str] = {
    0: "bank_msb",
    1: "modulation_wheel",
    2: "breath_controller",
    4: "foot_controller",
    5: "portamento_time",
    7: "volume",
    10: "pan",
    11: "expression",
    32: "bank_lsb",
    64: "sustain_pedal",
    65: "portamento_on_off",
    71: "harmonic_content",
    72: "release_time",
    73: "attack_time",
    74: "brightness",
    75: "filter_cutoff",
    76: "decay_time",
    77: "vibrato_rate",
    78: "vibrato_depth",
    79: "vibrato_delay",
    91: "reverb_send",
    92: "tremolo_depth",
    93: "chorus_send",
    94: "variation_send",
    120: "all_sound_off",
    121: "reset_all_controllers",
    123: "all_notes_off",
}


class XGCCController:
    """Centralized MIDI CC handler with O(1) channel-to-part lookup.

    Access pattern:
        controller.handle_cc(channel, controller, value)
    """

    def __init__(self, state: XGState):
        self.state = state

    def set_channel_to_part(self, mapping: dict[int, int]) -> None:
        """Set the O(1) channel-to-part lookup table."""
        with self.state.lock:
            self.state.channel_to_part = dict(mapping)

    def handle_cc(self, channel: int, controller: int, value: int) -> bool:
        """Handle a MIDI CC message.

        Args:
            channel: MIDI channel (0-15)
            controller: CC number (0-127)
            value: CC value (0-127)

        Returns:
            True if the CC was handled, False if unknown.
        """
        handler = _CC_HANDLERS.get(controller)
        if handler is None:
            return False

        with self.state.lock:
            # O(1) channel-to-part lookup
            part_num = self.state.channel_to_part.get(channel)
            if part_num is None:
                return False
            if part_num >= len(self.state.parts):
                return False

            part = self.state.parts[part_num]

            # Handle specific CCs that need special logic
            if handler == "volume":
                part.volume = max(0, min(127, value))
            elif handler == "pan":
                part.pan = max(0, min(127, value))
            elif handler == "bank_msb":
                part.bank_msb = max(0, min(127, value))
            elif handler == "bank_lsb":
                part.bank_lsb = max(0, min(127, value))
            elif handler == "reverb_send":
                part.reverb_send = max(0, min(127, value))
            elif handler == "chorus_send":
                part.chorus_send = max(0, min(127, value))
            elif handler == "variation_send":
                part.variation_send = max(0, min(127, value))
            elif handler == "filter_cutoff":
                part.filter_cutoff = max(0, min(127, value))
            elif handler == "filter_resonance":
                part.filter_resonance = max(0, min(127, value))
            else:
                # Generic: set attribute if it exists on part
                if hasattr(part, handler):
                    setattr(part, handler, max(0, min(127, value)))

        return True

    def handle_system_cc(self, controller: int, value: int) -> bool:
        """Handle a system-level CC (not per-part)."""
        handler = _CC_HANDLERS.get(controller)
        if handler is None:
            return False

        with self.state.lock:
            if hasattr(self.state.system, handler):
                setattr(self.state.system, handler, value)
                return True
        return False

    def get_cc_handlers(self) -> dict[int, str]:
        """Return the complete CC handler mapping."""
        return dict(_CC_HANDLERS)
