"""
Audio effects processing for XG synthesizer.

Provides reverb, chorus, delay, distortion, EQ, and other audio effects
with XG specification compliance and MIDI control support.
"""

from __future__ import annotations

# Core System Imports
from .effects_coordinator import XGEffectsCoordinator

# Factory System
from .effects_registry import XGEffectRegistry

# MIDI Control
from .midi_control_interface import XGMIDIController, XGNRPNController

# Performance Monitoring
from .performance_monitor import XGPerformanceMonitor, enable_performance_monitoring

# Validation and Testing
from .effect_validator import XGValidationSuite, print_validation_summary, validate_xg_effects_implementation

# Core Types (always available)
from .types import (
    XGBiquadCoeffs,
    XGBiquadState,
    XGBusType,
    XGChannelEQParams,
    XGChannelMixerParams,
    XGChannelParams,
    XGChorusType,
    XGDelayLineState,
    XGEffectCategory,
    XGEQType,
    XGInsertionType,
    XGLFOState,
    XGMasterEQParams,
    XGProcessingContext,
    XGProcessingState,
    XGProcessingStats,
    XGReverbType,
    XGSystemEffectsParams,
    XGVariationType,
)

# Version and Metadata
__version__ = "1.1.0"
__author__ = "XG Synthesis Core"
__description__ = "Complete XG Effects Processing System"

__all__ = [
    # Core System
    "XGEffectsCoordinator",
    # Factory System
    "XGEffectRegistry",
    # MIDI Control
    "XGNRPNController",
    "XGMIDIController",
    # Performance Monitoring
    "XGPerformanceMonitor",
    "enable_performance_monitoring",
    # Validation
    "XGValidationSuite",
    "print_validation_summary",
    "validate_xg_effects_implementation",
    # Core Types
    "XGReverbType",
    "XGChorusType",
    "XGVariationType",
    "XGInsertionType",
    "XGProcessingState",
    "XGEffectCategory",
    "XGBusType",
    "XGChannelParams",
    "XGSystemEffectsParams",
    "XGProcessingContext",
    "XGBiquadCoeffs",
    "XGBiquadState",
    "XGDelayLineState",
    "XGLFOState",
    "XGProcessingStats",
    "XGEQType",
    "XGChannelEQParams",
    "XGMasterEQParams",
    "XGChannelMixerParams",
]
