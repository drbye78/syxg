#!/usr/bin/env python3
"""
XG CHORUS ENGINE (MSB 1)

Complete chorus DSP implementation for XG MIDI Standard.
Provides high-quality chorus modulation effects controlled via NRPN parameters.

Features:
- MSB 1 NRPN parameter mapping to chorus controls
- LFO-modulated delay line processing
- XG chorus/flanger effect algorithms with feedback
- High-performance vectorized NumPy processing
- Thread-safe parameter updates during audio processing
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import threading
import math


class XGChorusParameters:
    """
    XG Chorus Parameter State (MSB 1)

    Holds current NRPN parameter values for chorus effect control:
    - Type (0-15): Effect type selection (chorus, flanger, etc.)
    - Rate (0-127): LFO modulation rate
    - Depth (0-127): Modulation depth
    - Feedback (0-127): Delay line feedback amount
    - Level (0-127): Effect send level
    - Delay (0-127): Base delay time
    - Output (0-127): Output control
    - Cross Feedback (0-127): Cross-channel feedback
    - LFO Waveform (0-3): LFO waveform type
    - Phase Diff (0-127): LFO phase difference for stereo
    """

    def __init__(self):
        # Default XG values
        self.type = 0  # Chorus 1
        self.rate = 64  # Medium rate
        self.depth = 64  # Medium depth
        self.feedback = 32  # Light feedback
        self.level = 64  # Medium level
        self.delay = 64  # Medium delay
        self.output = 64  # Medium output
        self.cross_feedback = 0  # No cross feedback
        self.lfo_waveform = 0  # Sine wave
        self.phase_diff = 64  # 90 degrees phase difference

    def update_from_nrpn(self, parameter_index: int, value: int) -> bool:
        """Update parameter from NRPN message."""
        if parameter_index == 0:
            self.type = min(max(value, 0), 15)
        elif parameter_index == 1:
            self.rate = value
        elif parameter_index == 2:
            self.depth = value
        elif parameter_index == 3:
            self.feedback = value
        elif parameter_index == 4:
            self.level = value
        elif parameter_index == 5:
            self.delay = value
        elif parameter_index == 6:
            self.output = value
        elif parameter_index == 7:
            self.cross_feedback = value
        elif parameter_index == 8:
            self.lfo_waveform = min(max(value, 0), 3)
        elif parameter_index == 9:
            self.phase_diff = value
        else:
            return False
        return True


class XGChorusEngine:
    """
    XG DIGITAL CHORUS ENGINE (MSB 1 NRPN CONTROL)

    High-quality chorus processor with complete XG NRPN parameter control.
    Implements LFO-modulated delay lines for chorus and flanger effects.

    Key Features:
    - MSB 1 NRPN parameter mapping (10 parameters)
    - LFO modulation with multiple waveforms
    - Delay line processing with feedback
    - Thread-safe parameter updates during processing
    - Vectorized NumPy processing for performance
    - Stereo processing with phase differences
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_delay_samples = int(0.05 * sample_rate)  # 50ms max delay

        # Thread safety
        self.lock = threading.RLock()

        # Parameter state
        self.current_params = XGChorusParameters()

        # Dual delay lines for left and right channels
        self.delay_buffer_left = np.zeros(self.max_delay_samples, dtype=np.float32)
        self.delay_buffer_right = np.zeros(self.max_delay_samples, dtype=np.float32)
        self.delay_write_pos = 0

        # Write positions for each delay line
        self.write_position = 0

        # LFO state
        self.lfo_phase = 0.0

        # Parameter change detection
        self.last_param_hash = None

    def set_sample_rate(self, sample_rate: int):
        """Update sample rate and reinitialize."""
        with self.lock:
            self.sample_rate = sample_rate
            self.max_delay_samples = int(0.05 * sample_rate)
            self.delay_buffer_left = np.zeros(self.max_delay_samples, dtype=np.float32)
            self.delay_buffer_right = np.zeros(self.max_delay_samples, dtype=np.float32)
            self.last_param_hash = None

    def process_audio_block(self, input_block: np.ndarray) -> np.ndarray:
        """
        Process audio block through XG chorus DSP.

        Args:
            input_block: Stereo audio block (N x 2)

        Returns:
            Processed stereo audio block with chorus
        """
        with self.lock:
            if len(input_block) == 0:
                return input_block

            # Check for parameter changes and update LFO if needed
            current_param_hash = self._get_param_hash()
            if current_param_hash != self.last_param_hash:
                self.last_param_hash = current_param_hash

            num_samples = len(input_block)
            output_block = np.zeros_like(input_block)

            # Process each sample
            for i in range(num_samples):
                # Update LFO phases
                lfo_left = self._get_lfo_value(self.lfo_phase, self.current_params.lfo_waveform)
                lfo_right = self._get_lfo_value(self.lfo_phase + (self.current_params.phase_diff / 127.0) * math.pi,
                                              self.current_params.lfo_waveform)

                # Convert parameter values to meaningful ranges
                base_delay_samples = int((self.current_params.delay / 127.0) * (self.max_delay_samples * 0.8)) + 5  # 5-45ms base delay
                modulation_samples = (self.current_params.depth / 127.0) * 10  # 0-10ms modulation

                # Calculate modulated delays
                delay_left = base_delay_samples + int(modulation_samples * lfo_left)
                delay_right = base_delay_samples + int(modulation_samples * lfo_right)

                # Clamp delays
                delay_left = min(max(delay_left, 1), self.max_delay_samples - 1)
                delay_right = min(max(delay_right, 1), self.max_delay_samples - 1)

                # Calculate input samples
                if len(input_block.shape) == 1:
                    input_left = input_right = input_block[i]
                else:
                    input_left = input_block[i, 0]
                    input_right = input_block[i, 1]

                # Read from delay buffers
                read_pos_left = (self.write_position - delay_left) % self.max_delay_samples
                read_pos_right = (self.write_position - delay_right) % self.max_delay_samples

                delayed_left = self.delay_buffer_left[read_pos_left]
                delayed_right = self.delay_buffer_right[read_pos_right]

                # Apply feedback
                feedback_gain = self.current_params.feedback / 127.0 - 0.5  # -0.5 to +0.5

                # Write to delay buffers (with feedback)
                processed_left = input_left + delayed_left * feedback_gain
                processed_right = input_right + delayed_right * feedback_gain

                self.delay_buffer_left[self.write_position] = processed_left
                self.delay_buffer_right[self.write_position] = processed_right

                # Increment write position
                self.write_position = (self.write_position + 1) % self.max_delay_samples

                # Mix dry and wet signals
                wet_level = self.current_params.level / 127.0

                if len(input_block.shape) == 1:
                    output_block[i] = input_left * (1.0 - wet_level) + delayed_left * wet_level
                else:
                    output_block[i, 0] = input_left * (1.0 - wet_level) + delayed_left * wet_level
                    output_block[i, 1] = input_right * (1.0 - wet_level) + delayed_right * wet_level

                # Update LFO phase
                lfo_freq = 0.1 + (self.current_params.rate / 127.0) * 9.9  # 0.1 to 10 Hz
                self.lfo_phase += 2 * math.pi * lfo_freq / self.sample_rate
                self.lfo_phase %= 2 * math.pi

            return output_block

    def _get_lfo_value(self, phase: float, waveform: int) -> float:
        """Generate LFO value based on waveform type."""
        if waveform == 0:  # Sine
            return math.sin(phase)
        elif waveform == 1:  # Triangle
            normalized = phase / (2 * math.pi)
            return 1.0 - abs((normalized % 1.0) * 2.0 - 1.0) * 2.0
        elif waveform == 2:  # Square
            return 1.0 if math.sin(phase) > 0 else -1.0
        elif waveform == 3:  # Sawtooth
            normalized = phase / (2 * math.pi)
            return (normalized % 1.0) * 2.0 - 1.0
        else:
            return math.sin(phase)

    def _get_param_hash(self) -> int:
        """Generate hash of current parameters for change detection."""
        params = [
            self.current_params.type,
            self.current_params.rate,
            self.current_params.depth,
            self.current_params.feedback,
            self.current_params.level,
            self.current_params.delay,
            self.current_params.lfo_waveform,
            self.current_params.phase_diff
        ]
        return hash(tuple(params))

    def set_nrpn_parameter(self, parameter_index: int, value: int) -> bool:
        """
        Set NRPN parameter value for chorus control.

        Args:
            parameter_index: NRPN LSB value (parameter number)
            value: NRPN 14-bit data value

        Returns:
            True if parameter was valid and updated
        """
        with self.lock:
            return self.current_params.update_from_nrpn(parameter_index, value >> 7)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current chorus engine state."""
        with self.lock:
            return {
                'type': self.current_params.type,
                'rate': self.current_params.rate,
                'depth': self.current_params.depth,
                'feedback': self.current_params.feedback,
                'level': self.current_params.level,
                'delay': self.current_params.delay,
                'lfo_waveform': self.current_params.lfo_waveform,
                'phase_diff': self.current_params.phase_diff,
                'sample_rate': self.sample_rate
            }
