"""
Engine Registry - Synthesis Engine Management Architecture

ARCHITECTURAL OVERVIEW:

The XG Engine Registry implements a sophisticated synthesis engine management system
designed for dynamic engine registration, priority-based selection, and capability-driven
discovery in professional audio synthesis environments.

ENGINE MANAGEMENT PHILOSOPHY:

1. DYNAMIC REGISTRATION: Engines register themselves with the system at runtime
2. PRIORITY-BASED SELECTION: Hierarchical priority system for engine selection
3. CAPABILITY-DRIVEN DISCOVERY: Feature-based engine discovery and matching
4. RESOURCE-AWARE OPTIMIZATION: System resource consideration for engine selection
5. FAILURE-TOLERANT DESIGN: Graceful degradation when engines fail to register

ENGINE PRIORITY HIERARCHY:

The registry implements a sophisticated priority system that reflects synthesis quality
and hardware compatibility requirements:

S90/S70 COMPATIBILITY ENGINES (Highest Priority):
- FDSP (10): Formant Dynamic Synthesis Processor - Vocal synthesis
- AN (9): Analog Physical Modeling - RP-PR modeling
- XG (7): XG AWM Synthesis - Core XG implementation

PROFESSIONAL SYNTHESIS ENGINES (Medium Priority):
- SF2 (8): SoundFont 2.0 - Professional sample playback
- FM (6): Frequency Modulation - Algorithmic synthesis
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from typing import Any

from .additive import AdditiveEngine
from .physical_modeling import ANEngine
from .convolution import ConvolutionReverbEngine
from .fdsp import FDSPEngine
from .fm_engine import FMEngine
from .granular import GranularEngine
from ..synthesizers.rendering import ModernXGSynthesizer
from .physical_engine import PhysicalEngine
from .sf2_engine import SF2Engine
from .spectral import SpectralEngine
from .synthesis_engine import SynthesisEngineRegistry
from .wavetable import WavetableEngine


class XGEngineRegistry:
    """
    Engine Registry

    Provides centralized management of synthesis engines with registration,
    priority-based selection, and capability discovery.
    """

    def __init__(self, sample_rate: int = 44100):
        """Initialize XG engine registry"""
        self.sample_rate = sample_rate
        self.registry = SynthesisEngineRegistry()

        # Engine priority configuration (higher = preferred)
        self.engine_priorities = {
            "fdsp": 10,  # Formant synthesis (highest priority for S90/S70)
            "an": 9,  # Analog physical modeling
            "sfz": 9,  # SFZ modern sample format (high priority)
            "sf2": 8,  # SoundFont playback
            "xg": 7,  # XG synthesis (AWM)
            "fm": 6,  # FM synthesis
            "wavetable": 5,  # Wavetable synthesis
            "additive": 4,  # Additive synthesis
            "granular": 3,  # Granular synthesis
            "physical": 2,  # Physical modeling
            "convolution": 1,  # Convolution reverb
            "spectral": 1,  # Spectral processing
        }

        # Engine capability mapping
        self.engine_capabilities = {
            "fdsp": ["formant_synthesis", "vocal_modeling", "phoneme_transition"],
            "an": ["physical_modeling", "analog_emulation", "rp_pr_modeling"],
            "sfz": [
                "sample_playback",
                "sfz_support",
                "multi_format",
                "velocity_layers",
                "round_robin",
            ],
            "sf2": ["sample_playback", "soundfont_support", "multi_sample"],
            "xg": ["awm_synthesis", "wave_rom", "workstation_synthesis"],
            "fm": [
                "frequency_modulation",
                "algorithmic_synthesis",
                "dx7_compatibility",
            ],
            "wavetable": ["wavetable_synthesis", "wave_scanning", "morphing"],
            "additive": [
                "harmonic_synthesis",
                "additive_resynthesis",
                "spectrum_control",
            ],
            "granular": ["granular_synthesis", "time_stretching", "microsound"],
            "physical": [
                "physical_modeling",
                "modal_synthesis",
                "excitation_filtering",
            ],
            "convolution": [
                "convolution_reverb",
                "impulse_response",
                "spatial_processing",
            ],
            "spectral": ["spectral_processing", "fft_synthesis", "frequency_domain"],
        }

        # Register all available engines
        self._register_all_engines()

        logger.info("XG Engine Registry: All synthesis engines registered and ready")

    def _register_all_engines(self):
        """Register all available synthesis engines"""

        # FDSP Engine (Formant Dynamic Synthesis Processor) - S90/S70 Vocal Synthesis
        try:
            fdsp_engine = FDSPSynthesisEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(fdsp_engine, "fdsp", self.engine_priorities["fdsp"])
            logger.info("FDSP Engine registered (Formant Synthesis)")
        except Exception as e:
            logger.warning(f"FDSP Engine registration failed: {e}")

        # AN Engine (Analog Physical Modeling) - S90/S70 RP-PR
        try:
            an_engine = ANEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(an_engine, "an", self.engine_priorities["an"])
            logger.info("AN Engine registered (Physical Modeling)")
        except Exception as e:
            logger.warning(f"AN Engine registration failed: {e}")

        # SF2 Engine (SoundFont) - Sample Playback
        try:
            sf2_engine = SF2Engine(sample_rate=self.sample_rate)
            self.registry.register_engine(sf2_engine, "sf2", self.engine_priorities["sf2"])
            logger.info("SF2 Engine registered (SoundFont)")
        except Exception as e:
            logger.warning(f"SF2 Engine registration failed: {e}")

        # SFZ Engine - Modern Sample Format
        try:
            from ..io.sfz.sfz_engine import SFZEngine

            sfz_engine = SFZEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(sfz_engine, "sfz", self.engine_priorities.get("sfz", 8))
            logger.info("SFZ Engine registered (Modern Sample Format)")
        except Exception as e:
            logger.warning(f"SFZ Engine registration failed: {e}")

        # XG Engine (AWM Synthesis) - Core XG Synthesis
        try:
            xg_engine = ModernXGSynthesizer(sample_rate=self.sample_rate)
            self.registry.register_engine(xg_engine, "xg", self.engine_priorities["xg"])
            logger.info("XG Engine registered (AWM Synthesis)")
        except Exception as e:
            logger.warning(f"XG Engine registration failed: {e}")

        # FM Engine - Frequency Modulation Synthesis
        try:
            fm_engine = FMEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(fm_engine, "fm", self.engine_priorities["fm"])
            logger.info("FM Engine registered (Frequency Modulation)")
        except Exception as e:
            logger.warning(f"FM Engine registration failed: {e}")

        # Wavetable Engine - Wavetable Synthesis
        try:
            wt_engine = WavetableEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                wt_engine, "wavetable", self.engine_priorities["wavetable"]
            )
            logger.info("Wavetable Engine registered (Wavetable Synthesis)")
        except Exception as e:
            logger.warning(f"Wavetable Engine registration failed: {e}")

        # Additive Engine - Additive Synthesis
        try:
            add_engine = AdditiveEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                add_engine, "additive", self.engine_priorities["additive"]
            )
            logger.info("Additive Engine registered (Additive Synthesis)")
        except Exception as e:
            logger.warning(f"Additive Engine registration failed: {e}")

        # Granular Engine - Granular Synthesis
        try:
            gran_engine = GranularEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                gran_engine, "granular", self.engine_priorities["granular"]
            )
            logger.info("Granular Engine registered (Granular Synthesis)")
        except Exception as e:
            logger.warning(f"Granular Engine registration failed: {e}")

        # Physical Engine - Physical Modeling
        try:
            phys_engine = PhysicalEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                phys_engine, "physical", self.engine_priorities["physical"]
            )
            logger.info("Physical Engine registered (Physical Modeling)")
        except Exception as e:
            logger.warning(f"Physical Engine registration failed: {e}")

        # Convolution Reverb Engine - Convolution Processing
        try:
            conv_engine = ConvolutionReverbEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                conv_engine, "convolution", self.engine_priorities["convolution"]
            )
            logger.info("Convolution Engine registered (Convolution Processing)")
        except Exception as e:
            logger.warning(f"Convolution Engine registration failed: {e}")

        # Spectral Engine - Spectral Processing
        try:
            spec_engine = SpectralEngine(sample_rate=self.sample_rate)
            self.registry.register_engine(
                spec_engine, "spectral", self.engine_priorities["spectral"]
            )
            logger.info("Spectral Engine registered (Spectral Processing)")
        except Exception as e:
            logger.warning(f"Spectral Engine registration failed: {e}")

    def get_engine_for_file(self, file_path: str) -> str | None:
        """
        Get appropriate engine for a file based on extension and content.

        Args:
            file_path: Path to audio/sample file

        Returns:
            Engine type identifier or None
        """
        return self.registry.detect_engine_for_file(file_path)

    def get_engines_for_format(self, file_format: str) -> list[str]:
        """
        Get all engines that support a specific file format.

        Args:
            file_format: File format (e.g., 'sf2', 'wav', 'aiff')

        Returns:
            List of compatible engine types
        """
        return self.registry.get_engines_for_format(file_format)

    def create_engine(self, engine_type: str, **kwargs) -> Any | None:
        """
        Create a new instance of a synthesis engine.

        Args:
            engine_type: Type of engine to create
            **kwargs: Additional constructor arguments

        Returns:
            Engine instance or None if creation failed
        """
        # Set default sample rate if not specified
        if "sample_rate" not in kwargs:
            kwargs["sample_rate"] = self.sample_rate

        return self.registry.create_engine(engine_type, **kwargs)

    def get_engine_info(self, engine_type: str) -> dict[str, Any] | None:
        """
        Get information about a specific engine type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine information dictionary or None
        """
        engine = self.registry.get_engine(engine_type)
        if engine:
            return engine.get_engine_info()
        return None

    def get_registered_engines(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered engines"""
        return self.registry.get_registered_engines()

    def get_engine_priority(self, engine_type: str) -> int:
        """
        Get priority of an engine type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine priority (higher = preferred)
        """
        return self.registry.get_engine_priority(engine_type)

    def set_engine_priority(self, engine_type: str, priority: int):
        """
        Set priority for an engine type.

        Args:
            engine_type: Engine type identifier
            priority: New priority value
        """
        if engine_type in self.engine_priorities:
            self.engine_priorities[engine_type] = priority
            # Note: Would need to re-register engine with new priority
            # This is a simplified implementation

    def get_engine_capabilities(self, engine_type: str) -> list[str]:
        """
        Get capabilities of an engine type.

        Args:
            engine_type: Engine type identifier

        Returns:
            List of engine capabilities
        """
        return self.engine_capabilities.get(engine_type, [])

    def find_engines_with_capability(self, capability: str) -> list[str]:
        """
        Find all engines that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of engine types with the capability
        """
        matching_engines = []
        for engine_type, capabilities in self.engine_capabilities.items():
            if capability in capabilities:
                matching_engines.append(engine_type)
        return matching_engines

    def get_s90_s70_engines(self) -> list[str]:
        """
        Get engines that provide S90/S70 compatibility features.

        Returns:
            List of S90/S70 compatible engine types
        """
        s90_s70_engines = [
            "fdsp",  # FDSP vocal synthesis
            "an",  # AN physical modeling with RP-PR
            "xg",  # XG AWM synthesis
        ]
        return [
            engine for engine in s90_s70_engines if self.registry.get_engine(engine) is not None
        ]

    def get_workstation_engines(self) -> list[str]:
        """
        Get engines that provide workstation-grade features.

        Returns:
            List of workstation engine types
        """
        workstation_engines = [
            "sf2",  # Professional sample playback
            "xg",  # XG multi-timbral synthesis
            "an",  # Advanced physical modeling
            "fdsp",  # Vocal synthesis
            "fm",  # Classic FM synthesis
            "wavetable",  # Modern wavetable synthesis
            "additive",  # Advanced additive synthesis
        ]
        return [
            engine for engine in workstation_engines if self.registry.get_engine(engine) is not None
        ]

    def get_experimental_engines(self) -> list[str]:
        """
        Get experimental/advanced synthesis engines.

        Returns:
            List of experimental engine types
        """
        experimental_engines = [
            "granular",  # Granular synthesis
            "physical",  # Advanced physical modeling
            "spectral",  # Spectral processing
            "convolution",  # Convolution processing
        ]
        return [
            engine
            for engine in experimental_engines
            if self.registry.get_engine(engine) is not None
        ]

    def get_engine_statistics(self) -> dict[str, Any]:
        """Get comprehensive engine registry statistics"""
        registered_engines = self.get_registered_engines()

        stats = {
            "total_engines": len(registered_engines),
            "s90_s70_engines": len(self.get_s90_s70_engines()),
            "workstation_engines": len(self.get_workstation_engines()),
            "experimental_engines": len(self.get_experimental_engines()),
            "engine_types": list(registered_engines.keys()),
            "supported_formats": self._get_all_supported_formats(),
            "priority_distribution": self._get_priority_distribution(registered_engines),
        }

        return stats

    def _get_all_supported_formats(self) -> list[str]:
        """Get all supported file formats across all engines"""
        formats = set()
        for engine_info in self.get_registered_engines().values():
            formats.update(engine_info.get("formats", []))
        return sorted(list(formats))

    def _get_priority_distribution(
        self, registered_engines: dict[str, dict[str, Any]]
    ) -> dict[str, int]:
        """Get distribution of engine priorities"""
        distribution = {}
        for engine_type, engine_data in registered_engines.items():
            priority = engine_data.get("priority", 0)
            distribution[engine_type] = priority
        return distribution

    def validate_engine_compatibility(self, engine_type: str) -> dict[str, Any]:
        """
        Validate engine compatibility and requirements.

        Args:
            engine_type: Engine type to validate

        Returns:
            Compatibility validation results
        """
        engine = self.registry.get_engine(engine_type)
        if not engine:
            return {"compatible": False, "reason": "Engine not registered"}

        # Basic compatibility checks
        compatibility = {
            "compatible": True,
            "sample_rate_match": engine.sample_rate == self.sample_rate,
            "interface_compliant": hasattr(engine, "generate_samples"),
            "capabilities_available": len(self.get_engine_capabilities(engine_type)) > 0,
        }

        # Check for any compatibility issues
        issues = []
        if not compatibility["sample_rate_match"]:
            issues.append(
                f"Sample rate mismatch: expected {self.sample_rate}, got {engine.sample_rate}"
            )
        if not compatibility["interface_compliant"]:
            issues.append("Engine does not implement required interface methods")
            compatibility["compatible"] = False
        if not compatibility["capabilities_available"]:
            issues.append("Engine has no registered capabilities")

        compatibility["issues"] = issues
        compatibility["overall_compatible"] = len(issues) == 0

        return compatibility

    def get_engine_requirements(self, engine_type: str) -> dict[str, Any]:
        """
        Get system requirements for an engine type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine requirements dictionary
        """
        # Base requirements for all engines
        base_requirements = {
            "cpu_cores": 1,
            "memory_mb": 50,
            "sample_rate": self.sample_rate,
            "real_time_capable": True,
        }

        # Engine-specific requirements
        engine_requirements = {
            "fdsp": {"cpu_cores": 2, "memory_mb": 100, "complexity": "high"},
            "an": {"cpu_cores": 2, "memory_mb": 150, "complexity": "high"},
            "sf2": {"cpu_cores": 1, "memory_mb": 200, "complexity": "medium"},
            "xg": {"cpu_cores": 1, "memory_mb": 100, "complexity": "medium"},
            "fm": {"cpu_cores": 1, "memory_mb": 50, "complexity": "low"},
            "wavetable": {"cpu_cores": 1, "memory_mb": 80, "complexity": "medium"},
            "additive": {"cpu_cores": 2, "memory_mb": 120, "complexity": "high"},
            "granular": {"cpu_cores": 2, "memory_mb": 150, "complexity": "high"},
            "physical": {"cpu_cores": 2, "memory_mb": 100, "complexity": "high"},
            "convolution": {"cpu_cores": 1, "memory_mb": 200, "complexity": "medium"},
            "spectral": {"cpu_cores": 2, "memory_mb": 150, "complexity": "high"},
        }

        # Merge base and engine-specific requirements
        requirements = base_requirements.copy()
        if engine_type in engine_requirements:
            requirements.update(engine_requirements[engine_type])

        return requirements

    def optimize_engine_selection(self, available_resources: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize engine selection based on available system resources.

        Args:
            available_resources: Dictionary with 'cpu_cores', 'memory_mb', etc.

        Returns:
            Optimization recommendations
        """
        recommendations = {
            "preferred_engines": [],
            "limited_engines": [],
            "disabled_engines": [],
            "resource_usage": {},
        }

        cpu_cores = available_resources.get("cpu_cores", 4)
        memory_mb = available_resources.get("memory_mb", 4096)

        for engine_type in self.get_registered_engines().keys():
            requirements = self.get_engine_requirements(engine_type)
            resource_usage = requirements.copy()

            # Check if engine can run with available resources
            if requirements["cpu_cores"] > cpu_cores:
                recommendations["disabled_engines"].append(engine_type)
                resource_usage["status"] = "disabled_cpu_limit"
            elif requirements["memory_mb"] > memory_mb:
                recommendations["disabled_engines"].append(engine_type)
                resource_usage["status"] = "disabled_memory_limit"
            elif requirements.get("complexity") == "high" and cpu_cores < 2:
                recommendations["limited_engines"].append(engine_type)
                resource_usage["status"] = "limited_cpu"
            else:
                recommendations["preferred_engines"].append(engine_type)
                resource_usage["status"] = "available"

            recommendations["resource_usage"][engine_type] = resource_usage

        return recommendations


# Global registry instance
_global_registry: XGEngineRegistry | None = None


def get_global_engine_registry(sample_rate: int = 44100) -> XGEngineRegistry:
    """
    Get the global engine registry instance.

    Args:
        sample_rate: Sample rate for engine initialization

    Returns:
        Global XGEngineRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = XGEngineRegistry(sample_rate)
    return _global_registry


def initialize_engine_registry(sample_rate: int = 44100) -> XGEngineRegistry:
    """
    Initialize the engine registry with all available engines.

    Args:
        sample_rate: Sample rate for engine initialization

    Returns:
        Initialized XGEngineRegistry
    """
    registry = get_global_engine_registry(sample_rate)
    logger.info(
        f"Engine Registry initialized with {len(registry.get_registered_engines())} engines"
    )
    return registry


# Export classes and functions
__all__ = [
    "XGEngineRegistry",
    "get_global_engine_registry",
    "initialize_engine_registry",
]
