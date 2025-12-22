"""
Abstract Synthesis Engine Framework

Defines the interface for modular synthesis engines in the voice-based architecture.
Provides a common interface for different synthesis methods (SF2, FM, Additive, etc.)
with standardized parameter handling and audio generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
import numpy as np


class SynthesisEngine(ABC):
    """
    Abstract base class for synthesis engines.

    Defines the standard interface that all synthesis engines must implement,
    providing a consistent way to generate audio regardless of the underlying
    synthesis method.

    This abstraction enables:
    - Modular synthesis engine swapping
    - Consistent parameter handling across engines
    - Standardized audio generation interface
    - Engine capability discovery and metadata
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

    @abstractmethod
    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> np.ndarray:
        """
        Generate audio samples for a note.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        pass

    @abstractmethod
    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by this engine.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if note can be played, False otherwise
        """
        pass

    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get engine information and capabilities.

        Returns:
            Dictionary containing engine metadata:
            - 'name': Engine name
            - 'type': Synthesis type ('sf2', 'fm', 'additive', 'physical')
            - 'capabilities': List of supported features
            - 'formats': List of supported file formats
            - 'polyphony': Maximum simultaneous voices
            - 'parameters': Available parameter names
        """
        pass

    def get_voice_parameters(self, program: int, bank: int = 0) -> Optional[Dict[str, Any]]:
        """
        Get voice parameters for a program/bank combination.

        Args:
            program: MIDI program number (0-127)
            bank: MIDI bank number (0-16383)

        Returns:
            Voice parameter dictionary or None if not supported
        """
        # Default implementation returns None - engines should override
        return None

    def get_engine_type(self) -> str:
        """
        Get the engine type identifier.

        Returns:
            Engine type string ('sf2', 'fm', 'additive', etc.)
        """
        return 'unknown'

    @abstractmethod
    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int) -> 'SynthesisPartial':
        """
        Create a partial instance for this engine.

        Args:
            partial_params: Parameters for the partial
            sample_rate: Audio sample rate

        Returns:
            SynthesisPartial instance configured for this engine
        """
        pass

    def get_supported_formats(self) -> List[str]:
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
        return modulation_type in ['pitch', 'filter', 'amp']

    def get_parameter_info(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a parameter.

        Args:
            parameter_name: Name of parameter

        Returns:
            Parameter information dictionary or None if parameter not supported
        """
        return None

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize parameters.

        Args:
            parameters: Raw parameter dictionary

        Returns:
            Validated and normalized parameter dictionary
        """
        # Default implementation: pass through unchanged
        return parameters.copy()

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage statistics.

        Returns:
            Memory usage information
        """
        return {
            'samples_loaded': 0,
            'memory_used_mb': 0.0,
            'cache_efficiency': 0.0
        }

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


class SynthesisEngineRegistry:
    """
    Registry for synthesis engines.

    Manages registration, discovery, and instantiation of synthesis engines.
    Provides engine priority system and automatic format detection.
    """

    def __init__(self):
        """Initialize engine registry."""
        self._engines: Dict[str, Dict[str, Any]] = {}
        self._engine_classes: Dict[str, type] = {}
        self._format_map: Dict[str, List[str]] = {}  # format -> [engine_types]
        self._priority_order: List[str] = []  # Engine priority for fallbacks

    def register_engine(self, engine: SynthesisEngine, engine_type: str,
                       priority: int = 0) -> None:
        """
        Register a synthesis engine.

        Args:
            engine: Engine instance (used for metadata)
            engine_type: Unique engine type identifier
            priority: Engine priority (higher = preferred)
        """
        engine_info = engine.get_engine_info()
        supported_formats = engine.get_supported_formats()

        self._engines[engine_type] = {
            'info': engine_info,
            'class': engine.__class__,
            'priority': priority,
            'formats': supported_formats,
            'instance': engine  # Keep instance for metadata access
        }

        self._engine_classes[engine_type] = engine.__class__

        # Update format mapping
        for fmt in supported_formats:
            if fmt not in self._format_map:
                self._format_map[fmt] = []
            if engine_type not in self._format_map[fmt]:
                self._format_map[fmt].append(engine_type)

        # Update priority order
        self._update_priority_order()

    def get_engine(self, engine_type: str) -> Optional[SynthesisEngine]:
        """
        Get engine instance by type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine instance or None if not found
        """
        if engine_type in self._engines:
            return self._engines[engine_type]['instance']
        return None

    def get_engine_class(self, engine_type: str) -> Optional[type]:
        """
        Get engine class by type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine class or None if not found
        """
        return self._engine_classes.get(engine_type)

    def create_engine(self, engine_type: str, **kwargs) -> Optional[SynthesisEngine]:
        """
        Create new engine instance.

        Args:
            engine_type: Engine type to create
            **kwargs: Engine constructor arguments

        Returns:
            New engine instance or None if creation failed
        """
        engine_class = self.get_engine_class(engine_type)
        if engine_class:
            try:
                return engine_class(**kwargs)
            except Exception as e:
                print(f"Failed to create engine {engine_type}: {e}")
                return None
        return None

    def get_engines_for_format(self, file_format: str) -> List[str]:
        """
        Get engine types that support a file format.

        Args:
            file_format: File format (extension)

        Returns:
            List of compatible engine types, ordered by priority
        """
        engine_types = self._format_map.get(file_format.lower(), [])
        return sorted(engine_types, key=lambda x: self._engines[x]['priority'], reverse=True)

    def get_registered_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered engines.

        Returns:
            Dictionary mapping engine types to their information
        """
        result = {}
        for engine_type, data in self._engines.items():
            result[engine_type] = {
                'info': data['info'],
                'priority': data['priority'],
                'formats': data['formats']
            }
        return result

    def detect_engine_for_file(self, file_path: str) -> Optional[str]:
        """
        Detect appropriate engine for a file based on extension.

        Args:
            file_path: Path to audio file

        Returns:
            Recommended engine type or None if no suitable engine
        """
        import os
        ext = os.path.splitext(file_path)[1].lower()

        compatible_engines = self.get_engines_for_format(ext)
        return compatible_engines[0] if compatible_engines else None

    def get_engine_priority(self, engine_type: str) -> int:
        """
        Get priority of an engine type.

        Args:
            engine_type: Engine type identifier

        Returns:
            Engine priority (higher = preferred)
        """
        return self._engines.get(engine_type, {}).get('priority', 0)

    def _update_priority_order(self) -> None:
        """Update internal priority ordering."""
        self._priority_order = sorted(
            self._engines.keys(),
            key=lambda x: self._engines[x]['priority'],
            reverse=True
        )

    def get_priority_order(self) -> List[str]:
        """
        Get engine types ordered by priority.

        Returns:
            List of engine types in priority order
        """
        return self._priority_order.copy()


# Import here to avoid circular imports
from ..partial.partial import SynthesisPartial
