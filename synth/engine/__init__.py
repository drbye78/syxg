"""
Synthesis engine layer for XG synthesizer.

Provides synthesis engine abstraction and registry for different synthesis technologies.
"""

from .synthesis_engine import SynthesisEngine, SynthesisEngineRegistry
from .sf2_engine import SF2Engine
from .modern_xg_synthesizer import ModernXGSynthesizer
from .optimized_coefficient_manager import get_global_coefficient_manager

__all__ = [
    'SynthesisEngine',
    'SynthesisEngineRegistry',
    'SF2Engine',
    'ModernXGSynthesizer',
    'get_global_coefficient_manager'
]
