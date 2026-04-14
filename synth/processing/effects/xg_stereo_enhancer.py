"""XG Stereo Enhancer - stereo field enhancement."""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np

class XGStereoEnhancer:
    """
    XG Stereo Enhancer

    Enhances stereo width and imaging with XG-compliant parameters:
    - Stereo width control with phase manipulation
    - High-frequency stereo enhancement
    - Low-frequency mono compatibility
    - Mid-side processing
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # XG stereo enhancer parameters
        self.params = {
            "width": 1.0,  # Stereo width (0-2, 1.0 = natural)
            "hf_width": 1.2,  # High-frequency width boost
            "lf_mono": 0.3,  # Low-frequency mono amount (0-1)
            "crossover": 200.0,  # Crossover frequency (Hz)
            "enabled": True,
        }

        # Crossover filters for frequency-dependent processing
        self.low_filter_state = [0.0, 0.0, 0.0, 0.0]  # LP filter state
        self.high_filter_state = [0.0, 0.0, 0.0, 0.0]  # HP filter state

        self.lock = threading.RLock()

    def set_parameter(self, param: str, value: float) -> bool:
        """Set stereo enhancer parameter."""
        with self.lock:
            if param not in self.params:
                return False

            # Validate ranges
            if param == "width":
                value = max(0.0, min(2.0, value))
            elif param == "hf_width":
                value = max(0.5, min(2.0, value))
            elif param == "lf_mono":
                value = max(0.0, min(1.0, value))
            elif param == "crossover":
                value = max(50.0, min(1000.0, value))

            self.params[param] = value

            # Update filter coefficients when crossover changes
            if param == "crossover":
                self._update_crossover_filters()

            return True

    def _update_crossover_filters(self) -> None:
        """Update crossover filter coefficients."""
        freq = self.params["crossover"]
        omega = 2 * math.pi * freq / self.sample_rate

        # Linkwitz-Riley crossover (4th order) approximation
        alpha = math.sin(omega) / (2 * 0.5)  # Q = 0.5

        # Low-pass coefficients
        self.lp_a0 = 1 + alpha
        self.lp_a1 = -2 * math.cos(omega)
        self.lp_a2 = 1 - alpha
        self.lp_b0 = (1 - math.cos(omega)) / 2
        self.lp_b1 = 1 - math.cos(omega)
        self.lp_b2 = (1 - math.cos(omega)) / 2

        # High-pass coefficients
        self.hp_a0 = 1 + alpha
        self.hp_a1 = -2 * math.cos(omega)
        self.hp_a2 = 1 - alpha
        self.hp_b0 = (1 + math.cos(omega)) / 2
        self.hp_b1 = -(1 + math.cos(omega))
        self.hp_b2 = (1 + math.cos(omega)) / 2

        # Normalize
        for prefix in ["lp_", "hp_"]:
            a0 = getattr(self, f"{prefix}a0")
            for coeff in ["a0", "a1", "a2", "b0", "b1", "b2"]:
                setattr(self, f"{prefix}{coeff}", getattr(self, f"{prefix}{coeff}") / a0)

    def process_sample(self, left_sample: float, right_sample: float) -> tuple[float, float]:
        """Process stereo sample pair through enhancer."""
        if not self.params["enabled"]:
            return left_sample, right_sample

        with self.lock:
            # Convert to mid-side
            mid = (left_sample + right_sample) / math.sqrt(2)
            side = (left_sample - right_sample) / math.sqrt(2)

            # Apply frequency-dependent processing
            if self.params["crossover"] > 0:
                # Filter mid signal
                mid_lp = self._apply_lowpass_filter(mid, self.low_filter_state)
                mid_hp = self._apply_highpass_filter(mid, self.high_filter_state)

                # Apply different width enhancement to different frequency bands
                # Low frequencies: mono compatibility
                mid_lp_enhanced = mid_lp * (1.0 - self.params["lf_mono"] * 0.5)

                # High frequencies: enhanced stereo
                side_hp_enhanced = side * self.params["hf_width"]

                # Combine bands
                mid_enhanced = mid_lp_enhanced + mid_hp
                side_enhanced = side * self.params["width"]  # Low freq side
                side_enhanced += side_hp_enhanced - side  # Add HF enhancement
            else:
                # No crossover - apply uniform enhancement
                mid_enhanced = mid
                side_enhanced = side * self.params["width"]

            # Convert back to left-right
            left_enhanced = (mid_enhanced + side_enhanced) / math.sqrt(2)
            right_enhanced = (mid_enhanced - side_enhanced) / math.sqrt(2)

            return left_enhanced, right_enhanced

    def _apply_lowpass_filter(self, input_sample: float, filter_state: list) -> float:
        """Apply low-pass filter to sample."""
        x0 = input_sample
        x1, x2, y1, y2 = filter_state

        y0 = self.lp_b0 * x0 + self.lp_b1 * x1 + self.lp_b2 * x2 - self.lp_a1 * y1 - self.lp_a2 * y2

        # Update filter state
        filter_state[:] = [x0, x1, y0, y1]

        return y0

    def _apply_highpass_filter(self, input_sample: float, filter_state: list) -> float:
        """Apply high-pass filter to sample."""
        x0 = input_sample
        x1, x2, y1, y2 = filter_state

        y0 = self.hp_b0 * x0 + self.hp_b1 * x1 + self.hp_b2 * x2 - self.hp_a1 * y1 - self.hp_a2 * y2

        # Update filter state
        filter_state[:] = [x0, x1, y0, y1]

        return y0

    def process_block(self, stereo_block: np.ndarray, num_samples: int) -> None:
        """Process block of stereo samples."""
        if not self.params["enabled"]:
            return

        with self.lock:
            for i in range(num_samples):
                left, right = self.process_sample(stereo_block[i, 0], stereo_block[i, 1])
                stereo_block[i, 0] = left
                stereo_block[i, 1] = right


