"""XG Volume Curve - volume scaling and dynamics."""

from __future__ import annotations

import math
import threading
from enum import IntEnum
from typing import Any

import numpy as np

class XGVolumeCurve:
    """
    XG Volume Curve Processor

    Implements XG volume curves with customizable response characteristics:
    - Linear, Exponential, Logarithmic curves
    - Knee softening for smooth transitions
    - Master volume scaling with curve application
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Volume curve parameters
        self.curve_type = 0  # 0=Linear, 1=Exponential, 2=Logarithmic, 3=Custom
        self.knee = 0.1  # Soft knee width (0-1)
        self.master_volume = 1.0  # Master volume scaling
        self.curve_shape = 2.0  # Curve shape parameter

        # Custom curve lookup table
        self.custom_curve = np.linspace(0.0, 1.0, 1024, dtype=np.float32)

        self.lock = threading.RLock()

    def set_curve_type(self, curve_type: int) -> None:
        """Set volume curve type."""
        with self.lock:
            self.curve_type = max(0, min(3, curve_type))

    def set_knee(self, knee: float) -> None:
        """Set soft knee width (0-1)."""
        with self.lock:
            self.knee = max(0.0, min(1.0, knee))

    def set_master_volume(self, volume: float) -> None:
        """Set master volume scaling (0-2)."""
        with self.lock:
            self.master_volume = max(0.0, min(2.0, volume))

    def set_curve_shape(self, shape: float) -> None:
        """Set curve shape parameter (0.1-10)."""
        with self.lock:
            self.curve_shape = max(0.1, min(10.0, shape))

    def set_custom_curve(self, curve_data: np.ndarray) -> None:
        """Set custom volume curve lookup table."""
        with self.lock:
            if len(curve_data) == 1024:
                self.custom_curve = curve_data.astype(np.float32)

    def apply_volume_curve(self, input_level: float) -> float:
        """
        Apply volume curve to input level.

        Args:
            input_level: Input level (0-1)

        Returns:
            Output level after curve application
        """
        with self.lock:
            if self.curve_type == 0:  # Linear
                output = input_level
            elif self.curve_type == 1:  # Exponential
                if input_level <= self.knee:
                    # Soft knee region
                    output = input_level * (1.0 / (self.knee + 1e-6)) * 0.5
                else:
                    # Exponential region
                    normalized = (input_level - self.knee) / (1.0 - self.knee + 1e-6)
                    exp_output = math.pow(normalized, 1.0 / self.curve_shape)
                    output = 0.5 + exp_output * 0.5
            elif self.curve_type == 2:  # Logarithmic
                if input_level <= self.knee:
                    # Soft knee region
                    output = input_level * (1.0 / (self.knee + 1e-6)) * 0.5
                else:
                    # Logarithmic region
                    normalized = (input_level - self.knee) / (1.0 - self.knee + 1e-6)
                    log_input = normalized * 0.9 + 0.1  # Avoid log(0)
                    log_output = math.log(log_input) / math.log(0.1)  # Normalize
                    output = 0.5 + log_output * 0.5
            else:  # Custom curve
                index = int(input_level * 1023)
                index = max(0, min(1023, index))
                output = self.custom_curve[index]

            return output * self.master_volume

    def reset(self) -> None:
        """Reset volume curve to default state."""
        with self.lock:
            self.curve_type = 0
            self.knee = 0.1
            self.master_volume = 1.0
            self.curve_shape = 2.0
            self.custom_curve = np.linspace(0.0, 1.0, 1024, dtype=np.float32)


