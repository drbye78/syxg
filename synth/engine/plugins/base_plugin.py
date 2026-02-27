"""
Base Engine Plugin System

Abstract base classes and interfaces for the modular engine plugin architecture.
Provides the foundation for extending synthesis engines with synthesizer-specific
features without code duplication.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class PluginType(Enum):
    """Types of engine plugins available."""
    SYNTHESIS_FEATURE = "synthesis_feature"      # Core synthesis enhancements
    MODULATION_SOURCE = "modulation_source"      # LFO, envelope extensions
    MODULATION_DESTINATION = "modulation_destination"  # Additional modulation targets
    EFFECTS_PROCESSING = "effects_processing"    # Built-in effects
    MIDI_PROCESSING = "midi_processing"          # MIDI feature extensions
    PARAMETER_MAPPING = "parameter_mapping"      # Parameter translation
    PRESET_MANAGEMENT = "preset_management"      # Preset handling extensions


class PluginCompatibility(Enum):
    """Plugin compatibility levels."""
    EXCLUSIVE = "exclusive"      # Only works with specific engine
    COMPATIBLE = "compatible"    # Works with compatible engines
    UNIVERSAL = "universal"      # Works with any engine


@dataclass(slots=True)
class PluginMetadata:
    """Metadata for engine plugins."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    compatibility: PluginCompatibility
    target_engines: list[str]  # Engine types this plugin works with
    dependencies: list[str] = None  # Required plugins
    parameters: dict[str, dict[str, Any]] = None  # Plugin parameters

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.parameters is None:
            self.parameters = {}


class PluginLoadContext:
    """Context provided to plugins during loading."""

    def __init__(self, engine_instance: Any, sample_rate: int, block_size: int,
                 plugin_registry: PluginRegistry):
        self.engine_instance = engine_instance
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.plugin_registry = plugin_registry
        self.shared_data: dict[str, Any] = {}  # For inter-plugin communication


class BaseEnginePlugin(ABC):
    """
    Abstract base class for all engine plugins.

    Plugins extend synthesis engines with additional features and capabilities,
    allowing synthesizer-specific enhancements without modifying core engine code.
    """

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.is_loaded = False
        self.is_enabled = True
        self.load_context: PluginLoadContext | None = None

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return self.metadata

    @abstractmethod
    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """
        Check if this plugin is compatible with the target engine.

        Args:
            engine_type: Type of engine (e.g., 'fm', 'wavetable')
            engine_version: Version of the engine

        Returns:
            True if compatible, False otherwise
        """
        pass

    @abstractmethod
    def load(self, context: PluginLoadContext) -> bool:
        """
        Load and initialize the plugin.

        Args:
            context: Loading context with engine instance and configuration

        Returns:
            True if loaded successfully, False otherwise
        """
        pass

    @abstractmethod
    def unload(self) -> bool:
        """
        Unload the plugin and clean up resources.

        Returns:
            True if unloaded successfully, False otherwise
        """
        pass

    def enable(self) -> bool:
        """Enable the plugin."""
        self.is_enabled = True
        return True

    def disable(self) -> bool:
        """Disable the plugin."""
        self.is_enabled = False
        return True

    def is_active(self) -> bool:
        """Check if plugin is loaded and enabled."""
        return self.is_loaded and self.is_enabled

    # Optional override methods for specific plugin types

    def process_audio_block(self, audio_block: Any) -> Any:
        """
        Process an audio block (for effects plugins).

        Args:
            audio_block: Input audio block

        Returns:
            Processed audio block
        """
        return audio_block

    def generate_samples(self, note: int, velocity: int, modulation: dict[str, float],
                        block_size: int) -> Any:
        """
        Generate additional audio samples (for synthesis feature plugins).

        Args:
            note: MIDI note
            velocity: MIDI velocity
            modulation: Modulation parameters
            block_size: Block size

        Returns:
            Generated audio samples
        """
        return None

    def get_modulation_sources(self) -> dict[str, Callable[[], float]]:
        """
        Get additional modulation sources provided by this plugin.

        Returns:
            Dictionary of modulation source name -> value function
        """
        return {}

    def get_modulation_destinations(self) -> dict[str, Callable[[float], None]]:
        """
        Get additional modulation destinations provided by this plugin.

        Returns:
            Dictionary of modulation destination name -> setter function
        """
        return {}

    def get_parameters(self) -> dict[str, Any]:
        """
        Get plugin parameters.

        Returns:
            Dictionary of parameter name -> value
        """
        return {}

    def set_parameter(self, name: str, value: Any) -> bool:
        """
        Set a plugin parameter.

        Args:
            name: Parameter name
            value: Parameter value

        Returns:
            True if set successfully, False otherwise
        """
        return False

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """
        Process a MIDI message.

        Args:
            status: MIDI status byte
            data1: MIDI data byte 1
            data2: MIDI data byte 2

        Returns:
            True if message was handled, False otherwise
        """
        return False

    def get_presets(self) -> dict[str, dict[str, Any]]:
        """
        Get plugin presets.

        Returns:
            Dictionary of preset name -> parameter dictionary
        """
        return {}

    def load_preset(self, preset_name: str) -> bool:
        """
        Load a plugin preset.

        Args:
            preset_name: Name of preset to load

        Returns:
            True if loaded successfully, False otherwise
        """
        return False

    def save_preset(self, preset_name: str) -> bool:
        """
        Save current parameters as a preset.

        Args:
            preset_name: Name for the preset

        Returns:
            True if saved successfully, False otherwise
        """
        return False


class SynthesisFeaturePlugin(BaseEnginePlugin):
    """
    Plugin for extending synthesis engines with additional synthesis features.

    Examples: formant filters, ring modulation, advanced wavetable features.
    """

    def get_synthesis_features(self) -> dict[str, Any]:
        """
        Get synthesis features provided by this plugin.

        Returns:
            Dictionary describing available synthesis features
        """
        return {}


class ModulationPlugin(BaseEnginePlugin):
    """
    Plugin for extending modulation capabilities.

    Examples: additional LFO shapes, envelope curves, modulation matrix extensions.
    """

    def get_modulation_features(self) -> dict[str, Any]:
        """
        Get modulation features provided by this plugin.

        Returns:
            Dictionary describing modulation capabilities
        """
        return {}


class EffectsPlugin(BaseEnginePlugin):
    """
    Plugin for adding built-in effects processing to engines.

    Examples: distortion, chorus, phaser built into the engine.
    """

    def get_effects_chain(self) -> list[dict[str, Any]]:
        """
        Get the effects chain provided by this plugin.

        Returns:
            List of effect configurations
        """
        return []


class MIDIPlugin(BaseEnginePlugin):
    """
    Plugin for extending MIDI processing capabilities.

    Examples: SysEx handling, NRPN processing, custom MIDI mappings.
    """

    def get_midi_features(self) -> dict[str, Any]:
        """
        Get MIDI features provided by this plugin.

        Returns:
            Dictionary describing MIDI capabilities
        """
        return {}


# Plugin factory function type
PluginFactory = Callable[[], BaseEnginePlugin]


def create_plugin_from_metadata(metadata: PluginMetadata,
                               plugin_class: type[BaseEnginePlugin]) -> BaseEnginePlugin:
    """
    Create a plugin instance from metadata and class.

    Args:
        metadata: Plugin metadata
        plugin_class: Plugin class to instantiate

    Returns:
        Plugin instance
    """
    return plugin_class(metadata)
