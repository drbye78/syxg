"""
Jupiter-X Unified Parameter System

Complete parameter management system providing unified access to all
synthesis parameters across GS, Jupiter-X, and advanced features.
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import json
import os
from enum import Enum


class ParameterScope(Enum):
    """Parameter scope definitions."""
    GLOBAL = "global"
    PART = "part"
    ENGINE = "engine"
    EFFECT = "effect"
    ARPEGGIATOR = "arpeggiator"
    MPE = "mpe"


class ParameterType(Enum):
    """Parameter type definitions."""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    STRING = "string"
    MIDI_CC = "midi_cc"
    NRPN = "nrpn"


class ParameterDefinition:
    """Complete parameter definition with metadata."""

    def __init__(self, name: str, scope: ParameterScope, param_type: ParameterType,
                 address: Tuple[int, ...], default_value: Any, min_value: Any = None,
                 max_value: Any = None, enum_values: List[str] = None,
                 unit: str = "", description: str = "", tags: List[str] = None):
        self.name = name
        self.scope = scope
        self.param_type = param_type
        self.address = address  # (scope_id, param_id, sub_id, etc.)
        self.default_value = default_value
        self.min_value = min_value
        self.max_value = max_value
        self.enum_values = enum_values or []
        self.unit = unit
        self.description = description
        self.tags = tags or []

        # Runtime state
        self.current_value = default_value
        self.callbacks: List[Callable] = []
        self.metadata = {}

    def validate_value(self, value: Any) -> bool:
        """Validate parameter value."""
        if self.param_type == ParameterType.BOOL:
            return isinstance(value, bool)
        elif self.param_type == ParameterType.INT:
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
            return True
        elif self.param_type == ParameterType.FLOAT:
            try:
                float(value)
                if self.min_value is not None and value < self.min_value:
                    return False
                if self.max_value is not None and value > self.max_value:
                    return False
                return True
            except (ValueError, TypeError):
                return False
        elif self.param_type == ParameterType.ENUM:
            return value in self.enum_values
        elif self.param_type == ParameterType.STRING:
            return isinstance(value, str)
        return True

    def normalize_value(self, value: Any) -> Any:
        """Normalize value to correct type."""
        if self.param_type == ParameterType.BOOL:
            return bool(value)
        elif self.param_type == ParameterType.INT:
            return int(value)
        elif self.param_type == ParameterType.FLOAT:
            return float(value)
        elif self.param_type == ParameterType.STRING:
            return str(value)
        return value

    def add_callback(self, callback: Callable):
        """Add parameter change callback."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove parameter change callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def notify_callbacks(self, old_value: Any, new_value: Any):
        """Notify all callbacks of parameter change."""
        for callback in self.callbacks:
            try:
                callback(self, old_value, new_value)
            except Exception as e:
                print(f"Parameter callback error for {self.name}: {e}")

    def get_parameter_info(self) -> Dict[str, Any]:
        """Get comprehensive parameter information."""
        return {
            'name': self.name,
            'scope': self.scope.value,
            'type': self.param_type.value,
            'address': self.address,
            'current_value': self.current_value,
            'default_value': self.default_value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'enum_values': self.enum_values,
            'unit': self.unit,
            'description': self.description,
            'tags': self.tags,
            'metadata': self.metadata,
        }


class JupiterXUnifiedParameterSystem:
    """
    Unified Parameter System for Jupiter-X

    Provides centralized parameter management across all synthesis components,
    with MIDI mapping, presets, and real-time control capabilities.
    """

    def __init__(self):
        self.lock = threading.RLock()

        # Parameter registry
        self.parameters: Dict[str, ParameterDefinition] = {}
        self.parameters_by_address: Dict[Tuple[int, ...], ParameterDefinition] = {}
        self.parameters_by_scope: Dict[ParameterScope, Dict[str, ParameterDefinition]] = {
            scope: {} for scope in ParameterScope
        }

        # MIDI mappings
        self.cc_mappings: Dict[Tuple[int, int], str] = {}  # (channel, cc) -> param_name
        self.nrpn_mappings: Dict[Tuple[int, int], str] = {}  # (msb, lsb) -> param_name

        # Presets and banks
        self.presets: Dict[str, Dict[str, Any]] = {}
        self.current_preset = "default"
        self.preset_banks: Dict[str, List[str]] = {}

        # Component references (set during initialization)
        self.component_manager = None
        self.arpeggiator = None
        self.mpe_manager = None
        self.effects_coordinator = None

        # Initialize parameter registry
        self._initialize_parameter_registry()

        print("🎛️ Jupiter-X Unified Parameter System: Initialized")

    def _initialize_parameter_registry(self):
        """Initialize comprehensive parameter registry."""
        with self.lock:
            # ===== SYSTEM PARAMETERS =====
            self._add_parameter(ParameterDefinition(
                "master_volume", ParameterScope.GLOBAL, ParameterType.FLOAT,
                (0, 0), 1.0, 0.0, 1.0, unit="level",
                description="Master output volume"
            ))

            self._add_parameter(ParameterDefinition(
                "master_pan", ParameterScope.GLOBAL, ParameterType.FLOAT,
                (0, 1), 0.0, -1.0, 1.0, unit="pan",
                description="Master stereo pan"
            ))

            # ===== PART PARAMETERS =====
            for part_num in range(16):
                # Basic part parameters
                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_volume", ParameterScope.PART, ParameterType.FLOAT,
                    (1, part_num, 0), 1.0, 0.0, 1.0, unit="level",
                    description=f"Part {part_num} volume"
                ))

                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_pan", ParameterScope.PART, ParameterType.FLOAT,
                    (1, part_num, 1), 0.0, -1.0, 1.0, unit="pan",
                    description=f"Part {part_num} pan"
                ))

                # Engine selection
                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_engine_mode", ParameterScope.PART, ParameterType.ENUM,
                    (1, part_num, 2), 0, 0, 1, ["GS", "Jupiter-X"],
                    description=f"Part {part_num} engine mode"
                ))

                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_jupiter_engine", ParameterScope.PART, ParameterType.ENUM,
                    (1, part_num, 3), 0, 0, 3, ["Analog", "Digital", "FM", "External"],
                    description=f"Part {part_num} Jupiter-X engine type"
                ))

            # ===== ENGINE PARAMETERS =====
            engine_types = ["analog", "digital", "fm", "external"]
            for part_num in range(16):
                for engine_idx, engine_name in enumerate(engine_types):
                    # Engine level
                    self._add_parameter(ParameterDefinition(
                        f"part_{part_num}_{engine_name}_level", ParameterScope.ENGINE, ParameterType.FLOAT,
                        (2, part_num, engine_idx, 0), 1.0, 0.0, 1.0, unit="level",
                        description=f"Part {part_num} {engine_name} engine level"
                    ))

                    # Engine-specific parameters (simplified - would be expanded)
                    self._add_parameter(ParameterDefinition(
                        f"part_{part_num}_{engine_name}_attack", ParameterScope.ENGINE, ParameterType.FLOAT,
                        (2, part_num, engine_idx, 1), 0.01, 0.001, 10.0, unit="seconds",
                        description=f"Part {part_num} {engine_name} attack time"
                    ))

                    self._add_parameter(ParameterDefinition(
                        f"part_{part_num}_{engine_name}_decay", ParameterScope.ENGINE, ParameterType.FLOAT,
                        (2, part_num, engine_idx, 2), 0.3, 0.001, 10.0, unit="seconds",
                        description=f"Part {part_num} {engine_name} decay time"
                    ))

            # ===== ARPEGGIATOR PARAMETERS =====
            for part_num in range(16):
                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_arp_enabled", ParameterScope.ARPEGGIATOR, ParameterType.BOOL,
                    (3, part_num, 0), False, description=f"Part {part_num} arpeggiator enable"
                ))

                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_arp_pattern", ParameterScope.ARPEGGIATOR, ParameterType.INT,
                    (3, part_num, 1), 0, 0, 31, unit="pattern",
                    description=f"Part {part_num} arpeggiator pattern"
                ))

                self._add_parameter(ParameterDefinition(
                    f"part_{part_num}_arp_tempo", ParameterScope.ARPEGGIATOR, ParameterType.FLOAT,
                    (3, part_num, 2), 120.0, 20.0, 300.0, unit="bpm",
                    description=f"Part {part_num} arpeggiator tempo"
                ))

            # ===== MPE PARAMETERS =====
            self._add_parameter(ParameterDefinition(
                "mpe_enabled", ParameterScope.MPE, ParameterType.BOOL,
                (4, 0), False, description="MPE mode enable"
            ))

            self._add_parameter(ParameterDefinition(
                "mpe_lower_zone_master", ParameterScope.MPE, ParameterType.INT,
                (4, 1), 0, 0, 15, unit="channel",
                description="MPE lower zone master channel"
            ))

            self._add_parameter(ParameterDefinition(
                "mpe_upper_zone_master", ParameterScope.MPE, ParameterType.INT,
                (4, 2), 9, 0, 15, unit="channel",
                description="MPE upper zone master channel"
            ))

            # ===== EFFECTS PARAMETERS =====
            self._add_parameter(ParameterDefinition(
                "reverb_enabled", ParameterScope.EFFECT, ParameterType.BOOL,
                (5, 0), True, description="Reverb effect enable"
            ))

            self._add_parameter(ParameterDefinition(
                "chorus_enabled", ParameterScope.EFFECT, ParameterType.BOOL,
                (5, 1), False, description="Chorus effect enable"
            ))

            self._add_parameter(ParameterDefinition(
                "reverb_level", ParameterScope.EFFECT, ParameterType.FLOAT,
                (5, 2), 0.3, 0.0, 1.0, unit="level",
                description="Reverb wet/dry mix"
            ))

    def _add_parameter(self, param: ParameterDefinition):
        """Add parameter to registry."""
        self.parameters[param.name] = param
        self.parameters_by_address[param.address] = param
        self.parameters_by_scope[param.scope][param.name] = param

    def set_component_references(self, component_manager=None, arpeggiator=None,
                               mpe_manager=None, effects_coordinator=None):
        """Set references to component managers."""
        self.component_manager = component_manager
        self.arpeggiator = arpeggiator
        self.mpe_manager = mpe_manager
        self.effects_coordinator = effects_coordinator

    def set_parameter(self, param_name: str, value: Any, source: str = "internal") -> bool:
        """
        Set parameter value with validation and callbacks.

        Args:
            param_name: Parameter name
            value: New parameter value
            source: Source of parameter change ("midi", "ui", "internal")

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            if param_name not in self.parameters:
                return False

            param = self.parameters[param_name]

            # Validate value
            if not param.validate_value(value):
                return False

            # Normalize value
            normalized_value = param.normalize_value(value)

            # Store old value
            old_value = param.current_value

            # Update parameter
            param.current_value = normalized_value

            # Propagate to components
            success = self._propagate_parameter_change(param, normalized_value, source)

            if success:
                # Notify callbacks
                param.notify_callbacks(old_value, normalized_value)

            return success

    def get_parameter(self, param_name: str) -> Any:
        """Get parameter current value."""
        with self.lock:
            if param_name in self.parameters:
                return self.parameters[param_name].current_value
            return None

    def get_parameter_definition(self, param_name: str) -> Optional[ParameterDefinition]:
        """Get parameter definition."""
        with self.lock:
            return self.parameters.get(param_name)

    def _propagate_parameter_change(self, param: ParameterDefinition,
                                   value: Any, source: str) -> bool:
        """Propagate parameter change to appropriate component."""
        try:
            scope, *address_parts = param.address

            if scope == 0:  # Global parameters
                if param.name == "master_volume":
                    if self.component_manager:
                        return self.component_manager.set_parameter(0x00, int(value * 127))
                elif param.name == "master_pan":
                    if self.component_manager:
                        return self.component_manager.set_parameter(0x01, int((value + 1.0) * 63.5))

            elif scope == 1:  # Part parameters
                part_num = address_parts[0]
                if self.component_manager:
                    part = self.component_manager.get_part(part_num)
                    if part:
                        if "volume" in param.name:
                            return part.set_parameter(0x02, int(value * 127))
                        elif "pan" in param.name:
                            return part.set_parameter(0x03, int((value + 1.0) * 63.5))

            elif scope == 3:  # Arpeggiator parameters
                part_num = address_parts[0]
                if self.arpeggiator:
                    if "arp_enabled" in param.name:
                        return self.arpeggiator.enable_arpeggiator(part_num, value)
                    elif "arp_pattern" in param.name:
                        return self.arpeggiator.set_pattern(part_num, value)

            elif scope == 4:  # MPE parameters
                if self.mpe_manager:
                    if param.name == "mpe_enabled":
                        self.mpe_manager.enable_mpe(value)
                        return True
                    elif "lower_zone" in param.name:
                        # Configure lower zone
                        pass
                    elif "upper_zone" in param.name:
                        # Configure upper zone
                        pass

            elif scope == 5:  # Effects parameters
                if self.effects_coordinator:
                    if "reverb" in param.name:
                        return self.effects_coordinator.set_system_effect_parameter(
                            "reverb", param.name.split("_")[1], value
                        )
                    elif "chorus" in param.name:
                        return self.effects_coordinator.set_system_effect_parameter(
                            "chorus", param.name.split("_")[1], value
                        )

            return True
        except Exception as e:
            print(f"Parameter propagation error for {param.name}: {e}")
            return False

    def process_midi_cc(self, channel: int, cc_number: int, value: int) -> bool:
        """Process MIDI CC message."""
        with self.lock:
            midi_key = (channel, cc_number)
            if midi_key in self.cc_mappings:
                param_name = self.cc_mappings[midi_key]
                # Convert MIDI value (0-127) to parameter range
                param = self.parameters[param_name]
                if param.param_type == ParameterType.FLOAT:
                    normalized_value = value / 127.0
                    if param.min_value is not None and param.max_value is not None:
                        normalized_value = param.min_value + normalized_value * (param.max_value - param.min_value)
                    return self.set_parameter(param_name, normalized_value, "midi")
                elif param.param_type == ParameterType.INT:
                    return self.set_parameter(param_name, value, "midi")
                elif param.param_type == ParameterType.BOOL:
                    return self.set_parameter(param_name, value > 63, "midi")

        return False

    def process_nrpn(self, msb: int, lsb: int, value: int) -> bool:
        """Process NRPN message."""
        with self.lock:
            nrpn_key = (msb, lsb)
            if nrpn_key in self.nrpn_mappings:
                param_name = self.nrpn_mappings[nrpn_key]
                # Convert NRPN value to parameter range
                param = self.parameters[param_name]
                if param.param_type == ParameterType.FLOAT:
                    normalized_value = value / 16383.0  # 14-bit NRPN
                    if param.min_value is not None and param.max_value is not None:
                        normalized_value = param.min_value + normalized_value * (param.max_value - param.min_value)
                    return self.set_parameter(param_name, normalized_value, "midi")
                else:
                    # For non-float parameters, use MSB only
                    midi_value = value >> 7
                    return self.set_parameter(param_name, midi_value, "midi")

        return False

    def add_midi_mapping(self, param_name: str, midi_type: str,
                        channel: int, controller: int) -> bool:
        """Add MIDI mapping for parameter."""
        with self.lock:
            if param_name not in self.parameters:
                return False

            if midi_type == "cc":
                self.cc_mappings[(channel, controller)] = param_name
            elif midi_type == "nrpn":
                self.nrpn_mappings[(channel, controller)] = param_name
            else:
                return False

            return True

    def remove_midi_mapping(self, param_name: str, midi_type: str,
                           channel: int, controller: int) -> bool:
        """Remove MIDI mapping for parameter."""
        with self.lock:
            if midi_type == "cc":
                key = (channel, controller)
                if key in self.cc_mappings and self.cc_mappings[key] == param_name:
                    del self.cc_mappings[key]
                    return True
            elif midi_type == "nrpn":
                key = (channel, controller)
                if key in self.nrpn_mappings and self.nrpn_mappings[key] == param_name:
                    del self.nrpn_mappings[key]
                    return True

        return False

    def save_preset(self, preset_name: str, bank_name: str = "default") -> bool:
        """Save current parameter state as preset."""
        with self.lock:
            if bank_name not in self.preset_banks:
                self.preset_banks[bank_name] = []

            # Collect current parameter values
            preset_data = {}
            for param_name, param in self.parameters.items():
                preset_data[param_name] = param.current_value

            preset_key = f"{bank_name}:{preset_name}"
            self.presets[preset_key] = preset_data

            if preset_name not in self.preset_banks[bank_name]:
                self.preset_banks[bank_name].append(preset_name)

            return True

    def load_preset(self, preset_name: str, bank_name: str = "default") -> bool:
        """Load preset."""
        with self.lock:
            preset_key = f"{bank_name}:{preset_name}"
            if preset_key not in self.presets:
                return False

            preset_data = self.presets[preset_key]

            # Apply preset values
            success = True
            for param_name, value in preset_data.items():
                if not self.set_parameter(param_name, value, "preset"):
                    success = False

            if success:
                self.current_preset = preset_key

            return success

    def get_parameter_list(self, scope: ParameterScope = None,
                          tags: List[str] = None) -> List[Dict[str, Any]]:
        """Get list of parameters with optional filtering."""
        with self.lock:
            params = []

            for param in self.parameters.values():
                # Filter by scope
                if scope and param.scope != scope:
                    continue

                # Filter by tags
                if tags:
                    if not any(tag in param.tags for tag in tags):
                        continue

                params.append(param.get_parameter_info())

            return params

    def get_midi_mappings(self) -> Dict[str, Any]:
        """Get all MIDI mappings."""
        with self.lock:
            return {
                'cc_mappings': dict(self.cc_mappings),
                'nrpn_mappings': dict(self.nrpn_mappings),
            }

    def reset_to_defaults(self) -> bool:
        """Reset all parameters to defaults."""
        with self.lock:
            success = True
            for param in self.parameters.values():
                if not self.set_parameter(param.name, param.default_value, "reset"):
                    success = False
            return success

    def export_parameter_state(self, filename: str) -> bool:
        """Export current parameter state to JSON file."""
        try:
            state = {
                'parameters': {name: param.current_value for name, param in self.parameters.items()},
                'presets': self.presets,
                'current_preset': self.current_preset,
                'midi_mappings': self.get_midi_mappings(),
            }

            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)

            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def import_parameter_state(self, filename: str) -> bool:
        """Import parameter state from JSON file."""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)

            # Restore parameters
            if 'parameters' in state:
                for param_name, value in state['parameters'].items():
                    self.set_parameter(param_name, value, "import")

            # Restore presets
            if 'presets' in state:
                self.presets.update(state['presets'])

            # Restore MIDI mappings
            if 'midi_mappings' in state:
                mappings = state['midi_mappings']
                if 'cc_mappings' in mappings:
                    self.cc_mappings.update(mappings['cc_mappings'])
                if 'nrpn_mappings' in mappings:
                    self.nrpn_mappings.update(mappings['nrpn_mappings'])

            return True
        except Exception as e:
            print(f"Import error: {e}")
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        with self.lock:
            return {
                'total_parameters': len(self.parameters),
                'parameters_by_scope': {scope.value: len(params) for scope, params in self.parameters_by_scope.items()},
                'midi_mappings': {
                    'cc_count': len(self.cc_mappings),
                    'nrpn_count': len(self.nrpn_mappings),
                },
                'presets': {
                    'total': len(self.presets),
                    'banks': list(self.preset_banks.keys()),
                    'current': self.current_preset,
                },
                'component_status': {
                    'component_manager': self.component_manager is not None,
                    'arpeggiator': self.arpeggiator is not None,
                    'mpe_manager': self.mpe_manager is not None,
                    'effects_coordinator': self.effects_coordinator is not None,
                },
            }


# Export the unified parameter system
__all__ = ['JupiterXUnifiedParameterSystem', 'ParameterDefinition', 'ParameterScope', 'ParameterType']
