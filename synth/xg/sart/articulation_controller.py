"""
Articulation Controller - NRPN/SYSEX Handler for S.Art2-style articulations.

DEPRECATED: This module is kept for backward compatibility.
Please import from the new modular structure:
    from synth.xg.sart.controllers import ArticulationController
    from synth.xg.sart.modifiers import SF2SampleModifier
    from synth.xg.sart.mappings import NRPN_ARTICULATION_MAP
"""
from __future__ import annotations

# Re-export from new modular structure for backward compatibility
from .controllers import ArticulationController, create_articulation_controller
from .modifiers import SF2SampleModifier, create_sample_modifier
from .mappings import (
    NRPN_ARTICULATION_MAP,
    MSB_CATEGORIES,
    get_articulation_from_nrpn,
    get_nrpn_for_articulation,
)

__all__ = [
    "ArticulationController",
    "create_articulation_controller",
    "SF2SampleModifier",
    "create_sample_modifier",
    "NRPN_ARTICULATION_MAP",
    "MSB_CATEGORIES",
    "get_articulation_from_nrpn",
    "get_nrpn_for_articulation",
]
