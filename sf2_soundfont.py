import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass

# Import classes from tg.py that we need for our implementation
from tg import ModulationDestination, ModulationSource

# Import the data classes from sf2.py
from sf2 import SF2Modulator, SF2InstrumentZone, SF2PresetZone, SF2SampleHeader, SF2Preset, SF2Instrument


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
        self.chunk_positions = {}  # Позиции чанков для быстрого доступа
        
        # Основные структуры данных
        self.presets: List[SF2Preset] = []
        self.instruments: List[SF2Instrument] = []
        self.sample_headers: List[SF2SampleHeader] = []
        
        # Флаги для отложенного парсинга
        self.headers_parsed = False  # Заголовки пресетов (bank, program, name)
        self.presets_parsed = False  # Полные данные пресетов
        self.instruments_parsed = False  # Полные данные инструментов
        self.samples_parsed = False  # Данные сэмплов
        
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
                    
                # Сохраняем позицию для последующего парсинга
                self.chunk_positions[list_type.decode('ascii')] = self.file.tell() - 4
                
                # Пропускаем содержимое чанка
                self.file.seek(chunk_size - 4, 1)
            else:
                # Пропускаем не-LIST чанки
                self.file.seek(chunk_size, 1)
            
            # Выравнивание до четного числа байт
            if chunk_size % 2 != 0:
                self.file.seek(1, 1)
    
    def _parse_preset_headers(self):
        """Парсит только заголовки пресетов (bank, program, name) для быстрой инициализации"""
        if not self.file or 'pdta' not in self.chunk_positions:
            return
            
        try:
            pdta_pos = self.chunk_positions['pdta']
            self.file.seek(pdta_pos - 8)
            
            # Читаем заголовок LIST pdta
            list_header = self.file.read(8)
            if len(list_header) >= 8:
                list_size = struct.unpack('<I', list_header[4:8])[0]
                self._parse_phdr_chunk(list_size - 4, pdta_pos + 4)
        except Exception as e:
            print(f"Ошибка при парсинге заголовков пресетов в {self.path}: {str(e)}")
    
    def _parse_phdr_chunk(self, chunk_size: int, start_offset: int):
        """Парсинг чанка phdr (заголовки пресетов) только для получения базовой информации"""
        if not self.file:
            return
            
        end_offset = start_offset + chunk_size
        self.file.seek(start_offset)
        
        # Читаем все заголовки пресетов за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 38)  # Исключаем терминальный пресет
        if len(raw_data) < chunk_size - 38:
            return
            
        # Распаковываем все заголовки пресетов одной операцией
        try:
            import numpy as np
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
                
        except ImportError:
            # Резервный вариант без numpy
            for i in range(0, len(raw_data), 38):
                if i + 38 <= len(raw_data):
                    preset_data = raw_data[i:i+38]
                    
                    # Извлечение данных
                    name = preset_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
                    preset = struct.unpack('<H', preset_data[20:22])[0]
                    bank = struct.unpack('<H', preset_data[22:24])[0]
                    preset_bag_ndx = struct.unpack('<H', preset_data[24:26])[0]
                    
                    # Создаем пресет
                    sf2_preset = SF2Preset()
                    sf2_preset.name = name
                    sf2_preset.preset = preset
                    sf2_preset.bank = bank
                    sf2_preset.preset_bag_index = preset_bag_ndx
                    self.presets.append(sf2_preset)
    
    def ensure_presets_parsed(self):
        """Гарантирует, что полные данные пресетов распаршены"""
        if self.presets_parsed:
            return
            
        if not self.file:
            return
            
        try:
            # Парсим полные данные пресетов
            self._parse_presets_data()
            self.presets_parsed = True
        except Exception as e:
            print(f"Ошибка при парсинге данных пресетов в {self.path}: {str(e)}")
            self.presets_parsed = True  # Помечаем как распаршенный даже в случае ошибки
    
    def ensure_instruments_parsed(self):
        """Гарантирует, что полные данные инструментов распаршены"""
        if self.instruments_parsed:
            return
            
        if not self.file:
            return
            
        try:
            # Парсим полные данные инструментов
            self._parse_instruments_data()
            self.instruments_parsed = True
        except Exception as e:
            print(f"Ошибка при парсинге данных инструментов в {self.path}: {str(e)}")
            self.instruments_parsed = True  # Помечаем как распаршенный даже в случае ошибки
    
    def ensure_samples_parsed(self):
        """Гарантирует, что данные сэмплов распаршены"""
        if self.samples_parsed:
            return
            
        if not self.file:
            return
            
        try:
            # Парсим данные сэмплов
            self._parse_samples_data()
            self.samples_parsed = True
        except Exception as e:
            print(f"Ошибка при парсинге данных сэмплов в {self.path}: {str(e)}")
            self.samples_parsed = True  # Помечаем как распаршенный даже в случае ошибки
    
    def _parse_presets_data(self):
        """Парсит полные данные пресетов (зоны, генераторы, модуляторы)"""
        if not self.file or 'pdta' not in self.chunk_positions:
            return
            
        pdta_pos = self.chunk_positions['pdta']
        self.file.seek(pdta_pos - 8)
        
        # Читаем заголовок LIST pdta
        list_header = self.file.read(8)
        if len(list_header) >= 8:
            list_size = struct.unpack('<I', list_header[4:8])[0]
            self._parse_pdta_presets(list_size - 4, pdta_pos + 4)
    
    def _parse_instruments_data(self):
        """Парсит полные данные инструментов (зоны, генераторы, модуляторы)"""
        if not self.file or 'pdta' not in self.chunk_positions:
            return
            
        pdta_pos = self.chunk_positions['pdta']
        self.file.seek(pdta_pos - 8)
        
        # Читаем заголовок LIST pdta
        list_header = self.file.read(8)
        if len(list_header) >= 8:
            list_size = struct.unpack('<I', list_header[4:8])[0]
            self._parse_pdta_instruments(list_size - 4, pdta_pos + 4)
    
    def _parse_samples_data(self):
        """Парсит данные сэмплов"""
        if not self.file or 'sdta' not in self.chunk_positions:
            return
            
        sdta_pos = self.chunk_positions['sdta']
        self.file.seek(sdta_pos - 8)
        
        # Читаем заголовок LIST sdta
        list_header = self.file.read(8)
        if len(list_header) >= 8:
            list_size = struct.unpack('<I', list_header[4:8])[0]
            self._parse_sdta_samples(list_size - 4, sdta_pos + 4)
    
    def _parse_pdta_presets(self, list_size: int, start_offset: int):
        """Парсинг данных пресетов из LIST pdta чанка"""
        if not self.file:
            return
            
        end_offset = start_offset + list_size
        current_pos = self.file.tell()
        
        # Парсим подчанки внутри pdta
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
            
            # Обработка различных типов подчанков для пресетов
            if subchunk_id == b'phdr':
                # Уже распаршено в заголовках
                self.file.seek(subchunk_size, 1)
            elif subchunk_id == b'pbag':
                self._parse_pbag_chunk(subchunk_size)
            elif subchunk_id == b'pmod':
                self._parse_pmod_chunk(subchunk_size)
            elif subchunk_id == b'pgen':
                self._parse_pgen_chunk(subchunk_size)
            else:
                # Пропускаем не относящиеся к пресетам чанки
                self.file.seek(subchunk_size, 1)

            self.file.seek(subchunk_end + (subchunk_size % 2))
        
        # Восстанавливаем позицию
        self.file.seek(current_pos)
    
    def _parse_pdta_instruments(self, list_size: int, start_offset: int):
        """Парсинг данных инструментов из LIST pdta чанка"""
        if not self.file:
            return
            
        end_offset = start_offset + list_size
        current_pos = self.file.tell()
        
        # Парсим подчанки внутри pdta
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
            
            # Обработка различных типов подчанков для инструментов
            if subchunk_id == b'inst':
                self._parse_inst_chunk(subchunk_size)
            elif subchunk_id == b'ibag':
                self._parse_ibag_chunk(subchunk_size)
            elif subchunk_id == b'imod':
                self._parse_imod_chunk(subchunk_size)
            elif subchunk_id == b'igen':
                self._parse_igen_chunk(subchunk_size)
            else:
                # Пропускаем не относящиеся к инструментам чанки
                self.file.seek(subchunk_size, 1)

            self.file.seek(subchunk_end + (subchunk_size % 2))
        
        # Восстанавливаем позицию
        self.file.seek(current_pos)
    
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
            
            # Проверка, является ли это подчанком smpl
            if subchunk_id == b'smpl':
                # Для отложенной загрузки просто сохраняем позицию
                # Реальные данные будут загружаться по запросу
                self.smpl_data_offset = self.file.tell()
                self.smpl_data_size = subchunk_size
                self.file.seek(subchunk_size, 1)
            else:
                # Пропускаем неизвестные подчанки
                self.file.seek(subchunk_size, 1)
            
            # Выравнивание до четного числа байт
            if subchunk_size % 2 != 0:
                self.file.seek(1, 1)
        
        # Восстанавливаем позицию
        self.file.seek(current_pos)
    
    def _parse_pbag_chunk(self, chunk_size: int):
        """Парсинг чанка pbag (заголовки зон пресетов)"""
        if not self.file or not self.presets:
            return
            
        num_zones = chunk_size // 4  # Каждая зона пресета 4 байта
        
        # Читаем все индексы зон за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 4)  # Исключаем терминальную зону
        if len(raw_data) < chunk_size - 4:
            return
            
        # Распаковываем все индексы зон одной операцией
        try:
            import numpy as np
            # Преобразуем байты в массив unsigned 16-bit чисел
            uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
            # Решейпим в массив пар (gen_ndx, mod_ndx)
            preset_zone_indices = uint16_array.reshape(-1, 2)
        except ImportError:
            # Резервный вариант без numpy
            preset_zone_indices = []
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    gen_ndx, mod_ndx = struct.unpack('<HH', raw_data[i:i+4])  # HH = два unsigned short
                    preset_zone_indices.append((gen_ndx, mod_ndx))
        
        # Привязываем зоны к пресетам за один проход
        if self.presets:
            # Предварительно вычисляем все границы зон
            zone_boundaries = []
            for i in range(len(self.presets)):
                start_idx = self.presets[i].preset_bag_index
                end_idx = self.presets[i+1].preset_bag_index if i < len(self.presets) - 1 else num_zones - 1
                zone_boundaries.append((start_idx, end_idx))
            
            # Привязываем зоны к пресетам
            for i, (start_idx, end_idx) in enumerate(zone_boundaries):
                preset = self.presets[i]
                # Добавляем все зоны для этого пресета за один раз
                for j in range(start_idx, min(end_idx, len(preset_zone_indices))):
                    gen_ndx, mod_ndx = preset_zone_indices[j]
                    
                    # Создаем зону пресета
                    preset_zone = SF2PresetZone()
                    preset_zone.preset = preset.preset
                    preset_zone.bank = preset.bank
                    preset_zone.instrument_index = 0  # Будет обновлено позже
                    preset_zone.instrument_name = ""
                    preset_zone.gen_ndx = gen_ndx
                    preset_zone.mod_ndx = mod_ndx
                    
                    preset.zones.append(preset_zone)
    
    def _parse_pgen_chunk(self, chunk_size: int):
        """Парсинг чанка pgen (генераторы пресетов)"""
        if not self.file or not self.presets:
            return
            
        # Читаем все генераторы за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size)
        if len(raw_data) < chunk_size:
            return
            
        # Распаковываем все генераторы одной операцией
        try:
            import numpy as np
            # Преобразуем байты в массив структурированных данных
            gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
            generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
            generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        except ImportError:
            # Резервный вариант без numpy
            generators = []
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    gen_type, gen_amount = struct.unpack('<Hh', raw_data[i:i+4])  # H = unsigned short, h = signed short
                    generators.append((gen_type, gen_amount))
        
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(generators):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех пресетов
        all_zone_boundaries = []
        for preset in self.presets:
            for zone in preset.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(generators)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((preset, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам пресетов за один проход
        instrument_names = [inst.name for inst in self.instruments] if self.instruments else []
        
        for preset, zone, start_idx, end_idx in all_zone_boundaries:
            # Обрабатываем генераторы для этой зоны
            for j in range(start_idx, min(end_idx, len(generators))):
                gen_type, gen_amount = generators[j]
                
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
    
    def _parse_pmod_chunk(self, chunk_size: int):
        """Парсинг чанка pmod (модуляторы пресетов)"""
        if not self.file or not self.presets:
            return
            
        num_modulators = chunk_size // 10  # Каждый модулятор 10 байт
        
        # Читаем все модуляторы за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size)
        if len(raw_data) < chunk_size:
            return
            
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
        
        # Привязываем модуляторы к зонам пресетов
        for preset in self.presets:
            for zone in preset.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(modulators)):
                    if modulators[i].source_oper == 0 and modulators[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = modulators[j]
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
        try:
            import numpy as np
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
                
        except ImportError:
            # Резервный вариант без numpy
            for i in range(0, len(raw_data), 22):
                if i + 22 <= len(raw_data):
                    inst_data = raw_data[i:i+22]
                    
                    # Извлечение данных
                    name = inst_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
                    inst_bag_ndx = struct.unpack('<H', inst_data[20:22])[0]
                    
                    # Создаем инструмент
                    sf2_instrument = SF2Instrument()
                    sf2_instrument.name = name
                    sf2_instrument.instrument_bag_index = inst_bag_ndx
                    self.instruments.append(sf2_instrument)
    
    def _parse_ibag_chunk(self, chunk_size: int):
        """Парсинг чанка ibag (заголовки зон инструментов)"""
        if not self.file or not self.instruments:
            return
            
        num_zones = chunk_size // 4  # Каждая зона инструмента 4 байта
        
        # Читаем все индексы зон за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size - 4)  # Исключаем терминальную зону
        if len(raw_data) < chunk_size - 4:
            return
            
        # Распаковываем все индексы зон одной операцией
        try:
            import numpy as np
            # Преобразуем байты в массив unsigned 16-bit чисел
            uint16_array = np.frombuffer(raw_data, dtype=np.uint16)
            # Решейпим в массив пар (gen_ndx, mod_ndx)
            instrument_zone_indices = uint16_array.reshape(-1, 2)
        except ImportError:
            # Резервный вариант без numpy
            instrument_zone_indices = []
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    gen_ndx, mod_ndx = struct.unpack('<HH', raw_data[i:i+4])  # HH = два unsigned short
                    instrument_zone_indices.append((gen_ndx, mod_ndx))
        
        # Предварительно вычисляем все границы зон
        if self.instruments:
            zone_boundaries = []
            for i in range(len(self.instruments)):
                start_idx = self.instruments[i].instrument_bag_index
                end_idx = self.instruments[i+1].instrument_bag_index if i < len(self.instruments) - 1 else num_zones - 1
                zone_boundaries.append((start_idx, end_idx))
            
            # Привязываем зоны к инструментам за один проход
            for i, (start_idx, end_idx) in enumerate(zone_boundaries):
                instrument = self.instruments[i]
                # Добавляем все зоны для этого инструмента за один раз
                for j in range(start_idx, min(end_idx, len(instrument_zone_indices))):
                    gen_ndx, mod_ndx = instrument_zone_indices[j]
                    
                    # Создаем зону инструмента
                    inst_zone = SF2InstrumentZone()
                    inst_zone.sample_index = 0  # Будет обновлено позже
                    inst_zone.gen_ndx = gen_ndx
                    inst_zone.mod_ndx = mod_ndx
                    
                    instrument.zones.append(inst_zone)
    
    def _parse_igen_chunk(self, chunk_size: int):
        """Парсинг чанка igen (генераторы инструментов)"""
        if not self.file or not self.instruments:
            return
            
        # Читаем все генераторы за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size)
        if len(raw_data) < chunk_size:
            return
            
        # Распаковываем все генераторы одной операцией
        try:
            import numpy as np
            # Преобразуем байты в массив структурированных данных
            gen_dtype = np.dtype([('gen_type', '<u2'), ('gen_amount', '<i2')])  # u2 = unsigned 16-bit, i2 = signed 16-bit
            generators_array = np.frombuffer(raw_data, dtype=gen_dtype)
            generators = [(int(gen['gen_type']), int(gen['gen_amount'])) for gen in generators_array]
        except ImportError:
            # Резервный вариант без numpy
            generators = []
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    gen_type, gen_amount = struct.unpack('<Hh', raw_data[i:i+4])  # H = unsigned short, h = signed short
                    generators.append((gen_type, gen_amount))
        
        # Создаем словарь для быстрого поиска терминальных генераторов
        terminal_gen_indices = set()
        for i, (gen_type, _) in enumerate(generators):
            if gen_type == 0:  # Терминальный генератор
                terminal_gen_indices.add(i)
        
        # Предварительно вычисляем границы зон для всех инструментов
        all_zone_boundaries = []
        for instrument in self.instruments:
            for zone in instrument.zones:
                start_idx = zone.gen_ndx
                # Быстрый поиск следующего терминального генератора
                end_idx = start_idx + 1
                for i in range(start_idx + 1, len(generators)):
                    if i in terminal_gen_indices:
                        end_idx = i
                        break
                all_zone_boundaries.append((instrument, zone, start_idx, end_idx))
        
        # Привязываем генераторы к зонам инструментов за один проход
        for instrument, zone, start_idx, end_idx in all_zone_boundaries:
            # Обрабатываем генераторы для этой зоны
            for j in range(start_idx, min(end_idx, len(generators))):
                gen_type, gen_amount = generators[j]
                
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
    
    def _parse_imod_chunk(self, chunk_size: int):
        """Парсинг чанка imod (модуляторы инструментов)"""
        if not self.file or not self.instruments:
            return
            
        # Читаем все модуляторы за один раз для лучшей производительности
        raw_data = self.file.read(chunk_size)
        if len(raw_data) < chunk_size:
            return
            
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
        
        # Привязываем модуляторы к зонам инструментов
        for instrument in self.instruments:
            for zone in instrument.zones:
                # Находим модуляторы для этой зоны
                start_idx = zone.mod_ndx
                end_idx = zone.mod_ndx + 1  # Временно, пока не найдем терминальную зону
                
                # Ищем терминальную зону
                for i in range(start_idx + 1, len(modulators)):
                    if modulators[i].source_oper == 0 and modulators[i].destination == 0:
                        end_idx = i
                        break
                
                # Обрабатываем модуляторы
                for j in range(start_idx, end_idx):
                    modulator = modulators[j]
                    zone.modulators.append(modulator)
    
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
        try:
            import numpy as np
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
                
        except ImportError:
            # Резервный вариант без numpy
            for i in range(0, len(raw_data), 46):
                if i + 46 <= len(raw_data):
                    sample_data = raw_data[i:i+46]
                    
                    # Извлечение данных
                    name = sample_data[:20].split(b'\x00')[0].decode('ascii', 'ignore')
                    start = struct.unpack('<I', sample_data[20:24])[0]
                    end = struct.unpack('<I', sample_data[24:28])[0]
                    start_loop = struct.unpack('<I', sample_data[28:32])[0]
                    end_loop = struct.unpack('<I', sample_data[32:36])[0]
                    sample_rate = struct.unpack('<I', sample_data[36:40])[0]
                    original_pitch = sample_data[40]
                    pitch_correction = struct.unpack('b', sample_data[41:42])[0]
                    sample_link = struct.unpack('<H', sample_data[42:44])[0]
                    sample_type = struct.unpack('<H', sample_data[44:46])[0]
                    
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
        # Найти пресет по банку и программе
        preset = None
        for p in self.presets:
            if p.preset == program and p.bank == bank:
                preset = p
                break
        
        if preset is None:
            return None
        
        # Если полные данные пресетов еще не распаршены, делаем это сейчас
        self.ensure_presets_parsed()
        
        return preset
    
    def get_instrument(self, index: int) -> Optional[SF2Instrument]:
        """
        Получает инструмент по индексу с отложенной загрузкой.
        
        Args:
            index: индекс инструмента
            
        Returns:
            SF2Instrument или None если не найден
        """
        # Если инструменты еще не распаршены, делаем это сейчас
        self.ensure_instruments_parsed()
        
        if index < 0 or index >= len(self.instruments):
            return None
            
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
        self.ensure_samples_parsed()
        
        if index < 0 or index >= len(self.sample_headers):
            return None
            
        return self.sample_headers[index]