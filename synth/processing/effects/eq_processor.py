"""XG Multi-Band Equalizer — 5-band parametric EQ with XG-compliant presets."""

from __future__ import annotations
from typing import Any
import numpy as np
from scipy import signal

SCIPY_AVAILABLE = True


class XGMultiBandEqualizer:
    """5-band parametric EQ (low/low-mid/mid/high-mid/high shelving) with XG presets 0-4."""

    EQ_PRESETS = {
        0: {"low_gain": 0.0, "low_mid_gain": 0.0, "mid_gain": 0.0, "high_mid_gain": 0.0, "high_gain": 0.0},
        1: {"low_gain": 4.0, "low_mid_gain": 3.0, "mid_gain": -2.0, "high_mid_gain": 4.0, "high_gain": 4.0},
        2: {"low_gain": 5.0, "low_mid_gain": -2.0, "mid_gain": 2.0, "high_mid_gain": 5.0, "high_gain": 3.0},
        3: {"low_gain": 5.0, "low_mid_gain": 3.0, "mid_gain": -2.0, "high_mid_gain": -2.0, "high_gain": 4.0},
        4: {"low_gain": 4.0, "low_mid_gain": 2.0, "mid_gain": 0.0, "high_mid_gain": 2.0, "high_gain": 4.0},
    }

    BAND_FREQUENCIES = {"low": 100.0, "low_mid": 300.0, "mid": 1000.0, "high_mid": 3000.0, "high": 8000.0}

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False
        self.level = 1.0
        self.eq_type = 0
        self.low_gain_db = 0.0
        self.low_mid_gain_db = 0.0
        self.mid_gain_db = 0.0
        self.high_mid_gain_db = 0.0
        self.high_gain_db = 0.0
        self.mid_freq_hz = 1000.0
        self.q_factor = 1.0
        self._filter_coeffs = {}
        self._filter_states = {}
        self._initialize_filters()
        self._temp_input = np.zeros(1024, dtype=np.float32)
        self._temp_output = np.zeros(1024, dtype=np.float32)
        self._filter_work_left: np.ndarray | None = None
        self._filter_work_right: np.ndarray | None = None
        self._eq_work_buffer: np.ndarray | None = None

    def _initialize_filters(self):
        self._filter_coeffs = {
            "low": self._create_shelving_coefficients("low", self.BAND_FREQUENCIES["low"], self.low_gain_db),
            "low_mid": self._create_parametric_coefficients(self.BAND_FREQUENCIES["low_mid"], self.low_mid_gain_db, self.q_factor),
            "mid": self._create_parametric_coefficients(self.mid_freq_hz, self.mid_gain_db, self.q_factor),
            "high_mid": self._create_parametric_coefficients(self.BAND_FREQUENCIES["high_mid"], self.high_mid_gain_db, self.q_factor),
            "high": self._create_shelving_coefficients("high", self.BAND_FREQUENCIES["high"], self.high_gain_db),
        }
        self._filter_states = {band: np.zeros(8, dtype=np.float64) for band in self._filter_coeffs}

    def _create_shelving_coefficients(self, band: str, freq: float, gain_db: float) -> np.ndarray:
        A = 10 ** (gain_db / 40.0)
        omega = 2 * np.pi * freq / self.sample_rate
        cos_omega, sin_omega = np.cos(omega), np.sin(omega)
        eq = max(self.q_factor, 0.707)
        alpha = sin_omega / (2 * eq)
        if A < 1e-6:
            A = 1e-6
        sA, aA = np.sqrt(A), A
        t1 = 2 * sA * alpha
        if band == "low":
            b0 = aA * ((aA + 1) + (aA - 1) * cos_omega + t1)
            b1 = -2 * aA * ((aA - 1) + (aA + 1) * cos_omega)
            b2 = aA * ((aA + 1) + (aA - 1) * cos_omega - t1)
            a0 = (aA + 1) - (aA - 1) * cos_omega + t1
            a1 = 2 * ((aA - 1) - (aA + 1) * cos_omega)
            a2 = (aA + 1) - (aA - 1) * cos_omega - t1
        else:
            b0 = aA * ((aA + 1) - (aA - 1) * cos_omega + t1)
            b1 = 2 * aA * ((aA - 1) - (aA + 1) * cos_omega)
            b2 = aA * ((aA + 1) - (aA - 1) * cos_omega - t1)
            a0 = (aA + 1) + (aA - 1) * cos_omega + t1
            a1 = -2 * ((aA - 1) - (aA + 1) * cos_omega)
            a2 = (aA + 1) + (aA - 1) * cos_omega - t1
        if abs(a0) < 1e-15:
            return np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        s = np.sign(A)
        return np.array([b0 * s / a0, b1 * s / a0, b2 * s / a0, a1 / a0, a2 / a0], dtype=np.float64)

    def _create_parametric_coefficients(self, freq: float, gain_db: float, q: float) -> np.ndarray:
        A = 10 ** (gain_db / 40.0)
        omega = 2 * np.pi * freq / self.sample_rate
        cos_omega, sin_omega = np.cos(omega), np.sin(omega)
        alpha = sin_omega / (2 * max(q, 0.5))
        if A < 1e-6:
            A = 1e-6
        temp = 1 + alpha / A
        if abs(temp) < 1e-15:
            return np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        return np.array([(1 + alpha * A) / temp, (-2 * cos_omega) / temp, (1 - alpha * A) / temp, (-2 * cos_omega) / temp, (1 - alpha / A) / temp], dtype=np.float64)

    def set_eq_type(self, eq_type: int):
        if 0 <= eq_type <= 4:
            self.eq_type = eq_type
            p = self.EQ_PRESETS[eq_type]
            self.low_gain_db, self.low_mid_gain_db, self.mid_gain_db, self.high_mid_gain_db, self.high_gain_db = p["low_gain"], p["low_mid_gain"], p["mid_gain"], p["high_mid_gain"], p["high_gain"]
            self._update_filter_coefficients()

    def set_low_gain(self, gain_db: float):
        self.low_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_low_mid_gain(self, gain_db: float):
        self.low_mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_mid_gain(self, gain_db: float):
        self.mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_high_mid_gain(self, gain_db: float):
        self.high_mid_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_high_gain(self, gain_db: float):
        self.high_gain_db = np.clip(gain_db, -12.0, 12.0)
        self._update_filter_coefficients()

    def set_mid_frequency(self, freq_hz: float):
        self.mid_freq_hz = np.clip(freq_hz, 100.0, 5220.0)
        self._update_filter_coefficients()

    def set_q_factor(self, q: float):
        self.q_factor = np.clip(q, 0.5, 5.5)
        self._update_filter_coefficients()

    def _update_filter_coefficients(self):
        self._initialize_filters()

    def process_buffer(self, buffer: np.ndarray) -> np.ndarray:
        if self.bypass or not self.enabled:
            return buffer  # No copy needed — caller can write through
        if buffer.ndim == 1:
            s = np.column_stack((buffer, buffer))
            return self._process_stereo_buffer_vectorized(s)[:, 0]
        return self._process_stereo_buffer_vectorized(buffer)

    def _process_stereo_buffer_vectorized(self, buffer: np.ndarray) -> np.ndarray:
        n = buffer.shape[0]
        if n > self._temp_input.shape[0]:
            self._temp_input = np.zeros(int(n * 1.5), dtype=np.float32)
            self._temp_output = np.zeros(int(n * 1.5), dtype=np.float32)
        out = buffer
        for band in ["low", "low_mid", "mid", "high_mid", "high"]:
            out = self._apply_biquad_filter_vectorized(out, band)
        if self.level != 1.0:
            out *= self.level
        return out

    def _apply_biquad_filter_vectorized(self, buf: np.ndarray, band: str) -> np.ndarray:
        b0, b1, b2, a1, a2 = self._filter_coeffs[band]
        st = self._filter_states[band]
        left, right = buf[:, 0], buf[:, 1]
        if SCIPY_AVAILABLE:
            lo, lf = signal.lfilter([b0, b1, b2], [1.0, a1, a2], left, zi=signal.lfiltic([b0, b1, b2], [1.0, a1, a2], [st[2], st[3]], [st[0], st[1]]))
            ro, rf = signal.lfilter([b0, b1, b2], [1.0, a1, a2], right, zi=signal.lfiltic([b0, b1, b2], [1.0, a1, a2], [st[6], st[7]], [st[4], st[5]]))
            st[:4] = [left[-1], left[-2] if len(left) > 1 else left[-1], lf[0], lf[1]]
            st[4:8] = [right[-1], right[-2] if len(right) > 1 else right[-1], rf[0], rf[1]]
        else:
            if self._filter_work_left is None or len(self._filter_work_left) < len(left):
                self._filter_work_left = np.zeros_like(left)
                self._filter_work_right = np.zeros_like(right)
            lo = self._filter_work_left[:len(left)]
            ro = self._filter_work_right[:len(right)]
            x = [st[0], st[1], st[4], st[5]]
            y = [st[2], st[3], st[6], st[7]]
            for ch, inp in enumerate([left, right]):
                ox, oy = x[ch * 2:ch * 2 + 2], y[ch * 2:ch * 2 + 2]
                for i in range(len(inp)):
                    y0 = b0 * inp[i] + b1 * ox[0] + b2 * ox[1] - a1 * oy[0] - a2 * oy[1]
                    if ch == 0:
                        lo[i] = y0
                    else:
                        ro[i] = y0
                    ox[1], ox[0] = ox[0], inp[i]
                    oy[1], oy[0] = oy[0], y0
                st[ch * 4:ch * 4 + 4] = [*ox, *oy]
        output = np.empty((len(lo), 2), dtype=buf.dtype)
        output[:, 0] = lo
        output[:, 1] = ro
        return output

    def reset(self):
        for state in self._filter_states.values():
            state.fill(0.0)

    def get_frequency_response(self, frequencies: np.ndarray) -> np.ndarray:
        resp = np.ones(len(frequencies), dtype=complex)
        for coeffs in self._filter_coeffs.values():
            b0, b1, b2, a1, a2 = coeffs
            z = np.exp(2j * np.pi * frequencies / self.sample_rate)
            resp *= (b0 + b1 * z + b2 * z**2) / (1.0 + a1 * z + a2 * z**2)
        return resp

    def get_parameters(self) -> dict[str, Any]:
        return {"eq_type": self.eq_type, "low_gain_db": self.low_gain_db, "low_mid_gain_db": self.low_mid_gain_db, "mid_gain_db": self.mid_gain_db, "high_mid_gain_db": self.high_mid_gain_db, "high_gain_db": self.high_gain_db, "mid_freq_hz": self.mid_freq_hz, "q_factor": self.q_factor}

    def set_parameters(self, params: dict[str, Any]):
        setters = {"eq_type": self.set_eq_type, "low_gain_db": self.set_low_gain, "low_mid_gain_db": self.set_low_mid_gain, "mid_gain_db": self.set_mid_gain, "high_mid_gain_db": self.set_high_mid_gain, "high_gain_db": self.set_high_gain, "mid_freq_hz": self.set_mid_frequency, "q_factor": self.set_q_factor}
        for k, v in params.items():
            if k in setters:
                setters[k](v)
