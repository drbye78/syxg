"""Spectral sustain model — filter noise to match attack spectrum.

Universal fallback for instruments where modal resonance is insufficient
(choir, accordion, ethnic, organ, pads). Generates timbrally rich sustain
by filtering colored noise through the attack boundary spectrum.

Why this works: the attack spectrum captures the instrument's formant
signature. Filtering noise to match it produces a timbrally related sustain.
The decay filter then shapes the time evolution per instrument group.
"""

from __future__ import annotations

import numpy as np

from synth.engines.acoustic.behavior_config import InstrumentGroup, get_modal_profile


class SpectralSustainModel:
    """Generate sustain audio from attack spectrum via filtered noise.

    Simpler and more universal than modal resonance. Suitable for
    instruments where the exact harmonic structure matters more than
    physical accuracy — choir, ethnic instruments, pads, accordion.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._noise_cache: np.ndarray | None = None
        self._noise_idx: int = 0

    def _ensure_noise(self, n: int) -> np.ndarray:
        """Generate or reuse pink-like noise (1/f approximation)."""
        if self._noise_cache is None or self._noise_idx + n > len(self._noise_cache):
            # Generate pink-like noise: white noise → 1/f filter via cumulative sum
            white = np.random.normal(0, 1, max(n * 2, 8192)).astype(np.float32)
            # Simple 1/f approximation: lowpass + normalize
            pink = np.cumsum(white)
            pink -= np.mean(pink)
            pink /= max(np.std(pink), 1e-6) * 3.0
            self._noise_cache = pink.astype(np.float32)
            self._noise_idx = 0
        result = self._noise_cache[self._noise_idx:self._noise_idx + n]
        self._noise_idx += n
        return result

    def generate(
        self,
        block_size: int,
        attack_spectrum: np.ndarray | None,
        instrument_group: InstrumentGroup,
        velocity: int,
        elapsed_samples: int,
    ) -> np.ndarray:
        """Generate one block of spectral sustain audio.

        Args:
            block_size: Samples to generate.
            attack_spectrum: FFT magnitude from attack boundary (rfft format).
                            If None, use synthesized spectrum from note.
            instrument_group: Instrument group for decay profile.
            velocity: MIDI velocity for excitation level.
            elapsed_samples: How long the note has been in sustain phase.

        Returns:
            Mono float32 array of spectral sustain audio.
        """
        # Generate noise base
        noise = self._ensure_noise(block_size)

        # Apply spectral shaping from attack
        if attack_spectrum is not None and len(attack_spectrum) >= block_size // 2 + 1:
            noise_fft = np.fft.rfft(noise)
            # Scale each bin by the attack spectrum magnitude (formant preservation)
            magnitude = np.abs(attack_spectrum[:len(noise_fft)])
            if np.max(magnitude) > 1e-6:
                magnitude /= np.max(magnitude)
            noise_fft *= magnitude
            shaped = np.fft.irfft(noise_fft, n=block_size)
        else:
            shaped = noise

        # Apply per-instrument decay curve
        profile = get_modal_profile(instrument_group)
        decay_rate = self._get_decay_rate(instrument_group, velocity)
        t = (elapsed_samples + np.arange(block_size, dtype=np.float32)) / self.sample_rate

        # Exponential decay
        envelope = np.exp(-t * decay_rate).astype(np.float32)

        # Velocity scaling
        vel_scale = velocity / 127.0

        return shaped * envelope * vel_scale * 0.3

    @staticmethod
    def _get_decay_rate(group: InstrumentGroup, velocity: int) -> float:
        """Per-instrument-group decay rate (higher = faster decay)."""
        base_rates = {
            InstrumentGroup.ACOUSTIC_PIANO: 2.5,
            InstrumentGroup.BOWED_STRINGS: 1.0,
            InstrumentGroup.ACOUSTIC_GUITAR: 3.0,
            InstrumentGroup.BRASS: 2.0,
            InstrumentGroup.REEDS_WOODWINDS: 1.5,
            InstrumentGroup.CHOIR: 1.2,
            InstrumentGroup.ORGAN: 0.3,  # Sustained
            InstrumentGroup.HARP: 4.0,
            InstrumentGroup.MALLETS: 5.0,
        }
        base = base_rates.get(group, 2.0)
        # Lower velocity = slightly faster decay (less energy)
        vel_factor = 0.8 + 0.4 * (velocity / 127.0)
        return base * vel_factor

    def reset(self) -> None:
        """Reset noise state for new note."""
        self._noise_idx = 0
