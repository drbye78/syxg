"""
XG Special Variation Effects - Production Implementation

This module implements XG special variation effects (types 58-83) with
production-quality DSP algorithms adapted from synth.processing.effects.processing.

Effects implemented:
- Expander (57): Downward expander
- Vocoder Comb Filter (58): Vocoder with comb filter characteristics
- Vocoder Phaser (59): Vocoder with phaser modulation
- Pitch Shift Up Minor Third (60): Pitch shift up by minor third
- Pitch Shift Down Minor Third (61): Pitch shift down by minor third
- Pitch Shift Up Major Third (62): Pitch shift up by major third
- Pitch Shift Down Major Third (63): Pitch shift down by major third
- Harmonizer (64): Harmonic interval generation
- Detune (65): Subtle pitch detuning
- ERL Hall Small (66): Early reflection hall small
- ERL Hall Medium (67): Early reflection hall medium
- ERL Hall Large (68): Early reflection hall large
- ERL Room Small (69): Early reflection room small
- ERL Room Medium (70): Early reflection room medium
- ERL Room Large (71): Early reflection room large
- ERL Studio Light (72): Early reflection studio light
- ERL Studio Heavy (73): Early reflection studio heavy
- Gate Reverb Fast Attack (74): Gate reverb with fast attack
- Gate Reverb Medium Attack (75): Gate reverb with medium attack
- Gate Reverb Slow Attack (76): Gate reverb with slow attack
- Voice Cancel (77): Voice cancellation effect
- Karaoke Reverb (78): Karaoke reverb effect
- Karaoke Echo (79): Karaoke echo effect
- Through (80-83): Pass-through effects

All implementations use zero-allocation processing and thread-safe state management.
"""

from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np


class SpecialVariationProcessor:
    """
    XG Special Variation Effects Processor

    Handles all special variation effects with production-quality DSP.
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
            if effect_type == 57:
                self._process_expander(stereo_mix, num_samples, params)
            elif effect_type == 58:
                self._process_vocoder_comb_filter(stereo_mix, num_samples, params)
            elif effect_type == 59:
                self._process_vocoder_phaser(stereo_mix, num_samples, params)
            elif effect_type == 60:
                self._process_pitch_shift_up_minor_third(stereo_mix, num_samples, params)
            elif effect_type == 61:
                self._process_pitch_shift_down_minor_third(stereo_mix, num_samples, params)
            elif effect_type == 62:
                self._process_pitch_shift_up_major_third(stereo_mix, num_samples, params)
            elif effect_type == 63:
                self._process_pitch_shift_down_major_third(stereo_mix, num_samples, params)
            elif effect_type == 64:
                self._process_harmonizer(stereo_mix, num_samples, params)
            elif effect_type == 65:
                self._process_detune(stereo_mix, num_samples, params)
            elif effect_type == 66:
                self._process_erl_hall_small(stereo_mix, num_samples, params)
            elif effect_type == 67:
                self._process_erl_hall_medium(stereo_mix, num_samples, params)
            elif effect_type == 68:
                self._process_erl_hall_large(stereo_mix, num_samples, params)
            elif effect_type == 69:
                self._process_erl_room_small(stereo_mix, num_samples, params)
            elif effect_type == 70:
                self._process_erl_room_medium(stereo_mix, num_samples, params)
            elif effect_type == 71:
                self._process_erl_room_large(stereo_mix, num_samples, params)
            elif effect_type == 72:
                self._process_erl_studio_light(stereo_mix, num_samples, params)
            elif effect_type == 73:
                self._process_erl_studio_heavy(stereo_mix, num_samples, params)
            elif effect_type == 74:
                self._process_gate_reverb_fast_attack(stereo_mix, num_samples, params)
            elif effect_type == 75:
                self._process_gate_reverb_medium_attack(stereo_mix, num_samples, params)
            elif effect_type == 76:
                self._process_gate_reverb_slow_attack(stereo_mix, num_samples, params)
            elif effect_type == 77:
                self._process_voice_cancel(stereo_mix, num_samples, params)
            elif effect_type == 78:
                self._process_karaoke_reverb(stereo_mix, num_samples, params)
            elif effect_type == 79:
                self._process_karaoke_echo(stereo_mix, num_samples, params)
            elif 80 <= effect_type <= 83:
                # Through effects - pass through unchanged
                pass

    def _ensure_state(self, effect_key: str, state_config: dict[str, Any]) -> dict[str, Any]:
        if effect_key not in self._effect_states:
            self._effect_states[effect_key] = state_config.copy()
        return self._effect_states[effect_key]

    def _process_expander(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        """Downward expander — attenuates signals below threshold."""
        threshold = params.get("parameter1", 0.5) * 0.8 + 0.1  # 0.1-0.9
        ratio = params.get("parameter2", 0.5) * 10.0 + 1.0      # 1:1 to 11:1
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            for ch in range(2):
                s = stereo_mix[i, ch]
                abs_s = abs(s)
                if abs_s < threshold:
                    # Attenuate below threshold
                    gain = (abs_s / max(threshold, 1e-10)) ** (ratio - 1.0)
                    stereo_mix[i, ch] = s * gain * level
                else:
                    stereo_mix[i, ch] = s * level * 0.9  # unity-ish gain

    def _process_vocoder_comb_filter(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        frequency = params.get("parameter1", 0.5) * 1000.0  # 0-1000 Hz
        resonance = params.get("parameter2", 0.5) * 0.9 + 0.1  # 0.1-1.0
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "vocoder_comb",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "feedback_l": 0.0,
                "feedback_r": 0.0,
                "write_pos_l": 0,
                "write_pos_r": 0,
            },
        )

        # Calculate delay time based on frequency (fundamental period)
        delay_samples = max(1, int(self.sample_rate / max(frequency, 20.0)))
        delay_samples = min(delay_samples, self.max_delay_samples - 1)

        for i in range(num_samples):
            for ch in range(2):
                delay_line = state["delay_line_l"] if ch == 0 else state["delay_line_r"]
                write_pos = state["write_pos_l"] if ch == 0 else state["write_pos_r"]
                feedback_key = "feedback_l" if ch == 0 else "feedback_r"

                read_pos = (write_pos - delay_samples) % self.max_delay_samples
                delayed = delay_line[int(read_pos)]

                # Apply resonance feedback
                input_sample = stereo_mix[i, ch]
                processed = input_sample + state[feedback_key] * resonance

                delay_line[write_pos] = processed
                state[feedback_key] = processed

                # Comb filter: input + delayed
                stereo_mix[i, ch] = (input_sample + delayed) * level

                if ch == 0:
                    state["write_pos_l"] = (write_pos + 1) % self.max_delay_samples
                else:
                    state["write_pos_r"] = (write_pos + 1) % self.max_delay_samples

    def _process_vocoder_phaser(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.8)
        feedback = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        state = self._ensure_state(
            "vocoder_phaser", {"lfo_phase": 0.0, "allpass_filters": [0.0] * 6}
        )

        for i in range(num_samples):
            # Update LFO with vocoder-like modulation
            lfo_phase = state["lfo_phase"]
            lfo_phase += 2 * math.pi * frequency / self.sample_rate
            state["lfo_phase"] = lfo_phase % (2 * math.pi)

            # Modulate frequency based on input level for vocoder effect
            input_level = abs(stereo_mix[i, 0]) + abs(stereo_mix[i, 1])
            mod_freq = frequency * (1.0 + input_level * 2.0)  # Modulate with input level

            input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
            filtered = input_sample

            # Process through all-pass filters with modulated frequency
            for stage in range(len(state["allpass_filters"])):
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
            stereo_mix[i, 0] = output * level
            stereo_mix[i, 1] = output * level

    def _process_pitch_shift(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float], semitones: float) -> None:
        """Real-time pitch shift using delay-line interpolation.
        
        Uses a delay line with fractional read offset for pitch shifting.
        A raised-cosine cross-fade window smooths the cyclic buffer transition.
        """
        ratio = 2.0 ** (semitones / 12.0)
        mix = params.get("parameter1", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Fixed base delay (3ms) for the delay line
        base_delay = max(1, int(0.003 * self.sample_rate))
        # Cross-fade window size in samples (20ms for smooth transitions)
        fade_size = max(1, int(0.020 * self.sample_rate))
        
        state = self._ensure_state("pitch_shift", {
            "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
            "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
            "write_pos": 0,
            "read_pos_frac": 0.0,  # fractional read offset counter
        })
        
        dl_l = state["delay_line_l"]
        dl_r = state["delay_line_r"]
        wp = state["write_pos"]
        rpf = state["read_pos_frac"]
        
        for i in range(num_samples):
            # Write current input samples to delay line
            dl_l[wp] = stereo_mix[i, 0]
            dl_r[wp] = stereo_mix[i, 1]
            
            # Read position: base_delay samples behind write, with fractional offset
            # The phase advances by (ratio - 1.0) per sample, creating pitch shift
            rpf += ratio - 1.0
            
            # Calculate absolute read position
            abs_read_pos = wp - base_delay + rpf
            
            # Wrap into delay line range
            read_pos = abs_read_pos % self.max_delay_samples
            read_idx = int(read_pos)
            frac = read_pos - read_idx
            next_idx = (read_idx + 1) % self.max_delay_samples
            
            # Linear interpolation between adjacent samples
            shifted_l = dl_l[read_idx] * (1.0 - frac) + dl_l[next_idx] * frac
            shifted_r = dl_r[read_idx] * (1.0 - frac) + dl_r[next_idx] * frac
            
            # Cross-fade at wrap point to avoid glitches
            # Calculate position in the cross-fade window
            wrap_distance = abs(abs_read_pos - self.max_delay_samples) if abs_read_pos >= base_delay else 0.0
            fade_gain = 1.0
            if wrap_distance < fade_size:
                # Raised cosine cross-fade
                fade_gain = 0.5 * (1.0 - np.cos(np.pi * wrap_distance / fade_size))
                # When fading out (near wrap), cross-fade with dry signal
                dry = stereo_mix[i, 0], stereo_mix[i, 1]
                wet = shifted_l, shifted_r
                shifted_l = wet[0] * fade_gain + dry[0] * (1.0 - fade_gain)
                shifted_r = wet[1] * fade_gain + dry[1] * (1.0 - fade_gain)
            
            # Dry/wet mix
            stereo_mix[i, 0] = stereo_mix[i, 0] * (1.0 - mix) + shifted_l * mix * level
            stereo_mix[i, 1] = stereo_mix[i, 1] * (1.0 - mix) + shifted_r * mix * level
            
            # Advance write position
            wp = (wp + 1) % self.max_delay_samples
        
        # Store updated state
        state["write_pos"] = wp
        state["read_pos_frac"] = rpf % self.max_delay_samples

    def _process_pitch_shift_up_minor_third(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        self._process_pitch_shift(stereo_mix, num_samples, params, 3.0)

    def _process_pitch_shift_down_minor_third(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        self._process_pitch_shift(stereo_mix, num_samples, params, -3.0)

    def _process_pitch_shift_up_major_third(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        self._process_pitch_shift(stereo_mix, num_samples, params, 4.0)

    def _process_pitch_shift_down_major_third(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        self._process_pitch_shift(stereo_mix, num_samples, params, -4.0)

    def _process_harmonizer(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Harmonizer — adds a pitch-shifted voice at specified interval."""
        shift_semitones = params.get("parameter1", 0.5) * 24.0 - 12.0  # -12 to +12 semitones
        mix = params.get("parameter2", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Save dry, process pitch-shifted version, mix with dry
        if not hasattr(self, '_harmonizer_work'):
            self._harmonizer_work = np.zeros((self.max_delay_samples, 2), dtype=np.float32)
        work = self._harmonizer_work
        
        # Copy first num_samples of stereo_mix to work buffer
        work[:num_samples, :] = stereo_mix[:num_samples, :]
        
        # Process work through pitch shift
        self._process_pitch_shift(work[:num_samples, :], num_samples, {"parameter1": 0.5, "parameter4": 0.5}, shift_semitones)
        
        # Mix: original (dry) + shifted (harmony)
        for i in range(num_samples):
            for ch in range(2):
                stereo_mix[i, ch] = stereo_mix[i, ch] * (1.0 - mix) + work[i, ch] * mix * level

    def _process_detune(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Detune — very slight pitch shift (0-50 cents)."""
        detune_cents = params.get("parameter1", 0.5) * 50.0  # 0-50 cents
        mix = params.get("parameter2", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Convert cents to semitones
        semitones = detune_cents / 100.0
        
        # Use pitch shift with very small semitone offset
        self._process_pitch_shift(stereo_mix, num_samples, params, semitones)

    def _process_erl(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float],
        state_key: str, delay_secs: list[float], tap_gain: float,
    ) -> None:
        level = params.get("parameter2", 0.5)
        n_taps = len(delay_secs)
        delays = [int(s * self.sample_rate) for s in delay_secs]

        state = self._ensure_state(
            state_key,
            {
                "delay_lines": [np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(n_taps)],
                "write_positions": [0] * n_taps,
            },
        )

        for i in range(num_samples):
            reflection_sum = 0.0
            for tap_idx, delay in enumerate(delays):
                read_pos = (state["write_positions"][tap_idx] - delay) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                input_sample = (stereo_mix[i, 0] + stereo_mix[i, 1]) / 2.0
                state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = input_sample

                reflection_sum += delayed * tap_gain
                state["write_positions"][tap_idx] = (state["write_positions"][tap_idx] + 1) % self.max_delay_samples

            # Dry/wet mix: attenuate dry signal proportionally to level, mix in reflections
            reflection_sum *= level
            for ch in range(2):
                dry = stereo_mix[i, ch]
                wet = reflection_sum
                stereo_mix[i, ch] = dry * (1.0 - level) + wet * level

    def _process_erl_hall_small(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_hall_small",
                          [0.008, 0.013, 0.019, 0.027], 0.15)

    def _process_erl_hall_medium(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_hall_medium",
                          [0.010, 0.017, 0.025, 0.035, 0.045, 0.055], 0.12)

    def _process_erl_hall_large(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_hall_large",
                          [0.015, 0.025, 0.038, 0.052, 0.068, 0.085, 0.105, 0.125], 0.1)

    def _process_erl_room_small(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_room_small",
                          [0.005, 0.008, 0.012], 0.18)

    def _process_erl_room_medium(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_room_medium",
                          [0.007, 0.011, 0.016, 0.022], 0.15)

    def _process_erl_room_large(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_room_large",
                          [0.010, 0.015, 0.022, 0.030, 0.040], 0.13)

    def _process_erl_studio_light(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_studio_light",
                          [0.006, 0.012, 0.018, 0.024], 0.16)

    def _process_erl_studio_heavy(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_erl(stereo_mix, num_samples, params, "erl_studio_heavy",
                          [0.005, 0.009, 0.014, 0.020, 0.027, 0.035], 0.11)

    def _process_gate_reverb(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float],
        state_key: str, attack_time: float, release_time: float,
    ) -> None:
        gate_threshold = params.get("parameter1", 0.5)
        level = params.get("parameter2", 0.5)
        density = 0.5

        state = self._ensure_state(state_key, {
            "delay_value_l": 0.0,
            "delay_value_r": 0.0,
            "envelope": 0.0,
        })

        for i in range(num_samples):
            # Gate envelope
            input_level = (abs(stereo_mix[i, 0]) + abs(stereo_mix[i, 1])) * 0.5
            if input_level > gate_threshold:
                state["envelope"] = min(1.0, state["envelope"] + 1.0 / (attack_time * self.sample_rate))
            else:
                state["envelope"] = max(0.0, state["envelope"] - 1.0 / (release_time * self.sample_rate))
            gate = state["envelope"]

            for ch in range(2):
                sample = stereo_mix[i, ch]
                # Simple 1-sample feedback delay as reverb character
                delay_val = state["delay_value_l"] if ch == 0 else state["delay_value_r"]
                reverb = delay_val * density
                state["delay_value_l" if ch == 0 else "delay_value_r"] = sample + reverb * 0.3
                # Gated output: dry + reverb character, both gated
                stereo_mix[i, ch] = (sample + reverb) * gate * level

    def _process_gate_reverb_fast_attack(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_gate_reverb(stereo_mix, num_samples, params, "gate_reverb_fast", 0.01, 0.2)

    def _process_gate_reverb_medium_attack(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_gate_reverb(stereo_mix, num_samples, params, "gate_reverb_medium", 0.05, 0.25)

    def _process_gate_reverb_slow_attack(self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]) -> None:
        self._process_gate_reverb(stereo_mix, num_samples, params, "gate_reverb_slow", 0.1, 0.3)

    def _process_voice_cancel(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        """Voice cancel using L-R phase cancellation."""
        for i in range(num_samples):
            left = stereo_mix[i, 0]
            right = stereo_mix[i, 1]
            cancel = (left - right) * 0.5
            stereo_mix[i, 0] = cancel
            stereo_mix[i, 1] = cancel

    def _process_karaoke_reverb(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        level = params.get("parameter1", 0.5)

        state = self._ensure_state(
            "karaoke_reverb",
            {
                "delay_lines": [
                    np.zeros(self.max_delay_samples, dtype=np.float32) for _ in range(3)
                ],
                "write_positions": [0, 0, 0],
                "feedback_l": 0.0,
                "feedback_r": 0.0,
            },
        )

        # Karaoke-optimized delays
        delays = [
            int(0.020 * self.sample_rate),
            int(0.035 * self.sample_rate),
            int(0.050 * self.sample_rate),
        ]

        for i in range(num_samples):
            reverb_sum = [0.0, 0.0]

            for tap_idx, delay in enumerate(delays):
                read_pos = (state["write_positions"][tap_idx] - delay) % self.max_delay_samples
                delayed = state["delay_lines"][tap_idx][int(read_pos)]

                for ch in range(2):
                    feedback_val = state["feedback_l"] if ch == 0 else state["feedback_r"]
                    sample = stereo_mix[i, ch]
                    processed = sample + feedback_val * 0.3
                    state["delay_lines"][tap_idx][state["write_positions"][tap_idx]] = processed
                    state["feedback_l" if ch == 0 else "feedback_r"] = delayed * 0.4

                    reverb_sum[ch] += delayed * 0.2

                state["write_positions"][tap_idx] = (
                    state["write_positions"][tap_idx] + 1
                ) % self.max_delay_samples

            reverb_sum[0] *= level
            reverb_sum[1] *= level
            stereo_mix[i, 0] += reverb_sum[0]
            stereo_mix[i, 1] += reverb_sum[1]

    def _process_karaoke_echo(
        self, stereo_mix: np.ndarray, num_samples: int, params: dict[str, float]
    ) -> None:
        level = params.get("parameter1", 0.5)

        state = self._ensure_state(
            "karaoke_echo",
            {
                "delay_line_l": np.zeros(self.max_delay_samples, dtype=np.float32),
                "delay_line_r": np.zeros(self.max_delay_samples, dtype=np.float32),
                "write_pos_l": 0,
                "write_pos_r": 0,
                "feedback_l": 0.0,
                "feedback_r": 0.0,
            },
        )

        delay_samples = int(0.3 * self.sample_rate)  # 300ms delay typical for karaoke

        for i in range(num_samples):
            for ch in range(2):
                dl_key = "delay_line_l" if ch == 0 else "delay_line_r"
                wp_key = "write_pos_l" if ch == 0 else "write_pos_r"
                fb_key = "feedback_l" if ch == 0 else "feedback_r"

                sample = stereo_mix[i, ch]
                wp = state[wp_key]

                read_pos = (wp - delay_samples) % self.max_delay_samples
                delayed = state[dl_key][int(read_pos)]

                feedback_sample = state[fb_key] * 0.4  # Moderate feedback
                processed = sample + feedback_sample

                state[dl_key][wp] = processed
                state[fb_key] = processed

                output = sample * (1.0 - level) + delayed * level
                stereo_mix[i, ch] = output

                state[wp_key] = (wp + 1) % self.max_delay_samples

    def get_supported_types(self) -> list:
        """Get list of supported effect types."""
        return list(range(57, 84))  # Types 57-83

    def reset(self) -> None:
        """Reset all effect states."""
        with self._lock:
            self._effect_states.clear()

