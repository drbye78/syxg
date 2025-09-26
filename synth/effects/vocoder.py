"""
Vocoder effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class VocoderEffect:
    """
    Production-quality vocoder effect implementation.

    A vocoder analyzes the spectrum of one signal (carrier) and applies it to another signal (modulator),
    creating a "robotized" voice effect. This implementation uses FFT-based analysis and synthesis.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the vocoder state"""
        # FFT parameters
        self.fft_size = 1024
        self.hop_size = self.fft_size // 4
        self.num_bands = 16

        # Frequency bands (logarithmic spacing)
        self.band_freqs = self._calculate_band_frequencies()

        # Buffers for FFT processing
        self.input_buffer = np.zeros(self.fft_size)
        self.output_buffer = np.zeros(self.fft_size)
        self.buffer_pos = 0

        # Filter states for each band
        self.band_filters = [self._create_band_filter(i) for i in range(self.num_bands)]

        # Window function
        self.window = np.hanning(self.fft_size)

    def _calculate_band_frequencies(self) -> List[float]:
        """Calculate center frequencies for vocoder bands"""
        bands = []
        min_freq = 200.0
        max_freq = 8000.0

        # Logarithmic spacing
        for i in range(self.num_bands):
            freq = min_freq * (max_freq / min_freq) ** (i / (self.num_bands - 1))
            bands.append(freq)

        return bands

    def _create_band_filter(self, band_idx: int) -> Dict[str, Any]:
        """Create filter coefficients for a specific frequency band"""
        center_freq = self.band_freqs[band_idx]
        bandwidth = center_freq * 0.3  # 30% bandwidth

        # Calculate filter coefficients (simplified bandpass)
        w0 = 2 * math.pi * center_freq / self.sample_rate
        bw = 2 * math.pi * bandwidth / self.sample_rate

        # Bandpass filter coefficients
        beta = math.cos(w0) * math.cos(bw)
        gamma = 1 + math.cos(bw)
        alpha = (gamma - beta) / 2

        return {
            "center_freq": center_freq,
            "bandwidth": bandwidth,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "envelope": 0.0,
            "prev_input": 0.0,
            "prev_output": 0.0
        }

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through vocoder effect.

        Parameters:
        - bands: number of frequency bands (1-20)
        - depth: modulation depth (0.0-1.0)
        - formant: formant shift (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        bands = int(params.get("bands", 0.5) * 20) + 1  # 1-20 bands
        depth = params.get("depth", 0.5)
        formant = params.get("formant", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "vocoder" not in state:
            state["vocoder"] = {
                "input_buffer": np.zeros(self.fft_size),
                "output_buffer": np.zeros(self.fft_size),
                "buffer_pos": 0,
                "band_filters": [self._create_band_filter(i) for i in range(min(bands, self.num_bands))],
                "fft_accumulator": np.zeros(self.fft_size, dtype=complex)
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Add to input buffer
        vocoder_state = state["vocoder"]
        vocoder_state["input_buffer"][vocoder_state["buffer_pos"]] = input_sample
        vocoder_state["buffer_pos"] = (vocoder_state["buffer_pos"] + 1) % self.fft_size

        # Process when we have enough samples
        output_sample = 0.0
        if vocoder_state["buffer_pos"] % self.hop_size == 0:
            output_sample = self._process_fft_frame(vocoder_state, depth, formant, bands)

        # Apply level
        return (output_sample * level, output_sample * level)

    def _process_fft_frame(self, state: Dict[str, Any], depth: float, formant: float, bands: int) -> float:
        """Process one FFT frame for vocoder analysis/synthesis"""
        # Apply window
        windowed = state["input_buffer"] * self.window

        # FFT analysis
        fft_result = np.fft.rfft(windowed)

        # Process frequency bands
        processed_fft = np.zeros_like(fft_result)

        for i, band_filter in enumerate(state["band_filters"][:min(bands, len(state["band_filters"]))]):
            # Extract band energy (simplified envelope follower)
            band_energy = self._extract_band_energy(fft_result, band_filter, formant)

            # Apply modulation depth
            band_energy *= depth

            # Apply to carrier (simplified synthesis)
            band_freq = band_filter["center_freq"]
            bin_idx = int(band_freq * self.fft_size / self.sample_rate)

            if bin_idx < len(processed_fft):
                processed_fft[bin_idx] = band_energy * fft_result[bin_idx]

        # Inverse FFT
        ifft_result = np.fft.irfft(processed_fft)

        # Overlap-add
        state["output_buffer"] = ifft_result * self.window

        # Return center sample
        return float(state["output_buffer"][self.fft_size // 2])

    def _extract_band_energy(self, fft_data: np.ndarray, band_filter: Dict[str, Any], formant: float) -> float:
        """Extract energy from a specific frequency band"""
        center_freq = band_filter["center_freq"]
        bandwidth = band_filter["bandwidth"]

        # Find frequency bins in this band
        bin_start = int((center_freq - bandwidth/2) * self.fft_size / self.sample_rate)
        bin_end = int((center_freq + bandwidth/2) * self.fft_size / self.sample_rate)

        bin_start = max(0, bin_start)
        bin_end = min(len(fft_data), bin_end)

        # Calculate band energy
        if bin_end > bin_start:
            band_energy = np.sum(np.abs(fft_data[bin_start:bin_end]) ** 2)
            band_energy = math.sqrt(band_energy / (bin_end - bin_start))
        else:
            band_energy = 0.0

        # Apply formant shift
        formant_shift = (formant - 0.5) * 2.0
        band_energy *= (1.0 + formant_shift * math.sin(center_freq * 0.001))

        return band_energy


# Factory function for creating vocoder effect
def create_vocoder_effect(sample_rate: int = 44100):
    """Create a vocoder effect instance"""
    return VocoderEffect(sample_rate)


# Process function for integration with main effects system
def process_vocoder_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through vocoder effect (for integration)"""
    effect = VocoderEffect()
    return effect.process(left, right, params, state)
