"""
Time Stretching Engine - Advanced Time Manipulation

Provides sophisticated time stretching algorithms for sample manipulation,
including phase vocoder, granular synthesis, and hybrid approaches for
professional audio processing in the XG synthesizer.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import threading


class TimeStretchingEngine:
    """
    Advanced time stretching engine with multiple algorithms.

    Supports various time stretching techniques including phase vocoder,
    granular synthesis, and hybrid approaches for high-quality audio processing.
    """

    def __init__(self, sample_rate: int = 44100, max_block_size: int = 8192):
        """
        Initialize time stretching engine.

        Args:
            sample_rate: Audio sample rate
            max_block_size: Maximum processing block size
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size

        # Algorithm settings
        self.algorithm = "phase_vocoder"  # 'phase_vocoder', 'granular', 'hybrid'
        self.quality = "high"  # 'fast', 'standard', 'high'

        # Processing parameters
        self.time_ratio = 1.0
        self.pitch_ratio = 1.0
        self.formant_ratio = 1.0

        # Buffer management
        self.input_buffer = np.zeros(max_block_size, dtype=np.float32)
        self.output_buffer = np.zeros(
            max_block_size * 2, dtype=np.float32
        )  # Allow for expansion

        # Phase vocoder state
        self.phase_accumulator = np.zeros(max_block_size // 2, dtype=np.float32)
        self.previous_phases = np.zeros(max_block_size // 2, dtype=np.float32)

        # Granular synthesis state
        self.grain_size = 1024
        self.grain_overlap = 0.5
        self.grains: List[np.ndarray] = []

        # Threading
        self.lock = threading.RLock()

    def set_time_ratio(self, ratio: float) -> bool:
        """
        Set time stretching ratio.

        Args:
            ratio: Time ratio (> 0.1, < 10.0)

        Returns:
            Success status
        """
        with self.lock:
            if 0.1 <= ratio <= 10.0:
                self.time_ratio = ratio
                return True
            return False

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

    def set_algorithm(self, algorithm: str) -> bool:
        """
        Set time stretching algorithm.

        Args:
            algorithm: Algorithm name ('phase_vocoder', 'granular', 'hybrid')

        Returns:
            Success status
        """
        with self.lock:
            if algorithm in ["phase_vocoder", "granular", "hybrid"]:
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
            if quality in ["fast", "standard", "high"]:
                self.quality = quality
                # Adjust parameters based on quality
                if quality == "fast":
                    self.grain_size = 512
                    self.grain_overlap = 0.25
                elif quality == "standard":
                    self.grain_size = 1024
                    self.grain_overlap = 0.5
                elif quality == "high":
                    self.grain_size = 2048
                    self.grain_overlap = 0.75
                return True
            return False

    def process_block(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process a block of audio with time stretching.

        Args:
            input_audio: Input audio block

        Returns:
            Processed audio block
        """
        with self.lock:
            if self.algorithm == "phase_vocoder":
                return self._process_phase_vocoder(input_audio)
            elif self.algorithm == "granular":
                return self._process_granular(input_audio)
            elif self.algorithm == "hybrid":
                return self._process_hybrid(input_audio)
            else:
                return input_audio

    def _process_phase_vocoder(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using phase vocoder algorithm with spectral processing.

        Args:
            input_audio: Input audio

        Returns:
            Time-stretched audio
        """
        if self.time_ratio == 1.0 and self.pitch_ratio == 1.0:
            return input_audio

        # Determine FFT size based on quality setting
        if self.quality == "fast":
            fft_size = 1024
            hop_size = 256
        elif self.quality == "standard":
            fft_size = 2048
            hop_size = 512
        else:  # high
            fft_size = 4096
            hop_size = 1024

        # Ensure input is float64 for FFT
        input_audio = input_audio.astype(np.float64)

        # Pad input to handle edge effects
        pad_size = fft_size // 2
        padded_input = np.pad(input_audio, (pad_size, pad_size), mode="edge")

        # Calculate number of frames
        num_frames = (len(padded_input) - fft_size) // hop_size + 1

        # Output storage
        output_length = int(len(input_audio) * self.time_ratio)
        output_audio = np.zeros(output_length + fft_size * 2, dtype=np.float64)

        # Phase vocoder processing
        stretch_factor = self.time_ratio
        phase_accum = np.zeros(fft_size // 2 + 1, dtype=np.float64)
        previous_phase = np.zeros(fft_size // 2 + 1, dtype=np.float64)

        # Synthesis hop size (different from analysis hop for time stretching)
        synthesis_hop = int(hop_size * stretch_factor)

        for frame_idx in range(num_frames):
            # Get current frame
            start_pos = frame_idx * hop_size
            frame = padded_input[start_pos : start_pos + fft_size]

            # Apply Hann window
            window = np.hanning(fft_size)
            windowed_frame = frame * window

            # FFT
            fft_result = np.fft.rfft(windowed_frame)
            magnitudes = np.abs(fft_result)
            phases = np.angle(fft_result)

            # Phase vocoder - adjust phases for time stretching
            phase_diff = phases - previous_phase
            previous_phase = phases

            # Unwrap phase differences
            phase_diff = np.mod(phase_diff + np.pi, 2 * np.pi) - np.pi

            # Expected phase increments
            expected_phase_increments = (
                2 * np.pi * np.arange(fft_size // 2 + 1) * hop_size / fft_size
            )

            # Calculate true phase with stretch factor
            true_phases = (
                phase_accum + (phase_diff + expected_phase_increments) * stretch_factor
            )
            phase_accum = true_phases

            # Apply pitch shifting if needed
            if self.pitch_ratio != 1.0:
                # Modify magnitudes for pitch shift
                pitch_shift_bins = int(
                    np.round(np.log2(self.pitch_ratio) * fft_size / 2)
                )
                shifted_mags = np.roll(magnitudes, pitch_shift_bins)
                # Fade edges to prevent artifacts
                fade_len = min(abs(pitch_shift_bins), fft_size // 4)
                if pitch_shift_bins > 0:
                    shifted_mags[:fade_len] *= np.linspace(0, 1, fade_len)
                else:
                    shifted_mags[-fade_len:] *= np.linspace(1, 0, fade_len)
                magnitudes = shifted_mags

            # New synthesis phases
            new_phases = phases + expected_phase_increments * (stretch_factor - 1)
            new_phases = np.mod(new_phases + np.pi, 2 * np.pi) - np.pi

            # Reconstruct with new phases
            new_fft = magnitudes * np.exp(1j * new_phases)
            stretched_frame = np.fft.irfft(new_fft, fft_size)

            # Overlap-add at stretched positions
            output_pos = frame_idx * synthesis_hop
            if output_pos + fft_size <= len(output_audio):
                output_audio[output_pos : output_pos + fft_size] += (
                    stretched_frame * window
                )

        # Trim and normalize
        output_audio = output_audio[:output_length]

        # Normalize
        if len(output_audio) > 0:
            output_audio *= np.sqrt(stretch_factor)

        return output_audio.astype(np.float32)

    def _process_granular(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using granular synthesis algorithm.

        Args:
            input_audio: Input audio

        Returns:
            Time-stretched audio
        """
        # Simplified granular synthesis implementation
        # In production, this would use proper granular techniques

        if self.time_ratio == 1.0:
            return input_audio

        # Create grains from input
        grains = []
        hop_size = int(self.grain_size * (1.0 - self.grain_overlap))

        for i in range(0, len(input_audio) - self.grain_size, hop_size):
            grain = input_audio[i : i + self.grain_size].copy()
            # Apply window
            window = np.hanning(self.grain_size)
            grain *= window
            grains.append(grain)

        if not grains:
            return input_audio

        # Reconstruct with time stretching
        output_length = int(len(input_audio) * self.time_ratio)
        output = np.zeros(output_length, dtype=np.float32)

        # Overlap-add grains
        output_hop = int(hop_size * self.time_ratio)

        for i, grain in enumerate(grains):
            start_pos = i * output_hop
            end_pos = start_pos + len(grain)

            if end_pos > len(output):
                break

            output[start_pos:end_pos] += grain

        return output

    def _process_hybrid(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process using hybrid algorithm combining phase vocoder and granular.

        Args:
            input_audio: Input audio

        Returns:
            Time-stretched audio
        """
        # Use phase vocoder for small ratios, granular for large ratios
        if abs(self.time_ratio - 1.0) < 0.5:
            return self._process_phase_vocoder(input_audio)
        else:
            return self._process_granular(input_audio)

    def _apply_pitch_shift(self, audio: np.ndarray, ratio: float) -> np.ndarray:
        """
        Apply pitch shifting to audio.

        Args:
            audio: Input audio
            ratio: Pitch ratio

        Returns:
            Pitch-shifted audio
        """
        # Simple pitch shifting via resampling
        # In production, this would use more sophisticated algorithms
        output_length = int(len(audio) / ratio)

        if output_length <= 0:
            return np.array([], dtype=np.float32)

        x_old = np.arange(len(audio))
        x_new = np.linspace(0, len(audio) - 1, output_length)

        return np.interp(x_new, x_old, audio).astype(np.float32)

    def get_stretch_info(self) -> Dict[str, Any]:
        """
        Get current time stretching configuration.

        Returns:
            Configuration information
        """
        with self.lock:
            return {
                "algorithm": self.algorithm,
                "quality": self.quality,
                "time_ratio": self.time_ratio,
                "pitch_ratio": self.pitch_ratio,
                "formant_ratio": self.formant_ratio,
                "grain_size": self.grain_size,
                "grain_overlap": self.grain_overlap,
                "sample_rate": self.sample_rate,
                "max_block_size": self.max_block_size,
            }

    def reset(self):
        """Reset time stretching engine to default state."""
        with self.lock:
            self.time_ratio = 1.0
            self.pitch_ratio = 1.0
            self.formant_ratio = 1.0
            self.phase_accumulator.fill(0)
            self.previous_phases.fill(0)
            self.grains.clear()

    def get_latency(self) -> int:
        """
        Get processing latency in samples.

        Returns:
            Latency in samples
        """
        if self.algorithm == "phase_vocoder":
            return self.max_block_size // 2
        elif self.algorithm == "granular":
            return self.grain_size
        else:
            return max(self.max_block_size // 2, self.grain_size)

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
        return ["phase_vocoder", "granular", "hybrid"]

    def get_supported_qualities(self) -> List[str]:
        """Get list of supported quality levels."""
        return ["fast", "standard", "high"]
