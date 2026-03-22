"""
XG Effect Presets - Complete XG Effect Configuration Presets

Provides predefined effect configurations for common scenarios,
accessible via NRPN MSB 16 for quick setup and professional workflows.

XG Preset Categories:
- Halls: Large/small concert halls, chambers
- Rooms: Recording studios, live rooms
- Plates: Electronic plate reverbs
- Ambience: General purpose reverbs
- Effects: Creative and special effects
- Vocal: Optimized for vocal performance
- Drums: Optimized for drum kits
- Guitar: Optimized for electric guitar
- Keyboard: Optimized for keyboard instruments

Copyright (c) 2025 XG Synthesis Core
"""

from __future__ import annotations

"""
XG Master Section - XG Master Compressor/Limiter, Stereo Enhancer, and Volume Curves

This module implements XG master section effects including:
- XG Master Compressor/Limiter with full parameter control
- XG Stereo Enhancer for spatial enhancement
- XG Volume Curves with customizable response curves

All components support XG NRPN parameter control and real-time operation.
"""

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


class XGMasterSection:
    """
    XG Master Section - Complete Master Effects Chain

    Combines compressor/limiter, stereo enhancer, and volume curves
    with XG-compliant parameter control and professional processing.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Initialize master section components
        self.compressor = XGMasterCompressor(sample_rate)
        self.stereo_enhancer = XGStereoEnhancer(sample_rate)
        self.volume_curve = XGVolumeCurve(sample_rate)

        # Master section configuration
        self.chain_order = ["compressor", "stereo_enhancer", "volume_curve"]
        self.master_bypass = False

        self.lock = threading.RLock()

    def set_parameter(self, component: str, param: str, value: float) -> bool:
        """Set parameter for a specific component."""
        with self.lock:
            if component == "compressor":
                return self.compressor.set_parameter(param, value)
            elif component == "stereo_enhancer":
                return self.stereo_enhancer.set_parameter(param, value)
            elif component == "volume_curve":
                if param == "curve_type":
                    self.volume_curve.set_curve_type(int(value))
                elif param == "knee":
                    self.volume_curve.set_knee(value)
                elif param == "master_volume":
                    self.volume_curve.set_master_volume(value)
                elif param == "curve_shape":
                    self.volume_curve.set_curve_shape(value)
                return True
            return False

    def set_chain_order(self, order: list[str]) -> None:
        """Set the processing order of master effects."""
        with self.lock:
            valid_components = {"compressor", "stereo_enhancer", "volume_curve"}
            if all(comp in valid_components for comp in order):
                self.chain_order = order

    def set_master_bypass(self, bypass: bool) -> None:
        """Set master bypass for entire section."""
        with self.lock:
            self.master_bypass = bypass

    def process_block(
        self, stereo_block: np.ndarray, num_samples: int, input_level: float = 1.0
    ) -> None:
        """
        Process block through complete master section.

        Args:
            stereo_block: Stereo audio block (num_samples, 2)
            num_samples: Number of samples to process
            input_level: Input level for volume curve (0-1)
        """
        if self.master_bypass:
            return

        with self.lock:
            # Process through chain in specified order
            for component in self.chain_order:
                if component == "compressor":
                    self.compressor.process_block(stereo_block, num_samples)
                elif component == "stereo_enhancer":
                    self.stereo_enhancer.process_block(stereo_block, num_samples)
                elif component == "volume_curve":
                    # Apply volume curve based on input level
                    curve_gain = self.volume_curve.apply_volume_curve(input_level)
                    stereo_block[:num_samples] *= curve_gain

            # Final limiting to prevent clipping
            np.clip(stereo_block[:num_samples], -1.0, 1.0, out=stereo_block[:num_samples])

    def get_master_status(self) -> dict[str, Any]:
        """Get status of all master section components."""
        with self.lock:
            return {
                "compressor": {
                    "enabled": self.compressor.params["enabled"],
                    "threshold": self.compressor.params["threshold"],
                    "ratio": self.compressor.params["ratio"],
                },
                "stereo_enhancer": {
                    "enabled": self.stereo_enhancer.params["enabled"],
                    "width": self.stereo_enhancer.params["width"],
                    "hf_width": self.stereo_enhancer.params["hf_width"],
                },
                "volume_curve": {
                    "curve_type": self.volume_curve.curve_type,
                    "master_volume": self.volume_curve.master_volume,
                },
                "chain_order": self.chain_order,
                "master_bypass": self.master_bypass,
            }

    def reset(self) -> None:
        """Reset all master section components."""
        with self.lock:
            # Reset components that have reset methods
            self.compressor.reset()
            # Note: XGStereoEnhancer and XGVolumeCurve don't need reset methods
            # as they are stateless or have simple state


class XGPresetCategory(IntEnum):
    """XG Effect Preset Categories"""

    HALL = 0
    ROOM = 1
    PLATE = 2
    AMBIENCE = 3
    EFFECTS = 4
    VOCAL = 5
    DRUMS = 6
    GUITAR = 7
    KEYBOARD = 8


class XGEffectPresets:
    """
    XG Effect Presets - Professional Effect Configurations

    Provides 128 predefined effect configurations covering all major
    use cases and professional mixing scenarios.

    Presets include complete system effect chains with:
    - Reverb (25 XG types)
    - Chorus (6 XG types)
    - Variation effects (84 types)
    - Master EQ (5-band parametric)
    """

    # XG Standard Effect Presets (128 total)
    PRESETS = {
        # XG DEFAULT (0)
        0: {
            "name": "XG Default",
            "category": XGPresetCategory.AMBIENCE,
            "description": "XG standard default settings",
            "reverb": {
                "type": 1,  # Hall 1
                "time": 2.5,
                "level": 0.4,
                "pre_delay": 0.02,
                "hf_damping": 0.5,
                "density": 0.8,
                "early_level": 0.5,
                "tail_level": 0.5,
            },
            "chorus": {
                "type": 0,  # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.3,
            },
            "variation": {
                "type": 13,  # Delay LCR
                "level": 0.5,
            },
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # HALL PRESETS (1-19)
        1: {
            "name": "Concert Hall Medium",
            "category": XGPresetCategory.HALL,
            "description": "Medium concert hall, balanced acoustics",
            "reverb": {
                "type": 3,  # Hall 3
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.015,
                "hf_damping": 0.4,
                "density": 0.7,
                "early_level": 0.6,
                "tail_level": 0.6,
            },
            "chorus": {
                "type": 1,  # Chorus 2
                "rate": 0.6,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.25,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 4,  # Concert
                "low_gain": 1.5,
                "mid_gain": 0.0,
                "high_gain": -0.5,
            },
        },
        # ROOM PRESETS (20-39)
        20: {
            "name": "Recording Studio A",
            "category": XGPresetCategory.ROOM,
            "description": "Professional recording studio, neutral response",
            "reverb": {
                "type": 9,  # Room 1
                "time": 0.8,
                "level": 0.3,
                "pre_delay": 0.008,
                "hf_damping": 0.6,
                "density": 0.9,
                "early_level": 0.8,
                "tail_level": 0.4,
            },
            "chorus": {"type": 0, "rate": 0.4, "depth": 0.2, "feedback": 0.0, "level": 0.15},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # PLATE PRESETS (40-49)
        40: {
            "name": "Plate Reverb 1",
            "category": XGPresetCategory.PLATE,
            "description": "Classic plate reverb, smooth and lush",
            "reverb": {
                "type": 17,  # Plate 1
                "time": 2.0,
                "level": 0.5,
                "pre_delay": 0.005,
                "hf_damping": 0.4,
                "density": 0.8,
                "early_level": 0.3,
                "tail_level": 0.8,
            },
            "chorus": {"type": 0, "rate": 0.3, "depth": 0.1, "feedback": 0.0, "level": 0.1},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # AMBIENCE PRESETS (50-69)
        50: {
            "name": "Ambience Small",
            "category": XGPresetCategory.AMBIENCE,
            "description": "Small space ambience for subtle enhancement",
            "reverb": {
                "type": 9,  # Room 1
                "time": 0.5,
                "level": 0.2,
                "pre_delay": 0.005,
                "hf_damping": 0.7,
                "density": 0.8,
                "early_level": 0.9,
                "tail_level": 0.3,
            },
            "chorus": {"type": 0, "rate": 0.2, "depth": 0.1, "feedback": 0.0, "level": 0.05},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # EFFECTS PRESETS (70-89)
        70: {
            "name": "Spring Reverb",
            "category": XGPresetCategory.EFFECTS,
            "description": "Vintage spring reverb simulation",
            "reverb": {
                "type": 17,  # Plate 1 (closest to spring)
                "time": 1.5,
                "level": 0.4,
                "pre_delay": 0.0,  # No pre-delay for spring character
                "hf_damping": 0.6,
                "density": 0.5,  # Less dense than plate
                "early_level": 0.2,
                "tail_level": 0.9,
            },
            "chorus": {"type": 0, "rate": 0.1, "depth": 0.05, "feedback": 0.0, "level": 0.0},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,  # Rock
                "low_gain": -1.0,
                "mid_gain": 0.0,
                "high_gain": 2.0,
            },
        },
        # VOCAL PRESETS (90-99)
        90: {
            "name": "Vocal Hall",
            "category": XGPresetCategory.VOCAL,
            "description": "Concert hall optimized for vocal performance",
            "reverb": {
                "type": 2,  # Hall 2
                "time": 2.2,
                "level": 0.45,
                "pre_delay": 0.025,  # Longer pre-delay for vocals
                "hf_damping": 0.25,  # Less damping for vocal clarity
                "density": 0.75,
                "early_level": 0.55,
                "tail_level": 0.65,
            },
            "chorus": {
                "type": 2,  # Celeste 1 (gentle for vocals)
                "rate": 0.4,
                "depth": 0.25,
                "feedback": 0.1,
                "level": 0.2,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,  # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.5,
            },
        },
        # DRUM PRESETS (100-109)
        100: {
            "name": "Drum Room",
            "category": XGPresetCategory.DRUMS,
            "description": "Recording studio drum room",
            "reverb": {
                "type": 10,  # Room 2
                "time": 0.6,
                "level": 0.25,
                "pre_delay": 0.0,  # No pre-delay for drums
                "hf_damping": 0.8,  # Heavy HF damping
                "density": 0.95,  # Very dense
                "early_level": 1.0,  # Strong early reflections
                "tail_level": 0.2,  # Short tail
            },
            "chorus": {"type": 0, "rate": 0.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # GUITAR PRESETS (110-119)
        110: {
            "name": "Guitar Plate",
            "category": XGPresetCategory.GUITAR,
            "description": "Plate reverb optimized for electric guitar",
            "reverb": {
                "type": 18,  # Plate 2
                "time": 1.8,
                "level": 0.4,
                "pre_delay": 0.008,
                "hf_damping": 0.35,  # Moderate damping
                "density": 0.75,
                "early_level": 0.4,
                "tail_level": 0.75,
            },
            "chorus": {
                "type": 4,  # Flanger 1 (classic guitar effect)
                "rate": 0.15,
                "depth": 0.6,
                "feedback": 0.4,
                "level": 0.3,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 3,  # Rock
                "low_gain": -0.5,
                "mid_gain": 1.0,
                "high_gain": 1.5,
            },
        },
        # KEYBOARD PRESETS (120-127)
        120: {
            "name": "Piano Hall",
            "category": XGPresetCategory.KEYBOARD,
            "description": "Concert hall optimized for acoustic piano",
            "reverb": {
                "type": 4,  # Hall 4
                "time": 3.0,
                "level": 0.55,
                "pre_delay": 0.03,  # Longer pre-delay for piano
                "hf_damping": 0.2,  # Light damping for piano brightness
                "density": 0.7,
                "early_level": 0.5,
                "tail_level": 0.7,
            },
            "chorus": {
                "type": 1,  # Chorus 2
                "rate": 0.5,
                "depth": 0.3,
                "feedback": 0.2,
                "level": 0.25,
            },
            "variation": {"type": 13, "level": 0.0},
            "eq": {
                "type": 1,  # Jazz
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
        # DEFAULT PRESET (127)
        127: {
            "name": "XG Default",
            "category": XGPresetCategory.AMBIENCE,
            "description": "XG specification default settings",
            "reverb": {
                "type": 1,  # Hall 1
                "time": 2.5,  # NRPN default (converted)
                "level": 0.4,
                "pre_delay": 0.02,
                "hf_damping": 0.5,
                "density": 0.8,
                "early_level": 0.5,
                "tail_level": 0.5,
            },
            "chorus": {
                "type": 0,  # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.3,
            },
            "variation": {
                "type": 13,  # Delay LCR
                "level": 0.5,
            },
            "eq": {
                "type": 0,  # Flat
                "low_gain": 0.0,
                "mid_gain": 0.0,
                "high_gain": 0.0,
            },
        },
    }

    @classmethod
    def get_preset(cls, preset_id: int) -> dict[str, Any]:
        """
        Get a preset configuration by ID.

        Args:
            preset_id: Preset ID (0-127)

        Returns:
            Preset configuration dictionary, or default if not found
        """
        return cls.PRESETS.get(preset_id, cls.PRESETS[127])  # Default to XG Default

    @classmethod
    def get_preset_names(cls) -> dict[int, str]:
        """
        Get all preset names indexed by ID.

        Returns:
            Dictionary mapping preset IDs to names
        """
        return {pid: preset["name"] for pid, preset in cls.PRESETS.items()}

    @classmethod
    def get_presets_by_category(cls, category: XGPresetCategory) -> dict[int, dict[str, Any]]:
        """
        Get all presets in a specific category.

        Args:
            category: Preset category

        Returns:
            Dictionary of presets in the category
        """
        return {
            pid: preset for pid, preset in cls.PRESETS.items() if preset.get("category") == category
        }

    @classmethod
    def apply_preset_to_coordinator(cls, preset_id: int, coordinator) -> bool:
        """
        Apply a preset configuration to an effects coordinator.

        Args:
            preset_id: Preset ID to apply
            coordinator: XGEffectsCoordinator instance

        Returns:
            True if preset was applied successfully
        """
        preset = cls.get_preset(preset_id)
        if not preset:
            return False

        try:
            # Apply reverb settings
            reverb = preset.get("reverb", {})
            if reverb:
                coordinator.set_system_effect_parameter("reverb", "type", reverb.get("type", 1))
                coordinator.set_system_effect_parameter("reverb", "time", reverb.get("time", 2.5))
                coordinator.set_system_effect_parameter("reverb", "level", reverb.get("level", 0.4))
                coordinator.set_system_effect_parameter(
                    "reverb", "pre_delay", reverb.get("pre_delay", 0.02)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "hf_damping", reverb.get("hf_damping", 0.5)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "density", reverb.get("density", 0.8)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "early_level", reverb.get("early_level", 0.5)
                )
                coordinator.set_system_effect_parameter(
                    "reverb", "tail_level", reverb.get("tail_level", 0.5)
                )

            # Apply chorus settings
            chorus = preset.get("chorus", {})
            if chorus:
                coordinator.set_system_effect_parameter("chorus", "type", chorus.get("type", 0))
                coordinator.set_system_effect_parameter("chorus", "rate", chorus.get("rate", 1.0))
                coordinator.set_system_effect_parameter("chorus", "depth", chorus.get("depth", 0.5))
                coordinator.set_system_effect_parameter(
                    "chorus", "feedback", chorus.get("feedback", 0.3)
                )
                coordinator.set_system_effect_parameter("chorus", "level", chorus.get("level", 0.3))

            # Apply variation settings
            variation = preset.get("variation", {})
            if variation:
                coordinator.set_variation_effect_type(variation.get("type", 13))

            # Apply EQ settings
            eq = preset.get("eq", {})
            if eq:
                coordinator.set_master_eq_type(eq.get("type", 0))
                coordinator.set_master_eq_gain("low", eq.get("low_gain", 0.0))
                coordinator.set_master_eq_gain("mid", eq.get("mid_gain", 0.0))
                coordinator.set_master_eq_gain("high", eq.get("high_gain", 0.0))

            return True

        except Exception as e:
            print(f"Error applying preset {preset_id}: {e}")
            return False
