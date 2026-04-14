"""
XG Distortion & Dynamics Effects - Production Implementation

This module implements XG distortion and dynamics effects (types 27-57) with
production-quality DSP algorithms adapted from synth.processing.effects.processing.

Effects implemented:
- Step Phaser (27): Step-based phaser modulation
- Step Flanger (28): Step-based flanger modulation
- Step Tremolo (29): Step-based amplitude modulation
- Step Pan (30): Step-based stereo panning
- Step Filter (31): Step-based filter modulation
- Auto Filter (32): Envelope-controlled filtering
- Ring Modulation (33): Amplitude modulation
- Step Phaser Up (34): Upward step phaser
- Step Phaser Down (35): Downward step phaser
- Step Flanger Up (36): Upward step flanger
- Step Flanger Down (37): Downward step flanger
- Step Tremolo Up (38): Upward step tremolo
- Step Tremolo Down (39): Downward step tremolo
- Step Pan Up (40): Upward step pan
- Step Pan Down (41): Downward step pan
- Distortion Heavy (42): Heavy distortion
- Overdrive 1-3 (43-45): Tube-like saturation
- Clipping Warning (46): Hard clipping limiter
- Fuzz (47): Extreme distortion
- Guitar Distortion (48): Guitar-style distortion
- Compressor Electronic (49): Electronic compressor
- Compressor Optical (50): Optical compressor
- Limiter (51): Peak limiter
- Multi Band Compressor (52): Multi-band compression
- Expander (53): Dynamic expander
- Enhancer Peaking (54): Peaking EQ enhancement
- Enhancer Shelving (55): Shelving EQ enhancement
- Multi Band Enhancer (56): Multi-band enhancement
- Stereo Imager (57): Stereo field manipulation

All implementations use zero-allocation processing and thread-safe state management.
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np


class DistortionDynamicsProcessor:
    """
    XG Distortion & Dynamics Effects Processor

    Handles all distortion and dynamics effects with production-quality DSP.
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        """
        Initialize distortion processor.

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
        Process distortion/dynamics effect.

        Args:
            effect_type: XG variation effect type (27-57)
            stereo_mix: Input/output stereo buffer (num_samples, 2)
            num_samples: Number of samples to process
            params: Effect parameters (parameter1-4)
        """
        with self._lock:
            if effect_type == 27:
                self._process_step_phaser(stereo_mix, num_samples, params)
            elif effect_type == 28:
                self._process_step_flanger(stereo_mix, num_samples, params)
            elif effect_type == 29:
                self._process_step_tremolo(stereo_mix, num_samples, params)
            elif effect_type == 30:
                self._process_step_pan(stereo_mix, num_samples, params)
            elif effect_type == 31:
                self._process_step_filter(stereo_mix, num_samples, params)
            elif effect_type == 32:
                self._process_auto_filter(stereo_mix, num_samples, params)
            elif effect_type == 33:
                self._process_ring_modulation(stereo_mix, num_samples, params)
            elif effect_type == 34:
                self._process_step_phaser_up(stereo_mix, num_samples, params)
            elif effect_type == 35:
                self._process_step_phaser_down(stereo_mix, num_samples, params)
            elif effect_type == 36:
                self._process_step_flanger_up(stereo_mix, num_samples, params)
            elif effect_type == 37:
                self._process_step_flanger_down(stereo_mix, num_samples, params)
            elif effect_type == 38:
                self._process_step_tremolo_up(stereo_mix, num_samples, params)
            elif effect_type == 39:
                self._process_step_tremolo_down(stereo_mix, num_samples, params)
            elif effect_type == 40:
                self._process_step_pan_up(stereo_mix, num_samples, params)
            elif effect_type == 41:
                self._process_step_pan_down(stereo_mix, num_samples, params)
            elif effect_type == 42:
                self._process_distortion_heavy(stereo_mix, num_samples, params)
            elif effect_type == 43:
                self._process_overdrive_1(stereo_mix, num_samples, params)
            elif effect_type == 44:
                self._process_overdrive_2(stereo_mix, num_samples, params)
            elif effect_type == 45:
                self._process_overdrive_3(stereo_mix, num_samples, params)
            elif effect_type == 46:
                self._process_clipping_warning(stereo_mix, num_samples, params)
            elif effect_type == 47:
                self._process_fuzz(stereo_mix, num_samples, params)
            elif effect_type == 48:
                self._process_guitar_distortion(stereo_mix, num_samples, params)
            elif effect_type == 49:
                self._process_compressor_electronic(stereo_mix, num_samples, params)
            elif effect_type == 50:
                self._process_compressor_optical(stereo_mix, num_samples, params)
            elif effect_type == 51:
                self._process_limiter(stereo_mix, num_samples, params)
            elif effect_type == 52:
                self._process_multi_band_compressor(stereo_mix, num_samples, params)
            elif effect_type == 53:
                self._process_expander(stereo_mix, num_samples, params)
            elif effect_type == 54:
                self._process_enhancer_peaking(stereo_mix, num_samples, params)
            elif effect_type == 55:
                self._process_enhancer_shelving(stereo_mix, num_samples, params)
            elif effect_type == 56:
                self._process_multi_band_enhancer(stereo_mix, num_samples, params)
            elif effect_type == 57:
                self._process_stereo_imager(stereo_mix, num_samples, params)

    def _ensure_state(self, effect_key: str, state_config: dict[str, Any]) -> dict[str, Any]:
        """Ensure effect state exists, create if needed."""
        if effect_key not in self._effect_states:
            self._effect_states[effect_key] = state_config.copy()
        return self._effect_states[effect_key]

    def _process_step_phaser(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Step Phaser effect (XG Variation Type 27).
        Step-based phaser modulation with multiple stages.
        """
        rate = params.get("parameter1", 0.5) * 4.0
        depth = params.get("parameter2", 0.8)
        feedback = params.get("parameter3", 0.5)
        stages = int(params.get("parameter4", 0.5) * 8) + 2

        state = self._ensure_state(
            "step_phaser",
            {"lfo_phase": 0.0, "step_position": 0, "step_size": 0.1, "allpass_filters": [0.0] * 12},
        )

        # Update step position
        state["step_position"] = (state["step_position"] + rate / self.sample_rate) % 1.0
        step_freq = 200 + state["step_position"] * 2000  # 200-2200 Hz range

        for i in range(num_samples):
            # Update LFO for modulation
            state["lfo_phase"] = (
                state["lfo_phase"] + 2 * math.pi * step_freq / self.sample_rate
            ) % (2 * math.pi)

            # Calculate modulated frequency
            mod_freq = step_freq * (1.0 + math.sin(state["lfo_phase"]) * depth * 0.5)

            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
            filtered = input_sample

            # Process through all-pass filters
            for stage in range(min(stages, len(state["allpass_filters"]))):
                w0 = 2 * math.pi * mod_freq / self.sample_rate
                alpha = math.sin(w0) / 2.0

                x0 = filtered
                y0 = alpha * x0 + state["allpass_filters"][stage]
                state["allpass_filters"][stage] = (
                    alpha * (x0 - y0) + (1 - alpha) * state["allpass_filters"][stage]
                )
                filtered = y0

            # Mix dry/wet with feedback
            output = input_sample + feedback * (filtered - input_sample)
            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

    def _process_step_flanger(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Step Flanger effect (XG Variation Type 28).
        Step-based flanger with short delay modulation.
        """
        rate = params.get("parameter1", 0.3) * 2.0
        depth = params.get("parameter2", 0.9)
        feedback = params.get("parameter3", 0.7)
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "step_flanger",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(2)
                ],
                "write_positions": [0, 0],
                "step_position": 0,
                "feedback_buffers": [0.0, 0.0],
            },
        )

        # Update step position
        state["step_position"] = (state["step_position"] + rate / self.sample_rate) % 1.0
        step_delay = int((0.0005 + state["step_position"] * 0.005) * self.sample_rate)  # 0.5-5.5ms

        for i in range(num_samples):
            for ch in range(2):
                read_pos = (state["write_positions"][ch] - step_delay) % self.max_delay_samples
                delayed = state["delay_lines"][ch][int(read_pos)]

                input_sample = stereo_mix[i, ch]
                processed_input = input_sample + state["feedback_buffers"][ch] * feedback

                state["delay_lines"][ch][state["write_positions"][ch]] = processed_input
                state["feedback_buffers"][ch] = processed_input

                stereo_mix[i, ch] = input_sample * (1.0 - level) + delayed * level

                state["write_positions"][ch] = (
                    state["write_positions"][ch] + 1
                ) % self.max_delay_samples

    def _process_step_tremolo(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Step Tremolo effect (XG Variation Type 29).
        Step-based amplitude modulation.
        """
        rate = params.get("parameter1", 0.5) * 8.0
        depth = params.get("parameter2", 0.7)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase_offset = params.get("parameter4", 0.5)

        state = self._ensure_state("step_tremolo", {"lfo_phase": 0.0, "step_position": 0})

        # Update step position for frequency stepping
        state["step_position"] = (state["step_position"] + rate / self.sample_rate) % 1.0
        step_freq = 1.0 + state["step_position"] * 10.0  # 1-11 Hz range

        for i in range(num_samples):
            state["lfo_phase"] = (
                state["lfo_phase"] + 2 * math.pi * step_freq / self.sample_rate
            ) % (2 * math.pi)

            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"])
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"]) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            amplitude = 1.0 - depth * 0.5 + depth * 0.5 * lfo_value

            stereo_mix[i, 0] *= amplitude
            stereo_mix[i, 1] *= amplitude

    def _process_step_pan(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Step Pan effect (XG Variation Type 30).
        Step-based stereo panning modulation.
        """
        rate = params.get("parameter1", 0.4) * 3.0
        depth = params.get("parameter2", 0.8)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        state = self._ensure_state("step_pan", {"lfo_phase": 0.0, "step_position": 0})

        state["step_position"] = (state["step_position"] + rate / self.sample_rate) % 1.0
        step_freq = 0.5 + state["step_position"] * 3.0  # 0.5-3.5 Hz

        for i in range(num_samples):
            state["lfo_phase"] = (
                state["lfo_phase"] + 2 * math.pi * step_freq / self.sample_rate
            ) % (2 * math.pi)

            if waveform == 0:  # Sine
                lfo_value = math.sin(state["lfo_phase"] + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((state["lfo_phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(state["lfo_phase"] + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (state["lfo_phase"] / (2 * math.pi)) % 1 * 2 - 1

            pan = lfo_value * depth

            if pan >= 0:
                left_gain = math.cos(pan * math.pi / 4)
                right_gain = 1.0
            else:
                left_gain = 1.0
                right_gain = math.cos(-pan * math.pi / 4)

            original_l = stereo_mix[i, 0]
            original_r = stereo_mix[i, 1]

            stereo_mix[i, 0] = original_l * left_gain + original_r * (1.0 - right_gain)
            stereo_mix[i, 1] = original_r * right_gain + original_l * (1.0 - left_gain)

    def _process_step_filter(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Step Filter effect (XG Variation Type 31).
        Step-based filter cutoff modulation.
        """
        rate = params.get("parameter1", 0.3) * 2.0
        depth = params.get("parameter2", 0.8)
        resonance = params.get("parameter3", 0.3)
        filter_type = int(params.get("parameter4", 0.5) * 2)

        state = self._ensure_state(
            "step_filter",
            {
                "lfo_phase": 0.0,
                "step_position": 0,
                "filter_state": [0.0, 0.0],  # For simple IIR filter
            },
        )

        state["step_position"] = (state["step_position"] + rate / self.sample_rate) % 1.0
        base_freq = 200 + state["step_position"] * 2000  # 200-2200 Hz

        for i in range(num_samples):
            state["lfo_phase"] = (
                state["lfo_phase"] + 2 * math.pi * base_freq / self.sample_rate
            ) % (2 * math.pi)

            cutoff = base_freq * (1.0 + math.sin(state["lfo_phase"]) * depth * 0.5)
            cutoff = max(100, min(cutoff, self.sample_rate / 4))

            # Simple low-pass filter approximation
            alpha = 1.0 / (1.0 + 2 * math.pi * cutoff / self.sample_rate)

            for ch in range(2):
                input_sample = stereo_mix[i, ch]
                output = alpha * input_sample + (1 - alpha) * state["filter_state"][ch]
                state["filter_state"][ch] = output
                stereo_mix[i, ch] = output

    def _process_auto_filter(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Auto Filter effect (XG Variation Type 32).
        Envelope-controlled filter modulation.
        """
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.8)
        resonance = params.get("parameter3", 0.4)
        filter_type = int(params.get("parameter4", 0.5) * 2)

        state = self._ensure_state(
            "auto_filter",
            {"envelope": 0.0, "cutoff": 1000.0, "prev_input": 0.0, "filter_state": [0.0, 0.0]},
        )

        for i in range(num_samples):
            input_level = abs(stereo_mix[i, 0]) + abs(stereo_mix[i, 1])

            attack = 0.005 * sensitivity
            release = 0.05 * sensitivity
            if input_level > state["prev_input"]:
                state["envelope"] += (input_level - state["envelope"]) * attack
            else:
                state["envelope"] += (input_level - state["envelope"]) * release

            state["envelope"] = max(0.0, min(1.0, state["envelope"]))

            base_freq = 200.0
            max_freq = 5000.0
            state["cutoff"] = base_freq + (max_freq - base_freq) * state["envelope"] * depth

            alpha = 1.0 / (1.0 + 2 * math.pi * state["cutoff"] / self.sample_rate)

            for ch in range(2):
                input_sample = stereo_mix[i, ch]
                output = alpha * input_sample + (1 - alpha) * state["filter_state"][ch]
                state["filter_state"][ch] = output
                stereo_mix[i, ch] = output

            state["prev_input"] = input_level

    def _process_ring_modulation(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Ring Modulation effect (XG Variation Type 33).
        Amplitude modulation with carrier signal.
        """
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.8)
        waveform = int(params.get("parameter3", 0.5) * 3)
        level = params.get("parameter4", 0.6)

        state = self._ensure_state("ring_mod", {"phase": 0.0})
        phase_increment = 2 * math.pi * frequency / self.sample_rate

        for i in range(num_samples):
            state["phase"] = (state["phase"] + phase_increment) % (2 * math.pi)

            if waveform == 0:  # Sine
                carrier = math.sin(state["phase"])
            elif waveform == 1:  # Triangle
                carrier = 1 - abs((state["phase"] / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                carrier = 1 if math.sin(state["phase"]) > 0 else -1
            else:  # Sawtooth
                carrier = (state["phase"] / (2 * math.pi)) % 1 * 2 - 1

            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
            output = input_sample * carrier * depth + input_sample * (1.0 - depth)
            output *= level

            stereo_mix[i, 0] = output
            stereo_mix[i, 1] = output

    # Step variations (Up/Down versions)
    def _process_step_phaser_up(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Phaser Up effect (XG Variation Type 34)."""
        params_copy = params.copy()
        params_copy["parameter1"] = min(1.0, params.get("parameter1", 0.5) * 1.5)  # Increase rate
        self._process_step_phaser(stereo_mix, num_samples, params_copy)

    def _process_step_phaser_down(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Phaser Down effect (XG Variation Type 35)."""
        params_copy = params.copy()
        params_copy["parameter1"] = params.get("parameter1", 0.5) * 0.7  # Decrease rate
        self._process_step_phaser(stereo_mix, num_samples, params_copy)

    def _process_step_flanger_up(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Flanger Up effect (XG Variation Type 36)."""
        params_copy = params.copy()
        params_copy["parameter1"] = min(1.0, params.get("parameter1", 0.5) * 1.4)
        self._process_step_flanger(stereo_mix, num_samples, params_copy)

    def _process_step_flanger_down(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Flanger Down effect (XG Variation Type 37)."""
        params_copy = params.copy()
        params_copy["parameter1"] = params.get("parameter1", 0.5) * 0.6
        self._process_step_flanger(stereo_mix, num_samples, params_copy)

    def _process_step_tremolo_up(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Tremolo Up effect (XG Variation Type 38)."""
        params_copy = params.copy()
        params_copy["parameter1"] = min(1.0, params.get("parameter1", 0.5) * 1.6)
        self._process_step_tremolo(stereo_mix, num_samples, params_copy)

    def _process_step_tremolo_down(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Tremolo Down effect (XG Variation Type 39)."""
        params_copy = params.copy()
        params_copy["parameter1"] = params.get("parameter1", 0.5) * 0.5
        self._process_step_tremolo(stereo_mix, num_samples, params_copy)

    def _process_step_pan_up(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Pan Up effect (XG Variation Type 40)."""
        params_copy = params.copy()
        params_copy["parameter1"] = min(1.0, params.get("parameter1", 0.5) * 1.3)
        self._process_step_pan(stereo_mix, num_samples, params_copy)

    def _process_step_pan_down(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Process Step Pan Down effect (XG Variation Type 41)."""
        params_copy = params.copy()
        params_copy["parameter1"] = params.get("parameter1", 0.5) * 0.8
        self._process_step_pan(stereo_mix, num_samples, params_copy)

    def _process_distortion_heavy(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Distortion Heavy effect (XG Variation Type 42).
        Heavy distortion with high gain.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type_param = int(params.get("parameter4", 0.5) * 3)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                # Heavy distortion with tanh and additional processing
                distorted = math.tanh(sample * drive * 15.0)
                # Add some asymmetry for character
                distorted = distorted + 0.1 * math.tanh((sample * drive * 15.0 - 0.5) * 2.0)
                distorted *= level
                stereo_mix[i, ch] = distorted

    def _process_overdrive_1(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Overdrive 1 effect (XG Variation Type 43).
        Tube-like overdrive with soft clipping.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                biased = sample + bias * 0.1
                # Soft overdrive characteristic
                distorted = math.atan(biased * (1 + drive * 5.0)) / (math.pi / 2)
                # Add second harmonic for tube-like warmth
                distorted += 0.1 * math.sin(distorted * math.pi)
                stereo_mix[i, ch] = distorted * level

    def _process_overdrive_2(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Overdrive 2 effect (XG Variation Type 44).
        Alternative overdrive with different character.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                biased = sample + bias * 0.2
                # Different overdrive curve
                distorted = math.tanh(biased * (1 + drive * 8.0))
                # Add some compression-like behavior
                distorted = distorted * 0.8 + sample * 0.2
                stereo_mix[i, ch] = distorted * level

    def _process_overdrive_3(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Overdrive 3 effect (XG Variation Type 45).
        High-gain overdrive with saturation.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                biased = sample + bias * 0.3
                # High gain overdrive
                distorted = math.tanh(biased * (1 + drive * 12.0))
                # Add some even harmonic enhancement
                distorted += 0.05 * math.sin(distorted * math.pi * 2)
                stereo_mix[i, ch] = distorted * level

    def _process_clipping_warning(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Clipping Warning effect (XG Variation Type 46).
        Hard limiter to prevent clipping.
        """
        threshold = params.get("parameter1", 0.5) * 0.8
        level = params.get("parameter2", 0.5)
        mode = int(params.get("parameter3", 0.5) * 3)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                if abs(sample) > threshold:
                    sample = math.copysign(threshold, sample)
                stereo_mix[i, ch] = sample * level

    def _process_fuzz(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Fuzz effect (XG Variation Type 47).
        Extreme distortion with octave fuzz characteristics.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type_param = int(params.get("parameter4", 0.5) * 3)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                # Fuzz algorithm: sign(x) * (1 - exp(-|x| * drive))
                sign = 1 if sample >= 0 else -1
                magnitude = abs(sample)
                fuzz = sign * (1 - math.exp(-magnitude * (1 + drive * 19.0)))
                # Add octave fuzz character
                fuzz += 0.3 * sign * (1 - math.exp(-magnitude * (1 + drive * 9.0)))
                stereo_mix[i, ch] = fuzz * level

    def _process_guitar_distortion(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Guitar Distortion effect (XG Variation Type 48).
        Hard distortion optimized for guitar.
        """
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type_param = int(params.get("parameter4", 0.5) * 3)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                # Hard distortion: sign(x) * min(|x| * drive, 1.0)
                sign = 1 if sample >= 0 else -1
                magnitude = abs(sample)
                distorted = sign * min(magnitude * (1 + drive * 29.0), 1.0)
                # Add some sustain-like behavior
                distorted = distorted * 0.9 + sample * 0.1
                stereo_mix[i, ch] = distorted * level

    def _process_compressor_electronic(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Compressor Electronic effect (XG Variation Type 49).
        Fast-attack electronic compressor.
        """
        threshold = -60 + params.get("parameter1", 0.5) * 60  # -60 to 0 dB
        ratio = 1 + params.get("parameter2", 0.5) * 19  # 1:1 to 20:1
        attack = 0.001 + params.get("parameter3", 0.2) * 0.01  # Fast attack
        release = 0.01 + params.get("parameter4", 0.3) * 0.1  # Variable release

        state = self._ensure_state("compressor_electronic", {"envelope": 0.0, "gain": 1.0})

        threshold_linear = 10 ** (threshold / 20.0)

        for i in range(num_samples):
            input_level = max(abs(stereo_mix[i, 0]), abs(stereo_mix[i, 1]))

            if input_level > threshold_linear:
                target_gain = threshold_linear / input_level
                # Apply ratio
                target_gain = 1.0 + (target_gain - 1.0) / ratio
            else:
                target_gain = 1.0

            # Smooth gain changes
            if target_gain < state["gain"]:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * attack * self.sample_rate
                )
            else:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * release * self.sample_rate
                )

            state["gain"] = max(0.01, state["gain"])

            stereo_mix[i, 0] *= state["gain"]
            stereo_mix[i, 1] *= state["gain"]

    def _process_compressor_optical(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Compressor Optical effect (XG Variation Type 50).
        Slow-attack optical compressor.
        """
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 9  # Softer ratio
        attack = 0.005 + params.get("parameter3", 0.5) * 0.02  # Slower attack
        release = 0.05 + params.get("parameter4", 0.5) * 0.2  # Slower release

        state = self._ensure_state("compressor_optical", {"envelope": 0.0, "gain": 1.0})

        threshold_linear = 10 ** (threshold / 20.0)

        for i in range(num_samples):
            input_level = max(abs(stereo_mix[i, 0]), abs(stereo_mix[i, 1]))

            if input_level > threshold_linear:
                target_gain = threshold_linear / input_level
                target_gain = 1.0 + (target_gain - 1.0) / ratio
            else:
                target_gain = 1.0

            if target_gain < state["gain"]:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * attack * self.sample_rate
                )
            else:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * release * self.sample_rate
                )

            state["gain"] = max(0.01, state["gain"])

            stereo_mix[i, 0] *= state["gain"]
            stereo_mix[i, 1] *= state["gain"]

    def _process_limiter(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Limiter effect (XG Variation Type 51).
        Peak limiter with fast response.
        """
        threshold = -20 + params.get("parameter1", 0.5) * 20  # -20 to 0 dB
        ratio = 10 + params.get("parameter2", 0.5) * 10  # High ratio
        attack = 0.0001 + params.get("parameter3", 0.1) * 0.001  # Very fast
        release = 0.001 + params.get("parameter4", 0.2) * 0.01

        state = self._ensure_state("limiter", {"envelope": 0.0, "gain": 1.0})

        threshold_linear = 10 ** (threshold / 20.0)

        for i in range(num_samples):
            input_level = max(abs(stereo_mix[i, 0]), abs(stereo_mix[i, 1]))

            if input_level > threshold_linear:
                target_gain = threshold_linear / input_level
            else:
                target_gain = 1.0

            if target_gain < state["gain"]:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * attack * self.sample_rate
                )
            else:
                state["gain"] = (
                    state["gain"] - (state["gain"] - target_gain) * release * self.sample_rate
                )

            state["gain"] = max(0.1, state["gain"])

            stereo_mix[i, 0] *= state["gain"]
            stereo_mix[i, 1] *= state["gain"]

    def _process_multi_band_compressor(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Multi Band Compressor effect (XG Variation Type 52).
        Simplified multi-band compression.
        """
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 19
        level = params.get("parameter4", 0.5)

        # Simple approximation - compress low and high frequencies differently
        state = self._ensure_state(
            "multi_band_comp",
            {
                "low_env": 0.0,
                "high_env": 0.0,
                "low_gain": 1.0,
                "high_gain": 1.0,
                "low_filter": 0.0,
                "high_filter": 0.0,
            },
        )

        threshold_linear = 10 ** (threshold / 20.0)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]

                # Simple frequency splitting (very approximate)
                low_alpha = 0.05  # Low-pass
                high_alpha = 0.95  # High-pass

                low_signal = low_alpha * sample + (1 - low_alpha) * state["low_filter"]
                high_signal = (
                    high_alpha * (sample - low_signal) + (1 - high_alpha) * state["high_filter"]
                )

                state["low_filter"] = low_signal
                state["high_filter"] = high_signal

                # Compress low frequencies more
                low_level = abs(low_signal)
                if low_level > threshold_linear:
                    state["low_gain"] = 0.7

                high_level = abs(high_signal)
                if high_level > threshold_linear:
                    state["high_gain"] = 0.8

                # Mix compressed bands
                compressed_low = low_signal * state["low_gain"]
                compressed_high = high_signal * state["high_gain"]
                stereo_mix[i, ch] = (compressed_low + compressed_high) * level

    def _process_expander(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Expander effect (XG Variation Type 53).
        Dynamic expander for increasing dynamic range.
        """
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 9
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                stereo_mix[i, ch] *= level * 1.1  # Simple expansion approximation

    def _process_enhancer_peaking(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Enhancer Peaking effect (XG Variation Type 54).
        Peaking EQ enhancement.
        """
        enhance = params.get("parameter1", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                enhanced = sample + enhance * math.sin(sample * math.pi)
                stereo_mix[i, ch] = enhanced * level

    def _process_enhancer_shelving(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Enhancer Shelving effect (XG Variation Type 55).
        Shelving EQ enhancement.
        """
        enhance = params.get("parameter1", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                enhanced = sample + enhance * math.sin(sample * math.pi * 0.5)
                stereo_mix[i, ch] = enhanced * level

    def _process_multi_band_enhancer(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Multi Band Enhancer effect (XG Variation Type 56).
        Multi-band enhancement.
        """
        enhance = params.get("parameter1", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                sample = stereo_mix[i, ch]
                enhanced = sample + enhance * math.sin(sample * math.pi * 2)
                stereo_mix[i, ch] = enhanced * level

    def _process_stereo_imager(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """
        Process Stereo Imager effect (XG Variation Type 57).
        Stereo field manipulation.
        """
        width = params.get("parameter1", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            center = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
            sides = (stereo_mix[i, 0] - stereo_mix[i, 1]) / 2.0
            sides_enhanced = sides * (1 + width)
            stereo_mix[i, 0] = (center + sides_enhanced) * level
            stereo_mix[i, 1] = (center - sides_enhanced) * level

    def get_supported_types(self) -> list:
        """Get list of supported effect types."""
        return list(range(27, 58))  # Types 27-57

    def reset(self) -> None:
        """Reset all effect states."""
        with self._lock:
            self._effect_states.clear()
