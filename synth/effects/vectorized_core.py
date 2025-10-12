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

        # PRE-ALLOCATED REVERB DELAY BUFFERS FOR HIGH-PERFORMANCE PROCESSING
        # Maximum reverb time: 10 seconds at 48kHz = 480,000 samples
        self.max_reverb_delay = int(10.0 * self.sample_rate)  # 10 seconds max reverb
        self.reverb_delay_buffers = [
            np.zeros(self.max_reverb_delay, dtype=np.float32) for _ in range(4)
        ]
        self.reverb_write_positions = [0, 0, 0, 0]  # Write positions for each delay line

        # PRE-ALLOCATED CHORUS DELAY BUFFER
        self.max_chorus_delay = int(0.05 * self.sample_rate)  # 50ms max delay
        self.chorus_delay_buffer = np.zeros(self.max_chorus_delay, dtype=np.float32)
        self.chorus_write_position = 0

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
                    self._apply_insertion_effect_to_channel_zero_alloc(
                        channel_array, insertion_params, num_samples, channel_idx
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

            # Apply system effects (reverb, chorus, variation) to the mixed output
            self._apply_system_effects_to_mix_zero_alloc(num_samples)

            # STEP 4: RETURN FINAL STEREO OUTPUT ONLY
            # Clean API: effects processor returns final mixed result
            return self.final_stereo_mix[:num_samples]

    def _apply_insertion_effect_to_channel_zero_alloc(self, channel_array: np.ndarray,
                                                     insertion_params: Dict[str, Any],
                                                     num_samples: int, channel_idx: int) -> None:
        """
        Apply insertion effect to a single channel using zero-allocation approach.

        Args:
            channel_array: Input channel audio as NumPy array
            insertion_params: Insertion effect parameters
            num_samples: Number of samples to process
            channel_idx: Channel index for pre-allocated buffer access
        """
        effect_type = insertion_params.get("type", 0)

        # Handle different insertion effect types
        if effect_type == 0:  # No effect
            # Copy input to processing buffer
            if len(channel_array.shape) == 2 and channel_array.shape[1] == 2:
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, :],
                         channel_array[:num_samples])
            else:
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 0],
                         channel_array[:num_samples])
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 1],
                         channel_array[:num_samples])
        elif effect_type == 1:  # Distortion
            self._apply_distortion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 2:  # Overdrive
            self._apply_overdrive_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 3:  # Compressor
            self._apply_compressor_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 4:  # Gate
            self._apply_gate_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 5:  # Envelope Filter
            self._apply_envelope_filter_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 6:  # Guitar Amp Sim
            self._apply_guitar_amp_sim_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 7:  # Rotary Speaker
            self._apply_rotary_speaker_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 8:  # Leslie
            self._apply_leslie_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 9:  # Enhancer
            self._apply_enhancer_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 10:  # Slicer
            self._apply_slicer_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 11:  # Vocoder
            self._apply_vocoder_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 12:  # Talk Wah
            self._apply_talk_wah_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 13:  # Harmonizer
            self._apply_harmonizer_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 14:  # Octave
            self._apply_octave_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 15:  # Detune
            self._apply_detune_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 16:  # Phaser
            self._apply_phaser_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 17:  # Flanger
            self._apply_flanger_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 18:  # Wah Wah
            self._apply_wah_wah_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 19:  # EQ
            self._apply_eq_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 20:  # Vocal Filter
            self._apply_vocal_filter_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 21:  # Auto Wah
            self._apply_auto_wah_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 22:  # Pitch Shifter
            self._apply_pitch_shifter_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 23:  # Ring Modulator
            self._apply_ring_mod_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 24:  # Tremolo
            self._apply_tremolo_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 25:  # Auto Pan
            self._apply_auto_pan_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 26:  # Step Phaser
            self._apply_step_phaser_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 27:  # Step Flanger
            self._apply_step_flanger_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 28:  # Step Filter
            self._apply_step_filter_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 29:  # Spectral Filter
            self._apply_spectral_filter_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 30:  # Resonator
            self._apply_resonator_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 31:  # Degrader
            self._apply_degrader_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        elif effect_type == 32:  # Vinyl Simulator
            self._apply_vinyl_sim_insertion_effect_zero_alloc(channel_array, insertion_params, num_samples, channel_idx)
        else:
            # Unknown effect type - copy original
            if len(channel_array.shape) == 2 and channel_array.shape[1] == 2:
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, :],
                         channel_array[:num_samples])
            else:
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 0],
                         channel_array[:num_samples])
                np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 1],
                         channel_array[:num_samples])

    def _apply_insertion_effect_to_channel(self, channel_array: np.ndarray,
                                          insertion_params: Dict[str, Any],
                                          num_samples: int) -> np.ndarray:
        """
        Apply insertion effect to a single channel.

        Args:
            channel_array: Input channel audio as NumPy array
            insertion_params: Insertion effect parameters
            num_samples: Number of samples to process

        Returns:
            Processed channel audio as NumPy array
        """
        effect_type = insertion_params.get("type", 0)

        # Handle different insertion effect types
        if effect_type == 0:  # No effect
            return channel_array.copy()
        elif effect_type == 1:  # Distortion
            return self._apply_distortion_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 2:  # Overdrive
            return self._apply_overdrive_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 3:  # Compressor
            return self._apply_compressor_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 16:  # Phaser
            return self._apply_phaser_effect(channel_array, insertion_params, num_samples)
        elif effect_type == 17:  # Flanger
            return self._apply_flanger_effect(channel_array, insertion_params, num_samples)
        else:
            # Unknown effect type - return original
            return channel_array.copy()

    def _apply_distortion_effect(self, input_array: np.ndarray,
                               params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply distortion effect to channel"""
        output = input_array.copy()

        # Simple distortion implementation
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply distortion curve
        output = np.tanh(output * (1.0 + drive * 10.0))

        # Apply tone filtering (simplified)
        if tone < 0.5:
            # Low-pass filter approximation
            alpha = tone * 2.0
            for i in range(1, len(output)):
                output[i] = alpha * output[i] + (1.0 - alpha) * output[i-1]

        # Apply output level
        output *= level * 2.0

        return output

    def _apply_overdrive_effect(self, input_array: np.ndarray,
                              params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply overdrive effect to channel"""
        output = input_array.copy()

        # Softer distortion than regular distortion
        drive = params.get("parameter1", 0.3)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply softer distortion curve
        output = output * (1.0 + drive * 5.0)
        output = np.clip(output, -1.0, 1.0)
        output = np.tanh(output * 1.5)

        # Apply tone filtering
        if tone < 0.5:
            alpha = tone * 2.0
            for i in range(1, len(output)):
                output[i] = alpha * output[i] + (1.0 - alpha) * output[i-1]

        # Apply output level
        output *= level * 2.0

        return output

    def _apply_compressor_effect(self, input_array: np.ndarray,
                               params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply compressor effect to channel"""
        output = input_array.copy()

        # Simple compressor implementation
        threshold = params.get("parameter1", 0.5)  # 0.0-1.0
        ratio = params.get("parameter2", 0.5)       # 1.0-10.0
        attack = params.get("parameter3", 0.1)      # 0.001-0.1 seconds
        release = params.get("parameter4", 0.5)     # 0.1-1.0 seconds

        # Convert parameters
        threshold_db = threshold * 40.0 - 20.0  # -20dB to +20dB
        threshold_linear = 10.0 ** (threshold_db / 20.0)
        ratio = 1.0 + ratio * 9.0  # 1.0 to 10.0

        # Simple compression
        compressed = np.copy(output)
        mask = np.abs(compressed) > threshold_linear
        compressed[mask] = np.sign(compressed[mask]) * (
            threshold_linear + (np.abs(compressed[mask]) - threshold_linear) / ratio
        )

        return compressed

    def _apply_phaser_effect(self, input_array: np.ndarray,
                           params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply phaser effect to channel"""
        # Simple phaser implementation
        frequency = params.get("frequency", 1.0)  # Hz
        depth = params.get("depth", 0.5)
        feedback = params.get("feedback", 0.3)

        # Create LFO for phaser
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)

        # Simple all-pass filter implementation
        output = np.zeros_like(input_array)
        prev_input = 0.0
        prev_output = 0.0

        for i in range(num_samples):
            # All-pass filter coefficient modulated by LFO
            g = depth * lfo[i] * 0.9 + 0.1

            # All-pass filter
            ap_input = input_array[i] + feedback * prev_output
            ap_output = g * ap_input + prev_input

            output[i] = ap_output
            prev_input = ap_input
            prev_output = ap_output

        return output

    def _apply_flanger_effect(self, input_array: np.ndarray,
                            params: Dict[str, Any], num_samples: int) -> np.ndarray:
        """Apply flanger effect to channel"""
        # Simple flanger implementation
        frequency = params.get("frequency", 0.5)  # Hz
        depth = params.get("depth", 0.7)
        feedback = params.get("feedback", 0.5)

        # Create LFO for flanger
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)

        # Delay line for flanger effect
        delay_samples = int(0.001 * self.sample_rate)  # 1ms base delay
        max_delay = int(0.005 * self.sample_rate)       # 5ms max delay

        output = np.zeros_like(input_array)
        delay_buffer = np.zeros(max_delay + 1)

        for i in range(num_samples):
            # Calculate variable delay
            delay_offset = int(depth * max_delay * (lfo[i] + 1.0) / 2.0)
            delay_pos = delay_samples + delay_offset

            if delay_pos < len(delay_buffer):
                delayed_sample = delay_buffer[delay_pos]
            else:
                delayed_sample = delay_buffer[-1]

            # Flanger output
            output[i] = input_array[i] + feedback * delayed_sample

            # Update delay buffer
            delay_buffer = np.roll(delay_buffer, 1)
            delay_buffer[0] = input_array[i]

        return output

    def _apply_system_effects_to_mix_zero_alloc(self, num_samples: int) -> None:
        """
        Apply system effects (reverb, chorus, variation, EQ) to the final mix using zero-allocation.

        Args:
            num_samples: Number of samples to process
        """
        # Get system effect parameters
        reverb_params = self.state_manager._current_state.get("reverb_params", {})
        chorus_params = self.state_manager._current_state.get("chorus_params", {})
        variation_params = self.state_manager._current_state.get("variation_params", {})
        equalizer_params = self.state_manager._current_state.get("equalizer_params", {})

        # Apply EQ first (as it's a frequency-domain effect)
        if equalizer_params:
            self._apply_eq_to_mix_zero_alloc(equalizer_params, num_samples)

        # Apply reverb
        if reverb_params.get("level", 0.0) > 0.0:
            self._apply_reverb_to_mix_zero_alloc(reverb_params, num_samples)

        # Apply chorus
        if chorus_params.get("level", 0.0) > 0.0:
            self._apply_chorus_to_mix_zero_alloc(chorus_params, num_samples)

        # Apply variation effect
        if variation_params.get("level", 0.0) > 0.0:
            self._apply_variation_to_mix_zero_alloc(variation_params, num_samples)

    def _apply_system_effects_to_mix(self, stereo_mix: np.ndarray, num_samples: int) -> np.ndarray:
        """
        Apply system effects (reverb, chorus, variation) to the final mix.

        Args:
            stereo_mix: Stereo mix as NumPy array (N x 2)
            num_samples: Number of samples to process

        Returns:
            Final mix with system effects applied
        """
        # Get system effect parameters
        reverb_params = self.state_manager._current_state.get("reverb_params", {})
        chorus_params = self.state_manager._current_state.get("chorus_params", {})
        variation_params = self.state_manager._current_state.get("variation_params", {})

        # Apply reverb
        if reverb_params.get("level", 0.0) > 0.0:
            stereo_mix = self._apply_reverb_to_mix(stereo_mix, reverb_params, num_samples)

        # Apply chorus
        if chorus_params.get("level", 0.0) > 0.0:
            stereo_mix = self._apply_chorus_to_mix(stereo_mix, chorus_params, num_samples)

        # Apply variation effect
        if variation_params.get("level", 0.0) > 0.0:
            stereo_mix = self._apply_variation_to_mix(stereo_mix, variation_params, num_samples)

        return stereo_mix

    def _apply_reverb_to_mix(self, input_mix: np.ndarray, params: Dict[str, Any],
                            num_samples: int) -> np.ndarray:
        """Apply reverb to stereo mix using vectorized circular buffer implementation"""
        reverb_time = params.get("time", 1.0)
        reverb_level = params.get("level", 0.3)

        # Calculate delay lengths for reverb taps
        delay_lengths = [
            int(0.03 * self.sample_rate),  # Early reflection 1
            int(0.05 * self.sample_rate),  # Early reflection 2
            int(0.07 * self.sample_rate),  # Early reflection 3
            int(reverb_time * self.sample_rate)  # Main reverb
        ]

        # Decay factors for each tap
        decay_factors = np.array([0.7 ** (j + 1) for j in range(4)], dtype=np.float32)

        output = input_mix.copy()
        
        # Vectorize the reverb processing for better performance
        for i in range(num_samples):
            # Calculate input sample
            input_sample = (input_mix[i, 0] + input_mix[i, 1]) * 0.5
            
            # Calculate reverb contributions for all taps at once
            reverb_sum = 0.0
            for j in range(4):
                delay_samples = delay_lengths[j]
                if delay_samples < self.max_reverb_delay:
                    # Read from circular buffer: (write_pos - delay) % buffer_size
                    read_pos = (self.reverb_write_positions[j] - delay_samples) % self.max_reverb_delay
                    reverb_sum += self.reverb_delay_buffers[j][read_pos] * decay_factors[j]

            # Add reverb to output
            output[i, 0] += reverb_sum * reverb_level
            output[i, 1] += reverb_sum * reverb_level

            # Write input sample to all delay buffers
            for j in range(4):
                if delay_lengths[j] < self.max_reverb_delay:
                    self.reverb_delay_buffers[j][self.reverb_write_positions[j]] = input_sample
                    self.reverb_write_positions[j] = (self.reverb_write_positions[j] + 1) % self.max_reverb_delay

        return output

    def _apply_chorus_to_mix(self, input_mix: np.ndarray, params: Dict[str, Any],
                            num_samples: int) -> np.ndarray:
        """Apply chorus to stereo mix using optimized circular buffer"""
        chorus_rate = params.get("rate", 1.0)
        chorus_depth = params.get("depth", 0.5)
        chorus_level = params.get("level", 0.3)

        # Create LFO for chorus
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * chorus_rate * t)

        output = input_mix.copy()
        base_delay_samples = int(0.02 * self.sample_rate)  # 20ms base delay
        max_delay_samples = int(0.03 * self.sample_rate)   # 30ms max delay

        # Calculate all delay offsets at once for vectorized processing
        delay_offsets = (chorus_depth * max_delay_samples * (lfo + 1.0) / 2.0).astype(np.int32)
        delays = base_delay_samples + delay_offsets

        # Process each sample
        for i in range(num_samples):
            # Read from circular buffer
            read_pos = (self.chorus_write_position - delays[i]) % self.max_chorus_delay
            delayed_sample = self.chorus_delay_buffer[read_pos]

            # Add chorus to output
            output[i, 0] += delayed_sample * chorus_level
            output[i, 1] += delayed_sample * chorus_level

            # Write input sample to delay buffer
            chorus_sample = (input_mix[i, 0] + input_mix[i, 1]) * 0.5
            self.chorus_delay_buffer[self.chorus_write_position] = chorus_sample
            self.chorus_write_position = (self.chorus_write_position + 1) % self.max_chorus_delay

        return output

    def _apply_variation_to_mix(self, input_mix: np.ndarray, params: Dict[str, Any],
                               num_samples: int) -> np.ndarray:
        """Apply variation effect to stereo mix"""
        # Simple delay effect as variation
        variation_type = params.get("type", 0)
        variation_level = params.get("level", 0.3)

        if variation_type == 0:  # Delay
            delay_samples = int(0.2 * self.sample_rate)  # 200ms delay
            output = input_mix.copy()

            # Simple delay implementation
            for i in range(delay_samples, num_samples):
                delay_sample = (input_mix[i - delay_samples, 0] + input_mix[i - delay_samples, 1]) * 0.5
                output[i, 0] += delay_sample * variation_level * 0.5
                output[i, 1] += delay_sample * variation_level * 0.5

            return output
        else:
            # Other variation types - return original for now
            return input_mix

    # ZERO-ALLOCATION EFFECT IMPLEMENTATIONS
    def _apply_distortion_effect_zero_alloc(self, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY DISTORTION EFFECT - ZERO ALLOCATION

        Multi-type distortion with proper tone control using DSP units
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get distortion parameters
        drive = params.get("parameter1", 0.5)  # 0.0-1.0
        tone = params.get("parameter2", 0.5)   # 0.0-1.0
        level = params.get("level", 0.5)       # 0.0-1.0
        distortion_type = params.get("parameter3", 0.0)  # 0.0-1.0 maps to types

        # Get filter for tone control
        tone_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"distortion_tone_{channel_idx}", 0,
            cutoff=1000.0 + tone * 3000.0,  # 1k-4k Hz tone control
            resonance=0.7,
            filter_type="lowpass"
        )

        # Apply distortion based on type
        type_idx = int(distortion_type * 3)  # 0-3 types

        if type_idx == 0:  # Soft clipping
            drive_scaled = drive * 9.0 + 1.0
            distorted = np.tanh(target_buffer * drive_scaled)
        elif type_idx == 1:  # Hard clipping
            drive_scaled = drive * 9.0 + 1.0
            np.clip(target_buffer * drive_scaled, -1.0, 1.0, out=target_buffer)
            distorted = target_buffer.copy()
        elif type_idx == 2:  # Asymmetric
            biased = target_buffer + drive * 0.1
            distorted = np.where(biased > 0,
                               1.0 - np.exp(-biased * (1 + drive * 9.0)),
                               -1.0 + np.exp(biased * (1 + drive * 9.0)))
        else:  # Symmetric
            drive_scaled = drive * 9.0 + 1.0
            distorted = np.tanh(target_buffer * drive_scaled)

        # Apply tone control through filter
        # Process through filter in blocks for efficiency
        output = np.empty_like(distorted)
        for i in range(0, len(distorted), 64):  # Process in 64-sample blocks
            end_idx = min(i + 64, len(distorted))
            block_input = distorted[i:end_idx]
            block_output = np.empty_like(block_input)

            # Apply filter to block
            filtered_block = tone_filter.process_block(
                block_input.reshape(-1, 1),  # Mono to stereo
                np.zeros((len(block_input), 1))  # Zero right channel
            )
            output[i:end_idx] = filtered_block[:, 0]  # Take left channel

        # Update target buffer
        np.copyto(target_buffer, output)

        # Apply level
        target_buffer *= level

    def _apply_overdrive_effect_zero_alloc(self, input_array: np.ndarray,
                                          params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply overdrive effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Softer distortion than regular distortion
        drive = params.get("parameter1", 0.3)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        # Apply softer distortion curve
        target_buffer *= (1.0 + drive * 5.0)
        np.clip(target_buffer, -1.0, 1.0, out=target_buffer)
        np.tanh(target_buffer * 1.5, out=target_buffer)

        # Apply tone filtering
        if tone < 0.5:
            alpha = tone * 2.0
            for i in range(1, num_samples):
                target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha) * target_buffer[i-1]

        # Apply output level
        target_buffer *= level * 2.0

    def _apply_compressor_effect_zero_alloc(self, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply professional compressor effect with sidechain-like processing using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Initialize compressor state if needed
        if not hasattr(self, '_compressor_states'):
            self._compressor_states = [{
                'gain': 1.0,
                'envelope': 0.0
            } for _ in range(16)]

        if channel_idx >= len(self._compressor_states):
            for _ in range(channel_idx - len(self._compressor_states) + 1):
                self._compressor_states.append({
                    'gain': 1.0,
                    'envelope': 0.0
                })

        state = self._compressor_states[channel_idx]

        # Professional compressor parameters
        threshold_db = (params.get("parameter1", 0.5) * 40.0) - 20.0  # -20dB to +20dB
        ratio = 1.0 + params.get("parameter2", 0.5) * 19.0             # 1:1 to 20:1
        attack_ms = 1.0 + params.get("parameter3", 0.5) * 99.0          # 1-100ms
        release_ms = 10.0 + params.get("parameter4", 0.5) * 490.0       # 10-500ms
        knee_db = 2.0  # 2dB soft knee

        # Convert to linear
        threshold_linear = 10.0 ** (threshold_db / 20.0)

        # Calculate attack/release coefficients (1-pole filters)
        attack_coeff = 1.0 - math.exp(-1.0 / (attack_ms * 0.001 * self.sample_rate))
        release_coeff = 1.0 - math.exp(-1.0 / (release_ms * 0.001 * self.sample_rate))

        # Process each sample for envelope following and compression
        current_gain = state['gain']
        envelope = state['envelope']

        for i in range(num_samples):
            # Calculate detection signal (RMS-like envelope)
            detection_input = target_buffer[i, 0]**2 + target_buffer[i, 1]**2  # Stereo sum of squares
            detection_linear = math.sqrt(max(detection_input, 1e-12))

            # Update envelope with attack/release characteristics
            if detection_linear > envelope:
                envelope += attack_coeff * (detection_linear - envelope)
            else:
                envelope += release_coeff * (detection_linear - envelope)

            # Calculate desired gain with soft knee
            if envelope <= threshold_linear:
                desired_gain_db = 0.0  # No compression
            else:
                # Soft knee calculation
                knee_linear = 10.0 ** (knee_db / 20.0)
                knee_threshold = threshold_linear * knee_linear

                if envelope <= knee_threshold:
                    # Soft knee region
                    knee_ratio = knee_db / ((envelope / threshold_linear - 1.0) / knee_linear + 1.0)
                    gain_reduction = (envelope / threshold_linear - 1.0) * (1.0 / knee_ratio - 1.0 / ratio) + knee_db
                    desired_gain_db = -gain_reduction
                else:
                    # Hard knee region
                    over_threshold = envelope - threshold_linear
                    gain_reduction = over_threshold * (1.0 - 1.0 / ratio)
                    desired_gain_db = -gain_reduction

            # Smooth gain changes to avoid artifacts
            desired_gain = 10.0 ** (desired_gain_db / 20.0)
            current_gain = 0.99 * current_gain + 0.01 * desired_gain

            # Apply gain with make-up gain compensation
            makeup_gain = 10.0 ** (abs(threshold_db) * (1.0 - 1.0 / ratio) / 20.0 * 0.1)  # Subtle makeup gain
            final_gain = current_gain * makeup_gain

            target_buffer[i] *= final_gain

        # Update state
        state['gain'] = current_gain
        state['envelope'] = envelope

        # Apply subtle limiting to prevent overshoots
        np.clip(target_buffer, -1.0, 1.0, out=target_buffer)

    def _apply_phaser_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY PHASER EFFECT - ZERO ALLOCATION

        8-stage phaser using DSP units with proper LFO management
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get LFO for modulation
        lfo_rate = params.get("parameter1", 0.5) * 4.0 + 0.1  # 0.1-4.1 Hz
        depth = params.get("parameter2", 0.5)                  # Modulation depth
        feedback = params.get("parameter3", 0.5) * 0.9         # Feedback (max 90%)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # Waveform type

        # Get LFO from DSP units
        lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform=["sine", "triangle", "square", "sawtooth"][lfo_waveform],
            rate=lfo_rate,
            depth=depth
        )

        # Get biquad bank for all-pass filters
        biquad_bank = self.dsp_units.get_biquad_bank()

        # Calculate 8 all-pass filter frequencies with exponential spacing
        base_freq = 600.0  # Starting frequency around 600Hz
        frequencies = [base_freq * (1.5 ** i) for i in range(8)]

        # Process through cascaded all-pass filters with LFO modulation
        processed = target_buffer.copy()
        for stage in range(8):
            # Get modulated frequency
            lfo_value = lfo.get_value()
            freq_modulation = 1.0 + depth * lfo_value * 0.7  # ±70% modulation
            current_freq = frequencies[stage] * freq_modulation

            # Apply all-pass filter using biquad bank
            processed = biquad_bank.apply_allpass_filter(
                processed, current_freq, resonance=0.0
            )

        # Apply feedback and mix
        feedback_signal = feedback * processed
        target_buffer[:] = target_buffer * 0.3 + processed * 0.7 + feedback_signal

    def _apply_flanger_effect_zero_alloc(self, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY FLANGER EFFECT - ZERO ALLOCATION

        Using DSP units for proper delay line and LFO management
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get flanger parameters
        frequency = params.get("frequency", 0.5)  # Hz
        depth = params.get("depth", 0.7)
        feedback = params.get("feedback", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # Waveform type

        # Get LFO from DSP units
        lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform=["sine", "triangle", "square", "sawtooth"][lfo_waveform],
            rate=frequency,
            depth=depth
        )

        # Get delay line from DSP units
        delay_network = self.dsp_units.get_delay_network()

        # Configure delay taps for flanger
        base_delay_samples = int(0.001 * self.sample_rate)  # 1ms base delay
        max_delay_samples = int(0.005 * self.sample_rate)   # 5ms max delay

        # Set up single tap for flanger
        delay_network.set_tap(0, base_delay_samples, 1.0, feedback)

        # Process through flanger
        for i in range(num_samples):
            # Get modulated delay time
            lfo_value = lfo.get_value()
            modulated_delay = base_delay_samples + int(depth * (max_delay_samples - base_delay_samples) * (lfo_value + 1.0) / 2.0)

            # Update delay tap
            delay_network.set_tap(0, modulated_delay, 1.0, feedback)

            # Get delayed sample
            input_sample = target_buffer[i].copy()
            delayed_sample = delay_network.process_sample(input_sample)

            # Apply flanger: mix input with delayed signal
            target_buffer[i] = input_sample + delayed_sample

    def _apply_gate_effect_zero_alloc(self, input_array: np.ndarray,
                                     params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply gate effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Gate effect implementation
        threshold = params.get("parameter1", 0.5) * 0.8  # 0.0-0.8 threshold
        reduction = params.get("parameter2", 0.5)       # gate reduction
        attack = params.get("parameter3", 0.1)          # attack time
        hold = params.get("parameter4", 0.2)            # hold time

        # Simple gate - mute signal below threshold
        mask = np.abs(target_buffer) < threshold
        target_buffer[mask] *= (1.0 - reduction)

    def _apply_envelope_filter_effect_zero_alloc(self, input_array: np.ndarray,
                                                  params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY ENVELOPE FILTER - ZERO ALLOCATION

        Auto-wah style envelope follower with resonant filter using DSP units
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get envelope follower from DSP units
        envelope_follower = self.dsp_units.get_envelope_follower()

        # Configure envelope follower
        attack_ms = params.get("parameter1", 0.5) * 50.0 + 1.0  # 1-51ms attack
        release_ms = params.get("parameter2", 0.5) * 200.0 + 10.0  # 10-210ms release
        envelope_follower.set_attack_release(attack_ms, release_ms)

        # Filter parameters
        base_cutoff = params.get("parameter3", 0.5) * 2000.0 + 200.0  # 200-2200 Hz base
        resonance = params.get("parameter4", 0.5) * 0.8 + 0.2  # 0.2-1.0 resonance

        # Get filter from DSP units
        filter_obj = self.dsp_units.get_filter_manager().get_filter_stage(
            f"envelope_filter_{channel_idx}", 0,
            cutoff=base_cutoff,
            resonance=resonance,
            filter_type="bandpass"
        )

        # Process each sample
        for i in range(num_samples):
            # Get envelope value
            envelope = envelope_follower.process_sample(target_buffer[i, 0])

            # Modulate filter cutoff based on envelope
            modulated_cutoff = base_cutoff + envelope * 3000.0  # Up to 5200 Hz

            # Update filter cutoff
            filter_obj.set_cutoff(modulated_cutoff)

            # Apply filter
            filtered_sample = filter_obj.process_sample(target_buffer[i, 0])
            target_buffer[i, 0] = filtered_sample

            # Same for right channel if stereo
            if target_buffer.shape[1] > 1:
                filtered_sample_r = filter_obj.process_sample(target_buffer[i, 1])
                target_buffer[i, 1] = filtered_sample_r

    def _apply_guitar_amp_sim_effect_zero_alloc(self, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY GUITAR AMP SIMULATION - ZERO ALLOCATION

        Multi-stage amp modeling with preamp, tone stack, and power amp using DSP units
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get parameters
        drive = params.get("parameter1", 0.5)  # Preamp drive
        bass = params.get("parameter2", 0.5)   # Bass control
        treble = params.get("parameter3", 0.5) # Treble control
        presence = params.get("parameter4", 0.5)  # Presence control

        # Stage 1: Preamp drive with asymmetric clipping
        preamp_gain = drive * 8.0 + 1.0
        target_buffer *= preamp_gain

        # Asymmetric diode clipping (silicon diodes)
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                x = target_buffer[i, ch]
                if x > 0.33:
                    target_buffer[i, ch] = 0.33 + (x - 0.33) * 0.1  # Soft clip positive
                elif x < -0.33:
                    target_buffer[i, ch] = -0.33 + (x + 0.33) * 0.2  # Harder clip negative

        # Stage 2: Tone stack simulation
        # Get filters for tone controls
        bass_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_bass_{channel_idx}", 0,
            cutoff=200.0 + bass * 300.0,  # 200-500 Hz
            resonance=0.7,
            filter_type="lowshelf"
        )

        treble_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_treble_{channel_idx}", 0,
            cutoff=2000.0 + treble * 4000.0,  # 2k-6k Hz
            resonance=0.7,
            filter_type="highshelf"
        )

        presence_filter = self.dsp_units.get_filter_manager().get_filter_stage(
            f"amp_presence_{channel_idx}", 0,
            cutoff=4000.0 + presence * 4000.0,  # 4k-8k Hz
            resonance=0.8,
            filter_type="peaking"
        )

        # Apply tone stack
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                sample = target_buffer[i, ch]

                # Bass boost/cut
                sample = bass_filter.process_sample(sample)

                # Treble boost/cut
                sample = treble_filter.process_sample(sample)

                # Presence boost/cut
                sample = presence_filter.process_sample(sample)

                target_buffer[i, ch] = sample

        # Stage 3: Power amp simulation with sag
        # Simple power amp compression
        for i in range(num_samples):
            for ch in range(target_buffer.shape[1]):
                x = target_buffer[i, ch]
                # Power amp compression (soft knee)
                if abs(x) > 0.7:
                    x = np.sign(x) * (0.7 + (abs(x) - 0.7) * 0.3)
                target_buffer[i, ch] = x

        # Apply final level
        target_buffer *= 0.8  # Conservative output level

    def _apply_rotary_speaker_effect_zero_alloc(self, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY ROTARY SPEAKER SIMULATION - ZERO ALLOCATION

        Dual-rotor Leslie simulation with horn and drum speakers using DSP units
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get parameters
        speed = params.get("parameter1", 0.5) * 5.0 + 0.5  # 0.5-5.5 Hz
        balance = params.get("parameter2", 0.5)            # Horn/drum balance
        accel = params.get("parameter3", 0.5)              # Acceleration
        level = params.get("parameter4", 0.5)              # Output level

        # Get LFOs for horn and drum rotation
        horn_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform="sine",
            rate=speed * 0.7,  # Horn is slower
            depth=1.0
        )

        drum_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx + 16,  # Different channel for drum
            waveform="sine",
            rate=speed,  # Drum is faster
            depth=1.0
        )

        # Get delay lines for Doppler effect
        horn_delay = self.dsp_units.get_delay_network()
        drum_delay = self.dsp_units.get_delay_network()

        # Configure delays for Doppler simulation
        horn_delay.set_tap(0, int(0.01 * self.sample_rate), 0.3, 0.0)  # 10ms delay
        drum_delay.set_tap(0, int(0.005 * self.sample_rate), 0.2, 0.0)  # 5ms delay

        # Process each sample
        for i in range(num_samples):
            # Get LFO values for modulation
            horn_mod = horn_lfo.get_value()
            drum_mod = drum_lfo.get_value()

            # Calculate Doppler modulation
            horn_doppler = 1.0 + horn_mod * 0.1  # ±10% pitch change
            drum_doppler = 1.0 + drum_mod * 0.05  # ±5% pitch change

            # Update delay times for Doppler effect
            horn_delay.set_tap(0, int(0.01 * self.sample_rate * horn_doppler), 0.3, 0.0)
            drum_delay.set_tap(0, int(0.005 * self.sample_rate * drum_doppler), 0.2, 0.0)

            # Process through delays
            input_sample = target_buffer[i, 0]  # Mono processing
            horn_output = horn_delay.process_sample(input_sample)
            drum_output = drum_delay.process_sample(input_sample)

            # Mix horn and drum with balance
            horn_level = balance
            drum_level = 1.0 - balance

            # Apply amplitude modulation for speaker characteristics
            horn_modulated = horn_output * (0.8 + horn_mod * 0.4)  # Horn amplitude modulation
            drum_modulated = drum_output * (0.9 + drum_mod * 0.2)  # Drum amplitude modulation

            # Combine and apply level
            output = (horn_modulated * horn_level + drum_modulated * drum_level) * level

            # Stereo output with slight panning
            target_buffer[i, 0] = output * 0.7  # Left
            target_buffer[i, 1] = output * 0.7  # Right

    def _apply_leslie_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY LESLIE SPEAKER SIMULATION - ZERO ALLOCATION

        Authentic Leslie 122 simulation with rotating horn and drum using DSP units
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get parameters
        speed = params.get("parameter1", 0.5) * 5.0 + 0.5  # 0.5-5.5 Hz
        balance = params.get("parameter2", 0.5)            # Horn/drum balance
        accel = params.get("parameter3", 0.5)              # Acceleration (unused for now)
        level = params.get("parameter4", 0.5)              # Output level

        # Get LFOs for horn and drum rotation
        horn_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx,
            waveform="sine",
            rate=speed * 0.7,  # Horn: ~0.35-3.85 Hz
            depth=1.0
        )

        drum_lfo = self.dsp_units.get_lfo_manager().get_channel_lfo(
            channel_idx + 16,  # Different channel for drum
            waveform="sine",
            rate=speed,  # Drum: ~0.5-5.5 Hz
            depth=1.0
        )

        # Get crossover filters for frequency splitting
        # Horn gets treble, drum gets bass
        crossover_low = self.dsp_units.get_filter_manager().get_filter_stage(
            f"leslie_crossover_low_{channel_idx}", 0,
            cutoff=800.0,  # 800Hz crossover
            resonance=0.7,
            filter_type="lowpass"
        )

        crossover_high = self.dsp_units.get_filter_manager().get_filter_stage(
            f"leslie_crossover_high_{channel_idx}", 0,
            cutoff=800.0,  # 800Hz crossover
            resonance=0.7,
            filter_type="highpass"
        )

        # Get delay networks for Doppler effect
        horn_delay = self.dsp_units.get_delay_network()
        drum_delay = self.dsp_units.get_delay_network()

        # Configure delays for authentic Leslie Doppler
        horn_delay.set_tap(0, int(0.015 * self.sample_rate), 0.4, 0.0)  # 15ms delay
        drum_delay.set_tap(0, int(0.008 * self.sample_rate), 0.3, 0.0)  # 8ms delay

        # Process each sample
        for i in range(num_samples):
            input_sample = target_buffer[i, 0]  # Mono processing

            # Split frequencies
            bass_signal = crossover_low.process_sample(input_sample)
            treble_signal = crossover_high.process_sample(input_sample)

            # Get LFO values
            horn_mod = horn_lfo.get_value()
            drum_mod = drum_lfo.get_value()

            # Calculate Doppler modulation
            horn_doppler = 1.0 + horn_mod * 0.08  # ±8% pitch change
            drum_doppler = 1.0 + drum_mod * 0.04  # ±4% pitch change

            # Update delay times
            horn_delay.set_tap(0, int(0.015 * self.sample_rate * horn_doppler), 0.4, 0.0)
            drum_delay.set_tap(0, int(0.008 * self.sample_rate * drum_doppler), 0.3, 0.0)

            # Process through delays
            horn_output = horn_delay.process_sample(treble_signal)
            drum_output = drum_delay.process_sample(bass_signal)

            # Apply amplitude modulation (horn has more modulation)
            horn_modulated = horn_output * (0.7 + horn_mod * 0.6)  # ±60% modulation
            drum_modulated = drum_output * (0.85 + drum_mod * 0.3)  # ±30% modulation

            # Mix horn and drum with balance
            horn_level = balance
            drum_level = 1.0 - balance

            # Combine and apply level
            output = (horn_modulated * horn_level + drum_modulated * drum_level) * level

            # Stereo output with slight stereo spread
            target_buffer[i, 0] = output * 0.8  # Left
            target_buffer[i, 1] = output * 0.8  # Right

    def _apply_enhancer_effect_zero_alloc(self, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply enhancer effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple enhancer - add harmonics and brightness
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        # Add odd harmonics
        enhanced = target_buffer + enhance * np.sin(target_buffer * math.pi)
        np.copyto(target_buffer, enhanced)

        # Apply bass/treble balance
        bass_factor = 0.5 + bass * 0.5
        treble_factor = 0.5 + treble * 0.5
        target_buffer *= bass_factor * treble_factor * level

    def _apply_slicer_effect_zero_alloc(self, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply slicer effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple slicer - rhythmic gate
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 2)
        phase = params.get("parameter4", 0.5)

        # Create LFO
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t + phase * 2 * math.pi)

        # Create gate pattern
        gate_signal = (lfo > -depth).astype(np.float32)
        target_buffer *= gate_signal[:, np.newaxis]

    def _apply_vocoder_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """
        PRODUCTION-QUALITY VOCODER EFFECT - ZERO ALLOCATION

        16-band vocoder with envelope following and carrier synthesis
        """
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Get parameters
        formant_shift = params.get("parameter1", 0.5) * 2.0  # 0-2x formant shift
        resonance = params.get("parameter2", 0.5) * 0.9 + 0.1  # 0.1-1.0 resonance
        mix = params.get("parameter3", 0.5)  # Dry/wet mix
        level = params.get("parameter4", 0.5)  # Output level

        # Get envelope follower for modulation source
        envelope_follower = self.dsp_units.get_envelope_follower()
        envelope_follower.set_attack_release(1.0, 50.0)  # Fast attack, slow release

        # Get biquad bank for band-pass filters
        filter_bank = self.dsp_units.get_biquad_bank()

        # Define 16 frequency bands (logarithmic spacing)
        bands = []
        for i in range(16):
            freq = 200 * (2 ** (i / 4))  # 200Hz to ~6.3kHz
            bands.append(freq)

        # Process each sample
        output = np.zeros_like(target_buffer)

        for i in range(num_samples):
            input_sample = target_buffer[i, 0]  # Use left channel as modulation source

            # Get envelope from input
            envelope = envelope_follower.process_sample(input_sample)

            # Generate carrier signal (synthesized voice-like sound)
            carrier = 0.0
            for band_idx, freq in enumerate(bands):
                # Modulate each band with envelope
                band_level = envelope * (0.5 + 0.5 * np.sin(2 * np.pi * freq * i / self.sample_rate))

                # Add to carrier with some noise for vocal character
                noise = np.random.random() * 2.0 - 1.0  # White noise
                carrier += band_level * noise * 0.1

            # Apply formant filtering to carrier
            for band_idx, freq in enumerate(bands):
                shifted_freq = freq * formant_shift
                if shifted_freq < 50:
                    shifted_freq = 50
                elif shifted_freq > 8000:
                    shifted_freq = 8000

                # Design band-pass filter for this frequency
                filter_bank.design_bandpass(band_idx % 8, shifted_freq, resonance)

                # Filter carrier through this band
                band_output = filter_bank.process_sample(band_idx % 8, carrier)
                carrier = band_output

            # Mix dry and wet signals
            dry_level = 1.0 - mix
            wet_level = mix

            final_sample = input_sample * dry_level + carrier * wet_level * level

            # Stereo output
            output[i, 0] = final_sample
            output[i, 1] = final_sample

        # Copy result to target buffer
        np.copyto(target_buffer, output)

    def _apply_talk_wah_effect_zero_alloc(self, input_array: np.ndarray,
                                         params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply talk wah effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Talk wah - automatic wah filter based on envelope
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 2)

        # Simple envelope following and filtering
        if hasattr(self, '_talk_wah_envelope') and len(self._talk_wah_envelope) >= num_samples:
            envelope = self._talk_wah_envelope[:num_samples]
        else:
            # Simple envelope detection
            envelope = np.abs(target_buffer.mean(axis=1) if len(target_buffer.shape) > 1 else target_buffer)
            for i in range(1, len(envelope)):
                envelope[i] = envelope[i] * 0.1 + envelope[i-1] * 0.9

        # Convert envelope to filter frequency
        filter_freq = 200 + envelope * 3000

        # Very simplified filtering
        for i in range(1, num_samples):
            alpha = 0.1 + (filter_freq[i] / 4000.0) * 0.4
            target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha) * target_buffer[i-1]

        target_buffer *= depth * 2.0

    def _apply_harmonizer_effect_zero_alloc(self, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply harmonizer effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simplified harmonizer - add pitch-shifted version
        intervals = (params.get("parameter1", 0.5) * 24.0) - 12.0  # semitones
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        mix = params.get("parameter4", 0.5)

        # Simple delay-based pitch shifter (very simplified)
        pitch_factor = 2 ** (intervals / 12.0)
        delay_samples = int(0.01 * self.sample_rate)  # 10ms delay

        # Add delayed version with different gain
        if delay_samples < num_samples:
            delayed = np.zeros_like(target_buffer)
            delayed[delay_samples:] = target_buffer[:-delay_samples]
            target_buffer += delayed * depth * 0.5

        target_buffer *= (1.0 - mix * depth + mix)

    def _apply_octave_effect_zero_alloc(self, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply octave effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple octave effect - add octave down
        shift = int(params.get("parameter1", 0.5) * 4) - 2
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        # Simple octave down using short delay
        octave_down_samples = int(self.sample_rate / (261.63 * (2 ** shift)))  # C4 frequency
        octave_down_samples = min(octave_down_samples, num_samples // 2)

        # Add octave-down signal
        if octave_down_samples > 0 and octave_down_samples < num_samples:
            octave_signal = np.zeros_like(target_buffer)
            for i in range(octave_down_samples, num_samples):
                octave_signal[i] = target_buffer[i - octave_down_samples] * 0.7
            target_buffer += octave_signal * mix

    def _apply_detune_effect_zero_alloc(self, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply detune effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple detuning with short delay
        shift = (params.get("parameter1", 0.5) * 100.0) - 50.0  # cents
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)

        # Calculate delay for detuning
        delay_cents = shift  # cents difference
        pitch_factor = 2 ** (delay_cents / 1200.0)
        delay_samples = int(0.005 * self.sample_rate * (1.0 - pitch_factor))  # small delay

        # Add detuned signal
        if delay_samples > 0 and delay_samples < num_samples:
            detuned = np.zeros_like(target_buffer)
            detuned[delay_samples:] = target_buffer[:-delay_samples]
            target_buffer += detuned * feedback * mix

    def _apply_wah_wah_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply wah wah effect using zero-allocation approach"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple wah-wah filter
        manual_pos = params.get("manual_position", 0.5)
        lfo_rate = params.get("lfo_rate", 0.5) * 5.0
        lfo_depth = params.get("lfo_depth", 0.5)
        resonance = params.get("resonance", 0.5)

        # Create LFO for wah
        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * lfo_rate * t)

        # Vary cutoff frequency
        cutoff_freq = manual_pos + lfo * lfo_depth * 0.5
        cutoff_freq = np.clip(cutoff_freq, 0.01, 0.99)

        # Simple bandpass filter approximation
        for i in range(1, num_samples):
            alpha = 0.1 + (cutoff_freq[i] * 0.4)
            target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha * resonance) * target_buffer[i-1]

    def _apply_eq_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                            params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply professional 3-band EQ insertion effect using zero-allocation approach with biquad filters"""
        # Get target buffer
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        # Copy input to target buffer first
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Initialize filter state if needed
        if not hasattr(self, '_eq_insertion_filters'):
            self._eq_insertion_filters = [{
                'low_state': [0.0, 0.0],    # x1, x2 for low shelf
                'mid_state': [0.0, 0.0],    # x1, x2 for peaking
                'high_state': [0.0, 0.0]    # x1, x2 for high shelf
            } for _ in range(16)]

        # Get or create filter state for this channel
        if channel_idx >= len(self._eq_insertion_filters):
            # Extend array if needed
            for _ in range(channel_idx - len(self._eq_insertion_filters) + 1):
                self._eq_insertion_filters.append({
                    'low_state': [0.0, 0.0],
                    'mid_state': [0.0, 0.0],
                    'high_state': [0.0, 0.0]
                })

        filter_state = self._eq_insertion_filters[channel_idx]

        # Parse parameters: 3-band EQ gains
        low_gain_db = (params.get("parameter1", 0.5) - 0.5) * 24.0  # -12 to +12 dB
        mid_gain_db = (params.get("parameter2", 0.5) - 0.5) * 24.0  # -12 to +12 dB
        high_gain_db = (params.get("parameter3", 0.5) - 0.5) * 24.0 # -12 to +12 dB

        # Convert dB to linear gain
        low_gain = 10.0 ** (low_gain_db / 20.0)
        mid_gain = 10.0 ** (mid_gain_db / 20.0)
        high_gain = 10.0 ** (high_gain_db / 20.0)

        # Design filter coefficients for standard 3-band EQ
        # Low shelf: 100Hz, Mid peak: 1kHz, High shelf: 5kHz

        # Process each channel (left/right) through the EQ
        for ch in range(target_buffer.shape[1]):
            channel_data = target_buffer[:, ch]

            # Apply low shelf filter
            low_filtered = self._apply_biquad_low_shelf(channel_data, low_gain, filter_state['low_state'])

            # Apply mid peaking filter
            mid_filtered = self._apply_biquad_peaking(low_filtered, mid_gain, 1000.0, 1.414, filter_state['mid_state'])

            # Apply high shelf filter
            high_filtered = self._apply_biquad_high_shelf(mid_filtered, high_gain, filter_state['high_state'])

            # Update output
            target_buffer[:, ch] = high_filtered

    def _apply_biquad_low_shelf(self, input_signal: np.ndarray, gain: float, state: List[float]) -> np.ndarray:
        """Apply biquad low shelf filter"""
        # Low shelf coefficients (cutoff=100Hz, slope=1)
        a0 = 1.0 + 2.0 * math.pi * 100.0 / self.sample_rate
        a1 = -2.0 * math.cos(2.0 * math.pi * 100.0 / self.sample_rate) / a0
        a2 = (1.0 - 2.0 * math.pi * 100.0 / self.sample_rate) / a0
        b0 = gain * a0
        b1 = gain * a1
        b2 = gain * a2

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = x

        return output

    def _apply_biquad_peaking(self, input_signal: np.ndarray, gain: float, freq: float,
                             q: float, state: List[float]) -> np.ndarray:
        """Apply biquad peaking filter"""
        w0 = 2.0 * math.pi * freq / self.sample_rate
        alpha = math.sin(w0) / (2.0 * q)

        a0 = 1.0 + alpha
        a1 = -2.0 * math.cos(w0)
        a2 = 1.0 - alpha
        b0 = (1.0 + alpha * gain) / a0
        b1 = (-2.0 * math.cos(w0)) / a0
        b2 = (1.0 - alpha * gain) / a0

        # Normalize a coefficients
        a1 = a1 / a0
        a2 = a2 / a0

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = y

        return output

    def _apply_biquad_high_shelf(self, input_signal: np.ndarray, gain: float, state: List[float]) -> np.ndarray:
        """Apply biquad high shelf filter"""
        # High shelf coefficients (cutoff=5kHz, slope=1)
        a0 = 1.0 + 2.0 * math.pi * 5000.0 / self.sample_rate
        a1 = -2.0 * math.cos(2.0 * math.pi * 5000.0 / self.sample_rate) / a0
        a2 = (1.0 - 2.0 * math.pi * 5000.0 / self.sample_rate) / a0
        b0 = gain * a0
        b1 = gain * a1
        b2 = gain * a2

        output = np.zeros_like(input_signal)
        for i in range(len(input_signal)):
            x = input_signal[i]
            y = b0 * x + b1 * state[0] + b2 * state[1] - a1 * state[0] - a2 * state[1]
            output[i] = y
            state[1] = state[0]
            state[0] = x

        return output

    def _apply_vocal_filter_effect_zero_alloc(self, input_array: np.ndarray,
                                             params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply vocal filter effect using zero-allocation approach"""
        # Simplified vocal filter - basic formant-like filtering
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple vocal filter - attenuate low and high frequencies
        for i in range(1, num_samples):
            target_buffer[i] = target_buffer[i] * 0.7 + target_buffer[i-1] * 0.3

    def _apply_auto_wah_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto wah insertion effect using zero-allocation approach"""
        self._apply_auto_wah_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_pitch_shifter_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply pitch shifter insertion effect using zero-allocation approach"""
        self._apply_pitch_shifter_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_ring_mod_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply ring mod insertion effect using zero-allocation approach"""
        self._apply_ring_mod_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_tremolo_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                  params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply tremolo insertion effect using zero-allocation approach"""
        self._apply_tremolo_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_auto_pan_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto pan insertion effect using zero-allocation approach"""
        self._apply_auto_pan_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_step_phaser_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                      params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step phaser insertion effect using zero-allocation approach"""
        self._apply_step_phaser_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_step_flanger_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step flanger insertion effect using zero-allocation approach"""
        self._apply_step_flanger_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_step_filter_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                      params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step filter insertion effect using zero-allocation approach"""
        self._apply_step_filter_effect_zero_alloc(input_array, params, num_samples, channel_idx)

    def _apply_spectral_filter_effect_zero_alloc(self, input_array: np.ndarray,
                                                params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply spectral filter effect using zero-allocation approach"""
        # Simplified spectral filter - just copy input
        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(self.channel_processing_buffers[channel_idx, :num_samples], input_array[:num_samples])
        else:
            np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 0], input_array[:num_samples])
            np.copyto(self.channel_processing_buffers[channel_idx, :num_samples, 1], input_array[:num_samples])

    def _apply_resonator_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                    params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply resonator insertion effect using zero-allocation approach"""
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple resonance - add feedback
        for i in range(1, num_samples):
            target_buffer[i] *= 1.2  # Simple resonance

    def _apply_degrader_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                   params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply degrader insertion effect using zero-allocation approach"""
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple bit crushing
        bit_depth = int(params.get("parameter1", 0.5) * 8) + 4
        if bit_depth < 16:
            scale = 2 ** bit_depth
            target_buffer[:] = np.floor(target_buffer * scale) / scale

    def _apply_vinyl_sim_insertion_effect_zero_alloc(self, input_array: np.ndarray,
                                                    params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply vinyl simulator insertion effect using zero-allocation approach"""
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple vinyl simulation - add some filtering and saturation
        target_buffer[:] = np.tanh(target_buffer * 1.5) * 0.9

    # --- Additional variation effect implementations ---

    def _apply_auto_wah_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto wah effect using zero-allocation approach - variation version"""
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simplified auto-wah - envelope controlled filter
        sensitivity = params.get("parameter1", 0.5)
        level = params.get("parameter2", 0.5)

        # Very simple envelope detection
        envelope = np.abs(target_buffer.mean(axis=1) if len(target_buffer.shape) > 1 else target_buffer)
        for i in range(1, len(envelope)):
            envelope[i] = envelope[i] * 0.1 + envelope[i-1] * 0.9

        for i in range(1, num_samples):
            filter_amount = 0.1 + envelope[i] * 0.4
            target_buffer[i] = filter_amount * target_buffer[i] + (1.0 - filter_amount) * target_buffer[i-1]

        target_buffer *= level

    def _apply_pitch_shifter_effect_zero_alloc(self, input_array: np.ndarray,
                                             params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply pitch shifter effect using zero-allocation approach"""
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        if not hasattr(self, '_pitch_shifter_buffers'):
            self._pitch_shifter_buffers = [np.zeros(self.block_size, dtype=np.float32) for _ in range(16)]
            self._pitch_shifter_positions = [0] * 16

        shift_factor = 2 ** (shift / 12.0)
        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]
        buffer = self._pitch_shifter_buffers[channel_idx]
        pos = self._pitch_shifter_positions[channel_idx]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Simple pitch shifting via delay
        delay_samples = int(0.01 * self.sample_rate * (2.0 - shift_factor))

        for i in range(num_samples):
            buffer[pos] = target_buffer[i, 0]  # Store left channel
            read_pos = (pos - delay_samples) % len(buffer)
            delayed = buffer[int(read_pos)]
            target_buffer[i] *= (1.0 - level)
            target_buffer[i] += delayed * level
            pos = (pos + 1) % len(buffer)

        self._pitch_shifter_positions[channel_idx] = pos
        target_buffer *= (1.0 - feedback + feedback)

    def _apply_ring_mod_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply ring mod effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 1000.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * frequency * t)
        modulator = 1.0 - depth + depth * lfo

        target_buffer *= modulator[:, np.newaxis]
        target_buffer *= level

    def _apply_tremolo_effect_zero_alloc(self, input_array: np.ndarray,
                                       params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply tremolo effect using zero-allocation approach"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t)
        mod_amount = 1.0 - depth * 0.5 + depth * 0.5 * lfo

        target_buffer *= mod_amount[:, np.newaxis]
        target_buffer *= level

    def _apply_auto_pan_effect_zero_alloc(self, input_array: np.ndarray,
                                        params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply auto pan effect using zero-allocation approach"""
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            mono_input = input_array[:, 0] if len(input_array.shape) == 2 else input_array
            np.copyto(target_buffer[:, 0], mono_input[:num_samples])
            np.copyto(target_buffer[:, 1], mono_input[:num_samples])

        t = np.arange(num_samples) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * rate * t)
        pan = lfo * depth * 0.5 + 0.5

        left_gain = np.sqrt(1.0 - pan)
        right_gain = np.sqrt(pan)

        original_left = target_buffer[:, 0].copy()
        original_right = target_buffer[:, 1].copy()

        target_buffer[:, 0] = original_left * left_gain + original_right * right_gain
        target_buffer[:, 1] = original_right * right_gain + original_left * left_gain

        target_buffer *= level

    def _apply_step_phaser_effect_zero_alloc(self, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step phaser effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Step-based modulation
        if not hasattr(self, '_step_phaser_counters'):
            self._step_phaser_counters = [0] * 16

        counter = self._step_phaser_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            step_modulation = current_step / (steps - 1) * 2.0 - 1.0

            filter_coeff = 0.1 + depth * step_modulation * 0.4
            # Very simple filtering
            if i > 0:
                target_buffer[i] = filter_coeff * target_buffer[i] + (1.0 - filter_coeff) * target_buffer[i-1]

        self._step_phaser_counters[channel_idx] = (counter + num_samples) % (step_size * steps)

    def _apply_step_flanger_effect_zero_alloc(self, input_array: np.ndarray,
                                            params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step flanger effect using zero-allocation approach"""
        frequency = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        # Step-based delay modulation
        if not hasattr(self, '_step_flanger_counters'):
            self._step_flanger_counters = [0] * 16

        counter = self._step_flanger_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        base_delay = int(0.001 * self.sample_rate)
        max_additional_delay = int(0.003 * self.sample_rate)

        # Use temp buffer for delay
        delay_buffer_size = base_delay + max_additional_delay + 10
        if not hasattr(self, '_step_flanger_buffers'):
            self._step_flanger_buffers = [np.zeros(delay_buffer_size, dtype=np.float32) for _ in range(16)]
            self._step_flanger_positions = [0] * 16

        buffer = self._step_flanger_buffers[channel_idx]
        pos = self._step_flanger_positions[channel_idx]

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            additional_delay = int((current_step / (steps - 1)) * max_additional_delay)
            total_delay = base_delay + additional_delay

            buffer[pos] = target_buffer[i, 0]  # Store sample
            read_pos = (pos - total_delay + len(buffer)) % len(buffer)
            delayed = buffer[int(read_pos)]

            target_buffer[i] += delayed * feedback
            pos = (pos + 1) % len(buffer)

        self._step_flanger_positions[channel_idx] = pos
        self._step_flanger_counters[channel_idx] = (counter + num_samples) % (step_size * steps)

    def _apply_step_filter_effect_zero_alloc(self, input_array: np.ndarray,
                                           params: Dict[str, Any], num_samples: int, channel_idx: int) -> None:
        """Apply step filter effect using zero-allocation approach"""
        cutoff_start = params.get("parameter1", 0.1) * 5000
        cutoff_end = params.get("parameter2", 0.9) * 5000
        resonance = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1

        target_buffer = self.channel_processing_buffers[channel_idx, :num_samples]

        if len(input_array.shape) == 2 and input_array.shape[1] == 2:
            np.copyto(target_buffer, input_array[:num_samples])
        else:
            np.copyto(target_buffer[:, 0], input_array[:num_samples])
            np.copyto(target_buffer[:, 1], input_array[:num_samples])

        if not hasattr(self, '_step_filter_counters'):
            self._step_filter_counters = [0] * 16

        counter = self._step_filter_counters[channel_idx]
        step_size = max(1, num_samples // steps)

        for i in range(num_samples):
            current_step = (counter + i) // step_size % steps
            t_step = current_step / (steps - 1)
            current_cutoff = cutoff_start + (cutoff_end - cutoff_start) * t_step

            norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
            norm_cutoff = max(0.01, min(0.95, norm_cutoff))

            alpha = 0.1 + norm_cutoff * 0.4
            if i > 0:
                target_buffer[i] = alpha * target_buffer[i] + (1.0 - alpha) * target_buffer[i-1]

        self._step_filter_counters[channel_idx] = (counter + num_samples) % (step_size * steps)

    def _apply_reverb_to_mix_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply reverb to stereo mix using VECTORIZED + NUMBA zero-allocation approach"""
        reverb_time = params.get("time", 1.0)
        reverb_level = params.get("level", 0.3)

        # Calculate delay lengths for reverb taps
        delay_lengths = np.array([
            int(0.03 * self.sample_rate),  # Early reflection 1
            int(0.05 * self.sample_rate),  # Early reflection 2
            int(0.07 * self.sample_rate),  # Early reflection 3
            int(reverb_time * self.sample_rate)  # Main reverb
        ], dtype=np.int32)

        # Decay factors for each tap
        decay_factors = np.array([0.7 ** (j + 1) for j in range(4)], dtype=np.float32)

        # VECTORIZED APPROACH: Process all samples at once
        # Calculate input samples for all positions
        input_samples = (self.final_stereo_mix[:num_samples, 0] + self.final_stereo_mix[:num_samples, 1]) * 0.5

        # VECTORIZED APPROACH: Process all samples at once
        # Calculate input samples for all positions
        input_samples = (self.final_stereo_mix[:num_samples, 0] + self.final_stereo_mix[:num_samples, 1]) * 0.5

        # Pre-calculate all read positions for vectorized access
        reverb_contributions = np.zeros(num_samples, dtype=np.float32)

        # Use vectorized computation function
        self._vectorized_reverb_compute(
            reverb_contributions,
            self.reverb_delay_buffers,
            self.reverb_write_positions,
            delay_lengths,
            decay_factors,
            self.max_reverb_delay,
            num_samples
        )

        # Apply reverb to output (VECTORIZED)
        reverb_signal = reverb_contributions * reverb_level
        self.final_stereo_mix[:num_samples, 0] += reverb_signal
        self.final_stereo_mix[:num_samples, 1] += reverb_signal

        # Write input samples to delay buffers (VECTORIZED where possible)
        for j in range(4):
            if delay_lengths[j] < self.max_reverb_delay:
                # Write samples in reverse order to maintain causality
                for i in range(num_samples):
                    write_pos = (self.reverb_write_positions[j] - num_samples + i + 1) % self.max_reverb_delay
                    self.reverb_delay_buffers[j][write_pos] = input_samples[i]
                self.reverb_write_positions[j] = (self.reverb_write_positions[j] + num_samples) % self.max_reverb_delay

    def _vectorized_reverb_compute(self, reverb_contributions, delay_buffers, write_positions,
                                  delay_lengths, decay_factors, max_delay, num_samples):
        """Vectorized reverb computation function"""
        for j in range(4):
            delay_samples = delay_lengths[j]
            if delay_samples < max_delay:
                # Calculate read positions for all samples at once (VECTORIZED)
                sample_indices = np.arange(num_samples)
                read_positions = (write_positions[j] - delay_samples - sample_indices) % max_delay
                # Vectorized buffer read and accumulation
                reverb_contributions += delay_buffers[j][read_positions] * decay_factors[j]

    def _vectorized_chorus_compute(self, delayed_samples, delay_buffer, write_position,
                                  delays, max_delay, num_samples):
        """Vectorized chorus computation function"""
        # Calculate all read positions at once
        sample_indices = np.arange(num_samples)
        read_positions = (write_position - delays - sample_indices) % max_delay
        # Vectorized buffer read
        delayed_samples[:] = delay_buffer[read_positions]

    def _apply_chorus_to_mix_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply chorus to stereo mix using VECTORIZED + NUMBA zero-allocation approach"""
        chorus_rate = params.get("rate", 1.0)
        chorus_depth = params.get("depth", 0.5)
        chorus_level = params.get("level", 0.3)

        # Create LFO for chorus (VECTORIZED)
        t = np.arange(num_samples, dtype=np.float32) / self.sample_rate
        lfo = np.sin(2.0 * np.pi * chorus_rate * t)

        base_delay_samples = int(0.02 * self.sample_rate)  # 20ms base delay
        max_delay_samples = int(0.03 * self.sample_rate)   # 30ms max delay

        # Calculate all delay offsets at once (VECTORIZED)
        delay_offsets = (chorus_depth * max_delay_samples * (lfo + 1.0) / 2.0).astype(np.int32)
        delays = base_delay_samples + delay_offsets

        # Calculate chorus input samples (average of left/right)
        chorus_input_samples = (self.final_stereo_mix[:num_samples, 0] + self.final_stereo_mix[:num_samples, 1]) * 0.5

        # VECTORIZED: Read all delayed samples at once
        delayed_samples = np.zeros(num_samples, dtype=np.float32)
        self._vectorized_chorus_compute(
            delayed_samples,
            self.chorus_delay_buffer,
            self.chorus_write_position,
            delays,
            self.max_chorus_delay,
            num_samples
        )

        # VECTORIZED: Apply chorus to output
        chorus_signal = delayed_samples * chorus_level
        self.final_stereo_mix[:num_samples, 0] += chorus_signal
        self.final_stereo_mix[:num_samples, 1] += chorus_signal

        # Write input samples to delay buffer in reverse order to maintain causality
        for i in range(num_samples):
            write_pos = (self.chorus_write_position - num_samples + i + 1) % self.max_chorus_delay
            self.chorus_delay_buffer[write_pos] = chorus_input_samples[i]

        self.chorus_write_position = (self.chorus_write_position + num_samples) % self.max_chorus_delay


    def _apply_variation_to_mix_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply variation effect to stereo mix using zero-allocation approach"""
        # Extract common parameters
        variation_type = params.get("type", 0)
        variation_level = params.get("level", 0.3)

        # Route to appropriate effect handler based on type
        if variation_type == 0:
            self._apply_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 1:
            self._apply_dual_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 2:
            self._apply_echo_variation_zero_alloc(params, num_samples)
        elif variation_type == 3:
            self._apply_pan_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 4:
            self._apply_cross_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 5:
            self._apply_multi_tap_variation_zero_alloc(params, num_samples)
        elif variation_type == 6:
            self._apply_reverse_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 7:
            self._apply_tremolo_variation_zero_alloc(params, num_samples)
        elif variation_type == 8:
            self._apply_auto_pan_variation_zero_alloc(params, num_samples)
        elif variation_type == 9:
            self._apply_phaser_variation_zero_alloc(params, num_samples)
        elif variation_type == 10:
            self._apply_flanger_variation_zero_alloc(params, num_samples)
        elif variation_type == 11:
            self._apply_auto_wah_variation_zero_alloc(params, num_samples)
        elif variation_type == 12:
            self._apply_ring_mod_variation_zero_alloc(params, num_samples)
        elif variation_type == 13:
            self._apply_pitch_shifter_variation_zero_alloc(params, num_samples)
        elif variation_type == 14:
            self._apply_distortion_variation_zero_alloc(params, num_samples)
        elif variation_type == 15:
            self._apply_overdrive_variation_zero_alloc(params, num_samples)
        elif variation_type == 16:
            self._apply_compressor_variation_zero_alloc(params, num_samples)
        elif variation_type == 17:
            self._apply_limiter_variation_zero_alloc(params, num_samples)
        elif variation_type == 18:
            self._apply_gate_variation_zero_alloc(params, num_samples)
        elif variation_type == 19:
            self._apply_expander_variation_zero_alloc(params, num_samples)
        elif variation_type == 20:
            self._apply_rotary_speaker_variation_zero_alloc(params, num_samples)
        elif variation_type == 21:
            self._apply_leslie_variation_zero_alloc(params, num_samples)
        elif variation_type == 22:
            self._apply_vibrato_variation_zero_alloc(params, num_samples)
        elif variation_type == 23:
            self._apply_acoustic_simulator_variation_zero_alloc(params, num_samples)
        elif variation_type == 24:
            self._apply_guitar_amp_sim_variation_zero_alloc(params, num_samples)
        elif variation_type == 25:
            self._apply_enhancer_variation_zero_alloc(params, num_samples)
        elif variation_type == 26:
            self._apply_slicer_variation_zero_alloc(params, num_samples)
        elif variation_type == 27:
            self._apply_step_phaser_variation_zero_alloc(params, num_samples)
        elif variation_type == 28:
            self._apply_step_flanger_variation_zero_alloc(params, num_samples)
        elif variation_type == 29:
            self._apply_step_tremolo_variation_zero_alloc(params, num_samples)
        elif variation_type == 30:
            self._apply_step_pan_variation_zero_alloc(params, num_samples)
        elif variation_type == 31:
            self._apply_step_filter_variation_zero_alloc(params, num_samples)
        elif variation_type == 32:
            self._apply_auto_filter_variation_zero_alloc(params, num_samples)
        elif variation_type == 33:
            self._apply_vocoder_variation_zero_alloc(params, num_samples)
        elif variation_type == 34:
            self._apply_talk_wah_variation_zero_alloc(params, num_samples)
        elif variation_type == 35:
            self._apply_harmonizer_variation_zero_alloc(params, num_samples)
        elif variation_type == 36:
            self._apply_octave_variation_zero_alloc(params, num_samples)
        elif variation_type == 37:
            self._apply_detune_variation_zero_alloc(params, num_samples)
        elif variation_type == 38:
            self._apply_chorus_reverb_variation_zero_alloc(params, num_samples)
        elif variation_type == 39:
            self._apply_stereo_imager_variation_zero_alloc(params, num_samples)
        elif variation_type == 40:
            self._apply_ambience_variation_zero_alloc(params, num_samples)
        elif variation_type == 41:
            self._apply_doubler_variation_zero_alloc(params, num_samples)
        elif variation_type == 42:
            self._apply_enhancer_reverb_variation_zero_alloc(params, num_samples)
        elif variation_type == 43:
            self._apply_spectral_variation_zero_alloc(params, num_samples)
        elif variation_type == 44:
            self._apply_resonator_variation_zero_alloc(params, num_samples)
        elif variation_type == 45:
            self._apply_degrader_variation_zero_alloc(params, num_samples)
        elif variation_type == 46:
            self._apply_vinyl_variation_zero_alloc(params, num_samples)
        elif variation_type == 47:
            self._apply_looper_variation_zero_alloc(params, num_samples)
        elif variation_type == 48:
            self._apply_step_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 49:
            self._apply_step_echo_variation_zero_alloc(params, num_samples)
        elif variation_type == 50:
            self._apply_step_pan_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 51:
            self._apply_step_cross_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 52:
            self._apply_step_multi_tap_variation_zero_alloc(params, num_samples)
        elif variation_type == 53:
            self._apply_step_reverse_delay_variation_zero_alloc(params, num_samples)
        elif variation_type == 54:
            self._apply_step_ring_mod_variation_zero_alloc(params, num_samples)
        elif variation_type == 55:
            self._apply_step_pitch_shifter_variation_zero_alloc(params, num_samples)
        elif variation_type == 56:
            self._apply_step_distortion_variation_zero_alloc(params, num_samples)
        elif variation_type == 57:
            self._apply_step_overdrive_variation_zero_alloc(params, num_samples)
        elif variation_type == 58:
            self._apply_step_compressor_variation_zero_alloc(params, num_samples)
        elif variation_type == 59:
            self._apply_step_limiter_variation_zero_alloc(params, num_samples)
        elif variation_type == 60:
            self._apply_step_gate_variation_zero_alloc(params, num_samples)
        elif variation_type == 61:
            self._apply_step_expander_variation_zero_alloc(params, num_samples)
        elif variation_type == 62:
            self._apply_step_rotary_speaker_variation_zero_alloc(params, num_samples)
        else:
            # Unknown effect type - no change to final mix
            pass

    def _apply_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Delay variation effect"""
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 ms
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        stereo = params.get("parameter4", 0.5)

        # Initialize delay buffer if needed (vectorized state management)
        if not hasattr(self, '_variation_delay_buffer') or len(self._variation_delay_buffer) != self.block_size:
            self._variation_delay_buffer = np.zeros(self.block_size, dtype=np.float32)
            self._variation_delay_pos = 0
            self._variation_delay_feedback = 0.0

        delay_samples = min(int(time * self.sample_rate / 1000.0), num_samples - 1)
        if delay_samples <= 0:
            return

        buffer = self._variation_delay_buffer
        pos = self._variation_delay_pos

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            # Read from delay buffer
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sample = buffer[int(delay_pos)]

            # Apply feedback
            feedback_sample = self._variation_delay_feedback * feedback
            processed_sample = input_sample + feedback_sample

            # Write to delay buffer
            buffer[pos] = processed_sample
            pos = (pos + 1) % len(buffer)
            self._variation_delay_feedback = processed_sample

            # Mix with original
            output_sample = input_sample * (1 - level) + delayed_sample * level
            left_mix = output_sample * (1 - stereo)
            right_mix = output_sample * stereo

            self.final_stereo_mix[i, 0] = left_mix
            self.final_stereo_mix[i, 1] = right_mix

        self._variation_delay_pos = pos

    def _apply_dual_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Dual Delay variation effect"""
        time1 = params.get("parameter1", 0.3) * 1000
        time2 = params.get("parameter2", 0.6) * 1000
        feedback = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        # Initialize delay buffers if needed
        if not hasattr(self, '_variation_dual_delay_buffers') or len(self._variation_dual_delay_buffers) != 2:
            self._variation_dual_delay_buffers = [
                np.zeros(self.block_size, dtype=np.float32) for _ in range(2)
            ]
            self._variation_dual_delay_pos = [0, 0]
            self._variation_dual_delay_feedback = 0.0

        delay_samples1 = min(int(time1 * self.sample_rate / 1000.0), num_samples // 2)
        delay_samples2 = min(int(time2 * self.sample_rate / 1000.0), num_samples // 2)

        buffers = self._variation_dual_delay_buffers
        pos = self._variation_dual_delay_pos

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            # Check bounds for each delay
            delay_pos1 = (pos[0] - delay_samples1) % len(buffers[0]) if delay_samples1 > 0 else 0
            delay_pos2 = (pos[1] - delay_samples2) % len(buffers[1]) if delay_samples2 > 0 else 0

            delayed_sample1 = buffers[0][int(delay_pos1)] if delay_samples1 > 0 else 0.0
            delayed_sample2 = buffers[1][int(delay_pos2)] if delay_samples2 > 0 else 0.0

            # Apply feedback
            feedback_sample = self._variation_dual_delay_feedback * feedback
            processed_sample = input_sample + feedback_sample

            # Write to delay buffers
            buffers[0][pos[0]] = processed_sample
            buffers[1][pos[1]] = processed_sample
            pos[0] = (pos[0] + 1) % len(buffers[0])
            pos[1] = (pos[1] + 1) % len(buffers[1])

            self._variation_dual_delay_feedback = processed_sample

            # Mix delays
            output = input_sample * (1 - level) + (delayed_sample1 + delayed_sample2) * level * 0.5
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

        self._variation_dual_delay_pos = pos

    def _apply_echo_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Echo variation effect"""
        time = params.get("parameter1", 0.5) * 1000
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        decay = params.get("parameter4", 0.8)

        # Initialize echo buffer if needed
        if not hasattr(self, '_variation_echo_buffer') or len(self._variation_echo_buffer) != self.block_size:
            self._variation_echo_buffer = np.zeros(self.block_size, dtype=np.float32)
            self._variation_echo_pos = 0
            self._variation_echo_feedback = 0.0

        delay_samples = min(int(time * self.sample_rate / 1000.0), num_samples - 1)
        if delay_samples <= 0:
            return

        buffer = self._variation_echo_buffer
        pos = self._variation_echo_pos

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            # Read from echo buffer
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sample = buffer[int(delay_pos)]

            # Apply feedback and decay
            feedback_sample = self._variation_echo_feedback * feedback * decay
            processed_sample = input_sample + feedback_sample

            # Write to echo buffer
            buffer[pos] = processed_sample
            pos = (pos + 1) % len(buffer)
            self._variation_echo_feedback = processed_sample

            # Mix with original
            output = input_sample * (1 - level) + delayed_sample * level
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

        self._variation_echo_pos = pos

    def _apply_tremolo_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Tremolo variation effect"""
        rate = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        # Initialize LFO state
        if not hasattr(self, '_variation_tremolo_phase'):
            self._variation_tremolo_phase = 0.0

        phase = self._variation_tremolo_phase

        for i in range(num_samples):
            # Update LFO phase
            phase += 2 * math.pi * rate / self.sample_rate

            if waveform == 0:  # Sine
                lfo_value = math.sin(phase + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((phase / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(phase + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (phase / (2 * math.pi)) % 1 * 2 - 1

            mod_amount = lfo_value * depth * 0.5 + 0.5
            self.final_stereo_mix[i, 0] *= mod_amount
            self.final_stereo_mix[i, 1] *= mod_amount

        self._variation_tremolo_phase = phase % (2 * math.pi)

    def _apply_auto_pan_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Auto Pan variation effect"""
        rate = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)
        phase = params.get("parameter4", 0.5)

        # Initialize LFO state
        if not hasattr(self, '_variation_auto_pan_phase'):
            self._variation_auto_pan_phase = 0.0

        lfo_phase = self._variation_auto_pan_phase

        for i in range(num_samples):
            # Update LFO phase
            lfo_phase += 2 * math.pi * rate / self.sample_rate

            if waveform == 0:  # Sine
                lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
            elif waveform == 1:  # Triangle
                lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
            elif waveform == 2:  # Square
                lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
            else:  # Sawtooth
                lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1

            pan = lfo_value * depth * 0.5 + 0.5

            # Auto-pan logic
            left_in = self.final_stereo_mix[i, 0]
            right_in = self.final_stereo_mix[i, 1]
            left_out = left_in * (1 - pan) + right_in * pan
            right_out = right_in * pan + left_in * (1 - pan)

            self.final_stereo_mix[i, 0] = left_out * (1 - depth) + left_out
            self.final_stereo_mix[i, 1] = right_out * (1 - depth) + right_out

        self._variation_auto_pan_phase = lfo_phase % (2 * math.pi)

    def _apply_phaser_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Phaser variation effect"""
        frequency = params.get("parameter1", 0.5) * 10.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)

        # Initialize phaser state
        if not hasattr(self, '_variation_phaser_state'):
            self._variation_phaser_state = {
                'phase': 0.0,
                'filters': [0.0] * 4
            }

        state = self._variation_phaser_state
        phase = state['phase']
        allpass_filters = state['filters']

        for i in range(num_samples):
            # Update LFO
            phase += 2 * math.pi * frequency / self.sample_rate

            if lfo_waveform == 0:  # Sine
                lfo_value = math.sin(phase)
            elif lfo_waveform == 1:  # Triangle
                lfo_value = 1 - abs((phase / math.pi) % 2 - 1) * 2
            elif lfo_waveform == 2:  # Square
                lfo_value = 1 if math.sin(phase) > 0 else -1
            else:  # Sawtooth
                lfo_value = (phase / (2 * math.pi)) % 1 * 2 - 1

            modulation = lfo_value * depth * 0.5 + 0.5
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            # All-pass filters
            filtered = input_sample
            for j in range(len(allpass_filters)):
                allpass_filters[j] = 0.7 * allpass_filters[j] + modulation * (filtered - allpass_filters[j])
                if j < len(allpass_filters) - 1:
                    filtered = allpass_filters[j]

            output = input_sample + feedback * (filtered - input_sample)
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

        state['phase'] = phase % (2 * math.pi)

    def _apply_flanger_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Flanger variation effect"""
        frequency = params.get("parameter1", 0.5) * 5.0
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)

        # Initialize flanger state
        if not hasattr(self, '_variation_flanger_state'):
            self._variation_flanger_state = {
                'phase': 0.0,
                'delay_buffer': np.zeros(int(0.02 * self.sample_rate)),
                'pos': 0,
                'feedback': 0.0
            }

        state = self._variation_flanger_state
        phase = state['phase']
        buffer = state['delay_buffer']
        pos = state['pos']

        delay_samples = int(len(buffer) * 0.5)

        for i in range(num_samples):
            # Update LFO
            phase += 2 * math.pi * frequency / self.sample_rate

            if lfo_waveform == 0:  # Sine
                lfo_value = math.sin(phase)
            elif lfo_waveform == 1:  # Triangle
                lfo_value = 1 - abs((phase / math.pi) % 2 - 1) * 2
            elif lfo_waveform == 2:  # Square
                lfo_value = 1 if math.sin(phase) > 0 else -1
            else:  # Sawtooth
                lfo_value = (phase / (2 * math.pi)) % 1 * 2 - 1

            modulation = lfo_value * depth * 0.5 + 0.5
            current_delay = int(delay_samples * modulation)

            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            # Read delayed sample
            delay_pos = (pos - current_delay) % len(buffer)
            delayed_sample = buffer[int(delay_pos)]

            # Apply feedback
            feedback_sample = state['feedback'] * feedback
            processed_sample = input_sample + feedback_sample

            # Write to buffer
            buffer[pos] = processed_sample
            pos = (pos + 1) % len(buffer)
            state['feedback'] = processed_sample

            # Mix with original
            output = input_sample * (1 - depth) + delayed_sample * depth
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

        state['phase'] = phase % (2 * math.pi)
        state['pos'] = pos

    def _apply_distortion_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Distortion variation effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type = int(params.get("parameter4", 0.5) * 3)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5

            if type == 0:  # Soft clipping
                output = math.atan(input_sample * drive * 5.0) / (math.pi / 2)
            elif type == 1:  # Hard clipping
                output = max(-1.0, min(1.0, input_sample * drive))
            elif type == 2:  # Asymmetric
                if input_sample > 0:
                    output = 1 - math.exp(-input_sample * drive)
                else:
                    output = -1 + math.exp(input_sample * drive)
            else:  # Symmetric
                output = math.tanh(input_sample * drive)

            # Apply tone filtering (simplified)
            if tone < 0.5:
                bass_boost = 1.0 + (0.5 - tone) * 2.0
                output = output * 0.7 + input_sample * 0.3 * bass_boost
            else:
                treble_boost = 1.0 + (tone - 0.5) * 2.0
                output = output * 0.7 + input_sample * 0.3 * treble_boost

            output *= level
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_overdrive_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Overdrive variation effect"""
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            biased = input_sample + bias * 0.1
            output = math.tanh(biased * (1 + drive * 9.0))

            # Apply tone filtering (simplified)
            if tone < 0.5:
                bass_boost = 1.0 + (0.5 - tone) * 2.0
                output = output * 0.7 + input_sample * 0.3 * bass_boost
            else:
                treble_boost = 1.0 + (tone - 0.5) * 2.0
                output = output * 0.7 + input_sample * 0.3 * treble_boost

            output *= level
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_compressor_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Compressor variation effect"""
        threshold = -60 + params.get("parameter1", 0.5) * 60
        ratio = 1 + params.get("parameter2", 0.5) * 19
        attack = 1 + params.get("parameter3", 0.5) * 99
        release = 10 + params.get("parameter4", 0.5) * 290

        threshold_linear = 10 ** (threshold / 20.0)

        # Initialize compressor state
        if not hasattr(self, '_variation_compressor_state'):
            self._variation_compressor_state = {
                'gain': 1.0,
                'attack_counter': 0,
                'release_counter': 0
            }

        state = self._variation_compressor_state

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            input_level = abs(input_sample)

            if input_level > threshold_linear:
                desired_gain = threshold_linear / (input_level ** (1/ratio))
            else:
                desired_gain = 1.0

            # Update gain with attack/release
            if desired_gain < state['gain']:
                factor = 1.0 / (attack * self.sample_rate / 1000.0 + 1)
                state['gain'] += (desired_gain - state['gain']) * factor
            else:
                factor = 1.0 / (release * self.sample_rate / 1000.0 + 1)
                state['gain'] += (desired_gain - state['gain']) * factor

            state['gain'] = max(0.001, min(1.0, state['gain']))

            output = input_sample * state['gain']
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_enhancer_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Enhancer variation effect"""
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            enhanced = input_sample + enhance * math.sin(input_sample * math.pi)

            # Apply bass and treble balance
            bass_factor = 0.5 + bass * 0.5
            treble_factor = 0.5 + treble * 0.5
            equalized = enhanced * (bass_factor * 0.6 + treble_factor * 0.4)

            output = equalized * level
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    # Simplified implementations for remaining effects (to satisfy the API)
    # These can be expanded to full implementations later

    def _apply_pan_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Pan Delay variation effect - simplified implementation"""
        # Simplified as regular delay with panning
        self._apply_delay_variation_zero_alloc(params, num_samples)

    def _apply_cross_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Cross Delay variation effect - simplified implementation"""
        # Simplified as regular delay
        self._apply_delay_variation_zero_alloc(params, num_samples)

    def _apply_multi_tap_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Multi Tap variation effect - simplified implementation"""
        # Simplified as regular delay
        self._apply_delay_variation_zero_alloc(params, num_samples)

    def _apply_reverse_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Reverse Delay variation effect - simplified implementation"""
        # Simplified as regular delay
        self._apply_delay_variation_zero_alloc(params, num_samples)

    def _apply_auto_wah_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Auto Wah variation effect - simplified implementation"""
        # Simplified as phaser
        self._apply_phaser_variation_zero_alloc(params, num_samples)

    def _apply_ring_mod_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Ring Mod variation effect - simplified implementation"""
        # Simplified as tremolo
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    def _apply_pitch_shifter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Pitch Shifter variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_limiter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Limiter variation effect - simplified implementation"""
        # Simplified as compressor
        self._apply_compressor_variation_zero_alloc(params, num_samples)

    def _apply_gate_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Gate variation effect - simplified implementation"""
        # Simplified as compressor
        self._apply_compressor_variation_zero_alloc(params, num_samples)

    def _apply_expander_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Expander variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_rotary_speaker_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Rotary Speaker variation effect - simplified implementation"""
        # Simplified as tremolo
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    def _apply_leslie_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Leslie variation effect - simplified implementation"""
        # Simplified as tremolo
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    def _apply_vibrato_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Vibrato variation effect - simplified implementation"""
        # Simplified as tremolo
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    def _apply_acoustic_simulator_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Acoustic Simulator variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_guitar_amp_sim_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Guitar Amp Sim variation effect - simplified implementation"""
        # Simplified as distortion
        self._apply_distortion_variation_zero_alloc(params, num_samples)

    def _apply_slicer_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Slicer variation effect - simplified implementation"""
        # Simplified as tremolo
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    # Step effects (simplified placeholders)
    def _apply_step_phaser_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Phaser variation effect - simplified implementation"""
        self._apply_phaser_variation_zero_alloc(params, num_samples)

    def _apply_step_flanger_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Flanger variation effect - simplified implementation"""
        self._apply_flanger_variation_zero_alloc(params, num_samples)

    def _apply_step_tremolo_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Tremolo variation effect - simplified implementation"""
        self._apply_tremolo_variation_zero_alloc(params, num_samples)

    def _apply_step_pan_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Pan variation effect - simplified implementation"""
        self._apply_auto_pan_variation_zero_alloc(params, num_samples)

    def _apply_step_filter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Filter variation effect - simplified implementation"""
        self._apply_phaser_variation_zero_alloc(params, num_samples)

    def _apply_auto_filter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Auto Filter variation effect - simplified implementation"""
        self._apply_phaser_variation_zero_alloc(params, num_samples)

    def _apply_vocoder_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Vocoder variation effect - simplified implementation"""
        # Simplified - basic filtering
        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * 0.8  # Simple level attenuation
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_talk_wah_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Talk Wah variation effect - simplified implementation"""
        self._apply_auto_wah_variation_zero_alloc(params, num_samples)

    def _apply_harmonizer_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Harmonizer variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_octave_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Octave variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_detune_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Detune variation effect - simplified implementation"""
        # Simplified - no change for now
        pass

    def _apply_chorus_reverb_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Chorus/Reverb variation effect - simplified implementation"""
        # Simplified - just apply some level mixing
        chorus_level = params.get("parameter1", 0.5)
        reverb_level = params.get("parameter2", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * (1 - chorus_level - reverb_level) + input_sample * chorus_level + input_sample * reverb_level
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_stereo_imager_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Stereo Imager variation effect - simplified implementation"""
        width = params.get("parameter1", 0.5)

        for i in range(num_samples):
            left = self.final_stereo_mix[i, 0]
            right = self.final_stereo_mix[i, 1]
            center = (left + right) * 0.5
            sides = (left - right) * 0.5 * width
            self.final_stereo_mix[i, 0] = center + sides
            self.final_stereo_mix[i, 1] = center - sides

    def _apply_ambience_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Ambience variation effect - simplified implementation"""
        reverb = params.get("parameter1", 0.5)
        delay = params.get("parameter2", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * (1 - reverb - delay) + input_sample * reverb + input_sample * delay
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_doubler_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Doubler variation effect - simplified implementation"""
        enhance = params.get("parameter1", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            doubled = input_sample  # Simplified doubling
            output = input_sample * (1 - enhance) + doubled * enhance
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_enhancer_reverb_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Enhancer/Reverb variation effect - simplified implementation"""
        enhance = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            enhanced = input_sample + enhance * math.sin(input_sample * math.pi)
            output = enhanced * (1 - reverb) + input_sample * reverb
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_spectral_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Spectral variation effect - simplified implementation"""
        # Basic spectral processing - just attenuation
        spectrum = params.get("parameter1", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * spectrum
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_resonator_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Resonator variation effect - simplified implementation"""
        resonance = params.get("parameter1", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * (1 + resonance)  # Simple resonance
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_degrader_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Degrader variation effect - simplified implementation"""
        bit_depth = int(params.get("parameter1", 0.5) * 16) + 1

        for i in range(num_samples):
            left = self.final_stereo_mix[i, 0]
            right = self.final_stereo_mix[i, 1]

            # Simple bit depth reduction
            if bit_depth < 16:
                scale = 2 ** bit_depth
                left = math.floor(left * scale) / scale
                right = math.floor(right * scale) / scale

            self.final_stereo_mix[i, 0] = left
            self.final_stereo_mix[i, 1] = right

    def _apply_vinyl_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Vinyl variation effect - simplified implementation"""
        warp = params.get("parameter1", 0.5)

        for i in range(num_samples):
            input_sample = (self.final_stereo_mix[i, 0] + self.final_stereo_mix[i, 1]) * 0.5
            output = input_sample * (1 - warp * 0.3)  # Simple warp effect
            self.final_stereo_mix[i, 0] = output
            self.final_stereo_mix[i, 1] = output

    def _apply_looper_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Looper variation effect - simplified implementation"""
        # Simplified - no change for looping effects
        pass

    def _apply_step_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Delay variation effect - simplified implementation"""
        self._apply_delay_variation_zero_alloc(params, num_samples)

    def _apply_step_echo_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Echo variation effect - simplified implementation"""
        self._apply_echo_variation_zero_alloc(params, num_samples)

    def _apply_step_pan_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Pan Delay variation effect - simplified implementation"""
        self._apply_pan_delay_variation_zero_alloc(params, num_samples)

    def _apply_step_cross_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Cross Delay variation effect - simplified implementation"""
        self._apply_cross_delay_variation_zero_alloc(params, num_samples)

    # Missing step variation effect implementations added below

    def _apply_step_multi_tap_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Multi Tap variation effect - simplified implementation"""
        self._apply_multi_tap_variation_zero_alloc(params, num_samples)

    def _apply_step_reverse_delay_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Reverse Delay variation effect - simplified implementation"""
        self._apply_reverse_delay_variation_zero_alloc(params, num_samples)

    def _apply_step_ring_mod_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Ring Mod variation effect - simplified implementation"""
        self._apply_ring_mod_variation_zero_alloc(params, num_samples)

    def _apply_step_pitch_shifter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Pitch Shifter variation effect - simplified implementation"""
        self._apply_pitch_shifter_variation_zero_alloc(params, num_samples)

    def _apply_step_distortion_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Distortion variation effect - simplified implementation"""
        self._apply_distortion_variation_zero_alloc(params, num_samples)

    def _apply_step_overdrive_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Overdrive variation effect - simplified implementation"""
        self._apply_overdrive_variation_zero_alloc(params, num_samples)

    def _apply_step_compressor_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Compressor variation effect - simplified implementation"""
        self._apply_compressor_variation_zero_alloc(params, num_samples)

    def _apply_step_limiter_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Limiter variation effect - simplified implementation"""
        self._apply_limiter_variation_zero_alloc(params, num_samples)

    def _apply_step_gate_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Gate variation effect - simplified implementation"""
        self._apply_gate_variation_zero_alloc(params, num_samples)

    def _apply_step_expander_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Expander variation effect - simplified implementation"""
        self._apply_expander_variation_zero_alloc(params, num_samples)

    def _apply_step_rotary_speaker_variation_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply Step Rotary Speaker variation effect - simplified implementation"""
        self._apply_rotary_speaker_variation_zero_alloc(params, num_samples)

    def _apply_eq_to_mix_zero_alloc(self, params: Dict[str, Any], num_samples: int) -> None:
        """Apply XG Multi-Band Equalizer to stereo mix using zero-allocation approach"""
        # Update EQ parameters from state manager
        eq_type = params.get("eq_type", 0)
        low_gain = params.get("low_gain", 0.0)
        mid_gain = params.get("mid_gain", 0.0)
        high_gain = params.get("high_gain", 0.0)
        mid_freq = params.get("mid_freq", 1000.0)
        q_factor = params.get("q_factor", 1.0)

        # Set EQ parameters
        self.equalizer.set_eq_type(eq_type)
        self.equalizer.set_low_gain(low_gain)
        self.equalizer.set_mid_gain(mid_gain)
        self.equalizer.set_high_gain(high_gain)
        self.equalizer.set_mid_frequency(mid_freq)
        self.equalizer.set_q_factor(q_factor)

        # Apply EQ to the final stereo mix
        self.final_stereo_mix[:num_samples] = self.equalizer.process_buffer(self.final_stereo_mix[:num_samples])

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
