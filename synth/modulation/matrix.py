"""
Modulation matrix for XG synthesizer.
Manages modulation routing and processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from .routes import ModulationRoute


class ModulationMatrix:
    """Матрица модуляции XG с поддержкой до 16 маршрутов"""
    def __init__(self, num_routes=16):
        self.routes: List[Optional[ModulationRoute]] = [None] * num_routes
        self.active_routes: List[ModulationRoute] = []  # Optimized list of only active routes
        self.num_routes = num_routes
        self._cache_key: Optional[tuple] = None
        self._cache_value: Dict[str, float] = {}

    def set_route(self, index, source, destination, amount=0.0, polarity=1.0,
                  velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Установка маршрута модуляции

        Args:
            index: индекс маршрута (0-15)
            source: источник модуляции
            destination: цель модуляции
            amount: глубина модуляции
            polarity: полярность (1.0 или -1.0)
            velocity_sensitivity: чувствительность к скорости
            key_scaling: зависимость от высоты ноты
        """
        if 0 <= index < self.num_routes:
            self.routes[index] = ModulationRoute(
                source, destination, amount, polarity,
                velocity_sensitivity, key_scaling
            )
            self._update_active_routes()

    def clear_route(self, index):
        """Очистка маршрута модуляции"""
        if 0 <= index < self.num_routes:
            self.routes[index] = None
            self._update_active_routes()

    def _update_active_routes(self):
        """Обновление кэшированного списка активных маршрутов"""
        self.active_routes = [route for route in self.routes if route is not None]
        self._cache_key = None  # Invalidate cache when routes change

    def _calculate_cache_key(self, sources, velocity, note):
        """Оптимизированный ключ для кэширования"""
        # Hash only critical parameters that affect modulation output
        return (tuple((src, round(val, 4)) for src, val in sources.items() 
                if src in ['lfo1', 'lfo2', 'pitch_bend', 'mod_wheel']),
                velocity // 8,  # Quantize velocity
                note)

    def process(self, sources, velocity, note):
        """
        Оптимизированная обработка матрицы модуляции с кэшированием
        """
        # Check cache first (only for stable parameters)
        cache_key = self._calculate_cache_key(sources, velocity, note)
        if cache_key == self._cache_key:
            return self._cache_value.copy()  # Return copy to prevent external modifications

        # Always initialize with empty dict but preserve key ordering for consistency
        modulation_values: Dict[str, float] = {}

        # Process only active routes (avoids None checks)
        for route in self.active_routes:
            if route.source in sources:
                source_value = sources[route.source]
                mod_value = route.get_modulation_value(source_value, velocity, note)

                # Safely accumulate values
                modulation_values[route.destination] = modulation_values.get(route.destination, 0.0) + mod_value

        # Update cache
        self._cache_key = cache_key
        self._cache_value = modulation_values.copy()  # Store copy to prevent external modifications
        return modulation_values.copy()  # Return immutable copy to caller

    def process_fast(self, sources, velocity, note):
        """
        Ultra-fast processing for real-time scenarios.
        Skips velocity/key scaling for maximum speed.
        """
        if not self.active_routes:
            return {}  # Empty modulation

        modulation_values: Dict[str, float] = {}

        # Fast path - no cache, no advanced features
        for route in self.active_routes:
            if route.source in sources:
                source_value = sources[route.source]
                mod_value = source_value * route.amount * route.polarity
                modulation_values[route.destination] = modulation_values.get(route.destination, 0.0) + mod_value

        return modulation_values
