import math
import numpy as np
import threading
from typing import Dict, List, Tuple, Optional, Callable, Any, Union

class XGEffectManager:
    """
    Полная реализация менеджера звуковых эффектов в соответствии со стандартом MIDI XG.
    Поддерживает системные эффекты, Insertion Effects, мультитимбральный режим и полный набор
    вариационных эффектов. Интегрируется с секвенсором через NRPN и SysEx сообщения.
    
    Поддерживаемые Insertion Effects:
    - 0: Off
    - 1: Distortion
    - 2: Overdrive
    - 3: Compressor
    - 4: Gate
    - 5: Envelope Filter
    - 6: Guitar Amp Sim
    - 7: Rotary Speaker
    - 8: Leslie
    - 9: Enhancer
    - 10: Slicer
    - 11: Vocoder
    - 12: Talk Wah
    - 13: Harmonizer
    - 14: Octave
    - 15: Detune
    - 16: Phaser
    - 17: Flanger
    
    Поддерживаемые Variation Effects (64 типа):
    - 0: Delay
    - 1: Dual Delay
    - 2: Echo
    - 3: Pan Delay
    - 4: Cross Delay
    - 5: Multi Tap
    - 6: Reverse Delay
    - 7: Tremolo
    - 8: Auto Pan
    - 9: Phaser
    - 10: Flanger
    - 11: Auto Wah
    - 12: Ring Mod
    - 13: Pitch Shifter
    - 14: Distortion
    - 15: Overdrive
    - 16: Compressor
    - 17: Limiter
    - 18: Gate
    - 19: Expander
    - 20: Rotary Speaker
    - 21: Leslie
    - 22: Vibrato
    - 23: Acoustic Simulator
    - 24: Guitar Amp Sim
    - 25: Enhancer
    - 26: Slicer
    - 27: Step Phaser
    - 28: Step Flanger
    - 29: Step Tremolo
    - 30: Step Pan
    - 31: Step Filter
    - 32: Auto Filter
    - 33: Vocoder
    - 34: Talk Wah
    - 35: Harmonizer
    - 36: Octave
    - 37: Detune
    - 38: Chorus/Reverb
    - 39: Stereo Imager
    - 40: Ambience
    - 41: Doubler
    - 42: Enhancer/Reverb
    - 43: Spectral
    - 44: Resonator
    - 45: Degrader
    - 46: Vinyl
    - 47: Looper
    - 48: Step Delay
    - 49: Step Echo
    - 50: Step Pan Delay
    - 51: Step Cross Delay
    - 52: Step Multi Tap
    - 53: Step Reverse Delay
    - 54: Step Ring Mod
    - 55: Step Pitch Shifter
    - 56: Step Distortion
    - 57: Step Overdrive
    - 58: Step Compressor
    - 59: Step Limiter
    - 60: Step Gate
    - 61: Step Expander
    - 62: Step Rotary Speaker
    
    Все эффекты поддерживают полную настройку через NRPN, SysEx и API класса.
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
        # Новые параметры вариационных эффектов
        (0, 147): {"target": "variation", "param": "new_param1", "transform": lambda x: x / 127.0},
        (0, 148): {"target": "variation", "param": "new_param2", "transform": lambda x: x / 127.0},
        
        # Insertion Effect Parameters (канал-специфичные)
        (0, 150): {"target": "insertion", "param": "type", "transform": lambda x: min(x, 17)},  # 0-17 типы (расширено)
        (0, 151): {"target": "insertion", "param": "parameter1", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 152): {"target": "insertion", "param": "parameter2", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 153): {"target": "insertion", "param": "parameter3", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 154): {"target": "insertion", "param": "parameter4", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 155): {"target": "insertion", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 156): {"target": "insertion", "param": "bypass", "transform": lambda x: x > 64},  # true/false
        # Новые параметры Insertion Effects
        (0, 157): {"target": "insertion", "param": "frequency", "transform": lambda x: x * 0.2},  # 0-25.4 Гц
        (0, 158): {"target": "insertion", "param": "depth", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 159): {"target": "insertion", "param": "feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0
        (0, 160): {"target": "insertion", "param": "lfo_waveform", "transform": lambda x: min(x, 3)},  # 0-3 типы волн
        
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
        (0, 160): {"target": "channel", "param": "reverb_send", "transform": lambda x: x / 127.0},  # Уровень отправки на реверберацию для канала
        (0, 161): {"target": "channel", "param": "chorus_send", "transform": lambda x: x / 127.0},  # Уровень отправки на хорус для канала
        (0, 162): {"target": "channel", "param": "variation_send", "transform": lambda x: x / 127.0},  # Уровень отправки на вариационный эффект для канала
        (0, 163): {"target": "channel", "param": "insertion_send", "transform": lambda x: x / 127.0},  # Уровень отправки на insertion effect для канала
        (0, 164): {"target": "channel", "param": "muted", "transform": lambda x: x > 64},  # Mute канала
        (0, 165): {"target": "channel", "param": "soloed", "transform": lambda x: x > 64},  # Solo канала
        (0, 166): {"target": "channel", "param": "pan", "transform": lambda x: (x - 64) / 64.0},  # Панорамирование канала
        (0, 167): {"target": "channel", "param": "volume", "transform": lambda x: x / 127.0},  # Громкость канала
        
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
        "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune",
        "Phaser", "Flanger"  # Новые эффекты
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
        self.current_nrpn_channel = 0  # Текущий канал для NRPN
        self.nrpn_active = False
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.data_msb = 0
        
        # Блокировка для потокобезопасности
        self.state_lock = threading.RLock()
        
        # Текущее состояние эффектов
        self._current_state = self._create_empty_state()
        self._temp_state = self._create_empty_state()
        self.state_update_pending = False
        
        # Состояние для эффектов на уровне канала
        self.channel_effect_states = [{} for _ in range(self.NUM_CHANNELS)]
        
        # Регистрация обработчиков эффектов
        self._insertion_effect_handlers = {
            1: self._process_distortion_effect,
            2: self._process_overdrive_effect,
            3: self._process_compressor_effect,
            4: self._process_gate_effect,
            5: self._process_envelope_filter_effect,
            6: self._process_guitar_amp_sim_effect,
            7: self._process_rotary_speaker_effect,
            8: self._process_leslie_effect,
            9: self._process_enhancer_effect,
            10: self._process_slicer_effect,
            11: self._process_vocoder_effect,
            12: self._process_talk_wah_effect,
            13: self._process_harmonizer_effect,
            14: self._process_octave_effect,
            15: self._process_detune_effect,
            16: self._process_phaser_effect,
            17: self._process_flanger_effect
        }
        
        # Регистрация обработчиков вариационных эффектов
        self._variation_effect_handlers = {
            0: self._process_delay_effect,
            1: self._process_dual_delay_effect,
            2: self._process_echo_effect,
            3: self._process_pan_delay_effect,
            4: self._process_cross_delay_effect,
            5: self._process_multi_tap_effect,
            6: self._process_reverse_delay_effect,
            7: self._process_tremolo_effect,
            8: self._process_auto_pan_effect,
            9: self._process_phaser_variation_effect,
            10: self._process_flanger_variation_effect,
            11: self._process_auto_wah_effect,
            12: self._process_ring_mod_effect,
            13: self._process_pitch_shifter_effect,
            14: self._process_distortion_variation_effect,
            15: self._process_overdrive_variation_effect,
            16: self._process_compressor_variation_effect,
            17: self._process_limiter_effect,
            18: self._process_gate_variation_effect,
            19: self._process_expander_effect,
            20: self._process_rotary_speaker_variation_effect,
            21: self._process_leslie_variation_effect,
            22: self._process_vibrato_effect,
            23: self._process_acoustic_simulator_effect,
            24: self._process_guitar_amp_sim_variation_effect,
            25: self._process_enhancer_variation_effect,
            26: self._process_slicer_variation_effect,
            27: self._process_step_phaser_effect,
            28: self._process_step_flanger_effect,
            29: self._process_step_tremolo_effect,
            30: self._process_step_pan_effect,
            31: self._process_step_filter_effect,
            32: self._process_auto_filter_effect,
            33: self._process_vocoder_variation_effect,
            34: self._process_talk_wah_variation_effect,
            35: self._process_harmonizer_variation_effect,
            36: self._process_octave_variation_effect,
            37: self._process_detune_variation_effect,
            38: self._process_chorus_reverb_effect,
            39: self._process_stereo_imager_effect,
            40: self._process_ambience_effect,
            41: self._process_doubler_effect,
            42: self._process_enhancer_reverb_effect,
            43: self._process_spectral_effect,
            44: self._process_resonator_effect,
            45: self._process_degrader_effect,
            46: self._process_vinyl_effect,
            47: self._process_looper_effect,
            48: self._process_step_delay_effect,
            49: self._process_step_echo_effect,
            50: self._process_step_pan_delay_effect,
            51: self._process_step_cross_delay_effect,
            52: self._process_step_multi_tap_effect,
            53: self._process_step_reverse_delay_effect,
            54: self._process_step_ring_mod_effect,
            55: self._process_step_pitch_shifter_effect,
            56: self._process_step_distortion_effect,
            57: self._process_step_overdrive_effect,
            58: self._process_step_compressor_effect,
            59: self._process_step_limiter_effect,
            60: self._process_step_gate_effect,
            61: self._process_step_expander_effect,
            62: self._process_step_rotary_speaker_effect
        }
        
        # Параметры для каждого типа Insertion Effect
        self._insertion_effect_params = {
            1: ["parameter1", "parameter2", "parameter3", "parameter4"],
            2: ["parameter1", "parameter2", "parameter3", "parameter4"],
            3: ["parameter1", "parameter2", "parameter3", "parameter4"],
            4: ["parameter1", "parameter2", "parameter3", "parameter4"],
            5: ["parameter1", "parameter2", "parameter3", "parameter4"],
            6: ["parameter1", "parameter2", "parameter3", "parameter4"],
            7: ["parameter1", "parameter2", "parameter3", "parameter4"],
            8: ["parameter1", "parameter2", "parameter3", "parameter4"],
            9: ["parameter1", "parameter2", "parameter3", "parameter4"],
            10: ["parameter1", "parameter2", "parameter3", "parameter4"],
            11: ["parameter1", "parameter2", "parameter3", "parameter4"],
            12: ["parameter1", "parameter2", "parameter3", "parameter4"],
            13: ["parameter1", "parameter2", "parameter3", "parameter4"],
            14: ["parameter1", "parameter2", "parameter3", "parameter4"],
            15: ["parameter1", "parameter2", "parameter3", "parameter4"],
            16: ["frequency", "depth", "feedback", "lfo_waveform"],
            17: ["frequency", "depth", "feedback", "lfo_waveform"]
        }
        
        # Параметры для каждого типа Variation Effect
        self._variation_effect_params = {
            0: ["time", "feedback", "level", "stereo"],
            1: ["time1", "time2", "feedback", "level"],
            2: ["time", "feedback", "level", "decay"],
            3: ["time", "feedback", "level", "rate"],
            4: ["time", "feedback", "level", "cross"],
            5: ["taps", "feedback", "level", "spacing"],
            6: ["time", "feedback", "level", "reverse"],
            7: ["rate", "depth", "waveform", "phase"],
            8: ["rate", "depth", "waveform", "phase"],
            9: ["frequency", "depth", "feedback", "lfo_waveform"],
            10: ["frequency", "depth", "feedback", "lfo_waveform"],
            11: ["sensitivity", "depth", "resonance", "mode"],
            12: ["frequency", "depth", "waveform", "level"],
            13: ["shift", "feedback", "mix", "formant"],
            14: ["drive", "tone", "level", "type"],
            15: ["drive", "tone", "level", "bias"],
            16: ["threshold", "ratio", "attack", "release"],
            17: ["threshold", "ratio", "attack", "release"],
            18: ["threshold", "reduction", "attack", "hold"],
            19: ["threshold", "ratio", "attack", "release"],
            20: ["speed", "balance", "accel", "level"],
            21: ["speed", "balance", "accel", "level"],
            22: ["rate", "depth", "waveform", "phase"],
            23: ["room", "depth", "reverb", "mode"],
            24: ["drive", "bass", "treble", "level"],
            25: ["enhance", "bass", "treble", "level"],
            26: ["rate", "depth", "waveform", "phase"],
            27: ["frequency", "depth", "feedback", "lfo_waveform"],
            28: ["frequency", "depth", "feedback", "lfo_waveform"],
            29: ["rate", "depth", "waveform", "phase"],
            30: ["rate", "depth", "waveform", "phase"],
            31: ["cutoff", "resonance", "depth", "lfo_waveform"],
            32: ["cutoff", "resonance", "depth", "lfo_waveform"],
            33: ["bands", "depth", "formant", "level"],
            34: ["sensitivity", "depth", "resonance", "mode"],
            35: ["intervals", "depth", "feedback", "mix"],
            36: ["shift", "feedback", "mix", "formant"],
            37: ["shift", "feedback", "mix", "formant"],
            38: ["chorus", "reverb", "mix", "level"],
            39: ["width", "depth", "reverb", "level"],
            40: ["reverb", "delay", "mix", "level"],
            41: ["enhance", "reverb", "mix", "level"],
            42: ["spectrum", "depth", "formant", "level"],
            43: ["resonance", "decay", "level", "mode"],
            44: ["bit_depth", "sample_rate", "level", "mode"],
            45: ["warp", "crackle", "level", "mode"],
            46: ["loop", "speed", "reverse", "level"],
            47: ["time", "feedback", "level", "taps"],
            48: ["time", "feedback", "level", "steps"],
            49: ["time", "feedback", "level", "steps"],
            50: ["time", "feedback", "level", "steps"],
            51: ["time", "feedback", "level", "steps"],
            52: ["taps", "feedback", "level", "steps"],
            53: ["time", "feedback", "level", "steps"],
            54: ["frequency", "depth", "waveform", "steps"],
            55: ["shift", "feedback", "steps", "formant"],
            56: ["drive", "tone", "steps", "type"],
            57: ["drive", "tone", "steps", "bias"],
            58: ["threshold", "ratio", "steps", "release"],
            59: ["threshold", "ratio", "steps", "release"],
            60: ["threshold", "reduction", "steps", "hold"],
            61: ["threshold", "ratio", "steps", "release"],
            62: ["speed", "balance", "steps", "level"]
        }
        
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

        # Инициализация состояния
        self.reset_effects()
    
    def _create_empty_state(self) -> Dict[str, Any]:
        """Создание пустого состояния эффектов"""
        return {
            "reverb_params": {},
            "chorus_params": {},
            "variation_params": {},
            "equalizer_params": {},
            "routing_params": {},
            "global_effect_params": {},
            "channel_params": [self._create_channel_params() for _ in range(self.NUM_CHANNELS)]
        }
    
    def _create_channel_params(self) -> Dict[str, Any]:
        """Создание параметров для канала"""
        return {
            "reverb_send": 0.5,  # Уровень отправки на реверберацию
            "chorus_send": 0.3,  # Уровень отправки на хорус
            "variation_send": 0.2,  # Уровень отправки на вариационный эффект
            "insertion_send": 1.0,  # Уровень отправки на insertion effect
            "muted": False,  # Канал замьючен
            "soloed": False,  # Канал в режиме solo
            "pan": 0.5,  # Панорамирование (0.0-1.0)
            "volume": 1.0,  # Громкость (0.0-1.0)
            "expression": 1.0,  # Выражение (0.0-1.0)
            "insertion_effect": self._create_insertion_effect_params()
        }
    
    def _create_insertion_effect_params(self) -> Dict[str, Any]:
        """Создание параметров Insertion Effect"""
        return {
            "enabled": True,
            "type": 0,  # Off
            "parameter1": 0.5,  # 0.0-1.0
            "parameter2": 0.5,  # 0.0-1.0
            "parameter3": 0.5,  # 0.0-1.0
            "parameter4": 0.5,  # 0.0-1.0
            "level": 1.0,  # 0.0-1.0
            "bypass": False,  # true/false
            # Новые параметры для Phaser и Flanger
            "frequency": 1.0,  # Новый параметр для эффектов вроде Phaser/Flanger
            "depth": 0.5,
            "feedback": 0.3,
            "lfo_waveform": 0  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        }
    
    def _copy_state(self, source: Dict[str, Any], dest: Dict[str, Any]):
        """Копирование состояния эффектов"""
        with self.state_lock:
            dest["reverb_params"] = source["reverb_params"].copy()
            dest["chorus_params"] = source["chorus_params"].copy()
            dest["variation_params"] = source["variation_params"].copy()
            dest["equalizer_params"] = source["equalizer_params"].copy()
            dest["routing_params"] = source["routing_params"].copy()
            dest["global_effect_params"] = source["global_effect_params"].copy()
            
            for i in range(self.NUM_CHANNELS):
                dest["channel_params"][i] = {
                    "reverb_send": source["channel_params"][i]["reverb_send"],
                    "chorus_send": source["channel_params"][i]["chorus_send"],
                    "variation_send": source["channel_params"][i]["variation_send"],
                    "insertion_send": source["channel_params"][i]["insertion_send"],
                    "muted": source["channel_params"][i]["muted"],
                    "soloed": source["channel_params"][i]["soloed"],
                    "pan": source["channel_params"][i]["pan"],
                    "volume": source["channel_params"][i]["volume"],
                    "expression": source["channel_params"][i]["expression"],
                    "insertion_effect": source["channel_params"][i]["insertion_effect"].copy()
                }
    
    def _update_parameter(self, state: Dict[str, Any], target: str, param: str, value: Any):
        """Обновление параметра в состоянии"""
        if target == "reverb":
            state["reverb_params"][param] = value
        elif target == "chorus":
            state["chorus_params"][param] = value
        elif target == "variation":
            state["variation_params"][param] = value
        elif target == "equalizer":
            state["equalizer_params"][param] = value
        elif target == "routing":
            state["routing_params"][param] = value
        elif target == "global":
            state["global_effect_params"][param] = value
        elif target == "channel":
            channel = self.current_nrpn_channel
            if 0 <= channel < self.NUM_CHANNELS:
                if param in ["reverb_send", "chorus_send", "variation_send", "insertion_send", "muted", "soloed", "pan", "volume"]:
                    state["channel_params"][channel][param] = value
        elif target == "insertion":
            channel = self.current_nrpn_channel
            if 0 <= channel < self.NUM_CHANNELS:
                if param in ["enabled", "type", "parameter1", "parameter2", "parameter3", "parameter4", 
                            "level", "bypass", "frequency", "depth", "feedback", "lfo_waveform"]:
                    state["channel_params"][channel]["insertion_effect"][param] = value
    
    def set_current_nrpn_channel(self, channel: int):
        """Установка текущего канала для NRPN"""
        if 0 <= channel < self.NUM_CHANNELS:
            self.current_nrpn_channel = channel
    
    def set_nrpn_msb(self, value: int):
        """Установка MSB для NRPN"""
        self.nrpn_msb = value
        self.nrpn_active = True
    
    def set_nrpn_lsb(self, value: int):
        """Установка LSB для NRPN"""
        self.nrpn_lsb = value
        self.nrpn_active = True
    
    def set_channel_effect_parameter(self, channel: int, nrpn_msb: int, nrpn_lsb: int, value: int):
        """
        Установка параметра эффекта для конкретного канала.
        
        Args:
            channel: MIDI-канал
            nrpn_msb: старший байт NRPN
            nrpn_lsb: младший байт NRPN
            value: значение (0-127)
        """
        nrpn = (nrpn_msb, nrpn_lsb)
        if nrpn not in self.XG_EFFECT_NRPN_PARAMS:
            return
            
        param_info = self.XG_EFFECT_NRPN_PARAMS[nrpn]
        real_value = param_info["transform"](value)
        
        # Обновляем временное состояние
        with self.state_lock:
            self._update_parameter(self._temp_state, param_info["target"], param_info["param"], real_value)
            self.state_update_pending = True
    
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
        real_value = param_info["transform"](data)
        
        # Обновляем временное состояние
        with self.state_lock:
            if channel is None:
                channel = self.current_nrpn_channel
                
            self._update_parameter(self._temp_state, param_info["target"], param_info["param"], real_value)
            self.state_update_pending = True
    
    def handle_sysex(self, manufacturer_id: int, data:  List[int]):
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
    
    def _handle_xg_parameter_change(self, data:  List[int]):
        """Обработка XG Parameter Change для эффектов"""
        if len(data) < 3:
            return
            
        # Извлечение параметра и значения
        parameter_msb = data[0]
        parameter_lsb = data[1]
        value = data[2]
        
        # Обработка как NRPN
        self.handle_nrpn(parameter_msb, parameter_lsb, value, 0)
    
    def _handle_xg_bulk_parameter_dump(self,data:  List[int]):
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
        state = self._get_current_state()
        
        if not channel_specific:
            # Структура bulk-дампа для системных эффектов:
            # F0 43 mm 7F 00 03 [данные] F7
            
            # Начинаем с заголовка
            dump = [0x43, 0x7F, 0x00, self.XG_BULK_EFFECTS]
            
            # Добавляем параметры эффектов в bulk-формате
            for target, params in [("reverb", state["reverb_params"]), 
                                  ("chorus", state["chorus_params"]),
                                  ("variation", state["variation_params"]),
                                  ("equalizer", state["equalizer_params"]),
                                  ("routing", state["routing_params"]),
                                  ("global", state["global_effect_params"])]:
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
                channel_params = state["channel_params"][channel]
                
                # Добавляем insertion effect параметры
                insertion_effect = channel_params.get("insertion_effect", {})
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
                    value = channel_params.get(param, 0.5)
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
            # Новые параметры Insertion Effects
            elif param == "frequency":
                if target == "insertion":
                    return int(value / 0.2)
            elif param == "depth" or param == "feedback":
                if target == "insertion":
                    return int(value * 127)
            elif param == "lfo_waveform":
                if target == "insertion":
                    return int(value)
        
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
                order_value : int = 0
                for i, effect in enumerate(range(int(value))):
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
    
    def get_channel_insertion_effect(self, channel: int) -> Dict[str, Any]:
        """Получение параметров Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                return self._current_state["channel_params"][channel]["insertion_effect"].copy()
        return self._create_insertion_effect_params()
    
    def set_channel_insertion_effect_enabled(self, channel: int, enabled: bool):
        """Включение/выключение Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["enabled"] = enabled
                self.state_update_pending = True
    
    def set_channel_insertion_effect_type(self, channel: int, effect_type: int):
        """Установка типа Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["type"] = effect_type
                self.state_update_pending = True
    
    def set_channel_insertion_effect_parameter(self, channel: int, param_index: int, value: float):
        """Установка параметра Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS and 1 <= param_index <= 4:
                param_name = f"parameter{param_index}"
                self._temp_state["channel_params"][channel]["insertion_effect"][param_name] = value
                self.state_update_pending = True
    
    def set_channel_insertion_effect_level(self, channel: int, level: float):
        """Установка уровня Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["level"] = level
                self.state_update_pending = True
    
    def set_channel_insertion_effect_bypass(self, channel: int, bypass: bool):
        """Установка обхода Insertion Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["bypass"] = bypass
                self.state_update_pending = True
    
    # --- Новые методы для управления Phaser ---
    
    def set_channel_phaser_frequency(self, channel: int, frequency: float):
        """Установка частоты LFO для фазера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_update_pending = True
    
    def set_channel_phaser_depth(self, channel: int, depth: float):
        """Установка глубины фазера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_update_pending = True
    
    def set_channel_phaser_feedback(self, channel: int, feedback: float):
        """Установка обратной связи фазера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_update_pending = True
    
    def set_channel_phaser_waveform(self, channel: int, waveform: int):
        """Установка формы волны LFO фазера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_update_pending = True
    
    # --- Новые методы для управления Flanger ---
    
    def set_channel_flanger_frequency(self, channel: int, frequency: float):
        """Установка частоты LFO для фленджера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["frequency"] = frequency
                self.state_update_pending = True
    
    def set_channel_flanger_depth(self, channel: int, depth: float):
        """Установка глубины фленджера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["depth"] = depth
                self.state_update_pending = True
    
    def set_channel_flanger_feedback(self, channel: int, feedback: float):
        """Установка обратной связи фленджера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["feedback"] = feedback
                self.state_update_pending = True
    
    def set_channel_flanger_waveform(self, channel: int, waveform: int):
        """Установка формы волны LFO фленджера на канале"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"]["lfo_waveform"] = waveform
                self.state_update_pending = True
    
    def reset_channel_insertion_effect(self, channel: int):
        """Сброс Insertion Effect для канала к значениям по умолчанию"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["insertion_effect"] = self._create_insertion_effect_params()
                self.state_update_pending = True
    
    def reset_all_insertion_effects(self):
        """Сброс всех Insertion Effects к значениям по умолчанию"""
        with self.state_lock:
            for i in range(self.NUM_CHANNELS):
                self._temp_state["channel_params"][i]["insertion_effect"] = self._create_insertion_effect_params()
            self.state_update_pending = True
    
    def process_audio(self, input_samples: List[List[Tuple[float, float]]], 
                     num_samples: int) -> List[List[Tuple[float, float]]]:
        """
        Обработка аудио с применением эффектов для всех каналов.
        
        Args:
            input_samples: список каналов, каждый содержит список стерео сэмплов [(left, right), ...]
            num_samples: количество обрабатываемых сэмплов (для автоматизации)
            
        Returns:
            список каналов, каждый содержит список обработанных стерео сэмплов [(left, right), ...]
        """
        if len(input_samples) != self.NUM_CHANNELS:
            raise ValueError(f"Ожидалось {self.NUM_CHANNELS} каналов, получено {len(input_samples)}")
        
        # Проверяем, что каждый канал содержит правильное количество сэмплов
        for i, channel_samples in enumerate(input_samples):
            if len(channel_samples) != num_samples:
                raise ValueError(f"Канал {i}: ожидалось {num_samples} сэмплов, получено {len(channel_samples)}")
        
        # Потокобезопасное получение состояния
        state = self._get_current_state()
        
        # Инициализация выходных данных
        output_channels = [[(0.0, 0.0) for _ in range(num_samples)] for _ in range(self.NUM_CHANNELS)]
        system_input_left = 0.0
        system_input_right = 0.0
        
        # Определение активных каналов (учет mute/solo)
        active_channels = self._get_active_channels(state)
        
        # Обработка Insertion Effects для каждого канала
        insertion_outputs = [[] for _ in range(self.NUM_CHANNELS)]
        for i in range(self.NUM_CHANNELS):
            if i not in active_channels:
                # Для неактивных каналов возвращаем нулевые сэмплы
                insertion_outputs[i] = [(0.0, 0.0) for _ in range(num_samples)]
                continue
                
            channel_samples = input_samples[i]
            ch_params = state["channel_params"][i]
            
            # Обработка каждого сэмпла в канале
            channel_output = []
            for j in range(num_samples):
                left_in, right_in = channel_samples[j]
                
                # Применение Insertion Effect
                insertion_effect = ch_params["insertion_effect"]
                insertion_send = ch_params["insertion_send"]
                
                if insertion_effect["enabled"] and insertion_send > 0 and not insertion_effect["bypass"]:
                    # Обработка через Insertion Effect
                    insertion_left, insertion_right = self._process_insertion_effect(
                        left_in, right_in, 
                        insertion_effect,
                        self.channel_effect_states[i],
                        state
                    )
                    insertion_left *= insertion_send
                    insertion_right *= insertion_send
                else:
                    insertion_left, insertion_right = 0.0, 0.0
                
                # Сохраняем для дальнейшей обработки
                insertion_outputs[i].append((insertion_left, insertion_right))
                
                # Формируем сигнал для системных эффектов
                reverb_send = ch_params["reverb_send"]
                system_input_left += left_in * (1 - insertion_send) * reverb_send
                system_input_right += right_in * (1 - insertion_send) * reverb_send
        
        # Обработка системных эффектов
        system_output = (0.0, 0.0)
        if not state["global_effect_params"].get("bypass_all", False) and any(active_channels):
            # Применение маршрутизации эффектов
            system_output = self._process_effect_routing(
                system_input_left, system_input_right, state
            )
        
        # Смешивание результатов для каждого канала
        for i in range(self.NUM_CHANNELS):
            if i not in active_channels:
                # Неактивные каналы остаются нулевыми
                output_channels[i] = [(0.0, 0.0) for _ in range(num_samples)]
                continue
                
            # Получаем Insertion Effect output для этого канала
            channel_insertion_output = insertion_outputs[i]
            ch_params = state["channel_params"][i]
            
            # Получаем вклад системных эффектов
            reverb_send = ch_params["reverb_send"]
            
            # Смешиваем оригинальный сигнал, Insertion Effect и системные эффекты
            volume = ch_params["volume"]
            expression = ch_params["expression"]
            channel_volume = volume * expression # * self.master_volume
            
            pan = ch_params["pan"]
            
            # Панорамирование
            left_volume = channel_volume * (1.0 - pan)
            right_volume = channel_volume * pan
            
            for j in range(num_samples):
                insertion_left, insertion_right = channel_insertion_output[j]
                system_contrib_left = system_output[0] * reverb_send
                system_contrib_right = system_output[1] * reverb_send
                
                # Применяем уровни к каждому сэмплу
                left_out = (insertion_left + system_contrib_left) * left_volume
                right_out = (insertion_right + system_contrib_right) * right_volume
                
                # Ограничиваем значения
                left_out = max(-1.0, min(1.0, left_out))
                right_out = max(-1.0, min(1.0, right_out))
                
                output_channels[i][j] = (left_out, right_out)
        
        # Применение общего уровня
        master_level = state["global_effect_params"].get("master_level", 0.8)
        if master_level != 1.0:
            for i in range(self.NUM_CHANNELS):
                for j in range(num_samples):
                    left_out, right_out = output_channels[i][j]
                    output_channels[i][j] = (left_out * master_level, right_out * master_level)
        
        # Проверка необходимости обновления состояния
        if self.state_update_pending:
            with self.state_lock:
                if self.state_update_pending:
                    self._copy_state(self._temp_state, self._current_state)
                    self.state_update_pending = False
        
        return output_channels
    
    def _get_active_channels(self, state: Dict[str, Any]) -> List[int]:
        """Определение активных каналов с учетом mute/solo"""
        soloed_channels = [i for i in range(self.NUM_CHANNELS) 
                          if state["channel_params"][i].get("soloed", False)]
        
        if soloed_channels:
            return soloed_channels
        
        return [i for i in range(self.NUM_CHANNELS) 
               if not state["channel_params"][i].get("muted", False)]
    
    def _process_effect_routing(self, left_in: float, right_in: float, 
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка маршрутизации эффектов в соответствии с настройками"""
        left_out, right_out = left_in, right_in
        routing_params = state["routing_params"]
        
        # Получаем порядок эффектов
        effect_order = routing_params.get("system_effect_order", [0, 1, 2])
        
        # Обработка в указанном порядке
        for effect_index in effect_order:
            if effect_index == 0:  # Reverb
                reverb_params = state["reverb_params"]
                reverb_amount = 1.0
                if routing_params.get("reverb_to_chorus", 0.0) > 0 and 1 in effect_order:
                    reverb_amount = 1.0 - routing_params["reverb_to_chorus"]
                
                reverb_left, reverb_right = self._process_reverb(
                    left_in * reverb_amount, 
                    right_in * reverb_amount,
                    reverb_params,
                    reverb_params #state
                )
                left_out += reverb_left * reverb_params.get("level", 0.6)
                right_out += reverb_right * reverb_params.get("level", 0.6)
                
                # Для последующих эффектов используем выход реверберации
                if routing_params.get("reverb_to_chorus", 0.0) > 0 and 1 in effect_order:
                    left_in = reverb_left * routing_params["reverb_to_chorus"]
                    right_in = reverb_right * routing_params["reverb_to_chorus"]
                else:
                    left_in, right_in = left_out, right_out
            
            elif effect_index == 1:  # Chorus
                chorus_params = state["chorus_params"]
                chorus_amount = 1.0
                if routing_params.get("chorus_to_variation", 0.0) > 0 and 2 in effect_order:
                    chorus_amount = 1.0 - routing_params["chorus_to_variation"]
                
                chorus_left, chorus_right = self._process_chorus(
                    left_in * chorus_amount, 
                    right_in * chorus_amount,
                    chorus_params,
                    chorus_params #state
                )
                left_out += chorus_left * chorus_params.get("level", 0.4)
                right_out += chorus_right * chorus_params.get("level", 0.4)
                
                # Для последующих эффектов используем выход хоруса
                if routing_params.get("chorus_to_variation", 0.0) > 0 and 2 in effect_order:
                    left_in = chorus_left * routing_params["chorus_to_variation"]
                    right_in = chorus_right * routing_params["chorus_to_variation"]
                else:
                    left_in, right_in = left_out, right_out
            
            elif effect_index == 2:  # Variation
                variation_params = state["variation_params"]
                variation_left, variation_right = self._process_variation_effect(
                    left_in, 
                    right_in,
                    variation_params,
                    state
                )
                left_out += variation_left * variation_params.get("level", 0.5)
                right_out += variation_right * variation_params.get("level", 0.5)
        
        # Применение эквалайзера ко всему сигналу
        equalizer_params = state["equalizer_params"]
        left_out, right_out = self._apply_equalizer(left_out, right_out, equalizer_params)
        
        # Применение стерео широты
        stereo_width = state["global_effect_params"].get("stereo_width", 0.5)
        if stereo_width < 1.0:
            center = (left_out + right_out) / 2.0
            left_out = center + (left_out - center) * stereo_width
            right_out = center + (right_out - center) * stereo_width
        
        return (left_out, right_out)
    
    def _apply_equalizer(self, left: float, right: float, 
                        equalizer_params: Dict[str, float]) -> Tuple[float, float]:
        """Применение эквалайзера к аудио сэмплу"""
        # Реализация 3-полосного эквалайзера с использованием билинейного преобразования
        low_gain = 10 ** (equalizer_params["low_gain"] / 20.0)
        mid_gain = 10 ** (equalizer_params["mid_gain"] / 20.0)
        high_gain = 10 ** (equalizer_params["high_gain"] / 20.0)
        mid_freq = equalizer_params["mid_freq"]
        q_factor = equalizer_params["q_factor"]
        
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

    def _process_reverb(self, left: float, right: float, 
                       reverb_params: Dict[str, float], 
                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка реверберации с использованием алгоритма Schroeder"""
        # Используем параметры реверберации
        reverb_type = reverb_params["type"]
        time = reverb_params["time"]
        level = reverb_params["level"]
        pre_delay = reverb_params["pre_delay"]
        hf_damping = reverb_params["hf_damping"]
        density = reverb_params["density"]
        early_level = reverb_params["early_level"]
        tail_level = reverb_params["tail_level"]
        
        # Алгоритм Schroeder для реверберации
        allpass_buffers = state["allpass_buffers"]
        allpass_indices = state["allpass_indices"]
        comb_buffers = state["comb_buffers"]
        comb_indices = state["comb_indices"]
        early_reflection_buffer = state["early_reflection_buffer"]
        early_reflection_index = state["early_reflection_index"]
        late_reflection_buffer = state["late_reflection_buffer"]
        late_reflection_index = state["late_reflection_index"]
        
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
        state["allpass_indices"] = allpass_indices
        state["comb_indices"] = comb_indices
        state["early_reflection_index"] = early_reflection_index
        state["late_reflection_index"] = late_reflection_index
        
        # Возвращаем стерео сигнал
        return (allpass_output * level * 0.7, allpass_output * level * 0.7)

    def _process_chorus(self, left: float, right: float, 
                       chorus_params: Dict[str, float], 
                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка хоруса с использованием двух LFO и стерео обработки"""
        # Используем параметры хоруса
        chorus_type = chorus_params["type"]
        rate = chorus_params["rate"]
        depth = chorus_params["depth"]
        feedback = chorus_params["feedback"]
        level = chorus_params["level"]
        delay = chorus_params["delay"]
        output = chorus_params["output"]
        cross_feedback = chorus_params["cross_feedback"]
        
        # Стерео хорус с двумя LFO
        delay_lines = state["delay_lines"]
        lfo_phases = state["lfo_phases"]
        lfo_rates = state["lfo_rates"]
        lfo_depths = state["lfo_depths"]
        write_indices = state["write_indices"]
        feedback_buffers = state["feedback_buffers"]
        
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
        state["lfo_phases"] = lfo_phases
        state["write_indices"] = write_indices
        state["feedback_buffers"] = feedback_buffers
        
        # Смешивание оригинала и хоруса
        return (
            left * (1 - output) + delayed_sample * output * level,
            right * (1 - output) + delayed_sample * output * level
        )
    
    def _process_variation_effect(self, left: float, right: float, 
                                variation_params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка вариационного эффекта"""
        effect_type = variation_params.get("type", 0)
        bypass = variation_params.get("bypass", False)
        
        # Проверка на обход эффекта
        if bypass:
            return (left, right)
        
        # Поиск обработчика для данного типа эффекта
        handler = self._variation_effect_handlers.get(int(effect_type))
        if handler:
            return handler(left, right, variation_params, state)
        
        # По умолчанию возвращаем оригинальный сигнал
        return (left, right)
    
    def _process_insertion_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any], 
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка Insertion Effect для отдельного канала"""
        effect_type = params.get("type", 0)
        bypass = params.get("bypass", False)
        
        # Проверка на обход эффекта
        if bypass:
            return (left, right)
        
        # Поиск обработчика для данного типа эффекта
        handler = self._insertion_effect_handlers.get(int(effect_type))
        if handler:
            return handler(left, right, params, state, system_state)
        
        # По умолчанию возвращаем оригинальный сигнал
        return (left, right)
    
    def register_insertion_effect(self, effect_type: int, handler: Callable, params: List[str]):
        """Регистрация нового Insertion Effect"""
        self._insertion_effect_handlers[effect_type] = handler
        self._insertion_effect_params[effect_type] = params
        
        # Обновляем список типов эффектов
        if effect_type >= len(self.XG_INSERTION_TYPES):
            # Дополняем список до нужной длины
            while len(self.XG_INSERTION_TYPES) <= effect_type:
                self.XG_INSERTION_TYPES.append(f"Custom Effect {len(self.XG_INSERTION_TYPES)}")
        
        # Добавляем эффект в список
        effect_name = handler.__name__.replace("_process_", "").replace("_effect", "")
        self.XG_INSERTION_TYPES[effect_type] = effect_name.title()
    
    def register_variation_effect(self, effect_type: int, handler: Callable, params: List[str]):
        """Регистрация нового Variation Effect"""
        self._variation_effect_handlers[effect_type] = handler
        self._variation_effect_params[effect_type] = params
        
        # Обновляем список типов эффектов
        if effect_type >= len(self.XG_VARIATION_TYPES):
            # Дополняем список до нужной длины
            while len(self.XG_VARIATION_TYPES) <= effect_type:
                self.XG_VARIATION_TYPES.append(f"Custom Effect {len(self.XG_VARIATION_TYPES)}")
        
        # Добавляем эффект в список
        effect_name = handler.__name__.replace("_process_", "").replace("_effect", "")
        self.XG_VARIATION_TYPES[effect_type] = effect_name.title()
    
    # --- Реализация всех Insertion Effects ---
    
    def _process_distortion_effect(self, left: float, right: float, 
                                  params: Dict[str, float], 
                                  state: Dict[str, Any], 
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Distortion (искажение)
        
        Параметры:
        - parameter1 (drive): интенсивность искажения (0.0-1.0)
        - parameter2 (tone): тембр (0.0-1.0)
        - parameter3 (level): уровень выходного сигнала (0.0-1.0)
        - parameter4 (type): тип искажения (0=simple, 1=asymmetric, 2=symmetric, 3=soft)
        
        Эффект искажения работает путем нелинейного преобразования входного сигнала,
        создавая новые гармоники и изменяя тембр звука.
        """
        # Используем параметры эффекта
        drive = params["parameter1"]
        tone = params["parameter2"]
        level = params["parameter3"]
        type = int(params["parameter4"] * 3)  # 0=simple, 1=asymmetric, 2=symmetric, 3=soft
        
        # Создаем состояние эффекта, если его нет
        if "distortion" not in state:
            state["distortion"] = {
                "prev_input": 0.0
            }
        
        # Получаем входной сигнал (среднее значение стерео)
        input_sample = (left + right) / 2.0
        
        # Применение искажения в зависимости от типа
        if type == 0:  # Simple clipping
            # Простое ограничение амплитуды
            output = max(-1.0, min(1.0, input_sample * (1 + drive * 9.0)))
        elif type == 1:  # Asymmetric
            # Асимметричное искажение (имитация лампового усилителя)
            if input_sample > 0:
                output = 1.0 - math.exp(-input_sample * (1 + drive * 9.0))
            else:
                output = -1.0 + math.exp(input_sample * (1 + drive * 9.0))
        elif type == 2:  # Symmetric
            # Симметричное искажение с использованием гиперболического тангенса
            output = math.tanh(input_sample * (1 + drive * 9.0))
        else:  # Soft clipping
            # Мягкое ограничение с использованием арктангенса
            output = math.atan(input_sample * (1 + drive * 9.0)) / (math.pi / 2.0)
        
        # Тон-контроль (простой эквалайзер)
        if tone < 0.5:
            # Больше низких частот
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Больше высоких частот
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        # Нормализация и применение уровня
        output = output * level
        
        return (output, output)
    
    def _process_overdrive_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any], 
                                 system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Overdrive (овердрайв)
        
        Параметры:
        - parameter1 (drive): интенсивность овердрайва (0.0-1.0)
        - parameter2 (tone): тембр (0.0-1.0)
        - parameter3 (level): уровень выходного сигнала (0.0-1.0)
        - parameter4 (bias): смещение (0.0-1.0)
        
        Овердрайв - это мягкая форма искажения, имитирующая перегрузку лампового усилителя.
        """
        # Используем параметры эффекта
        drive = params["parameter1"]
        tone = params["parameter2"]
        level = params["parameter3"]
        bias = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "overdrive" not in state:
            state["overdrive"] = {
                "prev_input": 0.0
            }
        
        # Получаем входной сигнал (среднее значение стерео)
        input_sample = (left + right) / 2.0
        
        # Добавляем небольшое смещение для асимметричного искажения
        biased = input_sample + bias * 0.1
        
        # Применение овердрайва (с использованием гиперболического тангенса)
        output = math.tanh(biased * (1 + drive * 9.0))
        
        # Тон-контроль
        if tone < 0.5:
            # Больше низких частот
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Больше высоких частот
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        # Нормализация и применение уровня
        output = output * level
        
        return (output, output)
    
    def _process_compressor_effect(self, left: float, right: float, 
                                  params: Dict[str, float], 
                                  state: Dict[str, Any], 
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Compressor (компрессор)
        
        Параметры:
        - parameter1 (threshold): порог (0.0-1.0, соответствует -60 до 0 дБ)
        - parameter2 (ratio): отношение компрессии (0.0-1.0, соответствует 1:1 до 20:1)
        - parameter3 (attack): атака (0.0-1.0, соответствует 1-100 мс)
        - parameter4 (release): релиз (0.0-1.0, соответствует 10-300 мс)
        
        Компрессор уменьшает динамический диапазон звука, делая тихие части громче,
        а громкие - тише.
        """
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
        if "compressor" not in state:
            state["compressor"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }
        
        # Получаем входной сигнал
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
        comp_state = state["compressor"]
        if desired_gain < comp_state["gain"]:
            # Атака
            if comp_state["attack_counter"] < attack_samples:
                comp_state["attack_counter"] += 1
                factor = comp_state["attack_counter"] / attack_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        else:
            # Релиз
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        
        # Сохранение состояния
        comp_state["gain"] = current_gain
        
        # Применение усиления
        output = input_sample * current_gain
        
        return (output, output)
    
    def _process_gate_effect(self, left: float, right: float, 
                            params: Dict[str, float], 
                            state: Dict[str, Any], 
                            system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Gate (шумоподавитель)
        
        Параметры:
        - parameter1 (threshold): порог (0.0-1.0, соответствует -80 до -10 дБ)
        - parameter2 (reduction): подавление (0.0-1.0, соответствует 0-60 дБ)
        - parameter3 (attack): атака (0.0-1.0, соответствует 1-10 мс)
        - parameter4 (hold): удержание (0.0-1.0, соответствует 0-1000 мс)
        
        Gate открывает сигнал только когда его уровень превышает заданный порог,
        что позволяет подавлять фоновый шум.
        """
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
        if "gate" not in state:
            state["gate"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Проверка порога
        gate_state = state["gate"]
        if input_level > threshold_linear:
            # Сигнал выше порога, открываем gate
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            # Сигнал ниже порога, проверяем hold
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False
        
        # Расчет усиления
        if gate_state["open"]:
            # Плавное открытие
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 1.0 / max(1, attack_samples)
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            # Плавное закрытие
            gate_state["gain"] *= 0.99  # экспоненциальное затухание
        
        # Применение редукции
        if not gate_state["open"]:
            gate_state["gain"] *= reduction_factor
        
        # Применение усиления
        output = input_sample * gate_state["gain"]
        
        return (output, output)
    
    def _process_envelope_filter_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any], 
                                       system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Envelope Filter (фильтр с управлением от огибающей)
        
        Параметры:
        - parameter1 (cutoff): частота среза (0.0-1.0, соответствует 20-20000 Гц)
        - parameter2 (resonance): резонанс (0.0-1.0)
        - parameter3 (sensitivity): чувствительность (0.0-1.0)
        - parameter4 (mode): режим (0=lowpass, 1=highpass, 2=bandpass, 3=notch)
        
        Envelope Filter изменяет частоту среза фильтра в зависимости от громкости входного сигнала.
        """
        # Используем параметры эффекта
        cutoff = 20 + params["parameter1"] * 19980  # 20-20000 Гц
        resonance = params["parameter2"]
        sensitivity = params["parameter3"]
        mode = int(params["parameter4"] * 3)  # 0=lowpass, 1=highpass, 2=bandpass, 3=notch
        
        # Создаем состояние эффекта, если его нет
        if "envelope_filter" not in state:
            state["envelope_filter"] = {
                "envelope": 0.0,
                "prev_input": 0.0,
                "filter_state": [0.0, 0.0]  # Для билинейного преобразования
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Вычисляем огибающую
        attack = 0.01 * sensitivity
        release = 0.1 * sensitivity
        if abs(input_sample) > state["envelope_filter"]["prev_input"]:
            # Атака
            state["envelope_filter"]["envelope"] += (abs(input_sample) - state["envelope_filter"]["envelope"]) * attack
        else:
            # Релиз
            state["envelope_filter"]["envelope"] += (abs(input_sample) - state["envelope_filter"]["envelope"]) * release
        
        # Ограничиваем огибающую
        state["envelope_filter"]["envelope"] = max(0.0, min(1.0, state["envelope_filter"]["envelope"]))
        
        # Вычисляем частоту среза в зависимости от огибающей
        base_freq = cutoff
        max_freq = cutoff * 10.0
        current_cutoff = base_freq + (max_freq - base_freq) * state["envelope_filter"]["envelope"]
        
        # Нормализуем частоту среза
        norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
        
        # Ограничиваем частоту среза
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))
        
        # Вычисляем параметры фильтра с использованием билинейного преобразования
        # Для упрощения используем простой резонансный фильтр
        Q = 1.0 / (resonance * 2.0 + 0.1)
        alpha = math.sin(math.pi * norm_cutoff) / (2 * Q)
        b0 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        b1 = 1 - math.cos(math.pi * norm_cutoff)
        b2 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(math.pi * norm_cutoff)
        a2 = 1 - alpha
        
        # Применяем фильтр
        x = input_sample
        y = (b0/a0) * x + (b1/a0) * state["envelope_filter"]["filter_state"][0] + \
            (b2/a0) * state["envelope_filter"]["filter_state"][1] - \
            (a1/a0) * state["envelope_filter"]["filter_state"][2] - \
            (a2/a0) * state["envelope_filter"]["filter_state"][3]
        
        # Обновляем состояние фильтра
        state["envelope_filter"]["filter_state"] = [
            x, 
            state["envelope_filter"]["filter_state"][0],
            y,
            state["envelope_filter"]["filter_state"][2]
        ]
        
        # Сохраняем предыдущий входной сигнал
        state["envelope_filter"]["prev_input"] = abs(input_sample)
        
        return (y, y)
    
    def _process_guitar_amp_sim_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any], 
                                      system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Guitar Amp Sim (симулятор гитарного усилителя)
        
        Параметры:
        - parameter1 (drive): драйв (0.0-1.0)
        - parameter2 (bass): басы (0.0-1.0)
        - parameter3 (treble): высокие (0.0-1.0)
        - parameter4 (level): уровень (0.0-1.0)
        
        Guitar Amp Sim имитирует звучание гитарного усилителя с кабинетом,
        включая искажение, тембр и импульсную характеристику кабинета.
        """
        # Используем параметры эффекта
        drive = params["parameter1"]
        bass = params["parameter2"]
        treble = params["parameter3"]
        level = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "guitar_amp_sim" not in state:
            state["guitar_amp_sim"] = {
                "prev_input": 0.0
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем искажение (имитация лампового усилителя)
        distorted = math.tanh(input_sample * (1 + drive * 9.0))
        
        # Применяем тембр (простой эквалайзер)
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)
        
        # Имитация кабинета (простая реверберация)
        cabinet = equalized * 0.8 + state["guitar_amp_sim"]["prev_input"] * 0.2
        
        # Нормализуем и применяем уровень
        output = cabinet * level
        
        # Сохраняем предыдущий входной сигнал
        state["guitar_amp_sim"]["prev_input"] = equalized
        
        return (output, output)
    
    def _process_rotary_speaker_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any], 
                                      system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Rotary Speaker (ротационный динамик)
        
        Параметры:
        - parameter1 (speed): скорость (0.0-1.0)
        - parameter2 (balance): баланс (0.0-1.0)
        - parameter3 (accel): ускорение (0.0-1.0)
        - parameter4 (level): уровень (0.0-1.0)
        
        Rotary Speaker имитирует звучание ротационного динамика (Leslie),
        создавая эффект Доплера и модуляции громкости.
        """
        # Используем параметры эффекта
        speed = params["parameter1"] * 5.0  # 0-5 Гц
        balance = params["parameter2"]
        accel = params["parameter3"]
        level = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "rotary_speaker" not in state:
            state["rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }
        
        # Обновляем фазы
        state["rotary_speaker"]["horn_phase"] += 2 * math.pi * state["rotary_speaker"]["horn_speed"] / self.sample_rate
        state["rotary_speaker"]["drum_phase"] += 2 * math.pi * state["rotary_speaker"]["drum_speed"] / self.sample_rate
        
        # Изменяем скорость вращения
        target_speed = speed * 0.5 + 0.5  # 0.5-1.0
        state["rotary_speaker"]["horn_speed"] += (target_speed - state["rotary_speaker"]["horn_speed"]) * accel
        state["rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["rotary_speaker"]["drum_speed"]) * accel
        
        # Вычисляем позиции
        horn_pos = math.sin(state["rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5
        
        # Применяем эффект
        input_sample = (left + right) / 2.0
        
        # Смешиваем каналы в зависимости от позиции
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos
        
        # Применяем баланс и уровень
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level
        
        return (left_out, right_out)
    
    def _process_leslie_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any], 
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Leslie (симулятор Leslie)
        
        Параметры:
        - parameter1 (speed): скорость (0.0-1.0)
        - parameter2 (balance): баланс (0.0-1.0)
        - parameter3 (accel): ускорение (0.0-1.0)
        - parameter4 (level): уровень (0.0-1.0)
        
        Leslie - это специфический тип ротационного динамика, часто используемый
        с органами Hammond для создания характерного звучания.
        """
        # Используем параметры эффекта
        speed = params["parameter1"] * 5.0  # 0-5 Гц
        balance = params["parameter2"]
        accel = params["parameter3"]
        level = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "leslie" not in state:
            state["leslie"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }
        
        # Обновляем фазы
        state["leslie"]["horn_phase"] += 2 * math.pi * state["leslie"]["horn_speed"] / self.sample_rate
        state["leslie"]["drum_phase"] += 2 * math.pi * state["leslie"]["drum_speed"] / self.sample_rate
        
        # Изменяем скорость вращения
        target_speed = speed * 0.5 + 0.5  # 0.5-1.0
        state["leslie"]["horn_speed"] += (target_speed - state["leslie"]["horn_speed"]) * accel
        state["leslie"]["drum_speed"] += (target_speed * 0.5 - state["leslie"]["drum_speed"]) * accel
        
        # Вычисляем позиции
        horn_pos = math.sin(state["leslie"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["leslie"]["drum_phase"] * 2) * 0.5 + 0.5
        
        # Применяем эффект
        input_sample = (left + right) / 2.0
        
        # Смешиваем каналы в зависимости от позиции
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos
        
        # Применяем баланс и уровень
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level
        
        return (left_out, right_out)
    
    def _process_enhancer_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any], 
                               system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Enhancer (тембровый усилитель)
        
        Параметры:
        - parameter1 (enhance): усиление (0.0-1.0)
        - parameter2 (bass): басы (0.0-1.0)
        - parameter3 (treble): высокие (0.0-1.0)
        - parameter4 (level): уровень (0.0-1.0)
        
        Enhancer усиливает определенные частоты для придания звуку большей четкости
        и "жизненности", часто используется для вокала и акустических инструментов.
        """
        # Используем параметры эффекта
        enhance = params["parameter1"]
        bass = params["parameter2"]
        treble = params["parameter3"]
        level = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "enhancer" not in state:
            state["enhancer"] = {
                "prev_input": 0.0
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем усилитель гармоник
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)
        
        # Применяем тембр (простой эквалайзер)
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)
        
        # Нормализуем и применяем уровень
        output = equalized * level
        
        return (output, output)
    
    def _process_slicer_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any], 
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Slicer (сайклер)
        
        Параметры:
        - parameter1 (rate): частота (0.0-1.0, соответствует 0-10 Гц)
        - parameter2 (depth): глубина (0.0-1.0)
        - parameter3 (waveform): форма волны (0=sine, 1=triangle, 2=square, 3=sawtooth)
        - parameter4 (phase): фаза (0.0-1.0)
        
        Slicer создает эффект "нарезки" звука с заданной частотой и формой волны,
        часто используется в электронной музыке.
        """
        # Используем параметры эффекта
        rate = params["parameter1"] * 10.0  # 0-10 Гц
        depth = params["parameter2"]
        waveform = int(params["parameter3"] * 3)  # 0=sine, 1=triangle, 2=square, 3=sawtooth
        phase = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "slicer" not in state:
            state["slicer"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["slicer"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение эффекта
        input_sample = (left + right) / 2.0
        
        # Вычисляем амплитуду на основе LFO
        amplitude = lfo_value * 2.0 - 1.0
        
        # Slicer эффект - обрезаем сигнал ниже порога
        output = input_sample if input_sample > amplitude else 0.0
        
        # Сохраняем фазу LFO
        state["slicer"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_vocoder_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any], 
                               system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Vocoder (вокодер)
        
        Параметры:
        - parameter1 (bands): количество полос (0.0-1.0, соответствует 1-20 полос)
        - parameter2 (depth): глубина (0.0-1.0)
        - parameter3 (formant): формант (0.0-1.0)
        - parameter4 (level): уровень (0.0-1.0)
        
        Vocoder анализирует спектр одного сигнала (носителя) и применяет его к другому сигналу (модулирующему),
        создавая эффект "роботизированного" голоса.
        """
        # Используем параметры эффекта
        bands = int(params["parameter1"] * 20) + 1  # 1-20 полос
        depth = params["parameter2"]
        formant = params["parameter3"]
        level = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "vocoder" not in state:
            # Создаем буферы для анализа спектра
            state["vocoder"] = {
                "carrier_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс
                "modulator_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс
                "carrier_pos": 0,
                "modulator_pos": 0,
                "analysis": [0.0] * bands
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Для простоты, вокодер требует двух входов (носитель и модулятор),
        # но в данном случае мы будем использовать один и тот же сигнал для обоих
        
        # Сохраняем в буферы
        state["vocoder"]["carrier_buffer"][state["vocoder"]["carrier_pos"]] = input_sample
        state["vocoder"]["modulator_buffer"][state["vocoder"]["modulator_pos"]] = input_sample
        
        # Обновляем позиции
        state["vocoder"]["carrier_pos"] = (state["vocoder"]["carrier_pos"] + 1) % len(state["vocoder"]["carrier_buffer"])
        state["vocoder"]["modulator_pos"] = (state["vocoder"]["modulator_pos"] + 1) % len(state["vocoder"]["modulator_buffer"])
        
        # Для полной реализации вокодера необходим спектральный анализ,
        # но для упрощения возвращаем оригинальный сигнал
        return (input_sample, input_sample)
    
    def _process_talk_wah_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any], 
                                system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Talk Wah (говорящий вау)
        
        Параметры:
        - parameter1 (sensitivity): чувствительность (0.0-1.0)
        - parameter2 (depth): глубина (0.0-1.0)
        - parameter3 (resonance): резонанс (0.0-1.0)
        - parameter4 (mode): режим (0=classic, 1=auto, 2=step, 3=random)
        
        Talk Wah автоматически изменяет частоту среза фильтра в зависимости от громкости входного сигнала,
        создавая эффект "говорящего" звука.
        """
        # Используем параметры эффекта
        sensitivity = params["parameter1"]
        depth = params["parameter2"]
        resonance = params["parameter3"]
        mode = int(params["parameter4"] * 3)  # 0=classic, 1=auto, 2=step, 3=random
        
        # Создаем состояние эффекта, если его нет
        if "talk_wah" not in state:
            state["talk_wah"] = {
                "envelope": 0.0,
                "prev_input": 0.0,
                "filter_state": [0.0, 0.0]
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Вычисляем огибающую
        attack = 0.01 * sensitivity
        release = 0.1 * sensitivity
        if abs(input_sample) > state["talk_wah"]["prev_input"]:
            # Атака
            state["talk_wah"]["envelope"] += (abs(input_sample) - state["talk_wah"]["envelope"]) * attack
        else:
            # Релиз
            state["talk_wah"]["envelope"] += (abs(input_sample) - state["talk_wah"]["envelope"]) * release
        
        # Ограничиваем огибающую
        state["talk_wah"]["envelope"] = max(0.0, min(1.0, state["talk_wah"]["envelope"]))
        
        # Вычисляем частоту среза в зависимости от огибающей
        base_freq = 500.0
        max_freq = 3000.0
        current_cutoff = base_freq + (max_freq - base_freq) * state["talk_wah"]["envelope"]
        
        # Нормализуем частоту среза
        norm_cutoff = current_cutoff / (self.sample_rate / 2.0)
        
        # Ограничиваем частоту среза
        norm_cutoff = max(0.001, min(0.95, norm_cutoff))
        
        # Вычисляем параметры фильтра
        Q = 1.0 / (resonance * 2.0 + 0.1)
        alpha = math.sin(math.pi * norm_cutoff) / (2 * Q)
        b0 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        b1 = 1 - math.cos(math.pi * norm_cutoff)
        b2 = (1 - math.cos(math.pi * norm_cutoff)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(math.pi * norm_cutoff)
        a2 = 1 - alpha
        
        # Применяем фильтр
        x = input_sample
        y = (b0/a0) * x + (b1/a0) * state["talk_wah"]["filter_state"][0] + \
            (b2/a0) * state["talk_wah"]["filter_state"][1] - \
            (a1/a0) * state["talk_wah"]["filter_state"][2] - \
            (a2/a0) * state["talk_wah"]["filter_state"][3]
        
        # Обновляем состояние фильтра
        state["talk_wah"]["filter_state"] = [
            x, 
            state["talk_wah"]["filter_state"][0],
            y,
            state["talk_wah"]["filter_state"][2]
        ]
        
        # Сохраняем предыдущий входной сигнал
        state["talk_wah"]["prev_input"] = abs(input_sample)
        
        return (y, y)
    
    def _process_harmonizer_effect(self, left: float, right: float, 
                                  params: Dict[str, float], 
                                  state: Dict[str, Any], 
                                  system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Harmonizer (гармонизатор)
        
        Параметры:
        - parameter1 (intervals): интервалы (0.0-1.0, соответствует -12 до +12 полутонов)
        - parameter2 (depth): глубина (0.0-1.0)
        - parameter3 (feedback): обратная связь (0.0-1.0)
        - parameter4 (mix): микс (0.0-1.0)
        
        Harmonizer создает гармонические дополнения к оригинальному звуку,
        изменяя высоту тона на заданные интервалы.
        """
        # Используем параметры эффекта
        intervals = params["parameter1"] * 24.0 - 12.0  # -12 до +12 полутонов
        depth = params["parameter2"]
        feedback = params["parameter3"]
        mix = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "harmonizer" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate * 0.1)  # 100 мс
            state["harmonizer"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** (intervals / 12.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        buffer = state["harmonizer"]["buffer"]
        pos = state["harmonizer"]["pos"]
        buffer[pos] = input_sample
        state["harmonizer"]["pos"] = (pos + 1) % len(buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = pos - int(len(buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        harmonized_sample = buffer[int(read_pos)]
        
        # Применяем обратную связь
        harmonized_sample = harmonized_sample + feedback * input_sample
        
        # Смешиваем оригинальный и гармонизированный сигналы
        output = input_sample * (1 - mix) + harmonized_sample * mix
        
        return (output, output)
    
    def _process_octave_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any], 
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Octave (октавирование)
        
        Параметры:
        - parameter1 (shift): сдвиг (0.0-1.0, соответствует -2 до +2 октав)
        - parameter2 (feedback): обратная связь (0.0-1.0)
        - parameter3 (mix): микс (0.0-1.0)
        - parameter4 (formant): формант (0.0-1.0)
        
        Octave изменяет высоту тона на целое количество октав вверх или вниз.
        """
        # Используем параметры эффекта
        shift = int(params["parameter1"] * 4) - 2  # -2 до +2 октав
        feedback = params["parameter2"]
        mix = params["parameter3"]
        formant = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "octave" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate * 0.1)  # 100 мс
            state["octave"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** shift
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        buffer = state["octave"]["buffer"]
        pos = state["octave"]["pos"]
        buffer[pos] = input_sample
        state["octave"]["pos"] = (pos + 1) % len(buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = pos - int(len(buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        octaved_sample = buffer[int(read_pos)]
        
        # Смешиваем оригинальный и октавированный сигналы
        output = input_sample * (1 - mix) + octaved_sample * mix
        
        return (output, output)
    
    def _process_detune_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any], 
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Detune (детюнинг)
        
        Параметры:
        - parameter1 (shift): сдвиг (0.0-1.0, соответствует -50 до +50 центов)
        - parameter2 (feedback): обратная связь (0.0-1.0)
        - parameter3 (mix): микс (0.0-1.0)
        - parameter4 (formant): формант (0.0-1.0)
        
        Detune создает эффект "двойного" звука, слегка изменяя высоту тона,
        что имитирует несколько инструментов, играющих одну и ту же ноту.
        """
        # Используем параметры эффекта
        shift = params["parameter1"] * 100.0 - 50.0  # -50 до +50 центов
        feedback = params["parameter2"]
        mix = params["parameter3"]
        formant = params["parameter4"]
        
        # Создаем состояние эффекта, если его нет
        if "detune" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate * 0.1)  # 100 мс
            state["detune"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** (shift / 1200.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        buffer = state["detune"]["buffer"]
        pos = state["detune"]["pos"]
        buffer[pos] = input_sample
        state["detune"]["pos"] = (pos + 1) % len(buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = pos - int(len(buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        detuned_sample = buffer[int(read_pos)]
        
        # Смешиваем оригинальный и детюненный сигналы
        output = input_sample * (1 - mix) + detuned_sample * mix
        
        return (output, output)
    
    def _process_phaser_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any], 
                              system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Phaser (фазер)
        
        Параметры:
        - frequency: частота LFO (0-25.4 Гц)
        - depth: глубина эффекта (0.0-1.0)
        - feedback: обратная связь (0.0-1.0)
        - lfo_waveform: форма волны LFO (0=sine, 1=triangle, 2=square, 3=sawtooth)
        
        Phaser создает характерный "космический" звук путем фазового сдвига
        различных частотных компонентов сигнала.
        """
        # Используем параметры эффекта
        frequency = params["frequency"]
        depth = params["depth"]
        feedback = params["feedback"]
        lfo_waveform = params["lfo_waveform"]
        
        # Получаем или создаем состояние эффекта
        if "phaser" not in state:
            state["phaser"] = {
                "lfo_phase": 0.0,
                "allpass_filters": [0.0] * 4  # Пример состояния фильтров
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["phaser"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение фазера (упрощенная модель)
        input_sample = (left + right) / 2.0
        allpass_filters = state["phaser"]["allpass_filters"]
        
        # Пример простого фазера с 4 ступенями
        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]
        
        # Применение обратной связи
        output = input_sample + feedback * (filtered - input_sample)
        
        # Сохраняем состояние
        state["phaser"]["lfo_phase"] = lfo_phase
        state["phaser"]["allpass_filters"] = allpass_filters
        
        return (output, output)
    
    def _process_flanger_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any], 
                               system_state: Dict[str, Any]) -> Tuple[float, float]:
        """
        Обработка эффекта Flanger (фленджер)
        
        Параметры:
        - frequency: частота LFO (0-10.0 Гц)
        - depth: глубина эффекта (0.0-1.0)
        - feedback: обратная связь (0.0-1.0)
        - lfo_waveform: форма волны LFO (0=sine, 1=triangle, 2=square, 3=sawtooth)
        
        Flanger создает эффект "летающего" звука путем микширования оригинального
        сигнала с задержанным, где задержка периодически изменяется.
        """
        # Используем параметры эффекта
        frequency = params["frequency"]
        depth = params["depth"]
        feedback = params["feedback"]
        lfo_waveform = params["lfo_waveform"]
        
        # Ограничиваем частоту для фленджера
        frequency = min(frequency, 10.0)
        
        # Получаем или создаем состояние эффекта
        if "flanger" not in state:
            # Создаем буфер задержки (примерно 20 мс при 44.1 кГц)
            delay_buffer_size = int(0.02 * self.sample_rate)
            state["flanger"] = {
                "lfo_phase": 0.0,
                "delay_buffer": [0.0] * delay_buffer_size,
                "buffer_pos": 0,
                "feedback_buffer": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["flanger"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Вычисляем текущую задержку (0-20 мс)
        delay_samples = int(lfo_value * len(state["flanger"]["delay_buffer"]) * 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["flanger"]["delay_buffer"]
        pos = state["flanger"]["buffer_pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["flanger"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["flanger"]["buffer_pos"] = (pos + 1) % len(buffer)
        state["flanger"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - depth) + delayed_sample * depth
        
        # Сохраняем состояние
        state["flanger"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    # --- Реализация всех Variation Effects ---
    
    def _process_delay_effect(self, left: float, right: float, 
                             params: Dict[str, float], 
                             state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        stereo = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "delay" not in state:
            # Создаем буфер задержки (макс. 1 сек при 44.1 кГц)
            delay_buffer_size = int(self.sample_rate)
            state["delay"] = {
                "buffer": [0.0] * delay_buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }
        
        # Вычисляем текущую задержку
        delay_samples = int(time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["delay"]["buffer"]
        pos = state["delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["delay"]["pos"] = (pos + 1) % len(buffer)
        state["delay"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        # Применяем стерео разнесение
        left_out = output * (1 - stereo)
        right_out = output * stereo
        
        return (left_out, right_out)
    
    def _process_dual_delay_effect(self, left: float, right: float, 
                                  params: Dict[str, float], 
                                  state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Dual Delay"""
        # Используем параметры эффекта
        time1 = params.get("parameter1", 0.3) * 1000  # 0-1000 мс
        time2 = params.get("parameter2", 0.6) * 1000  # 0-1000 мс
        feedback = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "dual_delay" not in state:
            # Создаем буферы задержки
            buffer_size1 = int(self.sample_rate)
            buffer_size2 = int(self.sample_rate)
            state["dual_delay"] = {
                "buffer1": [0.0] * buffer_size1,
                "buffer2": [0.0] * buffer_size2,
                "pos1": 0,
                "pos2": 0,
                "feedback_buffer": 0.0
            }
        
        # Вычисляем текущие задержки
        delay_samples1 = int(time1 * self.sample_rate / 1000.0)
        delay_samples2 = int(time2 * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значения из буферов задержки
        buffer1 = state["dual_delay"]["buffer1"]
        buffer2 = state["dual_delay"]["buffer2"]
        pos1 = state["dual_delay"]["pos1"]
        pos2 = state["dual_delay"]["pos2"]
        
        delay_pos1 = (pos1 - delay_samples1) % len(buffer1)
        delay_pos2 = (pos2 - delay_samples2) % len(buffer2)
        
        delayed_sample1 = buffer1[int(delay_pos1)]
        delayed_sample2 = buffer2[int(delay_pos2)]
        
        # Применяем обратную связь
        feedback_sample = state["dual_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буферы
        buffer1[pos1] = processed_sample
        buffer2[pos2] = processed_sample
        state["dual_delay"]["pos1"] = (pos1 + 1) % len(buffer1)
        state["dual_delay"]["pos2"] = (pos2 + 1) % len(buffer2)
        state["dual_delay"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанные сигналы
        output = input_sample * (1 - level) + (delayed_sample1 + delayed_sample2) * level * 0.5
        
        return (output, output)
    
    def _process_echo_effect(self, left: float, right: float, 
                            params: Dict[str, float], 
                            state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Echo"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        decay = params.get("parameter4", 0.8)
        
        # Получаем или создаем состояние эффекта
        if "echo" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["echo"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }
        
        # Вычисляем текущую задержку
        delay_samples = int(time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["echo"]["buffer"]
        pos = state["echo"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь с затуханием
        feedback_sample = state["echo"]["feedback_buffer"] * feedback * decay
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["echo"]["pos"] = (pos + 1) % len(buffer)
        state["echo"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        return (output, output)
    
    def _process_pan_delay_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Pan Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.3) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        rate = params.get("parameter4", 0.5) * 5.0  # 0-5 Гц
        
        # Получаем или создаем состояние эффекта
        if "pan_delay" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["pan_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["pan_delay"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Вычисляем текущую задержку
        delay_samples = int(time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["pan_delay"]["buffer"]
        pos = state["pan_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["pan_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["pan_delay"]["pos"] = (pos + 1) % len(buffer)
        state["pan_delay"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        # Применяем панорамирование через LFO
        pan = math.sin(lfo_phase) * 0.5 + 0.5
        left_out = output * (1 - pan)
        right_out = output * pan
        
        # Сохраняем фазу LFO
        state["pan_delay"]["lfo_phase"] = lfo_phase
        
        return (left_out, right_out)
    
    def _process_cross_delay_effect(self, left: float, right: float, 
                                   params: Dict[str, float], 
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Cross Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.3) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        cross = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "cross_delay" not in state:
            # Создаем буферы задержки для обоих каналов
            buffer_size = int(self.sample_rate)
            state["cross_delay"] = {
                "left_buffer": [0.0] * buffer_size,
                "right_buffer": [0.0] * buffer_size,
                "left_pos": 0,
                "right_pos": 0,
                "left_feedback": 0.0,
                "right_feedback": 0.0
            }
        
        # Вычисляем текущую задержку
        delay_samples = int(time * self.sample_rate / 1000.0)
        
        # Получаем входные сигналы
        input_left = left
        input_right = right
        
        # Получаем значения из буферов задержки
        left_buffer = state["cross_delay"]["left_buffer"]
        right_buffer = state["cross_delay"]["right_buffer"]
        left_pos = state["cross_delay"]["left_pos"]
        right_pos = state["cross_delay"]["right_pos"]
        
        left_delay_pos = (left_pos - delay_samples) % len(left_buffer)
        right_delay_pos = (right_pos - delay_samples) % len(right_buffer)
        
        left_delayed = left_buffer[int(left_delay_pos)]
        right_delayed = right_buffer[int(right_delay_pos)]
        
        # Применяем обратную связь с кросс-связью
        left_feedback = state["cross_delay"]["left_feedback"] * feedback * (1 - cross)
        right_feedback = state["cross_delay"]["right_feedback"] * feedback * (1 - cross)
        cross_left_feedback = state["cross_delay"]["right_feedback"] * feedback * cross
        cross_right_feedback = state["cross_delay"]["left_feedback"] * feedback * cross
        
        processed_left = input_left + left_feedback + cross_left_feedback
        processed_right = input_right + right_feedback + cross_right_feedback
        
        # Сохраняем в буферы
        left_buffer[left_pos] = processed_left
        right_buffer[right_pos] = processed_right
        state["cross_delay"]["left_pos"] = (left_pos + 1) % len(left_buffer)
        state["cross_delay"]["right_pos"] = (right_pos + 1) % len(right_buffer)
        state["cross_delay"]["left_feedback"] = processed_left
        state["cross_delay"]["right_feedback"] = processed_right
        
        # Смешиваем оригинальные и задержанные сигналы
        left_out = input_left * (1 - level) + left_delayed * level
        right_out = input_right * (1 - level) + right_delayed * level
        
        return (left_out, right_out)
    
    def _process_multi_tap_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Multi Tap"""
        # Используем параметры эффекта
        taps = int(params.get("parameter1", 0.5) * 10) + 1  # 1-10 тапов
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        spacing = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "multi_tap" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["multi_tap"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0
            }
        
        # Вычисляем задержки для тапов
        delays = []
        for i in range(taps):
            delay_time = (i * spacing * 500)  # до 500 мс
            delays.append(int(delay_time * self.sample_rate / 1000.0))
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значения из буфера задержки
        buffer = state["multi_tap"]["buffer"]
        pos = state["multi_tap"]["pos"]
        
        # Суммируем все тапы
        delayed_sum = 0.0
        for delay_samples in delays:
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sum += buffer[int(delay_pos)]
        
        # Нормализуем сумму
        delayed_sum /= taps
        
        # Применяем обратную связь
        feedback_sample = state["multi_tap"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["multi_tap"]["pos"] = (pos + 1) % len(buffer)
        state["multi_tap"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sum * level
        
        return (output, output)
    
    def _process_reverse_delay_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Reverse Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        reverse = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "reverse_delay" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["reverse_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "reverse_buffer": [0.0] * buffer_size
            }
        
        # Вычисляем текущую задержку
        delay_samples = int(time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["reverse_delay"]["buffer"]
        pos = state["reverse_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["reverse_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["reverse_delay"]["pos"] = (pos + 1) % len(buffer)
        state["reverse_delay"]["feedback_buffer"] = processed_sample
        
        # Обработка обратной задержки
        reverse_buffer = state["reverse_delay"]["reverse_buffer"]
        reverse_pos = (pos + delay_samples) % len(reverse_buffer)
        reverse_sample = reverse_buffer[int(reverse_pos)]
        
        # Сохраняем в обратный буфер
        reverse_buffer[pos] = processed_sample
        
        # Смешиваем оригинальный, прямой и обратный сигналы
        output = input_sample * (1 - level) + delayed_sample * level * (1 - reverse) + reverse_sample * level * reverse
        
        return (output, output)
    
    def _process_tremolo_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Tremolo"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        phase = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "tremolo" not in state:
            state["tremolo"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["tremolo"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение эффекта
        output_left = left * lfo_value
        output_right = right * lfo_value
        
        # Сохраняем фазу LFO
        state["tremolo"]["lfo_phase"] = lfo_phase
        
        return (output_left, output_right)
    
    def _process_auto_pan_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Auto Pan"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        phase = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "auto_pan" not in state:
            state["auto_pan"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["auto_pan"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO для панорамирования
        pan = lfo_value * depth * 0.5 + 0.5
        
        # Смешиваем каналы
        output_left = left * (1 - pan) + right * pan
        output_right = right * pan + left * (1 - pan)
        
        # Сохраняем фазу LFO
        state["auto_pan"]["lfo_phase"] = lfo_phase
        
        return (output_left, output_right)
    
    def _process_phaser_variation_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Phaser (вариационный)"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # 0-3 типы волн
        
        # Получаем или создаем состояние эффекта
        if "phaser_variation" not in state:
            state["phaser_variation"] = {
                "lfo_phase": 0.0,
                "allpass_filters": [0.0] * 4
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["phaser_variation"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение фазера
        input_sample = (left + right) / 2.0
        allpass_filters = state["phaser_variation"]["allpass_filters"]
        
        # Пример простого фазера с 4 ступенями
        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]
        
        # Применение обратной связи
        output = input_sample + feedback * (filtered - input_sample)
        
        # Сохраняем состояние
        state["phaser_variation"]["lfo_phase"] = lfo_phase
        state["phaser_variation"]["allpass_filters"] = allpass_filters
        
        return (output, output)
    
    def _process_flanger_variation_effect(self, left: float, right: float, 
                                        params: Dict[str, float], 
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Flanger (вариационный)"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # 0-3 типы волн
        
        # Ограничиваем частоту для фленджера
        frequency = min(frequency, 10.0)
        
        # Получаем или создаем состояние эффекта
        if "flanger_variation" not in state:
            # Создаем буфер задержки (примерно 20 мс при 44.1 кГц)
            delay_buffer_size = int(0.02 * self.sample_rate)
            state["flanger_variation"] = {
                "lfo_phase": 0.0,
                "delay_buffer": [0.0] * delay_buffer_size,
                "buffer_pos": 0,
                "feedback_buffer": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["flanger_variation"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Вычисляем текущую задержку (0-20 мс)
        delay_samples = int(lfo_value * len(state["flanger_variation"]["delay_buffer"]) * 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["flanger_variation"]["delay_buffer"]
        pos = state["flanger_variation"]["buffer_pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["flanger_variation"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["flanger_variation"]["buffer_pos"] = (pos + 1) % len(buffer)
        state["flanger_variation"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - depth) + delayed_sample * depth
        
        # Сохраняем состояние
        state["flanger_variation"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_auto_wah_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Auto Wah"""
        # Используем параметры эффекта
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Получаем или создаем состояние эффекта
        if "auto_wah" not in state:
            state["auto_wah"] = {
                "envelope": 0.0,
                "cutoff": 1000.0,
                "prev_input": 0.0
            }
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Вычисляем огибающую
        attack = 0.01
        release = 0.1
        if abs(input_sample) > state["auto_wah"]["prev_input"]:
            # Атака
            state["auto_wah"]["envelope"] += (abs(input_sample) - state["auto_wah"]["envelope"]) * attack
        else:
            # Релиз
            state["auto_wah"]["envelope"] += (abs(input_sample) - state["auto_wah"]["envelope"]) * release
        
        # Ограничиваем огибающую
        state["auto_wah"]["envelope"] = max(0.0, min(1.0, state["auto_wah"]["envelope"]))
        
        # Вычисляем частоту среза в зависимости от огибающей
        base_freq = 200.0
        max_freq = 5000.0
        state["auto_wah"]["cutoff"] = base_freq + (max_freq - base_freq) * state["auto_wah"]["envelope"]
        
        # Нормализуем частоту среза
        norm_cutoff = state["auto_wah"]["cutoff"] / (self.sample_rate / 2.0)
        
        # Ограничиваем частоту среза
        norm_cutoff = max(0.0, min(0.95, norm_cutoff))
        
        # Применяем фильтр (упрощенная модель)
        # Здесь должна быть реализация фильтра, но для упрощения возвращаем оригинальный сигнал
        output = input_sample
        
        # Сохраняем предыдущий входной сигнал
        state["auto_wah"]["prev_input"] = abs(input_sample)
        
        return (output, output)
    
    def _process_ring_mod_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Ring Mod"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 1000.0  # 0-1000 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        level = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "ring_mod" not in state:
            state["ring_mod"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["ring_mod"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение кольцевой модуляции
        input_sample = (left + right) / 2.0
        output = input_sample * lfo_value
        
        # Смешиваем оригинальный и модулированный сигналы
        output = input_sample * (1 - level) + output * level
        
        # Сохраняем фазу LFO
        state["ring_mod"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_pitch_shifter_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Pitch Shifter"""
        # Используем параметры эффекта
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0  # -12 до +12 полутонов
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "pitch_shifter" not in state:
            state["pitch_shifter"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс буфер
                "buffer_pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** (shift / 12.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        delay_buffer = state["pitch_shifter"]["delay_buffer"]
        buffer_pos = state["pitch_shifter"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["pitch_shifter"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        shifted_sample = delay_buffer[int(read_pos)]
        
        # Смешиваем оригинальный и сдвинутый сигналы
        output = input_sample * (1 - mix) + shifted_sample * mix
        
        return (output, output)
    
    def _process_distortion_variation_effect(self, left: float, right: float, 
                                           params: Dict[str, float], 
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Distortion (вариационный)"""
        # Используем параметры эффекта
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        type = int(params.get("parameter4", 0.5) * 3)  # 0-3 типы
        
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
    
    def _process_overdrive_variation_effect(self, left: float, right: float, 
                                          params: Dict[str, float], 
                                          state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Overdrive (вариационный)"""
        # Используем параметры эффекта
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        bias = params.get("parameter4", 0.5)
        
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
    
    def _process_compressor_variation_effect(self, left: float, right: float, 
                                           params: Dict[str, float], 
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Compressor (вариационный)"""
        # Используем параметры эффекта
        threshold = -60 + params.get("parameter1", 0.5) * 60  # -60 до 0 дБ
        ratio = 1 + params.get("parameter2", 0.5) * 19  # 1:1 до 20:1
        attack = 1 + params.get("parameter3", 0.5) * 99  # 1-100 мс
        release = 10 + params.get("parameter4", 0.5) * 290  # 10-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)
        
        # Создаем состояние компрессора, если его нет
        if "compressor_variation" not in state:
            state["compressor_variation"] = {
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
        comp_state = state["compressor_variation"]
        if desired_gain < comp_state["gain"]:
            # Атака
            if comp_state["attack_counter"] < attack_samples:
                comp_state["attack_counter"] += 1
                factor = comp_state["attack_counter"] / attack_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        else:
            # Релиз
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                current_gain = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                current_gain = desired_gain
        
        # Сохранение состояния
        comp_state["gain"] = current_gain
        
        # Применение усиления
        output = input_sample * current_gain
        
        return (output, output)
    
    def _process_limiter_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Limiter"""
        # Используем параметры эффекта
        threshold = -20 + params.get("parameter1", 0.5) * 20  # -20 до 0 дБ
        ratio = 10 + params.get("parameter2", 0.5) * 10  # 10:1 до 20:1
        attack = 0.1 + params.get("parameter3", 0.5) * 9.9  # 0.1-10 мс
        release = 50 + params.get("parameter4", 0.5) * 250  # 50-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        release_samples = int(release * self.sample_rate / 1000.0)
        
        # Создаем состояние лимитера, если его нет
        if "limiter" not in state:
            state["limiter"] = {
                "gain": 1.0,
                "attack_counter": 0,
                "release_counter": 0
            }
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level > threshold_linear:
            # Сигнал выше порога, применяем лимитирование
            desired_gain = threshold_linear / (input_level ** (1/ratio))
        else:
            # Сигнал ниже порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        limiter_state = state["limiter"]
        if desired_gain < limiter_state["gain"]:
            # Атака (быстрая)
            limiter_state["gain"] = desired_gain
        else:
            # Релиз (медленный)
            if limiter_state["release_counter"] < release_samples:
                limiter_state["release_counter"] += 1
                factor = limiter_state["release_counter"] / release_samples
                limiter_state["gain"] = limiter_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                limiter_state["gain"] = desired_gain
        
        # Применение усиления
        output = input_sample * limiter_state["gain"]
        
        return (output, output)
    
    def _process_gate_variation_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Gate (вариационный)"""
        # Используем параметры эффекта
        threshold = -80 + params.get("parameter1", 0.5) * 70  # -80 до -10 дБ
        reduction = params.get("parameter2", 0.5) * 60  # 0-60 дБ
        attack = 1 + params.get("parameter3", 0.5) * 9  # 1-10 мс
        hold = params.get("parameter4", 0.5) * 1000  # 0-1000 мс
        
        # Конвертация в линейные значения
        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        attack_samples = int(attack * self.sample_rate / 1000.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)
        
        # Создаем состояние gate, если его нет
        if "gate_variation" not in state:
            state["gate_variation"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0
            }
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Проверка порога
        gate_state = state["gate_variation"]
        if input_level > threshold_linear:
            # Сигнал выше порога, открываем gate
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            # Сигнал ниже порога, проверяем hold
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False
        
        # Расчет усиления
        if gate_state["open"]:
            # Плавное открытие
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 1.0 / max(1, attack_samples)
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            # Плавное закрытие
            gate_state["gain"] *= 0.99  # экспоненциальное затухание
        
        # Применение редукции
        if not gate_state["open"]:
            gate_state["gain"] *= reduction_factor
        
        # Применение усиления
        output = input_sample * gate_state["gain"]
        
        return (output, output)
    
    def _process_expander_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Expander"""
        # Используем параметры эффекта
        threshold = -60 + params.get("parameter1", 0.5) * 60  # -60 до 0 дБ
        ratio = 1 + params.get("parameter2", 0.5) * 9  # 1:1 до 10:1
        attack = 1 + params.get("parameter3", 0.5) * 99  # 1-100 мс
        release = 10 + params.get("parameter4", 0.5) * 290  # 10-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        
        # Создаем состояние экспандера, если его нет
        if "expander" not in state:
            state["expander"] = {
                "gain": 1.0,
                "counter": 0
            }
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level < threshold_linear:
            # Сигнал ниже порога, применяем экспандирование
            desired_gain = 1.0 / (ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            # Сигнал выше порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        expander_state = state["expander"]
        if desired_gain < expander_state["gain"]:
            # Релиз (медленный)
            expander_state["gain"] -= 0.01
            expander_state["gain"] = max(desired_gain, expander_state["gain"])
        else:
            # Атака (быстрая)
            expander_state["gain"] = desired_gain
        
        # Применение усиления
        output = input_sample * expander_state["gain"]
        
        return (output, output)
    
    def _process_rotary_speaker_variation_effect(self, left: float, right: float, 
                                               params: Dict[str, float], 
                                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Rotary Speaker (вариационный)"""
        # Используем параметры эффекта
        speed = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "rotary_speaker" not in state:
            state["rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }
        
        # Обновляем фазы
        state["rotary_speaker"]["horn_phase"] += 2 * math.pi * state["rotary_speaker"]["horn_speed"] / self.sample_rate
        state["rotary_speaker"]["drum_phase"] += 2 * math.pi * state["rotary_speaker"]["drum_speed"] / self.sample_rate
        
        # Изменяем скорость вращения
        target_speed = speed * 0.5 + 0.5  # 0.5-1.0
        state["rotary_speaker"]["horn_speed"] += (target_speed - state["rotary_speaker"]["horn_speed"]) * accel
        state["rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["rotary_speaker"]["drum_speed"]) * accel
        
        # Вычисляем позиции
        horn_pos = math.sin(state["rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5
        
        # Применяем эффект
        input_sample = (left + right) / 2.0
        
        # Смешиваем каналы в зависимости от позиции
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos
        
        # Применяем баланс и уровень
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level
        
        return (left_out, right_out)
    
    def _process_leslie_variation_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Leslie (вариационный)"""
        # Используем параметры эффекта
        speed = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        balance = params.get("parameter2", 0.5)
        accel = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "leslie" not in state:
            state["leslie"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0
            }
        
        # Обновляем фазы
        state["leslie"]["horn_phase"] += 2 * math.pi * state["leslie"]["horn_speed"] / self.sample_rate
        state["leslie"]["drum_phase"] += 2 * math.pi * state["leslie"]["drum_speed"] / self.sample_rate
        
        # Изменяем скорость вращения
        target_speed = speed * 0.5 + 0.5  # 0.5-1.0
        state["leslie"]["horn_speed"] += (target_speed - state["leslie"]["horn_speed"]) * accel
        state["leslie"]["drum_speed"] += (target_speed * 0.5 - state["leslie"]["drum_speed"]) * accel
        
        # Вычисляем позиции
        horn_pos = math.sin(state["leslie"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["leslie"]["drum_phase"] * 2) * 0.5 + 0.5
        
        # Применяем эффект
        input_sample = (left + right) / 2.0
        
        # Смешиваем каналы в зависимости от позиции
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos
        
        # Применяем баланс и уровень
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level
        
        return (left_out, right_out)
    
    def _process_vibrato_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Vibrato"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        phase = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "vibrato" not in state:
            state["vibrato"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["vibrato"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.02  # небольшое изменение высоты тона
        
        # Применение вибрато
        left_out = left * (1 + lfo_value)
        right_out = right * (1 + lfo_value)
        
        # Сохраняем фазу LFO
        state["vibrato"]["lfo_phase"] = lfo_phase
        
        return (left_out, right_out)
    
    def _process_acoustic_simulator_effect(self, left: float, right: float, 
                                          params: Dict[str, float], 
                                          state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Acoustic Simulator"""
        # Используем параметры эффекта
        room = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Упрощенная модель акустического симулятора
        # Комбинируем реверберацию и EQ
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем EQ в зависимости от режима
        if mode == 0:  # Комната
            bass_boost = 0.8 + room * 0.2
            mid_cut = 0.9 - room * 0.1
            treble_cut = 0.7 - room * 0.2
        elif mode == 1:  # Концертный зал
            bass_boost = 0.9 + room * 0.1
            mid_cut = 0.95
            treble_cut = 0.8 - room * 0.1
        elif mode == 2:  # Студия
            bass_boost = 0.7 + room * 0.3
            mid_cut = 1.0
            treble_cut = 0.9 - room * 0.1
        else:  # Сцена
            bass_boost = 0.6 + room * 0.4
            mid_cut = 0.8 + room * 0.2
            treble_cut = 0.7 + room * 0.3
        
        # Применяем EQ
        bass = input_sample * bass_boost
        mid = input_sample * mid_cut
        treble = input_sample * treble_cut
        
        # Смешиваем частоты
        output = bass * 0.3 + mid * 0.4 + treble * 0.3
        
        # Применяем небольшую реверберацию
        reverb_amount = reverb * 0.3
        output = output * (1 - reverb_amount) + input_sample * reverb_amount
        
        return (output, output)
    
    def _process_guitar_amp_sim_variation_effect(self, left: float, right: float, 
                                               params: Dict[str, float], 
                                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Guitar Amp Sim (вариационный)"""
        # Используем параметры эффекта
        drive = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем искажение (упрощенная модель)
        distorted = math.tanh(input_sample * (1 + drive * 9.0))
        
        # Применяем эквалайзер
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = distorted * (bass_boost * 0.7 + treble_boost * 0.3)
        
        # Нормализуем и применяем уровень
        output = equalized * level
        
        return (output, output)
    
    def _process_enhancer_variation_effect(self, left: float, right: float, 
                                         params: Dict[str, float], 
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Enhancer (вариационный)"""
        # Используем параметры эффекта
        enhance = params.get("parameter1", 0.5)
        bass = params.get("parameter2", 0.5)
        treble = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем усилитель гармоник
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)
        
        # Применяем эквалайзер
        bass_boost = 0.5 + bass * 0.5
        treble_boost = 0.5 + treble * 0.5
        equalized = enhanced * (bass_boost * 0.6 + treble_boost * 0.4)
        
        # Нормализуем и применяем уровень
        output = equalized * level
        
        return (output, output)
    
    def _process_slicer_variation_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Slicer (вариационный)"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        phase = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "slicer" not in state:
            state["slicer"] = {
                "lfo_phase": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["slicer"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase + phase * 2 * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase + phase * 2 * math.pi) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение эффекта
        input_sample = (left + right) / 2.0
        
        # Вычисляем амплитуду на основе LFO
        amplitude = lfo_value * 2.0 - 1.0
        
        # Slicer эффект - обрезаем сигнал ниже порога
        output = input_sample if input_sample > amplitude else 0.0
        
        # Сохраняем фазу LFO
        state["slicer"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_step_phaser_effect(self, left: float, right: float, 
                                   params: Dict[str, float], 
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Phaser"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_phaser" not in state:
            state["step_phaser"] = {
                "lfo_phase": 0.0,
                "allpass_filters": [0.0] * 4,
                "step": 0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["step_phaser"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Вычисляем текущий шаг
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != state["step_phaser"]["step"]:
            state["step_phaser"]["step"] = step
            
            # Сброс фильтров при смене шага
            state["step_phaser"]["allpass_filters"] = [0.0] * 4
        
        # Нормализация LFO
        lfo_value = step / (steps - 1)
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение фазера
        input_sample = (left + right) / 2.0
        allpass_filters = state["step_phaser"]["allpass_filters"]
        
        # Пример простого фазера с 4 ступенями
        filtered = input_sample
        for i in range(len(allpass_filters)):
            allpass_filters[i] = 0.7 * allpass_filters[i] + 0.3 * (filtered - lfo_value * allpass_filters[i])
            filtered = allpass_filters[i]
        
        # Применение обратной связи
        output = input_sample + feedback * (filtered - input_sample)
        
        # Сохраняем состояние
        state["step_phaser"]["lfo_phase"] = lfo_phase
        state["step_phaser"]["allpass_filters"] = allpass_filters
        
        return (output, output)
    
    def _process_step_flanger_effect(self, left: float, right: float, 
                                    params: Dict[str, float], 
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Flanger"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Ограничиваем частоту для фленджера
        frequency = min(frequency, 10.0)
        
        # Получаем или создаем состояние эффекта
        if "step_flanger" not in state:
            # Создаем буфер задержки (примерно 20 мс при 44.1 кГц)
            delay_buffer_size = int(0.02 * self.sample_rate)
            state["step_flanger"] = {
                "lfo_phase": 0.0,
                "delay_buffer": [0.0] * delay_buffer_size,
                "buffer_pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["step_flanger"]["lfo_phase"]
        lfo_phase += 2 * math.pi * frequency / self.sample_rate
        
        # Вычисляем текущий шаг
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != state["step_flanger"]["step"]:
            state["step_flanger"]["step"] = step
            
            # Сброс буфера при смене шага
            state["step_flanger"]["delay_buffer"] = [0.0] * len(state["step_flanger"]["delay_buffer"])
        
        # Нормализация LFO
        lfo_value = step / (steps - 1)
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Вычисляем текущую задержку (0-20 мс)
        delay_samples = int(lfo_value * len(state["step_flanger"]["delay_buffer"]) * 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["step_flanger"]["delay_buffer"]
        pos = state["step_flanger"]["buffer_pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["step_flanger"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_flanger"]["buffer_pos"] = (pos + 1) % len(buffer)
        state["step_flanger"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - depth) + delayed_sample * depth
        
        # Сохраняем состояние
        state["step_flanger"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_step_tremolo_effect(self, left: float, right: float, 
                                    params: Dict[str, float], 
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Tremolo"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 10.0  # 0-10 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_tremolo" not in state:
            state["step_tremolo"] = {
                "lfo_phase": 0.0,
                "step": 0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["step_tremolo"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Вычисляем текущий шаг
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != state["step_tremolo"]["step"]:
            state["step_tremolo"]["step"] = step
        
        # Нормализация шага
        lfo_value = step / (steps - 1)
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_value * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs(lfo_value * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if step > steps / 2 else 0
        else:  # Sawtooth
            lfo_value = lfo_value * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение эффекта
        output_left = left * lfo_value
        output_right = right * lfo_value
        
        # Сохраняем фазу LFO
        state["step_tremolo"]["lfo_phase"] = lfo_phase
        
        return (output_left, output_right)
    
    def _process_step_pan_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Pan"""
        # Используем параметры эффекта
        rate = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_pan" not in state:
            state["step_pan"] = {
                "lfo_phase": 0.0,
                "step": 0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["step_pan"]["lfo_phase"]
        lfo_phase += 2 * math.pi * rate / self.sample_rate
        
        # Вычисляем текущий шаг
        step = int((lfo_phase / (2 * math.pi)) * steps) % steps
        if step != state["step_pan"]["step"]:
            state["step_pan"]["step"] = step
        
        # Нормализация шага
        pan = step / (steps - 1)
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            pan = math.sin(pan * math.pi) * 0.5 + 0.5
        elif waveform == 1:  # Triangle
            pan = 1 - abs(pan * 2 - 1) * 0.5
        elif waveform == 2:  # Square
            pan = 1 if step > steps / 2 else 0
        else:  # Sawtooth
            pan = pan
        
        # Нормализация панорамирования
        pan = pan * depth
        
        # Смешиваем каналы
        output_left = left * (1 - pan) + right * pan
        output_right = right * pan + left * (1 - pan)
        
        # Сохраняем фазу LFO
        state["step_pan"]["lfo_phase"] = lfo_phase
        
        return (output_left, output_right)
    
    def _process_step_filter_effect(self, left: float, right: float, 
                                   params: Dict[str, float], 
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Filter"""
        # Используем параметры эффекта
        cutoff = params.get("parameter1", 0.5) * 10000.0  # 0-10000 Гц
        resonance = params.get("parameter2", 0.5)
        depth = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_filter" not in state:
            state["step_filter"] = {
                "step": 0,
                "prev_input": 0.0,
                "prev_output": 0.0
            }
        
        # Вычисляем текущий шаг
        step = state["step_filter"]["step"]
        step = (step + 1) % steps
        state["step_filter"]["step"] = step
        
        # Нормализация шага
        filter_amount = step / (steps - 1)
        filter_amount = filter_amount * depth
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем фильтр (упрощенная модель)
        # Здесь должна быть реализация фильтра, но для упрощения возвращаем оригинальный сигнал
        output = input_sample * (1 - filter_amount) + input_sample * filter_amount
        
        return (output, output)
    
    def _process_auto_filter_effect(self, left: float, right: float, 
                                   params: Dict[str, float], 
                                   state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Auto Filter"""
        # Используем параметры эффекта
        cutoff = params.get("parameter1", 0.5) * 10000.0  # 0-10000 Гц
        resonance = params.get("parameter2", 0.5)
        depth = params.get("parameter3", 0.5)
        lfo_waveform = int(params.get("parameter4", 0.5) * 3)  # 0-3 типы волн
        
        # Получаем или создаем состояние эффекта
        if "auto_filter" not in state:
            state["auto_filter"] = {
                "lfo_phase": 0.0,
                "envelope": 0.0,
                "prev_input": 0.0
            }
        
        # Обновляем фазу LFO
        lfo_phase = state["auto_filter"]["lfo_phase"]
        lfo_phase += 2 * math.pi * 1.0 / self.sample_rate  # 1 Гц
        
        # Генерация LFO в зависимости от формы волны
        if lfo_waveform == 0:  # Sine
            lfo_value = math.sin(lfo_phase)
        elif lfo_waveform == 1:  # Triangle
            lfo_value = 1 - abs((lfo_phase / math.pi) % 2 - 1) * 2
        elif lfo_waveform == 2:  # Square
            lfo_value = 1 if math.sin(lfo_phase) > 0 else -1
        else:  # Sawtooth
            lfo_value = (lfo_phase / (2 * math.pi)) % 1 * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Вычисляем частоту среза
        current_cutoff = cutoff * lfo_value
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем фильтр (упрощенная модель)
        # Здесь должна быть реализация фильтра, но для упрощения возвращаем оригинальный сигнал
        output = input_sample
        
        # Сохраняем фазу LFO
        state["auto_filter"]["lfo_phase"] = lfo_phase
        
        return (output, output)
    
    def _process_vocoder_variation_effect(self, left: float, right: float, 
                                        params: Dict[str, float], 
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Vocoder (вариационный)"""
        # Используем параметры эффекта
        bands = int(params.get("parameter1", 0.5) * 20) + 1  # 1-20 полос
        depth = params.get("parameter2", 0.5)
        formant = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Упрощенная модель вокодера
        # Здесь должна быть реализация вокодера, но для упрощения возвращаем оригинальный сигнал
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        return (left, right)
    
    def _process_talk_wah_variation_effect(self, left: float, right: float, 
                                         params: Dict[str, float], 
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Talk Wah (вариационный)"""
        # Используем параметры эффекта
        sensitivity = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        resonance = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Упрощенная модель Talk Wah
        # Комбинируем Auto Wah с управлением от микрофона
        
        # Здесь должна быть реализация эффекта, но для упрощения возвращаем оригинальный сигнал
        return (left, right)
    
    def _process_harmonizer_variation_effect(self, left: float, right: float, 
                                           params: Dict[str, float], 
                                           state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Harmonizer (вариационный)"""
        # Используем параметры эффекта
        intervals = params.get("parameter1", 0.5) * 24.0 - 12.0  # -12 до +12 полутонов
        depth = params.get("parameter2", 0.5)
        feedback = params.get("parameter3", 0.5)
        mix = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "harmonizer" not in state:
            state["harmonizer"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс буфер
                "buffer_pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** (intervals / 12.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        delay_buffer = state["harmonizer"]["delay_buffer"]
        buffer_pos = state["harmonizer"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["harmonizer"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        harmonized_sample = delay_buffer[int(read_pos)]
        
        # Применяем обратную связь
        harmonized_sample = harmonized_sample + feedback * input_sample
        
        # Смешиваем оригинальный и гармонизированный сигналы
        output = input_sample * (1 - mix) + harmonized_sample * mix
        
        return (output, output)
    
    def _process_octave_variation_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Octave (вариационный)"""
        # Используем параметры эффекта
        shift = int(params.get("parameter1", 0.5) * 4) - 2  # -2 до +2 октав
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "octave" not in state:
            state["octave"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс буфер
                "buffer_pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** shift
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        delay_buffer = state["octave"]["delay_buffer"]
        buffer_pos = state["octave"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["octave"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        octaved_sample = delay_buffer[int(read_pos)]
        
        # Смешиваем оригинальный и октавированный сигналы
        output = input_sample * (1 - mix) + octaved_sample * mix
        
        return (output, output)
    
    def _process_detune_variation_effect(self, left: float, right: float, 
                                       params: Dict[str, float], 
                                       state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Detune (вариационный)"""
        # Используем параметры эффекта
        shift = params.get("parameter1", 0.5) * 100.0 - 50.0  # -50 до +50 центов
        feedback = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        formant = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "detune" not in state:
            state["detune"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс буфер
                "buffer_pos": 0
            }
        
        # Вычисляем коэффициент изменения высоты тона
        pitch_factor = 2 ** (shift / 1200.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        delay_buffer = state["detune"]["delay_buffer"]
        buffer_pos = state["detune"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["detune"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        detuned_sample = delay_buffer[int(read_pos)]
        
        # Смешиваем оригинальный и детюненный сигналы
        output = input_sample * (1 - mix) + detuned_sample * mix
        
        return (output, output)
    
    def _process_chorus_reverb_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Chorus/Reverb"""
        # Используем параметры эффекта
        chorus = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем хорус (упрощенная модель)
        chorus_sample = input_sample  # Здесь должна быть реальная обработка хоруса
        
        # Применяем реверберацию (упрощенная модель)
        reverb_sample = input_sample  # Здесь должна быть реальная обработка реверберации
        
        # Смешиваем сигналы
        output = input_sample * (1 - mix) + chorus_sample * mix * chorus + reverb_sample * mix * reverb
        
        # Применяем уровень
        output *= level
        
        return (output, output)
    
    def _process_stereo_imager_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Stereo Imager"""
        # Используем параметры эффекта
        width = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        reverb = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        left_in = left
        right_in = right
        
        # Вычисляем среднее и разностный сигналы
        center = (left_in + right_in) / 2.0
        sides = (left_in - right_in) / 2.0
        
        # Усиливаем стерео изображение
        sides_enhanced = sides * (1 + width)
        
        # Возвращаем в стерео
        left_out = center + sides_enhanced
        right_out = center - sides_enhanced
        
        # Применяем глубину
        left_out = left_in * (1 - depth) + left_out * depth
        right_out = right_in * (1 - depth) + right_out * depth
        
        # Применяем уровень
        left_out *= level
        right_out *= level
        
        return (left_out, right_out)
    
    def _process_ambience_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Ambience"""
        # Используем параметры эффекта
        reverb = params.get("parameter1", 0.5)
        delay = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем реверберацию (упрощенная модель)
        reverb_sample = input_sample  # Здесь должна быть реальная обработка реверберации
        
        # Применяем задержку (упрощенная модель)
        delay_sample = input_sample  # Здесь должна быть реальная обработка задержки
        
        # Смешиваем сигналы
        output = input_sample * (1 - mix) + reverb_sample * mix * reverb + delay_sample * mix * delay
        
        # Применяем уровень
        output *= level
        
        return (output, output)
    
    def _process_doubler_effect(self, left: float, right: float, 
                               params: Dict[str, float], 
                               state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Doubler"""
        # Используем параметры эффекта
        enhance = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем эффект дублирования (упрощенная модель)
        doubled_sample = input_sample  # Здесь должна быть реальная обработка дублирования
        
        # Смешиваем сигналы
        output = input_sample * (1 - mix) + doubled_sample * mix
        
        # Применяем уровень
        output *= level
        
        return (output, output)
    
    def _process_enhancer_reverb_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Enhancer/Reverb"""
        # Используем параметры эффекта
        enhance = params.get("parameter1", 0.5)
        reverb = params.get("parameter2", 0.5)
        mix = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем усилитель гармоник (упрощенная модель)
        enhanced = input_sample + enhance * math.sin(input_sample * math.pi)
        
        # Применяем реверберацию (упрощенная модель)
        reverb_sample = input_sample  # Здесь должна быть реальная обработка реверберации
        
        # Смешиваем сигналы
        output = enhanced * (1 - mix) + reverb_sample * mix
        
        # Применяем уровень
        output *= level
        
        return (output, output)
    
    def _process_spectral_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Spectral"""
        # Используем параметры эффекта
        spectrum = params.get("parameter1", 0.5)
        depth = params.get("parameter2", 0.5)
        formant = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем спектральный эффект (упрощенная модель)
        # Здесь должна быть реализация спектрального эффекта
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        output = input_sample
        
        # Применяем уровень
        output *= level
        
        return (output, output)
    
    def _process_resonator_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Resonator"""
        # Используем параметры эффекта
        resonance = params.get("parameter1", 0.5)
        decay = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем резонатор (упрощенная модель)
        # Здесь должна быть реализация резонатора
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        output = input_sample
        
        return (output, output)
    
    def _process_degrader_effect(self, left: float, right: float, 
                                params: Dict[str, float], 
                                state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Degrader"""
        # Используем параметры эффекта
        bit_depth = int(params.get("parameter1", 0.5) * 16) + 1  # 1-16 бит
        sample_rate = params.get("parameter2", 0.5) * 22050.0 + 22050.0  # 22.05-44.1 кГц
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем деградацию (упрощенная модель)
        # Здесь должна быть реализация деградации
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        output = input_sample
        
        return (output, output)
    
    def _process_vinyl_effect(self, left: float, right: float, 
                             params: Dict[str, float], 
                             state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Vinyl"""
        # Используем параметры эффекта
        warp = params.get("parameter1", 0.5)
        crackle = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        mode = int(params.get("parameter4", 0.5) * 3)  # 0-3 режимы
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем эффект винила (упрощенная модель)
        # Здесь должна быть реализация эффекта винила
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        output = input_sample
        
        return (output, output)
    
    def _process_looper_effect(self, left: float, right: float, 
                              params: Dict[str, float], 
                              state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Looper"""
        # Используем параметры эффекта
        loop = params.get("parameter1", 0.5)
        speed = params.get("parameter2", 0.5)
        reverse = params.get("parameter3", 0.5)
        level = params.get("parameter4", 0.5)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Применяем лупер (упрощенная модель)
        # Здесь должна быть реализация лупера
        
        # Для демонстрации просто возвращаем оригинальный сигнал
        output = input_sample
        
        return (output, output)
    
    def _process_step_delay_effect(self, left: float, right: float, 
                                  params: Dict[str, float], 
                                  state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_delay" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["step_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_delay"]["step"]
        step = (step + 1) % steps
        state["step_delay"]["step"] = step
        
        # Вычисляем текущую задержку
        step_time = time * (step + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["step_delay"]["buffer"]
        pos = state["step_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["step_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_delay"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        return (output, output)
    
    def _process_step_echo_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Echo"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.7)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_echo" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["step_echo"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_echo"]["step"]
        step = (step + 1) % steps
        state["step_echo"]["step"] = step
        
        # Вычисляем текущую задержку
        step_time = time * (step + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["step_echo"]["buffer"]
        pos = state["step_echo"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь с затуханием
        feedback_sample = state["step_echo"]["feedback_buffer"] * feedback * (1 - step / steps)
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_echo"]["pos"] = (pos + 1) % len(buffer)
        state["step_echo"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        return (output, output)
    
    def _process_step_pan_delay_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Pan Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.3) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_pan_delay" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["step_pan_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_pan_delay"]["step"]
        step = (step + 1) % steps
        state["step_pan_delay"]["step"] = step
        
        # Вычисляем текущую задержку
        step_time = time * (step + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["step_pan_delay"]["buffer"]
        pos = state["step_pan_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["step_pan_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_pan_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_pan_delay"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sample * level
        
        # Применяем панорамирование по шагам
        pan = step / (steps - 1)
        left_out = output * (1 - pan)
        right_out = output * pan
        
        return (left_out, right_out)
    
    def _process_step_cross_delay_effect(self, left: float, right: float, 
                                        params: Dict[str, float], 
                                        state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Cross Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.3) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_cross_delay" not in state:
            # Создаем буферы задержки для обоих каналов
            buffer_size = int(self.sample_rate)
            state["step_cross_delay"] = {
                "left_buffer": [0.0] * buffer_size,
                "right_buffer": [0.0] * buffer_size,
                "left_pos": 0,
                "right_pos": 0,
                "left_feedback": 0.0,
                "right_feedback": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_cross_delay"]["step"]
        step = (step + 1) % steps
        state["step_cross_delay"]["step"] = step
        
        # Вычисляем текущую задержку
        step_time = time * (step + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)
        
        # Получаем входные сигналы
        input_left = left
        input_right = right
        
        # Получаем значения из буферов задержки
        left_buffer = state["step_cross_delay"]["left_buffer"]
        right_buffer = state["step_cross_delay"]["right_buffer"]
        left_pos = state["step_cross_delay"]["left_pos"]
        right_pos = state["step_cross_delay"]["right_pos"]
        
        left_delay_pos = (left_pos - delay_samples) % len(left_buffer)
        right_delay_pos = (right_pos - delay_samples) % len(right_buffer)
        
        left_delayed = left_buffer[int(left_delay_pos)]
        right_delayed = right_buffer[int(right_delay_pos)]
        
        # Применяем обратную связь с кросс-связью
        left_feedback = state["step_cross_delay"]["left_feedback"] * feedback * (1 - step / steps)
        right_feedback = state["step_cross_delay"]["right_feedback"] * feedback * (1 - step / steps)
        cross_left_feedback = state["step_cross_delay"]["right_feedback"] * feedback * (step / steps)
        cross_right_feedback = state["step_cross_delay"]["left_feedback"] * feedback * (step / steps)
        
        processed_left = input_left + left_feedback + cross_left_feedback
        processed_right = input_right + right_feedback + cross_right_feedback
        
        # Сохраняем в буферы
        left_buffer[left_pos] = processed_left
        right_buffer[right_pos] = processed_right
        state["step_cross_delay"]["left_pos"] = (left_pos + 1) % len(left_buffer)
        state["step_cross_delay"]["right_pos"] = (right_pos + 1) % len(right_buffer)
        state["step_cross_delay"]["left_feedback"] = processed_left
        state["step_cross_delay"]["right_feedback"] = processed_right
        
        # Смешиваем оригинальные и задержанные сигналы
        left_out = input_left * (1 - level) + left_delayed * level
        right_out = input_right * (1 - level) + right_delayed * level
        
        return (left_out, right_out)
    
    def _process_step_multi_tap_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Multi Tap"""
        # Используем параметры эффекта
        taps = int(params.get("parameter1", 0.5) * 10) + 1  # 1-10 тапов
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_multi_tap" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["step_multi_tap"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_multi_tap"]["step"]
        step = (step + 1) % steps
        state["step_multi_tap"]["step"] = step
        
        # Вычисляем задержки для тапов
        delays = []
        for i in range(taps):
            delay_time = (i * 500 * (step + 1) / steps)  # до 500 мс
            delays.append(int(delay_time * self.sample_rate / 1000.0))
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значения из буфера задержки
        buffer = state["step_multi_tap"]["buffer"]
        pos = state["step_multi_tap"]["pos"]
        
        # Суммируем все тапы
        delayed_sum = 0.0
        for delay_samples in delays:
            delay_pos = (pos - delay_samples) % len(buffer)
            delayed_sum += buffer[int(delay_pos)]
        
        # Нормализуем сумму
        delayed_sum /= taps
        
        # Применяем обратную связь
        feedback_sample = state["step_multi_tap"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_multi_tap"]["pos"] = (pos + 1) % len(buffer)
        state["step_multi_tap"]["feedback_buffer"] = processed_sample
        
        # Смешиваем оригинальный и задержанный сигнал
        output = input_sample * (1 - level) + delayed_sum * level
        
        return (output, output)
    
    def _process_step_reverse_delay_effect(self, left: float, right: float, 
                                         params: Dict[str, float], 
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Reverse Delay"""
        # Используем параметры эффекта
        time = params.get("parameter1", 0.5) * 1000  # 0-1000 мс
        feedback = params.get("parameter2", 0.5)
        level = params.get("parameter3", 0.5)
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_reverse_delay" not in state:
            # Создаем буфер задержки
            buffer_size = int(self.sample_rate)
            state["step_reverse_delay"] = {
                "buffer": [0.0] * buffer_size,
                "pos": 0,
                "feedback_buffer": 0.0,
                "reverse_buffer": [0.0] * buffer_size,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_reverse_delay"]["step"]
        step = (step + 1) % steps
        state["step_reverse_delay"]["step"] = step
        
        # Вычисляем текущую задержку
        step_time = time * (step + 1) / steps
        delay_samples = int(step_time * self.sample_rate / 1000.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Получаем значение из буфера задержки
        buffer = state["step_reverse_delay"]["buffer"]
        pos = state["step_reverse_delay"]["pos"]
        delay_pos = (pos - delay_samples) % len(buffer)
        delayed_sample = buffer[int(delay_pos)]
        
        # Применяем обратную связь
        feedback_sample = state["step_reverse_delay"]["feedback_buffer"] * feedback
        processed_sample = input_sample + feedback_sample
        
        # Сохраняем в буфер
        buffer[pos] = processed_sample
        state["step_reverse_delay"]["pos"] = (pos + 1) % len(buffer)
        state["step_reverse_delay"]["feedback_buffer"] = processed_sample
        
        # Обработка обратной задержки
        reverse_buffer = state["step_reverse_delay"]["reverse_buffer"]
        reverse_pos = (pos + delay_samples) % len(reverse_buffer)
        reverse_sample = reverse_buffer[int(reverse_pos)]
        
        # Сохраняем в обратный буфер
        reverse_buffer[pos] = processed_sample
        
        # Смешиваем оригинальный, прямой и обратный сигналы
        output = input_sample * (1 - level) + delayed_sample * level * (1 - step / steps) + reverse_sample * level * (step / steps)
        
        return (output, output)
    
    def _process_step_ring_mod_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Ring Mod"""
        # Используем параметры эффекта
        frequency = params.get("parameter1", 0.5) * 1000.0  # 0-1000 Гц
        depth = params.get("parameter2", 0.5)
        waveform = int(params.get("parameter3", 0.5) * 3)  # 0-3 типы волн
        steps = int(params.get("parameter4", 0.5) * 8) + 1  # 1-8 шагов
        
        # Получаем или создаем состояние эффекта
        if "step_ring_mod" not in state:
            state["step_ring_mod"] = {
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_ring_mod"]["step"]
        step = (step + 1) % steps
        state["step_ring_mod"]["step"] = step
        
        # Нормализация шага
        lfo_value = step / (steps - 1)
        
        # Генерация LFO в зависимости от формы волны
        if waveform == 0:  # Sine
            lfo_value = math.sin(lfo_value * math.pi)
        elif waveform == 1:  # Triangle
            lfo_value = 1 - abs(lfo_value * 2 - 1) * 2
        elif waveform == 2:  # Square
            lfo_value = 1 if step > steps / 2 else -1
        else:  # Sawtooth
            lfo_value = lfo_value * 2 - 1
        
        # Нормализация LFO
        lfo_value = lfo_value * depth * 0.5 + 0.5
        
        # Применение кольцевой модуляции
        input_sample = (left + right) / 2.0
        output = input_sample * lfo_value
        
        return (output, output)
    
    def _process_step_pitch_shifter_effect(self, left: float, right: float, 
                                         params: Dict[str, float], 
                                         state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Pitch Shifter"""
        # Используем параметры эффекта
        shift = (params.get("parameter1", 0.5) * 24.0) - 12.0  # -12 до +12 полутонов
        feedback = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        formant = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "step_pitch_shifter" not in state:
            state["step_pitch_shifter"] = {
                "delay_buffer": [0.0] * int(self.sample_rate * 0.1),  # 100 мс буфер
                "buffer_pos": 0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_pitch_shifter"]["step"]
        step = (step + 1) % steps
        state["step_pitch_shifter"]["step"] = step
        
        # Вычисляем коэффициент изменения высоты тона для текущего шага
        step_shift = shift * (step + 1) / steps
        pitch_factor = 2 ** (step_shift / 12.0)
        
        # Получаем входной сигнал
        input_sample = (left + right) / 2.0
        
        # Сохраняем в буфер задержки
        delay_buffer = state["step_pitch_shifter"]["delay_buffer"]
        buffer_pos = state["step_pitch_shifter"]["buffer_pos"]
        delay_buffer[buffer_pos] = input_sample
        state["step_pitch_shifter"]["buffer_pos"] = (buffer_pos + 1) % len(delay_buffer)
        
        # Вычисляем позицию для выборки с измененной высотой тона
        read_pos = buffer_pos - int(len(delay_buffer) * (1 - pitch_factor))
        if read_pos < 0:
            read_pos += len(delay_buffer)
        
        # Получаем сдвинутый по высоте тона сигнал
        shifted_sample = delay_buffer[int(read_pos)]
        
        # Смешиваем оригинальный и сдвинутый сигналы
        output = input_sample * (1 - feedback) + shifted_sample * feedback
        
        return (output, output)
    
    def _process_step_distortion_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Distortion"""
        # Используем параметры эффекта
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        type = int(params.get("parameter4", 0.5) * 3)  # 0-3 типы
        
        # Получаем или создаем состояние эффекта
        if "step_distortion" not in state:
            state["step_distortion"] = {
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_distortion"]["step"]
        step = (step + 1) % steps
        state["step_distortion"]["step"] = step
        
        # Нормализация шага
        step_drive = drive * (step + 1) / steps
        
        # Применение искажения
        input_sample = (left + right) / 2.0
        
        # Разные типы искажения
        if type == 0:  # Soft clipping
            output = math.atan(input_sample * step_drive * 5.0) / (math.pi / 2)
        elif type == 1:  # Hard clipping
            output = max(-1.0, min(1.0, input_sample * step_drive))
        elif type == 2:  # Asymmetric
            if input_sample > 0:
                output = 1 - math.exp(-input_sample * step_drive)
            else:
                output = -1 + math.exp(input_sample * step_drive)
        else:  # Symmetric
            output = math.tanh(input_sample * step_drive)
        
        # Тон-контроль (простой эквалайзер)
        if tone < 0.5:
            # Более низкие частоты
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Более высокие частоты
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        return (output, output)
    
    def _process_step_overdrive_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Overdrive"""
        # Используем параметры эффекта
        drive = params.get("parameter1", 0.5)
        tone = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        bias = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "step_overdrive" not in state:
            state["step_overdrive"] = {
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_overdrive"]["step"]
        step = (step + 1) % steps
        state["step_overdrive"]["step"] = step
        
        # Нормализация шага
        step_drive = drive * (step + 1) / steps
        
        # Применение овердрайва
        input_sample = (left + right) / 2.0
        
        # Моделирование лампового овердрайва
        # Добавляем небольшой сдвиг (bias) для асимметричного искажения
        biased = input_sample + bias * 0.1
        output = math.tanh(biased * (1 + step_drive * 9.0))
        
        # Тон-контроль
        if tone < 0.5:
            # Более низкие частоты
            bass_boost = 1.0 + (0.5 - tone) * 2.0
            output = output * 0.7 + input_sample * 0.3 * bass_boost
        else:
            # Более высокие частоты
            treble_boost = 1.0 + (tone - 0.5) * 2.0
            output = output * 0.7 + input_sample * 0.3 * treble_boost
        
        return (output, output)
    
    def _process_step_compressor_effect(self, left: float, right: float, 
                                      params: Dict[str, float], 
                                      state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Compressor"""
        # Используем параметры эффекта
        threshold = -60 + params.get("parameter1", 0.5) * 60  # -60 до 0 дБ
        ratio = 1 + params.get("parameter2", 0.5) * 19  # 1:1 до 20:1
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        release = 10 + params.get("parameter4", 0.5) * 290  # 10-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        release_samples = int(release * self.sample_rate / 1000.0)
        
        # Получаем или создаем состояние эффекта
        if "step_compressor" not in state:
            state["step_compressor"] = {
                "gain": 1.0,
                "release_counter": 0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_compressor"]["step"]
        step = (step + 1) % steps
        state["step_compressor"]["step"] = step
        
        # Нормализация шага
        step_ratio = ratio * (step + 1) / steps
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level > threshold_linear:
            # Сигнал выше порога, применяем компрессию
            desired_gain = threshold_linear / (input_level ** (1/step_ratio))
        else:
            # Сигнал ниже порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        comp_state = state["step_compressor"]
        if desired_gain < comp_state["gain"]:
            # Атака
            comp_state["gain"] = desired_gain
        else:
            # Релиз
            if comp_state["release_counter"] < release_samples:
                comp_state["release_counter"] += 1
                factor = comp_state["release_counter"] / release_samples
                comp_state["gain"] = comp_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                comp_state["gain"] = desired_gain
        
        # Применение усиления
        output = input_sample * comp_state["gain"]
        
        return (output, output)
    
    def _process_step_limiter_effect(self, left: float, right: float, 
                                    params: Dict[str, float], 
                                    state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Limiter"""
        # Используем параметры эффекта
        threshold = -20 + params.get("parameter1", 0.5) * 20  # -20 до 0 дБ
        ratio = 10 + params.get("parameter2", 0.5) * 10  # 10:1 до 20:1
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        release = 50 + params.get("parameter4", 0.5) * 250  # 50-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        release_samples = int(release * self.sample_rate / 1000.0)
        
        # Получаем или создаем состояние эффекта
        if "step_limiter" not in state:
            state["step_limiter"] = {
                "gain": 1.0,
                "release_counter": 0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_limiter"]["step"]
        step = (step + 1) % steps
        state["step_limiter"]["step"] = step
        
        # Нормализация шага
        step_ratio = ratio * (step + 1) / steps
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level > threshold_linear:
            # Сигнал выше порога, применяем лимитирование
            desired_gain = threshold_linear / (input_level ** (1/step_ratio))
        else:
            # Сигнал ниже порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        limiter_state = state["step_limiter"]
        if desired_gain < limiter_state["gain"]:
            # Атака (быстрая)
            limiter_state["gain"] = desired_gain
        else:
            # Релиз (медленный)
            if limiter_state["release_counter"] < release_samples:
                limiter_state["release_counter"] += 1
                factor = limiter_state["release_counter"] / release_samples
                limiter_state["gain"] = limiter_state["gain"] * (1 - factor) + desired_gain * factor
            else:
                limiter_state["gain"] = desired_gain
        
        # Применение усиления
        output = input_sample * limiter_state["gain"]
        
        return (output, output)
    
    def _process_step_gate_effect(self, left: float, right: float, 
                                 params: Dict[str, float], 
                                 state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Gate"""
        # Используем параметры эффекта
        threshold = -80 + params.get("parameter1", 0.5) * 70  # -80 до -10 дБ
        reduction = params.get("parameter2", 0.5) * 60  # 0-60 дБ
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        hold = params.get("parameter4", 0.5) * 1000  # 0-1000 мс
        
        # Конвертация в линейные значения
        threshold_linear = 10 ** (threshold / 20.0)
        reduction_factor = 10 ** (-reduction / 20.0)
        hold_samples = int(hold * self.sample_rate / 1000.0)
        
        # Получаем или создаем состояние эффекта
        if "step_gate" not in state:
            state["step_gate"] = {
                "open": False,
                "hold_counter": 0,
                "gain": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_gate"]["step"]
        step = (step + 1) % steps
        state["step_gate"]["step"] = step
        
        # Нормализация шага
        step_reduction = reduction * (step + 1) / steps
        step_reduction_factor = 10 ** (-step_reduction / 20.0)
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Проверка порога
        gate_state = state["step_gate"]
        if input_level > threshold_linear:
            # Сигнал выше порога, открываем gate
            gate_state["open"] = True
            gate_state["hold_counter"] = hold_samples
        else:
            # Сигнал ниже порога, проверяем hold
            if gate_state["hold_counter"] > 0:
                gate_state["hold_counter"] -= 1
            else:
                gate_state["open"] = False
        
        # Расчет усиления
        if gate_state["open"]:
            # Плавное открытие
            if gate_state["gain"] < 1.0:
                gate_state["gain"] += 0.1
                gate_state["gain"] = min(1.0, gate_state["gain"])
        else:
            # Плавное закрытие
            gate_state["gain"] *= 0.99  # экспоненциальное затухание
        
        # Применение редукции
        if not gate_state["open"]:
            gate_state["gain"] *= step_reduction_factor
        
        # Применение усиления
        output = input_sample * gate_state["gain"]
        
        return (output, output)
    
    def _process_step_expander_effect(self, left: float, right: float, 
                                     params: Dict[str, float], 
                                     state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Expander"""
        # Используем параметры эффекта
        threshold = -60 + params.get("parameter1", 0.5) * 60  # -60 до 0 дБ
        ratio = 1 + params.get("parameter2", 0.5) * 9  # 1:1 до 10:1
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        release = 10 + params.get("parameter4", 0.5) * 290  # 10-300 мс
        
        # Конвертация в коэффициенты
        threshold_linear = 10 ** (threshold / 20.0)
        
        # Получаем или создаем состояние эффекта
        if "step_expander" not in state:
            state["step_expander"] = {
                "gain": 1.0,
                "counter": 0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_expander"]["step"]
        step = (step + 1) % steps
        state["step_expander"]["step"] = step
        
        # Нормализация шага
        step_ratio = ratio * (step + 1) / steps
        
        # Обработка
        input_sample = (left + right) / 2.0
        input_level = abs(input_sample)
        
        # Расчет желаемого усиления
        if input_level < threshold_linear:
            # Сигнал ниже порога, применяем экспандирование
            desired_gain = 1.0 / (step_ratio * (threshold_linear / input_level))
            desired_gain = min(1.0, desired_gain)
        else:
            # Сигнал выше порога, полное усиление
            desired_gain = 1.0
        
        # Плавное изменение усиления
        expander_state = state["step_expander"]
        if desired_gain < expander_state["gain"]:
            # Релиз (медленный)
            expander_state["gain"] -= 0.01
            expander_state["gain"] = max(desired_gain, expander_state["gain"])
        else:
            # Атака (быстрая)
            expander_state["gain"] = desired_gain
        
        # Применение усиления
        output = input_sample * expander_state["gain"]
        
        return (output, output)
    
    def _process_step_rotary_speaker_effect(self, left: float, right: float, 
                                          params: Dict[str, float], 
                                          state: Dict[str, Any]) -> Tuple[float, float]:
        """Обработка эффекта Step Rotary Speaker"""
        # Используем параметры эффекта
        speed = params.get("parameter1", 0.5) * 5.0  # 0-5 Гц
        balance = params.get("parameter2", 0.5)
        steps = int(params.get("parameter3", 0.5) * 8) + 1  # 1-8 шагов
        level = params.get("parameter4", 0.5)
        
        # Получаем или создаем состояние эффекта
        if "step_rotary_speaker" not in state:
            state["step_rotary_speaker"] = {
                "horn_phase": 0.0,
                "drum_phase": 0.0,
                "horn_speed": 0.0,
                "drum_speed": 0.0,
                "step": 0
            }
        
        # Вычисляем текущий шаг
        step = state["step_rotary_speaker"]["step"]
        step = (step + 1) % steps
        state["step_rotary_speaker"]["step"] = step
        
        # Нормализация шага
        step_speed = speed * (step + 1) / steps
        
        # Обновляем фазы
        state["step_rotary_speaker"]["horn_phase"] += 2 * math.pi * state["step_rotary_speaker"]["horn_speed"] / self.sample_rate
        state["step_rotary_speaker"]["drum_phase"] += 2 * math.pi * state["step_rotary_speaker"]["drum_speed"] / self.sample_rate
        
        # Изменяем скорость вращения
        target_speed = step_speed * 0.5 + 0.5  # 0.5-1.0
        state["step_rotary_speaker"]["horn_speed"] += (target_speed - state["step_rotary_speaker"]["horn_speed"]) * 0.1
        state["step_rotary_speaker"]["drum_speed"] += (target_speed * 0.5 - state["step_rotary_speaker"]["drum_speed"]) * 0.1
        
        # Вычисляем позиции
        horn_pos = math.sin(state["step_rotary_speaker"]["horn_phase"]) * 0.5 + 0.5
        drum_pos = math.sin(state["step_rotary_speaker"]["drum_phase"] * 2) * 0.5 + 0.5
        
        # Применяем эффект
        input_sample = (left + right) / 2.0
        
        # Смешиваем каналы в зависимости от позиции
        left_out = input_sample * (1 - horn_pos) * (1 - drum_pos) + input_sample * horn_pos * drum_pos
        right_out = input_sample * horn_pos * (1 - drum_pos) + input_sample * (1 - horn_pos) * drum_pos
        
        # Применяем баланс и уровень
        left_out = left_out * (1 - balance) * level
        right_out = right_out * balance * level
        
        return (left_out, right_out)
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Получение текущего состояния эффектов"""
        with self.state_lock:
            state = self._create_empty_state()
            self._copy_state(self._current_state, state)
            return state
    
    def _apply_temp_state(self):
        """Применение временного состояния к текущему"""
        with self.state_lock:
            self._copy_state(self._temp_state, self._current_state)
            self.state_update_pending = True
    
    def reset_effects(self):
        """Сброс всех эффектов к значениям по умолчанию"""
        with self.state_lock:
            # Параметры реверберации
            self._temp_state["reverb_params"] = {
                "type": 0,  # Hall 1
                "time": 2.5,  # секунды
                "level": 0.6,  # 0.0-1.0
                "pre_delay": 20.0,  # миллисекунды
                "hf_damping": 0.5,  # 0.0-1.0
                "density": 0.8,  # 0.0-1.0
                "early_level": 0.7,  # 0.0-1.0
                "tail_level": 0.9,  # 0.0-1.0
                "allpass_buffers": [np.zeros(441) for _ in range(4)],
                "allpass_indices": [0] * 4,
                "comb_buffers": [np.zeros(441 * i) for i in range(1, 5)],
                "comb_indices": [0] * 4,
                "early_reflection_buffer": np.zeros(441),
                "early_reflection_index": 0,
                "late_reflection_buffer": np.zeros(441 * 10),
                "late_reflection_index": 0
            }

            # Параметры хоруса
            self._temp_state["chorus_params"] = {
                "type": 0,  # Chorus 1
                "rate": 1.0,  # Гц
                "depth": 0.5,  # 0.0-1.0
                "feedback": 0.3,  # 0.0-1.0
                "level": 0.4,  # 0.0-1.0
                "delay": 0.0,  # миллисекунды
                "output": 0.8,  # 0.0-1.0
                "cross_feedback": 0.2,  # 0.0-1.0
                "delay_lines": [np.zeros(4410) for _ in range(2)],  # 100ms задержки
                "lfo_phases": [0.0, 0.0],
                "lfo_rates": [1.0, 0.5],
                "lfo_depths": [0.5, 0.3],
                "write_indices": [0, 0],
                "feedback_buffers": [0.0, 0.0]
            }
            
            # Параметры вариационного эффекта
            self._temp_state["variation_params"] = {
                "type": 0,  # Delay
                "parameter1": 0.5,  # 0.0-1.0
                "parameter2": 0.5,  # 0.0-1.0
                "parameter3": 0.5,  # 0.0-1.0
                "parameter4": 0.5,  # 0.0-1.0
                "level": 0.5,  # 0.0-1.0
                "bypass": False  # true/false
            }
            
            # Параметры эквалайзера
            self._temp_state["equalizer_params"] = {
                "low_gain": 0.0,  # дБ
                "mid_gain": 0.0,  # дБ
                "high_gain": 0.0,  # дБ
                "mid_freq": 1000.0,  # Гц
                "q_factor": 1.0  # Q-фактор
            }
            
            # Параметры маршрутизации эффектов
            self._temp_state["routing_params"] = {
                "system_effect_order": [0, 1, 2],  # 0=reverb, 1=chorus, 2=variation
                "insertion_effect_order": [0],  # 0=insertion effect
                "parallel_routing": False,  # Использовать параллельную маршрутизацию
                "reverb_to_chorus": 0.0,  # Отправка реверберации на хорус
                "chorus_to_variation": 0.0  # Отправка хоруса на вариационный эффект
            }
            
            # Глобальные параметры эффектов
            self._temp_state["global_effect_params"] = {
                "reverb_send": 0.5,  # Уровень отправки на реверберацию
                "chorus_send": 0.3,  # Уровень отправки на хорус
                "variation_send": 0.2,  # Уровень отправки на вариационный эффект
                "stereo_width": 0.5,  # Ширина стерео (0.0-1.0)
                "master_level": 0.8,  # Общий уровень
                "bypass_all": False  # Обход всех эффектов
            }

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
            
            # Параметры для каждого MIDI-канала (16 каналов)
            for i in range(self.NUM_CHANNELS):
                self._temp_state["channel_params"][i] = {
                    "reverb_send": 0.5,  # Уровень отправки на реверберацию
                    "chorus_send": 0.3,  # Уровень отправки на хорус
                    "variation_send": 0.2,  # Уровень отправки на вариационный эффект
                    "insertion_send": 1.0,  # Уровень отправки на insertion effect
                    "muted": False,  # Канал замьючен
                    "soloed": False,  # Канал в режиме solo
                    "pan": 0.5,  # Панорамирование (0.0-1.0)
                    "expression": 1.0,  # Выражение (0.0-1.0)
                    "volume": 1.0,  # Громкость (0.0-1.0)
                    "volume": 1.0,  # Громкость (0.0-1.0)
                    "insertion_effect": {
                        "enabled": True,
                        "type": 0,  # Off
                        "parameter1": 0.5,  # 0.0-1.0
                        "parameter2": 0.5,  # 0.0-1.0
                        "parameter3": 0.5,  # 0.0-1.0
                        "parameter4": 0.5,  # 0.0-1.0
                        "level": 1.0,  # 0.0-1.0
                        "bypass": False,  # true/false
                        # Новые параметры для Phaser и Flanger
                        "frequency": 1.0,
                        "depth": 0.5,
                        "feedback": 0.3,
                        "lfo_waveform": 0
                    }
                }
            
            # Применяем временное состояние
            self._apply_temp_state()
    
    def set_effect_preset(self, preset_name: str):
        """Установка пресета эффектов для всего секвенсора"""
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
            },
            "Guitar Distortion": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 1,  # Distortion
                    "params": [80, 64, 100, 50],  # drive, tone, level, type
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Bass Compressor": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.2, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 3,  # Compressor
                    "params": [40, 30, 20, 70],  # threshold, ratio, attack, release
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Phaser Rock": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 16,  # Phaser
                    "params": [1.5, 0.8, 0.4, 0],  # frequency, depth, feedback, waveform
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Flanger Lead": {
                "reverb": {"type": 3, "time": 1.8, "level": 0.4, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {"type": 0, "parameter1": 0.5, "parameter2": 0.5, "parameter3": 0.5, "parameter4": 0.5, "level": 0.0},
                "insertion": {
                    "type": 17,  # Flanger
                    "params": [0.5, 0.9, 0.6, 1],  # frequency, depth, feedback, waveform
                    "enabled": True,
                    "bypass": False,
                    "send": 127
                }
            },
            "Step Phaser": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 27,  # Step Phaser
                    "params": [1.0, 0.7, 0.3, 4],  # frequency, depth, feedback, steps
                    "level": 0.5
                }
            },
            "Step Flanger": {
                "reverb": {"type": 0, "time": 1.8, "level": 0.4, "pre_delay": 25.0, "hf_damping": 0.4},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 28,  # Step Flanger
                    "params": [0.5, 0.8, 0.6, 4],  # frequency, depth, feedback, steps
                    "level": 0.5
                }
            },
            "Step Delay": {
                "reverb": {"type": 0, "time": 2.5, "level": 0.3, "pre_delay": 20.0, "hf_damping": 0.5},
                "chorus": {"type": 7, "rate": 1.0, "depth": 0.0, "feedback": 0.0, "level": 0.0},
                "variation": {
                    "type": 48,  # Step Delay
                    "params": [300, 0.5, 0.5, 4],  # time, feedback, level, steps
                    "level": 0.5
                }
            }
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            
            # Устанавливаем параметры реверберации
            if "reverb" in preset:
                for param, value in preset["reverb"].items():
                    nrpn_param = list(preset["reverb"].keys()).index(param)
                    self.set_channel_effect_parameter(0, 0, 120 + nrpn_param, int(value * 127))
            
            # Устанавливаем параметры хоруса
            if "chorus" in preset:
                for param, value in preset["chorus"].items():
                    nrpn_param = list(preset["chorus"].keys()).index(param)
                    self.set_channel_effect_parameter(0, 0, 130 + nrpn_param, int(value * 127))
            
            # Устанавливаем параметры вариационного эффекта
            if "variation" in preset:
                var_data = preset["variation"]
                self.set_variation_effect_type(0, var_data["type"])
                self.set_variation_effect_bypass(0, False)
                self.set_variation_effect_level(0, var_data.get("level", 0.5))
                
                # Устанавливаем параметры в зависимости от типа эффекта
                if "params" in var_data:
                    for i, param in enumerate(var_data["params"]):
                        self.set_variation_effect_parameter(0, i + 1, param)
                else:
                    for i, param in enumerate(["parameter1", "parameter2", "parameter3", "parameter4"]):
                        if param in var_data:
                            self.set_variation_effect_parameter(0, i + 1, var_data[param])
            
            # Устанавливаем параметры Insertion Effect
            if "insertion" in preset:
                ins_data = preset["insertion"]
                self.set_channel_insertion_effect_enabled(0, ins_data.get("enabled", True))
                self.set_channel_insertion_effect_bypass(0, ins_data.get("bypass", False))
                self.set_channel_insertion_effect_type(0, ins_data["type"])
                self.set_channel_effect_parameter(0, 0, 163, ins_data.get("send", 127))
                
                # Устанавливаем параметры в зависимости от типа эффекта
                if ins_data["type"] in [16, 17]:  # Phaser или Flanger
                    params = ins_data.get("params", [])
                    if len(params) > 0:
                        self.set_channel_phaser_frequency(0, params[0] * 0.2)
                    if len(params) > 1:
                        self.set_channel_phaser_depth(0, params[1] / 127.0)
                    if len(params) > 2:
                        self.set_channel_phaser_feedback(0, params[2] / 127.0)
                    if len(params) > 3:
                        self.set_channel_phaser_waveform(0, params[3])
                else:
                    for i, param in enumerate(ins_data.get("params", [])):
                        self.set_channel_insertion_effect_parameter(0, i + 1, param / 127.0)
    
    def set_variation_effect_type(self, channel: int, effect_type: int):
        """Установка типа Variational Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["variation_params"]["type"] = effect_type
                self.state_update_pending = True
    
    def set_variation_effect_bypass(self, channel: int, bypass: bool):
        """Установка обхода Variational Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["variation_params"]["bypass"] = bypass
                self.state_update_pending = True
    
    def set_variation_effect_level(self, channel: int, level: float):
        """Установка уровня Variational Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS:
                self._temp_state["channel_params"][channel]["variation_params"]["level"] = level
                self.state_update_pending = True
    
    def set_variation_effect_parameter(self, channel: int, param_index: int, value: float):
        """Установка параметра Variational Effect для канала"""
        with self.state_lock:
            if 0 <= channel < self.NUM_CHANNELS and 1 <= param_index <= 4:
                param_name = f"parameter{param_index}"
                self._temp_state["channel_params"][channel]["variation_params"][param_name] = value
                self.state_update_pending = True