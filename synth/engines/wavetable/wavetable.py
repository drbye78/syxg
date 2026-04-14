"""Wavetable data structure."""
from __future__ import annotations

import numpy as np


class Wavetable:
    """
    Single wavetable with interpolation and morphing capabilities.

    A wavetable is a single cycle waveform stored at high resolution
    for efficient playback with pitch control.
    """

    def __init__(self, data: np.ndarray, sample_rate: int = 44100, name: str = "unnamed"):
        """
        Initialize wavetable from audio data.

        Args:
            data: Audio waveform data (mono)
            sample_rate: Original sample rate
            name: Wavetable name for identification
        """
        self.name = name
        self.sample_rate = sample_rate

        # Ensure mono data
        if data.ndim > 1:
            data = data[:, 0]  # Take first channel

        # Remove DC offset
        data = data - np.mean(data)

        # Normalize to prevent clipping
        max_val = np.max(np.abs(data))
        if max_val > 0:
            data = data / max_val * 0.9  # Leave some headroom

        self.data = data.astype(np.float32)
        self.length = len(data)

        # Pre-compute for efficiency
        self._build_interpolation_tables()

    def _build_interpolation_tables(self):
        """Build interpolation tables for efficient playback."""
        # Linear interpolation is sufficient for wavetable synthesis
        # More advanced interpolation can be added later if needed
        pass

    def get_sample(self, phase: float) -> float:
        """
        Get sample at specified phase (0.0 to 1.0).

        Args:
            phase: Phase position (0.0 to 1.0)

        Returns:
            Interpolated sample value
        """
        # Convert phase to index
        index = phase * (self.length - 1)

        # Linear interpolation
        index_int = int(index)
        frac = index - index_int

        # Handle wraparound
        next_index = (index_int + 1) % self.length

        # Interpolate
        sample1 = self.data[index_int]
        sample2 = self.data[next_index]

        return sample1 + (sample2 - sample1) * frac

    def get_samples(self, phases: np.ndarray) -> np.ndarray:
        """
        Get multiple samples efficiently.

        Args:
            phases: Array of phase positions

        Returns:
            Array of interpolated samples
        """
        # Vectorized linear interpolation
        indices = phases * (self.length - 1)

        # Split into integer and fractional parts
        index_int = indices.astype(np.int32)
        frac = indices - index_int

        # Handle wraparound
        next_index = (index_int + 1) % self.length

        # Interpolate
        sample1 = self.data[index_int % self.length]
        sample2 = self.data[next_index % self.length]

        return sample1 + (sample2 - sample1) * frac


