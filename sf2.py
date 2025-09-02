import struct
import threading
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass

# Import classes from tg.py that we need for our implementation
from tg import ModulationDestination, ModulationSource

# Import our new SoundFont class
from sf2_soundfont import Sf2SoundFont
from sf2_dataclasses import *

# pyright: reportAssignmentType=false
@dataclass
class Sf2WavetableManager:
    """
    Менеджер wavetable сэмплов, основанный на SoundFont 2.0 файлах.
    Предоставляет интерфейс для XG Tone Generator с поддержкой нескольких слоев
    и барабанов. Реализует ленивую загрузку сэмплов и кэширование.
    Поддерживает загрузку нескольких SF2 файлов с приоритетами, черными списками
    и настраиваемым маппингом банков.
    
    Этот рефакторинг реализует стратегию отложенной загрузки, при которой
    структуры SF2 парсятся только при фактическом запросе.
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
    
    # Процессоры модуляторов для быстрого сопоставления
    MODULATOR_PROCESSORS = {
        5: lambda zone, source_name, amount, polarity: setattr(zone, 'lfo_to_pitch', amount * polarity) or setattr(zone, 'mod_lfo_to_pitch', amount * polarity),
        6: lambda zone, source_name, amount, polarity: setattr(zone, 'lfo_to_pitch', amount * polarity) or setattr(zone, 'vib_lfo_to_pitch', amount * polarity) or setattr(zone, 'vibrato_depth', amount * polarity),
        7: lambda zone, source_name, amount, polarity: setattr(zone, 'velocity_to_pitch', amount * polarity) or setattr(zone, 'mod_env_to_pitch', amount * polarity),
        10: lambda zone, source_name, amount, polarity: setattr(zone, 'lfo_to_filter', amount * polarity) or setattr(zone, 'mod_lfo_to_filter', amount * polarity),
        11: lambda zone, source_name, amount, polarity: setattr(zone, 'velocity_to_filter', amount * polarity) or setattr(zone, 'mod_env_to_filter', amount * polarity),
        13: lambda zone, source_name, amount, polarity: setattr(zone, 'tremolo_depth', amount * polarity) or setattr(zone, 'mod_lfo_to_volume', amount * polarity),
        77: lambda zone, source_name, amount, polarity: setattr(zone, 'tremolo_depth', amount * polarity),
        84: lambda zone, source_name, amount, polarity: setattr(zone, 'portamento_to_pitch', amount * polarity)
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
    
    # Сопоставление генераторов инструментов с обработчиками для оптимизации
    INST_GEN_HANDLERS = {
        53: ("sample_modes",),  # sampleModes
        54: ("exclusive_class",),  # exclusiveClass
        55: ("OverridingRootKey",),  # overridingRootKey
        56: ("sample_index",),  # sampleID
        0: ("start",),  # startAddrs
        1: ("end",),  # endAddrs
        2: ("start_loop",),  # startloopAddrs
        3: ("end_loop",),  # endloopAddrs
        12: ("initialFilterFc",),  # initialFilterFc
        13: ("initial_filterQ",),  # initialFilterQ
        21: ("Pan",),  # pan
        26: ("DelayFilEnv",),  # delayModEnv
        27: ("AttackFilEnv",),  # attackModEnv
        28: ("HoldFilEnv",),  # holdModEnv
        29: ("DecayFilEnv",),  # decayModEnv
        30: ("SustainFilEnv",),  # sustainModEnv
        31: ("ReleaseFilEnv",),  # releaseModEnv
        32: ("KeynumToModEnvHold",),  # keynumToModEnvHold
        33: ("KeynumToModEnvDecay",),  # keynumToModEnvDecay
        34: ("DelayVolEnv",),  # delayVolEnv
        35: ("AttackVolEnv",),  # attackVolEnv
        36: ("HoldVolEnv",),  # holdVolEnv
        37: ("DecayVolEnv",),  # decayVolEnv
        38: ("SustainVolEnv",),  # sustainVolEnv
        39: ("ReleaseVolEnv",),  # releaseVolEnv
        50: ("CoarseTune",),  # coarseTune
        51: ("FineTune",),  # fineTune
        5: ("mod_lfo_to_pitch",),  # modLfoToPitch
        6: ("vib_lfo_to_pitch",),  # vibLfoToPitch
        7: ("mod_env_to_pitch",),  # modEnvToPitch
        10: ("mod_lfo_to_filter",),  # modLfoToFilterFc
        11: ("mod_env_to_filter",),  # modEnvToFilterFc
        13: ("mod_lfo_to_volume",),  # modLfoToVolume
        36: ("KeynumToVolEnvHold",),  # keynumToVolEnvHold
        37: ("KeynumToVolEnvDecay",),  # keynumToVolEnvDecay
    }

    def __init__(self, sf2_paths: Union[str, List[str]], cache_size: Optional[int] = None):
        """
        Инициализация менеджера SoundFont.
        
        Args:
            sf2_paths: путь к файлу SoundFont (.sf2) или список путей
            cache_size: максимальный размер кэша в сэмплах (по умолчанию MAX_CACHE_SIZE)
        """
        self.lock = threading.Lock()
        # Поддержка одного или нескольких SF2 файлов
        self.sf2_paths = sf2_paths if isinstance(sf2_paths, list) else [sf2_paths]
        
        # Список SoundFont объектов для каждого SF2 файла
        self.soundfonts: List[Sf2SoundFont] = []
        
        # Настройки для каждого SF2 файла
        self.bank_blacklists: Dict[str, List[int]] = {}  # sf2_path -> список банков для исключения
        self.preset_blacklists: Dict[str, List[Tuple[int, int]]] = {}  # sf2_path -> список (bank, program) для исключения
        self.bank_mappings: Dict[str, Dict[int, int]] = {}  # sf2_path -> bank_mapping (midi_bank -> sf2_bank)
        
        # Кэш для загруженных сэмплов
        self.sample_cache = OrderedDict()
        self.current_cache_size = 0
        self.max_cache_size = cache_size if cache_size is not None else self.MAX_CACHE_SIZE
        
        # Инициализация кэшей для оптимизации
        self._source_name_cache = {}
        self._normalize_cache = {}
        
        # Инициализация SoundFont файлов
        self._initialize_soundfonts()
    
    def __del__(self):
        """Закрываем все файлы при уничтожении объекта"""
        for soundfont in self.soundfonts:
            if hasattr(soundfont, 'file') and soundfont.file and not soundfont.file.closed:
                soundfont.file.close()
    
    def _initialize_soundfonts(self):
        """Инициализация SoundFont файлов"""
        for i, sf2_path in enumerate(self.sf2_paths):
            try:
                # Создаем SoundFont объект для этого файла
                soundfont = Sf2SoundFont(sf2_path, i)
                self.soundfonts.append(soundfont)
            except Exception as e:
                print(f"Ошибка при инициализации SF2 файла {sf2_path}: {str(e)}")

    def get_program_parameters(self, program: int, bank: int = 0) -> dict:
        """
        Получение параметров программы в формате, совместимом с XGToneGenerator.
        Реализует отложенную загрузку - структуры SF2 парсятся только при фактическом запросе.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            словарь с параметрами программы
        """
        # Найти пресет и его SoundFont по банку и программе
        soundfont_obj = None
        preset_obj = None
        
        # Ищем пресет во всех SoundFont файлах
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                soundfont_obj = soundfont
                preset_obj = preset
                break
        
        # Если пресет не найден, возвращаем параметры по умолчанию
        if not soundfont_obj or not preset_obj:
            return self._get_default_parameters()
        
        # Получаем инструменты из соответствующего SoundFont
        instruments = soundfont_obj.instruments
        
        # Собрать все объединенные зоны для этого пресета
        all_merged_zones = []
        for preset_zone in preset_obj.zones:
            if preset_zone.instrument_index < len(instruments):
                instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                if instrument is not None:
                    # Объединяем параметры пресета и инструмента для каждой зоны
                    for instrument_zone in instrument.zones:
                        merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                        all_merged_zones.append(merged_zone)
        
        # Если зон нет, возвращаем параметры по умолчанию
        if not all_merged_zones:
            return self._get_default_parameters()
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in all_merged_zones:
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
                "rate": self._convert_lfo_rate(all_merged_zones[0].LFO1Freq),
                "depth": 0.5,
                "delay": self._convert_time_cents_to_seconds(all_merged_zones[0].DelayLFO1)
            },
            "lfo2": {
                "waveform": "triangle",
                "rate": self._convert_lfo_rate(all_merged_zones[0].LFO2Freq),
                "depth": 0.3,
                "delay": self._convert_time_cents_to_seconds(all_merged_zones[0].DelayLFO2)
            },
            "lfo3": {
                "waveform": "sawtooth",
                "rate": 0.5,
                "depth": 0.1,
                "delay": 0.5
            },
            "modulation": self._calculate_modulation_params(all_merged_zones),
            "partials": partials_params
        }
        
        return params

    def _get_modulator_source_name(self, modulator: SF2Modulator) -> str:
        """Получение имени источника модуляции с кэшированием"""
        # Создаем кэш если он еще не существует
        if not hasattr(self, '_source_name_cache'):
            self._source_name_cache = {}
        
        # Генерируем ключ для кэширования
        cache_key = (modulator.source_oper, modulator.source_index)
        
        # Проверяем кэш
        if cache_key in self._source_name_cache:
            return self._source_name_cache[cache_key]
        
        # Вычисляем имя источника
        source_name = "unknown_source"  # Значение по умолчанию
        
        # Сначала проверяем основной источник
        if modulator.source_oper in self.SF2_SOURCE_OPERATORS:
            source_name = self.SF2_SOURCE_OPERATORS[modulator.source_oper]
            
            # Для CC контроллеров добавляем индекс
            if source_name.startswith("cc_"):
                if modulator.source_index > 0:
                    source_name = f"{source_name}_{modulator.source_index}"
        # Для LFO
        elif modulator.source_oper == 5:
            source_name = "modLFO"
        elif modulator.source_oper == 6:
            source_name = "vibLFO"
        # Для огибающих
        elif modulator.source_oper == 7:
            source_name = "modEnv"
        elif modulator.source_oper == 13:
            source_name = "channel_aftertouch"
        
        # Сохраняем в кэш
        self._source_name_cache[cache_key] = source_name
        return source_name
    
    def _normalize_modulator_amount(self, amount: int, destination: int) -> float:
        """
        Нормализация глубины модуляции в зависимости от цели с кэшированием.
        
        Args:
            amount: исходное значение глубины модуляции
            destination: цель модуляции
            
        Returns:
            нормализованное значение глубины модуляции
        """
        # Создаем кэш если он еще не существует
        if not hasattr(self, '_normalize_cache'):
            self._normalize_cache = {}
        
        # Генерируем ключ для кэширования
        cache_key = (amount, destination)
        
        # Проверяем кэш
        if cache_key in self._normalize_cache:
            return self._normalize_cache[cache_key]
        
        # Вычисляем нормализованное значение
        abs_amount = abs(amount)
        
        # Для pitch модуляции (в центах)
        if destination in [5, 6, 7]:
            result = abs_amount / 100.0  # 100 = 1 цент
        # Для cutoff фильтра
        elif destination in [8, 10, 11]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для амплитуды
        elif destination in [13, 31, 33, 34, 35]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для панорамирования
        elif destination == 17:
            result = abs_amount / 100.0  # 0-100 в SoundFont -> 0-1
        # Для трепета (tremolo)
        elif destination in [77, 78]:
            result = abs_amount / 1000.0  # Нормализуем к 0-1
        # Для других целей
        else:
            result = abs_amount / 1000.0  # Общая нормализация
        
        # Сохраняем в кэш
        self._normalize_cache[cache_key] = result
        return result
    

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
        
        # Используем словарь для быстрого сопоставления целей и действий
        if destination in self.MODULATOR_PROCESSORS:
            processor = self.MODULATOR_PROCESSORS[destination]
            processor(zone, source_name, amount, polarity)
        # Обработка специфических целей вне словаря
        elif destination == 8:  # initialFilterFc
            if source_name == "note_on_velocity":
                zone.velocity_to_filter = amount * polarity
            elif source_name == "channel_aftertouch":
                zone.aftertouch_to_filter = amount * polarity
            elif source_name == "cc_mod_wheel":
                zone.mod_wheel_to_filter = amount * polarity
            elif source_name == "cc_brightness":
                zone.brightness_to_filter = amount * polarity
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


    def _merge_preset_and_instrument_params(self, preset_zone: SF2PresetZone, instrument_zone: SF2InstrumentZone) -> SF2InstrumentZone:
        """
        Объединяет параметры из зоны пресета и зоны инструмента.
        Параметры из пресета используются как значения по умолчанию, 
        которые могут быть переопределены параметрами из инструмента.
        
        Args:
            preset_zone: зона пресета
            instrument_zone: зона инструмента
            
        Returns:
            Объединенная зона инструмента с параметрами
        """
        # Создаем копию зоны инструмента для модификации
        merged_zone = SF2InstrumentZone()
        
        # Копируем все атрибуты из зоны инструмента
        for attr in instrument_zone.__slots__:
            setattr(merged_zone, attr, getattr(instrument_zone, attr))
        
        # Применяем параметры из пресета как значения по умолчанию
        # Только если в инструменте значение не установлено (равно 0 или стандартному значению)
        
        # Используем словарь для быстрого сопоставления типов генераторов
        generator_defaults = {
            8: (13500, "initialFilterFc"),  # initialFilterFc
            9: (0, "initial_filterQ"),  # initialFilterQ
            12: (0, "DelayVolEnv"),  # delayVolEnv
            13: (9600, "AttackVolEnv"),  # attackVolEnv
            14: (0, "HoldVolEnv"),  # holdVolEnv
            15: (19200, "DecayVolEnv"),  # decayVolEnv
            16: (0, "SustainVolEnv"),  # sustainVolEnv
            17: (24000, "ReleaseVolEnv"),  # releaseVolEnv
            21: (50, "Pan"),  # pan
            22: (0, "DelayLFO1"),  # delayModLFO
            23: (500, "LFO1Freq"),  # freqModLFO
            24: (0, "DelayLFO2"),  # delayVibLFO
            25: (0, "DelayFilEnv"),  # delayModEnv
            26: (19200, "AttackFilEnv"),  # attackModEnv
            27: (0, "HoldFilEnv"),  # holdModEnv
            28: (19200, "DecayFilEnv"),  # decayModEnv
            29: (0, "SustainFilEnv"),  # sustainModEnv
            30: (24000, "ReleaseFilEnv"),  # releaseModEnv
            32: (0, "KeynumToModEnvHold"),  # keynumToModEnvHold
            33: (0, "KeynumToModEnvDecay"),  # keynumToModEnvDecay
            34: (0, "DelayVolEnv"),  # delayVolEnv
            35: (9600, "AttackVolEnv"),  # attackVolEnv
            36: (0, "HoldVolEnv"),  # holdVolEnv
            37: (19200, "DecayVolEnv"),  # decayVolEnv
            38: (0, "SustainVolEnv"),  # sustainVolEnv
            39: (24000, "ReleaseVolEnv"),  # releaseVolEnv
            50: (0, "CoarseTune"),  # coarseTune
            51: (0, "FineTune")  # fineTune
        }
        
        # Обработка генераторов из пресета
        for gen_type, gen_amount in preset_zone.generators.items():
            # Для каждого типа генератора применяем значение из пресета как значение по умолчанию
            if gen_type in generator_defaults:
                default_value, attr_name = generator_defaults[gen_type]
                current_value = getattr(merged_zone, attr_name)
                # Применяем значение из пресета только если в инструменте значение по умолчанию
                if current_value == default_value:
                    setattr(merged_zone, attr_name, gen_amount)
        
        # Объединяем модуляторы из пресета и инструмента
        # Модуляторы из пресета добавляются первыми, затем модуляторы из инструмента
        merged_modulators = preset_zone.modulators + instrument_zone.modulators
        merged_zone.modulators = merged_modulators
        
        # Пересчитываем параметры модуляций после объединения
        for modulator in merged_zone.modulators:
            self._process_instrument_modulator(merged_zone, modulator)
        
        return merged_zone
    

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
        # Найти пресет и его SoundFont по банку и программе
        soundfont_obj = None
        preset_obj = None
        
        # Ищем пресет во всех SoundFont файлах
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                soundfont_obj = soundfont
                preset_obj = preset
                break
        
        # Если не найдено в банке 128, пробуем банк 0
        if not soundfont_obj or not preset_obj:
            for soundfont in self.soundfonts:
                preset = soundfont.get_preset(program, 0)
                if preset is not None:
                    soundfont_obj = soundfont
                    preset_obj = preset
                    break
        
        # Если пресет не найден, возвращаем параметры по умолчанию
        if not soundfont_obj or not preset_obj:
            return self._get_default_drum_parameters(note)
        
        # Получаем инструменты из соответствующего SoundFont
        instruments = soundfont_obj.instruments
        
        # Найти зоны, соответствующие этой ноте, и объединить параметры
        matching_merged_zones = []
        for preset_zone in preset_obj.zones:
            # Проверяем, попадает ли нота в диапазон зоны пресета
            if preset_zone.lokey <= note <= preset_zone.hikey:
                if preset_zone.instrument_index < len(instruments):
                    instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                    if instrument is not None:
                        # Проверяем зоны инструмента
                        for instrument_zone in instrument.zones:
                            # Проверяем, попадает ли нота в диапазон зоны инструмента
                            if instrument_zone.lokey <= note <= instrument_zone.hikey:
                                # Объединяем параметры пресета и инструмента
                                merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                                matching_merged_zones.append(merged_zone)
        
        # Если не найдено подходящих зон, возвращаем параметры по умолчанию
        if not matching_merged_zones:
            return self._get_default_drum_parameters(note)
        
        # Преобразуем зоны в параметры частичных структур
        partials_params = []
        for zone in matching_merged_zones:
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
                "waveform": "triangle",
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
            "modulation": self._calculate_modulation_params(matching_merged_zones),
            "partials": partials_params
        }
        
        return params
    
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
        """Возвращает параметры по умолчанию для барабанного инструмента"""
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
        self._source_name_cache.clear()
        self._normalize_cache.clear()
    
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
        # Найти пресет и его SoundFont по банку и программе
        soundfont_obj = None
        preset_obj = None
        
        # Ищем пресет во всех SoundFont файлах
        for soundfont in self.soundfonts:
            preset = soundfont.get_preset(program, bank)
            if preset is not None:
                soundfont_obj = soundfont
                preset_obj = preset
                break
        
        # Если пресет не найден, возвращаем None
        if not soundfont_obj or not preset_obj:
            return None
        
        # Получаем инструменты из соответствующего SoundFont
        instruments = soundfont_obj.instruments
        
        # Собрать все подходящие зоны и объединить параметры
        matching_merged_zones = []
        for preset_zone in preset_obj.zones:
            # Проверяем, попадает ли нота и velocity в диапазон зоны пресета
            if (preset_zone.lokey <= note <= preset_zone.hikey and
                preset_zone.lovel <= velocity <= preset_zone.hivel):
                
                if preset_zone.instrument_index < len(instruments):
                    instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                    if instrument is not None:
                        # Проверяем зоны инструмента
                        for instrument_zone in instrument.zones:
                            # Проверяем, попадает ли нота и velocity в диапазон зоны инструмента
                            if (instrument_zone.lokey <= note <= instrument_zone.hikey and
                                instrument_zone.lovel <= velocity <= instrument_zone.hivel):
                                # Объединяем параметры пресета и инструмента
                                merged_zone = self._merge_preset_and_instrument_params(preset_zone, instrument_zone)
                                matching_merged_zones.append(merged_zone)
        
        # Если нет подходящих зон или запрошенная частичная структура отсутствует, возвращаем None
        if not matching_merged_zones or partial_id >= len(matching_merged_zones):
            return None
        
        # Получаем нужную зону
        zone = matching_merged_zones[partial_id]
        
        # Получаем сэмпл
        sample_header = soundfont_obj.get_sample_header(zone.sample_index)
        if sample_header is None:
            return None
        
        # Загружаем сэмпл (из кэша или из файла)
        sample_data = self._load_sample_data(sample_header, soundfont_obj)
        if sample_data is None:
            return None
        
        # Возвращаем аудио данные
        return sample_data
   
    def _load_sample_data(self, sample_header: SF2SampleHeader, soundfont: Sf2SoundFont) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Загрузка данных сэмпла из файла или кэша.
        
        Args:
            sample_header: заголовок сэмпла
            soundfont: объект Sf2SoundFont
            
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
        sample_data = self._read_sample_from_file(sample_header, soundfont)
        if sample_data is None:
            return None
        
        # Добавляем в кэш
        self._add_to_cache(sample_header.name, sample_data)
        
        return sample_data
    
    def _read_sample_from_file(self, sample_header: SF2SampleHeader, soundfont: Sf2SoundFont) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Оптимизированное чтение сэмпла из файла с уменьшением количества операций.
        
        Args:
            sample_header: заголовок сэмпла
            soundfont: объект Sf2SoundFont
            
        Returns:
            Моно: список значений
            Стерео: список кортежей (левый, правый)
        """
        # Проверяем, есть ли файл
        if not soundfont.file or soundfont.file.closed:
            return None
        
        # Проверяем, есть ли данные о сэмпле в SoundFont
        if 'sdta' not in soundfont.chunk_positions:
            return None
        
        # Получаем позицию данных сэмпла
        smpl_data_offset = soundfont.chunk_positions['sdta']
        
        # Определяем размер сэмпла в сэмплах (не в байтах)
        sample_length = sample_header.end - sample_header.start
        if sample_length <= 0:
            return None
        
        # Определяем тип сэмпла (моно или стерео)
        is_stereo = (sample_header.type & 1) == 0 and (sample_header.type & 2) != 0
        
        # Вычисляем смещение в файле
        sample_offset = smpl_data_offset + sample_header.start * 2  # Предполагаем 16-битные сэмплы
        
        try:
            # Переходим к началу сэмпла
            soundfont.file.seek(sample_offset)
            
            # Читаем данные за один раз для лучшей производительности
            if is_stereo:
                # Для стерео читаем пары значений
                bytes_to_read = sample_length * 4  # 2 канала * 2 байта
                data = soundfont.file.read(bytes_to_read)
                if len(data) < bytes_to_read:
                    return None
                
                # Преобразуем в список кортежей (левый, правый) одной операцией
                unpacked_data = struct.unpack(f'<{sample_length*2}h', data)  # h = signed short
                samples = [(unpacked_data[i] / 32768.0, unpacked_data[i+1] / 32768.0) 
                          for i in range(0, len(unpacked_data), 2)]
            else:
                # Для моно читаем одиночные значения
                bytes_to_read = sample_length * 2
                data = soundfont.file.read(bytes_to_read)
                if len(data) < bytes_to_read:
                    return None
                
                # Преобразуем в список значений одной операцией
                unpacked_data = struct.unpack(f'<{sample_length}h', data)  # h = signed short
                samples = [value / 32768.0 for value in unpacked_data]
            
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


    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Устанавливает черный список банков для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_list: список номеров банков для исключения
        """
        with self.lock:
            self.bank_blacklists[sf2_path] = bank_list.copy()
            
            # Применяем изменения ко всем соответствующим SoundFont файлам
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.bank_blacklist = bank_list.copy()

    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Устанавливает черный список пресетов для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            preset_list: список кортежей (bank, program) для исключения
        """
        with self.lock:
            self.preset_blacklists[sf2_path] = preset_list.copy()
            
            # Применяем изменения ко всем соответствующим SoundFont файлам
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.preset_blacklist = preset_list.copy()

    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Устанавливает маппинг банков MIDI на банки SF2 для указанного файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_mapping: словарь маппинга midi_bank -> sf2_bank
        """
        with self.lock:
            self.bank_mappings[sf2_path] = bank_mapping.copy()
            
            # Применяем изменения ко всем соответствующим SoundFont файлам
            for soundfont in self.soundfonts:
                if soundfont.path == sf2_path:
                    soundfont.bank_mapping = bank_mapping.copy()
    
    def get_available_presets(self) -> List[Tuple[int, int, str]]:
        """
        Получение списка доступных пресетов.
        
        Returns:
            Список кортежей (bank, program, name)
        """
        presets = []
        
        # Собираем информацию о пресетах из всех SoundFont файлов
        with self.lock:
            for soundfont in self.soundfonts:
                # Получаем все пресеты из этого SoundFont
                for preset in soundfont.presets:
                    presets.append((preset.bank, preset.preset, preset.name))
        
        return presets
    
    def get_modulation_matrix(self, program: int, bank: int = 0) -> List[Dict[str, Any]]:
        """
        Получение матрицы модуляции для программы.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            Список маршрутов модуляции
        """
        # Найти пресет и его SoundFont по банку и программе
        soundfont_obj = None
        preset_obj = None
        
        # Ищем пресет во всех SoundFont файлах
        with self.lock:
            for soundfont in self.soundfonts:
                preset = soundfont.get_preset(program, bank)
                if preset is not None:
                    soundfont_obj = soundfont
                    preset_obj = preset
                    break
        
        # Если пресет не найден, возвращаем пустой список
        if not soundfont_obj or not preset_obj:
            return []
        
        # Собрать все модуляторы для этого пресета
        all_modulators = []
        for preset_zone in preset_obj.zones:
            all_modulators.extend(preset_zone.modulators)
            # Также получаем модуляторы из инструментов
            if preset_zone.instrument_index < len(soundfont_obj.instruments):
                instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                if instrument is not None:
                    for instrument_zone in instrument.zones:
                        all_modulators.extend(instrument_zone.modulators)
        
        # Создаем маршруты модуляции
        routes = []
        for modulator in all_modulators:
            # Преобразуем модуляторы SF2 в маршруты XG
            routes.append({
                "source": "unknown",  # Заглушка, в реальной реализации нужно преобразование
                "destination": "unknown",  # Заглушка, в реальной реализации нужно преобразование
                "amount": modulator.amount / 1000.0,  # Простое преобразование
                "polarity": 1.0 if modulator.source_polarity == 0 else -1.0,
                "velocity_sensitivity": 0.0,
                "key_scaling": 0.0
            })
        
        return routes

    def preload_program(self, program: int, bank: int = 0):
        """
        Preload program data to reduce latency during program changes.
        
        This method ensures that all necessary data for a specific program
        is loaded into memory, including presets, instruments, and sample headers.
        It performs on-demand parsing of the required data structures.
        
        Args:
            program: Program number (0-127)
            bank: Bank number (0-16383)
        """
        # Find the preset and its SoundFont by bank and program
        soundfont_obj = None
        preset_obj = None
        
        # Search for the preset in all SoundFont files
        with self.lock:
            for soundfont in self.soundfonts:
                preset = soundfont.get_preset(program, bank)
                if preset is not None:
                    soundfont_obj = soundfont
                    preset_obj = preset
                    break
        
        # If preset not found, nothing to preload
        if not soundfont_obj or not preset_obj:
            return
        
        # Preload the preset data if not already parsed
        try:
            # Ensure preset data is parsed
            with self.lock:
                soundfont_obj._ensure_preset_parsed(preset_obj.preset_bag_index)
            
            # Preload instrument data for all zones in the preset
            instruments = soundfont_obj.instruments
            for preset_zone in preset_obj.zones:
                if preset_zone.instrument_index < len(instruments):
                    with self.lock:
                        soundfont_obj._ensure_instrument_parsed(preset_zone.instrument_index)
            
            # Preload sample headers that are referenced by the instruments
            # This ensures faster access when samples are actually needed
            for preset_zone in preset_obj.zones:
                if preset_zone.instrument_index < len(instruments):
                    instrument = soundfont_obj.get_instrument(preset_zone.instrument_index)
                    if instrument is not None:
                        for instrument_zone in instrument.zones:
                            if instrument_zone.sample_index < len(soundfont_obj.sample_headers):
                                # Touch the sample header to ensure it's loaded
                                sample_header = soundfont_obj.get_sample_header(instrument_zone.sample_index)
                                if sample_header is not None:
                                    # We don't actually load the sample data here to save memory
                                    # Just ensure the header is parsed and available
                                    pass
                                
        except Exception as e:
            # Silently ignore preload errors to maintain performance
            # The actual loading will happen when the program is used
            pass
