"""
Modulation system for XG synthesizer.
Contains modulation sources, destinations, routes, and matrix.
"""
from __future__ import annotations

from .sources import ModulationSource
from .destinations import ModulationDestination
from .routes import ModulationRoute
from .matrix import ModulationMatrix

__all__ = [
    'ModulationSource',
    'ModulationDestination',
    'ModulationRoute',
    'ModulationMatrix'
]
