"""
XG Distortion Effects Subpackage

Implements XG distortion effects (types 43-56) with DSP algorithms.
"""

from .compressor import ProfessionalCompressor
from .dynamic_eq import DynamicEQEnhancer
from .multi_stage import MultiStageDistortionProcessor
from .multiband_compressor import MultibandCompressor
from .processor import ProductionDistortionDynamicsProcessor
from .tube_saturation import TubeSaturationProcessor

__all__ = [
    "DynamicEQEnhancer",
    "MultiStageDistortionProcessor",
    "MultibandCompressor",
    "ProductionDistortionDynamicsProcessor",
    "ProfessionalCompressor",
    "TubeSaturationProcessor",
]
