"""Unified Articulation Engine — modular, data-driven, stereo-native.

Replaces SF2SampleModifier and SArt2Bridge with a single engine backed by
modular ArticulationProcessor implementations and a data-driven registry.
"""

from .engine import ArticulationEngine
from .context import ArticulationContext
from .processor import ArticulationProcessor

__all__ = ["ArticulationEngine", "ArticulationContext", "ArticulationProcessor"]
