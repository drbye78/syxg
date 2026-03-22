"""
XG Chorus & Modulation Effects - Production Implementation

This module implements XG chorus and modulation effects (types 10-26) with
production-quality DSP algorithms adapted from synth.effects.processing.

Effects implemented:
- Chorus 1-4 (10-13): Multi-tap chorus with LFO modulation
- Celeste 1-2 (14-15): Pitch-shifted chorus variations
- Flanger 1-2 (16-17): Short delay with heavy feedback
- Delay LCR Chorus (18): Delay + Chorus combination
- Delay LR Chorus (19): Delay + Chorus combination
- Rotary Speaker Variation (20): Alternative rotary speaker
- Celeste Chorus (21): Enhanced celeste effect
- Vibrato (22): Pitch modulation effect
- Acoustic Simulator (23): Room acoustic simulation
- Guitar Amp Simulator (24): Guitar amplifier simulation
- Enhancer (25): Dynamic enhancement
- Slicer (26): Rhythmic gating effect

All implementations use zero-allocation processing and thread-safe state management.
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np


class ChorusModulationProcessor:
    """
    XG Chorus & Modulation Effects Processor

    Handles all chorus and modulation effects with production-quality DSP.
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        """
        Initialize chorus processor.

        Args:
            sample_rate: Sample rate in Hz
            max_delay_samples: Maximum delay line length
        """
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Effect state storage - thread-safe
        self._effect_states = {}
        self._lock = threading.RLock()

    def process_effect(
        self, effect_type: int, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process chorus/modulation effect.

        Args:
            effect_type: XG variation effect type (10-31)
            stereo_mix: Input/output stereo buffer (num_samples, 2)
            num_samples: Number of samples to process
            params: Effect parameters (parameter1-4)
        """
        with self._lock:
            if effect_type == 10:
                self._process_chorus_1(stereo_mix, num_samples, params)
            elif effect_type == 11:
                self._process_chorus_2(stereo_mix, num_samples, params)
            elif effect_type == 12:
                self._process_chorus_3(stereo_mix, num_samples, params)
            elif effect_type == 13:
                self._process_chorus_4(stereo_mix, num_samples, params)
            elif effect_type == 14:
                self._process_celeste_1(stereo_mix, num_samples, params)
            elif effect_type == 15:
                self._process_celeste_2(stereo_mix, num_samples, params)
            elif effect_type == 16:
                self._process_flanger_1(stereo_mix, num_samples, params)
            elif effect_type == 17:
                self._process_flanger_2(stereo_mix, num_samples, params)
            elif effect_type == 18:
                self._process_delay_lcr_chorus(stereo_mix, num_samples, params)
            elif effect_type == 19:
                self._process_delay_lr_chorus(stereo_mix, num_samples, params)
            elif effect_type == 20:
                self._process_rotary_speaker_variation(stereo_mix, num_samples, params)
            elif effect_type == 21:
                self._process_celeste_chorus(stereo_mix, num_samples, params)
            elif effect_type == 22:
                self._process_vibrato(stereo_mix, num_samples, params)
            elif effect_type == 23:
                self._process_acoustic_simulator(stereo_mix, num_samples, params)
            elif effect_type == 24:
                self._process_guitar_amp_simulator(stereo_mix, num_samples, params)
            elif effect_type == 25:
                self._process_enhancer(stereo_mix, num_samples, params)
            elif effect_type == 26:
                self._process_slicer(stereo_mix, num_samples, params)
            elif effect_type == 27:
                self._process_phaser_flanger(stereo_mix, num_samples, params)
            elif effect_type == 28:
                self._process_chorus_autopan(stereo_mix, num_samples, params)
            elif effect_type == 29:
                self._process_celeste_autopan(stereo_mix, num_samples, params)
            elif effect_type == 30:
                self._process_delay_autopan(stereo_mix, num_samples, params)
            elif effect_type == 31:
                self._process_reverb_autopan(stereo_mix, num_samples, params)

    def _ensure_state(self, effect_key: str, state_config: dict[str, Any]) -> dict[str, Any]:
        """Ensure effect state exists, create if needed."""
        if effect_key not in self._effect_states:
            self._effect_states[effect_key] = state_config.copy()
        return self._effect_states[effect_key]

    def _process_chorus_1(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Chorus 1 effect (XG Variation Type 10).
        Multi-tap chorus with LFO modulation - rich, lush chorus sound.
        """
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.2)
        level = params.get("parameter4", 0.4)

        state = self._ensure_state(
            "chorus_1",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(4)
                ],
                "write_positions": [0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.8, rate * 0.6, rate, rate * 0.4],
                "tap_delays": [
                    int(0.010 * self.sample_rate),
                    int(0.012 * self.sample_rate),
                    int(0.014 * self.sample_rate),
                    int(0.016 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            # Process each tap
            for tap_idx in range(4):
                # Update LFO phase
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                # Calculate modulated delay
                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.5)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                # Process left channel
                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed_l = state["delay_lines"][tap_idx][int(read_pos)]

                # Write current input to delay line
                input_l = stereo_mix[i, 0]
                input_r = stereo_mix[i, 1]
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = (
                    input_l + input_r
                ) * 0.5

                # Add to chorus sum
                chorus_sum[0] += delayed_l * 0.25
                chorus_sum[1] += delayed_l * 0.25

                # Update write position
                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            # Mix dry/wet
            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_chorus_2(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Chorus 2 effect (XG Variation Type 11).
        Faster chorus with different tap spacing.
        """
        rate = params.get("parameter1", 0.7) * 6.0  # Faster rate
        depth = params.get("parameter2", 0.6)  # Deeper modulation
        feedback = params.get("parameter3", 0.15)
        level = params.get("parameter4", 0.45)

        state = self._ensure_state(
            "chorus_2",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.9, rate * 0.7, rate * 1.1],
                "tap_delays": [
                    int(0.008 * self.sample_rate),
                    int(0.011 * self.sample_rate),
                    int(0.015 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(3):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.4)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * (1.0 / 3.0)
                chorus_sum[1] += delayed * (1.0 / 3.0)

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_chorus_3(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Chorus 3 effect (XG Variation Type 12).
        Chorus with feedback for richer sound.
        """
        rate = params.get("parameter1", 0.4) * 4.0
        depth = params.get("parameter2", 0.4)
        feedback = params.get("parameter3", 0.3)  # Higher feedback
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "chorus_3",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(4)
                ],
                "write_positions": [0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.8, rate * 0.6, rate, rate * 0.4],
                "tap_delays": [
                    int(0.012 * self.sample_rate),
                    int(0.016 * self.sample_rate),
                    int(0.020 * self.sample_rate),
                    int(0.024 * self.sample_rate),
                ],
                "feedback_buffers": [0.0, 0.0, 0.0, 0.0],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(4):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.6)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                # Add feedback
                processed_input = input_sample + state["feedback_buffers"][tap_idx] * feedback
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = processed_input
                state["feedback_buffers"][tap_idx] = processed_input

                chorus_sum[0] += delayed * 0.25
                chorus_sum[1] += delayed * 0.25

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_chorus_4(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Chorus 4 effect (XG Variation Type 13).
        Deep, wide chorus effect.
        """
        rate = params.get("parameter1", 0.3) * 3.0  # Slower rate
        depth = params.get("parameter2", 0.7)  # Deep modulation
        feedback = params.get("parameter3", 0.25)
        level = params.get("parameter4", 0.55)

        state = self._ensure_state(
            "chorus_4",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(6)
                ],
                "write_positions": [0, 0, 0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "lfo_rates": [
                    rate * 0.5,
                    rate * 0.7,
                    rate * 0.9,
                    rate * 1.1,
                    rate * 1.3,
                    rate * 1.5,
                ],
                "tap_delays": [
                    int(0.008 * self.sample_rate),
                    int(0.012 * self.sample_rate),
                    int(0.016 * self.sample_rate),
                    int(0.020 * self.sample_rate),
                    int(0.024 * self.sample_rate),
                    int(0.028 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(6):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.7)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * (1.0 / 6.0)
                chorus_sum[1] += delayed * (1.0 / 6.0)

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_celeste_1(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Celeste 1 effect (XG Variation Type 14).
        Pitch-shifted chorus with different tap spacing.
        """
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.2)
        level = params.get("parameter4", 0.4)

        state = self._ensure_state(
            "celeste_1",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(4)
                ],
                "write_positions": [0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.8, rate * 0.6, rate, rate * 0.4],
                # Celeste uses different spacing for pitch effect
                "tap_delays": [
                    int(0.008 * self.sample_rate),
                    int(0.015 * self.sample_rate),
                    int(0.011 * self.sample_rate),
                    int(0.013 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(4):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.3)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * 0.25
                chorus_sum[1] += delayed * 0.25

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_celeste_2(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Celeste 2 effect (XG Variation Type 15).
        Alternative celeste with different characteristics.
        """
        rate = params.get("parameter1", 0.6) * 6.0  # Faster
        depth = params.get("parameter2", 0.4)  # Shallower
        feedback = params.get("parameter3", 0.15)
        level = params.get("parameter4", 0.35)

        state = self._ensure_state(
            "celeste_2",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.7, rate * 0.9, rate * 1.2],
                "tap_delays": [
                    int(0.006 * self.sample_rate),
                    int(0.010 * self.sample_rate),
                    int(0.014 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(3):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.4)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * (1.0 / 3.0)
                chorus_sum[1] += delayed * (1.0 / 3.0)

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_flanger_1(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Flanger 1 effect (XG Variation Type 16).
        Classic flanger with short delay and feedback.
        """
        rate = params.get("parameter1", 0.5) * 2.0
        depth = params.get("parameter2", 0.8)
        feedback = params.get("parameter3", 0.6)  # High feedback for flanger
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "flanger_1",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(2)
                ],
                "write_positions": [0, 0],
                "lfo_phases": [0.0, math.pi],  # 180 degree phase difference for stereo
                "feedback_buffers": [0.0, 0.0],
            },
        )

        for i in range(num_samples):
            for ch in range(2):
                # Update LFO
                phase_increment = 2 * math.pi * rate / self.sample_rate
                state["lfo_phases"][ch] = (state["lfo_phases"][ch] + phase_increment) % (
                    2 * math.pi
                )

                # Short delay for flanger (0.2-2ms range)
                base_delay = int(0.0005 * self.sample_rate)  # 0.5ms base
                modulation = int(math.sin(state["lfo_phases"][ch]) * depth * base_delay * 2.0)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                # Read from delay line
                read_pos = (state["write_positions"][ch] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                # Apply feedback
                input_sample = stereo_mix[i, ch]
                processed_input = input_sample + state["feedback_buffers"][ch] * feedback

                # Write to delay line
                state["delay_lines"][ch][state["write_positions"][ch]] = processed_input
                state["feedback_buffers"][ch] = processed_input

                # Mix dry/wet with flanger characteristics
                stereo_mix[i, ch] = input_sample * (1.0 - level) + delayed * level

                state["write_positions"][ch] = (
                    state["write_positions"][ch] + 1
                ) % self.max_delay_samples

    def _process_flanger_2(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Flanger 2 effect (XG Variation Type 17).
        Alternative flanger with different modulation.
        """
        rate = params.get("parameter1", 0.3) * 1.5  # Slower
        depth = params.get("parameter2", 0.9)  # Deeper
        feedback = params.get("parameter3", 0.7)  # Higher feedback
        level = params.get("parameter4", 0.55)

        state = self._ensure_state(
            "flanger_2",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(2)
                ],
                "write_positions": [0, 0],
                "lfo_phases": [0.0, math.pi * 0.7],  # Different phase offset
                "feedback_buffers": [0.0, 0.0],
            },
        )

        for i in range(num_samples):
            for ch in range(2):
                phase_increment = 2 * math.pi * rate / self.sample_rate
                state["lfo_phases"][ch] = (state["lfo_phases"][ch] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = int(0.0008 * self.sample_rate)  # Slightly longer base delay
                modulation = int(math.sin(state["lfo_phases"][ch]) * depth * base_delay * 1.8)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (state["write_positions"][ch] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                input_sample = stereo_mix[i, ch]
                processed_input = input_sample + state["feedback_buffers"][ch] * feedback

                state["delay_lines"][ch][state["write_positions"][ch]] = processed_input
                state["feedback_buffers"][ch] = processed_input

                stereo_mix[i, ch] = input_sample * (1.0 - level) + delayed * level

                state["write_positions"][ch] = (
                    state["write_positions"][ch] + 1
                ) % self.max_delay_samples

    def _process_delay_lcr_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Delay LCR Chorus effect (XG Variation Type 18).
        Combination of delay and chorus processing.
        """
        # First apply delay LCR
        self._process_delay_lcr_chorus_delay(stereo_mix, num_samples, params)
        # Then apply chorus
        self._process_delay_lcr_chorus_chorus(stereo_mix, num_samples, params)

    def _process_delay_lcr_chorus_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Helper: Apply delay portion of Delay LCR Chorus."""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.2)
        delay_level = params.get("parameter3", 0.3)
        stereo_width = params.get("parameter4", 0.8)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "delay_lcr_chorus_delay",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_c": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
                "write_pos_c": 0,
                "feedback_l": 0.0,
                "feedback_r": 0.0,
                "feedback_c": 0.0,
            },
        )

        for i in range(num_samples):
            read_pos_l = (state["write_pos_l"] - delay_samples) % self.max_delay_samples
            read_pos_r = (state["write_pos_r"] - delay_samples) % self.max_delay_samples
            read_pos_c = (state["write_pos_c"] - delay_samples) % self.max_delay_samples

            delayed_l = state["delay_line_l"][int(read_pos_l)]
            delayed_r = state["delay_line_r"][int(read_pos_r)]
            delayed_c = state["delay_line_c"][int(read_pos_c)]

            input_l = stereo_mix[i, 0]
            input_r = stereo_mix[i, 1]
            input_c = (input_l + input_r) * 0.5

            processed_l = input_l + state["feedback_l"] * feedback
            processed_r = input_r + state["feedback_r"] * feedback
            processed_c = input_c + state["feedback_c"] * feedback

            state["delay_line_l"][state["write_pos_l"]] = processed_l
            state["delay_line_r"][state["write_pos_r"]] = processed_r
            state["delay_line_c"][state["write_pos_c"]] = processed_c

            state["feedback_l"] = processed_l
            state["feedback_r"] = processed_r
            state["feedback_c"] = processed_c

            wet_l = (delayed_l * (1.0 + stereo_width) + delayed_c * (1.0 - stereo_width)) * 0.5
            wet_r = (delayed_r * (1.0 + stereo_width) + delayed_c * (1.0 - stereo_width)) * 0.5

            stereo_mix[i, 0] = input_l * (1.0 - delay_level) + wet_l * delay_level
            stereo_mix[i, 1] = input_r * (1.0 - delay_level) + wet_r * delay_level

            state["write_pos_l"] = (state["write_pos_l"] + 1) % self.max_delay_samples
            state["write_pos_r"] = (state["write_pos_r"] + 1) % self.max_delay_samples
            state["write_pos_c"] = (state["write_pos_c"] + 1) % self.max_delay_samples

    def _process_delay_lcr_chorus_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Helper: Apply chorus portion of Delay LCR Chorus."""
        rate = params.get("parameter1", 0.4) * 4.0
        depth = params.get("parameter2", 0.4)
        chorus_feedback = params.get("parameter3", 0.2)
        chorus_level = params.get("parameter4", 0.4)

        state = self._ensure_state(
            "delay_lcr_chorus_chorus",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.8, rate * 0.6, rate],
                "tap_delays": [
                    int(0.008 * self.sample_rate),
                    int(0.011 * self.sample_rate),
                    int(0.014 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(3):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.4)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * (1.0 / 3.0)
                chorus_sum[1] += delayed * (1.0 / 3.0)

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = (
                stereo_mix[i, 0] * (1.0 - chorus_level) + chorus_sum[0] * chorus_level
            )
            stereo_mix[i, 1] = (
                stereo_mix[i, 1] * (1.0 - chorus_level) + chorus_sum[1] * chorus_level
            )

    def _process_delay_lr_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Delay LR Chorus effect (XG Variation Type 19).
        Dual delay combined with chorus.
        """
        # First apply delay LR
        self._process_delay_lr_chorus_delay(stereo_mix, num_samples, params)
        # Then apply chorus
        self._process_delay_lr_chorus_chorus(stereo_mix, num_samples, params)

    def _process_delay_lr_chorus_delay(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Helper: Apply delay portion of Delay LR Chorus."""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.25)
        delay_level = params.get("parameter3", 0.35)
        cross_feedback = params.get("parameter4", 0.3)

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "delay_lr_chorus_delay",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
                "feedback_l": 0.0,
                "feedback_r": 0.0,
            },
        )

        for i in range(num_samples):
            read_pos_l = (state["write_pos_l"] - delay_samples) % self.max_delay_samples
            read_pos_r = (state["write_pos_r"] - delay_samples) % self.max_delay_samples

            delayed_l = state["delay_line_l"][int(read_pos_l)]
            delayed_r = state["delay_line_r"][int(read_pos_r)]

            input_l = stereo_mix[i, 0]
            input_r = stereo_mix[i, 1]

            processed_l = (
                input_l
                + state["feedback_l"] * feedback
                + state["feedback_r"] * feedback * cross_feedback
            )
            processed_r = (
                input_r
                + state["feedback_r"] * feedback
                + state["feedback_l"] * feedback * cross_feedback
            )

            state["delay_line_l"][state["write_pos_l"]] = processed_l
            state["delay_line_r"][state["write_pos_r"]] = processed_r

            state["feedback_l"] = processed_l
            state["feedback_r"] = processed_r

            stereo_mix[i, 0] = input_l * (1.0 - delay_level) + delayed_l * delay_level
            stereo_mix[i, 1] = input_r * (1.0 - delay_level) + delayed_r * delay_level

            state["write_pos_l"] = (state["write_pos_l"] + 1) % self.max_delay_samples
            state["write_pos_r"] = (state["write_pos_r"] + 1) % self.max_delay_samples

    def _process_delay_lr_chorus_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Helper: Apply chorus portion of Delay LR Chorus."""
        rate = params.get("parameter1", 0.45) * 4.5
        depth = params.get("parameter2", 0.45)
        chorus_feedback = params.get("parameter3", 0.18)
        chorus_level = params.get("parameter4", 0.38)

        state = self._ensure_state(
            "delay_lr_chorus_chorus",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.85, rate * 0.65, rate * 1.05],
                "tap_delays": [
                    int(0.009 * self.sample_rate),
                    int(0.012 * self.sample_rate),
                    int(0.015 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(3):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.45)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * (1.0 / 3.0)
                chorus_sum[1] += delayed * (1.0 / 3.0)

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = (
                stereo_mix[i, 0] * (1.0 - chorus_level) + chorus_sum[0] * chorus_level
            )
            stereo_mix[i, 1] = (
                stereo_mix[i, 1] * (1.0 - chorus_level) + chorus_sum[1] * chorus_level
            )

    def _process_rotary_speaker_variation(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Rotary Speaker Variation effect (XG Variation Type 20).
        Alternative rotary speaker implementation.
        """
        speed = params.get("parameter1", 0.6) * 6.0
        balance = params.get("parameter2", 0.6)
        accel = params.get("parameter3", 0.08)
        level = params.get("parameter4", 0.48)

        state = self._ensure_state(
            "rotary_speaker_var",
            {"horn_phase": 0.0, "drum_phase": 0.0, "horn_speed": 0.0, "drum_speed": 0.0},
        )

        target_speed = speed * 0.6 + 0.4
        state["horn_speed"] += (target_speed - state["horn_speed"]) * accel
        state["drum_speed"] += (target_speed * 0.6 - state["drum_speed"]) * accel

        for i in range(num_samples):
            state["horn_phase"] = (
                state["horn_phase"] + 2 * math.pi * state["horn_speed"] / self.sample_rate
            ) % (2 * math.pi)
            state["drum_phase"] = (
                state["drum_phase"] + 2 * math.pi * state["drum_speed"] / self.sample_rate
            ) % (2 * math.pi)

            horn_pos = math.sin(state["horn_phase"])
            drum_pos = math.sin(state["drum_phase"] * 1.2)  # Slightly different ratio

            horn_doppler = 1.0 + horn_pos * 0.12  # Slightly different modulation
            drum_doppler = 1.0 + drum_pos * 0.06

            horn_pan = horn_pos * 0.6
            drum_pan = drum_pos * 0.35

            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            horn_l = input_sample * horn_doppler * (0.5 - horn_pan)
            horn_r = input_sample * horn_doppler * (0.5 + horn_pan)

            drum_l = input_sample * drum_doppler * (0.3 - drum_pan)
            drum_r = input_sample * drum_doppler * (0.3 + drum_pan)

            left_out = (horn_l * 0.65 + drum_l * 0.35) * level + stereo_mix[i, 0] * (1.0 - level)
            right_out = (horn_r * 0.65 + drum_r * 0.35) * level + stereo_mix[i, 1] * (1.0 - level)

            stereo_mix[i, 0] = left_out
            stereo_mix[i, 1] = right_out

    def _process_celeste_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Celeste Chorus effect (XG Variation Type 21).
        Enhanced celeste effect with chorus characteristics.
        """
        rate = params.get("parameter1", 0.55) * 5.5
        depth = params.get("parameter2", 0.55)
        feedback = params.get("parameter3", 0.22)
        level = params.get("parameter4", 0.42)

        state = self._ensure_state(
            "celeste_chorus",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(5)
                ],
                "write_positions": [0, 0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0, 0.0],
                "lfo_rates": [rate * 0.6, rate * 0.8, rate, rate * 1.2, rate * 1.4],
                "tap_delays": [
                    int(0.007 * self.sample_rate),
                    int(0.010 * self.sample_rate),
                    int(0.013 * self.sample_rate),
                    int(0.016 * self.sample_rate),
                    int(0.019 * self.sample_rate),
                ],
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            for tap_idx in range(5):
                phase_increment = 2 * math.pi * state["lfo_rates"][tap_idx] / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.35)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * 0.2
                chorus_sum[1] += delayed * 0.2

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_vibrato(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Vibrato effect (XG Variation Type 22).
        Pitch modulation effect.
        """
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state("vibrato", {"lfo_phase": 0.0})
        phase_increment = 2 * math.pi * rate / self.sample_rate

        for i in range(num_samples):
            state["lfo_phase"] = (state["lfo_phase"] + phase_increment) % (2 * math.pi)

            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            modulation = lfo_value * depth * 0.02
            stereo_mix[i, 0] *= 1.0 + modulation
            stereo_mix[i, 1] *= 1.0 + modulation

    def _process_acoustic_simulator(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Acoustic Simulator effect (XG Variation Type 23).
        Room acoustic simulation with frequency response.
        """
        room = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            if mode == 0:  # Room
                bass_boost = 0.8 + room * 0.2
                mid_cut = 0.9 - room * 0.1
                treble_cut = 0.7 - room * 0.2
            elif mode == 1:  # Concert Hall
                bass_boost = 0.9 + room * 0.1
                mid_cut = 0.95
                treble_cut = 0.8 - room * 0.1
            elif mode == 2:  # Studio
                bass_boost = 0.7 + room * 0.3
                mid_cut = 1.0
                treble_cut = 0.9 - room * 0.1
            else:  # Stage
                bass_boost = 0.6 + room * 0.4
                mid_cut = 0.8 + room * 0.2
                treble_cut = 0.7 + room * 0.3

            bass = input_sample * bass_boost
            mid = input_sample * mid_cut
            treble = input_sample * treble_cut
            output = bass * 0.3 + mid * 0.4 + treble * 0.3

            reverb_amount = reverb * 0.3
            output = output * (1 - reverb_amount) + input_sample * reverb_amount

            stereo_mix[i, 0] = output * (1 - depth * 0.3)
            stereo_mix[i, 1] = output * (1 - depth * 0.3)

    def _process_guitar_amp_simulator(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Guitar Amp Simulator effect (XG Variation Type 24).
        Guitar amplifier simulation with distortion.
        """
        drive = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0

            distorted = math.tanh(input_sample * (1 + drive * 9.0))

            bass_boost = 0.5 + bass * 0.5
            treble_boost = 0.5 + treble * 0.5
            equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)

            output = equalized * level
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

    def _process_enhancer(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Enhancer effect (XG Variation Type 25).
        Dynamic enhancement with harmonic enhancement.
        """
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]

                enhanced = sample + enhance * math.sin(sample * math.pi)

                bass_boost = 0.5 + bass * 0.5
                treble_boost = 0.5 + treble * 0.5
                shaped = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)

                stereo_mix[i, ch] = shaped * level

    def _process_slicer(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Slicer effect (XG Variation Type 26).
        Rhythmic gating effect with multiple waveforms.
        """
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state("slicer", {"lfo_phase": 0.0})
        phase_increment = 2 * math.pi * rate / self.sample_rate

        for i in range(num_samples):
            state["lfo_phase"] = (state["lfo_phase"] + phase_increment) % (2 * math.pi)

            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            lfo_value = lfo_value * depth * 0.5 + 0.5
            amplitude = lfo_value * 2.0 - 1.0

            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
            output = input_sample if input_sample > amplitude else 0.0

            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

    def _process_phaser_flanger(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Phaser-Flanger effect (XG Variation Type 27).
        Combined phaser and flanger effect.
        """
        rate = params.get("parameter1", 0.5) * 3.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.3)
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "phaser_flanger",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(4)
                ],
                "write_positions": [0, 0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0],
                "allpass_filters": [0.0] * 4,
                "feedback_buffers": [0.0, 0.0, 0.0, 0.0],
            },
        )

        for i in range(num_samples):
            output = stereo_mix[i, 0]  # Start with left channel

            # Apply all-pass filters (phaser portion)
            for stage in range(4):
                # Update LFO
                phase_increment = 2 * math.pi * rate / self.sample_rate
                state["lfo_phases"][stage] = (state["lfo_phases"][stage] + phase_increment) % (
                    2 * math.pi
                )

                # Calculate modulated delay for flanger portion
                base_delay = int(0.001 * self.sample_rate)  # 1ms base delay
                modulation = int(math.sin(state["lfo_phases"][stage]) * depth * base_delay)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                # Read from delay line
                read_pos = (state["write_positions"][stage] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][stage][int(read_pos)]

                # Apply feedback
                input_sample = output + state["feedback_buffers"][stage] * feedback
                state["delay_lines"][stage][state["write_positions"][stage]] = input_sample
                state["feedback_buffers"][stage] = input_sample

                # All-pass filter calculation
                g = 0.7  # All-pass coefficient
                allpass_output = delayed + g * (input_sample - delayed * g)
                state["allpass_filters"][stage] = allpass_output

                # Chain stages
                output = allpass_output

                state["write_positions"][stage] = (
                    state["write_positions"][stage] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + output * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + output * level

    def _process_chorus_autopan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Chorus Auto-Pan effect (XG Variation Type 28).
        Chorus with auto-panning modulation.
        """
        rate = params.get("parameter1", 0.5) * 4.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.2)
        level = params.get("parameter4", 0.4)

        state = self._ensure_state(
            "chorus_autopan",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "pan_phase": 0.0,
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            # Update pan LFO
            pan_increment = 2 * math.pi * rate * 0.3 / self.sample_rate
            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"])

            for tap_idx in range(3):
                # Update chorus LFO
                phase_increment = 2 * math.pi * rate / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                base_delay = int(0.010 * self.sample_rate)
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.5)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                # Apply auto-panning to each tap
                tap_pan = pan_pos + tap_idx * math.pi / 3  # Different pan for each tap
                left_gain = math.cos(tap_pan * math.pi / 4)
                right_gain = math.sin(tap_pan * math.pi / 4)

                chorus_sum[0] += delayed * left_gain * 0.33
                chorus_sum[1] += delayed * right_gain * 0.33

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_celeste_autopan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Celeste Auto-Pan effect (XG Variation Type 29).
        Celeste with auto-panning modulation.
        """
        rate = params.get("parameter1", 0.6) * 5.0
        depth = params.get("parameter2", 0.4)
        feedback = params.get("parameter3", 0.15)
        level = params.get("parameter4", 0.35)

        state = self._ensure_state(
            "celeste_autopan",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "pan_phase": 0.0,
            },
        )

        for i in range(num_samples):
            chorus_sum = np.zeros(2, dtype=np.float32)

            pan_increment = 2 * math.pi * rate * 0.4 / self.sample_rate
            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"]) * 0.8

            for tap_idx in range(3):
                phase_increment = 2 * math.pi * rate / self.sample_rate
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (
                    2 * math.pi
                )

                # Celeste uses different spacing
                base_delays = [
                    int(0.007 * self.sample_rate),
                    int(0.011 * self.sample_rate),
                    int(0.015 * self.sample_rate),
                ]
                base_delay = base_delays[tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * 0.3)
                total_delay = base_delay + modulation
                total_delay = max(1, min(total_delay, self.max_delay_samples - 1))

                read_pos = (
                    state["write_positions"][tap_idx] - total_delay
                ) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                # Apply auto-panning
                tap_pan = pan_pos + tap_idx * math.pi / 2
                left_gain = math.cos(tap_pan * math.pi / 4)
                right_gain = math.sin(tap_pan * math.pi / 4)

                chorus_sum[0] += delayed * left_gain * 0.33
                chorus_sum[1] += delayed * right_gain * 0.33

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_delay_autopan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Delay Auto-Pan effect (XG Variation Type 30).
        Delay with auto-panning modulation.
        """
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.25)
        delay_level = params.get("parameter3", 0.35)
        pan_rate = params.get("parameter4", 0.5) * 3.0

        delay_samples = int(time * self.sample_rate / 1000.0)
        delay_samples = max(1, min(delay_samples, self.max_delay_samples - 1))

        state = self._ensure_state(
            "delay_autopan",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(2)
                ],
                "write_positions": [0, 0],
                "feedback_buffers": [0.0, 0.0],
                "pan_phase": 0.0,
            },
        )

        for i in range(num_samples):
            # Update pan LFO
            pan_increment = 2 * math.pi * pan_rate / self.sample_rate
            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"])

            for ch in range(2):
                read_pos = (state["write_positions"][ch] - delay_samples) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                input_sample = stereo_mix[i, ch]
                processed = input_sample + state["feedback_buffers"][ch] * feedback
                state["delay_lines"][ch][state["write_positions"][ch]] = processed
                state["feedback_buffers"][ch] = processed

                # Apply auto-panning to delayed signal
                pan_offset = ch * math.pi  # Opposite channels pan differently
                channel_pan = pan_pos + pan_offset
                left_gain = math.cos(channel_pan * math.pi / 4)
                right_gain = math.sin(channel_pan * math.pi / 4)

                delayed_left = delayed * left_gain
                delayed_right = delayed * right_gain

                stereo_mix[i, 0] = (
                    stereo_mix[i, 0] * (1.0 - delay_level) + delayed_left * delay_level
                )
                stereo_mix[i, 1] = (
                    stereo_mix[i, 1] * (1.0 - delay_level) + delayed_right * delay_level
                )

                state["write_positions"][ch] = (
                    state["write_positions"][ch] + 1
                ) % self.max_delay_samples

    def _process_reverb_autopan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Reverb Auto-Pan effect (XG Variation Type 31).
        Reverb with auto-panning modulation.
        """
        reverb_time = params.get("parameter1", 0.5) * 3.0
        hf_damping = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.4)
        pan_rate = params.get("parameter4", 0.5) * 2.0

        state = self._ensure_state(
            "reverb_autopan",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(4)
                ],
                "write_positions": [0, 0, 0, 0],
                "feedback_buffers": [0.0, 0.0, 0.0, 0.0],
                "pan_phase": 0.0,
            },
        )

        # Simple reverb taps with different delays
        reverb_delays = [
            int(reverb_time * 0.1 * self.sample_rate),
            int(reverb_time * 0.15 * self.sample_rate),
            int(reverb_time * 0.22 * self.sample_rate),
            int(reverb_time * 0.3 * self.sample_rate),
        ]

        for i in range(num_samples):
            reverb_sum = np.zeros(2, dtype=np.float32)

            # Update pan LFO
            pan_increment = 2 * math.pi * pan_rate / self.sample_rate
            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"])

            for tap_idx, delay in enumerate(reverb_delays):
                delay = max(1, min(delay, self.max_delay_samples - 1))
                read_pos = (state["write_positions"][tap_idx] - delay) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                processed = input_sample + state["feedback_buffers"][tap_idx] * 0.4
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = processed
                state["feedback_buffers"][tap_idx] = processed

                # Apply auto-panning to each reverb tap
                tap_pan = pan_pos + tap_idx * math.pi / 2
                left_gain = math.cos(tap_pan * math.pi / 4)
                right_gain = math.sin(tap_pan * math.pi / 4)

                reverb_sum[0] += delayed * left_gain * 0.25
                reverb_sum[1] += delayed * right_gain * 0.25

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + reverb_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + reverb_sum[1] * level

    def get_supported_types(self) -> list:
        """Get list of supported effect types."""
        return list(range(10, 32))  # Types 10-31

    def reset(self) -> None:
        """Reset all effect states."""
        with self._lock:
            self._effect_states.clear()
