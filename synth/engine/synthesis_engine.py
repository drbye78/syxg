"""
Advanced Synthesis Engine Registry System - Unified Region-Based Architecture

Production-quality engine registry with dynamic loading, plugin architecture,
content-based selection, and XGML v3.0 integration. Supports runtime engine
management, performance monitoring, and intelligent synthesis method selection.

This is the REFACTORED version with unified region-based architecture supporting:
- Lazy initialization of regions and samples
- On-demand sample loading
- Multi-zone preset support (key splits, velocity splits)
- Unified interface across all synthesis engines

Features:
- Dynamic engine loading/unloading
- Plugin-style third-party engine support
- Content analysis for optimal engine selection
- Runtime configuration and optimization
- XGML v3.0 engine registry integration
- Performance monitoring and resource management
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import numpy as np
import threading
import time
import importlib
import importlib.util
import inspect
import os
from pathlib import Path

# Import new region-based architecture
from .region_descriptor import RegionDescriptor
from .preset_info import PresetInfo


class SynthesisEngine(ABC):
    """
    Abstract base class for synthesis engines - REFACTORED VERSION.

    Defines the standard interface that all synthesis engines must implement,
    providing a consistent way to generate audio regardless of the underlying
    synthesis method.

    This refactored version uses a region-based architecture with:
    - PresetInfo for lightweight preset metadata
    - RegionDescriptor for lazy region matching
    - IRegion for unified region interface
    - On-demand sample loading

    This abstraction enables:
    - Modular synthesis engine swapping
    - Consistent parameter handling across engines
    - Standardized audio generation interface
    - Engine capability discovery and metadata
    - Multi-zone preset support (key/velocity splits)
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
        """
        self.sample_rate = sample_rate
        self.block_size = block_size

        # S.Art2 articulation support - ENABLED BY DEFAULT
        # All regions created by this engine will be S.Art2-enabled
        self.sart2_enabled = True
        self.sart2_factory = None  # Set by ModernXGSynthesizer

    # ========== PRESET MANAGEMENT (NEW) ==========

    @abstractmethod
    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get preset metadata without loading regions.

        Returns lightweight PresetInfo with region descriptors.
        Called at program change time.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            PresetInfo with all region descriptors, or None if not found
        """
        pass

    @abstractmethod
    def get_all_region_descriptors(
        self, bank: int, program: int
    ) -> list[RegionDescriptor]:
        """
        Get ALL region descriptors for a preset.

        Returns descriptors for ALL zones/layers in the preset.
        Does NOT load sample data or create region instances.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            List of all RegionDescriptor objects for this preset
        """
        pass

    # ========== REGION CREATION (NEW) ==========

    def create_region(
        self, descriptor: RegionDescriptor, sample_rate: int
    ) -> IRegion:
        """
        Create a region instance from a descriptor.

        Called at note-on time for matching regions.
        Wraps base region with S.Art2 if enabled.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            IRegion instance (S.Art2-wrapped if enabled)
        """
        # Create base region (engine-specific implementation)
        base_region = self._create_base_region(descriptor, sample_rate)

        # Wrap with S.Art2 if enabled
        if self.sart2_enabled and self.sart2_factory:
            return self.sart2_factory.create_sart2_region(base_region)

        return base_region

    @abstractmethod
    def _create_base_region(
        self, descriptor: RegionDescriptor, sample_rate: int
    ) -> IRegion:
        """
        Create base region without S.Art2 wrapper.

        Engine-specific implementation creates the base region type.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            Base IRegion instance (SF2, FM, Additive, etc.)
        """
        pass

    @abstractmethod
    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for a region (SF2/SFZ only).

        Called when region is about to play.
        Returns True if sample loaded successfully.
        For algorithmic engines, this is a no-op (returns True).

        Args:
            region: Region instance to load sample for

        Returns:
            True if sample loaded or not needed, False if loading failed
        """
        pass

    # ========== LEGACY METHODS (DEPRECATED - kept for transition) ==========

    def get_voice_parameters(
        self, program: int, bank: int = 0, note: int = 60, velocity: int = 100
    ) -> dict[str, Any] | None:
        """
        Get voice parameters for a program/bank combination.

        DEPRECATED: Use get_preset_info() and get_regions_for_note() instead.
        This method is kept for backward compatibility during transition.

        Args:
            program: MIDI program number (0-127)
            bank: MIDI bank number (0-16383)
            note: MIDI note for zone matching (default 60)
            velocity: MIDI velocity for zone matching (default 100)

        Returns:
            Voice parameter dictionary or None if not supported
        """
        # Default implementation using new architecture
        preset_info = self.get_preset_info(bank, program)
        if not preset_info:
            return None

        # Get matching regions and return first one's params
        matching = preset_info.get_matching_descriptors(note, velocity)
        if matching and matching[0].generator_params:
            return matching[0].generator_params

        return None

    def get_engine_type(self) -> str:
        """
        Get the engine type identifier.

        Returns:
            Engine type string ('sf2', 'fm', 'additive', etc.)
        """
        return "unknown"

    def create_partial(
        self, partial_params: dict[str, Any], sample_rate: int
    ) -> SynthesisPartial:
        """
        Create a partial instance for this engine.

        DEPRECATED: Use create_region() instead.
        This method is kept for backward compatibility during transition.

        Args:
            partial_params: Parameters for the partial
            sample_rate: Audio sample rate

        Returns:
            SynthesisPartial instance configured for this engine
        """
        # Default implementation - engines should override if they support partials
        raise NotImplementedError(
            "create_partial() not implemented. Use create_region()."
        )

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported file formats.

        Returns:
            List of file extensions this engine can load
        """
        return []

    def get_max_polyphony(self) -> int:
        """
        Get maximum polyphony supported by this engine.

        Returns:
            Maximum number of simultaneous voices
        """
        return 64  # Default

    def supports_modulation(self, modulation_type: str) -> bool:
        """
        Check if engine supports a specific modulation type.

        Args:
            modulation_type: Type of modulation ('pitch', 'filter', 'amp', etc.)

        Returns:
            True if modulation type is supported
        """
        return modulation_type in ["pitch", "filter", "amp"]

    def get_parameter_info(self, parameter_name: str) -> dict[str, Any] | None:
        """
        Get information about a parameter.

        Args:
            parameter_name: Name of parameter

        Returns:
            Parameter information dictionary or None if parameter not supported
        """
        return None

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and normalize parameters.

        Args:
            parameters: Raw parameter dictionary

        Returns:
            Validated and normalized parameter dictionary
        """
        # Default implementation: pass through unchanged
        return parameters.copy()

    def get_memory_usage(self) -> dict[str, Any]:
        """
        Get current memory usage statistics.

        Returns:
            Memory usage information
        """
        return {"samples_loaded": 0, "memory_used_mb": 0.0, "cache_efficiency": 0.0}

    def optimize_for_polyphony(self, target_polyphony: int) -> None:
        """
        Optimize engine for target polyphony level.

        Args:
            target_polyphony: Target number of simultaneous voices
        """
        pass

    def reset(self) -> None:
        """Reset engine to clean state."""
        pass

    def cleanup(self) -> None:
        """Clean up engine resources."""
        pass


class EnginePluginManager:
    """
    Manages third-party engine plugins with dynamic loading.

    Supports plugin discovery, loading, and management for extending
    the synthesizer with custom synthesis engines.
    """

    def __init__(self, plugin_dirs: list[str | Path] | None = None):
        """
        Initialize plugin manager.

        Args:
            plugin_dirs: Directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or [Path(__file__).parent / "plugins"]
        self.loaded_plugins: dict[str, dict[str, Any]] = {}
        self.plugin_lock = threading.RLock()

    def discover_plugins(self) -> dict[str, dict[str, Any]]:
        """
        Discover available plugins in configured directories.

        Returns:
            Dictionary of discovered plugins with metadata
        """
        discovered = {}

        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue

            # Look for Python files that might be plugins
            for py_file in plugin_path.glob("*.py"):
                try:
                    plugin_info = self._analyze_plugin_file(py_file)
                    if plugin_info:
                        plugin_name = plugin_info["name"]
                        discovered[plugin_name] = plugin_info
                except Exception as e:
                    print(f"Error analyzing plugin {py_file}: {e}")

        return discovered

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a specific plugin by name.

        Args:
            plugin_name: Name of plugin to load

        Returns:
            True if plugin loaded successfully
        """
        with self.plugin_lock:
            if plugin_name in self.loaded_plugins:
                return True  # Already loaded

            discovered = self.discover_plugins()
            if plugin_name not in discovered:
                print(f"Plugin {plugin_name} not found")
                return False

            plugin_info = discovered[plugin_name]

            try:
                # Import the plugin module
                module_path = plugin_info["module_path"]
                spec = importlib.util.spec_from_file_location(plugin_name, module_path)
                if spec is None or spec.loader is None:
                    print(f"No valid module spec found for {plugin_name}")
                    return False
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find engine classes in the module
                engine_classes = []
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, SynthesisEngine)
                        and obj != SynthesisEngine
                    ):
                        engine_classes.append(obj)

                if not engine_classes:
                    print(f"No engine classes found in plugin {plugin_name}")
                    return False

                # Store loaded plugin info
                self.loaded_plugins[plugin_name] = {
                    "info": plugin_info,
                    "module": module,
                    "engine_classes": engine_classes,
                    "loaded_at": time.time(),
                }

                print(
                    f"✅ Loaded plugin {plugin_name} with {len(engine_classes)} engine(s)"
                )
                return True

            except Exception as e:
                print(f"❌ Failed to load plugin {plugin_name}: {e}")
                return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if plugin unloaded successfully
        """
        with self.plugin_lock:
            if plugin_name not in self.loaded_plugins:
                return False

            # Clean up plugin resources
            plugin_data = self.loaded_plugins[plugin_name]

            # Call cleanup on module if available
            if hasattr(plugin_data["module"], "cleanup"):
                try:
                    plugin_data["module"].cleanup()
                except Exception as e:
                    print(f"Error cleaning up plugin {plugin_name}: {e}")

            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]

            print(f"✅ Unloaded plugin {plugin_name}")
            return True

    def get_loaded_plugins(self) -> dict[str, dict[str, Any]]:
        """
        Get information about loaded plugins.

        Returns:
            Dictionary of loaded plugins with metadata
        """
        with self.plugin_lock:
            return {
                name: {
                    "info": data["info"],
                    "engine_count": len(data["engine_classes"]),
                    "loaded_at": data["loaded_at"],
                }
                for name, data in self.loaded_plugins.items()
            }

    def _analyze_plugin_file(self, file_path: Path) -> dict[str, Any] | None:
        """
        Analyze a Python file to determine if it's a valid plugin.

        Args:
            file_path: Path to Python file

        Returns:
            Plugin metadata or None if not a valid plugin
        """
        try:
            # Read file content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Look for plugin metadata in comments or docstrings
            plugin_info = {
                "name": file_path.stem,
                "path": str(file_path),
                "module_path": str(file_path),
                "description": "",
                "version": "1.0.0",
                "author": "Unknown",
                "engines": [],
            }

            # Extract metadata from special comments
            lines = content.split("\n")
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if line.startswith("# plugin:"):
                    parts = line[9:].split("=", 1)
                    if len(parts) == 2:
                        key, value = parts
                        plugin_info[key.strip()] = value.strip().strip("\"'")
                elif line.startswith('"""') and "plugin" in line.lower():
                    # Found docstring with plugin info
                    break

            # Try to find engine classes by inspecting the module
            try:
                spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                module = None
                if spec is None or spec.loader is None:
                    # Can't inspect module, but file exists - use content analysis only
                    pass
                else:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                engines = []
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, SynthesisEngine)
                        and obj != SynthesisEngine
                    ):
                        engine_info = {
                            "name": name,
                            "class": obj,
                            "description": obj.__doc__.split("\n")[0]
                            if obj.__doc__
                            else "",
                        }
                        engines.append(engine_info)

                plugin_info["engines"] = engines

            except Exception:
                # Can't inspect module, but file exists
                pass

            return (
                plugin_info
                if plugin_info["engines"] or "engine" in content.lower()
                else None
            )

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None


class ContentAnalyzer:
    """
    Analyzes content to determine optimal synthesis engine.

    Uses machine learning and heuristic analysis to recommend the best
    engine for specific types of audio content.
    """

    def __init__(self):
        self.analysis_cache = {}
        self.cache_lock = threading.RLock()

    def analyze_content(self, content_info: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze content characteristics to recommend engines.

        Args:
            content_info: Information about the content (file path, metadata, etc.)

        Returns:
            Analysis results with engine recommendations
        """
        cache_key = self._get_cache_key(content_info)

        with self.cache_lock:
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

        # Perform content analysis
        analysis = self._perform_content_analysis(content_info)

        # Cache result
        with self.cache_lock:
            self.analysis_cache[cache_key] = analysis

        return analysis

    def _perform_content_analysis(self, content_info: dict[str, Any]) -> dict[str, Any]:
        """
        Perform detailed content analysis.

        Args:
            content_info: Content information

        Returns:
            Analysis results
        """
        results = {
            "recommended_engines": [],
            "confidence_scores": {},
            "content_type": "unknown",
            "characteristics": {},
        }

        file_path = content_info.get("file_path")
        if not file_path:
            return results

        # Basic file extension analysis
        ext = Path(file_path).suffix.lower()

        # Analyze based on file type
        if ext == ".sf2":
            results["content_type"] = "soundfont"
            results["recommended_engines"] = ["sf2"]
            results["confidence_scores"] = {"sf2": 1.0}
            results["characteristics"] = {
                "polyphony": "high",
                "complexity": "high",
                "realism": "high",
            }
        elif ext in [".wav", ".aiff", ".flac"]:
            results["content_type"] = "sample"
            results["recommended_engines"] = ["wavetable", "granular"]
            results["confidence_scores"] = {"wavetable": 0.8, "granular": 0.6}
            results["characteristics"] = {
                "polyphony": "medium",
                "complexity": "low",
                "realism": "high",
            }
        elif ext in [".sfz"]:
            results["content_type"] = "sfz_program"
            results["recommended_engines"] = ["sfz"]
            results["confidence_scores"] = {"sfz": 1.0}
            results["characteristics"] = {
                "polyphony": "high",
                "complexity": "medium",
                "realism": "high",
            }
        else:
            # Unknown format - provide general recommendations
            results["content_type"] = "unknown"
            results["recommended_engines"] = ["sf2", "fm", "physical"]
            results["confidence_scores"] = {"sf2": 0.5, "fm": 0.4, "physical": 0.3}

        return results

    def _get_cache_key(self, content_info: dict[str, Any]) -> str:
        """Generate cache key for content analysis."""
        file_path = content_info.get("file_path", "")
        mtime = content_info.get("mtime", 0)
        size = content_info.get("size", 0)
        return f"{file_path}:{mtime}:{size}"


class PerformanceOptimizer:
    """
    Optimizes engine performance based on usage patterns and system resources.

    Monitors engine performance and automatically adjusts resource allocation
    for optimal synthesis quality and efficiency.
    """

    def __init__(self):
        self.performance_history = {}
        self.optimization_lock = threading.RLock()

    def update_performance_metrics(self, engine_type: str, metrics: dict[str, Any]):
        """
        Update performance metrics for an engine.

        Args:
            engine_type: Type of engine
            metrics: Performance metrics (CPU usage, latency, quality, etc.)
        """
        with self.optimization_lock:
            if engine_type not in self.performance_history:
                self.performance_history[engine_type] = []

            # Keep last 100 measurements
            history = self.performance_history[engine_type]
            history.append({"timestamp": time.time(), "metrics": metrics})

            if len(history) > 100:
                history.pop(0)

    def get_optimization_recommendations(self, engine_type: str) -> dict[str, Any]:
        """
        Get optimization recommendations for an engine.

        Args:
            engine_type: Engine type to optimize

        Returns:
            Optimization recommendations
        """
        with self.optimization_lock:
            history = self.performance_history.get(engine_type, [])

            if not history:
                return {"recommendations": []}

            # Analyze performance trends
            recent_metrics = [
                h["metrics"] for h in history[-10:]
            ]  # Last 10 measurements

            recommendations = []

            # CPU usage analysis
            cpu_usage = [m.get("cpu_percent", 0) for m in recent_metrics]
            avg_cpu = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0

            if avg_cpu > 80:
                recommendations.append(
                    {
                        "type": "reduce_polyphony",
                        "reason": f"High CPU usage ({avg_cpu:.1f}%)",
                        "action": "Reduce maximum polyphony by 20%",
                    }
                )

            # Latency analysis
            latencies = [m.get("latency_ms", 0) for m in recent_metrics]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0

            if avg_latency > 10:
                recommendations.append(
                    {
                        "type": "optimize_buffering",
                        "reason": f"High latency ({avg_latency:.1f}ms)",
                        "action": "Increase buffer size or reduce processing complexity",
                    }
                )

            return {"recommendations": recommendations}

    def apply_optimization(
        self, engine: SynthesisEngine, recommendation: dict[str, Any]
    ) -> bool:
        """
        Apply an optimization recommendation to an engine.

        Args:
            engine: Engine to optimize
            recommendation: Optimization recommendation

        Returns:
            True if optimization applied successfully
        """
        try:
            rec_type = recommendation.get("type")

            if rec_type == "reduce_polyphony":
                current_polyphony = engine.get_max_polyphony()
                new_polyphony = int(current_polyphony * 0.8)  # Reduce by 20%
                engine.optimize_for_polyphony(new_polyphony)
                print(
                    f"Optimized {engine.get_engine_type()} polyphony: {current_polyphony} -> {new_polyphony}"
                )
                return True

            elif rec_type == "optimize_buffering":
                # This would typically adjust buffer sizes or processing parameters
                print(f"Applied buffering optimization to {engine.get_engine_type()}")
                return True

            return False

        except Exception as e:
            print(f"Failed to apply optimization: {e}")
            return False


class SynthesisEngineRegistry:
    """
    Advanced Synthesis Engine Registry with XGML v3.0 Integration

    Production-quality engine registry supporting:
    - Dynamic plugin loading and management
    - Content-based engine selection
    - Runtime performance optimization
    - XGML v3.0 configuration integration
    - Thread-safe operations and monitoring
    """

    def __init__(self):
        """Initialize advanced engine registry."""
        self.lock = threading.RLock()

        # Core registry data
        self._engines: dict[str, dict[str, Any]] = {}
        self._engine_classes: dict[str, type] = {}
        self._format_map: dict[str, list[str]] = {}
        self._priority_order: list[str] = []

        # Advanced components
        self.plugin_manager = EnginePluginManager()
        self.content_analyzer = ContentAnalyzer()
        self.performance_optimizer = PerformanceOptimizer()

        # XGML v3.0 integration
        self.xgml_engine_config: dict[str, Any] = {}

        # Runtime monitoring
        self.engine_usage_stats: dict[str, dict[str, Any]] = {}
        self.last_optimization_check = time.time()

    def register_engine(
        self,
        engine: SynthesisEngine,
        engine_type: str,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a synthesis engine with enhanced metadata support.

        Args:
            engine: Engine instance
            engine_type: Unique engine type identifier
            priority: Engine priority (higher = preferred)
            metadata: Additional metadata for XGML integration
        """
        with self.lock:
            engine_info = engine.get_engine_info()
            supported_formats = engine.get_supported_formats()

            # Enhanced engine data structure
            self._engines[engine_type] = {
                "info": engine_info,
                "class": engine.__class__,
                "priority": priority,
                "formats": supported_formats,
                "instance": engine,
                "metadata": metadata or {},
                "registered_at": time.time(),
                "usage_count": 0,
                "last_used": None,
                "performance_metrics": {},
            }

            self._engine_classes[engine_type] = engine.__class__

            # Update mappings
            self._update_format_mapping(engine_type, supported_formats)
            self._update_priority_order()

            # Initialize usage stats
            self.engine_usage_stats[engine_type] = {
                "total_requests": 0,
                "successful_requests": 0,
                "average_response_time": 0.0,
                "error_count": 0,
            }

            print(f"✅ Registered engine: {engine_type} (priority: {priority})")

    def load_plugin_engines(self, plugin_name: str) -> int:
        """
        Load all engines from a plugin.

        Args:
            plugin_name: Name of plugin to load

        Returns:
            Number of engines loaded from plugin
        """
        if not self.plugin_manager.load_plugin(plugin_name):
            return 0

        plugin_data = self.plugin_manager.loaded_plugins.get(plugin_name)
        if not plugin_data:
            return 0

        engines_loaded = 0
        for engine_class in plugin_data["engine_classes"]:
            try:
                # Create engine instance with default parameters
                engine_instance = engine_class()

                # Generate engine type from class name
                engine_type = engine_class.__name__.lower().replace("engine", "")

                # Register the engine
                self.register_engine(
                    engine_instance,
                    engine_type,
                    priority=1,  # Default priority for plugins
                    metadata={"plugin": plugin_name, "source": "plugin"},
                )

                engines_loaded += 1

            except Exception as e:
                print(
                    f"Failed to load engine {engine_class.__name__} from plugin {plugin_name}: {e}"
                )

        return engines_loaded

    def select_engine_for_content(
        self, content_info: dict[str, Any], context: dict[str, Any] | None = None
    ) -> str | None:
        """
        Select optimal engine for content using advanced analysis.

        Args:
            content_info: Information about the content
            context: Additional context (polyphony needs, quality requirements, etc.)

        Returns:
            Recommended engine type
        """
        with self.lock:
            # Analyze content characteristics
            analysis = self.content_analyzer.analyze_content(content_info)

            # Consider context factors
            if context:
                analysis = self._apply_context_filters(analysis, context)

            # Get available engines that match content type
            recommended_engines = analysis.get("recommended_engines", [])

            # Filter by available engines and select best match
            available_matches = [
                eng for eng in recommended_engines if eng in self._engines
            ]

            if not available_matches:
                # Fallback to highest priority engine
                return self._priority_order[0] if self._priority_order else None

            # Return highest priority match
            return max(available_matches, key=lambda x: self._engines[x]["priority"])

    def configure_from_xgml(self, xgml_config: dict[str, Any]) -> bool:
        """
        Configure registry from XGML v3.0 synthesis_engines section.

        Args:
            xgml_config: XGML synthesis_engines configuration

        Returns:
            True if configuration applied successfully
        """
        with self.lock:
            try:
                self.xgml_engine_config = xgml_config

                registry_config = xgml_config.get("registry", {})

                # Update engine priorities
                if "engine_priorities" in registry_config:
                    priorities = registry_config["engine_priorities"]
                    for engine_type, priority in priorities.items():
                        if engine_type in self._engines:
                            self._engines[engine_type]["priority"] = priority

                    self._update_priority_order()

                # Configure channel assignments
                channel_assignments = xgml_config.get("channel_engines", {})
                if channel_assignments:
                    print(
                        f"🎹 Configured {len(channel_assignments)} channel engine assignments"
                    )

                # Configure individual engines
                engine_configs = {}
                for engine_name in [
                    "sf2_engine",
                    "fm_x_engine",
                    "physical_engine",
                    "spectral_engine",
                ]:
                    if engine_name in xgml_config:
                        config = xgml_config[engine_name]
                        engine_type = engine_name.replace("_engine", "")
                        engine_configs[engine_type] = config

                        if engine_type in self._engines and config.get("enabled", True):
                            print(f"🎹 Configured {engine_type} engine")

                print("✅ Applied XGML v3.0 engine registry configuration")
                return True

            except Exception as e:
                print(f"❌ Failed to apply XGML engine configuration: {e}")
                return False

    def optimize_performance(self) -> dict[str, Any]:
        """
        Perform automatic performance optimization across all engines.

        Returns:
            Optimization report
        """
        with self.lock:
            report = {
                "engines_optimized": 0,
                "recommendations_applied": 0,
                "performance_improvements": {},
            }

            current_time = time.time()

            # Only optimize if enough time has passed since last check
            if current_time - self.last_optimization_check < 60:  # 1 minute cooldown
                return report

            self.last_optimization_check = current_time

            # Analyze each engine
            for engine_type, engine_data in self._engines.items():
                engine = engine_data["instance"]

                # Get optimization recommendations
                recommendations = (
                    self.performance_optimizer.get_optimization_recommendations(
                        engine_type
                    )
                )

                # Apply recommendations
                for rec in recommendations.get("recommendations", []):
                    if self.performance_optimizer.apply_optimization(engine, rec):
                        report["recommendations_applied"] += 1

                if recommendations.get("recommendations"):
                    report["engines_optimized"] += 1

            return report

    def get_engine(self, engine_type: str) -> SynthesisEngine | None:
        """
        Get engine instance by type with usage tracking.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine instance or None if not found
        """
        with self.lock:
            if engine_type in self._engines:
                engine_data = self._engines[engine_type]
                engine_data["usage_count"] += 1
                engine_data["last_used"] = time.time()

                # Update usage stats
                if engine_type in self.engine_usage_stats:
                    self.engine_usage_stats[engine_type]["total_requests"] += 1

                return engine_data["instance"]
        return None

    def get_engine_class(self, engine_type: str) -> type | None:
        """Get engine class by type."""
        return self._engine_classes.get(engine_type)

    def create_engine(self, engine_type: str, **kwargs) -> SynthesisEngine | None:
        """
        Create new engine instance with validation.

        Args:
            engine_type: Engine type to create
            **kwargs: Engine constructor arguments

        Returns:
            New engine instance or None if creation failed
        """
        with self.lock:
            engine_class = self.get_engine_class(engine_type)
            if engine_class:
                try:
                    # Validate parameters if engine supports it
                    if hasattr(engine_class, "validate_parameters"):
                        kwargs = engine_class.validate_parameters(kwargs)

                    engine = engine_class(**kwargs)

                    # Update usage stats
                    if engine_type in self.engine_usage_stats:
                        self.engine_usage_stats[engine_type]["successful_requests"] += 1

                    return engine

                except Exception as e:
                    print(f"Failed to create engine {engine_type}: {e}")
                    if engine_type in self.engine_usage_stats:
                        self.engine_usage_stats[engine_type]["error_count"] += 1
                    return None
        return None

    def get_engines_for_format(self, file_format: str) -> list[str]:
        """Get engine types that support a file format, ordered by priority."""
        engine_types = self._format_map.get(file_format.lower(), [])
        return sorted(
            engine_types, key=lambda x: self._engines[x]["priority"], reverse=True
        )

    def get_registered_engines(self) -> dict[str, dict[str, Any]]:
        """Get comprehensive information about all registered engines."""
        with self.lock:
            result = {}
            for engine_type, data in self._engines.items():
                usage_stats = self.engine_usage_stats.get(engine_type, {})

                result[engine_type] = {
                    "info": data["info"],
                    "priority": data["priority"],
                    "formats": data["formats"],
                    "metadata": data["metadata"],
                    "usage": {
                        "count": data["usage_count"],
                        "last_used": data["last_used"],
                        "stats": usage_stats,
                    },
                    "performance": data.get("performance_metrics", {}),
                }
            return result

    def detect_engine_for_file(self, file_path: str) -> str | None:
        """Detect appropriate engine for a file using content analysis."""
        content_info = {
            "file_path": file_path,
            "mtime": os.path.getmtime(file_path) if os.path.exists(file_path) else 0,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        }

        return self.select_engine_for_content(content_info)

    def get_engine_priority(self, engine_type: str) -> int:
        """Get priority of an engine type."""
        return self._engines.get(engine_type, {}).get("priority", 0)

    def set_priority(self, engine_type: str, priority: int):
        """
        Set priority for an engine type.

        Args:
            engine_type: The engine type to set priority for
            priority: The priority value (higher = more preferred)
        """
        if engine_type in self._engines:
            self._engines[engine_type]["priority"] = priority
            self._update_priority_order()
        else:
            raise ValueError(f"Engine type '{engine_type}' not found in registry")

    def get_registry_status(self) -> dict[str, Any]:
        """
        Get comprehensive registry status.

        Returns:
            Detailed status information
        """
        with self.lock:
            return {
                "total_engines": len(self._engines),
                "engine_types": list(self._engines.keys()),
                "priority_order": self._priority_order.copy(),
                "supported_formats": list(self._format_map.keys()),
                "loaded_plugins": self.plugin_manager.get_loaded_plugins(),
                "xgml_configured": bool(self.xgml_engine_config),
                "performance_optimization": self.optimize_performance(),
                "usage_stats": self.engine_usage_stats.copy(),
            }

    def _update_format_mapping(self, engine_type: str, formats: list[str]):
        """Update format to engine mapping."""
        for fmt in formats:
            if fmt not in self._format_map:
                self._format_map[fmt] = []
            if engine_type not in self._format_map[fmt]:
                self._format_map[fmt].append(engine_type)

    def _update_priority_order(self):
        """Update internal priority ordering."""
        self._priority_order = sorted(
            self._engines.keys(),
            key=lambda x: self._engines[x]["priority"],
            reverse=True,
        )

    def _apply_context_filters(
        self, analysis: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply context-based filtering to analysis results.

        Args:
            analysis: Content analysis results
            context: Usage context information

        Returns:
            Filtered analysis results
        """
        filtered = analysis.copy()

        # Consider polyphony requirements
        required_polyphony = context.get("polyphony", "medium")
        if required_polyphony == "high":
            # Prefer engines that support high polyphony
            high_poly_engines = [
                eng
                for eng in filtered["recommended_engines"]
                if self._engines.get(eng, {}).get("info", {}).get("polyphony", "medium")
                in ["high", "unlimited"]
            ]
            if high_poly_engines:
                filtered["recommended_engines"] = high_poly_engines[:3]  # Top 3

        # Consider quality requirements
        quality_requirement = context.get("quality", "medium")
        if quality_requirement == "high":
            # Prioritize engines with high quality characteristics
            pass  # Could implement quality-based filtering

        return filtered

    def get_priority_order(self) -> list[str]:
        """Get engine types ordered by priority."""
        return self._priority_order.copy()


# Import here to avoid circular imports
from ..partial.partial import SynthesisPartial
# Note: Region import removed - use forward references instead to avoid circular import
