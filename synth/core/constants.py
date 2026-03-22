"""
XG Synthesizer Constants

Contains all MIDI constants, XG-specific constants, and default configuration values.
"""

from __future__ import annotations

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
        81: "Open Triangle",
    },
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
    "NUM_MIDI_CHANNELS": 16,
}

# Convenience constants (exposed for easier import)
SAMPLE_RATE = DEFAULT_CONFIG["SAMPLE_RATE"]
BLOCK_SIZE = DEFAULT_CONFIG["BLOCK_SIZE"]
MAX_POLYPHONY = DEFAULT_CONFIG["MAX_POLYPHONY"]

# Voice Allocation Modes
VOICE_ALLOCATION_MODES = {
    "POLY1": 0,  # Basic polyphonic mode
    "POLY2": 1,  # Priority-based polyphonic mode
    "POLY3": 2,  # Advanced polyphonic mode with voice stealing
    "MONO1": 3,  # Basic monophonic mode
    "MONO2": 4,  # Monophonic with portamento
    "MONO3": 5,  # Monophonic with legato
}

# Default Drum Kit Parameters
DEFAULT_DRUM_KIT_NOTES = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

DEFAULT_DRUM_PARAMETERS = {
    "tune": 0.0,  # No tuning adjustment
    "level": 1.0,  # Full level
    "pan": 0.0,  # Center pan
    "reverb_send": 0.2,  # 20% reverb send
    "chorus_send": 0.0,  # No chorus send
    "variation_send": 0.0,  # No variation send
    "filter_cutoff": 1000.0,  # Default cutoff
    "filter_resonance": 0.7,  # Default resonance
    "eg_attack": 0.01,  # Fast attack
    "eg_decay": 0.3,  # Medium decay
    "eg_release": 0.5,  # Medium release
    "pitch_coarse": 0,  # No coarse tuning
    "pitch_fine": 0,  # No fine tuning
}

# XG Voice NRPN Parameters - Complete XG Voice Parameter Mapping
XG_VOICE_NRPN_PARAMS = {
    # Element Switch Parameters (MSB 127, LSB 0-7)
    0: "element_switch",  # Bit field for active elements
    1: "element_switch_lsb",  # LSB for element switch (reserved)
    # Voice Parameters (MSB 127, LSB 8-127)
    8: "detune",  # Voice detune (±400 cents)
    9: "volume",  # Voice volume (0-127)
    10: "pan",  # Voice pan (-64 to +63)
    11: "assign_mode",  # Voice assignment mode (0-2)
    12: "coarse_tune",  # Coarse tuning (-24 to +24 semitones)
    13: "fine_tune",  # Fine tuning (-50 to +50 cents)
    # Filter Parameters (MSB 127, LSB 32-47)
    32: "filter_cutoff_freq",  # Filter cutoff frequency (0-127)
    33: "filter_resonance",  # Filter resonance (0-127)
    34: "filter_eg_depth",  # Filter EG depth (±63)
    35: "filter_lfo_depth",  # Filter LFO depth (0-127)
    # Envelope Parameters (MSB 127, LSB 48-96)
    48: "amp_attack_time",  # Amplitude envelope attack time (0-127)
    49: "amp_decay_time",  # Amplitude envelope decay time (0-127)
    50: "amp_sustain_level",  # Amplitude envelope sustain level (0-127)
    51: "amp_release_time",  # Amplitude envelope release time (0-127)
    52: "filter_attack_time",  # Filter envelope attack time (0-127)
    53: "filter_decay_time",  # Filter envelope decay time (0-127)
    54: "filter_sustain_level",  # Filter envelope sustain level (0-127)
    55: "filter_release_time",  # Filter envelope release time (0-127)
    # LFO Parameters (MSB 127, LSB 97-120)
    97: "lfo_speed",  # LFO speed (0-127)
    98: "lfo_depth",  # LFO depth (0-127)
    99: "lfo_waveform",  # LFO waveform type (0-3)
    100: "lfo_delay",  # LFO delay time (0-127)
    # Reserved for future XG Voice parameters
    121: "reserved_1",
    122: "reserved_2",
    123: "reserved_3",
    124: "reserved_4",
    125: "reserved_5",
    126: "reserved_6",
    127: "reserved_7",
}

# Convenience mapping for XG Voice NRPN parameters
XG_VOICE_NRPN_NAMES = {v: k for k, v in XG_VOICE_NRPN_PARAMS.items()}

# XG System Effects NRPN Parameters
XG_SYSTEM_EFFECTS_NRPN = {
    # Reverb Parameters (MSB 0)
    0: "reverb_type",
    1: "reverb_time",
    2: "reverb_diffusion",
    3: "reverb_pre_delay",
    4: "reverb_tone",
    5: "reverb_level",
    # Chorus Parameters (MSB 1)
    8: "chorus_type",
    9: "chorus_lfo_freq",
    10: "chorus_depth",
    11: "chorus_feedback",
    12: "chorus_send_to_reverb",
    13: "chorus_level",
    # Variation Parameters (MSB 2)
    16: "variation_type",
    17: "variation_parameter1",
    18: "variation_parameter2",
    19: "variation_parameter3",
    20: "variation_parameter4",
    21: "variation_parameter5",
    22: "variation_parameter6",
    23: "variation_parameter7",
    24: "variation_parameter8",
    25: "variation_level",
    # Multi Effects Parameters (MSB 3)
    26: "multi_fx_type",
    27: "multi_fx_part_parameter",
    28: "multi_fx_return_level",
    29: "multi_fx_pan",
    30: "multi_fx_send_reverb",
    31: "multi_fx_send_chorus",
    32: "multi_fx_send_delay",
}

# XG Drum Kit NRPN Parameters (MSB 40-41)
XG_DRUM_NRPN_PARAMS = {
    # Drum Note Parameters (MSB 40, LSB 0-127 = MIDI note numbers)
    0: "drum_tune",  # Fine tuning (-64 to +63)
    1: "drum_level",  # Note level (0-127)
    2: "drum_pan",  # Note pan (-64 to +63)
    3: "drum_reverb",  # Reverb send (0-127)
    4: "drum_chorus",  # Chorus send (0-127)
    5: "drum_variation",  # Variation send (0-127)
    6: "drum_cutoff",  # Filter cutoff frequency (0-127)
    7: "drum_resonance",  # Filter resonance (0-127)
    8: "drum_eg_attack",  # EG attack time (0-127)
    9: "drum_eg_decay",  # EG decay time (0-127)
    10: "drum_eg_release",  # EG release time (0-127)
    11: "drum_pitch_coarse",  # Coarse pitch tuning (-24 to +24 semitones)
    12: "drum_pitch_fine",  # Fine pitch tuning (-50 to +50 cents)
    # Drum Kit Selection (MSB 41, LSB 0)
    256: "drum_kit_select",  # MSB for drum kit selection (bank select)
    # Drum Setup Channel (MSB 40 or 41, LSB 254)
    254: "drum_setup_channel",  # Channel 16 (0-based: 15) - drum setup channel
}


class SynthConstants:
    """
    XG Synthesizer Constants Class

    Provides centralized access to all synthesizer constants and configuration values.
    """

    def __init__(self):
        """Initialize constants access."""
        pass

    # MIDI Constants
    @property
    def midi_constants(self):
        """Get MIDI system constants."""
        return MIDI_CONSTANTS.copy()

    @property
    def note_off(self):
        return MIDI_CONSTANTS["NOTE_OFF"]

    @property
    def note_on(self):
        return MIDI_CONSTANTS["NOTE_ON"]

    @property
    def control_change(self):
        return MIDI_CONSTANTS["CONTROL_CHANGE"]

    @property
    def program_change(self):
        return MIDI_CONSTANTS["PROGRAM_CHANGE"]

    @property
    def pitch_bend(self):
        return MIDI_CONSTANTS["PITCH_BEND"]

    @property
    def system_exclusive(self):
        return MIDI_CONSTANTS["SYSTEM_EXCLUSIVE"]

    # XG Constants
    @property
    def xg_constants(self):
        """Get XG-specific constants."""
        return XG_CONSTANTS.copy()

    @property
    def drum_setup_channel(self):
        """Get drum setup channel (0-based)."""
        return XG_CONSTANTS["DRUM_SETUP_CHANNEL"]

    # Default Configuration
    @property
    def default_config(self):
        """Get default configuration values."""
        return DEFAULT_CONFIG.copy()

    @property
    def sample_rate(self):
        """Get default sample rate."""
        return DEFAULT_CONFIG["SAMPLE_RATE"]

    @property
    def block_size(self):
        """Get default block size."""
        return DEFAULT_CONFIG["BLOCK_SIZE"]

    @property
    def max_polyphony(self):
        """Get default maximum polyphony."""
        return DEFAULT_CONFIG["MAX_POLYPHONY"]

    @property
    def num_midi_channels(self):
        """Get number of MIDI channels."""
        return DEFAULT_CONFIG["NUM_MIDI_CHANNELS"]

    # Voice Allocation
    @property
    def voice_allocation_modes(self):
        """Get voice allocation modes."""
        return VOICE_ALLOCATION_MODES.copy()

    # XG Voice NRPN Parameters
    @property
    def xg_voice_nrpn_params(self):
        """Get XG voice NRPN parameter mapping."""
        return XG_VOICE_NRPN_PARAMS.copy()

    @property
    def xg_voice_nrpn_names(self):
        """Get XG voice NRPN parameter names."""
        return XG_VOICE_NRPN_NAMES.copy()

    # XG System Effects NRPN
    @property
    def xg_system_effects_nrpn(self):
        """Get XG system effects NRPN parameters."""
        return XG_SYSTEM_EFFECTS_NRPN.copy()

    # XG Drum Parameters
    @property
    def xg_drum_nrpn_params(self):
        """Get XG drum NRPN parameters."""
        return XG_DRUM_NRPN_PARAMS.copy()

    @property
    def default_drum_parameters(self):
        """Get default drum kit parameters."""
        return DEFAULT_DRUM_PARAMETERS.copy()

    @property
    def default_drum_kit_notes(self):
        """Get default drum kit note numbers."""
        return DEFAULT_DRUM_KIT_NOTES.copy()

    # XG Drum Map
    @property
    def xg_drum_map(self):
        """Get XG drum map (MIDI note -> instrument name)."""
        return XG_CONSTANTS["XG_DRUM_MAP"].copy()

    def get_drum_instrument_name(self, note: int) -> str:
        """Get drum instrument name for MIDI note number."""
        return XG_CONSTANTS["XG_DRUM_MAP"].get(note, f"Unknown ({note})")

    def get_midi_constant(self, name: str):
        """Get MIDI constant by name."""
        return MIDI_CONSTANTS.get(name.upper())

    def get_xg_constant(self, name: str):
        """Get XG constant by name."""
        return XG_CONSTANTS.get(name.upper())

    def get_default_config_value(self, name: str):
        """Get default configuration value by name."""
        return DEFAULT_CONFIG.get(name.upper())
