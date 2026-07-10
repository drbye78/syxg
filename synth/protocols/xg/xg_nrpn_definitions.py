"""
Canonical NRPN parameter definitions for the XG specification.

Single source of truth for XG MIDI NRPN (Non-Registered Parameter Number)
parameter addresses. Every MSB/LSB pair used in the XG spec is defined here
with its official name, value range, and description.

Bridges (synth/xgml/bridges/) are the sole consumers of this module.
Processing-layer code (synth/processing/effects/) should reference these
definitions to resolve any numbering conflicts.

Address scheme follows the official XG specification:
  MSB 1   = System Reverb
  MSB 2   = System Chorus / Variation (differentiated by LSB value range)
  MSB 3-31 = Channel-specific parameters
  MSB 32-39 = Multi-part effect routing
  MSB 40-47 = Drum kit / part setup
  MSB 48-63 = Drum note parameters
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Parameter Address
# ---------------------------------------------------------------------------


class ParameterAddress(NamedTuple):
    """A single NRPN parameter identified by (MSB, LSB).

    NRPN is sent as: CC 99 (MSB), CC 98 (LSB), CC 6 (Data MSB), CC 38 (Data LSB).
    """

    msb: int
    lsb: int


@dataclass
class ParameterDef:
    """Definition of an NRPN parameter: address, name, range, and description."""

    address: ParameterAddress
    name: str
    min_value: int = 0
    max_value: int = 127
    unit: str = ""
    description: str = ""


# =============================================================================
# MSB 1: System Reverb
# =============================================================================

REVERB_TYPE = ParameterAddress(1, 0)
REVERB_TIME = ParameterAddress(1, 1)
REVERB_HF_DAMPING = ParameterAddress(1, 2)
REVERB_BALANCE = ParameterAddress(1, 3)
REVERB_LEVEL = ParameterAddress(1, 4)
REVERB_PRE_DELAY = ParameterAddress(1, 5)
REVERB_DENSITY = ParameterAddress(1, 6)
REVERB_EARLY_LEVEL = ParameterAddress(1, 7)
REVERB_TAIL_LEVEL = ParameterAddress(1, 8)
REVERB_SHAPE = ParameterAddress(1, 9)
REVERB_GATE_TIME = ParameterAddress(1, 10)
REVERB_PRE_DELAY_SCALE = ParameterAddress(1, 11)

# =============================================================================
# MSB 2: System Chorus / Variation (type at LSB 0 splits the block)
# =============================================================================

CHORUS_TYPE = ParameterAddress(2, 0)
CHORUS_RATE = ParameterAddress(2, 1)
CHORUS_DEPTH = ParameterAddress(2, 2)
CHORUS_FEEDBACK = ParameterAddress(2, 3)
CHORUS_LEVEL = ParameterAddress(2, 4)
CHORUS_DELAY_OFFSET = ParameterAddress(2, 5)
CHORUS_OUTPUT = ParameterAddress(2, 6)
CHORUS_CROSS_FEEDBACK = ParameterAddress(2, 7)
CHORUS_LFO_WAVEFORM = ParameterAddress(2, 8)
CHORUS_PHASE_DIFF = ParameterAddress(2, 9)

# Variation is identified by LSB 0 with type values 0x00-0x41
VARIATION_TYPE = ParameterAddress(2, 0)
VARIATION_PARAM_1 = ParameterAddress(2, 1)
VARIATION_PARAM_2 = ParameterAddress(2, 2)
VARIATION_PARAM_3 = ParameterAddress(2, 3)
VARIATION_PARAM_4 = ParameterAddress(2, 4)
VARIATION_PARAM_5 = ParameterAddress(2, 5)

# =============================================================================
# MSB 3-4: Basic Channel Parameters (volume, pan, expression, pitch bend)
# =============================================================================

CHANNEL_VOLUME_COARSE = ParameterAddress(3, 0)
CHANNEL_VOLUME_FINE = ParameterAddress(3, 1)
CHANNEL_PAN_COARSE = ParameterAddress(3, 2)
CHANNEL_PAN_FINE = ParameterAddress(3, 3)
CHANNEL_EXPRESSION_COARSE = ParameterAddress(3, 4)
CHANNEL_EXPRESSION_FINE = ParameterAddress(3, 5)
CHANNEL_MODULATION_DEPTH = ParameterAddress(3, 6)
CHANNEL_MODULATION_SPEED = ParameterAddress(3, 7)

CHANNEL_PITCH_COARSE = ParameterAddress(4, 0)
CHANNEL_PITCH_FINE = ParameterAddress(4, 1)
CHANNEL_PITCH_BEND_RANGE = ParameterAddress(4, 2)
CHANNEL_PORTAMENTO_MODE = ParameterAddress(4, 3)
CHANNEL_PORTAMENTO_TIME = ParameterAddress(4, 4)
CHANNEL_PITCH_BALANCE = ParameterAddress(4, 5)
CHANNEL_PORTAMENTO_CONTROL = ParameterAddress(4, 6)
CHANNEL_POLYPHONIC_MODE = ParameterAddress(4, 7)
CHANNEL_PORTAMENTO_LEGATO = ParameterAddress(4, 8)
CHANNEL_STEREO_WIDTH = ParameterAddress(4, 9)

# =============================================================================
# MSB 5-6: Filter Parameters
# =============================================================================

FILTER_CUTOFF = ParameterAddress(5, 0)
FILTER_RESONANCE = ParameterAddress(5, 1)
FILTER_ENV_ATTACK = ParameterAddress(5, 2)
FILTER_ENV_DECAY = ParameterAddress(5, 3)
FILTER_ENV_SUSTAIN = ParameterAddress(5, 4)
FILTER_ENV_RELEASE = ParameterAddress(5, 5)
FILTER_BRIGHTNESS = ParameterAddress(5, 6)
FILTER_TYPE = ParameterAddress(5, 7)
FILTER_VELOCITY_SENSITIVITY = ParameterAddress(6, 0)
FILTER_KEY_SCALING = ParameterAddress(6, 1)
FILTER_VELOCITY_CURVE = ParameterAddress(6, 2)
FILVER_ATTACK_TIME = ParameterAddress(6, 3)

# =============================================================================
# MSB 7-8: Amp Envelope
# =============================================================================

AMP_ENV_ATTACK = ParameterAddress(7, 0)
AMP_ENV_DECAY = ParameterAddress(7, 1)
AMP_ENV_SUSTAIN = ParameterAddress(7, 2)
AMP_ENV_RELEASE = ParameterAddress(7, 3)
AMP_ENV_VELOCITY_SENSE = ParameterAddress(7, 4)
AMP_ENV_KEY_SCALING = ParameterAddress(7, 5)

AMP_ENV_ATTACK_DEPTH = ParameterAddress(8, 0)
AMP_ENV_DECAY_DEPTH = ParameterAddress(8, 1)
AMP_ENV_SUSTAIN_DEPTH = ParameterAddress(8, 2)
AMP_ENV_RELEASE_DEPTH = ParameterAddress(8, 3)

# =============================================================================
# MSB 9-10: LFO Parameters
# =============================================================================

LFO1_WAVEFORM = ParameterAddress(9, 0)
LFO1_SPEED = ParameterAddress(9, 1)
LFO1_DELAY = ParameterAddress(9, 2)
LFO1_FADE_TIME = ParameterAddress(9, 3)
LFO1_PITCH_DEPTH = ParameterAddress(9, 4)
LFO1_FILTER_DEPTH = ParameterAddress(9, 5)
LFO1_AMP_DEPTH = ParameterAddress(9, 6)
LFO1_PITCH_CONTROL = ParameterAddress(9, 7)

LFO2_WAVEFORM = ParameterAddress(10, 0)
LFO2_SPEED = ParameterAddress(10, 1)
LFO2_DELAY = ParameterAddress(10, 2)
LFO2_FADE_TIME = ParameterAddress(10, 3)
LFO2_PITCH_DEPTH = ParameterAddress(10, 4)
LFO2_FILTER_DEPTH = ParameterAddress(10, 5)
LFO2_AMP_DEPTH = ParameterAddress(10, 6)
LFO2_PITCH_CONTROL = ParameterAddress(10, 7)

# =============================================================================
# MSB 11-12: Effects Send
# =============================================================================

SEND_REVERB = ParameterAddress(11, 0)
SEND_CHORUS = ParameterAddress(11, 1)
SEND_VARIATION = ParameterAddress(11, 2)
SEND_DRY_LEVEL = ParameterAddress(11, 3)
INSERTION_SEND_L = ParameterAddress(11, 4)
INSERTION_SEND_R = ParameterAddress(11, 5)
INSERTION_CONNECTION = ParameterAddress(11, 6)
SEND_CHORUS_TO_REVERB = ParameterAddress(11, 7)

# =============================================================================
# MSB 13: Pitch Envelope
# =============================================================================

PITCH_ENV_ATTACK = ParameterAddress(13, 0)
PITCH_ENV_DECAY = ParameterAddress(13, 1)
PITCH_ENV_SUSTAIN = ParameterAddress(13, 2)
PITCH_ENV_RELEASE = ParameterAddress(13, 3)
PITCH_ENV_ATTACK_LEVEL = ParameterAddress(13, 4)
PITCH_ENV_DECAY_LEVEL = ParameterAddress(13, 5)
PITCH_ENV_SUSTAIN_LEVEL = ParameterAddress(13, 6)
PITCH_ENV_RELEASE_LEVEL = ParameterAddress(13, 7)

# =============================================================================
# MSB 14: Pitch LFO
# =============================================================================

PITCH_LFO_WAVEFORM = ParameterAddress(14, 0)
PITCH_LFO_SPEED = ParameterAddress(14, 1)
PITCH_LFO_DELAY = ParameterAddress(14, 2)
PITCH_LFO_FADE_TIME = ParameterAddress(14, 3)
PITCH_LFO_DEPTH = ParameterAddress(14, 4)

# =============================================================================
# MSB 15-16: Controller Assignments (assignable controllers)
# =============================================================================

CTRL_ASSIGN_1 = ParameterAddress(15, 0)  # Mod Wheel
CTRL_ASSIGN_2 = ParameterAddress(15, 1)  # Foot Controller
CTRL_ASSIGN_3 = ParameterAddress(15, 2)  # Aftertouch
CTRL_ASSIGN_4 = ParameterAddress(15, 3)  # Breath Controller
CTRL_ASSIGN_5 = ParameterAddress(15, 4)  # General 1
CTRL_ASSIGN_6 = ParameterAddress(15, 5)  # General 2
CTRL_ASSIGN_7 = ParameterAddress(15, 6)  # General 3
CTRL_ASSIGN_8 = ParameterAddress(15, 7)  # General 4
CTRL_ASSIGN_9 = ParameterAddress(16, 0)  # Ribbon
CTRL_ASSIGN_10 = ParameterAddress(16, 1)  # General 5
CTRL_ASSIGN_11 = ParameterAddress(16, 2)  # General 6
CTRL_ASSIGN_12 = ParameterAddress(16, 3)  # General 7

# =============================================================================
# MSB 17-18: Scale / Micro Tuning
# =============================================================================

SCALE_TUNE_C = ParameterAddress(17, 0)
SCALE_TUNE_CS = ParameterAddress(17, 1)
SCALE_TUNE_D = ParameterAddress(17, 2)
SCALE_TUNE_DS = ParameterAddress(17, 3)
SCALE_TUNE_E = ParameterAddress(17, 4)
SCALE_TUNE_F = ParameterAddress(17, 5)
SCALE_TUNE_FS = ParameterAddress(17, 6)
SCALE_TUNE_G = ParameterAddress(17, 7)
SCALE_TUNE_GS = ParameterAddress(18, 0)
SCALE_TUNE_A = ParameterAddress(18, 1)
SCALE_TUNE_AS = ParameterAddress(18, 2)
SCALE_TUNE_B = ParameterAddress(18, 3)

MASTER_TUNE = ParameterAddress(18, 4)
MASTER_TRANSPOSE = ParameterAddress(18, 5)
TEMPERAMENT_SELECT = ParameterAddress(18, 6)

# =============================================================================
# MSB 19: Velocity / Element Reserve
# =============================================================================

VELOCITY_CURVE = ParameterAddress(19, 0)
VELOCITY_OFFSET = ParameterAddress(19, 1)
VELOCITY_RANGE_LOW = ParameterAddress(19, 2)
VELOCITY_RANGE_HIGH = ParameterAddress(19, 3)
ELEMENT_RESERVE = ParameterAddress(19, 4)

# =============================================================================
# MSB 32-34: Multi-Part Effect Routing (reverb/chorus/variation sends per part)
# =============================================================================

PART_REVERB_SEND = ParameterAddress(32, 0)  # + part number
PART_CHORUS_SEND = ParameterAddress(33, 0)  # + part number
PART_VARIATION_SEND = ParameterAddress(34, 0)  # + part number

def part_reverb_send(part: int) -> ParameterAddress:
    return ParameterAddress(32, part)

def part_chorus_send(part: int) -> ParameterAddress:
    return ParameterAddress(33, part)

def part_variation_send(part: int) -> ParameterAddress:
    return ParameterAddress(34, part)

# =============================================================================
# MSB 40-41: Drum Kit Assign
# =============================================================================

DRUM_KIT_NUMBER = ParameterAddress(40, 0)
DRUM_KIT_LEVEL = ParameterAddress(40, 3)
DRUM_KIT_PAN = ParameterAddress(40, 4)
DRUM_KIT_REVERB_SEND = ParameterAddress(40, 5)
DRUM_KIT_CHORUS_SEND = ParameterAddress(40, 6)
DRUM_KIT_VARIATION_SEND = ParameterAddress(40, 7)
DRUM_KIT_VELOCITY_CURVE = ParameterAddress(40, 8)
DRUM_KIT_ALT_PITCH = ParameterAddress(40, 9)
DRUM_KIT_DECAY = ParameterAddress(40, 10)
DRUM_KIT_VIBRATO_RATE = ParameterAddress(40, 11)
DRUM_KIT_VIBRATO_DEPTH = ParameterAddress(40, 12)

DRUM_KEY_ASSIGN = ParameterAddress(40, 2)    # note -> drum key
DRUM_WAVE_MSB = ParameterAddress(41, 1)
DRUM_WAVE_LSB = ParameterAddress(41, 0)

DRUM_COARSE_TUNE = ParameterAddress(41, 32)
DRUM_FINE_TUNE = ParameterAddress(41, 33)
DRUM_ATTACK_TIME = ParameterAddress(41, 34)
DRUM_DECAY_TIME = ParameterAddress(41, 35)
DRUM_FILTER_CUTOFF = ParameterAddress(41, 36)
DRUM_FILTER_RESONANCE = ParameterAddress(41, 37)
DRUM_EG_ATTACK = ParameterAddress(41, 38)
DRUM_EG_DECAY = ParameterAddress(41, 39)
DRUM_VELOCITY_PITCH_SENSE = ParameterAddress(41, 40)
DRUM_VELOCITY_FILTER_SENSE = ParameterAddress(41, 41)
DRUM_VELOCITY_AMP_SENSE = ParameterAddress(41, 42)
DRUM_LFO_RATE = ParameterAddress(41, 43)
DRUM_LFO_DEPTH = ParameterAddress(41, 44)
DRUM_LFO_WAVEFORM = ParameterAddress(41, 45)

# =============================================================================
# MSB 42-45: Multi-Part Setup
# =============================================================================

def part_voice_reserve(part: int) -> ParameterAddress:
    return ParameterAddress(42, part)

def part_mode(part: int) -> ParameterAddress:
    return ParameterAddress(43, part)

def part_level(part: int) -> ParameterAddress:
    return ParameterAddress(44, part)

def part_pan(part: int) -> ParameterAddress:
    return ParameterAddress(45, part)

# =============================================================================
# MSB 48-63: Drum Note Parameters (parameterized by note number + parameter index)
# =============================================================================

# Parameter index mapping for drum note parameters (used as LSB offset)
# Actual NRPN address: (48 + param_index, note_number)
class DrumNoteParam(Enum):
    """Parameter index for drum note NRPN (MSB = 48 + param_index)."""

    PITCH_COARSE = 0
    PITCH_FINE = 1
    LEVEL = 2
    PAN = 3
    REVERB_SEND = 4
    CHORUS_SEND = 5
    VARIATION_SEND = 6
    DECAY_TIME = 7
    ATTACK_TIME = 8
    FILTER_CUTOFF = 9
    FILTER_RESONANCE = 10
    LFO_RATE = 11
    LFO_DEPTH = 12
    EQ_LOW_GAIN = 13
    EQ_MID_GAIN = 14
    EQ_HIGH_GAIN = 15
    ALTERNATE_GROUP = 16
    MUTE_GROUP = 17


def drum_note_address(param: DrumNoteParam, note: int) -> ParameterAddress:
    """Get NRPN address for a drum note parameter.

    Args:
        param: The drum note parameter index.
        note: MIDI note number (0-127).

    Returns:
        (MSB, LSB) for the drum note NRPN.
    """
    return ParameterAddress(48 + param.value, note)


# =============================================================================
# Value Conversion Utilities
# =============================================================================

# Standard XG reverb types
XG_REVERB_TYPES_MAP: dict[int, str] = {
    0: "no_effect",
    1: "hall1",
    2: "hall2",
    3: "room1",
    4: "room2",
    5: "room3",
    6: "stage1",
    7: "stage2",
    8: "plate",
    9: "white_room",
    10: "tunnel",
    11: "canyon",
    12: "basement",
}

# Standard XG chorus types
XG_CHORUS_TYPES_MAP: dict[int, str] = {
    0: "chorus1",
    1: "chorus2",
    2: "chorus3",
    3: "chorus4",
    4: "chorus5",
    5: "celeste1",
    6: "celeste2",
    7: "celeste3",
    8: "celeste4",
    9: "celeste5",
    10: "flanger1",
    11: "flanger2",
    12: "flanger3",
    13: "flanger4",
    14: "flanger5",
    15: "flanger6",
    16: "symphonic1",
    17: "symphonic2",
}

# Standard XG variation types
XG_VARIATION_TYPES_MAP: dict[int, str] = {
    # Delays (0x00-0x0B)
    0: "delay_lcr",
    1: "delay_lr",
    2: "delay_center",
    3: "analog_delay_lcr",
    4: "analog_delay_lr",
    5: "analog_delay_center",
    6: "cross_delay",
    7: "tempo_delay_lcr",
    8: "tempo_delay_lr",
    9: "tempo_delay_center",
    10: "multi_tap_delay",
    11: "echo",
    # Choruses (0x10-0x19)
    16: "chorus1",
    17: "chorus2",
    18: "chorus3",
    19: "chorus4",
    20: "chorus5",
    21: "chorus6",
    22: "chorus7",
    23: "chorus8",
    24: "chorus9",
    25: "chorus10",
    # Flangers (0x20-0x27)
    32: "flanger1",
    33: "flanger2",
    34: "flanger3",
    35: "flanger4",
    36: "flanger5",
    37: "flanger6",
    38: "flanger7",
    39: "flanger8",
    # Distortion / Overdrive (0x30-0x35)
    48: "distortion1",
    49: "distortion2",
    50: "distortion3",
    51: "overdrive1",
    52: "overdrive2",
    53: "amp_simulator",
    # EQ (0x36-0x37)
    54: "spectral_tone",
    55: "parametric_eq",
    # Wah / Auto Wah (0x38)
    56: "auto_wah",
    # Phaser (0x39-0x3B)
    57: "phaser1",
    58: "phaser2",
    59: "phaser3",
    # Pitch Shift (0x3C-0x3F)
    60: "pitch_shift1",
    61: "pitch_shift2",
    62: "pitch_shift3",
    63: "pitch_shift4",
    # Rotary Speaker (0x40)
    64: "rotary_speaker",
    # Tremolo (0x41)
    65: "tremolo",
    # Auto Pan (0x42)
    66: "auto_pan",
    # Gate Reverb / Reverb Gate (0x43-0x44)
    67: "gate_reverb",
    68: "reverse_gate",
    # Compressor (0x45-0x46)
    69: "compressor",
    70: "limiter",
    # Enhancer (0x47)
    71: "enhancer",
}

# Insertion effect types
XG_INSERTION_TYPES_MAP: dict[int, str] = {
    0: "through",
    1: "stereo_eq",
    2: "stereo_graphic_eq",
    3: "stereo_parametric_eq",
    4: "enhancer",
    5: "overdrive",
    6: "distortion",
    7: "overdrive_to_chorus",
    8: "distortion_to_chorus",
    9: "chorus",
    10: "celeste",
    11: "flanger",
    12: "symphonic",
    13: "phaser",
    14: "auto_wah",
    15: "delay",
    16: "echo",
}

# LFO waveforms
XG_LFO_WAVEFORMS: dict[int, str] = {
    0: "sine",
    1: "triangle",
    2: "saw_up",
    3: "saw_down",
    4: "square",
    5: "sample_and_hold",
}


def nrpn_value_to_float(value: int, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Convert NRPN 7-bit value (0-127) to a float in [min_val, max_val]."""
    return min_val + (value / 127.0) * (max_val - min_val)


def float_to_nrpn_value(value: float, min_val: float = 0.0, max_val: float = 1.0) -> int:
    """Convert float in [min_val, max_val] to NRPN 7-bit value (0-127)."""
    normalized = (value - min_val) / (max_val - min_val)
    return max(0, min(127, round(normalized * 127)))


def note_name_to_midi(note_name: str) -> int:
    """Convert 'C4' → 60. Supports sharps (#) and flats (b)."""
    note_map = {
        "C": 0, "C#": 1, "Db": 1,
        "D": 2, "D#": 3, "Eb": 3,
        "E": 4, "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10,
        "B": 11,
    }
    name = note_name.strip()
    # Split note name into pitch class and octave
    # Octave is the trailing digits; pitch class is everything before
    i = 0
    while i < len(name) and not name[i].isdigit():
        i += 1
    note_part = name[:i]
    if i < len(name):
        octave = int(name[i:])
    else:
        octave = 4
    # Preserve case for flats ('b' must stay lowercase)
    # Normalize: first char uppercase, rest lowercase (so "C#" stays, "Db" stays)
    if len(note_part) == 1:
        note_part = note_part.upper()
    elif len(note_part) == 2:
        note_part = note_part[0].upper() + note_part[1].lower()
    return (octave + 1) * 12 + note_map.get(note_part, 60)


def midi_note_to_name(midi_note: int) -> str:
    """Convert 60 → 'C4'."""
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi_note // 12 - 1
    note = midi_note % 12
    return f"{note_names[note]}{octave}"
