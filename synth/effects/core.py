"""
XG Effects Core Manager

This module provides the main XGEffectManager class that coordinates
all XG effect processing, state management, and communication.
"""

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
