"""
Base Effect Class

This module provides the base class for all XG effects,
defining the common interface and functionality.
"""

from typing import Dict, List, Tuple, Optional, Any
import math


class BaseEffect:
    """
    Base class for all XG effects.

    Provides common functionality and interface that all effects must implement.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize the effect.

        Args:
            sample_rate: Sample rate for audio processing
        """
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False
        self.level = 1.0

        # Effect-specific state
        self._state = {}

    def process_sample(self, left: float, right: float) -> Tuple[float, float]:
        """
        Process a single stereo sample.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        if self.bypass or not self.enabled:
            return (left, right)

        return self._process_sample_impl(left, right)

    def process_block(self, input_block: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Process a block of stereo samples.

        Args:
            input_block: List of (left, right) sample tuples

        Returns:
            List of processed (left, right) sample tuples
        """
        if self.bypass or not self.enabled:
            return input_block.copy()

        output_block = []
        for left, right in input_block:
            processed = self._process_sample_impl(left, right)
            output_block.append(processed)

        return output_block

    def _process_sample_impl(self, left: float, right: float) -> Tuple[float, float]:
        """
        Implementation-specific sample processing.

        Must be overridden by subclasses.

        Args:
            left: Left channel input sample
            right: Right channel input sample

        Returns:
            Tuple of (left_output, right_output)
        """
        raise NotImplementedError("Subclasses must implement _process_sample_impl")

    def set_parameter(self, param_name: str, value: float):
        """
        Set an effect parameter.

        Args:
            param_name: Name of the parameter
            value: Parameter value
        """
        if hasattr(self, param_name):
            setattr(self, param_name, value)
        else:
            # Store in state dictionary
            self._state[param_name] = value

    def get_parameter(self, param_name: str) -> Optional[float]:
        """
        Get an effect parameter.

        Args:
            param_name: Name of the parameter

        Returns:
            Parameter value or None if not found
        """
        if hasattr(self, param_name):
            return getattr(self, param_name)
        elif param_name in self._state:
            return self._state[param_name]
        return None

    def reset(self):
        """Reset effect state to initial values"""
        self._state = {}
        self._reset_impl()

    def _reset_impl(self):
        """Implementation-specific reset logic"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """Get current effect state"""
        state = {
            "enabled": self.enabled,
            "bypass": self.bypass,
            "level": self.level,
        }
        state.update(self._state)
        return state

    def set_state(self, state: Dict[str, Any]):
        """Set effect state"""
        self.enabled = state.get("enabled", True)
        self.bypass = state.get("bypass", False)
        self.level = state.get("level", 1.0)

        # Update state dictionary
        for key, value in state.items():
            if key not in ["enabled", "bypass", "level"]:
                self._state[key] = value

    @property
    def name(self) -> str:
        """Get effect name"""
        return self.__class__.__name__.replace("Effect", "")

    def __str__(self) -> str:
        """String representation of the effect"""
        return f"{self.name} Effect (enabled={self.enabled}, bypass={self.bypass}, level={self.level:.2f})"
