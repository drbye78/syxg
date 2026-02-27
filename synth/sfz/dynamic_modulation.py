"""
SFZ Dynamic Parameter Modulation System

Provides real-time modulation from audio signals including envelope followers,
sidechain detection, and audio-derived modulation sources.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import math


class EnvelopeFollower:
    """
    Audio envelope follower for extracting modulation from audio signals.

    Tracks the amplitude envelope of an audio signal to create smooth
    modulation signals suitable for dynamic parameter control.
    """

    def __init__(self, sample_rate: int, attack_time: float = 0.01,
                 release_time: float = 0.1, hold_time: float = 0.0):
        """
        Initialize envelope follower.

        Args:
            sample_rate: Audio sample rate in Hz
            attack_time: Attack time in seconds
            release_time: Release time in seconds
            hold_time: Hold time in seconds
        """
        self.sample_rate = sample_rate
        self.attack_time = attack_time
        self.release_time = release_time
        self.hold_time = hold_time

        # Calculate coefficients
        self.attack_coeff = self._time_to_coeff(attack_time)
        self.release_coeff = self._time_to_coeff(release_time)

        # State
        self.envelope = 0.0
        self.hold_counter = 0
        self.hold_samples = int(hold_time * sample_rate)

        # Peak hold tracking
        self.peak_value = 0.0
        self.peak_decay_coeff = self._time_to_coeff(0.5)  # 500ms peak decay

    def _time_to_coeff(self, time_seconds: float) -> float:
        """Convert time to filter coefficient."""
        if time_seconds <= 0:
            return 1.0
        return 1.0 - math.exp(-1.0 / (time_seconds * self.sample_rate))

    def process(self, audio: np.ndarray) -> float:
        """
        Process audio block and return current envelope value.

        Args:
            audio: Audio buffer (can be mono or stereo)

        Returns:
            Current envelope value (0.0-1.0)
        """
        # Convert to mono if stereo
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=1)
        else:
            audio_mono = audio

        # Calculate RMS of the block
        rms = np.sqrt(np.mean(audio_mono ** 2))

        # Update peak tracking
        if rms > self.peak_value:
            self.peak_value = rms
            self.hold_counter = self.hold_samples
        else:
            # Decay peak during hold
            if self.hold_counter > 0:
                self.hold_counter -= 1
                self.peak_value *= (1.0 - self.peak_decay_coeff)
            else:
                self.peak_value *= (1.0 - self.peak_decay_coeff)

        # Use peak value for envelope following
        target = self.peak_value

        # Apply attack/release
        if target > self.envelope:
            # Attack
            self.envelope += (target - self.envelope) * self.attack_coeff
        else:
            # Release
            self.envelope += (target - self.envelope) * self.release_coeff

        # Normalize to 0.0-1.0 (assuming peak level around 1.0)
        return min(1.0, self.envelope)

    def reset(self) -> None:
        """Reset envelope follower state."""
        self.envelope = 0.0
        self.peak_value = 0.0
        self.hold_counter = 0


class SidechainDetector:
    """
    Sidechain detector for dynamic range compression and modulation.

    Detects audio signal levels for sidechain modulation, useful for
    pumping effects, ducking, and dynamic parameter control.
    """

    def __init__(self, sample_rate: int, attack_time: float = 0.001,
                 release_time: float = 0.1, ratio: float = 4.0,
                 threshold: float = 0.5):
        """
        Initialize sidechain detector.

        Args:
            sample_rate: Audio sample rate in Hz
            attack_time: Attack time in seconds
            release_time: Release time in seconds
            ratio: Compression ratio
            threshold: Compression threshold (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self.attack_time = attack_time
        self.release_time = release_time
        self.ratio = ratio
        self.threshold = threshold

        # Calculate coefficients
        self.attack_coeff = self._time_to_coeff(attack_time)
        self.release_coeff = self._time_to_coeff(release_time)

        # State
        self.envelope = 0.0

    def _time_to_coeff(self, time_seconds: float) -> float:
        """Convert time to filter coefficient."""
        if time_seconds <= 0:
            return 1.0
        return 1.0 - math.exp(-1.0 / (time_seconds * self.sample_rate))

    def process(self, audio: np.ndarray) -> float:
        """
        Process audio block and return sidechain modulation value.

        Args:
            audio: Audio buffer (can be mono or stereo)

        Returns:
            Sidechain modulation value (0.0-1.0, higher = more compression)
        """
        # Convert to mono if stereo
        if audio.ndim == 2:
            audio_mono = np.mean(audio, axis=1)
        else:
            audio_mono = audio

        # Calculate RMS of the block
        rms = np.sqrt(np.mean(audio_mono ** 2))

        # Apply compression curve
        if rms > self.threshold:
            # Above threshold - apply compression
            over_threshold = rms - self.threshold
            compressed = self.threshold + over_threshold / self.ratio
            target = compressed / rms if rms > 0 else 0
        else:
            # Below threshold - no compression
            target = 1.0

        # Smooth envelope
        if target < self.envelope:
            # Attack (signal getting louder)
            self.envelope += (target - self.envelope) * self.attack_coeff
        else:
            # Release (signal getting quieter)
            self.envelope += (target - self.envelope) * self.release_coeff

        # Return compression amount (0.0 = no compression, 1.0 = full compression)
        return 1.0 - self.envelope

    def reset(self) -> None:
        """Reset sidechain detector state."""
        self.envelope = 0.0


class RandomModulation:
    """
    Random modulation generator with sample & hold characteristics.

    Generates random values that change at specified intervals,
    suitable for adding variation and unpredictability to sounds.
    """

    def __init__(self, sample_rate: int, change_rate: float = 2.0,
                 smooth_changes: bool = True):
        """
        Initialize random modulation.

        Args:
            sample_rate: Audio sample rate in Hz
            change_rate: Rate of value changes in Hz
            smooth_changes: Whether to smooth transitions between values
        """
        self.sample_rate = sample_rate
        self.change_rate = change_rate
        self.smooth_changes = smooth_changes

        # State
        self.current_value = 0.0
        self.target_value = 0.0
        self.smooth_counter = 0

        # Calculate samples between changes
        self.samples_per_change = int(sample_rate / change_rate)
        self.sample_counter = 0

        # Smoothing
        self.smooth_samples = int(sample_rate * 0.05)  # 50ms smoothing
        self.smooth_step = 0.0

    def generate(self, block_size: int) -> np.ndarray:
        """
        Generate random modulation values for a block.

        Args:
            block_size: Number of samples to generate

        Returns:
            Array of modulation values (-1.0 to 1.0)
        """
        output = np.zeros(block_size)

        for i in range(block_size):
            # Check if we need a new random value
            if self.sample_counter >= self.samples_per_change:
                self.target_value = (np.random.random() - 0.5) * 2.0  # -1.0 to 1.0
                self.sample_counter = 0

                if self.smooth_changes:
                    self.smooth_step = (self.target_value - self.current_value) / self.smooth_samples
                    self.smooth_counter = self.smooth_samples
                else:
                    self.current_value = self.target_value

            # Apply smoothing if active
            if self.smooth_changes and self.smooth_counter > 0:
                self.current_value += self.smooth_step
                self.smooth_counter -= 1

                # Clamp to prevent overshoot
                if (self.smooth_step > 0 and self.current_value > self.target_value) or \
                   (self.smooth_step < 0 and self.current_value < self.target_value):
                    self.current_value = self.target_value
                    self.smooth_counter = 0

            output[i] = self.current_value
            self.sample_counter += 1

        return output

    def reset(self) -> None:
        """Reset random modulation state."""
        self.current_value = 0.0
        self.target_value = 0.0
        self.sample_counter = self.samples_per_change  # Force immediate change
        self.smooth_counter = 0


class NoiseModulation:
    """
    Noise-based modulation generator with different noise colors.

    Generates filtered noise suitable for modulation purposes,
    including white noise, pink noise, and brown noise.
    """

    def __init__(self, sample_rate: int, noise_type: str = 'white',
                 filter_cutoff: float = 1000.0):
        """
        Initialize noise modulation.

        Args:
            sample_rate: Audio sample rate in Hz
            noise_type: Type of noise ('white', 'pink', 'brown')
            filter_cutoff: Low-pass filter cutoff for smoothing
        """
        self.sample_rate = sample_rate
        self.noise_type = noise_type
        self.filter_cutoff = filter_cutoff

        # Noise generation state
        self.white_noise = np.random.normal(0, 1, 1024)  # Pre-generate white noise
        self.noise_index = 0

        # Pink noise state (Paul Kellet's algorithm)
        self.pink_b = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Brown noise state
        self.brown_value = 0.0

        # Filtering
        self.filter_state = 0.0
        self.filter_coeff = self._calculate_filter_coeff()

    def _calculate_filter_coeff(self) -> float:
        """Calculate filter coefficient from cutoff frequency."""
        if self.filter_cutoff <= 0:
            return 1.0
        return 1.0 - math.exp(-2.0 * math.pi * self.filter_cutoff / self.sample_rate)

    def generate_white(self, block_size: int) -> np.ndarray:
        """
        Generate white noise modulation.

        Args:
            block_size: Number of samples to generate

        Returns:
            Array of white noise values (-1.0 to 1.0)
        """
        output = np.zeros(block_size)

        for i in range(block_size):
            # Get white noise sample
            noise = self.white_noise[self.noise_index]
            self.noise_index = (self.noise_index + 1) % len(self.white_noise)

            # Apply low-pass filtering for smoothing
            self.filter_state += (noise - self.filter_state) * self.filter_coeff
            output[i] = self.filter_state

        # Normalize to approximately -1.0 to 1.0
        return output / 3.0

    def generate_pink(self, block_size: int) -> np.ndarray:
        """
        Generate pink noise modulation using Paul Kellet's algorithm.

        Args:
            block_size: Number of samples to generate

        Returns:
            Array of pink noise values (-1.0 to 1.0)
        """
        output = np.zeros(block_size)

        for i in range(block_size):
            # Generate white noise
            white = np.random.normal(0, 1)

            # Pink noise filter (Paul Kellet's algorithm)
            self.pink_b[0] = 0.99886 * self.pink_b[0] + white * 0.0555179
            self.pink_b[1] = 0.99332 * self.pink_b[1] + white * 0.0750759
            self.pink_b[2] = 0.96900 * self.pink_b[2] + white * 0.1538520
            self.pink_b[3] = 0.86650 * self.pink_b[3] + white * 0.3104856
            self.pink_b[4] = 0.55000 * self.pink_b[4] + white * 0.5329522
            self.pink_b[5] = -0.7616 * self.pink_b[5] - white * 0.0168980
            pink = (self.pink_b[0] + self.pink_b[1] + self.pink_b[2] + self.pink_b[3] +
                   self.pink_b[4] + self.pink_b[5] + self.pink_b[6] + white * 0.5362)
            self.pink_b[6] = white * 0.115926

            # Apply low-pass filtering
            self.filter_state += (pink - self.filter_state) * self.filter_coeff
            output[i] = self.filter_state

        # Normalize
        return output / 5.0

    def generate_brown(self, block_size: int) -> np.ndarray:
        """
        Generate brown noise modulation (random walk).

        Args:
            block_size: Number of samples to generate

        Returns:
            Array of brown noise values (-1.0 to 1.0)
        """
        output = np.zeros(block_size)

        for i in range(block_size):
            # Generate small random step
            step = np.random.normal(0, 0.01)  # Small step size

            # Update brown noise value
            self.brown_value += step

            # Clamp to reasonable range
            self.brown_value = max(-2.0, min(2.0, self.brown_value))

            # Apply low-pass filtering
            self.filter_state += (self.brown_value - self.filter_state) * self.filter_coeff
            output[i] = self.filter_state

        return output

    def generate(self, block_size: int) -> np.ndarray:
        """
        Generate noise modulation based on configured type.

        Args:
            block_size: Number of samples to generate

        Returns:
            Array of noise modulation values (-1.0 to 1.0)
        """
        if self.noise_type == 'pink':
            return self.generate_pink(block_size)
        elif self.noise_type == 'brown':
            return self.generate_brown(block_size)
        else:  # default to white
            return self.generate_white(block_size)

    def reset(self) -> None:
        """Reset noise modulation state."""
        self.filter_state = 0.0
        self.brown_value = 0.0
        self.pink_b = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.noise_index = 0


class ExternalModulation:
    """
    External modulation input processor.

    Handles modulation signals from external sources such as
    CV inputs, audio interfaces, or other modulation devices.
    """

    def __init__(self, sample_rate: int, smoothing: float = 0.1):
        """
        Initialize external modulation processor.

        Args:
            sample_rate: Audio sample rate in Hz
            smoothing: Smoothing time in seconds
        """
        self.sample_rate = sample_rate
        self.smoothing = smoothing

        # State
        self.current_value = 0.0
        self.smooth_coeff = self._time_to_coeff(smoothing)

    def _time_to_coeff(self, time_seconds: float) -> float:
        """Convert time to filter coefficient."""
        if time_seconds <= 0:
            return 1.0
        return 1.0 - math.exp(-1.0 / (time_seconds * self.sample_rate))

    def process_input(self, external_value: float) -> float:
        """
        Process external modulation input value.

        Args:
            external_value: External modulation value (-1.0 to 1.0)

        Returns:
            Smoothed modulation value
        """
        # Apply smoothing
        self.current_value += (external_value - self.current_value) * self.smooth_coeff
        return self.current_value

    def generate(self, block_size: int) -> np.ndarray:
        """
        Generate modulation block (for compatibility with other generators).

        In a real implementation, this would get values from external sources.
        For now, returns constant current value.

        Args:
            block_size: Number of samples to generate

        Returns:
            Array filled with current modulation value
        """
        return np.full(block_size, self.current_value)

    def reset(self) -> None:
        """Reset external modulation state."""
        self.current_value = 0.0


class SFZDynamicModulation:
    """
    Complete dynamic modulation system for SFZ instruments.

    Combines envelope followers, sidechain detection, random modulation,
    and external inputs to provide comprehensive dynamic modulation capabilities.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize dynamic modulation system.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Initialize modulation sources
        self.envelope_follower = EnvelopeFollower(sample_rate)
        self.sidechain_detector = SidechainDetector(sample_rate)
        self.random_generator = RandomModulation(sample_rate)
        self.noise_generator = NoiseModulation(sample_rate)
        self.external_input = ExternalModulation(sample_rate)

        # Configuration
        self.enabled_sources = {
            'envelope_follower': True,
            'sidechain_detector': True,
            'random_modulation': True,
            'noise_modulation': True,
            'external_input': False  # Disabled by default
        }

    def process_audio_modulation(self, audio: np.ndarray,
                               modulation_params: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Process audio signal and generate dynamic modulation sources.

        Args:
            audio: Audio buffer to analyze
            modulation_params: Modulation configuration parameters

        Returns:
            Dictionary of modulation source arrays
        """
        modulation_outputs = {}

        # Envelope following
        if self.enabled_sources['envelope_follower'] and 'envelope_follow' in modulation_params:
            envelope_value = self.envelope_follower.process(audio)
            # Convert to array for consistency
            block_size = len(audio) if audio.ndim == 1 else len(audio)
            modulation_outputs['audio_envelope'] = np.full(block_size, envelope_value)

        # Sidechain detection
        if self.enabled_sources['sidechain_detector'] and 'sidechain' in modulation_params:
            sidechain_value = self.sidechain_detector.process(audio)
            block_size = len(audio) if audio.ndim == 1 else len(audio)
            modulation_outputs['sidechain_level'] = np.full(block_size, sidechain_value)

        # Random modulation
        if self.enabled_sources['random_modulation'] and 'random' in modulation_params:
            block_size = len(audio) if audio.ndim == 1 else len(audio)
            modulation_outputs['random'] = self.random_generator.generate(block_size)

        # Noise modulation
        if self.enabled_sources['noise_modulation'] and 'noise' in modulation_params:
            block_size = len(audio) if audio.ndim == 1 else len(audio)
            modulation_outputs['noise'] = self.noise_generator.generate(block_size)

        # External input (would be updated from external source)
        if self.enabled_sources['external_input'] and 'external' in modulation_params:
            block_size = len(audio) if audio.ndim == 1 else len(audio)
            modulation_outputs['external'] = self.external_input.generate(block_size)

        return modulation_outputs

    def update_external_input(self, value: float) -> None:
        """
        Update external modulation input value.

        Args:
            value: New external modulation value (-1.0 to 1.0)
        """
        self.external_input.process_input(value)

    def configure_source(self, source_name: str, enabled: bool,
                        **kwargs) -> bool:
        """
        Configure a modulation source.

        Args:
            source_name: Name of the modulation source
            enabled: Whether the source is enabled
            **kwargs: Additional configuration parameters

        Returns:
            True if configuration was successful
        """
        if source_name not in self.enabled_sources:
            return False

        self.enabled_sources[source_name] = enabled

        # Apply additional configuration
        if source_name == 'envelope_follower':
            if 'attack' in kwargs:
                self.envelope_follower = EnvelopeFollower(
                    self.sample_rate,
                    attack_time=kwargs['attack'],
                    release_time=kwargs.get('release', 0.1)
                )
        elif source_name == 'sidechain_detector':
            if 'attack' in kwargs:
                self.sidechain_detector = SidechainDetector(
                    self.sample_rate,
                    attack_time=kwargs['attack'],
                    release_time=kwargs.get('release', 0.1)
                )
        elif source_name == 'random_modulation':
            if 'rate' in kwargs:
                self.random_generator = RandomModulation(
                    self.sample_rate,
                    change_rate=kwargs['rate']
                )
        elif source_name == 'noise_modulation':
            if 'type' in kwargs:
                self.noise_generator = NoiseModulation(
                    self.sample_rate,
                    noise_type=kwargs['type']
                )

        return True

    def get_modulation_info(self) -> dict[str, Any]:
        """
        Get information about modulation sources and their status.

        Returns:
            Dictionary with modulation system information
        """
        return {
            'sample_rate': self.sample_rate,
            'enabled_sources': self.enabled_sources.copy(),
            'envelope_follower': {
                'attack_time': self.envelope_follower.attack_time,
                'release_time': self.envelope_follower.release_time,
                'current_envelope': self.envelope_follower.envelope
            },
            'sidechain_detector': {
                'attack_time': self.sidechain_detector.attack_time,
                'release_time': self.sidechain_detector.release_time,
                'current_envelope': self.sidechain_detector.envelope
            },
            'random_modulation': {
                'change_rate': self.random_generator.change_rate,
                'current_value': self.random_generator.current_value
            },
            'noise_modulation': {
                'noise_type': self.noise_generator.noise_type,
                'filter_cutoff': self.noise_generator.filter_cutoff
            },
            'external_input': {
                'current_value': self.external_input.current_value,
                'smoothing': self.external_input.smoothing
            }
        }

    def reset_all_sources(self) -> None:
        """Reset all modulation sources to their initial state."""
        self.envelope_follower.reset()
        self.sidechain_detector.reset()
        self.random_generator.reset()
        self.noise_generator.reset()
        self.external_input.reset()

    def get_available_sources(self) -> list[str]:
        """
        Get list of available modulation sources.

        Returns:
            List of modulation source names
        """
        return [
            'audio_envelope',  # From envelope follower
            'sidechain_level', # From sidechain detector
            'random',          # Random modulation
            'noise',           # Noise modulation
            'external'         # External input
        ]

    def __str__(self) -> str:
        """String representation."""
        enabled = [name for name, enabled in self.enabled_sources.items() if enabled]
        return f"SFZDynamicModulation(sources={enabled})"

    def __repr__(self) -> str:
        return self.__str__()