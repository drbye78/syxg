"""
Jupiter-X Engine Plugins

Plugin extensions for Jupiter-X specific synthesis features.
These plugins extend the base synthesis engines with Jupiter-X capabilities
without duplicating core functionality.
"""
from __future__ import annotations

from .fm_extensions import JupiterXFMPlugin
from .digital_extensions import JupiterXDigitalPlugin
from .analog_extensions import JupiterXAnalogPlugin
from .external_extensions import JupiterXExternalPlugin

__all__ = [
    'JupiterXFMPlugin',
    'JupiterXDigitalPlugin',
    'JupiterXAnalogPlugin',
    'JupiterXExternalPlugin',
]
