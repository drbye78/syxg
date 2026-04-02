"""
Convolution Reverb Region - Production-grade IR-based reverb region.

Part of the unified region-based synthesis architecture.
ConvolutionReverbRegion implements convolution reverb with:
- Impulse response loading
- Convolution processing
- Wet/dry mixing
- Pre-delay control
- High-frequency damping
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class ConvolutionReverbRegion(IRegion):
    """
    Production-grade convolution reverb region.

    Features:
    - Impulse response loading from files or presets
    - Fast convolution processing (FFT-based)
    - Wet/dry mixing
    - Pre-delay control
    - High-frequency damping
    - Early reflection control

    Attributes:
        descriptor: Region metadata with reverb parameters
        sample_rate: Audio sample rate
    """

    __slots__ = [
        "_convolution_processor",
        "_dry_buffer",
        "_dry_level",
        "_early_level",
        "_high_freq_damping",
        "_ir_data",
        "_ir_name",
        "_predelay",
        "_wet_buffer",
        "_wet_level",
    ]

    def __init__(self, descriptor: RegionDescriptor, sample_rate: int = 44100):
        """
        Initialize convolution reverb region.

        Args:
            descriptor: Region metadata with reverb parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Impulse response
        self._ir_name = algo_params.get("ir_name", "hall")
        self._ir_data: np.ndarray | None = None

        # Mix parameters
        self._wet_level = algo_params.get("wet_level", 0.3)
        self._dry_level = algo_params.get("dry_level", 0.7)

        # Time parameters
        self._predelay = algo_params.get("predelay", 0.0)  # seconds

        # Filter parameters
        self._high_freq_damping = algo_params.get("high_freq_damping", 0.5)

        # Early reflection parameters
        self._early_level = algo_params.get("early_level", 1.0)

        # Runtime state
        self._convolution_processor: Any | None = None
        self._wet_buffer: np.ndarray | None = None
        self._dry_buffer: np.ndarray | None = None

    def _load_sample_data(self) -> np.ndarray | None:
        """Load impulse response data."""
        # Load impulse response from cache or preset
        self._ir_data = self._load_impulse_response(self._ir_name)
        return self._ir_data

    def _load_impulse_response(self, ir_name: str) -> np.ndarray | None:
        """
        Load impulse response by name.

        Args:
            ir_name: Impulse response name

        Returns:
            Impulse response data or None
        """
        # Built-in preset impulse responses (simplified)
        presets = {
            "hall": self._generate_hall_ir(),
            "room": self._generate_room_ir(),
            "plate": self._generate_plate_ir(),
            "spring": self._generate_spring_ir(),
            "cathedral": self._generate_cathedral_ir(),
        }

        return presets.get(ir_name, self._generate_hall_ir())

    def _generate_hall_ir(self) -> np.ndarray:
        """Generate concert hall impulse response."""
        length = int(self.sample_rate * 2.5)  # 2.5 seconds
        ir = np.zeros(length, dtype=np.float32)

        # Early reflections
        ir[100] = 0.8
        ir[300] = 0.6
        ir[500] = 0.4

        # Reverb tail (exponential decay)
        decay = np.exp(-np.linspace(0, 5, length - 600))
        noise = np.random.uniform(-1, 1, length - 600).astype(np.float32)
        ir[600:] = noise * decay * 0.3

        # High-frequency damping
        ir = self._apply_lowpass(ir, self._high_freq_damping)

        return ir

    def _generate_room_ir(self) -> np.ndarray:
        """Generate small room impulse response."""
        length = int(self.sample_rate * 0.5)  # 0.5 seconds
        ir = np.zeros(length, dtype=np.float32)

        # Early reflections (closer together)
        ir[50] = 0.9
        ir[150] = 0.7
        ir[250] = 0.5

        # Short reverb tail
        decay = np.exp(-np.linspace(0, 8, length - 300))
        noise = np.random.uniform(-1, 1, length - 300).astype(np.float32)
        ir[300:] = noise * decay * 0.2

        return self._apply_lowpass(ir, self._high_freq_damping)

    def _generate_plate_ir(self) -> np.ndarray:
        """Generate plate reverb impulse response."""
        length = int(self.sample_rate * 1.5)
        ir = np.zeros(length, dtype=np.float32)

        # Dense early reflections
        ir[20:100:20] = [0.7, 0.6, 0.5, 0.4]

        # Smooth plate decay
        decay = np.exp(-np.linspace(0, 4, length - 100))
        noise = np.random.uniform(-1, 1, length - 100).astype(np.float32)
        ir[100:] = noise * decay * 0.4

        return self._apply_lowpass(ir, 0.7)  # Plate has natural damping

    def _generate_spring_ir(self) -> np.ndarray:
        """Generate spring reverb impulse response."""
        length = int(self.sample_rate * 2.0)
        ir = np.zeros(length, dtype=np.float32)

        # Characteristic spring "boing"
        ir[50] = 0.9
        ir[150] = -0.6  # Phase inversion
        ir[250] = 0.4

        # Metallic decay
        decay = np.exp(-np.linspace(0, 3, length - 300))
        noise = np.random.uniform(-1, 1, length - 300).astype(np.float32)
        ir[300:] = noise * decay * 0.3

        return ir

    def _generate_cathedral_ir(self) -> np.ndarray:
        """Generate cathedral impulse response."""
        length = int(self.sample_rate * 5.0)  # 5 seconds
        ir = np.zeros(length, dtype=np.float32)

        # Distant early reflections
        ir[500] = 0.7
        ir[1000] = 0.5
        ir[1500] = 0.3

        # Very long decay
        decay = np.exp(-np.linspace(0, 3, length - 2000))
        noise = np.random.uniform(-1, 1, length - 2000).astype(np.float32)
        ir[2000:] = noise * decay * 0.2

        return self._apply_lowpass(ir, self._high_freq_damping)

    def _apply_lowpass(self, signal: np.ndarray, damping: float) -> np.ndarray:
        """Apply lowpass filter to signal."""
        if damping <= 0:
            return signal

        # Simple moving average lowpass
        kernel_size = int(damping * 10) + 1
        kernel = np.ones(kernel_size) / kernel_size
        return np.convolve(signal, kernel, mode="same").astype(np.float32)

    def _create_partial(self) -> Any | None:
        """
        Create convolution reverb partial.

        Returns:
            ConvolutionReverbPartial instance or None
        """
        try:
            # Load impulse response if not already loaded
            if self._ir_data is None:
                self._load_sample_data()

            # Create convolution processor
            from ..engine.convolution_reverb_engine import ConvolutionProcessor

            self._convolution_processor = ConvolutionProcessor(self._ir_data, self.sample_rate)

            # Set parameters
            self._convolution_processor.set_parameters(
                {
                    "wet_level": self._wet_level,
                    "dry_level": self._dry_level,
                    "predelay": self._predelay,
                    "high_freq_damping": self._high_freq_damping,
                    "early_level": self._early_level,
                }
            )

            # Allocate buffers
            self._wet_buffer = np.zeros(4096 * 2, dtype=np.float32)
            self._dry_buffer = np.zeros(4096 * 2, dtype=np.float32)

            # Build partial parameters
            partial_params = {
                "convolution_processor": self._convolution_processor,
                "ir_data": self._ir_data,
                "wet_level": self._wet_level,
                "dry_level": self._dry_level,
                "predelay": self._predelay,
            }

            # Import and create partial
            from ..partial.convolution_reverb_partial import ConvolutionReverbPartial

            partial = ConvolutionReverbPartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create convolution reverb partial: {e}")
            return None

    def _init_envelopes(self) -> None:
        """No envelopes for convolution reverb."""
        pass

    def _init_filters(self) -> None:
        """Filters handled by convolution processor."""
        pass

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this reverb region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Velocity can affect wet/dry mix
        if self._convolution_processor:
            wet_mod = self._wet_level * (0.5 + velocity / 127.0 * 0.5)
            self._convolution_processor.set_wet_level(wet_mod)

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate convolved reverb samples.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Convolution reverb is typically used as an effect send
        # For region use, we generate processed noise/signal

        if not self._partial:
            return np.zeros((block_size, 2), dtype=np.float32)

        try:
            # Apply modulation
            self._apply_modulation(modulation)

            # Generate samples from partial
            samples = self._partial.generate_samples(block_size, modulation)

            return samples

        except Exception as e:
            logger.error(f"Convolution reverb sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation to reverb parameters.

        Args:
            modulation: Modulation values dictionary
        """
        if not self._convolution_processor:
            return

        # Mod wheel to wet level
        mod_wheel = modulation.get("mod_wheel", 0.0)
        if mod_wheel > 0:
            wet = self._wet_level * (1.0 + mod_wheel)
            self._convolution_processor.set_wet_level(min(1.0, wet))

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """Update modulation state."""
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if reverb region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False

        if self._partial:
            return self._partial.is_active()

        # Reverb tails can be long
        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "ir_name": self._ir_name,
                "wet_level": self._wet_level,
                "dry_level": self._dry_level,
                "predelay": self._predelay,
                "high_freq_damping": self._high_freq_damping,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ConvolutionReverbRegion(ir={self._ir_name}, "
            f"wet={self._wet_level:.2f}, predelay={self._predelay:.3f}s)"
        )
