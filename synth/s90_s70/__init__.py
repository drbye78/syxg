"""
S90/S70 Specific Features Implementation

Hardware-specific parameters, behaviors, and compatibility features
for authentic S90/S70 emulation.
"""

from __future__ import annotations

from .control_surface_mapping import S90S70ControlSurfaceMapping
from .hardware_specifications import S90S70HardwareSpecs
from .performance_features import S90S70PerformanceFeatures
from .preset_compatibility import S90S70PresetCompatibility

__all__ = [
    "S90S70ControlSurfaceMapping",
    "S90S70HardwareSpecs",
    "S90S70PerformanceFeatures",
    "S90S70PresetCompatibility",
]
