"""
Plugin Registry System

Manages discovery, loading, and lifecycle of engine plugins.
Provides dependency resolution, compatibility checking, and plugin management.
"""

from __future__ import annotations

import importlib
import inspect
import traceback
from pathlib import Path
from typing import Any

from .base_plugin import (
    BaseEnginePlugin,
    PluginCompatibility,
    PluginLoadContext,
    PluginType,
)


class PluginLoadError(Exception):
    """Exception raised when plugin loading fails."""

    pass


class PluginDependencyError(Exception):
    """Exception raised when plugin dependencies cannot be satisfied."""

    pass


class PluginRegistry:
    """
    Registry for managing engine plugins.

    Handles plugin discovery, loading, dependency resolution, and lifecycle management.
    Provides a central point for plugin registration and access.
    """

    def __init__(self):
        self._plugins: dict[str, BaseEnginePlugin] = {}  # name -> plugin instance
        self._plugin_classes: dict[str, type[BaseEnginePlugin]] = {}  # name -> plugin class
        self._loaded_plugins: set[str] = set()  # Currently loaded plugin names
        self._plugin_dependencies: dict[str, set[str]] = {}  # plugin -> dependencies
        self._reverse_dependencies: dict[str, set[str]] = {}  # plugin -> dependents

        # Plugin search paths
        self._search_paths = [
            Path(__file__).parent / "jupiter_x",
            Path(__file__).parent / "yamaha",
            Path(__file__).parent / "roland",
            # Add more synthesizer-specific plugin directories as needed
        ]

    def register_plugin_class(self, name: str, plugin_class: type[BaseEnginePlugin]) -> bool:
        """
        Register a plugin class with the registry.

        Args:
            name: Unique plugin name
            plugin_class: Plugin class to register

        Returns:
            True if registered successfully, False otherwise
        """
        try:
            if name in self._plugin_classes:
                print(f"Warning: Plugin '{name}' already registered, overwriting")

            self._plugin_classes[name] = plugin_class

            # Extract dependencies from class metadata if available
            if hasattr(plugin_class, "get_plugin_metadata"):
                try:
                    # Use class method to get metadata
                    metadata = plugin_class.get_plugin_metadata()
                    self._plugin_dependencies[name] = set(metadata.dependencies)

                    # Update reverse dependencies
                    for dep in metadata.dependencies:
                        if dep not in self._reverse_dependencies:
                            self._reverse_dependencies[dep] = set()
                        self._reverse_dependencies[dep].add(name)
                except Exception as e:
                    print(f"Warning: Could not extract metadata from plugin '{name}': {e}")
                    self._plugin_dependencies[name] = set()
            elif hasattr(plugin_class, "get_metadata"):
                try:
                    # Fallback: Create temporary instance to get metadata
                    temp_instance = plugin_class()
                    metadata = temp_instance.get_metadata()
                    self._plugin_dependencies[name] = set(metadata.dependencies)

                    # Update reverse dependencies
                    for dep in metadata.dependencies:
                        if dep not in self._reverse_dependencies:
                            self._reverse_dependencies[dep] = set()
                        self._reverse_dependencies[dep].add(name)
                except Exception as e:
                    print(f"Warning: Could not extract metadata from plugin '{name}': {e}")
                    self._plugin_dependencies[name] = set()

            return True

        except Exception as e:
            print(f"Failed to register plugin class '{name}': {e}")
            return False

    def load_plugin(
        self,
        name: str,
        engine_instance: Any = None,
        sample_rate: int = 44100,
        block_size: int = 1024,
    ) -> bool:
        """
        Load a plugin by name.

        Args:
            name: Plugin name to load
            engine_instance: Engine instance to load plugin for
            sample_rate: Audio sample rate
            block_size: Processing block size

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Check if already loaded
            if name in self._loaded_plugins:
                return True

            # Check if plugin class is registered
            if name not in self._plugin_classes:
                raise PluginLoadError(f"Plugin '{name}' not registered")

            # Resolve dependencies first
            self._resolve_dependencies(name)

            # Create plugin instance
            plugin_class = self._plugin_classes[name]
            plugin_instance = plugin_class()

            # Create load context
            context = PluginLoadContext(
                engine_instance=engine_instance,
                sample_rate=sample_rate,
                block_size=block_size,
                plugin_registry=self,
            )

            # Load the plugin
            if not plugin_instance.load(context):
                raise PluginLoadError(f"Plugin '{name}' failed to load")

            # Store loaded plugin
            self._plugins[name] = plugin_instance
            self._loaded_plugins.add(name)

            print(f"✅ Plugin '{name}' loaded successfully")
            return True

        except Exception as e:
            print(f"Failed to load plugin '{name}': {e}")
            traceback.print_exc()
            return False

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin by name.

        Args:
            name: Plugin name to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if name not in self._loaded_plugins:
                return True

            # Check for dependents
            if name in self._reverse_dependencies:
                dependents = self._reverse_dependencies[name]
                active_dependents = [d for d in dependents if d in self._loaded_plugins]
                if active_dependents:
                    raise PluginDependencyError(
                        f"Cannot unload '{name}' - still required by: {active_dependents}"
                    )

            # Unload the plugin
            plugin = self._plugins[name]
            if not plugin.unload():
                print(f"Warning: Plugin '{name}' may not have unloaded cleanly")

            # Remove from registry
            del self._plugins[name]
            self._loaded_plugins.remove(name)

            print(f"✅ Plugin '{name}' unloaded successfully")
            return True

        except Exception as e:
            print(f"Failed to unload plugin '{name}': {e}")
            return False

    def get_plugin(self, name: str) -> BaseEnginePlugin | None:
        """
        Get a loaded plugin instance.

        Args:
            name: Plugin name

        Returns:
            Plugin instance if loaded, None otherwise
        """
        return self._plugins.get(name)

    def is_plugin_loaded(self, name: str) -> bool:
        """
        Check if a plugin is currently loaded.

        Args:
            name: Plugin name

        Returns:
            True if loaded, False otherwise
        """
        return name in self._loaded_plugins

    def get_loaded_plugins(self) -> dict[str, BaseEnginePlugin]:
        """
        Get all currently loaded plugins.

        Returns:
            Dictionary of plugin name -> plugin instance
        """
        return self._plugins.copy()

    def get_available_plugins(self) -> dict[str, type[BaseEnginePlugin]]:
        """
        Get all registered plugin classes.

        Returns:
            Dictionary of plugin name -> plugin class
        """
        return self._plugin_classes.copy()

    def discover_plugins(self) -> int:
        """
        Discover and register plugins from search paths.

        Returns:
            Number of plugins discovered
        """
        discovered_count = 0

        for search_path in self._search_paths:
            if not search_path.exists():
                continue

            # Discover plugins in this path
            count = self._discover_plugins_in_path(search_path)
            discovered_count += count

        print(f"🔍 Discovered {discovered_count} plugins")
        return discovered_count

    def _discover_plugins_in_path(self, path: Path) -> int:
        """Discover plugins in a specific path."""
        discovered = 0

        # Look for Python files
        for py_file in path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                # Import the module
                module_name = f"synth.engine.plugins.{path.name}.{py_file.stem}"
                module = importlib.import_module(module_name)

                # Look for plugin classes
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseEnginePlugin)
                        and obj != BaseEnginePlugin
                        and obj.__name__
                        not in [
                            "SynthesisFeaturePlugin",
                            "ModulationPlugin",
                            "EffectsPlugin",
                            "MIDIPlugin",
                        ]
                    ):
                        # Skip abstract base classes
                        try:
                            # Try to create a temporary instance to check if it's concrete
                            temp_instance = obj.__new__(obj)
                            # If we get here, it's not abstract
                        except TypeError:
                            # TypeError means it's abstract and can't be instantiated
                            continue

                        # Register the plugin
                        plugin_name = f"{path.name}.{py_file.stem}.{name}"
                        self.register_plugin_class(plugin_name, obj)
                        discovered += 1

            except Exception as e:
                print(f"Warning: Failed to load plugin from {py_file}: {e}")

        return discovered

    def _resolve_dependencies(self, plugin_name: str) -> None:
        """
        Resolve dependencies for a plugin.

        Args:
            plugin_name: Plugin to resolve dependencies for

        Raises:
            PluginDependencyError: If dependencies cannot be satisfied
        """
        dependencies = self._plugin_dependencies.get(plugin_name, set())

        for dep in dependencies:
            # Check if dependency is registered
            if dep not in self._plugin_classes:
                raise PluginDependencyError(
                    f"Dependency '{dep}' not found for plugin '{plugin_name}'"
                )

            # Load dependency if not already loaded
            if dep not in self._loaded_plugins:
                self.load_plugin(dep)

    def get_plugin_info(self, name: str) -> dict[str, Any] | None:
        """
        Get information about a plugin.

        Args:
            name: Plugin name

        Returns:
            Plugin information dictionary or None if not found
        """
        plugin = self._plugins.get(name)
        if plugin:
            metadata = plugin.get_metadata()
            return {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "type": metadata.plugin_type.value,
                "compatibility": metadata.compatibility.value,
                "target_engines": metadata.target_engines,
                "dependencies": list(metadata.dependencies),
                "loaded": True,
                "enabled": plugin.is_enabled,
                "active": plugin.is_active(),
            }

        plugin_class = self._plugin_classes.get(name)
        if plugin_class:
            try:
                # Try class method first, then fallback to instance method
                if hasattr(plugin_class, "get_plugin_metadata"):
                    metadata = plugin_class.get_plugin_metadata()
                else:
                    temp_instance = plugin_class()
                    metadata = temp_instance.get_metadata()
                return {
                    "name": metadata.name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "type": metadata.plugin_type.value,
                    "compatibility": metadata.compatibility.value,
                    "target_engines": metadata.target_engines,
                    "dependencies": list(metadata.dependencies),
                    "loaded": False,
                    "enabled": False,
                    "active": False,
                }
            except Exception:
                pass

        return None

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[str]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to find

        Returns:
            List of plugin names
        """
        matching_plugins = []

        for name, plugin_class in self._plugin_classes.items():
            try:
                # Try class method first, then fallback to instance method
                if hasattr(plugin_class, "get_plugin_metadata"):
                    metadata = plugin_class.get_plugin_metadata()
                else:
                    temp_instance = plugin_class()
                    metadata = temp_instance.get_metadata()
                if metadata.plugin_type == plugin_type:
                    matching_plugins.append(name)
            except Exception:
                continue

        return matching_plugins

    def get_plugins_for_engine(self, engine_type: str) -> list[str]:
        """
        Get all plugins compatible with a specific engine type.

        Args:
            engine_type: Engine type (e.g., 'fm', 'wavetable')

        Returns:
            List of compatible plugin names
        """
        compatible_plugins = []

        for name, plugin_class in self._plugin_classes.items():
            try:
                # Try class method first, then fallback to instance method
                if hasattr(plugin_class, "get_plugin_metadata"):
                    metadata = plugin_class.get_plugin_metadata()
                else:
                    temp_instance = plugin_class()
                    metadata = temp_instance.get_metadata()
                if (
                    engine_type in metadata.target_engines
                    or metadata.compatibility == PluginCompatibility.UNIVERSAL
                ):
                    compatible_plugins.append(name)
            except Exception:
                continue

        return compatible_plugins

    def validate_plugin_compatibility(
        self, plugin_name: str, engine_type: str, engine_version: str = "1.0.0"
    ) -> bool:
        """
        Validate plugin compatibility with an engine.

        Args:
            plugin_name: Plugin to validate
            engine_type: Engine type
            engine_version: Engine version

        Returns:
            True if compatible, False otherwise
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return False

        return plugin.check_compatibility(engine_type, engine_version)

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """
        Get the plugin dependency graph.

        Returns:
            Dictionary of plugin -> list of dependencies
        """
        return {name: list(deps) for name, deps in self._plugin_dependencies.items()}

    def reload_plugin(self, name: str) -> bool:
        """
        Reload a plugin (unload and load again).

        Args:
            name: Plugin name to reload

        Returns:
            True if reloaded successfully, False otherwise
        """
        try:
            if name in self._loaded_plugins:
                self.unload_plugin(name)
            return self.load_plugin(name)
        except Exception as e:
            print(f"Failed to reload plugin '{name}': {e}")
            return False

    def clear_registry(self) -> None:
        """Clear all plugins from registry."""
        # Unload all plugins first
        for name in list(self._loaded_plugins):
            self.unload_plugin(name)

        self._plugins.clear()
        self._plugin_classes.clear()
        self._loaded_plugins.clear()
        self._plugin_dependencies.clear()
        self._reverse_dependencies.clear()

        print("🧹 Plugin registry cleared")


# Global plugin registry instance
_global_registry = None


def get_global_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_global_plugin_registry() -> None:
    """Reset the global plugin registry."""
    global _global_registry
    if _global_registry:
        _global_registry.clear_registry()
    _global_registry = PluginRegistry()
