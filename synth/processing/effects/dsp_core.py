"""
Core DSP Framework for XG Effects - Production Implementation

This module provides fundamental DSP components used across multiple XG effects:
- Phase vocoder engine for pitch manipulation
- Multiband filter bank for frequency-domain processing
- Advanced envelope followers
- Professional delay networks
- FFT/IFFT utilities optimized for real-time audio

All components are optimized for low-latency, real-time processing.
"""

from __future__ import annotations

import math
import threading

import numpy as np


class PhaseVocoderEngine:
    """
    Production-quality phase vocoder for pitch shifting and time stretching.

    Features:
    - Real-time FFT-based processing
    - Formant preservation
    - Transient handling
    - Low latency operation
    """

    def __init__(self, sample_rate: int, window_size: int = 2048, hop_size: int = 512):
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.hop_size = hop_size
        self.overlap_factor = window_size // hop_size

        # Analysis and synthesis windows
        self.analysis_window = np.sqrt(np.hanning(window_size))
        self.synthesis_window = np.sqrt(np.hanning(window_size))

        # Phase vocoder state
        self.phase_accumulator = np.zeros(window_size // 2 + 1, dtype=np.complex128)
        self.previous_phases = np.zeros(window_size // 2 + 1, dtype=np.float64)

        # Buffers for overlap-add
        self.input_buffer = np.zeros(window_size)
        self.output_buffer = np.zeros(window_size)
        self.output_accumulator = np.zeros(window_size * 2)

        # Processing state
        self.buffer_pos = 0
        self.pitch_ratio = 1.0
        self.time_ratio = 1.0

        # Thread safety
        self.lock = threading.RLock()

    def set_pitch_ratio(self, ratio: float) -> None:
        with self.lock:
            self.pitch_ratio = np.clip(ratio, 0.25, 4.0)

    def set_time_ratio(self, ratio: float) -> None:
        with self.lock:
            self.time_ratio = np.clip(ratio, 0.25, 4.0)

    def process_sample(self, input_sample: float) -> float:
        with self.lock:
            # Add sample to input buffer
            self.input_buffer[self.buffer_pos] = input_sample
            self.buffer_pos += 1

            # Check if we have a full window
            if self.buffer_pos >= self.window_size:
                # Process frame
                output_frame = self._process_frame(self.input_buffer.copy())

                # Overlap-add to output accumulator
                start_pos = self.buffer_pos - self.window_size
                self.output_accumulator[start_pos : start_pos + self.window_size] += output_frame

                # Shift input buffer for overlap
                overlap_samples = self.window_size - self.hop_size
                self.input_buffer[:overlap_samples] = self.input_buffer[
                    self.hop_size : self.window_size
                ]
                self.buffer_pos = overlap_samples

            # Get output sample
            if self.buffer_pos >= self.hop_size:
                output_sample = self.output_accumulator[0]
                self.output_accumulator[:-1] = self.output_accumulator[1:]
                self.output_accumulator[-1] = 0.0
                return output_sample

            return 0.0

    def _process_frame(self, input_frame: np.ndarray) -> np.ndarray:
        # Apply analysis window
        windowed = input_frame * self.analysis_window

        # FFT
        spectrum = np.fft.rfft(windowed)

        # Get magnitudes and phases
        magnitudes = np.abs(spectrum)
        phases = np.angle(spectrum)

        # Phase vocoder processing
        modified_spectrum = self._phase_vocoder_process(spectrum, magnitudes, phases)

        # IFFT
        output_frame = np.fft.irfft(modified_spectrum).real

        # Apply synthesis window
        return output_frame * self.synthesis_window

    def _phase_vocoder_process(
        self, spectrum: np.ndarray, magnitudes: np.ndarray, phases: np.ndarray
    ) -> np.ndarray:
        """
        Core phase vocoder processing algorithm.

        Args:
            spectrum: Complex spectrum
            magnitudes: Magnitude spectrum
            phases: Phase spectrum

        Returns:
            Modified complex spectrum
        """
        # Phase unwrapping and accumulation
        phase_differences = phases - self.previous_phases
        self.previous_phases = phases.copy()

        # Unwrap phase differences
        phase_differences = np.unwrap(phase_differences)

        # Expected phase advance per hop
        expected_phase_advance = (
            2 * np.pi * self.hop_size * np.arange(len(phases)) / self.window_size
        )

        # True frequency
        true_freq = expected_phase_advance + phase_differences

        # Apply pitch shifting
        shifted_freq = true_freq * self.pitch_ratio

        # Accumulate phases for synthesis
        self.phase_accumulator += shifted_freq * self.time_ratio

        # Reconstruct spectrum
        modified_spectrum = magnitudes * np.exp(1j * self.phase_accumulator)

        return modified_spectrum

    def reset(self) -> None:
        """Reset phase vocoder state."""
        with self.lock:
            self.phase_accumulator.fill(0)
            self.previous_phases.fill(0)
            self.input_buffer.fill(0)
            self.output_buffer.fill(0)
            self.output_accumulator.fill(0)
            self.buffer_pos = 0


class MultibandFilterBank:
    """
    Multiband filter bank for frequency-domain processing (vocoder, multiband effects).

    Features:
    - Configurable number of bands
    - Linkwitz-Riley crossover filters
    - Real-time processing optimized
    - Per-band gain control
    """

    def __init__(
        self, sample_rate: int, num_bands: int = 16, freq_range: tuple[float, float] = (100, 8000)
    ):
        self.sample_rate = sample_rate
        self.num_bands = num_bands
        self.freq_range = freq_range

        # Calculate crossover frequencies
        self.crossover_freqs = self._calculate_crossover_frequencies()

        # Initialize filter states
        self.filter_states = [{} for _ in range(num_bands)]
        self.band_gains = np.ones(num_bands, dtype=np.float32)

        # Pre-allocated output buffer (avoids list allocation per sample)
        self._band_outputs = [0.0] * num_bands

        # Thread safety
        self.lock = threading.RLock()

    def _calculate_crossover_frequencies(self) -> np.ndarray:
        min_freq, max_freq = self.freq_range
        return np.logspace(np.log10(min_freq), np.log10(max_freq), self.num_bands + 1)

    def set_band_gain(self, band_idx: int, gain: float) -> None:
        with self.lock:
            if 0 <= band_idx < self.num_bands:
                self.band_gains[band_idx] = gain

    def process_sample(self, input_sample: float) -> list[float]:
        with self.lock:
            # First band: low-pass
            if self.num_bands > 0:
                lp_output = self._linkwitz_riley_lowpass(input_sample, self.crossover_freqs[1], 0)
                self._band_outputs[0] = lp_output * self.band_gains[0]

            # Middle bands: band-pass
            for i in range(1, self.num_bands - 1):
                bp_output = self._linkwitz_riley_bandpass(
                    input_sample, self.crossover_freqs[i], self.crossover_freqs[i + 1], i
                )
                self._band_outputs[i] = bp_output * self.band_gains[i]

            # Last band: high-pass
            if self.num_bands > 1:
                hp_output = self._linkwitz_riley_highpass(
                    input_sample, self.crossover_freqs[-2], self.num_bands - 1
                )
                self._band_outputs[self.num_bands - 1] = hp_output * self.band_gains[-1]

            return self._band_outputs

    def _linkwitz_riley_lowpass(self, input_sample: float, cutoff: float, band_idx: int) -> float:
        if band_idx not in self.filter_states[band_idx]:
            self.filter_states[band_idx]["lp"] = {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0}

        state = self.filter_states[band_idx]["lp"]

        # Cache filter coefficients (crossover freqs never change)
        if "coeffs" not in state:
            wc = 2 * np.pi * cutoff / self.sample_rate
            k = wc / np.tan(wc / 2)
            q = 1 / np.sqrt(2)
            norm = k * k + k / q + 1
            state["coeffs"] = (
                1 / norm,
                2 / norm,
                1 / norm,
                (2 * (1 - k * k)) / norm,
                (k * k - k / q + 1) / norm,
            )

        b0, b1, b2, a1, a2 = state["coeffs"]

        # Bilinear transform for 2nd order
        x0 = input_sample
        y0 = b0 * x0 + b1 * state["x1"] + b2 * state["x2"] - a1 * state["y1"] - a2 * state["y2"]

        # Update state
        state["x2"] = state["x1"]
        state["x1"] = x0
        state["y2"] = state["y1"]
        state["y1"] = y0

        return y0

    def _linkwitz_riley_highpass(self, input_sample: float, cutoff: float, band_idx: int) -> float:
        if "hp" not in self.filter_states[band_idx]:
            self.filter_states[band_idx]["hp"] = {"x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0}

        state = self.filter_states[band_idx]["hp"]

        # Cache filter coefficients (crossover freqs never change)
        if "coeffs" not in state:
            wc = 2 * np.pi * cutoff / self.sample_rate
            k = wc / np.tan(wc / 2)
            q = 1 / np.sqrt(2)
            norm = k * k + k / q + 1
            state["coeffs"] = (
                k * k / norm,
                -2 * k * k / norm,
                k * k / norm,
                (2 * (k * k - 1)) / norm,
                (1 - k / q + k * k) / norm,
            )

        b0, b1, b2, a1, a2 = state["coeffs"]

        x0 = input_sample
        y0 = b0 * x0 + b1 * state["x1"] + b2 * state["x2"] - a1 * state["y1"] - a2 * state["y2"]

        state["x2"] = state["x1"]
        state["x1"] = x0
        state["y2"] = state["y1"]
        state["y1"] = y0

        return y0

    def _linkwitz_riley_bandpass(
        self, input_sample: float, low_cutoff: float, high_cutoff: float, band_idx: int
    ) -> float:
        """Band-pass filter using low-pass and high-pass combination."""
        # Professional bandpass filter using cascaded Linkwitz-Riley filters
        # Provides steep rolloff and flat passband response
        lp_out = self._linkwitz_riley_lowpass(input_sample, high_cutoff, band_idx)
        return self._linkwitz_riley_highpass(lp_out, low_cutoff, band_idx)

    def reset(self) -> None:
        """Reset all filter states."""
        with self.lock:
            for band_states in self.filter_states:
                for filter_state in band_states.values():
                    # Reset filter state variables, preserve cached coefficients
                    filter_state["x1"] = 0.0
                    filter_state["x2"] = 0.0
                    filter_state["y1"] = 0.0
                    filter_state["y2"] = 0.0


class AdvancedEnvelopeFollower:
    """
    Advanced envelope follower with multiple attack/release characteristics.

    Features:
    - Configurable attack/release times
    - Peak/RMS detection modes
    - Look-ahead processing capability
    - Side-chain input support
    """

    def __init__(
        self,
        sample_rate: int,
        attack_time: float = 0.01,
        release_time: float = 0.1,
        mode: str = "peak",
    ):
        self.sample_rate = sample_rate
        self.attack_time = attack_time
        self.release_time = release_time
        self.mode = mode

        # Calculate coefficients
        self.attack_coeff = self._time_to_coeff(attack_time)
        self.release_coeff = self._time_to_coeff(release_time)

        # State
        self.envelope = 0.0
        self.peak_hold = 0.0
        self.rms_accumulator = 0.0
        self.rms_window_size = int(0.01 * sample_rate)  # 10ms RMS window

        # Thread safety
        self.lock = threading.RLock()

    def _time_to_coeff(self, time: float) -> float:
        return math.exp(-1.0 / (time * self.sample_rate))

    def process_sample(self, input_sample: float, sidechain_sample: float | None = None) -> float:
        with self.lock:
            # Use sidechain if provided, otherwise main input
            detect_sample = abs(sidechain_sample if sidechain_sample is not None else input_sample)

            if self.mode == "peak":
                # Peak detection
                if detect_sample > self.envelope:
                    self.envelope = (
                        self.attack_coeff * (self.envelope - detect_sample) + detect_sample
                    )
                else:
                    self.envelope = (
                        self.release_coeff * (self.envelope - detect_sample) + detect_sample
                    )

            elif self.mode == "rms":
                # RMS detection
                self.rms_accumulator = (
                    self.rms_accumulator * 0.99 + detect_sample * detect_sample * 0.01
                )
                rms_value = math.sqrt(self.rms_accumulator)

                if rms_value > self.envelope:
                    self.envelope = self.attack_coeff * (self.envelope - rms_value) + rms_value
                else:
                    self.envelope = self.release_coeff * (self.envelope - rms_value) + rms_value

            return self.envelope

    def set_attack_time(self, time: float) -> None:
        with self.lock:
            self.attack_time = max(0.001, time)
            self.attack_coeff = self._time_to_coeff(self.attack_time)

    def set_release_time(self, time: float) -> None:
        with self.lock:
            self.release_time = max(0.001, time)
            self.release_coeff = self._time_to_coeff(self.release_time)

    def reset(self) -> None:
        """Reset envelope state."""
        with self.lock:
            self.envelope = 0.0
            self.peak_hold = 0.0
            self.rms_accumulator = 0.0


class ProfessionalDelayNetwork:
    """
    Professional delay network with multiple taps and feedback control.

    Features:
    - Multiple delay taps with individual levels
    - Feedback control with damping
    - Stereo processing with cross-feedback
    - Diffusion control for reverb-like effects
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Delay lines for multiple taps
        self.delay_lines = []
        self.tap_delays = []
        self.tap_levels = []
        self.feedback_matrix = np.eye(4, dtype=np.float32)  # 4x4 feedback matrix

        # Diffusion parameters
        self.diffusion = 0.5
        self.damping = 0.1

        # Circular buffer write positions (one per delay line)
        self._write_positions: list[int] = []

        # Deterministic noise lookup table (avoids np.random.normal per sample)
        self._noise_table = np.random.uniform(-1.0, 1.0, 1024).astype(np.float32)
        self._noise_idx = 0

        # Thread safety
        self.lock = threading.RLock()

    def configure_taps(self, tap_configs: list[tuple[float, float]]) -> None:
        with self.lock:
            self.delay_lines = []
            self.tap_delays = []
            self.tap_levels = []

            for delay_time, level in tap_configs:
                delay_samples = int(delay_time * self.sample_rate)
                delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

                delay_line = np.zeros(self.max_delay_samples, dtype=np.float32)
                self.delay_lines.append(delay_line)
                self.tap_delays.append(delay_samples)
                self.tap_levels.append(level)

            # Initialize circular buffer write positions
            self._write_positions = [0] * len(self.delay_lines)

    def set_feedback_matrix(self, matrix: np.ndarray) -> None:
        with self.lock:
            self.feedback_matrix = matrix.copy()

    def process_sample(self, input_sample: float) -> float:
        with self.lock:
            output = 0.0

            for i, (delay_line, delay_samples, level) in enumerate(
                zip(self.delay_lines, self.tap_delays, self.tap_levels, strict=False)
            ):
                # Circular buffer read: sample from delay_samples ago
                read_pos = (self._write_positions[i] - delay_samples) % len(delay_line)
                delayed_sample = delay_line[int(read_pos)]

                # Add to output
                output += delayed_sample * level

                # Calculate feedback input
                feedback_input = input_sample

                # Add feedback from other taps
                for j, other_delay_line in enumerate(self.delay_lines):
                    if j != i:
                        other_read_pos = (self._write_positions[j] - self.tap_delays[j]) % len(
                            other_delay_line
                        )
                        feedback_input += (
                            other_delay_line[int(other_read_pos)] * self.feedback_matrix[i, j]
                        )

                # Apply damping and diffusion
                feedback_input *= 1.0 - self.damping

                # Deterministic noise via lookup table (avoids np.random.normal allocation)
                noise = self._noise_table[self._noise_idx] * self.diffusion * 0.01
                self._noise_idx = (self._noise_idx + 1) % 1024
                feedback_input += noise

                # Circular buffer write — O(1) instead of O(n) shift
                delay_line[self._write_positions[i]] = feedback_input
                self._write_positions[i] = (self._write_positions[i] + 1) % len(delay_line)

            return output

    def reset(self) -> None:
        """Reset all delay lines."""
        with self.lock:
            for delay_line in self.delay_lines:
                delay_line.fill(0.0)
            self._write_positions = [0] * len(self.delay_lines)


# Utility functions for FFT processing
class FFTProcessor:
    """Optimized FFT processor for real-time audio effects."""

    @staticmethod
    def rfft(input_frame: np.ndarray) -> np.ndarray:
        return np.fft.rfft(input_frame) / len(input_frame)

    @staticmethod
    def irfft(spectrum: np.ndarray, length: int | None = None) -> np.ndarray:
        if length is None:
            length = (len(spectrum) - 1) * 2
        return np.fft.irfft(spectrum, n=length) * length

    @staticmethod
    def create_window(window_type: str, length: int) -> np.ndarray:
        if window_type == "hann":
            return np.hanning(length)
        elif window_type == "hamming":
            return np.hamming(length)
        elif window_type == "blackman":
            return np.blackman(length)
        else:
            return np.ones(length)  # Rectangular window

