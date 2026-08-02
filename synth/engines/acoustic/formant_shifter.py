"""Formant-preserving pitch shift via phase vocoder.

Prevents the "chipmunk effect" when pitch-shifting instruments:
harmonic content shifts, but formant resonances stay at their
original frequencies. Critical for ensemble detune and harmonizer.

Implementation: STFT → phase vocoder for pitch shift → spectral envelope
separation → envelope reapplication → ISTFT.
"""

from __future__ import annotations

import numpy as np


def formant_preserving_shift(
    buf: np.ndarray,
    ratio: float,
    fft_size: int = 1024,
    hop_size: int = 256,
) -> np.ndarray:
    """Pitch shift with formant preservation.

    Args:
        buf: Stereo (n, 2) float32 buffer. Modified in-place.
        ratio: Pitch ratio (>1=shift up, <1=shift down).
        fft_size: FFT window size.
        hop_size: Hop size between frames.

    Returns:
        Modified buffer (in-place).
    """
    if abs(ratio - 1.0) < 0.001:
        return buf  # No shift needed

    window = np.hanning(fft_size).astype(np.float32)

    for ch in (0, 1):
        signal = buf[:, ch]
        n = len(signal)

        # 1. Extract spectral envelope from original signal
        envelope = _extract_spectral_envelope(signal, fft_size, hop_size, window)

        # 2. Phase vocoder pitch shift
        shifted = _phase_vocoder_shift(signal, ratio, fft_size, hop_size, window)

        # 3. Extract envelope from shifted signal
        shifted_envelope = _extract_spectral_envelope(
            shifted[:n], fft_size, hop_size, window
        )

        # 4. Replace shifted envelope with original (formant preservation)
        if len(shifted_envelope) > 0 and len(envelope) > 0:
            min_len = min(len(envelope), len(shifted_envelope))
            corrected = _apply_envelope(
                shifted[:n], envelope[:min_len], shifted_envelope[:min_len],
                fft_size, hop_size, window
            )
            buf[:len(corrected), ch] = corrected
        else:
            buf[:min(n, len(shifted)), ch] = shifted[:min(n, len(shifted))]

    return buf


def _extract_spectral_envelope(
    signal: np.ndarray, fft_size: int, hop_size: int, window: np.ndarray
) -> np.ndarray:
    """Extract slow-varying spectral envelope via low-resolution FFT.

    Uses larger-frame FFT with heavy window overlap to capture
    only the formant structure, not individual harmonics.
    """
    n_frames = (len(signal) - fft_size) // hop_size + 1
    if n_frames < 1:
        return np.array([])

    envelope_bins = fft_size // 2 + 1
    envelope = np.zeros((n_frames, envelope_bins), dtype=np.float32)

    for i in range(n_frames):
        start = i * hop_size
        frame = signal[start:start + fft_size] * window
        spec = np.abs(np.fft.rfft(frame))

        # Lowpass the spectrum to get envelope (formants are slow-varying)
        # Simple moving average over frequency bins
        smoothed = np.zeros_like(spec)
        win = 5
        for j in range(win, len(spec) - win):
            smoothed[j] = np.mean(spec[j - win:j + win + 1])
        # Copy edges
        smoothed[:win] = spec[:win]
        smoothed[-win:] = spec[-win:]

        if np.max(smoothed) > 1e-6:
            smoothed /= np.max(smoothed)
        envelope[i] = smoothed.astype(np.float32)

    return envelope


def _phase_vocoder_shift(
    signal: np.ndarray, ratio: float, fft_size: int, hop_size: int, window: np.ndarray
) -> np.ndarray:
    """Phase vocoder pitch shift.

    1. STFT with analysis hop
    2. Adjust phase advance per bin by ratio
    3. ISTFT with synthesis hop = analysis_hop / ratio
    """
    analysis_hop = hop_size
    synthesis_hop = int(analysis_hop / ratio)
    if synthesis_hop < 1:
        synthesis_hop = 1

    n_frames = (len(signal) - fft_size) // analysis_hop + 1
    if n_frames < 2:
        return signal

    out_len = synthesis_hop * n_frames + fft_size
    output = np.zeros(out_len, dtype=np.float32)
    output_weight = np.zeros(out_len, dtype=np.float32)

    prev_phase = np.zeros(fft_size // 2 + 1, dtype=np.float64)

    for i in range(n_frames):
        # Analysis
        start = i * analysis_hop
        frame = signal[start:start + fft_size] * window
        spec = np.fft.rfft(frame).astype(np.complex128)

        # Phase adjustment per bin
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Expected phase advance for perfect harmonic
        omega = 2.0 * np.pi * np.arange(len(phase)) / fft_size * analysis_hop
        expected = prev_phase + omega
        delta_phase = phase - prev_phase - omega
        # Wrap to [-pi, pi]
        delta_phase = np.arctan2(np.sin(delta_phase), np.cos(delta_phase))
        prev_phase = phase

        # Synthesis: adjust phase for ratio
        synthesis_phase = prev_phase + (omega + delta_phase) * ratio
        synthesis_spec = mag * np.exp(1j * synthesis_phase)

        # Synthesis with window
        syn_frame = np.fft.irfft(synthesis_spec.astype(np.complex64), n=fft_size)
        syn_frame *= window

        out_start = i * synthesis_hop
        output[out_start:out_start + fft_size] += syn_frame
        output_weight[out_start:out_start + fft_size] += window ** 2

    # Normalize by window overlap
    output_weight = np.maximum(output_weight, 1e-6)
    output /= output_weight
    return output.astype(np.float32)


def _apply_envelope(
    signal: np.ndarray,
    original_env: np.ndarray,
    shifted_env: np.ndarray,
    fft_size: int,
    hop_size: int,
    window: np.ndarray,
) -> np.ndarray:
    """Apply original spectral envelope to pitch-shifted signal.

    For each frame: FFT → divide by shifted envelope → multiply by original envelope → IFFT.
    """
    n_frames = min(len(original_env), (len(signal) - fft_size) // hop_size + 1)
    if n_frames < 1:
        return signal

    output = np.zeros(len(signal), dtype=np.float32)
    output_weight = np.zeros(len(signal), dtype=np.float32)

    for i in range(n_frames):
        start = i * hop_size
        frame = signal[start:start + fft_size] * window

        spec = np.fft.rfft(frame).astype(np.complex128)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Divide by shifted envelope, multiply by original
        orig = original_env[i][:len(mag)] + 1e-6
        shifted = shifted_env[i][:len(mag)] + 1e-6

        correction = np.minimum(orig / shifted, 5.0)  # Limit gain to 5x
        mag *= correction

        corrected_spec = mag * np.exp(1j * phase)
        syn_frame = np.fft.irfft(corrected_spec.astype(np.complex64), n=fft_size)
        syn_frame *= window

        output[start:start + fft_size] += syn_frame
        output_weight[start:start + fft_size] += window ** 2

    output_weight = np.maximum(output_weight, 1e-6)
    output /= output_weight
    return output.astype(np.float32)
