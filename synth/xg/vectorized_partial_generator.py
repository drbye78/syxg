"""
VECTORIZED PARTIAL GENERATOR - PHASE 2 PERFORMANCE

This module provides a vectorized partial generator implementation with
NumPy-based operations for maximum performance.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from ..core.vectorized_envelope import VectorizedADSREnvelope
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner


class VectorizedPartialGenerator:
    """
    Векторизованный частичный генератор для пакетной обработки нескольких частичных структур
    """
    
    def __init__(self, wavetables, notes, velocities, programs, partial_ids,
                 partial_params_list, is_drums=None, sample_rate=44100):
        """
        Инициализация векторизованного частичного генератора
        
        Args:
            wavetables: список объектов, предоставляющих доступ к wavetable сэмплам
            notes: массив MIDI нот (0-127)
            velocities: массив скоростей нажатия (0-127)
            programs: массив номеров программ (патчей)
            partial_ids: массив идентификаторов частичных структур
            partial_params_list: список параметров для частичных структур
            is_drums: массив флагов режима барабана
            sample_rate: частота дискретизации
        """
        self.block_size = len(notes)
        self.sample_rate = sample_rate
        
        # Параметры частичных структур
        self.wavetables = wavetables if isinstance(wavetables, list) else [wavetables] * self.block_size
        self.notes = np.array(notes, dtype=np.int32)
        self.velocities = np.array(velocities, dtype=np.int32)
        self.programs = np.array(programs, dtype=np.int32)
        self.partial_ids = np.array(partial_ids, dtype=np.int32)
        self.is_drums = np.array(is_drums if is_drums is not None else [False] * self.block_size, dtype=bool)
        
        # Извлечение параметров
        self.levels = np.array([params.get("level", 1.0) for params in partial_params_list], dtype=np.float32)
        self.pans = np.array([params.get("pan", 0.5) for params in partial_params_list], dtype=np.float32)
        self.key_range_lows = np.array([params.get("key_range_low", 0) for params in partial_params_list], dtype=np.int32)
        self.key_range_highs = np.array([params.get("key_range_high", 127) for params in partial_params_list], dtype=np.int32)
        self.velocity_range_lows = np.array([params.get("velocity_range_low", 0) for params in partial_params_list], dtype=np.int32)
        self.velocity_range_highs = np.array([params.get("velocity_range_high", 127) for params in partial_params_list], dtype=np.int32)
        self.key_scalings = np.array([params.get("key_scaling", 0.0) for params in partial_params_list], dtype=np.float32)
        self.velocity_senses = np.array([params.get("velocity_sense", 1.0) for params in partial_params_list], dtype=np.float32)
        self.initial_attenuations = np.array([params.get("initial_attenuation", 0.0) for params in partial_params_list], dtype=np.float32)
        self.scale_tunings = np.array([params.get("scale_tuning", 100) for params in partial_params_list], dtype=np.float32)
        self.overriding_root_keys = np.array([params.get("overriding_root_key", -1) for params in partial_params_list], dtype=np.int32)
        
        # Проверка активности частичных структур
        key_in_range = (self.key_range_lows <= self.notes) & (self.notes <= self.key_range_highs)
        velocity_in_range = (self.velocity_range_lows <= self.velocities) & (self.velocities <= self.velocity_range_highs)
        self.actives = key_in_range & velocity_in_range
        
        # Инициализация фаз
        self.phases = np.zeros(self.block_size, dtype=np.float32)
        self._update_phase_steps()
        
        # Инициализация огибающих (векторизованные)
        self.amp_envelopes = []
        self.filter_envelopes = []
        self.pitch_envelopes = []
        
        # Создание огибающих для каждой частичной структуры
        for i, params in enumerate(partial_params_list):
            if not self.actives[i]:
                self.amp_envelopes.append(None)
                self.filter_envelopes.append(None)
                self.pitch_envelopes.append(None)
                continue
            
            # Амплитудная огибающая
            amp_env_params = params["amp_envelope"]
            amp_envelope = VectorizedADSREnvelope(
                delay=amp_env_params["delay"],
                attack=amp_env_params["attack"],
                hold=amp_env_params["hold"],
                decay=amp_env_params["decay"],
                sustain=amp_env_params["sustain"],
                release=amp_env_params["release"],
                velocity_sense=self.velocity_senses[i],
                key_scaling=amp_env_params.get("key_scaling", 0.0),
                sample_rate=sample_rate
            )
            self.amp_envelopes.append(amp_envelope)
            
            # Фильтровая огибающая
            if not self.is_drums[i] or params.get("use_filter_env", True):
                filter_env_params = params["filter_envelope"]
                filter_envelope = VectorizedADSREnvelope(
                    delay=filter_env_params["delay"],
                    attack=filter_env_params["attack"],
                    hold=filter_env_params["hold"],
                    decay=filter_env_params["decay"],
                    sustain=filter_env_params["sustain"],
                    release=filter_env_params["release"],
                    key_scaling=filter_env_params.get("key_scaling", 0.0),
                    sample_rate=sample_rate
                )
                self.filter_envelopes.append(filter_envelope)
            else:
                self.filter_envelopes.append(None)
            
            # Pitch огибающая
            if not self.is_drums[i] or params.get("use_pitch_env", True):
                pitch_env_params = params["pitch_envelope"]
                pitch_envelope = VectorizedADSREnvelope(
                    delay=pitch_env_params["delay"],
                    attack=pitch_env_params["attack"],
                    hold=pitch_env_params["hold"],
                    decay=pitch_env_params["decay"],
                    sustain=pitch_env_params["sustain"],
                    release=pitch_env_params["release"],
                    sample_rate=sample_rate
                )
                self.pitch_envelopes.append(pitch_envelope)
            else:
                self.pitch_envelopes.append(None)
        
        # Запуск огибающих при Note On
        self._note_on_envelopes()
        
        # Поддержка модуляции
        self.velocity_crossfades = np.zeros(self.block_size, dtype=np.float32)
        self.note_crossfades = np.zeros(self.block_size, dtype=np.float32)
    
    def _update_phase_steps(self):
        """Обновление шагов фазы для частичных структур"""
        # Базовые частоты для нот
        base_freqs = 440.0 * (2 ** ((self.notes - 69) / 12.0))
        
        # Применение scale tuning
        tuning_multipliers = 2 ** (self.scale_tunings / 1200.0)
        base_freqs *= tuning_multipliers
        
        # Учет key scaling
        pitch_factors = 2 ** ((self.notes - 60) * self.key_scalings / 1200.0)
        final_freqs = base_freqs * pitch_factors
        
        # Для простоты используем фиксированную длину таблицы
        table_length = 2048  # Типичная длина wavetable
        self.phase_steps = final_freqs / self.sample_rate * table_length
    
    def _note_on_envelopes(self):
        """Запуск огибающих при Note On"""
        for i in range(self.block_size):
            if not self.actives[i]:
                continue
                
            if self.amp_envelopes[i]:
                self.amp_envelopes[i].note_on(self.velocities[i], self.notes[i])
            if self.filter_envelopes[i]:
                self.filter_envelopes[i].note_on(self.velocities[i], self.notes[i])
            if self.pitch_envelopes[i]:
                self.pitch_envelopes[i].note_on(self.velocities[i], self.notes[i])
    
    def is_active_vectorized(self) -> np.ndarray:
        """Проверка, активны ли частичные структуры (векторизованная)"""
        # Проверяем активность и состояние амплитудных огибающих
        active_statuses = self.actives.copy()
        
        for i in range(self.block_size):
            if not active_statuses[i]:
                continue
            if self.amp_envelopes[i] and hasattr(self.amp_envelopes[i], 'states'):
                # Проверяем, что огибающая не в состоянии idle
                active_statuses[i] = not np.all(self.amp_envelopes[i].states == "idle")
        
        return active_statuses
    
    def note_off_vectorized(self):
        """Обработка события Note Off (векторизованная)"""
        for i in range(self.block_size):
            if not self.actives[i]:
                continue
                
            if self.amp_envelopes[i]:
                self.amp_envelopes[i].note_off_vectorized()
            if self.filter_envelopes[i]:
                self.filter_envelopes[i].note_off_vectorized()
            if self.pitch_envelopes[i]:
                self.pitch_envelopes[i].note_off_vectorized()
    
    def generate_block_vectorized(self, lfos_list, global_pitch_mods: np.ndarray = None,
                                 velocity_crossfades: np.ndarray = None,
                                 note_crossfades: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Генерация блока аудио сэмплов для частичных структур (векторизованная)
        
        Args:
            lfos_list: список LFO для использования в модуляции
            global_pitch_mods: массив глобальных модуляций pitch
            velocity_crossfades: массив коэффициентов кросс-фейда по velocity
            note_crossfades: массив коэффициентов кросс-фейда по ноте
            
        Returns:
            кортеж (left_samples, right_samples) массивов в диапазоне [-1.0, 1.0]
        """
        if global_pitch_mods is None:
            global_pitch_mods = np.zeros(self.block_size, dtype=np.float32)
        if velocity_crossfades is None:
            velocity_crossfades = np.zeros(self.block_size, dtype=np.float32)
        if note_crossfades is None:
            note_crossfades = np.zeros(self.block_size, dtype=np.float32)
        
        # Сохраняем кросс-фейды
        self.velocity_crossfades = velocity_crossfades
        self.note_crossfades = note_crossfades
        
        # Проверяем активность
        active_mask = self.is_active_vectorized()
        
        if not np.any(active_mask):
            return (np.zeros(self.block_size, dtype=np.float32), 
                   np.zeros(self.block_size, dtype=np.float32))
        
        # Получение значений LFO (упрощенная реализация)
        lfo_values = {}
        for i, lfo in enumerate(lfos_list):
            if lfo is not None:
                # Для простоты используем среднее значение LFO
                lfo_values[f"lfo{i+1}"] = np.full(self.block_size, lfo.step(), dtype=np.float32)
        
        # Обработка амплитудных огибающих
        amp_envs = np.zeros(self.block_size, dtype=np.float32)
        for i in range(self.block_size):
            if active_mask[i] and self.amp_envelopes[i]:
                # Для простоты обрабатываем один сэмпл
                amp_envs[i] = self.amp_envelopes[i].process()
        
        # Фильтрация нулевых значений
        zero_amp_mask = (amp_envs <= 0.0) & active_mask
        active_mask &= ~zero_amp_mask
        
        if not np.any(active_mask):
            return (np.zeros(self.block_size, dtype=np.float32), 
                   np.zeros(self.block_size, dtype=np.float32))
        
        # Генерация базовых сэмплов (упрощенная реализация)
        # В реальной реализации здесь будет генерация из wavetable
        samples = np.sin(self.phases)  # Простая синусоида для демонстрации
        self.phases += self.phase_steps
        self.phases %= (2 * np.pi)  # Ограничение фазы
        
        # Применение огибающей амплитуды
        samples *= amp_envs
        
        # Применение уровня частичной структуры с учетом кросс-фейда
        effective_levels = self.levels.copy()
        
        # Учет кросс-фейда по velocity
        crossfade_velocity_mask = np.array([getattr(params, 'crossfade_velocity', False) 
                                          for params in self.__dict__.get('partial_params_list', [])])
        if len(crossfade_velocity_mask) == self.block_size:
            effective_levels *= (1.0 - velocity_crossfades * crossfade_velocity_mask)
        
        # Учет кросс-фейда по ноте
        crossfade_note_mask = np.array([getattr(params, 'crossfade_note', False) 
                                      for params in self.__dict__.get('partial_params_list', [])])
        if len(crossfade_note_mask) == self.block_size:
            effective_levels *= (1.0 - note_crossfades * crossfade_note_mask)
        
        # Применение начального ослабления
        attenuation_factors = 10 ** (-self.initial_attenuations / 20.0)
        effective_levels *= attenuation_factors
        
        samples *= effective_levels
        
        # Применение панорамирования
        left_samples = np.zeros(self.block_size, dtype=np.float32)
        right_samples = np.zeros(self.block_size, dtype=np.float32)
        
        for i in range(self.block_size):
            if not active_mask[i]:
                continue
                
            # Создание стерео паннера для каждого сэмпла
            panner = StereoPanner(pan_position=self.pans[i], sample_rate=self.sample_rate)
            left_out, right_out = panner.process(samples[i])
            left_samples[i] = left_out
            right_samples[i] = right_out
        
        return (left_samples, right_samples)
    
    # Методы для совместимости с оригинальной версией
    def is_active(self):
        """Проверка, активна ли частичная структура (для совместимости)"""
        if self.block_size > 0:
            return self.actives[0] and (self.amp_envelopes[0] is not None and 
                                      hasattr(self.amp_envelopes[0], 'states') and
                                      not np.all(self.amp_envelopes[0].states == "idle"))
        return False
    
    def note_off(self):
        """Обработка события Note Off (для совместимости)"""
        if self.block_size > 0:
            self.note_off_vectorized()
    
    def generate_sample(self, lfos, global_pitch_mod=0.0, velocity_crossfade=0.0, note_crossfade=0.0):
        """
        Генерация одного аудио сэмпла (для совместимости)
        
        Returns:
            кортеж (left_sample, right_sample) в диапазоне [-1.0, 1.0]
        """
        # Создаем массивы для совместимости
        lfos_list = [lfos] if not isinstance(lfos, list) else lfos
        global_pitch_mods = np.array([global_pitch_mod], dtype=np.float32)
        velocity_crossfades = np.array([velocity_crossfade], dtype=np.float32)
        note_crossfades = np.array([note_crossfade], dtype=np.float32)
        
        # Генерируем блок из одного сэмпла
        left_samples, right_samples = self.generate_block_vectorized(
            lfos_list, global_pitch_mods, velocity_crossfades, note_crossfades
        )
        
        if len(left_samples) > 0:
            return (left_samples[0], right_samples[0])
        else:
            return (0.0, 0.0)