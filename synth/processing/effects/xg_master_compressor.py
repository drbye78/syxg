"""XG Master Compressor - master bus dynamics processing."""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np

from .xg_volume_curve import XGVolumeCurve

class XGMasterCompressor:
    """
    XG Master Compressor/Limiter

    Professional compressor/limiter with XG-compliant parameters:
    - Threshold, ratio, attack, release controls
    - Soft knee and look-ahead processing
    - Peak/RMS detection modes
    - Side-chain filtering
    - Auto make-up gain
    """

    def __init__(self, sample_rate: int, max_lookahead_samples: int = 1024):
        self.sample_rate = sample_rate
        self.max_lookahead_samples = max_lookahead_samples

        # XG compressor parameters
        self.params = {
            "threshold": -20.0,  # dB (-60 to 0)
            "ratio": 4.0,  # 1:1 to 20:1
            "attack": 5.0,  # ms (0.1 to 100)
            "release": 100.0,  # ms (10 to 1000)
            "knee": 3.0,  # dB (0 to 20)
            "makeup_gain": 0.0,  # dB (auto or manual)
            "auto_makeup": True,  # Auto make-up gain
            "detection_mode": 0,  # 0=Peak, 1=RMS
            "sidechain_filter": False,  # High-pass sidechain
            "sidechain_freq": 150.0,  # Hz
            "dry_wet": 1.0,  # 0=Dry, 1=Wet
            "enabled": True,
        }

        # Look-ahead buffer for attack prediction
        self.lookahead_buffer = np.zeros(max_lookahead_samples, dtype=np.float32)
        self.lookahead_write_pos = 0
        self.lookahead_delay_samples = int(0.001 * sample_rate)  # 1ms default

        # Envelope followers for peak and RMS detection
        self.peak_envelope = self._create_envelope_follower()
        self.rms_envelope = self._create_envelope_follower()

        # Side-chain high-pass filter
        self.sidechain_filter_state = [0.0, 0.0, 0.0, 0.0]  # x1, x2, y1, y2

        # Auto make-up gain tracking
        self.gain_reduction_history = []
        self.history_length = int(1.0 * sample_rate)  # 1 second history

        self.lock = threading.RLock()

    def _create_envelope_follower(self):
        """Create envelope follower for level detection."""
        # Simple exponential envelope follower
        return {"attack_coeff": 1.0, "release_coeff": 1.0, "envelope": 0.0}

    def set_parameter(self, param: str, value: float) -> bool:
        """Set compressor parameter."""
        with self.lock:
            if param not in self.params:
                return False

            # Validate ranges
            if param == "threshold":
                value = max(-60.0, min(0.0, value))
            elif param == "ratio":
                value = max(1.0, min(20.0, value))
            elif param == "attack":
                value = max(0.1, min(100.0, value))
            elif param == "release":
                value = max(10.0, min(1000.0, value))
            elif param == "knee":
                value = max(0.0, min(20.0, value))
            elif param == "detection_mode":
                value = int(max(0, min(1, value)))
            elif param == "dry_wet":
                value = max(0.0, min(1.0, value))

            self.params[param] = value

            # Update envelope follower coefficients
            if param in ["attack", "release"]:
                self._update_envelope_coefficients()

            # Update side-chain filter
            if param in ["sidechain_filter", "sidechain_freq"]:
                self._update_sidechain_filter()

            return True

    def _update_envelope_coefficients(self) -> None:
        """Update envelope follower attack/release coefficients."""
        attack_time = self.params["attack"] / 1000.0  # Convert to seconds
        release_time = self.params["release"] / 1000.0

        # Calculate coefficients (simplified)
        self.peak_envelope["attack_coeff"] = 1.0 - math.exp(-1.0 / (attack_time * self.sample_rate))
        self.peak_envelope["release_coeff"] = 1.0 - math.exp(
            -1.0 / (release_time * self.sample_rate)
        )

        self.rms_envelope["attack_coeff"] = self.peak_envelope["attack_coeff"]
        self.rms_envelope["release_coeff"] = self.peak_envelope["release_coeff"]

    def _update_sidechain_filter(self) -> None:
        """Update side-chain high-pass filter coefficients."""
        if not self.params["sidechain_filter"]:
            return

        freq = self.params["sidechain_freq"]
        omega = 2 * math.pi * freq / self.sample_rate

        # High-pass filter coefficients
        alpha = math.sin(omega) / (2 * 0.707)  # Q = 0.707

        self.sidechain_a0 = 1 + alpha
        self.sidechain_a1 = -2 * math.cos(omega)
        self.sidechain_a2 = 1 - alpha
        self.sidechain_b0 = (1 + math.cos(omega)) / 2
        self.sidechain_b1 = -(1 + math.cos(omega))
        self.sidechain_b2 = (1 + math.cos(omega)) / 2

        # Normalize
        norm = self.sidechain_a0
        self.sidechain_a0 /= norm
        self.sidechain_a1 /= norm
        self.sidechain_a2 /= norm
        self.sidechain_b0 /= norm
        self.sidechain_b1 /= norm
        self.sidechain_b2 /= norm

    def process_sample(self, input_sample: float) -> float:
        """Process sample through compressor."""
        if not self.params["enabled"]:
            return input_sample

        with self.lock:
            # Side-chain processing
            sidechain_signal = input_sample

            # Apply side-chain filter if enabled
            if self.params["sidechain_filter"]:
                sidechain_signal = self._apply_sidechain_filter(sidechain_signal)

            # Level detection
            if self.params["detection_mode"] == 0:  # Peak detection
                level_db = self._update_peak_envelope(abs(sidechain_signal))
            else:  # RMS detection
                level_db = self._update_rms_envelope(sidechain_signal)

            # Calculate gain reduction
            gain_reduction_db = self._calculate_gain_reduction(level_db)

            # Apply make-up gain
            if self.params["auto_makeup"]:
                makeup_db = -gain_reduction_db * 0.5  # Partial compensation
            else:
                makeup_db = self.params["makeup_gain"]

            total_gain_db = makeup_db + gain_reduction_db

            # Convert to linear and apply
            gain_linear = 10.0 ** (total_gain_db / 20.0)

            # Dry/wet mix
            wet_sample = input_sample * gain_linear
            output_sample = (
                input_sample * (1.0 - self.params["dry_wet"]) + wet_sample * self.params["dry_wet"]
            )

            # Track gain reduction for auto make-up
            self.gain_reduction_history.append(gain_reduction_db)
            if len(self.gain_reduction_history) > self.history_length:
                self.gain_reduction_history.pop(0)

            return output_sample

    def _apply_sidechain_filter(self, input_sample: float) -> float:
        """Apply side-chain high-pass filter."""
        x0 = input_sample
        x1, x2, y1, y2 = self.sidechain_filter_state

        y0 = (
            self.sidechain_b0 * x0
            + self.sidechain_b1 * x1
            + self.sidechain_b2 * x2
            - self.sidechain_a1 * y1
            - self.sidechain_a2 * y2
        )

        # Update filter state
        self.sidechain_filter_state = [x0, x1, y0, y1]

        return y0

    def _update_peak_envelope(self, input_level: float) -> float:
        """Update peak envelope follower."""
        env = self.peak_envelope

        if input_level > env["envelope"]:
            env["envelope"] += (input_level - env["envelope"]) * env["attack_coeff"]
        else:
            env["envelope"] += (input_level - env["envelope"]) * env["release_coeff"]

        return 20.0 * math.log10(max(env["envelope"], 1e-6))

    def _update_rms_envelope(self, input_sample: float) -> float:
        """Update RMS envelope follower."""
        env = self.rms_envelope

        # RMS window (simplified)
        squared_sample = input_sample * input_sample

        if squared_sample > env["envelope"]:
            env["envelope"] += (squared_sample - env["envelope"]) * env["attack_coeff"]
        else:
            env["envelope"] += (squared_sample - env["envelope"]) * env["release_coeff"]

        rms_level = math.sqrt(max(env["envelope"], 1e-12))
        return 20.0 * math.log10(rms_level)

    def _calculate_gain_reduction(self, input_level_db: float) -> float:
        """Calculate gain reduction based on compressor parameters."""
        threshold = self.params["threshold"]
        ratio = self.params["ratio"]
        knee = self.params["knee"]

        if input_level_db <= threshold - knee / 2:
            # Below knee - no compression
            return 0.0
        elif input_level_db <= threshold + knee / 2:
            # Soft knee region
            knee_ratio = (input_level_db - (threshold - knee / 2)) / knee
            soft_ratio = 1.0 + (ratio - 1.0) * knee_ratio
            return (threshold - input_level_db) * (1.0 - 1.0 / soft_ratio)
        else:
            # Above knee - hard compression
            return (threshold - input_level_db) * (1.0 - 1.0 / ratio)

    def process_block(self, stereo_block: np.ndarray, num_samples: int) -> None:
        """Process block of samples with look-ahead compression."""
        if not self.params["enabled"]:
            return

        with self.lock:
            for i in range(num_samples):
                # Look-ahead processing
                if self.lookahead_delay_samples > 0:
                    # Store current sample in lookahead buffer
                    self.lookahead_buffer[self.lookahead_write_pos] = stereo_block[i, 0]
                    self.lookahead_write_pos = (self.lookahead_write_pos + 1) % len(
                        self.lookahead_buffer
                    )

                    # Read from delayed position
                    delayed_pos = (self.lookahead_write_pos - self.lookahead_delay_samples) % len(
                        self.lookahead_buffer
                    )
                    delayed_sample = self.lookahead_buffer[delayed_pos]

                    # Process delayed sample
                    processed = self.process_sample(delayed_sample)
                    stereo_block[i, 0] = processed

                    # Same for right channel
                    self.lookahead_buffer[self.lookahead_write_pos] = stereo_block[i, 1]
                    delayed_sample_r = self.lookahead_buffer[delayed_pos]
                    processed_r = self.process_sample(delayed_sample_r)
                    stereo_block[i, 1] = processed_r
                else:
                    # No look-ahead
                    stereo_block[i, 0] = self.process_sample(stereo_block[i, 0])
                    stereo_block[i, 1] = self.process_sample(stereo_block[i, 1])

    def reset(self) -> None:
        """Reset compressor state."""
        with self.lock:
            # Reset envelope followers
            self.peak_envelope["envelope"] = 0.0
            self.rms_envelope["envelope"] = 0.0

            # Clear gain reduction history
            self.gain_reduction_history.clear()

            # Reset filter state
            self.sidechain_filter_state = [0.0, 0.0, 0.0, 0.0]

            # Reset lookahead buffer
            self.lookahead_buffer.fill(0.0)
            self.lookahead_write_pos = 0


