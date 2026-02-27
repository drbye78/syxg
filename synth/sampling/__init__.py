"""
Enhanced Sampling System - Professional Sample Management

Advanced sample playback, editing, and processing capabilities
for workstation-grade sampling functionality.

Part of S90/S70 compatibility implementation - Phase 3.
"""
from __future__ import annotations

from .sample_manager import SampleManager
from .sample_editor import SampleEditor
from .sample_processor import SampleProcessor
from .sample_formats import SampleFormatHandler
from .sample_library import SampleLibrary
from .time_stretching import TimeStretchingEngine
from .pitch_shifting import PitchShiftingEngine

__all__ = [
    'SampleManager', 'SampleEditor', 'SampleProcessor',
    'SampleFormatHandler', 'SampleLibrary',
    'TimeStretchingEngine', 'PitchShiftingEngine'
]
