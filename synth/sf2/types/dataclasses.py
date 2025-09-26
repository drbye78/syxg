import struct
import numpy as np
import os
import warnings
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass


class SF2Modulator:
    """Represents a modulator in SoundFont 2.0"""
    __slots__ = [
        'source_oper', 'source_polarity', 'source_type', 'source_direction', 'source_index',
        'control_oper', 'control_polarity', 'control_type', 'control_direction', 'control_index',
        'destination', 'amount', 'amount_source_oper', 'amount_source_polarity',
        'amount_source_type', 'amount_source_direction', 'amount_source_index', 'transform'
    ]

    def __init__(self):
        # Modulation source
        self.source_oper = 0  # Source Operator
        self.source_polarity = 0  # 0 = unipolar, 1 = bipolar
        self.source_type = 0  # 0 = linear, 1 = concave
        self.source_direction = 0  # 0 = max -> min, 1 = min -> max
        self.source_index = 0  # Source index (for CC)

        # Modulation control
        self.control_oper = 0  # Control Operator
        self.control_polarity = 0
        self.control_type = 0
        self.control_direction = 0
        self.control_index = 0

        # Modulation target
        self.destination = 0  # Destination Generator

        # Modulation depth
        self.amount = 0  # Depth value

        # Modulation depth source
        self.amount_source_oper = 0
        self.amount_source_polarity = 0
        self.amount_source_type = 0
        self.amount_source_direction = 0
        self.amount_source_index = 0

        # Transform
        self.transform = 0  # Transform Operator

class SF2InstrumentZone:
    """Represents an instrument zone in SoundFont 2.0"""
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
        'mod_ndx', 'gen_ndx', 'generators', 'sample_modes', 'exclusive_class',
        'start', 'end', 'start_loop', 'end_loop', 'reverb_send', 'chorus_send',
        'scale_tuning', 'start_coarse', 'end_coarse', 'start_loop_coarse', 'end_loop_coarse'
    ]

    def __init__(self):
        # Note and velocity ranges
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127

        # Main parameters
        self.initial_filterQ = 0
        self.initialFilterFc = 13500
        self.peakConcave = 0
        self.voiceConcave = 0

        # Amplitude envelope parameters
        self.AttackVolEnv = -12000  # in time cents
        self.DecayVolEnv = -12000
        self.SustainVolEnv = 0  # 0-127 (0 = -inf dB)
        self.ReleaseVolEnv = -12000
        self.DelayVolEnv = -12000  # Amplitude envelope delay
        self.HoldVolEnv = -12000  # Amplitude envelope hold
        # Filter envelope parameters
        self.AttackFilEnv = -12000
        self.DecayFilEnv = -12000
        self.SustainFilEnv = 0
        self.ReleaseFilEnv = -12000
        self.DelayFilEnv = -12000  # Filter envelope delay
        self.HoldFilEnv = -12000  # Filter envelope hold

        # Pitch envelope parameters
        self.AttackPitchEnv = 0
        self.DecayPitchEnv = 0
        self.SustainPitchEnv = 0
        self.ReleasePitchEnv = 0
        self.DelayPitchEnv = 0  # Pitch envelope delay
        self.HoldPitchEnv = 0  # Pitch envelope hold

        # LFO parameters
        self.DelayLFO1 = 0
        self.DelayLFO2 = 0
        self.LFO1Freq = 500  # 0.01 Hz * value
        self.LFO2Freq = 0
        self.LFO1VolumeToPitch = 0
        self.LFO1VolumeToFilter = 0
        self.LFO1VolumeToVolume = 0

        # Panning
        self.InitialAttenuation = 0  # 0-1440 (0 = 1.0, 960 = -6dB, 1440 = -9dB)
        self.Pan = 50  # 0-100 (0 = left, 50 = center, 100 = right)

        # Velocity and pitch
        self.VelocityAttenuation = 0
        self.VelocityPitch = 0
        self.OverridingRootKey = -1  # -1 = use the note, otherwise reassign root key

        # Key scaling for envelopes
        self.KeynumToVolEnvHold = 0  # Keynum to Volume Envelope Hold
        self.KeynumToVolEnvDecay = 0  # Keynum to Volume Envelope Decay
        self.KeynumToModEnvHold = 0  # Keynum to Modulation Envelope Hold
        self.KeynumToModEnvDecay = 0  # Keynum to Modulation Envelope Decay

        # Pitch tuning
        self.CoarseTune = 0  # Coarse tuning (octaves)
        self.FineTune = 0  # Fine tuning (cents)
        self.scale_tuning = 100  # Scale tuning (100 cents = 1 semitone)

        # Sample reference
        self.sample_index = 0
        self.sample_name = "Default"

        # Additional flags
        self.mute = False
        self.keynum_to_volume = 0  # Key Number to Volume Envelope Delay

        # Sample parameters
        self.sample_modes = 0
        self.exclusive_class = 0
        self.start = 0
        self.end = 0
        self.start_loop = 0
        self.end_loop = 0
        self.start_coarse = 0
        self.end_coarse = 0
        self.start_loop_coarse = 0
        self.end_loop_coarse = 0

        # Effects send parameters
        self.reverb_send = 0  # 0-127
        self.chorus_send = 0  # 0-127

        # Modulators
        self.modulators = []

        # Generators (for storing parameters)
        self.generators = {}

        # Common modulations (for simplified access)
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
    """Represents a preset zone in SoundFont 2.0"""
    __slots__ = [
        'preset', 'bank', 'generators', 'modulators', 'instrument_index',
        'instrument_name', 'lokey', 'hikey', 'lovel', 'hivel', 'lfo_to_pitch',
        'lfo_to_filter', 'velocity_to_pitch', 'velocity_to_filter',
        'aftertouch_to_pitch', 'aftertouch_to_filter', 'mod_wheel_to_pitch',
        'mod_wheel_to_filter', 'brightness_to_filter', 'portamento_to_pitch',
        'tremolo_depth', 'vibrato_depth', 'gen_ndx', 'mod_ndx',
        # Generator parameters that might be set by preset generators
        'initialFilterFc', 'initial_filterQ', 'Pan', 'DelayLFO1', 'LFO1Freq',
        'DelayLFO2', 'DelayFilEnv', 'AttackFilEnv', 'HoldFilEnv', 'DecayFilEnv',
        'SustainFilEnv', 'ReleaseFilEnv', 'KeynumToModEnvHold', 'KeynumToModEnvDecay',
        'DelayVolEnv', 'AttackVolEnv', 'HoldVolEnv', 'DecayVolEnv', 'SustainVolEnv',
        'ReleaseVolEnv', 'KeynumToVolEnvHold', 'KeynumToVolEnvDecay', 'CoarseTune', 'FineTune',
        'reverb_send', 'chorus_send', 'InitialAttenuation', 'scale_tuning', 'OverridingRootKey',
        'start_coarse', 'end_coarse', 'start_loop_coarse', 'end_loop_coarse',
        "LFO2Freq"
    ]

    def __init__(self):
        self.preset = 0
        self.bank = 0
        self.generators = {}  # Dictionary to store generator parameters
        self.modulators = []  # List of modulators for this preset zone
        self.instrument_index = 0
        self.instrument_name = ""

        # Note and velocity ranges
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127

        # Generator parameters that might be set by preset generators
        self.initialFilterFc = 13500
        self.initial_filterQ = 0
        self.Pan = 50
        self.DelayLFO1 = 0
        self.LFO1Freq = 500
        self.DelayLFO2 = 0
        self.DelayFilEnv = -12000
        self.AttackFilEnv = -12000
        self.HoldFilEnv = -12000
        self.DecayFilEnv = -12000
        self.SustainFilEnv = 0
        self.ReleaseFilEnv = -12000
        self.KeynumToModEnvHold = 0
        self.KeynumToModEnvDecay = 0
        self.DelayVolEnv = -12000
        self.AttackVolEnv = -12000
        self.HoldVolEnv = -12000
        self.DecayVolEnv = -12000
        self.SustainVolEnv = 0
        self.ReleaseVolEnv = -12000
        self.KeynumToVolEnvHold = 0
        self.KeynumToVolEnvDecay = 0
        self.CoarseTune = 0
        self.FineTune = 0
        self.InitialAttenuation = 0  # 0-1440 (0 = 1.0, 960 = -6dB, 1440 = -9dB)
        self.scale_tuning = 100  # Scale tuning (100 cents = 1 semitone)
        self.OverridingRootKey = -1  # -1 = use the note, otherwise reassign root key
        self.start_coarse = 0
        self.end_coarse = 0
        self.start_loop_coarse = 0
        self.end_loop_coarse = 0

        # Effects send parameters
        self.reverb_send = 0  # 0-127
        self.chorus_send = 0  # 0-127

        # Common modulations (for simplified access)
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
        self.LFO2Freq = 0

class SF2SampleHeader:
    """Represents a sample header in SoundFont 2.0"""
    __slots__ = [
        'name', 'start', 'end', 'start_loop', 'end_loop', 'sample_rate',
        'original_pitch', 'pitch_correction', 'link', 'type', 'stereo',
        'data'
    ]

    def __init__(self):
        self.name = "Default"
        self.start = 0
        self.end = 0
        self.start_loop = 0
        self.end_loop = 0
        self.sample_rate = 44100
        self.original_pitch = 60  # MIDI note number
        self.pitch_correction = 0  # in cents
        self.link = 0
        self.type = 1  # 1 = mono, 2 = right, 4 = left, 8 = linked

        self.stereo = False
        self.data : Optional[Union[List[float], List[Tuple[float, float]]]] = None

    def size_estimate(self):
        if self.data:
            return len(self.data) * 8 if self.stereo else 4
        else:
            return 0

class SF2Preset:
    """Represents a preset (instrument) in SoundFont 2.0"""
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
        self.zones: List[SF2PresetZone] = []  # List of SF2PresetZone

class SF2Instrument:
    """Represents an instrument in SoundFont 2.0"""
    __slots__ = ['name', 'instrument_bag_index', 'zones']

    def __init__(self):
        self.name = "Default"
        self.instrument_bag_index = 0
        self.zones: List[SF2InstrumentZone] = []  # List of SF2InstrumentZone
