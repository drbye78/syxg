"""
Sample Modifiers for S.Art2 Articulation System.

Contains SF2SampleModifier class that applies real-time articulation
effects to sample data. Extracted for better code organization.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SF2SampleModifier:
    """
    Modifier that applies articulations to SF2 sample playback.

    Provides real-time sample manipulation for S.Art2-style articulations
    on SoundFont samples.

    Usage:
        modifier = SF2SampleModifier()
        modified = modifier.apply_articulation(sample, 'legato')
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize the sample modifier."""
        self.sample_rate = sample_rate
        self._custom_handlers: dict[str, Callable] = {}

    def apply_articulation(
        self,
        sample: np.ndarray,
        articulation: str,
        params: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """
        Apply articulation to sample data.

        Args:
            sample: Input sample array
            articulation: Articulation name
            params: Optional articulation parameters

        Returns:
            Modified sample array
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

    # =========================================================================
    # Articulation Methods
    # =========================================================================

    def apply_legato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply legato articulation - smooth transitions."""
        blend = params.get("blend", 0.5)
        transition_time = params.get("transition_time", 0.05)

        transition_samples = int(transition_time * self.sample_rate)
        if len(sample) > transition_samples * 2:
            fade_in = np.linspace(0, 1, transition_samples)
            fade_out = np.linspace(1, 0, transition_samples)

            result = sample.copy()
            result[:transition_samples] *= fade_in
            result[-transition_samples:] *= fade_out

            return result

        return sample

    def apply_staccato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply staccato articulation - short, detached notes."""
        length = params.get("note_length", 0.3)

        target_length = int(len(sample) * length)
        if target_length < len(sample):
            result = sample[:target_length]
            # Add decay
            decay = np.exp(-np.linspace(0, 5, len(result)))
            result = result * decay
            # Pad to original length
            result = np.pad(result, (0, len(sample) - len(result)), mode="constant")
            return result

        return sample

    def apply_vibrato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply vibrato - pitch modulation."""
        rate = params.get("rate", 5.0)
        depth = params.get("depth", 0.5)

        SEMITONE_RATIO = 1.059463359
        cents = depth / 100.0
        t = np.arange(len(sample)) / self.sample_rate
        pitch_mod = cents * np.sin(2 * np.pi * rate * t)
        freq_mult = SEMITONE_RATIO**pitch_mod

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_trill(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply trill - rapid alternation."""
        rate = params.get("rate", 8.0)
        interval = params.get("interval", 2)  # semitones

        SEMITONE_RATIO = 1.059463359
        t = np.arange(len(sample)) / self.sample_rate

        pitch_mod = interval * (np.sin(2 * np.pi * rate * t) > 0).astype(float)
        freq_mult = SEMITONE_RATIO**pitch_mod

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_pizzicato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply pizzicato - plucked string sound."""
        decay = params.get("decay", 8.0)

        t = np.arange(len(sample)) / self.sample_rate
        envelope = np.exp(-t * decay)

        return (sample * envelope).astype(np.float32)

    def apply_glissando(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply glissando - smooth pitch slide."""
        amount = params.get("amount", 12)

        SEMITONE_RATIO = 1.059463359
        t = np.arange(len(sample)) / self.sample_rate
        progress = np.linspace(0, 1, len(sample))
        pitch_rise = amount * progress
        freq_mult = SEMITONE_RATIO**pitch_rise

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_growl(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply growl - growling texture."""
        mod_freq = params.get("mod_freq", 25.0)
        depth = params.get("depth", 0.25)

        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))

        noise = np.random.normal(0, 0.1, len(sample))
        noise = np.convolve(noise, np.ones(50) / 50, mode="same")

        return (sample * mod + noise * 0.2).astype(np.float32)

    def apply_flutter(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply flutter tongue."""
        mod_freq = params.get("mod_freq", 12.0)
        depth = params.get("depth", 0.15)

        t = np.arange(len(sample)) / self.sample_rate
        mod = depth * (1 + np.sin(2 * np.pi * mod_freq * t))

        return (sample * mod).astype(np.float32)

    def apply_bend(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply pitch bend."""
        amount = params.get("amount", 1.0)

        SEMITONE_RATIO = 1.059463359
        bend_amount = amount / 12.0

        t = np.arange(len(sample)) / self.sample_rate
        progress = np.linspace(0, 1, len(sample))
        freq_mult = SEMITONE_RATIO ** (bend_amount * progress)

        return (sample * freq_mult).astype(np.float32)

    def apply_swell(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply swell - volume crescendo then decrescendo."""
        attack = params.get("attack", 0.1)
        release = params.get("release", 0.2)

        attack_samples = int(attack * self.sample_rate)
        release_samples = int(release * self.sample_rate)

        envelope = np.ones(len(sample))
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(1, 0, release_samples)

        return (sample * envelope).astype(np.float32)

    def apply_harmonics(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply harmonics - add harmonic content."""
        harmonic = params.get("harmonic", 2)
        level = params.get("level", 0.35)

        base_freq = 440
        t = np.arange(len(sample)) / self.sample_rate
        harmonic_wave = np.sin(2 * np.pi * base_freq * harmonic * t)

        return (sample + harmonic_wave * level).astype(np.float32)

    def apply_crescendo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply crescendo - gradual volume increase."""
        target_level = params.get("target_level", 1.0)
        duration = params.get("duration", 1.0)

        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / duration, 0, 1)

        envelope = 0.3 + progress * (target_level - 0.3)

        return (sample * envelope).astype(np.float32)

    def apply_diminuendo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply diminuendo - gradual volume decrease."""
        target_level = params.get("target_level", 0.1)
        duration = params.get("duration", 1.0)

        t = np.arange(len(sample)) / self.sample_rate
        progress = np.clip(t / duration, 0, 1)

        envelope = 1.0 - progress * (1.0 - target_level)

        return (sample * envelope).astype(np.float32)

    def apply_marcato(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply marcato - accented, strong attack."""
        attack_samples = int(0.02 * self.sample_rate)
        envelope = np.ones(len(sample))
        envelope[:attack_samples] = np.linspace(0, 1.5, attack_samples)

        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 8)

        return (sample * envelope * decay).astype(np.float32)

    def apply_soft_pedal(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply soft pedal (una corda) - reduced volume, softer tone."""
        level = params.get("level", 0.7)
        brightness = params.get("brightness", 0.8)

        result = sample * level

        if brightness < 1.0:
            kernel_size = int((1.0 - brightness) * 100) + 1
            kernel = np.ones(kernel_size) / kernel_size
            result = np.convolve(result, kernel, mode="same")

        return result.astype(np.float32)

    def apply_sustain_pedal(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply sustain pedal - extends release."""
        sustain_level = params.get("sustain_level", 0.8)
        release_rate = params.get("release_rate", 0.5)

        envelope = np.ones(len(sample))
        sustain_start = int(len(sample) * 0.3)
        for i in range(sustain_start, len(sample)):
            decay = np.exp(-(i - sustain_start) * release_rate / self.sample_rate)
            envelope[i] = sustain_level + (1 - sustain_level) * decay

        return (sample * envelope).astype(np.float32)

    def apply_hammer_on(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply hammer-on - quick pitch rise."""
        amount = params.get("amount", 2)
        SEMITONE_RATIO = 1.059463359

        pitch_rise = np.linspace(0, amount, len(sample))
        freq_mult = SEMITONE_RATIO**pitch_rise

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_pull_off(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply pull-off - quick pitch drop."""
        amount = params.get("amount", -2)
        SEMITONE_RATIO = 1.059463359

        pitch_drop = np.linspace(0, amount, len(sample))
        freq_mult = SEMITONE_RATIO**pitch_drop

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_palm_mute(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply palm mute - dampened sound."""
        damp_factor = params.get("damp_factor", 0.5)

        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 10 * (1 - damp_factor))

        attack_samples = int(0.01 * self.sample_rate)
        attack = np.zeros(len(sample))
        if attack_samples > 0:
            attack[:attack_samples] = np.random.normal(0, 0.2, attack_samples)

        return (sample * decay + attack * damp_factor * 0.3).astype(np.float32)

    def apply_tremolo(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply tremolo - fast volume modulation."""
        rate = params.get("rate", 6.0)
        depth = params.get("depth", 0.5)

        t = np.arange(len(sample)) / self.sample_rate
        mod = 1.0 - depth * (1 + np.sin(2 * np.pi * rate * t)) / 2

        return (sample * mod).astype(np.float32)

    def apply_sub_bass(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply sub bass - add sub-bass frequency content."""
        sub_freq = 40
        t = np.arange(len(sample)) / self.sample_rate
        sub_osc = np.sin(2 * np.pi * sub_freq * t) * 0.3

        kernel = np.ones(50) / 50
        sample_smooth = np.convolve(sample, kernel, mode="same")

        return (sample_smooth + sub_osc).astype(np.float32)

    def apply_dead_note(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply dead note - muted percussive sound."""
        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 30)

        noise = np.random.normal(0, 0.3, len(sample))
        noise = np.convolve(noise, np.ones(20) / 20, mode="same")

        result = sample * decay * 0.3 + noise * decay * 0.5
        return result.astype(np.float32)

    def apply_fret_noise(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Add fret noise - finger on frets."""
        noise_level = params.get("noise_level", 0.15)

        attack_samples = int(0.02 * self.sample_rate)
        fret_noise = np.zeros(len(sample))
        fret_noise[:attack_samples] = np.random.normal(0, noise_level, attack_samples)

        return (sample + fret_noise).astype(np.float32)

    def apply_organ_click(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply organ click - percussive attack."""
        click_level = params.get("click_level", 0.2)
        click_width = params.get("click_width", 0.005)

        click_samples = int(click_width * self.sample_rate)
        click = np.zeros(len(sample))
        click[:click_samples] = np.random.normal(0, click_level, click_samples)

        t = np.arange(click_samples) / self.sample_rate
        click[:click_samples] *= np.exp(-t * 50)

        return (sample + click).astype(np.float32)

    def apply_ethnic_bend(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply ethnic-style pitch bend."""
        bend_amount = params.get("bend_amount", 0.5)
        bend_speed = params.get("bend_speed", 0.3)

        SEMITONE_RATIO = 1.059463359
        t = np.arange(len(sample)) / self.sample_rate
        progress = 1 - np.exp(-t * bend_speed * 10)
        bend = bend_amount * progress
        freq_mult = SEMITONE_RATIO**bend

        indices = np.cumsum(freq_mult) / self.sample_rate
        indices = np.clip(indices * self.sample_rate, 0, len(sample) - 1).astype(int)

        return sample[indices].astype(np.float32)

    def apply_rim_shot(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply rim shot - hard attack with rim sound."""
        rim_level = params.get("rim_level", 0.6)

        attack_samples = int(0.005 * self.sample_rate)
        attack = np.zeros(len(sample))
        attack[:attack_samples] = np.random.normal(0, rim_level, attack_samples)

        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * 20)

        return (sample * decay + attack).astype(np.float32)

    def apply_open_rim(self, sample: np.ndarray, params: dict) -> np.ndarray:
        """Apply open rim shot - resonant."""
        ring_time = params.get("ring_time", 0.3)

        t = np.arange(len(sample)) / self.sample_rate
        decay = np.exp(-t * (3 / ring_time))

        return (sample * decay).astype(np.float32)


def create_sample_modifier(sample_rate: int = 44100) -> SF2SampleModifier:
    """Create and return an SF2SampleModifier instance."""
    return SF2SampleModifier(sample_rate=sample_rate)


__all__ = [
    "SF2SampleModifier",
    "create_sample_modifier",
]
