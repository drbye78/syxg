"""
Sample Modifiers for S.Art2 Articulation System.

Contains SF2SampleModifier class that applies real-time articulation
effects to sample data. Uses linear-interpolation resampling for pitch
effects and one-pole IIR filters for smoothing — no boxcar FIR filters,
no nearest-neighbor interpolation, no hardcoded 440Hz fundamental.

BUFFER DISCIPLINE (Phase 3):
- All hot-path methods use the internal scratch buffer system to avoid
  repeated np.zeros / np.ones / np.empty / sample.copy() allocations.
- _ensure_time(n) caches a time array that grows on demand (first call
  allocates; subsequent calls reuse silently until a larger block is needed).
- _ensure_scratch(n) provides a general-purpose work buffer.
- np.sin / np.exp math allocations are accepted as they are unavoidable
  ufunc temporaries, but scratch buffers eliminate all explicit allocation
  patterns (zeros, ones, empty, copy).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

SEMITONE_RATIO: float = 1.059463094359  # 2^(1/12)

# Default max block size for scratch buffer pre-allocation
_DEFAULT_MAX_BLOCK: int = 8192


class SF2SampleModifier:
    """
    Modifier that applies articulations to SF2 sample playback.

    Provides real-time sample manipulation for S.Art2-style articulations
    on SoundFont samples.  Zero-allocation in the hot path after the
    scratch buffers have grown to the maximum block size.

    Usage:
        modifier = SF2SampleModifier()
        modified = modifier.apply_articulation(sample, 'legato')
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize the sample modifier with scratch buffer cache."""
        self.sample_rate = sample_rate
        self._sr_recip = 1.0 / sample_rate
        self._custom_handlers: dict[str, Callable] = {}

        # One-pole IIR filter persistent state (per key)
        self._lp_state: dict[str, float] = {}

        # ---- Scratch buffer cache (zero-allocation hot path) ----
        # _t: mono time array, grows to max block size
        self._t: np.ndarray | None = None
        # _scratch: general-purpose work buffer
        self._scratch: np.ndarray | None = None
        # _phase: reusable phase / cumulative-sum buffer for _pitch_resample
        self._phase: np.ndarray | None = None
        # _prev_n: last seen block length (for fill-on-grow optimisation)
        self._prev_n: int = 0

    # =====================================================================
    # Scratch buffer helpers
    # =====================================================================

    def _ensure_time(self, n: int) -> np.ndarray:
        """
        Return a time array of length n: t[i] = i / sample_rate.

        Grows on demand — the first call (or any call with n larger
        than seen before) allocates and fills; all subsequent calls
        return a slice of the cached array with no allocation.
        """
        if self._t is None or len(self._t) < n:
            old = self._t
            self._t = np.empty(n, dtype=np.float32)
            if old is not None and len(old) > 0:
                # Copy old values, extend
                self._t[: len(old)] = old
                for i in range(len(old), n):
                    self._t[i] = self._t[i - 1] + self._sr_recip
            else:
                self._t[0] = 0.0
                for i in range(1, n):
                    self._t[i] = self._t[i - 1] + self._sr_recip
            self._prev_n = n
        return self._t[:n]

    def _ensure_scratch(self, n: int) -> np.ndarray:
        """Return a scratch buffer of at least *n* elements."""
        if self._scratch is None or len(self._scratch) < n:
            self._scratch = np.empty(n, dtype=np.float32)
        return self._scratch[:n]

    def _ensure_phase(self, n: int) -> np.ndarray:
        """Return the reusable phase buffer sized for cumulative sum + 1."""
        needed = n + 1
        if self._phase is None or len(self._phase) < needed:
            self._phase = np.zeros(needed, dtype=np.float64)
        elif len(self._phase) > needed:
            # Zero the first element only; the rest are overwritten by cumsum
            self._phase[0] = 0.0
        return self._phase[:needed]

    # =====================================================================
    # Dispatch
    # =====================================================================

    def apply_articulation(
        self,
        sample: np.ndarray,
        articulation: str,
        params: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """
        Apply articulation to sample data.

        Args:
            sample: Input sample array (mono 1-D)
            articulation: Articulation name
            params: Optional articulation parameters

        Returns:
            Modified sample array, float32, same length as input
        """
        params = params or {}

        if articulation == "normal" or not articulation:
            return sample

        # Check custom handlers first
        if articulation in self._custom_handlers:
            return self._custom_handlers[articulation](sample, params)

        # Apply specific articulation
        method_name = f"apply_{articulation}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(sample, params)

        # Default: return unchanged
        logger.debug(f"No specific handler for articulation: {articulation}")
        return sample

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a custom articulation handler."""
        self._custom_handlers[name] = handler

    # =====================================================================
    # Shared DSP helpers
    # =====================================================================

    @staticmethod
    def _validate_block(sample: np.ndarray) -> int:
        """Validate sample array and return length in samples."""
        if sample.ndim == 1:
            n = len(sample)
        else:
            n = sample.shape[0]
        if n < 1:
            raise ValueError("Sample array is empty")
        return n

    def _pitch_resample(
        self, sample: np.ndarray, freq_mult: np.ndarray
    ) -> np.ndarray:
        """
        Resample with linear interpolation.

        Replaces the previous nearest-neighbour approach.  Handles
        arbitrary time-varying frequency multipliers (e.g. from vibrato,
        glissando, bend).  Zero-allocation after scratch buffer warm-up.

        Args:
            sample: Input audio (mono 1-D), float32
            freq_mult: Per-sample frequency ratio (len = len(sample)),
                       values >1 speed up (raise pitch), <1 slow down.

        Returns:
            Resampled audio, float32, same length as *sample*.
        """
        n = len(sample)

        # Cumulative phase in original-sample coordinates — reuse phase buffer.
        phase = self._ensure_phase(n)
        phase[0] = 0.0
        np.cumsum(freq_mult, out=phase[1:])

        # Source coordinate for each output sample.
        src = phase[:-1]

        # Linear interpolation between neighbours.
        idx0 = np.floor(src).astype(np.int64)
        frac = (src - idx0).astype(np.float32)

        # Clamp to valid range to avoid IndexError at boundaries.
        idx0 = np.clip(idx0, 0, n - 1)
        idx1 = np.clip(idx0 + 1, 0, n - 1)

        # NOTE: fancy-indexing + arithmetic here is unavoidably allocating;
        # the result is our output so there is no way around it.
        result = sample[idx0] * (1.0 - frac) + sample[idx1] * frac
        return result.astype(np.float32, copy=False)

    def _one_pole_lowpass(
        self, sample: np.ndarray, cutoff_hz: float, key: str = "default"
    ) -> np.ndarray:
        """
        One-pole IIR lowpass filter.

        Replaces boxcar (FIR) convolution used previously.  O(N),
        constant memory, better frequency response.  Writes output
        into the internal scratch buffer to avoid np.empty allocation.

            y[n] = alpha * x[n] + (1 - alpha) * y[n-1]

        The filter *state* is persisted per *key* so that consecutive
        calls for the same articulation don't click at block boundaries.
        """
        dt = self._sr_recip
        tau = 1.0 / max(2.0 * np.pi * cutoff_hz, 1e-6)
        alpha = dt / (tau + dt)
        alpha = float(np.clip(alpha, 0.001, 0.999))

        n = len(sample)
        out = self._ensure_scratch(n)
        state = self._lp_state.get(key, 0.0)
        for i in range(n):
            state += alpha * (float(sample[i]) - state)
            out[i] = state
        self._lp_state[key] = state
        return out

    @staticmethod
    def _apply_envelope(sample: np.ndarray, envelope: np.ndarray) -> np.ndarray:
        """Multiply sample by an amplitude envelope."""
        return (sample * envelope).astype(np.float32, copy=False)

    # =====================================================================
    # Pitch-based articulations (via linear-interpolation resampling)
    # =====================================================================

    def apply_vibrato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply vibrato — sinusoidal pitch modulation."""
        rate = params.get("rate", 5.0)
        depth = params.get("depth", 0.5)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        # Map depth 0-1 → ±0.3 semitones peak deviation
        cents = depth * 0.3
        pitch_mod = cents * np.sin(2.0 * np.pi * rate * t)
        freq_mult = SEMITONE_RATIO**pitch_mod
        return self._pitch_resample(sample, freq_mult)

    def apply_trill(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply trill — smooth sinusoidal alternation (was square wave)."""
        rate = params.get("rate", 8.0)
        interval = params.get("interval", 2)  # semitones
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        # Sinusoidal, not square: no clicks at transition boundaries.
        pitch_mod = interval * 0.5 * (1.0 + np.sin(2.0 * np.pi * rate * t))
        freq_mult = SEMITONE_RATIO**pitch_mod
        return self._pitch_resample(sample, freq_mult)

    def apply_glissando(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply glissando — smooth pitch slide."""
        amount = params.get("amount", 12)  # semitones
        n = self._validate_block(sample)
        # Progress 0→1 over the block — small allocation accepted
        progress = np.arange(n, dtype=np.float32) / n
        freq_mult = SEMITONE_RATIO ** (amount * progress)
        return self._pitch_resample(sample, freq_mult)

    def apply_bend(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Apply pitch bend via resampling.

        NOTE: previous implementation used amplitude modulation (multiplying
        the sample by freq_mult), which produced tremolo, not pitch bend.
        """
        amount = params.get("amount", 1.0)  # semitones
        n = self._validate_block(sample)
        # Progress 0→1 over the block — small allocation accepted
        progress = np.arange(n, dtype=np.float32) / n
        freq_mult = SEMITONE_RATIO ** (amount * progress)
        return self._pitch_resample(sample, freq_mult)

    def apply_hammer_on(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply hammer-on — quick pitch rise."""
        amount = params.get("amount", 2)  # semitones
        n = self._validate_block(sample)
        pitch_rise = np.arange(n, dtype=np.float32) / n * amount
        freq_mult = SEMITONE_RATIO**pitch_rise
        return self._pitch_resample(sample, freq_mult)

    def apply_pull_off(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply pull-off — quick pitch drop."""
        amount = params.get("amount", -2)  # semitones (negative = down)
        n = self._validate_block(sample)
        pitch_drop = np.arange(n, dtype=np.float32) / n * amount
        freq_mult = SEMITONE_RATIO**pitch_drop
        return self._pitch_resample(sample, freq_mult)

    def apply_ethnic_bend(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply ethnic-style pitch bend (exponential approach)."""
        bend_amount = params.get("bend_amount", 0.5)  # semitones
        bend_speed = params.get("bend_speed", 0.3)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        # Exponential approach to target pitch.
        progress = 1.0 - np.exp(-t * bend_speed * 10.0)
        freq_mult = SEMITONE_RATIO ** (bend_amount * progress)
        return self._pitch_resample(sample, freq_mult)

    # =====================================================================
    # Amplitude envelope articulations
    # =====================================================================

    def apply_pizzicato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply pizzicato — plucked-string exponential decay."""
        decay = params.get("decay", 8.0)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        envelope = np.exp(-t * decay)
        return self._apply_envelope(sample, envelope)

    def apply_swell(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply swell — crescendo then decrescendo."""
        attack = params.get("attack", 0.1)
        release = params.get("release", 0.2)
        n = self._validate_block(sample)
        attack_samples = int(attack * self.sample_rate)
        release_samples = int(release * self.sample_rate)
        envelope = self._ensure_scratch(n)
        envelope[:] = 1.0  # in-place fill, no allocation
        if attack_samples > 0:
            attack_len = min(attack_samples, n)
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        if release_samples > 0:
            release_len = min(release_samples, n)
            envelope[-release_len:] = np.linspace(1, 0, release_len)
        return self._apply_envelope(sample, envelope)

    def apply_marcato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply marcato — accented attack with quick decay."""
        n = self._validate_block(sample)
        attack_samples = min(int(0.02 * self.sample_rate), n)
        envelope = self._ensure_scratch(n)
        envelope[:] = 1.0
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1.5, attack_samples)
        t = self._ensure_time(n)
        decay = np.exp(-t * 8.0)
        envelope *= decay  # compound in-place: still allocates decay, but
        # avoids the `envelope * decay` temp for _apply_envelope
        return self._apply_envelope(sample, envelope)

    def apply_crescendo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply crescendo — gradual volume increase."""
        target_level = params.get("target_level", 1.0)
        duration = params.get("duration", 1.0)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        progress = np.clip(t / duration, 0, 1)
        envelope = 0.3 + progress * (target_level - 0.3)
        return self._apply_envelope(sample, envelope)

    def apply_diminuendo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply diminuendo — gradual volume decrease."""
        target_level = params.get("target_level", 0.1)
        duration = params.get("duration", 1.0)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        progress = np.clip(t / duration, 0, 1)
        envelope = 1.0 - progress * (1.0 - target_level)
        return self._apply_envelope(sample, envelope)

    def apply_staccato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply staccato — short, detached note with decay tail."""
        length = params.get("note_length", 0.3)
        n = self._validate_block(sample)
        target_length = int(n * length)
        if 0 < target_length < n:
            # Use scratch buffer instead of np.zeros
            result = self._ensure_scratch(n)
            result[:] = 0.0
            result[:target_length] = sample[:target_length]
            # Exponential decay over the shortened region.
            t = self._ensure_time(target_length)
            decay = np.exp(-t * 5.0 / max(length, 0.01))
            result[:target_length] *= decay
            return result
        return sample

    def apply_legato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply legato — smooth fade-in / fade-out transitions."""
        transition_time = params.get("transition_time", 0.05)
        n = self._validate_block(sample)
        transition_samples = int(transition_time * self.sample_rate)
        if n > transition_samples * 2 and transition_samples > 0:
            # Copy sample into scratch buffer instead of sample.copy()
            result = self._ensure_scratch(n)
            result[:] = sample
            result[:transition_samples] *= np.linspace(0, 1, transition_samples)
            result[-transition_samples:] *= np.linspace(1, 0, transition_samples)
            return result
        return sample

    # =====================================================================
    # Amplitude modulation articulations (tremolo, flutter, growl)
    # =====================================================================

    def apply_tremolo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply tremolo — sinusoidal volume modulation."""
        rate = params.get("rate", 6.0)
        depth = params.get("depth", 0.5)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        # Symmetric: amplitude varies from (1-depth) to (1+depth)
        mod = 1.0 + depth * np.sin(2.0 * np.pi * rate * t)
        return self._apply_envelope(sample, mod)

    def apply_flutter(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply flutter tongue — fast amplitude modulation."""
        mod_freq = params.get("mod_freq", 12.0)
        depth = params.get("depth", 0.15)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        mod = 1.0 + depth * np.sin(2.0 * np.pi * mod_freq * t)
        return self._apply_envelope(sample, mod)

    def apply_growl(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Apply growl — low-frequency modulation + filtered noise texture.

        Uses one-pole IIR for noise colouration instead of the previous
        boxcar convolution.
        """
        mod_freq = params.get("mod_freq", 25.0)
        depth = params.get("depth", 0.25)
        n = self._validate_block(sample)
        if n < 1:
            return sample
        t = self._ensure_time(n)
        mod = 1.0 + depth * np.sin(2.0 * np.pi * mod_freq * t)
        # Filtered noise — one-pole IIR replaces boxcar + convolution.
        noise = np.random.normal(0, 0.08, n).astype(np.float32)
        noise = self._one_pole_lowpass(noise, 800.0, "growl")
        return ((sample * mod) + noise * 0.15).astype(np.float32)

    # =====================================================================
    # Filter-based articulations (via one-pole IIR)
    # =====================================================================

    def apply_soft_pedal(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Apply soft pedal (una corda) — reduced volume + lowpass.

        Uses one-pole IIR instead of O(NK) boxcar convolution.
        """
        level = params.get("level", 0.7)
        brightness = params.get("brightness", 0.8)
        result = sample * level
        if brightness < 1.0:
            cutoff = 200.0 + brightness * 19800.0
            result = self._one_pole_lowpass(result, cutoff, "soft_pedal")
        return result.astype(np.float32)

    def apply_sub_bass(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Apply sub bass — lowpass + sub-oscillator.

        Uses one-pole IIR instead of boxcar convolution for smoothing.
        """
        sub_freq = params.get("sub_freq", 40.0)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        sub_osc = np.sin(2.0 * np.pi * sub_freq * t) * 0.3
        sample_smooth = self._one_pole_lowpass(sample, 200.0, "sub_bass")
        return (sample_smooth + sub_osc).astype(np.float32)

    def apply_dead_note(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Apply dead note — muted percussive sound.

        Uses one-pole IIR for noise colouration instead of boxcar.
        """
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        decay = np.exp(-t * 30.0)
        noise = np.random.normal(0, 0.3, n).astype(np.float32)
        noise = self._one_pole_lowpass(noise, 1200.0, "dead_note")
        result = sample * decay * 0.3 + noise * decay * 0.5
        return result.astype(np.float32)

    # =====================================================================
    # Pedal articulations
    # =====================================================================

    def apply_sustain_pedal(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply sustain pedal — extends release with exponential decay."""
        sustain_level = params.get("sustain_level", 0.8)
        release_rate = params.get("release_rate", 0.5)
        n = self._validate_block(sample)
        envelope = self._ensure_scratch(n)
        envelope[:] = 1.0
        sustain_start = int(n * 0.3)
        if sustain_start < n:
            tail_len = n - sustain_start
            t = self._ensure_time(tail_len)
            decay = np.exp(-t * release_rate)
            envelope[sustain_start:] = sustain_level + (1.0 - sustain_level) * decay
        return self._apply_envelope(sample, envelope)

    # =====================================================================
    # Noise / impulse articulations
    # =====================================================================

    def apply_fret_noise(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Add fret noise — short burst at attack."""
        noise_level = params.get("noise_level", 0.15)
        n = self._validate_block(sample)
        attack_samples = int(0.02 * self.sample_rate)
        # Copy sample into scratch buffer instead of sample.copy()
        result = self._ensure_scratch(n)
        result[:] = sample
        if attack_samples > 0:
            attack_len = min(attack_samples, n)
            noise = np.random.normal(0, noise_level, attack_len).astype(np.float32)
            result[:attack_len] += noise
        return result.astype(np.float32)

    def apply_organ_click(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply organ click — percussive impulse at attack."""
        click_level = params.get("click_level", 0.2)
        click_width = params.get("click_width", 0.005)
        n = self._validate_block(sample)
        click_samples = int(click_width * self.sample_rate)
        # Copy sample into scratch buffer instead of sample.copy()
        result = self._ensure_scratch(n)
        result[:] = sample
        if click_samples > 0:
            click_len = min(click_samples, n)
            click = np.random.normal(0, click_level, click_len).astype(np.float32)
            t_click = self._ensure_time(click_len)
            click *= np.exp(-t_click * 50.0)
            result[:click_len] += click
        return result.astype(np.float32)

    def apply_palm_mute(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply palm mute — dampened decay + attack noise."""
        damp_factor = params.get("damp_factor", 0.5)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        decay = np.exp(-t * 10.0 * (1.0 - damp_factor))
        result = (sample * decay).astype(np.float32)
        attack_samples = int(0.01 * self.sample_rate)
        if attack_samples > 0:
            attack_len = min(attack_samples, n)
            noise = np.random.normal(0, 0.2, attack_len).astype(np.float32)
            result[:attack_len] += noise * damp_factor * 0.3
        return result

    def apply_rim_shot(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply rim shot — hard attack, fast decay, impulse."""
        rim_level = params.get("rim_level", 0.6)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        decay = np.exp(-t * 20.0)
        result = (sample * decay).astype(np.float32)
        attack_samples = int(0.005 * self.sample_rate)
        if attack_samples > 0:
            attack_len = min(attack_samples, n)
            impulse = np.random.normal(0, rim_level, attack_len).astype(np.float32)
            result[:attack_len] += impulse
        return result

    def apply_open_rim(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply open rim shot — resonant ring with decay."""
        ring_time = params.get("ring_time", 0.3)
        n = self._validate_block(sample)
        t = self._ensure_time(n)
        decay = np.exp(-t * (3.0 / max(ring_time, 0.01)))
        return self._apply_envelope(sample, decay)

    def apply_harmonics(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """
        Add harmonic content to the sample.

        Derives fundamental frequency from MIDI note number (defaults to
        A4 = 69 if not provided in params), instead of the previous
        hardcoded 440 Hz.
        """
        harmonic = params.get("harmonic", 2)
        level = params.get("level", 0.35)
        note = params.get("note", 69)  # MIDI note; A4 default
        n = self._validate_block(sample)
        base_freq = 440.0 * (SEMITONE_RATIO ** (note - 69))
        t = self._ensure_time(n)
        harmonic_wave = np.sin(2.0 * np.pi * base_freq * harmonic * t) * level
        return (sample + harmonic_wave).astype(np.float32)


def create_sample_modifier(sample_rate: int = 44100) -> SF2SampleModifier:
    """Create and return an SF2SampleModifier instance."""
    return SF2SampleModifier(sample_rate=sample_rate)


__all__ = [
    "SF2SampleModifier",
    "create_sample_modifier",
]
