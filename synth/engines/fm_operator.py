"""FM Operator - single FM synthesis operator with envelope."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


class FMOperator:
    """
    FM-X Compatible Operator with 8-stage envelopes and advanced modulation.

    Each operator supports:
    - 8-stage envelopes with loop points
    - Operator scaling (key/velocity sensitivity)
    - Multiple waveforms including formants
    - Advanced feedback and ring modulation
    - Individual LFO modulation
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize FM-X operator."""
        self.sample_rate = sample_rate

        # Oscillator parameters
        self.frequency_ratio = 1.0
        self.detune_cents = 0.0
        self.feedback_level = 0  # 0-7 levels
        self.waveform = "sine"
        self.phase = 0.0

        # FM-X 8-stage envelope (Level, Rate, Loop)
        self.envelope_levels = [0.0, 1.0, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0]  # 8 levels
        self.envelope_rates = [0.01, 0.3, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]  # 8 rates
        self.envelope_loop_start = -1  # -1 = no loop
        self.envelope_loop_end = -1
        self.envelope_phase = "idle"
        self.envelope_stage = 0
        self.envelope_value = 0.0
        self.envelope_time = 0.0

        # Operator scaling (FM-X style)
        self.key_scaling_depth = 0  # 0-7
        self.velocity_sensitivity = 0  # 0-7
        self.key_scaling_curve = "linear"  # linear, exp, log

        # Advanced modulation
        self.amplitude_mod = 1.0
        self.frequency_mod = 0.0
        self.phase_mod = 0.0

        # Feedback state (enhanced)
        self.feedback_sample = 0.0
        self.feedback_buffer = np.zeros(8, dtype=np.float32)  # Multi-tap feedback

        # Formant synthesis
        self.formant_enabled = False
        self.formant_data = []  # Spectral formant data

        # Ring modulation
        self.ring_mod_enabled = False
        self.ring_mod_operator = -1  # Operator to ring modulate with

        # LFO modulation
        self.lfo_depth = 0.0
        self.lfo_waveform = "sine"
        self.lfo_speed = 1.0
        self.lfo_phase = 0.0

    def set_parameters(self, params: dict[str, Any]):
        """Set FM-X operator parameters."""
        self.frequency_ratio = params.get("frequency_ratio", 1.0)
        self.detune_cents = params.get("detune_cents", 0.0)
        self.feedback_level = params.get("feedback_level", 0)
        self.waveform = params.get("waveform", "sine")

        # FM-X 8-stage envelope parameters
        if "envelope_levels" in params:
            self.envelope_levels = params["envelope_levels"][:8]  # Ensure 8 levels
        if "envelope_rates" in params:
            self.envelope_rates = params["envelope_rates"][:8]  # Ensure 8 rates

        self.envelope_loop_start = params.get("envelope_loop_start", -1)
        self.envelope_loop_end = params.get("envelope_loop_end", -1)

        # Operator scaling
        self.key_scaling_depth = params.get("key_scaling_depth", 0)
        self.velocity_sensitivity = params.get("velocity_sensitivity", 0)
        self.key_scaling_curve = params.get("key_scaling_curve", "linear")

        # Formant synthesis
        self.formant_enabled = params.get("formant_enabled", False)
        if "formant_data" in params:
            self.formant_data = params["formant_data"]

        # Ring modulation
        self.ring_mod_enabled = params.get("ring_mod_enabled", False)
        self.ring_mod_operator = params.get("ring_mod_operator", -1)

        # LFO parameters
        self.lfo_depth = params.get("lfo_depth", 0.0)
        self.lfo_waveform = params.get("lfo_waveform", "sine")
        self.lfo_speed = params.get("lfo_speed", 1.0)

    def note_on(self, velocity: int = 127):
        """Start FM-X 8-stage envelope."""
        self.envelope_phase = "active"
        self.envelope_stage = 0
        self.envelope_time = 0.0
        self.envelope_value = self.envelope_levels[0]

        # Apply velocity sensitivity
        if self.velocity_sensitivity > 0:
            velocity_scale = (velocity / 127.0) ** (1.0 / (8 - self.velocity_sensitivity))
            self.envelope_value *= velocity_scale

    def note_off(self):
        """Start envelope release phase."""
        # Jump to release stages (stages 6-7 in FM-X)
        if self.envelope_loop_start >= 0 and self.envelope_loop_end >= 0:
            # If looping, stop at current loop point
            self.envelope_stage = min(self.envelope_stage, self.envelope_loop_end)
        else:
            # Go to release stages
            self.envelope_stage = 6  # Release stage
        self.envelope_time = 0.0

    def update_envelope(self, dt: float):
        """Update FM-X 8-stage envelope."""
        if self.envelope_phase == "idle":
            self.envelope_value = 0.0
            return

        self.envelope_time += dt

        # Get current stage parameters
        current_level = self.envelope_levels[self.envelope_stage]
        next_level = self.envelope_levels[min(self.envelope_stage + 1, 7)]
        rate = self.envelope_rates[self.envelope_stage]

        # Handle zero rate (instant transition)
        if rate <= 0.001:
            self.envelope_value = next_level
            self._advance_envelope_stage()
            return

        # Calculate envelope progression
        if self.envelope_time >= rate:
            # Stage complete
            self.envelope_value = next_level
            self._advance_envelope_stage()
        else:
            # Interpolate between levels
            progress = self.envelope_time / rate
            if self.envelope_stage < 7:  # Not the last stage
                self.envelope_value = current_level + (next_level - current_level) * progress
            else:
                # Last stage holds or decays to zero
                self.envelope_value = current_level * (1.0 - progress)

    def _advance_envelope_stage(self):
        """Advance to next envelope stage."""
        if self.envelope_stage >= 7:
            # End of envelope
            self.envelope_phase = "idle"
            self.envelope_value = 0.0
            return

        self.envelope_stage += 1
        self.envelope_time = 0.0

        # Handle looping
        if (
            self.envelope_loop_start >= 0
            and self.envelope_loop_end >= 0
            and self.envelope_stage > self.envelope_loop_end
        ):
            # Loop back to start
            self.envelope_stage = self.envelope_loop_start

    def generate_sample(
        self,
        base_frequency: float,
        modulation_input: float = 0.0,
        ring_mod_input: float = 0.0,
    ) -> float:
        """
        Generate operator sample with FM-X features.

        Args:
            base_frequency: Base frequency for this operator
            modulation_input: Frequency modulation input from other operators
            ring_mod_input: Ring modulation input from paired operator

        Returns:
            Operator output sample
        """
        # Calculate modulated frequency
        detune_ratio = 2.0 ** (self.detune_cents / 1200.0)
        frequency = base_frequency * self.frequency_ratio * detune_ratio
        frequency += modulation_input

        # Apply LFO modulation to frequency
        if self.lfo_depth > 0.0:
            lfo_mod = self.lfo_depth * math.sin(self.lfo_phase)
            frequency *= 1.0 + lfo_mod * 0.1  # ±10% frequency modulation
            self.lfo_phase += 2.0 * math.pi * self.lfo_speed / self.sample_rate
            if self.lfo_phase > 2.0 * math.pi:
                self.lfo_phase -= 2.0 * math.pi

        # Update phase
        self.phase += 2.0 * math.pi * frequency / self.sample_rate
        if self.phase > 2.0 * math.pi:
            self.phase -= 2.0 * math.pi

        # Generate base waveform
        if self.waveform == "sine":
            output = math.sin(self.phase)
        elif self.waveform == "triangle":
            output = (
                2.0
                * abs(
                    2.0
                    * (
                        self.phase / (2.0 * math.pi)
                        - math.floor(self.phase / (2.0 * math.pi) + 0.5)
                    )
                )
                - 1.0
            )
        elif self.waveform == "sawtooth":
            output = 2.0 * (
                self.phase / (2.0 * math.pi) - math.floor(self.phase / (2.0 * math.pi) + 0.5)
            )
        elif self.waveform == "square":
            output = 1.0 if math.sin(self.phase) >= 0 else -1.0
        else:
            output = math.sin(self.phase)  # Default to sine

        # Apply formant synthesis if enabled
        if self.formant_enabled and self.formant_data:
            output = self._apply_formant_filter(output, self.formant_data)

        # Apply ring modulation if enabled
        if self.ring_mod_enabled and ring_mod_input != 0.0:
            output = output * ring_mod_input  # Ring modulation: A * B

        # Apply advanced feedback
        if self.feedback_level > 0:
            # Multi-tap feedback based on level (0-7)
            feedback_amount = self.feedback_level / 7.0

            # Mix current output with delayed feedback
            if len(self.feedback_buffer) > 0:
                # Use different tap based on feedback level
                tap_index = min(self.feedback_level - 1, len(self.feedback_buffer) - 1)
                delayed_feedback = self.feedback_buffer[tap_index]

                # Apply feedback to phase for FM-style feedback
                feedback_phase_mod = delayed_feedback * feedback_amount * 0.5
                output = math.sin(self.phase + feedback_phase_mod)

                # Update feedback buffer (shift)
                self.feedback_buffer = np.roll(self.feedback_buffer, 1)
                self.feedback_buffer[0] = output
            else:
                # Initialize feedback buffer
                self.feedback_buffer = np.zeros(min(self.feedback_level, 8), dtype=np.float32)

            self.feedback_sample = output

        # Apply envelope and amplitude modulation
        output *= self.envelope_value * self.amplitude_mod

        return output

    def _apply_formant_filter(self, input_sample: float, formant_data: list) -> float:
        """
        Apply formant filtering for vocal synthesis.

        Args:
            input_sample: Input audio sample
            formant_data: Formant filter parameters [freq, bandwidth, gain]

        Returns:
            Filtered output sample
        """
        if not formant_data or len(formant_data) < 3:
            return input_sample

        # Simple formant filter implementation
        # In a full implementation, this would be a proper IIR filter
        formant_freq = formant_data[0]  # Formant frequency in Hz
        bandwidth = formant_data[1]  # Bandwidth in Hz
        gain = formant_data[2]  # Gain multiplier

        # Simple resonant peak filter approximation
        # This is a simplified version - real formant synthesis would use
        # more sophisticated digital filter design
        resonance = bandwidth / (bandwidth + formant_freq * 0.1)
        filter_output = input_sample * (1.0 + resonance * gain)

        return filter_output

    def is_active(self) -> bool:
        """Check if operator is still active."""
        return self.envelope_phase != "idle"

    def reset(self):
        """Reset operator state."""
        self.phase = 0.0
        self.envelope_phase = "idle"
        self.envelope_value = 0.0
        self.envelope_time = 0.0
        self.feedback_sample = 0.0


