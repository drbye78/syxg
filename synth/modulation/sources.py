"""
Modulation sources for XG synthesizer.
Defines all available modulation sources.
"""

from typing import List


class ModulationSource:
    """Class representing modulation source"""
    VELOCITY = "velocity"
    AFTER_TOUCH = "after_touch"
    MOD_WHEEL = "mod_wheel"
    LFO1 = "lfo1"
    LFO2 = "lfo2"
    LFO3 = "lfo3"
    AMP_ENV = "amp_env"
    FILTER_ENV = "filter_env"
    PITCH_ENV = "pitch_env"
    KEY_PRESSURE = "key_pressure"
    BRIGHTNESS = "brightness"
    HARMONIC_CONTENT = "harmonic_content"
    PORTAMENTO = "portamento"
    VIBRATO = "vibrato"
    TREMOLO = "tremolo"
    TREMOLO_DEPTH = "tremolo_depth"
    TREMOLO_RATE = "tremolo_rate"
    NOTE_NUMBER = "note_number"

    # New sources from SoundFont
    BREATH_CONTROLLER = "breath_controller"
    FOOT_CONTROLLER = "foot_controller"
    DATA_ENTRY = "data_entry"
    VOLUME_CC = "volume_cc"
    BALANCE = "balance"
    PORTAMENTO_TIME_CC = "portamento_time_cc"

    @staticmethod
    def get_all_sources():
        return [
            ModulationSource.VELOCITY,
            ModulationSource.AFTER_TOUCH,
            ModulationSource.MOD_WHEEL,
            ModulationSource.LFO1,
            ModulationSource.LFO2,
            ModulationSource.LFO3,
            ModulationSource.AMP_ENV,
            ModulationSource.FILTER_ENV,
            ModulationSource.PITCH_ENV,
            ModulationSource.KEY_PRESSURE,
            ModulationSource.BRIGHTNESS,
            ModulationSource.HARMONIC_CONTENT,
            ModulationSource.PORTAMENTO,
            ModulationSource.VIBRATO,
            ModulationSource.TREMOLO,
            ModulationSource.TREMOLO_DEPTH,
            ModulationSource.TREMOLO_RATE,
            ModulationSource.NOTE_NUMBER,
            ModulationSource.BREATH_CONTROLLER,
            ModulationSource.FOOT_CONTROLLER,
            ModulationSource.DATA_ENTRY,
            ModulationSource.VOLUME_CC,
            ModulationSource.BALANCE,
            ModulationSource.PORTAMENTO_TIME_CC
        ]
