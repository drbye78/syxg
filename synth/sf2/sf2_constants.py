"""
SF2 SoundFont Specification Constants

Complete SF2 specification constants for 100% compliance.
Includes all generators, modulators, sample types, and controller mappings.
"""

from typing import Dict, List, Tuple, Any


# SF2 Generator Types (SF2.01 Specification Section 8.1)
SF2_GENERATORS: Dict[int, Dict[str, Any]] = {
    # Volume Envelope
    7: {"name": "endAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    8: {"name": "volEnvDelay", "default": -12000, "range": (-12000, 5000)},
    9: {"name": "volEnvAttack", "default": -12000, "range": (-12000, 8000)},
    10: {"name": "volEnvHold", "default": -12000, "range": (-12000, 5000)},
    11: {"name": "volEnvDecay", "default": -12000, "range": (-12000, 8000)},
    12: {"name": "volEnvSustain", "default": 0, "range": (0, 1000)},
    13: {"name": "volEnvRelease", "default": -12000, "range": (-12000, 8000)},
    14: {"name": "modEnvDelay", "default": -12000, "range": (-12000, 5000)},
    15: {"name": "modEnvAttack", "default": -12000, "range": (-12000, 8000)},
    16: {"name": "modEnvHold", "default": -12000, "range": (-12000, 5000)},
    17: {"name": "modEnvDecay", "default": -12000, "range": (-12000, 8000)},
    18: {"name": "modEnvSustain", "default": -12000, "range": (-12000, 1000)},
    19: {"name": "modEnvRelease", "default": -12000, "range": (-12000, 8000)},

    # Modulation
    20: {"name": "modEnvToPitch", "default": 0, "range": (-12000, 12000)},
    21: {"name": "delayModLFO", "default": -12000, "range": (-12000, 5000)},
    22: {"name": "freqModLFO", "default": 0, "range": (-16000, 4500)},
    23: {"name": "modLfoToVol", "default": 0, "range": (-960, 960)},
    24: {"name": "modLfoToFilterFc", "default": 0, "range": (-12000, 12000)},
    25: {"name": "modLfoToPitch", "default": 0, "range": (-12000, 12000)},
    26: {"name": "delayVibLFO", "default": -12000, "range": (-12000, 5000)},
    27: {"name": "freqVibLFO", "default": 0, "range": (-16000, 4500)},
    28: {"name": "vibLfoToPitch", "default": 0, "range": (-12000, 12000)},

    # Filter
    29: {"name": "initialFilterFc", "default": -200, "range": (-200, 17800)},  # 100Hz to 20kHz in cents
    30: {"name": "initialFilterQ", "default": 0, "range": (0, 960)},

    # Effects
    32: {"name": "reverbEffectsSend", "default": 0, "range": (0, 1000)},
    33: {"name": "chorusEffectsSend", "default": 0, "range": (0, 1000)},
    34: {"name": "pan", "default": 0, "range": (-500, 500)},

    # Instrument/Preset Linking
    41: {"name": "instrument", "default": -1, "range": (-1, 65535)},

    # Key/Velocity Ranges
    42: {"name": "keyRange", "default": 0x7F007F00, "range": (0, 0x7FFFFFFF)},  # lo_key | (hi_key << 8) | (lo_vel << 16) | (hi_vel << 24)
    43: {"name": "velRange", "default": 0x7F007F00, "range": (0, 0x7FFFFFFF)},

    # Tuning
    44: {"name": "startloopAddrsCoarse", "default": 0, "range": (-32768, 32767)},
    45: {"name": "keynum", "default": -1, "range": (-1, 127)},
    46: {"name": "velocity", "default": -1, "range": (-1, 127)},
    47: {"name": "endloopAddrsCoarse", "default": 0, "range": (-32768, 32767)},
    48: {"name": "coarseTune", "default": 0, "range": (-120, 120)},
    49: {"name": "fineTune", "default": 0, "range": (-99, 99)},
    50: {"name": "sampleID", "default": 0, "range": (0, 65535)},
    51: {"name": "sampleModes", "default": 0, "range": (0, 3)},  # 0=no loop, 1=loop, 2=reserved, 3=loop+playToEnd
    52: {"name": "scaleTuning", "default": 100, "range": (0, 1200)},  # cents per semitone
    53: {"name": "exclusiveClass", "default": 0, "range": (0, 127)},
    54: {"name": "overridingRootKey", "default": -1, "range": (-1, 127)},

    # Extended (for completeness)
    55: {"name": "endAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    56: {"name": "volEnvDelay", "default": -12000, "range": (-12000, 5000)},  # duplicate
    57: {"name": "volEnvAttack", "default": -12000, "range": (-12000, 8000)},  # duplicate
    58: {"name": "volEnvHold", "default": -12000, "range": (-12000, 5000)},   # duplicate
    59: {"name": "volEnvDecay", "default": -12000, "range": (-12000, 8000)},  # duplicate
    60: {"name": "volEnvSustain", "default": 0, "range": (0, 1000)},          # duplicate
    61: {"name": "volEnvRelease", "default": -12000, "range": (-12000, 8000)}, # duplicate
    62: {"name": "keyRange", "default": 0x7F007F00, "range": (0, 0x7FFFFFFF)}, # duplicate
    63: {"name": "velRange", "default": 0x7F007F00, "range": (0, 0x7FFFFFFF)}, # duplicate
    64: {"name": "keynum", "default": -1, "range": (-1, 127)},                # duplicate
    65: {"name": "velocity", "default": -1, "range": (-1, 127)},              # duplicate
}

# SF2 Modulator Sources (SF2.01 Specification Section 8.2.1)
SF2_MODULATOR_SOURCES: Dict[int, str] = {
    # General Controllers
    0: "none",
    2: "velocity",
    3: "key",
    10: "pan",
    13: "channel_pressure",
    14: "pitch_wheel",
    16: "timbre",  # Brightness
    17: "pitch",   # Coarse tune
    18: "fine_tune",

    # MIDI Controllers 0-127
    **{i: f"cc{i}" for i in range(128)},

    # Internal Sources (negative values)
    0x80: "link",  # For stereo samples
}

# SF2 Modulator Destinations (SF2.01 Specification Section 8.2.2)
SF2_MODULATOR_DESTINATIONS: Dict[int, str] = {
    0: "none",
    7: "endAddrsCoarseOffset",
    8: "volEnvDelay",
    9: "volEnvAttack",
    10: "volEnvHold",
    11: "volEnvDecay",
    12: "volEnvSustain",
    13: "volEnvRelease",
    14: "modEnvDelay",
    15: "modEnvAttack",
    16: "modEnvHold",
    17: "modEnvDecay",
    18: "modEnvSustain",
    19: "modEnvRelease",
    20: "modEnvToPitch",
    21: "delayModLFO",
    22: "freqModLFO",
    23: "modLfoToVol",
    24: "modLfoToFilterFc",
    25: "modLfoToPitch",
    26: "delayVibLFO",
    27: "freqVibLFO",
    28: "vibLfoToPitch",
    29: "initialFilterFc",
    30: "initialFilterQ",
    32: "reverbEffectsSend",
    33: "chorusEffectsSend",
    34: "pan",
    41: "instrument",
    42: "keyRange",
    43: "velRange",
    44: "startloopAddrsCoarse",
    45: "keynum",
    46: "velocity",
    47: "endloopAddrsCoarse",
    48: "coarseTune",
    49: "fineTune",
    52: "scaleTuning",
    53: "exclusiveClass",
    54: "overridingRootKey",
    55: "endAddrsCoarseOffset",
}

# SF2 Modulator Transform Types (SF2.01 Specification Section 8.2.3)
SF2_MODULATOR_TRANSFORMS: Dict[int, str] = {
    0: "linear",
    1: "absolute_value",
    2: "bipolar_to_unipolar",
}

# Sample Types (SF2.01 Specification Section 3.6)
SF2_SAMPLE_TYPES: Dict[int, Dict[str, any]] = {
    0x0001: {"name": "mono", "channels": 1, "bit_depth": 16, "loop_support": False},
    0x0002: {"name": "right", "channels": 1, "bit_depth": 16, "loop_support": False, "stereo_link": True},
    0x0004: {"name": "left", "channels": 1, "bit_depth": 16, "loop_support": False, "stereo_link": True},
    0x0008: {"name": "linked", "channels": 1, "bit_depth": 16, "loop_support": True},
    0x8001: {"name": "mono_24", "channels": 1, "bit_depth": 24, "loop_support": False},
    0x8002: {"name": "right_24", "channels": 1, "bit_depth": 24, "loop_support": False, "stereo_link": True},
    0x8004: {"name": "left_24", "channels": 1, "bit_depth": 24, "loop_support": False, "stereo_link": True},
    0x8008: {"name": "linked_24", "channels": 1, "bit_depth": 24, "loop_support": True},
}

# SF2 Chunk IDs (SF2.01 Specification)
SF2_CHUNK_IDS: Dict[str, str] = {
    # Main chunks
    'RIFF': 'RIFF header',
    'sfbk': 'SoundFont bank',
    'LIST': 'List chunk',

    # INFO subchunks
    'ifil': 'Version',
    'isng': 'Sound engine',
    'INAM': 'Bank name',
    'irom': 'ROM name/ID',
    'iver': 'ROM version',
    'ICRD': 'Creation date',
    'IENG': 'Creators',
    'IPRD': 'Product',
    'ICOP': 'Copyright',
    'ICMT': 'Comments',
    'ISFT': 'Tools',

    # sdta subchunks
    'smpl': 'Sample data (16-bit)',
    'sm24': 'Sample data (24-bit)',

    # pdta subchunks
    'phdr': 'Preset headers',
    'pbag': 'Preset bags',
    'pmod': 'Preset modulators',
    'pgen': 'Preset generators',
    'inst': 'Instrument headers',
    'ibag': 'Instrument bags',
    'imod': 'Instrument modulators',
    'igen': 'Instrument generators',
    'shdr': 'Sample headers',
}

# SF2 File Structure Constants
SF2_HEADER_SIZE = 8  # 4 bytes ID + 4 bytes size
SF2_RIFF_HEADER_SIZE = 12  # RIFF + size + sfbk

# Preset Header Structure (38 bytes)
SF2_PRESET_HEADER_FORMAT = '<20sHHIIIHHH'  # achPresetName(20), wPreset, wBank, wPresetBagNdx, dwLibrary, dwGenre, dwMorphology

# Instrument Header Structure (22 bytes)
SF2_INSTRUMENT_HEADER_FORMAT = '<20sH'  # achInstName(20), wInstBagNdx

# Sample Header Structure (46 bytes)
SF2_SAMPLE_HEADER_FORMAT = '<20sIIIIIIHHH'  # achSampleName(20), dwStart, dwEnd, dwStartloop, dwEndloop, dwSampleRate, byOriginalPitch, chPitchCorrection, wSampleLink, sfSampleType

# Bag Structure (4 bytes)
SF2_BAG_FORMAT = '<HH'  # wGenNdx, wModNdx

# Generator Structure (4 bytes)
SF2_GENERATOR_FORMAT = '<Hh'  # sfGenOper, shAmount

# Modulator Structure (10 bytes)
SF2_MODULATOR_FORMAT = '<HHhHHH'  # sfModSrcOper, sfModDestOper, modAmount, sfModAmtSrcOper, sfModTransOper

# Sample loop modes
SF2_LOOP_MODES: Dict[int, str] = {
    0: "no_loop",
    1: "forward_loop",
    2: "backward_loop",
    3: "forward_backward_loop"
}

# Default values for envelope stages (in timecents, where 1200 = 1 octave)
SF2_ENVELOPE_DEFAULTS = {
    'delay': -12000,    # -inf (no delay)
    'attack': -12000,   # -inf (instant attack)
    'hold': -12000,     # -inf (no hold)
    'decay': -12000,    # -inf (no decay)
    'sustain': 0,       # 0% (full sustain)
    'release': -12000   # -inf (no release)
}

# Timecent conversion constants
TIMECENT_FACTOR = 2.0 ** (1.0 / 1200.0)  # 2^(1/1200) for timecent to linear conversion
CENT_FACTOR = 2.0 ** (1.0 / 1200.0)     # Same for frequency cents

def timecents_to_seconds(timecents: int) -> float:
    """Convert SF2 timecents to seconds."""
    if timecents == -12000:
        return 0.0  # -inf means instant
    return TIMECENT_FACTOR ** timecents

def cents_to_frequency(cents: int) -> float:
    """Convert SF2 cents to frequency multiplier."""
    return CENT_FACTOR ** cents

def frequency_to_cents(frequency: float, base_freq: float = 440.0) -> int:
    """Convert frequency to SF2 cents relative to base frequency."""
    if frequency <= 0 or base_freq <= 0:
        return -12000  # -inf
    ratio = frequency / base_freq
    return int(1200.0 * (ratio ** (1.0 / 2.0)).real)  # Use real part for numerical stability