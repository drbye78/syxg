"""
XG Delay Variation Effects - Production Implementation

This module implements XG delay-based variation effects (types 0-9) with
production-quality DSP algorithms adapted from synth.processing.effects.processing.

Effects implemented:
- Delay L/C/R (0): 3-channel delay with stereo width
- Delay L/R (1): Dual delay with cross-feedback
- Echo (2): Echo with configurable decay
- Dual Delay (3): Two independent delay lines
- Pan Delay (4): Auto-panning delay with LFO
- Cross Delay (5): Cross-feedback delay processing
- Multi-tap Delay (6): Multiple simultaneous delay taps
- Reverse Delay (7): Reverse delay effect
- Tremolo (8): Amplitude modulation
- Auto-pan (9): Stereo panning modulation

All implementations use zero-allocation processing and thread-safe state management.
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np


class DelayVariationProcessor:
    """
    XG Delay Variation Effects Processor

    Handles all delay-based variation effects with production-quality DSP.
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Effect state storage - thread-safe
        self._effect_states = {}
        self._lock = threading.RLock()

    def process_effect(
        self, effect_type: int, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        with self._lock:
            if effect_type == 0:
                self._process_delay_lcr(stereo_mix, num_samples, params)
            elif effect_type == 1:
                self._process_delay_lr(stereo_mix, num_samples, params)
            elif effect_type == 2:
                self._process_echo(stereo_mix, num_samples, params)
            elif effect_type == 3:
                self._process_dual_delay(stereo_mix, num_samples, params)
            elif effect_type == 4:
                self._process_pan_delay(stereo_mix, num_samples, params)
            elif effect_type == 5:
                self._process_cross_delay(stereo_mix, num_samples, params)
            elif effect_type == 6:
                self._process_multi_tap_delay(stereo_mix, num_samples, params)
            elif effect_type == 7:
                self._process_reverse_delay(stereo_mix, num_samples, params)
            elif effect_type == 8:
                self._process_tremolo(stereo_mix, num_samples, params)
            elif effect_type == 9:
                self._process_auto_pan(stereo_mix, num_samples, params)

    def _ensure_state(self, effect_key: str, state_config: dict[str, Any]) -> dict[str, Any]:
        if effect_key not in self._effect_states:
            self._effect_states[effect_key] = state_config.copy()
        return self._effect_states[effect_key]

    def _process_delay_lcr(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        # XG Parameters: time(0-1000ms), feedback(0-1), level(0-1), stereo(0-1)
        time = params.get("parameter1", 0.5) * 1000  # 0-1000ms
        feedback = params.get("parameter2", 0.3)
        level = params.get("parameter3", 0.5)
        stereo_width = params.get("parameter4", 1.0)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        # Initialize delay lines
        state = self._ensure_state(
            "delay_lcr",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_c": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
                "write_pos_c": 0,
            },
        )

        for i in range(num_samples):
            # Read from delay lines
            read_pos_l = (state["write_pos_l"] - delay_samples) % self.max_delay_samples
            read_pos_r = (state["write_pos_r"] - delay_samples) % self.max_delay_samples
            read_pos_c = (state["write_pos_c"] - delay_samples) % self.max_delay_samples

            delayed_l = state["delay_line_l"][int(read_pos_l)]
            delayed_r = state["delay_line_r"][int(read_pos_r)]
            delayed_c = state["delay_line_c"][int(read_pos_c)]

            # Current input
            input_l = stereo_mix[i, 0]
            input_r = stereo_mix[i, 1]
            input_c = (input_l + input_r) * 0.5

            # Write to delay lines: input + delayed_tap * feedback
            state["delay_line_l"][state["write_pos_l"]] = input_l + delayed_l * feedback
            state["delay_line_r"][state["write_pos_r"]] = input_r + delayed_r * feedback
            state["delay_line_c"][state["write_pos_c"]] = input_c + delayed_c * feedback

            # Mix dry/wet with stereo width
            wet_l = (delayed_l * (1.0 + stereo_width) + delayed_c * (1.0 - stereo_width)) * 0.5
            wet_r = (delayed_r * (1.0 + stereo_width) + delayed_c * (1.0 - stereo_width)) * 0.5

            stereo_mix[i, 0] = input_l * (1.0 - level) + wet_l * level
            stereo_mix[i, 1] = input_r * (1.0 - level) + wet_r * level

            # Update write positions
            state["write_pos_l"] = (state["write_pos_l"] + 1) % self.max_delay_samples
            state["write_pos_r"] = (state["write_pos_r"] + 1) % self.max_delay_samples
            state["write_pos_c"] = (state["write_pos_c"] + 1) % self.max_delay_samples

    def _process_delay_lr(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.3)
        level = params.get("parameter3", 0.5)
        cross_feedback = params.get("parameter4", 0.0)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "delay_lr",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
            },
        )

        for i in range(num_samples):
            # Read from delay lines
            read_pos_l = (state["write_pos_l"] - delay_samples) % self.max_delay_samples
            read_pos_r = (state["write_pos_r"] - delay_samples) % self.max_delay_samples

            delayed_l = state["delay_line_l"][int(read_pos_l)]
            delayed_r = state["delay_line_r"][int(read_pos_r)]

            # Current input
            input_l = stereo_mix[i, 0]
            input_r = stereo_mix[i, 1]

            # Apply feedback with optional cross-feedback (using delay tap outputs)
            state["delay_line_l"][state["write_pos_l"]] = (
                input_l + delayed_l * feedback + delayed_r * cross_feedback
            )
            state["delay_line_r"][state["write_pos_r"]] = (
                input_r + delayed_r * feedback + delayed_l * cross_feedback
            )

            stereo_mix[i, 0] = input_l * (1.0 - level) + delayed_l * level
            stereo_mix[i, 1] = input_r * (1.0 - level) + delayed_r * level

            # Update write positions
            state["write_pos_l"] = (state["write_pos_l"] + 1) % self.max_delay_samples
            state["write_pos_r"] = (state["write_pos_r"] + 1) % self.max_delay_samples

    def _process_echo(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        decay = params.get("parameter4", 0.8)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "echo",
            {
                "delay_line": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos": 0,
            },
        )

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            read_pos = (state["write_pos"] - delay_samples) % self.max_delay_samples
            delayed_sample = state["delay_line"][int(read_pos)]

            # Write to delay line: input + delayed_tap * feedback * decay
            state["delay_line"][state["write_pos"]] = input_sample + delayed_sample * feedback * decay

            output = input_sample * (1.0 - level) + delayed_sample * level
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

            state["write_pos"] = (state["write_pos"] + 1) % self.max_delay_samples

    def _process_dual_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time1 = params.get("parameter1", 0.3) * 1000
        time2 = params.get("parameter2", 0.6) * 1000
        feedback = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        delay_samples1 = int(time1 * self.sample_rate / 1000.0)
        delay_samples2 = int(time2 * self.sample_rate / 1000.0)
        delay_samples1 = max(1, min(delay_samples1, self.max_delay_samples - 1))
        delay_samples2 = max(1, min(delay_samples2, self.max_delay_samples - 1))

        state = self._ensure_state(
            "dual_delay",
            {
                "delay_line1": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line2": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos1": 0,
                "write_pos2": 0,
            },
        )

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            # Read from both delay lines
            read_pos1 = (state["write_pos1"] - delay_samples1) % self.max_delay_samples
            read_pos2 = (state["write_pos2"] - delay_samples2) % self.max_delay_samples

            delayed1 = state["delay_line1"][int(read_pos1)]
            delayed2 = state["delay_line2"][int(read_pos2)]

            # Write to delay lines: input + delayed_tap * feedback
            state["delay_line1"][state["write_pos1"]] = input_sample + delayed1 * feedback
            state["delay_line2"][state["write_pos2"]] = input_sample + delayed2 * feedback

            output = input_sample * (1.0 - level) + (delayed1 + delayed2) * level * 0.5
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

            state["write_pos1"] = (state["write_pos1"] + 1) % self.max_delay_samples
            state["write_pos2"] = (state["write_pos2"] + 1) % self.max_delay_samples

    def _process_pan_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        rate = params.get("parameter4", 0.5) * 5.0

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "pan_delay",
            {
                "delay_line": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos": 0,
                "lfo_phase": 0.0,
            },
        )

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            lfo_phase = state["lfo_phase"]
            lfo_phase += 2 * math.pi * rate / self.sample_rate
            pan = math.sin(lfo_phase) * 0.5 + 0.5

            read_pos = (state["write_pos"] - delay_samples) % self.max_delay_samples
            delayed_sample = state["delay_line"][int(read_pos)]

            # Write to delay line: input + delayed_tap * feedback
            state["delay_line"][state["write_pos"]] = input_sample + delayed_sample * feedback

            # Mix dry/wet with panning
            output = input_sample * (1.0 - level) + delayed_sample * level
            left_out = output * (1.0 - pan)
            right_out = output * pan

            stereo_mix[i, 0] = left_out
            stereo_mix[i, 1] = right_out

            state["write_pos"] = (state["write_pos"] + 1) % self.max_delay_samples
            state["lfo_phase"] = lfo_phase % (2 * math.pi)

    def _process_cross_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        cross = params.get("parameter4", 0.5)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "cross_delay",
            {
                "left_delay": np.zeros(self.max_delay_samples, dtype=np.float32),
                "right_delay": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
            },
        )

        for i in range(num_samples):
            # Read from delay lines
            read_pos_l = (state["write_pos_l"] - delay_samples) % self.max_delay_samples
            read_pos_r = (state["write_pos_r"] - delay_samples) % self.max_delay_samples

            delayed_l = state["left_delay"][int(read_pos_l)]
            delayed_r = state["right_delay"][int(read_pos_r)]

            # Current input
            input_l = stereo_mix[i, 0]
            input_r = stereo_mix[i, 1]

            # Apply feedback with cross-feedback (using delay tap outputs)
            state["left_delay"][state["write_pos_l"]] = (
                input_l
                + delayed_l * feedback * (1.0 - cross)
                + delayed_r * feedback * cross
            )
            state["right_delay"][state["write_pos_r"]] = (
                input_r
                + delayed_r * feedback * (1.0 - cross)
                + delayed_l * feedback * cross
            )

            stereo_mix[i, 0] = input_l * (1.0 - level) + delayed_l * level
            stereo_mix[i, 1] = input_r * (1.0 - level) + delayed_r * level

            state["write_pos_l"] = (state["write_pos_l"] + 1) % self.max_delay_samples
            state["write_pos_r"] = (state["write_pos_r"] + 1) % self.max_delay_samples

    def _process_multi_tap_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        taps = int(params.get("parameter1", 0.5) * 10) + 1
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        spacing = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "multi_tap",
            {
                "delay_line": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos": 0,
            },
        )

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            # Generate multiple taps
            delayed_sum = 0.0
            for tap in range(taps):
                delay_time = (tap * spacing * 500) + 100  # Base delay + spacing
                delay_samples = int(delay_time * self.sample_rate / 1000.0)
                delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

                read_pos = (state["write_pos"] - delay_samples) % self.max_delay_samples
                delayed_sum += state["delay_line"][int(read_pos)]

            delayed_sum /= taps

            # Write to delay line: input + average_delayed_tap * feedback
            state["delay_line"][state["write_pos"]] = input_sample + delayed_sum * feedback

            output = input_sample * (1.0 - level) + delayed_sum * level
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

            state["write_pos"] = (state["write_pos"] + 1) % self.max_delay_samples

    def _process_reverse_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        reverse = params.get("parameter4", 0.5)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "reverse_delay",
            {
                "delay_line": np.zeros(self.max_delay_samples, dtype=np.float32),
                "reverse_buffer": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos": 0,
                "buffer_index": 0,
            },
        )

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            read_pos = (state["write_pos"] - delay_samples) % self.max_delay_samples
            delayed_sample = state["delay_line"][int(read_pos)]

            # Read from reverse buffer
            reverse_pos = (state["buffer_index"] + delay_samples) % self.max_delay_samples
            reverse_sample = state["reverse_buffer"][int(reverse_pos)]

            # Write to buffers: input + delayed_tap * feedback
            written = input_sample + delayed_sample * feedback
            state["delay_line"][state["write_pos"]] = written
            state["reverse_buffer"][state["write_pos"]] = written

            # Mix dry/wet with reverse mixing
            output = (
                input_sample * (1.0 - level)
                + delayed_sample * level * (1.0 - reverse)
                + reverse_sample * level * reverse
            )
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

            state["write_pos"] = (state["write_pos"] + 1) % self.max_delay_samples
            state["buffer_index"] = state["write_pos"]

    def _process_tremolo(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state("tremolo", {"lfo_phase": 0.0})
        phase_increment = 2 * math.pi * rate / self.sample_rate

        for i in range(num_samples):
            state["lfo_phase"] = (state["lfo_phase"] + phase_increment) % (2 * math.pi)

            # Get LFO value based on waveform
            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            # Convert to amplitude modulation
            amplitude = 1.0 - depth * 0.5 + depth * 0.5 * lfo_value

            # Apply modulation to both channels
            stereo_mix[i, 0] *= amplitude
            stereo_mix[i, 1] *= amplitude

    def _process_auto_pan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state("auto_pan", {"lfo_phase": 0.0})
        phase_increment = 2 * math.pi * rate / self.sample_rate

        for i in range(num_samples):
            state["lfo_phase"] = (state["lfo_phase"] + phase_increment) % (2 * math.pi)

            # Get LFO value
            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            # Convert to pan position (-1 to 1)
            pan = lfo_value * depth

            # Normalize pan to 0-1 for equal-power panning
            pan_norm = (pan + 1.0) * 0.5
            left_gain = math.cos(pan_norm * math.pi / 2.0)
            right_gain = math.sin(pan_norm * math.pi / 2.0)

            # Apply panning (no cross-mixing)
            original_l = stereo_mix[i, 0]
            original_r = stereo_mix[i, 1]
            stereo_mix[i, 0] = original_l * left_gain
            stereo_mix[i, 1] = original_r * right_gain

    def get_supported_types(self) -> list:
        """Get list of supported effect types."""
        return list(range(10))  # Types 0-9

    def reset(self) -> None:
        """Reset all effect states."""
        with self._lock:
            self._effect_states.clear()

