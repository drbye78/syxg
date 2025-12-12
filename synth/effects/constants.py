"""
XG Effects Constants and Parameter Mappings

This module contains all constants, parameter mappings, and type definitions
used by the XG effects system.
"""

import math
from typing import Dict, List, Tuple, Optional, Callable, Any, Union

# Constants for parameter transformation
TIME_CENTISECONDS_TO_SECONDS = 0.01
FILTER_CUTOFF_SCALE = 0.1
PAN_SCALE = 0.01
VELOCITY_SENSE_SCALE = 0.01
PITCH_SCALE = 0.1
FILTER_RESONANCE_SCALE = 0.01

# MIDI channel configuration
NUM_CHANNELS = 16

# SysEx Manufacturer ID for Yamaha
YAMAHA_MANUFACTURER_ID = [0x43]

# XG SysEx sub-status codes
XG_PARAMETER_CHANGE = 0x04
XG_BULK_PARAMETER_DUMP = 0x7F
XG_BULK_PARAMETER_REQUEST = 0x7E
XG_MODEL_ID_QUERY = 0x06  # Universal model ID query

XG_VOICE_NRPN_PARAMS: Dict[Tuple[int, int], Dict[str, Any]] = {
    # XG Voice parameters for MSB 127 (voice architecture parameters)
    (127, 0): {"target": "voice", "param": "element_switch", "transform": lambda x: x},
    (127, 1): {"target": "voice", "param": "velocity_limit_high", "transform": lambda x: x},
    (127, 2): {"target": "voice", "param": "velocity_limit_low", "transform": lambda x: x},
    (127, 3): {"target": "voice", "param": "note_limit_high", "transform": lambda x: x},
    (127, 4): {"target": "voice", "param": "note_limit_low", "transform": lambda x: x},
    (127, 5): {"target": "voice", "param": "note_shift", "transform": lambda x: x - 64},
    (127, 6): {"target": "voice", "param": "detune", "transform": lambda x: (x - 64) / 16.0},
    (127, 7): {"target": "voice", "param": "velocity_sensitivity", "transform": lambda x: x},
    (127, 8): {"target": "voice", "param": "volume", "transform": lambda x: x / 127.0},
    (127, 9): {"target": "voice", "param": "velocity_rate_sens", "transform": lambda x: (x - 64) / 32.0},
    (127, 10): {"target": "voice", "param": "pan", "transform": lambda x: (x - 64) / 64.0},
    (127, 11): {"target": "voice", "param": "assign_mode", "transform": lambda x: x},
    (127, 12): {"target": "voice", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (127, 13): {"target": "voice", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (127, 14): {"target": "voice", "param": "pitch_random", "transform": lambda x: x * 0.01},
    (127, 15): {"target": "voice", "param": "pitch_scale_tune", "transform": lambda x: (x - 64) * 0.03},
    (127, 16): {"target": "voice", "param": "pitch_scale_sens", "transform": lambda x: (x - 64) * 0.01},
    (127, 17): {"target": "voice", "param": "delay_mode", "transform": lambda x: x},
    (127, 18): {"target": "voice", "param": "delay_time", "transform": lambda x: x * 4},
    (127, 19): {"target": "voice", "param": "delay_feedback", "transform": lambda x: x / 127.0},
    (127, 20): {"target": "voice", "param": "lfo_waveform", "transform": lambda x: min(x, 3)},
    (127, 21): {"target": "voice", "param": "lfo_speed", "transform": lambda x: x * 0.1},
    (127, 22): {"target": "voice", "param": "lfo_delay", "transform": lambda x: x * 0.1},
    (127, 23): {"target": "voice", "param": "lfo_fade_time", "transform": lambda x: x * 0.1},
    (127, 24): {"target": "voice", "param": "lfo_pitch_mod_depth", "transform": lambda x: x},
    (127, 25): {"target": "voice", "param": "lfo_pitch_mod_sensitivity", "transform": lambda x: (x - 64) / 64.0},
    (127, 26): {"target": "voice", "param": "lfo_amplitude_mod_depth", "transform": lambda x: x / 127.0},
    (127, 27): {"target": "voice", "param": "lfo_amplitude_mod_sensitivity", "transform": lambda x: (x - 64) / 64.0},
    (127, 28): {"target": "voice", "param": "filter_cutoff", "transform": lambda x: 20 + x * 2.3},
    (127, 29): {"target": "voice", "param": "filter_resonance", "transform": lambda x: x / 127.0},
    (127, 30): {"target": "voice", "param": "filter_type", "transform": lambda x: min(x, 4)},
    (127, 31): {"target": "voice", "param": "filter_env_depth", "transform": lambda x: (x - 64) / 32.0},
}

# XG Effect NRPN Parameters MSB 0 (System Effects)
XG_EFFECT_NRPN_PARAMS: Dict[Tuple[int, int], Dict[str, Any]] = {
    # Reverb parameters (MSB 0, LSB 0-9)
    (0, 0): {"target": "reverb", "param": "type", "transform": lambda x: x},
    (0, 1): {"target": "reverb", "param": "time", "transform": lambda x: 0.1 + x * 0.05},
    (0, 2): {"target": "reverb", "param": "level", "transform": lambda x: x / 127.0},
    (0, 3): {"target": "reverb", "param": "hf_damping", "transform": lambda x: x / 127.0},
    (0, 4): {"target": "reverb", "param": "density", "transform": lambda x: x / 127.0},
    (0, 5): {"target": "reverb", "param": "early_level", "transform": lambda x: x / 127.0},
    (0, 6): {"target": "reverb", "param": "tail_level", "transform": lambda x: x / 127.0},
    (0, 7): {"target": "reverb", "param": "pre_delay", "transform": lambda x: x * 0.1},
    (0, 8): {"target": "reverb", "param": "feedback", "transform": lambda x: x / 127.0},
    (0, 9): {"target": "reverb", "param": "wet_dry", "transform": lambda x: x / 127.0},

    # Chorus parameters (MSB 0, LSB 10-19)
    (0, 10): {"target": "chorus", "param": "type", "transform": lambda x: x},
    (0, 11): {"target": "chorus", "param": "rate", "transform": lambda x: 0.1 + x * 0.05},
    (0, 12): {"target": "chorus", "param": "depth", "transform": lambda x: x / 127.0},
    (0, 13): {"target": "chorus", "param": "feedback", "transform": lambda x: x / 127.0},
    (0, 14): {"target": "chorus", "param": "level", "transform": lambda x: x / 127.0},
    (0, 15): {"target": "chorus", "param": "output", "transform": lambda x: x / 127.0},
    (0, 16): {"target": "chorus", "param": "cross_feedback", "transform": lambda x: x / 127.0},
    (0, 17): {"target": "chorus", "param": "delay", "transform": lambda x: x * 0.1},
    (0, 18): {"target": "chorus", "param": "surround", "transform": lambda x: x / 127.0},
    (0, 19): {"target": "chorus", "param": "wet_dry", "transform": lambda x: x / 127.0},

    # Variation parameters (MSB 0, LSB 20-29)
    (0, 20): {"target": "variation", "param": "type", "transform": lambda x: x},
    (0, 21): {"target": "variation", "param": "level", "transform": lambda x: x / 127.0},
    (0, 22): {"target": "variation", "param": "parameter1", "transform": lambda x: x / 127.0},
    (0, 23): {"target": "variation", "param": "parameter2", "transform": lambda x: x / 127.0},
    (0, 24): {"target": "variation", "param": "parameter3", "transform": lambda x: x / 127.0},
    (0, 25): {"target": "variation", "param": "parameter4", "transform": lambda x: x / 127.0},
    (0, 26): {"target": "variation", "param": "parameter5", "transform": lambda x: x / 127.0},
    (0, 27): {"target": "variation", "param": "parameter6", "transform": lambda x: x / 127.0},
    (0, 28): {"target": "variation", "param": "parameter7", "transform": lambda x: x / 127.0},
    (0, 29): {"target": "variation", "param": "parameter8", "transform": lambda x: x / 127.0},

    # Insertion effect parameters (MSB 0, LSB 30-39)
    (0, 30): {"target": "insertion", "param": "type", "transform": lambda x: x},
    (0, 31): {"target": "insertion", "param": "level", "transform": lambda x: x / 127.0},
    (0, 32): {"target": "insertion", "param": "parameter1", "transform": lambda x: x / 127.0},
    (0, 33): {"target": "insertion", "param": "parameter2", "transform": lambda x: x / 127.0},
    (0, 34): {"target": "insertion", "param": "parameter3", "transform": lambda x: x / 127.0},
    (0, 35): {"target": "insertion", "param": "parameter4", "transform": lambda x: x / 127.0},
    (0, 36): {"target": "insertion", "param": "parameter5", "transform": lambda x: x / 127.0},
    (0, 37): {"target": "insertion", "param": "parameter6", "transform": lambda x: x / 127.0},
    (0, 38): {"target": "insertion", "param": "parameter7", "transform": lambda x: x / 127.0},
    (0, 39): {"target": "insertion", "param": "parameter8", "transform": lambda x: x / 127.0},

    # Global effect parameters (MSB 0, LSB 120-127)
    (0, 120): {"target": "global", "param": "reverb_send", "transform": lambda x: x / 127.0},
    (0, 121): {"target": "global", "param": "chorus_send", "transform": lambda x: x / 127.0},
    (0, 122): {"target": "global", "param": "variation_send", "transform": lambda x: x / 127.0},
    (0, 123): {"target": "global", "param": "insertion_send", "transform": lambda x: x / 127.0},
    (0, 124): {"target": "global", "param": "master_level", "transform": lambda x: x / 127.0},
    (0, 125): {"target": "global", "param": "stereo_width", "transform": lambda x: x / 127.0},
    (0, 126): {"target": "global", "param": "bypass_all", "transform": lambda x: x > 0},
    (0, 127): {"target": "global", "param": "phase_lock", "transform": lambda x: x > 0},
}

# XG Channel NRPN Parameters
XG_CHANNEL_NRPN_PARAMS: Dict[Tuple[int, int], Dict[str, Any]] = {
    # Pitch Bend Range (RPN 0,0)
    (1, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (2, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (3, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (4, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (5, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (6, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (7, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (8, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (9, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (10, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (11, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (12, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (13, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (14, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
    (15, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},
}

# XG SysEx Constants
XG_SYSTEM_RESET = 0x00
XG_REGISTRATION_CHANGE = 0x08
XG_BULK_EFFECTS = 0x03
XG_BULK_CHANNEL_EFFECTS = 0x04
XG_BULK_MASTER_PARAMS = 0x00
XG_BULK_DRUM_PARAMS = 0x40
XG_BULK_SCENE_PARAMS = 0x09
