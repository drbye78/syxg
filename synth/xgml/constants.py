"""
XGML Constants and Definitions

Contains all constants, mappings, and definitions used by the XGML parser and translator.
"""
from __future__ import annotations

XGML_VERSION = "2.1"

# XGML Document Sections (v2.1)
XGML_SECTIONS = [
    # Metadata
    'xg_dsl_version',
    'description',
    'timestamp',

    # Legacy v1.0 sections
    'basic_messages',
    'rpn_parameters',
    'channel_parameters',
    'drum_parameters',
    'system_exclusive',
    'modulation_routing',
    'effects',
    'presets',
    'advanced_features',
    'sequences',

    # Modern v2.0 sections
    'synthesis_engines',
    'gs_configuration',
    'mpe_configuration',
    'modulation_matrix',
    'effects_configuration',
    'arpeggiator_configuration',
    'microtonal_tuning',

    # Advanced Engine Configurations (v2.1)
    'fm_x_engine',
    'sfz_engine',
    'physical_engine',
    'spectral_engine'
]

# XGML Sequence Types
SEQUENCE_TYPES = [
    'track',
    'events',
    'parameters'
]

# Program Name to MIDI Number Mapping (GM/XG Standard)
PROGRAM_NAMES = {
    # Pianos
    'acoustic_grand_piano': 0,
    'bright_acoustic_piano': 1,
    'electric_grand_piano': 2,
    'honky_tonk_piano': 3,
    'electric_piano_1': 4,
    'electric_piano_2': 5,
    'harpsichord': 6,
    'clavinet': 7,

    # Chromatic Percussion
    'celesta': 8,
    'glockenspiel': 9,
    'music_box': 10,
    'vibraphone': 11,
    'marimba': 12,
    'xylophone': 13,
    'tubular_bells': 14,
    'dulcimer': 15,

    # Organs
    'drawbar_organ': 16,
    'percussive_organ': 17,
    'rock_organ': 18,
    'church_organ': 19,
    'reed_organ': 20,
    'accordion': 21,
    'harmonica': 22,
    'tango_accordion': 23,

    # Guitars
    'nylon_string_guitar': 24,
    'steel_string_guitar': 25,
    'electric_jazz_guitar': 26,
    'electric_clean_guitar': 27,
    'electric_muted_guitar': 28,
    'overdriven_guitar': 29,
    'distortion_guitar': 30,
    'guitar_harmonics': 31,

    # Bass
    'acoustic_bass': 32,
    'electric_bass_finger': 33,
    'electric_bass_pick': 34,
    'fretless_bass': 35,
    'slap_bass_1': 36,
    'slap_bass_2': 37,
    'synth_bass_1': 38,
    'synth_bass_2': 39,

    # Strings
    'violin': 40,
    'viola': 41,
    'cello': 42,
    'contrabass': 43,
    'tremolo_strings': 44,
    'pizzicato_strings': 45,
    'orchestral_harp': 46,
    'timpani': 47,

    # Ensemble
    'string_ensemble_1': 48,
    'string_ensemble_2': 49,
    'synth_strings_1': 50,
    'synth_strings_2': 51,
    'choir_aahs': 52,
    'voice_oohs': 53,
    'synth_voice': 54,
    'orchestra_hit': 55,

    # Brass
    'trumpet': 56,
    'trombone': 57,
    'tuba': 58,
    'muted_trumpet': 59,
    'french_horn': 60,
    'brass_section': 61,
    'synth_brass_1': 62,
    'synth_brass_2': 63,

    # Reed
    'soprano_sax': 64,
    'alto_sax': 65,
    'tenor_sax': 66,
    'baritone_sax': 67,
    'oboe': 68,
    'english_horn': 69,
    'bassoon': 70,
    'clarinet': 71,

    # Pipe
    'piccolo': 72,
    'flute': 73,
    'recorder': 74,
    'pan_flute': 75,
    'blown_bottle': 76,
    'shakuhachi': 77,
    'whistle': 78,
    'ocarina': 79,

    # Synth Lead
    'lead_1_square': 80,
    'lead_2_sawtooth': 81,
    'lead_3_calliope': 82,
    'lead_4_chiff': 83,
    'lead_5_charang': 84,
    'lead_6_voice': 85,
    'lead_7_fifths': 86,
    'lead_8_bass_lead': 87,

    # Synth Pad
    'pad_1_new_age': 88,
    'pad_2_warm': 89,
    'pad_3_polysynth': 90,
    'pad_4_choir': 91,
    'pad_5_bowed': 92,
    'pad_6_metallic': 93,
    'pad_7_halo': 94,
    'pad_8_sweep': 95,

    # Synth Effects
    'fx_1_rain': 96,
    'fx_2_soundtrack': 97,
    'fx_3_crystal': 98,
    'fx_4_atmosphere': 99,
    'fx_5_brightness': 100,
    'fx_6_goblins': 101,
    'fx_7_echoes': 102,
    'fx_8_sci_fi': 103,

    # Ethnic
    'sitar': 104,
    'banjo': 105,
    'shamisen': 106,
    'koto': 107,
    'kalimba': 108,
    'bag_pipe': 109,
    'fiddle': 110,
    'shanai': 111,

    # Percussion
    'tinkle_bell': 112,
    'agogo': 113,
    'steel_drums': 114,
    'woodblock': 115,
    'taiko_drum': 116,
    'melodic_tom': 117,
    'synth_drum': 118,
    'reverse_cymbal': 119,

    # Sound Effects
    'guitar_fret_noise': 120,
    'breath_noise': 121,
    'seashore': 122,
    'bird_tweet': 123,
    'telephone_ring': 124,
    'helicopter': 125,
    'applause': 126,
    'gunshot': 127
}

# MIDI Controller Names (CC 0-119)
CONTROLLER_NAMES = {
    'bank_msb': 0,
    'bank_lsb': 32,
    'modulation': 1,
    'breath_controller': 2,
    'foot_controller': 4,
    'portamento_time': 5,
    'data_entry_msb': 6,
    'volume': 7,
    'balance': 8,
    'pan': 10,
    'expression': 11,
    'effect_control_1': 12,
    'effect_control_2': 13,
    'general_purpose_1': 16,
    'general_purpose_2': 17,
    'general_purpose_3': 18,
    'general_purpose_4': 19,
    'general_purpose_5': 80,
    'general_purpose_6': 81,
    'general_purpose_7': 82,
    'general_purpose_8': 83,

    # XG Sound Controllers
    'brightness': 74,
    'harmonic_content': 71,
    'release_time': 72,
    'attack_time': 73,
    'decay_time': 75,
    'vibrato_rate': 76,
    'vibrato_depth': 77,
    'vibrato_delay': 78,

    # XG Effect Sends
    'reverb_send': 91,
    'chorus_send': 93,
    'variation_send': 94,
    'external_data': 95,

    # XG General Purpose
    'sound_variation': 70,
    'tremor': 92,

    # Boolean Controllers
    'sustain': 64,
    'portamento': 65,
    'sostenuto': 66,
    'soft_pedal': 67,
    'legato_foot': 68,
    'hold_2': 69,

    # NRPN/RPN
    'nrpn_lsb': 98,
    'nrpn_msb': 99,
    'rpn_lsb': 100,
    'rpn_msb': 101,
    'data_increment': 96,
    'data_decrement': 97
}

# Pan Position Values
PAN_POSITIONS = {
    'left': 0,
    'right': 127,
    'center': 64,
    'left_10': 26,   # 10% left
    'left_20': 20,   # 20% left
    'left_30': 13,   # 30% left
    'right_10': 102, # 10% right
    'right_20': 108, # 20% right
    'right_30': 115  # 30% right
}

# Curve Types for Interpolation
CURVE_TYPES = [
    'linear',
    'exponential',
    'sine_wave',
    'triangle_wave',
    'sawtooth_wave',
    'square_wave',
    'adsr',
    'ar',
    'one_shot',
    'crescendo',
    'diminuendo',
    'vibrato',
    'tremolo',
    'glissando'
]

# Articulation Types
ARTICULATION_TYPES = [
    'legato',
    'staccato',
    'accent',
    'tenuto'
]

# Drum Kit Names
DRUM_KIT_NAMES = {
    'standard_drum_kit': 0,
    'room_drum_kit': 8,
    'rock_drum_kit': 16,
    'electronic_drum_kit': 24,
    'analog_drum_kit': 25,
    'jazz_drum_kit': 32,
    'brush_drum_kit': 40,
    'orchestral_drum_kit': 48,
    'sf_x_drum_kit': 56
}

# XG System Effects Types
SYSTEM_EFFECT_TYPES = {
    # Reverb Types
    'hall_1': 0, 'hall_2': 1, 'hall_3': 2, 'hall_4': 3,
    'room_1': 4, 'room_2': 5, 'room_3': 6, 'room_4': 7,
    'stage_1': 8, 'stage_2': 9, 'stage_3': 10, 'stage_4': 11,
    'plate': 12,

    # Chorus Types
    'chorus_1': 0, 'chorus_2': 1, 'celeste_1': 2, 'celeste_2': 3,
    'flanger_1': 4, 'flanger_2': 5
}

# XG Variation Effect Types
VARIATION_EFFECT_TYPES = {
    'chorus_1': 0, 'chorus_2': 1, 'chorus_3': 2, 'chorus_4': 3,
    'celeste_1': 4, 'celeste_2': 5,
    'flanger_1': 6, 'flanger_2': 7,
    'phaser_1': 8, 'phaser_2': 9,
    'auto_wah': 10, 'rotary_speaker': 11, 'tremolo': 12,
    'delay_lcr': 13, 'delay_lr': 14
}

# XG Insertion Effect Types
INSERTION_EFFECT_TYPES = {
    'distortion': 0, 'compressor': 1, '6band_eq': 2, 'delay': 3,
    'chorus': 4, 'flanger': 5, 'phaser': 6, 'auto_wah': 7,
    'tremolo': 8, 'rotary_speaker': 9, 'guitar_amp': 10, 'limiter': 11
}

# Filter Types
FILTER_TYPES = {
    'lowpass': 0,
    'highpass': 1,
    'bandpass': 2,
    'bandreject': 3
}

# LFO Waveforms
LFO_WAVEFORMS = {
    'triangle': 0,
    'sawtooth': 1,
    'square': 2,
    'sine': 3
}

# Controller Assignment Values
CONTROLLER_ASSIGNMENTS = {
    'off': 0,
    'modulation': 1,
    'volume': 2,
    'pan': 3,
    'expression': 4,
    'reverb_send': 5,
    'chorus_send': 6,
    'variation_send': 7,
    'filter_cutoff': 8,
    'filter_resonance': 9,
    'pitch_modulation': 10,
    'portamento_time': 11,
    'pitch_bend_range': 12
}

# Modern Synthesis Engine Types (v2.0)
SYNTHESIS_ENGINES = {
    'sf2': 'sf2',
    'sfz': 'sfz',
    'fm': 'fm',
    'additive': 'additive',
    'wavetable': 'wavetable',
    'physical': 'physical',
    'granular': 'granular',
    'spectral': 'spectral',
    'convolution_reverb': 'convolution_reverb',
    'advanced_physical': 'advanced_physical'
}

# GS Reverb Types
GS_REVERB_TYPES = {
    'off': 0,
    'small_room': 1,
    'medium_room': 2,
    'large_room': 3,
    'medium_hall': 4,
    'large_hall': 5,
    'plate': 6
}

# GS Chorus Types
GS_CHORUS_TYPES = {
    'off': 0,
    'chorus1': 1,
    'chorus2': 2,
    'celeste1': 3,
    'celeste2': 4,
    'flanger1': 5,
    'flanger2': 6
}

# GS Delay Types
GS_DELAY_TYPES = {
    'off': 0,
    'delay1': 1,
    'delay2': 2,
    'delay3': 3,
    'delay4': 4,
    'pan_delay1': 5,
    'pan_delay2': 6
}

# MPE Controller Numbers
MPE_CONTROLLERS = {
    'timbre': 74,
    'slide': 75,
    'lift': 76
}

# Advanced Effect Types
ADVANCED_EFFECT_TYPES = {
    # System Reverb Types
    'hall_1': 0, 'hall_2': 1, 'hall_3': 2, 'hall_4': 3,
    'room_1': 4, 'room_2': 5, 'room_3': 6, 'room_4': 7,
    'stage_1': 8, 'stage_2': 9, 'stage_3': 10, 'stage_4': 11,
    'plate': 12,

    # System Chorus Types
    'chorus_1': 0, 'chorus_2': 1, 'celeste_1': 2, 'celeste_2': 3,
    'flanger_1': 4, 'flanger_2': 5,

    # Variation Effect Types (62 types)
    'chorus1': 0, 'chorus2': 1, 'chorus3': 2, 'chorus4': 3,
    'celeste1': 4, 'celeste2': 5, 'flanger1': 6, 'flanger2': 7,
    'phaser1': 8, 'phaser2': 9, 'auto_wah': 10, 'rotary_speaker': 11,
    'tremolo': 12, 'delay_lcr': 13, 'delay_lr': 14,

    # Insertion Effect Types (17 types)
    'thru': 0, 'stereo_eq': 1, 'spectrum': 2, 'enhancer': 3,
    'overdrive': 4, 'distortion': 5, 'phaser': 6, 'auto_wah': 7,
    'rotary': 8, 'stereo_flanger': 9, 'step_flanger': 10, 'tremolo': 11,
    'auto_pan': 12, 'amp_simulator': 13, 'compressor': 14,
    'limiter': 15, 'delay_lcr': 16
}

# EQ Types
EQ_TYPES = {
    'flat': 0,
    'jazz': 1,
    'pops': 2,
    'rock': 3,
    'concert': 4
}

# Temperament Types
TEMPERAMENTS = {
    'equal': 'equal',
    'just': 'just',
    'pythagorean': 'pythagorean',
    'meantone': 'meantone',
    'werckmeister': 'werckmeister',
    'kirnberger': 'kirnberger',
    'custom': 'custom'
}

# Modulation Sources
MODULATION_SOURCES = {
    'lfo1': 'lfo1',
    'lfo2': 'lfo2',
    'envelope': 'envelope',
    'velocity': 'velocity',
    'aftertouch': 'aftertouch',
    'mod_wheel': 'mod_wheel',
    'pitch_bend': 'pitch_bend',
    'expression': 'expression',
    'breath': 'breath',
    'foot': 'foot',
    'timbre': 'timbre',
    'slide': 'slide',
    'lift': 'lift',
    'note_number': 'note_number',
    'random': 'random',
    'alternate': 'alternate'
}

# Modulation Destinations
MODULATION_DESTINATIONS = {
    'pitch': 'pitch',
    'volume': 'volume',
    'pan': 'pan',
    'filter_cutoff': 'filter_cutoff',
    'filter_resonance': 'filter_resonance',
    'filter_envelope': 'filter_envelope',
    'amp_envelope': 'amp_envelope',
    'lfo_rate': 'lfo_rate',
    'lfo_depth': 'lfo_depth',
    'timbre': 'timbre',
    'brightness': 'brightness',
    'harmonic_content': 'harmonic_content',
    'release_time': 'release_time',
    'attack_time': 'attack_time',
    'decay_time': 'decay_time',
    'sustain': 'sustain',
    'vibrato_rate': 'vibrato_rate',
    'vibrato_depth': 'vibrato_depth',
    'tremolo_rate': 'tremolo_rate',
    'tremolo_depth': 'tremolo_depth',
    'effect_send': 'effect_send',
    'effect_param': 'effect_param'
}

# Automation Curve Types
AUTOMATION_CURVE_TYPES = {
    'linear': 'linear',
    'exponential': 'exponential',
    'sine': 'sine',
    'triangle': 'triangle',
    'sawtooth': 'sawtooth',
    'square': 'square',
    'custom': 'custom'
}

# Envelope Stages
ENVELOPE_STAGES = {
    'attack': 'attack',
    'decay': 'decay',
    'sustain': 'sustain',
    'release': 'release',
    'hold': 'hold',
    'delay': 'delay'
}
