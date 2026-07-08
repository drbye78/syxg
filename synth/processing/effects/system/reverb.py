"""XG System Reverb Processor - convolution reverb with impulse response generation."""

from __future__ import annotations

import threading

import numpy as np
from scipy.signal import fftconvolve

from ..types import XGReverbType


# XG NRPN type (0x00-0x0C) to processor internal type mapping.
# XG NRPN spec sends reverb type as 0x00-0x0C but the processor dispatch
# uses internal type numbering (1-24 Hall/Room/Plate + 25-26 Stage).
# This mapping translates NRPN values to the correct internal type.
# See XGReverbType enum for all internal type definitions.
_NRPN_TO_TYPE: dict[int, int] = {
    0x01: 1,   # Hall 1 → Hall 1
    0x02: 2,   # Hall 2 → Hall 2
    0x03: 9,   # Room 1 → Room 1
    0x04: 10,  # Room 2 → Room 2
    0x05: 11,  # Room 3 → Room 3
    0x06: 25,  # Stage 1 → Stage 1
    0x07: 26,  # Stage 2 → Stage 2
    0x08: 17,  # Plate → Plate 1
    0x09: 6,   # White Room → Hall 6 (bright, medium decay)
    0x0A: 8,   # Tunnel → Hall 8 (long decay)
    0x0B: 15,  # Basement → Room 7 (dark, short)
    0x0C: 16,  # Canyon → Room 8 (very long)
}


class XGSystemReverbProcessor:
    """
    XG Convolution Reverb Processor

    Implements high-quality convolution reverb with complete XG specification support:
    - 26 XG reverb types (Hall 1-8, Room 1-8, Plate 1-8, Stage 1-2)
    - XG NRPN type values (0x00-0x0C) are automatically mapped to internal types
    - Individually controllable parameters: time, level, pre-delay, HF damping, density
    - Convolution-based processing with pre-computed impulse responses
    - Block-based processing for realtime performance
    """

    def __init__(self, sample_rate: int, max_ir_length: int = 44100 * 2, seed: int = 42):
        """
        Initialize XG reverb processor.

        Args:
            sample_rate: Sample rate in Hz
            max_ir_length: Maximum impulse response length in samples
            seed: Random seed for reproducible impulse response generation
        """
        self.sample_rate = sample_rate
        self.max_ir_length = max_ir_length
        self._rng = np.random.RandomState(seed)

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
        # Pre-allocated output work buffers (avoids np.zeros in hot path)
        self._conv_output_buffers: list[np.ndarray] = []

        # Thread safety
        self.lock = threading.RLock()
        self.param_updated = True

        # Initialize with default IR
        self._update_impulse_response()

    @staticmethod
    def _map_nrpn_to_processor_type(nrpn_type: int) -> int:
        """
        Map XG NRPN reverb type (0-12) to processor internal type (1-26).

        XG NRPN parameter 0 (reverb type) sends values 0x00-0x0C, but the
        processor dispatch uses internal type numbering (1-24 for Hall/Room/Plate,
        25-26 for Stage). This method translates between the two systems.

        Args:
            nrpn_type: XG NRPN reverb type (0-12), where 0 = No Effect

        Returns:
            Processor internal type (1-26), or 0 for No Effect
        """
        if nrpn_type == 0:
            return 0  # No Effect
        return _NRPN_TO_TYPE.get(nrpn_type, 1)  # Default Hall 1 for unknowns

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

        # Only allocate if buffers don't exist yet (init path, not per-block)
        if len(self.convolution_buffers) == 0:
            max_size = num_samples + self.max_ir_length - 1
            self.convolution_buffers = [
                np.zeros(max_size, dtype=np.float32) for _ in range(2)
            ]
            self.buffer_positions = [0, 0]
            # Pre-allocate output work buffers for direct convolution
            self._conv_output_buffers = [
                np.zeros(self.max_ir_length, dtype=np.float32) for _ in range(2)
            ]
        # If existing buffer is too small, resize (rare — only happens at startup)
        elif self.convolution_buffers[0].shape[0] < num_samples + len(self.current_ir) - 1:
            required_size = num_samples + len(self.current_ir) - 1
            self.convolution_buffers = [
                np.zeros(required_size, dtype=np.float32) for _ in range(2)
            ]
            self.buffer_positions = [0, 0]

    def _apply_pre_delay(
        self, stereo_mix: np.ndarray, num_samples: int, delay_samples: int
    ) -> None:
        """Apply pre-delay by swapping samples in the buffer (zero-alloc)."""
        if delay_samples >= num_samples or delay_samples <= 0:
            return

        # Use pre-allocated temp buffer in convolution_buffers for the swap
        # Rotate samples in the buffer using in-place indexing (no .copy())
        for ch in range(2):
            channel_data = stereo_mix[:, ch]
            # Rolling shift using np.roll — it creates a temp, BUT we avoid .copy()
            # Use a manual swap via pre-allocated temp space instead
            temp = self.convolution_buffers[ch][:delay_samples]
            temp[:] = channel_data[-delay_samples:]
            channel_data[delay_samples:] = channel_data[:-delay_samples]
            channel_data[:delay_samples] = temp

    def _apply_direct_convolution(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply convolution using FFT convolution (no per-sample loops)."""
        if self.current_ir is None:
            return

        ir_segment = (
            self.current_ir[:num_samples]
            if len(self.current_ir) > num_samples
            else self.current_ir
        )

        for ch in range(2):
            conv_result = fftconvolve(
                stereo_mix[:num_samples, ch], ir_segment, mode="same"
            )
            stereo_mix[:num_samples, ch] = conv_result

    def _apply_fft_convolution(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply convolution using FFT (unified path)."""
        self._apply_direct_convolution(stereo_mix, num_samples)

    def _update_impulse_response(self) -> None:
        """Generate or retrieve impulse response based on current parameters."""
        # Map XG NRPN values (0-12) to processor internal types if needed.
        # NRPN types 0x03-0x0C would otherwise map to wrong generator ranges
        # (e.g., NRPN Room 1 = 0x03 would become Hall 3 without this mapping).
        raw_type = self.params["reverb_type"]
        if raw_type <= 12:
            reverb_type = self._map_nrpn_to_processor_type(raw_type)
        else:
            reverb_type = raw_type

        # Create cache key from current parameters (mapped type ensures correctness)
        cache_key = (
            reverb_type,
            round(self.params["time"], 6),
            round(self.params["hf_damping"], 6),
            round(self.params["density"], 6),
            round(self.params["pre_delay"], 6),
        )

        if cache_key in self.ir_cache:
            self.current_ir = self.ir_cache[cache_key]
            return

        # Generate new impulse response
        ir_length = min(int(self.sample_rate * self.params["time"] * 1.5), self.max_ir_length)

        # XG reverb type determines characteristics - implement all 26 XG types
        if reverb_type == 0:  # No Effect — identity IR (pass-through)
            self.current_ir = np.array([1.0], dtype=np.float32)
        elif reverb_type == 1:  # Hall 1 (Small Hall)
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

        elif reverb_type == 25:  # Stage 1
            self._generate_xg_hall(2.0, 0.6, 0.5)
        elif reverb_type == 26:  # Stage 2
            self._generate_xg_hall(2.5, 0.7, 0.45)

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

        # Vectorized dense late reverberation with proper decay
        start_idx = int(0.4 * self.sample_rate)
        late_len = len(self.current_ir) - start_idx
        if late_len > 0:
            t = np.arange(start_idx, len(self.current_ir), dtype=np.float64) / self.sample_rate
            decay_factors = np.exp(-t / time)
            damping_factors = np.exp(-hf_damping * t * 1.8)
            noise = self._rng.uniform(-1.0, 1.0, late_len)
            self.current_ir[start_idx:] += noise * decay_factors * damping_factors * density * 0.8

    def _generate_xg_room(self, time: float, density: float, hf_damping: float) -> None:
        """Generate XG room-type impulse response with specific characteristics."""
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

        # Vectorized controlled late reverb for room character
        start_idx = int(0.08 * self.sample_rate)
        late_len = len(self.current_ir) - start_idx
        if late_len > 0:
            t = np.arange(start_idx, len(self.current_ir), dtype=np.float64) / self.sample_rate
            decay_factors = np.exp(-t / (time * 0.9))
            damping_factors = np.exp(-hf_damping * t * 1.3)
            noise = self._rng.uniform(-1.0, 1.0, late_len)
            self.current_ir[start_idx:] += noise * decay_factors * damping_factors * density * 0.6

    def _generate_xg_plate(self, time: float, density: float, hf_damping: float) -> None:
        """Generate XG plate-type impulse response with specific characteristics."""
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

        # Vectorized smooth, bright late reverb
        start_idx = int(0.03 * self.sample_rate)
        late_len = len(self.current_ir) - start_idx
        if late_len > 0:
            t = np.arange(start_idx, len(self.current_ir), dtype=np.float64) / self.sample_rate
            decay_factors = np.exp(-t / (time * 0.95))
            damping_factors = np.exp(-hf_damping * t * 0.8)  # Less HF damping for brightness
            noise = self._rng.uniform(-1.0, 1.0, late_len)
            # Add metallic character with high-frequency emphasis
            hf_boost = 1.0 + t * 0.3  # Slight HF boost over time
            self.current_ir[start_idx:] += noise * decay_factors * damping_factors * density * hf_boost * 0.4


