"""
Main synthesizer class for S.Art2.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any

import numpy as np
from scipy.io import wavfile

from .constants import (
    DEFAULT_SAMPLE_RATE,
    NRPN_MSB_CONTROL,
    NRPN_LSB_CONTROL,
    MOD_WHEEL_CONTROL,
    SynthConfig,
)
from .nrpn import YamahaNRPNMapper, midi_note_to_frequency
from .voice import VoiceManager, NoteEvent
from .effects import ReverbEffect, DelayEffect
from .audio import create_audio_output

logger = logging.getLogger(__name__)


class SuperArticulation2Synthesizer:
    """
    Enhanced Super Articulation 2 (S.Art2) synthesizer with:
    - Polyphonic voice management
    - Real-time audio output
    - Effects processing (reverb, delay)
    - Pitch bend and mod wheel support
    - Stereo output
    - Bug fixes
    """
    
    # Instrument parameter definitions (Extended list with 60+ instruments)
    INSTRUMENT_PARAMS: Dict[str, Dict] = {
        # === SAXOPHONES ===
        'soprano_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.3, 'mod_index_max': 4.5,
            'attack_time': 0.04, 'decay_time': 0.08, 'sustain_level': 0.72,
            'release_time': 0.18, 'feedback': 0.98
        },
        'alto_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.4, 'mod_index_max': 5.0,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.72,
            'release_time': 0.2, 'feedback': 0.98
        },
        'tenor_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.6, 'mod_index_max': 5.5,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.75,
            'release_time': 0.2, 'feedback': 0.98
        },
        'baritone_sax': {
            'synthesis_method': 'fm', 'mod_ratio': 1.7, 'mod_index_max': 6.0,
            'attack_time': 0.06, 'decay_time': 0.12, 'sustain_level': 0.78,
            'release_time': 0.25, 'feedback': 0.98
        },
        'saxophone': {  # Generic/default
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 5.0,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.7,
            'release_time': 0.2, 'feedback': 0.98
        },
        
        # === BRASS ===
        'piccolo_trumpet': {
            'synthesis_method': 'fm', 'mod_ratio': 1.8, 'mod_index_max': 3.5,
            'attack_time': 0.02, 'decay_time': 0.06, 'sustain_level': 0.75,
            'release_time': 0.12, 'feedback': 0.98
        },
        'trumpet': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 4.0,
            'attack_time': 0.03, 'decay_time': 0.08, 'sustain_level': 0.8,
            'release_time': 0.15, 'feedback': 0.98
        },
        'flugelhorn': {
            'synthesis_method': 'fm', 'mod_ratio': 1.9, 'mod_index_max': 3.8,
            'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.82,
            'release_time': 0.2, 'feedback': 0.98
        },
        'french_horn': {
            'synthesis_method': 'fm', 'mod_ratio': 2.2, 'mod_index_max': 4.2,
            'attack_time': 0.06, 'decay_time': 0.12, 'sustain_level': 0.8,
            'release_time': 0.25, 'feedback': 0.98
        },
        'trombone': {
            'synthesis_method': 'fm', 'mod_ratio': 2.5, 'mod_index_max': 3.5,
            'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.85,
            'release_time': 0.2, 'feedback': 0.98
        },
        'euphonium': {
            'synthesis_method': 'fm', 'mod_ratio': 2.3, 'mod_index_max': 3.8,
            'attack_time': 0.05, 'decay_time': 0.12, 'sustain_level': 0.82,
            'release_time': 0.22, 'feedback': 0.98
        },
        'tuba': {
            'synthesis_method': 'fm', 'mod_ratio': 0.6, 'mod_index_max': 5.5,
            'attack_time': 0.08, 'decay_time': 0.15, 'sustain_level': 0.75,
            'release_time': 0.3, 'feedback': 0.98
        },
        
        # === WOODWINDS ===
        'piccolo': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.0,
            'attack_time': 0.02, 'decay_time': 0.05, 'sustain_level': 0.6,
            'release_time': 0.1, 'feedback': 0.98
        },
        'flute': {
            'synthesis_method': 'fm', 'mod_ratio': 1.2, 'mod_index_max': 2.5,
            'attack_time': 0.06, 'decay_time': 0.09, 'sustain_level': 0.75,
            'release_time': 0.18, 'feedback': 0.98
        },
        'alto_flute': {
            'synthesis_method': 'fm', 'mod_ratio': 1.15, 'mod_index_max': 2.3,
            'attack_time': 0.07, 'decay_time': 0.1, 'sustain_level': 0.72,
            'release_time': 0.2, 'feedback': 0.98
        },
        'bass_flute': {
            'synthesis_method': 'fm', 'mod_ratio': 1.1, 'mod_index_max': 2.8,
            'attack_time': 0.08, 'decay_time': 0.12, 'sustain_level': 0.7,
            'release_time': 0.22, 'feedback': 0.98
        },
        'oboe': {
            'synthesis_method': 'fm', 'mod_ratio': 1.8, 'mod_index_max': 4.5,
            'attack_time': 0.08, 'decay_time': 0.11, 'sustain_level': 0.65,
            'release_time': 0.22, 'feedback': 0.98
        },
        'english_horn': {
            'synthesis_method': 'fm', 'mod_ratio': 1.7, 'mod_index_max': 4.2,
            'attack_time': 0.09, 'decay_time': 0.12, 'sustain_level': 0.68,
            'release_time': 0.24, 'feedback': 0.98
        },
        'clarinet': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 3.0,
            'attack_time': 0.07, 'decay_time': 0.12, 'sustain_level': 0.6,
            'release_time': 0.25, 'feedback': 0.98
        },
        'bass_clarinet': {
            'synthesis_method': 'fm', 'mod_ratio': 0.9, 'mod_index_max': 3.5,
            'attack_time': 0.08, 'decay_time': 0.14, 'sustain_level': 0.65,
            'release_time': 0.28, 'feedback': 0.98
        },
        'bassoon': {
            'synthesis_method': 'fm', 'mod_ratio': 0.8, 'mod_index_max': 4.8,
            'attack_time': 0.09, 'decay_time': 0.15, 'sustain_level': 0.6,
            'release_time': 0.3, 'feedback': 0.98
        },
        'contrabassoon': {
            'synthesis_method': 'fm', 'mod_ratio': 0.7, 'mod_index_max': 5.0,
            'attack_time': 0.1, 'decay_time': 0.18, 'sustain_level': 0.55,
            'release_time': 0.35, 'feedback': 0.98
        },
        'recorder': {
            'synthesis_method': 'fm', 'mod_ratio': 1.1, 'mod_index_max': 2.2,
            'attack_time': 0.05, 'decay_time': 0.08, 'sustain_level': 0.65,
            'release_time': 0.15, 'feedback': 0.98
        },
        'pan_flute': {
            'synthesis_method': 'fm', 'mod_ratio': 1.05, 'mod_index_max': 2.0,
            'attack_time': 0.03, 'decay_time': 0.06, 'sustain_level': 0.7,
            'release_time': 0.12, 'feedback': 0.98
        },
        'shakuhachi': {
            'synthesis_method': 'fm', 'mod_ratio': 1.25, 'mod_index_max': 3.0,
            'attack_time': 0.08, 'decay_time': 0.15, 'sustain_level': 0.6,
            'release_time': 0.3, 'feedback': 0.98
        },
        
        # === STRINGS ===
        'violin': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.1, 'decay_time': 0.15, 'sustain_level': 0.5,
            'release_time': 0.3
        },
        'viola': {
            'synthesis_method': 'ks', 'feedback': 0.993,
            'attack_time': 0.11, 'decay_time': 0.16, 'sustain_level': 0.48,
            'release_time': 0.32
        },
        'cello': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.12, 'decay_time': 0.18, 'sustain_level': 0.4,
            'release_time': 0.35
        },
        'contrabass': {
            'synthesis_method': 'ks', 'feedback': 0.988,
            'attack_time': 0.14, 'decay_time': 0.2, 'sustain_level': 0.45,
            'release_time': 0.4
        },
        'violin_section': {
            'synthesis_method': 'ks', 'feedback': 0.994,
            'attack_time': 0.12, 'decay_time': 0.18, 'sustain_level': 0.55,
            'release_time': 0.32
        },
        'strings_ensemble': {
            'synthesis_method': 'ks', 'feedback': 0.996,
            'attack_time': 0.15, 'decay_time': 0.2, 'sustain_level': 0.65,
            'release_time': 0.35
        },
        'pizzicato_strings': {
            'synthesis_method': 'ks', 'feedback': 0.95,
            'attack_time': 0.01, 'decay_time': 0.05, 'sustain_level': 0.3,
            'release_time': 0.1
        },
        
        # === PLUCKED/GUITARS ===
        'nylon_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.997,
            'attack_time': 0.02, 'decay_time': 0.04, 'sustain_level': 0.35,
            'release_time': 0.15
        },
        'steel_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.996,
            'attack_time': 0.015, 'decay_time': 0.04, 'sustain_level': 0.4,
            'release_time': 0.12
        },
        'guitar': {
            'synthesis_method': 'ks', 'feedback': 0.996,
            'attack_time': 0.02, 'decay_time': 0.05, 'sustain_level': 0.6,
            'release_time': 0.1
        },
        'electric_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.992,
            'attack_time': 0.015, 'decay_time': 0.06, 'sustain_level': 0.7,
            'release_time': 0.12
        },
        'clean_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.994,
            'attack_time': 0.018, 'decay_time': 0.05, 'sustain_level': 0.55,
            'release_time': 0.1
        },
        'overdrive_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.01, 'decay_time': 0.04, 'sustain_level': 0.75,
            'release_time': 0.08
        },
        'distortion_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.008, 'decay_time': 0.03, 'sustain_level': 0.8,
            'release_time': 0.06
        },
        'bass_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.03, 'decay_time': 0.07, 'sustain_level': 0.55,
            'release_time': 0.15
        },
        'electric_bass': {
            'synthesis_method': 'ks', 'feedback': 0.982,
            'attack_time': 0.025, 'decay_time': 0.06, 'sustain_level': 0.6,
            'release_time': 0.12
        },
        'fretless_bass': {
            'synthesis_method': 'ks', 'feedback': 0.987,
            'attack_time': 0.03, 'decay_time': 0.08, 'sustain_level': 0.52,
            'release_time': 0.18
        },
        'slap_bass': {
            'synthesis_method': 'ks', 'feedback': 0.975,
            'attack_time': 0.005, 'decay_time': 0.02, 'sustain_level': 0.65,
            'release_time': 0.08
        },
        'harp': {
            'synthesis_method': 'ks', 'feedback': 0.997,
            'attack_time': 0.01, 'decay_time': 0.04, 'sustain_level': 0.3,
            'release_time': 0.4
        },
        'banjo': {
            'synthesis_method': 'ks', 'feedback': 0.97,
            'attack_time': 0.005, 'decay_time': 0.03, 'sustain_level': 0.4,
            'release_time': 0.1
        },
        'mandolin': {
            'synthesis_method': 'ks', 'feedback': 0.994,
            'attack_time': 0.015, 'decay_time': 0.04, 'sustain_level': 0.45,
            'release_time': 0.12
        },
        'ukulele': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.01, 'decay_time': 0.03, 'sustain_level': 0.35,
            'release_time': 0.15
        },
        
        # === KEYBOARDS/PERCUSSION ===
        'piano': {
            'synthesis_method': 'ks', 'feedback': 0.999,
            'attack_time': 0.005, 'decay_time': 0.5, 'sustain_level': 0.4,
            'release_time': 0.8
        },
        'grand_piano': {
            'synthesis_method': 'ks', 'feedback': 0.9995,
            'attack_time': 0.003, 'decay_time': 0.6, 'sustain_level': 0.45,
            'release_time': 1.0
        },
        'stage_piano': {
            'synthesis_method': 'ks', 'feedback': 0.998,
            'attack_time': 0.006, 'decay_time': 0.4, 'sustain_level': 0.5,
            'release_time': 0.6
        },
        'electric_piano': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.5,
            'attack_time': 0.008, 'decay_time': 0.3, 'sustain_level': 0.5,
            'release_time': 0.4
        },
        'honkytonk_piano': {
            'synthesis_method': 'ks', 'feedback': 0.998,
            'attack_time': 0.006, 'decay_time': 0.4, 'sustain_level': 0.35,
            'release_time': 0.7
        },
        'clavinet': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.003, 'decay_time': 0.15, 'sustain_level': 0.5,
            'release_time': 0.2
        },
        
        # === ORGANS ===
        'hammond_organ': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 0.8,
            'attack_time': 0.01, 'decay_time': 0.1, 'sustain_level': 0.9,
            'release_time': 0.15
        },
        'perc_organ': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 1.2,
            'attack_time': 0.005, 'decay_time': 0.2, 'sustain_level': 0.8,
            'release_time': 0.25
        },
        'rock_organ': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 1.5,
            'attack_time': 0.008, 'decay_time': 0.15, 'sustain_level': 0.85,
            'release_time': 0.2
        },
        'church_organ': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 0.5,
            'attack_time': 0.02, 'decay_time': 0.3, 'sustain_level': 0.95,
            'release_time': 0.5
        },
        'reed_organ': {
            'synthesis_method': 'fm', 'mod_ratio': 2.5, 'mod_index_max': 1.0,
            'attack_time': 0.015, 'decay_time': 0.2, 'sustain_level': 0.75,
            'release_time': 0.3
        },
        
        # === CHROMATIC PERCUSSION ===
        'vibraphone': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.008, 'decay_time': 0.5, 'sustain_level': 0.3,
            'release_time': 0.8
        },
        'marimba': {
            'synthesis_method': 'ks', 'feedback': 0.98,
            'attack_time': 0.01, 'decay_time': 0.08, 'sustain_level': 0.25,
            'release_time': 0.6
        },
        'xylophone': {
            'synthesis_method': 'ks', 'feedback': 0.975,
            'attack_time': 0.005, 'decay_time': 0.04, 'sustain_level': 0.2,
            'release_time': 0.3
        },
        'glockenspiel': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.003, 'decay_time': 0.8, 'sustain_level': 0.25,
            'release_time': 1.0
        },
        'celesta': {
            'synthesis_method': 'ks', 'feedback': 0.992,
            'attack_time': 0.002, 'decay_time': 0.6, 'sustain_level': 0.3,
            'release_time': 0.9
        },
        'tubular_bells': {
            'synthesis_method': 'ks', 'feedback': 0.999,
            'attack_time': 0.01, 'decay_time': 1.5, 'sustain_level': 0.2,
            'release_time': 2.0
        },
        'carillon': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.002, 'decay_time': 1.2, 'sustain_level': 0.25,
            'release_time': 1.5
        },
        'dulcimer': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.015, 'decay_time': 0.3, 'sustain_level': 0.4,
            'release_time': 0.5
        },
        'santur': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.01, 'decay_time': 0.2, 'sustain_level': 0.35,
            'release_time': 0.4
        },
        
        # === ADDITIONAL GUITARS ===
        'jazz_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.02, 'decay_time': 0.06, 'sustain_level': 0.45,
            'release_time': 0.15
        },
        'muted_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.008, 'decay_time': 0.04, 'sustain_level': 0.35,
            'release_time': 0.08
        },
        'pedal_steel_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.997,
            'attack_time': 0.025, 'decay_time': 0.05, 'sustain_level': 0.5,
            'release_time': 0.2
        },
        'synth_guitar': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.015, 'decay_time': 0.08, 'sustain_level': 0.6,
            'release_time': 0.1
        },
        
        # === ADDITIONAL BASS ===
        'synth_bass': {
            'synthesis_method': 'ks', 'feedback': 0.975,
            'attack_time': 0.02, 'decay_time': 0.05, 'sustain_level': 0.5,
            'release_time': 0.1
        },
        'synth_bass_1': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.0,
            'attack_time': 0.01, 'decay_time': 0.1, 'sustain_level': 0.6,
            'release_time': 0.15
        },
        'synth_bass_2': {
            'synthesis_method': 'fm', 'mod_ratio': 0.5, 'mod_index_max': 3.0,
            'attack_time': 0.015, 'decay_time': 0.08, 'sustain_level': 0.55,
            'release_time': 0.12
        },
        
        # === ADDITIONAL STRINGS ===
        'synth_strings': {
            'synthesis_method': 'ks', 'feedback': 0.997,
            'attack_time': 0.08, 'decay_time': 0.1, 'sustain_level': 0.6,
            'release_time': 0.25
        },
        'slow_strings': {
            'synthesis_method': 'ks', 'feedback': 0.998,
            'attack_time': 0.2, 'decay_time': 0.15, 'sustain_level': 0.55,
            'release_time': 0.4
        },
        '60s_strings': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.1, 'decay_time': 0.12, 'sustain_level': 0.5,
            'release_time': 0.3
        },
        
        # === ADDITIONAL BRASS ===
        'brass_section': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 4.0,
            'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.8,
            'release_time': 0.2
        },
        'synth_brass_1': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 3.0,
            'attack_time': 0.02, 'decay_time': 0.08, 'sustain_level': 0.7,
            'release_time': 0.15
        },
        'synth_brass_2': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 4.0,
            'attack_time': 0.03, 'decay_time': 0.1, 'sustain_level': 0.75,
            'release_time': 0.18
        },
        
        # === SYNTH LEAD ===
        'saw_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.5,
            'attack_time': 0.01, 'decay_time': 0.1, 'sustain_level': 0.8,
            'release_time': 0.15
        },
        'square_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 1.5,
            'attack_time': 0.005, 'decay_time': 0.1, 'sustain_level': 0.7,
            'release_time': 0.12
        },
        'sine_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 0.5,
            'attack_time': 0.02, 'decay_time': 0.15, 'sustain_level': 0.6,
            'release_time': 0.2
        },
        'classic_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 2.0,
            'attack_time': 0.008, 'decay_time': 0.1, 'sustain_level': 0.75,
            'release_time': 0.15
        },
        'doc_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 0.5, 'mod_index_max': 3.5,
            'attack_time': 0.015, 'decay_time': 0.12, 'sustain_level': 0.65,
            'release_time': 0.18
        },
        'unison_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.0,
            'attack_time': 0.01, 'decay_time': 0.08, 'sustain_level': 0.8,
            'release_time': 0.12
        },
        'four_op_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 0.5, 'mod_index_max': 4.0,
            'attack_time': 0.008, 'decay_time': 0.15, 'sustain_level': 0.7,
            'release_time': 0.2
        },
        'chisel_lead': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 2.5,
            'attack_time': 0.005, 'decay_time': 0.08, 'sustain_level': 0.85,
            'release_time': 0.1
        },
        
        # === SYNTH PAD ===
        'warm_pad': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.0,
            'attack_time': 0.1, 'decay_time': 0.2, 'sustain_level': 0.7,
            'release_time': 0.4
        },
        'polysynth': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.0,
            'attack_time': 0.05, 'decay_time': 0.15, 'sustain_level': 0.65,
            'release_time': 0.3
        },
        'space_pad': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 1.5,
            'attack_time': 0.15, 'decay_time': 0.25, 'sustain_level': 0.6,
            'release_time': 0.5
        },
        'bow_pad': {
            'synthesis_method': 'ks', 'feedback': 0.998,
            'attack_time': 0.2, 'decay_time': 0.15, 'sustain_level': 0.55,
            'release_time': 0.5
        },
        'metal_pad': {
            'synthesis_method': 'fm', 'mod_ratio': 2.5, 'mod_index_max': 3.0,
            'attack_time': 0.03, 'decay_time': 0.2, 'sustain_level': 0.7,
            'release_time': 0.35
        },
        'halo_pad': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.2,
            'attack_time': 0.2, 'decay_time': 0.3, 'sustain_level': 0.65,
            'release_time': 0.6
        },
        
        # === SYNTH EFFECTS ===
        'sweep_pad': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 2.0,
            'attack_time': 0.1, 'decay_time': 0.3, 'sustain_level': 0.5,
            'release_time': 0.5
        },
        'rain': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.5,
            'attack_time': 0.05, 'decay_time': 0.2, 'sustain_level': 0.6,
            'release_time': 0.4
        },
        'soundtrack': {
            'synthesis_method': 'fm', 'mod_ratio': 1.5, 'mod_index_max': 1.0,
            'attack_time': 0.15, 'decay_time': 0.25, 'sustain_level': 0.55,
            'release_time': 0.5
        },
        'crystal': {
            'synthesis_method': 'fm', 'mod_ratio': 3.0, 'mod_index_max': 2.5,
            'attack_time': 0.005, 'decay_time': 0.4, 'sustain_level': 0.3,
            'release_time': 0.6
        },
        'atmosphere': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.5,
            'attack_time': 0.1, 'decay_time': 0.2, 'sustain_level': 0.6,
            'release_time': 0.45
        },
        'bright': {
            'synthesis_method': 'fm', 'mod_ratio': 2.0, 'mod_index_max': 2.0,
            'attack_time': 0.02, 'decay_time': 0.15, 'sustain_level': 0.7,
            'release_time': 0.25
        },
        
        # === ETHNIC/WORLD ===
        'sitar': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.01, 'decay_time': 0.1, 'sustain_level': 0.3,
            'release_time': 0.8
        },
        'oud': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.02, 'decay_time': 0.08, 'sustain_level': 0.4,
            'release_time': 0.3
        },
        'bouzouki': {
            'synthesis_method': 'ks', 'feedback': 0.994,
            'attack_time': 0.015, 'decay_time': 0.06, 'sustain_level': 0.45,
            'release_time': 0.25
        },
        'erhu': {
            'synthesis_method': 'ks', 'feedback': 0.995,
            'attack_time': 0.05, 'decay_time': 0.1, 'sustain_level': 0.5,
            'release_time': 0.3
        },
        'shamisen': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.005, 'decay_time': 0.04, 'sustain_level': 0.35,
            'release_time': 0.15
        },
        'koto': {
            'synthesis_method': 'ks', 'feedback': 0.992,
            'attack_time': 0.02, 'decay_time': 0.15, 'sustain_level': 0.3,
            'release_time': 0.5
        },
        'taiko': {
            'synthesis_method': 'ks', 'feedback': 0.95,
            'attack_time': 0.002, 'decay_time': 0.02, 'sustain_level': 0.4,
            'release_time': 0.1
        },
        'shamisen_JP': {
            'synthesis_method': 'ks', 'feedback': 0.985,
            'attack_time': 0.005, 'decay_time': 0.04, 'sustain_level': 0.35,
            'release_time': 0.15
        },
        'kalimba': {
            'synthesis_method': 'ks', 'feedback': 0.99,
            'attack_time': 0.005, 'decay_time': 0.3, 'sustain_level': 0.25,
            'release_time': 0.4
        },
        'bansuri': {
            'synthesis_method': 'fm', 'mod_ratio': 1.3, 'mod_index_max': 2.5,
            'attack_time': 0.05, 'decay_time': 0.12, 'sustain_level': 0.6,
            'release_time': 0.25
        },
        'bagpipe': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.5,
            'attack_time': 0.03, 'decay_time': 0.1, 'sustain_level': 0.7,
            'release_time': 0.2
        },
        'ocarina': {
            'synthesis_method': 'fm', 'mod_ratio': 1.2, 'mod_index_max': 2.0,
            'attack_time': 0.04, 'decay_time': 0.1, 'sustain_level': 0.65,
            'release_time': 0.2
        },
        
        # === PERCUSSIVE ===
        'taiko_drum': {
            'synthesis_method': 'ks', 'feedback': 0.92,
            'attack_time': 0.001, 'decay_time': 0.03, 'sustain_level': 0.3,
            'release_time': 0.08
        },
        'melodic_tom': {
            'synthesis_method': 'ks', 'feedback': 0.97,
            'attack_time': 0.003, 'decay_time': 0.15, 'sustain_level': 0.25,
            'release_time': 0.3
        },
        'synth_drum': {
            'synthesis_method': 'fm', 'mod_ratio': 0.5, 'mod_index_max': 3.0,
            'attack_time': 0.002, 'decay_time': 0.1, 'sustain_level': 0.4,
            'release_time': 0.15
        },
        'reverse_cymbal': {
            'synthesis_method': 'fm', 'mod_ratio': 1.0, 'mod_index_max': 1.5,
            'attack_time': 0.0, 'decay_time': 0.5, 'sustain_level': 0.3,
            'release_time': 0.3
        },
    }
    
    def __init__(
        self,
        instrument: str = 'saxophone',
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        base_feedback: float = 0.98,
        vibrato_depth: float = 0.05,
        vibrato_rate: float = 5.0,
        config: Optional[SynthConfig] = None,
    ):
        # Core parameters
        self.instrument = instrument.lower()
        self.sample_rate = sample_rate
        self.base_feedback = base_feedback
        self.vibrato_depth = vibrato_depth
        self.vibrato_rate = vibrato_rate
        
        # Configuration
        self.config = config or SynthConfig(sample_rate=sample_rate)
        self.config.sample_rate = sample_rate
        
        # Components
        self.nrpn_mapper = YamahaNRPNMapper()
        self.voice_manager = VoiceManager(sample_rate=sample_rate)
        
        # Effects
        self.reverb = ReverbEffect(
            sample_rate=sample_rate,
            room_size=self.config.reverb_room_size,
            wet_dry=self.config.reverb_wet_dry
        )
        self.delay = DelayEffect(
            sample_rate=sample_rate,
            delay_time=self.config.delay_time,
            feedback=self.config.delay_feedback,
            wet_dry=self.config.delay_wet_dry
        )
        
        # Audio output
        self.audio_output = create_audio_output(self.config)
        
        # State
        self.current_articulation = 'normal'
        self.nrpn_msb = 0
        self.nrpn_lsb = 0
        self.current_pitch_bend = 0.0
        self.current_mod_wheel = 0.0
        
        # MIDI Controller State
        self.bank_msb = 0
        self.bank_lsb = 0
        self.program_change = 0
        self.volume = 127
        self.expression = 127
        self.pan = 64  # 64 = center
        self.sustain_pedal = False
        self.sostenuto = False
        self.soft_pedal = False
        self.portamento_on = False
        self.portamento_time = 0
        self.breath_controller = 0
        self.foot_controller = 0
        self.filter_cutoff = 127
        self.filter_resonance = 127
        self.attack_time_adj = 64
        self.release_time_adj = 64
        self.vibrato_rate_adj = 64
        self.vibrato_depth_adj = 64
        self.aftertouch = 0
        
        # Sustained notes for sustain pedal
        self._sustained_notes: Dict[int, float] = {}
        self._sostenuto_notes: Dict[int, float] = {}
        
        # Pitch bend range (semitones)
        self.pitch_bend_range = 2
        
        # Instrument parameters
        self.instrument_params = self._get_instrument_params()
        self._validate_params()
        
        # Real-time control
        self._running = False
        self._midi_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Pre-generated wavetables for Karplus-Strong
        self._ks_wavetables: Dict[int, np.ndarray] = {}
        
        logger.info(f"Initialized S.Art2 synthesizer for {self.instrument} at {sample_rate} Hz")
    
    def _get_instrument_params(self) -> Dict[str, Dict]:
        """Get instrument parameters."""
        return self.INSTRUMENT_PARAMS.get(
            self.instrument,
            self.INSTRUMENT_PARAMS['saxophone']
        )
    
    def _validate_params(self) -> None:
        """Validate synthesizer parameters."""
        if self.instrument not in self.INSTRUMENT_PARAMS:
            raise ValueError(
                f"Unsupported instrument: {self.instrument}. "
                f"Supported: {list(self.INSTRUMENT_PARAMS.keys())}"
            )
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")
        if not 0 < self.base_feedback < 1:
            raise ValueError("Base feedback must be between 0 and 1.")
    
    # =========================================================================
    # Synthesis Methods
    # =========================================================================
    
    def _generate_fm_tone(
        self,
        freq: float,
        duration: float,
        velocity: int,
        params: Dict,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate FM synthesis tone."""
        SEMITONE_RATIO = 1.059463359
        n_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, n_samples, False)
        
        if pitch_bend != 0.0:
            freq = freq * (SEMITONE_RATIO ** pitch_bend)
        
        mod_index = (velocity / 127.0) * params['mod_index_max']
        mod_index *= (1.0 + mod_wheel * 0.5)
        
        mod_freq = freq * params['mod_ratio']
        modulator = np.sin(2 * np.pi * mod_freq * t)
        
        if mod_wheel > 0:
            vibrato = self.vibrato_depth * np.sin(2 * np.pi * self.vibrato_rate * t) * mod_wheel
            t_vibrato = t + vibrato / (2 * np.pi * freq)
        else:
            t_vibrato = t
        
        carrier = np.sin(2 * np.pi * freq * t_vibrato + mod_index * modulator)
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        
        return carrier * envelope * (velocity / 127.0)
    
    def _generate_ks_tone(
        self,
        freq: float,
        duration: float,
        velocity: int,
        params: Dict,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate Karplus-Strong physical modeling synthesis tone."""
        SEMITONE_RATIO = 1.059463359
        n_samples = int(self.sample_rate * duration)
        
        if pitch_bend != 0.0:
            freq = freq * (SEMITONE_RATIO ** pitch_bend)
        
        period = int(self.sample_rate / freq)
        
        if period not in self._ks_wavetables:
            self._ks_wavetables[period] = np.random.uniform(-1, 1, period)
        
        wavetable = self._ks_wavetables[period].copy()
        
        samples = np.zeros(n_samples)
        idx = 0
        prev_sample = 0.0
        
        feedback = params.get('feedback', self.base_feedback)
        
        for i in range(n_samples):
            current_sample = wavetable[idx]
            wavetable[idx] = feedback * 0.5 * (current_sample + prev_sample)
            samples[i] = wavetable[idx]
            prev_sample = current_sample
            idx = (idx + 1) % period
        
        envelope = self._generate_adsr_envelope(duration, velocity, params)
        
        envelope = envelope[:n_samples] if len(envelope) > n_samples else np.pad(
            envelope, (0, n_samples - len(envelope))
        )
        
        samples *= envelope
        
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples /= max_val
        
        samples *= (velocity / 127.0)
        
        return samples.astype(np.float32)
    
    def _generate_adsr_envelope(
        self,
        duration: float,
        velocity: int,
        params: Dict
    ) -> np.ndarray:
        """Generate ADSR envelope with proper edge case handling."""
        total_samples = int(self.sample_rate * duration)
        
        if total_samples <= 0:
            return np.array([])
        
        attack_time = params['attack_time'] * (1.5 if velocity < 80 else 1.0)
        decay_time = params['decay_time']
        release_time = params['release_time']
        sustain_level = params['sustain_level']
        
        attack_samples = min(int(attack_time * self.sample_rate), total_samples // 2)
        decay_samples = min(int(decay_time * self.sample_rate), total_samples - attack_samples)
        release_samples = min(int(release_time * self.sample_rate), total_samples - attack_samples - decay_samples)
        
        sustain_samples = total_samples - attack_samples - decay_samples - release_samples
        if sustain_samples < 0:
            release_samples = total_samples - attack_samples - decay_samples
            sustain_samples = 0
        
        envelope = np.zeros(total_samples)
        
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        decay_start = attack_samples
        decay_end = decay_start + decay_samples
        if decay_samples > 0:
            envelope[decay_start:decay_end] = np.linspace(1, sustain_level, decay_samples)
        
        sustain_end = decay_end + sustain_samples
        if sustain_samples > 0:
            envelope[decay_end:sustain_end] = sustain_level
        
        if release_samples > 0 and sustain_end < total_samples:
            release_start = sustain_end
            envelope[release_start:] = np.linspace(
                sustain_level, 0, min(total_samples - release_start, release_samples)
            )
        
        return envelope
    
    def _generate_base_tone(
        self,
        freq: float,
        duration: float,
        velocity: int = 100,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Generate base tone using appropriate synthesis method."""
        params = self.instrument_params
        
        if params['synthesis_method'] == 'fm':
            return self._generate_fm_tone(freq, duration, velocity, params, pitch_bend, mod_wheel)
        elif params['synthesis_method'] == 'ks':
            return self._generate_ks_tone(freq, duration, velocity, params, pitch_bend, mod_wheel)
        else:
            raise ValueError(f"Unknown synthesis method: {params['synthesis_method']}")
    
    # =========================================================================
    # Articulation Processing
    # =========================================================================
    
    def _apply_articulation(
        self,
        waveform: np.ndarray,
        articulation: str,
        freq: float,
        velocity: int = 100
    ) -> np.ndarray:
        """Apply articulation effect to waveform."""
        SEMITONE_RATIO = 1.059463359
        
        if articulation in ('normal', 'straight', 'legato'):
            return waveform
        
        t = np.arange(len(waveform)) / self.sample_rate
        duration = len(waveform) / self.sample_rate
        
        modification = np.ones_like(waveform)
        additive = np.zeros_like(waveform)
        
        # === DYNAMIC ARTICULATIONS ===
        if articulation == 'staccato':
            decay_env = np.exp(-t / 0.15)
            modification *= decay_env
        
        elif articulation == 'tenuto':
            # No modification - full sustain
            pass
        
        elif articulation == 'accent':
            accent_env = np.exp(-t / 0.08) * 1.4
            modification *= accent_env
        
        elif articulation == 'marcato':
            marcato_env = np.exp(-t / 0.1) * 1.5
            modification *= marcato_env
        
        elif articulation == 'sforzando':
            sfz_env = np.exp(-t / 0.05) * 1.8
            modification *= sfz_env
        
        elif articulation == 'pizzicato':
            decay_env = np.exp(-t / 0.08)
            modification *= decay_env
        
        # === PITCH BEND ARTICULATIONS ===
        elif articulation == 'bend':
            bend_amount = 1.02
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'up_bend':
            bend_amount = 1.03
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform) // 2)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq * bend_amount)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'down_bend':
            bend_amount = 0.97
            freq_slide = np.linspace(freq, freq * bend_amount, len(waveform) // 2)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq * bend_amount)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += bend_wave * fade * 0.5
        
        elif articulation == 'fall':
            fall_amount = 0.9
            freq_slide = np.linspace(freq, freq * fall_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            fall_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += fall_wave * fade * 0.6
        
        elif articulation == 'doit':
            doit_amount = 1.08
            freq_slide = np.linspace(freq, freq * doit_amount, len(waveform) // 3)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq * doit_amount)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            doit_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += doit_wave * fade * 0.5
        
        elif articulation == 'scoop':
            scoop_amount = 0.95
            freq_slide = np.linspace(freq * scoop_amount, freq, len(waveform) // 4)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            scoop_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += scoop_wave * fade * 0.5
        
        elif articulation == 'rip':
            rip_amount = 1.1
            freq_slide = np.linspace(freq, freq * rip_amount, len(waveform) // 4)
            freq_slide = np.concatenate([np.full(len(waveform) - len(freq_slide), freq * rip_amount), freq_slide[::-1]])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            rip_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 4)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += rip_wave * fade * 0.5
        
        # === MODULATION ARTICULATIONS ===
        elif articulation == 'vibrato':
            vibrato = self.vibrato_depth * np.sin(2 * np.pi * self.vibrato_rate * t)
            modification *= (1 + vibrato)
        
        elif articulation == 'tremolo':
            tremolo = 0.15 * (1 + np.sin(2 * np.pi * 6 * t))
            modification *= (1 - tremolo)
        
        elif articulation == 'growl':
            growl_freq = 25.0
            growl = 0.25 * (1 + np.sin(2 * np.pi * growl_freq * t))
            modification *= growl
        
        elif articulation == 'flutter':
            flutter_freq = 12.0
            flutter = 0.15 * (1 + np.sin(2 * np.pi * flutter_freq * t))
            modification *= flutter
        
        elif articulation == 'trill':
            trill_freq = 6.0
            trill_mod = np.sin(2 * np.pi * trill_freq * t)
            freq_mod = freq * (1 + 0.03 * trill_mod * (SEMITONE_RATIO - 1))
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            trill_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.7)
            additive += trill_wave * fade * 0.4
        
        elif articulation == 'shake':
            shake_freq = 8.0
            shake_mod = np.sin(2 * np.pi * shake_freq * t)
            freq_mod = freq * (1 + 0.04 * shake_mod)
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            shake_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.5)
            additive += shake_wave * fade * 0.3
        
        # === NOISE/TEXTURE ARTICULATIONS ===
        elif articulation == 'breath':
            noise = 0.12 * np.random.normal(0, 1, len(waveform))
            low_pass = np.convolve(noise, np.ones(100) / 100, mode='same')
            additive += low_pass
        
        elif articulation == 'tongue_slap':
            slap_duration = 0.015
            slap_samples = min(int(slap_duration * self.sample_rate), len(waveform) // 8)
            slap_noise = 0.35 * np.random.normal(0, 1, slap_samples)
            additive[:slap_samples] += slap_noise
        
        elif articulation == 'key_click':
            click_duration = 0.005
            click_samples = min(int(click_duration * self.sample_rate), 200)
            click_noise = 0.4 * np.random.normal(0, 1, click_samples)
            additive[:click_samples] += click_noise
        
        elif articulation == 'col_legno':
            legno_noise = 0.25 * np.random.normal(0, 1, len(waveform))
            additive += legno_noise
            modification *= np.exp(-t / 0.25)
        
        # === HARMONIC ARTICULATIONS ===
        elif articulation == 'harmonics':
            harmonic_mult = 2.0
            harmonic_wave = np.sin(2 * np.pi * freq * harmonic_mult * t)
            additive += 0.35 * harmonic_wave
        
        elif articulation == 'octave_harm':
            harmonic_wave = np.sin(2 * np.pi * freq * 2 * t)
            additive += 0.3 * harmonic_wave
        
        # === ENVELOPE MODIFICATIONS ===
        elif articulation == 'swell':
            t_last = t[-1] if len(t) > 0 else 1.0
            swell_env = np.sin(np.pi * t / t_last)
            modification *= swell_env * 1.3
        
        elif articulation == 'crescendo':
            cresc_env = np.linspace(0.5, 1.2, len(waveform))
            modification *= cresc_env
        
        elif articulation == 'diminuendo':
            dim_env = np.linspace(1.2, 0.3, len(waveform))
            modification *= dim_env
        
        # === GLISSANDO/PORTAMENTO ===
        elif articulation in ('glissando', 'portamento'):
            gliss_amount = 1.07
            freq_slide = np.linspace(freq, freq * gliss_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            gliss_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade)
            additive += gliss_wave * fade * 0.5
        
        # === BOW TECHNIQUES ===
        elif articulation == 'sul_ponticello':
            pont_noise = 0.2 * np.random.normal(0, 1, len(waveform))
            high_pass = np.cumsum(pont_noise) / len(waveform)
            additive += high_pass
        
        elif articulation == 'sul_tasto':
            # Bright, thin sound - emphasize harmonics
            harmonic = np.sin(2 * np.pi * freq * 3 * t) * 0.2
            additive += harmonic
        
        elif articulation == 'bow_up':
            bow_env = np.linspace(0.8, 1.1, len(waveform))
            modification *= bow_env
        
        elif articulation == 'bow_down':
            bow_env = np.linspace(1.1, 0.8, len(waveform))
            modification *= bow_env
        
        # === GUITAR TECHNIQUES ===
        elif articulation == 'hammer_on':
            hammer_duration = 0.015
            hammer_samples = min(int(hammer_duration * self.sample_rate), len(waveform) // 4)
            if len(waveform) > hammer_samples * 2:
                hammer_env = np.linspace(0, 1.3, hammer_samples)
                env_padded = np.ones(len(waveform))
                env_padded[hammer_samples:hammer_samples*2] = hammer_env
                modification *= env_padded
        
        elif articulation == 'pull_off':
            pull_duration = 0.015
            pull_samples = min(int(pull_duration * self.sample_rate), len(waveform) // 4)
            pull_env = np.linspace(1.2, 0.2, pull_samples)
            env_padded = np.ones(len(waveform))
            env_padded[-pull_samples:] = pull_env
            modification *= env_padded
        
        elif articulation == 'slide':
            slide_amount = 1.05
            freq_slide = np.linspace(freq, freq * slide_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            slide_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform))
            modification *= (1 - fade * 0.5)
            additive += slide_wave * fade * 0.4
        
        elif articulation == 'mute':
            mute_env = np.exp(-t / 0.3)
            modification *= (1 - 0.7 * mute_env)
        
        # === MISC ===
        elif articulation == 'detache':
            detache_samples = min(int(0.08 * self.sample_rate), len(waveform) // 4)
            detache_env = np.ones(len(waveform))
            detache_env[-detache_samples:] = np.linspace(1, 0, detache_samples)
            modification *= detache_env
        
        elif articulation == 'grace':
            grace_duration = min(0.04, duration * 0.2)
            grace_samples = int(grace_duration * self.sample_rate)
            if grace_samples < len(waveform) // 2:
                grace_freq = freq * SEMITONE_RATIO
                grace_t = np.arange(grace_samples) / self.sample_rate
                grace_wave = np.sin(2 * np.pi * grace_freq * grace_t)
                grace_env = np.linspace(0, 1, grace_samples // 2)
                grace_env = np.concatenate([grace_env, grace_env[::-1]])
                additive[:grace_samples] += grace_wave[:len(grace_env)] * grace_env * 0.4
        
        elif articulation == 'smear':
            smear_freq = 18.0
            smear_mod = 0.12 * np.sin(2 * np.pi * smear_freq * t)
            modification *= (1 + smear_mod)
        
        elif articulation == 'flip':
            flip_duration = min(0.025, duration * 0.15)
            flip_samples = min(int(flip_duration * self.sample_rate), len(waveform) // 3)
            flip_freq = freq * SEMITONE_RATIO * 2
            flip_t = np.arange(flip_samples) / self.sample_rate
            flip_wave = np.sin(2 * np.pi * flip_freq * flip_t)
            flip_env = np.linspace(0, 1, flip_samples // 2)
            flip_env = np.concatenate([flip_env, flip_env[::-1]])
            additive[:flip_samples] += flip_wave[:len(flip_env)] * flip_env * 0.35
        
        # === ADDITIONAL GUITAR TECHNIQUES ===
        elif articulation == 'palm_mute':
            mute_env = np.exp(-t / 0.15)
            modification *= (1 - 0.6 * mute_env)
        
        elif articulation == 'picking':
            pick_osc = 8.0  # Picking frequency
            pick_mod = 0.15 * (1 + np.sin(2 * np.pi * pick_osc * t))
            modification *= pick_mod
        
        elif articulation == 'tapping':
            tap_freq = 15.0
            tap_mod = 0.2 * (1 + np.sin(2 * np.pi * tap_freq * t))
            modification *= tap_mod
        
        elif articulation == 'strumming':
            strum_env = np.linspace(0.3, 1.0, len(waveform) // 4)
            strum_env = np.concatenate([strum_env, np.ones(len(waveform) - len(strum_env))])
            modification *= strum_env
        
        elif articulation == 'natural_harmonic':
            harmonic_freq = freq * 2.0
            harmonic_wave = np.sin(2 * np.pi * harmonic_freq * t)
            # Bell-like envelope
            harm_env = np.exp(-t / 0.5)
            additive += harmonic_wave * harm_env * 0.5
        
        elif articulation == 'artificial_harmonic':
            harmonic_freq = freq * 3.0
            harmonic_wave = np.sin(2 * np.pi * harmonic_freq * t)
            harm_env = np.exp(-t / 0.4)
            additive += harmonic_wave * harm_env * 0.45
        
        elif articulation == 'release_bend':
            bend_amount = 0.95
            freq_slide = np.linspace(freq * bend_amount, freq, len(waveform) // 3)
            freq_slide = np.concatenate([freq_slide, np.full(len(waveform) - len(freq_slide), freq)])
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            release_bend_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 3)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.5)
            additive += release_bend_wave * fade * 0.4
        
        # === ADDITIONAL WIND TECHNIQUES ===
        elif articulation == 'tonguing':
            tonguing_osc = 12.0
            tonguing_mod = 0.25 * (1 + np.sin(2 * np.pi * tonguing_osc * t))
            modification *= tonguing_mod
        
        elif articulation == 'double_tongue':
            double_osc = 8.0
            double_mod = 0.2 * (1 + np.sin(2 * np.pi * double_osc * t))
            modification *= double_mod
        
        elif articulation == 'flutter_tongue':
            flutter_osc = 14.0
            flutter_mod = 0.2 * (1 + np.sin(2 * np.pi * flutter_osc * t))
            modification *= flutter_mod
        
        elif articulation == 'lip_trill':
            trill_freq = 5.0
            trill_mod = np.sin(2 * np.pi * trill_freq * t)
            freq_mod = freq * (1 + 0.04 * trill_mod)
            phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
            trill_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.6)
            additive += trill_wave * fade * 0.35
        
        elif articulation == 'sub_breath':
            # Sub-bass with breath noise
            noise = 0.08 * np.random.normal(0, 1, len(waveform))
            low_pass = np.convolve(noise, np.ones(150) / 150, mode='same')
            additive += low_pass
            # Also lower the fundamental
            sub_freq = freq * 0.5
            sub_wave = np.sin(2 * np.pi * sub_freq * t)
            additive += sub_wave * 0.15
        
        # === ADDITIONAL STRING TECHNIQUES ===
        elif articulation == 'spiccato':
            spiccato_env = np.exp(-t / 0.06)
            modification *= spiccato_env
        
        elif articulation == 'tremolando':
            trem_freq = 12.0
            trem_mod = 0.15 * (1 + np.sin(2 * np.pi * trem_freq * t))
            modification *= trem_mod
        
        elif articulation == 'sul_ponte':
            # Near bridge - brighter, more nasal
            pont_harmonic = np.sin(2 * np.pi * freq * 2.5 * t) * 0.25
            additive += pont_harmonic
        
        # === BRASS TECHNIQUES ===
        elif articulation == 'muted_brass':
            mute_env = np.exp(-t / 0.2)
            modification *= (1 - 0.4 * mute_env)
            # Add metallic harmonics
            metal_harm = np.sin(2 * np.pi * freq * 3 * t) * 0.15
            additive += metal_harm * mute_env
        
        elif articulation == 'cup_mute':
            cup_env = np.exp(-t / 0.25)
            modification *= (1 - 0.35 * cup_env)
            cup_harm = np.sin(2 * np.pi * freq * 2 * t) * 0.1
            additive += cup_harm * cup_env
        
        elif articulation == 'harmon_mute':
            harm_env = np.exp(-t / 0.3)
            # Add harmon mute characteristic
            harm_freq = freq * 1.5
            harm_wave = np.sin(2 * np.pi * harm_freq * t)
            additive += harm_wave * harm_env * 0.2
        
        elif articulation == 'stopped':
            stopped_env = np.exp(-t / 0.12)
            modification *= stopped_env
        
        # === KEYBOARD TECHNIQUES ===
        elif articulation == 'pedal_noise':
            # Pedal up/down noise
            noise_duration = min(0.05, duration * 0.1)
            noise_samples = int(noise_duration * self.sample_rate)
            pedal_noise = 0.2 * np.random.normal(0, 1, noise_samples)
            # Add at the end
            if len(waveform) > noise_samples:
                additive[-noise_samples:] += pedal_noise
        
        elif articulation == 'key_off':
            # Key off - release sound
            release_env = np.exp(-t / 0.15)
            modification *= release_env
        
        # === EXPRESSION ARTICULATIONS ===
        elif articulation == 'subito':
            # Sudden change
            subito_point = len(waveform) // 3
            subito_env = np.ones(len(waveform))
            subito_env[:subito_point] *= 1.5
            modification *= subito_env
        
        elif articulation == 'forzing':
            # Forced, accented sound
            force_env = np.exp(-t / 0.06) * 1.6
            modification *= force_env
        
        elif articulation == 'weeping':
            # Sad, descending feel
            weep_freq = np.linspace(freq * 1.02, freq * 0.95, len(waveform))
            phase = np.cumsum(2 * np.pi * weep_freq / self.sample_rate)
            weep_wave = np.sin(phase)
            weep_env = np.linspace(1.0, 0.5, len(waveform))
            additive += weep_wave * weep_env * 0.3
        
        elif articulation == 'shouting':
            # Aggressive, loud
            shout_env = np.exp(-t / 0.08) * 1.4
            modification *= shout_env
            # Add distortion
            shout_dist = np.tanh(waveform * 1.5) * 0.3
            additive += shout_dist
        
        # === PERCUSSION TEXTURES ===
        elif articulation == 'rim_shot':
            rim_duration = 0.008
            rim_samples = min(int(rim_duration * self.sample_rate), 350)
            rim_noise = 0.5 * np.random.normal(0, 1, rim_samples)
            additive[:rim_samples] += rim_noise
        
        elif articulation == 'brush':
            brush_osc = 20.0
            brush_mod = 0.1 * (1 + np.sin(2 * np.pi * brush_osc * t))
            modification *= brush_mod
        
        # === GLISSENDO VARIATIONS ===
        elif articulation == 'gliss_up':
            gliss_amount = 1.1
            freq_slide = np.linspace(freq, freq * gliss_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            gliss_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.6)
            additive += gliss_wave * fade * 0.4
        
        elif articulation == 'gliss_down':
            gliss_amount = 0.9
            freq_slide = np.linspace(freq, freq * gliss_amount, len(waveform))
            phase = np.cumsum(2 * np.pi * freq_slide / self.sample_rate)
            gliss_wave = np.sin(phase)
            fade = np.linspace(0, 1, len(waveform) // 2)
            fade = np.concatenate([fade, np.ones(len(waveform) - len(fade))])
            modification *= (1 - fade * 0.6)
            additive += gliss_wave * fade * 0.4
        
        elif articulation == 'arp':
            # Arpeggio-like effect
            arp_freqs = [freq, freq * 1.25, freq * 1.5, freq * 1.25]
            arp_len = len(waveform) // len(arp_freqs)
            for i, af in enumerate(arp_freqs):
                start = i * arp_len
                end = min((i + 1) * arp_len, len(waveform))
                arp_wave = np.sin(2 * np.pi * af * t[start:end])
                fade = np.linspace(0.3, 0.8, end - start)
                additive[start:end] += arp_wave * fade * 0.2
        
        result = waveform * modification + additive
        
        max_val = np.max(np.abs(result))
        if max_val > 1.0:
            result /= max_val
        
        return result.astype(np.float32)
    
    # =========================================================================
    # Note Synthesis
    # =========================================================================
    
    def synthesize_note(
        self,
        freq: float,
        duration: float,
        velocity: int = 100,
        articulation: Optional[str] = None,
        pitch_bend: float = 0.0,
        mod_wheel: float = 0.0
    ) -> np.ndarray:
        """Synthesize a single note with all effects."""
        if articulation is None:
            articulation = self.current_articulation
        elif not isinstance(articulation, str):
            articulation = str(articulation)
        
        try:
            base = self._generate_base_tone(freq, duration, velocity, pitch_bend, mod_wheel)
            articulated = self._apply_articulation(base, articulation, freq, velocity)
            
            max_val = np.max(np.abs(articulated))
            if max_val > 0:
                articulated /= max_val
            
            return articulated
        
        except Exception as e:
            logger.error(f"Error synthesizing note: {e}")
            raise
    
    def synthesize_note_sequence(
        self,
        notes: List[Dict[str, Any]],
        overlap: float = 0.05
    ) -> np.ndarray:
        """Synthesize a sequence of notes with proper legato handling."""
        audio = np.array([], dtype=np.float32)
        prev_articulation = None
        
        for note in notes:
            freq = note.get('freq', 440.0)
            duration = note.get('duration', 1.0)
            velocity = int(note.get('velocity', 100))
            art = note.get('articulation')
            if art is None:
                art = self.current_articulation
            elif not isinstance(art, str):
                art = str(art)
            
            duration = max(0.01, duration)
            velocity = max(1, min(127, velocity))
            
            note_audio = self.synthesize_note(freq, duration, velocity, art)
            
            if prev_articulation == 'legato' and len(audio) > 0:
                overlap_samples = int(overlap * self.sample_rate)
                overlap_samples = max(0, min(overlap_samples, len(audio)))
                overlap_samples = min(overlap_samples, len(note_audio))
                
                if overlap_samples > 0:
                    fade_out = np.linspace(1, 0, overlap_samples)
                    fade_in = np.linspace(0, 1, overlap_samples)
                    audio[-overlap_samples:] *= fade_out
                    note_audio[:overlap_samples] *= fade_in
                    audio[-overlap_samples:] += note_audio[:overlap_samples]
                    audio = np.concatenate([audio, note_audio[overlap_samples:]])
                else:
                    audio = np.concatenate([audio, note_audio])
            else:
                audio = np.concatenate([audio, note_audio])
            
            prev_articulation = art
        
        return audio
    
    # =========================================================================
    # Effects Processing
    # =========================================================================
    
    def apply_effects(self, audio: np.ndarray) -> np.ndarray:
        """Apply reverb and delay effects."""
        if len(audio) == 0:
            return audio
        
        if self.config.enable_reverb:
            audio = self.reverb.process(audio)
        
        if self.config.enable_delay:
            audio = self.delay.process(audio)
        
        audio *= self.config.master_volume
        audio = np.tanh(audio * 1.5) / 1.5
        
        return audio
    
    # =========================================================================
    # Output Methods
    # =========================================================================
    
    def save_to_wav(self, audio: np.ndarray, filename: str) -> None:
        """Save audio to WAV file with stereo support."""
        try:
            if audio.ndim == 1:
                audio = np.stack([audio, audio], axis=1)
            
            audio = self.apply_effects(audio)
            audio_int16 = (audio * 32767).astype(np.int16)
            
            wavfile.write(filename, self.sample_rate, audio_int16)
            logger.info(f"Saved audio to {filename}")
        
        except Exception as e:
            logger.error(f"Error saving WAV: {e}")
            raise
    
    def play_audio(self, audio: np.ndarray):
        """Play audio through audio output."""
        if len(audio) == 0:
            return
        
        audio = self.apply_effects(audio)
        self.audio_output.write(audio)
    
    # =========================================================================
    # MIDI Processing
    # =========================================================================
    
    def process_midi_file(
        self,
        midi_path: str,
        output_wav: str = 'output.wav',
        tempo: int = 500000
    ) -> None:
        """Process MIDI file and render to WAV."""
        from .constants import MIDO_AVAILABLE
        if not MIDO_AVAILABLE:
            logger.error("mido library not available for MIDI processing")
            return
        
        import mido
        from mido import MidiFile
        
        mid = MidiFile(midi_path)
        
        ticks_per_beat = mid.ticks_per_beat if mid.ticks_per_beat > 0 else 480
        
        audio_chunks: List[np.ndarray] = []
        active_notes: Dict[int, NoteEvent] = {}
        current_time = 0.0
        
        for track in mid.tracks:
            for msg in track:
                delta_time_sec = mido.tick2second(msg.time, ticks_per_beat, tempo)
                current_time += delta_time_sec
                
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                
                if msg.type == 'control_change':
                    if msg.control == NRPN_MSB_CONTROL:
                        self.nrpn_msb = max(0, min(127, msg.value))
                    elif msg.control == NRPN_LSB_CONTROL:
                        self.nrpn_lsb = max(0, min(127, msg.value))
                        self.current_articulation = self.nrpn_mapper.get_articulation(
                            self.nrpn_msb, self.nrpn_lsb
                        )
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    note_num = max(0, min(127, msg.note))
                    velocity = max(0, min(127, msg.velocity))
                    freq = midi_note_to_frequency(note_num)
                    
                    active_notes[note_num] = NoteEvent(
                        note=note_num,
                        velocity=velocity,
                        start_time=current_time,
                        duration=0.0,
                        frequency=freq,
                        articulation=self.current_articulation,
                        pitch_bend=self.current_pitch_bend,
                        mod_wheel=self.current_mod_wheel
                    )
                
                elif (msg.type == 'note_off' or 
                      (msg.type == 'note_on' and msg.velocity == 0)):
                    note_num = max(0, min(127, msg.note))
                    
                    if note_num in active_notes:
                        note_event = active_notes.pop(note_num)
                        note_event.duration = current_time - note_event.start_time
                        note_event.duration = max(0.01, note_event.duration)
                        
                        note_audio = self.synthesize_note(
                            note_event.frequency,
                            note_event.duration,
                            note_event.velocity,
                            note_event.articulation,
                            note_event.pitch_bend,
                            note_event.mod_wheel
                        )
                        
                        start_sample = int(note_event.start_time * self.sample_rate)
                        required_length = start_sample + len(note_audio)
                        current_length = sum(len(c) for c in audio_chunks)
                        
                        if current_length < required_length:
                            padding = np.zeros(required_length - current_length, dtype=np.float32)
                            if audio_chunks:
                                audio_chunks[-1] = np.concatenate([audio_chunks[-1], padding])
                            else:
                                audio_chunks.append(padding)
                        
                        if audio_chunks:
                            audio_chunks[-1] = np.concatenate([audio_chunks[-1], note_audio])
                        else:
                            audio_chunks.append(note_audio)
        
        if audio_chunks:
            final_audio = np.concatenate(audio_chunks)
            self.save_to_wav(final_audio, output_wav)
        else:
            logger.warning("No audio generated from MIDI file")
    
    def listen_midi_real_time(
        self,
        port_name: Optional[str] = None,
        output_device: Optional[str] = None
    ) -> None:
        """Real-time MIDI listening with audio output."""
        from .constants import MIDO_AVAILABLE
        if not MIDO_AVAILABLE:
            logger.error("mido library not available for MIDI input")
            return
        
        import mido
        
        if port_name is None:
            available_ports = mido.get_input_names()
            if not available_ports:
                raise ValueError("No MIDI input ports available.")
            port_name = available_ports[0]
        
        logger.info(f"Listening on MIDI port: {port_name}")
        
        self.audio_output.start()
        self._running = True
        
        active_notes: Dict[int, float] = {}
        note_frequencies: Dict[int, float] = {}
        
        try:
            with mido.open_input(port_name) as inport:
                while self._running and not self._stop_event.is_set():
                    for msg in inport.iter_pending():
                        current_time = time.time()
                        
                        if msg.type == 'control_change':
                            if msg.control == NRPN_MSB_CONTROL:
                                self.nrpn_msb = max(0, min(127, msg.value))
                            elif msg.control == NRPN_LSB_CONTROL:
                                self.nrpn_lsb = max(0, min(127, msg.value))
                                self.current_articulation = self.nrpn_mapper.get_articulation(
                                    self.nrpn_msb, self.nrpn_lsb
                                )
                        
                        if msg.type == 'control_change' and msg.control == MOD_WHEEL_CONTROL:
                            self.current_mod_wheel = max(0, min(127, msg.value)) / 127.0
                        
                        if msg.type == 'note_on' and msg.velocity > 0:
                            note_num = max(0, min(127, msg.note))
                            velocity = max(0, min(127, msg.velocity))
                            
                            active_notes[note_num] = current_time
                            note_frequencies[note_num] = midi_note_to_frequency(note_num)
                            
                            logger.info(f"Note ON: {note_num}, velocity: {velocity}")
                        
                        elif (msg.type == 'note_off' or 
                              (msg.type == 'note_on' and msg.velocity == 0)):
                            note_num = max(0, min(127, msg.note))
                            
                            if note_num in active_notes:
                                start_time = active_notes.pop(note_num)
                                duration = current_time - start_time
                                duration = max(0.01, duration)
                                
                                freq = note_frequencies.pop(note_num, 440.0)
                                
                                note_audio = self.synthesize_note(
                                    freq,
                                    duration,
                                    100,
                                    self.current_articulation,
                                    self.current_pitch_bend,
                                    self.current_mod_wheel
                                )
                                
                                self.play_audio(note_audio)
                    
                    time.sleep(0.001)
        
        except Exception as e:
            logger.error(f"Error in MIDI listener: {e}")
        finally:
            self.stop()
    
    def start_midi_listener(self, port_name: Optional[str] = None):
        """Start MIDI listener in a separate thread."""
        self._stop_event.clear()
        self._midi_thread = threading.Thread(
            target=self.listen_midi_real_time,
            args=(port_name,),
            daemon=True
        )
        self._midi_thread.start()
        logger.info("MIDI listener started in background")
    
    def stop(self):
        """Stop the synthesizer and release resources."""
        self._running = False
        self._stop_event.set()
        
        self.audio_output.stop()
        self.voice_manager.all_notes_off()
        self.reverb.reset()
        self.delay.reset()
        
        logger.info("Synthesizer stopped")
    
    # =========================================================================
    # Parameter Setters
    # =========================================================================
    
    def set_instrument(self, instrument: str):
        """Change the current instrument."""
        instrument = instrument.lower()
        if instrument not in self.INSTRUMENT_PARAMS:
            raise ValueError(f"Unsupported instrument: {instrument}")
        self.instrument = instrument
        self.instrument_params = self._get_instrument_params()
        logger.info(f"Instrument changed to {instrument}")
    
    def set_articulation(self, articulation: str):
        """Set the current articulation."""
        self.current_articulation = articulation
        logger.info(f"Articulation set to {articulation}")
    
    def set_reverb_params(self, room_size: Optional[float] = None, wet_dry: Optional[float] = None):
        """Set reverb parameters."""
        self.reverb.set_parameters(room_size=room_size, wet_dry=wet_dry)
    
    def set_delay_params(
        self,
        delay_time: Optional[float] = None,
        feedback: Optional[float] = None,
        wet_dry: Optional[float] = None
    ):
        """Set delay parameters."""
        self.delay.set_parameters(
            delay_time=delay_time,
            feedback=feedback,
            wet_dry=wet_dry
        )
    
    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)."""
        self.config.master_volume = np.clip(volume, 0.0, 1.0)
    
    # =========================================================================
    # MIDI Controller Processing
    # =========================================================================
    
    def process_control_change(self, control: int, value: int) -> None:
        """Process MIDI Control Change messages.
        
        Args:
            control: CC number (0-127)
            value: CC value (0-127)
        """
        from .constants import (
            CC_BANK_SELECT_MSB, CC_BANK_SELECT_LSB, CC_MODULATION,
            CC_BREATH_CONTROLLER, CC_FOOT_CONTROLLER, CC_VOLUME,
            CC_PAN, CC_EXPRESSION, CC_SUSTAIN, CC_PORTAMENTO,
            CC_SOSTENUTO, CC_SOFT_PEDAL, CC_RESONANCE_FILTER,
            CC_RELEASE_TIME, CC_ATTACK_TIME, CC_CUTOFF_FILTER,
            CC_DECAY_TIME, CC_VIBRATO_RATE, CC_VIBRATO_DEPTH,
            CC_VIBRATO_DELAY, CC_PORTAMENTO_TIME, NRPN_MSB_CONTROL,
            NRPN_LSB_CONTROL
        )
        
        value = max(0, min(127, value))
        
        if control == CC_BANK_SELECT_MSB:
            self.bank_msb = value
            logger.debug(f"Bank MSB: {value}")
        
        elif control == CC_BANK_SELECT_LSB:
            self.bank_lsb = value
            logger.debug(f"Bank LSB: {value}")
        
        elif control == CC_MODULATION:
            self.current_mod_wheel = value / 127.0
        
        elif control == CC_BREATH_CONTROLLER:
            self.breath_controller = value
            logger.debug(f"Breath Controller: {value}")
        
        elif control == CC_FOOT_CONTROLLER:
            self.foot_controller = value
        
        elif control == CC_VOLUME:
            self.volume = value
            logger.debug(f"Volume: {value}")
        
        elif control == CC_PAN:
            self.pan = value
            logger.debug(f"Pan: {value}")
        
        elif control == CC_EXPRESSION:
            self.expression = value
            logger.debug(f"Expression: {value}")
        
        elif control == CC_SUSTAIN:
            # Sustain pedal: value >= 64 = on, < 64 = off
            was_on = self.sustain_pedal
            self.sustain_pedal = value >= 64
            
            if was_on and not self.sustain_pedal:
                # Sustain released - release all sustained notes
                self._release_sustained_notes()
            logger.debug(f"Sustain: {self.sustain_pedal}")
        
        elif control == CC_PORTAMENTO:
            self.portamento_on = value >= 64
        
        elif control == CC_SOSTENUTO:
            # Sostenuto: holds only notes that were on when pressed
            was_on = self.sostenuto
            self.sostenuto = value >= 64
            
            if was_on and not self.sostenuto:
                self._release_sostenuto_notes()
            logger.debug(f"Sostenuto: {self.sostenuto}")
        
        elif control == CC_SOFT_PEDAL:
            self.soft_pedal = value >= 64
        
        elif control == CC_RESONANCE_FILTER:
            self.filter_resonance = value
        
        elif control == CC_ATTACK_TIME:
            self.attack_time_adj = value
        
        elif control == CC_CUTOFF_FILTER:
            self.filter_cutoff = value
        
        elif control == CC_DECAY_TIME:
            pass  # Could adjust decay
        
        elif control == CC_RELEASE_TIME:
            self.release_time_adj = value
        
        elif control == CC_VIBRATO_RATE:
            self.vibrato_rate_adj = value
            # Update vibrato rate
            self.vibrato_rate = 5.0 * (value / 64.0)
        
        elif control == CC_VIBRATO_DEPTH:
            self.vibrato_depth_adj = value
            # Update vibrato depth
            self.vibrato_depth = 0.05 * (value / 64.0)
        
        elif control == CC_VIBRATO_DELAY:
            pass  # Could add vibrato delay
        
        elif control == CC_PORTAMENTO_TIME:
            self.portamento_time = value
        
        elif control == NRPN_MSB_CONTROL:
            self.nrpn_msb = value
        
        elif control == NRPN_LSB_CONTROL:
            self.nrpn_lsb = value
            # Update articulation from NRPN
            self.current_articulation = self.nrpn_mapper.get_articulation(
                self.nrpn_msb, self.nrpn_lsb
            )
            logger.debug(f"NRPN Articulation: {self.current_articulation}")
    
    def process_program_change(self, program: int) -> None:
        """Process MIDI Program Change message.
        
        Args:
            program: Program number (0-127)
        """
        from .nrpn import Genos2VoiceBank
        
        program = max(0, min(127, program))
        self.program_change = program
        
        # Look up instrument from voice bank
        instrument_name = Genos2VoiceBank.get_instrument(
            self.bank_msb, self.bank_lsb, program
        )
        
        if instrument_name:
            if instrument_name in self.INSTRUMENT_PARAMS:
                self.set_instrument(instrument_name)
                logger.info(f"Program Change: Bank {self.bank_msb}:{self.bank_lsb}, "
                          f"Program {program} -> {instrument_name}")
            else:
                logger.warning(f"Program {program} maps to unknown instrument: {instrument_name}")
        else:
            logger.debug(f"No voice mapping for Bank {self.bank_msb}:{self.bank_lsb}, Program {program}")
    
    def _release_sustained_notes(self) -> None:
        """Release all notes being held by sustain pedal."""
        # In real-time mode, this would trigger note-offs
        # For batch processing, notes would need to be released
        self._sustained_notes.clear()
        logger.debug("Released sustained notes")
    
    def _release_sostenuto_notes(self) -> None:
        """Release all notes being held by sostenuto pedal."""
        self._sostenuto_notes.clear()
        logger.debug("Released sostenuto notes")
    
    def _get_effective_velocity(self, velocity: int) -> int:
        """Calculate effective velocity from velocity + expression + volume.
        
        Args:
            velocity: Note velocity (0-127)
            
        Returns:
            Effective velocity after controller adjustments
        """
        # Combine velocity with expression and volume
        # MIDI spec: effective = velocity * (volume/127) * (expression/127)
        vol_factor = self.volume / 127.0
        expr_factor = self.expression / 127.0
        
        effective = velocity * vol_factor * expr_factor
        return max(1, min(127, int(effective)))
    
    def _apply_pan_to_audio(self, audio: np.ndarray) -> np.ndarray:
        """Apply stereo pan to audio.
        
        Args:
            audio: Mono audio array
            
        Returns:
            Stereo audio array with pan applied
        """
        if audio.ndim == 1:
            # Convert to stereo
            stereo = np.stack([audio, audio], axis=1)
        else:
            stereo = audio
        
        # Calculate pan values (0 = full left, 64 = center, 127 = full right)
        pan_val = self.pan / 127.0
        
        # Calculate left/right gains
        if pan_val < 0.5:
            # Left side
            left_gain = 1.0
            right_gain = pan_val * 2.0
        else:
            # Right side
            left_gain = (1.0 - pan_val) * 2.0
            right_gain = 1.0
        
        # Apply gains
        stereo[:, 0] *= left_gain
        stereo[:, 1] *= right_gain
        
        return stereo
