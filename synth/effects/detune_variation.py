"""
Detune Variation effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple, List
import numpy as np


class DetuneVariationEffect:
    """
    Detune Variation effect implementation.

    Creates chorus-like effects by slightly detuning the signal with multiple detuning options.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the detune variation effect state"""
        # Detuning buffers
        self.delay_buffer = [0.0] * int(self.sample_rate * 0.1)  # 100ms buffer
        self.buffer_pos = 0

        # Multiple detune voices
        self.detune_voices = 4
        self.voice_buffers = [[0.0] * int(self.sample_rate * 0.1) for _ in range(self.detune_voices)]
        self.voice_pos = [0] * self.detune_voices

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through detune variation effect.

        Parameters:
        - shift: detune amount (0.0-1.0, maps to -50 to +50 cents)
        - feedback: feedback amount (0.0-1.0)
        - mix: dry/wet mix (0.0-1.0)
        - formant: formant preservation (0.0-1.0)
        - voices: number of detune voices (0.0-1.0, maps to 1-4 voices)
        - spread: detune spread (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        shift = params.get("shift", 0.5) * 100.0 - 50.0  # -50 to +50 cents
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        formant = params.get("formant", 0.5)
        voices = int(params.get("voices", 0.5) * 3) + 1  # 1-4 voices
        spread = params.get("spread", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "detune_variation" not in state:
            state["detune_variation"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),
                "buffer_pos": 0,
                "voice_buffers": [[0.0] * int(self.sample_rate * 0.1) for _ in range(4)],
                "voice_pos": [0] * 4
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        # Store in delay buffer
        detune_state = state["detune_variation"]
        detune_state["delay_buffer"][detune_state["buffer_pos"]] = input_sample
        detune_state["buffer_pos"] = (detune_state["buffer_pos"] + 1) % len(detune_state["delay_buffer"])

        # Generate detuned voices
        detune_mix = 0.0
        for i in range(min(voices, len(detune_state["voice_buffers"]))):
            # Calculate detune amount for this voice
            voice_shift = shift + (spread * 20.0 * (i - (voices - 1) / 2.0))  # Spread voices
            pitch_factor = 2 ** (voice_shift / 1200.0)  # Convert cents to ratio

            # Calculate read position
            read_pos = detune_state["buffer_pos"] - int(len(detune_state["delay_buffer"]) * (1 - pitch_factor))
            if read_pos < 0:
                read_pos += len(detune_state["delay_buffer"])

            # Get detuned sample
            detuned_sample = detune_state["delay_buffer"][int(read_pos)]

            # Apply feedback
            detuned_sample += feedback * detune_state["voice_buffers"][i][detune_state["voice_pos"][i]]

            # Apply formant preservation
            if formant > 0:
                # Simple formant boost
                formant_boost = 1.0 + formant * 0.3
                detuned_sample *= formant_boost

            # Store for feedback
            detune_state["voice_buffers"][i][detune_state["voice_pos"][i]] = detuned_sample
            detune_state["voice_pos"][i] = (detune_state["voice_pos"][i] + 1) % len(detune_state["voice_buffers"][i])

            detune_mix += detuned_sample

        # Average voices
        if voices > 0:
            detune_mix /= voices

        # Mix dry and wet signals
        output = input_sample * (1 - mix) + detune_mix * mix

        # Apply level
        return (output * level, output * level)


# Factory function for creating detune variation effect
def create_detune_variation_effect(sample_rate: int = 44100):
    """Create a detune variation effect instance"""
    return DetuneVariationEffect(sample_rate)


# Process function for integration with main effects system
def process_detune_variation_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through detune variation effect (for integration)"""
    effect = DetuneVariationEffect()
    return effect.process(left, right, params, state)
