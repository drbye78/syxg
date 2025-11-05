"""
XG Synthesizer Constants

Contains all MIDI constants, XG-specific constants, and default configuration values.
"""

# MIDI System Status Constants
MIDI_CONSTANTS = {
    # MIDI System Messages
    "NOTE_OFF": 0x80,
    "NOTE_ON": 0x90,
    "POLY_PRESSURE": 0xA0,
    "CONTROL_CHANGE": 0xB0,
    "PROGRAM_CHANGE": 0xC0,
    "CHANNEL_PRESSURE": 0xD0,
    "PITCH_BEND": 0xE0,
    "SYSTEM_EXCLUSIVE": 0xF0,
    "MIDI_TIME_CODE": 0xF1,
    "SONG_POSITION": 0xF2,
    "SONG_SELECT": 0xF3,
    "TUNE_REQUEST": 0xF6,
    "END_OF_EXCLUSIVE": 0xF7,
    "TIMING_CLOCK": 0xF8,
    "START": 0xFA,
    "CONTINUE": 0xFB,
    "STOP": 0xFC,
    "ACTIVE_SENSING": 0xFE,
    "SYSTEM_RESET": 0xFF,

    # Registration System Messages
    "RPN_MSB": 101,
    "RPN_LSB": 100,
    "NRPN_MSB": 99,
    "NRPN_LSB": 98,
    "DATA_ENTRY_MSB": 6,
    "DATA_ENTRY_LSB": 38,
}

# XG-Specific Constants
XG_CONSTANTS = {
    # XG Drum Setup Parameters (NRPN)
    "DRUM_NOTE_NUMBER": 250,
    "DRUM_NOTE_TUNE": 251,
    "DRUM_NOTE_LEVEL": 252,
    "DRUM_NOTE_PAN": 253,
    "DRUM_NOTE_REVERB": 254,
    "DRUM_NOTE_CHORUS": 255,
    "DRUM_NOTE_VARIATION": 256,
    "DRUM_NOTE_KEY_ASSIGN": 257,
    "DRUM_NOTE_FILTER_CUTOFF": 258,
    "DRUM_NOTE_FILTER_RESONANCE": 259,
    "DRUM_NOTE_EG_ATTACK": 260,
    "DRUM_NOTE_EG_DECAY": 261,
    "DRUM_NOTE_EG_RELEASE": 262,
    "DRUM_NOTE_PITCH_COARSE": 263,
    "DRUM_NOTE_PITCH_FINE": 264,
    "DRUM_NOTE_LEVEL_HOLD": 265,
    "DRUM_NOTE_VARIATION_EFFECT": 266,
    "DRUM_NOTE_VARIATION_PARAMETER1": 267,
    "DRUM_NOTE_VARIATION_PARAMETER2": 268,
    "DRUM_NOTE_VARIATION_PARAMETER3": 269,
    "DRUM_NOTE_VARIATION_PARAMETER4": 270,
    "DRUM_NOTE_VARIATION_PARAMETER5": 271,
    "DRUM_NOTE_VARIATION_PARAMETER6": 272,
    "DRUM_NOTE_VARIATION_PARAMETER7": 273,
    "DRUM_NOTE_VARIATION_PARAMETER8": 274,
    "DRUM_NOTE_VARIATION_PARAMETER9": 275,
    "DRUM_NOTE_VARIATION_PARAMETER10": 276,

    # Drum Kit Selection
    "DRUM_KIT_SELECT_MSB": 277,
    "DRUM_KIT_SELECT_LSB": 278,

    # Drum Setup Channel (Channel 16, 0-based: 15)
    "DRUM_SETUP_CHANNEL": 15,

    # XG Drum Map (MIDI note -> instrument name)
    "XG_DRUM_MAP": {
        35: "Acoustic Bass Drum",
        36: "Bass Drum 1",
        37: "Side Stick",
        38: "Acoustic Snare",
        39: "Hand Clap",
        40: "Electric Snare",
        41: "Low Floor Tom",
        42: "Closed Hi Hat",
        43: "High Floor Tom",
        44: "Pedal Hi-Hat",
        45: "Low Tom",
        46: "Open Hi-Hat",
        47: "Low-Mid Tom",
        48: "Hi-Mid Tom",
        49: "Crash Cymbal 1",
        50: "High Tom",
        51: "Ride Cymbal 1",
        52: "Chinese Cymbal",
        53: "Ride Bell",
        54: "Tambourine",
        55: "Splash Cymbal",
        56: "Cowbell",
        57: "Crash Cymbal 2",
        58: "Vibra Slap",
        59: "Ride Cymbal 2",
        60: "High Bongo",
        61: "Low Bongo",
        62: "Mute High Conga",
        63: "Open High Conga",
        64: "Low Conga",
        65: "High Timbale",
        66: "Low Timbale",
        67: "High Agogo",
        68: "Low Agogo",
        69: "Cabasa",
        70: "Maracas",
        71: "Short Whistle",
        72: "Long Whistle",
        73: "Short Guiro",
        74: "Long Guiro",
        75: "Claves",
        76: "High Wood Block",
        77: "Low Wood Block",
        78: "Mute Cuica",
        79: "Open Cuica",
        80: "Mute Triangle",
        81: "Open Triangle"
    }
}

# Default Configuration Values
DEFAULT_CONFIG = {
    "SAMPLE_RATE": 48000,
    "BLOCK_SIZE": 1024,
    "MAX_POLYPHONY": 64,
    "MASTER_VOLUME": 1.0,
    "DEFAULT_PITCH_BEND_RANGE": 2,
    "DEFAULT_REVERB_SEND": 40,
    "DEFAULT_CHORUS_SEND": 0,
    "DEFAULT_VARIATION_SEND": 0,
    "NUM_MIDI_CHANNELS": 16
}

# Voice Allocation Modes
VOICE_ALLOCATION_MODES = {
    "POLY1": 0,   # Basic polyphonic mode
    "POLY2": 1,   # Priority-based polyphonic mode
    "POLY3": 2,   # Advanced polyphonic mode with voice stealing
    "MONO1": 3,   # Basic monophonic mode
    "MONO2": 4,   # Monophonic with portamento
    "MONO3": 5    # Monophonic with legato
}

# Default Drum Kit Parameters
DEFAULT_DRUM_KIT_NOTES = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

DEFAULT_DRUM_PARAMETERS = {
    "tune": 0.0,          # No tuning adjustment
    "level": 1.0,         # Full level
    "pan": 0.0,           # Center pan
    "reverb_send": 0.2,   # 20% reverb send
    "chorus_send": 0.0,   # No chorus send
    "variation_send": 0.0, # No variation send
    "filter_cutoff": 1000.0,  # Default cutoff
    "filter_resonance": 0.7,  # Default resonance
    "eg_attack": 0.01,    # Fast attack
    "eg_decay": 0.3,      # Medium decay
    "eg_release": 0.5,    # Medium release
    "pitch_coarse": 0,    # No coarse tuning
    "pitch_fine": 0,      # No fine tuning
}
