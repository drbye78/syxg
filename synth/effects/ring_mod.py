"""
Ring Mod effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class RingModEffect:
    """
    Ring Mod effect implementation.

    Creates metallic, bell-like sounds by multiplying the input signal with an oscillator.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the ring mod effect state"""
        # LFO state
        self.lfo_phase = 0.0

        # Filter state for smoothing
        self.filter_state = 0.0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through ring mod effect.

        Parameters:
        - frequency: modulation frequency (0.0-1.0, maps to 20-5000 Hz)
        - depth: modulation depth (0.0-1.0)
        - waveform: LFO waveform (0.0-1.0, maps to different waveforms)
        - mix: dry/wet mix (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        frequency = 20 + params.get("frequency", 0.5) * 4980  # 20-5000 Hz
        depth = params.get("depth", 0.5)
        waveform = int(params.get("waveform", 0.5) * 3)  # 0-3 waveforms
        mix = params.get("mix", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "ring_mod" not in state:
            state["ring_mod"] = {
                "lfo_phase": 0.0,
                "filter_state": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        ring_mod_state = state["ring_mod"]

        # Update LFO
        ring_mod_state["lfo_phase"] += 2 * math.pi * frequency / self.sample_rate

        # Generate LFO waveform
        if waveform == 0:  # Sine
            lfo_value = math.sin(ring_mod_state["lfo_phase"])
        elif waveform == 1:  # Triangle
            phase = ring_mod_state["lfo_phase"] / (2 * math.pi)
            lfo_value = 1 - abs((phase % 1) * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(ring_mod_state["lfo_phase"]) > 0 else -1
        else:  # Sawtooth
            phase = ring_mod_state["lfo_phase"] / (2 * math.pi)
            lfo_value = (phase % 1) * 2 - 1

        # Apply ring modulation
        # Ring modulation is simply multiplication of carrier and modulator
        modulated = input_sample * lfo_value

        # Apply depth control
        modulated *= depth

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + modulated * mix

        # Apply level
        return (output * level, output * level)


# Factory function for creating ring mod effect
def create_ring_mod_effect(sample_rate: int = 44100):
    """Create a ring mod effect instance"""
    return RingModEffect(sample_rate)


# Process function for integration with main effects system
def process_ring_mod_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through ring mod effect (for integration)"""
    effect = RingModEffect()
    return effect.process(left, right, params, state)
