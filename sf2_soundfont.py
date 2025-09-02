import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass

# Import classes from tg.py that we need for our implementation
from tg import ModulationDestination, ModulationSource

# Import the data classes from sf2_dataclasses.py
from sf2_dataclasses import SF2Modulator, SF2InstrumentZone, SF2PresetZone, SF2SampleHeader, SF2Preset, SF2Instrument


class Sf2SoundFont:
    """
    Представляет один SoundFont файл с возможностью отложенного парсинга.
    Реализует on-demand parsing of SF2 presets details such as generators, 
    modulators and their instruments along with their own generators and modulators.
    """
    
    def __init__(self, sf2_path: str, priority: int = 0):
        """
        Инициализация SoundFont файла.
        
        Args:
            sf2_path: путь к файлу SoundFont (.sf2)
            priority: приоритет файла (меньше = выше приоритет)
        """
        self.path = sf2_path
        self.priority = priority
        self.file = None
        self.file_size = 0
        self.chunk_info = {}  # Словарь (позиция, размер) чанков для быстрого доступа
        
        # Основные структуры данных
        self.presets: List[SF2Preset] = []
        self.instruments: List[SF2Instrument] = []
        self.sample_headers: List[SF2SampleHeader] = []
        
        # Флаги для отложенного парсинга
        self.headers_parsed = False  # Заголовки пресетов (bank, program, name)
        self.presets_parsed = False  # Полные данные пресетов
        self.instruments_parsed = False  # Полные данные инструментов
        self.samples_parsed = False  # Данные сэмплов
        
        # Кэши для on-demand parsing
        self.parsed_preset_indices = set()  # Индексы пресетов, которые уже распаршены
        self.parsed_instrument_indices = set()  # Индексы инструментов, которые уже распаршены
        
        # Индексные данные для on-demand parsing
        self.preset_zone_data = []  # Данные зон пресетов для парсинга по запросу
        self.instrument_zone_data = []  # Данные зон инструментов для парсинга по запросу

        self.preset_blacklist = []
        self.bank_blacklist = []
        self.bank_mapping = {}
        
        # Инициализация - только читаем заголовки файла
        self._initialize_file_headers()
    
    def __del__(self):
        """Закрываем файл при уничтожении объекта"""
        if self.file and not self.file.closed:
            self.file.close()
    
    def _initialize_file_headers(self):
        """Инициализация SF2 файла - читаем только заголовки для быстрой инициализации"""
        try:
            # Открываем файл для чтения с большим буфером для улучшения производительности
            self.file = open(self.path, 'rb', buffering=1024*1024)  # 1MB buffer
            
            # Проверка заголовка RIFF
            self.file.seek(0)
            header = self.file.read(12)
            if len(header) < 12 or header[:4] != b'RIFF' or header[8:12] != b'sfbk':
                raise ValueError(f"Некорректный формат SoundFont файла: {self.path}")
            
            # Определение размера файла
            self.file_size = struct.unpack('<I', header[4:8])[0] + 8
            
            # Находим позиции ключевых чанков без полного парсинга
            self._locate_sf2_chunks()
            
            # Парсим только заголовки пресетов для быстрой инициализации
            self._parse_preset_headers()
            self.headers_parsed = True
            
        except Exception as e:
            print(f"Ошибка при инициализации SF2 файла {self.path}: {str(e)}")
            if self.file and not self.file.closed:
                self.file.close()
            self.file = None
    
    def _locate_sf2_chunks(self):
        """Находит позиции ключевых чанков SF2 без полного парсинга"""
        if not self.file:
            return
            
        self.file.seek(12)  # Пропускаем заголовок RIFF
        
        while self.file.tell() < self.file_size - 8:
            # Чтение заголовка чанка
            chunk_header = self.file.read(8)
            if len(chunk_header) < 8:
                break
                
            chunk_id = chunk_header[:4]
            chunk_size = struct.unpack('<I', chunk_header[4:8])[0]
            
            # Определение конца чанка с учетом выравнивания
            chunk_end = self.file.tell() + chunk_size + (chunk_size % 2)
            
            # Обработка LIST-чанков (специальный контейнерный тип)
            if chunk_id == b'LIST':
                # Получаем тип LIST чанка
                list_type = self.file.read(4)
                if len(list_type) < 4:
                    break
                    
                # Сохраняем позицию и размер как кортеж
                list_position = self.file.tell() - 4
                self.chunk_info[list_type.decode('ascii')] = (list_position, chunk_size)
                
                # Для pdta чанка дополнительно парсим подчанки для оптимизации
                self._locate_subchunks(list_position, chunk_size)
            else:
                # Пропускаем не-LIST чанки
                self.file.seek(chunk_end)
    
    def _locate_subchunks(self, pdta_position: int, pdta_size: int):
        """Находит позиции обязательных подчанков в pdta для оптимизации on-demand парсинга"""
        if not self.file:
            return
            
        # Сохраняем текущую позицию
        current_pos = self.file.tell()
        
        try:
            # Переходим к началу pdta
            self.file.seek(pdta_position + 4)  # +4 чтобы пропустить заголовок LIST
            pdta_end = pdta_position + pdta_size - 4

            # Парсим подчанки внутри pdta
            while self.file.tell() < pdta_end - 8:
                # Чтение заголовка подчанка
                subchunk_header = self.file.read(8)
                if len(subchunk_header) < 8:
                    break
                    
                subchunk_id = subchunk_header[:4]
                subchunk_size = struct.unpack('<I', subchunk_header[4:8])[0]
                subchunk_name = subchunk_id.decode('ascii')
                # Сохраняем позицию и размер как кортеж
                self.chunk_info[subchunk_name] = (self.file.tell(), subchunk_size)
                
                # Определение конца подчанка
                subchunk_end = self.file.tell() + subchunk_size
                # Переходим к следующему подчанку
                self.file.seek(subchunk_end + (subchunk_size % 2))
                
        except Exception as e:
            # В случае ошибки просто пропускаем детальный парсинг
            pass
        finally:
            # Восстанавливаем позицию
            self.file.seek(current_pos)
    
    def _parse_preset_headers(self):
        """Парсит только заголовки пресетов (bank, program, name) для быстрой инициализации"""
                
        try:
            phdr_pos, phdr_size = self.chunk_info.get('phdr', (0, 0))
            self._parse_phdr_chunk(phdr_size, phdr_pos)
        except Exception as e:
            print(f"Ошибка при парсинге заголовков пресетов в {self.path}: {str(e)}")
    
    def _parse_phdr_chunk(self, chunk_size: int, start_offset: int):
        """Парсинг чанка phdr (заголовки пресетов) только для получения базовой информации"""
        if not self.file:
            return
            
        self.file.seek(start_offset)
        
        # Читаем все заголовки пресетов за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 38)  # Исключаем терминальный пресет
        if len(raw_data) < chunk_size - 38:
            return
            
        # Распаковываем все заголовки пресетов одной операцией
        # Создаем структурированный тип данных для заголовка пресета
        phdr_dtype = np.dtype([
            ('name', 'S20'),  # 20 байт для имени
            ('preset', '<u2'),  # uint16
            ('bank', '<u2'),  # uint16
            ('preset_bag_ndx', '<u2'),  # uint16
            ('library', '<u4'),  # uint32
            ('genre', '<u4'),  # uint32
            ('morphology', '<u4')  # uint32
        ])
        
        # Преобразуем байты в массив структурированных данных
        phdr_array = np.frombuffer(raw_data[:len(raw_data)//38*38], dtype=phdr_dtype)
        
        # Создаем пресеты из структурированных данных
        for phdr_record in phdr_array:
            # Извлечение данных
            name = phdr_record['name'].split(b'\x00')[0].decode('ascii', 'ignore')
            preset = int(phdr_record['preset'])
            bank = int(phdr_record['bank'])
            preset_bag_ndx = int(phdr_record['preset_bag_ndx'])
            
            # Создаем пресет
            sf2_preset = SF2Preset()
            sf2_preset.name = name
            sf2_preset.preset = preset
            sf2_preset.bank = bank
            sf2_preset.preset_bag_index = preset_bag_ndx
            self.presets.append(sf2_preset)
    
    def _ensure_preset_parsed(self, preset_index: int):
        """Гарантирует, что конкретный пресет распаршен"""
        if preset_index in self.parsed_preset_indices:
            return
            
        if not self.file:
            return
            
        try:
            # Parse only the specific preset requested, not all presets
            self._parse_single_preset_data(preset_index)
            self.parsed_preset_indices.add(preset_index)
        except Exception as e:
            print(f"Ошибка при парсинге пресета {preset_index} в {self.path}: {str(e)}")
            self.parsed_preset_indices.add(preset_index)  # Помечаем как распаршенный даже в случае ошибки
    
    def _ensure_instrument_parsed(self, instrument_index: int):
        """Гарантирует, что конкретный инструмент распаршен"""
        if instrument_index in self.parsed_instrument_indices:
            return
            
        if not self.file:
            return
            
        try:
            # Если уже парсили, но конкретный инструмент еще нет, парсим только его
            self._parse_single_instrument_data(instrument_index)
            self.parsed_instrument_indices.add(instrument_index)
        except Exception as e:
            print(f"Ошибка при парсинге инструмента {instrument_index} в {self.path}: {str(e)}")
            self.parsed_instrument_indices.add(instrument_index)  # Помечаем как распаршенный даже в случае ошибки
    
    def _parse_all_presets_data(self):
        """Парсит полные данные всех пресетов (зоны, генераторы, модуляторы)"""
        self._parse_pdta_presets()
    
    def _parse_all_instruments_data(self):
        """Парсит полные данные всех инструментов (зоны, генераторы, модуляторы)"""
        self._parse_pdta_instruments()
    
    def _parse_single_preset_data(self, preset_index: int):
        """Парсит данные только для одного конкретного пресета"""
        # Реализован частичный on-demand парсинг одного пресета
        # Парсим только данные, относящиеся к конкретному пресету
        if not self.file:
            return
            
        # Определяем границы зон для конкретного пресета
        preset = self.presets[preset_index]
        start_bag_index = preset.preset_bag_index
        end_bag_index = self.presets[preset_index + 1].preset_bag_index if preset_index + 1 < len(self.presets) else None
        
        # Парсим только нужные данные из pbag, pgen, pmod используя заранее сохраненные позиции
        self._parse_pdta_presets_selective(0, 0, start_bag_index, end_bag_index)
    
    def _parse_single_instrument_data(self, instrument_index: int):
        """Парсит данные только для одного конкретного инструмента"""
        # Реализован частичный on-demand парсинг одного инструмента
        # Парсим только данные, относящиеся к конкретному инструменту
        if not self.file:
            return
            
        # Определяем границы зон для конкретного инструмента
        instrument = self.instruments[instrument_index]
        start_bag_index = instrument.instrument_bag_index
        end_bag_index = self.instruments[instrument_index + 1].instrument_bag_index if instrument_index + 1 < len(self.instruments) else None
        
        # Парсим только нужные данные из ibag, igen, imod используя заранее сохраненные позиции
        self._parse_pdta_instruments_selective(0, 0, start_bag_index, end_bag_index)
    
    def _parse_pdta_presets_selective(self, list_size: int, start_offset: int, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсинг данных пресетов из LIST pdta чанка выборочно"""
        if not self.file:
            return
            
        # Используем заранее сохраненные позиции и размеры подчанков вместо сканирования
        pbag_data = []
        pgen_data = []
        pmod_data = []
        
        # Парсим pbag данные напрямую по сохраненной позиции
        if 'pbag' in self.chunk_info:
            pbag_pos, pbag_size = self.chunk_info['pbag']
            
            # Переходим к pbag
            self.file.seek(pbag_pos)
            # Парсим только нужные зоны
            pbag_data = self._parse_pbag_selective(pbag_size, start_bag_index, end_bag_index)
        
        # Парсим pmod данные напрямую по сохраненной позиции
        if 'pmod' in self.chunk_info:
            pmod_pos, pmod_size = self.chunk_info['pmod']
            
            # Переходим к pmod
            self.file.seek(pmod_pos)
            # Calculate correct start/end indices for modulators
            mod_start_idx, mod_end_idx = self._calculate_preset_modulator_indices(start_bag_index, end_bag_index)
            pmod_data = self._parse_pmod_selective(pmod_size, mod_start_idx, mod_end_idx)
        
        # Парсим pgen данные напрямую по сохраненной позиции
        if 'pgen' in self.chunk_info:
            pgen_pos, pgen_size = self.chunk_info['pgen']
            
            # Переходим к pgen
            self.file.seek(pgen_pos)
            # Calculate correct start/end indices for generators
            gen_start_idx, gen_end_idx = self._calculate_preset_generator_indices(start_bag_index, end_bag_index)
            pgen_data = self._parse_pgen_selective(pgen_size, gen_start_idx, gen_end_idx)
        
        # Теперь парсим зоны пресетов только для нужного диапазона
        if pbag_data and pgen_data and pmod_data:
            self._parse_preset_zones_selective(pbag_data, pgen_data, pmod_data, start_bag_index, end_bag_index)
            
            # Автоматически парсим все инструменты, используемые в этом пресете
            self._parse_preset_instruments(start_bag_index, end_bag_index)
    
    def _parse_pdta_instruments_selective(self, list_size: int, start_offset: int, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсинг данных инструментов из LIST pdta чанка выборочно"""
        if not self.file:
            return
            
        # Используем заранее сохраненные позиции и размеры подчанков вместо сканирования
        ibag_data = []
        igen_data = []
        imod_data = []
        
        # Парсим ibag данные напрямую по сохраненной позиции
        if 'ibag' in self.chunk_info:
            ibag_pos, ibag_size = self.chunk_info['ibag']
            
            # Переходим к ibag
            self.file.seek(ibag_pos)
            # Парсим только нужные зоны
            ibag_data = self._parse_ibag_selective(ibag_size, start_bag_index, end_bag_index)
        
        # Парсим imod данные напрямую по сохраненной позиции
        if 'imod' in self.chunk_info:
            imod_pos, imod_size = self.chunk_info['imod']
            
            # Переходим к imod
            self.file.seek(imod_pos)
            # Calculate correct start/end indices for modulators
            mod_start_idx, mod_end_idx = self._calculate_instrument_modulator_indices(start_bag_index, end_bag_index)
            imod_data = self._parse_imod_selective(imod_size, mod_start_idx, mod_end_idx)
        
        # Парсим igen данные напрямую по сохраненной позиции
        if 'igen' in self.chunk_info:
            igen_pos, igen_size = self.chunk_info['igen']
            
            # Переходим к igen
            self.file.seek(igen_pos)
            # Calculate correct start/end indices for generators
            gen_start_idx, gen_end_idx = self._calculate_instrument_generator_indices(start_bag_index, end_bag_index)
            igen_data = self._parse_igen_selective(igen_size, gen_start_idx, gen_end_idx)
        
        # Теперь парсим зоны инструментов только для нужного диапазона
        if ibag_data and igen_data and imod_data:
            self._parse_instrument_zones_selective(ibag_data, igen_data, imod_data, start_bag_index, end_bag_index)
    
    def _parse_pbag_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные зоны пресетов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Читаем только нужные зоны
        zones_needed = end_index - start_index
        start_position = 4 * start_index  # 4 байта на зону
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(4 * zones_needed)
        if len(raw_data) < 4 * zones_needed:
            return []
            
        # Распаковываем нужные зоны
        uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
        preset_zone_indices = uint16_array.reshape(-1, 2)
        return preset_zone_indices.tolist()
    
    def _parse_ibag_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные зоны инструментов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Читаем только нужные зоны
        zones_needed = end_index - start_index
        start_position = 4 * start_index  # 4 байта на зону
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(4 * zones_needed)
        if len(raw_data) < 4 * zones_needed:
            return []
            
        # Распаковываем нужные зоны
        uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
        instrument_zone_indices = uint16_array.reshape(-1, 2)
        return instrument_zone_indices.tolist()
    
    def _parse_pgen_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные генераторы пресетов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Каждый генератор занимает 4 байта (2 байта типа + 2 байта значения)
        generator_size = 4
        generators_needed = end_index - start_index
        start_position = generator_size * start_index
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(generator_size * generators_needed)
        if len(raw_data) < generator_size * generators_needed:
            return []
            
        # Распаковываем нужные генераторы
        # Преобразуем байты в массив структурированных данных
        gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
        generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
        generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        return generators
    
    def _parse_igen_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные генераторы инструментов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Каждый генератор занимает 4 байта (2 байта типа + 2 байта значения)
        generator_size = 4
        generators_needed = end_index - start_index
        start_position = generator_size * start_index
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(generator_size * generators_needed)
        if len(raw_data) < generator_size * generators_needed:
            return []
            
        # Распаковываем нужные генераторы
        # Преобразуем байты в массив структурированных данных
        gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
        generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
        generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        return generators
    
    def _parse_pmod_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные модуляторы пресетов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Каждый модулятор занимает 10 байт
        modulator_size = 10
        modulators_needed = end_index - start_index
        start_position = modulator_size * start_index
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(modulator_size * modulators_needed)
        if len(raw_data) < modulator_size * modulators_needed:
            return []
            
        # Распаковываем нужные модуляторы
        modulators = []
        for i in range(0, len(raw_data), 10):
            if i + 10 <= len(raw_data):
                mod_data = raw_data[i:i+10]
                
                modulator = SF2Modulator()
                
                # Парсинг источника модуляции (2 байта)
                source = struct.unpack('<H', mod_data[0:2])[0]
                modulator.source_oper = source & 0x000F
                modulator.source_polarity = (source & 0x0010) >> 4
                modulator.source_type = (source & 0x0020) >> 5
                modulator.source_direction = (source & 0x0040) >> 6
                modulator.source_index = (source & 0xFF80) >> 7
                
                # Парсинг управления модуляцией (2 байта)
                control = struct.unpack('<H', mod_data[2:4])[0]
                modulator.control_oper = control & 0x000F
                modulator.control_polarity = (control & 0x0010) >> 4
                modulator.control_type = (control & 0x0020) >> 5
                modulator.control_direction = (control & 0x0040) >> 6
                modulator.control_index = (control & 0xFF80) >> 7
                
                # Парсинг цели модуляции (2 байта)
                modulator.destination = struct.unpack('<H', mod_data[4:6])[0]
                
                # Парсинг глубины модуляции (2 байта)
                modulator.amount = struct.unpack('<h', mod_data[6:8])[0]  # signed short
                
                # Парсинг источника глубины модуляции (2 байта)
                amount_source = struct.unpack('<H', mod_data[8:10])[0]
                modulator.amount_source_oper = amount_source & 0x000F
                modulator.amount_source_polarity = (amount_source & 0x0010) >> 4
                modulator.amount_source_type = (amount_source & 0x0020) >> 5
                modulator.amount_source_direction = (amount_source & 0x0040) >> 6
                modulator.amount_source_index = (amount_source & 0xFF80) >> 7
                
                modulators.append(modulator)
        return modulators
    
    def _parse_imod_selective(self, chunk_size: int, start_index: int, end_index: Optional[int] = None):
        """Парсит только нужные модуляторы инструментов выборочно"""
        if not self.file:
            return []
            
        if end_index is None:
            end_index = start_index + 1
            
        # Каждый модулятор занимает 10 байт
        modulator_size = 10
        modulators_needed = end_index - start_index
        start_position = modulator_size * start_index
        self.file.seek(start_position, 1)  # Относительный seek
        
        raw_data = self.file.read(modulator_size * modulators_needed)
        if len(raw_data) < modulator_size * modulators_needed:
            return []
            
        # Распаковываем нужные модуляторы
        modulators = []
        for i in range(0, len(raw_data), 10):
            if i + 10 <= len(raw_data):
                mod_data = raw_data[i:i+10]
                
                modulator = SF2Modulator()
                
                # Парсинг источника модуляции (2 байта)
                source = struct.unpack('<H', mod_data[0:2])[0]
                modulator.source_oper = source & 0x000F
                modulator.source_polarity = (source & 0x0010) >> 4
                modulator.source_type = (source & 0x0020) >> 5
                modulator.source_direction = (source & 0x0040) >> 6
                modulator.source_index = (source & 0xFF80) >> 7
                
                # Парсинг управления модуляцией (2 байта)
                control = struct.unpack('<H', mod_data[2:4])[0]
                modulator.control_oper = control & 0x000F
                modulator.control_polarity = (control & 0x0010) >> 4
                modulator.control_type = (control & 0x0020) >> 5
                modulator.control_direction = (control & 0x0040) >> 6
                modulator.control_index = (control & 0xFF80) >> 7
                
                # Парсинг цели модуляции (2 байта)
                modulator.destination = struct.unpack('<H', mod_data[4:6])[0]
                
                # Парсинг глубины модуляции (2 байта)
                modulator.amount = struct.unpack('<h', mod_data[6:8])[0]  # signed short
                
                # Парсинг источника глубины модуляции (2 байта)
                amount_source = struct.unpack('<H', mod_data[8:10])[0]
                modulator.amount_source_oper = amount_source & 0x000F
                modulator.amount_source_polarity = (amount_source & 0x0010) >> 4
                modulator.amount_source_type = (amount_source & 0x0020) >> 5
                modulator.amount_source_direction = (amount_source & 0x0040) >> 6
                modulator.amount_source_index = (amount_source & 0xFF80) >> 7
                
                modulators.append(modulator)
        return modulators

    def _calculate_preset_generator_indices(self, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Calculate the actual start and end generator indices for a preset zone range"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Read pbag data to determine generator indices
        pbag_info = self.chunk_info.get('pbag')
        if not pbag_info:
            return 0, 1
        
        pbag_pos, _ = pbag_info
            
        # Calculate file position for the relevant pbag entries
        pbag_entry_size = 4  # 2 bytes gen_ndx + 2 bytes mod_ndx
        start_file_pos = pbag_pos + (start_bag_index * pbag_entry_size)
        
        self.file.seek(start_file_pos)
        
        # Read the generator indices for start and end bags
        start_data = self.file.read(pbag_entry_size)
        if len(start_data) >= pbag_entry_size:
            start_gen_ndx, _ = struct.unpack('<HH', start_data)
        else:
            start_gen_ndx = 0
            
        # For end index, we need to find the terminal generator
        end_file_pos = pbag_pos + (end_bag_index * pbag_entry_size)
        self.file.seek(end_file_pos)
        end_data = self.file.read(pbag_entry_size)
        if len(end_data) >= pbag_entry_size:
            end_gen_ndx, _ = struct.unpack('<HH', end_data)
        else:
            # If we can't read the end, estimate based on typical structure
            end_gen_ndx = start_gen_ndx + 10  # Estimate
            
        return start_gen_ndx, end_gen_ndx

    def _calculate_preset_modulator_indices(self, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Calculate the actual start and end modulator indices for a preset zone range"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Read pbag data to determine modulator indices
        pbag_info = self.chunk_info.get('pbag')
        if not pbag_info:
            return 0, 1
        
        pbag_pos, _ = pbag_info
            
        # Calculate file position for the relevant pbag entries
        pbag_entry_size = 4  # 2 bytes gen_ndx + 2 bytes mod_ndx
        start_file_pos = pbag_pos + (start_bag_index * pbag_entry_size)
        
        self.file.seek(start_file_pos)
        
        # Read the modulator indices for start and end bags
        start_data = self.file.read(pbag_entry_size)
        if len(start_data) >= pbag_entry_size:
            _, start_mod_ndx = struct.unpack('<HH', start_data)
        else:
            start_mod_ndx = 0
            
        # For end index, we need to find the terminal modulator
        end_file_pos = pbag_pos + (end_bag_index * pbag_entry_size)
        self.file.seek(end_file_pos)
        end_data = self.file.read(pbag_entry_size)
        if len(end_data) >= pbag_entry_size:
            _, end_mod_ndx = struct.unpack('<HH', end_data)
        else:
            # If we can't read the end, estimate based on typical structure
            end_mod_ndx = start_mod_ndx + 5  # Estimate
            
        return start_mod_ndx, end_mod_ndx

    def _calculate_instrument_generator_indices(self, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Calculate the actual start and end generator indices for an instrument zone range"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Read ibag data to determine generator indices
        ibag_info = self.chunk_info.get('ibag')
        if not ibag_info:
            return 0, 1
        
        ibag_pos, _ = ibag_info
            
        # Calculate file position for the relevant ibag entries
        ibag_entry_size = 4  # 2 bytes gen_ndx + 2 bytes mod_ndx
        start_file_pos = ibag_pos + (start_bag_index * ibag_entry_size)
        
        self.file.seek(start_file_pos)
        
        # Read the generator indices for start and end bags
        start_data = self.file.read(ibag_entry_size)
        if len(start_data) >= ibag_entry_size:
            start_gen_ndx, _ = struct.unpack('<HH', start_data)
        else:
            start_gen_ndx = 0
            
        # For end index, we need to find the terminal generator
        end_file_pos = ibag_pos + (end_bag_index * ibag_entry_size)
        self.file.seek(end_file_pos)
        end_data = self.file.read(ibag_entry_size)
        if len(end_data) >= ibag_entry_size:
            end_gen_ndx, _ = struct.unpack('<HH', end_data)
        else:
            # If we can't read the end, estimate based on typical structure
            end_gen_ndx = start_gen_ndx + 10  # Estimate
            
        return start_gen_ndx, end_gen_ndx

    def _calculate_instrument_modulator_indices(self, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Calculate the actual start and end modulator indices for an instrument zone range"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Read ibag data to determine modulator indices
        ibag_info = self.chunk_info.get('ibag')
        if not ibag_info:
            return 0, 1
        
        ibag_pos, _ = ibag_info
            
        # Calculate file position for the relevant ibag entries
        ibag_entry_size = 4  # 2 bytes gen_ndx + 2 bytes mod_ndx
        start_file_pos = ibag_pos + (start_bag_index * ibag_entry_size)
        
        self.file.seek(start_file_pos)
        
        # Read the modulator indices for start and end bags
        start_data = self.file.read(ibag_entry_size)
        if len(start_data) >= ibag_entry_size:
            _, start_mod_ndx = struct.unpack('<HH', start_data)
        else:
            start_mod_ndx = 0
            
        # For end index, we need to find the terminal modulator
        end_file_pos = ibag_pos + (end_bag_index * ibag_entry_size)
        self.file.seek(end_file_pos)
        end_data = self.file.read(ibag_entry_size)
        if len(end_data) >= ibag_entry_size:
            _, end_mod_ndx = struct.unpack('<HH', end_data)
        else:
            # If we can't read the end, estimate based on typical structure
            end_mod_ndx = start_mod_ndx + 5  # Estimate
            
        return start_mod_ndx, end_mod_ndx
    
    def _parse_preset_zones_selective(self, pbag_data, pgen_data, pmod_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит зоны пресетов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Обрабатываем только нужные зоны
        for i in range(start_bag_index, min(end_bag_index, len(pbag_data))):
            if i < len(pbag_data):
                gen_ndx, mod_ndx = pbag_data[i]
                
                # Создаем зону пресета
                preset_zone = SF2PresetZone()
                preset_zone.gen_ndx = gen_ndx
                preset_zone.mod_ndx = mod_ndx
                
                # Добавляем зону к соответствующему пресету
                for preset in self.presets:
                    if preset.preset_bag_index <= i < (preset.preset_bag_index + 1 if preset.preset_bag_index + 1 < len(pbag_data) else len(pbag_data)):
                        preset.zones.append(preset_zone)
                        break
        
        # Теперь парсим генераторы и модуляторы для всех зон
        self._parse_preset_generators_selective(pgen_data, start_bag_index, end_bag_index)
        self._parse_preset_modulators_selective(pmod_data, start_bag_index, end_bag_index)
    
    def _parse_preset_generators_selective(self, pgen_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит генераторы для зон пресетов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(pgen_data):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех пресетов в диапазоне
        all_zone_boundaries = []
        for preset in self.presets:
            for zone in preset.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(pgen_data)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((preset, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам пресетов
        instrument_names = [inst.name for inst in self.instruments] if self.instruments else []
        
        for preset, zone, start_idx, end_idx in all_zone_boundaries:
            # Обрабатываем генераторы для этой зоны
            for j in range(start_idx, min(end_idx, len(pgen_data))):
                gen_type, gen_amount = pgen_data[j]
                
                # Сохраняем генератор в словаре зоны пресета
                zone.generators[gen_type] = gen_amount
                
                # Быстрая обработка специфических генераторов без множественных условий
                if gen_type == 41:  # instrument
                    zone.instrument_index = gen_amount
                    # Ищем имя инструмента
                    if 0 <= gen_amount < len(instrument_names):
                        zone.instrument_name = instrument_names[gen_amount]
                elif gen_type == 42:  # keyRange
                    zone.lokey = gen_amount & 0xFF
                    zone.hikey = (gen_amount >> 8) & 0xFF
                elif gen_type == 43:  # velRange
                    zone.lovel = gen_amount & 0xFF
                    zone.hivel = (gen_amount >> 8) & 0xFF
                elif gen_type == 8:  # initialFilterFc
                    zone.initialFilterFc = gen_amount
                elif gen_type == 9:  # initialFilterQ
                    zone.initial_filterQ = gen_amount
                elif gen_type == 21:  # pan
                    zone.Pan = gen_amount
                elif gen_type == 22:  # delayModLFO
                    zone.DelayLFO1 = gen_amount
                elif gen_type == 23:  # freqModLFO
                    zone.LFO1Freq = gen_amount
                elif gen_type == 24:  # delayVibLFO
                    zone.DelayLFO2 = gen_amount
                elif gen_type == 25:  # delayModEnv
                    zone.DelayFilEnv = gen_amount
                elif gen_type == 26:  # attackModEnv
                    zone.AttackFilEnv = gen_amount
                elif gen_type == 27:  # holdModEnv
                    zone.HoldFilEnv = gen_amount
                elif gen_type == 28:  # decayModEnv
                    zone.DecayFilEnv = gen_amount
                elif gen_type == 29:  # sustainModEnv
                    zone.SustainFilEnv = gen_amount
                elif gen_type == 30:  # releaseModEnv
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
                elif gen_type == 44:  # keynumToVolEnvDecay
                    zone.KeynumToVolEnvDecay = gen_amount
                elif gen_type == 50:  # coarseTune
                    zone.CoarseTune = gen_amount
                elif gen_type == 51:  # fineTune
                    zone.FineTune = gen_amount
    
    def _parse_preset_modulators_selective(self, pmod_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит модуляторы для зон пресетов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Привязываем модуляторы к зонам пресетов
        for preset in self.presets:
            for zone in preset.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(pmod_data)):
                    if pmod_data[i].source_oper == 0 and pmod_data[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = pmod_data[j]
                    zone.modulators.append(modulator)
    
    def _parse_preset_instruments(self, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Автоматически парсит все инструменты, используемые в пресете"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Читаем pgen данные для определения инструментов
        if 'pgen' in self.chunk_info:
            pgen_pos, pgen_size = self.chunk_info['pgen']
            
            # Переходим к pgen
            self.file.seek(pgen_pos)
            
            # Парсим генераторы для определения инструментов
            gen_start_idx, gen_end_idx = self._calculate_preset_generator_indices(start_bag_index, end_bag_index)
            pgen_data = self._parse_pgen_selective(pgen_size, gen_start_idx, gen_end_idx)
            
            # Ищем инструменты в генераторах
            instrument_indices = set()
            for gen_type, gen_amount in pgen_data:
                if gen_type == 41:  # instrument generator
                    instrument_indices.add(gen_amount)
            
            # Парсим все найденные инструменты
            for inst_index in instrument_indices:
                if inst_index < len(self.instruments):
                    self._ensure_instrument_parsed(inst_index)
    
    def _parse_instrument_zones_selective(self, ibag_data, igen_data, imod_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит зоны инструментов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Обрабатываем только нужные зоны
        for i in range(start_bag_index, min(end_bag_index, len(ibag_data))):
            if i < len(ibag_data):
                gen_ndx, mod_ndx = ibag_data[i]
                
                # Создаем зону инструмента
                inst_zone = SF2InstrumentZone()
                inst_zone.gen_ndx = gen_ndx
                inst_zone.mod_ndx = mod_ndx
                
                # Добавляем зону к соответствующему инструменту
                for instrument in self.instruments:
                    if instrument.instrument_bag_index <= i < (instrument.instrument_bag_index + 1 if instrument.instrument_bag_index + 1 < len(ibag_data) else len(ibag_data)):
                        instrument.zones.append(inst_zone)
                        break
        
        # Теперь парсим генераторы и модуляторы для всех зон
        self._parse_instrument_generators_selective(igen_data, start_bag_index, end_bag_index)
        self._parse_instrument_modulators_selective(imod_data, start_bag_index, end_bag_index)
    
    def _parse_instrument_generators_selective(self, igen_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит генераторы для зон инструментов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(igen_data):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех инструментов в диапазоне
        all_zone_boundaries = []
        for instrument in self.instruments:
            for zone in instrument.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(igen_data)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((instrument, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам инструментов
        for instrument, zone, start_idx, end_idx in all_zone_boundaries:
            # Обрабатываем генераторы для этой зоны
            for j in range(start_idx, min(end_idx, len(igen_data))):
                gen_type, gen_amount = igen_data[j]
                
                # Сохраняем генератор в зоне инструмента
                zone.generators[gen_type] = gen_amount
                
                # Быстрая обработка специфических генераторов без множественных условий
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
                elif gen_type == 42:  # keyRange
                    zone.lokey = gen_amount & 0xFF
                    zone.hikey = (gen_amount >> 8) & 0xFF
                elif gen_type == 43:  # velRange
                    zone.lovel = gen_amount & 0xFF
                    zone.hivel = (gen_amount >> 8) & 0xFF
    
    def _parse_instrument_modulators_selective(self, imod_data, start_bag_index: int, end_bag_index: Optional[int] = None):
        """Парсит модуляторы для зон инструментов выборочно"""
        if end_bag_index is None:
            end_bag_index = start_bag_index + 1
            
        # Привязываем модуляторы к зонам инструментов
        for instrument in self.instruments:
            for zone in instrument.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(imod_data)):
                    if imod_data[i].source_oper == 0 and imod_data[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = imod_data[j]
                    zone.modulators.append(modulator)
    
    def _parse_pdta_presets(self):
        """Парсинг данных пресетов из LIST pdta чанка"""
        if not self.file:
            return
            
        # Используем заранее сохраненные позиции подчанков вместо сканирования LIST чанка
        pbag_data = []
        pgen_data = []
        pmod_data = []
        
        # Парсим pbag данные напрямую по сохраненной позиции
        if 'pbag' in self.chunk_info:
            pbag_pos, pbag_size = self.chunk_info['pbag']
            
            # Переходим к pbag
            self.file.seek(pbag_pos)
            # Читаем и парсим pbag данные
            pbag_raw_data = self.file.read(pbag_size)
            pbag_data = self._parse_bag_raw_data(pbag_raw_data)
        
        # Парсим pmod данные напрямую по сохраненной позиции
        if 'pmod' in self.chunk_info:
            pmod_pos, pmod_size = self.chunk_info['pmod']
            
            # Переходим к pmod
            self.file.seek(pmod_pos)
            # Читаем и парсим pmod данные
            pmod_raw_data = self.file.read(pmod_size)
            pmod_data = self._parse_pmod_raw_data(pmod_raw_data)
        
        # Парсим pgen данные напрямую по сохраненной позиции
        if 'pgen' in self.chunk_info:
            pgen_pos, pgen_size = self.chunk_info['pgen']
            
            # Переходим к pgen
            self.file.seek(pgen_pos)
            # Читаем и парсим pgen данные
            pgen_raw_data = self.file.read(pgen_size)
            pgen_data = self._parse_gen_raw_data(pgen_raw_data)
        
        # Теперь парсим зоны пресетов для всех пресетов
        self._parse_preset_zones(pbag_data, pgen_data, pmod_data)
    
    def _parse_pdta_instruments(self):
        """Парсинг данных инструментов из LIST pdta чанка"""
        if not self.file:
            return
            
        # Используем заранее сохраненные позиции подчанков вместо сканирования LIST чанка
        ibag_data = []
        igen_data = []
        imod_data = []
        
        # Парсим ibag данные напрямую по сохраненной позиции
        if 'ibag' in self.chunk_info:
            ibag_pos, ibag_size = self.chunk_info['ibag']
            
            # Переходим к ibag
            self.file.seek(ibag_pos)
            # Читаем и парсим ibag данные
            ibag_raw_data = self.file.read(ibag_size)
            ibag_data = self._parse_ibag_raw_data(ibag_raw_data)
        
        # Парсим imod данные напрямую по сохраненной позиции
        if 'imod' in self.chunk_info:
            imod_pos, imod_size = self.chunk_info['imod']
            
            # Переходим к imod
            self.file.seek(imod_pos)
            # Читаем и парсим imod данные
            imod_raw_data = self.file.read(imod_size)
            imod_data = self._parse_imod_raw_data(imod_raw_data)
        
        # Парсим igen данные напрямую по сохраненной позиции
        if 'igen' in self.chunk_info:
            igen_pos, igen_size = self.chunk_info['igen']
            
            # Переходим к igen
            self.file.seek(igen_pos)
            # Читаем и парсим igen данные
            igen_raw_data = self.file.read(igen_size)
            igen_data = self._parse_igen_raw_data(igen_raw_data)
        
        # Теперь парсим зоны инструментов для всех инструментов
        self._parse_instrument_zones(ibag_data, igen_data, imod_data)
    
    def _parse_bag_raw_data(self, raw_data):
        """Парсит сырые данные pbag / ibag чанка"""
        # Каждая зона пресета 4 байта
        
        # Распаковываем все индексы зон одной операцией
        # Преобразуем байты в массив unsigned 16-bit чисел
        uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
        # Решейпим в массив пар (gen_ndx, mod_ndx)
        preset_zone_indices = uint16_array.reshape(-1, 2)
        return preset_zone_indices.tolist()
    
    def _parse_gen_raw_data(self, raw_data):
        """Парсит сырые данные pgen / igen чанка"""
        # Распаковываем все генераторы одной операцией
        # Преобразуем байты в массив структурированных данных
        gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
        generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
        generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        return generators
    
    def _parse_pmod_raw_data(self, raw_data):
        """Парсит сырые данные pmod чанка"""
        # Распаковываем все модуляторы одной операцией
        modulators = []
        for i in range(0, len(raw_data), 10):
            if i + 10 <= len(raw_data):
                mod_data = raw_data[i:i+10]
                
                modulator = SF2Modulator()
                
                # Парсинг источника модуляции (2 байта)
                source = struct.unpack('<H', mod_data[0:2])[0]
                modulator.source_oper = source & 0x000F
                modulator.source_polarity = (source & 0x0010) >> 4
                modulator.source_type = (source & 0x0020) >> 5
                modulator.source_direction = (source & 0x0040) >> 6
                modulator.source_index = (source & 0xFF80) >> 7
                
                # Парсинг управления модуляцией (2 байта)
                control = struct.unpack('<H', mod_data[2:4])[0]
                modulator.control_oper = control & 0x000F
                modulator.control_polarity = (control & 0x0010) >> 4
                modulator.control_type = (control & 0x0020) >> 5
                modulator.control_direction = (control & 0x0040) >> 6
                modulator.control_index = (control & 0xFF80) >> 7
                
                # Парсинг цели модуляции (2 байта)
                modulator.destination = struct.unpack('<H', mod_data[4:6])[0]
                
                # Парсинг глубины модуляции (2 байта)
                modulator.amount = struct.unpack('<h', mod_data[6:8])[0]  # signed short
                
                # Парсинг источника глубины модуляции (2 байта)
                amount_source = struct.unpack('<H', mod_data[8:10])[0]
                modulator.amount_source_oper = amount_source & 0x000F
                modulator.amount_source_polarity = (amount_source & 0x0010) >> 4
                modulator.amount_source_type = (amount_source & 0x0020) >> 5
                modulator.amount_source_direction = (amount_source & 0x0040) >> 6
                modulator.amount_source_index = (amount_source & 0xFF80) >> 7
                
                modulators.append(modulator)
        return modulators
    
    def _parse_ibag_raw_data(self, raw_data):
        """Парсит сырые данные ibag чанка"""
        # Каждая зона инструмента 4 байта
        num_zones = len(raw_data) // 4
        
        # Распаковываем все индексы зон одной операцией
        # Преобразуем байты в массив unsigned 16-bit чисел
        uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
        # Решейпим в массив пар (gen_ndx, mod_ndx)
        instrument_zone_indices = uint16_array.reshape(-1, 2)
        return instrument_zone_indices.tolist()
    
    def _parse_igen_raw_data(self, raw_data):
        """Парсит сырые данные igen чанка"""
        # Распаковываем все генераторы одной операцией
        # Преобразуем байты в массив структурированных данных
        gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
        generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
        generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        return generators
    
    def _parse_imod_raw_data(self, raw_data):
        """Парсит сырые данные imod чанка"""
        # Распаковываем все модуляторы одной операцией
        modulators = []
        for i in range(0, len(raw_data), 10):
            if i + 10 <= len(raw_data):
                mod_data = raw_data[i:i+10]
                
                modulator = SF2Modulator()
                
                # Парсинг источника модуляции (2 байта)
                source = struct.unpack('<H', mod_data[0:2])[0]
                modulator.source_oper = source & 0x000F
                modulator.source_polarity = (source & 0x0010) >> 4
                modulator.source_type = (source & 0x0020) >> 5
                modulator.source_direction = (source & 0x0040) >> 6
                modulator.source_index = (source & 0xFF80) >> 7
                
                # Парсинг управления модуляцией (2 байта)
                control = struct.unpack('<H', mod_data[2:4])[0]
                modulator.control_oper = control & 0x000F
                modulator.control_polarity = (control & 0x0010) >> 4
                modulator.control_type = (control & 0x0020) >> 5
                modulator.control_direction = (control & 0x0040) >> 6
                modulator.control_index = (control & 0xFF80) >> 7
                
                # Парсинг цели модуляции (2 байта)
                modulator.destination = struct.unpack('<H', mod_data[4:6])[0]
                
                # Парсинг глубины модуляции (2 байта)
                modulator.amount = struct.unpack('<h', mod_data[6:8])[0]  # signed short
                
                # Парсинг источника глубины модуляции (2 байта)
                amount_source = struct.unpack('<H', mod_data[8:10])[0]
                modulator.amount_source_oper = amount_source & 0x000F
                modulator.amount_source_polarity = (amount_source & 0x0010) >> 4
                modulator.amount_source_type = (amount_source & 0x0020) >> 5
                modulator.amount_source_direction = (amount_source & 0x0040) >> 6
                modulator.amount_source_index = (amount_source & 0xFF80) >> 7
                
                modulators.append(modulator)
        return modulators
    
    def _parse_preset_zones(self, pbag_data, pgen_data, pmod_data):
        """Парсит зоны пресетов используя предварительно собранные данные"""
        if not self.presets or not pbag_data:
            return
        
        # Предварительно вычисляем все границы зон
        zone_boundaries = []
        for i in range(len(self.presets)):
            start_idx = self.presets[i].preset_bag_index
            end_idx = self.presets[i+1].preset_bag_index if i < len(self.presets) - 1 else len(pbag_data) - 1
            zone_boundaries.append((start_idx, end_idx))
        
        # Привязываем зоны к пресетам
        for i, (start_idx, end_idx) in enumerate(zone_boundaries):
            preset = self.presets[i]
            # Добавляем все зоны для этого пресета
            for j in range(start_idx, min(end_idx, len(pbag_data))):
                gen_ndx, mod_ndx = pbag_data[j]
                
                # Создаем зону пресета
                preset_zone = SF2PresetZone()
                preset_zone.preset = preset.preset
                preset_zone.bank = preset.bank
                preset_zone.instrument_index = 0  # Будет обновлено позже
                preset_zone.instrument_name = ""
                preset_zone.gen_ndx = gen_ndx
                preset_zone.mod_ndx = mod_ndx
                
                preset.zones.append(preset_zone)
        
        # Теперь парсим генераторы и модуляторы для всех зон
        self._parse_preset_generators(pgen_data)
        self._parse_preset_modulators(pmod_data)
    
    def _configure_preset_zone_from_generators(self, zone: SF2PresetZone, pgen_data: List[Tuple[int, int]], start_idx: int, end_idx: int, instrument_names: List[str]):
        """Конфигурирует зону пресета на основе списка генераторов"""
        # Обрабатываем генераторы для этой зоны
        for j in range(start_idx, min(end_idx, len(pgen_data))):
            gen_type, gen_amount = pgen_data[j]
            
            # Сохраняем генератор в словаре зоны пресета
            zone.generators[gen_type] = gen_amount
            
            # Быстрая обработка специфических генераторов без множественных условий
            if gen_type == 41:  # instrument
                zone.instrument_index = gen_amount
                # Ищем имя инструмента
                if 0 <= gen_amount < len(instrument_names):
                    zone.instrument_name = instrument_names[gen_amount]
            elif gen_type == 42:  # keyRange
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 43:  # velRange
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF
            elif gen_type == 8:  # initialFilterFc
                zone.initialFilterFc = gen_amount
            elif gen_type == 9:  # initialFilterQ
                zone.initial_filterQ = gen_amount
            elif gen_type == 21:  # pan
                zone.Pan = gen_amount
            elif gen_type == 22:  # delayModLFO
                zone.DelayLFO1 = gen_amount
            elif gen_type == 23:  # freqModLFO
                zone.LFO1Freq = gen_amount
            elif gen_type == 24:  # delayVibLFO
                zone.DelayLFO2 = gen_amount
            elif gen_type == 25:  # delayModEnv
                zone.DelayFilEnv = gen_amount
            elif gen_type == 26:  # attackModEnv
                zone.AttackFilEnv = gen_amount
            elif gen_type == 27:  # holdModEnv
                zone.HoldFilEnv = gen_amount
            elif gen_type == 28:  # decayModEnv
                zone.DecayFilEnv = gen_amount
            elif gen_type == 29:  # sustainModEnv
                zone.SustainFilEnv = gen_amount
            elif gen_type == 30:  # releaseModEnv
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
            elif gen_type == 44:  # keynumToVolEnvDecay
                zone.KeynumToVolEnvDecay = gen_amount
            elif gen_type == 50:  # coarseTune
                zone.CoarseTune = gen_amount
            elif gen_type == 51:  # fineTune
                zone.FineTune = gen_amount
    
    def _parse_preset_generators(self, pgen_data):
        """Парсит генераторы для всех зон пресетов"""
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(pgen_data):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех пресетов
        all_zone_boundaries = []
        for preset in self.presets:
            for zone in preset.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(pgen_data)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((preset, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам пресетов
        instrument_names = [inst.name for inst in self.instruments] if self.instruments else []
        
        for preset, zone, start_idx, end_idx in all_zone_boundaries:
            self._configure_preset_zone_from_generators(zone, pgen_data, start_idx, end_idx, instrument_names)
    
    def _parse_preset_modulators(self, pmod_data):
        """Парсит модуляторы для всех зон пресетов"""
        # Привязываем модуляторы к зонам пресетов
        for preset in self.presets:
            for zone in preset.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(pmod_data)):
                    if pmod_data[i].source_oper == 0 and pmod_data[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = pmod_data[j]
                    zone.modulators.append(modulator)
    
    def _parse_instrument_zones(self, ibag_data, igen_data, imod_data):
        """Парсит зоны инструментов используя предварительно собранные данные"""
        if not self.instruments or not ibag_data:
            return
        
        # Предварительно вычисляем все границы зон
        zone_boundaries = []
        for i in range(len(self.instruments)):
            start_idx = self.instruments[i].instrument_bag_index
            end_idx = self.instruments[i+1].instrument_bag_index if i < len(self.instruments) - 1 else len(ibag_data) - 1
            zone_boundaries.append((start_idx, end_idx))
        
        # Привязываем зоны к инструментам
        for i, (start_idx, end_idx) in enumerate(zone_boundaries):
            instrument = self.instruments[i]
            # Добавляем все зоны для этого инструмента
            for j in range(start_idx, min(end_idx, len(ibag_data))):
                gen_ndx, mod_ndx = ibag_data[j]
                
                # Создаем зону инструмента
                inst_zone = SF2InstrumentZone()
                inst_zone.sample_index = 0  # Будет обновлено позже
                inst_zone.gen_ndx = gen_ndx
                inst_zone.mod_ndx = mod_ndx
                
                instrument.zones.append(inst_zone)
        
        # Теперь парсим генераторы и модуляторы для всех зон
        self._parse_instrument_generators(igen_data)
        self._parse_instrument_modulators(imod_data)
    
    def _configure_instrument_zone_from_generators(self, zone: SF2InstrumentZone, igen_data: List[Tuple[int, int]], start_idx: int, end_idx: int):
        """Конфигурирует зону инструмента на основе списка генераторов"""
        # Обрабатываем генераторы для этой зоны
        for j in range(start_idx, min(end_idx, len(igen_data))):
            gen_type, gen_amount = igen_data[j]
            
            # Сохраняем генератор в зоне инструмента
            zone.generators[gen_type] = gen_amount
            
            # Быстрая обработка специфических генераторов без множественных условий
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
            elif gen_type == 42:  # keyRange
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 43:  # velRange
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF
    
    def _parse_instrument_generators(self, igen_data):
        """Парсит генераторы для всех зон инструментов"""
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(igen_data):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех инструментов
        all_zone_boundaries = []
        for instrument in self.instruments:
            for zone in instrument.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(igen_data)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((instrument, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам инструментов
        for instrument, zone, start_idx, end_idx in all_zone_boundaries:
            self._configure_instrument_zone_from_generators(zone, igen_data, start_idx, end_idx)
    
    def _parse_instrument_modulators(self, imod_data):
        """Парсит модуляторы для всех зон инструментов"""
        # Привязываем модуляторы к зонам инструментов
        for instrument in self.instruments:
            for zone in instrument.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(imod_data)):
                    if imod_data[i].source_oper == 0 and imod_data[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = imod_data[j]
                    zone.modulators.append(modulator)
    
    def _parse_inst_chunk(self, chunk_size: int):
        """Парсинг чанка inst (заголовки инструментов)"""
        if not self.file:
            return
            
        num_instruments = chunk_size // 22  # Каждый заголовок инструмента 22 байта
        
        # Читаем все заголовки инструментов за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 22)  # Исключаем терминальный инструмент
        if len(raw_data) < chunk_size - 22:
            return
            
        # Распаковываем все заголовки инструментов одной операцией
        # Создаем структурированный тип данных для заголовка инструмента
        inst_dtype = np.dtype([
            ('name', 'S20'),  # 20 байт для имени
            ('inst_bag_ndx', '<u2')  # uint16
        ])
        
        # Преобразуем байты в массив структурированных данных
        inst_array = np.frombuffer(raw_data[:len(raw_data)//22*22], dtype=inst_dtype)
        
        # Создаем инструменты из структурированных данных
        for inst_record in inst_array:
            # Извлечение данных
            name = inst_record['name'].split(b'\x00')[0].decode('ascii', 'ignore')
            inst_bag_ndx = int(inst_record['inst_bag_ndx'])
            
            # Создаем инструмент
            sf2_instrument = SF2Instrument()
            sf2_instrument.name = name
            sf2_instrument.instrument_bag_index = inst_bag_ndx
            self.instruments.append(sf2_instrument)
    
    def _parse_shdr_chunk(self, chunk_size: int):
        """Парсинг чанка shdr (заголовки сэмплов)"""
        if not self.file:
            return
            
        num_samples = chunk_size // 46  # Каждый заголовок сэмпла 46 байт
        
        # Читаем все заголовки сэмплов за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 46)  # Исключаем терминальный заголовок
        if len(raw_data) < chunk_size - 46:
            return
            
        # Распаковываем все заголовки сэмплов одной операцией
        # Создаем структурированный тип данных для заголовка сэмпла
        shdr_dtype = np.dtype([
            ('name', 'S20'),  # 20 байт для имени
            ('start', '<u4'),  # uint32
            ('end', '<u4'),  # uint32
            ('start_loop', '<u4'),  # uint32
            ('end_loop', '<u4'),  # uint32
            ('sample_rate', '<u4'),  # uint32
            ('original_pitch', 'u1'),  # uint8
            ('pitch_correction', 'i1'),  # int8
            ('sample_link', '<u2'),  # uint16
            ('sample_type', '<u2')  # uint16
        ])
        
        # Преобразуем байты в массив структурированных данных
        shdr_array = np.frombuffer(raw_data[:len(raw_data)//46*46], dtype=shdr_dtype)
        
        # Создаем заголовки сэмплов из структурированных данных
        for shdr_record in shdr_array:
            # Извлечение данных
            name = shdr_record['name'].split(b'\x00')[0].decode('ascii', 'ignore')
            start = int(shdr_record['start'])
            end = int(shdr_record['end'])
            start_loop = int(shdr_record['start_loop'])
            end_loop = int(shdr_record['end_loop'])
            sample_rate = int(shdr_record['sample_rate'])
            original_pitch = int(shdr_record['original_pitch'])
            pitch_correction = int(shdr_record['pitch_correction'])
            sample_link = int(shdr_record['sample_link'])
            sample_type = int(shdr_record['sample_type'])
            
            # Создаем заголовок сэмпла
            sample_header = SF2SampleHeader()
            sample_header.name = name
            sample_header.start = start
            sample_header.end = end
            sample_header.start_loop = start_loop
            sample_header.end_loop = end_loop
            sample_header.sample_rate = sample_rate
            sample_header.original_pitch = original_pitch
            sample_header.pitch_correction = pitch_correction
            sample_header.link = sample_link
            sample_header.type = sample_type
            self.sample_headers.append(sample_header)
    
    def get_preset(self, program: int, bank: int) -> Optional[SF2Preset]:
        """
        Получает пресет по программе и банку с отложенной загрузкой.
        
        Args:
            program: номер программы (0-127)
            bank: номер банка (0-16383)
            
        Returns:
            SF2Preset или None если не найден
        """
        # Применяем маппинг банков, если он задан
        mapped_bank = self.bank_mapping.get(bank, bank)
        
        # Проверяем, не заблокирован ли банк
        if mapped_bank in self.bank_blacklist:
            return None
            
        # Проверяем, не заблокирован ли конкретный пресет
        preset_key = (mapped_bank, program)
        if preset_key in self.preset_blacklist:
            return None
        
        # Найти пресет по банку и программе
        preset = None
        preset_index = -1
        for i, p in enumerate(self.presets):
            # Используем маппированный банк для поиска
            if p.preset == program and p.bank == mapped_bank:
                preset = p
                preset_index = i
                break
        
        if preset is None:
            return None
        
        # Если полные данные пресета еще не распаршены, делаем это сейчас
        self._ensure_preset_parsed(preset_index)
        
        return preset
    
    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """
        Получает инструмент по индексу с отложенной загрузкой.
        
        Args:
            index: индекс инструмента
            
        Returns:
            SF2Instrument или None если не найден
        """
        if index < 0 or index >= len(self.instruments):
            return None
        
        # Если инструмент еще не распаршен, делаем это сейчас
        self._ensure_instrument_parsed(index)
            
        return self.instruments[index]
    
    def get_sample_header(self, index: int) -> Optional[SF2SampleHeader]:
        """
        Получает заголовок сэмпла по индексу с отложенной загрузкой.
        
        Args:
            index: индекс заголовка сэмпла
            
        Returns:
            SF2SampleHeader или None если не найден
        """
        # Если сэмплы еще не распаршены, делаем это сейчас
        if not self.samples_parsed:
            if not self.file or 'sdta' not in self.chunk_info:
                return None if index < 0 or index >= len(self.sample_headers) else self.sample_headers[index]
            
            sdta_pos, _ = self.chunk_info['sdta']
            self.file.seek(sdta_pos - 8)
            
            # Читаем заголовок LIST sdta
            list_header = self.file.read(8)
            if len(list_header) >= 8:
                list_size = struct.unpack('<I', list_header[4:8])[0]
                self._parse_sdta_samples(list_size - 4, sdta_pos + 4)
            self.samples_parsed = True
        
        if index < 0 or index >= len(self.sample_headers):
            return None
            
        return self.sample_headers[index]
    
    def _parse_sdta_samples(self, list_size: int, start_offset: int):
        """Парсинг данных сэмплов из LIST sdta чанка"""
        if not self.file:
            return
            
        end_offset = start_offset + list_size
        current_pos = self.file.tell()
        
        # Парсим подчанки внутри sdta
        self.file.seek(start_offset)
        while self.file.tell() < end_offset - 8:
            # Чтение заголовка подчанка
            subchunk_header = self.file.read(8)
            if len(subchunk_header) < 8:
                break
                
            subchunk_id = subchunk_header[:4]
            subchunk_size = struct.unpack('<I', subchunk_header[4:8])[0]
            
            # Определение конца подчанка
            subchunk_end = self.file.tell() + subchunk_size
            
            # Проверка, является ли это подчанком shdr
            if subchunk_id == b'shdr':
                self._parse_shdr_chunk(subchunk_size)
                self.file.seek(subchunk_size, 1)
            else:
                # Пропускаем неизвестные подчанки
                self.file.seek(subchunk_size, 1)
            
            # Выравнивание до четного числа байт
            if subchunk_size % 2 != 0:
                self.file.seek(1, 1)
        
        # Восстанавливаем позицию
        self.file.seek(current_pos)