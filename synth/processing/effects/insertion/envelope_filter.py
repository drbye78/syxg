"""Production envelope filter processor."""

from __future__ import annotations

import math
import threading

from ..dsp_core import AdvancedEnvelopeFollower


class ProductionEnvelopeFilter:
    """
    Professional envelope filter with dynamic frequency control.

    Features:
    - Envelope follower driving filter cutoff
    - Band-pass filter characteristics
    - Attack/release controls
    - Frequency range control
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Envelope follower
        self.envelope_follower = AdvancedEnvelopeFollower(sample_rate, 0.01, 0.1)

        # Filter parameters
        self.center_freq = 1000.0
        self.q = 2.0
        self.sensitivity = 0.5
        self.freq_range = (200.0, 5000.0)  # Hz

        # Biquad filter state
        self.x1 = self.x2 = 0.0
        self.y1 = self.y2 = 0.0

        self.lock = threading.RLock()

    def _update_biquad_coefficients(self, freq: float, q: float):
        """Update biquad bandpass filter coefficients."""
        with self.lock:
            omega = 2 * math.pi * freq / self.sample_rate
            alpha = math.sin(omega) / (2 * q)

            # Bandpass coefficients
            self.b0 = alpha
            self.b1 = 0.0
            self.b2 = -alpha
            self.a0 = 1 + alpha
            self.a1 = -2 * math.cos(omega)
            self.a2 = 1 - alpha

            # Normalize
            norm = self.a0
            self.b0 /= norm
            self.b1 /= norm
            self.b2 /= norm
            self.a1 /= norm
            self.a2 /= norm

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process sample through envelope filter."""
        with self.lock:
            self.sensitivity = params.get("sensitivity", 0.5)
            self.q = params.get("resonance", 2.0)

            # Get input level for envelope
            input_level = abs(input_sample)

            # Update envelope
            envelope = self.envelope_follower.process_sample(input_sample)

            # Calculate filter frequency based on envelope
            min_freq, max_freq = self.freq_range
            freq_range = max_freq - min_freq
            filter_freq = min_freq + envelope * self.sensitivity * freq_range
            filter_freq = max(min_freq, min(max_freq, filter_freq))

            # Update filter coefficients
            self._update_biquad_coefficients(filter_freq, self.q)

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


