"""
XG Synthesizer Audio Engine

Handles audio block generation and processing for the XG synthesizer.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from ..core.constants import DEFAULT_CONFIG


class AudioEngine:
    """
    Handles audio block generation and processing for the XG synthesizer.

    Provides functionality for:
    - Audio block generation from channel renderers
    - Multi-channel audio mixing and processing
    - Effect processing integration
    - Master volume and limiting
    - Real-time audio output handling
    """

    def __init__(self, sample_rate: int = DEFAULT_CONFIG["SAMPLE_RATE"],
                 block_size: int = DEFAULT_CONFIG["BLOCK_SIZE"],
                 num_channels: int = DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]):
        """
        Initialize audio engine.

        Args:
            sample_rate: Sample rate in Hz
            block_size: Audio block size in samples
            num_channels: Number of MIDI channels
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_channels = num_channels
        self.master_volume = DEFAULT_CONFIG["MASTER_VOLUME"]

        # Audio buffers
        self.left_buffer = np.zeros(block_size, dtype=np.float32)
        self.right_buffer = np.zeros(block_size, dtype=np.float32)

        # Channel audio buffers - one per MIDI channel
        self.channel_buffers: List[List[Tuple[float, float]]] = [
            [(0.0, 0.0) for _ in range(block_size)] for _ in range(num_channels)
        ]

        # Effect processing state
        self.effect_enabled = True
        self.effect_channels = []  # Will be set by effect manager

    def set_master_volume(self, volume: float):
        """
        Set master volume.

        Args:
            volume: Volume level (0.0 - 1.0)
        """
        self.master_volume = max(0.0, min(1.0, volume))

    def generate_audio_block(self, channel_renderers: List, effect_manager,
                           block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block from all active channel renderers.

        Args:
            channel_renderers: List of channel renderer objects
            effect_manager: Effect manager for processing
            block_size: Block size in samples (optional)

        Returns:
            Tuple of (left_channel, right_channel) audio buffers
        """
        if block_size is None:
            block_size = self.block_size

        # Ensure buffers are correct size
        if len(self.left_buffer) != block_size:
            self.left_buffer = np.zeros(block_size, dtype=np.float32)
            self.right_buffer = np.zeros(block_size, dtype=np.float32)

        # Generate audio for each channel renderer
        self._generate_channel_audio(channel_renderers, block_size)

        # Apply effects if enabled
        if self.effect_enabled and effect_manager:
            return self._apply_effects(effect_manager, block_size)
        else:
            return self._mix_channels_without_effects(block_size)

    def _generate_channel_audio(self, channel_renderers: List, block_size: int):
        """
        Generate audio for each channel renderer.

        Args:
            channel_renderers: List of channel renderer objects
            block_size: Block size in samples
        """
        for channel_idx, renderer in enumerate(channel_renderers):
            if channel_idx >= self.num_channels:
                break

            if renderer.is_active():
                try:
                    # Generate block audio for this renderer
                    for sample_idx in range(block_size):
                        left_sample, right_sample = renderer.generate_sample()

                        # Add to existing audio on this channel
                        existing_left, existing_right = self.channel_buffers[channel_idx][sample_idx]
                        self.channel_buffers[channel_idx][sample_idx] = (
                            existing_left + left_sample,
                            existing_right + right_sample
                        )
                except Exception as e:
                    print(f"Error generating sample for channel {channel_idx}: {e}")
                    # Disable problematic renderer
                    renderer.active = False

    def _apply_effects(self, effect_manager, block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply effects to audio and return processed buffers.

        Args:
            effect_manager: Effect manager for processing
            block_size: Block size in samples

        Returns:
            Tuple of (left_channel, right_channel) processed audio buffers
        """
        try:
            # Prepare multichannel input data for effects
            input_channels = []
            for channel_idx in range(self.num_channels):
                channel_samples = []
                for sample_idx in range(block_size):
                    channel_samples.append(self.channel_buffers[channel_idx][sample_idx])
                input_channels.append(channel_samples)

            # Process effects for all channels
            effected_channels = effect_manager.process_audio(input_channels, block_size)

            # Mix all channels into single stereo output
            self.left_buffer.fill(0.0)
            self.right_buffer.fill(0.0)

            for channel_idx in range(self.num_channels):
                for sample_idx in range(block_size):
                    self.left_buffer[sample_idx] += effected_channels[channel_idx][sample_idx][0]
                    self.right_buffer[sample_idx] += effected_channels[channel_idx][sample_idx][1]

            # Apply master volume and limiting
            self._apply_master_volume_and_limiting(block_size)

            return self.left_buffer.copy(), self.right_buffer.copy()

        except Exception as e:
            print(f"Error processing effects: {e}")
            # If effects don't work, return unprocessed mix
            return self._mix_channels_without_effects(block_size)

    def _mix_channels_without_effects(self, block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Mix channels without effects processing.

        Args:
            block_size: Block size in samples

        Returns:
            Tuple of (left_channel, right_channel) mixed audio buffers
        """
        # Mix all channels into single stereo output
        self.left_buffer.fill(0.0)
        self.right_buffer.fill(0.0)

        for channel_idx in range(self.num_channels):
            for sample_idx in range(block_size):
                left_sample, right_sample = self.channel_buffers[channel_idx][sample_idx]
                self.left_buffer[sample_idx] += left_sample
                self.right_buffer[sample_idx] += right_sample

        # Apply master volume and limiting
        self._apply_master_volume_and_limiting(block_size)

        return self.left_buffer.copy(), self.right_buffer.copy()

    def _apply_master_volume_and_limiting(self, block_size: int):
        """
        Apply master volume and limiting to audio buffers.

        Args:
            block_size: Block size in samples
        """
        for sample_idx in range(block_size):
            # Apply master volume
            self.left_buffer[sample_idx] *= self.master_volume
            self.right_buffer[sample_idx] *= self.master_volume

            # Apply limiting
            self.left_buffer[sample_idx] = max(-1.0, min(1.0, self.left_buffer[sample_idx]))
            self.right_buffer[sample_idx] = max(-1.0, min(1.0, self.right_buffer[sample_idx]))

    def generate_audio_block_at_time(self, channel_renderers: List, effect_manager,
                                   block_size: Optional[int] = None,
                                   current_time: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block at specified time (for buffered mode).

        Args:
            channel_renderers: List of channel renderer objects
            effect_manager: Effect manager for processing
            block_size: Block size in samples (optional)
            current_time: Current time in seconds

        Returns:
            Tuple of (left_channel, right_channel) audio buffers
        """
        # For now, delegate to regular generation
        # In a full implementation, this would handle time-based processing
        return self.generate_audio_block(channel_renderers, effect_manager, block_size)

    def generate_audio_block_sample_accurate(self, channel_renderers: List, effect_manager,
                                           buffered_processor, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate audio block with sample-accurate MIDI message processing.

        Args:
            channel_renderers: List of channel renderer objects
            effect_manager: Effect manager for processing
            buffered_processor: Buffered processor for message timing
            block_size: Block size in samples (optional)

        Returns:
            Tuple of (left_channel, right_channel) audio buffers
        """
        if block_size is None:
            block_size = self.block_size

        # Ensure buffers are correct size
        if len(self.left_buffer) != block_size:
            self.left_buffer = np.zeros(block_size, dtype=np.float32)
            self.right_buffer = np.zeros(block_size, dtype=np.float32)

        # Set block start time for sample-accurate processing
        buffered_processor.set_block_start_time(buffered_processor.current_time)
        buffered_processor.prepare_sample_times(block_size)

        # Process each sample separately with MIDI message checking
        for sample_idx in range(block_size):
            # Process any MIDI messages that should occur at this sample
            midi_messages, sysex_messages = buffered_processor.process_sample_accurate_messages(sample_idx)

            # Process MIDI messages (would delegate to message handler)
            for status, data1, data2 in midi_messages:
                # Message processing would be handled here
                pass

            # Process SYSEX messages (would delegate to message handler)
            for sysex_data in sysex_messages:
                # SYSEX processing would be handled here
                pass

            # Generate audio for this sample
            left_sample, right_sample = self._generate_single_sample(channel_renderers)

            # Store in buffers
            self.left_buffer[sample_idx] = left_sample
            self.right_buffer[sample_idx] = right_sample

        # Apply effects to entire block
        if self.effect_enabled and effect_manager:
            return self._apply_effects_to_block(effect_manager, block_size)
        else:
            # Apply master volume and limiting
            self._apply_master_volume_and_limiting(block_size)
            return self.left_buffer.copy(), self.right_buffer.copy()

    def _generate_single_sample(self, channel_renderers: List) -> Tuple[float, float]:
        """
        Generate one audio sample from all active channel renderers.

        Args:
            channel_renderers: List of channel renderer objects

        Returns:
            Tuple of (left_sample, right_sample)
        """
        left_sum = 0.0
        right_sum = 0.0

        for renderer in channel_renderers:
            if renderer.is_active():
                try:
                    left_sample, right_sample = renderer.generate_sample()
                    left_sum += left_sample
                    right_sum += right_sample
                except Exception as e:
                    print(f"Error generating sample: {e}")
                    # Disable problematic renderer
                    renderer.active = False

        return left_sum, right_sum

    def _apply_effects_to_block(self, effect_manager, block_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply effects to entire audio block.

        Args:
            effect_manager: Effect manager for processing
            block_size: Block size in samples

        Returns:
            Tuple of (left_channel, right_channel) processed audio buffers
        """
        try:
            # Create multichannel input data for effects
            input_channels = []

            # For simplicity, use only stereo mix for effects
            # In a full implementation, this would handle per-channel effects
            stereo_samples = []
            for sample_idx in range(block_size):
                stereo_samples.append((self.left_buffer[sample_idx], self.right_buffer[sample_idx]))
            input_channels.append(stereo_samples)

            # Process effects
            effected_channels = effect_manager.process_audio(input_channels, block_size)

            # Extract processed stereo
            processed_left = np.zeros(block_size, dtype=np.float32)
            processed_right = np.zeros(block_size, dtype=np.float32)

            for sample_idx in range(block_size):
                processed_left[sample_idx] = effected_channels[0][sample_idx][0]
                processed_right[sample_idx] = effected_channels[0][sample_idx][1]

            # Apply master volume and limiting
            for sample_idx in range(block_size):
                processed_left[sample_idx] *= self.master_volume
                processed_right[sample_idx] *= self.master_volume
                processed_left[sample_idx] = max(-1.0, min(1.0, processed_left[sample_idx]))
                processed_right[sample_idx] = max(-1.0, min(1.0, processed_right[sample_idx]))

            return processed_left, processed_right

        except Exception as e:
            print(f"Error processing effects: {e}")
            # Return unprocessed audio with master volume and limiting
            self._apply_master_volume_and_limiting(block_size)
            return self.left_buffer.copy(), self.right_buffer.copy()

    def clear_channel_buffers(self):
        """
        Clear all channel audio buffers.
        """
        for channel_idx in range(self.num_channels):
            for sample_idx in range(self.block_size):
                self.channel_buffers[channel_idx][sample_idx] = (0.0, 0.0)

    def reset(self):
        """
        Reset audio engine to initial state.
        """
        self.left_buffer.fill(0.0)
        self.right_buffer.fill(0.0)
        self.clear_channel_buffers()
        self.master_volume = DEFAULT_CONFIG["MASTER_VOLUME"]

    def get_audio_info(self) -> Dict[str, Any]:
        """
        Get information about current audio state.

        Returns:
            Dictionary with audio information
        """
        return {
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
            "num_channels": self.num_channels,
            "master_volume": self.master_volume,
            "effect_enabled": self.effect_enabled,
            "buffer_size": len(self.left_buffer)
        }

    def set_effect_enabled(self, enabled: bool):
        """
        Enable or disable effect processing.

        Args:
            enabled: Whether effects should be enabled
        """
        self.effect_enabled = enabled
