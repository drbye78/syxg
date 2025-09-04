import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from collections import OrderedDict

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

class ModulationSource:
    """Класс для представления источника модуляции"""
    VELOCITY = "velocity"
    AFTER_TOUCH = "after_touch"
    MOD_WHEEL = "mod_wheel"
    LFO1 = "lfo1"
    LFO2 = "lfo2"
    LFO3 = "lfo3"
    AMP_ENV = "amp_env"
    FILTER_ENV = "filter_env"
    PITCH_ENV = "pitch_env"
    KEY_PRESSURE = "key_pressure"
    BRIGHTNESS = "brightness"
    HARMONIC_CONTENT = "harmonic_content"
    PORTAMENTO = "portamento"
    VIBRATO = "vibrato"
    TREMOLO = "tremolo"
    TREMOLO_DEPTH = "tremolo_depth"
    TREMOLO_RATE = "tremolo_rate"
    NOTE_NUMBER = "note_number"
    
    # Новые источники из SoundFont
    BREATH_CONTROLLER = "breath_controller"
    FOOT_CONTROLLER = "foot_controller"
    DATA_ENTRY = "data_entry"
    VOLUME_CC = "volume_cc"
    BALANCE = "balance"
    PORTAMENTO_TIME_CC = "portamento_time_cc"
    
    @staticmethod
    def get_all_sources():
        return [
            ModulationSource.VELOCITY,
            ModulationSource.AFTER_TOUCH,
            ModulationSource.MOD_WHEEL,
            ModulationSource.LFO1,
            ModulationSource.LFO2,
            ModulationSource.LFO3,
            ModulationSource.AMP_ENV,
            ModulationSource.FILTER_ENV,
            ModulationSource.PITCH_ENV,
            ModulationSource.KEY_PRESSURE,
            ModulationSource.BRIGHTNESS,
            ModulationSource.HARMONIC_CONTENT,
            ModulationSource.PORTAMENTO,
            ModulationSource.VIBRATO,
            ModulationSource.TREMOLO,
            ModulationSource.TREMOLO_DEPTH,
            ModulationSource.TREMOLO_RATE,
            ModulationSource.NOTE_NUMBER,
            ModulationSource.BREATH_CONTROLLER,
            ModulationSource.FOOT_CONTROLLER,
            ModulationSource.DATA_ENTRY,
            ModulationSource.VOLUME_CC,
            ModulationSource.BALANCE,
            ModulationSource.PORTAMENTO_TIME_CC
        ]

class ModulationDestination:
    """Класс для представления цели модуляции"""
    FILTER_CUTOFF = "filter_cutoff"
    PITCH = "pitch"
    FILTER_RESONANCE = "filter_resonance"
    AMP = "amp"
    PAN = "pan"
    LFO1_RATE = "lfo1_rate"
    LFO2_RATE = "lfo2_rate"
    LFO3_RATE = "lfo3_rate"
    LFO1_DEPTH = "lfo1_depth"
    LFO2_DEPTH = "lfo2_depth"
    LFO3_DEPTH = "lfo3_depth"
    VELOCITY_CROSSFADE = "velocity_crossfade"
    NOTE_CROSSFADE = "note_crossfade"
    
    # Новые цели из SoundFont
    FILTER_ATTACK = "filter_attack"
    FILTER_DECAY = "filter_decay"
    FILTER_DELAY = "filter_delay"
    FILTER_SUSTAIN = "filter_sustain"
    FILTER_RELEASE = "filter_release"
    FILTER_HOLD = "filter_hold"
    AMP_ATTACK = "amp_attack"
    AMP_DECAY = "amp_decay"
    AMP_DELAY = "amp_delay"
    AMP_SUSTAIN = "amp_sustain"
    AMP_RELEASE = "amp_release"
    AMP_HOLD = "amp_hold"
    PITCH_ATTACK = "pitch_attack" 
    PITCH_DECAY = "pitch_decay"                                                                     
    PITCH_SUSTAIN = "pitch_sustain"
    PITCH_RELEASE = "pitch_release"
    PITCH_HOLD = "pitch_hold"
    STEREO_WIDTH = "stereo_width"
    TREMOLO_DEPTH = "tremolo_depth"
    TREMOLO_RATE = "tremolo_rate"
    COARSE_TUNE = "coarse_tune"
    FINE_TUNE = "fine_tune"
    
    @staticmethod
    def get_all_destinations():
        return [
            ModulationDestination.PITCH,
            ModulationDestination.FILTER_CUTOFF,
            ModulationDestination.FILTER_RESONANCE,
            ModulationDestination.AMP,
            ModulationDestination.PAN,
            ModulationDestination.LFO1_RATE,
            ModulationDestination.LFO2_RATE,
            ModulationDestination.LFO3_RATE,
            ModulationDestination.LFO1_DEPTH,
            ModulationDestination.LFO2_DEPTH,
            ModulationDestination.LFO3_DEPTH,
            ModulationDestination.VELOCITY_CROSSFADE,
            ModulationDestination.NOTE_CROSSFADE,
            ModulationDestination.FILTER_ATTACK,
            ModulationDestination.FILTER_DECAY,
            ModulationDestination.FILTER_SUSTAIN,
            ModulationDestination.FILTER_RELEASE,
            ModulationDestination.FILTER_HOLD,
            ModulationDestination.AMP_ATTACK,
            ModulationDestination.AMP_DECAY,
            ModulationDestination.AMP_SUSTAIN,
            ModulationDestination.AMP_RELEASE,
            ModulationDestination.AMP_HOLD,
            ModulationDestination.PITCH_ATTACK,
            ModulationDestination.PITCH_DECAY,
            ModulationDestination.PITCH_SUSTAIN,
            ModulationDestination.PITCH_RELEASE,
            ModulationDestination.PITCH_HOLD,
            ModulationDestination.STEREO_WIDTH,
            ModulationDestination.TREMOLO_DEPTH,
            ModulationDestination.TREMOLO_RATE,
            ModulationDestination.COARSE_TUNE,
            ModulationDestination.FINE_TUNE
        ]

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
            self.routes[index] = ModulationRoute( # type: ignore
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
            кортеж (left, right)
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

class PartialGenerator:
    """
    Частичный генератор в соответствии с концепцией Partial Structure XG.
    Каждый PartialGenerator отвечает за одну частичную структуру в общем тоне.
    """
    def __init__(self, wavetable, note, velocity, program, partial_id, 
                 partial_params, is_drum=False, sample_rate=44100):
        """
        Инициализация частичного генератора.
        
        Args:
            wavetable: объект, предоставляющий доступ к wavetable сэмплам
            note: MIDI нота (0-127)
            velocity: громкость ноты (0-127)
            program: номер программы (патча)
            partial_id: идентификатор частичной структуры (0-3)
            partial_params: параметры для этой частичной структуры
            is_drum: работает ли в режиме барабана
            sample_rate: частота дискретизации
        """
        self.wavetable = wavetable  # Теперь сохраняем ссылку на wavetable
        self.partial_id = partial_id
        self.note = note
        self.velocity = velocity
        self.program = program
        self.is_drum = is_drum
        self.sample_rate = sample_rate
        self.active = True
        
        # Параметры частичной структуры
        self.level = partial_params.get("level", 1.0)  # Уровень смешивания
        self.pan = partial_params.get("pan", 0.5)  # Позиция панорамирования
        self.key_range_low = partial_params.get("key_range_low", 0)
        self.key_range_high = partial_params.get("key_range_high", 127)
        self.velocity_range_low = partial_params.get("velocity_range_low", 0)
        self.velocity_range_high = partial_params.get("velocity_range_high", 127)
        self.key_scaling = partial_params.get("key_scaling", 0.0)
        self.velocity_sense = partial_params.get("velocity_sense", 1.0)
        self.crossfade_velocity = partial_params.get("crossfade_velocity", False)
        self.crossfade_note = partial_params.get("crossfade_note", False)
        self.initial_attenuation = partial_params.get("initial_attenuation", 0.0)  # in dB
        self.scale_tuning = partial_params.get("scale_tuning", 100)  # in cents
        self.overriding_root_key = partial_params.get("overriding_root_key", -1)
        self.start_coarse = partial_params.get("start_coarse", 0)
        self.end_coarse = partial_params.get("end_coarse", 0)
        self.start_loop_coarse = partial_params.get("start_loop_coarse", 0)
        self.end_loop_coarse = partial_params.get("end_loop_coarse", 0)
        
        # Проверка, попадает ли нота в диапазон частичной структуры
        if not (self.key_range_low <= note <= self.key_range_high):
            self.active = False
            self.amp_envelope = None
            self.filter_envelope = None
            self.pitch_envelope = None 
            self.filter = None
            return
            
        # Проверка, попадает ли velocity в диапазон частичной структуры
        if not (self.velocity_range_low <= velocity <= self.velocity_range_high):
            self.active = False
            self.amp_envelope = None
            self.filter_envelope = None
            self.pitch_envelope = None 
            self.filter = None
            return
        
        # Инициализация фазы
        self.phase = 0.0
        self._update_phase_step()
        
        # Инициализация огибающих
        self.amp_envelope = ADSREnvelope(
            delay=partial_params["amp_envelope"]["delay"],
            attack=partial_params["amp_envelope"]["attack"],
            hold=partial_params["amp_envelope"]["hold"],
            decay=partial_params["amp_envelope"]["decay"],
            sustain=partial_params["amp_envelope"]["sustain"],
            release=partial_params["amp_envelope"]["release"],
            velocity_sense=self.velocity_sense,
            key_scaling=partial_params["amp_envelope"].get("key_scaling", 0.0),
            sample_rate=sample_rate
        )
        
        # Для барабанов фильтровая огибающая может быть отключена
        if not is_drum or partial_params.get("use_filter_env", True):
            self.filter_envelope = ADSREnvelope(
                delay=partial_params["filter_envelope"]["delay"],
                attack=partial_params["filter_envelope"]["attack"],
                hold=partial_params["filter_envelope"]["hold"],
                decay=partial_params["filter_envelope"]["decay"],
                sustain=partial_params["filter_envelope"]["sustain"],
                release=partial_params["filter_envelope"]["release"],
                key_scaling=partial_params["filter_envelope"].get("key_scaling", 0.0),
                sample_rate=sample_rate
            )
        else:
            self.filter_envelope = None
        
        # Для барабанов pitch огибающая может быть отключена
        if not is_drum or partial_params.get("use_pitch_env", True):
            self.pitch_envelope = ADSREnvelope(
                delay=partial_params["pitch_envelope"]["delay"],
                attack=partial_params["pitch_envelope"]["attack"],
                hold=partial_params["pitch_envelope"]["hold"],
                decay=partial_params["pitch_envelope"]["decay"],
                sustain=partial_params["pitch_envelope"]["sustain"],
                release=partial_params["pitch_envelope"]["release"],
                sample_rate=sample_rate
            )
        else:
            self.pitch_envelope = None
        
        # Инициализация фильтра
        self.filter = ResonantFilter(
            cutoff=partial_params["filter"]["cutoff"],
            resonance=partial_params["filter"]["resonance"],
            filter_type=partial_params["filter"]["type"],
            key_follow=partial_params["filter"].get("key_follow", 0.5),
            stereo_width=partial_params.get("stereo_width", 0.5),
            sample_rate=sample_rate
        )
        
        # Запуск огибающих при Note On
        self.amp_envelope.note_on(velocity, note)
        if self.filter_envelope:
            self.filter_envelope.note_on(velocity, note)
        if self.pitch_envelope:
            self.pitch_envelope.note_on(velocity, note)
        
        # Поддержка модуляции
        self.velocity_crossfade = 0.0
        self.note_crossfade = 0.0
    
    def _update_phase_step(self):
        """Обновление шага фазы для частичной структуры"""
        # Получение сэмпла из wavetable для этой частичной структуры
        table = self.wavetable.get_partial_table(self.note, self.program, self.partial_id, self.velocity)
        if table is None or len(table) == 0:
            self.active = False
            return
            
        # Determine the root key to use
        root_key = self.overriding_root_key if self.overriding_root_key >= 0 else self.note
            
        # Базовая частота для текущей ноты с учетом scale tuning
        base_freq = 440.0 * (2 ** ((root_key - 69) / 12.0))
        
        # Apply scale tuning (convert cents to frequency multiplier)
        tuning_multiplier = 2 ** (self.scale_tuning / 1200.0)
        base_freq *= tuning_multiplier
        
        # Учет key scaling (зависимость pitch от высоты ноты)
        pitch_factor = 2 ** ((self.note - 60) * self.key_scaling / 1200.0)
        final_freq = base_freq * pitch_factor
        
        table_length = len(table)
        self.phase_step = final_freq / self.sample_rate * table_length
    
    def is_active(self):
        """Проверка, активен ли частичный генератор"""
        return self.active and self.amp_envelope and self.amp_envelope.state != "idle"
    
    def note_off(self):
        """Обработка события Note Off"""
        if self.is_active():
            if self.amp_envelope:
                self.amp_envelope.note_off()
            if self.filter_envelope:
                self.filter_envelope.note_off()
            if self.pitch_envelope:
                self.pitch_envelope.note_off()
    
    def generate_sample(self, lfos, global_pitch_mod=0.0, velocity_crossfade=0.0, note_crossfade=0.0):
        """
        Генерация одного аудио сэмпла для частичной структуры
        
        Args:
            lfos: список LFO для использования в модуляции
            global_pitch_mod: глобальная модуляция pitch (от pitch bend и т.д.)
            velocity_crossfade: коэффициент кросс-фейда по velocity
            note_crossfade: коэффициент кросс-фейда по ноте
            
        Returns:
            кортеж (left_sample, right_sample) в диапазоне [-1.0, 1.0]
        """
        # Сохраняем кросс-фейды для использования в других методах
        self.velocity_crossfade = velocity_crossfade
        self.note_crossfade = note_crossfade
        
        if not self.is_active():
            return (0.0, 0.0)
        
        # Получение текущих значений LFO
        lfo_values = {
            "lfo1": lfos[0].step() if len(lfos) > 0 else 0.0,
            "lfo2": lfos[1].step() if len(lfos) > 1 else 0.0,
            "lfo3": lfos[2].step() if len(lfos) > 2 else 0.0
        }
        
        # Обработка амплитудной огибающей
        amp_env = self.amp_envelope.process() if self.amp_envelope else 0.0
        if amp_env <= 0:
            # self.active = False
            return (0.0, 0.0)
            
        # Обработка фильтровой огибающей
        filter_env = 0.0
        if self.filter_envelope:
            filter_env = self.filter_envelope.process()
        
        # Обработка pitch огибающей
        pitch_env = 0.0
        if self.pitch_envelope:
            pitch_env = self.pitch_envelope.process()
        
        # Расчет модуляции pitch
        pitch_mod = (
            lfo_values["lfo1"] * 0.5 +  # Пример глубины модуляции
            lfo_values["lfo2"] * 0.3 +
            pitch_env * 0.7 +
            global_pitch_mod
        )
        
        # Пересчет фазы с учетом модуляции pitch
        base_freq = 440.0 * (2 ** ((self.note - 69) / 12.0))
        freq_multiplier = 2 ** (pitch_mod / 1200.0)  # в центах
        final_freq = base_freq * freq_multiplier
        
        # Обновление phase_step для текущего сэмпла
        table = self.wavetable.get_partial_table(self.note, self.program, self.partial_id, self.velocity)
        if not table or len(table) == 0:
            # self.active = False
            return (0.0, 0.0)
            
        table_length = len(table)
        self.phase_step = final_freq / self.sample_rate * table_length
        
        # Проверка типа сэмплов (моно или стерео)
        is_stereo = isinstance(table[0], tuple) or (isinstance(table[0], list) and len(table[0]) == 2)
        
        # Генерация сэмпла из wavetable
        self.phase += self.phase_step
        if self.phase >= len(table):
            self.phase -= len(table)
            
        # Получение сэмпла с линейной интерполяцией
        idx = int(self.phase)
        frac = self.phase - idx
        next_idx = (idx + 1) % len(table)
        
        if is_stereo:
            # Стерео сэмпл
            left_sample = table[idx][0] + frac * (table[next_idx][0] - table[idx][0])
            right_sample = table[idx][1] + frac * (table[next_idx][1] - table[idx][1])
            sample = (left_sample, right_sample)
        else:
            # Моно сэмпл
            sample_val = table[idx] + frac * (table[next_idx] - table[idx])
            sample = sample_val
        
        # Общая модуляция cutoff: огибающая + LFO
        if self.filter:
            filter_cutoff_mod = 0.0
            if self.filter_envelope:
                filter_cutoff_mod = filter_env * 0.5 + lfo_values["lfo1"] * 0.3
            
            # Ограничение cutoff в допустимом диапазоне
            base_cutoff = self.filter.apply_note_pitch(self.note)
            cutoff = max(20, min(20000, base_cutoff * (0.5 + filter_cutoff_mod * 0.5)))
            self.filter.set_parameters(cutoff=cutoff)
            
            # Применение фильтра
            if is_stereo:
                filtered_sample = self.filter.process(sample, is_stereo=True)
            else:
                filtered_sample = self.filter.process(sample, is_stereo=False)
        else:
            filtered_sample = sample

        # Применение огибающей амплитуды
        amp_env = self.amp_envelope.process() if self.amp_envelope else 0.0
        
        # Применение уровня частичной структуры с учетом кросс-фейда
        effective_level = self.level
        
        # Учет кросс-фейда по velocity
        if self.crossfade_velocity:
            effective_level *= (1.0 - self.velocity_crossfade)
        
        # Учет кросс-фейда по ноте
        if self.crossfade_note:
            effective_level *= (1.0 - self.note_crossfade)
            
        # Apply initial attenuation (convert dB to linear scale)
        attenuation_factor = 10 ** (-self.initial_attenuation / 20.0)
        effective_level *= attenuation_factor
        
        if is_stereo:
            left_out = filtered_sample[0] * amp_env * effective_level
            right_out = filtered_sample[1] * amp_env * effective_level
        else:
            mono_sample = (filtered_sample[0] + filtered_sample[1]) * 0.5  * amp_env * effective_level # type: ignore
            # Применение панорамирования для этой частичной структуры
            panner = StereoPanner(pan_position=self.pan, sample_rate=self.sample_rate)
            left_out, right_out = panner.process(mono_sample)
        
        return (left_out, right_out)

class DrumNoteMap:
    """Класс для отображения MIDI нот на барабанные инструменты в соответствии с XG стандартом"""
    
    # Стандартная карта барабанов XG
    XG_DRUM_MAP = {
        35: "Acoustic Bass Drum",
        36: "Bass Drum 1",
        37: "Side Stick",
        38: "Acoustic Snare",
        39: "Hand Clap",
        40: "Electric Snare",
        41: "Low Floor Tom",
        42: "Closed Hi Hat",
        43: "High Floor Tom",
        44: "Pedal Hi-Hat",
        45: "Low Tom",
        46: "Open Hi-Hat",
        47: "Low-Mid Tom",
        48: "Hi-Mid Tom",
        49: "Crash Cymbal 1",
        50: "High Tom",
        51: "Ride Cymbal 1",
        52: "Chinese Cymbal",
        53: "Ride Bell",
        54: "Tambourine",
        55: "Splash Cymbal",
        56: "Cowbell",
        57: "Crash Cymbal 2",
        58: "Vibra Slap",
        59: "Ride Cymbal 2",
        60: "High Bongo",
        61: "Low Bongo",
        62: "Mute High Conga",
        63: "Open High Conga",
        64: "Low Conga",
        65: "High Timbale",
        66: "Low Timbale",
        67: "High Agogo",
        68: "Low Agogo",
        69: "Cabasa",
        70: "Maracas",
        71: "Short Whistle",
        72: "Long Whistle",
        73: "Short Guiro",
        74: "Long Guiro",
        75: "Claves",
        76: "High Wood Block",
        77: "Low Wood Block",
        78: "Mute Cuica",
        79: "Open Cuica",
        80: "Mute Triangle",
        81: "Open Triangle"
    }
    
    def __init__(self, drum_map=None):
        """
        Инициализация карты барабанов
        
        Args:
            drum_map: пользовательская карта барабанов (словарь note -> имя)
        """
        if drum_map is None:
            self.drum_map = self.XG_DRUM_MAP.copy()
        else:
            self.drum_map = drum_map
    
    def get_instrument_name(self, note):
        """
        Получение имени инструмента по MIDI ноте
        
        Args:
            note: MIDI нота (0-127)
            
        Returns:
            имя барабанного инструмента или None
        """
        return self.drum_map.get(note, None)
    
    def is_drum_note(self, note):
        """
        Проверка, является ли нота барабанным инструментом
        
        Args:
            note: MIDI нота (0-127)
            
        Returns:
            True, если это барабанный инструмент, иначе False
        """
        return note in self.drum_map

class ChannelNote:
    """Represents an active note on a channel"""
    def __init__(self, note: int, velocity: int, program: int, bank: int, 
                 wavetable, sample_rate: int, is_drum: bool = False):
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.is_drum = is_drum
        self.active = True
        self.sample_rate = sample_rate
        self.detune = 0.0
        self.phaser_depth = 0.0
        
        # Initialize parameters for this note
        self.params = self._get_parameters(program, bank, wavetable)
        
        # Initialize LFOs for this note
        lfo1_params = self.params.get("lfo1", {"waveform": "sine", "rate": 5.0, "depth": 0.5, "delay": 0.0})
        lfo2_params = self.params.get("lfo2", {"waveform": "triangle", "rate": 2.0, "depth": 0.3, "delay": 0.0})
        lfo3_params = self.params.get("lfo3", {"waveform": "sawtooth", "rate": 0.5, "depth": 0.1, "delay": 0.5})
        
        self.lfos = [
            LFO(id=0, waveform=lfo1_params["waveform"],
                rate=lfo1_params["rate"],
                depth=lfo1_params["depth"],
                delay=lfo1_params["delay"],
                sample_rate=sample_rate),
            LFO(id=1, waveform=lfo2_params["waveform"],
                rate=lfo2_params["rate"],
                depth=lfo2_params["depth"],
                delay=lfo2_params["delay"],
                sample_rate=sample_rate),
            LFO(id=2, waveform=lfo3_params["waveform"],
                rate=lfo3_params["rate"],
                depth=lfo3_params["depth"],
                delay=lfo3_params["delay"],
                sample_rate=sample_rate)
        ]
        
        # Initialize modulation matrix
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()
        
        # Initialize partials
        self.partials = []
        self._setup_partials(wavetable)
        
        # If no active partials and wavetable is available, create basic generator
        if not any(partial.is_active() for partial in self.partials) and wavetable is None:
            self._setup_basic_generator()
            
        # If still no active partials, mark as inactive
        if not any(partial.is_active() for partial in self.partials):
            self.active = False
            
        # Initialize envelopes
        self._initialize_envelopes()
        
    def _get_parameters(self, program: int, bank: int, wavetable):
        """Get parameters for this note"""
        try:
            params = wavetable.get_program_parameters(program, bank)
            if params:
                return params
        except Exception as e:
            print(f"Warning: Failed to get parameters from wavetable: {e}")
                
        # Default parameters (XG specification)
        return {
            "amp_envelope": {
                "delay": 0.0,
                "attack": 0.01,
                "hold": 0.0,
                "decay": 0.3,
                "sustain": 0.7,
                "release": 0.5,
                "velocity_sense": 1.0,
                "key_scaling": 0.0
            },
            "filter_envelope": {
                "delay": 0.0,
                "attack": 0.1,
                "hold": 0.0,
                "decay": 0.5,
                "sustain": 0.6,
                "release": 0.8,
                "key_scaling": 0.0
            },
            "pitch_envelope": {
                "delay": 0.0,
                "attack": 0.05,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.05
            },
            "filter": {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass",
                "key_follow": 0.5
            },
            "lfo1": {
                "waveform": "sine",
                "rate": 5.0,
                "depth": 0.5,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": 2.0,
                "depth": 0.3,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sawtooth",
                "rate": 0.5,
                "depth": 0.1,
                "delay": 0.5
            },
            "modulation": {
                "lfo1_to_pitch": 50.0,    # in cents
                "lfo2_to_pitch": 30.0,    # in cents
                "lfo3_to_pitch": 10.0,    # in cents
                "env_to_pitch": 30.0,     # in cents
                "aftertouch_to_pitch": 20.0,  # in cents
                "lfo_to_filter": 0.3,
                "env_to_filter": 0.5,
                "aftertouch_to_filter": 0.2,
                "tremolo_depth": 0.3,
                "vibrato_depth": 50.0,    # in cents
                "vibrato_rate": 5.0,
                "vibrato_delay": 0.0
            },
            "partials": [
                {
                    "level": 1.0,
                    "pan": 0.5,
                    "key_range_low": 0,
                    "key_range_high": 127,
                    "velocity_range_low": 0,
                    "velocity_range_high": 127,
                    "key_scaling": 0.0,
                    "velocity_sense": 1.0,
                    "crossfade_velocity": True,
                    "crossfade_note": True,
                    "use_filter_env": True,
                    "use_pitch_env": True,
                    "amp_envelope": {
                        "delay": 0.0,
                        "attack": 0.01,
                        "hold": 0.0,
                        "decay": 0.3,
                        "sustain": 0.7,
                        "release": 0.5,
                        "key_scaling": 0.0
                    },
                    "filter_envelope": {
                        "delay": 0.0,
                        "attack": 0.1,
                        "hold": 0.0,
                        "decay": 0.5,
                        "sustain": 0.6,
                        "release": 0.8,
                        "key_scaling": 0.0
                    },
                    "pitch_envelope": {
                        "delay": 0.0,
                        "attack": 0.05,
                        "hold": 0.0,
                        "decay": 0.1,
                        "sustain": 0.0,
                        "release": 0.05
                    },
                    "filter": {
                        "cutoff": 1000.0,
                        "resonance": 0.7,
                        "type": "lowpass"
                    },
                    "coarse_tune": 0,
                    "fine_tune": 0,
                    "initial_attenuation": 0,  # in dB
                    "scale_tuning": 100,       # in cents
                    "overriding_root_key": -1
                }
            ]
        }
        
    def _setup_partials(self, wavetable):
        """Setup partial structures for this note"""
        partials_params = self.params.get("partials", [])
        
        # Create partial generators for each partial structure
        for i, partial_params in enumerate(partials_params):
            # Apply key scaling to envelope parameters
            if "keynum_to_vol_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_vol_env_decay"] / 1200.0
                partial_params["amp_envelope"]["key_scaling"] = key_scaling
            
            if "keynum_to_mod_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_mod_env_decay"] / 1200.0
                partial_params["filter_envelope"]["key_scaling"] = key_scaling
            
            # Apply coarseTune and fineTune
            self.coarse_tune = partial_params.get("coarse_tune", 0)
            self.fine_tune = partial_params.get("fine_tune", 0)
            
            partial = PartialGenerator(
                wavetable=wavetable,
                note=self.note,
                velocity=self.velocity,
                program=self.program,
                partial_id=i,
                partial_params=partial_params,
                is_drum=self.is_drum,
                sample_rate=self.sample_rate
            )
            self.partials.append(partial)
            
    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix for this note"""
        # Get modulation parameters or use defaults
        modulation_params = self.params.get("modulation", {})
        
        # LFO1 -> Pitch
        self.mod_matrix.set_route(0, 
            ModulationSource.LFO1, 
            ModulationDestination.PITCH,
            amount=modulation_params.get("lfo1_to_pitch", 50.0) / 100.0,
            polarity=1.0
        )
        
        # LFO2 -> Pitch
        self.mod_matrix.set_route(1, 
            ModulationSource.LFO2, 
            ModulationDestination.PITCH,
            amount=modulation_params.get("lfo2_to_pitch", 30.0) / 100.0,
            polarity=1.0
        )
        
        # LFO3 -> Pitch
        self.mod_matrix.set_route(2, 
            ModulationSource.LFO3, 
            ModulationDestination.PITCH,
            amount=modulation_params.get("lfo3_to_pitch", 10.0) / 100.0,
            polarity=1.0
        )
        
        # Amp Envelope -> Filter Cutoff
        self.mod_matrix.set_route(3, 
            ModulationSource.AMP_ENV, 
            ModulationDestination.FILTER_CUTOFF,
            amount=modulation_params.get("env_to_filter", 0.5),
            polarity=1.0
        )
        
        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(4, 
            ModulationSource.LFO1, 
            ModulationDestination.FILTER_CUTOFF,
            amount=modulation_params.get("lfo_to_filter", 0.3),
            polarity=1.0
        )
        
        # Velocity -> Amp
        self.mod_matrix.set_route(5, 
            ModulationSource.VELOCITY, 
            ModulationDestination.AMP,
            amount=0.5,
            velocity_sensitivity=0.5
        )
        
        # Note Number -> Pitch
        self.mod_matrix.set_route(6, 
            ModulationSource.NOTE_NUMBER, 
            ModulationDestination.PITCH,
            amount=1.0,
            key_scaling=1.0
        )
        
        # Vibrato Depth
        self.mod_matrix.set_route(7, 
            ModulationSource.VIBRATO, 
            ModulationDestination.PITCH,
            amount=modulation_params.get("vibrato_depth", 50.0) / 100.0,
            polarity=1.0
        )
        
        # Tremolo Depth
        self.mod_matrix.set_route(8, 
            ModulationSource.TREMOLO_DEPTH, 
            ModulationDestination.AMP,
            amount=modulation_params.get("tremolo_depth", 0.3),
            polarity=1.0
        )
        
    def _initialize_envelopes(self):
        """Initialize envelopes for all partials"""
        for partial in self.partials:
            if partial.active:
                partial.amp_envelope.note_on(self.velocity, self.note)
                if partial.filter_envelope:
                    partial.filter_envelope.note_on(self.velocity, self.note)
                if partial.pitch_envelope:
                    partial.pitch_envelope.note_on(self.velocity, self.note)
                
    def note_off(self):
        """Handle note off for this note"""
        for partial in self.partials:
            partial.note_off()
            
    def is_active(self):
        """Check if this note is still active"""
        return self.active and any(partial.is_active() for partial in self.partials)
        
    def generate_sample(self, channel_state: Dict[str, Any], global_pitch_mod: float = 0.0):
        """Generate a sample for this note"""
        if not self.is_active():
            return (0.0, 0.0)
            
        # Get key pressure for this specific note
        key_pressure = channel_state.get("key_pressure", {}).get(self.note, 0)
            
        # Update LFOs with channel state
        for lfo in self.lfos:
            lfo.set_mod_wheel(channel_state["controllers"].get(1, 0))
            lfo.set_breath_controller(channel_state["controllers"].get(2, 0))
            lfo.set_foot_controller(channel_state["controllers"].get(4, 0))
            lfo.set_brightness(channel_state["controllers"].get(74, 64))
            lfo.set_harmonic_content(channel_state["controllers"].get(71, 64))
            lfo.set_channel_aftertouch(channel_state.get("channel_pressure_value", 0))
            lfo.set_key_aftertouch(key_pressure)
            
        # Collect modulation sources
        sources = {
            ModulationSource.VELOCITY: self.velocity / 127.0,
            ModulationSource.AFTER_TOUCH: channel_state.get("channel_pressure_value", 0) / 127.0,
            ModulationSource.MOD_WHEEL: channel_state["controllers"].get(1, 0) / 127.0,
            ModulationSource.BREATH_CONTROLLER: channel_state["controllers"].get(2, 0) / 127.0,
            ModulationSource.FOOT_CONTROLLER: channel_state["controllers"].get(4, 0) / 127.0,
            ModulationSource.DATA_ENTRY: channel_state["controllers"].get(6, 100) / 127.0,
            ModulationSource.LFO1: self.lfos[0].step(),
            ModulationSource.LFO2: self.lfos[1].step(),
            ModulationSource.LFO3: self.lfos[2].step(),
            ModulationSource.AMP_ENV: self.partials[0].amp_envelope.process() if self.partials and self.partials[0].amp_envelope else 0.0,
            ModulationSource.FILTER_ENV: self.partials[0].filter_envelope.process() if self.partials and self.partials[0].filter_envelope else 0.0,
            ModulationSource.PITCH_ENV: self.partials[0].pitch_envelope.process() if self.partials and self.partials[0].pitch_envelope else 0.0,
            ModulationSource.KEY_PRESSURE: key_pressure / 127.0,
            ModulationSource.BRIGHTNESS: channel_state["controllers"].get(74, 64) / 127.0,
            ModulationSource.HARMONIC_CONTENT: channel_state["controllers"].get(71, 64) / 127.0,
            ModulationSource.PORTAMENTO: 1.0 if channel_state["portamento_active"] else 0.0,
            ModulationSource.VIBRATO: 50.0 / 100.0,
            ModulationSource.TREMOLO: 0.0,
            ModulationSource.TREMOLO_DEPTH: 0.0,
            ModulationSource.TREMOLO_RATE: 4.0,
            ModulationSource.NOTE_NUMBER: self.note / 127.0,
            ModulationSource.VOLUME_CC: channel_state["controllers"].get(7, 100) / 127.0,
            ModulationSource.BALANCE: (channel_state["controllers"].get(8, 64) - 64) / 64.0,
            ModulationSource.PORTAMENTO_TIME_CC: channel_state["controllers"].get(5, 0) / 127.0
        }
        
        # Process modulation matrix
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)
        
        # Apply modulation to global pitch
        if ModulationDestination.PITCH in modulation_values:
            global_pitch_mod += modulation_values[ModulationDestination.PITCH]
            
        # Generate sample from partials
        left_sum = 0.0
        right_sum = 0.0
        active_partials = 0
        
        for partial in self.partials:
            if not partial.is_active():
                continue
                
            partial_samples = partial.generate_sample(
                lfos=self.lfos,
                global_pitch_mod=global_pitch_mod,
                velocity_crossfade=0.0,
                note_crossfade=0.0
            )
            
            left_sum += partial_samples[0]
            right_sum += partial_samples[1]
            active_partials += 1
            
        # Normalize by active partials
        if active_partials > 0:
            left_sum /= active_partials
            right_sum /= active_partials
            
        # Apply channel volume and expression
        volume = (channel_state["volume"] / 127.0) * (channel_state["expression"] / 127.0)
        left_out = left_sum * volume
        right_out = right_sum * volume
        
        return (left_out, right_out)

    def _setup_basic_generator(self):
        """Setup a basic sine wave generator when no wavetable is available"""
        # Create a simple sine wave partial
        basic_params = {
            "level": 1.0,
            "pan": 0.5,
            "key_range_low": 0,
            "key_range_high": 127,
            "velocity_range_low": 0,
            "velocity_range_high": 127,
            "key_scaling": 0.0,
            "velocity_sense": 1.0,
            "crossfade_velocity": False,
            "crossfade_note": False,
            "use_filter_env": True,
            "use_pitch_env": True,
            "amp_envelope": {
                "delay": 0.0,
                "attack": 0.01,
                "hold": 0.0,
                "decay": 0.3,
                "sustain": 0.7,
                "release": 0.5,
                "key_scaling": 0.0
            },
            "filter_envelope": {
                "delay": 0.0,
                "attack": 0.1,
                "hold": 0.0,
                "decay": 0.5,
                "sustain": 0.6,
                "release": 0.8,
                "key_scaling": 0.0
            },
            "pitch_envelope": {
                "delay": 0.0,
                "attack": 0.05,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.05
            },
            "filter": {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass"
            },
            "coarse_tune": 0,
            "fine_tune": 0
        }
        
        # For a basic generator, we'll add a simple sine wave partial
        # Note: This would normally use a wavetable, but we're creating a minimal implementation
        pass  # In a real implementation, this would create actual sound generation


class XGChannelRenderer:
    """
    Persistent per-channel renderer that handles all MIDI messages for a specific channel.
    Replaces the per-note XGToneGenerator approach with a more efficient per-channel approach.
    """
    
    # XG NRPN parameter mapping
    XG_NRPN_PARAMS = {
        # Amplitude Envelope Parameters
        (0, 1): {"target": "amp_envelope", "param": "attack", "transform": lambda x: x * 0.05},
        (0, 2): {"target": "amp_envelope", "param": "decay", "transform": lambda x: x * 0.05},
        (0, 3): {"target": "amp_envelope", "param": "release", "transform": lambda x: x * 0.05},
        (0, 4): {"target": "amp_envelope", "param": "sustain", "transform": lambda x: x / 127.0},
        (0, 40): {"target": "amp_envelope", "param": "velocity_sense", "transform": lambda x: 0.5 + x * 0.0078},  # 0.5-2.0
        (0, 41): {"target": "amp_envelope", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 42): {"target": "amp_envelope", "param": "hold", "transform": lambda x: x * 0.05},
        (0, 43): {"target": "amp_envelope", "param": "key_scaling", "transform": lambda x: (x - 64) / 64.0},
        
        # Filter Envelope Parameters
        (0, 5): {"target": "filter_envelope", "param": "attack", "transform": lambda x: x * 0.05},
        (0, 6): {"target": "filter_envelope", "param": "decay", "transform": lambda x: x * 0.05},
        (0, 7): {"target": "filter_envelope", "param": "release", "transform": lambda x: x * 0.05},
        (0, 8): {"target": "filter_envelope", "param": "sustain", "transform": lambda x: x / 127.0},
        (0, 9): {"target": "filter", "param": "key_follow", "transform": lambda x: x / 127.0},
        (0, 44): {"target": "filter_envelope", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 45): {"target": "filter_envelope", "param": "hold", "transform": lambda x: x * 0.05},
        (0, 46): {"target": "filter_envelope", "param": "key_scaling", "transform": lambda x: (x - 64) / 64.0},
        
        # Pitch Envelope Parameters
        (0, 10): {"target": "pitch_envelope", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 11): {"target": "pitch_envelope", "param": "attack", "transform": lambda x: x * 0.05},
        (0, 12): {"target": "pitch_envelope", "param": "hold", "transform": lambda x: x * 0.05},
        (0, 13): {"target": "pitch_envelope", "param": "decay", "transform": lambda x: x * 0.05},
        (0, 14): {"target": "pitch_envelope", "param": "sustain", "transform": lambda x: x / 127.0},
        (0, 15): {"target": "pitch_envelope", "param": "release", "transform": lambda x: x * 0.05},
        
        # Filter Parameters
        (0, 16): {"target": "filter", "param": "cutoff", "transform": lambda x: 20 + x * 150},
        (0, 17): {"target": "filter", "param": "resonance", "transform": lambda x: x / 64.0},
        (0, 18): {"target": "filter", "param": "type", "transform": lambda x: ["lowpass", "bandpass", "highpass"][min(x // 43, 2)]},
        
        # LFO 1 Parameters
        (0, 19): {"target": "lfo1", "param": "rate", "transform": lambda x: 0.1 + x * 0.2},
        (0, 20): {"target": "lfo1", "param": "depth", "transform": lambda x: x / 127.0},
        (0, 21): {"target": "lfo1", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 22): {"target": "lfo1", "param": "waveform", "transform": lambda x: ["sine", "triangle", "square", "sawtooth"][min(x // 32, 3)]},
        
        # LFO 2 Parameters
        (0, 23): {"target": "lfo2", "param": "rate", "transform": lambda x: 0.1 + x * 0.2},
        (0, 24): {"target": "lfo2", "param": "depth", "transform": lambda x: x / 127.0},
        (0, 25): {"target": "lfo2", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 26): {"target": "lfo2", "param": "waveform", "transform": lambda x: ["sine", "triangle", "square", "sawtooth"][min(x // 32, 3)]},
        
        # LFO 3 Parameters
        (0, 27): {"target": "lfo3", "param": "rate", "transform": lambda x: 0.1 + x * 0.2},
        (0, 28): {"target": "lfo3", "param": "depth", "transform": lambda x: x / 127.0},
        (0, 29): {"target": "lfo3", "param": "delay", "transform": lambda x: x * 0.05},
        (0, 30): {"target": "lfo3", "param": "waveform", "transform": lambda x: ["sine", "triangle", "square", "sawtooth"][min(x // 32, 3)]},
        
        # Pitch Parameters
        (0, 31): {"target": "pitch", "param": "lfo1_to_pitch", "transform": lambda x: x * 0.5},  # In cents
        (0, 32): {"target": "pitch", "param": "lfo2_to_pitch", "transform": lambda x: x * 0.5},  # In cents
        (0, 33): {"target": "pitch", "param": "lfo3_to_pitch", "transform": lambda x: x * 0.5},  # In cents
        (0, 34): {"target": "pitch", "param": "env_to_pitch", "transform": lambda x: x * 0.3},   # In cents
        (0, 35): {"target": "pitch", "param": "aftertouch_to_pitch", "transform": lambda x: x * 0.2},  # In cents
        
        # Vibrato Parameters
        (0, 33): {"target": "vibrato", "param": "rate", "transform": lambda x: 0.5 + x * 0.2},  # Hz
        (0, 34): {"target": "vibrato", "param": "depth", "transform": lambda x: x * 0.5},      # In cents
        (0, 35): {"target": "vibrato", "param": "delay", "transform": lambda x: x * 0.05},     # Seconds
        (0, 36): {"target": "vibrato", "param": "rise_time", "transform": lambda x: x * 0.05}, # Seconds
        
        # Tremolo Parameters
        (0, 40): {"target": "tremolo", "param": "rate", "transform": lambda x: 0.5 + x * 0.2},  # Hz
        (0, 41): {"target": "tremolo", "param": "depth", "transform": lambda x: x / 127.0},     # 0 to 1
        
        # Portamento Parameters
        (0, 50): {"target": "portamento", "param": "time", "transform": lambda x: x * 0.1},     # Seconds
        (0, 51): {"target": "portamento", "param": "mode", "transform": lambda x: x},           # 0=off, 1=on
        (0, 52): {"target": "portamento", "param": "control", "transform": lambda x: x / 127.0}, # Intensity
        
        # Note Shift Parameters
        (0, 53): {"target": "pitch", "param": "note_shift", "transform": lambda x: (x - 64) / 10.0},  # Semitones
        
        # Equalizer Parameters
        (0, 100): {"target": "equalizer", "param": "low_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 101): {"target": "equalizer", "param": "mid_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 102): {"target": "equalizer", "param": "high_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 103): {"target": "equalizer", "param": "mid_freq", "transform": lambda x: 100 + x * 40},  # Гц
        (0, 104): {"target": "equalizer", "param": "q_factor", "transform": lambda x: 0.5 + x * 0.04},  # Q-фактор
        
        # Stereo Parameters
        (0, 110): {"target": "stereo", "param": "width", "transform": lambda x: x / 127.0},  # Ширина стерео
        (0, 111): {"target": "stereo", "param": "chorus", "transform": lambda x: x / 127.0},  # Уровень хоруса
        
        # Partial Structure Parameters
        (0, 200): {"target": "partial", "param": "num_partials", "transform": lambda x: x + 1},  # Количество частичных структур
        (0, 201): {"target": "partial", "param": "level", "transform": lambda x: x / 127.0},  # Уровень частичной структуры
        (0, 202): {"target": "partial", "param": "pan", "transform": lambda x: x / 127.0},  # Панорамирование частичной структуры
        (0, 203): {"target": "partial", "param": "key_range_low", "transform": lambda x: x},  # Нижний предел диапазона
        (0, 204): {"target": "partial", "param": "key_range_high", "transform": lambda x: x},  # Верхний предел диапазона
        (0, 205): {"target": "partial", "param": "velocity_range_low", "transform": lambda x: x},  # Нижний предел velocity
        (0, 206): {"target": "partial", "param": "velocity_range_high", "transform": lambda x: x},  # Верхний предел velocity
        (0, 207): {"target": "partial", "param": "key_scaling", "transform": lambda x: (x - 64) / 64.0},  # Key scaling
        (0, 208): {"target": "partial", "param": "velocity_sense", "transform": lambda x: 0.5 + x * 0.0078},  # Чувствительность к velocity
        (0, 209): {"target": "partial", "param": "crossfade_velocity", "transform": lambda x: x > 64},  # Crossfade по velocity
        (0, 210): {"target": "partial", "param": "crossfade_note", "transform": lambda x: x > 64},  # Crossfade по ноте
        (0, 211): {"target": "partial", "param": "use_filter_env", "transform": lambda x: x > 64},  # Использовать фильтровую огибающую
        (0, 212): {"target": "partial", "param": "use_pitch_env", "transform": lambda x: x > 64},  # Использовать pitch огибающую
        
        # Drum Parameters
        (0, 250): {"target": "drum", "param": "note_map", "transform": lambda x: x},  # Выбор карты барабанов
        (0, 251): {"target": "drum", "param": "tune", "transform": lambda x: (x - 64) * 0.5},  # Настройка высоты
        (0, 252): {"target": "drum", "param": "level", "transform": lambda x: x / 127.0},  # Уровень
        (0, 253): {"target": "drum", "param": "pan", "transform": lambda x: (x - 64) / 64.0},  # Панорамирование
        (0, 254): {"target": "drum", "param": "solo", "transform": lambda x: x > 64},  # Solo режим
        (0, 255): {"target": "drum", "param": "mute", "transform": lambda x: x > 64},  # Mute режим
        
        # Global Parameters
        (0, 120): {"target": "global", "param": "volume", "transform": lambda x: x / 127.0},
        (0, 121): {"target": "global", "param": "expression", "transform": lambda x: x / 127.0},
        (0, 122): {"target": "global", "param": "pan", "transform": lambda x: (x - 64) / 64.0},
        
        # Modulation Matrix Parameters
        (0, 500): {"target": "mod_matrix", "param": "route_index", "transform": lambda x: x},
        (0, 501): {"target": "mod_matrix", "param": "source", "transform": lambda x: x},
        (0, 502): {"target": "mod_matrix", "param": "destination", "transform": lambda x: x},
        (0, 503): {"target": "mod_matrix", "param": "amount", "transform": lambda x: x / 127.0},
        (0, 504): {"target": "mod_matrix", "param": "polarity", "transform": lambda x: 1.0 if x < 64 else -1.0},
        (0, 505): {"target": "mod_matrix", "param": "velocity_sensitivity", "transform": lambda x: (x - 64) / 64.0},
        (0, 506): {"target": "mod_matrix", "param": "key_scaling", "transform": lambda x: (x - 64) / 64.0},
        
        # Extended XG Parameters
        # Filter Cutoff Modulation
        (0, 75): {"target": "filter", "param": "cutoff_mod", "transform": lambda x: (x - 64) / 64.0},
        # Decay Time Modulation
        (0, 76): {"target": "envelope", "param": "decay_mod", "transform": lambda x: (x - 64) / 64.0},
        # Celeste Detune
        (0, 94): {"target": "pitch", "param": "detune", "transform": lambda x: (x - 64) * 0.5},  # Cents
        # Phaser Depth
        (0, 95): {"target": "effect", "param": "phaser_depth", "transform": lambda x: x / 127.0},
        # General Purpose Buttons
        (0, 80): {"target": "button", "param": "gp_button_1", "transform": lambda x: x > 64},
        (0, 81): {"target": "button", "param": "gp_button_2", "transform": lambda x: x > 64},
        (0, 82): {"target": "button", "param": "gp_button_3", "transform": lambda x: x > 64},
        (0, 83): {"target": "button", "param": "gp_button_4", "transform": lambda x: x > 64},
        # Undefined/General Purpose Controllers
        (0, 85): {"target": "gp", "param": "gp_85", "transform": lambda x: x / 127.0},
        (0, 86): {"target": "gp", "param": "gp_86", "transform": lambda x: x / 127.0},
        (0, 87): {"target": "gp", "param": "gp_87", "transform": lambda x: x / 127.0},
        (0, 88): {"target": "gp", "param": "gp_88", "transform": lambda x: x / 127.0},
        (0, 89): {"target": "gp", "param": "gp_89", "transform": lambda x: x / 127.0},
        (0, 90): {"target": "gp", "param": "gp_90", "transform": lambda x: x / 127.0},
    }
    
    # XG RPN parameter mapping
    XG_RPN_PARAMS = {
        (0, 0): "pitch_bend_range",  # Pitch Bend Sensitivity
        (0, 2): "channel_coarse_tuning",
        (0, 3): "channel_fine_tuning",
        (0, 5): "vibrato_control",    # XG-specific
        (0, 120): "drum_mode",        # Drum Mode
    }
    
    # XG Controller mapping
    XG_CONTROLLERS = {
        1: "mod_wheel",          # Modulation Wheel
        2: "breath_controller",  # Breath Controller
        3: "undefined_3",        # Undefined
        4: "foot_controller",    # Foot Controller
        5: "portamento_time",    # Portamento Time
        6: "data_entry",         # Data Entry
        7: "volume",             # Volume
        8: "balance",            # Balance
        10: "pan",               # Pan
        11: "expression",        # Expression
        34: "vibrato_depth",     # Vibrato Depth
        35: "vibrato_rate",      # Vibrato Rate
        36: "vibrato_delay",     # Vibrato Delay
        64: "sustain_pedal",     # Sustain Pedal
        65: "portamento_switch", # Portamento Switch
        66: "sostenuto_pedal",   # Sostenuto Pedal
        67: "soft_pedal",        # Soft Pedal
        71: "harmonic_content",  # Harmonic Content
        74: "brightness",        # Brightness
        75: "filter_frequency",   # Filter Frequency (Cutoff)
        76: "decay_time",         # Decay Time
        77: "tremolo_depth",     # Tremolo Depth
        78: "tremolo_rate",      # Tremolo Rate
        80: "gp_button_1",       # General Purpose Button 1
        81: "gp_button_2",       # General Purpose Button 2
        82: "gp_button_3",       # General Purpose Button 3
        83: "gp_button_4",       # General Purpose Button 4
        84: "portamento_control", # Portamento Control
        85: "gp_85",             # Undefined/General Purpose
        86: "gp_86",             # Undefined/General Purpose
        87: "gp_87",             # Undefined/General Purpose
        88: "gp_88",             # Undefined/General Purpose
        89: "gp_89",             # Undefined/General Purpose
        90: "gp_90",             # Undefined/General Purpose
        91: "reverb_send",       # Reverb Send
        93: "chorus_send",       # Chorus Send
        94: "celeste_detune",    # Celeste Detune
        95: "phaser_depth",      # Phaser Depth
        120: "all_sound_off",    # All Sound Off
        121: "reset_all_controllers",  # Reset All Controllers
        123: "all_notes_off",    # All Notes Off
        126: "mono_mode",        # Mono Mode On
        127: "poly_mode",        # Poly Mode On
    }
    
    # Yamaha SysEx manufacturer ID
    YAMAHA_MANUFACTURER_ID = [0x43]
    
    # XG SysEx sub-status codes
    XG_SYSTEM_ON = 0x7E
    XG_PARAMETER_CHANGE = 0x04
    XG_BULK_PARAMETER_DUMP = 0x7F
    XG_BULK_PARAMETER_REQUEST = 0x7E
    
    # XG Bulk Data Types
    XG_BULK_PARTIAL = 0x00
    XG_BULK_PROGRAM = 0x01
    XG_BULK_DRUM_KIT = 0x02
    XG_BULK_SYSTEM = 0x03
    XG_BULK_ALL_PARAMETERS = 0x7F

    def __init__(self, channel: int, sample_rate: int = 44100, wavetable=None):
        """
        Initialize a persistent per-channel renderer.
        
        Args:
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate
            wavetable: Wavetable manager for sound generation
        """
        self.channel = channel
        self.sample_rate = sample_rate
        self.wavetable = wavetable
        self.active = True
        
        # Channel state
        self.program = 0
        self.bank = 0
        self.is_drum = False  # Default to melodic mode, can be changed via RPN 0,120
        
        # Active notes on this channel
        self.active_notes: Dict[int, ChannelNote] = OrderedDict()  # note -> ChannelNote
        
        # Controller state
        self.controllers = {
            1: 0,    # Modulation Wheel
            2: 0,    # Breath Controller
            3: 0,    # Undefined
            4: 0,    # Foot Controller
            5: 0,    # Portamento Time
            6: 100,  # Data Entry
            7: 100,  # Volume
            8: 64,   # Balance
            10: 64,  # Pan
            11: 127, # Expression
            34: 64,  # Vibrato Depth
            35: 64,  # Vibrato Rate
            36: 0,   # Vibrato Delay
            64: 0,   # Sustain Pedal
            65: 0,   # Portamento Switch
            66: 0,   # Sostenuto Pedal
            67: 0,   # Soft Pedal
            71: 64,  # Harmonic Content
            74: 64,  # Brightness
            75: 64,  # Filter Frequency (Cutoff)
            76: 64,  # Decay Time
            77: 0,   # Tremolo Depth
            78: 64,  # Tremolo Rate
            80: 0,   # General Purpose Button 1
            81: 0,   # General Purpose Button 2
            82: 0,   # General Purpose Button 3
            83: 0,   # General Purpose Button 4
            84: 0,   # Portamento Control
            85: 0,   # Undefined/General Purpose
            86: 0,   # Undefined/General Purpose
            87: 0,   # Undefined/General Purpose
            88: 0,   # Undefined/General Purpose
            89: 0,   # Undefined/General Purpose
            90: 0,   # Undefined/General Purpose
            91: 40,  # Reverb Send (XG default)
            93: 0,   # Chorus Send
            94: 0,   # Celeste Detune
            95: 0,   # Phaser Depth
            120: 0,  # All Sound Off
            121: 0,  # Reset All Controllers
            123: 0,  # All Notes Off
            126: 0,  # Mono Mode On
            127: 0,  # Poly Mode On
        }
        
        # Channel pressure (aftertouch)
        self.channel_pressure_value = 0
        
        # Key pressure (polyphonic aftertouch)
        self.key_pressure_values = {}  # note -> pressure
        
        # Pitch bend state
        self.pitch_bend_value = 8192  # Center value for 14-bit pitch bend
        self.pitch_bend_range = 2     # Default 2 semitones
        
        # RPN/NRPN state
        self.rpn_msb = 127
        self.rpn_lsb = 127
        self.nrpn_msb = 127
        self.nrpn_lsb = 127
        self.data_entry_msb = 0
        self.data_entry_lsb = 0
        
        # Channel parameters
        self.volume = 100
        self.expression = 127
        self.pan = 64
        self.balance = 64
        self.reverb_send = 40
        self.chorus_send = 0
        self.variation_send = 0
        
        # Initialize channel LFOs
        self.lfos = [
            LFO(id=0, waveform="sine", rate=5.0, depth=0.5, delay=0.0, sample_rate=sample_rate),
            LFO(id=1, waveform="triangle", rate=2.0, depth=0.3, delay=0.0, sample_rate=sample_rate),
            LFO(id=2, waveform="sawtooth", rate=0.5, depth=0.1, delay=0.5, sample_rate=sample_rate)
        ]
        
        # Initialize modulation matrix
        self.mod_matrix = ModulationMatrix(num_routes=16)
        self._setup_default_modulation_matrix()
        
        # Channel-specific parameters
        self.vibrato_rate = 5.0
        self.vibrato_depth = 50.0  # In cents
        self.vibrato_delay = 0.0
        self.tremolo_rate = 4.0
        self.tremolo_depth = 0.0
        self.portamento_time = 0.2  # 200ms default
        self.portamento_mode = 0    # Off by default
        self.stereo_width = 0.5     # Center
        self.chorus_level = 0.0     # No chorus by default
        self.mono_mode = False
        self.poly_mode = True
        
        # Drum parameters
        self.drum_parameters: Dict[int, Dict[str, Any]] = {}  # note -> parameters
        
    def _setup_default_modulation_matrix(self):
        """Setup default modulation matrix for the channel"""
        # Clear existing routes
        for i in range(16):
            self.mod_matrix.clear_route(i)
            
        # LFO1 -> Pitch
        self.mod_matrix.set_route(0, 
            ModulationSource.LFO1, 
            ModulationDestination.PITCH,
            amount=0.5,
            polarity=1.0
        )
        
        # LFO2 -> Pitch
        self.mod_matrix.set_route(1, 
            ModulationSource.LFO2, 
            ModulationDestination.PITCH,
            amount=0.3,
            polarity=1.0
        )
        
        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(2, 
            ModulationSource.LFO1, 
            ModulationDestination.FILTER_CUTOFF,
            amount=0.3,
            polarity=1.0
        )
        
        # Velocity -> Amp
        self.mod_matrix.set_route(3, 
            ModulationSource.VELOCITY, 
            ModulationDestination.AMP,
            amount=0.5,
            velocity_sensitivity=0.5
        )
        
    def get_channel_state(self) -> Dict[str, Any]:
        """Get the current channel state for note generation"""
        return {
            "program": self.program,
            "bank": self.bank,
            "volume": self.volume,
            "expression": self.expression,
            "pan": self.pan,
            "reverb_send": self.reverb_send,
            "chorus_send": self.chorus_send,
            "variation_send": self.variation_send,
            "controllers": self.controllers.copy(),
            "channel_pressure_value": self.channel_pressure_value,
            "key_pressure": self.key_pressure_values.copy(),
            "pitch_bend_value": self.pitch_bend_value,
            "pitch_bend_range": self.pitch_bend_range,
            "portamento_active": self.portamento_active,
        }
        
    def note_on(self, note: int, velocity: int):
        """Handle Note On message for this channel"""
        # If velocity is 0, treat as Note Off
        if velocity == 0:
            self.note_off(note, 0)
            return
            
        # Handle mono mode - only one note active at a time
        if self.mono_mode and self.active_notes:
            # Turn off all existing notes
            for existing_note in list(self.active_notes.keys()):
                self.active_notes[existing_note].note_off()
                del self.active_notes[existing_note]
            
        # Check if note is already playing
        if note in self.active_notes:
            # Note retrigger - note off then note on
            self.active_notes[note].note_off()
            del self.active_notes[note]
            
        # Handle portamento
        portamento_enabled = self.portamento_mode == 1 and self.previous_note is not None
        if portamento_enabled:
            # Calculate frequencies for portamento
            start_freq = 440.0 * (2 ** ((self.previous_note - 69) / 12.0)) # type: ignore
            target_freq = 440.0 * (2 ** ((note - 69) / 12.0))
            
            # Set up portamento parameters
            self.portamento_active = True
            self.portamento_target_freq = target_freq
            self.portamento_current_freq = start_freq
            self.portamento_step = (target_freq - start_freq) / (self.portamento_time * self.sample_rate)
        else:
            self.portamento_active = False
            self.portamento_target_freq = 0.0
            self.portamento_current_freq = 0.0
            self.portamento_step = 0.0
            
        # Create new note
        channel_note = ChannelNote(
            note=note,
            velocity=velocity,
            program=self.program,
            bank=self.bank,
            wavetable=self.wavetable,
            sample_rate=self.sample_rate,
            is_drum=self.is_drum
        )
        
        if channel_note.active:
            self.active_notes[note] = channel_note
            
        # Store this note as the previous note for potential portamento
        self.previous_note = note
            
    def note_off(self, note: int, velocity: int):
        """Handle Note Off message for this channel"""
        if note in self.active_notes:
            self.active_notes[note].note_off()
            # Note will be removed when it becomes inactive in generate_sample
            
    def control_change(self, controller: int, value: int):
        """Handle Control Change message for this channel"""
        self.controllers[controller] = value
        
        # Handle specific controllers
        if controller == 1:  # Modulation Wheel
            for lfo in self.lfos:
                lfo.set_mod_wheel(value)
        elif controller == 2:  # Breath Controller
            for lfo in self.lfos:
                lfo.set_breath_controller(value)
        elif controller == 4:  # Foot Controller
            for lfo in self.lfos:
                lfo.set_foot_controller(value)
        elif controller == 7:  # Volume
            self.volume = value
        elif controller == 8:  # Balance
            # Balance affects stereo positioning (similar to pan but different)
            self.balance = value
        elif controller == 10:  # Pan
            self.pan = value
        elif controller == 11:  # Expression
            self.expression = value
        elif controller == 64:  # Sustain Pedal
            sustain_on = value >= 64
            # Apply to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if sustain_on:
                        partial.amp_envelope.sustain_pedal_on()
                        if partial.filter_envelope:
                            partial.filter_envelope.sustain_pedal_on()
                    else:
                        partial.amp_envelope.sustain_pedal_off()
                        if partial.filter_envelope:
                            partial.filter_envelope.sustain_pedal_off()
        elif controller == 5:  # Portamento Time
            # Map 0-127 to portamento time (0-6.4 seconds)
            self.portamento_time = value * 0.05
        elif controller == 65:  # Portamento Switch
            self.portamento_mode = 1 if value >= 64 else 0
        elif controller == 66:  # Sostenuto Pedal
            sostenuto_on = value >= 64
            # Apply to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if sostenuto_on:
                        partial.amp_envelope.sostenuto_pedal_on()
                        if partial.filter_envelope:
                            partial.filter_envelope.sostenuto_pedal_on()
                    else:
                        partial.amp_envelope.sostenuto_pedal_off()
                        if partial.filter_envelope:
                            partial.filter_envelope.sostenuto_pedal_off()
        elif controller == 67:  # Soft Pedal
            soft_on = value >= 64
            # Apply to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if soft_on:
                        partial.amp_envelope.soft_pedal_on()
                        # Restart envelopes with soft pedal
                        if partial.amp_envelope.state != "idle":
                            partial.amp_envelope.note_on(note.velocity, note.note, soft_pedal=True)
                    else:
                        partial.amp_envelope.soft_pedal_off()
                        # Restart envelopes without soft pedal
                        if partial.amp_envelope.state != "idle":
                            partial.amp_envelope.note_on(note.velocity, note.note, soft_pedal=False)
        elif controller == 71:  # Harmonic Content
            # Apply to all LFOs and filters
            for lfo in self.lfos:
                lfo.set_harmonic_content(value)
            # Apply to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if partial.filter:
                        partial.filter.set_harmonic_content(value)
        elif controller == 74:  # Brightness
            # Apply to all LFOs and filters
            for lfo in self.lfos:
                lfo.set_brightness(value)
            # Apply to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if partial.filter:
                        partial.filter.set_brightness(value)
        elif controller == 75:  # Filter Frequency (Cutoff)
            # Apply filter cutoff modulation to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    if partial.filter:
                        # Map 0-127 to filter cutoff modulation range
                        cutoff_mod = (value - 64) / 64.0  # -1.0 to 1.0
                        partial.filter.set_parameters(modulated_cutoff=partial.filter.cutoff * (1.0 + cutoff_mod * 0.5))
        elif controller == 76:  # Decay Time
            # Apply decay time modulation to all active notes
            for note in self.active_notes.values():
                for partial in note.partials:
                    # Modulate amp envelope decay
                    decay_mod = (value - 64) / 64.0  # -1.0 to 1.0
                    partial.amp_envelope.update_parameters(modulated_decay=partial.amp_envelope.decay * (1.0 + decay_mod * 0.5))
                    # Modulate filter envelope decay if present
                    if partial.filter_envelope:
                        partial.filter_envelope.update_parameters(modulated_decay=partial.filter_envelope.decay * (1.0 + decay_mod * 0.5))
        elif controller == 80:  # General Purpose Button 1
            # Generic button, store state for custom use
            self.general_purpose_buttons = getattr(self, 'general_purpose_buttons', {})
            self.general_purpose_buttons[1] = value >= 64
        elif controller == 81:  # General Purpose Button 2
            self.general_purpose_buttons = getattr(self, 'general_purpose_buttons', {})
            self.general_purpose_buttons[2] = value >= 64
        elif controller == 82:  # General Purpose Button 3
            self.general_purpose_buttons = getattr(self, 'general_purpose_buttons', {})
            self.general_purpose_buttons[3] = value >= 64
        elif controller == 83:  # General Purpose Button 4
            self.general_purpose_buttons = getattr(self, 'general_purpose_buttons', {})
            self.general_purpose_buttons[4] = value >= 64
        elif controller == 91:  # Reverb Send
            self.reverb_send = value
        elif controller == 93:  # Chorus Send
            self.chorus_send = value
        elif controller == 94:  # Celeste Detune
            # Apply detune effect to all active notes
            detune_amount = (value - 64) / 64.0 * 50.0  # +/- 50 cents
            for note in self.active_notes.values():
                note.detune = detune_amount
        elif controller == 95:  # Phaser Depth
            # Apply phaser effect (simulated with filter modulation)
            phaser_depth = value / 127.0
            for note in self.active_notes.values():
                note.phaser_depth = phaser_depth
        elif controller == 120:  # All Sound Off
            # Immediately silence all notes
            for note in self.active_notes.values():
                note.active = False
            self.active_notes.clear()
        elif controller == 121:  # Reset All Controllers
            self._reset_controllers()
        elif controller == 123:  # All Notes Off
            # Release all notes
            for note in self.active_notes.values():
                note.note_off()
        elif controller == 126:  # Mono Mode On
            self.mono_mode = value > 0
            if self.mono_mode:
                # Turn off all but the latest note in mono mode
                if len(self.active_notes) > 1:
                    # Keep only the most recently played note
                    latest_note = list(self.active_notes.keys())[-1]
                    notes_to_release = [note for note in self.active_notes.keys() if note != latest_note]
                    for note in notes_to_release:
                        self.active_notes[note].note_off()
        elif controller == 127:  # Poly Mode On
            self.mono_mode = value == 0  # Poly mode is opposite of mono mode
                
        # Handle RPN/NRPN controllers
        if controller == 101:  # RPN MSB
            self.rpn_msb = value
            self.nrpn_msb = 127  # Reset NRPN
        elif controller == 100:  # RPN LSB
            self.rpn_lsb = value
            self.nrpn_lsb = 127  # Reset NRPN
        elif controller == 99:   # NRPN MSB
            self.nrpn_msb = value
            self.rpn_msb = 127   # Reset RPN
        elif controller == 98:   # NRPN LSB
            self.nrpn_lsb = value
            self.rpn_lsb = 127   # Reset RPN
        elif controller == 6:    # Data Entry MSB
            self.data_entry_msb = value
            self._handle_data_entry()
        elif controller == 38:   # Data Entry LSB
            self.data_entry_lsb = value
            self._handle_data_entry()
            
    def _reset_controllers(self):
        """Reset all controllers to default values"""
        self.controllers = {
            1: 0,    # Modulation Wheel
            2: 0,    # Breath Controller
            3: 0,    # Undefined
            4: 0,    # Foot Controller
            5: 0,    # Portamento Time
            6: 100,  # Data Entry
            7: 100,  # Volume
            8: 64,   # Balance
            10: 64,  # Pan
            11: 127, # Expression
            34: 64,  # Vibrato Depth
            35: 64,  # Vibrato Rate
            36: 0,   # Vibrato Delay
            64: 0,   # Sustain Pedal
            65: 0,   # Portamento Switch
            66: 0,   # Sostenuto Pedal
            67: 0,   # Soft Pedal
            71: 64,  # Harmonic Content
            74: 64,  # Brightness
            75: 64,  # Filter Frequency (Cutoff)
            76: 64,  # Decay Time
            77: 0,   # Tremolo Depth
            78: 64,  # Tremolo Rate
            80: 0,   # General Purpose Button 1
            81: 0,   # General Purpose Button 2
            82: 0,   # General Purpose Button 3
            83: 0,   # General Purpose Button 4
            84: 0,   # Portamento Control
            85: 0,   # Undefined/General Purpose
            86: 0,   # Undefined/General Purpose
            87: 0,   # Undefined/General Purpose
            88: 0,   # Undefined/General Purpose
            89: 0,   # Undefined/General Purpose
            90: 0,   # Undefined/General Purpose
            91: 40,  # Reverb Send (XG default)
            93: 0,   # Chorus Send
            94: 0,   # Celeste Detune
            95: 0,   # Phaser Depth
            120: 0,  # All Sound Off
            121: 0,  # Reset All Controllers
            123: 0,  # All Notes Off
            126: 0,  # Mono Mode On
            127: 0,  # Poly Mode On
        }
        
        # Reset LFOs
        for lfo in self.lfos:
            lfo.set_mod_wheel(0)
            lfo.set_breath_controller(0)
            lfo.set_foot_controller(0)
            lfo.set_brightness(64)
            lfo.set_harmonic_content(64)
            
        # Reset channel parameters
        self.volume = 100
        self.expression = 127
        self.pan = 64
        self.balance = 64
        self.vibrato_depth = 50.0
        self.vibrato_rate = 5.0
        self.vibrato_delay = 0.0
        self.tremolo_depth = 0.0
        self.tremolo_rate = 4.0
        self.portamento_control = 1.0
        self.portamento_time = 0.2
        self.portamento_mode = 0
        self.mono_mode = False
        self.general_purpose_buttons = {}
        
        # Reset filters on all active notes
        for note in self.active_notes.values():
            for partial in note.partials:
                if partial.filter:
                    partial.filter.set_brightness(64)
                    partial.filter.set_harmonic_content(64)
                    
        # Reset key pressure
        self.key_pressure_values.clear()
                    
    def _handle_data_entry(self):
        """Handle Data Entry for RPN/NRPN"""
        # Check if RPN is set
        if self.rpn_msb != 127 and self.rpn_lsb != 127:
            # Handle RPN
            self._handle_rpn(self.rpn_msb, self.rpn_lsb, self.data_entry_msb, self.data_entry_lsb)
        elif self.nrpn_msb != 127 and self.nrpn_lsb != 127:
            # Handle NRPN
            self._handle_nrpn(self.nrpn_msb, self.nrpn_lsb, self.data_entry_msb, self.data_entry_lsb)
            
    def _handle_rpn(self, rpn_msb: int, rpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle Registered Parameter Number"""
        rpn = (rpn_msb, rpn_lsb)
        if rpn not in self.XG_RPN_PARAMS:
            return
            
        param_name = self.XG_RPN_PARAMS[rpn]
        
        if param_name == "pitch_bend_range":
            semitones = data_msb
            cents = data_lsb
            self.pitch_bend_range = semitones + cents / 100.0
        elif param_name == "channel_coarse_tuning":
            self.coarse_tuning = data_msb - 64  # Value from -64 to 63
        elif param_name == "channel_fine_tuning":
            self.fine_tuning = (data_msb - 64) * 100 / 127.0  # Value from -50 to 50 cents
        elif param_name == "vibrato_control":
            # XG-specific vibrato control
            self.vibrato_depth = data_msb * 0.78
            self.vibrato_rate = 0.5 + data_lsb * 0.15
        elif param_name == "drum_mode":
            # Switch drum mode
            self.is_drum = (data_msb > 0)
            
    def _handle_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int):
        """Handle Non-Registered Parameter Number"""
        nrpn = (nrpn_msb, nrpn_lsb)
        if nrpn not in self.XG_NRPN_PARAMS:
            return
            
        param_info = self.XG_NRPN_PARAMS[nrpn]
        data = (data_msb << 7) | data_lsb  # 14-bit value
        real_value = param_info["transform"](data)
        
        # Handle different parameter targets
        if param_info["target"] == "mod_matrix":
            self._handle_modulation_matrix_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "partial":
            # Handle partial structure parameters
            self._handle_partial_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "drum":
            # Handle drum parameters
            self._handle_drum_nrpn(param_info["param"], real_value)
        elif param_info["target"].startswith("lfo"):
            # Handle LFO parameters
            lfo_index = int(param_info["target"][3]) - 1
            if 0 <= lfo_index < len(self.lfos):
                lfo = self.lfos[lfo_index]
                if param_info["param"] == "rate":
                    lfo.set_parameters(rate=real_value)
                elif param_info["param"] == "depth":
                    lfo.set_parameters(depth=real_value)
                elif param_info["param"] == "delay":
                    lfo.set_parameters(delay=real_value)
                elif param_info["param"] == "waveform":
                    lfo.set_parameters(waveform=real_value)
        elif param_info["target"] == "filter":
            # Handle filter parameters
            self._handle_filter_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "envelope":
            # Handle envelope parameters
            self._handle_envelope_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "pitch":
            # Handle pitch parameters
            self._handle_pitch_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "effect":
            # Handle effect parameters
            self._handle_effect_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "button":
            # Handle button parameters
            self._handle_button_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "gp":
            # Handle general purpose parameters
            self._handle_gp_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "equalizer":
            # Handle equalizer parameters
            self._handle_equalizer_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "effect":
            # Handle effect parameters
            self._handle_effect_nrpn(param_info["param"], real_value)
        elif param_info["target"] == "stereo":
            # Handle stereo parameters
            self._handle_stereo_nrpn(param_info["param"], real_value)
                    
    def _handle_modulation_matrix_nrpn(self, param: str, value: float):
        """Handle NRPN for modulation matrix"""
        # For channel renderer, we track the current route index
        if not hasattr(self, 'current_mod_matrix_route'):
            self.current_mod_matrix_route = 0
            
        if param == "route_index":
            self.current_mod_matrix_route = int(value) % 16
            return
            
        # Get current route
        route = self.mod_matrix.routes[self.current_mod_matrix_route]
        if route is None:
            # Create new route with default values
            route = ModulationRoute(
                source=ModulationSource.VELOCITY,
                destination=ModulationDestination.AMP,
                amount=0.0,
                polarity=1.0,
                velocity_sensitivity=0.0,
                key_scaling=0.0
            )
            
        # Update route parameter
        if param == "source":
            sources = ModulationSource.get_all_sources()
            source_index = int(value) % len(sources)
            route.source = sources[source_index]
        elif param == "destination":
            destinations = ModulationDestination.get_all_destinations()
            dest_index = int(value) % len(destinations)
            route.destination = destinations[dest_index]
        elif param == "amount":
            route.amount = value
        elif param == "polarity":
            route.polarity = 1.0 if value >= 0.5 else -1.0
        elif param == "velocity_sensitivity":
            route.velocity_sensitivity = value
        elif param == "key_scaling":
            route.key_scaling = value
            
        # Save updated route
        self.mod_matrix.set_route(self.current_mod_matrix_route, 
                                route.source, route.destination,
                                route.amount, route.polarity,
                                route.velocity_sensitivity, route.key_scaling)
                                
        # If route affects LFO, restart LFO
        if "lfo" in route.destination:
            lfo_index = int(route.destination[3]) - 1
            if 0 <= lfo_index < len(self.lfos):
                self.lfos[lfo_index].phase = 0.0
                self.lfos[lfo_index].delay_counter = 0
                
    def _handle_drum_nrpn(self, param: str, value: Union[float, List[float]]):
        """Handle NRPN for drum parameters"""
        # For drum parameters, we need a current note reference
        # This would typically be set by the synthesizer when handling drum setup
        if not hasattr(self, 'current_drum_note'):
            return
            
        note = self.current_drum_note
        
        if note not in self.drum_parameters:
            self.drum_parameters[note] = {}
            
        if param == "tune":
            self.drum_parameters[note]["tune"] = value
        elif param == "level":
            self.drum_parameters[note]["level"] = value
        elif param == "pan":
            self.drum_parameters[note]["pan"] = value
        elif param == "solo":
            self.drum_parameters[note]["solo"] = value
        elif param == "mute":
            self.drum_parameters[note]["mute"] = value
        elif param == "reverb_send":
            self.drum_parameters[note]["reverb_send"] = value
        elif param == "chorus_send":
            self.drum_parameters[note]["chorus_send"] = value
        elif param == "variation_send":
            self.drum_parameters[note]["variation_send"] = value
        elif param == "filter_cutoff":
            self.drum_parameters[note]["filter_cutoff"] = value
        elif param == "filter_resonance":
            self.drum_parameters[note]["filter_resonance"] = value
        elif param == "eg_attack":
            self.drum_parameters[note]["eg_attack"] = value
        elif param == "eg_decay":
            self.drum_parameters[note]["eg_decay"] = value
        elif param == "eg_release":
            self.drum_parameters[note]["eg_release"] = value
        elif param == "pitch_coarse":
            self.drum_parameters[note]["pitch_coarse"] = value
        elif param == "pitch_fine":
            self.drum_parameters[note]["pitch_fine"] = value
        elif param == "level_hold":
            self.drum_parameters[note]["level_hold"] = value
        elif param == "variation_effect":
            self.drum_parameters[note]["variation_effect"] = value
        elif param == "variation_params":
            # Ensure value is a list for variation parameters
            if isinstance(value, (int, float)):
                # Single value - treat as first parameter
                if "variation_params" not in self.drum_parameters[note]:
                    self.drum_parameters[note]["variation_params"] = [0.5] * 10
                self.drum_parameters[note]["variation_params"][0] = float(value)
            elif isinstance(value, (list, tuple)):
                # List of values - update all parameters
                if "variation_params" not in self.drum_parameters[note]:
                    self.drum_parameters[note]["variation_params"] = [0.5] * 10
                # Update variation parameters (10 parameters)
                for i in range(min(10, len(value))):
                    self.drum_parameters[note]["variation_params"][i] = float(value[i])
        elif param == "key_assign":
            self.drum_parameters[note]["key_assign"] = value
        elif param == "low_pass_filter":
            self.drum_parameters[note]["low_pass_filter"] = value
        elif param == "lfo_rate":
            self.drum_parameters[note]["lfo_rate"] = value
        elif param == "lfo_depth":
            self.drum_parameters[note]["lfo_depth"] = value
        elif param == "lfo_delay":
            self.drum_parameters[note]["lfo_delay"] = value
        elif param == "eq_bass_gain":
            self.drum_parameters[note]["eq_bass_gain"] = value
        elif param == "eq_treble_gain":
            self.drum_parameters[note]["eq_treble_gain"] = value
        elif param == "send_reverb":
            self.drum_parameters[note]["send_reverb"] = value
        elif param == "send_chorus":
            self.drum_parameters[note]["send_chorus"] = value
        elif param == "send_delay":
            self.drum_parameters[note]["send_delay"] = value
            
    def _handle_partial_nrpn(self, param: str, value: float):
        """Handle NRPN for partial structure parameters"""
        # For partial parameters, we update all active notes with the new parameter
        # This affects the sound parameters for all currently playing notes
        for note in self.active_notes.values():
            for partial in note.partials:
                # Update partial parameters based on the NRPN parameter
                if param == "level":
                    partial.level = value
                elif param == "pan":
                    partial.pan = value
                elif param == "key_range_low":
                    partial.key_range_low = int(value)
                elif param == "key_range_high":
                    partial.key_range_high = int(value)
                elif param == "velocity_range_low":
                    partial.velocity_range_low = int(value)
                elif param == "velocity_range_high":
                    partial.velocity_range_high = int(value)
                elif param == "key_scaling":
                    partial.key_scaling = value
                elif param == "velocity_sense":
                    partial.velocity_sense = value
                elif param == "crossfade_velocity":
                    partial.crossfade_velocity = bool(value > 0.5)
                elif param == "crossfade_note":
                    partial.crossfade_note = bool(value > 0.5)
                elif param == "use_filter_env":
                    # This would affect whether the filter envelope is used
                    pass  # Would need to enable/disable filter envelope
                elif param == "use_pitch_env":
                    # This would affect whether the pitch envelope is used
                    pass  # Would need to enable/disable pitch envelope
                elif param == "coarse_tune":
                    # Update coarse tuning for all partials
                    if hasattr(partial, 'coarse_tune'):
                        partial.coarse_tune = int(value)
                elif param == "fine_tune":
                    # Update fine tuning for all partials
                    if hasattr(partial, 'fine_tune'):
                        partial.fine_tune = int(value)
                # Additional partial parameters could be handled here
        
    def _handle_filter_nrpn(self, param: str, value: float):
        """Handle NRPN for filter parameters"""
        # Apply filter parameter to all active notes
        for note in self.active_notes.values():
            for partial in note.partials:
                if partial.filter:
                    if param == "cutoff":
                        partial.filter.set_parameters(cutoff=value)
                    elif param == "resonance":
                        partial.filter.set_parameters(resonance=value)
                    elif param == "type":
                        partial.filter.set_parameters(filter_type=value)
                    elif param == "key_follow":
                        partial.filter.set_parameters(key_follow=value)
                        
    def _handle_envelope_nrpn(self, param: str, value: float):
        """Handle NRPN for envelope parameters"""
        # Apply envelope parameter to all active notes
        for note in self.active_notes.values():
            for partial in note.partials:
                # Amp envelope
                if param.startswith("amp_"):
                    env_param = param[4:]  # Remove "amp_" prefix
                    if env_param == "attack":
                        partial.amp_envelope.update_parameters(attack=value)
                    elif env_param == "decay":
                        partial.amp_envelope.update_parameters(decay=value)
                    elif env_param == "release":
                        partial.amp_envelope.update_parameters(release=value)
                    elif env_param == "sustain":
                        partial.amp_envelope.update_parameters(sustain=value)
                    elif env_param == "delay":
                        partial.amp_envelope.update_parameters(delay=value)
                    elif env_param == "hold":
                        partial.amp_envelope.update_parameters(hold=value)
                        
                # Filter envelope
                if partial.filter_envelope and param.startswith("filter_"):
                    env_param = param[7:]  # Remove "filter_" prefix
                    if env_param == "attack":
                        partial.filter_envelope.update_parameters(attack=value)
                    elif env_param == "decay":
                        partial.filter_envelope.update_parameters(decay=value)
                    elif env_param == "release":
                        partial.filter_envelope.update_parameters(release=value)
                    elif env_param == "sustain":
                        partial.filter_envelope.update_parameters(sustain=value)
                    elif env_param == "delay":
                        partial.filter_envelope.update_parameters(delay=value)
                    elif env_param == "hold":
                        partial.filter_envelope.update_parameters(hold=value)
                        
    def _handle_pitch_nrpn(self, param: str, value: float):
        """Handle NRPN for pitch parameters"""
        # Apply pitch parameter to all active notes
        for note in self.active_notes.values():
            for partial in note.partials:
                if param == "note_shift":
                    # Apply note shift
                    pass  # Would be applied at note generation time
                elif param == "detune":
                    # Apply detune in cents
                    if hasattr(note, 'detune'):
                        note.detune = value
                        
    def _handle_button_nrpn(self, param: str, value: float):
        """Handle NRPN for button parameters"""
        # Store button state
        button_num = int(param.split("_")[-1])  # Extract button number
        if not hasattr(self, 'general_purpose_buttons'):
            self.general_purpose_buttons = {}
        self.general_purpose_buttons[button_num] = value > 0.5
        
    def _handle_gp_nrpn(self, param: str, value: float):
        """Handle NRPN for general purpose parameters"""
        # Store general purpose parameter
        gp_num = int(param.split("_")[-1])  # Extract GP number
        if not hasattr(self, 'general_purpose_params'):
            self.general_purpose_params = {}
        self.general_purpose_params[gp_num] = value
            
    def program_change(self, program: int):
        """Handle Program Change message for this channel"""
        self.program = program
        # In a real implementation, we would update all active notes with new parameters
        # For now, we'll just update the channel program
        
        # Update any channel-specific parameters based on the new program
        # This might include updating LFO rates, filter settings, etc.
        # depending on the program's characteristics
        
        # If there's a wavetable manager, we might want to preload the new program
        if self.wavetable:
            try:
                # Preload program data to reduce latency
                self.wavetable.preload_program(program, self.bank)
            except Exception as e:
                # Silently ignore preload errors to maintain performance
                pass
        
    def channel_pressure(self, pressure: int):
        """Handle Channel Pressure (Aftertouch) message"""
        self.channel_pressure_value = pressure
        # Apply to all LFOs
        for lfo in self.lfos:
            lfo.set_channel_aftertouch(pressure)
        # Apply to all active notes
        for note in self.active_notes.values():
            for partial in note.partials:
                if partial.filter:
                    partial.filter.set_aftertouch_mod(pressure / 127.0)
                    
    def pitch_bend(self, lsb: int, msb: int):
        """Handle Pitch Bend message"""
        # 14-bit pitch bend value
        self.pitch_bend_value = (msb << 7) | lsb
        
    def key_pressure(self, note: int, pressure: int):
        """Handle Key Pressure (Polyphonic Aftertouch) message"""
        # Store key pressure for this note
        self.key_pressure_values[note] = pressure
        
        # Apply to LFOs for this specific note if it's active
        if note in self.active_notes:
            channel_note = self.active_notes[note]
            for lfo in channel_note.lfos:
                lfo.set_key_aftertouch(pressure)
                
            # Apply to filters for this note
            for partial in channel_note.partials:
                if partial.filter:
                    partial.filter.set_aftertouch_mod(pressure / 127.0)
        
    def sysex(self, manufacturer_id: List[int], data: List[int]):
        """Handle System Exclusive message"""
        # Check if this is Yamaha SysEx
        if manufacturer_id != self.YAMAHA_MANUFACTURER_ID:
            return
            
        # Handle XG-specific SysEx messages
        if len(data) < 3:
            return
            
        device_id = data[0]
        sub_status = data[1]
        command = data[2]
        
        # XG System On
        if sub_status == self.XG_SYSTEM_ON and command == 0x00:
            self._handle_xg_system_on(data[3:])
        # XG Parameter Change
        elif sub_status == self.XG_PARAMETER_CHANGE:
            self._handle_xg_parameter_change(data[3:])
        # XG Bulk Parameter Dump
        elif sub_status == self.XG_BULK_PARAMETER_DUMP:
            self._handle_xg_bulk_parameter_dump(data[3:])
        # XG Bulk Parameter Request
        elif sub_status == self.XG_BULK_PARAMETER_REQUEST:
            self._handle_xg_bulk_parameter_request(data[3:])
        # XG Master Volume
        elif sub_status == 0x05:
            self._handle_xg_master_volume(data[3:])
        # XG Master Transpose
        elif sub_status == 0x06:
            self._handle_xg_master_transpose(data[3:])
        # XG Master Tune
        elif sub_status == 0x07:
            self._handle_xg_master_tune(data[3:])
        # XG Effect Parameters
        elif sub_status == 0x08:
            self._handle_xg_effect_parameters(data[3:])
        # XG Display Text
        elif sub_status == 0x09:
            self._handle_xg_display_text(data[3:])
            
    def _handle_xg_parameter_change(self, data: List[int]):
        """Handle XG Parameter Change message"""
        if len(data) < 3:
            return
            
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value = data[2]
        
        # Handle as NRPN
        self._handle_nrpn(parameter_msb, parameter_lsb, value, 0)
        
    def _handle_xg_bulk_parameter_dump(self, data: List[int]):
        """Handle XG Bulk Parameter Dump message"""
        if len(data) < 2:
            return
            
        bank = data[0]
        data_type = data[1]
        
        # Handle based on data type
        if data_type == self.XG_BULK_SYSTEM:
            self._handle_bulk_system(data[2:])
        elif data_type == self.XG_BULK_PROGRAM:
            self._handle_bulk_program(data[2:])
        elif data_type == self.XG_BULK_DRUM_KIT:
            self._handle_bulk_drum_kit(data[2:])
        elif data_type == self.XG_BULK_PARTIAL:
            self._handle_bulk_partial(data[2:])
        elif data_type == self.XG_BULK_ALL_PARAMETERS:
            self._handle_bulk_all_parameters(data[2:])
        # Other bulk data types are handled by the existing handlers or not implemented
        # XG_BULK_PARTIAL is already handled above
            
    def _handle_xg_bulk_parameter_request(self, data: List[int]):
        """Handle XG Bulk Parameter Request message"""
        if len(data) < 2:
            return
            
        bank = data[0]
        data_type = data[1]
        
        # In a real implementation, this would send a response with requested parameters
        # For now, we'll just log the request
        print(f"XG Bulk Parameter Request: Bank {bank}, Type {data_type}")
        
    def _handle_xg_master_volume(self, data: List[int]):
        """Handle XG Master Volume message"""
        if len(data) < 2:
            return
            
        # Extract 14-bit value
        volume = (data[0] << 7) | data[1]
        # Convert to 0.0-1.0 range
        master_volume = volume / 16383.0
        # Store for use in audio generation (would be used by parent synthesizer)
        self.master_volume = master_volume
        
    def _handle_xg_master_transpose(self, data: List[int]):
        """Handle XG Master Transpose message"""
        if len(data) < 1:
            return
            
        transpose = data[0] - 64  # Value from -64 to 63 semitones
        self.master_transpose = transpose
        
    def _handle_xg_master_tune(self, data: List[int]):
        """Handle XG Master Tune message"""
        if len(data) < 2:
            return
            
        # Extract 14-bit value (cent values from -100 to 100)
        tune = (data[0] << 7) | data[1]
        cents = (tune - 8192) * 100 / 8192.0  # Convert to cents
        self.master_tune = cents
        
    def _handle_xg_effect_parameters(self, data: List[int]):
        """Handle XG Effect Parameters message"""
        if len(data) < 3:
            return
            
        effect_type = data[0]
        parameter = data[1]
        # Extract 14-bit value
        value = (data[2] << 7) | data[3] if len(data) >= 4 else data[2]
        
        # Handle effect parameters
        if effect_type == 0:  # Reverb
            self._handle_reverb_parameters(parameter, value)
        elif effect_type == 1:  # Chorus
            self._handle_chorus_parameters(parameter, value)
        elif effect_type == 2:  # Variation
            self._handle_variation_parameters(parameter, value)
        elif effect_type == 3:  # Insertion
            self._handle_insertion_parameters(parameter, value)
            
    def _handle_reverb_parameters(self, parameter: int, value: int):
        """Handle Reverb Effect Parameters"""
        if parameter == 0:  # Reverb Type
            self.reverb_type = value
        elif parameter == 1:  # Reverb Parameter 1
            self.reverb_param1 = value / 127.0
        elif parameter == 2:  # Reverb Parameter 2
            self.reverb_param2 = value / 127.0
        elif parameter == 3:  # Reverb Parameter 3
            self.reverb_param3 = value / 127.0
        elif parameter == 4:  # Reverb Parameter 4
            self.reverb_param4 = value / 127.0
        elif parameter == 5:  # Reverb Return
            self.reverb_return = value / 127.0
        elif parameter == 6:  # Reverb Pan
            self.reverb_pan = (value - 64) / 64.0
            
    def _handle_chorus_parameters(self, parameter: int, value: int):
        """Handle Chorus Effect Parameters"""
        if parameter == 0:  # Chorus Type
            self.chorus_type = value
        elif parameter == 1:  # Chorus Parameter 1
            self.chorus_param1 = value / 127.0
        elif parameter == 2:  # Chorus Parameter 2
            self.chorus_param2 = value / 127.0
        elif parameter == 3:  # Chorus Parameter 3
            self.chorus_param3 = value / 127.0
        elif parameter == 4:  # Chorus Parameter 4
            self.chorus_param4 = value / 127.0
        elif parameter == 5:  # Chorus Return
            self.chorus_return = value / 127.0
        elif parameter == 6:  # Chorus Pan
            self.chorus_pan = (value - 64) / 64.0
        elif parameter == 7:  # Chorus Send Level
            self.chorus_send = value
            
    def _handle_variation_parameters(self, parameter: int, value: int):
        """Handle Variation Effect Parameters"""
        if parameter == 0:  # Variation Type
            self.variation_type = value
        elif parameter == 1:  # Variation Parameter 1
            self.variation_param1 = value / 127.0
        elif parameter == 2:  # Variation Parameter 2
            self.variation_param2 = value / 127.0
        elif parameter == 3:  # Variation Parameter 3
            self.variation_param3 = value / 127.0
        elif parameter == 4:  # Variation Parameter 4
            self.variation_param4 = value / 127.0
        elif parameter == 5:  # Variation Return
            self.variation_return = value / 127.0
        elif parameter == 6:  # Variation Pan
            self.variation_pan = (value - 64) / 64.0
        elif parameter == 7:  # Variation Send Level
            self.variation_send = value
            
    def _handle_insertion_parameters(self, parameter: int, value: int):
        """Handle Insertion Effect Parameters"""
        if parameter == 0:  # Insertion Type
            self.insertion_type = value
        elif parameter == 1:  # Insertion Parameter 1
            self.insertion_param1 = value / 127.0
        elif parameter == 2:  # Insertion Parameter 2
            self.insertion_param2 = value / 127.0
        elif parameter == 3:  # Insertion Parameter 3
            self.insertion_param3 = value / 127.0
        elif parameter == 4:  # Insertion Parameter 4
            self.insertion_param4 = value / 127.0
        elif parameter == 5:  # Insertion Return
            self.insertion_return = value / 127.0
        elif parameter == 6:  # Insertion Pan
            self.insertion_pan = (value - 64) / 64.0
            
    def _handle_xg_display_text(self, data: List[int]):
        """Handle XG Display Text message"""
        # Convert data to ASCII text (typically used for displaying song titles, etc.)
        try:
            text = bytes(data).decode('ascii')
            self.display_text = text
            print(f"XG Display Text: {text}")
        except UnicodeDecodeError:
            # Handle non-ASCII text
            self.display_text = "".join(chr(b) if 32 <= b <= 126 else '?' for b in data)
            print(f"XG Display Text (non-ASCII): {self.display_text}")
            
    def _handle_bulk_drum_kit(self, data: List[int]):
        """Handle bulk drum kit parameters"""
        if len(data) < 3:
            return
            
        drum_note = data[0]
        parameter = data[1]
        # Extract 14-bit value
        value = (data[2] << 7) | data[3] if len(data) >= 4 else data[2]
        
        # Handle drum kit parameters
        if drum_note not in self.drum_parameters:
            self.drum_parameters[drum_note] = {}
            
        if parameter == 0:  # Drum Note Map
            self.drum_parameters[drum_note]["note_map"] = value
        elif parameter == 1:  # Drum Tune
            self.drum_parameters[drum_note]["tune"] = (value - 8192) / 100.0
        elif parameter == 2:  # Drum Level
            self.drum_parameters[drum_note]["level"] = value / 127.0
        elif parameter == 3:  # Drum Pan
            self.drum_parameters[drum_note]["pan"] = (value - 64) / 64.0
        elif parameter == 4:  # Drum Reverb Send
            self.drum_parameters[drum_note]["reverb_send"] = value / 127.0
        elif parameter == 5:  # Drum Chorus Send
            self.drum_parameters[drum_note]["chorus_send"] = value / 127.0
        elif parameter == 6:  # Drum Variation Send
            self.drum_parameters[drum_note]["variation_send"] = value / 127.0
        elif parameter == 7:  # Drum Filter Cutoff
            self.drum_parameters[drum_note]["filter_cutoff"] = 20 + value * 150
        elif parameter == 8:  # Drum Filter Resonance
            self.drum_parameters[drum_note]["filter_resonance"] = value / 64.0
        elif parameter == 9:  # Drum EG Attack
            self.drum_parameters[drum_note]["eg_attack"] = value * 0.05
        elif parameter == 10:  # Drum EG Decay
            self.drum_parameters[drum_note]["eg_decay"] = value * 0.05
        elif parameter == 11:  # Drum EG Release
            self.drum_parameters[drum_note]["eg_release"] = value * 0.05
        elif parameter == 12:  # Drum Pitch Coarse
            self.drum_parameters[drum_note]["pitch_coarse"] = (value - 64) / 10.0
        elif parameter == 13:  # Drum Pitch Fine
            self.drum_parameters[drum_note]["pitch_fine"] = (value - 64) * 0.5
        elif parameter == 14:  # Drum Level Hold
            self.drum_parameters[drum_note]["level_hold"] = value > 64
        elif parameter == 15:  # Drum Variation Effect
            self.drum_parameters[drum_note]["variation_effect"] = value
        elif parameter >= 16 and parameter <= 25:  # Drum Variation Parameters (10 params)
            var_param_index = parameter - 16
            if "variation_params" not in self.drum_parameters[drum_note]:
                self.drum_parameters[drum_note]["variation_params"] = [0.5] * 10
            if var_param_index < 10:
                self.drum_parameters[drum_note]["variation_params"][var_param_index] = value / 127.0
            
    def _handle_xg_system_on(self, data: List[int]):
        """Handle XG System On message"""
        # Reset channel to XG defaults
        self.pitch_bend_range = 2
        self.coarse_tuning = 0
        self.fine_tuning = 0
        self.vibrato_rate = 5.0
        self.vibrato_depth = 50.0
        self.vibrato_delay = 0.0
        self.tremolo_depth = 0.0
        self.portamento_time = 0.2
        self.portamento_mode = 1
        self.stereo_width = 0.5
        self.chorus_level = 0.0
        self.is_drum = False
        
        # Reset portamento state
        self.portamento_active = False
        self.portamento_target_freq = 0.0
        self.portamento_current_freq = 0.0
        self.portamento_step = 0.0
        self.previous_note = None
        
        # Reset LFOs
        for lfo in self.lfos:
            lfo.phase = 0.0
            lfo.delay_counter = 0
            
        # Reset modulation matrix
        self._setup_default_modulation_matrix()
        
            
    def _handle_bulk_system(self, data: List[int]):
        """Handle bulk system parameters"""
        if len(data) < 2:
            return
            
        parameter = data[0]
        # Extract 14-bit value
        value = (data[1] << 7) | data[2] if len(data) >= 3 else data[1]
        
        # Handle system parameters
        if parameter == 0:  # Pitch Bend Range
            self.pitch_bend_range = value / 100.0
        elif parameter == 1:  # Channel Coarse Tuning
            self.coarse_tuning = value - 8192
        elif parameter == 2:  # Channel Fine Tuning
            self.fine_tuning = (value - 8192) * 100 / 16383.0
        elif parameter == 3:  # Stereo Width
            self.stereo_width = value / 16383.0
        elif parameter == 4:  # Chorus Level
            self.chorus_level = value / 16383.0
        elif parameter == 5:  # Reverb Level
            self.reverb_send = value / 127.0
        elif parameter == 6:  # Master Volume
            self.master_volume = value / 16383.0
        elif parameter == 7:  # Master Transpose
            self.master_transpose = value - 8192
        elif parameter == 8:  # Master Tune
            self.master_tune = (value - 8192) * 100 / 16383.0
            
    def _handle_bulk_program(self, data: List[int]):
        """Handle bulk program parameters"""
        if len(data) < 2:
            return
            
        parameter = data[0]
        # Extract 14-bit value
        value = (data[1] << 7) | data[2] if len(data) >= 3 else data[1]
        
        # Handle program parameters
        # These would typically affect the sound parameters for the current program
        # In a real implementation, we would update all active notes with new parameters
        if not hasattr(self, 'bulk_program_params'):
            self.bulk_program_params = {}
        self.bulk_program_params[parameter] = value
        
    def _handle_bulk_partial(self, data: List[int]):
        """Handle bulk partial structure parameters"""
        if len(data) < 3:
            return
            
        partial_id = data[0]
        parameter = data[1]
        # Extract 14-bit value
        value = (data[2] << 7) | data[3] if len(data) >= 4 else data[2]
        
        # Handle partial structure parameters
        # These would typically affect the sound parameters for specific partials
        # In a real implementation, we would update all active notes with new parameters
        if not hasattr(self, 'bulk_partial_params'):
            self.bulk_partial_params = {}
        if partial_id not in self.bulk_partial_params:
            self.bulk_partial_params[partial_id] = {}
        self.bulk_partial_params[partial_id][parameter] = value
        
    def _handle_bulk_all_parameters(self, data: List[int]):
        """Handle bulk all parameters dump"""
        if len(data) < 2:
            return
            
        parameter_group = data[0]
        parameter = data[1]
        # Extract 14-bit value
        value = (data[2] << 7) | data[3] if len(data) >= 4 else data[2]
        
        # Handle all parameters based on group
        if parameter_group == 0:  # System parameters
            self._handle_bulk_system([parameter] + [value >> 7, value & 0x7F])
        elif parameter_group == 1:  # Program parameters
            self._handle_bulk_program([parameter] + [value >> 7, value & 0x7F])
        elif parameter_group == 2:  # Drum kit parameters
            # Need drum note for drum parameters
            if hasattr(self, 'current_drum_note'):
                drum_note = self.current_drum_note
                self._handle_bulk_drum_kit([drum_note, parameter] + [value >> 7, value & 0x7F])
        elif parameter_group == 3:  # Partial structure parameters
            # Need partial ID for partial parameters
            if hasattr(self, 'current_partial_id'):
                partial_id = self.current_partial_id # type: ignore
                self._handle_bulk_partial([partial_id, parameter] + [value >> 7, value & 0x7F])
        
    def set_drum_instrument_parameters(self, note: int, parameters: Dict[str, Any]):
        """Set drum instrument parameters"""
        self.drum_parameters[note] = parameters.copy()
        
    def get_drum_instrument_parameters(self, note: int) -> Dict[str, Any]:
        """Get drum instrument parameters"""
        return self.drum_parameters.get(note, {}).copy()
        
    def set_current_drum_note(self, note: int):
        """Set current drum note for parameter setup"""
        self.current_drum_note = note
        
    def all_notes_off(self):
        """Turn off all active notes"""
        for note in self.active_notes.values():
            note.note_off()
            
    def all_sound_off(self):
        """Immediately silence all notes"""
        for note in self.active_notes.values():
            note.active = False
        self.active_notes.clear()
        
    def is_active(self) -> bool:
        """Check if this channel renderer has any active notes"""
        # Clean up inactive notes
        inactive_notes = [note for note, channel_note in self.active_notes.items() 
                         if not channel_note.is_active()]
        for note in inactive_notes:
            del self.active_notes[note]
            
        return len(self.active_notes) > 0
        
    def generate_sample(self) -> Tuple[float, float]:
        """
        Generate one stereo sample for this channel.
        
        Returns:
            Tuple of (left_sample, right_sample) in range [-1.0, 1.0]
        """
        # Clean up inactive notes
        inactive_notes = [note for note, channel_note in self.active_notes.items() 
                         if not channel_note.is_active()]
        for note in inactive_notes:
            del self.active_notes[note]
            
        # If no active notes, return silence
        if not self.active_notes:
            return (0.0, 0.0)
            
        # Get current channel state
        channel_state = self.get_channel_state()
        
        # Calculate pitch bend modulation
        pitch_bend_range_cents = self.pitch_bend_range * 100
        pitch_bend_offset = ((self.pitch_bend_value - 8192) / 8192.0) * pitch_bend_range_cents
        global_pitch_mod = pitch_bend_offset
        
        # Update portamento if active
        if self.portamento_active and self.portamento_step != 0:
            self.portamento_current_freq += self.portamento_step
            # Check if we've reached the target
            if (self.portamento_step > 0 and self.portamento_current_freq >= self.portamento_target_freq) or \
               (self.portamento_step < 0 and self.portamento_current_freq <= self.portamento_target_freq):
                self.portamento_current_freq = self.portamento_target_freq
                self.portamento_active = False
                self.portamento_step = 0.0
        
        # Generate samples from all active notes
        left_sum = 0.0
        right_sum = 0.0
        
        for note in self.active_notes.values():
            left, right = note.generate_sample(channel_state, global_pitch_mod)
            left_sum += left
            right_sum += right
            
        # Apply channel volume and expression
        channel_volume = (self.volume / 127.0) * (self.expression / 127.0)
        left_out = left_sum * channel_volume
        right_out = right_sum * channel_volume
        
        # Apply panning and balance
        # Panning: -1.0 (left) to 1.0 (right)
        pan = (self.pan - 64) / 64.0
        # Balance: -1.0 (left) to 1.0 (right) 
        balance = (self.balance - 64) / 64.0
        
        # Combine pan and balance effects
        combined_pan = pan + balance * 0.5  # Balance has half the effect of pan
        combined_pan = max(-1.0, min(1.0, combined_pan))  # Clamp to valid range
        
        if combined_pan != 0.0:
            # Simple linear panning
            left_gain = 0.5 * (1.0 - combined_pan)
            right_gain = 0.5 * (1.0 + combined_pan)
            left_out *= left_gain
            right_out *= right_gain
            
        # Clamp to valid range
        left_out = max(-1.0, min(1.0, left_out))
        right_out = max(-1.0, min(1.0, right_out))
        
        return (left_out, right_out)

    def _handle_equalizer_nrpn(self, param: str, value: float):
        """Handle NRPN for equalizer parameters"""
        # Handle EQ parameters for the channel
        if not hasattr(self, 'equalizer_params'):
            self.equalizer_params = {
                'low_gain': 0.0,
                'mid_gain': 0.0,
                'high_gain': 0.0,
                'mid_freq': 1000.0,
                'q_factor': 1.0
            }
        
        if param == "low_gain":
            self.equalizer_params['low_gain'] = (value - 64) * 0.2  # dB range
        elif param == "mid_gain":
            self.equalizer_params['mid_gain'] = (value - 64) * 0.2  # dB range
        elif param == "high_gain":
            self.equalizer_params['high_gain'] = (value - 64) * 0.2  # dB range
        elif param == "mid_freq":
            self.equalizer_params['mid_freq'] = 100 + value * 40  # Hz range
        elif param == "q_factor":
            self.equalizer_params['q_factor'] = 0.5 + value * 0.04  # Q factor range

    def _handle_effect_nrpn(self, param: str, value: float):
        """Handle NRPN for effect parameters"""
        # Handle effect parameters (reverb, chorus, etc.)
        if param == "reverb_send":
            self.reverb_send = value
        elif param == "chorus_send":
            self.chorus_send = value
        elif param == "variation_send":
            self.variation_send = value
        elif param == "delay_time":
            if not hasattr(self, 'effect_params'):
                self.effect_params = {}
            self.effect_params['delay_time'] = value * 0.1  # ms range
        elif param == "feedback":
            if not hasattr(self, 'effect_params'):
                self.effect_params = {}
            self.effect_params['feedback'] = value / 127.0

    def _handle_stereo_nrpn(self, param: str, value: float):
        """Handle NRPN for stereo parameters"""
        # Handle stereo parameters
        if param == "width":
            self.stereo_width = value / 127.0
        elif param == "center":
            if not hasattr(self, 'stereo_params'):
                self.stereo_params = {}
            self.stereo_params['center'] = (value - 64) / 64.0  # -1 to 1 range
        elif param == "spread":
            if not hasattr(self, 'stereo_params'):
                self.stereo_params = {}
            self.stereo_params['spread'] = value / 127.0