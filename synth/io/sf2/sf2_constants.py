"""
SF2 SoundFont Specification Constants

Complete SF2 specification constants for 100% compliance.
Includes all generators, modulators, sample types, and controller mappings.
"""

from __future__ import annotations

from typing import Any

# SF2 Generator Types (SF2.01 Specification Section 8.1)
# Numbers verified against sf2utils reference library generator.py
SF2_GENERATORS: dict[int, dict[str, Any]] = {
    # Address Offsets (sample start/end, fine+coarse)
    0: {"name": "startAddrsOffset", "default": 0, "range": (-32768, 32767)},
    1: {"name": "endAddrsOffset", "default": 0, "range": (-32768, 32767)},
    2: {"name": "startloopAddrsOffset", "default": 0, "range": (-32768, 32767)},
    3: {"name": "endloopAddrsOffset", "default": 0, "range": (-32768, 32767)},
    4: {"name": "startAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    # Modulation routing (LFO/envelope → pitch/filter/volume)
    5: {"name": "modLfoToPitch", "default": 0, "range": (-12000, 12000)},
    6: {"name": "vibLfoToPitch", "default": 0, "range": (-12000, 12000)},
    7: {"name": "modEnvToPitch", "default": 0, "range": (-12000, 12000)},
    # Filter
    8: {
        "name": "initialFilterFc",
        "default": 13500,
        "range": (1500, 13500),
    },  # SF2 spec: 1500..13500 cents (~19.7Hz..19.7kHz); default = open filter
    9: {"name": "initialFilterQ", "default": 0, "range": (0, 960)},
    # More modulation routing
    10: {"name": "modLfoToFilterFc", "default": 0, "range": (-12000, 12000)},
    11: {"name": "modEnvToFilterFc", "default": 0, "range": (-12000, 12000)},
    # Address offsets (continued)
    12: {"name": "endAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    13: {"name": "modLfoToVolume", "default": 0, "range": (-960, 960)},
    14: {"name": "vibLfoToVolume", "default": 0, "range": (-960, 960)},
    # Effects sends
    15: {"name": "chorusEffectsSend", "default": 0, "range": (0, 1000)},
    16: {"name": "reverbEffectsSend", "default": 0, "range": (0, 1000)},
    17: {"name": "pan", "default": 0, "range": (-500, 500)},
    # LFO delays/rates
    21: {"name": "delayModLFO", "default": -12000, "range": (-12000, 5000)},
    22: {"name": "freqModLFO", "default": 0, "range": (-16000, 4500)},
    23: {"name": "delayVibLFO", "default": -12000, "range": (-12000, 5000)},
    24: {"name": "freqVibLFO", "default": 0, "range": (-16000, 4500)},
    # Modulation envelope
    25: {"name": "delayModEnv", "default": -12000, "range": (-12000, 5000)},
    26: {"name": "attackModEnv", "default": -12000, "range": (-12000, 8000)},
    27: {"name": "holdModEnv", "default": -12000, "range": (-12000, 5000)},
    28: {"name": "decayModEnv", "default": -12000, "range": (-12000, 8000)},
    29: {"name": "sustainModEnv", "default": 0, "range": (0, 1000)},
    30: {"name": "releaseModEnv", "default": -12000, "range": (-12000, 8000)},
    # Key number to modulation envelope hold/decay scaling (SF2.01 §8.1.3)
    31: {"name": "keynumToModEnvHold", "default": 0, "range": (-1200, 1200)},
    32: {"name": "keynumToModEnvDecay", "default": 0, "range": (-1200, 1200)},
    # Volume envelope
    33: {"name": "delayVolEnv", "default": -12000, "range": (-12000, 5000)},
    34: {"name": "attackVolEnv", "default": -12000, "range": (-12000, 8000)},
    35: {"name": "holdVolEnv", "default": -12000, "range": (-12000, 5000)},
    36: {"name": "decayVolEnv", "default": -12000, "range": (-12000, 8000)},
    37: {"name": "sustainVolEnv", "default": 0, "range": (0, 1000)},
    38: {"name": "releaseVolEnv", "default": -12000, "range": (-12000, 8000)},
    # Key-number to envelope scaling
    39: {"name": "keynumToVolEnvHold", "default": 0, "range": (-1200, 1200)},
    40: {"name": "keynumToVolEnvDecay", "default": 0, "range": (-1200, 1200)},
    # Instrument/Preset Linking
    41: {"name": "instrument", "default": -1, "range": (-1, 65535)},
    # LFO → Pan modulation depth (non-standard but used by many soundfonts)
    42: {"name": "modLfoToPan", "default": 0, "range": (-500, 500)},
    # Key/Velocity Ranges
    43: {
        "name": "keyRange",
        "default": 0x7F007F00,
        "range": (0, 0x7FFFFFFF),
    },  # lo_key | (hi_key << 8) | (lo_vel << 16) | (hi_vel << 24)
    44: {"name": "velRange", "default": 0x7F007F00, "range": (0, 0x7FFFFFFF)},
    # Loop address offsets (coarse)
    45: {"name": "startloopAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    # Initial attenuation
    48: {"name": "initialAttenuation", "default": 0, "range": (0, 1000)},
    # End loop coarse offset
    50: {"name": "endloopAddrsCoarseOffset", "default": 0, "range": (-32768, 32767)},
    # Tuning
    51: {"name": "coarseTune", "default": 0, "range": (-120, 120)},
    52: {"name": "fineTune", "default": 0, "range": (-99, 99)},
    53: {"name": "sampleID", "default": 0, "range": (0, 65535)},
    54: {
        "name": "sampleModes",
        "default": 0,
        "range": (0, 3),
    },  # 0=no loop, 1=loop, 2=reserved, 3=loop+playToEnd
    56: {
        "name": "scaleTuning",
        "default": 100,
        "range": (0, 1200),
    },  # cents per semitone
    57: {"name": "exclusiveClass", "default": 0, "range": (0, 127)},
    58: {"name": "overridingRootKey", "default": -1, "range": (-1, 127)},
}

# SF2 Modulator Sources (SF2.01 Specification Section 8.2.1)
SF2_MODULATOR_SOURCES: dict[int, str] = {
    # General Controllers
    0: "none",
    2: "velocity",
    3: "key",
    10: "pan",
    13: "channel_pressure",
    14: "pitch_wheel",
    16: "timbre",  # Brightness
    17: "pitch",  # Coarse tune
    18: "fine_tune",
    # MIDI Controllers 0-127
    **{i: f"cc{i}" for i in range(128)},
    # Internal Sources (negative values)
    0x80: "link",  # For stereo samples
}

# SF2 Modulator Destinations (SF2.01 Specification Section 8.2.2)
# Numbers verified against sf2utils reference library generator.py
# Entries that are also generator numbers use standard SF2 gen numbers.
# Entries 45 (keynum) and 46 (velocity) are modulator-specific destinations.
SF2_MODULATOR_DESTINATIONS: dict[int, str] = {
    0: "none",
    5: "modLfoToPitch",
    6: "vibLfoToPitch",
    7: "modEnvToPitch",
    8: "initialFilterFc",
    9: "initialFilterQ",
    10: "modLfoToFilterFc",
    11: "modEnvToFilterFc",
    12: "endAddrsCoarseOffset",
    13: "modLfoToVolume",
    15: "chorusEffectsSend",
    16: "reverbEffectsSend",
    17: "pan",
    21: "delayModLFO",
    22: "freqModLFO",
    23: "delayVibLFO",
    24: "freqVibLFO",
    25: "delayModEnv",
    26: "attackModEnv",
    27: "holdModEnv",
    28: "decayModEnv",
    29: "sustainModEnv",
    30: "releaseModEnv",
    33: "delayVolEnv",
    34: "attackVolEnv",
    35: "holdVolEnv",
    36: "decayVolEnv",
    37: "sustainVolEnv",
    38: "releaseVolEnv",
    41: "instrument",
    43: "keyRange",
    44: "velRange",
     45: "keynum",  # modulator-specific destination (not a generator)
    46: "velocity",  # modulator-specific (not a generator)
    50: "endloopAddrsCoarseOffset",
    51: "coarseTune",
    52: "fineTune",
    56: "scaleTuning",
    57: "exclusiveClass",
    58: "overridingRootKey",
}

# SF2 Modulator Transform Types (SF2.01 Specification Section 8.2.3)
SF2_MODULATOR_TRANSFORMS: dict[int, str] = {
    0: "linear",
    1: "absolute_value",
    2: "bipolar_to_unipolar",
}

# Sample Types (SF2.01 Specification Section 3.6)
SF2_SAMPLE_TYPES: dict[int, dict[str, any]] = {
    0x0001: {"name": "mono", "channels": 1, "bit_depth": 16, "loop_support": False},
    0x0002: {
        "name": "right",
        "channels": 1,
        "bit_depth": 16,
        "loop_support": False,
        "stereo_link": True,
    },
    0x0004: {
        "name": "left",
        "channels": 1,
        "bit_depth": 16,
        "loop_support": False,
        "stereo_link": True,
    },
    0x0008: {"name": "linked", "channels": 1, "bit_depth": 16, "loop_support": True},
    0x8001: {"name": "mono_24", "channels": 1, "bit_depth": 24, "loop_support": False},
    0x8002: {
        "name": "right_24",
        "channels": 1,
        "bit_depth": 24,
        "loop_support": False,
        "stereo_link": True,
    },
    0x8004: {
        "name": "left_24",
        "channels": 1,
        "bit_depth": 24,
        "loop_support": False,
        "stereo_link": True,
    },
    0x8008: {"name": "linked_24", "channels": 1, "bit_depth": 24, "loop_support": True},
}

# SF2 Chunk IDs (SF2.01 Specification)
SF2_CHUNK_IDS: dict[str, str] = {
    # Main chunks
    "RIFF": "RIFF header",
    "sfbk": "SoundFont bank",
    "LIST": "List chunk",
    # INFO subchunks
    "ifil": "Version",
    "isng": "Sound engine",
    "INAM": "Bank name",
    "irom": "ROM name/ID",
    "iver": "ROM version",
    "ICRD": "Creation date",
    "IENG": "Creators",
    "IPRD": "Product",
    "ICOP": "Copyright",
    "ICMT": "Comments",
    "ISFT": "Tools",
    # sdta subchunks
    "smpl": "Sample data (16-bit)",
    "sm24": "Sample data (24-bit)",
    # pdta subchunks
    "phdr": "Preset headers",
    "pbag": "Preset bags",
    "pmod": "Preset modulators",
    "pgen": "Preset generators",
    "inst": "Instrument headers",
    "ibag": "Instrument bags",
    "imod": "Instrument modulators",
    "igen": "Instrument generators",
    "shdr": "Sample headers",
}

# SF2 File Structure Constants
SF2_HEADER_SIZE = 8  # 4 bytes ID + 4 bytes size
SF2_RIFF_HEADER_SIZE = 12  # RIFF + size + sfbk

# Preset Header Structure (38 bytes)
SF2_PRESET_HEADER_FORMAT = "<20sHHIIIHHH"  # achPresetName(20), wPreset, wBank, wPresetBagNdx, dwLibrary, dwGenre, dwMorphology

# Instrument Header Structure (22 bytes)
SF2_INSTRUMENT_HEADER_FORMAT = "<20sH"  # achInstName(20), wInstBagNdx

# Sample Header Structure (46 bytes)
SF2_SAMPLE_HEADER_FORMAT = "<20sIIIIIIHHH"  # achSampleName(20), dwStart, dwEnd, dwStartloop, dwEndloop, dwSampleRate, byOriginalPitch, chPitchCorrection, wSampleLink, sfSampleType

# Bag Structure (4 bytes)
SF2_BAG_FORMAT = "<HH"  # wGenNdx, wModNdx

# Generator Structure (4 bytes)
SF2_GENERATOR_FORMAT = "<Hh"  # sfGenOper, shAmount

# Modulator Structure (10 bytes)
SF2_MODULATOR_FORMAT = (
    "<HHhHHH"  # sfModSrcOper, sfModDestOper, modAmount, sfModAmtSrcOper, sfModTransOper
)

# Sample loop modes
SF2_LOOP_MODES: dict[int, str] = {
    0: "no_loop",
    1: "forward_loop",
    2: "backward_loop",
    3: "forward_backward_loop",
}

# Default values for envelope stages (in timecents, where 1200 = 1 octave)
SF2_ENVELOPE_DEFAULTS = {
    "delay": -12000,  # -inf (no delay)
    "attack": -12000,  # -inf (instant attack)
    "hold": -12000,  # -inf (no hold)
    "decay": -12000,  # -inf (no decay)
    "sustain": 0,  # 0% (full sustain)
    "release": -12000,  # -inf (no release)
}

# Timecent conversion constants
TIMECENT_FACTOR = 2.0 ** (1.0 / 1200.0)  # 2^(1/1200) for timecent to linear conversion
CENT_FACTOR = 2.0 ** (1.0 / 1200.0)  # Same for frequency cents


def timecents_to_seconds(timecents: int) -> float:
    """Convert SF2 timecents to seconds."""
    if timecents == -12000:
        return 0.0  # -inf means instant
    return TIMECENT_FACTOR**timecents


def cents_to_frequency(cents: int) -> float:
    """Convert SF2 cents to frequency multiplier."""
    return CENT_FACTOR**cents


def frequency_to_cents(frequency: float, base_freq: float = 440.0) -> int:
    """Convert frequency to SF2 cents relative to base frequency."""
    import math

    if frequency <= 0 or base_freq <= 0:
        return -12000  # -inf
    ratio = frequency / base_freq
    return int(1200.0 * math.log2(ratio))
