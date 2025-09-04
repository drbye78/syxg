import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import BinaryIO, Dict, List, Tuple, Optional, Union, Any, Callable
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
        self.instrument_names: List[str] = []
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
            self._parse_headers()
            self.headers_parsed = True
            
        except Exception as e:
            print(f"Ошибка при инициализации SF2 файла {self.path}: {str(e)}")
            if self.file and not self.file.closed:
                self.file.close()
            self.file: Optional[BinaryIO] = None
    
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
                    
                list_type_str = list_type.decode('ascii')
                
                # Сохраняем позицию и размер как кортеж
                list_position = self.file.tell() - 4
                self.chunk_info[list_type_str] = (list_position, chunk_size)
                
                # Для sdta LIST чанка также ищем внутренние чанки smpl и sm24
                if list_type_str == 'sdta':
                    self._locate_sdta_subchunks(list_position, chunk_size)
                else:
                    self._locate_subchunks(list_position, chunk_size)

            self.file.seek(chunk_end)
    
    def _locate_subchunks(self, pdta_position: int, pdta_size: int):
        """Находит позиции обязательных подчанков в pdta для оптимизации on-demand парсинга"""
        if not self.file:
            return
            
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
    
    def _locate_sdta_subchunks(self, sdta_position: int, sdta_size: int):
        """Находит позиции подчанков smpl и sm24 внутри sdta для правильной работы с 24-битными сэмплами"""
        if not self.file:
            return
            
        # Переходим к началу sdta
        self.file.seek(sdta_position + 4)  # +4 чтобы пропустить заголовок LIST
        sdta_end = sdta_position + sdta_size - 4

        # Парсим подчанки внутри sdta
        while self.file.tell() < sdta_end - 8:
            # Чтение заголовка подчанка
            subchunk_header = self.file.read(8)
            if len(subchunk_header) < 8:
                break
                
            subchunk_id = subchunk_header[:4]
            subchunk_size = struct.unpack('<I', subchunk_header[4:8])[0]
            subchunk_name = subchunk_id.decode('ascii')
            
            # Сохраняем позицию и размер как кортеж
            self.chunk_info[subchunk_name] = (self.file.tell(), subchunk_size)
            
            # Переходим к следующему подчанку
            self.file.seek(self.file.tell() + subchunk_size + (subchunk_size % 2))
    
    def _parse_headers(self):
        """Парсит только заголовки пресетов (bank, program, name) для быстрой инициализации"""
                
        try:
            phdr_pos, phdr_size = self.chunk_info.get('phdr', (0, 0))
            self._parse_phdr_chunk(phdr_size, phdr_pos)
            inst_pos, inst_size = self.chunk_info.get('inst', (0, 0))
            self._parse_inst_chunk(inst_pos, inst_size)
            shdr_pos, shdr_size = self.chunk_info.get('shdr', (0, 0))
            self._parse_shdr_chunk(shdr_pos, shdr_size)
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

    def _parse_single_preset_zones(self, preset_index: int):
        if not self.file:
            return

        preset = self.presets[preset_index]

        bag_size = 4
        pbag_start, pbag_size = self.chunk_info['pbag']
        next_index = preset_index + 1 if preset_index + 1 < len(self.presets) else None
        end_bag_index = self.presets[next_index].preset_bag_index if next_index is not None else pbag_size // bag_size
        start_bag_index = preset.preset_bag_index
        
        self.file.seek(pbag_start + start_bag_index * bag_size)
        bags_raw = self.file.read((end_bag_index - start_bag_index) * bag_size)
        pbag_data = self._parse_bag_raw_data(bags_raw)
        for gen_ndx, mod_ndx in pbag_data:
            preset_zone = SF2PresetZone()
            preset_zone.preset = preset.preset
            preset_zone.bank = preset.bank
            preset_zone.instrument_index = 0  # Будет обновлено позже
            preset_zone.instrument_name = ""
            preset_zone.gen_ndx = gen_ndx
            preset_zone.mod_ndx = mod_ndx
            preset.zones.append(preset_zone)

        next_raw = self.file.read(4)
        return self._parse_bag_raw_data(next_raw)[0]

    def _parse_single_instrument_zones(self, instrument_index: int):
        if not self.file:
            return

        instrument = self.instruments[instrument_index]

        bag_size = 4
        ibag_start, ibag_size = self.chunk_info['ibag']
        next_index = instrument_index + 1 if instrument_index + 1 < len(self.instruments) else None
        end_bag_index = self.instruments[next_index].instrument_bag_index if next_index is not None else ibag_size // bag_size
        start_bag_index = instrument.instrument_bag_index
        
        self.file.seek(ibag_start + start_bag_index * bag_size)
        bags_raw = self.file.read((end_bag_index - start_bag_index) * bag_size)
        ibag_data = self._parse_bag_raw_data(bags_raw)
        for gen_ndx, mod_ndx in ibag_data:
            inst_zone = SF2InstrumentZone()
            inst_zone.sample_index = 0  # Будет обновлено позже
            inst_zone.gen_ndx = gen_ndx
            inst_zone.mod_ndx = mod_ndx
            
            instrument.zones.append(inst_zone)

        next_raw = self.file.read(4)
        return self._parse_bag_raw_data(next_raw)[0]

    def _parse_single_preset_data(self, preset_index: int):
        """Парсит данные только для одного конкретного пресета"""
        if not self.file:
            return
            
        # Определяем границы зон для конкретного пресета
        preset = self.presets[preset_index]
        next_gen_ndx, next_mod_ndx = self._parse_single_preset_zones(preset_index) # type: ignore

        # Определяем границы генераторов для конкретного пресета
        pgen_start, pgen_size = self.chunk_info['pgen']
        pmod_start, pmod_size = self.chunk_info['pmod']
        generator_size = 4
        modulator_size = 10

        base_gen_index: int = preset.zones[0].gen_ndx
        self.file.seek(pgen_start + base_gen_index * generator_size)
        gens_raw = self.file.read((next_gen_ndx - base_gen_index) * generator_size)
        generators = self._parse_gen_raw_data(gens_raw)

        start_mod_index = preset.zones[0].mod_ndx
        self.file.seek(pmod_start + start_mod_index * modulator_size)
        mods_raw = self.file.read((next_mod_ndx - start_mod_index) * modulator_size)
        modulators = self._parse_mod_raw_data(mods_raw)

        for zone_index, zone in enumerate(preset.zones):
            # Определяем границы генераторов для конкретной зоны
            start_gen_index = zone.gen_ndx
            end_gen_index = preset.zones[zone_index + 1].gen_ndx if zone_index + 1 < len(preset.zones) else next_gen_ndx
            self._configure_preset_zone_from_generators(zone, generators, start_gen_index - base_gen_index, end_gen_index - base_gen_index)

            # Определяем границы модуляторов для конкретной зоны
            start_mod_index = zone.mod_ndx
            end_mod_index = preset.zones[zone_index + 1].mod_ndx if zone_index + 1 < len(preset.zones) else next_mod_ndx
            zone.modulators = modulators[start_mod_index - start_mod_index:end_mod_index - start_mod_index]

            if zone.instrument_index:
                self._ensure_instrument_parsed(zone.instrument_index)
    
    def _parse_single_instrument_data(self, instrument_index: int):
        """Парсит данные только для одного конкретного инструмента"""
        if not self.file:
            return
            
        # Определяем границы зон для конкретного инструмента
        instrument = self.instruments[instrument_index]
        next_gen_ndx, next_mod_ndx = self._parse_single_instrument_zones(instrument_index) # type: ignore
        igen_start, igen_size = self.chunk_info['igen']
        imod_start, imod_size = self.chunk_info['imod']
        generator_size = 4
        modulator_size = 10

        base_gen_index: int = instrument.zones[0].gen_ndx
        self.file.seek(igen_start + base_gen_index * generator_size)
        gens_raw = self.file.read((next_gen_ndx - base_gen_index) * generator_size)
        generators = self._parse_gen_raw_data(gens_raw)

        start_mod_index = instrument.zones[0].mod_ndx
        self.file.seek(imod_start + start_mod_index * modulator_size)
        mods_raw = self.file.read((next_mod_ndx - start_mod_index) * modulator_size)
        modulators = self._parse_mod_raw_data(mods_raw)

        for zone_index, zone in enumerate(instrument.zones):
            # Определяем границы генераторов для конкретной зоны
            start_gen_index = zone.gen_ndx
            end_gen_index = instrument.zones[zone_index + 1].gen_ndx if zone_index + 1 < len(instrument.zones) else next_gen_ndx
            self._configure_instrument_zone_from_generators(zone, generators, start_gen_index - base_gen_index, end_gen_index - base_gen_index)

            # Определяем границы модуляторов для конкретной зоны
            start_mod_index = zone.mod_ndx
            end_mod_index = instrument.zones[zone_index + 1].mod_ndx if zone_index + 1 < len(instrument.zones) else next_mod_ndx
            zone.modulators = modulators[start_mod_index - start_mod_index:end_mod_index - start_mod_index]
        
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
            pmod_data = self._parse_mod_raw_data(pmod_raw_data)
        
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
            ibag_data = self._parse_bag_raw_data(ibag_raw_data)
        
        # Парсим imod данные напрямую по сохраненной позиции
        if 'imod' in self.chunk_info:
            imod_pos, imod_size = self.chunk_info['imod']
            
            # Переходим к imod
            self.file.seek(imod_pos)
            # Читаем и парсим imod данные
            imod_raw_data = self.file.read(imod_size)
            imod_data = self._parse_mod_raw_data(imod_raw_data)
        
        # Парсим igen данные напрямую по сохраненной позиции
        if 'igen' in self.chunk_info:
            igen_pos, igen_size = self.chunk_info['igen']
            
            # Переходим к igen
            self.file.seek(igen_pos)
            # Читаем и парсим igen данные
            igen_raw_data = self.file.read(igen_size)
            igen_data = self._parse_gen_raw_data(igen_raw_data)
        
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
    
    def _parse_mod_raw_data(self, raw_data):
        """Парсит сырые данные pmod / imod чанка"""
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
    
    def _configure_preset_zone_from_generators(self, zone: SF2PresetZone, pgen_data: List[Tuple[int, int]], start_idx: int, end_idx: int):
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
                if 0 <= gen_amount < len(self.instrument_names):
                    zone.instrument_name = self.instrument_names[gen_amount]
            elif gen_type == 43:  # keyRange
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 44:  # velRange
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF
            elif gen_type == 8:  # initialFilterFc
                zone.initialFilterFc = gen_amount
            elif gen_type == 9:  # initialFilterQ
                zone.initial_filterQ = gen_amount
            elif gen_type == 17:  # pan
                zone.Pan = gen_amount
            elif gen_type == 21:  # delayModLFO
                zone.DelayLFO1 = gen_amount
            elif gen_type == 22:  # freqModLFO
                zone.LFO1Freq = gen_amount
            elif gen_type == 23:  # delayVibLFO
                zone.DelayLFO2 = gen_amount
            elif gen_type == 24:  # freqVibLFO
                zone.LFO1Freq = gen_amount
            elif gen_type == 25:  # delayModEnv - Fixed: was incorrectly mapped
                zone.DelayFilEnv = gen_amount
            elif gen_type == 26:  # attackModEnv - Fixed: was incorrectly mapped
                zone.AttackFilEnv = gen_amount
            elif gen_type == 27:  # holdModEnv - Fixed: was incorrectly mapped
                zone.HoldFilEnv = gen_amount
            elif gen_type == 28:  # decayModEnv - Fixed: was incorrectly mapped
                zone.DecayFilEnv = gen_amount
            elif gen_type == 29:  # sustainModEnv - Fixed: was incorrectly mapped
                zone.SustainFilEnv = gen_amount
            elif gen_type == 30:  # releaseModEnv - Fixed: was incorrectly mapped
                zone.ReleaseFilEnv = gen_amount
            elif gen_type == 31:  # keynumToModEnvHold - Fixed: was incorrectly mapped
                zone.KeynumToModEnvHold = gen_amount
            elif gen_type == 32:  # keynumToModEnvDecay - Fixed: was incorrectly mapped
                zone.KeynumToModEnvDecay = gen_amount
            elif gen_type == 33:  # delayVolEnv - Fixed: was incorrectly mapped
                zone.DelayVolEnv = gen_amount
            elif gen_type == 34:  # attackVolEnv - Fixed: was incorrectly mapped
                zone.AttackVolEnv = gen_amount
            elif gen_type == 35:  # holdVolEnv - Fixed: was incorrectly mapped
                zone.HoldVolEnv = gen_amount
            elif gen_type == 36:  # decayVolEnv - Fixed: was incorrectly mapped
                zone.DecayVolEnv = gen_amount
            elif gen_type == 37:  # sustainVolEnv - Fixed: was incorrectly mapped
                zone.SustainVolEnv = gen_amount
            elif gen_type == 38:  # releaseVolEnv - Fixed: was incorrectly mapped
                zone.ReleaseVolEnv = gen_amount
            elif gen_type == 39:  # keynumToVolEnvHold - Fixed: was incorrectly mapped
                zone.KeynumToVolEnvHold = gen_amount
            elif gen_type == 40:  # keynumToVolEnvDecay - Fixed: was incorrectly mapped
                zone.KeynumToVolEnvDecay = gen_amount
            elif gen_type == 51:  # coarseTune
                zone.CoarseTune = gen_amount
            elif gen_type == 52:  # fineTune
                zone.FineTune = gen_amount
            elif gen_type == 16:  # reverbEffectsSend - Added support for reverb send
                # Store reverb send value for XG partials (0-1000 -> 0-127)
                zone.reverb_send = max(0, min(127, gen_amount // 10)) if gen_amount >= 0 else 0
            elif gen_type == 15:  # chorusEffectsSend - Added support for chorus send
                # Store chorus send value for XG partials (0-1000 -> 0-127)
                zone.chorus_send = max(0, min(127, gen_amount // 10)) if gen_amount >= 0 else 0
            elif gen_type == 48:  # initialAttenuation - Added support for initial attenuation
                zone.InitialAttenuation = gen_amount
            elif gen_type == 56:  # scaleTuning - Added support for scale tuning
                zone.scale_tuning = gen_amount
            elif gen_type == 58:  # overridingRootKey - Added support for overriding root key
                zone.OverridingRootKey = gen_amount
            elif gen_type == 4:  # startAddrsCoarseOffset - Added support for coarse start address offset
                zone.start_coarse = gen_amount
            elif gen_type == 12:  # endAddrsCoarseOffset - Added support for coarse end address offset
                zone.end_coarse = gen_amount
            elif gen_type == 42:  # startloopAddrsCoarseOffset - Added support for coarse loop start address offset
                zone.start_loop_coarse = gen_amount
            elif gen_type == 45:  # endloopAddrsCoarseOffset - Added support for coarse loop end address offset
                zone.end_loop_coarse = gen_amount

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
        for preset, zone, start_idx, end_idx in all_zone_boundaries:
            self._configure_preset_zone_from_generators(zone, pgen_data, start_idx, end_idx)
    
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
            if gen_type == 54:  # sampleModes
                zone.sample_modes = gen_amount
            elif gen_type == 57:  # exclusiveClass
                zone.exclusive_class = gen_amount
            elif gen_type == 53:  # sampleID
                zone.sample_index = gen_amount
            elif gen_type == 0:  # startAddrsOffset
                zone.start = gen_amount
            elif gen_type == 1:  # endAddrsOffset
                zone.end = gen_amount
            elif gen_type == 2:  # startloopAddrsOffset
                zone.start_loop = gen_amount
            elif gen_type == 3:  # endloopAddrsOffset
                zone.end_loop = gen_amount
            elif gen_type == 8:  # initialFilterFc - Fixed: was incorrectly mapped
                zone.initialFilterFc = gen_amount
            elif gen_type == 9:  # initialFilterQ - Fixed: was incorrectly mapped
                zone.initial_filterQ = gen_amount
            elif gen_type == 17:  # pan - Fixed: was incorrectly mapped
                zone.Pan = gen_amount
            elif gen_type == 25:  # delayModEnv - Fixed: was incorrectly mapped
                zone.DelayFilEnv = gen_amount
            elif gen_type == 26:  # attackModEnv - Fixed: was incorrectly mapped
                zone.AttackFilEnv = gen_amount
            elif gen_type == 27:  # holdModEnv - Fixed: was incorrectly mapped
                zone.HoldFilEnv = gen_amount
            elif gen_type == 28:  # decayModEnv - Fixed: was incorrectly mapped
                zone.DecayFilEnv = gen_amount
            elif gen_type == 29:  # sustainModEnv - Fixed: was incorrectly mapped
                zone.SustainFilEnv = gen_amount
            elif gen_type == 30:  # releaseModEnv - Fixed: was incorrectly mapped
                zone.ReleaseFilEnv = gen_amount
            elif gen_type == 31:  # keynumToModEnvHold - Fixed: was incorrectly mapped
                zone.KeynumToModEnvHold = gen_amount
            elif gen_type == 32:  # keynumToModEnvDecay - Fixed: was incorrectly mapped
                zone.KeynumToModEnvDecay = gen_amount
            elif gen_type == 33:  # delayVolEnv - Fixed: was incorrectly mapped
                zone.DelayVolEnv = gen_amount
            elif gen_type == 34:  # attackVolEnv - Fixed: was incorrectly mapped
                zone.AttackVolEnv = gen_amount
            elif gen_type == 35:  # holdVolEnv - Fixed: was incorrectly mapped
                zone.HoldVolEnv = gen_amount
            elif gen_type == 36:  # decayVolEnv - Fixed: was incorrectly mapped
                zone.DecayVolEnv = gen_amount
            elif gen_type == 37:  # sustainVolEnv - Fixed: was incorrectly mapped
                zone.SustainVolEnv = gen_amount
            elif gen_type == 38:  # releaseVolEnv - Fixed: was incorrectly mapped
                zone.ReleaseVolEnv = gen_amount
            elif gen_type == 39:  # keynumToVolEnvHold - Fixed: was incorrectly mapped
                zone.KeynumToVolEnvHold = gen_amount
            elif gen_type == 40:  # keynumToVolEnvDecay - Fixed: was incorrectly mapped
                zone.KeynumToVolEnvDecay = gen_amount
            elif gen_type == 51:  # coarseTune
                zone.CoarseTune = gen_amount
            elif gen_type == 52:  # fineTune
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
            elif gen_type == 12:  # endAddrsCoarseOffset - Added support for coarse end address offset
                zone.end_coarse = gen_amount
            elif gen_type == 13:  # modLfoToVolume - Fixed: was incorrectly mapped
                zone.mod_lfo_to_volume = gen_amount
            elif gen_type == 43:  # keyRange - Fixed: was incorrectly mapped
                zone.lokey = gen_amount & 0xFF
                zone.hikey = (gen_amount >> 8) & 0xFF
            elif gen_type == 44:  # velRange - Fixed: was incorrectly mapped
                zone.lovel = gen_amount & 0xFF
                zone.hivel = (gen_amount >> 8) & 0xFF
            elif gen_type == 16:  # reverbEffectsSend - Added support for reverb send
                # Store reverb send value for XG partials (0-1000 -> 0-127)
                zone.reverb_send = max(0, min(127, gen_amount // 10)) if gen_amount >= 0 else 0
            elif gen_type == 15:  # chorusEffectsSend - Added support for chorus send
                # Store chorus send value for XG partials (0-1000 -> 0-127)
                zone.chorus_send = max(0, min(127, gen_amount // 10)) if gen_amount >= 0 else 0
            elif gen_type == 48:  # initialAttenuation - Added support for initial attenuation
                zone.InitialAttenuation = gen_amount
            elif gen_type == 56:  # scaleTuning - Added support for scale tuning
                zone.scale_tuning = gen_amount
            elif gen_type == 58:  # overridingRootKey - Added support for overriding root key
                zone.OverridingRootKey = gen_amount
            elif gen_type == 4:  # startAddrsCoarseOffset - Added support for coarse start address offset
                zone.start_coarse = gen_amount
            elif gen_type == 12:  # endAddrsCoarseOffset - Added support for coarse end address offset
                zone.end_coarse = gen_amount
            elif gen_type == 42:  # startloopAddrsCoarseOffset - Added support for coarse loop start address offset
                zone.start_loop_coarse = gen_amount
            elif gen_type == 45:  # endloopAddrsCoarseOffset - Added support for coarse loop end address offset
                zone.end_loop_coarse = gen_amount
            elif gen_type == 21:  # delayModLFO
                zone.DelayLFO1 = gen_amount
            elif gen_type == 22:  # freqModLFO
                zone.LFO1Freq = gen_amount
            elif gen_type == 23:  # delayVibLFO
                zone.DelayLFO2 = gen_amount
            elif gen_type == 24:  # freqVibLFO
                zone.LFO1Freq = gen_amount

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
    
    def _parse_inst_chunk(self, chunk_pos: int, chunk_size: int):
        """Парсинг чанка inst (заголовки инструментов)"""
        if not self.file:
            return
            
        self.file.seek(chunk_pos)  # Переходим к данным чанка

        # Читаем все заголовки инструментов за один раз для лучшей производительности
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

        self.instrument_names = [inst.name for inst in self.instruments]
    
    def _parse_shdr_chunk(self, chunk_pos: int, chunk_size: int):
        """Парсинг чанка shdr (заголовки сэмплов)"""
        if not self.file:
            return
            
        num_samples = chunk_size // 46  # Каждый заголовок сэмпла 46 байт
        self.file.seek(chunk_pos)  # Переходим к данным чанка
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
            sample_header.stereo = (sample_type & 3) == 2
            self.sample_headers.append(sample_header)
        
        self.samples_parsed = True
    
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
            shdr_pos, shdr_size = self.chunk_info['shdr']
            self._parse_shdr_chunk(shdr_pos, shdr_size)
            self.samples_parsed = True
        
        if index < 0 or index >= len(self.sample_headers):
            return None
            
        return self.sample_headers[index]
    
    def read_sample_data(self, sample_header: SF2SampleHeader) -> Optional[Union[List[float], List[Tuple[float, float]]]]:
        """
        Оптимизированное чтение сэмпла из файла с уменьшением количества операций.
        
        Args:
            sample_header: заголовок сэмпла
            
        Returns:
            Моно: список значений
            Стерео: список кортежей (левый, правый)
        """
        sample_length = sample_header.end - sample_header.start
        if self.file is None or 'smpl' not in self.chunk_info or not sample_length:
            return None
        
        if sample_header.data is not None:
            return sample_header.data

        smpl_pos, _ = self.chunk_info['smpl']
        num_samples = sample_length * 2 if sample_header.stereo else sample_length
        sample_size = num_samples * 2
        self.file.seek(smpl_pos + sample_header.start * 2)
        raw_data = self.file.read(sample_size)
        raw_samples = struct.unpack(f'<{num_samples}h', raw_data)

        is_24bit = 'sm24' in self.chunk_info
        if is_24bit:
            sm24_pos, _ = self.chunk_info['sm24']
            self.file.seek(sm24_pos + sample_header.start)
            aux_data = self.file.read(num_samples)
            maxx = 2.0 ** -23
            sample_data = [(raw_samples[i] << 8 | aux_data[i]) * maxx for i in range(num_samples)]
        else:
            sample_data = [raw_samples[i] / 32768.0 for i in range(num_samples)]

        if sample_header.stereo:
            sample_header.data = [(sample_data[i], sample_data[i + 1]) for i in range(0, len(sample_data), 2)]
        else:
            sample_header.data = sample_data

        return sample_header.data