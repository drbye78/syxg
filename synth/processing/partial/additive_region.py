"""
Additive Region - Production-grade additive synthesis region.

Part of the unified region-based synthesis architecture.
AdditiveRegion implements additive synthesis with:
- Up to 128 harmonic partials
- Real-time spectral morphing
- Bandwidth optimization
- Individual partial envelopes
- Brightness and spread control
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ...engines.region_descriptor import RegionDescriptor
from ...processing.partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class AdditiveRegion(IRegion):
    """
    Production-grade additive region with spectral morphing.

    Features:
    - Up to 128 harmonic partials
    - Real-time spectral morphing between presets
    - Bandwidth optimization (removes inaudible partials)
    - Velocity-based brightness control
    - Stereo spread for harmonics

    Attributes:
        descriptor: Region metadata with additive parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_bandwidth_limit",
        "_brightness",
        "_max_partials",
        "_morph_factor",
        "_partial_envelopes",
        "_spectrum",
        "_spectrum_type",
        "_spread",
        "_target_spectrum",
        "_velocity_to_brightness",
    ]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize additive region.

        Args:
            descriptor: Region metadata with additive parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Spectrum parameters
        self._spectrum_type = algo_params.get("spectrum_type", "sawtooth")
        self._max_partials = min(128, algo_params.get("max_partials", 64))
        self._brightness = algo_params.get("brightness", 1.0)
        self._spread = algo_params.get("spread", 0.0)

        # Morphing parameters
        self._morph_factor = algo_params.get("morph_factor", 0.0)
        self._bandwidth_limit = algo_params.get("bandwidth_limit", 20000.0)

        # Modulation parameters
        self._velocity_to_brightness = algo_params.get("velocity_to_brightness", 0.0)

        # Runtime state
        self._spectrum: Any | None = None
        self._target_spectrum: Any | None = None
        self._partial_envelopes: list[Any] = []

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for additive (algorithmic synthesis)."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create additive synthesis partial bank.

        Returns:
            AdditivePartial instance or None if creation failed
        """
        try:
            # Create spectrum based on type
            self._spectrum = self._create_spectrum(self._spectrum_type)

            if self._spectrum is None:
                logger.warning(f"Failed to create spectrum type '{self._spectrum_type}'")
                return None

            # Apply brightness scaling
            self._apply_brightness(self._spectrum)

            # Apply bandwidth optimization
            self._apply_bandwidth_optimization(self._spectrum)

            # Create partial envelopes
            self._create_partial_envelopes()

            # Build partial parameters
            partial_params = {
                "spectrum": self._spectrum,
                "max_partials": self._max_partials,
                "brightness": self._brightness,
                "spread": self._spread,
                "bandwidth_limit": self._bandwidth_limit,
                "partial_envelopes": self._partial_envelopes,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create additive partial
            from ...processing.partial.additive_partial import AdditivePartial

            partial = AdditivePartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create additive partial: {e}")
            return None

    def _create_spectrum(self, spectrum_type: str) -> Any | None:
        """
        Create harmonic spectrum.

        Args:
            spectrum_type: Type of spectrum ('sawtooth', 'square', 'triangle', 'custom')

        Returns:
            HarmonicSpectrum instance or None
        """
        try:
            from ...engines.additive import AdditiveEngine

            spectrum = HarmonicSpectrum(spectrum_type)

            if spectrum_type == "sawtooth":
                spectrum.create_sawtooth(self._max_partials)
            elif spectrum_type == "square":
                spectrum.create_square(self._max_partials)
            elif spectrum_type == "triangle":
                spectrum.create_triangle(self._max_partials)
            elif spectrum_type == "sine":
                spectrum.clear()
                spectrum.set_harmonic(1, 1.0)  # Only fundamental
            else:
                # Default to sawtooth
                spectrum.create_sawtooth(self._max_partials)

            return spectrum

        except Exception as e:
            logger.error(f"Failed to create spectrum: {e}")
            return None

    def _apply_brightness(self, spectrum: Any) -> None:
        """
        Apply brightness scaling to spectrum.

        Args:
            spectrum: HarmonicSpectrum instance
        """
        if self._brightness == 1.0:
            return  # No change needed

        # Scale harmonic amplitudes based on brightness
        # Brightness > 1.0: boost high harmonics
        # Brightness < 1.0: attenuate high harmonics
        for harmonic_num in range(1, self._max_partials + 1):
            harmonic = spectrum.get_harmonic(harmonic_num)
            if harmonic:
                # Brightness curve: higher harmonics affected more
                brightness_factor = self._brightness ** (harmonic_num / 16.0)
                harmonic["amplitude"] *= brightness_factor

    def _apply_bandwidth_optimization(self, spectrum: Any) -> None:
        """
        Remove partials above bandwidth limit.

        Args:
            spectrum: HarmonicSpectrum instance
        """
        # Calculate fundamental frequency
        base_freq = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))

        # Remove partials above bandwidth limit
        for harmonic_num in range(self._max_partials, 0, -1):
            partial_freq = base_freq * harmonic_num
            if partial_freq > self._bandwidth_limit:
                # Remove this harmonic
                harmonic = spectrum.get_harmonic(harmonic_num)
                if harmonic:
                    harmonic["amplitude"] = 0.0

    def _create_partial_envelopes(self) -> None:
        """Create individual envelopes for each partial."""
        self._partial_envelopes.clear()

        try:
            from ...primitives.envelope import UltraFastADSREnvelope

            # Get envelope parameters from descriptor
            env_params = self.descriptor.generator_params

            for i in range(self._max_partials):
                # Higher partials can have faster envelopes
                partial_factor = 1.0 - (i / self._max_partials) * 0.5

                envelope = UltraFastADSREnvelope(
                    delay=env_params.get("amp_delay", 0.0),
                    attack=env_params.get("amp_attack", 0.01) / partial_factor,
                    hold=env_params.get("amp_hold", 0.0),
                    decay=env_params.get("amp_decay", 0.3) / partial_factor,
                    sustain=env_params.get("amp_sustain", 0.7),
                    release=env_params.get("amp_release", 0.5) / partial_factor,
                    sample_rate=self.sample_rate,
                )

                self._partial_envelopes.append(envelope)

        except Exception as e:
            logger.error(f"Failed to create partial envelopes: {e}")
            self._partial_envelopes = []

    def _init_envelopes(self) -> None:
        """Initialize envelopes (already done in _create_partial)."""
        pass

    def _init_filters(self) -> None:
        """Initialize filters for additive region."""
        try:
            from ...primitives.filter import UltraFastResonantFilter

            # Get filter parameters
            cutoff = self.descriptor.generator_params.get("filter_cutoff", 20000.0)
            resonance = self.descriptor.generator_params.get("filter_resonance", 0.0)
            filter_type = self.descriptor.generator_params.get("filter_type", "lowpass")

            self._filters["filter"] = UltraFastResonantFilter(
                cutoff=cutoff,
                resonance=resonance,
                filter_type=filter_type,
                sample_rate=self.sample_rate,
            )

        except Exception as e:
            logger.error(f"Failed to initialize filter: {e}")

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this additive region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Recreate spectrum with velocity-based brightness
        if self._velocity_to_brightness > 0:
            brightness_mod = self._velocity_to_brightness * (velocity / 127.0)
            effective_brightness = self._brightness * (1.0 + brightness_mod)
            self._brightness = min(2.0, max(0.5, effective_brightness))

        # Recreate spectrum with new parameters
        self._spectrum = self._create_spectrum(self._spectrum_type)
        if self._spectrum:
            self._apply_brightness(self._spectrum)
            self._apply_bandwidth_optimization(self._spectrum)

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from additive partial.

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
                        logger.error(f"Additive filter processing failed: {e}")

            return samples

        except Exception as e:
            logger.error(f"Additive sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation to additive parameters.

        Args:
            modulation: Modulation values dictionary
        """
        # Mod wheel to brightness
        mod_wheel = modulation.get("mod_wheel", 0.0)
        if mod_wheel > 0 and self._velocity_to_brightness > 0:
            brightness_mod = mod_wheel * self._velocity_to_brightness
            # Apply to partial amplitudes
            if self._partial and hasattr(self._partial, "set_brightness"):
                self._partial.set_brightness(self._brightness * (1.0 + brightness_mod))

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation state.

        Args:
            modulation: Modulation parameter updates
        """
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if additive region is still producing sound."""
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
                "spectrum_type": self._spectrum_type,
                "max_partials": self._max_partials,
                "brightness": self._brightness,
                "spread": self._spread,
                "bandwidth_limit": self._bandwidth_limit,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"AdditiveRegion(type={self._spectrum_type}, "
            f"partials={self._max_partials}, brightness={self._brightness:.2f})"
        )
