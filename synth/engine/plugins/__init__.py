"""
Engine Plugin System

Modular plugin architecture for synthesizer engines, allowing feature extensions
and synthesizer-specific enhancements without code duplication.

This system enables:
- Feature extensions for existing engines
- Synthesizer-specific enhancements
- Plugin-based architecture for maintainability
- Clean separation of core engine functionality from extensions
"""

from .base_plugin import BaseEnginePlugin, PluginMetadata
from .plugin_registry import PluginRegistry, PluginLoadError, PluginDependencyError

__all__ = [
    'BaseEnginePlugin',
    'PluginMetadata',
    'PluginRegistry',
    'PluginLoadError',
    'PluginDependencyError',
]
