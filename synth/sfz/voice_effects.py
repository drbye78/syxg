"""
SFZ Voice-Level Effects Processing System

Provides per-voice effects processing for SFZ instruments with
professional-quality chorus, reverb, delay, and other effects.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import math


class SFZChorusProcessor:
    """
    Chorus effect processor for per-voice use.

    Features:
    - Multiple chorus algorithms (classic, ensemble, dimension)
    - Configurable delay times and depths
    - Stereo processing with width control
    - Optimized for low CPU usage per voice
    """

    def __init__(self, sample_rate: int, max_delay: int = 1024):
        """
        Initialize chorus processor.

        Args:
            sample_rate: Audio sample rate in Hz
            max_delay: Maximum delay buffer size in samples
        """
        self.sample_rate = sample_rate
        self.max_delay = max_delay

        # Chorus parameters
        self.depth = 0.3  # Modulation depth (0.0-1.0)
        self.rate = 0.25  # LFO rate in Hz
        self.delay = 15.0  # Base delay in ms
        self.width = 0.8  # Stereo width (0.0-1.0)
        self.mix = 0.5  # Wet/dry mix (0.0-1.0)
        self.feedback = 0.0  # Chorus feedback (0.0-0.3)

        # LFO state
        self.lfo_phase = 0.0
        self.lfo_inc = 2.0 * math.pi * self.rate / sample_rate

        # Delay buffers
        self.delay_buffer_left = np.zeros(max_delay)
        self.delay_buffer_right = np.zeros(max_delay)
        self.buffer_pos = 0

        # Current delay times
        self.current_delay_left = self._ms_to_samples(self.delay)
        self.current_delay_right = self._ms_to_samples(self.delay)

    def _ms_to_samples(self, ms: float) -> int:
        """Convert milliseconds to samples."""
        return int((ms / 1000.0) * self.sample_rate)

    def set_parameters(self, params: dict[str, float]) -> None:
        """
        Set chorus parameters.

        Args:
            params: Parameter dictionary
        """
        if 'depth' in params:
            self.depth = max(0.0, min(1.0, params['depth']))
        if 'rate' in params:
            self.rate = max(0.01, min(10.0, params['rate']))
            self.lfo_inc = 2.0 * math.pi * self.rate / self.sample_rate
        if 'delay' in params:
            self.delay = max(1.0, min(50.0, params['delay']))
        if 'width' in params:
            self.width = max(0.0, min(1.0, params['width']))
        if 'mix' in params:
            self.mix = max(0.0, min(1.0, params['mix']))
        if 'feedback' in params:
            self.feedback = max(0.0, min(0.3, params['feedback']))

    def process(self, input_signal: np.ndarray) -> np.ndarray:
        """
        Process audio through chorus effect.

        Args:
            input_signal: Stereo input buffer (block_size, 2)

        Returns:
            Processed stereo output buffer
        """
        if self.mix == 0.0:
            return input_signal.copy()

        block_size = len(input_signal)
        output = np.zeros_like(input_signal)

        for i in range(block_size):
            # Update LFO phase
            self.lfo_phase += self.lfo_inc
            if self.lfo_phase >= 2.0 * math.pi:
                self.lfo_phase -= 2.0 * math.pi

            # Calculate modulation
            modulation = math.sin(self.lfo_phase) * self.depth

            # Calculate delay times with modulation
            base_delay_samples = self._ms_to_samples(self.delay)
            delay_mod_left = modulation * base_delay_samples * 0.5
            delay_mod_right = -modulation * base_delay_samples * 0.5 * self.width

            delay_left = int(base_delay_samples + delay_mod_left)
            delay_right = int(base_delay_samples + delay_mod_right)

            # Ensure delays are within bounds
            delay_left = max(1, min(self.max_delay - 1, delay_left))
            delay_right = max(1, min(self.max_delay - 1, delay_right))

            # Read from delay buffers
            read_pos_left = (self.buffer_pos - delay_left) % self.max_delay
            read_pos_right = (self.buffer_pos - delay_right) % self.max_delay

            delayed_left = self.delay_buffer_left[read_pos_left]
            delayed_right = self.delay_buffer_right[read_pos_right]

            # Apply feedback
            input_left = input_signal[i, 0] + delayed_left * self.feedback
            input_right = input_signal[i, 1] + delayed_right * self.feedback

            # Write to delay buffers
            self.delay_buffer_left[self.buffer_pos] = input_left
            self.delay_buffer_right[self.buffer_pos] = input_right

            # Mix wet and dry signals
            output[i, 0] = input_signal[i, 0] * (1.0 - self.mix) + delayed_left * self.mix
            output[i, 1] = input_signal[i, 1] * (1.0 - self.mix) + delayed_right * self.mix

            # Update buffer position
            self.buffer_pos = (self.buffer_pos + 1) % self.max_delay

        return output

    def reset(self) -> None:
        """Reset chorus processor state."""
        self.lfo_phase = 0.0
        self.delay_buffer_left.fill(0.0)
        self.delay_buffer_right.fill(0.0)
        self.buffer_pos = 0


class SFZReverbProcessor:
    """
    Reverb effect processor optimized for per-voice use.

    Features:
    - Algorithmic reverb with adjustable room size
    - Pre-delay and decay time control
    - High-frequency damping
    - Stereo processing
    """

    def __init__(self, sample_rate: int, max_delay: int = 44100):
        """
        Initialize reverb processor.

        Args:
            sample_rate: Audio sample rate in Hz
            max_delay: Maximum delay buffer size in samples
        """
        self.sample_rate = sample_rate
        self.max_delay = max_delay

        # Reverb parameters
        self.room_size = 0.5  # Room size (0.0-1.0)
        self.damping = 0.5  # High frequency damping (0.0-1.0)
        self.wet_level = 0.3  # Wet signal level (0.0-1.0)
        self.dry_level = 0.7  # Dry signal level (0.0-1.0)
        self.width = 0.8  # Stereo width (0.0-1.0)
        self.pre_delay = 10.0  # Pre-delay in ms

        # Reverb state
        self.comb_filters_left = []
        self.comb_filters_right = []
        self.allpass_filters_left = []
        self.allpass_filters_right = []

        # Pre-delay buffer
        self.pre_delay_buffer = np.zeros(self._ms_to_samples(100.0))  # 100ms max
        self.pre_delay_pos = 0
        self.pre_delay_samples = self._ms_to_samples(self.pre_delay)

        self._initialize_filters()

    def _ms_to_samples(self, ms: float) -> int:
        """Convert milliseconds to samples."""
        return int((ms / 1000.0) * self.sample_rate)

    def _initialize_filters(self) -> None:
        """Initialize comb and allpass filters for reverb."""
        # Freeverb-style filter delays (scaled for smaller rooms)
        comb_delays = [1557, 1617, 1491, 1422, 1277, 1356, 1188, 1116]  # Base delays
        allpass_delays = [225, 556, 441, 341]  # Allpass delays

        # Scale delays based on room size
        scale_factor = 0.3 + self.room_size * 0.7  # 0.3 to 1.0

        # Initialize comb filters
        self.comb_filters_left = []
        self.comb_filters_right = []

        for i, delay in enumerate(comb_delays):
            scaled_delay = int(delay * scale_factor)
            scaled_delay = max(10, min(self.max_delay, scaled_delay))

            # Alternate left/right for stereo spread
            if i % 2 == 0:
                self.comb_filters_left.append(self._create_comb_filter(scaled_delay))
                self.comb_filters_right.append(self._create_comb_filter(scaled_delay + 23))  # Slight offset
            else:
                self.comb_filters_right.append(self._create_comb_filter(scaled_delay))
                self.comb_filters_left.append(self._create_comb_filter(scaled_delay + 23))

        # Initialize allpass filters
        self.allpass_filters_left = []
        self.allpass_filters_right = []

        for delay in allpass_delays:
            scaled_delay = int(delay * scale_factor)
            scaled_delay = max(5, min(self.max_delay // 4, scaled_delay))

            self.allpass_filters_left.append(self._create_allpass_filter(scaled_delay))
            self.allpass_filters_right.append(self._create_allpass_filter(scaled_delay + 5))

    def _create_comb_filter(self, delay_samples: int) -> dict[str, Any]:
        """Create a comb filter for reverb."""
        return {
            'buffer': np.zeros(delay_samples),
            'pos': 0,
            'delay': delay_samples,
            'feedback': 0.84,  # Standard freeverb feedback
            'damp': self.damping
        }

    def _create_allpass_filter(self, delay_samples: int) -> dict[str, Any]:
        """Create an allpass filter for reverb."""
        return {
            'buffer': np.zeros(delay_samples),
            'pos': 0,
            'delay': delay_samples,
            'feedback': 0.5  # Allpass feedback
        }

    def set_parameters(self, params: dict[str, float]) -> None:
        """
        Set reverb parameters.

        Args:
            params: Parameter dictionary
        """
        if 'room_size' in params:
            old_room_size = self.room_size
            self.room_size = max(0.0, min(1.0, params['room_size']))
            if self.room_size != old_room_size:
                self._initialize_filters()  # Reinitialize with new room size

        if 'damping' in params:
            self.damping = max(0.0, min(1.0, params['damping']))
            # Update damping on existing filters
            for filt in self.comb_filters_left + self.comb_filters_right:
                filt['damp'] = self.damping

        if 'wet_level' in params:
            self.wet_level = max(0.0, min(1.0, params['wet_level']))
        if 'dry_level' in params:
            self.dry_level = max(0.0, min(1.0, params['dry_level']))
        if 'width' in params:
            self.width = max(0.0, min(1.0, params['width']))
        if 'pre_delay' in params:
            self.pre_delay = max(0.0, min(100.0, params['pre_delay']))
            self.pre_delay_samples = self._ms_to_samples(self.pre_delay)

    def process(self, input_signal: np.ndarray) -> np.ndarray:
        """
        Process audio through reverb effect.

        Args:
            input_signal: Stereo input buffer (block_size, 2)

        Returns:
            Processed stereo output buffer
        """
        if self.wet_level == 0.0 and self.dry_level == 1.0:
            return input_signal.copy()

        block_size = len(input_signal)
        output = np.zeros_like(input_signal)

        for i in range(block_size):
            # Apply pre-delay
            pre_delay_pos = (self.pre_delay_pos - self.pre_delay_samples) % len(self.pre_delay_buffer)
            pre_delayed_left = self.pre_delay_buffer[pre_delay_pos] if self.pre_delay_samples > 0 else input_signal[i, 0]
            pre_delayed_right = self.pre_delay_buffer[pre_delay_pos] if self.pre_delay_samples > 0 else input_signal[i, 1]

            # Store input in pre-delay buffer
            self.pre_delay_buffer[self.pre_delay_pos] = (input_signal[i, 0] + input_signal[i, 1]) * 0.5
            self.pre_delay_pos = (self.pre_delay_pos + 1) % len(self.pre_delay_buffer)

            # Process through comb filters
            comb_left = comb_right = 0.0

            for filt in self.comb_filters_left:
                comb_left += self._process_comb_filter(filt, pre_delayed_left)
            for filt in self.comb_filters_right:
                comb_right += self._process_comb_filter(filt, pre_delayed_right)

            # Scale comb outputs
            comb_left *= 0.015  # Freeverb scaling
            comb_right *= 0.015

            # Process through allpass filters
            for filt in self.allpass_filters_left:
                comb_left = self._process_allpass_filter(filt, comb_left)
            for filt in self.allpass_filters_right:
                comb_right = self._process_allpass_filter(filt, comb_right)

            # Apply stereo width
            mid = (comb_left + comb_right) * 0.5
            side = (comb_left - comb_right) * 0.5 * self.width
            wet_left = mid + side
            wet_right = mid - side

            # Mix wet and dry signals
            output[i, 0] = input_signal[i, 0] * self.dry_level + wet_left * self.wet_level
            output[i, 1] = input_signal[i, 1] * self.dry_level + wet_right * self.wet_level

        return output

    def _process_comb_filter(self, filt: dict[str, Any], input_sample: float) -> float:
        """Process sample through comb filter."""
        buffer = filt['buffer']
        pos = filt['pos']
        delay = filt['delay']

        # Read delayed sample
        delayed = buffer[pos]

        # Apply damping
        damped = delayed * (1.0 - filt['damp'])

        # Calculate output
        output = input_sample + damped * filt['feedback']

        # Store in buffer
        buffer[pos] = output

        # Update position
        filt['pos'] = (pos + 1) % delay

        return output

    def _process_allpass_filter(self, filt: dict[str, Any], input_sample: float) -> float:
        """Process sample through allpass filter."""
        buffer = filt['buffer']
        pos = filt['pos']
        delay = filt['delay']

        # Read delayed sample
        delayed = buffer[pos]

        # Calculate output
        output = input_sample * -filt['feedback'] + delayed
        buffer[pos] = input_sample + delayed * filt['feedback']

        # Update position
        filt['pos'] = (pos + 1) % delay

        return output

    def reset(self) -> None:
        """Reset reverb processor state."""
        # Clear all filter buffers
        for filt in self.comb_filters_left + self.comb_filters_right:
            filt['buffer'].fill(0.0)
            filt['pos'] = 0

        for filt in self.allpass_filters_left + self.allpass_filters_right:
            filt['buffer'].fill(0.0)
            filt['pos'] = 0

        # Clear pre-delay buffer
        self.pre_delay_buffer.fill(0.0)
        self.pre_delay_pos = 0


class SFZDelayProcessor:
    """
    Delay effect processor for per-voice use.

    Features:
    - Configurable delay time and feedback
    - High-frequency damping
    - Stereo ping-pong option
    - Optimized for low latency
    """

    def __init__(self, sample_rate: int, max_delay: int = 44100):
        """
        Initialize delay processor.

        Args:
            sample_rate: Audio sample rate in Hz
            max_delay: Maximum delay buffer size in samples
        """
        self.sample_rate = sample_rate
        self.max_delay = max_delay

        # Delay parameters
        self.delay_time = 300.0  # Delay time in ms
        self.feedback = 0.3  # Feedback amount (0.0-0.9)
        self.wet_level = 0.4  # Wet signal level (0.0-1.0)
        self.dry_level = 0.6  # Dry signal level (0.0-1.0)
        self.ping_pong = False  # Stereo ping-pong mode

        # Calculate delay in samples
        self.delay_samples = self._ms_to_samples(self.delay_time)

        # Delay buffers
        self.delay_buffer_left = np.zeros(max_delay)
        self.delay_buffer_right = np.zeros(max_delay)
        self.buffer_pos = 0

        # High-frequency damping
        self.damping = 0.1  # Damping coefficient (0.0-0.5)
        self.damp_state_left = 0.0
        self.damp_state_right = 0.0

    def _ms_to_samples(self, ms: float) -> int:
        """Convert milliseconds to samples."""
        return int((ms / 1000.0) * self.sample_rate)

    def set_parameters(self, params: dict[str, float]) -> None:
        """
        Set delay parameters.

        Args:
            params: Parameter dictionary
        """
        if 'delay_time' in params:
            self.delay_time = max(1.0, min(2000.0, params['delay_time']))
            self.delay_samples = self._ms_to_samples(self.delay_time)

        if 'feedback' in params:
            self.feedback = max(0.0, min(0.9, params['feedback']))

        if 'wet_level' in params:
            self.wet_level = max(0.0, min(1.0, params['wet_level']))

        if 'dry_level' in params:
            self.dry_level = max(0.0, min(1.0, params['dry_level']))

        if 'ping_pong' in params:
            self.ping_pong = bool(params['ping_pong'])

        if 'damping' in params:
            self.damping = max(0.0, min(0.5, params['damping']))

    def process(self, input_signal: np.ndarray) -> np.ndarray:
        """
        Process audio through delay effect.

        Args:
            input_signal: Stereo input buffer (block_size, 2)

        Returns:
            Processed stereo output buffer
        """
        if self.wet_level == 0.0 and self.dry_level == 1.0:
            return input_signal.copy()

        block_size = len(input_signal)
        output = np.zeros_like(input_signal)

        for i in range(block_size):
            # Calculate read positions
            read_pos = (self.buffer_pos - self.delay_samples) % self.max_delay

            # Read delayed samples
            delayed_left = self.delay_buffer_left[read_pos]
            delayed_right = self.delay_buffer_right[read_pos]

            # Apply high-frequency damping
            self.damp_state_left = self.damp_state_left * (1.0 - self.damping) + delayed_left * self.damping
            damped_left = delayed_left - self.damp_state_left

            if self.ping_pong:
                self.damp_state_right = self.damp_state_right * (1.0 - self.damping) + delayed_right * self.damping
                damped_right = delayed_right - self.damp_state_right
            else:
                damped_right = damped_left  # Mono damping for stereo

            # Calculate feedback input
            if self.ping_pong:
                # Ping-pong: left to right, right to left
                fb_left = input_signal[i, 0] + damped_right * self.feedback
                fb_right = input_signal[i, 1] + damped_left * self.feedback
            else:
                # Normal stereo delay
                fb_left = input_signal[i, 0] + damped_left * self.feedback
                fb_right = input_signal[i, 1] + damped_right * self.feedback

            # Store in delay buffers
            self.delay_buffer_left[self.buffer_pos] = fb_left
            self.delay_buffer_right[self.buffer_pos] = fb_right

            # Mix wet and dry signals
            output[i, 0] = input_signal[i, 0] * self.dry_level + damped_left * self.wet_level
            output[i, 1] = input_signal[i, 1] * self.dry_level + damped_right * self.wet_level

            # Update buffer position
            self.buffer_pos = (self.buffer_pos + 1) % self.max_delay

        return output

    def reset(self) -> None:
        """Reset delay processor state."""
        self.delay_buffer_left.fill(0.0)
        self.delay_buffer_right.fill(0.0)
        self.buffer_pos = 0
        self.damp_state_left = 0.0
        self.damp_state_right = 0.0


class SFZVoiceEffectsProcessor:
    """
    Complete voice-level effects processor for SFZ instruments.

    Combines chorus, reverb, and delay effects with per-voice control
    and efficient processing suitable for polyphonic instruments.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize voice effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Initialize effect processors
        self.chorus = SFZChorusProcessor(sample_rate)
        self.reverb = SFZReverbProcessor(sample_rate)
        self.delay = SFZDelayProcessor(sample_rate)

        # Effect routing parameters
        self.chorus_send = 0.0
        self.reverb_send = 0.0
        self.delay_send = 0.0

        # Effect enable flags
        self.chorus_enabled = True
        self.reverb_enabled = True
        self.delay_enabled = True

    def set_effect_parameters(self, effect_name: str, params: dict[str, float]) -> bool:
        """
        Set parameters for a specific effect.

        Args:
            effect_name: Name of effect ('chorus', 'reverb', 'delay')
            params: Parameter dictionary

        Returns:
            True if effect was found and parameters set
        """
        if effect_name == 'chorus':
            self.chorus.set_parameters(params)
            return True
        elif effect_name == 'reverb':
            self.reverb.set_parameters(params)
            return True
        elif effect_name == 'delay':
            self.delay.set_parameters(params)
            return True

        return False

    def set_routing(self, chorus_send: float = 0.0, reverb_send: float = 0.0,
                   delay_send: float = 0.0) -> None:
        """
        Set effect routing levels.

        Args:
            chorus_send: Chorus send level (0.0-1.0)
            reverb_send: Reverb send level (0.0-1.0)
            delay_send: Delay send level (0.0-1.0)
        """
        self.chorus_send = max(0.0, min(1.0, chorus_send))
        self.reverb_send = max(0.0, min(1.0, reverb_send))
        self.delay_send = max(0.0, min(1.0, delay_send))

    def enable_effect(self, effect_name: str, enabled: bool = True) -> bool:
        """
        Enable or disable a specific effect.

        Args:
            effect_name: Name of effect ('chorus', 'reverb', 'delay')
            enabled: Whether to enable the effect

        Returns:
            True if effect was found and state changed
        """
        if effect_name == 'chorus':
            self.chorus_enabled = enabled
            return True
        elif effect_name == 'reverb':
            self.reverb_enabled = enabled
            return True
        elif effect_name == 'delay':
            self.delay_enabled = enabled
            return True

        return False

    def process_voice(self, audio: np.ndarray, block_size: int) -> np.ndarray:
        """
        Process audio through voice-level effects chain.

        Args:
            audio: Stereo input buffer (block_size, 2)
            block_size: Number of samples (for compatibility)

        Returns:
            Processed stereo output buffer
        """
        processed = audio.copy()

        # Apply chorus send
        if self.chorus_enabled and self.chorus_send > 0.0:
            chorus_wet = self.chorus.process(processed)
            dry_level = 1.0 - self.chorus_send
            wet_level = self.chorus_send
            processed = processed * dry_level + chorus_wet * wet_level

        # Apply reverb send
        if self.reverb_enabled and self.reverb_send > 0.0:
            reverb_wet = self.reverb.process(processed)
            dry_level = 1.0 - self.reverb_send
            wet_level = self.reverb_send
            processed = processed * dry_level + reverb_wet * wet_level

        # Apply delay send
        if self.delay_enabled and self.delay_send > 0.0:
            delay_wet = self.delay.process(processed)
            dry_level = 1.0 - self.delay_send
            wet_level = self.delay_send
            processed = processed * dry_level + delay_wet * wet_level

        return processed

    def get_effect_info(self) -> dict[str, Any]:
        """
        Get information about all effects.

        Returns:
            Dictionary with effect information
        """
        return {
            'chorus': {
                'enabled': self.chorus_enabled,
                'send': self.chorus_send,
                'depth': self.chorus.depth,
                'rate': self.chorus.rate,
                'delay': self.chorus.delay
            },
            'reverb': {
                'enabled': self.reverb_enabled,
                'send': self.reverb_send,
                'room_size': self.reverb.room_size,
                'damping': self.reverb.damping,
                'wet_level': self.reverb.wet_level
            },
            'delay': {
                'enabled': self.delay_enabled,
                'send': self.delay_send,
                'delay_time': self.delay.delay_time,
                'feedback': self.delay.feedback,
                'ping_pong': self.delay.ping_pong
            }
        }

    def reset_all_effects(self) -> None:
        """Reset all effect processors to clean state."""
        self.chorus.reset()
        self.reverb.reset()
        self.delay.reset()

    def get_memory_usage(self) -> dict[str, int]:
        """
        Get memory usage of all effects.

        Returns:
            Dictionary with memory usage in bytes
        """
        chorus_mem = len(self.chorus.delay_buffer_left) + len(self.chorus.delay_buffer_right)
        reverb_mem = (sum(len(f['buffer']) for f in self.reverb.comb_filters_left) +
                     sum(len(f['buffer']) for f in self.reverb.comb_filters_right) +
                     sum(len(f['buffer']) for f in self.reverb.allpass_filters_left) +
                     sum(len(f['buffer']) for f in self.reverb.allpass_filters_right) +
                     len(self.reverb.pre_delay_buffer))
        delay_mem = len(self.delay.delay_buffer_left) + len(self.delay.delay_buffer_right)

        return {
            'chorus': chorus_mem * 8,  # float64
            'reverb': reverb_mem * 8,  # float64
            'delay': delay_mem * 8,    # float64
            'total': (chorus_mem + reverb_mem + delay_mem) * 8
        }

    def __str__(self) -> str:
        """String representation."""
        info = self.get_effect_info()
        enabled_effects = [name for name, effect in info.items() if effect['enabled']]
        return f"SFZVoiceEffectsProcessor(effects={enabled_effects})"

    def __repr__(self) -> str:
        return self.__str__()