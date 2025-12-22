"""
Synthesis partial abstraction for XG synthesizer.

Provides the abstract base class for synthesis partials, defining the interface
that all synthesis engines must implement for their partials.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class SynthesisPartial(ABC):
    """
    Abstract base class for synthesis partials.

    A synthesis partial represents an individual synthesis element within a voice,
    such as a sample player, oscillator, or physical model. All synthesis engines
    must implement this interface for their partial types.
    """

    def __init__(self, params: Dict, sample_rate: int):
        """
        Initialize synthesis partial.

        Args:
            params: Partial-specific parameters
            sample_rate: Audio sample rate in Hz
        """
        self.params = params.copy()
        self.sample_rate = sample_rate
        self.active = True

    @abstractmethod
    def generate_samples(self, block_size: int, modulation: Dict) -> np.ndarray:
        """
        Generate audio samples for this partial.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Numpy array of shape (block_size * 2,) containing stereo audio samples
        """
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """
        Check if this partial is still producing sound.

        Returns:
            True if partial should continue generating samples, False otherwise
        """
        pass

    @abstractmethod
    def note_on(self, velocity: int, note: int) -> None:
        """
        Handle note-on event for this partial.

        Args:
            velocity: MIDI velocity (0-127)
            note: MIDI note number (0-127)
        """
        pass

    @abstractmethod
    def note_off(self) -> None:
        """
        Handle note-off event for this partial.
        """
        pass

    @abstractmethod
    def apply_modulation(self, modulation: Dict) -> None:
        """
        Apply modulation changes to partial parameters.

        Args:
            modulation: Dictionary of modulation values to apply
        """
        pass

    def reset(self) -> None:
        """
        Reset partial to initial state.

        This is called when the partial is reused from a pool.
        """
        self.active = True

    def get_partial_info(self) -> Dict[str, Any]:
        """
        Get information about this partial.

        Returns:
            Dictionary with partial metadata
        """
        return {
            'type': self.__class__.__name__,
            'active': self.active,
            'sample_rate': self.sample_rate,
            'params': self.params.copy()
        }

    def update_parameter(self, param_name: str, value: Any) -> None:
        """
        Update a single parameter.

        Args:
            param_name: Name of parameter to update
            value: New parameter value
        """
        self.params[param_name] = value

    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """
        Get a parameter value.

        Args:
            param_name: Name of parameter to retrieve
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        return self.params.get(param_name, default)
