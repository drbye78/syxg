"""
XGML (XG Markup Language) Parser and Translator

Provides high-level YAML-based interface for XG synthesizer control,
converting XGML documents to MIDI message sequences.
"""

from .parser import XGMLParser
from .translator import XGMLToMIDITranslator
from .constants import XGML_VERSION

__version__ = "1.0.0"
__all__ = ['XGMLParser', 'XGMLToMIDITranslator', 'XGML_VERSION']
