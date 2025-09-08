"""
Vibrato effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class VibratoEffect:
    """
    Vibrato effect implementation.

    Creates pitch modulation for adding expressiveness to sustained notes.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the vibrato effect state"""
        # Pitch shifting buffer
        self.delay_buffer = [0.0] * int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer_pos = 0

        # LFO state
        self.lfo_phase = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through vibrato effect.

        Parameters:
        - rate: LFO rate (0.0-1.0, maps to 1-10 Hz)
        - depth: modulation depth (0.0-1.0)
        - waveform: LFO waveform (0.0-1.0, maps to different waveforms)
        - delay: pre-delay before vibrato starts (0.0-1.0, maps to 0-100 ms)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        rate = 1.0 + params.get("rate", 0.5) * 9.0  # 1-10 Hz
        depth = params.get("depth", 0.5)
        waveform = int(params.get("waveform", 0.5) * 3)  # 0-3 waveforms
        delay = params.get("delay", 0.5) * 100.0  # 0-100 ms
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "vibrato" not in state:
            state["vibrato"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0,
                "lfo_phase": 0.0
            }

        # Get input samples
        left_input = left
        right_input = right

        vibrato_state = state["vibrato"]

        # Store inputs in delay buffer
        vibrato_state["delay_buffer"][vibrato_state["buffer_pos"]] = left_input
        vibrato_state["buffer_pos"] = (vibrato_state["buffer_pos"] + 1) % len(vibrato_state["delay_buffer"])

        # Update LFO
        vibrato_state["lfo_phase"] += 2 * math.pi * rate / self.sample_rate

        # Generate LFO waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(vibrato_state["lfo_phase"])
        elif waveform == 1:  # Triangle
            phase = vibrato_state["lfo_phase"] / (2 * math.pi)
            lfo_value = 1 - abs((phase % 1) * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(vibrato_state["lfo_phase"]) > 0 else -1
        else:  # Sawtooth
            phase = vibrato_state["lfo_phase"] / (2 * math.pi)
            lfo_value = (phase % 1) * 2 - 1

        # Calculate pitch shift factor
        pitch_shift = 1.0 + lfo_value * depth * 0.1  # Max ±10% pitch shift

        # Apply vibrato to left channel
        left_delay_samples = int(delay * self.sample_rate / 1000.0)
        left_read_pos = (vibrato_state["buffer_pos"] - left_delay_samples) % len(vibrato_state["delay_buffer"])
        left_delayed = vibrato_state["delay_buffer"][int(left_read_pos)]

        # Calculate modulated read position for vibrato
        vibrato_delay = int(left_delay_samples * pitch_shift)
        vibrato_read_pos = (vibrato_state["buffer_pos"] - vibrato_delay) % len(vibrato_state["delay_buffer"])
        left_vibrato = vibrato_state["delay_buffer"][int(vibrato_read_pos)]

        # Apply vibrato to right channel (with slight phase offset for stereo)
        right_delay_samples = int(delay * self.sample_rate / 1000.0)
        right_read_pos = (vibrato_state["buffer_pos"] - right_delay_samples) % len(vibrato_state["delay_buffer"])
        right_delayed = vibrato_state["delay_buffer"][int(right_read_pos)]

        # Calculate modulated read position for right channel
        right_vibrato_delay = int(right_delay_samples * pitch_shift)
        right_vibrato_read_pos = (vibrato_state["buffer_pos"] - right_vibrato_delay) % len(vibrato_state["delay_buffer"])
        right_vibrato = vibrato_state["delay_buffer"][int(right_vibrato_read_pos)]

        # Mix dry and wet signals
        left_output = left_input * (1 - depth) + left_vibrato * depth
        right_output = right_input * (1 - depth) + right_vibrato * depth

        # Apply level
        return (left_output * level, right_output * level)


# Factory function for creating vibrato effect
def create_vibrato_effect(sample_rate: int = 44100):
    """Create a vibrato effect instance"""
    return VibratoEffect(sample_rate)


# Process function for integration with main effects system
def process_vibrato_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through vibrato effect (for integration)"""
    effect = VibratoEffect()
    return effect.process(left, right, params, state)
