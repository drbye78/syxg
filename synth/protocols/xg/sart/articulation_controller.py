"""
Articulation Controller - NRPN/SYSEX Handler for S.Art2-style articulations.

DEPRECATED: This module is kept for backward compatibility.
Please import from the new modular structure:
    from synth.protocols.xg.sart.controllers import ArticulationController
    from synth.protocols.xg.sart.modifiers import SF2SampleModifier
    from synth.protocols.xg.sart.mappings import NRPN_ARTICULATION_MAP
"""

from __future__ import annotations

# Re-export from new modular structure for backward compatibility
from .controllers import ArticulationController, create_articulation_controller
from .mappings import (
    MSB_CATEGORIES,
    NRPN_ARTICULATION_MAP,
    get_articulation_from_nrpn,
    get_nrpn_for_articulation,
)
from .modifiers import SF2SampleModifier, create_sample_modifier

__all__ = [
    "MSB_CATEGORIES",
    "NRPN_ARTICULATION_MAP",
    "ArticulationController",
    "SF2SampleModifier",
    "create_articulation_controller",
    "create_sample_modifier",
    "get_articulation_from_nrpn",
    "get_nrpn_for_articulation",
]
