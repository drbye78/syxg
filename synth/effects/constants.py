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

# XG Bulk Data Types for effects
XG_BULK_EFFECTS = 0x03  # System parameters include effects
XG_BULK_CHANNEL_EFFECTS = 0x04  # Channel-specific effect parameters

# XG Effect NRPN Parameter Mappings
XG_EFFECT_NRPN_PARAMS: Dict[Tuple[int, int], Dict[str, Any]] = {
    # Reverb Parameters
    (0, 120): {"target": "reverb", "param": "type", "transform": lambda x: min(x, 7)},  # 0-7 types
    (0, 121): {"target": "reverb", "param": "time", "transform": lambda x: 0.1 + x * 0.05},  # 0.1-8.3 sec
    (0, 122): {"target": "reverb", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 123): {"target": "reverb", "param": "pre_delay", "transform": lambda x: x * 0.1},  # 0-12.7 ms
    (0, 124): {"target": "reverb", "param": "hf_damping", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 125): {"target": "reverb", "param": "density", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 126): {"target": "reverb", "param": "early_level", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 127): {"target": "reverb", "param": "tail_level", "transform": lambda x: x / 127.0},  # 0.0-1.0

    # Chorus Parameters
    (0, 130): {"target": "chorus", "param": "type", "transform": lambda x: min(x, 7)},  # 0-7 types
    (0, 131): {"target": "chorus", "param": "rate", "transform": lambda x: 0.1 + x * 0.05},  # 0.1-6.5 Hz
    (0, 132): {"target": "chorus", "param": "depth", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 133): {"target": "chorus", "param": "feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 134): {"target": "chorus", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 135): {"target": "chorus", "param": "delay", "transform": lambda x: x * 0.1},  # 0-12.7 ms
    (0, 136): {"target": "chorus", "param": "output", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 137): {"target": "chorus", "param": "cross_feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0

    # Variation Effect Parameters
    (0, 140): {"target": "variation", "param": "type", "transform": lambda x: min(x, 63)},  # 0-63 types
    (0, 141): {"target": "variation", "param": "parameter1", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 142): {"target": "variation", "param": "parameter2", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 143): {"target": "variation", "param": "parameter3", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 144): {"target": "variation", "param": "parameter4", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 145): {"target": "variation", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 146): {"target": "variation", "param": "bypass", "transform": lambda x: x > 64},  # true/false
    # New variation effect parameters
    (0, 147): {"target": "variation", "param": "new_param1", "transform": lambda x: x / 127.0},
    (0, 148): {"target": "variation", "param": "new_param2", "transform": lambda x: x / 127.0},

    # Insertion Effect Parameters (channel-specific)
    (0, 150): {"target": "insertion", "param": "type", "transform": lambda x: min(x, 17)},  # 0-17 types (extended)
    (0, 151): {"target": "insertion", "param": "parameter1", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 152): {"target": "insertion", "param": "parameter2", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 153): {"target": "insertion", "param": "parameter3", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 154): {"target": "insertion", "param": "parameter4", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 155): {"target": "insertion", "param": "level", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 156): {"target": "insertion", "param": "bypass", "transform": lambda x: x > 64},  # true/false
    # New Insertion Effects parameters
    (0, 157): {"target": "insertion", "param": "frequency", "transform": lambda x: x * 0.2},  # 0-25.4 Hz
    (0, 158): {"target": "insertion", "param": "depth", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 159): {"target": "insertion", "param": "feedback", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 160): {"target": "insertion", "param": "lfo_waveform", "transform": lambda x: min(x, 3)},  # 0-3 types

    # Equalizer Parameters
    (0, 100): {"target": "equalizer", "param": "low_gain", "transform": lambda x: (x - 64) * 0.2},  # dB
    (0, 101): {"target": "equalizer", "param": "mid_gain", "transform": lambda x: (x - 64) * 0.2},  # dB
    (0, 102): {"target": "equalizer", "param": "high_gain", "transform": lambda x: (x - 64) * 0.2},  # dB
    (0, 103): {"target": "equalizer", "param": "mid_freq", "transform": lambda x: 100 + x * 40},  # Hz
    (0, 104): {"target": "equalizer", "param": "q_factor", "transform": lambda x: 0.5 + x * 0.04},  # Q-factor

    # Stereo Parameters
    (0, 110): {"target": "stereo", "param": "width", "transform": lambda x: x / 127.0},  # Stereo width
    (0, 111): {"target": "stereo", "param": "chorus", "transform": lambda x: x / 127.0},  # Chorus level

    # Global Effect Parameters
    (0, 112): {"target": "global", "param": "reverb_send", "transform": lambda x: x / 127.0},  # Reverb send level
    (0, 113): {"target": "global", "param": "chorus_send", "transform": lambda x: x / 127.0},  # Chorus send level
    (0, 114): {"target": "global", "param": "variation_send", "transform": lambda x: x / 127.0},  # Variation send level

    # Channel-Specific Effect Parameters
    (0, 160): {"target": "channel", "param": "reverb_send", "transform": lambda x: x / 127.0},  # Reverb send for channel
    (0, 161): {"target": "channel", "param": "chorus_send", "transform": lambda x: x / 127.0},  # Chorus send for channel
    (0, 162): {"target": "channel", "param": "variation_send", "transform": lambda x: x / 127.0},  # Variation send for channel
    (0, 163): {"target": "channel", "param": "insertion_send", "transform": lambda x: x / 127.0},  # Insertion send for channel
    (0, 164): {"target": "channel", "param": "muted", "transform": lambda x: x > 64},  # Channel mute
    (0, 165): {"target": "channel", "param": "soloed", "transform": lambda x: x > 64},  # Channel solo
    (0, 166): {"target": "channel", "param": "pan", "transform": lambda x: (x - 64) / 64.0},  # Channel pan
    (0, 167): {"target": "channel", "param": "volume", "transform": lambda x: x / 127.0},  # Channel volume

    # Effect Routing Parameters
    (0, 170): {"target": "routing", "param": "system_effect_order", "transform": lambda x: x},  # System effect order
    (0, 171): {"target": "routing", "param": "insertion_effect_order", "transform": lambda x: x},  # Insertion effect order
    (0, 172): {"target": "routing", "param": "parallel_routing", "transform": lambda x: x > 64},  # Parallel routing
    (0, 173): {"target": "routing", "param": "reverb_to_chorus", "transform": lambda x: x / 127.0},  # Reverb to chorus
    (0, 174): {"target": "routing", "param": "chorus_to_variation", "transform": lambda x: x / 127.0},  # Chorus to variation

    # XG System Parameters (MSB 0, LSB 0-127)
    (0, 0): {"target": "system", "param": "master_tune", "transform": lambda x: (x - 64) * 0.1},  # -6.4 to +6.3 Hz
    (0, 1): {"target": "system", "param": "master_volume", "transform": lambda x: x / 127.0},  # 0.0-1.0
    (0, 2): {"target": "system", "param": "master_tune_fine", "transform": lambda x: (x - 64) * 0.01},  # -0.64 to +0.63 Hz
    (0, 3): {"target": "system", "param": "transpose", "transform": lambda x: x - 64},  # -64 to +63 semitones
    (0, 4): {"target": "system", "param": "drum_setup_reset", "transform": lambda x: x > 64},  # Reset drum setup
    (0, 5): {"target": "system", "param": "system_reset", "transform": lambda x: x > 64},  # System reset

    # XG Channel Parameters (MSB 1-15, LSB 0-127) - Channel-specific
    # These are handled per-channel in the state manager
}

# XG Channel NRPN Parameters (MSB 1-15 for channels 0-14)
XG_CHANNEL_NRPN_PARAMS: Dict[Tuple[int, int], Dict[str, Any]] = {
    # Pitch Bend Range (RPN 0,0)
    (1, 0): {"target": "channel", "param": "pitch_bend_range", "transform": lambda x: x},  # 0-24 semitones
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

    # Fine Tuning (RPN 0,1)
    (1, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},  # -1.0 to +1.0
    (2, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (3, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (4, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (5, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (6, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (7, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (8, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (9, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (10, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (11, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (12, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (13, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (14, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},
    (15, 1): {"target": "channel", "param": "fine_tuning", "transform": lambda x: (x - 64) / 8192.0},

    # Coarse Tuning (RPN 0,2)
    (1, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},  # -64 to +63 semitones
    (2, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (3, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (4, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (5, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (6, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (7, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (8, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (9, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (10, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (11, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (12, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (13, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (14, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},
    (15, 2): {"target": "channel", "param": "coarse_tuning", "transform": lambda x: x - 64},

    # Tuning Program (RPN 0,3)
    (1, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},  # 0-127
    (2, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (3, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (4, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (5, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (6, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (7, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (8, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (9, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (10, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (11, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (12, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (13, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (14, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},
    (15, 3): {"target": "channel", "param": "tuning_program", "transform": lambda x: x},

    # Tuning Bank (RPN 0,4)
    (1, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},  # 0-127
    (2, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (3, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (4, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (5, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (6, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (7, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (8, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (9, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (10, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (11, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (12, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (13, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (14, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},
    (15, 4): {"target": "channel", "param": "tuning_bank", "transform": lambda x: x},

    # Modulation Depth (RPN 0,5)
    (1, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},  # 0-127 cents
    (2, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (3, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (4, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (5, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (6, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (7, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (8, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (9, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (10, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (11, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (12, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (13, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (14, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},
    (15, 5): {"target": "channel", "param": "modulation_depth", "transform": lambda x: x},

    # Element Reserve (XG Part Parameter)
    (1, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},  # 0-127
    (2, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (3, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (4, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (5, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (6, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (7, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (8, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (9, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (10, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (11, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (12, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (13, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (14, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},
    (15, 6): {"target": "channel", "param": "element_reserve", "transform": lambda x: x},

    # Element Assign Mode (XG Part Parameter)
    (1, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},  # 0-127
    (2, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (3, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (4, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (5, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (6, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (7, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (8, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (9, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (10, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (11, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (12, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (13, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (14, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},
    (15, 7): {"target": "channel", "param": "element_assign_mode", "transform": lambda x: x},

    # Receive Channel (XG Part Parameter)
    (1, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},  # 0-15
    (2, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (3, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (4, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (5, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (6, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (7, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (8, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (9, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (10, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (11, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (12, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (13, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (14, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
    (15, 8): {"target": "channel", "param": "receive_channel", "transform": lambda x: x},
}

# XG Reverb Types
XG_REVERB_TYPES: List[str] = [
    "Hall 1", "Hall 2", "Hall 3", "Room 1", "Room 2", "Room 3", "Stage", "Plate"
]

# XG Chorus Types
XG_CHORUS_TYPES: List[str] = [
    "Chorus 1", "Chorus 2", "Chorus 3", "Ensemble 1", "Ensemble 2", "Flanger", "Flanger 2", "Off"
]

# XG Variation Effect Types
XG_VARIATION_TYPES: List[str] = [
    "Delay", "Dual Delay", "Echo", "Pan Delay", "Cross Delay", "Multi Tap",
    "Reverse Delay", "Tremolo", "Auto Pan", "Phaser", "Flanger", "Auto Wah",
    "Ring Mod", "Pitch Shifter", "Distortion", "Overdrive", "Compressor",
    "Limiter", "Gate", "Expander", "Rotary Speaker", "Leslie", "Vibrato",
    "Acoustic Simulator", "Guitar Amp Sim", "Enhancer", "Slicer", "Step Phaser",
    "Step Flanger", "Step Tremolo", "Step Pan", "Step Filter", "Auto Filter",
    "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune", "Chorus/Reverb",
    "Stereo Imager", "Ambience", "Doubler", "Enhancer/Reverb", "Spectral",
    "Resonator", "Degrader", "Vinyl", "Looper", "Step Delay", "Step Echo",
    "Step Pan Delay", "Step Cross Delay", "Step Multi Tap", "Step Reverse Delay",
    "Step Ring Mod", "Step Pitch Shifter", "Step Distortion", "Step Overdrive",
    "Step Compressor", "Step Limiter", "Step Gate", "Step Expander", "Step Rotary Speaker"
]

# XG Insertion Effect Types (Complete Implementation)
XG_INSERTION_TYPES: List[str] = [
    "Off", "Distortion", "Overdrive", "Compressor", "Gate", "Envelope Filter",
    "Guitar Amp Sim", "Rotary Speaker", "Leslie", "Enhancer", "Slicer",
    "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune",
    "Phaser", "Flanger", "Wah Wah", "Auto Wah", "Band Pass Filter",
    "Notch Filter", "Formant Filter", "Exciter", "Subharmonic Synth", "Ring Modulator",
    "Delay", "Echo", "Reverb", "Chorus", "Flanger 2", "Phaser 2",
    "Tremolo", "Auto Pan", "Rotary Speaker 2", "Leslie 2", "Enhancer 2",
    "Slicer 2", "Vocoder 2", "Talk Wah 2", "Harmonizer 2", "Octave 2",
    "Detune 2", "Distortion 2", "Overdrive 2", "Compressor 2", "Gate 2",
    "Envelope Filter 2", "Guitar Amp Sim 2", "Ring Modulator 2", "Delay 2",
    "Echo 2", "Reverb 2", "Chorus 2", "Flanger 3", "Phaser 3",
    "Tremolo 2", "Auto Pan 2", "Rotary Speaker 3", "Leslie 3", "Enhancer 3"
]

# Parameter mappings for each effect type (Complete Implementation)
INSERTION_EFFECT_PARAMS: Dict[int, List[str]] = {
    # Basic Effects
    1: ["drive", "tone", "level", "type"],  # Distortion
    2: ["drive", "tone", "level", "bias"],  # Overdrive
    3: ["threshold", "ratio", "attack", "release"],  # Compressor
    4: ["threshold", "reduction", "attack", "hold"],  # Gate
    5: ["sensitivity", "depth", "resonance", "mode"],  # Envelope Filter

    # Modulation Effects
    6: ["drive", "bass", "treble", "level"],  # Guitar Amp Sim
    7: ["speed", "balance", "accel", "level"],  # Rotary Speaker
    8: ["speed", "balance", "accel", "level"],  # Leslie
    9: ["enhance", "bass", "treble", "level"],  # Enhancer
    10: ["rate", "depth", "waveform", "phase"],  # Slicer

    # Special Effects
    11: ["bands", "depth", "formant", "level"],  # Vocoder
    12: ["sensitivity", "depth", "resonance", "mode"],  # Talk Wah
    13: ["intervals", "depth", "feedback", "mix"],  # Harmonizer
    14: ["shift", "feedback", "mix", "formant"],  # Octave
    15: ["shift", "feedback", "mix", "formant"],  # Detune

    # Filter Effects
    16: ["frequency", "depth", "feedback", "lfo_waveform"],  # Phaser
    17: ["frequency", "depth", "feedback", "lfo_waveform"],  # Flanger
    18: ["manual_position", "lfo_rate", "lfo_depth", "resonance"],  # Wah Wah
    19: ["sensitivity", "depth", "resonance", "mode"],  # Auto Wah
    20: ["cutoff", "resonance", "depth", "lfo_waveform"],  # Band Pass Filter
    21: ["cutoff", "resonance", "depth", "lfo_waveform"],  # Notch Filter
    22: ["cutoff", "resonance", "depth", "lfo_waveform"],  # Formant Filter
    23: ["enhance", "bass", "treble", "level"],  # Exciter
    24: ["shift", "feedback", "mix", "formant"],  # Subharmonic Synth
    25: ["frequency", "depth", "waveform", "level"],  # Ring Modulator

    # Delay Effects
    26: ["time", "feedback", "level", "stereo"],  # Delay
    27: ["time", "feedback", "level", "decay"],  # Echo
    28: ["time", "feedback", "level", "hf_damping"],  # Reverb
    29: ["rate", "depth", "waveform", "phase"],  # Chorus
    30: ["frequency", "depth", "feedback", "lfo_waveform"],  # Flanger 2
    31: ["frequency", "depth", "feedback", "lfo_waveform"],  # Phaser 2

    # Modulation Effects 2
    32: ["rate", "depth", "waveform", "phase"],  # Tremolo
    33: ["rate", "depth", "waveform", "phase"],  # Auto Pan
    34: ["speed", "balance", "accel", "level"],  # Rotary Speaker 2
    35: ["speed", "balance", "accel", "level"],  # Leslie 2
    36: ["enhance", "bass", "treble", "level"],  # Enhancer 2
    37: ["rate", "depth", "waveform", "phase"],  # Slicer 2

    # Special Effects 2
    38: ["bands", "depth", "formant", "level"],  # Vocoder 2
    39: ["sensitivity", "depth", "resonance", "mode"],  # Talk Wah 2
    40: ["intervals", "depth", "feedback", "mix"],  # Harmonizer 2
    41: ["shift", "feedback", "mix", "formant"],  # Octave 2
    42: ["shift", "feedback", "mix", "formant"],  # Detune 2

    # Distortion Effects 2
    43: ["drive", "tone", "level", "type"],  # Distortion 2
    44: ["drive", "tone", "level", "bias"],  # Overdrive 2
    45: ["threshold", "ratio", "attack", "release"],  # Compressor 2
    46: ["threshold", "reduction", "attack", "hold"],  # Gate 2
    47: ["sensitivity", "depth", "resonance", "mode"],  # Envelope Filter 2
    48: ["drive", "bass", "treble", "level"],  # Guitar Amp Sim 2
    49: ["frequency", "depth", "waveform", "level"],  # Ring Modulator 2

    # Delay Effects 2
    50: ["time", "feedback", "level", "stereo"],  # Delay 2
    51: ["time", "feedback", "level", "decay"],  # Echo 2
    52: ["time", "feedback", "level", "hf_damping"],  # Reverb 2
    53: ["rate", "depth", "waveform", "phase"],  # Chorus 2
    54: ["frequency", "depth", "feedback", "lfo_waveform"],  # Flanger 3
    55: ["frequency", "depth", "feedback", "lfo_waveform"],  # Phaser 3

    # Final Effects
    56: ["rate", "depth", "waveform", "phase"],  # Tremolo 2
    57: ["rate", "depth", "waveform", "phase"],  # Auto Pan 2
    58: ["speed", "balance", "accel", "level"],  # Rotary Speaker 3
    59: ["speed", "balance", "accel", "level"],  # Leslie 3
    60: ["enhance", "bass", "treble", "level"],  # Enhancer 3
}

VARIATION_EFFECT_PARAMS: Dict[int, List[str]] = {
    0: ["time", "feedback", "level", "stereo"],
    1: ["time1", "time2", "feedback", "level"],
    2: ["time", "feedback", "level", "decay"],
    3: ["time", "feedback", "level", "rate"],
    4: ["time", "feedback", "level", "cross"],
    5: ["taps", "feedback", "level", "spacing"],
    6: ["time", "feedback", "level", "reverse"],
    7: ["rate", "depth", "waveform", "phase"],
    8: ["rate", "depth", "waveform", "phase"],
    9: ["frequency", "depth", "feedback", "lfo_waveform"],
    10: ["frequency", "depth", "feedback", "lfo_waveform"],
    11: ["sensitivity", "depth", "resonance", "mode"],
    12: ["frequency", "depth", "waveform", "level"],
    13: ["shift", "feedback", "mix", "formant"],
    14: ["drive", "tone", "level", "type"],
    15: ["drive", "tone", "level", "bias"],
    16: ["threshold", "ratio", "attack", "release"],
    17: ["threshold", "ratio", "attack", "release"],
    18: ["threshold", "reduction", "attack", "hold"],
    19: ["threshold", "ratio", "attack", "release"],
    20: ["speed", "balance", "accel", "level"],
    21: ["speed", "balance", "accel", "level"],
    22: ["rate", "depth", "waveform", "phase"],
    23: ["room", "depth", "reverb", "mode"],
    24: ["drive", "bass", "treble", "level"],
    25: ["enhance", "bass", "treble", "level"],
    26: ["rate", "depth", "waveform", "phase"],
    27: ["frequency", "depth", "feedback", "lfo_waveform"],
    28: ["frequency", "depth", "feedback", "lfo_waveform"],
    29: ["rate", "depth", "waveform", "phase"],
    30: ["rate", "depth", "waveform", "phase"],
    31: ["cutoff", "resonance", "depth", "lfo_waveform"],
    32: ["cutoff", "resonance", "depth", "lfo_waveform"],
    33: ["bands", "depth", "formant", "level"],
    34: ["sensitivity", "depth", "resonance", "mode"],
    35: ["intervals", "depth", "feedback", "mix"],
    36: ["shift", "feedback", "mix", "formant"],
    37: ["shift", "feedback", "mix", "formant"],
    38: ["chorus", "reverb", "mix", "level"],
    39: ["width", "depth", "reverb", "level"],
    40: ["reverb", "delay", "mix", "level"],
    41: ["enhance", "reverb", "mix", "level"],
    42: ["spectrum", "depth", "formant", "level"],
    43: ["resonance", "decay", "level", "mode"],
    44: ["bit_depth", "sample_rate", "level", "mode"],
    45: ["warp", "crackle", "level", "mode"],
    46: ["loop", "speed", "reverse", "level"],
    47: ["time", "feedback", "level", "taps"],
    48: ["time", "feedback", "level", "steps"],
    49: ["time", "feedback", "level", "steps"],
    50: ["time", "feedback", "level", "steps"],
    51: ["time", "feedback", "level", "steps"],
    52: ["taps", "feedback", "level", "steps"],
    53: ["time", "feedback", "level", "steps"],
    54: ["frequency", "depth", "waveform", "steps"],
    55: ["shift", "feedback", "steps", "formant"],
    56: ["drive", "tone", "steps", "type"],
    57: ["drive", "tone", "steps", "bias"],
    58: ["threshold", "ratio", "steps", "release"],
    59: ["threshold", "ratio", "steps", "release"],
    60: ["threshold", "reduction", "steps", "hold"],
    61: ["threshold", "ratio", "steps", "release"],
    62: ["speed", "balance", "steps", "level"]
}

# XG Extended Effect Types - Additional effects for enhanced XG compliance
# These extend beyond the current implementation for future expansion

# XG Reverb Types (Extended)
XG_REVERB_TYPES_EXTENDED: List[str] = [
    "Hall 1", "Hall 2", "Hall 3", "Room 1", "Room 2", "Room 3", "Stage", "Plate",
    "White Room", "Tunnel", "Canyon", "Basement", "Church", "Cathedral", "Arena", "Hangar"
]

# XG Chorus Types (Extended)
XG_CHORUS_TYPES_EXTENDED: List[str] = [
    "Chorus 1", "Chorus 2", "Chorus 3", "Ensemble 1", "Ensemble 2", "Flanger", "Flanger 2", "Off",
    "Chorus Hall", "Chorus Room", "Ensemble Hall", "Flanger Hall", "Chorus+Reverb", "Ensemble+Reverb"
]

# XG Insertion Effect Types (Extended)
XG_INSERTION_TYPES_EXTENDED: List[str] = [
    "Off", "Distortion", "Overdrive", "Compressor", "Gate", "Envelope Filter",
    "Guitar Amp Sim", "Rotary Speaker", "Leslie", "Enhancer", "Slicer",
    "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune",
    "Phaser", "Flanger", "Wah Wah", "Auto Wah 2", "Band Pass Filter",
    "Notch Filter", "Formant Filter", "Exciter", "Subharmonic Synth", "Ring Modulator 2"
]

# XG Variation Effect Types (Extended)
XG_VARIATION_TYPES_EXTENDED: List[str] = [
    "Delay", "Dual Delay", "Echo", "Pan Delay", "Cross Delay", "Multi Tap",
    "Reverse Delay", "Tremolo", "Auto Pan", "Phaser", "Flanger", "Auto Wah",
    "Ring Mod", "Pitch Shifter", "Distortion", "Overdrive", "Compressor",
    "Limiter", "Gate", "Expander", "Rotary Speaker", "Leslie", "Vibrato",
    "Acoustic Simulator", "Guitar Amp Sim", "Enhancer", "Slicer", "Step Phaser",
    "Step Flanger", "Step Tremolo", "Step Pan", "Step Filter", "Auto Filter",
    "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune", "Chorus/Reverb",
    "Stereo Imager", "Ambience", "Doubler", "Enhancer/Reverb", "Spectral",
    "Resonator", "Degrader", "Vinyl", "Looper", "Step Delay", "Step Echo",
    "Step Pan Delay", "Step Cross Delay", "Step Multi Tap", "Step Reverse Delay",
    "Step Ring Mod", "Step Pitch Shifter", "Step Distortion", "Step Overdrive",
    "Step Compressor", "Step Limiter", "Step Gate", "Step Expander", "Step Rotary Speaker",
    # NEW EXTENDED EFFECTS
    "Multi Chorus", "Stereo Chorus", "Quad Chorus", "Hyper Chorus",
    "Multi Flanger", "Through-Zero Flanger", "Phaser 2", "Bi-Phase Phaser",
    "Auto Wah 2", "Touch Wah", "Pedal Wah", "Resonance Wah", "Formant Wah",
    "Pitch Wah", "Cry Wah", "Vowel Filter", "Talk Box", "Megaphone", "Telephone",
    "Radio", "Walkie Talkie", "Robot", "Alien", "Chorus+Delay", "Flanger+Delay",
    "Phaser+Delay", "Chorus+Flanger", "Rotary+Chorus", "Leslie+Chorus",
    "Ping Pong Delay", "Multi Tap Echo", "Reverse Echo", "Tape Echo",
    "Spring Reverb", "Plate Reverb 2", "Hall Reverb 2", "Room Reverb 2",
    "Ambience Reverb", "Stadium Reverb", "Concert Hall", "Opera House",
    "Drum Booth", "Vocal Booth", "Guitar Amp Room", "Bass Amp Room",
    "Control Room", "Live Room", "Chamber", "Cathedral 2", "Arena 2", "Hangar 2",
    "Canyon 2", "Tunnel 2", "Basement 2", "White Room 2", "Church 2",
    "Stone Room", "Wood Room", "Carpeted Room", "Draped Room", "Padded Cell",
    "Anechoic Chamber", "Infinite Reverb", "Gated Reverb"
]
