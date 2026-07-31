"""Articulation context carrying voice/note information to every processor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from synth.engines.acoustic.behavior_config import InstrumentGroup
    from synth.engines.acoustic.channel_context import ChannelAcousticContext
    from synth.engines.acoustic.voice_state import VoiceBehaviorState


@dataclass(slots=True)
class ArticulationContext:
    """Voice/note context passed to every articulation processor.

    Every processor receives this context so it can adjust behavior
    based on the instrument, note, velocity, and channel state.
    """

    note: int
    velocity: int
    instrument_group: "InstrumentGroup"
    sample_rate: int
    channel_context: "ChannelAcousticContext | None" = None
    voice_state: "VoiceBehaviorState | None" = None
