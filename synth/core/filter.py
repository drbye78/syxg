"""
Resonant Filter implementation for XG synthesizer.
Provides filtering with MIDI XG standard compliance.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class ResonantFilter:
    """Расширенный резонансный фильтр с поддержкой harmonic content, brightness и стерео обработки"""
    def __init__(self, cutoff=1000.0, resonance=0.7, filter_type="lowpass",
                 key_follow=0.5, stereo_width=0.5, sample_rate=44100):
        self.cutoff = cutoff
        self.resonance = resonance
        self.filter_type = filter_type
        self.key_follow = key_follow
        self.stereo_width = stereo_width  # 0.0 (моно) до 1.0 (полное стерео)
        self.sample_rate = sample_rate
        self.brightness_mod = 0.0
        self.harmonic_content_mod = 0.0

        # Поддержка модуляции stereo width
        self.modulated_stereo_width = stereo_width

        # Коэффициенты для левого и правого каналов
        self.b0_l, self.b1_l, self.b2_l, self.a1_l, self.a2_l = self._calculate_coefficients(0)
        self.b0_r, self.b1_r, self.b2_r, self.a1_r, self.a2_r = self._calculate_coefficients(1)

        # Буферы для левого канала
        self.x_l = [0.0, 0.0]
        self.y_l = [0.0, 0.0]

        # Буферы для правого канала
        self.x_r = [0.0, 0.0]
        self.y_r = [0.0, 0.0]


    def _calculate_coefficients(self, channel):
        """Расчет коэффициентов фильтра для указанного канала"""
        # Учет модулированной stereo width
        stereo_width = self.modulated_stereo_width

        # Учет стерео эффектов
        if channel == 0:  # Левый канал
            stereo_factor = 1.0 - stereo_width * 0.5
        else:  # Правый канал
            stereo_factor = 1.0 - stereo_width * 0.5 + stereo_width

        # Учет brightness и harmonic content
        effective_cutoff = self.cutoff * (1 + self.brightness_mod * 0.5) * stereo_factor
        effective_resonance = self.resonance * (1 + self.harmonic_content_mod * 0.3)

        omega = 2 * math.pi * min(effective_cutoff, self.sample_rate/2) / self.sample_rate
        alpha = math.sin(omega) / (2 * max(0.001, effective_resonance))
        cos_omega = math.cos(omega)

        if self.filter_type == "lowpass":
            b0 = (1 - cos_omega) / 2
            b1 = 1 - cos_omega
            b2 = (1 - cos_omega) / 2
            a0 = 1 + alpha
            a1 = -2 * cos_omega
            a2 = 1 - alpha
        elif self.filter_type == "bandpass":
            b0 = alpha
            b1 = 0
            b2 = -alpha
            a0 = 1 + alpha
            a1 = -2 * cos_omega
            a2 = 1 - alpha
        else:  # highpass
            b0 = (1 + cos_omega) / 2
            b1 = -(1 + cos_omega)
            b2 = (1 + cos_omega) / 2
            a0 = 1 + alpha
            a1 = -2 * cos_omega
            a2 = 1 - alpha

        # Нормализация
        return b0/a0, b1/a0, b2/a0, a1/a0, a2/a0

    def set_parameters(self, cutoff=None, resonance=None, filter_type=None, key_follow=None, stereo_width=None,
                      modulated_stereo_width=None):
        """Установка параметров фильтра"""
        if cutoff is not None:
            self.cutoff = max(20.0, min(20000.0, cutoff))
        if resonance is not None:
            self.resonance = max(0.0, min(2.0, resonance))
        if filter_type is not None:
            self.filter_type = filter_type
        if key_follow is not None:
            self.key_follow = max(0.0, min(1.0, key_follow))

        # Обновление модулированной stereo width
        if modulated_stereo_width is not None:
            self.modulated_stereo_width = max(0.0, min(1.0, modulated_stereo_width))

        # Обновление stereo width
        if stereo_width is not None:
            self.stereo_width = max(0.0, min(1.0, stereo_width))
            self.modulated_stereo_width = self.stereo_width

        self.b0_l, self.b1_l, self.b2_l, self.a1_l, self.a2_l = self._calculate_coefficients(0)
        self.b0_r, self.b1_r, self.b2_r, self.a1_r, self.a2_r = self._calculate_coefficients(1)

    def set_brightness(self, value):
        """Установка модуляции от brightness (0-127)"""
        self.brightness_mod = value / 127.0
        self.b0_l, self.b1_l, self.b2_l, self.a1_l, self.a2_l = self._calculate_coefficients(0)
        self.b0_r, self.b1_r, self.b2_r, self.a1_r, self.a2_r = self._calculate_coefficients(1)

    def set_harmonic_content(self, value):
        """Установка модуляции от harmonic content (0-127)"""
        self.harmonic_content_mod = value / 127.0
        self.b0_l, self.b1_l, self.b2_l, self.a1_l, self.a2_l = self._calculate_coefficients(0)
        self.b0_r, self.b1_r, self.b2_r, self.a1_r, self.a2_r = self._calculate_coefficients(1)

    def apply_note_pitch(self, note):
        """Применение влияния высоты ноты на cutoff через key follow"""
        if self.key_follow > 0:
            # Изменение cutoff пропорционально высоте ноты (на 1 октаву вверх - удвоение cutoff)
            pitch_factor = 2 ** ((note - 60) / 12 * self.key_follow)
            return self.cutoff * pitch_factor
        return self.cutoff

    def process(self, input_sample, is_stereo=False):
        """
        Обработка одного сэмпла через фильтр

        Args:
            input_sample: моно сэмпл или кортеж (left, right)
            is_stereo: флаг, указывающий, является ли вход стерео

        Returns:
            кортеж (left_sample, right_sample)
        """
        if is_stereo:
            left_in, right_in = input_sample
        else:
            left_in = right_in = input_sample

        # Обработка левого канала
        left_out = (self.b0_l * left_in +
                   self.b1_l * self.x_l[0] +
                   self.b2_l * self.x_l[1] -
                   self.a1_l * self.y_l[0] -
                   self.a2_l * self.y_l[1])

        # Обновление буферов левого канала
        self.x_l[1] = self.x_l[0]
        self.x_l[0] = left_in
        self.y_l[1] = self.y_l[0]
        self.y_l[0] = left_out

        # Обработка правого канала
        right_out = (self.b0_r * right_in +
                    self.b1_r * self.x_r[0] +
                    self.b2_r * self.x_r[1] -
                    self.a1_r * self.y_r[0] -
                    self.a2_r * self.y_r[1])

        # Обновление буферов правого канала
        self.x_r[1] = self.x_r[0]
        self.x_r[0] = right_in
        self.y_r[1] = self.y_r[0]
        self.y_r[0] = right_out

        return (left_out, right_out)
