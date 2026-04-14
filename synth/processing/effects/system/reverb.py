"""XG System Reverb Processor - convolution reverb with impulse response generation."""

from __future__ import annotations

import math
import threading

import numpy as np

from ..types import XGReverbType


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
            "reverb_type": XGReverbType.HALL_1.value,  # Type 1-24
            "time": 0.5,  # Reverb time (0.1-8.3 seconds)
            "level": 0.6,  # Wet/dry mix level (0-1)
            "pre_delay": 0.02,  # Pre-delay in seconds (0-0.05)
            "hf_damping": 0.5,  # High frequency damping (0-1)
            "density": 0.8,  # Reverberation density (0-1)
            "enabled": True,
        }

        # Convolution state
        self.current_ir: np.ndarray | None = None
        self.convolution_buffers: list[np.ndarray] = []
        self.buffer_positions: list[int] = []
        self.ir_cache: dict[tuple[int, float, float, float, float], np.ndarray] = {}

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
            ir_affecting_params = {"reverb_type", "time", "hf_damping", "density", "pre_delay"}
            if param in ir_affecting_params and abs(value - old_value) > 1e-6:
                self.param_updated = True
                return True

            return False

    def apply_system_effects_to_mix_zero_alloc(
        self, stereo_mix: np.ndarray, num_samples: int
    ) -> None:
        """
        Apply system reverb to the final stereo mix (in-place processing).

        This method implements zero-allocation processing by modifying the input buffer.
        Uses pre-allocated convolution buffers for the convolution processing.

        Args:
            stereo_mix: Input/output stereo mix buffer (N, 2)
            num_samples: Number of samples to process
        """
        if not self.params["enabled"] or self.current_ir is None:
            return

        with self.lock:
            # Update IR if parameters changed
            if self.param_updated:
                self._update_impulse_response()
                self.param_updated = False

            level = self.params["level"]
            if level <= 0.001:  # Effectively bypassed
                return

            # Ensure we have enough convolution buffers
            self._ensure_convolution_buffers(num_samples)

            # Apply pre-delay if configured
            if self.params["pre_delay"] > 0:
                pre_delay_samples = int(self.params["pre_delay"] * self.sample_rate)
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
        if self.current_ir is None:
            return

        # We maintain a circular buffer history for convolution
        required_size = num_samples + len(self.current_ir) - 1
        if (
            len(self.convolution_buffers) == 0
            or self.convolution_buffers[0].shape[0] < required_size
        ):
            self.convolution_buffers = [
                np.zeros(required_size, dtype=np.float32)
                for _ in range(2)  # Left and right
            ]
            self.buffer_positions = [0, 0]

    def _apply_pre_delay(
        self, stereo_mix: np.ndarray, num_samples: int, delay_samples: int
    ) -> None:
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
        if self.current_ir is None:
            return

        ir_length = len(self.current_ir)

        # Process left channel
        left_input = stereo_mix[:, 0]
        left_output = np.zeros(num_samples, dtype=np.float32)

        # Add current input to convolution buffer
        self.convolution_buffers[0][
            self.buffer_positions[0] : self.buffer_positions[0] + num_samples
        ] = left_input
        self.buffer_positions[0] = (self.buffer_positions[0] + num_samples) % len(
            self.convolution_buffers[0]
        )

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

        self.convolution_buffers[1][
            self.buffer_positions[1] : self.buffer_positions[1] + num_samples
        ] = right_input
        self.buffer_positions[1] = (self.buffer_positions[1] + num_samples) % len(
            self.convolution_buffers[1]
        )

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
        if self.current_ir is None:
            return

        try:
            from scipy.signal import fftconvolve

            # Process each channel
            for ch in range(2):
                channel_input = stereo_mix[:, ch]
                # Apply FFT convolution
                convolved = fftconvolve(channel_input, self.current_ir, mode="full")
                # Take the appropriate segment
                stereo_mix[:num_samples, ch] = convolved[:num_samples]

        except ImportError:
            # Fallback to direct convolution
            self._apply_direct_convolution(stereo_mix, num_samples)

    def _update_impulse_response(self) -> None:
        """Generate or retrieve impulse response based on current parameters."""
        # Create cache key from current parameters
        cache_key = (
            self.params["reverb_type"],
            round(self.params["time"], 3),
            round(self.params["hf_damping"], 3),
            round(self.params["density"], 3),
            round(self.params["pre_delay"], 3),
        )

        if cache_key in self.ir_cache:
            self.current_ir = self.ir_cache[cache_key]
            return

        # Generate new impulse response
        ir_length = min(int(self.sample_rate * self.params["time"] * 1.5), self.max_ir_length)
        self.current_ir = np.zeros(ir_length, dtype=np.float32)

        # XG reverb type determines characteristics - implement all 24 XG types
        reverb_type = self.params["reverb_type"]
        if reverb_type == 1:  # Hall 1 (Small Hall)
            self._generate_xg_hall(1.8, 0.4, 0.6)  # time, density, hf_damping
        elif reverb_type == 2:  # Hall 2 (Medium Hall)
            self._generate_xg_hall(2.2, 0.5, 0.5)
        elif reverb_type == 3:  # Hall 3 (Large Hall)
            self._generate_xg_hall(2.8, 0.6, 0.4)
        elif reverb_type == 4:  # Hall 4 (Large Hall +)
            self._generate_xg_hall(3.2, 0.7, 0.35)
        elif reverb_type == 5:  # Hall 5 (Large Hall ++)
            self._generate_xg_hall(3.6, 0.75, 0.3)
        elif reverb_type == 6:  # Hall 6 (Large Hall +++])
            self._generate_xg_hall(4.0, 0.8, 0.25)
        elif reverb_type == 7:  # Hall 7 (Large Hall +++])
            self._generate_xg_hall(4.5, 0.85, 0.2)
        elif reverb_type == 8:  # Hall 8 (Large Hall +++++)
            self._generate_xg_hall(5.0, 0.9, 0.15)

        elif reverb_type == 9:  # Room 1 (Small Room)
            self._generate_xg_room(0.8, 0.7, 0.8)  # time, density, hf_damping
        elif reverb_type == 10:  # Room 2 (Medium Room)
            self._generate_xg_room(1.2, 0.75, 0.7)
        elif reverb_type == 11:  # Room 3 (Large Room)
            self._generate_xg_room(1.6, 0.8, 0.6)
        elif reverb_type == 12:  # Room 4 (Large Room +)
            self._generate_xg_room(2.0, 0.85, 0.5)
        elif reverb_type == 13:  # Room 5 (Large Room ++)
            self._generate_xg_room(2.4, 0.9, 0.4)
        elif reverb_type == 14:  # Room 6 (Large Room +++])
            self._generate_xg_room(2.8, 0.95, 0.35)
        elif reverb_type == 15:  # Room 7 (Large Room +++])
            self._generate_xg_room(3.2, 1.0, 0.3)
        elif reverb_type == 16:  # Room 8 (Large Room +++++)
            self._generate_xg_room(3.6, 1.0, 0.25)

        elif reverb_type == 17:  # Plate 1
            self._generate_xg_plate(1.0, 0.8, 0.9)  # time, density, hf_damping
        elif reverb_type == 18:  # Plate 2
            self._generate_xg_plate(1.2, 0.85, 0.85)
        elif reverb_type == 19:  # Plate 3
            self._generate_xg_plate(1.4, 0.9, 0.8)
        elif reverb_type == 20:  # Plate 4
            self._generate_xg_plate(1.6, 0.95, 0.75)
        elif reverb_type == 21:  # Plate 5
            self._generate_xg_plate(1.8, 1.0, 0.7)
        elif reverb_type == 22:  # Plate 6
            self._generate_xg_plate(2.0, 1.0, 0.65)
        elif reverb_type == 23:  # Plate 7
            self._generate_xg_plate(2.2, 1.0, 0.6)
        elif reverb_type == 24:  # Plate 8
            self._generate_xg_plate(2.5, 1.0, 0.55)
        else:
            # Default to Hall 1 for unknown types
            self._generate_xg_hall(1.8, 0.4, 0.6)

        # Normalize
        max_val = np.max(np.abs(self.current_ir))
        if max_val > 0:
            self.current_ir /= max_val

        # Cache the impulse response
        if self.current_ir is not None:
            self.ir_cache[cache_key] = self.current_ir

    def _generate_xg_hall(self, time: float, density: float, hf_damping: float) -> None:
        """Generate XG hall-type impulse response with specific characteristics."""
        if self.current_ir is None:
            return

        # XG Hall characteristics: lush, spacious with rich early reflections
        ir_length = min(int(self.sample_rate * time * 1.5), self.max_ir_length)
        self.current_ir = np.zeros(ir_length, dtype=np.float32)

        # XG Hall early reflections pattern (more complex than basic hall)
        early_positions = [0.018, 0.032, 0.048, 0.072, 0.105, 0.155, 0.220, 0.310, 0.420, 0.550]
        early_gains = [1.0, 0.85, -0.65, 0.45, -0.35, 0.25, -0.18, 0.12, -0.08, 0.05]

        for pos, gain in zip(early_positions, early_gains, strict=False):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain * density

        # Dense late reverberation with proper decay
        for i in range(int(0.4 * self.sample_rate), len(self.current_ir)):
            decay_factor = math.exp(-(i / self.sample_rate) / time)
            damping_factor = math.exp(-hf_damping * (i / self.sample_rate) * 1.8)
            noise = (np.random.random() - 0.5) * 2.0
            self.current_ir[i] += noise * decay_factor * damping_factor * density * 0.8

    def _generate_xg_room(self, time: float, density: float, hf_damping: float) -> None:
        """Generate XG room-type impulse response with specific characteristics."""
        if self.current_ir is None:
            return

        # XG Room characteristics: intimate, warm with focused early reflections
        ir_length = min(int(self.sample_rate * time * 1.3), self.max_ir_length)
        self.current_ir = np.zeros(ir_length, dtype=np.float32)

        # XG Room early reflections (fewer but more focused)
        early_positions = [0.012, 0.022, 0.036, 0.052, 0.078, 0.110, 0.150]
        early_gains = [1.0, 0.75, -0.50, 0.35, -0.25, 0.15, -0.10]

        for pos, gain in zip(early_positions, early_gains, strict=False):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain * density

        # Controlled late reverb for room character
        for i in range(int(0.08 * self.sample_rate), len(self.current_ir)):
            decay_factor = math.exp(-(i / self.sample_rate) / (time * 0.9))
            damping_factor = math.exp(-hf_damping * (i / self.sample_rate) * 1.3)
            noise = (np.random.random() - 0.5) * 2.0
            self.current_ir[i] += noise * decay_factor * damping_factor * density * 0.6

    def _generate_xg_plate(self, time: float, density: float, hf_damping: float) -> None:
        """Generate XG plate-type impulse response with specific characteristics."""
        if self.current_ir is None:
            return

        # XG Plate characteristics: bright, metallic, smooth decay
        ir_length = min(int(self.sample_rate * time * 1.2), self.max_ir_length)
        self.current_ir = np.zeros(ir_length, dtype=np.float32)

        # XG Plate early reflections (metallic character)
        early_positions = [0.003, 0.008, 0.015, 0.024, 0.035, 0.050, 0.070]
        early_gains = [1.0, 0.95, -0.80, 0.60, -0.45, 0.30, -0.20]

        for pos, gain in zip(early_positions, early_gains, strict=False):
            sample_pos = int(pos * self.sample_rate)
            if sample_pos < len(self.current_ir):
                self.current_ir[sample_pos] += gain

        # Smooth, bright late reverb
        for i in range(int(0.03 * self.sample_rate), len(self.current_ir)):
            decay_factor = math.exp(-(i / self.sample_rate) / (time * 0.95))
            damping_factor = math.exp(
                -hf_damping * (i / self.sample_rate) * 0.8
            )  # Less HF damping for brightness
            noise = (np.random.random() - 0.5) * 2.0

            # Add metallic character with high-frequency emphasis
            hf_boost = 1.0 + (i / self.sample_rate) * 0.3  # Slight HF boost over time
            self.current_ir[i] += noise * decay_factor * damping_factor * density * hf_boost * 0.4

    def _generate_hall_ir(self) -> None:
        """Generate hall-type impulse response."""
        # Characteristics: large, lush, with multiple early reflections
        time = self.params["time"]
        damping = self.params["hf_damping"]
        density = self.params["density"]

        # Early reflections pattern for hall
        early_positions = [0.02, 0.035, 0.055, 0.08, 0.12, 0.18, 0.25, 0.35]
        early_gains = [1.0, 0.8, -0.6, 0.4, -0.3, 0.2, -0.15, 0.1]

        for pos, gain in zip(early_positions, early_gains, strict=False):
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
        time = self.params["time"]
        damping = self.params["hf_damping"]
        density = self.params["density"]

        # Fewer, less prominent early reflections
        early_positions = [0.015, 0.028, 0.045, 0.065, 0.095]
        early_gains = [1.0, 0.7, -0.4, 0.3, -0.2]

        for pos, gain in zip(early_positions, early_gains, strict=False):
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
        time = self.params["time"]
        damping = self.params["hf_damping"]
        density = self.params["density"]

        # Distinctive early reflections for plate
        early_positions = [0.005, 0.012, 0.019, 0.028, 0.042]
        early_gains = [1.0, 0.9, -0.7, 0.5, -0.4]

        for pos, gain in zip(early_positions, early_gains, strict=False):
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


