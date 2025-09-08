"""
Stereo Panner implementation for XG synthesizer.
Provides stereo positioning with MIDI XG standard compliance.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class StereoPanner:
    """Класс для панорамирования звука в стерео поле"""
    def __init__(self, pan_position=0.5, sample_rate=44100):
        """
        Инициализация стерео панорамы

        Args:
            pan_position: позиция панорамирования (0.0 - лево, 0.5 - центр, 1.0 - право)
            sample_rate: частота дискретизации
        """
        self.pan_position = pan_position
        self.sample_rate = sample_rate
        self.left_gain = 0.0
        self.right_gain = 0.0
        self._update_gains()

    def _update_gains(self):
        """Обновление коэффициентов усиления для левого и правого каналов"""
        # Нормализация позиции (0 = лево, 1 = право)
        pan = max(0.0, min(1.0, self.pan_position))

        # Синусоидальное панорамирование для сохранения уровня
        angle = pan * math.pi / 2
        self.left_gain = math.cos(angle)
        self.right_gain = math.sin(angle)

    def set_pan(self, controller_value):
        """
        Установка панорамирования через MIDI контроллер

        Args:
            controller_value: значение контроллера 10 (0-127)
        """
        # MIDI контроллер 10: 0 = лево, 64 = центр, 127 = право
        self.pan_position = controller_value / 127.0
        self._update_gains()

    def set_pan_normalized(self, pan_normalized):
        """
        Установка нормализованного панорамирования

        Args:
            pan_normalized: значение от 0.0 (лево) до 1.0 (право)
        """
        self.pan_position = max(0.0, min(1.0, pan_normalized))
        self._update_gains()

    def process(self, mono_sample):
        """
        Панорамирование моно сэмпла в стерео

        Args:
            mono_sample: входной моно сэмпл

        Returns:
            кортеж (left_sample, right_sample)
        """
        return (mono_sample * self.left_gain, mono_sample * self.right_gain)

    def process_stereo(self, left_in, right_in):
        """
        Обработка стерео сэмпла с возможным дополнительным панорамированием

        Args:
            left_in: левый входной сэмпл
            right_in: правый входной сэмпл

        Returns:
            кортеж (left_out, right_out)
        """
        # При обработке стерео сэмпла, применяем панорамирование к каждому каналу
        left_out = left_in * self.left_gain + right_in * (1.0 - self.right_gain)
        right_out = right_in * self.right_gain + left_in * (1.0 - self.left_gain)
        return (left_out, right_out)
