"""
XG Insertion Effects Subpackage

Insertion effects (types 0-17) with production-quality DSP algorithms.
"""

from .envelope_filter import ProductionEnvelopeFilter
from .flanger import ProductionFlangerProcessor
from .phaser import ProductionPhaserProcessor
from .processor import ProductionXGInsertionEffectsProcessor
from .rotary_speaker import ProfessionalRotarySpeaker

__all__ = [
    "ProductionEnvelopeFilter",
    "ProductionFlangerProcessor",
    "ProductionPhaserProcessor",
    "ProductionXGInsertionEffectsProcessor",
    "ProfessionalRotarySpeaker",
]
