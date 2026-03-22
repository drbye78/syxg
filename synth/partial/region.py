"""
Region Base Class - Unified interface for all synthesis regions.

Part of the unified region-based synthesis architecture.
IRegion defines the common interface for all region types (SF2, FM, Additive, etc.)
with support for lazy initialization and on-demand sample loading.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any

import numpy as np

# Import from engine module where RegionDescriptor is defined
from ..engine.region_descriptor import RegionDescriptor


class RegionState(IntEnum):
    """
    Region lifecycle states.

    States represent the progression of a region from creation to disposal.
    """

    CREATED = 0  # Region object created, not initialized
    INITIALIZED = 1  # Resources loaded, ready to play
    ACTIVE = 2  # Currently playing (note-on triggered)
    RELEASING = 3  # Note-off triggered, in release phase
    RELEASED = 4  # Envelope complete, ready for disposal


class IRegion(ABC):
    """
    Abstract base class for all region types.

    Unified interface for sample-based and algorithmic synthesis.
    Implements lazy initialization - sample data loaded only when needed.

    Attributes:
        descriptor: Region metadata and parameters
        sample_rate: Audio sample rate in Hz
        block_size: Processing block size in samples
        state: Current region lifecycle state
        current_note: Current MIDI note being played
        current_velocity: Current velocity being played
    """

    __slots__ = [
        "_envelopes",
        "_filters",
        "_initialized",
        "_modulation_state",
        "_output_buffer",
        "_partial",
        "_sample_data",
        "_work_buffer",
        "block_size",
        "current_note",
        "current_velocity",
        "descriptor",
        "sample_rate",
        "state",
    ]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize region with descriptor.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz
        """
        self.descriptor = descriptor
        self.sample_rate = sample_rate
        self.block_size = 1024  # Default, can be overridden

        # State
        self.state = RegionState.CREATED
        self.current_note = 0
        self.current_velocity = 0

        # Lazy-loaded resources
        self._sample_data: np.ndarray | None = None
        self._partial: Any | None = None
        self._initialized = False

        # Processing
        self._modulation_state: dict[str, float] = {}
        self._envelopes: dict[str, Any] = {}
        self._filters: dict[str, Any] = {}

        # Buffers (allocated on demand)
        self._output_buffer: np.ndarray | None = None
        self._work_buffer: np.ndarray | None = None

    # ========== LIFECYCLE MANAGEMENT ==========

    def initialize(self) -> bool:
        """
        Initialize region resources.

        Called automatically before first sample generation.
        Loads sample data and creates partial if needed.

        Returns:
            True if initialization succeeded, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Load sample data for sample-based engines
            if self.descriptor.sample_id is not None or self.descriptor.sample_path:
                self._sample_data = self._load_sample_data()
                if self._sample_data is None and self.descriptor.is_sample_based():
                    # Sample-based region requires sample data
                    return False

            # Create partial for audio generation
            self._partial = self._create_partial()
            if self._partial is None:
                return False

            # Initialize envelopes and filters
            self._init_envelopes()
            self._init_filters()

            # Allocate buffers
            self._allocate_buffers()

            self._initialized = True
            self.state = RegionState.INITIALIZED
            return True

        except Exception as e:
            # Log error using proper logging module
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Region initialization failed for {self.descriptor.engine_type}: {e}",
                exc_info=True,
                extra={
                    "region_id": self.descriptor.region_id,
                    "engine_type": self.descriptor.engine_type,
                    "sample_id": self.descriptor.sample_id,
                },
            )
            return False

    @abstractmethod
    def _load_sample_data(self) -> np.ndarray | None:
        """
        Load sample data (SF2/SFZ override, others return None).

        Returns:
            Sample data as numpy array, or None for algorithmic regions
        """
        pass

    @abstractmethod
    def _create_partial(self) -> Any | None:
        """
        Create synthesis partial for audio generation.

        Returns:
            SynthesisPartial instance or None if creation failed
        """
        pass

    @abstractmethod
    def _init_envelopes(self) -> None:
        """Initialize envelopes from generator parameters."""
        pass

    @abstractmethod
    def _init_filters(self) -> None:
        """Initialize filters from generator parameters."""
        pass

    def _allocate_buffers(self) -> None:
        """Allocate processing buffers."""
        # Allocate stereo output buffer
        self._output_buffer = np.zeros(self.block_size * 2, dtype=np.float32)
        self._work_buffer = np.zeros(self.block_size, dtype=np.float32)

    # ========== PLAYBACK ==========

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this region.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)

        Returns:
            True if region should play, False if it shouldn't
        """
        # Check if this region should play for this note/velocity
        if not self.descriptor.should_play_for_note(note, velocity):
            return False

        self.current_note = note
        self.current_velocity = velocity
        self.state = RegionState.ACTIVE

        # Initialize if not already done
        if not self._initialized:
            if not self.initialize():
                return False

        # Trigger partial
        if self._partial:
            if hasattr(self._partial, "note_on"):
                self._partial.note_on(velocity, note)

        return True

    def note_off(self) -> None:
        """Trigger note-off for this region."""
        self.state = RegionState.RELEASING

        if self._partial:
            if hasattr(self._partial, "note_off"):
                self._partial.note_off()

        # Release envelopes
        for envelope in self._envelopes.values():
            if hasattr(envelope, "note_off"):
                envelope.note_off()

    @abstractmethod
    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate audio samples for this region.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        pass

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation state.

        Args:
            modulation: Dictionary of modulation parameter updates
        """
        self._modulation_state.update(modulation)

        if self._partial:
            if hasattr(self._partial, "apply_modulation"):
                self._partial.apply_modulation(modulation)

    def is_active(self) -> bool:
        """
        Check if region is still producing sound.

        Returns:
            True if region should continue generating samples
        """
        if self.state == RegionState.RELEASED:
            return False

        if self.state == RegionState.RELEASING:
            # Check if envelope has completed
            if self._envelopes.get("amp_env"):
                env = self._envelopes["amp_env"]
                if hasattr(env, "is_active"):
                    return env.is_active()
            return False

        if self._partial:
            if hasattr(self._partial, "is_active"):
                return self._partial.is_active()

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    # ========== RESOURCE MANAGEMENT ==========

    def reset(self) -> None:
        """
        Reset region state for reuse.

        Called when region is returned to pool or reused.
        Does NOT release sample data (kept in cache).
        """
        self.state = RegionState.CREATED
        self.current_note = 0
        self.current_velocity = 0
        self._modulation_state.clear()

        # Reset partial if available
        if self._partial:
            if hasattr(self._partial, "reset"):
                self._partial.reset()

        # Reset envelopes
        for envelope in self._envelopes.values():
            if hasattr(envelope, "reset"):
                envelope.reset()

        self._initialized = False

    def dispose(self) -> None:
        """
        Release all resources.

        Called when region is no longer needed.
        Sample data may be cached or released based on memory pressure.
        """
        self.state = RegionState.RELEASED

        # Release partial
        if self._partial:
            if hasattr(self._partial, "dispose"):
                self._partial.dispose()
            self._partial = None

        # Release envelopes
        for envelope in self._envelopes.values():
            if hasattr(envelope, "dispose"):
                envelope.dispose()
        self._envelopes.clear()

        # Release filters
        for filter_obj in self._filters.values():
            if hasattr(filter_obj, "dispose"):
                filter_obj.dispose()
        self._filters.clear()

        # Release buffers
        self._output_buffer = None
        self._work_buffer = None

        # Sample data release handled by sample cache manager
        self._sample_data = None
        self.descriptor.is_sample_loaded = False

    # ========== UTILITY METHODS ==========

    def get_region_info(self) -> dict[str, Any]:
        """
        Get information about this region.

        Returns:
            Dictionary with region metadata and state
        """
        return {
            "region_id": self.descriptor.region_id,
            "engine_type": self.descriptor.engine_type,
            "key_range": self.descriptor.key_range,
            "velocity_range": self.descriptor.velocity_range,
            "state": self.state.name,
            "current_note": self.current_note,
            "current_velocity": self.current_velocity,
            "is_initialized": self._initialized,
            "is_sample_loaded": self.descriptor.is_sample_loaded,
        }

    def _get_generator_param(self, name: str, default: Any = None) -> Any:
        """
        Get a generator parameter from descriptor.

        Args:
            name: Parameter name
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        return self.descriptor.generator_params.get(name, default)

    def _get_algorithm_param(self, name: str, default: Any = None) -> Any:
        """
        Get an algorithm parameter from descriptor.

        Args:
            name: Parameter name
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        if self.descriptor.algorithm_params:
            return self.descriptor.algorithm_params.get(name, default)
        return default

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}(id={self.descriptor.region_id}, "
            f"type={self.descriptor.engine_type}, state={self.state.name})"
        )

    def __repr__(self) -> str:
        return self.__str__()


# Backward compatibility alias - Region is now IRegion
# Existing code (WavetableRegion, SFZRegion) can still import Region
Region = IRegion
