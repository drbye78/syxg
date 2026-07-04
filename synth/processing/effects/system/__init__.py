"""
XG System Effects Subpackage

System-wide effects applied to the final mix: reverb, chorus, modulation.
"""

from __future__ import annotations

from .chorus import XGSystemChorusProcessor
from .modulation import XGSystemModulationProcessor
from .processor import XGSystemEffectsProcessor
from .reverb import XGSystemReverbProcessor

__all__ = [
    "XGSystemChorusProcessor",
    "XGSystemEffectsProcessor",
    "XGSystemModulationProcessor",
    "XGSystemReverbProcessor",
]
