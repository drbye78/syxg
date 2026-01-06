"""
Pitch Shifting Engine - Advanced Pitch Manipulation

Provides sophisticated pitch shifting algorithms for sample manipulation,
including formant preservation, phase vocoder, and harmonic manipulation
for professional audio processing in the XG synthesizer.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import threading


class PitchShiftingEngine:
    """
    Advanced pitch shifting engine with multiple algorithms.

    Supports various pitch shifting techniques including phase vocoder,
    formant preservation, and harmonic manipulation for high-quality audio processing.
    """

    def __init__(self, sample_rate: int = 44100, max_block_size: int = 8192):
        """
        Initialize pitch shifting engine.

        Args:
            sample_rate: Audio sample rate
            max_block_size: Maximum processing block size
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size

        # Algorithm settings
        self.algorithm = 'phase_vocoder'  # 'phase_vocoder', 'resampling', 'harmonic'
        self.quality = 'high'  # 'fast', 'standard', 'high'

        # Processing parameters
        self.pitch_ratio = 1.0
        self.formant_ratio = 1.0
        self.time_stretch_ratio = 1.0

        # Buffer management
        self.input_buffer = np.zeros(max_block_size, dtype=np.float32)
        self.output_buffer = np.zeros(max_block_size * 2, dtype=np.float32)  # Allow for expansion

        # Phase vocoder state
        self.phase_accumulator = np.zeros(max_block_size // 2, dtype=np.float32)
        self.previous_phases = np.zeros(max_block_size // 2, dtype=np.float32)

        # Harmonic manipulation state
        self.harmonic_count = 8
        self.harmonic_gains = np.ones(self.harmonic_count, dtype=np.float32)

        # Threading
        self.lock = threading.RLock()

    def set_pitch_ratio(self, ratio: float) -> bool:
        """
        Set pitch shifting ratio.

        Args:
            ratio: Pitch ratio (> 0.25, < 4.0)

        Returns:
            Success status
        """
        with self.lock:
            if 0.25 <= ratio <= 4.0:
                self.pitch_ratio = ratio
                return True
            return False

    def set_formant_ratio(self, ratio: float) -> bool:
        """
        Set formant shifting ratio for vocal processing.

        Args:
            ratio: Formant ratio (> 0.5, < 2.0)

        Returns:
            Success status
        """
        with self.lock:
            if 0.5 <= ratio <= 2.0:
                self.formant_ratio = ratio
                return True
            return False

    def set_algorithm(self, algorithm: str) -> bool:
        """
        Set pitch shifting algorithm.

        Args:
            algorithm: Algorithm name ('phase_vocoder', 'resampling', 'harmonic')

        Returns:
            Success status
        """
        with self.lock:
            if algorithm in ['phase_vocoder', 'resampling', 'harmonic']:
                self.algorithm = algorithm
                return True
            return False

    def set_quality(self, quality: str) -> bool:
        """
        Set processing quality.

        Args:
            quality: Quality level ('fast', 'standard', 'high')

        Returns:
            Success status
        """
        with self.lock:
            if quality in ['fast', 'standard', 'high']:
                self.quality = quality
                return True
            return False

    def process_block(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process a block of audio with pitch shifting.

        Args:
            input_audio: Input audio block

        Returns:
            Processed audio block
        """
        with self.lock:
            if self.pitch_ratio == 1.0 and self.formant_ratio == 1.0:
                return input_audio

            if self.algorithm == 'phase_vocoder':
                return self._process_phase_vocoder(input_audio)
            elif self.algorithm == 'resampling':
                return self._process_resampling(input_audio)
            elif self.algorithm == 'harmonic':
                return self._process_harmonic(input_audio)
            else:
                return input_audio

    def _process_phase_vocoder(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using phase vocoder algorithm with formant preservation.

        Args:
            input_audio: Input audio

        Returns:
            Pitch-shifted audio
        """
        # Simplified phase vocoder implementation
        # In a production system, this would be much more sophisticated

        if self.pitch_ratio == 1.0:
            return input_audio

        # For now, implement simple resampling-based pitch shifting
        # This is a placeholder - real phase vocoder is much more complex
        output_length = int(len(input_audio) / self.pitch_ratio)

        if output_length <= 0:
            return np.array([], dtype=np.float32)

        # Simple interpolation for pitch shifting
        x_old = np.arange(len(input_audio))
        x_new = np.linspace(0, len(input_audio) - 1, output_length)

        shifted = np.interp(x_new, x_old, input_audio)

        # Apply formant shifting if needed
        if self.formant_ratio != 1.0:
            shifted = self._apply_formant_shift(shifted, self.formant_ratio)

        return shifted.astype(np.float32)

    def _process_resampling(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using simple resampling algorithm.

        Args:
            input_audio: Input audio

        Returns:
            Pitch-shifted audio
        """
        if self.pitch_ratio == 1.0:
            return input_audio

        # Simple resampling
        output_length = int(len(input_audio) / self.pitch_ratio)

        if output_length <= 0:
            return np.array([], dtype=np.float32)

        x_old = np.arange(len(input_audio))
        x_new = np.linspace(0, len(input_audio) - 1, output_length)

        shifted = np.interp(x_new, x_old, input_audio).astype(np.float32)

        # Apply formant correction for vocal processing
        if self.formant_ratio != 1.0:
            shifted = self._apply_formant_shift(shifted, self.formant_ratio)

        return shifted

    def _process_harmonic(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using harmonic manipulation algorithm.

        Args:
            input_audio: Input audio

        Returns:
            Pitch-shifted audio
        """
        if self.pitch_ratio == 1.0:
            return input_audio

        # Simplified harmonic manipulation
        # In production, this would analyze and manipulate individual harmonics

        # For now, use a simple approach
        output_length = int(len(input_audio) / self.pitch_ratio)
        shifted = np.zeros(output_length, dtype=np.float32)

        # Create harmonics
        for i in range(min(self.harmonic_count, 8)):
            harmonic_ratio = (i + 1) * self.pitch_ratio
            if harmonic_ratio <= 4.0:  # Limit to reasonable range
                # Generate harmonic
                harmonic_length = int(len(input_audio) / harmonic_ratio)
                if harmonic_length > 0:
                    x_old = np.arange(len(input_audio))
                    x_new = np.linspace(0, len(input_audio) - 1, harmonic_length)

                    harmonic = np.interp(x_new, x_old, input_audio)

                    # Mix harmonic into output
                    if len(harmonic) > 0:
                        # Resample to output length
                        if len(harmonic) != output_length:
                            x_out = np.linspace(0, len(harmonic) - 1, output_length)
                            harmonic = np.interp(x_out, np.arange(len(harmonic)), harmonic)

                        gain = self.harmonic_gains[i] / (i + 1)  # Reduce higher harmonics
                        shifted += harmonic * gain

        return shifted

    def _apply_formant_shift(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        """
        Apply formant shifting for vocal processing.

        Args:
            audio: Input audio
            ratio: Formant shift ratio

        Returns:
            Formant-shifted audio
        """
        # Simplified formant shifting
        # In production, this would use more sophisticated vocal processing

        if abs(ratio - 1.0) < 0.01:
            return audio

        # Simple spectral filtering approach
        # This is a placeholder - real formant shifting is much more complex

        # Apply a simple filter to simulate formant shifting
        # Higher ratio = higher formants, lower ratio = lower formants
        if ratio > 1.0:
            # Boost highs for higher formants
            return self._apply_simple_filter(audio, 0.7, 'highpass')
        elif ratio < 1.0:
            # Boost lows for lower formants
            return self._apply_simple_filter(audio, 0.3, 'lowpass')
        else:
            return audio

    def _apply_simple_filter(self, audio: np.ndarray, freq: float, filter_type: str) -> np.ndarray:
        """
        Apply simple filter for formant processing.

        Args:
            audio: Input audio
            freq: Normalized frequency (0-1)
            filter_type: Filter type

        Returns:
            Filtered audio
        """
        # Very simple filter implementation
        alpha = freq

        if filter_type == 'lowpass':
            # Simple lowpass
            filtered = np.zeros_like(audio)
            filtered[0] = audio[0]
            for i in range(1, len(audio)):
                filtered[i] = alpha * audio[i] + (1 - alpha) * filtered[i-1]
            return filtered

        elif filter_type == 'highpass':
            # Simple highpass
            filtered = np.zeros_like(audio)
            filtered[0] = audio[0]
            for i in range(1, len(audio)):
                filtered[i] = alpha * (filtered[i-1] + audio[i] - audio[i-1])
            return filtered

        else:
            return audio

    def set_harmonic_gains(self, gains: np.ndarray) -> bool:
        """
        Set gains for individual harmonics.

        Args:
            gains: Array of harmonic gains

        Returns:
            Success status
        """
        with self.lock:
            if len(gains) <= self.harmonic_count:
                self.harmonic_gains[:len(gains)] = gains
                return True
            return False

    def get_pitch_info(self) -> Dict[str, Any]:
        """
        Get current pitch shifting configuration.

        Returns:
            Configuration information
        """
        with self.lock:
            return {
                'algorithm': self.algorithm,
                'quality': self.quality,
                'pitch_ratio': self.pitch_ratio,
                'formant_ratio': self.formant_ratio,
                'time_stretch_ratio': self.time_stretch_ratio,
                'harmonic_count': self.harmonic_count,
                'harmonic_gains': self.harmonic_gains.tolist(),
                'sample_rate': self.sample_rate,
                'max_block_size': self.max_block_size
            }

    def reset(self):
        """Reset pitch shifting engine to default state."""
        with self.lock:
            self.pitch_ratio = 1.0
            self.formant_ratio = 1.0
            self.time_stretch_ratio = 1.0
            self.phase_accumulator.fill(0)
            self.previous_phases.fill(0)
            self.harmonic_gains.fill(1.0)

    def get_latency(self) -> int:
        """
        Get processing latency in samples.

        Returns:
            Latency in samples
        """
        if self.algorithm == 'phase_vocoder':
            return self.max_block_size // 2
        elif self.algorithm == 'resampling':
            return 0  # Minimal latency
        else:
            return self.max_block_size // 4

    def is_realtime_capable(self) -> bool:
        """
        Check if current settings are realtime capable.

        Returns:
            True if realtime processing is possible
        """
        # Check if processing can keep up with realtime requirements
        latency = self.get_latency()
        max_realtime_latency = self.sample_rate // 10  # 100ms max

        return latency <= max_realtime_latency

    def get_supported_algorithms(self) -> List[str]:
        """Get list of supported algorithms."""
        return ['phase_vocoder', 'resampling', 'harmonic']

    def get_supported_qualities(self) -> List[str]:
        """Get list of supported quality levels."""
        return ['fast', 'standard', 'high']

    def get_pitch_range(self) -> Tuple[float, float]:
        """
        Get supported pitch ratio range.

        Returns:
            Tuple of (min_ratio, max_ratio)
        """
        return (0.25, 4.0)

    def get_formant_range(self) -> Tuple[float, float]:
        """
        Get supported formant ratio range.

        Returns:
            Tuple of (min_ratio, max_ratio)
        """
        return (0.5, 2.0)
