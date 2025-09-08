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

        self._update_phase_step()

    def set_parameters(self, waveform=None, rate=None, depth=None, delay=None,
                       modulated_rate=None, modulated_depth=None):
        """Динамическое обновление параметров LFO"""
        if waveform is not None:
            self.waveform = waveform
        if rate is not None:
            self.rate = max(0.1, min(20.0, rate))
        if depth is not None:
            self.depth = max(0.0, min(1.0, depth))
        if delay is not None:
            self.delay = max(0.0, min(5.0, delay))
            self.delay_samples = int(self.delay * self.sample_rate)

        # Обновление модулированных параметров
        if modulated_rate is not None:
            self.modulated_rate = max(0.1, min(20.0, modulated_rate))
        if modulated_depth is not None:
            self.modulated_depth = max(0.0, min(1.0, modulated_depth))

        self._update_phase_step()

    def set_mod_wheel(self, value):
        """Установка значения модуляционного колеса (0-127)"""
        self.mod_wheel = value / 127.0
        self._update_phase_step()

    def set_breath_controller(self, value):
        """
        Установка значения контроллера дыхания (0-127)

        Args:
            value: значение контроллера дыхания (0-127)
        """
        self.breath_controller = value / 127.0
        self._update_phase_step()

    def set_foot_controller(self, value):
        """
        Установка значения контроллера педали (0-127)

        Args:
            value: значение контроллера педали (0-127)
        """
        self.foot_controller = value / 127.0
        self._update_phase_step()

    def set_channel_aftertouch(self, value):
        """Установка значения channel aftertouch (0-127)"""
        self.channel_aftertouch = value / 127.0
        self._update_phase_step()

    def set_key_aftertouch(self, value):
        """Установка значения key aftertouch (0-127)"""
        self.key_aftertouch = value / 127.0
        self._update_phase_step()

    def set_brightness(self, value):
        """Установка значения brightness (0-127)"""
        self.brightness_mod = value / 127.0
        self._update_phase_step()

    def set_harmonic_content(self, value):
        """Установка значения harmonic content (0-127)"""
        self.harmonic_content_mod = value / 127.0
        self._update_phase_step()

    def _update_phase_step(self):
        """Обновление скорости изменения фазы с учетом модуляции"""
        # Базовая скорость
        base_rate = self.rate

        # Модуляция скорости от различных источников
        rate_multiplier = (
            1 + self.mod_wheel * 0.5 +
            self.channel_aftertouch * 0.3 +
            self.key_aftertouch * 0.3 +
            self.brightness_mod * 0.2 +
            self.harmonic_content_mod * 0.2 +
            self.breath_controller * 0.4 +
            self.foot_controller * 0.3
        )

        # Расчет эффективной скорости
        effective_rate = max(0.1, base_rate * rate_multiplier)

        # Расчет шага фазы
        self.phase_step = effective_rate * 2 * math.pi / self.sample_rate

    def step(self):
        """Генерация следующего значения LFO с учетом задержки и модуляции"""
        # Обработка задержки
        if self.delay_counter < self.delay_samples:
            self.delay_counter += 1
            return 0.0

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
