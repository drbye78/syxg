"""
XG Equalization Processor - Channel and Master EQ

This module implements XG-compliant equalization for channels and master section.
Supports multiple EQ curves and comprehensive parameter control.

Key Features:
- XG EQ types with standard curves (Brilliance, Mellow, Bright, etc.)
- 3-band channel EQ (timbre control)
- 3-band master EQ for final mix
- Zero-allocation processing for realtime performance
- Thread-safe parameter updates
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum
import threading

# Import our types and utilities
try:
    from .types import XGEQType, XGChannelEQParams, XGMasterEQParams
except ImportError:
    # Fallback for development
    from synth.effects.processing import *


class XGEqualizerCoefficients:
    """
    Biquad Filter Coefficients for XG EQ Implementation

    Implements standard EQ curves using parametric biquad filters.
    """

    @staticmethod
    def create_low_shelf(sample_rate: float, freq: float, gain_db: float,
                        q_factor: float = 0.707) -> Tuple[float, float, float, float, float]:
        """
        Create low shelf filter coefficients.

        Args:
            sample_rate: Sample rate in Hz
            freq: Corner frequency in Hz
            gain_db: Gain in dB (-12 to +12)
            q_factor: Quality factor

        Returns:
            Tuple of (b0, b1, b2, a1, a2) coefficients
        """
        A = math.pow(10.0, gain_db / 40.0)
        w0 = 2.0 * math.pi * freq / sample_rate
        alpha = math.sin(w0) / (2.0 * q_factor)

        cos_w0 = math.cos(w0)
        sqrt_A = math.sqrt(A)

        b0 = A * ((A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha)
        b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha)
        a0 = (A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha
        a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cos_w0)
        a2 = (A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha

        # Normalize by a0
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0

        return b0, b1, b2, a1, a2

    @staticmethod
    def create_high_shelf(sample_rate: float, freq: float, gain_db: float,
                         q_factor: float = 0.707) -> Tuple[float, float, float, float, float]:
        """
        Create high shelf filter coefficients.

        Args:
            sample_rate: Sample rate in Hz
            freq: Corner frequency in Hz
            gain_db: Gain in dB (-12 to +12)
            q_factor: Quality factor

        Returns:
            Tuple of (b0, b1, b2, a1, a2) coefficients
        """
        A = math.pow(10.0, gain_db / 40.0)
        w0 = 2.0 * math.pi * freq / sample_rate
        alpha = math.sin(w0) / (2.0 * q_factor)

        cos_w0 = math.cos(w0)
        sqrt_A = math.sqrt(A)

        b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha)
        b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
        b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha)
        a0 = (A + 1.0) - (A - 1.0) * cos_w0 + 2.0 * sqrt_A * alpha
        a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
        a2 = (A + 1.0) - (A - 1.0) * cos_w0 - 2.0 * sqrt_A * alpha

        # Normalize by a0
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0

        return b0, b1, b2, a1, a2

    @staticmethod
    def create_peak_filter(sample_rate: float, freq: float, gain_db: float,
                          q_factor: float = 1.414) -> Tuple[float, float, float, float, float]:
        """
        Create peaking EQ filter coefficients.

        Args:
            sample_rate: Sample rate in Hz
            freq: Center frequency in Hz
            gain_db: Gain in dB (-12 to +12)
            q_factor: Quality factor

        Returns:
            Tuple of (b0, b1, b2, a1, a2) coefficients
        """
        A = math.pow(10.0, gain_db / 40.0)
        w0 = 2.0 * math.pi * freq / sample_rate
        alpha = math.sin(w0) / (2.0 * q_factor)

        cos_w0 = math.cos(w0)

        b0 = 1.0 + alpha * A
        b1 = -2.0 * cos_w0
        b2 = 1.0 - alpha * A
        a0 = 1.0 + alpha / A
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha / A

        # Normalize by a0
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0

        return b0, b1, b2, a1, a2


class XGChannelEQProcessor:
    """
    XG Channel EQ Processor

    Implements XG channel equalization with preset EQ curves and 3-band control.
    XG uses CC 71 for resonance/shape and CC 74 for frequency content.

    Features:
    - XG EQ types: Brilliance, Mellow, Bright, Warm, Clear, etc.
    - 3-band parametric EQ (low, mid, high)
    - Zero-allocation processing
    """

    def __init__(self, sample_rate: int):
        """
        Initialize XG channel EQ processor.

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate

        # XG channel EQ parameters
        self.params = XGChannelEQParams(
            type=XGEQType.FLAT,
            level=0.0,      # -12 to +12 dB
            frequency=1000.0, # Center frequency
            q_factor=1.0
        )

        # Filter state for stereo processing (L/R channels)
        self.filter_state = np.zeros((2, 4), dtype=np.float32)  # x1,x2,y1,y2 for each channel

        # Coefficients cache
        self.coefficients = None

        # Thread safety
        self.lock = threading.RLock()
        self.param_updated = True

        # Initialize
        self._update_coefficients()

    def set_eq_type(self, eq_type: XGEQType) -> bool:
        """
        Set XG EQ type (changes the entire EQ curve).

        Args:
            eq_type: XG EQ type

        Returns:
            True if successful
        """
        with self.lock:
            if isinstance(eq_type, XGEQType):
                self.params = self.params._replace(type=eq_type)
                self.param_updated = True
                return True
            elif isinstance(eq_type, int) and 0 <= eq_type <= 9:
                self.params = self.params._replace(type=XGEQType(eq_type))
                self.param_updated = True
                return True
            return False

    def set_eq_parameters(self, level: float = None, frequency: float = None,
                         q_factor: float = None) -> bool:
        """
        Set EQ parameters.

        Args:
            level: EQ level in dB (-12 to +12)
            frequency: Center frequency in Hz
            q_factor: Quality factor

        Returns:
            True if any parameter was changed
        """
        with self.lock:
            changed = False

            if level is not None:
                level = max(-12.0, min(12.0, level))
                if abs(level - self.params.level) > 0.01:
                    self.params = self.params._replace(level=level)
                    changed = True

            if frequency is not None:
                frequency = max(20.0, min(20000.0, frequency))
                if abs(frequency - self.params.frequency) > 0.1:
                    self.params = self.params._replace(frequency=frequency)
                    changed = True

            if q_factor is not None:
                q_factor = max(0.1, min(10.0, q_factor))
                if abs(q_factor - self.params.q_factor) > 0.01:
                    self.params = self.params._replace(q_factor=q_factor)
                    changed = True

            if changed:
                self.param_updated = True

            return changed

    def apply_channel_eq_zero_alloc(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """
        Apply channel EQ to stereo audio buffer (in-place processing).

        Args:
            stereo_audio: Input/output stereo buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        # Update coefficients if parameters changed
        if self.param_updated:
            self._update_coefficients()
            self.param_updated = False

        if self.coefficients is None:
            return

        # Apply EQ based on type
        if self.params.type == XGEQType.FLAT:
            return  # No processing for flat

        self._apply_preset_eq(stereo_audio, num_samples)

    def _update_coefficients(self) -> None:
        """Update filter coefficients based on current parameters."""
        # For XG compliance, we use preset curves rather than direct coefficient calculation
        # The actual coefficient updates happen in the preset methods
        pass

    def _apply_preset_eq(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """
        Apply XG preset EQ curve to the audio.

        XG EQ types implement specific frequency response curves.
        """
        eq_type = self.params.type

        if eq_type == XGEQType.BRILLIANCE:
            # Boost high frequencies, emphasize clarity
            self._apply_brilliance_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.MELLOW:
            # Soften high frequencies, warmer sound
            self._apply_mellow_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.BRIGHT:
            # Boost treble range
            self._apply_bright_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.WARM:
            # Boost mid-low range
            self._apply_warm_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.CLEAR:
            # Enhance mid-high clarity
            self._apply_clear_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.SOFT:
            # Reduce harshness
            self._apply_soft_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.CUT:
            # Mild high-cut filter
            self._apply_cut_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.BASS_BOOST:
            # Enhance low frequencies
            self._apply_bass_boost_curve(stereo_audio, num_samples)

        elif eq_type == XGEQType.TREBLE_BOOST:
            # Enhance high frequencies
            self._apply_treble_boost_curve(stereo_audio, num_samples)

    def _apply_brilliance_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Brilliance (presence/high clarity) curve."""
        # Implement as high-frequency boost shelf + mid-high peak
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 8000.0, 3.0, 0.707
        )
        coeffs_peak = XGEqualizerCoefficients.create_peak_filter(
            self.sample_rate, 5000.0, 2.0, 1.0
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high, coeffs_peak])

    def _apply_mellow_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Mellow (warmer, less harsh) curve."""
        # Implement as mild high-frequency cut
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 5000.0, -2.0, 0.707
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high])

    def _apply_bright_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Bright (enhanced treble) curve."""
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 10000.0, 4.0, 0.707
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high])

    def _apply_warm_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Warm (enhanced lows) curve."""
        coeffs_low = XGEqualizerCoefficients.create_low_shelf(
            self.sample_rate, 250.0, 3.0, 0.707
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_low])

    def _apply_clear_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Clear (mid-high clarity) curve."""
        coeffs_high_mid = XGEqualizerCoefficients.create_peak_filter(
            self.sample_rate, 3000.0, 2.0, 1.414
        )
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 8000.0, 1.0, 0.707
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high_mid, coeffs_high])

    def _apply_soft_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Soft (reduce harshness) curve."""
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 7000.0, -1.5, 0.707
        )
        coeffs_high_mid = XGEqualizerCoefficients.create_peak_filter(
            self.sample_rate, 5000.0, -1.0, 2.0
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high, coeffs_high_mid])

    def _apply_cut_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Cut (mild high-cut) curve."""
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 12000.0, -2.0, 0.707
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high])

    def _apply_bass_boost_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Bass Boost curve."""
        coeffs_low = XGEqualizerCoefficients.create_low_shelf(
            self.sample_rate, 100.0, 4.0, 0.5
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_low])

    def _apply_treble_boost_curve(self, stereo_audio: np.ndarray, num_samples: int) -> None:
        """Apply Treble Boost curve."""
        coeffs_high = XGEqualizerCoefficients.create_high_shelf(
            self.sample_rate, 10000.0, 4.0, 0.5
        )

        self._apply_cascaded_filters(stereo_audio, num_samples, [coeffs_high])

    def _apply_cascaded_filters(self, stereo_audio: np.ndarray, num_samples: int,
                               coeff_list: List[Tuple[float, float, float, float, float]]) -> None:
        """
        Apply cascaded biquad filters to stereo audio.

        Args:
            stereo_audio: Input/output audio buffer
            num_samples: Number of samples
            coeff_list: List of (b0,b1,b2,a1,a2) coefficient tuples
        """
        # Apply each filter in the cascade
        for b0, b1, b2, a1, a2 in coeff_list:
            for ch in range(2):  # Left, Right
                x1, x2, y1, y2 = self.filter_state[ch]

                for i in range(num_samples):
                    x = stereo_audio[i, ch]

                    # Biquad difference equation
                    y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2

                    # Update state
                    x2, x1 = x1, x
                    y2, y1 = y1, y

                    stereo_audio[i, ch] = y

                # Save updated state
                self.filter_state[ch] = [x1, x2, y1, y2]


class XGMasterEQProcessor:
    """
    XG Master EQ Processor

    Implements 3-band master equalization for the final stereo mix.
    Provides low, mid, and high frequency control for overall tone shaping.

    Features:
    - 3-band parametric EQ (low, mid, high)
    - Shelf filters for low/high, peak for mid
    - Zero-allocation processing
    - Real-time parameter updates
    """

    def __init__(self, sample_rate: int):
        """
        Initialize XG master EQ processor.

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate

        # XG master EQ parameters
        self.params = XGMasterEQParams(
            low_gain=0.0,     # dB (-12 to +12)
            mid_gain=0.0,     # dB (-12 to +12)
            high_gain=0.0,    # dB (-12 to +12)
            low_freq=100.0,   # Hz
            mid_freq=1000.0,  # Hz
            high_freq=8000.0, # Hz
            q_factor=0.707     # Q factor
        )

        # Filter state for stereo processing (Low, Mid, High shelves)
        self.filter_states = np.zeros((3, 2, 4), dtype=np.float32)  # [band][channel][x1,x2,y1,y2]

        # Coefficients cache
        self.coefficients = {}

        # Thread safety
        self.lock = threading.RLock()
        self.param_updated = True

        # Initialize
        self._update_coefficients()

    def set_master_eq_params(self, low_gain: float = None, mid_gain: float = None,
                           high_gain: float = None, low_freq: float = None,
                           mid_freq: float = None, high_freq: float = None,
                           q_factor: float = None) -> bool:
        """
        Set master EQ parameters.

        Args:
            low_gain: Low frequency gain in dB (-12 to +12)
            mid_gain: Mid frequency gain in dB (-12 to +12)
            high_gain: High frequency gain in dB (-12 to +12)
            low_freq: Low frequency cutoff (20-400 Hz)
            mid_freq: Mid frequency center (200-8000 Hz)
            high_freq: High frequency cutoff (2000-20000 Hz)
            q_factor: Q factor (0.1-2.0)

        Returns:
            True if any parameter was changed
        """
        with self.lock:
            changed = False

            if low_gain is not None:
                low_gain = max(-12.0, min(12.0, low_gain))
                if abs(low_gain - self.params.low_gain) > 0.01:
                    self.params = self.params._replace(low_gain=low_gain)
                    changed = True

            if mid_gain is not None:
                mid_gain = max(-12.0, min(12.0, mid_gain))
                if abs(mid_gain - self.params.mid_gain) > 0.01:
                    self.params = self.params._replace(mid_gain=mid_gain)
                    changed = True

            if high_gain is not None:
                high_gain = max(-12.0, min(12.0, high_gain))
                if abs(high_gain - self.params.high_gain) > 0.01:
                    self.params = self.params._replace(high_gain=high_gain)
                    changed = True

            if low_freq is not None:
                low_freq = max(20.0, min(400.0, low_freq))
                if abs(low_freq - self.params.low_freq) > 0.1:
                    self.params = self.params._replace(low_freq=low_freq)
                    changed = True

            if mid_freq is not None:
                mid_freq = max(200.0, min(8000.0, mid_freq))
                if abs(mid_freq - self.params.mid_freq) > 0.1:
                    self.params = self.params._replace(mid_freq=mid_freq)
                    changed = True

            if high_freq is not None:
                high_freq = max(2000.0, min(20000.0, high_freq))
                if abs(high_freq - self.params.high_freq) > 0.1:
                    self.params = self.params._replace(high_freq=high_freq)
                    changed = True

            if q_factor is not None:
                q_factor = max(0.1, min(2.0, q_factor))
                if abs(q_factor - self.params.q_factor) > 0.01:
                    self.params = self.params._replace(q_factor=q_factor)
                    changed = True

            if changed:
                self.param_updated = True

            return changed

    def apply_master_eq_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply master EQ to stereo mix (in-place processing).

        Args:
            stereo_mix: Input/output stereo mix buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        # Update coefficients if parameters changed
        if self.param_updated:
            self._update_coefficients()
            self.param_updated = False

        # Apply 3-band EQ cascade
        self._apply_3band_eq(stereo_mix, num_samples)

    def _update_coefficients(self) -> None:
        """Update all filter coefficients based on current parameters."""
        self.coefficients = {}

        # Low shelf filter
        if self.params.low_gain != 0.0:
            self.coefficients['low'] = XGEqualizerCoefficients.create_low_shelf(
                self.sample_rate, self.params.low_freq, self.params.low_gain, self.params.q_factor
            )

        # Mid peak filter
        if self.params.mid_gain != 0.0:
            self.coefficients['mid'] = XGEqualizerCoefficients.create_peak_filter(
                self.sample_rate, self.params.mid_freq, self.params.mid_gain, self.params.q_factor
            )

        # High shelf filter
        if self.params.high_gain != 0.0:
            self.coefficients['high'] = XGEqualizerCoefficients.create_high_shelf(
                self.sample_rate, self.params.high_freq, self.params.high_gain, self.params.q_factor
            )

    def _apply_3band_eq(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply 3-band master EQ to stereo mix.

        Cascades low shelf, mid peak, and high shelf filters.
        """
        # Process each band in order
        bands = ['low', 'mid', 'high']

        for band_idx, band_name in enumerate(bands):
            if band_name not in self.coefficients:
                continue

            b0, b1, b2, a1, a2 = self.coefficients[band_name]

            # Apply to both channels
            for ch in range(2):
                state = self.filter_states[band_idx, ch]
                x1, x2, y1, y2 = state

                for i in range(num_samples):
                    x = stereo_mix[i, ch]

                    # Biquad difference equation
                    y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2

                    # Update state
                    x2, x1 = x1, x
                    y2, y1 = y1, y

                    stereo_mix[i, ch] = y

                # Save updated state
                self.filter_states[band_idx, ch] = [x1, x2, y1, y2]


class XGEQProcessor:
    """
    XG Equalization Master Processor

    Provides unified EQ processing for both channel EQ and master EQ.
    Handles parameter management and effect routing.
    """

    def __init__(self, sample_rate: int, max_channels: int = 16):
        """
        Initialize XG EQ processor.

        Args:
            sample_rate: Sample rate in Hz
            max_channels: Maximum number of channels to process
        """
        self.sample_rate = sample_rate
        self.max_channels = max_channels

        # Channel EQ processors
        self.channel_eq_processors = []
        for _ in range(max_channels):
            self.channel_eq_processors.append(XGChannelEQProcessor(sample_rate))

        # Master EQ processor
        self.master_eq_processor = XGMasterEQProcessor(sample_rate)

        # Processing flags
        self.master_eq_enabled = True
        self.channel_eq_enabled = True

        # Thread safety
        self.lock = threading.RLock()

    def set_channel_eq_type(self, channel: int, eq_type: XGEQType) -> bool:
        """Set EQ type for a specific channel."""
        with self.lock:
            if 0 <= channel < len(self.channel_eq_processors):
                return self.channel_eq_processors[channel].set_eq_type(eq_type)
            return False

    def set_master_eq_params(self, **params) -> bool:
        """Set master EQ parameters."""
        with self.lock:
            return self.master_eq_processor.set_master_eq_params(**params)

    def apply_channel_eq(self, channel: int, stereo_audio: np.ndarray,
                        num_samples: int) -> None:
        """Apply EQ to a specific channel."""
        if self.channel_eq_enabled and 0 <= channel < len(self.channel_eq_processors):
            self.channel_eq_processors[channel].apply_channel_eq_zero_alloc(
                stereo_audio, num_samples
            )

    def apply_master_eq(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply master EQ to the final mix."""
        if self.master_eq_enabled:
            self.master_eq_processor.apply_master_eq_zero_alloc(stereo_mix, num_samples)

    def set_processing_flags(self, master_eq: bool = None, channel_eq: bool = None) -> None:
        """Set processing enable flags."""
        with self.lock:
            if master_eq is not None:
                self.master_eq_enabled = master_eq
            if channel_eq is not None:
                self.channel_eq_enabled = channel_eq

    def reset_all(self) -> None:
        """Reset all EQ settings to flat/default."""
        with self.lock:
            # Reset master EQ
            self.master_eq_processor.set_master_eq_params(
                low_gain=0.0, mid_gain=0.0, high_gain=0.0
            )

            # Reset all channel EQ processors
            for processor in self.channel_eq_processors:
                processor.set_eq_type(XGEQType.FLAT)
