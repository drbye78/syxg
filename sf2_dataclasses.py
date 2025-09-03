import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass


class SF2Modulator:
    """Представляет модулятор в SoundFont 2.0"""
    __slots__ = [
        'source_oper', 'source_polarity', 'source_type', 'source_direction', 'source_index',
        'control_oper', 'control_polarity', 'control_type', 'control_direction', 'control_index',
        'destination', 'amount', 'amount_source_oper', 'amount_source_polarity',
        'amount_source_type', 'amount_source_direction', 'amount_source_index', 'transform'
    ]
    
    def __init__(self):
        # Источник модуляции
        self.source_oper = 0  # Source Operator
        self.source_polarity = 0  # 0 = unipolar, 1 = bipolar
        self.source_type = 0  # 0 = linear, 1 = concave
        self.source_direction = 0  # 0 = max -> min, 1 = min -> max
        self.source_index = 0  # Индекс источника (для CC)
        
        # Управление модуляцией
        self.control_oper = 0  # Control Operator
        self.control_polarity = 0
        self.control_type = 0
        self.control_direction = 0
        self.control_index = 0
        
        # Цель модуляции
        self.destination = 0  # Destination Generator
        
        # Глубина модуляции
        self.amount = 0  # Значение глубины
        
        # Источник глубины модуляции
        self.amount_source_oper = 0
        self.amount_source_polarity = 0
        self.amount_source_type = 0
        self.amount_source_direction = 0
        self.amount_source_index = 0
        
        # Преобразование
        self.transform = 0  # Transform Operator

class SF2InstrumentZone:
    """Представляет зону инструмента в SoundFont 2.0"""
    __slots__ = [
        'lokey', 'hikey', 'lovel', 'hivel', 'initial_filterQ', 'initialFilterFc',
        'peakConcave', 'voiceConcave', 'AttackVolEnv', 'DecayVolEnv', 'SustainVolEnv',
        'ReleaseVolEnv', 'DelayVolEnv', 'HoldVolEnv', 'AttackFilEnv', 'DecayFilEnv',
        'SustainFilEnv', 'ReleaseFilEnv', 'DelayFilEnv', 'HoldFilEnv', 'AttackPitchEnv',
        'DecayPitchEnv', 'SustainPitchEnv', 'ReleasePitchEnv', 'DelayPitchEnv',
        'HoldPitchEnv', 'DelayLFO1', 'DelayLFO2', 'LFO1Freq', 'LFO2Freq',
        'LFO1VolumeToPitch', 'LFO1VolumeToFilter', 'LFO1VolumeToVolume',
        'InitialAttenuation', 'Pan', 'VelocityAttenuation', 'VelocityPitch',
        'OverridingRootKey', 'KeynumToVolEnvHold', 'KeynumToVolEnvDecay',
        'KeynumToModEnvHold', 'KeynumToModEnvDecay', 'CoarseTune', 'FineTune',
        'sample_index', 'sample_name', 'mute', 'keynum_to_volume', 'modulators',
        'lfo_to_pitch', 'lfo_to_filter', 'velocity_to_pitch', 'velocity_to_filter',
        'aftertouch_to_pitch', 'aftertouch_to_filter', 'mod_wheel_to_pitch',
        'mod_wheel_to_filter', 'brightness_to_filter', 'portamento_to_pitch',
        'tremolo_depth', 'mod_env_to_pitch', 'mod_lfo_to_pitch', 'vib_lfo_to_pitch',
        'vibrato_depth', 'mod_lfo_to_filter', 'mod_env_to_filter', 'mod_lfo_to_volume',
        'mod_ndx', 'gen_ndx', 'generators', 'sample_modes', 'exclusive_class',
        'start', 'end', 'start_loop', 'end_loop'
    ]
    
    def __init__(self):
        # Диапазоны нот и velocity
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127
        
        # Основные параметры
        self.initial_filterQ = 0
        self.initialFilterFc = 13500
        self.peakConcave = 0
        self.voiceConcave = 0
        
        # Параметры амплитудной огибающей
        self.AttackVolEnv = 9600  # в time cents
        self.DecayVolEnv = 19200
        self.SustainVolEnv = 0  # 0-127 (0 = -inf dB)
        self.ReleaseVolEnv = 24000
        self.DelayVolEnv = 0  # Задержка амплитудной огибающей
        self.HoldVolEnv = 0  # Hold амплитудной огибающей
        
        # Параметры фильтровой огибающей
        self.AttackFilEnv = 19200
        self.DecayFilEnv = 19200
        self.SustainFilEnv = 0
        self.ReleaseFilEnv = 24000
        self.DelayFilEnv = 0  # Задержка фильтровой огибающей
        self.HoldFilEnv = 0  # Hold фильтровой огибающей
        
        # Параметры pitch огибающей
        self.AttackPitchEnv = 0
        self.DecayPitchEnv = 0
        self.SustainPitchEnv = 0
        self.ReleasePitchEnv = 0
        self.DelayPitchEnv = 0  # Задержка pitch огибающей
        self.HoldPitchEnv = 0  # Hold pitch огибающей
        
        # LFO параметры
        self.DelayLFO1 = 0
        self.DelayLFO2 = 0
        self.LFO1Freq = 500  # 0.01 Гц * значение
        self.LFO2Freq = 0
        self.LFO1VolumeToPitch = 0
        self.LFO1VolumeToFilter = 0
        self.LFO1VolumeToVolume = 0
        
        # Панорамирование
        self.InitialAttenuation = 0  # 0-1440 (0 = 1.0, 960 = -6dB, 1440 = -9dB)
        self.Pan = 50  # 0-100 (0 = left, 50 = center, 100 = right)
        
        # Скорость и высота
        self.VelocityAttenuation = 0
        self.VelocityPitch = 0
        self.OverridingRootKey = -1  # -1 = использовать ноту, иначе переназначить root key
        
        # Key scaling для огибающих
        self.KeynumToVolEnvHold = 0  # Keynum to Volume Envelope Hold
        self.KeynumToVolEnvDecay = 0  # Keynum to Volume Envelope Decay
        self.KeynumToModEnvHold = 0  # Keynum to Modulation Envelope Hold
        self.KeynumToModEnvDecay = 0  # Keynum to Modulation Envelope Decay
        
        # Настройка высоты
        self.CoarseTune = 0  # Грубая настройка (октавы)
        self.FineTune = 0  # Точная настройка (центы)
        
        # Ссылка на сэмпл
        self.sample_index = 0
        self.sample_name = "Default"
        
        # Дополнительные флаги
        self.mute = False
        self.keynum_to_volume = 0  # Key Number to Volume Envelope Delay
        
        # Sample parameters
        self.sample_modes = 0
        self.exclusive_class = 0
        self.start = 0
        self.end = 0
        self.start_loop = 0
        self.end_loop = 0
        
        # Модуляторы
        self.modulators = []
        
        # Генераторы (для хранения параметров)
        self.generators = {}
        
        # Распространенные модуляции (для упрощенного доступа)
        self.lfo_to_pitch = 0.0
        self.lfo_to_filter = 0.0
        self.velocity_to_pitch = 0.0
        self.velocity_to_filter = 0.0
        self.aftertouch_to_pitch = 0.0
        self.aftertouch_to_filter = 0.0
        self.mod_wheel_to_pitch = 0.0
        self.mod_wheel_to_filter = 0.0
        self.brightness_to_filter = 0.0
        self.portamento_to_pitch = 0.0
        self.tremolo_depth = 0.0
        self.mod_env_to_pitch = 0.0
        self.mod_lfo_to_pitch = 0.0
        self.vib_lfo_to_pitch = 0.0
        self.vibrato_depth = 0.0
        self.mod_lfo_to_filter = 0.0
        self.mod_env_to_filter = 0.0
        self.mod_lfo_to_volume = 0.0
        self.mod_ndx = 0
        self.gen_ndx = 0

class SF2PresetZone:
    """Представляет зону пресета в SoundFont 2.0"""
    __slots__ = [
        'preset', 'bank', 'generators', 'modulators', 'instrument_index',
        'instrument_name', 'lokey', 'hikey', 'lovel', 'hivel', 'lfo_to_pitch',
        'lfo_to_filter', 'velocity_to_pitch', 'velocity_to_filter',
        'aftertouch_to_pitch', 'aftertouch_to_filter', 'mod_wheel_to_pitch',
        'mod_wheel_to_filter', 'brightness_to_filter', 'portamento_to_pitch',
        'tremolo_depth', 'vibrato_depth', 'gen_ndx', 'mod_ndx',
        # Generator parameters that might be set by preset generators
        'initialFilterFc', 'initial_filterQ', 'Pan', 'DelayLFO1', 'LFO1Freq',
        'DelayLFO2', 'DelayFilEnv', 'AttackFilEnv', 'HoldFilEnv', 'DecayFilEnv',
        'SustainFilEnv', 'ReleaseFilEnv', 'KeynumToModEnvHold', 'KeynumToModEnvDecay',
        'DelayVolEnv', 'AttackVolEnv', 'HoldVolEnv', 'DecayVolEnv', 'SustainVolEnv',
        'ReleaseVolEnv', 'KeynumToVolEnvHold', 'KeynumToVolEnvDecay', 'CoarseTune', 'FineTune'
    ]
    
    def __init__(self):
        self.preset = 0
        self.bank = 0
        self.generators = {}  # Dictionary to store generator parameters
        self.modulators = []  # List of modulators for this preset zone
        self.instrument_index = 0
        self.instrument_name = ""
        
        # Диапазоны нот и velocity
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127
        
        # Generator parameters that might be set by preset generators
        self.initialFilterFc = 13500
        self.initial_filterQ = 0
        self.Pan = 50
        self.DelayLFO1 = 0
        self.LFO1Freq = 500
        self.DelayLFO2 = 0
        self.DelayFilEnv = 0
        self.AttackFilEnv = 19200
        self.HoldFilEnv = 0
        self.DecayFilEnv = 19200
        self.SustainFilEnv = 0
        self.ReleaseFilEnv = 24000
        self.KeynumToModEnvHold = 0
        self.KeynumToModEnvDecay = 0
        self.DelayVolEnv = 0
        self.AttackVolEnv = 9600
        self.HoldVolEnv = 0
        self.DecayVolEnv = 19200
        self.SustainVolEnv = 0
        self.ReleaseVolEnv = 24000
        self.KeynumToVolEnvHold = 0
        self.KeynumToVolEnvDecay = 0
        self.CoarseTune = 0
        self.FineTune = 0
        
        # Распространенные модуляции (для упрощенного доступа)
        self.lfo_to_pitch = 0.0
        self.lfo_to_filter = 0.0
        self.velocity_to_pitch = 0.0
        self.velocity_to_filter = 0.0
        self.aftertouch_to_pitch = 0.0
        self.aftertouch_to_filter = 0.0
        self.mod_wheel_to_pitch = 0.0
        self.mod_wheel_to_filter = 0.0
        self.brightness_to_filter = 0.0
        self.portamento_to_pitch = 0.0
        self.tremolo_depth = 0.0
        self.vibrato_depth = 0.0
        self.gen_ndx = 0
        self.mod_ndx = 0

class SF2SampleHeader:
    """Представляет заголовок сэмпла в SoundFont 2.0"""
    __slots__ = [
        'name', 'start', 'end', 'start_loop', 'end_loop', 'sample_rate',
        'original_pitch', 'pitch_correction', 'link', 'type'
    ]
    
    def __init__(self):
        self.name = "Default"
        self.start = 0
        self.end = 0
        self.start_loop = 0
        self.end_loop = 0
        self.sample_rate = 44100
        self.original_pitch = 60  # MIDI note number
        self.pitch_correction = 0  # в центах
        self.link = 0
        self.type = 1  # 1 = mono, 2 = right, 4 = left, 8 = linked

class SF2Preset:
    """Представляет пресет (инструмент) в SoundFont 2.0"""
    __slots__ = [
        'name', 'preset', 'bank', 'preset_bag_index', 'library', 'genre',
        'morphology', 'zones'
    ]
    
    def __init__(self):
        self.name = "Default"
        self.preset = 0
        self.bank = 0
        self.preset_bag_index = 0
        self.library = 0
        self.genre = 0
        self.morphology = 0
        self.zones: List[SF2PresetZone] = []  # Список SF2PresetZone

class SF2Instrument:
    """Представляет инструмент в SoundFont 2.0"""
    __slots__ = ['name', 'instrument_bag_index', 'zones']
    
    def __init__(self):
        self.name = "Default"
        self.instrument_bag_index = 0
        self.zones: List[SF2InstrumentZone] = []  # Список SF2InstrumentZone
