"""
Partial abstraction layer for XG synthesizer.

Provides synthesis partial implementations and engine-agnostic partial interfaces.
"""

from __future__ import annotations

from .partial import SynthesisPartial
from .sf2_region import SF2Region

__all__ = ["SF2Region", "SynthesisPartial"]
