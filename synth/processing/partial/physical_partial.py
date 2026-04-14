"""
Physical Partial Implementation

Provides physical modeling partial for the voice-based architecture.
Wraps PhysicalEngine functionality for integration with the Voice system.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .partial import SynthesisPartial


class PhysicalPartial(SynthesisPartial):
    """
    Physical modeling partial.

    Wraps physical modeling engine functionality for use as a partial
    within the voice-based architecture.
    """

    def __init__(self, params: dict[str, Any], sample_rate: int):
        """
        Initialize physical modeling partial.

        Args:
            params: Physical modeling partial parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(params, sample_rate)

        # Physical modeling-specific parameters
        self.model_type = params.get("model_type", "pluck")
        self.brightness = params.get("brightness", 1.0)
        self.damping = params.get("damping", 0.99)
        self.scattering_coeff = params.get("scattering_coeff", 0.5)
        self.excitation_type = params.get("excitation_type", "pluck")

        # Create Physical engine instance for this partial
        from ...engines.physical_engine import PhysicalEngine

        self.physical_engine = PhysicalEngine(
            max_strings=1,  # Single string/waveguide per partial
            sample_rate=sample_rate,
        )

        # Configure physical engine
        self.physical_engine.set_model_type(0, self.model_type)
        self.physical_engine.set_brightness(self.brightness)
        self.physical_engine.set_damping(self.damping)

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate physical modeling samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Use stored note and velocity for generation
        return self.physical_engine.generate_samples(
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

        # Excite the physical model
        model_params = {
            "scattering_coeff": self.scattering_coeff,
            "brightness": self.brightness,
            "damping": self.damping,
        }

        self.physical_engine.excite_voice(0, note, velocity, model_params)

    def note_off(self) -> None:
        """Handle note-off event."""
        super().note_off()
        self.physical_engine.release_voice(0)

    def is_active(self) -> bool:
        """
        Check if physical partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active and self.physical_engine.is_active()

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        # Physical modulation is handled in real-time during sample generation
        # Additional modulation routing could be implemented here
        pass

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        if hasattr(self, "physical_engine"):
            self.physical_engine.reset()

    def get_partial_info(self) -> dict[str, Any]:
        """Get physical partial information."""
        info = super().get_partial_info()
        info.update(
            {
                "engine_type": "physical",
                "model_type": self.model_type,
                "brightness": self.brightness,
                "damping": self.damping,
                "scattering_coeff": self.scattering_coeff,
                "physical_engine_info": self.physical_engine.get_engine_info()
                if hasattr(self.physical_engine, "get_engine_info")
                else {},
            }
        )
        return info
