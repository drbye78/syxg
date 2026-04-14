"""Multiband compressor for frequency-specific dynamics processing."""

from __future__ import annotations

import math
import threading

from .compressor import ProfessionalCompressor

class MultibandCompressor:
    """
    Multiband compressor for frequency-specific dynamics processing.

    Features:
    - 3-band crossover (low/mid/high)
    - Independent compression per band
    - Crossover filtering
    - Per-band make-up gain
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Crossover frequencies
        self.low_mid_freq = 250.0  # Hz
        self.mid_high_freq = 2500.0  # Hz

        # Band filters (simple approximation)
        self.low_filter = 0.0
        self.mid_filter = 0.0
        self.high_filter = 0.0

        # Per-band compressors
        self.low_compressor = ProfessionalCompressor(sample_rate)
        self.mid_compressor = ProfessionalCompressor(sample_rate)
        self.high_compressor = ProfessionalCompressor(sample_rate)

        self.lock = threading.RLock()

    def configure_bands(self, low_params: dict, mid_params: dict, high_params: dict):
        """Configure compression parameters for each band."""
        with self.lock:
            self.low_compressor.set_parameters(**low_params)
            self.mid_compressor.set_parameters(**mid_params)
            self.high_compressor.set_parameters(**high_params)

    def process_sample(self, input_sample: float) -> float:
        """Process sample through multiband compressor."""
        with self.lock:
            # Simple frequency splitting (approximation)
            # Low band (LPF)
            alpha_low = 1.0 / (1.0 + 2 * math.pi * self.low_mid_freq / self.sample_rate)
            low_band = alpha_low * input_sample + (1 - alpha_low) * self.low_filter
            self.low_filter = low_band

            # High band (HPF)
            alpha_high = 1.0 / (1.0 + 2 * math.pi * self.mid_high_freq / self.sample_rate)
            high_band = alpha_high * (input_sample - low_band) + (1 - alpha_high) * self.high_filter
            self.high_filter = high_band

            # Mid band (difference)
            mid_band = input_sample - low_band - high_band

            # Compress each band
            low_processed = self.low_compressor.process_sample(low_band)
            mid_processed = self.mid_compressor.process_sample(mid_band)
            high_processed = self.high_compressor.process_sample(high_band)

            # Sum bands
            return low_processed + mid_processed + high_processed


