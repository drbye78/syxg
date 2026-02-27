"""
FM Partial Implementation

Provides FM synthesis partial for the voice-based architecture.
Wraps FMEngine functionality for integration with the Voice system.
"""
from __future__ import annotations

from typing import Any
import numpy as np

from .partial import SynthesisPartial


class FMPartial(SynthesisPartial):
    """
    FM synthesis partial.

    Wraps FM synthesis engine functionality for use as a partial
    within the voice-based architecture.
    """

    def __init__(self, params: dict[str, Any], sample_rate: int):
        """
        Initialize FM partial.

        Args:
            params: FM partial parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(params, sample_rate)

        # FM-specific parameters
        self.algorithm = params.get('algorithm', 'basic')
        self.num_operators = params.get('num_operators', 6)
        self.operator_params = params.get('operator_params', {})

        # Create FM engine instance for this partial
        from ..engine.fm_engine import FMEngine
        self.fm_engine = FMEngine(
            num_operators=self.num_operators,
            sample_rate=sample_rate
        )

        # Configure FM engine
        self.fm_engine.set_algorithm(self.algorithm)

        # Set operator parameters
        for op_idx, op_params in self.operator_params.items():
            if isinstance(op_idx, int) and 0 <= op_idx < self.num_operators:
                self.fm_engine.set_operator_parameters(op_idx, op_params)

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate FM synthesis samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Use stored note and velocity for generation
        return self.fm_engine.generate_samples(
            self.params.get('note', 60),
            self.params.get('velocity', 100),
            modulation,
            block_size
        )

    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        super().note_on(velocity, note)
        self.fm_engine.note_on(note, velocity)

    def note_off(self) -> None:
        """Handle note-off event."""
        super().note_off()
        self.fm_engine.note_off(self.params.get('note', 60))

    def is_active(self) -> bool:
        """
        Check if FM partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active and self.fm_engine.is_active()

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        # FM modulation is handled in real-time during sample generation
        # Additional modulation routing could be implemented here
        pass

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        if hasattr(self, 'fm_engine'):
            self.fm_engine.reset()

    def get_partial_info(self) -> dict[str, Any]:
        """Get FM partial information."""
        info = super().get_partial_info()
        info.update({
            'engine_type': 'fm',
            'algorithm': self.algorithm,
            'num_operators': self.num_operators,
            'fm_engine_info': self.fm_engine.get_engine_info() if hasattr(self.fm_engine, 'get_engine_info') else {}
        })
        return info
