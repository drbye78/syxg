"""XG System Effects Processor - orchestrator for reverb, chorus, modulation."""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np

from .reverb import XGSystemReverbProcessor
from .chorus import XGSystemChorusProcessor
from .modulation import XGSystemModulationProcessor

class XGSystemEffectsProcessor:
    """
    XG System Effects Master Processor

    Orchestrates the system-wide effects chain: Reverb -> Chorus -> Optional Modulation
    Provides a unified interface for all system effects processing.
    """

    def __init__(
        self,
        sample_rate: int,
        block_size: int,
        dsp_units,
        max_reverb_delay: int,
        max_chorus_delay: int,
    ):
        """
        Initialize system effects processor.

        Args:
            sample_rate: Sample rate in Hz
            block_size: Maximum block size for processing
            dsp_units: DSP units manager (for sharing resources)
            max_reverb_delay: Maximum reverb delay in samples
            max_chorus_delay: Maximum chorus delay in samples
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Initialize effect processors
        self.reverb_processor = XGSystemReverbProcessor(sample_rate, max_reverb_delay)
        self.chorus_processor = XGSystemChorusProcessor(sample_rate, max_chorus_delay)
        self.modulation_processor = XGSystemModulationProcessor(sample_rate)

        # System effects chain configuration
        self.chain_config = {
            "reverb_enabled": True,
            "chorus_enabled": True,
            "modulation_enabled": False,
            "master_level": 1.0,
        }

        # Thread safety
        self.lock = threading.RLock()

    def set_system_effect_parameter(self, effect: str, param: str, value: float) -> bool:
        """
        Set a system effect parameter.

        Args:
            effect: Effect name ('reverb', 'chorus', 'modulation')
            param: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if effect == "reverb":
                return self.reverb_processor.set_parameter(param, value)
            elif effect == "chorus":
                return self.chorus_processor.set_parameter(param, value)
            elif effect == "modulation":
                return (
                    self.modulation_processor.set_parameter(param, value)
                    if hasattr(self.modulation_processor, "set_parameter")
                    else False
                )
            else:
                return False

    def set_chain_config(self, config: dict[str, Any]) -> None:
        """
        Update the effects chain configuration.

        Args:
            config: Configuration dictionary
        """
        with self.lock:
            for key, value in config.items():
                if key in self.chain_config:
                    self.chain_config[key] = value

    def apply_system_effects_to_mix_zero_alloc(
        self, stereo_mix: np.ndarray, num_samples: int
    ) -> None:
        """
        Apply the complete system effects chain to the stereo mix.

        Processing order: Reverb -> Chorus -> Optional Modulation -> Master Level

        Args:
            stereo_mix: Input/output stereo mix buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        with self.lock:
            # Ensure we don't process more samples than we can handle
            num_samples = min(num_samples, stereo_mix.shape[0])

            # Apply reverb if enabled
            if self.chain_config["reverb_enabled"]:
                self.reverb_processor.apply_system_effects_to_mix_zero_alloc(
                    stereo_mix, num_samples
                )

            # Apply chorus if enabled
            if self.chain_config["chorus_enabled"]:
                self.chorus_processor.apply_system_effects_to_mix_zero_alloc(
                    stereo_mix, num_samples
                )

            # Apply additional modulation if enabled
            if self.chain_config["modulation_enabled"]:
                self.modulation_processor.apply_system_effects_to_mix_zero_alloc(
                    stereo_mix, num_samples
                )

            # Apply master level
            if self.chain_config["master_level"] != 1.0:
                stereo_mix[:num_samples] *= self.chain_config["master_level"]

            # Final clipping to prevent overflow
            np.clip(stereo_mix[:num_samples], -1.0, 1.0, out=stereo_mix[:num_samples])

    def get_system_effects_status(self) -> dict[str, Any]:
        """Get current status of all system effects."""
        with self.lock:
            return {
                "reverb": {
                    "enabled": self.chain_config["reverb_enabled"],
                    "type": self.reverb_processor.params.get("reverb_type", "unknown"),
                    "level": self.reverb_processor.params.get("level", 0.0),
                },
                "chorus": {
                    "enabled": self.chain_config["chorus_enabled"],
                    "type": self.chorus_processor.params.get("chorus_type", "unknown"),
                    "level": self.chorus_processor.params.get("level", 0.0),
                },
                "modulation": {
                    "enabled": self.chain_config.get("modulation_enabled", False),
                },
                "master_level": self.chain_config["master_level"],
            }
