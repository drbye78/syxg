"""
S90/S70 Specific Features Implementation

Hardware-specific parameters, behaviors, and compatibility features
for authentic S90/S70 emulation.
"""

from .hardware_specifications import S90S70HardwareSpecs
from .preset_compatibility import S90S70PresetCompatibility
from .control_surface_mapping import S90S70ControlSurfaceMapping
from .performance_features import S90S70PerformanceFeatures

__all__ = [
    'S90S70HardwareSpecs',
    'S90S70PresetCompatibility',
    'S90S70ControlSurfaceMapping',
    'S90S70PerformanceFeatures'
]
