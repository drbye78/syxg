"""
XG Insertion Effects Subpackage

Insertion effects (types 0-17) with production-quality DSP algorithms.
"""

from __future__ import annotations

from .envelope_filter import ProductionEnvelopeFilter
from .flanger import ProductionFlangerProcessor
from .phaser import ProductionPhaserProcessor
from .processor import ProductionXGInsertionEffectsProcessor
from .rotary_speaker import ProfessionalRotarySpeaker
from .vocoder import CarrierVocoder

__all__ = [
    "CarrierVocoder",
    "ProductionEnvelopeFilter",
    "ProductionFlangerProcessor",
    "ProductionPhaserProcessor",
    "ProductionXGInsertionEffectsProcessor",
    "ProfessionalRotarySpeaker",
]
