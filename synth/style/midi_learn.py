"""
MIDI Learn System for Style Engine

Provides MIDI controller learning functionality to map physical controllers
to style engine parameters. Supports real-time learning, multiple curves,
and persistent mapping storage.

Features:
- MIDI learn mode for any style parameter
- Multiple response curves
- Value range mapping
- Save/load mappings
- Callback-based parameter updates
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
from enum import Enum
import threading
import json
import time
import numpy as np


class LearnTargetType(Enum):
    """Types of parameters that can be learned."""

    # Style transport controls
    STYLE_START_STOP = "style_start_stop"
    STYLE_PLAY_PAUSE = "style_play_pause"
    STYLE_STOP = "style_stop"
    
    # Section controls
    STYLE_SECTION_NEXT = "style_section_next"
    STYLE_SECTION_PREV = "style_section_prev"
    STYLE_SECTION_A = "style_section_a"
    STYLE_SECTION_B = "style_section_b"
    STYLE_SECTION_C = "style_section_c"
    STYLE_SECTION_D = "style_section_d"
    
    # Fill and transition controls
    STYLE_FILL = "style_fill"
    STYLE_BREAK = "style_break"
    STYLE_INTRO = "style_intro"
    STYLE_ENDING = "style_ending"
    
    # Continuous parameters
    STYLE_TEMPO = "style_tempo"
    STYLE_DYNAMICS = "style_dynamics"
    STYLE_VOLUME = "style_volume"
    STYLE_TEMPO_FINE = "style_tempo_fine"
    
    # Voice/OTS controls
    OTS_1 = "ots_1"
    OTS_2 = "ots_2"
    OTS_3 = "ots_3"
    OTS_4 = "ots_4"
    OTS_5 = "ots_5"
    OTS_6 = "ots_6"
    OTS_7 = "ots_7"
    OTS_8 = "ots_8"
    OTS_NEXT = "ots_next"
    OTS_PREV = "ots_prev"
    
    # Registration controls
    REGISTRATION_1 = "registration_1"
    REGISTRATION_2 = "registration_2"
    REGISTRATION_3 = "registration_3"
    REGISTRATION_4 = "registration_4"
    REGISTRATION_NEXT = "registration_next"
    REGISTRATION_PREV = "registration_prev"
    
    # Effect controls
    EFFECT_REVERB = "effect_reverb"
    EFFECT_CHORUS = "effect_chorus"
    EFFECT_VARIATION = "effect_variation"
    
    # Advanced controls
    STYLE_OCTAVE = "style_octave"
    STYLE_TRANSPOSE = "style_transpose"
    STYLE_SYNC_START = "style_sync_start"
    STYLE_ACMP_ON_OFF = "style_acmp_on_off"
    STYLE_SPLIT_POINT = "style_split_point"


class MIDILearnMapping:
    """
    Single MIDI learn mapping entry.
    
    Attributes:
        cc_number: MIDI CC number (0-127)
        channel: MIDI channel (0-15)
        target_type: Type of parameter being controlled
        target_param: Specific parameter name
        min_val: Minimum output value
        max_val: Maximum output value
        curve: Response curve (linear, exponential, logarithmic, sine)
        label: Human-readable label
        momentary: If True, returns to default on release
        snap_to_grid: Snap value to grid increments (0 = disabled)
        default_value: Default/center value for momentary controls
        inverted: If True, inverts the CC value
        channel_specific: If True, only responds to specific channel
    """

    def __init__(
        self,
        cc_number: int,
        channel: int,
        target_type: LearnTargetType,
        target_param: str,
        min_val: float = 0.0,
        max_val: float = 1.0,
        curve: str = "linear",
        label: str = "",
        momentary: bool = False,
        snap_to_grid: float = 0.0,
        default_value: float = 0.5,
        inverted: bool = False,
        channel_specific: bool = True,
    ):
        self.cc_number = cc_number
        self.channel = channel
        self.target_type = target_type
        self.target_param = target_param
        self.min_val = min_val
        self.max_val = max_val
        self.curve = curve
        self.label = label
        self.momentary = momentary
        self.snap_to_grid = snap_to_grid
        self.default_value = default_value
        self.inverted = inverted
        self.channel_specific = channel_specific
        self.last_value: float = default_value
        self.last_raw_value: int = 0

    def process_value(self, raw_value: int) -> float:
        """
        Process raw MIDI value through curve and scaling.
        
        Args:
            raw_value: Raw MIDI CC value (0-127)
            
        Returns:
            Processed output value
        """
        # Handle inversion
        if self.inverted:
            raw_value = 127 - raw_value
        
        self.last_raw_value = raw_value
        
        # Normalize to 0-1
        normalized = raw_value / 127.0
        
        # Apply curve
        curve_func = MIDILearn.CURVES.get(self.curve, MIDILearn.CURVES["linear"])
        processed = curve_func(normalized)
        
        # Scale to output range
        mapped_value = self.min_val + processed * (self.max_val - self.min_val)
        
        # Apply snap-to-grid if enabled
        if self.snap_to_grid > 0:
            grid_steps = round(mapped_value / self.snap_to_grid)
            mapped_value = grid_steps * self.snap_to_grid
            mapped_value = max(self.min_val, min(self.max_val, mapped_value))
        else:
            mapped_value = max(self.min_val, min(self.max_val, mapped_value))
        
        self.last_value = mapped_value
        return mapped_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "cc_number": self.cc_number,
            "channel": self.channel,
            "target_type": self.target_type.value,
            "target_param": self.target_param,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "curve": self.curve,
            "label": self.label,
            "momentary": self.momentary,
            "snap_to_grid": self.snap_to_grid,
            "default_value": self.default_value,
            "inverted": self.inverted,
            "channel_specific": self.channel_specific,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MIDILearnMapping:
        return cls(
            cc_number=data["cc_number"],
            channel=data["channel"],
            target_type=LearnTargetType(data["target_type"]),
            target_param=data["target_param"],
            min_val=data.get("min_val", 0.0),
            max_val=data.get("max_val", 1.0),
            curve=data.get("curve", "linear"),
            label=data.get("label", ""),
            momentary=data.get("momentary", False),
            snap_to_grid=data.get("snap_to_grid", 0.0),
            default_value=data.get("default_value", 0.5),
            inverted=data.get("inverted", False),
            channel_specific=data.get("channel_specific", True),
        )


class MIDILearn:
    """
    MIDI Learn System for Style Engine

    Provides controller mapping with learn functionality.
    
    Features:
    - Real-time MIDI learn mode
    - 30+ mappable targets
    - Multiple response curves (linear, exponential, logarithmic, sine)
    - Value range mapping and scaling
    - Snap-to-grid for discrete values
    - Momentary switch support
    - Persistent mapping storage (JSON)
    - Callback-based parameter updates
    - Default mapping presets
    """

    CURVES = {
        "linear": lambda x: x,
        "exponential": lambda x: x * x,
        "logarithmic": lambda x: x**0.5 if x > 0 else 0,
        "sine": lambda x: (1.0 + np.sin((x - 0.5) * np.pi)) / 2.0,
        "inverse_sine": lambda x: np.arcsin(2 * x - 1) / np.pi + 0.5 if 0 <= x <= 1 else x,
    }

    # Default mapping presets for common MIDI controllers
    DEFAULT_MAPPINGS = {
        "korg_nanokontrol2": {
            # Sliders
            (1, 0): MIDILearnMapping(1, 0, LearnTargetType.STYLE_VOLUME, "master_volume"),
            (1, 1): MIDILearnMapping(1, 1, LearnTargetType.STYLE_TEMPO, "tempo", 40, 280),
            (1, 2): MIDILearnMapping(1, 2, LearnTargetType.STYLE_DYNAMICS, "dynamics", 0, 127),
            # Knobs
            (16, 0): MIDILearnMapping(16, 0, LearnTargetType.EFFECT_REVERB, "reverb", 0, 127),
            (17, 0): MIDILearnMapping(17, 0, LearnTargetType.EFFECT_CHORUS, "chorus", 0, 127),
        },
        "akai_apc_mini": {
            # Faders
            (48, 0): MIDILearnMapping(48, 0, LearnTargetType.OTS_1, "ots_1"),
            (49, 0): MIDILearnMapping(49, 0, LearnTargetType.OTS_2, "ots_2"),
            (50, 0): MIDILearnMapping(50, 0, LearnTargetType.OTS_3, "ots_3"),
            (51, 0): MIDILearnMapping(51, 0, LearnTargetType.OTS_4, "ots_4"),
        },
    }

    def __init__(self):
        self.lock = threading.RLock()
        self.mappings: dict[tuple[int, int], MIDILearnMapping] = {}
        self.pending_learn: tuple[LearnTargetType, str] | None = None
        self.callbacks: dict[LearnTargetType, list[Callable]] = {}
        self.learn_enabled = False
        
        # Active values for momentary controls
        self.active_values: dict[tuple[int, int], float] = {}
        
        # Learn timeout (auto-cancel after N seconds)
        self.learn_timeout: float = 10.0
        self.learn_start_time: float | None = None
        
        # Mapping groups (for organizing by function)
        self.groups: dict[str, list[tuple[int, int]]] = {
            "transport": [],
            "sections": [],
            "fills": [],
            "continuous": [],
            "ots": [],
            "registration": [],
            "effects": [],
        }

    def start_learn(self, target_type: LearnTargetType, target_param: str = "", 
                    timeout: float | None = None) -> None:
        """
        Start learn mode for a specific target.
        
        Args:
            target_type: Type of parameter to learn
            target_param: Specific parameter name
            timeout: Optional timeout in seconds (overrides default)
        """
        with self.lock:
            self.pending_learn = (target_type, target_param)
            self.learn_enabled = True
            self.learn_start_time = time.time()
            if timeout:
                self.learn_timeout = timeout

    def check_learn_timeout(self) -> bool:
        """Check if learn mode has timed out."""
        if self.learn_enabled and self.learn_start_time:
            if time.time() - self.learn_start_time > self.learn_timeout:
                self.cancel_learn()
                return True
        return False

    def cancel_learn(self) -> None:
        """Cancel pending learn mode."""
        with self.lock:
            self.pending_learn = None
            self.learn_enabled = False
            self.learn_start_time = None

    def process_midi(
        self, cc_number: int, channel: int, value: int
    ) -> dict[str, Any] | None:
        """
        Process incoming MIDI CC message.

        Args:
            cc_number: MIDI CC number
            channel: MIDI channel
            value: CC value (0-127)
            
        Returns:
            Dict with target info and processed value if mapping exists,
            or learn confirmation if in learn mode
        """
        with self.lock:
            key = (cc_number, channel)

            # Check for learn timeout
            self.check_learn_timeout()

            # Handle learn mode
            if self.learn_enabled and self.pending_learn:
                target_type, target_param = self.pending_learn
                mapping = MIDILearnMapping(
                    cc_number=cc_number,
                    channel=channel,
                    target_type=target_type,
                    target_param=target_param,
                )
                self.mappings[key] = mapping
                self._add_to_group(target_type, key)
                self.cancel_learn()
                return {"learned": True, "target": target_type.value, "cc": cc_number, "channel": channel}

            # Process existing mapping
            if key in self.mappings:
                mapping = self.mappings[key]
                
                # Check channel specificity
                if mapping.channel_specific and mapping.channel != channel:
                    return None
                
                processed_value = mapping.process_value(value)
                
                # Handle momentary (return to default when released)
                if mapping.momentary:
                    if value == 0:
                        processed_value = mapping.default_value
                    self.active_values[key] = processed_value

                # Trigger callbacks
                self._trigger_callbacks(mapping.target_type, processed_value, value)

                return {
                    "target_type": mapping.target_type.value,
                    "target_param": mapping.target_param,
                    "value": processed_value,
                    "raw_value": value,
                    "label": mapping.label,
                }

            return None

    def _add_to_group(self, target_type: LearnTargetType, key: tuple[int, int]) -> None:
        """Add mapping to appropriate group."""
        group_map = {
            LearnTargetType.STYLE_START_STOP: "transport",
            LearnTargetType.STYLE_PLAY_PAUSE: "transport",
            LearnTargetType.STYLE_STOP: "transport",
            LearnTargetType.STYLE_SECTION_NEXT: "sections",
            LearnTargetType.STYLE_SECTION_PREV: "sections",
            LearnTargetType.STYLE_SECTION_A: "sections",
            LearnTargetType.STYLE_SECTION_B: "sections",
            LearnTargetType.STYLE_SECTION_C: "sections",
            LearnTargetType.STYLE_SECTION_D: "sections",
            LearnTargetType.STYLE_FILL: "fills",
            LearnTargetType.STYLE_BREAK: "fills",
            LearnTargetType.STYLE_INTRO: "fills",
            LearnTargetType.STYLE_ENDING: "fills",
            LearnTargetType.STYLE_TEMPO: "continuous",
            LearnTargetType.STYLE_DYNAMICS: "continuous",
            LearnTargetType.STYLE_VOLUME: "continuous",
            LearnTargetType.OTS_1: "ots",
            LearnTargetType.OTS_2: "ots",
            LearnTargetType.OTS_3: "ots",
            LearnTargetType.OTS_4: "ots",
            LearnTargetType.OTS_5: "ots",
            LearnTargetType.OTS_6: "ots",
            LearnTargetType.OTS_7: "ots",
            LearnTargetType.OTS_8: "ots",
            LearnTargetType.REGISTRATION_1: "registration",
            LearnTargetType.REGISTRATION_2: "registration",
            LearnTargetType.EFFECT_REVERB: "effects",
            LearnTargetType.EFFECT_CHORUS: "effects",
        }
        
        group = group_map.get(target_type)
        if group and group in self.groups:
            if key not in self.groups[group]:
                self.groups[group].append(key)

    def _trigger_callbacks(self, target_type: LearnTargetType, 
                          processed_value: float, raw_value: int) -> None:
        """Trigger registered callbacks for a target type."""
        if target_type in self.callbacks:
            for callback in self.callbacks[target_type]:
                try:
                    callback(processed_value, raw_value)
                except Exception:
                    pass  # Don't let callback errors break processing

    def register_callback(
        self, target_type: LearnTargetType, callback: Callable
    ) -> None:
        """Register callback for a target type."""
        with self.lock:
            if target_type not in self.callbacks:
                self.callbacks[target_type] = []
            if callback not in self.callbacks[target_type]:
                self.callbacks[target_type].append(callback)

    def unregister_callback(
        self, target_type: LearnTargetType, callback: Callable
    ) -> bool:
        """Unregister a callback."""
        with self.lock:
            if target_type in self.callbacks and callback in self.callbacks[target_type]:
                self.callbacks[target_type].remove(callback)
                return True
            return False

    def add_mapping(self, mapping: MIDILearnMapping) -> bool:
        """Add a manual mapping."""
        with self.lock:
            key = (mapping.cc_number, mapping.channel)
            if key in self.mappings:
                return False
            self.mappings[key] = mapping
            self._add_to_group(mapping.target_type, key)
            return True

    def remove_mapping(self, cc_number: int, channel: int) -> bool:
        """Remove a mapping."""
        with self.lock:
            key = (cc_number, channel)
            if key in self.mappings:
                # Remove from groups
                for group_keys in self.groups.values():
                    if key in group_keys:
                        group_keys.remove(key)
                del self.mappings[key]
                return True
            return False

    def get_mapping(self, cc_number: int, channel: int) -> MIDILearnMapping | None:
        """Get mapping for a CC."""
        with self.lock:
            return self.mappings.get((cc_number, channel))

    def get_all_mappings(self) -> list[MIDILearnMapping]:
        """Get all mappings."""
        with self.lock:
            return list(self.mappings.values())

    def get_mappings_by_group(self, group: str) -> list[MIDILearnMapping]:
        """Get all mappings in a group."""
        with self.lock:
            if group not in self.groups:
                return []
            return [self.mappings[key] for key in self.groups[group] if key in self.mappings]

    def clear_all_mappings(self) -> None:
        """Clear all mappings."""
        with self.lock:
            self.mappings.clear()
            self.pending_learn = None
            self.learn_enabled = False
            self.active_values.clear()
            for group in self.groups:
                self.groups[group] = []

    def load_default_mappings(self, controller_preset: str) -> bool:
        """
        Load default mappings for a known controller.
        
        Args:
            controller_preset: Name of controller preset
            
        Returns:
            True if preset was found and loaded
        """
        with self.lock:
            if controller_preset not in self.DEFAULT_MAPPINGS:
                return False
            
            preset = self.DEFAULT_MAPPINGS[controller_preset]
            for key, mapping in preset.items():
                self.mappings[key] = mapping
                self._add_to_group(mapping.target_type, key)
            return True

    def export_mappings(self) -> list[dict[str, Any]]:
        """Export all mappings as serializable list."""
        return [m.to_dict() for m in self.mappings.values()]

    def import_mappings(self, data: list[dict[str, Any]]) -> bool:
        """Import mappings from serialized list."""
        try:
            with self.lock:
                self.mappings.clear()
                for group in self.groups:
                    self.groups[group] = []
                    
                for item in data:
                    mapping = MIDILearnMapping.from_dict(item)
                    self.mappings[(mapping.cc_number, mapping.channel)] = mapping
                    self._add_to_group(mapping.target_type, (mapping.cc_number, mapping.channel))
                return True
        except Exception:
            return False

    def save_to_file(self, filepath: str) -> bool:
        """Save mappings to JSON file."""
        try:
            with open(filepath, "w") as f:
                json.dump({
                    "mappings": self.export_mappings(),
                    "groups": {k: list(v) for k, v in self.groups.items()},
                }, f, indent=2)
            return True
        except Exception:
            return False

    def load_from_file(self, filepath: str) -> bool:
        """Load mappings from JSON file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
            
            with self.lock:
                if isinstance(data, list):
                    # Old format (just mappings list)
                    return self.import_mappings(data)
                elif isinstance(data, dict):
                    # New format with groups
                    self.import_mappings(data.get("mappings", []))
                    groups = data.get("groups", {})
                    for group, keys in groups.items():
                        if group in self.groups:
                            self.groups[group] = [tuple(k) for k in keys]
                    return True
            return False
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Get MIDI learn status."""
        with self.lock:
            return {
                "learn_enabled": self.learn_enabled,
                "pending_learn": self.pending_learn[0].value
                if self.pending_learn
                else None,
                "learn_timeout": self.learn_timeout,
                "mapping_count": len(self.mappings),
                "groups": {k: len(v) for k, v in self.groups.items()},
                "mappings": [
                    {
                        "cc": m.cc_number,
                        "ch": m.channel,
                        "target": m.target_type.value,
                        "label": m.label,
                    }
                    for m in self.mappings.values()
                ],
            }
