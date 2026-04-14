"""
Synthesis engine layer for XG synthesizer.

Provides synthesis engine abstraction and registry for different synthesis technologies.
"""

from __future__ import annotations

from .additive import AdditiveEngine
from .convolution import ConvolutionReverbEngine
from .fdsp import FDSPEngine
from .fm_engine import FMEngine
from .granular import GranularEngine
from .optimized_coefficient_manager import get_global_coefficient_manager
from .physical_engine import PhysicalEngine
from .physical_modeling import ANEngine
from .sf2_engine import SF2Engine
from .spectral import SpectralEngine
from .synthesis_engine import SynthesisEngine, SynthesisEngineRegistry
from .wavetable import WavetableEngine

__all__ = [
    "ANEngine",
    "AdditiveEngine",
    "ConvolutionReverbEngine",
    "FDSPEngine",
    "FMEngine",
    "GranularEngine",

    "PhysicalEngine",
    "SF2Engine",
    "SpectralEngine",
    "SynthesisEngine",
    "SynthesisEngineRegistry",
    "WavetableEngine",
    "get_global_coefficient_manager",
]
