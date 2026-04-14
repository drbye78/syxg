"""Professional compressor with full attack/release characteristics."""

from __future__ import annotations

import math
import threading

from ..dsp_core import AdvancedEnvelopeFollower

class ProfessionalCompressor:
    """
    Professional compressor with full attack/release characteristics.

    Features:
    - Configurable attack/release times
    - Ratio and threshold controls
    - Knee softening
    - Side-chain filtering
    - Make-up gain
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Compressor parameters
        self.threshold = -24.0  # dB
        self.ratio = 4.0  # 4:1
        self.attack_time = 0.01  # seconds
        self.release_time = 0.1  # seconds
        self.knee = 3.0  # dB soft knee
        self.makeup_gain = 0.0  # dB

        # Envelope follower
        self.envelope_follower = AdvancedEnvelopeFollower(
            sample_rate, self.attack_time, self.release_time
        )

        # Side-chain filter (high-pass for de-essing)
        self.sidechain_filter = 0.0
        self.sidechain_alpha = 0.0

        self.lock = threading.RLock()

    def set_parameters(
        self,
        threshold: float,
        ratio: float,
        attack: float,
        release: float,
        knee: float = 3.0,
        makeup: float = 0.0,
    ):
        """Set compressor parameters."""
        with self.lock:
            self.threshold = threshold
            self.ratio = ratio
            self.attack_time = attack
            self.release_time = release
            self.knee = knee
            self.makeup_gain = makeup

            # Update envelope follower
            self.envelope_follower.set_attack_time(attack)
            self.envelope_follower.set_release_time(release)

    def process_sample(self, input_sample: float, sidechain_sample: float | None = None) -> float:
        """Process sample through compressor."""
        with self.lock:
            # Use sidechain if provided
            control_signal = sidechain_sample if sidechain_sample is not None else input_sample

            # Side-chain filtering (optional high-pass)
            if self.sidechain_alpha > 0:
                control_signal = (
                    self.sidechain_alpha * control_signal
                    + (1 - self.sidechain_alpha) * self.sidechain_filter
                )
                self.sidechain_filter = control_signal

            # Convert to dB for envelope following
            if abs(control_signal) < 1e-6:
                control_db = -120.0
            else:
                control_db = 20.0 * math.log10(abs(control_signal))

            # Get envelope in dB
            envelope_db = self.envelope_follower.process_sample(control_signal)

            # Compressor gain calculation
            if envelope_db > self.threshold + self.knee / 2:
                # Above knee - hard compression
                gain_reduction = (envelope_db - self.threshold) * (1.0 - 1.0 / self.ratio)
                gain_reduction = min(gain_reduction, 40.0)  # Limit gain reduction
            elif envelope_db > self.threshold - self.knee / 2:
                # Soft knee region
                knee_ratio = (envelope_db - (self.threshold - self.knee / 2)) / self.knee
                soft_ratio = 1.0 + (self.ratio - 1.0) * knee_ratio
                gain_reduction = (envelope_db - self.threshold) * (1.0 - 1.0 / soft_ratio)
            else:
                # Below threshold - no compression
                gain_reduction = 0.0

            # Add make-up gain
            total_gain_db = self.makeup_gain - gain_reduction

            # Convert back to linear
            gain_linear = 10.0 ** (total_gain_db / 20.0)

            return input_sample * gain_linear


