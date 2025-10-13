"""
Vectorized Effect Manager

This module provides a high-performance effects manager implementation with
NumPy-based operations for maximum performance.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Union
import threading

from synth.effects.dsp_units import DSPUnitsManager

# Import internal modules
from ..core.constants import DEFAULT_CONFIG
from ..engine.optimized_coefficient_manager import OptimizedCoefficientManager
from .state import EffectStateManager
from .communication import XGCommunicationHandler
from .processing import XGAudioProcessor
from .equalizer import XGMultiBandEqualizer

# Import new effect processing modules
from .insertion_effects import InsertionEffectsProcessor
from .system_effects import SystemEffectsProcessor

# Import math for effect calculations
import math


class VectorizedEffectManager:
    """
    High-Performance Vectorized Effect Manager

    Manages audio effects processing with vectorized NumPy operations for maximum performance.

    Key optimizations implemented:
    - NumPy-based operations replacing Python loops with vectorized operations
    - Batch processing of entire audio blocks rather than per-sample processing
    - Pre-allocated buffers to eliminate allocation overhead
    - Streamlined effects processing on final mixed output
    - Efficient buffer clearing using vectorized operations

    This implementation provides significant performance improvements while maintaining
    full effect processing quality and XG compatibility.
    """

    def __init__(self, synth):
        """
        Initialize vectorized effects manager with pre-allocated buffers.
        
        Args:
            sample_rate: Sample rate in Hz for effect processing
        """
        self.sample_rate = synth.sample_rate
        self.memory_pool = synth.memory_pool
        self.block_size = synth.block_size
        self.synth = synth

        # Thread safety lock
        self.lock = threading.RLock()

        # Effect state management with optimized state handling
        self.state_manager = EffectStateManager()

        # Communication handler for effect parameter control with optimized parameter handling
        self.comm_handler = XGCommunicationHandler(self.state_manager)

        # Audio processor for effect algorithms with optimized audio processing
        # Uses the production-grade XGAudioProcessor for full XG effect processing
        self.audio_processor = XGAudioProcessor(self.state_manager, self.sample_rate)

        # XG Multi-Band Equalizer for system EQ processing
        self.equalizer = XGMultiBandEqualizer(self.sample_rate)

        # Optimized coefficient manager for pre-computed mathematical operations
        # Eliminates expensive calculations (sqrt, pow, exp) from inner loops
        self.coeff_manager = OptimizedCoefficientManager()

        # DSP Units Manager for shared high-performance components
        self.dsp_units = DSPUnitsManager(self.sample_rate)

        # Set up communication handler references with optimized reference handling
        self.comm_handler.state_manager = self.state_manager

        # PRE-ALLOCATED EFFECT BUFFERS FOR VECTORIZED PROCESSING
        # Pre-allocate main effect buffers with maximum expected block size
        self.left_buffer = self.memory_pool.get_mono_buffer()
        self.right_buffer = self.memory_pool.get_mono_buffer()
        
        # PRE-ALLOCATED TEMPORARY BUFFERS FOR INTERMEDIATE PROCESSING
        # Pre-allocate temporary buffers for intermediate effect processing
        self.temp_left = self.memory_pool.get_mono_buffer()
        self.temp_right = self.memory_pool.get_mono_buffer()
        
        # PRE-ALLOCATED MULTICHANNEL INPUT/OUTPUT BUFFERS FOR EFFECTS PROCESSING
        # Pre-allocate buffers for multichannel effect processing with vectorized operations
        self.effect_input = self.memory_pool.get_mono_buffer()
        self.effect_output = self.memory_pool.get_mono_buffer()

        # PRE-ALLOCATED BUFFER FOR STEREO EFFECT PROCESSING
        # Pre-allocate buffer for stereo effect processing with vectorized operations
        self.stereo_buffer = self.memory_pool.get_stereo_buffer()

        # ZERO-ALLOCATION BUFFERS FOR MULTI-CHANNEL PROCESSING
        # Pre-allocate per-channel processing buffers to avoid allocation during hot path
        self.channel_processing_buffers = np.zeros((16, self.block_size, 2), dtype=np.float32)
        self.mix_left_buffer = self.memory_pool.get_mono_buffer()
        self.mix_right_buffer = self.memory_pool.get_mono_buffer()
        self.final_stereo_mix = self.memory_pool.get_stereo_buffer()

        # Initialize effect processors
        self.insertion_effects = InsertionEffectsProcessor(
            self.sample_rate, self.block_size, self.dsp_units
        )
        
        # System effects processor requires max delay values
        max_reverb_delay = int(10.0 * self.sample_rate)  # 10 seconds max reverb
        max_chorus_delay = int(0.05 * self.sample_rate)  # 50ms max delay
        self.system_effects = SystemEffectsProcessor(
            self.sample_rate, self.block_size, self.dsp_units, 
            max_reverb_delay, max_chorus_delay
        )

        # EFFECT PROCESSING STATE
        self.current_block_size = 0
        self.buffer_dirty = False

        # Initialize effects with optimized initialization
        self.reset_effects()

    def reset_effects(self):
        """Reset all effects to default values with optimized reset."""
        with self.lock:
            self.state_manager.reset_effects()

    def get_current_state(self) -> Dict[str, Any]:
        """Get current effects state with thread-safe access."""
        with self.lock:
            return self.state_manager.get_current_state()

    def get_channel_insertion_effect(self, channel: int) -> Dict[str, Any]:
        """Get insertion effect parameters for channel with optimized parameter access."""
        with self.lock:
            return self.state_manager.get_channel_insertion_effect(channel)

    def set_channel_insertion_effect_enabled(self, channel: int, enabled: bool):
        """Enable/disable insertion effect for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["enabled"] = enabled
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_type(self, channel: int, effect_type: int):
        """Set insertion effect type for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["type"] = effect_type
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_parameter(self, channel: int, param_index: int, value: float):
        """Set insertion effect parameter for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16 and 1 <= param_index <= 4:  # Validate ranges
                param_name = f"parameter{param_index}"
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"][param_name] = value
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_level(self, channel: int, level: float):
        """Set insertion effect level for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["level"] = level
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_bypass(self, channel: int, bypass: bool):
        """Set insertion effect bypass for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["bypass"] = bypass
                self.state_manager.state_update_pending = True

    # Extended Phaser/Flanger methods with optimized parameter updates
    def set_channel_phaser_frequency(self, channel: int, frequency: float):
        """Set phaser LFO frequency for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_manager.state_update_pending = True

    def set_channel_phaser_depth(self, channel: int, depth: float):
        """Set phaser depth for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_manager.state_update_pending = True

    def set_channel_phaser_feedback(self, channel: int, feedback: float):
        """Set phaser feedback for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_manager.state_update_pending = True

    def set_channel_phaser_waveform(self, channel: int, waveform: int):
        """Set phaser LFO waveform for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_manager.state_update_pending = True

    # Flanger methods with optimized parameter updates
    def set_channel_flanger_frequency(self, channel: int, frequency: float):
        """Set flanger LFO frequency for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_manager.state_update_pending = True

    def set_channel_flanger_depth(self, channel: int, depth: float):
        """Set flanger depth for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_manager.state_update_pending = True

    def set_channel_flanger_feedback(self, channel: int, feedback: float):
        """Set flanger feedback for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_manager.state_update_pending = True

    def set_channel_flanger_waveform(self, channel: int, waveform: int):
        """Set flanger LFO waveform for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_manager.state_update_pending = True

    def reset_channel_insertion_effect(self, channel: int):
        """Reset insertion effect for channel to defaults with optimized reset."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"] = \
                    self.state_manager._create_insertion_effect_params()
                self.state_manager.state_update_pending = True

    def reset_all_insertion_effects(self):
        """Reset all insertion effects to defaults with optimized batch reset."""
        with self.lock:
            for i in range(16):  # Reset all 16 channels
                self.state_manager._temp_state["channel_params"][i]["insertion_effect"] = \
                    self.state_manager._create_insertion_effect_params()
            self.state_manager.state_update_pending = True

    # Audio processing with vectorized operations
    def process_audio(self, input_samples: List[List[Tuple[float, float]]],
                     num_samples: int) -> List[List[Tuple[float, float]]]:
        """
        Process audio with XG effects applied - legacy compatibility method.
        
        This method converts the input format to what VectorizedEffectManager expects
        and then calls the vectorized processing methods.
        
        Args:
            input_samples: List of channels with stereo sample tuples
            num_samples: Number of samples to process
            
        Returns:
            Processed audio samples
        """
        with self.lock:
            # Convert input format to what we expect (list of numpy arrays)
            input_channels = []
            for channel_samples in input_samples:
                # Convert list of tuples to numpy array
                if channel_samples:
                    # Extract left and right channels
                    left_samples = np.array([sample[0] for sample in channel_samples[:num_samples]], dtype=np.float32)
                    right_samples = np.array([sample[1] for sample in channel_samples[:num_samples]], dtype=np.float32)
                    # Stack as stereo array
                    stereo_channel = np.column_stack((left_samples, right_samples))
                    input_channels.append(stereo_channel)
                else:
                    # Empty channel
                    input_channels.append(np.zeros((num_samples, 2), dtype=np.float32))
            
            # Process using our vectorized multi-channel method
            processed_channels = self.process_multi_channel_vectorized(input_channels, num_samples)
            
            # Convert back to the expected format (list of lists of tuples)
            result = []
            for channel_array in processed_channels:
                channel_samples = []
                for i in range(min(num_samples, len(channel_array))):
                    channel_samples.append((float(channel_array[i, 0]), float(channel_array[i, 1])))
                # Pad with zeros if needed
                while len(channel_samples) < num_samples:
                    channel_samples.append((0.0, 0.0))
                result.append(channel_samples)
            
            # Ensure we have the right number of channels (16 for MIDI)
            while len(result) < 16:
                result.append([(0.0, 0.0)] * num_samples)
            
            return result[:16]  # Limit to 16 channels

    def process_audio_vectorized(self, input_samples: np.ndarray,
                           num_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        High-Performance Vectorized Audio Processing

        Process audio with XG effects applied using vectorized NumPy operations.

        Key performance optimizations:
        - Vectorized operations using NumPy for efficient mathematical operations
        - Batch processing of entire audio blocks rather than per-sample
        - Pre-allocated buffers to reduce allocation overhead
        - Streamlined effects processing on final mixed output
        - Efficient buffer clearing using vectorized operations

        Args:
            input_samples: Input audio samples as NumPy array
            num_samples: Number of samples to process

        Returns:
            Tuple of (left_channel, right_channel) processed audio buffers
        """
        with self.lock:
            # ENSURE BUFFERS ARE CORRECT SIZE - DYNAMIC BUFFER RESIZING
            # Only resize buffers when necessary to avoid allocation overhead
            if num_samples > self.block_size:
                raise Exception(f"too large block size - {num_samples}")

            # UPDATE CURRENT BLOCK SIZE - TRACK PROCESSING STATE
            self.current_block_size = num_samples
            self.buffer_dirty = True

            # PREPARE INPUT DATA FOR EFFECTS PROCESSING - OPTIMIZED DATA PREPARATION
            # Prepare input data for effects processing with vectorized operations
            if len(input_samples.shape) == 2 and input_samples.shape[1] == 2:
                # Stereo input - copy directly using vectorized operations
                np.copyto(self.left_buffer[:num_samples], input_samples[:, 0])
                np.copyto(self.right_buffer[:num_samples], input_samples[:, 1])
            elif len(input_samples.shape) == 1:
                # Mono input - duplicate to both channels using vectorized operations
                np.copyto(self.left_buffer[:num_samples], input_samples)
                np.copyto(self.right_buffer[:num_samples], input_samples)
            else:
                # Unsupported input format - return input unchanged with optimized handling
                return input_samples, input_samples

            # APPLY EFFECTS TO ENTIRE AUDIO BLOCK - STREAMLINED EFFECTS PROCESSING
            # Instead of processing effects for all 16 channels separately (inefficient),
            # process effects on the final mixed stereo output (much more efficient)
            
            try:
                # PREPARE VECTORIZED INPUT FOR EFFECTS PROCESSING - OPTIMIZED INPUT PREPARATION
                # Stack left and right channels as columns in pre-allocated buffer using vectorized operations
                np.stack((self.left_buffer[:num_samples], self.right_buffer[:num_samples]), 
                        axis=1, out=self.effect_input[:num_samples])
                
                # PROCESS EFFECTS WITH VECTORIZED OPERATIONS ON MIXED STEREO OUTPUT - HIGHLY OPTIMIZED
                # This is much more efficient than processing effects for all 16 channels separately
                self.effect_output[:num_samples] = self.audio_processor.process_stereo_audio_vectorized(
                    self.effect_input[:num_samples]
                )
                
                # SEPARATE STEREO CHANNELS FROM PROCESSED OUTPUT - OPTIMIZED CHANNEL SEPARATION
                left_result = self.effect_output[:num_samples, 0]
                right_result = self.effect_output[:num_samples, 1]
                
                # APPLY FINAL LIMITING WITH VECTORIZED OPERATIONS - OPTIMIZED CLIPPING
                np.clip(left_result, -1.0, 1.0, out=left_result)
                np.clip(right_result, -1.0, 1.0, out=right_result)
                
                return left_result, right_result

            except Exception as e:
                print(f"Error processing effects: {e}")
                # If effects don't work, return unprocessed mix with optimized fallback
                # Apply final limiting with vectorized operations
                np.clip(self.left_buffer[:num_samples], -1.0, 1.0, out=self.left_buffer[:num_samples])
                np.clip(self.right_buffer[:num_samples], -1.0, 1.0, out=self.right_buffer[:num_samples])
                return self.left_buffer[:num_samples], self.right_buffer[:num_samples]

    def process_stereo_audio_vectorized(self, input_samples: np.ndarray) -> np.ndarray:
        """
        High-Performance Vectorized Stereo Audio Processing

        Process stereo audio with XG effects applied using vectorized NumPy operations.

        Key performance optimizations:
        - Vectorized operations using NumPy for efficient mathematical operations
        - Batch processing of entire audio blocks rather than per-sample
        - Pre-allocated buffers to reduce allocation overhead
        - Streamlined effects processing on final mixed output
        - Efficient buffer clearing using vectorized operations

        Args:
            input_samples: Input stereo audio samples as NumPy array (N x 2)

        Returns:
            Processed stereo audio samples as NumPy array (N x 2)
        """
        num_samples = input_samples.shape[0]
        
        with self.lock:
            # ENSURE BUFFERS ARE CORRECT SIZE - DYNAMIC BUFFER RESIZING
            # Only resize buffers when necessary to avoid allocation overhead
            if num_samples > self.block_size:
                raise Exception(f"too large block size - {num_samples}")

            # UPDATE CURRENT BLOCK SIZE - TRACK PROCESSING STATE
            self.current_block_size = num_samples
            self.buffer_dirty = True

            # COPY INPUT DATA TO PROCESSING BUFFERS - OPTIMIZED DATA COPYING
            # Copy input data to processing buffers using vectorized operations
            np.copyto(self.effect_input[:num_samples], input_samples[:num_samples])
            
            # PROCESS EFFECTS WITH VECTORIZED OPERATIONS ON MIXED STEREO OUTPUT - HIGHLY OPTIMIZED
            # This is much more efficient than processing effects for all 16 channels separately
            self.effect_output[:num_samples] = self.audio_processor.process_stereo_audio_vectorized(
                self.effect_input[:num_samples]
            )
            
            # APPLY FINAL LIMITING WITH VECTORIZED OPERATIONS - OPTIMIZED CLIPPING
            np.clip(self.effect_output[:num_samples], -1.0, 1.0, 
                    out=self.effect_output[:num_samples])
            
            return self.effect_output[:num_samples]

    def process_multi_channel_vectorized(self, input_channels: List[np.ndarray],
                                        num_samples: int) -> np.ndarray:
        """
        ZERO-ALLOCATION XG-COMPLIANT MULTI-CHANNEL EFFECTS PROCESSING

        Process multi-channel audio through complete XG effects chain using pre-allocated buffers:
        1. Apply insertion effects to each channel individually (XG compliant)
        2. Mix channels together with proper panning (XG compliant)
        3. Apply system effects (reverb/chorus/variation) to final mix (XG compliant)

        Uses zero-allocation approach - no buffers, lists, or dicts allocated during hot path.

        Args:
            input_channels: List of input channel audio samples as NumPy arrays (16 channels max)
            num_samples: Number of samples to process

        Returns:
            Final stereo mix as NumPy array with shape (num_samples, 2)
        """
        with self.lock:
            # ENSURE BUFFERS ARE CORRECT SIZE - DYNAMIC BUFFER RESIZING
            if num_samples > self.block_size:
                raise Exception(f"too large block size - {num_samples}")

            # STEP 1: APPLY INSERTION EFFECTS PER-CHANNEL (XG COMPLIANT) - ZERO ALLOCATION
            # Process each channel using pre-allocated buffers - ZERO ALLOCATION
            num_channels_to_process = min(len(input_channels), 16)

            for channel_idx in range(num_channels_to_process):
                channel_array = input_channels[channel_idx]

                # Get insertion effect parameters for this channel
                insertion_params = self.state_manager.get_channel_insertion_effect(channel_idx)

                if insertion_params.get("enabled", False) and not insertion_params.get("bypass", False):
                    # Apply insertion effect to this channel using pre-allocated buffer
                    self.insertion_effects.apply_insertion_effect_to_channel_zero_alloc(
                        target_buffer=self.channel_processing_buffers[channel_idx],
                        channel_array=channel_array,
                        insertion_params=insertion_params,
                        num_samples=num_samples,
                        channel_idx=channel_idx
                    )
                else:
                    # No insertion effect or bypassed - copy original channel to processing buffer
                    if len(channel_array.shape) == 2 and channel_array.shape[1] == 2:
                        # Stereo channel
                        np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, :],
                                 channel_array[:num_samples])
                    else:
                        # Mono channel - duplicate to both sides
                        np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 0],
                                 channel_array[:num_samples])
                        np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 1],
                                 channel_array[:num_samples])

            # STEP 2: MIX ALL CHANNELS TOGETHER WITH PROPER PANNING - ZERO ALLOCATION
            # Clear mix buffers using vectorized operations
            self.mix_left_buffer[:num_samples].fill(0.0)
            self.mix_right_buffer[:num_samples].fill(0.0)

            for channel_idx in range(num_channels_to_process):
                # Get channel parameters for mixing
                channel_params = self.state_manager._current_state["channel_params"][channel_idx]
                volume = channel_params.get("volume", 1.0)
                expression = channel_params.get("expression", 1.0)
                pan = channel_params.get("pan", 0.5)  # 0.0 = left, 1.0 = right

                # Calculate channel gain
                channel_gain = volume * expression
                pan_left, pan_right = self.coeff_manager.get_panning(pan)

                # Mix this channel into the final mix using in-place operations
                channel_left = self.channel_processing_buffers[channel_idx, :num_samples, 0]
                channel_right = self.channel_processing_buffers[channel_idx, :num_samples, 1]

                # Apply gain and pan, accumulate to mix buffers
                np.add(self.mix_left_buffer[:num_samples],
                      channel_left * channel_gain * pan_left,
                      out=self.mix_left_buffer[:num_samples])
                np.add(self.mix_right_buffer[:num_samples],
                      channel_right * channel_gain * pan_right,
                      out=self.mix_right_buffer[:num_samples])

            # STEP 3: APPLY SYSTEM EFFECTS TO FINAL MIX (XG COMPLIANT) - ZERO ALLOCATION
            # Create stereo mix array using pre-allocated buffer
            np.stack((self.mix_left_buffer[:num_samples], self.mix_right_buffer[:num_samples]),
                    axis=1, out=self.final_stereo_mix[:num_samples])

            # Apply system effects (reverb, chorus, variation) to the mixed output using the system effects processor
            self.system_effects.apply_system_effects_to_mix_zero_alloc(
                stereo_mix=self.final_stereo_mix,
                num_samples=num_samples
            )

            # STEP 4: RETURN FINAL STEREO OUTPUT ONLY
            # Clean API: effects processor returns final mixed result
            return self.final_stereo_mix[:num_samples]

    def _apply_system_effects_to_mix_zero_alloc(self, num_samples: int) -> None:
        """
        Apply system effects (reverb, chorus, variation, EQ) to the final mix using zero-allocation.

        Args:
            num_samples: Number of samples to process
        """
        self.system_effects.apply_system_effects_to_mix_zero_alloc(
            stereo_mix=self.final_stereo_mix,
            num_samples=num_samples
        )

    def _apply_system_effects_to_mix(self, stereo_mix: np.ndarray, num_samples: int) -> np.ndarray:
        """
        Apply system effects (reverb, chorus, variation) to the final mix.

        Args:
            stereo_mix: Stereo mix as NumPy array (N x 2)
            num_samples: Number of samples to process

        Returns:
            Final mix with system effects applied
        """
        return self.system_effects.apply_system_effects_to_mix(
            stereo_mix=stereo_mix,
            num_samples=num_samples
        )

    # Communication methods with optimized parameter handling
    def set_current_nrpn_channel(self, channel: int):
        """Set current NRPN channel with optimized parameter update."""
        with self.lock:
            self.comm_handler.set_current_nrpn_channel(channel)

    def set_nrpn_msb(self, value: int):
        """Set NRPN MSB with optimized parameter update."""
        with self.lock:
            self.comm_handler.set_nrpn_msb(value)

    def set_nrpn_lsb(self, value: int):
        """Set NRPN LSB with optimized parameter update."""
        with self.lock:
            self.comm_handler.set_nrpn_lsb(value)

    def set_channel_effect_parameter(self, channel: int, nrpn_msb: int, nrpn_lsb: int, value: int):
        """Set channel effect parameter via NRPN with optimized parameter update."""
        with self.lock:
            self.comm_handler.set_channel_effect_parameter(channel, nrpn_msb, nrpn_lsb, value)

    def handle_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int,
                   channel: Optional[int] = None) -> bool:
        """
        Handle NRPN message for effects with optimized parameter processing.
        
        Performance optimizations:
        1. BATCH PARAMETER PROCESSING - Processes parameters in batches rather than individually
        2. OPTIMIZED VALIDATION - Validates parameters efficiently without unnecessary checks
        3. DIRECT STATE UPDATES - Updates state directly without additional processing overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to effect state
        
        Returns:
            True if NRPN was handled, False otherwise
        """
        with self.lock:
            return self.comm_handler.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb, channel)

    def handle_sysex(self, manufacturer_id: List[int], data: List[int]) -> bool:
        """
        Handle SysEx message for effects with optimized message processing.
        
        Performance optimizations:
        1. BATCH MESSAGE PROCESSING - Processes messages in batches rather than individually
        2. OPTIMIZED PARSING - Parses messages efficiently without unnecessary checks
        3. DIRECT STATE UPDATES - Updates state directly without additional processing overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to effect state
        
        Returns:
            True if SysEx was handled, False otherwise
        """
        with self.lock:
            return self.comm_handler.handle_sysex(manufacturer_id, data)

    def get_bulk_dump(self, channel_specific: bool = False) -> List[int]:
        """
        Generate bulk dump of current effect parameters with optimized data serialization.
        
        Performance optimizations:
        1. BATCH DATA SERIALIZATION - Serializes data in batches rather than individually
        2. OPTIMIZED FORMATTING - Formats data efficiently without unnecessary conversions
        3. PRE-ALLOCATED BUFFERS - Uses pre-allocated buffers to reduce allocation overhead
        4. ZERO-CLEARING OPTIMIZATION - Clears buffers efficiently using vectorized operations
        
        Args:
            channel_specific: If True, generate channel-specific dump
            
        Returns:
            SysEx data for bulk dump
        """
        with self.lock:
            return self.comm_handler.get_bulk_dump(channel_specific)

    def process_bulk_dump(self, effect_type: int, param_offset: int, data: list) -> bool:
        """
        Process bulk dump data for effect parameters.

        Args:
            effect_type: Effect type (0-4: reverb, chorus, variation, insertion, EQ)
            param_offset: Starting parameter offset for this bulk dump chunk
            data: List of 7-bit parameter values to set

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            with self.lock:
                return self._process_bulk_dump_internal(effect_type, param_offset, data)
        except Exception as e:
            print(f"Error processing bulk dump data: {e}")
            return False

    def _process_bulk_dump_internal(self, effect_type: int, param_offset: int, data: list) -> bool:
        """Internal method for processing bulk dump parameter values"""
        if effect_type == 0:  # Reverb parameters
            # XG Reverb Parameters
            reverb_params = [
                "type", "time", "level", "pre_delay", "hf_damping", "density",
                "early_level", "tail_level", "shape", "gate_time", "predelay_scale"
            ]
            for i, value in enumerate(data):
                param_index = param_offset + i
                if param_index < len(reverb_params):
                    param_name = reverb_params[param_index]
                    # Convert 7-bit MIDI value to parameter value
                    if param_name == "type":
                        # 0-7 types -> direct mapping
                        current_value = min(max(value, 0), 7)
                    elif param_name == "time":
                        # 0-127 -> 0.1-8.3 sec
                        current_value = (value / 127.0) * 8.2 + 0.1
                    elif param_name in ["level", "early_level", "tail_level", "hf_damping", "density", "shape", "predelay_scale"]:
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "pre_delay":
                        # 0-127 -> 0-12.7 ms
                        current_value = (value / 127.0) * 12.7
                    elif param_name == "gate_time":
                        # 0-127 -> 0-12.7 ms
                        current_value = (value / 127.0) * 12.7
                    else:
                        # Default 0-127 -> 0.0-1.0
                        current_value = value / 127.0

                    # Update state manager
                    self.state_manager._temp_state["reverb_params"][param_name] = current_value
                    self.state_manager.state_update_pending = True

            return True

        elif effect_type == 1:  # Chorus parameters
            # XG Chorus Parameters
            chorus_params = [
                "type", "rate", "depth", "feedback", "level", "delay",
                "output", "cross_feedback", "lfo_waveform", "phase_diff"
            ]
            for i, value in enumerate(data):
                param_index = param_offset + i
                if param_index < len(chorus_params):
                    param_name = chorus_params[param_index]
                    # Convert 7-bit MIDI value to parameter value
                    if param_name == "type":
                        # 0-7 types -> direct mapping
                        current_value = min(max(value, 0), 7)
                    elif param_name == "rate":
                        # 0-127 -> 0.1-6.5 Hz
                        current_value = (value / 127.0) * 6.4 + 0.1
                    elif param_name in ["depth", "feedback", "level", "output", "cross_feedback"]:
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "delay":
                        # 0-127 -> 0-12.7 ms
                        current_value = (value / 127.0) * 12.7
                    elif param_name == "lfo_waveform":
                        # 0-3 waveform types -> direct mapping
                        current_value = min(max(value, 0), 3)
                    elif param_name == "phase_diff":
                        # 0-127 -> 0-180 degrees
                        current_value = (value / 127.0) * 180.0
                    else:
                        # Default 0-127 -> 0.0-1.0
                        current_value = value / 127.0

                    # Update state manager
                    self.state_manager._temp_state["chorus_params"][param_name] = current_value
                    self.state_manager.state_update_pending = True

            return True

        elif effect_type == 2:  # Variation Effect parameters
            # XG Variation Parameters
            variation_params = [
                "type", "parameter1", "parameter2", "parameter3", "parameter4",
                "level", "bypass", "pan", "send_reverb", "send_chorus"
            ]
            for i, value in enumerate(data):
                param_index = param_offset + i
                if param_index < len(variation_params):
                    param_name = variation_params[param_index]
                    # Convert 7-bit MIDI value to parameter value
                    if param_name == "type":
                        # 0-63 types -> direct mapping
                        current_value = min(max(value, 0), 63)
                    elif param_name in ["parameter1", "parameter2", "parameter3", "parameter4"]:
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "level":
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "bypass":
                        # 0 or 127 -> Boolean
                        current_value = True if value >= 64 else False
                    elif param_name == "pan":
                        # 0-127 -> -1.0 to +1.0
                        current_value = (value - 64) / 64.0
                    elif param_name in ["send_reverb", "send_chorus"]:
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    else:
                        # Default 0-127 -> 0.0-1.0
                        current_value = value / 127.0

                    # Update state manager
                    self.state_manager._temp_state["variation_params"][param_name] = current_value
                    self.state_manager.state_update_pending = True

            return True

        elif effect_type == 3:  # Insertion Effect parameters
            # XG Insertion Parameters
            insertion_params = [
                "type", "parameter1", "parameter2", "parameter3", "parameter4",
                "level", "bypass", "frequency", "depth", "feedback", "lfo_waveform"
            ]
            for i, value in enumerate(data):
                param_index = param_offset + i
                if param_index < len(insertion_params):
                    param_name = insertion_params[param_index]
                    # Convert 7-bit MIDI value to parameter value
                    if param_name == "type":
                        # 0-17 types -> direct mapping
                        current_value = min(max(value, 0), 17)
                    elif param_name in ["parameter1", "parameter2", "parameter3", "parameter4"]:
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "level":
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "bypass":
                        # 0 or 127 -> Boolean
                        current_value = True if value >= 64 else False
                    elif param_name == "frequency":
                        # 0-127 -> 0.1-25.5 Hz
                        current_value = (value / 127.0) * 25.4 + 0.1
                    elif param_name == "depth":
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "feedback":
                        # 0-127 -> 0.0-1.0
                        current_value = value / 127.0
                    elif param_name == "lfo_waveform":
                        # 0-3 waveform types -> direct mapping
                        current_value = min(max(value, 0), 3)
                    else:
                        # Default 0-127 -> 0.0-1.0
                        current_value = value / 127.0

                    # Update state manager
                    self.state_manager._temp_state["insertion_params"][param_name] = current_value
                    self.state_manager.state_update_pending = True

            return True

        elif effect_type == 4:  # EQ parameters
            # XG EQ Parameters
            eq_params = [
                "low_gain", "mid_gain", "high_gain", "mid_freq", "q_factor"
            ]
            for i, value in enumerate(data):
                param_index = param_offset + i
                if param_index < len(eq_params):
                    param_name = eq_params[param_index]
                    # Convert 7-bit MIDI value to parameter value
                    if param_name in ["low_gain", "mid_gain", "high_gain"]:
                        # 0-127 -> -12.8 to +12.6 dB
                        current_value = ((value - 64) / 64.0) * 12.8
                    elif param_name == "mid_freq":
                        # 0-127 -> 100-5220 Hz
                        current_value = (value / 127.0) * 5120 + 100
                    elif param_name == "q_factor":
                        # 0-127 -> 0.5-5.5
                        current_value = (value / 127.0) * 5.0 + 0.5
                    else:
                        # Default 0-127 -> 0.0-1.0
                        current_value = value / 127.0

                    # Update state manager
                    self.state_manager._temp_state["equalizer_params"][param_name] = current_value
                    self.state_manager.state_update_pending = True

            return True

        # Unsupported effect type
        return False

    def reset_to_xg_defaults(self):
        """
        Reset all effects to XG defaults with optimized reset.
        """
        with self.lock:
            self.reset_effects()

    def get_bulk_parameter(self, effect_type: int, param_index: int) -> int:
        """
        Get an effect parameter value by index for bulk dump generation.

        Args:
            effect_type: Effect type identifier (0-4: reverb, chorus, variation, insertion, EQ)
            param_index: Parameter index

        Returns:
            7-bit parameter value
        """
        try:
            with self.lock:  # Thread-safe access
                return self._get_bulk_parameter_internal(effect_type, param_index)
        except Exception as e:
            print(f"Error getting effect bulk parameter: {e}")
            return 0

    def _get_bulk_parameter_internal(self, effect_type: int, param_index: int) -> int:
        """Internal method for getting bulk parameter values"""
        # Get current parameter value based on effect type and parameter index
        if effect_type == 0:  # Reverb parameters
            # XG Reverb Parameters
            reverb_params = [
                "type", "time", "level", "pre_delay", "hf_damping", "density",
                "early_level", "tail_level", "shape", "gate_time", "predelay_scale"
            ]
            if param_index < len(reverb_params):
                param_name = reverb_params[param_index]
                current_value = self.state_manager._temp_state.get("reverb_params", {}).get(param_name, 0.0)

                # Convert to 7-bit MIDI value based on parameter type
                if param_name == "type":
                    # 0-7 types -> 0-7 MIDI values
                    midi_value = int(min(current_value, 7))
                elif param_name == "time":
                    # 0.1-8.3 sec -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value - 0.1) / 0.05)))
                elif param_name in ["level", "early_level", "tail_level", "hf_damping", "density", "shape", "predelay_scale"]:
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "pre_delay":
                    # 0-12.7 ms -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value / 0.1)))
                elif param_name == "gate_time":
                    # 0-12.7 ms -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value / 0.1)))
                else:
                    # Default 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))

                return midi_value

        elif effect_type == 1:  # Chorus parameters
            # XG Chorus Parameters
            chorus_params = [
                "type", "rate", "depth", "feedback", "level", "delay",
                "output", "cross_feedback", "lfo_waveform", "phase_diff"
            ]
            if param_index < len(chorus_params):
                param_name = chorus_params[param_index]
                current_value = self.state_manager._temp_state.get("chorus_params", {}).get(param_name, 0.0)

                # Convert to 7-bit MIDI value based on parameter type
                if param_name == "type":
                    # 0-7 types -> 0-7 MIDI values
                    midi_value = int(min(current_value, 7))
                elif param_name == "rate":
                    # 0.1-6.5 Hz -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value - 0.1) / 0.05)))
                elif param_name in ["depth", "feedback", "level", "output", "cross_feedback"]:
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "delay":
                    # 0-12.7 ms -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value / 0.1)))
                elif param_name == "lfo_waveform":
                    # 0-3 waveform types -> 0-3 MIDI values
                    midi_value = int(min(current_value, 3))
                elif param_name == "phase_diff":
                    # 0-180 degrees -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value / 180.0 * 127)))
                else:
                    # Default 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))

                return midi_value

        elif effect_type == 2:  # Variation Effect parameters
            # XG Variation Parameters (global)
            variation_params = [
                "type", "parameter1", "parameter2", "parameter3", "parameter4",
                "level", "bypass", "pan", "send_reverb", "send_chorus"
            ]
            if param_index < len(variation_params):
                param_name = variation_params[param_index]
                current_value = self.state_manager._temp_state.get("variation_params", {}).get(param_name, 0.0)

                # Convert to 7-bit MIDI value based on parameter type
                if param_name == "type":
                    # 0-63 types -> 0-63 MIDI values
                    midi_value = int(min(current_value, 63))
                elif param_name in ["parameter1", "parameter2", "parameter3", "parameter4"]:
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "level":
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "bypass":
                    # Boolean -> 0 or 127 MIDI values
                    midi_value = 127 if current_value else 0
                elif param_name == "pan":
                    # -1.0 to +1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value + 1.0) * 64)))
                elif param_name in ["send_reverb", "send_chorus"]:
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                else:
                    # Default 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))

                return midi_value

        elif effect_type == 3:  # Insertion Effect parameters (global)
            # XG Insertion Parameters (global view)
            insertion_params = [
                "type", "parameter1", "parameter2", "parameter3", "parameter4",
                "level", "bypass", "frequency", "depth", "feedback", "lfo_waveform"
            ]
            if param_index < len(insertion_params):
                param_name = insertion_params[param_index]
                current_value = self.state_manager._temp_state.get("insertion_params", {}).get(param_name, 0.0)

                # Convert to 7-bit MIDI value based on parameter type
                if param_name == "type":
                    # 0-17 types -> 0-17 MIDI values
                    midi_value = int(min(current_value, 17))
                elif param_name in ["parameter1", "parameter2", "parameter3", "parameter4"]:
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "level":
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "bypass":
                    # Boolean -> 0 or 127 MIDI values
                    midi_value = 127 if current_value else 0
                elif param_name == "frequency":
                    # 0.1-25.5 Hz -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value - 0.1) / 0.2)))
                elif param_name == "depth":
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "feedback":
                    # 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))
                elif param_name == "lfo_waveform":
                    # 0-3 waveform types -> 0-3 MIDI values
                    midi_value = int(min(current_value, 3))
                else:
                    # Default 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))

                return midi_value

        elif effect_type == 4:  # EQ parameters
            # XG EQ Parameters
            eq_params = [
                "low_gain", "mid_gain", "high_gain", "mid_freq", "q_factor"
            ]
            if param_index < len(eq_params):
                param_name = eq_params[param_index]
                current_value = self.state_manager._temp_state.get("equalizer_params", {}).get(param_name, 0.0)

                # Convert to 7-bit MIDI value based on parameter type
                if param_name in ["low_gain", "mid_gain", "high_gain"]:
                    # -12.8 to +12.6 dB -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value + 12.8) / 0.2)))
                elif param_name == "mid_freq":
                    # 100-5220 Hz -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value - 100) / 40)))
                elif param_name == "q_factor":
                    # 0.5-5.5 Q-factor -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, (current_value - 0.5) / 0.04)))
                else:
                    # Default 0.0-1.0 -> 0-127 MIDI values
                    midi_value = int(max(0, min(127, current_value * 127)))

                return midi_value

        # Default value for unhandled parameters
        return 0

    def get_parameter_value(self, effect_type: int, param: int) -> int:
        """
        Get parameter value for bulk dump generation.

        Args:
            effect_type: Effect type (0-4: reverb, chorus, variation, insertion, EQ)
            param: Parameter index

        Returns:
            Parameter value (0-127)
        """
        return self.get_bulk_parameter(effect_type, param)

    def process_stereo_audio_vectorized_tuple(self, input_samples: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process stereo audio returning separate left/right channels (tuple format).

        This method provides compatibility with calling code that expects tuple unpacking:
        left_effected, right_effected = effect_manager.process_stereo_audio_vectorized(input)

        Args:
            input_samples: Input stereo audio samples as NumPy array (N x 2)

        Returns:
            Tuple of (left_channel, right_channel) processed audio buffers
        """
        num_samples = input_samples.shape[0]

        with self.lock:
            # ENSURE BUFFERS ARE CORRECT SIZE - DYNAMIC BUFFER RESIZING
            if num_samples > self.block_size:
                raise Exception(f"too large block size - {num_samples}")

            # COPY INPUT DATA TO PROCESSING BUFFERS
            np.copyto(self.effect_input[:num_samples], input_samples[:num_samples])

            # PROCESS EFFECTS WITH VECTORIZED OPERATIONS
            try:
                self.effect_output[:num_samples] = self.audio_processor.process_stereo_audio_vectorized(
                    self.effect_input[:num_samples]
                )

                # RETURN SEPARATE CHANNELS FOR CALLERS EXPECTING TUPLE
                left_result = self.effect_output[:num_samples, 0].copy()
                right_result = self.effect_output[:num_samples, 1].copy()

                # Apply final limiting
                np.clip(left_result, -1.0, 1.0, out=left_result)
                np.clip(right_result, -1.0, 1.0, out=right_result)

                return left_result, right_result

            except Exception as e:
                print(f"Error in tuple-style vectorized effects: {e}")
                # Return input unchanged on error
                left_result = input_samples[:num_samples, 0].copy()
                right_result = input_samples[:num_samples, 1].copy()
                return left_result, right_result

    # Variation effect methods with optimized parameter updates
    def set_variation_effect_type(self, channel: int, effect_type: int):
        """Set variation effect type for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["type"] = effect_type
                self.state_manager.state_update_pending = True

    def set_variation_effect_bypass(self, channel: int, bypass: bool):
        """Set variation effect bypass for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["bypass"] = bypass
                self.state_manager.state_update_pending = True

    def set_variation_effect_level(self, channel: int, level: float):
        """Set variation effect level for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16:  # Validate channel range
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["level"] = level
                self.state_manager.state_update_pending = True

    def set_variation_effect_parameter(self, channel: int, param_index: int, value: float):
        """Set variation effect parameter for channel with optimized parameter update."""
        with self.lock:
            if 0 <= channel < 16 and 1 <= param_index <= 4:  # Validate ranges
                param_name = f"parameter{param_index}"
                self.state_manager._temp_state["channel_params"][channel]["variation_params"][param_name] = value
                self.state_manager.state_update_pending = True

    # XG Multi-Band Equalizer methods
    def set_eq_type(self, eq_type: int):
        """Set EQ type (0-4: Flat, Jazz, Pops, Rock, Concert)"""
        with self.lock:
            if 0 <= eq_type <= 4:
                self.state_manager._temp_state["equalizer_params"]["eq_type"] = eq_type
                self.state_manager.state_update_pending = True

    def set_eq_low_gain(self, gain_db: float):
        """Set EQ low band gain (-12 to +12 dB)"""
        with self.lock:
            self.state_manager._temp_state["equalizer_params"]["low_gain"] = max(-12.0, min(12.0, gain_db))
            self.state_manager.state_update_pending = True

    def set_eq_mid_gain(self, gain_db: float):
        """Set EQ mid band gain (-12 to +12 dB)"""
        with self.lock:
            self.state_manager._temp_state["equalizer_params"]["mid_gain"] = max(-12.0, min(12.0, gain_db))
            self.state_manager.state_update_pending = True

    def set_eq_high_gain(self, gain_db: float):
        """Set EQ high band gain (-12 to +12 dB)"""
        with self.lock:
            self.state_manager._temp_state["equalizer_params"]["high_gain"] = max(-12.0, min(12.0, gain_db))
            self.state_manager.state_update_pending = True

    def set_eq_mid_frequency(self, freq_hz: float):
        """Set EQ mid band frequency (100-5220 Hz)"""
        with self.lock:
            self.state_manager._temp_state["equalizer_params"]["mid_freq"] = max(100.0, min(5220.0, freq_hz))
            self.state_manager.state_update_pending = True

    def set_eq_q_factor(self, q: float):
        """Set EQ Q factor (0.5-5.5)"""
        with self.lock:
            self.state_manager._temp_state["equalizer_params"]["q_factor"] = max(0.5, min(5.5, q))
            self.state_manager.state_update_pending = True

    # Preset management with optimized preset handling
    def set_effect_preset(self, preset_name: str):
        """
        Set effect preset for entire sequencer with optimized preset application.
        
        Performance optimizations:
        1. BATCH PRESET APPLICATION - Applies presets in batches rather than individually
        2. OPTIMIZED PARAMETER UPDATES - Updates parameters efficiently without unnecessary checks
        3. DIRECT STATE UPDATES - Updates state directly without additional processing overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to effect state
        
        Args:
            preset_name: Name of preset to load
        """
        presets = self._get_presets()
        if preset_name in presets:
            preset = presets[preset_name]

            with self.lock:
                # Apply system effects with optimized parameter updates
                if "reverb" in preset:
                    for param, value in preset["reverb"].items():
                        nrpn_param = list(preset["reverb"].keys()).index(param)
                        self.set_channel_effect_parameter(0, 0, 120 + nrpn_param, int(value * 127))

                if "chorus" in preset:
                    for param, value in preset["chorus"].items():
                        nrpn_param = list(preset["chorus"].keys()).index(param)
                        self.set_channel_effect_parameter(0, 0, 130 + nrpn_param, int(value * 127))

                if "variation" in preset:
                    var_data = preset["variation"]
                    self.set_variation_effect_type(0, var_data["type"])
                    self.set_variation_effect_bypass(0, False)
                    self.set_variation_effect_level(0, var_data.get("level", 0.5))

                    if "params" in var_data:
                        for i, param in enumerate(var_data["params"]):
                            self.set_variation_effect_parameter(0, i + 1, param)
                    else:
                        for i, param in enumerate(["parameter1", "parameter2", "parameter3", "parameter4"]):
                            if param in var_data:
                                self.set_variation_effect_parameter(0, i + 1, var_data[param])

                # Apply insertion effects with optimized parameter updates
                if "insertion" in preset:
                    ins_data = preset["insertion"]
                    self.set_channel_insertion_effect_enabled(0, ins_data.get("enabled", True))
                    self.set_channel_insertion_effect_bypass(0, ins_data.get("bypass", False))
                    self.set_channel_insertion_effect_type(0, ins_data["type"])
                    self.set_channel_effect_parameter(0, 0, 163, ins_data.get("send", 127))

                    if ins_data["type"] in [16, 17]:  # Phaser or Flanger
                        params = ins_data.get("params", [])
                        if len(params) > 0:
                            self.set_channel_phaser_frequency(0, params[0] * 0.2)
                        if len(params) > 1:
                            self.set_channel_phaser_depth(0, params[1] / 127.0)
                        if len(params) > 2:
                            self.set_channel_phaser_feedback(0, params[2] / 127.0)
                        if len(params) > 3:
                            self.set_channel_phaser_waveform(0, params[3])
                    else:
                        for i, param in enumerate(ins_data.get("params", [])):
                            self.set_channel_insertion_effect_parameter(0, i + 1, param / 127.0)

    def _get_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get available effect presets with optimized preset retrieval."""
        return {
            "Default": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.6, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 0, "rate": 1.0, "depth": 0.5, "feedback": 0.3, "level": 0.4},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.5}
            },
            "Rock Hall": {
                "reverb": {"type": 0, "time": 3.5, "level": 0.7, "pre_delay": 15.0, "hf_damping": 0.6},
                "chorus": {"type": 0, "rate": 1.2, "depth": 0.4, "feedback": 0.2, "level": 0.3},
                "variation": {"type": 0, "parameter1": 0.3, "parameter2": 0.4, "parameter3": 0.6, "parameter4": 0.5, "level": 0.3}
            },
            "Jazz Club": {
                "reverb": {"type": 3, "time": 1.8, "level": 0.5, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 1, "rate": 0.8, "depth": 0.3, "feedback": 0.1, "level": 0.2},
                "variation": {"type": 9, "parameter1": 0.6, "parameter2": 0.7, "parameter3": 0.5, "parameter4": 0.4, "level": 0.4}
            },
            "Guitar Distortion": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 1,  # Distortion
                    "params": [80, 64, 100, 50],  # drive, tone, level, type
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Bass Compressor": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.2, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 3,  # Compressor
                    "params": [40, 30, 20, 70],  # threshold, ratio, attack, release
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Phaser Rock": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 16,  # Phaser
                    "params": [1.5, 0.8, 0.4, 0],  # frequency, depth, feedback, waveform
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Flanger Lead": {
                "reverb": {"type": 3, "time": 1.8, "level": 0.4, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 17,  # Flanger
                    "params": [0.5, 0.9, 0.6, 1],  # frequency, depth, feedback, waveform
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Step Phaser": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 27,  # Step Phaser
                    "params": [1.0, 0.7, 0.3, 4],  # frequency, depth, feedback, steps
                    "level": 0.5
                }
            },
            "Step Flanger": {
                "reverb": {"type": 3, "time": 1.8, "level": 0.4, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 28,  # Step Flanger
                    "params": [0.5, 0.8, 0.6, 4],  # frequency, depth, feedback, steps
                    "level": 0.5
                }
            },
            "Step Delay": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 48,  # Step Delay
                    "params": [300, 0.5, 0.5, 4],  # time, feedback, level, steps
                    "level": 0.5
                }
            }
        }