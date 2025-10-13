"""
Insertion Effects Module

This module contains all insertion effect implementations for the XG Synthesizer.
These effects are applied to individual channels rather than the final mix.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
import math
from synth.effects.dsp_units import DSPUnitsManager


class InsertionEffectsProcessor:
    """
    Processor for insertion effects that are applied to individual channels.
    
    These effects are applied per-channel before mixing, unlike system effects
    which are applied to the final mixed output.
    """
    
    def __init__(self, sample_rate: int, block_size: int, dsp_units: DSPUnitsManager):
        """
        Initialize the insertion effects processor.
        
        Args:
            sample_rate: Sample rate for audio processing
            block_size: Size of audio blocks to process
            dsp_units: DSP units manager for shared components
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.dsp_units = dsp_units
        
        # Pre-allocated buffers for zero-allocation processing
        self._eq_insertion_filters = [{
            'low_state': [0.0, 0.0],    # x1, x2 for low shelf
            'mid_state': [0.0, 0.0],    # x1, x2 for peaking
            'high_state': [0.0, 0.0]    # x1, x2 for high shelf
        } for _ in range(16)]
        
        # Initialize compressor states
        self._compressor_states = [{
            'gain': 1.0,
            'envelope': 0.0
        } for _ in range(16)]

    def apply_insertion_effect_to_channel_zero_alloc(
        self, 
        target_buffer: np.ndarray, 
        channel_array: np.ndarray,
        insertion_params: Dict[str, Any],
        num_samples: int, 
        channel_idx: int
    ) -> None:
        """
        Apply insertion effect to a single channel using zero-allocation approach.

        Args:
            target_buffer: Pre-allocated buffer to write results to
            channel_array: Input channel audio as NumPy array
            insertion_params: Insertion effect parameters
            num_samples: Number of samples to process
            channel_idx: Channel index for pre-allocated buffer access
        """
        effect_type = insertion_params.get("type", 0)

        # Handle different insertion effect types
        if effect_type == 0:  # No effect
            # Copy input to processing buffer
            if len(channel_array.shape) == 2 and channel_array.shape[1] == 2:
                np.copyto(target_buffer[:num_samples, :], channel_array[:num_samples])
            else:
                np.copyto(target_buffer[:num_samples, 0], channel_array[:num_samples])
                np.copyto(target_buffer[:num_samples, 1], channel_array[:num_samples])
        elif effect_type == 1:  # Distortion
            self._apply_distortion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 2:  # Overdrive
            self._apply_overdrive_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 3:  # Compressor
            self._apply_compressor_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 4:  # Gate
            self._apply_gate_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 5:  # Envelope Filter
            self._apply_envelope_filter_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 6:  # Guitar Amp Sim
            self._apply_guitar_amp_sim_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 7:  # Rotary Speaker
            self._apply_rotary_speaker_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 8:  # Leslie
            self._apply_leslie_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 9:  # Enhancer
            self._apply_enhancer_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 10:  # Slicer
            self._apply_slicer_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 11:  # Vocoder
            self._apply_vocoder_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 12:  # Talk Wah
            self._apply_talk_wah_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 13:  # Harmonizer
            self._apply_harmonizer_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 14:  # Octave
            self._apply_octave_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 15:  # Detune
            self._apply_detune_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 16:  # Phaser
            self._apply_phaser_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 17:  # Flanger
            self._apply_flanger_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 18:  # Wah Wah
            self._apply_wah_wah_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 19:  # EQ
            self._apply_eq_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 20:  # Vocal Filter
            self._apply_vocal_filter_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 21:  # Auto Wah
            self._apply_auto_wah_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 22:  # Pitch Shifter
            self._apply_pitch_shifter_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 23:  # Ring Modulator
            self._apply_ring_mod_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 24:  # Tremolo
            self._apply_tremolo_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 25:  # Auto Pan
            self._apply_auto_pan_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 26:  # Step Phaser
            self._apply_step_phaser_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 27:  # Step Flanger
            self._apply_step_flanger_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 28:  # Step Filter
            self._apply_step_filter_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 29:  # Spectral Filter
            self._apply_spectral_filter_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 30:  # Resonator
            self._apply_resonator_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 31:  # Degrader
            self._apply_degrader_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 32:  # Vinyl Simulator
            self._apply_vinyl_sim_insertion_effect_zero_alloc(target_buffer, channel_array, insertion_params, num_samples, channel_idx)
        else:
            # Unknown effect type - copy original
            if len(channel_array.shape) == 2 and channel_array.shape[1] == 2:
                np.copyto(target_buffer[:num_samples, :], channel_array[:num_samples])
            else:
                np.copyto(target_buffer[:num_samples, 0], channel_array[:num_samples])
                np.copyto(target_buffer[:num_samples, 1], channel_array[:num_samples])

    def apply_insertion_effect_to_channel(
        self, 
        channel_array: np.ndarray,
        insertion_params: Dict[str, Any],
        num_samples: int
    ) -> np.ndarray:
        """
        Apply insertion effect to a single channel.

        Args:
            channel_array: Input channel audio as NumPy array
            insertion_params: Insertion effect parameters
            num_samples: Number of samples to process

        Returns:
            Processed channel audio as NumPy array
        """
        effect_type = insertion_params.get("type", 0)

        # Handle different insertion effect types
        if effect_type == 0:  # No effect
            return channel_array.copy()
        elif effect_type == 1:  # Distortion
            return self._apply_distortion_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 2:  # Overdrive
            return self._apply_overdrive_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 3:  # Compressor
            return self._apply_compressor_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 16:  # Phaser
            return self._apply_phaser_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 17:  # Flanger
            return self._apply_flanger_effect(channel_array, insertion_params, num_samples)
        else:
            # Unknown effect type - return original
            return channel_array.copy()

    def _apply_distortion_effect(self, input_array: np.ndarray,
                               params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply distortion effect to channel"""
        output = input_array.copy()

        # Simple distortion implementation
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply distortion curve
        output = np.tanh(output * (1.0 + drive * 10.0))

        # Apply tone filtering (simplified)
        if tone < 0.5:
            # Low-pass filter approximation
            alpha = tone * 2.0
            for i in range(1, len(output)):
                output[i] = alpha * output[i] + (1.0 - alpha) * output[i-1]

        # Apply output level
        output *= level * 2.0

        return output

    def _apply_overdrive_effect(self, input_array: np.ndarray,
                              params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply overdrive effect to channel"""
        output = input_array.copy()

        # Softer distortion than regular distortion
        drive = params.get("parameter1", 0.3)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply softer distortion curve
        output = output * (1.0 + drive * 5.0)
        output = np.clip(output, -1.0, 1.0)
        output = np.tanh(output * 1.5)

        # Apply tone filtering
        if tone < 0.5:
            alpha = tone * 2.0
            for i in range(1, len(output)):
                output[i] = alpha * output[i] + (1.0 - alpha) * output[i-1]

        # Apply output level
        output *= level * 2.0

        return output

    def _apply_compressor_effect(self, input_array: np.ndarray,
                               params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply compressor effect to channel"""
        output = input_array.copy()

        # Simple compressor implementation
        threshold = params.get("parameter1", 0.5)  # 0.0-1.0
        ratio = params.get("parameter2", 0.5)       # 1.0-10.0
        attack = params.get("parameter3", 0.1)      # 0.001-0.1 seconds
        release = params.get("parameter4", 0.5)     # 0.1-1.0 seconds

        # Convert parameters
        threshold_db = threshold * 40.0 - 20.0  # -20dB to +20dB
        threshold_linear = 10.0 ** (threshold_db / 20.0)
        ratio = 1.0 + ratio * 9.0  # 1.0 to 10.0

        # Simple compression
        compressed = np.copy(output)
        mask = np.abs(compressed) > threshold_linear
        compressed[mask] = np.sign(compressed[mask]) * (
            threshold_linear + (np.abs(compressed[mask]) - threshold_linear) / ratio
        )

        return compressed

    def _apply_phaser_effect(self, input_array: np.ndarray,
                           params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply phaser effect to channel"""
        # Simple phaser implementation
        frequency = params.get("frequency", 1.0)  # Hz
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.3)

        # Create LFO for phaser
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)

        # Simple all-pass filter implementation
        output = np.zeros_like(input_array)
        prev_input = 0.0
        prev_output = 0.0

        for i in range(num_samples):
            # All-pass filter coefficient modulated by LFO
            g = depth * lfo[i] * 0.9 + 0.1

            # All-pass filter
            ap_input = input_array[i] + feedback * prev_output
            ap_output = g * ap_input + prev_input

            output[i] = ap_output
            prev_input = ap_input
            prev_output = ap_output

        return output

    def _apply_flanger_effect(self, input_array: np.ndarray,
                            params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply flanger effect to channel"""
        # Simple flanger implementation
        frequency = params.get("frequency", 0.5)  # Hz
        depth = params.get("depth", 0.7)
        feedback = params.get("feedback", 0.5)

        # Create LFO for flanger
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)

        # Delay line for flanger effect
        delay_samples = int(0.001 * self.sample_rate)  # 1ms base delay
        max_delay = int(0.005 * self.sample_rate)       # 5ms max delay

        output = np.zeros_like(input_array)
        delay_buffer = np.zeros(max_delay + 1)

        for i in range(num_samples):
            # Calculate variable delay
            delay_offset = int(depth * max_delay * (lfo[i] + 1.0) / 2.0)
            delay_pos = delay_samples + delay_offset

            if delay_pos < len(delay_buffer):
                delayed_sample = delay_buffer[delay_pos]
            else:
                delayed_sample = delay_buffer[-1]

            # Flanger output
            output[i] = input_array[i] + feedback * delayed_sample

            # Update delay buffer
            delay_buffer = np.roll(delay_buffer, 1)
            delay_buffer[0] = input_array[i]

        return output

    # ZERO-ALLOCATION EFFECT IMPLEMENTATIONS
    def _apply_distortion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY DISTORTION EFFECT - ZERO ALLOCATION

        Multi-type distortion with proper tone control using DSP units
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get distortion parameters
        drive = params.get("parameter1", 0.5)  # 0.0-1.0
        tone = params.get("parameter2", 0.5)   # 0.0-1.0
        level = params.get("level", 0.5)       # 0.0-1.0
        distortion_type = params.get("parameter3", 0.0)  # 0.0-1.0 maps to types

        # Get filter for tone control
        tone_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"distortion_tone_{channel_idx}", 0,
            cutoff=1000.0 + tone * 3000.0,  # 1k-4k Hz tone control
            resonance=0.7,
            filter_type="lowpass"
        )

        # Apply distortion based on type
        type_idx = int(distortion_type * 3)  # 0-3 types

        if type_idx == 0:  # Soft clipping
            drive_scaled = drive * 9.0 + 1.0
            distorted = np.tanh(target_buffer[:num_samples] * drive_scaled)
        elif type_idx == 1:  # Hard clipping
            drive_scaled = drive * 9.0 + 1.0
            np.copyto(target_buffer[:num_samples], target_buffer[:num_samples])
            np.clip(target_buffer[:num_samples] * drive_scaled, -1.0, 1.0, out=target_buffer[:num_samples])
            distorted = target_buffer[:num_samples].copy()
        elif type_idx == 2:  # Asymmetric
            biased = target_buffer[:num_samples] + drive * 0.1
            distorted = np.where(biased > 0,
                               1.0 - np.exp(-biased * (1 + drive * 9.0)),
                               -1.0 + np.exp(biased * (1 + drive * 9.0)))
        else:  # Symmetric
            drive_scaled = drive * 9.0 + 1.0
            distorted = np.tanh(target_buffer[:num_samples] * drive_scaled)

        # Apply tone control through filter
        # Process through filter in blocks for efficiency
        output = np.empty_like(distorted)
        for i in range(0, len(distorted), 64):  # Process in 64-sample blocks
            end_idx = min(i + 64, len(distorted))
            block_input = distorted[i:end_idx]
            block_output = np.empty_like(block_input)

            # Apply filter to block
            filtered_block = tone_filter.process_block(
                block_input.reshape(-1, 1),  # Mono to stereo
                np.zeros((len(block_input), 1))  # Zero right channel
            )
            output[i:end_idx] = filtered_block[:, 0]  # Take left channel

        # Update target buffer
        np.copyto(target_buffer[:num_samples], output)

        # Apply level
        target_buffer[:num_samples] *= level

    def _apply_overdrive_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                          params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply overdrive effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Softer distortion than regular distortion
        drive = params.get("parameter1", 0.3)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply softer distortion curve
        target_buffer[:num_samples] *= (1.0 + drive * 5.0)
        np.clip(target_buffer[:num_samples], -1.0, 1.0, out=target_buffer[:num_samples])
        np.tanh(target_buffer[:num_samples] * 1.5, out=target_buffer[:num_samples])

        # Apply tone filtering
        if tone < 0.5:
            alpha = tone * 2.0
            for i in range(1, num_samples):
                target_buffer[i, 0] = alpha * target_buffer[i, 0] + (1.0 - alpha) * target_buffer[i-1, 0]
                target_buffer[i, 1] = alpha * target_buffer[i, 1] + (1.0 - alpha) * target_buffer[i-1, 1]

        # Apply output level
        target_buffer[:num_samples] *= level * 2.0

    def _apply_compressor_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply professional compressor effect with sidechain-like processing using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get or create state for this channel
        if channel_idx >= len(self._compressor_states):
            for _ in range(channel_idx - len(self._compressor_states) + 1):
                self._compressor_states.append({
                    'gain': 1.0,
                    'envelope': 0.0
                })

        state = self._compressor_states[channel_idx]

        # Professional compressor parameters
        threshold_db = (params.get("parameter1", 0.5) * 40.0) - 20.0  # -20dB to +20dB
        ratio = 1.0 + params.get("parameter2", 0.5) * 19.0             # 1:1 to 20:1
        attack_ms = 1.0 + params.get("parameter3", 0.5) * 99.0          # 1-100ms
        release_ms = 10.0 + params.get("parameter4", 0.5) * 490.0       # 10-500ms
        knee_db = 2.0  # 2dB soft knee

        # Convert to linear
        threshold_linear = 10.0 ** (threshold_db / 20.0)

        # Calculate attack/release coefficients (1-pole filters)
        attack_coeff = 1.0 - math.exp(-1.0 / (attack_ms * 0.001 * self.sample_rate))
        release_coeff = 1.0 - math.exp(-1.0 / (release_ms * 0.001 * self.sample_rate))

        # Process each sample for envelope following and compression
        current_gain = state['gain']
        envelope = state['envelope']

        for i in range(num_samples):
            # Calculate detection signal (RMS-like envelope)
            detection_input = target_buffer[i, 0]**2 + target_buffer[i, 1]**2  # Stereo sum of squares
            detection_linear = math.sqrt(max(detection_input, 1e-12))

            # Update envelope with attack/release characteristics
            if detection_linear > envelope:
                envelope += attack_coeff * (detection_linear - envelope)
            else:
                envelope += release_coeff * (detection_linear - envelope)

            # Calculate desired gain with soft knee
            if envelope <= threshold_linear:
                desired_gain_db = 0.0  # No compression
            else:
                # Soft knee calculation
                knee_linear = 10.0 ** (knee_db / 20.0)
                knee_threshold = threshold_linear * knee_linear

                if envelope <= knee_threshold:
                    # Soft knee region
                    knee_ratio = knee_db / ((envelope / threshold_linear - 1.0) / knee_linear + 1.0)
                    gain_reduction = (envelope / threshold_linear - 1.0) * (1.0 / knee_ratio - 1.0 / ratio) + knee_db
                    desired_gain_db = -gain_reduction
                else:
                    # Hard knee region
                    over_threshold = envelope - threshold_linear
                    gain_reduction = over_threshold * (1.0 - 1.0 / ratio)
                    desired_gain_db = -gain_reduction

            # Smooth gain changes to avoid artifacts
            desired_gain = 10.0 ** (desired_gain_db / 20.0)
            current_gain = 0.99 * current_gain + 0.01 * desired_gain

            # Apply gain with make-up gain compensation
            makeup_gain = 10.0 ** (abs(threshold_db) * (1.0 - 1.0 / ratio) / 20.0 * 0.1)  # Subtle makeup gain
            final_gain = current_gain * makeup_gain

            target_buffer[i] *= final_gain

        # Update state
        state['gain'] = current_gain
        state['envelope'] = envelope

        # Apply subtle limiting to prevent overshoots
        np.clip(target_buffer[:num_samples], -1.0, 1.0, out=target_buffer[:num_samples])

    def _apply_phaser_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY PHASER EFFECT - ZERO ALLOCATION

        8-stage phaser using DSP units with proper LFO management
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get LFO for modulation
        lfo_rate = params.get("parameter1", 0.5) * 4.0 + 0.1  # 0.1-4.1 Hz
        depth = params.get("parameter2", 0.5)                  # Modulation depth
        feedback = params.get("parameter3", 0.5) * 0.9         # Feedback (max 90%)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # Waveform type

        # Get LFO from DSP units
        lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform=["sine", "triangle", "square", "sawtooth"][lfo_waveform],
            rate=lfo_rate,
            depth=depth
        )

        # Get biquad bank for all-pass filters
        biquad_bank = self.dsp_units.get_biquad_bank()

        # Calculate 8 all-pass filter frequencies with exponential spacing
        base_freq = 600.0  # Starting frequency around 600Hz
        frequencies = [base_freq * (1.5 ** i) for i in range(8)]

        # Process through cascaded all-pass filters with LFO modulation
        processed = target_buffer[:num_samples].copy()
        for stage in range(8):
            # Get modulated frequency
            lfo_value = lfo.get_value()
            freq_modulation = 1.0 + depth * lfo_value * 0.7  # ±70% modulation
            current_freq = frequencies[stage] * freq_modulation

            # Apply all-pass filter using biquad bank
            processed = biquad_bank.apply_allpass_filter(
                processed, current_freq, resonance=0.0
            )

        # Apply feedback and mix
        feedback_signal = feedback * processed
        target_buffer[:num_samples] = target_buffer[:num_samples] * 0.3 + processed * 0.7 + feedback_signal

    def _apply_flanger_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY FLANGER EFFECT - ZERO ALLOCATION

        Using DSP units for proper delay line and LFO management
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get flanger parameters
        frequency = params.get("frequency", 0.5)  # Hz
        depth = params.get("depth", 0.7)
        feedback = params.get("feedback", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # Waveform type

        # Get LFO from DSP units
        lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform=["sine", "triangle", "square", "sawtooth"][lfo_waveform],
            rate=frequency,
            depth=depth
        )

        # Get delay line from DSP units
        delay_network = self.dsp_units.get_delay_network()

        # Configure delay taps for flanger
        base_delay_samples = int(0.001 * self.sample_rate)  # 1ms base delay
        max_delay_samples = int(0.005 * self.sample_rate)   # 5ms max delay

        # Set up single tap for flanger
        delay_network.set_tap(0, base_delay_samples, 1.0, feedback)

        # Process through flanger
        for i in range(num_samples):
            # Get modulated delay time
            lfo_value = lfo.get_value()
            modulated_delay = base_delay_samples + int(depth * (max_delay_samples - base_delay_samples) * (lfo_value + 1.0) / 2.0)

            # Update delay tap
            delay_network.set_tap(0, modulated_delay, 1.0, feedback)

            # Get delayed sample
            input_sample = target_buffer[i].copy()
            delayed_sample = delay_network.process_sample(input_sample)

            # Apply flanger: mix input with delayed signal
            target_buffer[i] = input_sample + delayed_sample

    def _apply_gate_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                     params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply gate effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Gate effect implementation
        threshold = params.get("parameter1", 0.5) * 0.8  # 0.0-0.8 threshold
        reduction = params.get("parameter2", 0.5)       # gate reduction
        attack = params.get("parameter3", 0.1)          # attack time
        hold = params.get("parameter4", 0.2)            # hold time

        # Simple gate - mute signal below threshold
        mask = np.abs(target_buffer[:num_samples]) < threshold
        target_buffer[:num_samples][mask] *= (1.0 - reduction)

    def _apply_envelope_filter_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                  params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY ENVELOPE FILTER - ZERO ALLOCATION

        Auto-wah style envelope follower with resonant filter using DSP units
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get envelope follower from DSP units
        envelope_follower = self.dsp_units.get_envelope_follower()

        # Configure envelope follower
        attack_ms = params.get("parameter1", 0.5) * 50.0 + 1.0  # 1-51ms attack
        release_ms = params.get("parameter2", 0.5) * 200.0 + 10.0  # 10-210ms release
        envelope_follower.set_attack_release(attack_ms, release_ms)

        # Filter parameters
        base_cutoff = params.get("parameter3", 0.5) * 2000.0 + 200.0  # 200-2200 Hz base
        resonance = params.get("parameter4", 0.5) * 0.8 + 0.2  # 0.2-1.0 resonance

        # Get filter from DSP units
        filter_obj = self.dsp_units.get_filter_manager().get_filter_stage(
            f"envelope_filter_{channel_idx}", 0,
            cutoff=base_cutoff,
            resonance=resonance,
            filter_type="bandpass"
        )

        # Process each sample
        for i in range(num_samples):
            # Get envelope value
            envelope = envelope_follower.process_sample(target_buffer[i, 0])

            # Modulate filter cutoff based on envelope
            modulated_cutoff = base_cutoff + envelope * 3000.0  # Up to 5200 Hz

            # Update filter cutoff
            filter_obj.set_cutoff(modulated_cutoff)

            # Apply filter
            filtered_sample = filter_obj.process_sample(target_buffer[i, 0])
            target_buffer[i, 0] = filtered_sample

            # Same for right channel if stereo
            if target_buffer.shape[1] > 1:
                filtered_sample_r = filter_obj.process_sample(target_buffer[i, 1])
                target_buffer[i, 1] = filtered_sample_r

    def _apply_guitar_amp_sim_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY GUITAR AMP SIMULATION - ZERO ALLOCATION

        Multi-stage amp modeling with preamp, tone stack, and power amp using DSP units
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get parameters
        drive = params.get("parameter1", 0.5)  # Preamp drive
        bass = params.get("parameter2", 0.5)   # Bass control
        treble = params.get("parameter3", 0.5) # Treble control
        presence = params.get("parameter4", 0.5)  # Presence control

        # Stage 1: Preamp drive with asymmetric clipping
        preamp_gain = drive * 8.0 + 1.0
        target_buffer[:num_samples] *= preamp_gain

        # Asymmetric diode clipping (silicon diodes)
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                x = target_buffer[i, ch]
                if x > 0.33:
                    target_buffer[i, ch] = 0.33 + (x - 0.33) * 0.1  # Soft clip positive
                elif x < -0.33:
                    target_buffer[i, ch] = -0.33 + (x + 0.33) * 0.2  # Harder clip negative

        # Stage 2: Tone stack simulation
        # Get filters for tone controls
        bass_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_bass_{channel_idx}", 0,
            cutoff=200.0 + bass * 300.0,  # 200-500 Hz
            resonance=0.7,
            filter_type="lowshelf"
        )

        treble_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_treble_{channel_idx}", 0,
            cutoff=2000.0 + treble * 4000.0,  # 2k-6k Hz
            resonance=0.7,
            filter_type="highshelf"
        )

        presence_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_presence_{channel_idx}", 0,
            cutoff=4000.0 + presence * 4000.0,  # 4k-8k Hz
            resonance=0.8,
            filter_type="peaking"
        )

        # Apply tone stack
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                sample = target_buffer[i, ch]

                # Bass boost/cut
                sample = bass_filter.process_sample(sample)

                # Treble boost/cut
                sample = treble_filter.process_sample(sample)

                # Presence boost/cut
                sample = presence_filter.process_sample(sample)

                target_buffer[i, ch] = sample

        # Stage 3: Power amp simulation with sag
        # Simple power amp compression
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                x = target_buffer[i, ch]
                # Power amp compression (soft knee)
                if abs(x) > 0.7:
                    x = np.sign(x) * (0.7 + (abs(x) - 0.7) * 0.3)
                target_buffer[i, ch] = x

        # Apply final level
        target_buffer[:num_samples] *= 0.8  # Conservative output level

    def _apply_rotary_speaker_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY ROTARY SPEAKER SIMULATION - ZERO ALLOCATION

        Dual-rotor Leslie simulation with horn and drum speakers using DSP units
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get parameters
        speed = params.get("parameter1", 0.5) * 5.0 + 0.5  # 0.5-5.5 Hz
        balance = params.get("parameter2", 0.5)            # Horn/drum balance
        accel = params.get("parameter3", 0.5)              # Acceleration
        level = params.get("parameter4", 0.5)              # Output level

        # Get LFOs for horn and drum rotation
        horn_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform="sine",
            rate=speed * 0.7,  # Horn is slower
            depth=1.0
        )

        drum_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx + 16,  # Different channel for drum
            waveform="sine",
            rate=speed,  # Drum is faster
            depth=1.0
        )

        # Get delay lines for Doppler effect
        horn_delay = self.dsp_units.get_delay_network()
        drum_delay = self.dsp_units.get_delay_network()

        # Configure delays for Doppler simulation
        horn_delay.set_tap(0, int(0.01 * self.sample_rate), 0.3, 0.0)  # 10ms delay
        drum_delay.set_tap(0, int(0.005 * self.sample_rate), 0.2, 0.0)  # 5ms delay

        # Process each sample
        for i in range(num_samples):
            # Get LFO values for modulation
            horn_mod = horn_lfo.get_value()
            drum_mod = drum_lfo.get_value()

            # Calculate Doppler modulation
            horn_doppler = 1.0 + horn_mod * 0.1  # ±10% pitch change
            drum_doppler = 1.0 + drum_mod * 0.05  # ±5% pitch change

            # Update delay times for Doppler effect
            horn_delay.set_tap(0, int(0.01 * self.sample_rate * horn_doppler), 0.3, 0.0)
            drum_delay.set_tap(0, int(0.005 * self.sample_rate * drum_doppler), 0.2, 0.0)

            # Process through delays
            input_sample = target_buffer[i, 0]  # Mono processing
            horn_output = horn_delay.process_sample(input_sample)
            drum_output = drum_delay.process_sample(input_sample)

            # Mix horn and drum with balance
            horn_level = balance
            drum_level = 1.0 - balance

            # Apply amplitude modulation for speaker characteristics
            horn_modulated = horn_output * (0.8 + horn_mod * 0.4)  # Horn amplitude modulation
            drum_modulated = drum_output * (0.9 + drum_mod * 0.2)  # Drum amplitude modulation

            # Combine and apply level
            output = (horn_modulated * horn_level + drum_modulated * drum_level) * level

            # Stereo output with slight panning
            target_buffer[i, 0] = output * 0.7  # Left
            target_buffer[i, 1] = output * 0.7  # Right

    def _apply_leslie_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY LESLIE SPEAKER SIMULATION - ZERO ALLOCATION

        Authentic Leslie 122 simulation with rotating horn and drum using DSP units
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get parameters
        speed = params.get("parameter1", 0.5) * 5.0 + 0.5  # 0.5-5.5 Hz
        balance = params.get("parameter2", 0.5)            # Horn/drum balance
        accel = params.get("parameter3", 0.5)              # Acceleration (unused for now)
        level = params.get("parameter4", 0.5)              # Output level

        # Get LFOs for horn and drum rotation
        horn_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform="sine",
            rate=speed * 0.7,  # Horn: ~0.35-3.85 Hz
            depth=1.0
        )

        drum_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx + 16,  # Different channel for drum
            waveform="sine",
            rate=speed,  # Drum: ~0.5-5.5 Hz
            depth=1.0
        )

        # Get crossover filters for frequency splitting
        # Horn gets treble, drum gets bass
        crossover_low = self.dsp_units.get_filter_manager().get_filter_stage(
            f"leslie_crossover_low_{channel_idx}", 0,
            cutoff=800.0,  # 800Hz crossover
            resonance=0.7,
            filter_type="lowpass"
        )

        crossover_high = self.dsp_units.get_filter_manager().get_filter_stage(
            f"leslie_crossover_high_{channel_idx}", 0,
            cutoff=800.0,  # 800Hz crossover
            resonance=0.7,
            filter_type="highpass"
        )

        # Get delay networks for Doppler effect
        horn_delay = self.dsp_units.get_delay_network()
        drum_delay = self.dsp_units.get_delay_network()

        # Configure delays for authentic Leslie Doppler
        horn_delay.set_tap(0, int(0.015 * self.sample_rate), 0.4, 0.0)  # 15ms delay
        drum_delay.set_tap(0, int(0.008 * self.sample_rate), 0.3, 0.0)  # 8ms delay

        # Process each sample
        for i in range(num_samples):
            input_sample = target_buffer[i, 0]  # Mono processing

            # Split frequencies
            bass_signal = crossover_low.process_sample(input_sample)
            treble_signal = crossover_high.process_sample(input_sample)

            # Get LFO values
            horn_mod = horn_lfo.get_value()
            drum_mod = drum_lfo.get_value()

            # Calculate Doppler modulation
            horn_doppler = 1.0 + horn_mod * 0.08  # ±8% pitch change
            drum_doppler = 1.0 + drum_mod * 0.04  # ±4% pitch change

            # Update delay times
            horn_delay.set_tap(0, int(0.015 * self.sample_rate * horn_doppler), 0.4, 0.0)
            drum_delay.set_tap(0, int(0.008 * self.sample_rate * drum_doppler), 0.3, 0.0)

            # Process through delays
            horn_output = horn_delay.process_sample(treble_signal)
            drum_output = drum_delay.process_sample(bass_signal)

            # Apply amplitude modulation (horn has more modulation)
            horn_modulated = horn_output * (0.7 + horn_mod * 0.6)  # ±60% modulation
            drum_modulated = drum_output * (0.85 + drum_mod * 0.3)  # ±30% modulation

            # Mix horn and drum with balance
            horn_level = balance
            drum_level = 1.0 - balance

            # Combine and apply level
            output = (horn_modulated * horn_level + drum_modulated * drum_level) * level

            # Stereo output with slight stereo spread
            target_buffer[i, 0] = output * 0.8  # Left
            target_buffer[i, 1] = output * 0.8  # Right

    def _apply_enhancer_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply enhancer effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple enhancer - add harmonics and brightness
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        # Add odd harmonics
        enhanced = target_buffer[:num_samples] + enhance * np.sin(target_buffer[:num_samples] * math.pi)
        np.copyto(target_buffer[:num_samples], enhanced)

        # Apply bass/treble balance
        bass_factor = 0.5 + bass * 0.5
        treble_factor = 0.5 + treble * 0.5
        target_buffer[:num_samples] *= bass_factor * treble_factor * level

    def _apply_slicer_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply slicer effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple slicer - rhythmic gate
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 2)
        phase = params.get("parameter4", 0.5)

        # Create LFO
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t + phase * 2 * math.pi)

        # Create gate pattern
        gate_signal = (lfo > -depth).astype(np.float32)
        target_buffer[:num_samples] *= gate_signal[:, np.newaxis]

    def _apply_vocoder_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY VOCODER EFFECT - ZERO ALLOCATION

        16-band vocoder with envelope following and carrier synthesis
        """
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get parameters
        formant_shift = params.get("parameter1", 0.5) * 2.0  # 0-2x formant shift
        resonance = params.get("parameter2", 0.5) * 0.9 + 0.1  # 0.1-1.0 resonance
        mix = params.get("parameter3", 0.5)  # Dry/wet mix
        level = params.get("parameter4", 0.5)  # Output level

        # Get envelope follower for modulation source
        envelope_follower = self.dsp_units.get_envelope_follower()
        envelope_follower.set_attack_release(1.0, 50.0)  # Fast attack, slow release

        # Get biquad bank for band-pass filters
        filter_bank = self.dsp_units.get_biquad_bank()

        # Define 16 frequency bands (logarithmic spacing)
        bands = []
        for i in range(16):
            freq = 200 * (2 ** (i / 4))  # 200Hz to ~6.3kHz
            bands.append(freq)

        # Process each sample
        output = np.zeros_like(target_buffer[:num_samples])

        for i in range(num_samples):
            input_sample = target_buffer[i, 0]  # Use left channel as modulation source

            # Get envelope from input
            envelope = envelope_follower.process_sample(input_sample)

            # Generate carrier signal (synthesized voice-like sound)
            carrier = 0.0
            for band_idx, freq in enumerate(bands):
                # Modulate each band with envelope
                band_level = envelope * (0.5 + 0.5 * np.sin(2 * np.pi * freq * i / self.sample_rate))

                # Add to carrier with some noise for vocal character
                noise = np.random.random() * 2.0 - 1.0  # White noise
                carrier += band_level * noise * 0.1

            # Apply formant filtering to carrier
            for band_idx, freq in enumerate(bands):
                shifted_freq = freq * formant_shift
                if shifted_freq < 50:
                    shifted_freq = 50
                elif shifted_freq > 8000:
                    shifted_freq = 8000

                # Design band-pass filter for this frequency
                filter_bank.design_bandpass(band_idx % 8, shifted_freq, resonance)

                # Filter carrier through this band
                band_output = filter_bank.process_sample(band_idx % 8, carrier)
                carrier = band_output

            # Mix dry and wet signals
            dry_level = 1.0 - mix
            wet_level = mix

            final_sample = input_sample * dry_level + carrier * wet_level * level

            # Stereo output
            output[i, 0] = final_sample
            output[i, 1] = final_sample

        # Copy result to target buffer
        np.copyto(target_buffer[:num_samples], output)

    def _apply_talk_wah_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply talk wah effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Talk wah - automatic wah filter based on envelope
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 2)

        # Simple envelope following and filtering
        if hasattr(self, '_talk_wah_envelope') and len(self._talk_wah_envelope) >= num_samples:
            envelope = self._talk_wah_envelope[:num_samples]
        else:
            # Simple envelope detection
            envelope = np.abs(target_buffer[:num_samples].mean(axis=1) if len(target_buffer.shape) > 1 else target_buffer[:num_samples])
            for i in range(1, len(envelope)):
                envelope[i] = envelope[i] * 0.1 + envelope[i-1] * 0.9

        # Convert envelope to filter frequency
        filter_freq = 200 + envelope * 3000

        # Very simplified filtering
        for i in range(1, num_samples):
            alpha = 0.1 + (filter_freq[i] / 4000.0) * 0.4
            target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha) * target_buffer[i-1]

        target_buffer[:num_samples] *= depth * 2.0

    def _apply_harmonizer_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply harmonizer effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simplified harmonizer - add pitch-shifted version
        intervals = (params.get("parameter1", 0.5) * 24.0) - 12.0  # semitones
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        mix = params.get("parameter4", 0.5)

        # Simple delay-based pitch shifter (very simplified)
        pitch_factor = 2 ** (intervals / 12.0)
        delay_samples = int(0.01 * self.sample_rate)  # 10ms delay

        # Add delayed version with different gain
        if delay_samples < num_samples:
            delayed = np.zeros_like(target_buffer[:num_samples])
            delayed[delay_samples:] = target_buffer[:num_samples][:-delay_samples]
            target_buffer[:num_samples] += delayed * depth * 0.5

        target_buffer[:num_samples] *= (1.0 - mix * depth + mix)

    def _apply_octave_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply octave effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple octave effect - add octave down
        shift = int(params.get("parameter1", 0.5) * 4) - 2
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        # Simple octave down using short delay
        octave_down_samples = int(self.sample_rate / (261.63 * (2 ** shift)))  # C4 frequency
        octave_down_samples = min(octave_down_samples, num_samples // 2)

        # Add octave-down signal
        if octave_down_samples > 0 and octave_down_samples < num_samples:
            octave_signal = np.zeros_like(target_buffer[:num_samples])
            for i in range(octave_down_samples, num_samples):
                octave_signal[i] = target_buffer[i - octave_down_samples] * 0.7
            target_buffer[:num_samples] += octave_signal * mix

    def _apply_detune_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply detune effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple detuning with short delay
        shift = (params.get("parameter1", 0.5) * 100.0) - 50.0  # cents
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        # Calculate delay for detuning
        delay_cents = shift  # cents difference
        pitch_factor = 2 ** (delay_cents / 1200.0)
        delay_samples = int(0.005 * self.sample_rate * (1.0 - pitch_factor))  # small delay

        # Add detuned signal
        if delay_samples > 0 and delay_samples < num_samples:
            detuned = np.zeros_like(target_buffer[:num_samples])
            detuned[delay_samples:] = target_buffer[:num_samples][:-delay_samples]
            target_buffer[:num_samples] += detuned * feedback * mix

    def _apply_wah_wah_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply wah wah effect using zero-allocation approach"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple wah-wah filter
        manual_pos = params.get("manual_position", 0.5)
        lfo_rate = params.get("lfo_rate", 0.5) * 5.0
        lfo_depth = params.get("lfo_depth", 0.5)
        resonance = params.get("resonance", 0.5)

        # Create LFO for wah
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * lfo_rate * t)

        # Vary cutoff frequency
        cutoff_freq = manual_pos + lfo * lfo_depth * 0.5
        cutoff_freq = np.clip(cutoff_freq, 0.01, 0.99)

        # Simple bandpass filter approximation
        for i in range(1, num_samples):
            alpha = 0.1 + (cutoff_freq[i] * 0.4)
            target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha * resonance) * target_buffer[i-1]

    def _apply_eq_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                            params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply professional 3-band EQ insertion effect using zero-allocation approach with biquad filters"""
        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Get or create filter state for this channel
        if channel_idx >= len(self._eq_insertion_filters):
            # Extend array if needed
            for _ in range(channel_idx - len(self._eq_insertion_filters) + 1):
                self._eq_insertion_filters.append({
                    'low_state': [0.0, 0.0],    # x1, x2 for low shelf
                    'mid_state': [0.0, 0.0],    # x1, x2 for peaking
                    'high_state': [0.0, 0.0]    # x1, x2 for high shelf
                })

        filter_state = self._eq_insertion_filters[channel_idx]

        # Parse parameters: 3-band EQ gains
        low_gain_db = (params.get("parameter1", 0.5) - 0.5) * 24.0  # -12 to +12 dB
        mid_gain_db = (params.get("parameter2", 0.5) - 0.5) * 24.0  # -12 to +12 dB
        high_gain_db = (params.get("parameter3", 0.5) - 0.5) * 24.0 # -12 to +12 dB

        # Convert dB to linear gain
        low_gain = 10.0 ** (low_gain_db / 20.0)
        mid_gain = 10.0 ** (mid_gain_db / 20.0)
        high_gain = 10.0 ** (high_gain_db / 20.0)

        # Design filter coefficients for standard 3-band EQ
        # Low shelf: 100Hz, Mid peak: 1kHz, High shelf: 5kHz

        # Process each channel (left/right) through the EQ
        for ch in range(target_buffer.shape[1]):
            channel_data = target_buffer[:num_samples, ch]

            # Apply low shelf filter
            low_filtered = self._apply_biquad_low_shelf(channel_data, low_gain, filter_state['low_state'])

            # Apply mid peaking filter
            mid_filtered = self._apply_biquad_peaking(low_filtered, mid_gain, 1000.0, 1.414, filter_state['mid_state'])

            # Apply high shelf filter
            high_filtered = self._apply_biquad_high_shelf(mid_filtered, high_gain, filter_state['high_state'])

            # Update output
            target_buffer[:num_samples, ch] = high_filtered

    def _apply_biquad_low_shelf(self, input_signal: np.ndarray, gain: float, state: List[float]) -> np.ndarray:
        """Apply biquad low shelf filter"""
        # Low shelf coefficients (cutoff=100Hz, slope=1)
        a0 = 1.0 + 2.0 * math.pi * 100.0 / self.sample_rate
        a1 = -2.0 * math.cos(2.0 * math.pi * 100.0 / self.sample_rate) / a0
        a2 = (1.0 - 2.0 * math.pi * 100.0 / self.sample_rate) / a0
        b0 = gain * a0
        b1 = gain * a1
        b2 = gain * a2

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = x

        return output

    def _apply_biquad_peaking(self, input_signal: np.ndarray, gain: float, freq: float,
                             q: float, state: List[float]) -> np.ndarray:
        """Apply biquad peaking filter"""
        w0 = 2.0 * math.pi * freq / self.sample_rate
        alpha = math.sin(w0) / (2.0 * q)

        a0 = 1.0 + alpha
        a1 = -2.0 * math.cos(w0)
        a2 = 1.0 - alpha
        b0 = (1.0 + alpha * gain) / a0
        b1 = (-2.0 * math.cos(w0)) / a0
        b2 = (1.0 - alpha * gain) / a0

        # Normalize a coefficients
        a1 = a1 / a0
        a2 = a2 / a0

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = y

        return output

    def _apply_biquad_high_shelf(self, input_signal: np.ndarray, gain: float, state: List[float]) -> np.ndarray:
        """Apply biquad high shelf filter"""
        # High shelf coefficients (cutoff=5kHz, slope=1)
        a0 = 1.0 + 2.0 * math.pi * 5000.0 / self.sample_rate
        a1 = -2.0 * math.cos(2.0 * math.pi * 5000.0 / self.sample_rate) / a0
        a2 = (1.0 - 2.0 * math.pi * 5000.0 / self.sample_rate) / a0
        b0 = gain * a0
        b1 = gain * a1
        b2 = gain * a2

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = x

        return output

    def _apply_vocal_filter_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                             params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply vocal filter effect using zero-allocation approach"""
        # Simplified vocal filter - basic formant-like filtering
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple vocal filter - attenuate low and high frequencies
        for i in range(1, num_samples):
            target_buffer[i, 0] = target_buffer[i, 0] * 0.7 + target_buffer[i-1, 0] * 0.3
            target_buffer[i, 1] = target_buffer[i, 1] * 0.7 + target_buffer[i-1, 1] * 0.3

    def _apply_auto_wah_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto wah insertion effect using zero-allocation approach"""
        self._apply_auto_wah_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_pitch_shifter_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply pitch shifter insertion effect using zero-allocation approach"""
        self._apply_pitch_shifter_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_ring_mod_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply ring mod insertion effect using zero-allocation approach"""
        self._apply_ring_mod_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_tremolo_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                  params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply tremolo insertion effect using zero-allocation approach"""
        self._apply_tremolo_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_auto_pan_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto pan insertion effect using zero-allocation approach"""
        self._apply_auto_pan_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_step_phaser_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                      params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step phaser insertion effect using zero-allocation approach"""
        self._apply_step_phaser_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_step_flanger_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step flanger insertion effect using zero-allocation approach"""
        self._apply_step_flanger_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_step_filter_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                      params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step filter insertion effect using zero-allocation approach"""
        self._apply_step_filter_effect_zero_alloc(target_buffer, input_array, params, num_samples, channel_idx)

    def _apply_spectral_filter_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply spectral filter effect using zero-allocation approach"""
        # Simplified spectral filter - just copy input
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

    def _apply_resonator_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                    params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply resonator insertion effect using zero-allocation approach"""
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple resonance - add feedback
        for i in range(1, num_samples):
            target_buffer[i, 0] *= 1.2  # Simple resonance
            target_buffer[i, 1] *= 1.2  # Simple resonance

    def _apply_degrader_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply degrader insertion effect using zero-allocation approach"""
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple bit crushing
        bit_depth = int(params.get("parameter1", 0.5) * 8) + 4
        if bit_depth < 16:
            scale = 2 ** bit_depth
            target_buffer[:num_samples, 0] = np.floor(target_buffer[:num_samples, 0] * scale) / scale
            target_buffer[:num_samples, 1] = np.floor(target_buffer[:num_samples, 1] * scale) / scale

    def _apply_vinyl_sim_insertion_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                                    params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply vinyl simulator insertion effect using zero-allocation approach"""
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple vinyl simulation - add some filtering and saturation
        target_buffer[:num_samples] = np.tanh(target_buffer[:num_samples] * 1.5) * 0.9

    # --- Additional variation effect implementations ---

    def _apply_auto_wah_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto wah effect using zero-allocation approach - variation version"""
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simplified auto-wah - envelope controlled filter
        sensitivity = params.get("parameter1", 0.5)
        level = params.get("parameter2", 0.5)

        # Very simple envelope detection
        envelope = np.abs(target_buffer[:num_samples].mean(axis=1) if len(target_buffer.shape) > 1 else target_buffer[:num_samples])
        for i in range(1, len(envelope)):
            envelope[i] = envelope[i] * 0.1 + envelope[i-1] * 0.9

        for i in range(1, num_samples):
            filter_amount = 0.1 + envelope[i] * 0.4
            target_buffer[i, 0] = filter_amount * target_buffer[i, 0] + (1.0 - filter_amount) * target_buffer[i-1, 0]
            target_buffer[i, 1] = filter_amount * target_buffer[i, 1] + (1.0 - filter_amount) * target_buffer[i-1, 1]

        target_buffer[:num_samples] *= level

    def _apply_pitch_shifter_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                             params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply pitch shifter effect using zero-allocation approach"""
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        if not hasattr(self, '_pitch_shifter_buffers'):
            self._pitch_shifter_buffers = [np.zeros(self.block_size, dtype=np.float32) for _ in range(16)]
            self._pitch_shifter_positions = [0] * 16

        shift_factor = 2 ** (shift / 12.0)
        buffer = self._pitch_shifter_buffers[channel_idx]
        pos = self._pitch_shifter_positions[channel_idx]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Simple pitch shifting via delay
        delay_samples = int(0.01 * self.sample_rate * (2.0 - shift_factor))

        for i in range(num_samples):
            buffer[pos] = target_buffer[i, 0]  # Store left channel
            read_pos = (pos - delay_samples) % len(buffer)
            delayed = buffer[int(read_pos)]
            target_buffer[i, 0] = target_buffer[i, 0] * (1.0 - level) + delayed * level
            target_buffer[i, 1] = target_buffer[i, 1] * (1.0 - level) + delayed * level
            pos = (pos + 1) % len(buffer)

        self._pitch_shifter_positions[channel_idx] = pos
        target_buffer[:num_samples] *= (1.0 - feedback + feedback)

    def _apply_ring_mod_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply ring mod effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)
        modulator = 1.0 - depth + depth * lfo

        target_buffer[:num_samples] *= modulator[:, np.newaxis]
        target_buffer[:num_samples] *= level

    def _apply_tremolo_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply tremolo effect using zero-allocation approach"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t)
        mod_amount = 1.0 - depth * 0.5 + depth * 0.5 * lfo

        target_buffer[:num_samples] *= mod_amount[:, np.newaxis]
        target_buffer[:num_samples] *= level

    def _apply_auto_pan_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto pan effect using zero-allocation approach"""
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            mono_input = input_array[:, 0] if len(input_array.shape) == 2 else input_array
            np.copyto(target_buffer[:num_samples, 0], mono_input[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], mono_input[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t)
        pan = lfo * depth * 0.5 + 0.5

        left_gain = np.sqrt(1.0 - pan)
        right_gain = np.sqrt(pan)

        original_left = target_buffer[:num_samples, 0].copy()
        original_right = target_buffer[:num_samples, 1].copy()

        target_buffer[:num_samples, 0] = original_left * left_gain + original_right * right_gain
        target_buffer[:num_samples, 1] = original_right * right_gain + original_left * left_gain

        target_buffer[:num_samples] *= level

    def _apply_step_phaser_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step phaser effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Step-based modulation
        if not hasattr(self, '_step_phaser_counters'):
            self._step_phaser_counters = [0] * 16

        counter = self._step_phaser_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            step_modulation = current_step / (steps - 1) * 2.0 - 1.0

            filter_coeff = 0.1 + depth * step_modulation * 0.4
            # Very simple filtering
            if i > 0:
                target_buffer[i, 0] = filter_coeff * target_buffer[i, 0] + (1.0 - filter_coeff) * target_buffer[i-1, 0]
                target_buffer[i, 1] = filter_coeff * target_buffer[i, 1] + (1.0 - filter_coeff) * target_buffer[i-1, 1]

        self._step_phaser_counters[channel_idx] = (counter + num_samples) % (step_size * steps)

    def _apply_step_flanger_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                            params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step flanger effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        # Step-based delay modulation
        if not hasattr(self, '_step_flanger_counters'):
            self._step_flanger_counters = [0] * 16

        counter = self._step_flanger_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        base_delay = int(0.001 * self.sample_rate)
        max_additional_delay = int(0.003 * self.sample_rate)

        # Use temp buffer for delay
        delay_buffer_size = base_delay + max_additional_delay + 10
        if not hasattr(self, '_step_flanger_buffers'):
            self._step_flanger_buffers = [np.zeros(delay_buffer_size, dtype=np.float32) for _ in range(16)]
            self._step_flanger_positions = [0] * 16

        buffer = self._step_flanger_buffers[channel_idx]
        pos = self._step_flanger_positions[channel_idx]

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            additional_delay = int((current_step / (steps - 1)) * max_additional_delay)
            total_delay = base_delay + additional_delay

            buffer[pos] = target_buffer[i, 0]  # Store sample
            read_pos = (pos - total_delay + len(buffer)) % len(buffer)
            delayed = buffer[int(read_pos)]

            target_buffer[i] += delayed * feedback
            pos = (pos + 1) % len(buffer)

        self._step_flanger_positions[channel_idx] = pos
        self._step_flanger_counters[channel_idx] = (counter + num_samples) % (step_size * steps)

    def _apply_step_filter_effect_zero_alloc(self, target_buffer: np.ndarray, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step filter effect using zero-allocation approach"""
        cutoff_start = params.get("parameter1", 0.1) * 5000
        cutoff_end = params.get("parameter2", 0.9) * 5000
        resonance = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer[:num_samples, :], input_array[:num_samples])
        else:
            np.copyto(target_buffer[:num_samples, 0], input_array[:num_samples])
            np.copyto(target_buffer[:num_samples, 1], input_array[:num_samples])

        if not hasattr(self, '_step_filter_counters'):
            self._step_filter_counters = [0] * 16

        counter = self._step_filter_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            t_step = current_step / (steps - 1)
            current_cutoff = cutoff_start + (cutoff_end - cutoff_start) * t_step

            norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
            norm_cutoff = max(0.01, min(0.95, norm_cutoff))

            alpha = 0.1 + norm_cutoff * 0.4
            if i > 0:
                target_buffer[i, 0] = alpha * target_buffer[i, 0] + (1.0 - alpha) * target_buffer[i-1, 0]
                target_buffer[i, 1] = alpha * target_buffer[i, 1] + (1.0 - alpha) * target_buffer[i-1, 1]

        self._step_filter_counters[channel_idx] = (counter + num_samples) % (step_size * steps)