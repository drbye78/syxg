"""
Advanced Modulation Matrix for SFZ Synthesis

Implements a comprehensive modulation system supporting 200+ modulation routes
with real-time control, bipolar modulation, and advanced curve shaping.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable
import numpy as np
import math


class ModulationRoute:
    """
    Individual modulation route with advanced parameters.

    Supports bipolar modulation, custom curves, smoothing, and polarity control.
    """

    def __init__(
        self,
        source: str,
        destination: str,
        amount: float,
        curve: str = "linear",
        bipolar: bool = False,
        smooth: float = 0.0,
        polarity: int = 1,
    ):
        """
        Initialize modulation route.

        Args:
            source: Modulation source (e.g., 'velocity', 'cc1', 'lfo1')
            destination: Modulation destination (e.g., 'volume', 'pan', 'cutoff')
            amount: Modulation amount (-1.0 to 1.0 for bipolar, 0.0 to 1.0 for unipolar)
            curve: Shaping curve ('linear', 'exponential', 'logarithmic', 'sine')
            bipolar: Whether modulation is bipolar (±amount) or unipolar (0 to amount)
            smooth: Smoothing time in seconds (0 = no smoothing)
            polarity: Polarity multiplier (-1, 0, 1)
        """
        self.source = source
        self.destination = destination
        self.amount = amount
        self.curve = curve
        self.bipolar = bipolar
        self.smooth = smooth
        self.polarity = polarity

        # Runtime state
        self.current_value = 0.0
        self.target_value = 0.0
        self.smoothing_factor = self._calculate_smoothing_factor(smooth)

        # Pre-computed curve function
        self.curve_func = self._get_curve_function(curve)

    def _calculate_smoothing_factor(self, smooth_time: float) -> float:
        """Calculate smoothing factor from time constant."""
        if smooth_time <= 0.0:
            return 1.0  # No smoothing

        # One-pole lowpass filter coefficient
        # smooth_time is the time for 63% convergence
        sample_rate = getattr(self, "sample_rate", 44100.0)
        return 1.0 - math.exp(-1.0 / (smooth_time * sample_rate))

    def _get_curve_function(self, curve_name: str) -> Callable[[float], float]:
        """Get curve shaping function."""
        if curve_name == "linear":
            return lambda x: x
        elif curve_name == "exponential":
            return lambda x: x * x if x >= 0 else -(x * x)
        elif curve_name == "logarithmic":
            return lambda x: math.copysign(math.sqrt(abs(x)), x) if x != 0 else 0.0
        elif curve_name == "sine":
            return lambda x: math.sin(x * math.pi / 2)
        else:
            return lambda x: x  # Default to linear

    def update_source(self, source_value: float):
        """
        Update modulation source value.

        Args:
            source_value: New source value (typically 0.0 to 1.0)
        """
        # Apply curve shaping
        shaped_value = self.curve_func(source_value)

        # Calculate target modulation value
        if self.bipolar:
            # Bipolar: -amount to +amount
            self.target_value = shaped_value * 2.0 - 1.0  # Convert 0-1 to -1-+1
            self.target_value *= self.amount
        else:
            # Unipolar: 0 to amount
            self.target_value = shaped_value * self.amount

        # Apply polarity
        self.target_value *= self.polarity

    def process(self, block_size: int) -> np.ndarray:
        """
        Process modulation for a block of samples.

        Args:
            block_size: Number of samples to process

        Returns:
            Array of modulation values for the block
        """
        if self.smooth <= 0.0:
            # No smoothing - constant value
            return np.full(block_size, self.target_value, dtype=np.float32)

        # Apply smoothing filter
        output = np.zeros(block_size, dtype=np.float32)

        for i in range(block_size):
            # One-pole lowpass filter
            self.current_value += (self.target_value - self.current_value) * self.smoothing_factor
            output[i] = self.current_value

        return output

    def get_current_value(self) -> float:
        """Get current modulation value."""
        return self.current_value

    def reset(self):
        """Reset modulation state."""
        self.current_value = 0.0
        self.target_value = 0.0


class AdvancedModulationMatrix:
    """
    Advanced modulation matrix supporting 200+ modulation routes.

    Features:
    - Multiple modulation sources (CC, velocity, LFOs, envelopes, etc.)
    - Multiple modulation destinations (parameters, effects, etc.)
    - Bipolar and unipolar modulation
    - Custom curve shaping
    - Real-time smoothing
    - Block-based processing for efficiency
    """

    # Standard SFZ modulation sources
    STANDARD_SOURCES = {
        # MIDI Controllers (0-127)
        **{f"cc{i}": f"cc{i}" for i in range(128)},
        # Standard MIDI sources
        "velocity": "velocity",
        "key": "key",  # Note number as modulation source
        "channel_aftertouch": "channel_aftertouch",
        "poly_aftertouch": "poly_aftertouch",  # Per-note aftertouch
        "pitch_bend": "pitch_bend",
        # Special SFZ sources
        "random": "random",  # Random value per note
        "sequence": "sequence",  # Round robin sequence
        # Envelope outputs as modulation sources
        "amp_env": "amp_env",
        "filter_env": "filter_env",
        "pitch_env": "pitch_env",
        # LFO outputs
        "lfo1": "lfo1",
        "lfo2": "lfo2",
        "lfo3": "lfo3",
        "lfo4": "lfo4",
    }

    # Standard SFZ modulation destinations
    STANDARD_DESTINATIONS = {
        # Amplitude
        "volume": "volume",
        "pan": "pan",
        "width": "width",  # Stereo width
        # Pitch
        "tune": "tune",
        "bend": "bend",
        "pitch": "pitch",
        # Filter
        "cutoff": "cutoff",
        "resonance": "resonance",
        "filter_gain": "filter_gain",
        # Effects sends
        "reverb_send": "reverb_send",
        "chorus_send": "chorus_send",
        "delay_send": "delay_send",
        # LFO parameters
        "lfo1_freq": "lfo1_freq",
        "lfo1_depth": "lfo1_depth",
        "lfo2_freq": "lfo2_freq",
        "lfo2_depth": "lfo2_depth",
        # Envelope parameters
        "amp_attack": "amp_attack",
        "amp_decay": "amp_decay",
        "amp_sustain": "amp_sustain",
        "amp_release": "amp_release",
        # Filter envelope parameters
        "filter_attack": "filter_attack",
        "filter_decay": "filter_decay",
        "filter_sustain": "filter_sustain",
        "filter_release": "filter_release",
    }

    def __init__(self, max_routes: int = 256):
        """
        Initialize advanced modulation matrix.

        Args:
            max_routes: Maximum number of modulation routes
        """
        self.max_routes = max_routes
        self.routes: list[ModulationRoute] = []

        # Source value cache for efficiency
        self.source_values: dict[str, float] = {}
        self.source_arrays: dict[str, np.ndarray] = {}  # For block processing

        # Initialize standard sources to 0
        for source in self.STANDARD_SOURCES.values():
            self.source_values[source] = 0.0

    def add_route(
        self,
        source: str,
        destination: str,
        amount: float = 1.0,
        curve: str = "linear",
        bipolar: bool = False,
        smooth: float = 0.0,
        polarity: int = 1,
    ) -> bool:
        """
        Add a modulation route.

        Args:
            source: Modulation source name
            destination: Modulation destination name
            amount: Modulation amount
            curve: Shaping curve
            bipolar: Bipolar modulation flag
            smooth: Smoothing time in seconds
            polarity: Polarity (-1, 0, 1)

        Returns:
            True if route was added, False if limit exceeded
        """
        if len(self.routes) >= self.max_routes:
            return False

        route = ModulationRoute(source, destination, amount, curve, bipolar, smooth, polarity)
        self.routes.append(route)
        return True

    def remove_route(self, source: str, destination: str) -> bool:
        """
        Remove a modulation route.

        Args:
            source: Modulation source name
            destination: Modulation destination name

        Returns:
            True if route was removed, False if not found
        """
        for i, route in enumerate(self.routes):
            if route.source == source and route.destination == destination:
                self.routes.pop(i)
                return True
        return False

    def clear_routes(self, destination: str | None = None):
        """
        Clear modulation routes.

        Args:
            destination: If specified, clear only routes to this destination
        """
        if destination is None:
            self.routes.clear()
        else:
            self.routes = [r for r in self.routes if r.destination != destination]

    def update_source(self, source: str, value: float):
        """
        Update a modulation source value.

        Args:
            source: Source name
            value: New value (typically 0.0 to 1.0)
        """
        if source in self.source_values:
            self.source_values[source] = value

            # Update all routes that use this source
            for route in self.routes:
                if route.source == source:
                    route.update_source(value)

    def update_sources(self, source_updates: dict[str, float]):
        """
        Update multiple modulation sources.

        Args:
            source_updates: Dictionary of source name -> value
        """
        for source, value in source_updates.items():
            self.update_source(source, value)

    def process_block(self, block_size: int) -> dict[str, np.ndarray]:
        """
        Process modulation for a block of samples.

        Args:
            block_size: Number of samples to process

        Returns:
            Dictionary mapping destinations to modulation arrays
        """
        # Group routes by destination for efficiency
        dest_routes: dict[str, list[ModulationRoute]] = {}

        for route in self.routes:
            if route.destination not in dest_routes:
                dest_routes[route.destination] = []
            dest_routes[route.destination].append(route)

        # Process each destination
        result: dict[str, np.ndarray] = {}

        for destination, routes in dest_routes.items():
            if not routes:
                continue

            # Sum all routes for this destination
            dest_array = np.zeros(block_size, dtype=np.float32)

            for route in routes:
                route_array = route.process(block_size)
                dest_array += route_array

            result[destination] = dest_array

        return result

    def get_current_values(self) -> dict[str, float]:
        """
        Get current modulation values for all destinations.

        Returns:
            Dictionary mapping destinations to current values
        """
        result = {}
        dest_routes: dict[str, list[ModulationRoute]] = {}

        # Group routes by destination
        for route in self.routes:
            if route.destination not in dest_routes:
                dest_routes[route.destination] = []
            dest_routes[route.destination].append(route)

        # Sum current values for each destination
        for destination, routes in dest_routes.items():
            total = sum(route.get_current_value() for route in routes)
            result[destination] = total

        return result

    def get_route_info(self) -> list[dict[str, Any]]:
        """
        Get information about all modulation routes.

        Returns:
            List of route information dictionaries
        """
        return [
            {
                "source": route.source,
                "destination": route.destination,
                "amount": route.amount,
                "curve": route.curve,
                "bipolar": route.bipolar,
                "smooth": route.smooth,
                "polarity": route.polarity,
                "current_value": route.get_current_value(),
            }
            for route in self.routes
        ]

    def reset(self):
        """Reset all modulation state."""
        for route in self.routes:
            route.reset()

        # Reset source values to defaults
        for source in self.source_values:
            self.source_values[source] = 0.0

    def get_available_sources(self) -> list[str]:
        """Get list of available modulation sources."""
        return list(self.STANDARD_SOURCES.keys())

    def get_available_destinations(self) -> list[str]:
        """Get list of available modulation destinations."""
        return list(self.STANDARD_DESTINATIONS.keys())

    def validate_route(self, source: str, destination: str) -> tuple[bool, str]:
        """
        Validate a modulation route.

        Args:
            source: Source name
            destination: Destination name

        Returns:
            (is_valid, error_message)
        """
        if source not in self.STANDARD_SOURCES:
            return False, f"Unknown source: {source}"

        if destination not in self.STANDARD_DESTINATIONS:
            return False, f"Unknown destination: {destination}"

        return True, ""

    def __len__(self) -> int:
        """Get number of modulation routes."""
        return len(self.routes)

    def __str__(self) -> str:
        """String representation."""
        return f"AdvancedModulationMatrix(routes={len(self.routes)})"

    def __repr__(self) -> str:
        return self.__str__()
