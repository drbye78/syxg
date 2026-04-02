"""
Spectral Region - Production-grade FFT-based spectral synthesis region.

Part of the unified region-based synthesis architecture.
SpectralRegion implements spectral synthesis with:
- FFT-based spectral processing
- Real-time spectral morphing
- Harmonic enhancement
- Spectral filtering
- Freeze/morph effects
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class SpectralRegion(IRegion):
    """
    Production-grade spectral synthesis region with FFT processing.

    Features:
    - FFT-based spectral analysis and synthesis
    - Real-time spectral morphing between presets
    - Harmonic enhancement and suppression
    - Spectral filtering (bandpass, notch, etc.)
    - Freeze/morph effects
    - Spectral noise injection

    Attributes:
        descriptor: Region metadata with spectral parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_fft_processor",
        "_fft_size",
        "_freeze_enabled",
        "_frozen_spectrum",
        "_harmonic_enhancement",
        "_hop_size",
        "_morph_factor",
        "_noise_injection",
        "_spectral_buffer",
        "_spectral_filter",
    ]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize spectral region.

        Args:
            descriptor: Region metadata with spectral parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # FFT parameters
        self._fft_size = algo_params.get("fft_size", 2048)
        self._hop_size = algo_params.get("hop_size", 512)

        # Spectral processing parameters
        self._morph_factor = algo_params.get("morph_factor", 0.0)
        self._harmonic_enhancement = algo_params.get("harmonic_enhancement", 1.0)
        self._spectral_filter = algo_params.get("spectral_filter", "passthrough")
        self._freeze_enabled = algo_params.get("freeze_enabled", False)
        self._noise_injection = algo_params.get("noise_injection", 0.0)

        # Runtime state
        self._spectral_buffer: np.ndarray | None = None
        self._frozen_spectrum: np.ndarray | None = None
        self._fft_processor: Any | None = None

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for spectral (FFT processing)."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create spectral synthesis partial.

        Returns:
            SpectralPartial instance or None if creation failed
        """
        try:
            # Create FFT processor
            self._fft_processor = self._create_fft_processor()

            if self._fft_processor is None:
                logger.warning("Failed to create FFT processor")
                return None

            # Initialize spectral buffer
            self._spectral_buffer = np.zeros(self._fft_size, dtype=np.complex128)

            # Build partial parameters
            partial_params = {
                "fft_processor": self._fft_processor,
                "fft_size": self._fft_size,
                "hop_size": self._hop_size,
                "morph_factor": self._morph_factor,
                "harmonic_enhancement": self._harmonic_enhancement,
                "spectral_filter": self._spectral_filter,
                "freeze_enabled": self._freeze_enabled,
                "noise_injection": self._noise_injection,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create spectral partial
            from ..partial.spectral_partial import SpectralPartial

            partial = SpectralPartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create spectral partial: {e}")
            return None

    def _create_fft_processor(self) -> Any | None:
        """
        Create FFT processor for spectral analysis/synthesis.

        Returns:
            FFTProcessor instance or None
        """
        try:
            from ..engine.spectral_engine import FFTProcessor

            processor = FFTProcessor(
                fft_size=self._fft_size, hop_size=self._hop_size, window_type="hann"
            )

            return processor

        except Exception as e:
            logger.error(f"Failed to create FFT processor: {e}")
            return None

    def _init_envelopes(self) -> None:
        """Initialize envelopes for spectral region."""
        try:
            from ..core.envelope import UltraFastADSREnvelope

            # Get envelope parameters
            env_params = self.descriptor.generator_params

            self._envelopes["amp_env"] = UltraFastADSREnvelope(
                delay=env_params.get("amp_delay", 0.0),
                attack=env_params.get("amp_attack", 0.01),
                hold=env_params.get("amp_hold", 0.0),
                decay=env_params.get("amp_decay", 0.3),
                sustain=env_params.get("amp_sustain", 0.7),
                release=env_params.get("amp_release", 0.5),
                sample_rate=self.sample_rate,
            )

        except Exception as e:
            logger.error(f"Failed to create envelope: {e}")

    def _init_filters(self) -> None:
        """Initialize spectral filters."""
        # Spectral filtering is handled by FFT processor
        pass

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this spectral region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Initialize spectral buffer with harmonic content based on note
        self._initialize_spectrum_for_note(note, velocity)

        return True

    def _initialize_spectrum_for_note(self, note: int, velocity: int) -> None:
        """
        Initialize spectrum with harmonics for given note.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
        """
        if self._spectral_buffer is None:
            return

        # Calculate fundamental frequency bin
        fundamental_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
        bin_size = self.sample_rate / self._fft_size
        fundamental_bin = int(fundamental_freq / bin_size)

        # Add harmonics with decreasing amplitude
        velocity_scale = velocity / 127.0
        for harmonic in range(1, min(20, self._fft_size // fundamental_bin // 2)):
            bin_index = fundamental_bin * harmonic
            if bin_index < self._fft_size // 2:
                # Harmonic amplitude decreases with harmonic number
                amplitude = velocity_scale / harmonic
                amplitude *= self._harmonic_enhancement

                # Set magnitude in spectrum
                self._spectral_buffer[bin_index] = amplitude
                # Conjugate for negative frequencies
                self._spectral_buffer[self._fft_size - bin_index] = amplitude

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from spectral processing.

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

            # Apply envelope if present
            if "amp_env" in self._envelopes:
                env = self._envelopes["amp_env"]
                if hasattr(env, "generate_block"):
                    env_buffer = np.zeros(block_size, dtype=np.float32)
                    env.generate_block(env_buffer, block_size)
                    samples[:, :] *= env_buffer[:, np.newaxis]

            return samples

        except Exception as e:
            logger.error(f"Spectral sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation to spectral parameters.

        Args:
            modulation: Modulation values dictionary
        """
        # Mod wheel to morph factor
        mod_wheel = modulation.get("mod_wheel", 0.0)
        if mod_wheel > 0:
            self._morph_factor = min(1.0, mod_wheel)

        # Aftertouch to harmonic enhancement
        aftertouch = modulation.get("channel_aftertouch", 0.0)
        if aftertouch > 0 and self._partial:
            enhancement = self._harmonic_enhancement * (1.0 + aftertouch)
            if hasattr(self._partial, "set_harmonic_enhancement"):
                self._partial.set_harmonic_enhancement(enhancement)

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation state.

        Args:
            modulation: Modulation parameter updates
        """
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if spectral region is still producing sound."""
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
                "fft_size": self._fft_size,
                "hop_size": self._hop_size,
                "morph_factor": self._morph_factor,
                "harmonic_enhancement": self._harmonic_enhancement,
                "spectral_filter": self._spectral_filter,
                "freeze_enabled": self._freeze_enabled,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SpectralRegion(fft={self._fft_size}, "
            f"morph={self._morph_factor:.2f}, freeze={self._freeze_enabled})"
        )
