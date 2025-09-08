"""
Chorus/Reverb effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class ChorusReverbEffect:
    """
    Chorus/Reverb effect implementation.

    Combines chorus and reverb effects for rich, spacious sound.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the chorus/reverb effect state"""
        # Chorus state
        self.chorus_delay_lines = [np.zeros(4410) for _ in range(2)]  # 100ms delays
        self.chorus_lfo_phases = [0.0, 0.0]
        self.chorus_lfo_rates = [1.0, 0.5]
        self.chorus_lfo_depths = [0.5, 0.3]
        self.chorus_write_indices = [0, 0]
        self.chorus_feedback_buffers = [0.0, 0.0]

        # Reverb state
        self.reverb_allpass_buffers = [np.zeros(441) for _ in range(4)]
        self.reverb_allpass_indices = [0] * 4
        self.reverb_comb_buffers = [np.zeros(441 * i) for i in range(1, 5)]
        self.reverb_comb_indices = [0] * 4
        self.reverb_early_reflection_buffer = np.zeros(441)
        self.reverb_early_reflection_index = 0
        self.reverb_late_reflection_buffer = np.zeros(441 * 10)
        self.reverb_late_reflection_index = 0

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through chorus/reverb effect.

        Parameters:
        - chorus: chorus amount (0.0-1.0)
        - reverb: reverb amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - level: output level (0.0-1.0)
        - chorus_rate: chorus LFO rate (0.0-1.0)
        - chorus_depth: chorus modulation depth (0.0-1.0)
        - reverb_time: reverb decay time (0.0-1.0)
        - reverb_damping: reverb high frequency damping (0.0-1.0)
        """
        # Get parameters
        chorus = params.get("chorus", 0.5)
        reverb = params.get("reverb", 0.5)
        mix = params.get("mix", 0.5)
        level = params.get("level", 0.5)
        chorus_rate = params.get("chorus_rate", 0.5) * 5.0  # 0-5 Hz
        chorus_depth = params.get("chorus_depth", 0.5)
        reverb_time = params.get("reverb_time", 0.5) * 5.0  # 0-5 seconds
        reverb_damping = params.get("reverb_damping", 0.5)

        # Initialize state if needed
        if "chorus_reverb" not in state:
            state["chorus_reverb"] = {
                "chorus_delay_lines": [np.zeros(4410) for _ in range(2)],
                "chorus_lfo_phases": [0.0, 0.0],
                "chorus_lfo_rates": [1.0, 0.5],
                "chorus_lfo_depths": [0.5, 0.3],
                "chorus_write_indices": [0, 0],
                "chorus_feedback_buffers": [0.0, 0.0],
                "reverb_allpass_buffers": [np.zeros(441) for _ in range(4)],
                "reverb_allpass_indices": [0] * 4,
                "reverb_comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
                "reverb_comb_indices": [0] * 4,
                "reverb_early_reflection_buffer": np.zeros(441),
                "reverb_early_reflection_index": 0,
                "reverb_late_reflection_buffer": np.zeros(441 * 10),
                "reverb_late_reflection_index": 0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        chorus_reverb_state = state["chorus_reverb"]

        # Apply chorus effect
        chorus_output = self._apply_chorus(input_sample, chorus_rate, chorus_depth, chorus_reverb_state)

        # Apply reverb effect
        reverb_output = self._apply_reverb(input_sample, reverb_time, reverb_damping, chorus_reverb_state)

        # Mix chorus and reverb
        combined_wet = chorus_output * chorus + reverb_output * reverb

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + combined_wet * mix

        # Apply level
        return (output * level, output * level)

    def _apply_chorus(self, input_sample: float, rate: float, depth: float, state: Dict[str, Any]) -> float:
        """Apply chorus effect"""
        # Update LFO phases
        state["chorus_lfo_phases"][0] = (state["chorus_lfo_phases"][0] + state["chorus_lfo_rates"][0] * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        state["chorus_lfo_phases"][1] = (state["chorus_lfo_phases"][1] + state["chorus_lfo_rates"][1] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delays
        base_delay_samples = int(0.02 * self.sample_rate)  # 20ms base delay
        modulation1 = int(state["chorus_lfo_depths"][0] * depth * self.sample_rate / 1000.0 * (1 + math.sin(state["chorus_lfo_phases"][0])) / 2)
        modulation2 = int(state["chorus_lfo_depths"][1] * depth * self.sample_rate / 1000.0 * (1 + math.sin(state["chorus_lfo_phases"][1])) / 2)

        total_delay1 = base_delay_samples + modulation1
        total_delay2 = base_delay_samples + modulation2

        # Clamp delays
        max_delay = len(state["chorus_delay_lines"][0]) - 1
        total_delay1 = min(total_delay1, max_delay)
        total_delay2 = min(total_delay2, max_delay)

        # Read from delay buffers
        read_index1 = (state["chorus_write_indices"][0] - total_delay1) % len(state["chorus_delay_lines"][0])
        read_index2 = (state["chorus_write_indices"][1] - total_delay2) % len(state["chorus_delay_lines"][1])

        delayed_sample1 = state["chorus_delay_lines"][0][int(read_index1)]
        delayed_sample2 = state["chorus_delay_lines"][1][int(read_index2)]

        # Apply feedback
        feedback_sample1 = delayed_sample1 * 0.3 + state["chorus_feedback_buffers"][0] * 0.2
        feedback_sample2 = delayed_sample2 * 0.3 + state["chorus_feedback_buffers"][1] * 0.2

        # Write to delay buffers
        state["chorus_delay_lines"][0][state["chorus_write_indices"][0]] = input_sample + feedback_sample1
        state["chorus_delay_lines"][1][state["chorus_write_indices"][1]] = input_sample + feedback_sample2

        # Update indices
        state["chorus_write_indices"][0] = (state["chorus_write_indices"][0] + 1) % len(state["chorus_delay_lines"][0])
        state["chorus_write_indices"][1] = (state["chorus_write_indices"][1] + 1) % len(state["chorus_delay_lines"][1])

        # Update feedback buffers
        state["chorus_feedback_buffers"][0] = feedback_sample1
        state["chorus_feedback_buffers"][1] = feedback_sample2

        # Mix delayed samples
        return (delayed_sample1 + delayed_sample2) * 0.5

    def _apply_reverb(self, input_sample: float, time: float, damping: float, state: Dict[str, Any]) -> float:
        """Apply reverb effect using Schroeder algorithm"""
        # Pre-delay
        pre_delay_samples = int(0.02 * self.sample_rate)  # 20ms pre-delay
        if pre_delay_samples >= len(state["reverb_early_reflection_buffer"]):
            pre_delay_samples = len(state["reverb_early_reflection_buffer"]) - 1

        # Write to pre-delay buffer
        state["reverb_early_reflection_buffer"][state["reverb_early_reflection_index"]] = input_sample
        state["reverb_early_reflection_index"] = (state["reverb_early_reflection_index"] + 1) % len(state["reverb_early_reflection_buffer"])

        # Read from pre-delay buffer
        pre_delay_index = (state["reverb_early_reflection_index"] - pre_delay_samples) % len(state["reverb_early_reflection_buffer"])
        pre_delay_sample = state["reverb_early_reflection_buffer"][int(pre_delay_index)]

        # Early reflections
        early_reflections = pre_delay_sample * 0.7

        # Comb filter processing
        comb_input = early_reflections
        comb_output = 0.0

        for i in range(len(state["reverb_comb_buffers"])):
            delay_length = int(time * self.sample_rate * (i + 1) / 8.0)
            if delay_length >= len(state["reverb_comb_buffers"][i]):
                delay_length = len(state["reverb_comb_buffers"][i]) - 1

            # Read from delay buffer
            read_index = (state["reverb_comb_indices"][i] - delay_length) % len(state["reverb_comb_buffers"][i])
            comb_sample = state["reverb_comb_buffers"][i][int(read_index)]

            # Calculate feedback
            feedback = 0.7 + (i * 0.05)

            # Write to delay buffer with feedback and damping
            state["reverb_comb_buffers"][i][state["reverb_comb_indices"][i]] = comb_input + comb_sample * feedback * (1.0 - damping)
            state["reverb_comb_indices"][i] = (state["reverb_comb_indices"][i] + 1) % len(state["reverb_comb_buffers"][i])

            # Add to output
            comb_output += comb_sample * 0.9

        # Allpass filter processing for diffusion
        allpass_output = comb_output
        for i in range(len(state["reverb_allpass_buffers"])):
            delay_length = int(time * self.sample_rate * (i + 1) / 16.0)
            if delay_length >= len(state["reverb_allpass_buffers"][i]):
                delay_length = len(state["reverb_allpass_buffers"][i]) - 1

            # Read from delay buffer
            read_index = (state["reverb_allpass_indices"][i] - delay_length) % len(state["reverb_allpass_buffers"][i])
            allpass_sample = state["reverb_allpass_buffers"][i][int(read_index)]

            # Allpass filter
            g = 0.7
            state["reverb_allpass_buffers"][i][state["reverb_allpass_indices"][i]] = allpass_output
            state["reverb_allpass_indices"][i] = (state["reverb_allpass_indices"][i] + 1) % len(state["reverb_allpass_buffers"][i])

            # Apply allpass formula
            allpass_output = -g * allpass_output + allpass_sample + g * allpass_sample

        return allpass_output * 0.6


# Factory function for creating chorus/reverb effect
def create_chorus_reverb_effect(sample_rate: int = 44100):
    """Create a chorus/reverb effect instance"""
    return ChorusReverbEffect(sample_rate)


# Process function for integration with main effects system
def process_chorus_reverb_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through chorus/reverb effect (for integration)"""
    effect = ChorusReverbEffect()
    return effect.process(left, right, params, state)
