"""
Modulation matrix for XG synthesizer.
Manages modulation routing and processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from .routes import ModulationRoute


class ModulationMatrix:
    """Матрица модуляции XG с поддержкой до 16 маршрутов"""
    def __init__(self, num_routes=16):
        self.routes = [None] * num_routes
        self.num_routes = num_routes

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
            self.routes[index] = ModulationRoute(  # type: ignore
                source, destination, amount, polarity,
                velocity_sensitivity, key_scaling
            )

    def clear_route(self, index):
        """Очистка маршрута модуляции"""
        if 0 <= index < self.num_routes:
            self.routes[index] = None

    def process(self, sources, velocity, note):
        """
        Обработка матрицы модуляции

        Args:
            sources: словарь с текущими значениями источников
            velocity: скорость нажатия (0-127)
            note: MIDI нота (0-127)

        Returns:
            словарь с модулирующими значениями для целей
        """
        modulation_values = {}

        for route in self.routes:
            if route is None:
                continue

            if route.source in sources:
                source_value = sources[route.source]
                mod_value = route.get_modulation_value(source_value, velocity, note)

                if route.destination not in modulation_values:
                    modulation_values[route.destination] = 0.0
                modulation_values[route.destination] += mod_value

        return modulation_values
