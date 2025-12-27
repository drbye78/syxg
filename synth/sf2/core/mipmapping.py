"""
SF2 Audio Mip-Mapping System

High-quality pitch-shifting through pre-filtered sample versions.
Provides anti-aliased high-pitch note playback for professional sound quality.
"""

import numpy as np
from typing import Dict, Optional, List, Any
import time
from collections import OrderedDict
import threading


class SampleMipMap:
    """
    Audio mip-mapping system for high-quality pitch-shifting.

    Stores multiple filtered versions of samples for different pitch ranges.
    Prevents aliasing artifacts in high-pitch notes (C6+) by using
    appropriately filtered sample versions.
    """

    # Mip level definitions with pitch ratio thresholds
    MIP_LEVELS = [
        {'name': 'original', 'cutoff': None, 'max_ratio': 2.0, 'description': 'Original sample for normal pitch ranges'},
        {'name': 'filtered_1', 'cutoff': 8000, 'max_ratio': 4.0, 'description': 'Lightly filtered for 2x-4x pitch ratios'},
        {'name': 'filtered_2', 'cutoff': 4000, 'max_ratio': 8.0, 'description': 'Moderately filtered for 4x-8x pitch ratios'},
        {'name': 'filtered_3', 'cutoff': 2000, 'max_ratio': float('inf'), 'description': 'Heavily filtered for 8x+ pitch ratios'}
    ]

    def __init__(self, original_sample: np.ndarray, sample_rate: int):
        """
        Initialize mip-map with original sample.

        Args:
            original_sample: Original 16-bit PCM sample data
            sample_rate: Sample rate in Hz (typically 44100)
        """
        self.original_sample = original_sample.astype(np.float32)
        self.sample_rate = sample_rate

        # Generated mip levels (lazy initialization)
        self.generated_levels: Dict[int, Optional[np.ndarray]] = {}
        self.generation_times: Dict[int, float] = {}

        # Quality metrics for optimization
        self.quality_metrics: Dict[int, Dict[str, float]] = {}

        # Store original in level 0
        self.generated_levels[0] = self.original_sample

    def get_level(self, level: int) -> np.ndarray:
        """
        Get mip level sample data, generating it if needed.

        Args:
            level: Mip level (0=original, 1-3=filtered versions)

        Returns:
            Filtered sample data for the specified level
        """
        if level < 0 or level >= len(self.MIP_LEVELS):
            raise ValueError(f"Invalid mip level {level}. Must be 0-{len(self.MIP_LEVELS)-1}")

        # Return original for level 0
        if level == 0:
            return self.original_sample

        # Generate level if not already created
        if level not in self.generated_levels or self.generated_levels[level] is None:
            start_time = time.time()
            self.generated_levels[level] = self._generate_level(level)
            self.generation_times[level] = time.time() - start_time

        return self.generated_levels[level]

    def _generate_level(self, level: int) -> np.ndarray:
        """
        Generate filtered version for the specified mip level.

        Uses high-quality IIR filtering with zero-phase response to prevent
        phase distortion while providing steep anti-aliasing.
        """
        try:
            from scipy.signal import butter, filtfilt
        except ImportError:
            # Fallback to simple low-pass if scipy not available
            print("Warning: scipy not available, using simple low-pass filter")
            return self._generate_simple_filter(level)

        config = self.MIP_LEVELS[level]
        cutoff_freq = config['cutoff']

        if cutoff_freq is None:
            return self.original_sample

        # Design high-quality filter
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist

        # Ensure cutoff is valid
        normalized_cutoff = min(normalized_cutoff, 0.95)  # Stay below Nyquist

        # 8th order Butterworth filter for steep rolloff
        filter_order = 8
        try:
            filter_result = butter(filter_order, normalized_cutoff, btype='low')
            if filter_result is None or len(filter_result) != 2:
                raise ValueError("Invalid filter response from butter()")
            b, a = filter_result
        except Exception as e:
            print(f"Filter design failed, using simple filter: {e}")
            return self._generate_simple_filter(level)

        # Apply zero-phase filtering to preserve transients
        try:
            filtered = filtfilt(b, a, self.original_sample)
        except Exception as e:
            print(f"Filter application failed, using simple filter: {e}")
            return self._generate_simple_filter(level)

        # Calculate quality metrics
        self._calculate_quality_metrics(level, filtered)

        return filtered.astype(np.float32)

    def _generate_simple_filter(self, level: int) -> np.ndarray:
        """
        Fallback simple low-pass filter when scipy is not available.
        """
        config = self.MIP_LEVELS[level]
        cutoff_freq = config['cutoff']

        if cutoff_freq is None:
            return self.original_sample

        # Simple 1-pole IIR low-pass
        # coefficient = cutoff_freq / (cutoff_freq + sample_rate/2)
        # This is a rough approximation
        alpha = cutoff_freq / (cutoff_freq + self.sample_rate / 2)

        filtered = np.zeros_like(self.original_sample)
        filtered[0] = self.original_sample[0]

        for i in range(1, len(self.original_sample)):
            filtered[i] = alpha * self.original_sample[i] + (1 - alpha) * filtered[i-1]

        return filtered

    def _calculate_quality_metrics(self, level: int, filtered_sample: np.ndarray):
        """
        Calculate quality metrics for the filtered sample.

        Tracks frequency response, aliasing potential, and other quality indicators.
        """
        # Simple RMS difference from original (higher = more filtering)
        if level > 0:
            diff_rms = np.sqrt(np.mean((self.original_sample - filtered_sample) ** 2))
            original_rms = np.sqrt(np.mean(self.original_sample ** 2))
            attenuation_db = 20 * np.log10(diff_rms / original_rms) if original_rms > 0 else -float('inf')

            self.quality_metrics[level] = {
                'attenuation_db': attenuation_db,
                'filter_cutoff': self.MIP_LEVELS[level]['cutoff'],
                'sample_length': len(filtered_sample),
                'generation_time': self.generation_times.get(level, 0.0)
            }

    def get_memory_usage(self) -> int:
        """Get total memory usage of all generated mip levels in bytes."""
        total_bytes = 0
        for level_data in self.generated_levels.values():
            if level_data is not None:
                total_bytes += level_data.nbytes
        return total_bytes

    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about mip-map generation."""
        generated_levels = [level for level, data in self.generated_levels.items() if data is not None]

        return {
            'total_levels': len(self.MIP_LEVELS),
            'generated_levels': len(generated_levels),
            'memory_usage_bytes': self.get_memory_usage(),
            'memory_usage_mb': self.get_memory_usage() / (1024 * 1024),
            'generation_times': self.generation_times.copy(),
            'quality_metrics': self.quality_metrics.copy(),
            'levels_info': [
                {
                    'level': i,
                    'name': config['name'],
                    'generated': i in self.generated_levels and self.generated_levels[i] is not None,
                    'cutoff': config['cutoff'],
                    'max_ratio': config['max_ratio']
                }
                for i, config in enumerate(self.MIP_LEVELS)
            ]
        }

    def clear_level(self, level: int):
        """Clear a specific mip level to free memory."""
        if level in self.generated_levels and level != 0:  # Never clear original
            self.generated_levels[level] = None
            if level in self.generation_times:
                del self.generation_times[level]
            if level in self.quality_metrics:
                del self.quality_metrics[level]

    def preload_levels(self, max_level: int = 3):
        """Preload mip levels up to the specified maximum."""
        for level in range(1, min(max_level + 1, len(self.MIP_LEVELS))):
            self.get_level(level)  # Triggers generation

    @classmethod
    def select_mip_level(cls, pitch_ratio: float) -> int:
        """
        Select appropriate mip level based on pitch shift ratio.

        Args:
            pitch_ratio: Playback speed / original speed (e.g., 4.0 for 4x speedup)

        Returns:
            Optimal mip level for the pitch ratio
        """
        for level, config in enumerate(cls.MIP_LEVELS):
            if pitch_ratio <= config['max_ratio']:
                return level

        # Fallback to highest filtering level
        return len(cls.MIP_LEVELS) - 1

    @classmethod
    def get_level_info(cls, level: int) -> Dict[str, Any]:
        """Get information about a specific mip level."""
        if level < 0 or level >= len(cls.MIP_LEVELS):
            raise ValueError(f"Invalid mip level {level}")

        return cls.MIP_LEVELS[level].copy()


class MipLevelSelector:
    """
    Intelligent mip level selection with hysteresis.

    Prevents rapid level switching that could cause audio artifacts.
    Uses hysteresis to ensure stable level selection.
    """

    def __init__(self, hysteresis_threshold: float = 0.1):
        """
        Initialize selector with hysteresis.

        Args:
            hysteresis_threshold: Fraction of range for hysteresis (0.1 = 10%)
        """
        self.current_level = 0
        self.hysteresis_threshold = hysteresis_threshold
        self.last_pitch_ratio = 1.0

    def select_stable_level(self, pitch_ratio: float) -> int:
        """
        Select mip level with hysteresis for stability.

        Args:
            pitch_ratio: Current pitch ratio

        Returns:
            Stable mip level (may not change immediately)
        """
        target_level = SampleMipMap.select_mip_level(pitch_ratio)

        # Allow immediate jumps for large ratio changes
        if abs(target_level - self.current_level) > 1:
            self.current_level = target_level
            self.last_pitch_ratio = pitch_ratio
            return self.current_level

        # Apply hysteresis for adjacent level changes
        if target_level > self.current_level:
            # Switching up (more filtering needed)
            ratio_threshold = SampleMipMap.MIP_LEVELS[self.current_level]['max_ratio']
            hysteresis_ratio = ratio_threshold * (1 + self.hysteresis_threshold)

            if pitch_ratio > hysteresis_ratio:
                self.current_level = target_level
                self.last_pitch_ratio = pitch_ratio

        elif target_level < self.current_level:
            # Switching down (less filtering needed)
            ratio_threshold = SampleMipMap.MIP_LEVELS[target_level]['max_ratio']
            hysteresis_ratio = ratio_threshold * (1 - self.hysteresis_threshold)

            if pitch_ratio < hysteresis_ratio:
                self.current_level = target_level
                self.last_pitch_ratio = pitch_ratio

        return self.current_level

    def force_level(self, level: int):
        """Force a specific mip level (for testing/debugging)."""
        if 0 <= level < len(SampleMipMap.MIP_LEVELS):
            self.current_level = level

    def reset(self):
        """Reset to default state."""
        self.current_level = 0
        self.last_pitch_ratio = 1.0

    def get_state(self) -> Dict[str, Any]:
        """Get current selector state."""
        return {
            'current_level': self.current_level,
            'last_pitch_ratio': self.last_pitch_ratio,
            'hysteresis_threshold': self.hysteresis_threshold,
            'level_info': SampleMipMap.get_level_info(self.current_level)
        }


def create_sample_mipmap(original_sample: np.ndarray, sample_rate: int) -> SampleMipMap:
    """
    Factory function to create a SampleMipMap instance.

    Args:
        original_sample: Original PCM sample data
        sample_rate: Sample rate in Hz

    Returns:
        Configured SampleMipMap instance
    """
    return SampleMipMap(original_sample, sample_rate)


def test_mipmapping():
    """Basic functionality test for mip-mapping system."""
    # Create test sample (1kHz sine wave)
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    test_sample = np.sin(2 * np.pi * 1000 * t).astype(np.float32)

    # Create mip-map
    mipmap = create_sample_mipmap(test_sample, sample_rate)

    # Test level generation
    for level in range(len(SampleMipMap.MIP_LEVELS)):
        level_data = mipmap.get_level(level)
        assert level_data is not None
        assert len(level_data) == len(test_sample)
        print(f"Level {level} ({SampleMipMap.MIP_LEVELS[level]['name']}): {len(level_data)} samples")

    # Test level selection
    test_ratios = [1.0, 2.5, 4.5, 9.0, 20.0]
    for ratio in test_ratios:
        level = SampleMipMap.select_mip_level(ratio)
        print(f"Ratio {ratio}: Level {level} ({SampleMipMap.MIP_LEVELS[level]['name']})")

    # Test selector
    selector = MipLevelSelector()
    for ratio in [1.0, 3.0, 5.0, 2.0, 7.0]:  # Test hysteresis
        level = selector.select_stable_level(ratio)
        print(f"Ratio {ratio}: Stable level {level}")

    stats = mipmap.get_generation_stats()
    print(f"Mip-map stats: {stats['generated_levels']}/{stats['total_levels']} levels, {stats['memory_usage_mb']:.2f} MB")

    print("✅ Mip-mapping system test passed!")
    return True


if __name__ == "__main__":
    test_mipmapping()
