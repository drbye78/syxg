"""
XG Variation Effects Implementation

This module implements the 15 XG Variation effect types including
advanced choruses, flanging, phasing, modulation, and filter effects.

XG Variation Effects (MSB 3, LSB 0-14):
0: Chorus 1     - Classic chorus with depth control
1: Chorus 2     - Alternative chorus settings
2: Chorus 3     - Another chorus variation
3: Chorus 4     - Chorus with different modulation
4: Celeste 1    - Chorus with inverted channel
5: Celeste 2    - Alternative celeste settings
6: Flanger 1    - Standard flanging effect
7: Flanger 2    - Alternative flanging parameters
8: Phaser 1     - All-pass filter phasing
9: Phaser 2     - Alternative phaser settings
10: Auto Wah    - Envelope-followed filter sweep
11: Rotary Speaker - Rotary speaker simulation
12: Tremolo     - Amplitude modulation
13: Delay LCR   - Left-center-right delay
14: Delay LR    - Left-right delay

Copyright (c) 2025
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import math
from enum import Enum


class XGVariationType(Enum):
    """XG Variation Effect Types"""
    CHORUS_1 = 0
    CHORUS_2 = 1
    CHORUS_3 = 2
    CHORUS_4 = 3
    CELESTE_1 = 4
    CELESTE_2 = 5
    FLANGER_1 = 6
    FLANGER_2 = 7
    PHASER_1 = 8
    PHASER_2 = 9
    AUTO_WAH = 10
    ROTARY_SPEAKER = 11
    TREMOLO = 12
    DELAY_LCR = 13
    DELAY_LR = 14


class XGChorusVariation:
    """
    XG Chorus Variation Effect

    Enhanced chorus implementation with multiple algorithms:
    - Independent LFOs for left/right channels
    - Feedback control for richer sound
    - Multiple depth and rate combinations
    """

    def __init__(self, sample_rate: int = 44100, variation_type: XGVariationType = XGVariationType.CHORUS_1):
        self.sample_rate = sample_rate
        self.variation_type = variation_type

        # Chorus parameters
        self.rate = 0.5          # LFO rate (Hz)
        self.depth = 0.5         # Modulation depth
        self.feedback = 0.0      # Feedback amount
        self.send_level = 0.3    # Send level

        # Initialize based on variation type
        self._set_variation_parameters()

        # Dual LFO for stereo chorus
        self.lfo_phase_left = 0.0
        self.lfo_phase_right = 0.0
        self.lfo_increment = 2.0 * np.pi * self.rate / sample_rate

        # Delay lines for chorus
        max_delay_samples = int(0.05 * sample_rate)  # 50ms max delay
        self.delay_line_left = np.zeros(max_delay_samples, dtype=np.float32)
        self.delay_line_right = np.zeros(max_delay_samples, dtype=np.float32)
        self.write_ptr = 0

    def _set_variation_parameters(self):
        """Set parameters based on XG variation type"""
        params = {
            XGVariationType.CHORUS_1:   {'rate': 0.5, 'depth': 0.5, 'feedback': 0.0},
            XGVariationType.CHORUS_2:   {'rate': 1.0, 'depth': 0.7, 'feedback': 0.2},
            XGVariationType.CHORUS_3:   {'rate': 0.3, 'depth': 0.6, 'feedback': 0.0},
            XGVariationType.CHORUS_4:   {'rate': 1.5, 'depth': 0.4, 'feedback': 0.1},
            XGVariationType.CELESTE_1:  {'rate': 0.3, 'depth': 0.4, 'feedback': -0.3},
            XGVariationType.CELESTE_2:  {'rate': 0.4, 'depth': 0.6, 'feedback': -0.4},
        }

        if self.variation_type in params:
            p = params[self.variation_type]
            self.rate = p['rate']
            self.depth = p['depth']
            self.feedback = p['feedback']

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """Process chorus variation for a block of samples"""
        if self.send_level <= 0.0:
            return

        block_size = len(input_left)
        delay_size = len(self.delay_line_left)

        # Generate modulation for this block (stereo-phased LFOs)
        lfo_mod_left = np.zeros(block_size, dtype=np.float32)
        lfo_mod_right = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Left channel LFO
            lfo_mod_left[i] = 0.5 * (1.0 + np.sin(self.lfo_phase_left))
            self.lfo_phase_left += self.lfo_increment
            if self.lfo_phase_left >= 2.0 * np.pi:
                self.lfo_phase_left -= 2.0 * np.pi

            # Right channel LFO (180 degrees out of phase for celeste effects)
            phase_offset = np.pi if self.variation_type in [XGVariationType.CELESTE_1, XGVariationType.CELESTE_2] else 0.0
            lfo_mod_right[i] = 0.5 * (1.0 + np.sin(self.lfo_phase_right + phase_offset))
            self.lfo_phase_right += self.lfo_increment
            if self.lfo_phase_right >= 2.0 * np.pi:
                self.lfo_phase_right -= 2.0 * np.pi

        # Base delay times (in samples)
        base_delay_left = 15 + 20 * (1.0 - self.depth)   # 15-35 samples
        base_delay_right = base_delay_left  # Same for most choruses

        # Process left channel
        for i in range(block_size):
            # Calculate modulated delay
            mod_delay = lfo_mod_left[i] * 15.0  # ±7.5 samples modulation
            delay_samples = base_delay_left + mod_delay
            delay_samples = max(5, min(delay_samples, delay_size - 2))

            # Interpolate delayed sample
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            # Get delayed samples with interpolation
            sample1 = self.delay_line_left[(self.write_ptr - delay_int) % delay_size]
            sample2 = self.delay_line_left[(self.write_ptr - delay_int - 1) % delay_size]
            delayed_sample = sample1 + delay_frac * (sample2 - sample1)

            # Apply feedback to input
            feedback_sample = delayed_sample * self.feedback
            input_with_fb = input_left[i] + feedback_sample

            # Store in delay line
            self.delay_line_left[self.write_ptr] = input_with_fb

            # Mix dry and wet
            dry_level = 1.0 - self.send_level * 0.5
            wet_level = self.send_level * 0.5
            output_left[i] = input_left[i] * dry_level + delayed_sample * wet_level

        # Process right channel (similar, but celeste uses inverted feedback)
        fb_polarity = -1.0 if self.variation_type in [XGVariationType.CELESTE_1, XGVariationType.CELESTE_2] else 1.0

        for i in range(block_size):
            # Calculate modulated delay
            mod_delay = lfo_mod_right[i] * 15.0
            delay_samples = base_delay_right + mod_delay
            delay_samples = max(5, min(delay_samples, delay_size - 2))

            # Interpolate delayed sample
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            sample1 = self.delay_line_right[(self.write_ptr - delay_int) % delay_size]
            sample2 = self.delay_line_right[(self.write_ptr - delay_int - 1) % delay_size]
            delayed_sample = sample1 + delay_frac * (sample2 - sample1)

            # Apply feedback (inverted for celeste)
            feedback_sample = delayed_sample * self.feedback * fb_polarity
            input_with_fb = input_right[i] + feedback_sample

            # Store in delay line
            self.delay_line_right[self.write_ptr] = input_with_fb

            # Mix dry and wet
            dry_level = 1.0 - self.send_level * 0.5
            wet_level = self.send_level * 0.5
            output_right[i] = input_right[i] * dry_level + delayed_sample * wet_level

            # Update write pointer
            self.write_ptr = (self.write_ptr + 1) % delay_size


class XGFlangerVariation:
    """
    XG Flanger Effect Implementation

    Through-zero flanging with feedback control, featuring:
    - Low-frequency modulation of delay time
    - Negative feedback for through-zero flanging
    - Two variation settings for different modulation rates
    """

    def __init__(self, sample_rate: int = 44100, variation_type: XGVariationType = XGVariationType.FLANGER_1):
        self.sample_rate = sample_rate
        self.variation_type = variation_type

        # Flanger parameters
        self.rate = 0.1          # LFO rate (Hz) - slower than chorus
        self.depth = 0.7         # Deeper modulation for flanging
        self.feedback = 0.7      # Higher feedback for prominent flanging
        self.send_level = 0.4    # Slightly higher send level

        self._set_variation_parameters()

        # LFO for flanging
        self.lfo_phase = 0.0
        self.lfo_increment = 2.0 * np.pi * self.rate / sample_rate

        # Delay line for through-zero flanging
        max_delay_samples = int(0.01 * sample_rate)  # 10ms max delay (shorter than chorus)
        self.delay_line = np.zeros(max_delay_samples, dtype=np.float32)
        self.write_ptr = 0

    def _set_variation_parameters(self):
        """Set parameters based on XG variation type"""
        if self.variation_type == XGVariationType.FLANGER_1:
            self.rate = 0.1
            self.depth = 0.7
            self.feedback = 0.7
        elif self.variation_type == XGVariationType.FLANGER_2:
            self.rate = 0.2
            self.depth = 0.9
            self.feedback = 0.9

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """Process flanger effect for a block of samples"""
        if self.send_level <= 0.0:
            return

        block_size = len(input_left)
        delay_size = len(self.delay_line)

        # Generate LFO modulation for this block
        lfo_mod = np.zeros(block_size, dtype=np.float32)
        for i in range(block_size):
            lfo_mod[i] = np.sin(self.lfo_phase)
            self.lfo_phase += self.lfo_increment
            if self.lfo_phase >= 2.0 * np.pi:
                self.lfo_phase -= 2.0 * np.pi

        # Base delay time (around 1-2ms for through-zero flanging)
        base_delay = 2.0 + 3.0 * (1.0 - self.depth)
        delay_modulation = 3.0 * self.depth

        # Convert to mono for flanging (stereo input becomes mono signal)
        mono_input = (input_left + input_right) * 0.5

        # Process flanger on mono signal, then expand to stereo
        mono_output = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # Calculate modulated delay (through-zero flanging uses full-wave modulation)
            mod_delay = lfo_mod[i] * delay_modulation
            delay_samples = base_delay + mod_delay
            delay_samples = max(0.5, min(delay_samples, delay_size - 2))

            # Interpolate delayed sample
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            sample1 = self.delay_line[(self.write_ptr - delay_int) % delay_size]
            sample2 = self.delay_line[(self.write_ptr - delay_int - 1) % delay_size]
            delayed_sample = sample1 + delay_frac * (sample2 - sample1)

            # Through-zero flanging: add feedback to input
            feedback_sample = delayed_sample * self.feedback
            input_with_fb = mono_input[i] - feedback_sample  # Subtractive feedback for through-zero

            # Store in delay line
            self.delay_line[self.write_ptr] = input_with_fb

            # Wet output (mono flanging)
            dry_level = 1.0 - self.send_level
            wet_level = self.send_level
            mono_output[i] = mono_input[i] * dry_level + delayed_sample * wet_level

            self.write_ptr = (self.write_ptr + 1) % delay_size

        # Expand mono to stereo output
        output_left[:] = mono_output
        output_right[:] = mono_output

    def set_parameters(self, rate: float = None, depth: float = None,
                      feedback: float = None, send_level: float = None):
        """Set flanger parameters"""
        if rate is not None:
            self.rate = max(0.05, min(5.0, rate))
            self.lfo_increment = 2.0 * np.pi * self.rate / self.sample_rate
        if depth is not None:
            self.depth = max(0.0, min(1.0, depth))
        if feedback is not None:
            self.feedback = max(-0.95, min(0.95, feedback))
        if send_level is not None:
            self.send_level = max(0.0, min(1.0, send_level))


class XGPhaserVariation:
    """
    XG Phaser Effect Implementation

    Multi-stage all-pass filter phasing with resonant peaks:
    - Cascaded all-pass filters creating notches and peaks
    - LFO modulation of filter coefficients
    - Feedback control for stronger phasing
    """

    def __init__(self, sample_rate: int = 44100, variation_type: XGVariationType = XGVariationType.PHASER_1):
        self.sample_rate = sample_rate
        self.variation_type = variation_type

        # Phaser parameters
        self.rate = 0.5          # LFO rate
        self.depth = 0.6         # Modulation depth
        self.feedback = 0.5      # Feedback amount
        self.send_level = 0.4    # Send level

        self._set_variation_parameters()

        # LFO for phasing
        self.lfo_phase = 0.0
        self.lfo_increment = 2.0 * np.pi * self.rate / sample_rate

        # All-pass filter stages (4-6 stages typical)
        self.num_stages = 6
        self.allpass_filters = []

        # Initialize all-pass filter delays and coefficients
        for i in range(self.num_stages):
            # Frequency spacing for each stage
            base_freq = 300 + i * 400  # 300Hz, 700Hz, 1100Hz, etc.
            delay_samples = int(sample_rate / (base_freq * 4))  # Quarter-wave delay

            filter_state = {
                'delay_line': np.zeros(delay_samples, dtype=np.float32),
                'write_ptr': 0,
                'prev_output': 0.0
            }
            self.allpass_filters.append(filter_state)

    def _set_variation_parameters(self):
        """Set parameters based on XG variation type"""
        if self.variation_type == XGVariationType.PHASER_1:
            self.rate = 0.5
            self.depth = 0.6
            self.feedback = 0.5
        elif self.variation_type == XGVariationType.PHASER_2:
            self.rate = 1.0
            self.depth = 0.8
            self.feedback = 0.7

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """Process phaser effect for a block of samples"""
        if self.send_level <= 0.0:
            return

        block_size = len(input_left)

        # Generate LFO modulation signal for the whole block
        lfo_values = np.zeros(block_size, dtype=np.float32)
        for i in range(block_size):
            lfo_values[i] = 0.5 * (1.0 + np.sin(self.lfo_phase))
            self.lfo_phase += self.lfo_increment
            if self.lfo_phase >= 2.0 * np.pi:
                self.lfo_phase -= 2.0 * np.pi

        # Process through all-pass filter stages
        # Start with dry signal
        mono_left = input_left.copy()
        mono_right = input_right.copy()

        # Apply phaser to each channel through cascaded all-pass filters
        for channel_idx, input_signal in enumerate([mono_left, mono_right]):
            feedback_signal = 0.0

            for stage_idx, filter_state in enumerate(self.allpass_filters):
                delay_line = filter_state['delay_line']
                delay_size = len(delay_line)
                write_ptr = filter_state['write_ptr']

                for i in range(block_size):
                    # Modulate all-pass coefficient with LFO
                    lfo_mod = 0.3 + 0.4 * lfo_values[i] * self.depth  # 0.3-0.7 range
                    coeff = lfo_mod

                    # All-pass filter: y[n] = x[n] * c + x[n-d] * -c + y[n-d] * c
                    # where c is the modulation coefficient

                    # Read delayed sample
                    read_ptr = (write_ptr - delay_size + 1) % delay_size
                    delayed_sample = delay_line[read_ptr]

                    # All-pass calculation with feedback
                    input_sample = input_signal[i] + feedback_signal * self.feedback
                    output_sample = input_sample * coeff + delayed_sample * (-coeff) + filter_state['prev_output'] * coeff

                    # Store in delay line
                    delay_line[write_ptr] = input_sample

                    # Update state
                    filter_state['prev_output'] = output_sample
                    input_signal[i] = output_sample  # Feed to next stage

                    write_ptr = (write_ptr + 1) % delay_size

                filter_state['write_ptr'] = write_ptr

                # Add feedback from this stage
                feedback_signal += output_sample

        # Mix dry and processed signals
        dry_level = 1.0 - self.send_level
        wet_level = self.send_level

        output_left[:] = input_left * dry_level + mono_left * wet_level
        output_right[:] = input_right * dry_level + mono_right * wet_level

    def set_parameters(self, rate: float = None, depth: float = None,
                      feedback: float = None, send_level: float = None):
        """Set phaser parameters"""
        if rate is not None:
            self.rate = max(0.1, min(5.0, rate))
            self.lfo_increment = 2.0 * np.pi * self.rate / self.sample_rate
        if depth is not None:
            self.depth = max(0.0, min(1.0, depth))
        if feedback is not None:
            self.feedback = max(0.0, min(0.95, feedback))
        if send_level is not None:
            self.send_level = max(0.0, min(1.0, send_level))


class XGAutoWahVariation:
    """
    XG Auto Wah Effect Implementation

    Envelope-followed filter sweep, creating a classic "wah" effect:
    - Amplitude envelope detection
    - Filter sweep based on input level
    - Q control for resonance amount
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.variation_type = XGVariationType.AUTO_WAH

        # Auto-wah parameters
        self.sensitivity = 0.5   # Envelope sensitivity
        self.q = 2.0            # Filter Q/resonance
        self.send_level = 0.6   # Send level

        # State variable filter for wah effect
        self.freq_min = 200     # Minimum wah frequency
        self.freq_max = 2000    # Maximum wah frequency
        self.freq_range = self.freq_max - self.freq_min

        # Envelope follower
        self.envelope = 0.0
        self.attack_coeff = 0.01  # Fast attack
        self.release_coeff = 0.999  # Slow release

        # Filter state (state variable filter)
        self.low = 0.0
        self.band = 0.0
        self.high = 0.0

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """Process auto-wah effect for a block of samples"""
        if self.send_level <= 0.0:
            return

        block_size = len(input_left)

        # Convert stereo to mono for envelope detection
        mono_signal = (input_left + input_right) * 0.5

        for i in range(block_size):
            # Envelope follower
            input_level = abs(mono_signal[i])

            if input_level > self.envelope:
                # Attack
                self.envelope += (input_level - self.envelope) * self.attack_coeff
            else:
                # Release
                self.envelope += (input_level - self.envelope) * self.release_coeff

            # Map envelope to filter frequency
            env_normalized = min(1.0, self.envelope * self.sensitivity * 10.0)
            freq_hz = self.freq_min + env_normalized * self.freq_range

            # Convert frequency to filter coefficient
            # State variable filter coefficient calculation
            f = 2.0 * np.sin(np.pi * freq_hz / self.sample_rate)
            q_factor = 1.0 / self.q

            # State variable filter processing
            input_sample = mono_signal[i]

            self.low = self.low + f * self.band
            self.band = q_factor * f * (input_sample - self.low - self.band) + self.band
            self.high = input_sample - self.low - q_factor * self.band

            # Use bandpass output for wah effect
            wah_output = self.band

            # Mix dry and wet
            dry_level = 1.0 - self.send_level
            wet_level = self.send_level

            # Mono wah to stereo output
            output_left[i] = input_left[i] * dry_level + wah_output * wet_level
            output_right[i] = input_right[i] * dry_level + wah_output * wet_level

    def set_parameters(self, sensitivity: float = None, q: float = None, send_level: float = None):
        """Set auto-wah parameters"""
        if sensitivity is not None:
            self.sensitivity = max(0.0, min(1.0, sensitivity))
        if q is not None:
            self.q = max(0.5, min(10.0, q))
        if send_level is not None:
            self.send_level = max(0.0, min(1.0, send_level))


class XGDelayVariation:
    """
    XG Delay Effects (LCR and LR variants)

    Stereo delay effects with left-center-right or left-right configurations:
    - Independent delay times for each channel
    - Feedback control for multiple repeats
    - High-frequency damping for natural decay
    """

    def __init__(self, sample_rate: int = 44100, variation_type: XGVariationType = XGVariationType.DELAY_LCR):
        self.sample_rate = sample_rate
        self.variation_type = variation_type

        # Delay parameters
        self.delay_time_left = 0.200  # 200ms
        self.delay_time_right = 0.250  # 250ms (LCR) or 300ms (LR)
        self.feedback = 0.4           # Feedback amount
        self.hf_damp = 0.5            # High-frequency damping
        self.send_level = 0.3         # Send level

        self._set_variation_parameters()

        # Initialize delay lines
        max_delay_samples = int(1.0 * sample_rate)  # 1 second maximum
        samples_left = int(self.delay_time_left * sample_rate)
        samples_right = int(self.delay_time_right * sample_rate)

        # Left channel delay line
        self.delay_line_left = np.zeros(max_delay_samples, dtype=np.float32)
        self.write_ptr_left = 0

        # Right channel delay line
        self.delay_line_right = np.zeros(max_delay_samples, dtype=np.float32)
        self.write_ptr_right = 0

        # HF damping filter state
        self.damp_coeff = 0.9 - self.hf_damp * 0.8  # Higher damping -> lower coeff
        self.damp_state_left = 0.0
        self.damp_state_right = 0.0

        # LCR delay (center delay is midpoint between left and right)
        if self.variation_type == XGVariationType.DELAY_LCR:
            center_delay = (self.delay_time_left + self.delay_time_right) / 2.0
            self.delay_time_center = center_delay

            self.delay_line_center = np.zeros(max_delay_samples, dtype=np.float32)
            self.write_ptr_center = 0
            self.damp_state_center = 0.0

            self.center_samples = int(self.delay_time_center * sample_rate)

    def _set_variation_parameters(self):
        """Set parameters based on XG variation type"""
        if self.variation_type == XGVariationType.DELAY_LCR:
            # LCR: Left=200ms, Center=225ms, Right=250ms
            self.delay_time_left = 0.200
            self.delay_time_right = 0.250
            self.feedback = 0.4
        elif self.variation_type == XGVariationType.DELAY_LR:
            # LR: Left=250ms, Right=300ms
            self.delay_time_left = 0.250
            self.delay_time_right = 0.300
            self.feedback = 0.45

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """Process delay effect for a block of samples"""
        if self.send_level <= 0.0:
            return

        block_size = len(input_left)

        # Get delay sample counts
        left_samples = int(self.delay_time_left * self.sample_rate)
        right_samples = int(self.delay_time_right * self.sample_rate)

        left_delay_size = len(self.delay_line_left)

        for i in range(block_size):
            # Process left channel delay
            left_read_pos = (self.write_ptr_left - left_samples) % left_delay_size
            left_delayed = self.delay_line_left[left_read_pos]

            # Apply HF damping to left channel
            left_delayed = left_delayed * self.damp_coeff + self.damp_state_left * (1.0 - self.damp_coeff)
            self.damp_state_left = left_delayed

            # Process right channel delay
            right_read_pos = (self.write_ptr_right - right_samples) % left_delay_size
            right_delayed = self.delay_line_right[right_read_pos]

            # Apply HF damping to right channel
            right_delayed = right_delayed * self.damp_coeff + self.damp_state_right * (1.0 - self.damp_coeff)
            self.damp_state_right = right_delayed

            # Handle LCR vs LR variations
            if self.variation_type == XGVariationType.DELAY_LCR:
                # LCR: Mix center delay with original input
                center_read_pos = (self.write_ptr_center - self.center_samples) % left_delay_size
                center_delayed = self.delay_line_center[center_read_pos]
                center_delayed = center_delayed * self.damp_coeff + self.damp_state_center * (1.0 - self.damp_coeff)
                self.damp_state_center = center_delayed

                # Center goes to both channels (slightly attenuated)
                center_contribution = center_delayed * 0.5
                left_final = left_delayed + center_contribution
                right_final = right_delayed + center_contribution

                # Write center delay line
                center_input = (input_left[i] + input_right[i]) * 0.5 + center_delayed * self.feedback
                self.delay_line_center[self.write_ptr_center] = center_input
                self.write_ptr_center = (self.write_ptr_center + 1) % left_delay_size
            else:
                # LR: Standard stereo delay
                left_final = left_delayed
                right_final = right_delayed

            # Mix dry and wet signals
            dry_level = 1.0 - self.send_level
            wet_level = self.send_level

            output_left[i] = input_left[i] * dry_level + left_final * wet_level
            output_right[i] = input_right[i] * dry_level + right_final * wet_level

            # Write input to delay lines with feedback
            left_fb = input_left[i] + left_delayed * self.feedback
            right_fb = input_right[i] + right_delayed * self.feedback

            self.delay_line_left[self.write_ptr_left] = left_fb
            self.delay_line_right[self.write_ptr_right] = right_fb

            self.write_ptr_left = (self.write_ptr_left + 1) % left_delay_size
            self.write_ptr_right = (self.write_ptr_right + 1) % left_delay_size

    def set_parameters(self, delay_time_left: float = None, delay_time_right: float = None,
                      feedback: float = None, hf_damp: float = None, send_level: float = None):
        """Set delay parameters"""
        if delay_time_left is not None:
            self.delay_time_left = max(0.001, min(1.0, delay_time_left))
        if delay_time_right is not None:
            self.delay_time_right = max(0.001, min(1.0, delay_time_right))
        if feedback is not None:
            self.feedback = max(0.0, min(0.95, feedback))
        if hf_damp is not None:
            self.hf_damp = max(0.0, min(1.0, hf_damp))
            self.damp_coeff = 0.9 - self.hf_damp * 0.8
        if send_level is not None:
            self.send_level = max(0.0, min(1.0, send_level))


class XGVariationEffectProcessor:
    """
    XG Variation Effect Processor

    Manages all 15 XG variation effects and provides a unified interface
    for processing audio through any XG variation effect type.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Current active variation effect
        self.current_variation_type = XGVariationType.CHORUS_1
        self.current_effect = None

        # Effect parameter ranges for XG NRPN control
        self.param_ranges = {
            'rate': (0.05, 5.0),      # LFO/modulation rate
            'depth': (0.0, 1.0),      # Effect depth
            'feedback': (-0.95, 0.95), # Feedback amount
            'send_level': (0.0, 1.0), # Send level
            'sensitivity': (0.0, 1.0), # Envelope sensitivity
            'q_factor': (0.5, 10.0),   # Q/resonance
            'delay_time': (0.001, 1.0), # Delay time in seconds
            'hf_damp': (0.0, 1.0),     # High-frequency damping
        }

        # Initialize with default chorus effect
        self.set_variation_type(self.current_variation_type)

    def set_variation_type(self, variation_type: XGVariationType) -> None:
        """
        Set the current XG variation effect type

        Args:
            variation_type: XG variation effect type to activate
        """
        self.current_variation_type = variation_type

        # Create appropriate effect instance based on type
        if variation_type in [XGVariationType.CHORUS_1, XGVariationType.CHORUS_2,
                             XGVariationType.CHORUS_3, XGVariationType.CHORUS_4,
                             XGVariationType.CELESTE_1, XGVariationType.CELESTE_2]:
            self.current_effect = XGChorusVariation(self.sample_rate, variation_type)
        elif variation_type in [XGVariationType.FLANGER_1, XGVariationType.FLANGER_2]:
            self.current_effect = XGFlangerVariation(self.sample_rate, variation_type)
        elif variation_type in [XGVariationType.PHASER_1, XGVariationType.PHASER_2]:
            self.current_effect = XGPhaserVariation(self.sample_rate, variation_type)
        elif variation_type == XGVariationType.AUTO_WAH:
            self.current_effect = XGAutoWahVariation(self.sample_rate)
        elif variation_type == XGVariationType.TREMOLO:
            # Tremolo would use amplitude modulation effect (not implemented yet)
            self.current_effect = None
        elif variation_type == XGVariationType.ROTARY_SPEAKER:
            # Rotary speaker effect (not implemented yet)
            self.current_effect = None
        elif variation_type in [XGVariationType.DELAY_LCR, XGVariationType.DELAY_LR]:
            self.current_effect = XGDelayVariation(self.sample_rate, variation_type)
        else:
            self.current_effect = None

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """
        Process audio through the current variation effect

        Args:
            input_left: Left channel input
            input_right: Right channel input
            output_left: Left channel output (modified in-place)
            output_right: Right channel output (modified in-place)
        """
        if self.current_effect is None:
            # No effect selected, pass through unchanged
            output_left[:] = input_left
            output_right[:] = input_right
            return

        self.current_effect.process_block(input_left, input_right, output_left, output_right)

    def set_parameter(self, param_name: str, value: float) -> None:
        """
        Set a parameter for the current variation effect

        Args:
            param_name: Parameter name ('rate', 'depth', 'feedback', etc.)
            value: Parameter value (will be clamped to valid range)
        """
        if self.current_effect is None:
            return

        # Clamp parameter value to valid range
        if param_name in self.param_ranges:
            min_val, max_val = self.param_ranges[param_name]
            clamped_value = max(min_val, min(max_val, value))
        else:
            clamped_value = value

        # Map parameter names to effect methods
        if hasattr(self.current_effect, 'set_parameters'):
            if param_name == 'rate':
                self.current_effect.set_parameters(rate=clamped_value)
            elif param_name == 'depth':
                self.current_effect.set_parameters(depth=clamped_value)
            elif param_name == 'feedback':
                self.current_effect.set_parameters(feedback=clamped_value)
            elif param_name == 'send_level':
                self.current_effect.set_parameters(send_level=clamped_value)
            elif param_name == 'sensitivity' and isinstance(self.current_effect, XGAutoWahVariation):
                self.current_effect.set_parameters(sensitivity=clamped_value)
            elif param_name == 'q_factor' and isinstance(self.current_effect, XGAutoWahVariation):
                self.current_effect.set_parameters(q=clamped_value)
            elif 'delay' in param_name and isinstance(self.current_effect, XGDelayVariation):
                if 'left' in param_name:
                    self.current_effect.set_parameters(delay_time_left=clamped_value)
                elif 'right' in param_name:
                    self.current_effect.set_parameters(delay_time_right=clamped_value)
                else:
                    self.current_effect.set_parameters(delay_time_left=clamped_value,
                                                     delay_time_right=clamped_value)

    def get_current_effect_info(self) -> Dict[str, Any]:
        """
        Get information about the currently active variation effect

        Returns:
            Dictionary containing effect type and current parameters
        """
        if self.current_effect is None:
            return {
                'effect_type': None,
                'parameters': {}
            }

        # Extract current parameters from effect instance
        params = {}
        for attr in ['rate', 'depth', 'feedback', 'send_level', 'sensitivity', 'q',
                     'delay_time_left', 'delay_time_right', 'hf_damp']:
            if hasattr(self.current_effect, attr):
                params[attr] = getattr(self.current_effect, attr)

        return {
            'effect_type': self.current_variation_type.name,
            'parameters': params
        }

    def handle_nrpn_variation_parameters(self, nrpn_lsb: int, data_msb: int) -> bool:
        """
        Handle XG variation effect NRPN parameters (MSB 3)

        Args:
            nrpn_lsb: NRPN LSB (parameter type)
            data_msb: Data MSB (parameter value)

        Returns:
            True if parameter was handled, False otherwise
        """
        # NRPN LSB 0: Variation Type Selection
        if nrpn_lsb == 0:
            variation_type = XGVariationType(min(data_msb, 14))  # 0-14 valid
            self.set_variation_type(variation_type)
            return True

        # NRPN LSB 1: Variation Parameter 1 (Rate/Time)
        elif nrpn_lsb == 1:
            # Map 0-127 to parameter range based on effect type
            if isinstance(self.current_effect, (XGChorusVariation, XGFlangerVariation, XGPhaserVariation)):
                rate_hz = 0.05 + (data_msb / 127.0) * 4.95  # 0.05-5.0 Hz
                self.set_parameter('rate', rate_hz)
            elif isinstance(self.current_effect, XGDelayVariation):
                delay_time = 0.001 + (data_msb / 127.0) * 0.999  # 1ms-1sec
                self.set_parameter('delay_time', delay_time)
            return True

        # NRPN LSB 2: Variation Parameter 2 (Depth)
        elif nrpn_lsb == 2:
            depth = data_msb / 127.0  # 0.0-1.0
            self.set_parameter('depth', depth)
            return True

        # NRPN LSB 3: Variation Parameter 3 (Feedback/Modulation)
        elif nrpn_lsb == 3:
            if isinstance(self.current_effect, XGChorusVariation):
                # Chorus feedback: -0.5 to +0.5
                feedback = ((data_msb - 64) / 63.0) * 0.5
                self.set_parameter('feedback', feedback)
            elif isinstance(self.current_effect, (XGFlangerVariation, XGPhaserVariation)):
                # Flanger/phaser feedback: -0.95 to +0.95
                feedback = ((data_msb - 64) / 63.0) * 0.95
                self.set_parameter('feedback', feedback)
            return True

        # NRPN LSB 4: Variation Parameter 4 (Sensitivity/Q)
        elif nrpn_lsb == 4:
            if isinstance(self.current_effect, XGAutoWahVariation):
                sensitivity = data_msb / 127.0
                self.set_parameter('sensitivity', sensitivity)
            # Additional parameters would go here

        return False
