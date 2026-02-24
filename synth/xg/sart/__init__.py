"""
S.Art2 (Super Articulation 2) Articulation System.

Provides universal articulation control across ALL synthesis engines in Modern XG Synth.
Wraps any IRegion implementation with expressive articulation capabilities.

This package contains the CORE S.Art2 integration components:
- sart2_region: SArt2Region wrapper for articulation control
- articulation_controller: ArticulationController for parameter management  
- nrpn: YamahaNRPNMapper for NRPN message processing

Note: The standalone synthesizer and related components have been integrated
into ModernXGSynthesizer. Use synth.engine.modern_xg_synthesizer instead.

Package Structure:
- sart2_region: S.Art2 wrapper for any IRegion implementation
- articulation_controller: Articulation control and parameter management
- nrpn: NRPN mapping for Yamaha S.Art2 articulations

Usage:
    from synth import ModernXGSynthesizer
    
    # S.Art2 is enabled by default
    synth = ModernXGSynthesizer()
    
    # Set articulation
    synth.set_channel_articulation(0, 'legato')
    
    # Or via NRPN
    synth.process_nrpn(channel=0, msb=1, lsb=1, value=0)
"""

from .sart2_region import SArt2Region, SArt2RegionFactory
from .articulation_controller import ArticulationController
from .nrpn import YamahaNRPNMapper, midi_note_to_frequency

__version__ = "3.0.0"

__all__ = [
    # Core S.Art2 integration
    "SArt2Region",
    "SArt2RegionFactory",
    "ArticulationController",
    
    # NRPN mapping
    "YamahaNRPNMapper",
    "midi_note_to_frequency",
]

# Deprecated imports (for backward compatibility during transition)
# These will be removed in a future version
_DEPRECATED = {
    "SuperArticulation2Synthesizer": "Use ModernXGSynthesizer from synth.engine.modern_xg_synthesizer instead",
    "SynthConfig": "Use ModernXGSynthesizer configuration instead",
    "VoiceManager": "Use VoiceManager from synth.voice.voice_manager instead",
    "VoiceState": "Use Voice from synth.voice.voice instead",
    "NoteEvent": "Use NoteEvent from synth.voice.voice_instance instead",
}


def __getattr__(name):
    """Handle deprecated imports with helpful error messages."""
    if name in _DEPRECATED:
        import warnings
        warnings.warn(
            f"{name} is deprecated and will be removed in a future version. "
            f"{_DEPRECATED[name]}",
            DeprecationWarning,
            stacklevel=2
        )
        # Return None or raise ImportError
        raise ImportError(
            f"{name} has been moved. {_DEPRECATED[name]}"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
