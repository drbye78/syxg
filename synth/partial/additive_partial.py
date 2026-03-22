"""
Additive Partial Implementation

Provides additive synthesis partial for the voice-based architecture.
Wraps AdditiveEngine functionality for integration with the Voice system.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .partial import SynthesisPartial


class AdditivePartial(SynthesisPartial):
    """
    Additive synthesis partial.

    Wraps additive synthesis engine functionality for use as a partial
    within the voice-based architecture.
    """

    def __init__(self, params: dict[str, Any], sample_rate: int):
        """
        Initialize additive partial.

        Args:
            params: Additive partial parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(params, sample_rate)

        # Additive-specific parameters
        self.spectrum_type = params.get("spectrum_type", "sawtooth")
        self.num_partials = params.get("num_partials", 32)
        self.brightness = params.get("brightness", 1.0)
        self.spread = params.get("spread", 0.0)
        self.harmonic_params = params.get("harmonic_params", {})

        # Create Additive engine instance for this partial
        from ..engine.additive_engine import AdditiveEngine

        self.additive_engine = AdditiveEngine(
            max_partials=self.num_partials, sample_rate=sample_rate
        )

        # Configure additive engine
        self.additive_engine.set_spectrum_type(self.spectrum_type, self.num_partials)
        self.additive_engine.set_brightness(self.brightness)
        self.additive_engine.set_spread(self.spread)

        # Set individual harmonic parameters if provided
        for harmonic_idx, harmonic_params in self.harmonic_params.items():
            if isinstance(harmonic_idx, int) and 0 <= harmonic_idx < self.num_partials:
                self.additive_engine.set_partial_parameters(harmonic_idx, harmonic_params)

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate additive synthesis samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Use stored note and velocity for generation
        return self.additive_engine.generate_samples(
            self.params.get("note", 60), self.params.get("velocity", 100), modulation, block_size
        )

    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        super().note_on(velocity, note)
        self.additive_engine.note_on(note, velocity)

    def note_off(self) -> None:
        """Handle note-off event."""
        super().note_off()
        self.additive_engine.note_off(self.params.get("note", 60))

    def is_active(self) -> bool:
        """
        Check if additive partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active and self.additive_engine.is_active()

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        # Additive modulation is handled in real-time during sample generation
        # Additional modulation routing could be implemented here
        pass

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        if hasattr(self, "additive_engine"):
            self.additive_engine.reset()

    def get_partial_info(self) -> dict[str, Any]:
        """Get additive partial information."""
        info = super().get_partial_info()
        info.update(
            {
                "engine_type": "additive",
                "spectrum_type": self.spectrum_type,
                "num_partials": self.num_partials,
                "brightness": self.brightness,
                "spread": self.spread,
                "additive_engine_info": self.additive_engine.get_engine_info()
                if hasattr(self.additive_engine, "get_engine_info")
                else {},
            }
        )
        return info
