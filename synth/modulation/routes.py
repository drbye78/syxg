"""
Modulation routes for XG synthesizer.
Defines modulation route configuration and processing.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class ModulationRoute:
    """Маршрут модуляции в матрице модуляции"""
    def __init__(self, source, destination, amount=0.0, polarity=1.0,
                 velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Инициализация маршрута модуляции

        Args:
            source: источник модуляции (из ModulationSource)
            destination: цель модуляции (из ModulationDestination)
            amount: глубина модуляции (0.0-1.0)
            polarity: полярность (1.0 или -1.0)
            velocity_sensitivity: чувствительность к скорости (0.0-1.0)
            key_scaling: зависимость от высоты ноты (-1.0-1.0)
        """
        self.source = source
        self.destination = destination
        self.amount = amount
        self.polarity = polarity
        self.velocity_sensitivity = velocity_sensitivity
        self.key_scaling = key_scaling

    def get_modulation_value(self, source_value, velocity, note):
        """
        Получение значения модуляции для данного маршрута

        Args:
            source_value: текущее значение источника
            velocity: скорость нажатия (0-127)
            note: MIDI нота (0-127)

        Returns:
            значение модуляции
        """
        # Применение полярности
        value = source_value * self.polarity * self.amount

        # Применение чувствительности к скорости
        if self.velocity_sensitivity != 0.0:
            velocity_factor = (velocity / 127.0) ** (1.0 + self.velocity_sensitivity)
            value *= velocity_factor

        # Применение key scaling
        if self.key_scaling != 0.0:
            # Нормализация ноты (60 = C3)
            note_factor = (note - 60) / 60.0
            key_factor = 1.0 + note_factor * self.key_scaling
            value *= max(0.1, key_factor)

        return value
