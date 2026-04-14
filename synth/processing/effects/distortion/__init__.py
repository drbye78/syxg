"""
XG Distortion Effects Subpackage

Implements XG distortion effects (types 43-56) with DSP algorithms.
"""

from .tube_saturation import TubeSaturationProcessor
from .multi_stage import MultiStageDistortionProcessor
from .compressor import ProfessionalCompressor
from .multiband_compressor import MultibandCompressor
from .dynamic_eq import DynamicEQEnhancer
from .processor import ProductionDistortionDynamicsProcessor

__all__ = [
    "TubeSaturationProcessor",
    "MultiStageDistortionProcessor",
    "ProfessionalCompressor",
    "MultibandCompressor",
    "DynamicEQEnhancer",
    "ProductionDistortionDynamicsProcessor",
]
