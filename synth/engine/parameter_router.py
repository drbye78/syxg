"""
Parameter routing system for hierarchical parameter distribution.

This module implements the hierarchical parameter routing system that distributes
parameters from the synthesizer level down to individual partials using the
ParameterUpdate protocol. Now integrated with the unified parameter system
for synthesizer-specific parameter handling.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING
from ..types.parameter_types import ParameterUpdate, ParameterScope, ParameterSource, SynthesizerType
from ..types.unified_parameters import get_unified_parameter_system

if TYPE_CHECKING:
    from .modern_xg_synthesizer import ModernXGSynthesizer


class ParameterRouter:
    """
    Routes parameters hierarchically through the synthesizer architecture.

    This class implements the hierarchical parameter routing system that ensures
    parameters are delivered to the correct architectural level with proper
    scoping and validation.
    """

    def __init__(self, synthesizer: ModernXGSynthesizer | None = None):
        """
        Initialize parameter router.

        Args:
            synthesizer: Reference to the main synthesizer (optional for testing)
        """
        self.synthesizer = synthesizer
        self.parameter_cache: dict[str, ParameterUpdate] = {}
        self.route_history: list[dict] = []  # For debugging

    def route_parameter_update(self, param_update: ParameterUpdate) -> bool:
        """
        Route a parameter update to the appropriate architectural level.

        Args:
            param_update: Parameter update to route

        Returns:
            True if routing successful, False otherwise
        """
        # Validate parameter update
        if not self._validate_parameter_update(param_update):
            return False

        # Cache parameter for debugging
        self.parameter_cache[param_update.name] = param_update

        # Route based on scope
        if param_update.scope == ParameterScope.GLOBAL:
            return self._route_global_parameter(param_update)
        elif param_update.scope == ParameterScope.CHANNEL:
            return self._route_channel_parameter(param_update)
        elif param_update.scope == ParameterScope.VOICE:
            return self._route_voice_parameter(param_update)
        elif param_update.scope == ParameterScope.PARTIAL:
            return self._route_partial_parameter(param_update)
        else:
            return False

    def _validate_parameter_update(self, param_update: ParameterUpdate) -> bool:
        """
        Validate parameter update before routing.

        Args:
            param_update: Parameter update to validate

        Returns:
            True if valid, False otherwise
        """
        # Check scope/channel consistency
        if param_update.scope == ParameterScope.CHANNEL and param_update.channel is None:
            return False
        if param_update.scope == ParameterScope.GLOBAL and param_update.channel is not None:
            return False

        # Parameter value ranges validation
        value = param_update.value
        if not isinstance(value, (int, float)):
            return False
        
        # Validate based on parameter type
        param_name = param_update.name.lower()
        
        # Volume/pan parameters: 0-127 or 0.0-1.0
        if 'volume' in param_name or 'pan' in param_name or 'gain' in param_name:
            if not (0 <= value <= 127 or 0.0 <= value <= 1.0):
                return False
        
        # Pitch/tune parameters: cents or semitones
        if 'tune' in param_name or 'pitch' in param_name or 'transpose' in param_name:
            if not (-8192 <= value <= 8191 or -12 <= value <= 12):
                return False
        
        # Rate/depth parameters
        if 'rate' in param_name or 'depth' in param_name or 'speed' in param_name:
            if not (0 <= value <= 127 or 0.0 <= value <= 1.0):
                return False

        return True

    def _route_global_parameter(self, param_update: ParameterUpdate) -> bool:
        """
        Route global parameter to all relevant subsystems.

        Global parameters affect the entire synthesizer and may need to be
        propagated to channels, voices, and partials.

        Args:
            param_update: Global parameter update

        Returns:
            True if routing successful
        """
        # Update synthesizer global state
        self.synthesizer.apply_global_parameter(param_update)

        # Determine if parameter needs channel propagation
        if self._should_propagate_to_channels(param_update.name):
            # Propagate to all active channels
            for channel_num in range(16):
                if hasattr(self.synthesizer, 'channels') and channel_num in self.synthesizer.channels:
                    channel = self.synthesizer.channels[channel_num]
                    channel.apply_channel_parameter(param_update)

        # Determine if parameter needs effects routing
        if self._is_effects_parameter(param_update.name):
            if hasattr(self.synthesizer, 'effects_coordinator'):
                self.synthesizer.effects_coordinator.apply_global_effects_parameter(param_update)

        # Log routing for debugging
        self._log_parameter_route(param_update, "global")

        return True

    def _route_channel_parameter(self, param_update: ParameterUpdate) -> bool:
        """
        Route channel-specific parameter to appropriate channel.

        Args:
            param_update: Channel parameter update

        Returns:
            True if routing successful
        """
        if param_update.channel is None:
            return False

        # Get target channel
        if hasattr(self.synthesizer, 'channels') and param_update.channel in self.synthesizer.channels:
            channel = self.synthesizer.channels[param_update.channel]

            # Apply to channel
            channel.apply_channel_parameter(param_update)

            # Determine if parameter needs voice propagation
            if self._should_propagate_to_voices(param_update.name):
                # Propagate to all voices in this channel
                for voice in channel.active_voices:
                    voice.apply_channel_parameter(param_update)

            # Log routing
            self._log_parameter_route(param_update, f"channel_{param_update.channel}")

            return True

        return False

    def _route_voice_parameter(self, param_update: ParameterUpdate) -> bool:
        """
        Route voice-specific parameter to appropriate voice.

        Args:
            param_update: Voice parameter update

        Returns:
            True if routing successful
        """
        if param_update.channel is None:
            return False

        # Find target voice (this requires voice management system)
        # For now, broadcast to all voices in channel
        if hasattr(self.synthesizer, 'channels') and param_update.channel in self.synthesizer.channels:
            channel = self.synthesizer.channels[param_update.channel]

            for voice in channel.active_voices:
                voice.apply_voice_parameter(param_update.name, param_update.value)

            # Log routing
            self._log_parameter_route(param_update, f"voice_channel_{param_update.channel}")

            return True

        return False

    def _route_partial_parameter(self, param_update: ParameterUpdate) -> bool:
        """
        Route partial-specific parameter to appropriate partial.

        Args:
            param_update: Partial parameter update

        Returns:
            True if routing successful
        """
        if param_update.channel is None:
            return False

        # Find target partial (requires partial management system)
        # For now, this would need to be implemented based on the specific
        # voice and partial addressing scheme

        # Log routing
        self._log_parameter_route(param_update, f"partial_channel_{param_update.channel}")

        # Implement partial routing - find target partial
        if hasattr(self.synthesizer, 'channels') and param_update.channel in self.synthesizer.channels:
            channel = self.synthesizer.channels[param_update.channel]
            
            # Get partial index from parameter update if available
            partial_idx = getattr(param_update, 'partial_index', None)
            
            if partial_idx is not None:
                # Route to specific partial
                if hasattr(channel, 'partials') and partial_idx < len(channel.partials):
                    partial = channel.partials[partial_idx]
                    partial.apply_partial_parameter(param_update)
            else:
                # Route to all partials in the channel
                if hasattr(channel, 'partials'):
                    for partial in channel.partials:
                        partial.apply_partial_parameter(param_update)

        return True

    def _should_propagate_to_channels(self, param_name: str) -> bool:
        """
        Determine if a global parameter should be propagated to channels.

        Args:
            param_name: Parameter name

        Returns:
            True if parameter should propagate to channels
        """
        # Parameters that affect individual channels
        channel_propagation_params = {
            'master_volume', 'master_pan', 'master_tune', 'master_transpose',
            'reverb_send', 'chorus_send', 'variation_send'
        }

        return param_name in channel_propagation_params

    def _should_propagate_to_voices(self, param_name: str) -> bool:
        """
        Determine if a channel parameter should be propagated to voices.

        Args:
            param_name: Parameter name

        Returns:
            True if parameter should propagate to voices
        """
        # Parameters that affect individual voices
        voice_propagation_params = {
            'volume', 'pan', 'expression', 'pitch_bend',
            'modulation_wheel', 'sustain_pedal', 'soft_pedal'
        }

        return param_name in voice_propagation_params

    def _is_effects_parameter(self, param_name: str) -> bool:
        """
        Determine if parameter affects global effects.

        Args:
            param_name: Parameter name

        Returns:
            True if parameter affects effects
        """
        effects_params = {
            'reverb_time', 'reverb_hf_damp', 'reverb_predelay', 'reverb_type',
            'chorus_rate', 'chorus_depth', 'chorus_feedback', 'chorus_type',
            'distortion_drive', 'distortion_tone', 'distortion_mix', 'distortion_type'
        }

        return param_name in effects_params

    def _log_parameter_route(self, param_update: ParameterUpdate, route_target: str):
        """
        Log parameter routing for debugging and monitoring.

        Args:
            param_update: Parameter update that was routed
            route_target: Target of the routing (e.g., "global", "channel_0")
        """
        route_info = {
            'timestamp': self.synthesizer.current_time if hasattr(self.synthesizer, 'current_time') else 0,
            'parameter': param_update.name,
            'value': param_update.value,
            'scope': param_update.scope.value,
            'source': param_update.source.value,
            'channel': param_update.channel,
            'route_target': route_target
        }

        self.route_history.append(route_info)

        # Keep history limited to prevent memory issues
        if len(self.route_history) > 1000:
            self.route_history = self.route_history[-500:]

    def get_routing_stats(self) -> dict:
        """
        Get parameter routing statistics.

        Returns:
            Dictionary with routing statistics
        """
        total_routes = len(self.route_history)
        scope_counts = {}
        source_counts = {}

        for route in self.route_history[-100:]:  # Last 100 routes
            scope = route['scope']
            source = route['source']

            scope_counts[scope] = scope_counts.get(scope, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            'total_routes': total_routes,
            'recent_scope_distribution': scope_counts,
            'recent_source_distribution': source_counts,
            'cached_parameters': len(self.parameter_cache)
        }

    def clear_cache(self):
        """Clear parameter cache and routing history."""
        self.parameter_cache.clear()
        self.route_history.clear()

        # Additional methods needed for synthesizer integration
    def register_source(self, name: str, source) -> None:
        """
        Register a parameter source.

        Args:
            name: Source name
            source: Source object (must have process_control_message method)
        """
        if not hasattr(self, 'sources'):
            self.sources: dict[str, Any] = {}
        self.sources[name] = source

    def register_validator(self, name: str, validator_func) -> None:
        """
        Register a parameter validator.

        Args:
            name: Validator name
            validator_func: Validation function
        """
        if not hasattr(self, 'validators'):
            self.validators: dict[str, Any] = {}
        self.validators[name] = validator_func

    def register_monitor(self, name: str, monitor) -> None:
        """
        Register a parameter monitor.

        Args:
            name: Monitor name
            monitor: Monitor object
        """
        if not hasattr(self, 'monitors'):
            self.monitors: dict[str, Any] = {}
        self.monitors[name] = monitor

    def route_parameter(self, param_path: str, value: float, channel: int = None, part: int = None) -> bool:
        """
        Route a parameter change to the appropriate destination.

        Args:
            param_path: Parameter path (e.g., 'filter.cutoff')
            value: New parameter value
            channel: MIDI channel (for channel-specific parameters)
            part: Part number (for XG multi-part parameters)

        Returns:
            True if parameter was routed successfully
        """
        try:
            # Create parameter update
            from ..types.parameter_types import ParameterUpdate, ParameterScope, ParameterSource

            if channel is not None:
                scope = ParameterScope.CHANNEL
            else:
                scope = ParameterScope.GLOBAL

            param_update = ParameterUpdate(
                name=param_path,
                value=value,
                scope=scope,
                source=ParameterSource.INTERNAL,
                channel=channel
            )

            # Route using existing routing system
            return self.route_parameter_update(param_update)

        except Exception as e:
            print(f"Parameter routing error for {param_path}: {e}")
            return False

    def get_parameter_value(self, param_path: str, channel: int = None, part: int = None) -> float:
        """
        Get current value of a parameter.

        Args:
            param_path: Parameter path
            channel: MIDI channel
            part: Part number

        Returns:
            Current parameter value (default 0.0 if not set)
        """
        # Check parameter cache first
        if param_path in self.parameter_cache:
            return self.parameter_cache[param_path].value

        # Return default value if not found
        return 0.0

    def validate_parameter(self, param_path: str, value: float) -> bool:
        """
        Validate a parameter value.

        Args:
            param_path: Parameter path
            value: Value to validate

        Returns:
            True if value is valid
        """
        # Basic validation - could be extended
        if not isinstance(value, (int, float)):
            return False

        # Check if we have specific validators
        if hasattr(self, 'validators'):
            for validator in self.validators.values():
                if callable(validator):
                    try:
                        if not validator(param_path, value):
                            return False
                    except Exception:
                        pass  # Continue with other validators

        return True

    def _make_key(self, param_path: str, channel: int = None, part: int = None) -> str:
        """Create a unique key for parameter storage"""
        key = param_path
        if channel is not None:
            key += f"_ch{channel}"
        if part is not None:
            key += f"_pt{part}"
        return key
