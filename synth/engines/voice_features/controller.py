"""Voice-level synthesis features for S.Art2 articulation control.

These features modify voice/channel state BEFORE sample generation,
unlike the ArticulationEngine processors which operate on audio buffers.

Handles: trigger modes (trig/gate/tie/legato_synth), glide (portamento),
LFO sync, filter envelope routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Trigger modes — envelope behavior across note boundaries
# ============================================================================


class TriggerMode(StrEnum):
    """Voice envelope trigger behavior."""

    NORMAL = "normal"     # Standard: attack → decay → sustain → release
    LEGATO = "legato"     # Skip attack on overlapping notes (attack_skip = True)
    GATE = "gate"         # Sustain while key held, release on last key-up
    TIE = "tie"           # Skip attack + envelope reset on overlapping notes
    TRIG = "trig"         # One-shot: envelope runs to completion regardless of note-off


@dataclass(slots=True)
class VoiceFeatureState:
    """Mutable voice-level feature state, applied before note generation."""

    trigger_mode: TriggerMode = TriggerMode.NORMAL
    lfo_sync_enabled: bool = False
    filter_envelope_depth: float = 0.0
    filter_envelope_polarity: str = "+"
    glide_time: float = 0.0
    glide_active: bool = False

    # Set by the envelope state machine at note-on
    attack_skip: bool = False

    # Set by Channel/Voice for portamento tracking
    portamento_active: bool = False
    portamento_time: float = 0.0
    portamento_last_note: int | None = None


class VoiceFeatureController:
    """Applies voice-level feature settings to a VoiceInstance.

    Call apply() at note-on, BEFORE the voice generates its first block.
    """

    def apply(
        self,
        voice: Any,
        feature: str,
        params: dict[str, Any],
    ) -> None:
        """Apply a voice-level articulation feature to a voice.

        Args:
            voice: VoiceInstance or similar object with mutable state.
            feature: Feature name from the VOICE_LEVEL registry entry.
            params: Parameters for the feature.
        """
        if feature == "trigger_mode":
            mode = TriggerMode(params.get("mode", "normal"))
            if mode == TriggerMode.LEGATO:
                self._set_legato(voice)
            elif mode == TriggerMode.GATE:
                self._set_gate(voice)
            elif mode == TriggerMode.TIE:
                self._set_tie(voice)
            elif mode == TriggerMode.TRIG:
                self._set_trig(voice)

        elif feature == "glide":
            glide_time = params.get("time", 0.05)
            self._set_glide(voice, glide_time)

        elif feature == "lfo_sync":
            enabled = params.get("enabled", True)
            self._set_lfo_sync(voice, enabled)

        elif feature == "filter_envelope":
            depth = params.get("depth", 0.8)
            polarity = params.get("polarity", "+")
            self._set_filter_envelope(voice, depth, polarity)

    # ── Trigger mode implementations ──

    @staticmethod
    def _set_legato(voice: Any) -> None:
        """Skip attack on overlapping notes. Uses existing attack_skip flag."""
        if hasattr(voice, "attack_skip"):
            voice.attack_skip = True
        elif hasattr(voice, "_state") and hasattr(voice._state, "attack_skip"):
            voice._state.attack_skip = True

    @staticmethod
    def _set_gate(voice: Any) -> None:
        """Sustain while any key held, release on last key-up."""
        if hasattr(voice, "envelope_gate_mode"):
            voice.envelope_gate_mode = True

    @staticmethod
    def _set_tie(voice: Any) -> None:
        """Skip envelope reset on tied notes — pitch changes only."""
        if hasattr(voice, "envelope_skip_attack"):
            voice.envelope_skip_attack = True

    @staticmethod
    def _set_trig(voice: Any) -> None:
        """One-shot envelope that runs to completion regardless of note-off."""
        if hasattr(voice, "envelope_one_shot"):
            voice.envelope_one_shot = True

    # ── Glide (portamento) — delegates to existing portamento system ──

    @staticmethod
    def _set_glide(voice: Any, glide_time: float) -> None:
        """Enable portamento/glide between notes.

        The existing SF2Region portamento system handles pitch interpolation.
        This sets the portamento time from the articulation parameter.
        """
        # Route through channel-level portamento (CC5/CC65)
        # If the voice has a channel reference, set portamento state there
        if hasattr(voice, "channel_obj") and voice.channel_obj is not None:
            ch = voice.channel_obj
            if hasattr(ch, "controllers"):
                # CC65 >= 64 enables portamento
                ch.controllers[65] = 127
                # CC5 = portamento time (0-127 → 0-5s)
                time_cc = min(127, int(glide_time * 25.4))
                ch.controllers[5] = time_cc

        # Also set directly on the voice for immediate effect
        if hasattr(voice, "_pre_portamento_active"):
            voice._pre_portamento_active = True
            voice._pre_portamento_time = glide_time

    # ── LFO sync ──

    @staticmethod
    def _set_lfo_sync(voice: Any, enabled: bool) -> None:
        """Set LFO phase reset on note-on."""
        if hasattr(voice, "lfo_sync_enabled"):
            voice.lfo_sync_enabled = enabled

    # ── Filter envelope routing ──

    @staticmethod
    def _set_filter_envelope(voice: Any, depth: float, polarity: str) -> None:
        """Route envelope output to filter cutoff with configurable depth."""
        if hasattr(voice, "filter_env_depth"):
            voice.filter_env_depth = depth
            voice.filter_env_polarity = polarity
        # Set on modulation state for the base region to consume
        if hasattr(voice, "modulation_state"):
            sign = 1.0 if polarity == "+" else -1.0
            voice.modulation_state["filter_env_depth"] = depth * sign
