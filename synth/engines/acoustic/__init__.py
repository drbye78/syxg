"""SuperNATURAL-Acoustic alike behavior-modeling engine.

Wraps a sampler engine (SF2/SFZ) as the base and adds real-time behavior
modeling driven by MIDI, covering both single-note dynamics and cross-note
(multi-voice) dynamics via a shared per-channel acoustic context.
"""

from __future__ import annotations

from .behavior_config import BehaviorConfig, EnsembleConfig, InstrumentGroup
from .channel_context import ChannelAcousticContext
from .voice_state import VoiceBehaviorState, VoicePhase

__all__ = [
    "BehaviorConfig",
    "ChannelAcousticContext",
    "EnsembleConfig",
    "InstrumentGroup",
    "VoiceBehaviorState",
    "VoicePhase",
]
