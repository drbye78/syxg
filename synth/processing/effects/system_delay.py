"""SystemDelayEffect — SC-8850 System Delay processor."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# SC-8850 Delay types
DELAY_TYPES = {
    0: "delay_1",
    1: "delay_2",
    2: "delay_3",
    3: "pan_delay_1",
    4: "pan_delay_2",
    5: "pan_delay_3",
    6: "long_delay_1",
    7: "long_delay_2",
    8: "long_delay_3",
    9: "modulation_delay",
}


class SystemDelayEffect:
    """SC-8850 System Delay effect.

    Simple stereo delay processor supporting 10 SC-8850 delay types.
    Parallel to reverb/chorus in the system effects section.
    """

    def __init__(self, sample_rate: int, max_delay_seconds: float = 5.0):
        self.sample_rate = sample_rate
        self.max_samples = int(max_delay_seconds * sample_rate)
        # Pre-allocated delay buffers (zero-alloc in hot path)
        self._delay_buf_l = np.zeros(self.max_samples, dtype=np.float32)
        self._delay_buf_r = np.zeros(self.max_samples, dtype=np.float32)
        self._write_pos = 0

        # Parameters
        self.delay_type: int = 0  # 0-9
        self.time: float = 400.0  # ms
        self.feedback: float = 0.3  # 0.0-1.0
        self.level: float = 0.5  # 0.0-1.0
        self.rate: float = 0.5  # Hz (for modulation delay)
        self.depth: float = 0.3  # 0.0-1.0 (for modulation delay)
        self.high_damp: float = 0.3

        # Modulation delay state
        self._phase: float = 0.0

    def set_delay_type(self, delay_type: int) -> None:
        """Set delay type (0-9 mapping to SC-8850 delay types)."""
        self.delay_type = max(0, min(9, delay_type))

    def set_parameter(self, param_name: str, value: Any) -> None:
        """Set a parameter by name."""
        if hasattr(self, param_name):
            setattr(self, param_name, float(value))

    def get_delay_samples(self) -> int:
        """Get the delay tap in samples based on current type and time."""
        type_modifiers = {
            0: 1.0,  # delay_1
            1: 1.5,  # delay_2
            2: 0.5,  # delay_3
            3: 1.0,  # pan_delay_1
            4: 1.5,  # pan_delay_2
            5: 0.5,  # pan_delay_3
            6: 4.0,  # long_delay_1
            7: 6.0,  # long_delay_2
            8: 8.0,  # long_delay_3
            9: 1.0,  # modulation_delay
        }
        modifier = type_modifiers.get(self.delay_type, 1.0)
        delay_ms = self.time * modifier
        return int(delay_ms * self.sample_rate / 1000.0)

    def process(
        self,
        input_l: np.ndarray,
        input_r: np.ndarray,
        output_l: np.ndarray,
        output_r: np.ndarray,
        num_samples: int,
    ) -> None:
        """Process stereo audio through the delay effect.

        Args:
            input_l: Left input channel buffer (read-only)
            input_r: Right input channel buffer (read-only)
            output_l: Left output buffer (written to)
            output_r: Right output buffer (written to)
            num_samples: Number of samples to process
        """
        delay_samples = self.get_delay_samples()
        if delay_samples < 1 or delay_samples >= self.max_samples:
            return

        is_pan_delay = 3 <= self.delay_type <= 5
        is_mod_delay = self.delay_type == 9

        for i in range(num_samples):
            wp = self._write_pos

            # Read from delay line
            read_pos = (wp - delay_samples) % self.max_samples
            delayed_l = self._delay_buf_l[read_pos]
            delayed_r = self._delay_buf_r[read_pos]

            # Modulation delay: add LFO to delay time
            if is_mod_delay:
                mod = self.depth * self.max_samples * 0.1
                self._phase += 2.0 * np.pi * self.rate / self.sample_rate
                if self._phase > 2.0 * np.pi:
                    self._phase -= 2.0 * np.pi
                mod_offset = int(mod * (1.0 + np.sin(self._phase)))
                mod_read = (wp - min(delay_samples + mod_offset, self.max_samples - 1)) % self.max_samples
                delayed_l = self._delay_buf_l[mod_read]
                delayed_r = self._delay_buf_r[mod_read]

            # Apply high damp filter (simple one-pole)
            delayed_l *= 1.0 - self.high_damp * 0.3
            delayed_r *= 1.0 - self.high_damp * 0.3

            # Write input + feedback to delay line
            fb = self.feedback * 0.7
            self._delay_buf_l[wp] = input_l[i] + delayed_l * fb
            self._delay_buf_r[wp] = input_r[i] + delayed_r * fb

            # Output = delayed signal * level
            output_l[i] = delayed_l * self.level
            output_r[i] = delayed_r * self.level

            # Pan delay: ping-pong between channels
            if is_pan_delay:
                self._delay_buf_l[wp] += delayed_r * fb * 0.5
                self._delay_buf_r[wp] += delayed_l * fb * 0.5

            self._write_pos = (wp + 1) % self.max_samples

    def reset(self) -> None:
        """Reset delay buffers and state."""
        self._delay_buf_l.fill(0.0)
        self._delay_buf_r.fill(0.0)
        self._write_pos = 0
        self._phase = 0.0
