"""
Advanced Physical Region - Production-grade advanced physical modeling region.

Part of the unified region-based synthesis architecture.
AdvancedPhysicalRegion implements advanced physical modeling with:
- Multi-body coupling
- Non-linear behavior
- Environmental modeling
- Complex resonator networks
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class AdvancedPhysicalRegion(IRegion):
    """
    Production-grade advanced physical modeling region.

    Features:
    - Multi-body coupled resonators
    - Non-linear behavior modeling
    - Environmental factors (temperature, humidity)
    - Complex material properties
    - Modal synthesis support
    - Interactive physical modeling

    Attributes:
        descriptor: Region metadata with physical parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_advanced_model",
        "_coupling_matrix",
        "_environment",
        "_material_properties",
        "_modal_frequencies",
        "_nonlinearity",
        "_resonator_count",
        "_resonator_network",
    ]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize advanced physical region.

        Args:
            descriptor: Region metadata with physical parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Resonator network parameters
        self._resonator_count = min(16, algo_params.get("resonator_count", 4))
        self._coupling_matrix = algo_params.get("coupling_matrix", "linear")
        self._nonlinearity = algo_params.get("nonlinearity", 0.0)

        # Environmental parameters
        self._environment = {
            "temperature": algo_params.get("temperature", 20.0),  # Celsius
            "humidity": algo_params.get("humidity", 50.0),  # Percent
            "pressure": algo_params.get("pressure", 1.0),  # Atmospheres
        }

        # Material properties
        self._material_properties = {
            "density": algo_params.get("density", 1.0),
            "stiffness": algo_params.get("stiffness", 1.0),
            "damping": algo_params.get("material_damping", 0.5),
        }

        # Modal frequencies (for modal synthesis)
        self._modal_frequencies = algo_params.get("modal_frequencies", None)

        # Runtime state
        self._advanced_model: Any | None = None
        self._resonator_network: list[Any] = []

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for advanced physical modeling."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create advanced physical modeling partial.

        Returns:
            AdvancedPhysicalPartial instance or None
        """
        try:
            # Create advanced physical model
            self._advanced_model = self._create_advanced_model()

            if self._advanced_model is None:
                logger.warning("Failed to create advanced physical model")
                return None

            # Create resonator network
            self._create_resonator_network()

            # Build partial parameters
            partial_params = {
                "advanced_model": self._advanced_model,
                "resonator_network": self._resonator_network,
                "resonator_count": self._resonator_count,
                "coupling_matrix": self._coupling_matrix,
                "nonlinearity": self._nonlinearity,
                "environment": self._environment,
                "material_properties": self._material_properties,
                "modal_frequencies": self._modal_frequencies,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create partial
            from ..partial.advanced_physical_partial import AdvancedPhysicalPartial

            partial = AdvancedPhysicalPartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create advanced physical partial: {e}")
            return None

    def _create_advanced_model(self) -> Any | None:
        """
        Create advanced physical model instance.

        Returns:
            AdvancedPhysicalModel instance or None
        """
        try:
            from ..engine.advanced_physical_engine import AdvancedPhysicalModel

            model = AdvancedPhysicalModel(self.sample_rate)

            # Set environmental parameters
            model.set_environment(self._environment)

            # Set material properties
            model.set_material_properties(self._material_properties)

            # Set nonlinearity
            model.set_nonlinearity(self._nonlinearity)

            return model

        except Exception as e:
            logger.error(f"Failed to create advanced model: {e}")
            return None

    def _create_resonator_network(self) -> None:
        """Create network of coupled resonators."""
        self._resonator_network.clear()

        try:
            from ..core.waveguide import DigitalWaveguide

            base_frequency = self._calculate_frequency()

            for i in range(self._resonator_count):
                waveguide = DigitalWaveguide(self.sample_rate)

                # Set frequency for this resonator
                if self._modal_frequencies and i < len(self._modal_frequencies):
                    freq = self._modal_frequencies[i]
                else:
                    # Harmonic series with slight detuning
                    freq = base_frequency * (i + 1) * (1.0 + np.random.uniform(-0.001, 0.001))

                waveguide.set_frequency(freq)

                # Set resonator parameters
                waveguide.set_parameters(
                    {
                        "scattering_coeff": self._material_properties["stiffness"],
                        "loop_filter_coeff": 1.0 - self._material_properties["damping"] * 0.1,
                        "body_size": 1.0 / (i + 1),  # Higher modes are smaller
                    }
                )

                self._resonator_network.append(waveguide)

        except Exception as e:
            logger.error(f"Failed to create resonator network: {e}")

    def _calculate_frequency(self) -> float:
        """Calculate frequency for current note."""
        frequency = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))

        fine_tune = self.descriptor.generator_params.get("fine_tune", 0.0)
        frequency *= 2.0 ** (fine_tune / 1200.0)

        return frequency

    def _init_envelopes(self) -> None:
        """Initialize envelopes (handled by advanced model)."""
        pass

    def _init_filters(self) -> None:
        """Initialize filters (handled by advanced model)."""
        pass

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this advanced physical region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Excite all resonators in network
        for i, resonator in enumerate(self._resonator_network):
            if hasattr(resonator, "excite"):
                # Velocity affects excitation strength
                # Higher modes are excited less
                strength = (velocity / 127.0) * (1.0 / (i + 1))
                resonator.excite("strike", strength)

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from advanced physical model.

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

            return samples

        except Exception as e:
            logger.error(f"Advanced physical sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """Apply modulation to advanced physical parameters."""
        # Aftertouch to nonlinearity
        aftertouch = modulation.get("channel_aftertouch", 0.0)
        if aftertouch > 0 and self._advanced_model:
            if hasattr(self._advanced_model, "set_nonlinearity"):
                nonlin = self._nonlinearity * (1.0 + aftertouch * 2.0)
                self._advanced_model.set_nonlinearity(min(1.0, nonlin))

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """Update modulation state."""
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if advanced physical region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False

        # Check if any resonator still has energy
        for resonator in self._resonator_network:
            if hasattr(resonator, "is_active") and resonator.is_active():
                return True

        if self._partial:
            return self._partial.is_active()

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "resonator_count": self._resonator_count,
                "coupling_matrix": self._coupling_matrix,
                "nonlinearity": self._nonlinearity,
                "temperature": self._environment["temperature"],
                "humidity": self._environment["humidity"],
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"AdvancedPhysicalRegion(resonators={self._resonator_count}, "
            f"coupling={self._coupling_matrix}, nonlinear={self._nonlinearity:.2f})"
        )
