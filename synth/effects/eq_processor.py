"""
XG Multi-Band Equalizer Implementation

Conforms to MIDI XG specification for system equalizer effects.
Provides 5-band parametric EQ with XG-compliant parameter ranges and control.
"""
from __future__ import annotations

import numpy as np
from typing import Any
import math

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class XGMultiBandEqualizer:
    """
    XG-Conformant Multi-Band Equalizer

    Implements the MIDI XG system equalizer with 5 frequency bands:
    - Low: ~100 Hz (shelving)
    - Low-Mid: ~300 Hz (parametric)
    - Mid: 1000-5220 Hz (parametric, controllable)
    - High-Mid: ~3000 Hz (parametric)
    - High: ~8000 Hz (shelving)

    XG Parameters (System Effects NRPN):
    - EQ Type: 0-4 (Flat, Jazz, Pops, Rock, Concert)
    - EQ Gain Low: -12 to +12 dB
    - EQ Gain Mid: -12 to +12 dB
    - EQ Gain High: -12 to +12 dB
    - EQ Frequency Mid: 100-5220 Hz
    - EQ Q Factor: 0.5-5.5
    """

    # XG EQ Type Presets (gain values in dB)
    EQ_PRESETS = {
        0: {  # Flat
            "low_gain": 0.0,
            "low_mid_gain": 0.0,
            "mid_gain": 0.0,
            "high_mid_gain": 0.0,
            "high_gain": 0.0
        },
        1: {  # Jazz
            "low_gain": 4.0,
            "low_mid_gain": 3.0,
            "mid_gain": -2.0,
            "high_mid_gain": 4.0,
            "high_gain": 4.0
        },
        2: {  # Pops
            "low_gain": 5.0,
            "low_mid_gain": -2.0,
            "mid_gain": 2.0,
            "high_mid_gain": 5.0,
            "high_gain": 3.0
        },
        3: {  # Rock
            "low_gain": 5.0,
            "low_mid_gain": 3.0,
            "mid_gain": -2.0,
            "high_mid_gain": -2.0,
            "high_gain": 4.0
        },
        4: {  # Concert
            "low_gain": 4.0,
            "low_mid_gain": 2.0,
            "mid_gain": 0.0,
            "high_mid_gain": 2.0,
            "high_gain": 4.0
        }
    }

    # Fixed frequency bands (XG specification)
    BAND_FREQUENCIES = {
        "low": 100.0,        # Low shelving
        "low_mid": 300.0,    # Low-mid parametric
        "mid": 1000.0,       # Mid parametric (variable 100-5220 Hz)
        "high_mid": 3000.0,  # High-mid parametric
        "high": 8000.0       # High shelving
    }

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize XG Multi-Band Equalizer

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False
        self.level = 1.0

        # XG EQ Parameters
        self.eq_type = 0  # 0-4 (Flat, Jazz, Pops, Rock, Concert)
        self.low_gain_db = 0.0      # -12 to +12 dB
        self.low_mid_gain_db = 0.0  # Fixed gain for low-mid band
        self.mid_gain_db = 0.0      # -12 to +12 dB
        self.high_mid_gain_db = 0.0 # Fixed gain for high-mid band
        self.high_gain_db = 0.0     # -12 to +12 dB
        self.mid_freq_hz = 1000.0   # 100-5220 Hz
        self.q_factor = 1.0         # 0.5-5.5

        # Internal filter coefficients (pre-computed for performance)
        self._filter_coeffs = {}
        self._filter_states = {}  # For IIR filter persistence across buffers
        self._initialize_filters()

        # Pre-allocate arrays for performance (reusing memory)
        self._temp_input = np.zeros(1024, dtype=np.float32)
        self._temp_output = np.zeros(1024, dtype=np.float32)

    def _initialize_filters(self):
        """Initialize biquad filter coefficients for each EQ band"""
        self._filter_coeffs = {
            "low": self._create_shelving_coefficients("low", self.BAND_FREQUENCIES["low"], self.low_gain_db),
            "low_mid": self._create_parametric_coefficients(self.BAND_FREQUENCIES["low_mid"], self.low_mid_gain_db, self.q_factor),
            "mid": self._create_parametric_coefficients(self.mid_freq_hz, self.mid_gain_db, self.q_factor),
            "high_mid": self._create_parametric_coefficients(self.BAND_FREQUENCIES["high_mid"], self.high_mid_gain_db, self.q_factor),
            "high": self._create_shelving_coefficients("high", self.BAND_FREQUENCIES["high"], self.high_gain_db)
        }

        # Initialize filter states for each band [left_x1, left_x2, left_y1, left_y2, right_x1, right_x2, right_y1, right_y2]
        self._filter_states = {
            band: np.zeros(8, dtype=np.float64) for band in self._filter_coeffs.keys()
        }

    def _create_shelving_coefficients(self, band: str, freq: float, gain_db: float) -> np.ndarray:
        """
        Create a shelving filter (low/high shelf) coefficients using standard cookbook formula

        Args:
            band: Band name ("low" or "high")
            freq: Corner frequency in Hz
            gain_db: Gain in dB

        Returns:
            Filter coefficients array [b0, b1, b2, a1, a2]
        """
        # Convert gain to linear
        A = 10 ** (gain_db / 20.0)

        # Calculate filter coefficients using standard cookbook formula
        omega = 2 * np.pi * freq / self.sample_rate
        cos_omega = np.cos(omega)
        sin_omega = np.sin(omega)

        # Use default Q value for shelving filters to avoid numerical issues
        effective_q = max(self.q_factor, 0.707)  # Use minimum Q to avoid issues
        alpha = sin_omega / (2 * effective_q)

        # For numerical stability, avoid division by very small numbers
        if abs(A) < 1e-6:
            # This shouldn't happen with normal gain values, but just in case
            A = 1e-6 if A > 0 else -1e-6

        # Low shelf filter coefficients
        if band == "low":
            # Low shelf: cookbook formula
            sqrt_A = np.sqrt(abs(A))
            temp1 = 2 * sqrt_A * alpha
            temp2 = (abs(A) + 1) - (abs(A) - 1) * cos_omega

            b0 = abs(A) * ((abs(A) + 1) + (abs(A) - 1) * cos_omega + temp1)
            b1 = -2 * abs(A) * ((abs(A) - 1) + (abs(A) + 1) * cos_omega)
            b2 = abs(A) * ((abs(A) + 1) + (abs(A) - 1) * cos_omega - temp1)
            a0 = (abs(A) + 1) - (abs(A) - 1) * cos_omega + temp1
            a1 = 2 * ((abs(A) - 1) - (abs(A) + 1) * cos_omega)
            a2 = (abs(A) + 1) - (abs(A) - 1) * cos_omega - temp1
        else:  # High shelf
            sqrt_A = np.sqrt(abs(A))
            temp1 = 2 * sqrt_A * alpha
            temp2 = (abs(A) + 1) - (abs(A) - 1) * cos_omega

            b0 = abs(A) * ((abs(A) + 1) - (abs(A) - 1) * cos_omega + temp1)
            b1 = 2 * abs(A) * ((abs(A) - 1) - (abs(A) + 1) * cos_omega)
            b2 = abs(A) * ((abs(A) + 1) - (abs(A) - 1) * cos_omega - temp1)
            a0 = (abs(A) + 1) + (abs(A) - 1) * cos_omega + temp1
            a1 = -2 * ((abs(A) - 1) - (abs(A) + 1) * cos_omega)
            a2 = (abs(A) + 1) + (abs(A) - 1) * cos_omega - temp1

        # Ensure a0 is not zero to avoid division by zero
        if abs(a0) < 1e-15:
            # Return a neutral filter (bypass) if coefficients are unstable
            return np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

        # Apply sign of original A to b coefficients
        sign_a = np.sign(A)
        b0 *= sign_a
        b1 *= sign_a
        b2 *= sign_a

        # Normalize by a0
        return np.array([b0/a0, b1/a0, b2/a0, a1/a0, a2/a0], dtype=np.float64)

    def _create_parametric_coefficients(self, freq: float, gain_db: float, q: float) -> np.ndarray:
        """
        Create a parametric (peaking) filter coefficients using standard cookbook formula

        Args:
            freq: Center frequency in Hz
            gain_db: Gain in dB
            q: Q factor

        Returns:
            Filter coefficients array [b0, b1, b2, a1, a2]
        """
        # Convert gain to linear
        A = 10 ** (gain_db / 20.0)

        # Calculate filter coefficients
        omega = 2 * np.pi * freq / self.sample_rate
        cos_omega = np.cos(omega)
        sin_omega = np.sin(omega)

        # Use a minimum Q to prevent numerical issues
        effective_q = max(q, 0.5)
        alpha = sin_omega / (2 * effective_q)

        # For numerical stability, avoid division by very small numbers
        # When A is small (high negative gain), we need extra care
        if abs(A) < 1e-6:
            # This shouldn't happen with normal gain values, but just in case
            A = 1e-6 if A > 0 else -1e-6

        # Peaking EQ coefficients using cookbook formula
        # Use safe division to avoid numerical issues
        temp = 1 + alpha / A
        if abs(temp) < 1e-15:
            # If temp is too small, return a neutral filter (bypass)
            return np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

        b0 = (1 + alpha * A) / temp
        b1 = (-2 * cos_omega) / temp
        b2 = (1 - alpha * A) / temp
        a1 = (-2 * cos_omega) / temp
        a2 = (1 - alpha / A) / temp

        return np.array([b0, b1, b2, a1, a2], dtype=np.float64)

    def set_eq_type(self, eq_type: int):
        """
        Set EQ type (XG preset)

        Args:
            eq_type: EQ type 0-4 (Flat, Jazz, Pops, Rock, Concert)
        """
        if 0 <= eq_type <= 4:
            self.eq_type = eq_type
            preset = self.EQ_PRESETS[eq_type]

            # Apply preset gains
            self.low_gain_db = preset["low_gain"]
            self.low_mid_gain_db = preset["low_mid_gain"]
            self.mid_gain_db = preset["mid_gain"]
            self.high_mid_gain_db = preset["high_mid_gain"]
            self.high_gain_db = preset["high_gain"]

            # Update filter coefficients
            self._update_filter_coefficients()

    def set_low_gain(self, gain_db: float):
        """
        Set low band gain

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.low_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_low_mid_gain(self, gain_db: float):
        """
        Set low-mid band gain

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.low_mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_mid_gain(self, gain_db: float):
        """
        Set mid band gain

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_high_mid_gain(self, gain_db: float):
        """
        Set high-mid band gain

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.high_mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_high_gain(self, gain_db: float):
        """
        Set high band gain

        Args:
            gain_db: Gain in dB (-12 to +12)
        """
        self.high_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_mid_frequency(self, freq_hz: float):
        """
        Set mid band frequency

        Args:
            freq_hz: Frequency in Hz (100-5220)
        """
        self.mid_freq_hz = np.clip(freq_hz, 100.0, 5220.0)
        self._update_filter_coefficients()

    def set_q_factor(self, q: float):
        """
        Set Q factor for parametric bands

        Args:
            q: Q factor (0.5-5.5)
        """
        self.q_factor = np.clip(q, 0.5, 5.5)
        self._update_filter_coefficients()

    def _update_filter_coefficients(self):
        """Update all filter coefficients based on current parameters"""
        self._filter_coeffs["low"] = self._create_shelving_coefficients("low", self.BAND_FREQUENCIES["low"], self.low_gain_db)
        self._filter_coeffs["low_mid"] = self._create_parametric_coefficients(self.BAND_FREQUENCIES["low_mid"], self.low_mid_gain_db, self.q_factor)
        self._filter_coeffs["mid"] = self._create_parametric_coefficients(self.mid_freq_hz, self.mid_gain_db, self.q_factor)
        self._filter_coeffs["high_mid"] = self._create_parametric_coefficients(self.BAND_FREQUENCIES["high_mid"], self.high_mid_gain_db, self.q_factor)
        self._filter_coeffs["high"] = self._create_shelving_coefficients("high", self.BAND_FREQUENCIES["high"], self.high_gain_db)

    def process_buffer(self, buffer: np.ndarray) -> np.ndarray:
        """
        Process a buffer of samples through the EQ using FULLY VECTORIZED operations

        Args:
            buffer: Input buffer (can be 1D mono or 2D stereo)

        Returns:
            Processed buffer
        """
        if self.bypass or not self.enabled:
            return buffer.copy()

        if buffer.ndim == 1:
            # Mono processing - duplicate to stereo, process, then take left channel
            stereo_input = np.column_stack((buffer, buffer))
            stereo_output = self._process_stereo_buffer_vectorized(stereo_input)
            return stereo_output[:, 0]  # Return mono channel
        else:
            # Stereo processing
            return self._process_stereo_buffer_vectorized(buffer)

    def _process_stereo_buffer_vectorized(self, buffer: np.ndarray) -> np.ndarray:
        """
        FULLY VECTORIZED: Process entire stereo buffer through all EQ bands at once

        This implementation uses vectorized operations for maximum performance:
        1. All samples in each channel are processed simultaneously
        2. All 5 equalizer bands are applied in sequence as vectorized operations
        3. Filter state is maintained between calls for continuous processing
        4. Memory is reused to avoid allocations during processing

        Args:
            buffer: Stereo input buffer (N x 2)

        Returns:
            Processed stereo buffer (N x 2)
        """
        # Ensure we have enough space in temp arrays
        n_samples = buffer.shape[0]
        if n_samples > self._temp_input.shape[0]:
            # Reallocate with some headroom
            size = int(n_samples * 1.5)
            self._temp_input = np.zeros(size, dtype=np.float32)
            self._temp_output = np.zeros(size, dtype=np.float32)

        # Work with a copy of the input buffer
        output = buffer.copy()

        # Process each equalizer band in sequence using vectorized operations
        for band_name in ["low", "low_mid", "mid", "high_mid", "high"]:
            output = self._apply_biquad_filter_vectorized(output, band_name)

        # Apply level scaling if different from 1.0
        if self.level != 1.0:
            output *= self.level

        return output

    def _apply_biquad_filter_vectorized(self, stereo_buffer: np.ndarray, band_name: str) -> np.ndarray:
        """
        HIGHLY OPTIMIZED: Apply biquad filter to stereo buffer using true vectorized operations

        This implementation processes the entire buffer using scipy.lfilter when available,
        which provides maximum performance by eliminating per-sample loops.

        Args:
            stereo_buffer: Stereo input buffer (N x 2)
            band_name: Name of the band to apply

        Returns:
            Filtered stereo buffer (N x 2)
        """
        # Get filter coefficients for this band
        coeffs = self._filter_coeffs[band_name]
        b0, b1, b2, a1, a2 = coeffs

        # Get the filter state for this band
        state = self._filter_states[band_name]

        # Extract left and right channels
        left_in = stereo_buffer[:, 0]
        right_in = stereo_buffer[:, 1]

        if SCIPY_AVAILABLE:
            # Use scipy's optimized lfilter with initial conditions for maximum performance
            from scipy import signal

            # Process left channel with preserved filter state
            left_initial_conditions = signal.lfiltic([b0, b1, b2], [1.0, a1, a2],
                                                    [state[2], state[3]],  # y values [y(n-1), y(n-2)]
                                                    [state[0], state[1]])  # x values [x(n-1), x(n-2)]
            left_out, left_final_state = signal.lfilter([b0, b1, b2], [1.0, a1, a2],
                                                       left_in, zi=left_initial_conditions)

            # Process right channel with preserved filter state
            right_initial_conditions = signal.lfiltic([b0, b1, b2], [1.0, a1, a2],
                                                     [state[6], state[7]],  # y values [y(n-1), y(n-2)]
                                                     [state[4], state[5]])  # x values [x(n-1), x(n-2)]
            right_out, right_final_state = signal.lfilter([b0, b1, b2], [1.0, a1, a2],
                                                         right_in, zi=right_initial_conditions)

            # Update the state with final values from the filter
            state[0:4] = [left_in[-1], left_in[-2] if len(left_in) > 1 else left_in[-1],
                         left_final_state[0], left_final_state[1]]  # x1, x2, y1, y2 for left
            state[4:8] = [right_in[-1], right_in[-2] if len(right_in) > 1 else right_in[-1],
                         right_final_state[0], right_final_state[1]]  # x1, x2, y1, y2 for right
        else:
            # Pure NumPy implementation as fallback - not ideal but functional
            # Process left channel
            left_out = np.zeros_like(left_in)
            x1_l, x2_l = state[0], state[1]
            y1_l, y2_l = state[2], state[3]

            for i in range(len(left_in)):
                y0 = b0 * left_in[i] + b1 * x1_l + b2 * x2_l - a1 * y1_l - a2 * y2_l
                left_out[i] = y0
                x2_l, x1_l = x1_l, left_in[i]
                y2_l, y1_l = y1_l, y0

            # Process right channel
            right_out = np.zeros_like(right_in)
            x1_r, x2_r = state[4], state[5]
            y1_r, y2_r = state[6], state[7]

            for i in range(len(right_in)):
                y0 = b0 * right_in[i] + b1 * x1_r + b2 * x2_r - a1 * y1_r - a2 * y2_r
                right_out[i] = y0
                x2_r, x1_r = x1_r, right_in[i]
                y2_r, y1_r = y1_r, y0

            # Update state
            state[0], state[1] = x1_l, x2_l
            state[2], state[3] = y1_l, y2_l
            state[4], state[5] = x1_r, x2_r
            state[6], state[7] = y1_r, y2_r

        # Return the processed stereo output
        return np.column_stack((left_out, right_out)).astype(stereo_buffer.dtype)

    def reset(self):
        """Reset filter states"""
        for state in self._filter_states.values():
            state.fill(0.0)

    def get_frequency_response(self, frequencies: np.ndarray) -> np.ndarray:
        """
        Get frequency response of the EQ

        Args:
            frequencies: Array of frequencies in Hz

        Returns:
            Complex frequency response
        """
        response = np.ones(len(frequencies), dtype=complex)

        for band, coeffs in self._filter_coeffs.items():
            # Calculate frequency response for this band
            b0, b1, b2, a1, a2 = coeffs
            b = np.array([b0, b1, b2])
            a = np.array([1.0, a1, a2])  # a0 is normalized to 1

            # Evaluate transfer function at given frequencies
            omega = 2 * np.pi * frequencies / self.sample_rate
            z = np.exp(1j * omega)

            # Direct form transfer function evaluation
            num = b[0] + b[1] * z + b[2] * z**2
            den = a[0] + a[1] * z + a[2] * z**2

            response *= num / den

        return response

    def get_parameters(self) -> dict[str, Any]:
        """Get current EQ parameters"""
        return {
            "eq_type": self.eq_type,
            "low_gain_db": self.low_gain_db,
            "low_mid_gain_db": self.low_mid_gain_db,
            "mid_gain_db": self.mid_gain_db,
            "high_mid_gain_db": self.high_mid_gain_db,
            "high_gain_db": self.high_gain_db,
            "mid_freq_hz": self.mid_freq_hz,
            "q_factor": self.q_factor
        }

    def set_parameters(self, params: dict[str, Any]):
        """Set EQ parameters"""
        if "eq_type" in params:
            self.set_eq_type(params["eq_type"])
        if "low_gain_db" in params:
            self.set_low_gain(params["low_gain_db"])
        if "low_mid_gain_db" in params:
            self.set_low_mid_gain(params["low_mid_gain_db"])
        if "mid_gain_db" in params:
            self.set_mid_gain(params["mid_gain_db"])
        if "high_mid_gain_db" in params:
            self.set_high_mid_gain(params["high_mid_gain_db"])
        if "high_gain_db" in params:
            self.set_high_gain(params["high_gain_db"])
        if "mid_freq_hz" in params:
            self.set_mid_frequency(params["mid_freq_hz"])
        if "q_factor" in params:
            self.set_q_factor(params["q_factor"])
