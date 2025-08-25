#!/usr/bin/env python3
"""
Optimized SoundFont 2.0 parser with improved performance.
This version properly handles LIST chunks in the RIFF structure and optimizes parsing speed.
"""

import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, BinaryIO

from tg import ModulationDestination, ModulationSource

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
        'mod_ndx', 'gen_ndx'
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
        
        # Модуляторы
        self.modulators = []
        
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
        'tremolo_depth', 'vibrato_depth', 'gen_ndx', 'mod_ndx'
    ]
    
    def __init__(self):
        self.preset = 0
        self.bank = 0
        self.generators = {}
        self.modulators = []
        self.instrument_index = 0
        self.instrument_name = ""
        
        # Диапазоны нот и velocity
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127
        
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
        self.zones = []  # Список SF2PresetZone

class SF2Instrument:
    """Представляет инструмент в SoundFont 2.0"""
    __slots__ = ['name', 'instrument_bag_index', 'zones']
    
    def __init__(self):
        self.name = "Default"
        self.instrument_bag_index = 0
        self.zones = []  # Список SF2InstrumentZone

class Sf2WavetableManager:
    """
    Оптимизированный менеджер wavetable сэмплов, основанный на SoundFont 2.0 файлах.
    Предоставляет интерфейс для XG Tone Generator с поддержкой нескольких слоев
    и барабанов. Реализует ленивую загрузку сэмплов и кэширование.
    Поддерживает загрузку нескольких SF2 файлов с приоритетами, черными списками
    и настраиваемым маппингом банков.
    """
    
    # Константы для преобразования параметров
    TIME_CENTISECONDS_TO_SECONDS = 0.01
    FILTER_CUTOFF_SCALE = 0.1
    PAN_SCALE = 0.01
    VELOCITY_SENSE_SCALE = 0.01
    PITCH_SCALE = 0.1
    FILTER_RESONANCE_SCALE = 0.01
    
    # Максимальный размер кэша сэмплов (в сэмплах, не в байтах)
    MAX_CACHE_SIZE = 50000000  # ~200 МБ для 16-битных сэмплов
    
    # Константы SoundFont для источников модуляции
    SF2_SOURCE_OPERATORS = {
        0: "no_controller",
        1: "note_on_velocity",
        2: "note_on_key_number",
        3: "polyphonic_aftertouch",
        4: "channel_aftertouch",
        5: "pitch_wheel",
        16: "cc_mod_wheel",
        17: "cc_breath_controller",
        18: "cc_unknown_18",
        19: "cc_foot_controller",
        20: "cc_portamento_time",
        21: "cc_data_entry",
        22: "cc_volume",
        23: "cc_balance",
        32: "cc_bank_select_lsb",
        33: "cc_mod_wheel_lsb",
        34: "cc_breath_controller_lsb",
        35: "cc_unknown_35_lsb",
        36: "cc_foot_controller_lsb",
        37: "cc_portamento_time_lsb",
        38: "cc_data_entry_lsb",
        39: "cc_volume_lsb",
        40: "cc_balance_lsb",
        74: "cc_brightness",
        77: "cc_tremolo_depth",
        78: "cc_tremolo_rate",
        84: "cc_portamento_control"
    }
    
    # Константы SoundFont для целей модуляции
    SF2_DESTINATION_GENERATORS = {
        0: "startAddrsOffset",
        1: "endAddrsOffset",
        2: "startloopAddrsOffset",
        3: "endloopAddrsOffset",
        4: "startAddrsCoarseOffset",
        5: "modLfoToPitch",
        6: "vibLfoToPitch",
        7: "modEnvToPitch",
        8: "initialFilterFc",
        9: "initialFilterQ",
        10: "modLfoToFilterFc",
        11: "modEnvToFilterFc",
        12: "endAddrsCoarseOffset",
        13: "modLfoToVolume",
        15: "chorusEffectsSend",
        16: "reverbEffectsSend",
        17: "pan",
        18: "delayModLFO",
        19: "freqModLFO",
        20: "delayVibLFO",
        21: "freqVibLFO",
        22: "delayModEnv",
        23: "attackModEnv",
        24: "holdModEnv",
        25: "decayModEnv",
        26: "sustainModEnv",
        27: "releaseModEnv",
        28: "keynumToModEnvHold",
        29: "keynumToModEnvDecay",
        30: "delayVolEnv",
        31: "attackVolEnv",
        32: "holdVolEnv",
        33: "decayVolEnv",
        34: "sustainVolEnv",
        35: "releaseVolEnv",
        36: "keynumToVolEnvHold",
        37: "keynumToVolEnvDecay",
        38: "instrument",
        40: "keyRange",
        41: "velRange",
        42: "startloopAddrsCoarseOffset",
        43: "keynumToVolEnvDecay",
        44: "fixedMidivel",
        50: "coarseTune",
        51: "fineTune",
        53: "sampleModes",
        54: "exclusiveClass",
        55: "overridingRootKey",
        56: "endOper"
    }
    
    # Сопоставление целей SoundFont с целями XG
    SF2_TO_XG_DESTINATIONS = {
        5: ModulationDestination.PITCH,  # modLfoToPitch
        6: ModulationDestination.PITCH,  # vibLfoToPitch
        7: ModulationDestination.PITCH,  # modEnvToPitch
        8: ModulationDestination.FILTER_CUTOFF,  # initialFilterFc
        10: ModulationDestination.FILTER_CUTOFF,  # modLfoToFilterFc
        11: ModulationDestination.FILTER_CUTOFF,  # modEnvToFilterFc
        13: ModulationDestination.AMP,  # modLfoToVolume
        17: ModulationDestination.PAN,  # pan
        22: ModulationDestination.AMP_ATTACK,  # delayVolEnv
        23: ModulationDestination.FILTER_ATTACK,  # attackModEnv
        24: ModulationDestination.FILTER_HOLD,  # holdModEnv
        25: ModulationDestination.FILTER_DECAY,  # decayModEnv
        26: ModulationDestination.FILTER_SUSTAIN,  # sustainModEnv
        27: ModulationDestination.FILTER_RELEASE,  # releaseModEnv
        28: ModulationDestination.FILTER_HOLD,  # keynumToModEnvHold
        29: ModulationDestination.FILTER_DECAY,  # keynumToModEnvDecay
        30: ModulationDestination.AMP_ATTACK,  # delayVolEnv
        31: ModulationDestination.AMP_ATTACK,  # attackVolEnv
        32: ModulationDestination.AMP_HOLD,  # holdVolEnv
        33: ModulationDestination.AMP_DECAY,  # decayVolEnv
        34: ModulationDestination.AMP_SUSTAIN,  # sustainVolEnv
        35: ModulationDestination.AMP_RELEASE,  # releaseVolEnv
        36: ModulationDestination.AMP_HOLD,  # keynumToVolEnvHold
        37: ModulationDestination.AMP_DECAY,  # keynumToVolEnvDecay
        50: "coarseTune",  # coarseTune
        51: "fineTune",  # fineTune
        77: ModulationDestination.TREMOLO_DEPTH,  # cc_tremolo_depth
        78: ModulationDestination.TREMOLO_RATE  # cc_tremolo_rate
    }
    
    # Сопоставление источников SoundFont с источниками XG
    SF2_TO_XG_SOURCES = {
        "note_on_velocity": ModulationSource.VELOCITY,
        "channel_aftertouch": ModulationSource.AFTER_TOUCH,
        "cc_mod_wheel": ModulationSource.MOD_WHEEL,
        "modLFO": ModulationSource.LFO1,
        "vibLFO": ModulationSource.LFO2,
        "modEnv": ModulationSource.AMP_ENV,
        "pitch_wheel": ModulationSource.NOTE_NUMBER,
        "cc_brightness": ModulationSource.BRIGHTNESS,
        "cc_tremolo_depth": ModulationSource.TREMOLO_DEPTH,
        "cc_tremolo_rate": ModulationSource.TREMOLO_RATE,
        "cc_portamento_control": ModulationSource.PORTAMENTO
    }

    def __init__(self, sf2_paths: Union[str, List[str]], cache_size: int = None):
        """
        Инициализация менеджера SoundFont.
        
        Args:
            sf2_paths: путь к файлу SoundFont (.sf2) или список путей
            cache_size: максимальный размер кэша в сэмплах (по умолчанию MAX_CACHE_SIZE)
        """
        # Поддержка одного или нескольких SF2 файлов
        self.sf2_paths = sf2_paths if isinstance(sf2_paths, list) else [sf2_paths]
        
        # Список менеджеров для каждого SF2 файла
        self.sf2_managers: List[Dict[str, Any]] = []
        
        # Глобальные данные
        self.presets: List[SF2Preset] = []
        self.instruments: List[SF2Instrument] = []
        self.sample_headers: List[SF2SampleHeader] = []
        self.bank_instruments: Dict[int, Dict[int, int]] = {}  # bank -> program -> preset index
        
        # Настройки для каждого SF2 файла
        self.bank_blacklists: Dict[str, List[int]] = {}  # sf2_path -> список банков для исключения
        self.preset_blacklists: Dict[str, List[Tuple[int, int]]] = {}  # sf2_path -> список (bank, program) для исключения
        self.bank_mappings: Dict[str, Dict[int, int]] = {}  # sf2_path -> bank_mapping (midi_bank -> sf2_bank)
        
        # Кэш для загруженных сэмплов
        self.sample_cache = OrderedDict()
        self.current_cache_size = 0
        self.max_cache_size = cache_size if cache_size is not None else self.MAX_CACHE_SIZE
        
        # Загружаем все SF2 файлы
        self._load_all_sf2_files()
        
        # Собираем все пресеты в один глобальный список с приоритетами
        self._build_global_preset_map()
    
    def __del__(self):
        """Закрываем все файлы при уничтожении объекта"""
        for manager in self.sf2_managers:
            if 'file' in manager and hasattr(manager['file'], 'closed') and not manager['file'].closed:
                manager['file'].close()
    
    def _load_all_sf2_files(self):
        """Загрузка всех SF2 файлов с оптимизацией"""
        for i, sf2_path in enumerate(self.sf2_paths):
            try:
                # Открываем файл для чтения с большим буфером
                sf2_file = open(sf2_path, 'rb', buffering=1024*1024)  # 1MB buffer
                
                # Проверка заголовка RIFF
                sf2_file.seek(0)
                header = sf2_file.read(12)
                if len(header) < 12 or header[:4] != b'RIFF' or header[8:12] != b'sfbk':
                    raise ValueError(f"Некорректный формат SoundFont файла: {sf2_path}")
                
                # Определение размера файла
                file_size = struct.unpack('<I', header[4:8])[0] + 8
                
                # Создаем менеджер для этого файла
                manager = {
                    'path': sf2_path,
                    'file': sf2_file,
                    'priority': i,  # Приоритет по порядку загрузки
                    'presets': [],
                    'instruments': [],
                    'sample_headers': [],
                    'bank_instruments': {}
                }
                
                # Парсинг чанков
                self._parse_chunks_for_manager(manager, 12, file_size)
                
                # Проверяем, что файл корректен
                if not manager['presets'] or not manager['instruments'] or not manager['sample_headers']:
                    raise ValueError(f"Некорректный файл SoundFont: отсутствуют необходимые данные в {sf2_path}")
                
                self.sf2_managers.append(manager)
                
            except Exception as e:
                print(f"Ошибка при загрузке SF2 файла {sf2_path}: {str(e)}")
                if 'sf2_file' in locals() and not sf2_file.closed:
                    sf2_file.close()

    def _parse_structure(self):
        """Парсинг структуры файла SoundFont (устаревший метод, оставлен для совместимости)"""
        pass

    def _parse_chunks_for_manager(self, manager: Dict[str, Any], start_offset: int, end_offset: int):
        """Оптимизированный парсинг чанков SoundFont файла"""
        sf2_file = manager['file']
        sf2_file.seek(start_offset)
        
        # Предварительно читаем большой блок данных для уменьшения количества операций чтения
        file_data = sf2_file.read(min(1024*1024, end_offset - start_offset))  # 1MB или до конца
        data_offset = start_offset
        pos = 0
        
        while pos < len(file_data) - 8:
            # Чтение заголовка чанка из буфера
            if pos + 8 > len(file_data):
                break
                
            chunk_id = file_data[pos:pos+4]
            chunk_size_bytes = file_data[pos+4:pos+8]
            if len(chunk_size_bytes) < 4:
                break
            chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
            
            # Переход к данным чанка
            pos += 8
            chunk_end = pos + chunk_size
            
            # Обработка LIST-чанков
            if chunk_id == b'LIST':
                if pos + 4 > len(file_data):
                    break
                list_type = file_data[pos:pos+4]
                pos += 4
                
                # Обработка вложенных чанков
                if list_type == b'pdta':
                    # Обработка параметрических данных
                    self._parse_pdta_chunk_for_manager(manager, file_data, pos, chunk_end, data_offset)
                elif list_type == b'sdta':
                    # Обработка аудиоданных
                    self._parse_sdta_chunk_for_manager(manager, file_data, pos, chunk_end, data_offset)
                # Для других LIST-чанков пропускаем содержимое
                
                pos = chunk_end
            else:
                # Обработка обычных чанков
                chunk_data = file_data[pos:chunk_end] if chunk_end <= len(file_data) else None
                
                if chunk_id == b'phdr':
                    self._parse_phdr_chunk_data(manager, chunk_data)
                elif chunk_id == b'pbag':
                    self._parse_pbag_chunk_data(manager, chunk_data)
                elif chunk_id == b'pmod':
                    self._parse_pmod_chunk_data(manager, chunk_data)
                elif chunk_id == b'pgen':
                    self._parse_pgen_chunk_data(manager, chunk_data)
                elif chunk_id == b'inst':
                    self._parse_inst_chunk_data(manager, chunk_data)
                elif chunk_id == b'ibag':
                    self._parse_ibag_chunk_data(manager, chunk_data)
                elif chunk_id == b'imod':
                    self._parse_imod_chunk_data(manager, chunk_data)
                elif chunk_id == b'igen':
                    self._parse_igen_chunk_data(manager, chunk_data)
                elif chunk_id == b'shdr':
                    self._parse_shdr_chunk_data(manager, chunk_data)
                
                pos = chunk_end
            
            # Выравнивание до четного числа байт
            if chunk_size % 2 != 0:
                pos += 1

    def _parse_pdta_chunk_for_manager(self, manager: Dict[str, Any], file_data: bytes, start_pos: int, end_pos: int, data_offset: int):
        """Оптимизированный парсинг параметрических данных"""
        pos = start_pos
        
        while pos < end_pos - 8:
            if pos + 8 > len(file_data):
                break
                
            subchunk_id = file_data[pos:pos+4]
            subchunk_size_bytes = file_data[pos+4:pos+8]
            if len(subchunk_size_bytes) < 4:
                break
            subchunk_size = struct.unpack('<I', subchunk_size_bytes)[0]
            
            pos += 8
            subchunk_end = pos + subchunk_size
            subchunk_data = file_data[pos:subchunk_end] if subchunk_end <= len(file_data) else None
            
            # Обработка подчанков
            if subchunk_id == b'phdr':
                self._parse_phdr_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'pbag':
                self._parse_pbag_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'pmod':
                self._parse_pmod_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'pgen':
                self._parse_pgen_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'inst':
                self._parse_inst_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'ibag':
                self._parse_ibag_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'imod':
                self._parse_imod_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'igen':
                self._parse_igen_chunk_data(manager, subchunk_data)
            elif subchunk_id == b'shdr':
                self._parse_shdr_chunk_data(manager, subchunk_data)
            
            pos = subchunk_end
            
            # Выравнивание
            if subchunk_size % 2 != 0:
                pos += 1

    def _parse_sdta_chunk_for_manager(self, manager: Dict[str, Any], file_data: bytes, start_pos: int, end_pos: int, data_offset: int):
        """Оптимизированный парсинг аудиоданных"""
        pos = start_pos
        
        while pos < end_pos - 8:
            if pos + 8 > len(file_data):
                break
                
            subchunk_id = file_data[pos:pos+4]
            subchunk_size_bytes = file_data[pos+4:pos+8]
            if len(subchunk_size_bytes) < 4:
                break
            subchunk_size = struct.unpack('<I', subchunk_size_bytes)[0]
            
            pos += 8
            
            # Обработка подчанков аудиоданных
            if subchunk_id == b'smpl':
                manager['smpl_data_offset'] = data_offset + pos
                manager['smpl_data_size'] = subchunk_size
                # Не читаем данные сейчас, будем читать по требованию
                break  # Обычно только один smpl чанк
            
            pos += subchunk_size
            
            # Выравнивание
            if subchunk_size % 2 != 0:
                pos += 1

    # Оптимизированные методы парсинга данных
    def _parse_phdr_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг заголовков пресетов"""
        if chunk_data is None:
            return
            
        presets = manager['presets']
        num_presets = len(chunk_data) // 38
        
        for i in range(num_presets - 1):  # Последний пресет - терминальный
            offset = i * 38
            if offset + 38 > len(chunk_data):
                break
                
            preset_data = chunk_data[offset:offset+38]
            
            # Извлечение данных одним вызовом unpack
            name_bytes = preset_data[:20]
            preset_vals = struct.unpack('<20sHHHLLL', preset_data[:38])
            
            # Извлечение имени
            name = preset_vals[0].split(b'\x00')[0].decode('ascii', 'ignore')
            
            # Создаем пресет
            sf2_preset = SF2Preset()
            sf2_preset.name = name
            sf2_preset.preset = preset_vals[1]
            sf2_preset.bank = preset_vals[2]
            sf2_preset.preset_bag_index = preset_vals[3]
            presets.append(sf2_preset)

    def _parse_pbag_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг заголовков зон пресетов"""
        if chunk_data is None or len(chunk_data) < 4:
            return
            
        presets = manager['presets']
        num_zones = len(chunk_data) // 4
        
        # Предварительно читаем все индексы
        zone_indices = []
        for i in range(num_zones - 1):  # Последняя зона - терминальная
            offset = i * 4
            if offset + 4 > len(chunk_data):
                break
            gen_ndx, mod_ndx = struct.unpack('<HH', chunk_data[offset:offset+4])
            zone_indices.append((gen_ndx, mod_ndx))
        
        # Привязываем зоны к пресетам
        for i, preset in enumerate(presets):
            start_idx = preset.preset_bag_index
            end_idx = presets[i+1].preset_bag_index if i < len(presets) - 1 else num_zones - 1
            
            for j in range(start_idx, min(end_idx, len(zone_indices))):
                gen_ndx, mod_ndx = zone_indices[j]
                
                preset_zone = SF2PresetZone()
                preset_zone.preset = preset.preset
                preset_zone.bank = preset.bank
                preset_zone.instrument_index = 0
                preset_zone.instrument_name = ""
                preset_zone.gen_ndx = gen_ndx
                preset_zone.mod_ndx = mod_ndx
                preset.zones.append(preset_zone)

    def _parse_pgen_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг генераторов пресетов"""
        if chunk_data is None or len(chunk_data) < 4:
            return
            
        presets = manager['presets']
        instruments = manager['instruments']
        num_gens = len(chunk_data) // 4
        
        # Предварительно читаем все генераторы
        generators = []
        for i in range(num_gens):
            offset = i * 4
            if offset + 4 > len(chunk_data):
                break
            gen_type, gen_amount = struct.unpack('<Hh', chunk_data[offset:offset+4])
            generators.append((gen_type, gen_amount))
        
        # Привязываем генераторы к зонам пресетов
        for preset in presets:
            for zone in preset.zones:
                start_idx = zone.gen_ndx
                # Ищем терминальную зону
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(generators)):
                    if generators[i][0] == 0:  # Терминальный генератор
                        end_idx = i
                        break
                
                # Обрабатываем генераторы
                for j in range(start_idx, min(end_idx, len(generators))):
                    gen_type, gen_amount = generators[j]
                    
                    if gen_type == 41:  # instrument
                        zone.instrument_index = gen_amount
                        if zone.instrument_index < len(instruments):
                            zone.instrument_name = instruments[zone.instrument_index].name
                    elif gen_type == 42:  # keyRange
                        zone.lokey = gen_amount & 0xFF
                        zone.hikey = (gen_amount >> 8) & 0xFF
                    elif gen_type == 43:  # velRange
                        zone.lovel = gen_amount & 0xFF
                        zone.hivel = (gen_amount >> 8) & 0xFF
                    elif gen_type == 12:  # initialFilterFc
                        zone.initialFilterFc = gen_amount
                    elif gen_type == 13:  # initialFilterQ
                        zone.initial_filterQ = gen_amount
                    elif gen_type == 21:  # pan
                        zone.Pan = gen_amount
                    elif gen_type == 22:  # delayModLFO
                        zone.DelayLFO1 = gen_amount
                    elif gen_type == 23:  # freqModLFO
                        zone.LFO1Freq = gen_amount
                    elif gen_type == 24:  # delayVibLFO
                        zone.DelayLFO2 = gen_amount
                    elif gen_type == 26:  # delayModEnv
                        zone.DelayFilEnv = gen_amount
                    elif gen_type == 27:  # attackModEnv
                        zone.AttackFilEnv = gen_amount
                    elif gen_type == 28:  # holdModEnv
                        zone.HoldFilEnv = gen_amount
                    elif gen_type == 29:  # decayModEnv
                        zone.DecayFilEnv = gen_amount
                    elif gen_type == 30:  # sustainModEnv
                        zone.SustainFilEnv = gen_amount
                    elif gen_type == 31:  # releaseModEnv
                        zone.ReleaseFilEnv = gen_amount
                    elif gen_type == 32:  # keynumToModEnvHold
                        zone.KeynumToModEnvHold = gen_amount
                    elif gen_type == 33:  # keynumToModEnvDecay
                        zone.KeynumToModEnvDecay = gen_amount
                    elif gen_type == 34:  # delayVolEnv
                        zone.DelayVolEnv = gen_amount
                    elif gen_type == 35:  # attackVolEnv
                        zone.AttackVolEnv = gen_amount
                    elif gen_type == 36:  # holdVolEnv
                        zone.HoldVolEnv = gen_amount
                    elif gen_type == 37:  # decayVolEnv
                        zone.DecayVolEnv = gen_amount
                    elif gen_type == 38:  # sustainVolEnv
                        zone.SustainVolEnv = gen_amount
                    elif gen_type == 39:  # releaseVolEnv
                        zone.ReleaseVolEnv = gen_amount
                    elif gen_type == 40:  # keynumToVolEnvHold
                        zone.KeynumToVolEnvHold = gen_amount
                    elif gen_type == 41:  # keynumToVolEnvDecay
                        zone.KeynumToVolEnvDecay = gen_amount

    def _parse_pmod_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг модуляторов пресетов"""
        if chunk_data is None or len(chunk_data) < 10:
            return
            
        presets = manager['presets']
        num_modulators = len(chunk_data) // 10
        
        # Предварительно читаем все модуляторы
        modulators = []
        for i in range(num_modulators):
            offset = i * 10
            if offset + 10 > len(chunk_data):
                break
            mod_data = chunk_data[offset:offset+10]
            
            # Распаковываем все поля одним вызовом
            vals = struct.unpack('<HHHHhH', mod_data)
            
            modulator = SF2Modulator()
            modulator.source_oper = vals[0] & 0x000F
            modulator.source_polarity = (vals[0] & 0x0010) >> 4
            modulator.source_type = (vals[0] & 0x0020) >> 5
            modulator.source_direction = (vals[0] & 0x0040) >> 6
            modulator.source_index = (vals[0] & 0xFF80) >> 7
            
            modulator.control_oper = vals[1] & 0x000F
            modulator.control_polarity = (vals[1] & 0x0010) >> 4
            modulator.control_type = (vals[1] & 0x0020) >> 5
            modulator.control_direction = (vals[1] & 0x0040) >> 6
            modulator.control_index = (vals[1] & 0xFF80) >> 7
            
            modulator.destination = vals[2]
            modulator.amount = vals[3]
            
            modulator.amount_source_oper = vals[4] & 0x000F
            modulator.amount_source_polarity = (vals[4] & 0x0010) >> 4
            modulator.amount_source_type = (vals[4] & 0x0020) >> 5
            modulator.amount_source_direction = (vals[4] & 0x0040) >> 6
            modulator.amount_source_index = (vals[4] & 0xFF80) >> 7
            
            modulator.transform = vals[5]
            modulators.append(modulator)
        
        # Привязываем модуляторы к зонам пресетов
        for preset in presets:
            for zone in preset.zones:
                start_idx = zone.mod_ndx
                # Ищем терминальную зону
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(modulators)):
                    if modulators[i].source_oper == 0 and modulators[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, min(end_idx, len(modulators))):
                    modulator = modulators[j]
                    zone.modulators.append(modulator)
                    self._process_preset_modulator(zone, modulator)

    def _parse_inst_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг заголовков инструментов"""
        if chunk_data is None:
            return
            
        instruments = manager['instruments']
        num_instruments = len(chunk_data) // 22
        
        for i in range(num_instruments - 1):  # Последний инструмент - терминальный
            offset = i * 22
            if offset + 22 > len(chunk_data):
                break
                
            inst_data = chunk_data[offset:offset+22]
            
            # Извлечение данных
            name_bytes = inst_data[:20]
            inst_bag_ndx = struct.unpack('<H', inst_data[20:22])[0]
            
            # Извлечение имени
            name = name_bytes.split(b'\x00')[0].decode('ascii', 'ignore')
            
            # Создаем инструмент
            sf2_instrument = SF2Instrument()
            sf2_instrument.name = name
            sf2_instrument.instrument_bag_index = inst_bag_ndx
            instruments.append(sf2_instrument)

    def _parse_ibag_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг заголовков зон инструментов"""
        if chunk_data is None or len(chunk_data) < 4:
            return
            
        instruments = manager['instruments']
        num_zones = len(chunk_data) // 4
        
        # Предварительно читаем все индексы
        zone_indices = []
        for i in range(num_zones - 1):  # Последняя зона - терминальная
            offset = i * 4
            if offset + 4 > len(chunk_data):
                break
            gen_ndx, mod_ndx = struct.unpack('<HH', chunk_data[offset:offset+4])
            zone_indices.append((gen_ndx, mod_ndx))
        
        # Привязываем зоны к инструментам
        for i, instrument in enumerate(instruments):
            start_idx = instrument.instrument_bag_index
            end_idx = instruments[i+1].instrument_bag_index if i < len(instruments) - 1 else num_zones - 1
            
            for j in range(start_idx, min(end_idx, len(zone_indices))):
                gen_ndx, mod_ndx = zone_indices[j]
                
                inst_zone = SF2InstrumentZone()
                inst_zone.sample_index = 0
                inst_zone.gen_ndx = gen_ndx
                inst_zone.mod_ndx = mod_ndx
                instrument.zones.append(inst_zone)

    def _parse_igen_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг генераторов инструментов"""
        if chunk_data is None or len(chunk_data) < 4:
            return
            
        instruments = manager['instruments']
        num_gens = len(chunk_data) // 4
        
        # Предварительно читаем все генераторы
        generators = []
        for i in range(num_gens):
            offset = i * 4
            if offset + 4 > len(chunk_data):
                break
            gen_type, gen_amount = struct.unpack('<Hh', chunk_data[offset:offset+4])
            generators.append((gen_type, gen_amount))
        
        # Привязываем генераторы к зонам инструментов
        for instrument in instruments:
            for zone in instrument.zones:
                start_idx = zone.gen_ndx
                # Ищем терминальную зону
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(generators)):
                    if generators[i][0] == 0:  # Терминальный генератор
                        end_idx = i
                        break
                
                # Обрабатываем генераторы
                for j in range(start_idx, min(end_idx, len(generators))):
                    gen_type, gen_amount = generators[j]
                    
                    if gen_type == 53:  # sampleModes
                        zone.sample_modes = gen_amount
                    elif gen_type == 54:  # exclusiveClass
                        zone.exclusive_class = gen_amount
                    elif gen_type == 55:  # overridingRootKey
                        zone.OverridingRootKey = gen_amount
                    elif gen_type == 56:  # sampleID
                        zone.sample_index = gen_amount
                    elif gen_type == 0:  # startAddrs
                        zone.start = gen_amount
                    elif gen_type == 1:  # endAddrs
                        zone.end = gen_amount
                    elif gen_type == 2:  # startloopAddrs
                        zone.start_loop = gen_amount
                    elif gen_type == 3:  # endloopAddrs
                        zone.end_loop = gen_amount
                    elif gen_type == 12:  # initialFilterFc
                        zone.initialFilterFc = gen_amount
                    elif gen_type == 13:  # initialFilterQ
                        zone.initial_filterQ = gen_amount
                    elif gen_type == 21:  # pan
                        zone.Pan = gen_amount
                    elif gen_type == 26:  # delayModEnv
                        zone.DelayFilEnv = gen_amount
                    elif gen_type == 27:  # attackModEnv
                        zone.AttackFilEnv = gen_amount
                    elif gen_type == 28:  # holdModEnv
                        zone.HoldFilEnv = gen_amount
                    elif gen_type == 29:  # decayModEnv
                        zone.DecayFilEnv = gen_amount
                    elif gen_type == 30:  # sustainModEnv
                        zone.SustainFilEnv = gen_amount
                    elif gen_type == 31:  # releaseModEnv
                        zone.ReleaseFilEnv = gen_amount
                    elif gen_type == 32:  # keynumToModEnvHold
                        zone.KeynumToModEnvHold = gen_amount
                    elif gen_type == 33:  # keynumToModEnvDecay
                        zone.KeynumToModEnvDecay = gen_amount
                    elif gen_type == 34:  # delayVolEnv
                        zone.DelayVolEnv = gen_amount
                    elif gen_type == 35:  # attackVolEnv
                        zone.AttackVolEnv = gen_amount
                    elif gen_type == 36:  # holdVolEnv
                        zone.HoldVolEnv = gen_amount
                    elif gen_type == 37:  # decayVolEnv
                        zone.DecayVolEnv = gen_amount
                    elif gen_type == 38:  # sustainVolEnv
                        zone.SustainVolEnv = gen_amount
                    elif gen_type == 39:  # releaseVolEnv
                        zone.ReleaseVolEnv = gen_amount
                    elif gen_type == 42:  # keyRange
                        zone.lokey = gen_amount & 0xFF
                        zone.hikey = (gen_amount >> 8) & 0xFF
                    elif gen_type == 43:  # velRange
                        zone.lovel = gen_amount & 0xFF
                        zone.hivel = (gen_amount >> 8) & 0xFF
                    elif gen_type == 50:  # coarseTune
                        zone.CoarseTune = gen_amount
                    elif gen_type == 51:  # fineTune
                        zone.FineTune = gen_amount
                    elif gen_type == 5:  # modLfoToPitch
                        zone.mod_lfo_to_pitch = gen_amount
                    elif gen_type == 6:  # vibLfoToPitch
                        zone.vib_lfo_to_pitch = gen_amount
                    elif gen_type == 7:  # modEnvToPitch
                        zone.mod_env_to_pitch = gen_amount
                    elif gen_type == 10:  # modLfoToFilterFc
                        zone.mod_lfo_to_filter = gen_amount
                    elif gen_type == 11:  # modEnvToFilterFc
                        zone.mod_env_to_filter = gen_amount
                    elif gen_type == 13:  # modLfoToVolume
                        zone.mod_lfo_to_volume = gen_amount
                    elif gen_type == 36:  # keynumToVolEnvHold
                        zone.KeynumToVolEnvHold = gen_amount
                    elif gen_type == 37:  # keynumToVolEnvDecay
                        zone.KeynumToVolEnvDecay = gen_amount

    def _parse_imod_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг модуляторов инструментов"""
        if chunk_data is None or len(chunk_data) < 10:
            return
            
        instruments = manager['instruments']
        num_modulators = len(chunk_data) // 10
        
        # Предварительно читаем все модуляторы
        modulators = []
        for i in range(num_modulators):
            offset = i * 10
            if offset + 10 > len(chunk_data):
                break
            mod_data = chunk_data[offset:offset+10]
            
            # Распаковываем все поля одним вызовом
            vals = struct.unpack('<HHHHhH', mod_data)
            
            modulator = SF2Modulator()
            modulator.source_oper = vals[0] & 0x000F
            modulator.source_polarity = (vals[0] & 0x0010) >> 4
            modulator.source_type = (vals[0] & 0x0020) >> 5
            modulator.source_direction = (vals[0] & 0x0040) >> 6
            modulator.source_index = (vals[0] & 0xFF80) >> 7
            
            modulator.control_oper = vals[1] & 0x000F
            modulator.control_polarity = (vals[1] & 0x0010) >> 4
            modulator.control_type = (vals[1] & 0x0020) >> 5
            modulator.control_direction = (vals[1] & 0x0040) >> 6
            modulator.control_index = (vals[1] & 0xFF80) >> 7
            
            modulator.destination = vals[2]
            modulator.amount = vals[3]
            
            modulator.amount_source_oper = vals[4] & 0x000F
            modulator.amount_source_polarity = (vals[4] & 0x0010) >> 4
            modulator.amount_source_type = (vals[4] & 0x0020) >> 5
            modulator.amount_source_direction = (vals[4] & 0x0040) >> 6
            modulator.amount_source_index = (vals[4] & 0xFF80) >> 7
            
            modulator.transform = vals[5]
            modulators.append(modulator)
        
        # Привязываем модуляторы к зонам инструментов
        for instrument in instruments:
            for zone in instrument.zones:
                start_idx = zone.mod_ndx
                # Ищем терминальную зону
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(modulators)):
                    if modulators[i].source_oper == 0 and modulators[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, min(end_idx, len(modulators))):
                    modulator = modulators[j]
                    zone.modulators.append(modulator)
                    self._process_instrument_modulator(zone, modulator)

    def _parse_shdr_chunk_data(self, manager: Dict[str, Any], chunk_data: Optional[bytes]):
        """Оптимизированный парсинг заголовков сэмплов"""
        if chunk_data is None:
            return
            
        sample_headers = manager['sample_headers']
        num_samples = len(chunk_data) // 46
        
        for i in range(num_samples - 1):  # Последний сэмпл - терминальный
            offset = i * 46
            if offset + 46 > len(chunk_data):
                break
                
            sample_data = chunk_data[offset:offset+46]
            
            # Извлечение данных одним вызовом unpack
            vals = struct.unpack('<20sIIIIIBbHH', sample_data)
            
            # Извлечение имени
            name = vals[0].split(b'\x00')[0].decode('ascii', 'ignore')
            
            # Создаем заголовок сэмпла
            sample_header = SF2SampleHeader()
            sample_header.name = name
            sample_header.start = vals[1]
            sample_header.end = vals[2]
            sample_header.start_loop = vals[3]
            sample_header.end_loop = vals[4]
            sample_header.sample_rate = vals[5]
            sample_header.original_pitch = vals[6]
            sample_header.pitch_correction = vals[7]
            sample_header.link = vals[8]
            sample_header.type = vals[9]
            sample_headers.append(sample_header)

    # Остальные методы остаются без изменений для совместимости
    def _process_preset_modulator(self, zone: SF2PresetZone, modulator: SF2Modulator):
        """Обработка модулятора пресета для извлечения полезных параметров"""
        # Определяем источник модуляции
        source_name = self._get_modulator_source_name(modulator)
        
        # Определяем цель модуляции
        destination = modulator.destination
        
        # Глубина модуляции (нормализуем)
        amount = self._normalize_modulator_amount(modulator.amount, destination)
        
        # Определяем полярность
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0
        
        # Обработка часто используемых модуляций
        if destination == 7:  # modEnvToPitch
            zone.velocity_to_pitch = amount * polarity
        elif destination == 5:  # modLfoToPitch
            zone.lfo_to_pitch = amount * polarity
        elif destination == 6:  # vibLfoToPitch
            zone.lfo_to_pitch = amount * polarity
            zone.vibrato_depth = amount * polarity  # Добавляем специфический параметр для вибрато
        elif destination == 8:  # initialFilterFc
            if source_name == "note_on_velocity":
                zone.velocity_to_filter = amount * polarity
            elif source_name == "channel_aftertouch":
                zone.aftertouch_to_filter = amount * polarity
            elif source_name == "cc_mod_wheel":
                zone.mod_wheel_to_filter = amount * polarity
            elif source_name == "cc_brightness":
                zone.brightness_to_filter = amount * polarity
        elif destination == 10:  # modLfoToFilterFc
            zone.lfo_to_filter = amount * polarity
        elif destination == 11:  # modEnvToFilterFc
            if source_name == "note_on_velocity":
                zone.velocity_to_filter = amount * polarity
        elif destination == 13:  # modLfoToVolume
            zone.tremolo_depth = amount * polarity
        elif destination == 17:  # pan
            # Обработка модуляции панорамирования
            pass
        elif destination == 77:  # cc_tremolo_depth
            zone.tremolo_depth = amount * polarity
        elif destination == 78:  # cc_tremolo_rate
            # Обработка скорости трепета
            pass
        elif destination == 84:  # cc_portamento_control
            zone.portamento_to_pitch = amount * polarity

    def _process_instrument_modulator(self, zone: SF2InstrumentZone, modulator: SF2Modulator):
        """Обработка модулятора инструмента для извлечения полезных параметров"""
        # Определяем источник модуляции
        source_name = self._get_modulator_source_name(modulator)
        
        # Определяем цель модуляции
        destination = modulator.destination
        
        # Глубина модуляции (нормализуем)
        amount = self._normalize_modulator_amount(modulator.amount, destination)
        
        # Определяем полярность
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0
        
        # Обработка часто используемых модуляций
        if destination == 7:  # modEnvToPitch
            zone.velocity_to_pitch = amount * polarity
            zone.mod_env_to_pitch = amount * polarity  # Добавляем специфический параметр
        elif destination == 5:  # modLfoToPitch
            zone.lfo_to_pitch = amount * polarity
            zone.mod_lfo_to_pitch = amount * polarity  # Добавляем специфический параметр
        elif destination == 6:  # vibLfoToPitch
            zone.lfo_to_pitch = amount * polarity
            zone.vib_lfo_to_pitch = amount * polarity  # Добавляем специфический параметр
            zone.vibrato_depth = amount * polarity  # Добавляем специфический параметр для вибрато
        elif destination == 8:  # initialFilterFc
            if source_name == "note_on_velocity":
                zone.velocity_to_filter = amount * polarity
            elif source_name == "channel_aftertouch":
                zone.aftertouch_to_filter = amount * polarity
            elif source_name == "cc_mod_wheel":
                zone.mod_wheel_to_filter = amount * polarity
            elif source_name == "cc_brightness":
                zone.brightness_to_filter = amount * polarity
        elif destination == 10:  # modLfoToFilterFc
            zone.lfo_to_filter = amount * polarity
            zone.mod_lfo_to_filter = amount * polarity  # Добавляем специфический параметр
        elif destination == 11:  # modEnvToFilterFc
            if source_name == "note_on_velocity":
                zone.velocity_to_filter = amount * polarity
            zone.mod_env_to_filter = amount * polarity  # Добавляем специфический параметр
        elif destination == 13:  # modLfoToVolume
            zone.tremolo_depth = amount * polarity
            zone.mod_lfo_to_volume = amount * polarity  # Добавляем специфический параметр
        elif destination == 17:  # pan
            # Обработка модуляции панорамирования
            pass
        elif destination == 22:  # delayModEnv
            # Обработка задержки модуляционной огибающей
            pass
        elif destination == 23:  # attackModEnv
            # Обработка атаки модуляционной огибающей
            pass
        elif destination == 24:  # holdModEnv
            # Обработка hold модуляционной огибающей
            pass
        elif destination == 25:  # decayModEnv
            # Обработка спада модуляционной огибающей
            pass
        elif destination == 26:  # sustainModEnv
            # Обработка sustain модуляционной огибающей
            pass
        elif destination == 27:  # releaseModEnv
            # Обработка релиза модуляционной огибающей
            pass
        elif destination == 28:  # keynumToModEnvHold
            # Обработка keynum to mod env hold
            pass
        elif destination == 29:  # keynumToModEnvDecay
            # Обработка keynum to mod env decay
            pass
        elif destination == 30:  # delayVolEnv
            # Обработка задержки амплитудной огибающей
            pass
        elif destination == 31:  # attackVolEnv
            # Обработка атаки амплитудной огибающей
            pass
        elif destination == 32:  # holdVolEnv
            # Обработка hold амплитудной огибающей
            pass
        elif destination == 33:  # decayVolEnv
            # Обработка спада амплитудной огибающей
            pass
        elif destination == 34:  # sustainVolEnv
            # Обработка sustain амплитудной огибающей
            pass
        elif destination == 35:  # releaseVolEnv
            # Обработка релиза амплитудной огибающей
            pass
        elif destination == 36:  # keynumToVolEnvHold
            # Обработка keynum to vol env hold
            pass
        elif destination == 37:  # keynumToVolEnvDecay
            # Обработка keynum to vol env decay
            pass
        elif destination == 77:  # cc_tremolo_depth
            zone.tremolo_depth = amount * polarity
        elif destination == 78:  # cc_tremolo_rate
            # Обработка скорости трепета
            pass
        elif destination == 84:  # cc_portamento_control
            zone.portamento_to_pitch = amount * polarity

    def _get_modulator_source_name(self, modulator: SF2Modulator) -> str:
        """Получение имени источника модуляции"""
        # Сначала проверяем основной источник
        if modulator.source_oper in self.SF2_SOURCE_OPERATORS:
            source_name = self.SF2_SOURCE_OPERATORS[modulator.source_oper]
            
            # Для CC контроллеров добавляем индекс
            if source_name.startswith("cc_"):
                if modulator.source_index > 0:
                    return f"{source_name}_{modulator.source_index}"
                return source_name
            
            return source_name
        
        # Для LFO
        if modulator.source_oper == 5:
            return "modLFO"
        elif modulator.source_oper == 6:
            return "vibLFO"
        
        # Для огибающих
        if modulator.source_oper == 7:
            return "modEnv"
        elif modulator.source_oper == 13:
            return "channel_aftertouch"
        
        return "unknown_source"

    def _normalize_modulator_amount(self, amount: int, destination: int) -> float:
        """
        Нормализация глубины модуляции в зависимости от цели.
        
        Args:
            amount: исходное значение глубины модуляции
            destination: цель модуляции
            
        Returns:
            нормализованное значение глубины модуляции
        """
        # Для pitch модуляции (в центах)
        if destination in [5, 6, 7]:
            return abs(amount) / 100.0  # 100 = 1 цент
        
        # Для cutoff фильтра
        elif destination in [8, 10, 11]:
            return abs(amount) / 1000.0  # Нормализуем к 0-1
        
        # Для амплитуды
        elif destination in [13, 31, 33, 34, 35]:
            return abs(amount) / 1000.0  # Нормализуем к 0-1
        
        # Для панорамирования
        elif destination == 17:
            return abs(amount) / 100.0  # 0-100 в SoundFont -> 0-1
        
        # Для трепета (tremolo)
        elif destination in [77, 78]:
            return abs(amount) / 1000.0  # Нормализуем к 0-1
        
        # Для других целей
        else:
            return abs(amount) / 1000.0  # Общая нормализация

    def _build_global_preset_map(self):
        """Собираем все пресеты из всех SF2 файлов в один глобальный список с приоритетами"""
        # Очищаем глобальные структуры
        self.presets.clear()
        self.instruments.clear()
        self.sample_headers.clear()
        self.bank_instruments.clear()
        
        # Собираем все пресеты с учетом приоритетов
        all_presets = []
        
        for manager in self.sf2_managers:
            sf2_path = manager['path']
            presets = manager['presets']
            
            # Получаем настройки для этого SF2 файла
            bank_blacklist = self.bank_blacklists.get(sf2_path, [])
            preset_blacklist = self.preset_blacklists.get(sf2_path, [])
            bank_mapping = self.bank_mappings.get(sf2_path, {})
            
            for i, preset in enumerate(presets):
                # Применяем черный список банков
                if preset.bank in bank_blacklist:
                    continue
                
                # Применяем черный список пресетов
                if (preset.bank, preset.preset) in preset_blacklist:
                    continue
                
                # Применяем маппинг банков
                mapped_bank = bank_mapping.get(preset.bank, preset.bank)
                
                # Добавляем информацию о приоритете и источнике
                all_presets.append({
                    'preset': preset,
                    'manager': manager,
                    'original_bank': preset.bank,
                    'mapped_bank': mapped_bank,
                    'priority': manager['priority']
                })
        
        # Сортируем по приоритету (меньше значение = выше приоритет)
        all_presets.sort(key=lambda x: x['priority'])
        
        # Строим финальную карту с учетом приоритетов
        preset_index = 0
        for preset_info in all_presets:
            preset = preset_info['preset']
            mapped_bank = preset_info['mapped_bank']
            
            # Проверяем, есть ли уже пресет с таким банком и программой
            if mapped_bank not in self.bank_instruments:
                self.bank_instruments[mapped_bank] = {}
            
            # Если пресет еще не добавлен, добавляем его
            if preset.preset not in self.bank_instruments[mapped_bank]:
                self.bank_instruments[mapped_bank][preset.preset] = preset_index
                self.presets.append(preset)
                preset_index += 1

    # Остальные методы остаются без изменений для функциональности
    def get_program_parameters(self, program: int, bank: int = 0) -> dict:
        """
        Получение параметров программы в формате, совместимом с XGToneGenerator.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            словарь с параметрами программы
        """
        # Найти пресет и его менеджер по банку и программе
        preset_idx = self._find_preset_index(program, bank)
        if preset_idx is None:
            # Возвращаем параметры по умолчанию
            return self._get_default_parameters()
        
        preset = self.presets[preset_idx]
        
        # Определяем, из какого менеджера взят этот пресет
        manager = None
        for mgr in self.sf2_managers:
            for preset_in_mgr in mgr['presets']:
                if (preset_in_mgr.name == preset.name and 
                    preset_in_mgr.preset == preset.preset and 
                    preset_in_mgr.bank == preset.bank):
                    manager = mgr
                    break
            if manager:
                break
        
        # Получаем инструменты из соответствующего менеджера
        instruments = manager['instruments'] if manager else self.instruments
        
        # Собрать все зоны инструментов для этого пресета
        all_zones = []
        for preset_zone in preset.zones:
            if preset_zone.instrument_index < len(instruments):
                instrument = instruments[preset_zone.instrument_index]
                all_zones.extend(instrument.zones)
        
        # Если зон нет, возвращаем параметры по умолчанию
        if not all_zones:
            return self._get_default_parameters()
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in all_zones:
            partial_params = self._convert_zone_to_partial_params(zone)
            partials_params.append(partial_params)
        
        # Базовые параметры
        params = {
            "amp_envelope": self._calculate_average_envelope(
                [p["amp_envelope"] for p in partials_params]
            ),
            "filter_envelope": self._calculate_average_envelope(
                [p["filter_envelope"] for p in partials_params]
            ),
            "pitch_envelope": self._calculate_average_envelope(
                [p["pitch_envelope"] for p in partials_params]
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": {
                "waveform": "sine",
                "rate": self._convert_lfo_rate(all_zones[0].LFO1Freq),
                "depth": 0.5,
                "delay": self._convert_time_cents_to_seconds(all_zones[0].DelayLFO1)
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": self._convert_lfo_rate(all_zones[0].LFO2Freq),
                "depth": 0.3,
                "delay": self._convert_time_cents_to_seconds(all_zones[0].DelayLFO2)
            },
            "lfo3": {
                "waveform": "sawtooth",
                "rate": 0.5,
                "depth": 0.1,
                "delay": 0.5
            },
            "modulation": self._calculate_modulation_params(all_zones),
            "partials": partials_params
        }
        
        return params

    def _convert_time_cents_to_seconds(self, time_cents: int) -> float:
        """
        Преобразование временных параметров из SoundFont в секунды.
        Использует правильную логарифмическую шкалу SoundFont 2.0.
        
        Args:
            time_cents: значение в time cents
            
        Returns:
            время в секундах
        """
        if time_cents <= 0:
            return 0.001  # минимальное значение
        
        # SoundFont использует формулу: time = 0.001 * 10^(value/1200)
        return 0.001 * (10 ** (time_cents / 1200.0))

    def _convert_lfo_rate(self, lfo_value: int) -> float:
        """Преобразование значения LFO rate из SoundFont в Гц"""
        if lfo_value <= 0:
            return 0.1  # минимальная скорость
        
        # SoundFont использует логарифмическую шкалу
        return (10 ** (lfo_value / 1200.0)) * 0.01

    def _convert_lfo_delay(self, delay_value: int) -> float:
        """Преобразование значения LFO delay из SoundFont в секунды"""
        if delay_value <= 0:
            return 0.0
        
        # SoundFont использует логарифмическую шкалу
        return (10 ** (delay_value / 1200.0)) * self.TIME_CENTISECONDS_TO_SECONDS

    def _calculate_modulation_params(self, zones: List[SF2InstrumentZone]) -> dict:
        """Рассчитывает параметры модуляции из зон"""
        # Начальные значения
        params = {
            "lfo1_to_pitch": 0.0,
            "lfo2_to_pitch": 0.0,
            "lfo3_to_pitch": 0.0,
            "env_to_pitch": 0.0,
            "aftertouch_to_pitch": 0.0,
            "lfo_to_filter": 0.0,
            "env_to_filter": 0.0,
            "aftertouch_to_filter": 0.0,
            "tremolo_depth": 0.0,
            "vibrato_depth": 0.0,
            "vibrato_rate": 5.0,
            "vibrato_delay": 0.0
        }
        
        # Собираем данные из всех зон
        for zone in zones:
            params["lfo1_to_pitch"] += zone.lfo_to_pitch
            params["env_to_pitch"] += zone.velocity_to_pitch
            params["aftertouch_to_pitch"] += zone.aftertouch_to_pitch
            params["lfo_to_filter"] += zone.lfo_to_filter
            params["env_to_filter"] += zone.velocity_to_filter
            params["aftertouch_to_filter"] += zone.aftertouch_to_filter
            params["tremolo_depth"] += zone.tremolo_depth
            params["vibrato_depth"] += zone.vibrato_depth
            
            # Дополнительные параметры для вибрато
            if hasattr(zone, 'vib_lfo_to_pitch'):
                params["vibrato_depth"] += zone.vib_lfo_to_pitch
            if hasattr(zone, 'LFO2Freq'):
                params["vibrato_rate"] = self._convert_lfo_rate(zone.LFO2Freq)
            if hasattr(zone, 'DelayLFO2'):
                params["vibrato_delay"] = self._convert_time_cents_to_seconds(zone.DelayLFO2)
        
        # Нормализуем по количеству зон
        num_zones = len(zones)
        if num_zones > 0:
            for key in params:
                if key not in ["vibrato_rate", "vibrato_delay"]:  # Эти параметры не нормализуем
                    params[key] /= num_zones
                # Ограничиваем разумными значениями
                if key not in ["vibrato_rate", "vibrato_delay"]:
                    params[key] = max(0.0, min(1.0, params[key]))
        
        return params

    def get_drum_parameters(self, note: int, program: int, bank: int = 128) -> dict:
        """
        Получение параметров барабана в формате, совместимом с XGToneGenerator.
        
        Args:
            note: MIDI нота (0-127)
            program: номер программы (обычно 0 для барабанов)
            bank: номер банка (обычно 128 для барабанов)
            
        Returns:
            словарь с параметрами барабана
        """
        # Для барабанов используем специальный банк (128)
        preset_idx = self._find_preset_index(program, bank)
        if preset_idx is None:
            # Пытаемся найти в банке 0
            preset_idx = self._find_preset_index(program, 0)
            if preset_idx is None:
                return self._get_default_drum_parameters(note)
        
        preset = self.presets[preset_idx]
        
        # Определяем, из какого менеджера взят этот пресет
        manager = None
        for mgr in self.sf2_managers:
            for preset_in_mgr in mgr['presets']:
                if (preset_in_mgr.name == preset.name and 
                    preset_in_mgr.preset == preset.preset and 
                    preset_in_mgr.bank == preset.bank):
                    manager = mgr
                    break
            if manager:
                break
        
        # Получаем инструменты из соответствующего менеджера
        instruments = manager['instruments'] if manager else self.instruments
        
        # Найти зоны, соответствующие этой ноте
        matching_zones = []
        for preset_zone in preset.zones:
            if preset_zone.lokey <= note <= preset_zone.hikey:
                if preset_zone.instrument_index < len(instruments):
                    instrument = instruments[preset_zone.instrument_index]
                    for zone in instrument.zones:
                        if zone.lokey <= note <= zone.hikey:
                            matching_zones.append(zone)
        
        # Если не найдено подходящих зон, возвращаем параметры по умолчанию
        if not matching_zones:
            return self._get_default_drum_parameters(note)
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in matching_zones:
            partial_params = self._convert_zone_to_partial_params(zone, is_drum=True)
            partial_params["key_range_low"] = note
            partial_params["key_range_high"] = note
            partials_params.append(partial_params)
        
        # Базовые параметры для барабанов
        params = {
            "amp_envelope": self._calculate_average_envelope(
                [p["amp_envelope"] for p in partials_params]
            ),
            "filter_envelope": self._calculate_average_envelope(
                [p["filter_envelope"] for p in partials_params]
            ),
            "pitch_envelope": self._calculate_average_envelope(
                [p["pitch_envelope"] for p in partials_params]
            ),
            "filter": self._calculate_average_filter(
                [p["filter"] for p in partials_params]
            ),
            "lfo1": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "modulation": self._calculate_modulation_params(matching_zones),
            "partials": partials_params
        }
        
        return params

    def get_partial_table(self, note: int, program: int, partial_id: int, 
                         velocity: int, bank: int = 0) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Получение сэмпла для частичной структуры.
        
        Args:
            note: MIDI нота (0-127)
            program: номер программы (0-127)
            partial_id: идентификатор частичной структуры
            velocity: скорость нажатия (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            список сэмплов или список кортежей (левый, правый) для стерео
        """
        # Определяем, барабан ли это
        is_drum = (bank == 128)
        
        # Найти пресет и его менеджер
        preset_idx = self._find_preset_index(program, bank)
        if preset_idx is None:
            return None
        
        preset = self.presets[preset_idx]
        
        # Определяем, из какого менеджера взят этот пресет
        manager = None
        for mgr in self.sf2_managers:
            for preset_in_mgr in mgr['presets']:
                if (preset_in_mgr.name == preset.name and 
                    preset_in_mgr.preset == preset.preset and 
                    preset_in_mgr.bank == preset.bank):
                    manager = mgr
                    break
            if manager:
                break
        
        # Получаем инструменты и заголовки сэмплов из соответствующего менеджера
        instruments = manager['instruments'] if manager else self.instruments
        sample_headers = manager['sample_headers'] if manager else self.sample_headers
        
        # Собрать все подходящие зоны
        matching_zones = []
        for preset_zone in preset.zones:
            if (preset_zone.lokey <= note <= preset_zone.hikey and
                preset_zone.lovel <= velocity <= preset_zone.hivel):
                
                if preset_zone.instrument_index < len(instruments):
                    instrument = instruments[preset_zone.instrument_index]
                    for zone in instrument.zones:
                        if (zone.lokey <= note <= zone.hikey and
                            zone.lovel <= velocity <= zone.hivel):
                            matching_zones.append(zone)
        
        # Если нет подходящих зон или запрошенная частичная структура отсутствует, возвращаем None
        if not matching_zones or partial_id >= len(matching_zones):
            return None
        
        # Получаем нужную зону
        zone = matching_zones[partial_id]
        
        # Получаем сэмпл
        if zone.sample_index >= len(sample_headers):
            return None
        
        sample_header = sample_headers[zone.sample_index]
        
        # Загружаем сэмпл (из кэша или из файла)
        sample_data = self._load_sample_data(sample_header, manager)
        if sample_data is None:
            return None
        
        # Возвращаем аудио данные
        return sample_data

    def _find_preset_index(self, program: int, bank: int) -> Optional[int]:
        """Поиск индекса пресета по программе и банку"""
        if bank in self.bank_instruments and program in self.bank_instruments[bank]:
            return self.bank_instruments[bank][program]
        return None

    def _convert_zone_to_partial_params(self, zone: SF2InstrumentZone, 
                                       is_drum: bool = False) -> dict:
        """Преобразование зоны SoundFont в параметры частичной структуры"""
        # Преобразование времени (в time cents) в секунды
        def time_cents_to_seconds(time_cents):
            if time_cents <= 0:
                return 0.001  # минимальное значение для избежания деления на ноль
            # SoundFont использует логарифмическую шкалу для времени
            return 0.001 * (10 ** (time_cents / 1200.0))
        
        # Преобразование cutoff фильтра
        cutoff = max(20.0, min(20000.0, zone.initialFilterFc * self.FILTER_CUTOFF_SCALE))
        
        # Преобразование резонанса
        resonance = max(0.0, min(2.0, zone.initial_filterQ * self.FILTER_RESONANCE_SCALE))
        
        # Преобразование панорамирования
        pan = max(0.0, min(1.0, zone.Pan * self.PAN_SCALE))
        
        # Преобразование velocity sensitivity
        velocity_sense = max(0.0, min(2.0, 1.0 + zone.VelocityAttenuation * self.VELOCITY_SENSE_SCALE))
        
        # Преобразование pitch смещения
        pitch_shift = zone.VelocityPitch * self.PITCH_SCALE
        
        # Базовые параметры
        partial_params = {
            "level": 1.0,
            "pan": pan,
            "key_range_low": zone.lokey,
            "key_range_high": zone.hikey,
            "velocity_range_low": zone.lovel,
            "velocity_range_high": zone.hivel,
            "key_scaling": 0.0,
            "velocity_sense": velocity_sense,
            "crossfade_velocity": True,
            "crossfade_note": True,
            "use_filter_env": True,
            "use_pitch_env": True,
            "pitch_shift": pitch_shift,
            "note_crossfade": 0.0,
            "velocity_crossfade": 0.0,
            
            # Амплитудная огибающая
            "amp_envelope": {
                "delay": time_cents_to_seconds(zone.DelayVolEnv),
                "attack": time_cents_to_seconds(zone.AttackVolEnv),
                "hold": time_cents_to_seconds(zone.HoldVolEnv),
                "decay": time_cents_to_seconds(zone.DecayVolEnv),
                "sustain": max(0.0, min(1.0, 1.0 - zone.SustainVolEnv / 1000.0)),
                "release": time_cents_to_seconds(zone.ReleaseVolEnv),
                "key_scaling": zone.KeynumToVolEnvDecay / 1200.0
            },
            
            # Фильтровая огибающая
            "filter_envelope": {
                "delay": time_cents_to_seconds(zone.DelayFilEnv),
                "attack": time_cents_to_seconds(zone.AttackFilEnv),
                "hold": time_cents_to_seconds(zone.HoldFilEnv),
                "decay": time_cents_to_seconds(zone.DecayFilEnv),
                "sustain": max(0.0, min(1.0, 1.0 - zone.SustainFilEnv / 1000.0)),
                "release": time_cents_to_seconds(zone.ReleaseFilEnv),
                "key_scaling": zone.KeynumToModEnvDecay / 1200.0
            },
            
            # Pitch огибающая
            "pitch_envelope": {
                "delay": time_cents_to_seconds(zone.DelayPitchEnv),
                "attack": time_cents_to_seconds(zone.AttackPitchEnv),
                "hold": time_cents_to_seconds(zone.HoldPitchEnv),
                "decay": time_cents_to_seconds(zone.DecayPitchEnv),
                "sustain": max(0.0, min(1.0, 1.0 - zone.SustainPitchEnv / 1000.0)),
                "release": time_cents_to_seconds(zone.ReleasePitchEnv)
            },
            
            # Фильтр
            "filter": {
                "cutoff": cutoff,
                "resonance": resonance,
                "type": "lowpass",
                "key_follow": 0.5
            },
            
            # Настройка высоты
            "coarse_tune": zone.CoarseTune,
            "fine_tune": zone.FineTune
        }
        
        # Для барабанов упрощаем параметры
        if is_drum:
            partial_params["use_filter_env"] = False
            partial_params["use_pitch_env"] = False
            partial_params["amp_envelope"]["attack"] = max(0.001, partial_params["amp_envelope"]["attack"] * 0.1)
            partial_params["amp_envelope"]["decay"] = max(0.01, partial_params["amp_envelope"]["decay"] * 0.5)
            partial_params["amp_envelope"]["sustain"] = 0.0
        
        return partial_params

    def _calculate_average_envelope(self, envelopes: List[dict]) -> dict:
        """Рассчитывает средние значения огибающей из нескольких частичных структур"""
        if not envelopes:
            return {
                "delay": 0.0,
                "attack": 0.01,
                "hold": 0.0,
                "decay": 0.3,
                "sustain": 0.7,
                "release": 0.5,
                "key_scaling": 0.0
            }
        
        total = {"delay": 0.0, "attack": 0.0, "hold": 0.0, "decay": 0.0, "sustain": 0.0, "release": 0.0, "key_scaling": 0.0}
        count = len(envelopes)
        
        for env in envelopes:
            total["delay"] += env["delay"]
            total["attack"] += env["attack"]
            total["hold"] += env["hold"]
            total["decay"] += env["decay"]
            total["sustain"] += env["sustain"]
            total["release"] += env["release"]
            total["key_scaling"] += env.get("key_scaling", 0.0)
        
        return {
            "delay": total["delay"] / count,
            "attack": total["attack"] / count,
            "hold": total["hold"] / count,
            "decay": total["decay"] / count,
            "sustain": total["sustain"] / count,
            "release": total["release"] / count,
            "key_scaling": total["key_scaling"] / count
        }

    def _calculate_average_filter(self, filters: List[dict]) -> dict:
        """Рассчитывает средние значения фильтра из нескольких частичных структур"""
        if not filters:
            return {
                "cutoff": 1000.0,
                "resonance": 0.7,
                "type": "lowpass",
                "key_follow": 0.5
            }
        
        total = {"cutoff": 0.0, "resonance": 0.0}
        count = len(filters)
        
        for f in filters:
            total["cutoff"] += f["cutoff"]
            total["resonance"] += f["resonance"]
        
        return {
            "cutoff": total["cutoff"] / count,
            "resonance": total["resonance"] / count,
            "type": "lowpass",
            "key_follow": 0.5
        }

    def _load_sample_data(self, sample_header: SF2SampleHeader, manager: Optional[Dict[str, Any]] = None) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Загрузка данных сэмпла из файла или кэша.
        
        Args:
            sample_header: заголовок сэмпла
            manager: менеджер SF2 файла (опционально, для многфайлового режима)
            
        Returns:
            Моно: список значений
            Стерео: список кортежей (левый, правый)
        """
        # Проверяем, есть ли сэмпл в кэше
        if sample_header.name in self.sample_cache:
            # Обновляем порядок использования для LRU кэша
            self.sample_cache.move_to_end(sample_header.name)
            return self.sample_cache[sample_header.name]
        
        # Загружаем сэмпл из файла
        sample_data = self._read_sample_from_file(sample_header, manager)
        if sample_data is None:
            return None
        
        # Добавляем в кэш
        self._add_to_cache(sample_header.name, sample_data)
        
        return sample_data

    def _read_sample_from_file(self, sample_header: SF2SampleHeader, manager: Optional[Dict[str, Any]] = None) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Чтение сэмпла из файла.
        
        Args:
            sample_header: заголовок сэмпла
            manager: менеджер SF2 файла (опционально, для многфайлового режима)
            
        Returns:
            Моно: список значений
            Стерео: список кортежей (левый, правый)
        """
        # Определяем, какой файл использовать
        if manager is not None:
            sf2_file = manager['file']
            smpl_data_offset = manager.get('smpl_data_offset')
            smpl_data_size = manager.get('smpl_data_size')
        else:
            # Режим совместимости для одиночного файла
            sf2_file = self.sf2_file if hasattr(self, 'sf2_file') else None
            smpl_data_offset = getattr(self, 'smpl_data_offset', None)
            smpl_data_size = getattr(self, 'smpl_data_size', None)
        
        # Проверяем, есть ли данные о сэмпле
        if smpl_data_offset is None or smpl_data_size is None:
            return None
        
        # Определяем размер сэмпла в сэмплах (не в байтах)
        sample_length = sample_header.end - sample_header.start
        if sample_length <= 0:
            return None
        
        # Определяем тип сэмпла (моно или стерео)
        is_stereo = (sample_header.type & 1) == 0 and (sample_header.type & 2) != 0
        is_right = (sample_header.type & 2) != 0
        is_left = (sample_header.type & 4) != 0
        
        # Вычисляем смещение в файле
        sample_offset = smpl_data_offset + sample_header.start * 2  # Предполагаем 16-битные сэмплы
        
        try:
            # Переходим к началу сэмпла
            sf2_file.seek(sample_offset)
            
            # Читаем данные
            if is_stereo:
                # Для стерео читаем пары значений
                data = sf2_file.read(sample_length * 4)  # 2 канала * 2 байта
                if len(data) < sample_length * 4:
                    return None
                
                # Преобразуем в список кортежей (левый, правый)
                samples = []
                for i in range(0, len(data), 4):
                    left = struct.unpack('<h', data[i:i+2])[0]
                    right = struct.unpack('<h', data[i+2:i+4])[0]
                    samples.append((left / 32768.0, right / 32768.0))
            else:
                # Для моно читаем одиночные значения
                data = sf2_file.read(sample_length * 2)
                if len(data) < sample_length * 2:
                    return None
                
                # Преобразуем в список значений
                samples = []
                for i in range(0, len(data), 2):
                    value = struct.unpack('<h', data[i:i+2])[0]
                    samples.append(value / 32768.0)
            
            return samples
        except Exception as e:
            warnings.warn(f"Ошибка при чтении сэмпла {sample_header.name}: {str(e)}")
            return None

    def _add_to_cache(self, name: str, sample_data: Union[List[float], List[Tuple[float, float]]]):
        """Добавление сэмпла в кэш с учетом ограничения размера"""
        # Оцениваем размер данных
        size_estimate = len(sample_data)
        if isinstance(sample_data[0], tuple):
            size_estimate *= 2  # Стерео занимает в 2 раза больше
        
        # Если кэш переполнен, удаляем наименее используемые элементы
        while self.current_cache_size + size_estimate > self.max_cache_size and len(self.sample_cache) > 0:
            # Удаляем наименее используемый элемент (первый в OrderedDict)
            removed_name, removed_data = self.sample_cache.popitem(last=False)
            removed_size = len(removed_data)
            if isinstance(removed_data[0], tuple):
                removed_size *= 2
            self.current_cache_size -= removed_size
        
        # Добавляем новый элемент
        self.sample_cache[name] = sample_data
        self.current_cache_size += size_estimate

    def _get_default_parameters(self) -> dict:
        """Возвращает параметры по умолчанию для мелодического инструмента"""
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
                "lfo1_to_pitch": 50.0,
                "lfo2_to_pitch": 30.0,
                "lfo3_to_pitch": 10.0,
                "env_to_pitch": 30.0,
                "aftertouch_to_pitch": 20.0,
                "lfo_to_filter": 0.3,
                "env_to_filter": 0.5,
                "aftertouch_to_filter": 0.2,
                "tremolo_depth": 0.3,
                "vibrato_depth": 50.0,
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
                    "fine_tune": 0
                }
            ]
        }

    def _get_default_drum_parameters(self, note: int) -> dict:
        """Возвращает параметры по умолчанию для барабана"""
        return {
            "amp_envelope": {
                "delay": 0.0,
                "attack": 0.001,
                "hold": 0.0,
                "decay": 0.1,
                "sustain": 0.0,
                "release": 0.001,
                "velocity_sense": 1.0,
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
                "type": "lowpass",
                "key_follow": 0.5
            },
            "lfo1": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo2": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "lfo3": {
                "waveform": "sine",
                "rate": 0.0,
                "depth": 0.0,
                "delay": 0.0
            },
            "modulation": {
                "lfo1_to_pitch": 0.0,
                "lfo2_to_pitch": 0.0,
                "lfo3_to_pitch": 0.0,
                "env_to_pitch": 0.0,
                "aftertouch_to_pitch": 0.0,
                "lfo_to_filter": 0.0,
                "env_to_filter": 0.0,
                "aftertouch_to_filter": 0.0,
                "tremolo_depth": 0.0,
                "vibrato_depth": 0.0,
                "vibrato_rate": 0.0,
                "vibrato_delay": 0.0
            },
            "partials": [
                {
                    "level": 1.0,
                    "pan": 0.5,
                    "key_range_low": note,
                    "key_range_high": note,
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

    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Устанавливает черный список банков для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_list: список номеров банков для исключения
        """
        self.bank_blacklists[sf2_path] = bank_list
        # Перестраиваем глобальную карту пресетов
        self._build_global_preset_map()

    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Устанавливает черный список пресетов для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            preset_list: список кортежей (bank, program) для исключения
        """
        self.preset_blacklists[sf2_path] = preset_list
        # Перестраиваем глобальную карту пресетов
        self._build_global_preset_map()

    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Устанавливает маппинг банков MIDI на банки SF2 для указанного файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_mapping: словарь маппинга midi_bank -> sf2_bank
        """
        self.bank_mappings[sf2_path] = bank_mapping
        # Перестраиваем глобальную карту пресетов
        self._build_global_preset_map()

    def get_available_presets(self) -> List[Tuple[int, int, str]]:
        """
        Возвращает список доступных пресетов.
        
        Returns:
            Список кортежей (bank, program, name)
        """
        presets_info = []
        for preset in self.presets:
            presets_info.append((preset.bank, preset.preset, preset.name))
        return presets_info

    def is_drum_bank(self, bank: int) -> bool:
        """
        Проверяет, является ли банк барабанным.
        
        Args:
            bank: номер банка
            
        Returns:
            True, если банк барабанный, иначе False
        """
        # В SoundFont банк 128 обычно используется для барабанов
        return bank == 128

    def clear_cache(self):
        """Очистка кэша сэмплов"""
        self.sample_cache.clear()
        self.current_cache_size = 0

    def get_modulation_matrix(self, program: int, bank: int = 0) -> List[Dict[str, Any]]:
        """
        Получение матрицы модуляции для программы.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            Список маршрутов модуляции
        """
        # Найти пресет и его менеджер по банку и программе
        preset_idx = self._find_preset_index(program, bank)
        if preset_idx is None:
            return []
        
        preset = self.presets[preset_idx]
        
        # Определяем, из какого менеджера взят этот пресет
        manager = None
        for mgr in self.sf2_managers:
            for preset_in_mgr in mgr['presets']:
                if (preset_in_mgr.name == preset.name and 
                    preset_in_mgr.preset == preset.preset and 
                    preset_in_mgr.bank == preset.bank):
                    manager = mgr
                    break
            if manager:
                break
        
        # Получаем инструменты из соответствующего менеджера
        instruments = manager['instruments'] if manager else self.instruments
        
        # Собрать все зоны инструментов для этого пресета
        all_zones = []
        for preset_zone in preset.zones:
            if preset_zone.instrument_index < len(instruments):
                instrument = instruments[preset_zone.instrument_index]
                all_zones.extend(instrument.zones)
        
        # Создаем маршруты модуляции
        routes = []
        
        # Обрабатываем модуляторы из зон
        for zone in all_zones:
            for modulator in zone.modulators:
                # Получаем имя источника
                source_name = self._get_modulator_source_name(modulator)
                if source_name not in self.SF2_TO_XG_SOURCES:
                    continue
                
                # Получаем имя цели
                if modulator.destination not in self.SF2_TO_XG_DESTINATIONS:
                    continue
                
                # Нормализуем глубину модуляции
                amount = self._normalize_modulator_amount(modulator.amount, modulator.destination)
                
                # Определяем полярность
                polarity = 1.0 if modulator.source_polarity == 0 else -1.0
                
                # Добавляем маршрут
                routes.append({
                    "source": self.SF2_TO_XG_SOURCES[source_name],
                    "destination": self.SF2_TO_XG_DESTINATIONS[modulator.destination],
                    "amount": amount,
                    "polarity": polarity,
                    "velocity_sensitivity": 0.0,
                    "key_scaling": 0.0
                })
        
        return routes