"""
Granular Partial Implementation

Provides granular synthesis partial for the voice-based architecture.
Wraps GranularEngine functionality for integration with the Voice system.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .partial import SynthesisPartial


class GranularPartial(SynthesisPartial):
    """
    Granular synthesis partial.

    Wraps granular synthesis engine functionality for use as a partial
    within the voice-based architecture.
    """

    def __init__(self, params: dict[str, Any], sample_rate: int):
        """
        Initialize granular partial.

        Args:
            params: Granular partial parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(params, sample_rate)

        # Granular-specific parameters
        self.density = params.get("density", 20.0)
        self.duration_ms = params.get("duration_ms", 100.0)
        self.position = params.get("position", 0.5)
        self.position_spread = params.get("position_spread", 0.2)
        self.pitch_shift = params.get("pitch_shift", 1.0)
        self.pitch_spread = params.get("pitch_spread", 0.1)
        self.pan_spread = params.get("pan_spread", 0.5)
        self.time_stretch = params.get("time_stretch", 1.0)
        self.freeze = params.get("freeze", False)

        # Create Granular engine instance for this partial
        from ...engines.granular import GranularEngine

        self.granular_engine = GranularEngine(
            max_clouds=1,  # Single cloud per partial
            sample_rate=sample_rate,
        )

        # Configure granular engine
        self.granular_engine.set_time_stretch(self.time_stretch)
        self.granular_engine.set_freeze(self.freeze)

        # Set up source buffer if provided
        source_buffer = params.get("source_buffer")
        if source_buffer is not None:
            self.granular_engine.set_source_buffer(np.array(source_buffer))

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate granular samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Use stored note and velocity for generation
        return self.granular_engine.generate_samples(
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

        # Create grain cloud for this note
        cloud_params = {
            "density": self.density,
            "duration_ms": self.duration_ms,
            "position": self.position,
            "position_spread": self.position_spread,
            "pitch_shift": self.pitch_shift,
            "pitch_spread": self.pitch_spread,
            "pan_spread": self.pan_spread,
        }

        self.granular_engine.create_grain_cloud(cloud_params)

    def note_off(self) -> None:
        """Handle note-off event."""
        super().note_off()
        self.granular_engine.note_off(self.params.get("note", 60))

    def is_active(self) -> bool:
        """
        Check if granular partial is still active.

        Returns:
            True if partial should continue generating samples
        """
        return self.active and self.granular_engine.is_active()

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        # Granular modulation is handled in real-time during sample generation
        # Additional modulation routing could be implemented here

        # Update time stretch based on modulation
        time_stretch_mod = modulation.get("time_stretch", 0.0)
        if time_stretch_mod != 0.0:
            new_stretch = self.time_stretch * (1.0 + time_stretch_mod)
            self.granular_engine.set_time_stretch(new_stretch)

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        if hasattr(self, "granular_engine"):
            self.granular_engine.reset()

    def set_source_buffer(self, audio_buffer: np.ndarray):
        """
        Set source audio buffer for granular processing.

        Args:
            audio_buffer: Mono or stereo audio buffer
        """
        if hasattr(self, "granular_engine"):
            self.granular_engine.set_source_buffer(audio_buffer)

    def set_grain_parameters(
        self, density: float = None, duration_ms: float = None, position_spread: float = None
    ):
        """
        Set grain parameters dynamically.

        Args:
            density: Grains per second
            duration_ms: Grain duration in milliseconds
            position_spread: Position randomization (0.0-1.0)
        """
        if density is not None:
            self.density = max(1.0, min(200.0, density))
        if duration_ms is not None:
            self.duration_ms = max(10.0, min(1000.0, duration_ms))
        if position_spread is not None:
            self.position_spread = max(0.0, min(1.0, position_spread))

        # Update active clouds
        if hasattr(self, "granular_engine"):
            cloud_params = {
                "density": self.density,
                "duration_ms": self.duration_ms,
                "position_spread": self.position_spread,
            }
            self.granular_engine.set_cloud_parameters(0, cloud_params)

    def get_partial_info(self) -> dict[str, Any]:
        """Get granular partial information."""
        info = super().get_partial_info()
        info.update(
            {
                "engine_type": "granular",
                "density": self.density,
                "duration_ms": self.duration_ms,
                "position": self.position,
                "position_spread": self.position_spread,
                "pitch_shift": self.pitch_shift,
                "pitch_spread": self.pitch_spread,
                "pan_spread": self.pan_spread,
                "time_stretch": self.time_stretch,
                "freeze": self.freeze,
                "granular_engine_info": self.granular_engine.get_engine_info()
                if hasattr(self.granular_engine, "get_engine_info")
                else {},
            }
        )
        return info
