"""Wavetable partial."""
from __future__ import annotations
from typing import Any
import numpy as np
from ...processing.partial.partial import SynthesisPartial
from ...processing.partial.region import Region
from .oscillator import WavetableOscillator
class WavetablePartial(SynthesisPartial):
    """
    Wavetable synthesis partial that wraps a WavetableOscillator.

    Implements the SynthesisPartial interface for wavetable-based synthesis.
    """

    def __init__(self, params: dict[str, Any], sample_rate: int, wavetable_bank: WavetableBank):
        """
        Initialize wavetable partial.

        Args:
            params: Partial parameters
            sample_rate: Audio sample rate
            wavetable_bank: Reference to wavetable bank
        """
        super().__init__(params, sample_rate)
        self.wavetable_bank = wavetable_bank
        self.oscillator = WavetableOscillator(sample_rate)

        # Configure oscillator
        self._configure_oscillator()

    def _configure_oscillator(self):
        """Configure the oscillator based on current parameters."""
        # Set wavetable
        wt_name = self.params.get("wavetable", "sine")
        wavetable = self.wavetable_bank.get_wavetable(wt_name)
        if wavetable:
            self.oscillator.set_wavetable(wavetable)

        # Set other parameters
        if "frequency" in self.params:
            self.oscillator.set_frequency(self.params["frequency"])
        if "amplitude" in self.params:
            self.oscillator.set_amplitude(self.params["amplitude"])

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate audio samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        if not self.active:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Apply modulation
        freq_mod = modulation.get("pitch", 0.0) / 1200.0  # Convert cents to ratio
        amp_mod = modulation.get("volume", 0.0)
        wt_pos = modulation.get("timbre", 0.0)

        self.oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

        # Generate mono samples
        mono_samples = self.oscillator.generate_samples(block_size)

        # Convert to stereo (2D interleaved format)
        stereo_samples = np.zeros((block_size, 2), dtype=np.float32)
        stereo_samples[:, 0] = mono_samples  # Left channel
        stereo_samples[:, 1] = mono_samples  # Right channel

        return stereo_samples

    def is_active(self) -> bool:
        """Check if partial is active."""
        return self.active and self.oscillator.is_active()

    def note_on(self, velocity: int, note: int) -> None:
        """Handle note-on event."""
        self.active = True
        self.oscillator.set_note(note, velocity)

    def note_off(self) -> None:
        """Handle note-off event."""
        self.oscillator.note_off()
        # Keep partial active for release if needed

    def apply_modulation(self, modulation: dict[str, float]) -> None:
        """Apply modulation changes."""
        # Update oscillator modulation
        freq_mod = modulation.get("pitch", 0.0) / 1200.0
        amp_mod = modulation.get("volume", 0.0)
        wt_pos = modulation.get("timbre", 0.0)

        self.oscillator.update_modulation(freq_mod, amp_mod, wt_pos)

    def reset(self) -> None:
        """Reset partial to initial state."""
        super().reset()
        self.oscillator.reset()

    def update_parameter(self, param_name: str, value: Any) -> None:
        """Update a parameter and reconfigure if needed."""
        super().update_parameter(param_name, value)

        # Reconfigure oscillator if relevant parameters changed
        if param_name in ["wavetable", "frequency", "amplitude"]:
            self._configure_oscillator()


