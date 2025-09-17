"""
VECTORIZED MODULATION MATRIX - PHASE 2 PERFORMANCE

This module provides a vectorized modulation matrix implementation with
NumPy-based operations for maximum performance.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class VectorizedModulationRoute:
    """Векторизованный маршрут модуляции в матрице модуляции"""
    def __init__(self, source, destination, amount=0.0, polarity=1.0,
                 velocity_sensitivity=0.0, key_scaling=0.0):
        """
        Инициализация векторизованного маршрута модуляции
        
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
        self.amount = np.float32(amount)
        self.polarity = np.float32(polarity)
        self.velocity_sensitivity = np.float32(velocity_sensitivity)
        self.key_scaling = np.float32(key_scaling)

    def get_modulation_value_vectorized(self, source_values: np.ndarray, 
                                      velocities: np.ndarray, notes: np.ndarray) -> np.ndarray:
        """
        Получение значений модуляции для данного маршрута в векторизованном виде
        
        Args:
            source_values: массив текущих значений источника
            velocities: массив скоростей нажатия (0-127)
            notes: массив MIDI нот (0-127)
            
        Returns:
            массив значений модуляции
        """
        # Применение полярности
        values = source_values * self.polarity * self.amount
        
        # Применение чувствительности к скорости в векторизованном виде
        if self.velocity_sensitivity != 0.0:
            velocity_factors = (velocities / 127.0) ** (1.0 + self.velocity_sensitivity)
            values *= velocity_factors
        
        # Применение key scaling в векторизованном виде
        if self.key_scaling != 0.0:
            # Нормализация нот (60 = C3)
            note_factors = (notes - 60) / 60.0
            key_factors = 1.0 + note_factors * self.key_scaling
            key_factors = np.maximum(0.1, key_factors)  # Ограничение минимального значения
            values *= key_factors
        
        return values


class VectorizedModulationMatrix:
    """Векторизованная матрица модуляции XG с поддержкой до 16 маршрутов"""
    def __init__(self, num_routes=16):
        self.routes: List[Optional[VectorizedModulationRoute]] = [None] * num_routes
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
            self.routes[index] = VectorizedModulationRoute(
                source, destination, amount, polarity,
                velocity_sensitivity, key_scaling
            )

    def clear_route(self, index):
        """Очистка маршрута модуляции"""
        if 0 <= index < self.num_routes:
            self.routes[index] = None

    def process_vectorized(self, sources: Dict[str, np.ndarray], 
                          velocities: np.ndarray, notes: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Обработка матрицы модуляции в векторизованном виде
        
        Args:
            sources: словарь с массивами текущих значений источников
            velocities: массив скоростей нажатия (0-127)
            notes: массив MIDI нот (0-127)
            
        Returns:
            словарь с массивами модулирующих значений для целей
        """
        # Определение размера массивов
        if len(velocities) == 0:
            return {}
            
        block_size = len(velocities)
        modulation_values: Dict[str, np.ndarray] = {}
        
        # Обработка всех маршрутов в векторизованном виде
        for route in self.routes:
            if route is None:
                continue
                
            if route.source in sources:
                source_values = sources[route.source]
                
                # Проверка размера массива источника
                if len(source_values) != block_size:
                    # Интерполяция или репликация значений для соответствия размеру блока
                    if len(source_values) == 1:
                        source_values = np.full(block_size, source_values[0], dtype=np.float32)
                    else:
                        # Линейная интерполяция
                        indices = np.linspace(0, len(source_values) - 1, block_size)
                        source_values = np.interp(indices, 
                                                np.arange(len(source_values)), 
                                                source_values).astype(np.float32)
                
                # Получение значений модуляции в векторизованном виде
                mod_values = route.get_modulation_value_vectorized(source_values, velocities, notes)
                
                # Аккумулирование значений модуляции для каждой цели
                if route.destination not in modulation_values:
                    modulation_values[route.destination] = np.zeros(block_size, dtype=np.float32)
                modulation_values[route.destination] += mod_values
        
        return modulation_values

    def process(self, sources: Dict[str, float], velocity: int, note: int) -> Dict[str, float]:
        """
        Обработка матрицы модуляции для одиночного сэмпла (совместимость с оригинальной версией)
        
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
                # Создание скалярных массивов для совместимости
                mod_value = route.get_modulation_value_vectorized(
                    np.array([source_value], dtype=np.float32),
                    np.array([velocity], dtype=np.float32),
                    np.array([note], dtype=np.float32)
                )[0]  # Получаем скалярное значение
                
                if route.destination not in modulation_values:
                    modulation_values[route.destination] = 0.0
                modulation_values[route.destination] += mod_value
        
        return modulation_values