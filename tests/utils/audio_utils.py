"""
Audio Testing Utilities for XG Synthesizer Test Suite

Provides helper functions for audio analysis, comparison, and test signal generation.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple


def generate_test_frequency(
    freq: float, duration: float, sample_rate: int = 44100, amplitude: float = 1.0
) -> np.ndarray:
    """
    Generate a test sine wave at specified frequency.

    Args:
        freq: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Peak amplitude (0.0 to 1.0)

    Returns:
        Mono audio buffer as float32 numpy array
    """
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, dtype=np.float32)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def generate_white_noise(duration: float, sample_rate: int = 44100, amplitude: float = 1.0) -> np.ndarray:
    """
    Generate white noise test signal.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Peak amplitude (0.0 to 1.0)

    Returns:
        Mono audio buffer as float32 numpy array
    """
    num_samples = int(sample_rate * duration)
    noise = np.random.randn(num_samples).astype(np.float32)
    # Normalize to [-amplitude, amplitude]
    max_val = np.max(np.abs(noise))
    if max_val > 0:
        noise = noise / max_val * amplitude
    return noise


def calculate_rms(buffer: np.ndarray) -> float:
    """
    Calculate RMS (Root Mean Square) level of audio buffer.

    Args:
        buffer: Audio buffer (mono or stereo interleaved)

    Returns:
        RMS level as float
    """
    return float(np.sqrt(np.mean(buffer ** 2)))


def calculate_peak(buffer: np.ndarray) -> float:
    """
    Calculate peak level of audio buffer.

    Args:
        buffer: Audio buffer (mono or stereo interleaved)

    Returns:
        Peak level as float
    """
    return float(np.max(np.abs(buffer)))


def detect_clipping(buffer: np.ndarray, threshold: float = 0.99) -> bool:
    """
    Detect clipping in audio buffer.

    Args:
        buffer: Audio buffer (mono or stereo interleaved)
        threshold: Clipping threshold (default 0.99)

    Returns:
        True if clipping detected, False otherwise
    """
    return bool(np.any(np.abs(buffer) > threshold))


def compare_audio_buffers(
    buffer1: np.ndarray, buffer2: np.ndarray, tolerance: float = 0.01
) -> Tuple[bool, float]:
    """
    Compare two audio buffers with tolerance.

    Args:
        buffer1: First audio buffer
        buffer2: Second audio buffer
        tolerance: Maximum allowed difference

    Returns:
        Tuple of (buffers_match, max_difference)
    """
    if buffer1.shape != buffer2.shape:
        return False, float('inf')

    max_diff = float(np.max(np.abs(buffer1 - buffer2)))
    return max_diff <= tolerance, max_diff


def apply_window(buffer: np.ndarray, window_type: str = "hann") -> np.ndarray:
    """
    Apply window function to audio buffer.

    Args:
        buffer: Audio buffer
        window_type: Window type ('hann', 'hamming', 'blackman')

    Returns:
        Windowed audio buffer
    """
    n = len(buffer)

    if window_type == "hann":
        window = np.hanning(n)
    elif window_type == "hamming":
        window = np.hamming(n)
    elif window_type == "blackman":
        window = np.blackman(n)
    else:
        window = np.ones(n)

    return buffer * window


def calculate_snr(signal: np.ndarray, noise: np.ndarray) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) in dB.

    Args:
        signal: Signal buffer
        noise: Noise buffer

    Returns:
        SNR in dB
    """
    signal_power = np.mean(signal ** 2)
    noise_power = np.mean(noise ** 2)

    if noise_power == 0:
        return float('inf')

    snr = 10 * np.log10(signal_power / noise_power)
    return float(snr)


def calculate_thd(signal: np.ndarray, sample_rate: int = 44100, fundamental_freq: float = 440.0) -> float:
    """
    Calculate Total Harmonic Distortion (THD) in dB.

    Args:
        signal: Audio buffer containing sine wave
        sample_rate: Sample rate in Hz
        fundamental_freq: Expected fundamental frequency in Hz

    Returns:
        THD+N in dB (negative value, lower is better)
    """
    # Apply window to reduce spectral leakage
    windowed = apply_window(signal, "hann")

    # Compute FFT
    fft = np.fft.rfft(windowed)
    magnitude = np.abs(fft)

    # Find fundamental frequency bin
    freqs = np.fft.rfftfreq(len(windowed), 1.0 / sample_rate)
    fundamental_bin = np.argmin(np.abs(freqs - fundamental_freq))

    # Calculate fundamental power
    fundamental_power = magnitude[fundamental_bin] ** 2

    # Calculate total power (excluding DC)
    total_power = np.sum(magnitude[1:] ** 2)

    # Calculate harmonic power (sum of harmonics)
    harmonic_power = 0.0
    for harmonic in range(2, 11):  # Up to 10th harmonic
        harmonic_freq = fundamental_freq * harmonic
        if harmonic_freq < sample_rate / 2:
            harmonic_bin = np.argmin(np.abs(freqs - harmonic_freq))
            harmonic_power += magnitude[harmonic_bin] ** 2

    # Calculate THD
    if fundamental_power == 0:
        return 0.0

    thd = np.sqrt(harmonic_power / fundamental_power)
    thd_db = 20 * np.log10(thd) if thd > 0 else float('-inf')

    return float(thd_db)


def stereo_to_mono(stereo_buffer: np.ndarray) -> np.ndarray:
    """
    Convert stereo interleaved buffer to mono.

    Args:
        stereo_buffer: Stereo buffer (samples * 2)

    Returns:
        Mono buffer (samples)
    """
    if len(stereo_buffer) % 2 != 0:
        raise ValueError("Stereo buffer length must be even")

    left = stereo_buffer[::2]
    right = stereo_buffer[1::2]
    return (left + right) * 0.5


def mono_to_stereo(mono_buffer: np.ndarray) -> np.ndarray:
    """
    Convert mono buffer to stereo interleaved.

    Args:
        mono_buffer: Mono buffer (samples)

    Returns:
        Stereo buffer (samples * 2)
    """
    stereo = np.zeros(len(mono_buffer) * 2, dtype=mono_buffer.dtype)
    stereo[::2] = mono_buffer
    stereo[1::2] = mono_buffer
    return stereo


def pan_stereo(stereo_buffer: np.ndarray, pan: float) -> np.ndarray:
    """
    Apply panning to stereo buffer using constant power law.

    Args:
        stereo_buffer: Stereo interleaved buffer
        pan: Pan position (-1.0 = full left, 0.0 = center, 1.0 = full right)

    Returns:
        Panned stereo buffer
    """
    # Constant power panning using cos/sin law
    # θ = (pan + 1) * π/4 maps pan from [-1, 1] to [0, π/2]
    theta = (pan + 1) * np.pi / 4
    left_gain = np.cos(theta)
    right_gain = np.sin(theta)

    result = stereo_buffer.copy()
    result[::2] *= left_gain
    result[1::2] *= right_gain
    return result


def apply_volume(buffer: np.ndarray, volume: float) -> np.ndarray:
    """
    Apply volume scaling to audio buffer.

    Args:
        buffer: Audio buffer
        volume: Volume factor (0.0 = silence, 1.0 = unity, >1.0 = boost)

    Returns:
        Scaled audio buffer
    """
    return buffer * volume


def fade_in(buffer: np.ndarray, fade_samples: int) -> np.ndarray:
    """
    Apply fade-in to audio buffer.

    Args:
        buffer: Audio buffer
        fade_samples: Number of samples for fade

    Returns:
        Buffer with fade-in applied
    """
    result = buffer.copy()
    fade_samples = min(fade_samples, len(buffer))
    fade_curve = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    result[:fade_samples] *= fade_curve
    return result


def fade_out(buffer: np.ndarray, fade_samples: int) -> np.ndarray:
    """
    Apply fade-out to audio buffer.

    Args:
        buffer: Audio buffer
        fade_samples: Number of samples for fade

    Returns:
        Buffer with fade-out applied
    """
    result = buffer.copy()
    fade_samples = min(fade_samples, len(buffer))
    fade_curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    result[-fade_samples:] *= fade_curve
    return result


def concatenate_buffers(buffers: list[np.ndarray]) -> np.ndarray:
    """
    Concatenate multiple audio buffers.

    Args:
        buffers: List of audio buffers

    Returns:
        Concatenated audio buffer
    """
    return np.concatenate(buffers)


def split_stereo(stereo_buffer: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Split stereo interleaved buffer into separate left and right channels.

    Args:
        stereo_buffer: Stereo interleaved buffer (samples * 2)

    Returns:
        Tuple of (left_channel, right_channel)
    """
    if len(stereo_buffer) % 2 != 0:
        raise ValueError("Stereo buffer length must be even")

    left = stereo_buffer[::2].copy()
    right = stereo_buffer[1::2].copy()
    return left, right


def merge_stereo(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """
    Merge separate left and right channels into stereo interleaved buffer.

    Args:
        left: Left channel buffer
        right: Right channel buffer

    Returns:
        Stereo interleaved buffer
    """
    if len(left) != len(right):
        raise ValueError("Left and right channels must have same length")

    stereo = np.zeros(len(left) * 2, dtype=left.dtype)
    stereo[::2] = left
    stereo[1::2] = right
    return stereo