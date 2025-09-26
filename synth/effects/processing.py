"""
XG Effects Audio Processing

This module handles the core audio processing pipeline for XG effects,
including effect routing, mixing, and real-time audio processing.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import numpy as np

from .constants import NUM_CHANNELS
from .state import EffectStateManager


class XGAudioProcessor:
    """
    Handles audio processing for XG effects including routing and mixing.
    """

    def __init__(self, state_manager: EffectStateManager, sample_rate: int = 44100):
        """Initialize the audio processor"""
        self.state_manager = state_manager
        self.sample_rate = sample_rate

        # Internal effect state buffers
        self._reverb_state = self._create_reverb_state()
        self._chorus_state = self._create_chorus_state()

    def _create_reverb_state(self) -> Dict[str, Any]:
        """Create initial reverb state"""
        return {
            "allpass_buffers": [np.zeros(441) for _ in range(4)],
            "allpass_indices": [0] * 4,
            "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
            "comb_indices": [0] * 4,
            "early_reflection_buffer": np.zeros(441),
            "early_reflection_index": 0,
            "late_reflection_buffer": np.zeros(441 * 10),
            "late_reflection_index": 0
        }

    def _create_chorus_state(self) -> Dict[str, Any]:
        """Create initial chorus state"""
        return {
            "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms delays
            "lfo_phases": [0.0, 0.0],
            "lfo_rates": [1.0, 0.5],
            "lfo_depths": [0.5, 0.3],
            "write_indices": [0, 0],
            "feedback_buffers": [0.0, 0.0]
        }

    def process_audio(self, input_samples: List[List[Tuple[float, float]]],
                     num_samples: int) -> List[List[Tuple[float, float]]]:
        """
        Process audio with XG effects applied.

        Args:
            input_samples: List of channels, each containing stereo sample tuples
            num_samples: Number of samples to process

        Returns:
            Processed audio samples
        """
        if len(input_samples) != NUM_CHANNELS:
            raise ValueError(f"Expected {NUM_CHANNELS} channels, got {len(input_samples)}")

        # Validate input samples
        for i, channel_samples in enumerate(input_samples):
            if len(channel_samples) != num_samples:
                raise ValueError(f"Channel {i}: expected {num_samples} samples, got {len(channel_samples)}")

        # Get current state (thread-safe)
        state = self.state_manager.get_current_state()

        # Initialize output
        output_channels = [[(0.0, 0.0) for _ in range(num_samples)] for _ in range(NUM_CHANNELS)]

        # Get active channels
        active_channels = self.state_manager.get_active_channels(state)

        # System input accumulation
        system_input_left = 0.0
        system_input_right = 0.0

        # Process insertion effects for each channel
        insertion_outputs = [[] for _ in range(NUM_CHANNELS)]

        for i in range(NUM_CHANNELS):
            if i not in active_channels:
                # Inactive channels output silence
                insertion_outputs[i] = [(0.0, 0.0) for _ in range(num_samples)]
                continue

            channel_samples = input_samples[i]
            ch_params = state["channel_params"][i]

            # Process each sample in the channel
            channel_output = []
            for j in range(num_samples):
                left_in, right_in = channel_samples[j]

                # Apply insertion effect
                insertion_effect = ch_params["insertion_effect"]
                insertion_send = ch_params["insertion_send"]

                if (insertion_effect["enabled"] and
                    insertion_send > 0 and
                    not insertion_effect["bypass"]):

                    # Process through insertion effect
                    insertion_left, insertion_right = self._process_insertion_effect(
                        left_in, right_in, insertion_effect,
                        self.state_manager.channel_effect_states[i], state
                    )
                    insertion_left *= insertion_send
                    insertion_right *= insertion_send
                else:
                    insertion_left, insertion_right = 0.0, 0.0

                # Store for later mixing
                channel_output.append((insertion_left, insertion_right))

                # Accumulate for system effects
                reverb_send = ch_params["reverb_send"]
                system_input_left += left_in * (1 - insertion_send) * reverb_send
                system_input_right += right_in * (1 - insertion_send) * reverb_send

            insertion_outputs[i] = channel_output

        # Process system effects
        system_output = (0.0, 0.0)
        if (not state["global_effect_params"].get("bypass_all", False) and
            any(active_channels)):
            # Apply effect routing
            system_output = self._process_effect_routing(
                system_input_left, system_input_right, state
            )

        # Mix channels and apply final processing
        for i in range(NUM_CHANNELS):
            if i not in active_channels:
                # Inactive channels remain silent
                output_channels[i] = [(0.0, 0.0) for _ in range(num_samples)]
                continue

            # Get insertion effect output for this channel
            channel_insertion_output = insertion_outputs[i]
            ch_params = state["channel_params"][i]

            # Get system effect contribution
            reverb_send = ch_params["reverb_send"]

            # Apply volume, expression, and pan
            volume = ch_params["volume"]
            expression = ch_params["expression"]
            channel_volume = volume * expression

            pan = ch_params["pan"]
            left_volume = channel_volume * (1.0 - pan)
            right_volume = channel_volume * pan

            # Mix and apply levels
            for j in range(num_samples):
                insertion_left, insertion_right = channel_insertion_output[j]
                system_contrib_left = system_output[0] * reverb_send
                system_contrib_right = system_output[1] * reverb_send

                # Combine insertion and system effects
                left_out = (insertion_left + system_contrib_left) * left_volume
                right_out = (insertion_right + system_contrib_right) * right_volume

                # Apply clipping
                left_out = max(-1.0, min(1.0, left_out))
                right_out = max(-1.0, min(1.0, right_out))

                output_channels[i][j] = (left_out, right_out)

        # Apply master level
        master_level = state["global_effect_params"].get("master_level", 0.8)
        if master_level != 1.0:
            for i in range(NUM_CHANNELS):
                for j in range(num_samples):
                    left_out, right_out = output_channels[i][j]
                    output_channels[i][j] = (left_out * master_level, right_out * master_level)

        # Apply state updates if pending
        if self.state_manager.state_update_pending:
            self.state_manager.apply_temp_state()

        return output_channels

    def process_stereo_audio_vectorized(self, input_samples: np.ndarray) -> np.ndarray:
        """
        Wrapper method to provide vectorized interface for VectorizedEffectManager.

        Args:
            input_samples: Input stereo audio samples as NumPy array (N x 2)

        Returns:
            Processed stereo audio samples as NumPy array (N x 2)
        """
        num_samples = input_samples.shape[0]

        # Convert numpy array to the expected list format for process_audio
        channels_input = [
            [(float(input_samples[i, 0]), float(input_samples[i, 1])) for i in range(num_samples)]
        ]

        # Call the main processing method
        processed_channels = self.process_audio(channels_input, num_samples)

        # Convert back to numpy array format
        if len(processed_channels) > 0 and len(processed_channels[0]) == num_samples:
            # Extract the first channel (the processed one)
            processed = processed_channels[0]
            # Convert list of tuples to numpy array
            left_channel = np.array([sample[0] for sample in processed], dtype=np.float32)
            right_channel = np.array([sample[1] for sample in processed], dtype=np.float32)
            result = np.column_stack((left_channel, right_channel))
            return result
        else:
            # Return input unchanged if processing failed
            return input_samples

    def _process_effect_routing(self, left_in: float, right_in: float,
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process effect routing according to XG specifications.

        Args:
            left_in: Left input sample
            right_in: Right input sample
            state: Current effect state

        Returns:
            Processed stereo output
        """
        left_out, right_out = left_in, right_in
        routing_params = state["routing_params"]

        # Get effect order
        effect_order = routing_params.get("system_effect_order", [0, 1, 2])

        # Process effects in order
        for effect_index in effect_order:
            if effect_index == 0:  # Reverb
                reverb_params = state["reverb_params"]
                reverb_amount = 1.0

                # Check for reverb-to-chorus routing
                if (routing_params.get("reverb_to_chorus", 0.0) > 0 and
                    1 in effect_order):
                    reverb_amount = 1.0 - routing_params["reverb_to_chorus"]

                # Process reverb
                reverb_left, reverb_right = self._process_reverb(
                    left_in * reverb_amount, right_in * reverb_amount,
                    reverb_params, self._reverb_state
                )

                # Mix with original
                left_out += reverb_left * reverb_params.get("level", 0.6)
                right_out += reverb_right * reverb_params.get("level", 0.6)

                # Route to next effect if configured
                if (routing_params.get("reverb_to_chorus", 0.0) > 0 and
                    1 in effect_order):
                    left_in = reverb_left * routing_params["reverb_to_chorus"]
                    right_in = reverb_right * routing_params["reverb_to_chorus"]
                else:
                    left_in, right_in = left_out, right_out

            elif effect_index == 1:  # Chorus
                chorus_params = state["chorus_params"]
                chorus_amount = 1.0

                # Check for chorus-to-variation routing
                if (routing_params.get("chorus_to_variation", 0.0) > 0 and
                    2 in effect_order):
                    chorus_amount = 1.0 - routing_params["chorus_to_variation"]

                # Process chorus
                chorus_left, chorus_right = self._process_chorus(
                    left_in * chorus_amount, right_in * chorus_amount,
                    chorus_params, self._chorus_state
                )

                # Mix with original
                left_out += chorus_left * chorus_params.get("level", 0.4)
                right_out += chorus_right * chorus_params.get("level", 0.4)

                # Route to next effect if configured
                if (routing_params.get("chorus_to_variation", 0.0) > 0 and
                    2 in effect_order):
                    left_in = chorus_left * routing_params["chorus_to_variation"]
                    right_in = chorus_right * routing_params["chorus_to_variation"]
                else:
                    left_in, right_in = left_out, right_out

            elif effect_index == 2:  # Variation
                variation_params = state["variation_params"]

                # Process variation effect
                variation_left, variation_right = self._process_variation_effect(
                    left_in, right_in, variation_params, state
                )

                # Mix with original
                left_out += variation_left * variation_params.get("level", 0.5)
                right_out += variation_right * variation_params.get("level", 0.5)

        # Apply equalizer to final output
        equalizer_params = state["equalizer_params"]
        left_out, right_out = self._apply_equalizer(left_out, right_out, equalizer_params)

        # Apply stereo width
        stereo_width = state["global_effect_params"].get("stereo_width", 0.5)
        if stereo_width < 1.0:
            center = (left_out + right_out) / 2.0
            left_out = center + (left_out - center) * stereo_width
            right_out = center + (right_out - center) * stereo_width

        return (left_out, right_out)

    def _apply_equalizer(self, left: float, right: float,
                        equalizer_params: Dict[str, float]) -> Tuple[float, float]:
        """
        Apply 3-band equalizer to audio samples.

        Args:
            left: Left input sample
            right: Right input sample
            equalizer_params: Equalizer parameters

        Returns:
            Equalized stereo output
        """
        # Convert dB to linear gain
        low_gain = 10 ** (equalizer_params.get("low_gain", 0.0) / 20.0)
        mid_gain = 10 ** (equalizer_params.get("mid_gain", 0.0) / 20.0)
        high_gain = 10 ** (equalizer_params.get("high_gain", 0.0) / 20.0)

        mid_freq = equalizer_params.get("mid_freq", 1000.0)
        q_factor = equalizer_params.get("q_factor", 1.0)

        # Calculate filter coefficients (simplified implementation)
        w0 = 2 * math.pi * mid_freq / self.sample_rate
        alpha = math.sin(w0) / (2 * q_factor)

        # Bandpass filter coefficients
        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha

        # Apply frequency-specific gains (simplified)
        # In a full implementation, this would use proper IIR filtering
        mid_left = left * (mid_gain - 1.0)
        mid_right = right * (mid_gain - 1.0)

        return (
            left * low_gain + mid_left + right * high_gain,
            right * low_gain + mid_right + right * high_gain
        )

    def _process_reverb(self, left: float, right: float,
                       reverb_params: Dict[str, float],
                       state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process reverb using Schroeder algorithm.

        Args:
            left: Left input sample
            right: Right input sample
            reverb_params: Reverb parameters
            state: Reverb state

        Returns:
            Reverberated stereo output
        """
        # Extract parameters
        reverb_type = reverb_params.get("type", 0)
        time = reverb_params.get("time", 2.5)
        level = reverb_params.get("level", 0.6)
        pre_delay = reverb_params.get("pre_delay", 20.0)
        hf_damping = reverb_params.get("hf_damping", 0.5)
        density = reverb_params.get("density", 0.8)
        early_level = reverb_params.get("early_level", 0.7)
        tail_level = reverb_params.get("tail_level", 0.9)

        # Schroeder reverb algorithm
        allpass_buffers = state["allpass_buffers"]
        allpass_indices = state["allpass_indices"]
        comb_buffers = state["comb_buffers"]
        comb_indices = state["comb_indices"]
        early_reflection_buffer = state["early_reflection_buffer"]
        early_reflection_index = state["early_reflection_index"]
        late_reflection_buffer = state["late_reflection_buffer"]
        late_reflection_index = state["late_reflection_index"]

        # Input sample (mono for reverb)
        input_sample = (left + right) / 2.0

        # Pre-delay
        pre_delay_samples = int(pre_delay * self.sample_rate / 1000.0)
        if pre_delay_samples >= len(early_reflection_buffer):
            pre_delay_samples = len(early_reflection_buffer) - 1

        # Write to pre-delay buffer
        early_reflection_buffer[early_reflection_index] = input_sample
        early_reflection_index = (early_reflection_index + 1) % len(early_reflection_buffer)

        # Read from pre-delay buffer
        pre_delay_index = (early_reflection_index - pre_delay_samples) % len(early_reflection_buffer)
        pre_delay_sample = early_reflection_buffer[int(pre_delay_index)]

        # Early reflections
        early_reflections = pre_delay_sample * early_level

        # Comb filter density
        num_comb_filters = 4 + int(density * 4)
        comb_input = early_reflections

        # Process through comb filters
        for i in range(min(num_comb_filters, len(comb_buffers))):
            delay_length = int(time * self.sample_rate * (i + 1) / 8.0)
            if delay_length >= len(comb_buffers[i]):
                delay_length = len(comb_buffers[i]) - 1

            # Read from delay buffer
            read_index = (comb_indices[i] - delay_length) % len(comb_buffers[i])
            comb_sample = comb_buffers[i][int(read_index)]

            # Calculate feedback
            feedback = 0.7 + (i * 0.05)

            # Write to delay buffer with feedback and damping
            comb_buffers[i][comb_indices[i]] = comb_input + comb_sample * feedback * (1.0 - hf_damping)
            comb_indices[i] = (comb_indices[i] + 1) % len(comb_buffers[i])

            # Add to output
            comb_input += comb_sample * tail_level

        # Process through allpass filters for diffusion
        allpass_output = comb_input
        for i in range(len(allpass_buffers)):
            delay_length = int(time * self.sample_rate * (i + 1) / 16.0)
            if delay_length >= len(allpass_buffers[i]):
                delay_length = len(allpass_buffers[i]) - 1

            # Read from delay buffer
            read_index = (allpass_indices[i] - delay_length) % len(allpass_buffers[i])
            allpass_sample = allpass_buffers[i][int(read_index)]

            # Allpass filter
            g = 0.7  # Damping coefficient
            allpass_buffers[i][allpass_indices[i]] = allpass_output
            allpass_indices[i] = (allpass_indices[i] + 1) % len(allpass_buffers[i])

            # Apply allpass formula
            allpass_output = -g * allpass_output + allpass_sample + g * allpass_sample

        # Update state
        state["allpass_indices"] = allpass_indices
        state["comb_indices"] = comb_indices
        state["early_reflection_index"] = early_reflection_index
        state["late_reflection_index"] = late_reflection_index

        # Return stereo output
        return (allpass_output * level * 0.7, allpass_output * level * 0.7)

    def _process_chorus(self, left: float, right: float,
                       chorus_params: Dict[str, float],
                       state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process chorus effect with dual LFO modulation.

        Args:
            left: Left input sample
            right: Right input sample
            chorus_params: Chorus parameters
            state: Chorus state

        Returns:
            Chorused stereo output
        """
        # Extract parameters
        chorus_type = chorus_params.get("type", 0)
        rate = chorus_params.get("rate", 1.0)
        depth = chorus_params.get("depth", 0.5)
        feedback = chorus_params.get("feedback", 0.3)
        level = chorus_params.get("level", 0.4)
        delay = chorus_params.get("delay", 0.0)
        output = chorus_params.get("output", 0.8)
        cross_feedback = chorus_params.get("cross_feedback", 0.2)

        # Chorus state
        delay_lines = state["delay_lines"]
        lfo_phases = state["lfo_phases"]
        lfo_rates = state["lfo_rates"]
        lfo_depths = state["lfo_depths"]
        write_indices = state["write_indices"]
        feedback_buffers = state["feedback_buffers"]

        # Process left channel
        left_input = left

        # Update LFO phase
        lfo_phases[0] = (lfo_phases[0] + lfo_rates[0] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(delay * self.sample_rate / 1000.0)
        modulation = int(lfo_depths[0] * depth * self.sample_rate / 1000.0 * (1 + math.sin(lfo_phases[0])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(delay_lines[0]):
            total_delay = len(delay_lines[0]) - 1

        # Read from delay buffer
        read_index = (write_indices[0] - total_delay) % len(delay_lines[0])
        delayed_sample = delay_lines[0][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * feedback + feedback_buffers[0] * cross_feedback
        delay_lines[0][write_indices[0]] = left_input + feedback_sample

        # Update write index
        write_indices[0] = (write_indices[0] + 1) % len(delay_lines[0])
        feedback_buffers[0] = feedback_sample

        # Process right channel
        right_input = right

        # Update LFO phase
        lfo_phases[1] = (lfo_phases[1] + lfo_rates[1] * 2 * math.pi / self.sample_rate) % (2 * math.pi)

        # Calculate modulated delay
        base_delay_samples = int(delay * self.sample_rate / 1000.0)
        modulation = int(lfo_depths[1] * depth * self.sample_rate / 1000.0 * (1 + math.sin(lfo_phases[1])) / 2)
        total_delay = base_delay_samples + modulation

        if total_delay >= len(delay_lines[1]):
            total_delay = len(delay_lines[1]) - 1

        # Read from delay buffer
        read_index = (write_indices[1] - total_delay) % len(delay_lines[1])
        delayed_sample = delay_lines[1][int(read_index)]

        # Apply feedback
        feedback_sample = delayed_sample * feedback + feedback_buffers[1] * cross_feedback
        delay_lines[1][write_indices[1]] = right_input + feedback_sample

        # Update write index
        write_indices[1] = (write_indices[1] + 1) % len(delay_lines[1])
        feedback_buffers[1] = feedback_sample

        # Update state
        state["lfo_phases"] = lfo_phases
        state["write_indices"] = write_indices
        state["feedback_buffers"] = feedback_buffers

        # Mix original and chorused signals
        return (
            left * (1 - output) + delayed_sample * output * level,
            right * (1 - output) + delayed_sample * output * level
        )

    def _process_variation_effect(self, left: float, right: float,
                                variation_params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process variation effect based on type.

        Args:
            left: Left input sample
            right: Right input sample
            variation_params: Variation effect parameters
            state: System state

        Returns:
            Processed stereo output
        """
        effect_type = variation_params.get("type", 0)
        bypass = variation_params.get("bypass", False)

        # Check bypass
        if bypass:
            return (left, right)

        # Route to appropriate effect handler based on type
        if effect_type == 0:
            return self._process_delay_effect(left, right, variation_params, state)
        elif effect_type == 1:
            return self._process_dual_delay_effect(left, right, variation_params, state)
        elif effect_type == 2:
            return self._process_echo_effect(left, right, variation_params, state)
        elif effect_type == 3:
            return self._process_pan_delay_effect(left, right, variation_params, state)
        elif effect_type == 4:
            return self._process_cross_delay_effect(left, right, variation_params, state)
        elif effect_type == 5:
            return self._process_multi_tap_effect(left, right, variation_params, state)
        elif effect_type == 6:
            return self._process_reverse_delay_effect(left, right, variation_params, state)
        elif effect_type == 7:
            return self._process_tremolo_effect(left, right, variation_params, state)
        elif effect_type == 8:
            return self._process_auto_pan_effect(left, right, variation_params, state)
        elif effect_type == 9:
            return self._process_phaser_variation_effect(left, right, variation_params, state)
        elif effect_type == 10:
            return self._process_flanger_variation_effect(left, right, variation_params, state)
        elif effect_type == 11:
            return self._process_auto_wah_effect(left, right, variation_params, state)
        elif effect_type == 12:
            return self._process_ring_mod_effect(left, right, variation_params, state)
        elif effect_type == 13:
            return self._process_pitch_shifter_effect(left, right, variation_params, state)
        elif effect_type == 14:
            return self._process_distortion_variation_effect(left, right, variation_params, state)
        elif effect_type == 15:
            return self._process_overdrive_variation_effect(left, right, variation_params, state)
        elif effect_type == 16:
            return self._process_compressor_variation_effect(left, right, variation_params, state)
        elif effect_type == 17:
            return self._process_limiter_effect(left, right, variation_params, state)
        elif effect_type == 18:
            return self._process_gate_variation_effect(left, right, variation_params, state)
        elif effect_type == 19:
            return self._process_expander_effect(left, right, variation_params, state)
        elif effect_type == 20:
            return self._process_rotary_speaker_variation_effect(left, right, variation_params, state)
        elif effect_type == 21:
            return self._process_leslie_variation_effect(left, right, variation_params, state)
        elif effect_type == 22:
            return self._process_vibrato_effect(left, right, variation_params, state)
        elif effect_type == 23:
            return self._process_acoustic_simulator_effect(left, right, variation_params, state)
        elif effect_type == 24:
            return self._process_guitar_amp_sim_variation_effect(left, right, variation_params, state)
        elif effect_type == 25:
            return self._process_enhancer_variation_effect(left, right, variation_params, state)
        elif effect_type == 26:
            return self._process_slicer_variation_effect(left, right, variation_params, state)
        elif effect_type == 27:
            return self._process_step_phaser_effect(left, right, variation_params, state)
        elif effect_type == 28:
            return self._process_step_flanger_effect(left, right, variation_params, state)
        elif effect_type == 29:
            return self._process_step_tremolo_effect(left, right, variation_params, state)
        elif effect_type == 30:
            return self._process_step_pan_effect(left, right, variation_params, state)
        elif effect_type == 31:
            return self._process_step_filter_effect(left, right, variation_params, state)
        elif effect_type == 32:
            return self._process_auto_filter_effect(left, right, variation_params, state)
        elif effect_type == 33:
            return self._process_vocoder_variation_effect(left, right, variation_params, state)
        elif effect_type == 34:
            return self._process_talk_wah_variation_effect(left, right, variation_params, state)
        elif effect_type == 35:
            return self._process_harmonizer_variation_effect(left, right, variation_params, state)
        elif effect_type == 36:
            return self._process_octave_variation_effect(left, right, variation_params, state)
        elif effect_type == 37:
            return self._process_detune_variation_effect(left, right, variation_params, state)
        elif effect_type == 38:
            return self._process_chorus_reverb_effect(left, right, variation_params, state)
        elif effect_type == 39:
            return self._process_stereo_imager_effect(left, right, variation_params, state)
        elif effect_type == 40:
            return self._process_ambience_effect(left, right, variation_params, state)
        elif effect_type == 41:
            return self._process_doubler_effect(left, right, variation_params, state)
        elif effect_type == 42:
            return self._process_enhancer_reverb_effect(left, right, variation_params, state)
        elif effect_type == 43:
            return self._process_spectral_effect(left, right, variation_params, state)
        elif effect_type == 44:
            return self._process_resonator_effect(left, right, variation_params, state)
        elif effect_type == 45:
            return self._process_degrader_effect(left, right, variation_params, state)
        elif effect_type == 46:
            return self._process_vinyl_effect(left, right, variation_params, state)
        elif effect_type == 47:
            return self._process_looper_effect(left, right, variation_params, state)
        elif effect_type == 48:
            return self._process_step_delay_effect(left, right, variation_params, state)
        elif effect_type == 49:
            return self._process_step_echo_effect(left, right, variation_params, state)
        elif effect_type == 50:
            return self._process_step_pan_delay_effect(left, right, variation_params, state)
        elif effect_type == 51:
            return self._process_step_cross_delay_effect(left, right, variation_params, state)
        elif effect_type == 52:
            return self._process_step_multi_tap_effect(left, right, variation_params, state)
        elif effect_type == 53:
            return self._process_step_reverse_delay_effect(left, right, variation_params, state)
        elif effect_type == 54:
            return self._process_step_ring_mod_effect(left, right, variation_params, state)
        elif effect_type == 55:
            return self._process_step_pitch_shifter_effect(left, right, variation_params, state)
        elif effect_type == 56:
            return self._process_step_distortion_effect(left, right, variation_params, state)
        elif effect_type == 57:
            return self._process_step_overdrive_effect(left, right, variation_params, state)
        elif effect_type == 58:
            return self._process_step_compressor_effect(left, right, variation_params, state)
        elif effect_type == 59:
            return self._process_step_limiter_effect(left, right, variation_params, state)
        elif effect_type == 60:
            return self._process_step_gate_effect(left, right, variation_params, state)
        elif effect_type == 61:
            return self._process_step_expander_effect(left, right, variation_params, state)
        elif effect_type == 62:
            return self._process_step_rotary_speaker_effect(left, right, variation_params, state)

        # Default: return original signal
        return (left, right)

    def _process_insertion_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any],
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Process insertion effect based on type.

        Args:
            left: Left input sample
            right: Right input sample
            params: Insertion effect parameters
            state: Channel effect state
            system_state: System state

        Returns:
            Processed stereo output
        """
        effect_type = params.get("type", 0)
        bypass = params.get("bypass", False)

        # Check bypass
        if bypass:
            return (left, right)

        # Route to appropriate effect handler
        if effect_type == 1:
            return self._process_distortion_effect(left, right, params, state, system_state)
        elif effect_type == 2:
            return self._process_overdrive_effect(left, right, params, state, system_state)
        elif effect_type == 3:
            return self._process_compressor_effect(left, right, params, state, system_state)
        elif effect_type == 4:
            return self._process_gate_effect(left, right, params, state, system_state)
        elif effect_type == 5:
            return self._process_envelope_filter_effect(left, right, params, state, system_state)
        elif effect_type == 6:
            return self._process_guitar_amp_sim_effect(left, right, params, state, system_state)
        elif effect_type == 7:
            return self._process_rotary_speaker_effect(left, right, params, state, system_state)
        elif effect_type == 8:
            return self._process_leslie_effect(left, right, params, state, system_state)
        elif effect_type == 9:
            return self._process_enhancer_effect(left, right, params, state, system_state)
        elif effect_type == 10:
            return self._process_slicer_effect(left, right, params, state, system_state)
        elif effect_type == 11:
            return self._process_vocoder_effect(left, right, params, state, system_state)
        elif effect_type == 12:
            return self._process_talk_wah_effect(left, right, params, state, system_state)
        elif effect_type == 13:
            return self._process_harmonizer_effect(left, right, params, state, system_state)
        elif effect_type == 14:
            return self._process_octave_effect(left, right, params, state, system_state)
        elif effect_type == 15:
            return self._process_detune_effect(left, right, params, state, system_state)
        elif effect_type == 16:
            return self._process_phaser_effect(left, right, params, state, system_state)
        elif effect_type == 17:
            return self._process_flanger_effect(left, right, params, state, system_state)
        elif effect_type == 18:
            return self._process_wah_wah_effect(left, right, params, state, system_state)

        # Default: return original signal
        return (left, right)

    # --- Variation Effect Implementations ---

    def _process_delay_effect(self, left: float, right: float,
                             params: Dict[str, float],
                             state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Delay effect"""
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 ms
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        stereo = params.get("parameter4", 0.5)

        if "delay" not in state:
            buffer_size = int(self.sample_rate)
            state["delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }

        delay_samples = int(time * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["delay"]["buffer"]
        pos = state["delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["delay"]["pos"] = (pos + 1) % len(buffer)
        state["delay"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        left_out = output * (1 - stereo)
        right_out = output * stereo

        return (left_out, right_out)

    def _process_dual_delay_effect(self, left: float, right: float,
                                  params: Dict[str, float],
                                  state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Dual Delay effect"""
        time1 = params.get("parameter1", 0.3) * 1000
        time2 = params.get("parameter2", 0.6) * 1000
        feedback = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        if "dual_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["dual_delay"] = {
                "buffer1": [0.0] * buffer_size,
                "buffer2": [0.0] * buffer_size,
                "pos1": 0,
                "pos2": 0,
                "feedback_buffer": 0.0
            }

        delay_samples1 = int(time1 * self.sample_rate / 1000.0)
        delay_samples2 = int(time2 * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer1 = state["dual_delay"]["buffer1"]
        buffer2 = state["dual_delay"]["buffer2"]
        pos1 = state["dual_delay"]["pos1"]
        pos2 = state["dual_delay"]["pos2"]

        delay_pos1 = (pos1 - delay_samples1) % len(buffer1)
        delay_pos2 = (pos2 - delay_samples2) % len(buffer2)

        delayed_sample1 = buffer1[int(delay_pos1)]
        delayed_sample2 = buffer2[int(delay_pos2)]

        feedback_sample = state["dual_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer1[pos1] = processed_sample
        buffer2[pos2] = processed_sample
        state["dual_delay"]["pos1"] = (pos1 + 1) % len(buffer1)
        state["dual_delay"]["pos2"] = (pos2 + 1) % len(buffer2)
        state["dual_delay"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + (delayed_sample1 + delayed_sample2) * level * 0.5
        return (output, output)

    def _process_echo_effect(self, left: float, right: float,
                            params: Dict[str, float],
                            state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Echo effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        decay = params.get("parameter4", 0.8)

        if "echo" not in state:
            buffer_size = int(self.sample_rate)
            state["echo"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }

        delay_samples = int(time * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["echo"]["buffer"]
        pos = state["echo"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["echo"]["feedback_buffer"] * feedback * decay
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["echo"]["pos"] = (pos + 1) % len(buffer)
        state["echo"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        return (output, output)

    def _process_pan_delay_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Pan Delay effect"""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        rate = params.get("parameter4", 0.5) * 5.0

        if "pan_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["pan_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "lfo_phase": 0.0
            }

        lfo_phase = state["pan_delay"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        delay_samples = int(time * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["pan_delay"]["buffer"]
        pos = state["pan_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["pan_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["pan_delay"]["pos"] = (pos + 1) % len(buffer)
        state["pan_delay"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        pan = math.sin(lfo_phase) * 0.5 + 0.5
        left_out = output * (1 - pan)
        right_out = output * pan

        state["pan_delay"]["lfo_phase"] = lfo_phase
        return (left_out, right_out)

    def _process_cross_delay_effect(self, left: float, right: float,
                                   params: Dict[str, float],
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Cross Delay effect"""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        cross = params.get("parameter4", 0.5)

        if "cross_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["cross_delay"] = {
                "left_buffer": [0.0] * buffer_size,
                "right_buffer": [0.0] * buffer_size,
                "left_pos": 0,
                "right_pos": 0,
                "left_feedback": 0.0,
                "right_feedback": 0.0
            }

        delay_samples = int(time * self.sample_rate / 1000.0)

        buffer_left = state["cross_delay"]["left_buffer"]
        buffer_right = state["cross_delay"]["right_buffer"]
        pos_left = state["cross_delay"]["left_pos"]
        pos_right = state["cross_delay"]["right_pos"]

        delay_pos_left = (pos_left - delay_samples) % len(buffer_left)
        delay_pos_right = (pos_right - delay_samples) % len(buffer_right)

        delayed_left = buffer_left[int(delay_pos_left)]
        delayed_right = buffer_right[int(delay_pos_right)]

        feedback_left = state["cross_delay"]["left_feedback"] * feedback * (1 - cross)
        feedback_right = state["cross_delay"]["right_feedback"] * feedback * (1 - cross)
        cross_left_feedback = state["cross_delay"]["right_feedback"] * feedback * cross
        cross_right_feedback = state["cross_delay"]["left_feedback"] * feedback * cross

        processed_left = left + feedback_left + cross_left_feedback
        processed_right = right + feedback_right + cross_right_feedback

        buffer_left[pos_left] = processed_left
        buffer_right[pos_right] = processed_right
        state["cross_delay"]["left_pos"] = (pos_left + 1) % len(buffer_left)
        state["cross_delay"]["right_pos"] = (pos_right + 1) % len(buffer_right)
        state["cross_delay"]["left_feedback"] = processed_left
        state["cross_delay"]["right_feedback"] = processed_right

        left_out = left * (1 - level) + delayed_left * level
        right_out = right * (1 - level) + delayed_right * level

        return (left_out, right_out)

    def _process_multi_tap_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Multi Tap effect"""
        taps = int(params.get("parameter1", 0.5) * 10) + 1
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        spacing = params.get("parameter4", 0.5)

        if "multi_tap" not in state:
            buffer_size = int(self.sample_rate)
            state["multi_tap"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }

        input_sample = (left + right) / 2.0
        buffer = state["multi_tap"]["buffer"]
        pos = state["multi_tap"]["pos"]

        delayed_sum = 0.0
        for i in range(taps):
            delay_time = (i * spacing * 500)
            delay_samples = int(delay_time * self.sample_rate / 1000.0)
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sum += buffer[int(delay_pos)]

        delayed_sum /= taps

        feedback_sample = state["multi_tap"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["multi_tap"]["pos"] = (pos + 1) % len(buffer)
        state["multi_tap"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sum * level
        return (output, output)

    def _process_reverse_delay_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Reverse Delay effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        reverse = params.get("parameter4", 0.5)

        if "reverse_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["reverse_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "reverse_buffer": [0.0] * buffer_size
            }

        delay_samples = int(time * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["reverse_delay"]["buffer"]
        pos = state["reverse_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["reverse_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["reverse_delay"]["pos"] = (pos + 1) % len(buffer)
        state["reverse_delay"]["feedback_buffer"] = processed_sample

        reverse_buffer = state["reverse_delay"]["reverse_buffer"]
        reverse_pos = (pos + delay_samples) % len(reverse_buffer)
        reverse_sample = reverse_buffer[int(reverse_pos)]

        reverse_buffer[pos] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level * (1 - reverse) + reverse_sample * level * reverse
        return (output, output)

    def _process_tremolo_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Tremolo effect"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        if "tremolo" not in state:
            state["tremolo"] = {"lfo_phase": 0.0}

        lfo_phase = state["tremolo"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        output_left = left * lfo_value
        output_right = right * lfo_value

        state["tremolo"]["lfo_phase"] = lfo_phase
        return (output_left, output_right)

    def _process_auto_pan_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Auto Pan effect"""
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        if "auto_pan" not in state:
            state["auto_pan"] = {"lfo_phase": 0.0}

        lfo_phase = state["auto_pan"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        pan = lfo_value * depth * 0.5 + 0.5
        left_out = left * (1 - pan) + right * pan
        right_out = right * pan + left * (1 - pan)

        state["auto_pan"]["lfo_phase"] = lfo_phase
        return (left_out, right_out)

    def _process_phaser_variation_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Phaser effect (variation)"""
        frequency = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)

        if "phaser_variation" not in state:
            state["phaser_variation"] = {
                "lfo_phase": 0.0,
                "allpass_filters": [0.0] * 4
            }

        lfo_phase = state["phaser_variation"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        allpass_filters = state["phaser_variation"]["allpass_filters"]

        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]

        output = input_sample + feedback * (filtered - input_sample)

        state["phaser_variation"]["lfo_phase"] = lfo_phase
        state["phaser_variation"]["allpass_filters"] = allpass_filters
        return (output, output)

    def _process_flanger_variation_effect(self, left: float, right: float,
                                        params: Dict[str, float],
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Flanger effect (variation)"""
        frequency = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)

        frequency = min(frequency, 10.0)

        if "flanger_variation" not in state:
            delay_buffer_size = int(0.02 * self.sample_rate)
            state["flanger_variation"] = {
                "lfo_phase": 0.0,
                "delay_buffer": [0.0] * delay_buffer_size,
                "buffer_pos": 0,
                "feedback_buffer": 0.0
            }

        lfo_phase = state["flanger_variation"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        delay_samples = int(lfo_value * len(state["flanger_variation"]["delay_buffer"]) * 0.5)
        input_sample = (left + right) / 2.0

        buffer = state["flanger_variation"]["delay_buffer"]
        pos = state["flanger_variation"]["buffer_pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["flanger_variation"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["flanger_variation"]["buffer_pos"] = (pos + 1) % len(buffer)
        state["flanger_variation"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - depth) + delayed_sample * depth

        state["flanger_variation"]["lfo_phase"] = lfo_phase
        return (output, output)

    def _process_auto_wah_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Auto Wah effect"""
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        if "auto_wah" not in state:
            state["auto_wah"] = {
                "envelope": 0.0,
                "cutoff": 1000.0,
                "prev_input": 0.0
            }

        input_sample = (left + right) / 2.0

        attack = 0.01
        release = 0.1
        if abs(input_sample) > state["auto_wah"]["prev_input"]:
            state["auto_wah"]["envelope"] += (abs(input_sample) - state["auto_wah"]["envelope"]) * attack
        else:
            state["auto_wah"]["envelope"] += (abs(input_sample) - state["auto_wah"]["envelope"]) * release

        state["auto_wah"]["envelope"] = max(0.0, min(1.0, state["auto_wah"]["envelope"]))

        base_freq = 200.0
        max_freq = 5000.0
        state["auto_wah"]["cutoff"] = base_freq + (max_freq - base_freq) * state["auto_wah"]["envelope"]

        norm_cutoff = state["auto_wah"]["cutoff"] / (self.sample_rate / 2.0)
        norm_cutoff = max(0.0, min(0.95, norm_cutoff))

        # Simplified filter implementation
        output = input_sample

        state["auto_wah"]["prev_input"] = abs(input_sample)
        return (output, output)

    def _process_ring_mod_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Ring Mod effect"""
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        level = params.get("parameter4", 0.5)

        if "ring_mod" not in state:
            state["ring_mod"] = {"lfo_phase": 0.0}

        lfo_phase = state["ring_mod"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        output = input_sample * lfo_value
        output = input_sample * (1 - level) + output * level

        state["ring_mod"]["lfo_phase"] = lfo_phase
        return (output, output)

    def _process_pitch_shifter_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Pitch Shifter effect"""
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        if "pitch_shifter" not in state:
            buffer_size = int(self.sample_rate * 0.1)
            state["pitch_shifter"] = {
                "delay_buffer": [0.0] * buffer_size,
                "buffer_pos": 0
            }

        pitch_factor = 2 ** (shift / 12.0)
        input_sample = (left + right) / 2.0

        delay_buffer = state["pitch_shifter"]["delay_buffer"]
        buffer_pos = state["pitch_shifter"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["pitch_shifter"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)

        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)

        shifted_sample = delay_buffer[int(read_pos)]
        output = input_sample * (1 - mix) + shifted_sample * mix

        return (output, output)

    def _process_distortion_variation_effect(self, left: float, right: float,
                                           params: Dict[str, float],
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Distortion effect (variation)"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0

        if type == 0:  # Soft clipping
            output = math.atan(input_sample * drive * 5.0) / (math.pi / 2)
        elif type == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * drive))
        elif type == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * drive)
            else:
                output = -1 + math.exp(input_sample * drive)
        else:  # Symmetric
            output = math.tanh(input_sample * drive)

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        output *= level
        return (output, output)

    def _process_overdrive_variation_effect(self, left: float, right: float,
                                          params: Dict[str, float],
                                          state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Overdrive effect (variation)"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + drive * 9.0))

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        output *= level
        return (output, output)

    def _process_compressor_variation_effect(self, left: float, right: float,
                                           params: Dict[str, float],
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Compressor effect (variation)"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 19
        attack = 1 + params.get("parameter3", 0.5) * 99
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        if "compressor_variation" not in state:
            state["compressor_variation"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            desired_gain = 1.0

        comp_state = state["compressor_variation"]
        if desired_gain < comp_state["gain"]:
            if comp_state["attack_counter"] < attack_samples:
                comp_state["attack_counter"] += 1
                factor = comp_state["attack_counter"] / attack_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        else:
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain

        comp_state["gain"] = current_gain
        output = input_sample * current_gain
        return (output, output)

    def _process_limiter_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Limiter effect"""
        threshold = -20 + params.get("parameter1", 0.5) * 20
        ratio = 10 + params.get("parameter2", 0.5) * 10
        attack = 0.1 + params.get("parameter3", 0.5) * 9.9
        release = 50 + params.get("parameter4", 0.5) * 250

        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        if "limiter" not in state:
            state["limiter"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            desired_gain = 1.0

        limiter_state = state["limiter"]
        if desired_gain < limiter_state["gain"]:
            limiter_state["gain"] = desired_gain
        else:
            if limiter_state["release_counter"] < release_samples:
                limiter_state["release_counter"] += 1
                factor = limiter_state["release_counter"] / release_samples
                limiter_state["gain"] = limiter_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                limiter_state["gain"] = desired_gain

        output = input_sample * limiter_state["gain"]
        return (output, output)

    def _process_gate_variation_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Gate effect (variation)"""
        threshold = -80 + params.get("parameter1", 0.5) * 70
        reduction = params.get("parameter2", 0.5) * 60
        attack = 1 + params.get("parameter3", 0.5) * 9
        hold = params.get("parameter4", 0.5) * 1000

        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)

        if "gate_variation" not in state:
            state["gate_variation"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        gate_state = state["gate_variation"]
        if input_level > threshold_linear:
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False

        if gate_state["open"]:
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 1.0 / max(1, attack_samples)
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            gate_state["gain"] *= 0.99

        if not gate_state["open"]:
            gate_state["gain"] *= reduction_factor

        output = input_sample * gate_state["gain"]
        return (output, output)

    def _process_expander_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Expander effect"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 9
        attack = 1 + params.get("parameter3", 0.5) * 99
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)

        if "expander" not in state:
            state["expander"] = {
                "gain": 1.0,
                "counter": 0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level < threshold_linear:
            desired_gain = 1.0 / (ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            desired_gain = 1.0

        expander_state = state["expander"]
        if desired_gain < expander_state["gain"]:
            expander_state["gain"] -= 0.01
            expander_state["gain"] = max(desired_gain, expander_state["gain"])
        else:
            expander_state["gain"] = desired_gain

        output = input_sample * expander_state["gain"]
        return (output, output)

    def _process_rotary_speaker_variation_effect(self, left: float, right: float,
                                               params: Dict[str, float],
                                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Rotary Speaker effect (variation)"""
        speed = params.get("parameter1", 0.5) * 5.0
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        if "rotary_speaker" not in state:
            state["rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }

        state["rotary_speaker"]["horn_phase"] += 2 * math.pi * state["rotary_speaker"]["horn_speed"] / self.sample_rate
        state["rotary_speaker"]["drum_phase"] += 2 * math.pi * state["rotary_speaker"]["drum_speed"] / self.sample_rate

        target_speed = speed * 0.5 + 0.5
        state["rotary_speaker"]["horn_speed"] += (target_speed - state["rotary_speaker"]["horn_speed"]) * accel
        state["rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["rotary_speaker"]["drum_speed"]) * accel

        horn_pos = math.sin(state["rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5

        input_sample = (left + right) / 2.0
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    def _process_leslie_variation_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Leslie effect (variation)"""
        speed = params.get("parameter1", 0.5) * 5.0
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        if "leslie" not in state:
            state["leslie"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }

        state["leslie"]["horn_phase"] += 2 * math.pi * state["leslie"]["horn_speed"] / self.sample_rate
        state["leslie"]["drum_phase"] += 2 * math.pi * state["leslie"]["drum_speed"] / self.sample_rate

        target_speed = speed * 0.5 + 0.5
        state["leslie"]["horn_speed"] += (target_speed - state["leslie"]["horn_speed"]) * accel
        state["leslie"]["drum_speed"] += (target_speed * 0.5 - state["leslie"]["drum_speed"]) * accel

        horn_pos = math.sin(state["leslie"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["leslie"]["drum_phase"] * 2) * 0.5 + 0.5

        input_sample = (left + right) / 2.0
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    # --- Insertion Effect Implementations ---

    def _process_distortion_effect(self, left: float, right: float,
                                  params: Dict[str, float],
                                  state: Dict[str, Any],
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Distortion effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0

        if type == 0:  # Soft clipping
            output = math.atan(input_sample * drive * 5.0) / (math.pi / 2)
        elif type == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * drive))
        elif type == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * drive)
            else:
                output = -1 + math.exp(input_sample * drive)
        else:  # Symmetric
            output = math.tanh(input_sample * drive)

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        output *= level
        return (output, output)

    def _process_overdrive_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any],
                                 system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Overdrive effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + drive * 9.0))

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        output *= level
        return (output, output)

    def _process_compressor_effect(self, left: float, right: float,
                                  params: Dict[str, float],
                                  state: Dict[str, Any],
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Compressor effect"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 19
        attack = 1 + params.get("parameter3", 0.5) * 99
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        if "compressor" not in state:
            state["compressor"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            desired_gain = 1.0

        comp_state = state["compressor"]
        if desired_gain < comp_state["gain"]:
            if comp_state["attack_counter"] < attack_samples:
                comp_state["attack_counter"] += 1
                factor = comp_state["attack_counter"] / attack_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        else:
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain

        comp_state["gain"] = current_gain
        output = input_sample * current_gain
        return (output, output)

    def _process_gate_effect(self, left: float, right: float,
                            params: Dict[str, float],
                            state: Dict[str, Any],
                            system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Gate effect"""
        threshold = -80 + params.get("parameter1", 0.5) * 70
        reduction = params.get("parameter2", 0.5) * 60
        attack = 1 + params.get("parameter3", 0.5) * 9
        hold = params.get("parameter4", 0.5) * 1000

        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)

        if "gate" not in state:
            state["gate"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0
            }

        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        gate_state = state["gate"]
        if input_level > threshold_linear:
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False

        if gate_state["open"]:
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 1.0 / max(1, attack_samples)
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            gate_state["gain"] *= 0.99

        if not gate_state["open"]:
            gate_state["gain"] *= reduction_factor

        output = input_sample * gate_state["gain"]
        return (output, output)

    def _process_envelope_filter_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any],
                                       system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Envelope Filter effect"""
        cutoff = 20 + params.get("parameter1", 0.5) * 19980
        resonance = params.get("parameter2", 0.5)
        sensitivity = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        if "envelope_filter" not in state:
            state["envelope_filter"] = {
                "envelope": 0.0,
                "prev_input": 0.0,
                "filter_state": [0.0, 0.0]
            }

        input_sample = (left + right) / 2.0

        attack = 0.01 * sensitivity
        release = 0.1 * sensitivity
        if abs(input_sample) > state["envelope_filter"]["prev_input"]:
            state["envelope_filter"]["envelope"] += (abs(input_sample) - state["envelope_filter"]["envelope"]) * attack
        else:
            state["envelope_filter"]["envelope"] += (abs(input_sample) - state["envelope_filter"]["envelope"]) * release

        state["envelope_filter"]["envelope"] = max(0.0, min(1.0, state["envelope_filter"]["envelope"]))

        base_freq = cutoff
        max_freq = cutoff * 10.0
        current_cutoff = base_freq + (max_freq - base_freq) * state["envelope_filter"]["envelope"]

        norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))

        Q = 1.0 / (resonance * 2.0 + 0.1)
        alpha = math.sin(math.pi * norm_cutoff) / (2 * Q)
        b0 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        b1 = 1 - math.cos(math.pi * norm_cutoff)
        b2 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(math.pi * norm_cutoff)
        a2 = 1 - alpha

        x = input_sample
        y = (b0/a0) * x + (b1/a0) * state["envelope_filter"]["filter_state"][0] + \
            (b2/a0) * state["envelope_filter"]["filter_state"][1] - \
            (a1/a0) * state["envelope_filter"]["filter_state"][2] - \
            (a2/a0) * state["envelope_filter"]["filter_state"][3]

        state["envelope_filter"]["filter_state"] = [
            x,
            state["envelope_filter"]["filter_state"][0],
            y,
            state["envelope_filter"]["filter_state"][2]
        ]

        state["envelope_filter"]["prev_input"] = abs(input_sample)
        return (y, y)

    def _process_guitar_amp_sim_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any],
                                      system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Guitar Amp Sim effect"""
        drive = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        distorted = math.tanh(input_sample * (1 + drive * 9.0))

        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)

        output = equalized * level
        return (output, output)

    def _process_rotary_speaker_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any],
                                      system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Rotary Speaker effect"""
        speed = params.get("parameter1", 0.5) * 5.0
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        if "rotary_speaker" not in state:
            state["rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }

        state["rotary_speaker"]["horn_phase"] += 2 * math.pi * state["rotary_speaker"]["horn_speed"] / self.sample_rate
        state["rotary_speaker"]["drum_phase"] += 2 * math.pi * state["rotary_speaker"]["drum_speed"] / self.sample_rate

        target_speed = speed * 0.5 + 0.5
        state["rotary_speaker"]["horn_speed"] += (target_speed - state["rotary_speaker"]["horn_speed"]) * accel
        state["rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["rotary_speaker"]["drum_speed"]) * accel

        horn_pos = math.sin(state["rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5

        input_sample = (left + right) / 2.0
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    def _process_leslie_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any],
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Leslie effect"""
        speed = params.get("parameter1", 0.5) * 5.0
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        if "leslie" not in state:
            state["leslie"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }

        state["leslie"]["horn_phase"] += 2 * math.pi * state["leslie"]["horn_speed"] / self.sample_rate
        state["leslie"]["drum_phase"] += 2 * math.pi * state["leslie"]["drum_speed"] / self.sample_rate

        target_speed = speed * 0.5 + 0.5
        state["leslie"]["horn_speed"] += (target_speed - state["leslie"]["horn_speed"]) * accel
        state["leslie"]["drum_speed"] += (target_speed * 0.5 - state["leslie"]["drum_speed"]) * accel

        horn_pos = math.sin(state["leslie"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["leslie"]["drum_phase"] * 2) * 0.5 + 0.5

        input_sample = (left + right) / 2.0
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    def _process_enhancer_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any],
                               system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Enhancer effect"""
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)

        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)

        output = equalized * level
        return (output, output)

    def _process_slicer_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any],
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Slicer effect"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        if "slicer" not in state:
            state["slicer"] = {"lfo_phase": 0.0}

        lfo_phase = state["slicer"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        amplitude = lfo_value * 2.0 - 1.0
        output = input_sample if input_sample > amplitude else 0.0

        state["slicer"]["lfo_phase"] = lfo_phase
        return (output, output)

    def _process_vocoder_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any],
                               system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Vocoder effect"""
        # Simplified vocoder implementation
        return (left, right)

    def _process_talk_wah_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any],
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Talk Wah effect"""
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        if "talk_wah" not in state:
            state["talk_wah"] = {
                "envelope": 0.0,
                "prev_input": 0.0,
                "filter_state": [0.0, 0.0]
            }

        input_sample = (left + right) / 2.0

        attack = 0.01 * sensitivity
        release = 0.1 * sensitivity
        if abs(input_sample) > state["talk_wah"]["prev_input"]:
            state["talk_wah"]["envelope"] += (abs(input_sample) - state["talk_wah"]["envelope"]) * attack
        else:
            state["talk_wah"]["envelope"] += (abs(input_sample) - state["talk_wah"]["envelope"]) * release

        state["talk_wah"]["envelope"] = max(0.0, min(1.0, state["talk_wah"]["envelope"]))

        base_freq = 500.0
        max_freq = 3000.0
        current_cutoff = base_freq + (max_freq - base_freq) * state["talk_wah"]["envelope"]

        norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))

        Q = 1.0 / (resonance * 2.0 + 0.1)
        alpha = math.sin(math.pi * norm_cutoff) / (2 * Q)
        b0 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        b1 = 1 - math.cos(math.pi * norm_cutoff)
        b2 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(math.pi * norm_cutoff)
        a2 = 1 - alpha

        x = input_sample
        y = (b0/a0) * x + (b1/a0) * state["talk_wah"]["filter_state"][0] + \
            (b2/a0) * state["talk_wah"]["filter_state"][1] - \
            (a1/a0) * state["talk_wah"]["filter_state"][2] - \
            (a2/a0) * state["talk_wah"]["filter_state"][3]

        state["talk_wah"]["filter_state"] = [
            x,
            state["talk_wah"]["filter_state"][0],
            y,
            state["talk_wah"]["filter_state"][2]
        ]

        state["talk_wah"]["prev_input"] = abs(input_sample)
        return (y, y)

    def _process_harmonizer_effect(self, left: float, right: float,
                                  params: Dict[str, float],
                                  state: Dict[str, Any],
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Harmonizer effect"""
        intervals = params.get("parameter1", 0.5) * 24.0 - 12.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        mix = params.get("parameter4", 0.5)

        if "harmonizer" not in state:
            buffer_size = int(self.sample_rate * 0.1)
            state["harmonizer"] = {
                "delay_buffer": [0.0] * buffer_size,
                "buffer_pos": 0
            }

        pitch_factor = 2 ** (intervals / 12.0)
        input_sample = (left + right) / 2.0

        delay_buffer = state["harmonizer"]["delay_buffer"]
        buffer_pos = state["harmonizer"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["harmonizer"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)

        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)

        harmonized_sample = delay_buffer[int(read_pos)]
        harmonized_sample = harmonized_sample + feedback * input_sample
        output = input_sample * (1 - mix) + harmonized_sample * mix

        return (output, output)

    def _process_octave_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any],
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Octave effect"""
        shift = int(params.get("parameter1", 0.5) * 4) - 2
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        if "octave" not in state:
            buffer_size = int(self.sample_rate * 0.1)
            state["octave"] = {
                "delay_buffer": [0.0] * buffer_size,
                "buffer_pos": 0
            }

        pitch_factor = 2 ** shift
        input_sample = (left + right) / 2.0

        delay_buffer = state["octave"]["delay_buffer"]
        buffer_pos = state["octave"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["octave"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)

        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)

        octaved_sample = delay_buffer[int(read_pos)]
        output = input_sample * (1 - mix) + octaved_sample * mix

        return (output, output)

    def _process_detune_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any],
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Detune effect"""
        shift = params.get("parameter1", 0.5) * 100.0 - 50.0
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        if "detune" not in state:
            buffer_size = int(self.sample_rate * 0.1)
            state["detune"] = {
                "delay_buffer": [0.0] * buffer_size,
                "buffer_pos": 0
            }

        pitch_factor = 2 ** (shift / 1200.0)
        input_sample = (left + right) / 2.0

        delay_buffer = state["detune"]["delay_buffer"]
        buffer_pos = state["detune"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["detune"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)

        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)

        detuned_sample = delay_buffer[int(read_pos)]
        output = input_sample * (1 - mix) + detuned_sample * mix

        return (output, output)

    def _process_phaser_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any],
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Phaser effect"""
        frequency = params.get("frequency", 1.0)
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.3)
        lfo_waveform = params.get("lfo_waveform", 0)

        if "phaser" not in state:
            state["phaser"] = {
                "lfo_phase": 0.0,
                "allpass_filters": [0.0] * 4
            }

        lfo_phase = state["phaser"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        allpass_filters = state["phaser"]["allpass_filters"]

        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]

        output = input_sample + feedback * (filtered - input_sample)

        state["phaser"]["lfo_phase"] = lfo_phase
        state["phaser"]["allpass_filters"] = allpass_filters
        return (output, output)

    def _process_flanger_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any],
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Flanger effect"""
        frequency = params.get("frequency", 0.5)
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.3)
        lfo_waveform = params.get("lfo_waveform", 0)

        frequency = min(frequency, 10.0)

        if "flanger" not in state:
            delay_buffer_size = int(0.02 * self.sample_rate)
            state["flanger"] = {
                "lfo_phase": 0.0,
                "delay_buffer": [0.0] * delay_buffer_size,
                "buffer_pos": 0,
                "feedback_buffer": 0.0
            }

        lfo_phase = state["flanger"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate

        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        delay_samples = int(lfo_value * len(state["flanger"]["delay_buffer"]) * 0.5)
        input_sample = (left + right) / 2.0

        buffer = state["flanger"]["delay_buffer"]
        pos = state["flanger"]["buffer_pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["flanger"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["flanger"]["buffer_pos"] = (pos + 1) % len(buffer)
        state["flanger"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - depth) + delayed_sample * depth

        state["flanger"]["lfo_phase"] = lfo_phase
        return (output, output)

    def _process_wah_wah_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any],
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Wah Wah effect"""
        manual_position = params.get("manual_position", 0.5)
        lfo_rate = params.get("lfo_rate", 0.5) * 5.0
        lfo_depth = params.get("lfo_depth", 0.5)
        resonance = params.get("resonance", 0.5)

        if "wah_wah" not in state:
            state["wah_wah"] = {
                "lfo_phase": 0.0,
                "filter_state": [0.0, 0.0, 0.0, 0.0]  # x1, x2, y1, y2 for biquad filter
            }

        lfo_phase = state["wah_wah"]["lfo_phase"]
        lfo_phase += 2 * math.pi * lfo_rate / self.sample_rate

        # LFO modulation
        lfo_value = math.sin(lfo_phase) * lfo_depth * 0.5 + 0.5
        cutoff_freq = manual_position + lfo_value * 0.5  # Combine manual and LFO
        cutoff_freq = max(0.01, min(0.99, cutoff_freq))  # Clamp to valid range

        # Convert to frequency
        freq = 200.0 + cutoff_freq * 3800.0  # 200Hz to 4000Hz range
        norm_cutoff = freq / (self.sample_rate / 2.0)
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))

        # Resonance (Q factor)
        q = 1.0 / (resonance * 2.0 + 0.1)

        # Bandpass filter coefficients
        alpha = math.sin(math.pi * norm_cutoff) / (2 * q)
        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(math.pi * norm_cutoff)
        a2 = 1 - alpha

        # Process left channel
        x_left = left
        filter_state = state["wah_wah"]["filter_state"]
        y_left = (b0/a0) * x_left + (b1/a0) * filter_state[0] + (b2/a0) * filter_state[1] - \
                 (a1/a0) * filter_state[2] - (a2/a0) * filter_state[3]

        # Update filter state for left
        filter_state[0] = x_left
        filter_state[1] = filter_state[0]
        filter_state[2] = y_left
        filter_state[3] = filter_state[2]

        # Process right channel (same coefficients)
        x_right = right
        y_right = (b0/a0) * x_right + (b1/a0) * filter_state[0] + (b2/a0) * filter_state[1] - \
                  (a1/a0) * filter_state[2] - (a2/a0) * filter_state[3]

        # Update filter state for right
        filter_state[0] = x_right
        filter_state[1] = filter_state[0]
        filter_state[2] = y_right
        filter_state[3] = filter_state[2]

        state["wah_wah"]["lfo_phase"] = lfo_phase
        state["wah_wah"]["filter_state"] = filter_state

        return (y_left, y_right)

    # --- Additional Variation Effect Implementations (simplified stubs) ---

    def _process_vibrato_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Vibrato effect"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        if "vibrato" not in state:
            state["vibrato"] = {"lfo_phase": 0.0}

        lfo_phase = state["vibrato"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        else:
            lfo_value = math.sin(lfo_phase)

        lfo_value = lfo_value * depth * 0.02
        output_left = left * (1 + lfo_value)
        output_right = right * (1 + lfo_value)

        state["vibrato"]["lfo_phase"] = lfo_phase
        return (output_left, output_right)

    def _process_acoustic_simulator_effect(self, left: float, right: float,
                                          params: Dict[str, float],
                                          state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Acoustic Simulator effect"""
        room = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0

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

        return (output, output)

    def _process_guitar_amp_sim_variation_effect(self, left: float, right: float,
                                               params: Dict[str, float],
                                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Guitar Amp Sim effect (variation)"""
        drive = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        distorted = math.tanh(input_sample * (1 + drive * 9.0))

        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)

        output = equalized * level
        return (output, output)

    def _process_enhancer_variation_effect(self, left: float, right: float,
                                         params: Dict[str, float],
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Enhancer effect (variation)"""
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)

        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)

        output = equalized * level
        return (output, output)

    def _process_slicer_variation_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Slicer effect (variation)"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        if "slicer" not in state:
            state["slicer"] = {"lfo_phase": 0.0}

        lfo_phase = state["slicer"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        amplitude = lfo_value * 2.0 - 1.0
        output = input_sample if input_sample > amplitude else 0.0

        state["slicer"]["lfo_phase"] = lfo_phase
        return (output, output)

    # --- Simplified stubs for remaining effects ---

    def _process_step_phaser_effect(self, left: float, right: float,
                                   params: Dict[str, float],
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Phaser effect"""
        return (left, right)

    def _process_step_flanger_effect(self, left: float, right: float,
                                    params: Dict[str, float],
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Flanger effect"""
        return (left, right)

    def _process_step_tremolo_effect(self, left: float, right: float,
                                    params: Dict[str, float],
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Tremolo effect"""
        return (left, right)

    def _process_step_pan_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Pan effect"""
        return (left, right)

    def _process_step_filter_effect(self, left: float, right: float,
                                   params: Dict[str, float],
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Filter effect"""
        return (left, right)

    def _process_auto_filter_effect(self, left: float, right: float,
                                   params: Dict[str, float],
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Auto Filter effect"""
        return (left, right)

    def _process_vocoder_variation_effect(self, left: float, right: float,
                                        params: Dict[str, float],
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Vocoder effect (variation)"""
        return (left, right)

    def _process_talk_wah_variation_effect(self, left: float, right: float,
                                         params: Dict[str, float],
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Talk Wah effect (variation)"""
        return (left, right)

    def _process_harmonizer_variation_effect(self, left: float, right: float,
                                           params: Dict[str, float],
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Harmonizer effect (variation)"""
        return (left, right)

    def _process_octave_variation_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Octave effect (variation)"""
        return (left, right)

    def _process_detune_variation_effect(self, left: float, right: float,
                                       params: Dict[str, float],
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Detune effect (variation)"""
        return (left, right)

    def _process_chorus_reverb_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Chorus/Reverb effect"""
        chorus = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        chorus_sample = input_sample  # Simplified chorus
        reverb_sample = input_sample  # Simplified reverb
        output = input_sample * (1 - mix) + chorus_sample * mix * chorus + reverb_sample * mix * reverb
        output *= level
        return (output, output)

    def _process_stereo_imager_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Stereo Imager effect"""
        width = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        center = (left + right) / 2.0
        sides = (left - right) / 2.0
        sides_enhanced = sides * (1 + width)
        left_out = center + sides_enhanced
        right_out = center - sides_enhanced
        left_out = left * (1 - depth) + left_out * depth
        right_out = right * (1 - depth) + right_out * depth
        left_out *= level
        right_out *= level
        return (left_out, right_out)

    def _process_ambience_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Ambience effect"""
        reverb = params.get("parameter1", 0.5)
        delay = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        reverb_sample = input_sample  # Simplified reverb
        delay_sample = input_sample  # Simplified delay
        output = input_sample * (1 - mix) + reverb_sample * mix * reverb + delay_sample * mix * delay
        output *= level
        return (output, output)

    def _process_doubler_effect(self, left: float, right: float,
                               params: Dict[str, float],
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Doubler effect"""
        enhance = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        doubled_sample = input_sample  # Simplified doubler
        output = input_sample * (1 - mix) + doubled_sample * mix
        output *= level
        return (output, output)

    def _process_enhancer_reverb_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Enhancer/Reverb effect"""
        enhance = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)
        reverb_sample = input_sample  # Simplified reverb
        output = enhanced * (1 - mix) + reverb_sample * mix
        output *= level
        return (output, output)

    def _process_spectral_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Spectral effect"""
        spectrum = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        formant = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        output = input_sample * level
        return (output, output)

    def _process_resonator_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Resonator effect"""
        resonance = params.get("parameter1", 0.5)
        decay = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0
        output = input_sample * level
        return (output, output)

    def _process_degrader_effect(self, left: float, right: float,
                                params: Dict[str, float],
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Degrader effect"""
        bit_depth = int(params.get("parameter1", 0.5) * 16) + 1
        sample_rate = params.get("parameter2", 0.5) * 22050.0 + 22050.0
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0
        output = input_sample * level
        return (output, output)

    def _process_vinyl_effect(self, left: float, right: float,
                             params: Dict[str, float],
                             state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Vinyl effect"""
        warp = params.get("parameter1", 0.5)
        crackle = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)

        input_sample = (left + right) / 2.0
        output = input_sample * level
        return (output, output)

    def _process_looper_effect(self, left: float, right: float,
                              params: Dict[str, float],
                              state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Looper effect"""
        loop = params.get("parameter1", 0.5)
        speed = params.get("parameter2", 0.5)
        reverse = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        input_sample = (left + right) / 2.0
        output = input_sample * level
        return (output, output)

    def _process_step_delay_effect(self, left: float, right: float,
                                  params: Dict[str, float],
                                  state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Delay effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["step_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        step = state["step_delay"]["step"]
        step = (step + 1) % steps
        state["step_delay"]["step"] = step

        delay_samples = int(time * (step + 1) / steps * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["step_delay"]["buffer"]
        pos = state["step_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["step_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["step_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_delay"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        return (output, output)

    def _process_step_echo_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Echo effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_echo" not in state:
            buffer_size = int(self.sample_rate)
            state["step_echo"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        step = state["step_echo"]["step"]
        step = (step + 1) % steps
        state["step_echo"]["step"] = step

        delay_samples = int(time * (step + 1) / steps * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["step_echo"]["buffer"]
        pos = state["step_echo"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["step_echo"]["feedback_buffer"] * feedback * (1 - step / steps)
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["step_echo"]["pos"] = (pos + 1) % len(buffer)
        state["step_echo"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        return (output, output)

    def _process_step_pan_delay_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Pan Delay effect"""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_pan_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["step_pan_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        step = state["step_pan_delay"]["step"]
        step = (step + 1) % steps
        state["step_pan_delay"]["step"] = step

        delay_samples = int(time * (step + 1) / steps * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["step_pan_delay"]["buffer"]
        pos = state["step_pan_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["step_pan_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["step_pan_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_pan_delay"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level
        pan = step / (steps - 1)
        left_out = output * (1 - pan)
        right_out = output * pan

        return (left_out, right_out)

    def _process_step_cross_delay_effect(self, left: float, right: float,
                                        params: Dict[str, float],
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Cross Delay effect"""
        time = params.get("parameter1", 0.3) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_cross_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["step_cross_delay"] = {
                "left_buffer": [0.0] * buffer_size,
                "right_buffer": [0.0] * buffer_size,
                "left_pos": 0,
                "right_pos": 0,
                "left_feedback": 0.0,
                "right_feedback": 0.0,
                "step": 0
            }

        step = state["step_cross_delay"]["step"]
        step = (step + 1) % steps
        state["step_cross_delay"]["step"] = step

        delay_samples = int(time * (step + 1) / steps * self.sample_rate / 1000.0)

        buffer_left = state["step_cross_delay"]["left_buffer"]
        buffer_right = state["step_cross_delay"]["right_buffer"]
        pos_left = state["step_cross_delay"]["left_pos"]
        pos_right = state["step_cross_delay"]["right_pos"]

        delay_pos_left = (pos_left - delay_samples) % len(buffer_left)
        delay_pos_right = (pos_right - delay_samples) % len(buffer_right)

        delayed_left = buffer_left[int(delay_pos_left)]
        delayed_right = buffer_right[int(delay_pos_right)]

        feedback_left = state["step_cross_delay"]["left_feedback"] * feedback * (1 - step / steps)
        feedback_right = state["step_cross_delay"]["right_feedback"] * feedback * (1 - step / steps)
        cross_left_feedback = state["step_cross_delay"]["right_feedback"] * feedback * (step / steps)
        cross_right_feedback = state["step_cross_delay"]["left_feedback"] * feedback * (step / steps)

        processed_left = left + feedback_left + cross_left_feedback
        processed_right = right + feedback_right + cross_right_feedback

        buffer_left[pos_left] = processed_left
        buffer_right[pos_right] = processed_right
        state["step_cross_delay"]["left_pos"] = (pos_left + 1) % len(buffer_left)
        state["step_cross_delay"]["right_pos"] = (pos_right + 1) % len(buffer_right)
        state["step_cross_delay"]["left_feedback"] = processed_left
        state["step_cross_delay"]["right_feedback"] = processed_right

        left_out = left * (1 - level) + delayed_left * level
        right_out = right * (1 - level) + delayed_right * level

        return (left_out, right_out)

    def _process_step_multi_tap_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Multi Tap effect"""
        taps = int(params.get("parameter1", 0.5) * 10) + 1
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_multi_tap" not in state:
            buffer_size = int(self.sample_rate)
            state["step_multi_tap"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }

        step = state["step_multi_tap"]["step"]
        step = (step + 1) % steps
        state["step_multi_tap"]["step"] = step

        input_sample = (left + right) / 2.0
        buffer = state["step_multi_tap"]["buffer"]
        pos = state["step_multi_tap"]["pos"]

        delayed_sum = 0.0
        for i in range(taps):
            delay_time = (i * 500 * (step + 1) / steps)
            delay_samples = int(delay_time * self.sample_rate / 1000.0)
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sum += buffer[int(delay_pos)]

        delayed_sum /= taps

        feedback_sample = state["step_multi_tap"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["step_multi_tap"]["pos"] = (pos + 1) % len(buffer)
        state["step_multi_tap"]["feedback_buffer"] = processed_sample

        output = input_sample * (1 - level) + delayed_sum * level
        return (output, output)

    def _process_step_reverse_delay_effect(self, left: float, right: float,
                                         params: Dict[str, float],
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Reverse Delay effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_reverse_delay" not in state:
            buffer_size = int(self.sample_rate)
            state["step_reverse_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "reverse_buffer": [0.0] * buffer_size,
                "step": 0
            }

        step = state["step_reverse_delay"]["step"]
        step = (step + 1) % steps
        state["step_reverse_delay"]["step"] = step

        delay_samples = int(time * (step + 1) / steps * self.sample_rate / 1000.0)
        input_sample = (left + right) / 2.0

        buffer = state["step_reverse_delay"]["buffer"]
        pos = state["step_reverse_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]

        feedback_sample = state["step_reverse_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample

        buffer[pos] = processed_sample
        state["step_reverse_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_reverse_delay"]["feedback_buffer"] = processed_sample

        reverse_buffer = state["step_reverse_delay"]["reverse_buffer"]
        reverse_pos = (pos + delay_samples) % len(reverse_buffer)
        reverse_sample = reverse_buffer[int(reverse_pos)]

        reverse_buffer[pos] = processed_sample

        output = input_sample * (1 - level) + delayed_sample * level * (1 - step / steps) + reverse_sample * level * (step / steps)
        return (output, output)

    def _process_step_ring_mod_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Ring Mod effect"""
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if "step_ring_mod" not in state:
            state["step_ring_mod"] = {"step": 0}

        step = state["step_ring_mod"]["step"]
        step = (step + 1) % steps
        state["step_ring_mod"]["step"] = step

        lfo_value = step / (steps - 1)

        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_value * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs(lfo_value * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if step > steps / 2 else -1
        else:  # Sawtooth
            lfo_value = lfo_value * 2 - 1

        lfo_value = lfo_value * depth * 0.5 + 0.5
        input_sample = (left + right) / 2.0
        output = input_sample * lfo_value
        return (output, output)

    def _process_step_pitch_shifter_effect(self, left: float, right: float,
                                         params: Dict[str, float],
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Pitch Shifter effect"""
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0
        feedback = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        formant = params.get("parameter4", 0.5)

        if "step_pitch_shifter" not in state:
            buffer_size = int(self.sample_rate * 0.1)
            state["step_pitch_shifter"] = {
                "delay_buffer": [0.0] * buffer_size,
                "buffer_pos": 0,
                "step": 0
            }

        step = state["step_pitch_shifter"]["step"]
        step = (step + 1) % steps
        state["step_pitch_shifter"]["step"] = step

        pitch_factor = 2 ** (shift * (step + 1) / steps / 12.0)
        input_sample = (left + right) / 2.0

        delay_buffer = state["step_pitch_shifter"]["delay_buffer"]
        buffer_pos = state["step_pitch_shifter"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["step_pitch_shifter"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)

        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)

        shifted_sample = delay_buffer[int(read_pos)]
        output = input_sample * (1 - feedback) + shifted_sample * feedback

        return (output, output)

    def _process_step_distortion_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Distortion effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        type = int(params.get("parameter4", 0.5) * 3)

        if "step_distortion" not in state:
            state["step_distortion"] = {"step": 0}

        step = state["step_distortion"]["step"]
        step = (step + 1) % steps
        state["step_distortion"]["step"] = step

        step_drive = drive * (step + 1) / steps
        input_sample = (left + right) / 2.0

        if type == 0:  # Soft clipping
            output = math.atan(input_sample * step_drive * 5.0) / (math.pi / 2)
        elif type == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * step_drive))
        elif type == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * step_drive)
            else:
                output = -1 + math.exp(input_sample * step_drive)
        else:  # Symmetric
            output = math.tanh(input_sample * step_drive)

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        return (output, output)

    def _process_step_overdrive_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Overdrive effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        bias = params.get("parameter4", 0.5)

        if "step_overdrive" not in state:
            state["step_overdrive"] = {"step": 0}

        step = state["step_overdrive"]["step"]
        step = (step + 1) % steps
        state["step_overdrive"]["step"] = step

        step_drive = drive * (step + 1) / steps
        input_sample = (left + right) / 2.0
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + step_drive * 9.0))

        if tone < 0.5:
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost

        return (output, output)

    def _process_step_compressor_effect(self, left: float, right: float,
                                      params: Dict[str, float],
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Compressor effect"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 19
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        if "step_compressor" not in state:
            state["step_compressor"] = {
                "gain": 1.0,
                "release_counter": 0,
                "step": 0
            }

        step = state["step_compressor"]["step"]
        step = (step + 1) % steps
        state["step_compressor"]["step"] = step

        step_ratio = ratio * (step + 1) / steps
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/step_ratio))
        else:
            desired_gain = 1.0

        comp_state = state["step_compressor"]
        if desired_gain < comp_state["gain"]:
            comp_state["gain"] = desired_gain
        else:
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                comp_state["gain"] = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                comp_state["gain"] = desired_gain

        output = input_sample * comp_state["gain"]
        return (output, output)

    def _process_step_limiter_effect(self, left: float, right: float,
                                    params: Dict[str, float],
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Limiter effect"""
        threshold = -20 + params.get("parameter1", 0.5) * 20
        ratio = 10 + params.get("parameter2", 0.5) * 10
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        release = 50 + params.get("parameter4", 0.5) * 250

        threshold_linear = 10 ** (threshold / 20.0)
        release_samples = int(release * self.sample_rate / 1000.0)

        if "step_limiter" not in state:
            state["step_limiter"] = {
                "gain": 1.0,
                "release_counter": 0,
                "step": 0
            }

        step = state["step_limiter"]["step"]
        step = (step + 1) % steps
        state["step_limiter"]["step"] = step

        step_ratio = ratio * (step + 1) / steps
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level > threshold_linear:
            desired_gain = threshold_linear / (input_level ** (1/step_ratio))
        else:
            desired_gain = 1.0

        limiter_state = state["step_limiter"]
        if desired_gain < limiter_state["gain"]:
            limiter_state["gain"] = desired_gain
        else:
            if limiter_state["release_counter"] < release_samples:
                limiter_state["release_counter"] += 1
                factor = limiter_state["release_counter"] / release_samples
                limiter_state["gain"] = limiter_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                limiter_state["gain"] = desired_gain

        output = input_sample * limiter_state["gain"]
        return (output, output)

    def _process_step_gate_effect(self, left: float, right: float,
                                 params: Dict[str, float],
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Gate effect"""
        threshold = -80 + params.get("parameter1", 0.5) * 70
        reduction = params.get("parameter2", 0.5) * 60
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        hold = params.get("parameter4", 0.5) * 1000

        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)

        if "step_gate" not in state:
            state["step_gate"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0,
                "step": 0
            }

        step = state["step_gate"]["step"]
        step = (step + 1) % steps
        state["step_gate"]["step"] = step

        step_reduction = reduction * (step + 1) / steps
        step_reduction_factor = 10 ** (-step_reduction / 20.0)
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        gate_state = state["step_gate"]
        if input_level > threshold_linear:
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False

        if gate_state["open"]:
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 1.0 / max(1, 100)  # Simplified attack
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            gate_state["gain"] *= 0.99

        if not gate_state["open"]:
            gate_state["gain"] *= step_reduction_factor

        output = input_sample * gate_state["gain"]
        return (output, output)

    def _process_step_rotary_speaker_effect(self, left: float, right: float,
                                         params: Dict[str, float],
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Rotary Speaker effect"""
        speed = params.get("parameter1", 0.5) * 5.0
        balance = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        level = params.get("parameter4", 0.5)

        if "step_rotary_speaker" not in state:
            state["step_rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0,
                "step": 0
            }

        step = state["step_rotary_speaker"]["step"]
        step = (step + 1) % steps
        state["step_rotary_speaker"]["step"] = step

        target_speed = speed * (step + 1) / steps
        state["step_rotary_speaker"]["horn_speed"] += (target_speed - state["step_rotary_speaker"]["horn_speed"]) * 0.1
        state["step_rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["step_rotary_speaker"]["drum_speed"]) * 0.1

        state["step_rotary_speaker"]["horn_phase"] += 2 * math.pi * state["step_rotary_speaker"]["horn_speed"] / self.sample_rate
        state["step_rotary_speaker"]["drum_phase"] += 2 * math.pi * state["step_rotary_speaker"]["drum_speed"] / self.sample_rate

        horn_pos = math.sin(state["step_rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["step_rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5

        input_sample = (left + right) / 2.0
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos

        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level

        return (left_out, right_out)

    def _process_step_expander_effect(self, left: float, right: float,
                                     params: Dict[str, float],
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Process Step Expander effect"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 9
        steps = int(params.get("parameter3", 0.5) * 8) + 1
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)

        if "step_expander" not in state:
            state["step_expander"] = {
                "gain": 1.0,
                "counter": 0,
                "step": 0
            }

        step = state["step_expander"]["step"]
        step = (step + 1) % steps
        state["step_expander"]["step"] = step

        step_ratio = ratio * (step + 1) / steps
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)

        if input_level < threshold_linear:
            desired_gain = 1.0 / (step_ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            desired_gain = 1.0

        expander_state = state["step_expander"]
        if desired_gain < expander_state["gain"]:
            expander_state["gain"] -= 0.01
            expander_state["gain"] = max(desired_gain, expander_state["gain"])
        else:
            expander_state["gain"] = desired_gain

        output = input_sample * expander_state["gain"]
        return (output, output)
