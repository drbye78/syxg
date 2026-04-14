"""
Modulation system for XG synthesizer.
Contains modulation sources, destinations, routes, and matrix.
"""

from __future__ import annotations

from .destinations import ModulationDestination
from .matrix import ModulationMatrix
from .routes import ModulationRoute
from .sources import ModulationSource

__all__ = ["ModulationDestination", "ModulationMatrix", "ModulationRoute", "ModulationSource"]
