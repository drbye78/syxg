"""
Low Frequency Oscillator (LFO) implementation for XG synthesizer.
Provides modulation sources with MIDI XG standard compliance.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class LFO:
    """Низкочастотный осциллятор с расширенной поддержкой модуляции от контроллеров"""
    def __init__(self, id=0, waveform="sine", rate=5.0, depth=1.0, delay=0.0,
                mod_wheel=0.0, channel_aftertouch=0.0, key_aftertouch=0.0,
                sample_rate=44100):
        """
        Инициализация низкочастотного осциллятора с расширенной поддержкой модуляции от контроллеров

        Args:
            id: идентификатор LFO
            waveform: форма волны (sine, triangle, square, sawtooth)
            rate: частота в Гц
            depth: глубина модуляции (0.0-1.0)
            delay: задержка в секундах
            mod_wheel: значение модуляционного колеса (0.0-1.0)
            channel_aftertouch: значение channel aftertouch (0.0-1.0)
            key_aftertouch: значение key aftertouch (0.0-1.0)
            sample_rate: частота дискретизации
        """
        self.id = id
        self.waveform = waveform
        self.rate = rate
        self.depth = depth
        self.delay = delay
        self.sample_rate = sample_rate
        self.phase = 0.0
        self.delay_samples = int(delay * sample_rate)
        self.delay_counter = 0
        self.mod_wheel = mod_wheel
        self.channel_aftertouch = channel_aftertouch
        self.key_aftertouch = key_aftertouch
        self.brightness_mod = 0.0
        self.harmonic_content_mod = 0.0
        self.breath_controller = 0.0
        self.foot_controller = 0.0

        # Поддержка модуляции параметров
        self.modulated_rate = rate
        self.modulated_depth = depth

        # Phase 2 optimization: Cache phase step to reduce update frequency
        self.phase_step_cache = 0.0
        self.phase_step_dirty = True
        self._update_phase_step()

    def set_parameters(self, waveform=None, rate=None, depth=None, delay=None,
                       modulated_rate=None, modulated_depth=None):
        """Динамическое обновление параметров LFO"""
        changed = False
        if waveform is not None:
            self.waveform = waveform
        if rate is not None:
            # Optimized clamping
            if rate < 0.1:
                self.rate = 0.1
            elif rate > 20.0:
                self.rate = 20.0
            else:
                self.rate = rate
            changed = True
        if depth is not None:
            # Optimized clamping
            if depth < 0.0:
                self.depth = 0.0
            elif depth > 1.0:
                self.depth = 1.0
            else:
                self.depth = depth
        if delay is not None:
            # Optimized clamping
            if delay < 0.0:
                self.delay = 0.0
            elif delay > 5.0:
                self.delay = 5.0
            else:
                self.delay = delay
            self.delay_samples = int(self.delay * self.sample_rate)

        # Обновление модулированных параметров
        if modulated_rate is not None:
            # Optimized clamping
            if modulated_rate < 0.1:
                self.modulated_rate = 0.1
            elif modulated_rate > 20.0:
                self.modulated_rate = 20.0
            else:
                self.modulated_rate = modulated_rate
            changed = True
        if modulated_depth is not None:
            # Optimized clamping
            if modulated_depth < 0.0:
                self.modulated_depth = 0.0
            elif modulated_depth > 1.0:
                self.modulated_depth = 1.0
            else:
                self.modulated_depth = modulated_depth

        if changed:
            self.phase_step_dirty = True

    def set_mod_wheel(self, value):
        """Установка значения модуляционного колеса (0-127)"""
        self.mod_wheel = value / 127.0
        self.phase_step_dirty = True

    def set_breath_controller(self, value):
        """
        Установка значения контроллера дыхания (0-127)

        Args:
            value: значение контроллера дыхания (0-127)
        """
        self.breath_controller = value / 127.0
        self.phase_step_dirty = True

    def set_foot_controller(self, value):
        """
        Установка значения контроллера педали (0-127)

        Args:
            value: значение контроллера педали (0-127)
        """
        self.foot_controller = value / 127.0
        self.phase_step_dirty = True

    def set_channel_aftertouch(self, value):
        """Установка значения channel aftertouch (0-127)"""
        self.channel_aftertouch = value / 127.0
        self.phase_step_dirty = True

    def set_key_aftertouch(self, value):
        """Установка значения key aftertouch (0-127)"""
        self.key_aftertouch = value / 127.0
        self.phase_step_dirty = True

    def set_brightness(self, value):
        """Установка значения brightness (0-127)"""
        self.brightness_mod = value / 127.0
        self.phase_step_dirty = True

    def set_harmonic_content(self, value):
        """Установка значения harmonic content (0-127)"""
        self.harmonic_content_mod = value / 127.0
        self.phase_step_dirty = True

    def _update_phase_step(self):
        """Обновление скорости изменения фазы с учетом модуляции"""
        # Cache calculations to reduce max() calls and improve performance
        # Базовая скорость
        base_rate = self.rate

        # Модуляция скорости от различных источников (pre-calculated)
        rate_multiplier = (
            1.0 + self.mod_wheel * 0.5 +
            self.channel_aftertouch * 0.3 +
            self.key_aftertouch * 0.3 +
            self.brightness_mod * 0.2 +
            self.harmonic_content_mod * 0.2 +
            self.breath_controller * 0.4 +
            self.foot_controller * 0.3
        )

        # Расчет эффективной скорости (optimized clamping)
        if base_rate * rate_multiplier < 0.1:
            effective_rate = 0.1
        else:
            effective_rate = base_rate * rate_multiplier

        # Расчет шага фазы (pre-calculate constants)
        self.phase_step = effective_rate * 6.283185307179586 / self.sample_rate  # 2 * π

    def step(self):
        """Генерация следующего значения LFO с учетом задержки и модуляции"""
        # Обработка задержки
        if self.delay_counter < self.delay_samples:
            self.delay_counter += 1
            return 0.0

        # Phase 2 optimization: Only update phase step when dirty
        if self.phase_step_dirty:
            self._update_phase_step()
            self.phase_step_dirty = False

        # Обновление фазы
        self.phase = (self.phase + self.phase_step) % (2 * math.pi)

        # Генерация волны в зависимости от типа
        if self.waveform == "sine":
            base_value = math.sin(self.phase)
        elif self.waveform == "triangle":
            value = (self.phase / math.pi) % 2
            base_value = 1.0 - abs(value - 1) * 2
        elif self.waveform == "square":
            base_value = 1.0 if self.phase < math.pi else -1.0
        elif self.waveform == "sawtooth":
            base_value = (self.phase / (2 * math.pi)) * 2 - 1
        else:
            base_value = 0.0

        # Применение модулированной глубины
        return base_value * self.modulated_depth
