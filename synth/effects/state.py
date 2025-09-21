"""
XG Effects State Management

This module handles the state management for XG effects, including
parameter storage, state transitions, and thread-safe operations.
"""

import threading
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import numpy as np

from .constants import NUM_CHANNELS


class EffectStateManager:
    """
    Manages the state of XG effects with thread-safe operations.
    """

    def __init__(self):
        """Initialize the state manager"""
        # Thread safety
        self.state_lock = threading.RLock()

        # Current and temporary states
        self._current_state = self._create_empty_state()
        self._temp_state = self._create_empty_state()
        self.state_update_pending = False

        # Channel effect states
        self.channel_effect_states = [{} for _ in range(NUM_CHANNELS)]

        # Internal effect states
        self._reverb_state = self._create_reverb_state()
        self._chorus_state = self._create_chorus_state()

    def _create_empty_state(self) -> Dict[str, Any]:
        """Create an empty state structure"""
        return {
            "reverb_params": {},
            "chorus_params": {},
            "variation_params": {},
            "equalizer_params": {},
            "routing_params": {},
            "global_effect_params": {},
            "channel_params": [self._create_channel_params() for _ in range(NUM_CHANNELS)]
        }

    def _create_channel_params(self) -> Dict[str, Any]:
        """Create default parameters for a channel"""
        return {
            "reverb_send": 0.5,  # Reverb send level
            "chorus_send": 0.3,  # Chorus send level
            "variation_send": 0.2,  # Variation send level
            "insertion_send": 1.0,  # Insertion send level
            "muted": False,  # Channel mute
            "soloed": False,  # Channel solo
            "pan": 0.5,  # Pan (0.0-1.0)
            "volume": 1.0,  # Volume (0.0-1.0)
            "expression": 1.0,  # Expression (0.0-1.0)
            # XG Channel Parameters
            "pitch_bend_range": 2,  # Pitch bend range in semitones (0-24)
            "fine_tuning": 0.0,  # Fine tuning (-1.0 to +1.0 representing -100 to +100 cents)
            "coarse_tuning": 0,  # Coarse tuning (-64 to +63 semitones)
            "tuning_program": 0,  # Tuning program (0-127)
            "tuning_bank": 0,  # Tuning bank (0-127)
            "modulation_depth": 64,  # Modulation depth (0-127 cents)
            "element_reserve": 0,  # Element reserve (0-127)
            "element_assign_mode": 0,  # Element assign mode (0-127)
            "receive_channel": 0,  # Receive channel (0-15)
            "insertion_effect": self._create_insertion_effect_params(),
            "variation_params": self._create_variation_params()
        }

    def _create_insertion_effect_params(self) -> Dict[str, Any]:
        """Create default parameters for insertion effect"""
        return {
            "enabled": True,
            "type": 0,  # Off
            "parameter1": 0.5,  # 0.0-1.0
            "parameter2": 0.5,  # 0.0-1.0
            "parameter3": 0.5,  # 0.0-1.0
            "parameter4": 0.5,  # 0.0-1.0
            "level": 1.0,  # 0.0-1.0
            "bypass": False,  # true/false
            # Extended parameters for Phaser and Flanger
            "frequency": 1.0,
            "depth": 0.5,
            "feedback": 0.3,
            "lfo_waveform": 0,  # 0=sine, 1=triangle, 2=square, 3=sawtooth
            # Additional parameters for all effect types
            "drive": 0.5,
            "tone": 0.5,
            "bias": 0.5,
            "threshold": 0.5,
            "ratio": 0.5,
            "attack": 0.1,
            "release": 0.5,
            "reduction": 0.5,
            "hold": 0.1,
            "sensitivity": 0.5,
            "resonance": 0.5,
            "mode": 0,
            "bass": 0.5,
            "treble": 0.5,
            "enhance": 0.5,
            "speed": 1.0,
            "balance": 0.5,
            "accel": 0.5,
            "rate": 1.0,
            "waveform": 0,
            "phase": 0.0,
            "bands": 8,
            "formant": 0.5,
            "intervals": 12,
            "mix": 0.5,
            "shift": 0.0,
            "cutoff": 1000.0,
            "manual_position": 0.5,
            "lfo_rate": 1.0,
            "lfo_depth": 0.5,
            "time": 0.5,
            "stereo": 0.5,
            "decay": 0.5,
            "hf_damping": 0.5
        }

    def _create_variation_params(self) -> Dict[str, Any]:
        """Create default parameters for variation effect"""
        return {
            "type": 0,  # Delay
            "parameter1": 0.5,  # 0.0-1.0
            "parameter2": 0.5,  # 0.0-1.0
            "parameter3": 0.5,  # 0.0-1.0
            "parameter4": 0.5,  # 0.0-1.0
            "level": 0.5,  # 0.0-1.0
            "bypass": False  # true/false
        }

    def _create_reverb_state(self) -> Dict[str, Any]:
        """Create initial reverb state"""
        return {
            "allpass_buffers": [np.zeros(441) for _ in range(4)],
            "allpass_indices": [0] * 4,
            "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
            "comb_indices": [0] * 4,
            "early_reflection_buffer": np.zeros(441),
            "early_reflection_index": 0,
            "late_reflection_buffer": np.zeros(441 * 10),
            "late_reflection_index": 0
        }

    def _create_chorus_state(self) -> Dict[str, Any]:
        """Create initial chorus state"""
        return {
            "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms delays
            "lfo_phases": [0.0, 0.0],
            "lfo_rates": [1.0, 0.5],
            "lfo_depths": [0.5, 0.3],
            "write_indices": [0, 0],
            "feedback_buffers": [0.0, 0.0]
        }

    def _copy_state(self, source: Dict[str, Any], dest: Dict[str, Any]):
        """Copy state from source to destination"""
        with self.state_lock:
            dest["reverb_params"] = source["reverb_params"].copy()
            dest["chorus_params"] = source["chorus_params"].copy()
            dest["variation_params"] = source["variation_params"].copy()
            dest["equalizer_params"] = source["equalizer_params"].copy()
            dest["routing_params"] = source["routing_params"].copy()
            dest["global_effect_params"] = source["global_effect_params"].copy()

            for i in range(NUM_CHANNELS):
                dest["channel_params"][i] = {
                    "reverb_send": source["channel_params"][i]["reverb_send"],
                    "chorus_send": source["channel_params"][i]["chorus_send"],
                    "variation_send": source["channel_params"][i]["variation_send"],
                    "insertion_send": source["channel_params"][i]["insertion_send"],
                    "muted": source["channel_params"][i]["muted"],
                    "soloed": source["channel_params"][i]["soloed"],
                    "pan": source["channel_params"][i]["pan"],
                    "volume": source["channel_params"][i]["volume"],
                    "expression": source["channel_params"][i]["expression"],
                    # XG Channel Parameters
                    "pitch_bend_range": source["channel_params"][i].get("pitch_bend_range", 2),
                    "fine_tuning": source["channel_params"][i].get("fine_tuning", 0.0),
                    "coarse_tuning": source["channel_params"][i].get("coarse_tuning", 0),
                    "tuning_program": source["channel_params"][i].get("tuning_program", 0),
                    "tuning_bank": source["channel_params"][i].get("tuning_bank", 0),
                    "modulation_depth": source["channel_params"][i].get("modulation_depth", 64),
                    "element_reserve": source["channel_params"][i].get("element_reserve", 0),
                    "element_assign_mode": source["channel_params"][i].get("element_assign_mode", 0),
                    "receive_channel": source["channel_params"][i].get("receive_channel", 0),
                    "insertion_effect": {
                        **source["channel_params"][i]["insertion_effect"],
                        # Ensure all parameters are present
                        "enabled": source["channel_params"][i]["insertion_effect"].get("enabled", True),
                        "type": source["channel_params"][i]["insertion_effect"].get("type", 0),
                        "parameter1": source["channel_params"][i]["insertion_effect"].get("parameter1", 0.5),
                        "parameter2": source["channel_params"][i]["insertion_effect"].get("parameter2", 0.5),
                        "parameter3": source["channel_params"][i]["insertion_effect"].get("parameter3", 0.5),
                        "parameter4": source["channel_params"][i]["insertion_effect"].get("parameter4", 0.5),
                        "level": source["channel_params"][i]["insertion_effect"].get("level", 1.0),
                        "bypass": source["channel_params"][i]["insertion_effect"].get("bypass", False),
                        "frequency": source["channel_params"][i]["insertion_effect"].get("frequency", 1.0),
                        "depth": source["channel_params"][i]["insertion_effect"].get("depth", 0.5),
                        "feedback": source["channel_params"][i]["insertion_effect"].get("feedback", 0.3),
                        "lfo_waveform": source["channel_params"][i]["insertion_effect"].get("lfo_waveform", 0),
                        "drive": source["channel_params"][i]["insertion_effect"].get("drive", 0.5),
                        "tone": source["channel_params"][i]["insertion_effect"].get("tone", 0.5),
                        "bias": source["channel_params"][i]["insertion_effect"].get("bias", 0.5),
                        "threshold": source["channel_params"][i]["insertion_effect"].get("threshold", 0.5),
                        "ratio": source["channel_params"][i]["insertion_effect"].get("ratio", 0.5),
                        "attack": source["channel_params"][i]["insertion_effect"].get("attack", 0.1),
                        "release": source["channel_params"][i]["insertion_effect"].get("release", 0.5),
                        "reduction": source["channel_params"][i]["insertion_effect"].get("reduction", 0.5),
                        "hold": source["channel_params"][i]["insertion_effect"].get("hold", 0.1),
                        "sensitivity": source["channel_params"][i]["insertion_effect"].get("sensitivity", 0.5),
                        "resonance": source["channel_params"][i]["insertion_effect"].get("resonance", 0.5),
                        "mode": source["channel_params"][i]["insertion_effect"].get("mode", 0),
                        "bass": source["channel_params"][i]["insertion_effect"].get("bass", 0.5),
                        "treble": source["channel_params"][i]["insertion_effect"].get("treble", 0.5),
                        "enhance": source["channel_params"][i]["insertion_effect"].get("enhance", 0.5),
                        "speed": source["channel_params"][i]["insertion_effect"].get("speed", 1.0),
                        "balance": source["channel_params"][i]["insertion_effect"].get("balance", 0.5),
                        "accel": source["channel_params"][i]["insertion_effect"].get("accel", 0.5),
                        "rate": source["channel_params"][i]["insertion_effect"].get("rate", 1.0),
                        "waveform": source["channel_params"][i]["insertion_effect"].get("waveform", 0),
                        "phase": source["channel_params"][i]["insertion_effect"].get("phase", 0.0),
                        "bands": source["channel_params"][i]["insertion_effect"].get("bands", 8),
                        "formant": source["channel_params"][i]["insertion_effect"].get("formant", 0.5),
                        "intervals": source["channel_params"][i]["insertion_effect"].get("intervals", 12),
                        "mix": source["channel_params"][i]["insertion_effect"].get("mix", 0.5),
                        "shift": source["channel_params"][i]["insertion_effect"].get("shift", 0.0),
                        "cutoff": source["channel_params"][i]["insertion_effect"].get("cutoff", 1000.0),
                        "manual_position": source["channel_params"][i]["insertion_effect"].get("manual_position", 0.5),
                        "lfo_rate": source["channel_params"][i]["insertion_effect"].get("lfo_rate", 1.0),
                        "lfo_depth": source["channel_params"][i]["insertion_effect"].get("lfo_depth", 0.5),
                        "time": source["channel_params"][i]["insertion_effect"].get("time", 0.5),
                        "stereo": source["channel_params"][i]["insertion_effect"].get("stereo", 0.5),
                        "decay": source["channel_params"][i]["insertion_effect"].get("decay", 0.5),
                        "hf_damping": source["channel_params"][i]["insertion_effect"].get("hf_damping", 0.5)
                    },
                    "variation_params": source["channel_params"][i]["variation_params"].copy()
                }

    def _update_parameter(self, state: Dict[str, Any], target: str, param: str, value: Any):
        """Update a parameter in the state"""
        if target == "reverb":
            state["reverb_params"][param] = value
        elif target == "chorus":
            state["chorus_params"][param] = value
        elif target == "variation":
            state["variation_params"][param] = value
        elif target == "equalizer":
            state["equalizer_params"][param] = value
        elif target == "routing":
            state["routing_params"][param] = value
        elif target == "global":
            state["global_effect_params"][param] = value
        elif target == "system":
            # Handle system parameters
            if "system_params" not in state:
                state["system_params"] = {}
            state["system_params"][param] = value
        elif target == "channel":
            channel = getattr(self, 'current_nrpn_channel', 0)
            if 0 <= channel < NUM_CHANNELS:
                # Handle XG channel parameters
                if param in ["reverb_send", "chorus_send", "variation_send", "insertion_send",
                           "muted", "soloed", "pan", "volume", "expression",
                           "pitch_bend_range", "fine_tuning", "coarse_tuning",
                           "tuning_program", "tuning_bank", "modulation_depth",
                           "element_reserve", "element_assign_mode", "receive_channel"]:
                    state["channel_params"][channel][param] = value
        elif target == "insertion":
            channel = getattr(self, 'current_nrpn_channel', 0)
            if 0 <= channel < NUM_CHANNELS:
                # Support all insertion effect parameters
                valid_params = [
                    "enabled", "type", "parameter1", "parameter2", "parameter3", "parameter4",
                    "level", "bypass", "frequency", "depth", "feedback", "lfo_waveform",
                    "drive", "tone", "bias", "threshold", "ratio", "attack", "release",
                    "reduction", "hold", "sensitivity", "resonance", "mode", "bass", "treble",
                    "enhance", "speed", "balance", "accel", "rate", "waveform", "phase",
                    "bands", "formant", "intervals", "mix", "shift", "cutoff", "manual_position",
                    "lfo_rate", "lfo_depth", "time", "stereo", "decay", "hf_damping"
                ]
                if param in valid_params:
                    state["channel_params"][channel]["insertion_effect"][param] = value

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current state (thread-safe)"""
        with self.state_lock:
            state = self._create_empty_state()
            self._copy_state(self._current_state, state)
            return state

    def update_temp_state(self, target: str, param: str, value: Any):
        """Update the temporary state"""
        with self.state_lock:
            self._update_parameter(self._temp_state, target, param, value)
            self.state_update_pending = True

    def apply_temp_state(self):
        """Apply temporary state to current state"""
        with self.state_lock:
            if self.state_update_pending:
                self._copy_state(self._temp_state, self._current_state)
                self.state_update_pending = False

    def reset_effects(self):
        """Reset all effects to default values"""
        with self.state_lock:
            # Reverb parameters
            self._temp_state["reverb_params"] = {
                "type": 0,  # Hall 1
                "time": 2.5,  # seconds
                "level": 0.6,  # 0.0-1.0
                "pre_delay": 20.0,  # milliseconds
                "hf_damping": 0.5,  # 0.0-1.0
                "density": 0.8,  # 0.0-1.0
                "early_level": 0.7,  # 0.0-1.0
                "tail_level": 0.9,  # 0.0-1.0
                "allpass_buffers": [np.zeros(441) for _ in range(4)],
                "allpass_indices": [0] * 4,
                "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
                "comb_indices": [0] * 4,
                "early_reflection_buffer": np.zeros(441),
                "early_reflection_index": 0,
                "late_reflection_buffer": np.zeros(441 * 10),
                "late_reflection_index": 0
            }

            # Chorus parameters
            self._temp_state["chorus_params"] = {
                "type": 0,  # Chorus 1
                "rate": 1.0,  # Hz
                "depth": 0.5,  # 0.0-1.0
                "feedback": 0.3,  # 0.0-1.0
                "level": 0.4,  # 0.0-1.0
                "delay": 0.0,  # milliseconds
                "output": 0.8,  # 0.0-1.0
                "cross_feedback": 0.2,  # 0.0-1.0
                "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms delays
                "lfo_phases": [0.0, 0.0],
                "lfo_rates": [1.0, 0.5],
                "lfo_depths": [0.5, 0.3],
                "write_indices": [0, 0],
                "feedback_buffers": [0.0, 0.0]
            }

            # Variation effect parameters
            self._temp_state["variation_params"] = {
                "type": 0,  # Delay
                "parameter1": 0.5,  # 0.0-1.0
                "parameter2": 0.5,  # 0.0-1.0
                "parameter3": 0.5,  # 0.0-1.0
                "parameter4": 0.5,  # 0.0-1.0
                "level": 0.5,  # 0.0-1.0
                "bypass": False  # true/false
            }

            # Equalizer parameters
            self._temp_state["equalizer_params"] = {
                "low_gain": 0.0,  # dB
                "mid_gain": 0.0,  # dB
                "high_gain": 0.0,  # dB
                "mid_freq": 1000.0,  # Hz
                "q_factor": 1.0  # Q-factor
            }

            # Routing parameters
            self._temp_state["routing_params"] = {
                "system_effect_order": [0, 1, 2],  # 0=reverb, 1=chorus, 2=variation
                "insertion_effect_order": [0],  # 0=insertion effect
                "parallel_routing": False,  # Parallel routing
                "reverb_to_chorus": 0.0,  # Reverb to chorus
                "chorus_to_variation": 0.0  # Chorus to variation
            }

            # Global effect parameters
            self._temp_state["global_effect_params"] = {
                "reverb_send": 0.5,  # Reverb send level
                "chorus_send": 0.3,  # Chorus send level
                "variation_send": 0.2,  # Variation send level
                "stereo_width": 0.5,  # Stereo width (0.0-1.0)
                "master_level": 0.8,  # Master level
                "bypass_all": False  # Bypass all effects
            }

            # Channel parameters
            for i in range(NUM_CHANNELS):
                self._temp_state["channel_params"][i] = {
                    "reverb_send": 0.5,  # Reverb send level
                    "chorus_send": 0.3,  # Chorus send level
                    "variation_send": 0.2,  # Variation send level
                    "insertion_send": 1.0,  # Insertion send level
                    "muted": False,  # Channel mute
                    "soloed": False,  # Channel solo
                    "pan": 0.5,  # Pan (0.0-1.0)
                    "volume": 1.0,  # Volume (0.0-1.0)
                    "expression": 1.0,  # Expression (0.0-1.0)
                    # XG Channel Parameters (XG defaults)
                    "pitch_bend_range": 2,  # Default XG pitch bend range
                    "fine_tuning": 0.0,  # No fine tuning
                    "coarse_tuning": 0,  # No coarse tuning
                    "tuning_program": 0,  # Default tuning program
                    "tuning_bank": 0,  # Default tuning bank
                    "modulation_depth": 64,  # Default modulation depth
                    "element_reserve": 0,  # Default element reserve
                    "element_assign_mode": 0,  # Default element assign mode
                    "receive_channel": i,  # Default to own channel
                    "insertion_effect": {
                        "enabled": True,
                        "type": 0,  # Off
                        "parameter1": 0.5,  # 0.0-1.0
                        "parameter2": 0.5,  # 0.0-1.0
                        "parameter3": 0.5,  # 0.0-1.0
                        "parameter4": 0.5,  # 0.0-1.0
                        "level": 1.0,  # 0.0-1.0
                        "bypass": False,  # true/false
                        # Extended parameters for Phaser and Flanger
                        "frequency": 1.0,
                        "depth": 0.5,
                        "feedback": 0.3,
                        "lfo_waveform": 0,  # 0=sine, 1=triangle, 2=square, 3=sawtooth
                        # Additional parameters for all effect types
                        "drive": 0.5,
                        "tone": 0.5,
                        "bias": 0.5,
                        "threshold": 0.5,
                        "ratio": 0.5,
                        "attack": 0.1,
                        "release": 0.5,
                        "reduction": 0.5,
                        "hold": 0.1,
                        "sensitivity": 0.5,
                        "resonance": 0.5,
                        "mode": 0,
                        "bass": 0.5,
                        "treble": 0.5,
                        "enhance": 0.5,
                        "speed": 1.0,
                        "balance": 0.5,
                        "accel": 0.5,
                        "rate": 1.0,
                        "waveform": 0,
                        "phase": 0.0,
                        "bands": 8,
                        "formant": 0.5,
                        "intervals": 12,
                        "mix": 0.5,
                        "shift": 0.0,
                        "cutoff": 1000.0,
                        "manual_position": 0.5,
                        "lfo_rate": 1.0,
                        "lfo_depth": 0.5,
                        "time": 0.5,
                        "stereo": 0.5,
                        "decay": 0.5,
                        "hf_damping": 0.5
                    },
                    "variation_params": {
                        "type": 0,  # Delay
                        "parameter1": 0.5,  # 0.0-1.0
                        "parameter2": 0.5,  # 0.0-1.0
                        "parameter3": 0.5,  # 0.0-1.0
                        "parameter4": 0.5,  # 0.0-1.0
                        "level": 0.5,  # 0.0-1.0
                        "bypass": False  # true/false
                    }
                }

            # Apply the temporary state
            self.apply_temp_state()

    def get_channel_insertion_effect(self, channel: int) -> Dict[str, Any]:
        """Get insertion effect parameters for a channel"""
        with self.state_lock:
            if 0 <= channel < NUM_CHANNELS:
                return self._current_state["channel_params"][channel]["insertion_effect"].copy()
        return self._create_insertion_effect_params()

    def get_active_channels(self, state: Dict[str, Any]) -> List[int]:
        """Get list of active channels (considering mute/solo)"""
        soloed_channels = [i for i in range(NUM_CHANNELS)
                          if state["channel_params"][i].get("soloed", False)]

        if soloed_channels:
            return soloed_channels

        return [i for i in range(NUM_CHANNELS)
               if not state["channel_params"][i].get("muted", False)]
