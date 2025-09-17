"""
XG Effects Core Manager

This module provides the main XGEffectManager class that coordinates
all XG effect processing, state management, and communication.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union

from .constants import NUM_CHANNELS
from .state import EffectStateManager
from .communication import XGCommunicationHandler
from .processing import XGAudioProcessor


class XGEffectManager:
    """
    Complete implementation of XG effects manager supporting system effects,
    insertion effects, multitimbral mode, and full variation effects set.
    Integrates with sequencer through NRPN and SysEx messages.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize XG effects manager.

        Args:
            sample_rate: Sample rate for audio processing
        """
        self.sample_rate = sample_rate

        # Initialize core components
        self.state_manager = EffectStateManager()
        self.comm_handler = XGCommunicationHandler(self.state_manager)
        self.audio_processor = XGAudioProcessor(self.state_manager, sample_rate)

        # Set up communication handler references
        self.comm_handler.state_manager = self.state_manager

        # Initialize effects
        self.reset_effects()

    def reset_effects(self):
        """Reset all effects to default values"""
        self.state_manager.reset_effects()

    # State management methods
    def get_current_state(self) -> Dict[str, Any]:
        """Get current effects state (thread-safe)"""
        return self.state_manager.get_current_state()

    def get_channel_insertion_effect(self, channel: int) -> Dict[str, Any]:
        """Get insertion effect parameters for channel"""
        return self.state_manager.get_channel_insertion_effect(channel)

    # Channel-specific effect methods
    def set_channel_insertion_effect_enabled(self, channel: int, enabled: bool):
        """Enable/disable insertion effect for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["enabled"] = enabled
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_type(self, channel: int, effect_type: int):
        """Set insertion effect type for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["type"] = effect_type
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_parameter(self, channel: int, param_index: int, value: float):
        """Set insertion effect parameter for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS and 1 <= param_index <= 4:
                param_name = f"parameter{param_index}"
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"][param_name] = value
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_level(self, channel: int, level: float):
        """Set insertion effect level for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["level"] = level
                self.state_manager.state_update_pending = True

    def set_channel_insertion_effect_bypass(self, channel: int, bypass: bool):
        """Set insertion effect bypass for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["bypass"] = bypass
                self.state_manager.state_update_pending = True

    # Extended Phaser/Flanger methods
    def set_channel_phaser_frequency(self, channel: int, frequency: float):
        """Set phaser LFO frequency for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_manager.state_update_pending = True

    def set_channel_phaser_depth(self, channel: int, depth: float):
        """Set phaser depth for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_manager.state_update_pending = True

    def set_channel_phaser_feedback(self, channel: int, feedback: float):
        """Set phaser feedback for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_manager.state_update_pending = True

    def set_channel_phaser_waveform(self, channel: int, waveform: int):
        """Set phaser LFO waveform for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_manager.state_update_pending = True

    # Flanger methods
    def set_channel_flanger_frequency(self, channel: int, frequency: float):
        """Set flanger LFO frequency for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_manager.state_update_pending = True

    def set_channel_flanger_depth(self, channel: int, depth: float):
        """Set flanger depth for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_manager.state_update_pending = True

    def set_channel_flanger_feedback(self, channel: int, feedback: float):
        """Set flanger feedback for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_manager.state_update_pending = True

    def set_channel_flanger_waveform(self, channel: int, waveform: int):
        """Set flanger LFO waveform for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_manager.state_update_pending = True

    def reset_channel_insertion_effect(self, channel: int):
        """Reset insertion effect for channel to defaults"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["insertion_effect"] = \
                    self.state_manager._create_insertion_effect_params()
                self.state_manager.state_update_pending = True

    def reset_all_insertion_effects(self):
        """Reset all insertion effects to defaults"""
        with self.state_manager.state_lock:
            for i in range(NUM_CHANNELS):
                self.state_manager._temp_state["channel_params"][i]["insertion_effect"] = \
                    self.state_manager._create_insertion_effect_params()
            self.state_manager.state_update_pending = True

    # Audio processing
    def process_audio(self, input_samples: List[List[Tuple[float, float]]],
                     num_samples: int) -> List[List[Tuple[float, float]]]:
        """
        Process audio with XG effects applied.

        Args:
            input_samples: List of channels with stereo sample tuples
            num_samples: Number of samples to process

        Returns:
            Processed audio samples
        """
        return self.audio_processor.process_audio(input_samples, num_samples)

    def process_stereo_audio_vectorized(self, input_samples):
        """
        Process stereo audio with XG effects applied using vectorized operations.
        
        This is a compatibility method for the optimized synthesizer implementation.
        
        Args:
            input_samples: Input stereo audio samples as NumPy array (N x 2)
            
        Returns:
            Processed stereo audio samples as NumPy array (N x 2)
        """
        # For compatibility with the optimized implementation, we'll process
        # the stereo audio as a single channel with both left and right samples
        num_samples = input_samples.shape[0]
        
        # Convert NumPy array to the format expected by the audio processor
        # Create a single channel with stereo tuples
        channel_samples = [(input_samples[i, 0], input_samples[i, 1]) for i in range(num_samples)]
        
        # Create 16 empty channels (to match expected format)
        input_channels = [channel_samples] + [[] for _ in range(15)]
        
        try:
            # Process audio
            processed_channels = self.audio_processor.process_audio(input_channels, num_samples)
            
            # Convert back to NumPy array format
            if processed_channels and len(processed_channels) > 0 and len(processed_channels[0]) > 0:
                result = np.zeros((num_samples, 2), dtype=np.float32)
                for i, (left, right) in enumerate(processed_channels[0]):
                    result[i, 0] = left
                    result[i, 1] = right
                return result
        except Exception as e:
            # print(f"Error processing effects: {e}")
            pass
        
        # If processing failed, return input unchanged
        return input_samples

    # Communication methods
    def set_current_nrpn_channel(self, channel: int):
        """Set current NRPN channel"""
        self.comm_handler.set_current_nrpn_channel(channel)

    def set_nrpn_msb(self, value: int):
        """Set NRPN MSB"""
        self.comm_handler.set_nrpn_msb(value)

    def set_nrpn_lsb(self, value: int):
        """Set NRPN LSB"""
        self.comm_handler.set_nrpn_lsb(value)

    def set_channel_effect_parameter(self, channel: int, nrpn_msb: int, nrpn_lsb: int, value: int):
        """Set channel effect parameter via NRPN"""
        self.comm_handler.set_channel_effect_parameter(channel, nrpn_msb, nrpn_lsb, value)

    def handle_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int,
                   channel: Optional[int] = None) -> bool:
        """
        Handle NRPN message for effects.

        Returns:
            True if NRPN was handled, False otherwise
        """
        return self.comm_handler.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb, channel)

    def handle_sysex(self, manufacturer_id: List[int], data: List[int]) -> bool:
        """
        Handle SysEx message for effects.

        Returns:
            True if SysEx was handled, False otherwise
        """
        return self.comm_handler.handle_sysex(manufacturer_id, data)

    def get_bulk_dump(self, channel_specific: bool = False) -> List[int]:
        """
        Generate bulk dump of current effect parameters.

        Args:
            channel_specific: If True, generate channel-specific dump

        Returns:
            SysEx data for bulk dump
        """
        return self.comm_handler.get_bulk_dump(channel_specific)

    # Variation effect methods
    def set_variation_effect_type(self, channel: int, effect_type: int):
        """Set variation effect type for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["type"] = effect_type
                self.state_manager.state_update_pending = True

    def set_variation_effect_bypass(self, channel: int, bypass: bool):
        """Set variation effect bypass for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["bypass"] = bypass
                self.state_manager.state_update_pending = True

    def set_variation_effect_level(self, channel: int, level: float):
        """Set variation effect level for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                self.state_manager._temp_state["channel_params"][channel]["variation_params"]["level"] = level
                self.state_manager.state_update_pending = True

    def set_variation_effect_parameter(self, channel: int, param_index: int, value: float):
        """Set variation effect parameter for channel"""
        with self.state_manager.state_lock:
            if 0 <= channel < NUM_CHANNELS and 1 <= param_index <= 4:
                param_name = f"parameter{param_index}"
                self.state_manager._temp_state["channel_params"][channel]["variation_params"][param_name] = value
                self.state_manager.state_update_pending = True

    # Preset management
    def set_effect_preset(self, preset_name: str):
        """
        Set effect preset for entire sequencer.

        Args:
            preset_name: Name of preset to load
        """
        presets = self._get_presets()
        if preset_name in presets:
            preset = presets[preset_name]

            # Apply system effects
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

            # Apply insertion effects
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
        """Get available effect presets"""
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
                "reverb": {"type": 0, "time": 1.8, "level": 0.4, "pre_delay": 25.0, "hf_damping": 0.4},
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

    def process_bulk_dump(self, effect_type: int, param_offset: int, data: list) -> bool:
        """
        Process bulk dump data for effect parameters.
        
        Args:
            effect_type: Effect type identifier
            param_offset: Starting parameter offset
            data: List of 7-bit parameter values
            
        Returns:
            True if processed successfully
        """
        # Implementation from previous edit

    def get_bulk_parameter(self, effect_type: int, param_index: int) -> int:
        """
        Get an effect parameter value by index for bulk dump generation.
        
        Args:
            effect_type: Effect type identifier
            param_index: Parameter index
            
        Returns:
            7-bit parameter value
        """
        try:
            # Get current parameter value based on effect type and parameter index
            if effect_type == 0:  # Reverb parameters
                # XG Reverb Parameters
                reverb_params = [
                    "type", "time", "level", "pre_delay", "hf_damping", "density", 
                    "early_level", "tail_level", "shape", "gate_time", "predelay_scale"
                ]
                if param_index < len(reverb_params):
                    param_name = reverb_params[param_index]
                    with self.state_manager.state_lock:
                        current_value = self.state_manager._temp_state["reverb_params"].get(param_name, 0.0)
                    
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
                    with self.state_manager.state_lock:
                        current_value = self.state_manager._temp_state["chorus_params"].get(param_name, 0.0)
                    
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
                # XG Variation Parameters
                variation_params = [
                    "type", "parameter1", "parameter2", "parameter3", "parameter4",
                    "level", "bypass", "pan", "send_reverb", "send_chorus"
                ]
                if param_index < len(variation_params):
                    param_name = variation_params[param_index]
                    with self.state_manager.state_lock:
                        current_value = self.state_manager._temp_state["variation_params"].get(param_name, 0.0)
                    
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
            
            elif effect_type == 3:  # Insertion Effect parameters
                # XG Insertion Parameters
                insertion_params = [
                    "type", "parameter1", "parameter2", "parameter3", "parameter4",
                    "level", "bypass", "frequency", "depth", "feedback", "lfo_waveform"
                ]
                if param_index < len(insertion_params):
                    param_name = insertion_params[param_index]
                    with self.state_manager.state_lock:
                        current_value = self.state_manager._temp_state["insertion_params"].get(param_name, 0.0)
                    
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
                    with self.state_manager.state_lock:
                        current_value = self.state_manager._temp_state["equalizer_params"].get(param_name, 0.0)
                    
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
            
        except Exception as e:
            print(f"Error getting effect bulk parameter: {e}")
            return 0
