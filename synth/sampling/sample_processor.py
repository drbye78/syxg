"""
Sample Processor - Advanced Sample Processing

Provides advanced sample processing capabilities including real-time effects,
pitch shifting, time stretching, and format conversion.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np


class SampleProcessor:
    """
    Advanced sample processor with real-time capabilities.

    Provides pitch shifting, time stretching, filtering, and format conversion
    for the XG synthesizer's sample management system.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize sample processor.

        Args:
            sample_rate: Processing sample rate
        """
        self.sample_rate = sample_rate
        self.processing_buffer = np.zeros(4096, dtype=np.float32)
        self.lock = threading.RLock()

        # Processing parameters
        self.pitch_shift_ratio = 1.0
        self.time_stretch_ratio = 1.0
        self.filter_cutoff = 20000.0
        self.filter_resonance = 0.707

    def process_sample(
        self, sample_data: np.ndarray, processing_params: dict[str, Any]
    ) -> np.ndarray:
        """
        Process sample with given parameters.

        Args:
            sample_data: Input sample data
            processing_params: Processing parameters

        Returns:
            Processed sample data
        """
        with self.lock:
            processed = sample_data.copy()

            # Apply processing chain
            if processing_params.get("normalize", False):
                processed = self._normalize_sample(processed)

            if "pitch_shift" in processing_params:
                ratio = processing_params["pitch_shift"]
                processed = self._pitch_shift_sample(processed, ratio)

            if "time_stretch" in processing_params:
                ratio = processing_params["time_stretch"]
                processed = self._time_stretch_sample(processed, ratio)

            if "filter" in processing_params:
                filter_params = processing_params["filter"]
                processed = self._apply_filter(processed, filter_params)

            return processed

    def _normalize_sample(self, sample_data: np.ndarray) -> np.ndarray:
        """Normalize sample to maximum amplitude."""
        max_val = np.max(np.abs(sample_data))
        if max_val > 0:
            return sample_data / max_val
        return sample_data

    def _pitch_shift_sample(self, sample_data: np.ndarray, ratio: float) -> np.ndarray:
        """
        Simple pitch shifting using resampling.

        Args:
            sample_data: Input sample
            ratio: Pitch shift ratio (>1 = higher pitch, <1 = lower pitch)

        Returns:
            Pitch-shifted sample
        """
        # Professional pitch shifting using high-quality resampling
        if abs(ratio - 1.0) < 0.01:
            return sample_data

        # Use scipy's high-quality FFT-based resampling
        from scipy import signal

        new_length = int(len(sample_data) / ratio)
        return signal.resample(sample_data, new_length)

    def _time_stretch_sample(self, sample_data: np.ndarray, ratio: float) -> np.ndarray:
        """
        Simple time stretching.

        Args:
            sample_data: Input sample
            ratio: Time stretch ratio (>1 = longer, <1 = shorter)

        Returns:
            Time-stretched sample
        """
        if abs(ratio - 1.0) < 0.01:
            return sample_data

        # Simple implementation - repeat/interpolate
        new_length = int(len(sample_data) * ratio)
        return np.interp(
            np.linspace(0, len(sample_data) - 1, new_length),
            np.arange(len(sample_data)),
            sample_data,
        )

    def _apply_filter(self, sample_data: np.ndarray, filter_params: dict[str, Any]) -> np.ndarray:
        """Apply filter to sample."""
        from scipy import signal

        cutoff = filter_params.get("cutoff", 1000.0)
        order = filter_params.get("order", 4)
        btype = filter_params.get("type", "lowpass")

        # Normalize cutoff frequency
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff / nyquist

        if normalized_cutoff >= 1.0:
            return sample_data

        # Design filter
        b, a = signal.butter(order, normalized_cutoff, btype=btype)

        # Apply filter
        return signal.filtfilt(b, a, sample_data)

    def convert_sample_format(
        self, sample_data: np.ndarray, from_format: str, to_format: str
    ) -> np.ndarray:
        """
        Convert between sample formats.

        Args:
            sample_data: Input sample data
            from_format: Source format ('int16', 'int24', 'int32', 'float32', etc.)
            to_format: Target format

        Returns:
            Converted sample data
        """
        # Convert from source format to float32
        if from_format == "int16":
            sample_data = sample_data.astype(np.float32) / 32768.0
        elif from_format == "int24":
            # 24-bit samples are typically stored as 32-bit with padding
            sample_data = sample_data.astype(np.float32) / 8388608.0
        elif from_format == "int32":
            sample_data = sample_data.astype(np.float32) / 2147483648.0
        elif from_format == "float32":
            pass  # Already in correct format
        else:
            raise ValueError(f"Unsupported source format: {from_format}")

        # Convert to target format
        if to_format == "float32":
            return sample_data
        elif to_format == "int16":
            return np.clip(sample_data * 32767, -32768, 32767).astype(np.int16)
        elif to_format == "int24":
            clipped = np.clip(sample_data * 8388607, -8388608, 8388607)
            # 24-bit samples need special handling
            return clipped.astype(np.int32)
        elif to_format == "int32":
            return np.clip(sample_data * 2147483647, -2147483648, 2147483647).astype(np.int32)
        else:
            raise ValueError(f"Unsupported target format: {to_format}")

    def get_processing_info(self) -> dict[str, Any]:
        """Get information about current processing state."""
        return {
            "sample_rate": self.sample_rate,
            "buffer_size": len(self.processing_buffer),
            "pitch_shift_ratio": self.pitch_shift_ratio,
            "time_stretch_ratio": self.time_stretch_ratio,
            "filter_cutoff": self.filter_cutoff,
            "filter_resonance": self.filter_resonance,
        }
