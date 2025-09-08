"""
Stereo Imager effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class StereoImagerEffect:
    """
    Stereo Imager effect implementation.

    Enhances or manipulates stereo field for better spatial imaging.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the stereo imager effect state"""
        # Filter states for frequency-dependent stereo processing
        self.low_freq_state = {"left": 0.0, "right": 0.0}
        self.mid_freq_state = {"left": 0.0, "right": 0.0}
        self.high_freq_state = {"left": 0.0, "right": 0.0}

        # Delay states for stereo widening
        self.delay_state = {"left": 0.0, "right": 0.0}

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through stereo imager effect.

        Parameters:
        - width: stereo width (0.0-1.0, 0=mono, 1=wide stereo)
        - depth: processing depth (0.0-1.0)
        - reverb: reverb enhancement (0.0-1.0)
        - level: output level (0.0-1.0)
        - center: center channel boost (0.0-1.0)
        - sides: side channels boost (0.0-1.0)
        - low_freq_width: low frequency stereo width (0.0-1.0)
        - high_freq_width: high frequency stereo width (0.0-1.0)
        """
        # Get parameters
        width = params.get("width", 0.5)
        depth = params.get("depth", 0.5)
        reverb = params.get("reverb", 0.5)
        level = params.get("level", 0.5)
        center = params.get("center", 0.5)
        sides = params.get("sides", 0.5)
        low_freq_width = params.get("low_freq_width", 0.5)
        high_freq_width = params.get("high_freq_width", 0.5)

        # Initialize state if needed
        if "stereo_imager" not in state:
            state["stereo_imager"] = {
                "low_freq_state": {"left": 0.0, "right": 0.0},
                "mid_freq_state": {"left": 0.0, "right": 0.0},
                "high_freq_state": {"left": 0.0, "right": 0.0},
                "delay_state": {"left": 0.0, "right": 0.0}
            }

        stereo_imager_state = state["stereo_imager"]

        # Apply frequency-dependent stereo processing
        left_processed, right_processed = self._apply_frequency_stereo(
            left, right, low_freq_width, high_freq_width, stereo_imager_state
        )

        # Apply stereo widening
        left_wide, right_wide = self._apply_stereo_widening(
            left_processed, right_processed, width, stereo_imager_state
        )

        # Apply center/sides processing
        left_center, right_center = self._apply_center_sides(
            left_wide, right_wide, center, sides
        )

        # Apply reverb enhancement
        left_reverb, right_reverb = self._apply_reverb_enhancement(
            left_center, right_center, reverb, stereo_imager_state
        )

        # Mix processed and original signals based on depth
        left_out = left * (1 - depth) + left_reverb * depth
        right_out = right * (1 - depth) + right_reverb * depth

        # Apply level
        return (left_out * level, right_out * level)

    def _apply_frequency_stereo(self, left: float, right: float, low_freq_width: float,
                               high_freq_width: float, state: Dict[str, Any]) -> Tuple[float, float]:
        """Apply frequency-dependent stereo processing"""
        # Calculate center and side signals
        center = (left + right) / 2.0
        sides = (left - right) / 2.0

        # Low frequency processing (below ~200 Hz)
        # Low frequencies are naturally mono, so we can enhance or reduce their stereo
        low_center = center * 0.8  # Low frequencies are mostly in center
        low_sides = sides * low_freq_width  # Control stereo width of lows

        # High frequency processing (above ~5kHz)
        # High frequencies can be more stereo
        high_center = center * 0.2  # Less low freq content in highs
        high_sides = sides * (1.0 + high_freq_width)  # Enhance stereo of highs

        # Mid frequency processing (200Hz - 5kHz)
        mid_center = center * 0.5
        mid_sides = sides * 0.8

        # Combine frequency bands
        left_out = low_center + low_sides + mid_center + mid_sides + high_center + high_sides
        right_out = low_center - low_sides + mid_center - mid_sides + high_center - high_sides

        return (left_out, right_out)

    def _apply_stereo_widening(self, left: float, right: float, width: float,
                              state: Dict[str, Any]) -> Tuple[float, float]:
        """Apply stereo widening using delay and phase processing"""
        # Calculate center and side signals
        center = (left + right) / 2.0
        sides = (left - right) / 2.0

        # Apply delay to sides for widening effect
        delay_samples = int(width * self.sample_rate / 1000.0)  # 0-1ms delay
        if delay_samples > 0:
            # Simple delay using state
            delayed_sides = state["delay_state"]["left"] * 0.7 + sides * 0.3
            state["delay_state"]["left"] = sides
            sides = delayed_sides

        # Enhance sides based on width
        enhanced_sides = sides * (1.0 + width * 0.5)

        # Reconstruct stereo signal
        left_out = center + enhanced_sides
        right_out = center - enhanced_sides

        return (left_out, right_out)

    def _apply_center_sides(self, left: float, right: float, center_boost: float,
                           sides_boost: float) -> Tuple[float, float]:
        """Apply center and sides channel processing"""
        # Extract center and sides
        center = (left + right) / 2.0
        sides = (left - right) / 2.0

        # Apply boosts
        center *= (1.0 + center_boost)
        sides *= (1.0 + sides_boost)

        # Reconstruct stereo signal
        left_out = center + sides
        right_out = center - sides

        return (left_out, right_out)

    def _apply_reverb_enhancement(self, left: float, right: float, reverb_amount: float,
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Apply reverb enhancement for better spatial imaging"""
        if reverb_amount == 0:
            return (left, right)

        # Simple reverb enhancement using allpass filters
        # This creates a sense of space without full reverb processing

        # Allpass filter for left channel
        g = 0.6 * reverb_amount  # Feedback coefficient
        allpass_delay = int(0.01 * self.sample_rate)  # 10ms delay

        # Simulate allpass processing (simplified)
        left_delayed = state["low_freq_state"]["left"]
        state["low_freq_state"]["left"] = left

        left_allpass = -g * left + left_delayed + g * left_delayed

        # Allpass filter for right channel
        right_delayed = state["low_freq_state"]["right"]
        state["low_freq_state"]["right"] = right

        right_allpass = -g * right + right_delayed + g * right_delayed

        # Mix original and processed signals
        left_out = left * (1 - reverb_amount * 0.3) + left_allpass * reverb_amount * 0.3
        right_out = right * (1 - reverb_amount * 0.3) + right_allpass * reverb_amount * 0.3

        return (left_out, right_out)


# Factory function for creating stereo imager effect
def create_stereo_imager_effect(sample_rate: int = 44100):
    """Create a stereo imager effect instance"""
    return StereoImagerEffect(sample_rate)


# Process function for integration with main effects system
def process_stereo_imager_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through stereo imager effect (for integration)"""
    effect = StereoImagerEffect()
    return effect.process(left, right, params, state)
