"""
VECTORIZED ADSR ENVELOPE - PHASE 2 PERFORMANCE

This module provides a vectorized ADSR envelope implementation with
NumPy-based operations for maximum performance.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
import math


class VectorizedADSREnvelope:
    """Векторизованная ADSR огибающая с оптимизациями для пакетной обработки"""
    
    def __init__(self, delay=0.0, attack=0.01, hold=0.0, decay=0.3, sustain=0.7, release=0.5,
                 velocity_sense=1.0, key_scaling=0.0, sample_rate=48000):
        """
        Инициализация векторизованной ADSR огибающей
        
        Args:
            delay: Время задержки в секундах
            attack: Время атаки в секундах
            hold: Время удержания в секундах
            decay: Время спада в секундах
            sustain: Уровень удержания (0.0 - 1.0)
            release: Время релиза в секундах
            velocity_sense: Чувствительность к скорости (0.0 - 2.0)
            key_scaling: Зависимость от высоты ноты
            sample_rate: Частота дискретизации в Гц
        """
        self.sample_rate = sample_rate
        
        # Параметры огибающей
        self.delay = max(0.0, delay)
        self.attack = max(0.001, attack)
        self.hold = max(0.0, hold)
        self.decay = max(0.001, decay)
        self.sustain = max(0.0, min(1.0, sustain))
        self.release = max(0.001, release)
        self.velocity_sense = max(0.0, min(2.0, velocity_sense))
        self.key_scaling = key_scaling
        
        # Состояния огибающей (векторизованные)
        self.states = np.full(1, "idle", dtype='<U10')  # Текущие состояния
        self.levels = np.zeros(1, dtype=np.float32)     # Текущие уровни
        self.release_starts = np.zeros(1, dtype=np.float32)  # Уровни начала релиза
        
        # Счетчики для delay и hold
        self.delay_counters = np.zeros(1, dtype=np.int32)
        self.hold_counters = np.zeros(1, dtype=np.int32)
        
        # Предвычисленные параметры
        self.delay_samples = int(self.delay * sample_rate)
        self.hold_samples = int(self.hold * sample_rate)
        
        # Инкременты и декременты
        self._recalculate_increments()
        
        # Флаги педалей (векторизованные)
        self.sustain_pedals = np.zeros(1, dtype=bool)
        self.sostenuto_pedals = np.zeros(1, dtype=bool)
        self.held_by_sostenuto = np.zeros(1, dtype=bool)
        self.soft_pedals = np.zeros(1, dtype=bool)
        self.hold_notes_flags = np.zeros(1, dtype=bool)
        
        # For backward compatibility with single-envelope interface
        self._single_state = "idle"
        
    @property
    def state(self):
        """Get the state of the first envelope for backward compatibility"""
        if len(self.states) > 0:
            return self.states[0]
        return self._single_state

    @state.setter
    def state(self, value):
        """Set the state of the first envelope for backward compatibility"""
        if len(self.states) > 0:
            self.states[0] = value
        else:
            self._single_state = value
        
    def _recalculate_increments(self):
        """Пересчет инкрементов для текущих параметров"""
        # Attack - логарифмический рост
        if self.attack > 0:
            self.attack_increment = np.float32(1.0 / (self.attack * self.sample_rate * 2))
        else:
            self.attack_increment = np.float32(1.0)
        
        # Decay - линейное уменьшение до sustain уровня
        if self.decay > 0:
            self.decay_decrement = np.float32((1.0 - self.sustain) / (self.decay * self.sample_rate))
        else:
            self.decay_decrement = np.float32(1.0 - self.sustain)
        
        # Release - линейное уменьшение
        if self.release > 0:
            self.release_decrement = np.float32(1.0 / (self.release * self.sample_rate))
        else:
            self.release_decrement = np.float32(1.0)
    
    def set_block_size(self, block_size: int):
        """Установка размера блока для векторизованной обработки"""
        # Расширяем все массивы до нужного размера
        current_size = len(self.states)
        
        if block_size > current_size:
            # Расширяем массивы
            self.states = np.resize(self.states, block_size)
            self.states[current_size:] = "idle"
            
            self.levels = np.resize(self.levels, block_size)
            self.levels[current_size:] = 0.0
            
            self.release_starts = np.resize(self.release_starts, block_size)
            self.release_starts[current_size:] = 0.0
            
            self.delay_counters = np.resize(self.delay_counters, block_size)
            self.delay_counters[current_size:] = 0
            
            self.hold_counters = np.resize(self.hold_counters, block_size)
            self.hold_counters[current_size:] = 0
            
            self.sustain_pedals = np.resize(self.sustain_pedals, block_size)
            self.sostenuto_pedals = np.resize(self.sostenuto_pedals, block_size)
            self.held_by_sostenuto = np.resize(self.held_by_sostenuto, block_size)
            self.soft_pedals = np.resize(self.soft_pedals, block_size)
            self.hold_notes_flags = np.resize(self.hold_notes_flags, block_size)
            
        elif block_size < current_size:
            # Уменьшаем массивы
            self.states = self.states[:block_size]
            self.levels = self.levels[:block_size]
            self.release_starts = self.release_starts[:block_size]
            self.delay_counters = self.delay_counters[:block_size]
            self.hold_counters = self.hold_counters[:block_size]
            self.sustain_pedals = self.sustain_pedals[:block_size]
            self.sostenuto_pedals = self.sostenuto_pedals[:block_size]
            self.held_by_sostenuto = self.held_by_sostenuto[:block_size]
            self.soft_pedals = self.soft_pedals[:block_size]
            self.hold_notes_flags = self.hold_notes_flags[:block_size]
    
    def update_parameters(self, delay=None, attack=None, hold=None, decay=None, sustain=None, release=None,
                         velocity_sense=None, key_scaling=None):
        """Обновление параметров огибающей"""
        if delay is not None:
            self.delay = max(0.0, delay)
            self.delay_samples = int(self.delay * self.sample_rate)
        if attack is not None:
            self.attack = max(0.001, attack)
        if hold is not None:
            self.hold = max(0.0, hold)
            self.hold_samples = int(self.hold * self.sample_rate)
        if decay is not None:
            self.decay = max(0.001, decay)
        if sustain is not None:
            self.sustain = max(0.0, min(1.0, sustain))
        if release is not None:
            self.release = max(0.001, release)
        if velocity_sense is not None:
            self.velocity_sense = max(0.0, min(2.0, velocity_sense))
        if key_scaling is not None:
            self.key_scaling = key_scaling
        
        self._recalculate_increments()
        
        # Корректировка текущих уровней при изменении sustain
        if sustain is not None and len(self.states) > 0:
            sustain_mask = (self.states == "sustain")
            self.levels[sustain_mask] = self.sustain
    
    def note_on(self, velocity, note=60, soft_pedal=False):
        """Handle Note On event with compatibility interface."""
        # For single envelope, create arrays and call vectorized version
        velocities = np.array([velocity], dtype=np.float32)
        notes = np.array([note], dtype=np.float32)
        soft_pedals = np.array([soft_pedal], dtype=bool)
        self.note_on_vectorized(velocities, notes, soft_pedals)

    def note_on_vectorized(self, velocities: np.ndarray, notes: np.ndarray = None, 
                          soft_pedals: np.ndarray = None):
        """
        Обработка события Note On для векторизованной обработки
        
        Args:
            velocities: массив скоростей нажатия (0-127)
            notes: массив MIDI нот (0-127), по умолчанию 60
            soft_pedals: массив состояний soft pedal, по умолчанию False
        """
        if notes is None:
            notes = np.full_like(velocities, 60)
        if soft_pedals is None:
            soft_pedals = np.zeros_like(velocities, dtype=bool)
        
        block_size = len(velocities)
        self.set_block_size(block_size)
        
        # Применение чувствительности к скорости
        normalized_velocities = velocities / 127.0
        velocity_factors = np.minimum(1.0, normalized_velocities ** self.velocity_sense)
        
        # Применение key scaling
        if self.key_scaling != 0.0:
            note_factors = (notes - 60) / 60.0
            key_factors = 1.0 + note_factors * self.key_scaling
            
            # Применяем модифицированные параметры (в упрощенном виде)
            # В реальной реализации нужно модифицировать временные параметры
            pass
        
        # Применение soft pedal
        soft_velocity_factors = np.where(soft_pedals, velocity_factors * 0.5, velocity_factors)
        
        # Инициализация состояний
        self.states[:] = "delay"
        self.delay_counters[:] = 0
        self.levels[:] = 0.0 * soft_velocity_factors
        
        # Обработка hold notes
        hold_mask = self.hold_notes_flags
        self.states[hold_mask] = "sustain"
        self.levels[hold_mask] = self.sustain * soft_velocity_factors[hold_mask]
    
    def note_off_vectorized(self):
        """Обработка события Note Off для векторизованной обработки"""
        # Проверка активных педалей
        pedal_active = self.sustain_pedals | self.sostenuto_pedals | self.hold_notes_flags
        
        # Определение состояний, которые должны перейти в release
        should_release = (~pedal_active) & (self.states != "release") & (self.states != "idle")
        
        # Установка начальных значений релиза
        self.release_starts[should_release] = self.levels[should_release]
        
        # Переход в состояние release
        self.states[should_release] = "release"
    
    def process(self):
        """Process one sample of envelope generation with compatibility interface."""
        # For single envelope, process block of size 1 and return first element
        if len(self.states) == 0:
            return 0.0
        # Process one sample and return the level
        self.process_block_vectorized(1)
        return self.levels[0]

    def process_block_vectorized(self, block_size: int) -> np.ndarray:
        """
        Обработка блока огибающих в векторизованном виде
        
        Args:
            block_size: Размер блока в сэмплах
            
        Returns:
            Массив уровней огибающих для всего блока
        """
        self.set_block_size(block_size)
        
        # Создаем копию текущих уровней для возврата
        output_levels = self.levels.copy()
        
        # Обработка состояния delay
        delay_mask = (self.states == "delay")
        if np.any(delay_mask):
            self.delay_counters[delay_mask] += 1
            transition_to_attack = (self.delay_counters >= self.delay_samples) & delay_mask
            self.states[transition_to_attack] = "attack"
        
        # Обработка состояния attack
        attack_mask = (self.states == "attack")
        if np.any(attack_mask):
            self.levels[attack_mask] += self.attack_increment
            attack_complete = (self.levels >= 1.0) & attack_mask
            self.levels[attack_complete] = 1.0
            self.states[attack_complete] = "hold"
            self.hold_counters[attack_complete] = 0
        
        # Обработка состояния hold
        hold_mask = (self.states == "hold")
        if np.any(hold_mask):
            self.hold_counters[hold_mask] += 1
            transition_to_decay = (self.hold_counters >= self.hold_samples) & hold_mask
            self.states[transition_to_decay] = "decay"
        
        # Обработка состояния decay
        decay_mask = (self.states == "decay")
        if np.any(decay_mask):
            self.levels[decay_mask] -= self.decay_decrement
            sustain_reached = (np.abs(self.levels - self.sustain) < 0.001) & decay_mask
            self.levels[sustain_reached] = self.sustain
            self.states[sustain_reached] = "sustain"
        
        # Состояние sustain (уровень остается на sustain)
        # Ничего не делаем, уровень уже установлен
        
        # Обработка состояния release
        release_mask = (self.states == "release")
        if np.any(release_mask):
            self.levels[release_mask] -= self.release_decrement
            release_complete = (self.levels <= 0.0) & release_mask
            self.levels[release_complete] = 0.0
            self.states[release_complete] = "idle"
        
        return output_levels.copy()
    
    def note_on(self, velocity, note=60, soft_pedal=False):
        """Обработка события Note On для совместимости с оригинальной версией"""
        # Создаем скалярные массивы для совместимости
        velocities = np.array([velocity], dtype=np.float32)
        notes = np.array([note], dtype=np.float32)
        soft_pedals = np.array([soft_pedal], dtype=bool)
        
        self.note_on_vectorized(velocities, notes, soft_pedals)
    
    def note_off(self):
        """Обработка события Note Off для совместимости с оригинальной версией"""
        # Для совместимости обрабатываем только первый элемент
        if len(self.states) > 0:
            # Проверка активных педалей только для первого элемента
            pedal_active = (self.sustain_pedals[0] or self.sostenuto_pedals[0] or self.hold_notes_flags[0])
            
            # Проверка состояния
            if not pedal_active and self.states[0] not in ["release", "idle"]:
                self.release_starts[0] = self.levels[0]
                self.states[0] = "release"
    
    def process(self):
        """Обработка одного сэмпла для совместимости с оригинальной версией"""
        if len(self.states) == 0:
            return 0.0
            
        # Обрабатываем только первый элемент и возвращаем его уровень
        temp_states = self.states.copy()
        temp_levels = self.levels.copy()
        temp_delay_counters = self.delay_counters.copy()
        temp_hold_counters = self.hold_counters.copy()
        temp_release_starts = self.release_starts.copy()
        
        # Выполняем обработку для одного сэмпла
        # Это упрощенная версия process_block_vectorized для одного элемента
        output = self.process_block_vectorized(1)[0]
        
        return output