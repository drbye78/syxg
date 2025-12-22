"""
Additive Synthesis Engine

Implements additive synthesis with up to 128 partials supporting real-time
harmonic control, morphing, and bandwidth optimization for high partial counts.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import math

from .synthesis_engine import SynthesisEngine
from ..partial.additive_partial import AdditivePartial


class AdditivePartialOscillator:
    """
    Single partial oscillator for additive synthesis.

    Each partial has independent frequency, amplitude, and phase control,
    with support for real-time parameter modulation.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize additive partial oscillator."""
        self.sample_rate = sample_rate

        # Frequency and amplitude parameters
        self.frequency_ratio = 1.0  # Ratio to fundamental frequency
        self.amplitude = 0.0        # Linear amplitude (0.0 to 1.0)
        self.phase = 0.0           # Current phase (0 to 2π)
        self.phase_offset = 0.0    # Phase offset in radians

        # Envelope parameters (simplified ADSR)
        self.attack_time = 0.01
        self.decay_time = 0.3
        self.sustain_level = 0.7
        self.release_time = 0.5
        self.envelope_phase = 'idle'

        # Envelope state
        self.envelope_value = 0.0
        self.envelope_time = 0.0

        # Modulation parameters
        self.amplitude_mod = 1.0
        self.frequency_mod = 0.0
        self.phase_mod = 0.0

    def set_parameters(self, params: Dict[str, Any]):
        """Set partial parameters."""
        self.frequency_ratio = params.get('frequency_ratio', 1.0)
        self.amplitude = params.get('amplitude', 0.0)
        self.phase_offset = params.get('phase_offset', 0.0)

        # Envelope parameters
        self.attack_time = params.get('attack_time', 0.01)
        self.decay_time = params.get('decay_time', 0.3)
        self.sustain_level = params.get('sustain_level', 0.7)
        self.release_time = params.get('release_time', 0.5)

    def note_on(self, velocity: int = 127):
        """Start partial envelope."""
        self.envelope_phase = 'attack'
        self.envelope_time = 0.0
        self.phase = self.phase_offset  # Reset phase to offset

    def note_off(self):
        """Start partial release."""
        self.envelope_phase = 'release'
        self.envelope_time = 0.0

    def update_envelope(self, dt: float):
        """Update envelope state."""
        self.envelope_time += dt

        if self.envelope_phase == 'attack':
            if self.envelope_time >= self.attack_time:
                self.envelope_value = 1.0
                self.envelope_phase = 'decay'
                self.envelope_time = 0.0
            else:
                self.envelope_value = self.envelope_time / self.attack_time

        elif self.envelope_phase == 'decay':
            if self.envelope_time >= self.decay_time:
                self.envelope_value = self.sustain_level
                self.envelope_phase = 'sustain'
            else:
                decay_progress = self.envelope_time / self.decay_time
                self.envelope_value = 1.0 - decay_progress * (1.0 - self.sustain_level)

        elif self.envelope_phase == 'sustain':
            self.envelope_value = self.sustain_level

        elif self.envelope_phase == 'release':
            if self.envelope_time >= self.release_time:
                self.envelope_value = 0.0
                self.envelope_phase = 'idle'
            else:
                release_progress = self.envelope_time / self.release_time
                self.envelope_value = self.sustain_level * (1.0 - release_progress)

        elif self.envelope_phase == 'idle':
            self.envelope_value = 0.0

    def generate_sample(self, base_frequency: float) -> float:
        """
        Generate partial sample.

        Args:
            base_frequency: Fundamental frequency

        Returns:
            Partial output sample
        """
        # Calculate instantaneous frequency with modulation
        frequency = base_frequency * self.frequency_ratio + self.frequency_mod

        # Update phase
        phase_increment = 2.0 * math.pi * frequency / self.sample_rate
        self.phase += phase_increment + self.phase_mod

        # Keep phase in reasonable range
        while self.phase > 2.0 * math.pi:
            self.phase -= 2.0 * math.pi
        while self.phase < 0:
            self.phase += 2.0 * math.pi

        # Generate sine wave
        sample = math.sin(self.phase)

        # Apply amplitude envelope and modulation
        sample *= self.amplitude * self.envelope_value * self.amplitude_mod

        return sample

    def is_active(self) -> bool:
        """Check if partial is still active."""
        return self.envelope_phase != 'idle'

    def reset(self):
        """Reset partial state."""
        self.phase = self.phase_offset
        self.envelope_phase = 'idle'
        self.envelope_value = 0.0
        self.envelope_time = 0.0


class HarmonicSpectrum:
    """
    Harmonic spectrum definition for additive synthesis.

    Defines amplitude and phase relationships for harmonics,
    supporting various spectral shapes and morphing.
    """

    def __init__(self, name: str = "custom"):
        """Initialize harmonic spectrum."""
        self.name = name
        self.harmonics: Dict[int, Dict[str, float]] = {}  # harmonic_number -> {'amplitude': float, 'phase': float}

    def set_harmonic(self, harmonic_number: int, amplitude: float, phase: float = 0.0):
        """Set parameters for a specific harmonic."""
        self.harmonics[harmonic_number] = {
            'amplitude': amplitude,
            'phase': phase
        }

    def get_harmonic(self, harmonic_number: int) -> Optional[Dict[str, float]]:
        """Get parameters for a specific harmonic."""
        return self.harmonics.get(harmonic_number)

    def clear(self):
        """Clear all harmonics."""
        self.harmonics.clear()

    def create_sawtooth(self, num_harmonics: int = 32):
        """Create sawtooth wave spectrum."""
        self.clear()
        for i in range(1, num_harmonics + 1):
            amplitude = 1.0 / i  # 1/n amplitude for each harmonic
            phase = 0.0 if i % 2 == 1 else math.pi  # Alternating phase
            self.set_harmonic(i, amplitude, phase)

    def create_square(self, num_harmonics: int = 32):
        """Create square wave spectrum."""
        self.clear()
        for i in range(1, num_harmonics + 1, 2):  # Only odd harmonics
            amplitude = 1.0 / i
            phase = 0.0
            self.set_harmonic(i, amplitude, phase)

    def create_triangle(self, num_harmonics: int = 32):
        """Create triangle wave spectrum."""
        self.clear()
        for i in range(1, num_harmonics + 1, 2):  # Only odd harmonics
            amplitude = 1.0 / (i * i)  # 1/n² amplitude
            phase = math.pi if (i // 2) % 2 == 1 else 0.0  # Alternating phase
            self.set_harmonic(i, amplitude, phase)

    def create_pulse(self, duty_cycle: float = 0.5, num_harmonics: int = 32):
        """Create pulse wave spectrum with variable duty cycle."""
        self.clear()
        for i in range(1, num_harmonics + 1):
            amplitude = math.sin(math.pi * i * duty_cycle) / (math.pi * i)
            phase = 0.0
            self.set_harmonic(i, amplitude, phase)

    def morph_to(self, target_spectrum: 'HarmonicSpectrum', morph_factor: float) -> 'HarmonicSpectrum':
        """
        Morph this spectrum towards another spectrum.

        Args:
            target_spectrum: Target spectrum to morph towards
            morph_factor: Morph factor (0.0 = this spectrum, 1.0 = target spectrum)

        Returns:
            Morphed spectrum
        """
        morphed = HarmonicSpectrum(f"{self.name}_morph")

        # Get all harmonic numbers from both spectra
        all_harmonics = set(self.harmonics.keys()) | set(target_spectrum.harmonics.keys())

        for harmonic in all_harmonics:
            source_harm = self.harmonics.get(harmonic, {'amplitude': 0.0, 'phase': 0.0})
            target_harm = target_spectrum.harmonics.get(harmonic, {'amplitude': 0.0, 'phase': 0.0})

            # Linear interpolation
            amplitude = source_harm['amplitude'] * (1.0 - morph_factor) + target_harm['amplitude'] * morph_factor
            phase = source_harm['phase'] * (1.0 - morph_factor) + target_harm['phase'] * morph_factor

            morphed.set_harmonic(harmonic, amplitude, phase)

        return morphed


class AdditiveEngine(SynthesisEngine):
    """
    Additive Synthesis Engine.

    Implements additive synthesis with up to 128 partials supporting:
    - Real-time harmonic control and morphing
    - Multiple predefined spectral shapes
    - Bandwidth optimization for high partial counts
    - Individual partial envelopes and modulation
    """

    def __init__(self, max_partials: int = 128, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize additive synthesis engine.

        Args:
            max_partials: Maximum number of partials (1-128)
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        super().__init__(sample_rate, block_size)
        self.max_partials = max(1, min(128, max_partials))

        # Initialize partial oscillators
        self.partials = [AdditivePartialOscillator(sample_rate) for _ in range(self.max_partials)]

        # Spectral control
        self.current_spectrum = HarmonicSpectrum("current")
        self.target_spectrum = HarmonicSpectrum("target")
        self.morph_factor = 0.0
        self.morph_time = 0.0
        self.morph_duration = 0.0

        # Global parameters
        self.master_volume = 1.0
        self.brightness = 1.0  # Spectral brightness control
        self.spread = 0.0      # Stereo spread control

        # Bandwidth optimization
        self.bandwidth_limit = 20000.0  # Hz
        self.partial_decay = 1.0         # How quickly higher partials decay

        # Initialize with sawtooth spectrum
        self.current_spectrum.create_sawtooth(min(32, self.max_partials))
        self.apply_spectrum_to_partials()

        # Voice state
        self.active_notes = {}
        self.current_note = 60
        self.current_velocity = 100

    def get_engine_info(self) -> Dict[str, Any]:
        """Get additive engine information."""
        return {
            'name': 'Additive Synthesis Engine',
            'type': 'additive',
            'capabilities': ['additive_synthesis', 'harmonic_control', 'spectral_morphing', 'bandwidth_optimization'],
            'formats': ['.add', '.harm'],  # Custom additive patch formats
            'polyphony': 8,  # Additive synthesis is very CPU intensive
            'parameters': ['spectrum_type', 'brightness', 'spread', 'morph_factor', 'bandwidth_limit'],
            'max_partials': self.max_partials
        }

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float], block_size: int) -> np.ndarray:
        """
        Generate additive synthesis audio samples.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Update current note and velocity
        self.current_note = note
        self.current_velocity = velocity

        # Calculate base frequency
        base_freq = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Apply pitch bend
        pitch_bend_semitones = modulation.get('pitch', 0.0) / 100.0  # Convert cents to semitones
        bend_ratio = 2.0 ** (pitch_bend_semitones / 12.0)
        base_freq *= bend_ratio

        # Update spectral morphing
        self.update_spectral_morphing(1.0 / self.sample_rate)

        # Generate samples
        left_output = np.zeros(block_size, dtype=np.float32)
        right_output = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Update envelopes for active partials
            dt = 1.0 / self.sample_rate
            for partial in self.partials:
                if partial.is_active():
                    partial.update_envelope(dt)

            # Generate and sum partials
            left_sample = 0.0
            right_sample = 0.0

            for partial_idx, partial in enumerate(self.partials):
                if partial.amplitude > 0.0 and partial.is_active():
                    # Generate partial sample
                    sample = partial.generate_sample(base_freq)

                    # Apply stereo spread based on partial index
                    if self.spread > 0.0:
                        # Higher partials are panned wider
                        pan_factor = (partial_idx / max(1, len(self.partials) - 1)) * self.spread
                        left_gain = 1.0 - pan_factor * 0.5
                        right_gain = 1.0 + pan_factor * 0.5
                        left_sample += sample * left_gain
                        right_sample += sample * right_gain
                    else:
                        # Mono
                        left_sample += sample
                        right_sample += sample

            # Apply master volume and velocity
            velocity_scale = velocity / 127.0
            master_scale = self.master_volume * velocity_scale

            left_output[i] = left_sample * master_scale
            right_output[i] = right_sample * master_scale

        # Combine into stereo buffer
        stereo_output = np.column_stack((left_output, right_output))

        return stereo_output

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported."""
        return 0 <= note <= 127

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> 'AdditivePartial':
        """Create additive partial."""
        from ..partial.additive_partial import AdditivePartial
        return AdditivePartial(partial_params, sample_rate)

    def set_spectrum_type(self, spectrum_type: str, num_harmonics: int = 32):
        """
        Set the current spectrum type.

        Args:
            spectrum_type: Type of spectrum ('sawtooth', 'square', 'triangle', 'pulse')
            num_harmonics: Number of harmonics to generate
        """
        num_harmonics = min(num_harmonics, self.max_partials)

        if spectrum_type == 'sawtooth':
            self.current_spectrum.create_sawtooth(num_harmonics)
        elif spectrum_type == 'square':
            self.current_spectrum.create_square(num_harmonics)
        elif spectrum_type == 'triangle':
            self.current_spectrum.create_triangle(num_harmonics)
        elif spectrum_type == 'pulse':
            self.current_spectrum.create_pulse(0.5, num_harmonics)
        else:
            # Custom spectrum - keep current
            return

        self.apply_spectrum_to_partials()

    def morph_to_spectrum(self, target_spectrum: HarmonicSpectrum, duration: float = 1.0):
        """
        Morph current spectrum to target spectrum over time.

        Args:
            target_spectrum: Target spectrum to morph to
            duration: Morph duration in seconds
        """
        self.target_spectrum = target_spectrum
        self.morph_duration = duration
        self.morph_time = 0.0
        self.morph_factor = 0.0

    def set_brightness(self, brightness: float):
        """
        Set spectral brightness (affects high-frequency content).

        Args:
            brightness: Brightness factor (0.0 = dark, 1.0 = bright, >1.0 = brighter)
        """
        self.brightness = max(0.0, brightness)
        self.apply_brightness_to_partials()

    def set_spread(self, spread: float):
        """
        Set stereo spread for partials.

        Args:
            spread: Spread factor (0.0 = mono, 1.0 = full stereo spread)
        """
        self.spread = max(0.0, min(1.0, spread))

    def set_partial_parameters(self, partial_idx: int, params: Dict[str, Any]):
        """
        Set parameters for a specific partial.

        Args:
            partial_idx: Partial index (0-127)
            params: Partial parameters
        """
        if 0 <= partial_idx < self.max_partials:
            self.partials[partial_idx].set_parameters(params)

    def get_partial_parameters(self, partial_idx: int) -> Dict[str, Any]:
        """
        Get parameters for a specific partial.

        Args:
            partial_idx: Partial index (0-127)

        Returns:
            Partial parameters dictionary
        """
        if 0 <= partial_idx < self.max_partials:
            partial = self.partials[partial_idx]
            return {
                'frequency_ratio': partial.frequency_ratio,
                'amplitude': partial.amplitude,
                'phase_offset': partial.phase_offset,
                'attack_time': partial.attack_time,
                'decay_time': partial.decay_time,
                'sustain_level': partial.sustain_level,
                'release_time': partial.release_time
            }
        return {}

    def apply_spectrum_to_partials(self):
        """Apply current spectrum to partial oscillators."""
        for harmonic_num, harmonic_data in self.current_spectrum.harmonics.items():
            if harmonic_num <= self.max_partials:
                partial_idx = harmonic_num - 1  # 0-based indexing
                amplitude = harmonic_data['amplitude']
                phase = harmonic_data['phase']

                # Apply bandwidth limiting and brightness
                if harmonic_num * 100.0 > self.bandwidth_limit:  # Rough estimate
                    amplitude *= 0.1  # Heavy attenuation

                # Apply brightness (boost high frequencies)
                if self.brightness != 1.0:
                    brightness_factor = 1.0 + (harmonic_num - 1) * (self.brightness - 1.0) * 0.1
                    amplitude *= brightness_factor

                # Apply partial decay (higher partials decay faster)
                decay_factor = 1.0 / (1.0 + (harmonic_num - 1) * self.partial_decay * 0.01)
                amplitude *= decay_factor

                self.partials[partial_idx].set_parameters({
                    'frequency_ratio': float(harmonic_num),
                    'amplitude': amplitude,
                    'phase_offset': phase
                })

    def apply_brightness_to_partials(self):
        """Reapply brightness to current spectrum."""
        self.apply_spectrum_to_partials()

    def update_spectral_morphing(self, dt: float):
        """Update spectral morphing state."""
        if self.morph_duration > 0.0 and self.morph_time < self.morph_duration:
            self.morph_time += dt
            self.morph_factor = min(1.0, self.morph_time / self.morph_duration)

            # Create morphed spectrum
            morphed_spectrum = self.current_spectrum.morph_to(self.target_spectrum, self.morph_factor)

            # Apply morphed spectrum
            for harmonic_num, harmonic_data in morphed_spectrum.harmonics.items():
                if harmonic_num <= self.max_partials:
                    partial_idx = harmonic_num - 1
                    self.partials[partial_idx].set_parameters({
                        'frequency_ratio': float(harmonic_num),
                        'amplitude': harmonic_data['amplitude'],
                        'phase_offset': harmonic_data['phase']
                    })

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        self.active_notes[note] = velocity
        self.current_note = note
        self.current_velocity = velocity

        # Start envelopes for active partials
        for partial in self.partials:
            if partial.amplitude > 0.0:
                partial.note_on(velocity)

    def note_off(self, note: int):
        """Handle note-off event."""
        if note in self.active_notes:
            del self.active_notes[note]

        # Start release for active partials
        for partial in self.partials:
            if partial.is_active():
                partial.note_off()

    def is_active(self) -> bool:
        """Check if engine is active."""
        return any(partial.is_active() for partial in self.partials)

    def reset(self):
        """Reset engine state."""
        self.active_notes.clear()
        for partial in self.partials:
            partial.reset()

    def get_supported_formats(self) -> List[str]:
        """Get supported file formats."""
        return ['.add', '.harm']

    def load_preset(self, preset_data: Dict[str, Any]):
        """
        Load additive preset data.

        Args:
            preset_data: Preset parameters dictionary
        """
        # Set spectrum type
        spectrum_type = preset_data.get('spectrum_type', 'sawtooth')
        num_harmonics = preset_data.get('num_harmonics', 32)
        self.set_spectrum_type(spectrum_type, num_harmonics)

        # Set global parameters
        self.master_volume = preset_data.get('master_volume', 1.0)
        self.brightness = preset_data.get('brightness', 1.0)
        self.spread = preset_data.get('spread', 0.0)
        self.bandwidth_limit = preset_data.get('bandwidth_limit', 20000.0)

        # Apply settings
        self.apply_brightness_to_partials()

    def save_preset(self) -> Dict[str, Any]:
        """
        Save current preset data.

        Returns:
            Preset parameters dictionary
        """
        return {
            'spectrum_type': 'custom',  # Could be improved to detect type
            'num_harmonics': len(self.current_spectrum.harmonics),
            'master_volume': self.master_volume,
            'brightness': self.brightness,
            'spread': self.spread,
            'bandwidth_limit': self.bandwidth_limit,
            'harmonics': self.current_spectrum.harmonics.copy()
        }

    def get_spectrum_info(self) -> Dict[str, Any]:
        """Get current spectrum information."""
        return {
            'name': self.current_spectrum.name,
            'num_harmonics': len(self.current_spectrum.harmonics),
            'morph_factor': self.morph_factor,
            'brightness': self.brightness,
            'spread': self.spread,
            'bandwidth_limit': self.bandwidth_limit
        }
