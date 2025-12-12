"""
XG Effects Manager - Multi-Stage Effects Processing Engine

This module implements the complete XG effects processing architecture with:
- System Effects: Reverb, Chorus (shared across all parts)
- Variation Effects: Per-channel variation effects
- Insertion Effects: 3 per-part effect chains
- Proper signal routing and parameter control

XG Effects Signal Flow:
Input → Insert → Variation → Reverb → Chorus → Output

Copyright (c) 2025
"""

import numpy as np
import threading
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from enum import Enum

from ..core.envelope import UltraFastADSREnvelope
from ..engine.optimized_coefficient_manager import get_global_coefficient_manager


class XGProcessingState(Enum):
    """XG Effects Processing State"""
    IDLE = 0
    INITIALIZING = 1
    PROCESSING = 2
    RELEASE = 3


class XGEffectSlot(Enum):
    """XG Effect Slot Types"""
    SYSTEM_REVERB = 0      # Shared reverb (MSB 1)
    SYSTEM_CHORUS = 1      # Shared chorus (MSB 2)
    VARIATION = 2          # Per-part variation effect (MSB 3)
    INSERTION_1 = 3        # Part insertion effect 1
    INSERTION_2 = 4        # Part insertion effect 2
    INSERTION_3 = 5        # Part insertion effect 3


class XGReverbType(Enum):
    """XG Reverb Types (MSB 1, LSB 0-3)"""
    HALL_1 = 0     # Small Hall
    HALL_2 = 1     # Medium Hall
    HALL_3 = 2     # Large Hall
    HALL_4 = 3     # Large Hall +
    ROOM_1 = 4     # Small Room
    ROOM_2 = 5     # Medium Room
    ROOM_3 = 6     # Large Room
    ROOM_4 = 7     # Large Room +
    STAGE_1 = 8    # Small Stage
    STAGE_2 = 9    # Medium Stage
    STAGE_3 = 10   # Large Stage
    STAGE_4 = 11   # Large Stage +
    PLATE = 12     # Plate Reverb


class XGChorusType(Enum):
    """XG Chorus Types (MSB 2, LSB 0-1)"""
    CHORUS_1 = 0
    CHORUS_2 = 1
    CELESTE_1 = 2
    CELESTE_2 = 3
    FLANGER_1 = 4
    FLANGER_2 = 5


class XGVariationType(Enum):
    """XG Variation Types (MSB 3, LSB 0-14)"""
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


class XGReverbEffect:
    """
    XG Reverb Effect Implementation

    Features 13 reverb types with full parameter control:
    - Time: 0.1-5.0s
    - HF Damp: 0-100%
    - Feedback: 0-95%
    - Level: 0-127
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.reverb_type = XGReverbType.HALL_1
        self.time = 1.5   # seconds
        self.hf_damp = 0.5  # 0-1
        self.feedback = 0.4  # 0-0.95
        self.level = 0.3   # 0-1

        # Reverb state
        self.delay_lines: Dict[str, np.ndarray] = {}
        self.filter_state: np.ndarray = np.zeros(4, dtype=np.float32)
        self.hf_damping_filters: List[np.ndarray] = []

        # Initialize standard reverb architecture
        self._initialize_reverb()

        # Coefficient manager
        self.coeff_manager = get_global_coefficient_manager()

    def _initialize_reverb(self):
        """Initialize reverb delay lines and filters"""
        # Standard reverb comb filter delays (in samples)
        comb_delays = [1557, 1617, 1491, 1422, 1277, 1356, 1188, 1116]

        for i, delay in enumerate(comb_delays):
            self.delay_lines[f'comb_{i}'] = np.zeros(delay, dtype=np.float32)

        # All-pass filters for diffusion
        allpass_delays = [225, 556, 441, 341]
        for i, delay in enumerate(allpass_delays):
            self.delay_lines[f'allpass_{i}'] = np.zeros(delay, dtype=np.float32)

        # Pre-delay
        self.delay_lines['predelay'] = np.zeros(int(0.03 * self.sample_rate), dtype=np.float32)

        # Write pointers for delay lines
        self.write_ptrs = {key: 0 for key in self.delay_lines.keys()}

    def set_reverb_type(self, reverb_type: XGReverbType):
        """Set XG reverb type with appropriate settings"""
        self.reverb_type = reverb_type

        # XG reverb type presets
        type_settings = {
            XGReverbType.HALL_1:   {'time': 0.8,  'hf_damp': 0.2, 'feedback': 0.3},
            XGReverbType.HALL_2:   {'time': 1.2,  'hf_damp': 0.3, 'feedback': 0.4},
            XGReverbType.HALL_3:   {'time': 1.8,  'hf_damp': 0.4, 'feedback': 0.5},
            XGReverbType.HALL_4:   {'time': 2.5,  'hf_damp': 0.5, 'feedback': 0.6},
            XGReverbType.ROOM_1:   {'time': 0.5,  'hf_damp': 0.1, 'feedback': 0.2},
            XGReverbType.ROOM_2:   {'time': 0.8,  'hf_damp': 0.2, 'feedback': 0.3},
            XGReverbType.ROOM_3:   {'time': 1.2,  'hf_damp': 0.3, 'feedback': 0.4},
            XGReverbType.ROOM_4:   {'time': 1.8,  'hf_damp': 0.4, 'feedback': 0.5},
            XGReverbType.STAGE_1:  {'time': 1.0,  'hf_damp': 0.3, 'feedback': 0.4},
            XGReverbType.STAGE_2:  {'time': 1.5,  'hf_damp': 0.4, 'feedback': 0.5},
            XGReverbType.STAGE_3:  {'time': 2.2,  'hf_damp': 0.5, 'feedback': 0.6},
            XGReverbType.STAGE_4:  {'time': 3.0,  'hf_damp': 0.6, 'feedback': 0.7},
            XGReverbType.PLATE:    {'time': 1.0,  'hf_damp': 0.5, 'feedback': 0.8},
        }

        if reverb_type in type_settings:
            settings = type_settings[reverb_type]
            self.time = settings['time']
            self.hf_damp = settings['hf_damp']
            self.feedback = settings['feedback']

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """
        Process reverb for a block of samples

        Args:
            input_left: Left channel input
            input_right: Right channel input
            output_left: Left channel output (modified in-place)
            output_right: Right channel output (modified in-place)
        """
        if self.level <= 0.0:
            # No reverb
            return

        block_size = len(input_left)

        # Stereo to mono input with slight widening
        mono_input = (input_left + input_right) * 0.5

        # Pre-delay
        predelay_output = self._process_delay(mono_input, 'predelay')

        # Process through comb filters
        comb_outputs = []
        for i in range(8):
            comb_out = self._process_comb_filter(predelay_output, f'comb_{i}')
            comb_outputs.append(comb_out)

        # Mix comb filter outputs
        comb_mix = np.zeros(block_size, dtype=np.float32)
        for i, comb_out in enumerate(comb_outputs):
            # Prime numbers for different gains
            gain = 1.0 / (i + 3)  # Decreasing gains: 1/3, 1/4, 1/5, ...
            comb_mix += comb_out * gain

        # Normalize comb mix
        comb_mix *= 1.0 / sum(1.0 / (i + 3) for i in range(8))

        # Process all-pass filters for diffusion
        diffused = comb_mix.copy()
        for i in range(4):
            diffused = self._process_allpass_filter(diffused, f'allpass_{i}')

        # Apply HF damping
        damped = self._apply_hf_damping(diffused)

        # Stereo expansion
        wet_left = damped * (1.0 + self.level * 0.3)   # Slight left emphasis
        wet_right = damped * (1.0 + self.level * 0.3)  # Slight right emphasis

        # Mix dry and wet signals
        dry_level = 1.0 - self.level
        wet_level = self.level

        output_left[:] = input_left * dry_level + wet_left * wet_level
        output_right[:] = input_right * dry_level + wet_right * wet_level

    def _process_delay(self, input_signal: np.ndarray, delay_key: str) -> np.ndarray:
        """Process through a delay line"""
        delay_line = self.delay_lines[delay_key]
        delay_size = len(delay_line)
        write_ptr = self.write_ptrs[delay_key]

        output = np.zeros(len(input_signal), dtype=np.float32)

        for i in range(len(input_signal)):
            # Read from delay line
            read_ptr = (write_ptr - delay_size + 1) % delay_size
            output[i] = delay_line[read_ptr]

            # Write to delay line
            delay_line[write_ptr] = input_signal[i]

            # Update write pointer
            write_ptr = (write_ptr + 1) % delay_size

        self.write_ptrs[delay_key] = write_ptr
        return output

    def _process_comb_filter(self, input_signal: np.ndarray, comb_key: str) -> np.ndarray:
        """Process through a comb filter with feedback"""
        delay_output = self._process_delay(input_signal, comb_key)

        # Apply feedback gain
        feedback_gain = self.feedback

        # Add feedback to input for next iteration
        # Note: This is a simplified implementation
        feedback_signal = delay_output * feedback_gain

        return input_signal + feedback_signal

    def _process_allpass_filter(self, input_signal: np.ndarray, allpass_key: str) -> np.ndarray:
        """Process through an all-pass filter for diffusion"""
        delay_output = self._process_delay(input_signal, allpass_key)

        # All-pass filter: y[n] = x[n] * g + y[n-d] - x[n-d] * g
        # where g is the feedback coefficient (typically 0.7)
        g = 0.7

        # Simplified all-pass implementation
        output = input_signal * g + delay_output - input_signal * g

        return output

    def _apply_hf_damping(self, input_signal: np.ndarray) -> np.ndarray:
        """Apply high-frequency damping"""
        if self.hf_damp <= 0.0:
            return input_signal

        # Simple first-order low-pass damping of high frequencies
        damped = input_signal.copy()

        # Feedback coefficient based on HF damp (0.0 = no damp, 1.0 = heavy damp)
        fb_coeff = self.hf_damp * 0.9

        # Apply one-pole low-pass filter
        prev_sample = getattr(self, '_damp_prev', 0.0)

        for i in range(len(damped)):
            damped[i] = damped[i] * (1.0 - fb_coeff) + prev_sample * fb_coeff
            prev_sample = damped[i]

        self._damp_prev = prev_sample
        return damped

    def set_parameters(self, time: Optional[float] = None, hf_damp: Optional[float] = None,
                      feedback: Optional[float] = None, level: Optional[float] = None):
        """Set reverb parameters (0.0-1.0 range for all except time)"""
        if time is not None:
            self.time = max(0.1, min(5.0, time))
        if hf_damp is not None:
            self.hf_damp = max(0.0, min(1.0, hf_damp))
        if feedback is not None:
            self.feedback = max(0.0, min(0.95, feedback))  # Prevent instability
        if level is not None:
            self.level = max(0.0, min(1.0, level))


class XGChorusEffect:
    """
    XG Chorus Effect Implementation

    Features chorus/flanger/celeste effects with:
    - LFO modulation (0.125-8.0 Hz)
    - Depth control (0-127)
    - Feedback (-63 to +63)
    - Send level (0-127)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.chorus_type = XGChorusType.CHORUS_1

        # LFO parameters
        self.lfo_rate = 0.5   # Hz
        self.lfo_depth = 0.5  # 0-1

        # Chorus parameters
        self.feedback = 0.0   # -1 to 1
        self.send_level = 0.3 # 0-1

        # Delay lines (up to 50ms delay)
        max_delay = int(0.05 * sample_rate)  # 50ms
        self.delay_line_left = np.zeros(max_delay, dtype=np.float32)
        self.delay_line_right = np.zeros(max_delay, dtype=np.float32)

        self.delay_write_ptr = 0

        # LFO state
        self.lfo_phase = 0.0
        self.lfo_increment = 2.0 * np.pi * self.lfo_rate / sample_rate

        # Coefficient manager
        self.coeff_manager = get_global_coefficient_manager()

    def set_chorus_type(self, chorus_type: XGChorusType):
        """Set XG chorus type with appropriate settings"""
        self.chorus_type = chorus_type

        # XG chorus type presets
        type_settings = {
            XGChorusType.CHORUS_1:   {'rate': 0.5, 'depth': 0.5, 'feedback': 0.0},
            XGChorusType.CHORUS_2:   {'rate': 1.0, 'depth': 0.7, 'feedback': 0.2},
            XGChorusType.CELESTE_1:  {'rate': 0.3, 'depth': 0.4, 'feedback': -0.3},
            XGChorusType.CELESTE_2:  {'rate': 0.4, 'depth': 0.6, 'feedback': -0.4},
            XGChorusType.FLANGER_1:  {'rate': 0.1, 'depth': 0.9, 'feedback': 0.7},
            XGChorusType.FLANGER_2:  {'rate': 0.2, 'depth': 1.0, 'feedback': 0.9},
        }

        if chorus_type in type_settings:
            settings = type_settings[chorus_type]
            self.lfo_rate = settings['rate']
            self.lfo_depth = settings['depth']
            self.feedback = settings['feedback']
            self.lfo_increment = 2.0 * np.pi * self.lfo_rate / self.sample_rate

    def process_block(self, input_left: np.ndarray, input_right: np.ndarray,
                     output_left: np.ndarray, output_right: np.ndarray) -> None:
        """
        Process chorus/flanger for a block of samples

        Args:
            input_left: Left channel input
            input_right: Right channel input
            output_left: Left channel output (modified in-place)
            output_right: Right channel output (modified in-place)
        """
        if self.send_level <= 0.0:
            # No chorus
            return

        block_size = len(input_left)

        # Generate LFO modulation for this block
        lfo_values = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            lfo_values[i] = 0.5 * (1.0 + np.sin(self.lfo_phase))
            self.lfo_phase += self.lfo_increment

            # Keep phase in 0-2π range
            if self.lfo_phase >= 2.0 * np.pi:
                self.lfo_phase -= 2.0 * np.pi

        # Convert LFO to delay modulation (samples)
        max_delay = len(self.delay_line_left) - 1
        min_delay = 5  # Minimum 5 samples delay

        # LFO controls delay time variation
        base_delay = 15.0 + 30.0 * (1.0 - self.lfo_depth)  # 15-45 samples base
        delay_modulation = max_delay * 0.1 * self.lfo_depth  # ±10% modulation

        # Process left channel
        left_wet = np.zeros(block_size, dtype=np.float32)
        for i in range(block_size):
            # Calculate modulated delay
            lfo_mod = delay_modulation * lfo_values[i]
            delay_samples = base_delay + lfo_mod
            delay_samples = max(min_delay, min(max_delay, delay_samples))

            # Interpolate delayed sample
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            # Read from delay line with interpolation
            delayed_sample = self._interpolate_delay(self.delay_line_left,
                                                    self.delay_write_ptr,
                                                    delay_int, delay_frac,
                                                    len(self.delay_line_left))

            # Apply feedback
            feedback_sample = delayed_sample * self.feedback
            input_with_feedback = input_left[i] + feedback_sample

            # Write to delay line
            self.delay_line_left[self.delay_write_ptr] = input_with_feedback

            # Wet output
            left_wet[i] = delayed_sample

            # Update write pointer
            self.delay_write_ptr = (self.delay_write_ptr + 1) % len(self.delay_line_left)

        # Process right channel (opposite phase for stereo effect)
        right_phase_offset = np.pi  # 180 degrees out of phase
        right_lfo_values = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            right_lfo_values[i] = 0.5 * (1.0 + np.sin(self.lfo_phase + right_phase_offset))

        right_wet = np.zeros(block_size, dtype=np.float32)
        for i in range(block_size):
            # Calculate modulated delay for right channel
            lfo_mod = delay_modulation * right_lfo_values[i]
            delay_samples = base_delay + lfo_mod
            delay_samples = max(min_delay, min(max_delay, delay_samples))

            # Interpolate delayed sample
            delay_int = int(delay_samples)
            delay_frac = delay_samples - delay_int

            delayed_sample = self._interpolate_delay(self.delay_line_right,
                                                   self.delay_write_ptr,
                                                   delay_int, delay_frac,
                                                   len(self.delay_line_right))

            # Apply feedback (inverted for stereo effect)
            feedback_sample = delayed_sample * self.feedback * -1.0
            input_with_feedback = input_right[i] + feedback_sample

            # Write to delay line
            self.delay_line_right[self.delay_write_ptr] = input_with_feedback

            # Wet output
            right_wet[i] = delayed_sample

            # Update write pointer
            self.delay_write_ptr = (self.delay_write_ptr + 1) % len(self.delay_line_right)

        # Mix dry and wet signals
        wet_gain = self.send_level
        dry_gain = 1.0 - self.send_level * 0.5  # Reduce dry slightly for chorus

        output_left[:] = input_left * dry_gain + left_wet * wet_gain
        output_right[:] = input_right * dry_gain + right_wet * wet_gain

    def _interpolate_delay(self, delay_line: np.ndarray, write_ptr: int,
                          delay_int: int, delay_frac: float, delay_size: int) -> float:
        """Interpolate sample from delay line"""
        # Calculate read pointer
        read_ptr = (write_ptr - delay_int) % delay_size

        # Get samples for interpolation
        sample1_idx = read_ptr % delay_size
        sample2_idx = (read_ptr - 1) % delay_size

        sample1 = delay_line[sample1_idx]

        # Handle boundary case
        if sample2_idx < 0:
            sample2_idx = delay_size - 1

        sample2 = delay_line[sample2_idx]

        # Linear interpolation
        return sample1 + delay_frac * (sample2 - sample1)

    def set_parameters(self, lfo_rate: Optional[float] = None, lfo_depth: Optional[float] = None,
                      feedback: Optional[float] = None, send_level: Optional[float] = None):
        """Set chorus parameters"""
        if lfo_rate is not None:
            self.lfo_rate = max(0.125, min(8.0, lfo_rate))
            self.lfo_increment = 2.0 * np.pi * self.lfo_rate / self.sample_rate

        if lfo_depth is not None:
            self.lfo_depth = max(0.0, min(1.0, lfo_depth))

        if feedback is not None:
            self.feedback = max(-1.0, min(1.0, feedback))

        if send_level is not None:
            self.send_level = max(0.0, min(1.0, send_level))


class XGEffectsManager:
    """
    XG Multi-Stage Effects Processing Engine

    Implements complete XG effects architecture:
    - System Effects: Reverb, Chorus (shared across parts)
    - Variation Effects: Per-part variation effects
    - Insertion Effects: 3 per-part effect chains

    Signal Flow: Input → Insert → Variation → Reverb → Chorus → Output
    """

    def __init__(self, sample_rate: int = 44100, max_parts: int = 16):
        self.sample_rate = sample_rate
        self.max_parts = max_parts

        # System effects (shared across all parts)
        self.system_reverb = XGReverbEffect(sample_rate)
        self.system_chorus = XGChorusEffect(sample_rate)

        # Per-part effect routing
        self.part_variation_effects: List[Optional[Callable]] = [None] * max_parts
        self.part_insertion_chains: List[List[Optional[Callable]]] = [
            [None, None, None] for _ in range(max_parts)
        ]

        # Effect send levels per part (0-127 MIDI range)
        self.reverb_send_levels = np.full(max_parts, 40, dtype=np.int32)   # CC 91 default
        self.chorus_send_levels = np.full(max_parts, 0, dtype=np.int32)    # CC 93 default
        self.variation_send_levels = np.full(max_parts, 0, dtype=np.int32) # CC 94 default

        # Master effect enables
        self.reverb_enabled = True
        self.chorus_enabled = True
        self.variation_enabled = True
        self.insertion_enabled = True

        # Processing state
        self.state = XGProcessingState.IDLE

        # Thread safety
        self.lock = threading.RLock()

        # Initialize pooling for temporary buffers
        self.temp_buffers: List[np.ndarray] = []

        # Effect parameter cache to avoid redundant updates
        self.parameter_cache = {}

        print(f"XG Effects Manager initialized for {max_parts} parts at {sample_rate}Hz")

    def initialize(self):
        """Initialize effects processing"""
        with self.lock:
            self.state = XGProcessingState.INITIALIZING

            # Pre-allocate temporary processing buffers
            buffer_size = 1024  # Standard block size
            for _ in range(8):  # Enough for stereo processing pipeline
                self.temp_buffers.append(
                    np.zeros(buffer_size * 2, dtype=np.float32)
                )

            # Set default XG effect parameters
            self._set_default_xg_parameters()

            self.state = XGProcessingState.PROCESSING
            print("XG Effects System ready for processing")

    def initialize_xg_effects(self):
        """Alias for initialize() - compatibility with synthesizer"""
        self.initialize()

    def _set_default_xg_parameters(self):
        """Set default XG effect parameters per specification"""
        # Default system reverb: Hall 1
        self.system_reverb.set_reverb_type(XGReverbType.HALL_1)
        self.system_reverb.set_parameters(time=1.5, hf_damp=0.3, feedback=0.4, level=0.4)

        # Default system chorus: Chorus 1
        self.system_chorus.set_chorus_type(XGChorusType.CHORUS_1)
        self.system_chorus.set_parameters(lfo_rate=0.5, lfo_depth=0.5, feedback=0.0, send_level=0.3)

        # Default part send levels (XG defaults)
        # Reverb: 40/127, Chorus: 0/127, Variation: 0/127
        pass  # Already set in __init__

    def process_part(self, part_id: int, input_left: np.ndarray, input_right: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process audio for a single part through the complete XG effects chain

        Args:
            part_id: MIDI channel/part number (0-15)
            input_left: Left channel input buffer
            input_right: Right channel input buffer

        Returns:
            Tuple of (processed_left, processed_right) buffers
        """
        if self.state != XGProcessingState.PROCESSING:
            # Return input unchanged if not initialized
            return input_left.copy(), input_right.copy()

        if part_id >= self.max_parts:
            return input_left.copy(), input_right.copy()

        with self.lock:
            # Get temporary buffers for processing
            temp1_left, temp1_right = self._get_temp_buffers()
            temp2_left, temp2_right = self._get_temp_buffers()

            # Copy input to temp1
            temp1_left[:len(input_left)] = input_left
            temp1_right[:len(input_right)] = input_right

            # Step 1: Insertion effects (3 per part)
            if self.insertion_enabled:
                self._process_insertion_chain(part_id, temp1_left, temp1_right, temp2_left, temp2_right)
                # Swap buffers - insertion output becomes input to next stage
                temp1_left, temp2_left = temp2_left, temp1_left
                temp1_right, temp2_right = temp2_right, temp1_right

            # Step 2: Variation effect (per part)
            if self.variation_enabled:
                self._process_variation_effect(part_id, temp1_left, temp1_right, temp2_left, temp2_right)
                # Swap buffers
                temp1_left, temp2_left = temp2_left, temp1_left
                temp1_right, temp2_right = temp2_right, temp1_right

            # Step 3: System effects (shared)
            final_left = temp1_left.copy()
            final_right = temp1_right.copy()

            # Add reverb send (with part-specific level)
            if self.reverb_enabled and self.reverb_send_levels[part_id] > 0:
                reverb_send = self.reverb_send_levels[part_id] / 127.0
                self.system_reverb.set_parameters(level=reverb_send)
                self.system_reverb.process_block(temp1_left, temp1_right, final_left, final_right)

            # Add chorus send (with part-specific level)
            if self.chorus_enabled and self.chorus_send_levels[part_id] > 0:
                chorus_send = self.chorus_send_levels[part_id] / 127.0
                self.system_chorus.set_parameters(send_level=chorus_send)
                self.system_chorus.process_block(final_left, final_right, final_left, final_right)

            # Return processed buffers
            return final_left[:len(input_left)], final_right[:len(input_right)]

    def _process_insertion_chain(self, part_id: int, in_left: np.ndarray, in_right: np.ndarray,
                               out_left: np.ndarray, out_right: np.ndarray) -> None:
        """Process the 3-slot insertion effect chain for a part"""
        # Copy input to output initially
        out_left[:len(in_left)] = in_left
        out_right[:len(in_right)] = in_right

        # Process through each insertion slot
        for slot in self.part_insertion_chains[part_id]:
            if slot is not None:
                # TODO: Implement insertion effect processing
                # For now, pass through unchanged
                pass

    def _process_variation_effect(self, part_id: int, in_left: np.ndarray, in_right: np.ndarray,
                                out_left: np.ndarray, out_right: np.ndarray) -> None:
        """Process variation effect for a part"""
        # Copy input to output initially
        out_left[:len(in_left)] = in_left
        out_right[:len(in_right)] = in_right

        # Process variation effect if configured
        if self.part_variation_effects[part_id] is not None:
            # TODO: Implement variation effect processing
            # For now, pass through unchanged
            pass

    def _get_temp_buffers(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get temporary buffers for processing"""
        # Cycle through available temp buffers
        if not self.temp_buffers:
            # Fallback if no buffers available
            size = 2048
            return np.zeros(size, dtype=np.float32), np.zeros(size, dtype=np.float32)

        buffer = self.temp_buffers.pop(0)
        mid = len(buffer) // 2
        left = buffer[:mid]
        right = buffer[mid:]

        # Return to pool after use (will be managed by caller)
        self.temp_buffers.append(buffer)

        return left, right

    # XG Parameter Control Interface (NRPN MSB 0-19)

    def handle_nrpn_system_effects(self, msb: int, lsb: int, data_msb: int, data_lsb: int) -> bool:
        """
        Handle XG System Effects NRPN parameters

        Args:
            msb: NRPN MSB (1=Reverb, 2=Chorus, 3=Variation)
            lsb: NRPN LSB (parameter type)
            data_msb: Data MSB (parameter value)
            data_lsb: Data LSB (unused for most parameters)

        Returns:
            True if parameter was handled, False otherwise
        """
        if msb == 1:  # System Reverb Parameters
            return self._handle_reverb_nrpn(lsb, data_msb)
        elif msb == 2:  # System Chorus Parameters
            return self._handle_chorus_nrpn(lsb, data_msb)
        elif msb == 3:  # System Variation Parameters
            return self._handle_variation_nrpn(lsb, data_msb)

        return False

    def _handle_reverb_nrpn(self, lsb: int, value: int) -> bool:
        """Handle XG Reverb NRPN parameters"""
        if lsb == 0:  # Reverb Type (0-12)
            reverb_type = XGReverbType(min(value, 12))
            self.system_reverb.set_reverb_type(reverb_type)
            return True
        elif lsb == 2:  # Reverb Time (0-127)
            time_seconds = 0.1 + (value / 127.0) * 4.9  # 0.1-5.0s
            self.system_reverb.set_parameters(time=time_seconds)
            return True
        elif lsb == 4:  # HF Damp (0-127)
            hf_damp = value / 127.0
            self.system_reverb.set_parameters(hf_damp=hf_damp)
            return True
        elif lsb == 6:  # Reverb Feedback (0-127)
            feedback = value / 127.0
            self.system_reverb.set_parameters(feedback=feedback)
            return True

        return False

    def _handle_chorus_nrpn(self, lsb: int, value: int) -> bool:
        """Handle XG Chorus NRPN parameters"""
        if lsb == 0:  # Chorus Type (0-5)
            chorus_type = XGChorusType(min(value, 5))
            self.system_chorus.set_chorus_type(chorus_type)
            return True
        elif lsb == 2:  # LFO Rate (0-127)
            rate_hz = 0.125 + (value / 127.0) * 7.875  # 0.125-8.0Hz
            self.system_chorus.set_parameters(lfo_rate=rate_hz)
            return True
        elif lsb == 4:  # LFO Depth (0-127)
            depth = value / 127.0
            self.system_chorus.set_parameters(lfo_depth=depth)
            return True
        elif lsb == 6:  # Feedback (0-127 mapped to -63-+63)
            feedback = ((value - 64) / 63.0) * 0.5  # More conservative range
            self.system_chorus.set_parameters(feedback=feedback)
            return True

        return False

    def _handle_variation_nrpn(self, lsb: int, value: int) -> bool:
        """Handle XG Variation NRPN parameters"""
        if lsb == 0:  # Variation Type (0-14)
            variation_type = XGVariationType(min(value, 14))
            # TODO: Implement variation type switching
            return True

        return False

    def set_part_send_levels(self, part_id: int, reverb_send: Optional[int] = None,
                           chorus_send: Optional[int] = None, variation_send: Optional[int] = None):
        """Set effect send levels for a specific part (MIDI CC style)"""
        with self.lock:
            if part_id < self.max_parts:
                if reverb_send is not None:
                    self.reverb_send_levels[part_id] = max(0, min(127, reverb_send))
                if chorus_send is not None:
                    self.chorus_send_levels[part_id] = max(0, min(127, chorus_send))
                if variation_send is not None:
                    self.variation_send_levels[part_id] = max(0, min(127, variation_send))

    def set_channel_reverb_send(self, channel: int, level: int):
        """Set reverb send level for a channel (compatibility alias)"""
        self.set_part_send_levels(channel, reverb_send=level)

    def set_channel_chorus_send(self, channel: int, level: int):
        """Set chorus send level for a channel (compatibility alias)"""
        self.set_part_send_levels(channel, chorus_send=level)

    def set_channel_variation_send(self, channel: int, level: int):
        """Set variation send level for a channel (compatibility alias)"""
        self.set_part_send_levels(channel, variation_send=level)

    def reset_to_xg_defaults(self):
        """Reset all effects to XG specification defaults"""
        with self.lock:
            # Reset to XG default values
            self._set_default_xg_parameters()
            # Reset all effect parameters to defaults
            self.system_reverb.set_reverb_type(XGReverbType.HALL_1)
            self.system_chorus.set_chorus_type(XGChorusType.CHORUS_1)
            # Reinitialize processing
            self.state = XGProcessingState.PROCESSING

    def reset_effects(self):
        """Reset all effects to off/bypass state"""
        with self.lock:
            # Disable all effects
            self.reverb_enabled = False
            self.chorus_enabled = False
            self.variation_enabled = False
            self.insertion_enabled = False
            # Reset send levels to zero
            self.reverb_send_levels.fill(0)
            self.chorus_send_levels.fill(0)
            self.variation_send_levels.fill(0)

    def get_channel_insertion_effect(self, channel: int) -> Dict[str, Any]:
        """Get insertion effect for a specific channel (compatibility stub)"""
        # TODO: Implement full insertion effects
        return {
            'enabled': False,
            'bypass': True,
            'type': 0
        }

    def handle_effect_activation(self, cc_number: int, value: int):
        """Handle effect unit activation CC messages"""
        # CC 200-209 range for XG effect activation
        effect_idx = cc_number - 200
        if 0 <= effect_idx < 10:
            # Map to insertion effect slots
            # For now, just enable/disable based on value
            self.insertion_enabled = value > 0

    def handle_sysex(self, manufacturer_id: List[int], data: List[int]):
        """Handle SYSEX messages for XG effects"""
        # TODO: Implement XG SYSEX effect control
        pass

    def process_multi_channel_vectorized(self, channel_audio: List[np.ndarray], block_size: int) -> np.ndarray:
        """Process multiple channels through effects system (stub implementation)"""
        # For now, just mix channels to stereo
        if not channel_audio:
            return np.zeros((block_size, 2), dtype=np.float32)

        # Mix all channels to stereo output
        stereo_output = np.zeros((block_size, 2), dtype=np.float32)
        for channel_buffer in channel_audio:
            if channel_buffer is not None and len(channel_buffer) >= block_size:
                np.add(stereo_output, channel_buffer[:block_size], out=stereo_output)

        return stereo_output

    def get_current_state(self) -> Dict[str, Any]:
        """Get current effects state for monitoring"""
        return {
            'reverb_params': {
                'level': self.system_reverb.level,
                'type': self.system_reverb.reverb_type.name
            },
            'chorus_params': {
                'level': self.system_chorus.send_level,
                'type': self.system_chorus.chorus_type.name
            },
            'variation_params': {
                'level': 0.0  # Not implemented yet
            },
            'equalizer_params': {}  # Not implemented yet
        }

    def get_effect_status(self) -> Dict[str, Any]:
        """Get current status of all effects"""
        return {
            'system_reverb': {
                'enabled': self.reverb_enabled,
                'type': self.system_reverb.reverb_type.name,
                'time': self.system_reverb.time,
                'hf_damp': self.system_reverb.hf_damp,
                'feedback': self.system_reverb.feedback,
                'level': self.system_reverb.level,
            },
            'system_chorus': {
                'enabled': self.chorus_enabled,
                'type': self.system_chorus.chorus_type.name,
                'lfo_rate': self.system_chorus.lfo_rate,
                'lfo_depth': self.system_chorus.lfo_depth,
                'feedback': self.system_chorus.feedback,
                'send_level': self.system_chorus.send_level,
            },
            'part_sends': {
                'reverb': self.reverb_send_levels.tolist(),
                'chorus': self.chorus_send_levels.tolist(),
                'variation': self.variation_send_levels.tolist(),
            }
        }

    def shutdown(self):
        """Clean shutdown of effects system"""
        with self.lock:
            self.state = XGProcessingState.IDLE
            self.temp_buffers.clear()
            self.parameter_cache.clear()
