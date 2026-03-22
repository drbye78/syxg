"""
XG Variation Effects Coordinator - Modular Implementation

This module coordinates the complete XG system variation effects using a modular
architecture. Each category of effects is implemented in separate modules for
maintainability and to overcome file size limitations.

Features:
- Complete 84 XG variation effect types
- Modular architecture for maintainability
- Zero-allocation processing with pre-allocated buffers
- Thread-safe operation
- Full XG specification compliance

Current modules:
- delay_variations.py: Delay effects (types 0-9)
- [Future]: chorus_modulation.py, distortion_dynamics.py, special_variations.py
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np

from .chorus_modulation import ChorusModulationProcessor

# Import modular processors
from .delay_variations import DelayVariationProcessor
from .distortion_pro import ProductionDistortionDynamicsProcessor
from .special_variations import SpecialVariationProcessor

# Import from our type definitions
from .types import XGVariationType


class XGVariationEffectsProcessor:
    """
    XG Variation Effects Master Coordinator

    Orchestrates all variation effects processors using modular architecture.
    Routes effects to appropriate specialized processors based on type ranges.
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        """
        Initialize variation effects coordinator.

        Args:
            sample_rate: Sample rate in Hz
            max_delay_samples: Maximum delay for effect processing
        """
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Initialize modular processors
        self.delay_processor = DelayVariationProcessor(sample_rate, max_delay_samples)
        self.chorus_processor = ChorusModulationProcessor(sample_rate, max_delay_samples)
        self.distortion_processor = ProductionDistortionDynamicsProcessor(
            sample_rate, max_delay_samples
        )
        self.special_processor = SpecialVariationProcessor(sample_rate, max_delay_samples)

        # Effect state storage for parameters (coordinator level)
        self._effect_states = {}

        # Current variation type
        self.current_variation_type = XGVariationType.CHORUS_1.value

        # Thread safety
        self.lock = threading.RLock()

    def set_variation_type(self, variation_type: XGVariationType) -> None:
        """Set the current variation effect type."""
        with self.lock:
            self.current_variation_type = variation_type.value

    def set_parameter(self, param: str, value: float) -> bool:
        """
        Set a variation effect parameter.

        This affects all variation processors that use the parameter.
        """
        # Store parameter for effect processing
        with self.lock:
            self._effect_states[param] = value
        return True

    def apply_variation_effect_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply the current variation effect to the stereo mix (in-place).
        Routes to appropriate modular processor based on effect type.

        Args:
            stereo_mix: Input/output stereo buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        with self.lock:
            effect_type = self.current_variation_type

            # Route to appropriate modular processor based on effect type ranges
            if 0 <= effect_type <= 9:
                # Delay effects (0-9) - route to delay processor
                self.delay_processor.process_effect(
                    effect_type, stereo_mix, num_samples, self._effect_states
                )
            elif 10 <= effect_type <= 26:
                # Chorus/Modulation effects (10-26) - route to chorus processor (PRODUCTION-READY)
                if self.chorus_processor:
                    self.chorus_processor.process_effect(
                        effect_type, stereo_mix, num_samples, self._effect_states
                    )
            elif 27 <= effect_type <= 57:
                # Distortion/Dynamics effects (27-57) - route to distortion processor (production-ready)
                if self.distortion_processor:
                    self.distortion_processor.process_effect(
                        effect_type, stereo_mix, num_samples, self._effect_states
                    )
            elif 58 <= effect_type <= 83:
                # Special/Spatial effects (58-83) - route to special processor (production-ready)
                if self.special_processor:
                    self.special_processor.process_effect(
                        effect_type, stereo_mix, num_samples, self._effect_states
                    )
            else:
                # Unknown effect type - pass through
                pass

    def get_variation_status(self) -> dict[str, Any]:
        """Get current variation effect status."""
        with self.lock:
            return {
                "type": self.current_variation_type,
                "parameters": dict(self._effect_states),
                "supported_effects": 84,
                "modular_processors": {
                    "delay": self.delay_processor.get_supported_types()
                    if self.delay_processor
                    else [],
                    "chorus": self.chorus_processor.get_supported_types()
                    if self.chorus_processor
                    else [],
                    "distortion": self.distortion_processor.get_supported_types()
                    if self.distortion_processor
                    else [],
                    "special": self.special_processor.get_supported_types()
                    if self.special_processor
                    else [],
                },
            }
