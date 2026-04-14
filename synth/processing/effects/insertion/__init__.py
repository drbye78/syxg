"""
XG Insertion Effects Subpackage

Insertion effects (types 0-17) with production-quality DSP algorithms.
"""

from .phaser import ProductionPhaserProcessor
from .flanger import ProductionFlangerProcessor
from .rotary_speaker import ProfessionalRotarySpeaker
from .envelope_filter import ProductionEnvelopeFilter
from .processor import ProductionXGInsertionEffectsProcessor

__all__ = [
    "ProductionPhaserProcessor",
    "ProductionFlangerProcessor",
    "ProfessionalRotarySpeaker",
    "ProductionEnvelopeFilter",
    "ProductionXGInsertionEffectsProcessor",
]
