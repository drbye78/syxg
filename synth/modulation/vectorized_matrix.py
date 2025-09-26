"""
VECTORIZED MODULATION MATRIX - PHASE 2 PERFORMANCE

This module provides a vectorized modulation matrix implementation with
NumPy-based operations for maximum performance.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


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
    """Vectorized XG modulation matrix with support up to 16 routes"""
    def __init__(self, num_routes=16):
        self.routes: List[Optional[VectorizedModulationRoute]] = [None] * num_routes
        self.num_routes = num_routes

        # Performance optimization: Pre-computed coefficient cache
        self.coefficient_cache = {}
        self.cache_version = 0
        self.last_sources_hash = None

    def set_route(self, index, source, destination, amount=0.0, polarity=1.0,
                  velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Setting modulation route
        
        Args:
            index: route index (0-15)
            source: modulation source
            destination: modulation destination
            amount: modulation depth
            polarity: polarity (1.0 or -1.0)
            velocity_sensitivity: velocity sensitivity
            key_scaling: note height dependency
        """
        if 0 <= index < self.num_routes:
            self.routes[index] = VectorizedModulationRoute(
                source, destination, amount, polarity,
                velocity_sensitivity, key_scaling
            )

    def clear_route(self, index):
        """Clearing modulation route"""
        if 0 <= index < self.num_routes:
            self.routes[index] = None

    def process_vectorized(self, sources: Dict[str, np.ndarray], 
                          velocities: np.ndarray, notes: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Processing modulation matrix in vectorized form
        
        Args:
            sources: dictionary with arrays of current source values
            velocities: array of key press velocities (0-127)
            notes: array of MIDI notes (0-127)

        Returns:
            dictionary with arrays of modulating values for destinations
        """
        # Determining array size
        if len(velocities) == 0:
            return {}
            
        block_size = len(velocities)
        modulation_values: Dict[str, np.ndarray] = {}
        
        # Processing all routes in vectorized form
        for route in self.routes:
            if route is None:
                continue
                
            if route.source in sources:
                source_values = sources[route.source]
                
                # Checking source array size
                if len(source_values) != block_size:
                    # Interpolation or replication of values to match block size
                    if len(source_values) == 1:
                        source_values = np.full(block_size, source_values[0], dtype=np.float32)
                    else:
                        # Linear interpolation
                        indices = np.linspace(0, len(source_values) - 1, block_size)
                        source_values = np.interp(indices, 
                                                np.arange(len(source_values)), 
                                                source_values).astype(np.float32)
                
                # Getting modulation values in vectorized form
                mod_values = route.get_modulation_value_vectorized(source_values, velocities, notes)
                
                # Accumulating modulation values for each target
                if route.destination not in modulation_values:
                    modulation_values[route.destination] = np.zeros(block_size, dtype=np.float32)
                modulation_values[route.destination] += mod_values
        
        return modulation_values

    def process(self, sources: Dict[str, float], velocity: int, note: int) -> Dict[str, float]:
        """
        Processing modulation matrix for single sample (compatibility with original version)

        Args:
            sources: dictionary with current source values
            velocity: key press velocity (0-127)
            note: MIDI note (0-127)

        Returns:
            dictionary with modulating values for destinations
        """
        modulation_values = {}

        for route in self.routes:
            if route is None:
                continue

            if route.source in sources:
                source_value = sources[route.source]
                # Creating scalar arrays for compatibility
                mod_value = route.get_modulation_value_vectorized(
                    np.array([source_value], dtype=np.float32),
                    np.array([velocity], dtype=np.float32),
                    np.array([note], dtype=np.float32)
                )[0]  # Get scalar value

                if route.destination not in modulation_values:
                    modulation_values[route.destination] = 0.0
                modulation_values[route.destination] += mod_value

        return modulation_values

    def process_optimized(self, sources: Dict[str, float], velocity: int, note: int) -> Dict[str, float]:
        """
        Optimized modulation processing with pre-computed coefficients

        Args:
            sources: dictionary with current source values
            velocity: key press velocity (0-127)
            note: MIDI note (0-127)

        Returns:
            dictionary with modulating values for destinations
        """
        # Check if we can use cached coefficients
        sources_hash = hash(tuple(sorted(sources.items())))
        if sources_hash == self.last_sources_hash and self.coefficient_cache:
            return self._apply_cached_modulation(sources, velocity, note)

        # Compute fresh modulation values
        modulation_values = {}

        for route in self.routes:
            if route is None or route.source not in sources:
                continue

            source_value = sources[route.source]

            # Pre-compute modulation coefficient to avoid repeated calculations
            cache_key = (route.source, route.destination, velocity, note)
            if cache_key not in self.coefficient_cache:
                # Calculate and cache the coefficient
                coeff = self._calculate_modulation_coefficient(route, source_value, velocity, note)
                self.coefficient_cache[cache_key] = coeff
            else:
                coeff = self.coefficient_cache[cache_key]

            if route.destination not in modulation_values:
                modulation_values[route.destination] = 0.0
            modulation_values[route.destination] += coeff

        self.last_sources_hash = sources_hash
        return modulation_values

    def _calculate_modulation_coefficient(self, route, source_value: float, velocity: int, note: int) -> float:
        """Calculate modulation coefficient with optimized operations"""
        # Apply polarity and amount
        value = source_value * route.polarity * route.amount

        # Apply velocity sensitivity
        if route.velocity_sensitivity != 0.0:
            velocity_factor = (velocity / 127.0) ** (1.0 + route.velocity_sensitivity)
            value *= velocity_factor

        # Apply key scaling
        if route.key_scaling != 0.0:
            note_factor = (note - 60) / 60.0
            key_factor = 1.0 + note_factor * route.key_scaling
            key_factor = max(0.1, key_factor)  # Prevent zero or negative values
            value *= key_factor

        return value

    def _apply_cached_modulation(self, sources: Dict[str, float], velocity: int, note: int) -> Dict[str, float]:
        """Apply modulation using cached coefficients for better performance"""
        modulation_values = {}

        for route in self.routes:
            if route is None or route.source not in sources:
                continue

            cache_key = (route.source, route.destination, velocity, note)
            if cache_key in self.coefficient_cache:
                coeff = self.coefficient_cache[cache_key]

                if route.destination not in modulation_values:
                    modulation_values[route.destination] = 0.0
                modulation_values[route.destination] += coeff

        return modulation_values

    def clear_cache(self):
        """Clear the modulation coefficient cache"""
        self.coefficient_cache.clear()
        self.last_sources_hash = None
