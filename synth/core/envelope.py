"""
ADSR Envelope implementation for XG synthesizer.
Provides envelope generation with MIDI XG standard compliance.
"""

import math
import time
from typing import Dict, List, Tuple, Optional, Callable, Any, Union


class ADSREnvelope:
    """ADSR огибающая в соответствии со стандартом MIDI XG с расширенной поддержкой контроллеров"""
    def __init__(self, delay=0.0, attack=0.01, hold=0.0, decay=0.3, sustain=0.7, release=0.5,
                 velocity_sense=1.0, key_scaling=0.0, sample_rate=44100):
        self.delay = delay
        self.attack = attack
        self.hold = hold
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.velocity_sense = velocity_sense  # Чувствительность к скорости
        self.key_scaling = key_scaling  # Зависимость от высоты ноты
        self.sample_rate = sample_rate
        self.state = "idle"
        self.level = 0.0
        self.release_start = 0.0
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.hold_notes = False

        # Поддержка модуляции параметров
        self.modulated_delay = delay
        self.modulated_attack = attack
        self.modulated_hold = hold
        self.modulated_decay = decay
        self.modulated_sustain = sustain
        self.modulated_release = release
        self._recalculate_increments()

    def _recalculate_increments(self):
        """Пересчет инкрементов для текущих параметров"""
        # Используем модулированные параметры
        delay = self.modulated_delay
        attack = self.modulated_attack
        hold = self.modulated_hold
        decay = self.modulated_decay
        sustain = self.modulated_sustain
        release = self.modulated_release

        # Delay - просто задержка перед началом атаки
        self.delay_samples = int(delay * self.sample_rate)
        self.delay_counter = 0

        # Attack - логарифмический рост (более естественный для слуха)
        if attack > 0:
            self.attack_increment = 1.0 / (attack * self.sample_rate * 2)
        else:
            self.attack_increment = 1.0  # мгновенный attack

        # Hold - фиксация уровня после атаки
        self.hold_samples = int(hold * self.sample_rate)
        self.hold_counter = 0

        # Decay - линейное уменьшение до sustain уровня
        if decay > 0:
            self.decay_decrement = (1.0 - sustain) / (decay * self.sample_rate)
        else:
            self.decay_decrement = 1.0 - sustain  # мгновенный decay

        # Release - линейное уменьшение
        if release > 0:
            self.release_decrement = 1.0 / (release * self.sample_rate)
        else:
            self.release_decrement = 1.0  # мгновенный release

    def update_parameters(self, delay=None, attack=None, hold=None, decay=None, sustain=None, release=None,
                          velocity_sense=None, key_scaling=None,
                          modulated_delay=None, modulated_attack=None, modulated_hold=None,
                          modulated_decay=None, modulated_sustain=None, modulated_release=None):
        """Динамическое обновление параметров огибающей"""
        if delay is not None:
            self.delay = max(0.0, delay)
        if attack is not None:
            self.attack = max(0.001, attack)
        if hold is not None:
            self.hold = max(0.0, hold)
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

        # Обновление модулированных параметров
        if modulated_delay is not None:
            self.modulated_delay = max(0.0, modulated_delay)
        if modulated_attack is not None:
            self.modulated_attack = max(0.001, modulated_attack)
        if modulated_hold is not None:
            self.modulated_hold = max(0.0, modulated_hold)
        if modulated_decay is not None:
            self.modulated_decay = max(0.001, modulated_decay)
        if modulated_sustain is not None:
            self.modulated_sustain = max(0.0, min(1.0, modulated_sustain))
        if modulated_release is not None:
            self.modulated_release = max(0.001, modulated_release)

        self._recalculate_increments()

        # Корректировка текущего уровня при изменении sustain
        if self.state == "sustain" and sustain is not None:
            self.level = self.sustain

    def note_on(self, velocity, note=60, soft_pedal=False):
        """Обработка события Note On"""
        # Применение чувствительности к скорости
        velocity_factor = min(1.0, (velocity / 127.0) ** self.velocity_sense)

        # Применение key scaling (зависимость параметров от высоты ноты)
        if self.key_scaling != 0.0:
            # Нормализация ноты (60 = C3)
            note_factor = (note - 60) / 60.0
            key_factor = 1.0 + note_factor * self.key_scaling
            # Применяем ко всем временным параметрам
            self.update_parameters(
                modulated_delay=self.delay * key_factor,
                modulated_attack=self.attack * key_factor,
                modulated_hold=self.hold * key_factor,
                modulated_decay=self.decay * key_factor,
                modulated_release=self.release * key_factor
            )
        else:
            # Если key scaling не применяется, убедимся, что модулированные параметры равны базовым
            self.update_parameters(
                modulated_delay=self.delay,
                modulated_attack=self.attack,
                modulated_hold=self.hold,
                modulated_decay=self.decay,
                modulated_release=self.release
            )

        # Применение soft pedal (уменьшает громкость и атаку)
        if soft_pedal:
            velocity_factor *= 0.5
            # Увеличение attack времени при soft pedal
            self.update_parameters(modulated_attack=self.attack * 2.0)

        self.state = "delay"
        self.delay_counter = 0
        self.level = 0.0 * velocity_factor

        if self.hold_notes:
            self.state = "sustain"
            self.level = self.sustain * velocity_factor

    def note_off(self):
        """Обработка события Note Off"""
        if not self.sustain_pedal and not self.sostenuto_pedal and not self.hold_notes:
            if self.state not in ["release", "idle"]:
                self.release_start = self.level
                self.state = "release"

    def sustain_pedal_on(self):
        """Включение sustain педали"""
        self.sustain_pedal = True

    def sustain_pedal_off(self):
        """Выключение sustain педали"""
        self.sustain_pedal = False
        if self.state == "sustain" and not (self.sostenuto_pedal or self.hold_notes):
            self.release_start = self.level
            self.state = "release"

    def sostenuto_pedal_on(self):
        """Включение sostenuto педали (удержание текущих нот)"""
        self.sostenuto_pedal = True
        if self.state in ["sustain", "decay"]:
            self.held_by_sostenuto = True

    def sostenuto_pedal_off(self):
        """Выключение sostenuto педали"""
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        if self.state == "sustain" and not (self.sustain_pedal or self.hold_notes):
            self.release_start = self.level
            self.state = "release"

    def soft_pedal_on(self):
        """Включение soft pedal"""
        self.soft_pedal = True

    def soft_pedal_off(self):
        """Выключение soft pedal"""
        self.soft_pedal = False
        # Восстановление оригинальных параметров
        self.update_parameters(
            modulated_attack=self.attack,
            modulated_hold=self.hold,
            modulated_decay=self.decay,
            modulated_release=self.release
        )

    def all_notes_off(self):
        """Сброс всех нот (как при All Notes Off контроллере)"""
        self.hold_notes = True
        if self.state not in ["release", "idle"]:
            self.state = "sustain"
            self.level = self.sustain

    def reset_all_notes(self):
        """Полный сброс (All Sound Off)"""
        self.hold_notes = False
        self.sustain_pedal = False
        self.sostenuto_pedal = False
        self.held_by_sostenuto = False
        self.soft_pedal = False
        self.release_start = self.level
        self.state = "release"

    def process(self):
        """Обработка одного сэмпла огибающей"""
        if self.state == "delay":
            self.delay_counter += 1
            if self.delay_counter >= self.delay_samples:
                self.state = "attack"

        elif self.state == "attack":
            self.level = min(1.0, self.level + self.attack_increment)
            if self.level >= 1.0:
                self.level = 1.0
                self.state = "hold"
                self.hold_counter = 0

        elif self.state == "hold":
            self.hold_counter += 1
            if self.hold_counter >= self.hold_samples:
                self.state = "decay"

        elif self.state == "decay":
            self.level = max(self.sustain, self.level - self.decay_decrement)
            if abs(self.level - self.sustain) < 0.001:
                self.level = self.sustain
                self.state = "sustain"

        elif self.state == "sustain":
            # Уровень остается на sustain уровне
            pass

        elif self.state == "release":
            self.level = max(0.0, self.level - self.release_decrement)
            if self.level <= 0:
                self.level = 0.0
                self.state = "idle"

        return self.level
