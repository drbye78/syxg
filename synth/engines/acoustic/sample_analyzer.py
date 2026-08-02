"""Sample segmentation and modal analysis for behavioral synthesis.

Extracts attack/sustain/release boundaries and modal parameters from
SF2 sample data at load time. Results are cached per note for zero
lookup cost during audio rendering.

Phase-locked crossfade: modal oscillators are initialized with the
PCM signal's phase at the crossfade boundary for seamless transition.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class SampleSegments:
    """Attack, sustain, and release regions of a segmented sample."""

    attack: np.ndarray          # PCM attack transient
    sustain: np.ndarray         # Quasi-periodic sustain portion
    release: np.ndarray         # Release tail
    attack_length: int          # Samples
    crossfade_length: int       # Recommended PCM→Model crossfade duration


@dataclass(slots=True)
class ModalParameter:
    """A single modal resonance parameter."""

    frequency: float            # Hz
    amplitude: float            # Normalized 0-1
    decay_rate: float           # Per-second damping
    phase: float = 0.0          # Initial phase (set at crossfade boundary)


class SampleSegmenter:
    """Detect attack/sustain/release boundaries in sample data.

    Uses RMS energy envelope + adaptive threshold detection.
    Falls back to fixed-duration segmentation if auto-detection fails.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._fixed_attack_ms = 100   # Fallback attack duration
        self._fixed_release_ms = 200  # Fallback release duration

    def segment(self, sample: np.ndarray, note: int = 60) -> SampleSegments:
        """Segment a sample into attack, sustain, and release regions.

        Args:
            sample: Mono float32 sample data.
            note: MIDI note number (for instrument-specific thresholds).

        Returns:
            SampleSegments with boundary positions.
        """
        if len(sample) < 1024:
            return self._fixed_segmentation(sample)

        try:
            return self._auto_segment(sample)
        except Exception:
            return self._fixed_segmentation(sample)

    def _auto_segment(self, sample: np.ndarray) -> SampleSegments:
        """Auto-detect boundaries using RMS envelope."""
        # Compute RMS envelope with 256-sample window
        n = len(sample)
        win = 256
        if n < win * 4:
            return self._fixed_segmentation(sample)

        rms = np.zeros(n // win, dtype=np.float32)
        for i in range(len(rms)):
            seg = sample[i * win : min((i + 1) * win, n)]
            rms[i] = np.sqrt(np.mean(seg ** 2))

        if len(rms) < 4:
            return self._fixed_segmentation(sample)

        # Find attack end: first local minimum after peak
        peak_idx = int(np.argmax(rms))
        attack_end_win = peak_idx + 1
        for i in range(peak_idx + 1, len(rms) - 1):
            if rms[i] < rms[i - 1] * 0.8:
                attack_end_win = i
                break

        # Find release start: envelope drops below 30% of sustain average
        sustain_start = min(attack_end_win + 1, len(rms) - 2)
        sustain_rms = rms[sustain_start : max(sustain_start + 4, len(rms) // 2)]
        if len(sustain_rms) < 2:
            return self._fixed_segmentation(sample)
        sustain_avg = float(np.mean(sustain_rms))
        if sustain_avg <= 0.0:
            return self._fixed_segmentation(sample)

        release_start_win = len(rms)
        for i in range(sustain_start, len(rms) - 1):
            if rms[i] < sustain_avg * 0.3:
                release_start_win = i
                break

        attack_end = min(attack_end_win * win, n // 2)
        release_start = min(release_start_win * win, n - win * 2)
        if release_start <= attack_end + win:
            release_start = max(n - self._fixed_release_ms * self.sample_rate // 1000, attack_end + win)

        crossfade_len = int(min(0.030 * self.sample_rate, (release_start - attack_end) // 4))

        return SampleSegments(
            attack=sample[:attack_end].copy(),
            sustain=sample[attack_end:release_start].copy(),
            release=sample[release_start:].copy(),
            attack_length=attack_end,
            crossfade_length=crossfade_len,
        )

    def _fixed_segmentation(self, sample: np.ndarray) -> SampleSegments:
        """Fixed-duration fallback segmentation."""
        n = len(sample)
        attack_end = int(self._fixed_attack_ms * self.sample_rate / 1000)
        release_start = max(n - int(self._fixed_release_ms * self.sample_rate / 1000), attack_end + 1024)
        attack_end = min(attack_end, n // 3)
        release_start = max(release_start, n - n // 4)

        return SampleSegments(
            attack=sample[:attack_end].copy(),
            sustain=sample[attack_end:release_start].copy(),
            release=sample[release_start:].copy(),
            attack_length=attack_end,
            crossfade_length=int(0.030 * self.sample_rate),
        )


class ModalAnalyzer:
    """Extract modal parameters from sustain portion of a sample.

    Uses windowed FFT peak detection to identify dominant harmonic
    frequencies, amplitudes, and decay rates.
    """

    def __init__(self, sample_rate: int = 44100, num_modes: int = 12):
        self.sample_rate = sample_rate
        self.num_modes = num_modes

    def analyze(self, sustain: np.ndarray, note: int = 60) -> list[ModalParameter]:
        """Extract modal parameters from sustain data.

        Args:
            sustain: Quasi-periodic sustain portion of sample.
            note: MIDI note for fundamental frequency hint.

        Returns:
            List of ModalParameter objects sorted by frequency.
        """
        if len(sustain) < 512:
            return self._synthesize_modes(note)

        try:
            return self._fft_analyze(sustain, note)
        except Exception:
            return self._synthesize_modes(note)

    def _fft_analyze(self, sustain: np.ndarray, note: int) -> list[ModalParameter]:
        """FFT-based modal extraction."""
        n = min(len(sustain), 8192)
        windowed = sustain[-n:] * np.hanning(n)
        spectrum = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(n, 1.0 / self.sample_rate)

        # Find peaks: local maxima above noise floor
        noise_floor = np.mean(spectrum) * 3.0
        peaks = []
        for i in range(2, len(spectrum) - 2):
            if (spectrum[i] > noise_floor and
                spectrum[i] > spectrum[i - 1] and
                spectrum[i] > spectrum[i + 1] and
                spectrum[i] > spectrum[i - 2] and
                spectrum[i] > spectrum[i + 2]):
                peaks.append((freqs[i], spectrum[i], i))

        # Sort by amplitude, take top N modes
        peaks.sort(key=lambda x: -x[1])
        peaks = peaks[:self.num_modes]

        # Normalize amplitudes
        if peaks:
            max_amp = peaks[0][1]
            peaks = [(f, a / max_amp, i) for f, a, i in peaks]

        # Estimate decay rate from amplitude envelope
        decay_rate = self._estimate_decay(sustain)

        modes = []
        for freq, amp, _ in peaks:
            if freq > 20.0 and freq < self.sample_rate * 0.45:
                modes.append(ModalParameter(
                    frequency=float(freq),
                    amplitude=float(amp),
                    decay_rate=decay_rate * (1.0 + float(freq) / 5000.0),
                ))

        if not modes:
            return self._synthesize_modes(note)
        return sorted(modes, key=lambda m: m.frequency)

    def _estimate_decay(self, sustain: np.ndarray) -> float:
        """Estimate amplitude decay rate from RMS envelope."""
        win = 256
        n_windows = len(sustain) // win
        if n_windows < 4:
            return 2.0  # Default: moderate decay

        rms_env = np.zeros(n_windows, dtype=np.float32)
        for i in range(n_windows):
            seg = sustain[i * win : (i + 1) * win]
            rms_env[i] = float(np.sqrt(np.mean(seg ** 2)))

        if rms_env[0] <= 0.0:
            return 2.0

        # Linear fit on log envelope
        log_env = np.log(np.maximum(rms_env, 1e-6))
        if len(log_env) < 2:
            return 2.0
        slope = (log_env[-1] - log_env[0]) / max(n_windows - 1, 1)
        return max(0.5, -slope * self.sample_rate / win)

    def _synthesize_modes(self, note: int) -> list[ModalParameter]:
        """Synthesize modal parameters from note number (fallback)."""
        fundamental = 440.0 * (2.0 ** ((note - 69) / 12.0))
        modes = []
        for i in range(1, min(self.num_modes + 1, 9)):
            freq = fundamental * i
            # Higher partials decay faster, lower amplitude
            amp = 1.0 / i ** 1.2
            decay = 2.0 * (1.0 + i / 4.0)
            modes.append(ModalParameter(
                frequency=freq,
                amplitude=amp,
                decay_rate=decay,
            ))
        return modes


class NoteModalCache:
    """Modal parameters indexed by MIDI note number.

    Pre-computed during SF2 loading. Interpolates between nearest
    cached notes for unloaded pitches.
    """

    def __init__(self):
        self._cache: dict[int, list[ModalParameter]] = {}

    def store(self, note: int, modes: list[ModalParameter]) -> None:
        self._cache[note] = modes

    def get(self, note: int) -> list[ModalParameter] | None:
        """Return pre-computed modal params. Interpolates if not cached."""
        if note in self._cache:
            return self._cache[note]

        if not self._cache:
            return None

        # Find nearest cached notes
        notes = sorted(self._cache.keys())
        below = [n for n in notes if n <= note]
        above = [n for n in notes if n >= note]

        if below and above:
            lo, hi = max(below), min(above)
            return self._interpolate(lo, hi, note)
        elif below:
            return self._cache[max(below)]
        elif above:
            return self._cache[min(above)]
        return None

    def _interpolate(
        self, lo_note: int, hi_note: int, target: int
    ) -> list[ModalParameter]:
        """Linear interpolation between two cached note profiles."""
        lo_modes = self._cache[lo_note]
        hi_modes = self._cache[hi_note]
        if not lo_modes or not hi_modes:
            return lo_modes or hi_modes or []

        t = (target - lo_note) / max(hi_note - lo_note, 1)
        result = []
        for i in range(min(len(lo_modes), len(hi_modes))):
            freq = lo_modes[i].frequency * (1.0 - t) + hi_modes[i].frequency * t
            amp = lo_modes[i].amplitude * (1.0 - t) + hi_modes[i].amplitude * t
            decay = lo_modes[i].decay_rate * (1.0 - t) + hi_modes[i].decay_rate * t
            result.append(ModalParameter(frequency=freq, amplitude=amp, decay_rate=decay))
        return result

    def preload_from_samples(
        self, samples: dict[int, np.ndarray], sr: int, num_modes: int = 12
    ) -> int:
        """Pre-compute modal parameters for all samples at load time.

        Called during SF2 loading. Analyzes each sample's sustain portion
        and caches the modal parameters by note number. This eliminates
        all analysis from the audio thread.

        Args:
            samples: dict of {note_number: sample_data}
            sr: Sample rate
            num_modes: Number of modal frequencies to extract

        Returns:
            Number of notes successfully cached.
        """
        segmenter = SampleSegmenter(sr)
        analyzer = ModalAnalyzer(sr, num_modes)
        count = 0
        for note, sample in samples.items():
            try:
                seg = segmenter.segment(sample, note)
                modes = analyzer.analyze(seg.sustain, note)
                if modes:
                    self.store(note, modes)
                    count += 1
            except Exception:
                pass
        return count
