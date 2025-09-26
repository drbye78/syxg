"""
Looper effect implementation for XG effects package.
"""

import math
from typing import Dict, Any, Tuple
import numpy as np


class LooperEffect:
    """
    Looper effect implementation.

    Creates looping effects with variable speed and reverse playback.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reset()

    def reset(self):
        """Reset the looper effect state"""
        # Create loop buffer (2 seconds)
        self.loop_buffer = [0.0] * (self.sample_rate * 2)
        self.buffer_pos = 0
        self.loop_length = self.sample_rate  # 1 second default
        self.is_recording = False
        self.is_playing = False

    def process(self, left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process audio through looper effect.

        Parameters:
        - loop: loop length (0.0-1.0, maps to different loop lengths)
        - speed: playback speed (0.0-1.0)
        - reverse: reverse playback (0.0-1.0)
        - level: output level (0.0-1.0)
        """
        # Get parameters
        loop = params.get("loop", 0.5)
        speed = params.get("speed", 0.5) * 2.0  # 0-2x speed
        reverse = params.get("reverse", 0.5)
        level = params.get("level", 0.5)

        # Initialize state if needed
        if "looper" not in state:
            state["looper"] = {
                "loop_buffer": [0.0] * (self.sample_rate * 2),
                "buffer_pos": 0,
                "loop_length": self.sample_rate,
                "is_recording": False,
                "is_playing": False,
                "playback_pos": 0.0
            }

        # Get input sample
        input_sample = (left + right) / 2.0

        looper_state = state["looper"]

        # Update loop length based on parameter
        looper_state["loop_length"] = int(self.sample_rate * (0.5 + loop * 1.5))  # 0.5-2 seconds

        # Record input if recording is enabled
        if looper_state["is_recording"]:
            looper_state["loop_buffer"][looper_state["buffer_pos"]] = input_sample
            looper_state["buffer_pos"] = (looper_state["buffer_pos"] + 1) % looper_state["loop_length"]

        # Generate output
        output_sample = 0.0
        if looper_state["is_playing"]:
            # Calculate playback position
            playback_pos = looper_state["playback_pos"]

            # Apply speed
            playback_pos += speed
            if playback_pos >= looper_state["loop_length"]:
                playback_pos = 0.0

            # Apply reverse
            if reverse > 0.5:
                actual_pos = looper_state["loop_length"] - 1 - int(playback_pos)
            else:
                actual_pos = int(playback_pos)

            # Get sample from buffer
            if 0 <= actual_pos < len(looper_state["loop_buffer"]):
                output_sample = looper_state["loop_buffer"][actual_pos]

            looper_state["playback_pos"] = playback_pos

        # Mix input and loop output
        output = input_sample * (1 - level) + output_sample * level

        return (output, output)

    def start_recording(self, state: Dict[str, Any]):
        """Start recording into the loop buffer"""
        if "looper" in state:
            state["looper"]["is_recording"] = True
            state["looper"]["buffer_pos"] = 0  # Reset position

    def stop_recording(self, state: Dict[str, Any]):
        """Stop recording"""
        if "looper" in state:
            state["looper"]["is_recording"] = False

    def start_playback(self, state: Dict[str, Any]):
        """Start loop playback"""
        if "looper" in state:
            state["looper"]["is_playing"] = True
            state["looper"]["playback_pos"] = 0.0

    def stop_playback(self, state: Dict[str, Any]):
        """Stop loop playback"""
        if "looper" in state:
            state["looper"]["is_playing"] = False


# Factory function for creating looper effect
def create_looper_effect(sample_rate: int = 44100):
    """Create a looper effect instance"""
    return LooperEffect(sample_rate)


# Process function for integration with main effects system
def process_looper_effect(left: float, right: float, params: Dict[str, float], state: Dict[str, Any]) -> Tuple[float, float]:
    """Process audio through looper effect (for integration)"""
    effect = LooperEffect()
    return effect.process(left, right, params, state)


# Control functions for integration
def start_looper_recording(state: Dict[str, Any]):
    """Start recording for looper effect"""
    effect = LooperEffect()
    effect.start_recording(state)


def stop_looper_recording(state: Dict[str, Any]):
    """Stop recording for looper effect"""
    effect = LooperEffect()
    effect.stop_recording(state)


def start_looper_playback(state: Dict[str, Any]):
    """Start playback for looper effect"""
    effect = LooperEffect()
    effect.start_playback(state)


def stop_looper_playback(state: Dict[str, Any]):
    """Stop playback for looper effect"""
    effect = LooperEffect()
    effect.stop_playback(state)
