"""
XG Low Frequency Oscillator - Production XG-Compliant Implementation

Provides XG-standard LFO modulation sources with enhanced parameter control.
This replaces the old LFO class with full XG compliance for channel-level modulation.
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union

# Pre-computed sine lookup table for ultra-fast LFO processing
_SINE_TABLE_SIZE = 8192
_SINE_TABLE = np.sin(np.linspace(0, 2 * np.pi, _SINE_TABLE_SIZE, dtype=np.float32))


class XGLFO:
    """
    XG-compliant Low Frequency Oscillator with interpretable parameter control.

    XG Specification Compliance:
    - Pitch modulation delay and fade-in parameters
    - Proper XG controller parameter ranges
    - Per-channel LFO resources (not per-note)
    - Enhanced modulation source control
    """

    __slots__ = (
        'id', 'waveform', 'rate', 'depth', 'delay', 'sample_rate',
        'pitch_delay', 'pitch_fade_in', 'pitch_depth', 'tremolo_depth',
        'mod_wheel', 'breath_controller', 'foot_controller', 'channel_aftertouch',
        'key_aftertouch', 'brightness', 'harmonic_content', 'phase',
        'delay_counter', 'delay_samples', 'phase_step', '_last_output', '_dirty'
    )

    # XG LFO Pitch Modulation Parameters
    DEFAULT_PITCH_DELAY = 0.0     # seconds
    DEFAULT_PITCH_FADE_IN = 0.5   # seconds
    DEFAULT_PITCH_DEPTH = 50      # cents
    DEFAULT_TREMOLO_DEPTH = 0.3   # amplitude modulation

    def __init__(self, id: int, waveform: str = "sine", rate: float = 5.0,
                 depth: float = 1.0, delay: float = 0.0, sample_rate: int = 44100):
        """
        Initialize XG-compliant LFO with proper parameter ranges.

        Args:
            id: XG LFO identifier (0, 1, 2 for LFO1, LFO2, LFO3)
            waveform: Waveform type (sine, triangle, square, sawtooth, sample_and_hold)
            rate: Frequency in Hz (0.1 - 20.0 per XG)
            depth: Modulation depth (0.0 - 1.0)
            delay: Delay before modulation starts (0.0 - 5.0 seconds)
            sample_rate: Audio sample rate
        """
        self.id = id
        self.waveform = self._validate_waveform(waveform)
        self.rate = max(0.1, min(20.0, rate))  # XG rate limits
        self.depth = max(0.0, min(1.0, depth))
        self.delay = max(0.0, min(5.0, delay))
        self.sample_rate = sample_rate

        # XG-enhanced modulation parameters
        self.pitch_delay = self.DEFAULT_PITCH_DELAY
        self.pitch_fade_in = self.DEFAULT_PITCH_FADE_IN
        self.pitch_depth = self.DEFAULT_PITCH_DEPTH
        self.tremolo_depth = self.DEFAULT_TREMOLO_DEPTH

        # Statistical modulation sources (must be initialized before _calculate_phase_step)
        self.mod_wheel = 0.0
        self.breath_controller = 0.0
        self.foot_controller = 0.0
        self.channel_aftertouch = 0.0
        self.key_aftertouch = 0.0
        self.brightness = 64
        self.harmonic_content = 64

        # Internal state
        self.phase = 0.0
        self.delay_counter = 0
        self.delay_samples = int(self.delay * sample_rate)
        self.phase_step = self._calculate_phase_step()

        # Cache for performance
        self._last_output = 0.0
        self._dirty = True

    def _validate_waveform(self, waveform: str) -> str:
        """Validate and return supported XG waveform types."""
        valid_waveforms = ["sine", "triangle", "square", "sawtooth", "sample_and_hold"]
        return waveform if waveform in valid_waveforms else "sine"

    def _calculate_phase_step(self) -> float:
        """Calculate phase step with XG controller modulation."""
        # Base frequency with modulation
        base_rate = self.rate

        # XG controller modulation (Sound Controllers can affect LFO rate)
        rate_modulation = (
            (self.mod_wheel - 0.5) * 0.5 +           # Mod wheel ±50%
            (self.breath_controller - 0.5) * 0.4 +   # Breath ±40%
            (self.foot_controller - 0.5) * 0.3 +     # Foot ±30%
            (self.channel_aftertouch - 0.5) * 0.3    # Aftertouch ±30%
        )

        # Brightness affects LFO rate (+/- 2 octaves)
        brightness_factor = ((self.brightness - 64) / 64.0) * 4.0  # ±4 semitones
        rate_multiplier = 2.0 ** (brightness_factor / 12.0)

        modulated_rate = max(0.1, min(20.0, base_rate * rate_multiplier * (1.0 + rate_modulation)))

        # Convert frequency to phase step
        return modulated_rate * 2.0 * math.pi / self.sample_rate

    def set_pitch_modulation(self, delay: Optional[float] = None, fade_in: Optional[float] = None, depth: Optional[int] = None):
        """Set XG pitch modulation parameters per specification."""
        if delay is not None:
            self.pitch_delay = max(0.0, min(5.0, delay))
        if fade_in is not None:
            self.pitch_fade_in = max(0.001, min(5.0, fade_in))
        if depth is not None:
            self.pitch_depth = max(0, min(600, depth))  # XG range 0-600 cents

        self._dirty = True

    def set_tremolo_depth(self, depth: Optional[float] = None):
        """Set XG tremolo depth parameter."""
        if depth is not None:
            self.tremolo_depth = max(0.0, min(1.0, depth))

        self._dirty = True

    # XG Controller Parameter Updates (Sound Controllers 77-79)

    def update_xg_vibrato_rate(self, value: int):
        """XG Sound Controller 77 - Vibrato Rate (LFO Rate)."""
        # 0-127 maps to 0.1-10.0 Hz logarithmically per XG
        if value <= 64:
            lfo_rate = 0.1 + (value / 64.0) * 0.9
        else:
            lfo_rate = 1.0 + ((value - 64) / 63.0) * 9.0

        self.rate = lfo_rate
        self._dirty = True

    def update_xg_vibrato_depth(self, value: int):
        """XG Sound Controller 78 - Vibrato Depth (Pitch modulation)."""
        # 0-127 maps to 0-600 cents linearly per XG
        depth_cents = (value / 127.0) * 600.0
        self.pitch_depth = depth_cents
        self._dirty = True

    def update_xg_vibrato_delay(self, value: int):
        """XG Sound Controller 79 - Vibrato Delay (Pitch modulation delay)."""
        # 0-127 maps to 0-5.0 seconds linearly per XG
        delay_seconds = (value / 127.0) * 5.0
        self.pitch_delay = delay_seconds

        # Recalculate delay samples
        self.delay_samples = int(delay_seconds * self.sample_rate)
        self._dirty = True

    def set_mod_wheel(self, value: float):
        """Set XG modulation wheel (0.0-1.0)."""
        self.mod_wheel = max(0.0, min(1.0, value))
        self._dirty = True

    def set_breath_controller(self, value: float):
        """Set XG breath controller (0.0-1.0)."""
        self.breath_controller = max(0.0, min(1.0, value))
        self._dirty = True

    def set_foot_controller(self, value: float):
        """Set XG foot controller (0.0-1.0)."""
        self.foot_controller = max(0.0, min(1.0, value))
        self._dirty = True

    def set_channel_aftertouch(self, value: float):
        """Set XG channel aftertouch (0.0-1.0)."""
        self.channel_aftertouch = max(0.0, min(1.0, value))
        self._dirty = True

    def set_key_aftertouch(self, value: float):
        """Set XG key (polyphonic) aftertouch (0.0-1.0)."""
        self.key_aftertouch = max(0.0, min(1.0, value))
        self._dirty = True

    def set_brightness(self, value: int):
        """Set XG brightness controller (0-127)."""
        self.brightness = max(0, min(127, value))
        self._dirty = True

    def set_harmonic_content(self, value: int):
        """Set XG harmonic content controller (0-127)."""
        self.harmonic_content = max(0, min(127, value))

    def step(self) -> float:
        """
        Generate next LFO sample with XG pitch modulation delay/fade-in.

        Returns:
            LFO output value (-1.0 to 1.0)
        """
        # Handle modulation delay
        if self.delay_counter < self.delay_samples:
            self.delay_counter += 1
            self._last_output = 0.0
            return 0.0

        # Update parameters if dirty
        if self._dirty:
            self.phase_step = self._calculate_phase_step()
            self._dirty = False

        # Generate base waveform - ULTRA-OPTIMIZED with lookup table
        self.phase = (self.phase + self.phase_step) % (2.0 * math.pi)

        if self.waveform == "sine":
            # ULTRA-OPTIMIZED: Use pre-computed sine lookup table
            phase_index = int((self.phase / (2.0 * math.pi)) * (_SINE_TABLE_SIZE - 1))
            base_output = _SINE_TABLE[phase_index]
        elif self.waveform == "triangle":
            phase_norm = self.phase / (2.0 * math.pi)
            base_output = 1.0 - abs(2.0 * (phase_norm - 0.5))
        elif self.waveform == "square":
            base_output = 1.0 if self.phase < math.pi else -1.0
        elif self.waveform == "sawtooth":
            base_output = (self.phase / math.pi) - 1.0
        elif self.waveform == "sample_and_hold":
            # Simple sample and hold (change every few samples)
            base_output = self._last_output if (self.phase % 0.5) < self.phase_step else (
                1.0 if self.phase % 2.0 < 1.0 else -1.0
            )
        else:
            # ULTRA-OPTIMIZED: Use pre-computed sine lookup table as fallback
            phase_index = int((self.phase / (2.0 * math.pi)) * (_SINE_TABLE_SIZE - 1))
            base_output = _SINE_TABLE[phase_index]

        # Apply XG pitch modulation fade-in
        fade_in_progress = min(1.0, (self.delay_counter - self.delay_samples) /
                              (self.pitch_fade_in * self.sample_rate))
        modulated_depth = self.depth * fade_in_progress

        self._last_output = base_output * modulated_depth
        return self._last_output

    def get_pitch_modulation(self, vibrato_enabled: bool = True) -> float:
        """Get pitch modulation value in cents per XG specification."""
        if not vibrato_enabled or self.pitch_delay > self.delay_counter / self.sample_rate:
            return 0.0

        # Convert LFO output to cents (XG pitch modulation range)
        return self.step() * self.pitch_depth

    def get_tremolo_modulation(self) -> float:
        """Get tremolo (amplitude) modulation."""
        return self.step() * self.tremolo_depth

    def reset(self):
        """Reset LFO state for new note or parameter change."""
        self.phase = 0.0
        self.delay_counter = 0
        self._last_output = 0.0

    def set_parameters(self, waveform: Optional[str] = None, rate: Optional[float] = None,
                      depth: Optional[float] = None, delay: Optional[float] = None):
        """Update LFO parameters dynamically."""
        if waveform is not None:
            self.waveform = self._validate_waveform(waveform)
        if rate is not None:
            self.rate = max(0.1, min(20.0, rate))
            self._dirty = True
        if depth is not None:
            self.depth = max(0.0, min(1.0, depth))
        if delay is not None:
            self.delay = max(0.0, min(5.0, delay))
            self.delay_samples = int(self.delay * self.sample_rate)

        if any([rate is not None, delay is not None]):
            self.reset()


# Maintain backward compatibility for existing code
class LFO(XGLFO):
    """Backward compatibility alias for existing code."""
    pass
