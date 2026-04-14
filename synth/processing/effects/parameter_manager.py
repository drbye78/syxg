"""XG Parameter Manager - manages effect parameters."""

from __future__ import annotations

import logging
import math
import threading
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

class XGParameterManager:
    """
    XG Parameter Manager

    Central parameter management for all XG effects, providing validation,
    preset management, and parameter range mapping.
    """

    def __init__(self):
        """Initialize parameter manager."""
        self.parameter_ranges: dict[str, tuple[float, float]] = {}
        self.default_presets: dict[str, dict[str, Any]] = {}

        # Thread safety
        self.lock = threading.RLock()

        # Initialize parameter ranges and presets
        self._initialize_parameter_ranges()
        self._initialize_default_presets()

    def _initialize_parameter_ranges(self) -> None:
        """Initialize parameter range definitions."""
        self.parameter_ranges = {
            # System effect ranges
            "reverb_time": (0.1, 8.3),
            "reverb_level": (0.0, 1.0),
            "reverb_hf_damping": (0.0, 1.0),
            "reverb_pre_delay": (0.0, 0.05),
            "reverb_density": (0.0, 1.0),
            "chorus_rate": (0.125, 10.0),
            "chorus_depth": (0.0, 1.0),
            "chorus_feedback": (-0.25, 0.25),
            "chorus_level": (0.0, 1.0),
            # Channel parameters
            "volume": (0.0, 1.0),
            "pan": (-1.0, 1.0),
            "reverb_send": (0.0, 1.0),
            "chorus_send": (0.0, 1.0),
            "variation_send": (0.0, 1.0),
            # EQ parameters
            "eq_level": (-12.0, 12.0),
            "eq_frequency": (20.0, 20000.0),
            "eq_q_factor": (0.1, 10.0),
            # Master EQ ranges
            "low_gain": (-12.0, 12.0),
            "mid_gain": (-12.0, 12.0),
            "high_gain": (-12.0, 12.0),
            "low_freq": (20.0, 400.0),
            "mid_freq": (200.0, 8000.0),
            "high_freq": (2000.0, 20000.0),
        }

    def _initialize_default_presets(self) -> None:
        """Initialize default parameter presets."""
        self.default_presets = {
            "default_reverb": {
                "time": 1.5,
                "level": 0.4,
                "hf_damping": 0.5,
                "pre_delay": 0.02,
                "density": 0.8,
                "enabled": True,
            },
            "default_chorus": {
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.4,
                "delay": 0.012,
                "enabled": True,
            },
            "default_channel": XG_CHANNEL_MIXER_DEFAULT._asdict(),
        }

    def validate_parameter(self, param_name: str, value: float) -> tuple[bool, float]:
        """
        Validate and clamp a parameter value.

        Args:
            param_name: Parameter name
            value: Parameter value

        Returns:
            Tuple of (is_valid, clamped_value)
        """
        with self.lock:
            if param_name not in self.parameter_ranges:
                return False, value

            min_val, max_val = self.parameter_ranges[param_name]
            clamped_value = max(min_val, min(max_val, value))
            return True, clamped_value

    def get_default_preset(self, preset_name: str) -> dict[str, Any] | None:
        """Get a default parameter preset."""
        with self.lock:
            return self.default_presets.get(preset_name)

    def get_parameter_range(self, param_name: str) -> tuple[float, float] | None:
        """Get parameter range for a given parameter."""
        with self.lock:
            return self.parameter_ranges.get(param_name)
