"""
FDSP Region - Production-grade formant synthesis region.

Part of the unified region-based synthesis architecture.
FDSPRegion implements formant synthesis with:
- Phoneme transitions
- Vocal tract modeling
- Breath noise control
- Vibrato with rate/depth control
- Multiple excitation types
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ...engines.region_descriptor import RegionDescriptor
from ...processing.partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class FDSPRegion(IRegion):
    """
    Production-grade FDSP (Formant Dynamic Synthesis Processor) region.

    Features:
    - Formant synthesis with phoneme transitions
    - Vocal tract modeling
    - Breath noise control
    - Vibrato with rate/depth control
    - Multiple excitation types (vocal, wind, string)
    - Real-time formant shifting

    Attributes:
        descriptor: Region metadata with FDSP parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_breath_level",
        "_excitation_type",
        "_fdsp_engine",
        "_formant_shift",
        "_phoneme",
        "_target_phoneme",
        "_tilt",
        "_transition_progress",
        "_transition_speed",
        "_vibrato_depth",
        "_vibrato_rate",
    ]

    PHONEMES = ["a", "e", "i", "o", "u", "ə", "N", "M", "L", "R", "s", "S"]
    EXCITATION_TYPES = ["vocal", "wind", "string", "noise"]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize FDSP region.

        Args:
            descriptor: Region metadata with FDSP parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Phoneme parameters
        self._phoneme = algo_params.get("phoneme", "ə")
        self._target_phoneme = algo_params.get("target_phoneme", None)
        self._transition_speed = algo_params.get("transition_speed", 0.1)

        # Formant parameters
        self._formant_shift = algo_params.get("formant_shift", 1.0)
        self._tilt = algo_params.get("tilt", 0.5)

        # Vibrato parameters
        self._vibrato_rate = algo_params.get("vibrato_rate", 5.0)
        self._vibrato_depth = algo_params.get("vibrato_depth", 0.0)

        # Breath and excitation
        self._breath_level = algo_params.get("breath_level", 0.0)
        self._excitation_type = algo_params.get("excitation_type", "vocal")

        # Runtime state
        self._fdsp_engine: Any | None = None
        self._transition_progress = 0.0

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for FDSP (algorithmic synthesis)."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create FDSP synthesis partial.

        Returns:
            FDSPPartial instance or None if creation failed
        """
        try:
            # Create FDSP engine for this region
            self._fdsp_engine = self._create_fdsp_engine()

            if self._fdsp_engine is None:
                logger.warning("Failed to create FDSP engine")
                return None

            # Set initial phoneme
            self._fdsp_engine.set_phoneme(self._phoneme)

            # Set vocal parameters
            self._fdsp_engine.set_parameters(
                {
                    "pitch": self._calculate_frequency(),
                    "formant_shift": self._formant_shift,
                    "tilt": self._tilt,
                    "vibrato_rate": self._vibrato_rate,
                    "vibrato_depth": self._vibrato_depth,
                    "breath_level": self._breath_level,
                    "excitation_type": self._excitation_type,
                }
            )

            # Build partial parameters
            partial_params = {
                "fdsp_engine": self._fdsp_engine,
                "phoneme": self._phoneme,
                "excitation_type": self._excitation_type,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create FDSP partial
            from ...processing.partial.fdsp_partial import FDSPPartial

            partial = FDSPPartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create FDSP partial: {e}")
            return None

    def _create_fdsp_engine(self) -> Any | None:
        """
        Create FDSP engine instance.

        Returns:
            FDSPEngine instance or None
        """
        try:
            from ...engines.fdsp import FDSPEngine

            fdsp = FDSPEngine(self.sample_rate)

            # Validate phoneme
            if self._phoneme not in self.PHONEMES:
                logger.warning(f"Invalid phoneme '{self._phoneme}', using 'ə'")
                self._phoneme = "ə"

            return fdsp

        except Exception as e:
            logger.error(f"Failed to create FDSP engine: {e}")
            return None

    def _calculate_frequency(self) -> float:
        """
        Calculate frequency for current note.

        Returns:
            Frequency in Hz
        """
        # MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))

        # Apply fine tuning
        fine_tune = self.descriptor.generator_params.get("fine_tune", 0.0)
        frequency *= 2.0 ** (fine_tune / 1200.0)

        return frequency

    def _init_envelopes(self) -> None:
        """Initialize envelopes (handled by FDSP engine)."""
        pass

    def _init_filters(self) -> None:
        """Initialize filters for FDSP region."""
        try:
            from ...primitives.filter import UltraFastResonantFilter

            # Get filter parameters
            cutoff = self.descriptor.generator_params.get("filter_cutoff", 8000.0)
            resonance = self.descriptor.generator_params.get("filter_resonance", 0.0)

            self._filters["filter"] = UltraFastResonantFilter(
                cutoff=cutoff,
                resonance=resonance,
                filter_type="lowpass",
                sample_rate=self.sample_rate,
            )

        except Exception as e:
            logger.error(f"Failed to initialize filter: {e}")

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this FDSP region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Update FDSP engine parameters
        if self._fdsp_engine:
            self._fdsp_engine.set_pitch(self._calculate_frequency())

            # Velocity affects breath level
            breath_mod = velocity / 127.0
            self._fdsp_engine.set_breath_level(self._breath_level * breath_mod)

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from FDSP engine.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        if not self._partial:
            return np.zeros((block_size, 2), dtype=np.float32)

        try:
            # Apply modulation
            self._apply_modulation(modulation)

            # Generate samples from partial
            samples = self._partial.generate_samples(block_size, modulation)

            # Apply filter if present
            if "filter" in self._filters:
                filter_obj = self._filters["filter"]
                if hasattr(filter_obj, "process_block"):
                    try:
                        filtered = filter_obj.process_block(samples)
                        if filtered is not None:
                            samples = filtered
                    except Exception as e:
                        logger.error(f"FDSP filter processing failed: {e}")

            return samples

        except Exception as e:
            logger.error(f"FDSP sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation to FDSP parameters.

        Args:
            modulation: Modulation values dictionary
        """
        if not self._fdsp_engine:
            return

        # Mod wheel to vibrato depth
        mod_wheel = modulation.get("mod_wheel", 0.0)
        if mod_wheel > 0:
            vibrato_depth = self._vibrato_depth * (1.0 + mod_wheel * 2.0)
            self._fdsp_engine.set_vibrato_depth(vibrato_depth)

        # Aftertouch to formant shift
        aftertouch = modulation.get("channel_aftertouch", 0.0)
        if aftertouch > 0:
            formant_mod = self._formant_shift * (1.0 + aftertouch * 0.5)
            self._fdsp_engine.set_formant_shift(formant_mod)

        # Breath controller to breath level
        breath = modulation.get("breath_controller", 0.0)
        if breath > 0:
            self._fdsp_engine.set_breath_level(breath)

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation state.

        Args:
            modulation: Modulation parameter updates
        """
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if FDSP region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False

        if self._partial:
            return self._partial.is_active()

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "phoneme": self._phoneme,
                "target_phoneme": self._target_phoneme,
                "formant_shift": self._formant_shift,
                "vibrato_rate": self._vibrato_rate,
                "vibrato_depth": self._vibrato_depth,
                "excitation_type": self._excitation_type,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"FDSPRegion(phoneme={self._phoneme}, "
            f"excitation={self._excitation_type}, formant={self._formant_shift:.2f})"
        )
