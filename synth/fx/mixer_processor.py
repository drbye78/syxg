"""
XG Mixer Processor - Channel Mixing and Routing

This module implements XG-compliant channel mixing with panning, volume control,
and effect send management. Provides the final mix-down from multi-channel
input to stereo output with proper XG mixing rules.

Key Features:
- XG channel parameters (volume, pan, effect sends)
- Multi-channel mixing with panning law
- Effect send routing (reverb, chorus, variation)
- Solo/mute functionality
- Zero-allocation processing for realtime performance
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import threading

# Import our types and utilities
try:
    from .types import XGChannelMixerParams, XG_CHANNEL_MIXER_DEFAULT
except ImportError:
    # Fallback for development
    from synth.effects.processing import *


class XGChannelMixer:
    """
    XG Channel Mixer

    Implements XG channel mixing with panning and effect send routing.
    Handles one channel's mixing parameters and processing.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize XG channel mixer.

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate

        # XG channel parameters
        self.params = XG_CHANNEL_MIXER_DEFAULT._replace()

        # Thread safety
        self.lock = threading.RLock()

    def set_channel_params(self, volume: float = None, pan: float = None,
                          reverb_send: float = None, chorus_send: float = None,
                          variation_send: float = None, mute: bool = None,
                          solo: bool = None) -> bool:
        """
        Set channel mixing parameters.

        Args:
            volume: Channel volume (0.0-1.0)
            pan: Channel pan (-1.0 left to +1.0 right)
            reverb_send: Reverb send level (0.0-1.0)
            chorus_send: Chorus send level (0.0-1.0)
            variation_send: Variation send level (0.0-1.0)
            mute: Channel mute flag
            solo: Channel solo flag

        Returns:
            True if any parameter was changed
        """
        with self.lock:
            changed = False

            if volume is not None:
                volume = max(0.0, min(1.0, volume))
                if abs(volume - self.params.volume) > 0.001:
                    self.params = self.params._replace(volume=volume)
                    changed = True

            if pan is not None:
                pan = max(-1.0, min(1.0, pan))
                if abs(pan - self.params.pan) > 0.001:
                    self.params = self.params._replace(pan=pan)
                    changed = True

            if reverb_send is not None:
                reverb_send = max(0.0, min(1.0, reverb_send))
                if abs(reverb_send - self.params.reverb_send) > 0.001:
                    self.params = self.params._replace(reverb_send=reverb_send)
                    changed = True

            if chorus_send is not None:
                chorus_send = max(0.0, min(1.0, chorus_send))
                if abs(chorus_send - self.params.chorus_send) > 0.001:
                    self.params = self.params._replace(chorus_send=chorus_send)
                    changed = True

            if variation_send is not None:
                variation_send = max(0.0, min(1.0, variation_send))
                if abs(variation_send - self.params.variation_send) > 0.001:
                    self.params = self.params._replace(variation_send=variation_send)
                    changed = True

            if mute is not None:
                if mute != self.params.mute:
                    self.params = self.params._replace(mute=mute)
                    changed = True

            if solo is not None:
                if solo != self.params.solo:
                    self.params = self.params._replace(solo=solo)
                    changed = True

            return changed

    def apply_channel_mixing_to_buffers(self, input_audio: np.ndarray,
                                       main_mix_left: np.ndarray,
                                       main_mix_right: np.ndarray,
                                       num_samples: int,
                                       reverb_send_buffers: Optional[List[np.ndarray]] = None,
                                       chorus_send_buffers: Optional[List[np.ndarray]] = None,
                                       variation_send_buffers: Optional[List[np.ndarray]] = None) -> None:
        """
        Apply channel mixing with panning and effect sends to separate buffers.

        Args:
            input_audio: Input audio (samples,) for mono or (samples, 2) for stereo
            main_mix_left: Main mix left buffer to accumulate into
            main_mix_right: Main mix right buffer to accumulate into
            num_samples: Number of samples to process
            reverb_send_buffers: List of reverb send buffers (one per channel)
            chorus_send_buffers: List of chorus send buffers (one per channel)
            variation_send_buffers: List of variation send buffers (one per channel)
        """
        with self.lock:
            # Skip processing if muted
            if self.params.mute:
                return

            volume = self.params.volume
            pan = self.params.pan

            # Calculate pan law (equal power panning)
            # XG uses equal power panning for smooth stereo imaging
            pan_rad = (pan + 1.0) * 0.5 * np.pi * 0.5  # Convert to 0-90 degrees
            left_gain = np.cos(pan_rad)
            right_gain = np.sin(pan_rad)

            # Apply volume and panning
            if input_audio.ndim == 1:
                # Mono input
                left_signal = input_audio[:num_samples] * volume * left_gain
                right_signal = input_audio[:num_samples] * volume * right_gain
            else:
                # Stereo input - apply panning independently to both channels
                # This allows for stereo input while still applying channel pan
                left_in = input_audio[:num_samples, 0]
                right_in = input_audio[:num_samples, 1]

                left_signal = (left_in * left_gain + right_in * (1.0 - right_gain)) * volume
                right_signal = (right_in * right_gain + left_in * (1.0 - left_gain)) * volume

            # Accumulate into main mix
            main_mix_left[:num_samples] += left_signal
            main_mix_right[:num_samples] += right_signal

            # Handle effect sends if buffers provided
            if reverb_send_buffers is not None and len(reverb_send_buffers) > 0:
                reverb_level = self.params.reverb_send
                if reverb_level > 0.001:
                    for buf_idx, send_buf in enumerate(reverb_send_buffers):
                        # Distribute to multiple send buffers if available
                        send_level = reverb_level / len(reverb_send_buffers)
                        send_buf[:num_samples, 0] += left_signal * send_level
                        send_buf[:num_samples, 1] += right_signal * send_level

            if chorus_send_buffers is not None and len(chorus_send_buffers) > 0:
                chorus_level = self.params.chorus_send
                if chorus_level > 0.001:
                    for buf_idx, send_buf in enumerate(chorus_send_buffers):
                        send_level = chorus_level / len(chorus_send_buffers)
                        send_buf[:num_samples, 0] += left_signal * send_level
                        send_buf[:num_samples, 1] += right_signal * send_level

            if variation_send_buffers is not None and len(variation_send_buffers) > 0:
                variation_level = self.params.variation_send
                if variation_level > 0.001:
                    for buf_idx, send_buf in enumerate(variation_send_buffers):
                        send_level = variation_level / len(variation_send_buffers)
                        send_buf[:num_samples, 0] += left_signal * send_level
                        send_buf[:num_samples, 1] += right_signal * send_level


class XGMasterMixer:
    """
    XG Master Mixer

    Implements the final mastering stage of the XG mixer with advanced stereo
    enhancement, limiting, and final level control.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize XG master mixer.

        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Master parameters
        self.master_volume = 1.0
        self.stereo_width = 1.0  # 0=mono, 1=normal stereo, >1=enhanced stereo
        self.limiter_enabled = True
        self.limiter_threshold = -0.1  # dBFS threshold
        self.limiter_release = 0.1     # Release time in seconds

        # Internal state
        self.release_samples = int(self.limiter_release * sample_rate)
        self.envelope_state = 1.0

        # Thread safety
        self.lock = threading.RLock()

    def set_master_params(self, volume: float = None, stereo_width: float = None,
                         limiter_enabled: bool = None) -> bool:
        """
        Set master mixing parameters.

        Args:
            volume: Master volume (0.0-2.0)
            stereo_width: Stereo width enhancement (0.0-2.0)
            limiter_enabled: Enable master limiter

        Returns:
            True if any parameter was changed
        """
        with self.lock:
            changed = False

            if volume is not None:
                volume = max(0.0, min(2.0, volume))
                if abs(volume - self.master_volume) > 0.001:
                    self.master_volume = volume
                    changed = True

            if stereo_width is not None:
                stereo_width = max(0.0, min(2.0, stereo_width))
                if abs(stereo_width - self.stereo_width) > 0.001:
                    self.stereo_width = stereo_width
                    changed = True

            if limiter_enabled is not None:
                if limiter_enabled != self.limiter_enabled:
                    self.limiter_enabled = limiter_enabled
                    changed = True

            return changed

    def apply_master_processing_zero_alloc(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """
        Apply master processing to stereo mix (in-place).

        Args:
            stereo_mix: Input/output stereo mix buffer (num_samples, 2)
            num_samples: Number of samples to process
        """
        with self.lock:
            # Apply stereo width enhancement
            if self.stereo_width != 1.0:
                self._apply_stereo_width(stereo_mix, num_samples)

            # Apply master volume
            if self.master_volume != 1.0:
                stereo_mix[:num_samples] *= self.master_volume

            # Apply master limiting
            if self.limiter_enabled:
                self._apply_master_limiter(stereo_mix, num_samples)

    def _apply_stereo_width(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply stereo width enhancement/correction."""
        for i in range(num_samples):
            left = stereo_mix[i, 0]
            right = stereo_mix[i, 1]

            # Calculate mid/side components
            mid = (left + right) * 0.5
            side = (left - right) * 0.5

            # Apply width enhancement
            if self.stereo_width > 1.0:
                # Enhance stereo width
                side *= self.stereo_width
            elif self.stereo_width < 1.0:
                # Narrow stereo image
                side *= self.stereo_width

            # Reconstruct stereo
            stereo_mix[i, 0] = mid + side
            stereo_mix[i, 1] = mid - side

    def _apply_master_limiter(self, stereo_mix: np.ndarray, num_samples: int) -> None:
        """Apply simple master limiting to prevent clipping."""
        threshold_linear = 10.0 ** (self.limiter_threshold / 20.0)

        for i in range(num_samples):
            # Calculate peak level
            peak = max(abs(stereo_mix[i, 0]), abs(stereo_mix[i, 1]))

            if peak > threshold_linear:
                # Calculate limiting ratio
                ratio = threshold_linear / peak

                # Apply envelope smoothing to avoid artifacts
                if ratio < self.envelope_state:
                    # Attack (immediate limiting)
                    self.envelope_state = ratio
                else:
                    # Release (gradual increase)
                    release_rate = 1.0 / self.release_samples
                    self.envelope_state = min(1.0, self.envelope_state + release_rate)

                # Apply limiting
                stereo_mix[i, 0] *= self.envelope_state
                stereo_mix[i, 1] *= self.envelope_state
            else:
                # Release envelope
                release_rate = 1.0 / self.release_samples
                self.envelope_state = min(1.0, self.envelope_state + release_rate)


class XGChannelMixerProcessor:
    """
    XG Channel Mixer Processor

    Manages multi-channel mixing with XG-compliant parameters and processing.
    Handles the complete mixing pipeline from individual channels to final stereo output.
    """

    def __init__(self, sample_rate: int, max_channels: int = 16):
        """
        Initialize XG channel mixer processor.

        Args:
            sample_rate: Sample rate in Hz
            max_channels: Maximum number of channels to support
        """
        self.sample_rate = sample_rate
        self.max_channels = max_channels

        # Channel mixers (one per channel)
        self.channel_mixers = []
        for _ in range(max_channels):
            self.channel_mixers.append(XGChannelMixer(sample_rate))

        # Master mixer for final processing
        self.master_mixer = XGMasterMixer(sample_rate)

        # Solo state tracking
        self.solo_channels = set()  # Set of channels with solo enabled

        # Thread safety
        self.lock = threading.RLock()

    def set_channel_params(self, channel: int, **params) -> bool:
        """
        Set parameters for a specific channel.

        Args:
            channel: Channel number (0-15)
            **params: Channel parameters (volume, pan, sends, etc.)

        Returns:
            True if parameters were set successfully
        """
        with self.lock:
            if 0 <= channel < len(self.channel_mixers):
                success = self.channel_mixers[channel].set_channel_params(**params)
                self._update_solo_state(channel)
                return success
            return False

    def mix_channels_to_stereo_zero_alloc(self, channel_inputs: List[np.ndarray],
                                         stereo_output: np.ndarray, num_samples: int,
                                         effect_send_outputs: Optional[Dict[str, List[np.ndarray]]] = None) -> None:
        """
        Mix multiple channel inputs to stereo output with XG-compliant processing.

        Args:
            channel_inputs: List of channel audio arrays (mono or stereo)
            stereo_output: Output stereo buffer (num_samples, 2) - modified in-place
            num_samples: Number of samples to process
            effect_send_outputs: Optional dict of effect send buffers by type
                               ('reverb', 'chorus', 'variation' -> List[buffer])
        """
        with self.lock:
            # Clear output buffers
            stereo_output[:num_samples, :] = 0.0

            # Prepare effect send buffers
            reverb_sends = []
            chorus_sends = []
            variation_sends = []

            if effect_send_outputs:
                reverb_sends = effect_send_outputs.get('reverb', [])
                chorus_sends = effect_send_outputs.get('chorus', [])
                variation_sends = effect_send_outputs.get('variation', [])

                # Clear send buffers
                for buf in reverb_sends + chorus_sends + variation_sends:
                    buf[:num_samples, :] = 0.0

            # Determine which channels to mix (solo logic)
            active_channels = self._get_active_channels(len(channel_inputs))

            # Mix channels with panning and sends
            for ch_idx in active_channels:
                if ch_idx >= len(channel_inputs):
                    continue

                input_audio = channel_inputs[ch_idx]
                if input_audio is None or len(input_audio) == 0:
                    continue

                # Get references to main mix output
                main_left = stereo_output[:num_samples, 0]
                main_right = stereo_output[:num_samples, 1]

                # Mix channel into main output and effect sends
                self.channel_mixers[ch_idx].apply_channel_mixing_to_buffers(
                    input_audio, main_left, main_right, num_samples,
                    reverb_sends, chorus_sends, variation_sends
                )

            # Apply master processing
            self.master_mixer.apply_master_processing_zero_alloc(stereo_output, num_samples)

    def set_master_params(self, **params) -> bool:
        """Set master mixing parameters."""
        with self.lock:
            return self.master_mixer.set_master_params(**params)

    def get_channel_params(self, channel: int) -> Optional[XGChannelMixerParams]:
        """Get current parameters for a channel."""
        with self.lock:
            if 0 <= channel < len(self.channel_mixers):
                return self.channel_mixers[channel].params
            return None

    def get_master_status(self) -> Dict[str, Any]:
        """Get master mixer status."""
        with self.lock:
            return {
                'master_volume': self.master_mixer.master_volume,
                'stereo_width': self.master_mixer.stereo_width,
                'limiter_enabled': self.master_mixer.limiter_enabled,
                'solo_channels': list(self.solo_channels),
            }

    def reset_all_channels(self) -> None:
        """Reset all channel parameters to default."""
        with self.lock:
            for mixer in self.channel_mixers:
                mixer.params = XG_CHANNEL_MIXER_DEFAULT._replace()
            self.solo_channels.clear()

    def _get_active_channels(self, num_inputs: int) -> List[int]:
        """
        Determine which channels should be mixed based on solo/mute state.

        Returns list of channel indices to process.
        """
        if len(self.solo_channels) == 0:
            # No solos enabled - mix all active channels that aren't muted
            return [i for i in range(min(num_inputs, self.max_channels))
                   if not self.channel_mixers[i].params.mute]
        else:
            # Solos enabled - only mix solo channels that aren't muted
            return [i for i in self.solo_channels
                   if i < num_inputs and not self.channel_mixers[i].params.mute]

    def _update_solo_state(self, channel: int) -> None:
        """Update internal solo state tracking."""
        if self.channel_mixers[channel].params.solo:
            self.solo_channels.add(channel)
        else:
            self.solo_channels.discard(channel)
