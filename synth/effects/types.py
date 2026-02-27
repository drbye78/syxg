"""
XG Effects Data Types and Structures

This module defines all data types, structures, and enums used throughout
the XG effects processing subsystem. These are optimized for zero-allocation
processing with minimal memory overhead.
"""
from __future__ import annotations

import numpy as np
from typing import NamedTuple, Any
from enum import IntEnum, Enum


class XGProcessingState(Enum):
    """XG Effects Processing State"""
    IDLE = 0
    INITIALIZING = 1
    PROCESSING = 2
    RELEASE = 3


class XGReverbType(IntEnum):
    """XG Reverb Types (MSB 0, Type 1-24)"""
    HALL_1 = 1     # Small Hall
    HALL_2 = 2     # Medium Hall
    HALL_3 = 3     # Large Hall
    HALL_4 = 4     # Large Hall +
    HALL_5 = 5     # Large Hall ++
    HALL_6 = 6     # Large Hall +++
    HALL_7 = 7     # Large Hall ++++
    HALL_8 = 8     # Large Hall +++++
    ROOM_1 = 9     # Small Room
    ROOM_2 = 10    # Medium Room
    ROOM_3 = 11    # Large Room
    ROOM_4 = 12    # Large Room +
    ROOM_5 = 13    # Large Room ++
    ROOM_6 = 14    # Large Room +++
    ROOM_7 = 15    # Large Room ++++
    ROOM_8 = 16    # Large Room +++++
    PLATE_1 = 17   # Plate Reverb 1
    PLATE_2 = 18   # Plate Reverb 2
    PLATE_3 = 19   # Plate Reverb 3
    PLATE_4 = 20   # Plate Reverb 4
    PLATE_5 = 21   # Plate Reverb 5
    PLATE_6 = 22   # Plate Reverb 6
    PLATE_7 = 23   # Plate Reverb 7
    PLATE_8 = 24   # Plate Reverb 8


class XGChorusType(IntEnum):
    """XG Chorus Types (MSB 2, LSB 0-1)"""
    CHORUS_1 = 0
    CHORUS_2 = 1
    CELESTE_1 = 2
    CELESTE_2 = 3
    FLANGER_1 = 4
    FLANGER_2 = 5


class XGVariationType(IntEnum):
    """XG Variation Types (MSB 3, LSB 0-83) - Complete 84-type enumeration"""
    # Delay Effects (0-19)
    DELAY_LCR = 0
    DELAY_LR = 1
    DELAY_L_R = 2
    DELAY_MONO = 3
    DELAY_L_R_STEREO = 4
    DELAY_L_R_STEREO_SHORT = 5
    DELAY_L_R_STEREO_LONG = 6
    DELAY_PING_PONG_1 = 7
    DELAY_PING_PONG_2 = 8
    DELAY_PING_PONG_3 = 9

    # Chorus Effects (10-31)
    CHORUS_1 = 10
    CHORUS_2 = 11
    CHORUS_3 = 12
    CHORUS_4 = 13
    CELESTE_1 = 14
    CELESTE_2 = 15
    FLANGER_1 = 16
    FLANGER_2 = 17
    DELAY_LCR_CHORUS = 18
    DELAY_LR_CHORUS = 19
    FLANGER_CHORUS = 20
    CELESTE_CHORUS = 21
    TREMOLO = 22
    VIBRATO = 23
    CHORUS_REVERB = 24
    CELESTE_REVERB = 25
    PHASER = 26
    PHASER_FLANGER = 27
    CHORUS_AUTOPAN = 28
    CELESTE_AUTOPAN = 29
    DELAY_AUTOPAN = 30
    REVERB_AUTOPAN = 31

    # Modulation Effects (32-39)
    AUTO_PAN = 32
    AUTO_WAH = 33
    RING_MODULATION = 34
    STEP_PHASER_UP = 35
    STEP_PHASER_DOWN = 36
    STEP_FLANGER_UP = 37
    STEP_FLANGER_DOWN = 38
    STEP_TREMOLO_UP = 39
    STEP_TREMOLO_DOWN = 40
    STEP_PAN_UP = 41
    STEP_PAN_DOWN = 42

    # Distortion/Overdrive (43-52)
    DISTORTION_LIGHT = 43
    DISTORTION_MEDIUM = 44
    DISTORTION_HEAVY = 45
    OVERDRIVE_1 = 46
    OVERDRIVE_2 = 47
    OVERDRIVE_3 = 48
    CLIPPING_WARNING = 49
    FUZZ = 50
    GUITAR_DISTORTION = 51
    GUITAR_AMP_SIMULATOR = 52

    # Dynamics Processing (53-57)
    COMPRESSOR_ELECTRONIC = 53
    COMPRESSOR_OPTICAL = 54
    LIMITER = 55
    MULTI_BAND_COMPRESSOR = 56
    EXPANDER = 57

    # Enhancer Effects (58-61)
    ENHANCER_PEAKING = 58
    ENHANCER_SHELVING = 59
    MULTI_BAND_ENHANCER = 60
    STEREO_IMAGER = 61

    # Vocoder/Modulation (62-65)
    VOCODER_COMB_FILTER = 62
    VOCODER_PHASER = 63
    PITCH_SHIFT_UP_MINOR_THIRD = 64
    PITCH_SHIFT_DOWN_MINOR_THIRD = 65
    PITCH_SHIFT_UP_MAJOR_THIRD = 66
    PITCH_SHIFT_DOWN_MAJOR_THIRD = 67
    HARMONIZER = 68
    DETUNE = 69

    # Early Reflections (70-77)
    ERL_HALL_SMALL = 70
    ERL_HALL_MEDIUM = 71
    ERL_HALL_LARGE = 72
    ERL_ROOM_SMALL = 73
    ERL_ROOM_MEDIUM = 74
    ERL_ROOM_LARGE = 75
    ERL_STUDIO_LIGHT = 76
    ERL_STUDIO_HEAVY = 77

    # Gate Reverbs (78-80)
    GATE_REVERB_FAST_ATTACK = 78
    GATE_REVERB_MEDIUM_ATTACK = 79
    GATE_REVERB_SLOW_ATTACK = 80

    # Special Effects (81-83)
    VOICE_CANCEL = 81
    KARAOKE_REVERB = 82
    KARAOKE_ECHO = 83


class XGInsertionType(IntEnum):
    """XG Insertion Effect Types (0-24)"""
    THROUGH = 0          # Bypass
    DISTORTION = 1       # Distortion
    OVERDRIVE = 2        # Overdrive
    AMP_SIMULATOR = 3    # Guitar Amp Simulator
    COMPRESSOR = 4       # Compressor
    NOISE_GATE = 5       # Noise Gate
    WAH_WAH = 6          # Wah Wah
    EQUALIZER_3BAND = 7  # 3-Band EQ
    PITCH_SHIFTER = 8    # Pitch Shifter
    HARMONIZER = 9       # Harmonizer
    PHASER = 10          # Phaser
    FLANGER = 11         # Flanger
    CHORUS = 12          # Chorus
    DELAY = 13           # Delay
    REVERB = 14          # Reverb
    TREMOLO = 15         # Tremolo
    AUTO_PAN = 16        # Auto Pan
    ENHANCER = 17        # Enhancer
    SLICER = 18          # Slicer
    VOCODER = 19         # Vocoder
    TALK_WAH = 20        # Talk Box Wah
    OCTAVE = 21          # Octave
    DETUNE = 22          # Detune
    RING_MODULATION = 23 # Ring Modulation
    LO_FI = 24           # Lo-Fi


class XGBusType(Enum):
    """XG Audio Bus Types"""
    MAIN_L = "main_l"
    MAIN_R = "main_r"
    REVERB_SEND = "reverb_send"
    CHORUS_SEND = "chorus_send"
    VARIATION_SEND = "variation_send"
    INSERTION_SEND = "insertion_send"
    AUX_1 = "aux_1"
    AUX_2 = "aux_2"
    AUX_3 = "aux_3"
    AUX_4 = "aux_4"
    AUX_5 = "aux_5"
    AUX_6 = "aux_6"
    AUX_7 = "aux_7"
    AUX_8 = "aux_8"
    AUX_9 = "aux_9"
    AUX_10 = "aux_10"


class XGChannelParams(NamedTuple):
    """XG Channel Parameters Structure - Optimized for zero-allocation"""
    volume: float      # 0.0-1.0, channel volume
    expression: float  # 0.0-1.0, channel expression
    pan: float         # -1.0 (left) to +1.0 (right), channel pan
    reverb_send: float # 0.0-1.0, reverb send level
    chorus_send: float # 0.0-1.0, chorus send level
    variation_send: float # 0.0-1.0, variation send level
    insertion_active: bool # whether insertion effect is active
    insertion_type: XGInsertionType # insertion effect type


class XGSystemEffectsParams(NamedTuple):
    """XG System Effects Parameters"""
    reverb_type: XGReverbType
    reverb_level: float
    reverb_time: float
    reverb_hf_damping: float
    reverb_pre_delay: float
    chorus_type: XGChorusType
    chorus_level: float
    chorus_rate: float
    chorus_depth: float
    chorus_feedback: float
    variation_type: XGVariationType
    variation_level: float
    bypass_all: bool


class XGProcessingContext(NamedTuple):
    """XG Processing Context - All state needed for block processing"""
    sample_rate: int
    block_size: int
    num_input_channels: int
    num_output_channels: int
    channel_params: dict[int, XGChannelParams]  # channel_id -> params
    system_effects_params: XGSystemEffectsParams


class XGBiquadCoeffs(NamedTuple):
    """Biquad Filter Coefficients - Optimized for SIMD-friendly access"""
    b0: float
    b1: float
    b2: float
    a1: float
    a2: float


class XGBiquadState(NamedTuple):
    """Biquad Filter State - 8 floats for stereo processing (L + R channels)"""
    x1: float  # input n-1 (left)
    x2: float  # input n-2 (left)
    y1: float  # output n-1 (left)
    y2: float  # output n-2 (left)
    x1_r: float  # input n-1 (right)
    x2_r: float  # input n-2 (right)
    y1_r: float  # output n-1 (right)
    y2_r: float  # output n-2 (right)


class XGDelayLineState(NamedTuple):
    """Delay Line State - Fixed-size circular buffer indices"""
    write_pos: int
    feedback_buffer: float
    feedback_right: float  # for stereo delay lines


class XGLFOState(NamedTuple):
    """LFO State - For modulation effects"""
    phase: float
    phase_r: float  # right channel phase (for stereo)
    current_value: float
    current_value_r: float


class XGProcessingStats(NamedTuple):
    """XG Processing Statistics - For monitoring and profiling"""
    total_samples_processed: int
    average_block_time_ms: float
    peak_cpu_usage_percent: float
    active_channels: int
    active_effects: int
    memory_usage_mb: float
    buffer_allocations: int  # Should be 0 in ideal operation


# EQ and Mixer types (additional)
class XGEQType(IntEnum):
    """XG Equalization Types (standard EQ curves)"""
    FLAT = 0
    BRILLIANCE = 1
    MELLOW = 2
    BRIGHT = 3
    WARM = 4
    CLEAR = 5
    SOFT = 6
    CUT = 7
    BASS_BOOST = 8
    TREBLE_BOOST = 9


class XGChannelEQParams(NamedTuple):
    """XG Channel EQ Parameters (XG CC 71 for resonance, 74 for frequency)"""
    type: XGEQType
    level: float  # -12 to +12 dB range
    frequency: float  # Center frequency in Hz
    q_factor: float  # Q/resonance factor (0.1-10.0)


class XGMasterEQParams(NamedTuple):
    """XG Master EQ Parameters"""
    low_gain: float    # Low frequency gain (-12 to +12 dB)
    mid_gain: float    # Mid frequency gain (-12 to +12 dB)
    high_gain: float   # High frequency gain (-12 to +12 dB)
    low_freq: float    # Low frequency cutoff (20-400 Hz)
    mid_freq: float    # Mid frequency center (200-8000 Hz)
    high_freq: float   # High frequency cutoff (2000-20000 Hz)
    q_factor: float    # Overall Q factor (0.1-2.0)


class XGChannelMixerParams(NamedTuple):
    """XG Channel Mixer Parameters for Channel Mixing"""
    volume: float      # 0.0-1.0, channel volume
    pan: float         # -1.0 (left) to +1.0 (right), channel pan
    reverb_send: float # 0.0-1.0, reverb send level
    chorus_send: float # 0.0-1.0, chorus send level
    variation_send: float # 0.0-1.0, variation send level
    mute: bool         # Channel mute
    solo: bool         # Channel solo


class XGEffectCategory(IntEnum):
    """XG Effect Categories"""
    SYSTEM = 0      # System-wide effects (Reverb, Chorus)
    VARIATION = 1   # Variation effects (83 types)
    INSERTION = 2   # Insertion effects (18 types)
    EQUALIZER = 3   # EQ effects (10 types)


# Constants optimized for zero-allocation processing
MAX_BLOCK_SIZE = 1024  # Maximum block size for processing
MAX_CHANNELS = 16      # Maximum MIDI channels
MAX_VOICES_PER_CHANNEL = 4  # Maximum voices per channel
MAX_EFFECT_BUSES = 16  # Maximum effect buses

# Pre-computed constants to avoid runtime allocation
STEREO_ROUTING_MATRIX_DEFAULT = np.zeros((MAX_CHANNELS, 2), dtype=np.float32)  # Main L/R
EFFECT_SEND_MATRIX_DEFAULT = np.zeros((MAX_CHANNELS, MAX_EFFECT_BUSES - 2), dtype=np.float32)  # Effect sends

# Effect type categories with their ranges (from XG specification)
XG_VARIATION_EFFECT_CATEGORIES = {
    "delay": (0, 9),              # 10 delay effects
    "chorus": (10, 31),           # 22 chorus/flanger/phase effects
    "modulation": (32, 42),       # 11 modulation/tremolo/pan effects
    "distortion": (43, 52),       # 10 distortion/overdrive/amp effects
    "dynamics": (53, 57),         # 5 compressor/limiter/expander effects
    "enhancer": (58, 61),         # 4 enhancer/imaging effects
    "vocoder": (62, 63),          # 2 vocoder effects
    "pitch_shift": (64, 69),      # 6 pitch shift/harmonizer effects
    "early_reflection": (70, 77), # 8 early reflection effects
    "gate_reverb": (78, 80),      # 3 gate reverb effects
    "special": (81, 83),          # 3 special effects
}

XG_INSERTION_EFFECT_CATEGORIES = {
    "bypass": (0, 0),             # 1 bypass effect
    "distortion": (1, 3),         # 3 distortion effects
    "dynamics": (4, 5),           # 2 dynamics effects
    "wah": (6, 6),                # 1 wah effect
    "eq": (7, 7),                 # 1 EQ effect
    "pitch": (8, 9),              # 2 pitch effects
    "modulation": (10, 15),       # 6 modulation effects
    "enhancer": (16, 17),         # 2 enhancer effects
    "vocoder": (18, 21),          # 4 vocoder effects
    "special": (22, 24),          # 3 special effects
}

# XG Parameter ranges (for validation and scaling)
XG_PARAMETER_RANGES = {
    "reverb_time": (0.1, 8.3),         # Time in seconds
    "reverb_level": (0.0, 1.0),        # Send level
    "reverb_pre_delay": (0.0, 0.05),   # Pre-delay in seconds
    "reverb_hf_damping": (0.0, 1.0),   # HF damping factor
    "reverb_density": (0.0, 1.0),      # Reverb density
    "chorus_rate": (0.125, 10.0),      # LFO rate in Hz
    "chorus_depth": (0.0, 1.0),        # Modulation depth
    "chorus_feedback": (-0.5, 0.5),    # Feedback amount
    "variation_param1": (0.0, 1.0),    # General parameter 1
    "variation_param2": (0.0, 1.0),    # General parameter 2
    "variation_param3": (0.0, 1.0),    # General parameter 3
    "variation_param4": (0.0, 1.0),    # General parameter 4
}

# Default XG parameters (loaded at startup)
XG_DEFAULT_PARAMS = XGSystemEffectsParams(
    reverb_type=XGReverbType.HALL_1,
    reverb_level=0.6,
    reverb_time=2.5,
    reverb_hf_damping=0.5,
    reverb_pre_delay=20e-3,  # 20ms
    chorus_type=XGChorusType.CHORUS_1,
    chorus_level=0.4,
    chorus_rate=1.0,
    chorus_depth=0.5,
    chorus_feedback=0.3,
    variation_type=XGVariationType.DELAY_LCR,
    variation_level=0.5,
    bypass_all=False
)

XG_CHANNEL_MIXER_DEFAULT = XGChannelMixerParams(
    volume=0.8,
    pan=0.0,
    reverb_send=0.0,
    chorus_send=0.0,
    variation_send=0.0,
    mute=False,
    solo=False
)

XG_MASTER_EQ_DEFAULT = XGMasterEQParams(
    low_gain=0.0,
    mid_gain=0.0,
    high_gain=0.0,
    low_freq=100.0,
    mid_freq=1000.0,
    high_freq=8000.0,
    q_factor=0.707
)
