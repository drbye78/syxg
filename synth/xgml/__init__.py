"""
XGML (XG Markup Language) Parser and Translator

Provides high-level YAML-based interface for XG synthesizer control,
converting XGML documents to MIDI message sequences.
"""

from __future__ import annotations

from .constants import XGML_VERSION
from .parser import XGMLParser
from .translator import XGMLToMIDITranslator

__version__ = "2.0.0"
__all__ = ["XGML_VERSION", "XGMLParser", "XGMLToMIDITranslator"]
