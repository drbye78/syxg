"""
Partial generator implementation for XG synthesizer.
Handles individual partial structures within a tone.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from ..core.vectorized_envelope import VectorizedADSREnvelope
from ..core.filter import ResonantFilter
from ..core.panner import StereoPanner


class PartialGenerator:
    """
    Частичный генератор в соответствии с концепцией Partial Structure XG.
    Каждый PartialGenerator отвечает за одну частичную структуру в общем тоне.
    """
    def __init__(self, wavetable, note, velocity, program, partial_id,
                 partial_params, is_drum=False, sample_rate=44100, bank=0):
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
        self.bank = bank
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
        self.initial_attenuation = partial_params.get("initial_attenuation", 0.0)  # in dB
        self.scale_tuning = partial_params.get("scale_tuning", 100)  # in cents
        self.overriding_root_key = partial_params.get("overriding_root_key", -1)
        self.start_coarse = partial_params.get("start_coarse", 0)
        self.end_coarse = partial_params.get("end_coarse", 0)
        self.start_loop_coarse = partial_params.get("start_loop_coarse", 0)
        self.end_loop_coarse = partial_params.get("end_loop_coarse", 0)

        # Проверка, попадает ли нота в диапазон частичной структуры
        if not (self.key_range_low <= note <= self.key_range_high):
            self.active = False
            self.amp_envelope = None
            self.filter_envelope = None
            self.pitch_envelope = None
            self.filter = None
            return

        # Проверка, попадает ли velocity в диапазон частичной структуры
        if not (self.velocity_range_low <= velocity <= self.velocity_range_high):
            self.active = False
            self.amp_envelope = None
            self.filter_envelope = None
            self.pitch_envelope = None
            self.filter = None
            return

        # Инициализация фазы
        self.phase = 0.0
        self._update_phase_step()

        # Инициализация огибающих
        self.amp_envelope = VectorizedADSREnvelope(
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
            self.filter_envelope = VectorizedADSREnvelope(
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
            self.pitch_envelope = VectorizedADSREnvelope(
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
        # Check if wavetable is available
        if self.wavetable is None:
            # Use basic sine wave generation when no wavetable is available
            self.active = True
            # Calculate basic frequency for sine wave
            root_key = self.overriding_root_key if self.overriding_root_key >= 0 else self.note
            base_freq = 440.0 * (2 ** ((root_key - 69) / 12.0))
            tuning_multiplier = 2 ** (self.scale_tuning / 1200.0)
            base_freq *= tuning_multiplier
            pitch_factor = 2 ** ((self.note - 60) * self.key_scaling / 1200.0)
            final_freq = base_freq * pitch_factor
            # For basic sine wave, we don't need a table, just set phase step
            self.phase_step = final_freq / self.sample_rate * 2 * 3.14159  # 2π for sine wave
            return

        # Получение сэмпла из wavetable для этой частичной структуры
        table = self.wavetable.get_partial_table(self.note, self.program, self.partial_id, self.velocity, self.bank)
        if table is None or len(table) == 0:
            self.active = False
            return

        # Determine the root key to use
        root_key = self.overriding_root_key if self.overriding_root_key >= 0 else self.note

        # Базовая частота для текущей ноты с учетом scale tuning
        base_freq = 440.0 * (2 ** ((root_key - 69) / 12.0))

        # Apply scale tuning (convert cents to frequency multiplier)
        tuning_multiplier = 2 ** (self.scale_tuning / 1200.0)
        base_freq *= tuning_multiplier

        # Учет key scaling (зависимость pitch от высоты ноты)
        pitch_factor = 2 ** ((self.note - 60) * self.key_scaling / 1200.0)
        final_freq = base_freq * pitch_factor

        table_length = len(table)
        self.phase_step = final_freq / self.sample_rate * table_length

    def is_active(self):
        """Проверка, активен ли частичный генератор"""
        return self.active and self.amp_envelope and self.amp_envelope.state != "idle"

    def note_off(self):
        """Обработка события Note Off"""
        if self.is_active():
            if self.amp_envelope:
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
        amp_env = self.amp_envelope.process() if self.amp_envelope else 0.0
        if amp_env <= 0:
            # self.active = False
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

        # Handle wavetable vs basic generation
        if self.wavetable is None:
            # Basic sine wave generation
            self.phase += self.phase_step
            if self.phase >= 2 * 3.14159:  # Keep phase in 0-2π range
                self.phase -= 2 * 3.14159

            # Generate sine wave sample
            sample_val = math.sin(self.phase)
            sample = sample_val
            is_stereo = False
        else:
            # Обновление phase_step для текущего сэмпла
            table = self.wavetable.get_partial_table(self.note, self.program, self.partial_id, self.velocity, self.bank)
            if not table or len(table) == 0:
                # self.active = False
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
        if self.filter:
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
        else:
            filtered_sample = sample

        # Применение огибающей амплитуды
        amp_env = self.amp_envelope.process() if self.amp_envelope else 0.0

        # Применение уровня частичной структуры с учетом кросс-фейда
        effective_level = self.level

        # Учет кросс-фейда по velocity
        if self.crossfade_velocity:
            effective_level *= (1.0 - self.velocity_crossfade)

        # Учет кросс-фейда по ноте
        if self.crossfade_note:
            effective_level *= (1.0 - self.note_crossfade)

        # Apply initial attenuation (convert dB to linear scale)
        attenuation_factor = 10 ** (-self.initial_attenuation / 20.0)
        effective_level *= attenuation_factor

        if is_stereo:
            if isinstance(filtered_sample, (tuple, list)) and len(filtered_sample) >= 2:
                left_out = filtered_sample[0] * amp_env * effective_level
                right_out = filtered_sample[1] * amp_env * effective_level
            else:
                # Handle stereo format mismatch
                mono_sample = (filtered_sample if isinstance(filtered_sample, (int, float)) else 0.0) * amp_env * effective_level
                left_out = mono_sample
                right_out = mono_sample
        else:
            # Handle both wavetable mono samples and basic sine wave generation
            if isinstance(filtered_sample, (tuple, list)) and len(filtered_sample) >= 2:
                mono_sample = (filtered_sample[0] + filtered_sample[1]) * 0.5 * amp_env * effective_level
            else:
                # Basic sine wave case - filtered_sample is a float
                mono_sample = (filtered_sample if isinstance(filtered_sample, (int, float)) else 0.0) * amp_env * effective_level

        # Применение панорамирования для этой частичной структуры
        panner = StereoPanner(pan_position=self.pan, sample_rate=self.sample_rate)
        left_out, right_out = panner.process(mono_sample)

        return (left_out, right_out)

    # XG Synthesis Parameter Control Methods
    def set_harmonic_content(self, value: float):
        """Set harmonic content parameter (XG Sound Controller 71) - affects timbre/harmonic structure"""
        if self.filter and hasattr(self.filter, 'set_harmonic_content'):
            # Scale 0.0-1.0 to appropriate filter parameter range
            normalized_value = max(0.0, min(1.0, value))
            self.filter.set_harmonic_content(normalized_value)

    def set_brightness(self, value: float):
        """Set brightness parameter (XG Sound Controller 72) - affects filter cutoff/brightness"""
        if self.filter and hasattr(self.filter, 'set_brightness'):
            # Scale 0.0-1.0 to 0-127 MIDI range
            midi_value = int(value * 127.0)
            midi_value = max(0, min(127, midi_value))
            self.filter.set_brightness(midi_value)

    def set_release_time(self, value: float):
        """Set release time parameter (XG Sound Controller 73) - affects envelope release"""
        if self.amp_envelope:
            # Scale 0.0-1.0 to release time range (0.001-2.0 seconds)
            release_time = 0.001 + (value * 1.999)
            self.amp_envelope.update_parameters(release=release_time)
        if self.filter_envelope:
            self.filter_envelope.update_parameters(release=max(0.001, value * 2.0))

    def set_attack_time(self, value: float):
        """Set attack time parameter (XG Sound Controller 74) - affects envelope attack"""
        if self.amp_envelope:
            # Scale 0.0-1.0 to attack time range (0.001-1.0 seconds)
            attack_time = 0.001 + (value * 0.999)
            self.amp_envelope.update_parameters(attack=attack_time)
        if self.filter_envelope:
            self.filter_envelope.update_parameters(attack=max(0.001, value * 1.0))

    def set_decay_time(self, value: float):
        """Set decay time parameter (XG Sound Controller 76) - affects envelope decay"""
        if self.amp_envelope:
            # Scale 0.0-1.0 to decay time range (0.001-5.0 seconds)
            decay_time = 0.001 + (value * 4.999)
            self.amp_envelope.update_parameters(decay=decay_time)
        if self.filter_envelope:
            self.filter_envelope.update_parameters(decay=max(0.001, value * 5.0))

    def set_filter_cutoff(self, value: float):
        """Set filter cutoff frequency (XG Sound Controller 75) - affects filter cutoff"""
        if self.filter:
            # Scale 0.0-1.0 to cutoff frequency range (20Hz-20kHz)
            cutoff_freq = 20.0 + (value ** 2) * (20000.0 - 20.0)  # Exponential scaling
            self.filter.set_parameters(cutoff=cutoff_freq)

    def set_filter_resonance(self, value: float):
        """Set filter resonance (additional XG parameter) - affects filter Q factor"""
        if self.filter:
            # Scale 0.0-1.0 to resonance range (0.0-2.0)
            resonance = value * 2.0
            self.filter.set_parameters(resonance=resonance)

    def update_attack_rate(self, rate: float):
        """Update attack rate continuously for real-time control"""
        self.set_attack_time(rate)

    def update_decay_rate(self, rate: float):
        """Update decay rate continuously for real-time control"""
        self.set_decay_time(rate)

    def update_release_rate(self, rate: float):
        """Update release rate continuously for real-time control"""
        self.set_release_time(rate)
