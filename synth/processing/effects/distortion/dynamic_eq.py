"""Dynamic EQ enhancer for peaking and shelving enhancement."""

from __future__ import annotations

import math
import threading

import numpy as np

from ..dsp_core import AdvancedEnvelopeFollower

class DynamicEQEnhancer:
    """
    Dynamic EQ enhancer for peaking and shelving enhancement.

    Features:
    - Dynamic equalization based on input level
    - Peaking or shelving characteristics
    - Frequency-specific enhancement
    """

    def __init__(
        self, sample_rate: int, freq: float = 5000.0, q: float = 1.0, peaking: bool = True
    ):
        self.sample_rate = sample_rate
        self.center_freq = freq
        self.q = q
        self.peaking = peaking

        # Biquad filter coefficients
        self.a0 = 1.0
        self.a1 = 0.0
        self.a2 = 0.0
        self.b0 = 1.0
        self.b1 = 0.0
        self.b2 = 0.0

        # Filter state
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

        # Envelope follower for dynamic control
        self.envelope = AdvancedEnvelopeFollower(sample_rate, 0.01, 0.1)

        self.lock = threading.RLock()

        # Initialize filter
        self._update_coefficients(0.0)  # Flat response initially

    def _update_coefficients(self, gain_db: float):
        """Update biquad filter coefficients for given gain."""
        with self.lock:
            A = 10.0 ** (gain_db / 40.0)
            omega = 2 * math.pi * self.center_freq / self.sample_rate
            alpha = math.sin(omega) / (2 * self.q)

            if self.peaking:
                # Peaking EQ
                self.a0 = 1 + alpha / A
                self.a1 = -2 * math.cos(omega)
                self.a2 = 1 - alpha / A
                self.b0 = 1 + alpha * A
                self.b1 = -2 * math.cos(omega)
                self.b2 = 1 - alpha * A
            else:
                # Shelving EQ (simplified)
                self.a0 = A + 1
                self.a1 = -2 * math.cos(omega)
                self.a2 = A - 1
                self.b0 = A * (A + 1 - (A - 1) * math.cos(omega) + 2 * alpha * math.sqrt(A))
                self.b1 = -2 * A * math.cos(omega)
                self.b2 = A * (A + 1 - (A - 1) * math.cos(omega) - 2 * alpha * math.sqrt(A))

            # Normalize
            norm = self.a0
            self.a0 /= norm
            self.a1 /= norm
            self.a2 /= norm
            self.b0 /= norm
            self.b1 /= norm
            self.b2 /= norm

    def process_sample(self, input_sample: float, enhance_amount: float) -> float:
        """Process sample through dynamic EQ enhancer."""
        with self.lock:
            # Get input level for dynamic control
            input_level = self.envelope.process_sample(input_sample)

            # Calculate dynamic gain based on input level
            # More enhancement at lower levels
            if input_level < 0.1:
                dynamic_gain = enhance_amount * (1.0 - input_level * 5.0)
            else:
                dynamic_gain = enhance_amount * 0.5

            # Update filter coefficients
            self._update_coefficients(dynamic_gain * 12.0)  # Max 12dB boost

            # Process through biquad filter
            output = (
                self.b0 * input_sample
                + self.b1 * self.x1
                + self.b2 * self.x2
                - self.a1 * self.y1
                - self.a2 * self.y2
            )

            # Update filter state
            self.x2 = self.x1
            self.x1 = input_sample
            self.y2 = self.y1
            self.y1 = output

            return output


