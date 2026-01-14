"""
Effects System - Professional Audio Effects Processing

Complete effects processing system with XG/GM2 compatibility, workstation-grade
effects, and comprehensive parameter control for professional audio production.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable, Union
import threading
import time
import math
import numpy as np
from pathlib import Path
import os
import hashlib
import weakref


class EffectsSystem:
    """
    Complete effects processing system for XG synthesizer.

    Provides professional audio effects with XG/GM2 compatibility,
    workstation-grade processing, and comprehensive parameter control.
    """

    def __init__(self, synthesizer):
        """
        Initialize effects system.

        Args:
            synthesizer: Reference to the parent synthesizer
        """
        self.synthesizer = synthesizer
        self.lock = threading.RLock()

        # Effects components
        self.effects_coordinator = None
        self.motif_effects = None

        # Initialize effects
        self._init_effects_system()

    def _init_effects_system(self):
        """Initialize effects processing system"""
        # Effects coordinator with GS integration
        from ..effects import XGEffectsCoordinator
        self.effects_coordinator = XGEffectsCoordinator(
            sample_rate=self.synthesizer.sample_rate,
            block_size=self.synthesizer.block_size,
            max_channels=self.synthesizer.max_channels,
            synthesizer=self.synthesizer  # Pass self for GS parameter access
        )

        # Motif Effects Processor for workstation-grade effects
        from ..xg.xg_motif_effects import MotifEffectsProcessor
        self.motif_effects = MotifEffectsProcessor(sample_rate=self.synthesizer.sample_rate)

        print("🎹 Effects system initialized with XG/GM2 compatibility")

    def apply_effects(self, block_size: int) -> None:
        """
        Apply XG effects processing to audio output.

        Args:
            block_size: Size of audio block to process
        """
        if not self.effects_coordinator:
            return

        # Use XG effects coordinator
        channel_audio_list = [self.synthesizer.channel_buffers[i][:block_size]
                            for i in range(len(self.synthesizer.channels))]

        self.effects_coordinator.process_channels_to_stereo_zero_alloc(
            channel_audio_list, self.synthesizer.output_buffer[:block_size], block_size
        )

    def reset_all_effects(self):
        """Reset all effects to default state"""
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'reset_all_effects'):
            self.effects_coordinator.reset_all_effects()

        if self.motif_effects and hasattr(self.motif_effects, 'reset'):
            self.motif_effects.reset()

    def cleanup_effects(self):
        """Clean up effects resources"""
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'cleanup'):
            self.effects_coordinator.cleanup()

        if self.motif_effects and hasattr(self.motif_effects, 'cleanup'):
            self.motif_effects.cleanup()

    def get_effects_status(self) -> Dict[str, Any]:
        """
        Get effects system status.

        Returns:
            Dictionary with effects system information
        """
        status = {
            'coordinator_active': self.effects_coordinator is not None,
            'motif_effects_active': self.motif_effects is not None,
        }

        if self.effects_coordinator:
            status['coordinator_info'] = {
                'sample_rate': self.effects_coordinator.sample_rate,
                'block_size': self.effects_coordinator.block_size,
                'max_channels': self.effects_coordinator.max_channels,
            }

        if self.motif_effects:
            status['motif_effects_info'] = {
                'sample_rate': self.motif_effects.sample_rate,
                'effects_count': getattr(self.motif_effects, 'effects_count', 0),
            }

        return status

    def set_system_reverb(self, reverb_type: int, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set system reverb effect.

        Args:
            reverb_type: XG reverb type (0-127)
            parameters: Optional reverb parameters

        Returns:
            True if set successfully, False otherwise
        """
        if self.effects_coordinator:
            # Try to set via XG components first
            if hasattr(self.synthesizer, 'xg_components') and self.synthesizer.xg_components:
                return self.synthesizer.xg_components.get_component('effects').set_system_reverb_type(reverb_type)

            # Fallback to direct coordinator control
            if hasattr(self.effects_coordinator, 'set_reverb_type'):
                return self.effects_coordinator.set_reverb_type(reverb_type, parameters)

        return False

    def set_system_chorus(self, chorus_type: int, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set system chorus effect.

        Args:
            chorus_type: XG chorus type (0-127)
            parameters: Optional chorus parameters

        Returns:
            True if set successfully, False otherwise
        """
        if self.effects_coordinator:
            # Try to set via XG components first
            if hasattr(self.synthesizer, 'xg_components') and self.synthesizer.xg_components:
                return self.synthesizer.xg_components.get_component('effects').set_system_chorus_type(chorus_type)

            # Fallback to direct coordinator control
            if hasattr(self.effects_coordinator, 'set_chorus_type'):
                return self.effects_coordinator.set_chorus_type(chorus_type, parameters)

        return False

    def set_system_variation(self, variation_type: int, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set system variation effect.

        Args:
            variation_type: XG variation type (0-127)
            parameters: Optional variation parameters

        Returns:
            True if set successfully, False otherwise
        """
        if self.effects_coordinator:
            # Try to set via XG components first
            if hasattr(self.synthesizer, 'xg_components') and self.synthesizer.xg_components:
                return self.synthesizer.xg_components.get_component('effects').set_system_variation_type(variation_type)

            # Fallback to direct coordinator control
            if hasattr(self.effects_coordinator, 'set_variation_type'):
                return self.effects_coordinator.set_variation_type(variation_type, parameters)

        return False

    def get_effect_capabilities(self) -> Dict[str, Any]:
        """
        Get effects system capabilities.

        Returns:
            Dictionary with effects capabilities information
        """
        capabilities = {
            'xg_effects_supported': False,
            'gs_effects_supported': False,
            'motif_effects_supported': self.motif_effects is not None,
            'coordinator_supported': self.effects_coordinator is not None,
        }

        if hasattr(self.synthesizer, 'xg_components') and self.synthesizer.xg_components:
            xg_effects = self.synthesizer.xg_components.get_component('effects')
            if xg_effects and hasattr(xg_effects, 'get_effect_capabilities'):
                capabilities['xg_effects_supported'] = True
                capabilities['xg_capabilities'] = xg_effects.get_effect_capabilities()

        if hasattr(self.synthesizer, 'gs_components') and self.synthesizer.gs_components:
            capabilities['gs_effects_supported'] = True

        return capabilities

    def process_channel_effects(self, channel_audio: np.ndarray, channel: int,
                              block_size: int) -> np.ndarray:
        """
        Process effects for a specific channel.

        Args:
            channel_audio: Channel audio buffer
            channel: Channel number
            block_size: Audio block size

        Returns:
            Processed channel audio
        """
        # Apply channel-specific effects if available
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'process_channel'):
            return self.effects_coordinator.process_channel(channel_audio, channel, block_size)

        # Return unchanged audio if no processing available
        return channel_audio

    def set_channel_effect_send(self, channel: int, effect_type: str, send_level: float):
        """
        Set effect send level for a channel.

        Args:
            channel: Channel number
            effect_type: Type of effect ('reverb', 'chorus', 'variation')
            send_level: Send level (0.0 to 1.0)
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'set_channel_send'):
            self.effects_coordinator.set_channel_send(channel, effect_type, send_level)

    def get_channel_effect_send(self, channel: int, effect_type: str) -> float:
        """
        Get effect send level for a channel.

        Args:
            channel: Channel number
            effect_type: Type of effect ('reverb', 'chorus', 'variation')

        Returns:
            Send level (0.0 to 1.0)
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'get_channel_send'):
            return self.effects_coordinator.get_channel_send(channel, effect_type)
        return 0.0

    def set_master_effect_level(self, effect_type: str, level: float):
        """
        Set master effect level.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')
            level: Master level (0.0 to 1.0)
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'set_master_level'):
            self.effects_coordinator.set_master_level(effect_type, level)

    def get_master_effect_level(self, effect_type: str) -> float:
        """
        Get master effect level.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')

        Returns:
            Master level (0.0 to 1.0)
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'get_master_level'):
            return self.effects_coordinator.get_master_level(effect_type)
        return 1.0

    def enable_effect(self, effect_type: str, enabled: bool = True):
        """
        Enable or disable an effect.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')
            enabled: Whether to enable the effect
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'enable_effect'):
            self.effects_coordinator.enable_effect(effect_type, enabled)

    def is_effect_enabled(self, effect_type: str) -> bool:
        """
        Check if an effect is enabled.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')

        Returns:
            True if effect is enabled, False otherwise
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'is_effect_enabled'):
            return self.effects_coordinator.is_effect_enabled(effect_type)
        return False

    def get_effect_parameters(self, effect_type: str) -> Dict[str, Any]:
        """
        Get parameters for a specific effect.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')

        Returns:
            Dictionary of effect parameters
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'get_effect_parameters'):
            return self.effects_coordinator.get_effect_parameters(effect_type)
        return {}

    def set_effect_parameter(self, effect_type: str, parameter: str, value: Any) -> bool:
        """
        Set a parameter for a specific effect.

        Args:
            effect_type: Type of effect ('reverb', 'chorus', 'variation')
            parameter: Parameter name
            value: Parameter value

        Returns:
            True if parameter was set successfully, False otherwise
        """
        if self.effects_coordinator and hasattr(self.effects_coordinator, 'set_effect_parameter'):
            return self.effects_coordinator.set_effect_parameter(effect_type, parameter, value)
        return False
