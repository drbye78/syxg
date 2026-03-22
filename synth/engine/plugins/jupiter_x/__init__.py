"""
Jupiter-X Engine Plugins

Plugin extensions for Jupiter-X specific synthesis features.
These plugins extend the base synthesis engines with Jupiter-X capabilities
without duplicating core functionality.
"""

from __future__ import annotations

from .analog_extensions import JupiterXAnalogPlugin
from .digital_extensions import JupiterXDigitalPlugin
from .external_extensions import JupiterXExternalPlugin
from .fm_extensions import JupiterXFMPlugin

__all__ = [
    "JupiterXAnalogPlugin",
    "JupiterXDigitalPlugin",
    "JupiterXExternalPlugin",
    "JupiterXFMPlugin",
]
