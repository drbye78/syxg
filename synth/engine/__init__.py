"""
Synthesis engine layer for XG synthesizer.

Provides synthesis engine abstraction and registry for different synthesis technologies.
"""

from __future__ import annotations

from .additive_engine import AdditiveEngine
from .an_engine import ANEngine
from .convolution_reverb_engine import ConvolutionReverbEngine
from .fdsp_engine import FDSPEngine
from .fm_engine import FMEngine
from .granular_engine import GranularEngine
from .modern_xg_synthesizer import ModernXGSynthesizer
from .optimized_coefficient_manager import get_global_coefficient_manager
from .physical_engine import PhysicalEngine
from .sf2_engine import SF2Engine
from .spectral_engine import SpectralEngine
from .synthesis_engine import SynthesisEngine, SynthesisEngineRegistry
from .wavetable_engine import WavetableEngine

__all__ = [
    "ANEngine",
    "AdditiveEngine",
    "ConvolutionReverbEngine",
    "FDSPEngine",
    "FMEngine",
    "GranularEngine",
    "ModernXGSynthesizer",
    "PhysicalEngine",
    "SF2Engine",
    "SpectralEngine",
    "SynthesisEngine",
    "SynthesisEngineRegistry",
    "WavetableEngine",
    "get_global_coefficient_manager",
]
