"""
XG System Effects Subpackage

System-wide effects applied to the final mix: reverb, chorus, modulation.
"""

from .reverb import XGSystemReverbProcessor
from .chorus import XGSystemChorusProcessor
from .modulation import XGSystemModulationProcessor
from .processor import XGSystemEffectsProcessor

__all__ = [
    "XGSystemReverbProcessor",
    "XGSystemChorusProcessor",
    "XGSystemModulationProcessor",
    "XGSystemEffectsProcessor",
]
