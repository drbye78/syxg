"""
SF2 Data Classes - Complete SF2 specification implementation.

This module provides the core data structures for SoundFont 2.0 files,
implementing all generators, modulators, zones, samples, presets, and instruments
according to the SF2 specification.
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Union, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class SF2Modulator:
    """Represents a complete modulator in SoundFont 2.0 with all advanced features"""
    __slots__ = [
        # Primary modulation source
        'source_oper', 'source_polarity', 'source_type', 'source_direction', 'source_index',

        # Secondary modulation source (control)
        'control_oper', 'control_polarity', 'control_type', 'control_direction', 'control_index',

        # Modulation target
        'destination', 'amount',

        # Amount modulation source (depth modulation)
        'amount_source_oper', 'amount_source_polarity', 'amount_source_type',
        'amount_source_direction', 'amount_source_index',

        # Transform operation
        'transform',

        # Computed values for processing
        'source_cc', 'control_cc', 'amount_cc', 'final_amount'
    ]

    def __init__(self):
        # Primary modulation source (what modulates)
        self.source_oper = 0  # Source Operator (0=no controller, 2=key number, 3=velocity, etc.)
        self.source_polarity = 0  # 0 = unipolar (0 to 1), 1 = bipolar (-1 to +1)
        self.source_type = 0  # 0 = linear, 1 = concave, 2 = convex, 3 = switch
        self.source_direction = 0  # 0 = max->min (normal), 1 = min->max (reverse)
        self.source_index = 0  # Source index (for CC controllers)

        # Secondary modulation source (control input)
        self.control_oper = 0  # Control Operator
        self.control_polarity = 0  # 0 = unipolar, 1 = bipolar
        self.control_type = 0  # 0 = linear, 1 = concave, 2 = convex, 3 = switch
        self.control_direction = 0  # 0 = max->min, 1 = min->max
        self.control_index = 0  # Control index

        # Modulation target and depth
        self.destination = 0  # Destination Generator (what gets modulated)
        self.amount = 0  # Base modulation amount

        # Amount modulation source (modulates the modulation depth)
        self.amount_source_oper = 0  # Amount source operator
        self.amount_source_polarity = 0  # 0 = unipolar, 1 = bipolar
        self.amount_source_type = 0  # 0 = linear, 1 = concave, 2 = convex, 3 = switch
        self.amount_source_direction = 0  # 0 = max->min, 1 = min->max
        self.amount_source_index = 0  # Amount source index

        # Transform operation
        self.transform = 0  # Transform Operator (0=linear, 1=absolute)

        # Computed values for runtime processing
        self.source_cc = -1  # Resolved CC number for source
        self.control_cc = -1  # Resolved CC number for control
        self.amount_cc = -1  # Resolved CC number for amount source
        self.final_amount = 0.0  # Computed final modulation amount

    def compute_modulation_value(self, source_value: float, control_value: float = 1.0,
                                amount_value: float = 1.0) -> float:
        """
        Compute the final modulation value based on all sources and transforms.

        Args:
            source_value: Primary source value (0.0 to 1.0)
            control_value: Secondary control value (0.0 to 1.0)
            amount_value: Amount modulation value (0.0 to 1.0)

        Returns:
            Final modulation amount (-1.0 to +1.0)
        """
        # Apply source polarity and direction
        if self.source_polarity == 1:  # Bipolar
            source_value = (source_value * 2.0) - 1.0
        if self.source_direction == 1:  # Reverse direction
            source_value = 1.0 - source_value

        # Apply source type (concave/convex/switch)
        source_value = self._apply_transform_type(source_value, self.source_type)

        # Apply control if present
        if self.control_oper != 0:
            if self.control_polarity == 1:  # Bipolar
                control_value = (control_value * 2.0) - 1.0
            if self.control_direction == 1:  # Reverse direction
                control_value = 1.0 - control_value
            control_value = self._apply_transform_type(control_value, self.control_type)
            source_value *= control_value

        # Apply amount modulation
        if self.amount_source_oper != 0:
            if self.amount_source_polarity == 1:  # Bipolar
                amount_value = (amount_value * 2.0) - 1.0
            if self.amount_source_direction == 1:  # Reverse direction
                amount_value = 1.0 - amount_value
            amount_value = self._apply_transform_type(amount_value, self.amount_source_type)
            source_value *= amount_value

        # Apply base amount
        result = source_value * (self.amount / 32768.0)  # SF2 amounts are 16-bit signed

        # Apply final transform
        if self.transform == 1:  # Absolute value
            result = abs(result)

        self.final_amount = result
        return result

    def _apply_transform_type(self, value: float, transform_type: int) -> float:
        """
        Apply SF2 transform type to modulation value.

        Args:
            value: Input value (-1.0 to +1.0)
            transform_type: SF2 transform type (0=linear, 1=concave, 2=convex, 3=switch)

        Returns:
            Transformed value
        """
        if transform_type == 0:  # Linear
            return value
        elif transform_type == 1:  # Concave (square root curve)
            sign = 1.0 if value >= 0 else -1.0
            return sign * math.sqrt(abs(value))
        elif transform_type == 2:  # Convex (square curve)
            return value * value * (1.0 if value >= 0 else -1.0)
        elif transform_type == 3:  # Switch (threshold)
            return 1.0 if value >= 0.5 else 0.0
        else:
            return value  # Default to linear

class SF2InstrumentZone:
    """
    Represents an instrument zone in SoundFont 2.0 with complete generator support

    Notes on fields:
    - sampleID and sample_index are synchronized for consistency
    - sample_name is populated from SHDR chunk during parsing
    - Various duplicate fields exist for backward compatibility (deprecated)
    """
    __slots__ = [
        # Basic generators (0-7)
        'startAddrsOffset', 'endAddrsOffset', 'startloopAddrsOffset', 'endloopAddrsOffset',
        'startAddrsCoarseOffset', 'modLfoToPitch', 'vibLfoToPitch', 'modEnvToPitch',

        # Filter generators (8-11)
        'initialFilterFc', 'initialFilterQ', 'modLfoToFilterFc', 'modEnvToFilterFc',

        # Volume envelope generators (12-20)
        'modLfoToVolume', 'unused1', 'chorusEffectsSend', 'reverbEffectsSend', 'pan',
        'unused2', 'unused3', 'unused4', 'delayModLFO',

        # LFO generators (21-27)
        'freqModLFO', 'delayVibLFO', 'freqVibLFO', 'delayModEnv', 'attackModEnv',
        'holdModEnv', 'decayModEnv',

        # More envelope generators (28-35)
        'sustainModEnv', 'releaseModEnv', 'keynumToModEnvHold', 'keynumToModEnvDecay',
        'delayVolEnv', 'attackVolEnv', 'holdVolEnv', 'decayVolEnv',

        # Volume envelope completion (36-43)
        'sustainVolEnv', 'releaseVolEnv', 'keynumToVolEnvHold', 'keynumToVolEnvDecay',
        'instrument', 'reserved1', 'keyRange', 'velRange',

        # Sample manipulation (44-51)
        'startloopAddrsCoarse', 'keynum', 'velocity', 'initialAttenuation',
        'reserved2', 'endloopAddrsCoarse', 'coarseTune', 'fineTune',

        # More tuning and effects (52-59)
        'sampleID', 'sampleModes', 'reserved3', 'scaleTuning',
        'exclusiveClass', 'overridingRootKey', 'unused5', 'endAddrsCoarseOffset',

        # Legacy compatibility fields (for backward compatibility)
        'lokey', 'hikey', 'lovel', 'hivel', 'initial_filterQ',
        'peakConcave', 'voiceConcave', 'AttackVolEnv', 'DecayVolEnv', 'SustainVolEnv',
        'ReleaseVolEnv', 'DelayVolEnv', 'HoldVolEnv',
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
        'scale_tuning', 'start_coarse', 'end_coarse', 'start_loop_coarse', 'end_loop_coarse',
        'preset_instrument_index'
    ]

    def __init__(self):
        # Initialize all SF2 generators with their default values according to SF2 spec

        # Sample addressing generators (0-7)
        self.startAddrsOffset = 0
        self.endAddrsOffset = 0
        self.startloopAddrsOffset = 0
        self.endloopAddrsOffset = 0
        self.startAddrsCoarseOffset = 0
        self.modLfoToPitch = 0
        self.vibLfoToPitch = 0
        self.modEnvToPitch = 0

        # Filter generators (8-11)
        self.initialFilterFc = 13500  # ~8.5kHz in cents above 8.175Hz
        self.initialFilterQ = 0
        self.modLfoToFilterFc = 0
        self.modEnvToFilterFc = 0

        # Volume envelope generators (12-20)
        self.modLfoToVolume = 0
        self.unused1 = 0
        self.chorusEffectsSend = 0
        self.reverbEffectsSend = 0
        self.pan = 0  # -500 to +500 (0 = center)
        self.unused2 = 0
        self.unused3 = 0
        self.unused4 = 0
        self.delayModLFO = 0

        # LFO generators (21-27)
        self.freqModLFO = 0  # Default LFO frequency
        self.delayVibLFO = 0
        self.freqVibLFO = 0
        self.delayModEnv = -12000  # Default delay (no delay)
        self.attackModEnv = -12000
        self.holdModEnv = -12000
        self.decayModEnv = -12000

        # More envelope generators (28-35)
        self.sustainModEnv = 0
        self.releaseModEnv = -12000
        self.keynumToModEnvHold = 0
        self.keynumToModEnvDecay = 0
        self.delayVolEnv = -12000
        self.attackVolEnv = -12000
        self.holdVolEnv = -12000
        self.decayVolEnv = -12000

        # Volume envelope completion (36-43)
        self.sustainVolEnv = 0
        self.releaseVolEnv = -12000
        self.keynumToVolEnvHold = 0
        self.keynumToVolEnvDecay = 0
        self.instrument = 0  # Not used in zones
        self.reserved1 = 0
        self.keyRange = 32512  # 0x7F00 - default key range 0-127 (low=0, high=127)
        self.velRange = 32512  # 0x7F00 - default vel range 0-127 (low=0, high=127)

        # Sample manipulation (44-51)
        self.startloopAddrsCoarse = 0
        self.keynum = -1  # -1 = use root key from sample
        self.velocity = -1  # -1 = use note velocity
        self.initialAttenuation = 0
        self.reserved2 = 0
        self.endloopAddrsCoarse = 0
        self.coarseTune = 0
        self.fineTune = 0

        # More tuning and effects (52-59)
        self.sampleID = -1  # -1 = not set yet, 0+ = valid sample indices
        self.sampleModes = 0
        self.reserved3 = 0
        self.scaleTuning = 100  # 100 cents per semitone
        self.exclusiveClass = 0
        self.overridingRootKey = -1  # -1 = use sample root key
        self.unused5 = 0
        self.endAddrsCoarseOffset = 0

        # Range helper fields (computed from keyRange/velRange)
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127
        self.initial_filterQ = 0

        # Legacy compatibility fields (restore essential ones used by existing code)
        # These will be deprecated in future versions - use generators dict directly
        # Some fields needed for compatibility with other parts of codebase
        self.DelayLFO1 = 0
        self.DelayLFO2 = 0
        self.LFO1Freq = 0  # Default LFO frequency
        self.LFO2Freq = 0
        self.peakConcave = 0
        self.voiceConcave = 0
        self.AttackVolEnv = -12000
        self.scale_tuning = 100
        self.sample_index = -1  # -1 = not set yet, 0+ = valid sample indices
        self.sample_name = ""  # Empty string = not populated from SF2 file
        self.mute = False
        self.keynum_to_volume = 0
        self.modulators = []
        self.generators = {}
        self.sample_modes = 0
        self.exclusive_class = 0
        self.start = 0
        self.end = 0
        self.start_loop = 0
        self.end_loop = 0
        self.reverb_send = 0
        self.chorus_send = 0
        self.start_coarse = 0
        self.end_coarse = 0
        self.start_loop_coarse = 0
        self.end_loop_coarse = 0
        self.preset_instrument_index = -1

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
    """Represents a preset zone in SoundFont 2.0 with complete generator support"""
    __slots__ = [
        # Basic preset zone fields
        'preset', 'bank', 'generators', 'modulators', 'instrument_index',
        'instrument_name', 'gen_ndx', 'mod_ndx',

        # All SF2 generators that can be set at preset level
        'startAddrsOffset', 'endAddrsOffset', 'startloopAddrsOffset', 'endloopAddrsOffset',
        'startAddrsCoarseOffset', 'modLfoToPitch', 'vibLfoToPitch', 'modEnvToPitch',
        'initialFilterFc', 'initialFilterQ', 'modLfoToFilterFc', 'modEnvToFilterFc',
        'modLfoToVolume', 'unused1', 'chorusEffectsSend', 'reverbEffectsSend', 'pan',
        'unused2', 'unused3', 'unused4', 'delayModLFO', 'freqModLFO', 'delayVibLFO',
        'freqVibLFO', 'delayModEnv', 'attackModEnv', 'holdModEnv', 'decayModEnv',
        'sustainModEnv', 'releaseModEnv', 'keynumToModEnvHold', 'keynumToModEnvDecay',
        'delayVolEnv', 'attackVolEnv', 'holdVolEnv', 'decayVolEnv', 'sustainVolEnv',
        'releaseVolEnv', 'keynumToVolEnvHold', 'keynumToVolEnvDecay', 'instrument',
        'reserved1', 'keyRange', 'velRange', 'startloopAddrsCoarse', 'keynum',
        'velocity', 'initialAttenuation', 'reserved2', 'endloopAddrsCoarse',
        'coarseTune', 'fineTune', 'sampleID', 'sampleModes', 'reserved3',
        'scaleTuning', 'exclusiveClass', 'overridingRootKey', 'unused5',
        'endAddrsCoarseOffset',

        # Legacy compatibility fields
        'lokey', 'hikey', 'lovel', 'hivel', 'lfo_to_pitch',
        'lfo_to_filter', 'velocity_to_pitch', 'velocity_to_filter',
        'aftertouch_to_pitch', 'aftertouch_to_filter', 'mod_wheel_to_pitch',
        'mod_wheel_to_filter', 'brightness_to_filter', 'portamento_to_pitch',
        'tremolo_depth', 'vibrato_depth',
        # Generator parameters that might be set by preset generators
        'initial_filterQ', 'Pan', 'DelayLFO1', 'LFO1Freq',
        'DelayLFO2', 'DelayFilEnv', 'AttackFilEnv', 'HoldFilEnv', 'DecayFilEnv',
        'SustainFilEnv', 'ReleaseFilEnv', 'KeynumToModEnvHold', 'KeynumToModEnvDecay',
        'DelayVolEnv', 'AttackVolEnv', 'HoldVolEnv', 'DecayVolEnv', 'SustainVolEnv',
        'ReleaseVolEnv', 'KeynumToVolEnvHold', 'KeynumToVolEnvDecay', 'CoarseTune', 'FineTune',
        'reverb_send', 'chorus_send', 'InitialAttenuation', 'scale_tuning', 'OverridingRootKey',
        'start_coarse', 'end_coarse', 'start_loop_coarse', 'end_loop_coarse',
        "LFO2Freq"
    ]

    def __init__(self):
        # Basic preset zone fields
        self.preset = 0
        self.bank = 0
        self.generators = {}  # Dictionary to store generator parameters
        self.modulators = []  # List of modulators for this preset zone
        self.instrument_index = -1  # -1 = not set yet, 0+ = valid instrument indices
        self.instrument_name = ""
        self.gen_ndx = 0
        self.mod_ndx = 0

        # Initialize all SF2 generators with default values (presets can override instrument defaults)

        # Sample addressing generators (0-7) - usually not set at preset level
        self.startAddrsOffset = 0
        self.endAddrsOffset = 0
        self.startloopAddrsOffset = 0
        self.endloopAddrsOffset = 0
        self.startAddrsCoarseOffset = 0
        self.modLfoToPitch = 0
        self.vibLfoToPitch = 0
        self.modEnvToPitch = 0

        # Filter generators (8-11)
        self.initialFilterFc = 13500  # Default filter cutoff
        self.initialFilterQ = 0
        self.modLfoToFilterFc = 0
        self.modEnvToFilterFc = 0

        # Volume envelope generators (12-20)
        self.modLfoToVolume = 0
        self.unused1 = 0
        self.chorusEffectsSend = 0
        self.reverbEffectsSend = 0
        self.pan = 0  # -500 to +500
        self.unused2 = 0
        self.unused3 = 0
        self.unused4 = 0
        self.delayModLFO = 0

        # LFO generators (21-27)
        self.freqModLFO = 0
        self.delayVibLFO = 0
        self.freqVibLFO = 0
        self.delayModEnv = -12000
        self.attackModEnv = -12000
        self.holdModEnv = -12000
        self.decayModEnv = -12000

        # More envelope generators (28-35)
        self.sustainModEnv = 0
        self.releaseModEnv = -12000
        self.keynumToModEnvHold = 0
        self.keynumToModEnvDecay = 0
        self.delayVolEnv = -12000
        self.attackVolEnv = -12000
        self.holdVolEnv = -12000
        self.decayVolEnv = -12000

        # Volume envelope completion (36-43)
        self.sustainVolEnv = 0
        self.releaseVolEnv = -12000
        self.keynumToVolEnvHold = 0
        self.keynumToVolEnvDecay = 0
        self.instrument = 0  # References instrument index
        self.reserved1 = 0
        self.keyRange = 32512  # 0x7F00 - default key range 0-127 (low=0, high=127)
        self.velRange = 32512  # 0x7F00 - default vel range 0-127 (low=0, high=127)

        # Sample manipulation (44-51)
        self.startloopAddrsCoarse = 0
        self.keynum = -1
        self.velocity = -1
        self.initialAttenuation = 0
        self.reserved2 = 0
        self.endloopAddrsCoarse = 0
        self.coarseTune = 0
        self.fineTune = 0

        # More tuning and effects (52-59)
        self.sampleID = -1
        self.sampleModes = 0
        self.reserved3 = 0
        self.scaleTuning = 100
        self.exclusiveClass = 0
        self.overridingRootKey = -1
        self.unused5 = 0
        self.endAddrsCoarseOffset = 0

        # Legacy compatibility fields
        self.lokey = 0
        self.hikey = 127
        self.lovel = 0
        self.hivel = 127
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

        # Generator parameters that might be set by preset generators
        self.initial_filterQ = 0
        self.Pan = 0  # Center pan position (-500 to +500)
        self.DelayLFO1 = 0
        self.LFO1Freq = 0  # Default LFO frequency
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
        self.InitialAttenuation = 0
        self.scale_tuning = 100
        self.OverridingRootKey = -1
        self.start_coarse = 0
        self.end_coarse = 0
        self.start_loop_coarse = 0
        self.end_loop_coarse = 0
        self.reverb_send = 0
        self.chorus_send = 0
        self.LFO2Freq = 0

class SF2SampleHeader:
    """Represents a sample header in SoundFont 2.0"""
    __slots__ = [
        'name', 'start', 'end', 'start_loop', 'end_loop', 'sample_rate',
        'original_pitch', 'pitch_correction', 'link', 'type', 'stereo',
        'data', 'channels', 'sample_format'
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
        self.channels = 1  # 1 = mono, 2 = stereo
        self.sample_format = "mono"  # "mono" or "stereo"
        self.data : Optional[Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]] = None

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


# ===== NEW PRODUCTION-QUALITY SF2 DATA STRUCTURES =====


class SampleFormat(Enum):
    """Enumeration of supported sample formats in SF2"""
    MONO_16BIT = "mono_16bit"
    MONO_24BIT = "mono_24bit"
    STEREO_16BIT = "stereo_16bit"
    STEREO_24BIT = "stereo_24bit"


@dataclass
class SF2Generator:
    """
    Complete SF2 generator with type, amount, and metadata.

    Implements all 60+ SF2 generators according to specification.
    """
    generator_type: int  # Generator type (0-65)
    amount: int  # Generator amount (-32768 to 32767)
    name: str = ""  # Human-readable name for debugging

    def __post_init__(self):
        """Validate generator data after initialization."""
        if not (0 <= self.generator_type <= 65):
            raise ValueError(f"Invalid generator type: {self.generator_type}")
        if not (-32768 <= self.amount <= 32767):
            raise ValueError(f"Generator amount out of range: {self.amount}")


@dataclass
class SF2Modulator:
    """
    Complete SF2 modulator with all transform operations.

    Supports the full SF2 modulation specification including
    dual sources, amount modulation, and transforms.
    """
    # Primary modulation source
    source_operator: int
    source_polarity: int = 0
    source_type: int = 0
    source_direction: int = 0
    source_index: int = 0

    # Secondary modulation source (control)
    control_operator: int = 0
    control_polarity: int = 0
    control_type: int = 0
    control_direction: int = 0
    control_index: int = 0

    # Modulation target and depth
    destination: int = 0
    amount: int = 0

    # Amount modulation source
    amount_source_operator: int = 0
    amount_source_polarity: int = 0
    amount_source_type: int = 0
    amount_source_direction: int = 0
    amount_source_index: int = 0

    # Transform operation
    transform: int = 0

    def compute_modulation_value(
        self,
        source_value: float,
        control_value: float = 1.0,
        amount_value: float = 1.0
    ) -> float:
        """
        Compute final modulation value with all SF2 transforms.

        Args:
            source_value: Primary source value (0.0 to 1.0)
            control_value: Secondary control value (0.0 to 1.0)
            amount_value: Amount modulation value (0.0 to 1.0)

        Returns:
            Final modulation amount (-1.0 to +1.0)
        """
        # Apply source polarity and direction
        if self.source_polarity == 1:  # Bipolar
            source_value = (source_value * 2.0) - 1.0
        if self.source_direction == 1:  # Reverse direction
            source_value = 1.0 - source_value

        # Apply source type (concave/convex/switch)
        source_value = self._apply_transform_type(source_value,
                                                self.source_type)

        # Apply control if present
        if self.control_operator != 0:
            if self.control_polarity == 1:  # Bipolar
                control_value = (control_value * 2.0) - 1.0
            if self.control_direction == 1:  # Reverse direction
                control_value = 1.0 - control_value
            control_value = self._apply_transform_type(control_value,
                                                     self.control_type)
            source_value *= control_value

        # Apply amount modulation
        if self.amount_source_operator != 0:
            if self.amount_source_polarity == 1:  # Bipolar
                amount_value = (amount_value * 2.0) - 1.0
            if self.amount_source_direction == 1:  # Reverse direction
                amount_value = 1.0 - amount_value
            amount_value = self._apply_transform_type(amount_value,
                                                    self.amount_source_type)
            source_value *= amount_value

        # Apply base amount
        result = source_value * (self.amount / 32768.0)

        # Apply final transform
        if self.transform == 1:  # Absolute value
            result = abs(result)

        return result

    @staticmethod
    def _apply_transform_type(value: float, transform_type: int) -> float:
        """Apply SF2 transform type to modulation value."""
        if transform_type == 0:  # Linear
            return value
        elif transform_type == 1:  # Concave (square root curve)
            sign = 1.0 if value >= 0 else -1.0
            return sign * math.sqrt(abs(value))
        elif transform_type == 2:  # Convex (square curve)
            return value * value * (1.0 if value >= 0 else -1.0)
        elif transform_type == 3:  # Switch (threshold)
            return 1.0 if value >= 0.5 else 0.0
        else:
            return value  # Default to linear


@dataclass
class SF2Zone:
    """
    Unified zone class for both preset and instrument zones.

    Provides complete SF2 zone processing with proper inheritance
    and generator/modulator support.
    """
    # Basic zone properties
    zone_type: str  # 'preset' or 'instrument'
    generators: Dict[int, SF2Generator] = field(default_factory=dict)
    modulators: List[SF2Modulator] = field(default_factory=list)

    # Zone ranges (computed from generators)
    key_low: int = 0
    key_high: int = 127
    vel_low: int = 0
    vel_high: int = 127

    # References (different for preset vs instrument zones)
    instrument_index: Optional[int] = None  # For preset zones
    sample_index: Optional[int] = None      # For instrument zones

    # Processing state
    is_global: bool = False  # True if zone has no sample/instrument reference
    processed: bool = False  # True after complete processing

    def __post_init__(self):
        """Initialize zone with SF2 defaults."""
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize all SF2 generators with specification defaults."""
        # Volume envelope defaults (SF2 spec section 8.1)
        defaults = {
            8: SF2Generator(8, -12000, "volEnvDelay"),      # delayVolEnv
            9: SF2Generator(9, -12000, "volEnvAttack"),     # attackVolEnv
            10: SF2Generator(10, -12000, "volEnvHold"),     # holdVolEnv
            11: SF2Generator(11, -12000, "volEnvDecay"),    # decayVolEnv
            12: SF2Generator(12, 0, "volEnvSustain"),       # sustainVolEnv
            13: SF2Generator(13, -12000, "volEnvRelease"),  # releaseVolEnv

            # Modulation envelope defaults
            14: SF2Generator(14, -12000, "modEnvDelay"),    # delayModEnv
            15: SF2Generator(15, -12000, "modEnvAttack"),   # attackModEnv
            16: SF2Generator(16, -12000, "modEnvHold"),     # holdModEnv
            17: SF2Generator(17, -12000, "modEnvDecay"),    # decayModEnv
            18: SF2Generator(18, -12000, "modEnvSustain"),  # sustainModEnv
            19: SF2Generator(19, -12000, "modEnvRelease"),  # releaseModEnv

            # Filter defaults
            29: SF2Generator(29, 13500, "initialFilterFc"), # ~8.5kHz
            30: SF2Generator(30, 0, "initialFilterQ"),      # 0 = 1 pole

            # LFO defaults
            21: SF2Generator(21, -12000, "delayModLFO"),    # No delay
            22: SF2Generator(22, 0, "freqModLFO"),          # Default frequency
            26: SF2Generator(26, -12000, "delayVibLFO"),    # No delay
            27: SF2Generator(27, 0, "freqVibLFO"),          # Default frequency

            # Key/velocity ranges
            42: SF2Generator(42, 32512, "keyRange"),        # Full range 0-127
            43: SF2Generator(43, 32512, "velRange"),        # Full range 0-127

            # Tuning defaults
            48: SF2Generator(48, 0, "coarseTune"),          # No coarse tuning
            49: SF2Generator(49, 0, "fineTune"),            # No fine tuning
            52: SF2Generator(52, 100, "scaleTuning"),       # 100 cents/semitone

            # Effects defaults
            32: SF2Generator(32, 0, "reverbEffectsSend"),   # No reverb send
            33: SF2Generator(33, 0, "chorusEffectsSend"),   # No chorus send
            34: SF2Generator(34, 0, "pan"),                 # Center pan
        }

        # Set defaults for generators not already set
        for gen_type, default_gen in defaults.items():
            if gen_type not in self.generators:
                self.generators[gen_type] = default_gen

    def get_generator_value(self, gen_type: int,
                          default: Optional[int] = None) -> int:
        """
        Get generator value with optional default.

        Args:
            gen_type: Generator type to retrieve
            default: Default value if generator not found

        Returns:
            Generator amount value
        """
        if gen_type in self.generators:
            return self.generators[gen_type].amount
        return default if default is not None else 0

    def set_generator_value(self, gen_type: int, amount: int,
                          name: str = ""):
        """Set generator value."""
        self.generators[gen_type] = SF2Generator(gen_type, amount, name)

    def update_ranges_from_generators(self):
        """Update key/velocity ranges from generator values."""
        # Key range (generator 42)
        key_range = self.get_generator_value(42, 32512)  # Default full range
        self.key_low = key_range & 0xFF
        self.key_high = (key_range >> 8) & 0xFF

        # Velocity range (generator 43)
        vel_range = self.get_generator_value(43, 32512)  # Default full range
        self.vel_low = vel_range & 0xFF
        self.vel_high = (vel_range >> 8) & 0xFF

    def matches_note_velocity(self, note: int, velocity: int) -> bool:
        """
        Check if zone matches the given note and velocity.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            True if zone matches, False otherwise
        """
        return (self.key_low <= note <= self.key_high and
                self.vel_low <= velocity <= self.vel_high)


@dataclass
class SF2Sample:
    """
    Enhanced SF2 sample with mip-mapping and multi-format support.

    Supports 16/24-bit mono/stereo samples with integrated mip-mapping
    for high-quality high-pitch playback.
    """
    # Sample metadata
    name: str
    sample_rate: int
    original_pitch: int  # MIDI note number
    pitch_correction: int  # Pitch correction in cents
    format: SampleFormat

    # Sample data
    data: Optional[np.ndarray] = None

    # Loop information
    loop_start: int = 0
    loop_end: int = 0
    loop_mode: int = 0  # 0=no loop, 1=forward, 2=backward, 3=alternating

    # Stereo information (for stereo samples)
    linked_sample: Optional['SF2Sample'] = None

    # Mip-mapping support
    mip_map: Optional[Any] = None  # Will be SampleMipMap instance

    # Processing state
    loaded: bool = False
    memory_usage: int = 0

    def __post_init__(self):
        """Validate sample data after initialization."""
        if self.data is not None:
            self._validate_data()
            self.memory_usage = self.data.nbytes

    def _validate_data(self):
        """Validate sample data format and consistency."""
        if self.data is None:
            return

        if self.format == SampleFormat.MONO_16BIT:
            if self.data.dtype != np.int16 or len(self.data.shape) != 1:
                raise ValueError("MONO_16BIT sample must be 1D int16 array")
        elif self.format == SampleFormat.MONO_24BIT:
            if self.data.dtype != np.float32 or len(self.data.shape) != 1:
                raise ValueError("MONO_24BIT sample must be 1D float32 array")
        elif self.format in [SampleFormat.STEREO_16BIT, SampleFormat.STEREO_24BIT]:
            if len(self.data.shape) != 2 or self.data.shape[1] != 2:
                raise ValueError("Stereo sample must be 2D array with shape (n, 2)")

    def get_pitch_ratio_for_note(self, note: int) -> float:
        """
        Calculate pitch ratio for playing sample at given note.

        Args:
            note: MIDI note number (0-127)

        Returns:
            Pitch ratio (playback_speed / original_speed)
        """
        note_diff = note - self.original_pitch
        pitch_correction_semitones = self.pitch_correction / 100.0
        total_semitones = note_diff + pitch_correction_semitones
        return 2.0 ** (total_semitones / 12.0)

    def get_mip_level(self, pitch_ratio: float) -> Optional[np.ndarray]:
        """
        Get appropriate mip level for pitch ratio.

        Args:
            pitch_ratio: Playback pitch ratio

        Returns:
            Sample data for optimal mip level, or None if no data
        """
        if self.mip_map is None:
            return self.data

        level = self.mip_map.select_mip_level(pitch_ratio)
        return self.mip_map.get_level(level)

    def is_stereo(self) -> bool:
        """Check if sample is stereo."""
        return self.format in [SampleFormat.STEREO_16BIT, SampleFormat.STEREO_24BIT]

    def get_channel_count(self) -> int:
        """Get number of channels (1=mono, 2=stereo)."""
        return 2 if self.is_stereo() else 1


@dataclass
class SF2Instrument:
    """
    Complete SF2 instrument with zone processing and inheritance.

    Implements full SF2 instrument specification with proper zone
    ordering and global zone handling.
    """
    name: str
    zones: List[SF2Zone] = field(default_factory=list)

    # Processing state
    processed: bool = False
    global_zone: Optional[SF2Zone] = None

    def process_zones(self):
        """Process zones with proper SF2 inheritance rules."""
        if self.processed:
            return

        # Separate global and local zones
        local_zones = []
        for zone in self.zones:
            if zone.is_global:
                self.global_zone = zone
            else:
                local_zones.append(zone)

        # Apply global zone inheritance to local zones
        if self.global_zone:
            for zone in local_zones:
                self._inherit_from_global_zone(zone)

        # Update zone ranges from generators
        for zone in self.zones:
            zone.update_ranges_from_generators()

        self.processed = True

    def _inherit_from_global_zone(self, zone: SF2Zone):
        """Apply global zone generators/modulators to local zone."""
        if self.global_zone is None:
            return

        # Inherit generators not set in local zone
        for gen_type, global_gen in self.global_zone.generators.items():
            if gen_type not in zone.generators:
                zone.generators[gen_type] = global_gen

        # Inherit modulators (add to existing modulators)
        zone.modulators.extend(self.global_zone.modulators)

    def get_matching_zones(self, note: int, velocity: int) -> List[SF2Zone]:
        """
        Get zones that match the given note and velocity.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones
        """
        if not self.processed:
            self.process_zones()

        return [zone for zone in self.zones
                if not zone.is_global and zone.matches_note_velocity(note, velocity)]


@dataclass
class SF2Preset:
    """
    Complete SF2 preset with multi-layer support.

    Implements full SF2 preset specification with proper layer ordering,
    global zones, and instrument referencing.
    """
    name: str
    bank: int
    preset_number: int
    zones: List[SF2Zone] = field(default_factory=list)

    # Processing state
    processed: bool = False
    global_zone: Optional[SF2Zone] = None

    def process_zones(self):
        """Process zones with proper SF2 inheritance rules."""
        if self.processed:
            return

        # Separate global and local zones
        local_zones = []
        for zone in self.zones:
            if zone.is_global:
                self.global_zone = zone
            else:
                local_zones.append(zone)

        # Apply global zone inheritance to local zones
        if self.global_zone:
            for zone in local_zones:
                self._inherit_from_global_zone(zone)

        # Update zone ranges from generators
        for zone in self.zones:
            zone.update_ranges_from_generators()

        self.processed = True

    def _inherit_from_global_zone(self, zone: SF2Zone):
        """Apply global zone generators/modulators to local zone."""
        if self.global_zone is None:
            return

        # Inherit generators not set in local zone
        for gen_type, global_gen in self.global_zone.generators.items():
            if gen_type not in zone.generators:
                zone.generators[gen_type] = global_gen

        # Inherit modulators (add to existing modulators)
        zone.modulators.extend(self.global_zone.modulators)

    def get_matching_zones(self, note: int, velocity: int) -> List[SF2Zone]:
        """
        Get zones that match the given note and velocity.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of matching zones (can be multiple for layering)
        """
        if not self.processed:
            self.process_zones()

        return [zone for zone in self.zones
                if not zone.is_global and zone.matches_note_velocity(note, velocity)]

    def get_layer_count(self, note: int, velocity: int) -> int:
        """
        Get number of layers (simultaneous zones) for note/velocity.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            Number of layers that would play simultaneously
        """
        return len(self.get_matching_zones(note, velocity))
