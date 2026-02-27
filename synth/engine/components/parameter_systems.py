"""
Parameter Systems - GS/XG Parameter Management

Production-quality parameter priority system for managing GS/XG protocol precedence
and performance monitoring for the synthesizer.
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading
import time
import math
from pathlib import Path
import os
import hashlib
import weakref


class ParameterPrioritySystem:
    """
    GS/XG Parameter Priority System

    Manages parameter precedence between GS and XG protocols,
    allowing seamless switching between modes while preserving
    parameter relationships.
    """

    def __init__(self):
        self.active_protocol = 'auto'  # 'xg', 'gs', or 'auto'
        self.parameter_sources = {}  # param_key -> {'xg': value, 'gs': value, 'timestamp': time}

        # Parameter mappings between GS and XG
        self.parameter_mappings = {
            # Volume mappings
            'master_volume': {'gs': 'system_params.master_volume', 'xg': 'system.master_volume'},
            'part_volume': {'gs': 'multipart.parts.{channel}.volume', 'xg': 'channels.{channel}.xg_config.part_level'},

            # Pan mappings
            'part_pan': {'gs': 'multipart.parts.{channel}.pan', 'xg': 'channels.{channel}.xg_config.part_pan'},

            # Effects send mappings
            'reverb_send': {'gs': 'multipart.parts.{channel}.reverb_send', 'xg': 'channels.{channel}.xg_config.effects_sends.reverb'},
            'chorus_send': {'gs': 'multipart.parts.{channel}.chorus_send', 'xg': 'channels.{channel}.xg_config.effects_sends.chorus'},
            'variation_send': {'gs': 'multipart.parts.{channel}.delay_send', 'xg': 'channels.{channel}.xg_config.effects_sends.variation'},

            # System effects
            'system_reverb_type': {'gs': 'system_params.reverb_type', 'xg': 'effects.system_reverb_type'},
            'system_chorus_type': {'gs': 'system_params.chorus_type', 'xg': 'effects.system_chorus_type'},
        }

        self.lock = threading.RLock()

    def set_active_protocol(self, protocol: str):
        """Set active protocol: 'xg', 'gs', or 'auto'"""
        with self.lock:
            if protocol in ['xg', 'gs', 'auto']:
                self.active_protocol = protocol

    def update_parameter(self, param_key: str, value: Any, source: str, channel: int = None):
        """Update parameter from specific source (gs or xg)"""
        with self.lock:
            if source not in ['gs', 'xg']:
                return

            # Create parameter key with channel if specified
            full_key = f"{param_key}_ch{channel}" if channel is not None else param_key

            if full_key not in self.parameter_sources:
                self.parameter_sources[full_key] = {}

            self.parameter_sources[full_key][source] = value
            self.parameter_sources[full_key]['timestamp'] = time.time()

    def get_active_value(self, param_key: str, channel: int = None) -> Any | None:
        """Get parameter value based on active protocol"""
        with self.lock:
            full_key = f"{param_key}_ch{channel}" if channel is not None else param_key

            if full_key not in self.parameter_sources:
                return None

            sources = self.parameter_sources[full_key]

            if self.active_protocol == 'xg':
                return sources.get('xg')
            elif self.active_protocol == 'gs':
                return sources.get('gs')
            else:  # auto - use most recently set
                return self._get_most_recent_value(sources)

    def _get_most_recent_value(self, sources: dict[str, Any]) -> Any | None:
        """Get most recently set value from available sources"""
        xg_time = sources.get('timestamp_xg', 0)
        gs_time = sources.get('timestamp_gs', 0)

        if xg_time > gs_time and 'xg' in sources:
            return sources['xg']
        elif gs_time > xg_time and 'gs' in sources:
            return sources['gs']
        elif 'xg' in sources:
            return sources['xg']
        elif 'gs' in sources:
            return sources['gs']

        return None

    def is_gs_active(self) -> bool:
        """Check if GS protocol is currently active"""
        return self.active_protocol in ['gs', 'auto']

    def is_xg_active(self) -> bool:
        """Check if XG protocol is currently active"""
        return self.active_protocol in ['xg', 'auto']

    def get_parameter_status(self) -> dict[str, Any]:
        """Get parameter system status"""
        with self.lock:
            return {
                'active_protocol': self.active_protocol,
                'total_parameters': len(self.parameter_sources),
                'gs_parameters': sum(1 for p in self.parameter_sources.values() if 'gs' in p),
                'xg_parameters': sum(1 for p in self.parameter_sources.values() if 'xg' in p),
                'parameter_mappings': self.parameter_mappings.copy()
            }


class PerformanceMonitor:
    """Production performance monitoring"""

    def __init__(self):
        self.metrics = {
            'midi_messages_processed': 0,
            'audio_blocks_generated': 0,
            'active_voices': 0,
            'cpu_usage_percent': 0.0,
            'buffer_pool_hits': 0,
            'buffer_pool_misses': 0,
            'xg_messages_processed': 0,
        }
        self.lock = threading.RLock()

    def update(self, **metrics):
        """Update performance metrics"""
        with self.lock:
            self.metrics.update(metrics)

    def get_report(self) -> dict[str, Any]:
        """Get performance report"""
        with self.lock:
            return self.metrics.copy()
