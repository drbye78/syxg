"""ArticulationProcessor — abstract base for all modular DSP processors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from .context import ArticulationContext


class ArticulationProcessor(ABC):
    """Abstract base class for all articulation DSP processors.

    Each processor handles a category of articulations (pitch, envelope,
    filter, noise, etc.) and is instantiated once per ArticulationEngine
    (lazy-init, reused across voices).

    Hot-path contract:
    - process() modifies buf in-place. No allocation.
    - reset() clears state for voice reuse.
    - Processors operate on stereo (n, 2) float32 buffers.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

    @abstractmethod
    def process(
        self,
        buf: np.ndarray,
        context: ArticulationContext,
        params: dict[str, Any],
    ) -> None:
        """Apply articulation to stereo buffer in-place.

        Args:
            buf: Stereo (n, 2) float32 buffer. Modified in-place.
            context: Voice/note/instrument context.
            params: Articulation-specific parameters from the registry.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset processor state for voice reuse. Called on note-off."""
        ...
