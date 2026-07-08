"""Production flanger processor with correct algorithm."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProductionFlangerProcessor:
    """
    Professional flanger with correct LFO depth, negative feedback, and HF damping.

    Algorithm:
        - LFO sweeps delay line read position
        - ``lfo_depth`` controls sweep width::
            sweep_range = lfo_depth * (max_delay - min_delay) / 2
        - Feedback with sign handling (negative = phase-inverted feedback for jet plane)
        - One-pole lowpass on feedback path for HF damping
        - Linear interpolation for fractional delay reads
        - Separate dry/wet mix parameter
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 44100):
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples
        self.buffer_size = max_delay_samples

        # Delay line: extra 4 samples for interpolation safety; modulo uses buffer_size
        self.delay_line = np.zeros(max_delay_samples + 4, dtype=np.float32)
        self.write_pos = 0

        # LFO
        self.lfo_phase = 0.0
        self.lfo_rate = 0.5
        self.lfo_depth = 0.7

        # Parameters
        self.feedback = 0.5
        self.dry_wet = 0.5
        self.hf_damping = 0.5
        self.fb_lowpass_state = 0.0

        # Delay range (0.1 ms – 10 ms)
        self.min_delay = int(0.0001 * self.sample_rate)  # 0.1 ms
        self.max_delay = int(0.01 * self.sample_rate)  # 10 ms

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process one sample through the flanger.

        Parameters (via *params*):
            rate       — LFO rate in Hz (0.05 – 5.0)
            depth      — Modulation depth (0.0 – 1.0); controls sweep width
            feedback   — Feedback amount (-0.9 – 0.9); negative = inverted
            dry_wet    — Dry/wet mix (0.0 – 1.0, default 0.5)
            hf_damping — HF damping in feedback path (0.0 – 0.99, default 0.5)
        """
        with self.lock:
            self.lfo_rate = params.get("rate", 0.5)
            self.lfo_depth = params.get("depth", 0.7)
            self.feedback = params.get("feedback", 0.5)
            self.dry_wet = params.get("dry_wet", 0.5)
            self.hf_damping = params.get("hf_damping", 0.5)

            # ---- LFO update ----------------------------------------------------
            phase_inc = 2 * math.pi * self.lfo_rate / self.sample_rate
            self.lfo_phase = (self.lfo_phase + phase_inc) % (2 * math.pi)
            lfo = math.sin(self.lfo_phase)  # -1 … 1

            # ---- Modulated delay -----------------------------------------------
            center_delay = (self.min_delay + self.max_delay) / 2.0
            sweep_range = self.lfo_depth * (self.max_delay - self.min_delay) / 2.0
            delay_samples = center_delay + lfo * sweep_range
            delay_samples = max(
                self.min_delay * 0.5, min(delay_samples, self.max_delay * 1.5)
            )

            # ---- Interpolated read from delay line -----------------------------
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int
            read_pos1 = (self.write_pos - delay_int) % self.buffer_size
            read_pos2 = (read_pos1 - 1) % self.buffer_size
            delayed1 = self.delay_line[read_pos1]
            delayed2 = self.delay_line[read_pos2]
            delayed_sample = delayed1 * (1.0 - delay_frac) + delayed2 * delay_frac

            # ---- Feedback with sign handling -----------------------------------
            # Negative feedback = phase-inverted delay for classic jet-plane sound
            if self.feedback >= 0:
                delayed_for_feedback = delayed_sample * self.feedback
            else:
                delayed_for_feedback = -(delayed_sample * abs(self.feedback))

            # ---- HF damping (one-pole lowpass) on feedback path ----------------
            self.fb_lowpass_state += self.hf_damping * (
                delayed_for_feedback - self.fb_lowpass_state
            )

            # ---- Write to delay line -------------------------------------------
            feedback_input = input_sample + self.fb_lowpass_state
            self.delay_line[self.write_pos] = feedback_input
            self.write_pos = (self.write_pos + 1) % self.buffer_size

            # ---- Dry/wet mix ---------------------------------------------------
            return input_sample * (1.0 - self.dry_wet) + delayed_sample * self.dry_wet

    def process_block(self, samples: np.ndarray, params: dict[str, float]) -> None:
        """Process a block of samples with a single lock acquisition.

        Args:
            samples: Block of audio samples (modified in-place).
            params: Dictionary with optional keys:
                "rate" - LFO rate in Hz
                "depth" - Modulation depth (0.0 - 1.0)
                "feedback" - Feedback amount (-0.9 - 0.9)
                "dry_wet" - Dry/wet mix (0.0 - 1.0)
                "hf_damping" - HF damping (0.0 - 0.99)
        """
        with self.lock:
            rate = params.get("rate", 0.5)
            depth = params.get("depth", 0.7)
            fb = params.get("feedback", 0.5)
            dry_wet_val = params.get("dry_wet", 0.5)
            hf_damp = params.get("hf_damping", 0.5)

            phase_inc = 2.0 * math.pi * rate / self.sample_rate
            center_delay = (self.min_delay + self.max_delay) / 2.0
            sweep_range = depth * (self.max_delay - self.min_delay) / 2.0

            for i in range(len(samples)):
                input_sample = float(samples[i])

                # LFO
                self.lfo_phase = (self.lfo_phase + phase_inc) % (2.0 * math.pi)
                lfo = math.sin(self.lfo_phase)

                # Modulated delay
                delay_samples = center_delay + lfo * sweep_range
                delay_samples = max(
                    self.min_delay * 0.5, min(delay_samples, self.max_delay * 1.5)
                )

                # Interpolated read
                delay_int = int(delay_samples)
                delay_frac = delay_samples - delay_int
                read_pos1 = (self.write_pos - delay_int) % self.buffer_size
                read_pos2 = (read_pos1 - 1) % self.buffer_size
                delayed_sample = (
                    self.delay_line[read_pos1] * (1.0 - delay_frac)
                    + self.delay_line[read_pos2] * delay_frac
                )

                # Feedback with sign handling
                if fb >= 0.0:
                    delayed_for_feedback = delayed_sample * fb
                else:
                    delayed_for_feedback = -(delayed_sample * abs(fb))

                # HF damping (one-pole lowpass)
                self.fb_lowpass_state += hf_damp * (
                    delayed_for_feedback - self.fb_lowpass_state
                )

                # Write to delay line
                self.delay_line[self.write_pos] = input_sample + self.fb_lowpass_state
                self.write_pos = (self.write_pos + 1) % self.buffer_size

                # Dry/wet mix
                samples[i] = input_sample * (1.0 - dry_wet_val) + delayed_sample * dry_wet_val
