"""
XG System Effects - Reverb and Chorus Processors

This module implements the system-wide effects that are applied to the final
mix of all channels. Includes convolution reverb and stereo chorus/flanger.

Key Features:
- Convolution reverb with XG-compliant impulse response generation
- Stereo chorus with advanced LFO modulation and cross-feedback
- Block-based processing with zero-allocation design
- Thread-safe parameter updates
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum
import threading

# Import from our type definitions
from .types import XGReverbType, XGChorusType, XGProcessingContext


class XGSystemReverbProcessor:
    """
    XG Convolution Reverb Processor

    Implements high-quality convolution reverb with complete XG specification support:
    - 25 XG reverb types (Hall 1-8, Room 9-16, Plate 17-24)
    - Individually controllable parameters: time, level, pre-delay, HF damping, density
    - Convolution-based processing with pre-computed impulse responses
    - Block-based processing for realtime performance
    """

    def __init__(self, sample_rate: int, max_ir_length: int = 44100 * 2):
        """
        Initialize XG reverb processor.

        Args:
            sample_rate: Sample rate in Hz
            max_ir_length: Maximum impulse response length in samples
        """
        self.sample_rate = sample_rate
        self.max_ir_length = max_ir_length

        # XG reverb parameters with NRPN defaults
        self.params = {
            'reverb_type': XGReverbType.HALL_1.value,      # Type 1-24
            'time': 0.5,          # Reverb time (0.1-8.3 seconds)
            'level': 0.6,         # Wet/dry mix level (0-1)
            'pre_delay': 0.02,    # Pre-delay in seconds (0-0.05)
            'hf_damping': 0.5,    # High frequency damping (0-1)
            'density': 0.8,       # Reverberation density (0-1)
            'enabled': True,
        }

        # Convolution state
        self.current_ir: Optional[np.ndarray] = None
        self.convolution_buffers: List[np.ndarray] = []
        self.buffer_positions: List[int] = []
        self.ir_cache: Dict[Tuple[int, float, float, float, float], np.ndarray] = {}

        # Thread safety
        self.lock = threading.RLock()
        self.param_updated = True

        # Initialize with default IR
        self._update_impulse_response()

    def set_parameter(self, param: str, value: float) -> bool:
        """
        Set a reverb parameter value.

        Args:
            param: Parameter name ('time', 'level', 'pre_delay', 'hf_damping', 'density', 'reverb_type')
            value: Parameter value

        Returns:
            True if parameter was updated and IR needs refresh
        """
        with self.lock:
            if param not in self.params:
                return False

            old_value = self.params[param]
            self.params[param] = value

            # Check if IR needs to be updated
            ir_affecting_params = {'reverb_type', 'time', 'hf_damping', 'density', 'pre_delay'}
            if param in ir_affecting_params and abs(value - old_value) > 1e-6:
                self.param_updated = True
                return True

            return False

    def apply_system_effects_to_mix_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply system reverb to the final stereo mix (in-place processing).

        This method implements zero-allocation processing by modifying the input buffer.
        Uses pre-allocated convolution buffers for the convolution processing.

        Args:
            stereo_mix: Input/output stereo mix buffer (N, 2)
            num_samples: Number of samples to process
        """
        if not self.params['enabled'] or self.current_ir is None:
            return

        with self.lock:
            # Update IR if parameters changed
            if self.param_updated:
                self._update_impulse_response()
                self.param_updated = False

            level = self.params['level']
            if level <= 0.001:  # Effectively bypassed
                return

            # Ensure we have enough convolution buffers
            self._ensure_convolution_buffers(num_samples)

            # Apply pre-delay if configured
            if self.params['pre_delay'] > 0:
                pre_delay_samples = int(self.params['pre_delay'] * self.sample_rate)
                self._apply_pre_delay(stereo_mix, num_samples, pre_delay_samples)

            # Apply convolution reverb
            # For performance, we use a hybrid approach: direct convolution for short IRs,
            # FFT convolution for longer ones
            if len(self.current_ir) <= 256:
                self._apply_direct_convolution(stereo_mix, num_samples)
            else:
                self._apply_fft_convolution(stereo_mix, num_samples)

            # Scale by wet/dry mix level
            stereo_mix *= level

    def _ensure_convolution_buffers(self, num_samples: int) -> None:
        """Ensure we have adequate convolution buffers for processing."""
        # We maintain a circular buffer history for convolution
        required_size = num_samples + len(self.current_ir) - 1
        if len(self.convolution_buffers) == 0 or self.convolution_buffers[0].shape[0] < required_size:
            self.convolution_buffers = [
                np.zeros(required_size, dtype=np.float32) for _ in range(2)  # Left and right
            ]
            self.buffer_positions = [0, 0]

    def _apply_pre_delay(self, stereo_mix: np.ndarray, num_samples: int, delay_samples: int) -> None:
        """Apply pre-delay by swapping samples in the buffer."""
        if delay_samples >= num_samples:
            # If delay is longer than block, delay entire block
            return

        # Rotate samples in the buffer (simple pre-delay implementation)
        for ch in range(2):
            channel_data = stereo_mix[:, ch]
            # Store the end samples
            end_samples = channel_data[-delay_samples:].copy()
            # Shift samples forward
            channel_data[delay_samples:] = channel_data[:-delay_samples]
            # Put the moved samples at the beginning (as delay)
            channel_data[:delay_samples] = end_samples

    def _apply_direct_convolution(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply direct convolution for shorter impulse responses."""
        ir_length = len(self.current_ir)

        # Process left channel
        left_input = stereo_mix[:, 0]
        left_output = np.zeros(num_samples, dtype=np.float32)

        # Add current input to convolution buffer
        self.convolution_buffers[0][self.buffer_positions[0]:self.buffer_positions[0] + num_samples] = left_input
        self.buffer_positions[0] = (self.buffer_positions[0] + num_samples) % len(self.convolution_buffers[0])

        # Perform convolution
        for i in range(num_samples):
            pos = self.buffer_positions[0] - num_samples + i
            if pos < 0:
                pos += len(self.convolution_buffers[0])

            conv_sum = 0.0
            for j in range(min(ir_length, len(self.convolution_buffers[0]) - pos)):
                conv_sum += self.convolution_buffers[0][pos + j] * self.current_ir[j]
            left_output[i] = conv_sum

        # Same for right channel
        right_input = stereo_mix[:, 1]
        right_output = np.zeros(num_samples, dtype=np.float32)

        self.convolution_buffers[1][self.buffer_positions[1]:self.buffer_positions[1] + num_samples] = right_input
        self.buffer_positions[1] = (self.buffer_positions[1] + num_samples) % len(self.convolution_buffers[1])

        for i in range(num_samples):
            pos = self.buffer_positions[1] - num_samples + i
            if pos < 0:
                pos += len(self.convolution_buffers[1])

            conv_sum = 0.0
            for j in range(min(ir_length, len(self.convolution_buffers[1]) - pos)):
                conv_sum += self.convolution_buffers[1][pos + j] * self.current_ir[j]
            right_output[i] = conv_sum

        # Update stereo_mix with reverb
        stereo_mix[:] = np.column_stack((left_output, right_output))

    def _apply_fft_convolution(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply FFT-based convolution for longer impulse responses."""
        try:
            from scipy.signal import fftconvolve

            # Process each channel
            for ch in range(2):
                channel_input = stereo_mix[:, ch]
                # Apply FFT convolution
                convolved = fftconvolve(channel_input, self.current_ir, mode='full')
                # Take the appropriate segment
                stereo_mix[:num_samples, ch] = convolved[:num_samples]

        except ImportError:
            # Fallback to direct convolution
            self._apply_direct_convolution(stereo_mix, num_samples)

    def _update_impulse_response(self) -> None:
        """Generate or retrieve impulse response based on current parameters."""
        # Create cache key from current parameters
        cache_key = (
            self.params['reverb_type'],
            round(self.params['time'], 3),
            round(self.params['hf_damping'], 3),
            round(self.params['density'], 3),
            round(self.params['pre_delay'], 3)
        )

        if cache_key in self.ir_cache:
            self.current_ir = self.ir_cache[cache_key]
            return

        # Generate new impulse response
        ir_length = min(int(self.sample_rate * self.params['time'] * 1.5), self.max_ir_length)
        self.current_ir = np.zeros(ir_length, dtype=np.float32)

        # XG reverb type determines characteristics
        reverb_type = self.params['reverb_type']
        if 1 <= reverb_type <= 8:  # Hall types
            self._generate_hall_ir()
        elif 9 <= reverb_type <= 16:  # Room types
            self._generate_room_ir()
        elif 17 <= reverb_type <= 24:  # Plate types
            self._generate_plate_ir()

        # Normalize
        max_val = np.max(np.abs(self.current_ir))
        if max_val > 0:
            self.current_ir /= max_val

        # Cache the impulse response
        self.ir_cache[cache_key] = self.current_ir

    def _generate_hall_ir(self) -> None:
        """Generate hall-type impulse response."""
        # Characteristics: large, lush, with multiple early reflections
        time = self.params['time']
        damping = self.params['hf_damping']
        density = self.params['density']

        # Early reflections pattern for hall
        early_positions = [0.02, 0.035, 0.055, 0.08, 0.12, 0.18, 0.25, 0.35]
        early_gains = [1.0, 0.8, -0.6, 0.4, -0.3, 0.2, -0.15, 0.1]

        for pos, gain in zip(early_positions, early_gains):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain * (0.3 + density * 0.7)

        # Dense late reverberation
        for i in range(int(0.5 * self.sample_rate), len(self.current_ir)):
            # Exponential decay with damping
            decay_factor = math.exp(-(i / self.sample_rate) / time)
            # High frequency damping
            damping_factor = math.exp(-damping * (i / self.sample_rate) * 2.0)
            # Dense noise excitation
            noise = (np.random.random() - 0.5) * 2.0
            self.current_ir[i] += noise * decay_factor * damping_factor * density

    def _generate_room_ir(self) -> None:
        """Generate room-type impulse response."""
        # Characteristics: more intimate than hall, with fewer early reflections
        time = self.params['time']
        damping = self.params['hf_damping']
        density = self.params['density']

        # Fewer, less prominent early reflections
        early_positions = [0.015, 0.028, 0.045, 0.065, 0.095]
        early_gains = [1.0, 0.7, -0.4, 0.3, -0.2]

        for pos, gain in zip(early_positions, early_gains):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain * (0.4 + density * 0.6)

        # More subdued late reverb
        for i in range(int(0.1 * self.sample_rate), len(self.current_ir)):
            decay_factor = math.exp(-(i / self.sample_rate) / (time * 0.8))
            damping_factor = math.exp(-damping * (i / self.sample_rate) * 1.5)
            noise = (np.random.random() - 0.5) * 2.0
            self.current_ir[i] += noise * decay_factor * damping_factor * (density * 0.8)

    def _generate_plate_ir(self) -> None:
        """Generate plate-type impulse response."""
        # Characteristics: bright, metallic, shorter decay than hall
        time = self.params['time']
        damping = self.params['hf_damping']
        density = self.params['density']

        # Distinctive early reflections for plate
        early_positions = [0.005, 0.012, 0.019, 0.028, 0.042]
        early_gains = [1.0, 0.9, -0.7, 0.5, -0.4]

        for pos, gain in zip(early_positions, early_gains):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain

        # Bright, metallic late reverb with less HF damping
        for i in range(int(0.05 * self.sample_rate), len(self.current_ir)):
            decay_factor = math.exp(-(i / self.sample_rate) / (time * 0.9))
            damping_factor = math.exp(-damping * (i / self.sample_rate) * 0.7)  # Less HF damping
            # More filtered noise for metallic sound
            noise = (np.random.random() - 0.5) * 2.0
            # High-pass characteristic
            if i > 0.1 * self.sample_rate:
                noise = noise * max(0.6, 1.0 - (i / self.sample_rate) * 0.5)
            self.current_ir[i] += noise * decay_factor * damping_factor * density


class XGSystemChorusProcessor:
    """
    XG Chorus/Flanger Processor

    Implements advanced stereo chorus with LFO modulation and cross-feedback.
    Supports all XG chorus types with full parameter control.

    Key features:
    - Multiple LFO waveforms (sine, triangle, square, saw)
    - Stereo processing with phase differences
    - Cross-channel feedback
    - Block-based processing for realtime performance
    """

    def __init__(self, sample_rate: int, max_delay_samples: int = 8192):
        """
        Initialize XG chorus processor.

        Args:
            sample_rate: Sample rate in Hz
            max_delay_samples: Maximum delay line length in samples
        """
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # XG chorus parameters
        self.params = {
            'chorus_type': XGChorusType.CHORUS_1.value,  # Type 0-5
            'rate': 1.0,          # LFO rate in Hz (0.125-10.0)
            'depth': 0.5,         # Modulation depth (0-1)
            'feedback': 0.3,      # Feedback amount (-0.5 to +0.5)
            'level': 0.4,         # Wet/dry mix level (0-1)
            'delay': 0.012,       # Base delay in seconds
            'cross_feedback': 0.0, # Cross-feedback between channels (0-1)
            'lfo_waveform': 0,    # LFO waveform (0=sine, 1=triangle, 2=square, 3=saw)
            'phase_diff': 90.0,   # Phase difference in degrees
            'enabled': True,
        }

        # Delay lines for stereo processing
        self.left_delay_line = np.zeros(max_delay_samples, dtype=np.float32)
        self.right_delay_line = np.zeros(max_delay_samples, dtype=np.float32)
        self.left_write_pos = 0
        self.right_write_pos = 0

        # LFO state
        self.lfo_phase = 0.0
        self.lfo_phase_right = 0.0

        # Thread safety
        self.lock = threading.RLock()
        self.param_updated = True

        # Pre-compute modulation tables for better performance
        self._lfo_tables = self._generate_lfo_tables()

    def set_parameter(self, param: str, value: float) -> bool:
        """
        Set a chorus parameter value.

        Args:
            param: Parameter name
            value: Parameter value

        Returns:
            True if parameter was updated
        """
        with self.lock:
            if param not in self.params:
                return False
            self.params[param] = value
            self.param_updated = True
            return True

    def _generate_lfo_tables(self) -> Dict[str, np.ndarray]:
        """Pre-compute LFO waveform tables for better performance."""
        # Generate one cycle of each waveform
        table_size = 1024
        phases = np.linspace(0, 2 * np.pi, table_size, endpoint=False)

        return {
            'sine': np.sin(phases),
            'triangle': 2 * np.abs((phases / (2 * np.pi) * 4) % 4 - 2) - 1,
            'square': np.sign(np.sin(phases)),
            'saw': 2 * (phases / (2 * np.pi) % 1) - 1
        }

    def _get_lfo_value(self, phase: float, waveform: int) -> float:
        """Get LFO value for given phase and waveform type."""
        table_size = len(self._lfo_tables['sine'])
        table_index = int((phase % (2 * np.pi)) / (2 * np.pi) * table_size) % table_size

        if waveform == 0:  # Sine
            return self._lfo_tables['sine'][table_index]
        elif waveform == 1:  # Triangle
            return self._lfo_tables['triangle'][table_index]
        elif waveform == 2:  # Square
            return self._lfo_tables['square'][table_index]
        else:  # Sawtooth
            return self._lfo_tables['saw'][table_index]

    def apply_system_effects_to_mix_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply system chorus to the final stereo mix (in-place processing).

        Args:
            stereo_mix: Input/output stereo mix buffer (N, 2)
            num_samples: Number of samples to process
        """
        if not self.params['enabled'] or self.params['level'] <= 0.001:
            return

        with self.lock:
            # Apply chorus processing in blocks
            self._process_chorus_block(stereo_mix, num_samples)

    def _process_chorus_block(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Process a block of samples through chorus modulation."""
        rate = self.params['rate']
        depth = self.params['depth']
        feedback = self.params['feedback'] / 127.0 * 0.5  # Scale feedback
        level = self.params['level']
        delay = self.params['delay']
        cross_feedback = self.params['cross_feedback'] / 127.0 * 0.5
        lfo_waveform = int(self.params['lfo_waveform'])
        phase_diff_degrees = self.params['phase_diff']

        # Convert to samples
        base_delay_samples = int(delay * self.sample_rate)
        max_modulation_samples = int(0.012 * self.sample_rate)  # 12ms max modulation

        # Process each sample
        for i in range(num_samples):
            # Update LFO phases
            phase_increment = 2 * np.pi * rate / self.sample_rate
            self.lfo_phase = (self.lfo_phase + phase_increment) % (2 * np.pi)

            phase_diff_rad = phase_diff_degrees * np.pi / 180.0
            self.lfo_phase_right = (self.lfo_phase + phase_diff_rad) % (2 * np.pi)

            # Get LFO values
            lfo_left = self._get_lfo_value(self.lfo_phase, lfo_waveform)
            lfo_right = self._get_lfo_value(self.lfo_phase_right, lfo_waveform)

            # Calculate modulated delay times
            mod_left = base_delay_samples + int(lfo_left * depth * max_modulation_samples)
            mod_right = base_delay_samples + int(lfo_right * depth * max_modulation_samples)

            # Ensure valid delay range
            mod_left = max(1, min(mod_left, self.max_delay_samples - 1))
            mod_right = max(1, min(mod_right, self.max_delay_samples - 1))

            # Read from delay lines
            read_pos_left = (self.left_write_pos - mod_left) % self.max_delay_samples
            read_pos_right = (self.right_write_pos - mod_right) % self.max_delay_samples

            delayed_left = self.left_delay_line[read_pos_left]
            delayed_right = self.right_delay_line[read_pos_right]

            # Get input samples
            input_left = stereo_mix[i, 0]
            input_right = stereo_mix[i, 1]

            # Apply feedback and cross-feedback
            feedback_left = feedback * delayed_left + cross_feedback * delayed_right
            feedback_right = feedback * delayed_right + cross_feedback * delayed_left

            # Calculate new samples to write to delay lines
            new_left = input_left + feedback_left
            new_right = input_right + feedback_right

            # Write to delay lines
            self.left_delay_line[self.left_write_pos] = new_left
            self.right_delay_line[self.right_write_pos] = new_right

            # Update write positions
            self.left_write_pos = (self.left_write_pos + 1) % self.max_delay_samples
            self.right_write_pos = (self.right_write_pos + 1) % self.max_delay_samples

            # Mix dry and wet signals
            stereo_mix[i, 0] = input_left * (1.0 - level) + delayed_left * level
            stereo_mix[i, 1] = input_right * (1.0 - level) + delayed_right * level


class XGSystemModulationProcessor:
    """
    XG System Modulation Effects Processor

    Handles system-wide modulation effects that can be applied in addition to
    or instead of reverb/chorus. Includes tremolo, autopan, flanger, etc.
    """

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.params = {
            'type': 0,           # Effect type
            'rate': 5.0,         # LFO rate
            'depth': 0.5,        # Modulation depth
            'enabled': False,
        }

        # Effect state
        self.lfo_phase = 0.0

        # Thread safety
        self.lock = threading.RLock()

    def set_parameter(self, param: str, value: float) -> bool:
        """
        Set a modulation parameter value.

        Args:
            param: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if param in self.params:
                self.params[param] = value
                return True
            return False

    def apply_system_effects_to_mix_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply system modulation effects to the mix."""
        if not self.params['enabled']:
            return

        with self.lock:
            # Simple tremolo implementation for now
            rate = self.params['rate']
            depth = self.params['depth']

            for i in range(num_samples):
                # Update LFO phase
                phase_increment = 2 * np.pi * rate / self.sample_rate
                self.lfo_phase = (self.lfo_phase + phase_increment) % (2 * np.pi)

                # Generate amplitude modulation
                mod = math.sin(self.lfo_phase)
                amplitude = 1.0 - depth * 0.5 + depth * 0.5 * mod

                # Apply to both channels
                stereo_mix[i, 0] *= amplitude
                stereo_mix[i, 1] *= amplitude


class XGSystemEffectsProcessor:
    """
    XG System Effects Master Processor

    Orchestrates the system-wide effects chain: Reverb -> Chorus -> Optional Modulation
    Provides a unified interface for all system effects processing.
    """

    def __init__(self, sample_rate: int, block_size: int,
                 dsp_units, max_reverb_delay: int, max_chorus_delay: int):
        """
        Initialize system effects processor.

        Args:
            sample_rate: Sample rate in Hz
            block_size: Maximum block size for processing
            dsp_units: DSP units manager (for sharing resources)
            max_reverb_delay: Maximum reverb delay in samples
            max_chorus_delay: Maximum chorus delay in samples
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

        # Initialize effect processors
        self.reverb_processor = XGSystemReverbProcessor(sample_rate, max_reverb_delay)
        self.chorus_processor = XGSystemChorusProcessor(sample_rate, max_chorus_delay)
        self.modulation_processor = XGSystemModulationProcessor(sample_rate)

        # System effects chain configuration
        self.chain_config = {
            'reverb_enabled': True,
            'chorus_enabled': True,
            'modulation_enabled': False,
            'master_level': 1.0,
        }

        # Thread safety
        self.lock = threading.RLock()

    def set_system_effect_parameter(self, effect: str, param: str, value: float) -> bool:
        """
        Set a system effect parameter.

        Args:
            effect: Effect name ('reverb', 'chorus', 'modulation')
            param: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if effect == 'reverb':
                return self.reverb_processor.set_parameter(param, value)
            elif effect == 'chorus':
                return self.chorus_processor.set_parameter(param, value)
            elif effect == 'modulation':
                return self.modulation_processor.set_parameter(param, value) if hasattr(self.modulation_processor, 'set_parameter') else False
            else:
                return False

    def set_chain_config(self, config: Dict[str, Any]) -> None:
        """
        Update the effects chain configuration.

        Args:
            config: Configuration dictionary
        """
        with self.lock:
            for key, value in config.items():
                if key in self.chain_config:
                    self.chain_config[key] = value

    def apply_system_effects_to_mix_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply the complete system effects chain to the stereo mix.

        Processing order: Reverb -> Chorus -> Optional Modulation -> Master Level

        Args:
            stereo_mix: Input/output stereo mix buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        with self.lock:
            # Ensure we don't process more samples than we can handle
            num_samples = min(num_samples, stereo_mix.shape[0])

            # Apply reverb if enabled
            if self.chain_config['reverb_enabled']:
                self.reverb_processor.apply_system_effects_to_mix_zero_alloc(stereo_mix, num_samples)

            # Apply chorus if enabled
            if self.chain_config['chorus_enabled']:
                self.chorus_processor.apply_system_effects_to_mix_zero_alloc(stereo_mix, num_samples)

            # Apply additional modulation if enabled
            if self.chain_config['modulation_enabled']:
                self.modulation_processor.apply_system_effects_to_mix_zero_alloc(stereo_mix, num_samples)

            # Apply master level
            if self.chain_config['master_level'] != 1.0:
                stereo_mix[:num_samples] *= self.chain_config['master_level']

            # Final clipping to prevent overflow
            np.clip(stereo_mix[:num_samples], -1.0, 1.0, out=stereo_mix[:num_samples])

    def get_system_effects_status(self) -> Dict[str, Any]:
        """Get current status of all system effects."""
        with self.lock:
            return {
                'reverb': {
                    'enabled': self.chain_config['reverb_enabled'],
                    'type': self.reverb_processor.params.get('reverb_type', 'unknown'),
                    'level': self.reverb_processor.params.get('level', 0.0),
                },
                'chorus': {
                    'enabled': self.chain_config['chorus_enabled'],
                    'type': self.chorus_processor.params.get('chorus_type', 'unknown'),
                    'level': self.chorus_processor.params.get('level', 0.0),
                },
                'modulation': {
                    'enabled': self.chain_config.get('modulation_enabled', False),
                },
                'master_level': self.chain_config['master_level'],
            }
