import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any, Union, TypeVar

T = TypeVar('T')

class XGEffectManager:
    """
    Полная реализация менеджера звуковых эффектов в соответствии со стандартом MIDI XG.
    Поддерживает системные эффекты, Insertion Effects, мультитимбральный режим и полный набор
    вариационных эффектов. Интегрируется с секвенсором через NRPN и SysEx сообщения.
    """
    
    # Константы для преобразования параметров
    TIME_CENTISECONDS_TO_SECONDS = 0.01
    FILTER_CUTOFF_SCALE = 0.1
    PAN_SCALE = 0.01
    VELOCITY_SENSE_SCALE = 0.01
    PITCH_SCALE = 0.1
    FILTER_RESONANCE_SCALE = 0.01
    
    # Количество MIDI-каналов в мультитимбральном режиме
    NUM_CHANNELS = 16
    
    # Сопоставление NRPN параметров XG для эффектов
    XG_EFFECT_NRPN_PARAMS = {
        # Reverb Parameters
        (0, 120): {"target": "reverb", "param": "type", "transform": lambda x: min(x, 7)},  # 0-7 типы
        (0, 121): {"target": "reverb", "param": "time", "transform": lambda x: 0.1 + x * 0.05},  # 0.1-8.3 сек
        (0, 122): {"target": "reverb", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 123): {"target": "reverb", "param": "pre_delay", "transform": lambda x: x * 0.1},  # 0-12.7 мс
        (0, 124): {"target": "reverb", "param": "hf_damping", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 125): {"target": "reverb", "param": "density", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 126): {"target": "reverb", "param": "early_level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 127): {"target": "reverb", "param": "tail_level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        
        # Chorus Parameters
        (0, 130): {"target": "chorus", "param": "type", "transform": lambda x: min(x, 7)},  # 0-7 типы
        (0, 131): {"target": "chorus", "param": "rate", "transform": lambda x: 0.1 + x * 0.05},  # 0.1-6.5 Гц
        (0, 132): {"target": "chorus", "param": "depth", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 133): {"target": "chorus", "param": "feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 134): {"target": "chorus", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 135): {"target": "chorus", "param": "delay", "transform": lambda x: x * 0.1},  # 0-12.7 мс
        (0, 136): {"target": "chorus", "param": "output", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 137): {"target": "chorus", "param": "cross_feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0
        
        # Variation Effect Parameters
        (0, 140): {"target": "variation", "param": "type", "transform": lambda x: min(x, 63)},  # 0-63 типы
        (0, 141): {"target": "variation", "param": "parameter1", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 142): {"target": "variation", "param": "parameter2", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 143): {"target": "variation", "param": "parameter3", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 144): {"target": "variation", "param": "parameter4", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 145): {"target": "variation", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 146): {"target": "variation", "param": "bypass", "transform": lambda x: x > 64},  # true/false
        
        # Insertion Effect Parameters (канал-специфичные)
        (0, 150): {"target": "insertion", "param": "type", "transform": lambda x: min(x, 15)},  # 0-15 типы
        (0, 151): {"target": "insertion", "param": "parameter1", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 152): {"target": "insertion", "param": "parameter2", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 153): {"target": "insertion", "param": "parameter3", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 154): {"target": "insertion", "param": "parameter4", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 155): {"target": "insertion", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 156): {"target": "insertion", "param": "bypass", "transform": lambda x: x > 64},  # true/false
        
        # Equalizer Parameters
        (0, 100): {"target": "equalizer", "param": "low_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 101): {"target": "equalizer", "param": "mid_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 102): {"target": "equalizer", "param": "high_gain", "transform": lambda x: (x - 64) * 0.2},  # дБ
        (0, 103): {"target": "equalizer", "param": "mid_freq", "transform": lambda x: 100 + x * 40},  # Гц
        (0, 104): {"target": "equalizer", "param": "q_factor", "transform": lambda x: 0.5 + x * 0.04},  # Q-фактор
        
        # Stereo Parameters
        (0, 110): {"target": "stereo", "param": "width", "transform": lambda x: x / 127.0},  # Ширина стерео
        (0, 111): {"target": "stereo", "param": "chorus", "transform": lambda x: x / 127.0},  # Уровень хоруса
        
        # Global Effect Parameters
        (0, 112): {"target": "global", "param": "reverb_send", "transform": lambda x: x / 127.0},  # Уровень отправки на реверберацию
        (0, 113): {"target": "global", "param": "chorus_send", "transform": lambda x: x / 127.0},  # Уровень отправки на хорус
        (0, 114): {"target": "global", "param": "variation_send", "transform": lambda x: x / 127.0},  # Уровень отправки на вариационный эффект
        
        # Channel-Specific Effect Parameters
        (0, 160): {"target": "channel", "param": "reverb_send", "transform": lambda x, ch: (ch, x / 127.0)},  # Уровень отправки на реверберацию для канала
        (0, 161): {"target": "channel", "param": "chorus_send", "transform": lambda x, ch: (ch, x / 127.0)},  # Уровень отправки на хорус для канала
        (0, 162): {"target": "channel", "param": "variation_send", "transform": lambda x, ch: (ch, x / 127.0)},  # Уровень отправки на вариационный эффект для канала
        (0, 163): {"target": "channel", "param": "insertion_send", "transform": lambda x, ch: (ch, x / 127.0)},  # Уровень отправки на insertion effect для канала
        (0, 164): {"target": "channel", "param": "muted", "transform": lambda x, ch: (ch, x > 64)},  # Mute канала
        (0, 165): {"target": "channel", "param": "soloed", "transform": lambda x, ch: (ch, x > 64)},  # Solo канала
        (0, 166): {"target": "channel", "param": "pan", "transform": lambda x, ch: (ch, (x - 64) / 64.0)},  # Панорамирование канала
        (0, 167): {"target": "channel", "param": "volume", "transform": lambda x, ch: (ch, x / 127.0)},  # Громкость канала
        
        # Effect Routing Parameters
        (0, 170): {"target": "routing", "param": "system_effect_order", "transform": lambda x: x},  # Порядок системных эффектов
        (0, 171): {"target": "routing", "param": "insertion_effect_order", "transform": lambda x: x},  # Порядок insertion эффектов
        (0, 172): {"target": "routing", "param": "parallel_routing", "transform": lambda x: x > 64},  # Использовать параллельную маршрутизацию
        (0, 173): {"target": "routing", "param": "reverb_to_chorus", "transform": lambda x: x / 127.0},  # Отправка реверберации на хорус
        (0, 174): {"target": "routing", "param": "chorus_to_variation", "transform": lambda x: x / 127.0},  # Отправка хоруса на вариационный эффект
    }
    
    # Типы реверберации XG
    XG_REVERB_TYPES = [
        "Hall 1", "Hall 2", "Hall 3", "Room 1", "Room 2", "Room 3", "Stage", "Plate"
    ]
    
    # Типы хоруса XG
    XG_CHORUS_TYPES = [
        "Chorus 1", "Chorus 2", "Chorus 3", "Ensemble 1", "Ensemble 2", "Flanger", "Flanger 2", "Off"
    ]
    
    # Типы вариационного эффекта XG
    XG_VARIATION_TYPES = [
        "Delay", "Dual Delay", "Echo", "Pan Delay", "Cross Delay", "Multi Tap", 
        "Reverse Delay", "Tremolo", "Auto Pan", "Phaser", "Flanger", "Auto Wah", 
        "Ring Mod", "Pitch Shifter", "Distortion", "Overdrive", "Compressor", 
        "Limiter", "Gate", "Expander", "Rotary Speaker", "Leslie", "Vibrato", 
        "Acoustic Simulator", "Guitar Amp Sim", "Enhancer", "Slicer", "Step Phaser", 
        "Step Flanger", "Step Tremolo", "Step Pan", "Step Filter", "Auto Filter", 
        "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune", "Chorus/Reverb", 
        "Stereo Imager", "Ambience", "Doubler", "Enhancer/Reverb", "Spectral", 
        "Resonator", "Degrader", "Vinyl", "Looper", "Step Delay", "Step Echo", 
        "Step Pan Delay", "Step Cross Delay", "Step Multi Tap", "Step Reverse Delay",
        "Step Ring Mod", "Step Pitch Shifter", "Step Distortion", "Step Overdrive", 
        "Step Compressor", "Step Limiter", "Step Gate", "Step Expander", "Step Rotary Speaker"
    ]
    
    # Типы Insertion Effects XG
    XG_INSERTION_TYPES = [
        "Off", "Distortion", "Overdrive", "Compressor", "Gate", "Envelope Filter", 
        "Guitar Amp Sim", "Rotary Speaker", "Leslie", "Enhancer", "Slicer", 
        "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune"
    ]
    
    # SysEx Manufacturer ID для Yamaha
    YAMAHA_MANUFACTURER_ID = [0x43]
    
    # XG SysEx sub-status codes
    XG_PARAMETER_CHANGE = 0x04
    XG_BULK_PARAMETER_DUMP = 0x7F
    XG_BULK_PARAMETER_REQUEST = 0x7E
    
    # XG Bulk Data Types для эффектов
    XG_BULK_EFFECTS = 0x03  # System parameters include effects
    XG_BULK_CHANNEL_EFFECTS = 0x04  # Channel-specific effect parameters

    def __init__(self, sample_rate: int = 44100):
        """
        Инициализация менеджера эффектов XG.
        
        Args:
            sample_rate: частота дискретизации для обработки эффектов
        """
        self.sample_rate = sample_rate
        self.current_channel = 0  # Текущий канал для обработки NRPN
        
        # Параметры реверберации
        self.reverb_params = {
            "type": 0,  # Hall 1
            "time": 2.5,  # секунды
            "level": 0.6,  # 0.0-1.0
            "pre_delay": 20.0,  # миллисекунды
            "hf_damping": 0.5,  # 0.0-1.0
            "density": 0.8,  # 0.0-1.0
            "early_level": 0.7,  # 0.0-1.0
            "tail_level": 0.9  # 0.0-1.0
        }
        
        # Параметры хоруса
        self.chorus_params = {
            "type": 0,  # Chorus 1
            "rate": 1.0,  # Гц
            "depth": 0.5,  # 0.0-1.0
            "feedback": 0.3,  # 0.0-1.0
            "level": 0.4,  # 0.0-1.0
            "delay": 0.0,  # миллисекунды
            "output": 0.8,  # 0.0-1.0
            "cross_feedback": 0.2  # 0.0-1.0
        }
        
        # Параметры вариационного эффекта
        self.variation_params = {
            "type": 0,  # Delay
            "parameter1": 0.5,  # 0.0-1.0
            "parameter2": 0.5,  # 0.0-1.0
            "parameter3": 0.5,  # 0.0-1.0
            "parameter4": 0.5,  # 0.0-1.0
            "level": 0.5,  # 0.0-1.0
            "bypass": False  # true/false
        }
        
        # Параметры эквалайзера
        self.equalizer_params = {
            "low_gain": 0.0,  # дБ
            "mid_gain": 0.0,  # дБ
            "high_gain": 0.0,  # дБ
            "mid_freq": 1000.0,  # Гц
            "q_factor": 1.0  # Q-фактор
        }
        
        # Параметры маршрутизации эффектов
        self.routing_params = {
            "system_effect_order": [0, 1, 2],  # 0=reverb, 1=chorus, 2=variation
            "insertion_effect_order": [0],  # 0=insertion effect
            "parallel_routing": False,  # Использовать параллельную маршрутизацию
            "reverb_to_chorus": 0.0,  # Отправка реверберации на хорус
            "chorus_to_variation": 0.0  # Отправка хоруса на вариационный эффект
        }
        
        # Глобальные параметры эффектов
        self.global_effect_params = {
            "reverb_send": 0.5,  # Уровень отправки на реверберацию
            "chorus_send": 0.3,  # Уровень отправки на хорус
            "variation_send": 0.2,  # Уровень отправки на вариационный эффект
            "stereo_width": 0.5,  # Ширина стерео (0.0-1.0)
            "master_level": 0.8,  # Общий уровень
            "bypass_all": False  # Обход всех эффектов
        }
        
        # Параметры для каждого MIDI-канала (16 каналов)
        self.channel_params = []
        for i in range(self.NUM_CHANNELS):
            self.channel_params.append({
                "reverb_send": 0.5,  # Уровень отправки на реверберацию
                "chorus_send": 0.3,  # Уровень отправки на хорус
                "variation_send": 0.2,  # Уровень отправки на вариационный эффект
                "insertion_send": 1.0,  # Уровень отправки на insertion effect
                "muted": False,  # Канал замьючен
                "soloed": False,  # Канал в режиме solo
                "pan": 0.5,  # Панорамирование (0.0-1.0)
                "volume": 1.0,  # Громкость (0.0-1.0)
                "insertion_effect": {
                    "type": 0,  # Off
                    "parameter1": 0.5,  # 0.0-1.0
                    "parameter2": 0.5,  # 0.0-1.0
                    "parameter3": 0.5,  # 0.0-1.0
                    "parameter4": 0.5,  # 0.0-1.0
                    "level": 1.0,  # 0.0-1.0
                    "bypass": False  # true/false
                }
            })
        
        # Внутренние состояния эффектов
        self._reverb_state = {
            "allpass_buffers": [np.zeros(441) for _ in range(4)],
            "allpass_indices": [0] * 4,
            "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
            "comb_indices": [0] * 4,
            "early_reflection_buffer": np.zeros(441),
            "early_reflection_index": 0,
            "late_reflection_buffer": np.zeros(441 * 10),
            "late_reflection_index": 0
        }
        
        self._chorus_state = {
            "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms задержки
            "lfo_phases": [0.0, 0.0],
            "lfo_rates": [1.0, 0.5],
            "lfo_depths": [0.5, 0.3],
            "write_indices": [0, 0],
            "feedback_buffers": [0.0, 0.0]
        }
        
        self._insertion_state = {
            "delay_buffer": np.zeros(441 * 2),  # 200ms задержки
            "write_index": 0,
            "feedback_buffer": 0.0
        }
        
        # Типы эффектов для bulk-дампов
        self.effect_types = {
            "reverb": self.reverb_params,
            "chorus": self.chorus_params,
            "variation": self.variation_params,
            "equalizer": self.equalizer_params,
            "routing": self.routing_params,
            "global": self.global_effect_params
        }
        
        # Состояние эффектов для каждого канала
        self.channel_effect_states = [{} for _ in range(self.NUM_CHANNELS)]
    
    def handle_nrpn(self, nrpn_msb: int, nrpn_lsb: int, data_msb: int, data_lsb: int, channel: Optional[int] = None):
        """
        Обработка NRPN сообщения (Non-Registered Parameter Number) для эффектов.
        
        Args:
            nrpn_msb: старший байт NRPN
            nrpn_lsb: младший байт NRPN
            data_msb: старший байт данных
            data_lsb: младший байт данных
            channel: MIDI-канал (если None, используется текущий)
        """
        nrpn = (nrpn_msb, nrpn_lsb)
        if nrpn not in self.XG_EFFECT_NRPN_PARAMS:
            return
            
        param_info = self.XG_EFFECT_NRPN_PARAMS[nrpn]
        data = (data_msb << 7) | data_lsb  # 14-bit value
        
        # Применение преобразования
        if "channel" in param_info["target"] and channel is None:
            # Для канал-специфичных параметров используем текущий канал
            real_value = param_info["transform"](data, self.current_channel)
        else:
            real_value = param_info["transform"](data)
        
        # Обработка параметра
        target = param_info["target"]
        param = param_info["param"]
        
        if target == "reverb":
            self.reverb_params[param] = real_value
        elif target == "chorus":
            self.chorus_params[param] = real_value
        elif target == "variation":
            self.variation_params[param] = real_value
        elif target == "equalizer":
            self.equalizer_params[param] = real_value
        elif target == "routing":
            self.routing_params[param] = real_value
        elif target == "global":
            self.global_effect_params[param] = real_value
        elif target == "insertion":
            # Insertion effects применяются к текущему каналу
            ch = channel if channel is not None else self.current_channel
            if 0 <= ch < self.NUM_CHANNELS:
                self.channel_params[ch]["insertion_effect"][param] = real_value
        elif target == "channel":
            # Обработка канал-специфичных параметров
            ch, value = real_value
            if 0 <= ch < self.NUM_CHANNELS:
                if param == "reverb_send":
                    self.channel_params[ch]["reverb_send"] = value
                elif param == "chorus_send":
                    self.channel_params[ch]["chorus_send"] = value
                elif param == "variation_send":
                    self.channel_params[ch]["variation_send"] = value
                elif param == "insertion_send":
                    self.channel_params[ch]["insertion_send"] = value
                elif param == "muted":
                    self.channel_params[ch]["muted"] = value
                elif param == "soloed":
                    self.channel_params[ch]["soloed"] = value
                elif param == "pan":
                    self.channel_params[ch]["pan"] = value
                elif param == "volume":
                    self.channel_params[ch]["volume"] = value
    
    def handle_sysex(self, manufacturer_id: List[int], data: List[int]):
        """
        Обработка SysEx сообщения (System Exclusive) для эффектов.
        
        Args:
            manufacturer_id: ID производителя (для Yamaha обычно [0x43])
             данные сообщения
        """
        # Проверка, что это Yamaha SysEx
        if manufacturer_id != self.YAMAHA_MANUFACTURER_ID:
            return
        
        # Обработка XG-specific SysEx сообщений для эффектов
        if len(data) < 3:
            return
            
        device_id = data[0]
        sub_status = data[1]
        command = data[2]
        
        # XG Parameter Change (F0 43 mm 04 0n pp vv F7)
        if sub_status == self.XG_PARAMETER_CHANGE:
            self._handle_xg_parameter_change(data[3:])
        
        # XG Bulk Parameter Dump (F0 43 mm 7F 0n tt ... F7)
        elif sub_status == self.XG_BULK_PARAMETER_DUMP:
            self._handle_xg_bulk_parameter_dump(data[3:])
    
    def _handle_xg_parameter_change(self, data: List[int]):
        """Обработка XG Parameter Change для эффектов"""
        if len(data) < 3:
            return
            
        # Извлечение параметра и значения
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value = data[2]
        
        # Обработка как NRPN
        self.handle_nrpn(parameter_msb, parameter_lsb, value, 0)
    
    def _handle_xg_bulk_parameter_dump(self, data: List[int]):
        """Обработка XG Bulk Parameter Dump для эффектов"""
        if len(data) < 2:
            return
            
        # Проверка типа данных
        data_type = data[1]
        
        # Обработка системных эффектов
        if data_type == self.XG_BULK_EFFECTS:
            self._handle_bulk_effects(data[2:])
        # Обработка канал-специфичных эффектов
        elif data_type == self.XG_BULK_CHANNEL_EFFECTS:
            self._handle_bulk_channel_effects(data[2:])
    
    def _handle_bulk_effects(self, data: List[int]):
        """Обработка bulk данных для системных эффектов"""
        # Определяем структуру bulk-дампа XG для эффектов
        offset = 0
        while offset < len(data) - 1:
            # Извлечение параметра и значения
            param_msb = data[offset]
            param_lsb = data[offset + 1]
            
            # Проверяем, является ли это NRPN для эффектов
            if (param_msb, param_lsb) in self.XG_EFFECT_NRPN_PARAMS:
                # Извлечение 14-bit значения
                if offset + 3 >= len(data):
                    break
                    
                value = (data[offset + 2] << 7) | data[offset + 3]
                
                # Обработка как NRPN
                self.handle_nrpn(param_msb, param_lsb, value >> 7, value & 0x7F)
                
                # Переход к следующему параметру
                offset += 4
            else:
                # Пропускаем неизвестный параметр
                offset += 1
    
    def _handle_bulk_channel_effects(self, data: List[int]):
        """Обработка bulk данных для канал-специфичных эффектов"""
        # Структура bulk-дампа для канал-специфичных эффектов:
        # [channel] [param_msb] [param_lsb] [value_msb] [value_lsb] ...
        
        offset = 0
        while offset < len(data) - 4:
            # Извлечение канала и параметра
            channel = data[offset]
            param_msb = data[offset + 1]
            param_lsb = data[offset + 2]
            
            # Проверяем, является ли это NRPN для канал-специфичных эффектов
            if (param_msb, param_lsb) in self.XG_EFFECT_NRPN_PARAMS:
                # Извлечение 14-bit значения
                value = (data[offset + 3] << 7) | data[offset + 4]
                
                # Обработка как NRPN для конкретного канала
                self.handle_nrpn(param_msb, param_lsb, value >> 7, value & 0x7F, channel)
                
                # Переход к следующему параметру
                offset += 5
            else:
                # Пропускаем неизвестный параметр
                offset += 1
    
    def get_bulk_dump(self, channel_specific: bool = False) -> List[int]:
        """
        Генерация bulk-дампа текущих параметров эффектов.
        
        Args:
            channel_specific: если True, генерирует дамп для канал-специфичных эффектов
            
        Returns:
            Список байт для SysEx сообщения
        """
        if not channel_specific:
            # Структура bulk-дампа для системных эффектов:
            # F0 43 mm 7F 00 03 [данные] F7
            
            # Начинаем с заголовка
            dump = [0x43, 0x7F, 0x00, self.XG_BULK_EFFECTS]
            
            # Добавляем параметры эффектов в bulk-формате
            for target, params in self.effect_types.items():
                for param, value in params.items():
                    # Находим соответствующий NRPN
                    nrpn = self._find_nrpn_for_parameter(target, param)
                    if nrpn is None:
                        continue
                    
                    # Преобразуем значение в 14-bit формат
                    data_value = self._convert_to_bulk_value(target, param, value)
                    
                    # Добавляем в дамп
                    dump.append(nrpn[0])  # MSB
                    dump.append(nrpn[1])  # LSB
                    dump.append((data_value >> 7) & 0x7F)  # MSB данных
                    dump.append(data_value & 0x7F)  # LSB данных
            
            return dump
        else:
            # Структура bulk-дампа для канал-специфичных эффектов:
            # F0 43 mm 7F 00 04 [данные] F7
            
            # Начинаем с заголовка
            dump = [0x43, 0x7F, 0x00, self.XG_BULK_CHANNEL_EFFECTS]
            
            # Добавляем параметры для каждого канала
            for channel in range(self.NUM_CHANNELS):
                channel_params = self.channel_params[channel]
                
                # Добавляем insertion effect параметры
                insertion_effect = channel_params["insertion_effect"]
                for param, value in insertion_effect.items():
                    nrpn = self._find_nrpn_for_parameter("insertion", param)
                    if nrpn is None:
                        continue
                    
                    data_value = self._convert_to_bulk_value("insertion", param, value)
                    dump.append(channel)
                    dump.append(nrpn[0])
                    dump.append(nrpn[1])
                    dump.append((data_value >> 7) & 0x7F)
                    dump.append(data_value & 0x7F)
                
                # Добавляем канал-специфичные параметры
                for param in ["reverb_send", "chorus_send", "variation_send", 
                             "insertion_send", "muted", "soloed", "pan", "volume"]:
                    nrpn = self._find_nrpn_for_parameter("channel", param)
                    if nrpn is None:
                        continue
                    
                    # Преобразуем значение в 14-bit формат
                    value = channel_params[param]
                    if param == "muted" or param == "soloed":
                        data_value = 127 if value else 0
                    elif param == "pan":
                        data_value = int((value * 2 - 1) * 64 + 64)
                    else:
                        data_value = int(value * 127)
                    
                    dump.append(channel)
                    dump.append(nrpn[0])
                    dump.append(nrpn[1])
                    dump.append((data_value >> 7) & 0x7F)
                    dump.append(data_value & 0x7F)
            
            return dump
    
    def _find_nrpn_for_parameter(self, target: str, param: str) -> Optional[Tuple[int, int]]:
        """Поиск NRPN для указанного параметра"""
        for nrpn, info in self.XG_EFFECT_NRPN_PARAMS.items():
            if info["target"] == target and info["param"] == param:
                return nrpn
        return None
    
    def _convert_to_bulk_value(self, target: str, param: str, value: Union[float, bool, int]) -> int:
        """Преобразование значения параметра в 14-bit формат для bulk-дампа"""
        # Находим NRPN для параметра
        nrpn = self._find_nrpn_for_parameter(target, param)
        if nrpn is None:
            return 0
        
        # Находим обратное преобразование
        param_info = self.XG_EFFECT_NRPN_PARAMS[nrpn]
        
        # Для булевых значений
        if isinstance(value, bool):
            return 127 if value else 0
        
        # Для численных значений
        if target == "reverb":
            if param == "type":
                return int(value)
            elif param == "time":
                return int((value - 0.1) / 0.05)
            elif param == "level" or param == "hf_damping" or param == "density" or \
                 param == "early_level" or param == "tail_level":
                return int(value * 127)
            elif param == "pre_delay":
                return int(value / 0.1)
        
        elif target == "chorus":
            if param == "type":
                return int(value)
            elif param == "rate":
                return int((value - 0.1) / 0.05)
            elif param == "depth" or param == "feedback" or param == "level" or \
                 param == "output" or param == "cross_feedback":
                return int(value * 127)
            elif param == "delay":
                return int(value / 0.1)
        
        elif target == "variation" or target == "insertion":
            if param == "type":
                return int(value)
            elif param.startswith("parameter") or param == "level":
                return int(value * 127)
            elif param == "bypass":
                return 127 if value else 0
        
        elif target == "equalizer":
            if param == "low_gain" or param == "mid_gain" or param == "high_gain":
                return int((value / 0.2) + 64)
            elif param == "mid_freq":
                return int((value - 100) / 40)
            elif param == "q_factor":
                return int((value - 0.5) / 0.04)
        
        elif target == "routing":
            if param == "system_effect_order" or param == "insertion_effect_order":
                # Для порядка эффектов используем битовое представление
                order_value = 0
                for i, effect in enumerate(value):
                    order_value |= (effect << (i * 4))
                return order_value
            elif param == "parallel_routing":
                return 127 if value else 0
            elif param == "reverb_to_chorus" or param == "chorus_to_variation":
                return int(value * 127)
        
        elif target == "global" or "channel" in target:
            if param == "reverb_send" or param == "chorus_send" or param == "variation_send" or \
               param == "insertion_send" or param == "stereo_width" or param == "master_level":
                return int(value * 127)
            elif param == "bypass_all" or param == "muted" or param == "soloed":
                return 127 if value else 0
            elif param == "pan":
                return int((value * 2 - 1) * 64 + 64)
            elif param == "volume":
                return int(value * 127)
        
        # По умолчанию просто масштабируем до 0-127
        return int(value * 127)
    
    def process_audio(self, input_samples: List[Tuple[float, float]], 
                     channel_levels: Optional[List[float]] = None) -> List[Tuple[float, float]]:
        """
        Обработка аудио с применением эффектов для всех каналов.
        
        Args:
            input_samples: список стерео сэмплов для каждого канала [(left, right), ...]
            channel_levels: уровни для каждого канала (если None, используется 1.0)
            
        Returns:
            список обработанных стерео сэмплов [(left, right), ...]
        """
        if len(input_samples) != self.NUM_CHANNELS:
            raise ValueError(f"Ожидалось {self.NUM_CHANNELS} каналов, получено {len(input_samples)}")
        
        # Инициализация выходных данных
        output_samples = [(0.0, 0.0)] * self.NUM_CHANNELS
        system_input = (0.0, 0.0)
        
        # Определение активных каналов (учет mute/solo)
        active_channels = self._get_active_channels()
        
        # Обработка Insertion Effects для каждого канала
        insertion_outputs = []
        for i in range(self.NUM_CHANNELS):
            if i not in active_channels:
                insertion_outputs.append((0.0, 0.0))
                continue
                
            left_in, right_in = input_samples[i]
            
            # Применение Insertion Effect
            insertion_send = self.channel_params[i]["insertion_send"]
            if insertion_send > 0 and not self.channel_params[i]["insertion_effect"]["bypass"]:
                insertion_out = self._process_insertion_effect(
                    (left_in, right_in), 
                    self.channel_params[i]["insertion_effect"],
                    self.channel_effect_states[i]
                )
                insertion_left, insertion_right = insertion_out
                insertion_left *= insertion_send
                insertion_right *= insertion_send
            else:
                insertion_left, insertion_right = 0.0, 0.0
            
            # Сохраняем для дальнейшей обработки
            insertion_outputs.append((insertion_left, insertion_right))
            
            # Формируем сигнал для системных эффектов
            channel_level = channel_levels[i] if channel_levels else 1.0
            reverb_send = self.channel_params[i]["reverb_send"] * channel_level
            chorus_send = self.channel_params[i]["chorus_send"] * channel_level
            variation_send = self.channel_params[i]["variation_send"] * channel_level
            
            system_left = left_in * (1 - insertion_send) * channel_level
            system_right = right_in * (1 - insertion_send) * channel_level
            
            # Добавляем к системному входу
            system_input = (
                system_input[0] + system_left * reverb_send,
                system_input[1] + system_right * reverb_send
            )
        
        # Обработка системных эффектов
        system_output = (0.0, 0.0)
        if not self.global_effect_params["bypass_all"] and any(active_channels):
            # Применение маршрутизации эффектов
            system_output = self._process_effect_routing(system_input, active_channels)
        
        # Смешивание результатов
        for i in range(self.NUM_CHANNELS):
            if i not in active_channels:
                output_samples[i] = (0.0, 0.0)
                continue
                
            # Получаем Insertion Effect output
            insertion_left, insertion_right = insertion_outputs[i]
            
            # Получаем вклад системных эффектов
            system_contrib = (
                system_output[0] * self.channel_params[i]["reverb_send"],
                system_output[1] * self.channel_params[i]["reverb_send"]
            )
            
            # Смешиваем оригинальный сигнал, Insertion Effect и системные эффекты
            channel_volume = self.channel_params[i]["volume"]
            channel_pan = self.channel_params[i]["pan"]
            
            # Панорамирование
            left_volume = channel_volume * (1.0 - channel_pan)
            right_volume = channel_volume * channel_pan
            
            output_samples[i] = (
                (insertion_left + system_contrib[0]) * left_volume,
                (insertion_right + system_contrib[1]) * right_volume
            )
        
        # Применение общего уровня
        master_level = self.global_effect_params["master_level"]
        output_samples = [
            (left * master_level, right * master_level) 
            for left, right in output_samples
        ]
        
        return output_samples
    
    def _get_active_channels(self) -> List[int]:
        """Определение активных каналов с учетом mute/solo"""
        soloed_channels = [i for i in range(self.NUM_CHANNELS) 
                          if self.channel_params[i]["soloed"]]
        
        if soloed_channels:
            return soloed_channels
        
        return [i for i in range(self.NUM_CHANNELS) 
               if not self.channel_params[i]["muted"]]
    
    def _process_effect_routing(self, input_sample: Tuple[float, float], 
                               active_channels: List[int]) -> Tuple[float, float]:
        """Обработка маршрутизации эффектов в соответствии с настройками"""
        left_in, right_in = input_sample
        left_out, right_out = left_in, right_in
        
        # Получаем порядок эффектов
        effect_order = self.routing_params["system_effect_order"]
        
        # Обработка в указанном порядке
        for effect_index in effect_order:
            if effect_index == 0:  # Reverb
                reverb_amount = 1.0
                if self.routing_params["reverb_to_chorus"] > 0 and 1 in effect_order:
                    # Для параллельной маршрутизации сохраняем часть сигнала
                    reverb_amount = 1.0 - self.routing_params["reverb_to_chorus"]
                
                reverb_left, reverb_right = self._process_reverb(
                    left_in * reverb_amount, 
                    right_in * reverb_amount
                )
                left_out += reverb_left * self.reverb_params["level"]
                right_out += reverb_right * self.reverb_params["level"]
                
                # Для последующих эффектов используем выход реверберации
                if self.routing_params["reverb_to_chorus"] > 0 and 1 in effect_order:
                    left_in = reverb_left * self.routing_params["reverb_to_chorus"]
                    right_in = reverb_right * self.routing_params["reverb_to_chorus"]
                else:
                    left_in, right_in = left_out, right_out
            
            elif effect_index == 1:  # Chorus
                chorus_amount = 1.0
                if self.routing_params["chorus_to_variation"] > 0 and 2 in effect_order:
                    # Для параллельной маршрутизации сохраняем часть сигнала
                    chorus_amount = 1.0 - self.routing_params["chorus_to_variation"]
                
                chorus_left, chorus_right = self._process_chorus(
                    left_in * chorus_amount, 
                    right_in * chorus_amount
                )
                left_out += chorus_left * self.chorus_params["level"]
                right_out += chorus_right * self.chorus_params["level"]
                
                # Для последующих эффектов используем выход хоруса
                if self.routing_params["chorus_to_variation"] > 0 and 2 in effect_order:
                    left_in = chorus_left * self.routing_params["chorus_to_variation"]
                    right_in = chorus_right * self.routing_params["chorus_to_variation"]
                else:
                    left_in, right_in = left_out, right_out
            
            elif effect_index == 2:  # Variation
                variation_left, variation_right = self._process_variation_effect(
                    left_in, 
                    right_in
                )
                left_out += variation_left * self.variation_params["level"]
                right_out += variation_right * self.variation_params["level"]
        
        # Применение эквалайзера ко всему сигналу
        left_out, right_out = self._apply_equalizer(left_out, right_out)
        
        return (left_out, right_out)
    
    def _apply_equalizer(self, left: float, right: float) -> Tuple[float, float]:
        """Применение эквалайзера к аудио сэмплу"""
        # Реализация 3-полосного эквалайзера с использованием билинейного преобразования
        low_gain = 10 ** (self.equalizer_params["low_gain"] / 20.0)
        mid_gain = 10 ** (self.equalizer_params["mid_gain"] / 20.0)
        high_gain = 10 ** (self.equalizer_params["high_gain"] / 20.0)
        mid_freq = self.equalizer_params["mid_freq"]
        q_factor = self.equalizer_params["q_factor"]
        
        # Вычисляем коэффициенты для полосового фильтра
        w0 = 2 * math.pi * mid_freq / self.sample_rate
        alpha = math.sin(w0) / (2 * q_factor)
        
        # Коэффициенты для полосового фильтра
        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        # Применение фильтрации
        # В реальной реализации здесь были бы буферы состояния фильтра
        # Для упрощения просто умножаем на коэффициенты
        mid_left = left * (mid_gain - 1.0)
        mid_right = right * (mid_gain - 1.0)
        
        return (
            left * low_gain + mid_left + right * high_gain,
            right * low_gain + mid_right + right * high_gain
        )
    
    def _process_reverb(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка реверберации с использованием алгоритма Schroeder"""
        # Используем параметры реверберации
        reverb_type = self.reverb_params["type"]
        time = self.reverb_params["time"]
        level = self.reverb_params["level"]
        pre_delay = self.reverb_params["pre_delay"]
        hf_damping = self.reverb_params["hf_damping"]
        density = self.reverb_params["density"]
        early_level = self.reverb_params["early_level"]
        tail_level = self.reverb_params["tail_level"]
        
        # Алгоритм Schroeder для реверберации
        allpass_buffers = self._reverb_state["allpass_buffers"]
        allpass_indices = self._reverb_state["allpass_indices"]
        comb_buffers = self._reverb_state["comb_buffers"]
        comb_indices = self._reverb_state["comb_indices"]
        early_reflection_buffer = self._reverb_state["early_reflection_buffer"]
        early_reflection_index = self._reverb_state["early_reflection_index"]
        late_reflection_buffer = self._reverb_state["late_reflection_buffer"]
        late_reflection_index = self._reverb_state["late_reflection_index"]
        
        # Входной сигнал
        input_sample = (left + right) / 2.0
        
        # Предварительная задержка
        pre_delay_samples = int(pre_delay * self.sample_rate / 1000.0)
        if pre_delay_samples >= len(early_reflection_buffer):
            pre_delay_samples = len(early_reflection_buffer) - 1
        
        # Запись в буфер предварительной задержки
        early_reflection_buffer[early_reflection_index] = input_sample
        early_reflection_index = (early_reflection_index + 1) % len(early_reflection_buffer)
        
        # Чтение из буфера с предварительной задержкой
        pre_delay_index = (early_reflection_index - pre_delay_samples) % len(early_reflection_buffer)
        pre_delay_sample = early_reflection_buffer[int(pre_delay_index)]
        
        # Ранние отражения
        early_reflections = pre_delay_sample * early_level
        
        # Плотность отражений (density)
        # Влияет на количество и распределение комб-фильтров
        num_comb_filters = 4 + int(density * 4)
        
        # Обработка через комб-фильтры
        comb_input = early_reflections
        for i in range(min(num_comb_filters, len(comb_buffers))):
            # Длина задержки для комб-фильтра (увеличивается для каждого фильтра)
            delay_length = int(time * self.sample_rate * (i + 1) / 8.0)
            if delay_length >= len(comb_buffers[i]):
                delay_length = len(comb_buffers[i]) - 1
            
            # Чтение из буфера задержки
            read_index = (comb_indices[i] - delay_length) % len(comb_buffers[i])
            comb_sample = comb_buffers[i][int(read_index)]
            
            # Запись в буфер задержки с обратной связью и затуханием высоких частот
            feedback = 0.7 + (i * 0.05)  # Увеличиваем feedback для более длинных задержек
            comb_buffers[i][comb_indices[i]] = comb_input + comb_sample * feedback * (1.0 - hf_damping)
            comb_indices[i] = (comb_indices[i] + 1) % len(comb_buffers[i])
            
            # Добавляем к выходу
            comb_input += comb_sample * tail_level
        
        # Обработка через allpass фильтры для диффузии
        allpass_output = comb_input
        for i in range(len(allpass_buffers)):
            # Длина задержки для allpass фильтра
            delay_length = int(time * self.sample_rate * (i + 1) / 16.0)
            if delay_length >= len(allpass_buffers[i]):
                delay_length = len(allpass_buffers[i]) - 1
            
            # Чтение из буфера задержки
            read_index = (allpass_indices[i] - delay_length) % len(allpass_buffers[i])
            allpass_sample = allpass_buffers[i][int(read_index)]
            
            # Запись в буфер задержки
            allpass_buffers[i][allpass_indices[i]] = allpass_output
            allpass_indices[i] = (allpass_indices[i] + 1) % len(allpass_buffers[i])
            
            # Применение allpass фильтра
            g = 0.7  # Коэффициент затухания
            allpass_output = -g * allpass_output + allpass_sample + g * allpass_sample
        
        # Сохраняем состояние
        self._reverb_state["allpass_indices"] = allpass_indices
        self._reverb_state["comb_indices"] = comb_indices
        self._reverb_state["early_reflection_index"] = early_reflection_index
        self._reverb_state["late_reflection_index"] = late_reflection_index
        
        # Возвращаем стерео сигнал
        return (allpass_output * level * 0.7, allpass_output * level * 0.7)
    
    def _process_chorus(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка хоруса с использованием двух LFO и стерео обработки"""
        # Используем параметры хоруса
        chorus_type = self.chorus_params["type"]
        rate = self.chorus_params["rate"]
        depth = self.chorus_params["depth"]
        feedback = self.chorus_params["feedback"]
        level = self.chorus_params["level"]
        delay = self.chorus_params["delay"]
        output = self.chorus_params["output"]
        cross_feedback = self.chorus_params["cross_feedback"]
        
        # Стерео хорус с двумя LFO
        delay_lines = self._chorus_state["delay_lines"]
        lfo_phases = self._chorus_state["lfo_phases"]
        lfo_rates = self._chorus_state["lfo_rates"]
        lfo_depths = self._chorus_state["lfo_depths"]
        write_indices = self._chorus_state["write_indices"]
        feedback_buffers = self._chorus_state["feedback_buffers"]
        
        # Обработка левого канала
        left_input = left
        
        # Обновление LFO для левого канала
        lfo_phases[0] = (lfo_phases[0] + lfo_rates[0] * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Модуляция задержки
        base_delay_samples = int(delay * self.sample_rate / 1000.0)
        modulation = int(lfo_depths[0] * depth * self.sample_rate / 1000.0 * (1 + math.sin(lfo_phases[0])) / 2)
        total_delay = base_delay_samples + modulation
        
        if total_delay >= len(delay_lines[0]):
            total_delay = len(delay_lines[0]) - 1
        
        # Чтение из буфера
        read_index = (write_indices[0] - total_delay) % len(delay_lines[0])
        delayed_sample = delay_lines[0][int(read_index)]
        
        # Применение feedback
        feedback_sample = delayed_sample * feedback + feedback_buffers[0] * cross_feedback
        delay_lines[0][write_indices[0]] = left_input + feedback_sample
        
        # Обновление индекса записи
        write_indices[0] = (write_indices[0] + 1) % len(delay_lines[0])
        feedback_buffers[0] = feedback_sample
        
        # Обработка правого канала
        right_input = right
        
        # Обновление LFO для правого канала (с фазовым сдвигом)
        lfo_phases[1] = (lfo_phases[1] + lfo_rates[1] * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Модуляция задержки
        base_delay_samples = int(delay * self.sample_rate / 1000.0)
        modulation = int(lfo_depths[1] * depth * self.sample_rate / 1000.0 * (1 + math.sin(lfo_phases[1])) / 2)
        total_delay = base_delay_samples + modulation
        
        if total_delay >= len(delay_lines[1]):
            total_delay = len(delay_lines[1]) - 1
        
        # Чтение из буфера
        read_index = (write_indices[1] - total_delay) % len(delay_lines[1])
        delayed_sample = delay_lines[1][int(read_index)]
        
        # Применение feedback
        feedback_sample = delayed_sample * feedback + feedback_buffers[1] * cross_feedback
        delay_lines[1][write_indices[1]] = right_input + feedback_sample
        
        # Обновление индекса записи
        write_indices[1] = (write_indices[1] + 1) % len(delay_lines[1])
        feedback_buffers[1] = feedback_sample
        
        # Сохраняем состояние
        self._chorus_state["lfo_phases"] = lfo_phases
        self._chorus_state["write_indices"] = write_indices
        self._chorus_state["feedback_buffers"] = feedback_buffers
        
        # Смешивание оригинала и хоруса
        return (
            left * (1 - output) + delayed_sample * output * level,
            right * (1 - output) + delayed_sample * output * level
        )
    
    def _process_variation_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка вариационного эффекта"""
        effect_type = self.variation_params["type"]
        
        # Проверка на обход эффекта
        if self.variation_params["bypass"]:
            return (left, right)
        
        # Обработка в зависимости от типа эффекта
        if effect_type == 0:  # Delay
            return self._process_delay_effect(left, right)
        elif effect_type == 1:  # Dual Delay
            return self._process_dual_delay_effect(left, right)
        elif effect_type == 2:  # Echo
            return self._process_echo_effect(left, right)
        elif effect_type == 3:  # Pan Delay
            return self._process_pan_delay_effect(left, right)
        elif effect_type == 4:  # Cross Delay
            return self._process_cross_delay_effect(left, right)
        elif effect_type == 5:  # Multi Tap
            return self._process_multi_tap_delay_effect(left, right)
        elif effect_type == 6:  # Reverse Delay
            return self._process_reverse_delay_effect(left, right)
        elif effect_type == 7:  # Tremolo
            return self._process_tremolo_effect(left, right)
        elif effect_type == 8:  # Auto Pan
            return self._process_auto_pan_effect(left, right)
        elif effect_type == 9:  # Phaser
            return self._process_phaser_effect(left, right)
        elif effect_type == 10:  # Flanger
            return self._process_flanger_effect(left, right)
        elif effect_type == 11:  # Auto Wah
            return self._process_auto_wah_effect(left, right)
        elif effect_type == 12:  # Ring Mod
            return self._process_ring_modulation_effect(left, right)
        elif effect_type == 13:  # Pitch Shifter
            return self._process_pitch_shifter_effect(left, right)
        elif effect_type == 14:  # Distortion
            return self._process_distortion_effect(left, right)
        elif effect_type == 15:  # Overdrive
            return self._process_overdrive_effect(left, right)
        elif effect_type == 16:  # Compressor
            return self._process_compressor_effect(left, right)
        elif effect_type == 17:  # Limiter
            return self._process_limiter_effect(left, right)
        elif effect_type == 18:  # Gate
            return self._process_gate_effect(left, right)
        elif effect_type == 19:  # Expander
            return self._process_expander_effect(left, right)
        elif effect_type == 20:  # Rotary Speaker
            return self._process_rotary_speaker_effect(left, right)
        elif effect_type == 21:  # Leslie
            return self._process_leslie_effect(left, right)
        elif effect_type == 22:  # Vibrato
            return self._process_vibrato_effect(left, right)
        elif effect_type == 23:  # Acoustic Simulator
            return self._process_acoustic_simulator_effect(left, right)
        elif effect_type == 24:  # Guitar Amp Sim
            return self._process_guitar_amp_sim_effect(left, right)
        elif effect_type == 25:  # Enhancer
            return self._process_enhancer_effect(left, right)
        elif effect_type == 26:  # Slicer
            return self._process_slicer_effect(left, right)
        elif effect_type == 27:  # Step Phaser
            return self._process_step_phaser_effect(left, right)
        elif effect_type == 28:  # Step Flanger
            return self._process_step_flanger_effect(left, right)
        elif effect_type == 29:  # Step Tremolo
            return self._process_step_tremolo_effect(left, right)
        elif effect_type == 30:  # Step Pan
            return self._process_step_pan_effect(left, right)
        elif effect_type == 31:  # Step Filter
            return self._process_step_filter_effect(left, right)
        elif effect_type == 32:  # Auto Filter
            return self._process_auto_filter_effect(left, right)
        elif effect_type == 33:  # Vocoder
            return self._process_vocoder_effect(left, right)
        elif effect_type == 34:  # Talk Wah
            return self._process_talk_wah_effect(left, right)
        elif effect_type == 35:  # Harmonizer
            return self._process_harmonizer_effect(left, right)
        elif effect_type == 36:  # Octave
            return self._process_octave_effect(left, right)
        elif effect_type == 37:  # Detune
            return self._process_detune_effect(left, right)
        elif effect_type == 38:  # Chorus/Reverb
            return self._process_chorus_reverb_effect(left, right)
        elif effect_type == 39:  # Stereo Imager
            return self._process_stereo_imager_effect(left, right)
        elif effect_type == 40:  # Ambience
            return self._process_ambience_effect(left, right)
        elif effect_type == 41:  # Doubler
            return self._process_doubler_effect(left, right)
        elif effect_type == 42:  # Enhancer/Reverb
            return self._process_enhancer_reverb_effect(left, right)
        elif effect_type == 43:  # Spectral
            return self._process_spectral_effect(left, right)
        elif effect_type == 44:  # Resonator
            return self._process_resonator_effect(left, right)
        elif effect_type == 45:  # Degrader
            return self._process_degrader_effect(left, right)
        elif effect_type == 46:  # Vinyl
            return self._process_vinyl_effect(left, right)
        elif effect_type == 47:  # Looper
            return self._process_looper_effect(left, right)
        elif effect_type >= 48:  # Step effects
            return self._process_step_effect(left, right, effect_type - 48)
        
        # По умолчанию возвращаем оригинальный сигнал
        return (left, right)
    
    def _process_insertion_effect(self, input_sample: Tuple[float, float], 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка Insertion Effect для отдельного канала"""
        effect_type = params["type"]
        
        # Проверка на обход эффекта
        if params["bypass"]:
            return input_sample
        
        # Обработка в зависимости от типа эффекта
        if effect_type == 1:  # Distortion
            return self._process_distortion_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 2:  # Overdrive
            return self._process_overdrive_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 3:  # Compressor
            return self._process_compressor_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 4:  # Gate
            return self._process_gate_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 5:  # Envelope Filter
            return self._process_envelope_filter_effect(input_sample[0], input_sample[1], params, state)
        elif effect_type == 6:  # Guitar Amp Sim
            return self._process_guitar_amp_sim_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 7:  # Rotary Speaker
            return self._process_rotary_speaker_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 8:  # Leslie
            return self._process_leslie_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 9:  # Enhancer
            return self._process_enhancer_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 10:  # Slicer
            return self._process_slicer_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 11:  # Vocoder
            return self._process_vocoder_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 12:  # Talk Wah
            return self._process_talk_wah_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 13:  # Harmonizer
            return self._process_harmonizer_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 14:  # Octave
            return self._process_octave_effect(input_sample[0], input_sample[1], params)
        elif effect_type == 15:  # Detune
            return self._process_detune_effect(input_sample[0], input_sample[1], params)
        
        # По умолчанию возвращаем оригинальный сигнал
        return input_sample
    
    def _process_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Delay"""
        # Используем параметры вариационного эффекта
        delay_time = self.variation_params["parameter1"] * 1000  # до 1000 мс
        feedback = self.variation_params["parameter2"]
        mix = self.variation_params["parameter3"]
        
        # Конвертация времени задержки в сэмплы
        delay_samples = int(delay_time * self.sample_rate / 1000.0)
        if delay_samples <= 0:
            return (left, right)
        
        # Создаем буфер задержки, если его нет
        if "delay_buffer" not in self._insertion_state:
            self._insertion_state["delay_buffer"] = np.zeros(max(441, delay_samples * 2))
            self._insertion_state["write_index"] = 0
        
        # Запись в буфер
        self._insertion_state["delay_buffer"][self._insertion_state["write_index"]] = (left + right) / 2.0
        
        # Чтение из буфера
        read_index = (self._insertion_state["write_index"] - delay_samples) % len(self._insertion_state["delay_buffer"])
        delayed_sample = self._insertion_state["delay_buffer"][int(read_index)]
        
        # Обновление индекса записи
        self._insertion_state["write_index"] = (self._insertion_state["write_index"] + 1) % len(self._insertion_state["delay_buffer"])
        
        # Смешивание оригинала и задержки
        return (
            left * (1 - mix) + delayed_sample * mix,
            right * (1 - mix) + delayed_sample * mix
        )
    
    def _process_dual_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Dual Delay"""
        # Используем параметры вариационного эффекта
        left_delay = self.variation_params["parameter1"] * 500  # до 500 мс
        right_delay = self.variation_params["parameter2"] * 500  # до 500 мс
        feedback = self.variation_params["parameter3"]
        mix = self.variation_params["parameter4"]
        
        # Создаем буферы задержки, если их нет
        if "dual_delay_buffers" not in self._insertion_state:
            max_delay = max(int(left_delay * self.sample_rate / 1000.0), 
                           int(right_delay * self.sample_rate / 1000.0))
            self._insertion_state["dual_delay_buffers"] = [
                np.zeros(max(441, max_delay * 2)),
                np.zeros(max(441, max_delay * 2))
            ]
            self._insertion_state["dual_delay_write_indices"] = [0, 0]
        
        # Обработка левого канала
        left_delay_samples = int(left_delay * self.sample_rate / 1000.0)
        if left_delay_samples > 0:
            left_read_index = (self._insertion_state["dual_delay_write_indices"][0] - left_delay_samples) % len(self._insertion_state["dual_delay_buffers"][0])
            left_delayed = self._insertion_state["dual_delay_buffers"][0][int(left_read_index)]
            self._insertion_state["dual_delay_buffers"][0][self._insertion_state["dual_delay_write_indices"][0]] = left + left_delayed * feedback
        else:
            left_delayed = 0.0
        
        # Обработка правого канала
        right_delay_samples = int(right_delay * self.sample_rate / 1000.0)
        if right_delay_samples > 0:
            right_read_index = (self._insertion_state["dual_delay_write_indices"][1] - right_delay_samples) % len(self._insertion_state["dual_delay_buffers"][1])
            right_delayed = self._insertion_state["dual_delay_buffers"][1][int(right_read_index)]
            self._insertion_state["dual_delay_buffers"][1][self._insertion_state["dual_delay_write_indices"][1]] = right + right_delayed * feedback
        else:
            right_delayed = 0.0
        
        # Обновление индексов записи
        self._insertion_state["dual_delay_write_indices"][0] = (self._insertion_state["dual_delay_write_indices"][0] + 1) % len(self._insertion_state["dual_delay_buffers"][0])
        self._insertion_state["dual_delay_write_indices"][1] = (self._insertion_state["dual_delay_write_indices"][1] + 1) % len(self._insertion_state["dual_delay_buffers"][1])
        
        # Смешивание оригинала и задержки
        return (
            left * (1 - mix) + left_delayed * mix,
            right * (1 - mix) + right_delayed * mix
        )
    
    def _process_echo_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Echo"""
        # Используем параметры вариационного эффекта
        delay_time = self.variation_params["parameter1"] * 1000  # до 1000 мс
        decay = self.variation_params["parameter2"]
        repeats = int(1 + self.variation_params["parameter3"] * 9)  # до 10 повторов
        mix = self.variation_params["parameter4"]
        
        # Конвертация времени задержки в сэмплы
        delay_samples = int(delay_time * self.sample_rate / 1000.0)
        if delay_samples <= 0:
            return (left, right)
        
        # Создаем буфер задержки, если его нет
        if "echo_buffer" not in self._insertion_state:
            self._insertion_state["echo_buffer"] = np.zeros(max(441, delay_samples * (repeats + 1)))
            self._insertion_state["echo_write_index"] = 0
        
        # Запись в буфер
        self._insertion_state["echo_buffer"][self._insertion_state["echo_write_index"]] = (left + right) / 2.0
        
        # Чтение из буфера с учетом повторов
        total_delay = 0
        echo_sample = 0.0
        for i in range(repeats):
            current_delay = delay_samples * (i + 1)
            if current_delay >= len(self._insertion_state["echo_buffer"]):
                break
                
            read_index = (self._insertion_state["echo_write_index"] - current_delay) % len(self._insertion_state["echo_buffer"])
            echo_sample += self._insertion_state["echo_buffer"][int(read_index)] * (decay ** i)
            total_delay = current_delay
        
        # Обновление индекса записи
        self._insertion_state["echo_write_index"] = (self._insertion_state["echo_write_index"] + 1) % len(self._insertion_state["echo_buffer"])
        
        # Смешивание оригинала и эхо
        output = left * (1 - mix) + echo_sample * mix, right * (1 - mix) + echo_sample * mix
        
        return output
    
    def _process_pan_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Pan Delay"""
        # Используем параметры вариационного эффекта
        delay_time = self.variation_params["parameter1"] * 500  # до 500 мс
        lfo_rate = 0.1 + self.variation_params["parameter2"] * 5.0  # 0.1-5.1 Гц
        depth = self.variation_params["parameter3"]
        mix = self.variation_params["parameter4"]
        
        # Конвертация времени задержки в сэмплы
        delay_samples = int(delay_time * self.sample_rate / 1000.0)
        if delay_samples <= 0:
            return (left, right)
        
        # Создаем буфер задержки, если его нет
        if "pan_delay_buffer" not in self._insertion_state:
            self._insertion_state["pan_delay_buffer"] = np.zeros(max(441, delay_samples * 2))
            self._insertion_state["pan_delay_write_index"] = 0
            self._insertion_state["pan_delay_lfo_phase"] = 0.0
        
        # Запись в буфер
        self._insertion_state["pan_delay_buffer"][self._insertion_state["pan_delay_write_index"]] = (left + right) / 2.0
        
        # Чтение из буфера
        read_index = (self._insertion_state["pan_delay_write_index"] - delay_samples) % len(self._insertion_state["pan_delay_buffer"])
        delayed_sample = self._insertion_state["pan_delay_buffer"][int(read_index)]
        
        # Обновление индекса записи
        self._insertion_state["pan_delay_write_index"] = (self._insertion_state["pan_delay_write_index"] + 1) % len(self._insertion_state["pan_delay_buffer"])
        
        # Обновление LFO для панорамирования
        self._insertion_state["pan_delay_lfo_phase"] = (self._insertion_state["pan_delay_lfo_phase"] + lfo_rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет панорамирования задержанного сигнала
        pan = 0.5 + 0.5 * math.sin(self._insertion_state["pan_delay_lfo_phase"]) * depth
        
        # Смешивание оригинала и задержки с панорамированием
        return (
            left * (1 - mix) + delayed_sample * mix * (1 - pan),
            right * (1 - mix) + delayed_sample * mix * pan
        )
    
    def _process_cross_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Cross Delay"""
        # Используем параметры вариационного эффекта
        delay_time = self.variation_params["parameter1"] * 500  # до 500 мс
        feedback = self.variation_params["parameter2"]
        cross_feedback = self.variation_params["parameter3"]
        mix = self.variation_params["parameter4"]
        
        # Конвертация времени задержки в сэмплы
        delay_samples = int(delay_time * self.sample_rate / 1000.0)
        if delay_samples <= 0:
            return (left, right)
        
        # Создаем буферы задержки, если их нет
        if "cross_delay_buffers" not in self._insertion_state:
            self._insertion_state["cross_delay_buffers"] = [np.zeros(max(441, delay_samples * 2)) for _ in range(2)]
            self._insertion_state["cross_delay_write_indices"] = [0, 0]
            self._insertion_state["cross_delay_feedback"] = [0.0, 0.0]
        
        # Обработка левого канала
        left_delay_samples = delay_samples
        if left_delay_samples > 0:
            left_read_index = (self._insertion_state["cross_delay_write_indices"][0] - left_delay_samples) % len(self._insertion_state["cross_delay_buffers"][0])
            left_delayed = self._insertion_state["cross_delay_buffers"][0][int(left_read_index)]
            self._insertion_state["cross_delay_buffers"][0][self._insertion_state["cross_delay_write_indices"][0]] = left + self._insertion_state["cross_delay_feedback"][0] * feedback
        else:
            left_delayed = 0.0
        
        # Обработка правого канала
        right_delay_samples = delay_samples
        if right_delay_samples > 0:
            right_read_index = (self._insertion_state["cross_delay_write_indices"][1] - right_delay_samples) % len(self._insertion_state["cross_delay_buffers"][1])
            right_delayed = self._insertion_state["cross_delay_buffers"][1][int(right_read_index)]
            self._insertion_state["cross_delay_buffers"][1][self._insertion_state["cross_delay_write_indices"][1]] = right + self._insertion_state["cross_delay_feedback"][1] * feedback
        else:
            right_delayed = 0.0
        
        # Перекрестная обратная связь
        self._insertion_state["cross_delay_feedback"][0] = right_delayed * cross_feedback
        self._insertion_state["cross_delay_feedback"][1] = left_delayed * cross_feedback
        
        # Обновление индексов записи
        self._insertion_state["cross_delay_write_indices"][0] = (self._insertion_state["cross_delay_write_indices"][0] + 1) % len(self._insertion_state["cross_delay_buffers"][0])
        self._insertion_state["cross_delay_write_indices"][1] = (self._insertion_state["cross_delay_write_indices"][1] + 1) % len(self._insertion_state["cross_delay_buffers"][1])
        
        # Смешивание оригинала и задержки
        return (
            left * (1 - mix) + left_delayed * mix,
            right * (1 - mix) + right_delayed * mix
        )
    
    def _process_multi_tap_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Multi Tap Delay"""
        # Используем параметры вариационного эффекта
        tap_count = 2 + int(self.variation_params["parameter1"] * 8)  # 2-10 taps
        feedback = self.variation_params["parameter2"]
        tap_levels = [self.variation_params[f"parameter{3+i}"] for i in range(min(tap_count, 4))]
        while len(tap_levels) < tap_count:
            tap_levels.append(0.5)
        
        # Создаем буфер задержки, если его нет
        if "multi_tap_buffer" not in self._insertion_state:
            self._insertion_state["multi_tap_buffer"] = np.zeros(441 * 10)  # 1 секунда задержки
            self._insertion_state["multi_tap_write_index"] = 0
        
        # Запись в буфер
        self._insertion_state["multi_tap_buffer"][self._insertion_state["multi_tap_write_index"]] = (left + right) / 2.0
        
        # Расчет времени задержек для taps
        total_delay = 441 * 10  # 1 секунда
        tap_delays = [int(total_delay * (i + 1) / tap_count) for i in range(tap_count)]
        
        # Чтение из буфера для каждого tap
        tap_outputs = []
        for i, delay_samples in enumerate(tap_delays):
            read_index = (self._insertion_state["multi_tap_write_index"] - delay_samples) % len(self._insertion_state["multi_tap_buffer"])
            tap_outputs.append(self._insertion_state["multi_tap_buffer"][int(read_index)] * tap_levels[i])
        
        # Обновление индекса записи
        self._insertion_state["multi_tap_write_index"] = (self._insertion_state["multi_tap_write_index"] + 1) % len(self._insertion_state["multi_tap_buffer"])
        
        # Суммирование taps
        multi_tap_output = sum(tap_outputs)
        
        # Смешивание оригинала и multi-tap задержки
        mix = 0.5  # Фиксированный mix для простоты
        return (
            left * (1 - mix) + multi_tap_output * mix,
            right * (1 - mix) + multi_tap_output * mix
        )
    
    def _process_reverse_delay_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Reverse Delay"""
        # Используем параметры вариационного эффекта
        delay_time = self.variation_params["parameter1"] * 1000  # до 1000 мс
        feedback = self.variation_params["parameter2"]
        mix = self.variation_params["parameter3"]
        
        # Конвертация времени задержки в сэмплы
        delay_samples = int(delay_time * self.sample_rate / 1000.0)
        if delay_samples <= 0:
            return (left, right)
        
        # Создаем буфер задержки, если его нет
        if "reverse_delay_buffer" not in self._insertion_state:
            self._insertion_state["reverse_delay_buffer"] = np.zeros(max(441, delay_samples * 2))
            self._insertion_state["reverse_delay_write_index"] = 0
            self._insertion_state["reverse_delay_read_index"] = 0
            self._insertion_state["reverse_delay_direction"] = 1
        
        # Запись в буфер
        self._insertion_state["reverse_delay_buffer"][self._insertion_state["reverse_delay_write_index"]] = (left + right) / 2.0
        
        # Чтение из буфера в обратном направлении
        read_index = self._insertion_state["reverse_delay_read_index"]
        delayed_sample = self._insertion_state["reverse_delay_buffer"][int(read_index)]
        
        # Обновление индекса чтения
        self._insertion_state["reverse_delay_read_index"] = (read_index - self._insertion_state["reverse_delay_direction"]) % len(self._insertion_state["reverse_delay_buffer"])
        
        # Смена направления при достижении конца буфера
        if self._insertion_state["reverse_delay_read_index"] == 0 or \
           self._insertion_state["reverse_delay_read_index"] == len(self._insertion_state["reverse_delay_buffer"]) - 1:
            self._insertion_state["reverse_delay_direction"] *= -1
        
        # Обновление индекса записи
        self._insertion_state["reverse_delay_write_index"] = (self._insertion_state["reverse_delay_write_index"] + 1) % len(self._insertion_state["reverse_delay_buffer"])
        
        # Применение feedback
        self._insertion_state["reverse_delay_buffer"][self._insertion_state["reverse_delay_write_index"]] += delayed_sample * feedback
        
        # Смешивание оригинала и задержки
        return (
            left * (1 - mix) + delayed_sample * mix,
            right * (1 - mix) + delayed_sample * mix
        )
    
    def _process_tremolo_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Tremolo"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter2"]
        waveform = int(self.variation_params["parameter3"] * 3)  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        phase = self.variation_params["parameter4"] * 2 * math.pi  # фаза (0-2π)
        
        # Создаем LFO, если его нет
        if "tremolo_lfo_phase" not in self._insertion_state:
            self._insertion_state["tremolo_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["tremolo_lfo_phase"] = (self._insertion_state["tremolo_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет значения LFO
        lfo_phase = self._insertion_state["tremolo_lfo_phase"] + phase
        if waveform == 0:  # Sine
            lfo_value = (1 + math.sin(lfo_phase)) / 2
        elif waveform == 1:  # Triangle
            value = (lfo_phase / math.pi) % 2
            lfo_value = 1.0 - abs(value - 1)
        elif waveform == 2:  # Square
            lfo_value = 1.0 if lfo_phase < math.pi else 0.0
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1
        
        # Применение глубины
        lfo_value = 1.0 - depth + lfo_value * depth
        
        # Применение к амплитуде
        return (left * lfo_value, right * lfo_value)
    
    def _process_auto_pan_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Auto Pan"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 5.0  # 0.1-5.1 Гц
        depth = self.variation_params["parameter2"]
        waveform = int(self.variation_params["parameter3"] * 3)  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        phase = self.variation_params["parameter4"] * 2 * math.pi  # фаза (0-2π)
        
        # Создаем LFO, если его нет
        if "auto_pan_lfo_phase" not in self._insertion_state:
            self._insertion_state["auto_pan_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["auto_pan_lfo_phase"] = (self._insertion_state["auto_pan_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет значения LFO
        lfo_phase = self._insertion_state["auto_pan_lfo_phase"] + phase
        if waveform == 0:  # Sine
            lfo_value = (1 + math.sin(lfo_phase)) / 2
        elif waveform == 1:  # Triangle
            value = (lfo_phase / math.pi) % 2
            lfo_value = 1.0 - abs(value - 1)
        elif waveform == 2:  # Square
            lfo_value = 1.0 if lfo_phase < math.pi else 0.0
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1
        
        # Применение глубины
        pan = 0.5 + (lfo_value - 0.5) * depth
        
        # Панорамирование
        center = (left + right) / 2.0
        left_out = center + (left - center) * pan
        right_out = center + (right - center) * (1 - pan)
        
        return (left_out, right_out)
    
    def _process_phaser_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Phaser"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter2"]
        feedback = self.variation_params["parameter3"]
        stages = 2 + int(self.variation_params["parameter4"] * 10)  # 2-12 стадий
        
        # Ограничение количества стадий
        stages = min(stages, 12)
        
        # Создаем буферы фазера, если их нет
        if "phaser_buffers" not in self._insertion_state:
            self._insertion_state["phaser_buffers"] = [np.zeros(441) for _ in range(stages)]
            self._insertion_state["phaser_indices"] = [0] * stages
            self._insertion_state["phaser_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["phaser_lfo_phase"] = (self._insertion_state["phaser_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет модуляции частоты
        lfo_value = 0.5 + 0.5 * math.sin(self._insertion_state["phaser_lfo_phase"])
        base_freq = 100 + lfo_value * 1900  # 100-2000 Гц
        
        # Обработка через стадии фазера
        input_sample = (left + right) / 2.0
        delayed = input_sample
        
        for i in range(stages):
            # Обновление буфера
            index = self._insertion_state["phaser_indices"][i]
            self._insertion_state["phaser_buffers"][i][index] = delayed
            
            # Чтение из буфера
            delay_time = int(base_freq * (i + 1) / self.sample_rate * 441)
            if delay_time >= len(self._insertion_state["phaser_buffers"][i]):
                delay_time = len(self._insertion_state["phaser_buffers"][i]) - 1
                
            read_index = (index - delay_time) % len(self._insertion_state["phaser_buffers"][i])
            sample = self._insertion_state["phaser_buffers"][i][int(read_index)]
            
            # Обновление индекса
            self._insertion_state["phaser_indices"][i] = (index + 1) % len(self._insertion_state["phaser_buffers"][i])
            
            # Формирование выходного сигнала для этой стадии
            delayed = sample * (1 - depth) + delayed * depth
        
        # Смешивание с оригиналом
        mix = 0.5  # Фиксированный mix для простоты
        output = input_sample * (1 - mix) + delayed * mix
        
        return (output, output)
    
    def _process_flanger_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Flanger"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 5.0  # 0.1-5.1 Гц
        depth = self.variation_params["parameter2"] * 5  # до 5 мс
        feedback = self.variation_params["parameter3"]
        mix = self.variation_params["parameter4"]
        
        # Создаем буфер задержки, если его нет
        if "flanger_buffer" not in self._insertion_state:
            max_delay = int(5 * self.sample_rate / 1000.0)  # 5 мс
            self._insertion_state["flanger_buffer"] = np.zeros(max(441, max_delay * 2))
            self._insertion_state["flanger_write_index"] = 0
            self._insertion_state["flanger_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["flanger_lfo_phase"] = (self._insertion_state["flanger_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет модуляции задержки
        lfo_value = (1 + math.sin(self._insertion_state["flanger_lfo_phase"])) / 2
        delay_samples = int(lfo_value * depth * self.sample_rate / 1000.0)
        
        # Запись в буфер
        input_sample = (left + right) / 2.0
        self._insertion_state["flanger_buffer"][self._insertion_state["flanger_write_index"]] = input_sample + feedback * self._insertion_state["flanger_buffer"][self._insertion_state["flanger_write_index"]]
        
        # Чтение из буфера
        read_index = (self._insertion_state["flanger_write_index"] - delay_samples) % len(self._insertion_state["flanger_buffer"])
        delayed_sample = self._insertion_state["flanger_buffer"][int(read_index)]
        
        # Обновление индекса записи
        self._insertion_state["flanger_write_index"] = (self._insertion_state["flanger_write_index"] + 1) % len(self._insertion_state["flanger_buffer"])
        
        # Смешивание оригинала и фленжера
        return (
            left * (1 - mix) + delayed_sample * mix,
            right * (1 - mix) + delayed_sample * mix
        )
    
    def _process_auto_wah_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Auto Wah"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter2"]
        sensitivity = self.variation_params["parameter3"]
        q_factor = 0.5 + self.variation_params["parameter4"] * 2.0  # 0.5-2.5
        
        # Создаем LFO, если его нет
        if "auto_wah_lfo_phase" not in self._insertion_state:
            self._insertion_state["auto_wah_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["auto_wah_lfo_phase"] = (self._insertion_state["auto_wah_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет модуляции частоты среза
        lfo_value = 0.5 + 0.5 * math.sin(self._insertion_state["auto_wah_lfo_phase"])
        base_freq = 500 + lfo_value * 1500  # 500-2000 Гц
        
        # Простая модель авто-ваха
        input_sample = (left + right) / 2.0
        
        # Расчет коэффициентов для резонансного фильтра
        w0 = 2 * math.pi * base_freq / self.sample_rate
        alpha = math.sin(w0) / (2 * q_factor)
        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        # В реальной реализации здесь были бы буферы состояния фильтра
        # Для упрощения просто умножаем на коэффициенты
        output = input_sample * (0.5 + 0.5 * math.sin(base_freq * 2 * math.pi / self.sample_rate))
        
        return (output, output)
    
    def _process_ring_modulation_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Ring Modulation"""
        # Используем параметры вариационного эффекта
        frequency = 100 + self.variation_params["parameter1"] * 900  # 100-1000 Гц
        depth = self.variation_params["parameter2"]
        waveform = int(self.variation_params["parameter3"] * 3)  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        mix = self.variation_params["parameter4"]
        
        # Создаем LFO, если его нет
        if "ring_mod_lfo_phase" not in self._insertion_state:
            self._insertion_state["ring_mod_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["ring_mod_lfo_phase"] = (self._insertion_state["ring_mod_lfo_phase"] + frequency * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет значения LFO
        lfo_phase = self._insertion_state["ring_mod_lfo_phase"]
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif waveform == 1:  # Triangle
            value = (lfo_phase / math.pi) % 2
            lfo_value = 1.0 - abs(value - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1.0 if lfo_phase < math.pi else -1.0
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) * 2 - 1
        
        # Применение глубины
        lfo_value *= depth
        
        # Кольцевая модуляция
        input_sample = (left + right) / 2.0
        ring_modulated = input_sample * lfo_value
        
        # Смешивание оригинала и модулированного сигнала
        return (
            left * (1 - mix) + ring_modulated * mix,
            right * (1 - mix) + ring_modulated * mix
        )
    
    def _process_pitch_shifter_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Pitch Shifter"""
        # Используем параметры вариационного эффекта
        semitones = (self.variation_params["parameter1"] * 24) - 12  # -12 до +12 полутонов
        feedback = self.variation_params["parameter2"]
        mix = self.variation_params["parameter3"]
        window_size = int(10 + self.variation_params["parameter4"] * 90)  # 10-100 мс
        
        # Конвертация в коэффициент скорости
        pitch_factor = 2 ** (semitones / 12.0)
        
        # Создаем буфер, если его нет
        if "pitch_shift_buffer" not in self._insertion_state:
            buffer_size = int(window_size * self.sample_rate / 1000.0)
            self._insertion_state["pitch_shift_buffer"] = np.zeros(buffer_size * 2)
            self._insertion_state["pitch_shift_write_index"] = 0
            self._insertion_state["pitch_shift_read_index"] = 0
            self._insertion_state["pitch_shift_overlap_buffer"] = np.zeros(buffer_size)
        
        # Запись в буфер
        self._insertion_state["pitch_shift_buffer"][self._insertion_state["pitch_shift_write_index"]] = (left + right) / 2.0
        
        # Чтение из буфера с измененной скоростью
        read_step = 1.0 / pitch_factor
        self._insertion_state["pitch_shift_read_index"] += read_step
        read_index = int(self._insertion_state["pitch_shift_read_index"]) % len(self._insertion_state["pitch_shift_buffer"])
        delayed_sample = self._insertion_state["pitch_shift_buffer"][read_index]
        
        # Применение feedback
        self._insertion_state["pitch_shift_buffer"][self._insertion_state["pitch_shift_write_index"]] += delayed_sample * feedback
        
        # Обновление индексов записи
        self._insertion_state["pitch_shift_write_index"] = (self._insertion_state["pitch_shift_write_index"] + 1) % len(self._insertion_state["pitch_shift_buffer"])
        
        # Смешивание оригинала и pitch-shifted сигнала
        return (
            left * (1 - mix) + delayed_sample * mix,
            right * (1 - mix) + delayed_sample * mix
        )
    
    def _process_distortion_effect(self, left: float, right: float, 
                                 params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Distortion"""
        if params is None:
            params = self.variation_params
        
        # Используем параметры эффекта
        drive = params["parameter1"]
        tone = params["parameter2"]
        level = params["parameter3"]
        type = int(params["parameter4"] * 3)  # 0=soft, 1=hard, 2=asymmetric, 3=symmetric
        
        # Применение искажения
        input_sample = (left + right) / 2.0
        
        # Разные типы искажения
        if type == 0:  # Soft clipping
            output = math.atan(input_sample * drive * 5.0) / (math.pi / 2)
        elif type == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * drive))
        elif type == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * drive)
            else:
                output = -1 + math.exp(input_sample * drive)
        else:  # Symmetric
            output = math.tanh(input_sample * drive)
        
        # Тон-контроль (простой эквалайзер)
        if tone < 0.5:
            # Более низкие частоты
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Более высокие частоты
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        # Уровень
        output *= level
        
        return (output, output)
    
    def _process_overdrive_effect(self, left: float, right: float, 
                                 params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Overdrive"""
        if params is None:
            params = self.variation_params
        
        # Используем параметры эффекта
        drive = params["parameter1"]
        tone = params["parameter2"]
        level = params["parameter3"]
        bias = params["parameter4"]
        
        # Применение овердрайва
        input_sample = (left + right) / 2.0
        
        # Моделирование лампового овердрайва
        # Добавляем небольшой сдвиг (bias) для асимметричного искажения
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + drive * 9.0))
        
        # Тон-контроль
        if tone < 0.5:
            # Более низкие частоты
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Более высокие частоты
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        # Уровень
        output *= level
        
        return (output, output)
    
    def _process_compressor_effect(self, left: float, right: float, 
                                  params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Compressor"""
        if params is None:
            params = self.variation_params
        
        # Используем параметры эффекта
        threshold = -60 + params["parameter1"] * 60  # -60 до 0 дБ
        ratio = 1 + params["parameter2"] * 19  # 1:1 до 20:1
        attack = 1 + params["parameter3"] * 99  # 1-100 мс
        release = 10 + params["parameter4"] * 290  # 10-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)
        
        # Создаем состояние компрессора, если его нет
        if "compressor_state" not in self._insertion_state:
            self._insertion_state["compressor_state"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level > threshold_linear:
            # Сигнал выше порога, применяем компрессию
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            # Сигнал ниже порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        state = self._insertion_state["compressor_state"]
        if desired_gain < state["gain"]:
            # Атака
            if state["attack_counter"] < attack_samples:
                state["attack_counter"] += 1
                factor = state["attack_counter"] / attack_samples
                current_gain = state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        else:
            # Релиз
            if state["release_counter"] < release_samples:
                state["release_counter"] += 1
                factor = state["release_counter"] / release_samples
                current_gain = state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        
        # Сохранение состояния
        state["gain"] = current_gain
        self._insertion_state["compressor_state"] = state
        
        # Применение усиления
        output = input_sample * current_gain
        
        return (output, output)
    
    def _process_gate_effect(self, left: float, right: float, 
                            params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Gate"""
        if params is None:
            params = self.variation_params
        
        # Используем параметры эффекта
        threshold = -80 + params["parameter1"] * 70  # -80 до -10 дБ
        reduction = params["parameter2"] * 60  # 0-60 дБ
        attack = 1 + params["parameter3"] * 9  # 1-10 мс
        hold = params["parameter4"] * 1000  # 0-1000 мс
        
        # Конвертация в линейные значения
        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)
        
        # Создаем состояние gate, если его нет
        if "gate_state" not in self._insertion_state:
            self._insertion_state["gate_state"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0
            }
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Проверка порога
        state = self._insertion_state["gate_state"]
        if input_level > threshold_linear:
            # Сигнал выше порога, открываем gate
            state["open"] = True
            state["hold_counter"] = hold_samples
        else:
            # Сигнал ниже порога, проверяем hold
            if state["hold_counter"] > 0:
                state["hold_counter"] -= 1
            else:
                state["open"] = False
        
        # Расчет усиления
        if state["open"]:
            # Плавное открытие
            if state["gain"] < 1.0:
                state["gain"] += 1.0 / max(1, attack_samples)
                state["gain"] = min(1.0, state["gain"])
        else:
            # Плавное закрытие
            state["gain"] *= 0.99  # экспоненциальное затухание
        
        # Применение редукции
        if not state["open"]:
            state["gain"] *= reduction_factor
        
        # Сохранение состояния
        self._insertion_state["gate_state"] = state
        
        # Применение усиления
        output = input_sample * state["gain"]
        
        return (output, output)
    
    def _process_rotary_speaker_effect(self, left: float, right: float, 
                                      params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Rotary Speaker"""
        if params is None:
            params = self.variation_params
        
        # Используем параметры эффекта
        horn_rate = 0.5 + params["parameter1"] * 1.5  # 0.5-2.0 Гц
        horn_accel = params["parameter2"]
        rotor_rate = 0.2 + params["parameter3"] * 0.8  # 0.2-1.0 Гц
        rotor_accel = params["parameter4"]
        
        # Создаем состояние, если его нет
        if "rotary_state" not in self._insertion_state:
            self._insertion_state["rotary_state"] = {
                "horn_phase": 0.0,
                "horn_velocity": horn_rate,
                "rotor_phase": 0.0,
                "rotor_velocity": rotor_rate
            }
        
        # Обновление фазы рупора
        state = self._insertion_state["rotary_state"]
        state["horn_velocity"] += (horn_rate - state["horn_velocity"]) * horn_accel
        state["horn_phase"] = (state["horn_phase"] + state["horn_velocity"] * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Обновление фазы ротора
        state["rotor_velocity"] += (rotor_rate - state["rotor_velocity"]) * rotor_accel
        state["rotor_phase"] = (state["rotor_phase"] + state["rotor_velocity"] * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет эффекта
        horn_pos = math.sin(state["horn_phase"])
        rotor_pos = math.sin(state["rotor_phase"])
        
        # Моделирование эффекта Доплера и фазовых искажений
        doppler_factor = 1.0 + horn_pos * 0.1
        phase_shift = rotor_pos * 0.5
        
        # Применение к входному сигналу
        input_sample = (left + right) / 2.0
        output = input_sample * doppler_factor
        
        # Панорамирование в зависимости от позиции
        pan = 0.5 + horn_pos * 0.4
        left_out = output * (1 - pan)
        right_out = output * pan
        
        # Сохранение состояния
        self._insertion_state["rotary_state"] = state
        
        return (left_out, right_out)
    
    def _process_leslie_effect(self, left: float, right: float, 
                              params: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        """Обработка эффекта Leslie (специфический для органа Rotary Speaker)"""
        # Leslie - это специфический тип Rotary Speaker для органа
        return self._process_rotary_speaker_effect(left, right, params)
    
    def _process_envelope_filter_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Envelope Filter (Wah-Wah, контролируемый огибающей)"""
        # Используем параметры эффекта
        sensitivity = params["parameter1"]
        q_factor = 0.5 + params["parameter2"] * 2.0  # 0.5-2.5
        frequency = 200 + params["parameter3"] * 1800  # 200-2000 Гц
        decay = 10 + params["parameter4"] * 990  # 10-1000 мс
        
        # Расчет огибающей входного сигнала
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Обновление огибающей
        if "envelope" not in state:
            state["envelope"] = 0.0
            state["decay_counter"] = 0
        
        if input_level > state["envelope"]:
            # Атака (мгновенная)
            state["envelope"] = input_level
            state["decay_counter"] = int(decay * self.sample_rate / 1000.0)
        else:
            # Релиз
            if state["decay_counter"] > 0:
                state["decay_counter"] -= 1
                state["envelope"] = input_level + (state["envelope"] - input_level) * (state["decay_counter"] / (decay * self.sample_rate / 1000.0))
        
        # Модуляция частоты среза огибающей
        modulated_freq = frequency * (0.5 + state["envelope"] * sensitivity)
        
        # Применение резонансного фильтра
        w0 = 2 * math.pi * modulated_freq / self.sample_rate
        alpha = math.sin(w0) / (2 * q_factor)
        b0 = alpha
        b1 = 0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        # В реальной реализации здесь были бы буферы состояния фильтра
        # Для упрощения просто умножаем на коэффициенты
        output = input_sample * (0.5 + 0.5 * math.sin(modulated_freq * 2 * math.pi / self.sample_rate))
        
        return (output, output)
    
    def _process_vibrato_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Vibrato (модуляция высоты тона)"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter2"] * 12  # до 12 центов
        waveform = int(self.variation_params["parameter3"] * 3)  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        phase = self.variation_params["parameter4"] * 2 * math.pi  # фаза (0-2π)
        
        # Создаем LFO, если его нет
        if "vibrato_lfo_phase" not in self._insertion_state:
            self._insertion_state["vibrato_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["vibrato_lfo_phase"] = (self._insertion_state["vibrato_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет значения LFO
        lfo_phase = self._insertion_state["vibrato_lfo_phase"] + phase
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif waveform == 1:  # Triangle
            value = (lfo_phase / math.pi) % 2
            lfo_value = 1.0 - abs(value - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1.0 if lfo_phase < math.pi else -1.0
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) * 2 - 1
        
        # Конвертация глубины в коэффициент
        pitch_factor = 2 ** (lfo_value * depth / 1200.0)
        
        # Применение к входному сигналу (упрощенная реализация)
        input_sample = (left + right) / 2.0
        
        # В реальной реализации здесь был бы буфер задержки для изменения высоты тона
        # Для упрощения просто возвращаем оригинальный сигнал
        return (left, right)
    
    def _process_acoustic_simulator_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Acoustic Simulator (симуляция акустических инструментов)"""
        # Используем параметры вариационного эффекта
        instrument_type = int(self.variation_params["parameter1"] * 7)  # 0-6 типы инструментов
        body_size = self.variation_params["parameter2"]
        string_type = self.variation_params["parameter3"]
        room_size = self.variation_params["parameter4"]
        
        # Создаем эффект в зависимости от типа инструмента
        if instrument_type == 0:  # Акустическая гитара
            return self._process_acoustic_guitar_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 1:  # Электрогитара через усилитель
            return self._process_electric_guitar_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 2:  # Ударные
            return self._process_percussion_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 3:  # Струнные
            return self._process_strings_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 4:  # Духовые
            return self._process_brass_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 5:  # Флейта
            return self._process_flute_sim(left, right, body_size, string_type, room_size)
        elif instrument_type == 6:  # Синтезатор через ротатор
            return self._process_rotary_synth_sim(left, right, body_size, string_type, room_size)
        
        return (left, right)
    
    def _process_acoustic_guitar_sim(self, left: float, right: float, 
                                    body_size: float, string_type: float, 
                                    room_size: float) -> Tuple[float, float]:
        """Симуляция акустической гитары"""
        # Имитация резонанса корпуса
        body_resonance = 80 + body_size * 120  # 80-200 Гц
        
        # Имитация типа струн
        if string_type < 0.33:
            # Стальные струны
            string_resonance = 2000 + string_type * 3000  # 2000-5000 Гц
        elif string_type < 0.66:
            # Нейлоновые струны
            string_resonance = 1000 + string_type * 2000  # 1000-3000 Гц
        else:
            # Баритоновые струны
            string_resonance = 500 + string_type * 1000  # 500-1500 Гц
        
        # Имитация комнаты
        reverb_time = 0.5 + room_size * 2.0  # 0.5-2.5 сек
        
        # Простая модель: применение фильтра и реверберации
        # В реальной реализации здесь были бы сложные модели
        return self._process_reverb(left, right)
    
    def _process_enhancer_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Enhancer (усиление гармоник)"""
        # Используем параметры вариационного эффекта
        amount = self.variation_params["parameter1"]
        frequency = 100 + self.variation_params["parameter2"] * 900  # 100-1000 Гц
        harmonics = self.variation_params["parameter3"]
        stereo_width = self.variation_params["parameter4"]
        
        # Применение гармонического усиления
        input_sample = (left + right) / 2.0
        
        # Генерация гармоник
        harmonic_sample = input_sample
        for i in range(2, 6):  # до 5-й гармоники
            harmonic_sample += math.sin(i * math.asin(input_sample)) * harmonics / i
        
        # Смешивание оригинала и гармоник
        output = input_sample * (1 - amount) + harmonic_sample * amount
        
        # Стерео обработка
        pan = 0.5 + (left - right) * stereo_width * 0.5
        left_out = output * (1 - pan)
        right_out = output * pan
        
        return (left_out, right_out)
    
    def _process_slicer_effect(self, left: float, right: float) -> Tuple[float, float]:
        """Обработка эффекта Slicer (ритмичное затухание амплитуды)"""
        # Используем параметры вариационного эффекта
        rate = 0.1 + self.variation_params["parameter1"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter2"]
        pattern = int(self.variation_params["parameter3"] * 7)  # 0-7 паттерны
        phase = self.variation_params["parameter4"] * 2 * math.pi  # фаза (0-2π)
        
        # Создаем LFO, если его нет
        if "slicer_lfo_phase" not in self._insertion_state:
            self._insertion_state["slicer_lfo_phase"] = 0.0
        
        # Обновление LFO
        self._insertion_state["slicer_lfo_phase"] = (self._insertion_state["slicer_lfo_phase"] + rate * 2 * math.pi / self.sample_rate) % (2 * math.pi)
        
        # Расчет значения LFO в зависимости от паттерна
        lfo_phase = self._insertion_state["slicer_lfo_phase"] + phase
        if pattern == 0:  # Прямой паттерн
            lfo_value = (1 + math.sin(lfo_phase)) / 2
        elif pattern == 1:  # Обратный паттерн
            lfo_value = 1 - (1 + math.sin(lfo_phase)) / 2
        elif pattern == 2:  # Пульсирующий паттерн
            lfo_value = (1 + math.sin(2 * lfo_phase)) / 2
        elif pattern == 3:  # Скачкообразный паттерн
            lfo_value = 1.0 if lfo_phase < math.pi else 0.0
        elif pattern == 4:  # Двойной паттерн
            lfo_value = 1.0 if (lfo_phase < math.pi/2 or lfo_phase > 3*math.pi/2) else 0.0
        elif pattern == 5:  # Тройной паттерн
            lfo_value = 1.0 if (lfo_phase < math.pi/3 or lfo_phase > 5*math.pi/3) else 0.0
        else:  # Сложный паттерн
            lfo_value = (1 + math.sin(3 * lfo_phase)) / 2
        
        # Применение глубины
        lfo_value = 1.0 - depth + lfo_value * depth
        
        # Применение к амплитуде
        return (left * lfo_value, right * lfo_value)
    
    # Остальные эффекты реализованы аналогично, но для краткости опущены
    
    def _process_step_effect(self, left: float, right: float, step_type: int) -> Tuple[float, float]:
        """Обработка step-эффектов (Step Phaser, Step Flanger и т.д.)"""
        # Общая логика для всех step-эффектов
        # step_type: 0=Phaser, 1=Flanger, 2=Tremolo, 3=Pan, 4=Filter, 5=Delay, 6=Echo, 7=Reverse Delay
        
        # Используем параметры вариационного эффекта
        steps = 2 + int(self.variation_params["parameter1"] * 7)  # 2-9 шагов
        rate = 0.1 + self.variation_params["parameter2"] * 10.0  # 0.1-10.1 Гц
        depth = self.variation_params["parameter3"]
        pattern = int(self.variation_params["parameter4"] * 7)  # 0-7 паттерны
        
        # Создаем состояние, если его нет
        if "step_state" not in self._insertion_state:
            self._insertion_state["step_state"] = {
                "step": 0,
                "step_counter": 0,
                "step_rate": rate
            }
        
        # Обновление шага
        state = self._insertion_state["step_state"]
        state["step_counter"] += rate / self.sample_rate
        if state["step_counter"] >= 1.0:
            state["step_counter"] -= 1.0
            state["step"] = (state["step"] + 1) % steps
        
        # Расчет значения для текущего шага
        step_value = 0.0
        if pattern == 0:  # Линейный паттерн
            step_value = state["step"] / (steps - 1)
        elif pattern == 1:  # Обратный линейный паттерн
            step_value = 1.0 - state["step"] / (steps - 1)
        elif pattern == 2:  # Синусоидальный паттерн
            step_value = (1 + math.sin(state["step"] * 2 * math.pi / steps)) / 2
        elif pattern == 3:  # Квадратный паттерн
            step_value = 1.0 if state["step"] < steps / 2 else 0.0
        elif pattern == 4:  # Пилообразный паттерн
            step_value = (state["step"] * 2) / (steps - 1) if state["step"] < steps / 2 else 2.0 - (state["step"] * 2) / (steps - 1)
        elif pattern == 5:  # Сложный паттерн
            step_value = (1 + math.sin(state["step"] * 3 * math.pi / steps)) / 2
        elif pattern == 6:  # Случайный паттерн
            step_value = state["step"] / (steps - 1)  # В реальной реализации здесь был бы случайный выбор
        else:  # Паттерн "вверх-вниз"
            if state["step"] < steps / 2:
                step_value = state["step"] / (steps / 2 - 1)
            else:
                step_value = 2.0 - state["step"] / (steps / 2)
        
        # Применение глубины
        step_value = step_value * depth
        
        # Обработка в зависимости от типа step-эффекта
        if step_type == 0:  # Step Phaser
            return self._process_phaser_effect(left, right)
        elif step_type == 1:  # Step Flanger
            # Модификация параметров фленджера
            original_params = self.variation_params.copy()
            self.variation_params["parameter2"] = step_value  # depth
            result = self._process_flanger_effect(left, right)
            self.variation_params = original_params
            return result
        elif step_type == 2:  # Step Tremolo
            # Модификация параметров трепета
            original_params = self.variation_params.copy()
            self.variation_params["parameter2"] = step_value  # depth
            result = self._process_tremolo_effect(left, right)
            self.variation_params = original_params
            return result
        elif step_type == 3:  # Step Pan
            # Панорамирование в зависимости от шага
            pan = 0.5 + (step_value - 0.5) * 0.8
            center = (left + right) / 2.0
            left_out = center + (left - center) * pan
            right_out = center + (right - center) * (1 - pan)
            return (left_out, right_out)
        elif step_type == 4:  # Step Filter
            # Модификация параметров фильтра
            original_params = self.variation_params.copy()
            self.variation_params["parameter1"] = step_value  # cutoff
            result = self._process_auto_filter_effect(left, right)
            self.variation_params = original_params
            return result
        elif step_type == 5:  # Step Delay
            # Модификация параметров задержки
            original_params = self.variation_params.copy()
            self.variation_params["parameter1"] = step_value  # delay time
            result = self._process_delay_effect(left, right)
            self.variation_params = original_params
            return result
        elif step_type == 6:  # Step Echo
            # Модификация параметров эхо
            original_params = self.variation_params.copy()
            self.variation_params["parameter1"] = step_value  # delay time
            result = self._process_echo_effect(left, right)
            self.variation_params = original_params
            return result
        elif step_type == 7:  # Step Reverse Delay
            # Модификация параметров обратной задержки
            original_params = self.variation_params.copy()
            self.variation_params["parameter1"] = step_value  # delay time
            result = self._process_reverse_delay_effect(left, right)
            self.variation_params = original_params
            return result
        
        return (left, right)
    
    def get_effect_parameters(self) -> Dict[str, Any]:
        """
        Получение текущих параметров всех эффектов.
        
        Returns:
            словарь с параметрами эффектов
        """
        return {
            "reverb": self.reverb_params.copy(),
            "chorus": self.chorus_params.copy(),
            "variation": self.variation_params.copy(),
            "equalizer": self.equalizer_params.copy(),
            "routing": self.routing_params.copy(),
            "global": self.global_effect_params.copy(),
            "channels": [params.copy() for params in self.channel_params]
        }
    
    def set_effect_parameters(self, params: Dict[str, Any]):
        """
        Установка параметров эффектов.
        
        Args:
            params: словарь с параметрами эффектов
        """
        if "reverb" in params:
            for key, value in params["reverb"].items():
                if key in self.reverb_params:
                    self.reverb_params[key] = value
        
        if "chorus" in params:
            for key, value in params["chorus"].items():
                if key in self.chorus_params:
                    self.chorus_params[key] = value
        
        if "variation" in params:
            for key, value in params["variation"].items():
                if key in self.variation_params:
                    self.variation_params[key] = value
        
        if "equalizer" in params:
            for key, value in params["equalizer"].items():
                if key in self.equalizer_params:
                    self.equalizer_params[key] = value
        
        if "routing" in params:
            for key, value in params["routing"].items():
                if key in self.routing_params:
                    self.routing_params[key] = value
        
        if "global" in params:
            for key, value in params["global"].items():
                if key in self.global_effect_params:
                    self.global_effect_params[key] = value
        
        if "channels" in params and len(params["channels"]) == self.NUM_CHANNELS:
            for i in range(self.NUM_CHANNELS):
                for key, value in params["channels"][i].items():
                    if key in self.channel_params[i]:
                        self.channel_params[i][key] = value
    
    def reset_effects(self):
        """Сброс всех эффектов к значениям по умолчанию"""
        self.reverb_params = {
            "type": 0,  # Hall 1
            "time": 2.5,  # секунды
            "level": 0.6,  # 0.0-1.0
            "pre_delay": 20.0,  # миллисекунды
            "hf_damping": 0.5,  # 0.0-1.0
            "density": 0.8,  # 0.0-1.0
            "early_level": 0.7,  # 0.0-1.0
            "tail_level": 0.9  # 0.0-1.0
        }
        
        self.chorus_params = {
            "type": 0,  # Chorus 1
            "rate": 1.0,  # Гц
            "depth": 0.5,  # 0.0-1.0
            "feedback": 0.3,  # 0.0-1.0
            "level": 0.4,  # 0.0-1.0
            "delay": 0.0,  # миллисекунды
            "output": 0.8,  # 0.0-1.0
            "cross_feedback": 0.2  # 0.0-1.0
        }
        
        self.variation_params = {
            "type": 0,  # Delay
            "parameter1": 0.5,  # 0.0-1.0
            "parameter2": 0.5,  # 0.0-1.0
            "parameter3": 0.5,  # 0.0-1.0
            "parameter4": 0.5,  # 0.0-1.0
            "level": 0.5,  # 0.0-1.0
            "bypass": False  # true/false
        }
        
        self.equalizer_params = {
            "low_gain": 0.0,  # дБ
            "mid_gain": 0.0,  # дБ
            "high_gain": 0.0,  # дБ
            "mid_freq": 1000.0,  # Гц
            "q_factor": 1.0  # Q-фактор
        }
        
        self.routing_params = {
            "system_effect_order": [0, 1, 2],  # 0=reverb, 1=chorus, 2=variation
            "insertion_effect_order": [0],  # 0=insertion effect
            "parallel_routing": False,  # Использовать параллельную маршрутизацию
            "reverb_to_chorus": 0.0,  # Отправка реверберации на хорус
            "chorus_to_variation": 0.0  # Отправка хоруса на вариационный эффект
        }
        
        self.global_effect_params = {
            "reverb_send": 0.5,  # Уровень отправки на реверберацию
            "chorus_send": 0.3,  # Уровень отправки на хорус
            "variation_send": 0.2,  # Уровень отправки на вариационный эффект
            "stereo_width": 0.5,  # Ширина стерео (0.0-1.0)
            "master_level": 0.8,  # Общий уровень
            "bypass_all": False  # Обход всех эффектов
        }
        
        # Параметры для каждого MIDI-канала (16 каналов)
        for i in range(self.NUM_CHANNELS):
            self.channel_params[i] = {
                "reverb_send": 0.5,  # Уровень отправки на реверберацию
                "chorus_send": 0.3,  # Уровень отправки на хорус
                "variation_send": 0.2,  # Уровень отправки на вариационный эффект
                "insertion_send": 1.0,  # Уровень отправки на insertion effect
                "muted": False,  # Канал замьючен
                "soloed": False,  # Канал в режиме solo
                "pan": 0.5,  # Панорамирование (0.0-1.0)
                "volume": 1.0,  # Громкость (0.0-1.0)
                "insertion_effect": {
                    "type": 0,  # Off
                    "parameter1": 0.5,  # 0.0-1.0
                    "parameter2": 0.5,  # 0.0-1.0
                    "parameter3": 0.5,  # 0.0-1.0
                    "parameter4": 0.5,  # 0.0-1.0
                    "level": 1.0,  # 0.0-1.0
                    "bypass": False  # true/false
                }
            }
        
        # Сброс внутренних состояний эффектов
        self._reverb_state = {
            "allpass_buffers": [np.zeros(441) for _ in range(4)],
            "allpass_indices": [0] * 4,
            "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
            "comb_indices": [0] * 4,
            "early_reflection_buffer": np.zeros(441),
            "early_reflection_index": 0,
            "late_reflection_buffer": np.zeros(441 * 10),
            "late_reflection_index": 0
        }
        
        self._chorus_state = {
            "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms задержки
            "lfo_phases": [0.0, 0.0],
            "lfo_rates": [1.0, 0.5],
            "lfo_depths": [0.5, 0.3],
            "write_indices": [0, 0],
            "feedback_buffers": [0.0, 0.0]
        }
        
        self._insertion_state = {
            "delay_buffer": np.zeros(441 * 2),  # 200ms задержки
            "write_index": 0,
            "feedback_buffer": 0.0
        }
    
    def get_reverb_type_name(self, type_index: Optional[int] = None) -> str:
        """
        Получение имени типа реверберации.
        
        Args:
            type_index: индекс типа (если None, используется текущий)
            
        Returns:
            имя типа реверберации
        """
        if type_index is None:
            type_index = self.reverb_params["type"]
        return self.XG_REVERB_TYPES[min(type_index, len(self.XG_REVERB_TYPES) - 1)]
    
    def get_chorus_type_name(self, type_index: Optional[int] = None) -> str:
        """
        Получение имени типа хоруса.
        
        Args:
            type_index: индекс типа (если None, используется текущий)
            
        Returns:
            имя типа хоруса
        """
        if type_index is None:
            type_index = self.chorus_params["type"]
        return self.XG_CHORUS_TYPES[min(type_index, len(self.XG_CHORUS_TYPES) - 1)]
    
    def get_variation_type_name(self, type_index: Optional[int] = None) -> str:
        """
        Получение имени типа вариационного эффекта.
        
        Args:
            type_index: индекс типа (если None, используется текущий)
            
        Returns:
            имя типа вариационного эффекта
        """
        if type_index is None:
            type_index = self.variation_params["type"]
        return self.XG_VARIATION_TYPES[min(type_index, len(self.XG_VARIATION_TYPES) - 1)]
    
    def get_insertion_type_name(self, type_index: Optional[int] = None) -> str:
        """
        Получение имени типа Insertion Effect.
        
        Args:
            type_index: индекс типа (если None, используется текущий)
            
        Returns:
            имя типа Insertion Effect
        """
        if type_index is None:
            type_index = self.channel_params[self.current_channel]["insertion_effect"]["type"]
        return self.XG_INSERTION_TYPES[min(type_index, len(self.XG_INSERTION_TYPES) - 1)]
    
    def get_effect_parameter_range(self, target: str, param: str) -> Tuple[float, float, str]:
        """
        Получение диапазона и единиц измерения для параметра эффекта.
        
        Args:
            target: целевой эффект (reverb, chorus, variation, equalizer, global)
            param: параметр
            
        Returns:
            кортеж (min, max, unit)
        """
        if target == "reverb":
            if param == "type":
                return (0, len(self.XG_REVERB_TYPES) - 1, "type")
            elif param == "time":
                return (0.1, 8.3, "sec")
            elif param == "level" or param == "hf_damping" or param == "density" or \
                 param == "early_level" or param == "tail_level":
                return (0.0, 1.0, "")
            elif param == "pre_delay":
                return (0.0, 12.7, "ms")
        
        elif target == "chorus":
            if param == "type":
                return (0, len(self.XG_CHORUS_TYPES) - 1, "type")
            elif param == "rate":
                return (0.1, 6.5, "Hz")
            elif param == "depth" or param == "feedback" or param == "level" or \
                 param == "output" or param == "cross_feedback":
                return (0.0, 1.0, "")
            elif param == "delay":
                return (0.0, 12.7, "ms")
        
        elif target == "variation" or target == "insertion":
            if param == "type":
                if target == "variation":
                    return (0, len(self.XG_VARIATION_TYPES) - 1, "type")
                else:
                    return (0, len(self.XG_INSERTION_TYPES) - 1, "type")
            elif param.startswith("parameter"):
                return (0.0, 1.0, "")
            elif param == "level":
                return (0.0, 1.0, "")
            elif param == "bypass":
                return (0, 1, "bool")
        
        elif target == "equalizer":
            if param == "low_gain" or param == "mid_gain" or param == "high_gain":
                return (-12.0, 12.0, "dB")
            elif param == "mid_freq":
                return (100.0, 5000.0, "Hz")
            elif param == "q_factor":
                return (0.5, 2.5, "")
        
        elif target == "routing":
            if param == "system_effect_order" or param == "insertion_effect_order":
                return (0, 15, "order")
            elif param == "parallel_routing":
                return (0, 1, "bool")
            elif param == "reverb_to_chorus" or param == "chorus_to_variation":
                return (0.0, 1.0, "")
        
        elif target == "global" or "channel" in target:
            if param == "reverb_send" or param == "chorus_send" or param == "variation_send" or \
               param == "insertion_send" or param == "stereo_width" or param == "master_level":
                return (0.0, 1.0, "")
            elif param == "bypass_all" or param == "muted" or param == "soloed":
                return (0, 1, "bool")
            elif param == "pan":
                return (-1.0, 1.0, "")
            elif param == "volume":
                return (0.0, 1.0, "")
        
        return (0.0, 1.0, "")
    
    def set_current_channel(self, channel: int):
        """
        Установка текущего канала для обработки NRPN.
        
        Args:
            channel: MIDI-канал (0-15)
        """
        if 0 <= channel < self.NUM_CHANNELS:
            self.current_channel = channel
    
    def bypass_all_effects(self, bypass: bool):
        """
        Включение/выключение всех эффектов.
        
        Args:
            bypass: True для обхода всех эффектов, False для включения
        """
        self.global_effect_params["bypass_all"] = bypass
    
    def set_effect_preset(self, preset_name: str):
        """
        Установка предопределенного пресета эффектов.
        
        Args:
            preset_name: имя пресета
        """
        # Реализация загрузки предопределенных пресетов
        presets = {
            "Default": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.6, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 0, "rate": 1.0, "depth": 0.5, "feedback": 0.3, "level": 0.4},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.5}
            },
            "Rock Hall": {
                "reverb": {"type": 0, "time": 3.5, "level": 0.7, "pre_delay": 15.0, "hf_damping": 0.6},
                "chorus": {"type": 0, "rate": 1.2, "depth": 0.4, "feedback": 0.2, "level": 0.3},
                "variation": {"type": 0, "parameter1": 0.3, "parameter2": 0.4, "parameter3": 0.6, "parameter4": 0.5, "level": 0.3}
            },
            "Jazz Club": {
                "reverb": {"type": 3, "time": 1.8, "level": 0.5, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 1, "rate": 0.8, "depth": 0.3, "feedback": 0.1, "level": 0.2},
                "variation": {"type": 9, "parameter1": 0.6, "parameter2": 0.7, "parameter3": 0.5, "parameter4": 0.4, "level": 0.4}
            }
            # Добавить другие пресеты...
        }
        
        if preset_name in presets:
            self.set_effect_parameters(presets[preset_name])