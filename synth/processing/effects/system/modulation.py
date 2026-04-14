"""XG System Modulation Processor."""

from __future__ import annotations

import math
import threading

import numpy as np


class XGSystemModulationProcessor:
    """
    XG System Modulation Effects Processor

    Handles system-wide modulation effects that can be applied in addition to
    or instead of reverb/chorus. Includes tremolo, autopan, flanger, etc.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.params = {
            "type": 0,  # Effect type
            "rate": 5.0,  # LFO rate
            "depth": 0.5,  # Modulation depth
            "enabled": False,
        }

        # Effect state
        self.lfo_phase = 0.0

        # Thread safety
        self.lock = threading.RLock()

    def set_parameter(self, param: str, value: float) -> bool:
        """
        Set a modulation parameter value.

        Args:
            param: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if param in self.params:
                self.params[param] = value
                return True
            return False

    def apply_system_effects_to_mix_zero_alloc(
        self, stereo_mix: np.ndarray, num_samples: int
    ) -> None:
        """Apply system modulation effects to the mix."""
        if not self.params["enabled"]:
            return

        with self.lock:
            # Simple tremolo implementation for now
            rate = self.params["rate"]
            depth = self.params["depth"]

            for i in range(num_samples):
                # Update LFO phase
                phase_increment = 2 * np.pi * rate / self.sample_rate
                self.lfo_phase = (self.lfo_phase + phase_increment) % (2 * np.pi)

                # Generate amplitude modulation
                mod = math.sin(self.lfo_phase)
                amplitude = 1.0 - depth * 0.5 + depth * 0.5 * mod

                # Apply to both channels
                stereo_mix[i, 0] *= amplitude
                stereo_mix[i, 1] *= amplitude


