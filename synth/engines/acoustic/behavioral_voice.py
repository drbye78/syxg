"""Behavioral Voice — hybrid PCM+Model synthesis for acoustic instruments.

The core behavioral synthesis component. At note-on, plays a PCM attack
transient from SF2 sample data, then crossfades to a physically-inspired
modal resonator for infinitely variable sustain and release.

Per the Behavioral Synthesis strategy, the modal resonator uses a phase-locked
crossfade: at the transition boundary, oscillator phases are initialized from
the PCM signal's short-time FFT to eliminate comb filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from synth.engines.acoustic.sample_analyzer import ModalParameter


class VoicePhase(StrEnum):
    ATTACK = "attack"      # Playing PCM transient
    CROSSFADE = "crossfade" # Transitioning PCM→Model
    SUSTAIN = "sustain"    # Pure behavioral sustain
    RELEASE = "release"    # Behavioral release with damper


@dataclass(slots=True)
class BehavioralVoiceState:
    """Per-voice mutable state for behavioral synthesis."""

    phase: VoicePhase = VoicePhase.ATTACK
    note: int = 60
    velocity: int = 100
    sample_rate: int = 44100

    # PCM attack state
    attack_position: float = 0.0
    attack_length: int = 0
    attack_data: np.ndarray | None = None

    # Crossfade state
    crossfade_position: int = 0
    crossfade_length: int = 0

    # Modal oscillator state
    oscillators: list[_ModalOscillator] = field(default_factory=list)

    # Excitation state
    excitation_level: float = 0.0
    excitation_decay: float = 0.0

    # Damper
    damper_position: float = 0.0  # 0.0=fully open, 1.0=fully damped


@dataclass(slots=True)
class _ModalOscillator:
    """Single damped harmonic oscillator per mode."""

    mode: ModalParameter
    position: float = 0.0  # Current displacement
    velocity: float = 0.0  # Current velocity


class BehavioralVoice:
    """Hybrid PCM+Model voice for a single note.

    Usage:
        voice = BehavioralVoice(sample_rate=44100)
        voice.note_on(60, 100, attack_data, modes, attack_len=4410)
        # In audio loop:
        while voice.is_active():
            buf = voice.render(256)
    """

    def __init__(self, sample_rate: int = 44100):
        self.state = BehavioralVoiceState(sample_rate=sample_rate)
        self._output: np.ndarray | None = None
        self._render_buf: np.ndarray | None = None

    def note_on(
        self,
        note: int,
        velocity: int,
        attack_data: np.ndarray,
        modes: list[ModalParameter],
        attack_length: int = 0,
        crossfade_length: int = 1323,  # ~30ms at 44.1kHz
    ) -> None:
        """Initialize voice with PCM attack and modal parameters.

        Phase-locks oscillators to PCM signal at crossfade start for
        seamless transition.
        """
        sr = self.state.sample_rate
        self.state.note = note
        self.state.velocity = velocity
        self.state.phase = VoicePhase.ATTACK
        self.state.attack_position = 0
        self.state.crossfade_position = 0

        # Use provided attack length or auto-detect
        if attack_length > 0 and attack_length < len(attack_data):
            self.state.attack_data = attack_data
            self.state.attack_length = attack_length
        else:
            self.state.attack_data = attack_data
            self.state.attack_length = len(attack_data)

        self.state.crossfade_length = crossfade_length

        # Excitation level from velocity
        self.state.excitation_level = velocity / 127.0
        # Higher notes decay slightly faster
        freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
        self.state.excitation_decay = 0.5 + freq / 8000.0

        # Initialize oscillators with phase lock
        if len(attack_data) >= 512:
            self._phase_lock_oscillators(attack_data, modes)
        else:
            self._init_oscillators(modes)

        # Clear output buffer
        self._output = None

    def _phase_lock_oscillators(
        self, attack_data: np.ndarray, modes: list[ModalParameter]
    ) -> None:
        """Initialize oscillator phases from PCM signal at crossfade boundary."""
        window = attack_data[-512:] * np.hanning(512)
        spectrum = np.fft.rfft(window)
        sr = self.state.sample_rate

        self.state.oscillators = []
        for mode in modes:
            bin_idx = int(mode.frequency * 512 / sr)
            if bin_idx < len(spectrum):
                phase = float(np.angle(spectrum[bin_idx]))
            else:
                phase = 0.0
            osc = _ModalOscillator(mode=mode)
            osc.position = mode.amplitude * np.cos(phase) * self.state.excitation_level
            osc.velocity = mode.amplitude * np.sin(phase) * self.state.excitation_level * mode.frequency
            self.state.oscillators.append(osc)

    def _init_oscillators(self, modes: list[ModalParameter]) -> None:
        """Initialize oscillators without phase lock (fallback)."""
        self.state.oscillators = []
        for mode in modes:
            self.state.oscillators.append(_ModalOscillator(mode=mode))

    def render(self, block_size: int) -> np.ndarray:
        """Render one block of audio. Returns mono float32 array."""
        out = np.zeros(block_size, dtype=np.float32)
        state = self.state

        for i in range(block_size):
            sample = 0.0

            if state.phase == VoicePhase.ATTACK:
                # Play PCM attack
                pos = int(state.attack_position)
                if pos < state.attack_length and state.attack_data is not None:
                    sample = float(state.attack_data[pos])
                    state.attack_position += 1.0
                else:
                    state.phase = VoicePhase.CROSSFADE
                    state.crossfade_position = 0

            if state.phase == VoicePhase.CROSSFADE:
                # Crossfade PCM→Model
                t = state.crossfade_position / max(state.crossfade_length, 1)
                pcm = 0.0
                pos = int(state.attack_position)
                if pos < len(state.attack_data) if state.attack_data is not None else 0:
                    if state.attack_data is not None:
                        pcm = float(state.attack_data[pos])
                        state.attack_position += 1.0

                model = self._render_model_sample(i, block_size)
                sample = pcm * (1.0 - t) + model * t

                state.crossfade_position += 1
                if state.crossfade_position >= state.crossfade_length:
                    state.phase = VoicePhase.SUSTAIN

            elif state.phase == VoicePhase.SUSTAIN:
                # Pure behavioral sustain
                sample = self._render_model_sample(i, block_size)

            elif state.phase == VoicePhase.RELEASE:
                # Behavioral release with damper
                sample = self._render_model_sample(i, block_size)
                # Damper reduces excitation, oscillators decay naturally
                damping = 1.0 - state.damper_position * 0.99
                if damping < 0.01:
                    state.oscillators.clear()

            out[i] = np.clip(sample, -1.0, 1.0)

        return out

    def _render_model_sample(self, _block_index: int, _block_size: int) -> float:
        """Render one sample of modal synthesis."""
        sample = 0.0
        dt = 1.0 / self.state.sample_rate
        for osc in self.state.oscillators:
            m = osc.mode
            w = 2.0 * np.pi * m.frequency
            # Damped harmonic oscillator: x'' + 2d*x' + w^2*x = 0
            # Discretized using velocity Verlet-like integration
            osc_velocity = osc.velocity
            osc_position = osc.position

            # Damping force + restoring force
            damping_force = 2.0 * m.decay_rate * osc_velocity
            restoring_force = w * w * osc_position

            # Update velocity (half-step)
            osc_velocity -= (damping_force + restoring_force) * dt * 0.5
            # Update position
            osc_position += osc_velocity * dt
            # Update velocity (half-step)
            osc_velocity -= (damping_force + restoring_force) * dt * 0.5

            osc.velocity = osc_velocity
            osc.position = osc_position

            sample += osc_position * m.amplitude * 0.1  # Scale to avoid clipping

        return float(sample)

    def note_off(self) -> None:
        """Transition to release phase."""
        self.state.phase = VoicePhase.RELEASE

    def set_damper(self, position: float) -> None:
        """Set continuous damper position (0.0=open, 1.0=fully damped)."""
        self.state.damper_position = max(0.0, min(1.0, position))
        if self.state.phase == VoicePhase.SUSTAIN and position > 0.8:
            self.note_off()

    def is_active(self) -> bool:
        """Voice is still producing audible output."""
        if self.state.phase == VoicePhase.RELEASE and not self.state.oscillators:
            return False
        return True
