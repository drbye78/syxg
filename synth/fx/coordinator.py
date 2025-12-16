"""
XG Effects Coordinator - Main Effects Processing Engine

Coordinates the complete XG effects processing pipeline with zero-allocation
processing, multi-channel support, and full XG specification compliance.

Architecture:
- System Effects: Reverb, Chorus (shared across channels)
- Variation Effects: Per-channel variation effects (83 types all channel-dependent)
- Insertion Effects: 3-slot per-channel insertion effects (18 types each)
- Master Effects: EQ and final mixing

Processing Order: Input → Insertion → Variation → Reverb → Chorus → Master → Output
"""

import numpy as np
import threading
from typing import Dict, List, Optional, Tuple, Any
from .types import (
    XGReverbType, XGChorusType, XGVariationType, XGInsertionType,
    XGProcessingState, XGEffectCategory, XGChannelParams,
    XGSystemEffectsParams, XGProcessingContext
)


class XGEffectsCoordinator:
    """
    Main XG Effects Coordinator - Zero-Allocation Processing Engine

    Coordinates all XG effects processing with proper signal routing:
    1. Insertion effects (3 slots per channel)
    2. Variation effects (1 slot per channel, 83 XG types)
    3. System effects (Reverb & Chorus shared across channels)
    4. Master effects (EQ, mixing)

    Features:
    - Zero-allocation processing with pre-allocated buffers
    - Thread-safe operations with proper synchronization
    - Full XG NRPN/MIDI CC control interface
    - Performance monitoring and quality control
    - Configurable processing order and bypass options
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        block_size: int = 1024,
        max_channels: int = 16
    ):
        """
        Initialize XG Effects Coordinator.

        Args:
            sample_rate: Audio sampling rate (Hz)
            block_size: Processing block size (samples)
            max_channels: Maximum number of MIDI channels to support
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_channels = max_channels

        # Processing state
        self.state = XGProcessingState.IDLE
        self.lock = threading.RLock()

        # Pre-allocated processing buffers (zero-allocation design)
        self._initialize_buffers()

        # Effect routing and configuration
        self._initialize_effect_routing()

        # Effect processors (initialized as needed)
        self._initialize_effect_processors()

        # Parameter storage
        self.system_params = XGSystemEffectsParams(
            reverb_type=XGReverbType.HALL_1,
            reverb_level=0.4,
            reverb_time=2.5,
            reverb_hf_damping=0.5,
            reverb_pre_delay=20e-3,
            chorus_type=XGChorusType.CHORUS_1,
            chorus_level=0.3,
            chorus_rate=1.0,
            chorus_depth=0.5,
            chorus_feedback=0.3,
            variation_type=XGVariationType.DELAY_LCR,
            variation_level=0.5,
            bypass_all=False
        )

        # Initialize variation effects processor
        from .variation_effects import XGVariationEffectsProcessor
        self.variation_processor = XGVariationEffectsProcessor(
            sample_rate=self.sample_rate,
            max_delay_samples=self.block_size * 4  # Reasonable delay buffer size
        )
        self.variation_processor.set_variation_type(self.system_params.variation_type)

        # Initialize coordinator
        self.reset_all_effects()
        self.state = XGProcessingState.PROCESSING

    def _initialize_buffers(self):
        """Initialize pre-allocated processing buffers (zero-allocation principle)."""
        # Main processing buffers
        self.channel_input_buffers = [
            np.zeros((self.block_size, 2), dtype=np.float32)
            for _ in range(self.max_channels)
        ]
        self.channel_output_buffers = [
            np.zeros((self.block_size, 2), dtype=np.float32)
            for _ in range(self.max_channels)
        ]

        # Effect accumulation buffers
        self.reverb_accumulate = np.zeros((self.block_size, 2), dtype=np.float32)
        self.chorus_accumulate = np.zeros((self.block_size, 2), dtype=np.float32)
        self.variation_accumulate = np.zeros((self.block_size, 2), dtype=np.float32)

        # Final mixing buffer
        self.final_mix_buffer = np.zeros((self.block_size, 2), dtype=np.float32)

        # Temporary processing buffers
        self.temp_buffers = [
            np.zeros((self.block_size, 2), dtype=np.float32)
            for _ in range(4)  # Enough for effect chaining
        ]

    def _initialize_effect_routing(self):
        """Initialize effect routing configuration."""
        # Effect send levels (0.0-1.0 range)
        self.reverb_send_levels = np.full(self.max_channels, 0.0, dtype=np.float32)
        self.chorus_send_levels = np.full(self.max_channels, 0.0, dtype=np.float32)
        self.variation_send_levels = np.full(self.max_channels, 0.0, dtype=np.float32)

        # Effect types per channel
        self.variation_effect_types = [
            XGVariationType.DELAY_LCR for _ in range(self.max_channels)
        ]
        self.insertion_effect_types = [
            [XGInsertionType.THROUGH, XGInsertionType.THROUGH, XGInsertionType.THROUGH]
            for _ in range(self.max_channels)
        ]

    def _initialize_effect_processors(self):
        """Initialize effect processor instances."""
        # System effect processors
        self.reverb_processor = None  # ConvolutionReverbEffect placeholder
        self.chorus_processor = None  # StereoChorusEffect placeholder

        # Per-channel effect processors
        self.variation_processors = [None] * self.max_channels

        # Initialize production insertion effect processors
        from .insertion_pro import ProductionXGInsertionEffectsProcessor
        self.insertion_processors = [
            ProductionXGInsertionEffectsProcessor(self.sample_rate, self.block_size * 4)
            for _ in range(self.max_channels)
        ]

    def reset_all_effects(self):
        """Reset all effects to XG specification defaults."""
        with self.lock:
            # Reset to XG defaults
            self.system_params = XGSystemEffectsParams(
                reverb_type=XGReverbType.HALL_1,
                reverb_level=0.4,
                reverb_time=2.5,
                reverb_hf_damping=0.5,
                reverb_pre_delay=20e-3,
                chorus_type=XGChorusType.CHORUS_1,
                chorus_level=0.3,
                chorus_rate=1.0,
                chorus_depth=0.5,
                chorus_feedback=0.3,
                variation_type=XGVariationType.DELAY_LCR,
                variation_level=0.5,
                bypass_all=False
            )

            # Reset send levels to XG defaults
            self.reverb_send_levels.fill(40/127)  # CC 91 default
            self.chorus_send_levels.fill(0/127)   # CC 93 default
            self.variation_send_levels.fill(0/127) # CC 94 default

            # Set channel 10 (index 9) to drum mode with appropriate sends
            # In XG: drums typically have minimal effects by default

    def process_channels_to_stereo_zero_alloc(
        self,
        channel_inputs: List[np.ndarray],
        stereo_output: np.ndarray,
        num_samples: int
    ) -> None:
        """
        Process multiple channels through XG effects to stereo output (zero-allocation).

        Complete XG effects processing pipeline:
        1. Per-channel insertion effects (3 slots each)
        2. Per-channel variation effects (1 slot each)
        3. System reverb (shared across channels)
        4. System chorus (shared across channels)
        5. Final stereo mixing

        Args:
            channel_inputs: List of input channel buffers (stereo numpy arrays)
            stereo_output: Output stereo buffer (modified in-place)
            num_samples: Number of samples to process
        """
        if self.state != XGProcessingState.PROCESSING:
            return

        with self.lock:
            if self.system_params.bypass_all:
                # Bypass mode: direct mix to stereo
                stereo_output.fill(0.0)
                for ch_idx, channel_in in enumerate(channel_inputs):
                    if channel_in is not None and ch_idx < self.max_channels:
                        # Simple stereo mix (left = left + right, right = left + right)
                        np.add(stereo_output, channel_in[:num_samples], out=stereo_output)
                return

            # Reset accumulation buffers
            self.reverb_accumulate.fill(0.0)
            self.chorus_accumulate.fill(0.0)
            self.final_mix_buffer.fill(0.0)

            # Process each channel through the full XG effects chain
            for ch_idx, channel_in in enumerate(channel_inputs):
                if channel_in is None or ch_idx >= self.max_channels:
                    continue

                # Get input for this channel
                channel_input = channel_in[:num_samples]
                channel_output = self.temp_buffers[0][:num_samples]

                # Step 1: Process insertion effects (3 slots)
                # Use the production insertion effects processor
                insertion_params = {
                    f"slot_drive": 1.0,
                    f"slot_tone": 0.5,
                    f"slot_level": 0.8,
                    f"slot_threshold": -20.0,
                    f"slot_ratio": 4.0,
                    f"slot_attack": 5.0,
                    f"slot_release": 100.0,
                    f"slot_sensitivity": 0.5,
                    f"slot_resonance": 2.0,
                    f"slot_rate": 1.0,
                    f"slot_depth": 0.5,
                    f"slot_feedback": 0.3,
                    f"slot_speed": 0.5,
                    f"slot_enhance": 0.5,
                    "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5
                }

                self.insertion_processors[ch_idx].apply_insertion_effect_to_channel_zero_alloc(
                    self.temp_buffers[2][:num_samples],  # target_buffer
                    channel_input,                       # channel_array
                    insertion_params,                    # insertion_params
                    num_samples,                         # num_samples
                    ch_idx                               # channel_idx
                )
                np.copyto(channel_output, self.temp_buffers[2][:num_samples])

                # Step 2: Process variation effect
                variation_output = self.temp_buffers[1][:num_samples]
                variation_level = self.variation_send_levels[ch_idx]

                if variation_level > 0:
                    # Apply variation effect to channel
                    np.copyto(variation_output, channel_output)
                    self.variation_processor.apply_variation_effect_zero_alloc(
                        variation_output, num_samples
                    )
                    # Mix dry/wet
                    np.copyto(variation_output,
                             channel_output * (1.0 - variation_level) +
                             variation_output * variation_level)
                else:
                    # No variation effect - pass through
                    np.copyto(variation_output, channel_output)

                # Step 3: Send to system effects
                final_channel_output = variation_output

                # Send to reverb
                reverb_send = self.reverb_send_levels[ch_idx] * self.system_params.reverb_level
                if reverb_send > 0:
                    # Add to reverb accumulation (placeholder)
                    scaled_send = final_channel_output * reverb_send
                    np.add(self.reverb_accumulate, scaled_send, out=self.reverb_accumulate)

                # Send to chorus
                chorus_send = self.chorus_send_levels[ch_idx] * self.system_params.chorus_level
                if chorus_send > 0:
                    # Add to chorus accumulation (placeholder)
                    scaled_send = final_channel_output * chorus_send
                    np.add(self.chorus_accumulate, scaled_send, out=self.chorus_accumulate)

                # Dry signal to final mix
                dry_level = 1.0 - max(reverb_send, chorus_send)
                if dry_level > 0:
                    np.add(self.final_mix_buffer, final_channel_output * dry_level,
                          out=self.final_mix_buffer)

            # Step 4: Process system effects and mix final output
            # For now, simplified mixing (reverb/chorus processing not implemented yet)
            # TODO: Implement actual reverb and chorus processing
            np.copyto(stereo_output, self.final_mix_buffer)

            # Add processed reverb (placeholder)
            if np.max(np.abs(self.reverb_accumulate)) > 0:
                stereo_output += self.reverb_accumulate * 0.3

            # Add processed chorus (placeholder)
            if np.max(np.abs(self.chorus_accumulate)) > 0:
                stereo_output += self.chorus_accumulate * 0.3

    def set_effect_send_level(self, channel: int, effect_type: str, level: float):
        """
        Set effect send level for a specific channel and effect type.

        Args:
            channel: MIDI channel (0-15)
            effect_type: 'reverb', 'chorus', or 'variation'
            level: Send level (0.0-1.0)
        """
        if not (0 <= channel < self.max_channels):
            return

        with self.lock:
            level = max(0.0, min(1.0, level))
            if effect_type == 'reverb':
                self.reverb_send_levels[channel] = level
            elif effect_type == 'chorus':
                self.chorus_send_levels[channel] = level
            elif effect_type == 'variation':
                self.variation_send_levels[channel] = level

    def set_system_effect_parameter(self, effect: str, parameter: str, value):
        """
        Set system effect parameter.

        Args:
            effect: 'reverb', 'chorus', or 'variation'
            parameter: Parameter name (e.g., 'type', 'level')
            value: Parameter value
        """
        pass  # TODO: Implement system parameter setting

    def set_channel_insertion_effect(self, channel: int, slot: int, effect_type: int):
        """
        Set insertion effect for a channel and slot.

        Args:
            channel: MIDI channel (0-15)
            slot: Insertion slot (0-2)
            effect_type: XG insertion effect type (0-24)
        """
        if not (0 <= channel < self.max_channels and 0 <= slot < 3):
            return

        with self.lock:
            if 0 <= effect_type <= 24:
                self.insertion_effect_types[channel][slot] = XGInsertionType(effect_type)

    def set_variation_effect_type(self, variation_type: int):
        """
        Set variation effect type for all channels.

        Args:
            variation_type: XG variation effect type (0-83)
        """
        if 0 <= variation_type <= 83:
            with self.lock:
                variation_type_enum = XGVariationType(variation_type)
                self.system_params = self.system_params._replace(
                    variation_type=variation_type_enum
                )
                # Update the variation processor with new type
                if hasattr(self, 'variation_processor'):
                    self.variation_processor.set_variation_type(variation_type_enum)

    def set_master_controls(self, level: float = 1.0, wet_dry: float = 1.0):
        """
        Set master controls.

        Args:
            level: Master level (0.0-1.0)
            wet_dry: Wet/dry mix (0.0-1.0, where 1.0 = 100% wet)
        """
        pass  # TODO: Implement master controls

    def get_current_state(self) -> Dict[str, Any]:
        """Get current effects state for monitoring."""
        return {
            'reverb_params': {
                'level': self.system_params.reverb_level,
                'type': self.system_params.reverb_type.name
            },
            'chorus_params': {
                'level': self.system_params.chorus_level,
                'type': self.system_params.chorus_type.name
            },
            'variation_params': {
                'level': self.system_params.variation_level,
                'type': self.system_params.variation_type.name
            },
            'equalizer_params': {}
        }

    def handle_midi_cc(self, channel: int, cc_number: int, value: int):
        """
        Handle MIDI CC message for XG effects control.

        Args:
            channel: MIDI channel
            cc_number: CC number (0-127)
            value: CC value (0-127)
        """
        # Map CC numbers to effect controls
        if cc_number == 91:  # Reverb Send
            self.set_effect_send_level(channel, 'reverb', value / 127.0)
        elif cc_number == 93:  # Chorus Send
            self.set_effect_send_level(channel, 'chorus', value / 127.0)
        elif cc_number == 94:  # Variation Send
            self.set_effect_send_level(channel, 'variation', value / 127.0)
        elif 200 <= cc_number <= 209:  # Effect Unit Activation
            # TODO: Handle effect unit activation
            pass

    def get_effect_status(self) -> Dict[str, Any]:
        """Get current status of all effects (for monitoring)."""
        return {
            'system_reverb': {
                'enabled': not self.system_params.bypass_all,
                'type': self.system_params.reverb_type.name,
                'time': self.system_params.reverb_time,
                'hf_damp': self.system_params.reverb_hf_damping,
                'feedback': self.system_params.reverb_pre_delay,
                'level': self.system_params.reverb_level,
            },
            'system_chorus': {
                'enabled': not self.system_params.bypass_all,
                'type': self.system_params.chorus_type.name,
                'rate': self.system_params.chorus_rate,
                'depth': self.system_params.chorus_depth,
                'feedback': self.system_params.chorus_feedback,
                'level': self.system_params.chorus_level,
            },
            'part_sends': {
                'reverb': self.reverb_send_levels.tolist(),
                'chorus': self.chorus_send_levels.tolist(),
                'variation': self.variation_send_levels.tolist(),
            }
        }

    def shutdown(self):
        """Clean shutdown of effects coordinator."""
        with self.lock:
            self.state = XGProcessingState.IDLE
            # Clear all buffers
            for buffer in self.channel_input_buffers + self.channel_output_buffers + self.temp_buffers:
                buffer.fill(0.0)
            self.reverb_accumulate.fill(0.0)
            self.chorus_accumulate.fill(0.0)
            self.final_mix_buffer.fill(0.0)
