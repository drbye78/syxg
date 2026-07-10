"""
XGML (XG Markup Language) — Parser, Bridges, and Type System.

Provides:
  - XGMLConfigParser: unified YAML → typed XGMLConfig
  - XGMLMIDIBridge: XGMLConfig → list[MIDIMessage]
  - XGMLSynthBridge: XGMLConfig → synthesizer API calls
  - XGMLConfig: typed dataclass for the full XGML document model
"""

from __future__ import annotations

from .bridges.midi import XGMLMIDIBridge
from .bridges.synth import XGMLSynthBridge
from .parser import XGMLConfigParser
from .types import XGMLConfig

__all__ = [
    "XGMLConfigParser",
    "XGMLMIDIBridge",
    "XGMLSynthBridge",
    "XGMLConfig",
]
