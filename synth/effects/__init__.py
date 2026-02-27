"""
Audio effects processing for XG synthesizer.

Provides reverb, chorus, delay, distortion, EQ, and other audio effects
with XG specification compliance and MIDI control support.
"""
from __future__ import annotations

# Core System Imports
from .effects_coordinator import XGEffectsCoordinator

# Factory System
try:
    from .effects_registry import XGEffectRegistry, XGEffectFactory
except ImportError:
    XGEffectRegistry = None
    XGEffectFactory = None

# MIDI Control
try:
    from .midi_control_interface import XGNRPNController, XGMIDIController
except ImportError:
    XGNRPNController = None
    XGMIDIController = None

# Performance Monitoring
try:
    from .performance_monitor import XGPerformanceMonitor, enable_performance_monitoring
except ImportError:
    XGPerformanceMonitor = None
    enable_performance_monitoring = lambda: None

# Validation and Testing
try:
    from .effect_validator import XGValidationSuite, print_validation_summary
    from .effect_validator import validate_xg_effects_implementation
except ImportError:
    XGValidationSuite = None
    print_validation_summary = None
    validate_xg_effects_implementation = lambda *args, **kwargs: None

# Core Types (always available)
from .types import (
    XGReverbType, XGChorusType, XGVariationType, XGInsertionType,
    XGProcessingState, XGEffectCategory, XGBusType,
    XGChannelParams, XGSystemEffectsParams, XGProcessingContext,
    XGBiquadCoeffs, XGBiquadState, XGDelayLineState, XGLFOState,
    XGProcessingStats, XGEQType, XGChannelEQParams,
    XGMasterEQParams, XGChannelMixerParams
)

# Version and Metadata
__version__ = "2.0.0"
__author__ = "XG Synthesis Core"
__description__ = "Complete XG Effects Processing System"

__all__ = [
    # Core System
    'XGEffectsCoordinator',

    # Factory System
    'XGEffectRegistry', 'XGEffectFactory',

    # MIDI Control
    'XGNRPNController', 'XGMIDIController',

    # Performance Monitoring
    'XGPerformanceMonitor', 'enable_performance_monitoring',

    # Validation
    'XGValidationSuite', 'print_validation_summary', 'validate_xg_effects_implementation',

    # Core Types
    'XGReverbType', 'XGChorusType', 'XGVariationType', 'XGInsertionType',
    'XGProcessingState', 'XGEffectCategory', 'XGBusType',
    'XGChannelParams', 'XGSystemEffectsParams', 'XGProcessingContext',
    'XGBiquadCoeffs', 'XGBiquadState', 'XGDelayLineState', 'XGLFOState',
    'XGProcessingStats', 'XGEQType', 'XGChannelEQParams',
    'XGMasterEQParams', 'XGChannelMixerParams',
]
