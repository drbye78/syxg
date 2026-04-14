"""
Physical Region - Production-grade physical modeling region.

Part of the unified region-based synthesis architecture.
PhysicalRegion implements physical modeling synthesis with:
- Digital waveguide synthesis
- Karplus-Strong plucked string algorithm
- Multiple physical models (string, tube, membrane)
- Physical parameter control (tension, damping, material)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ...engines.region_descriptor import RegionDescriptor
from ...processing.partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class PhysicalRegion(IRegion):
    """
    Production-grade physical modeling region.

    Features:
    - Digital waveguide synthesis
    - Karplus-Strong plucked string
    - Multiple physical models (string, tube, membrane, plate)
    - Physical parameter control (tension, damping, body size)
    - Multiple excitation types (pluck, strike, blow, bow)

    Attributes:
        descriptor: Region metadata with physical parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_body_size",
        "_brightness",
        "_damping",
        "_decay_time",
        "_excitation_signal",
        "_excitation_type",
        "_material",
        "_model_type",
        "_tension",
        "_waveguide",
    ]

    MODEL_TYPES = ["string", "tube", "membrane", "plate"]
    EXCITATION_TYPES = ["pluck", "strike", "blow", "bow"]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize physical modeling region.

        Args:
            descriptor: Region metadata with physical parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Model parameters
        self._model_type = algo_params.get("model_type", "string")
        self._excitation_type = algo_params.get("excitation_type", "pluck")

        # Physical parameters
        self._tension = algo_params.get("tension", 0.5)
        self._damping = algo_params.get("damping", 0.5)
        self._body_size = algo_params.get("body_size", 0.5)
        self._material = algo_params.get("material", "steel")

        # Envelope parameters
        self._decay_time = algo_params.get("decay_time", 1.0)
        self._brightness = algo_params.get("brightness", 0.5)

        # Runtime state
        self._waveguide: Any | None = None
        self._excitation_signal: np.ndarray | None = None

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for physical modeling (algorithmic)."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create physical modeling partial.

        Returns:
            PhysicalPartial instance or None if creation failed
        """
        try:
            # Create waveguide based on model type
            self._waveguide = self._create_waveguide()

            if self._waveguide is None:
                logger.warning(f"Failed to create waveguide for model '{self._model_type}'")
                return None

            # Create excitation signal
            self._excitation_signal = self._create_excitation()

            # Build partial parameters
            partial_params = {
                "waveguide": self._waveguide,
                "excitation_signal": self._excitation_signal,
                "model_type": self._model_type,
                "excitation_type": self._excitation_type,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create physical partial
            from ...processing.partial.physical_partial import PhysicalPartial

            partial = PhysicalPartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create physical partial: {e}")
            return None

    def _create_waveguide(self) -> Any | None:
        """
        Create digital waveguide for physical model.

        Returns:
            Waveguide instance or None
        """
        try:
            from ...primitives.waveguide import DigitalWaveguide

            # Create waveguide
            waveguide = DigitalWaveguide(self.sample_rate)

            # Set frequency
            frequency = self._calculate_frequency()
            waveguide.set_frequency(frequency)

            # Set physical parameters based on model type
            if self._model_type == "string":
                # String parameters
                waveguide.set_parameters(
                    {
                        "scattering_coeff": self._tension,
                        "loop_filter_coeff": 1.0 - self._damping * 0.1,
                        "body_size": self._body_size,
                    }
                )

            elif self._model_type == "tube":
                # Tube parameters (wind instrument)
                waveguide.set_parameters(
                    {
                        "scattering_coeff": 0.8,  # Fixed for tube
                        "loop_filter_coeff": 1.0 - self._damping * 0.05,
                        "body_size": self._body_size * 2.0,  # Tubes are larger
                    }
                )

            elif self._model_type == "membrane":
                # Membrane parameters (drum head)
                waveguide.set_parameters(
                    {
                        "scattering_coeff": self._tension * 0.5,
                        "loop_filter_coeff": 1.0 - self._damping * 0.2,
                        "body_size": self._body_size,
                    }
                )

            elif self._model_type == "plate":
                # Plate parameters (metal plate)
                waveguide.set_parameters(
                    {
                        "scattering_coeff": self._tension * 0.7,
                        "loop_filter_coeff": 1.0 - self._damping * 0.15,
                        "body_size": self._body_size * 1.5,
                    }
                )

            return waveguide

        except Exception as e:
            logger.error(f"Failed to create waveguide: {e}")
            return None

    def _create_excitation(self) -> np.ndarray | None:
        """
        Create excitation signal for physical model.

        Returns:
            Excitation signal as numpy array or None
        """
        try:
            # Excitation length (short burst)
            excitation_length = int(self.sample_rate * 0.01)  # 10ms
            excitation = np.zeros(excitation_length, dtype=np.float32)

            # Velocity affects excitation amplitude
            velocity_scale = self.current_velocity / 127.0

            if self._excitation_type == "pluck":
                # Plucked string excitation (noise burst with decay)
                noise = np.random.uniform(-1, 1, excitation_length).astype(np.float32)
                envelope = np.exp(-np.linspace(0, 5, excitation_length))
                excitation = noise * envelope * velocity_scale

            elif self._excitation_type == "strike":
                # Striked excitation (impulse with harmonics)
                excitation[0] = velocity_scale  # Main impulse
                excitation[1:5] = velocity_scale * 0.5  # Harmonics

            elif self._excitation_type == "blow":
                # Blown excitation (noise with envelope)
                noise = np.random.uniform(-1, 1, excitation_length).astype(np.float32)
                envelope = np.exp(-np.linspace(0, 3, excitation_length))
                excitation = noise * envelope * velocity_scale

            elif self._excitation_type == "bow":
                # Bowed excitation (periodic stick-slip)
                bow_frequency = self._calculate_frequency()
                bow_samples = int(self.sample_rate / bow_frequency)
                for i in range(min(excitation_length, bow_samples * 4)):
                    # Stick-slip pattern
                    if i % bow_samples < bow_samples * 0.8:
                        excitation[i] = velocity_scale  # Stick
                    else:
                        excitation[i] = -velocity_scale * 0.5  # Slip

            # Apply material-based filtering
            excitation = self._apply_material_filter(excitation)

            return excitation

        except Exception as e:
            logger.error(f"Failed to create excitation: {e}")
            return None

    def _apply_material_filter(self, excitation: np.ndarray) -> np.ndarray:
        """
        Apply material-based filtering to excitation.

        Args:
            excitation: Raw excitation signal

        Returns:
            Filtered excitation signal
        """
        # Simple material filtering based on brightness
        if self._brightness < 0.5:
            # Dull material (felt, wood) - lowpass
            kernel_size = int((1.0 - self._brightness * 2) * 10) + 1
            kernel = np.ones(kernel_size) / kernel_size
            excitation = np.convolve(excitation, kernel, mode="same")
        elif self._brightness > 0.5:
            # Bright material (metal, glass) - highpass
            # Simple highpass: subtract lowpass from original
            kernel_size = int((self._brightness - 0.5) * 20) + 1
            kernel = np.ones(kernel_size) / kernel_size
            lowpass = np.convolve(excitation, kernel, mode="same")
            excitation = excitation * 0.5 + (excitation - lowpass) * 0.5

        return excitation.astype(np.float32)

    def _calculate_frequency(self) -> float:
        """
        Calculate frequency for current note.

        Returns:
            Frequency in Hz
        """
        # MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))

        # Apply fine tuning
        fine_tune = self.descriptor.generator_params.get("fine_tune", 0.0)
        frequency *= 2.0 ** (fine_tune / 1200.0)

        return frequency

    def _init_envelopes(self) -> None:
        """Initialize envelopes (handled by waveguide)."""
        pass

    def _init_filters(self) -> None:
        """Initialize filters (handled by waveguide)."""
        pass

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this physical region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Excite the waveguide
        if self._waveguide:
            self._waveguide.excite(self._excitation_type, velocity / 127.0)

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from physical model.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        if not self._partial:
            return np.zeros((block_size, 2), dtype=np.float32)

        try:
            # Generate samples from partial
            samples = self._partial.generate_samples(block_size, modulation)

            # Apply any additional processing
            if "filter" in self._filters:
                filter_obj = self._filters["filter"]
                if hasattr(filter_obj, "process_block"):
                    try:
                        filtered = filter_obj.process_block(samples)
                        if filtered is not None:
                            samples = filtered
                    except Exception as e:
                        logger.error(f"Physical filter processing failed: {e}")

            return samples

        except Exception as e:
            logger.error(f"Physical sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def is_active(self) -> bool:
        """Check if physical region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False

        # Check if waveguide still has energy
        if self._waveguide and hasattr(self._waveguide, "is_active"):
            return self._waveguide.is_active()

        if self._partial:
            return self._partial.is_active()

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "model_type": self._model_type,
                "excitation_type": self._excitation_type,
                "tension": self._tension,
                "damping": self._damping,
                "body_size": self._body_size,
                "material": self._material,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"PhysicalRegion(model={self._model_type}, "
            f"excitation={self._excitation_type}, mat={self._material})"
        )
