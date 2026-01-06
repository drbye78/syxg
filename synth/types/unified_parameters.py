"""
Unified Parameter System - Jupiter-X Compatible Parameter Management

Provides a unified parameter system that supports Jupiter-X parameter mappings,
validation, and real-time updates with hardware-accurate response curves.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import math


class ParameterScope(Enum):
    """Parameter scope definitions."""
    GLOBAL = "global"
    CHANNEL = "channel"
    VOICE = "voice"
    PARTIAL = "partial"


class ParameterSource(Enum):
    """Parameter source definitions."""
    INTERNAL = "internal"
    MIDI_CC = "midi_cc"
    NRPN = "nrpn"
    RPN = "rpn"
    SYSEX = "sysex"
    AUTOMATION = "automation"


class ParameterUpdate:
    """
    Parameter update container for unified parameter system.

    Supports Jupiter-X parameter mappings with hardware-accurate curves.
    """

    def __init__(self, name: str, value: float, scope: ParameterScope = ParameterScope.GLOBAL,
                 source: ParameterSource = ParameterSource.INTERNAL, channel: Optional[int] = None):
        """
        Initialize parameter update.

        Args:
            name: Parameter name
            value: Parameter value
            scope: Parameter scope
            source: Parameter source
            channel: MIDI channel (for channel-specific parameters)
        """
        self.name = name
        self.value = value
        self.scope = scope
        self.source = source
        self.channel = channel
        self.timestamp = self._get_timestamp()

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'value': self.value,
            'scope': self.scope.value,
            'source': self.source.value,
            'channel': self.channel,
            'timestamp': self.timestamp
        }


class JupiterXParameterMapping:
    """
    Jupiter-X parameter mapping system.

    Provides hardware-accurate parameter curves and ranges for Jupiter-X compatibility.
    """

    # Jupiter-X parameter ranges and curves
    PARAMETER_RANGES = {
        # Oscillator parameters
        'osc1_waveform': {'min': 0, 'max': 127, 'default': 0, 'curve': 'linear'},
        'osc1_coarse_tune': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
        'osc1_fine_tune': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
        'osc1_level': {'min': 0, 'max': 127, 'default': 100, 'curve': 'linear'},

        'osc2_waveform': {'min': 0, 'max': 127, 'default': 0, 'curve': 'linear'},
        'osc2_coarse_tune': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
        'osc2_fine_tune': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
        'osc2_level': {'min': 0, 'max': 127, 'default': 100, 'curve': 'linear'},

        # Filter parameters
        'filter_cutoff': {'min': 0, 'max': 127, 'default': 64, 'curve': 'exponential'},
        'filter_resonance': {'min': 0, 'max': 127, 'default': 0, 'curve': 'linear'},
        'filter_drive': {'min': 0, 'max': 127, 'default': 0, 'curve': 'exponential'},
        'filter_type': {'min': 0, 'max': 3, 'default': 0, 'curve': 'linear'},

        # Amplifier parameters
        'amp_level': {'min': 0, 'max': 127, 'default': 100, 'curve': 'linear'},
        'amp_attack': {'min': 0, 'max': 127, 'default': 0, 'curve': 'exponential'},
        'amp_decay': {'min': 0, 'max': 127, 'default': 64, 'curve': 'exponential'},
        'amp_sustain': {'min': 0, 'max': 127, 'default': 127, 'curve': 'linear'},
        'amp_release': {'min': 0, 'max': 127, 'default': 64, 'curve': 'exponential'},

        # LFO parameters
        'lfo1_rate': {'min': 0, 'max': 127, 'default': 64, 'curve': 'exponential'},
        'lfo1_depth': {'min': 0, 'max': 127, 'default': 0, 'curve': 'linear'},
        'lfo1_waveform': {'min': 0, 'max': 3, 'default': 0, 'curve': 'linear'},

        'lfo2_rate': {'min': 0, 'max': 127, 'default': 32, 'curve': 'exponential'},
        'lfo2_depth': {'min': 0, 'max': 127, 'default': 0, 'curve': 'linear'},
        'lfo2_waveform': {'min': 0, 'max': 3, 'default': 1, 'curve': 'linear'},

        # Effects parameters
        'distortion_drive': {'min': 0, 'max': 127, 'default': 0, 'curve': 'exponential'},
        'distortion_tone': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
        'phaser_rate': {'min': 0, 'max': 127, 'default': 32, 'curve': 'exponential'},
        'phaser_depth': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},

        # Performance parameters
        'pitch_bend_range': {'min': 0, 'max': 24, 'default': 2, 'curve': 'linear'},
        'portamento_time': {'min': 0, 'max': 127, 'default': 0, 'curve': 'exponential'},
        'transpose': {'min': 0, 'max': 127, 'default': 64, 'curve': 'linear'},
    }

    # MIDI CC mappings for Jupiter-X
    MIDI_CC_MAPPINGS = {
        1: 'modulation_wheel',
        7: 'volume',
        10: 'pan',
        11: 'expression',
        64: 'sustain_pedal',
        65: 'portamento_on_off',
        84: 'portamento_time',
        74: 'filter_cutoff',
        71: 'filter_resonance',
        79: 'filter_drive',
        73: 'amp_attack',
        75: 'amp_decay',
        79: 'amp_release',
        72: 'amp_release',  # Alternative mapping
    }

    @classmethod
    def get_parameter_range(cls, param_name: str) -> Optional[Dict[str, Any]]:
        """
        Get parameter range and curve information.

        Args:
            param_name: Parameter name

        Returns:
            Parameter range information or None if not found
        """
        return cls.PARAMETER_RANGES.get(param_name)

    @classmethod
    def validate_parameter_value(cls, param_name: str, value: float) -> float:
        """
        Validate and clamp parameter value to Jupiter-X range.

        Args:
            param_name: Parameter name
            value: Raw parameter value

        Returns:
            Validated and clamped parameter value
        """
        param_info = cls.get_parameter_range(param_name)
        if param_info:
            return max(param_info['min'], min(param_info['max'], value))
        return value

    @classmethod
    def apply_parameter_curve(cls, param_name: str, midi_value: int) -> float:
        """
        Apply Jupiter-X parameter curve to MIDI value.

        Args:
            param_name: Parameter name
            midi_value: MIDI value (0-127)

        Returns:
            Curved parameter value
        """
        param_info = cls.get_parameter_range(param_name)
        if not param_info:
            return midi_value / 127.0

        curve_type = param_info.get('curve', 'linear')

        if curve_type == 'linear':
            return midi_value / 127.0
        elif curve_type == 'exponential':
            # Exponential curve for frequency/time parameters
            if midi_value == 0:
                return 0.0
            return math.pow(midi_value / 127.0, 2.0)
        else:
            return midi_value / 127.0

    @classmethod
    def get_midi_cc_mapping(cls, cc_number: int) -> Optional[str]:
        """
        Get parameter name for MIDI CC number.

        Args:
            cc_number: MIDI CC number (0-127)

        Returns:
            Parameter name or None if not mapped
        """
        return cls.MIDI_CC_MAPPINGS.get(cc_number)


class UnifiedParameterSystem:
    """
    Unified parameter system for Jupiter-X compatibility.

    Provides centralized parameter management with hardware-accurate curves,
    validation, and real-time updates.
    """

    def __init__(self):
        """Initialize unified parameter system."""
        self.parameter_values: Dict[str, float] = {}
        self.parameter_callbacks: Dict[str, List[Callable]] = {}
        self.parameter_history: List[ParameterUpdate] = []
        self.max_history_size = 1000

        # Initialize default parameter values
        self._initialize_default_parameters()

    def _initialize_default_parameters(self):
        """Initialize default parameter values from Jupiter-X mappings."""
        for param_name, param_info in JupiterXParameterMapping.PARAMETER_RANGES.items():
            self.parameter_values[param_name] = param_info['default']

    def set_parameter(self, param_name: str, value: float, scope: ParameterScope = ParameterScope.GLOBAL,
                     source: ParameterSource = ParameterSource.INTERNAL, channel: Optional[int] = None) -> bool:
        """
        Set parameter value with validation and callbacks.

        Args:
            param_name: Parameter name
            value: Parameter value
            scope: Parameter scope
            source: Parameter source
            channel: MIDI channel

        Returns:
            True if parameter was set successfully
        """
        # Validate parameter value
        validated_value = JupiterXParameterMapping.validate_parameter_value(param_name, value)

        # Store old value for callbacks
        old_value = self.parameter_values.get(param_name)

        # Update parameter
        self.parameter_values[param_name] = validated_value

        # Create parameter update record
        update = ParameterUpdate(param_name, validated_value, scope, source, channel)
        self.parameter_history.append(update)

        # Maintain history size limit
        if len(self.parameter_history) > self.max_history_size:
            self.parameter_history = self.parameter_history[-self.max_history_size:]

        # Trigger callbacks if value changed
        if old_value != validated_value:
            self._trigger_callbacks(param_name, validated_value, old_value)

        return True

    def get_parameter(self, param_name: str, default: Optional[float] = None) -> Optional[float]:
        """
        Get parameter value.

        Args:
            param_name: Parameter name
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        return self.parameter_values.get(param_name, default)

    def register_callback(self, param_name: str, callback: Callable) -> bool:
        """
        Register callback for parameter changes.

        Args:
            param_name: Parameter name
            callback: Callback function (param_name, new_value, old_value)

        Returns:
            True if registered successfully
        """
        if param_name not in self.parameter_callbacks:
            self.parameter_callbacks[param_name] = []

        if callback not in self.parameter_callbacks[param_name]:
            self.parameter_callbacks[param_name].append(callback)
            return True

        return False

    def unregister_callback(self, param_name: str, callback: Callable) -> bool:
        """
        Unregister callback for parameter changes.

        Args:
            param_name: Parameter name
            callback: Callback function to remove

        Returns:
            True if unregistered successfully
        """
        if param_name in self.parameter_callbacks:
            if callback in self.parameter_callbacks[param_name]:
                self.parameter_callbacks[param_name].remove(callback)
                return True

        return False

    def _trigger_callbacks(self, param_name: str, new_value: float, old_value: Optional[float]):
        """Trigger callbacks for parameter change."""
        if param_name in self.parameter_callbacks:
            for callback in self.parameter_callbacks[param_name]:
                try:
                    callback(param_name, new_value, old_value)
                except Exception as e:
                    print(f"Parameter callback error for {param_name}: {e}")

    def process_midi_cc(self, cc_number: int, cc_value: int, channel: int = 0) -> Optional[ParameterUpdate]:
        """
        Process MIDI CC message and create parameter update.

        Args:
            cc_number: MIDI CC number (0-127)
            cc_value: MIDI CC value (0-127)
            channel: MIDI channel

        Returns:
            ParameterUpdate if CC is mapped, None otherwise
        """
        param_name = JupiterXParameterMapping.get_midi_cc_mapping(cc_number)
        if param_name:
            # Apply parameter curve
            curved_value = JupiterXParameterMapping.apply_parameter_curve(param_name, cc_value)

            # Create parameter update
            update = ParameterUpdate(
                param_name,
                curved_value,
                ParameterScope.CHANNEL,
                ParameterSource.MIDI_CC,
                channel
            )

            # Apply the update
            self.set_parameter(param_name, curved_value, ParameterScope.CHANNEL,
                             ParameterSource.MIDI_CC, channel)

            return update

        return None

    def get_parameter_history(self, param_name: Optional[str] = None, limit: int = 50) -> List[ParameterUpdate]:
        """
        Get parameter update history.

        Args:
            param_name: Specific parameter name, or None for all
            limit: Maximum number of history entries to return

        Returns:
            List of parameter updates
        """
        if param_name:
            history = [update for update in self.parameter_history if update.name == param_name]
        else:
            history = self.parameter_history

        return history[-limit:] if limit > 0 else history

    def reset_to_defaults(self):
        """Reset all parameters to Jupiter-X defaults."""
        self.parameter_values.clear()
        self.parameter_history.clear()
        self._initialize_default_parameters()

    def get_parameter_info(self) -> Dict[str, Any]:
        """
        Get comprehensive parameter system information.

        Returns:
            Parameter system status and statistics
        """
        return {
            'total_parameters': len(self.parameter_values),
            'total_callbacks': sum(len(callbacks) for callbacks in self.parameter_callbacks.values()),
            'history_size': len(self.parameter_history),
            'max_history_size': self.max_history_size,
            'parameter_names': list(self.parameter_values.keys()),
            'callback_parameters': list(self.parameter_callbacks.keys())
        }


# Global unified parameter system instance
_unified_parameter_system = None

def get_unified_parameter_system() -> UnifiedParameterSystem:
    """
    Get global unified parameter system instance.

    Returns:
        UnifiedParameterSystem instance
    """
    global _unified_parameter_system
    if _unified_parameter_system is None:
        _unified_parameter_system = UnifiedParameterSystem()
    return _unified_parameter_system
