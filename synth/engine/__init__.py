"""
Synthesis engine layer for XG synthesizer.

Provides synthesis engine abstraction and registry for different synthesis technologies.
"""
from __future__ import annotations

from .synthesis_engine import SynthesisEngine, SynthesisEngineRegistry
from .sf2_engine import SF2Engine
from .modern_xg_synthesizer import ModernXGSynthesizer
from .fdsp_engine import FDSPEngine
from .an_engine import ANEngine
from .fm_engine import FMEngine
from .wavetable_engine import WavetableEngine
from .additive_engine import AdditiveEngine
from .granular_engine import GranularEngine
from .physical_engine import PhysicalEngine
from .convolution_reverb_engine import ConvolutionReverbEngine
from .spectral_engine import SpectralEngine
from .optimized_coefficient_manager import get_global_coefficient_manager

__all__ = [
    'SynthesisEngine',
    'SynthesisEngineRegistry',
    'SF2Engine',
    'ModernXGSynthesizer',
    'FDSPEngine',
    'ANEngine',
    'FMEngine',
    'WavetableEngine',
    'AdditiveEngine',
    'GranularEngine',
    'PhysicalEngine',
    'ConvolutionReverbEngine',
    'SpectralEngine',
    'get_global_coefficient_manager'
]
