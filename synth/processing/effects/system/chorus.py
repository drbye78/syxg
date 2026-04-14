"""XG System Chorus Processor - stereo chorus with advanced LFO modulation."""

from __future__ import annotations

import threading

import numpy as np

from ..types import XGChorusType


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
        Initialize XG chorus processor with all 6 XG chorus types.

        Args:
            sample_rate: Sample rate in Hz
            max_delay_samples: Maximum delay line length in samples
        """
        self.sample_rate = sample_rate
        self.max_delay_samples = max_delay_samples

        # XG chorus type definitions with default parameters
        self.chorus_type_presets = {
            0: {  # Chorus 1
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "delay": 0.012,
                "cross_feedback": 0.0,
                "lfo_waveform": 0,
                "phase_diff": 90.0,
            },
            1: {  # Chorus 2
                "rate": 0.8,
                "depth": 0.6,
                "feedback": 0.4,
                "delay": 0.015,
                "cross_feedback": 0.1,
                "lfo_waveform": 0,
                "phase_diff": 120.0,
            },
            2: {  # Celeste 1
                "rate": 0.5,
                "depth": 0.7,
                "feedback": 0.2,
                "delay": 0.008,
                "cross_feedback": 0.0,
                "lfo_waveform": 1,
                "phase_diff": 180.0,  # Triangle wave
            },
            3: {  # Celeste 2
                "rate": 0.3,
                "depth": 0.8,
                "feedback": 0.3,
                "delay": 0.010,
                "cross_feedback": 0.2,
                "lfo_waveform": 1,
                "phase_diff": 150.0,
            },
            4: {  # Flanger 1
                "rate": 0.2,
                "depth": 0.9,
                "feedback": 0.7,
                "delay": 0.002,
                "cross_feedback": 0.0,
                "lfo_waveform": 0,
                "phase_diff": 0.0,
            },
            5: {  # Flanger 2
                "rate": 0.15,
                "depth": 1.0,
                "feedback": 0.8,
                "delay": 0.003,
                "cross_feedback": 0.3,
                "lfo_waveform": 2,
                "phase_diff": 45.0,  # Square wave
            },
        }

        # XG chorus parameters
        self.params = {
            "chorus_type": XGChorusType.CHORUS_1.value,  # Type 0-5
            "rate": 1.0,  # LFO rate in Hz (0.125-10.0)
            "depth": 0.5,  # Modulation depth (0-1)
            "feedback": 0.3,  # Feedback amount (-0.5 to +0.5)
            "level": 0.4,  # Wet/dry mix level (0-1)
            "delay": 0.012,  # Base delay in seconds
            "cross_feedback": 0.0,  # Cross-feedback between channels (0-1)
            "lfo_waveform": 0,  # LFO waveform (0=sine, 1=triangle, 2=square, 3=saw)
            "phase_diff": 90.0,  # Phase difference in degrees
            "enabled": True,
        }

        # Apply initial type settings
        self._apply_chorus_type_preset(XGChorusType.CHORUS_1.value)

    def _apply_chorus_type_preset(self, chorus_type: int) -> None:
        """
        Apply XG chorus type preset parameters.

        Args:
            chorus_type: XG chorus type (0-5)
        """
        if chorus_type in self.chorus_type_presets:
            preset = self.chorus_type_presets[chorus_type]
            for param, value in preset.items():
                self.params[param] = value
            self.param_updated = True

        # Delay lines for stereo processing
        self.left_delay_line = np.zeros(self.max_delay_samples, dtype=np.float32)
        self.right_delay_line = np.zeros(self.max_delay_samples, dtype=np.float32)
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

            # Special handling for chorus_type - apply preset
            if param == "chorus_type":
                chorus_type = int(value)
                if 0 <= chorus_type <= 5:
                    self._apply_chorus_type_preset(chorus_type)
                    return True
                return False

            self.params[param] = value
            self.param_updated = True
            return True

    def set_chorus_type(self, chorus_type: int) -> bool:
        """
        Set XG chorus type (0-5).

        Args:
            chorus_type: XG chorus type (0=Chorus 1, 1=Chorus 2, 2=Celeste 1,
                           3=Celeste 2, 4=Flanger 1, 5=Flanger 2)

        Returns:
            True if type was set successfully
        """
        return self.set_parameter("chorus_type", chorus_type)

    def _generate_lfo_tables(self) -> dict[str, np.ndarray]:
        """Pre-compute LFO waveform tables for better performance."""
        # Generate one cycle of each waveform
        table_size = 1024
        phases = np.linspace(0, 2 * np.pi, table_size, endpoint=False)

        return {
            "sine": np.sin(phases),
            "triangle": 2 * np.abs((phases / (2 * np.pi) * 4) % 4 - 2) - 1,
            "square": np.sign(np.sin(phases)),
            "saw": 2 * (phases / (2 * np.pi) % 1) - 1,
        }

    def _get_lfo_value(self, phase: float, waveform: int) -> float:
        """Get LFO value for given phase and waveform type."""
        table_size = len(self._lfo_tables["sine"])
        table_index = int((phase % (2 * np.pi)) / (2 * np.pi) * table_size) % table_size

        if waveform == 0:  # Sine
            return self._lfo_tables["sine"][table_index]
        elif waveform == 1:  # Triangle
            return self._lfo_tables["triangle"][table_index]
        elif waveform == 2:  # Square
            return self._lfo_tables["square"][table_index]
        else:  # Sawtooth
            return self._lfo_tables["saw"][table_index]

    def apply_system_effects_to_mix_zero_alloc(
        self, stereo_mix: np.ndarray, num_samples: int
    ) -> None:
        """
        Apply system chorus to the final stereo mix (in-place processing).

        Args:
            stereo_mix: Input/output stereo mix buffer (N, 2)
            num_samples: Number of samples to process
        """
        if not self.params["enabled"] or self.params["level"] <= 0.001:
            return

        with self.lock:
            # Apply chorus processing in blocks
            self._process_chorus_block(stereo_mix, num_samples)

    def _process_chorus_block(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Process a block of samples through chorus modulation."""
        rate = self.params["rate"]
        depth = self.params["depth"]
        feedback = self.params["feedback"] / 127.0 * 0.5  # Scale feedback
        level = self.params["level"]
        delay = self.params["delay"]
        cross_feedback = self.params["cross_feedback"] / 127.0 * 0.5
        lfo_waveform = int(self.params["lfo_waveform"])
        phase_diff_degrees = self.params["phase_diff"]

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


