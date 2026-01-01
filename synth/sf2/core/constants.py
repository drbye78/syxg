"""
SF2 Constants - Complete SoundFont 2.0 specification constants.

This module defines all constants used in the SF2 specification,
including generator types, modulator sources, RIFF chunk IDs,
and other specification-defined values.
"""

import math
from typing import Dict, List, Tuple
from enum import Enum, IntEnum


# ===== RIFF CHUNK IDENTIFIERS =====

class RIFFChunks:
    """RIFF chunk identifiers used in SF2 files."""
    RIFF = b'RIFF'
    LIST = b'LIST'
    SF2_MAGIC = b'sfbk'

    # SF2 sub-chunks
    INFO = b'INFO'
    SDTA = b'sdta'  # Sample data
    PDTA = b'pdta'  # Preset/instrument data

    # INFO sub-chunks
    IFIL = b'ifil'  # Version
    ISNG = b'isng'  # Sound engine
    INAM = b'inam'  # Bank name
    IROM = b'irom'  # ROM name
    IVER = b'iver'  # ROM version
    ICRD = b'icrd'  # Creation date
    IENG = b'ieng'  # Sound designers
    IPRD = b'iprd'  # Intended product
    ICOP = b'icop'  # Copyright
    ICMT = b'icmt'  # Comments
    ISFT = b'isft'  # Software

    # SDTA sub-chunks
    SMPL = b'smpl'  # Sample data
    SM24 = b'sm24'  # 24-bit sample data

    # PDTA sub-chunks
    PHDR = b'phdr'  # Preset headers
    PBAG = b'pbag'  # Preset bags
    PMOD = b'pmod'  # Preset modulators
    PGEN = b'pgen'  # Preset generators
    IHDR = b'inst'  # Instrument headers (note: 'inst', not 'ihdr')
    IBAG = b'ibag'  # Instrument bags
    IMOD = b'imod'  # Instrument modulators
    IGEN = b'igen'  # Instrument generators
    SHDR = b'shdr'  # Sample headers


# ===== GENERATOR TYPES =====

class GeneratorType(IntEnum):
    """SF2 Generator types (0-65) as defined in specification section 8.1."""
    # Sample addressing (0-7)
    startAddrsOffset = 0
    endAddrsOffset = 1
    startloopAddrsOffset = 2
    endloopAddrsOffset = 3
    startAddrsCoarseOffset = 4
    modLfoToPitch = 5
    vibLfoToPitch = 6
    modEnvToPitch = 7

    # Filter (8-11)
    initialFilterFc = 8
    initialFilterQ = 9
    modLfoToFilterFc = 10
    modEnvToFilterFc = 11

    # Volume envelope (12-20)
    modLfoToVolume = 12
    unused1 = 13
    chorusEffectsSend = 14
    reverbEffectsSend = 15
    pan = 16
    unused2 = 17
    unused3 = 18
    unused4 = 19
    delayModLFO = 20

    # LFO (21-27)
    freqModLFO = 21
    delayVibLFO = 22
    freqVibLFO = 23
    delayModEnv = 24
    attackModEnv = 25
    holdModEnv = 26
    decayModEnv = 27

    # More envelope (28-35)
    sustainModEnv = 28
    releaseModEnv = 29
    keynumToModEnvHold = 30
    keynumToModEnvDecay = 31
    delayVolEnv = 32
    attackVolEnv = 33
    holdVolEnv = 34
    decayVolEnv = 35

    # Volume envelope completion (36-43)
    sustainVolEnv = 36
    releaseVolEnv = 37
    keynumToVolEnvHold = 38
    keynumToVolEnvDecay = 39
    instrument = 40
    reserved1 = 41
    keyRange = 42
    velRange = 43

    # Sample manipulation (44-51)
    startloopAddrsCoarse = 44
    keynum = 45
    velocity = 46
    initialAttenuation = 47
    reserved2 = 48
    endloopAddrsCoarse = 49
    coarseTune = 50
    fineTune = 51

    # More tuning and effects (52-59)
    sampleID = 52
    sampleModes = 53
    reserved3 = 54
    scaleTuning = 55
    exclusiveClass = 56
    overridingRootKey = 57
    unused5 = 58
    endAddrsCoarseOffset = 59

    # Legacy/duplicates (60-65)
    modEnvToFilterFc_dup = 60  # Duplicate of 11
    modLfoToFilterFc2_dup = 61  # Duplicate of 10
    volEnvDelay_dup = 62       # Duplicate of 32
    volEnvAttack_dup = 63      # Duplicate of 33
    volEnvHold_dup = 64        # Duplicate of 34
    volEnvDecay_dup = 65       # Duplicate of 35


# Generator names for debugging
GENERATOR_NAMES: Dict[int, str] = {
    0: "startAddrsOffset",
    1: "endAddrsOffset",
    2: "startloopAddrsOffset",
    3: "endloopAddrsOffset",
    4: "startAddrsCoarseOffset",
    5: "modLfoToPitch",
    6: "vibLfoToPitch",
    7: "modEnvToPitch",
    8: "initialFilterFc",
    9: "initialFilterQ",
    10: "modLfoToFilterFc",
    11: "modEnvToFilterFc",
    12: "modLfoToVolume",
    13: "unused1",
    14: "chorusEffectsSend",
    15: "reverbEffectsSend",
    16: "pan",
    17: "unused2",
    18: "unused3",
    19: "unused4",
    20: "delayModLFO",
    21: "freqModLFO",
    22: "delayVibLFO",
    23: "freqVibLFO",
    24: "delayModEnv",
    25: "attackModEnv",
    26: "holdModEnv",
    27: "decayModEnv",
    28: "sustainModEnv",
    29: "releaseModEnv",
    30: "keynumToModEnvHold",
    31: "keynumToModEnvDecay",
    32: "delayVolEnv",
    33: "attackVolEnv",
    34: "holdVolEnv",
    35: "decayVolEnv",
    36: "sustainVolEnv",
    37: "releaseVolEnv",
    38: "keynumToVolEnvHold",
    39: "keynumToVolEnvDecay",
    40: "instrument",
    41: "reserved1",
    42: "keyRange",
    43: "velRange",
    44: "startloopAddrsCoarse",
    45: "keynum",
    46: "velocity",
    47: "initialAttenuation",
    48: "reserved2",
    49: "endloopAddrsCoarse",
    50: "coarseTune",
    51: "fineTune",
    52: "sampleID",
    53: "sampleModes",
    54: "reserved3",
    55: "scaleTuning",
    56: "exclusiveClass",
    57: "overridingRootKey",
    58: "unused5",
    59: "endAddrsCoarseOffset",
    60: "modEnvToFilterFc",
    61: "modLfoToFilterFc2",
    62: "volEnvDelay",
    63: "volEnvAttack",
    64: "volEnvHold",
    65: "volEnvDecay"
}


# ===== GENERATOR DEFAULTS =====

# Default values for all generators (SF2 specification section 8.1)
GENERATOR_DEFAULTS: Dict[int, int] = {
    # Sample addressing
    0: 0,      # startAddrsOffset
    1: 0,      # endAddrsOffset
    2: 0,      # startloopAddrsOffset
    3: 0,      # endloopAddrsOffset
    4: 0,      # startAddrsCoarseOffset
    5: 0,      # modLfoToPitch
    6: 0,      # vibLfoToPitch
    7: 0,      # modEnvToPitch

    # Filter
    8: 13500,  # initialFilterFc (~8.5kHz in cents above 8.175Hz)
    9: 0,      # initialFilterQ
    10: 0,     # modLfoToFilterFc
    11: 0,     # modEnvToFilterFc

    # Volume envelope
    12: 0,     # modLfoToVolume
    13: 0,     # unused1
    14: 0,     # chorusEffectsSend
    15: 0,     # reverbEffectsSend
    16: 0,     # pan
    17: 0,     # unused2
    18: 0,     # unused3
    19: 0,     # unused4
    20: -12000, # delayModLFO

    # LFO
    21: 0,     # freqModLFO
    22: -12000, # delayVibLFO
    23: 0,     # freqVibLFO
    24: -12000, # delayModEnv
    25: -12000, # attackModEnv
    26: -12000, # holdModEnv
    27: -12000, # decayModEnv

    # More envelope
    28: 0,     # sustainModEnv
    29: -12000, # releaseModEnv
    30: 0,     # keynumToModEnvHold
    31: 0,     # keynumToModEnvDecay
    32: -12000, # delayVolEnv
    33: -12000, # attackVolEnv
    34: -12000, # holdVolEnv
    35: -12000, # decayVolEnv

    # Volume envelope completion
    36: 0,     # sustainVolEnv
    37: -12000, # releaseVolEnv
    38: 0,     # keynumToVolEnvHold
    39: 0,     # keynumToVolEnvDecay
    40: 0,     # instrument
    41: 0,     # reserved1
    42: 32512, # keyRange (0x7F00 = full range 0-127)
    43: 32512, # velRange (0x7F00 = full range 0-127)

    # Sample manipulation
    44: 0,     # startloopAddrsCoarse
    45: -1,    # keynum (-1 = use sample root key)
    46: -1,    # velocity (-1 = use note velocity)
    47: 0,     # initialAttenuation
    48: 0,     # reserved2
    49: 0,     # endloopAddrsCoarse
    50: 0,     # coarseTune
    51: 0,     # fineTune

    # More tuning and effects
    52: 0,     # sampleID
    53: 0,     # sampleModes
    54: 0,     # reserved3
    55: 100,   # scaleTuning (100 cents per semitone)
    56: 0,     # exclusiveClass
    57: -1,    # overridingRootKey (-1 = use sample root key)
    58: 0,     # unused5
    59: 0,     # endAddrsCoarseOffset

    # Legacy/duplicates
    60: 0,     # modEnvToFilterFc
    61: 0,     # modLfoToFilterFc2
    62: -12000, # volEnvDelay
    63: -12000, # volEnvAttack
    64: -12000, # volEnvHold
    65: -12000, # volEnvDecay
}


# ===== MODULATOR SOURCES =====

class ModulatorSource(IntEnum):
    """Modulator source operators (SF2 specification section 8.2.1)."""
    NO_CONTROLLER = 0
    NOTE_ON_VELOCITY = 2
    NOTE_ON_KEY_NUMBER = 3
    POLY_PRESSURE = 10
    CHANNEL_PRESSURE = 13
    PITCH_WHEEL = 14
    PITCH_WHEEL_SENSITIVITY = 16

    # MIDI CC sources (17-31 for CC 1-15, 52-76 for CC 16-40, etc.)
    # CC 1 = 17, CC 2 = 18, ..., CC 127 = 144
    @staticmethod
    def cc_controller(cc_number: int) -> int:
        """Convert MIDI CC number to SF2 modulator source."""
        if 0 <= cc_number <= 127:
            return 17 + cc_number
        raise ValueError(f"Invalid CC number: {cc_number}")


# ===== MODULATOR TRANSFORMS =====

class ModulatorTransform(IntEnum):
    """Modulator transform types (SF2 specification section 8.2.3)."""
    LINEAR = 0
    ABSOLUTE_VALUE = 1


# ===== SAMPLE FORMATS =====

class SampleType(IntEnum):
    """Sample type flags (SF2 specification section 3.6)."""
    MONO_SAMPLE = 1
    RIGHT_SAMPLE = 2
    LEFT_SAMPLE = 4
    LINKED_SAMPLE = 8
    MONO_24BIT = 0x8001     # ROM mono sample
    RIGHT_24BIT = 0x8002    # ROM right sample
    LEFT_24BIT = 0x8004     # ROM left sample
    LINKED_24BIT = 0x8008   # ROM linked sample


# ===== SF2 SPECIFICATION CONSTANTS =====

class SF2Spec:
    """SF2 specification constants and limits."""

    # File format
    VERSION_MAJOR = 2
    VERSION_MINOR = 1

    # Structure sizes (in bytes)
    PRESET_HEADER_SIZE = 38
    INSTRUMENT_HEADER_SIZE = 22
    SAMPLE_HEADER_SIZE = 46
    BAG_ENTRY_SIZE = 4       # gen_ndx (2) + mod_ndx (2)
    GEN_ENTRY_SIZE = 4       # gen_type (2) + amount (2, signed)
    MOD_ENTRY_SIZE = 10      # Complete modulator structure

    # Limits
    MAX_PRESETS = 128
    MAX_INSTRUMENTS = 1000
    MAX_SAMPLES = 1000
    MAX_ZONES_PER_PRESET = 100
    MAX_ZONES_PER_INSTRUMENT = 100

    # Time conversion (SF2 uses 1200 cents = 1 octave for envelopes)
    CENTS_TO_SECONDS_FACTOR = 1200.0

    # Filter conversion
    FILTER_FC_BASE = 8.175798915643707  # A-1 in Hz
    FILTER_FC_CENTS_FACTOR = 1200.0      # Cents per octave


# ===== UTILITY FUNCTIONS =====

def cents_to_frequency(cents: int) -> float:
    """
    Convert SF2 cents value to frequency in Hz.

    Args:
        cents: Cents value (relative to A-1 = 0 cents)

    Returns:
        Frequency in Hz
    """
    return SF2Spec.FILTER_FC_BASE * (2.0 ** (cents / SF2Spec.FILTER_FC_CENTS_FACTOR))


def frequency_to_cents(frequency: float) -> int:
    """
    Convert frequency in Hz to SF2 cents value.

    Args:
        frequency: Frequency in Hz

    Returns:
        Cents value (relative to A-1 = 0 cents)
    """
    if frequency <= 0:
        return 0
    return int(SF2Spec.FILTER_FC_CENTS_FACTOR * math.log2(frequency / SF2Spec.FILTER_FC_BASE))


def timecents_to_seconds(timecents: int) -> float:
    """
    Convert SF2 timecents to seconds.

    Args:
        timecents: Time in timecents

    Returns:
        Time in seconds
    """
    if timecents == -12000:  # Special case: no delay/attack/etc.
        return 0.0
    return 2.0 ** (timecents / SF2Spec.CENTS_TO_SECONDS_FACTOR)


def seconds_to_timecents(seconds: float) -> int:
    """
    Convert seconds to SF2 timecents.

    Args:
        seconds: Time in seconds

    Returns:
        Time in timecents
    """
    if seconds <= 0:
        return -12000
    return int(SF2Spec.CENTS_TO_SECONDS_FACTOR * math.log2(seconds))


def key_range_to_bytes(low: int, high: int) -> int:
    """
    Convert key range to SF2 byte format.

    Args:
        low: Low key (0-127)
        high: High key (0-127)

    Returns:
        SF2 range value (16-bit)
    """
    return (high << 8) | low


def vel_range_to_bytes(low: int, high: int) -> int:
    """
    Convert velocity range to SF2 byte format.

    Args:
        low: Low velocity (0-127)
        high: High velocity (0-127)

    Returns:
        SF2 range value (16-bit)
    """
    return (high << 8) | low


def bytes_to_key_range(range_bytes: int) -> Tuple[int, int]:
    """
    Convert SF2 range bytes to key range.

    Args:
        range_bytes: SF2 range value (16-bit)

    Returns:
        Tuple of (low_key, high_key)
    """
    low = range_bytes & 0xFF
    high = (range_bytes >> 8) & 0xFF
    return low, high


def bytes_to_vel_range(range_bytes: int) -> Tuple[int, int]:
    """
    Convert SF2 range bytes to velocity range.

    Args:
        range_bytes: SF2 range value (16-bit)

    Returns:
        Tuple of (low_velocity, high_velocity)
    """
    low = range_bytes & 0xFF
    high = (range_bytes >> 8) & 0xFF
    return low, high


# ===== VALIDATION CONSTANTS =====

class ValidationLimits:
    """Validation limits for SF2 data."""

    # Generator value ranges
    GEN_VALUE_MIN = -32768
    GEN_VALUE_MAX = 32767

    # MIDI note ranges
    MIDI_NOTE_MIN = 0
    MIDI_NOTE_MAX = 127

    # Velocity ranges
    VELOCITY_MIN = 0
    VELOCITY_MAX = 127

    # Attenuation (0 = full volume, 1440 = silence)
    ATTENUATION_MIN = 0
    ATTENUATION_MAX = 1440

    # Pan (-500 to +500, 0 = center)
    PAN_MIN = -500
    PAN_MAX = 500

    # Filter cutoff (1500 = 20Hz, 13500 = ~8.5kHz)
    FILTER_FC_MIN = 1500
    FILTER_FC_MAX = 13500

    # Filter Q (0 = 1 pole, 960 = 960/10 = 96 poles)
    FILTER_Q_MIN = 0
    FILTER_Q_MAX = 960

    # Effects sends (0 = no effect, 1000 = max send)
    EFFECTS_SEND_MIN = 0
    EFFECTS_SEND_MAX = 1000
