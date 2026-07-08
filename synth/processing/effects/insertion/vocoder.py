"""Professional carrier vocoder for insertion effects."""

from __future__ import annotations

import math
import threading

import numpy as np


class CarrierVocoder:
    """
    Multiband vocoder with cascaded one-pole band splitting.

    Splits both modulator and carrier into N frequency bands using a
    cascaded one-pole LPF structure, extracts spectral envelopes
    from the modulator per band, and applies them to the carrier.

    Features:
    - N-band cascaded one-pole crossover (≈6dB/oct per stage)
    - Independent envelope follower per band (attack=10ms, release=50ms)
    - Optional dry/wet mix
    """

    def __init__(self, sample_rate: int, num_bands: int = 8):
        self.sample_rate = sample_rate
        self.num_bands = num_bands

        # Log-spaced crossover frequencies (200 Hz - 8 kHz)
        self.crossover_freqs = [
            200.0 * (8000.0 / 200.0) ** (i / num_bands) for i in range(num_bands - 1)
        ]

        # One-pole coefficient per band (pre-computed)
        self._lpf_alphas = np.array(
            [2.0 * math.sin(math.pi * f / sample_rate) for f in self.crossover_freqs],
            dtype=np.float64,
        )
        # Clamp to [0, 1)
        self._lpf_alphas = np.clip(self._lpf_alphas, 0.0, 0.999)

        # Per-band LPF state (modulator path)
        self._mod_lp = np.zeros(num_bands - 1, dtype=np.float64)
        # Per-band LPF state (carrier path)
        self._car_lp = np.zeros(num_bands - 1, dtype=np.float64)

        # Envelope followers per band
        self._envelopes = np.zeros(num_bands, dtype=np.float64)
        self.attack_coeff = 1.0 - math.exp(-1.0 / (0.01 * sample_rate))
        self.release_coeff = 1.0 - math.exp(-1.0 / (0.05 * sample_rate))

        self.lock = threading.RLock()

    def set_attack_release(self, attack_ms: float, release_ms: float) -> None:
        """Set envelope follower time constants."""
        with self.lock:
            attack_s = max(0.001, attack_ms / 1000.0)
            release_s = max(0.001, release_ms / 1000.0)
            self.attack_coeff = 1.0 - math.exp(-1.0 / (attack_s * self.sample_rate))
            self.release_coeff = 1.0 - math.exp(-1.0 / (release_s * self.sample_rate))

    def process_sample(self, modulator: float, carrier: float) -> float:
        """Process one sample through the vocoder.

        Args:
            modulator: Modulation signal (extracts spectral envelope)
            carrier: Carrier signal (receives spectral envelope)

        Returns:
            Vocoded output sample
        """
        with self.lock:
            output = 0.0

            # Split both signals into bands using cascaded one-pole LPFs
            mod_remain = modulator
            car_remain = carrier

            for band in range(self.num_bands):
                if band < self.num_bands - 1:
                    # Cascaded one-pole LPF at crossover
                    alpha = self._lpf_alphas[band]
                    self._mod_lp[band] += alpha * (mod_remain - self._mod_lp[band])
                    self._car_lp[band] += alpha * (car_remain - self._car_lp[band])

                    # Band signal: HPF output = input - LPF output
                    mod_band = mod_remain - self._mod_lp[band]
                    car_band = car_remain - self._car_lp[band]

                    # Continue remainder for next band
                    mod_remain = self._mod_lp[band]
                    car_remain = self._car_lp[band]
                else:
                    # Last band: the remainder (lowest frequencies)
                    mod_band = mod_remain
                    car_band = car_remain

                # Envelope follower for this band (from modulator)
                abs_mod = abs(mod_band)
                if abs_mod > self._envelopes[band]:
                    self._envelopes[band] += self.attack_coeff * (abs_mod - self._envelopes[band])
                else:
                    self._envelopes[band] += self.release_coeff * (abs_mod - self._envelopes[band])
                env = self._envelopes[band]

                # Apply envelope to carrier band and accumulate
                output += car_band * env

            # Normalize by number of bands
            return output / self.num_bands
