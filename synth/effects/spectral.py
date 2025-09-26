"""
Spectral effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class SpectralEffect:
    """
    Production-quality spectral effect implementation.

    Applies real-time FFT-based spectral processing to create unique timbral transformations.
    Supports various spectral manipulations including filtering, freezing, and morphing.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the spectral effect state"""
        # FFT parameters
        self.fft_size = 2048
        self.hop_size = self.fft_size // 4
        self.overlap = self.fft_size - self.hop_size

        # Buffers for FFT processing
        self.input_buffer = np.zeros(self.fft_size)
        self.output_buffer = np.zeros(self.fft_size)
        self.fft_window = np.hanning(self.fft_size)
        self.buffer_pos = 0

        # Spectral processing state
        self.prev_magnitude = np.zeros(self.fft_size // 2 + 1)
        self.phase_accumulator = np.zeros(self.fft_size // 2 + 1)

        # Frequency domain processing
        self.spectral_filter = np.ones(self.fft_size // 2 + 1)

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through spectral effect.

        Parameters:
        - spectrum: spectral processing amount (0.0-1.0)
        - depth: processing depth (0.0-1.0)
        - formant: formant shift (0.0-1.0)
        - level: output level (0.0-1.0)
        - freeze: spectral freeze amount (0.0-1.0)
        - morph: spectral morphing (0.0-1.0)
        - filter_type: spectral filter type (0.0-1.0, maps to different filters)
        """
        # Get parameters
        spectrum = params.get("spectrum", 0.5)
        depth = params.get("depth", 0.5)
        formant = params.get("formant", 0.5)
        level = params.get("level", 0.5)
        freeze = params.get("freeze", 0.0)
        morph = params.get("morph", 0.5)
        filter_type = int(params.get("filter_type", 0.5) * 4)  # 0-4 filter types

        # Initialize state if needed
        if "spectral" not in state:
            state["spectral"] = {
                "input_buffer": np.zeros(self.fft_size),
                "output_buffer": np.zeros(self.fft_size),
                "buffer_pos": 0,
                "prev_magnitude": np.zeros(self.fft_size // 2 + 1),
                "phase_accumulator": np.zeros(self.fft_size // 2 + 1),
                "spectral_filter": np.ones(self.fft_size // 2 + 1)
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Add to input buffer
        spectral_state = state["spectral"]
        spectral_state["input_buffer"][spectral_state["buffer_pos"]] = input_sample
        spectral_state["buffer_pos"] = (spectral_state["buffer_pos"] + 1) % self.fft_size

        # Process when we have enough samples
        output_sample = 0.0
        if spectral_state["buffer_pos"] % self.hop_size == 0:
            output_sample = self._process_spectral_frame(spectral_state, spectrum, depth, formant,
                                                       freeze, morph, filter_type)

        # Apply level
        return (output_sample * level, output_sample * level)

    def _process_spectral_frame(self, state: Dict[str, Any], spectrum: float, depth: float,
                              formant: float, freeze: float, morph: float, filter_type: int) -> float:
        """Process one spectral frame"""
        # Apply window
        windowed = state["input_buffer"] * self.fft_window

        # FFT analysis
        fft_result = np.fft.rfft(windowed)

        # Extract magnitude and phase
        magnitude = np.abs(fft_result)
        phase = np.angle(fft_result)

        # Apply spectral processing
        processed_magnitude = self._apply_spectral_processing(
            magnitude, state, spectrum, depth, formant, freeze, morph, filter_type
        )

        # Reconstruct complex spectrum
        processed_fft = processed_magnitude * np.exp(1j * phase)

        # Inverse FFT
        ifft_result = np.fft.irfft(processed_fft)

        # Overlap-add
        state["output_buffer"] = ifft_result * self.fft_window

        # Return center sample
        return float(state["output_buffer"][self.fft_size // 2])

    def _apply_spectral_processing(self, magnitude: np.ndarray, state: Dict[str, Any],
                                 spectrum: float, depth: float, formant: float,
                                 freeze: float, morph: float, filter_type: int) -> np.ndarray:
        """Apply various spectral processing techniques"""
        processed = magnitude.copy()

        # Apply spectral freeze
        if freeze > 0:
            processed = processed * (1 - freeze) + state["prev_magnitude"] * freeze

        # Apply formant shifting
        if formant != 0.5:
            shift_amount = (formant - 0.5) * 0.5  # -0.25 to +0.25 octave shift
            processed = self._apply_formant_shift(processed, shift_amount)

        # Apply spectral filtering
        filter_response = self._generate_spectral_filter(len(processed), filter_type, depth)
        processed *= (1 - spectrum) + (processed * filter_response) * spectrum

        # Apply spectral morphing
        if morph != 0.5:
            morph_target = self._generate_morph_target(len(processed), morph)
            processed = processed * (1 - morph * 0.5) + morph_target * (morph * 0.5)

        # Update state
        state["prev_magnitude"] = processed.copy()

        return processed

    def _apply_formant_shift(self, spectrum: np.ndarray, shift_amount: float) -> np.ndarray:
        """Apply formant shifting to spectrum"""
        shifted = np.zeros_like(spectrum)

        # Calculate frequency bins
        freq_bins = np.arange(len(spectrum)) * (self.sample_rate / (2 * len(spectrum)))

        # Apply shift to each bin
        for i in range(len(spectrum)):
            # Calculate shifted frequency
            shifted_freq = freq_bins[i] * (2 ** shift_amount)

            # Find corresponding bin in original spectrum
            shifted_bin = int(shifted_freq * 2 * len(spectrum) / self.sample_rate)

            if 0 <= shifted_bin < len(spectrum):
                shifted[i] = spectrum[shifted_bin]

        return shifted

    def _generate_spectral_filter(self, size: int, filter_type: int, depth: float) -> np.ndarray:
        """Generate spectral filter response"""
        freq_bins = np.arange(size) / size  # Normalized frequency 0-1

        if filter_type == 0:  # Lowpass
            cutoff = 0.3 + depth * 0.4  # 0.3-0.7
            response = 1 / (1 + np.exp(10 * (freq_bins - cutoff)))
        elif filter_type == 1:  # Highpass
            cutoff = 0.3 + depth * 0.4  # 0.3-0.7
            response = 1 / (1 + np.exp(-10 * (freq_bins - cutoff)))
        elif filter_type == 2:  # Bandpass
            center = 0.5
            width = 0.1 + depth * 0.3  # 0.1-0.4
            response = np.exp(-0.5 * ((freq_bins - center) / width) ** 2)
        elif filter_type == 3:  # Notch
            center = 0.5
            width = 0.1 + depth * 0.3  # 0.1-0.4
            response = 1 - np.exp(-0.5 * ((freq_bins - center) / width) ** 2)
        else:  # Comb filter
            spacing = 0.1 + depth * 0.2  # 0.1-0.3
            response = np.sin(2 * np.pi * freq_bins / spacing) ** 2

        return response

    def _generate_morph_target(self, size: int, morph: float) -> np.ndarray:
        """Generate target spectrum for morphing"""
        freq_bins = np.arange(size) / size

        # Create different spectral shapes based on morph parameter
        if morph < 0.33:
            # Bright spectrum
            target = freq_bins ** 0.5
        elif morph < 0.66:
            # Flat spectrum
            target = np.ones(size)
        else:
            # Dark spectrum
            target = (1 - freq_bins) ** 0.5

        return target


# Factory function for creating spectral effect
def create_spectral_effect(sample_rate: int = 44100):
    """Create a spectral effect instance"""
    return SpectralEffect(sample_rate)


# Process function for integration with main effects system
def process_spectral_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through spectral effect (for integration)"""
    effect = SpectralEffect()
    return effect.process(left, right, params, state)
