"""Wavetable oscillator."""
from __future__ import annotations
import numpy as np
from .wavetable import Wavetable
class WavetableOscillator:
    """
    Wavetable oscillator with frequency control and modulation.

    Provides efficient wavetable playback with pitch modulation,
    amplitude control, and multi-timbral capabilities.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.wavetable: Wavetable | None = None

        # Oscillator state
        self.phase = 0.0
        self.frequency = 440.0
        self.amplitude = 1.0

        # Modulation inputs
        self.frequency_mod = 0.0
        self.amplitude_mod = 0.0
        self.wavetable_position = 0.0  # For wavetable morphing

        # Voice state
        self.active = False
        self.note = 60
        self.velocity = 100

    def set_wavetable(self, wavetable: Wavetable):
        """Set the wavetable for this oscillator."""
        self.wavetable = wavetable

    def set_frequency(self, frequency: float):
        """Set base frequency in Hz."""
        self.frequency = max(20.0, min(frequency, self.sample_rate / 2.0))

    def set_note(self, midi_note: int, velocity: int = 100):
        """Set oscillator to specific MIDI note."""
        self.note = midi_note
        self.velocity = velocity
        self.active = True

        # Convert MIDI note to frequency
        self.frequency = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

        # Apply velocity to amplitude
        self.amplitude = (velocity / 127.0) ** 0.3  # Slight compression

    def set_amplitude(self, amplitude: float):
        """Set amplitude (0.0 to 1.0)."""
        self.amplitude = max(0.0, min(amplitude, 1.0))

    def update_modulation(self, freq_mod: float = 0.0, amp_mod: float = 0.0, wt_pos: float = 0.0):
        """Update modulation inputs."""
        self.frequency_mod = freq_mod
        self.amplitude_mod = amp_mod
        self.wavetable_position = wt_pos

    def generate_samples(self, block_size: int) -> np.ndarray:
        """
        Generate audio samples for this oscillator.

        Args:
            block_size: Number of samples to generate

        Returns:
            Audio buffer (block_size,)
        """
        if not self.wavetable or not self.active:
            return np.zeros(block_size, dtype=np.float32)

        # Calculate phase increment
        base_increment = self.frequency / self.sample_rate
        modulated_freq = self.frequency * (1.0 + self.frequency_mod)
        phase_increment = modulated_freq / self.sample_rate

        # Generate phases
        phases = np.zeros(block_size)
        current_phase = self.phase

        for i in range(block_size):
            phases[i] = current_phase
            current_phase = (current_phase + phase_increment) % 1.0

        # Update oscillator phase
        self.phase = current_phase

        # Get samples from wavetable
        samples = self.wavetable.get_samples(phases)

        # Apply amplitude modulation
        modulated_amplitude = self.amplitude * (1.0 + self.amplitude_mod)
        samples *= modulated_amplitude

        return samples.astype(np.float32)

    def is_active(self) -> bool:
        """Check if oscillator is active."""
        return self.active

    def note_off(self):
        """Trigger note off (oscillator will continue until released)."""
        self.active = False

    def reset(self):
        """Reset oscillator state."""
        self.phase = 0.0
        self.frequency_mod = 0.0
        self.amplitude_mod = 0.0
        self.active = False


