import math
from typing import List, Tuple, Optional, Union


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
    """Represents an instrument zone in SoundFont 2.0 with complete generator support"""
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
        self.sampleID = 0
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
        self.sample_index = -1
        self.sample_name = "Default"
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
        self.instrument_index = -1  # -1 means not yet set, will be set by generator parsing
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
        self.sampleID = 0
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
        self.Pan = 50
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
