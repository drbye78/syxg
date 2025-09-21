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

# XG Insertion Effect Types
XG_INSERTION_TYPES: List[str] = [
    "Off", "Distortion", "Overdrive", "Compressor", "Gate", "Envelope Filter",
    "Guitar Amp Sim", "Rotary Speaker", "Leslie", "Enhancer", "Slicer",
    "Vocoder", "Talk Wah", "Harmonizer", "Octave", "Detune",
    "Phaser", "Flanger", "Wah Wah"  # Added Wah Wah effect
]

# Parameter mappings for each effect type
INSERTION_EFFECT_PARAMS: Dict[int, List[str]] = {
    1: ["parameter1", "parameter2", "parameter3", "parameter4"],
    2: ["parameter1", "parameter2", "parameter3", "parameter4"],
    3: ["parameter1", "parameter2", "parameter3", "parameter4"],
    4: ["parameter1", "parameter2", "parameter3", "parameter4"],
    5: ["parameter1", "parameter2", "parameter3", "parameter4"],
    6: ["parameter1", "parameter2", "parameter3", "parameter4"],
    7: ["parameter1", "parameter2", "parameter3", "parameter4"],
    8: ["parameter1", "parameter2", "parameter3", "parameter4"],
    9: ["parameter1", "parameter2", "parameter3", "parameter4"],
    10: ["parameter1", "parameter2", "parameter3", "parameter4"],
    11: ["parameter1", "parameter2", "parameter3", "parameter4"],
    12: ["parameter1", "parameter2", "parameter3", "parameter4"],
    13: ["parameter1", "parameter2", "parameter3", "parameter4"],
    14: ["parameter1", "parameter2", "parameter3", "parameter4"],
    15: ["parameter1", "parameter2", "parameter3", "parameter4"],
    16: ["frequency", "depth", "feedback", "lfo_waveform"],
    17: ["frequency", "depth", "feedback", "lfo_waveform"],
    18: ["manual_position", "lfo_rate", "lfo_depth", "resonance"]  # Wah Wah parameters
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
