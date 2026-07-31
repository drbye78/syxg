"""ArticulationEngine — unified, data-driven, stereo-native articulation processor.

Replaces SF2SampleModifier and SArt2Bridge with a single engine backed by
modular ArticulationProcessor instances and a data-driven registry.

Usage:
    engine = ArticulationEngine(sample_rate=44100)
    ctx = ArticulationContext(note=60, velocity=100, ...)
    engine.apply(buf, "vibrato", ctx)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .context import ArticulationContext
from .processor import ArticulationProcessor
from .registry import (
    ARTICULATION_REGISTRY,
    DYNAMICS,
    NOTE_LEVEL,
    STUB,
    VOICE_LEVEL,
    populate_fallback_aliases,
)

logger = logging.getLogger(__name__)

# Ensure fallback aliases are populated at import time
populate_fallback_aliases()


class ArticulationEngine:
    """Unified articulation processing engine.

    Owns a pool of lazy-initialized ArticulationProcessor instances.
    Dispatch is data-driven via ARTICULATION_REGISTRY.
    """

    def __init__(self, sample_rate: int):
        """Initialize the articulation engine.

        Args:
            sample_rate: Audio sample rate in Hz.
        """
        self.sample_rate = sample_rate
        self._processors: dict[type, ArticulationProcessor] = {}

    def get_processor(self, proc_type: type[ArticulationProcessor]) -> ArticulationProcessor:
        """Get or lazy-create a processor instance.

        Args:
            proc_type: The processor class to retrieve.

        Returns:
            A shared processor instance (reused across voices).
        """
        if proc_type not in self._processors:
            try:
                self._processors[proc_type] = proc_type(self.sample_rate)
            except TypeError:
                # Some processors need the engine reference (e.g. CompositeProcessor)
                self._processors[proc_type] = proc_type(self.sample_rate, self)
        return self._processors[proc_type]

    def apply(
        self,
        buf: np.ndarray,
        articulation: str,
        context: ArticulationContext,
    ) -> None:
        """Apply an articulation to a stereo buffer in-place.

        Args:
            buf: Stereo (n, 2) float32 buffer. Modified in-place.
            articulation: Articulation name from NRPN_ARTICULATION_MAP.
            context: Voice/note/instrument context for this buffer.

        Silently returns for:
        - "normal" articulation (no processing needed)
        - Unknown articulations (logged at debug level)
        - STUB entries (logged at debug level)
        - DYNAMICS entries (handled at CC level, not sample DSP)
        - VOICE_LEVEL entries (handled at voice level, not sample DSP)
        """
        if articulation == "normal" or not articulation:
            return

        entry = ARTICULATION_REGISTRY.get(articulation)
        if entry is None:
            logger.debug(f"No registry entry for articulation: {articulation}")
            return

        proc_type, params = entry

        if proc_type is STUB:
            reason = params.get("reason", "unknown")
            logger.debug(f"STUB articulation '{articulation}': {reason}")
            return
        elif proc_type is DYNAMICS:
            return
        elif proc_type is VOICE_LEVEL:
            # Route to voice-level features via VoiceFeatureController
            from synth.engines.voice_features import VoiceFeatureController

            feature = params.get("feature", "trigger_mode")
            if context.voice_state is not None:
                ctrl = VoiceFeatureController()
                ctrl.apply(context.voice_state, feature, params)
            return
        elif proc_type is NOTE_LEVEL:
            # Handled at note-on by ArticulationNoteSequencer — no sample DSP
            return

        try:
            processor = self.get_processor(proc_type)
            processor.process(buf, context, params)
        except Exception:
            logger.exception(f"Error applying articulation '{articulation}'")

    def reset(self) -> None:
        """Reset all processor state (called on voice reuse or channel reset)."""
        for proc in self._processors.values():
            try:
                proc.reset()
            except Exception:
                logger.exception("Error resetting processor")
