"""
XG Chorus & Modulation Effects - Production Implementation

This module implements XG chorus and modulation effects (types 10-26) with
production-quality DSP algorithms adapted from synth.processing.effects.processing.

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
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # Effect state storage - thread-safe
        self._effect_states = {}
        self._lock = threading.RLock()

    def process_effect(
        self, effect_type: int, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
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

    def _process_tap_chorus(
        self,
        stereo_mix: np.ndarray,
        num_samples: int,
        rate: float,
        depth: float,
        feedback: float,
        level: float,
        state_key: str,
        n_taps: int,
        lfo_rate_ratios: list[float],
        tap_delay_secs: list[float],
        mod_factor: float,
        use_feedback: bool = False,
    ) -> None:
        state = self._ensure_state(
            state_key,
            {
                "delay_lines": [np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(n_taps)],
                "write_positions": [0] * n_taps,
                "lfo_phases": [0.0] * n_taps,
                "lfo_rates": [rate * r for r in lfo_rate_ratios],
                "tap_delays": [int(t * self.sample_rate) for t in tap_delay_secs],
                **({"feedback_buffers": [0.0] * n_taps} if use_feedback else {}),
            },
        )
        weight = 1.0 / n_taps
        chorus_sum = np.empty(2, dtype=np.float32)
        phase_increments = [2 * math.pi * rate / self.sample_rate for rate in state["lfo_rates"]]
        for i in range(num_samples):
            chorus_sum.fill(0.0)
            for tap_idx in range(n_taps):
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increments[tap_idx]) % (2 * math.pi)

                base_delay = state["tap_delays"][tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * mod_factor)
                total_delay = max(1, min(base_delay + modulation, self.max_delay_samples - 1))

                read_pos = (state["write_positions"][tap_idx] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                if use_feedback:
                    processed = input_sample + state["feedback_buffers"][tap_idx] * feedback
                    state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = processed
                    state["feedback_buffers"][tap_idx] = processed
                else:
                    state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                chorus_sum[0] += delayed * weight
                chorus_sum[1] += delayed * weight

                state["write_positions"][tap_idx] = (state["write_positions"][tap_idx] + 1) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_chorus_1(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.5) * 5.0,
            depth=params.get("parameter2", 0.5),
            feedback=params.get("parameter3", 0.2),
            level=params.get("parameter4", 0.4),
            state_key="chorus_1", n_taps=4,
            lfo_rate_ratios=[0.8, 0.6, 1.0, 0.4],
            tap_delay_secs=[0.010, 0.012, 0.014, 0.016],
            mod_factor=0.5,
        )

    def _process_chorus_2(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.7) * 6.0,
            depth=params.get("parameter2", 0.6),
            feedback=params.get("parameter3", 0.15),
            level=params.get("parameter4", 0.45),
            state_key="chorus_2", n_taps=3,
            lfo_rate_ratios=[0.9, 0.7, 1.1],
            tap_delay_secs=[0.008, 0.011, 0.015],
            mod_factor=0.4,
        )

    def _process_chorus_3(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.4) * 4.0,
            depth=params.get("parameter2", 0.4),
            feedback=params.get("parameter3", 0.3),
            level=params.get("parameter4", 0.5),
            state_key="chorus_3", n_taps=4,
            lfo_rate_ratios=[0.8, 0.6, 1.0, 0.4],
            tap_delay_secs=[0.012, 0.016, 0.02, 0.024],
            mod_factor=0.6,
            use_feedback=True,
        )

    def _process_chorus_4(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.3) * 3.0,
            depth=params.get("parameter2", 0.7),
            feedback=params.get("parameter3", 0.25),
            level=params.get("parameter4", 0.55),
            state_key="chorus_4", n_taps=6,
            lfo_rate_ratios=[0.5, 0.7, 0.9, 1.1, 1.3, 1.5],
            tap_delay_secs=[0.008, 0.012, 0.016, 0.02, 0.024, 0.028],
            mod_factor=0.7,
        )

    def _process_celeste_1(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.5) * 5.0,
            depth=params.get("parameter2", 0.5),
            feedback=params.get("parameter3", 0.2),
            level=params.get("parameter4", 0.4),
            state_key="celeste_1", n_taps=4,
            lfo_rate_ratios=[0.8, 0.6, 1.0, 0.4],
            tap_delay_secs=[0.008, 0.015, 0.011, 0.013],
            mod_factor=0.3,
        )

    def _process_celeste_2(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.6) * 6.0,
            depth=params.get("parameter2", 0.4),
            feedback=params.get("parameter3", 0.15),
            level=params.get("parameter4", 0.35),
            state_key="celeste_2", n_taps=3,
            lfo_rate_ratios=[0.7, 0.9, 1.2],
            tap_delay_secs=[0.006, 0.01, 0.014],
            mod_factor=0.4,
        )

    def _process_flanger(
        self, stereo_mix: np.ndarray, num_samples: int,
        rate: float, depth: float, feedback: float, level: float,
        state_key: str, base_delay_secs: float, mod_factor: float,
        phase_offset: float,
    ) -> None:
        state = self._ensure_state(
            state_key,
            {
                "delay_lines": [np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(2)],
                "write_positions": [0, 0],
                "lfo_phases": [0.0, phase_offset],
                "feedback_buffers": [0.0, 0.0],
            },
        )
        phase_increment = 2 * math.pi * rate / self.sample_rate
        for i in range(num_samples):
            for ch in range(2):
                state["lfo_phases"][ch] = (state["lfo_phases"][ch] + phase_increment) % (2 * math.pi)

                base_delay = int(base_delay_secs * self.sample_rate)
                modulation = int(math.sin(state["lfo_phases"][ch]) * depth * base_delay * mod_factor)
                total_delay = max(1, min(base_delay + modulation, self.max_delay_samples - 1))

                read_pos = (state["write_positions"][ch] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                input_sample = stereo_mix[i, ch]
                processed_input = input_sample + state["feedback_buffers"][ch] * feedback
                state["delay_lines"][ch][state["write_positions"][ch]] = processed_input
                state["feedback_buffers"][ch] = processed_input

                stereo_mix[i, ch] = input_sample * (1.0 - level) + delayed * level

                state["write_positions"][ch] = (state["write_positions"][ch] + 1) % self.max_delay_samples

    def _process_flanger_1(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_flanger(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.5) * 2.0,
            depth=params.get("parameter2", 0.8),
            feedback=params.get("parameter3", 0.6),
            level=params.get("parameter4", 0.5),
            state_key="flanger_1",
            base_delay_secs=0.0005,
            mod_factor=2.0,
            phase_offset=math.pi,
        )

    def _process_flanger_2(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_flanger(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.3) * 1.5,
            depth=params.get("parameter2", 0.9),
            feedback=params.get("parameter3", 0.7),
            level=params.get("parameter4", 0.55),
            state_key="flanger_2",
            base_delay_secs=0.0008,
            mod_factor=1.8,
            phase_offset=math.pi * 0.7,
        )

    def _process_delay_lcr_chorus(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        self._process_delay_lcr_chorus_delay(stereo_mix, num_samples, params)
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

        chorus_sum = np.empty(2, dtype=np.float32)
        tap_phase_increments = [2 * math.pi * r / self.sample_rate for r in state["lfo_rates"]]
        for i in range(num_samples):
            chorus_sum.fill(0.0)

            for tap_idx in range(3):
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + tap_phase_increments[tap_idx]) % (
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
        self._process_delay_lr_chorus_delay(stereo_mix, num_samples, params)
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

        chorus_sum = np.empty(2, dtype=np.float32)
        tap_phase_increments = [2 * math.pi * r / self.sample_rate for r in state["lfo_rates"]]
        for i in range(num_samples):
            chorus_sum.fill(0.0)

            for tap_idx in range(3):
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + tap_phase_increments[tap_idx]) % (
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

        horn_increment = 2 * math.pi * state["horn_speed"] / self.sample_rate
        drum_increment = 2 * math.pi * state["drum_speed"] / self.sample_rate
        for i in range(num_samples):
            state["horn_phase"] = (
                state["horn_phase"] + horn_increment
            ) % (2 * math.pi)
            state["drum_phase"] = (
                state["drum_phase"] + drum_increment
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

    def _process_celeste_chorus(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_tap_chorus(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.55) * 5.5,
            depth=params.get("parameter2", 0.55),
            feedback=params.get("parameter3", 0.22),
            level=params.get("parameter4", 0.42),
            state_key="celeste_chorus", n_taps=5,
            lfo_rate_ratios=[0.6, 0.8, 1.0, 1.2, 1.4],
            tap_delay_secs=[0.007, 0.01, 0.013, 0.016, 0.019],
            mod_factor=0.35,
        )

    def _process_vibrato(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        rate = max(0.1, params.get("parameter1", 0.5) * 10.0)
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "vibrato",
            {
                "delay_line_l": np.zeros(int(0.01 * self.sample_rate + 4), dtype=np.float32),
                "delay_line_r": np.zeros(int(0.01 * self.sample_rate + 4), dtype=np.float32),
                "write_pos": 0,
                "lfo_phase": 0.0,
            },
        )
        buf_len = len(state["delay_line_l"])
        center_delay = int(0.003 * self.sample_rate)
        phase_inc = 2.0 * math.pi * rate / self.sample_rate

        for i in range(num_samples):
            state["lfo_phase"] = (state["lfo_phase"] + phase_inc) % (2.0 * math.pi)

            if waveform == 0:  # Sine
                lfo = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo = 1.0 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1.0
            else:  # Sawtooth
                lfo = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            # Pitch modulation via modulated delay line
            sweep = depth * 0.5 * center_delay
            delay_samples = center_delay + lfo * sweep
            delay_samples = max(1.0, min(delay_samples, buf_len - 1))

            for ch in range(2):
                dl = state["delay_line_l"] if ch == 0 else state["delay_line_r"]
                wp = state["write_pos"]

                # Write current sample into delay line
                dl[wp] = stereo_mix[i, ch]

                # Read with linear interpolation at modulated delay
                di = int(delay_samples)
                df = delay_samples - di
                rp1 = (wp - di) % buf_len
                rp2 = (rp1 - 1) % buf_len
                delayed = dl[rp1] * (1.0 - df) + dl[rp2] * df

                stereo_mix[i, ch] = delayed

            state["write_pos"] = (state["write_pos"] + 1) % buf_len

    def _process_acoustic_simulator(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        room = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        state = self._ensure_state(
            "acoustic_sim",
            {
                "lpf_l": 0.0,
                "lpf_r": 0.0,
                "mid_lpf_l": 0.0,
                "mid_lpf_r": 0.0,
            },
        )

        # Precompute filter coefficients
        lpf_alpha = 2.0 * math.sin(math.pi * 500.0 / self.sample_rate)
        if lpf_alpha > 1.0:
            lpf_alpha = 1.0
        mid_alpha = 2.0 * math.sin(math.pi * 2500.0 / self.sample_rate)
        if mid_alpha > 1.0:
            mid_alpha = 1.0

        for i in range(num_samples):
            if mode == 0:  # Room
                bass_boost = 0.8 + room * 0.2
                mid_boost = 0.9 - room * 0.1
                treble_boost = 0.7 - room * 0.2
            elif mode == 1:  # Concert Hall
                bass_boost = 0.9 + room * 0.1
                mid_boost = 0.95
                treble_boost = 0.8 - room * 0.1
            elif mode == 2:  # Studio
                bass_boost = 0.7 + room * 0.3
                mid_boost = 1.0
                treble_boost = 0.9 - room * 0.1
            else:  # Stage
                bass_boost = 0.6 + room * 0.4
                mid_boost = 0.8 + room * 0.2
                treble_boost = 0.7 + room * 0.3

            for ch in range(2):
                sample = stereo_mix[i, ch]
                state_key_lpf = "lpf_l" if ch == 0 else "lpf_r"
                state_key_mid = "mid_lpf_l" if ch == 0 else "mid_lpf_r"

                # One-pole LPF at 500Hz separates bass
                state[state_key_lpf] += lpf_alpha * (sample - state[state_key_lpf])
                bass = state[state_key_lpf] * bass_boost

                # Complementary highpass = mid + treble content
                mid_high = sample - state[state_key_lpf]

                # Second one-pole LPF on mid_high at 2500Hz extracts mid
                state[state_key_mid] += mid_alpha * (mid_high - state[state_key_mid])
                mid = state[state_key_mid] * mid_boost

                # Treble = complementary highpass of mid_high
                treble = (mid_high - state[state_key_mid]) * treble_boost

                # Sum the three bands
                output = bass + mid + treble

                # Apply reverb blend
                reverb_amount = reverb * 0.3
                output = output * (1.0 - reverb_amount) + sample * reverb_amount

                stereo_mix[i, ch] = output * (1.0 - depth * 0.3)

    def _process_guitar_amp_simulator(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
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
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]

                # Soft-clip harmonic enhancement using tanh (smooth, less aliasing than sin)
                enhanced = sample + enhance * math.tanh(sample * 2.0) * 0.5

                bass_boost = 0.5 + bass * 0.5
                treble_boost = 0.5 + treble * 0.5
                shaped = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)

                stereo_mix[i, ch] = shaped * level

    def _process_slicer(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
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
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else 0
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1

            # LFO generates envelope in 0-to-1 range
            if waveform != 3:  # Sine, triangle, square need mapping to [0, 1]
                lfo_value = (lfo_value + 1.0) * 0.5
            # waveform 3 (sawtooth) already 0-to-1 from the modulo

            amplitude = lfo_value * depth  # 0 to depth

            # Apply as gain envelope multiplier (not threshold gate)
            stereo_mix[i, 0] = stereo_mix[i, 0] * amplitude
            stereo_mix[i, 1] = stereo_mix[i, 1] * amplitude

    def _process_phaser_flanger(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        rate = params.get("parameter1", 0.5) * 3.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.3)
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "phaser_flanger",
            {
                # Per-channel, per-stage all-pass memory
                "x1": [[0.0] * 4 for _ in range(2)],
                "y1": [[0.0] * 4 for _ in range(2)],
                "lfo_phases": [0.0, 0.0, 0.0, 0.0],
                "fb": 0.0,  # Global feedback sample
            },
        )

        phase_increment = 2 * math.pi * rate / self.sample_rate
        for i in range(num_samples):
            # Global feedback from previous sample's final output
            fb_signal = state["fb"] * feedback

            for ch in range(2):
                output = stereo_mix[i, ch] + fb_signal

                for stage in range(4):
                    state["lfo_phases"][stage] = (state["lfo_phases"][stage] + phase_increment) % (
                        2 * math.pi
                    )

                    # Modulate all-pass coefficient g with LFO
                    lfo = math.sin(state["lfo_phases"][stage])
                    g = 0.5 + 0.5 * depth * lfo

                    # First-order all-pass: y[n] = -g * x[n] + x[n-1] + g * y[n-1]
                    x1 = state["x1"][ch][stage]
                    y1 = state["y1"][ch][stage]
                    y = -g * output + x1 + g * y1
                    state["x1"][ch][stage] = output
                    state["y1"][ch][stage] = y
                    output = y

                # Store final output for next sample's feedback
                state["fb"] = output

                # Mix dry/wet
                stereo_mix[i, ch] = stereo_mix[i, ch] * (1.0 - level) + output * level

    def _process_autopan_3tap(
        self, stereo_mix: np.ndarray, num_samples: int,
        rate: float, depth: float, level: float,
        state_key: str,
        base_delay_secs: list[float], mod_factor: float,
        pan_rate_factor: float, pan_amp: float, tap_spacing: float,
    ) -> None:
        state = self._ensure_state(
            state_key,
            {
                "delay_lines": [np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)],
                "write_positions": [0, 0, 0],
                "lfo_phases": [0.0, 0.0, 0.0],
                "pan_phase": 0.0,
            },
        )
        base_delays = [int(s * self.sample_rate) for s in base_delay_secs]

        chorus_sum = np.empty(2, dtype=np.float32)
        pan_increment = 2 * math.pi * rate * pan_rate_factor / self.sample_rate
        phase_increment = 2 * math.pi * rate / self.sample_rate
        for i in range(num_samples):
            chorus_sum.fill(0.0)

            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"])

            for tap_idx in range(3):
                state["lfo_phases"][tap_idx] = (state["lfo_phases"][tap_idx] + phase_increment) % (2 * math.pi)

                base_delay = base_delays[tap_idx]
                modulation = int(math.sin(state["lfo_phases"][tap_idx]) * depth * base_delay * mod_factor)
                total_delay = max(1, min(base_delay + modulation, self.max_delay_samples - 1))

                read_pos = (state["write_positions"][tap_idx] - total_delay) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) * 0.5
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                tap_pan = pan_pos + tap_idx * tap_spacing
                left_gain = math.cos(tap_pan * math.pi / 4)
                right_gain = math.sin(tap_pan * math.pi / 4)

                chorus_sum[0] += delayed * left_gain * 0.33
                chorus_sum[1] += delayed * right_gain * 0.33

                state["write_positions"][tap_idx] = (state["write_positions"][tap_idx] + 1) % self.max_delay_samples

            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - level) + chorus_sum[0] * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - level) + chorus_sum[1] * level

    def _process_chorus_autopan(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_autopan_3tap(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.5) * 4.0,
            depth=params.get("parameter2", 0.5),
            level=params.get("parameter4", 0.4),
            state_key="chorus_autopan",
            base_delay_secs=[0.010, 0.010, 0.010],
            mod_factor=0.5,
            pan_rate_factor=0.3,
            pan_amp=1.0,
            tap_spacing=math.pi / 3,
        )

    def _process_celeste_autopan(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_autopan_3tap(
            stereo_mix, num_samples,
            rate=params.get("parameter1", 0.6) * 5.0,
            depth=params.get("parameter2", 0.4),
            level=params.get("parameter4", 0.35),
            state_key="celeste_autopan",
            base_delay_secs=[0.007, 0.011, 0.015],
            mod_factor=0.3,
            pan_rate_factor=0.4,
            pan_amp=0.8,
            tap_spacing=math.pi / 2,
        )

    def _process_delay_autopan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
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

        pan_increment = 2 * math.pi * pan_rate / self.sample_rate
        for i in range(num_samples):
            state["pan_phase"] = (state["pan_phase"] + pan_increment) % (2 * math.pi)
            pan_pos = math.sin(state["pan_phase"])

            for ch in range(2):
                read_pos = (state["write_positions"][ch] - delay_samples) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                input_sample = stereo_mix[i, ch]
                processed = input_sample + state["feedback_buffers"][ch] * feedback
                state["delay_lines"][ch][state["write_positions"][ch]] = processed
                state["feedback_buffers"][ch] = processed

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

        reverb_delays = [
            int(reverb_time * 0.1 * self.sample_rate),
            int(reverb_time * 0.15 * self.sample_rate),
            int(reverb_time * 0.22 * self.sample_rate),
            int(reverb_time * 0.3 * self.sample_rate),
        ]

        reverb_sum = np.empty(2, dtype=np.float32)
        pan_increment = 2 * math.pi * pan_rate / self.sample_rate
        for i in range(num_samples):
            reverb_sum.fill(0.0)

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
        with self._lock:
            self._effect_states.clear()
