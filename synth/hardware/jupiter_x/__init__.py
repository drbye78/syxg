"""
Jupiter-X Synthesizer Module

Production-grade Roland Jupiter-X synthesizer implementation with complete
MIDI parameter control, multi-engine architecture, and integration with
the modern synthesizer framework.

Features:
- 16-part multitimbral synthesis
- 4 synthesis engines per part (Analog, Digital, FM, External)
- Complete SysEx and NRPN MIDI support
- Grid-based arpeggiator patterns
- Comprehensive effects processing
- Thread-safe, zero-allocation operation
"""

from __future__ import annotations

from .arpeggiator import (
    JupiterXArpeggiatorEngine,
    JupiterXArpeggiatorInstance,
    JupiterXArpeggiatorPattern,
)
from .component_manager import (
    JupiterXComponentManager,
    JupiterXEffectsParameters,
    JupiterXSystemParameters,
)
from .constants import *
from .jupiter_x_engine import JupiterXEngineIntegration, create_jupiter_x_engine
from .midi_controller import JupiterXMIDIController
from .mpe_manager import JupiterXMPEManager
from .nrpn_controller import JupiterXNRPNController
from .part import JupiterXEngine, JupiterXEnvelope, JupiterXPart
from .performance_optimizer import JupiterXPerformanceOptimizer

# Jupiter-X engines are now consolidated into base engines with plugins
# from .analog_engine import JupiterXAnalogEngine  # REMOVED - use AdditiveEngine + JupiterXAnalogPlugin
# Jupiter-X engines are now consolidated into base engines with plugins
# from .digital_engine import JupiterXDigitalEngine  # REMOVED - use WavetableEngine + JupiterXDigitalPlugin
# from .fm_engine import JupiterXFMEngine  # REMOVED - use FMEngine + JupiterXFMPlugin
# from .external_engine import JupiterXExternalEngine  # REMOVED - use GranularEngine + JupiterXExternalPlugin
# from .fm_engine import JupiterXFMEngine  # REMOVED - use FMEngine + JupiterXFMPlugin
# from .external_engine import JupiterXExternalEngine  # REMOVED - use GranularEngine + JupiterXExternalPlugin
from .synthesizer import JupiterXSynthesizer, JupiterXSynthesizerInterface
from .sysex_controller import JupiterXSysExController
from .unified_parameter_system import JupiterXUnifiedParameterSystem

__version__ = "1.0.0"
__author__ = "Jupiter-X Development Team"

__all__ = [
    # Core classes
    "JupiterXComponentManager",
    "JupiterXPart",
    "JupiterXMIDIController",
    # Engine classes
    "JupiterXAnalogEngine",
    "JupiterXEngine",
    # Parameter classes
    "JupiterXSystemParameters",
    "JupiterXEffectsParameters",
    # MIDI controllers
    "JupiterXSysExController",
    "JupiterXNRPNController",
    # Constants
    "JUPITER_X_MANUFACTURER_ID",
    "JUPITER_X_MODEL_ID",
    "ENGINE_ANALOG",
    "ENGINE_DIGITAL",
    "ENGINE_FM",
    "ENGINE_EXTERNAL",
    "ENGINE_NAMES",
]


def create_jupiter_x_synthesizer(sample_rate: int = 44100) -> JupiterXComponentManager:
    """
    Create a new Jupiter-X synthesizer instance.

    Args:
        sample_rate: Audio sample rate in Hz

    Returns:
        Configured Jupiter-X synthesizer
    """
    return JupiterXComponentManager(sample_rate)


def get_jupiter_x_info() -> dict:
    """
    Get Jupiter-X module information.

    Returns:
        Dictionary with module capabilities and version info
    """
    return {
        "name": "Jupiter-X Synthesizer",
        "version": __version__,
        "manufacturer": "Roland",
        "model": "Jupiter-X",
        "parts": 16,
        "engines_per_part": 4,
        "engine_types": list(ENGINE_NAMES.values()),
        "midi_support": ["SysEx", "NRPN", "Standard MIDI"],
        "effects": ["Reverb", "Chorus", "Delay", "Distortion"],
        "arpeggiator": "Grid-based patterns",
        "polyphony": "16 monophonic parts",
    }
