import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any
from collections import OrderedDict
import threading

from sf2 import Sf2WavetableManager
from tg import XGToneGenerator, ADSREnvelope, LFO, ModulationMatrix
from fx import XGEffectManager


class XGSynthesizer:
    """
    Полностью совместимый с MIDI XG программный синтезатор.
    
    Поддерживает:
    - Все MIDI сообщения включая SYSEX и Bulk SYSEX
    - Генерацию аудио блоками произвольного размера
    - Настройку максимальной полифонии
    - Полный контроль над тон-генерацией
    - Обработку эффектов
    - Управление SF2-файлами с черными списками и маппингом банков
    - Инициализацию в соответствии со стандартом MIDI XG
    """
    
    # Константы по умолчанию
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_BLOCK_SIZE = 512
    DEFAULT_MAX_POLYPHONY = 64
    DEFAULT_MASTER_VOLUME = 1.0
    
    # Системные статусы MIDI
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCH_BEND = 0xE0
    SYSTEM_EXCLUSIVE = 0xF0
    MIDI_TIME_CODE = 0xF1
    SONG_POSITION = 0xF2
    SONG_SELECT = 0xF3
    TUNE_REQUEST = 0xF6
    END_OF_EXCLUSIVE = 0xF7
    TIMING_CLOCK = 0xF8
    START = 0xFA
    CONTINUE = 0xFB
    STOP = 0xFC
    ACTIVE_SENSING = 0xFE
    SYSTEM_RESET = 0xFF
    
    # Регистрация системных сообщений
    RPN_MSB = 101
    RPN_LSB = 100
    NRPN_MSB = 99
    NRPN_LSB = 98
    DATA_ENTRY_MSB = 6
    DATA_ENTRY_LSB = 38
    
    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE, 
                 block_size: int = DEFAULT_BLOCK_SIZE,
                 max_polyphony: int = DEFAULT_MAX_POLYPHONY):
        """
        Инициализация XG синтезатора.
        
        Args:
            sample_rate: частота дискретизации (по умолчанию 44100 Гц)
            block_size: размер аудио блока в сэмплах (по умолчанию 512)
            max_polyphony: максимальная полифония (по умолчанию 64 голоса)
        """
        # Основные параметры
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_polyphony = max_polyphony
        self.master_volume = self.DEFAULT_MASTER_VOLUME
        
        # Блокировка для потокобезопасности
        self.lock = threading.RLock()
        
        # Управление SF2 файлами
        self.sf2_manager: Optional[Sf2WavetableManager] = None
        self.sf2_paths: List[str] = []
        
        # Тон-генераторы (голоса)
        self.tone_generators: List[XGToneGenerator] = []
        self.active_notes: Dict[Tuple[int, int], XGToneGenerator] = {}  # (channel, note) -> generator
        
        # Состояние MIDI каналов
        self.channel_states: List[Dict[str, Any]] = [self._create_channel_state() for _ in range(16)]
        
        # Состояние RPN/NRPN
        self.rpn_states: List[Dict[str, int]] = [{"msb": 127, "lsb": 127} for _ in range(16)]
        self.nrpn_states: List[Dict[str, int]] = [{"msb": 127, "lsb": 127} for _ in range(16)]
        self.data_entry_states: List[Dict[str, int]] = [{"msb": 0, "lsb": 0} for _ in range(16)]
        
        # Эффекты
        self.effect_manager = XGEffectManager(sample_rate)
        
        # Счетчики для уникальной идентификации
        self.generator_id_counter = 0
        
        # Инициализация XG
        self._initialize_xg()
    
    def _create_channel_state(self) -> Dict[str, Any]:
        """Создание начального состояния MIDI канала"""
        return {
            "program": 0,
            "bank": 0,
            "volume": 100,
            "expression": 127,
            "pan": 64,
            "mod_wheel": 0,
            "pitch_bend": 8192,
            "pitch_bend_range": 2,
            "sustain_pedal": False,
            "portamento": False,
            "portamento_time": 0,
            "reverb_send": 40,
            "chorus_send": 0,
            "variation_send": 0,
            "key_pressure": {},
            "controllers": {i: 0 for i in range(128)},
            "rpn_msb": 127,
            "rpn_lsb": 127,
            "nrpn_msb": 127,
            "nrpn_lsb": 127
        }
    
    def _initialize_xg(self):
        """Инициализация XG синтезатора в соответствии со стандартом"""
        # Отправляем XG System On сообщение
        self.send_sysex([0xF0, 0x43, 0x10, 0x4C, 0x00, 0x00, 0x7E, 0x00, 0xF7])
    
    def set_sf2_files(self, sf2_paths: List[str]):
        """
        Установка списка SF2 файлов для использования синтезатором.
        
        Args:
            sf2_paths: список путей к SF2 файлам
        """
        with self.lock:
            self.sf2_paths = sf2_paths.copy()
            self.sf2_manager = Sf2WavetableManager(sf2_paths)
    
    def set_bank_blacklist(self, sf2_path: str, bank_list: List[int]):
        """
        Установка черного списка банков для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_list: список номеров банков для исключения
        """
        if self.sf2_manager:
            with self.lock:
                self.sf2_manager.set_bank_blacklist(sf2_path, bank_list)
    
    def set_preset_blacklist(self, sf2_path: str, preset_list: List[Tuple[int, int]]):
        """
        Установка черного списка пресетов для указанного SF2 файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            preset_list: список кортежей (bank, program) для исключения
        """
        if self.sf2_manager:
            with self.lock:
                self.sf2_manager.set_preset_blacklist(sf2_path, preset_list)
    
    def set_bank_mapping(self, sf2_path: str, bank_mapping: Dict[int, int]):
        """
        Установка маппинга банков MIDI на банки SF2 для указанного файла.
        
        Args:
            sf2_path: путь к SF2 файлу
            bank_mapping: словарь маппинга midi_bank -> sf2_bank
        """
        if self.sf2_manager:
            with self.lock:
                self.sf2_manager.set_bank_mapping(sf2_path, bank_mapping)
    
    def set_max_polyphony(self, max_polyphony: int):
        """
        Установка максимальной полифонии.
        
        Args:
            max_polyphony: максимальное количество одновременных голосов
        """
        with self.lock:
            self.max_polyphony = max_polyphony
    
    def set_master_volume(self, volume: float):
        """
        Установка мастер-громкости.
        
        Args:
            volume: громкость (0.0 - 1.0)
        """
        with self.lock:
            self.master_volume = max(0.0, min(1.0, volume))
    
    def send_midi_message(self, status: int, data1: int, data2: int = 0):
        """
        Отправка MIDI сообщения в синтезатор.
        
        Args:
            status: статус байт (включая номер канала)
            data1: первый байт данных
            data2: второй байт данных (для сообщений с двумя байтами данных)
        """
        with self.lock:
            # Определяем номер канала
            channel = status & 0x0F
            command = status & 0xF0
            
            # Обрабатываем команды
            if command == self.NOTE_OFF:
                self._handle_note_off(channel, data1, data2)
            elif command == self.NOTE_ON:
                self._handle_note_on(channel, data1, data2)
            elif command == self.POLY_PRESSURE:
                self._handle_poly_pressure(channel, data1, data2)
            elif command == self.CONTROL_CHANGE:
                self._handle_control_change(channel, data1, data2)
            elif command == self.PROGRAM_CHANGE:
                self._handle_program_change(channel, data1)
            elif command == self.CHANNEL_PRESSURE:
                self._handle_channel_pressure(channel, data1)
            elif command == self.PITCH_BEND:
                self._handle_pitch_bend(channel, data1, data2)
    
    def send_sysex(self, data: List[int]):
        """
        Отправка системного эксклюзивного сообщения.
        
        Args:
            data: данные SYSEX сообщения (включая F0 и F7)
        """
        with self.lock:
            # Проверка, что это действительно SYSEX сообщение
            if len(data) < 3 or data[0] != self.SYSTEM_EXCLUSIVE or data[-1] != self.END_OF_EXCLUSIVE:
                return
            
            # Определяем производителя
            if len(data) >= 2 and data[1] == 0x43:  # Yamaha
                self._handle_yamaha_sysex(data)
            else:
                # Обработка других производителей
                pass
    
    def _handle_note_off(self, channel: int, note: int, velocity: int):
        """Обработка Note Off сообщения"""
        # Проверяем, есть ли активная нота на этом канале
        key = (channel, note)
        if key in self.active_notes:
            generator = self.active_notes[key]
            generator.note_off()
            # Удаляем из активных нот
            del self.active_notes[key]
    
    def _handle_note_on(self, channel: int, note: int, velocity: int):
        """Обработка Note On сообщения"""
        # Если velocity = 0, это Note Off
        if velocity == 0:
            self._handle_note_off(channel, note, velocity)
            return
        
        # Проверяем максимальную полифонию
        if len(self.active_notes) >= self.max_polyphony:
            # Удаляем самый старый голос
            oldest_key = next(iter(self.active_notes))
            oldest_generator = self.active_notes[oldest_key]
            oldest_generator.note_off()
            del self.active_notes[oldest_key]
        
        # Получаем состояние канала
        channel_state = self.channel_states[channel]
        
        # Создаем новый тон-генератор
        generator = self._create_tone_generator(
            note=note,
            velocity=velocity,
            program=channel_state["program"],
            channel=channel,
            bank=channel_state["bank"]
        )
        
        if generator:
            # Сохраняем генератор
            key = (channel, note)
            self.active_notes[key] = generator
            self.tone_generators.append(generator)
    
    def _handle_poly_pressure(self, channel: int, note: int, pressure: int):
        """Обработка Poly Pressure (Key Aftertouch) сообщения"""
        key = (channel, note)
        if key in self.active_notes:
            generator = self.active_notes[key]
            generator.handle_key_aftertouch(note, pressure)
        
        # Обновляем состояние канала
        self.channel_states[channel]["key_pressure"][note] = pressure
    
    def _handle_control_change(self, channel: int, controller: int, value: int):
        """Обработка Control Change сообщения"""
        # Обновляем состояние контроллера
        self.channel_states[channel]["controllers"][controller] = value
        
        # Обработка специфических контроллеров
        if controller == 1:  # Modulation Wheel
            self.channel_states[channel]["mod_wheel"] = value
        elif controller == 7:  # Volume
            self.channel_states[channel]["volume"] = value
        elif controller == 10:  # Pan
            self.channel_states[channel]["pan"] = value
        elif controller == 11:  # Expression
            self.channel_states[channel]["expression"] = value
        elif controller == 64:  # Sustain Pedal
            self.channel_states[channel]["sustain_pedal"] = (value >= 64)
        elif controller == 65:  # Portamento Switch
            self.channel_states[channel]["portamento"] = (value >= 64)
        elif controller == 91:  # Reverb Send
            self.channel_states[channel]["reverb_send"] = value
        elif controller == 93:  # Chorus Send
            self.channel_states[channel]["chorus_send"] = value
        elif controller == 120:  # All Sound Off
            self._handle_all_sound_off(channel)
        elif controller == 121:  # Reset All Controllers
            self._handle_reset_all_controllers(channel)
        elif controller == 123:  # All Notes Off
            self._handle_all_notes_off(channel)
        
        # Обработка RPN/NRPN
        if controller == self.RPN_MSB:
            self.rpn_states[channel]["msb"] = value
            self.nrpn_states[channel]["msb"] = 127  # Сбрасываем NRPN
        elif controller == self.RPN_LSB:
            self.rpn_states[channel]["lsb"] = value
            self.nrpn_states[channel]["lsb"] = 127  # Сбрасываем NRPN
        elif controller == self.NRPN_MSB:
            self.nrpn_states[channel]["msb"] = value
            self.rpn_states[channel]["msb"] = 127  # Сбрасываем RPN
        elif controller == self.NRPN_LSB:
            self.nrpn_states[channel]["lsb"] = value
            self.rpn_states[channel]["lsb"] = 127  # Сбрасываем RPN
        elif controller == self.DATA_ENTRY_MSB:
            self.data_entry_states[channel]["msb"] = value
            self._handle_data_entry(channel)
        elif controller == self.DATA_ENTRY_LSB:
            self.data_entry_states[channel]["lsb"] = value
            self._handle_data_entry(channel)
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_controller_change(controller, value)
    
    def _handle_program_change(self, channel: int, program: int):
        """Обработка Program Change сообщения"""
        self.channel_states[channel]["program"] = program
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_program_change(program)
    
    def _handle_channel_pressure(self, channel: int, pressure: int):
        """Обработка Channel Pressure (Aftertouch) сообщения"""
        self.channel_states[channel]["channel_pressure"] = pressure
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_aftertouch(pressure)
    
    def _handle_pitch_bend(self, channel: int, lsb: int, msb: int):
        """Обработка Pitch Bend сообщения"""
        # 14-битное значение pitch bend
        value = (msb << 7) | lsb
        self.channel_states[channel]["pitch_bend"] = value
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_pitch_bend(value)
    
    def _handle_data_entry(self, channel: int):
        """Обработка Data Entry для RPN/NRPN"""
        # Получаем текущие состояния
        rpn_msb = self.rpn_states[channel]["msb"]
        rpn_lsb = self.rpn_states[channel]["lsb"]
        nrpn_msb = self.nrpn_states[channel]["msb"]
        nrpn_lsb = self.nrpn_states[channel]["lsb"]
        data_msb = self.data_entry_states[channel]["msb"]
        data_lsb = self.data_entry_states[channel]["lsb"]
        
        # Проверяем, что RPN или NRPN установлены
        if rpn_msb != 127 and rpn_lsb != 127:
            # Обрабатываем RPN
            self._handle_rpn(channel, rpn_msb, rpn_lsb, data_msb, data_lsb)
        elif nrpn_msb != 127 and nrpn_lsb != 127:
            # Обрабатываем NRPN
            self._handle_nrpn(channel, nrpn_msb, nrpn_lsb, data_msb, data_lsb)
    
    def _handle_rpn(self, channel: int, rpn_msb: int, rpn_lsb: int, data_msb: int, data_lsb: int):
        """Обработка Registered Parameter Number"""
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_rpn(rpn_msb, rpn_lsb, data_msb, data_lsb)
    
    def _handle_nrpn(self, channel: int, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int):
        """Обработка Non-Registered Parameter Number"""
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                generator.handle_nrpn(nrpn_msb, nrpn_lsb, data_msb, data_lsb)
    
    def _handle_yamaha_sysex(self, data: List[int]):
        """Обработка Yamaha SYSEX сообщений"""
        if len(data) < 6:
            return
        
        # device_id = data[2]
        sub_status = data[3]
        
        # XG System On
        if sub_status == 0x4C and len(data) >= 8 and data[4] == 0x00 and data[5] == 0x00 and data[6] == 0x7E:
            self._initialize_xg()
        # XG Parameter Change
        elif sub_status == 0x4C and len(data) >= 7:
            self._handle_xg_parameter_change(data[4:])
        # XG Bulk Parameter Dump
        elif sub_status == 0x7F:
            self._handle_xg_bulk_parameter_dump(data[4:])
        # Другие XG сообщения
        else:
            # Передаем сообщение менеджеру эффектов
            manufacturer_id = [0x43]
            self.effect_manager.handle_sysex(manufacturer_id, data[1:])
    
    def _handle_xg_parameter_change(self, data: List[int]):
        """Обработка XG Parameter Change сообщения"""
        if len(data) < 3:
            return
        
        # Извлечение параметра и значения
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value_msb = data[2]
        value_lsb = data[3] if len(data) > 3 else 0
        
        # 14-битное значение
        value = (value_msb << 7) | value_lsb
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            generator.handle_xg_parameter_change(parameter_msb, parameter_lsb, value_msb, value_lsb)
        
        # Передаем сообщение менеджеру эффектов
        self.effect_manager.handle_xg_parameter_change(parameter_msb, parameter_lsb, value_msb, value_lsb)
    
    def _handle_xg_bulk_parameter_dump(self, data: List[int]):
        """Обработка XG Bulk Parameter Dump сообщения"""
        if len(data) < 2:
            return
        
        # Извлечение типа данных
        bank = data[0]
        data_type = data[1]
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            generator.handle_xg_bulk_parameter_dump(bank, data_type, data[2:])
        
        # Передаем сообщение менеджеру эффектов
        self.effect_manager.handle_xg_bulk_parameter_dump(bank, data_type, data[2:])
    
    def _handle_all_sound_off(self, channel: int):
        """Обработка All Sound Off контроллера"""
        # Останавливаем все активные ноты на канале
        keys_to_remove = []
        for key, generator in self.active_notes.items():
            if key[0] == channel:
                generator.note_off()
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.active_notes[key]
    
    def _handle_reset_all_controllers(self, channel: int):
        """Обработка Reset All Controllers контроллера"""
        # Сбрасываем состояние контроллеров канала
        self.channel_states[channel] = self._create_channel_state()
        
        # Передаем сообщение активным тон-генераторам
        for generator in self.tone_generators:
            if generator.channel == channel:
                # Сбрасываем контроллеры в тон-генераторе
                pass  # Реализация зависит от внутренней структуры тон-генератора
    
    def _handle_all_notes_off(self, channel: int):
        """Обработка All Notes Off контроллера"""
        # Останавливаем все активные ноты на канале
        keys_to_remove = []
        for key, generator in self.active_notes.items():
            if key[0] == channel:
                generator.note_off()
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.active_notes[key]
    
    def _create_tone_generator(self, note: int, velocity: int, program: int, channel: int, bank: int) -> Optional[XGToneGenerator]:
        """Создание нового тон-генератора"""
        if not self.sf2_manager:
            return None
        
        # Определяем, барабан ли это (канал 9 или специальный банк)
        is_drum = (channel == 9) or (bank == 128)
        
        # Получаем матрицу модуляции из SoundFont
        modulation_matrix = []
        if hasattr(self.sf2_manager, 'get_modulation_matrix'):
            modulation_matrix = self.sf2_manager.get_modulation_matrix(program, bank)
        
        # Создаем тон-генератор
        try:
            generator = XGToneGenerator(
                wavetable=self.sf2_manager,
                note=note,
                velocity=velocity,
                program=program,
                channel=channel,
                sample_rate=self.sample_rate,
                is_drum=is_drum,
                modulation_matrix=modulation_matrix,
                bank=bank
            )
            
            # Устанавливаем уникальный ID
            generator.id = self.generator_id_counter
            self.generator_id_counter += 1
            
            return generator
        except Exception as e:
            print(f"Ошибка при создании тон-генератора: {e}")
            return None
    
    def generate_audio_block(self, block_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Генерация аудио блока.
        
        Args:
            block_size: размер блока в сэмплах (если None, используется значение по умолчанию)
            
        Returns:
            кортеж (left_channel, right_channel) с аудио данными
        """
        if block_size is None:
            block_size = self.block_size
        
        # Создаем буферы для аудио данных
        left_buffer = np.zeros(block_size, dtype=np.float32)
        right_buffer = np.zeros(block_size, dtype=np.float32)
        
        with self.lock:
            # Генерируем аудио для каждого активного тон-генератора
            active_generators = []
            for generator in self.tone_generators:
                if generator.is_active():
                    active_generators.append(generator)
            
            # Обновляем список тон-генераторов
            self.tone_generators = active_generators
            
            # Генерируем аудио
            for i in range(block_size):
                left_sample = 0.0
                right_sample = 0.0
                
                # Суммируем выходы всех активных генераторов
                for generator in active_generators:
                    try:
                        l, r = generator.generate_sample()
                        left_sample += l
                        right_sample += r
                    except Exception as e:
                        print(f"Ошибка при генерации сэмпла: {e}")
                        # Отключаем проблемный генератор
                        generator.active = False
                
                # Применяем мастер-громкость
                left_sample *= self.master_volume
                right_sample *= self.master_volume
                
                # Ограничиваем значения
                left_buffer[i] = max(-1.0, min(1.0, left_sample))
                right_buffer[i] = max(-1.0, min(1.0, right_sample))
            
            # Применяем эффекты
            try:
                effected_samples = self.effect_manager.process_audio(
                    [(left_buffer[i], right_buffer[i]) for i in range(block_size)],
                    block_size
                )
                left_buffer = np.array([s[0] for s in effected_samples], dtype=np.float32)
                right_buffer = np.array([s[1] for s in effected_samples], dtype=np.float32)
            except Exception as e:
                print(f"Ошибка при обработке эффектов: {e}")
        
        return left_buffer, right_buffer
    
    def get_active_voice_count(self) -> int:
        """Получение количества активных голосов"""
        with self.lock:
            return len([g for g in self.tone_generators if g.is_active()])
    
    def get_available_programs(self) -> List[Tuple[int, int, str]]:
        """
        Получение списка доступных программ (пресетов).
        
        Returns:
            Список кортежей (bank, program, name)
        """
        if self.sf2_manager:
            with self.lock:
                return self.sf2_manager.get_available_presets()
        return []
    
    def reset(self):
        """Полный сброс синтезатора"""
        with self.lock:
            # Останавливаем все активные ноты
            for generator in self.tone_generators:
                try:
                    generator.note_off()
                except:
                    pass
            
            # Очищаем все структуры
            self.tone_generators.clear()
            self.active_notes.clear()
            
            # Сбрасываем состояния каналов
            self.channel_states = [self._create_channel_state() for _ in range(16)]
            
            # Сбрасываем RPN/NRPN состояния
            self.rpn_states = [{"msb": 127, "lsb": 127} for _ in range(16)]
            self.nrpn_states = [{"msb": 127, "lsb": 127} for _ in range(16)]
            self.data_entry_states = [{"msb": 0, "lsb": 0} for _ in range(16)]
            
            # Сбрасываем эффекты
            self.effect_manager.reset_effects()
            
            # Переинициализируем XG
            self._initialize_xg()


# Пример использования:
#
# # Создание синтезатора
# synth = XGSynthesizer(sample_rate=44100, block_size=512, max_polyphony=64)
#
# # Установка SF2 файлов
# synth.set_sf2_files(["path/to/soundfont1.sf2", "path/to/soundfont2.sf2"])
#
# # Настройка черных списков и маппинга банков
# synth.set_bank_blacklist("path/to/soundfont1.sf2", [120, 121, 122])
# synth.set_preset_blacklist("path/to/soundfont1.sf2", [(0, 30), (0, 31)])
# synth.set_bank_mapping("path/to/soundfont1.sf2", {1: 0, 2: 1})
#
# # Отправка MIDI сообщений
# synth.send_midi_message(0x90, 60, 100)  # Note On: C4, velocity 100 на канале 0
# synth.send_midi_message(0x80, 60, 64)   # Note Off: C4 на канале 0
#
# # Генерация аудио блока
# left_channel, right_channel = synth.generate_audio_block(1024)
#
# # Получение информации
# voice_count = synth.get_active_voice_count()
# programs = synth.get_available_programs()