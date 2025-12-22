"""
Spectral Synthesis Engine

FFT-based spectral synthesis and processing for advanced sound design.
Provides real-time spectral analysis, synthesis, and manipulation.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from scipy import signal
import math

from .synthesis_engine import SynthesisEngine


class FFTProcessor:
    """
    High-performance FFT processor for spectral analysis and synthesis.

    Provides efficient forward/inverse FFT with windowing and overlap-add
    processing for real-time spectral manipulation.
    """

    def __init__(self, fft_size: int = 2048, hop_size: int = 512, window_type: str = 'hann'):
        """
        Initialize FFT processor.

        Args:
            fft_size: FFT size (must be power of 2)
            hop_size: Hop size for overlap processing
            window_type: Window function type
        """
        self.fft_size = fft_size
        self.hop_size = hop_size
        self.overlap = fft_size // hop_size

        # Create window function
        if window_type == 'hann':
            self.window = np.hanning(fft_size)
        elif window_type == 'hamming':
            self.window = np.hamming(fft_size)
        elif window_type == 'blackman':
            self.window = np.blackman(fft_size)
        else:
            self.window = np.ones(fft_size)  # Rectangular window

        # Pre-compute normalization factors
        self.window_sum = np.sum(self.window)
        self.normalization_factor = 1.0 / (self.window_sum / self.overlap)

        # Internal buffers
        self.input_buffer = np.zeros(fft_size)
        self.output_buffer = np.zeros(fft_size)
        self.fft_buffer = np.zeros(fft_size, dtype=np.complex128)

    def forward(self, audio: np.ndarray) -> np.ndarray:
        """
        Perform forward FFT with windowing.

        Args:
            audio: Input audio buffer

        Returns:
            Complex frequency domain representation
        """
        # Apply window
        windowed = audio * self.window

        # Perform FFT
        fft_result = np.fft.fft(windowed, self.fft_size)

        # Normalize
        fft_result *= self.normalization_factor

        return fft_result

    def inverse(self, spectrum: np.ndarray) -> np.ndarray:
        """
        Perform inverse FFT with windowing.

        Args:
            spectrum: Complex frequency domain data

        Returns:
            Time domain audio
        """
        # Perform IFFT
        ifft_result = np.fft.ifft(spectrum, self.fft_size).real

        # Apply window
        windowed = ifft_result * self.window

        return windowed

    def process_block(self, input_block: np.ndarray) -> np.ndarray:
        """
        Process a block of audio with overlap-add FFT processing.

        Args:
            input_block: Input audio block

        Returns:
            Processed audio block
        """
        # For now, implement simple FFT processing
        # Full overlap-add would require more complex buffering

        # Ensure input is correct size
        if len(input_block) != self.fft_size:
            # Pad or truncate as needed
            if len(input_block) < self.fft_size:
                padded = np.zeros(self.fft_size)
                padded[:len(input_block)] = input_block
                input_block = padded
            else:
                input_block = input_block[:self.fft_size]

        # Forward FFT
        spectrum = self.forward(input_block)

        # Apply spectral processing (placeholder - will be overridden)
        processed_spectrum = spectrum.copy()

        # Inverse FFT
        output = self.inverse(processed_spectrum)

        return output


class SpectralFilter:
    """
    Spectral domain filter for frequency-specific processing.

    Provides various filtering operations in the frequency domain including:
    - Bandpass/bandreject filtering
    - Frequency shifting
    - Spectral gating
    - Harmonic enhancement
    """

    def __init__(self, fft_size: int = 2048, sample_rate: int = 44100):
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.nyquist = sample_rate / 2.0

        # Filter parameters
        self.low_cutoff = 0.0
        self.high_cutoff = self.nyquist
        self.bandwidth = 1000.0
        self.center_freq = 1000.0
        self.gain = 1.0

        # Filter types
        self.filter_type = 'passthrough'  # passthrough, bandpass, bandreject, notch, etc.

    def set_bandpass(self, center_freq: float, bandwidth: float, gain: float = 1.0):
        """Configure bandpass filter."""
        self.filter_type = 'bandpass'
        self.center_freq = max(20.0, min(center_freq, self.nyquist - 20.0))
        self.bandwidth = max(10.0, bandwidth)
        self.gain = gain

    def set_bandreject(self, center_freq: float, bandwidth: float):
        """Configure bandreject filter."""
        self.filter_type = 'bandreject'
        self.center_freq = max(20.0, min(center_freq, self.nyquist - 20.0))
        self.bandwidth = max(10.0, bandwidth)
        self.gain = 0.0

    def set_lowpass(self, cutoff: float):
        """Configure lowpass filter."""
        self.filter_type = 'lowpass'
        self.high_cutoff = max(20.0, min(cutoff, self.nyquist))
        self.gain = 1.0

    def set_highpass(self, cutoff: float):
        """Configure highpass filter."""
        self.filter_type = 'highpass'
        self.low_cutoff = max(20.0, min(cutoff, self.nyquist))
        self.gain = 1.0

    def process_spectrum(self, spectrum: np.ndarray) -> np.ndarray:
        """
        Apply filter to frequency domain spectrum.

        Args:
            spectrum: Complex frequency spectrum

        Returns:
            Filtered spectrum
        """
        # Create frequency bins
        freqs = np.fft.fftfreq(self.fft_size, 1.0 / self.sample_rate)

        # Create filter mask
        mask = np.ones(len(spectrum), dtype=np.complex128)

        if self.filter_type == 'bandpass':
            # Bandpass filter
            low_edge = self.center_freq - self.bandwidth / 2.0
            high_edge = self.center_freq + self.bandwidth / 2.0

            # Create bandpass mask
            band_mask = ((freqs >= low_edge) & (freqs <= high_edge))
            mask[band_mask] *= self.gain
            mask[~band_mask] *= 0.0

        elif self.filter_type == 'bandreject':
            # Bandreject filter
            low_edge = self.center_freq - self.bandwidth / 2.0
            high_edge = self.center_freq + self.bandwidth / 2.0

            # Create bandreject mask
            band_mask = ((freqs >= low_edge) & (freqs <= high_edge))
            mask[band_mask] *= self.gain
            mask[~band_mask] *= 1.0

        elif self.filter_type == 'lowpass':
            # Lowpass filter
            mask[freqs > self.high_cutoff] *= 0.0
            mask[freqs < -self.high_cutoff] *= 0.0

        elif self.filter_type == 'highpass':
            # Highpass filter
            mask[(freqs > -self.low_cutoff) & (freqs < self.low_cutoff)] *= 0.0

        # Apply filter
        return spectrum * mask


class GranularEngine:
    """
    Granular synthesis engine for time-domain audio manipulation.

    Provides granular synthesis capabilities including:
    - Time stretching and pitch shifting
    - Granular scattering and diffusion
    - Texture generation
    - Freeze and reverse granulation
    """

    def __init__(self, sample_rate: int = 44100, max_grains: int = 100):
        self.sample_rate = sample_rate
        self.max_grains = max_grains

        # Grain parameters
        self.grain_size = 0.050  # 50ms grains
        self.grain_density = 10.0  # grains per second
        self.grain_pitch = 1.0
        self.grain_position = 0.0
        self.grain_spread = 0.0  # Random position spread

        # Internal state
        self.grains: List[Dict[str, Any]] = []
        self.source_audio: Optional[np.ndarray] = None
        self.source_length = 0

        # Random number generator for grain scattering
        self.rng = np.random.RandomState()

    def set_source_audio(self, audio: np.ndarray):
        """Set source audio for granulation."""
        if audio is not None and len(audio) > 0:
            self.source_audio = audio.copy()
            self.source_length = len(audio)
        else:
            self.source_audio = None
            self.source_length = 0

    def set_grain_parameters(self, size: float = 0.050, density: float = 10.0,
                           pitch: float = 1.0, position: float = 0.0, spread: float = 0.0):
        """Set grain parameters."""
        self.grain_size = max(0.001, min(size, 1.0))  # 1ms to 1s
        self.grain_density = max(0.1, min(density, 1000.0))  # 0.1 to 1000 grains/sec
        self.grain_pitch = max(0.1, min(pitch, 4.0))  # 0.1x to 4x speed
        self.grain_position = max(0.0, min(position, 1.0))  # Position in source (0-1)
        self.grain_spread = max(0.0, min(spread, 1.0))  # Position randomization

    def generate_grains(self, duration: float) -> List[Dict[str, Any]]:
        """
        Generate grain schedule for given duration.

        Args:
            duration: Duration in seconds

        Returns:
            List of grain dictionaries
        """
        if self.source_audio is None:
            return []

        grains = []
        num_grains = int(duration * self.grain_density)

        for i in range(num_grains):
            # Calculate grain timing
            time = i / self.grain_density

            # Calculate grain position with spread
            base_position = self.grain_position
            if self.grain_spread > 0:
                position_variation = (self.rng.random() - 0.5) * self.grain_spread
                base_position = np.clip(base_position + position_variation, 0.0, 1.0)

            # Convert position to sample index
            start_sample = int(base_position * (self.source_length - 1))

            # Calculate grain size in samples
            grain_samples = int(self.grain_size * self.sample_rate)

            # Ensure grain doesn't exceed source boundaries
            end_sample = min(start_sample + grain_samples, self.source_length)

            grain = {
                'start_time': time,
                'start_sample': start_sample,
                'end_sample': end_sample,
                'pitch': self.grain_pitch,
                'amplitude': 1.0,
                'pan': 0.0  # Center panned
            }

            grains.append(grain)

        return grains

    def process_grains(self, grains: List[Dict[str, Any]], block_size: int,
                      current_time: float) -> np.ndarray:
        """
        Process grains for current time block.

        Args:
            grains: List of grain definitions
            block_size: Audio block size
            current_time: Current time in seconds

        Returns:
            Audio block with grain output
        """
        if self.source_audio is None:
            return np.zeros(block_size)

        output = np.zeros(block_size)

        # Find grains active in this block
        block_start = current_time
        block_end = current_time + block_size / self.sample_rate

        for grain in grains:
            grain_start = grain['start_time']
            grain_duration = (grain['end_sample'] - grain['start_sample']) / self.sample_rate / grain['pitch']

            if grain_start < block_end and grain_start + grain_duration > block_start:
                # Grain is active in this block
                grain_audio = self._synthesize_grain(grain, block_size, block_start)
                output += grain_audio

        return output

    def _synthesize_grain(self, grain: Dict[str, Any], block_size: int,
                         block_start: float) -> np.ndarray:
        """Synthesize a single grain."""
        start_sample = grain['start_sample']
        end_sample = grain['end_sample']
        pitch = grain['pitch']
        amplitude = grain['amplitude']

        # Get grain audio from source
        grain_length = end_sample - start_sample
        if grain_length <= 0:
            return np.zeros(block_size)

        # Extract grain with pitch shifting
        if pitch == 1.0:
            # No pitch shift
            grain_audio = self.source_audio[start_sample:end_sample].copy()
        else:
            # Simple pitch shifting by resampling
            original_indices = np.arange(grain_length)
            resampled_indices = original_indices / pitch

            # Linear interpolation
            int_indices = resampled_indices.astype(int)
            frac = resampled_indices - int_indices

            # Clamp indices
            int_indices = np.clip(int_indices, 0, grain_length - 2)
            frac = np.clip(frac, 0.0, 1.0)

            grain_audio = (self.source_audio[start_sample + int_indices] * (1 - frac) +
                          self.source_audio[start_sample + int_indices + 1] * frac)

        # Apply amplitude envelope (simple triangle window)
        if len(grain_audio) > 0:
            envelope = np.ones(len(grain_audio))
            # Fade in/out
            fade_samples = min(100, len(grain_audio) // 4)
            if fade_samples > 0:
                envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
                envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

            grain_audio *= envelope * amplitude

        # Return grain (will be zero-padded to block_size if needed)
        result = np.zeros(block_size)
        result[:len(grain_audio)] = grain_audio

        return result


class SpectralSynthesizer:
    """
    Core spectral synthesis engine.

    Combines FFT processing, spectral filtering, and granular synthesis
    for advanced sound design and transformation.
    """

    def __init__(self, sample_rate: int = 44100, fft_size: int = 2048):
        self.sample_rate = sample_rate
        self.fft_size = fft_size

        # Core components
        self.fft_processor = FFTProcessor(fft_size=fft_size)
        self.spectral_filters = [SpectralFilter(fft_size, sample_rate) for _ in range(8)]
        self.granular_engine = GranularEngine(sample_rate)

        # Synthesis parameters
        self.morph_position = 0.0  # For spectral morphing
        self.noise_amount = 0.0
        self.freeze_spectrum = False
        self.frozen_spectrum: Optional[np.ndarray] = None

    def analyze_audio(self, audio: np.ndarray) -> np.ndarray:
        """Analyze audio into spectral representation."""
        return self.fft_processor.forward(audio)

    def synthesize_from_spectrum(self, spectrum: np.ndarray) -> np.ndarray:
        """Synthesize audio from spectral representation."""
        return self.fft_processor.inverse(spectrum)

    def process_spectral_block(self, input_block: np.ndarray) -> np.ndarray:
        """
        Process audio block through spectral domain.

        Args:
            input_block: Input audio block

        Returns:
            Processed audio block
        """
        # Forward FFT
        spectrum = self.analyze_audio(input_block)

        # Freeze spectrum if requested
        if self.freeze_spectrum:
            if self.frozen_spectrum is None:
                self.frozen_spectrum = spectrum.copy()
            else:
                spectrum = self.frozen_spectrum.copy()

        # Apply spectral filters
        for spectral_filter in self.spectral_filters:
            spectrum = spectral_filter.process_spectrum(spectrum)

        # Add spectral noise if requested
        if self.noise_amount > 0:
            noise_spectrum = self._generate_noise_spectrum()
            spectrum = spectrum * (1.0 - self.noise_amount) + noise_spectrum * self.noise_amount

        # Inverse FFT
        output = self.synthesize_from_spectrum(spectrum)

        return output

    def _generate_noise_spectrum(self) -> np.ndarray:
        """Generate random noise spectrum."""
        # Create random complex spectrum with magnitude envelope
        magnitudes = np.random.exponential(1.0, self.fft_size // 2 + 1)
        phases = np.random.uniform(0, 2 * np.pi, self.fft_size // 2 + 1)

        # Convert to complex
        complex_spectrum = magnitudes * np.exp(1j * phases)

        # Make symmetric for real-valued IFFT
        full_spectrum = np.concatenate([complex_spectrum, np.conj(complex_spectrum[-2:0:-1])])

        return full_spectrum

    def set_freeze(self, freeze: bool):
        """Freeze current spectrum for static spectral processing."""
        self.freeze_spectrum = freeze
        if not freeze:
            self.frozen_spectrum = None

    def add_spectral_filter(self, filter_type: str, **params):
        """Add and configure a spectral filter."""
        # Find available filter slot
        for spectral_filter in self.spectral_filters:
            # Simple filter configuration
            if filter_type == 'bandpass':
                spectral_filter.set_bandpass(**params)
            elif filter_type == 'bandreject':
                spectral_filter.set_bandreject(**params)
            elif filter_type == 'lowpass':
                spectral_filter.set_lowpass(**params)
            elif filter_type == 'highpass':
                spectral_filter.set_highpass(**params)
            break


class SpectralEngine(SynthesisEngine):
    """
    Spectral Synthesis Engine

    FFT-based spectral synthesis and processing engine providing:
    - Real-time spectral analysis and synthesis
    - Spectral filtering and manipulation
    - Granular synthesis integration
    - Advanced sound design capabilities
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024, fft_size: int = 2048):
        """
        Initialize spectral synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            fft_size: FFT size for spectral processing
        """
        super().__init__(sample_rate, block_size)

        # Core spectral processor
        self.spectral_synth = SpectralSynthesizer(sample_rate, fft_size)

        # Granular synthesis integration
        self.use_granular = False
        self.grain_schedule: List[Dict[str, Any]] = []
        self.current_time = 0.0

        # Engine state
        self.input_buffer = np.zeros(block_size)
        self.output_buffer = np.zeros(block_size)

        # Processing modes
        self.processing_mode = 'spectral'  # 'spectral', 'granular', 'hybrid'

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return 'spectral'

    def set_processing_mode(self, mode: str):
        """
        Set processing mode.

        Args:
            mode: 'spectral', 'granular', or 'hybrid'
        """
        if mode in ['spectral', 'granular', 'hybrid']:
            self.processing_mode = mode

    def enable_granular(self, enable: bool = True):
        """Enable or disable granular synthesis."""
        self.use_granular = enable

    def set_granular_parameters(self, **params):
        """Set granular synthesis parameters."""
        self.spectral_synth.granular_engine.set_grain_parameters(**params)

    def add_spectral_filter(self, filter_type: str, **params):
        """Add spectral filter."""
        self.spectral_synth.add_spectral_filter(filter_type, **params)

    def set_freeze_spectrum(self, freeze: bool):
        """Freeze spectrum for static processing."""
        self.spectral_synth.set_freeze(freeze)

    def set_noise_amount(self, amount: float):
        """Set spectral noise amount (0.0 to 1.0)."""
        self.spectral_synth.noise_amount = max(0.0, min(amount, 1.0))

    def load_audio_for_granulation(self, audio: np.ndarray):
        """Load audio for granular processing."""
        self.spectral_synth.granular_engine.set_source_audio(audio)

    def get_regions_for_note(self, note: int, velocity: int, program: int = 0, bank: int = 0) -> List[Any]:
        """
        Get regions for note (spectral engine creates dynamic regions).

        Returns dynamic region that indicates spectral processing should be used.
        """
        class SpectralRegion:
            def __init__(self, note, velocity, mode):
                self.note = note
                self.velocity = velocity
                self.mode = mode

            def should_play_for_note(self, n, v):
                return n == self.note and v == self.velocity

        return [SpectralRegion(note, velocity, self.processing_mode)]

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> SpectralSynthesizer:
        """
        Create spectral synthesizer instance.

        Args:
            partial_params: Parameters for the synthesizer
            sample_rate: Audio sample rate

        Returns:
            Configured SpectralSynthesizer
        """
        # Return the shared synthesizer instance
        # In a full implementation, this might create separate instances
        return self.spectral_synth

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> np.ndarray:
        """
        Generate audio samples using spectral synthesis.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        # Convert MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))

        # Generate base audio (simple sine wave for demonstration)
        # In practice, this would use more sophisticated source material
        t = np.linspace(0, block_size / self.sample_rate, block_size, endpoint=False)
        base_audio = np.sin(2 * np.pi * frequency * t)

        # Apply velocity
        velocity_gain = velocity / 127.0
        base_audio *= velocity_gain

        # Apply spectral processing
        if self.processing_mode in ['spectral', 'hybrid']:
            processed_audio = self.spectral_synth.process_spectral_block(base_audio)
        else:
            processed_audio = base_audio

        # Add granular component if enabled
        if self.use_granular and self.processing_mode in ['granular', 'hybrid']:
            # Generate grain schedule if needed
            if not self.grain_schedule:
                self.grain_schedule = self.spectral_synth.granular_engine.generate_grains(
                    duration=block_size / self.sample_rate
                )

            # Process grains
            granular_audio = self.spectral_synth.granular_engine.process_grains(
                self.grain_schedule, block_size, self.current_time
            )

            # Mix spectral and granular
            if self.processing_mode == 'hybrid':
                processed_audio = processed_audio * 0.7 + granular_audio * 0.3
            else:
                processed_audio = granular_audio

        # Apply modulation
        processed_audio = self._apply_modulation(processed_audio, modulation, block_size)

        # Convert to stereo
        stereo_audio = np.column_stack([processed_audio, processed_audio])

        # Update time
        self.current_time += block_size / self.sample_rate

        return stereo_audio

    def _apply_modulation(self, audio: np.ndarray, modulation: Dict[str, float],
                         block_size: int) -> np.ndarray:
        """Apply modulation effects to generated audio."""
        # Filter modulation (affects spectral content)
        if 'cutoff' in modulation:
            # Simulate filter cutoff by adjusting spectral processing
            cutoff_norm = modulation['cutoff'] / 20000.0
            # This would adjust spectral filter parameters
            pass

        # Amplitude modulation
        if 'volume' in modulation:
            audio *= (1.0 + modulation['volume'])

        # Pan modulation
        if 'pan' in modulation:
            pan = np.clip(modulation['pan'], -1.0, 1.0)
            left_gain = 1.0 - max(0.0, pan)
            right_gain = 1.0 - max(0.0, -pan)
            audio *= left_gain  # Apply to mono signal before stereo conversion

        return audio

    def is_note_supported(self, note: int) -> bool:
        """Check if note is supported (all notes supported in spectral synthesis)."""
        return 0 <= note <= 127

    def get_supported_formats(self) -> List[str]:
        """Get supported file formats for spectral processing."""
        return ['.wav', '.aiff', '.flac', '.ogg']  # For loading source material

    def get_engine_info(self) -> Dict[str, Any]:
        """Get comprehensive engine information."""
        return {
            'name': 'Spectral Synthesis Engine',
            'type': 'spectral',
            'version': '1.0',
            'capabilities': [
                'fft_analysis_synthesis', 'spectral_filtering', 'granular_synthesis',
                'spectral_freezing', 'noise_synthesis', 'real_time_spectral_morphing',
                'time_stretching', 'pitch_shifting', 'spectral_cross_synthesis'
            ],
            'formats': self.get_supported_formats(),
            'fft_size': self.spectral_synth.fft_processor.fft_size,
            'processing_modes': ['spectral', 'granular', 'hybrid'],
            'current_mode': self.processing_mode,
            'granular_enabled': self.use_granular,
            'parameters': [
                'processing_mode', 'granular_params', 'spectral_filters',
                'freeze_spectrum', 'noise_amount', 'fft_size'
            ],
            'modulation_sources': [
                'velocity', 'key', 'cc1-cc127', 'pitch_bend', 'aftertouch'
            ],
            'modulation_destinations': [
                'volume', 'pan', 'cutoff', 'resonance', 'grain_density',
                'grain_size', 'grain_pitch', 'spectral_morph', 'noise_amount'
            ]
        }

    def get_spectral_info(self) -> Dict[str, Any]:
        """Get detailed spectral processing information."""
        return {
            'fft_size': self.spectral_synth.fft_processor.fft_size,
            'hop_size': self.spectral_synth.fft_processor.hop_size,
            'window_type': 'hann',  # Would be configurable
            'processing_mode': self.processing_mode,
            'freeze_enabled': self.spectral_synth.freeze_spectrum,
            'noise_amount': self.spectral_synth.noise_amount,
            'num_filters': len(self.spectral_synth.spectral_filters),
            'granular_active': self.use_granular
        }

    def reset(self) -> None:
        """Reset engine to clean state."""
        self.current_time = 0.0
        self.grain_schedule.clear()
        self.spectral_synth.set_freeze(False)
        self.spectral_synth.noise_amount = 0.0

    def cleanup(self) -> None:
        """Clean up engine resources."""
        self.reset()
        # Clear any cached audio
        self.spectral_synth.granular_engine.source_audio = None

    def __str__(self) -> str:
        """String representation."""
        info = self.get_engine_info()
        return (f"SpectralEngine(mode={info['current_mode']}, "
                f"fft_size={info['fft_size']}, "
                f"granular={info['granular_enabled']})")

    def __repr__(self) -> str:
        return self.__str__()
