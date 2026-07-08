"""Production phaser processor."""

from __future__ import annotations

import math
import threading

import numpy as np


class ProductionPhaserProcessor:
    """
    Professional phaser implementation with modulated all-pass filters.

    Uses cascaded first-order all-pass IIR filters:
        y[n] = -g * x[n] + x[n-1] + g * y[n-1]

    Features:
    - Multi-stage all-pass filter chain (logarithmically spaced notches)
    - LFO modulation of filter frequencies
    - Global feedback control
    - Dry/wet mix
    - Thread-safe with RLock
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.num_stages = 6

        # State per stage: previous input and previous output
        self.x1: list[float] = [0.0] * self.num_stages
        self.y1: list[float] = [0.0] * self.num_stages

        # Base notch frequencies spread logarithmically from 200 Hz to 4000 Hz
        self.base_freqs: list[float] = [
            200.0 * (4000.0 / 200.0) ** (i / max(1, self.num_stages - 1))
            for i in range(self.num_stages)
        ]

        # LFO
        self.lfo_phase: float = 0.0
        self.lfo_rate: float = 1.0
        self.lfo_depth: float = 0.5

        # Feedback (-0.9 to 0.9)
        self.feedback: float = 0.3

        # Dry/wet mix (0.0 = dry, 1.0 = wet)
        self.dry_wet: float = 0.5

        # One-sample feedback state
        self._feedback_state: float = 0.0

        self.lock = threading.RLock()

    def process_sample(self, input_sample: float, params: dict[str, float]) -> float:
        """Process a single sample through the phaser.

        Args:
            input_sample: Input audio sample.
            params: Dictionary with optional keys:
                "rate" - LFO rate in Hz (0.1 - 10.0)
                "depth" - LFO depth (0.0 - 1.0)
                "feedback" - Feedback amount (-0.9 - 0.9)
                "dry_wet" - Dry/wet mix (0.0 - 1.0)

        Returns:
            Processed output sample.
        """
        with self.lock:
            # Update parameters
            self.lfo_rate = params.get("rate", 1.0)
            self.lfo_depth = params.get("depth", 0.5)
            self.feedback = params.get("feedback", 0.3)
            self.dry_wet = params.get("dry_wet", 0.5)

            # Compute LFO phase
            phase_increment = 2.0 * math.pi * self.lfo_rate / self.sample_rate
            self.lfo_phase = (self.lfo_phase + phase_increment) % (2.0 * math.pi)
            lfo = math.sin(self.lfo_phase)

            # Process through the feedback loop: input + output * feedback
            # Note: feedback is applied after the all-pass chain on the *next*
            # sample.  Since we process per-sample here, we store the overall
            # output internally and let the caller's feedback accumulate
            # naturally.  We keep a simple one-sample feedback state.
            stage_input = input_sample + self._feedback_state * self.feedback
            self._feedback_state = 0.0  # will be set after all-pass chain

            # Process through cascaded all-pass stages
            stage_output = stage_input
            for i in range(self.num_stages):
                # Modulated frequency for this stage
                freq = self.base_freqs[i] * (1.0 + lfo * self.lfo_depth)
                freq = max(20.0, min(freq, self.sample_rate * 0.45))

                # Compute all-pass coefficient g
                # g = (tan(omega/2) - 1) / (tan(omega/2) + 1)
                omega = 2.0 * math.pi * freq / self.sample_rate
                tan_half = math.tan(omega / 2.0)
                g = (tan_half - 1.0) / (tan_half + 1.0)

                # First-order all-pass:
                #   y[n] = -g * x[n] + x[n-1] + g * y[n-1]
                y = -g * stage_output + self.x1[i] + g * self.y1[i]
                self.x1[i] = stage_output
                self.y1[i] = y
                stage_output = y

            # Store overall output for feedback on next sample
            self._feedback_state = stage_output

            # Dry/wet mix
            result = input_sample * (1.0 - self.dry_wet) + stage_output * self.dry_wet
            return result

    def process_block(self, samples: np.ndarray, params: dict[str, float]) -> None:
        """Process a block of samples with a single lock acquisition.

        Args:
            samples: Block of audio samples (modified in-place).
            params: Dictionary with optional keys:
                "rate" - LFO rate in Hz
                "depth" - LFO depth (0.0 - 1.0)
                "feedback" - Feedback amount (-0.9 - 0.9)
                "dry_wet" - Dry/wet mix (0.0 - 1.0)
        """
        with self.lock:
            rate = params.get("rate", 1.0)
            depth = params.get("depth", 0.5)
            feedback = params.get("feedback", 0.3)
            dry_wet_val = params.get("dry_wet", 0.5)

            phase_inc = 2.0 * math.pi * rate / self.sample_rate

            for i in range(len(samples)):
                input_sample = float(samples[i])

                # LFO
                self.lfo_phase = (self.lfo_phase + phase_inc) % (2.0 * math.pi)
                lfo = math.sin(self.lfo_phase)

                # Apply feedback from previous sample's output
                stage_input = input_sample + self._feedback_state * feedback
                self._feedback_state = 0.0

                # Process through cascaded all-pass stages
                stage_output = stage_input
                for j in range(self.num_stages):
                    freq = self.base_freqs[j] * (1.0 + lfo * depth)
                    freq = max(20.0, min(freq, self.sample_rate * 0.45))

                    omega = 2.0 * math.pi * freq / self.sample_rate
                    tan_half = math.tan(omega / 2.0)
                    g = (tan_half - 1.0) / (tan_half + 1.0)

                    y = -g * stage_output + self.x1[j] + g * self.y1[j]
                    self.x1[j] = stage_output
                    self.y1[j] = y
                    stage_output = y

                # Store feedback for next sample
                self._feedback_state = stage_output

                # Dry/wet mix
                samples[i] = input_sample * (1.0 - dry_wet_val) + stage_output * dry_wet_val

    def reset(self) -> None:
        """Reset all filter state and LFO phase."""
        with self.lock:
            self.x1 = [0.0] * self.num_stages
            self.y1 = [0.0] * self.num_stages
            self.lfo_phase = 0.0
            self._feedback_state = 0.0
