import math
import numpy as np
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
        self._recalculate_increments()
        
        # Поддержка модуляции параметров
        self.modulated_delay = delay
        self.modulated_attack = attack
        self.modulated_hold = hold
        self.modulated_decay = decay
        self.modulated_sustain = sustain
        self.modulated_release = release
    
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
            modulated_decay=self.decay,
            modulated_release=self.release
        )
    
    def all_notes_off(self):
        """Сброс всех нот (как при All Notes Off контроллере)"""
        self.hold_notes = True
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
        
        # Поддержка модуляции параметров
        self.modulated_rate = rate
        self.modulated_depth = depth
        
        # Параметры фильтра для контроллеров дыхания и педали
        self.filter_params = {
            'base_cutoff': 1000.0,
            'base_resonance': 0.7,
            'base_depth': 0.5,
            'base_harmonic': 0.3
        }
        
        self._update_phase_step()
    
    def __update_phase_step(self):
        """Обновление скорости изменения фазы"""
        # Модулированная скорость
        effective_rate = self.modulated_rate
        
        # Модуляция скорости от различных источников
        effective_rate *= (
            1 + self.mod_wheel * 0.5 +
            self.channel_aftertouch * 0.3 +
            self.key_aftertouch * 0.3 +
            self.brightness_mod * 0.2
        )
        self.phase_step = max(0.1, effective_rate) * 2 * math.pi / self.sample_rate
    
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
        
        # Обновление параметров фильтра, которые управляются контроллером дыхания
        if hasattr(self, 'filter_params'):
            # Модуляция частоты среза фильтра в зависимости от дыхания
            breath_mod = 1.0 + self.breath_controller * 0.5
            self.filter_params['cutoff'] = self.filter_params['base_cutoff'] * breath_mod
            
            # Модуляция резонанса фильтра в зависимости от дыхания
            resonance_mod = 1.0 + self.breath_controller * 0.3
            self.filter_params['resonance'] = self.filter_params['base_resonance'] * resonance_mod
            
            # Обновление коэффициентов фильтра
            self._update_filter_coefficients()
        
    def set_foot_controller(self, value):
        """
        Установка значения контроллера педали (0-127)
        
        Args:
            value: значение контроллера педали (0-127)
        """
        self.foot_controller = value / 127.0
        self._update_phase_step()
        
        # Обновление параметров фильтра, которые управляются контроллером педали
        if hasattr(self, 'filter_params'):
            # Модуляция глубины LFO в зависимости от педали
            depth_mod = 1.0 + self.foot_controller * 0.5
            self.filter_params['depth'] = self.filter_params['base_depth'] * depth_mod
            
            # Модуляция гармонического содержания в зависимости от педали
            harmonic_mod = 1.0 + self.foot_controller * 0.7
            self.filter_params['harmonic_content'] = self.filter_params['base_harmonic'] * harmonic_mod
            
            # Обновление коэффициентов фильтра
            self._update_filter_coefficients()

    def _update_filter_coefficients(self):
        """Обновление коэффициентов фильтра на основе текущих параметров"""
        if not hasattr(self, 'filter_params'):
            return
        
        # Получаем текущие параметры фильтра
        base_cutoff = self.filter_params['base_cutoff']
        base_resonance = self.filter_params['base_resonance']
        
        # Применение модуляции от контроллеров
        effective_cutoff = base_cutoff * (1 + self.brightness_mod * 0.5)
        effective_resonance = base_resonance * (1 + self.harmonic_content_mod * 0.3)
        
        # Расчет коэффициентов для фильтра низких частот
        w0 = 2 * math.pi * min(effective_cutoff, self.sample_rate/2) / self.sample_rate
        alpha = math.sin(w0) / (2 * max(0.001, effective_resonance))
        cos_omega = math.cos(w0)
        
        # Коэффициенты для фильтра низких частот
        b0_low = (1 - cos_omega) / 2
        b1_low = 1 - cos_omega
        b2_low = (1 - cos_omega) / 2
        a0_low = 1 + alpha
        a1_low = -2 * cos_omega
        a2_low = 1 - alpha
        
        # Коэффициенты для фильтра высоких частот
        b0_high = (1 + cos_omega) / 2
        b1_high = -(1 + cos_omega)
        b2_high = (1 + cos_omega) / 2
        a0_high = 1 + alpha
        a1_high = -2 * cos_omega
        a2_high = 1 - alpha
        
        # Коэффициенты для полосового фильтра
        b0_band = alpha
        b1_band = 0
        b2_band = -alpha
        a0_band = 1 + alpha
        a1_band = -2 * cos_omega
        a2_band = 1 - alpha
        
        # Сохранение коэффициентов для последующего использования
        self.filter_coefficients = {
            'lowpass': {
                'b0': b0_low / a0_low,
                'b1': b1_low / a0_low,
                'b2': b2_low / a0_low,
                'a1': a1_low / a0_low,
                'a2': a2_low / a0_low
            },
            'highpass': {
                'b0': b0_high / a0_high,
                'b1': b1_high / a0_high,
                'b2': b2_high / a0_high,
                'a1': a1_high / a0_high,
                'a2': a2_high / a0_high
            },
            'bandpass': {
                'b0': b0_band / a0_band,
                'b1': b1_band / a0_band,
                'b2': b2_band / a0_band,
                'a1': a1_band / a0_band,
                'a2': a2_band / a0_band
            }
        }
    
    def _update_phase_step(self):
        """Обновление скорости изменения фазы с учетом модуляции"""
        # Модулированная скорость
        effective_rate = self.modulated_rate
        
        # Модуляция скорости от различных источников
        effective_rate *= (
            1 + self.mod_wheel * 0.5 +
            self.channel_aftertouch * 0.3 +
            self.key_aftertouch * 0.3 +
            self.brightness_mod * 0.2 +
            self.harmonic_content_mod * 0.2 +
            self.breath_controller * 0.4 +
            self.foot_controller * 0.3
        )
        
        # Расчет шага фазы с учетом модулированной скорости
        self.phase_step = max(0.1, effective_rate) * 2 * math.pi / self.sample_rate

    
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
    
    def step(self):
        """Генерация следующего значения LFO с учетом задержки и модуляции"""
        # Обработка задержки
        if self.delay_counter < self.delay_samples:
            self.delay_counter += 1
            return 0.0
        
        # Обновление фазы с учетом модулированной скорости
        self.phase = (self.phase + self.phase_step * self.modulated_rate) % (2 * math.pi)
        
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
    PITCH = "pitch"
    FILTER_CUTOFF = "filter_cutoff"
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
        
        # Коэффициенты для левого и правого каналов
        self.b0_l, self.b1_l, self.b2_l, self.a1_l, self.a2_l = self._calculate_coefficients(0)
        self.b0_r, self.b1_r, self.b2_r, self.a1_r, self.a2_r = self._calculate_coefficients(1)
        
        # Буферы для левого канала
        self.x_l = [0.0, 0.0]
        self.y_l = [0.0, 0.0]
        
        # Буферы для правого канала
        self.x_r = [0.0, 0.0]
        self.y_r = [0.0, 0.0]
        
        self.brightness_mod = 0.0
        self.harmonic_content_mod = 0.0
        
        # Поддержка модуляции stereo width
        self.modulated_stereo_width = stereo_width
    
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
        
        # Проверка, попадает ли нота в диапазон частичной структуры
        if not (self.key_range_low <= note <= self.key_range_high):
            self.active = False
            return
            
        # Проверка, попадает ли velocity в диапазон частичной структуры
        if not (self.velocity_range_low <= velocity <= self.velocity_range_high):
            self.active = False
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
            
        # Базовая частота для текущей ноты
        base_freq = 440.0 * (2 ** ((self.note - 69) / 12.0))
        
        # Учет key scaling (зависимость pitch от высоты ноты)
        pitch_factor = 2 ** ((self.note - 60) * self.key_scaling / 1200.0)
        final_freq = base_freq * pitch_factor
        
        table_length = len(table)
        self.phase_step = final_freq / self.sample_rate * table_length
    
    def is_active(self):
        """Проверка, активен ли частичный генератор"""
        return self.active and self.amp_envelope.state != "idle"
    
    def note_off(self):
        """Обработка события Note Off"""
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
        amp_env = self.amp_envelope.process()
        if amp_env <= 0:
            self.active = False
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
            self.active = False
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
        
        # Применение уровня частичной структуры с учетом кросс-фейда
        effective_level = self.level
        
        # Учет кросс-фейда по velocity
        if self.crossfade_velocity:
            effective_level *= (1.0 - self.velocity_crossfade)
        
        # Учет кросс-фейда по ноте
        if self.crossfade_note:
            effective_level *= (1.0 - self.note_crossfade)
        
        if is_stereo:
            left_out = filtered_sample[0] * amp_env * effective_level
            right_out = filtered_sample[1] * amp_env * effective_level
        else:
            mono_sample = filtered_sample * amp_env * effective_level # type: ignore
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

class XGToneGenerator:
    """
    Тон-генератор в соответствии со стандартом MIDI XG с полной поддержкой
    множественных LFO, матрицы модуляции, Partial Structure и барабанов.
    """
    
    # Сопоставление NRPN параметров XG
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
        (0, 31): {"target": "pitch", "param": "lfo1_to_pitch", "transform": lambda x: x * 0.5},  # В центах
        (0, 32): {"target": "pitch", "param": "lfo2_to_pitch", "transform": lambda x: x * 0.5},  # В центах
        (0, 33): {"target": "pitch", "param": "lfo3_to_pitch", "transform": lambda x: x * 0.5},  # В центах
        (0, 34): {"target": "pitch", "param": "env_to_pitch", "transform": lambda x: x * 0.3},   # В центах
        (0, 35): {"target": "pitch", "param": "aftertouch_to_pitch", "transform": lambda x: x * 0.2},  # В центах
        
        # Vibrato Parameters
        (0, 33): {"target": "vibrato", "param": "rate", "transform": lambda x: 0.5 + x * 0.2},  # Hz
        (0, 34): {"target": "vibrato", "param": "depth", "transform": lambda x: x * 0.5},      # В центах
        (0, 35): {"target": "vibrato", "param": "delay", "transform": lambda x: x * 0.05},     # Секунды
        (0, 36): {"target": "vibrato", "param": "rise_time", "transform": lambda x: x * 0.05}, # Секунды
        
        # Tremolo Parameters
        (0, 40): {"target": "tremolo", "param": "rate", "transform": lambda x: 0.5 + x * 0.2},  # Hz
        (0, 41): {"target": "tremolo", "param": "depth", "transform": lambda x: x / 127.0},     # От 0 до 1
        
        # Portamento Parameters
        (0, 50): {"target": "portamento", "param": "time", "transform": lambda x: x * 0.1},     # Секунды
        (0, 51): {"target": "portamento", "param": "mode", "transform": lambda x: x},           # 0=off, 1=on
        (0, 52): {"target": "portamento", "param": "control", "transform": lambda x: x / 127.0}, # Интенсивность
        
        # Note Shift Parameters
        (0, 53): {"target": "pitch", "param": "note_shift", "transform": lambda x: (x - 64) / 10.0},  # Полутоны
        
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
    }
    
    # Сопоставление RPN параметров
    XG_RPN_PARAMS = {
        (0, 0): "pitch_bend_range",  # Pitch Bend Sensitivity
        (0, 2): "channel_coarse_tuning",
        (0, 3): "channel_fine_tuning",
        (0, 5): "vibrato_control",    # Специфично для XG
        (0, 120): "drum_mode",        # Drum Mode
    }
    
    # Контроллеры, специфичные для XG
    XG_CONTROLLERS = {
        1: "mod_wheel",          # Modulation Wheel
        2: "breath_controller",  # Breath Controller
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
        77: "tremolo_depth",     # Tremolo Depth
        78: "tremolo_rate",      # Tremolo Rate
        84: "portamento_control", # Portamento Control
        120: "all_sound_off",    # All Sound Off
        121: "reset_all_controllers",  # Reset All Controllers
        123: "all_notes_off",    # All Notes Off
        126: "mono_mode",        # Mono Mode On
        127: "poly_mode",        # Poly Mode On
    }
    
    # SysEx Manufacturer ID для Yamaha
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

    def __init__(self, wavetable, note, velocity, program, channel=0, sample_rate=44100,
                 portamento=False, previous_note=None, portamento_time=None,
                 same_note_key_on_assign=True, note_shift=0.0, is_drum=False,
                 modulation_matrix=None, bank=0):
        """
        Инициализация XG тон-генератора с поддержкой множественных LFO,
        матрицы модуляции, Partial Structure и барабанов.
        
        Args:
            wavetable: объект, предоставляющий доступ к wavetable сэмплам
            note: MIDI нота (0-127)
            velocity: громкость ноты (0-127)
            program: номер программы (патча)
            channel: MIDI-канал (для обработки channel-specific сообщений)
            sample_rate: частота дискретизации
            portamento: включен ли portamento
            previous_note: предыдущая нота для portamento
            portamento_time: время portamento в секундах
            same_note_key_on_assign: режим SAME NOTE NUMBER KEY ON ASSIGN
            note_shift: сдвиг ноты в полутонах
            is_drum: работает ли в режиме барабана
            modulation_matrix: матрица модуляции для инициализации
            bank: номер банка (0-16383)
        """
        self.wavetable = wavetable
        self.note = note
        self.velocity = velocity
        self.program = program
        self.bank = bank
        self.channel = channel
        self.sample_rate = sample_rate
        self.active = True
        self.same_note_key_on_assign = same_note_key_on_assign  # Режим SAME NOTE NUMBER KEY ON ASSIGN
        self.note_shift = note_shift  # Сдвиг ноты в полутонах
        self.is_drum = is_drum  # Режим барабана
        
        # Состояние контроллеров
        self.controllers = {
            1: 0,    # Modulation Wheel
            2: 0,    # Breath Controller
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
            77: 0,   # Tremolo Depth
            78: 64,  # Tremolo Rate
            84: 0,   # Portamento Control
            120: 0,  # All Sound Off
            121: 0,  # Reset All Controllers
            123: 0,  # All Notes Off
            126: 0,  # Mono Mode On
            127: 0,  # Poly Mode On
        }
        self.channel_pressure = 0
        self.key_pressure = {note: 0}  # Послеудар для каждой ноты
        
        # Параметры по умолчанию в соответствии с XG стандартом
        self.pitch_bend_range = 2  # по умолчанию 2 полутона
        self.pitch_bend_value = 8192  # центральное значение для 14-битного pitch bend
        self.detune = 0  # смещение в центах
        self.scale_tuning = [0] * 12  # настройка для каждого полутона
        self.coarse_tuning = 0  # грубая настройка в октавах
        self.fine_tuning = 0    # точная настройка в центах
        
        # Параметры барабанов
        self.drum_tune = 0.0  # Настройка высоты барабана
        self.drum_level = 1.0  # Уровень барабана
        self.drum_pan = 0.5  # Панорамирование барабана
        self.drum_solo = False  # Solo режим барабана
        self.drum_mute = False  # Mute режим барабана
        self.drum_note_map = DrumNoteMap()  # Карта барабанов
        
        # Параметры vibrato
        self.vibrato_rate = 5.0
        self.vibrato_depth = 50.0  # в центах
        self.vibrato_delay = 0.0
        self.vibrato_rise_time = 0.0
        
        # Параметры tremolo
        self.tremolo_rate = 4.0
        self.tremolo_depth = 0.0
        
        # Параметры portamento
        self.portamento_enabled = portamento
        self.portamento_time = portamento_time or 0.2  # по умолчанию 200ms
        self.portamento_control = 1.0
        self.portamento_mode = 1  # 1 = on, 0 = off
        
        # Параметры стерео
        self.stereo_width = 0.5  # 0.0 (моно) до 1.0 (полное стерео)
        self.chorus_level = 0.0  # Уровень хоруса
        
        # Инициализация текущей и целевой частоты для portamento
        if portamento and previous_note is not None:
            self.start_freq = self._note_to_freq(previous_note)
            self.target_freq = self._note_to_freq(note)
            self.current_freq = self.start_freq
            self.portamento_active = True
            self.portamento_step = (self.target_freq - self.start_freq) / (self.portamento_time * sample_rate)
        else:
            self.current_freq = self._note_to_freq(note)
            self.portamento_active = False
        
        # Получение параметров из wavetable
        self.params = self._get_parameters(program)
        
        # Инициализация множественных LFO (до 3)
        self.lfos = [
            LFO(id=0, waveform=self.params["lfo1"]["waveform"],
                rate=self.params["lfo1"]["rate"],
                depth=self.params["lfo1"]["depth"],
                delay=self.params["lfo1"]["delay"],
                sample_rate=sample_rate),
            LFO(id=1, waveform=self.params["lfo2"]["waveform"],
                rate=self.params["lfo2"]["rate"],
                depth=self.params["lfo2"]["depth"],
                delay=self.params["lfo2"]["delay"],
                sample_rate=sample_rate),
            LFO(id=2, waveform=self.params["lfo3"]["waveform"],
                rate=self.params["lfo3"]["rate"],
                depth=self.params["lfo3"]["depth"],
                delay=self.params["lfo3"]["delay"],
                sample_rate=sample_rate)
        ]
        
        # Инициализация матрицы модуляции
        self.mod_matrix = ModulationMatrix(num_routes=16)
        
        # Если предоставлена матрица модуляции из SoundFont, используем её
        if modulation_matrix is not None:
            self._setup_modulation_matrix_from_sf2(modulation_matrix)
        else:
            self._setup_default_modulation_matrix()
        
        # Инициализация частичных структур
        self.partials = []
        self._setup_partials(wavetable)
        
        # Если нет активных частичных структур, генератор неактивен
        if not any(partial.is_active() for partial in self.partials):
            self.active = False
    
    def _note_to_freq(self, note):
        """Преобразование MIDI ноты в частоту с учетом настройки"""
        base_note = note + self.note_shift
        
        # Для барабанов применяем drum_tune
        if self.is_drum:
            base_note += self.drum_tune
        
        # Учет coarseTune и fineTune из SoundFont
        if hasattr(self, 'coarse_tune') and hasattr(self, 'fine_tune'):
            base_note += self.coarse_tune + self.fine_tune / 100.0
        
        return 440.0 * (2 ** ((base_note - 69) / 12.0))
    
    def _get_parameters(self, program):
        """Получение параметров для конкретной программы"""
        # Получение параметров из wavetable, если они доступны
        if hasattr(self.wavetable, "get_program_parameters"):
            params = self.wavetable.get_program_parameters(program, self.bank)
            if params:
                return params
        
        # Параметры по умолчанию (соответствуют XG спецификации)
        base_params = {
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
                "lfo1_to_pitch": 50.0,    # в центах
                "lfo2_to_pitch": 30.0,    # в центах
                "lfo3_to_pitch": 10.0,    # в центах
                "env_to_pitch": 30.0,     # в центах
                "aftertouch_to_pitch": 20.0,  # в центах
                "lfo_to_filter": 0.3,
                "env_to_filter": 0.5,
                "aftertouch_to_filter": 0.2,
                "tremolo_depth": 0.3,
                "vibrato_depth": 50.0,    # в центах
                "vibrato_rate": 5.0,
                "vibrato_delay": 0.0
            }
        }
        
        # Для барабанов используем специальные параметры
        if self.is_drum:
            # Проверяем, является ли нота барабаном
            if self.drum_note_map.is_drum_note(self.note):
                # Получаем специфические параметры для этого барабана
                drum_params = self.wavetable.get_drum_parameters(self.note, self.program, self.bank)
                if drum_params:
                    return drum_params
            
            # Параметры по умолчанию для барабанов
            return {
                **base_params,
                "partials": [
                    {
                        "level": 1.0,
                        "pan": 0.5,
                        "key_range_low": self.note,
                        "key_range_high": self.note,
                        "velocity_range_low": 0,
                        "velocity_range_high": 127,
                        "key_scaling": 0.0,
                        "velocity_sense": 1.0,
                        "crossfade_velocity": False,
                        "crossfade_note": False,
                        "use_filter_env": False,
                        "use_pitch_env": False,
                        "amp_envelope": {
                            "delay": 0.0,
                            "attack": 0.001,
                            "hold": 0.0,
                            "decay": 0.1,
                            "sustain": 0.0,
                            "release": 0.001,
                            "key_scaling": 0.0
                        },
                        "filter_envelope": {
                            "delay": 0.0,
                            "attack": 0.01,
                            "hold": 0.0,
                            "decay": 0.3,
                            "sustain": 0.5,
                            "release": 0.1,
                            "key_scaling": 0.0
                        },
                        "pitch_envelope": {
                            "delay": 0.0,
                            "attack": 0.001,
                            "hold": 0.0,
                            "decay": 0.05,
                            "sustain": 0.0,
                            "release": 0.001
                        },
                        "filter": {
                            "cutoff": 1500.0,
                            "resonance": 0.5,
                            "type": "lowpass"
                        },
                        "coarse_tune": 0,
                        "fine_tune": 0
                    }
                ]
            }
        
        # Параметры по умолчанию для мелодических инструментов
        return {
            **base_params,
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
                    "fine_tune": 0
                }
            ]
        }
    
    def _setup_modulation_matrix_from_sf2(self, sf2_modulation_matrix):
        """Инициализация матрицы модуляции на основе данных из SoundFont"""
        # Очищаем текущую матрицу
        for i in range(16):
            self.mod_matrix.clear_route(i)
        
        # Добавляем маршруты из SoundFont
        for i, route in enumerate(sf2_modulation_matrix[:16]):  # Ограничиваем 16 маршрутами
            self.mod_matrix.set_route(
                index=i,
                source=route["source"],
                destination=route["destination"],
                amount=route["amount"],
                polarity=route["polarity"],
                velocity_sensitivity=route.get("velocity_sensitivity", 0.0),
                key_scaling=route.get("key_scaling", 0.0)
            )
    
    def _setup_default_modulation_matrix(self):
        """Настройка матрицы модуляции по умолчанию"""
        # LFO1 -> Pitch
        self.mod_matrix.set_route(0, 
            ModulationSource.LFO1, 
            ModulationDestination.PITCH,
            amount=self.params["modulation"]["lfo1_to_pitch"] / 100.0,
            polarity=1.0
        )
        
        # LFO2 -> Pitch
        self.mod_matrix.set_route(1, 
            ModulationSource.LFO2, 
            ModulationDestination.PITCH,
            amount=self.params["modulation"]["lfo2_to_pitch"] / 100.0,
            polarity=1.0
        )
        
        # LFO3 -> Pitch
        self.mod_matrix.set_route(2, 
            ModulationSource.LFO3, 
            ModulationDestination.PITCH,
            amount=self.params["modulation"]["lfo3_to_pitch"] / 100.0,
            polarity=1.0
        )
        
        # Amp Envelope -> Filter Cutoff
        self.mod_matrix.set_route(3, 
            ModulationSource.AMP_ENV, 
            ModulationDestination.FILTER_CUTOFF,
            amount=self.params["modulation"]["env_to_filter"],
            polarity=1.0
        )
        
        # LFO1 -> Filter Cutoff
        self.mod_matrix.set_route(4, 
            ModulationSource.LFO1, 
            ModulationDestination.FILTER_CUTOFF,
            amount=self.params["modulation"]["lfo_to_filter"],
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
            amount=self.params["modulation"]["vibrato_depth"] / 100.0,
            polarity=1.0
        )
        
        # Tremolo Depth
        self.mod_matrix.set_route(8, 
            ModulationSource.TREMOLO_DEPTH, 
            ModulationDestination.AMP,
            amount=self.params["modulation"]["tremolo_depth"],
            polarity=1.0
        )
    
    def _setup_partials(self, wavetable):
        """Настройка частичных структур на основе параметров"""
        partials_params = self.params.get("partials", [])
        
        # Создаем частичные генераторы для каждой частичной структуры
        for i, partial_params in enumerate(partials_params):
            # Применение key scaling к параметрам огибающих
            if "keynum_to_vol_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_vol_env_decay"] / 1200.0
                partial_params["amp_envelope"]["key_scaling"] = key_scaling
            
            if "keynum_to_mod_env_decay" in partial_params:
                key_scaling = partial_params["keynum_to_mod_env_decay"] / 1200.0
                partial_params["filter_envelope"]["key_scaling"] = key_scaling
            
            # Применение coarseTune и fineTune
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
    
    def update_portamento(self):
        """Обновление состояния portamento"""
        if not self.portamento_active or not self.portamento_mode:
            return
            
        # Плавное изменение текущей частоты к целевой
        if abs(self.current_freq - self.target_freq) > 0.1:
            self.current_freq += self.portamento_step
            # Корректировка шага для учета control параметра
            if self.portamento_control < 1.0:
                self.current_freq = self.start_freq + (self.target_freq - self.start_freq) * self.portamento_control
        else:
            self.current_freq = self.target_freq
            self.portamento_active = False
    
    def handle_controller_change(self, controller, value):
        """
        Обработка сообщения Controller Change
        
        Args:
            controller: номер контроллера (0-127)
            value: значение контроллера (0-127)
        """
        self.controllers[controller] = value
        
        # Обработка стандартных контроллеров
        if controller == 1:  # Modulation Wheel
            for lfo in self.lfos:
                lfo.set_mod_wheel(value)
            
        elif controller == 2:  # Breath Controller
            for lfo in self.lfos:
                lfo.set_breath_controller(value)
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_brightness(value / 127.0)
            
        elif controller == 4:  # Foot Controller
            for lfo in self.lfos:
                lfo.set_foot_controller(value)
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_harmonic_content(value / 127.0)
            
        elif controller == 5:  # Portamento Time
            # Влияет на время portamento
            self.portamento_time = value * 0.05  # 0-6.4 секунды
            
        elif controller == 6:  # Data Entry
            # Data Entry используется для тонкой настройки параметров
            # Может использоваться в комбинации с RPN/NRPN
            pass
            
        elif controller == 7:  # Volume
            # Volume влияет на общий уровень, будет учтен при генерации
            pass
            
        elif controller == 8:  # Balance
            # Balance влияет на панорамирование
            for partial in self.partials:
                # В реальной реализации каждый partial может иметь свое панорамирование
                partial.pan = 0.5 + (value - 64) / 127.0
            
        elif controller == 10:  # Pan
            # Панорамирование
            for partial in self.partials:
                # В реальной реализации каждый partial может иметь свое панорамирование
                pass
            
        elif controller == 11:  # Expression
            # Expression влияет на громкость, будет учтено при генерации
            pass
            
        elif controller == 34:  # Vibrato Depth
            self.vibrato_depth = value * 0.78  # 0-100 центов
            
        elif controller == 35:  # Vibrato Rate
            self.vibrato_rate = 0.5 + value * 0.15  # 0.5-20 Hz
            
        elif controller == 36:  # Vibrato Delay
            self.vibrato_delay = value * 0.05  # 0-6.4 секунды
            
        elif controller == 64:  # Sustain Pedal
            if value >= 64:
                for partial in self.partials:
                    partial.amp_envelope.sustain_pedal_on()
                    if partial.filter_envelope:
                        partial.filter_envelope.sustain_pedal_on()
            else:
                for partial in self.partials:
                    partial.amp_envelope.sustain_pedal_off()
                    if partial.filter_envelope:
                        partial.filter_envelope.sustain_pedal_off()
                
        elif controller == 65:  # Portamento Switch
            self.portamento_mode = 1 if value >= 64 else 0
            
        elif controller == 66:  # Sostenuto Pedal
            if value >= 64:
                for partial in self.partials:
                    partial.amp_envelope.sostenuto_pedal_on()
                    if partial.filter_envelope:
                        partial.filter_envelope.sostenuto_pedal_on()
            else:
                for partial in self.partials:
                    partial.amp_envelope.sostenuto_pedal_off()
                    if partial.filter_envelope:
                        partial.filter_envelope.sostenuto_pedal_off()
                
        elif controller == 67:  # Soft Pedal
            if value >= 64:
                for partial in self.partials:
                    partial.amp_envelope.soft_pedal_on()
                    # Перезапуск огибающих с учетом soft pedal
                    if partial.amp_envelope.state != "idle":
                        partial.amp_envelope.note_on(self.velocity, self.note, soft_pedal=True)
            else:
                for partial in self.partials:
                    partial.amp_envelope.soft_pedal_off()
                    # Перезапуск огибающих без soft pedal
                    if partial.amp_envelope.state != "idle":
                        partial.amp_envelope.note_on(self.velocity, self.note, soft_pedal=False)
            
        elif controller == 71:  # Harmonic Content
            # Влияет на резонанс фильтра и форму волны
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_harmonic_content(value)
            for lfo in self.lfos:
                lfo.set_harmonic_content(value)
            
        elif controller == 74:  # Brightness
            # Влияет на cutoff фильтра
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_brightness(value)
            for lfo in self.lfos:
                lfo.set_brightness(value)
            
        elif controller == 77:  # Tremolo Depth
            self.tremolo_depth = value / 127.0
            
        elif controller == 78:  # Tremolo Rate
            self.tremolo_rate = 0.5 + value * 0.15  # 0.5-20 Hz
            
        elif controller == 84:  # Portamento Control
            self.portamento_control = value / 127.0
            
        elif controller == 120:  # All Sound Off
            for partial in self.partials:
                partial.amp_envelope.reset_all_notes()
                if partial.filter_envelope:
                    partial.filter_envelope.reset_all_notes()
            
        elif controller == 121:  # Reset All Controllers
            self.controllers = {k: 0 if k in [1, 2, 4, 34, 35, 36, 65, 66, 67, 71, 74, 77, 78, 84] 
                               else 127 if k == 11 else 64 if k == 10 else 0 for k in self.controllers}
            for lfo in self.lfos:
                lfo.set_mod_wheel(0)
                lfo.set_breath_controller(0)
                lfo.set_foot_controller(0)
                lfo.set_brightness(64)
                lfo.set_harmonic_content(64)
            for partial in self.partials:
                partial.amp_envelope.sustain_pedal = False
                partial.amp_envelope.sostenuto_pedal = False
                partial.amp_envelope.soft_pedal = False
            self.vibrato_depth = 50.0
            self.vibrato_rate = 5.0
            self.vibrato_delay = 0.0
            self.tremolo_depth = 0.0
            self.tremolo_rate = 4.0
            self.portamento_control = 1.0
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_brightness(64)
                    partial.filter.set_harmonic_content(64)
    
    def handle_nrpn(self, nrpn_msb, nrpn_lsb, data_msb, data_lsb):
        """
        Обработка NRPN сообщения (Non-Registered Parameter Number)
        
        Args:
            nrpn_msb: старший байт NRPN
            nrpn_lsb: младший байт NRPN
            data_msb: старший байт данных
            data_lsb: младший байт данных
        """
        nrpn = (nrpn_msb, nrpn_lsb)
        if nrpn not in self.XG_NRPN_PARAMS:
            return
            
        param_info = self.XG_NRPN_PARAMS[nrpn]
        data = (data_msb << 7) | data_lsb  # 14-bit value
        
        # Применение преобразования
        real_value = param_info["transform"](data)
        
        # Обработка матрицы модуляции
        if param_info["target"] == "mod_matrix":
            self._handle_modulation_matrix_nrpn(param_info["param"], real_value)
            return
        
        # Обработка частичных структур
        if param_info["target"] == "partial":
            self._handle_partial_nrpn(param_info["param"], real_value)
            return
        
        # Обработка барабанов
        if param_info["target"] == "drum":
            self._handle_drum_nrpn(param_info["param"], real_value)
            return
        
        # Обработка LFO
        if param_info["target"].startswith("lfo"):
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
            return
        
        # Обработка огибающих
        if param_info["target"] == "amp_envelope":
            for partial in self.partials:
                if param_info["param"] == "delay":
                    partial.amp_envelope.update_parameters(modulated_delay=real_value)
                elif param_info["param"] == "attack":
                    partial.amp_envelope.update_parameters(modulated_attack=real_value)
                elif param_info["param"] == "hold":
                    partial.amp_envelope.update_parameters(modulated_hold=real_value)
                elif param_info["param"] == "decay":
                    partial.amp_envelope.update_parameters(modulated_decay=real_value)
                elif param_info["param"] == "sustain":
                    partial.amp_envelope.update_parameters(modulated_sustain=real_value)
                elif param_info["param"] == "release":
                    partial.amp_envelope.update_parameters(modulated_release=real_value)
                elif param_info["param"] == "velocity_sense":
                    partial.amp_envelope.update_parameters(velocity_sense=real_value)
                elif param_info["param"] == "key_scaling":
                    partial.amp_envelope.update_parameters(key_scaling=real_value)
        elif param_info["target"] == "filter_envelope":
            for partial in self.partials:
                if partial.filter_envelope:
                    if param_info["param"] == "delay":
                        partial.filter_envelope.update_parameters(modulated_delay=real_value)
                    elif param_info["param"] == "attack":
                        partial.filter_envelope.update_parameters(modulated_attack=real_value)
                    elif param_info["param"] == "hold":
                        partial.filter_envelope.update_parameters(modulated_hold=real_value)
                    elif param_info["param"] == "decay":
                        partial.filter_envelope.update_parameters(modulated_decay=real_value)
                    elif param_info["param"] == "sustain":
                        partial.filter_envelope.update_parameters(modulated_sustain=real_value)
                    elif param_info["param"] == "release":
                        partial.filter_envelope.update_parameters(modulated_release=real_value)
                    elif param_info["param"] == "key_scaling":
                        partial.filter_envelope.update_parameters(key_scaling=real_value)
        elif param_info["target"] == "pitch_envelope":
            for partial in self.partials:
                if partial.pitch_envelope:
                    if param_info["param"] == "delay":
                        partial.pitch_envelope.update_parameters(modulated_delay=real_value)
                    elif param_info["param"] == "attack":
                        partial.pitch_envelope.update_parameters(modulated_attack=real_value)
                    elif param_info["param"] == "hold":
                        partial.pitch_envelope.update_parameters(modulated_hold=real_value)
                    elif param_info["param"] == "decay":
                        partial.pitch_envelope.update_parameters(modulated_decay=real_value)
                    elif param_info["param"] == "sustain":
                        partial.pitch_envelope.update_parameters(modulated_sustain=real_value)
                    elif param_info["param"] == "release":
                        partial.pitch_envelope.update_parameters(modulated_release=real_value)
        elif param_info["target"] == "filter":
            for partial in self.partials:
                if partial.filter:
                    if param_info["param"] == "cutoff":
                        partial.filter.set_parameters(cutoff=real_value)
                    elif param_info["param"] == "resonance":
                        partial.filter.set_parameters(resonance=real_value)
                    elif param_info["param"] == "key_follow":
                        partial.filter.key_follow = real_value
        elif param_info["target"] == "pitch":
            # Обработка pitch модуляции через матрицу
            pass
        elif param_info["target"] == "vibrato":
            if param_info["param"] == "rate":
                self.vibrato_rate = real_value
            elif param_info["param"] == "depth":
                self.vibrato_depth = real_value
            elif param_info["param"] == "delay":
                self.vibrato_delay = real_value
            elif param_info["param"] == "rise_time":
                self.vibrato_rise_time = real_value
        elif param_info["target"] == "tremolo":
            if param_info["param"] == "rate":
                self.tremolo_rate = real_value
            elif param_info["param"] == "depth":
                self.tremolo_depth = real_value
        elif param_info["target"] == "portamento":
            if param_info["param"] == "time":
                self.portamento_time = real_value
            elif param_info["param"] == "mode":
                self.portamento_mode = 1 if real_value > 0 else 0
            elif param_info["param"] == "control":
                self.portamento_control = real_value
        elif param_info["target"] == "equalizer":
            # В реальной реализации здесь обрабатывались бы параметры эквализатора
            pass
        elif param_info["target"] == "stereo":
            if param_info["param"] == "width":
                self.stereo_width = real_value
                for partial in self.partials:
                    if partial.filter:
                        partial.filter.set_parameters(stereo_width=self.stereo_width)
            elif param_info["param"] == "chorus":
                self.chorus_level = real_value
        elif param_info["target"] == "global":
            # Глобальные параметры обрабатываются при генерации
            pass
    
    def _handle_modulation_matrix_nrpn(self, param, value):
        """Обработка NRPN для матрицы модуляции"""
        # Для матрицы модуляции требуется отслеживать текущий индекс маршрута
        if not hasattr(self, 'current_mod_matrix_route'):
            self.current_mod_matrix_route = 0
        
        if param == "route_index":
            self.current_mod_matrix_route = int(value) % 16
            return
        
        # Получаем текущий маршрут
        route = self.mod_matrix.routes[self.current_mod_matrix_route]
        if route is None:
            # Создаем новый маршрут с параметрами по умолчанию
            route = ModulationRoute(
                source=ModulationSource.VELOCITY,
                destination=ModulationDestination.AMP,
                amount=0.0,
                polarity=1.0,
                velocity_sensitivity=0.0,
                key_scaling=0.0
            )
        
        # Обновляем параметр маршрута
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
        
        # Сохраняем обновленный маршрут
        self.mod_matrix.set_route(self.current_mod_matrix_route, 
                                route.source, route.destination,
                                route.amount, route.polarity,
                                route.velocity_sensitivity, route.key_scaling)
        
        # Если маршрут влияет на LFO, перезапускаем LFO
        if "lfo" in route.destination:
            lfo_index = int(route.destination[3]) - 1
            if 0 <= lfo_index < len(self.lfos):
                self.lfos[lfo_index].phase = 0.0
                self.lfos[lfo_index].delay_counter = 0
    
    def _handle_partial_nrpn(self, param, value):
        """Обработка NRPN для частичных структур"""
        # В реальной реализации здесь обрабатывались бы параметры частичных структур
        pass
    
    def _handle_drum_nrpn(self, param, value):
        """Обработка NRPN для барабанов"""
        if param == "tune":
            self.drum_tune = value
            # Пересчитываем частоту для барабанов
            if self.is_drum:
                self.current_freq = self._note_to_freq(self.note)
        elif param == "level":
            self.drum_level = value
        elif param == "pan":
            self.drum_pan = value
        elif param == "solo":
            self.drum_solo = value
        elif param == "mute":
            self.drum_mute = value
        elif param == "note_map":
            # В реальной реализации здесь менялась бы карта барабанов
            pass
    
    def handle_rpn(self, rpn_msb, rpn_lsb, data_msb, data_lsb):
        """
        Обработка RPN сообщения (Registered Parameter Number)
        
        Args:
            rpn_msb: старший байт RPN
            rpn_lsb: младший байт RPN
            data_msb: старший байт данных
            data_lsb: младший байт данных
        """
        rpn = (rpn_msb, rpn_lsb)
        if rpn not in self.XG_RPN_PARAMS:
            return
            
        param_name = self.XG_RPN_PARAMS[rpn]
        
        if param_name == "pitch_bend_range":
            semitones = data_msb
            cents = data_lsb
            self.pitch_bend_range = semitones + cents / 100.0
            
        elif param_name == "channel_coarse_tuning":
            self.coarse_tuning = data_msb - 64  # значение от -64 до 63
            
        elif param_name == "channel_fine_tuning":
            self.fine_tuning = (data_msb - 64) * 100 / 127.0  # значение от -50 до 50 центов
            
        elif param_name == "vibrato_control":
            # Управление vibrato через RPN (специфично для XG)
            self.vibrato_depth = data_msb * 0.78
            self.vibrato_rate = 0.5 + data_lsb * 0.15
        
        elif param_name == "drum_mode":
            # Переключение в режим барабана
            self.is_drum = (data_msb > 0)
            # Пересоздание частичных структур для нового режима
            self.partials = []
            self._setup_partials(self.wavetable)
    
    def handle_aftertouch(self, pressure):
        """
        Обработка Channel Aftertouch
        
        Args:
            pressure: значение послеудара (0-127)
        """
        self.channel_pressure = pressure
        for lfo in self.lfos:
            lfo.set_channel_aftertouch(pressure)
        for partial in self.partials:
            if partial.filter:
                partial.filter.set_aftertouch_mod(pressure / 127.0)
    
    def handle_key_aftertouch(self, note, pressure):
        """
        Обработка Key Aftertouch для конкретной ноты
        
        Args:
            note: MIDI нота
            pressure: значение послеудара (0-127)
        """
        if note == self.note:
            self.key_pressure[note] = pressure
            for lfo in self.lfos:
                lfo.set_key_aftertouch(pressure)
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_aftertouch_mod(pressure / 127.0)
    
    def handle_pitch_bend(self, value):
        """
        Обработка сообщения Pitch Bend
        
        Args:
            value: 14-битное значение pitch bend (0-16383)
        """
        self.pitch_bend_value = value
    
    def handle_program_change(self, program):
        """
        Обработка сообщения Program Change
        
        Args:
            program: новый номер программы
        """
        self.program = program
        self.params = self._get_parameters(program)
        
        # Обновление LFO
        self.lfos[0].set_parameters(
            waveform=self.params["lfo1"]["waveform"],
            rate=self.params["lfo1"]["rate"],
            depth=self.params["lfo1"]["depth"],
            delay=self.params["lfo1"]["delay"]
        )
        self.lfos[1].set_parameters(
            waveform=self.params["lfo2"]["waveform"],
            rate=self.params["lfo2"]["rate"],
            depth=self.params["lfo2"]["depth"],
            delay=self.params["lfo2"]["delay"]
        )
        self.lfos[2].set_parameters(
            waveform=self.params["lfo3"]["waveform"],
            rate=self.params["lfo3"]["rate"],
            depth=self.params["lfo3"]["depth"],
            delay=self.params["lfo3"]["delay"]
        )
        
        # Получение матрицы модуляции из SoundFont
        modulation_matrix = []
        if hasattr(self.wavetable, 'get_modulation_matrix'):
            modulation_matrix = self.wavetable.get_modulation_matrix(program, self.bank)
        
        # Обновление матрицы модуляции
        self.update_modulation_matrix(modulation_matrix)
        
        # Пересоздание частичных структур
        self.partials = []
        self._setup_partials(self.wavetable)
        
        # Если нет активных частичных структур, генератор неактивен
        if not any(partial.is_active() for partial in self.partials):
            self.active = False
    
    def update_modulation_matrix(self, modulation_matrix):
        """
        Обновление матрицы модуляции во время работы.
        
        Args:
            modulation_matrix: список маршрутов модуляции
        """
        # Очищаем текущую матрицу
        for i in range(16):
            self.mod_matrix.clear_route(i)
        
        # Добавляем маршруты из SoundFont
        for i, route in enumerate(modulation_matrix[:16]):  # Ограничиваем 16 маршрутами
            self.mod_matrix.set_route(
                index=i,
                source=route["source"],
                destination=route["destination"],
                amount=route["amount"],
                polarity=route["polarity"],
                velocity_sensitivity=route.get("velocity_sensitivity", 0.0),
                key_scaling=route.get("key_scaling", 0.0)
            )
        
        # Перезапуск LFO при изменении их параметров
        for i, lfo in enumerate(self.lfos):
            if any(route["destination"] in [
                getattr(ModulationDestination, f"LFO{i+1}_RATE"), 
                getattr(ModulationDestination, f"LFO{i+1}_DEPTH")
            ] for route in modulation_matrix):
                lfo.phase = 0.0
                lfo.delay_counter = 0
    
    def handle_sysex(self, manufacturer_id, data):
        """
        Обработка SysEx сообщения (System Exclusive)
        
        Args:
            manufacturer_id: ID производителя (для Yamaha обычно [0x43])
             данные сообщения
        """
        # Проверка, что это Yamaha SysEx
        if manufacturer_id != self.YAMAHA_MANUFACTURER_ID:
            return
        
        # Обработка XG-specific SysEx сообщений
        if len(data) < 3:
            return
            
        device_id = data[0]
        sub_status = data[1]
        command = data[2]
        
        # XG System On (F0 43 mm 7E 00 00 7E 00 F7)
        if sub_status == self.XG_SYSTEM_ON and command == 0x00:
            self._handle_xg_system_on(data[3:])
        
        # XG Parameter Change (F0 43 mm 04 0n pp vv F7)
        elif sub_status == self.XG_PARAMETER_CHANGE:
            self._handle_xg_parameter_change(data[3:])
        
        # XG Bulk Parameter Dump (F0 43 mm 7F 0n tt ... F7)
        elif sub_status == self.XG_BULK_PARAMETER_DUMP:
            self._handle_xg_bulk_parameter_dump(data[3:])
        
        # XG Bulk Parameter Request (F0 43 mm 7E 0n tt ... F7)
        elif sub_status == self.XG_BULK_PARAMETER_REQUEST:
            self._handle_xg_bulk_parameter_request(data[3:])
    
    def _handle_xg_system_on(self, data):
        """Обработка XG System On"""
        # Инициализация параметров XG
        self.pitch_bend_range = 2
        self.coarse_tuning = 0
        self.fine_tuning = 0
        self.scale_tuning = [0] * 12
        self.vibrato_rate = 5.0
        self.vibrato_depth = 50.0
        self.vibrato_delay = 0.0
        self.tremolo_depth = 0.0
        self.portamento_time = 0.2
        self.portamento_mode = 1
        self.note_shift = 0.0
        self.stereo_width = 0.5
        self.chorus_level = 0.0
        self.is_drum = False
        
        # Параметры барабанов
        self.drum_tune = 0.0
        self.drum_level = 1.0
        self.drum_pan = 0.5
        self.drum_solo = False
        self.drum_mute = False
        
        # Перезапуск LFO
        for lfo in self.lfos:
            lfo.phase = 0.0
            lfo.delay_counter = 0
        
        # Пересоздание частичных структур
        self.partials = []
        self._setup_partials(self.wavetable)
        
        # Если нет активных частичных структур, генератор неактивен
        if not any(partial.is_active() for partial in self.partials):
            self.active = False
    
    def _handle_xg_parameter_change(self, data):
        """Обработка XG Parameter Change"""
        if len(data) < 3:
            return
            
        # Извлечение параметра и значения
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value = data[2]
        
        # Обработка как NRPN
        self.handle_nrpn(parameter_msb, parameter_lsb, value, 0)
    
    def _handle_xg_bulk_parameter_dump(self, data):
        """Обработка XG Bulk Parameter Dump"""
        if len(data) < 2:
            return
            
        # Извлечение типа данных
        bank = data[0]
        data_type = data[1]
        
        # Обработка в зависимости от типа данных
        if data_type == self.XG_BULK_PARTIAL:
            self._handle_bulk_partial(data[2:])
        elif data_type == self.XG_BULK_PROGRAM:
            self._handle_bulk_program(data[2:])
        elif data_type == self.XG_BULK_DRUM_KIT:
            self._handle_bulk_drum_kit(data[2:])
        elif data_type == self.XG_BULK_SYSTEM:
            self._handle_bulk_system(data[2:])
        elif data_type == self.XG_BULK_ALL_PARAMETERS:
            self._handle_bulk_all_parameters(data[2:])
    
    def _handle_bulk_partial(self, data):
        """Обработка bulk данных для частичной структуры"""
        if len(data) < 2:
            return
            
        partial_id = data[0]
        parameter = data[1]
        
        # Извлечение значения (14-bit)
        value = (data[2] << 7) | data[3]
        
        # Обновление параметра частичной структуры
        if 0 <= partial_id < len(self.partials):
            partial = self.partials[partial_id]
            
            # Обработка различных параметров частичной структуры
            if parameter == 0:  # Level
                partial.level = value / 16383.0
            elif parameter == 1:  # Pan
                partial.pan = value / 16383.0
            elif parameter == 2:  # Key Range Low
                partial.key_range_low = value & 0x7F
            elif parameter == 3:  # Key Range High
                partial.key_range_high = value & 0x7F
            elif parameter == 4:  # Velocity Range Low
                partial.velocity_range_low = value & 0x7F
            elif parameter == 5:  # Velocity Range High
                partial.velocity_range_high = value & 0x7F
            elif parameter == 6:  # Key Scaling
                partial.key_scaling = (value - 8192) / 8192.0
            elif parameter == 7:  # Velocity Sense
                partial.velocity_sense = 0.5 + value * 0.0078
            elif parameter == 8:  # Crossfade Velocity
                partial.crossfade_velocity = (value > 8192)
            elif parameter == 9:  # Crossfade Note
                partial.crossfade_note = (value > 8192)
            elif parameter == 10:  # Use Filter Env
                partial.use_filter_env = (value > 8192)
            elif parameter == 11:  # Use Pitch Env
                partial.use_pitch_env = (value > 8192)
            elif parameter == 12:  # Amp Env Delay
                partial.amp_envelope.update_parameters(modulated_delay=value * 0.05)
            elif parameter == 13:  # Amp Env Attack
                partial.amp_envelope.update_parameters(modulated_attack=value * 0.05)
            elif parameter == 14:  # Amp Env Hold
                partial.amp_envelope.update_parameters(modulated_hold=value * 0.05)
            elif parameter == 15:  # Amp Env Decay
                partial.amp_envelope.update_parameters(modulated_decay=value * 0.05)
            elif parameter == 16:  # Amp Env Sustain
                partial.amp_envelope.update_parameters(modulated_sustain=value / 127.0)
            elif parameter == 17:  # Amp Env Release
                partial.amp_envelope.update_parameters(modulated_release=value * 0.05)
            elif parameter == 18:  # Filter Env Delay
                partial.filter_envelope.update_parameters(modulated_delay=value * 0.05)
            elif parameter == 19:  # Filter Env Attack
                partial.filter_envelope.update_parameters(modulated_attack=value * 0.05)
            elif parameter == 20:  # Filter Env Hold
                partial.filter_envelope.update_parameters(modulated_hold=value * 0.05)
            elif parameter == 21:  # Filter Env Decay
                partial.filter_envelope.update_parameters(modulated_decay=value * 0.05)
            elif parameter == 22:  # Filter Env Sustain
                partial.filter_envelope.update_parameters(modulated_sustain=value / 127.0)
            elif parameter == 23:  # Filter Env Release
                partial.filter_envelope.update_parameters(modulated_release=value * 0.05)
    
    def _handle_bulk_program(self, data):
        """Обработка bulk данных для программы"""
        if len(data) < 2:
            return
            
        parameter = data[0]
        
        # Извлечение значения (14-bit)
        value = (data[1] << 7) | data[2]
        
        # Обработка различных параметров программы
        if parameter == 0:  # Amp Envelope Attack
            for partial in self.partials:
                partial.amp_envelope.update_parameters(attack=value * 0.05)
        elif parameter == 1:  # Amp Envelope Decay
            for partial in self.partials:
                partial.amp_envelope.update_parameters(decay=value * 0.05)
        elif parameter == 2:  # Amp Envelope Sustain
            for partial in self.partials:
                partial.amp_envelope.update_parameters(sustain=value / 127.0)
        elif parameter == 3:  # Amp Envelope Release
            for partial in self.partials:
                partial.amp_envelope.update_parameters(release=value * 0.05)
        elif parameter == 4:  # Filter Cutoff
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_parameters(cutoff=20 + value * 150)
        elif parameter == 5:  # Filter Resonance
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_parameters(resonance=value / 64.0)
        elif parameter == 6:  # LFO1 Rate
            self.lfos[0].set_parameters(rate=0.1 + value * 0.2)
        elif parameter == 7:  # LFO1 Depth
            self.lfos[0].set_parameters(depth=value / 127.0)
        elif parameter == 8:  # LFO1 Delay
            self.lfos[0].set_parameters(delay=value * 0.05)
        elif parameter == 9:  # LFO1 Waveform
            waveforms = ["sine", "triangle", "square", "sawtooth"]
            waveform = waveforms[min(value // 32, 3)]
            self.lfos[0].set_parameters(waveform=waveform)
        elif parameter == 10:  # LFO2 Rate
            self.lfos[1].set_parameters(rate=0.1 + value * 0.2)
        elif parameter == 11:  # LFO2 Depth
            self.lfos[1].set_parameters(depth=value / 127.0)
        elif parameter == 12:  # LFO2 Delay
            self.lfos[1].set_parameters(delay=value * 0.05)
        elif parameter == 13:  # LFO2 Waveform
            waveforms = ["sine", "triangle", "square", "sawtooth"]
            waveform = waveforms[min(value // 32, 3)]
            self.lfos[1].set_parameters(waveform=waveform)
        elif parameter == 14:  # LFO3 Rate
            self.lfos[2].set_parameters(rate=0.1 + value * 0.2)
        elif parameter == 15:  # LFO3 Depth
            self.lfos[2].set_parameters(depth=value / 127.0)
        elif parameter == 16:  # LFO3 Delay
            self.lfos[2].set_parameters(delay=value * 0.05)
        elif parameter == 17:  # LFO3 Waveform
            waveforms = ["sine", "triangle", "square", "sawtooth"]
            waveform = waveforms[min(value // 32, 3)]
            self.lfos[2].set_parameters(waveform=waveform)
        elif parameter == 18:  # Modulation Matrix
            self._handle_bulk_modulation_matrix(data[3:])
        elif parameter == 19:  # Amp Envelope Delay
            for partial in self.partials:
                partial.amp_envelope.update_parameters(delay=value * 0.05)
        elif parameter == 20:  # Amp Envelope Hold
            for partial in self.partials:
                partial.amp_envelope.update_parameters(hold=value * 0.05)
        elif parameter == 21:  # Filter Envelope Delay
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(delay=value * 0.05)
        elif parameter == 22:  # Filter Envelope Hold
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(hold=value * 0.05)
        elif parameter == 23:  # Key Scaling Amp Env
            for partial in self.partials:
                partial.amp_envelope.update_parameters(key_scaling=(value - 8192) / 8192.0)
        elif parameter == 24:  # Key Scaling Filter Env
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(key_scaling=(value - 8192) / 8192.0)
        elif parameter == 25:  # Vibrato Depth
            self.vibrato_depth = value * 0.78
        elif parameter == 26:  # Vibrato Rate
            self.vibrato_rate = 0.5 + value * 0.15
        elif parameter == 27:  # Vibrato Delay
            self.vibrato_delay = value * 0.05
        elif parameter == 28:  # Tremolo Depth
            self.tremolo_depth = value / 127.0
    
    def _handle_bulk_modulation_matrix(self, data):
        """Обработка bulk данных для матрицы модуляции"""
        if len(data) < 6:
            return
            
        route_index = data[0]
        source = data[1]
        destination = data[2]
        amount = (data[3] << 7) | data[4]
        polarity = 1.0 if data[5] < 64 else -1.0
        
        # Получаем источники и цели
        sources = ModulationSource.get_all_sources()
        destinations = ModulationDestination.get_all_destinations()
        
        # Проверка индексов
        if route_index < 16 and source < len(sources) and destination < len(destinations):
            self.mod_matrix.set_route(
                index=route_index,
                source=sources[source],
                destination=destinations[destination],
                amount=amount / 16383.0,
                polarity=polarity
            )
    
    def _handle_bulk_drum_kit(self, data):
        """Обработка bulk данных для барабанного набора"""
        if len(data) < 2:
            return
            
        note = data[0]
        parameter = data[1]
        
        # Извлечение значения (14-bit)
        value = (data[2] << 7) | data[3]
        
        # Обработка различных параметров барабана
        if parameter == 0:  # Tune
            self.drum_tune = (value - 8192) * 0.5
        elif parameter == 1:  # Level
            self.drum_level = value / 16383.0
        elif parameter == 2:  # Pan
            self.drum_pan = (value - 8192) / 8192.0
        elif parameter == 3:  # Solo
            self.drum_solo = (value > 8192)
        elif parameter == 4:  # Mute
            self.drum_mute = (value > 8192)
    
    def _handle_bulk_system(self, data):
        """Обработка bulk данных для системных параметров"""
        if len(data) < 2:
            return
            
        parameter = data[0]
        
        # Извлечение значения (14-bit)
        value = (data[1] << 7) | data[2]
        
        # Обработка различных системных параметров
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
    
    def _handle_bulk_all_parameters(self, data):
        """Обработка bulk данных для всех параметров"""
        # Разбиваем данные на блоки и обрабатываем каждый блок отдельно
        offset = 0
        while offset < len(data):
            if offset + 4 > len(data):
                break
                
            # Извлечение типа данных
            data_type = data[offset]
            parameter = data[offset+1]
            
            # Извлечение значения (14-bit)
            value = (data[offset+2] << 7) | data[offset+3]
            
            # Обработка в зависимости от типа данных
            if data_type == self.XG_BULK_PARTIAL:
                self._handle_bulk_partial([parameter, value >> 7, value & 0x7F])
            elif data_type == self.XG_BULK_PROGRAM:
                self._handle_bulk_program([parameter, value >> 7, value & 0x7F])
            elif data_type == self.XG_BULK_DRUM_KIT:
                self._handle_bulk_drum_kit([parameter, value >> 7, value & 0x7F])
            elif data_type == self.XG_BULK_SYSTEM:
                self._handle_bulk_system([parameter, value >> 7, value & 0x7F])
            
            offset += 4
    
    def _handle_xg_bulk_parameter_request(self, data):
        """Обработка запроса bulk данных"""
        # В реальной реализации здесь формировался бы ответ с запрошенными параметрами
        pass
    
    def note_off(self):
        """Обработка события Note Off"""
        for partial in self.partials:
            partial.note_off()
    
    def note_on(self, new_velocity, same_note=False):
        """
        Обработка события Note On для той же ноты (SAME NOTE NUMBER KEY ON ASSIGN)
        
        Args:
            new_velocity: новая скорость нажатия
            same_note: флаг, указывающий, что это повторная нота
        """
        if same_note and self.same_note_key_on_assign:
            # В режиме SAME NOTE NUMBER KEY ON ASSIGN для той же ноты:
            # - Если sustain pedal выключен, перезапускаем огибающую
            # - Если sustain pedal включен, игнорируем повторное нажатие
            if not self.partials[0].amp_envelope.sustain_pedal and not self.partials[0].amp_envelope.sostenuto_pedal:
                self.velocity = new_velocity
                for partial in self.partials:
                    partial.amp_envelope.note_on(new_velocity, self.note)
                    if partial.filter_envelope:
                        partial.filter_envelope.note_on(new_velocity, self.note)
                    if partial.pitch_envelope:
                        partial.pitch_envelope.note_on(new_velocity, self.note)
        else:
            # Обычное поведение для новой ноты
            self.velocity = new_velocity
            for partial in self.partials:
                partial.amp_envelope.note_on(new_velocity, self.note)
                if partial.filter_envelope:
                    partial.filter_envelope.note_on(new_velocity, self.note)
                if partial.pitch_envelope:
                    partial.pitch_envelope.note_on(new_velocity, self.note)
    
    def is_active(self):
        """Проверка, активен ли тон-генератор"""
        return self.active and any(partial.is_active() for partial in self.partials)
    
    def generate_sample(self):
        """
        Генерация одного аудио сэмпла в стерео формате с использованием
        множественных LFO, матрицы модуляции и Partial Structure.
        
        Returns:
            кортеж (left_sample, right_sample) в диапазоне [-1.0, 1.0]
        """
        if not self.is_active():
            return (0.0, 0.0)
        
        # Обновление portamento (плавный переход между нотами)
        self.update_portamento()
        
        # Обработка pitch bend
        pitch_bend_range_cents = self.pitch_bend_range * 100
        pitch_bend_offset = ((self.pitch_bend_value - 8192) / 8192.0) * pitch_bend_range_cents
        
        # Обработка detune
        total_detune = self.detune + pitch_bend_offset
        
        # Глобальная модуляция pitch (от pitch bend и других глобальных источников)
        global_pitch_mod = total_detune
        
        # Сбор значений источников для матрицы модуляции
        sources = {
            ModulationSource.VELOCITY: self.velocity / 127.0,
            ModulationSource.AFTER_TOUCH: self.channel_pressure / 127.0,
            ModulationSource.MOD_WHEEL: self.controllers[1] / 127.0,
            ModulationSource.BREATH_CONTROLLER: self.controllers[2] / 127.0,
            ModulationSource.FOOT_CONTROLLER: self.controllers[4] / 127.0,
            ModulationSource.DATA_ENTRY: self.controllers[6] / 127.0,
            ModulationSource.LFO1: self.lfos[0].step(),
            ModulationSource.LFO2: self.lfos[1].step(),
            ModulationSource.LFO3: self.lfos[2].step(),
            ModulationSource.AMP_ENV: self.partials[0].amp_envelope.process() if self.partials else 0.0,
            ModulationSource.FILTER_ENV: self.partials[0].filter_envelope.process() if self.partials and self.partials[0].filter_envelope else 0.0,
            ModulationSource.PITCH_ENV: self.partials[0].pitch_envelope.process() if self.partials and self.partials[0].pitch_envelope else 0.0,
            ModulationSource.KEY_PRESSURE: self.key_pressure.get(self.note, 0) / 127.0,
            ModulationSource.BRIGHTNESS: self.controllers[74] / 127.0,
            ModulationSource.HARMONIC_CONTENT: self.controllers[71] / 127.0,
            ModulationSource.PORTAMENTO: 1.0 if self.portamento_active else 0.0,
            ModulationSource.VIBRATO: self.vibrato_depth / 100.0,
            ModulationSource.TREMOLO: self.tremolo_depth,
            ModulationSource.TREMOLO_DEPTH: self.tremolo_depth,
            ModulationSource.TREMOLO_RATE: self.tremolo_rate,
            ModulationSource.NOTE_NUMBER: self.note / 127.0,
            ModulationSource.VOLUME_CC: self.controllers[7] / 127.0,
            ModulationSource.BALANCE: (self.controllers[8] - 64) / 64.0,
            ModulationSource.PORTAMENTO_TIME_CC: self.controllers[5] / 127.0
        }
        
        # Применение матрицы модуляции
        modulation_values = self.mod_matrix.process(sources, self.velocity, self.note)
        
        # Применение модуляции к глобальным параметрам
        if ModulationDestination.PITCH in modulation_values:
            global_pitch_mod += modulation_values[ModulationDestination.PITCH]
        
        # Обработка модуляции параметров LFO
        for i, lfo in enumerate(self.lfos):
            lfo_index = i + 1
            lfo_rate_param = getattr(ModulationDestination, f"LFO{lfo_index}_RATE")
            lfo_depth_param = getattr(ModulationDestination, f"LFO{lfo_index}_DEPTH")
            
            if lfo_rate_param in modulation_values:
                lfo.set_parameters(modulated_rate=lfo.rate * (1 + modulation_values[lfo_rate_param]))
            
            if lfo_depth_param in modulation_values:
                lfo.set_parameters(modulated_depth=lfo.depth * (1 + modulation_values[lfo_depth_param]))
        
        # Обработка модуляции параметров амплитудной огибающей
        if ModulationDestination.AMP_DELAY in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_delay=partial.amp_envelope.delay * (1 + modulation_values[ModulationDestination.AMP_DELAY])
                )
        
        if ModulationDestination.AMP_ATTACK in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_attack=partial.amp_envelope.attack * (1 + modulation_values[ModulationDestination.AMP_ATTACK])
                )
        
        if ModulationDestination.AMP_HOLD in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_hold=partial.amp_envelope.hold * (1 + modulation_values[ModulationDestination.AMP_HOLD])
                )
        
        if ModulationDestination.AMP_DECAY in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_decay=partial.amp_envelope.decay * (1 + modulation_values[ModulationDestination.AMP_DECAY])
                )
        
        if ModulationDestination.AMP_SUSTAIN in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_sustain=partial.amp_envelope.sustain * (1 + modulation_values[ModulationDestination.AMP_SUSTAIN])
                )
        
        if ModulationDestination.AMP_RELEASE in modulation_values:
            for partial in self.partials:
                partial.amp_envelope.update_parameters(
                    modulated_release=partial.amp_envelope.release * (1 + modulation_values[ModulationDestination.AMP_RELEASE])
                )
        
        # Обработка модуляции параметров фильтровой огибающей
        if ModulationDestination.FILTER_DELAY in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_delay=partial.filter_envelope.delay * (1 + modulation_values[ModulationDestination.FILTER_DELAY])
                    )
        
        if ModulationDestination.FILTER_ATTACK in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_attack=partial.filter_envelope.attack * (1 + modulation_values[ModulationDestination.FILTER_ATTACK])
                    )
        
        if ModulationDestination.FILTER_HOLD in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_hold=partial.filter_envelope.hold * (1 + modulation_values[ModulationDestination.FILTER_HOLD])
                    )
        
        if ModulationDestination.FILTER_DECAY in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_decay=partial.filter_envelope.decay * (1 + modulation_values[ModulationDestination.FILTER_DECAY])
                    )
        
        if ModulationDestination.FILTER_SUSTAIN in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_sustain=partial.filter_envelope.sustain * (1 + modulation_values[ModulationDestination.FILTER_SUSTAIN])
                    )
        
        if ModulationDestination.FILTER_RELEASE in modulation_values:
            for partial in self.partials:
                if partial.filter_envelope:
                    partial.filter_envelope.update_parameters(
                        modulated_release=partial.filter_envelope.release * (1 + modulation_values[ModulationDestination.FILTER_RELEASE])
                    )
        
        # Обработка модуляции stereo width
        if ModulationDestination.STEREO_WIDTH in modulation_values:
            self.stereo_width = max(0.0, min(1.0, 0.5 + modulation_values[ModulationDestination.STEREO_WIDTH]))
            for partial in self.partials:
                if partial.filter:
                    partial.filter.set_parameters(modulated_stereo_width=self.stereo_width)
        
        # Расчет кросс-фейда по velocity
        velocity_crossfade = 0.0
        if ModulationDestination.VELOCITY_CROSSFADE in modulation_values:
            velocity_crossfade = modulation_values[ModulationDestination.VELOCITY_CROSSFADE]
        
        # Расчет кросс-фейда по ноте
        note_crossfade = 0.0
        if ModulationDestination.NOTE_CROSSFADE in modulation_values:
            note_crossfade = modulation_values[ModulationDestination.NOTE_CROSSFADE]
        
        # Генерация сэмпла для каждой частичной структуры и их смешивание
        left_sum = 0.0
        right_sum = 0.0
        active_partials = 0
        
        for partial in self.partials:
            if not partial.is_active():
                continue
                
            partial_samples = partial.generate_sample(
                lfos=self.lfos,
                global_pitch_mod=global_pitch_mod,
                velocity_crossfade=velocity_crossfade,
                note_crossfade=note_crossfade
            )
            
            left_sum += partial_samples[0]
            right_sum += partial_samples[1]
            active_partials += 1
        
        # Нормализация по количеству активных частичных структур
        if active_partials > 0:
            left_sum /= active_partials
            right_sum /= active_partials
        
        # Общая громкость (volume и expression)
        volume = (self.controllers[7] / 127.0) * (self.controllers[11] / 127.0)
        left_out = left_sum * volume
        right_out = right_sum * volume
        
        # Применение уровня барабана (если в режиме барабана)
        if self.is_drum:
            left_out *= self.drum_level
            right_out *= self.drum_level
            
            # Применение панорамирования барабана
            panner = StereoPanner(pan_position=self.drum_pan, sample_rate=self.sample_rate)
            left_out, right_out = panner.process((left_out + right_out) / 2.0)
        
        # Применение стерео эффектов (хорус)
        if self.chorus_level > 0:
            # Простой стерео хорус
            delay = 0.015  # 15ms задержка
            feedback = 0.7
            wet = self.chorus_level
            
            # Задержка для правого канала
            right_delayed = left_out * feedback
            left_out = left_out * (1 - wet) + right_delayed * wet
            right_out = right_out * (1 - wet) + left_out * wet
        
        return (left_out, right_out)