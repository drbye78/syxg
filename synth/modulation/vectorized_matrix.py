"""
Vectorized Modulation Matrix

Provides efficient, vectorized modulation routing for XG synthesizer.
Optimized for real-time audio processing with minimal memory allocations.
"""
from __future__ import annotations

import numpy as np


class VectorizedModulationRoute:
    """Vectorized modulation route in the modulation matrix"""
    def __init__(self, source, destination, amount=0.0, polarity=1.0,
                 velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Initialization of vectorized modulation route
        
        Args:
            source: modulation source (from ModulationSource)
            destination: modulation destination (from ModulationDestination)
            amount: modulation depth (0.0-1.0)
            polarity: polarity (1.0 or -1.0)
            velocity_sensitivity: velocity sensitivity (0.0-1.0)
            key_scaling: note height dependency (-1.0-1.0)
        """
        self.source = source
        self.destination = destination
        self.amount = np.float32(amount)
        self.polarity = np.float32(polarity)
        self.velocity_sensitivity = np.float32(velocity_sensitivity)
        self.key_scaling = np.float32(key_scaling)

    def get_modulation_value_vectorized(self, source_values: np.ndarray, 
                                      velocities: np.ndarray, notes: np.ndarray) -> np.ndarray:
        """
        Getting modulation values for this route in vectorized form
        
        Args:
            source_values: array of current source values
            velocities: array of key press velocities (0-127)
            notes: array of MIDI notes (0-127)

        Returns:
            array of modulation values
        """
        # Applying polarity
        values = source_values * self.polarity * self.amount
        
        # Applying velocity sensitivity in vectorized form
        if self.velocity_sensitivity != 0.0:
            velocity_factors = (velocities / 127.0) ** (1.0 + self.velocity_sensitivity)
            values *= velocity_factors
        
        # Applying key scaling in vectorized form
        if self.key_scaling != 0.0:
            # Note normalization (60 = C3)
            note_factors = (notes - 60) / 60.0
            key_factors = 1.0 + note_factors * self.key_scaling
            key_factors = np.maximum(0.1, key_factors)  # Limiting minimum value
            values *= key_factors
        
        return values


class VectorizedModulationMatrix:
    """
    Vectorized XG modulation matrix with support for up to 16 routes.

    Optimized for real-time audio processing with pre-allocated destination arrays
    to minimize memory allocations during processing.

    Args:
        num_routes: Maximum number of modulation routes (default: 16)
    """
    def __init__(self, num_routes: int = 16):
        if not isinstance(num_routes, int) or num_routes < 1 or num_routes > 32:
            raise ValueError("num_routes must be between 1 and 32")

        self.routes: list[VectorizedModulationRoute | None] = [None] * num_routes
        self.num_routes = num_routes

        # Pre-allocated destination arrays to avoid allocations during processing
        self._dest_arrays: dict[str, np.ndarray] = {}
        self._max_block_size = 0  # Track max block size for array sizing

    def set_route(self, index: int, source: str, destination: str,
                  amount: float = 0.0, polarity: float = 1.0,
                  velocity_sensitivity: float = 0.0, key_scaling: float = 0.0) -> None:
        """
        Set a modulation route at the specified index.

        Args:
            index: Route index (0 to num_routes-1)
            source: Source parameter name
            destination: Destination parameter name
            amount: Modulation amount (0.0-1.0)
            polarity: Modulation polarity (1.0 or -1.0)
            velocity_sensitivity: Velocity sensitivity (0.0-1.0)
            key_scaling: Key scaling amount (-1.0-1.0)

        Raises:
            ValueError: If index is out of range
            TypeError: If parameters have invalid types
        """
        if not isinstance(index, int) or not (0 <= index < self.num_routes):
            raise ValueError(f"Route index must be between 0 and {self.num_routes-1}")

        if not isinstance(source, str) or not isinstance(destination, str):
            raise TypeError("Source and destination must be strings")

        self.routes[index] = VectorizedModulationRoute(
            source, destination, amount, polarity,
            velocity_sensitivity, key_scaling
        )

        # Initialize destination array for this route if not already present
        if destination not in self._dest_arrays:
            self._dest_arrays[destination] = np.zeros(self._max_block_size or 1024, dtype=np.float32)

    def clear_route(self, index: int) -> None:
        """
        Clear a modulation route at the specified index.

        Args:
            index: Route index to clear

        Raises:
            ValueError: If index is out of range
        """
        if not isinstance(index, int) or not (0 <= index < self.num_routes):
            raise ValueError(f"Route index must be between 0 and {self.num_routes-1}")

        self.routes[index] = None

    def process_vectorized(self, sources: dict[str, np.ndarray],
                          velocities: np.ndarray, notes: np.ndarray) -> dict[str, np.ndarray]:
        """
        Process modulation matrix in vectorized form.

        Args:
            sources: Dictionary mapping source names to value arrays
            velocities: Array of key velocities (0-127)
            notes: Array of MIDI note numbers (0-127)

        Returns:
            Dictionary mapping destination names to modulation value arrays

        Raises:
            ValueError: If input arrays have mismatched sizes
        """
        # Input validation
        if len(velocities) != len(notes):
            raise ValueError("Velocities and notes arrays must have the same length")

        block_size = len(velocities)
        if block_size == 0:
            return {}

        # Resize destination arrays if block size changed
        if block_size > self._max_block_size:
            self._resize_destination_arrays(block_size)
            self._max_block_size = block_size

        modulation_values: dict[str, np.ndarray] = {}

        # Process all routes
        for route in self.routes:
            if route is None or route.source not in sources:
                continue

            source_values = sources[route.source]

            # Ensure source array size matches block size
            if len(source_values) != block_size:
                if len(source_values) == 1:
                    # Broadcast scalar to array
                    source_values = np.full(block_size, source_values[0], dtype=np.float32)
                else:
                    raise ValueError(f"Source array size {len(source_values)} doesn't match block size {block_size}")

            # Calculate modulation values
            mod_values = route.get_modulation_value_vectorized(source_values, velocities, notes)

            # Accumulate to destination (reuse pre-allocated array)
            if route.destination not in modulation_values:
                dest_array = self._dest_arrays[route.destination]
                dest_array.fill(0.0)  # Clear the array
                modulation_values[route.destination] = dest_array

            modulation_values[route.destination] += mod_values

        return modulation_values

    def _resize_destination_arrays(self, new_size: int) -> None:
        """Resize all destination arrays to accommodate larger block sizes."""
        for dest_name in self._dest_arrays:
            # Create new larger array and copy existing data if any
            new_array = np.zeros(new_size, dtype=np.float32)
            old_array = self._dest_arrays[dest_name]
            if len(old_array) > 0:
                copy_size = min(len(old_array), new_size)
                new_array[:copy_size] = old_array[:copy_size]
            self._dest_arrays[dest_name] = new_array

    def get_active_routes(self) -> list[int]:
        """
        Get list of indices for active (non-None) routes.

        Returns:
            List of active route indices
        """
        return [i for i, route in enumerate(self.routes) if route is not None]

    def clear_all_routes(self) -> None:
        """Clear all modulation routes."""
        self.routes = [None] * self.num_routes
