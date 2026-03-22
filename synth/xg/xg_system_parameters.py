"""
XG System Parameters (NRPN MSB 1-2)

Implements XG system effect parameters for reverb and chorus.
Handles NRPN MSB 1 (System Reverb) and MSB 2 (System Chorus/Variation).

XG Specification Compliance:
- MSB 1: System Reverb parameters (Type, Time, HfDamp, Balance, Level)
- MSB 2: System Chorus parameters (Type, LFO Freq, Depth, Feedback, Send Level)
- MSB 2: System Variation parameters (Type-dependent parameters)

Copyright (c) 2025
"""

from __future__ import annotations

import threading
from typing import Any


class XGSystemEffectParameters:
    """
    XG System Effect Parameters (NRPN MSB 1-2)

    Handles XG system effect parameters for professional effect control.
    Provides complete system reverb and chorus parameter management.

    Key Features:
    - System reverb with 10 XG reverb types (Hall1/2, Room1/2, etc.)
    - System chorus with 5 XG chorus types (Chorus1-5)
    - System variation effects with 42 XG variation types
    - Real-time parameter updates during playback
    - Thread-safe operation for live performance
    """

    # XG Reverb Types (MSB 1 LSB 0)
    XG_REVERB_TYPES = {
        0x00: {"name": "No Effect", "time": 0.0, "hf_damp": 0.0},
        0x01: {"name": "Hall 1", "time": 1.8, "hf_damp": 0.5},
        0x02: {"name": "Hall 2", "time": 2.4, "hf_damp": 0.4},
        0x03: {"name": "Room 1", "time": 0.8, "hf_damp": 0.6},
        0x04: {"name": "Room 2", "time": 1.2, "hf_damp": 0.5},
        0x05: {"name": "Room 3", "time": 1.6, "hf_damp": 0.4},
        0x06: {"name": "Stage 1", "time": 2.2, "hf_damp": 0.3},
        0x07: {"name": "Stage 2", "time": 3.1, "hf_damp": 0.2},
        0x08: {"name": "Plate", "time": 2.8, "hf_damp": 0.1},
        0x09: {"name": "White Room", "time": 1.5, "hf_damp": 0.8},
        0x0A: {"name": "Tunnel", "time": 4.2, "hf_damp": 0.0},
        0x0B: {"name": "Basement", "time": 3.8, "hf_damp": 0.2},
        0x0C: {"name": "Canyon", "time": 5.5, "hf_damp": 0.0},
    }

    # XG Chorus Types (MSB 2 LSB 0)
    XG_CHORUS_TYPES = {
        0x40: {"name": "Chorus 1", "lfo_freq": 0.4, "depth": 0.6, "feedback": 0.3},
        0x41: {"name": "Chorus 2", "lfo_freq": 0.5, "depth": 0.5, "feedback": 0.2},
        0x42: {"name": "Chorus 3", "lfo_freq": 0.6, "depth": 0.4, "feedback": 0.1},
        0x43: {"name": "Chorus 4", "lfo_freq": 0.7, "depth": 0.3, "feedback": 0.0},
        0x44: {"name": "Chorus 5", "lfo_freq": 0.8, "depth": 0.2, "feedback": -0.1},
        0x45: {"name": "Celeste 1", "lfo_freq": 0.3, "depth": 0.8, "feedback": 0.4},
        0x46: {"name": "Celeste 2", "lfo_freq": 0.4, "depth": 0.7, "feedback": 0.3},
        0x47: {"name": "Celeste 3", "lfo_freq": 0.5, "depth": 0.6, "feedback": 0.2},
        0x48: {"name": "Celeste 4", "lfo_freq": 0.6, "depth": 0.5, "feedback": 0.1},
        0x49: {"name": "Celeste 5", "lfo_freq": 0.7, "depth": 0.4, "feedback": 0.0},
        0x4A: {"name": "Flanger 1", "lfo_freq": 0.2, "depth": 0.9, "feedback": 0.5},
        0x4B: {"name": "Flanger 2", "lfo_freq": 0.3, "depth": 0.8, "feedback": 0.4},
        0x4C: {"name": "Flanger 3", "lfo_freq": 0.4, "depth": 0.7, "feedback": 0.3},
        0x4D: {"name": "Flanger 4", "lfo_freq": 0.5, "depth": 0.6, "feedback": 0.2},
        0x4E: {"name": "Flanger 5", "lfo_freq": 0.6, "depth": 0.5, "feedback": 0.1},
        0x4F: {"name": "Flanger 6", "lfo_freq": 0.7, "depth": 0.4, "feedback": 0.0},
        0x50: {"name": "Symphonic 1", "lfo_freq": 0.1, "depth": 1.0, "feedback": 0.6},
        0x51: {"name": "Symphonic 2", "lfo_freq": 0.2, "depth": 0.9, "feedback": 0.5},
    }

    # XG Variation Types (MSB 2 LSB 0) - First 32 of 42 total
    XG_VARIATION_TYPES = {
        # Delay types (0x00-0x0F)
        0x00: {
            "name": "Delay L,R",
            "type": "delay",
            "params": {"delay_time": 0.3, "feedback": 0.2, "level": 0.5},
        },
        0x01: {
            "name": "Delay L,C,R",
            "type": "delay",
            "params": {"delay_time": 0.4, "feedback": 0.3, "level": 0.5},
        },
        0x02: {
            "name": "Cross Delay",
            "type": "delay",
            "params": {"delay_time": 0.5, "feedback": 0.4, "level": 0.5},
        },
        0x03: {
            "name": "Echo",
            "type": "delay",
            "params": {"delay_time": 0.8, "feedback": 0.6, "level": 0.4},
        },
        # Chorus types (0x10-0x1F)
        0x10: {
            "name": "Chorus 1",
            "type": "chorus",
            "params": {"lfo_freq": 0.4, "depth": 0.6, "feedback": 0.3},
        },
        0x11: {
            "name": "Chorus 2",
            "type": "chorus",
            "params": {"lfo_freq": 0.5, "depth": 0.5, "feedback": 0.2},
        },
        0x12: {
            "name": "Chorus 3",
            "type": "chorus",
            "params": {"lfo_freq": 0.6, "depth": 0.4, "feedback": 0.1},
        },
        0x13: {
            "name": "Chorus 4",
            "type": "chorus",
            "params": {"lfo_freq": 0.7, "depth": 0.3, "feedback": 0.0},
        },
        # Flanger types (0x20-0x2F)
        0x20: {
            "name": "Flanger 1",
            "type": "flanger",
            "params": {"lfo_freq": 0.2, "depth": 0.9, "feedback": 0.5},
        },
        0x21: {
            "name": "Flanger 2",
            "type": "flanger",
            "params": {"lfo_freq": 0.3, "depth": 0.8, "feedback": 0.4},
        },
        0x22: {
            "name": "Flanger 3",
            "type": "flanger",
            "params": {"lfo_freq": 0.4, "depth": 0.7, "feedback": 0.3},
        },
        0x23: {
            "name": "Flanger 4",
            "type": "flanger",
            "params": {"lfo_freq": 0.5, "depth": 0.6, "feedback": 0.2},
        },
        # Distortion types (0x30-0x3F)
        0x30: {
            "name": "Distortion 1",
            "type": "distortion",
            "params": {"drive": 0.3, "tone": 0.5, "level": 0.7},
        },
        0x31: {
            "name": "Distortion 2",
            "type": "distortion",
            "params": {"drive": 0.5, "tone": 0.4, "level": 0.6},
        },
        0x32: {
            "name": "Distortion 3",
            "type": "distortion",
            "params": {"drive": 0.7, "tone": 0.3, "level": 0.5},
        },
        0x33: {
            "name": "Overdrive 1",
            "type": "distortion",
            "params": {"drive": 0.4, "tone": 0.6, "level": 0.8},
        },
    }

    def __init__(self):
        """
        Initialize XG System Effect Parameters
        """
        self.lock = threading.RLock()

        # Current system effect parameters
        self.system_reverb = self._create_default_reverb()
        self.system_chorus = self._create_default_chorus()
        self.system_variation = self._create_default_variation()

        # Parameter change callback
        self.parameter_change_callback = None

        print("🎹 XG SYSTEM PARAMETERS: Initialized")
        print("   Reverb, Chorus, and Variation effect parameters ready")

    def _create_default_reverb(self) -> dict[str, Any]:
        """Create default XG reverb parameters."""
        return {
            "type": 0x01,  # Hall 1
            "time": 1.8,  # seconds (0.3-30.0)
            "hf_damping": 0.5,  # 0.0-1.0
            "balance": 0.5,  # 0.0-1.0 (wet/dry)
            "level": 0.4,  # 0.0-1.0
            "name": "Hall 1",
        }

    def _create_default_chorus(self) -> dict[str, Any]:
        """Create default XG chorus parameters."""
        return {
            "type": 0x41,  # Chorus 1
            "lfo_freq": 0.4,  # Hz (0.0-39.7)
            "depth": 0.6,  # 0.0-1.0
            "feedback": 0.3,  # -1.0 to 1.0
            "send_level": 0.3,  # 0.0-1.0
            "name": "Chorus 1",
        }

    def _create_default_variation(self) -> dict[str, Any]:
        """Create default XG variation parameters."""
        return {
            "type": 0x10,  # Chorus 1
            "params": {"lfo_freq": 0.4, "depth": 0.6, "feedback": 0.3},
            "name": "Chorus 1",
        }

    def handle_nrpn_msb1(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 1 (System Reverb) messages.

        Args:
            lsb: NRPN LSB value (0-127)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            # Convert 14-bit value to 7-bit for most parameters
            value_7bit = data_value >> 7

            if lsb == 0:  # Reverb Type
                if data_value in self.XG_REVERB_TYPES:
                    reverb_info = self.XG_REVERB_TYPES[data_value]
                    self.system_reverb.update(
                        {
                            "type": data_value,
                            "name": reverb_info["name"],
                            "time": reverb_info["time"],
                            "hf_damping": reverb_info["hf_damp"],
                        }
                    )
                    self._notify_parameter_change("reverb_type", data_value)
                    return True

            elif lsb == 1:  # Reverb Time
                # Convert 0-16383 to 0.3-30.0 seconds
                time_seconds = 0.3 + (data_value / 16383.0) * 29.7
                self.system_reverb["time"] = time_seconds
                self._notify_parameter_change("reverb_time", time_seconds)
                return True

            elif lsb == 2:  # Reverb HfDamp
                # Convert 0-16383 to 0.0-1.0
                hf_damping = data_value / 16383.0
                self.system_reverb["hf_damping"] = hf_damping
                self._notify_parameter_change("reverb_hf_damping", hf_damping)
                return True

            elif lsb == 3:  # Reverb Balance
                # Convert 0-16383 to 0.0-1.0 (wet/dry mix)
                balance = data_value / 16383.0
                self.system_reverb["balance"] = balance
                self._notify_parameter_change("reverb_balance", balance)
                return True

            elif lsb == 4:  # Reverb Level
                # Convert 0-16383 to 0.0-1.0
                level = data_value / 16383.0
                self.system_reverb["level"] = level
                self._notify_parameter_change("reverb_level", level)
                return True

        return False

    def handle_nrpn_msb2(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 2 (System Chorus/Variation) messages.

        Args:
            lsb: NRPN LSB value (0-127)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            # Convert 14-bit value to 7-bit for most parameters
            value_7bit = data_value >> 7

            if lsb == 0:  # Chorus/Variation Type
                # First check if it's a chorus type (0x40-0x51)
                if data_value in self.XG_CHORUS_TYPES:
                    chorus_info = self.XG_CHORUS_TYPES[data_value]
                    self.system_chorus.update(
                        {
                            "type": data_value,
                            "name": chorus_info["name"],
                            "lfo_freq": chorus_info["lfo_freq"],
                            "depth": chorus_info["depth"],
                            "feedback": chorus_info["feedback"],
                        }
                    )
                    self._notify_parameter_change("chorus_type", data_value)
                    return True

                # Check if it's a variation type (0x00-0x3F)
                elif data_value in self.XG_VARIATION_TYPES:
                    variation_info = self.XG_VARIATION_TYPES[data_value]
                    self.system_variation.update(
                        {
                            "type": data_value,
                            "name": variation_info["name"],
                            "params": variation_info["params"].copy(),
                        }
                    )
                    self._notify_parameter_change("variation_type", data_value)
                    return True

            elif lsb == 1:  # Chorus LFO Frequency
                # Convert 0-16383 to 0.0-39.7 Hz
                lfo_freq = (data_value / 16383.0) * 39.7
                self.system_chorus["lfo_freq"] = lfo_freq
                self._notify_parameter_change("chorus_lfo_freq", lfo_freq)
                return True

            elif lsb == 2:  # Chorus Depth
                # Convert 0-16383 to 0.0-1.0
                depth = data_value / 16383.0
                self.system_chorus["depth"] = depth
                self._notify_parameter_change("chorus_depth", depth)
                return True

            elif lsb == 3:  # Chorus Feedback
                # Convert 0-16383 to -1.0 to 1.0
                feedback = (data_value / 16383.0) * 2.0 - 1.0
                self.system_chorus["feedback"] = feedback
                self._notify_parameter_change("chorus_feedback", feedback)
                return True

            elif lsb == 4:  # Chorus Send Level
                # Convert 0-16383 to 0.0-1.0
                send_level = data_value / 16383.0
                self.system_chorus["send_level"] = send_level
                self._notify_parameter_change("chorus_send_level", send_level)
                return True

            # Handle variation-specific parameters (LSB 5-127)
            # These depend on the current variation type
            elif 5 <= lsb <= 127:
                return self._handle_variation_parameter(lsb, data_value)

        return False

    def _handle_variation_parameter(self, lsb: int, data_value: int) -> bool:
        """
        Handle variation effect specific parameters.

        Args:
            lsb: NRPN LSB value
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        variation_type = self.system_variation["type"]
        var_info = self.XG_VARIATION_TYPES.get(variation_type, {})

        if var_info.get("type") == "delay":
            return self._handle_delay_variation(lsb, data_value, var_info)
        elif var_info.get("type") == "chorus":
            return self._handle_chorus_variation(lsb, data_value, var_info)
        elif var_info.get("type") == "flanger":
            return self._handle_flanger_variation(lsb, data_value, var_info)
        elif var_info.get("type") == "distortion":
            return self._handle_distortion_variation(lsb, data_value, var_info)

        return False

    def _handle_delay_variation(self, lsb: int, data_value: int, var_info: dict) -> bool:
        """Handle delay variation parameters."""
        if lsb == 5:  # Delay Time
            delay_time = 0.001 + (data_value / 16383.0) * 4.999  # 1ms-5s
            self.system_variation["params"]["delay_time"] = delay_time
            self._notify_parameter_change("variation_delay_time", delay_time)
            return True
        elif lsb == 6:  # Feedback
            feedback = data_value / 16383.0  # 0.0-1.0
            self.system_variation["params"]["feedback"] = feedback
            self._notify_parameter_change("variation_feedback", feedback)
            return True
        elif lsb == 7:  # Level
            level = data_value / 16383.0  # 0.0-1.0
            self.system_variation["params"]["level"] = level
            self._notify_parameter_change("variation_level", level)
            return True
        return False

    def _handle_chorus_variation(self, lsb: int, data_value: int, var_info: dict) -> bool:
        """Handle chorus variation parameters."""
        if lsb == 5:  # LFO Frequency
            lfo_freq = (data_value / 16383.0) * 39.7
            self.system_variation["params"]["lfo_freq"] = lfo_freq
            self._notify_parameter_change("variation_lfo_freq", lfo_freq)
            return True
        elif lsb == 6:  # Depth
            depth = data_value / 16383.0
            self.system_variation["params"]["depth"] = depth
            self._notify_parameter_change("variation_depth", depth)
            return True
        elif lsb == 7:  # Feedback
            feedback = (data_value / 16383.0) * 2.0 - 1.0
            self.system_variation["params"]["feedback"] = feedback
            self._notify_parameter_change("variation_feedback", feedback)
            return True
        return False

    def _handle_flanger_variation(self, lsb: int, data_value: int, var_info: dict) -> bool:
        """Handle flanger variation parameters."""
        if lsb == 5:  # LFO Frequency
            lfo_freq = (data_value / 16383.0) * 39.7
            self.system_variation["params"]["lfo_freq"] = lfo_freq
            self._notify_parameter_change("variation_lfo_freq", lfo_freq)
            return True
        elif lsb == 6:  # Depth
            depth = data_value / 16383.0
            self.system_variation["params"]["depth"] = depth
            self._notify_parameter_change("variation_depth", depth)
            return True
        elif lsb == 7:  # Feedback
            feedback = (data_value / 16383.0) * 2.0 - 1.0
            self.system_variation["params"]["feedback"] = feedback
            self._notify_parameter_change("variation_feedback", feedback)
            return True
        return False

    def _handle_distortion_variation(self, lsb: int, data_value: int, var_info: dict) -> bool:
        """Handle distortion variation parameters."""
        if lsb == 5:  # Drive
            drive = data_value / 16383.0
            self.system_variation["params"]["drive"] = drive
            self._notify_parameter_change("variation_drive", drive)
            return True
        elif lsb == 6:  # Tone
            tone = data_value / 16383.0
            self.system_variation["params"]["tone"] = tone
            self._notify_parameter_change("variation_tone", tone)
            return True
        elif lsb == 7:  # Level
            level = data_value / 16383.0
            self.system_variation["params"]["level"] = level
            self._notify_parameter_change("variation_level", level)
            return True
        return False

    def _notify_parameter_change(self, parameter_name: str, value: Any):
        """Notify parameter change callback."""
        if self.parameter_change_callback:
            self.parameter_change_callback(parameter_name, value)

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback

    def get_system_reverb_parameters(self) -> dict[str, Any]:
        """Get current system reverb parameters."""
        with self.lock:
            return self.system_reverb.copy()

    def get_system_chorus_parameters(self) -> dict[str, Any]:
        """Get current system chorus parameters."""
        with self.lock:
            return self.system_chorus.copy()

    def get_system_variation_parameters(self) -> dict[str, Any]:
        """Get current system variation parameters."""
        with self.lock:
            return self.system_variation.copy()

    def get_reverb_type_name(self, type_value: int) -> str:
        """Get reverb type name from type value."""
        return self.XG_REVERB_TYPES.get(type_value, {}).get("name", f"Unknown ({type_value:02X})")

    def get_chorus_type_name(self, type_value: int) -> str:
        """Get chorus type name from type value."""
        return self.XG_CHORUS_TYPES.get(type_value, {}).get("name", f"Unknown ({type_value:02X})")

    def get_variation_type_name(self, type_value: int) -> str:
        """Get variation type name from type value."""
        return self.XG_VARIATION_TYPES.get(type_value, {}).get(
            "name", f"Unknown ({type_value:02X})"
        )

    def get_effect_parameter_ranges(self) -> dict[str, dict[str, Any]]:
        """
        Get parameter ranges for all XG system effects.

        Returns:
            Dictionary with parameter ranges for validation
        """
        return {
            "reverb": {
                "type": {"min": 0x00, "max": 0x0C, "default": 0x01},
                "time": {"min": 0.3, "max": 30.0, "default": 1.8},
                "hf_damping": {"min": 0.0, "max": 1.0, "default": 0.5},
                "balance": {"min": 0.0, "max": 1.0, "default": 0.5},
                "level": {"min": 0.0, "max": 1.0, "default": 0.4},
            },
            "chorus": {
                "type": {"min": 0x40, "max": 0x51, "default": 0x41},
                "lfo_freq": {"min": 0.0, "max": 39.7, "default": 0.4},
                "depth": {"min": 0.0, "max": 1.0, "default": 0.6},
                "feedback": {"min": -1.0, "max": 1.0, "default": 0.3},
                "send_level": {"min": 0.0, "max": 1.0, "default": 0.3},
            },
            "variation": {
                "type": {"min": 0x00, "max": 0x3F, "default": 0x10},
                # Parameter ranges depend on variation type
            },
        }

    def reset_to_xg_defaults(self):
        """Reset all system effect parameters to XG defaults."""
        with self.lock:
            self.system_reverb = self._create_default_reverb()
            self.system_chorus = self._create_default_chorus()
            self.system_variation = self._create_default_variation()

        print("🎹 XG SYSTEM PARAMETERS: Reset to XG defaults")

    def export_parameters(self) -> dict[str, Any]:
        """Export all system effect parameters."""
        with self.lock:
            return {
                "reverb": self.system_reverb.copy(),
                "chorus": self.system_chorus.copy(),
                "variation": self.system_variation.copy(),
                "version": "1.0",
            }

    def import_parameters(self, params: dict[str, Any]) -> bool:
        """Import system effect parameters."""
        try:
            with self.lock:
                if "reverb" in params:
                    self.system_reverb.update(params["reverb"])
                if "chorus" in params:
                    self.system_chorus.update(params["chorus"])
                if "variation" in params:
                    self.system_variation.update(params["variation"])
                return True
        except Exception as e:
            print(f"❌ XG SYSTEM PARAMETERS: Import failed - {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get system effect parameters status."""
        with self.lock:
            return {
                "reverb_active": self.system_reverb["level"] > 0.0,
                "chorus_active": self.system_chorus["send_level"] > 0.0,
                "variation_active": self.system_variation.get("params", {}).get("level", 0.0) > 0.0,
                "reverb_type": self.system_reverb["name"],
                "chorus_type": self.system_chorus["name"],
                "variation_type": self.system_variation["name"],
                "parameter_count": 3,  # reverb, chorus, variation
            }
